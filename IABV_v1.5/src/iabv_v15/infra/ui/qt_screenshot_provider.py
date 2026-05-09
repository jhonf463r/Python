"""Provider de screenshot basado en PySide6.QScreen.

Cumple el Protocol ``UIScreenshotProvider`` definido en
``iabv_v15.infra.mcp.audit_tools``:

    class UIScreenshotProvider(Protocol):
        def capture(self, region: str) -> bytes: ...

Estrategia:
    * Si ya hay una ``QGuiApplication`` viva (caso típico: el proceso IABV
      con la UI corriendo), se usa esa instancia.  IABV usa
      ``QGuiApplication`` (no ``QApplication`` de QtWidgets), así que
      buscamos ventanas via ``QGuiApplication.topLevelWindows()`` en vez
      de ``QApplication.topLevelWidgets()``.
    * Si no hay ``QGuiApplication`` (caso MCP server arrancado standalone),
      el provider no puede capturar sin pisarle el event loop al host,
      así que devuelve ``b""`` (la tool de MCP lo traduce a
      ``{error: "ui_not_running"}``).

Regiones soportadas (mapeo mínimo, extensible sin romper contrato):
    * ``"control_center"`` / ``"evolution_center"`` / ``"main"`` → ventana
      top-level IABV (la primera ventana con título que contenga "IABV"
      o, si no hay, la ventana activa). Cae a la pantalla primaria si
      tampoco hay ventana.
    * ``"screen"`` / ``""`` → pantalla primaria completa.

Nunca levanta: cualquier error se traduce a bytes vacíos para que la tool
MCP degrade explícitamente en vez de crashear.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


_WINDOW_REGIONS = {
    "control_center",
    "evolution_center",
    "main",
    "window",
}
_SCREEN_REGIONS = {"screen", "primary", "desktop", ""}


class QtScreenshotProvider:
    """Captura la ventana IABV vía QScreen.grabWindow (PySide6)."""

    def __init__(self, *, app_factory: Any | None = None) -> None:
        """Args:
            app_factory: callable opcional que devuelve la ``QGuiApplication``.
                Por defecto usa ``QGuiApplication.instance()`` para NO crear un
                event loop nuevo (crear uno desde el MCP server rompería
                el proceso de UI si estuviera corriendo).
        """
        self._app_factory = app_factory

    # ------------------------------------------------------------------
    # Contrato UIScreenshotProvider

    def capture(self, region: str) -> bytes:
        try:
            return self._capture_impl(region)
        except Exception as exc:  # pragma: no cover - defensa
            logger.warning("QtScreenshotProvider.capture falló: %r", exc)
            return b""

    # ------------------------------------------------------------------
    # Implementación

    def _capture_impl(self, region: str) -> bytes:
        try:
            from PySide6.QtCore import QBuffer, QIODevice
            from PySide6.QtGui import QGuiApplication
        except Exception as exc:  # pragma: no cover - depende del entorno
            logger.debug("PySide6 no disponible: %r", exc)
            return b""

        app = self._resolve_app(QGuiApplication)
        if app is None:
            return b""

        region_key = (region or "").strip().lower()
        pixmap = None

        if region_key.startswith("hwnd:"):
            pixmap = self._grab_external_hwnd(app, region_key)
            if pixmap is None or pixmap.isNull():
                return b""

        if (pixmap is None or pixmap.isNull()) and (region_key in _WINDOW_REGIONS or region_key == ""):
            pixmap = self._grab_iabv_window(app)

        if pixmap is None or pixmap.isNull():
            pixmap = self._grab_primary_screen(app)

        if pixmap is None or pixmap.isNull():
            return b""

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            return b""
        data = bytes(buffer.data())
        buffer.close()
        return data

    def _resolve_app(self, QGuiApplication: Any) -> Any:
        if self._app_factory is not None:
            try:
                return self._app_factory()
            except Exception as exc:  # pragma: no cover - defensa
                logger.debug("app_factory falló: %r", exc)
                return None
        return QGuiApplication.instance()

    def _grab_iabv_window(self, app: Any) -> Any:
        """Captura la ventana IABV usando app.topLevelWindows().

        IABV usa ``QGuiApplication`` (no ``QApplication``), así que
        ``topLevelWidgets()`` no existe.  Usamos ``topLevelWindows()``
        que devuelve ``list[QWindow]``.  ``QWindow`` no tiene ``.grab()``
        directo, así que usamos ``QScreen.grabWindow(winId)`` para
        capturar el contenido de la ventana.

        Recibe la instancia ya resuelta (via ``_resolve_app``) para
        respetar ``app_factory`` cuando se inyecta en tests.
        """
        try:
            windows = list(app.topLevelWindows() or [])
        except Exception:
            return None
        if not windows:
            return None
        target = None
        for w in windows:
            try:
                title = (w.title() or "").strip()
            except Exception:  # pragma: no cover
                title = ""
            if title and "iabv" in title.lower():
                target = w
                break
        if target is None:
            for w in windows:
                try:
                    if w.isVisible() and w.width() > 0 and w.height() > 0:
                        target = w
                        break
                except Exception:  # pragma: no cover
                    continue
        if target is None:
            return None
        try:
            screen = target.screen()
            if screen is None:
                return None
            wid = int(target.winId())
            if not wid:
                return None
            return screen.grabWindow(wid)
        except Exception as exc:  # pragma: no cover
            logger.debug("screen.grabWindow(winId) falló: %r", exc)
            return None

    def _grab_external_hwnd(self, app: Any, region_key: str) -> Any:
        """Capture a specific native window id when WorldModel found it."""
        try:
            hwnd = int(str(region_key).split(":", 1)[1].strip() or "0")
        except Exception:
            return None
        if hwnd <= 0:
            return None
        try:
            screen = app.primaryScreen()
        except Exception:
            screen = None
        if screen is None:
            try:
                screens = list(app.screens() or [])
                screen = screens[0] if screens else None
            except Exception:
                screen = None
        if screen is None:
            return None
        try:
            return screen.grabWindow(hwnd)
        except Exception as exc:  # pragma: no cover
            logger.debug("screen.grabWindow(external hwnd=%s) fallÃ³: %r", hwnd, exc)
            return None

    def _grab_primary_screen(self, app: Any) -> Any:
        try:
            screen = app.primaryScreen()
        except Exception as exc:  # pragma: no cover
            logger.debug("primaryScreen() falló: %r", exc)
            return None
        if screen is None:
            return None
        try:
            return screen.grabWindow(0)
        except Exception as exc:  # pragma: no cover
            logger.debug("screen.grabWindow(0) falló: %r", exc)
            return None
