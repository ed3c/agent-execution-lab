from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_execution_lab.lab09 import run_hitl_experiment


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        approved = run_hitl_experiment(Path(directory) / "approved", decision="approved")
        rejected = run_hitl_experiment(Path(directory) / "rejected", decision="rejected")

    baseline = approved["baseline"]
    treatment = approved["treatment"]
    reject_treatment = rejected["treatment"]
    passed = (
        baseline["return_codes"] == [99, 0]
        and baseline["request_ids"] == ["approval-1", "approval-2"]
        and baseline["physical_effects"] == 0
        and treatment["return_codes"] == [99, 0]
        and treatment["request_ids"] == ["approval:run-1:privileged-step"]
        and treatment["decision_writes"] == 1
        and treatment["physical_effects"] == 1
        and treatment["pause"]["status"] == "approved"
        and treatment["pause"]["operation_id"] == "run-1:privileged-step"
        and reject_treatment["physical_effects"] == 0
        and reject_treatment["pause"]["status"] == "rejected"
    )
    report = {"approved": approved, "rejected": rejected, "claim_passed": passed}
    evidence = Path("evidence/experiments/lab09.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"machine evidence: {evidence.resolve()}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
