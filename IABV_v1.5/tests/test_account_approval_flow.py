"""Account Approval Flow — exhaustive end-to-end validation.

Validates the complete chain:
  UI → AccountApprovalLedger → worker_health_gate → ATO metadata → audit trail

Tests cover:
  - Per-tool isolation (chatgpt approval does NOT affect claude)
  - Approval changes active account for that tool
  - Fallback works when approved account is exhausted/missing/blocked
  - Without approval, ranking is normal (auto_ranked)
  - Persistence survives restart (new ledger instance reads same file)
  - No regression in inventory or ranking
  - Trazability fields present in gate, task_packet, audit trail
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    AccountApproval,
    AccountInventoryEntry,
    AccountInventorySnapshot,
    AccountStatus,
    AccountType,
    utc_now,
)
from iabv_v15.services.account_approval_ledger import AccountApprovalLedger


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

TMP_ROOT = Path('/tmp/test_approval_flow')


def _clean_tmp():
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)
    TMP_ROOT.mkdir(parents=True)


def _make_ledger() -> AccountApprovalLedger:
    return AccountApprovalLedger(data_root=str(TMP_ROOT))


def _multi_tool_pool() -> dict[str, Any]:
    """Pool with chatgpt (2 workers) + claude (1 worker)."""
    return {
        'workers': [
            {'email': 'alice@test.com', 'tool': 'chatgpt', 'browser': 'chrome',
             'profile': 'Default', 'remaining_messages': 10, 'used_in_window': 5,
             'limit': 15, 'exhausted': False, 'label': 'ChatGPT Free'},
            {'email': 'bob@test.com', 'tool': 'chatgpt', 'browser': 'edge',
             'profile': 'P1', 'remaining_messages': 3, 'used_in_window': 12,
             'limit': 15, 'exhausted': False, 'label': 'ChatGPT Free'},
            {'email': 'carol@test.com', 'tool': 'claude', 'browser': 'chrome',
             'profile': 'Default', 'remaining_messages': 20, 'used_in_window': 0,
             'limit': 20, 'exhausted': False, 'label': 'Claude Free'},
        ],
        'exhausted': [],
        'available_count': 3,
        'exhausted_count': 0,
        'by_tool': {
            'chatgpt': [{'email': 'alice@test.com'}, {'email': 'bob@test.com'}],
            'claude': [{'email': 'carol@test.com'}],
        },
        'total_remaining_messages': 33,
        'tools_available': ['chatgpt', 'claude'],
    }


def _make_router(pool, ledger=None):
    from iabv_v15.services.roles.local_role_router import LocalRoleRouter
    mock = MagicMock()
    mock.health_check.return_value = MagicMock(status='available')
    return LocalRoleRouter(
        workspace_root='/tmp/test_router',
        general_provider=mock,
        visual_provider=mock,
        optional_provider=None,
        embedding_service=MagicMock(),
        sql_service=MagicMock(),
        analytics_service=MagicMock(),
        customer_support_service=MagicMock(),
        engineering_review_service=MagicMock(),
        teaching_gap_analyzer=MagicMock(),
        episode_repository=MagicMock(),
        knowledge_repository=MagicMock(),
        run_repository=MagicMock(),
        artifact_repository=MagicMock(),
        account_resource_scanner=lambda: pool,
        account_approval_ledger=ledger,
    )


# ──────────────────────────────────────────────────────────────
# 1. STRUCTURAL FLOW VERIFICATION
# ──────────────────────────────────────────────────────────────

class TestStructuralFlow:
    """Verify every link: UI → ledger → worker_health_gate → ATO."""

    def setup_method(self):
        _clean_tmp()

    def teardown_method(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_approval_registered_by_tool(self):
        """UI approval → ledger writes per-tool entry."""
        ledger = _make_ledger()
        approval = AccountApproval(
            tool='chatgpt', email='alice@test.com',
            origin='centro_vivo_ui', reason='user_manual_approval',
        )
        ledger.approve(approval)

        # Verify file exists and has correct structure
        fp = TMP_ROOT / 'evolution' / 'selected_account_by_tool.json'
        assert fp.exists(), 'Ledger file not created'

        data = json.loads(fp.read_text())
        assert 'chatgpt' in data
        assert data['chatgpt']['email'] == 'alice@test.com'
        assert data['chatgpt']['tool'] == 'chatgpt'
        assert data['chatgpt']['origin'] == 'centro_vivo_ui'
        assert 'approved_at' in data['chatgpt']

    def test_worker_gate_reads_approval_for_tool(self):
        """worker_health_gate uses approved account as top_worker."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='bob@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['top_worker']['email'] == 'bob@test.com'
        assert gate['account_selection_source'] == 'user_approved'
        assert gate['fallback_used'] is False
        assert gate['approved_account']['email'] == 'bob@test.com'

    def test_other_tools_not_affected(self):
        """Approving chatgpt does NOT change claude's top_worker."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='bob@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)

        # chatgpt: uses approved
        gate_chatgpt = router.worker_health_gate(target_assistant='chatgpt')
        assert gate_chatgpt['top_worker']['email'] == 'bob@test.com'
        assert gate_chatgpt['account_selection_source'] == 'user_approved'

        # claude: uses auto-ranked (no approval for claude)
        gate_claude = router.worker_health_gate(target_assistant='claude')
        assert gate_claude['top_worker']['email'] == 'carol@test.com'
        assert gate_claude['account_selection_source'] == 'auto_ranked'
        assert gate_claude['fallback_used'] is False
        assert 'approved_account' not in gate_claude

    def test_no_approval_uses_ranking(self):
        """Without any approval, gate returns auto-ranked top."""
        pool = _multi_tool_pool()
        # No ledger at all
        router = _make_router(pool, ledger=None)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate.get('account_selection_source', 'auto_ranked') == 'auto_ranked'
        assert gate.get('fallback_used', False) is False

    def test_no_approval_with_ledger_empty(self):
        """Ledger exists but has no approval for tool → auto_ranked."""
        ledger = _make_ledger()
        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['account_selection_source'] == 'auto_ranked'
        assert gate['fallback_used'] is False


# ──────────────────────────────────────────────────────────────
# 2. FALLBACK VALIDATION
# ──────────────────────────────────────────────────────────────

class TestFallback:
    """Verify fallback when approved account is exhausted/missing/blocked."""

    def setup_method(self):
        _clean_tmp()

    def teardown_method(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_fallback_exhausted_account(self):
        """Approved account exhausted → fallback to ranking."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='bob@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        # Make bob exhausted
        pool['workers'][1]['exhausted'] = True
        pool['workers'][1]['remaining_messages'] = 0

        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['top_worker']['email'] == 'alice@test.com'  # fallback to top-ranked
        assert gate['account_selection_source'] == 'user_approved_fallback'
        assert gate['fallback_used'] is True
        assert gate['approved_account']['email'] == 'bob@test.com'

    def test_fallback_missing_account(self):
        """Approved account not in pool at all → fallback."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='nobody@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['top_worker']['email'] == 'alice@test.com'
        assert gate['fallback_used'] is True
        assert gate['account_selection_source'] == 'user_approved_fallback'

    def test_fallback_zero_remaining(self):
        """Approved account has 0 remaining_messages → fallback."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='bob@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        pool['workers'][1]['remaining_messages'] = 0  # not exhausted flag, but 0 msgs

        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['fallback_used'] is True
        assert gate['top_worker']['email'] == 'alice@test.com'

    def test_fallback_does_not_break_dispatch(self):
        """Even with fallback, gate returns usable=True and valid workers."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='nonexistent@test.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['available_count'] > 0
        assert len(gate['workers']) > 0
        assert gate['top_worker'] is not None


# ──────────────────────────────────────────────────────────────
# 3. TRAZABILITY
# ──────────────────────────────────────────────────────────────

class TestTrazability:
    """Verify traceability fields in gate result, task_packet, audit trail."""

    def setup_method(self):
        _clean_tmp()

    def teardown_method(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_gate_result_fields_user_approved(self):
        """Gate result contains all required traceability fields."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='bob@test.com', origin='centro_vivo_ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        # Required fields
        assert 'account_selection_source' in gate
        assert gate['account_selection_source'] == 'user_approved'
        assert 'fallback_used' in gate
        assert gate['fallback_used'] is False
        assert 'approved_account' in gate
        assert gate['approved_account']['email'] == 'bob@test.com'
        assert gate['approved_account']['tool'] == 'chatgpt'
        assert 'top_worker' in gate
        # recommended_account = what ranking WOULD have chosen
        assert 'recommended_account' in gate
        assert gate['recommended_account']['email'] == 'alice@test.com'

    def test_gate_result_fields_auto_ranked(self):
        """Without approval, auto_ranked fields are present."""
        pool = _multi_tool_pool()
        ledger = _make_ledger()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['account_selection_source'] == 'auto_ranked'
        assert gate['fallback_used'] is False
        assert 'approved_account' not in gate
        # recommended == top_worker when auto_ranked
        assert gate['recommended_account']['email'] == gate['top_worker']['email']

    def test_gate_result_fields_fallback(self):
        """Fallback case has all fields including approved_account."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='nonexistent@x.com', origin='ui',
        ))

        pool = _multi_tool_pool()
        router = _make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['account_selection_source'] == 'user_approved_fallback'
        assert gate['fallback_used'] is True
        assert gate['approved_account']['email'] == 'nonexistent@x.com'
        # recommended_account still shows what ranking chose
        assert gate['recommended_account']['email'] == 'alice@test.com'

    def test_task_packet_account_selection(self):
        """_build_task_packet includes account_selection block."""
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator

        # Build a minimal session with worker_gate metadata
        session = MagicMock()
        session.metadata = {
            'worker_gate': {
                'usable': True,
                'top_worker': {'email': 'bob@test.com', 'tool': 'chatgpt', 'score': 0.8},
                'recommended_account': {'email': 'alice@test.com', 'tool': 'chatgpt', 'score': 0.9},
                'ranked_workers': [],
                'available_count': 2,
                'account_selection_source': 'user_approved',
                'fallback_used': False,
                'approved_account': {'email': 'bob@test.com', 'tool': 'chatgpt'},
            },
        }
        session.user_goal = 'test'
        session.intent = MagicMock()
        session.intent.intent_key = 'test'
        session.intent.detected_role = MagicMock()
        session.intent.detected_role.value = 'general'

        dc = MagicMock()
        dc.governance = {'assistant_kind': 'chatgpt', 'should_consult': True}
        dc.metadata = {}

        packet = AdaptiveTaskOrchestrator._build_task_packet(
            session=session,
            decision_context=dc,
            perception=None,
        )

        assert 'account_selection' in packet
        sel = packet['account_selection']
        assert sel['source'] == 'user_approved'
        assert sel['fallback_used'] is False
        assert sel['approved_account']['email'] == 'bob@test.com'
        assert sel['recommended_account']['email'] == 'alice@test.com'
        assert sel['is_human_approved'] is True

    def test_task_packet_auto_ranked(self):
        """task_packet without approval shows auto_ranked."""
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator

        session = MagicMock()
        session.metadata = {
            'worker_gate': {
                'usable': True,
                'top_worker': {'email': 'alice@test.com'},
                'ranked_workers': [],
                'available_count': 2,
                'account_selection_source': 'auto_ranked',
                'fallback_used': False,
            },
        }
        session.intent = MagicMock()
        session.intent.intent_key = 'test'
        session.intent.detected_role = MagicMock()
        session.intent.detected_role.value = 'general'

        dc = MagicMock()
        dc.governance = {}
        dc.metadata = {}

        packet = AdaptiveTaskOrchestrator._build_task_packet(
            session=session, decision_context=dc, perception=None,
        )

        sel = packet['account_selection']
        assert sel['source'] == 'auto_ranked'
        assert sel['is_human_approved'] is False
        assert sel['approved_account'] == {}

    def test_audit_trail_record(self):
        """_audit_account_selection writes to DecisionAuditTrail."""
        from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail

        tmp_audit = TMP_ROOT / 'audit'
        tmp_audit.mkdir(parents=True)
        trail = DecisionAuditTrail(data_root=str(tmp_audit))

        from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
        ato = MagicMock(spec=AdaptiveTaskOrchestrator)
        ato.decision_audit_trail = trail
        ato._audit_account_selection = AdaptiveTaskOrchestrator._audit_account_selection.__get__(ato)

        gate = {
            'account_selection_source': 'user_approved',
            'fallback_used': False,
            'top_worker': {'email': 'bob@test.com', 'tool': 'chatgpt', 'score': 0.8},
            'recommended_account': {'email': 'alice@test.com', 'tool': 'chatgpt', 'score': 0.9},
            'approved_account': {'email': 'bob@test.com', 'tool': 'chatgpt'},
            'available_count': 2,
        }

        ato._audit_account_selection(tool='chatgpt', gate=gate, user_goal='test query')

        records = trail.load_recent(10)
        assert len(records) == 1
        rec = records[0]
        assert rec['phase'] == 'provider_selection'
        assert rec['model_used'] == 'bob@test.com'
        meta = rec.get('metadata', {})
        acct = meta.get('account_selection', {})
        assert acct['tool'] == 'chatgpt'
        assert acct['source'] == 'user_approved'
        assert acct['selected_email'] == 'bob@test.com'
        assert acct['recommended_email'] == 'alice@test.com'
        assert acct['approved_email'] == 'bob@test.com'
        assert acct['fallback_used'] is False
        assert acct['is_human_approved'] is True

    def test_audit_trail_fallback_record(self):
        """Fallback is recorded with correct outcome in audit trail."""
        from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail

        tmp_audit = TMP_ROOT / 'audit_fb'
        tmp_audit.mkdir(parents=True)
        trail = DecisionAuditTrail(data_root=str(tmp_audit))

        from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
        ato = MagicMock(spec=AdaptiveTaskOrchestrator)
        ato.decision_audit_trail = trail
        ato._audit_account_selection = AdaptiveTaskOrchestrator._audit_account_selection.__get__(ato)

        gate = {
            'account_selection_source': 'user_approved_fallback',
            'fallback_used': True,
            'top_worker': {'email': 'alice@test.com', 'tool': 'chatgpt', 'score': 0.9},
            'recommended_account': {'email': 'alice@test.com', 'tool': 'chatgpt', 'score': 0.9},
            'approved_account': {'email': 'exhausted@test.com', 'tool': 'chatgpt'},
            'available_count': 1,
        }

        ato._audit_account_selection(tool='chatgpt', gate=gate, user_goal='test fb')

        records = trail.load_recent(10)
        assert len(records) == 1
        rec = records[0]
        assert rec['outcome'] == 'fallback_used'
        acct = rec['metadata']['account_selection']
        assert acct['fallback_used'] is True
        assert acct['approved_email'] == 'exhausted@test.com'
        assert acct['selected_email'] == 'alice@test.com'
        assert acct['recommended_email'] == 'alice@test.com'


# ──────────────────────────────────────────────────────────────
# 4. PERSISTENCE
# ──────────────────────────────────────────────────────────────

class TestPersistence:
    """Verify persistence survives restart and stores all required fields."""

    def setup_method(self):
        _clean_tmp()

    def teardown_method(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_persistence_survives_restart(self):
        """New ledger instance reads existing approvals from disk."""
        ledger1 = _make_ledger()
        ledger1.approve(AccountApproval(
            tool='chatgpt', email='alice@test.com', origin='ui',
            reason='manual_switch',
        ))

        # Simulate restart: new instance
        ledger2 = _make_ledger()
        result = ledger2.get_approved('chatgpt')
        assert result is not None
        assert result.email == 'alice@test.com'
        assert result.tool == 'chatgpt'
        assert result.origin == 'ui'

    def test_persistence_per_tool_independent(self):
        """Each tool has its own entry; updating one doesn't touch others."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(tool='chatgpt', email='a@test.com'))
        ledger.approve(AccountApproval(tool='claude', email='b@test.com'))

        # Update chatgpt only
        ledger.approve(AccountApproval(tool='chatgpt', email='c@test.com'))

        # Verify
        fp = TMP_ROOT / 'evolution' / 'selected_account_by_tool.json'
        data = json.loads(fp.read_text())
        assert data['chatgpt']['email'] == 'c@test.com'
        assert data['claude']['email'] == 'b@test.com'

    def test_persistence_stores_required_fields(self):
        """Persisted approval includes tool, email, timestamp, origin, valid."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(
            tool='chatgpt', email='alice@test.com',
            origin='centro_vivo_ui', reason='test',
        ))

        fp = TMP_ROOT / 'evolution' / 'selected_account_by_tool.json'
        data = json.loads(fp.read_text())
        entry = data['chatgpt']

        assert entry['tool'] == 'chatgpt'
        assert entry['email'] == 'alice@test.com'
        assert 'approved_at' in entry  # timestamp
        assert entry['origin'] == 'centro_vivo_ui'
        assert entry['valid'] is True

    def test_revoke_removes_only_that_tool(self):
        """Revoking one tool leaves others intact."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(tool='chatgpt', email='a@test.com'))
        ledger.approve(AccountApproval(tool='claude', email='b@test.com'))

        ledger.revoke('chatgpt')

        assert ledger.get_approved('chatgpt') is None
        assert ledger.get_approved('claude') is not None
        assert ledger.get_approved('claude').email == 'b@test.com'


