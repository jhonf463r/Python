"""Tests for CentroVivoViewModel — unified operational dashboard."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    IssueSeverity,
    NetworkStatusSnapshot,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    TaskIntent,
    ToolCard,
    ToolLiveStatus,
    ToolType,
    ToolValidationStatus,
    WindowObservation,
    WorldModelSnapshot,
)
from iabv_v15.ui.viewmodels.centro_vivo_viewmodel import CentroVivoViewModel


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


# ------------------------------------------------------------------
# Fakes
# ------------------------------------------------------------------

class FakeAdaptiveSessionRepository:
    def __init__(self, sessions: list[AdaptiveSession] | None = None):
        self._sessions = sessions or []

    def list_recent(self, limit: int = 20) -> list[AdaptiveSession]:
        return self._sessions[:limit]


class FakeToolRecordRepository:
    def __init__(self, cards: list[ToolCard] | None = None):
        self._cards = cards or []

    def list_cards(self) -> list[ToolCard]:
        return self._cards


class FakeExperimentLabRepository:
    def __init__(self, runs=None, recommendations=None):
        self._runs = runs or []
        self._recommendations = recommendations or []

    def list_runs(self, limit: int = 20, **kwargs) -> list:
        return self._runs[:limit]

    def list_recommendations(self, limit: int = 10, **kwargs) -> list:
        return self._recommendations[:limit]


class FakeSelfExaminationService:
    def __init__(self, review: SelfExaminationSnapshot | None = None):
        self._review = review

    def current_review_cached(self) -> SelfExaminationSnapshot | None:
        return self._review

    def current_review(self, *, refresh: bool = False) -> SelfExaminationSnapshot | None:
        raise AssertionError('Centro Vivo must not use the active OSES reader')


class FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot | None = None):
        self._snapshot = snapshot

    def current_model(self) -> WorldModelSnapshot | None:
        return self._snapshot


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_centro_vivo_empty_state():
    """ViewModel with no services returns empty lists and sane status."""
    vm = CentroVivoViewModel()
    assert vm.get_orchestrator_queue() == []
    assert vm.get_ia_distribution() == []
    assert vm.get_heuristic_decisions() == []
    assert vm.get_experiment_metrics() == []
    assert vm.get_learning_gaps() == []
    assert vm.get_self_examination_findings() == []
    assert vm.get_world_model_summary() == {}
    assert vm.get_working() is False
    assert vm.get_last_refresh_utc() != ''
    assert '0 sesiones en cola' in vm.get_status_text()


def test_centro_vivo_orchestrator_queue():
    """Orchestrator queue populated from AdaptiveSessionRepository."""
    sessions = [
        AdaptiveSession(
            session_id='s1',
            user_goal='Fix login bug',
            intent=TaskIntent(intent_key='project.evolution'),
            status=AdaptiveSessionStatus.EXECUTING,
            chosen_pack_title='Code Review Pack',
        ),
        AdaptiveSession(
            session_id='s2',
            user_goal='Research GPU models',
            intent=TaskIntent(intent_key='research.local'),
            status=AdaptiveSessionStatus.PLANNED,
        ),
    ]
    repo = FakeAdaptiveSessionRepository(sessions)
    vm = CentroVivoViewModel(adaptive_session_repository=repo)

    queue = vm.get_orchestrator_queue()
    assert len(queue) == 2
    assert queue[0]['session_id'] == 's1'
    assert queue[0]['user_goal'] == 'Fix login bug'
    assert queue[0]['status'] == 'executing'
    assert queue[0]['chosen_pack'] == 'Code Review Pack'
    assert queue[1]['status'] == 'planned'
    assert '1 activas' in vm.get_status_text()


def test_centro_vivo_ia_distribution():
    """IA distribution populated from ToolRecordRepository cards."""
    cards = [
        ToolCard(tool_id='ollama_llm', title='Ollama LLM', tool_type=ToolType.LLM_LOCAL, adapter_key='ollama', available=True),
        ToolCard(tool_id='devin_api', title='Devin API', tool_type=ToolType.MCP_CLIENT, adapter_key='devin', available=True),
        ToolCard(tool_id='claude_web', title='Claude Web', tool_type=ToolType.LLM_WEB_UI, adapter_key='claude', available=False),
    ]
    repo = FakeToolRecordRepository(cards)
    vm = CentroVivoViewModel(tool_record_repository=repo)

    dist = vm.get_ia_distribution()
    assert len(dist) == 3
    assert dist[0]['tool_id'] == 'ollama_llm'


def test_centro_vivo_self_examination_findings():
    """Findings from OperationalSelfExaminationService are surfaced."""
    findings = [
        SelfExaminationFinding(
            finding_id='f1',
            category='performance',
            title='High latency on Ollama',
            severity=IssueSeverity.HIGH,
            confidence=0.85,
            recommendation='Switch to qwen3:4b for fast queries',
            status='observed',
        ),
        SelfExaminationFinding(
            finding_id='f2',
            category='routing',
            title='Claude web underutilized',
            severity=IssueSeverity.MEDIUM,
            confidence=0.60,
            recommendation='Route web_browsing tasks to Claude',
            status='observed',
        ),
    ]
    review = SelfExaminationSnapshot(
        review_id='r1',
        findings=findings,
        source_coverage={'run_repository': 'READ_OK'},
        source_errors={},
        metadata={
            'source_coverage_contract': 'OSES_SOURCE_COVERAGE_R1',
            'required_source_ids': ['run_repository'],
            'source_coverage': {'run_repository': 'READ_OK'},
            'source_errors': {},
        },
    )
    service = FakeSelfExaminationService(review)
    vm = CentroVivoViewModel(self_examination_service=service)

    result = vm.get_self_examination_findings()
    assert len(result) == 2
    assert result[0]['title'] == 'High latency on Ollama'
    assert result[0]['severity'] == 'high'
    assert result[0]['confidence'] == 0.85
    assert result[1]['category'] == 'routing'
    assert '2 hallazgos' in vm.get_status_text()


def test_centro_vivo_world_model_summary():
    """World model summary extracted from WorldModelService."""
    snapshot = WorldModelSnapshot(
        active_windows=[
            WindowObservation(title='Opera', app_name='opera'),
            WindowObservation(title='PowerShell', app_name='powershell'),
        ],
        focused_window=WindowObservation(title='Opera', app_name='opera'),
        tool_live_status=[
            ToolLiveStatus(tool_id='ollama', status='ready', available=True),
            ToolLiveStatus(tool_id='devin', status='ready', available=True),
            ToolLiveStatus(tool_id='claude', status='degraded', available=False),
        ],
        network_status=NetworkStatusSnapshot(connected=True),
    )
    service = FakeWorldModelService(snapshot)
    vm = CentroVivoViewModel(world_model_service=service)

    summary = vm.get_world_model_summary()
    assert summary['window_count'] == 2
    assert summary['network_connected'] is True
    assert summary['tool_count'] == 3
    assert summary['tools_ready'] == 2
    assert summary['tools_degraded'] == 1
    assert '2/3 herramientas listas' in vm.get_status_text()


def test_centro_vivo_learning_gaps_from_backlog():
    """Learning gaps populated from chat_research_backlog jsonl files."""
    workspace = _workspace('test_centro_vivo_learning_gaps')
    try:
        backlog_dir = workspace / 'chat_research_backlog'
        backlog_dir.mkdir(parents=True, exist_ok=True)
        entries = [
            {
                'kind': 'gpu_hardware',
                'label': 'GPU detectada por usuario',
                'snippet': 'tengo GPU RTX 4060',
                'research_hint': 'Probar modelos con CUDA',
                'timestamp': '2026-04-22T00:00:01Z',
                'session_id': 'sess1',
            },
            {
                'kind': 'local_model',
                'label': 'Modelo local mencionado',
                'snippet': 'instale qwen3',
                'research_hint': 'Verificar rendimiento de qwen3',
                'timestamp': '2026-04-22T00:00:02Z',
                'session_id': 'sess1',
            },
        ]
        fp = backlog_dir / 'sess1.jsonl'
        fp.write_text('\n'.join(json.dumps(e) for e in entries), encoding='utf-8')

        vm = CentroVivoViewModel(data_root=str(workspace))

        gaps = vm.get_learning_gaps()
        assert len(gaps) == 2
        assert gaps[0]['kind'] == 'local_model'
        assert gaps[0]['snippet'] == 'instale qwen3'
        assert gaps[1]['kind'] == 'gpu_hardware'
        assert '2 areas de investigacion' in vm.get_status_text()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_centro_vivo_refresh_updates_data():
    """Calling refresh() updates all data."""
    sessions = [
        AdaptiveSession(
            session_id='s1',
            user_goal='Initial goal',
            intent=TaskIntent(intent_key='general.assistance'),
            status=AdaptiveSessionStatus.COMPLETED,
        ),
    ]
    repo = FakeAdaptiveSessionRepository(sessions)
    vm = CentroVivoViewModel(adaptive_session_repository=repo)

    assert len(vm.get_orchestrator_queue()) == 1
    first_ts = vm.get_last_refresh_utc()

    repo._sessions.append(
        AdaptiveSession(
            session_id='s2',
            user_goal='New task',
            intent=TaskIntent(intent_key='research.local'),
            status=AdaptiveSessionStatus.EXECUTING,
        ),
    )
    vm.refresh()

    assert len(vm.get_orchestrator_queue()) == 2
    assert vm.get_last_refresh_utc() >= first_ts


def test_centro_vivo_bootstrap_wires_viewmodel():
    """Bootstrap creates and wires CentroVivoViewModel."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    workspace = _workspace('test_centro_vivo_bootstrap')
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        from iabv_v15.bootstrap import AppBootstrap
        bootstrap = AppBootstrap(str(workspace))
        bootstrap._build_ui_objects()

        assert hasattr(bootstrap, 'centro_vivo_viewmodel')
        vm = bootstrap.centro_vivo_viewmodel
        assert isinstance(vm, CentroVivoViewModel)
        assert isinstance(vm.get_orchestrator_queue(), list)
        assert isinstance(vm.get_ia_distribution(), list)
        assert isinstance(vm.get_world_model_summary(), dict)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_centro_vivo_navigation_route_exists():
    """NavigationController includes centro_vivo route."""
    from iabv_v15.ui.controllers.navigation_controller import NavigationController
    nav = NavigationController()
    keys = [r['key'] for r in nav.get_routes()]
    assert 'centro_vivo' in keys

    nav.navigate('centro_vivo')
    assert nav.get_current_route() == 'centro_vivo'

