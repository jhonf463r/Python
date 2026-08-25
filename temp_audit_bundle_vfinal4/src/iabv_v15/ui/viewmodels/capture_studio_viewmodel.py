from __future__ import annotations

import json
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from iabv_v15.domain.models import (
    AppConfig,
    BrowserProfileConfig,
    CaptureChannel,
    HiddenIncident,
    IncidentStatus,
    IssueSeverity,
    PersistStrategy,
    RunStatus,
    SessionArtifact,
    SitePolicy,
)
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler
from iabv_v15.services.capture.universal_perception_service import UniversalPerceptionService
from iabv_v15.services.capture.replay_annotation_service import ReplayAnnotationService
from iabv_v15.services.capture.replay_learning_feedback_service import ReplayLearningFeedbackService
from iabv_v15.services.capture.replay_visual_assembler import ReplayVisualAssembler
from iabv_v15.services.capture.browser_teach_session_service import BrowserTeachSessionService, parse_frame_event_context
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.capture.training_profile_manager import TrainingProfileManager
from iabv_v15.services.evolution.execution_dossier_service import ExecutionDossierService
from iabv_v15.services.audit.audit_teach_verification_service import AuditTeachVerificationService
from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector
from iabv_v15.services.evolution.session_health_service import SessionHealthService
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.evolution.user_clue_service import UserClueService
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.ui.qt import QObject, Property, QGuiApplication, QTimer, Signal, Slot

logger = logging.getLogger(__name__)


