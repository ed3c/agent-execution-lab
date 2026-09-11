from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .lab07 import FileExternalService, stable_operation_id


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class FileApprovalService:
    """Persistent fake human-approval service. Duplicate decisions are idempotent."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"next_id": 1, "requests": {}, "decisions": {}, "decision_writes": 0}
        return _read_json(self.path)

    def _save(self, data: dict[str, Any]) -> None:
        _atomic_json_write(self.path, data)

    def request(self, operation_id: str, *, stable_approval_id: str | None = None) -> str:
        data = self._load()
        if stable_approval_id is None:
            approval_id = f"approval-{data['next_id']}"
            data["next_id"] += 1
        else:
            approval_id = stable_approval_id
        data["requests"].setdefault(approval_id, {"operation_id": operation_id})
        self._save(data)
        return approval_id

    def decide(self, approval_id: str, decision: str) -> None:
        if decision not in {"approved", "rejected"}:
            raise ValueError(decision)
        data = self._load()
        existing = data["decisions"].get(approval_id)
        if existing is not None and existing != decision:
            raise ValueError("conflicting approval decision")
        if existing is None:
            data["decisions"][approval_id] = decision
            data["decision_writes"] += 1
        self._save(data)

    def lookup(self, approval_id: str) -> str | None:
        return self._load()["decisions"].get(approval_id)

    def snapshot(self) -> dict[str, Any]:
        return self._load()


def stable_approval_id(operation_id: str) -> str:
    return f"approval:{operation_id}"


def _load_durable_pause(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def run_worker(
    *,
    mode: str,
    approval_path: Path,
    pause_path: Path,
    effects_path: Path,
    crash_after_request: bool,
) -> None:
    operation_id = stable_operation_id("run-1", "privileged-step")
    approvals = FileApprovalService(approval_path)

    if mode == "baseline":
        # The external request survives, but its identity exists only in this process.
        approval_id = approvals.request(operation_id)
        if crash_after_request:
            os._exit(99)
        decision = approvals.lookup(approval_id)
        if decision != "approved":
            return
    elif mode == "treatment":
        pause = _load_durable_pause(pause_path)
        if pause is None:
            approval_id = stable_approval_id(operation_id)
            _atomic_json_write(
                pause_path,
                {
                    "operation_id": operation_id,
                    "approval_id": approval_id,
                    "status": "waiting",
                },
            )
            approvals.request(operation_id, stable_approval_id=approval_id)
        else:
            approval_id = pause["approval_id"]

        if crash_after_request:
            os._exit(99)

        decision = approvals.lookup(approval_id)
        if decision is None:
            return
        pause = _read_json(pause_path)
        pause["decision"] = decision
        pause["status"] = decision
        _atomic_json_write(pause_path, pause)
        if decision != "approved":
            return
    else:
        raise ValueError(mode)

    # Reuse Lab 07 operation identity so approval does not create a second effect identity.
    FileExternalService(effects_path).commit_idempotent(operation_id, "privileged-action")


def _invoke(root: Path, *, mode: str, crash: bool) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "agent_execution_lab.lab09",
        "--mode",
        mode,
        "--approvals",
        str(root / "approvals.json"),
        "--pause",
        str(root / "pause.json"),
        "--effects",
        str(root / "effects.json"),
    ]
    if crash:
        cmd.append("--crash-after-request")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    return subprocess.run(cmd, capture_output=True, text=True, env=env).returncode


def run_hitl_experiment(root: Path, *, decision: str = "approved") -> dict[str, Any]:
    report: dict[str, Any] = {}
    for mode in ("baseline", "treatment"):
        scenario = root / mode
        scenario.mkdir(parents=True, exist_ok=True)
        first = _invoke(scenario, mode=mode, crash=True)
        service = FileApprovalService(scenario / "approvals.json")
        request_ids = list(service.snapshot()["requests"])
        first_approval_id = request_ids[0]
        service.decide(first_approval_id, decision)
        # Deliver the same human decision twice; it must remain one durable decision.
        service.decide(first_approval_id, decision)
        second = _invoke(scenario, mode=mode, crash=False)

        approvals = service.snapshot()
        effects = FileExternalService(scenario / "effects.json").snapshot()
        report[mode] = {
            "return_codes": [first, second],
            "request_ids": list(approvals["requests"]),
            "decisions": approvals["decisions"],
            "decision_writes": approvals["decision_writes"],
            "physical_effects": len(effects["effects"]),
            "pause": _load_durable_pause(scenario / "pause.json"),
        }
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("baseline", "treatment"), required=True)
    parser.add_argument("--approvals", type=Path, required=True)
    parser.add_argument("--pause", type=Path, required=True)
    parser.add_argument("--effects", type=Path, required=True)
    parser.add_argument("--crash-after-request", action="store_true")
    args = parser.parse_args()
    run_worker(
        mode=args.mode,
        approval_path=args.approvals,
        pause_path=args.pause,
        effects_path=args.effects,
        crash_after_request=args.crash_after_request,
    )


if __name__ == "__main__":
    main()
