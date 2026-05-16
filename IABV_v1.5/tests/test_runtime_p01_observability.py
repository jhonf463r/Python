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
        assert task.status.value == 'UNRESOLVED'
        assert task.metadata.get('covered_by_pr') == '#377'
        assert task.metadata.get('verification_status') == 'CODE_VERIFIED_AWAITING_LIVE_PROOF'
        audit = task.metadata.get('code_audit')
        assert audit is not None
        assert audit['tests_passed'] >= 286
        assert audit['tests_failed'] == 0

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


# ── E. Success / blocked tracing via _apply_task_result ────────

def _make_apply_result_stub():
    """Build a stub VM capable of running _apply_task_result for
    external_consultation without AppBootstrap.

    Binds only the dispatch-tracing path and _apply_task_result itself.
    Heavy sub-methods are replaced with no-ops via MagicMock.
    """
    import types
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = _make_stub_vm()
    stub._last_user_goal = 'test goal'
    stub._provider_refreshing = False
    stub._provider_cards = []
    stub._agent_cards = []
    stub._pbt_state = {}
    stub._pbt_candidates = []
    stub._chat_interaction_lifecycle = None
    stub._interaction_has_pending_followup = False
    stub._progress_cards = []
    stub._assistant_guidance_mode = 'auto'
    stub._assistant_action_buttons = []
    stub._traced_calls = []

    original_trace = ControlCenterViewModel._trace_dispatch_terminal

    def _capture_trace(self, **kwargs):
        self._traced_calls.append(kwargs)
        original_trace(self, **kwargs)

    # Bind real methods for the tracing path
    for name in (
        '_apply_task_result', '_should_defer_heavy_work',
        '_remember_external_failure', '_clear_external_failure_memory',
    ):
        stub.__dict__[name] = types.MethodType(
            getattr(ControlCenterViewModel, name), stub,
        )
    stub.__dict__['_trace_dispatch_terminal'] = types.MethodType(_capture_trace, stub)
    # Static method
    stub._derive_external_consultation_outcome = ControlCenterViewModel._derive_external_consultation_outcome

    # No-op stubs for everything else _apply_task_result calls
    _noop = lambda *a, **kw: None
    _noop_list = lambda *a, **kw: []
    for attr in (
        '_clear_autonomy_activity_override', '_update_adaptive_state',
        '_set_external_consultation_activity', '_resolve_active_interaction',
        '_update_progress_cards', '_append_message', '_record_chat_audit',
        '_update_evolution_snapshot', '_refresh_development_packet',
        '_refresh_autonomy_dock', '_reset_assistant_guidance',
        '_set_autonomy_activity_override', '_promote_metacognition_after_resolution',
        '_set_live_status', '_collect_metrics',
    ):
        setattr(stub, attr, _noop)
    stub._build_agent_cards = _noop_list
    stub.dataChanged = MagicMock()
    stub.taskResolved = MagicMock()
    stub.taskFailed = MagicMock()
    stub._FINAL_INTERACTION_OUTCOMES = ControlCenterViewModel._FINAL_INTERACTION_OUTCOMES
    stub._TERMINAL_DISPATCH_STATES = ControlCenterViewModel._TERMINAL_DISPATCH_STATES
    return stub


