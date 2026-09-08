from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from iabv_v15.domain.models import CodexAcceptanceCriteria, CodexPendingIssue, CodexTaskSpec, CodexTestPlan
from iabv_v15.infra.mcp.server import IABVMCPServer
from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools


class _Mcp:
    def __init__(self): self.tools = {}
    def tool(self):
        def register(fn): self.tools[fn.__name__] = fn; return fn
        return register


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()


def _tools(root: Path, canonical_task_spec_fn=None):
    mcp = _Mcp()
    register_self_update_tools(
        mcp, lambda: root, lambda **_: None, lambda value: value,
        canonical_task_spec_fn,
    )
    return mcp.tools


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"; root.mkdir()
    _git(root, "init"); _git(root, "config", "user.email", "test@example.invalid"); _git(root, "config", "user.name", "IABV Test")
    (root / "sample.txt").write_text("before\n", encoding="utf-8")
    _git(root, "add", "sample.txt"); _git(root, "commit", "-m", "initial")
    return root


def _spec(*, include_unsatisfied: bool = False) -> dict:
    criteria = [
        CodexAcceptanceCriteria(description="A real commit exists", metadata={"observation": "commit_created", "expected": True}),
        CodexAcceptanceCriteria(description="Real subprocess passed", metadata={"observation": "tests_passed", "expected": True}),
    ]
    if include_unsatisfied:
        criteria.append(CodexAcceptanceCriteria(description="Push must succeed", metadata={"observation": "push_succeeded", "expected": True}))
    return CodexTaskSpec(title="real loop", goal="change sample", acceptance_criteria=criteria, test_plan=CodexTestPlan(commands=[f'"{sys.executable}" -c "print(\'1 passed\')"'])).model_dump(mode="json")


def test_registered_production_path_captures_real_commit_test_and_attribution(tmp_path):
    root = _repo(tmp_path); tools = _tools(root)
    base = _git(root, "rev-parse", "HEAD")
    assert tools["apply_text_patch"]("sample.txt", "before", "after")["status"] == "ok"
    result = tools["git_commit_and_push"]("real evidence loop", "sample.txt", False, _spec())
    assert result["status"] == "ok"
    assert result["commit_hash"] != base
    evidence = result["development_evidence"]
    payload = json.loads(Path(evidence["path"]).read_text(encoding="utf-8"))
    assert payload["execution_evidence"]["base_commit"] == base
    assert payload["execution_evidence"]["result_commit"] == result["commit_hash"]
    assert payload["execution_evidence"]["changed_files"] == ["sample.txt"]
    assert payload["test_result"]["exit_code"] == 0
    assert payload["test_result"]["passed_count"] == 1
    assert payload["audit_result"]["execution_evidence_id"] == evidence["execution_evidence_id"]
    assert payload["task_outcome"]["development_audit_result_id"] == evidence["audit_result_id"]


def test_registered_path_resolves_existing_canonical_spec_by_id(tmp_path):
    root = _repo(tmp_path)
    canonical = CodexTaskSpec.model_validate(_spec())
    issue = CodexPendingIssue(
        summary="canonical task is persisted by evolution",
        metadata={"autonomous_response_codex_task_spec": canonical.model_dump(mode="json")},
    )
    server = object.__new__(IABVMCPServer)
    server.container = SimpleNamespace(
        pending_issue_repository=SimpleNamespace(list_recent=lambda limit: [issue]),
    )
    tools = _tools(root, server._canonical_codex_task_spec)
    tools["apply_text_patch"]("sample.txt", "before", "after")
    result = tools["git_commit_and_push"](
        "canonical evidence loop", "sample.txt", False, None, canonical.codex_task_id,
    )
    payload = json.loads(Path(result["development_evidence"]["path"]).read_text(encoding="utf-8"))
    assert payload["task_spec"]["codex_task_id"] == canonical.codex_task_id
    assert payload["audit_result"]["criteria"][0]["name"] == canonical.acceptance_criteria[0].description


def test_passing_test_without_declared_observation_does_not_pass_objective(tmp_path):
    root = _repo(tmp_path); tools = _tools(root)
    tools["apply_text_patch"]("sample.txt", "before", "after")
    result = tools["git_commit_and_push"]("objective remains unproven", "sample.txt", False, _spec(include_unsatisfied=True))
    payload = json.loads(Path(result["development_evidence"]["path"]).read_text(encoding="utf-8"))
    assert payload["test_result"]["status"] == "passed"
    assert payload["audit_result"]["verdict"] == "fail"
    assert payload["task_outcome"]["status"] == "success"


def test_failed_real_test_produces_failed_development_outcome(tmp_path):
    root = _repo(tmp_path); tools = _tools(root)
    tools["apply_text_patch"]("sample.txt", "before", "after")
    failed_spec = CodexTaskSpec(
        title="failing loop", goal="change sample",
        acceptance_criteria=[CodexAcceptanceCriteria(description="Tests pass", metadata={"observation": "tests_passed", "expected": True})],
        test_plan=CodexTestPlan(commands=[f'"{sys.executable}" -c "import sys; sys.exit(7)"']),
    ).model_dump(mode="json")
    result = tools["git_commit_and_push"]("failed test evidence", "sample.txt", False, failed_spec)
    payload = json.loads(Path(result["development_evidence"]["path"]).read_text(encoding="utf-8"))
    assert payload["test_result"]["exit_code"] == 7
    assert payload["test_result"]["status"] == "failed"
    assert payload["task_outcome"]["status"] == "failed"


def test_push_failure_preserves_real_commit_and_records_partial_outcome(tmp_path):
    root = _repo(tmp_path); tools = _tools(root)
    tools["apply_text_patch"]("sample.txt", "before", "after")
    result = tools["git_commit_and_push"]("push failure evidence", "sample.txt", True, _spec(include_unsatisfied=True))
    assert result["status"] == "partial"
    assert result["commit_hash"] == _git(root, "rev-parse", "HEAD")
    payload = json.loads(Path(result["development_evidence"]["path"]).read_text(encoding="utf-8"))
    assert payload["task_outcome"]["status"] == "partial"
    assert payload["audit_result"]["verdict"] == "fail"
