from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_execution_lab.lab01 import AgentLoop, Decision, FakeTool, ScriptedPolicy


async def execute_cases() -> dict[str, object]:
    cases: dict[str, object] = {}

    success_tool = FakeTool()
    success = await AgentLoop(max_steps=3).run(
        task="successful bounded run",
        policy=ScriptedPolicy(
            [Decision.tool("echo", value="alpha"), Decision.final("done")]
        ),
        tools={"echo": success_tool},
        run_id="lab01-success",
    )
    cases["success"] = success.to_dict()

    failure_tool = FakeTool(fail_on_calls={1})
    failure = await AgentLoop(max_steps=3).run(
        task="deterministic tool failure",
        policy=ScriptedPolicy(
            [Decision.tool("echo", value="boom"), Decision.final("unreachable")]
        ),
        tools={"echo": failure_tool},
        run_id="lab01-tool-failure",
    )
    cases["tool_failure"] = failure.to_dict()

    budget_tool = FakeTool()
    budget = await AgentLoop(max_steps=2).run(
        task="step budget exhaustion",
        policy=ScriptedPolicy(
            [
                Decision.tool("echo", value="1"),
                Decision.tool("echo", value="2"),
                Decision.final("unreachable"),
            ]
        ),
        tools={"echo": budget_tool},
        run_id="lab01-budget",
    )
    cases["budget_exhaustion"] = budget.to_dict()

    return {
        "claim": (
            "A bounded in-memory loop is sufficient for short ephemeral tasks only when "
            "failure may terminate the run and the environment is read-only/disposable."
        ),
        "cases": cases,
    }


def main() -> None:
    evidence = asyncio.run(execute_cases())
    output = ROOT / "evidence" / "experiments" / "lab01.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print("Lab 01 evidence")
    for name, payload in evidence["cases"].items():
        print(
            f"- {name}: status={payload['status']}, "
            f"steps={len(payload['steps'])}, tool_failures={payload['tool_failures']}"
        )
    print(f"machine evidence: {output}")


if __name__ == "__main__":
    main()
