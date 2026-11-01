"""Explicit publisher for the sanitised Control Master signal.

The publisher uses a temporary clone and writes exactly one allowlisted file
to a dedicated non-default branch. It never touches the user's working checkout,
never force-pushes, and never writes to main. Git's configured credential helper
is used by Git itself; this module does not read or store credentials.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPOSITORY_URL = "https://github.com/jhonf463r/Python.git"
_SIGNAL_BRANCH = "control-master-live"
_SIGNAL_PATH = Path("IABV_v1.5/data/evolution/control_master/shared_signal.json")
_ALLOWED_TOP_LEVEL = {
    "schema_version", "project_id", "signal_status", "signal_id", "source",
    "generated_at_utc", "expires_at_utc", "freshness_window_seconds",
    "queue", "counts", "reason_codes", "transport", "content_sha256",
}
_ALLOWED_QUEUE_KEYS = {"status", "item_count", "items"}
_ALLOWED_ITEM_KEYS = {"item_id", "status", "source", "priority_label", "priority_score"}


class ControlMasterSignalPublisher:
    """Publish only a validated allowlist signal to a dedicated public branch."""

    def publish(self, signal: dict[str, Any]) -> dict[str, Any]:
        reason = self._validate_signal(signal)
        if reason:
            return {"status": "BLOCKED", "reason": reason, "branch": _SIGNAL_BRANCH}
        try:
            with tempfile.TemporaryDirectory(prefix="iabv-control-master-signal-") as tmp:
                checkout = Path(tmp) / "repo"
                heads = self._run_git(
                    ["ls-remote", "--heads", _REPOSITORY_URL, f"refs/heads/{_SIGNAL_BRANCH}"]
                )
                source_branch = _SIGNAL_BRANCH if heads.stdout.strip() else "main"
                self._run_git([
                    "clone", "--quiet", "--depth", "1", "--single-branch",
                    "--branch", source_branch, _REPOSITORY_URL, str(checkout),
                ])
                target = checkout / _SIGNAL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary_target = target.with_suffix(".json.tmp")
                temporary_target.write_text(
                    json.dumps(signal, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
                temporary_target.replace(target)

                self._run_git(["add", "--", _SIGNAL_PATH.as_posix()], cwd=checkout)
                staged = self._run_git(
                    ["diff", "--cached", "--name-only"], cwd=checkout
                ).stdout.splitlines()
                if staged != [_SIGNAL_PATH.as_posix()]:
                    return {"status": "BLOCKED", "reason": "STAGED_PATH_SET_NOT_EXACT", "branch": _SIGNAL_BRANCH}
                diff = self._run_git(
                    ["diff", "--cached", "--quiet"], cwd=checkout, allow_returncodes=(0, 1)
                )
                if diff.returncode == 0:
                    return {"status": "UNCHANGED", "branch": _SIGNAL_BRANCH, "path": _SIGNAL_PATH.as_posix()}

                self._run_git(["config", "user.name", "IABV Control Master Signal"], cwd=checkout)
                self._run_git(["config", "user.email", "iabv-signal@users.noreply.github.com"], cwd=checkout)
                self._run_git([
                    "commit", "--quiet", "-m",
                    "chore(control-master): publish sanitised live signal",
                ], cwd=checkout)
                commit_sha = self._run_git(["rev-parse", "HEAD"], cwd=checkout).stdout.strip()
                self._run_git([
                    "push", "origin", f"HEAD:refs/heads/{_SIGNAL_BRANCH}",
                ], cwd=checkout)
                return {
                    "status": "PUBLISHED",
                    "branch": _SIGNAL_BRANCH,
                    "path": _SIGNAL_PATH.as_posix(),
                    "commit_sha": commit_sha,
                    "content_sha256": signal["content_sha256"],
                    "main_modified": False,
                    "force_push": False,
                }
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            # Do not expose command output that might contain environment details.
            return {"status": "BLOCKED", "reason": "GIT_TRANSPORT_FAILED_OR_REJECTED", "branch": _SIGNAL_BRANCH}

    @staticmethod
    def _validate_signal(signal: dict[str, Any]) -> str | None:
        if not isinstance(signal, dict) or set(signal) != _ALLOWED_TOP_LEVEL:
            return "SIGNAL_SCHEMA_REJECTED"
        if signal.get("schema_version") != "iabv.control_master_signal.v1":
            return "SIGNAL_VERSION_REJECTED"
        if signal.get("project_id") != "IABV":
            return "PROJECT_SCOPE_REJECTED"
        if signal.get("signal_status") not in {"AVAILABLE", "EMPTY_QUEUE"}:
            return "SIGNAL_NOT_AVAILABLE"
        if signal.get("transport") != "READY_FOR_DEDICATED_BRANCH_PUBLICATION":
            return "TRANSPORT_STATE_REJECTED"
        supplied_hash = signal.get("content_sha256")
        unhashed = {key: value for key, value in signal.items() if key != "content_sha256"}
        canonical = json.dumps(unhashed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if not isinstance(supplied_hash, str) or hashlib.sha256(canonical.encode("utf-8")).hexdigest() != supplied_hash:
            return "SIGNAL_HASH_MISMATCH"
        try:
            generated = datetime.fromisoformat(str(signal.get("generated_at_utc")).replace("Z", "+00:00"))
            expires = datetime.fromisoformat(str(signal.get("expires_at_utc")).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if generated.tzinfo is None or expires.tzinfo is None or expires <= now:
                return "SIGNAL_EXPIRED_OR_TIME_UNVERIFIED"
            if (expires - generated).total_seconds() > 900:
                return "SIGNAL_EXPIRY_WINDOW_INVALID"
        except (TypeError, ValueError):
            return "SIGNAL_TIME_INVALID"
        source = signal.get("source")
        if not isinstance(source, dict) or set(source) != {"component", "state_id", "state_updated_at_utc"}:
            return "SOURCE_SCHEMA_REJECTED"
        if source.get("component") != "ControlMasterService" or not isinstance(source.get("state_id"), str):
            return "SOURCE_IDENTITY_REJECTED"
        if not isinstance(signal.get("counts"), dict) or not isinstance(signal.get("reason_codes"), list):
            return "SIGNAL_COUNTS_OR_REASONS_INVALID"
        queue = signal.get("queue")
        if not isinstance(queue, dict) or set(queue) != _ALLOWED_QUEUE_KEYS:
            return "QUEUE_SCHEMA_REJECTED"
        items = queue.get("items")
        if not isinstance(items, list) or any(
            not isinstance(item, dict)
            or set(item) != _ALLOWED_ITEM_KEYS
            or not isinstance(item.get("item_id"), str)
            or not isinstance(item.get("status"), str)
            or not isinstance(item.get("source"), str)
            or not isinstance(item.get("priority_label"), str)
            or isinstance(item.get("priority_score"), bool)
            or not isinstance(item.get("priority_score"), int)
            for item in items
        ):
            return "QUEUE_ITEM_SCHEMA_REJECTED"
        if queue.get("item_count") != len(items):
            return "QUEUE_COUNT_MISMATCH"
        if signal.get("signal_status") == "EMPTY_QUEUE" and (items or queue.get("status") != "EMPTY_QUEUE"):
            return "EMPTY_QUEUE_CONTRADICTION"
        if signal.get("signal_status") == "AVAILABLE" and not items:
            return "NON_EMPTY_QUEUE_CONTRADICTION"
        return None

    @staticmethod
    def _run_git(
        args: list[str],
        *,
        cwd: Path | None = None,
        allow_returncodes: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
        if result.returncode not in allow_returncodes:
            raise RuntimeError("GIT_COMMAND_FAILED")
        return result
