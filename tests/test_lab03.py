from __future__ import annotations

import asyncio

from agent_execution_lab.lab03 import (
    FakeAmbiguousService,
    blind_retry_write,
    safe_write,
)


def run(coro):
    return asyncio.run(coro)


def test_blind_retry_duplicates_after_commit_when_response_is_lost() -> None:
    service = FakeAmbiguousService(["postcommit_timeout", "normal"])
    result = run(blind_retry_write(service, {"amount": 10}, max_attempts=2))
    assert result["write_index"] == 1
    assert service.calls == 2
    assert len(service.writes) == 2


def test_safe_write_reconciles_postcommit_timeout_without_duplicate() -> None:
    service = FakeAmbiguousService(["postcommit_timeout"])
    result, metrics = run(
        safe_write(service, {"amount": 10}, idempotency_key="payment-1")
    )
    assert result["write_index"] == 0
    assert service.calls == 1
    assert len(service.writes) == 1
    assert metrics.reconciliations == 1
    assert metrics.retries == 0


def test_safe_write_retries_known_precommit_transient_failure() -> None:
    service = FakeAmbiguousService(["precommit_failure", "normal"])
    result, metrics = run(
        safe_write(service, {"amount": 10}, idempotency_key="payment-2")
    )
    assert result["write_index"] == 0
    assert service.calls == 2
    assert len(service.writes) == 1
    assert metrics.retries == 1
    assert metrics.reconciliations == 0
