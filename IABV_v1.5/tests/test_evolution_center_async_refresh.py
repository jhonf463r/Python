"""Tests for EvolutionCenterViewModel async refresh.

Covers:
- refreshAsync() runs data collection off the UI thread
- Generation-based coalescing discards stale results
- Synchronous refresh() still works for tests (backward compat)
- _collect_refresh_data() returns expected shape
- _apply_collected_data() correctly sets all UI properties
- In-flight guard prevents duplicate background work
- Service failures are tolerated with safe defaults
"""
from __future__ import annotations

import time
import threading
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

# Break circular import: pre-import the modules that cause the cycle.
import iabv_v15.services.roles.analytics_strategy_service  # noqa: F401
import iabv_v15.services.roles.engineering_review_service   # noqa: F401

from iabv_v15.ui.viewmodels.evolution_center_viewmodel import EvolutionCenterViewModel


def _make_minimal_vm(*, defer: bool = True) -> EvolutionCenterViewModel:
    """Create EvolutionCenterViewModel with mocked dependencies."""
    health = SimpleNamespace(
        model_dump=lambda mode='json': {'summary': 'health ok'},
        summary='health ok',
    )
    dossier = SimpleNamespace(model_dump=lambda mode='json': {'dossier_id': 'd1', 'title': 'D1'})
    incident = SimpleNamespace(model_dump=lambda mode='json': {
        'incident_id': 'i1', 'severity': 'medium', 'status': 'open',
        'summary': 'inc1', 'incident_kind': 'test',
    })
    backlog_item = SimpleNamespace(model_dump=lambda mode='json': {'issue_id': 'b1'})
    pending_item = SimpleNamespace(model_dump=lambda mode='json': {'issue_id': 'p1'})
    tool_card = SimpleNamespace(model_dump=lambda mode='json': {'tool_id': 't1'})

    mock_evolution_review = MagicMock()
    mock_evolution_review.build_project_health.return_value = health
    mock_evolution_review.build_improvement_backlog.return_value = [backlog_item]

    mock_dossier_repo = MagicMock()
    mock_dossier_repo.list_recent.return_value = [dossier]

    mock_incident_repo = MagicMock()
    mock_incident_repo.list_recent.return_value = [incident]

    mock_pending_repo = MagicMock()
    mock_pending_repo.list_recent.return_value = [pending_item]

    mock_tool_repo = MagicMock()
    mock_tool_repo.list_cards.return_value = [tool_card]

    vm = EvolutionCenterViewModel(
        dossier_repository=mock_dossier_repo,
        hidden_incident_repository=mock_incident_repo,
        evolution_review_service=mock_evolution_review,
        incident_packet_service=MagicMock(),
        self_check_orchestrator=MagicMock(),
        pending_issue_repository=mock_pending_repo,
        tool_record_repository=mock_tool_repo,
        defer_initial_refresh=defer,
    )
    # Wait for any deferred refresh to complete
    if defer:
        for _ in range(20):
            if not vm._refresh_in_flight:
                break
            time.sleep(0.1)
    return vm


# --- Shape & data ---

def test_collect_refresh_data_returns_expected_shape() -> None:
    vm = _make_minimal_vm()
    data = vm._collect_refresh_data()
    expected_keys = {
        'snapshot', 'dossiers', 'filtered_incidents', 'backlog',
        'pending', 'tool_cards', 'ia_comparisons',
        'environment_self_model', 'world_model', 'autonomous_validation',
        'portable_context', 'self_examination', 'control_master_digest',
    }
    assert expected_keys.issubset(data.keys()), f'Missing keys: {expected_keys - data.keys()}'


def test_collect_refresh_data_populates_from_services() -> None:
    vm = _make_minimal_vm()
    data = vm._collect_refresh_data()
    assert data['snapshot'] is not None
    assert data['snapshot']['summary'] == 'health ok'
    assert len(data['dossiers']) == 1
    assert data['dossiers'][0]['dossier_id'] == 'd1'
    assert len(data['filtered_incidents']) == 1
    assert len(data['backlog']) == 1
    assert len(data['pending']) == 1
    assert len(data['tool_cards']) == 1


