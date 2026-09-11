from __future__ import annotations

from agent_execution_lab.eval_suite import run_architecture_suite


def test_extended_suite_proves_six_claims_and_rejects_both_negative_controls() -> None:
    report = run_architecture_suite(seed=17)

    assert report["suite_passed"] is True
    assert len(report["comparisons"]) == 6
    assert all(item["claim_passed"] for item in report["comparisons"])
    assert len(report["negative_controls"]) == 2
    assert all(item["rejected_by_grader"] for item in report["negative_controls"])


def test_extended_suite_same_seed_has_same_semantic_fingerprint() -> None:
    first = run_architecture_suite(seed=17)
    second = run_architecture_suite(seed=17)

    assert first["prior_suite_fingerprint"] == second["prior_suite_fingerprint"]
    assert first["semantic_fingerprint"] == second["semantic_fingerprint"]
