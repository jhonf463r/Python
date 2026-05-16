"""P0.16 tests: avoid UI freeze after an external consultation timeout.

The live failure was:
external_consultation timed out, then the user asked IABV to retry/analyze
the error. The follow-up entered the normal local inference path and the UI
froze. These tests keep that follow-up on a cheap evidence-only path.
"""
from __future__ import annotations

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
        _append_message=lambda *args, **kwargs: messages.append((args, kwargs)),
        _set_live_status=lambda value: setattr(stub, '_live_status', value),
        _clear_autonomy_activity_override=lambda: setattr(stub, '_autonomy_activity_override', {}),
        dataChanged=SimpleNamespace(emit=MagicMock()),
        _messages=messages,
    )
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


def test_external_failure_followup_ignores_stale_failure_memory() -> None:
    vm = _followup_stub()
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
