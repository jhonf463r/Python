"""P0.73 - Semantic Action Binding + Existing UI Focus.

These tests cover the live failure observed on Windows: after ChatGPT was
blocked, the user wrote "usa un navegador mio..." and IABV answered through
the generic failure-followup path instead of selecting a governed browser
action.
"""

from __future__ import annotations

import json
import time
import types
import uuid
from types import SimpleNamespace
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
    vm._classify_incident_followup_intent = lambda message, incident: viewmodel_cls._classify_incident_followup_intent(
        message, incident,
    )
    vm._classify_external_action_followup = lambda message, **kwargs: viewmodel_cls._classify_external_action_followup(
        vm, message, **kwargs,
    )
    vm._format_human_assist_message = viewmodel_cls._format_human_assist_message
    vm._GOVERNED_LAUNCH_OFFER = viewmodel_cls._GOVERNED_LAUNCH_OFFER
    vm._EXTERNAL_ACTION_BROWSER_TERMS = viewmodel_cls._EXTERNAL_ACTION_BROWSER_TERMS
    vm._EXTERNAL_ACTION_OWNERSHIP_TERMS = viewmodel_cls._EXTERNAL_ACTION_OWNERSHIP_TERMS
    vm._EXTERNAL_ACTION_DO_TERMS = viewmodel_cls._EXTERNAL_ACTION_DO_TERMS
    vm._EXTERNAL_ACTION_SHOW_TERMS = viewmodel_cls._EXTERNAL_ACTION_SHOW_TERMS
    vm._BROWSER_APP_TOKENS = viewmodel_cls._BROWSER_APP_TOKENS
    vm._ASSISTANT_WINDOW_TOKENS = viewmodel_cls._ASSISTANT_WINDOW_TOKENS
    vm._SECURITY_RETEST_PATTERNS = viewmodel_cls._SECURITY_RETEST_PATTERNS
    vm._detect_cdp_available = MagicMock(return_value={'available': False, 'error': 'connection_failed'})
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(active_windows=[]))
    vm._browser_session_inventory = lambda **kwargs: viewmodel_cls._browser_session_inventory(vm, **kwargs)
    vm._format_browser_inventory_summary = viewmodel_cls._format_browser_inventory_summary
    vm._focus_existing_browser_from_inventory = MagicMock(return_value={'focused': False, 'error': 'no_hwnd_candidate'})
    vm._launch_governed_browser_session = MagicMock(return_value={
        'launched': True,
        'cdp_url': 'http://localhost:9223',
        'profile_label': 'iabv_governed_browser_profile',
        'error': '',
    })
    vm._try_focus_incident_window = MagicMock(return_value=False)
    vm._record_show_window_learning = MagicMock()
    vm._append_message = MagicMock()
    vm._set_live_status = MagicMock()
    vm._clear_autonomy_activity_override = MagicMock()
    vm._clear_external_failure_memory = MagicMock()
    vm._resolve_incident_frame = MagicMock()
    vm.dataChanged = MagicMock()
    vm._working = False
    vm._busy_label = ''
    vm._latest_response_text = ''
    vm._latest_response_meta = ''
    vm._last_adaptive_payload = {}
    vm._last_user_goal = 'has una consulta a ChatGPT: responde solo S si entiendes'
    vm._last_visible_browser_surface = {}
    vm._sanitize_visible_response_text = viewmodel_cls._sanitize_visible_response_text
    vm._visible_response_text_looks_useful = viewmodel_cls._visible_response_text_looks_useful
    vm._restore_clipboard_text = MagicMock()
    vm._attempt_visible_user_browser_response_capture = lambda **kwargs: viewmodel_cls._attempt_visible_user_browser_response_capture(
        vm, **kwargs,
    )
    vm._attempt_visible_user_browser_prompt_send = lambda **kwargs: viewmodel_cls._attempt_visible_user_browser_prompt_send(
        vm, **kwargs,
    )
    vm._run_external_consultation = MagicMock(return_value=True)
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


