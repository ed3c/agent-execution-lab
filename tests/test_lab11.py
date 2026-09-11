from __future__ import annotations

from pathlib import Path

from agent_execution_lab.lab11 import run_duplicate_worker_experiment


def test_shared_runnable_state_allows_duplicate_process_execution(tmp_path: Path) -> None:
    report = run_duplicate_worker_experiment(tmp_path)
    baseline = report["baseline"]

    assert baseline["return_codes"] == [0, 0]
    assert baseline["physical_effects"] == 2
    assert {effect["worker_id"] for effect in baseline["effects"]} == {"worker-a", "worker-b"}


def test_lease_allows_one_authoritative_worker_effect(tmp_path: Path) -> None:
    report = run_duplicate_worker_experiment(tmp_path)
    treatment = report["treatment"]

    assert treatment["return_codes"] == [0, 0]
    assert treatment["physical_effects"] == 1
    assert sum(item["token"] is not None for item in treatment["results"]) == 1
    assert sum(item["committed"] for item in treatment["results"]) == 1
    assert treatment["effects"][0]["operation_id"] == "run-1:step-1"


def test_expired_owner_can_be_replaced_but_stale_token_cannot_commit(tmp_path: Path) -> None:
    report = run_duplicate_worker_experiment(tmp_path)
    takeover = report["takeover"]

    assert takeover["token_a"] == 1
    assert takeover["token_b"] == 2
    assert takeover["stale_commit_accepted"] is False
    assert takeover["takeover_commit_accepted"] is True
    assert len(takeover["effects"]) == 1
    assert takeover["effects"][0]["worker_id"] == "worker-b"
    assert takeover["effects"][0]["token"] == 2


def test_lease_expiry_without_fencing_still_allows_stale_late_commit(tmp_path: Path) -> None:
    report = run_duplicate_worker_experiment(tmp_path)
    broken = report["planted_no_fencing"]

    assert broken["physical_effects"] == 2
    assert [effect["token"] for effect in broken["effects"]] == [1, 2]
    assert [effect["worker_id"] for effect in broken["effects"]] == ["worker-a", "worker-b"]
