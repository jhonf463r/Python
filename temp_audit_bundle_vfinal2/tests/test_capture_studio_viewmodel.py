from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    BrowserObservationBundle,
    CaptureChannel,
    CapturedStep,
    HiddenIncident,
    PersistStrategy,
    RedactionSummary,
    SessionArtifact,
    SiteSessionResult,
)
from iabv_v15.infra.config import load_app_config
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler
from iabv_v15.services.capture.replay_annotation_service import ReplayAnnotationService
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService
from iabv_v15.services.capture.replay_learning_feedback_service import ReplayLearningFeedbackService
from iabv_v15.services.capture.replay_visual_assembler import ReplayVisualAssembler
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.capture.training_profile_manager import TrainingProfileManager
from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector
from iabv_v15.services.evolution.session_health_service import SessionHealthService
from iabv_v15.services.evolution.user_clue_service import UserClueService
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.ui.viewmodels.capture_studio_viewmodel import CaptureStudioViewModel


class FakeTeachSessionService:
    def __init__(self, episode_repository: EpisodeRepository, screenshots_dir: str):
        self.episode_repository = episode_repository
        self.screenshots_dir = Path(screenshots_dir)
        self.redaction_summary = RedactionSummary(redacted_steps=1, redacted_network_fields=2, stored_secrets=1)
        self._episode_id = ''
        self._url = 'about:blank'
        self.paused = False
        self.last_profile_config = None
        self.last_site_policy = None

    def start_session(self, *, title, url, profile_config, site_policy, tags=None):
        self.last_profile_config = profile_config
        self.last_site_policy = site_policy
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

    def pause_session(self):
        self.paused = True

    def resume_session(self):
        self.paused = False

    def stop_session(self):
        screenshot_dir = self.screenshots_dir / self._episode_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / 'visible_step.png'
        screenshot_path.write_bytes(bytes.fromhex('89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082'))
        self.episode_repository.save_step(
            self._episode_id,
            CapturedStep(
                episode_id=self._episode_id,
                action_type='click',
                target='#submit-login',
                text_value=None,
                screenshot_path=str(screenshot_path),
                metadata={
                    'selector': '#submit-login',
                    'element_role': 'button',
                    'button_text': 'Ingresar',
                    'capture_channel': CaptureChannel.VISIBLE.value,
                },
            ),
        )
        self.episode_repository.save_step(
            self._episode_id,
            CapturedStep(
                episode_id=self._episode_id,
                action_type='scroll',
                target='body',
                text_value=None,
                metadata={
                    'selector': 'body',
                    'element_role': 'document',
                    'scroll_y': 420,
                    'capture_channel': CaptureChannel.BACKGROUND.value,
                },
            ),
        )
        bundle = BrowserObservationBundle(
            episode_id=self._episode_id,
            url=self._url,
            capture_channels=[CaptureChannel.VISIBLE, CaptureChannel.BACKGROUND, CaptureChannel.API],
        )
        return bundle, SiteSessionResult(site_id='generic_web', authenticated=True, requires_manual_login=False, reason='Storage state guardado.')


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_capture_studio_viewmodel_accepts_adaptive_prefill_and_detects_site() -> None:
    root = _workspace('capture_studio_adaptive_prefill')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    viewmodel = CaptureStudioViewModel(
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
        interaction_learning_service=interaction_learning,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=tool_records),
    )

    viewmodel.applyAdaptiveTeachingPrefill(
        {
            'lesson_title': 'Wplay login corto',
            'target_label': 'Wplay',
            'start_url': 'https://www.wplay.co/login',
            'objective': 'Abrir Wplay e iniciar sesion.',
            'expected_outcome': 'Sesion iniciada y panel principal visible.',
            'notes': 'Corregir submit y vigilar bridge_lag.',
            'site_id': 'wplay',
        }
    )

    assert viewmodel.teachingDraftLessonTitle == 'Wplay login corto'
    assert viewmodel.teachingDraftTargetLabel == 'Wplay'
    assert viewmodel.teachingDraftStartUrl == 'https://www.wplay.co/login'
    assert viewmodel.teachingDraftObjective == 'Abrir Wplay e iniciar sesion.'
    assert viewmodel.teachingDraftExpectedOutcome == 'Sesion iniciada y panel principal visible.'
    assert viewmodel.teachingDraftNotes == 'Corregir submit y vigilar bridge_lag.'
    assert viewmodel.selectedSiteId == 'wplay'
    assert 'Formulario preparado desde el Centro de Control' in viewmodel.teachingStatus


