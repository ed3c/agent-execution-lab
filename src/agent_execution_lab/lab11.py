from __future__ import annotations

import fcntl
import json
import multiprocessing as mp
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .lab07 import stable_operation_id


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return json.loads(json.dumps(default))
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _append_json_line(path: Path, lock_path: Path, payload: dict[str, Any]) -> None:
    with _exclusive_lock(lock_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class LeaseStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")

    def _read_locked(self) -> dict[str, Any]:
        return _read_json(
            self.path,
            {"next_token": 1, "step_id": None, "owner": None, "token": None, "expires_at": None},
        )

    def acquire(self, *, step_id: str, worker_id: str, now: int, ttl: int) -> int | None:
        with _exclusive_lock(self.lock_path):
            state = self._read_locked()
            active = (
                state["owner"] is not None
                and state["step_id"] == step_id
                and state["expires_at"] is not None
                and state["expires_at"] > now
            )
            if active:
                return None
            token = int(state["next_token"])
            state.update(
                {
                    "next_token": token + 1,
                    "step_id": step_id,
                    "owner": worker_id,
                    "token": token,
                    "expires_at": now + ttl,
                }
            )
            _write_json(self.path, state)
            return token

    def snapshot(self) -> dict[str, Any]:
        with _exclusive_lock(self.lock_path):
            return self._read_locked()


class FencedEffectService:
    def __init__(self, effects_path: Path, lease_store: LeaseStore) -> None:
        self.effects_path = effects_path
        self.lease_store = lease_store

    def commit(
        self,
        *,
        step_id: str,
        operation_id: str,
        worker_id: str,
        token: int,
        now: int,
    ) -> bool:
        # Lease mutation and effect authorization share one lock, so a stale owner
        # cannot pass validation while a newer token is being installed.
        with _exclusive_lock(self.lease_store.lock_path):
            lease = self.lease_store._read_locked()
            authoritative = (
                lease["step_id"] == step_id
                and lease["owner"] == worker_id
                and lease["token"] == token
                and lease["expires_at"] is not None
                and lease["expires_at"] > now
            )
            if not authoritative:
                return False

            effects = _read_json(self.effects_path, {"effects": []})
            if any(effect["operation_id"] == operation_id for effect in effects["effects"]):
                return True
            effects["effects"].append(
                {
                    "step_id": step_id,
                    "operation_id": operation_id,
                    "worker_id": worker_id,
                    "token": token,
                }
            )
            _write_json(self.effects_path, effects)
            return True

    def snapshot(self) -> dict[str, Any]:
        return _read_json(self.effects_path, {"effects": []})


def _baseline_worker(
    state_path: str,
    effects_path: str,
    effects_lock_path: str,
    barrier: Any,
    worker_id: str,
) -> None:
    state = _read_json(Path(state_path), {"status": "ready"})
    if state["status"] != "ready":
        return
    barrier.wait()
    _append_json_line(
        Path(effects_path),
        Path(effects_lock_path),
        {"worker_id": worker_id, "operation_id": stable_operation_id("run-1", "step-1")},
    )


def _leased_worker(
    lease_path: str,
    effects_path: str,
    results_path: str,
    results_lock_path: str,
    barrier: Any,
    worker_id: str,
) -> None:
    barrier.wait()
    lease = LeaseStore(Path(lease_path))
    token = lease.acquire(step_id="step-1", worker_id=worker_id, now=0, ttl=10)
    committed = False
    if token is not None:
        committed = FencedEffectService(Path(effects_path), lease).commit(
            step_id="step-1",
            operation_id=stable_operation_id("run-1", "step-1"),
            worker_id=worker_id,
            token=token,
            now=1,
        )
    _append_json_line(
        Path(results_path),
        Path(results_lock_path),
        {"worker_id": worker_id, "token": token, "committed": committed},
    )


def _spawn_pair(target: Any, args_builder: Any) -> list[int]:
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(2)
    processes = []
    for worker_id in ("worker-a", "worker-b"):
        process = ctx.Process(target=target, args=(*args_builder(barrier), worker_id))
        process.start()
        processes.append(process)
    for process in processes:
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join()
            raise RuntimeError("worker did not terminate")
    return [int(process.exitcode or 0) for process in processes]


def run_duplicate_worker_experiment(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    baseline_root = root / "baseline"
    baseline_root.mkdir(parents=True, exist_ok=True)
    _write_json(baseline_root / "state.json", {"status": "ready"})
    baseline_codes = _spawn_pair(
        _baseline_worker,
        lambda barrier: (
            str(baseline_root / "state.json"),
            str(baseline_root / "effects.jsonl"),
            str(baseline_root / "effects.lock"),
            barrier,
        ),
    )
    baseline_effects = _read_json_lines(baseline_root / "effects.jsonl")

    treatment_root = root / "treatment"
    treatment_root.mkdir(parents=True, exist_ok=True)
    treatment_codes = _spawn_pair(
        _leased_worker,
        lambda barrier: (
            str(treatment_root / "lease.json"),
            str(treatment_root / "effects.json"),
            str(treatment_root / "results.jsonl"),
            str(treatment_root / "results.lock"),
            barrier,
        ),
    )
    lease = LeaseStore(treatment_root / "lease.json")
    treatment_effects = FencedEffectService(treatment_root / "effects.json", lease).snapshot()["effects"]
    treatment_results = _read_json_lines(treatment_root / "results.jsonl")

    takeover_root = root / "takeover"
    takeover_root.mkdir(parents=True, exist_ok=True)
    takeover_lease = LeaseStore(takeover_root / "lease.json")
    token_a = takeover_lease.acquire(step_id="step-1", worker_id="worker-a", now=0, ttl=5)
    token_b = takeover_lease.acquire(step_id="step-1", worker_id="worker-b", now=6, ttl=5)
    effects = FencedEffectService(takeover_root / "effects.json", takeover_lease)
    stale_commit = effects.commit(
        step_id="step-1",
        operation_id=stable_operation_id("run-1", "step-1"),
        worker_id="worker-a",
        token=int(token_a),
        now=7,
    )
    takeover_commit = effects.commit(
        step_id="step-1",
        operation_id=stable_operation_id("run-1", "step-1"),
        worker_id="worker-b",
        token=int(token_b),
        now=7,
    )

    return {
        "baseline": {
            "return_codes": baseline_codes,
            "effects": baseline_effects,
            "physical_effects": len(baseline_effects),
        },
        "treatment": {
            "return_codes": treatment_codes,
            "results": sorted(treatment_results, key=lambda item: item["worker_id"]),
            "effects": treatment_effects,
            "physical_effects": len(treatment_effects),
            "lease": lease.snapshot(),
        },
        "takeover": {
            "token_a": token_a,
            "token_b": token_b,
            "stale_commit_accepted": stale_commit,
            "takeover_commit_accepted": takeover_commit,
            "effects": effects.snapshot()["effects"],
        },
    }
