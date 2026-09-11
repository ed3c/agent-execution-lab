from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_execution_lab.lab07 import run_crash_gap_experiment


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = run_crash_gap_experiment(Path(directory))

    baseline = report["baseline"]
    treatment = report["treatment"]
    passed = (
        baseline["return_codes"] == [99, 0]
        and baseline["duplicate_effects"] == 1
        and baseline["physical_effects"] == 2
        and treatment["return_codes"] == [99, 0]
        and treatment["duplicate_effects"] == 0
        and treatment["physical_effects"] == 1
        and treatment["reconciliations"] >= 1
        and treatment["operation_ids_seen"] == ["run-1:step-1"]
        and treatment["state"]["status"] == "completed"
    )
    report["claim_passed"] = passed

    evidence = Path("evidence/experiments/lab07.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"machine evidence: {evidence.resolve()}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
