from __future__ import annotations

import types
from types import SimpleNamespace


def _make_blocked_preflight_stub() -> SimpleNamespace:
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _last_adaptive_payload={},
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _captured_payload={},
    )

    def _capture_payload(payload):
        stub._captured_payload = payload

    stub._update_adaptive_state = _capture_payload
    stub._guidance_for_external_preflight_block = lambda **_: {'mode': 'need_evolution_review'}
    stub._human_external_consultation_failure = (
        lambda assistant_title, detail, flags=None: (
            f'{assistant_title} requiere verificacion de seguridad.',
            f'{assistant_title}: blocked_by_security_verification',
            f'Verificacion de seguridad pendiente para {assistant_title}.',
        )
    )
    stub._is_resource_pressure_block = ControlCenterViewModel._is_resource_pressure_block
    stub._blocked_external_consultation_result = types.MethodType(
        ControlCenterViewModel._blocked_external_consultation_result,
        stub,
    )
    return stub


def test_preflight_security_verification_returns_specific_terminal_state() -> None:
    vm = _make_blocked_preflight_stub()

    result = vm._blocked_external_consultation_result(
        assistant_kind='chatgpt',
        assistant_title='ChatGPT',
        preflight={
            'blocked': True,
            'reason': 'ChatGPT web asistido quedo bloqueado por una verificacion de seguridad del sitio.',
            'governance': {
                'diagnostic_category': 'browser_security_verification',
                'external_state_flags': ['browser_security_verification'],
                'reason': 'ChatGPT web asistido quedo bloqueado por una verificacion de seguridad del sitio.',
            },
            'approval_checkpoints': [],
        },
    )

    assert result['success'] is False
    assert result['terminal_state'] == 'blocked_by_security_verification'
    assert result['block_type'] == 'browser_security_verification'
    assert result['meta'] == 'ChatGPT: blocked_by_security_verification'
    assert vm._latest_response_meta == 'ChatGPT: blocked_by_security_verification'
    assert vm._busy_label == 'Verificacion de seguridad pendiente para ChatGPT.'
    preflight_meta = vm._captured_payload['metadata']['external_consultation_preflight']
    assert preflight_meta['block_type'] == 'browser_security_verification'
    assert preflight_meta['requires_observation_permission'] is False
