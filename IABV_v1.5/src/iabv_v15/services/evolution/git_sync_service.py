"""GitSyncService — auto-pull gobernado de origin/main.

Servicio minimalista que respeta AGENTS.md:
    * nunca hace git reset --hard ni git clean,
    * ``git pull --no-rebase`` cuando el working tree esta limpio,
    * consulta a ``AutonomyGovernancePolicy`` antes de aplicar cambios,
    * registra UNRESOLVED en ``ControlMasterService`` cuando bloquea.

El servicio es opt-in: todos sus colaboradores son opcionales. Si no se le
pasa policy o control_master, los side-effects correspondientes quedan en
no-op y el servicio solo reporta estado.

No crea otro cerebro ni reemplaza ``AutonomousValidationCycleService``. Su
unico trabajo es traer commits nuevos de ``origin/<branch>`` cuando sea
seguro y reportar el estado para que un humano o un servicio superior
decida el siguiente paso (reinicio, validacion sandbox, etc.).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitSyncStatus:
    """Snapshot de la relacion entre el checkout local y ``origin/<branch>``."""

    branch: str
    commits_behind: int
    commits_ahead: int
    tree_dirty: bool
    fetch_failed: bool
    fetch_error: str | None = None
    can_sync: bool = False
    block_reason: str | None = None

    @property
    def has_new_commits(self) -> bool:
        return self.commits_behind > 0


@dataclass(frozen=True)
class GitSyncResult:
    """Resultado de un intento de sincronizacion."""

    status_before: GitSyncStatus
    applied: bool
    commits_applied: int = 0
    pull_error: str | None = None
    new_head: str | None = None
    blocked_reasons: tuple[str, ...] = field(default_factory=tuple)


class GitSyncService:
    """Mantiene el checkout local alineado con ``origin/<branch>`` de forma gobernada."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        branch: str = "main",
        autonomy_governance_policy: Any | None = None,
        control_master_service: Any | None = None,
        runner: Any | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.branch = branch
        self.autonomy_governance_policy = autonomy_governance_policy
        self.control_master_service = control_master_service
        self._run = runner or self._default_runner

    def _default_runner(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> GitSyncStatus:
        """Fetches origin and computes the sync status. Never mutates tree."""

        fetch = self._run(["git", "fetch", "origin", self.branch])
        fetch_failed = fetch.returncode != 0
        fetch_error = (fetch.stderr or fetch.stdout or "").strip() if fetch_failed else None

        tree_dirty = self._is_tree_dirty()
        behind, ahead = self._ahead_behind()

        block_reason: str | None = None
        can_sync = True
        if fetch_failed:
            can_sync = False
            block_reason = f"fetch failed: {fetch_error or 'unknown'}"
        elif tree_dirty:
            can_sync = False
            block_reason = "working tree has uncommitted changes"
        elif ahead > 0 and behind == 0:
            can_sync = False
            block_reason = f"local branch has {ahead} unpushed commit(s), no remote changes"
        elif behind == 0:
            can_sync = False
            block_reason = "already up to date"

        return GitSyncStatus(
            branch=self.branch,
            commits_behind=behind,
            commits_ahead=ahead,
            tree_dirty=tree_dirty,
            fetch_failed=fetch_failed,
            fetch_error=fetch_error,
            can_sync=can_sync,
            block_reason=block_reason,
        )

    def sync(self) -> GitSyncResult:
        """Runs fast-forward-only pull when safe. Reports result structurally.

        Never runs destructive ops. On block, registers an UNRESOLVED item in
        ``ControlMasterService`` (if provided) so operators see the state in
        the next digest.
        """

        status = self.check()
        blocked: list[str] = []

        if not status.can_sync:
            reason = status.block_reason or "unknown block reason"
            blocked.append(reason)
            # "already up to date" is the healthy no-op state, not an issue that
            # needs operator attention — skip it to avoid polluting the digest.
            if not self._is_benign_noop(status):
                self._register_unresolved(status)
            return GitSyncResult(status_before=status, applied=False, blocked_reasons=tuple(blocked))

        policy_allows, policy_reason = self._policy_allows()
        if not policy_allows:
            blocked.append(f"autonomy policy blocked: {policy_reason}")
            self._register_unresolved(status, extra_reason=blocked[-1])
            return GitSyncResult(status_before=status, applied=False, blocked_reasons=tuple(blocked))

        pull = self._run(["git", "pull", "--no-rebase", "origin", self.branch])
        if pull.returncode != 0:
            pull_error = (pull.stderr or pull.stdout or "").strip()
            blocked.append(f"pull failed: {pull_error}")
            self._register_unresolved(status, extra_reason=blocked[-1])
            return GitSyncResult(
                status_before=status,
                applied=False,
                pull_error=pull_error,
                blocked_reasons=tuple(blocked),
            )

        new_head = self._current_head()
        return GitSyncResult(
            status_before=status,
            applied=True,
            commits_applied=status.commits_behind,
            new_head=new_head,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_benign_noop(status: GitSyncStatus) -> bool:
        """True when the block reason is the healthy "nothing to do" state."""

        if status.fetch_failed or status.tree_dirty:
            return False
        if status.commits_behind == 0 and status.commits_ahead == 0:
            return True
        return False

    def _is_tree_dirty(self) -> bool:
        result = self._run(["git", "status", "--porcelain"])
        if result.returncode != 0:
            # If git itself fails, treat the tree as dirty to block sync.
            return True
        return bool((result.stdout or "").strip())

    def _ahead_behind(self) -> tuple[int, int]:
        result = self._run(
            [
                "git",
                "rev-list",
                "--left-right",
                "--count",
                f"HEAD...origin/{self.branch}",
            ]
        )
        if result.returncode != 0:
            return (0, 0)
        parts = (result.stdout or "").strip().split()
        if len(parts) != 2:
            return (0, 0)
        try:
            ahead = int(parts[0])
            behind = int(parts[1])
        except ValueError:
            return (0, 0)
        return (behind, ahead)

    def _current_head(self) -> str | None:
        result = self._run(["git", "rev-parse", "HEAD"])
        if result.returncode != 0:
            return None
        return (result.stdout or "").strip() or None

    def _policy_allows(self) -> tuple[bool, str | None]:
        policy = self.autonomy_governance_policy
        if policy is None:
            return True, None
        candidates = (
            "allow_git_sync",
            "allows_git_sync",
            "allow_self_update",
        )
        for name in candidates:
            method = getattr(policy, name, None)
            if callable(method):
                try:
                    verdict = method()
                except Exception as exc:  # noqa: BLE001 - policy must not crash sync
                    return False, f"{name} raised: {exc}"
                if isinstance(verdict, tuple) and len(verdict) == 2:
                    allowed, reason = verdict
                    return bool(allowed), reason if not allowed else None
                return bool(verdict), None if verdict else f"{name}() returned falsy"
        return True, None

    def _register_unresolved(self, status: GitSyncStatus, *, extra_reason: str | None = None) -> None:
        service = self.control_master_service
        if service is None:
            return
        message_parts = [
            "git_sync blocked:",
            extra_reason or status.block_reason or "unknown reason",
        ]
        if status.commits_behind:
            message_parts.append(f"(behind={status.commits_behind})")
        if status.commits_ahead:
            message_parts.append(f"(ahead={status.commits_ahead})")
        message = " ".join(message_parts)
        mark = getattr(service, "mark_unresolved", None)
        if not callable(mark):
            return
        try:
            mark(message, evidence=[f"branch={status.branch}"])
        except Exception:  # noqa: BLE001 - never let UNRESOLVED reporting break sync
            return
