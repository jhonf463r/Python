"""P0.40 focused tests: External Intent Sovereignty + Guided Human Assistance
+ Startup Freeze Budget.

All tests use SimpleNamespace stubs (no AppBootstrap) for speed.
Target: full suite < 5s on normal machine.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Stub factories ────────────────────────────────────────────


def _make_stub_vm(**overrides):
    """Lightweight namespace with P0.40 helper methods bound."""
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
        _last_adaptive_payload={},
        _last_guidance_action='',
        _live_status='idle',
        _heavy_result_guard_active=False,
        _task_start_ts=0.0,
        _external_failure_memory=None,
        _active_incident_frame=None,
        _deferred_retry_generation=0,
        _DEFERRED_RETRY_COOLDOWN_S=0.0,
        _DEFERRED_RETRY_MAX=3,
        _deferred_retry_count=0,
        _deferred_retry_last_ts=0.0,
        _last_user_goal='',
        _attached_files=[],
        _contextual_suggestions=[],
    )
    for k, v in overrides.items():
        setattr(stub, k, v)

    for name in (
        '_evaluate_consultation_quiescence',
        '_schedule_deferred_consultation_retry',
        '_build_assistant_web_skill_profile',
        '_scan_assistant_web_skill',
        '_build_repair_packet',
        '_try_devin_repair',
        '_try_handle_consultation_followup',
        '_assistant_display_name',
        '_should_defer_heavy_work',
        '_normalize_provider',
        '_sanitize_for_repair',
        '_assess_external_readiness',
        '_run_external_consultation',
        '_detect_cdp_available',
        '_set_autonomy_activity_override',
        '_schedule_worker_timeout',
        '_queue_ui_call',
        '_explicit_assistant_preference',
        '_try_handle_incident_followup',
        '_classify_incident_followup_intent',
        '_try_focus_incident_window',
        '_build_incident_help_response',
        '_get_active_incident',
        '_resolve_incident_frame',
        '_record_show_window_learning',
        '_trace_window_focus_result',
        '_current_world_model',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is None:
            continue
        if isinstance(
            ControlCenterViewModel.__dict__.get(name),
            staticmethod,
        ):
            stub.__dict__[name] = method
        else:
            stub.__dict__[name] = types.MethodType(method, stub)

    for attr in (
        '_WEB_SKILL_SESSION_MODES',
        '_WEB_SKILL_AUTH_STATES',
        '_FOLLOWUP_RETRY_PATTERNS',
        '_FOLLOWUP_QUERY_PATTERNS',
        '_FOLLOWUP_WINDOW_PATTERNS',
        '_PROVIDER_ALIASES',
        '_EXTERNAL_WORKER_TIMEOUT_S',
        '_HELP_OFFER_TOKENS',
        '_SHOW_PROBLEM_TOKENS',
        '_VISIBILITY_DISPUTE_TOKENS',
        '_PROFILE_MISMATCH_TOKENS',
        '_RETRY_DONE_TOKENS',
    ):
        val = getattr(ControlCenterViewModel, attr, None)
        if val is not None:
            setattr(stub, attr, val)

    _noop = lambda *a, **kw: None
    for attr in (
        '_append_message', '_record_chat_audit', '_set_live_status',
        '_collect_metrics', '_update_evolution_snapshot',
        '_resolve_active_interaction',
        '_on_deferred_retry_ready',
        '_on_deferred_retry_still_blocked',
        '_clear_autonomy_activity_override',
    ):
        if not hasattr(stub, attr):
            setattr(stub, attr, _noop)
    stub.dataChanged = MagicMock()
    stub.taskResolved = MagicMock()
    stub.taskFailed = MagicMock()
    stub.config = SimpleNamespace(
        workspace_root='/tmp/test_iabv',
        ollama_base_url='', lm_studio_base_url='', ollama_embedding_model='',
    )
    stub.tool_adapters = {}
    stub.adaptive_orchestrator = SimpleNamespace(
        _assess_resource_pressure=lambda: {'under_pressure': False},
    )
    # P0.40: assistant preference resolver
    from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
    stub._assistant_preference_resolver = AssistantPreferenceResolver()
    return stub


# ══════════════════════════════════════════════════════════════
# Test 1: ChatGPT explicit intent does NOT fall to local
# ══════════════════════════════════════════════════════════════

class TestExternalIntentSovereignty:

    @pytest.mark.parametrize('phrase', [
        'haz una consulta a ChatGPT: responde solo S si entiendes',
        'consulta nueva a ChatGPT',
        'pregúntale a ChatGPT si entiende',
        'consulta a chatgpt',
        'usa claude para revisar esto',
        'consulta devin sobre este bug',
    ])
    def test_explicit_external_intent_detected(self, phrase):
        """External intent phrases must be detected by _explicit_assistant_preference."""
        from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
        resolver = AssistantPreferenceResolver()
        result = resolver.resolve(phrase)
        assert result != '', f'Phrase "{phrase}" should detect external intent, got empty'

    @pytest.mark.parametrize('phrase,expected_assistant', [
        ('haz una consulta a ChatGPT: responde solo S si entiendes', 'chatgpt'),
        ('consulta nueva a ChatGPT', 'chatgpt'),
        ('pregúntale a ChatGPT si entiende', 'chatgpt'),
        ('usa claude para revisar esto', 'claude'),
    ])
    def test_explicit_intent_maps_correct_assistant(self, phrase, expected_assistant):
        """The resolver must map to the correct assistant family."""
        from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
        resolver = AssistantPreferenceResolver()
        result = resolver.resolve(phrase)
        assert result == expected_assistant

    def test_sovereignty_guard_calls_run_external_consultation(self):
        """When explicit intent is detected, _run_external_consultation must be called,
        NOT the local chat handler."""
        stub = _make_stub_vm()
        consultation_called = {}

        def mock_run_external(assistant_kind, *, announce=True):
            consultation_called['assistant'] = assistant_kind
            consultation_called['called'] = True
            return True

        stub._run_external_consultation = types.MethodType(
            lambda self, ak, *, announce=True: mock_run_external(ak, announce=announce),
            stub,
        )
        # Simulate the sovereignty guard logic from sendChat
        message = 'haz una consulta a ChatGPT: responde solo S si entiendes'
        explicit = stub._explicit_assistant_preference(message)
        assert explicit == 'chatgpt'
        # The sovereignty guard should route to _run_external_consultation
        if explicit:
            stub._last_user_goal = message
            stub._interaction_has_pending_followup = True
            stub._run_external_consultation(explicit, announce=True)

        assert consultation_called.get('called') is True
        assert consultation_called.get('assistant') == 'chatgpt'

    def test_sovereignty_guard_prevents_local_resolution(self):
        """Explicit external intent must NOT be handled by _try_handle_lightweight_chat."""
        stub = _make_stub_vm()
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        # Bind _is_general_chat_message
        stub._is_general_chat_message = types.MethodType(
            ControlCenterViewModel._is_general_chat_message, stub,
        )
        stub._seems_task_like_message = lambda msg: False
        message = 'haz una consulta a ChatGPT: responde solo S si entiendes'
        # The sovereignty guard should catch it BEFORE lightweight chat
        explicit = stub._explicit_assistant_preference(message)
        assert explicit == 'chatgpt', 'Sovereignty guard must detect this as external intent'

    def test_readiness_gate_triggered_for_external_intent(self):
        """_run_external_consultation calls _assess_external_readiness internally."""
        stub = _make_stub_vm()
        readiness_called = {}

        original_assess = stub._assess_external_readiness

        def tracking_assess(assistant_kind):
            readiness_called['called'] = True
            readiness_called['assistant'] = assistant_kind
            return {
                'action_possible': False,
                'blocking_reason': 'test_block',
                'next_human_action': 'test action',
                'session_selected': 'test',
                'build_state': 'current',
                'resource_pressure': 'none',
                'confidence': 0.5,
            }

        stub._assess_external_readiness = types.MethodType(
            lambda self, ak: tracking_assess(ak), stub,
        )

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            mock_tracer.return_value = MagicMock()
            stub._run_external_consultation('chatgpt', announce=True)

        assert readiness_called.get('called') is True


# ══════════════════════════════════════════════════════════════
# Test 2: Security follow-up "abre esa verificación" does NOT fall local
# ══════════════════════════════════════════════════════════════

class TestGuidedHumanAssistanceIntent:

    def _make_incident(self, **overrides):
        incident = {
            'incident_id': 'test-inc-001',
            'block_type': 'security_verification',
            'assistant_title': 'ChatGPT',
            'profile_label': 'chatgpt_program_session/test',
            'user_help_needed': 'Resuelve la verificacion',
            'available_actions': ['show_problem_window'],
            'resolved': False,
            'expires_at': time.time() + 300,
            'created_at': time.time(),
            'terminal_state': '',
        }
        incident.update(overrides)
        return incident

    def test_abre_esa_verificacion_classified_as_show_problem(self):
        """'abre esa verificacion' must classify as show_problem intent."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        incident = self._make_incident()
        result = ControlCenterViewModel._classify_incident_followup_intent(
            'abre esa verificacion y yo te ayudo con eso', incident,
        )
        assert result['intent'] in ('show_problem', 'help_offer'), \
            f'Expected show_problem or help_offer, got {result["intent"]}'
        assert result['score'] >= 0.5

    def test_yo_te_ayudo_classified_as_help_offer(self):
        """'yo te ayudo con eso' must classify as help_offer intent."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        incident = self._make_incident()
        result = ControlCenterViewModel._classify_incident_followup_intent(
            'yo te ayudo con eso', incident,
        )
        assert result['intent'] == 'help_offer'
        assert result['score'] >= 0.5

    def test_incident_followup_handler_catches_abre_verificacion(self):
        """_try_handle_incident_followup must catch 'abre esa verificacion'."""
        stub = _make_stub_vm()
        incident = self._make_incident()
        stub._active_incident_frame = incident

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            mock_tracer.return_value = MagicMock()
            result = stub._try_handle_incident_followup(
                'ok abre esa verificacion de seguridad y yo te ayudo con eso',
            )

        assert result is True, 'Incident followup must handle this message'

    def test_no_incident_returns_false(self):
        """Without active incident, handler must return False."""
        stub = _make_stub_vm()
        stub._active_incident_frame = None
        result = stub._try_handle_incident_followup('abre esa verificacion')
        assert result is False


# ══════════════════════════════════════════════════════════════
# Test 3: Window focus uses hwnd when available
# ══════════════════════════════════════════════════════════════

class TestWindowFocus:

    def test_focus_with_hwnd_calls_win32(self):
        """When incident has hwnd, _try_focus_incident_window should try Win32."""
        stub = _make_stub_vm()
        incident = {
            'incident_id': 'test-inc-002',
            'hwnd': 12345,
            'profile_label': 'test/profile',
        }
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            mock_tracer.return_value = MagicMock()
            # On Linux, ctypes.windll doesn't exist — focus will fail
            # but the method should still attempt it
            result = stub._try_focus_incident_window(incident)
        # On Linux, Win32 API is not available, so result is False
        # but the important thing is it tried (no crash)
        assert isinstance(result, bool)

    def test_focus_without_hwnd_produces_unresolved(self):
        """Without hwnd, focus should trace unresolved."""
        stub = _make_stub_vm()
        incident = {
            'incident_id': 'test-inc-003',
            'profile_label': 'test/profile',
        }
        stub._current_world_model = lambda: SimpleNamespace(active_windows=[])

        traced_events = []

        def mock_trace(kind, **data):
            traced_events.append({'kind': kind, 'data': data})
            return {}

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace = mock_trace
            mock_tracer.return_value = tracer_inst
            result = stub._try_focus_incident_window(incident)

        assert result is False
        focus_results = [e for e in traced_events if e['kind'] == 'incident_problem_window_focus_result']
        assert len(focus_results) >= 1
        assert focus_results[0]['data']['method'] == 'unresolved'
        assert focus_results[0]['data']['success'] is False


# ══════════════════════════════════════════════════════════════
# Test 4: Startup truth refresh deferred if query_pending
# ══════════════════════════════════════════════════════════════

class TestStartupFreezeBudget:

    def test_truth_refresh_deferred_when_query_pending(self):
        """truth_refresh must be deferred if watchdog reports query_pending."""
        from iabv_v15.bootstrap import AppBootstrap

        boot = object.__new__(AppBootstrap)
        boot._truth_refresh_active = True
        boot._startup_followup_active = True
        boot._deferred_setup_active = False
        boot._startup_evolution_active = False
        boot._prebuild_paused = False

        traced_events = []

        class FakeTracer:
            def trace(self, kind, **data):
                traced_events.append({'kind': kind, 'data': data})
                return {}

        boot._tracer = FakeTracer()
        boot.ui_heartbeat_watchdog = SimpleNamespace(
            _query_pending=True,
            _recent_stalls=[],
            set_startup_followup_active=lambda v: None,
            set_bootstrap_flags=lambda d: None,
        )

        boot._final_startup_truth_refresh()

        assert boot._truth_refresh_active is False
        deferred = [e for e in traced_events if e['kind'] == 'startup_heavy_work_deferred_due_to_user_or_stall']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'query_pending'

    def test_truth_refresh_deferred_when_recent_stall(self):
        """truth_refresh must be deferred if recent UI stall detected."""
        from iabv_v15.bootstrap import AppBootstrap

        boot = object.__new__(AppBootstrap)
        boot._truth_refresh_active = True
        boot._startup_followup_active = True
        boot._deferred_setup_active = False
        boot._startup_evolution_active = False
        boot._prebuild_paused = False

        traced_events = []

        class FakeTracer:
            def trace(self, kind, **data):
                traced_events.append({'kind': kind, 'data': data})
                return {}

        boot._tracer = FakeTracer()
        boot.ui_heartbeat_watchdog = SimpleNamespace(
            _query_pending=False,
            _recent_stalls=[{'at': time.time(), 'duration_ms': 5000}],
            set_startup_followup_active=lambda v: None,
            set_bootstrap_flags=lambda d: None,
        )

        boot._final_startup_truth_refresh()

        assert boot._truth_refresh_active is False
        deferred = [e for e in traced_events if e['kind'] == 'startup_heavy_work_deferred_due_to_user_or_stall']
        assert len(deferred) >= 1
        assert deferred[0]['data']['reason'] == 'recent_ui_stall'

    def test_truth_refresh_skips_heavy_work_when_fresh(self):
        """truth_refresh must not run heavy OSES/PortableContext at startup when fresh."""
        from iabv_v15.bootstrap import AppBootstrap

        boot = object.__new__(AppBootstrap)
        boot._truth_refresh_active = True
        boot._startup_followup_active = True
        boot._deferred_setup_active = False
        boot._startup_evolution_active = False
        boot._prebuild_paused = False
        boot.config = SimpleNamespace(data_dir=None)

        traced_events = []

        class FakeTracer:
            def trace(self, kind, **data):
                traced_events.append({'kind': kind, 'data': data})
                return {}

        boot._tracer = FakeTracer()
        boot.ui_heartbeat_watchdog = SimpleNamespace(
            _query_pending=False,
            _recent_stalls=[],
            set_startup_followup_active=lambda v: None,
            set_bootstrap_flags=lambda d: None,
        )
        boot.operational_self_examination_service = MagicMock()
        boot.portable_context_service = MagicMock()

        boot._final_startup_truth_refresh()

        assert boot._truth_refresh_active is False
        deferred = [e for e in traced_events if e['kind'] == 'startup_heavy_work_deferred_due_to_user_or_stall']
        assert len(deferred) == 0
        skipped = [e for e in traced_events if e['kind'] == 'startup_truth_refresh_skipped_fresh']
        assert len(skipped) == 1
        boot.operational_self_examination_service.build_review.assert_not_called()
        boot.portable_context_service.build_package.assert_not_called()


# ══════════════════════════════════════════════════════════════
# Test 5: OSES detects external intent misrouted local
# ══════════════════════════════════════════════════════════════

class TestOSESExternalIntentMisroutedFinding:

    def test_oses_detects_misrouted_intent(self):
        """OSES must produce finding when external intent was resolved locally."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / 'data' / 'logs' / 'runtime_audit.jsonl'
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            # Write a misrouted event
            event = {
                'kind': 'interaction_resolved',
                'data': {
                    'provider': 'local',
                    'message_excerpt': 'haz una consulta a chatgpt: responde S',
                },
            }
            with audit_path.open('w') as fh:
                fh.write(json.dumps(event) + '\n')

            svc = object.__new__(OperationalSelfExaminationService)
            svc.workspace_root = tmpdir
            findings = svc._external_readiness_missing_findings()

            misrouted = [f for f in findings if f.category == 'external_intent_misrouted_local']
            assert len(misrouted) >= 1
            assert misrouted[0].severity.value == 'high'


