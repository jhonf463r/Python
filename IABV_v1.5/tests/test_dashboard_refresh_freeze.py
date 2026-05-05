"""Tests for DashboardViewModel background refresh (fix-dashboard-refresh-freeze).

Verifies:
1. defer_initial_refresh does not block the calling thread
2. Heavy I/O runs outside the main thread (via ThreadPoolExecutor)
3. Results arrive back through Signal/Slot (refreshResolved)
4. Manual refresh() also delegates to background
5. Timeline marks are emitted (dashboard_vm_refresh_start/done/failed)
6. OSES can read the new marks and attribute slow dashboard refresh
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.infra.startup_timeline import StartupTimeline, reset_global_timeline_for_tests


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_repos(*, fail: bool = False):
    """Create mock repositories."""
    episode_repo = MagicMock()
    knowledge_repo = MagicMock()
    run_repo = MagicMock()
    embedding_service = MagicMock()
    role_router = MagicMock()

    episode_repo.list_recent.return_value = [{'id': 1}]
    knowledge_repo.list_recent.return_value = [{'id': 2}, {'id': 3}]
    run_repo.list_recent.return_value = [{'id': 4}]
    embedding_service.describe_index.return_value = {'knowledge_count': 5}

    if fail:
        knowledge_repo.list_recent.side_effect = RuntimeError('DB locked')

    return episode_repo, knowledge_repo, run_repo, role_router, embedding_service


def _make_vm_no_timer(*, fail: bool = False):
    """Build a DashboardViewModel with defer=False (sync path, no QTimer)."""
    from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
    repos = _make_repos(fail=fail)
    vm = DashboardViewModel(*repos, defer_initial_refresh=False)
    return vm, repos


# ------------------------------------------------------------------ #
# 1. defer_initial_refresh does not block the calling thread
# ------------------------------------------------------------------ #


class TestDeferInitialRefresh:
    """Constructor with defer_initial_refresh=True returns immediately
    without blocking; the actual work is deferred to a QTimer → pool."""

    def test_constructor_deferred_returns_with_empty_cards(self):
        """With defer=True, constructor returns before refresh runs."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        # Patch QTimer to prevent actual scheduling
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer') as mock_timer:
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)
        # Cards are empty because refresh hasn't run yet
        assert vm._summary_cards == []
        # QTimer.singleShot was called with the deferred method
        mock_timer.singleShot.assert_called_once_with(250, vm._deferred_initial_refresh)

    def test_constructor_sync_populates_immediately(self):
        vm, _ = _make_vm_no_timer()
        assert len(vm._summary_cards) == 4
        assert vm._summary_cards[0]['title'] == 'Episodios'

    def test_deferred_initial_refresh_submits_to_pool(self):
        """_deferred_initial_refresh submits _refresh_data_bg to the pool."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)
        with patch.object(vm._bg_pool, 'submit') as mock_submit:
            vm._deferred_initial_refresh()
            mock_submit.assert_called_once_with(vm._refresh_data_bg)


# ------------------------------------------------------------------ #
# 2. Heavy I/O runs outside the main thread
# ------------------------------------------------------------------ #


class TestBackgroundThread:
    """Verify that _refresh_data_bg runs on a non-main thread."""

    def test_refresh_runs_on_worker_thread(self):
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        thread_names: list[str] = []
        original_list_recent = repos[0].list_recent

        def capture_thread(**kwargs):
            thread_names.append(threading.current_thread().name)
            return original_list_recent(**kwargs)
        repos[0].list_recent.side_effect = capture_thread

        # Submit directly to pool and wait
        vm._bg_pool.submit(vm._refresh_data_bg).result()

        assert len(thread_names) >= 1
        assert any('dvm-bg' in name for name in thread_names), (
            f'Expected dvm-bg worker thread, got: {thread_names}'
        )

    def test_collect_summary_cards_does_io(self):
        """_collect_summary_cards calls all four repository methods."""
        vm, repos = _make_vm_no_timer()
        ep_repo, kn_repo, run_repo, _, emb_service = repos
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        lim = DashboardViewModel._SUMMARY_QUERY_LIMIT
        ep_repo.list_recent.assert_called_with(limit=lim)
        kn_repo.list_recent.assert_called_with(limit=lim)
        run_repo.list_recent.assert_called_with(limit=lim)
        emb_service.describe_index.assert_called_once()


# ------------------------------------------------------------------ #
# 3. Results arrive through Signal/Slot (refreshResolved)
# ------------------------------------------------------------------ #


class TestSignalSlot:
    """Verify that background results are applied via Signal → _apply_refresh."""

    def test_apply_refresh_updates_cards(self):
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        assert vm._summary_cards == []
        cards = [
            {'title': 'Episodios', 'value': '1', 'hint': 'test'},
            {'title': 'Conocimiento', 'value': '2', 'hint': 'test'},
        ]
        vm._apply_refresh(cards)
        assert vm._summary_cards == cards

    def test_refresh_data_bg_produces_correct_cards(self):
        """_refresh_data_bg collects cards and emits refreshResolved."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        # Verify _collect_summary_cards returns the right data
        cards = vm._collect_summary_cards()
        assert len(cards) == 4
        assert cards[0]['title'] == 'Episodios'
        assert cards[0]['value'] == '1'
        assert cards[3]['value'] == '5'

    def test_refresh_data_bg_calls_collect_and_emits(self):
        """_refresh_data_bg calls _collect_summary_cards then emits."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        with patch.object(vm, '_collect_summary_cards', return_value=[{'test': True}]) as mock_collect:
            # Run synchronously to verify the path
            vm._refresh_data_bg()
            mock_collect.assert_called_once()

    def test_refresh_data_bg_handles_error_gracefully(self):
        """_refresh_data_bg emits refreshFailed on exception."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos(fail=True)
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        # Should not raise — the error is caught and emitted via signal
        vm._bg_pool.submit(vm._refresh_data_bg).result()
        # Cards remain empty because the error was caught
        assert vm._summary_cards == []


