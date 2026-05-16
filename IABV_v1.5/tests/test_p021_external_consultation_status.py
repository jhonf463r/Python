"""P0.21 regression tests for ChatGPT consultation reuse and status answers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


def test_status_reused_metadata_derives_reused_context_without_message_hint() -> None:
    payload = {
        'success': True,
        'message': 'Consulta externa lista.',
        'payload': {
            'metadata': {
                'external_consultation': {
                    'status': 'reused',
                    'response_captured': False,
                }
            }
        },
    }

    assert ControlCenterViewModel._derive_external_consultation_outcome(payload) == 'reused_context'


def test_explicit_reused_context_payload_is_terminal_for_ui() -> None:
    payload = {
        'success': True,
        'message': 'Ya tenia una consulta equivalente para ChatGPT.',
        'meta': 'Reutilizando contexto existente.',
        'payload': {
            'metadata': {
                'external_consultation': {
                    'status': 'reused',
                    'explicit_external_consultation': True,
                    'force_new_external_consultation': True,
                }
            }
        },
    }

    assert ControlCenterViewModel._should_finalize_reused_external_context(payload) is True


def test_apply_external_reused_context_closes_processing_lifecycle() -> None:
    resolved: list[tuple[str, str]] = []
    messages: list[tuple] = []
    traces: list[dict] = []
    vm = SimpleNamespace(
        _last_external_consultation_ts=0.0,
        _last_adaptive_payload={},
        _last_user_goal='has una consulta a chatgpt',
        _active_dispatch_ids={'external_consultation': 'dispatch-1'},
        _FINAL_INTERACTION_OUTCOMES=ControlCenterViewModel._FINAL_INTERACTION_OUTCOMES,
        _interaction_has_pending_followup=True,
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _clear_autonomy_activity_override=lambda: None,
        _update_adaptive_state=lambda payload: None,
        _append_message=lambda *args, **kwargs: messages.append((args, kwargs)),
        _record_chat_audit=lambda **kwargs: None,
        _external_state_notice=lambda flags: '',
        _derive_external_consultation_outcome=ControlCenterViewModel._derive_external_consultation_outcome,
        _clear_external_failure_memory=lambda: None,
        _remember_external_failure=lambda **kwargs: None,
        _set_external_consultation_activity=lambda **kwargs: setattr(vm, '_activity_kwargs', kwargs),
        _trace_dispatch_terminal=lambda **kwargs: traces.append(kwargs),
        _invalidate_dispatch=lambda task_name: vm._active_dispatch_ids.pop(task_name, None),
        _should_finalize_reused_external_context=lambda payload: ControlCenterViewModel._should_finalize_reused_external_context(payload),
        _resolve_active_interaction=lambda *, outcome='resolved', provider='': resolved.append((outcome, provider)),
        _update_progress_cards=lambda: None,
        _should_defer_heavy_work=lambda: True,
        dataChanged=SimpleNamespace(emit=MagicMock()),
    )
    payload = {
        'success': True,
        'message': 'Ya tenia una consulta equivalente para ChatGPT.',
        'meta': 'Reutilizando contexto existente.',
        'payload': {
            'metadata': {
                'external_consultation': {
                    'status': 'reused',
                    'explicit_external_consultation': True,
                }
            }
        },
        'assistant_title': 'ChatGPT web asistido',
    }

    ControlCenterViewModel._apply_task_result(vm, 'external_consultation', payload)

    assert resolved == [('reused_context_resolved', 'ChatGPT web asistido')]
    assert vm._interaction_has_pending_followup is False
    assert vm._busy_label == 'Consulta externa lista con ChatGPT web asistido.'
    assert vm.dataChanged.emit.called


def _operational_status_stub() -> SimpleNamespace:
    messages: list[tuple] = []
    vm = SimpleNamespace(
        _last_user_goal='',
        _latest_response_text='',
        _latest_response_meta='',
        _busy_label='',
        _working=False,
        _normalized_command_text=lambda message: ' '.join(str(message or '').lower().strip().split()),
        _runtime_latest_dispatch_lifecycle_snapshot=lambda: {
            'task_name': 'external_consultation',
            'terminal_state': 'success',
            'duration_ms': 171.0,
            'provider': 'ChatGPT web asistido',
            'dispatch_id': 'abc123',
        },
        _runtime_build_fingerprint_snapshot=lambda: {
            'branch': 'main',
            'head': '9e997cb8ffc097a040aeec5f1a91dd821648d690',
            'dirty': True,
        },
        _runtime_latest_interaction_event_snapshot=lambda: {
            'outcome': 'reused_context',
            'is_final': False,
        },
        _clear_autonomy_activity_override=lambda: None,
        _append_message=lambda *args, **kwargs: messages.append((args, kwargs)),
        _record_chat_audit=lambda **kwargs: None,
        _set_live_status=lambda value: setattr(vm, '_live_status', value),
        dataChanged=SimpleNamespace(emit=MagicMock()),
        _messages=messages,
    )
    return vm


def test_operational_status_question_is_lightweight_and_evidence_based() -> None:
    vm = _operational_status_stub()

    handled = ControlCenterViewModel._is_operational_status_question(
        vm,
        'si puedes hacer la consulta si o no?',
    )
    ControlCenterViewModel._answer_operational_status_question(vm, 'si puedes hacer la consulta si o no?')

    assert handled is True
    assert vm._live_status == 'idle'
    assert 'reused_context' in vm._latest_response_text
    assert 'no hizo una consulta nueva' in vm._latest_response_text
    assert vm._latest_response_meta.startswith('Estado operativo local')
    assert vm.dataChanged.emit.called


def test_lightweight_chat_routes_operational_status_before_heavy_inference() -> None:
    called: list[str] = []
    vm = SimpleNamespace(
        _is_operational_status_question=lambda message: True,
        _answer_operational_status_question=lambda message: called.append(message),
    )

    assert ControlCenterViewModel._try_handle_lightweight_chat(vm, 'te falta mucho para responder?') is True
    assert called == ['te falta mucho para responder?']
