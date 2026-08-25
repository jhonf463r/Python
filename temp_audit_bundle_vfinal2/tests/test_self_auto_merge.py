"""Tests para ``iabv_v15.infra.mcp.self_auto_merge``.

Cubre la politica pura (salvaguardas de rama, checks) y el flujo completo
de ``auto_merge`` contra un ``GitHubClient`` mockeado — nunca pega a la
GitHub API real.
"""

from __future__ import annotations

from typing import Any

import pytest

from iabv_v15.infra.mcp.self_auto_merge import (
    GitHubApiError,
    GitHubClient,
    MergeResult,
    auto_merge,
    checks_are_green,
    is_safe_branch,
    resolve_token,
)


class _FakeClient(GitHubClient):
    """``GitHubClient`` in-memory para tests. No hace HTTP."""

    def __init__(
        self,
        *,
        pr: dict[str, Any] | None = None,
        check_runs: list[dict[str, Any]] | None = None,
        merge_response: dict[str, Any] | None = None,
        fetch_pr_error: GitHubApiError | None = None,
        fetch_checks_error: GitHubApiError | None = None,
        merge_error: GitHubApiError | None = None,
    ) -> None:
        # no super().__init__: no queremos el token real
        self._pr = pr or {}
        self._check_runs = check_runs or []
        self._merge_response = merge_response or {"merged": True, "sha": "faketsha"}
        self._fetch_pr_error = fetch_pr_error
        self._fetch_checks_error = fetch_checks_error
        self._merge_error = merge_error
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def fetch_pr(self, repo: str, number: int) -> dict[str, Any]:
        self.calls.append(("fetch_pr", (repo, number)))
        if self._fetch_pr_error is not None:
            raise self._fetch_pr_error
        return dict(self._pr)

    def fetch_check_runs(self, repo: str, sha: str) -> list[dict[str, Any]]:
        self.calls.append(("fetch_check_runs", (repo, sha)))
        if self._fetch_checks_error is not None:
            raise self._fetch_checks_error
        return list(self._check_runs)

    def merge_pr(self, repo: str, number: int, method: str) -> dict[str, Any]:
        self.calls.append(("merge_pr", (repo, number, method)))
        if self._merge_error is not None:
            raise self._merge_error
        return dict(self._merge_response)


def _pr(**overrides: Any) -> dict[str, Any]:
    base = {
        "merged": False,
        "state": "open",
        "mergeable_state": "clean",
        "title": "feat: something",
        "head": {"ref": "devin/1776-x", "sha": "abc123"},
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "branch,expected",
    [
        ("devin/auto-thing", True),
        ("iabv-auto/promote", True),
        ("main", False),
        ("feature/x", False),
        ("", False),
    ],
)
def test_is_safe_branch(branch, expected):
    assert is_safe_branch(branch) is expected


def test_checks_are_green_empty_is_allowed():
    ok, reason = checks_are_green([])
    assert ok is True
    assert reason == "no-checks"


def test_checks_are_green_blocks_pending_and_failure():
    pending = [{"name": "tests", "status": "in_progress", "conclusion": None}]
    assert checks_are_green(pending)[0] is False

    failing = [{"name": "tests", "status": "completed", "conclusion": "failure"}]
    assert checks_are_green(failing)[0] is False


def test_resolve_token_prefers_iabv_scoped_name(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "scoped")
    monkeypatch.setenv("GITHUB_TOKEN", "global")
    assert resolve_token() == "scoped"


def test_resolve_token_none_when_empty(monkeypatch):
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert resolve_token() is None


def test_auto_merge_missing_token_returns_structured_result(monkeypatch):
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    result = auto_merge("foo/bar", 1)
    assert result.status == "missing_token"
    assert result.to_exit_code() == 3
    assert "token" in result.detail.lower()


