"""Focused tests for P0 runtime slice: consulting cycle closure,
anti-freeze gating, and structured handoff messages.

Sub-objective A: timeout watchdog cleans busy state and produces actionable message.
Sub-objective B: pressure gating prevents heavy deferred work under HIGH/CRITICAL.
Sub-objective C: external tool failure handoff messages are structured and actionable.
"""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    EnvironmentRiskSignal,
    EnvironmentSelfModel,
    IssueSeverity,
)


# ── helpers ──────────────────────────────────────────────────────

def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / f'{name}_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    stop = getattr(bootstrap, 'stop', None)
    if callable(stop):
        stop()
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


def _drain_ui(viewmodel, *, timeout_seconds: float = 12.0) -> None:
    from iabv_v15.ui.qt import QGuiApplication
    app = QGuiApplication.instance()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if app is not None:
            app.processEvents()
        if not viewmodel.get_working():
            return
        time.sleep(0.05)
    if app is not None:
        app.processEvents()


# ── Sub-objective A: consulting cycle closure ────────────────────

class TestTimeoutWatchdog:
    """_schedule_worker_timeout fires taskFailed when deadline passes."""

    def test_timeout_fires_when_worker_hangs(self) -> None:
        """Watchdog emits taskFailed when done_event is never set.
        We verify the watchdog thread calls taskFailed.emit by checking
        that _apply_task_failure eventually clears _working."""
        bootstrap = _make_bootstrap('test_timeout_fires')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            done = threading.Event()

            vm._schedule_worker_timeout(
                done_event=done,
                task_name='chat',
                timeout_s=0.1,
            )
            time.sleep(0.5)
            _drain_ui(vm, timeout_seconds=3.0)

            assert vm._working is False, (
                'watchdog should have fired taskFailed which resets _working'
            )
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_timeout_fires_for_external_consultation(self) -> None:
        bootstrap = _make_bootstrap('test_timeout_external')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            done = threading.Event()

            vm._schedule_worker_timeout(
                done_event=done,
                task_name='external_consultation',
                timeout_s=0.1,
            )
            time.sleep(0.5)
            _drain_ui(vm, timeout_seconds=3.0)

            assert vm._working is False, (
                'watchdog should have fired taskFailed for external_consultation'
            )
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_no_timeout_when_worker_finishes_in_time(self) -> None:
        bootstrap = _make_bootstrap('test_no_timeout')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            done = threading.Event()

            vm._schedule_worker_timeout(
                done_event=done,
                task_name='chat',
                timeout_s=0.5,
            )
            done.set()  # worker finishes immediately
            time.sleep(0.8)

            # _working should remain True because watchdog did NOT fire
            assert vm._working is True, (
                'taskFailed should NOT fire when worker finishes in time'
            )
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_no_timeout_when_already_resolved(self) -> None:
        """If _working is already False, watchdog should not fire."""
        bootstrap = _make_bootstrap('test_no_timeout_resolved')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = False  # already resolved

            done = threading.Event()

            vm._schedule_worker_timeout(
                done_event=done,
                task_name='chat',
                timeout_s=0.1,
            )
            time.sleep(0.4)

            # _working should remain False — watchdog skips emit when already resolved
            assert vm._working is False
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_apply_task_failure_resets_working(self) -> None:
        """_apply_task_failure must always reset _working so UI escapes busy."""
        bootstrap = _make_bootstrap('test_apply_failure_resets')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            vm._apply_task_failure('chat', 'timeout: la operacion supero el tiempo maximo')

            assert vm._working is False, '_working must be False after failure'
            last = vm.get_chat_messages()[-1]['text']
            assert 'verificar' in last.lower() or 'reenviar' in last.lower()
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_external_consultation_failure_resets_working(self) -> None:
        """_apply_task_failure for external_consultation must reset _working."""
        bootstrap = _make_bootstrap('test_ext_failure_resets')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            vm._apply_task_failure('external_consultation', 'acceso denegado al sitio')

            assert vm._working is False, 'UI must not stay in consulting state'
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_timeout_message_is_actionable(self) -> None:
        """_humanize_task_failure produces actionable text for timeout."""
        bootstrap = _make_bootstrap('test_timeout_actionable')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            msg, meta = vm._humanize_task_failure(
                'chat',
                'La operacion (chat) supero el tiempo maximo de 120s. Puedes intentar de nuevo.',
            )
            assert meta == 'timeout'
            assert 'verificar' in msg.lower() or 'reenviar' in msg.lower()
        finally:
            _cleanup_bootstrap(bootstrap)


