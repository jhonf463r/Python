"""Subprocess Audit Wrapper — records subprocess lifecycle as visibility events.

Wraps subprocess launches (MCP, tunnel, external tools) and records
start, exit and error events to UIVisibilityAuditService.  Safe to
use on any platform; no-ops if audit service is None.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SubprocessAuditWrapper:
    """Records subprocess lifecycle events to UIVisibilityAuditService."""

    def __init__(
        self,
        *,
        visibility_audit: Any | None = None,
    ) -> None:
        self._audit = visibility_audit
        self._tracked: dict[str, dict[str, Any]] = {}

    @property
    def is_active(self) -> bool:
        return self._audit is not None

    def record_start(
        self,
        *,
        process_name: str,
        pid: int | None = None,
        command: str = "",
    ) -> None:
        """Record a subprocess start event."""
        if self._audit is None:
            return
        self._tracked[process_name] = {"pid": pid, "command": command}
        self._audit.record_event(
            category="subprocess",
            kind="start",
            summary=process_name,
            metadata={"pid": pid, "command": command},
        )

    def record_exit(
        self,
        *,
        process_name: str,
        returncode: int | None = None,
    ) -> None:
        """Record a subprocess exit event."""
        if self._audit is None:
            return
        self._tracked.pop(process_name, None)
        self._audit.record_event(
            category="subprocess",
            kind="exit",
            summary=process_name,
            metadata={"returncode": returncode},
        )

    def record_error(
        self,
        *,
        process_name: str,
        error: str = "",
    ) -> None:
        """Record a subprocess error event."""
        if self._audit is None:
            return
        self._audit.record_event(
            category="subprocess",
            kind="error",
            summary=f"{process_name}: {error}",
            metadata={"process_name": process_name, "error": error},
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "active": self.is_active,
            "tracked_count": len(self._tracked),
            "tracked_processes": list(self._tracked.keys()),
        }
