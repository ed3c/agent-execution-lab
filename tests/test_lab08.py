from __future__ import annotations

from pathlib import Path

import pytest

from agent_execution_lab.lab08 import DurableEventLog, TransitionEvent, run_event_order_experiment


def test_mutable_snapshot_diverges_for_same_events_in_different_arrival_order(tmp_path: Path) -> None:
    report = run_event_order_experiment(tmp_path)
    baseline = report["baseline"]

    assert baseline["ordered_state"] == "completed"
    assert baseline["reordered_state"] == "running"
    assert baseline["diverged"] is True


def test_durable_event_replay_deduplicates_and_orders_transitions(tmp_path: Path) -> None:
    report = run_event_order_experiment(tmp_path)
    treatment = report["treatment"]

    assert treatment["state"] == "completed"
    assert treatment["canonical_event_ids"] == ["event-start", "event-complete"]
    assert treatment["duplicates_ignored"] == 1
    assert treatment["operation_ids"] == ["run-1:step-1"]
    assert treatment["stable_after_restart"] is True


def test_conflicting_duplicate_event_is_rejected(tmp_path: Path) -> None:
    log = DurableEventLog(tmp_path / "events.jsonl")
    log.append(TransitionEvent("same", 1, "step_started", "run-1:step-1"))
    log.append(TransitionEvent("same", 2, "step_completed", "run-1:step-1"))

    with pytest.raises(ValueError, match="conflicting duplicate event"):
        log.replay()