def test_centro_vivo_does_not_fall_back_to_active_oses_reader_when_cache_missing():
    class LegacyOnlyOSES:
        def current_review(self, *, refresh: bool = False):
            raise AssertionError('active OSES reader must not be called')

    vm = CentroVivoViewModel(self_examination_service=LegacyOnlyOSES())

    assert vm.get_self_examination_findings() == []
    assert vm.get_self_examination_status() == 'READ_UNVERIFIED'
    assert 'OSES READ_UNVERIFIED' in vm.get_status_text()
\n

def test_centro_vivo_exposes_read_failures_instead_of_clean_empty_panels(tmp_path):
    class FailingSessionRepository:
        def list_recent(self, limit=20):
            raise RuntimeError('session repository unavailable')

    class FailingWorldModel:
        def current_model(self):
            raise RuntimeError('world model unavailable')

    vm = CentroVivoViewModel(
        adaptive_session_repository=FailingSessionRepository(),
        world_model_service=FailingWorldModel(),
        data_root=str(tmp_path),
    )

    assert vm.get_orchestrator_queue() == []
    assert vm.get_source_statuses()['adaptive_session_repository'] == 'READ_FAILED'
    assert vm.get_source_statuses()['world_model_service'] == 'READ_FAILED'
    assert 'Fuentes no verificadas:' in vm.get_status_text()
    assert 'adaptive_session_repository=READ_FAILED' in vm.get_status_text()
    assert 'world_model_service=READ_FAILED' in vm.get_status_text()


