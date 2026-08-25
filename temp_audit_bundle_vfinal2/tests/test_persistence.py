from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import CapturedStep, SessionArtifact
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.screenshot_store import ScreenshotStore
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.session_state_store import SessionStateStore
from iabv_v15.infra.persistence.snapshot_version_manager import SnapshotVersionManager
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
from iabv_v15.services.training.payload_archive_service import PayloadArchiveService
from iabv_v15.services.training.training_orchestrator import TrainingOrchestrator


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_episode_repository_and_artifacts_roundtrip() -> None:
    root = _workspace('persistence')
    db = AppDatabase(str(root / 'app.sqlite'))
    repo = EpisodeRepository(str(root / 'episodes'), db)
    artifact_repo = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    manifest = repo.create_episode('Test Capture', tags=['smoke'])

    step = CapturedStep(episode_id=manifest.episode_id, action_type='click', target='submit')
    repo.save_step(manifest.episode_id, step)

    artifact = SessionArtifact(
        episode_id=manifest.episode_id,
        kind='network_exchange',
        path=f'{manifest.episode_id}/api/exchange.json',
        metadata={'capture_channel': 'api', 'redacted': True, 'redacted_fields': 2, 'site_id': 'generic_web'},
    )
    saved_artifact = artifact_repo.save(artifact, payload={'status': 200, 'url': 'https://example.com'})

    loaded = repo.load_episode(manifest.episode_id)
    loaded_artifacts = artifact_repo.list_for_episode(manifest.episode_id)
    assert len(loaded) == 1
    assert loaded[0].target == 'submit'
    assert len(loaded_artifacts) == 1
    assert Path(saved_artifact.path).exists()
    assert loaded_artifacts[0].kind == 'network_exchange'

    storage = ArtifactStorage(str(root / 'shots'))
    screenshots = ScreenshotStore(storage)
    saved = screenshots.save_bytes(manifest.episode_id, 'frame.png', b'png-bytes')
    assert Path(saved).exists()

def test_training_payload_includes_browser_artifacts() -> None:
    root = _workspace('payload')
    db = AppDatabase(str(root / 'app.sqlite'))
    episode_repo = EpisodeRepository(str(root / 'episodes'), db)
    knowledge_repo = KnowledgeRepository(db)
    run_repo = RunRepository(db)
    artifact_repo = SessionArtifactRepository(db, ArtifactStorage(str(root / 'artifacts')))
    manifest = episode_repo.create_episode('Teach Session', tags=['browser_teach'])
    episode_repo.save_step(
        manifest.episode_id,
        CapturedStep(
            episode_id=manifest.episode_id,
            action_type='input',
            target='#password',
            metadata={'sensitive': True, 'masked_value': '[REDACTED]', 'vault_ref': {'ref_id': '123'}},
        ),
    )
    artifact_repo.save(
        SessionArtifact(
            episode_id=manifest.episode_id,
            kind='dom_snapshot',
            path=f'{manifest.episode_id}/background/dom.json',
            metadata={'capture_channel': 'background', 'redacted': True, 'site_id': 'generic_web'},
        ),
        payload={'url': 'https://example.com', 'form_fields': []},
    )

    manager = SnapshotVersionManager(str(root / 'payloads'))
    archive = PayloadArchiveService(str(root / 'payloads'), manager)
    orchestrator = TrainingOrchestrator(
        workspace_root=str(root),
        episode_repository=episode_repo,
        knowledge_repository=knowledge_repo,
        run_repository=run_repo,
        archive_service=archive,
        artifact_repository=artifact_repo,
    )
    payload = orchestrator.prepare_payload()
    assert payload.artifacts
    assert payload.capture_channels[0].value == 'background'
    assert payload.redaction_summary.redacted_steps == 1
    saved_path = archive.archive(payload)
    assert Path(saved_path).exists()
    snapshot = manager.load_snapshot('training_payload_v2.json')
    assert 'artifacts' in snapshot['spec']['fields']

def test_session_state_store_backup_and_snapshot_manager() -> None:
    root = _workspace('state')
    store = SessionStateStore()
    state_path = root / 'state.json'
    store.save_json_atomic({'session': 'ok'}, str(state_path))
    backup = store.save_with_backup(str(state_path), {'session': 'updated'})
    assert backup is not None
    assert state_path.exists()
    assert store.load_json(str(state_path))['session'] == 'updated'

    manager = SnapshotVersionManager(str(root / 'payloads'))
    saved_path = manager.save_snapshot_atomic('payload.json', {'spec': {'version': 2}, 'payload': {'x': 1}})
    assert Path(saved_path).exists()
    snapshot = manager.load_snapshot('payload.json')
    migrated = manager.migrate_snapshot(snapshot, {'version': 2, 'extra': True})
    assert migrated['meta']['compatibility'] == 'adaptable'

def test_browser_session_controller_raises_before_start() -> None:
    controller = BrowserSessionController(user_data_dir='profile', storage_state_path='state.json', headless=True)
    with pytest.raises(RuntimeError):
        controller.new_page()


def test_browser_session_controller_uses_maximized_launch_args() -> None:
    controller = BrowserSessionController(user_data_dir='profile', storage_state_path='state.json', headless=True)
    assert '--start-maximized' in controller.launch_args
