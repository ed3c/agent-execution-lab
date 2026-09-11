from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CheckpointError(RuntimeError):
    pass


@dataclass(frozen=True)
class Checkpoint:
    task_id: str
    next_step: int
    version: int = 1


class CheckpointStore:
    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def _checksum(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def save(self, checkpoint: Checkpoint) -> None:
        body = {
            "version": checkpoint.version,
            "task_id": checkpoint.task_id,
            "next_step": checkpoint.next_step,
        }
        envelope = {"checkpoint": body, "checksum": self._checksum(body)}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(envelope), encoding="utf-8")
        os.replace(tmp, self.path)

    def load(self) -> Checkpoint | None:
        if not self.path.exists():
            return None
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            body = envelope["checkpoint"]
            checksum = envelope["checksum"]
            if checksum != self._checksum(body):
                raise CheckpointError("checkpoint checksum mismatch")
            if body.get("version") != 1:
                raise CheckpointError("unsupported checkpoint version")
            if not isinstance(body.get("task_id"), str):
                raise CheckpointError("invalid checkpoint task_id")
            if not isinstance(body.get("next_step"), int) or body["next_step"] < 0:
                raise CheckpointError("invalid checkpoint next_step")
            return Checkpoint(
                task_id=body["task_id"],
                next_step=body["next_step"],
                version=body["version"],
            )
        except CheckpointError:
            raise
        except Exception as exc:
            raise CheckpointError(f"invalid checkpoint: {exc}") from exc


def append_effect(path: Path, *, task_id: str, step: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"task_id": task_id, "step": step}) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_effect_steps(path: Path) -> list[int]:
    if not path.exists():
        return []
    return [json.loads(line)["step"] for line in path.read_text().splitlines() if line]


def worker(
    *,
    mode: str,
    task_id: str,
    total_steps: int,
    effects_path: Path,
    checkpoint_path: Path,
    crash_after_step: int | None,
) -> int:
    if mode not in {"baseline", "checkpoint"}:
        raise ValueError(f"unknown mode: {mode}")

    start_step = 0
    store = CheckpointStore(checkpoint_path)
    if mode == "checkpoint":
        checkpoint = store.load()
        if checkpoint is not None:
            if checkpoint.task_id != task_id:
                raise CheckpointError("checkpoint belongs to another task")
            start_step = checkpoint.next_step

    for step in range(start_step, total_steps):
        append_effect(effects_path, task_id=task_id, step=step)
        if mode == "checkpoint":
            # This lab crashes only after side effect + checkpoint are durable.
            # Crash between those writes is intentionally deferred to the next boundary experiment.
            store.save(Checkpoint(task_id=task_id, next_step=step + 1))
        if crash_after_step is not None and step == crash_after_step:
            os._exit(99)

    return 0


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "checkpoint"], required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--effects", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--crash-after-step", type=int)
    args = parser.parse_args()
    try:
        return worker(
            mode=args.mode,
            task_id=args.task_id,
            total_steps=args.total_steps,
            effects_path=args.effects,
            checkpoint_path=args.checkpoint,
            crash_after_step=args.crash_after_step,
        )
    except CheckpointError as exc:
        print(f"checkpoint error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
