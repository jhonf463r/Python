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
        self.events: list[dict[str, Any]] = []

    def mark(self, phase: str, **kwargs: Any) -> None:
        self.marks.append(phase)
        self.events.append({'phase': phase, 'extra': kwargs})


class _FakeMainWindow:
    def __init__(self) -> None:
        self.raise_calls = 0
        self.activate_calls = 0

    def raise_(self) -> None:
        self.raise_calls += 1

    def requestActivate(self) -> None:
        self.activate_calls += 1


class _FakeSplash:
    def __init__(self) -> None:
        self.ready_calls = 0

    def set_ready(self) -> None:
        self.ready_calls += 1


def _make_bootstrap_stub(*, with_main_win: bool = False) -> AppBootstrap:
    """Bypass __init__ — we are testing handler methods in isolation."""
    stub = AppBootstrap.__new__(AppBootstrap)
    stub._timeline = _RecordingTimeline()  # type: ignore[attr-defined]
    stub._splash = _FakeSplash()  # type: ignore[attr-defined]
    if with_main_win:
        stub._main_win = _FakeMainWindow()  # type: ignore[attr-defined]
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


# --- Diagnostic instrumentation ------------------------------------------- #


def test_handle_qml_loader_event_marks_granular_hito() -> None:
    """Cada transicion de Loader QML genera un hito en el timeline.

    El nombre del hito incluye el loader y el valor de status, asi la
    auditoria distingue ``mainShellLoader_status_2`` (Loading) de
    ``mainShellLoader_status_1`` (Ready) en el JSONL.
    """
    boot = _make_bootstrap_stub()
    boot._handle_qml_loader_event('mainShellLoader', 2, True)
    boot._handle_qml_loader_event('mainShellLoader', 1, True)
    boot._handle_qml_loader_event('pageLoader', 2, True)
    marks = boot._timeline.marks  # type: ignore[attr-defined]
    assert 'qml_loader_mainShellLoader_status_2' in marks
    assert 'qml_loader_mainShellLoader_status_1' in marks
    assert 'qml_loader_pageLoader_status_2' in marks
    # Extra debe incluir loader, status, active
    events = boot._timeline.events  # type: ignore[attr-defined]
    payload = next(e for e in events if e['phase'] == 'qml_loader_mainShellLoader_status_1')
    assert payload['extra']['loader'] == 'mainShellLoader'
    assert payload['extra']['status'] == 1
    assert payload['extra']['active'] is True


def test_handle_main_qml_completed_marks_hito() -> None:
    boot = _make_bootstrap_stub()
    boot._handle_main_qml_completed()
    assert 'main_qml_completed' in boot._timeline.marks  # type: ignore[attr-defined]


def test_handle_page_loader_ready_marks_hito_and_raises_main_window() -> None:
    boot = _make_bootstrap_stub(with_main_win=True)
    boot._handle_page_loader_ready()
    assert 'page_loader_ready' in boot._timeline.marks  # type: ignore[attr-defined]
    assert boot._main_win.raise_calls == 1  # type: ignore[attr-defined]
    assert boot._main_win.activate_calls == 1  # type: ignore[attr-defined]
    assert 'main_window_raised_after_ready' in boot._timeline.marks  # type: ignore[attr-defined]


def test_handle_splash_closing_marks_hito() -> None:
    boot = _make_bootstrap_stub()
    boot._handle_splash_closing()
    assert 'splash_window_closing' in boot._timeline.marks  # type: ignore[attr-defined]


def test_shell_loader_ready_raises_main_window_after_set_ready() -> None:
    """Z-order fight: set_ready DEBE ir seguido de raise_/activate."""
    boot = _make_bootstrap_stub(with_main_win=True)
    boot._handle_shell_loader_ready()
    # Splash fue marcado ready
    assert boot._splash.ready_calls == 1  # type: ignore[attr-defined]
    # Y main_win fue subido por encima
    assert boot._main_win.raise_calls == 1  # type: ignore[attr-defined]
    assert boot._main_win.activate_calls == 1  # type: ignore[attr-defined]
    marks = boot._timeline.marks  # type: ignore[attr-defined]
    assert marks.index('shell_loader_ready') < marks.index('splash_set_ready')
    assert marks.index('splash_set_ready') < marks.index('main_window_raised_after_ready')


