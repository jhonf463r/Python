from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    BrowserObservationBundle,
    CaptureChannel,
    CapturedStep,
    RedactionSummary,
    SessionArtifact,
    SiteSessionResult,
)
from iabv_v15.infra.config import load_app_config
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.capture.training_profile_manager import TrainingProfileManager
from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector
from iabv_v15.services.evolution.session_health_service import SessionHealthService
from iabv_v15.services.evolution.user_clue_service import UserClueService
from iabv_v15.ui.viewmodels.capture_studio_viewmodel import CaptureStudioViewModel


class FakeTeachSessionService:
    def __init__(self, episode_repository: EpisodeRepository):
        self.episode_repository = episode_repository
        self.redaction_summary = RedactionSummary(redacted_steps=1, redacted_network_fields=2, stored_secrets=1)
        self._episode_id = ''
        self._url = 'about:blank'

    def start_session(self, *, title, url, profile_config, site_policy, tags=None):
        episode = self.episode_repository.create_episode(title=title, tags=tags or [], notes=f'teach_url={url}')
        self._episode_id = episode.episode_id
        self._url = url
        return episode, SiteSessionResult(site_id=site_policy.site_id, authenticated=False, requires_manual_login=True, reason='Login manual pendiente.')

    def record_step(self, *, action_type, target=None, text_value=None, metadata=None, capture_screenshot=True):
        step = CapturedStep(
            episode_id=self._episode_id,
            action_type=action_type,
            target=target,
            text_value=text_value,
            metadata=metadata or {},
        )
        return self.episode_repository.save_step(self._episode_id, step)

    def stop_session(self):
        self.episode_repository.save_step(
            self._episode_id,
            CapturedStep(
                episode_id=self._episode_id,
                action_type='click',
                target='#submit-login',
                metadata={
                    'selector': '#submit-login',
                    'element_role': 'button',
                    'button_text': 'Ingresar',
                    'capture_channel': CaptureChannel.VISIBLE.value,
                },
            ),
        )
        bundle = BrowserObservationBundle(
            episode_id=self._episode_id,
            url=self._url,
            capture_channels=[CaptureChannel.VISIBLE, CaptureChannel.BACKGROUND],
        )
        return bundle, SiteSessionResult(site_id='generic_web', authenticated=True, requires_manual_login=False, reason='Storage state guardado.')


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_viewmodel(root: Path) -> CaptureStudioViewModel:
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes)
    return CaptureStudioViewModel(
        config=config,
        episode_repository=episodes,
        artifact_repository=artifacts,
        site_policy_registry=registry,
        profile_manager=profiles,
        secret_vault=SecretVault(),
        browser_teach_session_service=teach_service,
        browser_learning_assembler=BrowserLearningAssembler(),
        hidden_incident_repository=hidden_incidents,
        user_clue_repository=user_clues,
        runtime_signal_collector=RuntimeSignalCollector(),
        hidden_incident_detector=HiddenIncidentDetector(),
        session_health_service=SessionHealthService(),
        user_clue_service=UserClueService(clue_repository=user_clues, incident_repository=hidden_incidents),
    )


def test_capture_studio_history_actions_support_replay_and_delete() -> None:
    root = _workspace('capture_history_actions')
    viewmodel = _build_viewmodel(root)

    viewmodel.startTeaching(
        'Login guiado',
        'Wplay',
        'https://wplay.co',
        'Iniciar sesion y llegar al panel principal.',
        'Panel principal visible.',
        'No compartir secretos.',
        True,
        True,
        False,
    )
    episode_id = viewmodel.activeEpisodeId
    viewmodel.stopTeaching()

    assert viewmodel.teachingHistory
    assert viewmodel.replaySteps

    viewmodel.showReplayGuided(episode_id)

    assert viewmodel.selectedTeachingHistory['episode_id'] == episode_id
    assert 'Replay guiado cargado' in viewmodel.teachingStatus
    assert str(len(viewmodel.replaySteps)) in viewmodel.teachingSummary

    viewmodel.deleteTeachingEpisode(episode_id)

    assert all(item['episode_id'] != episode_id for item in viewmodel.teachingHistory)
    assert viewmodel.episode_repository.load_episode(episode_id) == []
    assert viewmodel.artifact_repository.list_for_episode(episode_id) == []
    assert not (Path(viewmodel.config.episodes_dir) / episode_id).exists()


