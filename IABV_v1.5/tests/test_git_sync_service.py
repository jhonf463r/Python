from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from iabv_v15.services.evolution.git_sync_service import (
    GitSyncResult,
    GitSyncService,
    GitSyncStatus,
)


# ----------------------------------------------------------------------
# Fake runner (fast, no subprocess) — covers the decision branches.
# ----------------------------------------------------------------------


class FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class FakeRunner:
    def __init__(self, recipe: dict[tuple[str, ...], FakeCompleted]) -> None:
        self.recipe = recipe
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: list[str]) -> FakeCompleted:
        key = tuple(args)
        self.calls.append(key)
        if key in self.recipe:
            return self.recipe[key]
        # sensible defaults for unstubbed commands
        if args[:2] == ["git", "status"]:
            return FakeCompleted(stdout="")
        if args[:2] == ["git", "rev-list"]:
            return FakeCompleted(stdout="0 0\n")
        if args[:2] == ["git", "rev-parse"]:
            return FakeCompleted(stdout="deadbeef\n")
        return FakeCompleted(returncode=0)


def _svc(recipe: dict[tuple[str, ...], FakeCompleted], **kwargs: Any) -> tuple[GitSyncService, FakeRunner]:
    runner = FakeRunner(recipe)
    svc = GitSyncService(repo_root="/fake", runner=runner, **kwargs)
    return svc, runner


def test_check_detects_new_commits_clean_tree() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 3\n"),
    }
    svc, _ = _svc(recipe)
    status = svc.check()
    assert isinstance(status, GitSyncStatus)
    assert status.commits_behind == 3
    assert status.commits_ahead == 0
    assert status.tree_dirty is False
    assert status.can_sync is True
    assert status.block_reason is None
    assert status.has_new_commits is True


def test_check_blocks_on_dirty_tree() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=" M foo.py\n"),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 2\n"),
    }
    svc, _ = _svc(recipe)
    status = svc.check()
    assert status.tree_dirty is True
    assert status.can_sync is False
    assert "uncommitted" in (status.block_reason or "")


def test_check_blocks_on_local_ahead() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="1 2\n"),
    }
    svc, _ = _svc(recipe)
    status = svc.check()
    assert status.commits_ahead == 1
    assert status.commits_behind == 2
    assert status.can_sync is False
    assert "unpushed" in (status.block_reason or "")


def test_check_reports_up_to_date() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 0\n"),
    }
    svc, _ = _svc(recipe)
    status = svc.check()
    assert status.can_sync is False
    assert "up to date" in (status.block_reason or "")


def test_check_reports_fetch_failure() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(stderr="network down\n", returncode=1),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 0\n"),
    }
    svc, _ = _svc(recipe)
    status = svc.check()
    assert status.fetch_failed is True
    assert status.fetch_error and "network down" in status.fetch_error
    assert status.can_sync is False


def test_sync_applies_ff_pull_when_safe() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 2\n"),
        ("git", "pull", "--ff-only", "origin", "main"): FakeCompleted(stdout="Fast-forward\n"),
        ("git", "rev-parse", "HEAD"): FakeCompleted(stdout="cafebabe\n"),
    }
    svc, runner = _svc(recipe)
    result = svc.sync()
    assert isinstance(result, GitSyncResult)
    assert result.applied is True
    assert result.commits_applied == 2
    assert result.new_head == "cafebabe"
    # pull was actually invoked
    assert ("git", "pull", "--ff-only", "origin", "main") in runner.calls


def test_sync_blocks_on_dirty_tree_and_registers_unresolved() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=" M foo.py\n"),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 1\n"),
    }
    recorded: list[tuple[str, list[str] | None]] = []

    class FakeCM:
        def mark_unresolved(self, item: str, *, evidence: list[str] | None = None) -> None:
            recorded.append((item, evidence))

    svc, runner = _svc(recipe, control_master_service=FakeCM())
    result = svc.sync()
    assert result.applied is False
    assert any("uncommitted" in reason for reason in result.blocked_reasons)
    # pull must NOT have been invoked
    assert ("git", "pull", "--ff-only", "origin", "main") not in runner.calls
    assert len(recorded) == 1
    assert "uncommitted" in recorded[0][0]


def test_sync_respects_autonomy_policy_block() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 1\n"),
    }

    class BlockingPolicy:
        def allow_git_sync(self) -> tuple[bool, str]:
            return (False, "maintenance window")

    svc, runner = _svc(recipe, autonomy_governance_policy=BlockingPolicy())
    result = svc.sync()
    assert result.applied is False
    assert any("maintenance window" in r for r in result.blocked_reasons)
    assert ("git", "pull", "--ff-only", "origin", "main") not in runner.calls


def test_sync_reports_pull_failure() -> None:
    recipe = {
        ("git", "fetch", "origin", "main"): FakeCompleted(),
        ("git", "status", "--porcelain"): FakeCompleted(stdout=""),
        ("git", "rev-list", "--left-right", "--count", "HEAD...origin/main"): FakeCompleted(stdout="0 1\n"),
        ("git", "pull", "--ff-only", "origin", "main"): FakeCompleted(stderr="not a fast-forward\n", returncode=1),
    }
    svc, _ = _svc(recipe)
    result = svc.sync()
    assert result.applied is False
    assert result.pull_error and "not a fast-forward" in result.pull_error


# ----------------------------------------------------------------------
# End-to-end against a real git repo (no network).
# ----------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def test_end_to_end_against_real_local_repos() -> None:
    root = Path("/tmp") / f"iabv_git_sync_{uuid.uuid4().hex[:8]}"
    remote = root / "remote.git"
    clone = root / "clone"
    try:
        root.mkdir(parents=True, exist_ok=True)
        _git("init", "--bare", "-b", "main", str(remote), cwd=root)
        _git("clone", str(remote), str(clone), cwd=root)
        _git("config", "user.email", "test@example.com", cwd=clone)
        _git("config", "user.name", "test", cwd=clone)
        (clone / "README.md").write_text("v1")
        _git("add", "README.md", cwd=clone)
        _git("commit", "-m", "v1", cwd=clone)
        _git("push", "-u", "origin", "main", cwd=clone)

        # second working copy that will lag behind
        lagger = root / "lagger"
        _git("clone", str(remote), str(lagger), cwd=root)
        _git("config", "user.email", "test@example.com", cwd=lagger)
        _git("config", "user.name", "test", cwd=lagger)

        # advance the upstream via the first clone
        (clone / "README.md").write_text("v2")
        _git("add", "README.md", cwd=clone)
        _git("commit", "-m", "v2", cwd=clone)
        _git("push", "origin", "main", cwd=clone)

        svc = GitSyncService(repo_root=lagger, branch="main")
        status = svc.check()
        assert status.commits_behind == 1
        assert status.commits_ahead == 0
        assert status.tree_dirty is False
        assert status.can_sync is True

        result = svc.sync()
        assert result.applied is True
        assert result.commits_applied == 1
        assert (lagger / "README.md").read_text() == "v2"

        # running check again reports up-to-date
        status_after = svc.check()
        assert status_after.commits_behind == 0
        assert status_after.can_sync is False
        assert "up to date" in (status_after.block_reason or "")
    finally:
        shutil.rmtree(root, ignore_errors=True)
