from __future__ import annotations

from agent_execution_lab.lab10 import run_dag_experiment


def test_bounded_concurrency_reduces_independent_critical_path() -> None:
    report = run_dag_experiment()
    baseline = report["baseline"]
    treatment = report["treatment"]

    assert baseline["completed"] == ["A", "B", "C"]
    assert treatment["completed"] == ["A", "B", "C"]
    assert baseline["max_concurrency"] == 1
    assert treatment["max_concurrency"] == 2
    assert treatment["dependency_violations"] == []
    assert treatment["wall_time_seconds"] < baseline["wall_time_seconds"] * 0.8


def test_downstream_task_never_starts_before_dependencies_finish() -> None:
    report = run_dag_experiment()
    treatment = report["treatment"]

    assert treatment["started"][-1] == "C"
    assert treatment["dependency_violations"] == []


def test_failed_branch_blocks_dependent_task_without_erasing_independent_success() -> None:
    report = run_dag_experiment()
    failure = report["branch_failure"]

    assert failure["failed"] == ["A"]
    assert failure["completed"] == ["B"]
    assert "C" not in failure["started"]
    assert failure["dependency_violations"] == []


def test_naive_parallel_all_is_rejected_for_dependency_violation() -> None:
    report = run_dag_experiment()
    broken = report["planted_broken"]

    assert "C" in broken["dependency_violations"]
