from __future__ import annotations

import asyncio

from agent_execution_lab.lab01 import (
    AgentLoop,
    Decision,
    FakeTool,
    RunStatus,
    ScriptedPolicy,
)


def run(coro):
    return asyncio.run(coro)


def test_successful_bounded_run_records_trace() -> None:
    tool = FakeTool()
    policy = ScriptedPolicy(
        [Decision.tool("echo", value="alpha"), Decision.final("done")]
    )

    result = run(
        AgentLoop(max_steps=3).run(
            task="success", policy=policy, tools={"echo": tool}, run_id="success"
        )
    )

    assert result.status == RunStatus.SUCCEEDED
    assert result.final_output == "done"
    assert len(result.steps) == 2
    assert result.steps[0].observation == "observed:alpha"
    assert tool.calls == 1
    assert [event.event_type for event in result.events] == [
        "run_started",
        "decision",
        "tool_started",
        "tool_succeeded",
        "decision",
        "run_succeeded",
        "run_finished",
    ]


def test_injected_tool_failure_has_no_hidden_retry() -> None:
    tool = FakeTool(fail_on_calls={1})
    policy = ScriptedPolicy(
        [Decision.tool("echo", value="boom"), Decision.final("must-not-run")]
    )

    result = run(
        AgentLoop(max_steps=3).run(
            task="fail", policy=policy, tools={"echo": tool}, run_id="failure"
        )
    )

    assert result.status == RunStatus.FAILED
    assert result.tool_failures == 1
    assert tool.calls == 1
    assert len(result.steps) == 1
    assert "injected failure" in (result.steps[0].error or "")
    assert "run_succeeded" not in [event.event_type for event in result.events]


def test_step_budget_exhaustion_is_hard_stop() -> None:
    tool = FakeTool()
    policy = ScriptedPolicy(
        [
            Decision.tool("echo", value="1"),
            Decision.tool("echo", value="2"),
            Decision.final("unreachable"),
        ]
    )

    result = run(
        AgentLoop(max_steps=2).run(
            task="budget", policy=policy, tools={"echo": tool}, run_id="budget"
        )
    )

    assert result.status == RunStatus.BUDGET_EXHAUSTED
    assert result.final_output is None
    assert len(result.steps) == 2
    assert tool.calls == 2
    assert "step_budget_exhausted" in [event.event_type for event in result.events]


def test_tool_timeout_fails_once_without_retry() -> None:
    tool = FakeTool(delay_seconds=0.05)
    policy = ScriptedPolicy([Decision.tool("echo", value="slow")])

    result = run(
        AgentLoop(max_steps=2, tool_timeout_seconds=0.005).run(
            task="timeout", policy=policy, tools={"echo": tool}, run_id="timeout"
        )
    )

    assert result.status == RunStatus.FAILED
    assert result.tool_failures == 1
    assert tool.calls == 1
    assert "tool timeout" in (result.steps[0].error or "")
