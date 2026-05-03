"""Splash Audit Adapter — bridges SplashController events to UIVisibilityAuditService.

Listens to SplashController signals (status changes, errors, ready,
closingNow) and records them as visibility audit events.  Safe to
construct on any platform; no-ops if splash_controller is None.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SplashAuditAdapter:
    """Connects SplashController lifecycle to UIVisibilityAuditService."""

    def __init__(
        self,
        *,
        splash_controller: Any | None = None,
        visibility_audit: Any | None = None,
    ) -> None:
        self._splash = splash_controller
        self._audit = visibility_audit
        self._connected = False

        if self._splash is not None and self._audit is not None:
            self._connect()

    def _connect(self) -> None:
        """Wire signal connections from splash to audit."""
        try:
            self._splash.statusChanged.connect(self._on_status)
            self._connected = True
        except Exception:
            pass
        try:
            self._splash.hasErrorChanged.connect(self._on_error)
        except Exception:
            pass
        try:
            self._splash.readyChanged.connect(self._on_ready)
        except Exception:
            pass
        try:
            self._splash.closingNow.connect(self._on_closing)
        except Exception:
            pass
        if self._connected:
            logger.info("splash_audit_adapter: connected to splash signals")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _on_status(self) -> None:
        if self._audit is None or self._splash is None:
            return
        status = ""
        try:
            status = self._splash.status
        except Exception:
            pass
        self._audit.record_event(
            category="splash",
            kind="status",
            summary=status,
        )

    def _on_error(self) -> None:
        if self._audit is None or self._splash is None:
            return
        detail = ""
        try:
            detail = self._splash.errorDetail
        except Exception:
            pass
        self._audit.record_event(
            category="splash",
            kind="error",
            summary=detail,
        )

    def _on_ready(self) -> None:
        if self._audit is None:
            return
        self._audit.record_event(
            category="splash",
            kind="ready",
            summary="splash ready",
        )

    def _on_closing(self) -> None:
        if self._audit is None:
            return
        self._audit.record_event(
            category="splash",
            kind="closing",
            summary="splash window closing",
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "splash_available": self._splash is not None,
            "audit_available": self._audit is not None,
        }
