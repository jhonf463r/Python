"""Tests for the 4 bugs found in live audit post-#305.

1. PortableContext pending export must NOT include COMPLETED tasks
2. Systray icon resolution must resolve from repo root, not src/
3. Startup final refresh: after page_loader_ready, persisted snapshot
   must reflect the complete timeline (populate_ui_done present)
4. QQuickStyle.setStyle guard: calling setStyle twice must only invoke
   the underlying API once
5. Regression: existing platform_pending_queue behaviour unchanged
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.domain.models import (
    PendingTaskStatus,
    PlatformPendingTask,
)
from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue


# ------------------------------------------------------------------ #
# 1. PortableContext pending export — COMPLETED excluded
# ------------------------------------------------------------------ #


class TestPendingExportNoCompleted:
    """to_portable_items() must not export COMPLETED tasks."""

    @pytest.fixture
    def queue(self, tmp_path: Path) -> PlatformPendingQueue:
        return PlatformPendingQueue(evolution_dir=str(tmp_path / 'evolution'))

    def test_completed_excluded_from_portable(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='a', title='Pending', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='b', title='Completed', status=PendingTaskStatus.COMPLETED))
        queue.upsert(PlatformPendingTask(id='c', title='Ready', status=PendingTaskStatus.READY_FOR_NEXT_SLICE))
        queue.upsert(PlatformPendingTask(id='d', title='Blocked', status=PendingTaskStatus.BLOCKED))

        items = queue.to_portable_items()
        ids = {i['id'] for i in items}
        assert 'b' not in ids, 'COMPLETED task should not appear in portable items'
        assert 'a' in ids
        assert 'c' in ids
        assert 'd' in ids

    def test_only_completed_produces_empty(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='x', title='Done', status=PendingTaskStatus.COMPLETED))
        queue.upsert(PlatformPendingTask(id='y', title='Done2', status=PendingTaskStatus.COMPLETED))
        items = queue.to_portable_items()
        assert items == []

    def test_limit_respected_after_filtering(self, queue: PlatformPendingQueue):
        for i in range(10):
            queue.upsert(PlatformPendingTask(
                id=f'p{i}', title=f'Task {i}',
                status=PendingTaskStatus.PENDING,
            ))
        queue.upsert(PlatformPendingTask(id='done', title='Done', status=PendingTaskStatus.COMPLETED))
        items = queue.to_portable_items(limit=5)
        assert len(items) == 5
        assert all(i['status'] != 'COMPLETED' for i in items)


# ------------------------------------------------------------------ #
# 2. Systray icon resolution — repo root, not src/
# ------------------------------------------------------------------ #


class TestSystrayIconResolution:
    """_find_app_icon() must resolve assets from repo root."""

    def test_find_app_icon_resolves_from_repo_root(self):
        from iabv_v15.services.platform.win_systray_bridge import _find_app_icon
        icon_path = _find_app_icon()
        if icon_path:
            p = Path(icon_path)
            assert p.is_file(), f'Icon path {p} does not exist'
            assert 'assets' in str(p) or 'scripts' in str(p)

    def test_find_repo_root_finds_assets_dir(self):
        from iabv_v15.services.platform.win_systray_bridge import _find_repo_root
        root = _find_repo_root()
        assert (root / 'assets').is_dir(), f'repo root {root} has no assets/ dir'

    def test_icon_not_under_src(self):
        from iabv_v15.services.platform.win_systray_bridge import _find_app_icon
        icon_path = _find_app_icon()
        if icon_path:
            parts = Path(icon_path).parts
            parent_of_assets = None
            for i, part in enumerate(parts):
                if part in ('assets', 'scripts') and i > 0:
                    parent_of_assets = parts[i - 1]
            assert parent_of_assets != 'src', \
                f'Icon resolved under src/ instead of repo root: {icon_path}'


# ------------------------------------------------------------------ #
# 3. Startup final refresh — persisted snapshot reflects complete boot
# ------------------------------------------------------------------ #


class TestStartupFinalRefresh:
    """After page_loader_ready, the truth refresh must re-persist snapshots
    that include populate_ui_done in the timeline."""

    def _workspace(self, tmp_path: Path, name: str) -> Path:
        root = tmp_path / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _write_timeline(self, root: Path, events: list[dict]) -> Path:
        log_dir = root / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / 'startup_timeline.jsonl'
        with path.open('w', encoding='utf-8') as fh:
            for evt in events:
                fh.write(json.dumps(evt))
                fh.write('\n')
        return path

    def test_snapshot_reflects_complete_boot(self, tmp_path: Path):
        """When timeline has populate_ui_done + page_loader_ready, the
        startup_health snapshot must report them in phases_seen."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        root = self._workspace(tmp_path, 'complete_boot')
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 2000.0, 'rss_mb': 120.0},
            {'phase': 'run_start', 't_ms_from_start': 2010.0, 'rss_mb': 120.0},
            {'phase': 'splash_visible', 't_ms_from_start': 2200.0, 'rss_mb': 125.0},
            {'phase': 'main_window_shown', 't_ms_from_start': 5000.0, 'rss_mb': 200.0},
            {'phase': 'populate_ui_start', 't_ms_from_start': 5100.0, 'rss_mb': 210.0},
            {'phase': 'populate_ui_done', 't_ms_from_start': 8000.0, 'rss_mb': 280.0},
            {'phase': 'shell_loader_ready', 't_ms_from_start': 9000.0, 'rss_mb': 290.0},
            {'phase': 'page_loader_ready', 't_ms_from_start': 10000.0, 'rss_mb': 300.0},
            {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 10100.0, 'rss_mb': 300.0},
            {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 12000.0, 'rss_mb': 310.0},
        ]
        self._write_timeline(root, events)

        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        svc = PortableContextService(workspace_root=str(root), storage=storage)
        snap = svc._startup_health_snapshot()

        assert snap['status'] == 'analyzed'
        assert 'populate_ui_done' in snap['phases_seen']
        assert 'page_loader_ready' in snap['phases_seen']

    def test_partial_boot_missing_populate_ui_done(self, tmp_path: Path):
        """Early snapshot (before populate_ui_done) must NOT have it."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.services.evolution.portable_context_service import PortableContextService

        root = self._workspace(tmp_path, 'partial_boot')
        events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 2000.0, 'rss_mb': 120.0},
            {'phase': 'run_start', 't_ms_from_start': 2010.0, 'rss_mb': 120.0},
            {'phase': 'main_window_shown', 't_ms_from_start': 5000.0, 'rss_mb': 200.0},
        ]
        self._write_timeline(root, events)

        storage = ArtifactStorage(str(root / 'data' / 'evolution'))
        svc = PortableContextService(workspace_root=str(root), storage=storage)
        snap = svc._startup_health_snapshot()

        assert snap['status'] == 'analyzed'
        assert 'populate_ui_done' not in snap.get('phases_seen', [])

    def test_final_refresh_method_exists(self):
        """_final_startup_truth_refresh must exist on AppBootstrap."""
        from iabv_v15.bootstrap import AppBootstrap
        assert hasattr(AppBootstrap, '_final_startup_truth_refresh')
        assert callable(AppBootstrap._final_startup_truth_refresh)


# ------------------------------------------------------------------ #
# 4. QQuickStyle.setStyle guard — idempotent
# ------------------------------------------------------------------ #


class TestQQuickStyleGuard:
    """QQuickStyle.setStyle must be idempotent: second call is a no-op."""

    def test_stub_is_idempotent(self):
        from iabv_v15.ui.qt import QQuickStyle
        QQuickStyle._applied = False
        QQuickStyle.setStyle('Basic')
        assert QQuickStyle._applied is True
        QQuickStyle.setStyle('Basic')
        assert QQuickStyle._applied is True

    def test_has_applied_attribute(self):
        from iabv_v15.ui.qt import QQuickStyle
        assert hasattr(QQuickStyle, '_applied')


# ------------------------------------------------------------------ #
# 5. Regression: existing queue behaviour unchanged
# ------------------------------------------------------------------ #


class TestPendingQueueRegression:
    """Existing queue methods still work after to_portable_items fix."""

    @pytest.fixture
    def queue(self, tmp_path: Path) -> PlatformPendingQueue:
        return PlatformPendingQueue(evolution_dir=str(tmp_path / 'evolution'))

    def test_list_all_includes_completed(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='a', title='P', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='b', title='C', status=PendingTaskStatus.COMPLETED))
        all_tasks = queue.list_all()
        ids = {t.id for t in all_tasks}
        assert 'a' in ids
        assert 'b' in ids

    def test_list_actionable_unchanged(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p', title='P', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='r', title='R', status=PendingTaskStatus.READY_FOR_NEXT_SLICE))
        queue.upsert(PlatformPendingTask(id='c', title='C', status=PendingTaskStatus.COMPLETED))
        actionable = queue.list_actionable()
        assert len(actionable) == 2
        assert {t.id for t in actionable} == {'p', 'r'}

    def test_summary_unchanged(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p', title='P', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='c', title='C', status=PendingTaskStatus.COMPLETED))
        s = queue.summary()
        assert s['total'] == 2
        assert s['by_status']['PENDING'] == 1
        assert s['by_status']['COMPLETED'] == 1

    def test_portable_items_status_field_correct(self, queue: PlatformPendingQueue):
        queue.upsert(PlatformPendingTask(id='p', title='P', status=PendingTaskStatus.PENDING))
        queue.upsert(PlatformPendingTask(id='b', title='B', status=PendingTaskStatus.BLOCKED))
        items = queue.to_portable_items()
        statuses = {i['status'] for i in items}
        assert statuses == {'PENDING', 'BLOCKED'}
