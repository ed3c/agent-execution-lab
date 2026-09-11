from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_execution_lab.lab03 import FakeAmbiguousService, blind_retry_write, safe_write


async def main_async() -> dict[str, object]:
    payload = {"amount": 10}

    baseline = FakeAmbiguousService(["postcommit_timeout", "normal"])
    await blind_retry_write(baseline, payload)

    ambiguous = FakeAmbiguousService(["postcommit_timeout"])
    _, ambiguous_metrics = await safe_write(
        ambiguous, payload, idempotency_key="logical-op-1"
    )

    transient = FakeAmbiguousService(["precommit_failure", "normal"])
    _, transient_metrics = await safe_write(
        transient, payload, idempotency_key="logical-op-2"
    )

    return {
        "blind_retry_ambiguous": {
            "service_calls": baseline.calls,
            "physical_writes": len(baseline.writes),
        },
        "idempotent_reconcile_ambiguous": {
            "service_calls": ambiguous.calls,
            "physical_writes": len(ambiguous.writes),
            "metrics": ambiguous_metrics.__dict__,
        },
        "bounded_retry_precommit": {
            "service_calls": transient.calls,
            "physical_writes": len(transient.writes),
            "metrics": transient_metrics.__dict__,
        },
    }


def main() -> None:
    evidence = asyncio.run(main_async())
    path = ROOT / "evidence" / "experiments" / "lab03.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
