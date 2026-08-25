"""Account Inventory & Continuity Layer — focused tests.

Covers:
- Domain model construction (AccountInventoryEntry, AccountInventorySnapshot)
- Snapshot building via build_inventory_snapshot (mocked scanner data)
- Continuity queue ranking (score-based ordering)
- Control Master projection (_project_account_inventory)
- PortableContext export (_account_inventory_continuity_section)
- ViewModel data and approval slot
"""

from __future__ import annotations

import json
import shutil
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from iabv_v15.domain.models import (
    AccountInventoryEntry,
    AccountInventorySnapshot,
    AccountStatus,
    AccountType,
    utc_now,
)


# ──────────────────────────────────────────────────────────────
# 1. Domain model construction
# ──────────────────────────────────────────────────────────────

class TestAccountInventoryEntry:
    def test_defaults(self):
        entry = AccountInventoryEntry(email="user@test.com")
        assert entry.email == "user@test.com"
        assert entry.browser == ""
        assert entry.tool == ""
        assert entry.has_session is False
        assert entry.quota_remaining == 0
        assert entry.quota_limit == 0
        assert entry.exhausted is False
        assert entry.account_type == AccountType.UNKNOWN
        assert entry.block_signals == []
        assert entry.score == 0.0
        assert entry.status == AccountStatus.UNRESOLVED
        assert entry.unresolved == []
        assert entry.metadata == {}

    def test_full_construction(self):
        now = utc_now()
        entry = AccountInventoryEntry(
            email="dev@example.com",
            browser="chrome",
            profile="Default",
            tool="chatgpt",
            has_session=True,
            session_verified_at=now,
            quota_remaining=10,
            quota_limit=15,
            quota_resets_at=now,
            exhausted=False,
            account_type=AccountType.TRIAL,
            block_signals=["rate_limited"],
            score=0.75,
            status=AccountStatus.ACTIVE,
            unresolved=["UNRESOLVED:cookie_validity"],
            metadata={"label": "ChatGPT Free"},
        )
        assert entry.tool == "chatgpt"
        assert entry.score == 0.75
        assert entry.status == AccountStatus.ACTIVE
        assert entry.account_type == AccountType.TRIAL
        assert "rate_limited" in entry.block_signals

    def test_serialization_roundtrip(self):
        entry = AccountInventoryEntry(
            email="a@b.com", tool="claude", score=0.5,
            status=AccountStatus.EXHAUSTED,
        )
        data = entry.model_dump(mode="json")
        assert data["email"] == "a@b.com"
        assert data["status"] == "exhausted"
        restored = AccountInventoryEntry.model_validate(data)
        assert restored.email == entry.email
        assert restored.status == entry.status


class TestAccountInventorySnapshot:
    def test_empty_snapshot(self):
        snap = AccountInventorySnapshot()
        assert snap.entries == []
        assert snap.continuity_queue == []
        assert snap.active_count == 0
        assert snap.exhausted_count == 0
        assert snap.total_remaining_messages == 0
        assert snap.tools_available == []
        assert snap.unresolved_items == []

    def test_snapshot_with_entries(self):
        e1 = AccountInventoryEntry(
            email="a@t.com", tool="chatgpt", score=0.9,
            status=AccountStatus.ACTIVE, quota_remaining=10,
        )
        e2 = AccountInventoryEntry(
            email="b@t.com", tool="claude", score=0.3,
            status=AccountStatus.EXHAUSTED, exhausted=True,
        )
        snap = AccountInventorySnapshot(
            entries=[e1, e2],
            continuity_queue=[e1],
            active_count=1,
            exhausted_count=1,
            total_remaining_messages=10,
            tools_available=["chatgpt"],
            unresolved_items=["UNRESOLVED:test"],
        )
        assert len(snap.entries) == 2
        assert len(snap.continuity_queue) == 1
        assert snap.continuity_queue[0].email == "a@t.com"
        assert snap.active_count == 1
        assert snap.exhausted_count == 1

    def test_serialization_roundtrip(self):
        e = AccountInventoryEntry(email="x@y.com", tool="codex")
        snap = AccountInventorySnapshot(entries=[e], active_count=1)
        data = snap.model_dump(mode="json")
        assert data["active_count"] == 1
        restored = AccountInventorySnapshot.model_validate(data)
        assert len(restored.entries) == 1
        assert restored.entries[0].email == "x@y.com"