class TestApplyTaskResultTracing:
    """_apply_task_result must emit correct terminal_state for all scenarios."""

    def test_external_blocked_permission_traces_blocked(self) -> None:
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result('external_consultation', {
            'success': False,
            'meta': 'blocked_by_permission',
            'assistant_title': 'ChatGPT',
            'message': 'Access denied',
        })
        assert len(vm._traced_calls) == 1
        assert vm._traced_calls[0]['terminal_state'] == 'blocked_by_permission'
        assert 'external_consultation_blocked' in vm._traced_calls[0]['reason']

    def test_external_blocked_security_traces_security(self) -> None:
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result('external_consultation', {
            'success': False,
            'meta': 'ChatGPT: blocked_by_security_verification',
            'assistant_title': 'ChatGPT',
            'message': 'Security check required',
        })
        assert len(vm._traced_calls) == 1
        assert vm._traced_calls[0]['terminal_state'] == 'blocked_by_security_verification'

    def test_external_success_traces_success(self) -> None:
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result('external_consultation', {
            'success': True,
            'meta': 'consulta completada',
            'assistant_title': 'ChatGPT',
            'message': 'Respuesta recibida',
        })
        assert len(vm._traced_calls) == 1
        assert vm._traced_calls[0]['terminal_state'] == 'success'
        assert vm._traced_calls[0]['reason'] == 'resolved'

    def test_dispatch_id_invalidated_after_trace(self) -> None:
        vm = _make_apply_result_stub()
        d_id = vm._new_dispatch_id('external_consultation')
        assert vm._is_dispatch_active('external_consultation', d_id)
        vm._apply_task_result('external_consultation', {
            'success': False,
            'meta': 'blocked_by_permission',
            'assistant_title': 'Claude',
        })
        assert not vm._is_dispatch_active('external_consultation', d_id)

    def test_external_blocked_quota_traces_quota(self) -> None:
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result('external_consultation', {
            'success': False,
            'meta': 'blocked_by_quota',
            'assistant_title': 'ChatGPT',
        })
        assert vm._traced_calls[0]['terminal_state'] == 'blocked_by_quota'

    def test_external_blocked_unknown_falls_to_failed_actionable(self) -> None:
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result('external_consultation', {
            'success': False,
            'meta': 'some unknown error',
            'assistant_title': 'Codex',
        })
        assert vm._traced_calls[0]['terminal_state'] == 'failed_with_actionable_reason'


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


# ── G. P0.2 Dispatch lifecycle tests ─────────────────────────

class TestDispatchLifecycleReconstruction:
    """started → terminal can be reconstructed with duration and state."""

    def test_started_to_success_reconstructs_duration(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='d001',
            provider='ollama', source='sendChat',
            user_goal_excerpt='hola', visible_busy_label='Procesando...',
        )
        import time; time.sleep(0.01)
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='d001',
            terminal_state='success', provider='ollama',
            user_visible_message_present=True,
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        assert len(cycles) >= 1
        c = next(c for c in cycles if c['dispatch_id'] == 'd001'[:12])
        assert c['terminal_state'] == 'success'
        assert c['duration_ms'] > 0
        assert c['unresolved'] is False
        assert c['task_name'] == 'chat'

    def test_started_to_blocked_reconstructs_terminal(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='external_consultation', dispatch_id='d002',
            provider='ChatGPT', source='_run_external_consultation',
        )
        tracer.trace_dispatch_terminal(
            task_name='external_consultation', dispatch_id='d002',
            terminal_state='blocked_by_permission', provider='ChatGPT',
            reason='external_consultation_blocked: blocked_by_permission',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        c = next(c for c in cycles if c['dispatch_id'] == 'd002'[:12])
        assert c['terminal_state'] == 'blocked_by_permission'
        assert c['unresolved'] is False

    def test_started_to_timeout_reconstructs_terminal(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='d003',
            source='sendChat',
        )
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='d003',
            terminal_state='timeout',
            reason='worker did not complete within 120s',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        c = next(c for c in cycles if c['dispatch_id'] == 'd003'[:12])
        assert c['terminal_state'] == 'timeout'
        assert c['unresolved'] is False

    def test_started_without_terminal_is_unresolved(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='adaptive_action', dispatch_id='d004',
            source='_run_adaptive_action:execute',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        c = next(c for c in cycles if c['dispatch_id'] == 'd004'[:12])
        assert c['unresolved'] is True
        assert c['terminal_state'] == ''

    def test_lifecycle_correlated_sorted_newest_first(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='old1', source='s')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='old1', terminal_state='success')
        import time; time.sleep(0.005)
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='new2', source='s')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='new2', terminal_state='timeout')
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        correlated = [c for c in cycles if not c['orphan_terminal'] and not c['unresolved']]
        assert correlated[0]['dispatch_id'] == 'new2'[:12]
        assert correlated[1]['dispatch_id'] == 'old1'[:12]


