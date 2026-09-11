from __future__ import annotations

from pathlib import Path

import pytest

from agent_execution_lab.lab05 import (
    IsolatedWorkspaceFactory,
    SandboxPolicy,
    WorkspaceSandbox,
    trial_a,
    trial_b_broken,
    verify_result,
)


def test_shared_workspace_creates_false_positive_from_previous_trial(tmp_path: Path) -> None:
    shared = WorkspaceSandbox(tmp_path / "shared", SandboxPolicy())
    shared.root.mkdir()
    trial_a(shared)
    assert verify_result(shared) is True
    trial_b_broken(shared)
    assert verify_result(shared) is True  # false positive caused by leaked artifact


def test_isolated_workspace_removes_cross_trial_contamination(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.mkdir()
    factory = IsolatedWorkspaceFactory(template)
    first = factory.create()
    second = factory.create()
    try:
        trial_a(first)
        trial_b_broken(second)
        assert verify_result(first) is True
        assert verify_result(second) is False
    finally:
        factory.destroy(first)
        factory.destroy(second)


def test_repeated_isolated_broken_trials_are_stably_rejected(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.mkdir()
    factory = IsolatedWorkspaceFactory(template)
    outcomes = []
    for _ in range(5):
        sandbox = factory.create()
        try:
            trial_b_broken(sandbox)
            outcomes.append(verify_result(sandbox))
        finally:
            factory.destroy(sandbox)
    assert outcomes == [False] * 5


def test_policy_is_explicit_for_network_resource_and_path_boundary(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    sandbox = WorkspaceSandbox(root, SandboxPolicy(network_allowed=False, max_output_bytes=4))
    with pytest.raises(PermissionError, match="network disabled"):
        sandbox.request_network()
    with pytest.raises(RuntimeError, match="byte limit"):
        sandbox.write_output("large.txt", "12345")
    with pytest.raises(RuntimeError, match="escapes sandbox"):
        sandbox.write_output("../escape.txt", "x")