def test_centro_vivo_distinguishes_missing_learning_gap_source_from_verified_empty(tmp_path):
    vm = CentroVivoViewModel(data_root=str(tmp_path))

    assert vm.get_learning_gaps() == []
    assert vm.get_source_statuses()['learning_gaps'] == 'CONFIRMED_NOT_FOUND'
    assert 'learning_gaps=CONFIRMED_NOT_FOUND' in vm.get_status_text()


def test_centro_vivo_marks_unconfigured_services_without_claiming_empty_is_verified():
    vm = CentroVivoViewModel()

    statuses = vm.get_source_statuses()
    assert statuses['adaptive_session_repository'] == 'NOT_CONFIGURED'
    assert statuses['tool_record_repository'] == 'NOT_CONFIGURED'
    assert statuses['self_examination_service'] == 'NOT_CONFIGURED'
    assert 'Fuentes no verificadas:' in vm.get_status_text()


def test_centro_vivo_preserves_partial_tool_record_diagnostics_and_redacts_paths(tmp_path):
    report = type('Report', (), {
        'status': type('Status', (), {'value': 'READ_PARTIAL'})(),
        'records_seen': 2,
        'records_loaded': 1,
        'failed_ids': ['corrupt-card'],
        'missing_ids': [],
        'collection_error_type': '',
        'to_dict': lambda self: {
            'status': 'READ_PARTIAL',
            'records_seen': 2,
            'records_loaded': 1,
            'failed_ids': ['corrupt-card'],
            'path': 'C:/Users/private-user/IABV/data/tool_records',
        },
    })()

    class ReportedReadError(RuntimeError):
        def __init__(self):
            super().__init__('partial ToolRecord read')
            self.report = report

    class PartialToolRecordRepository:
        last_read_report = report

        def list_cards(self):
            raise ReportedReadError()

    vm = CentroVivoViewModel(
        tool_record_repository=PartialToolRecordRepository(),
        data_root=str(tmp_path),
    )

    assert vm.get_ia_distribution() == []
    assert vm.get_source_statuses()['tool_record_repository'] == 'READ_PARTIAL'
    diagnostic = vm.get_source_reports()['tool_record_repository']
    assert diagnostic['records_loaded'] == 1
    assert 'path' not in diagnostic
    assert 'private-user' not in str(diagnostic)
    assert 'tool_record_repository=READ_PARTIAL' in vm.get_status_text()