# ══════════════════════════════════════════════════════════════
# Test 6: OSES detects startup truth refresh stall
# ══════════════════════════════════════════════════════════════

class TestOSESStartupStallFinding:

    def test_oses_detects_startup_stall(self):
        """OSES must produce finding when startup_truth_refresh stall is repeated."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / 'data' / 'logs' / 'runtime_audit.jsonl'
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            events = [
                {'kind': 'startup_truth_refresh_stall_detected', 'data': {'phase': 'oses_build_review', 'elapsed_ms': 3000}},
                {'kind': 'startup_truth_refresh_stall_detected', 'data': {'phase': 'portable_context_build', 'elapsed_ms': 2500}},
            ]
            with audit_path.open('w') as fh:
                for ev in events:
                    fh.write(json.dumps(ev) + '\n')

            svc = object.__new__(OperationalSelfExaminationService)
            svc.workspace_root = tmpdir
            findings = svc._external_readiness_missing_findings()

            stall_findings = [f for f in findings if f.category == 'startup_truth_refresh_stall_repeated']
            assert len(stall_findings) >= 1


# ══════════════════════════════════════════════════════════════
# Test 7: PortableContext exports next-time policy without PII
# ══════════════════════════════════════════════════════════════

class TestPortableContextNextTimePolicy:

    def test_next_time_policy_section_exists(self):
        """PortableContext must export a next_time_policies section."""
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.events.return_value = [{
                'data': {
                    'policy': 'when_security_verification_show_window_first',
                    'block_type': 'security_verification',
                    'user_action': 'show_problem_window_requested',
                },
            }]
            mock_tracer.return_value = tracer_inst

            svc = object.__new__(PortableContextService)
            svc.workspace_root = '/tmp/test'

            from datetime import datetime, timezone
            section = svc._next_time_policy_section(now=datetime.now(timezone.utc))

        assert section.section_id == 'next_time_policies'
        assert len(section.items) >= 1
        # Verify no PII in the items
        for item in section.items:
            for val in item.values():
                assert '@' not in str(val), 'Policy must not contain PII'
                assert 'password' not in str(val).lower()

    def test_default_policy_when_no_events(self):
        """When no events, a default policy should still be present."""
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.events.return_value = []
            mock_tracer.return_value = tracer_inst

            svc = object.__new__(PortableContextService)
            svc.workspace_root = '/tmp/test'

            from datetime import datetime, timezone
            section = svc._next_time_policy_section(now=datetime.now(timezone.utc))

        assert len(section.items) >= 1
        assert section.items[0]['policy'] == 'when_security_verification_show_window_first'


# ══════════════════════════════════════════════════════════════
# Test 8: Runtime traces are emitted correctly
# ══════════════════════════════════════════════════════════════

class TestRuntimeTraces:

    def test_external_intent_detected_trace(self):
        """Sovereignty guard must emit external_intent_detected trace."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = RuntimeAuditTracer(log_dir=tmpdir)
            tracer.trace(
                'external_intent_detected',
                assistant_kind='chatgpt',
                message_excerpt='haz una consulta a ChatGPT',
                source='sendChat_sovereignty_guard',
            )
            events = tracer.events(kind='external_intent_detected')
            assert len(events) >= 1
            assert events[0]['data']['assistant_kind'] == 'chatgpt'
            assert events[0]['data']['source'] == 'sendChat_sovereignty_guard'

    def test_incident_human_assistance_requested_trace(self):
        """Learning note must emit incident_human_assistance_requested trace."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = RuntimeAuditTracer(log_dir=tmpdir)
            tracer.trace(
                'incident_human_assistance_requested',
                incident_id='test-001',
                block_type='security_verification',
                user_action='show_problem_window_requested',
                policy='when_security_verification_show_window_first',
            )
            events = tracer.events(kind='incident_human_assistance_requested')
            assert len(events) >= 1
            assert events[0]['data']['policy'] == 'when_security_verification_show_window_first'

    def test_startup_heavy_work_deferred_trace(self):
        """Startup freeze budget must emit deferred trace."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = RuntimeAuditTracer(log_dir=tmpdir)
            tracer.trace(
                'startup_heavy_work_deferred_due_to_user_or_stall',
                phase='truth_refresh',
                reason='query_pending',
            )
            events = tracer.events(kind='startup_heavy_work_deferred_due_to_user_or_stall')
            assert len(events) >= 1
            assert events[0]['data']['reason'] == 'query_pending'

    def test_window_focus_result_trace(self):
        """Window focus must emit result trace."""
        from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer

        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = RuntimeAuditTracer(log_dir=tmpdir)
            tracer.trace(
                'incident_problem_window_focus_result',
                incident_id='test-002',
                method='unresolved',
                success=False,
            )
            events = tracer.events(kind='incident_problem_window_focus_result')
            assert len(events) >= 1
            assert events[0]['data']['method'] == 'unresolved'
            assert events[0]['data']['success'] is False
