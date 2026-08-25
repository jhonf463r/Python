"""Focused tests for OSES boot profile findings.

Covers:
- no finding when store is None
- no finding when boot_count < 2
- p95 boot alto finding when p95 exceeds threshold
- wiring_duration alto finding when avg wiring exceeds threshold
- boot regression finding when last boot >> rolling average
- no findings when all metrics are healthy
- thresholds are exported and tunable
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.boot_profile_store import BootProfileStore
from iabv_v15.services.evolution.operational_self_examination_service import (
    BOOT_P95_MS_DEGRADED,
    BOOT_REGRESSION_RATIO,
    BOOT_WIRING_AVG_MS_DEGRADED,
    OperationalSelfExaminationService,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


class _FakeEnvModel:
    def __init__(self, environment_id: str) -> None:
        self.environment_id = environment_id


class _FakeEnvService:
    def __init__(self, env_id: str) -> None:
        self._env_id = env_id

    def current_model(self) -> _FakeEnvModel:
        return _FakeEnvModel(self._env_id)


class _FakeWorldModelService:
    def __init__(self, env_id: str) -> None:
        self.environment_self_awareness_service = _FakeEnvService(env_id)


def _make_oses(root: Path, *, store: BootProfileStore | None = None, env_id: str = '') -> OperationalSelfExaminationService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    svc = OperationalSelfExaminationService(
        workspace_root=str(root),
        storage=storage,
        world_model_service=_FakeWorldModelService(env_id) if env_id else None,
    )
    svc.boot_profile_store = store
    return svc


def _fast_timeline(boot_ms: float = 5000.0, wiring_ms: float = 3000.0) -> list[dict[str, Any]]:
    """Healthy boot timeline."""
    return [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
        {'phase': 'wire_services_start', 't_ms_from_start': 25.0, 'rss_mb': 91.0},
        {'phase': 'wire_services_done', 't_ms_from_start': wiring_ms, 'rss_mb': 100.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': boot_ms - 500, 'rss_mb': 105.0},
        {'phase': 'page_loader_ready', 't_ms_from_start': boot_ms, 'rss_mb': 110.0},
    ]


def _slow_timeline(boot_ms: float = 35000.0, wiring_ms: float = 25000.0) -> list[dict[str, Any]]:
    """Degraded boot timeline."""
    return [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
        {'phase': 'wire_services_start', 't_ms_from_start': 25.0, 'rss_mb': 91.0},
        {'phase': 'wire_services_done', 't_ms_from_start': wiring_ms, 'rss_mb': 120.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': boot_ms - 500, 'rss_mb': 130.0},
        {'phase': 'page_loader_ready', 't_ms_from_start': boot_ms, 'rss_mb': 140.0},
    ]


# --------------------------------------------------------------------------- #
# No findings when store/data missing
# --------------------------------------------------------------------------- #


def test_no_findings_without_store() -> None:
    root = _workspace('oses_bp_no_store')
    svc = _make_oses(root, env_id='test-env')
    assert svc._boot_profile_findings() == []


def test_no_findings_without_env_id() -> None:
    root = _workspace('oses_bp_no_env')
    store = BootProfileStore(data_root=root / 'data')
    svc = _make_oses(root, store=store, env_id='')
    assert svc._boot_profile_findings() == []


def test_no_findings_with_single_boot() -> None:
    root = _workspace('oses_bp_single')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-single'
    store.record_boot_session(environment_id=env_id, timeline_events=_fast_timeline())
    svc = _make_oses(root, store=store, env_id=env_id)
    assert svc._boot_profile_findings() == []


# --------------------------------------------------------------------------- #
# Healthy boots — no findings
# --------------------------------------------------------------------------- #


def test_no_findings_when_healthy() -> None:
    root = _workspace('oses_bp_healthy')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-healthy'
    for _ in range(3):
        store.record_boot_session(environment_id=env_id, timeline_events=_fast_timeline())
    svc = _make_oses(root, store=store, env_id=env_id)
    findings = svc._boot_profile_findings()
    assert len(findings) == 0


# --------------------------------------------------------------------------- #
# p95 boot alto
# --------------------------------------------------------------------------- #


def test_p95_boot_alto_finding() -> None:
    root = _workspace('oses_bp_p95')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-p95'
    for _ in range(3):
        store.record_boot_session(
            environment_id=env_id,
            timeline_events=_slow_timeline(boot_ms=35000.0),
        )
    svc = _make_oses(root, store=store, env_id=env_id)
    findings = svc._boot_profile_findings()
    p95_findings = [f for f in findings if f.metadata.get('finding_type') == 'boot_p95_high']
    assert len(p95_findings) == 1
    f = p95_findings[0]
    assert f.category == 'boot_profile_degradation'
    assert f.confidence == 0.85
    assert f.metadata['p95_ms'] > BOOT_P95_MS_DEGRADED
    assert f.metadata['threshold_ms'] == BOOT_P95_MS_DEGRADED


# --------------------------------------------------------------------------- #
# wiring_duration alto
# --------------------------------------------------------------------------- #


def test_wiring_duration_alto_finding() -> None:
    root = _workspace('oses_bp_wiring')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-wiring'
    for _ in range(3):
        store.record_boot_session(
            environment_id=env_id,
            timeline_events=_slow_timeline(boot_ms=10000.0, wiring_ms=25000.0),
        )
    svc = _make_oses(root, store=store, env_id=env_id)
    findings = svc._boot_profile_findings()
    wiring_findings = [f for f in findings if f.metadata.get('finding_type') == 'wiring_duration_high']
    assert len(wiring_findings) == 1
    f = wiring_findings[0]
    assert f.category == 'boot_profile_degradation'
    assert f.metadata['wiring_avg_ms'] > BOOT_WIRING_AVG_MS_DEGRADED
    assert f.metadata['threshold_ms'] == BOOT_WIRING_AVG_MS_DEGRADED


# --------------------------------------------------------------------------- #
# Boot regression
# --------------------------------------------------------------------------- #


def test_boot_regression_finding() -> None:
    root = _workspace('oses_bp_regression')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-regression'
    # Record several fast boots then one slow boot
    for _ in range(4):
        store.record_boot_session(
            environment_id=env_id,
            timeline_events=_fast_timeline(boot_ms=5000.0),
        )
    store.record_boot_session(
        environment_id=env_id,
        timeline_events=_slow_timeline(boot_ms=15000.0),
    )
    svc = _make_oses(root, store=store, env_id=env_id)
    findings = svc._boot_profile_findings()
    regression_findings = [f for f in findings if f.metadata.get('finding_type') == 'boot_regression']
    assert len(regression_findings) == 1
    f = regression_findings[0]
    assert f.category == 'boot_profile_regression'
    assert f.metadata['ratio'] >= BOOT_REGRESSION_RATIO
    assert f.metadata['last_boot_ms'] > f.metadata['avg_ms']


def test_no_regression_when_last_boot_normal() -> None:
    root = _workspace('oses_bp_no_regression')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-no-regr'
    for _ in range(3):
        store.record_boot_session(
            environment_id=env_id,
            timeline_events=_fast_timeline(boot_ms=5000.0),
        )
    svc = _make_oses(root, store=store, env_id=env_id)
    findings = svc._boot_profile_findings()
    regression_findings = [f for f in findings if f.metadata.get('finding_type') == 'boot_regression']
    assert len(regression_findings) == 0


# --------------------------------------------------------------------------- #
# Thresholds are accessible module-level constants
# --------------------------------------------------------------------------- #


def test_thresholds_are_exported() -> None:
    assert BOOT_P95_MS_DEGRADED > 0
    assert BOOT_WIRING_AVG_MS_DEGRADED > 0
    assert BOOT_REGRESSION_RATIO > 1.0
