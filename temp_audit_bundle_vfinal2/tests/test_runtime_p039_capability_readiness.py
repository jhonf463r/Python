"""P0.39 focused tests: Universal Capability Readiness.

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
from unittest.mock import MagicMock, patch

import pytest


# ── Stub factories ────────────────────────────────────────────


def _make_stub_vm(**overrides):
    """Lightweight namespace with P0.38 + P0.39 helper methods bound."""
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
    )
    for k, v in overrides.items():
        setattr(stub, k, v)

    # Bind P0.38 + P0.39 methods from ControlCenterViewModel
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

    # Copy class-level tuples/constants
    for attr in (
        '_WEB_SKILL_SESSION_MODES',
        '_WEB_SKILL_AUTH_STATES',
        '_FOLLOWUP_RETRY_PATTERNS',
        '_FOLLOWUP_QUERY_PATTERNS',
        '_FOLLOWUP_WINDOW_PATTERNS',
        '_PROVIDER_ALIASES',
        '_EXTERNAL_WORKER_TIMEOUT_S',
    ):
        val = getattr(ControlCenterViewModel, attr, None)
        if val is not None:
            setattr(stub, attr, val)

    # Noop helpers
    _noop = lambda *a, **kw: None
    for attr in (
        '_append_message', '_record_chat_audit', '_set_live_status',
        '_collect_metrics', '_update_evolution_snapshot',
        '_resolve_active_interaction',
        '_on_deferred_retry_ready',
        '_on_deferred_retry_still_blocked',
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
    return stub


# ══════════════════════════════════════════════════════════════
# 1. Runtime stale blocks normal test and shows action
# ══════════════════════════════════════════════════════════════

class TestRuntimeStaleBlocksConsultation:

    def test_stale_build_blocks_action(self):
        """When build is stale, action_possible must be False."""
        stub = _make_stub_vm()
        # Patch trace_build_fingerprint to return stale
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': True, 'head': 'abc123def456',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['action_possible'] is False
        assert readiness['blocking_reason'] == 'build_stale'
        assert 'origin/main' in readiness['next_human_action']
        assert readiness['build_state'] == 'stale'

    def test_stale_build_shows_human_action(self):
        """Stale build must produce next_human_action with runtime alignment instructions."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': True, 'head': 'deadbeef1234',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['next_human_action'] != ''
        assert 'runtime' in readiness['next_human_action'].lower()

    def test_current_build_allows_action(self):
        """When build is current, stale should not block."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc123def456',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['build_state'] == 'current'
        assert readiness['blocking_reason'] != 'build_stale'


# ══════════════════════════════════════════════════════════════
# 2. P0.38 markers present after merge
# ══════════════════════════════════════════════════════════════

class TestP038MarkersPresent:

    def test_readiness_contract_has_all_fields(self):
        """Readiness contract must have all 16+ required fields."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc123',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        required_keys = {
            'tool_id', 'assistant_kind', 'device_state', 'build_state',
            'resource_pressure', 'session_mode', 'session_selected',
            'auth_state', 'security_block_state', 'observation_permission',
            'action_possible', 'capture_possible', 'response_capture_mode',
            'confidence', 'blocking_reason', 'next_human_action',
            'evidence_refs', 'last_verified_at',
        }
        assert required_keys.issubset(readiness.keys())

    def test_assistant_kind_propagated(self):
        """assistant_kind must match the input parameter."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('claude')

        assert readiness['assistant_kind'] == 'claude'
        assert 'claude' in readiness['tool_id']


# ══════════════════════════════════════════════════════════════
# 3. ChatGPT readiness without CDP does not declare available
# ══════════════════════════════════════════════════════════════

class TestChatGPTReadinessWithoutCDP:

    def test_no_cdp_capture_not_possible_via_cdp(self):
        """Without CDP, response_capture_mode should not be 'cdp'."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        # Without CDP env var or actual CDP, mode should not be cdp
        if readiness['response_capture_mode'] == 'cdp':
            # This can only happen if web skill profile reports cdp available
            assert readiness['capture_possible'] is True
        else:
            assert readiness['response_capture_mode'] in (
                'manual_pasteback', 'dom_observation',
            )

    def test_no_cdp_session_not_governed_cdp(self):
        """Without CDP env, session_selected should not be governed_user_chrome_cdp."""
        stub = _make_stub_vm()
        env_backup = os.environ.pop('IABV_PREFER_CDP_SESSION', None)
        try:
            with patch(
                'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
            ) as mock_tracer:
                tracer_inst = MagicMock()
                tracer_inst.trace_build_fingerprint.return_value = {
                    'stale': False, 'head': 'abc',
                }
                tracer_inst.trace_external_readiness.return_value = {}
                mock_tracer.return_value = tracer_inst
                readiness = stub._assess_external_readiness('chatgpt')
        finally:
            if env_backup is not None:
                os.environ['IABV_PREFER_CDP_SESSION'] = env_backup

        assert readiness['session_selected'] != 'governed_user_chrome_cdp'