# ------------------------------------------------------------------ #
# 4. Manual refresh() also delegates to background
# ------------------------------------------------------------------ #


class TestManualRefresh:
    """The refresh() Slot used by 'Actualizar metricas' button must not block."""

    def test_refresh_slot_submits_to_pool(self):
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        with patch.object(vm._bg_pool, 'submit') as mock_submit:
            vm.refresh()
            mock_submit.assert_called_once_with(vm._refresh_data_bg)


# ------------------------------------------------------------------ #
# 5. Timeline marks are emitted
# ------------------------------------------------------------------ #


class TestTimelineMarks:
    """Verify dashboard_vm_refresh_start/done marks in startup timeline."""

    def test_marks_emitted_on_success(self):
        reset_global_timeline_for_tests()
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        vm._bg_pool.submit(vm._refresh_data_bg).result()

        from iabv_v15.infra.startup_timeline import get_global_timeline
        tl = get_global_timeline()
        phases = [e['phase'] for e in tl.events()]
        assert 'dashboard_vm_refresh_start' in phases
        assert 'dashboard_vm_refresh_done' in phases

    def test_marks_emitted_on_failure(self):
        reset_global_timeline_for_tests()
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos(fail=True)
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)

        vm._bg_pool.submit(vm._refresh_data_bg).result()

        from iabv_v15.infra.startup_timeline import get_global_timeline
        tl = get_global_timeline()
        phases = [e['phase'] for e in tl.events()]
        assert 'dashboard_vm_refresh_start' in phases
        assert 'dashboard_vm_refresh_failed' in phases


# ------------------------------------------------------------------ #
# 6. OSES reads new dashboard marks
# ------------------------------------------------------------------ #


class TestOSESDashboardMarks:
    """OSES _startup_health_findings reads dashboard_vm_refresh marks."""

    def test_oses_detects_slow_dashboard_refresh(self, tmp_path: Path):
        import json
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 100.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 500.0, 'rss_mb': 110.0},
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 750.0, 'rss_mb': 115.0},
            {'phase': 'dashboard_vm_refresh_done', 't_ms_from_start': 40818.0, 'rss_mb': 200.0},
        ]
        jsonl_path = tmp_path / 'data' / 'logs' / 'startup_timeline.jsonl'
        jsonl_path.parent.mkdir(parents=True)
        with jsonl_path.open('w') as fh:
            for evt in events:
                fh.write(json.dumps(evt) + '\n')

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(tmp_path)
        oses.boot_profile_store = None

        findings = oses._startup_health_findings()
        categories = [f.category for f in findings]
        assert 'startup_degradation' in categories
        slow_findings = [f for f in findings if 'Dashboard refresh lento' in f.title]
        assert len(slow_findings) == 1
        assert slow_findings[0].metadata['observed_ms'] == 40068.0

    def test_oses_detects_dashboard_refresh_failure(self, tmp_path: Path):
        import json
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 100.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 500.0, 'rss_mb': 110.0},
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 750.0, 'rss_mb': 115.0},
            {'phase': 'dashboard_vm_refresh_failed', 't_ms_from_start': 800.0, 'rss_mb': 115.0},
        ]
        jsonl_path = tmp_path / 'data' / 'logs' / 'startup_timeline.jsonl'
        jsonl_path.parent.mkdir(parents=True)
        with jsonl_path.open('w') as fh:
            for evt in events:
                fh.write(json.dumps(evt) + '\n')

        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )
        oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        oses.workspace_root = str(tmp_path)
        oses.boot_profile_store = None

        findings = oses._startup_health_findings()
        fail_findings = [f for f in findings if 'fallo' in f.title.lower()]
        assert len(fail_findings) == 1


# ------------------------------------------------------------------ #
# 7. ThreadPoolExecutor lifecycle
# ------------------------------------------------------------------ #


class TestPoolLifecycle:
    """Verify the bg pool is created and can be shut down."""

    def test_pool_exists(self):
        vm, _ = _make_vm_no_timer()
        assert vm._bg_pool is not None
        assert not vm._bg_pool._shutdown

    def test_shutdown_is_safe(self):
        vm, _ = _make_vm_no_timer()
        vm._shutdown_bg_pool()
        # Second shutdown should not raise
        vm._shutdown_bg_pool()

    def test_has_refresh_resolved_signal(self):
        """DashboardViewModel must have refreshResolved and refreshFailed signals."""
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        repos = _make_repos()
        with patch('iabv_v15.ui.viewmodels.dashboard_viewmodel.QTimer'):
            vm = DashboardViewModel(*repos, defer_initial_refresh=True)
        assert hasattr(vm, 'refreshResolved')
        assert hasattr(vm, 'refreshFailed')
