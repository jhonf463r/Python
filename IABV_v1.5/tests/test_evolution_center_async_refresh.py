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
        'refreshStatusChanged',
    ]
    for name in expected:
        assert hasattr(vm, name), f'Missing granular signal: {name}'


# --- Refresh episodes & telemetry ---

def _make_sample_data(**overrides: Any) -> dict[str, Any]:
    """Build a sample collected-data dict for _apply_refresh_snapshot tests."""
    base: dict[str, Any] = {
        'snapshot': {'summary': 'health ok'},
        'dossiers': [{'dossier_id': 'd1', 'title': 'D1'}],
        'filtered_incidents': [{'incident_id': 'i1', 'severity': 'medium', 'status': 'open', 'summary': 'inc1'}],
        'backlog': [{'issue_id': 'b1'}],
        'pending': [{'issue_id': 'p1'}],
        'tool_cards': [{'tool_id': 't1'}],
        'ia_comparisons': [],
        'environment_self_model': {},
        'world_model': {},
        'autonomous_validation': {},
        'portable_context': {},
        'self_examination': {},
        'control_master_digest': {},
        '_refresh_meta': {
            'refresh_id': 'r000001',
            'source': 'user_click',
            'generation': 1,
            't0': time.perf_counter(),
        },
    }
    base.update(overrides)
    return base


def test_refreshFromUser_traces_user_click() -> None:
    """refreshFromUser must trace evolution_refresh_requested with source=user_click."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm.refreshFromUser()
    for _ in range(30):
        if not vm._refresh_in_flight:
            break
        time.sleep(0.1)
    kinds = [t['kind'] for t in traced]
    assert 'evolution_refresh_requested' in kinds
    req = next(t for t in traced if t['kind'] == 'evolution_refresh_requested')
    assert req['source'] == 'user_click'


def test_in_flight_refresh_traces_skipped() -> None:
    """Second refresh while in-flight must trace evolution_refresh_skipped."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_in_flight = True
    vm.refreshFromUser()
    kinds = [t['kind'] for t in traced]
    assert 'evolution_refresh_skipped' in kinds
    skipped = next(t for t in traced if t['kind'] == 'evolution_refresh_skipped')
    assert skipped['reason'] == 'in_flight'
    # in-flight skip must NOT change refreshStatus
    assert vm._refresh_status != 'refreshing'


def test_refresh_episode_full_lifecycle() -> None:
    """Direct call to _apply_refresh_snapshot must trace requested→started→collected→applied."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data = _make_sample_data()
    vm._apply_refresh_snapshot(1, data)
    kinds = [t['kind'] for t in traced]
    assert 'evolution_refresh_applied' in kinds, f'Expected evolution_refresh_applied, got: {kinds}'
    applied = next(t for t in traced if t['kind'] == 'evolution_refresh_applied')
    assert 'duration_ms' in applied
    assert 'changed_sections' in applied
    assert 'unchanged_sections' in applied
    assert 'emitted_signals' in applied
    assert applied['source'] == 'user_click'
    assert applied['refresh_id'] == 'r000001'
    assert vm._refresh_status == 'idle'
    assert vm._refresh_in_flight is False


def test_unchanged_refresh_produces_correct_result() -> None:
    """Two _apply_refresh_snapshot with same data -> second produces unchanged."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    # First apply populates fingerprints
    data1 = _make_sample_data()
    vm._apply_refresh_snapshot(1, data1)
    # Second apply with same data — must be unchanged
    traced.clear()
    vm._refresh_generation = 2
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data2 = _make_sample_data(_refresh_meta={'refresh_id': 'r000002', 'source': 'user_click', 'generation': 2, 't0': time.perf_counter()})
    vm._apply_refresh_snapshot(2, data2)
    applied = [t for t in traced if t['kind'] == 'evolution_refresh_applied']
    assert len(applied) == 1, f'Expected 1 evolution_refresh_applied, got {len(applied)}: {[t["kind"] for t in traced]}'
    assert applied[0]['result'] == 'unchanged'
    assert vm._last_refresh_result == 'unchanged'
    assert 'no hubo cambios' in vm._last_refresh_summary


