"""Account Approval Ledger — per-tool user-approved account selection.

Persists ``selected_account_by_tool.json`` so that the worker health
gate can read user-approved overrides without re-scanning.  Each tool
key maps to a single ``AccountApproval``.

The file survives restarts and is consumed by:
- ``LocalRoleRouter.worker_health_gate`` (priority override)
- ``AdaptiveTaskOrchestrator`` (decision context injection)
- ``DecisionAuditTrail`` (traceability)

Thread-safe: all reads and writes go through a single lock.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from iabv_v15.domain.models import AccountApproval

logger = logging.getLogger(__name__)


class AccountApprovalLedger:
    """Per-tool ledger of user-approved account selections."""

    _FILE_NAME = 'selected_account_by_tool.json'

    def __init__(self, data_root: str | Path = '') -> None:
        import os
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_root:
            self._data_root = Path(data_root)
        elif env_dir:
            self._data_root = Path(env_dir)
        else:
            self._data_root = Path.home() / 'IABV_v1.5' / 'data'
        self._lock = Lock()

    @property
    def _file_path(self) -> Path:
        d = self._data_root / 'evolution'
        d.mkdir(parents=True, exist_ok=True)
        return d / self._FILE_NAME

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def approve(self, approval: AccountApproval) -> AccountApproval:
        """Register a user-approved account for a tool.

        Overwrites any previous approval for the same tool.
        Other tools are NOT affected.
        """
        with self._lock:
            state = self._load()
            state[approval.tool] = approval.model_dump(mode='json')
            self._save(state)
        logger.info(
            'account_approval_ledger: tool=%s email=%s origin=%s',
            approval.tool, approval.email, approval.origin,
        )
        return approval

    def revoke(self, tool: str) -> bool:
        """Remove the approved account for a tool. Returns True if found."""
        with self._lock:
            state = self._load()
            if tool not in state:
                return False
            del state[tool]
            self._save(state)
        logger.info('account_approval_ledger: revoked tool=%s', tool)
        return True

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_approved(self, tool: str) -> AccountApproval | None:
        """Return the approved account for *tool*, or None."""
        with self._lock:
            state = self._load()
        raw = state.get(tool)
        if raw is None:
            return None
        try:
            return AccountApproval.model_validate(raw)
        except Exception:
            return None

    def get_all(self) -> dict[str, AccountApproval]:
        """Return all per-tool approvals."""
        with self._lock:
            state = self._load()
        result: dict[str, AccountApproval] = {}
        for tool, raw in state.items():
            try:
                result[tool] = AccountApproval.model_validate(raw)
            except Exception:
                continue
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        fp = self._file_path
        if not fp.exists():
            return {}
        try:
            return json.loads(fp.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _save(self, state: dict[str, Any]) -> None:
        fp = self._file_path
        try:
            fp.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.warning('account_approval_ledger: save failed: %s', exc)
