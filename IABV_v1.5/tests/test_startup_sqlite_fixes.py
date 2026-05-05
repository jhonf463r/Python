"""Tests for startup-freeze and SQLite lock-contention fixes.

Covers:
- database.py: WAL mode, busy_timeout, _exec_with_retry
- dashboard_viewmodel.py: sub-phase timeline markers
- bootstrap.py: _record_startup_sqlite_incident
- operational_self_examination_service.py: _sqlite_lock_contention_findings
- tool_registry.py: seed_defaults graceful error handling
- cpu_frequency regression (from PR #342)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from iabv_v15.infra.persistence.database import AppDatabase


_BASE = Path(__file__).resolve().parent.parent / 'data'


def _workspace(name: str) -> Path:
    p = _BASE / f'test_{name}_{uuid.uuid4().hex[:8]}'
    p.mkdir(parents=True, exist_ok=True)
    return p


# ------------------------------------------------------------------
# B. SQLite lock contention fixes
# ------------------------------------------------------------------


class TestDatabaseWALAndTimeout:
    """Verify WAL journal_mode and busy_timeout are applied."""

    def test_connect_enables_wal_mode(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv('IABV_SQLITE_WAL', '1')
        db = AppDatabase(str(tmp_path / 'test.sqlite'))
        with db.connect() as conn:
            mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
            assert mode == 'wal', f'Expected WAL, got {mode}'

    def test_connect_sets_busy_timeout(self, tmp_path: Path) -> None:
        db = AppDatabase(str(tmp_path / 'test.sqlite'))
        with db.connect() as conn:
            timeout = conn.execute('PRAGMA busy_timeout').fetchone()[0]
            assert timeout >= 5000, f'Expected >= 5000, got {timeout}'

    def test_exec_with_retry_succeeds_on_transient_lock(self, tmp_path: Path) -> None:
        db = AppDatabase(str(tmp_path / 'test.sqlite'))
        db.execute(
            "CREATE TABLE IF NOT EXISTS test_retry (id TEXT PRIMARY KEY, val TEXT)"
        )

        call_count = 0
        original_connect = db.connect

        def flaky_connect():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise sqlite3.OperationalError('database is locked')
            return original_connect()

        with patch.object(db, 'connect', side_effect=flaky_connect):
            db.execute("INSERT OR REPLACE INTO test_retry VALUES ('a', 'b')")

        row = db.fetchone("SELECT val FROM test_retry WHERE id='a'")
        assert row is not None
        assert row[0] == 'b'

    def test_exec_with_retry_raises_after_max_retries(self, tmp_path: Path) -> None:
        db = AppDatabase(str(tmp_path / 'test.sqlite'))

        def always_locked():
            raise sqlite3.OperationalError('database is locked')

        with patch.object(db, 'connect', side_effect=always_locked):
            try:
                db.execute("SELECT 1")
                assert False, 'Should have raised'
            except sqlite3.OperationalError as exc:
                assert 'database is locked' in str(exc)

    def test_exec_with_retry_does_not_retry_other_errors(self, tmp_path: Path) -> None:
        db = AppDatabase(str(tmp_path / 'test.sqlite'))

        def syntax_error():
            raise sqlite3.OperationalError('near syntax error')

        with patch.object(db, 'connect', side_effect=syntax_error):
            try:
                db.execute("BAD SQL")
                assert False, 'Should have raised'
            except sqlite3.OperationalError as exc:
                assert 'syntax' in str(exc)

    def test_concurrent_writes_with_wal(self, tmp_path: Path) -> None:
        """Two threads writing to the same DB should not crash with WAL + busy_timeout."""
        db = AppDatabase(str(tmp_path / 'concurrent.sqlite'))
        db.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")

        errors: list[Exception] = []

        def writer(start: int) -> None:
            try:
                for i in range(20):
                    db.execute(
                        "INSERT OR REPLACE INTO t VALUES (?, ?)",
                        (start + i, f'val-{start + i}'),
                    )
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=writer, args=(0,))
        t2 = threading.Thread(target=writer, args=(1000,))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        assert not errors, f'Concurrent write errors: {errors}'
        rows = db.fetchall("SELECT COUNT(*) FROM t")
        assert rows[0][0] == 40


# ------------------------------------------------------------------
# A. Dashboard sub-phase timeline markers
# ------------------------------------------------------------------


class TestDashboardSubPhaseTimeline:
    """Verify _collect_summary_cards emits sub-phase markers."""

    def test_collect_summary_cards_emits_sub_phase_markers(self) -> None:
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel

        marked_phases: list[str] = []

        episode_repo = MagicMock()
        episode_repo.list_recent.return_value = []
        knowledge_repo = MagicMock()
        knowledge_repo.list_recent.return_value = []
        run_repo = MagicMock()
        run_repo.list_recent.return_value = []
        embedding_svc = MagicMock()
        embedding_svc.describe_index.return_value = {'knowledge_count': 0}

        with patch(
            'iabv_v15.ui.viewmodels.dashboard_viewmodel.DashboardViewModel._mark_timeline',
            side_effect=lambda phase, **kw: marked_phases.append(phase),
        ):
            vm = DashboardViewModel.__new__(DashboardViewModel)
            vm.episode_repository = episode_repo
            vm.knowledge_repository = knowledge_repo
            vm.run_repository = run_repo
            vm.embedding_service = embedding_svc
            cards = vm._collect_summary_cards()

        assert len(cards) == 4
        expected_markers = [
            'dashboard_vm_refresh_query_episodes_start',
            'dashboard_vm_refresh_query_episodes_done',
            'dashboard_vm_refresh_query_knowledge_done',
            'dashboard_vm_refresh_query_runs_done',
            'dashboard_vm_refresh_query_index_done',
        ]
        for marker in expected_markers:
            assert marker in marked_phases, f'Missing marker: {marker}'


# ------------------------------------------------------------------
# C. OSES SQLite lock contention finding
# ------------------------------------------------------------------


class TestOSESSqliteLockContention:
    """Verify _sqlite_lock_contention_findings reads incident file."""

    def test_reads_incident_and_produces_finding(self, tmp_path: Path) -> None:
        from iabv_v15.domain.models import IssueSeverity
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        evolution_dir = tmp_path / 'evolution'
        exam_dir = evolution_dir / 'self_examination'
        exam_dir.mkdir(parents=True)

        incident = {
            'category': 'sqlite_lock_contention',
            'title': 'database is locked durante startup',
            'summary': 'deferred_tool_availability_probe fallo con: database is locked',
            'severity': 'HIGH',
            'confidence': 0.95,
            'recommendation': 'Verificar WAL mode',
            'source_refs': ['iabv_v15.infra.persistence.database'],
            'timestamp': '2026-05-05T10:00:00+00:00',
            'error': 'database is locked',
        }
        (exam_dir / 'startup_sqlite_incident.json').write_text(
            json.dumps(incident), encoding='utf-8',
        )

        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.evolution_dir = str(evolution_dir)

        findings = svc._sqlite_lock_contention_findings()
        assert len(findings) == 1
        f = findings[0]
        assert f.category == 'sqlite_lock_contention'
        assert f.severity == IssueSeverity.HIGH
        assert 'database is locked' in f.summary

    def test_returns_empty_when_no_incident(self, tmp_path: Path) -> None:
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        svc = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
        svc.evolution_dir = str(tmp_path / 'evolution')

        findings = svc._sqlite_lock_contention_findings()
        assert findings == []


# ------------------------------------------------------------------
# Bootstrap: _record_startup_sqlite_incident
# ------------------------------------------------------------------


class TestRecordStartupSqliteIncident:
    """Verify bootstrap persists incident file on 'database is locked'."""

    def test_persists_incident_file(self, tmp_path: Path) -> None:
        from types import SimpleNamespace

        from iabv_v15.bootstrap import AppBootstrap

        boot = AppBootstrap.__new__(AppBootstrap)
        boot.config = SimpleNamespace(evolution_dir=str(tmp_path / 'evolution'))

        exc = sqlite3.OperationalError('database is locked')
        boot._record_startup_sqlite_incident(exc)

        incident_path = tmp_path / 'evolution' / 'self_examination' / 'startup_sqlite_incident.json'
        assert incident_path.exists()
        data = json.loads(incident_path.read_text(encoding='utf-8'))
        assert data['category'] == 'sqlite_lock_contention'
        assert 'database is locked' in data['error']

    def test_ignores_non_lock_errors(self, tmp_path: Path) -> None:
        from types import SimpleNamespace

        from iabv_v15.bootstrap import AppBootstrap

        boot = AppBootstrap.__new__(AppBootstrap)
        boot.config = SimpleNamespace(evolution_dir=str(tmp_path / 'evolution'))

        exc = RuntimeError('some other error')
        boot._record_startup_sqlite_incident(exc)

        incident_path = tmp_path / 'evolution' / 'self_examination' / 'startup_sqlite_incident.json'
        assert not incident_path.exists()


# ------------------------------------------------------------------
# ToolRegistry: seed_defaults graceful handling
# ------------------------------------------------------------------


class TestToolRegistrySeedDefaultsGraceful:
    """Verify _seed_defaults catches save_card / refresh_card errors."""

    def test_seed_defaults_survives_save_card_failure(self, tmp_path: Path) -> None:
        from iabv_v15.services.tools.tool_registry import ToolRegistry

        db = AppDatabase(str(tmp_path / 'tools.sqlite'))
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository

        repo = ToolRecordRepository(db, ArtifactStorage(str(tmp_path / 'storage')))

        original_save = repo.save_card
        save_calls = []

        def failing_save(card):
            save_calls.append(card.tool_id)
            if len(save_calls) <= 2:
                raise sqlite3.OperationalError('database is locked')
            return original_save(card)

        repo.save_card = failing_save

        adapters: dict = {}
        registry = ToolRegistry(repo, adapters)
        assert registry is not None
        assert len(save_calls) >= 1


# ------------------------------------------------------------------
# Dashboard query limit reduction
# ------------------------------------------------------------------


class TestDashboardQueryLimit:
    """Verify dashboard queries use reduced limit."""

    def test_summary_query_limit_is_low(self) -> None:
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
        assert DashboardViewModel._SUMMARY_QUERY_LIMIT <= 20

    def test_collect_summary_cards_passes_limit(self) -> None:
        from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel

        episode_repo = MagicMock()
        episode_repo.list_recent.return_value = []
        knowledge_repo = MagicMock()
        knowledge_repo.list_recent.return_value = []
        run_repo = MagicMock()
        run_repo.list_recent.return_value = []
        embedding_svc = MagicMock()
        embedding_svc.describe_index.return_value = {'knowledge_count': 0}

        with patch(
            'iabv_v15.ui.viewmodels.dashboard_viewmodel.DashboardViewModel._mark_timeline',
        ):
            vm = DashboardViewModel.__new__(DashboardViewModel)
            vm.episode_repository = episode_repo
            vm.knowledge_repository = knowledge_repo
            vm.run_repository = run_repo
            vm.embedding_service = embedding_svc
            vm._collect_summary_cards()

        limit = DashboardViewModel._SUMMARY_QUERY_LIMIT
        episode_repo.list_recent.assert_called_once_with(limit=limit)
        knowledge_repo.list_recent.assert_called_once_with(limit=limit)
        run_repo.list_recent.assert_called_once_with(limit=limit)


# ------------------------------------------------------------------
# Incident generation from tool probes (not just fatal errors)
# ------------------------------------------------------------------


class TestIncidentFromToolProbes:
    """Verify _log_tool_availability records incident on probe lock errors."""

    def test_lock_errors_during_probes_generate_incident(self, tmp_path: Path) -> None:
        from types import SimpleNamespace

        from iabv_v15.bootstrap import AppBootstrap

        boot = AppBootstrap.__new__(AppBootstrap)
        boot.config = SimpleNamespace(evolution_dir=str(tmp_path / 'evolution'))
        boot._tool_availability_logged = False
        boot._timeline = MagicMock()

        # Simulate tool_registry that raises lock error during refresh
        tool_card = MagicMock()
        tool_card.tool_id = 'test_tool'
        tool_card.adapter_key = 'test_adapter'
        tool_card.available = False
        tool_card.last_validated_at_utc = None

        registry = MagicMock()
        registry.list_cards.return_value = [tool_card]
        registry.refresh_card.side_effect = sqlite3.OperationalError('database is locked')
        boot.tool_registry = registry

        # Run _log_tool_availability — should NOT raise, but should
        # record incident file
        with patch.dict('os.environ', {'IABV_MCP_SUBPROCESS': '0'}):
            try:
                boot._log_tool_availability()
            except Exception:
                pass

        incident_path = tmp_path / 'evolution' / 'self_examination' / 'startup_sqlite_incident.json'
        assert incident_path.exists(), 'Incident file should be created on probe lock errors'
        data = json.loads(incident_path.read_text(encoding='utf-8'))
        assert data['category'] == 'sqlite_lock_contention'


# ------------------------------------------------------------------
# ToolRegistry: seed_defaults skips refresh_card
# ------------------------------------------------------------------


class TestSeedDefaultsSkipsRefresh:
    """Verify _seed_defaults no longer calls refresh_card for existing cards."""

    def test_seed_defaults_does_not_refresh_existing_unchanged(self, tmp_path: Path) -> None:
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        from iabv_v15.services.tools.tool_registry import ToolRegistry

        db = AppDatabase(str(tmp_path / 'tools2.sqlite'))
        repo = ToolRecordRepository(db, ArtifactStorage(str(tmp_path / 'storage2')))

        # First init seeds defaults
        registry1 = ToolRegistry(repo, {})
        cards_after_first = repo.list_cards()
        assert len(cards_after_first) > 0

        # Second init should NOT call refresh_card for existing unchanged cards
        with patch.object(ToolRegistry, 'refresh_card', wraps=lambda self, c, **kw: c) as mock_refresh:
            registry2 = ToolRegistry(repo, {})
            # refresh_card should NOT be called during seed_defaults
            assert mock_refresh.call_count == 0


# ------------------------------------------------------------------
# cpu_frequency regression (PR #342)
# ------------------------------------------------------------------


class TestCpuFrequencyRegression:
    """Verify cpu_frequency is marked sensor_not_exposed, not UNRESOLVED."""

    def test_missing_cpu_frequency_marked_not_available(self, tmp_path: Path) -> None:
        root = tmp_path / 'cpu_freq_test'
        root.mkdir()
        try:
            from iabv_v15.bootstrap import AppBootstrap
            bootstrap = AppBootstrap(str(root))
            svc = bootstrap.environment_self_awareness_service
            model = svc.current_model()
            hw = model.hardware_profile
            if hw.get('current_clock_mhz') is None or hw.get('max_clock_mhz') is None:
                sensors = hw.get('sensors_not_available', [])
                sensor_names = [s['sensor'] for s in sensors]
                assert 'cpu_frequency' in sensor_names
                cpu_entry = next(s for s in sensors if s['sensor'] == 'cpu_frequency')
                assert cpu_entry['reason'] == 'sensor_not_exposed_on_this_host'
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ------------------------------------------------------------------
# Integration: database + tool_registry under concurrent access
# ------------------------------------------------------------------


class TestToolRegistryConcurrentAccess:
    """Simulate UI + MCP concurrent DB access with WAL."""

    def test_concurrent_seed_and_query(self, tmp_path: Path) -> None:
        db = AppDatabase(str(tmp_path / 'concurrent_tools.sqlite'))

        errors: list[Exception] = []

        def seed_writer():
            try:
                from iabv_v15.infra.persistence.storage import ArtifactStorage
                from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
                repo = ToolRecordRepository(db, ArtifactStorage(str(tmp_path / 's1')))
                from iabv_v15.services.tools.tool_registry import ToolRegistry
                ToolRegistry(repo, {})
            except Exception as exc:
                errors.append(exc)

        def query_reader():
            try:
                for _ in range(10):
                    db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
                    time.sleep(0.05)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=seed_writer)
        t2 = threading.Thread(target=query_reader)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        assert not errors, f'Concurrent access errors: {errors}'
