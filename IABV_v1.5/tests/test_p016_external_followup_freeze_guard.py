"""P0.16 tests: avoid UI freeze after an external consultation timeout.

The live failure was:
external_consultation timed out, then the user asked IABV to retry/analyze
the error. The follow-up entered the normal local inference path and the UI
froze. These tests keep that follow-up on a cheap evidence-only path.
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


def _followup_stub() -> SimpleNamespace:
    messages: list[tuple] = []
    stub = SimpleNamespace(
        _last_external_failure_payload={},
        _last_external_failure_ts=0.0,
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _working=True,
        _live_status='processing',
        _autonomy_activity_override={'active': True},
        _EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S=ControlCenterViewModel._EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S,
        _EXTERNAL_FAILURE_FOLLOWUP_PATTERNS=ControlCenterViewModel._EXTERNAL_FAILURE_FOLLOWUP_PATTERNS,
        _EXTERNAL_FAILURE_DEICTIC_TOKENS=ControlCenterViewModel._EXTERNAL_FAILURE_DEICTIC_TOKENS,
        _EXTERNAL_FAILURE_SECURITY_HELP_PATTERNS=ControlCenterViewModel._EXTERNAL_FAILURE_SECURITY_HELP_PATTERNS,
        _SECURITY_HELP_OPEN_WINDOW_PATTERNS=ControlCenterViewModel._SECURITY_HELP_OPEN_WINDOW_PATTERNS,
        _SECURITY_VERIFICATION_VISIBILITY_DISPUTE_PATTERNS=ControlCenterViewModel._SECURITY_VERIFICATION_VISIBILITY_DISPUTE_PATTERNS,
        _SECURITY_PROFILE_MISMATCH_PATTERNS=ControlCenterViewModel._SECURITY_PROFILE_MISMATCH_PATTERNS,
        _SECURITY_RETEST_PATTERNS=ControlCenterViewModel._SECURITY_RETEST_PATTERNS,
        _external_consultation_browser_override={},
        _last_adaptive_payload={},
        config=SimpleNamespace(workspace_root=''),
        _append_message=lambda *args, **kwargs: messages.append((args, kwargs)),
        _set_live_status=lambda value: setattr(stub, '_live_status', value),
        _clear_autonomy_activity_override=lambda: setattr(stub, '_autonomy_activity_override', {}),
        dataChanged=SimpleNamespace(emit=MagicMock()),
        _messages=messages,
    )
    stub._external_failure_indicates_security_verification = (
        lambda payload: ControlCenterViewModel._external_failure_indicates_security_verification(stub, payload)
    )
    stub._external_failure_followup_can_recover_from_audit = (
        lambda lowered_message: ControlCenterViewModel._external_failure_followup_can_recover_from_audit(stub, lowered_message)
    )
    stub._recover_external_failure_from_runtime_audit = (
        lambda lowered_message: ControlCenterViewModel._recover_external_failure_from_runtime_audit(stub, lowered_message)
    )
    stub._security_help_requests_visible_window = (
        lambda lowered_message: ControlCenterViewModel._security_help_requests_visible_window(stub, lowered_message)
    )
    stub._security_followup_disputes_visible_verification = (
        lambda lowered_message: ControlCenterViewModel._security_followup_disputes_visible_verification(stub, lowered_message)
    )
    stub._security_followup_requests_user_browser = (
        lambda lowered_message: ControlCenterViewModel._security_followup_requests_user_browser(stub, lowered_message)
    )
    stub._security_verification_assistant_kind = (
        lambda assistant_title, payload: ControlCenterViewModel._security_verification_assistant_kind(stub, assistant_title, payload)
    )
    stub._remember_user_browser_external_override = (
        lambda assistant_kind: ControlCenterViewModel._remember_user_browser_external_override(stub, assistant_kind=assistant_kind)
    )
    stub._open_security_verification_window = MagicMock(return_value={
        'opened': True,
        'mode': 'visible_isolated_profile',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
    })
    return stub


def test_external_failure_followup_answers_without_heavy_inference() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='ChatGPT web asistido: timeout',
        meta='timeout',
        outcome='timeout',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'intente nuevamente si no analiza bien cual es el error',
    )

    assert handled is True
    assert vm._working is False
    assert vm._live_status == 'idle'
    assert 'ChatGPT' in vm._latest_response_text
    assert 'timeout' in vm._latest_response_text
    assert 'razonamiento local pesado' in vm._latest_response_text
    assert vm._latest_response_meta == 'ChatGPT: external_failure_followup'
    assert vm.dataChanged.emit.called


def test_security_verification_help_followup_uses_failure_memory() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='No pude consultar ChatGPT todavia por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'y puedes desbloquear la verificacion de seguridad o si requieres me ayudas',
    )

    assert handled is True
    assert vm._working is False
    assert vm._live_status == 'idle'
    assert 'ruta externa si fue elegida' in vm._latest_response_text
    assert 'captcha' in vm._latest_response_text
    assert 'ya lo hice' in vm._latest_response_text
    assert 'razonamiento local pesado' in vm._latest_response_text
    assert vm._latest_response_meta == 'ChatGPT: external_failure_followup'
    assert vm._open_security_verification_window.called


def test_deictic_followup_after_security_block_does_not_dispatch_local_chat() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='ChatGPT web asistido quedo bloqueado por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='failed_with_actionable_reason',
        dispatch_id='external-123',
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'pueddes solucionar eso',
    )

    assert handled is True
    assert vm._working is False
    assert vm._live_status == 'idle'
    assert vm._latest_response_meta == 'ChatGPT: external_failure_followup_deictic'
    assert 'razonamiento local pesado' in vm._latest_response_text
    assert vm._messages[-1][1]['reasoning_path'] == 'external_failure_followup_deictic'


def test_security_words_do_not_trigger_without_security_failure() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='ChatGPT web asistido: timeout',
        meta='timeout',
        outcome='timeout',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'puedes desbloquear la seguridad de otra cosa',
    )

    assert handled is False
    assert vm._messages == []


def test_security_help_without_open_request_does_not_open_window() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='No pude consultar ChatGPT todavia por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'por que esta bloqueado por seguridad?',
    )

    assert handled is True
    assert vm._open_security_verification_window.called is False
    assert 'ya lo hice' in vm._latest_response_text


def test_security_window_open_failure_is_reported_as_unresolved() -> None:
    vm = _followup_stub()
    vm._open_security_verification_window = MagicMock(return_value={
        'opened': False,
        'mode': 'failed',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
        'error': 'boom',
    })
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='No pude consultar ChatGPT todavia por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'ok abre la ventana yo te ayudo con eso',
    )

    assert handled is True
    assert vm._open_security_verification_window.called
    assert 'UNRESOLVED:security_verification_window_open_failed' in vm._latest_response_text


def test_security_profile_mismatch_opens_user_browser_not_isolated_profile() -> None:
    vm = _followup_stub()
    vm._open_security_verification_window = MagicMock(return_value={
        'opened': True,
        'mode': 'visible_user_browser',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
        'isolated_profile_skipped': True,
    })
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='No pude consultar ChatGPT todavia por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'pero ya me autentique en mi Chrome, esa ventana que abriste no era',
    )

    assert handled is True
    vm._open_security_verification_window.assert_called_once()
    assert vm._open_security_verification_window.call_args.kwargs['prefer_user_browser'] is True
    assert vm._external_consultation_browser_override['mode'] == 'user_browser_manual'
    assert 'conflicto de perfiles' in vm._latest_response_text
    assert 'perfil aislado' in vm._latest_response_text
    assert 'handoff/manual' in vm._latest_response_text


def test_security_profile_mismatch_detects_user_visible_chatgpt_window() -> None:
    vm = _followup_stub()
    vm._open_security_verification_window = MagicMock(return_value={
        'opened': True,
        'mode': 'visible_user_browser',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
        'isolated_profile_skipped': True,
    })
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='No pude consultar ChatGPT todavia por verificacion de seguridad.',
        meta='ChatGPT: blocked_by_security_verification',
        outcome='blocked',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'yo veo bien la ventana con chatgpt',
    )

    assert handled is True
    vm._open_security_verification_window.assert_called_once()
    assert vm._open_security_verification_window.call_args.kwargs['prefer_user_browser'] is True
    assert vm._external_consultation_browser_override['mode'] == 'user_browser_manual'
    assert 'conflicto de perfiles' in vm._latest_response_text


def test_security_visibility_dispute_does_not_repeat_unproven_captcha_claim() -> None:
    vm = _followup_stub()
    vm._open_security_verification_window = MagicMock(return_value={
        'opened': True,
        'mode': 'visible_isolated_profile',
        'assistant_kind': 'chatgpt',
        'url': 'https://chatgpt.com/',
    })
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='ChatGPT web asistido quedo bloqueado por una verificacion de seguridad.',
        meta='Ruta bloqueada para ChatGPT.',
        outcome='blocked',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='failed_with_actionable_reason',
        dispatch_id='external-visual-dispute',
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'no veo la verificacion de seguridad que me dices, muestrame la ventana',
    )

    assert handled is True
    assert vm._working is False
    assert vm._live_status == 'idle'
    assert vm._latest_response_meta == 'ChatGPT: external_failure_shared_reality_dispute'
    assert 'no tengo evidencia visual' in vm._latest_response_text
    assert 'preflight/historial' in vm._latest_response_text
    assert 'UNRESOLVED:security_verification_visual_proof_missing' in vm._latest_response_text
    assert vm._external_consultation_browser_override['mode'] == 'user_browser_manual'
    assert vm._messages[-1][1]['reasoning_path'] == 'external_failure_shared_reality_dispute'


def test_security_visibility_dispute_recovers_external_failure_after_restart(tmp_path) -> None:
    vm = _followup_stub()
    vm.config = SimpleNamespace(workspace_root=str(tmp_path))
    logs = tmp_path / 'data' / 'logs'
    logs.mkdir(parents=True)
    audit = logs / 'runtime_audit.jsonl'
    audit.write_text(
        '\n'.join([
            json.dumps({
                'kind': 'permission',
                'data': {
                    'permission_id': 'external_consultation:chatgpt',
                    'action': 'blocked',
                    'reason': 'ChatGPT web asistido quedo bloqueado por una verificacion de seguridad del sitio.',
                },
            }),
            json.dumps({
                'kind': 'dispatch_terminal',
                'data': {
                    'task_name': 'external_consultation',
                    'dispatch_id': 'external-after-restart',
                    'terminal_state': 'failed_with_actionable_reason',
                    'provider': 'ChatGPT',
                    'reason': 'external_consultation_blocked: Ruta bloqueada para ChatGPT.',
                },
            }),
        ]),
        encoding='utf-8',
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'no veo la verificacion de seguridad',
    )

    assert handled is True
    assert vm._working is False
    assert vm._live_status == 'idle'
    assert vm._last_external_failure_payload['recovered_from'] == 'runtime_audit'
    assert vm._latest_response_meta == 'ChatGPT: external_failure_shared_reality_dispute'
    assert 'no tengo evidencia visual' in vm._latest_response_text
    assert 'UNRESOLVED:security_verification_visual_proof_missing' in vm._latest_response_text
    assert vm._messages[-1][1]['reasoning_path'] == 'external_failure_shared_reality_dispute'


def test_metacognitive_cdp_preference_becomes_user_browser_handoff(monkeypatch) -> None:
    vm = SimpleNamespace(
        _external_consultation_browser_override={},
        _assistant_display_name=lambda assistant_kind: 'ChatGPT',
    )
    vm._active_user_browser_external_override = (
        lambda assistant_kind: ControlCenterViewModel._active_user_browser_external_override(vm, assistant_kind)
    )
    monkeypatch.setenv('IABV_PREFER_CDP_SESSION', '1')

    overrides = ControlCenterViewModel._external_consultation_goal_overrides(vm, 'chatgpt')

    assert overrides['prefer_user_browser_session'] is True
    assert overrides['response_capture_mode'] == 'manual_pasteback'
    assert overrides['isolated_session_required'] is False
    assert overrides['browser_override_reason'] == 'metacognitive_cdp_preference'
    assert overrides['browser_override_source'] == 'IABV_PREFER_CDP_SESSION'


def test_security_retest_defers_profile_mismatch_to_followup_path() -> None:
    vm = _followup_stub()
    vm._last_adaptive_payload = {
        'metadata': {
            'external_consultation': {
                'status': 'blocked_external',
                'detail': 'browser_security_verification',
                'assistant_kind': 'chatgpt',
            }
        }
    }

    handled = ControlCenterViewModel._try_handle_security_verification_retest(
        vm,
        'a mi si me funciona en mi chrome',
    )

    assert handled is False


def test_external_failure_followup_ignores_stale_failure_memory(tmp_path) -> None:
    vm = _followup_stub()
    vm.config = SimpleNamespace(workspace_root=str(tmp_path))
    vm._last_external_failure_payload = {
        'assistant_title': 'ChatGPT',
        'message': 'timeout',
        'meta': 'timeout',
        'outcome': 'timeout',
        'success': False,
    }
    vm._last_external_failure_ts = time.time() - 9999

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'analiza el error de chatgpt',
    )

    assert handled is False
    assert vm._messages == []


def test_external_failure_followup_ignores_unrelated_chat() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='timeout',
        meta='timeout',
        outcome='timeout',
        success=False,
    )

    handled = ControlCenterViewModel._try_handle_external_failure_followup(
        vm,
        'crea una nota nueva',
    )

    assert handled is False
    assert vm._messages == []


def test_external_failure_memory_clears_after_success() -> None:
    vm = _followup_stub()
    ControlCenterViewModel._remember_external_failure(
        vm,
        assistant_title='ChatGPT',
        message='timeout',
        meta='timeout',
        outcome='timeout',
        success=False,
    )

    ControlCenterViewModel._clear_external_failure_memory(vm)

    assert vm._last_external_failure_payload == {}
    assert vm._last_external_failure_ts == 0.0


def test_dock_skip_trace_is_rate_limited_by_reason() -> None:
    vm = SimpleNamespace(
        _dock_skip_last_trace={},
        _DOCK_SKIP_TRACE_COOLDOWN_S=15.0,
    )

    assert ControlCenterViewModel._should_trace_dock_skip(vm, 'query_pending') is True
    assert ControlCenterViewModel._should_trace_dock_skip(vm, 'query_pending') is False
    assert ControlCenterViewModel._should_trace_dock_skip(vm, 'resource_pressure') is True

    vm._dock_skip_last_trace['query_pending'] = time.time() - 20.0
    assert ControlCenterViewModel._should_trace_dock_skip(vm, 'query_pending') is True