def test_user_browser_request_prefers_existing_visible_window(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[
            SimpleNamespace(
                title='ChatGPT - Google Chrome',
                app_name='chrome.exe',
                pid=1234,
                focused=False,
                metadata={'hwnd': 4567},
            ),
        ],
    ))
    vm._browser_session_inventory = lambda **kwargs: viewmodel_cls._browser_session_inventory(vm, **kwargs)
    vm._format_browser_inventory_summary = viewmodel_cls._format_browser_inventory_summary
    vm._focus_existing_browser_from_inventory = MagicMock(return_value={
        'focused': True,
        'selected_window': {'title': 'ChatGPT - Google Chrome', 'hwnd': 4567},
        'method': 'win32_hwnd',
        'error': '',
    })
    msg = 'usa mi navegador que ya tiene gmail logueado para hacer la consulta'

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        handled = viewmodel_cls._try_handle_external_action_followup(vm, msg)

    assert handled is True
    vm._focus_existing_browser_from_inventory.assert_called_once()
    vm._launch_governed_browser_session.assert_not_called()
    assert 'existing_browser_focused' in vm._latest_response_meta
    assert 'lo traje al frente' in vm._latest_response_text
    assert 'sin CDP/puente' in vm._latest_response_text
    assert vm._last_visible_browser_surface['surface'] == 'existing_browser_visible'


def test_browser_inventory_reports_background_process_without_visible_window(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[],
        background_processes=[
            SimpleNamespace(process_name='msedge', pid=10636, state='ok', memory_mb=250.0),
        ],
    ))

    inventory = viewmodel_cls._browser_session_inventory(
        vm,
        assistant_kind='chatgpt',
        cdp_probe={'available': False, 'error': 'connection_failed'},
    )
    summary = viewmodel_cls._format_browser_inventory_summary(inventory)

    assert inventory['candidate_count'] == 0
    assert inventory['browser_process_count'] == 1
    assert inventory['recommended_strategy'] == 'existing_browser_process_without_visible_window'
    assert 'browser_processes_exist_without_top_level_window' in inventory['limitations']
    assert 'procesos de navegador sin ventana visible' in summary


def test_user_browser_process_launches_default_browser_before_governed(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[],
        background_processes=[
            SimpleNamespace(process_name='msedge', pid=10636, state='ok', memory_mb=250.0),
        ],
    ))
    vm._launch_user_default_browser_visible_session = MagicMock(return_value={
        'launched': True,
        'launch_target': 'https://chatgpt.com/',
        'surface': 'user_default_browser_visible',
        'semantic_bridge': 'none',
        'error': '',
    })
    msg = 'usa mi navegador normal con la cuenta abierta para hacer la consulta'

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        handled = viewmodel_cls._try_handle_external_action_followup(vm, msg)

    assert handled is True
    vm._launch_user_default_browser_visible_session.assert_called_once()
    vm._launch_governed_browser_session.assert_not_called()
    assert 'user_default_browser_visible_launched' in vm._latest_response_meta
    assert 'navegador normal' in vm._latest_response_text
    assert 'DOM/CDP' in vm._latest_response_text
    assert vm._last_visible_browser_surface['surface'] == 'user_default_browser_visible'


def test_retry_after_visible_browser_launch_sends_prompt_to_same_surface(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'user_default_browser_visible',
        'semantic_bridge': 'none',
        'launch_target': 'https://chatgpt.com/',
    }
    vm._attempt_visible_user_browser_prompt_send = MagicMock(return_value={
        'attempted': True,
        'success': True,
        'status': 'prompt_sent',
        'focused_title': 'ChatGPT - Google Chrome',
        'reason': 'visible_prompt_pasted_and_submitted',
    })
    msg = (
        'ok ahroa has la cosulta que tengas pendiente, analiza si puede usar '
        'bien el chatgp y si puedes en segundo plano mejor'
    )

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        handled = viewmodel_cls._try_handle_external_action_followup(vm, msg)

    assert handled is True
    vm._attempt_visible_user_browser_prompt_send.assert_called_once()
    vm._run_external_consultation.assert_not_called()
    assert 'visible_prompt_sent' in vm._latest_response_meta
    assert 'ya envi' in vm._latest_response_text.lower()
    assert 'chat local' in vm._latest_response_text.lower()
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'semantic_action_binding_result' in traced_kinds
    assert any(
        call.kwargs.get('action_taken') == 'send_prompt_to_visible_browser_surface'
        for call in tracer.trace.call_args_list
    )


def test_retry_after_visible_browser_launch_unresolved_does_not_blind_retry(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'existing_browser_visible',
        'semantic_bridge': 'none',
        'selected_window': {'title': 'ChatGPT - Google Chrome'},
    }
    vm._attempt_visible_user_browser_prompt_send = MagicMock(return_value={
        'attempted': True,
        'success': False,
        'status': 'target_missing',
        'reason': 'visible_browser_window_not_focusable',
        'unresolved_fields': ['focusable_browser_window'],
    })
    msg = 'has la cosulta pendiente en chatgp'

    handled = viewmodel_cls._try_handle_external_action_followup(vm, msg)

    assert handled is True
    vm._attempt_visible_user_browser_prompt_send.assert_called_once()
    vm._run_external_consultation.assert_not_called()
    assert 'visible_prompt_unresolved' in vm._latest_response_meta
    assert 'no pude enfocarla' in vm._latest_response_text


