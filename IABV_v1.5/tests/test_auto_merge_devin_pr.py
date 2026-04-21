"""Tests para ``scripts/auto_merge_devin_pr.py``.

Cubren la parte pura (politica de ramas seguras, semantica de checks).
No hacemos HTTP real; las partes que pegan a GitHub quedan fuera.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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


def test_resolve_token_prefers_iabv(auto_merge, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "first")
    monkeypatch.setenv("IABV_GITHUB_TOKEN", "second")
    monkeypatch.setenv("GITHUB_TOKEN", "third")
    monkeypatch.setenv("GH_TOKEN", "fourth")
    assert auto_merge._resolve_token() == "first"


def test_resolve_token_falls_through_to_gh_token(auto_merge, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN_IABV", raising=False)
    monkeypatch.delenv("IABV_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "fallback")
    assert auto_merge._resolve_token() == "fallback"


def test_resolve_token_raises_when_all_empty(auto_merge, monkeypatch):
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit):
        auto_merge._resolve_token()


def test_resolve_token_ignores_whitespace_only(auto_merge, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN_IABV", "   ")
    monkeypatch.setenv("GITHUB_TOKEN", "real")
    assert auto_merge._resolve_token() == "real"
