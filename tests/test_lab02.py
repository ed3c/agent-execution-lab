from __future__ import annotations

import asyncio

import pytest

from agent_execution_lab.lab02 import FakeExternalService, ToolGateway, direct_write


def run(coro):
    return asyncio.run(coro)


def test_baseline_commits_malformed_and_unauthorized_payloads() -> None:
    service = FakeExternalService()
    run(direct_write(service, {"value": "missing-action"}))
    run(direct_write(service, {"action": "delete", "value": "secret"}))
    assert len(service.writes) == 2


def test_gateway_rejects_malformed_without_side_effect() -> None:
    service = FakeExternalService()
    gateway = ToolGateway(service, allowed_actions={"append"})
    with pytest.raises(ValueError):
        run(gateway.write({"value": "missing-action"}, idempotency_key="bad-1"))
    assert service.writes == []
    assert gateway.audit[-1].reason == "invalid action"


def test_gateway_rejects_unauthorized_without_side_effect() -> None:
    service = FakeExternalService()
    gateway = ToolGateway(service, allowed_actions={"append"})
    with pytest.raises(PermissionError):
        run(
            gateway.write(
                {"action": "delete", "value": "secret"},
                idempotency_key="deny-1",
            )
        )
    assert service.writes == []
    assert gateway.audit[-1].reason == "unauthorized action"


def test_baseline_duplicates_but_gateway_idempotency_deduplicates() -> None:
    baseline = FakeExternalService()
    payload = {"action": "append", "value": "alpha"}
    run(direct_write(baseline, payload))
    run(direct_write(baseline, payload))
    assert len(baseline.writes) == 2

    protected = FakeExternalService()
    gateway = ToolGateway(protected, allowed_actions={"append"})
    first = run(gateway.write(payload, idempotency_key="same-op"))
    second = run(gateway.write(payload, idempotency_key="same-op"))
    assert first == second
    assert len(protected.writes) == 1


def test_gateway_valid_action_still_succeeds() -> None:
    service = FakeExternalService()
    gateway = ToolGateway(service, allowed_actions={"append"})
    result = run(
        gateway.write(
            {"action": "append", "value": "ok"}, idempotency_key="valid-1"
        )
    )
    assert result["payload"]["value"] == "ok"
    assert len(service.writes) == 1
    assert gateway.audit[-1].allowed is True
