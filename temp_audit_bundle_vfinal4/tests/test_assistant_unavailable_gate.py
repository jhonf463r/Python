"""Tests for the explicit assistant_unavailable gate.

When an explicit external consultation (e.g. ChatGPT) is blocked because
the assistant is detected as unavailable, the UI must NOT silently redirect
to local.  Instead it must surface the approval dialog so the user
understands:
  - that ChatGPT is not available
  - that they can retry, open/verify the tool, or audit

This reuses the existing approval dialog / permission_gates wiring.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    OperationalBlockRecord,
    ToolLiveStatus,
    WorldModelSnapshot,
)


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


def test_assistant_unavailable_triggers_approval_dialog() -> None:
    """When governance blocks with assistant_unavailable, the guidance
    mode must be 'need_approval' (not 'need_evolution_review') so the
    approval dialog is visible in QML."""
    bootstrap = _make_bootstrap('test_assistant_unavailable_gate')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        governance = {
            'autonomy_level': 'guarded_local',
            'recommended_action': 'continue_local',
            'reason': 'No pude confirmar que ChatGPT este disponible antes de usarla.',
            'block_risky_action': True,
            'diagnostic_category': 'assistant_unavailable',
            'blockers': ['No pude confirmar que ChatGPT este disponible antes de usarla.'],
            'external_state_flags': ['assistant_unavailable'],
        }
        guidance = viewmodel._guidance_for_external_preflight_block(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            governance=governance,
            approval_checkpoints=[],
        )
        assert guidance['mode'] == 'need_approval', (
            'assistant_unavailable must trigger need_approval mode so the '
            'approval dialog is shown, not need_evolution_review'
        )
        assert 'no disponible' in guidance['title'].lower()
        action_keys = [a['action'] for a in guidance['actions']]
        assert 'consult_chatgpt' in action_keys, (
            'User must be able to retry the consultation'
        )
    finally:
        _cleanup_bootstrap(bootstrap)


def test_assistant_unavailable_approval_dialog_visible_after_blocked_result() -> None:
    """End-to-end: _blocked_external_consultation_result with
    assistant_unavailable must set _approval_dialog_visible = True."""
    bootstrap = _make_bootstrap('test_assistant_unavailable_dialog_visible')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._last_adaptive_payload = {
            'session_id': 'test-unavailable',
            'status': 'active',
            'metadata': {},
        }

        preflight = {
            'blocked': True,
            'reason': 'No pude confirmar que ChatGPT este disponible.',
            'governance': {
                'autonomy_level': 'guarded_local',
                'reason': 'No pude confirmar que ChatGPT este disponible.',
                'block_risky_action': True,
                'diagnostic_category': 'assistant_unavailable',
                'blockers': ['assistant_unavailable'],
                'external_state_flags': ['assistant_unavailable'],
            },
            'approval_checkpoints': [],
            'world_model_summary': {},
        }

        result = viewmodel._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )
        assert result['success'] is False
        assert viewmodel._approval_dialog_visible is True, (
            'Approval dialog must be visible when assistant_unavailable blocks'
        )
        assert 'no disponible' in viewmodel._approval_dialog_title.lower()
    finally:
        _cleanup_bootstrap(bootstrap)


def test_other_block_types_do_not_trigger_approval_dialog() -> None:
    """Non-assistant_unavailable blocks without approval_checkpoints
    must still use need_evolution_review (no dialog)."""
    bootstrap = _make_bootstrap('test_other_block_no_dialog')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        governance = {
            'autonomy_level': 'guarded_local',
            'reason': 'La red no esta lista.',
            'block_risky_action': True,
            'diagnostic_category': 'network_blocked',
            'blockers': ['network_blocked'],
        }
        guidance = viewmodel._guidance_for_external_preflight_block(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            governance=governance,
            approval_checkpoints=[],
        )
        assert guidance['mode'] == 'need_evolution_review', (
            'network_blocked should not trigger approval dialog'
        )
    finally:
        _cleanup_bootstrap(bootstrap)


def test_assistant_unavailable_does_not_silently_redirect_to_local() -> None:
    """The response message must mention the assistant name and the
    block reason, not silently proceed with local routing."""
    bootstrap = _make_bootstrap('test_unavailable_no_silent_redirect')
    try:
        viewmodel = bootstrap.control_center_viewmodel
        assert viewmodel is not None

        viewmodel._last_adaptive_payload = {
            'session_id': 'test-no-redirect',
            'status': 'active',
            'metadata': {},
        }

        preflight = {
            'blocked': True,
            'reason': 'No pude confirmar que ChatGPT este disponible antes de usarla.',
            'governance': {
                'reason': 'No pude confirmar que ChatGPT este disponible antes de usarla.',
                'block_risky_action': True,
                'diagnostic_category': 'assistant_unavailable',
                'blockers': ['assistant_unavailable'],
            },
            'approval_checkpoints': [],
            'world_model_summary': {},
        }

        result = viewmodel._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )
        msg = result['message'].lower()
        assert 'chatgpt' in msg, 'User must see which assistant is blocked'
        assert 'bloqueada' in msg or 'lanzar' in msg, (
            'Response must mention the block, not silently redirect'
        )
    finally:
        _cleanup_bootstrap(bootstrap)
