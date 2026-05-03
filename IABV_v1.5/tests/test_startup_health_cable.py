"""Focalized tests for the cable ``startup_timeline.jsonl -> PortableContext + OSES``.

Cubre solo el slice agregado en este PR.  No probamos el sistema completo:
- :meth:`PortableContextService._startup_health_snapshot` y
  :meth:`PortableContextService._startup_health_section` con JSONL sintetico
- :meth:`OperationalSelfExaminationService._startup_health_findings` con
  escenarios saludable y degradado, y los thresholds publicos del modulo

Sin servicio nuevo, sin memoria paralela: leemos exactamente el JSONL que
``iabv_v15.infra.startup_timeline`` ya produce.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.operational_self_examination_service import (
    STARTUP_DEFERRED_MS_DEGRADED,
    STARTUP_INIT_MS_DEGRADED,
    STARTUP_RUN_TO_WINDOW_MS_DEGRADED,
    OperationalSelfExaminationService,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_timeline(root: Path, events: list[dict]) -> Path:
    log_dir = root / 'data' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / 'startup_timeline.jsonl'
    with path.open('w', encoding='utf-8') as fh:
        for evt in events:
            fh.write(json.dumps(evt))
            fh.write('\n')
    return path


def _make_portable_service(root: Path) -> PortableContextService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    # All other deps default to None — _startup_health_snapshot only needs
    # workspace_root.  This is intentional: the slice under test should be
    # decoupled from the rest of the package builder.
    return PortableContextService(
        workspace_root=str(root),
        storage=storage,
    )


def _make_oses(root: Path) -> OperationalSelfExaminationService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    return OperationalSelfExaminationService(
        workspace_root=str(root),
        storage=storage,
    )


# --------------------------------------------------------------------------- #
# PortableContextService._startup_health_snapshot
# --------------------------------------------------------------------------- #


def test_startup_health_snapshot_marks_unresolved_when_jsonl_missing() -> None:
    root = _workspace('startup_health_no_log')
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['status'] == 'no_log'
    assert 'UNRESOLVED:startup_timeline_missing' in snap['unresolved_fields']


def test_startup_health_snapshot_marks_unresolved_when_jsonl_empty() -> None:
    root = _workspace('startup_health_empty')
    log_dir = root / 'data' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / 'startup_timeline.jsonl').write_text('', encoding='utf-8')
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['status'] == 'no_data'
    assert 'UNRESOLVED:startup_timeline_empty' in snap['unresolved_fields']


def test_startup_health_snapshot_computes_intervals_from_last_run() -> None:
    root = _workspace('startup_health_analyzed')
    # First (older) run is short; second run is fully analyzable.  The snapshot
    # must pick the latest contiguous run only — the boundary is detected by a
    # non-monotonic ``t_ms_from_start`` jump.
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        # Boundary: new process restarts t0
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 2200.0, 'rss_mb': 130.0},
        {'phase': 'run_start', 't_ms_from_start': 2210.0, 'rss_mb': 130.0},
        {'phase': 'splash_visible', 't_ms_from_start': 2400.0, 'rss_mb': 135.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 5500.0, 'rss_mb': 220.0},
        {'phase': 'app_exec_about_to_start', 't_ms_from_start': 5510.0, 'rss_mb': 220.0},
        {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 5520.0, 'rss_mb': 220.0},
        {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 7800.0, 'rss_mb': 260.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['status'] == 'analyzed'
    assert snap['init_ms'] == 2200.0
    assert snap['run_to_window_ms'] == 3290.0
    assert snap['deferred_ms'] == 2280.0
    assert snap['rss_mb_max'] == 260.0
    assert 'main_window_shown' in snap['phases_seen']
    assert snap['unresolved_fields'] == []
    assert snap['recent_blockers'] == []


def test_startup_health_snapshot_flags_blockers_and_falls_back_to_init_done() -> None:
    root = _workspace('startup_health_degraded')
    # No ``run_start`` event — the snapshot must fall back to
    # ``bootstrap_init_done -> main_window_shown`` for run_to_window_ms.
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 9000.0, 'rss_mb': 200.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 22000.0, 'rss_mb': 350.0},
        {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 22100.0, 'rss_mb': 360.0},
        {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 28500.0, 'rss_mb': 410.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['status'] == 'analyzed'
    assert snap['init_ms'] == 9000.0
    assert snap['run_to_window_ms'] == 13000.0
    assert snap['deferred_ms'] == 6400.0
    blocker_phases = {b['phase'] for b in snap['recent_blockers']}
    assert {'bootstrap_init', 'run_to_main_window', 'deferred_post_window'} <= blocker_phases


def test_startup_health_section_summarises_from_snapshot() -> None:
    root = _workspace('startup_health_section')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1200.0, 'rss_mb': 110.0},
        {'phase': 'run_start', 't_ms_from_start': 1210.0, 'rss_mb': 110.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 4800.0, 'rss_mb': 240.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    from datetime import datetime, timezone

    section = svc._startup_health_section(status=snap, now=datetime.now(timezone.utc))
    assert section.section_id == 'startup_health'
    assert section.source_kind == 'startup_timeline_jsonl'
    assert section.confidence == 0.85
    assert section.metadata['status'] == 'analyzed'
    assert section.metadata['init_ms'] == 1200.0
    assert section.metadata['run_to_window_ms'] == 3590.0
    assert any(item.get('phase') == 'bootstrap_init' for item in section.items)


def test_startup_health_section_marks_unresolved_when_no_log() -> None:
    root = _workspace('startup_health_section_no_log')
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    from datetime import datetime, timezone

    section = svc._startup_health_section(status=snap, now=datetime.now(timezone.utc))
    assert section.confidence == 0.0
    assert 'UNRESOLVED:startup_timeline_missing' in section.unresolved_fields


# --------------------------------------------------------------------------- #
# OperationalSelfExaminationService._startup_health_findings
# --------------------------------------------------------------------------- #


def test_oses_thresholds_are_module_constants() -> None:
    # Public, greppable knobs requested by the user.
    assert STARTUP_INIT_MS_DEGRADED == 4000.0
    assert STARTUP_RUN_TO_WINDOW_MS_DEGRADED == 8000.0
    assert STARTUP_DEFERRED_MS_DEGRADED == 5000.0


def test_oses_startup_health_findings_returns_empty_when_no_log() -> None:
    root = _workspace('oses_startup_no_log')
    oses = _make_oses(root)
    assert oses._startup_health_findings() == []


def test_oses_startup_health_findings_returns_empty_when_healthy() -> None:
    root = _workspace('oses_startup_healthy')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 110.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 110.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 4500.0, 'rss_mb': 170.0},
        {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 4600.0, 'rss_mb': 170.0},
        {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 6800.0, 'rss_mb': 200.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    assert oses._startup_health_findings() == []


def test_oses_startup_health_findings_emits_per_threshold_crossed() -> None:
    root = _workspace('oses_startup_degraded')
    # init=9000ms (>2x init threshold), run_to_window=13000ms (degraded),
    # deferred=6400ms (degraded), RSS growth 320MB (>150MB threshold).
    # Four findings expected: 3 degradation + 1 memory_spike.
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 9000.0, 'rss_mb': 200.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 22000.0, 'rss_mb': 350.0},
        {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 22100.0, 'rss_mb': 360.0},
        {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 28500.0, 'rss_mb': 410.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    assert len(findings) == 4
    categories = {f.category for f in findings}
    assert categories == {'startup_degradation', 'startup_memory_spike'}
    degradation_phases = {f.metadata['phase'] for f in findings if f.category == 'startup_degradation'}
    assert degradation_phases == {'bootstrap_init', 'run_to_main_window', 'deferred_post_window'}
    init_finding = next(f for f in findings if f.metadata['phase'] == 'bootstrap_init')
    # init_ms 9000 > 2 * threshold (4000), should be HIGH severity.
    assert init_finding.severity.value == 'high'
    assert 'data/logs/startup_timeline.jsonl' in init_finding.source_refs


def test_oses_startup_health_findings_emits_only_for_crossed_thresholds() -> None:
    root = _workspace('oses_startup_partial_degraded')
    # Only run_to_window crosses; init and deferred are healthy.
    # RSS growth = 220MB (300-80) > 150MB threshold, so memory_spike also fires.
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1200.0, 'rss_mb': 110.0},
        {'phase': 'run_start', 't_ms_from_start': 1210.0, 'rss_mb': 110.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 12000.0, 'rss_mb': 200.0},
        {'phase': 'deferred_post_window_setup_start', 't_ms_from_start': 12100.0, 'rss_mb': 200.0},
        {'phase': 'deferred_post_window_setup_done', 't_ms_from_start': 14000.0, 'rss_mb': 210.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    assert len(findings) == 1
    assert findings[0].metadata['phase'] == 'run_to_main_window'
    assert findings[0].metadata['observed_ms'] == 10790.0


# --------------------------------------------------------------------------- #
# False-ready detection (cable: false-ready -> PortableContext + OSES)
# --------------------------------------------------------------------------- #
# These tests cover the slice that catches the live-audit bug: ``splash_set_ready``
# being emitted before the QML ``mainShellLoader`` actually instantiated the
# real shell.  The detection lives entirely on top of ``startup_timeline.jsonl``
# and the existing PortableContext/OSES surfaces — no new service, no parallel
# memory.


def test_startup_health_snapshot_detects_false_ready_when_splash_before_shell_ready() -> None:
    """splash_set_ready < shell_loader_ready is dishonest; snapshot must flag it."""
    root = _workspace('startup_false_ready_order')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 150.0},
        # splash declared ready BEFORE shell_loader_ready — dishonest
        {'phase': 'splash_set_ready', 't_ms_from_start': 3010.0, 'rss_mb': 150.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': 4200.0, 'rss_mb': 240.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 41000.0, 'rss_mb': 320.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['false_ready_detected'] is True
    assert 'splash_set_ready_before_shell_loader_ready' in snap['false_ready_reasons']
    blocker_phases = {b.get('phase') for b in snap['recent_blockers']}
    assert 'startup_false_ready' in blocker_phases


def test_startup_health_snapshot_detects_false_ready_when_no_shell_loader_ready() -> None:
    """splash declared ready but neither shell_loader_ready nor fallback ever fired."""
    root = _workspace('startup_false_ready_missing_shell')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1200.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1210.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 2500.0, 'rss_mb': 150.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 2900.0, 'rss_mb': 220.0},
        # splash_set_ready arrived but the shell loader signal never did
        {'phase': 'splash_set_ready', 't_ms_from_start': 3000.0, 'rss_mb': 220.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['false_ready_detected'] is True
    assert 'splash_set_ready_without_shell_loader_ready' in snap['false_ready_reasons']


def test_startup_health_snapshot_flags_fallback_as_dishonest() -> None:
    """If the fallback fired, splash never received the honest QML signal."""
    root = _workspace('startup_false_ready_fallback')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1200.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1210.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 2500.0, 'rss_mb': 150.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 2900.0, 'rss_mb': 220.0},
        {'phase': 'shell_loader_ready_fallback', 't_ms_from_start': 47500.0, 'rss_mb': 380.0},
        {'phase': 'splash_set_ready', 't_ms_from_start': 47510.0, 'rss_mb': 380.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['false_ready_detected'] is True
    assert 'shell_loader_ready_fallback_used' in snap['false_ready_reasons']


def test_startup_health_snapshot_clean_when_shell_loader_ready_arrived_in_order() -> None:
    """Honest startup: shell_loader_ready -> splash_set_ready (populate_ui_done later)."""
    root = _workspace('startup_honest_ready')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 150.0},
        # Phased construction: shell ready -> splash -> populate_ui_done much later
        {'phase': 'shell_loader_ready', 't_ms_from_start': 4200.0, 'rss_mb': 240.0},
        {'phase': 'splash_set_ready', 't_ms_from_start': 4210.0, 'rss_mb': 240.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 120000.0, 'rss_mb': 320.0},
    ]
    _write_timeline(root, events)
    svc = _make_portable_service(root)
    snap = svc._startup_health_snapshot()
    assert snap['false_ready_detected'] is False
    assert snap['false_ready_reasons'] == []


def test_oses_emits_startup_false_ready_finding_when_order_violated() -> None:
    root = _workspace('oses_false_ready')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 150.0},
        # splash before shell_loader_ready — dishonest
        {'phase': 'splash_set_ready', 't_ms_from_start': 3010.0, 'rss_mb': 150.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': 4200.0, 'rss_mb': 240.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 41000.0, 'rss_mb': 320.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    false_ready = [f for f in findings if f.category == 'startup_false_ready']
    assert len(false_ready) == 1
    f = false_ready[0]
    assert 'splash_set_ready_before_shell_loader_ready' in f.metadata['reasons']
    assert f.severity.name == 'HIGH'


def test_oses_does_not_emit_false_ready_when_order_is_honest() -> None:
    root = _workspace('oses_honest_ready')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 150.0},
        # Phased: shell_loader_ready -> splash -> populate_ui_done much later
        {'phase': 'shell_loader_ready', 't_ms_from_start': 4200.0, 'rss_mb': 240.0},
        {'phase': 'splash_set_ready', 't_ms_from_start': 4210.0, 'rss_mb': 240.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 120000.0, 'rss_mb': 320.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    assert [f for f in findings if f.category == 'startup_false_ready'] == []


# --------------------------------------------------------------------------- #
# Phased architecture awareness (PR #307+)
# --------------------------------------------------------------------------- #

def test_oses_phased_populate_ui_no_false_positive() -> None:
    """When phased milestones exist, total span should NOT trigger a finding
    if synchronous phases are fast (even if total span > threshold)."""
    root = _workspace('oses_phased_no_false_positive')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 2200.0, 'rss_mb': 130.0},
        {'phase': 'run_start', 't_ms_from_start': 2210.0, 'rss_mb': 130.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 5500.0, 'rss_mb': 220.0},
        # Phased populate_ui: sync phases are fast
        {'phase': 'populate_ui_start', 't_ms_from_start': 6184.0, 'rss_mb': 250.0},
        {'phase': 'populate_ui_critical_done', 't_ms_from_start': 6270.0, 'rss_mb': 255.0},
        {'phase': 'populate_ui_deferred_1_start', 't_ms_from_start': 6272.0, 'rss_mb': 255.0},
        {'phase': 'populate_ui_deferred_1_done', 't_ms_from_start': 6337.0, 'rss_mb': 260.0},
        # Async gap (pageLoader incubation) — NOT main-thread blocking
        {'phase': 'populate_ui_done', 't_ms_from_start': 34900.0, 'rss_mb': 310.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    freeze_findings = [f for f in findings if f.category == 'startup_populate_ui_freeze']
    # Total span is 28716ms but sync phases are only ~153ms — no finding
    assert freeze_findings == []


def test_oses_phased_populate_ui_detects_slow_sync_phases() -> None:
    """When phased milestones exist but sync phases are slow, emit finding."""
    root = _workspace('oses_phased_slow_sync')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 2200.0, 'rss_mb': 130.0},
        {'phase': 'run_start', 't_ms_from_start': 2210.0, 'rss_mb': 130.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 5500.0, 'rss_mb': 220.0},
        # Phased populate_ui: phase 1 is slow!
        {'phase': 'populate_ui_start', 't_ms_from_start': 6000.0, 'rss_mb': 250.0},
        {'phase': 'populate_ui_critical_done', 't_ms_from_start': 9000.0, 'rss_mb': 280.0},
        {'phase': 'populate_ui_deferred_1_start', 't_ms_from_start': 9002.0, 'rss_mb': 280.0},
        {'phase': 'populate_ui_deferred_1_done', 't_ms_from_start': 12000.0, 'rss_mb': 320.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 40000.0, 'rss_mb': 350.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    freeze_findings = [f for f in findings if f.category == 'startup_populate_ui_freeze']
    assert len(freeze_findings) == 1
    f = freeze_findings[0]
    assert f.metadata['phase'] == 'populate_ui_phased'
    assert f.metadata['sync_blocking_ms'] == 5998.0  # (9000-6000) + (12000-9002)
    assert f.metadata['phase_1_ms'] == 3000.0
    assert f.metadata['deferred_1_ms'] == 2998.0


def test_oses_legacy_populate_ui_still_works() -> None:
    """Without phased milestones, legacy total-span detection still works."""
    root = _workspace('oses_legacy_populate')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 2200.0, 'rss_mb': 130.0},
        {'phase': 'run_start', 't_ms_from_start': 2210.0, 'rss_mb': 130.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 5500.0, 'rss_mb': 220.0},
        # Legacy: no phased milestones
        {'phase': 'populate_ui_start', 't_ms_from_start': 6000.0, 'rss_mb': 250.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 36000.0, 'rss_mb': 450.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    freeze_findings = [f for f in findings if f.category == 'startup_populate_ui_freeze']
    assert len(freeze_findings) == 1
    f = freeze_findings[0]
    assert f.metadata['phase'] == 'populate_ui'
    assert f.metadata['observed_ms'] == 30000.0


# --------------------------------------------------------------------------- #
# OSES → PlatformPendingQueue bridge
# --------------------------------------------------------------------------- #

def test_oses_bridge_creates_pending_task_from_critical_finding() -> None:
    """HIGH/CRITICAL findings in bridgeable categories create queue tasks."""
    root = _workspace('oses_bridge_critical')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 2200.0, 'rss_mb': 130.0},
        {'phase': 'run_start', 't_ms_from_start': 2210.0, 'rss_mb': 130.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 5500.0, 'rss_mb': 220.0},
        # Legacy populate_ui: slow (will trigger CRITICAL finding)
        {'phase': 'populate_ui_start', 't_ms_from_start': 6000.0, 'rss_mb': 250.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 36000.0, 'rss_mb': 450.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    # Build review triggers the bridge
    oses.build_review()

    from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
    queue = PlatformPendingQueue(evolution_dir=str(root / 'data' / 'evolution'))
    task = queue.get('oses_startup_populate_ui_freeze')
    assert task is not None
    assert task.priority == 'critical'
    assert task.category == 'oses_finding'
    assert task.status.value == 'PENDING'


def test_oses_bridge_skips_low_severity_findings() -> None:
    """MEDIUM/LOW findings should NOT create queue tasks."""
    root = _workspace('oses_bridge_low')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 110.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 110.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 4800.0, 'rss_mb': 200.0},
        # Healthy populate_ui — no finding
        {'phase': 'populate_ui_start', 't_ms_from_start': 4810.0, 'rss_mb': 200.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 5000.0, 'rss_mb': 210.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    oses.build_review()

    from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
    queue = PlatformPendingQueue(evolution_dir=str(root / 'data' / 'evolution'))
    task = queue.get('oses_startup_populate_ui_freeze')
    assert task is None


def test_oses_emits_false_ready_with_high_severity_for_fallback_path() -> None:
    root = _workspace('oses_fallback_path')
    events = [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
        {'phase': 'bootstrap_init_done', 't_ms_from_start': 1500.0, 'rss_mb': 100.0},
        {'phase': 'run_start', 't_ms_from_start': 1510.0, 'rss_mb': 100.0},
        {'phase': 'main_window_shown', 't_ms_from_start': 3000.0, 'rss_mb': 150.0},
        {'phase': 'populate_ui_done', 't_ms_from_start': 3500.0, 'rss_mb': 220.0},
        {'phase': 'shell_loader_ready_fallback', 't_ms_from_start': 47500.0, 'rss_mb': 380.0},
        {'phase': 'splash_set_ready', 't_ms_from_start': 47510.0, 'rss_mb': 380.0},
    ]
    _write_timeline(root, events)
    oses = _make_oses(root)
    findings = oses._startup_health_findings()
    false_ready = [f for f in findings if f.category == 'startup_false_ready']
    assert len(false_ready) == 1
    assert 'shell_loader_ready_fallback_used' in false_ready[0].metadata['reasons']
