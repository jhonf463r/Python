"""Tests para SystemBacklogService."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.services.evolution.system_backlog_service import (
    BacklogItem,
    SystemBacklogService,
)


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def backlog(tmp_workspace: Path) -> SystemBacklogService:
    return SystemBacklogService(tmp_workspace)


class TestBacklogItem:
    def test_create_default(self):
        item = BacklogItem('Install aider_coder')
        assert item.title == 'Install aider_coder'
        assert item.status == 'pending'
        assert item.category == 'infrastructure'
        assert item.priority == 'medium'

    def test_roundtrip(self):
        item = BacklogItem('Fix CI', category='deployment', priority='high')
        d = item.to_dict()
        restored = BacklogItem.from_dict(d)
        assert restored.title == 'Fix CI'
        assert restored.category == 'deployment'
        assert restored.priority == 'high'
        assert restored.item_id == item.item_id


class TestSystemBacklogService:
    def test_add_and_get(self, backlog: SystemBacklogService):
        item = backlog.add_item('Fix flaky test', category='error_recovery')
        pending = backlog.get_pending()
        assert len(pending) == 1
        assert pending[0].title == 'Fix flaky test'

    def test_deduplication(self, backlog: SystemBacklogService):
        backlog.add_item('Fix flaky test')
        backlog.add_item('Fix flaky test')
        pending = backlog.get_pending()
        assert len(pending) == 1

    def test_mark_completed(self, backlog: SystemBacklogService):
        item = backlog.add_item('Install aider')
        assert backlog.mark_completed(item.item_id)
        pending = backlog.get_pending()
        assert len(pending) == 0

    def test_mark_blocked(self, backlog: SystemBacklogService):
        item = backlog.add_item('Deploy X')
        assert backlog.mark_blocked(item.item_id, 'needs VPN')
        pending = backlog.get_pending()
        assert len(pending) == 0

    def test_filter_by_category(self, backlog: SystemBacklogService):
        backlog.add_item('A', category='infrastructure')
        backlog.add_item('B', category='ui')
        backlog.add_item('C', category='learning')

        infra = backlog.get_pending(category='infrastructure')
        assert len(infra) == 1
        assert infra[0].title == 'A'

    def test_filter_auto_executable(self, backlog: SystemBacklogService):
        backlog.add_item('Manual task', auto_executable=False)
        backlog.add_item('Auto task', auto_executable=True)

        auto = backlog.get_pending(auto_executable_only=True)
        assert len(auto) == 1
        assert auto[0].title == 'Auto task'

    def test_priority_ordering(self, backlog: SystemBacklogService):
        backlog.add_item('Low', priority='low')
        backlog.add_item('Critical', priority='critical')
        backlog.add_item('High', priority='high')

        pending = backlog.get_pending()
        assert pending[0].title == 'Critical'
        assert pending[1].title == 'High'
        assert pending[2].title == 'Low'

    def test_ingest_from_findings(self, backlog: SystemBacklogService):
        findings = [
            {
                'finding_id': 'f1',
                'title': 'chatgpt falla en OCR',
                'category': 'recurring_failure',
                'severity': 'high',
                'recommendation': 'Cambiar a claude para OCR',
            },
            {
                'finding_id': 'f2',
                'title': 'Token proximo a expirar',
                'category': 'token_rotation',
                'severity': 'medium',
                'recommendation': 'Ejecutar rotate_tokens.ps1',
            },
        ]
        added = backlog.ingest_from_findings(findings)
        assert added == 2
        pending = backlog.get_pending()
        assert len(pending) == 2

    def test_summary(self, backlog: SystemBacklogService):
        backlog.add_item('A', category='infrastructure', priority='high')
        backlog.add_item('B', category='ui', priority='low')
        backlog.add_item('C', category='audit', auto_executable=True)

        s = backlog.summary()
        assert s['total_items'] == 3
        assert s['auto_executable_count'] == 1
        assert 'infrastructure' in s['pending_by_category']

    def test_persistence(self, tmp_workspace: Path):
        b1 = SystemBacklogService(tmp_workspace)
        b1.add_item('Persist me', category='audit')

        b2 = SystemBacklogService(tmp_workspace)
        pending = b2.get_pending()
        assert len(pending) == 1
        assert pending[0].title == 'Persist me'

    def test_dismiss(self, backlog: SystemBacklogService):
        item = backlog.add_item('Not needed')
        assert backlog.dismiss(item.item_id, 'irrelevant')
        pending = backlog.get_pending()
        assert len(pending) == 0

    def test_mark_auto_executed(self, backlog: SystemBacklogService):
        item = backlog.add_item('Auto install', auto_executable=True)
        assert backlog.mark_auto_executed(item.item_id)
        pending = backlog.get_pending()
        assert len(pending) == 0