def test_fallback_also_raises_main_window() -> None:
    boot = _make_bootstrap_stub(with_main_win=True)
    boot._force_splash_ready_fallback()
    assert boot._main_win.raise_calls == 1  # type: ignore[attr-defined]
    marks = boot._timeline.marks  # type: ignore[attr-defined]
    assert 'shell_loader_ready_fallback' in marks
    assert 'main_window_raised_after_ready' in marks


def test_raise_main_window_tolerates_missing_main_win() -> None:
    boot = _make_bootstrap_stub()  # no main_win
    # No debe romper aun cuando _main_win nunca fue seteado
    boot._raise_main_window_now('test')
    assert 'main_window_raised_after_ready' not in boot._timeline.marks  # type: ignore[attr-defined]


# --- MainWindowBridge new slots ------------------------------------------- #


def test_main_window_bridge_emits_page_loader_ready_signal_once() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge

    bridge = MainWindowBridge('IABV', '/tmp/iabv_test_root')
    fired: list[bool] = []
    bridge.pageLoaderReady.connect(lambda: fired.append(True))
    bridge.signal_page_loader_ready()
    bridge.signal_page_loader_ready()
    assert fired == [True]


def test_main_window_bridge_emits_qml_loader_event() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge

    bridge = MainWindowBridge('IABV', '/tmp/iabv_test_root')
    received: list[tuple[str, int, bool]] = []
    bridge.qmlLoaderEvent.connect(
        lambda name, status, active: received.append((str(name), int(status), bool(active)))
    )
    bridge.signal_qml_loader_event('mainShellLoader', 2, True)
    bridge.signal_qml_loader_event('pageLoader', 1, True)
    assert received == [
        ('mainShellLoader', 2, True),
        ('pageLoader', 1, True),
    ]


def test_main_window_bridge_emits_main_qml_completed() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge

    bridge = MainWindowBridge('IABV', '/tmp/iabv_test_root')
    fired: list[bool] = []
    bridge.mainQmlCompleted.connect(lambda: fired.append(True))
    bridge.signal_main_qml_completed()
    bridge.signal_main_qml_completed()
    # Sin idempotencia aqui — onCompleted es un evento por instancia QML;
    # si QML lo invoca dos veces (recompose), bridge re-emite.
    assert fired == [True, True]


def test_main_window_bridge_emits_splash_closing() -> None:
    from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge

    bridge = MainWindowBridge('IABV', '/tmp/iabv_test_root')
    fired: list[bool] = []
    bridge.splashClosing.connect(lambda: fired.append(True))
    bridge.signal_splash_closing()
    assert fired == [True]


# --- SplashController close signal ---------------------------------------- #


def test_splash_controller_emits_closing_now_signal() -> None:
    from iabv_v15.ui.splash_controller import SplashController

    splash = SplashController(workspace_dir=None)
    fired: list[bool] = []
    splash.closingNow.connect(lambda: fired.append(True))
    splash.signal_closing()
    splash.signal_closing()
    assert fired == [True, True]


# --- Birth Readiness Gate Tests --------------------------------------------- #


class _FakeBridgeStatus:
    def __init__(self, running: bool = False, control_vm_bound: bool = False) -> None:
        self.running = running
        self.control_vm_bound = control_vm_bound


class _FakeBridge:
    def __init__(self, running: bool = False, control_vm_bound: bool = False) -> None:
        self.status = _FakeBridgeStatus(running, control_vm_bound)


class _FakeOsesSnapshot:
    def __init__(self, findings: list[Any] | None = None) -> None:
        self.findings = findings or []


class _FakeFinding:
    def __init__(self, severity: str = 'LOW', title: str = 'test') -> None:
        self.severity = severity
        self.title = title


class _FakeOses:
    def __init__(self, findings: list[Any] | None = None) -> None:
        self.current_snapshot = _FakeOsesSnapshot(findings)


