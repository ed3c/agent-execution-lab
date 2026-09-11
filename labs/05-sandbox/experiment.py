from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_execution_lab.lab05 import (
    IsolatedWorkspaceFactory,
    SandboxPolicy,
    WorkspaceSandbox,
    trial_a,
    trial_b_broken,
    verify_result,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shared = WorkspaceSandbox(root / "shared", SandboxPolicy())
        shared.root.mkdir()
        trial_a(shared)
        first = verify_result(shared)
        trial_b_broken(shared)
        false_positive = verify_result(shared)

        template = root / "template"
        template.mkdir()
        factory = IsolatedWorkspaceFactory(template)
        start = time.perf_counter()
        a = factory.create()
        b = factory.create()
        setup = time.perf_counter() - start
        try:
            trial_a(a)
            trial_b_broken(b)
            isolated_a = verify_result(a)
            isolated_b = verify_result(b)
        finally:
            factory.destroy(a)
            factory.destroy(b)

    evidence = {
        "shared_workspace": {
            "trial_a_pass": first,
            "broken_trial_b_pass": false_positive,
            "false_positive": false_positive,
        },
        "isolated_workspace": {
            "trial_a_pass": isolated_a,
            "broken_trial_b_pass": isolated_b,
            "false_positive": isolated_b,
            "two_workspace_setup_seconds": setup,
        },
        "policy": SandboxPolicy().__dict__,
    }
    path = ROOT / "evidence" / "experiments" / "lab05.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
