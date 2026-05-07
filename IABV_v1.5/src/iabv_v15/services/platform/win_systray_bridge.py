"""Windows System Tray icon bridge (Fix 19a).

Wraps ``QSystemTrayIcon`` from PySide6 to show IABV in the Windows
notification area with a context menu.  The bridge is safe to construct
on non-Windows platforms — it silently no-ops when ``QSystemTrayIcon``
is unavailable or when running without a display.

The bridge exposes:
- ``show()``   — add the icon to the tray
- ``hide()``   — remove the icon from the tray
- ``set_tooltip(text)`` — update the hover tooltip
- ``show_message(title, body)`` — display a balloon/toast notification
- ``is_available`` — whether the platform supports tray icons at all
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TRAY_AVAILABLE = False
_QSystemTrayIcon: Any = None
_QIcon: Any = None
_QMenu: Any = None
_QAction: Any = None
_QApplication: Any = None

try:
    if os.name == 'nt':
        from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
        from PySide6.QtGui import QIcon, QAction
        _QSystemTrayIcon = QSystemTrayIcon
        _QIcon = QIcon
        _QMenu = QMenu
        _QAction = QAction
        _QApplication = QApplication
        _TRAY_AVAILABLE = True
except ImportError:
    pass


def _find_repo_root() -> Path:
    """Walk up from this file to find the repository root.

    The repo root is identified as the first ancestor that contains an
    ``assets/`` directory.  Falls back to ``parents[4]`` (the expected
    depth for ``src/iabv_v15/services/platform/``) if no marker is found.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / 'assets').is_dir():
            return ancestor
    return here.parents[4]


def _find_app_icon() -> str:
    """Find the best available icon file for the tray."""
    root = _find_repo_root()
    candidates = [
        root / 'assets' / 'burve.ico',
        root / 'scripts' / 'iabv.ico',
        root / 'assets' / 'burve.png',
        root / 'scripts' / 'iabv_icon.png',
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    logger.warning('systray_bridge: no icon found under %s', root)
    return ''


class WinSystrayBridge:
    """Manage the IABV system-tray icon on Windows."""

    def __init__(self, *, app_name: str = 'IABV v1.5') -> None:
        self._app_name = app_name
        self._tray: Any = None
        self._menu: Any = None
        self._visible = False
        self._on_show_window: Any = None
        self._on_quit: Any = None

    @property
    def is_available(self) -> bool:
        if not _TRAY_AVAILABLE:
            return False
        try:
            if _QApplication is None or _QApplication.instance() is None:
                return False
            return bool(_QSystemTrayIcon.isSystemTrayAvailable())
        except Exception:
            return False

    def show(
        self,
        *,
        on_show_window: Any = None,
        on_quit: Any = None,
    ) -> bool:
        """Create and show the tray icon.  Returns True on success."""
        if not self.is_available:
            logger.info('systray_bridge: not available on this platform')
            return False

        if self._tray is not None:
            return True

        self._on_show_window = on_show_window
        self._on_quit = on_quit

        try:
            icon_path = _find_app_icon()
            icon = _QIcon(icon_path) if icon_path else _QIcon()

            app = _QApplication.instance()
            self._tray = _QSystemTrayIcon(icon, parent=app)
            self._tray.setToolTip(self._app_name)

            self._menu = _QMenu()

            action_show = _QAction('Mostrar IABV', self._menu)
            if on_show_window is not None:
                action_show.triggered.connect(on_show_window)
            self._menu.addAction(action_show)

            self._menu.addSeparator()

            action_quit = _QAction('Salir', self._menu)
            if on_quit is not None:
                action_quit.triggered.connect(on_quit)
            else:
                action_quit.triggered.connect(self._default_quit)
            self._menu.addAction(action_quit)

            self._tray.setContextMenu(self._menu)
            self._tray.show()
            self._visible = True
            logger.info('systray_bridge: tray icon shown (icon=%s)', icon_path or 'default')
            return True
        except Exception:
            logger.exception('systray_bridge: failed to show tray icon')
            self._tray = None
            return False

    def hide(self) -> None:
        """Remove the tray icon."""
        if self._tray is not None:
            try:
                self._tray.hide()
            except Exception:
                pass
            self._tray = None
            self._visible = False

    def set_tooltip(self, text: str) -> None:
        if self._tray is not None:
            try:
                self._tray.setToolTip(text)
            except Exception:
                pass

    def show_message(
        self,
        title: str,
        body: str,
        *,
        icon_type: str = 'information',
        duration_ms: int = 5000,
    ) -> bool:
        """Show a balloon notification from the tray icon.

        ``icon_type`` can be 'information', 'warning', or 'critical'.
        Returns True if the message was sent successfully.
        """
        if self._tray is None:
            return False
        try:
            icon_map = {
                'information': _QSystemTrayIcon.MessageIcon.Information,
                'warning': _QSystemTrayIcon.MessageIcon.Warning,
                'critical': _QSystemTrayIcon.MessageIcon.Critical,
                'none': _QSystemTrayIcon.MessageIcon.NoIcon,
            }
            msg_icon = icon_map.get(icon_type, _QSystemTrayIcon.MessageIcon.Information)
            self._tray.showMessage(title, body, msg_icon, duration_ms)
            return True
        except Exception:
            logger.exception('systray_bridge: failed to show message')
            return False

    @property
    def visible(self) -> bool:
        return self._visible

    def snapshot(self) -> dict[str, Any]:
        """Return a machine-readable snapshot of the bridge state."""
        return {
            'available': self.is_available,
            'visible': self._visible,
            'app_name': self._app_name,
            'has_menu': self._menu is not None,
        }

    def _default_quit(self) -> None:
        try:
            app = _QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