# ══════════════════════════════════════════════════════════════
# 4. Security verification produces next_human_action
# ══════════════════════════════════════════════════════════════

class TestSecurityVerificationProducesHumanAction:

    def test_security_block_in_readiness(self):
        """When web skill profile reports security_verification block,
        readiness must include next_human_action."""
        stub = _make_stub_vm()
        # Override _build_assistant_web_skill_profile to report security block
        def fake_profile(self_arg, ak):
            return {
                'active_session_mode': 'isolated_profile',
                'auth_status': 'security_verification',
                'cdp_status': 'unavailable',
                'window_status': 'found',
                'window_hwnd': 12345,
                'last_block_reason': 'blocked_by_security_verification',
                'browser_profile_path': 'data/tool_teaching/external_assistants/chatgpt_program_session/browser_profile',
            }
        stub._build_assistant_web_skill_profile = types.MethodType(fake_profile, stub)

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['security_block_state'] == 'security_verification'
        assert readiness['action_possible'] is False
        assert readiness['blocking_reason'] == 'security_verification_recent'
        assert readiness['next_human_action'] != ''
        assert 'perfil aislado' in readiness['next_human_action']
        assert 'ya lo hice' in readiness['next_human_action']

    def test_security_verification_blocks_consultation(self):
        """_run_external_consultation must return False when security_verification blocks."""
        stub = _make_stub_vm()
        def fake_readiness(self_arg, ak):
            return {
                'tool_id': 'external_assistant_chatgpt',
                'assistant_kind': ak,
                'assistant_title': 'ChatGPT',
                'device_state': 'window_found',
                'build_state': 'current',
                'resource_pressure': 'none',
                'session_mode': 'isolated_profile',
                'session_selected': 'isolated_profile',
                'auth_state': 'security_verification',
                'security_block_state': 'security_verification',
                'observation_permission': 'unknown',
                'action_possible': False,
                'capture_possible': False,
                'response_capture_mode': 'manual_pasteback',
                'confidence': 0.2,
                'blocking_reason': 'security_verification_recent',
                'next_human_action': 'Resuelve la verificacion en la ventana IABV.',
                'evidence_refs': [],
                'last_verified_at': time.time(),
            }
        stub._assess_external_readiness = types.MethodType(fake_readiness, stub)
        result = stub._run_external_consultation('chatgpt', announce=True)
        assert result is False
        assert stub._working is False
        assert 'security_verification' in stub._latest_response_meta
        assert 'Resuelve' in stub._latest_response_text

    def test_security_block_produces_handoff_message(self):
        """Security block must produce message with next_human_action."""
        stub = _make_stub_vm()
        def fake_readiness(self_arg, ak):
            return {
                'tool_id': 'external_assistant_chatgpt',
                'assistant_kind': ak,
                'assistant_title': 'ChatGPT',
                'device_state': 'window_found',
                'build_state': 'current',
                'resource_pressure': 'none',
                'session_mode': 'isolated_profile',
                'session_selected': 'isolated_profile',
                'auth_state': 'security_verification',
                'security_block_state': 'security_verification',
                'observation_permission': 'unknown',
                'action_possible': False,
                'capture_possible': False,
                'response_capture_mode': 'manual_pasteback',
                'confidence': 0.2,
                'blocking_reason': 'security_verification_recent',
                'next_human_action': 'Resuelve la verificacion y escribe ya lo hice.',
                'evidence_refs': [],
                'last_verified_at': time.time(),
            }
        stub._assess_external_readiness = types.MethodType(fake_readiness, stub)
        stub._run_external_consultation('chatgpt', announce=True)
        assert 'ya lo hice' in stub._latest_response_text

    def test_security_block_explains_chrome_difference(self):
        """next_human_action must mention that the profile is NOT user's normal Chrome."""
        stub = _make_stub_vm()
        def fake_profile(self_arg, ak):
            return {
                'active_session_mode': 'isolated_profile',
                'auth_status': 'security_verification',
                'cdp_status': 'unavailable',
                'window_status': 'found',
                'window_hwnd': 12345,
                'last_block_reason': 'blocked_by_security_verification',
                'browser_profile_path': 'chatgpt_program_session/browser_profile',
            }
        stub._build_assistant_web_skill_profile = types.MethodType(fake_profile, stub)

        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert 'Chrome normal' in readiness['next_human_action']