def test_classifier_binds_typo_consultation_to_retry_with_context(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    result = viewmodel_cls._classify_external_action_followup(
        vm,
        'ok ahroa has la cosulta pendiente en chatgp en segundo plano',
        failure_payload=vm._last_external_failure_payload,
    )

    assert result['intent'] == 'retry_external_consultation_requested'
    assert result['confidence'] >= 0.50


def test_visible_prompt_send_focuses_title_when_world_model_has_no_hwnd(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'user_default_browser_visible',
        'semantic_bridge': 'none',
        'selected_window': {'title': 'ChatGPT - Google Chrome'},
    }
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[
            SimpleNamespace(
                title='ChatGPT - Google Chrome',
                app_name='chrome.exe',
                pid=3796,
                focused=False,
                metadata={},
            ),
        ],
        background_processes=[],
    ))
    runner = MagicMock()
    runner.read_clipboard_text.return_value = 'clipboard anterior'
    runner._wait_and_focus_any_window.return_value = 'ChatGPT - Google Chrome'

    with (
        patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer),
        patch('iabv_v15.services.tools.ui_execution_runner.UIExecutionRunner', return_value=runner),
    ):
        result = viewmodel_cls._attempt_visible_user_browser_prompt_send(
            vm,
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            prompt_text='responde solo S si entiendes',
        )

    assert result['success'] is True
    assert result['status'] == 'prompt_sent'
    assert result['focused_title'] == 'ChatGPT - Google Chrome'
    runner._paste_text.assert_called_once_with('responde solo S si entiendes')
    runner._send_virtual_key.assert_called_once_with(0x0D)
    vm._restore_clipboard_text.assert_called_once_with('clipboard anterior')
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'visible_prompt_send_started' in traced_kinds
    assert 'visible_prompt_send_result' in traced_kinds


def test_security_retest_captures_visible_browser_response_before_governed_retest(viewmodel_cls):
    tracer = MagicMock()
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'existing_browser_visible',
        'selected_window': {'title': 'ChatGPT - Microsoft Edge', 'hwnd': 777},
        'semantic_bridge': 'none',
    }
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[
            SimpleNamespace(
                title='ChatGPT - Microsoft Edge',
                app_name='msedge.exe',
                pid=123,
                focused=False,
                metadata={'hwnd': 777},
            ),
        ],
        background_processes=[],
    ))
    vm._focus_existing_browser_from_inventory = MagicMock(return_value={
        'focused': True,
        'selected_window': {'title': 'ChatGPT - Microsoft Edge', 'hwnd': 777},
        'method': 'win32_hwnd',
    })
    runner = MagicMock()
    runner.read_clipboard_text.return_value = 'texto previo'
    runner.copy_active_window_text.return_value = 'ChatGPT\nS'

    with (
        patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer),
        patch('iabv_v15.services.tools.ui_execution_runner.UIExecutionRunner', return_value=runner),
    ):
        handled = viewmodel_cls._try_handle_security_verification_retest(vm, 'ya lo hice')

    assert handled is True
    assert 'response_captured' in vm._latest_response_meta
    assert 'sin leer cookies/tokens/credenciales' in vm._latest_response_text
    vm._clear_external_failure_memory.assert_called_once()
    vm._resolve_incident_frame.assert_called_once_with('resolved')
    runner.copy_active_window_text.assert_called_once_with(select_all=True, settle_seconds=0.18)
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'visible_response_capture_started' in traced_kinds
    assert 'visible_response_capture_result' in traced_kinds
    assert 'semantic_capture_ladder_result' in traced_kinds


