"""Tests para el CLI ``scripts/auto_merge_devin_pr.py``.

La logica pura (rama segura, evaluacion de checks, resolucion de token)
vive en ``iabv_v15.infra.mcp.self_auto_merge``; aca cubrimos que el CLI
sigue exponiendo las mismas funciones para compatibilidad y que el
``main`` resuelve correctamente los codigos de salida segun el resultado.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "auto_merge_devin_pr.py"


@pytest.fixture(scope="module")
def auto_merge():
    spec = importlib.util.spec_from_file_location("iabv_auto_merge", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["iabv_auto_merge"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "branch,expected",
    [
        ("devin/1776-feature", True),
        ("devin/auto-thing", True),
        ("iabv-auto/promote-foo-1234", True),
        ("main", False),
        ("feature/manual-work", False),
        ("hotfix/urgent", False),
        ("", False),
    ],
)
def test_is_safe_branch_policy(auto_merge, branch, expected):
    assert auto_merge.is_safe_branch(branch) is expected


def test_checks_are_green_empty_allows(auto_merge):
    ok, reason = auto_merge.checks_are_green([])
    assert ok is True
    assert reason == "no-checks"


def test_checks_are_green_all_success(auto_merge):
    runs = [
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "tests", "status": "completed", "conclusion": "success"},
    ]
    ok, reason = auto_merge.checks_are_green(runs)
    assert ok is True
    assert reason == "all-green"


def test_checks_are_green_accepts_skipped_and_neutral(auto_merge):
    runs = [
        {"name": "a", "status": "completed", "conclusion": "skipped"},
        {"name": "b", "status": "completed", "conclusion": "neutral"},
    ]
    ok, _ = auto_merge.checks_are_green(runs)
    assert ok is True


def test_checks_are_green_blocks_on_pending(auto_merge):
    runs = [
        {"name": "tests", "status": "in_progress", "conclusion": None},
    ]
    ok, reason = auto_merge.checks_are_green(runs)
    assert ok is False
    assert "tests" in reason


def test_checks_are_green_blocks_on_failure(auto_merge):
    runs = [
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "tests", "status": "completed", "conclusion": "failure"},
    ]
    ok, reason = auto_merge.checks_are_green(runs)
    assert ok is False
    assert "tests" in reason


def test_checks_are_green_blocks_on_completed_with_null_conclusion(auto_merge):
    runs = [
        {"name": "weird", "status": "completed", "conclusion": None},
    ]
    ok, reason = auto_merge.checks_are_green(runs)
    assert ok is False
    assert "weird" in reason


def test_resolve_token_prefers_iabv(auto_merge, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "first")
    monkeypatch.setenv("IABV_GITHUB_TOKEN", "second")
    monkeypatch.setenv("GITHUB_TOKEN", "third")
    monkeypatch.setenv("GH_TOKEN", "fourth")
    assert auto_merge.resolve_token() == "first"


def test_resolve_token_falls_through_to_gh_token(auto_merge, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN_IABV", raising=False)
    monkeypatch.delenv("IABV_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "fallback")
    assert auto_merge.resolve_token() == "fallback"


def test_resolve_token_returns_none_when_all_empty(auto_merge, monkeypatch):
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert auto_merge.resolve_token() is None


def test_resolve_token_ignores_whitespace_only(auto_merge, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "   ")
    monkeypatch.setenv("GITHUB_TOKEN", "real")
    assert auto_merge.resolve_token() == "real"


def test_main_returns_3_when_no_token(auto_merge, monkeypatch, capsys):
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    code = auto_merge.main(["123", "--repo", "foo/bar"])
    captured = capsys.readouterr()
    assert code == 3
    assert "no encontre un token" in captured.err.lower() or "no encontre" in captured.err


def test_main_invokes_auto_merge_with_args(auto_merge, monkeypatch):
    """main() delega a la funcion del modulo compartido con los args del CLI."""

    captured: dict[str, Any] = {}

    def fake_auto_merge(repo, pr_number, *, method, force, token):
        captured["repo"] = repo
        captured["pr_number"] = pr_number
        captured["method"] = method
        captured["force"] = force
        captured["token"] = token
        return auto_merge.MergeResult(
            status="merged",
            pr_number=pr_number,
            repo=repo,
            branch="devin/foo",
            title="t",
            mergeable_state="clean",
            method=method,
            reason="ok",
            detail="ok",
            merge_sha="deadbeef",
        )

    monkeypatch.setattr(auto_merge, "auto_merge", fake_auto_merge)
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "tok")

    code = auto_merge.main(["42", "--repo", "foo/bar", "--method", "squash"])
    assert code == 0
    assert captured == {
        "repo": "foo/bar",
        "pr_number": 42,
        "method": "squash",
        "force": False,
        "token": "tok",
    }