class TestTerminalDispatchStates:
    """Every dispatch state constant is present and complete."""

    def test_terminal_states_are_defined(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        states = ControlCenterViewModel._TERMINAL_DISPATCH_STATES
        required = {
            'success', 'blocked_by_permission', 'blocked_by_security_verification',
            'blocked_by_quota', 'timeout', 'cancelled',
            'failed_with_actionable_reason', 'needs_human_handoff',
        }
        assert required <= states, f'Missing terminal states: {required - states}'

    def test_humanize_returns_terminal_meta_for_permission_block(self) -> None:
        bootstrap = _make_bootstrap('test_terminal_permission')
        try:
            vm = bootstrap.control_center_viewmodel
            _, meta = vm._humanize_task_failure(
                'external_consultation',
                'acceso denegado al recurso',
            )
            assert meta == 'blocked_by_permission'
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_humanize_returns_terminal_meta_for_quota(self) -> None:
        bootstrap = _make_bootstrap('test_terminal_quota')
        try:
            vm = bootstrap.control_center_viewmodel
            _, meta = vm._humanize_task_failure('chat', 'quota exceeded')
            assert meta == 'blocked_by_quota'
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_humanize_returns_terminal_meta_for_session(self) -> None:
        bootstrap = _make_bootstrap('test_terminal_session')
        try:
            vm = bootstrap.control_center_viewmodel
            _, meta = vm._humanize_task_failure('chat', 'login required')
            assert meta == 'blocked_by_permission'
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_humanize_returns_terminal_meta_for_generic(self) -> None:
        bootstrap = _make_bootstrap('test_terminal_generic')
        try:
            vm = bootstrap.control_center_viewmodel
            _, meta = vm._humanize_task_failure('chat', 'something unexpected')
            assert meta == 'failed_with_actionable_reason'
        finally:
            _cleanup_bootstrap(bootstrap)


# ── Sub-objective B: anti-freeze gating ──────────────────────────

class TestPressureGating:
    """Heavy deferred work is skipped under HIGH/CRITICAL pressure."""

    def test_should_defer_under_high_pressure(self) -> None:
        bootstrap = _make_bootstrap('test_defer_high')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None

            env_service = getattr(
                vm.adaptive_orchestrator.context_assembler,
                'environment_self_awareness_service',
                None,
            )
            if env_service is None:
                assert vm._should_defer_heavy_work() is False
                return

            env_service._current_model = EnvironmentSelfModel(
                cpu_cores=4,
                ram_total_gb=8.0,
                ram_available_gb=0.5,
                disk_total_gb=100.0,
                disk_available_gb=10.0,
                gpu_available=False,
                risk_signals=[
                    EnvironmentRiskSignal(
                        kind='ram_pressure',
                        severity=IssueSeverity.HIGH,
                        summary='RAM below threshold',
                    ),
                ],
            )
            assert vm._should_defer_heavy_work() is True
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_should_defer_under_critical_pressure(self) -> None:
        bootstrap = _make_bootstrap('test_defer_critical')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None

            env_service = getattr(
                vm.adaptive_orchestrator.context_assembler,
                'environment_self_awareness_service',
                None,
            )
            if env_service is None:
                assert vm._should_defer_heavy_work() is False
                return

            env_service._current_model = EnvironmentSelfModel(
                cpu_cores=4,
                ram_total_gb=8.0,
                ram_available_gb=0.2,
                disk_total_gb=100.0,
                disk_available_gb=2.0,
                gpu_available=False,
                risk_signals=[
                    EnvironmentRiskSignal(
                        kind='ram_pressure',
                        severity=IssueSeverity.CRITICAL,
                        summary='RAM critically low',
                    ),
                ],
            )
            assert vm._should_defer_heavy_work() is True
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_no_defer_under_normal_pressure(self) -> None:
        bootstrap = _make_bootstrap('test_no_defer_normal')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            assert vm._should_defer_heavy_work() is False
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_apply_task_failure_skips_heavy_work_under_pressure(self) -> None:
        """Under pressure, _apply_task_failure must NOT call heavy methods."""
        bootstrap = _make_bootstrap('test_result_skips_heavy')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None

            calls = {'evolution': 0, 'dev_packet': 0, 'autonomy_dock': 0}

            def _count_evolution() -> None:
                calls['evolution'] += 1

            def _count_dev_packet() -> None:
                calls['dev_packet'] += 1

            def _count_autonomy_dock() -> None:
                calls['autonomy_dock'] += 1

            vm._update_evolution_snapshot = _count_evolution  # type: ignore[method-assign]
            vm._refresh_development_packet = _count_dev_packet  # type: ignore[method-assign]
            vm._refresh_autonomy_dock = _count_autonomy_dock  # type: ignore[method-assign]

            # Force pressure
            vm._should_defer_heavy_work = lambda: True  # type: ignore[method-assign]

            vm._working = True
            vm._apply_task_failure('chat', 'some error')

            assert calls['evolution'] == 0, 'evolution snapshot should be skipped under pressure'
            assert calls['dev_packet'] == 0, 'dev packet refresh should be skipped under pressure'
            assert calls['autonomy_dock'] == 0, 'autonomy dock refresh should be skipped under pressure'
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_apply_task_failure_runs_heavy_work_without_pressure(self) -> None:
        """Without pressure, _apply_task_failure runs heavy methods normally."""
        bootstrap = _make_bootstrap('test_result_runs_heavy')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None

            calls = {'evolution': 0}

            def _count_evolution() -> None:
                calls['evolution'] += 1

            vm._update_evolution_snapshot = _count_evolution  # type: ignore[method-assign]

            # No pressure
            vm._should_defer_heavy_work = lambda: False  # type: ignore[method-assign]

            vm._working = True
            vm._apply_task_failure('chat', 'some error')

            assert calls['evolution'] >= 1, 'evolution snapshot should run without pressure'
        finally:
            _cleanup_bootstrap(bootstrap)


# ── Sub-objective C: handoff visual/explicativo ──────────────────

class TestHandoffMessages:
    """External tool failure produces structured, actionable messages."""

    def test_security_verification_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_security')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'ChatGPT',
                'browser_security_verification detected before chat could open',
            )
            assert 'Herramienta: ChatGPT' in msg
            assert 'Bloqueo: verificacion de seguridad' in msg
            assert 'Evidencia:' in msg
            assert 'Accion humana:' in msg
            assert 'via local' in msg.lower()
            assert 'blocked_by_security_verification' in meta
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_codex_state_missing_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_codex')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'Codex',
                'codex_state_missing: no se encontro el estado del hilo',
            )
            assert 'Herramienta: Codex' in msg
            assert 'Bloqueo: falta tracking' in msg
            assert 'Accion humana:' in msg
            assert 'needs_human_handoff' in meta
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_access_denied_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_access')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'Claude',
                'acceso denegado al recurso de API',
            )
            assert 'Herramienta: Claude' in msg
            assert 'Bloqueo: acceso denegado' in msg
            assert 'Accion humana:' in msg
            assert 'blocked_by_permission' in meta
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_session_expired_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_session')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'ChatGPT',
                'session expired, login required',
            )
            assert 'Herramienta: ChatGPT' in msg
            assert 'Bloqueo: sesion' in msg
            assert 'Accion humana:' in msg
            assert 'blocked_by_permission' in meta
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_timeout_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_timeout')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'Ollama',
                'timeout after 60s waiting for response',
            )
            assert 'Herramienta: Ollama' in msg
            assert 'timeout' in meta
            assert 'via local' in msg.lower()
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_quota_limit_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_quota')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'ChatGPT',
                'rate limit exceeded for this API key',
            )
            assert 'Herramienta: ChatGPT' in msg
            assert 'cuota o limite' in msg.lower()
            assert 'blocked_by_quota' in meta
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_generic_failure_handoff(self) -> None:
        bootstrap = _make_bootstrap('test_handoff_generic')
        try:
            vm = bootstrap.control_center_viewmodel
            msg, meta, busy = vm._human_external_consultation_failure(
                'Codex',
                'unexpected DOM structure in chat window',
            )
            assert 'Herramienta: Codex' in msg
            assert 'fallo no clasificado' in msg.lower()
            assert 'failed_with_actionable_reason' in meta
            assert 'via local' in msg.lower()
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_external_failure_does_not_stay_consulting(self) -> None:
        """After external consultation failure, busy state is cleared."""
        bootstrap = _make_bootstrap('test_external_not_consulting')
        try:
            vm = bootstrap.control_center_viewmodel
            assert vm is not None
            vm._working = True

            vm._apply_task_failure(
                'external_consultation',
                'acceso denegado al sitio',
            )

            assert vm._working is False, 'UI must not stay in busy/consulting state'
            last_msg = vm.get_chat_messages()[-1]['text']
            assert 'permisos' in last_msg.lower() or 'herramienta' in last_msg.lower() or \
                'denegado' in last_msg.lower()
        finally:
            _cleanup_bootstrap(bootstrap)

    def test_fallback_local_mentioned_in_all_handoffs(self) -> None:
        """Every handoff branch mentions local fallback viability."""
        bootstrap = _make_bootstrap('test_fallback_mentions')
        try:
            vm = bootstrap.control_center_viewmodel
            test_cases = [
                ('ChatGPT', 'browser_security_verification block'),
                ('Codex', 'codex_state_missing'),
                ('Claude', 'acceso denegado'),
                ('ChatGPT', 'session expired'),
                ('Ollama', 'timeout after 60s'),
                ('ChatGPT', 'rate limit exceeded'),
                ('Codex', 'unexpected error'),
            ]
            for title, detail in test_cases:
                msg, _, _ = vm._human_external_consultation_failure(title, detail)
                assert 'via local' in msg.lower() or 'sigo con' in msg.lower(), (
                    f'Handoff for ({title}, {detail}) must mention local fallback'
                )
        finally:
            _cleanup_bootstrap(bootstrap)
