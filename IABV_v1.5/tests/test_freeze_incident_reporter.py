"""Tests for FreezeIncidentReporter and metacognition investigation phases."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure src is importable
# ---------------------------------------------------------------------------
_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from iabv_v15.services.evolution.freeze_incident_reporter import (
    FreezeIncidentReporter,
    _sqlite_lock_probe,
    _thread_snapshot,
)
from iabv_v15.services.evolution.platform_pending_queue import (
    CATEGORY_INVESTIGATION,
    PlatformPendingQueue,
)


# ======================================================================
# FreezeIncidentReporter
# ======================================================================


class TestFreezeIncidentReporter:
    """Core behavior of capture_incident, list_reports, get_report."""

    @pytest.fixture()
    def reporter(self, tmp_path: Path) -> FreezeIncidentReporter:
        return FreezeIncidentReporter(evolution_dir=str(tmp_path))

    def test_capture_creates_json_file(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_incident(trigger='test')
        assert path.exists()
        assert path.suffix == '.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['trigger'] == 'test'
        assert data['report_version'] == '1.0'

    def test_capture_includes_all_sections(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_incident(
            trigger='user',
            user_description='se congeló al abrir evolución',
        )
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['user_description'] == 'se congeló al abrir evolución'
        for key in ('resources', 'threads', 'sqlite', 'startup_timeline',
                    'monitor_history', 'environment', 'pending_queue',
                    'oses_findings', 'process'):
            assert key in data, f'missing section: {key}'

    def test_process_section_has_correct_pid(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_incident(trigger='test')
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['process']['pid'] == os.getpid()
        assert data['process']['platform'] == sys.platform

    def test_list_reports_returns_metadata(self, reporter: FreezeIncidentReporter) -> None:
        reporter.capture_incident(trigger='auto')
        reporter.capture_incident(trigger='user', user_description='freeze 2')
        reports = reporter.list_reports()
        assert len(reports) == 2
        triggers = {r['trigger'] for r in reports}
        assert triggers == {'auto', 'user'}

    def test_get_report_by_filename(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_incident(trigger='test')
        loaded = reporter.get_report(path.name)
        assert loaded is not None
        assert loaded['trigger'] == 'test'

    def test_get_report_nonexistent_returns_none(self, reporter: FreezeIncidentReporter) -> None:
        assert reporter.get_report('nonexistent.json') is None

    def test_extra_context_included(self, reporter: FreezeIncidentReporter) -> None:
        path = reporter.capture_incident(
            trigger='test',
            extra_context={'debug_hint': 'check thread pool'},
        )
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['extra']['debug_hint'] == 'check thread pool'

    def test_capture_with_mock_orchestrator(self, reporter: FreezeIncidentReporter) -> None:
        mock_orch = MagicMock()
        mock_orch.get_scheduling_report.return_value = {
            'resources': {
                'ram_total_mb': 16000,
                'ram_available_mb': 2000,
                'ram_used_pct': 87.5,
            },
        }
        path = reporter.capture_incident(
            trigger='auto',
            resource_orchestrator=mock_orch,
        )
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['resources']['ram_used_pct'] == 87.5

    def test_capture_with_mock_timeline(self, reporter: FreezeIncidentReporter) -> None:
        mock_tl = MagicMock()
        mock_tl.events.return_value = [
            {'phase': 'bootstrap_init', 't_ms_from_start': 100.0, 'rss_mb': 50.0},
            {'phase': 'services_ready', 't_ms_from_start': 500.0, 'rss_mb': 120.0},
        ]
        path = reporter.capture_incident(
            trigger='startup',
            startup_timeline=mock_tl,
        )
        data = json.loads(path.read_text(encoding='utf-8'))
        assert len(data['startup_timeline']) == 2
        assert data['startup_timeline'][0]['phase'] == 'bootstrap_init'

    def test_capture_with_mock_pending_queue(self, reporter: FreezeIncidentReporter) -> None:
        mock_queue = MagicMock()
        mock_queue.summary.return_value = {'total': 5, 'pending': 3}
        mock_task = MagicMock()
        mock_task.id = 'test_task'
        mock_task.title = 'Test'
        mock_task.priority = 'medium'
        mock_task.category = 'investigation'
        mock_queue.list_actionable.return_value = [mock_task]
        path = reporter.capture_incident(
            trigger='user',
            pending_queue=mock_queue,
        )
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['pending_queue']['summary']['total'] == 5

    def test_list_reports_limit(self, reporter: FreezeIncidentReporter) -> None:
        import time
        for i in range(5):
            reporter.capture_incident(trigger=f'test_{i}')
            time.sleep(0.01)
        reports = reporter.list_reports(limit=3)
        assert len(reports) == 3


# ======================================================================
# Helpers
# ======================================================================


class TestThreadSnapshot:
    def test_returns_list(self) -> None:
        threads = _thread_snapshot()
        assert isinstance(threads, list)
        assert len(threads) > 0
        assert 'name' in threads[0]
        assert 'alive' in threads[0]


class TestSqliteLockProbe:
    def test_no_db_returns_no_db(self) -> None:
        result = _sqlite_lock_probe(None)
        assert result['status'] == 'no_db'

    def test_nonexistent_path(self) -> None:
        result = _sqlite_lock_probe('/tmp/nonexistent_db_12345.sqlite')
        assert result['status'] == 'no_db'

    def test_valid_db(self, tmp_path: Path) -> None:
        import sqlite3
        db_file = tmp_path / 'test.sqlite'
        conn = sqlite3.connect(str(db_file))
        conn.execute('CREATE TABLE t (id INTEGER)')
        conn.close()
        result = _sqlite_lock_probe(str(db_file))
        assert result['status'] == 'ok'
        assert 'journal_mode' in result


# ======================================================================
# Metacognition investigation phases
# ======================================================================


class TestMetacognitionPhases:
    """Seed and inspect the 3 investigation phases."""

    @pytest.fixture()
    def queue(self, tmp_path: Path) -> PlatformPendingQueue:
        return PlatformPendingQueue(evolution_dir=str(tmp_path))

    def test_seed_creates_three_tasks(self, queue: PlatformPendingQueue) -> None:
        seeded = queue.seed_metacognition_investigation_phases()
        assert len(seeded) == 3

    def test_phase_ids_are_correct(self, queue: PlatformPendingQueue) -> None:
        queue.seed_metacognition_investigation_phases()
        expected_ids = {
            'inv_phase_a_antifreeze',
            'inv_phase_b_visual_metacognition',
            'inv_phase_c_guided_replay',
        }
        actual_ids = {t.id for t in queue.list_all() if t.id.startswith('inv_')}
        assert actual_ids == expected_ids

    def test_categories_are_investigation(self, queue: PlatformPendingQueue) -> None:
        queue.seed_metacognition_investigation_phases()
        for t in queue.list_all():
            if t.id.startswith('inv_'):
                assert t.category == CATEGORY_INVESTIGATION

    def test_seed_is_idempotent(self, queue: PlatformPendingQueue) -> None:
        queue.seed_metacognition_investigation_phases()
        queue.seed_metacognition_investigation_phases()
        inv_tasks = [t for t in queue.list_all() if t.id.startswith('inv_')]
        assert len(inv_tasks) == 3

    def test_completed_phase_not_overwritten(self, queue: PlatformPendingQueue) -> None:
        from iabv_v15.domain.models import PendingTaskStatus
        queue.seed_metacognition_investigation_phases()
        task = queue.get('inv_phase_a_antifreeze')
        assert task is not None
        task = task.model_copy(update={'status': PendingTaskStatus.COMPLETED})
        queue.upsert(task)
        queue.seed_metacognition_investigation_phases()
        reloaded = queue.get('inv_phase_a_antifreeze')
        assert reloaded is not None
        assert reloaded.status == PendingTaskStatus.COMPLETED

    def test_phase_b_depends_on_phase_a(self, queue: PlatformPendingQueue) -> None:
        queue.seed_metacognition_investigation_phases()
        phase_b = queue.get('inv_phase_b_visual_metacognition')
        assert phase_b is not None
        assert 'inv_phase_a_antifreeze' in phase_b.dependency_missing

    def test_phase_priorities(self, queue: PlatformPendingQueue) -> None:
        queue.seed_metacognition_investigation_phases()
        a = queue.get('inv_phase_a_antifreeze')
        b = queue.get('inv_phase_b_visual_metacognition')
        c = queue.get('inv_phase_c_guided_replay')
        assert a is not None and a.priority == 'high'
        assert b is not None and b.priority == 'medium'
        assert c is not None and c.priority == 'low'


# ======================================================================
# CATEGORY_INVESTIGATION constant
# ======================================================================


class TestCategoryInvestigation:
    def test_constant_value(self) -> None:
        assert CATEGORY_INVESTIGATION == 'investigation'

    def test_constant_is_string(self) -> None:
        assert isinstance(CATEGORY_INVESTIGATION, str)