# --- Apply ---

def test_apply_collected_data_sets_properties() -> None:
    vm = _make_minimal_vm()
    data = vm._collect_refresh_data()
    data['_status_summary'] = 'health ok'
    vm._apply_collected_data(data)

    assert vm._health_snapshot['summary'] == 'health ok'
    assert len(vm._recent_dossiers) == 1
    assert len(vm._recent_incidents) == 1
    assert len(vm._improvement_backlog) == 1
    assert len(vm._recent_pending_issues) == 1
    assert len(vm._known_tool_cards) == 1
    assert 'health ok' in vm._status_text


# --- Sync refresh backward compat ---

def test_sync_refresh_works() -> None:
    vm = _make_minimal_vm()
    vm._health_snapshot = {}
    vm.refresh()
    assert vm._health_snapshot.get('summary') == 'health ok'
    assert len(vm._recent_dossiers) == 1


def test_sync_refresh_emits_data_changed() -> None:
    vm = _make_minimal_vm()
    emissions: list[bool] = []
    vm.dataChanged.connect(lambda: emissions.append(True))
    vm.refresh()
    assert len(emissions) >= 1, 'refresh() must emit dataChanged at least once'


# --- Async refresh ---

def test_refresh_async_runs_off_calling_thread() -> None:
    vm = _make_minimal_vm()
    collection_threads: list[str] = []
    original_collect = vm._collect_refresh_data

    def tracking_collect() -> dict[str, Any]:
        collection_threads.append(threading.current_thread().name)
        return original_collect()

    vm._collect_refresh_data = tracking_collect  # type: ignore[assignment]
    vm._refresh_in_flight = False
    vm.refreshAsync()
    time.sleep(1.5)

    assert len(collection_threads) >= 1
    assert collection_threads[0] != threading.current_thread().name
    assert 'ecvm-bg' in collection_threads[0]


def test_refresh_async_in_flight_guard() -> None:
    vm = _make_minimal_vm()
    call_count = 0
    original_collect = vm._collect_refresh_data

    def slow_collect() -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        time.sleep(0.5)
        return original_collect()

    vm._collect_refresh_data = slow_collect  # type: ignore[assignment]
    vm._refresh_in_flight = False
    vm.refreshAsync()
    vm.refreshAsync()  # should be skipped
    vm.refreshAsync()  # should be skipped
    time.sleep(2.0)

    assert call_count == 1, f'Expected 1 bg call, got {call_count}'


# --- Generation coalescing ---

def test_generation_increments_on_refresh_async() -> None:
    vm = _make_minimal_vm()
    vm._refresh_in_flight = False
    vm._refresh_generation = 0

    gen_before = vm._refresh_generation
    vm.refreshAsync()
    gen_after = vm._refresh_generation
    assert gen_after == gen_before + 1
    time.sleep(1.0)


def test_apply_refresh_snapshot_discards_stale() -> None:
    vm = _make_minimal_vm()
    vm._refresh_generation = 5

    data = vm._collect_refresh_data()
    data['_status_summary'] = 'stale data'
    vm._health_snapshot = {}
    vm._apply_refresh_snapshot(3, data)

    assert vm._health_snapshot == {}  # not applied


def test_apply_refresh_snapshot_accepts_matching() -> None:
    vm = _make_minimal_vm()
    vm._refresh_generation = 5

    data = vm._collect_refresh_data()
    data['_status_summary'] = 'health ok'
    vm._apply_refresh_snapshot(5, data)

    assert vm._health_snapshot.get('summary') == 'health ok'


# --- Service failures ---