def test_security_retest_visible_capture_unreadable_does_not_run_blind_governed_retest(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'existing_browser_visible',
        'selected_window': {'title': 'ChatGPT - Microsoft Edge', 'hwnd': 777},
        'semantic_bridge': 'none',
    }
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[
            SimpleNamespace(
                title='ChatGPT - Microsoft Edge',
                app_name='msedge.exe',
                pid=123,
                focused=False,
                metadata={'hwnd': 777},
            ),
        ],
        background_processes=[],
    ))
    vm._focus_existing_browser_from_inventory = MagicMock(return_value={
        'focused': True,
        'selected_window': {'title': 'ChatGPT - Microsoft Edge', 'hwnd': 777},
    })
    runner = MagicMock()
    runner.read_clipboard_text.return_value = 'texto previo'
    runner.copy_active_window_text.return_value = 'IABV procesando'
    vm._bg_pool = MagicMock()

    with patch('iabv_v15.services.tools.ui_execution_runner.UIExecutionRunner', return_value=runner):
        handled = viewmodel_cls._try_handle_security_verification_retest(vm, 'ya lo hice')

    assert handled is True
    assert 'visible_capture_unreadable' in vm._latest_response_meta
    assert 'pégala' in vm._latest_response_text or 'pega' in vm._latest_response_text
    vm._bg_pool.submit.assert_not_called()
    vm._clear_external_failure_memory.assert_not_called()


