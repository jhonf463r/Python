"""P0.72 — External Consultation Human-Assist Bridge + Governed Browser Launch.

Focused tests for the fixes that close the handoff when ChatGPT blocks with a
security verification, CDP to the user's Chrome is unavailable, or the user
offers help. Core contract: UNA SOLA VENTANA — the user is NEVER told to run a
terminal command (e.g. ``chrome.exe --remote-debugging-port=9222``).

Covers:
1. ChatGPT security verification produces an actionable four-line handoff.
2. "usa mi navegador" with CDP timeout does not ask for a manual command.
3. "muéstrame la ventana" is handled (does not fall to local LLM).
4. Visible fallback is only enabled with human help / explicit policy.
5. External adapter never declares success without response_captured.
6. ActiveIncidentFrame without hwnd marks security_window_unbound.
7. OSES detects repeated CDP-unavailable while user keeps asking for browser.
8. PortableContext exports human_assist_bridge_status.
9. UNA SOLA VENTANA respected: no "--remote-debugging-port=9222" instruction.
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def viewmodel_cls():
    from iabv_v15.ui.viewmodels import control_center_viewmodel as mod
    return mod.ControlCenterViewModel


@pytest.fixture()
def tracer_mock():
    return MagicMock()


def _security_incident() -> dict:
    return {
        'incident_id': 'inc-p072-1',
        'assistant_kind': 'chatgpt',
        'assistant_title': 'ChatGPT',
        'block_type': 'browser_security_verification',
        'terminal_state': 'blocked_by_security_verification',
        'profile_label': 'chatgpt_program_session',
        'user_help_needed': 'completar la verificación de seguridad',
        'launch_target': 'https://chatgpt.com/',
        'target_window_title': '',
        'hwnd_available': False,
        'cdp_available': False,
        'created_at': time.time(),
        'available_actions': ['show_problem_window', 'switch_to_user_chrome_cdp'],
    }


def _make_followup_vm(viewmodel_cls, incident, *, window_opened=False):
    vm = MagicMock(spec=viewmodel_cls)
    vm._get_active_incident = MagicMock(return_value=incident)
    vm._classify_incident_followup_intent = viewmodel_cls._classify_incident_followup_intent
    vm._format_human_assist_message = viewmodel_cls._format_human_assist_message
    vm._GOVERNED_LAUNCH_OFFER = viewmodel_cls._GOVERNED_LAUNCH_OFFER
    vm._try_focus_incident_window = MagicMock(return_value=window_opened)
    vm._record_show_window_learning = MagicMock()
    vm._build_incident_help_response = MagicMock(return_value='help')
    vm._launch_governed_browser_session = MagicMock(return_value={
        'launched': True, 'cdp_url': 'http://localhost:9223',
        'profile_label': 'iabv_governed_browser_profile', 'error': '',
    })
    vm._append_message = MagicMock()
    vm._set_live_status = MagicMock()
    vm._clear_autonomy_activity_override = MagicMock()
    vm.dataChanged = MagicMock()
    vm._working = False
    vm._busy_label = ''
    return vm


# ---------------------------------------------------------------------------
# 1 + 6 + 9. security verification → four-line handoff, window_unbound trace
# ---------------------------------------------------------------------------

class TestSecurityVerificationHandoff:
    def test_show_problem_no_window_offers_governed_launch(self, viewmodel_cls, tracer_mock):
        incident = _security_incident()
        vm = _make_followup_vm(viewmodel_cls, incident, window_opened=False)

        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer_mock):
            handled = viewmodel_cls._try_handle_incident_followup(vm, 'muéstrame la ventana')

        assert handled is True
        msg = vm._latest_response_text
        # Four-line actionable contract.
        assert msg.startswith('IABV ve:')
        assert 'IABV no puede verificar:' in msg
        assert 'Lo que necesito de ti:' in msg
        assert 'Acción que puedo hacer ahora:' in msg
        # UNA SOLA VENTANA: no command instruction.
        assert '--remote-debugging-port' not in msg
        assert 'chrome.exe' not in msg.lower()
        # Task F: security_window_unbound trace emitted.
        tracer_mock.trace_security_window_unbound.assert_called_once()
        tracer_mock.trace_governed_browser_session.assert_called()

    def test_show_problem_handled_not_local_llm(self, viewmodel_cls, tracer_mock):
        """Task C: 'muéstrame la ventana' must be handled, not fall to LLM."""
        incident = _security_incident()
        vm = _make_followup_vm(viewmodel_cls, incident, window_opened=True)

        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer_mock):
            handled = viewmodel_cls._try_handle_incident_followup(vm, 'muéstrame la ventana')

        assert handled is True
        vm._append_message.assert_called_once()


# ---------------------------------------------------------------------------
# 2 + 9. "usa mi navegador" / "usar mi chrome" with CDP timeout — no command
# ---------------------------------------------------------------------------

class TestCDPUnavailableNoCommand:
    def test_usar_mi_chrome_cdp_timeout_offers_governed_window(self, viewmodel_cls, tracer_mock):
        vm = MagicMock(spec=viewmodel_cls)
        vm._CHROME_BRIDGE_PATTERNS = viewmodel_cls._CHROME_BRIDGE_PATTERNS
        vm._verify_chrome_bridge_capability = MagicMock(return_value=True)
        vm._format_human_assist_message = viewmodel_cls._format_human_assist_message
        vm._GOVERNED_LAUNCH_OFFER = viewmodel_cls._GOVERNED_LAUNCH_OFFER
        vm._detect_cdp_available = MagicMock(return_value={
            'available': False, 'cdp_url': 'http://localhost:9222',
            'browser_version': '', 'error': 'connection_failed: timed out',
        })
        vm._append_message = MagicMock()
        vm.dataChanged = MagicMock()

        os.environ.pop('IABV_PREFER_CDP_SESSION', None)
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer_mock):
            handled = viewmodel_cls._try_handle_user_chrome_bridge_selection(vm, 'usar mi chrome')

        assert handled is True
        msg = vm._latest_response_text
        assert '--remote-debugging-port' not in msg
        assert 'chrome.exe' not in msg.lower()
        assert 'gobernada' in msg.lower()
        # Did not silently enable CDP preference.
        assert os.environ.get('IABV_PREFER_CDP_SESSION') != '1'
        tracer_mock.trace_governed_browser_session.assert_called()


# ---------------------------------------------------------------------------
# 3. do_it_yourself ("hazlo tú") opens governed window, not local LLM
# ---------------------------------------------------------------------------

class TestDoItYourself:
    def test_hazlo_tu_launches_governed_window(self, viewmodel_cls, tracer_mock):
        incident = _security_incident()
        vm = _make_followup_vm(viewmodel_cls, incident)

        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer_mock):
            handled = viewmodel_cls._try_handle_incident_followup(vm, 'hazlo tú')

        assert handled is True
        vm._launch_governed_browser_session.assert_called_once()
        msg = vm._latest_response_text
        assert msg.startswith('IABV ve:')
        assert '--remote-debugging-port' not in msg

    def test_hazlo_t_degraded_encoding_launches_governed_window(self, viewmodel_cls, tracer_mock):
        incident = _security_incident()
        vm = _make_followup_vm(viewmodel_cls, incident)

        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer_mock):
            handled = viewmodel_cls._try_handle_incident_followup(vm, 'hazlo t?')

        assert handled is True
        vm._launch_governed_browser_session.assert_called_once()
        assert vm._latest_response_meta.startswith('incident_followup')

    def test_classifier_recognizes_governed_window_phrase(self, viewmodel_cls):
        incident = _security_incident()
        res = viewmodel_cls._classify_incident_followup_intent(
            'abre la ventana gobernada', incident,
        )
        assert res['intent'] == 'do_it_yourself'


# ---------------------------------------------------------------------------
# 4. Visible fallback gated on human help / policy
# ---------------------------------------------------------------------------

class TestVisibleFallbackGating:
    def _adapter(self):
        from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter
        return ExternalAssistantToolAdapter()

    def _card_task(self, *, task_meta=None, card_meta=None):
        from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
        card = ToolCard(
            tool_id='chatgpt_web_assisted', title='ChatGPT', tool_type=ToolType.LLM_WEB_UI,
            adapter_key='external_assistant', metadata=card_meta or {},
        )
        task = ToolTask(
            tool_id='chatgpt_web_assisted', title='consulta', objective='hola',
            metadata=task_meta or {},
        )
        return card, task

    def test_silent_by_default(self):
        adapter = self._adapter()
        card, task = self._card_task()
        allowed, policy = adapter._visible_fallback_allowed(
            card=card, task=task, fallback_error='browser_security_verification',
        )
        assert allowed is False
        assert policy == 'silent_default'

    def test_allowed_when_user_offered_help(self):
        adapter = self._adapter()
        card, task = self._card_task(task_meta={'visible_fallback_requested': True})
        allowed, policy = adapter._visible_fallback_allowed(
            card=card, task=task, fallback_error='browser_security_verification',
        )
        assert allowed is True
        assert policy == 'user_offered_help'

    def test_allowed_when_policy_active(self):
        adapter = self._adapter()
        card, task = self._card_task(
            task_meta={'visible_fallback_policy': 'when_security_verification_show_window_first'},
        )
        allowed, policy = adapter._visible_fallback_allowed(
            card=card, task=task, fallback_error='browser_security_verification',
        )
        assert allowed is True
        assert policy == 'when_security_verification_show_window_first'


# ---------------------------------------------------------------------------
# 5. External adapter never declares success without response_captured
# ---------------------------------------------------------------------------

class TestNoSuccessWithoutCapture:
    def test_security_verification_block_is_not_success(self):
        from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter
        from iabv_v15.domain.models import ToolCard, ToolTask, ToolType

        adapter = ExternalAssistantToolAdapter()
        card = ToolCard(
            tool_id='chatgpt_web_assisted', title='ChatGPT',
            tool_type=ToolType.LLM_WEB_UI, adapter_key='external_assistant',
            metadata={
                'launch_mode': 'web_assisted',
                'web_url': 'https://chatgpt.com/',
                'response_capture_mode': 'dom_capture',
                'assistant_kind': 'chatgpt',
            },
        )
        task = ToolTask(
            tool_id='chatgpt_web_assisted', title='consulta', objective='hola',
            metadata={'response_capture_mode': 'dom_capture'},
        )
        adapter._capture_desktop_response = MagicMock(return_value={
            'response_captured': False,
            'error_message': 'browser_security_verification',
            'focused_title': 'Just a moment...',
            'metadata': {},
        })

        result = adapter.run(card, task, sandbox=False)
        assert result['success'] is False
        assert result['metadata'].get('response_captured') in (False, None)


# ---------------------------------------------------------------------------
# 7. OSES: repeated CDP-unavailable while user keeps requesting browser
# ---------------------------------------------------------------------------

class TestOSESCDPUnavailableRepeated:
    def test_finding_emitted_when_cdp_unavailable_ge_2(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        audit = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit.parent.mkdir(parents=True)
        lines = []
        for _ in range(3):
            lines.append(json.dumps({
                'kind': 'user_browser_cdp_unavailable',
                'data': {'assistant_kind': 'chatgpt'},
            }))
        audit.write_text('\n'.join(lines), encoding='utf-8')

        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._human_assist_bridge_findings(svc)
        cats = {f.metadata.get('pattern') for f in findings}
        assert 'cdp_unavailable_user_keeps_requesting_browser' in cats

    def test_command_violation_detected(self, tmp_path):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        audit = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
        audit.parent.mkdir(parents=True)
        audit.write_text(json.dumps({
            'kind': 'assistant_response',
            'data': {'text': 'abre chrome con --remote-debugging-port=9222'},
        }), encoding='utf-8')

        svc = MagicMock(spec=OperationalSelfExaminationService)
        svc.workspace_root = str(tmp_path)
        findings = OperationalSelfExaminationService._human_assist_bridge_findings(svc)
        patterns = {f.metadata.get('pattern') for f in findings}
        assert 'command_instruction_violated_single_window_principle' in patterns


# ---------------------------------------------------------------------------
# 8. PortableContext exports human_assist_bridge_status
# ---------------------------------------------------------------------------

class TestPortableContextExport:
    def test_section_exposes_bridge_status(self):
        import types
        from datetime import datetime, timezone
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        svc = MagicMock(spec=PortableContextService)
        svc._section = types.MethodType(PortableContextService._section, svc)

        tracer = MagicMock()
        tracer.events = MagicMock(return_value=[])
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer',
                   return_value=tracer):
            section = PortableContextService._human_assist_bridge_section(
                svc, now=datetime.now(timezone.utc),
            )

        assert section.section_id == 'human_assist_bridge'
        item = section.items[0]
        assert 'human_assist_bridge_status' in item
        assert 'cdp_bridge_status' in item
        assert 'visible_fallback_policy' in item
        assert 'last_external_consultation_failure' in item
