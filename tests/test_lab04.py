from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_execution_lab.lab04 import CheckpointError, CheckpointStore, read_effect_steps


def invoke(tmp_path: Path, mode: str, crash: int | None) -> subprocess.CompletedProcess[str]:
    effects = tmp_path / f"{mode}.effects.jsonl"
    checkpoint = tmp_path / f"{mode}.checkpoint.json"
    cmd = [
        sys.executable,
        "-m",
        "agent_execution_lab.lab04",
        "--mode",
        mode,
        "--task-id",
        "task-1",
        "--total-steps",
        "5",
        "--effects",
        str(effects),
        "--checkpoint",
        str(checkpoint),
    ]
    if crash is not None:
        cmd += ["--crash-after-step", str(crash)]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(cmd, text=True, capture_output=True, env=env)


def test_baseline_hard_crash_forces_restart_and_repeats_work(tmp_path: Path) -> None:
    crashed = invoke(tmp_path, "baseline", 2)
    assert crashed.returncode == 99
    assert read_effect_steps(tmp_path / "baseline.effects.jsonl") == [0, 1, 2]

    resumed = invoke(tmp_path, "baseline", None)
    assert resumed.returncode == 0
    assert read_effect_steps(tmp_path / "baseline.effects.jsonl") == [0, 1, 2, 0, 1, 2, 3, 4]


def test_checkpoint_hard_crash_resumes_without_repeating_committed_steps(tmp_path: Path) -> None:
    crashed = invoke(tmp_path, "checkpoint", 2)
    assert crashed.returncode == 99
    assert read_effect_steps(tmp_path / "checkpoint.effects.jsonl") == [0, 1, 2]

    resumed = invoke(tmp_path, "checkpoint", None)
    assert resumed.returncode == 0
    assert read_effect_steps(tmp_path / "checkpoint.effects.jsonl") == [0, 1, 2, 3, 4]


def test_corrupt_checkpoint_is_rejected_not_silently_ignored(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"checkpoint":{"version":1,"task_id":"x","next_step":3},"checksum":"wrong"}')
    with pytest.raises(CheckpointError, match="checksum"):
        CheckpointStore(path).load()