def test_centro_vivo_account_inventory_propagates_partial_subsource_coverage(tmp_path, monkeypatch):
    from iabv_v15.domain.models import AccountInventorySnapshot
    from iabv_v15.services import account_resource_scanner

    snapshot = AccountInventorySnapshot(
        source_coverage={
            'browser_accounts': 'READ_OK',
            'browser_sessions': 'READ_PARTIAL',
            'quota_tracker': 'READ_FAILED',
        },
        source_errors={
            'browser_sessions': 'PermissionError',
            'quota_tracker': 'PermissionError',
        },
    )
    monkeypatch.setattr(
        account_resource_scanner,
        'build_inventory_snapshot',
        lambda: snapshot,
    )
    vm = CentroVivoViewModel(
        data_root=str(tmp_path),
        defer_initial_refresh=True,
    )

    vm.refresh()

    assert vm.get_account_inventory() == []
    assert vm.get_source_statuses()['account_inventory'] == 'READ_FAILED'
    reports = vm.get_source_reports()['account_inventory']
    assert reports['source_coverage']['browser_sessions'] == 'READ_PARTIAL'
    assert reports['source_coverage']['quota_tracker'] == 'READ_FAILED'



def test_centro_vivo_preserves_read_failed_self_examination_status() -> None:
    review = SelfExaminationSnapshot(
        review_id='r-failed',
        findings=[],
        source_coverage={'run_repository': 'READ_FAILED'},
        source_errors={'run_repository': 'PermissionError'},
        metadata={
            'source_coverage_contract': 'OSES_SOURCE_COVERAGE_R1',
            'required_source_ids': ['run_repository'],
            'source_coverage': {'run_repository': 'READ_FAILED'},
            'source_errors': {'run_repository': 'PermissionError'},
        },
    )
    vm = CentroVivoViewModel(self_examination_service=FakeSelfExaminationService(review))

    assert vm.get_self_examination_findings() == []
    assert vm._self_examination_status == 'READ_FAILED'


import pytest


@pytest.mark.parametrize('status', ['READ_FAILED', 'CORRUPT', 'SCHEMA_UNSUPPORTED'])
def test_centro_vivo_maps_corrupt_account_subsources_to_read_failed(tmp_path, monkeypatch, status) -> None:
    from iabv15.domain.models import AccountInventorySnapshot
    from iabv15.services import account_resource_scanner

    snapshot = AccountInventorySnapshot(
        source_coverage={'quota_tracker': status},
        source_errors={'quota_tracker': 'invalid_or_unreadable'},
    )
    monkeypatch.setattr(account_resource_scanner, 'build_inventory_snapshot', lambda: snapshot)
    vm = CentroVivoViewModel(data_root=str(tmp_path), defer_initial_refresh=True)

    vm.refresh()

    assert vm.get_source_statuses()['account_inventory'] == 'READ_FAILED'
