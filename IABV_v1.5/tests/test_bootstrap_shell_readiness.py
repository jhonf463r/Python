"""Focalized tests for the splash readiness handshake (false-ready fix).

Cubre la cadena que evita que el splash declare ready antes de que el
shell QML real este vivo:

    QML mainShellLoader.onStatusChanged == Loader.Ready
        -> mainWindowBridge.signal_shell_loader_ready()
        -> MainWindowBridge.shellLoaderReady (Qt signal)
        -> AppBootstrap._handle_shell_loader_ready()
        -> mark hito ``shell_loader_ready`` + splash.set_ready()

Y el camino fallback determinista cuando QML nunca emite la senal:

    QTimer.singleShot(IABV_SHELL_READY_FALLBACK_MS) ->
    AppBootstrap._force_splash_ready_fallback() ->
    mark hito ``shell_loader_ready_fallback`` + splash.set_ready()

Sin servicio nuevo: testeamos las funciones de bootstrap directamente
con dobles minimos.  El resto del bootstrap (servicios, ViewModels,
QGuiApplication) no se construye — solo necesitamos los atributos que
``_handle_shell_loader_ready`` y ``_force_splash_ready_fallback`` leen.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.bootstrap import AppBootstrap


class _RecordingTimeline:
    def __init__(self) -> None:
        self.marks: list[str] = []

    def mark(self, phase: str, **_kwargs: Any) -> None:
        self.marks.append(phase)


class _FakeSplash:
    def __init__(self) -> None:
        self.ready_calls = 0

    def set_ready(self) -> None:
        self.ready_calls += 1


def _make_bootstrap_stub() -> AppBootstrap:
    """Bypass __init__ — we are testing two methods in isolation."""
    stub = AppBootstrap.__new__(AppBootstrap)
    stub._timeline = _RecordingTimeline()  # type: ignore[attr-defined]
    stub._splash = _FakeSplash()  # type: ignore[attr-defined]
    return stub


def test_handle_shell_loader_ready_marks_hito_and_fires_splash() -> None:
    boot = _make_bootstrap_stub()
    boot._handle_shell_loader_ready()
    assert boot._splash.ready_calls == 1  # type: ignore[attr-defined]
    assert 'shell_loader_ready' in boot._timeline.marks  # type: ignore[attr-defined]
    assert 'splash_set_ready' in boot._timeline.marks  # type: ignore[attr-defined]


def test_handle_shell_loader_ready_is_idempotent() -> None:
    boot = _make_bootstrap_stub()
    boot._handle_shell_loader_ready()
    boot._handle_shell_loader_ready()
    boot._handle_shell_loader_ready()
    assert boot._splash.ready_calls == 1  # type: ignore[attr-defined]
    # the hito is only marked once
    assert boot._timeline.marks.count('shell_loader_ready') == 1  # type: ignore[attr-defined]


def test_handle_shell_loader_ready_tolerates_missing_splash() -> None:
    boot = _make_bootstrap_stub()
    boot._splash = None  # type: ignore[attr-defined]
    # Must not raise
    boot._handle_shell_loader_ready()
    assert 'shell_loader_ready' in boot._timeline.marks  # type: ignore[attr-defined]
    # splash_set_ready is NOT marked when splash is missing — honesty
    assert 'splash_set_ready' not in boot._timeline.marks  # type: ignore[attr-defined]


def test_force_splash_ready_fallback_marks_distinct_hito() -> None:
    """Fallback must be distinguishable in the JSONL from honest closure."""
    boot = _make_bootstrap_stub()
    boot._force_splash_ready_fallback()
    assert boot._splash.ready_calls == 1  # type: ignore[attr-defined]
    assert 'shell_loader_ready_fallback' in boot._timeline.marks  # type: ignore[attr-defined]
    assert 'splash_set_ready' in boot._timeline.marks  # type: ignore[attr-defined]
    # And NOT the honest hito — auditoria distingue
    assert 'shell_loader_ready' not in boot._timeline.marks  # type: ignore[attr-defined]


def test_fallback_is_no_op_after_honest_signal() -> None:
    """If the honest signal already fired, the fallback timer must do nothing."""
    boot = _make_bootstrap_stub()
    boot._handle_shell_loader_ready()
    initial_calls = boot._splash.ready_calls  # type: ignore[attr-defined]
    boot._force_splash_ready_fallback()
    # No double-fire on the splash
    assert boot._splash.ready_calls == initial_calls  # type: ignore[attr-defined]
    # Fallback hito is NOT marked when honest already happened
    assert 'shell_loader_ready_fallback' not in boot._timeline.marks  # type: ignore[attr-defined]


def test_honest_signal_after_fallback_is_no_op() -> None:
    """If fallback fired first, the honest signal must not double-fire splash."""
    boot = _make_bootstrap_stub()
    boot._force_splash_ready_fallback()
    initial_calls = boot._splash.ready_calls  # type: ignore[attr-defined]
    boot._handle_shell_loader_ready()
    assert boot._splash.ready_calls == initial_calls  # type: ignore[attr-defined]


# --- Bridge wiring -------------------------------------------------------- #


def test_main_window_bridge_emits_shell_loader_ready_signal() -> None:
    """signal_shell_loader_ready() must emit shellLoaderReady exactly once."""
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge

    bridge = MainWindowBridge('IABV', '/tmp/iabv_test_root')
    fired = []
    bridge.shellLoaderReady.connect(lambda: fired.append(True))
    bridge.signal_shell_loader_ready()
    bridge.signal_shell_loader_ready()
    bridge.signal_shell_loader_ready()
    assert fired == [True]