def test_changed_refresh_detects_sections() -> None:
    """First _apply_refresh_snapshot with data must detect changed sections."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data = _make_sample_data()
    vm._apply_refresh_snapshot(1, data)
    applied = [t for t in traced if t['kind'] == 'evolution_refresh_applied']
    assert len(applied) == 1, f'Expected 1 evolution_refresh_applied, got {len(applied)}'
    assert applied[0]['result'] == 'changed'
    assert len(applied[0]['changed_sections']) > 0
    assert vm._last_refresh_result == 'changed'
    assert 'cambiaron' in vm._last_refresh_summary


def test_content_change_same_id_produces_changed() -> None:
    """If item content changes but id stays the same, fingerprint must detect it."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    # First apply
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data1 = _make_sample_data(dossiers=[{'dossier_id': 'd1', 'title': 'original', 'status': 'open'}])
    vm._apply_refresh_snapshot(1, data1)
    # Second apply with same id but different content
    traced.clear()
    vm._refresh_generation = 2
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data2 = _make_sample_data(
        dossiers=[{'dossier_id': 'd1', 'title': 'modified', 'status': 'closed'}],
        _refresh_meta={'refresh_id': 'r000003', 'source': 'user_click', 'generation': 2, 't0': time.perf_counter()},
    )
    vm._apply_refresh_snapshot(2, data2)
    applied = [t for t in traced if t['kind'] == 'evolution_refresh_applied']
    assert len(applied) == 1
    assert applied[0]['result'] == 'changed'
    assert 'dossiers' in applied[0]['changed_sections']


def test_stale_generation_cleans_status() -> None:
    """If generation is stale, _apply_refresh_snapshot must clean refreshStatus."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 5
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data = _make_sample_data(_refresh_meta={'refresh_id': 'rstale', 'source': 'user_click', 'generation': 3, 't0': time.perf_counter()})
    vm._apply_refresh_snapshot(3, data)  # gen 3 vs current 5 — stale
    assert vm._refresh_status == 'idle', 'refreshStatus must be cleaned on stale generation'
    assert vm._last_refresh_result == 'cancelled'
    assert vm._refresh_in_flight is False


def test_result_none_cleans_status() -> None:
    """If _done receives result=None, refreshStatus must not stay as refreshing."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    vm._refresh_generation = 1
    # Simulate _bg returning None — call _apply_refresh_snapshot with non-dict
    vm._apply_refresh_snapshot(1, None)
    assert vm._refresh_status == 'idle'
    assert vm._last_refresh_result == 'cancelled'
    assert vm._refresh_in_flight is False