def test_capture_studio_viewmodel_creates_brief_learning_bundle_and_replay_history() -> None:
    root = _workspace('capture_studio')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    viewmodel = CaptureStudioViewModel(
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
        interaction_learning_service=interaction_learning,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=tool_records),
    )

    viewmodel.startTeaching(
        'Login guiado',
        'Wplay',
        'https://wplay.co',
        'Iniciar sesion y llegar al panel principal.',
        'Panel principal visible.',
        'No compartir secretos.',
        True,
        True,
        True,
    )

    assert viewmodel.sessionActive is True
    assert viewmodel.activeEpisodeId
    episode_id = viewmodel.activeEpisodeId
    saved_artifacts = artifacts.list_for_episode(episode_id)
    assert any(item.kind == 'teaching_brief' for item in saved_artifacts)
    assert 'Ensenanza iniciada' in viewmodel.teachingStatus

    viewmodel.pauseTeaching()
    assert viewmodel.sessionPaused is True
    assert teach_service.paused is True
    assert 'Captura pausada' in viewmodel.teachingStatus

    viewmodel.resumeTeaching()
    assert viewmodel.sessionPaused is False
    assert teach_service.paused is False
    assert 'Captura reanudada' in viewmodel.teachingStatus

    viewmodel.stopTeaching()

    assert viewmodel.sessionActive is False
    saved_artifacts = artifacts.list_for_episode(episode_id)
    assert any(item.kind == 'learning_bundle' for item in saved_artifacts)
    assert 'Ensenanza detenida' in viewmodel.teachingStatus
    assert viewmodel.teachingHistory
    assert viewmodel.selectedTeachingHistory['episode_id'] == episode_id
    assert any(step['action_type'] == 'click' and step['element_role'] == 'button' for step in viewmodel.replaySteps)
    assert any(step['action_type'] == 'scroll' for step in viewmodel.replaySteps)
    assert any(step['has_screenshot'] and step['screenshot_url'].startswith('file:///') for step in viewmodel.replaySteps)
    assert viewmodel.selectedTeachingHistory['screenshot_count'] >= 1
    stored_interaction_episodes = tool_records.list_interaction_episodes(limit=10)
    assert len(stored_interaction_episodes) == 1
    assert stored_interaction_episodes[0].tool_id == 'playwright_browser'
    assert stored_interaction_episodes[0].metadata['source'] == 'teaching_session'
    assert stored_interaction_episodes[0].metadata['live_audit']['decision']['action'] in {'consult_codex', 'retry_after_rebuild', 'continue_local'}
    assert 'auditoria:' in viewmodel.teachingSummary.lower()


def test_capture_studio_viewmodel_builds_visual_signal_snapshot() -> None:
    root = _workspace('capture_studio_visual_signal_snapshot')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    viewmodel = CaptureStudioViewModel(
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
        interaction_learning_service=interaction_learning,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=tool_records),
    )

    viewmodel._replay_visual_summary = {
        'visual_summary': {'green_count': 3, 'orange_count': 1, 'red_count': 0},
        'learning_readiness': {'status': 'ready'},
        'login_learning': {'status': 'partial'},
        'cross_check_summary': {'status': 'aligned'},
        'metadata': {
            'latest_url': 'https://example.com/chat',
            'latest_title': 'Chat especial',
            'dom_available': True,
            'visible_targets': ['chat input', 'send button'],
            'evidence_refs': ['episode:1'],
        },
    }
    viewmodel._assistant_lane_summary = {'total': 1, 'background': 1}
    viewmodel._session_health = {'status': 'active'}

    signal = viewmodel.get_visual_signal_snapshot()

    assert signal['capture_available'] is True
    assert signal['dom_available'] is True
    assert signal['latest_url'] == 'https://example.com/chat'
    assert signal['latest_title'] == 'Chat especial'
    assert signal['learning_ready'] is True
    assert signal['cross_check_status'] == 'aligned'
    assert 'chat input' in signal['visible_targets']
    assert signal['metadata']['lane_summary']['total'] == 1


