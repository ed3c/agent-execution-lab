from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_execution_lab.lab08 import run_event_order_experiment


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = run_event_order_experiment(Path(directory))

    baseline = report["baseline"]
    treatment = report["treatment"]
    passed = (
        baseline["diverged"] is True
        and baseline["ordered_state"] == "completed"
        and baseline["reordered_state"] == "running"
        and treatment["state"] == "completed"
        and treatment["duplicates_ignored"] == 1
        and treatment["canonical_event_ids"] == ["event-start", "event-complete"]
        and treatment["operation_ids"] == ["run-1:step-1"]
    )
    report["claim_passed"] = passed

    evidence = Path("evidence/experiments/lab08.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"machine evidence: {evidence.resolve()}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
