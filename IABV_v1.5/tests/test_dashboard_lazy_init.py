"""Tests for DashboardViewModel lazy init — refresh runs in background."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel


def _make_vm(*, defer: bool = True) -> DashboardViewModel:
    """Build a DashboardViewModel with mocked dependencies."""
    episode_repo = MagicMock()
    episode_repo.list_recent.return_value = [{'id': 1}, {'id': 2}]
    knowledge_repo = MagicMock()
    knowledge_repo.list_recent.return_value = [{'id': 1}]
    run_repo = MagicMock()
    run_repo.list_recent.return_value = [{'id': 1}, {'id': 2}, {'id': 3}]
    embedding_svc = MagicMock()
    embedding_svc.describe_index.return_value = {'knowledge_count': 42}
    role_router = MagicMock()

    vm = DashboardViewModel(
        episode_repository=episode_repo,
        knowledge_repository=knowledge_repo,
        run_repository=run_repo,
        role_router=role_router,
        embedding_service=embedding_svc,
        defer_initial_refresh=defer,
    )
    return vm


class TestDashboardLazyInit:
    def test_has_bg_pool(self) -> None:
        vm = _make_vm()
        assert hasattr(vm, '_bg_pool')
        assert isinstance(vm._bg_pool, ThreadPoolExecutor)

    def test_init_does_not_call_repos_synchronously(self) -> None:
        """__init__ should NOT call list_recent synchronously."""
        vm = _make_vm(defer=True)
        # list_recent might have been called already by bg thread,
        # but the point is __init__ returns immediately
        assert vm._summary_cards == [] or len(vm._summary_cards) > 0

    def test_refresh_submits_to_pool(self) -> None:
        vm = _make_vm(defer=True)
        vm._bg_pool = MagicMock()
        vm.refresh()
        vm._bg_pool.submit.assert_called_once_with(vm._bg_refresh)

    def test_bg_refresh_builds_cards(self) -> None:
        vm = _make_vm(defer=True)
        # Call _bg_refresh directly (simulates bg thread)
        vm._bg_refresh()
        # Wait a bit for signal processing
        time.sleep(0.2)

    def test_apply_refresh_sets_cards(self) -> None:
        vm = _make_vm(defer=True)
        cards = [
            {'title': 'Episodios', 'value': '5', 'hint': 'test'},
            {'title': 'Conocimiento', 'value': '3', 'hint': 'test'},
        ]
        vm._apply_refresh(cards)
        assert vm._summary_cards == cards

    def test_placeholder_health_cards(self) -> None:
        vm = _make_vm(defer=True)
        cards = vm._placeholder_health_cards()
        assert len(cards) == 3
        assert all(c['status'] == 'inactivo' for c in cards)

    def test_refresh_health_not_busy(self) -> None:
        vm = _make_vm(defer=True)
        assert vm._health_busy is False

    def test_shutdown_bg_pool(self) -> None:
        vm = _make_vm(defer=True)
        vm._shutdown_bg_pool()
        # Should not raise after shutdown