# ──────────────────────────────────────────────────────────────
# 2. Snapshot building (build_inventory_snapshot)
# ──────────────────────────────────────────────────────────────

def _mock_pool() -> dict[str, Any]:
    """Simulated worker pool from estimate_available_workers."""
    return {
        'workers': [
            {
                'email': 'user1@test.com',
                'full_name': 'User One',
                'tool': 'chatgpt',
                'browser': 'chrome',
                'profile': 'Default',
                'remaining_messages': 10,
                'used_in_window': 5,
                'limit': 15,
                'window_hours': 3,
                'exhausted': False,
                'label': 'ChatGPT Free',
                'resets_at': None,
            },
            {
                'email': 'user2@test.com',
                'full_name': 'User Two',
                'tool': 'claude',
                'browser': 'edge',
                'profile': 'Profile 1',
                'remaining_messages': 5,
                'used_in_window': 15,
                'limit': 20,
                'window_hours': 8,
                'exhausted': False,
                'label': 'Claude Free',
                'resets_at': None,
            },
        ],
        'exhausted': [
            {
                'email': 'user3@test.com',
                'full_name': 'User Three',
                'tool': 'chatgpt',
                'browser': 'firefox',
                'profile': 'default-release',
                'remaining_messages': 0,
                'used_in_window': 15,
                'limit': 15,
                'window_hours': 3,
                'exhausted': True,
                'label': 'ChatGPT Free',
                'resets_at': '2026-05-03T20:00:00+00:00',
            },
        ],
        'available_count': 2,
        'exhausted_count': 1,
        'by_tool': {
            'chatgpt': [{'email': 'user1@test.com'}],
            'claude': [{'email': 'user2@test.com'}],
        },
        'total_remaining_messages': 15,
        'tools_available': ['chatgpt', 'claude'],
    }


def _mock_quota() -> dict[str, Any]:
    return {
        'statuses': [
            {'tool': 'chatgpt', 'email': 'user1@test.com', 'remaining': 10, 'exhausted': False, 'used_in_window': 5},
            {'tool': 'claude', 'email': 'user2@test.com', 'remaining': 5, 'exhausted': False, 'used_in_window': 15},
            {'tool': 'chatgpt', 'email': 'user3@test.com', 'remaining': 0, 'exhausted': True, 'used_in_window': 15},
        ],
        'total_tracked': 3,
        'exhausted_count': 1,
        'available_count': 2,
    }


def _mock_ranked(target: str, *, pool=None, block_signals=None) -> list[dict[str, Any]]:
    """Simulated ranked workers from rank_workers_for_target."""
    return [
        {'email': 'user1@test.com', 'tool': 'chatgpt', 'browser': 'chrome',
         'profile': 'Default', 'score': 0.85, 'remaining_messages': 10},
        {'email': 'user2@test.com', 'tool': 'claude', 'browser': 'edge',
         'profile': 'Profile 1', 'score': 0.60, 'remaining_messages': 5},
    ]


