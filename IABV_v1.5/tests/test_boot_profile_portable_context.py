"""Focused tests for BootProfileStore -> PortableContextService cable.

Covers:
- _boot_profile_snapshot with no store (store is None)
- _boot_profile_snapshot with no environment_id
- _boot_profile_snapshot with no data (store exists, no JSONL entries)
- _boot_profile_snapshot with real data
- _boot_profile_section renders correct portable section for each status
- build_package metadata includes boot_profile dict
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.evolution.boot_profile_store import BootProfileStore
from iabv_v15.services.evolution.portable_context_service import PortableContextService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_service(root: Path, *, store: BootProfileStore | None = None, env_id: str = '') -> PortableContextService:
    storage = ArtifactStorage(str(root / 'data' / 'evolution'))
    env_svc = _FakeEnvService(env_id) if env_id else None
    svc = PortableContextService(
        workspace_root=str(root),
        storage=storage,
        environment_self_awareness_service=env_svc,
    )
    svc.boot_profile_store = store
    return svc


class _FakeEnvService:
    """Minimal stub that returns a fixed environment_id."""

    def __init__(self, environment_id: str) -> None:
        self._env_id = environment_id

    def current_model(self) -> '_FakeEnvModel':
        return _FakeEnvModel(self._env_id)


class _FakeEnvModel:
    def __init__(self, environment_id: str) -> None:
        self.environment_id = environment_id
        self.scan_status = 'complete'
        self.unresolved_fields: list[str] = []
        self.known_environment = True


def _sample_timeline() -> list[dict[str, Any]]:
    return [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 96.0},
        {'phase': 'wire_services_start', 't_ms_from_start': 25.0, 'rss_mb': 97.0},
        {'phase': 'wire_services_done', 't_ms_from_start': 18170.0, 'rss_mb': 112.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': 22000.0, 'rss_mb': 115.0},
        {'phase': 'page_loader_ready', 't_ms_from_start': 24500.0, 'rss_mb': 118.0},
    ]


# --------------------------------------------------------------------------- #
# _boot_profile_snapshot
# --------------------------------------------------------------------------- #


def test_snapshot_no_store() -> None:
    root = _workspace('bp_no_store')
    svc = _make_service(root)
    snap = svc._boot_profile_snapshot()
    assert snap['status'] == 'no_store'


def test_snapshot_no_environment_id() -> None:
    root = _workspace('bp_no_env')
    store = BootProfileStore(data_root=root / 'data')
    svc = _make_service(root, store=store, env_id='')
    snap = svc._boot_profile_snapshot()
    assert snap['status'] == 'no_environment_id'


def test_snapshot_no_data() -> None:
    root = _workspace('bp_no_data')
    store = BootProfileStore(data_root=root / 'data')
    svc = _make_service(root, store=store, env_id='test-env-001')
    snap = svc._boot_profile_snapshot()
    assert snap['status'] == 'no_data'
    assert snap['boot_count'] == 0


def test_snapshot_with_data() -> None:
    root = _workspace('bp_with_data')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-002'
    store.record_boot_session(
        environment_id=env_id,
        timeline_events=_sample_timeline(),
        metadata={'test': True},
    )
    store.record_boot_session(
        environment_id=env_id,
        timeline_events=_sample_timeline(),
        metadata={'test': True},
    )
    svc = _make_service(root, store=store, env_id=env_id)
    snap = svc._boot_profile_snapshot()
    assert snap['status'] == 'ok'
    assert snap['boot_count'] == 2
    assert snap['environment_id'] == env_id
    assert 'boot_duration' in snap
    assert snap['boot_duration']['avg_ms'] > 0
    assert snap['boot_duration']['median_ms'] > 0
    assert snap['boot_duration']['p95_ms'] > 0
    assert 'rss_peak' in snap
    assert snap['rss_peak']['max_mb'] > 0
    assert len(snap.get('slowest_phases', [])) > 0
    assert snap.get('first_seen', '') != ''
    assert snap.get('last_seen', '') != ''


# --------------------------------------------------------------------------- #
# _boot_profile_section
# --------------------------------------------------------------------------- #


def test_section_no_store() -> None:
    from iabv_v15.domain.models import utc_now
    root = _workspace('bp_sec_no_store')
    svc = _make_service(root)
    section = svc._boot_profile_section(status={'status': 'no_store'}, now=utc_now())
    assert section.section_id == 'boot_profile'
    assert 'no disponible' in section.summary.lower() or 'no disponible' in section.summary
    assert 'UNRESOLVED:boot_profile_store_missing' in section.unresolved_fields
    assert section.confidence == 0.0


def test_section_no_data() -> None:
    from iabv_v15.domain.models import utc_now
    root = _workspace('bp_sec_no_data')
    svc = _make_service(root)
    status = {'status': 'no_data', 'environment_id': 'env-x', 'boot_count': 0}
    section = svc._boot_profile_section(status=status, now=utc_now())
    assert section.section_id == 'boot_profile'
    assert 'sin datos' in section.summary.lower()
    assert 'UNRESOLVED:boot_profile_no_data' in section.unresolved_fields
    assert section.confidence == 0.0


def test_section_with_data() -> None:
    from iabv_v15.domain.models import utc_now
    root = _workspace('bp_sec_with_data')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-section'
    store.record_boot_session(
        environment_id=env_id,
        timeline_events=_sample_timeline(),
    )
    svc = _make_service(root, store=store, env_id=env_id)
    snap = svc._boot_profile_snapshot()
    section = svc._boot_profile_section(status=snap, now=utc_now())
    assert section.section_id == 'boot_profile'
    assert section.confidence == 0.85
    assert env_id in section.summary
    assert '1 boots' in section.summary
    assert len(section.items) >= 4
    labels = [item.get('label') for item in section.items]
    assert 'environment_id' in labels
    assert 'boot_count' in labels
    assert 'boot_duration' in labels
    assert 'rss_peak' in labels
    assert section.metadata.get('status') == 'ok'
    assert section.metadata.get('boot_count') == 1


# --------------------------------------------------------------------------- #
# metadata in build_package
# --------------------------------------------------------------------------- #


def test_metadata_includes_boot_profile() -> None:
    root = _workspace('bp_metadata')
    store = BootProfileStore(data_root=root / 'data')
    env_id = 'test-env-meta'
    store.record_boot_session(
        environment_id=env_id,
        timeline_events=_sample_timeline(),
    )
    svc = _make_service(root, store=store, env_id=env_id)
    package = svc.build_package()
    assert 'boot_profile' in package.metadata
    bp = package.metadata['boot_profile']
    assert bp.get('status') == 'ok'
    assert bp.get('boot_count') == 1

    section_ids = [s.section_id for s in package.sections]
    assert 'boot_profile' in section_ids
