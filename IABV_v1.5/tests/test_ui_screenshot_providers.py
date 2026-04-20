"""Tests para los UIScreenshotProvider adapters (F1.1).

Los tests no requieren un display real: todos los providers se instancian
con `app_factory` o `mss_factory` inyectados, o se verifica la degradación
a `b""` cuando la dependencia no está disponible.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from iabv_v15.infra.mcp import audit_tools
from iabv_v15.infra.ui.mss_screenshot_provider import MssScreenshotProvider
from iabv_v15.infra.ui.qt_screenshot_provider import QtScreenshotProvider


# ---------------------------------------------------------------------------
# QtScreenshotProvider


def test_qt_provider_returns_empty_when_pyside6_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si PySide6 no está importable, `capture` devuelve `b""` (no raise)."""

    # Inyectamos un factory que simula la ausencia total de Qt: devolvemos
    # un app_factory que levanta ImportError.
    def boom() -> object:
        raise ImportError("PySide6 no disponible")

    provider = QtScreenshotProvider(app_factory=boom)
    assert provider.capture("control_center") == b""


def test_qt_provider_returns_empty_without_qapplication() -> None:
    """Si `QApplication.instance()` es None, degrada en silencio."""

    provider = QtScreenshotProvider(app_factory=lambda: None)
    result = provider.capture("control_center")
    assert result == b""


def test_qt_provider_captures_via_factory_with_fake_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con un factory que inyecta un QGuiApplication/QApplication falso,
    el provider llega a `screen.grabWindow(0) → pixmap.save(PNG)`.

    Usamos monkeypatch sobre los imports internos de PySide6 para no
    depender del binario real en CI.
    """

    # Construimos un universo mínimo donde QPixmap.save escribe bytes PNG
    # válidos (PNG magic header) en el buffer.
    png_magic = b"\x89PNG\r\n\x1a\n" + b"FAKE_PNG_PAYLOAD"

    class _FakeBuffer:
        def __init__(self) -> None:
            self._data = bytearray()
            self._open = False

        def open(self, mode: object) -> bool:
            self._open = True
            return True

        def close(self) -> None:
            self._open = False

        def data(self) -> bytes:
            return bytes(self._data)

        def write(self, data: bytes) -> int:  # pragma: no cover - no usado
            self._data.extend(data)
            return len(data)

    class _FakePixmap:
        def isNull(self) -> bool:
            return False

        def save(self, buffer: _FakeBuffer, fmt: str) -> bool:
            assert fmt == "PNG"
            buffer._data.extend(png_magic)
            return True

    class _FakeScreen:
        def grabWindow(self, wid: int) -> _FakePixmap:
            assert wid == 0
            return _FakePixmap()

    class _FakeQGuiApplication:
        @staticmethod
        def primaryScreen() -> _FakeScreen:
            return _FakeScreen()

        @staticmethod
        def instance() -> object:
            return object()

    class _FakeQApplication:
        @staticmethod
        def instance() -> object | None:
            return None

        @staticmethod
        def topLevelWidgets() -> list[object]:
            return []

    class _FakeIODeviceFlag:
        WriteOnly = 1

    class _FakeQIODevice:
        OpenModeFlag = _FakeIODeviceFlag

    # Inyectamos los fakes vía un módulo sintético.
    import sys
    import types as _types

    pyside6_core = _types.ModuleType("PySide6.QtCore")
    pyside6_core.QBuffer = _FakeBuffer  # type: ignore[attr-defined]
    pyside6_core.QIODevice = _FakeQIODevice  # type: ignore[attr-defined]

    pyside6_gui = _types.ModuleType("PySide6.QtGui")
    pyside6_gui.QGuiApplication = _FakeQGuiApplication  # type: ignore[attr-defined]
    pyside6_gui.QPixmap = _FakePixmap  # type: ignore[attr-defined]

    pyside6_widgets = _types.ModuleType("PySide6.QtWidgets")
    pyside6_widgets.QApplication = _FakeQApplication  # type: ignore[attr-defined]

    pyside6_pkg = _types.ModuleType("PySide6")
    pyside6_pkg.QtCore = pyside6_core  # type: ignore[attr-defined]
    pyside6_pkg.QtGui = pyside6_gui  # type: ignore[attr-defined]
    pyside6_pkg.QtWidgets = pyside6_widgets  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "PySide6", pyside6_pkg)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", pyside6_core)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", pyside6_gui)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", pyside6_widgets)

    provider = QtScreenshotProvider(app_factory=lambda: _FakeQGuiApplication())
    data = provider.capture("control_center")

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 8


# ---------------------------------------------------------------------------
# MssScreenshotProvider


def test_mss_provider_returns_empty_without_mss() -> None:
    """Sin factory y sin mss instalado, degrada a `b""`."""

    provider = MssScreenshotProvider(mss_factory=lambda: None)
    assert provider.capture("screen") == b""


def test_mss_provider_captures_via_fake_factory() -> None:
    """Con `mss_factory` inyectado, la captura produce bytes PNG."""

    class _FakeShot:
        size = (4, 4)
        # 4x4 RGB raw bytes (48 = 4*4*3)
        rgb = bytes([0xFF, 0x00, 0x00] * 16)

    class _FakeSct:
        monitors = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]

        def grab(self, monitor: object) -> _FakeShot:
            return _FakeShot()

        def __enter__(self) -> "_FakeSct":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    provider = MssScreenshotProvider(mss_factory=lambda: _FakeSct())
    data = provider.capture("screen")

    # Puede usar mss.tools.to_png o Pillow; si ninguno está, devolverá b"".
    # En CI al menos uno debería estar disponible (Pillow).
    if not data:
        pytest.skip("Ni mss.tools ni Pillow disponibles para codificar PNG")
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_mss_provider_resolves_monitor_by_index() -> None:
    """`region='monitor_2'` apunta al índice 2 en `sct.monitors`."""

    class _FakeShot:
        size = (2, 2)
        rgb = bytes([0x00, 0xFF, 0x00] * 4)

    captured: dict = {}

    class _FakeSct:
        monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]

        def grab(self, monitor: object) -> _FakeShot:
            captured["monitor"] = monitor
            return _FakeShot()

        def __enter__(self) -> "_FakeSct":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    provider = MssScreenshotProvider(mss_factory=lambda: _FakeSct())
    provider.capture("monitor_2")

    assert captured["monitor"] is _FakeSct.monitors[2]


# ---------------------------------------------------------------------------
# Integración con audit_tools.capture_ui_screenshot


def test_capture_ui_screenshot_uses_provider_output() -> None:
    """Un provider real devuelve bytes PNG → la tool los expone en base64."""

    png_payload = b"\x89PNG\r\n\x1a\n" + b"FAKE_BODY"

    class _FakeProvider:
        def capture(self, region: str) -> bytes:
            assert region == "control_center"
            return png_payload

    result = audit_tools.capture_ui_screenshot(_FakeProvider(), region="control_center")
    assert result["format"] == "png"
    assert result["size_bytes"] == len(png_payload)
    assert result["region"] == "control_center"
    assert "bytes_base64" in result


def test_capture_ui_screenshot_degrades_when_provider_returns_empty() -> None:
    """Si el provider devuelve `b""` (Qt/mss no operativos), degrada."""

    class _EmptyProvider:
        def capture(self, region: str) -> bytes:
            return b""

    result = audit_tools.capture_ui_screenshot(_EmptyProvider(), region="main")
    assert result["error"] == "ui_not_running"
    assert result["region"] == "main"
