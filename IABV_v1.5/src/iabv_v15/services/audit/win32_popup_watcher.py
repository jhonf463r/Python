"""Win32 Popup Watcher — detects and records Win32 popup/dialog windows.

On Windows, uses ctypes to enumerate top-level windows and detect
unexpected popups (UAC, error dialogs, confirmation prompts).
On non-Windows, all methods are safe no-ops.

Records events to UIVisibilityAuditService when popups are detected.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_IS_WINDOWS = os.name == "nt"


class Win32PopupWatcher:
    """Detects Win32 popup windows and records them as visibility events."""

    def __init__(
        self,
        *,
        visibility_audit: Any | None = None,
    ) -> None:
        self._audit = visibility_audit
        self._is_windows = _IS_WINDOWS
        self._known_popups: set[str] = set()

    @property
    def is_active(self) -> bool:
        return self._audit is not None

    @property
    def is_windows(self) -> bool:
        return self._is_windows

    def check_popups(self) -> list[dict[str, Any]]:
        """Scan for Win32 popup windows. Returns list of detected popups.

        UNRESOLVED: Real Win32 enumeration requires a live Windows
        desktop with ctypes/win32gui access. This method provides the
        contract; actual enumeration is only functional on Windows.
        """
        if not self._is_windows:
            return []
        return self._scan_win32_popups()

    def record_popup(
        self,
        *,
        title: str,
        window_class: str = "",
        detail: str = "",
    ) -> dict[str, Any] | None:
        """Manually record a detected popup."""
        if self._audit is None:
            return None
        popup_key = f"{window_class}:{title}"
        self._known_popups.add(popup_key)
        return self._audit.record_event(
            category="win32_popup",
            kind="detected",
            summary=title,
            metadata={
                "window_class": window_class,
                "detail": detail,
            },
        )

    def record_popup_dismissed(
        self,
        *,
        title: str,
        window_class: str = "",
    ) -> dict[str, Any] | None:
        """Record that a popup was dismissed."""
        if self._audit is None:
            return None
        popup_key = f"{window_class}:{title}"
        self._known_popups.discard(popup_key)
        return self._audit.record_event(
            category="win32_popup",
            kind="dismissed",
            summary=title,
            metadata={"window_class": window_class},
        )

    def _scan_win32_popups(self) -> list[dict[str, Any]]:
        """Enumerate Win32 windows looking for popups.

        UNRESOLVED: Requires ctypes + live Windows desktop. The
        implementation here is the contract; full enumeration uses
        EnumWindows + IsWindowVisible + GetClassName.
        """
        detected: list[dict[str, Any]] = []
        try:
            import ctypes
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]

            def _callback(hwnd: int, _: Any) -> bool:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                class_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buf, 256)
                window_class = class_buf.value
                popup_indicators = ("#32770", "Dialog", "Alert", "Error")
                if any(ind in window_class for ind in popup_indicators):
                    popup = {"title": title, "class": window_class, "hwnd": hwnd}
                    detected.append(popup)
                    self.record_popup(
                        title=title,
                        window_class=window_class,
                    )
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(  # type: ignore[attr-defined]
                ctypes.c_bool, ctypes.c_int, ctypes.c_int
            )
            user32.EnumWindows(WNDENUMPROC(_callback), 0)
        except Exception as exc:
            logger.debug("win32_popup_watcher: scan failed: %s", exc)
        return detected

    def snapshot(self) -> dict[str, Any]:
        return {
            "active": self.is_active,
            "is_windows": self._is_windows,
            "known_popups": len(self._known_popups),
        }
