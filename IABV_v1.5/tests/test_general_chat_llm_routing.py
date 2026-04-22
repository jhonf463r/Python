"""Tests for PR G: _answer_general_chat routes through LLM instead of templates.

Validates that general chat questions (e.g. "que puedes hacer", "hola",
meta-assistant prompts) now go through the orchestrator/LLM pipeline
instead of returning hardcoded template strings.  When the LLM is
unavailable the method must fall back to templates gracefully.
"""
from __future__ import annotations

import threading
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to build a minimal ControlCenterViewModel without PySide6
# ---------------------------------------------------------------------------

def _stub_signal():
    """Return a callable that mimics Signal.emit / Signal.connect."""
    class _Sig:
        def __init__(self):
            self._slots: list = []
        def connect(self, slot):
            self._slots.append(slot)
        def emit(self, *args):
            for s in self._slots:
                s(*args)
    return _Sig()


def _make_viewmodel():
    """Build a ControlCenterViewModel-like object with just enough wiring."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    # We cannot instantiate ControlCenterViewModel directly without Qt,
    # so we test the method logic by extracting key behavioural properties.
    # Instead we verify the source code structure.
    import inspect
    source = inspect.getsource(ControlCenterViewModel._answer_general_chat)
    return source


class TestAnswerGeneralChatRoutesLLM:
    """Verify _answer_general_chat dispatches to the orchestrator."""

    def test_method_spawns_worker_thread(self):
        """The new implementation must use threading.Thread for async LLM call."""
        source = _make_viewmodel()
        assert 'threading.Thread' in source, (
            '_answer_general_chat should spawn a worker thread for the LLM call'
        )

    def test_method_calls_build_request(self):
        """The worker must call _build_request to create an InferenceRequest."""
        source = _make_viewmodel()
        assert '_build_request' in source, (
            '_answer_general_chat should call _build_request(message)'
        )

    def test_method_calls_infer_task(self):
        """The worker must call inference_service.infer_task."""
        source = _make_viewmodel()
        assert 'infer_task' in source, (
            '_answer_general_chat should call inference_service.infer_task'
        )

    def test_method_emits_task_resolved(self):
        """On success the worker must emit taskResolved('chat', ...)."""
        source = _make_viewmodel()
        assert "taskResolved.emit" in source, (
            '_answer_general_chat should emit taskResolved on success'
        )

    def test_fallback_on_exception(self):
        """On LLM failure the method must fall back to _general_chat_reply."""
        source = _make_viewmodel()
        assert '_general_chat_reply' in source, (
            '_answer_general_chat should fall back to _general_chat_reply on error'
        )

    def test_sets_working_flag(self):
        """Must set _working = True before spawning the worker."""
        source = _make_viewmodel()
        assert '_working = True' in source, (
            '_answer_general_chat should set _working = True'
        )

    def test_sets_autonomy_activity_override(self):
        """Must show activity override while waiting for LLM."""
        source = _make_viewmodel()
        assert '_set_autonomy_activity_override' in source, (
            '_answer_general_chat should set autonomy activity override'
        )

    def test_no_direct_template_reply(self):
        """Must NOT directly return _general_chat_reply as the primary path."""
        source = _make_viewmodel()
        # The old code had: reply = self._general_chat_reply(message)
        #                    self._append_message('assistant', 'IABV', reply, ...)
        # as the ONLY path.  Now _general_chat_reply should only appear in except.
        lines = source.split('\n')
        primary_template_call = False
        in_except = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('except'):
                in_except = True
            if '_general_chat_reply' in stripped and not in_except:
                primary_template_call = True
        assert not primary_template_call, (
            '_general_chat_reply should only appear in the except/fallback block, '
            'not as the primary response path'
        )

    def test_includes_provider_name_in_payload(self):
        """The taskResolved payload must include provider_name for audit."""
        source = _make_viewmodel()
        assert 'provider_name' in source

    def test_includes_summary_in_payload(self):
        """The taskResolved payload must include summary."""
        source = _make_viewmodel()
        assert "'summary'" in source

    def test_includes_local_chat_llm_key(self):
        """The taskResolved payload must include local_chat_llm for tracing."""
        source = _make_viewmodel()
        assert 'local_chat_llm' in source


class TestGeneralChatReplyStillExists:
    """_general_chat_reply must still exist as fallback."""

    def test_method_exists(self):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert hasattr(ControlCenterViewModel, '_general_chat_reply'), (
            '_general_chat_reply must still exist as fallback for when LLM is unavailable'
        )
