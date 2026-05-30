"""P0.73 - Semantic Action Binding + Existing UI Focus.

These tests cover the live failure observed on Windows: after ChatGPT was
blocked, the user wrote "usa un navegador mio..." and IABV answered through
the generic failure-followup path instead of selecting a governed browser
action.
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def viewmodel_cls():
    from iabv_v15.ui.viewmodels import control_center_viewmodel as mod
    return mod.ControlCenterViewModel


def _semantic_vm(viewmodel_cls, *, active_incident: dict | None = None):
    vm = MagicMock(spec=viewmodel_cls)
    vm._last_external_failure_payload = {
        'assistant_title': 'ChatGPT',
        'assistant_kind': 'chatgpt',
        'terminal_state': 'failed_with_actionable_reason',
        'dispatch_id': 'dispatch-p073',
        'message': 'Ruta bloqueada para ChatGPT.',
        'meta': 'browser_security_verification',
        'outcome': 'blocked',
    }
    vm._last_external_failure_ts = time.time()
    vm._EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S = viewmodel_cls._EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S
    vm._get_active_incident = MagicMock(return_value=active_incident)
    vm._normalized_command_text = lambda message: viewmodel_cls._normalized_command_text(vm, message)
    vm._explicit_assistant_preference = MagicMock(return_value='')
    vm._assistant_display_name = lambda kind: viewmodel_cls._assistant_display_name(vm, kind)
    vm._classify_external_action_followup = lambda message, **kwargs: viewmodel_cls._classify_external_action_followup(
        vm, message, **kwargs,
    )
    vm._format_human_assist_message = viewmodel_cls._format_human_assist_message
    vm._GOVERNED_LAUNCH_OFFER = viewmodel_cls._GOVERNED_LAUNCH_OFFER
    vm._EXTERNAL_ACTION_BROWSER_TERMS = viewmodel_cls._EXTERNAL_ACTION_BROWSER_TERMS
    vm._EXTERNAL_ACTION_OWNERSHIP_TERMS = viewmodel_cls._EXTERNAL_ACTION_OWNERSHIP_TERMS
    vm._EXTERNAL_ACTION_DO_TERMS = viewmodel_cls._EXTERNAL_ACTION_DO_TERMS
    vm._EXTERNAL_ACTION_SHOW_TERMS = viewmodel_cls._EXTERNAL_ACTION_SHOW_TERMS
    vm._detect_cdp_available = MagicMock(return_value={'available': False, 'error': 'connection_failed'})
    vm._launch_governed_browser_session = MagicMock(return_value={
        'launched': True,
        'cdp_url': 'http://localhost:9223',
        'profile_label': 'iabv_governed_browser_profile',
        'error': '',
    })
    vm._try_focus_incident_window = MagicMock(return_value=False)
    vm._append_message = MagicMock()
    vm._set_live_status = MagicMock()
    vm._clear_autonomy_activity_override = MagicMock()
    vm.dataChanged = MagicMock()
    vm._working = False
    vm._busy_label = ''
    return vm


def test_usa_un_navegador_mio_launches_governed_browser(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    msg = (
        'ok puedes usar un navegador mio con una cuenta de gmail que esta '
        'logueada, analiza bien y haz la consulta busca soluciones'
    )

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        handled = viewmodel_cls._try_handle_external_action_followup(vm, msg)

    assert handled is True
    vm._launch_governed_browser_session.assert_called_once()
    assert 'ventana gobernada' in vm._latest_response_text.lower()
    assert 'external_failure_followup' not in vm._latest_response_meta
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'semantic_action_binding_started' in traced_kinds
    assert 'semantic_action_binding_result' in traced_kinds
    assert 'external_followup_action_executed' in traced_kinds


def test_classifier_binds_gmail_logged_account_to_human_login_available(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    result = viewmodel_cls._classify_external_action_followup(
        vm,
        'usa una cuenta gmail que ya esta logueada para ChatGPT',
        failure_payload=vm._last_external_failure_payload,
    )

    assert result['intent'] == 'human_login_available'
    assert result['confidence'] >= 0.5


def test_show_problem_phrase_still_maps_to_window_action(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls, active_incident={'assistant_kind': 'chatgpt', 'assistant_title': 'ChatGPT'})
    result = viewmodel_cls._classify_external_action_followup(
        vm,
        'muestrame la ventana donde esta el problema',
        active_incident={'assistant_kind': 'chatgpt'},
    )

    assert result['intent'] == 'show_problem_window_requested'


def test_shortcut_launcher_no_longer_exits_silently_on_recent_lock():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    vbs = (root / 'scripts' / 'IABV.vbs').read_text(encoding='utf-8', errors='ignore')
    ps1 = (root / 'scripts' / 'start_iabv.ps1').read_text(encoding='utf-8', errors='ignore')

    assert 'WScript.Quit 0' not in vbs
    assert 'startup_existing_instance_focus_attempted' in ps1
    assert 'focused_existing' in ps1


def test_oses_flags_generic_followup_that_should_have_been_action_binding(tmp_path):
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )

    audit = tmp_path / 'data' / 'logs' / 'runtime_audit.jsonl'
    audit.parent.mkdir(parents=True)
    audit.write_text(json.dumps({
        'kind': 'external_failure_followup_answered',
        'data': {
            'dispatch_id': 'dispatch-p073',
            'user_message': (
                'ok puedes usar un navegador mio con una cuenta gmail logueada '
                'y haz la consulta'
            ),
        },
    }), encoding='utf-8')

    svc = MagicMock(spec=OperationalSelfExaminationService)
    svc.workspace_root = str(tmp_path)
    findings = OperationalSelfExaminationService._human_assist_bridge_findings(svc)
    patterns = {f.metadata.get('pattern') for f in findings}
    assert 'semantic_action_binding_missed' in patterns
