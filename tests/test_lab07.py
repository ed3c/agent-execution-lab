from __future__ import annotations

from pathlib import Path

from agent_execution_lab.lab07 import run_crash_gap_experiment, stable_operation_id


def test_stable_operation_identity_is_deterministic() -> None:
    assert stable_operation_id("run-1", "step-1") == "run-1:step-1"
    assert stable_operation_id("run-1", "step-1") == stable_operation_id("run-1", "step-1")


def test_checkpoint_only_replay_duplicates_committed_side_effect(tmp_path: Path) -> None:
    report = run_crash_gap_experiment(tmp_path)
    baseline = report["baseline"]

    assert baseline["return_codes"] == [99, 0]
    assert baseline["write_calls"] == 2
    assert baseline["physical_effects"] == 2
    assert baseline["duplicate_effects"] == 1
    assert baseline["reconciliations"] == 0
    assert baseline["state"]["status"] == "completed"


def test_operation_identity_plus_reconciliation_avoids_duplicate_effect(tmp_path: Path) -> None:
    report = run_crash_gap_experiment(tmp_path)
    treatment = report["treatment"]

    assert treatment["return_codes"] == [99, 0]
    assert treatment["write_calls"] == 1
    assert treatment["physical_effects"] == 1
    assert treatment["duplicate_effects"] == 0
    assert treatment["reconciliations"] == 2
    assert treatment["operation_ids_seen"] == ["run-1:step-1"]
    assert treatment["state"]["operation_id"] == "run-1:step-1"
    assert treatment["state"]["status"] == "completed"


def test_treatment_advances_state_only_after_committed_outcome_is_known(tmp_path: Path) -> None:
    report = run_crash_gap_experiment(tmp_path)
    treatment = report["treatment"]

    assert treatment["reconciliations"] >= 1
    assert treatment["physical_effects"] == 1
    assert treatment["state"]["status"] == "completed"
