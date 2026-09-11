from __future__ import annotations

import json
from pathlib import Path

from agent_execution_lab.lab10 import run_dag_experiment


def main() -> None:
    report = run_dag_experiment()
    baseline = report["baseline"]
    treatment = report["treatment"]
    broken = report["planted_broken"]
    failure = report["branch_failure"]

    passed = (
        baseline["completed"] == ["A", "B", "C"]
        and treatment["completed"] == ["A", "B", "C"]
        and baseline["max_concurrency"] == 1
        and treatment["max_concurrency"] == 2
        and treatment["dependency_violations"] == []
        and treatment["wall_time_seconds"] < baseline["wall_time_seconds"] * 0.8
        and "C" in broken["dependency_violations"]
        and failure["failed"] == ["A"]
        and failure["completed"] == ["B"]
        and "C" not in failure["started"]
    )
    report["claim_passed"] = passed
    evidence = Path("evidence/experiments/lab10.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"machine evidence: {evidence.resolve()}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
