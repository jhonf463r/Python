"""Adapters de UI (screenshot providers, etc).

Los módulos de este paquete implementan el Protocol `UIScreenshotProvider`
definido en `iabv_v15.infra.mcp.audit_tools` para que la tool MCP
`capture_ui_screenshot` pueda devolver bytes PNG reales en vez de degradar
siempre a `ui_not_running`.

Providers disponibles:
    - `QtScreenshotProvider`: usa PySide6.QtGui.QScreen.grabWindow.
    - `MssScreenshotProvider`: usa python-mss como fallback headless-ish.
    - `build_ui_screenshot_provider`: factory que elige el primero disponible.
"""

from iabv_v15.infra.ui.factory import build_ui_screenshot_provider
from iabv_v15.infra.ui.mss_screenshot_provider import MssScreenshotProvider
from iabv_v15.infra.ui.qt_screenshot_provider import QtScreenshotProvider

__all__ = [
    "MssScreenshotProvider",
    "QtScreenshotProvider",
    "build_ui_screenshot_provider",
]