def test_capture_studio_viewmodel_uses_storage_state_only_even_if_legacy_profile_exists() -> None:
    root = _workspace('capture_studio_storage_state_only')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)

    broken_root = Path(config.browser_profiles_dir) / 'iabv_ai_generic_web'
    broken_default = broken_root / 'Default'
    broken_default.mkdir(parents=True, exist_ok=True)
    (broken_default / 'Cookies-journal').write_text('broken clone marker', encoding='utf-8')
    manifest = {
        'profile_id': 'iabv_ai_generic_web',
        'site_id': 'generic_web',
        'mode': 'cloned_profile',
        'user_data_dir': str(broken_root),
        'storage_state_path': str(Path(config.browser_states_dir) / 'generic_web.json'),
        'warning': '',
    }
    (broken_root / 'profile.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    viewmodel = CaptureStudioViewModel(
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

    viewmodel.startTeaching(
        'Consulta guiada',
        'Google',
        'https://www.google.com',
        'Abrir Google y capturar visible.',
        'Google visible.',
        'No compartir secretos.',
        True,
        True,
        True,
    )

    assert viewmodel.sessionActive is True
    assert teach_service.last_profile_config is not None
    assert teach_service.last_profile_config.persist_strategy == PersistStrategy.STORAGE_STATE_ONLY
    assert teach_service.last_profile_config.user_data_dir is None
    assert teach_service.last_profile_config.storage_state_path.endswith('generic_web.json')
    assert 'sesion ligera' in viewmodel.loginStatus.lower() or 'login manual' in viewmodel.loginStatus.lower()


def test_capture_studio_viewmodel_reports_browser_lock_on_access_denied() -> None:
    root = _workspace('capture_studio_access_denied')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)

    class _DeniedTeachSessionService(FakeTeachSessionService):
        def start_session(self, **kwargs):
            raise PermissionError(13, 'Acceso denegado', None, 5, None)

    teach_service = _DeniedTeachSessionService(episodes, config.screenshots_dir)
    viewmodel = CaptureStudioViewModel(
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

    viewmodel.startTeaching(
        'Login guiado',
        'Google',
        'https://www.google.com',
        'Abrir Google y capturar visible.',
        'Google visible.',
        'Prueba tecnica.',
        True,
        True,
        True,
    )

    assert viewmodel.sessionActive is False
    assert 'no pudo abrir la sesion ligera' in viewmodel.teachingStatus.lower()
    assert 'playwright' in viewmodel.teachingSummary.lower() or 'chromium' in viewmodel.teachingSummary.lower()
    assert 'bloqueo detectado' in viewmodel.loginStatus.lower()



def test_capture_studio_viewmodel_infers_site_from_url_and_uses_storage_state_only() -> None:
    root = _workspace('capture_studio_auto_site_storage_state')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)

    busy_root = Path(config.browser_profiles_dir) / 'iabv_ai_wplay'
    busy_default = busy_root / 'Default'
    busy_default.mkdir(parents=True, exist_ok=True)
    (busy_default / 'Preferences').write_text('{}', encoding='utf-8')
    (busy_root / 'lockfile').write_text('', encoding='utf-8')
    manifest = {
        'profile_id': 'iabv_ai_wplay',
        'site_id': 'wplay',
        'mode': 'fresh_profile',
        'user_data_dir': str(busy_root),
        'storage_state_path': str(Path(config.browser_states_dir) / 'wplay.json'),
        'warning': '',
    }
    (busy_root / 'profile.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    viewmodel = CaptureStudioViewModel(
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

    assert viewmodel.selectedSiteId == 'generic_web'

    viewmodel.previewTeachingTarget('https://www.wplay.co/casino-en-vivo', 'Casino Wplay')

    assert viewmodel.selectedSiteId == 'wplay'

    viewmodel.startTeaching(
        'Login guiado',
        'Wplay',
        'https://www.wplay.co/casino-en-vivo',
        'Iniciar sesion y llegar al panel principal.',
        'Panel principal visible.',
        'No compartir secretos.',
        True,
        True,
        True,
    )

    assert viewmodel.sessionActive is True
    assert teach_service.last_profile_config is not None
    assert teach_service.last_profile_config.site_id == 'wplay'
    assert teach_service.last_profile_config.persist_strategy == PersistStrategy.STORAGE_STATE_ONLY
    assert teach_service.last_profile_config.user_data_dir is None
    assert teach_service.last_profile_config.storage_state_path.endswith('wplay.json')


def test_capture_studio_viewmodel_records_user_clue_and_updates_history_with_incident() -> None:
    root = _workspace('capture_studio_user_clue')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    viewmodel = CaptureStudioViewModel(
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

    viewmodel.startTeaching(
        'Login guiado',
        'Google',
        'https://www.google.com',
        'Abrir Google y capturar visible.',
        'Google visible.',
        'Prueba tecnica.',
        True,
        True,
        True,
    )
    episode_id = viewmodel.activeEpisodeId
    hidden_incidents.save(
        HiddenIncident(
            episode_id=episode_id,
            site_id='generic_web',
            incident_kind='navigation_stall',
            summary='La pestana nueva se quedo cargando.',
            probable_cause='Sin progreso visible en la nueva pestana.',
        )
    )

    viewmodel.recordUserClue('Se congelo al abrir otra pestana.')
    assert 'Pista del usuario registrada' in viewmodel.teachingStatus
    viewmodel.stopTeaching()

    assert user_clues.list_recent(limit=5)
    assert any(item['incident_count'] >= 1 for item in viewmodel.teachingHistory if item['episode_id'] == episode_id)


def test_capture_studio_viewmodel_manual_annotation_updates_visual_learning() -> None:
    root = _workspace('capture_studio_manual_annotation')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    replay_repo = ReplayAnnotationRepository(db, ArtifactStorage(config.replay_annotations_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    confidence = ReplayConfidenceService()
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    viewmodel = CaptureStudioViewModel(
        config=config,
        episode_repository=episodes,
        artifact_repository=artifacts,
        site_policy_registry=registry,
        profile_manager=profiles,
        secret_vault=SecretVault(),
        browser_teach_session_service=teach_service,
        browser_learning_assembler=BrowserLearningAssembler(confidence),
        hidden_incident_repository=hidden_incidents,
        user_clue_repository=user_clues,
        runtime_signal_collector=RuntimeSignalCollector(),
        hidden_incident_detector=HiddenIncidentDetector(),
        session_health_service=SessionHealthService(),
        user_clue_service=UserClueService(clue_repository=user_clues, incident_repository=hidden_incidents),
        replay_annotation_service=ReplayAnnotationService(replay_repo),
        replay_visual_assembler=ReplayVisualAssembler(confidence),
        replay_learning_feedback_service=ReplayLearningFeedbackService(),
        interaction_learning_service=interaction_learning,
    )

    viewmodel.startTeaching(
        'Login guiado',
        'Wplay',
        'https://wplay.co',
        'Iniciar sesion y llegar al panel principal.',
        'Panel principal visible.',
        'No compartir secretos.',
        True,
        True,
        True,
    )
    episode_id = viewmodel.activeEpisodeId
    viewmodel.stopTeaching()
    viewmodel.showReplayGuided(episode_id)

    assert viewmodel.replayFrames
    viewmodel.beginAnnotationDraw()
    assert viewmodel.annotationDrawMode is True
    viewmodel.commitAnnotationRect(0.12, 0.18, 0.24, 0.14)

    assert viewmodel.annotationDrawMode is True
    assert viewmodel.selectedTeachingHistory['manual_correction_count'] >= 1
    bundle_artifact = next(item for item in artifacts.list_for_episode(episode_id) if item.kind == 'learning_bundle')
    payload = artifacts.storage.load_json(bundle_artifact.path)
    assert payload['visual_summary']['manual_correction_count'] >= 1
    assert replay_repo.list_for_episode(episode_id)
    assert payload['interaction_episode_id']
    interaction_episodes = tool_records.list_interaction_episodes(limit=10)
    assert len(interaction_episodes) == 1
    assert interaction_episodes[0].interaction_episode_id == payload['interaction_episode_id']
    assert any(signal.label.startswith('manual_corrections:') for signal in interaction_episodes[0].learning_signals)

def test_capture_studio_viewmodel_replay_gallery_includes_two_plane_audit_metadata() -> None:
    from iabv_v15.services.audit.audit_teach_verification_service import AuditTeachVerificationService

    root = _workspace('capture_studio_two_plane_audit')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    replay_repo = ReplayAnnotationRepository(db, ArtifactStorage(config.replay_annotations_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    confidence = ReplayConfidenceService()
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    viewmodel = CaptureStudioViewModel(
        config=config,
        episode_repository=episodes,
        artifact_repository=artifacts,
        site_policy_registry=registry,
        profile_manager=profiles,
        secret_vault=SecretVault(),
        browser_teach_session_service=teach_service,
        browser_learning_assembler=BrowserLearningAssembler(confidence),
        hidden_incident_repository=hidden_incidents,
        user_clue_repository=user_clues,
        runtime_signal_collector=RuntimeSignalCollector(),
        hidden_incident_detector=HiddenIncidentDetector(),
        session_health_service=SessionHealthService(),
        user_clue_service=UserClueService(clue_repository=user_clues, incident_repository=hidden_incidents),
        replay_annotation_service=ReplayAnnotationService(replay_repo),
        replay_visual_assembler=ReplayVisualAssembler(confidence),
        replay_learning_feedback_service=ReplayLearningFeedbackService(),
        interaction_learning_service=interaction_learning,
        audit_teach_verification_service=AuditTeachVerificationService(replay_confidence_service=confidence),
    )

    viewmodel.startTeaching(
        'Login guiado',
        'Wplay',
        'https://wplay.co',
        'Iniciar sesion y llegar al panel principal.',
        'Panel principal visible.',
        'No compartir secretos.',
        True,
        True,
        True,
    )
    episode_id = viewmodel.activeEpisodeId
    viewmodel.stopTeaching()

    gallery = viewmodel._load_replay_gallery(episode_id)
    summary_metadata = dict((gallery.get('summary') or {}).get('metadata') or {})

    assert 'audit_issue_count' in summary_metadata
    assert summary_metadata.get('audit_status') in {'confirmed', 'doubtful', 'insufficient'}
    assert summary_metadata.get('audit_overall_confidence') is not None
    assert any(step.get('audit_label') for step in gallery.get('timeline_steps', []))
    assert any(frame.get('audit_overlay_count', 0) >= 1 for frame in gallery.get('frames', []))


def test_capture_studio_viewmodel_guided_replay_marks_structured_login_green() -> None:
    root = _workspace('capture_studio_structured_login_green')
    config = load_app_config(str(root))
    db = AppDatabase(config.sqlite_path)
    episodes = EpisodeRepository(config.episodes_dir, db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(config.browser_artifacts_dir))
    hidden_incidents = HiddenIncidentRepository(db, ArtifactStorage(config.evolution_dir))
    user_clues = UserClueRepository(db, ArtifactStorage(config.evolution_dir))
    registry = SitePolicyRegistry(config.site_policies_dir)
    profiles = TrainingProfileManager(config.browser_profiles_dir)
    teach_service = FakeTeachSessionService(episodes, config.screenshots_dir)
    tool_records = ToolRecordRepository(db, ArtifactStorage(config.tool_teaching_dir))
    interaction_learning = InteractionLearningService(tool_records)
    replay_annotations = ReplayAnnotationRepository(db, ArtifactStorage(config.replay_annotations_dir))

    episode = episodes.create_episode('Wplay login verde', tags=['wplay', 'teach_session'])
    screenshot_dir = Path(config.screenshots_dir) / episode.episode_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / 'login_step.png'
    screenshot_path.write_bytes(bytes.fromhex('89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082'))
    episodes.save_step(
        episode.episode_id,
        CapturedStep(
            episode_id=episode.episode_id,
            action_type='frame_fallback',
            target='frame:loginandgettemptoken',
            screenshot_path=str(screenshot_path),
            metadata={
                'capture_channel': CaptureChannel.VISIBLE.value,
                'capture_source': 'frame_fallback',
                'frame_request_type': 'LoginAndGetTempToken',
                'field_role': 'email',
                'selector': 'frame:loginandgettemptoken',
                'frame_url': 'https://login.example/#{"requestType":"LoginAndGetTempToken","postParams":{"username":"user@example.com","password":"secret"}}',
                'textPreview': 'Login detectado en frame embebido.',
            },
        ),
    )
    artifacts.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='teaching_brief',
            path=f'{episode.episode_id}/brief/teaching_brief.json',
            metadata={'artifact_kind': 'teaching_brief', 'site_id': 'wplay'},
        ),
        payload={
            'lesson_title': 'Wplay login',
            'target_label': 'Wplay',
            'start_url': 'https://www.wplay.co/login',
            'objective': 'Abrir Wplay e iniciar sesion.',
            'expected_outcome': 'Sesion iniciada y panel visible.',
            'site_id': 'wplay',
            'display_name': 'Wplay',
        },
    )
    artifacts.save(
        SessionArtifact(
            episode_id=episode.episode_id,
            kind='learning_bundle',
            path=f'{episode.episode_id}/summary/learning_bundle.json',
            metadata={'artifact_kind': 'learning_bundle', 'site_id': 'wplay'},
        ),
        payload={
            'learning_readiness': {'status': 'partial', 'visual_alignment_score': 0.0, 'critical_object_coverage': 0.0},
            'login_learning': {'status': 'partial', 'login_visual_completeness': 0.0},
            'visual_summary': {'green_count': 0, 'orange_count': 4, 'red_count': 0, 'visual_alignment_score': 0.0, 'critical_object_coverage': 0.0, 'login_visual_completeness': 0.0},
        },
    )

    viewmodel = CaptureStudioViewModel(
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
        replay_annotation_service=ReplayAnnotationService(replay_annotations),
        replay_visual_assembler=ReplayVisualAssembler(ReplayConfidenceService()),
        replay_learning_feedback_service=ReplayLearningFeedbackService(),
        interaction_learning_service=interaction_learning,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=tool_records),
    )

    viewmodel.showReplayGuided(episode.episode_id)

    assert viewmodel.replayVisualSummary['green_count'] >= 3
    assert any(step['annotation_status'] == 'known' and step['has_screenshot'] for step in viewmodel.replaySteps if step['action_type'] in {'input', 'keydown', 'submit'})
    assert any(frame['status_counts']['green'] > 0 for frame in viewmodel.replayFrames)


def _make_capture_bootstrap(name: str) -> tuple[AppBootstrap, Path]:
    workspace = _workspace(name)
    bootstrap = AppBootstrap(str(workspace))
    bootstrap._build_ui_objects()
    bootstrap._test_workspace = workspace  # type: ignore[attr-defined]
    return bootstrap, workspace


def _cleanup_capture_bootstrap(bootstrap: AppBootstrap, workspace: Path) -> None:
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    finally:
        _ = bootstrap


def test_capture_studio_viewmodel_surfaces_assistant_replay_and_feedback() -> None:
    bootstrap, workspace = _make_capture_bootstrap('capture_studio_assistant_replay')
    try:
        chatgpt_desktop = bootstrap.tool_record_repository.get_card('chatgpt_installed')
        assert chatgpt_desktop is not None
        bootstrap.tool_record_repository.save_card(
            chatgpt_desktop.model_copy(
                update={
                    'metadata': {
                        **chatgpt_desktop.metadata,
                        'executable_path': '',
                        'command_name': 'definitely_missing_external_app',
                        'command_aliases': [],
                        'windows_default_paths': [],
                    }
                }
            )
        )
        chatgpt_web = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert chatgpt_web is not None
        bootstrap.tool_record_repository.save_card(chatgpt_web.model_copy(update={'metadata': {**chatgpt_web.metadata, 'dry_run_launch': True}}))
        refreshed = bootstrap.tool_record_repository.get_card('chatgpt_web_assisted')
        assert refreshed is not None
        bootstrap.tool_registry.refresh_card(refreshed)

        task, _, _ = bootstrap.tool_teach_service.execute_external_consultation(
            user_goal='resume el estado del objetivo activo',
            assistant_preference='chatgpt',
            context_pack='Objetivo activo: validar progreso longitudinal.',
            site_id='wplay',
            goal_parameters={'objective_id': 'objective-1', 'project_id': 'project-1', 'task_id': 'task-1'},
            approved=True,
            launch_dry_run=True,
        )

        viewmodel = bootstrap.capture_studio_viewmodel
        assert viewmodel is not None
        viewmodel.refresh()
        cards = viewmodel.get_assistant_replay_cards()
        assert cards
        selected = next(item for item in cards if item['task_id'] == task.task_id)
        assert selected['assistant_kind'] == 'chatgpt'
        assert selected['lane'] == 'background'
        assert selected['status'] == 'orange'
        assert selected['session_scope'] == 'program_chat'
        assert viewmodel.get_assistant_lane_summary()['pending'] >= 1

        viewmodel.selectAssistantReplayTask(task.task_id)
        steps = viewmodel.get_assistant_replay_steps()
        titles = [item['title'] for item in steps]
        assert 'Sesion e hilo' in titles
        assert 'Lane seleccionada' in titles
        assert 'Captura de respuesta' in titles

        viewmodel.recordAssistantReplayFeedback(task.task_id, 'no uses este chat')
        updated_task = bootstrap.tool_record_repository.get_task(task.task_id)
        assert updated_task is not None
        assert updated_task.metadata['assistant_feedback'][-1]['kind'] == 'no uses este chat'
        viewmodel.refresh()
        refreshed_card = next(item for item in viewmodel.get_assistant_replay_cards() if item['task_id'] == task.task_id)
        assert refreshed_card['feedback'][-1]['kind'] == 'no uses este chat'
    finally:
        _cleanup_capture_bootstrap(bootstrap, workspace)

