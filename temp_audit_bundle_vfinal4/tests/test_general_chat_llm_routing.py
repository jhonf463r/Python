"""Tests for the lightweight general chat path.

Smalltalk and capability FAQs should answer locally and immediately,
without entering the heavy inference path that can freeze the visible UI.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap


class TestGeneralChatReplyStillExists:
    """_general_chat_reply must still exist as fallback."""

    def test_method_exists(self):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert hasattr(ControlCenterViewModel, '_general_chat_reply'), (
            '_general_chat_reply must still exist as fallback for when LLM is unavailable'
        )


def _make_bootstrap() -> tuple[AppBootstrap, Path]:
    workspace = Path.cwd() / 'data' / f'test_general_chat_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    return bootstrap, workspace


def _cleanup_bootstrap(bootstrap: AppBootstrap, workspace: Path) -> None:
    stop = getattr(bootstrap, 'stop', None)
    if callable(stop):
        stop()
    shutil.rmtree(workspace, ignore_errors=True)


class TestLightweightGeneralChat:

    def test_hola_avoids_infer_task(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            viewmodel = bootstrap.control_center_viewmodel
            assert viewmodel is not None
            called = {'infer_task': 0}

            def _unexpected_infer_task(request):
                called['infer_task'] += 1
                raise AssertionError('hola should not enter infer_task')

            viewmodel.inference_service.infer_task = _unexpected_infer_task  # type: ignore[method-assign]
            viewmodel.sendChat('hola')

            assert called['infer_task'] == 0
            assert viewmodel.get_working() is False
            assert viewmodel.get_chat_messages()[-1]['text'].startswith('Hola.')
        finally:
            _cleanup_bootstrap(bootstrap, workspace)

    def test_capability_faq_avoids_infer_task(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            viewmodel = bootstrap.control_center_viewmodel
            assert viewmodel is not None
            called = {'infer_task': 0}

            def _unexpected_infer_task(request):
                called['infer_task'] += 1
                raise AssertionError('capability FAQ should not enter infer_task')

            viewmodel.inference_service.infer_task = _unexpected_infer_task  # type: ignore[method-assign]
            viewmodel.sendChat('que puedes hacer?')

            assert called['infer_task'] == 0
            assert viewmodel.get_working() is False
            reply = viewmodel.get_chat_messages()[-1]['text']
            assert 'Puedo ayudarte' in reply
        finally:
            _cleanup_bootstrap(bootstrap, workspace)
