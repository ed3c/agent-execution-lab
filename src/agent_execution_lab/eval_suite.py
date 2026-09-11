from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .lab06 import run_suite
from .lab07 import run_crash_gap_experiment
from .lab08 import run_event_order_experiment
from .lab09 import run_hitl_experiment
from .lab10 import run_dag_experiment
from .lab11 import run_duplicate_worker_experiment


def _strip_time(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_time(v) for k, v in value.items() if "wall_time" not in k}
    if isinstance(value, list):
        return [_strip_time(v) for v in value]
    return value


def _fingerprint(comparisons: list[dict[str, Any]], negatives: list[dict[str, Any]]) -> str:
    stable = json.dumps(
        _strip_time({"comparisons": comparisons, "negative_controls": negatives}),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable.encode()).hexdigest()


def _lab07_comparison() -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory() as directory:
        report = run_crash_gap_experiment(Path(directory))
    baseline = report["baseline"]
    treatment = report["treatment"]
    passed = (
        baseline["return_codes"] == [99, 0]
        and baseline["duplicate_effects"] == 1
        and treatment["return_codes"] == [99, 0]
        and treatment["duplicate_effects"] == 0
        and treatment["physical_effects"] == 1
        and treatment["operation_ids_seen"] == ["run-1:step-1"]
    )
    return (
        {"name": "lab07-commit-checkpoint-gap", "baseline": baseline, "treatment": treatment, "claim_passed": passed},
        {"name": "planted-broken-checkpoint-only-replay", "rejected_by_grader": baseline["duplicate_effects"] > 0, "observed": baseline},
    )


def _lab08_comparison() -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory() as directory:
        report = run_event_order_experiment(Path(directory))
    baseline = report["baseline"]
    treatment = report["treatment"]
    passed = (
        baseline["diverged"] is True
        and treatment["state"] == "completed"
        and treatment["duplicates_ignored"] == 1
        and treatment["canonical_event_ids"] == ["event-start", "event-complete"]
        and treatment["operation_ids"] == ["run-1:step-1"]
    )
    return (
        {"name": "lab08-durable-event-replay", "baseline": baseline, "treatment": treatment, "claim_passed": passed},
        {"name": "planted-broken-last-arrival-wins-replay", "rejected_by_grader": baseline["reordered_state"] != "completed", "observed": baseline},
    )


def _lab09_comparison() -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        approved = run_hitl_experiment(root / "approved", decision="approved")
        rejected = run_hitl_experiment(root / "rejected", decision="rejected")
    baseline = approved["baseline"]
    treatment = {"approved": approved["treatment"], "rejected": rejected["treatment"]}
    passed = (
        baseline["request_ids"] == ["approval-1", "approval-2"]
        and baseline["physical_effects"] == 0
        and treatment["approved"]["request_ids"] == ["approval:run-1:privileged-step"]
        and treatment["approved"]["physical_effects"] == 1
        and treatment["rejected"]["physical_effects"] == 0
    )
    return (
        {"name": "lab09-durable-hitl-pause-resume", "baseline": baseline, "treatment": treatment, "claim_passed": passed},
        {"name": "planted-broken-in-memory-approval-identity", "rejected_by_grader": len(baseline["request_ids"]) > 1 and baseline["physical_effects"] == 0, "observed": baseline},
    )


def _lab10_comparison() -> tuple[dict[str, Any], dict[str, Any]]:
    report = run_dag_experiment()
    baseline = report["baseline"]
    treatment = report["treatment"]
    failure = report["branch_failure"]
    broken = report["planted_broken"]
    passed = (
        baseline["completed"] == ["A", "B", "C"]
        and treatment["completed"] == ["A", "B", "C"]
        and baseline["max_concurrency"] == 1
        and treatment["max_concurrency"] == 2
        and treatment["dependency_violations"] == []
        and treatment["wall_time_seconds"] < baseline["wall_time_seconds"] * 0.8
        and failure["failed"] == ["A"]
        and failure["completed"] == ["B"]
        and "C" not in failure["started"]
    )
    return (
        {"name": "lab10-bounded-concurrent-dag", "baseline": baseline, "treatment": {"normal": treatment, "branch_failure": failure}, "claim_passed": passed},
        {"name": "planted-broken-ignore-dag-dependencies", "rejected_by_grader": "C" in broken["dependency_violations"], "observed": broken},
    )


def _lab11_comparison() -> tuple[dict[str, Any], dict[str, Any]]:
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
    )
    return (
        {"name": "lab11-worker-lease-fencing", "baseline": baseline, "treatment": {"race": treatment, "takeover": takeover}, "claim_passed": passed},
        {"name": "planted-broken-lease-without-fencing", "rejected_by_grader": broken["physical_effects"] > 1, "observed": broken},
    )


def run_architecture_suite(seed: int) -> dict[str, Any]:
    prior = run_suite(seed)
    lab07, neg07 = _lab07_comparison()
    lab08, neg08 = _lab08_comparison()
    lab09, neg09 = _lab09_comparison()
    lab10, neg10 = _lab10_comparison()
    lab11, neg11 = _lab11_comparison()
    comparisons = [*prior["comparisons"], lab07, lab08, lab09, lab10, lab11]
    negatives = [prior["negative_control"], neg07, neg08, neg09, neg10, neg11]
    suite_passed = all(item["claim_passed"] for item in comparisons) and all(
        item["rejected_by_grader"] for item in negatives
    )
    return {
        "seed": seed,
        "suite_passed": suite_passed,
        "comparisons": comparisons,
        "negative_controls": negatives,
        "prior_suite_fingerprint": prior["semantic_fingerprint"],
        "semantic_fingerprint": _fingerprint(comparisons, negatives),
    }


def render_architecture_summary(report: dict[str, Any]) -> str:
    lines = [
        f"# Agent execution architecture eval — seed {report['seed']}",
        "",
        f"Suite: {'PASS' if report['suite_passed'] else 'FAIL'}",
        "",
    ]
    for item in report["comparisons"]:
        lines.append(f"- {'PASS' if item['claim_passed'] else 'FAIL'} — {item['name']}")
    for negative in report["negative_controls"]:
        lines.append(f"- {'PASS' if negative['rejected_by_grader'] else 'FAIL'} — reject {negative['name']}")
    lines.extend([
        "",
        f"Prior Lab 01–06 fingerprint: `{report['prior_suite_fingerprint']}`",
        f"Semantic fingerprint: `{report['semantic_fingerprint']}`",
        "",
    ])
    return "\n".join(lines)