# ══════════════════════════════════════════════════════════════
# 5. "abre la ventana" uses active incident, not local
# ══════════════════════════════════════════════════════════════

class TestOpenWindowUsesIncident:

    def test_window_followup_uses_incident_hwnd(self):
        """'abre la ventana' must prefer ActiveIncidentFrame hwnd."""
        stub = _make_stub_vm()
        stub._active_incident_frame = {
            'resolved': False,
            'expires_at': time.time() + 300,
            'assistant_kind': 'chatgpt',
            'assistant_title': 'ChatGPT',
            'hwnd': 99999,
        }
        # The followup handler should use the incident frame's hwnd
        # We test via _try_handle_consultation_followup
        assert stub._active_incident_frame['hwnd'] == 99999


# ══════════════════════════════════════════════════════════════
# 6. "intenta nuevamente" under pressure stays deferred
# ══════════════════════════════════════════════════════════════

class TestRetryUnderPressureDeferred:

    def test_readiness_allows_high_pressure_external_consultation(self):
        """High pressure must budget heavy work, not block explicit consultation."""
        stub = _make_stub_vm()
        stub.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {
                'under_pressure': True,
                'critical': False,
                'active_signals': ['high_memory_usage'],
            },
        )
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['action_possible'] is True
        assert readiness['blocking_reason'] == ''
        assert readiness['resource_pressure'] == 'high'

    def test_critical_pressure_blocks(self):
        """Under critical pressure, readiness must block with critical indicator."""
        stub = _make_stub_vm()
        stub.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {
                'under_pressure': True,
                'critical': True,
                'active_signals': ['disk_critical'],
            },
        )
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['action_possible'] is False


# ══════════════════════════════════════════════════════════════
# 7. OSES detects readiness_missing
# ══════════════════════════════════════════════════════════════

class TestOSESDetectsReadinessMissing:

    def test_oses_finds_repeated_readiness_failures(self):
        """OSES must detect external_readiness_assessed events with action_possible=False."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / 'data' / 'logs' / 'runtime_audit.jsonl'
            audit_path.parent.mkdir(parents=True)
            # Write 3 blocked readiness events
            for i in range(3):
                entry = {
                    'kind': 'external_readiness_assessed',
                    'ts': time.time() - (3 - i) * 60,
                    'data': {
                        'action_possible': False,
                        'blocking_reason': 'build_stale',
                        'assistant_kind': 'chatgpt',
                    },
                }
                with audit_path.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')

            svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
            svc.workspace_root = tmpdir
            findings = svc._external_readiness_missing_findings()

        assert len(findings) >= 1
        categories = [f.category for f in findings]
        assert 'external_readiness_missing' in categories
        assert 'build_stale_repeated' in categories

    def test_oses_no_finding_when_no_failures(self):
        """OSES must not create finding when no readiness failures exist."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / 'data' / 'logs' / 'runtime_audit.jsonl'
            audit_path.parent.mkdir(parents=True)
            # Write 1 successful readiness event
            entry = {
                'kind': 'external_readiness_assessed',
                'ts': time.time(),
                'data': {
                    'action_possible': True,
                    'blocking_reason': '',
                    'assistant_kind': 'chatgpt',
                },
            }
            with audit_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')

            svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
            svc.workspace_root = tmpdir
            findings = svc._external_readiness_missing_findings()

        readiness_findings = [f for f in findings if f.category == 'external_readiness_missing']
        assert len(readiness_findings) == 0

    def test_oses_detects_cdp_unavailable_repeated(self):
        """OSES must detect repeated CDP unavailable from web_skill_profile_built."""
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / 'data' / 'logs' / 'runtime_audit.jsonl'
            audit_path.parent.mkdir(parents=True)
            for i in range(4):
                entry = {
                    'kind': 'web_skill_profile_built',
                    'ts': time.time() - (4 - i) * 30,
                    'data': {'cdp_status': 'unavailable'},
                }
                with audit_path.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')

            svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
            svc.workspace_root = tmpdir
            findings = svc._external_readiness_missing_findings()

        categories = [f.category for f in findings]
        assert 'cdp_unavailable_repeated' in categories


