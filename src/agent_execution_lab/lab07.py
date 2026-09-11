from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_operation_id(run_id: str, step_id: str) -> str:
    return f"{run_id}:{step_id}"


def initialize_step_state(path: Path, *, run_id: str, step_id: str) -> None:
    _atomic_json_write(
        path,
        {
            "run_id": run_id,
            "step_id": step_id,
            "operation_id": stable_operation_id(run_id, step_id),
            "status": "pending",
        },
    )


class FileExternalService:
    """A process-persistent fake external service with observable physical effects."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"calls": [], "effects": [], "operations": {}}
        return _read_json(self.path)

    def _save(self, data: dict[str, Any]) -> None:
        _atomic_json_write(self.path, data)

    def commit_unkeyed(self, value: str) -> dict[str, Any]:
        data = self._load()
        effect = {"effect_id": len(data["effects"]), "operation_id": None, "value": value}
        data["calls"].append({"kind": "write", "operation_id": None})
        data["effects"].append(effect)
        self._save(data)
        return effect

    def commit_idempotent(self, operation_id: str, value: str) -> dict[str, Any]:
        data = self._load()
        data["calls"].append({"kind": "write", "operation_id": operation_id})
        existing = data["operations"].get(operation_id)
        if existing is not None:
            self._save(data)
            return existing
        effect = {
            "effect_id": len(data["effects"]),
            "operation_id": operation_id,
            "value": value,
        }
        data["effects"].append(effect)
        data["operations"][operation_id] = effect
        self._save(data)
        return effect

    def reconcile(self, operation_id: str) -> dict[str, Any] | None:
        data = self._load()
        data["calls"].append({"kind": "reconcile", "operation_id": operation_id})
        existing = data["operations"].get(operation_id)
        self._save(data)
        return existing

    def snapshot(self) -> dict[str, Any]:
        return self._load()


def execute_pending_step(
    *,
    mode: str,
    state_path: Path,
    service_path: Path,
    value: str,
    crash_after_commit: bool,
) -> None:
    state = _read_json(state_path)
    if state["status"] == "completed":
        return

    service = FileExternalService(service_path)
    if mode == "baseline":
        service.commit_unkeyed(value)
    elif mode == "treatment":
        operation_id = state["operation_id"]
        observed = service.reconcile(operation_id)
        if observed is None:
            service.commit_idempotent(operation_id, value)
    else:
        raise ValueError(f"unknown mode: {mode}")

    if crash_after_commit:
        os._exit(99)

    state["status"] = "completed"
    _atomic_json_write(state_path, state)


def _invoke_worker(
    root: Path,
    *,
    mode: str,
    crash_after_commit: bool,
) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "agent_execution_lab.lab07",
        "--mode",
        mode,
        "--state",
        str(root / "state.json"),
        "--service",
        str(root / "service.json"),
        "--value",
        "charge-10",
    ]
    if crash_after_commit:
        cmd.append("--crash-after-commit")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode


def _summarize(root: Path, return_codes: list[int]) -> dict[str, Any]:
    state = _read_json(root / "state.json")
    service = FileExternalService(root / "service.json").snapshot()
    write_calls = [call for call in service["calls"] if call["kind"] == "write"]
    reconciliations = [call for call in service["calls"] if call["kind"] == "reconcile"]
    operation_ids_seen = sorted(
        {
            call["operation_id"]
            for call in service["calls"]
            if call.get("operation_id") is not None
        }
    )
    return {
        "return_codes": return_codes,
        "service_calls": len(service["calls"]),
        "write_calls": len(write_calls),
        "physical_effects": len(service["effects"]),
        "duplicate_effects": max(0, len(service["effects"]) - 1),
        "reconciliations": len(reconciliations),
        "operation_ids_seen": operation_ids_seen,
        "state": state,
    }


def run_crash_gap_experiment(root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for mode in ("baseline", "treatment"):
        scenario = root / mode
        scenario.mkdir(parents=True, exist_ok=True)
        initialize_step_state(scenario / "state.json", run_id="run-1", step_id="step-1")
        first = _invoke_worker(scenario, mode=mode, crash_after_commit=True)
        second = _invoke_worker(scenario, mode=mode, crash_after_commit=False)
        report[mode] = _summarize(scenario, [first, second])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("baseline", "treatment"), required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--service", type=Path, required=True)
    parser.add_argument("--value", required=True)
    parser.add_argument("--crash-after-commit", action="store_true")
    args = parser.parse_args()
    execute_pending_step(
        mode=args.mode,
        state_path=args.state,
        service_path=args.service,
        value=args.value,
        crash_after_commit=args.crash_after_commit,
    )


if __name__ == "__main__":
    main()
