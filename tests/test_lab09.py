from __future__ import annotations

from pathlib import Path

from agent_execution_lab.lab09 import run_hitl_experiment


def test_in_memory_approval_identity_is_lost_across_process_death(tmp_path: Path) -> None:
    report = run_hitl_experiment(tmp_path, decision="approved")
    baseline = report["baseline"]

    assert baseline["return_codes"] == [99, 0]
    assert baseline["request_ids"] == ["approval-1", "approval-2"]
    assert baseline["decisions"] == {"approval-1": "approved"}
    assert baseline["decision_writes"] == 1
    assert baseline["physical_effects"] == 0
    assert baseline["pause"] is None


def test_durable_pause_reuses_same_approval_after_restart(tmp_path: Path) -> None:
    report = run_hitl_experiment(tmp_path, decision="approved")
    treatment = report["treatment"]

    assert treatment["return_codes"] == [99, 0]
    assert treatment["request_ids"] == ["approval:run-1:privileged-step"]
    assert treatment["decisions"] == {"approval:run-1:privileged-step": "approved"}
    assert treatment["decision_writes"] == 1
    assert treatment["physical_effects"] == 1
    assert treatment["pause"] == {
        "operation_id": "run-1:privileged-step",
        "approval_id": "approval:run-1:privileged-step",
        "decision": "approved",
        "status": "approved",
    }


def test_rejection_survives_restart_and_blocks_privileged_effect(tmp_path: Path) -> None:
    report = run_hitl_experiment(tmp_path, decision="rejected")
    treatment = report["treatment"]

    assert treatment["request_ids"] == ["approval:run-1:privileged-step"]
    assert treatment["decisions"] == {"approval:run-1:privileged-step": "rejected"}
    assert treatment["decision_writes"] == 1
    assert treatment["physical_effects"] == 0
    assert treatment["pause"]["status"] == "rejected"
    assert treatment["pause"]["operation_id"] == "run-1:privileged-step"