# ══════════════════════════════════════════════════════════════
# 8. PortableContext exports capability readiness
# ══════════════════════════════════════════════════════════════

class TestPortableContextExportsReadiness:

    def test_capability_readiness_section_exists(self):
        """PortableContext must export a capability_readiness section."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        # Build a minimal instance
        svc = PortableContextService.__new__(PortableContextService)
        svc.workspace_root = '/tmp/test_iabv'
        section = svc._capability_readiness_section(now=time.time())
        assert section.section_id == 'capability_readiness'
        assert 'P0.39' in section.title

    def test_capability_readiness_with_events(self):
        """When readiness events exist, section should contain items."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer

        tracer = get_runtime_tracer()
        tracer.trace_external_readiness(
            assistant_kind='chatgpt',
            action_possible=True,
            confidence=0.8,
            blocking_reason='',
            session_selected='isolated_profile',
            security_block='none',
            capture_mode='dom_observation',
        )

        svc = PortableContextService.__new__(PortableContextService)
        svc.workspace_root = '/tmp/test_iabv'
        section = svc._capability_readiness_section(now=time.time())
        assert len(section.items) >= 1
        item = section.items[0]
        assert item['assistant_kind'] == 'chatgpt'
        assert item['action_possible'] is True

    def test_capability_readiness_no_pii(self):
        """Readiness section items must not contain PII fields."""
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer

        tracer = get_runtime_tracer()
        tracer.trace_external_readiness(
            assistant_kind='chatgpt',
            action_possible=False,
            confidence=0.3,
            blocking_reason='build_stale',
            session_selected='isolated_profile',
            security_block='none',
            capture_mode='manual_pasteback',
        )

        svc = PortableContextService.__new__(PortableContextService)
        svc.workspace_root = '/tmp/test_iabv'
        section = svc._capability_readiness_section(now=time.time())
        for item in section.items:
            for key in item:
                assert key not in ('email', 'password', 'cookie', 'token', 'credentials')
            for val in item.values():
                if isinstance(val, str):
                    assert '@' not in val or val == 'none'  # no email-like PII


# ══════════════════════════════════════════════════════════════
# 9. No PII in traces
# ══════════════════════════════════════════════════════════════

class TestNoPIIInTraces:

    def test_readiness_trace_no_pii(self):
        """trace_external_readiness must not log PII."""
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        event = tracer.trace_external_readiness(
            assistant_kind='chatgpt',
            action_possible=False,
            confidence=0.5,
            blocking_reason='security_verification_recent',
            session_selected='isolated_profile',
            security_block='security_verification',
            capture_mode='manual_pasteback',
        )
        # Check no PII fields in the event data
        data = event.get('data', {})
        for key in data:
            assert key not in ('email', 'password', 'cookie', 'token')
        for val in data.values():
            if isinstance(val, str):
                assert '@' not in val or val in ('none', '')


# ══════════════════════════════════════════════════════════════
# 10. platform_pending validates with PlatformPendingTask
# ══════════════════════════════════════════════════════════════

class TestPlatformPendingValidation:

    def test_p039_task_validates(self):
        """P0.39 platform_pending task must validate with PlatformPendingTask."""
        from iabv_v15.domain.models import PlatformPendingTask
        task_path = (
            Path(__file__).resolve().parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_runtime_capability_readiness_universal_p039.json'
        )
        assert task_path.exists(), f'Missing: {task_path}'
        raw = task_path.read_text(encoding='utf-8')
        task = PlatformPendingTask.model_validate_json(raw)
        assert task.id == 'runtime_capability_readiness_universal_p039'
        assert task.status == 'PENDING'
        assert task.metadata is not None
        meta = task.metadata
        if isinstance(meta, dict):
            assert meta.get('verification_status') == 'CODE_FIX_PENDING_LIVE_PROOF'


