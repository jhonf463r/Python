"""Tests for Fase 5 — Resume-Aware Orchestration.

Verifies:
1. _load_resume_context returns startup_summary when service is wired
2. _load_resume_context returns {} when service is None
3. _load_resume_context returns {} when startup_summary crashes
4. Resume hints are injected into session.metadata
5. _resume_loaded flag prevents repeated loading
6. _build_task_packet includes resume_context and has_resume_hints
"""

from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    DecisionContext,
    ExecutionPlaybook,
    IntentRouteDecision,
    PerceptionSnapshot,
    TaskContext,
    TaskIntent,
    TaskRole,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    AdaptiveTaskOrchestrator,
)


def _make_ato(**overrides) -> AdaptiveTaskOrchestrator:
    """Build a minimal ATO with mocked dependencies."""
    defaults = dict(
        role_router=MagicMock(),
        adaptive_session_repository=MagicMock(),
        intent_service=MagicMock(),
        context_assembler=MagicMock(),
        capability_service=MagicMock(),
        strategy_pack_registry=MagicMock(),
        planner_service=MagicMock(),
        approval_gate_service=MagicMock(),
        execution_playbook_service=MagicMock(),
        task_outcome_recorder=MagicMock(),
    )
    defaults.update(overrides)
    return AdaptiveTaskOrchestrator(**defaults)


_FAKE_SUMMARY = {
    'actionable_tasks': [
        {'id': 't1', 'title': 'Finish auth refactor', 'priority': 'high'},
    ],
    'blocked_tasks': [],
    'resume_hints': [
        {
            'session_id': 'sess-001',
            'user_goal': 'Implementar login OAuth',
            'handoff_required': True,
            'last_status': 'interrupted',
        },
        {
            'session_id': 'sess-002',
            'user_goal': 'Fix JSONL corruption',
            'handoff_required': False,
            'last_status': 'partial',
        },
    ],
    'queue_summary': {'total': 3, 'actionable': 1, 'blocked': 0},
}


# ------------------------------------------------------------------ #
# 1. _load_resume_context returns summary when service is wired
# ------------------------------------------------------------------ #


def test_load_resume_context_returns_summary():
    mock_acs = MagicMock()
    mock_acs.startup_summary.return_value = _FAKE_SUMMARY
    ato = _make_ato(autonomy_cycle_service=mock_acs)

    result = ato._load_resume_context()

    assert result == _FAKE_SUMMARY
    mock_acs.startup_summary.assert_called_once()


# ------------------------------------------------------------------ #
# 2. _load_resume_context returns {} without service
# ------------------------------------------------------------------ #


def test_load_resume_context_without_service():
    ato = _make_ato(autonomy_cycle_service=None)

    result = ato._load_resume_context()

    assert result == {}


# ------------------------------------------------------------------ #
# 3. _load_resume_context handles crash
# ------------------------------------------------------------------ #


def test_load_resume_context_handles_crash():
    mock_acs = MagicMock()
    mock_acs.startup_summary.side_effect = RuntimeError('db locked')
    ato = _make_ato(autonomy_cycle_service=mock_acs)

    result = ato._load_resume_context()

    assert result == {}


# ------------------------------------------------------------------ #
# 4. Resume hints injected in session metadata
# ------------------------------------------------------------------ #


def test_resume_hints_injected_in_session_metadata():
    mock_acs = MagicMock()
    mock_acs.startup_summary.return_value = _FAKE_SUMMARY
    ato = _make_ato(autonomy_cycle_service=mock_acs)

    session = AdaptiveSession(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='general.assistance',
            detected_role=TaskRole.KNOWLEDGE,
        ),
        status=AdaptiveSessionStatus.PLANNED,
        metadata={},
    )

    # Simulate what _handle_request_body does for resume loading
    if not session.metadata.get('_resume_loaded'):
        _resume = ato._load_resume_context()
        if _resume.get('resume_hints'):
            session.metadata['resume_context'] = _resume
            session.metadata['has_resume_hints'] = True
            session.metadata['resume_hint_count'] = len(_resume['resume_hints'])
        session.metadata['_resume_loaded'] = True

    assert session.metadata['has_resume_hints'] is True
    assert session.metadata['resume_hint_count'] == 2
    assert session.metadata['resume_context'] == _FAKE_SUMMARY
    assert session.metadata['_resume_loaded'] is True


# ------------------------------------------------------------------ #
# 5. _resume_loaded prevents repeated loading
# ------------------------------------------------------------------ #


def test_resume_loaded_only_once():
    mock_acs = MagicMock()
    mock_acs.startup_summary.return_value = _FAKE_SUMMARY
    ato = _make_ato(autonomy_cycle_service=mock_acs)

    session = AdaptiveSession(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='general.assistance',
            detected_role=TaskRole.KNOWLEDGE,
        ),
        status=AdaptiveSessionStatus.PLANNED,
        metadata={},
    )

    # First load
    if not session.metadata.get('_resume_loaded'):
        _resume = ato._load_resume_context()
        if _resume.get('resume_hints'):
            session.metadata['resume_context'] = _resume
            session.metadata['has_resume_hints'] = True
            session.metadata['resume_hint_count'] = len(_resume['resume_hints'])
        session.metadata['_resume_loaded'] = True

    assert mock_acs.startup_summary.call_count == 1

    # Second load — should be skipped
    if not session.metadata.get('_resume_loaded'):
        _resume = ato._load_resume_context()
        if _resume.get('resume_hints'):
            session.metadata['resume_context'] = _resume

    # Still only called once
    assert mock_acs.startup_summary.call_count == 1


# ------------------------------------------------------------------ #
# 6. _build_task_packet includes resume_context and has_resume_hints
# ------------------------------------------------------------------ #


def test_build_task_packet_includes_resume_context():
    session = AdaptiveSession(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='general.assistance',
            detected_role=TaskRole.KNOWLEDGE,
        ),
        status=AdaptiveSessionStatus.PLANNED,
        metadata={
            'resume_context': _FAKE_SUMMARY,
            'has_resume_hints': True,
        },
    )

    intent = TaskIntent(intent_key='general.assistance', detected_role=TaskRole.KNOWLEDGE)
    route = IntentRouteDecision(detected_role=TaskRole.KNOWLEDGE)
    decision_context = DecisionContext(user_goal='test goal', intent=intent, route_decision=route)

    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session,
        decision_context=decision_context,
        perception=None,
    )

    assert packet['has_resume_hints'] is True
    assert packet['resume_context'] == _FAKE_SUMMARY
    assert len(packet['resume_context']['resume_hints']) == 2


def test_build_task_packet_no_resume_context():
    """When no resume hints exist, packet shows empty context."""
    session = AdaptiveSession(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='general.assistance',
            detected_role=TaskRole.KNOWLEDGE,
        ),
        status=AdaptiveSessionStatus.PLANNED,
        metadata={},
    )

    intent = TaskIntent(intent_key='general.assistance', detected_role=TaskRole.KNOWLEDGE)
    route = IntentRouteDecision(detected_role=TaskRole.KNOWLEDGE)
    decision_context = DecisionContext(user_goal='test goal', intent=intent, route_decision=route)

    packet = AdaptiveTaskOrchestrator._build_task_packet(
        session=session,
        decision_context=decision_context,
        perception=None,
    )

    assert packet['has_resume_hints'] is False
    assert packet['resume_context'] == {}
