"""Tests for dashboard summary freeze fix.

Verifies:
1. _collect_summary_cards uses count() not list_recent()
2. refresh() is non-blocking (bg thread via ThreadPoolExecutor)
3. Results come back via signal/slot (refreshResolved)
4. Timeline metadata includes duration_ms and counts
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch, call

from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel


def _make_dashboard_vm(*, defer: bool = True) -> DashboardViewModel:
    """Build a DashboardViewModel with mocked repositories."""
    episode_repo = MagicMock()
    episode_repo.count.return_value = 42
    episode_repo.list_recent.return_value = []

    knowledge_repo = MagicMock()
    knowledge_repo.count.return_value = 100
    knowledge_repo.list_recent.return_value = []

    run_repo = MagicMock()
    run_repo.count.return_value = 77
    run_repo.list_recent.return_value = []

    role_router = MagicMock()
    embedding_service = MagicMock()
    embedding_service.describe_index.return_value = {'knowledge_count': 95}

    vm = DashboardViewModel(
        episode_repository=episode_repo,
        knowledge_repository=knowledge_repo,
        run_repository=run_repo,
        role_router=role_router,
        embedding_service=embedding_service,
        defer_initial_refresh=defer,
    )
    return vm


# ── count() vs list_recent() ──


def test_collect_summary_cards_uses_count_not_list_recent() -> None:
    vm = _make_dashboard_vm()
    cards = vm._collect_summary_cards()

    vm.episode_repository.count.assert_called_once()
    vm.knowledge_repository.count.assert_called_once()
    vm.run_repository.count.assert_called_once()

    vm.episode_repository.list_recent.assert_not_called()
    vm.knowledge_repository.list_recent.assert_not_called()
    vm.run_repository.list_recent.assert_not_called()


def test_summary_cards_show_correct_counts() -> None:
    vm = _make_dashboard_vm()
    cards = vm._collect_summary_cards()

    assert len(cards) == 4
    assert cards[0]['value'] == '42'
    assert cards[0]['title'] == 'Episodios'
    assert cards[1]['value'] == '100'
    assert cards[1]['title'] == 'Conocimiento'
    assert cards[2]['value'] == '77'
    assert cards[2]['title'] == 'Ejecuciones'
    assert cards[3]['value'] == '95'
    assert cards[3]['title'] == 'Indexado'


def test_last_refresh_counts_populated() -> None:
    vm = _make_dashboard_vm()
    vm._collect_summary_cards()

    assert vm._last_refresh_counts == {
        'episodes': 42,
        'knowledge': 100,
        'runs': 77,
    }


# ── refresh is non-blocking ──


def test_refresh_submits_to_bg_pool() -> None:
    vm = _make_dashboard_vm()
    vm._bg_pool = MagicMock()
    vm.refresh()
    vm._bg_pool.submit.assert_called_once_with(vm._refresh_data_bg)


def test_refresh_data_bg_emits_resolved_signal() -> None:
    vm = _make_dashboard_vm()
    resolved_cards: list[list[dict]] = []
    vm.refreshResolved.connect(lambda cards: resolved_cards.append(cards))

    vm._refresh_data_bg()

    assert len(resolved_cards) == 1
    assert len(resolved_cards[0]) == 4
    assert resolved_cards[0][0]['value'] == '42'


def test_refresh_data_bg_emits_failed_on_error() -> None:
    vm = _make_dashboard_vm()
    vm.episode_repository.count.side_effect = RuntimeError('DB locked')
    errors: list[str] = []
    vm.refreshFailed.connect(lambda msg: errors.append(msg))

    vm._refresh_data_bg()

    assert len(errors) == 1
    assert 'DB locked' in errors[0]


# ── signal/slot: results arrive on main thread ──


def test_apply_refresh_updates_summary_cards() -> None:
    vm = _make_dashboard_vm()
    assert vm._summary_cards == []

    test_cards = [{'title': 'Test', 'value': '1', 'hint': 'h'}]
    vm._apply_refresh(test_cards)

    assert vm._summary_cards == test_cards


def test_refresh_bg_triggers_apply_refresh_via_signal() -> None:
    vm = _make_dashboard_vm()
    assert vm._summary_cards == []

    vm._refresh_data_bg()

    assert len(vm._summary_cards) == 4
    assert vm._summary_cards[0]['value'] == '42'


# ── timeline metadata ──


def test_timeline_metadata_includes_duration_and_counts() -> None:
    vm = _make_dashboard_vm()
    marks: list[tuple] = []
    original_mark = vm._mark_timeline

    def _capture_mark(phase, **extra):
        marks.append((phase, extra))

    vm._mark_timeline = _capture_mark

    vm._refresh_data_bg()

    phases = [m[0] for m in marks]
    assert 'dashboard_vm_refresh_start' in phases
    assert 'dashboard_vm_refresh_done' in phases

    done_mark = next(m for m in marks if m[0] == 'dashboard_vm_refresh_done')
    meta = done_mark[1]
    assert 'duration_ms' in meta
    assert meta['duration_ms'] >= 0
    assert meta['episodes_count'] == 42
    assert meta['knowledge_count'] == 100
    assert meta['runs_count'] == 77


def test_timeline_metadata_on_failure() -> None:
    vm = _make_dashboard_vm()
    vm.episode_repository.count.side_effect = RuntimeError('fail')
    marks: list[tuple] = []

    def _capture_mark(phase, **extra):
        marks.append((phase, extra))

    vm._mark_timeline = _capture_mark
    vm._refresh_data_bg()

    phases = [m[0] for m in marks]
    assert 'dashboard_vm_refresh_failed' in phases

    fail_mark = next(m for m in marks if m[0] == 'dashboard_vm_refresh_failed')
    meta = fail_mark[1]
    assert 'duration_ms' in meta
    assert 'error' in meta


# ── deferred initial refresh uses bg ──


def test_deferred_initial_refresh_uses_bg_pool() -> None:
    vm = _make_dashboard_vm(defer=True)
    vm._bg_pool = MagicMock()
    vm._deferred_initial_refresh()
    vm._bg_pool.submit.assert_called_once_with(vm._refresh_data_bg)