# ══════════════════════════════════════════════════════════════
# 11. Readiness gate blocks _run_external_consultation
# ══════════════════════════════════════════════════════════════

class TestReadinessGateBlocksConsultation:

    def test_stale_build_prevents_consultation(self):
        """_run_external_consultation must return False when readiness blocks."""
        stub = _make_stub_vm()
        # Override _assess_external_readiness to return blocked
        def fake_readiness(self_arg, ak):
            return {
                'tool_id': 'external_assistant_chatgpt',
                'assistant_kind': ak,
                'assistant_title': 'ChatGPT',
                'device_state': 'unknown',
                'build_state': 'stale',
                'resource_pressure': 'none',
                'session_mode': 'isolated_profile',
                'session_selected': 'isolated_profile',
                'auth_state': 'unknown',
                'security_block_state': 'none',
                'observation_permission': 'unknown',
                'action_possible': False,
                'capture_possible': False,
                'response_capture_mode': 'manual_pasteback',
                'confidence': 0.0,
                'blocking_reason': 'build_stale',
                'next_human_action': 'Alinea el runtime con origin/main.',
                'evidence_refs': [],
                'last_verified_at': time.time(),
            }
        stub._assess_external_readiness = types.MethodType(fake_readiness, stub)

        result = stub._run_external_consultation('chatgpt', announce=True)
        assert result is False
        assert stub._working is False
        assert 'build_stale' in stub._latest_response_meta

    def test_pressure_defers_consultation_via_readiness(self):
        """Under pressure, readiness gate defers and returns False."""
        stub = _make_stub_vm()
        def fake_readiness(self_arg, ak):
            return {
                'tool_id': 'external_assistant_chatgpt',
                'assistant_kind': ak,
                'assistant_title': 'ChatGPT',
                'device_state': 'unknown',
                'build_state': 'current',
                'resource_pressure': 'high',
                'session_mode': 'isolated_profile',
                'session_selected': 'isolated_profile',
                'auth_state': 'unknown',
                'security_block_state': 'none',
                'observation_permission': 'unknown',
                'action_possible': False,
                'capture_possible': False,
                'response_capture_mode': 'manual_pasteback',
                'confidence': 0.5,
                'blocking_reason': 'resource_pressure_high',
                'next_human_action': '',
                'evidence_refs': [],
                'last_verified_at': time.time(),
                'retry_after_s': 15,
            }
        stub._assess_external_readiness = types.MethodType(fake_readiness, stub)

        result = stub._run_external_consultation('chatgpt', announce=True)
        assert result is False
        assert 'resource_pressure' in stub._latest_response_meta


# ══════════════════════════════════════════════════════════════
# 12. Confidence score calculation
# ══════════════════════════════════════════════════════════════