def test_auto_merge_happy_path_merges_devin_branch():
    client = _FakeClient(
        pr=_pr(head={"ref": "devin/1776-test", "sha": "sha1"}),
        check_runs=[{"name": "lint", "status": "completed", "conclusion": "success"}],
        merge_response={"merged": True, "sha": "merged-sha"},
    )
    result = auto_merge("foo/bar", 42, client=client)
    assert isinstance(result, MergeResult)
    assert result.status == "merged"
    assert result.merge_sha == "merged-sha"
    assert result.branch == "devin/1776-test"
    assert result.branch_safe is True
    assert result.to_exit_code() == 0
    # Se llamaron las tres operaciones esperadas.
    assert [c[0] for c in client.calls] == ["fetch_pr", "fetch_check_runs", "merge_pr"]


def test_auto_merge_blocks_non_safe_branch_without_force():
    client = _FakeClient(pr=_pr(head={"ref": "feature/manual", "sha": "x"}))
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "blocked"
    assert result.reason == "branch_not_safe"
    assert result.to_exit_code() == 2
    # Nunca llegamos a pedir checks ni a mergear.
    assert [c[0] for c in client.calls] == ["fetch_pr"]


def test_auto_merge_blocks_on_dirty_mergeable_state():
    client = _FakeClient(pr=_pr(mergeable_state="dirty"))
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "blocked"
    assert result.reason == "mergeable_state_blocks"
    assert "dirty" in result.detail


def test_auto_merge_blocks_when_checks_failing():
    client = _FakeClient(
        pr=_pr(),
        check_runs=[{"name": "tests", "status": "completed", "conclusion": "failure"}],
    )
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "blocked"
    assert result.reason == "checks_not_green"
    assert result.check_runs_count == 1
    # Nunca llegamos a /merge.
    assert [c[0] for c in client.calls] == ["fetch_pr", "fetch_check_runs"]


def test_auto_merge_respects_already_merged_without_calling_merge_api():
    client = _FakeClient(pr=_pr(merged=True, state="closed"))
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "already_merged"
    assert result.to_exit_code() == 0
    # No pedimos checks ni mergeamos de nuevo.
    assert [c[0] for c in client.calls] == ["fetch_pr"]


def test_auto_merge_closed_pr_is_noop():
    client = _FakeClient(pr=_pr(state="closed", merged=False))
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "closed"
    assert result.to_exit_code() == 0


def test_auto_merge_force_overrides_branch_and_checks():
    client = _FakeClient(
        pr=_pr(head={"ref": "feature/manual", "sha": "s"}),
        check_runs=[{"name": "tests", "status": "completed", "conclusion": "failure"}],
        merge_response={"merged": True, "sha": "forced"},
    )
    result = auto_merge("foo/bar", 1, client=client, force=True)
    assert result.status == "merged"
    assert result.merge_sha == "forced"


def test_auto_merge_http_error_on_fetch_is_reported():
    err = GitHubApiError(500, "GET", "https://example.invalid", "boom")
    client = _FakeClient(fetch_pr_error=err)
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "http_error"
    assert result.reason == "fetch_pr_failed"
    assert result.extra.get("http_code") == 500
    assert result.to_exit_code() == 3


def test_auto_merge_http_error_on_merge_call_is_reported():
    err = GitHubApiError(422, "PUT", "https://example.invalid", "conflict")
    client = _FakeClient(
        pr=_pr(),
        check_runs=[],
        merge_error=err,
    )
    result = auto_merge("foo/bar", 1, client=client)
    assert result.status == "http_error"
    assert result.reason == "merge_api_failed"
    assert result.extra.get("http_code") == 422


def test_merge_result_to_dict_roundtrip_is_serializable():
    result = MergeResult(
        status="merged",
        pr_number=1,
        repo="foo/bar",
        branch="devin/1-x",
        title="t",
        mergeable_state="clean",
        method="squash",
        reason="ok",
        detail="ok",
        merge_sha="abc",
        checks_summary="no-checks",
        check_runs_count=0,
        branch_safe=True,
        extra={"http_code": 200},
    )
    data = result.to_dict()
    assert data["status"] == "merged"
    assert data["extra"]["http_code"] == 200
