from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


class TransientWriteError(RuntimeError):
    """Failure known to occur before commit; retry may be safe."""


class AmbiguousWriteError(RuntimeError):
    """The service may have committed, but the response was lost."""


@dataclass
class FakeAmbiguousService:
    modes: list[str]
    calls: int = 0
    writes: list[dict[str, Any]] = field(default_factory=list)
    by_key: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def write(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls += 1
        mode = self.modes.pop(0) if self.modes else "normal"

        if mode == "precommit_failure":
            raise TransientWriteError("injected pre-commit failure")

        if idempotency_key and idempotency_key in self.by_key:
            result = self.by_key[idempotency_key]
        else:
            result = {"write_index": len(self.writes), "payload": dict(payload)}
            self.writes.append(dict(payload))
            if idempotency_key:
                self.by_key[idempotency_key] = result

        if mode == "postcommit_timeout":
            raise AmbiguousWriteError("injected response loss after commit")

        return result

    async def read_by_idempotency_key(self, key: str) -> dict[str, Any] | None:
        return self.by_key.get(key)


async def blind_retry_write(
    service: FakeAmbiguousService,
    payload: dict[str, Any],
    *,
    max_attempts: int = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            return await service.write(payload)
        except (TransientWriteError, AmbiguousWriteError) as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


@dataclass
class SafeWriteMetrics:
    attempts: int = 0
    retries: int = 0
    reconciliations: int = 0


async def safe_write(
    service: FakeAmbiguousService,
    payload: dict[str, Any],
    *,
    idempotency_key: str,
    max_attempts: int = 3,
    backoff_seconds: float = 0.0,
) -> tuple[dict[str, Any], SafeWriteMetrics]:
    metrics = SafeWriteMetrics()

    for attempt in range(1, max_attempts + 1):
        metrics.attempts += 1
        try:
            result = await service.write(payload, idempotency_key=idempotency_key)
            return result, metrics
        except TransientWriteError:
            if attempt >= max_attempts:
                raise
            metrics.retries += 1
            if backoff_seconds:
                await asyncio.sleep(backoff_seconds * attempt)
        except AmbiguousWriteError:
            metrics.reconciliations += 1
            committed = await service.read_by_idempotency_key(idempotency_key)
            if committed is not None:
                return committed, metrics
            if attempt >= max_attempts:
                raise
            metrics.retries += 1
            if backoff_seconds:
                await asyncio.sleep(backoff_seconds * attempt)

    raise AssertionError("unreachable")
