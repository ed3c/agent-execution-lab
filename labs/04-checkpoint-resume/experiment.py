from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from agent_execution_lab.lab04 import read_effect_steps


def invoke(root: Path, mode: str, crash: int | None) -> tuple[int, float]:
    cmd = [
        sys.executable,
        "-m",
        "agent_execution_lab.lab04",
        "--mode",
        mode,
        "--task-id",
        f"{mode}-task",
        "--total-steps",
        "5",
        "--effects",
        str(root / f"{mode}.effects.jsonl"),
        "--checkpoint",
        str(root / f"{mode}.checkpoint.json"),
    ]
    if crash is not None:
        cmd += ["--crash-after-step", str(crash)]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, time.perf_counter() - start


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        b1, bt1 = invoke(root, "baseline", 2)
        b2, bt2 = invoke(root, "baseline", None)
        c1, ct1 = invoke(root, "checkpoint", 2)
        c2, ct2 = invoke(root, "checkpoint", None)
        baseline_steps = read_effect_steps(root / "baseline.effects.jsonl")
        checkpoint_steps = read_effect_steps(root / "checkpoint.effects.jsonl")

    evidence = {
        "failure_point": 2,
        "baseline": {
            "return_codes": [b1, b2],
            "effects": baseline_steps,
            "repeated_steps": len(baseline_steps) - len(set(baseline_steps)),
            "wall_time_seconds": bt1 + bt2,
        },
        "checkpoint": {
            "return_codes": [c1, c2],
            "effects": checkpoint_steps,
            "repeated_steps": len(checkpoint_steps) - len(set(checkpoint_steps)),
            "wall_time_seconds": ct1 + ct2,
        },
    }
    path = ROOT / "evidence" / "experiments" / "lab04.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
