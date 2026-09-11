from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_execution_lab.lab02 import FakeExternalService, ToolGateway, direct_write


async def main_async() -> dict[str, object]:
    payload = {"action": "append", "value": "alpha"}
    baseline = FakeExternalService()
    await direct_write(baseline, {"value": "missing-action"})
    await direct_write(baseline, {"action": "delete", "value": "secret"})
    await direct_write(baseline, payload)
    await direct_write(baseline, payload)

    service = FakeExternalService()
    gateway = ToolGateway(service, allowed_actions={"append"})
    rejected = 0
    for bad, key in [
        ({"value": "missing-action"}, "bad"),
        ({"action": "delete", "value": "secret"}, "deny"),
    ]:
        try:
            await gateway.write(bad, idempotency_key=key)
        except (ValueError, PermissionError):
            rejected += 1
    await gateway.write(payload, idempotency_key="logical-op")
    await gateway.write(payload, idempotency_key="logical-op")

    return {
        "baseline": {"physical_writes": len(baseline.writes)},
        "treatment": {
            "physical_writes": len(service.writes),
            "rejected_invalid_or_unauthorized": rejected,
            "audit_events": [event.__dict__ for event in gateway.audit],
        },
    }


def main() -> None:
    evidence = asyncio.run(main_async())
    path = ROOT / "evidence" / "experiments" / "lab02.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
