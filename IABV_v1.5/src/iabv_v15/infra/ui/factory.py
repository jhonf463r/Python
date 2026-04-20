"""Factory para ``UIScreenshotProvider``.

Regla: devolver un provider real sólo si hay probabilidad de captura
efectiva. En caso de duda, devolver ``None`` para que la tool MCP degrade
de forma explícita a ``{error: "ui_not_running"}``.

Orden de preferencia:
    1. ``QtScreenshotProvider`` si `QApplication.instance()` está viva
       (caso IABV UI corriendo en el mismo proceso).
    2. ``MssScreenshotProvider`` si python-mss está importable y hay
       display (sistema con GUI real).
    3. ``None`` (headless CI, Linux sin X, sin forma de capturar).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def build_ui_screenshot_provider() -> Any | None:
    """Devuelve el mejor provider disponible o ``None``."""

    qt = _try_qt_provider()
    if qt is not None:
        return qt
    mss_provider = _try_mss_provider()
    if mss_provider is not None:
        return mss_provider
    return None


def _try_qt_provider() -> Any | None:
    try:
        from PySide6.QtWidgets import QApplication  # type: ignore
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    try:
        from iabv_v15.infra.ui.qt_screenshot_provider import QtScreenshotProvider

        return QtScreenshotProvider()
    except Exception as exc:  # pragma: no cover
        logger.debug("QtScreenshotProvider no pudo instanciarse: %r", exc)
        return None


def _try_mss_provider() -> Any | None:
    # mss necesita display activo. En Linux CI no hay; detectamos por
    # ausencia de DISPLAY / WAYLAND_DISPLAY antes de intentar.
    if os.name == "posix":
        display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        if not display:
            return None
    try:
        import mss  # type: ignore  # noqa: F401
    except Exception:
        return None
    try:
        from iabv_v15.infra.ui.mss_screenshot_provider import MssScreenshotProvider

        return MssScreenshotProvider()
    except Exception as exc:  # pragma: no cover
        logger.debug("MssScreenshotProvider no pudo instanciarse: %r", exc)
        return None
