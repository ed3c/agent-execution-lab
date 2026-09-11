from __future__ import annotations

import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    task_id: str
    dependencies: tuple[str, ...]
    duration_seconds: float
    fail: bool = False


class ExecutionRecorder:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = 0
        self.max_concurrency = 0
        self.completed: set[str] = set()
        self.failed: set[str] = set()
        self.started: list[str] = []
        self.dependency_violations: list[str] = []

    def run(self, task: Task) -> None:
        with self.lock:
            missing = [dep for dep in task.dependencies if dep not in self.completed]
            if missing:
                self.dependency_violations.append(task.task_id)
            self.running += 1
            self.max_concurrency = max(self.max_concurrency, self.running)
            self.started.append(task.task_id)
        try:
            time.sleep(task.duration_seconds)
            if task.fail:
                raise RuntimeError(f"task failed: {task.task_id}")
            with self.lock:
                self.completed.add(task.task_id)
        except Exception:
            with self.lock:
                self.failed.add(task.task_id)
            raise
        finally:
            with self.lock:
                self.running -= 1


def fixture(*, fail_a: bool = False) -> dict[str, Task]:
    return {
        "A": Task("A", (), 0.12, fail=fail_a),
        "B": Task("B", (), 0.12),
        "C": Task("C", ("A", "B"), 0.02),
    }


def _report(started_at: float, recorder: ExecutionRecorder) -> dict[str, Any]:
    return {
        "wall_time_seconds": time.perf_counter() - started_at,
        "max_concurrency": recorder.max_concurrency,
        "completed": sorted(recorder.completed),
        "failed": sorted(recorder.failed),
        "started": recorder.started,
        "dependency_violations": recorder.dependency_violations,
    }


def execute_sequential(tasks: dict[str, Task]) -> dict[str, Any]:
    recorder = ExecutionRecorder()
    started_at = time.perf_counter()
    for task_id in ("A", "B", "C"):
        task = tasks[task_id]
        if any(dep in recorder.failed for dep in task.dependencies):
            continue
        try:
            recorder.run(task)
        except RuntimeError:
            pass
    return _report(started_at, recorder)


def execute_bounded_dag(tasks: dict[str, Task], *, max_workers: int = 2) -> dict[str, Any]:
    recorder = ExecutionRecorder()
    started_at = time.perf_counter()
    pending = set(tasks)
    running: dict[Any, str] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while pending or running:
            blocked_by_failure = {
                task_id
                for task_id in pending
                if any(dep in recorder.failed for dep in tasks[task_id].dependencies)
            }
            pending -= blocked_by_failure

            ready = sorted(
                task_id
                for task_id in pending
                if all(dep in recorder.completed for dep in tasks[task_id].dependencies)
            )
            while ready and len(running) < max_workers:
                task_id = ready.pop(0)
                pending.remove(task_id)
                future = executor.submit(recorder.run, tasks[task_id])
                running[future] = task_id

            if not running:
                break

            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in done:
                running.pop(future)
                try:
                    future.result()
                except RuntimeError:
                    pass

    return _report(started_at, recorder)


def execute_naive_parallel_all(tasks: dict[str, Task]) -> dict[str, Any]:
    """Planted broken scheduler: ignores every dependency edge."""
    recorder = ExecutionRecorder()
    started_at = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(recorder.run, tasks[task_id]) for task_id in ("A", "B", "C")]
        for future in futures:
            try:
                future.result()
            except RuntimeError:
                pass
    return _report(started_at, recorder)


def run_dag_experiment() -> dict[str, Any]:
    baseline = execute_sequential(fixture())
    treatment = execute_bounded_dag(fixture(), max_workers=2)
    broken = execute_naive_parallel_all(fixture())
    failure = execute_bounded_dag(fixture(fail_a=True), max_workers=2)
    return {
        "baseline": baseline,
        "treatment": treatment,
        "planted_broken": broken,
        "branch_failure": failure,
    }
