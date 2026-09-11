from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .lab01 import AgentLoop, Decision, FakeTool, RunStatus, ScriptedPolicy
from .lab02 import FakeExternalService, ToolGateway, direct_write
from .lab03 import FakeAmbiguousService, blind_retry_write, safe_write
from .lab04 import read_effect_steps
from .lab05 import (
    IsolatedWorkspaceFactory,
    SandboxPolicy,
    WorkspaceSandbox,
    trial_a,
    trial_b_broken,
    verify_result,
)


@dataclass(frozen=True)
class Comparison:
    name: str
    baseline: dict[str, Any]
    treatment: dict[str, Any]
    claim_passed: bool


@dataclass(frozen=True)
class NegativeControl:
    name: str
    rejected_by_grader: bool
    observed: dict[str, Any]


def _semantic_fingerprint(comparisons: list[Comparison], negative: NegativeControl) -> str:
    payload = {
        "comparisons": [asdict(item) for item in comparisons],
        "negative_control": asdict(negative),
    }

    def strip_time(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: strip_time(v) for k, v in value.items() if "wall_time" not in k}
        if isinstance(value, list):
            return [strip_time(v) for v in value]
        return value

    stable = json.dumps(strip_time(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode()).hexdigest()


def _lab01() -> Comparison:
    decisions = [
        Decision.tool("echo", value="1"),
        Decision.tool("echo", value="2"),
        Decision.tool("echo", value="3"),
        Decision.final("done"),
    ]
    loose_tool = FakeTool()
    loose = asyncio.run(
        AgentLoop(max_steps=100).run(
            task="runaway-boundary",
            policy=ScriptedPolicy(list(decisions)),
            tools={"echo": loose_tool},
            run_id="eval-lab01-baseline",
        )
    )
    bounded_tool = FakeTool()
    bounded = asyncio.run(
        AgentLoop(max_steps=2).run(
            task="runaway-boundary",
            policy=ScriptedPolicy(list(decisions)),
            tools={"echo": bounded_tool},
            run_id="eval-lab01-treatment",
        )
    )
    baseline = {"status": loose.status.value, "steps": len(loose.steps)}
    treatment = {"status": bounded.status.value, "steps": len(bounded.steps)}
    passed = (
        baseline["steps"] > 2
        and treatment["steps"] == 2
        and bounded.status == RunStatus.BUDGET_EXHAUSTED
    )
    return Comparison("lab01-step-budget", baseline, treatment, passed)


def _lab02() -> Comparison:
    async def execute() -> tuple[dict[str, Any], dict[str, Any]]:
        baseline_service = FakeExternalService()
        await direct_write(baseline_service, {"value": "malformed"})
        await direct_write(baseline_service, {"action": "delete", "value": "secret"})
        payload = {"action": "append", "value": "alpha"}
        await direct_write(baseline_service, payload)
        await direct_write(baseline_service, payload)

        service = FakeExternalService()
        gateway = ToolGateway(service, allowed_actions={"append"})
        rejected = 0
        for bad, key in [
            ({"value": "malformed"}, "bad"),
            ({"action": "delete", "value": "secret"}, "deny"),
        ]:
            try:
                await gateway.write(bad, idempotency_key=key)
            except (ValueError, PermissionError):
                rejected += 1
        await gateway.write(payload, idempotency_key="same")
        await gateway.write(payload, idempotency_key="same")

        return (
            {
                "physical_writes": len(baseline_service.writes),
                "invalid_or_unauthorized_committed": 2,
                "duplicate_writes": 1,
            },
            {
                "physical_writes": len(service.writes),
                "rejected_invalid_or_unauthorized": rejected,
                "invalid_or_unauthorized_committed": 0,
                "duplicate_writes": 0,
            },
        )

    baseline, treatment = asyncio.run(execute())
    passed = (
        baseline["invalid_or_unauthorized_committed"] > 0
        and baseline["duplicate_writes"] > 0
        and treatment["invalid_or_unauthorized_committed"] == 0
        and treatment["duplicate_writes"] == 0
        and treatment["physical_writes"] == 1
    )
    return Comparison("lab02-tool-gateway", baseline, treatment, passed)


def _lab03() -> Comparison:
    async def execute() -> tuple[dict[str, Any], dict[str, Any]]:
        payload = {"amount": 10}
        baseline_service = FakeAmbiguousService(["postcommit_timeout", "normal"])
        await blind_retry_write(baseline_service, payload)

        service = FakeAmbiguousService(["postcommit_timeout"])
        _, metrics = await safe_write(service, payload, idempotency_key="same-logical-op")
        return (
            {
                "service_calls": baseline_service.calls,
                "physical_writes": len(baseline_service.writes),
                "duplicate_writes": max(0, len(baseline_service.writes) - 1),
            },
            {
                "service_calls": service.calls,
                "physical_writes": len(service.writes),
                "duplicate_writes": max(0, len(service.writes) - 1),
                "reconciliations": metrics.reconciliations,
            },
        )

    baseline, treatment = asyncio.run(execute())
    passed = (
        baseline["duplicate_writes"] == 1
        and treatment["duplicate_writes"] == 0
        and treatment["physical_writes"] == 1
        and treatment["reconciliations"] == 1
    )
    return Comparison("lab03-ambiguous-write", baseline, treatment, passed)


def _invoke_lab04(root: Path, mode: str, crash_step: int | None) -> tuple[int, float]:
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "agent_execution_lab.lab04",
        "--mode",
        mode,
        "--task-id",
        f"eval-{mode}",
        "--total-steps",
        "5",
        "--effects",
        str(root / f"{mode}.effects.jsonl"),
        "--checkpoint",
        str(root / f"{mode}.checkpoint.json"),
    ]
    if crash_step is not None:
        cmd += ["--crash-after-step", str(crash_step)]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, time.perf_counter() - start