def test_capture_studio_history_marks_partial_recovery_and_builds_replay_from_artifacts() -> None:
    root = _workspace('capture_history_partial')
    viewmodel = _build_viewmodel(root)

    episode = viewmodel.episode_repository.create_episode(
        title='Sesion parcial',
        tags=['browser_teach', 'site:generic_web'],
        notes='teach_url=https://example.com',
    )
    viewmodel.artifact_repository.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='teaching_brief',
            path=f'{episode.episode_id}/brief/teaching_brief.json',
            metadata={'capture_channel': CaptureChannel.BACKGROUND.value, 'redacted': True},
        ),
        payload={'target_label': 'Portal', 'objective': 'Entrar y validar panel', 'site_id': 'generic_web'},
    )
    viewmodel.artifact_repository.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='dom_snapshot',
            path=f'{episode.episode_id}/background/dom.json',
            metadata={'capture_channel': CaptureChannel.BACKGROUND.value, 'redacted': True},
        ),
        payload={'title': 'Panel', 'visible_text_excerpt': 'Contenido del panel principal'},
    )
    viewmodel.artifact_repository.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='network_exchange',
            path=f'{episode.episode_id}/api/request.json',
            metadata={'capture_channel': CaptureChannel.API.value, 'redacted': True},
        ),
        payload={'method': 'POST', 'url': 'https://example.com/api/login', 'status_code': 200},
    )

    viewmodel.refresh()
    viewmodel.showReplayGuided(episode.episode_id)

    assert viewmodel.selectedTeachingHistory['episode_id'] == episode.episode_id
    assert viewmodel.selectedTeachingHistory['status'] == 'partial_recovery'
    assert viewmodel.selectedTeachingHistory['has_recoverable_replay'] is True
    assert any(step['action_type'] == 'teaching_brief' for step in viewmodel.replaySteps)
    assert any(step['action_type'] == 'dom_snapshot' for step in viewmodel.replaySteps)
    assert any(step['action_type'] == 'network_exchange' for step in viewmodel.replaySteps)


def test_capture_studio_history_rebuilds_legacy_frame_fallback_login_replay() -> None:
    root = _workspace('capture_history_legacy_frame_replay')
    viewmodel = _build_viewmodel(root)

    episode = viewmodel.episode_repository.create_episode(
        title='Sesion login legacy',
        tags=['browser_teach', 'site:generic_web'],
        notes='teach_url=https://example.com/login',
    )
    frame_reference = 'https://example.com/frame#%7B%22requestType%22%3A%22LoginAndGetTempToken%22%2C%22requestId%22%3A%22legacy-1%22%2C%22postParams%22%3A%7B%22username%22%3A%22demo%40example.com%22%2C%22password%22%3A%22Secreto123%22%7D%7D'
    viewmodel.episode_repository.save_step(
        episode.episode_id,
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='frame_fallback',
            target='frame:loginandgettemptoken',
            metadata={
                'selector': 'frame:loginandgettemptoken',
                'capture_channel': CaptureChannel.VISIBLE.value,
                'capture_source': 'frame_fallback',
                'frame_url': frame_reference,
                'frame_request_type': 'LoginAndGetTempToken',
                'textPreview': 'Login detectado en frame embebido.',
            },
        ),
    )

    viewmodel.refresh()
    viewmodel.showReplayGuided(episode.episode_id)

    action_types = [step['action_type'] for step in viewmodel.replaySteps]
    serialized = str(viewmodel.replaySteps)
    assert action_types[:4] == ['input', 'input', 'keydown', 'submit']
    assert 'demo@example.com' not in serialized
    assert 'Secreto123' not in serialized
    assert any(step['element_role'] == 'password_input' and step['sensitive'] for step in viewmodel.replaySteps)
    assert any(step['action_type'] == 'keydown' and step['text'] == 'Enter' for step in viewmodel.replaySteps)
    assert all(step['learning_relevant'] for step in viewmodel.replaySteps[:4])
    assert all(step['learning_priority'] > 0 for step in viewmodel.replaySteps[:4])
    assert any('Aprender' not in (step.get('learning_reason') or '') or step['learning_reason'] for step in viewmodel.replaySteps[:4])
