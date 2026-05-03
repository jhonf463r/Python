"""UI Visibility Audit Service — central registry for user-visible events.

Records dialogs, toasts, FileNotFoundError, Win32 popups, splash events
and subprocess audit events so that ControlMaster and other downstream
consumers can read what the user actually sees at runtime.

Thread-safe: all mutations go through a lock.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UIVisibilityAuditService:
    """Central registry for user-visible UI events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []

    def record_event(
        self,
        *,
        category: str,
        kind: str,
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a visibility event and return the event dict."""
        event: dict[str, Any] = {
            "timestamp": _utc_now(),
            "category": category,
            "kind": kind,
            "summary": summary,
            "resolved": False,
            "metadata": dict(metadata or {}),
        }
        with self._lock:
            self._events.append(event)
        logger.debug("ui_visibility_audit: %s/%s — %s", category, kind, summary)
        return event

    def record_dialog_opened(
        self,
        *,
        dialog_type: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.record_event(
            category="dialog",
            kind=f"opened:{dialog_type}",
            summary=detail,
            metadata=metadata,
        )

    def record_dialog_closed(
        self,
        *,
        dialog_type: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = self.record_event(
            category="dialog",
            kind=f"closed:{dialog_type}",
            summary=detail,
            metadata=metadata,
        )
        # Mark matching open event as resolved
        with self._lock:
            for e in reversed(self._events):
                if (
                    e["category"] == "dialog"
                    and e["kind"] == f"opened:{dialog_type}"
                    and not e["resolved"]
                ):
                    e["resolved"] = True
                    break
        return event

    def record_file_not_found(
        self,
        *,
        path: str,
        context: str = "",
    ) -> dict[str, Any]:
        return self.record_event(
            category="file_not_found",
            kind="FileNotFoundError",
            summary=path,
            metadata={"context": context} if context else None,
        )

    # ------------------------------------------------------------------
    # Read API — consumed by ControlMaster
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a compact summary of visibility state."""
        with self._lock:
            events = list(self._events)

        by_category: dict[str, int] = {}
        unresolved = 0
        file_not_found = 0
        unexpected = 0
        for e in events:
            cat = e.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            if not e.get("resolved", False) and "closed:" not in e.get("kind", ""):
                unresolved += 1
            if cat == "file_not_found":
                file_not_found += 1
            if cat == "unexpected":
                unexpected += 1

        return {
            "total_events": len(events),
            "unresolved": unresolved,
            "file_not_found": file_not_found,
            "unexpected": unexpected,
            "by_category": by_category,
        }

    def events(self) -> list[dict[str, Any]]:
        """Return a copy of all recorded events."""
        with self._lock:
            return list(self._events)