def _lab04(seed: int) -> Comparison:
    crash_step = seed % 3 + 1
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        b1, bt1 = _invoke_lab04(root, "baseline", crash_step)
        b2, bt2 = _invoke_lab04(root, "baseline", None)
        c1, ct1 = _invoke_lab04(root, "checkpoint", crash_step)
        c2, ct2 = _invoke_lab04(root, "checkpoint", None)
        bsteps = read_effect_steps(root / "baseline.effects.jsonl")
        csteps = read_effect_steps(root / "checkpoint.effects.jsonl")

    baseline = {
        "crash_step": crash_step,
        "return_codes": [b1, b2],
        "repeated_steps": len(bsteps) - len(set(bsteps)),
        "wall_time_seconds": bt1 + bt2,
    }
    treatment = {
        "crash_step": crash_step,
        "return_codes": [c1, c2],
        "repeated_steps": len(csteps) - len(set(csteps)),
        "wall_time_seconds": ct1 + ct2,
    }
    passed = (
        baseline["return_codes"] == [99, 0]
        and treatment["return_codes"] == [99, 0]
        and baseline["repeated_steps"] > 0
        and treatment["repeated_steps"] == 0
    )
    return Comparison("lab04-checkpoint-resume", baseline, treatment, passed)


def _lab05() -> Comparison:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shared = WorkspaceSandbox(root / "shared", SandboxPolicy())
        shared.root.mkdir()
        trial_a(shared)
        trial_b_broken(shared)
        baseline_false_positive = verify_result(shared)

        template = root / "template"
        template.mkdir()
        factory = IsolatedWorkspaceFactory(template)
        sandbox = factory.create()
        try:
            trial_b_broken(sandbox)
            treatment_false_positive = verify_result(sandbox)
        finally:
            factory.destroy(sandbox)

    baseline = {
        "broken_trial_passed": baseline_false_positive,
        "false_positive": baseline_false_positive,
    }
    treatment = {
        "broken_trial_passed": treatment_false_positive,
        "false_positive": treatment_false_positive,
    }
    passed = baseline["false_positive"] is True and treatment["false_positive"] is False
    return Comparison("lab05-workspace-isolation", baseline, treatment, passed)


def _negative_control_from_lab03() -> NegativeControl:
    async def execute() -> dict[str, Any]:
        service = FakeAmbiguousService(["postcommit_timeout", "normal"])
        await blind_retry_write(service, {"amount": 10})
        return {
            "physical_writes": len(service.writes),
            "duplicate_writes": max(0, len(service.writes) - 1),
        }

    observed = asyncio.run(execute())
    treatment_would_pass = (
        observed["physical_writes"] == 1 and observed["duplicate_writes"] == 0
    )
    return NegativeControl(
        name="planted-broken-ambiguous-write-treatment",
        rejected_by_grader=not treatment_would_pass,
        observed=observed,
    )


def run_suite(seed: int) -> dict[str, Any]:
    comparisons = [_lab01(), _lab02(), _lab03(), _lab04(seed), _lab05()]
    negative = _negative_control_from_lab03()
    all_claims_passed = all(item.claim_passed for item in comparisons)
    suite_passed = all_claims_passed and negative.rejected_by_grader
    fingerprint = _semantic_fingerprint(comparisons, negative)
    return {
        "seed": seed,
        "suite_passed": suite_passed,
        "comparisons": [asdict(item) for item in comparisons],
        "negative_control": asdict(negative),
        "semantic_fingerprint": fingerprint,
    }


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        f"# Agent execution eval — seed {report['seed']}",
        "",
        f"Suite: {'PASS' if report['suite_passed'] else 'FAIL'}",
        "",
    ]
    for item in report["comparisons"]:
        lines.append(f"- {'PASS' if item['claim_passed'] else 'FAIL'} — {item['name']}")
    negative = report["negative_control"]
    lines.append(
        f"- {'PASS' if negative['rejected_by_grader'] else 'FAIL'} — negative control rejected"
    )
    lines.extend(["", f"Semantic fingerprint: `{report['semantic_fingerprint']}`", ""])
    return "\n".join(lines)
