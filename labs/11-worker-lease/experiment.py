from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_execution_lab.lab11 import run_duplicate_worker_experiment


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = run_duplicate_worker_experiment(Path(directory))

    baseline = report["baseline"]
    treatment = report["treatment"]
    takeover = report["takeover"]
    broken = report["planted_no_fencing"]
    passed = (
        baseline["return_codes"] == [0, 0]
        and baseline["physical_effects"] == 2
        and treatment["return_codes"] == [0, 0]
        and treatment["physical_effects"] == 1
        and sum(item["token"] is not None for item in treatment["results"]) == 1
        and sum(item["committed"] for item in treatment["results"]) == 1
        and takeover["token_a"] == 1
        and takeover["token_b"] == 2
        and takeover["stale_commit_accepted"] is False
        and takeover["takeover_commit_accepted"] is True
        and len(takeover["effects"]) == 1
        and broken["physical_effects"] == 2
    )
    report["claim_passed"] = passed
    evidence = Path("evidence/experiments/lab11.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"machine evidence: {evidence.resolve()}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