class TestTraceDispatchStarted:
    """trace_dispatch_started records correct fields."""

    def test_started_event_fields(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace_dispatch_started(
            task_name='chat',
            dispatch_id='abc123def456',
            interaction_id='int-001',
            provider='ollama',
            source='sendChat',
            user_goal_excerpt='como esta el clima',
            visible_busy_label='Procesando...',
        )
        assert event['kind'] == 'dispatch_started'
        d = event['data']
        assert d['task_name'] == 'chat'
        assert d['dispatch_id'] == 'abc123def456'[:12]
        assert d['interaction_id'] == 'int-001'
        assert d['provider'] == 'ollama'
        assert d['source'] == 'sendChat'
        assert d['user_goal_excerpt'] == 'como esta el clima'
        assert d['visible_busy_label'] == 'Procesando...'

    def test_started_truncates_long_fields(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        event = tracer.trace_dispatch_started(
            task_name='chat',
            dispatch_id='x' * 64,
            user_goal_excerpt='y' * 200,
            visible_busy_label='z' * 200,
        )
        d = event['data']
        assert len(d['dispatch_id']) == 12
        assert len(d['user_goal_excerpt']) == 120
        assert len(d['visible_busy_label']) == 120


class TestLatestDispatchLifecycleProperty:
    """latestDispatchLifecycle exposes correct read-only summary."""

    def test_returns_empty_when_no_events(self) -> None:
        vm = _make_stub_vm()
        import types
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        vm.__dict__['latestDispatchLifecycle'] = types.MethodType(
            lambda self: ControlCenterViewModel.latestDispatchLifecycle.fget(self), vm)
        # Without mocking the tracer, this should return {} or handle gracefully
        result = vm.latestDispatchLifecycle()
        assert isinstance(result, dict)

    def test_returns_lifecycle_data_with_tracer(self) -> None:
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='test01',
            provider='ollama', source='sendChat',
        )
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='test01',
            terminal_state='success', provider='ollama',
            user_visible_message_present=True,
        )
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            import types
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            vm = _make_stub_vm()
            result = ControlCenterViewModel.latestDispatchLifecycle.fget(vm)
            assert result['task_name'] == 'chat'
            assert result['terminal_state'] == 'success'
            assert result['unresolved'] is False


# ── H. Orphan terminal priority tests (BLOCKER 1 fix) ────────

class TestOrphanTerminalPriority:
    """Correlated lifecycle beats orphan terminal in priority."""

    def test_correlated_preferred_over_orphan_terminal(self) -> None:
        """started→terminal with dispatch_id + orphan terminal posterior:
        recent_dispatch_lifecycles(limit=1) must return the correlated cycle."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='abc123',
            provider='ollama', source='sendChat',
        )
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='abc123',
            terminal_state='timeout', provider='ollama',
        )
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='',
            terminal_state='timeout',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=1)
        assert len(cycles) == 1
        c = cycles[0]
        assert c['dispatch_id'] == 'abc123'[:12]
        assert c['duration_ms'] > 0
        assert c['provider'] == 'ollama'
        assert c['orphan_terminal'] is False

    def test_orphan_terminal_marked_as_orphan(self) -> None:
        """Orphan terminal without any started: appears with orphan_terminal=True."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='',
            terminal_state='timeout',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        assert len(cycles) == 1
        c = cycles[0]
        assert c['orphan_terminal'] is True
        assert c['terminal_state'] == 'timeout'

    def test_unresolved_started_not_lost(self) -> None:
        """A started event without terminal stays unresolved=True and is not hidden."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='unres01',
            source='sendChat',
        )
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='',
            terminal_state='timeout',
        )
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        unresolved = [c for c in cycles if c['unresolved']]
        orphans = [c for c in cycles if c['orphan_terminal']]
        assert len(unresolved) == 1
        assert unresolved[0]['dispatch_id'] == 'unres01'[:12]
        assert len(orphans) == 1
        assert orphans[0]['orphan_terminal'] is True

    def test_latest_dispatch_lifecycle_prefers_correlated(self) -> None:
        """latestDispatchLifecycle must pick correlated over orphan terminal."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(
            task_name='chat', dispatch_id='abc123',
            provider='ollama', source='sendChat',
        )
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='abc123',
            terminal_state='timeout', provider='ollama',
        )
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(
            task_name='chat', dispatch_id='',
            terminal_state='timeout',
        )
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            vm = _make_stub_vm()
            result = ControlCenterViewModel.latestDispatchLifecycle.fget(vm)
            assert result['dispatch_id'] == 'abc123'[:12]
            assert result['duration_ms'] > 0
            assert result['provider'] == 'ollama'
            assert result['orphan_terminal'] is False


