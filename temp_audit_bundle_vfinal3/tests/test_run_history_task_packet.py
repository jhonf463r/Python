"""Tests for task_packet visibility in RunHistoryViewModel.

Covers:
- payload includes truth_state from task_packet evidence_basis
- payload shows selected_worker_label when worker exists
- gate_ran / gate_usable / gate_available_count populated
- approval_required reflected
- unresolved_count and unresolved_summary populated
- backward compat: no session_repository → fields default gracefully
- truth_state observed / inferred / unresolved distinguishable
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceRequest,
    InferenceResult,
    ReasoningMode,
    RoleRoute,
    RunRecord,
    RunStatus,
    TaskContext,
    TaskIntent,
    TaskRole,
)
from iabv_v15.ui.viewmodels.run_history_viewmodel import RunHistoryViewModel


# ─── Helpers ──────────────────────────────────────────────────


def _make_run(run_id: str | None = None, goal: str = 'test') -> RunRecord:
    rid = run_id or uuid4().hex
    return RunRecord(
        run_id=rid,
        request=InferenceRequest(user_goal=goal),
        result=InferenceResult(
            request_id='req',
            provider_name='ollama',
            reasoning_mode=ReasoningMode.LOCAL,
            summary='ok',
            inferred_task=goal,
            confidence=0.9,
            executor_model='fake',
        ),
        route=RoleRoute(
            task_role=TaskRole.KNOWLEDGE,
            role_title='Knowledge',
            provider_name='ollama',
            model_profile_id='m1',
            model_name='fake',
            reason='test',
        ),
        status=RunStatus.SUCCESS,
        duration_ms=100,
    )


def _make_session(
    run_id: str,
    task_packet: dict[str, Any] | None = None,
) -> AdaptiveSession:
    meta: dict[str, Any] = {}
    if task_packet is not None:
        meta['task_packet'] = task_packet
    return AdaptiveSession(
        user_goal='test',
        intent=TaskIntent(
            intent_key='general.assistance',
            summary='test',
            detected_role=TaskRole.KNOWLEDGE,
        ),
        run_id=run_id,
        metadata=meta,
    )


def _build_vm(
    runs: list[RunRecord],
    sessions: list[AdaptiveSession] | None = None,
) -> RunHistoryViewModel:
    run_repo = MagicMock()
    run_repo.list_recent.return_value = runs

    session_repo: MagicMock | None = None
    if sessions is not None:
        session_repo = MagicMock()
        by_run: dict[str, list[AdaptiveSession]] = {}
        for s in sessions:
            by_run.setdefault(s.run_id or '', []).append(s)
        session_repo.find_by_run.side_effect = lambda rid: by_run.get(rid, [])

    return RunHistoryViewModel(
        repository=run_repo,
        session_repository=session_repo,
        defer_initial_refresh=True,
    )


# ─── Tests ────────────────────────────────────────────────────


def test_payload_observed_truth_state() -> None:
    """task_packet with observed evidence_basis → truth_state='observed'."""
    run = _make_run()
    tp = {
        'evidence_basis': {'state': 'observed', 'live_sources': ['world_model'], 'persisted_sources': [], 'unresolved': []},
        'worker_gate_summary': {'ran': True, 'usable': True, 'top_worker': {'email': 'a@b.com', 'tool': 'chatgpt'}, 'available_count': 2},
        'selected_worker': {'email': 'a@b.com', 'tool': 'chatgpt'},
        'governance_flags': {'approval_required': False, 'should_consult': True, 'block_risky_action': False},
        'unresolved': [],
    }
    session = _make_session(run.run_id, tp)
    vm = _build_vm([run], [session])
    vm.refresh()
    payload = vm.runs[0]
    assert payload['truth_state'] == 'observed'


def test_payload_inferred_truth_state() -> None:
    """task_packet with inferred evidence_basis → truth_state='inferred'."""
    run = _make_run()
    tp = {
        'evidence_basis': {'state': 'inferred', 'live_sources': [], 'persisted_sources': ['learning'], 'unresolved': []},
        'worker_gate_summary': {'ran': True, 'usable': True, 'top_worker': {}, 'available_count': 1},
        'selected_worker': {},
        'governance_flags': {'approval_required': False, 'should_consult': False, 'block_risky_action': False},
        'unresolved': [],
    }
    session = _make_session(run.run_id, tp)
    vm = _build_vm([run], [session])
    vm.refresh()
    assert vm.runs[0]['truth_state'] == 'inferred'


def test_payload_unresolved_truth_state() -> None:
    """task_packet with unresolved evidence_basis → truth_state='unresolved'."""
    run = _make_run()
    tp = {
        'evidence_basis': {'state': 'unresolved', 'live_sources': [], 'persisted_sources': [], 'unresolved': ['tool_status', 'env_id']},
        'worker_gate_summary': {'ran': False, 'usable': False, 'top_worker': {}, 'available_count': 0},
        'selected_worker': {},
        'governance_flags': {'approval_required': False, 'should_consult': False, 'block_risky_action': False},
        'unresolved': ['tool_status', 'env_id'],
    }
    session = _make_session(run.run_id, tp)
    vm = _build_vm([run], [session])
    vm.refresh()
    payload = vm.runs[0]
    assert payload['truth_state'] == 'unresolved'
    assert payload['unresolved_count'] == 2
    assert 'tool_status' in payload['unresolved_summary']


def test_selected_worker_visible() -> None:
    """selected_worker_label shows tool + email when worker exists."""
    run = _make_run()
    tp = {
        'evidence_basis': {'state': 'observed'},
        'worker_gate_summary': {'ran': True, 'usable': True, 'top_worker': {'email': 'user@test.com', 'tool': 'claude'}, 'available_count': 3},
        'selected_worker': {'email': 'user@test.com', 'tool': 'claude'},
        'governance_flags': {'approval_required': False},
        'unresolved': [],
    }
    session = _make_session(run.run_id, tp)
    vm = _build_vm([run], [session])
    vm.refresh()
    assert vm.runs[0]['selected_worker_label'] == 'claude (user@test.com)'


def test_gate_ran_false_vs_true_usable_false() -> None:
    """gate_ran=False and gate_ran=True+usable=False are distinguishable."""
    run_no_gate = _make_run(run_id='no_gate')
    tp_no_gate = {
        'evidence_basis': {'state': 'observed'},
        'worker_gate_summary': {'ran': False, 'usable': False, 'top_worker': {}, 'available_count': 0},
        'selected_worker': {},
        'governance_flags': {'approval_required': False},
        'unresolved': [],
    }
    run_blocked = _make_run(run_id='blocked')
    tp_blocked = {
        'evidence_basis': {'state': 'observed'},
        'worker_gate_summary': {'ran': True, 'usable': False, 'top_worker': {}, 'available_count': 0},
        'selected_worker': {},
        'governance_flags': {'approval_required': False},
        'unresolved': [],
    }
    vm = _build_vm(
        [run_no_gate, run_blocked],
        [_make_session('no_gate', tp_no_gate), _make_session('blocked', tp_blocked)],
    )
    vm.refresh()
    p_no = next(r for r in vm.runs if r['run_id'] == 'no_gate')
    p_bl = next(r for r in vm.runs if r['run_id'] == 'blocked')
    assert p_no['gate_ran'] is False
    assert p_bl['gate_ran'] is True
    assert p_bl['gate_usable'] is False


def test_approval_required_reflected() -> None:
    """approval_required from governance_flags appears in payload."""
    run = _make_run()
    tp = {
        'evidence_basis': {'state': 'observed'},
        'worker_gate_summary': {'ran': True, 'usable': True, 'top_worker': {}, 'available_count': 1},
        'selected_worker': {},
        'governance_flags': {'approval_required': True, 'should_consult': True, 'block_risky_action': False},
        'unresolved': [],
    }
    session = _make_session(run.run_id, tp)
    vm = _build_vm([run], [session])
    vm.refresh()
    assert vm.runs[0]['approval_required'] is True


def test_backward_compat_no_session_repository() -> None:
    """Without session_repository, task_packet fields default gracefully."""
    run = _make_run()
    vm = _build_vm([run], sessions=None)
    vm.refresh()
    payload = vm.runs[0]
    assert payload['truth_state'] == ''
    assert payload['selected_worker_label'] == ''
    assert payload['gate_ran'] is False
    assert payload['gate_usable'] is False
    assert payload['gate_available_count'] == 0
    assert payload['approval_required'] is False
    assert payload['unresolved_count'] == 0
    assert payload['unresolved_summary'] == ''


def test_backward_compat_no_task_packet_in_session() -> None:
    """Session exists but no task_packet → defaults gracefully."""
    run = _make_run()
    session = _make_session(run.run_id, task_packet=None)
    vm = _build_vm([run], [session])
    vm.refresh()
    payload = vm.runs[0]
    assert payload['truth_state'] == ''
    assert payload['selected_worker_label'] == ''
    assert payload['unresolved_count'] == 0


def test_existing_properties_not_broken() -> None:
    """Existing payload fields remain intact after adding task_packet fields."""
    run = _make_run(goal='Existing prop test')
    vm = _build_vm([run], sessions=None)
    vm.refresh()
    payload = vm.runs[0]
    assert payload['role_label'] is not None
    assert payload['duration_label'] == '100 ms'
    assert payload['model_label'] == 'fake'
    assert 'run_id' in payload
    assert 'status' in payload
