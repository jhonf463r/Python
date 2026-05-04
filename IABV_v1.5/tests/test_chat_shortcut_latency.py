"""Tests for expanded general-chat shortcut detection and latency recording.

Slice: expand _is_general_chat_message for informal greetings + record
real latency_ms in _record_chat_audit across all chat paths.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap


def _make_bootstrap(name: str) -> AppBootstrap:
    workspace = Path.cwd() / 'data' / f'{name}_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap


def _cleanup_bootstrap(bootstrap: AppBootstrap) -> None:
    workspace = getattr(bootstrap, '_test_workspace', None)
    stop = getattr(bootstrap, 'stop', None)
    if callable(stop):
        stop()
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


# ── _is_general_chat_message: informal greetings ──


def test_como_estas_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_como_estas')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('como estas') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_como_estas_with_accent_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_como_estas_accent')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('cómo estás') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_que_tal_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_que_tal')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('que tal') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_hey_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_hey')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('hey') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_todo_bien_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_todo_bien')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('todo bien') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_que_onda_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_que_onda')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('que onda') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_como_andas_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_como_andas')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('como andas') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_como_te_va_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_como_te_va')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('como te va') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_oye_is_general_chat() -> None:
    bootstrap = _make_bootstrap('test_oye')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('oye') is True
    finally:
        _cleanup_bootstrap(bootstrap)


def test_task_like_still_not_general_chat() -> None:
    bootstrap = _make_bootstrap('test_task_not_general')
    try:
        vm = bootstrap.control_center_viewmodel
        assert vm._is_general_chat_message('consulta chatgpt') is False
        assert vm._is_general_chat_message('abrir wplay') is False
        assert vm._is_general_chat_message('login') is False
    finally:
        _cleanup_bootstrap(bootstrap)


# ── informal greeting goes through shortcut, not orchestrator ──


def test_como_estas_uses_shortcut_not_orchestrator() -> None:
    bootstrap = _make_bootstrap('test_como_estas_shortcut')
    try:
        vm = bootstrap.control_center_viewmodel
        called = {'infer_task': 0}

        def _unexpected_infer(request):
            called['infer_task'] += 1
            raise AssertionError('informal greeting should not trigger infer_task')

        vm.inference_service.infer_task = _unexpected_infer  # type: ignore[method-assign]
        vm.sendChat('como estas')

        assert called['infer_task'] == 0
        assert vm.get_working() is False
        msgs = vm.get_chat_messages()
        assistant_msgs = [m for m in msgs if m.get('role') == 'assistant']
        assert len(assistant_msgs) >= 1
    finally:
        _cleanup_bootstrap(bootstrap)


def test_que_tal_uses_shortcut_not_orchestrator() -> None:
    bootstrap = _make_bootstrap('test_que_tal_shortcut')
    try:
        vm = bootstrap.control_center_viewmodel
        called = {'infer_task': 0}

        def _unexpected_infer(request):
            called['infer_task'] += 1
            raise AssertionError('que tal should not trigger infer_task')

        vm.inference_service.infer_task = _unexpected_infer  # type: ignore[method-assign]
        vm.sendChat('que tal')

        assert called['infer_task'] == 0
        assert vm.get_working() is False
    finally:
        _cleanup_bootstrap(bootstrap)


# ── latency tracking ──


def test_chat_elapsed_ms_returns_positive() -> None:
    bootstrap = _make_bootstrap('test_elapsed_ms')
    try:
        vm = bootstrap.control_center_viewmodel
        import time
        vm._chat_request_start = time.monotonic() - 0.05
        elapsed = vm._chat_elapsed_ms()
        assert elapsed > 0.0
        assert elapsed >= 40.0  # at least ~50ms expected
    finally:
        _cleanup_bootstrap(bootstrap)


def test_chat_elapsed_ms_zero_when_no_start() -> None:
    bootstrap = _make_bootstrap('test_elapsed_zero')
    try:
        vm = bootstrap.control_center_viewmodel
        if hasattr(vm, '_chat_request_start'):
            delattr(vm, '_chat_request_start')
        elapsed = vm._chat_elapsed_ms()
        assert elapsed == 0.0
    finally:
        _cleanup_bootstrap(bootstrap)


def test_general_chat_shortcut_records_latency() -> None:
    bootstrap = _make_bootstrap('test_general_chat_latency')
    try:
        vm = bootstrap.control_center_viewmodel
        audit_calls: list[dict] = []
        original_record = vm._record_chat_audit

        def _capture_audit(**kwargs):
            audit_calls.append(kwargs)
            return original_record(**kwargs)

        vm._record_chat_audit = _capture_audit  # type: ignore[method-assign]
        vm.sendChat('como estas')

        assert len(audit_calls) >= 1
        call = audit_calls[-1]
        assert call['reasoning_path'] == 'general_chat'
        assert call['latency_ms'] > 0.0
    finally:
        _cleanup_bootstrap(bootstrap)


def test_hola_shortcut_records_latency() -> None:
    bootstrap = _make_bootstrap('test_hola_latency')
    try:
        vm = bootstrap.control_center_viewmodel
        audit_calls: list[dict] = []
        original_record = vm._record_chat_audit

        def _capture_audit(**kwargs):
            audit_calls.append(kwargs)
            return original_record(**kwargs)

        vm._record_chat_audit = _capture_audit  # type: ignore[method-assign]
        vm.sendChat('hola')

        assert len(audit_calls) >= 1
        call = audit_calls[-1]
        assert call['reasoning_path'] == 'general_chat'
        assert call['latency_ms'] > 0.0
    finally:
        _cleanup_bootstrap(bootstrap)


# ── _general_chat_reply: informal phrases get specific reply ──


def test_general_chat_reply_como_estas() -> None:
    bootstrap = _make_bootstrap('test_reply_como_estas')
    try:
        vm = bootstrap.control_center_viewmodel
        reply, meta, tag = vm._general_chat_reply('como estas')
        assert 'funcionando' in reply.lower() or 'aqui' in reply.lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_general_chat_reply_que_tal() -> None:
    bootstrap = _make_bootstrap('test_reply_que_tal')
    try:
        vm = bootstrap.control_center_viewmodel
        reply, meta, tag = vm._general_chat_reply('que tal')
        assert 'funcionando' in reply.lower() or 'aqui' in reply.lower()
    finally:
        _cleanup_bootstrap(bootstrap)
