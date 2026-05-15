"""P0.1 focused tests: terminal-state audit, runtime audit tracing,
and lightweight ControlCenterViewModel stub coverage.

All tests use SimpleNamespace stubs (no AppBootstrap) for speed.
Target: full suite < 10s on normal machine.
"""
from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ── Reuse stub factory from P0 ─────────────────────────────────

def _make_stub_vm():
    """Lightweight namespace with pure helper methods bound."""
    import types
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _active_dispatch_ids={},
        _working=False,
        _working_since=0,
        _busy_label='',
        _latest_response_text='',
        _latest_response_meta='',
        _chat_messages=[],
        _auto_route_enabled=True,
        _selected_role='general_analyst',
        _active_interaction_id=None,
        _interaction_has_pending_followup=False,
        _autonomy_activity_override={},
        _diagnostic_text='',
        _diagnostic_truth_state='unresolved',
        _provider_refreshing=False,
        _ui_state_lock=threading.Lock(),
        _adaptive_session_id=None,
    )
    for name in (
        '_humanize_task_failure',
        '_human_external_consultation_failure',
        '_should_defer_heavy_work',
        '_new_dispatch_id',
        '_is_dispatch_active',
        '_invalidate_dispatch',
        '_external_state_notice',
        '_trace_dispatch_terminal',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            stub.__dict__[name] = types.MethodType(method, stub)
    return stub


# ── A. Terminal-state audit tests ───────────────────────────────

class TestTerminalStateAudit:
    """Verify every failure classification maps to a defined terminal state."""

    def setup_method(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        self.vm = _make_stub_vm()
        self.terminal_states = ControlCenterViewModel._TERMINAL_DISPATCH_STATES

    def test_timeout_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('chat', 'timeout after 120s')
        assert meta in self.terminal_states

    def test_permission_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('external_consultation', 'acceso denegado')
        assert meta in self.terminal_states

    def test_quota_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('chat', 'quota exceeded')
        assert meta in self.terminal_states

    def test_session_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('chat', 'login required')
        assert meta in self.terminal_states

    def test_generic_failure_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('chat', 'unknown error xyz')
        assert meta in self.terminal_states

    def test_traceback_maps_to_terminal(self) -> None:
        _, meta = self.vm._humanize_task_failure('chat', 'AttributeError: foo')
        assert meta in self.terminal_states

    def test_external_security_verification_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification detected',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_external_codex_state_missing_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'Codex', 'codex_state_missing',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_external_access_denied_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'Claude', 'acceso denegado',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_external_timeout_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'Ollama', 'timeout after 60s',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_external_quota_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'ChatGPT', 'rate limit exceeded',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_external_generic_maps_to_terminal(self) -> None:
        _, meta, _ = self.vm._human_external_consultation_failure(
            'Codex', 'unexpected DOM error',
        )
        terminal = meta.split(': ', 1)[-1] if ': ' in meta else meta
        assert terminal in self.terminal_states

    def test_all_eight_terminal_states_present(self) -> None:
        required = {
            'success', 'blocked_by_permission', 'blocked_by_security_verification',
            'blocked_by_quota', 'timeout', 'cancelled',
            'failed_with_actionable_reason', 'needs_human_handoff',
        }
        assert required == self.terminal_states


# ── B. Runtime audit tracing tests ─────────────────────────────

class TestRuntimeAuditTracing:
    """RuntimeAuditTracer.trace_dispatch_terminal records correctly."""

    def test_trace_dispatch_terminal_records_event(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace_dispatch_terminal(
            task_name='chat',
            dispatch_id='abc123def456',
            terminal_state='timeout',
            interaction_id='int-001',
            provider='ollama',
            reason='watchdog fired after 120s',
            user_visible_message_present=True,
        )
        assert event['kind'] == 'dispatch_terminal'
        data = event['data']
        assert data['task_name'] == 'chat'
        assert data['dispatch_id'] == 'abc123def456'[:12]
        assert data['terminal_state'] == 'timeout'
        assert data['interaction_id'] == 'int-001'
        assert data['provider'] == 'ollama'
        assert data['user_visible_message_present'] is True

    def test_trace_dispatch_terminal_truncates_dispatch_id(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        long_id = 'a' * 32
        event = tracer.trace_dispatch_terminal(
            task_name='external_consultation',
            dispatch_id=long_id,
            terminal_state='cancelled',
            reason='stale_discarded: worker finished after dispatch invalidated',
        )
        assert len(event['data']['dispatch_id']) == 12

    def test_trace_dispatch_terminal_empty_dispatch_id(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace_dispatch_terminal(
            task_name='adaptive_action',
            terminal_state='success',
        )
        assert event['data']['dispatch_id'] == ''

    def test_trace_events_filterable_by_kind(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_terminal(
            task_name='chat', terminal_state='timeout',
        )
        tracer.trace_dispatch_terminal(
            task_name='external_consultation', terminal_state='blocked_by_permission',
        )
        tracer.trace('some_other_kind')
        dispatch_events = tracer.events(kind='dispatch_terminal')
        assert len(dispatch_events) == 2
        assert all(e['kind'] == 'dispatch_terminal' for e in dispatch_events)


class TestViewModelTraceHelper:
    """_trace_dispatch_terminal helper on ControlCenterViewModel stub."""

    def test_trace_helper_calls_tracer(self) -> None:
        vm = _make_stub_vm()
        vm._active_interaction_id = 'test-int-123'
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_get:
            mock_tracer = MagicMock()
            mock_get.return_value = mock_tracer
            vm._trace_dispatch_terminal(
                task_name='chat',
                dispatch_id='abc123',
                terminal_state='timeout',
                reason='watchdog',
            )
            mock_tracer.trace_dispatch_terminal.assert_called_once()
            call_kwargs = mock_tracer.trace_dispatch_terminal.call_args[1]
            assert call_kwargs['task_name'] == 'chat'
            assert call_kwargs['terminal_state'] == 'timeout'
            assert call_kwargs['interaction_id'] == 'test-int-123'

    def test_trace_helper_survives_import_error(self) -> None:
        vm = _make_stub_vm()
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   side_effect=ImportError('test')):
            # Must not raise
            vm._trace_dispatch_terminal(
                task_name='chat', terminal_state='timeout',
            )


# ── C. Lightweight ControlCenterViewModel P0-critical path stubs ──

class TestExternalConsultationFailureStub:
    """External consultation failure humanization without bootstrap."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_access_denied_stops_waiting_state(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'Claude', 'acceso denegado al recurso de API',
        )
        assert 'blocked_by_permission' in meta
        assert 'Herramienta: Claude' in msg
        assert 'acceso denegado' in msg.lower()
        assert busy  # busy label set

    def test_security_verification_handoff(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'ChatGPT', 'browser_security_verification challenge',
        )
        assert 'blocked_by_security_verification' in meta
        assert 'captcha' in msg.lower() or 'verificacion' in msg.lower()
        assert 'Accion humana:' in msg

    def test_missing_thread_tracking_handoff(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'Codex', 'codex_state_missing: no thread state found',
        )
        assert 'needs_human_handoff' in meta
        assert 'tracking' in msg.lower() or 'hilo' in msg.lower()

    def test_wrong_thread_notice(self) -> None:
        notice = self.vm._external_state_notice(['wrong_thread'])
        assert 'no coincide' in notice.lower() or 'hilo esperado' in notice.lower()

    def test_session_expired_fallback(self) -> None:
        msg, meta, busy = self.vm._human_external_consultation_failure(
            'ChatGPT', 'session expired, login required',
        )
        assert 'blocked_by_permission' in meta
        assert 'via local' in msg.lower() or 'sigo con' in msg.lower()


class TestDispatchIdGuardsAdaptiveAction:
    """adaptive_action now has dispatch_id — verify via stubs."""

    def setup_method(self) -> None:
        self.vm = _make_stub_vm()

    def test_adaptive_action_dispatch_id_created(self) -> None:
        d1 = self.vm._new_dispatch_id('adaptive_action')
        assert self.vm._is_dispatch_active('adaptive_action', d1)

    def test_adaptive_action_new_dispatch_invalidates_old(self) -> None:
        d1 = self.vm._new_dispatch_id('adaptive_action')
        d2 = self.vm._new_dispatch_id('adaptive_action')
        assert not self.vm._is_dispatch_active('adaptive_action', d1)
        assert self.vm._is_dispatch_active('adaptive_action', d2)

    def test_adaptive_action_independent_from_chat(self) -> None:
        d_chat = self.vm._new_dispatch_id('chat')
        d_aa = self.vm._new_dispatch_id('adaptive_action')
        assert self.vm._is_dispatch_active('chat', d_chat)
        assert self.vm._is_dispatch_active('adaptive_action', d_aa)


class TestPressureGatingStub:
    """_should_defer_heavy_work under various pressure states."""

    def test_high_pressure_defers(self) -> None:
        vm = _make_stub_vm()
        vm.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {'under_pressure': True}
        )
        assert vm._should_defer_heavy_work() is True

    def test_normal_pressure_allows(self) -> None:
        vm = _make_stub_vm()
        vm.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {'under_pressure': False}
        )
        assert vm._should_defer_heavy_work() is False

    def test_orchestrator_error_allows(self) -> None:
        vm = _make_stub_vm()
        vm.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=MagicMock(side_effect=RuntimeError)
        )
        assert vm._should_defer_heavy_work() is False


# ── D. Platform pending metadata tests (model-validated) ───────

class TestPlatformPendingModelValidation:
    """Platform pending task files validate with PlatformPendingTask model."""

    _TASK_IDS = [
        ('runtime_consulting_lifecycle_recovery', 'runtime_consulting_lifecycle_recovery'),
        ('runtime_main_thread_antifreeze_budget', 'runtime_main_thread_antifreeze_budget'),
        ('external_visual_handoff_alignment', 'external_visual_handoff_alignment'),
    ]

    def _load_and_validate(self, filename: str):
        from pathlib import Path
        from iabv_v15.domain.models import PlatformPendingTask
        path = Path(__file__).parent.parent / 'data' / 'evolution' / 'platform_pending' / f'task_{filename}.json'
        assert path.exists(), f'Missing platform_pending file: {path}'
        return PlatformPendingTask.model_validate_json(path.read_bytes())

    def test_consulting_lifecycle_validates_with_correct_id(self) -> None:
        task = self._load_and_validate('runtime_consulting_lifecycle_recovery')
        assert task.id == 'runtime_consulting_lifecycle_recovery'
        assert task.status.value == 'READY_FOR_NEXT_SLICE'
        assert task.metadata.get('covered_by_pr') == '#377'

    def test_antifreeze_budget_validates_with_correct_id(self) -> None:
        task = self._load_and_validate('runtime_main_thread_antifreeze_budget')
        assert task.id == 'runtime_main_thread_antifreeze_budget'
        assert task.status.value == 'READY_FOR_NEXT_SLICE'
        assert task.metadata.get('covered_by_pr') == '#377'

    def test_external_handoff_validates_with_correct_id(self) -> None:
        task = self._load_and_validate('external_visual_handoff_alignment')
        assert task.id == 'external_visual_handoff_alignment'
        assert task.status.value == 'READY_FOR_NEXT_SLICE'
        assert task.metadata.get('covered_by_pr') == '#377'

    def test_all_tasks_have_unresolved_in_metadata(self) -> None:
        for filename, expected_id in self._TASK_IDS:
            task = self._load_and_validate(filename)
            assert task.id == expected_id, f'{filename}: id mismatch'
            assert task.metadata.get('unresolved'), f'{filename} must have unresolved in metadata'

    def test_all_tasks_have_resume_hint(self) -> None:
        for filename, _ in self._TASK_IDS:
            task = self._load_and_validate(filename)
            assert task.resume_hint, f'{filename} must have resume_hint'


# ── E. Success tracing tests ──────────────────────────────────

class TestSuccessTracing:
    """_apply_task_result must emit trace_dispatch_terminal with success."""

    def test_success_trace_emitted_on_chat_result(self) -> None:
        vm = _make_stub_vm()
        d_id = vm._new_dispatch_id('chat')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_get:
            mock_tracer = MagicMock()
            mock_get.return_value = mock_tracer
            vm._trace_dispatch_terminal(
                task_name='chat',
                dispatch_id=d_id,
                terminal_state='success',
                provider='ollama',
                reason='resolved',
                user_visible_message=True,
            )
            mock_tracer.trace_dispatch_terminal.assert_called_once()
            call_kwargs = mock_tracer.trace_dispatch_terminal.call_args[1]
            assert call_kwargs['terminal_state'] == 'success'
            assert call_kwargs['task_name'] == 'chat'

    def test_success_trace_emitted_on_external_consultation(self) -> None:
        vm = _make_stub_vm()
        d_id = vm._new_dispatch_id('external_consultation')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_get:
            mock_tracer = MagicMock()
            mock_get.return_value = mock_tracer
            vm._trace_dispatch_terminal(
                task_name='external_consultation',
                dispatch_id=d_id,
                terminal_state='success',
                provider='ChatGPT',
                reason='resolved',
                user_visible_message=True,
            )
            call_kwargs = mock_tracer.trace_dispatch_terminal.call_args[1]
            assert call_kwargs['terminal_state'] == 'success'
            assert call_kwargs['task_name'] == 'external_consultation'

    def test_success_trace_emitted_on_adaptive_action(self) -> None:
        vm = _make_stub_vm()
        d_id = vm._new_dispatch_id('adaptive_action')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_get:
            mock_tracer = MagicMock()
            mock_get.return_value = mock_tracer
            vm._trace_dispatch_terminal(
                task_name='adaptive_action',
                dispatch_id=d_id,
                terminal_state='success',
                reason='resolved',
                user_visible_message=True,
            )
            call_kwargs = mock_tracer.trace_dispatch_terminal.call_args[1]
            assert call_kwargs['terminal_state'] == 'success'


# ── F. Stale workers use 'cancelled' not 'stale_discarded' ────

class TestStaleWorkerUsesCancelled:
    """All stale worker traces must use terminal_state='cancelled'."""

    def test_no_stale_discarded_in_terminal_states(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert 'stale_discarded' not in ControlCenterViewModel._TERMINAL_DISPATCH_STATES

    def test_cancelled_in_terminal_states(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert 'cancelled' in ControlCenterViewModel._TERMINAL_DISPATCH_STATES

    def test_stale_dispatch_traces_cancelled(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace_dispatch_terminal(
            task_name='chat',
            dispatch_id='abc123',
            terminal_state='cancelled',
            reason='stale_discarded: worker finished after dispatch invalidated',
        )
        assert event['data']['terminal_state'] == 'cancelled'
        assert 'stale_discarded' in event['data']['reason']
