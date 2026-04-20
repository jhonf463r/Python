"""Provider de screenshot basado en PySide6.QScreen.

Cumple el Protocol ``UIScreenshotProvider`` definido en
``iabv_v15.infra.mcp.audit_tools``:

    class UIScreenshotProvider(Protocol):
        def capture(self, region: str) -> bytes: ...

Estrategia:
    * Si ya hay una `QApplication` viva (caso típico: el proceso IABV
      con la UI corriendo), se usa esa instancia.
    * Si no hay `QApplication` (caso MCP server arrancado standalone),
      el provider no puede capturar sin pisarle el event loop al host,
      así que devuelve `b""` (la tool de MCP lo traduce a
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

import io
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
            app_factory: callable opcional que devuelve la `QApplication`.
                Por defecto usa `QApplication.instance()` para NO crear un
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
            from PySide6.QtGui import QGuiApplication, QPixmap  # noqa: F401 (QPixmap usado por grab)
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover - depende del entorno
            logger.debug("PySide6 no disponible: %r", exc)
            return b""

        app = self._resolve_app(QApplication, QGuiApplication)
        if app is None:
            # No hay QApplication viva; este provider no crea una porque eso
            # rompería el event loop de la UI real. Cae a `ui_not_running`.
            return b""

        region_key = (region or "").strip().lower()
        pixmap = None

        if region_key in _WINDOW_REGIONS or region_key == "":
            pixmap = self._grab_iabv_window(QApplication)

        if pixmap is None or pixmap.isNull():
            pixmap = self._grab_primary_screen(QGuiApplication)

        if pixmap is None or pixmap.isNull():
            return b""

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            return b""
        data = bytes(buffer.data())
        buffer.close()
        return data

    def _resolve_app(self, QApplication: Any, QGuiApplication: Any) -> Any:
        if self._app_factory is not None:
            try:
                return self._app_factory()
            except Exception as exc:  # pragma: no cover - defensa
                logger.debug("app_factory falló: %r", exc)
                return None
        return QApplication.instance() or QGuiApplication.instance()

    def _grab_iabv_window(self, QApplication: Any) -> Any:
        app = QApplication.instance()
        if app is None:
            return None
        windows = list(app.topLevelWidgets() or [])
        if not windows:
            return None
        target = None
        for w in windows:
            try:
                title = (w.windowTitle() or "").strip()
            except Exception:  # pragma: no cover
                title = ""
            if title and "iabv" in title.lower():
                target = w
                break
        if target is None:
            # Primera visible con tamaño razonable.
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
            return target.grab()
        except Exception as exc:  # pragma: no cover
            logger.debug("window.grab() falló: %r", exc)
            return None

    def _grab_primary_screen(self, QGuiApplication: Any) -> Any:
        try:
            screen = QGuiApplication.primaryScreen()
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