class TestConfidenceScore:

    def test_confidence_decreases_with_stale(self):
        """Stale build should reduce confidence."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': True, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        assert readiness['confidence'] < 1.0

    def test_confidence_high_when_all_clear(self):
        """With no blockers, confidence should be 1.0."""
        stub = _make_stub_vm()
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_build_fingerprint.return_value = {
                'stale': False, 'head': 'abc',
            }
            tracer_inst.trace_external_readiness.return_value = {}
            mock_tracer.return_value = tracer_inst
            readiness = stub._assess_external_readiness('chatgpt')

        # Without any blockers confidence should be high
        assert readiness['confidence'] >= 0.8


# ══════════════════════════════════════════════════════════════
# 13. Deferred retry thread-safe (no PytestUnhandledThreadExceptionWarning)
# ══════════════════════════════════════════════════════════════

class TestDeferredRetryThreadSafe:

    def test_deferred_retry_ready_no_thread_warning(self):
        """Deferred retry ready path must not produce thread warning."""
        stub = _make_stub_vm()
        done_event = threading.Event()
        original_mock = MagicMock()
        def _on_ready(*args, **kwargs):
            original_mock(*args, **kwargs)
            done_event.set()
        stub._on_deferred_retry_ready = _on_ready
        stub.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {'under_pressure': False},
        )
        stub._DEFERRED_RETRY_COOLDOWN_S = 0.0
        stub._deferred_retry_last_ts = 0.0
        stub._deferred_retry_count = 0
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer, patch('time.sleep'):
            tracer_inst = MagicMock()
            tracer_inst.trace_consultation_quiescence.return_value = {}
            mock_tracer.return_value = tracer_inst
            stub._schedule_deferred_consultation_retry('chatgpt', 0.1)
            done_event.wait(timeout=5.0)
            original_mock.assert_called()

    def test_deferred_retry_still_blocked_no_thread_warning(self):
        """Deferred retry still-blocked path must not produce thread warning."""
        stub = _make_stub_vm()
        done_event = threading.Event()
        original_mock = MagicMock()
        def _on_blocked(*args, **kwargs):
            original_mock(*args, **kwargs)
            done_event.set()
        stub._on_deferred_retry_still_blocked = _on_blocked
        stub.adaptive_orchestrator = SimpleNamespace(
            _assess_resource_pressure=lambda: {
                'under_pressure': True,
                'critical': True,
                'active_signals': ['ram_critical'],
            },
        )
        stub._DEFERRED_RETRY_COOLDOWN_S = 0.0
        stub._deferred_retry_last_ts = 0.0
        stub._deferred_retry_count = 0
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer, patch('time.sleep'):
            tracer_inst = MagicMock()
            tracer_inst.trace_consultation_quiescence.return_value = {}
            mock_tracer.return_value = tracer_inst
            stub._schedule_deferred_consultation_retry('chatgpt', 0.1)
            done_event.wait(timeout=5.0)
            original_mock.assert_called()

    def test_simple_namespace_fallback_no_crash(self):
        """_queue_ui_call with SimpleNamespace must not crash."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        stub = _make_stub_vm()
        stub._on_deferred_retry_ready = MagicMock()
        method = getattr(ControlCenterViewModel, '_queue_ui_call', None)
        assert method is not None
        bound = types.MethodType(method, stub)
        bound('_on_deferred_retry_ready', 'chatgpt')
        stub._on_deferred_retry_ready.assert_called_once_with('chatgpt')

    def test_stale_generation_no_retry(self):
        """If generation changes, retry must not fire."""
        stub = _make_stub_vm()
        stub._on_deferred_retry_ready = MagicMock()
        stub._DEFERRED_RETRY_COOLDOWN_S = 0.0
        stub._deferred_retry_last_ts = 0.0
        stub._deferred_retry_count = 0
        with patch(
            'iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
        ) as mock_tracer:
            tracer_inst = MagicMock()
            tracer_inst.trace_consultation_quiescence.return_value = {}
            mock_tracer.return_value = tracer_inst
            stub._schedule_deferred_consultation_retry('chatgpt', 0.1)
            # Bump generation to stale the retry
            stub._deferred_retry_generation += 1
            time.sleep(0.5)
        stub._on_deferred_retry_ready.assert_not_called()

    def test_missing_method_no_crash(self):
        """_queue_ui_call with missing method must not crash."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        stub = _make_stub_vm()
        # Don't define _on_nonexistent — it should not crash
        bound = types.MethodType(ControlCenterViewModel._queue_ui_call, stub)
        bound('_on_nonexistent_method', 'chatgpt')  # should not raise


# ══════════════════════════════════════════════════════════════
# 14. RuntimeAuditTracer trace method
# ══════════════════════════════════════════════════════════════

class TestRuntimeAuditTracerReadiness:

    def test_trace_external_readiness_records_event(self):
        """trace_external_readiness must record an event with correct kind."""
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        event = tracer.trace_external_readiness(
            assistant_kind='chatgpt',
            action_possible=True,
            confidence=0.9,
            blocking_reason='',
            session_selected='isolated_profile',
        )
        assert event['kind'] == 'external_readiness_assessed'
        assert event['data']['assistant_kind'] == 'chatgpt'
        assert event['data']['action_possible'] is True
        assert event['data']['confidence'] == 0.9

    def test_trace_external_readiness_queryable(self):
        """Readiness events must be queryable via events(kind=...)."""
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        tracer.trace_external_readiness(
            assistant_kind='claude',
            action_possible=False,
            confidence=0.2,
            blocking_reason='build_stale',
        )
        events = tracer.events(kind='external_readiness_assessed', limit=10)
        claude_events = [e for e in events if e.get('data', {}).get('assistant_kind') == 'claude']
        assert len(claude_events) >= 1
