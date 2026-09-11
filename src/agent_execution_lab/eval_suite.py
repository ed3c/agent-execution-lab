from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .lab06 import run_suite
from .lab07 import run_crash_gap_experiment


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
    claim_passed = (
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
    comparison = {
        "name": "lab07-commit-checkpoint-gap",
        "baseline": baseline,
        "treatment": treatment,
        "claim_passed": claim_passed,
    }
    planted_broken = {
        "name": "planted-broken-checkpoint-only-replay",
        "rejected_by_grader": baseline["duplicate_effects"] > 0,
        "observed": baseline,
    }
    return comparison, planted_broken


def run_architecture_suite(seed: int) -> dict[str, Any]:
    prior = run_suite(seed)
    lab07, lab07_negative = _lab07_comparison()
    comparisons = [*prior["comparisons"], lab07]
    negatives = [prior["negative_control"], lab07_negative]
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
        lines.append(
            f"- {'PASS' if negative['rejected_by_grader'] else 'FAIL'} — reject {negative['name']}"
        )
    lines.extend(
        [
            "",
            f"Prior Lab 01–06 fingerprint: `{report['prior_suite_fingerprint']}`",
            f"Semantic fingerprint: `{report['semantic_fingerprint']}`",
            "",
        ]
    )
    return "\n".join(lines)