def test_collect_tolerates_service_failures() -> None:
    mock_evolution_review = MagicMock()
    mock_evolution_review.build_project_health.side_effect = RuntimeError('db error')
    mock_evolution_review.build_improvement_backlog.side_effect = RuntimeError('db error')

    mock_dossier_repo = MagicMock()
    mock_dossier_repo.list_recent.side_effect = RuntimeError('db error')

    mock_incident_repo = MagicMock()
    mock_incident_repo.list_recent.side_effect = RuntimeError('db error')

    vm = EvolutionCenterViewModel(
        dossier_repository=mock_dossier_repo,
        hidden_incident_repository=mock_incident_repo,
        evolution_review_service=mock_evolution_review,
        incident_packet_service=MagicMock(),
        self_check_orchestrator=MagicMock(),
        defer_initial_refresh=True,
    )
    time.sleep(0.5)  # let deferred refresh attempt complete
    data = vm._collect_refresh_data()

    assert data['snapshot'] is None
    assert data['dossiers'] == []
    assert data['filtered_incidents'] == []
    assert data['backlog'] == []


# --- Infrastructure ---

def test_bg_pool_single_threaded() -> None:
    vm = _make_minimal_vm()
    assert vm._bg_pool._max_workers == 1


def test_has_refresh_ready_signal() -> None:
    vm = _make_minimal_vm()
    assert hasattr(vm, 'refreshReady')


# --- Granular signals ---

def test_apply_collected_data_does_not_emit_dataChanged() -> None:
    """_apply_collected_data must emit granular signals, not dataChanged."""
    vm = _make_minimal_vm()
    data_emissions: list[bool] = []
    vm.dataChanged.connect(lambda: data_emissions.append(True))
    data = vm._collect_refresh_data()
    data['_status_summary'] = 'test'
    vm._apply_collected_data(data)
    assert len(data_emissions) == 0, (
        '_apply_collected_data should NOT emit dataChanged; '
        f'got {len(data_emissions)} emissions'
    )


def test_apply_collected_data_emits_granular_signals() -> None:
    """_apply_collected_data must emit all expected granular signals."""
    vm = _make_minimal_vm()
    signal_names = [
        'overviewChanged', 'incidentsChanged', 'dossiersChanged',
        'backlogChanged', 'toolsChanged', 'worldModelChanged',
        'metacognitionChanged', 'screenshotsChanged', 'proactiveChanged',
        'iaComparisonsChanged',
    ]
    counts: dict[str, int] = {name: 0 for name in signal_names}
    for name in signal_names:
        sig = getattr(vm, name)
        sig.connect(lambda n=name: counts.__setitem__(n, counts[n] + 1))

    data = vm._collect_refresh_data()
    data['_status_summary'] = 'test'
    vm._apply_collected_data(data)

    for name in signal_names:
        assert counts[name] >= 1, f'{name} was not emitted by _apply_collected_data'


def test_sync_refresh_emits_dataChanged_for_compat() -> None:
    """refresh() (sync) must still emit dataChanged for backward compat."""
    vm = _make_minimal_vm()
    emissions: list[bool] = []
    vm.dataChanged.connect(lambda: emissions.append(True))
    vm.refresh()
    assert len(emissions) >= 1, 'refresh() must emit dataChanged for compat'


def test_refreshAsync_does_not_emit_dataChanged() -> None:
    """refreshAsync path must NOT emit dataChanged (only granular)."""
    vm = _make_minimal_vm()
    data_emissions: list[bool] = []
    vm.dataChanged.connect(lambda: data_emissions.append(True))
    vm._refresh_in_flight = False
    vm.refreshAsync()
    for _ in range(30):
        if not vm._refresh_in_flight:
            break
        time.sleep(0.1)
    assert len(data_emissions) == 0, (
        'refreshAsync should NOT emit dataChanged; '
        f'got {len(data_emissions)} emissions'
    )


def test_granular_signals_exist_on_vm() -> None:
    """All granular signal attributes must exist."""
    vm = _make_minimal_vm()
    expected = [
        'overviewChanged', 'incidentsChanged', 'dossiersChanged',
        'backlogChanged', 'toolsChanged', 'worldModelChanged',
        'metacognitionChanged', 'screenshotsChanged', 'proactiveChanged',
        'publishPrChanged', 'iaComparisonsChanged', 'clipboardChanged',
    ]
    for name in expected:
        assert hasattr(vm, name), f'Missing granular signal: {name}'
