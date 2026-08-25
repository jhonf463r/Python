"""Windows toast notification bridge (Fix 21).

Sends native Windows toast / balloon notifications using the best
available backend:

1. **winotify** — Modern Windows 10+ Action Center toasts.  Requires
   ``pip install winotify``.
2. **QSystemTrayIcon balloon** — Falls back to the systray balloon
   notification if ``WinSystrayBridge`` is active and winotify is
   unavailable.
3. **noop** — On non-Windows or when no backend is available, all
   calls are safe no-ops.

Usage::

    bridge = WinToastBridge(app_name='IABV v1.5')
    bridge.notify('Alerta', 'Starvation detectada', icon='warning')
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

logger = logging.getLogger(__name__)

_WINOTIFY_AVAILABLE = False
try:
    if os.name == 'nt':
        from winotify import Notification as _WinotifyNotification  # type: ignore[import-untyped]
        _WINOTIFY_AVAILABLE = True
except Exception:
    pass


class WinToastBridge:
    """Windows notification bridge with winotify / balloon fallback."""

    def __init__(
        self,
        app_name: str = 'IABV v1.5',
        icon_path: str | None = None,
        systray_bridge: Any | None = None,
    ) -> None:
        self._app_name = app_name
        self._icon_path = icon_path or ''
        self._systray = systray_bridge
        self._backend: str = 'none'
        if _WINOTIFY_AVAILABLE:
            self._backend = 'winotify'
        elif self._systray is not None:
            self._backend = 'balloon'

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True if at least one notification backend is ready."""
        if _WINOTIFY_AVAILABLE:
            return True
        if self._systray is not None and getattr(self._systray, 'is_available', False):
            return True
        return False

    @property
    def backend(self) -> str:
        """Return the active backend name: 'winotify', 'balloon', or 'none'."""
        if _WINOTIFY_AVAILABLE:
            return 'winotify'
        if self._systray is not None and getattr(self._systray, 'is_available', False):
            return 'balloon'
        return 'none'

    def notify(
        self,
        title: str,
        body: str,
        *,
        icon: Literal['info', 'warning', 'error'] = 'info',
        duration_ms: int = 5000,
    ) -> bool:
        """Send a toast notification.  Returns True on success."""
        if _WINOTIFY_AVAILABLE:
            return self._notify_winotify(title, body, icon=icon)
        if self._systray is not None:
            return self._notify_balloon(title, body, icon=icon, duration_ms=duration_ms)
        return False

    def snapshot(self) -> dict[str, Any]:
        """Return diagnostic snapshot of the bridge state."""
        return {
            'available': self.is_available,
            'backend': self.backend,
            'winotify_installed': _WINOTIFY_AVAILABLE,
            'systray_available': (
                getattr(self._systray, 'is_available', False)
                if self._systray is not None
                else False
            ),
            'platform': os.name,
        }

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _notify_winotify(
        self,
        title: str,
        body: str,
        *,
        icon: str = 'info',
    ) -> bool:
        try:
            toast = _WinotifyNotification(
                app_id=self._app_name,
                title=title,
                msg=body,
            )
            if self._icon_path:
                toast.set_audio(None, loop=False)
                try:
                    toast.icon = self._icon_path
                except Exception:
                    pass
            toast.show()
            return True
        except Exception as exc:
            logger.warning('winotify notification failed: %s', exc)
            return False

    def _notify_balloon(
        self,
        title: str,
        body: str,
        *,
        icon: str = 'info',
        duration_ms: int = 5000,
    ) -> bool:
        try:
            self._systray.show_message(
                title=title,
                body=body,
                icon_type=icon if icon in ('information', 'warning', 'critical') else 'information',
                duration_ms=duration_ms,
            )
            return True
        except Exception as exc:
            logger.warning('balloon notification failed: %s', exc)
            return False