# ── I. Unresolved dispatch visibility tests (BLOCKER 2 fix) ──

class TestUnresolvedDispatchVisibility:
    """New unresolved dispatch must not be hidden by older correlated."""

    def test_new_unresolved_beats_old_correlated(self) -> None:
        """old correlated success + new unresolved started:
        recent_dispatch_lifecycles(limit=1)[0] must be the new unresolved."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='old1', source='s')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='old1', terminal_state='success')
        import time; time.sleep(0.005)
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='new2', source='s')
        cycles = tracer.recent_dispatch_lifecycles(limit=1)
        assert len(cycles) == 1
        assert cycles[0]['dispatch_id'] == 'new2'[:12]
        assert cycles[0]['unresolved'] is True

    def test_correlated_still_beats_orphan(self) -> None:
        """correlated + later orphan terminal:
        correlated with dispatch_id must still win over orphan."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='c01', source='s')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='c01', terminal_state='success')
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='', terminal_state='timeout')
        cycles = tracer.recent_dispatch_lifecycles(limit=1)
        assert cycles[0]['dispatch_id'] == 'c01'[:12]
        assert cycles[0]['orphan_terminal'] is False

    def test_orphan_only_appears_with_flag(self) -> None:
        """orphan only: appears as orphan_terminal=True."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='', terminal_state='failed_with_actionable_reason')
        cycles = tracer.recent_dispatch_lifecycles(limit=5)
        assert len(cycles) == 1
        assert cycles[0]['orphan_terminal'] is True

    def test_latest_lifecycle_shows_new_unresolved(self) -> None:
        """latestDispatchLifecycle: old success + new unresolved must show new unresolved."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='old1', source='s')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='old1', terminal_state='success')
        import time; time.sleep(0.005)
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='new2', source='s')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            vm = _make_stub_vm()
            result = ControlCenterViewModel.latestDispatchLifecycle.fget(vm)
            assert result['dispatch_id'] == 'new2'[:12]
            assert result['unresolved'] is True

    def test_latest_lifecycle_correlated_over_orphan(self) -> None:
        """latestDispatchLifecycle: old success + later orphan must show old correlated."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
        tracer = RuntimeAuditTracer()
        tracer.trace_dispatch_started(task_name='chat', dispatch_id='c01', source='s', provider='ollama')
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='c01', terminal_state='success', provider='ollama')
        import time; time.sleep(0.005)
        tracer.trace_dispatch_terminal(task_name='chat', dispatch_id='', terminal_state='timeout')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            vm = _make_stub_vm()
            result = ControlCenterViewModel.latestDispatchLifecycle.fget(vm)
            assert result['dispatch_id'] == 'c01'[:12]
            assert result['orphan_terminal'] is False
            assert result['terminal_state'] == 'success'