def test_birth_ready_case_1_false_incomplete_readiness() -> None:
    """CASE 1: FALSE - incomplete readiness (no UI signals, no chat bridge)."""
    boot = _make_bootstrap_stub()
    # No UI signals received
    boot._shell_loader_ready_handled = False  # type: ignore[attr-defined]
    boot._page_loader_ready_received = False  # type: ignore[attr-defined]
    # No chat bridge
    boot.ui_bridge_server = None  # type: ignore[attr-defined]
    boot.control_center_viewmodel = None  # type: ignore[attr-defined]
    # No OSES findings (should not block)
    boot.operational_self_examination_service = None  # type: ignore[attr-defined]
    
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_case_2_true_legitimate_readiness() -> None:
    """CASE 2: TRUE - legitimate readiness (UI + chat bridge + no critical findings)."""
    boot = _make_bootstrap_stub()
    # UI signal received
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot._page_loader_ready_received = False  # type: ignore[attr-defined]
    # Chat bridge operational
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    # No critical OSES findings
    boot.operational_self_examination_service = _FakeOses(findings=[  # type: ignore[attr-defined]
        _FakeFinding(severity='LOW', title='minor warning'),
        _FakeFinding(severity='MEDIUM', title='info'),
    ])
    
    assert boot.is_birth_ready() is True  # type: ignore[attr-defined]


def test_birth_ready_case_3_fallback_visual_ready_but_not_birth_ready() -> None:
    """CASE 3: FALLBACK - visual ready (splash closed) but birth not ready.
    
    This tests the semantic distinction: splash may close via fallback
    even when chat bridge is not yet operational.
    """
    boot = _make_bootstrap_stub()
    # UI signal received via fallback (splash closed)
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot._page_loader_ready_received = False  # type: ignore[attr-defined]
    # Chat bridge NOT yet operational (lazy VM construction pending)
    boot.ui_bridge_server = None  # type: ignore[attr-defined]
    boot.control_center_viewmodel = None  # type: ignore[attr-defined]
    # No critical findings
    boot.operational_self_examination_service = None  # type: ignore[attr-defined]
    
    # Splash is visually ready, but system is NOT birth-ready
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_case_4_critical_finding_blocks_birth() -> None:
    """CASE 4: CRITICAL FINDING - birth not ready due to HIGH/CRITICAL OSES finding."""
    boot = _make_bootstrap_stub()
    # UI signal received
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot._page_loader_ready_received = False  # type: ignore[attr-defined]
    # Chat bridge operational
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    # CRITICAL OSES finding present
    boot.operational_self_examination_service = _FakeOses(findings=[  # type: ignore[attr-defined]
        _FakeFinding(severity='LOW', title='minor'),
        _FakeFinding(severity='CRITICAL', title='database locked'),
    ])
    
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_high_severity_also_blocks() -> None:
    """HIGH severity findings also block birth readiness."""
    boot = _make_bootstrap_stub()
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    boot.operational_self_examination_service = _FakeOses(findings=[  # type: ignore[attr-defined]
        _FakeFinding(severity='HIGH', title='startup error'),
    ])
    
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_page_loader_sufficient_for_ui_ready() -> None:
    """page_loader_ready is sufficient for UI_READY even if shell signal missing."""
    boot = _make_bootstrap_stub()
    boot._shell_loader_ready_handled = False  # type: ignore[attr-defined]
    boot._page_loader_ready_received = True  # type: ignore[attr-defined]
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    boot.operational_self_examination_service = _FakeOses(findings=[])  # type: ignore[attr-defined]
    
    assert boot.is_birth_ready() is True  # type: ignore[attr-defined]


def test_birth_ready_chat_bridge_not_running_blocks() -> None:
    """Chat bridge not running blocks birth even if UI is ready."""
    boot = _make_bootstrap_stub()
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot.ui_bridge_server = _FakeBridge(running=False, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    boot.operational_self_examination_service = _FakeOses(findings=[])  # type: ignore[attr-defined]
    
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_control_vm_not_bound_blocks() -> None:
    """Control VM not bound blocks birth even if bridge is running."""
    boot = _make_bootstrap_stub()
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=False)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    boot.operational_self_examination_service = _FakeOses(findings=[])  # type: ignore[attr-defined]
    
    assert boot.is_birth_ready() is False  # type: ignore[attr-defined]


def test_birth_ready_fail_open_on_oses_check_failure() -> None:
    """If OSES check fails, birth is not blocked (fail-open for safety)."""
    boot = _make_bootstrap_stub()
    boot._shell_loader_ready_handled = True  # type: ignore[attr-defined]
    boot.ui_bridge_server = _FakeBridge(running=True, control_vm_bound=True)  # type: ignore[attr-defined]
    boot.control_center_viewmodel = object()  # type: ignore[attr-defined]
    # OSES service exists but has no snapshot (check will fail gracefully)
    boot.operational_self_examination_service = _FakeOses(findings=None)  # type: ignore[attr-defined]
    
    assert boot.is_birth_ready() is True  # type: ignore[attr-defined]
