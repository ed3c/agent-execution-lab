from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .lab07 import stable_operation_id


@dataclass(frozen=True)
class TransitionEvent:
    event_id: str
    sequence: int
    kind: str
    operation_id: str


def apply_mutable_snapshot(events: Iterable[TransitionEvent]) -> str:
    """Naive last-arrival-wins snapshot with no event identity or ordering semantics."""
    state = "pending"
    for event in events:
        if event.kind == "step_started":
            state = "running"
        elif event.kind == "step_completed":
            state = "completed"
        else:
            raise ValueError(f"unknown event kind: {event.kind}")
    return state


class DurableEventLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: TransitionEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read_arrival_order(self) -> list[TransitionEvent]:
        if not self.path.exists():
            return []
        events: list[TransitionEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(TransitionEvent(**json.loads(line)))
        return events

    def replay(self) -> dict[str, Any]:
        arrivals = self.read_arrival_order()
        by_id: dict[str, TransitionEvent] = {}
        duplicates_ignored = 0
        for event in arrivals:
            existing = by_id.get(event.event_id)
            if existing is None:
                by_id[event.event_id] = event
            elif existing == event:
                duplicates_ignored += 1
            else:
                raise ValueError(f"conflicting duplicate event: {event.event_id}")

        canonical = sorted(by_id.values(), key=lambda event: event.sequence)
        sequences = [event.sequence for event in canonical]
        if sequences != list(range(1, len(canonical) + 1)):
            raise ValueError(f"non-contiguous transition sequence: {sequences}")

        state = "pending"
        for event in canonical:
            if state == "pending" and event.kind == "step_started":
                state = "running"
            elif state == "running" and event.kind == "step_completed":
                state = "completed"
            else:
                raise ValueError(f"invalid transition: state={state}, event={event.kind}")

        return {
            "state": state,
            "arrival_event_ids": [event.event_id for event in arrivals],
            "canonical_event_ids": [event.event_id for event in canonical],
            "duplicates_ignored": duplicates_ignored,
            "operation_ids": sorted({event.operation_id for event in canonical}),
        }


def transition_fixture() -> tuple[TransitionEvent, TransitionEvent]:
    operation_id = stable_operation_id("run-1", "step-1")
    return (
        TransitionEvent("event-start", 1, "step_started", operation_id),
        TransitionEvent("event-complete", 2, "step_completed", operation_id),
    )


def run_event_order_experiment(root: Path) -> dict[str, Any]:
    started, completed = transition_fixture()
    ordered = [started, completed]
    reordered = [completed, started]

    baseline = {
        "ordered_state": apply_mutable_snapshot(ordered),
        "reordered_state": apply_mutable_snapshot(reordered),
    }
    baseline["diverged"] = baseline["ordered_state"] != baseline["reordered_state"]

    log = DurableEventLog(root / "events.jsonl")
    for event in [completed, started, started]:
        log.append(event)

    # Re-open from disk to prove replay does not rely on in-memory state.
    treatment = DurableEventLog(root / "events.jsonl").replay()
    treatment["stable_after_restart"] = treatment["state"] == "completed"

    return {"baseline": baseline, "treatment": treatment}
