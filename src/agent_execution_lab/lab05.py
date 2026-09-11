from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxPolicy:
    network_allowed: bool = False
    max_output_bytes: int = 1024 * 1024


@dataclass
class WorkspaceSandbox:
    root: Path
    policy: SandboxPolicy

    def write_output(self, relative_path: str, content: str) -> None:
        data = content.encode("utf-8")
        if len(data) > self.policy.max_output_bytes:
            raise RuntimeError("output exceeds sandbox byte limit")
        target = (self.root / relative_path).resolve()
        if self.root.resolve() not in target.parents and target != self.root.resolve():
            raise RuntimeError("path escapes sandbox root")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def request_network(self) -> None:
        if not self.policy.network_allowed:
            raise PermissionError("network disabled by sandbox policy")


class IsolatedWorkspaceFactory:
    def __init__(self, template: Path, policy: SandboxPolicy | None = None):
        self.template = template
        self.policy = policy or SandboxPolicy()

    def create(self) -> WorkspaceSandbox:
        root = Path(tempfile.mkdtemp(prefix="agent-execution-lab05-"))
        if self.template.exists():
            shutil.copytree(self.template, root, dirs_exist_ok=True)
        return WorkspaceSandbox(root=root, policy=self.policy)

    @staticmethod
    def destroy(sandbox: WorkspaceSandbox) -> None:
        shutil.rmtree(sandbox.root, ignore_errors=True)


def trial_a(sandbox: WorkspaceSandbox) -> None:
    sandbox.write_output("result.txt", "PASS")


def trial_b_broken(sandbox: WorkspaceSandbox) -> None:
    """Intentionally broken treatment: should produce result.txt but does nothing."""
    del sandbox


def verify_result(sandbox: WorkspaceSandbox) -> bool:
    path = sandbox.root / "result.txt"
    return path.exists() and path.read_text(encoding="utf-8") == "PASS"
