from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeExternalService:
    writes: list[dict[str, Any]] = field(default_factory=list)
    idempotency_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    delay_seconds: float = 0.0

    async def write(self, payload: dict[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if idempotency_key and idempotency_key in self.idempotency_results:
            return self.idempotency_results[idempotency_key]
        result = {"write_index": len(self.writes), "payload": dict(payload)}
        self.writes.append(dict(payload))
        if idempotency_key:
            self.idempotency_results[idempotency_key] = result
        return result


async def direct_write(service: FakeExternalService, payload: dict[str, Any]) -> dict[str, Any]:
    """Unsafe baseline: forwards whatever the caller supplied."""
    return await service.write(payload)


@dataclass
class AuditEvent:
    allowed: bool
    reason: str
    action: str | None
    idempotency_key: str | None


@dataclass
class ToolGateway:
    service: FakeExternalService
    allowed_actions: set[str]
    timeout_seconds: float = 1.0
    audit: list[AuditEvent] = field(default_factory=list)

    async def write(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        action = payload.get("action")
        value = payload.get("value")
        if not isinstance(action, str) or not action:
            self._deny("invalid action", action, idempotency_key)
            raise ValueError("payload.action must be a non-empty string")
        if not isinstance(value, str) or not value:
            self._deny("invalid value", action, idempotency_key)
            raise ValueError("payload.value must be a non-empty string")
        if action not in self.allowed_actions:
            self._deny("unauthorized action", action, idempotency_key)
            raise PermissionError(f"action not allowed: {action}")
        if not idempotency_key:
            self._deny("missing idempotency key", action, idempotency_key)
            raise ValueError("idempotency key is required")

        try:
            result = await asyncio.wait_for(
                self.service.write(payload, idempotency_key=idempotency_key),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            self._deny("timeout", action, idempotency_key)
            raise

        self.audit.append(AuditEvent(True, "allowed", action, idempotency_key))
        return result

    def _deny(self, reason: str, action: str | None, key: str | None) -> None:
        self.audit.append(AuditEvent(False, reason, action, key))
