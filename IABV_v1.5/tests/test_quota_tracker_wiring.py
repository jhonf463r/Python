"""Tests for evidence-gated quota tracking in AdaptiveTaskOrchestrator.

Quota is recorded only when the result is non-sandboxed and explicitly binds the
actual tool/account identity to the worker selected during preflight.
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


def test_quota_tracker_revision_changes_after_atomic_usage_write(
    tmp_path: Path,
) -> None:
    from iabv_v15.services.account_resource_scanner import (
        quota_tracker_revision,
        record_message_sent,
    )

    with patch.dict('os.environ', {'IABV_WORKSPACE': str(tmp_path)}):
        quota_dir = tmp_path / 'data' / 'evolution'
        quota_dir.mkdir(parents=True, exist_ok=True)
        before = quota_tracker_revision()

        result = record_message_sent('chatgpt', 'quota-fingerprint@test.com')
        after = quota_tracker_revision()

    assert result['tool'] == 'chatgpt'
    assert before[0] == after[0]
    assert before != after


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


def test_quota_attribution_does_not_count_sandbox_dry_run() -> None:
    result = {
        'status': 'prepared',
        'dry_run': True,
        'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-sandbox-1',
        },
    }
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='unit_test',
        )

    assert tracking == {
        'status': 'NOT_COUNTED',
        'reason': 'sandbox_dry_run',
        'source': 'unit_test',
    }
    mock_quota.assert_not_called()


def test_quota_attribution_requires_actual_account_identity() -> None:
    result = {
        'status': 'prepared',
        'dry_run': False,
        'actual_assistant_kind': 'chatgpt',
    }
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='unit_test',
        )

    assert tracking['status'] == 'UNVERIFIED'
    assert tracking['reason'] == 'actual_account_binding_missing'
    mock_quota.assert_not_called()


def test_quota_attribution_rejects_actual_tool_mismatch() -> None:
    result = {
        'status': 'prepared',
        'dry_run': False,
        'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'claude',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-tool-mismatch-1',
        },
    }
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='unit_test',
        )

    assert tracking['status'] == 'UNVERIFIED'
    assert tracking['reason'] == 'actual_tool_mismatch'
    mock_quota.assert_not_called()


def test_quota_attribution_rejects_account_email_mismatch() -> None:
    result = {
        'status': 'prepared',
        'dry_run': False,
        'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'other@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-email-mismatch-1',
        },
    }
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='governed_dispatch',
        )

    assert tracking['status'] == 'UNVERIFIED'
    assert tracking['reason'] == 'actual_account_mismatch'
    assert tracking['source'] == 'governed_dispatch'
    mock_quota.assert_not_called()


def test_quota_attribution_rejects_missing_dry_run_state() -> None:
    result = {
        'status': 'prepared',
        'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-no-dryrun-1',
        },
    }
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='governed_dispatch',
        )

    assert tracking['status'] == 'UNVERIFIED'
    assert tracking['reason'] == 'dry_run_state_missing'
    mock_quota.assert_not_called()


def test_quota_attribution_records_only_exact_actual_identity() -> None:
    result = {
        'status': 'prepared',
        'dry_run': False,
        'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-exact-1',
        },
    }
    quota = {'tool': 'chatgpt', 'email': 'alice@test.com', 'used_in_window': 1}
    with patch.object(
        AdaptiveTaskOrchestrator,
        '_record_quota_usage',
        return_value=quota,
    ) as mock_quota:
        tracking = AdaptiveTaskOrchestrator._record_quota_usage_if_verified(
            result,
            expected_tool='chatgpt',
            expected_email='alice@test.com',
            source='unit_test',
        )

    assert tracking['status'] == 'RECORDED'
    assert tracking['quota_status'] == quota
    assert tracking['source'] == 'unit_test'
    mock_quota.assert_called_once_with('chatgpt', 'alice@test.com', source='unit_test')


# ---------------------------------------------------------------------------
# 2. govern_adaptive_payload wires quota after successful dispatch
# ---------------------------------------------------------------------------

def test_govern_payload_records_quota_on_prepared_with_actual_identity() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
            'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-govern-1',
        },
            'dry_run': False,
            'reason': 'test',
        },
    )
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


def test_govern_payload_does_not_count_sandbox_dry_run() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
            'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-govern-sandbox-1',
        },
            'dry_run': True,
        },
    )
    dc = _make_dc(governance={'should_consult': True, 'assistant_kind': 'chatgpt'})
    with patch.object(
        orchestrator, '_decision_context_from_payload', return_value=dc,
    ), patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        payload = {'metadata': {}}
        result = orchestrator.govern_adaptive_payload(
            payload, user_goal='test goal', source='test',
        )
        ae = (result.get('metadata') or {}).get('autonomous_evolution') or {}
        assert ae['quota_tracking']['status'] == 'NOT_COUNTED'
        assert ae['quota_tracking']['reason'] == 'sandbox_dry_run'
        mock_quota.assert_not_called()


def test_govern_payload_keeps_missing_account_identity_unverified() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
            'actual_assistant_kind': 'chatgpt',
            'dry_run': False,
        },
    )
    dc = _make_dc(governance={'should_consult': True, 'assistant_kind': 'chatgpt'})
    with patch.object(
        orchestrator, '_decision_context_from_payload', return_value=dc,
    ), patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        payload = {'metadata': {}}
        result = orchestrator.govern_adaptive_payload(
            payload, user_goal='test goal', source='test',
        )
        ae = (result.get('metadata') or {}).get('autonomous_evolution') or {}
        assert ae['quota_tracking']['status'] == 'UNVERIFIED'
        assert ae['quota_tracking']['reason'] == 'actual_account_binding_missing'
        mock_quota.assert_not_called()


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
        gate_result={
            'usable': True,
            'top_worker': {'email': 'alice@test.com', 'tool': 'claude', 'score': 0.9},
            'available_count': 1,
            'ranked_workers': [{'email': 'alice@test.com', 'tool': 'claude'}],
        },
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'claude',
            'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'claude',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-parallel-1',
        },
            'dry_run': False,
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


def test_parallel_comparison_does_not_count_without_actual_account_identity() -> None:
    orchestrator, router, evo_svc = _make_orchestrator(
        gate_result={
            'usable': True,
            'top_worker': {'email': 'alice@test.com', 'tool': 'claude', 'score': 0.9},
            'available_count': 1,
            'ranked_workers': [{'email': 'alice@test.com', 'tool': 'claude'}],
        },
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'claude',
            'actual_assistant_kind': 'claude',
            'dry_run': False,
        },
    )
    with patch.object(
        AdaptiveTaskOrchestrator, '_record_quota_usage',
    ) as mock_quota:
        request = InferenceRequest(user_goal='test', auto_route=False)
        result = orchestrator._run_single_ia_consultation(
            request=request,
            candidate={'assistant_kind': 'claude', 'score': 0.8},
            synaptic_decision=None,
            decision_context=None,
        )
        assert result['quota_tracking']['status'] == 'UNVERIFIED'
        assert result['quota_tracking']['reason'] == 'actual_account_binding_missing'
        mock_quota.assert_not_called()


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
    orchestrator, router, evo_svc = _make_orchestrator(
        evolution_result={
            'status': 'prepared',
            'assistant_kind': 'chatgpt',
            'actual_account_binding': {
            'schema': 'ACCOUNT_BINDING_R1',
            'status': 'VERIFIED',
            'actual_tool': 'chatgpt',
            'account_email': 'alice@test.com',
            'identity_source': 'test_adapter',
            'evidence_ref': 'exec-quota-result-1',
        },
            'dry_run': False,
        },
    )
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



def test_deductive_context_does_not_claim_no_accounts_when_quota_is_corrupt(
    tmp_path: Path, monkeypatch,
) -> None:
    from iabv_v15.services.auto_correction_engine import _build_deductive_context
    class _EmptyToolRegistry:
        def __init__(self, workspace_root: str):
            self.workspace_root = workspace_root

        def list_cards(self):
            return []

    monkeypatch.setattr(
        "iabv_v15.services.tools.tool_registry.ToolRegistry",
        _EmptyToolRegistry,
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.scan_browser_accounts",
        lambda: {"count": 0, "accounts": []},
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.scan_browser_sessions",
        lambda: {"session_count": 0, "by_tool": {}},
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.scan_ollama_api",
        lambda: {"available": False},
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.scan_devin_api",
        lambda: {"available": False},
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.scan_github_api",
        lambda: {"available": False},
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.get_all_quota_status",
        lambda: {
            "statuses": [],
            "total_tracked": 0,
            "source_coverage": {"quota_tracker": "CORRUPT"},
            "source_errors": {"quota_tracker": "JSONDecodeError"},
        },
    )
    monkeypatch.setattr(
        "iabv_v15.services.account_resource_scanner.estimate_available_workers",
        lambda: {
            "workers": [],
            "exhausted": [],
            "unverified": [{
                "tool": "chatgpt",
                "email": "user@test.com",
                "browser": "Chrome",
                "profile": "Default",
            }],
            "unverified_count": 1,
            "available_count": 0,
            "exhausted_count": 0,
            "total_remaining_messages": 0,
            "source_coverage": {"quota_tracker": "CORRUPT"},
        },
    )

    report = _build_deductive_context([], workspace=str(tmp_path))

    assert "Cuotas no verificables (CORRUPT)" in report
    assert "Sesiones detectadas sin cuota verificada: 1" in report
    assert "Sin cuentas rastreadas todavia" not in report
    assert "Sin asistentes con sesion activa detectados" not in report



def test_deductive_rotate_account_preserves_unverified_quota_state() -> None:
    from iabv_v15.services.auto_correction_engine import _execute_rotate_account

    with patch(
        'iabv_v15.services.account_resource_scanner.best_account_for_tool',
        side_effect=RuntimeError('quota_tracker_unverified:corrupt'),
    ):
        result = _execute_rotate_account({
            'tool': 'chatgpt',
            'exhausted_email': 'user@test.com',
            'reason': 'quota exceeded',
        })

    assert result['action'] == 'rotate_account'
    assert result['status'] == 'unverified'
    assert result['detail'] == 'quota_tracker_unverified:corrupt'
    assert 'corrected' != result['status']
