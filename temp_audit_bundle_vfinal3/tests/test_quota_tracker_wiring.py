"""Tests for Fase 2: quota tracker wiring in AdaptiveTaskOrchestrator.

Verifies that ``record_message_sent`` is called through ``_record_quota_usage``
whenever the orchestrator dispatches to an external assistant via
``plan_or_execute``.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from iabv_v15.domain.models import (
    DecisionContext,
    InferenceRequest,
    IntentRouteDecision,
    TaskIntent,
    TaskRole,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    AdaptiveTaskOrchestrator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dc(*, governance: dict | None = None) -> DecisionContext:
    """Build a minimal DecisionContext with required fields."""
    return DecisionContext(
        user_goal='test goal',
        intent=TaskIntent(
            intent_key='research.external_consultation',
            detected_role=TaskRole.RESEARCH,
        ),
        route_decision=IntentRouteDecision(
            detected_role=TaskRole.RESEARCH,
        ),
        governance=governance or {},
    )


def _make_orchestrator(
    *,
    gate_result: dict | None = None,
    evolution_result: dict | None = None,
) -> tuple[AdaptiveTaskOrchestrator, MagicMock, MagicMock]:
    """Build a minimal orchestrator with mocked router + evolution service."""
    router = MagicMock()
    gate = gate_result or {
        'usable': True,
        'top_worker': {'email': 'alice@test.com', 'tool': 'chatgpt', 'score': 0.9},
        'available_count': 1,
        'ranked_workers': [{'email': 'alice@test.com', 'tool': 'chatgpt'}],
    }
    router.worker_health_gate.return_value = gate

    evo_svc = MagicMock()
    evo_result = evolution_result or {
        'status': 'prepared',
        'assistant_kind': 'chatgpt',
        'actual_assistant_kind': 'chatgpt',
        'reason': 'test',
    }
    evo_svc.plan_or_execute.return_value = evo_result

    orchestrator = AdaptiveTaskOrchestrator(
        role_router=router,
        adaptive_session_repository=MagicMock(),
        intent_service=MagicMock(),
        context_assembler=MagicMock(),
        capability_service=MagicMock(),
        strategy_pack_registry=MagicMock(),
        planner_service=MagicMock(),
        approval_gate_service=MagicMock(),
        execution_playbook_service=MagicMock(),
        task_outcome_recorder=MagicMock(),
        autonomous_evolution_service=evo_svc,
    )
    return orchestrator, router, evo_svc


# ---------------------------------------------------------------------------
# 1. _record_quota_usage calls record_message_sent correctly
# ---------------------------------------------------------------------------

def test_record_quota_usage_calls_record_message_sent(tmp_path: Path) -> None:
    with patch.dict('os.environ', {'IABV_WORKSPACE': str(tmp_path)}):
        (tmp_path / 'data' / 'evolution').mkdir(parents=True, exist_ok=True)
        result = AdaptiveTaskOrchestrator._record_quota_usage(
            'chatgpt', 'alice@test.com',
        )
        assert result is not None
        assert result['tool'] == 'chatgpt'
        assert result['email'] == 'alice@test.com'
        assert result['used_in_window'] >= 1
        assert result['total_sent_all_time'] >= 1

        qf = tmp_path / 'data' / 'evolution' / 'quota_tracker.json'
        assert qf.exists()
        state = json.loads(qf.read_text(encoding='utf-8'))
        assert 'chatgpt:alice@test.com' in state['accounts']


def test_record_quota_usage_noop_without_tool() -> None:
    assert AdaptiveTaskOrchestrator._record_quota_usage('', 'alice@test.com') is None


def test_record_quota_usage_noop_without_email() -> None:
    assert AdaptiveTaskOrchestrator._record_quota_usage('chatgpt', '') is None


def test_record_quota_usage_never_raises() -> None:
    with patch(
        'iabv_v15.services.account_resource_scanner.record_message_sent',
        side_effect=RuntimeError('disk full'),
    ):
        result = AdaptiveTaskOrchestrator._record_quota_usage(
            'chatgpt', 'alice@test.com',
        )
        assert result is None


# ---------------------------------------------------------------------------
# 2. govern_adaptive_payload wires quota after successful dispatch
# ---------------------------------------------------------------------------

def test_govern_payload_records_quota_on_prepared() -> None:
    orchestrator, router, evo_svc = _make_orchestrator()
    dc = _make_dc(governance={'should_consult': True, 'assistant_kind': 'chatgpt'})
    with patch.object(
        orchestrator, '_decision_context_from_payload', return_value=dc,
    ), patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage', return_value={'used_in_window': 1},
    ) as mock_quota:
        payload = {'metadata': {}}
        orchestrator.govern_adaptive_payload(
            payload, user_goal='test goal', source='test',
        )
        mock_quota.assert_called_once()
        call_args = mock_quota.call_args
        assert call_args[0][0] == 'chatgpt'
        assert call_args[0][1] == 'alice@test.com'


def test_govern_payload_skips_quota_on_noop() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={'status': 'noop', 'assistant_kind': '', 'reason': 'not needed'},
    )
    dc = _make_dc(governance={'should_consult': False})
    with patch.object(
        orchestrator, '_decision_context_from_payload', return_value=dc,
    ), patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        payload = {'metadata': {}}
        orchestrator.govern_adaptive_payload(
            payload, user_goal='test', source='test',
        )
        mock_quota.assert_not_called()


def test_govern_payload_skips_quota_on_failed() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={'status': 'failed', 'assistant_kind': 'chatgpt', 'reason': 'err'},
    )
    dc = _make_dc(governance={'should_consult': True, 'assistant_kind': 'chatgpt'})
    with patch.object(
        orchestrator, '_decision_context_from_payload', return_value=dc,
    ), patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        payload = {'metadata': {}}
        orchestrator.govern_adaptive_payload(
            payload, user_goal='test', source='test',
        )
        mock_quota.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Parallel comparison path records quota
# ---------------------------------------------------------------------------

def test_parallel_comparison_records_quota() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'claude',
            'actual_assistant_kind': 'claude',
        },
    )
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage', return_value={'used_in_window': 1},
    ) as mock_quota:
        request = InferenceRequest(user_goal='test', auto_route=False)
        result = orchestrator._run_single_ia_consultation(
            request=request,
            candidate={'assistant_kind': 'claude', 'score': 0.8},
            synaptic_decision=None,
            decision_context=None,
        )
        mock_quota.assert_called_once()
        assert result.get('quota_status') is not None


def test_parallel_comparison_skips_quota_on_noop() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={'status': 'noop', 'assistant_kind': '', 'reason': 'not needed'},
    )
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        request = InferenceRequest(user_goal='test', auto_route=False)
        orchestrator._run_single_ia_consultation(
            request=request,
            candidate={'assistant_kind': 'claude', 'score': 0.8},
            synaptic_decision=None,
            decision_context=None,
        )
        mock_quota.assert_not_called()


# ---------------------------------------------------------------------------
# 4. quota_status flows into result dict
# ---------------------------------------------------------------------------

def test_quota_status_in_govern_result(tmp_path: Path) -> None:
    orchestrator, router, evo_svc = _make_orchestrator()
    dc = _make_dc(governance={'should_consult': True, 'assistant_kind': 'chatgpt'})
    with patch.dict('os.environ', {'IABV_WORKSPACE': str(tmp_path)}):
        (tmp_path / 'data' / 'evolution').mkdir(parents=True, exist_ok=True)
        with patch.object(
            orchestrator, '_decision_context_from_payload', return_value=dc,
        ):
            payload = {'metadata': {}}
            result = orchestrator.govern_adaptive_payload(
                payload, user_goal='test', source='test',
            )
            ae = (result.get('metadata') or {}).get('autonomous_evolution') or {}
            assert 'quota_status' in ae
            assert ae['quota_status']['tool'] == 'chatgpt'


# ---------------------------------------------------------------------------
# 5. Cumulative counting: two dispatches = total_sent_all_time >= 2
# ---------------------------------------------------------------------------

def test_cumulative_quota_counting(tmp_path: Path) -> None:
    with patch.dict('os.environ', {'IABV_WORKSPACE': str(tmp_path)}):
        (tmp_path / 'data' / 'evolution').mkdir(parents=True, exist_ok=True)

        r1 = AdaptiveTaskOrchestrator._record_quota_usage('chatgpt', 'bob@test.com')
        r2 = AdaptiveTaskOrchestrator._record_quota_usage('chatgpt', 'bob@test.com')

        assert r1 is not None and r2 is not None
        assert r2['total_sent_all_time'] == 2
        assert r2['used_in_window'] == 2
