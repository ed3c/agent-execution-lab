from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


class DecisionKind(str, Enum):
    TOOL = "tool"
    FINAL = "final"


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    tool_name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    output: str | None = None

    @classmethod
    def tool(cls, name: str, **args: Any) -> "Decision":
        return cls(kind=DecisionKind.TOOL, tool_name=name, args=args)

    @classmethod
    def final(cls, output: str) -> "Decision":
        return cls(kind=DecisionKind.FINAL, output=output)


@dataclass(frozen=True)
class Event:
    sequence: int
    event_type: str
    step_index: int | None
    data: dict[str, Any]


@dataclass(frozen=True)
class StepRecord:
    index: int
    decision: Decision
    observation: str | None = None
    error: str | None = None


@dataclass
class RunRecord:
    run_id: str
    task: str
    status: RunStatus = RunStatus.RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    final_output: str | None = None
    tool_failures: int = 0
    started_at: float = field(default_factory=time.perf_counter)
    finished_at: float | None = None

    @property
    def wall_time_seconds(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        for step in payload["steps"]:
            step["decision"]["kind"] = step["decision"]["kind"].value
        payload["wall_time_seconds"] = self.wall_time_seconds
        return payload


class Tool(Protocol):
    async def execute(self, args: dict[str, Any]) -> str: ...


class Policy(Protocol):
    def decide(self, run: RunRecord) -> Decision: ...


@dataclass
class AgentLoop:
    max_steps: int = 8
    tool_timeout_seconds: float = 1.0

    async def run(
        self,
        *,
        task: str,
        policy: Policy,
        tools: dict[str, Tool],
        run_id: str | None = None,
    ) -> RunRecord:
        run = RunRecord(run_id=run_id or str(uuid.uuid4()), task=task)
        self._emit(run, "run_started", None, task=task)

        while run.status == RunStatus.RUNNING:
            if len(run.steps) >= self.max_steps:
                run.status = RunStatus.BUDGET_EXHAUSTED
                self._emit(run, "step_budget_exhausted", None, max_steps=self.max_steps)
                break

            decision = policy.decide(run)
            step_index = len(run.steps)
            self._emit(run, "decision", step_index, kind=decision.kind.value)

            if decision.kind == DecisionKind.FINAL:
                step = StepRecord(index=step_index, decision=decision)
                run.steps.append(step)
                run.final_output = decision.output
                run.status = RunStatus.SUCCEEDED
                self._emit(run, "run_succeeded", step_index, output=decision.output)
                break

            if decision.kind != DecisionKind.TOOL or not decision.tool_name:
                run.status = RunStatus.FAILED
                error = "invalid tool decision"
                run.steps.append(StepRecord(index=step_index, decision=decision, error=error))
                self._emit(run, "run_failed", step_index, error=error)
                break

            tool = tools.get(decision.tool_name)
            if tool is None:
                run.status = RunStatus.FAILED
                error = f"unknown tool: {decision.tool_name}"
                run.steps.append(StepRecord(index=step_index, decision=decision, error=error))
                self._emit(run, "tool_failed", step_index, error=error)
                break

            self._emit(run, "tool_started", step_index, tool=decision.tool_name)
            try:
                observation = await asyncio.wait_for(
                    tool.execute(decision.args), timeout=self.tool_timeout_seconds
                )
            except TimeoutError:
                run.tool_failures += 1
                run.status = RunStatus.FAILED
                error = f"tool timeout after {self.tool_timeout_seconds:.3f}s"
                run.steps.append(StepRecord(index=step_index, decision=decision, error=error))
                self._emit(run, "tool_failed", step_index, tool=decision.tool_name, error=error)
                break
            except Exception as exc:  # baseline intentionally has no retry
                run.tool_failures += 1
                run.status = RunStatus.FAILED
                error = f"{type(exc).__name__}: {exc}"
                run.steps.append(StepRecord(index=step_index, decision=decision, error=error))
                self._emit(run, "tool_failed", step_index, tool=decision.tool_name, error=error)
                break

            run.steps.append(
                StepRecord(index=step_index, decision=decision, observation=observation)
            )
            self._emit(
                run,
                "tool_succeeded",
                step_index,
                tool=decision.tool_name,
                observation=observation,
            )

        run.finished_at = time.perf_counter()
        self._emit(run, "run_finished", None, status=run.status.value)
        return run

    @staticmethod
    def _emit(
        run: RunRecord, event_type: str, step_index: int | None, **data: Any
    ) -> None:
        run.events.append(
            Event(
                sequence=len(run.events),
                event_type=event_type,
                step_index=step_index,
                data=data,
            )
        )


@dataclass
class ScriptedPolicy:
    """Deterministic policy for controlled execution experiments."""

    decisions: list[Decision]
    cursor: int = 0

    def decide(self, run: RunRecord) -> Decision:
        del run
        if self.cursor >= len(self.decisions):
            return Decision(kind=DecisionKind.TOOL, tool_name=None)
        decision = self.decisions[self.cursor]
        self.cursor += 1
        return decision


@dataclass
class FakeTool:
    """Deterministic tool used to physically inject success, failure, and timeout."""

    fail_on_calls: set[int] = field(default_factory=set)
    delay_seconds: float = 0.0
    calls: int = 0

    async def execute(self, args: dict[str, Any]) -> str:
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.calls in self.fail_on_calls:
            raise RuntimeError(f"injected failure on call {self.calls}")
        value = args.get("value", "ok")
        return f"observed:{value}"