class CaptureStudioViewModel(QObject):
    dataChanged = Signal()

    def __init__(
        self,
        *,
        config: AppConfig,
        episode_repository: EpisodeRepository,
        artifact_repository: SessionArtifactRepository,
        site_policy_registry: SitePolicyRegistry,
        profile_manager: TrainingProfileManager,
        secret_vault: SecretVault,
        browser_teach_session_service: BrowserTeachSessionService,
        browser_learning_assembler: BrowserLearningAssembler,
        hidden_incident_repository: HiddenIncidentRepository,
        user_clue_repository: UserClueRepository,
        runtime_signal_collector: RuntimeSignalCollector,
        hidden_incident_detector: HiddenIncidentDetector,
        session_health_service: SessionHealthService,
        user_clue_service: UserClueService,
        execution_dossier_service: ExecutionDossierService | None = None,
        replay_annotation_service: ReplayAnnotationService | None = None,
        replay_visual_assembler: ReplayVisualAssembler | None = None,
        replay_learning_feedback_service: ReplayLearningFeedbackService | None = None,
        interaction_learning_service: InteractionLearningService | None = None,
        tool_record_repository: ToolRecordRepository | None = None,
        live_audit_supervisor: LiveAuditSupervisor | None = None,
        audit_teach_verification_service: AuditTeachVerificationService | None = None,
        universal_perception_service: UniversalPerceptionService | None = None,
        defer_initial_refresh: bool = False,
    ) -> None:
        super().__init__()
        self.config = config
        self.episode_repository = episode_repository
        self.artifact_repository = artifact_repository
        self.site_policy_registry = site_policy_registry
        self.profile_manager = profile_manager
        self.secret_vault = secret_vault
        self.browser_teach_session_service = browser_teach_session_service
        self.browser_learning_assembler = browser_learning_assembler
        self.hidden_incident_repository = hidden_incident_repository
        self.user_clue_repository = user_clue_repository
        self.runtime_signal_collector = runtime_signal_collector
        self.hidden_incident_detector = hidden_incident_detector
        self.session_health_service = session_health_service
        self.user_clue_service = user_clue_service
        self.execution_dossier_service = execution_dossier_service
        self.replay_annotation_service = replay_annotation_service
        self.replay_visual_assembler = replay_visual_assembler
        self.replay_learning_feedback_service = replay_learning_feedback_service
        self.interaction_learning_service = interaction_learning_service
        self.tool_record_repository = tool_record_repository
        self.live_audit_supervisor = live_audit_supervisor
        self.audit_teach_verification_service = audit_teach_verification_service
        self.universal_perception_service = universal_perception_service
        self._episodes: list[dict] = []
        self._summary_cards: list[dict] = []
        self._policy_cards: list[dict] = []
        self._profile_cards: list[dict] = []
        self._channel_cards: list[dict] = []
        self._review_steps: list[dict] = []
        self._teaching_history: list[dict] = []
        self._replay_steps: list[dict] = []
        self._replay_frames: list[dict] = []
        self._replay_visual_summary: dict = {}
        self._assistant_replay_cards: list[dict] = []
        self._assistant_replay_steps: list[dict] = []
        self._assistant_lane_summary: dict = {}
        self._selected_assistant_replay_task_id = ''
        self._selected_replay_frame_index = 0
        self._selected_replay_step_index = 0
        self._selected_replay_annotation_id = ''
        self._replay_zoom = 1.0
        self._replay_status_filter = 'all'
        self._annotation_draw_mode = False
        self._selected_teaching_history: dict = {}
        self._selected_history_episode_id = ''
        self._selected_policy: dict = {}
        self._selected_site_id = 'generic_web'
        self._selected_profile_card: dict = {}
        self._login_status = 'La sesion de ensenanza se prepara sola. Si un sitio requiere login, la app intentara restaurar storage state y luego te dejara iniciar sesion manualmente.'
        self._security_state: dict = {}
        self._teaching_status = (
            'Completa el formulario y pulsa Ensenar para iniciar la captura. '
            'La captura usa una sesion administrada ligera con storage state por sitio, sin gestionar perfiles visibles.'
        )
        self._teaching_summary = 'Aun no hay una ensenanza activa ni un paquete de aprendizaje reciente.'
        self._teaching_draft_version = 0
        self._teaching_draft_lesson_title = 'Nueva ensenanza'
        self._teaching_draft_target_label = ''
        self._teaching_draft_start_url = ''
        self._teaching_draft_objective = ''
        self._teaching_draft_expected_outcome = ''
        self._teaching_draft_notes = ''
        self._session_active = False
        self._session_paused = False
        self._session_finalizing = False
        self._active_episode_id = ''
        self._active_site_policy: SitePolicy | None = None
        self._capture_progress_text = ''
        self._session_health: dict = {}
        self._runtime_signals: list[dict] = []
        self._live_incident_text = 'Sin incidencias.'
        self._flow_steps = [
            {'title': 'Capturar', 'hint': 'Registrar la sesion visible sin perder el contexto humano.'},
            {'title': 'Revisar', 'hint': 'Cruzar visible, segundo plano y trafico API.'},
            {'title': 'Confirmar', 'hint': 'Validar significado, selectores y reglas del entorno.'},
            {'title': 'Memorizar', 'hint': 'Empaquetar episodios y artefactos redactados para aprender.'},
            {'title': 'Ejecutar', 'hint': 'Reutilizar el conocimiento con salvaguardas activas.'},
        ]
        if defer_initial_refresh:
            QTimer.singleShot(0, self._safe_refresh)
        else:
            self.refresh()

    def get_episodes(self) -> list[dict]:
        return self._episodes

    def get_flow_steps(self) -> list[dict]:
        return self._flow_steps

    def get_summary_cards(self) -> list[dict]:
        return self._summary_cards

    def get_policy_cards(self) -> list[dict]:
        return self._policy_cards

    def get_channel_cards(self) -> list[dict]:
        return self._channel_cards

    def get_review_steps(self) -> list[dict]:
        return self._review_steps

    def get_teaching_history(self) -> list[dict]:
        return self._teaching_history

    def get_replay_steps(self) -> list[dict]:
        return self._replay_steps

    def get_replay_frames(self) -> list[dict]:
        return self._replay_frames

    def get_replay_current_frame(self) -> dict:
        if 0 <= self._selected_replay_frame_index < len(self._replay_frames):
            return self._replay_frames[self._selected_replay_frame_index]
        return self._replay_frames[0] if self._replay_frames else {}

    def get_replay_visual_summary(self) -> dict:
        return self._replay_visual_summary

    def get_visual_signal_snapshot(self) -> dict[str, Any]:
        if self.universal_perception_service is not None:
            try:
                return self.universal_perception_service.build_signal(
                    replay_summary=self._replay_visual_summary,
                    session_health=self._session_health,
                    lane_summary=self._assistant_lane_summary,
                    runtime_signals=self._runtime_signals,
                    site_id=self._selected_site_id,
                ).model_dump(mode='json')
            except Exception:
                pass
        summary = dict(self._replay_visual_summary or {})
        metadata = dict(summary.get('metadata') or {})
        session_health = dict(self._session_health or {})
        lane_summary = dict(self._assistant_lane_summary or {})
        visual_summary = dict(summary.get('visual_summary') or {})
        learning_readiness = dict(summary.get('learning_readiness') or {})
        cross_check = dict(summary.get('cross_check_summary') or {})
        login_learning = dict(summary.get('login_learning') or {})

        visible_targets: list[str] = []
        for collection in (
            summary.get('visible_targets'),
            metadata.get('visible_targets'),
            summary.get('focus_targets'),
            metadata.get('focus_targets'),
        ):
            if isinstance(collection, (list, tuple, set)):
                for item in collection:
                    normalized = str(item or '').strip()
                    if normalized and normalized not in visible_targets:
                        visible_targets.append(normalized)

        visual_evidence_refs: list[str] = []
        for collection in (
            summary.get('visual_evidence_refs'),
            metadata.get('visual_evidence_refs'),
            summary.get('evidence_refs'),
            metadata.get('evidence_refs'),
        ):
            if isinstance(collection, (list, tuple, set)):
                for item in collection:
                    normalized = str(item or '').strip()
                    if normalized and normalized not in visual_evidence_refs:
                        visual_evidence_refs.append(normalized)

        latest_url = str(
            metadata.get('latest_url')
            or summary.get('latest_url')
            or metadata.get('url')
            or summary.get('url')
            or session_health.get('current_url')
            or ''
        ).strip()
        latest_title = str(
            metadata.get('latest_title')
            or summary.get('latest_title')
            or metadata.get('page_title')
            or summary.get('page_title')
            or session_health.get('window_title')
            or ''
        ).strip()
        dom_available = bool(
            metadata.get('dom_available')
            or summary.get('dom_available')
            or metadata.get('dom_node_count')
            or summary.get('dom_node_count')
            or session_health.get('dom_available')
        )
        capture_available = bool(
            summary
            or lane_summary.get('total')
            or session_health.get('status')
            or visual_evidence_refs
            or latest_url
            or latest_title
        )
        login_detected = bool(
            summary.get('login_detected')
            or metadata.get('login_detected')
            or login_learning.get('status') in {'partial', 'ready'}
            or session_health.get('login_required')
            or session_health.get('status') == 'login_required'
        )
        learning_ready = bool(
            summary.get('learning_ready')
            or metadata.get('learning_ready')
            or learning_readiness.get('status') == 'ready'
        )
        cross_check_status = str(
            summary.get('cross_check_status')
            or metadata.get('cross_check_status')
            or cross_check.get('status')
            or learning_readiness.get('status')
            or ''
        ).strip()
        unresolved_fields = [
            str(item).strip()
            for item in (summary.get('unresolved_fields') or metadata.get('unresolved_fields') or [])
            if str(item).strip()
        ]
        if not capture_available and 'UNRESOLVED:visual_signal_source' not in unresolved_fields:
            unresolved_fields.append('UNRESOLVED:visual_signal_source')

        return {
            'source': str(summary.get('source') or metadata.get('source') or 'capture_studio'),
            'capture_available': capture_available,
            'dom_available': dom_available,
            'latest_url': latest_url,
            'latest_title': latest_title,
            'visible_targets': visible_targets[:8],
            'login_detected': login_detected,
            'learning_ready': learning_ready,
            'cross_check_status': cross_check_status,
            'visual_evidence_refs': visual_evidence_refs[:8],
            'unresolved_fields': unresolved_fields,
            'metadata': {
                'green_count': int(visual_summary.get('green_count') or summary.get('green_count') or 0),
                'orange_count': int(visual_summary.get('orange_count') or summary.get('orange_count') or 0),
                'red_count': int(visual_summary.get('red_count') or summary.get('red_count') or 0),
                'lane_summary': lane_summary,
                'session_health_status': str(session_health.get('status') or ''),
                'learning_status': str(learning_readiness.get('status') or ''),
                'login_status': str(login_learning.get('status') or ''),
            },
        }

    def get_selected_replay_step(self) -> dict:
        if 0 <= self._selected_replay_step_index < len(self._replay_steps):
            return self._replay_steps[self._selected_replay_step_index]
        return {}

    def get_selected_replay_annotation(self) -> dict:
        annotation_id = self._selected_replay_annotation_id
        if not annotation_id:
            return {}
        for frame in self._replay_frames:
            for overlay in frame.get('overlays', []):
                if overlay.get('annotation_id') == annotation_id:
                    return overlay
        return {}

    def get_replay_zoom(self) -> float:
        return self._replay_zoom

    def get_replay_status_filter(self) -> str:
        return self._replay_status_filter

    def get_replay_can_go_prev(self) -> bool:
        return self._selected_replay_frame_index > 0

    def get_replay_can_go_next(self) -> bool:
        return self._selected_replay_frame_index < max(0, len(self._replay_frames) - 1)

    def get_annotation_draw_mode(self) -> bool:
        return self._annotation_draw_mode

    def get_selected_teaching_history(self) -> dict:
        return self._selected_teaching_history

    def get_selected_policy(self) -> dict:
        return self._selected_policy

    def get_selected_site_id(self) -> str:
        return self._selected_site_id

    def get_login_status(self) -> str:
        return self._login_status

    def get_security_state(self) -> dict:
        return self._security_state

    def get_teaching_status(self) -> str:
        return self._teaching_status

    def get_teaching_summary(self) -> str:
        return self._teaching_summary


    def get_teaching_draft_version(self) -> int:
        return self._teaching_draft_version

    def get_teaching_draft_lesson_title(self) -> str:
        return self._teaching_draft_lesson_title

    def get_teaching_draft_target_label(self) -> str:
        return self._teaching_draft_target_label

    def get_teaching_draft_start_url(self) -> str:
        return self._teaching_draft_start_url

    def get_teaching_draft_objective(self) -> str:
        return self._teaching_draft_objective

    def get_teaching_draft_expected_outcome(self) -> str:
        return self._teaching_draft_expected_outcome

    def get_teaching_draft_notes(self) -> str:
        return self._teaching_draft_notes

    def get_session_active(self) -> bool:
        return self._session_active

    def get_session_paused(self) -> bool:
        return self._session_paused

    def get_session_finalizing(self) -> bool:
        return self._session_finalizing

    def get_capture_progress_text(self) -> str:
        return self._capture_progress_text

    def get_session_health(self) -> dict:
        return self._session_health

    def get_runtime_signals(self) -> list[dict]:
        return list(self._runtime_signals)

    def get_live_incident_text(self) -> str:
        return self._live_incident_text

    def get_can_start(self) -> bool:
        if self._session_active or self._session_finalizing:
            return False
        return True

    def get_can_pause(self) -> bool:
        return self._session_active and not self._session_paused and not self._session_finalizing

    def get_can_resume(self) -> bool:
        return self._session_active and self._session_paused and not self._session_finalizing

    def get_can_stop(self) -> bool:
        return self._session_active and not self._session_finalizing

    def get_active_episode_id(self) -> str:
        return self._active_episode_id

    def _selected_profile_card_for_site(self, site_id: str | None = None) -> dict:
        return {}

    def _sync_selected_profile_state(self) -> None:
        self._selected_profile_card = {}

    def _sync_login_status(self) -> None:
        if self._session_active:
            return
        self._login_status = 'La sesion de ensenanza se prepara sola. Si un sitio requiere login, la app intentara restaurar storage state por sitio y luego te dejara iniciar sesion manualmente.'

    def _normalize_url_probe(self, start_url: str) -> str:
        value = start_url.strip()
        if not value:
            return ''
        if value.startswith(('http://', 'https://', 'about:', 'file://')):
            return value
        if '.' in value and ' ' not in value:
            return f'https://{value}'
        return ''

    def _extract_domain(self, start_url: str) -> str:
        candidate = self._normalize_url_probe(start_url)
        if not candidate:
            return ''
        parsed = urlsplit(candidate)
        domain = (parsed.netloc or parsed.path or '').split('@')[-1].split(':')[0].strip().lower()
        while domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def _policy_domains(self, policy: SitePolicy) -> list[str]:
        domains: list[str] = []
        for item in policy.domains:
            domain = (item or '').strip().lower()
            if not domain or domain == '*':
                continue
            if domain.startswith(('http://', 'https://')):
                parsed = urlsplit(domain)
                domain = (parsed.netloc or parsed.path or '').split(':')[0].lower()
            while domain.startswith('www.'):
                domain = domain[4:]
            if domain:
                domains.append(domain)
        return domains

    def _domain_matches_policy(self, domain: str, policy: SitePolicy) -> bool:
        if not domain:
            return False
        return any(domain == candidate or domain.endswith(f'.{candidate}') for candidate in self._policy_domains(policy))

    def _infer_policy(self, start_url: str = '', target_label: str = '', explicit_site_id: str | None = None) -> SitePolicy | None:
        if explicit_site_id:
            explicit = self.site_policy_registry.get_policy(explicit_site_id.strip())
            if explicit is not None:
                return explicit
        policies = self.site_policy_registry.list_policies()
        if not policies:
            return None
        domain = self._extract_domain(start_url)
        if domain:
            for policy in policies:
                if self._domain_matches_policy(domain, policy):
                    return policy
        probe = target_label.strip().lower()
        if probe:
            for policy in policies:
                names = [policy.site_id.lower(), policy.display_name.lower(), *self._policy_domains(policy)]
                if any(probe in item or item in probe for item in names if item):
                    return policy
        current = self._current_policy()
        if current is not None:
            return current
        return next((policy for policy in policies if policy.site_id == 'generic_web'), policies[0])

    def _apply_policy_selection(self, policy: SitePolicy | None) -> SitePolicy | None:
        if policy is None:
            return None
        self._selected_site_id = policy.site_id
        self._selected_policy = policy.model_dump(mode='json')
        self._sync_selected_profile_state()
        self._sync_login_status()
        return policy

    def _runtime_site_id(self) -> str:
        if self._active_site_policy is not None:
            return self._active_site_policy.site_id
        if self._selected_policy:
            return self._selected_policy.get('site_id', self._selected_site_id) or self._selected_site_id
        return self._selected_site_id

    def _capture_runtime_incidents(self, runtime_snapshot: dict | None) -> list[dict]:
        snapshot = dict(runtime_snapshot or {})
        episode_id = snapshot.get('episode_id') or self._active_episode_id or self._selected_history_episode_id
        site_id = snapshot.get('site_id') or self._runtime_site_id() or 'generic_web'
        signals = self.runtime_signal_collector.capture_tick(episode_id=episode_id or None, site_id=site_id, runtime_snapshot=snapshot)
        self._runtime_signals = [item.model_dump(mode='json') for item in signals]
        existing = self.hidden_incident_repository.find_by_episode(episode_id) if episode_id else []
        new_incidents = self.hidden_incident_detector.detect_from_snapshot(
            episode_id=episode_id or None,
            site_id=site_id,
            runtime_snapshot=snapshot,
            signals=signals,
            existing_incidents=existing,
        )
        for incident in new_incidents:
            self.hidden_incident_repository.save(incident)
        incidents = self.hidden_incident_repository.find_by_episode(episode_id) if episode_id else existing + new_incidents
        health = self.session_health_service.snapshot_for_teaching_session(
            episode_id=episode_id or None,
            site_id=site_id,
            runtime_snapshot=snapshot,
            incidents=incidents,
        )
        self._session_health = health.model_dump(mode='json')
        self._live_incident_text = health.detail if health.health_flags else health.health_label
        return [item.model_dump(mode='json') for item in incidents]

    def _refresh_session_health(self, runtime_snapshot: dict | None = None) -> None:
        snapshot = dict(runtime_snapshot or {})
        episode_id = self._active_episode_id or self._selected_history_episode_id
        site_id = snapshot.get('site_id') or self._runtime_site_id() or 'generic_web'
        incidents = self.hidden_incident_repository.find_by_episode(episode_id) if episode_id else []
        if not snapshot and hasattr(self.browser_teach_session_service, 'runtime_snapshot') and self._session_active:
            try:
                snapshot = self.browser_teach_session_service.runtime_snapshot()
            except Exception:
                snapshot = {}
        health = self.session_health_service.snapshot_for_teaching_session(
            episode_id=episode_id or None,
            site_id=site_id,
            runtime_snapshot=snapshot,
            incidents=incidents,
        )
        self._session_health = health.model_dump(mode='json')
        self._live_incident_text = health.detail if health.health_flags else health.health_label

    @Slot()
    def refresh(self) -> None:
        episodes = self.episode_repository.list_recent(limit=24)
        artifacts = self.artifact_repository.list_recent(limit=120)
        policies = self.site_policy_registry.list_policies()
        storage_states = list(Path(self.config.browser_states_dir).glob('*.json'))
        self._episodes = [episode.model_dump(mode='json') for episode in episodes]
        self._policy_cards = [self._policy_to_card(policy) for policy in policies]
        self._profile_cards = []
        self._summary_cards = [
            {'title': 'Entornos', 'value': str(len(policies)), 'hint': 'Politicas activas para sesiones guiadas en navegador y futuros entornos.'},
            {'title': 'Estado guardado', 'value': str(len(storage_states)), 'hint': 'Storage state por sitio reutilizable cuando la pagina permite conservar sesion.'},
            {'title': 'Episodios', 'value': str(len(episodes)), 'hint': 'Sesiones recientes listas para revision y memoria.'},
            {'title': 'Artefactos', 'value': str(len(artifacts)), 'hint': 'Visible, segundo plano y API preservados con redaccion.'},
        ]
        self._channel_cards = self._build_channel_cards(artifacts)
        self._review_steps = self._load_review_steps(episodes)
        self._teaching_history = self._build_teaching_history(episodes)
        self._sync_selected_teaching_history()
        selected_policy = self.site_policy_registry.get_policy(self._selected_site_id)
        if selected_policy is None and policies:
            selected_policy = policies[0]
            self._selected_site_id = selected_policy.site_id
        self._selected_policy = selected_policy.model_dump(mode='json') if selected_policy is not None else {}
        self._sync_selected_profile_state()
        self._sync_login_status()
        capture_stats = getattr(self.browser_teach_session_service, 'capture_stats', {}) or {}
        self._security_state = {
            'label': 'Secretos protegidos',
            'detail': 'Passwords, emails, cookies y tokens se enmascaran antes de persistir o analizar.',
            'vault_mode': 'Windows Credential Manager' if self.secret_vault.available else 'Vault no disponible; solo redaccion local.',
            'local_first': 'Analisis crudo solo local hasta generar un resumen seguro para aprendizaje.',
            'capture_hint': 'Canales disponibles: interfaz visible, segundo plano y API.',
            'credential_check': 'Las credenciales se guardan solo como referencia de vault y valor enmascarado; el texto crudo se elimina del paso.',
            'bridge_active': bool(capture_stats.get('bridge_active')),
            'capture_visible_ok': bool(capture_stats.get('capture_visible_ok')),
            'frames_detected': int(capture_stats.get('frames_detected', 0) or 0),
            'api_capture_mode': capture_stats.get('api_capture_mode', 'smart'),
            'visible_step_count': int(capture_stats.get('visible_step_count', 0) or 0),
            'screenshot_count': int(capture_stats.get('screenshot_count', 0) or 0),
        }
        self._refresh_session_health(capture_stats if isinstance(capture_stats, dict) else {})
        self._refresh_assistant_replay()
        self.dataChanged.emit()

    def _safe_refresh(self) -> None:
        try:
            self.refresh()
        except Exception as exc:
            logger.warning('capture_studio: deferred refresh skipped: %s', exc)

    def _refresh_assistant_replay(self) -> None:
        if self.tool_record_repository is None:
            self._assistant_replay_cards = []
            self._assistant_replay_steps = []
            self._assistant_lane_summary = {}
            self._selected_assistant_replay_task_id = ''
            return
        tasks = [task for task in self.tool_record_repository.list_tasks(limit=24) if str(task.metadata.get('consultation_scope') or '').strip() == 'external_assistant']
        cards = [self._assistant_replay_card(task) for task in tasks]
        cards = [card for card in cards if card]
        self._assistant_replay_cards = cards
        if self._selected_assistant_replay_task_id and not any(card.get('task_id') == self._selected_assistant_replay_task_id for card in cards):
            self._selected_assistant_replay_task_id = ''
        if not self._selected_assistant_replay_task_id and cards:
            self._selected_assistant_replay_task_id = str(cards[0].get('task_id') or '')
        self._assistant_replay_steps = self._assistant_replay_step_list(self._selected_assistant_replay_task_id)
        lane_counts = {'background': 0, 'app': 0, 'manual': 0, 'captured': 0, 'pending': 0, 'blocked': 0}
        for card in cards:
            lane = str(card.get('lane') or 'manual')
            lane_counts[lane if lane in lane_counts else 'manual'] += 1
            status = str(card.get('status') or '')
            if status == 'green':
                lane_counts['captured'] += 1
            elif status == 'orange':
                lane_counts['pending'] += 1
            else:
                lane_counts['blocked'] += 1
        self._assistant_lane_summary = {
            'total': len(cards),
            'selected_task_id': self._selected_assistant_replay_task_id,
            **lane_counts,
        }

    def _assistant_replay_card(self, task) -> dict:
        result = self._assistant_latest_result(task.task_id)
        metadata = self._assistant_consultation_metadata(task, result)
        assistant_kind = str(metadata.get('assistant_kind') or task.metadata.get('assistant_kind') or '').strip().lower()
        thread_key = str(metadata.get('thread_key') or task.metadata.get('thread_key') or '')
        thread_title = str(metadata.get('thread_title') or task.metadata.get('thread_title') or '')
        lane = str(metadata.get('capture_lane') or task.metadata.get('capture_lane') or 'manual')
        awaiting_reason = str(metadata.get('awaiting_reason') or task.metadata.get('awaiting_reason') or '')
        status = self._assistant_replay_status(metadata, result)
        summary = str(
            metadata.get('response_summary')
            or metadata.get('detail')
            or metadata.get('response_excerpt')
            or getattr(result, 'output_text', '')
            or task.objective
        ).strip()
        return {
            'task_id': task.task_id,
            'result_id': getattr(result, 'result_id', ''),
            'assistant_kind': assistant_kind,
            'assistant_title': self._assistant_title(assistant_kind),
            'title': str(task.title or self._assistant_title(assistant_kind) or 'Consulta externa'),
            'status': status,
            'status_label': self._assistant_status_label(status),
            'lane': lane,
            'thread_key': thread_key,
            'thread_title': thread_title,
            'session_label': str(metadata.get('session_label') or task.metadata.get('session_label') or ''),
            'session_scope': str(metadata.get('session_scope') or task.metadata.get('session_scope') or ''),
            'awaiting_reason': awaiting_reason,
            'summary': summary,
            'validation_status': str(metadata.get('response_validation', {}).get('status') or getattr(getattr(result, 'validation_status', None), 'value', '') or ''),
            'learning_status': 'consolidado' if bool(metadata.get('response_ingested')) else ('pendiente' if str(metadata.get('status') or '') == 'awaiting_response' else 'rechazado' if metadata.get('coherence_flags') else 'capturado'),
            'coherence_flags': list(metadata.get('coherence_flags') or []),
            'feedback': list(task.metadata.get('assistant_feedback') or []),
        }

    def _assistant_latest_result(self, task_id: str):
        if self.tool_record_repository is None:
            return None
        results = self.tool_record_repository.list_results(task_id=task_id, limit=1)
        return results[0] if results else None

    def _assistant_consultation_metadata(self, task, result) -> dict:
        task_metadata = dict(task.metadata or {})
        result_metadata = dict(getattr(result, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        consultation = dict(result_metadata.get('autonomous_consultation') or task_metadata.get('autonomous_consultation') or {})
        merged = {**task_metadata, **consultation, **execution_metadata}
        if result is not None and getattr(result, 'output_text', '') and 'detail' not in merged:
            merged['detail'] = getattr(result, 'output_text', '')
        return merged

    def _assistant_replay_status(self, metadata: dict, result) -> str:
        coherence_flags = list(metadata.get('coherence_flags') or [])
        validation = dict(metadata.get('response_validation') or {})
        status = str(metadata.get('status') or getattr(getattr(result, 'execution_state', None), 'state', '') or '').strip()
        if coherence_flags or status in {'failed', 'adapter_missing'}:
            return 'red'
        if bool(metadata.get('response_ingested')) or validation.get('status') in {'approved', 'sandbox_pass'} or bool(metadata.get('response_captured')):
            return 'green'
        if status in {'awaiting_response', 'prepared', 'reused', 'captured'} or metadata.get('response_capture_pending'):
            return 'orange'
        return 'red'

    def _assistant_status_label(self, status: str) -> str:
        return {'green': 'verde', 'orange': 'naranja', 'red': 'rojo'}.get(str(status or ''), 'rojo')

    def _assistant_title(self, assistant_kind: str) -> str:
        return {
            'codex': 'Codex',
            'chatgpt': 'ChatGPT',
            'claude': 'Claude',
            'ollama': 'Ollama',
        }.get(str(assistant_kind or '').strip().lower(), 'Asistente externo')

    def _assistant_replay_step_list(self, task_id: str) -> list[dict]:
        if self.tool_record_repository is None or not task_id:
            return []
        task = self.tool_record_repository.get_task(task_id)
        if task is None:
            return []
        result = self._assistant_latest_result(task_id)
        metadata = self._assistant_consultation_metadata(task, result)
        validation = dict(metadata.get('response_validation') or {})
        steps = [
            self._assistant_step(
                title='Sesion e hilo',
                detail=(str(metadata.get('session_label') or 'sin sesion') + ' | ' + str(metadata.get('thread_title') or metadata.get('thread_key') or 'sin hilo dedicado')).strip(),
                status='known' if metadata.get('thread_key') or metadata.get('session_label') else 'missing',
            ),
            self._assistant_step(
                title='Lane seleccionada',
                detail=' > '.join(metadata.get('lane_priority') or [str(metadata.get('capture_lane') or 'manual')]),
                status='known' if str(metadata.get('capture_lane') or '') in {'background', 'app'} else 'uncertain',
            ),
            self._assistant_step(
                title='Captura de respuesta',
                detail=str(metadata.get('awaiting_reason') or metadata.get('detail') or 'sin detalle de captura'),
                status='known' if metadata.get('response_captured') else ('uncertain' if metadata.get('response_capture_pending') or str(metadata.get('status') or '') == 'awaiting_response' else 'missing'),
            ),
            self._assistant_step(
                title='Validacion y adopcion',
                detail=str(validation.get('rationale') or metadata.get('response_summary') or 'sin validacion registrada'),
                status='known' if validation.get('status') in {'approved', 'sandbox_pass'} or metadata.get('response_ingested') else ('uncertain' if validation.get('status') in {'review_needed', ''} else 'missing'),
            ),
            self._assistant_step(
                title='Aprendizaje resultante',
                detail=' | '.join(list(metadata.get('coherence_flags') or [])) or ('Aprendizaje consolidado para esta consulta.' if metadata.get('response_ingested') else 'Todavia no consolido aprendizaje estable.'),
                status='known' if metadata.get('response_ingested') and not metadata.get('coherence_flags') else ('uncertain' if str(metadata.get('status') or '') in {'awaiting_response', 'captured'} else 'missing'),
            ),
        ]
        for entry in (self.tool_record_repository.list_log(task_id=task_id, limit=3) if self.tool_record_repository is not None else []):
            steps.append(
                self._assistant_step(
                    title=str(entry.get('action_type') or 'evento').replace('_', ' '),
                    detail=str((entry.get('payload') or {}).get('detail') or (entry.get('payload') or {}).get('reason') or entry.get('state') or ''),
                    status='uncertain',
                )
            )
        return steps

    def _assistant_step(self, *, title: str, detail: str, status: str) -> dict:
        palette = {
            'known': '#7df0a8',
            'uncertain': '#f0a65b',
            'missing': '#ff7f7f',
        }
        return {
            'title': title,
            'detail': detail,
            'status': status,
            'display_color': palette.get(status, '#f0a65b'),
        }

    @Slot(str)
    def selectAssistantReplayTask(self, task_id: str) -> None:
        self._selected_assistant_replay_task_id = task_id.strip()
        self._assistant_replay_steps = self._assistant_replay_step_list(self._selected_assistant_replay_task_id)
        self.dataChanged.emit()

    @Slot(str, str)
    def recordAssistantReplayFeedback(self, task_id: str, feedback_kind: str) -> None:
        if self.tool_record_repository is None:
            return
        task = self.tool_record_repository.get_task(task_id.strip())
        if task is None:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = dict(task.metadata or {})
        feedback = list(metadata.get('assistant_feedback') or [])
        feedback.append({'kind': feedback_kind.strip(), 'created_at_utc': timestamp})
        metadata['assistant_feedback'] = feedback[-12:]
        self.tool_record_repository.save_task(task.model_copy(update={'metadata': metadata}))
        site_id = str(task.site_id or metadata.get('site_id') or self._selected_site_id or 'generic_web')
        episode_id = self._selected_history_episode_id or None
        if self.user_clue_service is not None:
            clue_text = f"[assistant_replay] {feedback_kind.strip()} | tool {task.tool_id} | hilo {metadata.get('thread_title') or metadata.get('thread_key') or 'sin hilo'}"
            self.user_clue_service.attach_to_latest_context(text=clue_text, site_id=site_id, episode_id=episode_id)
        self._teaching_status = 'Feedback de asistente guardado para auditar la consulta externa.'
        self._refresh_assistant_replay()
        self.dataChanged.emit()

    def get_assistant_replay_cards(self) -> list[dict]:
        return self._assistant_replay_cards

    def get_assistant_replay_steps(self) -> list[dict]:
        return self._assistant_replay_steps

    def get_assistant_lane_summary(self) -> dict:
        return self._assistant_lane_summary


    def applyAdaptiveTeachingPrefill(self, draft: dict | None) -> None:
        if self._session_active or self._session_finalizing:
            return
        payload = dict(draft or {})
        self._teaching_draft_lesson_title = str(payload.get('lesson_title') or 'Nueva ensenanza').strip() or 'Nueva ensenanza'
        self._teaching_draft_target_label = str(payload.get('target_label') or '').strip()
        self._teaching_draft_start_url = str(payload.get('start_url') or '').strip()
        self._teaching_draft_objective = str(payload.get('objective') or '').strip()
        self._teaching_draft_expected_outcome = str(payload.get('expected_outcome') or '').strip()
        self._teaching_draft_notes = str(payload.get('notes') or '').strip()
        explicit_site_id = str(payload.get('site_id') or '').strip()
        policy = self._infer_policy(
            start_url=self._teaching_draft_start_url,
            target_label=self._teaching_draft_target_label,
            explicit_site_id=explicit_site_id or self._selected_site_id,
        )
        if policy is not None:
            self._apply_policy_selection(policy)
        self._teaching_draft_version += 1
        summary_bits: list[str] = []
        if self._teaching_draft_start_url:
            summary_bits.append(f'URL inicial sugerida: {self._teaching_draft_start_url}')
        if self._teaching_draft_objective:
            summary_bits.append(f'Objetivo sugerido: {self._teaching_draft_objective}')
        if self._teaching_draft_expected_outcome:
            summary_bits.append(f'Resultado esperado: {self._teaching_draft_expected_outcome}')
        self._teaching_status = 'Formulario preparado desde el Centro de Control con el contexto que ya conozco del flujo.'
        self._teaching_summary = ' | '.join(summary_bits) if summary_bits else 'Formulario listo para completar lo que todavia no conozco.'
        self.dataChanged.emit()

    @Slot(str)
    def selectSite(self, site_id: str) -> None:
        policy = self._infer_policy(explicit_site_id=site_id.strip() or self._selected_site_id)
        self._apply_policy_selection(policy)
        self.dataChanged.emit()

    @Slot(str, str)
    def previewTeachingTarget(self, start_url: str, target_label: str) -> None:
        if self._session_active or self._session_finalizing:
            return
        previous_site_id = self._selected_site_id
        policy = self._infer_policy(start_url=start_url, target_label=target_label)
        if policy is None:
            return
        self._apply_policy_selection(policy)
        if previous_site_id != self._selected_site_id and not self._teaching_status.startswith('Ensenanza '):
            self._teaching_status = f'Sitio detectado automaticamente: {policy.display_name}. La sesion ligera se ajusto a esta URL.'
        self.dataChanged.emit()

    @Slot(str)
    def selectTeachingEpisode(self, episode_id: str) -> None:
        self._selected_history_episode_id = episode_id.strip()
        self._sync_selected_teaching_history()
        self.dataChanged.emit()

    @Slot(str)
    def showReplayGuided(self, episode_id: str) -> None:
        target_episode_id = episode_id.strip()
        if not target_episode_id:
            return
        self._selected_history_episode_id = target_episode_id
        self._sync_selected_teaching_history()
        selected_title = self._selected_teaching_history.get('title', 'Replay guiado')
        self._teaching_status = f'Replay guiado cargado para {selected_title}.'
        suggested = self._selected_teaching_history.get('suggested_commands') or []
        suggestion_text = f" | di: {suggested[1] if len(suggested) > 1 else suggested[0]}" if suggested else ''
        self._teaching_summary = (
            f"Pasos detectados: {len(self._replay_steps)} | frames: {len(self._replay_frames)} | episodio: {target_episode_id}"
            f" | aprendizaje: {self._selected_teaching_history.get('learning_readiness', 'insufficient')}"
            f" | login: {self._selected_teaching_history.get('login_learning_status', 'insufficient')}"
            f" | verde/naranja/rojo: {self._replay_visual_summary.get('green_count', 0)}/{self._replay_visual_summary.get('orange_count', 0)}/{self._replay_visual_summary.get('red_count', 0)}"
            f"{suggestion_text}"
        )
        self.dataChanged.emit()

    @Slot(int)
    def openReplayFrame(self, index: int) -> None:
        if not self._replay_frames:
            return
        index = max(0, min(index, len(self._replay_frames) - 1))
        self._selected_replay_frame_index = index
        frame = self._replay_frames[index]
        frame_step_ids = set(frame.get('step_ids') or [])
        matching_index = next((i for i, step in enumerate(self._replay_steps) if step.get('step_id') in frame_step_ids), None)
        if matching_index is None:
            matching_index = next((i for i, step in enumerate(self._replay_steps) if step.get('frame_index') == index), None)
        if matching_index is not None:
            self._selected_replay_step_index = matching_index
        self._selected_replay_annotation_id = ''
        self.dataChanged.emit()

    @Slot()
    def nextReplayFrame(self) -> None:
        if self._selected_replay_frame_index < len(self._replay_frames) - 1:
            self.openReplayFrame(self._selected_replay_frame_index + 1)

    @Slot()
    def previousReplayFrame(self) -> None:
        if self._selected_replay_frame_index > 0:
            self.openReplayFrame(self._selected_replay_frame_index - 1)

    @Slot(int)
    def selectReplayStep(self, step_index: int) -> None:
        if not self._replay_steps:
            return
        step_index = max(0, min(step_index, len(self._replay_steps) - 1))
        self._selected_replay_step_index = step_index
        step = self._replay_steps[step_index]
        frame_index = step.get('frame_index', -1)
        if isinstance(frame_index, int) and frame_index >= 0:
            self._selected_replay_frame_index = max(0, min(frame_index, len(self._replay_frames) - 1))
        self._selected_replay_annotation_id = step.get('annotation_id') or ''
        self.dataChanged.emit()

    @Slot(str)
    def selectReplayAnnotation(self, annotation_id: str) -> None:
        self._selected_replay_annotation_id = annotation_id.strip()
        self.dataChanged.emit()

    @Slot(float)
    def setReplayZoom(self, value: float) -> None:
        self._replay_zoom = max(0.5, min(float(value or 1.0), 3.0))
        self.dataChanged.emit()

    @Slot(str)
    def setReplayStatusFilter(self, value: str) -> None:
        normalized = (value or 'all').strip().lower()
        if normalized not in {'all', 'green', 'orange', 'red'}:
            normalized = 'all'
        if normalized != self._replay_status_filter:
            self._replay_status_filter = normalized
            self.dataChanged.emit()

    @Slot()
    def beginAnnotationDraw(self) -> None:
        self._annotation_draw_mode = not self._annotation_draw_mode
        self._teaching_status = (
            'Modo dibujo activo: arrastra sobre la captura para encerrar el objeto y pulsa Cancelar dibujo cuando termines.'
            if self._annotation_draw_mode
            else 'Modo dibujo desactivado.'
        )
        self.dataChanged.emit()

    @Slot(float, float, float, float)
    def commitAnnotationRect(self, x: float, y: float, width: float, height: float) -> None:
        if self.replay_annotation_service is None or not self._selected_teaching_history:
            return
        frame = self.get_replay_current_frame()
        if not frame:
            return
        episode_id = self._selected_teaching_history.get('episode_id', '')
        if not episode_id:
            return
        rect = {
            'valid': True,
            'x': max(0.0, min(1.0, float(x))),
            'y': max(0.0, min(1.0, float(y))),
            'width': max(0.0, min(1.0, float(width))),
            'height': max(0.0, min(1.0, float(height))),
        }
        step = self.get_selected_replay_step()
        overlay_label = step.get('overlay_label') or step.get('text') or step.get('selector') or 'objeto corregido'
        annotation = self.replay_annotation_service.save_user_annotation(
            episode_id=episode_id,
            screenshot_path=frame.get('screenshot_path', ''),
            group_key=frame.get('group_key', ''),
            step_id=step.get('step_id') or None,
            linked_screenshot_id=frame.get('frame_id', ''),
            overlay_kind='rect',
            status='user_corrected',
            confidence_score=0.96,
            overlay_rect=rect,
            overlay_label=overlay_label,
            overlay_notes='Correccion manual del usuario sobre el replay.',
            metadata={'selected_step_index': self._selected_replay_step_index},
        )
        self._selected_replay_annotation_id = annotation.annotation_id
        self._refresh_replay_after_annotation(episode_id)
        self._teaching_status = (
            'Anotacion guardada como aprendizaje persistente. '
            'Puedes dibujar otra o pulsar Cancelar dibujo cuando termines.'
        )
        self.dataChanged.emit()

    @Slot(str, str)
    def setReplayAnnotationStatus(self, annotation_id: str, status: str) -> None:
        if self.replay_annotation_service is None:
            return
        updated = self.replay_annotation_service.update_status(annotation_id.strip(), status.strip())
        if updated is None:
            return
        self._selected_replay_annotation_id = updated.annotation_id
        self._refresh_replay_after_annotation(updated.episode_id)
        self._teaching_status = 'Estado de anotacion actualizado.'
        self.dataChanged.emit()

    @Slot(str, str)
    def setReplayAnnotationLabel(self, annotation_id: str, label: str) -> None:
        if self.replay_annotation_service is None:
            return
        updated = self.replay_annotation_service.update_label(annotation_id.strip(), label.strip())
        if updated is None:
            return
        self._selected_replay_annotation_id = updated.annotation_id
        self._refresh_replay_after_annotation(updated.episode_id)
        self._teaching_status = 'Etiqueta de anotacion actualizada.'
        self.dataChanged.emit()

    @Slot(str)
    def clearReplayAnnotation(self, annotation_id: str) -> None:
        if self.replay_annotation_service is None or not self._selected_teaching_history:
            return
        episode_id = self._selected_teaching_history.get('episode_id', '')
        self.replay_annotation_service.clear(annotation_id.strip())
        self._selected_replay_annotation_id = ''
        self._refresh_replay_after_annotation(episode_id)
        self._teaching_status = 'Anotacion eliminada del replay.'
        self.dataChanged.emit()

    @Slot(str)
    def deleteTeachingEpisode(self, episode_id: str) -> None:
        target_episode_id = episode_id.strip()
        if not target_episode_id:
            return
        if self._session_active and target_episode_id == self._active_episode_id:
            self._teaching_status = 'Deten la ensenanza activa antes de eliminarla del historial.'
            self.dataChanged.emit()
            return
        try:
            steps = self.episode_repository.load_episode(target_episode_id)
            artifacts = self.artifact_repository.list_for_episode(target_episode_id)
            for step in steps:
                self._delete_managed_path(step.screenshot_path)
            for artifact in artifacts:
                self._delete_managed_path(artifact.path)
            self._delete_managed_path(Path(self.config.screenshots_dir) / target_episode_id)
            self._delete_managed_path(Path(self.config.browser_artifacts_dir) / target_episode_id)
            self._delete_managed_path(Path(self.config.episodes_dir) / target_episode_id)
            self.episode_repository.db.execute('DELETE FROM episodes WHERE episode_id = ?', (target_episode_id,))
            self.artifact_repository.db.execute('DELETE FROM session_artifacts WHERE episode_id = ?', (target_episode_id,))
            if self._selected_history_episode_id == target_episode_id:
                self._selected_history_episode_id = ''
            if self._active_episode_id == target_episode_id:
                self._active_episode_id = ''
            self.refresh()
            self._teaching_status = f'Ensenanza {target_episode_id} eliminada del historial.'
            self._teaching_summary = f'Quedan {len(self._teaching_history)} ensenanzas recientes disponibles para replay.'
            self.dataChanged.emit()
        except Exception as exc:
            self._teaching_status = f'No pude eliminar la ensenanza: {exc}'
            self.dataChanged.emit()

    @Slot(str)
    def bootstrapProfile(self, site_id: str) -> None:
        site_key = site_id.strip() or self._selected_site_id
        policy = self.site_policy_registry.get_policy(site_key)
        if policy is None:
            self._login_status = f'No existe politica para {site_key}.'
            self.dataChanged.emit()
            return
        profile = self._build_profile_config(policy)
        result = self.profile_manager.bootstrap_clone(profile)
        self._selected_site_id = policy.site_id
        self.refresh()
        profile_card = next((item for item in self._profile_cards if item.get('profile_id') == result.profile_id), None) or {}
        health_detail = profile_card.get('health_detail', 'Reutilizalo para conservar sesion.')
        self._login_status = (
            f'Perfil IA {result.profile_id} listo en {result.user_data_dir}. '
            f'{health_detail} '
            f'No uses tu Google principal; si necesitas sync, usa una cuenta secundaria.'
        )
        self.dataChanged.emit()

    @Slot(str, str)
    def openProfileManual(self, site_id: str, start_url: str) -> None:
        site_key = site_id.strip() or self._selected_site_id
        policy = self.site_policy_registry.get_policy(site_key)
        if policy is None:
            self._login_status = f'No existe politica para {site_key}.'
            self.dataChanged.emit()
            return
        profile = self.profile_manager.bootstrap_clone(self._build_profile_config(policy))
        resolved_url = self._resolve_start_url(start_url, policy)
        result = self.profile_manager.open_profile(profile, start_url=resolved_url)
        self.refresh()
        if result.get('status') == 'ok':
            self._login_status = (
                f'Perfil IA {profile.profile_id} abierto en modo manual. Usa este perfil para iniciar sesion en la web o, si realmente necesitas sync, con una cuenta Google secundaria. '
                f'Cierra este Chrome antes de iniciar captura administrada.'
            )
        else:
            self._login_status = f"No pude abrir el perfil IA: {result.get('detail', 'sin detalle')}"
        self.dataChanged.emit()

    @Slot(str)
    def recreateProfile(self, site_id: str) -> None:
        if self._session_active:
            self._login_status = 'Deten la ensenanza activa antes de recrear el perfil IA.'
            self.dataChanged.emit()
            return
        site_key = site_id.strip() or self._selected_site_id
        policy = self.site_policy_registry.get_policy(site_key)
        if policy is None:
            self._login_status = f'No existe politica para {site_key}.'
            self.dataChanged.emit()
            return
        profile = self._build_profile_config(policy)
        result = self.profile_manager.recreate_profile(profile)
        self.refresh()
        self._login_status = (
            f'Perfil IA {result.profile_id} recreado limpio. Abrelo manualmente, inicia sesion de nuevo y luego reutilizalo para ensenar. '
            f'Google principal no recomendado.'
        )
        self.dataChanged.emit()

    @Slot(str)
    def createPlaceholderEpisode(self, title: str) -> None:
        title = title.strip() or 'Sesion guiada'
        self.episode_repository.create_episode(
            title=title,
            tags=['teach_session', f'site:{self._selected_site_id}'],
            notes='Borrador creado desde Estudio de ensenanza.',
        )
        self.refresh()

    @Slot(str, str, str)
    def savePolicyDraft(self, site_id: str, login_selector: str, logout_selector: str) -> None:
        policy = self.site_policy_registry.get_policy(site_id.strip() or self._selected_site_id)
        if policy is None:
            return
        updated = policy.model_copy(
            update={
                'login_selector': login_selector.strip() or policy.login_selector,
                'logout_selector': logout_selector.strip() or policy.logout_selector,
            }
        )
        self.site_policy_registry.upsert_policy(updated)
        self._selected_site_id = updated.site_id
        self.refresh()

    @Slot(str, str, str, str, str, str, bool, bool, bool)
    def startTeaching(
        self,
        title: str,
        target_label: str,
        start_url: str,
        objective: str,
        expected_outcome: str,
        notes: str,
        capture_visible: bool,
        capture_background: bool,
        capture_api: bool,
    ) -> None:
        policy = self._apply_policy_selection(self._infer_policy(start_url=start_url, target_label=target_label))
        if policy is None:
            self._teaching_status = 'No hay politica disponible para iniciar la ensenanza.'
            self.dataChanged.emit()
            return
        lesson_title = title.strip() or 'Sesion guiada'
        runtime_policy = self._build_runtime_policy(policy, capture_background, capture_api)
        resolved_url = self._resolve_start_url(start_url, runtime_policy)
        brief_payload = self._build_teaching_brief(
            lesson_title=lesson_title,
            target_label=target_label,
            start_url=resolved_url,
            objective=objective,
            expected_outcome=expected_outcome,
            notes=notes,
            capture_visible=capture_visible,
            capture_background=capture_background,
            capture_api=capture_api,
            policy=runtime_policy,
        )
        try:
            self._session_finalizing = False
            self._capture_progress_text = ''
            self._session_health = {}
            self._live_incident_text = 'Sin incidencias.'
            profile = self._build_profile_config(runtime_policy)
            episode, session_state = self.browser_teach_session_service.start_session(
                title=lesson_title,
                url=resolved_url,
                profile_config=profile,
                site_policy=runtime_policy,
                tags=[f'target:{(target_label or runtime_policy.display_name).strip() or runtime_policy.site_id}', 'teach_mode:browser'],
            )
            self.browser_teach_session_service.record_step(
                action_type='teaching_brief',
                target=(target_label.strip() or runtime_policy.display_name),
                text_value=objective.strip() or expected_outcome.strip() or None,
                metadata={
                    'capture_channel': CaptureChannel.VISIBLE.value if capture_visible else CaptureChannel.BACKGROUND.value,
                    'textPreview': (objective.strip() or expected_outcome.strip() or notes.strip())[:180],
                    'teaching_brief': brief_payload,
                    'target_label': target_label.strip(),
                    'element_role': 'teaching_brief',
                },
                capture_screenshot=False,
            )
            self._save_teaching_brief_artifact(episode.episode_id, runtime_policy, brief_payload, capture_background, capture_api)
            self._session_active = True
            self._session_paused = False
            self._active_episode_id = episode.episode_id
            self._selected_history_episode_id = episode.episode_id
            self._active_site_policy = runtime_policy
            self.refresh()
            self._login_status = session_state.reason or 'Sesion ligera lanzada en navegador administrado.'
            self._teaching_status = f'Ensenanza iniciada para {lesson_title}. Ya se esta recopilando visible, segundo plano y API segun tu seleccion.'
            self._teaching_summary = (
                f'Episodio activo: {episode.episode_id} | inicio {resolved_url} | '
                f'canales seleccionados: {self._format_capture_channels(capture_visible, capture_background, capture_api)}'
            )
            self.dataChanged.emit()
        except Exception as exc:
            self._session_active = False
            self._session_paused = False
            self._session_finalizing = False
            self._active_episode_id = ''
            self._active_site_policy = None
            self._capture_progress_text = ''
            self._session_health = {}
            self._live_incident_text = 'Sin incidencias.'
            error_text = str(exc)
            if 'Acceso denegado' in error_text or '[WinError 5]' in error_text:
                self.refresh()
                self._teaching_status = 'No pude iniciar la ensenanza porque el navegador administrado no pudo abrir la sesion ligera.'
                self._teaching_summary = 'Cierra otros navegadores pesados, espera unos segundos y vuelve a intentar. Si persiste, revisamos Playwright, Chromium o la pagina objetivo.'
                self._login_status = 'Bloqueo detectado al abrir la sesion ligera administrada.'
                self.dataChanged.emit()
                return
            self._teaching_status = f'No pude iniciar la ensenanza: {exc}'
            self._teaching_summary = 'Revisa Playwright, Chromium y la URL inicial antes de volver a intentar.'
            self.dataChanged.emit()
    @Slot()
    def stopTeaching(self) -> None:
        if not self._session_active:
            self._teaching_status = 'No hay una ensenanza activa para detener.'
            self.dataChanged.emit()
            return
        finalize_started = time.monotonic()
        self._session_finalizing = True
        self._capture_progress_text = 'Finalizando sesion: consolidando visible, segundo plano y API inteligente.'
        self._teaching_status = 'Finalizando captura. La interfaz queda bloqueada mientras se consolida el replay.'
        self.dataChanged.emit()
        self._process_ui_events()
        episode_id = self._active_episode_id
        try:
            self._capture_progress_text = 'Cerrando navegador y reuniendo observaciones recuperables.'
            self.dataChanged.emit()
            self._process_ui_events()
            bundle, session_state = self.browser_teach_session_service.stop_session()
            policy = self._active_site_policy or self._current_policy()
            episode_id = bundle.episode_id
            self._capture_progress_text = 'Empaquetando resumen y reconstruyendo historial guiado.'
            self.dataChanged.emit()
            self._process_ui_events()
            steps = self.episode_repository.load_episode(episode_id)
            artifacts = self.artifact_repository.list_for_episode(episode_id)
            learning_packet = self.browser_learning_assembler.assemble(
                episode_id=episode_id,
                site_policy=policy,
                steps=steps,
                artifacts=artifacts,
                bundle=bundle,
                redaction_summary=self.browser_teach_session_service.redaction_summary,
            )
            learning_packet = self._save_learning_bundle(episode_id, policy, learning_packet)
            final_artifacts = self.artifact_repository.list_for_episode(episode_id)
            status = (learning_packet.get('capture_stats') or {}).get('status', 'completed')
            replay_quality = self._infer_replay_quality(steps, final_artifacts, learning_packet)
            runtime_snapshot = {
                **(learning_packet.get('capture_stats') or {}),
                'episode_id': episode_id,
                'site_id': policy.site_id if policy is not None else self._runtime_site_id(),
                'replay_quality': replay_quality,
                'has_recoverable_replay': bool(steps or final_artifacts),
                'duration_ms': int(max(0.0, (time.monotonic() - finalize_started) * 1000.0)),
            }
            self._capture_runtime_incidents(runtime_snapshot)
            summary_text = (
                f'Pasos: {len(steps)} | artefactos: {len(final_artifacts)} | '
                f'visible: {(learning_packet.get("capture_stats") or {}).get("visible_step_count", 0)} | '
                f'capturas: {(learning_packet.get("capture_stats") or {}).get("screenshot_count", 0)} | '
                f'API guardada: {(learning_packet.get("capture_stats") or {}).get("api_saved_count", 0)} | '
                f'replay: {replay_quality}'
            )
            cross_check_summary = dict(learning_packet.get('cross_check_summary') or {})
            if cross_check_summary:
                summary_text += (
                    f" | cruce visual: {cross_check_summary.get('confirmed_count', 0)} confirmado(s), "
                    f"{cross_check_summary.get('doubtful_count', 0)} dudoso(s), "
                    f"{cross_check_summary.get('insufficient_count', 0)} insuficiente(s)"
                )
            audit_summary = str((learning_packet.get('metadata') or {}).get('audit_summary') or '')
            if audit_summary:
                summary_text += f' | auditoria: {audit_summary}'
            self._record_teaching_dossier(
                episode_id=episode_id,
                title=policy.display_name if policy is not None else 'Ensenanza',
                status=RunStatus.PARTIAL if status == 'partial_recovery' else RunStatus.SUCCESS,
                summary=summary_text,
                metrics={**runtime_snapshot, 'has_recoverable_replay': bool(steps or final_artifacts)},
                steps=steps,
                artifacts=final_artifacts,
            )
            self._session_active = False
            self._session_paused = False
            self._session_finalizing = False
            self._active_episode_id = episode_id
            self._selected_history_episode_id = episode_id
            self._active_site_policy = None
            self.refresh()
            self._login_status = session_state.reason if session_state is not None else 'Sesion detenida correctamente.'
            if status == 'partial_recovery':
                self._teaching_status = f'Ensenanza detenida con recuperacion parcial para {episode_id}.'
            else:
                self._teaching_status = f'Ensenanza detenida y recopilada para {episode_id}.'
            self._teaching_summary = summary_text
            self._capture_progress_text = 'Sesion consolidada y replay listo para historial.'
            self.dataChanged.emit()
        except Exception as exc:
            self._session_active = False
            self._session_paused = False
            self._session_finalizing = False
            self._active_site_policy = None
            self._capture_progress_text = f'Recuperando replay parcial tras el error: {exc}'
            replay_recovered = self._recover_partial_teaching(episode_id)
            partial_steps = self.episode_repository.load_episode(episode_id)
            partial_artifacts = self.artifact_repository.list_for_episode(episode_id)
            runtime_snapshot = {
                'episode_id': episode_id,
                'site_id': self._runtime_site_id(),
                'status': 'partial_recovery',
                'has_recoverable_replay': bool(partial_steps or partial_artifacts),
                'replay_quality': self._infer_replay_quality(partial_steps, partial_artifacts, {'capture_stats': {'status': 'partial_recovery'}}),
                'duration_ms': int(max(0.0, (time.monotonic() - finalize_started) * 1000.0)),
            }
            self._capture_runtime_incidents(runtime_snapshot)
            self.refresh()
            self._record_teaching_dossier(
                episode_id=episode_id,
                title='Ensenanza parcial',
                status=RunStatus.PARTIAL,
                summary=replay_recovered,
                error_summary=str(exc),
                metrics={**runtime_snapshot, 'has_recoverable_replay': bool(self._replay_steps)},
                steps=partial_steps,
                artifacts=partial_artifacts,
            )
            self._teaching_status = f'La finalizacion encontro un problema, pero intente recuperar la ensenanza: {exc}'
            self._teaching_summary = replay_recovered
            self.dataChanged.emit()
    @Slot()
    def pollTeachingSession(self) -> None:
        if not self._session_active or self._session_paused or self._session_finalizing:
            return
        poll = getattr(self.browser_teach_session_service, 'poll_live_capture', None)
        if not callable(poll):
            return
        try:
            runtime_snapshot = poll() or {}
            self._capture_runtime_incidents(runtime_snapshot)
            self.refresh()
            self._teaching_summary = (
                f'Episodio activo: {self._active_episode_id} | '
                f'visible: {self._security_state.get("visible_step_count", 0)} | '
                f'capturas: {self._security_state.get("screenshot_count", 0)} | '
                f'frames: {self._security_state.get("frames_detected", 0)} | '
                f'salud: {self._session_health.get("health_label", "Sin incidencias")}'
            )
            self.dataChanged.emit()
        except Exception as exc:
            self._teaching_status = f'La captura en vivo encontro una incidencia recuperable: {exc}'
            self.dataChanged.emit()

    @Slot(str)
    def recordUserClue(self, clue_text: str) -> None:
        text_value = clue_text.strip()
        if not text_value:
            self._teaching_status = 'Escribe una pista breve antes de registrarla.'
            self.dataChanged.emit()
            return
        episode_id = self._active_episode_id or self._selected_history_episode_id or None
        site_id = self._runtime_site_id() or 'generic_web'
        clue = self.user_clue_service.attach_to_latest_context(
            text=text_value,
            site_id=site_id,
            episode_id=episode_id,
        )
        self.refresh()
        self._teaching_status = 'Pista del usuario registrada y enlazada a la evidencia mas cercana.'
        self._teaching_summary = f'Pista guardada: {clue.text}'
        self.dataChanged.emit()

    @Slot()
    def pauseTeaching(self) -> None:
        if not self._session_active:
            self._teaching_status = 'No hay una ensenanza activa para pausar.'
            self.dataChanged.emit()
            return
        if self._session_paused:
            self._teaching_status = 'La ensenanza ya esta en pausa.'
            self.dataChanged.emit()
            return
        if hasattr(self.browser_teach_session_service, 'pause_session'):
            self.browser_teach_session_service.pause_session()
        self._session_paused = True
        self._teaching_status = 'Captura pausada. Ya no se agregaran eventos nuevos hasta que reanudes.'
        self._teaching_summary = 'La sesion sigue abierta en el navegador administrado y puede reanudarse cuando quieras.'
        self.dataChanged.emit()

    @Slot()
    def resumeTeaching(self) -> None:
        if not self._session_active:
            self._teaching_status = 'No hay una ensenanza activa para reanudar.'
            self.dataChanged.emit()
            return
        if not self._session_paused:
            self._teaching_status = 'La ensenanza ya esta activa.'
            self.dataChanged.emit()
            return
        if hasattr(self.browser_teach_session_service, 'resume_session'):
            self.browser_teach_session_service.resume_session()
        self._session_paused = False
        self._teaching_status = 'Captura reanudada. Los eventos vuelven a registrarse.'
        self._teaching_summary = 'Puedes seguir ensenando y luego detener para recopilar el replay guiado.'
        self.dataChanged.emit()

    def _current_policy(self) -> SitePolicy | None:
        policy = self.site_policy_registry.get_policy(self._selected_site_id)
        if policy is not None:
            return policy
        policies = self.site_policy_registry.list_policies()
        return policies[0] if policies else None

    def _build_profile_config(self, policy: SitePolicy) -> BrowserProfileConfig:
        return BrowserProfileConfig(
            profile_id=f'state_{policy.site_id}',
            site_id=policy.site_id,
            channel='chrome',
            user_data_dir=None,
            storage_state_path=str(Path(self.config.browser_states_dir) / f'{policy.site_id}.json'),
            source_user_data_dir=None,
            source_profile_dir=None,
            login_check_selector=policy.login_selector,
            logout_check_selector=policy.logout_selector,
            persist_strategy=PersistStrategy.STORAGE_STATE_ONLY,
            headless=False,
        )

    def _build_runtime_policy(self, policy: SitePolicy, capture_background: bool, capture_api: bool) -> SitePolicy:
        return policy.model_copy(
            update={
                'capture_dom': capture_background,
                'capture_console': capture_background,
                'capture_storage': capture_background,
                'capture_network': capture_api,
            }
        )

    def _resolve_start_url(self, start_url: str, policy: SitePolicy) -> str:
        value = start_url.strip()
        if value:
            if value.startswith(('http://', 'https://', 'about:', 'file://')):
                return value
            if '.' in value and ' ' not in value:
                return f'https://{value}'
        if policy.login_url:
            return policy.login_url
        if policy.domains:
            candidate = policy.domains[0]
            if candidate and candidate != '*':
                return f'https://{candidate}' if not candidate.startswith('http') else candidate
        return 'about:blank'

    def _build_teaching_brief(
        self,
        *,
        lesson_title: str,
        target_label: str,
        start_url: str,
        objective: str,
        expected_outcome: str,
        notes: str,
        capture_visible: bool,
        capture_background: bool,
        capture_api: bool,
        policy: SitePolicy,
    ) -> dict:
        return {
            'lesson_title': lesson_title,
            'target_label': target_label.strip(),
            'start_url': start_url,
            'objective': objective.strip(),
            'expected_outcome': expected_outcome.strip(),
            'notes': notes.strip(),
            'site_id': policy.site_id,
            'display_name': policy.display_name,
            'capture_channels': {
                'visible': capture_visible,
                'background': capture_background,
                'api': capture_api,
            },
            'capture_mode': 'browser_live',
        }

    def _save_teaching_brief_artifact(self, episode_id: str, policy: SitePolicy, brief_payload: dict, capture_background: bool, capture_api: bool) -> None:
        self.artifact_repository.save(
            SessionArtifact(
                episode_id=episode_id,
                kind='teaching_brief',
                path=f'{episode_id}/brief/teaching_brief.json',
                metadata={
                    'artifact_kind': 'teaching_brief',
                    'capture_channel': CaptureChannel.BACKGROUND.value if capture_background else CaptureChannel.VISIBLE.value,
                    'site_id': policy.site_id,
                    'redacted': True,
                    'content_type': 'application/json',
                    'api_requested': capture_api,
                },
            ),
            payload=brief_payload,
        )

    def _load_teaching_brief_payload(self, episode_id: str) -> dict:
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        brief_artifact = next((item for item in reversed(artifacts) if item.kind == 'teaching_brief'), None)
        payload = self._load_artifact_payload(brief_artifact)
        return dict(payload or {})

    def _policy_to_card(self, policy: SitePolicy) -> dict:
        return {
            'site_id': policy.site_id,
            'display_name': policy.display_name,
            'domains': ', '.join(policy.domains),
            'login_selector': policy.login_selector or 'sin selector',
            'logout_selector': policy.logout_selector or 'sin selector',
            'capture_mode': self._capture_mode_label(policy),
            'sensitive_rules': len(policy.sensitive_selectors) + len(policy.sensitive_names),
        }

    def _profile_to_card(self, payload: dict) -> dict:
        state_path = payload.get('storage_state_path') or ''
        return {
            'profile_id': payload.get('profile_id', 'sin_nombre'),
            'site_id': payload.get('site_id', 'generic_web'),
            'mode': payload.get('mode', 'fresh_profile'),
            'user_data_dir': payload.get('user_data_dir', ''),
            'storage_state_path': state_path,
            'has_state': bool(state_path and Path(state_path).exists()),
            'warning': payload.get('warning', ''),
            'account_hint': 'Usa una cuenta Google secundaria solo si necesitas sincronizacion. La principal no se recomienda.',
            'healthy': payload.get('healthy', True),
            'health_detail': payload.get('health_detail', 'Sin diagnostico del perfil.'),
        }

    def _build_channel_cards(self, artifacts) -> list[dict]:
        counts = {'visible': 0, 'background': 0, 'api': 0}
        for artifact in artifacts:
            channel = artifact.metadata.get('capture_channel')
            if channel in counts:
                counts[channel] += 1
        return [
            {'key': 'visible', 'title': 'Visible', 'count': counts['visible'], 'detail': 'Timeline humano, screenshots y pasos redactados.'},
            {'key': 'background', 'title': 'Segundo plano', 'count': counts['background'], 'detail': 'DOM, storage metadata, cookies sin valor y consola.'},
            {'key': 'api', 'title': 'API', 'count': counts['api'], 'detail': 'Requests y responses con headers y cuerpos filtrados.'},
        ]

    def _load_review_steps(self, episodes) -> list[dict]:
        review_steps: list[dict] = []
        for episode in episodes[:3]:
            for step in self.episode_repository.load_episode(episode.episode_id)[-6:]:
                review_steps.append(self._step_to_replay_item(step, review_index=len(review_steps) + 1, compact=True))
        return review_steps[:12]

    def _build_teaching_history(self, episodes) -> list[dict]:
        history: list[dict] = []
        for episode in episodes:
            if not self._is_teaching_episode(episode):
                continue
            steps = self.episode_repository.load_episode(episode.episode_id)
            episode_artifacts = self.artifact_repository.list_for_episode(episode.episode_id)
            channels = sorted({artifact.metadata.get('capture_channel', 'visible') for artifact in episode_artifacts if artifact.metadata.get('capture_channel')})
            brief = self._load_artifact_payload(next((item for item in episode_artifacts if item.kind == 'teaching_brief'), None)) or {}
            learning_bundle = self._load_artifact_payload(next((item for item in reversed(episode_artifacts) if item.kind == 'learning_bundle'), None)) or {}
            site_tag = next((tag.split(':', 1)[1] for tag in episode.tags if tag.startswith('site:')), brief.get('site_id', 'generic_web'))
            gallery = self._load_replay_gallery(episode.episode_id)
            replay_preview = gallery['timeline_steps']
            visual_summary = dict(gallery.get('summary') or learning_bundle.get('visual_summary') or {})
            fallback_learning = self._derive_learning_from_replay(
                replay_steps=replay_preview,
                artifacts=episode_artifacts,
                site_id=site_tag,
                display_name=brief.get('display_name') or brief.get('target_label') or episode.title,
            )
            if self.replay_learning_feedback_service is not None:
                learning_bundle = self.replay_learning_feedback_service.apply_annotations_to_learning(learning_bundle or fallback_learning, visual_summary)
            learning_readiness = learning_bundle.get('learning_readiness') or fallback_learning['learning_readiness']
            login_learning = learning_bundle.get('login_learning') or fallback_learning['login_learning']
            screenshot_count = sum(1 for step in steps if step.screenshot_path)
            visible_step_count = sum(1 for step in steps if (step.metadata or {}).get('capture_channel') == CaptureChannel.VISIBLE.value and step.action_type != 'teaching_brief')
            api_artifact_count = sum(1 for artifact in episode_artifacts if artifact.kind == 'network_exchange' or artifact.metadata.get('capture_channel') == CaptureChannel.API.value)
            status = self._infer_teaching_status(steps, episode_artifacts, learning_bundle)
            has_recoverable_replay = bool(steps or episode_artifacts)
            incidents = self.hidden_incident_repository.find_by_episode(episode.episode_id)
            replay_quality = self._infer_replay_quality(steps, episode_artifacts, learning_bundle)
            history.append(
                {
                    'episode_id': episode.episode_id,
                    'title': episode.title,
                    'updated_at': episode.updated_at_utc.isoformat(),
                    'step_count': episode.step_count,
                    'visible_step_count': visible_step_count,
                    'artifact_count': len(episode_artifacts),
                    'api_artifact_count': api_artifact_count,
                    'screenshot_count': screenshot_count,
                    'incident_count': len(incidents),
                    'replay_quality': replay_quality,
                    'channels': ', '.join(channels) or 'sin canales',
                    'site_id': site_tag,
                    'target_label': brief.get('target_label', ''),
                    'objective': brief.get('objective', ''),
                    'expected_outcome': brief.get('expected_outcome', ''),
                    'notes': episode.notes,
                    'capture_mode': brief.get('capture_mode', 'browser_live'),
                    'learning_summary': learning_bundle.get('action_counts', {}),
                    'redacted_steps': (learning_bundle.get('redaction_summary') or {}).get('redacted_steps', 0),
                    'redacted_network_fields': (learning_bundle.get('redaction_summary') or {}).get('redacted_network_fields', 0),
                    'status': status,
                    'has_recoverable_replay': has_recoverable_replay,
                    'relevant_step_count': learning_bundle.get('relevant_step_count', fallback_learning['relevant_step_count']),
                    'screenshot_step_count': learning_bundle.get('screenshot_step_count', fallback_learning['screenshot_step_count']),
                    'learning_readiness': learning_readiness.get('status', fallback_learning['learning_readiness']['status']),
                    'learning_summary_text': learning_readiness.get('summary', fallback_learning['learning_readiness']['summary']),
                    'login_learning_status': login_learning.get('status', fallback_learning['login_learning']['status']),
                    'login_learning_summary': login_learning.get('summary', fallback_learning['login_learning']['summary']),
                    'suggested_commands': learning_bundle.get('suggested_commands') or login_learning.get('suggested_commands') or fallback_learning['suggested_commands'],
                    'visual_alignment_score': float(visual_summary.get('visual_alignment_score', learning_readiness.get('visual_alignment_score', 0.0)) or 0.0),
                    'learning_coverage_score': float(visual_summary.get('learning_coverage_score', learning_readiness.get('learning_coverage_score', 0.0)) or 0.0),
                    'manual_correction_count': int(visual_summary.get('manual_correction_count', learning_readiness.get('manual_correction_count', 0)) or 0),
                    'critical_object_coverage': float(visual_summary.get('critical_object_coverage', learning_readiness.get('critical_object_coverage', 0.0)) or 0.0),
                    'login_visual_completeness': float(visual_summary.get('login_visual_completeness', login_learning.get('login_visual_completeness', 0.0)) or 0.0),
                    'green_count': int(visual_summary.get('green_count', 0) or 0),
                    'orange_count': int(visual_summary.get('orange_count', 0) or 0),
                    'red_count': int(visual_summary.get('red_count', 0) or 0),
                    'useful_frame_count': int(visual_summary.get('useful_frames', 0) or 0),
                    'contextual_frame_count': int(visual_summary.get('contextual_frames', 0) or 0),
                    'critical_objects': list(visual_summary.get('critical_objects') or []),
                    'corrected_objects': list(visual_summary.get('corrected_objects') or []),
                    'gaps': list(visual_summary.get('gaps') or []),
                }
            )
        return history

    def _load_replay_gallery(self, episode_id: str) -> dict:
        replay = self._build_raw_replay_steps(episode_id)
        annotations = self.replay_annotation_service.list_for_episode(episode_id) if self.replay_annotation_service is not None else []
        if self.replay_visual_assembler is None:
            return {
                'timeline_steps': replay,
                'frames': [],
                'summary': {},
            }
        base_gallery = self.replay_visual_assembler.build_gallery(
            episode_id=episode_id,
            replay_steps=replay,
            annotations=annotations,
        )
        if self.audit_teach_verification_service is None:
            return base_gallery
        learning_packet: dict = {}
        interaction_episode = None
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        bundle_artifact = next((item for item in reversed(artifacts) if item.kind == 'learning_bundle'), None)
        if bundle_artifact is not None:
            learning_packet = self._load_artifact_payload(bundle_artifact) or {}
        if self.interaction_learning_service is not None:
            interaction_id = str(
                learning_packet.get('interaction_episode_id')
                or (learning_packet.get('metadata') or {}).get('interaction_episode_id')
                or ''
            ).strip()
            if interaction_id:
                interaction_episode = self.interaction_learning_service.repository.get_interaction_episode(interaction_id)
        try:
            objective = str(learning_packet.get('objective') or '')
            if not objective and interaction_episode is not None:
                objective = interaction_episode.objective
            audit_result = self.audit_teach_verification_service.verify_replay(
                episode_id=episode_id,
                replay_steps=replay,
                annotations=annotations,
                learning_packet=learning_packet,
                interaction_episode=interaction_episode,
                objective=objective,
            )
            return self.replay_visual_assembler.assemble_with_audit(
                episode_id=episode_id,
                replay_steps=replay,
                annotations=annotations,
                audit_annotations=audit_result.audit_annotations,
                audit_report=audit_result.audit_report,
                cross_check_result=audit_result.cross_check_result,
            ).model_dump(mode='json')
        except Exception as exc:
            summary = dict(base_gallery.get('summary') or {})
            metadata = dict(summary.get('metadata') or {})
            metadata['audit_error'] = str(exc)
            summary['metadata'] = metadata
            base_gallery['summary'] = summary
            return base_gallery

    def _derive_learning_from_replay(self, *, replay_steps: list[dict], artifacts: list[SessionArtifact], site_id: str, display_name: str) -> dict:
        relevant_count = sum(1 for item in replay_steps if item.get('learning_relevant'))
        screenshot_count = sum(1 for item in replay_steps if item.get('has_screenshot'))
        roles = {str(item.get('element_role') or '').lower() for item in replay_steps}
        actions = {str(item.get('action_type') or '').lower() for item in replay_steps}
        email_or_user = bool({'email_input', 'username_input'} & roles)
        password = 'password_input' in roles
        submit = 'submit' in actions or any(
            str(item.get('action_type') or '').lower() == 'keydown' and str(item.get('text') or '').lower() == 'enter'
            for item in replay_steps
        )
        auth_blob_parts: list[str] = []
        for artifact in artifacts:
            payload = self._load_artifact_payload(artifact) or {}
            if artifact.kind == 'dom_snapshot':
                auth_blob_parts.extend([
                    str(payload.get('title') or ''),
                    str(payload.get('visible_text_excerpt') or ''),
                    str(payload.get('html_excerpt') or ''),
                ])
            elif artifact.kind == 'network_exchange':
                auth_blob_parts.extend([
                    str(payload.get('url') or ''),
                    str(payload.get('graphql_operation') or ''),
                ])
        auth_blob = ' '.join(auth_blob_parts).lower()
        auth_keywords = getattr(self.browser_learning_assembler, 'AUTH_KEYWORDS', set())
        authenticated = any(keyword in auth_blob for keyword in auth_keywords)
        signals: list[str] = []
        missing: list[str] = []
        if email_or_user:
            signals.append('campo de correo o usuario detectado')
        else:
            missing.append('falta detectar un campo de correo o usuario')
        if password:
            signals.append('campo de contrasena detectado')
        else:
            missing.append('falta detectar un campo de contrasena')
        if submit:
            signals.append('envio de login detectado')
        else:
            missing.append('falta detectar la accion de envio del login')
        if authenticated:
            signals.append('evidencia de sesion autenticada detectada')
        else:
            missing.append('falta evidencia solida de que la sesion quedo autenticada')
        if email_or_user and password and submit and authenticated:
            login_status = 'ready'
            login_summary = 'La ensenanza ya contiene senales suficientes para entender el inicio de sesion como flujo reutilizable, aunque todavia debe conectarse a la ejecucion automatizada.'
        elif sum(bool(flag) for flag in [email_or_user, password, submit, authenticated]) >= 2:
            login_status = 'partial'
            login_summary = 'La ensenanza entiende partes importantes del login, pero todavia no conviene asumir ejecucion automatica completa.'
        else:
            login_status = 'insufficient'
            login_summary = 'La ensenanza aun no contiene suficientes senales para afirmar que el login fue aprendido como tarea.'
        if relevant_count >= 4 and screenshot_count >= 2 and login_status == 'ready':
            learning_status = 'ready'
            learning_summary = 'La ensenanza quedo bien capturada y marcada como fuerte para aprendizaje.'
        elif relevant_count >= 2 or login_status in {'ready', 'partial'}:
            learning_status = 'partial'
            learning_summary = 'La ensenanza ya aporta senales utiles, pero todavia necesita mas evidencia o conexion con ejecucion.'
        else:
            learning_status = 'insufficient'
            learning_summary = 'La ensenanza aun es demasiado pobre para quedar lista como habilidad ejecutable.'
        display = display_name or site_id or 'sitio ensenado'
        return {
            'relevant_step_count': relevant_count,
            'screenshot_step_count': screenshot_count,
            'learning_readiness': {
                'status': learning_status,
                'summary': learning_summary,
            },
            'login_learning': {
                'status': login_status,
                'summary': login_summary,
                'signals': signals,
                'missing_signals': missing,
                'suggested_commands': [f'Abrir {display}', f'Abrir {display} e iniciar sesion'],
            },
            'suggested_commands': [f'Abrir {display}', f'Abrir {display} e iniciar sesion'],
        }

    def _sync_selected_teaching_history(self) -> None:
        if not self._teaching_history:
            self._selected_teaching_history = {}
            self._replay_steps = []
            self._replay_frames = []
            self._replay_visual_summary = {}
            self._selected_replay_frame_index = 0
            self._selected_replay_step_index = 0
            self._selected_replay_annotation_id = ''
            self._replay_status_filter = 'all'
            return
        selected_id = self._selected_history_episode_id or self._active_episode_id
        selected = next((item for item in self._teaching_history if item['episode_id'] == selected_id), None)
        if selected is None:
            selected = next((item for item in self._teaching_history if item.get('has_recoverable_replay')), self._teaching_history[0])
            self._selected_history_episode_id = selected['episode_id']
        self._selected_teaching_history = selected
        gallery = self._load_replay_gallery(selected['episode_id'])
        self._replay_steps = gallery.get('timeline_steps', [])
        self._replay_frames = gallery.get('frames', [])
        self._replay_visual_summary = gallery.get('summary', {})
        self._selected_replay_frame_index = 0
        if self._replay_steps:
            self._selected_replay_step_index = 0
            first_frame_index = self._replay_steps[0].get('frame_index', -1)
            if isinstance(first_frame_index, int) and first_frame_index >= 0:
                self._selected_replay_frame_index = first_frame_index
        else:
            self._selected_replay_step_index = 0
        self._selected_replay_annotation_id = ''
        self._replay_status_filter = 'all'

    def _build_replay_steps(self, episode_id: str) -> list[dict]:
        return self._load_replay_gallery(episode_id).get('timeline_steps', [])

    def _build_raw_replay_steps(self, episode_id: str) -> list[dict]:
        replay: list[dict] = []
        for step in self.episode_repository.load_episode(episode_id):
            replay.extend(self._step_to_replay_items(step, start_index=len(replay) + 1, compact=False))
        has_real_visible = any(item.get('has_screenshot') or item.get('action_type') not in {'teaching_brief', 'frame_fallback'} for item in replay)
        if has_real_visible:
            return self._prune_replay_steps(replay)
        recovered = self._recover_partial_replay_steps(episode_id)
        if not replay:
            return self._prune_replay_steps(recovered)
        merged = list(replay)
        for item in recovered:
            if item['action_type'] == 'teaching_brief':
                continue
            item = dict(item)
            item['step_index'] = len(merged) + 1
            merged.append(item)
            if len(merged) >= 36:
                break
        return self._prune_replay_steps(merged)

    def _prune_replay_steps(self, replay: list[dict]) -> list[dict]:
        if not replay:
            return []
        structured_frames = {
            item.get('frame_url')
            for item in replay
            if item.get('capture_source') == 'frame_fallback_structured' and item.get('frame_url')
        }
        if not structured_frames:
            return replay
        filtered: list[dict] = []
        for item in replay:
            if (
                item.get('action_type') == 'frame_fallback'
                and item.get('frame_url') in structured_frames
                and not item.get('has_screenshot')
            ):
                continue
            filtered.append(dict(item))
        for index, item in enumerate(filtered, start=1):
            item['step_index'] = index
        return filtered

    def _record_teaching_dossier(
        self,
        *,
        episode_id: str,
        title: str,
        status: RunStatus,
        summary: str,
        metrics: dict,
        steps: list,
        artifacts: list[SessionArtifact],
        error_summary: str = '',
    ) -> None:
        if self.execution_dossier_service is None or not episode_id:
            return
        try:
            self.execution_dossier_service.build_for_teaching_session(
                episode_id=episode_id,
                title=title,
                status=status,
                metrics=metrics,
                steps=steps,
                artifacts=artifacts,
                summary=summary,
                error_summary=error_summary,
            )
        except Exception:
            return

    def _recover_partial_teaching(self, episode_id: str) -> str:
        if not episode_id:
            return 'No habia episodio activo para recuperar.'
        policy = self._active_site_policy or self._current_policy()
        steps = self.episode_repository.load_episode(episode_id)
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        if policy is not None and artifacts:
            partial_packet = {
                'episode_id': episode_id,
                'site_id': policy.site_id,
                'display_name': policy.display_name,
                'capture_channels': sorted({artifact.metadata.get('capture_channel', 'visible') for artifact in artifacts}),
                'action_counts': {},
                'artifact_count': len(artifacts),
                'step_count': len(steps),
                'capture_stats': {'status': 'partial_recovery'},
                'redaction_summary': self.browser_teach_session_service.redaction_summary.model_dump(mode='json'),
            }
            try:
                self._save_learning_bundle(episode_id, policy, partial_packet)
            except Exception:
                pass
        recovered = self._recover_partial_replay_steps(episode_id)
        if self._selected_history_episode_id != episode_id:
            self._selected_history_episode_id = episode_id
        return f'Recuperacion parcial: {len(recovered)} pasos o artefactos quedaron listos para replay.'

    def _recover_partial_replay_steps(self, episode_id: str) -> list[dict]:
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        replay: list[dict] = []
        for artifact in artifacts:
            item = self._build_artifact_replay_item(artifact, review_index=len(replay) + 1)
            if item is not None:
                replay.append(item)
            if len(replay) >= 12:
                break
        return replay

    def _build_artifact_replay_item(self, artifact: SessionArtifact, *, review_index: int) -> dict | None:
        payload = self._load_artifact_payload(artifact) or {}
        channel = artifact.metadata.get('capture_channel') or 'background'
        detail = 'Artefacto recuperado para replay parcial.'
        text = artifact.kind.replace('_', ' ')
        element_role = artifact.kind
        if artifact.kind == 'teaching_brief':
            detail = payload.get('objective') or payload.get('expected_outcome') or 'Brief de ensenanza recuperado.'
            text = payload.get('target_label') or payload.get('lesson_title') or 'Brief de ensenanza'
            element_role = 'teaching_brief'
        elif artifact.kind == 'dom_snapshot':
            detail = (payload.get('visible_text_excerpt') or payload.get('title') or 'Snapshot de segundo plano recuperado.')[:180]
            text = payload.get('title') or payload.get('url') or 'DOM snapshot'
            element_role = 'background'
        elif artifact.kind == 'network_exchange':
            detail = f"{payload.get('method', 'GET')} {payload.get('url', '')} | estado {payload.get('status_code', 'n/d')}"
            text = payload.get('graphql_operation') or payload.get('url') or 'API exchange'
            element_role = 'api'
        elif artifact.kind == 'learning_bundle':
            readiness = payload.get('learning_readiness') or {}
            login_learning = payload.get('login_learning') or {}
            detail = readiness.get('summary') or login_learning.get('summary') or 'Resumen de aprendizaje recuperado.'
            text = payload.get('display_name') or artifact.kind
            element_role = 'learning_bundle'
        else:
            detail = str(payload)[:180] if payload else detail
        synthetic_step_id = f"artifact::{artifact.artifact_id}"
        return {
            'step_id': synthetic_step_id,
            'artifact_id': artifact.artifact_id,
            'step_index': review_index,
            'episode_id': artifact.episode_id,
            'action_type': artifact.kind,
            'target': artifact.path,
            'text': text,
            'timestamp': artifact.created_at_utc.isoformat(),
            'sensitive': False,
            'channel': channel,
            'element_role': element_role,
            'selector': artifact.path,
            'detail': detail,
            'input_type': '',
            'button_text': '',
            'aria_label': '',
            'placeholder': '',
            'frame_url': '',
            'frame_name': '',
            'capture_source': 'artifact_recovery',
            'screenshot_reason': '',
            'key_display': '',
            'screenshot_name': '',
            'screenshot_path': '',
            'screenshot_url': '',
            'linked_screenshot_id': artifact.artifact_id,
            'group_key': f"artifact::{artifact.artifact_id}",
            'has_screenshot': False,
            'learning_relevant': artifact.kind in {'teaching_brief', 'learning_bundle'},
            'learning_priority': 40 if artifact.kind in {'teaching_brief', 'learning_bundle'} else 0,
            'learning_reason': 'Artefacto resumido para explicar lo aprendido.' if artifact.kind in {'teaching_brief', 'learning_bundle'} else '',
            'overlay_rect': {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0},
            'metadata_snapshot': dict(payload) if isinstance(payload, dict) else {'preview': str(payload)[:120]},
        }

    def _refresh_replay_after_annotation(self, episode_id: str) -> None:
        self._persist_replay_feedback(episode_id)
        self.refresh()
        self._selected_history_episode_id = episode_id
        self._sync_selected_teaching_history()

    def _persist_replay_feedback(self, episode_id: str) -> None:
        if not episode_id:
            return
        selected = next((item for item in self._teaching_history if item.get('episode_id') == episode_id), None)
        gallery = self._load_replay_gallery(episode_id)
        summary = dict(gallery.get('summary') or {})
        artifacts = self.artifact_repository.list_for_episode(episode_id)
        bundle_artifact = next((item for item in reversed(artifacts) if item.kind == 'learning_bundle'), None)
        existing_packet = self._load_artifact_payload(bundle_artifact) or {}
        if not existing_packet:
            fallback = self._derive_learning_from_replay(
                replay_steps=gallery.get('timeline_steps', []),
                artifacts=artifacts,
                site_id=(selected or {}).get('site_id', 'generic_web'),
                display_name=(selected or {}).get('title', episode_id),
            )
            existing_packet = fallback
        if self.replay_learning_feedback_service is not None:
            updated_packet = self.replay_learning_feedback_service.apply_annotations_to_learning(existing_packet, summary)
        else:
            updated_packet = dict(existing_packet)
            updated_packet['visual_summary'] = summary
        policy = self.site_policy_registry.get_policy((selected or {}).get('site_id', '')) or self._current_policy()
        if policy is not None:
            self._save_learning_bundle(episode_id, policy, updated_packet)
        self._upsert_visual_incidents(episode_id, summary)
        steps = self.episode_repository.load_episode(episode_id)
        title = (selected or {}).get('title', f'Replay visual {episode_id}')
        self._record_teaching_dossier(
            episode_id=episode_id,
            title=title,
            status=RunStatus.SUCCESS,
            summary='Replay visual actualizado con anotaciones, colores por confianza y feedback persistente.',
            metrics={
                'replay_visual_summary': summary,
                'manual_correction_count': summary.get('manual_correction_count', 0),
            },
            steps=steps,
            artifacts=artifacts,
        )

    def _upsert_visual_incidents(self, episode_id: str, summary: dict) -> None:
        if not episode_id:
            return
        existing = {item.incident_kind: item for item in self.hidden_incident_repository.find_by_episode(episode_id)}
        site_id = self._selected_teaching_history.get('site_id', self._runtime_site_id() or 'generic_web')
        incidents_to_manage = []
        visual_alignment = float(summary.get('visual_alignment_score', 0.0) or 0.0)
        critical_coverage = float(summary.get('critical_object_coverage', 0.0) or 0.0)
        manual_corrections = int(summary.get('manual_correction_count', 0) or 0)
        red_count = int(summary.get('red_count', 0) or 0)
        gaps = list(summary.get('gaps') or [])
        if visual_alignment < 0.5 or red_count >= 2:
            incidents_to_manage.append(
                ('visual_alignment_weak', 'El replay visual aun no alinea bien los eventos criticos sobre las capturas.', 'Faltan rectangulos fiables o hay demasiados overlays rojos.', IssueSeverity.HIGH if red_count >= 3 else IssueSeverity.MEDIUM)
            )
        if critical_coverage < 0.66 or gaps:
            incidents_to_manage.append(
                ('critical_object_missing', 'Todavia faltan objetos criticos del flujo en el replay visual.', '; '.join(gaps[:3]) or 'Hay correo, contrasena o submit sin evidencia fuerte.', IssueSeverity.HIGH)
            )
        if manual_corrections >= 2:
            incidents_to_manage.append(
                ('manual_correction_hotspot', 'El usuario esta corrigiendo manualmente objetos del replay con frecuencia.', 'Conviene convertir estas correcciones en reglas o anotaciones preferidas.', IssueSeverity.MEDIUM)
            )
        if manual_corrections > 0 and red_count > 0:
            incidents_to_manage.append(
                ('annotation_conflict', 'Hay diferencias entre la captura original y la correccion manual del replay.', 'La evidencia visual todavia no converge del todo.', IssueSeverity.MEDIUM)
            )
        active_kinds = {item[0] for item in incidents_to_manage}
        for kind, incident in existing.items():
            if kind in {'visual_alignment_weak', 'critical_object_missing', 'manual_correction_hotspot', 'annotation_conflict'} and kind not in active_kinds:
                recovered = incident.model_copy(update={
                    'status': IncidentStatus.RECOVERED,
                    'summary': f'{incident.summary} | recuperado por nuevas anotaciones o mejor alineacion visual.',
                    'updated_at_utc': incident.updated_at_utc,
                    'metadata': {**incident.metadata, 'visual_summary': summary},
                })
                self.hidden_incident_repository.save(recovered)
        for kind, summary_text, detail, severity in incidents_to_manage:
            incident = existing.get(kind)
            if incident is None:
                incident = HiddenIncident(
                    episode_id=episode_id,
                    site_id=site_id,
                    incident_kind=kind,
                    severity=severity,
                    status=IncidentStatus.NEEDS_FIX,
                    summary=summary_text,
                    probable_cause=detail,
                    detail=detail,
                    metadata={'visual_summary': summary},
                )
            else:
                incident = incident.model_copy(update={
                    'severity': severity,
                    'status': IncidentStatus.NEEDS_FIX,
                    'summary': summary_text,
                    'probable_cause': detail,
                    'detail': detail,
                    'metadata': {**incident.metadata, 'visual_summary': summary},
                })
            self.hidden_incident_repository.save(incident)

    def _infer_replay_quality(self, steps: list, artifacts: list[SessionArtifact], learning_bundle: dict) -> str:
        visible_steps = [step for step in steps if (getattr(step, 'metadata', {}) or {}).get('capture_channel') == CaptureChannel.VISIBLE.value and getattr(step, 'action_type', '') != 'teaching_brief']
        screenshots = [step for step in steps if getattr(step, 'screenshot_path', None)]
        if visible_steps and screenshots:
            return 'complete'
        if steps or artifacts or (learning_bundle.get('capture_stats') or {}).get('status') == 'partial_recovery':
            return 'partial'
        return 'insufficient'

    def _infer_teaching_status(self, steps: list, artifacts: list[SessionArtifact], learning_bundle: dict) -> str:
        capture_stats = learning_bundle.get('capture_stats') or {}
        if capture_stats.get('status'):
            return capture_stats.get('status')
        if any(artifact.kind == 'learning_bundle' for artifact in artifacts):
            return 'completed'
        if steps or artifacts:
            return 'partial_recovery'
        return 'incomplete'

    def _save_learning_bundle(self, episode_id: str, policy: SitePolicy, learning_packet: dict) -> dict:
        existing_artifacts = self.artifact_repository.list_for_episode(episode_id)
        existing = next((item for item in reversed(existing_artifacts) if item.kind == 'learning_bundle'), None)
        existing_payload = self._load_artifact_payload(existing) or {}
        payload = self._sync_universal_interaction_learning(
            episode_id=episode_id,
            policy=policy,
            learning_packet=dict(learning_packet or {}),
            existing_packet=existing_payload,
        )
        artifact = SessionArtifact(
            episode_id=episode_id,
            kind='learning_bundle',
            path=f'{episode_id}/summary/learning_bundle.json',
            metadata={
                'artifact_kind': 'learning_bundle',
                'capture_channel': CaptureChannel.BACKGROUND.value,
                'site_id': policy.site_id,
                'redacted': True,
                'content_type': 'application/json',
            },
        )
        if existing is not None:
            artifact = artifact.model_copy(update={
                'artifact_id': existing.artifact_id,
                'created_at_utc': existing.created_at_utc,
            })
        self.artifact_repository.save(artifact, payload=payload)
        return payload

    def _sync_universal_interaction_learning(
        self,
        *,
        episode_id: str,
        policy: SitePolicy,
        learning_packet: dict,
        existing_packet: dict,
    ) -> dict:
        packet = dict(learning_packet or {})
        if self.interaction_learning_service is None:
            return packet
        metadata = dict(packet.get('metadata') or {})
        try:
            steps = self.episode_repository.load_episode(episode_id)
            brief = self._load_teaching_brief_payload(episode_id)
            previous_episode_id = str(packet.get('interaction_episode_id') or existing_packet.get('interaction_episode_id') or '').strip() or None
            interaction_episode = self.interaction_learning_service.learn_from_teaching_session(
                episode_id=episode_id,
                site_id=policy.site_id,
                display_name=packet.get('display_name') or brief.get('display_name') or brief.get('target_label') or policy.display_name,
                objective=brief.get('objective') or packet.get('objective') or f'Ensenanza guiada de {policy.display_name}',
                expected_outcome=brief.get('expected_outcome') or packet.get('expected_outcome') or '',
                notes=brief.get('notes') or '',
                steps=steps,
                learning_packet=packet,
                previous_episode_id=previous_episode_id,
            )
            if interaction_episode is None:
                return packet
            if self.live_audit_supervisor is not None:
                recent_incidents = [
                    item.model_dump(mode='json')
                    for item in self.hidden_incident_repository.list_recent(limit=12)
                    if item.site_id == policy.site_id or not policy.site_id
                ]
                interaction_episode, packet, _snapshot = self.live_audit_supervisor.audit_teaching_session(
                    site_id=policy.site_id,
                    display_name=packet.get('display_name') or brief.get('display_name') or brief.get('target_label') or policy.display_name,
                    learning_packet=packet,
                    interaction_episode=interaction_episode,
                    incidents=recent_incidents,
                )
                if interaction_episode is None:
                    return packet
                metadata = dict(packet.get('metadata') or metadata)
            metadata.update({
                'interaction_episode_id': interaction_episode.interaction_episode_id,
                'interaction_pattern_id': interaction_episode.pattern_id or '',
                'interaction_selector_reason': interaction_episode.selector_reason,
                'interaction_reused_pattern': interaction_episode.reused_pattern,
                'teaching_episode': dict(packet.get('teaching_episode') or {}),
                'cross_check_summary': dict(packet.get('cross_check_summary') or {}),
                'visual_teaching_frame_count': len(packet.get('visual_teaching_frames') or []),
            })
            metadata.pop('interaction_sync_error', None)
            packet['metadata'] = metadata
            packet['interaction_episode_id'] = interaction_episode.interaction_episode_id
            packet['interaction_pattern_id'] = interaction_episode.pattern_id or ''
            packet['interaction_confidence'] = interaction_episode.confidence
            packet['reused_interaction_pattern'] = interaction_episode.reused_pattern
            packet['interaction_learning_signals'] = [item.label for item in interaction_episode.learning_signals]
            packet['teaching_episode'] = dict(packet.get('teaching_episode') or {})
            packet['cross_check_summary'] = dict(packet.get('cross_check_summary') or {})
        except Exception as exc:
            metadata['interaction_sync_error'] = str(exc)
            packet['metadata'] = metadata
            return packet
        return packet

    def _process_ui_events(self) -> None:
        app = QGuiApplication.instance()
        if app is not None and hasattr(app, 'processEvents'):
            app.processEvents()
            return
        if hasattr(QGuiApplication, 'processEvents'):
            QGuiApplication.processEvents()

    def _step_to_replay_items(self, step, *, start_index: int, compact: bool) -> list[dict]:
        if step.action_type == 'frame_fallback':
            expanded = self._expand_frame_fallback_replay_items(step, start_index=start_index)
            if expanded:
                return expanded
        return [self._step_to_replay_item(step, review_index=start_index, compact=compact)]

    def _expand_frame_fallback_replay_items(self, step, *, start_index: int) -> list[dict]:
        metadata = step.metadata or {}
        frame_reference = metadata.get('frame_url') or step.target or ''
        payload = parse_frame_event_context(frame_reference)
        request_type = metadata.get('frame_request_type') or str(payload.get('requestType') or '').strip()
        if not request_type:
            return []
        sanitized_frame_url = self._sanitize_replay_text(metadata.get('frame_url') or frame_reference)
        items: list[dict] = []
        index = start_index
        post_params = payload.get('postParams') if isinstance(payload.get('postParams'), dict) else {}
        if request_type == 'LoginAndGetTempToken':
            username = str(post_params.get('username') or '')
            if username:
                items.append(
                    self._build_structured_replay_item(
                        step=step,
                        review_index=index,
                        action_type='input',
                        target='#login-username',
                        text=self._mask_replay_value(username, 'email' if '@' in username else 'username'),
                        element_role='email_input' if '@' in username else 'username_input',
                        selector='#login-username',
                        detail='Ingreso detectado en campo de correo o usuario (reconstruido desde frame/API).',
                        sensitive=True,
                        frame_url=sanitized_frame_url,
                    )
                )
                index += 1
            if post_params.get('password') is not None:
                items.append(
                    self._build_structured_replay_item(
                        step=step,
                        review_index=index,
                        action_type='input',
                        target='#login-password',
                        text='[REDACTED]',
                        element_role='password_input',
                        selector='#login-password',
                        detail='Ingreso detectado en campo de contrasena (valor protegido).',
                        sensitive=True,
                        frame_url=sanitized_frame_url,
                    )
                )
                index += 1
            items.append(
                self._build_structured_replay_item(
                    step=step,
                    review_index=index,
                    action_type='keydown',
                    target='#login-password',
                    text='Enter',
                    element_role='password_input',
                    selector='#login-password',
                    detail='Tecla Enter usada para enviar el login (reconstruida desde frame/API).',
                    sensitive=False,
                    frame_url=sanitized_frame_url,
                )
            )
            index += 1
            items.append(
                self._build_structured_replay_item(
                    step=step,
                    review_index=index,
                    action_type='submit',
                    target='#login-form',
                    text='Iniciar sesion',
                    element_role='form',
                    selector='#login-form',
                    detail='Envio del formulario de inicio de sesion detectado en frame embebido.',
                    sensitive=False,
                    frame_url=sanitized_frame_url,
                )
            )
            return items
        if request_type == 'Logout':
            items.append(
                self._build_structured_replay_item(
                    step=step,
                    review_index=index,
                    action_type='click',
                    target='#logout',
                    text='Cerrar sesion',
                    element_role='button',
                    selector='#logout',
                    detail='Accion de cierre de sesion detectada en frame embebido.',
                    sensitive=False,
                    frame_url=sanitized_frame_url,
                )
            )
            return items
        return [
            self._build_structured_replay_item(
                step=step,
                review_index=start_index,
                action_type='frame_fallback',
                target=f'frame:{request_type.lower()}',
                text=request_type,
                element_role='frame',
                selector=f'frame:{request_type.lower()}',
                detail='Accion detectada en frame embebido y reconstruida desde metadatos protegidos.',
                sensitive=False,
                frame_url=sanitized_frame_url,
            )
        ]

    def _build_structured_replay_item(
        self,
        *,
        step,
        review_index: int,
        action_type: str,
        target: str,
        text: str,
        element_role: str,
        selector: str,
        detail: str,
        sensitive: bool,
        frame_url: str,
    ) -> dict:
        screenshot_path = self._resolve_screenshot_path(getattr(step, 'screenshot_path', None))
        screenshot_url = screenshot_path.as_uri() if screenshot_path is not None and screenshot_path.exists() else ''
        screenshot_name = screenshot_path.name if screenshot_path is not None else ''
        marker = self._build_learning_marker(
            action_type=action_type,
            element_role=element_role,
            metadata={'frame_url': frame_url, 'key_display': text if action_type == 'keydown' else ''},
            has_screenshot=bool(screenshot_url),
        )
        synthetic_step_id = f"{step.step_id if hasattr(step, 'step_id') else step.episode_id}:{review_index}:{action_type}"
        return {
            'step_id': synthetic_step_id,
            'artifact_id': '',
            'step_index': review_index,
            'episode_id': step.episode_id,
            'action_type': action_type,
            'target': target,
            'text': text,
            'timestamp': step.timestamp_utc.isoformat(),
            'sensitive': sensitive,
            'channel': 'visible',
            'element_role': element_role,
            'selector': selector,
            'detail': detail,
            'input_type': 'password' if element_role == 'password_input' else ('email' if element_role == 'email_input' else ''),
            'button_text': text if action_type in {'click', 'submit'} else '',
            'aria_label': '',
            'placeholder': '',
            'frame_url': frame_url,
            'frame_name': '',
            'capture_source': 'frame_fallback_structured',
            'screenshot_reason': '',
            'key_display': text if action_type == 'keydown' else '',
            'screenshot_name': screenshot_name,
            'screenshot_path': str(screenshot_path) if screenshot_path is not None else '',
            'screenshot_url': screenshot_url,
            'linked_screenshot_id': screenshot_name,
            'group_key': str(screenshot_path) if screenshot_path is not None else f"no_screenshot::{synthetic_step_id}",
            'has_screenshot': bool(screenshot_url),
            'learning_relevant': marker['relevant'],
            'learning_priority': marker['priority'],
            'learning_reason': marker['reason'],
            'overlay_rect': {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0},
            'metadata_snapshot': {
                'frame_url': frame_url,
                'frame_request_type': (getattr(step, 'metadata', {}) or {}).get('frame_request_type', ''),
                'capture_source': 'frame_fallback_structured',
                'field_role': element_role,
                'selector': selector,
            },
        }

    def _step_to_replay_item(self, step, *, review_index: int, compact: bool) -> dict:
        metadata = step.metadata or {}
        element_role = metadata.get('field_role') or metadata.get('element_role') or metadata.get('tag_name') or metadata.get('input_type') or 'elemento'
        selector = self._sanitize_replay_text(metadata.get('selector') or step.target or 'sin selector')
        text_value = metadata.get('masked_value') or step.text_value or metadata.get('key_display') or metadata.get('textPreview') or metadata.get('button_text') or self._fallback_replay_text(step.action_type, element_role, metadata)
        text_value = self._sanitize_replay_text(text_value)
        channel = metadata.get('capture_channel') or 'visible'
        detail = self._describe_step(step.action_type, element_role, metadata)
        if compact:
            detail = text_value
        screenshot_path = self._resolve_screenshot_path(step.screenshot_path)
        screenshot_url = screenshot_path.as_uri() if screenshot_path is not None and screenshot_path.exists() else ''
        screenshot_name = screenshot_path.name if screenshot_path is not None else ''
        marker = self._build_learning_marker(
            action_type=step.action_type,
            element_role=element_role,
            metadata=metadata,
            has_screenshot=bool(screenshot_url),
        )
        group_key = str(screenshot_path) if screenshot_path is not None else f"no_screenshot::{step.step_id}"
        return {
            'step_id': step.step_id,
            'artifact_id': '',
            'step_index': review_index,
            'episode_id': step.episode_id,
            'action_type': step.action_type,
            'target': self._sanitize_replay_text(step.target or selector),
            'text': text_value,
            'timestamp': step.timestamp_utc.isoformat(),
            'sensitive': bool(metadata.get('sensitive')),
            'channel': channel,
            'element_role': element_role,
            'selector': selector,
            'detail': detail,
            'input_type': metadata.get('input_type') or '',
            'button_text': self._sanitize_replay_text(metadata.get('button_text') or ''),
            'aria_label': self._sanitize_replay_text(metadata.get('aria_label') or ''),
            'placeholder': self._sanitize_replay_text(metadata.get('placeholder') or ''),
            'frame_url': self._sanitize_replay_text(metadata.get('frame_url') or ''),
            'frame_name': metadata.get('frame_name') or '',
            'capture_source': metadata.get('capture_source') or '',
            'screenshot_reason': metadata.get('screenshot_reason') or '',
            'key_display': metadata.get('key_display') or '',
            'screenshot_name': screenshot_name,
            'screenshot_path': str(screenshot_path) if screenshot_path is not None else '',
            'screenshot_url': screenshot_url,
            'linked_screenshot_id': screenshot_name,
            'group_key': group_key,
            'has_screenshot': bool(screenshot_url),
            'learning_relevant': marker['relevant'],
            'learning_priority': marker['priority'],
            'learning_reason': marker['reason'],
            'overlay_rect': self._build_overlay_rect(metadata),
            'metadata_snapshot': dict(metadata),
        }

    def _describe_step(self, action_type: str, element_role: str, metadata: dict) -> str:
        field_role = metadata.get('field_role') or element_role
        if action_type == 'teaching_brief':
            brief = metadata.get('teaching_brief') or {}
            return f"Objetivo: {brief.get('objective') or metadata.get('textPreview') or 'sin objetivo'}"
        if action_type == 'scroll':
            return f"Scroll detectado hasta Y={metadata.get('scroll_y', 0)}"
        if action_type == 'visual_checkpoint':
            return 'Checkpoint visual capturado por intervalo para no perder contexto visible.'
        if action_type == 'visible_recovery':
            return 'Recuperacion visual creada al finalizar para no perder el replay.'
        if action_type == 'frame_fallback':
            request_type = metadata.get('frame_request_type') or ''
            if request_type:
                return f'Frame embebido detectado: {request_type}. Se intento reconstruir la accion protegida.'
            return metadata.get('textPreview') or 'Frame embebido sin bridge directo; se guardo captura visible de respaldo.'
        if action_type == 'keydown':
            key_value = metadata.get('key_display') or metadata.get('key_code') or 'tecla'
            if field_role in {'password', 'password_input'}:
                return f'Tecla {key_value} en campo de contrasena.'
            if field_role in {'email', 'email_input'}:
                return f'Tecla {key_value} en campo de correo.'
            return f'Tecla {key_value} en {element_role}.'
        if action_type in {'click', 'submit', 'focus'}:
            label = metadata.get('button_text') or metadata.get('aria_label') or metadata.get('textPreview') or ''
            return f"{action_type} sobre {element_role}" + (f" | {label}" if label else '')
        if action_type in {'input', 'change'}:
            if field_role in {'password', 'password_input'}:
                return 'Ingreso detectado en campo de contrasena protegido.'
            if field_role in {'email', 'email_input'}:
                return 'Ingreso detectado en campo de correo protegido.'
            if field_role in {'username', 'username_input'}:
                return 'Ingreso detectado en campo de usuario protegido.'
            placeholder = metadata.get('placeholder') or metadata.get('name') or ''
            return f"{action_type} en {element_role}" + (f" | {placeholder}" if placeholder else '')
        return f"{action_type} en {element_role}"

    def _build_learning_marker(self, *, action_type: str, element_role: str, metadata: dict, has_screenshot: bool) -> dict:
        role = str(metadata.get('field_role') or metadata.get('element_role') or element_role or '').lower()
        key_display = str(metadata.get('key_display') or '').lower()
        if action_type in {'input', 'change'} and role in {'email', 'email_input', 'username', 'username_input', 'password', 'password_input'}:
            return {'relevant': True, 'priority': 100, 'reason': 'Campo clave de autenticacion o identificacion detectado.'}
        if action_type in {'input', 'change'}:
            return {'relevant': True, 'priority': 88, 'reason': 'Entrada de texto util para ensenar como se llena el flujo.'}
        if action_type in {'click', 'submit'}:
            return {'relevant': True, 'priority': 92, 'reason': 'Accion de decision o envio detectada como parte del flujo.'}
        if action_type == 'keydown' and key_display in {'enter', 'tab'}:
            return {'relevant': True, 'priority': 84, 'reason': f'Tecla {key_display or "especial"} usada para avanzar o enviar el flujo.'}
        if action_type == 'scroll':
            return {'relevant': True, 'priority': 56, 'reason': 'Desplazamiento detectado para revelar contenido importante.'}
        if action_type == 'focus':
            return {'relevant': True, 'priority': 44, 'reason': 'Cambio de foco detectado sobre un elemento relevante.'}
        if action_type in {'visible_recovery', 'visual_checkpoint'} and has_screenshot:
            return {'relevant': True, 'priority': 28, 'reason': 'Captura de contexto visual guardada para no perder el estado de la pagina.'}
        if action_type == 'frame_fallback':
            return {'relevant': True, 'priority': 70, 'reason': 'Accion reconstruida desde frame embebido o metadatos protegidos.'}
        return {'relevant': False, 'priority': 0, 'reason': ''}

    def _build_overlay_rect(self, metadata: dict) -> dict:
        rect = metadata.get('element_rect') or metadata.get('elementRect')
        width = metadata.get('viewport_width') or metadata.get('viewportWidth') or 0
        height = metadata.get('viewport_height') or metadata.get('viewportHeight') or 0
        if not isinstance(rect, dict):
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        try:
            x = float(rect.get('x', 0) or 0)
            y = float(rect.get('y', 0) or 0)
            w = float(rect.get('width', 0) or 0)
            h = float(rect.get('height', 0) or 0)
            vw = float(width or 0)
            vh = float(height or 0)
        except (TypeError, ValueError):
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        if vw <= 0 or vh <= 0 or w <= 0 or h <= 0:
            return {'valid': False, 'x': 0, 'y': 0, 'width': 0, 'height': 0}
        return {
            'valid': True,
            'x': max(0.0, min(1.0, x / vw)),
            'y': max(0.0, min(1.0, y / vh)),
            'width': max(0.0, min(1.0, w / vw)),
            'height': max(0.0, min(1.0, h / vh)),
        }

    def _fallback_replay_text(self, action_type: str, element_role: str, metadata: dict) -> str:
        action = str(action_type or '').lower()
        role = str(element_role or '').lower()
        if role in {'password_input', 'password'}:
            return 'campo contrasena'
        if role in {'email_input', 'email'}:
            return 'campo correo'
        if role in {'username_input', 'username'}:
            return 'campo usuario'
        if action == 'visual_checkpoint':
            return 'checkpoint visual'
        if action == 'teaching_brief':
            return 'brief de ensenanza'
        if action == 'click':
            return 'clic'
        if action == 'submit':
            return 'submit'
        if action == 'scroll':
            return 'scroll'
        if action == 'keydown':
            key_display = str(metadata.get('key_display') or '').strip()
            return f'tecla {key_display}'.strip() if key_display else 'tecla'
        return str(role or action or 'objeto')

    def _sanitize_replay_text(self, value: str | None) -> str:
        if not value:
            return ''
        text = str(value)
        for _ in range(2):
            decoded = unquote(text)
            text = decoded if decoded != text else text
            text = re.sub(
                r'([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})',
                lambda match: f"{match.group(1)}***@{match.group(2)}",
                text,
            )
            text = re.sub(
                r'(?i)(password|passwd|pwd|token|authorization|cookie|csrf)=([^&#\s]+)',
                lambda match: f"{match.group(1)}=[REDACTED]",
                text,
            )
            text = re.sub(
                r'(?i)("password"\s*:\s*")([^"]*)(")',
                lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}",
                text,
            )
            text = re.sub(
                r'(?i)("token"\s*:\s*")([^"]*)(")',
                lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}",
                text,
            )
            text = re.sub(
                r'(?i)("username"\s*:\s*")([^"]*)(")',
                lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}",
                text,
            )
        return text

    def _mask_replay_value(self, value: str, role: str) -> str:
        if role == 'email':
            return self._sanitize_replay_text(value)
        if role == 'username':
            return value[:1] + '***' if value else '[REDACTED]'
        return '[REDACTED]'

    def _resolve_screenshot_path(self, screenshot_path: str | None) -> Path | None:
        if not screenshot_path:
            return None
        candidate = Path(screenshot_path)
        if not candidate.is_absolute():
            candidate = Path(self.config.screenshots_dir) / screenshot_path
        return candidate

    def _load_artifact_payload(self, artifact: SessionArtifact | None):
        if artifact is None:
            return None
        try:
            path = Path(artifact.path)
            if path.is_absolute() and path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
            return self.artifact_repository.storage.load_json(artifact.path)
        except Exception:
            return None

    def _is_teaching_episode(self, episode) -> bool:
        tags = set(episode.tags or [])
        return any(tag in tags for tag in {'browser_teach', 'teach_session', 'teach_mode:browser'}) or 'teach_url=' in (episode.notes or '')
    def _capture_mode_label(self, policy: SitePolicy) -> str:
        modes = []
        if policy.capture_dom:
            modes.append('DOM')
        if policy.capture_network:
            modes.append('API')
        if policy.capture_console:
            modes.append('Consola')
        if policy.capture_storage:
            modes.append('Storage')
        return ', '.join(modes)

    def _format_capture_channels(self, capture_visible: bool, capture_background: bool, capture_api: bool) -> str:
        selected = []
        if capture_visible:
            selected.append('Visible')
        if capture_background:
            selected.append('Segundo plano')
        if capture_api:
            selected.append('API')
        return ', '.join(selected) or 'Visible'

    def _delete_managed_path(self, path_like) -> None:
        if not path_like:
            return
        candidate = Path(path_like)
        if not candidate.is_absolute():
            candidate = self.artifact_repository.storage.root / candidate
        try:
            resolved = candidate.resolve(strict=False)
        except Exception:
            return
        managed_roots = [
            Path(self.config.data_dir).resolve(strict=False),
            Path(self.config.workspace_root).resolve(strict=False),
        ]
        if not any(resolved == root or root in resolved.parents for root in managed_roots):
            return
        if resolved.is_dir():
            shutil.rmtree(resolved, ignore_errors=True)
            return
        if resolved.exists():
            resolved.unlink(missing_ok=True)
            self._delete_empty_parents(resolved.parent, stop_roots=managed_roots)

    def _delete_empty_parents(self, directory: Path, *, stop_roots: list[Path]) -> None:
        current = directory
        while current and all(current != root for root in stop_roots):
            try:
                if current.exists() and not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                    continue
            except Exception:
                return
            break

    episodes = Property(list, get_episodes, notify=dataChanged)
    flowSteps = Property(list, get_flow_steps, constant=True)
    summaryCards = Property(list, get_summary_cards, notify=dataChanged)
    policyCards = Property(list, get_policy_cards, notify=dataChanged)
    channelCards = Property(list, get_channel_cards, notify=dataChanged)
    reviewSteps = Property(list, get_review_steps, notify=dataChanged)
    teachingHistory = Property(list, get_teaching_history, notify=dataChanged)
    replaySteps = Property(list, get_replay_steps, notify=dataChanged)
    replayFrames = Property(list, get_replay_frames, notify=dataChanged)
    replayCurrentFrame = Property(dict, get_replay_current_frame, notify=dataChanged)
    replayVisualSummary = Property(dict, get_replay_visual_summary, notify=dataChanged)
    visualSignalSnapshot = Property(dict, get_visual_signal_snapshot, notify=dataChanged)
    assistantReplayCards = Property(list, get_assistant_replay_cards, notify=dataChanged)
    assistantReplaySteps = Property(list, get_assistant_replay_steps, notify=dataChanged)
    assistantLaneSummary = Property(dict, get_assistant_lane_summary, notify=dataChanged)
    selectedReplayStep = Property(dict, get_selected_replay_step, notify=dataChanged)
    selectedReplayAnnotation = Property(dict, get_selected_replay_annotation, notify=dataChanged)
    replayZoom = Property(float, get_replay_zoom, notify=dataChanged)
    replayStatusFilter = Property(str, get_replay_status_filter, notify=dataChanged)
    replayCanGoPrev = Property(bool, get_replay_can_go_prev, notify=dataChanged)
    replayCanGoNext = Property(bool, get_replay_can_go_next, notify=dataChanged)
    annotationDrawMode = Property(bool, get_annotation_draw_mode, notify=dataChanged)
    selectedTeachingHistory = Property(dict, get_selected_teaching_history, notify=dataChanged)
    selectedPolicy = Property(dict, get_selected_policy, notify=dataChanged)
    selectedSiteId = Property(str, get_selected_site_id, notify=dataChanged)
    loginStatus = Property(str, get_login_status, notify=dataChanged)
    securityState = Property(dict, get_security_state, notify=dataChanged)
    teachingStatus = Property(str, get_teaching_status, notify=dataChanged)
    teachingSummary = Property(str, get_teaching_summary, notify=dataChanged)
    teachingDraftVersion = Property(int, get_teaching_draft_version, notify=dataChanged)
    teachingDraftLessonTitle = Property(str, get_teaching_draft_lesson_title, notify=dataChanged)
    teachingDraftTargetLabel = Property(str, get_teaching_draft_target_label, notify=dataChanged)
    teachingDraftStartUrl = Property(str, get_teaching_draft_start_url, notify=dataChanged)
    teachingDraftObjective = Property(str, get_teaching_draft_objective, notify=dataChanged)
    teachingDraftExpectedOutcome = Property(str, get_teaching_draft_expected_outcome, notify=dataChanged)
    teachingDraftNotes = Property(str, get_teaching_draft_notes, notify=dataChanged)
    sessionActive = Property(bool, get_session_active, notify=dataChanged)
    sessionPaused = Property(bool, get_session_paused, notify=dataChanged)
    sessionFinalizing = Property(bool, get_session_finalizing, notify=dataChanged)
    captureProgressText = Property(str, get_capture_progress_text, notify=dataChanged)
    sessionHealth = Property(dict, get_session_health, notify=dataChanged)
    runtimeSignals = Property(list, get_runtime_signals, notify=dataChanged)
    liveIncidentText = Property(str, get_live_incident_text, notify=dataChanged)
    canStart = Property(bool, get_can_start, notify=dataChanged)
    canPause = Property(bool, get_can_pause, notify=dataChanged)
    canResume = Property(bool, get_can_resume, notify=dataChanged)
    canStop = Property(bool, get_can_stop, notify=dataChanged)
    activeEpisodeId = Property(str, get_active_episode_id, notify=dataChanged)
















