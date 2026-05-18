from __future__ import annotations

import json
import os
import time
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


def _bind(stub: SimpleNamespace, *names: str) -> SimpleNamespace:
    for name in names:
        stub.__dict__[name] = types.MethodType(getattr(ControlCenterViewModel, name), stub)
    return stub


def _incident_stub(tmp_path: Path | None = None) -> SimpleNamespace:
    messages: list[tuple] = []
    stub = SimpleNamespace(
        _active_incident_frame=None,
        _last_external_failure_payload={},
        _last_external_failure_ts=0.0,
        _last_adaptive_payload={'metadata': {}},
        _last_user_goal='has una consulta a chatgpt',
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _working=True,
        _live_status='processing',
        _autonomy_activity_override={'active': True},
        _active_interaction_id='interaction-1',
        _INCIDENT_FRAME_TTL_S=ControlCenterViewModel._INCIDENT_FRAME_TTL_S,
        _SECURITY_RETEST_PATTERNS=ControlCenterViewModel._SECURITY_RETEST_PATTERNS,
        _INCIDENT_HELP_TOKENS=ControlCenterViewModel._INCIDENT_HELP_TOKENS,
        _INCIDENT_SHOW_TOKENS=ControlCenterViewModel._INCIDENT_SHOW_TOKENS,
        _INCIDENT_VISIBILITY_TOKENS=ControlCenterViewModel._INCIDENT_VISIBILITY_TOKENS,
        _INCIDENT_PROFILE_TOKENS=ControlCenterViewModel._INCIDENT_PROFILE_TOKENS,
        _INCIDENT_BRIDGE_LAUNCH_TOKENS=ControlCenterViewModel._INCIDENT_BRIDGE_LAUNCH_TOKENS,
        _INCIDENT_BRIDGE_SWITCH_TOKENS=ControlCenterViewModel._INCIDENT_BRIDGE_SWITCH_TOKENS,
        _SECURITY_VERIFICATION_VISIBILITY_DISPUTE_PATTERNS=ControlCenterViewModel._SECURITY_VERIFICATION_VISIBILITY_DISPUTE_PATTERNS,
        _SECURITY_PROFILE_MISMATCH_PATTERNS=ControlCenterViewModel._SECURITY_PROFILE_MISMATCH_PATTERNS,
        _EXTERNAL_FAILURE_SECURITY_HELP_PATTERNS=ControlCenterViewModel._EXTERNAL_FAILURE_SECURITY_HELP_PATTERNS,
        _EXTERNAL_FAILURE_FOLLOWUP_PATTERNS=ControlCenterViewModel._EXTERNAL_FAILURE_FOLLOWUP_PATTERNS,
        _EXTERNAL_FAILURE_DEICTIC_TOKENS=ControlCenterViewModel._EXTERNAL_FAILURE_DEICTIC_TOKENS,
        config=SimpleNamespace(workspace_root=str(tmp_path or Path.cwd())),
        dataChanged=SimpleNamespace(emit=MagicMock()),
        _append_message=lambda *a, **kw: messages.append((a, kw)),
        _set_live_status=lambda value: setattr(stub, '_live_status', value),
        _clear_autonomy_activity_override=lambda: setattr(stub, '_autonomy_activity_override', {}),
        _explicit_assistant_preference=lambda message: '',
        _detect_cdp_available=lambda timeout=2.0, cdp_url='': {'available': False, 'error': 'unavailable'},
        _current_world_model=lambda: SimpleNamespace(active_windows=[]),
        _try_handle_cdp_launch_request=MagicMock(return_value=False),
        _try_handle_user_chrome_bridge_selection=MagicMock(return_value=False),
        _try_handle_security_verification_retest=MagicMock(return_value=False),
        _messages=messages,
    )
    _bind(
        stub,
        '_remember_external_failure',
        '_clear_external_failure_memory',
        '_maybe_create_active_incident_frame',
        '_describe_incident_actions',
        '_get_active_incident',
        '_resolve_incident_frame',
        '_classify_incident_followup_intent',
        '_try_handle_incident_followup',
        '_build_incident_help_response',
        '_try_focus_incident_window',
        '_external_failure_indicates_security_verification',
        '_security_verification_assistant_kind',
        '_recover_external_failure_from_runtime_audit',
        '_external_failure_followup_can_recover_from_audit',
    )
    stub._describe_user_help_needed = ControlCenterViewModel._describe_user_help_needed
    return stub