class TestBuildInventorySnapshot:
    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_basic_snapshot(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
        snap = build_inventory_snapshot()

        assert isinstance(snap, AccountInventorySnapshot)
        assert len(snap.entries) == 3  # 2 available + 1 exhausted
        assert snap.active_count == 2
        assert snap.exhausted_count == 1
        assert snap.total_remaining_messages == 15

    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_continuity_queue_order(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
        snap = build_inventory_snapshot()

        assert len(snap.continuity_queue) == 2
        # First entry should have highest score
        assert snap.continuity_queue[0].score >= snap.continuity_queue[1].score
        assert snap.continuity_queue[0].email == 'user1@test.com'

    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_exhausted_not_in_queue(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
        snap = build_inventory_snapshot()

        queue_emails = [e.email for e in snap.continuity_queue]
        assert 'user3@test.com' not in queue_emails

    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_unresolved_items(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
        snap = build_inventory_snapshot()

        assert any('UNRESOLVED' in u for u in snap.unresolved_items)

    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_tools_available(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.services.account_resource_scanner import build_inventory_snapshot
        snap = build_inventory_snapshot()

        assert 'chatgpt' in snap.tools_available
        assert 'claude' in snap.tools_available


# ──────────────────────────────────────────────────────────────
# 3. Control Master projection
# ──────────────────────────────────────────────────────────────

class _FakeControlMasterRepo:
    def __init__(self):
        self._state = None

    def load_latest_state(self):
        return self._state

    def save_state(self, state):
        self._state = state
        return state

    def list_rules(self):
        return []

    def list_decisions(self):
        return []


class TestControlMasterProjection:
    def test_scanner_not_connected(self):
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        repo = _FakeControlMasterRepo()
        service = ControlMasterService(repository=repo)
        state = service.current_state()
        inv = state.metadata.get('account_inventory', {})
        assert inv['status'] == 'scanner_not_connected'
        assert any('UNRESOLVED' in u for u in inv.get('unresolved_items', []))

    def test_scanner_returns_snapshot(self):
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        repo = _FakeControlMasterRepo()

        entry = AccountInventoryEntry(
            email="test@test.com", tool="chatgpt",
            score=0.8, quota_remaining=10, quota_limit=15,
            status=AccountStatus.ACTIVE,
        )
        snapshot = AccountInventorySnapshot(
            entries=[entry],
            continuity_queue=[entry],
            active_count=1,
            exhausted_count=0,
            total_remaining_messages=10,
            tools_available=["chatgpt"],
            unresolved_items=["UNRESOLVED:test_item"],
        )

        service = ControlMasterService(
            repository=repo,
            account_resource_scanner=snapshot,
        )
        state = service.current_state()
        inv = state.metadata.get('account_inventory', {})
        assert inv['status'] == 'ok'
        assert inv['active_count'] == 1
        assert inv['exhausted_count'] == 0
        assert inv['total_remaining_messages'] == 10
        assert inv['next_recommended'] is not None
        assert inv['next_recommended']['email'] == 'test@test.com'

    def test_scanner_callable(self):
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        repo = _FakeControlMasterRepo()

        entry = AccountInventoryEntry(
            email="call@test.com", tool="claude", score=0.5,
            status=AccountStatus.ACTIVE, quota_remaining=5,
        )
        snapshot = AccountInventorySnapshot(
            entries=[entry], continuity_queue=[entry],
            active_count=1, total_remaining_messages=5,
            tools_available=["claude"],
        )

        service = ControlMasterService(
            repository=repo,
            account_resource_scanner=lambda: snapshot,
        )
        state = service.current_state()
        inv = state.metadata['account_inventory']
        assert inv['status'] == 'ok'
        assert inv['next_recommended']['email'] == 'call@test.com'

    def test_unresolved_propagated(self):
        from iabv_v15.services.evolution.control_master_service import ControlMasterService
        repo = _FakeControlMasterRepo()

        snapshot = AccountInventorySnapshot(
            unresolved_items=["UNRESOLVED:cookie_validity"],
        )
        service = ControlMasterService(
            repository=repo,
            account_resource_scanner=snapshot,
        )
        state = service.current_state()
        assert "UNRESOLVED:cookie_validity" in state.unresolved_items


# ──────────────────────────────────────────────────────────────
# 4. PortableContext export
# ──────────────────────────────────────────────────────────────

class TestPortableContextSection:
    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_section_creation(self, mock_pool, mock_quota, mock_ranked):
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        tmp = Path('/tmp/test_pc_account_inv')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        storage = ArtifactStorage(str(tmp))

        service = PortableContextService(
            workspace_root=str(tmp),
            storage=storage,
        )
        now = utc_now()
        section = service._account_inventory_continuity_section(now=now)

        assert section.section_id == 'account_inventory_continuity'
        assert section.title == 'Inventario de cuentas y cola de continuidad'
        assert section.confidence > 0.0
        assert len(section.items) > 0
        assert section.metadata.get('requires_human_approval') is True

        shutil.rmtree(tmp, ignore_errors=True)

    def test_section_handles_scanner_failure(self):
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        tmp = Path('/tmp/test_pc_account_inv_fail')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        storage = ArtifactStorage(str(tmp))

        service = PortableContextService(
            workspace_root=str(tmp),
            storage=storage,
        )
        now = utc_now()

        with patch(
            'iabv_v15.services.account_resource_scanner.build_inventory_snapshot',
            side_effect=RuntimeError("scanner unavailable"),
        ):
            section = service._account_inventory_continuity_section(now=now)
            assert section.confidence == 0.0
            assert any('UNRESOLVED' in f for f in (section.unresolved_fields or []))

        shutil.rmtree(tmp, ignore_errors=True)


# ──────────────────────────────────────────────────────────────
# 5. ViewModel (no PySide6 required — mock Qt)
# ──────────────────────────────────────────────────────────────

class TestViewModelAccountInventory:
    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_build_account_inventory(self, mock_pool, mock_quota, mock_ranked):
        """Test _build_account_inventory returns structured data."""
        from iabv_v15.ui.viewmodels.centro_vivo_viewmodel import CentroVivoViewModel
        vm = CentroVivoViewModel(defer_initial_refresh=False)
        result = vm._build_account_inventory()
        assert 'entries' in result
        assert 'summary' in result
        assert len(result['entries']) == 3
        summary = result['summary']
        assert summary['active_count'] == 2
        assert summary['exhausted_count'] == 1
        assert summary['requires_human_approval'] is True
        assert summary['next_recommended'] is not None

    @patch('iabv_v15.services.account_resource_scanner.rank_workers_for_target', side_effect=_mock_ranked)
    @patch('iabv_v15.services.account_resource_scanner.get_all_quota_status', side_effect=_mock_quota)
    @patch('iabv_v15.services.account_resource_scanner.estimate_available_workers', side_effect=_mock_pool)
    def test_approve_account_switch(self, mock_pool, mock_quota, mock_ranked):
        """Test approveAccountSwitch persists via ledger."""
        tmp = Path('/tmp/test_vm_approval')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        from iabv_v15.ui.viewmodels.centro_vivo_viewmodel import CentroVivoViewModel
        vm = CentroVivoViewModel(defer_initial_refresh=False, data_root=str(tmp))
        vm.approveAccountSwitch("chatgpt", "user1@test.com")

        ledger_file = tmp / 'evolution' / 'selected_account_by_tool.json'
        assert ledger_file.exists()
        data = json.loads(ledger_file.read_text())
        assert 'chatgpt' in data
        assert data['chatgpt']['email'] == 'user1@test.com'
        assert data['chatgpt']['origin'] == 'centro_vivo_ui'
        assert 'approved_at' in data['chatgpt']

        shutil.rmtree(tmp, ignore_errors=True)


# ──────────────────────────────────────────────────────────────
# 6. AccountApprovalLedger
# ──────────────────────────────────────────────────────────────

class TestAccountApprovalLedger:
    def _make_ledger(self, tmp: Path):
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        return AccountApprovalLedger(data_root=str(tmp))

    def test_approve_and_read(self):
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        tmp = Path('/tmp/test_ledger_basic')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        ledger = AccountApprovalLedger(data_root=str(tmp))

        approval = AccountApproval(tool='chatgpt', email='a@b.com', origin='ui')
        ledger.approve(approval)

        result = ledger.get_approved('chatgpt')
        assert result is not None
        assert result.email == 'a@b.com'
        assert result.tool == 'chatgpt'
        shutil.rmtree(tmp, ignore_errors=True)

    def test_per_tool_isolation(self):
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        tmp = Path('/tmp/test_ledger_isolation')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        ledger = AccountApprovalLedger(data_root=str(tmp))

        ledger.approve(AccountApproval(tool='chatgpt', email='a@b.com'))
        ledger.approve(AccountApproval(tool='claude', email='c@d.com'))

        chatgpt = ledger.get_approved('chatgpt')
        claude = ledger.get_approved('claude')
        assert chatgpt is not None and chatgpt.email == 'a@b.com'
        assert claude is not None and claude.email == 'c@d.com'

        # Approving chatgpt does NOT change claude
        ledger.approve(AccountApproval(tool='chatgpt', email='x@y.com'))
        assert ledger.get_approved('chatgpt').email == 'x@y.com'
        assert ledger.get_approved('claude').email == 'c@d.com'
        shutil.rmtree(tmp, ignore_errors=True)

    def test_revoke(self):
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        tmp = Path('/tmp/test_ledger_revoke')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        ledger = AccountApprovalLedger(data_root=str(tmp))

        ledger.approve(AccountApproval(tool='chatgpt', email='a@b.com'))
        assert ledger.revoke('chatgpt') is True
        assert ledger.get_approved('chatgpt') is None
        assert ledger.revoke('chatgpt') is False
        shutil.rmtree(tmp, ignore_errors=True)

    def test_get_all(self):
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        tmp = Path('/tmp/test_ledger_all')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        ledger = AccountApprovalLedger(data_root=str(tmp))

        ledger.approve(AccountApproval(tool='chatgpt', email='a@b.com'))
        ledger.approve(AccountApproval(tool='claude', email='c@d.com'))
        all_approvals = ledger.get_all()
        assert len(all_approvals) == 2
        assert 'chatgpt' in all_approvals
        assert 'claude' in all_approvals
        shutil.rmtree(tmp, ignore_errors=True)

    def test_persistence_survives_reload(self):
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
        tmp = Path('/tmp/test_ledger_persist')
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)

        ledger1 = AccountApprovalLedger(data_root=str(tmp))
        ledger1.approve(AccountApproval(tool='chatgpt', email='a@b.com'))

        # New instance reads from disk
        ledger2 = AccountApprovalLedger(data_root=str(tmp))
        result = ledger2.get_approved('chatgpt')
        assert result is not None
        assert result.email == 'a@b.com'
        shutil.rmtree(tmp, ignore_errors=True)


# ──────────────────────────────────────────────────────────────
# 7. Worker health gate with account approval
# ──────────────────────────────────────────────────────────────

class _FakeLedger:
    """Minimal ledger stub for worker_health_gate tests."""
    def __init__(self):
        self._state: dict[str, Any] = {}

    def approve(self, tool: str, email: str):
        from iabv_v15.domain.models import AccountApproval
        a = AccountApproval(tool=tool, email=email, origin='test')
        self._state[tool] = a

    def get_approved(self, tool: str):
        return self._state.get(tool)

    def get_all(self):
        return dict(self._state)


class TestWorkerHealthGateApproval:
    def _make_router(self, scanner_pool, ledger=None):
        """Create a LocalRoleRouter with minimal fakes for worker gate tests."""
        from iabv_v15.services.roles.local_role_router import LocalRoleRouter
        from unittest.mock import MagicMock

        mock_provider = MagicMock()
        mock_provider.health_check.return_value = MagicMock(status='available')
        mock_embedding = MagicMock()
        mock_embedding.health_check.return_value = MagicMock(status='available')

        router = LocalRoleRouter(
            workspace_root='/tmp/test_router',
            general_provider=mock_provider,
            visual_provider=mock_provider,
            optional_provider=None,
            embedding_service=mock_embedding,
            sql_service=MagicMock(),
            analytics_service=MagicMock(),
            customer_support_service=MagicMock(),
            engineering_review_service=MagicMock(),
            teaching_gap_analyzer=MagicMock(),
            episode_repository=MagicMock(),
            knowledge_repository=MagicMock(),
            run_repository=MagicMock(),
            artifact_repository=MagicMock(),
            account_resource_scanner=lambda: scanner_pool,
            account_approval_ledger=ledger,
        )
        return router

    def _pool_with_workers(self):
        return {
            'workers': [
                {'email': 'a@test.com', 'tool': 'chatgpt', 'browser': 'chrome',
                 'profile': 'Default', 'remaining_messages': 10, 'used_in_window': 5,
                 'limit': 15, 'exhausted': False, 'label': 'ChatGPT Free'},
                {'email': 'b@test.com', 'tool': 'chatgpt', 'browser': 'edge',
                 'profile': 'Profile 1', 'remaining_messages': 5, 'used_in_window': 10,
                 'limit': 15, 'exhausted': False, 'label': 'ChatGPT Free'},
            ],
            'exhausted': [],
            'available_count': 2,
            'exhausted_count': 0,
            'by_tool': {'chatgpt': [{'email': 'a@test.com'}, {'email': 'b@test.com'}]},
            'total_remaining_messages': 15,
            'tools_available': ['chatgpt'],
        }

    def test_no_approval_uses_auto_ranked(self):
        """Without ledger approval, top_worker is from ranking."""
        pool = self._pool_with_workers()
        router = self._make_router(pool, ledger=None)
        gate = router.worker_health_gate(target_assistant='chatgpt')
        assert gate['usable'] is True
        assert gate.get('account_selection_source', 'auto_ranked') == 'auto_ranked'
        assert gate.get('fallback_used', False) is False

    def test_approval_overrides_top_worker(self):
        """User-approved account becomes top_worker."""
        pool = self._pool_with_workers()
        ledger = _FakeLedger()
        ledger.approve('chatgpt', 'b@test.com')  # b has lower ranking
        router = self._make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['top_worker']['email'] == 'b@test.com'
        assert gate['account_selection_source'] == 'user_approved'
        assert gate['fallback_used'] is False
        assert gate['approved_account']['email'] == 'b@test.com'

    def test_approval_fallback_when_exhausted(self):
        """If approved account is exhausted, fallback to auto-ranked."""
        pool = self._pool_with_workers()
        # Make b exhausted
        pool['workers'][1]['exhausted'] = True
        pool['workers'][1]['remaining_messages'] = 0
        ledger = _FakeLedger()
        ledger.approve('chatgpt', 'b@test.com')
        router = self._make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        # Falls back to top-ranked (a@test.com)
        assert gate['top_worker']['email'] == 'a@test.com'
        assert gate['account_selection_source'] == 'user_approved_fallback'
        assert gate['fallback_used'] is True

    def test_approval_tool_a_does_not_affect_tool_b(self):
        """Approving chatgpt doesn't change claude results."""
        pool = self._pool_with_workers()
        # Add a claude worker
        pool['workers'].append({
            'email': 'c@test.com', 'tool': 'claude', 'browser': 'chrome',
            'profile': 'Default', 'remaining_messages': 20, 'used_in_window': 0,
            'limit': 20, 'exhausted': False, 'label': 'Claude Free',
        })
        pool['available_count'] = 3
        pool['by_tool']['claude'] = [{'email': 'c@test.com'}]
        pool['tools_available'].append('claude')

        ledger = _FakeLedger()
        ledger.approve('chatgpt', 'b@test.com')
        router = self._make_router(pool, ledger=ledger)

        # chatgpt uses approved
        gate_chatgpt = router.worker_health_gate(target_assistant='chatgpt')
        assert gate_chatgpt['top_worker']['email'] == 'b@test.com'
        assert gate_chatgpt['account_selection_source'] == 'user_approved'

        # claude is unaffected (no approval for claude)
        gate_claude = router.worker_health_gate(target_assistant='claude')
        assert gate_claude['top_worker']['email'] == 'c@test.com'
        assert gate_claude.get('account_selection_source', 'auto_ranked') == 'auto_ranked'

    def test_approval_for_missing_account_falls_back(self):
        """Approved account not in pool → fallback."""
        pool = self._pool_with_workers()
        ledger = _FakeLedger()
        ledger.approve('chatgpt', 'nonexistent@test.com')
        router = self._make_router(pool, ledger=ledger)
        gate = router.worker_health_gate(target_assistant='chatgpt')

        assert gate['usable'] is True
        assert gate['top_worker']['email'] == 'a@test.com'
        assert gate['fallback_used'] is True


# ──────────────────────────────────────────────────────────────
# 8. AccountApproval domain model
# ──────────────────────────────────────────────────────────────

class TestAccountApproval:
    def test_defaults(self):
        from iabv_v15.domain.models import AccountApproval
        a = AccountApproval(tool='chatgpt', email='test@test.com')
        assert a.tool == 'chatgpt'
        assert a.email == 'test@test.com'
        assert a.origin == 'ui'
        assert a.valid is True
        assert a.reason == ''
        assert a.browser == ''

    def test_roundtrip(self):
        from iabv_v15.domain.models import AccountApproval
        a = AccountApproval(
            tool='claude', email='x@y.com',
            origin='centro_vivo_ui', reason='manual_switch',
        )
        data = a.model_dump(mode='json')
        restored = AccountApproval.model_validate(data)
        assert restored.tool == 'claude'
        assert restored.email == 'x@y.com'
        assert restored.origin == 'centro_vivo_ui'