def test_visible_capture_missing_target_reports_unresolved_without_copy(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    vm._last_visible_browser_surface = {
        'surface': 'user_default_browser_visible',
        'semantic_bridge': 'none',
    }
    vm._current_world_model = MagicMock(return_value=SimpleNamespace(
        active_windows=[],
        background_processes=[],
    ))

    result = viewmodel_cls._attempt_visible_user_browser_response_capture(
        vm,
        assistant_kind='chatgpt',
        assistant_title='ChatGPT',
    )

    assert result['attempted'] is True
    assert result['success'] is False
    assert result['status'] == 'target_missing'
    assert 'focusable_browser_window' in result['unresolved_fields']


def test_visible_capture_sanitizes_pii_and_tokens(viewmodel_cls):
    raw = 'Cuenta faber@example.com token=abcdefghijklmnopqrstuvwxyz1234567890 password=secreto'
    sanitized = viewmodel_cls._sanitize_visible_response_text(raw)

    assert 'faber@example.com' not in sanitized
    assert 'abcdefghijklmnopqrstuvwxyz1234567890' not in sanitized
    assert 'secreto' not in sanitized
    assert '[redacted_email]' in sanitized
    assert '[redacted]' in sanitized


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


def test_observation_permission_phrase_maps_to_window_action(viewmodel_cls):
    vm = _semantic_vm(viewmodel_cls)
    result = viewmodel_cls._classify_external_action_followup(
        vm,
        'permito observar ChatGPT',
        failure_payload=vm._last_external_failure_payload,
    )

    assert result['intent'] == 'show_problem_window_requested'
    assert result['confidence'] >= 0.5


def test_incident_observation_permission_phrase_opens_help_path(viewmodel_cls):
    incident = {
        'incident_id': 'incident-observe',
        'assistant_kind': 'chatgpt',
        'assistant_title': 'ChatGPT',
        'terminal_state': 'blocked_by_security_verification',
        'block_type': 'browser_security_verification',
        'profile_label': 'chatgpt_program_session/browser_profile',
        'created_at': time.time(),
        'expires_at': time.time() + 600,
        'resolved': False,
        'user_help_needed': 'Completar verificacion o permitir ventana gobernada.',
    }
    vm = _semantic_vm(viewmodel_cls, active_incident=incident)
    vm._try_focus_incident_window = MagicMock(return_value=False)

    handled = viewmodel_cls._try_handle_incident_followup(vm, 'permito observar ChatGPT')

    assert handled is True
    assert 'IABV ve:' in vm._latest_response_text
    assert 'ventana gobernada' in vm._latest_response_text.lower()
    assert 'local' not in vm._latest_response_meta.lower()


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


def test_external_intent_preempts_active_local_chat_worker(viewmodel_cls):
    """A stale local chat worker must not block a fresh ChatGPT request.

    This reproduces the live Windows finding: a previous "sigue" local
    worker was still active, so the next "consulta a ChatGPT" message returned
    before the external-intent sovereignty guard could run.
    """
    run_calls: list[tuple[str, bool]] = []
    terminal_calls: list[dict] = []
    tracer = MagicMock()
    vm = SimpleNamespace(
        _working=True,
        _working_since=time.time(),
        _busy_label='procesando local anterior',
        _active_dispatch_ids={'chat': 'chat-old-001'},
        _attached_files=[],
        _active_interaction_id='int-p073',
        _interaction_has_pending_followup=False,
        _live_status='processing',
        _last_external_failure_payload=None,
        _last_external_failure_ts=0.0,
        _last_user_goal='',
        _chat_messages=[],
        _contextual_suggestions=[],
        dataChanged=MagicMock(),
    )
    vm._explicit_assistant_preference = types.MethodType(
        viewmodel_cls._explicit_assistant_preference,
        vm,
    )
    from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
    vm._assistant_preference_resolver = AssistantPreferenceResolver()
    vm._classify_external_action_followup = MagicMock(return_value={'intent': ''})
    vm._get_active_incident = MagicMock(return_value=None)
    vm._invalidate_dispatch = lambda name: vm._active_dispatch_ids.pop(name, None)
    vm._trace_dispatch_terminal = lambda **kwargs: terminal_calls.append(kwargs)
    vm._set_live_status = MagicMock()
    vm._clear_autonomy_activity_override = MagicMock()
    vm._generate_dispatch_id = lambda task_name: f'dispatch-{task_name}-{uuid.uuid4().hex[:8]}'
    vm._generate_interaction_id = lambda: f'interaction-{uuid.uuid4().hex[:8]}'
    vm._resolve_active_interaction = MagicMock()
    vm._append_message = MagicMock()
    vm._routing_mode_label = MagicMock(return_value='auto')
    vm._try_handle_chat_command = MagicMock(return_value=False)
    vm._try_resolve_pending_observation_permission = MagicMock(return_value=False)
    vm._try_handle_shared_reality_followup = MagicMock(return_value=False)
    vm._try_handle_incident_followup = MagicMock(return_value=False)
    vm._try_handle_security_verification_retest = MagicMock(return_value=False)
    vm._try_handle_external_action_followup = MagicMock(return_value=False)
    vm._try_handle_user_chrome_bridge_selection = MagicMock(return_value=False)
    vm._try_handle_cdp_permission_revoke = MagicMock(return_value=False)
    vm._try_handle_consultation_followup = MagicMock(return_value=False)
    vm._try_handle_external_failure_followup = MagicMock(return_value=False)
    vm._try_handle_continuity_message = MagicMock(return_value=False)
    vm._try_handle_deep_internal_audit = MagicMock(return_value=False)
    vm._try_handle_structured_self_audit = MagicMock(return_value=False)
    vm._try_handle_lightweight_chat = MagicMock(return_value=False)
    vm._set_autonomy_activity_override = MagicMock()
    vm._bg_pool_submit = MagicMock()
    vm._ingest_chat_capabilities = MagicMock()
    vm._refresh_development_packet = MagicMock()
    vm._chat_shortcut_analysis = MagicMock(return_value={})
    vm._schedule_worker_timeout = MagicMock()
    vm._is_dispatch_active = lambda task_name, dispatch_id: vm._active_dispatch_ids.get(task_name) == dispatch_id
    vm._run_external_consultation = lambda assistant, announce=True: run_calls.append((assistant, announce)) or True

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        viewmodel_cls.sendChat(vm, 'has una consulta en ChatGPT: responde solo S si entiendes')

    assert run_calls == [('chatgpt', True)]
    # After fix: dispatch is created but then invalidated by external intent preemption
    # The dispatch ID in _active_dispatch_ids should be different from the original
    assert vm._active_dispatch_ids.get('chat') != 'chat-old-001'
    assert terminal_calls[0]['terminal_state'] == 'superseded_by_external_intent'
    assert vm._resolve_active_interaction.call_count == 0
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'external_intent_preempted_local_worker' in traced_kinds
    assert 'external_intent_detected' in traced_kinds


def test_bare_sigue_uses_structured_continuity_not_local_worker(viewmodel_cls):
    """Bare continuity commands must not fall through to heavy local chat."""
    tracer = MagicMock()
    vm = SimpleNamespace(
        _last_user_goal='hacer una consulta externa y auditar el resultado',
        latestDispatchLifecycle={
            'task_name': 'chat',
            'terminal_state': 'timeout',
        },
        dataChanged=SimpleNamespace(emit=MagicMock()),
    )
    vm._normalized_command_text = types.MethodType(
        viewmodel_cls._normalized_command_text,
        vm,
    )
    vm._CONTINUITY_COMMANDS = viewmodel_cls._CONTINUITY_COMMANDS
    vm._is_continuity_message = types.MethodType(
        viewmodel_cls._is_continuity_message,
        vm,
    )
    vm._append_message = MagicMock()

    with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer', return_value=tracer):
        handled = viewmodel_cls._try_handle_continuity_message(vm, 'sigue')

    assert handled is True
    vm._append_message.assert_called_once()
    response = vm._append_message.call_args.args[2]
    assert 'sin abrir un worker pesado' in response
    traced_kinds = [call.args[0] for call in tracer.trace.call_args_list if call.args]
    assert 'continuity_message_answered' in traced_kinds
