from __future__ import annotations

from agent_execution_lab.lab06 import run_suite


def test_controlled_eval_suite_proves_all_five_claims_and_rejects_negative_control() -> None:
    report = run_suite(seed=17)
    assert report["suite_passed"] is True
    assert len(report["comparisons"]) == 5
    assert all(item["claim_passed"] for item in report["comparisons"])
    assert report["negative_control"]["rejected_by_grader"] is True


def test_same_seed_has_same_semantic_evidence_fingerprint() -> None:
    first = run_suite(seed=17)
    second = run_suite(seed=17)
    assert first["semantic_fingerprint"] == second["semantic_fingerprint"]