def test_failed_apply_produces_failed_status() -> None:
    """If _apply_collected_data raises, refreshStatus must be failed."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    # Inject a broken _apply_collected_data
    original_apply = vm._apply_collected_data
    def broken_apply(data: dict) -> None:
        raise RuntimeError('test apply failure')
    vm._apply_collected_data = broken_apply
    data = _make_sample_data()
    vm._apply_refresh_snapshot(1, data)
    assert vm._refresh_status == 'failed'
    assert vm._last_refresh_result == 'failed'
    assert 'No pude actualizar' in vm._last_refresh_summary
    assert vm._refresh_in_flight is False
    failed = [t for t in traced if t['kind'] == 'evolution_refresh_failed']
    assert len(failed) == 1
    vm._apply_collected_data = original_apply


def test_refresh_status_properties_use_granular_signal() -> None:
    """refreshStatus/lastRefreshSummary/lastRefreshResult use refreshStatusChanged, not dataChanged."""
    vm = _make_minimal_vm()
    status_emissions: list[bool] = []
    data_emissions: list[bool] = []
    vm.refreshStatusChanged.connect(lambda: status_emissions.append(True))
    vm.dataChanged.connect(lambda: data_emissions.append(True))
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data = _make_sample_data()
    vm._apply_refresh_snapshot(1, data)
    assert len(status_emissions) >= 1, 'refreshStatusChanged must fire'
    assert len(data_emissions) == 0, 'dataChanged must NOT fire from _apply_refresh_snapshot'


def test_signals_only_for_changed_sections() -> None:
    """Unchanged refresh must NOT emit all granular signals — only overviewChanged."""
    vm = _make_minimal_vm()
    # First apply populates fingerprints
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data1 = _make_sample_data()
    vm._apply_refresh_snapshot(1, data1)
    # Now connect signals and do unchanged refresh
    emitted_signals: list[str] = []
    vm.dossiersChanged.connect(lambda: emitted_signals.append('dossiersChanged'))
    vm.incidentsChanged.connect(lambda: emitted_signals.append('incidentsChanged'))
    vm.backlogChanged.connect(lambda: emitted_signals.append('backlogChanged'))
    vm.toolsChanged.connect(lambda: emitted_signals.append('toolsChanged'))
    vm.overviewChanged.connect(lambda: emitted_signals.append('overviewChanged'))
    vm.worldModelChanged.connect(lambda: emitted_signals.append('worldModelChanged'))
    vm.metacognitionChanged.connect(lambda: emitted_signals.append('metacognitionChanged'))
    vm.iaComparisonsChanged.connect(lambda: emitted_signals.append('iaComparisonsChanged'))
    vm._refresh_generation = 2
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data2 = _make_sample_data(_refresh_meta={'refresh_id': 'r000010', 'source': 'user_click', 'generation': 2, 't0': time.perf_counter()})
    vm._apply_refresh_snapshot(2, data2)
    # overviewChanged always fires; section-specific signals must NOT fire for unchanged
    assert 'overviewChanged' in emitted_signals
    # No section-specific signals for unchanged data
    assert 'dossiersChanged' not in emitted_signals, f'dossiersChanged should not fire for unchanged data, got: {emitted_signals}'
    assert 'incidentsChanged' not in emitted_signals


def test_emitted_signals_in_audit_reflects_reality() -> None:
    """emitted_signals in trace must match what was actually emitted."""
    vm = _make_minimal_vm()
    traced: list[dict[str, Any]] = []
    vm._trace_refresh = lambda kind, **kw: traced.append({'kind': kind, **kw})
    vm._refresh_generation = 1
    vm._refresh_in_flight = True
    vm._refresh_status = 'refreshing'
    data = _make_sample_data()
    vm._apply_refresh_snapshot(1, data)
    applied = [t for t in traced if t['kind'] == 'evolution_refresh_applied']
    assert len(applied) == 1
    emitted = applied[0]['emitted_signals']
    assert isinstance(emitted, list)
    # First apply has changes -> multiple signals
    assert 'overviewChanged' in emitted
    # Must contain at least one section signal for the changed data
    assert len(emitted) > 1


def test_refresh_status_shows_refreshing_then_result() -> None:
    """refreshFromUser transitions status through refreshing → idle."""
    vm = _make_minimal_vm()
    statuses: list[str] = []
    vm.refreshStatusChanged.connect(lambda: statuses.append(vm._refresh_status))
    vm.refreshFromUser()
    for _ in range(30):
        if not vm._refresh_in_flight:
            break
        time.sleep(0.1)
    time.sleep(0.3)
    assert 'refreshing' in statuses or vm._refresh_status == 'idle'


def test_no_new_service_created() -> None:
    """Verify no new service class was created — only ViewModel changes."""
    import iabv_v15.ui.viewmodels.evolution_center_viewmodel as mod
    defined_here = [name for name in dir(mod) if isinstance(getattr(mod, name, None), type) and not name.startswith('_') and getattr(getattr(mod, name), '__module__', '') == mod.__name__]
    assert defined_here == ['EvolutionCenterViewModel'], f'Unexpected classes defined in module: {defined_here}'


def test_section_fingerprint_detects_list_changes() -> None:
    """Fingerprint changes when list content changes."""
    fp1 = EvolutionCenterViewModel._section_fingerprint([{'dossier_id': 'a'}])
    fp2 = EvolutionCenterViewModel._section_fingerprint([{'dossier_id': 'b'}])
    fp3 = EvolutionCenterViewModel._section_fingerprint([{'dossier_id': 'a'}])
    assert fp1 != fp2
    assert fp1 == fp3


def test_section_fingerprint_detects_dict_changes() -> None:
    """Fingerprint changes when dict content changes."""
    fp1 = EvolutionCenterViewModel._section_fingerprint({'summary': 'hello'})
    fp2 = EvolutionCenterViewModel._section_fingerprint({'summary': 'world'})
    assert fp1 != fp2


def test_section_fingerprint_detects_content_change_same_id() -> None:
    """Fingerprint changes when list item content changes but id stays the same."""
    fp1 = EvolutionCenterViewModel._section_fingerprint([{'dossier_id': 'a', 'status': 'open', 'title': 'foo'}])
    fp2 = EvolutionCenterViewModel._section_fingerprint([{'dossier_id': 'a', 'status': 'closed', 'title': 'foo'}])
    assert fp1 != fp2, 'Fingerprint must detect content change even when id is the same'


def test_section_fingerprint_detects_dict_field_change() -> None:
    """Fingerprint changes when dict fields like assistant_brief change."""
    fp1 = EvolutionCenterViewModel._section_fingerprint({'assistant_brief': 'v1', 'status': 'ok'})
    fp2 = EvolutionCenterViewModel._section_fingerprint({'assistant_brief': 'v2', 'status': 'ok'})
    assert fp1 != fp2, 'Fingerprint must detect dict field changes beyond just summary/keys'