def test_external_security_block_creates_active_incident_frame(tmp_path: Path) -> None:
    stub = _incident_stub(tmp_path)

    stub._remember_external_failure(
        assistant_title='ChatGPT',
        message='Ruta bloqueada.',
        meta='browser_security_verification',
        outcome='blocked',
        success=False,
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        dispatch_id='d-1',
    )

    frame = stub._get_active_incident()
    assert frame is not None
    assert frame['block_type'] == 'browser_security_verification'
    assert 'show_problem_window' in frame['available_actions']
    assert frame['dispatch_id'] == 'd-1'


def test_help_offer_uses_incident_frame_not_local_chat(tmp_path: Path) -> None:
    stub = _incident_stub(tmp_path)
    stub._maybe_create_active_incident_frame(
        assistant_title='ChatGPT',
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        meta='browser_security_verification',
        dispatch_id='d-2',
    )

    assert stub._try_handle_incident_followup('cómo te puedo ayudar') is True

    assert stub._working is False
    assert stub._live_status == 'idle'
    assert 'Lo que yo veo' in stub._latest_response_text
    assert 'ChatGPT' in stub._latest_response_text
    assert stub._latest_response_meta.startswith('incident_followup:')


def test_show_problem_attempts_window_focus(tmp_path: Path) -> None:
    stub = _incident_stub(tmp_path)
    stub._maybe_create_active_incident_frame(
        assistant_title='ChatGPT',
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        meta='browser_security_verification',
        dispatch_id='d-3',
    )
    stub._try_focus_incident_window = MagicMock(return_value=True)

    assert stub._try_handle_incident_followup('ábreme la ventana donde tienes el problema') is True

    stub._try_focus_incident_window.assert_called_once()
    assert 'Abrí o enfoqué' in stub._latest_response_text


def test_bridge_launch_intent_delegates_to_existing_handler(tmp_path: Path) -> None:
    stub = _incident_stub(tmp_path)
    stub._maybe_create_active_incident_frame(
        assistant_title='ChatGPT',
        assistant_kind='chatgpt',
        terminal_state='blocked_by_security_verification',
        meta='browser_security_verification',
        dispatch_id='d-4',
    )
    stub._try_handle_cdp_launch_request = MagicMock(return_value=True)

    assert stub._try_handle_incident_followup('abrir chrome con puente') is True

    stub._try_handle_cdp_launch_request.assert_called_once()
    assert stub._live_status == 'idle'


def test_cdp_unavailable_clears_stale_preference() -> None:
    messages: list[tuple] = []
    os.environ['IABV_PREFER_CDP_SESSION'] = '1'
    stub = SimpleNamespace(
        _CHROME_BRIDGE_PATTERNS=ControlCenterViewModel._CHROME_BRIDGE_PATTERNS,
        _detect_cdp_available=lambda: {'available': False, 'error': 'connection_failed'},
        _latest_response_text='',
        _latest_response_meta='',
        _working=True,
        _live_status='processing',
        _append_message=lambda *a, **kw: messages.append((a, kw)),
        _set_live_status=lambda value: setattr(stub, '_live_status', value),
        dataChanged=SimpleNamespace(emit=MagicMock()),
    )
    _bind(stub, '_try_handle_user_chrome_bridge_selection')

    try:
        assert stub._try_handle_user_chrome_bridge_selection('usar mi chrome') is True
        assert os.environ.get('IABV_PREFER_CDP_SESSION') is None
        assert stub._live_status == 'idle'
    finally:
        os.environ.pop('IABV_PREFER_CDP_SESSION', None)


def test_recover_from_runtime_audit_creates_incident(tmp_path: Path) -> None:
    audit_dir = tmp_path / 'data' / 'logs'
    audit_dir.mkdir(parents=True)
    events = [
        {
            'kind': 'dispatch_terminal',
            'data': {
                'task_name': 'external_consultation',
                'terminal_state': 'blocked_by_security_verification',
                'reason': 'browser_security_verification',
                'provider': 'ChatGPT',
                'dispatch_id': 'd-5',
            },
        }
    ]
    (audit_dir / 'runtime_audit.jsonl').write_text(
        '\n'.join(json.dumps(e) for e in events),
        encoding='utf-8',
    )
    stub = _incident_stub(tmp_path)

    assert stub._try_handle_incident_followup('cómo te puedo ayudar con eso') is True

    assert stub._get_active_incident() is not None
    assert 'Lo que yo veo' in stub._latest_response_text


def test_platform_pending_p037_json_validates() -> None:
    from iabv_v15.domain.models import PlatformPendingTask

    path = (
        Path(__file__).resolve().parent.parent
        / 'data' / 'evolution' / 'platform_pending'
        / 'task_runtime_active_incident_self_correction_p037.json'
    )
    assert path.exists()
    PlatformPendingTask.model_validate_json(path.read_text(encoding='utf-8'))
