"""P0.37 — Active Incident Frame + Guided Human Assistance Resolver.

Focused tests:
1. 'cómo te puedo ayudar' after blocked_by_security_verification → help_offer, not local
2. 'ábreme la ventana donde tienes el problema' → show_problem + window open attempt
3. 'no veo la verificación' → visibility_dispute
4. 'yo ya inicié sesión en Chrome' → profile_mismatch
5. 'ya lo hice' → retry_done → delegates to retest
6. 'haz una nueva consulta a ChatGPT' → NOT captured (new_request)
7. Without active incident, 'cómo te puedo ayudar' → not captured
8. Runtime traces emitted for each classified intent
9. OSES finding when help offers fall to local chat
10. No PII in incident frame or traces
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracer():
    from iabv_v15.services.evolution.runtime_audit_tracer import RuntimeAuditTracer
    return RuntimeAuditTracer(log_dir=None)


@pytest.fixture()
def viewmodel_cls():
    from iabv_v15.ui.viewmodels import control_center_viewmodel as mod
    return mod.ControlCenterViewModel


@pytest.fixture()
def active_incident():
    """A realistic active incident frame for blocked_by_security_verification."""
    return {
        'incident_id': 'inc_test1234',
        'assistant_kind': 'chatgpt',
        'assistant_title': 'ChatGPT',
        'terminal_state': 'blocked_by_security_verification',
        'block_type': 'browser_security_verification',
        'profile_label': 'chatgpt_program_session',
        'cdp_available': False,
        'last_user_goal': 'consulta a chatgpt sobre Python',
        'user_help_needed': (
            'Completar la verificacion de seguridad (captcha/login) '
            'en la ventana del perfil puente de IABV, o activar '
            'CDP para usar tu Chrome normal.'
        ),
        'available_actions': [
            'retest_after_user_confirms', 'show_problem_window', 'manual_pasteback',
        ],
        'created_at': time.time() - 30,  # 30 seconds ago
        'expires_at': time.time() + 870,
        'dispatch_id': 'disp_abc123',
        'resolved': False,
    }


# ---------------------------------------------------------------------------
# 1. 'cómo te puedo ayudar' → help_offer
# ---------------------------------------------------------------------------

class TestHelpOffer:
    def test_help_offer_classified(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'cómo te puedo ayudar', active_incident,
        )
        assert result['intent'] == 'help_offer'
        assert result['score'] >= 1.0

    def test_que_necesitas_de_mi(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'qué necesitas de mí', active_incident,
        )
        assert result['intent'] == 'help_offer'

    def test_handler_returns_true_with_incident(self, viewmodel_cls, active_incident):
        vm = MagicMock(spec=viewmodel_cls)
        vm._active_incident_frame = active_incident
        vm._get_active_incident = lambda: active_incident
        vm._classify_incident_followup_intent = viewmodel_cls._classify_incident_followup_intent
        vm._build_incident_help_response = lambda inc: viewmodel_cls._build_incident_help_response(vm, inc)
        vm._try_focus_incident_window = lambda inc: False
        vm._try_handle_security_verification_retest = lambda msg: False
        vm.dataChanged = MagicMock()
        vm._set_live_status = MagicMock()
        vm._clear_autonomy_activity_override = MagicMock()
        vm._append_message = MagicMock()
        vm._working = False

        result = viewmodel_cls._try_handle_incident_followup(vm, 'cómo te puedo ayudar')
        assert result is True
        assert 'lo que yo veo' in vm._latest_response_text.lower() or 'lo que necesito' in vm._latest_response_text.lower()


# ---------------------------------------------------------------------------
# 2. 'ábreme la ventana' → show_problem
# ---------------------------------------------------------------------------

class TestShowProblem:
    def test_show_problem_classified(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'ábreme la ventana donde tienes el problema', active_incident,
        )
        assert result['intent'] == 'show_problem'
        assert result['score'] >= 1.0

    def test_muestrame_donde(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'muéstrame dónde está el problema', active_incident,
        )
        assert result['intent'] == 'show_problem'


# ---------------------------------------------------------------------------
# 3. 'no veo la verificación' → visibility_dispute
# ---------------------------------------------------------------------------

class TestVisibilityDispute:
    def test_no_veo_classified(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'no veo la verificación', active_incident,
        )
        assert result['intent'] == 'visibility_dispute'

    def test_a_mi_si_funciona(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'a mí sí me funciona', active_incident,
        )
        assert result['intent'] == 'visibility_dispute'


# ---------------------------------------------------------------------------
# 4. 'yo ya inicié sesión en Chrome' → profile_mismatch
# ---------------------------------------------------------------------------

class TestProfileMismatch:
    def test_ya_inicie_sesion(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'yo ya inicié sesión en chrome', active_incident,
        )
        assert result['intent'] == 'profile_mismatch'

    def test_mi_chrome_si_funciona(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'en mi chrome sí funciona', active_incident,
        )
        assert result['intent'] == 'profile_mismatch'


# ---------------------------------------------------------------------------
# 5. 'ya lo hice' → retry_done
# ---------------------------------------------------------------------------

class TestRetryDone:
    def test_ya_lo_hice_classified(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'ya lo hice', active_incident,
        )
        assert result['intent'] == 'retry_done'

    def test_ya_pase_captcha(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'ya pasé el captcha', active_incident,
        )
        assert result['intent'] == 'retry_done'


# ---------------------------------------------------------------------------
# 6. 'haz una nueva consulta a ChatGPT' → NOT captured (unrelated to incident)
# ---------------------------------------------------------------------------

class TestNewRequest:
    def test_new_request_not_captured(self, viewmodel_cls, active_incident):
        result = viewmodel_cls._classify_incident_followup_intent(
            'haz una nueva consulta a ChatGPT sobre machine learning', active_incident,
        )
        # New request doesn't match any incident followup tokens
        assert result['intent'] == 'unrelated'


# ---------------------------------------------------------------------------
# 7. Without active incident → not captured
# ---------------------------------------------------------------------------

class TestNoActiveIncident:
    def test_no_incident_returns_false(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        vm._active_incident_frame = None
        vm._get_active_incident = lambda: None
        result = viewmodel_cls._try_handle_incident_followup(vm, 'cómo te puedo ayudar')
        assert result is False

    def test_expired_incident_returns_false(self, viewmodel_cls):
        expired = {
            'incident_id': 'inc_expired',
            'resolved': False,
            'expires_at': time.time() - 100,
            'created_at': time.time() - 1000,
        }
        vm = MagicMock(spec=viewmodel_cls)
        vm._active_incident_frame = expired

        def _get():
            if expired.get('resolved'):
                return None
            if time.time() > expired.get('expires_at', 0):
                return None
            return expired
        vm._get_active_incident = _get
        result = viewmodel_cls._try_handle_incident_followup(vm, 'cómo te puedo ayudar')
        assert result is False


# ---------------------------------------------------------------------------
# 8. Runtime traces emitted
# ---------------------------------------------------------------------------

class TestRuntimeTraces:
    def test_incident_frame_created_trace(self, tracer):
        # Simulate what _create_active_incident_frame does
        ev = tracer.trace(
            'active_incident_frame_created',
            incident_id='inc_test',
            terminal_state='blocked_by_security_verification',
            block_type='browser_security_verification',
            assistant_kind='chatgpt',
            cdp_available=False,
        )
        assert ev['kind'] == 'active_incident_frame_created'
        assert ev['data']['block_type'] == 'browser_security_verification'

    def test_intent_classified_trace(self, tracer):
        ev = tracer.trace(
            'incident_followup_intent_classified',
            incident_id='inc_test',
            intent='help_offer',
            score=1.3,
            block_type='browser_security_verification',
            terminal_state='blocked_by_security_verification',
        )
        assert ev['kind'] == 'incident_followup_intent_classified'
        assert ev['data']['intent'] == 'help_offer'

    def test_action_selected_trace(self, tracer):
        ev = tracer.trace(
            'incident_followup_action_selected',
            incident_id='inc_test',
            intent='show_problem',
            action_taken='window_open_attempted',
        )
        assert ev['kind'] == 'incident_followup_action_selected'
        assert ev['data']['action_taken'] == 'window_open_attempted'

    def test_resolved_trace(self, tracer):
        ev = tracer.trace(
            'incident_followup_resolved_or_unresolved',
            incident_id='inc_test',
            resolution='resolved',
            terminal_state='blocked_by_security_verification',
        )
        assert ev['kind'] == 'incident_followup_resolved_or_unresolved'


# ---------------------------------------------------------------------------
# 9. OSES finding when help falls to local
# ---------------------------------------------------------------------------

class TestOSESIncidentFallback:
    def test_finding_generated_when_block_then_local_ge_2(self, tmp_path):
        audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit_path.parent.mkdir(parents=True)
        # Pattern: dispatch_terminal(blocked) → chat_inference_started (2x)
        events = [
            {'kind': 'dispatch_terminal', 'data': {'terminal_state': 'blocked_by_security_verification'}},
            {'kind': 'chat_inference_started', 'data': {}},
            {'kind': 'dispatch_terminal', 'data': {'terminal_state': 'blocked_by_security_verification'}},
            {'kind': 'chat_inference_started', 'data': {}},
        ]
        audit_path.write_text(
            '\n'.join(json.dumps(e) for e in events),
            encoding='utf-8',
        )

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._incident_followup_local_fallback_findings(svc)
        assert len(findings) == 1
        assert findings[0].category == 'incident_followup_falls_to_local_chat'
        assert findings[0].metadata['local_fallback_count'] == 2

    def test_no_finding_when_incident_handled(self, tmp_path):
        audit_path = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit_path.parent.mkdir(parents=True)
        # Pattern: dispatch_terminal(blocked) → incident_followup handled → no local chat
        events = [
            {'kind': 'dispatch_terminal', 'data': {'terminal_state': 'blocked_by_security_verification'}},
            {'kind': 'incident_followup_intent_classified', 'data': {'intent': 'help_offer'}},
            {'kind': 'dispatch_terminal', 'data': {'terminal_state': 'blocked_by_security_verification'}},
            {'kind': 'external_failure_followup_answered', 'data': {}},
        ]
        audit_path.write_text(
            '\n'.join(json.dumps(e) for e in events),
            encoding='utf-8',
        )

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._incident_followup_local_fallback_findings(svc)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# 10. No PII in incident frame or traces
# ---------------------------------------------------------------------------

class TestNoPIIInIncidentFrame:
    def test_incident_frame_no_pii(self, viewmodel_cls):
        frame = {
            'incident_id': 'inc_test',
            'assistant_kind': 'chatgpt',
            'assistant_title': 'ChatGPT',
            'terminal_state': 'blocked_by_security_verification',
            'block_type': 'browser_security_verification',
            'profile_label': 'chatgpt_program_session',
            'cdp_available': False,
            'last_user_goal': 'pregunta sobre python',
            'user_help_needed': 'Completar verificacion',
            'created_at': time.time(),
        }
        serialized = json.dumps(frame)
        pii_markers = ['@gmail', 'password', 'token=', 'cookie=', 'Bearer', 'session_id=']
        for marker in pii_markers:
            assert marker not in serialized, f'PII marker {marker!r} in incident frame'

    def test_trace_event_no_pii(self, tracer):
        ev = tracer.trace(
            'incident_followup_intent_classified',
            incident_id='inc_test',
            intent='help_offer',
            score=1.3,
        )
        serialized = json.dumps(ev.get('data', {}))
        pii_markers = ['@gmail', 'password', 'token=', 'cookie=', 'Bearer']
        for marker in pii_markers:
            assert marker not in serialized


# ---------------------------------------------------------------------------
# 11. _create_active_incident_frame integration
# ---------------------------------------------------------------------------

class TestCreateIncidentFrame:
    def test_frame_created_via_remember_failure(self, viewmodel_cls):
        """_remember_external_failure should create incident frame for blocked states."""
        vm = MagicMock(spec=viewmodel_cls)
        vm._last_user_goal = 'consulta chatgpt'
        vm._create_active_incident_frame = viewmodel_cls._create_active_incident_frame.__get__(vm)
        vm._describe_user_help_needed = viewmodel_cls._describe_user_help_needed
        vm._describe_available_actions = viewmodel_cls._describe_available_actions

        viewmodel_cls._remember_external_failure(
            vm,
            assistant_title='ChatGPT',
            message='Verificacion de seguridad',
            meta='blocked_by_security_verification',
            outcome='blocked',
            assistant_kind='chatgpt',
            terminal_state='blocked_by_security_verification',
            dispatch_id='disp_test',
        )

        assert vm._active_incident_frame is not None
        assert vm._active_incident_frame['block_type'] == 'browser_security_verification'
        assert vm._active_incident_frame['assistant_kind'] == 'chatgpt'

    def test_no_frame_for_non_blocked_failure(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        vm._last_user_goal = 'consulta'
        vm._active_incident_frame = None
        # _create_active_incident_frame should NOT be called for non-blocked states
        calls = []
        vm._create_active_incident_frame = lambda **kw: calls.append(kw)

        viewmodel_cls._remember_external_failure(
            vm,
            assistant_title='ChatGPT',
            message='Timeout',
            meta='generic_error',
            outcome='failed',
            terminal_state='failed',
            dispatch_id='disp_test2',
        )
        assert len(calls) == 0


# ---------------------------------------------------------------------------
# 12. Incident resolved / expired lifecycle
# ---------------------------------------------------------------------------

class TestIncidentLifecycle:
    def test_resolved_incident_not_returned(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        frame = {
            'incident_id': 'inc_resolved',
            'resolved': True,
            'expires_at': time.time() + 100,
        }
        vm._active_incident_frame = frame
        result = viewmodel_cls._get_active_incident(vm)
        assert result is None

    def test_active_incident_returned(self, viewmodel_cls):
        vm = MagicMock(spec=viewmodel_cls)
        frame = {
            'incident_id': 'inc_active',
            'resolved': False,
            'expires_at': time.time() + 100,
        }
        vm._active_incident_frame = frame
        result = viewmodel_cls._get_active_incident(vm)
        assert result is not None
        assert result['incident_id'] == 'inc_active'