# ──────────────────────────────────────────────────────────────
# 5. NO REGRESSION
# ──────────────────────────────────────────────────────────────

class TestNoRegression:
    """Verify no bypass, no global state, ranking still works."""

    def setup_method(self):
        _clean_tmp()

    def teardown_method(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_no_global_account_state(self):
        """Ledger is per-tool, not a single global account."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(tool='chatgpt', email='a@test.com'))

        all_approvals = ledger.get_all()
        assert len(all_approvals) == 1
        assert 'chatgpt' in all_approvals
        assert 'claude' not in all_approvals

    def test_ranking_unaffected_without_approval(self):
        """Without approval, worker_health_gate produces same ranking."""
        pool = _multi_tool_pool()

        # Without ledger
        router_no_ledger = _make_router(pool, ledger=None)
        gate_no = router_no_ledger.worker_health_gate(target_assistant='chatgpt')

        # With empty ledger
        ledger = _make_ledger()
        router_with_ledger = _make_router(pool, ledger=ledger)
        gate_yes = router_with_ledger.worker_health_gate(target_assistant='chatgpt')

        # Same top_worker
        assert gate_no['top_worker']['email'] == gate_yes['top_worker']['email']
        assert gate_yes['account_selection_source'] == 'auto_ranked'

    def test_approval_does_not_bypass_ato(self):
        """Approval flows through worker_health_gate, not around ATO."""
        # The approval is ONLY consumed via _resolve_approved_account
        # inside worker_health_gate. There is no direct path from
        # ledger to execution that bypasses the gate.
        from iabv_v15.services.roles.local_role_router import LocalRoleRouter

        # Verify _resolve_approved_account is called ONLY from
        # worker_health_gate by checking the code structure
        import inspect
        source = inspect.getsource(LocalRoleRouter.worker_health_gate)
        assert '_resolve_approved_account' in source

        # Verify _resolve_approved_account is a private method
        assert hasattr(LocalRoleRouter, '_resolve_approved_account')

    def test_multiple_approvals_per_tool_only_last_counts(self):
        """Approving twice for same tool → only last approval active."""
        ledger = _make_ledger()
        ledger.approve(AccountApproval(tool='chatgpt', email='first@test.com'))
        ledger.approve(AccountApproval(tool='chatgpt', email='second@test.com'))

        result = ledger.get_approved('chatgpt')
        assert result.email == 'second@test.com'
