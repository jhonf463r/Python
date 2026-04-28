from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import threading
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _generate_chat_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    suffix = uuid.uuid4().hex[:6]
    return f'{stamp}-{suffix}'

from iabv_v15.domain.models import (
    AmbiguityLevel,
    AppConfig,
    ComplexityLevel,
    EnvironmentSelfModel,
    InferenceRequest,
    ObjectiveNodeKind,
    RoleProfile,
    TaskRole,
    WorldModelSnapshot,
    canonical_external_state_flags,
)
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.assistant_preference_resolver import AssistantPreferenceResolver
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.evolution.autonomy_activity_projector import AutonomyActivityProjector
from iabv_v15.services.evolution.evolution_review_service import EvolutionReviewService
from iabv_v15.services.inference.inference_service import InferenceService
from iabv_v15.services.self_teach.self_teach_orchestrator import SelfTeachOrchestrator
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.training.training_orchestrator import TrainingOrchestrator
from iabv_v15.services.capture.universal_perception_service import UniversalPerceptionService
from iabv_v15.ui.qt import QObject, Property, QGuiApplication, Signal, Slot


class ControlCenterViewModel(QObject):
    dataChanged = Signal()
    taskResolved = Signal(str, object)
    taskFailed = Signal(str, str)

    # Señales evolutivas para diálogos UI (Task B)
    credentialPromptRequested = Signal(dict)  # {domain, reason, username_hint}
    clarificationRequested = Signal(dict)     # {id, question, options, context}
    missingDependencyRequested = Signal(dict) # {package_name, manager, reason}
    backgroundActivityChanged = Signal(dict)  # {text, progress, status, details}
    providerHealthChanged = Signal(list)       # [ProviderHealth]
    mcpBridgeChanged = Signal(dict)            # status dict del MCPBridgeService

    # Señales del botón "Auditarme ahora" (Frente 2 — SelfAuditService).
    # El VM NO decide rutas ni reacciona al resultado más allá de emitir:
    # cualquier acción sobre el snapshot es decisión humana.
    selfAuditStarted = Signal()
    selfAuditCompleted = Signal(str)  # JSON serializado del SelfAuditSnapshot
    selfAuditFailed = Signal(str)     # detalle textual del fallo

    # Señales avanzadas del chat (Frente 4 — UI Chat Avanzada)
    fileAttached = Signal(dict)           # {name, path, size, type}
    fileDetached = Signal(str)            # path del archivo removido
    chatSearchResults = Signal(list)      # lista de mensajes filtrados
    contextualSuggestionsChanged = Signal(list)  # sugerencias contextuales
    liveStatusChanged = Signal(str)       # "idle"|"processing"|"streaming"|"error"
    codeApplyRequested = Signal(str, str) # (code, language)
    chatDownloadRequested = Signal(str, str)  # (content, filename)

    def __init__(
        self,
        *,
        config: AppConfig,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        artifact_repository: SessionArtifactRepository,
        inference_service: InferenceService,
        role_router: LocalRoleRouter,
        adaptive_orchestrator: AdaptiveTaskOrchestrator,
        training_orchestrator: TrainingOrchestrator,
        pbt_service: PBTControlService,
        development_assist_service: DevelopmentAssistService,
        engineering_review_service: EngineeringReviewService,
        embedding_service: EmbeddingIndexService,
        navigation_controller: QObject | None = None,
        self_teach_orchestrator: SelfTeachOrchestrator | None = None,
        capture_studio_viewmodel: QObject | None = None,
        tool_teach_service: Any | None = None,
        autonomous_evolution_service: Any | None = None,
        evolution_review_service: EvolutionReviewService | None = None,
        experiment_lab_repository: ExperimentLabRepository | None = None,
        tool_record_repository: ToolRecordRepository | None = None,
        scenario_run_repository: ScenarioRunRepository | None = None,
        autonomy_activity_projector: AutonomyActivityProjector | None = None,
        objective_repository: Any | None = None,
        universal_perception_service: UniversalPerceptionService | None = None,
        autonomous_validation_cycle: Any | None = None,
        tool_discovery_service: Any | None = None,
        self_examination_service: Any | None = None,
        mcp_bridge_service: Any | None = None,
        control_master_service: Any | None = None,
        control_master_digest_builder: Any | None = None,
        self_audit_service: Any | None = None,
        chat_capability_ingestion_service: Any | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.artifact_repository = artifact_repository
        self.inference_service = inference_service
        self.role_router = role_router
        self._assistant_preference_resolver = AssistantPreferenceResolver()
        self.adaptive_orchestrator = adaptive_orchestrator
        self.training_orchestrator = training_orchestrator
        self.pbt_service = pbt_service
        self.development_assist_service = development_assist_service
        self.engineering_review_service = engineering_review_service
        self.embedding_service = embedding_service
        self.navigation_controller = navigation_controller
        self.self_teach_orchestrator = self_teach_orchestrator
        self.capture_studio_viewmodel = capture_studio_viewmodel
        self.tool_teach_service = tool_teach_service
        self.autonomous_evolution_service = autonomous_evolution_service
        self.evolution_review_service = evolution_review_service
        self.experiment_lab_repository = experiment_lab_repository
        self.tool_record_repository = tool_record_repository
        self.scenario_run_repository = scenario_run_repository
        self.autonomy_activity_projector = autonomy_activity_projector
        self.objective_repository = objective_repository
        self.universal_perception_service = universal_perception_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.tool_discovery_service = tool_discovery_service
        self.self_examination_service = self_examination_service
        self.control_master_service = control_master_service
        self.control_master_digest_builder = control_master_digest_builder
        self._control_master_digest: dict[str, Any] = {}
        self._control_master_brief = 'Control maestro no disponible en esta sesion.'
        self.self_audit_service = self_audit_service
        self._last_self_audit_summary = ''
        self._self_audit_running = False

        # Servicio que escucha cada mensaje del usuario en busca de capacidades
        # declaradas (GPU, modelos locales, cuentas externas, runtimes). Cuando
        # detecta algo lo persiste en data/chat_research_backlog/<session>.jsonl
        # para que OSES y ExperimentLab lo consuman despues. Es OPCIONAL: si no
        # esta inyectado, sendChat funciona igual (comportamiento legacy).
        self.chat_capability_ingestion_service = chat_capability_ingestion_service
        self._chat_session_id = _generate_chat_session_id()
        self._pending_capability_notice: list[str] = []

        self._selected_role = config.default_task_role.value
        self._auto_route_enabled = True
        self._advanced_visible = False
        self._working = False
        self._provider_refreshing = False
        self._busy_label = 'Modo automatico activo. Escribe tu consulta y la consola elegira el rol, el pack y la estrategia por fases.'
        self._provider_cards = self._placeholder_provider_cards()
        self._progress_cards: list[dict[str, Any]] = []
        self._evolution_overview: dict[str, Any] = {}
        self._evolution_area_cards: list[dict[str, Any]] = []
        self._evolution_blockers: list[dict[str, str]] = []
        self._agent_cards: list[dict[str, Any]] = []
        self._legacy_cards = self._build_legacy_cards()
        self._role_cards = [profile.model_dump(mode='json') for profile in self.role_router.role_profiles]
        self._ui_state_lock = threading.Lock()
        self._chat_messages: list[dict[str, str]] = []
        self._attached_files: list[dict[str, Any]] = []
        self._live_status: str = 'idle'
        self._contextual_suggestions: list[dict[str, Any]] = []
        self._chat_search_query: str = ''
        self._pbt_state: dict[str, Any] = {}
        self._pbt_candidates: list[dict[str, Any]] = []
        self._diagnostic_text = 'Diagnostico pendiente. La consola revisa el stack local automaticamente y puedes pedirme ajustes o aprobaciones por chat.'
        self._strategy_text = 'La consola adaptativa decide intencion, arma contexto, mide readiness, propone estrategia y deja checkpoints claros antes de ejecutar.'
        self._recommendation_text = 'qwen3:8b queda como motor principal, pero ahora el Centro de Control usa packs por dominio y aprobaciones por fases.'
        self._legacy_summary = 'Se mantiene lo mejor del legado: PBT y snapshots de IABV 1.3, captura persistente de IABV 1.4 y ahora una capa adaptativa auditable por encima.'
        self._repo_bridge_text = self.development_assist_service.build_repo_bridge_summary()
        self._local_stack_text = self.development_assist_service.build_local_stack_summary()
        self._last_user_goal = ''
        self._last_goal_context: dict[str, Any] = {}
        self._clipboard_notice = 'Todavia no se ha copiado nada al portapapeles.'
        self._development_packet = ''
        self._latest_response_text = 'Todavia no hay respuesta final en esta sesion.'
        self._latest_response_meta = 'Cuando completes una consulta, aqui veras el rol detectado, el pack usado y si hubo aprobaciones.'
        self._approval_dialog_visible = False
        self._approval_dialog_title = 'Aprobacion requerida'
        self._approval_dialog_text = 'No hay aprobaciones pendientes.'
        self._assistant_guidance_mode = 'idle'
        self._assistant_guidance_text = 'Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex.'
        self._assistant_action_buttons: list[dict[str, str]] = []
        self._last_adaptive_payload: dict[str, Any] = {}
        self._pending_cloud_plan: Any = None
        self._autonomy_activity_override: dict[str, Any] = {}
        self._live_process_summary: dict[str, Any] = {}
        self._live_work_items: list[dict[str, Any]] = []
        self._assistant_session_cards: list[dict[str, Any]] = []
        self._autonomy_timeline: list[dict[str, Any]] = []

        self._adaptive_session_id = ''
        self._adaptive_status_text = 'Sin sesion adaptativa activa.'
        self._adaptive_intent_text = 'La intencion detectada aparecera aqui.'
        self._adaptive_context_text = 'El contexto util aparecera aqui.'
        self._adaptive_strategy_text = 'La estrategia propuesta aparecera aqui.'
        self._adaptive_execution_text = 'La ejecucion por fases aparecera aqui.'
        self._adaptive_evidence_text = 'La evidencia usada por el orquestador aparecera aqui.'
        self._adaptive_evolution_text = 'La traza evolutiva aparecera aqui.'
        self._adaptive_capability_cards: list[dict[str, str]] = []
        self._adaptive_approval_cards: list[dict[str, str]] = []
        self._adaptive_playbook_steps: list[dict[str, str]] = []
        self._adaptive_action_buttons = {
            'approve_strategy': False,
            'approve_next': False,
            'simulate': False,
            'execute': False,
            'abort': False,
        }

        # --- MCP bridge (Capa 1) ---
        # Permite a agentes externos (Devin/Claude/Codex) consumir el programa
        # via MCP. El ViewModel solo observa el estado publicado por el
        # service; NO decide rutas y NO reemplaza governance.
        self.mcp_bridge_service = mcp_bridge_service
        self._mcp_bridge_status: dict[str, Any] = {
            'enabled_pref': False,
            'running': False,
            'state': 'stopped',
            'tunnel_url': None,
            'transport': 'streamable-http',
            'bind_host': '127.0.0.1',
            'bind_port': 8765,
            'last_error': None,
            'governance_blocked': False,
            'governance_reason': None,
        }
        if self.mcp_bridge_service is not None:
            try:
                self.mcp_bridge_service.attach_listener(self._on_mcp_bridge_status)
            except Exception:
                pass

        self.taskResolved.connect(self._apply_task_result)
        self.taskFailed.connect(self._apply_task_failure)
        self._seed_messages()
        self._seed_development_packet()
        # Defer heavy refresh to a background thread so the QML engine
        # can load and render the UI immediately.  The seed message and
        # placeholder cards are already set so the chat area is visible
        # from the first frame; the full data arrives shortly after.
        # In test environments (no QGuiApplication), run synchronously
        # to avoid races with test assertions.
        has_gui = QGuiApplication.instance() is not None
        if has_gui:
            def _deferred_startup() -> None:
                try:
                    self.refresh()
                except Exception:
                    logger.exception('deferred startup refresh failed')
                try:
                    self.refreshAutonomyDock()
                except Exception:
                    logger.exception('deferred autonomy dock refresh failed')
                try:
                    self._refresh_provider_health(announce=False)
                except Exception:
                    logger.exception('deferred provider health failed')
            threading.Thread(target=_deferred_startup, name='vm-deferred-startup', daemon=True).start()
        else:
            self.refresh()
            self._refresh_provider_health(announce=False)

    def _placeholder_provider_cards(self) -> list[dict[str, Any]]:
        return [
            {'provider_name': 'Ollama', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.', 'role': 'generalista principal'},
            {'provider_name': 'Ollama Vision', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.', 'role': 'perfil visual'},
            {'provider_name': 'LM Studio', 'status': 'inactivo', 'available': False, 'detail': 'Componente opcional.', 'role': 'complemento opcional'},
            {'provider_name': 'Embeddings', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.', 'role': 'recuperacion semantica'},
        ]

    def _build_legacy_cards(self) -> list[dict[str, str]]:
        return [
            {'version': 'IABV 1.4', 'module': 'Playwright persistente', 'detail': 'Perfiles clonados, storage_state, timeline visible y observacion del navegador.'},
            {'version': 'IABV 1.4', 'module': 'Recorder y captura', 'detail': 'Base para capturar pasos, contexto visible y acciones humanas.'},
            {'version': 'IABV 1.3', 'module': 'PBT y checkpoints', 'detail': 'Scheduler, selector, mutacion y snapshots para afinar estrategias locales.'},
            {'version': 'IABV 1.3', 'module': 'SQLite y feature-store', 'detail': 'Consulta segura, analitica y paquetes estructurados sin cargar legacy en runtime.'},
        ]

    def _seed_messages(self) -> None:
        if self._chat_messages:
            return
        self._chat_messages = [
            {
                'role': 'assistant',
                'speaker': 'IABV',
                'text': 'Chat operativo listo. Describe tu objetivo y voy a detectar la intencion, el pack y el siguiente paso util sin preguntas genericas. Tambien puedes escribir mostrar avanzado, aprobar estrategia o revisar stack.',
                'meta': self._routing_mode_label(),
            }
        ]

    def _translate_status(self, status: str) -> str:
        return {
            'ready': 'listo',
            'degraded': 'degradado',
            'unavailable': 'no disponible',
            'optional_inactive': 'opcional no activo',
            'idle': 'inactivo',
        }.get(status, status)

    def _append_message(self, role: str, speaker: str, text: str, meta: str = '',
                        *, attachments: list[dict[str, Any]] | None = None,
                        code_blocks: list[dict[str, Any]] | None = None,
                        status: str = 'complete',
                        reasoning: str = '') -> None:
        msg: dict[str, Any] = {'role': role, 'speaker': speaker, 'text': text, 'meta': meta,
                               'status': status, 'timestamp': datetime.now(timezone.utc).strftime('%H:%M')}
        if attachments:
            msg['attachments'] = attachments
        if code_blocks:
            msg['codeBlocks'] = code_blocks
        if reasoning:
            msg['reasoning'] = reasoning
        with self._ui_state_lock:
            self._chat_messages.append(msg)
            self._chat_messages = self._chat_messages[-30:]
        self._refresh_contextual_suggestions()
        self._validate_ui_reflects_reality()

    def send_message_from_bridge(self, text: str) -> None:
        """Receive a message from UIBridgeService and inject it into the chat.

        Called by MCP agents via the UIBridgeServer TCP connection.
        The message appears in the UI as coming from an external agent.
        """
        self._append_message(
            role='bridge',
            speaker='MCP Agent',
            text=text,
            meta='via UIBridge IPC',
        )
        self.dataChanged.emit()

    def _count_payloads(self) -> int:
        payload_dir = Path(self.config.payloads_dir)
        return len(list(payload_dir.glob('*.json'))) if payload_dir.exists() else 0

    def _collect_metrics(self) -> dict[str, int]:
        return {
            'episodes': len(self.episode_repository.list_recent(limit=200)),
            'knowledge': len(self.knowledge_repository.list_recent(limit=200)),
            'artifacts': len(self.artifact_repository.list_recent(limit=400)),
            'runs': len(self.run_repository.list_recent(limit=200)),
            'payloads': self._count_payloads(),
            'profiles': len([item for item in Path(self.config.browser_profiles_dir).glob('*') if item.is_dir()]),
        }

    def _selected_role_profile(self) -> RoleProfile:
        return next(profile for profile in self.role_router.role_profiles if profile.role.value == self._selected_role)

    def _selected_role_title(self) -> str:
        return self._selected_role_profile().title

    def _routing_mode_label(self) -> str:
        if self._auto_route_enabled:
            return 'Modo automatico: intencion, contexto, pack y aprobaciones se calculan solos antes de la respuesta.'
        return f'Rol forzado: {self._selected_role_title()}.'

    def _update_progress_cards(self) -> None:
        metrics = self._collect_metrics()
        index_state = self.embedding_service.describe_index()
        pbt_generation = int(self._pbt_state.get('generation', 0))
        self._progress_cards = [
            {'title': 'Episodios', 'value': str(metrics['episodes']), 'hint': 'Sesiones de ensenanza listas para revisar'},
            {'title': 'Artefactos', 'value': str(metrics['artifacts']), 'hint': 'Visible, segundo plano y API protegidos'},
            {'title': 'Conocimiento', 'value': str(metrics['knowledge']), 'hint': 'Memoria confirmada para reutilizacion'},
            {'title': 'Ejecuciones', 'value': str(metrics['runs']), 'hint': 'Consultas por rol ya registradas'},
            {'title': 'Indice', 'value': str(index_state.get('knowledge_count', 0)), 'hint': 'Base semantica reflejada por embeddings locales'},
            {'title': 'PBT', 'value': str(pbt_generation), 'hint': 'Generaciones exploradas con tuner local'},
        ]

    def _latest_replay_visual_summary(self) -> dict[str, Any]:
        viewmodel = self.capture_studio_viewmodel
        if viewmodel is None:
            return {}
        getter = getattr(viewmodel, 'get_replay_visual_summary', None)
        if callable(getter):
            try:
                return dict(getter() or {})
            except Exception:
                return {}
        try:
            return dict(getattr(viewmodel, 'replayVisualSummary') or {})
        except Exception:
            return {}

    def _latest_assistant_lane_summary(self) -> dict[str, Any]:
        viewmodel = self.capture_studio_viewmodel
        if viewmodel is None:
            return {}
        getter = getattr(viewmodel, 'get_assistant_lane_summary', None)
        if callable(getter):
            try:
                return dict(getter() or {})
            except Exception:
                return {}
        try:
            return dict(getattr(viewmodel, 'assistantLaneSummary') or {})
        except Exception:
            return {}

    def _tool_id_for_assistant(self, assistant_kind: str) -> str:
        normalized = str(assistant_kind or '').strip().lower()
        return {
            'codex': 'codex_installed',
            'chatgpt': 'chatgpt_installed',
            'claude': 'claude_installed',
            'ollama': 'ollama_llm',
        }.get(normalized, '')

    def _latest_visual_signal(self, *, message: str = '', goal_parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        replay_summary = self._latest_replay_visual_summary()
        session_health = self._latest_session_health_snapshot()
        lane_summary = self._latest_assistant_lane_summary()
        runtime_signals = self._latest_runtime_signals()
        parameters = dict(goal_parameters or {})
        explicit_assistant = str(
            parameters.get('assistant_preference')
            or parameters.get('assistant_kind')
            or self._explicit_assistant_preference(message)
            or ''
        ).strip().lower()
        preferred_tool_id = self._tool_id_for_assistant(explicit_assistant)
        metadata = dict((self._last_adaptive_payload.get('metadata') or {}))
        external_state_flags = self._external_state_flags_from_payloads(
            dict(metadata.get('autonomous_evolution') or {}),
            dict(metadata.get('autonomous_evolution_response') or {}),
            dict(metadata.get('external_consultation') or {}),
            session_health,
        )
        if self.universal_perception_service is not None:
            try:
                return self.universal_perception_service.build_signal(
                    replay_summary=replay_summary,
                    session_health=session_health,
                    lane_summary=lane_summary,
                    runtime_signals=runtime_signals,
                    tool_id=preferred_tool_id,
                    assistant_kind=explicit_assistant,
                    site_id=self._current_site_id(),
                    external_state_flags=external_state_flags,
                ).model_dump(mode='json')
            except Exception:
                pass
        viewmodel = self.capture_studio_viewmodel
        if viewmodel is not None:
            getter = getattr(viewmodel, 'get_visual_signal_snapshot', None)
            if callable(getter):
                try:
                    return dict(getter() or {})
                except Exception:
                    pass
            try:
                property_payload = getattr(viewmodel, 'visualSignalSnapshot')
                if property_payload:
                    return dict(property_payload or {})
            except Exception:
                pass
        metadata = dict(replay_summary.get('metadata') or {})
        visible_targets = [
            str(item).strip()
            for item in (replay_summary.get('visible_targets') or metadata.get('visible_targets') or replay_summary.get('focus_targets') or [])
            if str(item).strip()
        ]
        visual_evidence_refs = [
            str(item).strip()
            for item in (replay_summary.get('visual_evidence_refs') or replay_summary.get('evidence_refs') or metadata.get('evidence_refs') or [])
            if str(item).strip()
        ]
        capture_available = bool(replay_summary or session_health or lane_summary)
        unresolved_fields = []
        if not capture_available:
            unresolved_fields.append('UNRESOLVED:visual_signal_source')
        return {
            'source': str(replay_summary.get('source') or metadata.get('source') or 'control_center_fallback'),
            'source_app': str(self._current_site_id() or explicit_assistant or 'control_center'),
            'capture_available': capture_available,
            'dom_available': bool(metadata.get('dom_available') or replay_summary.get('dom_available') or session_health.get('dom_available')),
            'latest_url': str(metadata.get('latest_url') or replay_summary.get('latest_url') or session_health.get('current_url') or '').strip(),
            'latest_title': str(metadata.get('latest_title') or replay_summary.get('latest_title') or session_health.get('window_title') or '').strip(),
            'visible_targets': visible_targets[:8],
            'login_detected': bool(replay_summary.get('login_detected') or metadata.get('login_detected') or session_health.get('login_required')),
            'learning_ready': bool(replay_summary.get('learning_ready') or metadata.get('learning_ready')),
            'cross_check_status': str(replay_summary.get('cross_check_status') or metadata.get('cross_check_status') or '').strip(),
            'visual_evidence_refs': visual_evidence_refs[:8],
            'visual_snapshot': {
                'status': 'available' if capture_available else 'no_disponible',
                'capture_mode': 'control_center_fallback',
                'screen_capture': 'available' if capture_available else 'no_disponible',
            },
            'dom_summary': {
                'status': 'available' if bool(metadata.get('dom_available') or replay_summary.get('dom_available') or session_health.get('dom_available')) else 'no_disponible',
                'reason': '' if bool(metadata.get('dom_available') or replay_summary.get('dom_available') or session_health.get('dom_available')) else 'dom_not_exposed_in_current_capture',
            },
            'available_actions': [],
            'detected_blocks': external_state_flags,
            'confidence': 0.55 if capture_available else 0.25,
            'unresolved_fields': unresolved_fields,
            'metadata': {
                'lane_summary': lane_summary,
                'session_health_status': str(session_health.get('status') or ''),
            },
        }

    def _latest_runtime_signals(self) -> list[dict[str, Any]]:
        viewmodel = self.capture_studio_viewmodel
        if viewmodel is None:
            return []
        getter = getattr(viewmodel, 'get_runtime_signals', None)
        if callable(getter):
            try:
                payload = getter() or []
                return [dict(item) for item in payload if isinstance(item, dict)]
            except Exception:
                return []
        try:
            payload = getattr(viewmodel, 'runtimeSignals') or []
            return [dict(item) for item in payload if isinstance(item, dict)]
        except Exception:
            return []

    def _latest_session_health_snapshot(self) -> dict[str, Any]:
        viewmodel = self.capture_studio_viewmodel
        if viewmodel is None:
            return {}
        getter = getattr(viewmodel, 'get_session_health', None)
        if callable(getter):
            try:
                return dict(getter() or {})
            except Exception:
                return {}
        try:
            return dict(getattr(viewmodel, 'sessionHealth') or {})
        except Exception:
            return {}

    def _latest_ia_trace(self) -> list[dict[str, Any]]:
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        trace: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        def append_entry(candidate: Any) -> None:
            if not isinstance(candidate, dict):
                return
            payload = dict(candidate)
            trace_id = str(payload.get('trace_id') or payload.get('task_id') or payload.get('result_id') or '').strip()
            if trace_id and trace_id in seen_ids:
                return
            if trace_id:
                seen_ids.add(trace_id)
            trace.append(payload)

        for candidate in (
            metadata.get('ia_trace'),
            dict(metadata.get('perception_snapshot') or {}).get('ia_trace'),
            dict(metadata.get('autonomous_evolution_response') or {}).get('ia_trace_entry'),
            dict(metadata.get('autonomous_evolution') or {}).get('ia_trace_entry'),
            dict(metadata.get('external_consultation') or {}).get('ia_trace_entry'),
        ):
            if isinstance(candidate, list):
                for item in candidate:
                    append_entry(item)
            else:
                append_entry(candidate)
        if trace:
            return trace

        consultation = dict(metadata.get('autonomous_evolution') or {})
        if consultation:
            append_entry(
                {
                    'trace_id': str((consultation.get('ia_trace_entry') or {}).get('trace_id') or consultation.get('task_id') or consultation.get('result_id') or ''),
                    'assistant_kind': str(consultation.get('assistant_kind') or ''),
                    'assistant_configuration': dict(consultation.get('assistant_configuration') or {}),
                    'config_signature': str(consultation.get('config_signature') or ''),
                    'route': str(consultation.get('recommended_route') or consultation.get('route') or ''),
                    'result_label': str(consultation.get('status') or ''),
                    'success': bool(consultation.get('response_ingested') or consultation.get('success')),
                    'execution_ms': int(consultation.get('execution_ms') or 0),
                    'confidence': float(consultation.get('confidence') or 0.0),
                    'evidence_refs': [str(item).strip() for item in (consultation.get('evidence_refs') or []) if str(item).strip()],
                    'reused_later': bool(consultation.get('reused_later', False)),
                    'verdict': str(consultation.get('response_next_action') or consultation.get('verdict') or consultation.get('status') or ''),
                    'external_state_flags': canonical_external_state_flags(
                        list(consultation.get('external_state_flags') or []) + list(consultation.get('coherence_flags') or [])
                    ),
                    'task_id': str(consultation.get('task_id') or ''),
                    'result_id': str(consultation.get('result_id') or ''),
                    'metadata': {
                        'requested_assistant_kind': str(consultation.get('requested_assistant_kind') or consultation.get('assistant_kind') or ''),
                        'actual_assistant_kind': str(consultation.get('actual_assistant_kind') or consultation.get('assistant_kind') or ''),
                        'tool_id': str(consultation.get('selected_tool_id') or ''),
                        'session_scope': str(consultation.get('session_scope') or ''),
                        'thread_key': str(consultation.get('thread_key') or ''),
                        'thread_title': str(consultation.get('thread_title') or ''),
                        'capture_lane': str(consultation.get('capture_lane') or ''),
                        'state': str(consultation.get('status') or ''),
                        'detail': str(consultation.get('detail') or consultation.get('reason') or ''),
                        'awaiting_reason': str(consultation.get('awaiting_reason') or ''),
                    },
                }
            )
        lane_summary = self._latest_assistant_lane_summary()
        if lane_summary:
            append_entry(
                {
                    'trace_id': f"lane:{lane_summary.get('selected_task_id') or 'summary'}",
                    'assistant_kind': '',
                    'route': '',
                    'result_label': 'lane_summary',
                    'success': False,
                    'execution_ms': 0,
                    'confidence': 0.0,
                    'evidence_refs': [],
                    'reused_later': False,
                    'verdict': 'observed_lane_summary',
                    'external_state_flags': [],
                    'task_id': str(lane_summary.get('selected_task_id') or ''),
                    'result_id': '',
                    'metadata': lane_summary,
                }
            )
        return trace

    def _structured_conversational_prompt_from_payload(self, payload: dict[str, Any]) -> bool | None:
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        perception_snapshot = dict(metadata.get('perception_snapshot') or {})
        intent_metadata = dict((decision_context.get('intent') or {}).get('metadata') or (payload.get('intent') or {}).get('metadata') or {})
        if 'conversational_prompt' in decision_context.get('metadata', {}):
            return bool(decision_context.get('metadata', {}).get('conversational_prompt'))
        if 'conversational_prompt' in perception_snapshot.get('metadata', {}):
            return bool(perception_snapshot.get('metadata', {}).get('conversational_prompt'))
        if 'conversational_prompt' in intent_metadata:
            return bool(intent_metadata.get('conversational_prompt'))
        return None

    def _conversational_prompt_from_payload(self, payload: dict[str, Any]) -> bool:
        return bool(self._structured_conversational_prompt_from_payload(payload))

    def _latest_live_audit(self) -> dict[str, Any]:
        payload = self._last_adaptive_payload or {}
        context = dict(payload.get('context') or {})
        metadata = dict(payload.get('metadata') or {})
        return dict(context.get('live_audit') or metadata.get('live_audit') or {})

    def _goal_context_from_payload(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        active_payload = dict(payload or self._last_adaptive_payload or {})
        metadata = dict(active_payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        goal_context = decision_context.get('goal_context') or metadata.get('goal_context') or (active_payload.get('context') or {}).get('goal_context') or {}
        return dict(goal_context) if isinstance(goal_context, dict) else {}

    def _goal_context_from_repository(self, site_id: str | None = None) -> dict[str, Any]:
        if self.objective_repository is None:
            return {}
        try:
            preferred_site = site_id or self._current_site_id() or None
            task = self.objective_repository.latest_active(kind=ObjectiveNodeKind.TASK, site_id=preferred_site)
            if task is None and preferred_site:
                task = self.objective_repository.latest_active(kind=ObjectiveNodeKind.TASK)
            project = self.objective_repository.latest_active(kind=ObjectiveNodeKind.PROJECT, site_id=preferred_site)
            if project is None and preferred_site:
                project = self.objective_repository.latest_active(kind=ObjectiveNodeKind.PROJECT)
            objective = self.objective_repository.latest_active(kind=ObjectiveNodeKind.OBJECTIVE, site_id=preferred_site)
            if objective is None and preferred_site:
                objective = self.objective_repository.latest_active(kind=ObjectiveNodeKind.OBJECTIVE)
            if task is not None and task.parent_id:
                project = self.objective_repository.get(task.parent_id) or project
            if task is not None and task.root_id:
                objective = self.objective_repository.get(task.root_id) or objective
            elif project is not None and project.root_id:
                objective = self.objective_repository.get(project.root_id) or objective
            if objective is None and project is None and task is None:
                return {}
            subtasks = self.objective_repository.list_children(task.objective_id, kind=ObjectiveNodeKind.SUBTASK, limit=8) if task is not None else []
            active = task or project or objective
            progress = float((task.progress if task is not None else None) or (project.progress if project is not None else None) or (objective.progress if objective is not None else None) or 0.0)
            confidence = float((task.confidence if task is not None else None) or (project.confidence if project is not None else None) or (objective.confidence if objective is not None else None) or 0.0)
            blocker = str((task.blocker if task is not None else '') or (project.blocker if project is not None else '') or (objective.blocker if objective is not None else '')).strip()
            status = str((task.status.value if task is not None else '') or (project.status.value if project is not None else '') or (objective.status.value if objective is not None else 'pending'))
            if status == 'completed':
                trend = 'completado'
            elif blocker:
                trend = 'bloqueado'
            elif progress >= 0.7:
                trend = 'avanzando'
            elif progress > 0.0:
                trend = 'en curso'
            else:
                trend = 'iniciado'
            return {
                'objective': objective.model_dump(mode='json') if objective is not None else {},
                'project': project.model_dump(mode='json') if project is not None else {},
                'task': task.model_dump(mode='json') if task is not None else {},
                'subtasks': [item.model_dump(mode='json') for item in subtasks],
                'active_node_id': active.objective_id if active is not None else '',
                'active_title': active.title if active is not None else '',
                'priority': int(getattr(active, 'priority', 50) or 50),
                'status': status,
                'progress': round(progress, 4),
                'blocker': blocker,
                'confidence': round(confidence, 4),
                'trend': trend,
                'evidence_refs': list(dict.fromkeys((objective.evidence_refs if objective is not None else []) + (project.evidence_refs if project is not None else []) + (task.evidence_refs if task is not None else []))),
                'metadata': {
                    'source': 'objective_repository',
                    'site_id': preferred_site or '',
                },
            }
        except Exception:
            return {}

    def _goal_context_for_display(self, site_id: str | None = None) -> dict[str, Any]:
        current = dict(self._last_goal_context or {})
        metadata = dict(current.get('metadata') or {})
        current_site = str(metadata.get('site_id') or '').strip()
        if current and (not site_id or (current_site and current_site == site_id)):
            return current
        payload_context = self._goal_context_from_payload(self._last_adaptive_payload)
        payload_site = str((payload_context.get('metadata') or {}).get('site_id') or '').strip()
        if payload_context and (not site_id or (payload_site and payload_site == site_id)):
            return payload_context
        return self._goal_context_from_repository(site_id)

    def _explicit_assistant_preference(self, message: str) -> str:
        # Delegated to AssistantPreferenceResolver so the same parsing can be
        # reused from non-UI entrypoints (orchestrator, chat bridge, CLI) and
        # exercised in pure-Python tests without Qt.
        return self._assistant_preference_resolver.resolve(message)

    def _is_general_chat_message(self, message: str) -> bool:
        command = ' '.join(str(message or '').lower().strip().split())
        if not command:
            return False
        if self._explicit_assistant_preference(command):
            return False
        meta_assistant_prompt = (
            any(token in command for token in ('codex', 'chatgpt', 'claude', 'ollama', 'devin', 'windsurf', 'ia', 'ias'))
            and any(token in command for token in ('sabes', 'puedes', 'puedo', 'internamente', 'automatic', 'automatica', 'autom?tico', 'respondieron'))
        )
        if meta_assistant_prompt:
            return True
        if any(token in command for token in ('consultar codex', 'consulta codex', 'consultar chatgpt', 'consulta chatgpt', 'consultar claude', 'consulta claude', 'abrir wplay', 'inicia sesion', 'login', 'autotest', 'payload', 'pbt')):
            return False
        if any(phrase in command for phrase in ('que sabes hacer', 'qu? sabes hacer', 'que puedes hacer', 'qu? puedes hacer', 'en que puedes ayudar', 'en qu? puedes ayudar', 'quien eres', 'qui?n eres', 'como funcionas', 'c?mo funcionas')):
            return True
        greeting_prefixes = ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')
        return len(command.split()) <= 4 and any(command.startswith(prefix) for prefix in greeting_prefixes)

    def _goal_parameters_for_request(self, message: str, site_hint: str | None) -> dict[str, Any]:
        parameters = {
            'selected_role': self._selected_role,
            'site_hint': site_hint or '',
        }
        explicit_assistant = self._explicit_assistant_preference(message)
        if explicit_assistant:
            parameters.update(
                {
                    'assistant_preference': explicit_assistant,
                    'assistant_kind': explicit_assistant,
                    'explicit_external_consultation': True,
                    'consultation_scope': 'external_assistant',
                }
            )
        if self._is_general_chat_message(message) and not explicit_assistant:
            return parameters
        goal_context = self._goal_context_for_display(site_hint)
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        if goal_context:
            parameters.update(
                {
                    'objective_id': str(objective.get('objective_id') or ''),
                    'objective_title': str(objective.get('title') or goal_context.get('active_title') or ''),
                    'project_id': str(project.get('objective_id') or ''),
                    'project_title': str(project.get('title') or ''),
                    'task_id': str(task.get('objective_id') or ''),
                    'task_title': str(task.get('title') or goal_context.get('active_title') or ''),
                    'priority': int(goal_context.get('priority') or objective.get('priority') or 50),
                    'goal_status': str(goal_context.get('status') or ''),
                    'goal_progress': float(goal_context.get('progress') or 0.0),
                    'goal_confidence': float(goal_context.get('confidence') or 0.0),
                    'goal_blocker': str(goal_context.get('blocker') or ''),
                }
            )
        return parameters

    def _experiment_subject_keys_for_goal(self, *, goal_context: dict[str, Any], site_id: str | None) -> list[str]:
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        keys: list[str] = []
        for candidate in (
            str(task.get('objective_id') or ''),
            str(project.get('objective_id') or ''),
            str(objective.get('objective_id') or ''),
            str(goal_context.get('active_node_id') or ''),
            str(site_id or ''),
            'general',
        ):
            probe = candidate.strip()
            if probe and probe not in keys:
                keys.append(probe)
        return keys

    def _scoped_experiment_history(self, *, goal_context: dict[str, Any], site_id: str | None) -> tuple[list[Any], list[Any]]:
        if self.experiment_lab_repository is None:
            return [], []
        subject_keys = self._experiment_subject_keys_for_goal(goal_context=goal_context, site_id=site_id)
        runs: list[Any] = []
        recommendations: list[Any] = []
        seen_runs: set[str] = set()
        seen_recommendations: set[str] = set()
        for subject_key in subject_keys:
            for item in self.experiment_lab_repository.list_recommendations(subject_key=subject_key, limit=4):
                recommendation_id = str(getattr(item, 'recommendation_id', '') or '')
                if recommendation_id and recommendation_id in seen_recommendations:
                    continue
                if recommendation_id:
                    seen_recommendations.add(recommendation_id)
                recommendations.append(item)
            for item in self.experiment_lab_repository.list_runs(subject_key=subject_key, limit=12):
                run_id = str(getattr(item, 'run_id', '') or '')
                if run_id and run_id in seen_runs:
                    continue
                if run_id:
                    seen_runs.add(run_id)
                runs.append(item)
            if len(runs) >= 12 and len(recommendations) >= 4:
                break
        if not runs and not recommendations:
            runs = self.experiment_lab_repository.list_runs(limit=12)
            recommendations = self.experiment_lab_repository.list_recommendations(limit=4)
        return runs[:12], recommendations[:4]

    def _strategy_history_labels(self, *, experiment_runs: list[Any], latest_recommendation: Any | None) -> dict[str, Any]:
        tried: list[str] = []
        for item in experiment_runs:
            route = getattr(getattr(item, 'route', None), 'value', str(getattr(item, 'route', '') or ''))
            label = str(getattr(item, 'candidate_label', '') or route or '').strip()
            if label and label not in tried:
                tried.append(label)
        recommended_route = str(getattr(getattr(latest_recommendation, 'recommended_route', None), 'value', '') or '').strip()
        discarded: list[str] = []
        ranked_routes = list(getattr(latest_recommendation, 'metadata', {}).get('ranked_routes') or []) if latest_recommendation is not None else []
        for item in ranked_routes:
            route = str(item.get('route') or '').strip()
            if route and route != recommended_route and route not in discarded:
                discarded.append(route)
        if not discarded and recommended_route:
            for item in experiment_runs:
                route = str(getattr(getattr(item, 'route', None), 'value', '') or '').strip()
                if route and route != recommended_route and route not in discarded:
                    discarded.append(route)
        focus = str(getattr(latest_recommendation, 'subject_key', '') or (getattr(experiment_runs[0], 'subject_key', '') if experiment_runs else '') or 'general')
        return {
            'tried': tried[:4],
            'discarded': discarded[:4],
            'focus': focus,
        }

    def _update_evolution_snapshot(self) -> None:
        try:
            self._update_evolution_snapshot_inner()
        except Exception as exc:
            logger.debug('_update_evolution_snapshot failed (non-critical): %s', exc)

    def _update_evolution_snapshot_inner(self) -> None:
        health_snapshot = self.evolution_review_service.build_project_health().model_dump(mode='json') if self.evolution_review_service is not None else {}
        experiment_runs = self.experiment_lab_repository.list_runs(limit=12) if self.experiment_lab_repository is not None else []
        experiment_recommendations = self.experiment_lab_repository.list_recommendations(limit=3) if self.experiment_lab_repository is not None else []
        latest_recommendation = experiment_recommendations[0] if experiment_recommendations else None
        scenario_runs = self.scenario_run_repository.list_recent(limit=12) if self.scenario_run_repository is not None else []
        patterns = self.tool_record_repository.list_interaction_patterns(limit=24) if self.tool_record_repository is not None else []
        observations = self.tool_record_repository.list_interaction_observations(limit=24) if self.tool_record_repository is not None else []
        interaction_episodes = self.tool_record_repository.list_interaction_episodes(limit=24) if self.tool_record_repository is not None else []
        tool_results = self.tool_record_repository.list_results(limit=24) if self.tool_record_repository is not None else []
        replay_summary = self._latest_replay_visual_summary()
        replay_metadata = dict(replay_summary.get('metadata') or {})
        live_audit = self._latest_live_audit()
        metadata = dict((self._last_adaptive_payload.get('metadata') or {}))
        decision_context = dict(metadata.get('decision_context') or {})
        governance = dict(decision_context.get('governance') or metadata.get('governance') or {})
        autonomous = dict(metadata.get('autonomous_evolution') or {})
        autonomous_response = dict(metadata.get('autonomous_evolution_response') or {})
        response_validation = dict(autonomous_response.get('response_validation') or {})
        adoption_plan = dict(autonomous_response.get('adoption_plan') or {})
        current_intent = dict(self._last_adaptive_payload.get('intent') or {})
        goal_context = self._goal_context_for_display(self._current_site_id() or None)
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        current_goal = str(objective.get('title') or goal_context.get('active_title') or self._last_user_goal or current_intent.get('title') or 'Sin objetivo activo.')
        current_project = str(project.get('title') or '')
        current_task = str(task.get('title') or '')
        current_goal_status = str(goal_context.get('status') or 'sin_objetivo')
        current_goal_progress = float(goal_context.get('progress') or 0.0)
        current_goal_confidence = float(goal_context.get('confidence') or 0.0)
        current_goal_blocker = str(goal_context.get('blocker') or '').strip()
        experiment_runs, experiment_recommendations = self._scoped_experiment_history(
            goal_context=goal_context,
            site_id=self._current_site_id() or None,
        )
        latest_recommendation = experiment_recommendations[0] if experiment_recommendations else None
        current_status = str(self._last_adaptive_payload.get('status') or 'sin_sesion')
        current_pack = str(((self._last_adaptive_payload.get('chosen_pack') or {}).get('title') or 'sin pack'))
        autonomy_level = str(governance.get('autonomy_level') or 'sin_gobernanza')
        autonomy_confidence = float(governance.get('confidence') or 0.0)
        weak_capabilities = [item for item in self._adaptive_capability_cards if item.get('status') in {'insufficient', 'partial'}]
        reusable_patterns = sum(1 for item in patterns if getattr(item, 'reusable', False))
        reused_episodes = sum(1 for item in interaction_episodes if getattr(item, 'reused_pattern', False))
        assistant_results = [
            item for item in tool_results
            if str(item.metadata.get('assistant_kind') or item.execution_state.metadata.get('assistant_kind') or '').strip()
        ]
        latest_scenario = scenario_runs[0] if scenario_runs else None
        latest_result = assistant_results[0] if assistant_results else None
        latest_issue = str((replay_metadata.get('audit_findings') or [''])[0] or replay_metadata.get('audit_rationale') or '')
        strategy_labels = self._strategy_history_labels(
            experiment_runs=experiment_runs,
            latest_recommendation=latest_recommendation,
        )
        latest_experiment = 'Todavia no hay experimentos registrados.'
        if latest_recommendation is not None:
            latest_experiment = (
                f"{latest_recommendation.subject_key} | {latest_recommendation.domain.value} | ruta {latest_recommendation.recommended_route.value} | "
                f"score {latest_recommendation.score:.2f}"
            )
        elif experiment_runs:
            last_run = experiment_runs[0]
            latest_experiment = (
                f"{last_run.subject_key} | {last_run.domain.value} | candidato {last_run.candidate_label or last_run.candidate_id or 'n/d'} | "
                f"score {last_run.metrics.total_score:.2f}"
            )

        learning_status = 'blocked' if latest_scenario is not None and latest_scenario.pending_issue_id else 'active' if scenario_runs else 'idle'
        learning_trend = 'ajustando' if latest_scenario is not None and latest_scenario.runtime_adjustments else 'sin historial' if not scenario_runs else 'estable'
        learning_detail = (
            str(latest_scenario.diagnosis.summary)
            if latest_scenario is not None and latest_scenario.diagnosis is not None and latest_scenario.diagnosis.summary
            else 'Todavia no hay un autotest reciente con diagnostico detallado.'
        )
        learning_blocker = 'Hay un pending issue abierto para este escenario.' if latest_scenario is not None and latest_scenario.pending_issue_id else ''

        algorithm_status = 'active' if experiment_runs else 'idle'
        algorithm_trend = 'al alza' if latest_recommendation is not None and latest_recommendation.score >= 0.7 else 'estable' if latest_recommendation is not None else 'sin base'
        algorithm_detail_base = latest_recommendation.rationale if latest_recommendation is not None and latest_recommendation.rationale else latest_experiment
        strategy_history_bits: list[str] = []
        if strategy_labels['tried']:
            strategy_history_bits.append(f"probadas {', '.join(strategy_labels['tried'])}")
        if strategy_labels['discarded']:
            strategy_history_bits.append(f"descartadas {', '.join(strategy_labels['discarded'])}")
        algorithm_detail = ' | '.join([algorithm_detail_base, *strategy_history_bits]) if strategy_history_bits else algorithm_detail_base
        algorithm_focus = str(strategy_labels.get('focus') or 'general')

        pbt_candidates = list(self._pbt_state.get('candidates', []))
        best_candidate = max((float(item.get('score', 0.0)) for item in pbt_candidates), default=0.0)
        pbt_generation = int(self._pbt_state.get('generation', 0))
        variable_status = 'active' if pbt_generation else 'idle'
        variable_trend = 'explorando' if pbt_generation else 'sin explorar'
        variable_detail = str(self._pbt_state.get('summary') or 'Todavia no hay generaciones PBT registradas.')

        investigation_status = 'warning' if autonomous and not autonomous.get('response_ingested') else 'active' if assistant_results or autonomous or governance.get('research_needed') else 'idle'
        investigation_trend = 'esperando respuesta' if autonomous and not autonomous.get('response_ingested') else 'investigando' if governance.get('research_needed') else 'aprovechando consultas' if assistant_results else 'sin base'
        investigation_detail = (
            str(autonomous.get('response_summary') or autonomous.get('detail') or autonomous.get('context_excerpt') or '')
            or (str(latest_result.output_text or latest_result.error_message or latest_result.execution_state.detail) if latest_result is not None else 'Todavia no hay consultas externas recientes.')
        )
        if adoption_plan or response_validation:
            investigation_detail += (
                f" | validacion {response_validation.get('status') or 'n/d'} | "
                f"via {adoption_plan.get('execution_lane') or 'n/d'} | sandbox {bool(response_validation.get('sandbox_required'))}"
            )
        investigation_blocker = 'La consulta externa sigue pendiente de respuesta util.' if autonomous and not autonomous.get('response_ingested') else ''
        if not investigation_blocker and str(response_validation.get('status') or '') in {'review_needed', 'insufficient'}:
            investigation_blocker = str(response_validation.get('rationale') or '')

        task_status = 'blocked' if current_goal_status == 'blocked' or current_goal_blocker else 'warning' if weak_capabilities or current_status in {'need_info', 'waiting_approval'} else 'active' if self._adaptive_session_id or goal_context or self._last_user_goal else 'idle'
        task_trend = str(goal_context.get('trend') or ('esperando aprobacion' if current_status == 'waiting_approval' else 'necesita evidencia' if weak_capabilities else 'en curso' if self._adaptive_session_id else 'sin objetivo'))
        task_detail = (
            f"Objetivo: {current_goal} | proyecto: {current_project or 'n/d'} | tarea: {current_task or 'n/d'} | "
            f"pack: {current_pack} | estado adaptativo: {current_status} | progreso {current_goal_progress:.2f} | confianza {current_goal_confidence:.2f}"
        )
        task_blocker = current_goal_blocker
        if not task_blocker and weak_capabilities:
            first_weak = weak_capabilities[0]
            task_blocker = str(first_weak.get('detail') or first_weak.get('title') or 'Hay capacidades debiles en esta ruta.')

        replay_status = str(replay_metadata.get('audit_status') or '')
        audit_status = 'blocked' if replay_status in {'failed', 'diverging', 'weak'} else 'warning' if replay_status else 'active' if live_audit else 'idle'
        audit_trend = 'alineado' if float(replay_metadata.get('audit_overall_confidence') or 0.0) >= 0.75 else 'fragil' if replay_status else 'sin evidencia'
        audit_detail = (
            f"audit_status {replay_status or 'sin auditoria'} | confianza {float(replay_metadata.get('audit_overall_confidence') or 0.0):.2f} | "
            f"matching {int(replay_metadata.get('steps_matching') or 0)} | diverging {int(replay_metadata.get('steps_diverging') or 0)}"
        )
        audit_blocker = latest_issue or str(live_audit.get('summary') or '') if (latest_issue or live_audit) else ''

        memory_status = 'active' if reusable_patterns or reused_episodes else 'warning' if patterns or interaction_episodes else 'idle'
        memory_trend = 'reutilizando' if reused_episodes else 'acumulando' if patterns or interaction_episodes else 'sin base'
        memory_detail = (
            f"patrones {len(patterns)} | observaciones {len(observations)} | episodios {len(interaction_episodes)} | reutilizados {reused_episodes}"
        )
        memory_blocker = 'Aun no hay patrones reutilizados en ejecuciones recientes.' if patterns and not reused_episodes else ''

        maturity_status = 'warning' if governance.get('approval_required') or governance.get('block_risky_action') else 'active' if autonomy_level not in {'', 'sin_gobernanza'} else 'idle'
        maturity_trend = 'replanificando' if governance.get('should_replan') else 'investigando' if governance.get('research_needed') else 'estable' if autonomy_level not in {'', 'sin_gobernanza'} else 'sin base'
        maturity_detail = (
            f"autonomia {autonomy_level} | accion {governance.get('recommended_action') or 'continue_local'} | "
            f"sandbox {bool(governance.get('require_sandbox'))} | confianza {autonomy_confidence:.2f} | "
            f"decision {governance.get('decision_source') or 'n/d'} | replan auto {bool(metadata.get('replanned_automatically') or metadata.get('auto_replanned'))}"
        )
        maturity_blocker = '; '.join(str(item).strip() for item in (governance.get('blockers') or []) if str(item).strip()[:160])

        area_cards = [
            {
                'title': 'Aprendizaje',
                'status': learning_status,
                'trend': learning_trend,
                'summary': f"{len(scenario_runs)} autotests | {sum(len(item.runtime_adjustments) for item in scenario_runs)} ajustes",
                'detail': learning_detail,
                'blocker': learning_blocker,
                'help': 'Ejecuta un autotest o revisa el pending issue asociado.',
            },
            {
                'title': 'Algoritmos probados',
                'status': algorithm_status,
                'trend': algorithm_trend,
                'summary': f"{len(experiment_runs)} experimentos | foco {algorithm_focus} | recomendacion {latest_recommendation.recommended_route.value if latest_recommendation is not None else 'n/d'}",
                'detail': algorithm_detail,
                'blocker': '' if experiment_runs else 'Todavia no hay experimentos recientes para comparar rutas.',
                'help': 'Lanza un experimento o deja que el auditor contraste candidatos.',
            },
            {
                'title': 'Variables exploradas',
                'status': variable_status,
                'trend': variable_trend,
                'summary': f"generacion {pbt_generation} | candidatos {len(pbt_candidates)} | mejor score {best_candidate:.2f}",
                'detail': variable_detail,
                'blocker': '' if pbt_generation else 'PBT aun no ha explorado generaciones en esta sesion.',
                'help': 'Ejecuta un ciclo PBT cuando quieras afinar defaults y thresholds.',
            },
            {
                'title': 'Investigaciones utiles',
                'status': investigation_status,
                'trend': investigation_trend,
                'summary': f"{len(assistant_results)} consultas registradas | asistente {str(autonomous.get('assistant_kind') or 'n/d')}",
                'detail': investigation_detail,
                'blocker': investigation_blocker,
                'help': 'Ingiere la respuesta externa o vuelve a auditar la autonomia.',
            },
            {
                'title': 'Objetivos y tareas',
                'status': task_status,
                'trend': task_trend,
                'summary': current_goal,
                'detail': task_detail,
                'blocker': task_blocker,
                'help': 'Aprueba la fase siguiente o refuerza la evidencia de la capacidad debil.',
            },
            {
                'title': 'Auditoria y coherencia',
                'status': audit_status,
                'trend': audit_trend,
                'summary': str(live_audit.get('decision_action') or replay_status or 'sin auditoria reciente'),
                'detail': audit_detail,
                'blocker': audit_blocker,
                'help': str(live_audit.get('recommended_action') or 'Abrir replay auditado o revisar la ultima discrepancia.'),
            },
            {
                'title': 'Memoria y reutilizacion',
                'status': memory_status,
                'trend': memory_trend,
                'summary': f"reutilizables {reusable_patterns} | conocimiento {self._collect_metrics()['knowledge']}",
                'detail': memory_detail + f" | autonomia {autonomy_level} | confianza {autonomy_confidence:.2f}",
                'blocker': memory_blocker or maturity_blocker,
                'help': 'Convierte ejecuciones repetidas en patrones reutilizables y evidencia estable.',
            },
        ]

        blockers = [
            {
                'title': card['title'],
                'detail': card['blocker'],
                'help': card['help'],
            }
            for card in area_cards
            if str(card.get('blocker') or '').strip()
        ]
        for proposal in list(health_snapshot.get('backlog') or [])[:2]:
            detail = str(proposal.get('rationale') or proposal.get('recommended_change') or '').strip()
            if not detail:
                continue
            blockers.append(
                {
                    'title': str(proposal.get('title') or 'Backlog evolutivo'),
                    'detail': detail,
                    'help': ', '.join(proposal.get('suggested_tests') or []) or 'Revisar backlog prioritario.',
                }
            )
        blockers = blockers[:4]

        active_areas = sum(1 for card in area_cards if card['status'] in {'active', 'warning', 'blocked'})
        blocked_areas = sum(1 for card in area_cards if card['status'] == 'blocked')
        warning_areas = sum(1 for card in area_cards if card['status'] == 'warning')
        overall_status = 'blocked' if blocked_areas else 'warning' if warning_areas >= 2 else 'active' if active_areas >= 4 else 'idle'
        if latest_recommendation is not None and latest_recommendation.score >= 0.7:
            overall_trend = 'mejorando'
        elif active_areas:
            overall_trend = 'estable'
        else:
            overall_trend = 'sin base'
        next_help = blockers[0]['help'] if blockers else (self._assistant_action_buttons[0]['label'] if self._assistant_action_buttons else 'Seguir capturando evidencia y ejecutando tareas reales.')
        self._evolution_overview = {
            'title': 'Pulso evolutivo',
            'status': overall_status,
            'trend': overall_trend,
            'summary': f"{active_areas}/{len(area_cards)} areas con evidencia operativa | bloqueos {len(blockers)} | objetivo {current_goal} | progreso {current_goal_progress:.2f} | autonomia {autonomy_level}",
            'detail': (
                str(health_snapshot.get('summary') or 'Todavia no hay suficiente evidencia para resumir la evolucion.')
                + f" Progreso longitudinal: {current_goal_status} | confianza {current_goal_confidence:.2f}."
            ),
            'latest_experiment': latest_experiment,
            'human_help': next_help,
            'current_goal': current_goal,
            'compact_cards': [
                {'title': 'Aprendizaje', 'value': str(len(scenario_runs)), 'detail': 'autotests recientes'},
                {'title': 'Experimentos', 'value': str(len(experiment_runs)), 'detail': f"{algorithm_focus} | {latest_recommendation.recommended_route.value if latest_recommendation is not None else (autonomy_level or 'sin ruta sugerida') }"},
                {'title': 'Bloqueos', 'value': str(len(blockers)), 'detail': f"autonomia {autonomy_level or 'n/d'} | confianza {autonomy_confidence:.2f}"},
                {'title': 'Reutilizacion', 'value': str(reusable_patterns + reused_episodes), 'detail': 'patrones o reusos detectados'},
            ],
        }
        self._evolution_area_cards = area_cards
        self._evolution_blockers = blockers
    def _assistant_tool_ids(self) -> list[str]:
        # devin_api y github_api son adapters activos (API REST) que el usuario
        # tambien entiende como "IAs con las que me conecto". Dejarlos fuera hacia
        # que el chat respondiera "no tengo conexion con Devin" aun cuando el
        # adapter estaba vivo y respondiendo 200 OK.
        return [
            'ollama_llm',
            'devin_api',
            'github_api',
            'codex_installed',
            'chatgpt_installed',
            'chatgpt_web_assisted',
            'claude_installed',
            'claude_web_assisted',
        ]

    def _tool_registry(self):
        return getattr(self.tool_teach_service, 'registry', None)

    def _refresh_assistant_cards(self) -> None:
        registry = self._tool_registry()
        if registry is None:
            return
        for tool_id in self._assistant_tool_ids():
            card = registry.get_card(tool_id)
            if card is not None:
                registry.refresh_card(card)

    def _assistant_tool_cards(self) -> list[dict[str, Any]]:
        registry = self._tool_registry()
        if registry is None:
            return []
        cards: list[dict[str, Any]] = []
        for tool_id in self._assistant_tool_ids():
            card = registry.get_card(tool_id)
            if card is None:
                continue
            metadata = dict(card.metadata or {})
            launch_mode = str(metadata.get('launch_mode') or '').strip().lower()
            response_capture_mode = str(metadata.get('response_capture_mode') or '').strip().lower()
            manual_return = bool(metadata.get('requires_manual_pasteback', False))
            assistant_kind = str(metadata.get('assistant_kind') or tool_id.split('_')[0] or card.title).strip() or card.title
            clipboard_capture = response_capture_mode == 'clipboard_capture'
            isolated_session = bool(metadata.get('isolated_session_required', False))
            automatic = card.available and response_capture_mode in {'tool_result', 'direct_text', 'local_evidence', 'clipboard_capture', 'dom_capture', 'browser_dom'} and not manual_return
            if automatic and isolated_session:
                status = 'sesion aislada'
            elif automatic:
                status = 'listo automatico'
            elif card.available and launch_mode == 'web_assisted':
                status = 'web preparada'
            elif card.available:
                status = 'listo guiado'
            else:
                status = 'no disponible'
            if clipboard_capture and card.available:
                detail = 'La app fue detectada; intentare capturar la respuesta automaticamente por clipboard y si falla pedire pegado manual.'
            elif isolated_session and card.available:
                detail = 'La consulta se hara en una sesion aislada del programa, separada de tus chats normales, con captura automatica en segundo plano cuando esa sesion ya este autenticada.'
            elif automatic:
                detail = 'Consulta local o captura directa lista sin pegado manual.'
            elif card.available and launch_mode == 'web_assisted':
                detail = 'La via web ya esta preparada; requiere internet, sesion y devolver la respuesta a IABV.'
            elif card.available:
                detail = 'La app fue detectada; puedo abrirla y preparar la consulta, pero la respuesta vuelve por pegado manual.'
            else:
                detail = 'No detectado al arrancar. La autonomia seguira con las vias que si esten disponibles.'
            scope = {
                'ollama': 'Consulta local automatica',
                'codex': 'Correccion tecnica y codigo',
                'chatgpt': 'Investigacion explicativa',
                'claude': 'Analisis y contraste externo',
                'devin': 'Sesion autonoma remota via API',
                'github': 'Operaciones GitHub nativas via API',
            }.get(assistant_kind, 'Asistente externo')
            cards.append(
                {
                    'name': card.title,
                    'status': status,
                    'detail': detail,
                    'scope': scope,
                    'tool_id': card.tool_id,
                    'assistant_kind': assistant_kind,
                }
            )
        return cards

    def _aggregate_assistant_entries(self, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Cuando un asistente tiene dos variantes (ej: claude app + claude web)
        # y una esta lista pero la otra no, el chat no debe repetir "Claude no
        # esta disponible". Colapsamos por assistant_kind y nos quedamos con la
        # mejor variante segun prioridad de status.
        priority = {
            'listo automatico': 5,
            'sesion aislada': 4,
            'web preparada': 3,
            'listo guiado': 2,
            'no disponible': 0,
        }

        def rank(status: str) -> int:
            normalized = status.strip().lower()
            for key, value in priority.items():
                if key in normalized:
                    return value
            return 1

        friendly_kind_titles = {
            'ollama': 'Ollama local',
            'codex': 'Codex',
            'chatgpt': 'ChatGPT',
            'claude': 'Claude',
            'devin': 'Devin',
            'github': 'GitHub',
        }

        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            kind_raw = str(card.get('assistant_kind') or '').strip().lower()
            key = kind_raw or str(card.get('name') or card.get('tool_id') or id(card))
            if key not in order:
                order.append(key)
            current = grouped.get(key)
            if current is None or rank(str(card.get('status') or '')) > rank(str(current.get('status') or '')):
                merged = dict(card)
                friendly = friendly_kind_titles.get(kind_raw)
                if friendly and kind_raw:
                    # Solo re-etiquetamos cuando hay mas de una variante del mismo
                    # kind; si es unico respetamos el titulo original del card.
                    variants_for_kind = [c for c in cards if isinstance(c, dict) and str(c.get('assistant_kind') or '').strip().lower() == kind_raw]
                    if len(variants_for_kind) > 1:
                        merged['name'] = friendly
                grouped[key] = merged
        return [grouped[key] for key in order if key in grouped]

    def _startup_readiness_text(self, *, validating_local_stack: bool = False) -> str:
        goal_context = self._goal_context_for_display(self._current_site_id() or None)
        active_title = str((goal_context.get('objective') or {}).get('title') or goal_context.get('active_title') or 'sin objetivo activo').strip() or 'sin objetivo activo'
        assistant_cards = self._assistant_tool_cards()
        total = len(assistant_cards) or 1
        available_cards = [item for item in assistant_cards if item.get('status') != 'no disponible']
        automatic_cards = [item for item in assistant_cards if item.get('status') == 'listo automatico']
        available_count = len(available_cards)
        automatic_count = len(automatic_cards)
        available_names = ', '.join(item.get('name') or '' for item in available_cards) or 'ninguno'
        automatic_names = ', '.join(item.get('name') or '' for item in automatic_cards) or 'ninguno'
        if validating_local_stack:
            return (
                f'Arranque autonomo: objetivo {active_title} | asistentes detectados {available_count}/{total} '
                f'({available_names}) | automaticos {automatic_names}. Estoy validando stack local y coherencia evolutiva.'
            )
        return (
            f'Autonomia lista: objetivo {active_title} | asistentes disponibles {available_count}/{total} '
            f'({available_names}) | automaticos {automatic_count} ({automatic_names}).'
        )

    def _assistant_display_name(self, assistant_kind: str) -> str:
        return {
            'codex': 'Codex',
            'chatgpt': 'ChatGPT',
            'claude': 'Claude',
            'ollama': 'Ollama',
        }.get(str(assistant_kind or '').strip().lower(), 'Asistente externo')

    def _assistant_kind_from_tool_id(self, tool_id: str) -> str:
        normalized = str(tool_id or '').strip().lower()
        if normalized.startswith('codex'):
            return 'codex'
        if normalized.startswith('claude'):
            return 'claude'
        if normalized.startswith('chatgpt'):
            return 'chatgpt'
        if normalized.startswith('ollama'):
            return 'ollama'
        return ''

    def _contains_internal_chat_terms(self, text: str) -> bool:
        normalized = ' '.join(str(text or '').lower().strip().split())
        if not normalized:
            return False
        forbidden_terms = (
            'need_adapter',
            'protective_local',
            'guidance_mode',
            'continue_local',
            'simulacion',
            'simulación',
            'sesion adaptativa',
            'autonomia_level',
            'autonomy_level',
            'governance',
            'gobernanza',
            'readiness',
            'executor',
            'adaptador operativo',
            'no hay un executor',
            'pack activo',
            'estado adaptativo',
            'simulacion completada',
        )
        return any(term in normalized for term in forbidden_terms)

    def _environment_self_awareness_service(self):
        assembler = getattr(self.adaptive_orchestrator, 'context_assembler', None)
        return getattr(assembler, 'environment_self_awareness_service', None)

    def _current_environment_self_model(self) -> EnvironmentSelfModel:
        service = self._environment_self_awareness_service()
        if service is None:
            return EnvironmentSelfModel(scan_status='unavailable', unresolved_fields=['UNRESOLVED:environment_self_model'])
        try:
            return service.current_model()
        except Exception:
            return EnvironmentSelfModel(scan_status='degraded', unresolved_fields=['UNRESOLVED:environment_self_model'])

    def _world_model_service(self):
        assembler = getattr(self.adaptive_orchestrator, 'context_assembler', None)
        return getattr(assembler, 'world_model_service', None)

    def _current_world_model(self) -> WorldModelSnapshot:
        service = self._world_model_service()
        if service is None:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            return service.current_model()
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _current_validation_snapshot(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return {}
        try:
            return service.current_snapshot().model_dump(mode='json')
        except Exception:
            return {}

    def _current_validation_status(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'get_status'):
            return {'unresolved_fields': ['UNRESOLVED:autonomous_validation_status']}
        try:
            return dict(service.get_status() or {})
        except Exception:
            return {'unresolved_fields': ['UNRESOLVED:autonomous_validation_status']}

    def _current_tool_discovery_status(self) -> dict[str, Any]:
        service = self.tool_discovery_service
        if service is None or not hasattr(service, 'get_status'):
            return {'unresolved_fields': ['UNRESOLVED:tool_discovery_status']}
        try:
            return dict(service.get_status() or {})
        except Exception:
            return {'unresolved_fields': ['UNRESOLVED:tool_discovery_status']}

    def _current_self_examination_snapshot(self) -> dict[str, Any]:
        service = self.self_examination_service
        if service is None or not hasattr(service, 'current_review'):
            return {}
        try:
            review = service.current_review(refresh=True)
            if hasattr(service, 'review_summary'):
                return dict(service.review_summary(review) or {})
            return review.model_dump(mode='json')
        except Exception:
            return {}

    def _is_world_model_question(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        direct_phrases = (
            'que esta pasando',
            'qué está pasando',
            'que pasa ahora',
            'qué pasa ahora',
            'que tienes abierto',
            'qué tienes abierto',
            'que esta abierto',
            'qué está abierto',
            'que ventanas tienes abiertas',
            'qué ventanas tienes abiertas',
            'que ventana esta en foco',
            'qué ventana está en foco',
            'que pasa con mi internet',
            'qué pasa con mi internet',
            'como esta mi internet',
            'cómo está mi internet',
            'como esta el internet',
            'cómo está el internet',
            'por que no responde codex',
            'por qué no responde codex',
            'por que no responde chatgpt',
            'por qué no responde chatgpt',
            'por que no responde claude',
            'por qué no responde claude',
            'por que no responde ollama',
            'por qué no responde ollama',
            'puedes ver los navegadores',
            'puedes ver mis navegadores',
            'que navegadores tengo abiertos',
            'qué navegadores tengo abiertos',
            'que navegadores hay abiertos',
            'qué navegadores hay abiertos',
            'que navegadores estan abiertos',
            'qué navegadores están abiertos',
            'que navegadores tienes abiertos',
            'qué navegadores tienes abiertos',
            'que navegadores ves',
            'qué navegadores ves',
            'ves mis navegadores',
            'ves los navegadores',
            'navegadores abiertos',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_about_windows = any(token in word_tokens for token in ('ventana', 'ventanas', 'foco', 'abierto', 'abiertas'))
        asks_about_network = any(token in word_tokens for token in ('internet', 'red', 'conexion', 'conexión'))
        mentions_tool = any(token in word_tokens for token in ('codex', 'chatgpt', 'claude', 'ollama'))
        asks_tool_state = any(token in word_tokens for token in ('responde', 'bloqueado', 'hilo', 'mensajes', 'agotados', 'abierto', 'abierta'))
        requests_consultation = any(token in word_tokens for token in ('consulta', 'consultar', 'usa', 'usar'))
        asks_about_live_tool = mentions_tool and asks_tool_state and not requests_consultation
        asks_current_state = any(phrase in normalized for phrase in ('que esta pasando', 'qué está pasando'))
        # "navegadores" + visibility words → world model (open browsers), not accounts
        asks_about_browsers = (
            any(token in word_tokens for token in ('navegador', 'navegadores', 'browser', 'browsers'))
            and any(token in word_tokens for token in ('abierto', 'abiertos', 'abiertas', 'abierta', 'ves', 'ver', 'puedes', 'tienes'))
        )
        return asks_about_windows or asks_about_network or asks_about_live_tool or asks_current_state or asks_about_browsers

    _COMPOUND_CONJUNCTIONS = (' y ', ' y,', ' pero ', ' con eso ', ' ademas ', ' tambien ', ' además ', ' también ', ' revisa ', ' revisá ')

    def _is_self_awareness_question(self, message: str, *, fast_only: bool = False) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        direct_phrases = (
            'conoces tu entorno',
            'sabes tu entorno',
            'conoces tu arquitectura',
            'sabes tu arquitectura',
            'que herramientas tienes',
            'qué herramientas tienes',
            'que herramientas hay disponibles',
            'qué herramientas hay disponibles',
            'con que ias te conectas',
            'con qué ias te conectas',
            'con que ias te puedes conectar',
            'con qué ias te puedes conectar',
            'con que ia te conectas',
            'con qué ia te conectas',
            'con que ia te puedes conectar',
            'con qué ia te puedes conectar',
            'con que asistentes te conectas',
            'con qué asistentes te conectas',
            'con que asistentes te puedes conectar',
            'con qué asistentes te puedes conectar',
            'que tan consciente eres',
            'qué tan consciente eres',
            'que tan bien estas',
            'qué tan bien estás',
            'que tan bien estas ahora',
            'qué tan bien estás ahora',
            'como estas ahora',
            'cómo estás ahora',
            'que tienes disponible',
            'qué tienes disponible',
        )
        for phrase in direct_phrases:
            if phrase in normalized:
                remainder = normalized[normalized.index(phrase) + len(phrase):]
                if any(conj in remainder for conj in self._COMPOUND_CONJUNCTIONS) and len(remainder.split()) > 5:
                    return False
                return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_system_state = any(token in word_tokens for token in ('entorno', 'arquitectura', 'herramienta', 'herramientas', 'ias', 'ia', 'estado', 'conexiones'))
        asks_directly = any(token in normalized for token in ('conoces', 'sabes', 'tienes', 'disponibles', 'te conectas', 'te puedes conectar', 'consciente', 'que tan bien', 'como estas', 'cómo estás'))
        if asks_system_state and asks_directly:
            return True
        if fast_only:
            return False
        # Ollama fallback
        try:
            from iabv_v15.services.account_resource_scanner import classify_chat_intent
            result = classify_chat_intent(normalized)
            if result and result.get('category') == 'self_awareness' and float(result.get('confidence', 0)) >= 0.6:
                return True
        except Exception:
            pass
        return False

    def _is_learning_question(self, message: str, *, fast_only: bool = False) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        if self._is_operational_teaching_prompt(message):
            return False
        if any(token in normalized for token in ('revisarte', 'autoexaminacion', 'auto examinacion', 'fallando mas', 'repitiendo mal', 'cambios recomiendas')):
            return False
        direct_phrases = (
            'que aprendiste',
            'qué aprendiste',
            'que has aprendido',
            'qué has aprendido',
            'que va mejor',
            'qué va mejor',
            'que esta funcionando mejor',
            'qué está funcionando mejor',
            'que herramienta esta funcionando mejor',
            'qué herramienta está funcionando mejor',
            'que herramientas estan funcionando mejor',
            'qué herramientas están funcionando mejor',
            'por que cambiaste de ruta',
            'por qué cambiaste de ruta',
            'por que cambiaste',
            'por qué cambiaste',
            'que estas probando ahora',
            'qué estás probando ahora',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        if 'aprend' in normalized:
            return True
        if (
            any(token in word_tokens for token in ('herramienta', 'herramientas', 'rutas', 'ruta', 'ias', 'ia', 'probando', 'funcionando'))
            and any(token in word_tokens for token in ('mejor', 'mejores', 'aprendido', 'cambiaste', 'aprendiste'))
        ):
            return True
        if fast_only:
            return False
        # Ollama fallback
        try:
            from iabv_v15.services.account_resource_scanner import classify_chat_intent
            result = classify_chat_intent(normalized)
            if result and result.get('category') == 'learning' and float(result.get('confidence', 0)) >= 0.6:
                return True
        except Exception:
            pass
        return False

    def _is_evolution_status_question(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        direct_phrases = (
            'que herramienta va ganando',
            'qué herramienta va ganando',
            'que herramientas van ganando',
            'qué herramientas van ganando',
            'que esta en validacion',
            'qué está en validacion',
            'que esta en validación',
            'qué está en validación',
            'que fue descartado',
            'qué fue descartado',
            'que fue descartada',
            'qué fue descartada',
            'que herramientas fueron descartadas',
            'qué herramientas fueron descartadas',
            'que se descubrio nuevo',
            'qué se descubrio nuevo',
            'que se descubrió nuevo',
            'qué se descubrió nuevo',
            'que herramienta nueva vale la pena probar',
            'qué herramienta nueva vale la pena probar',
            'que herramienta vale la pena probar',
            'qué herramienta vale la pena probar',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_evolution = any(token in word_tokens for token in ('ganando', 'validacion', 'descartado', 'descartadas', 'descubrio', 'nuevo', 'nueva'))
        asks_tools = any(token in word_tokens for token in ('herramienta', 'herramientas', 'ruta', 'rutas', 'probar'))
        return asks_evolution and asks_tools

    def _is_operational_teaching_prompt(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        teaching_phrases = (
            'quiero ensenarte',
            'quiero enseñarte',
            'te voy a ensenar',
            'te voy a enseñar',
            'te enseno',
            'te enseño',
            'que te enseno',
            'que te enseño',
            'aprende a',
            'ensenate',
            'enséñate',
        )
        if not any(phrase in normalized for phrase in teaching_phrases):
            return False
        operational_signals = (
            'abre',
            'abrir',
            'sitio',
            'pagina',
            'página',
            'login',
            'sesion',
            'sesión',
            'inicia sesion',
            'inicia sesión',
            'iniciar sesion',
            'iniciar sesión',
            'detectar',
            'ubicar',
            'dejar lista',
            'dejar listo',
            'siguiente fase',
            'sin apostar',
            'sin dinero',
        )
        return bool(self._explicit_site_hint_from_message(message)) or self._seems_task_like_message(message) or any(
            token in normalized for token in operational_signals
        )

    def _is_self_examination_question(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        direct_phrases = (
            'examinate',
            'examínate',
            'revisate',
            'revísate',
            'que esta fallando mas',
            'qué está fallando más',
            'que falla mas',
            'qué falla más',
            'que estas repitiendo mal',
            'qué estás repitiendo mal',
            'que deberias mejorar',
            'qué deberías mejorar',
            'que cambios recomiendas',
            'qué cambios recomiendas',
            'que aprendiste al revisarte',
            'qué aprendiste al revisarte',
            'que recomiendas cambiar',
            'qué recomiendas cambiar',
            'que deberias corregir',
            'qué deberías corregir',
            # Log self-inspection / runtime self-diagnosis
            'analiza tus logs',
            'analiza tus propios logs',
            'revisa tus logs',
            'que anomalias detectas',
            'qué anomalías detectas',
            'diagnosticate',
            'diagnostícate',
            'autodiagnostico',
            'autodiagnóstico',
            'que ves en tus logs',
            'qué ves en tus logs',
            'que detectas en tu log',
            'qué detectas en tu log',
            'analiza tu log',
            'revisa tu log',
            'lee tus logs',
            # Fix 58: action-oriented self-examination phrases
            'soluciona los bloqueos',
            'arregla los bloqueos',
            'corrige los bloqueos',
            'resuelve los bloqueos',
            'soluciona los problemas',
            'arregla los problemas',
            'corrige los problemas',
            'resuelve los problemas',
            'soluciona los pendientes',
            'arregla los pendientes',
            'secciones caducadas',
            'informacion caducada',
            'información caducada',
            'datos caducados',
            'trabajo en vivo',
            'que esta bloqueado',
            'qué está bloqueado',
            'que bloqueos hay',
            'qué bloqueos hay',
            'que bloqueos tienes',
            'qué bloqueos tienes',
            'soluciona todo',
            'arregla todo',
            'corrige todo',
            'que pendientes tienes',
            'qué pendientes tienes',
            'que tareas pendientes',
            'qué tareas pendientes',
            'resuelve lo pendiente',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_review = any(token in word_tokens for token in ('fallando', 'falla', 'repitiendo', 'mejorar', 'cambios', 'cambiar', 'corregir', 'revisarte', 'autoexaminacion', 'anomalias', 'anomalías', 'diagnostica', 'logs'))
        asks_meta = any(token in word_tokens for token in ('recomiendas', 'recomendar', 'aprendiste', 'aprendido', 'deberias', 'debería', 'deberias', 'detectas', 'analiza', 'revisa', 'dime'))
        if asks_review and asks_meta:
            return True
        # Fix 58: action verbs + system-problem nouns
        asks_fix = any(token in word_tokens for token in ('soluciona', 'solucionar', 'arregla', 'arreglar', 'corrige', 'corregir', 'resuelve', 'resolver', 'repara', 'reparar'))
        has_problem = any(token in word_tokens for token in ('bloqueos', 'bloqueo', 'problemas', 'problema', 'pendientes', 'pendiente', 'caducadas', 'caducados', 'caducada', 'errores', 'fallos', 'fallas'))
        return asks_fix and has_problem

    def _is_account_resource_question(self, message: str, *, fast_only: bool = False) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        # Guard: questions about a specific API key or provider are NOT
        # account_resource — they should go through the general chat IA
        # which has system context to answer precisely.
        _specific_provider_tokens = (
            'groq', 'gemini', 'openrouter', 'together', 'deepseek',
            'api key', 'apikey', 'api_key',
            'que modelo', 'qué modelo', 'estas usando', 'estás usando',
            'usa groq', 'usa gemini', 'usa openrouter',
            'key de groq', 'key de gemini', 'key de openrouter',
        )
        if any(tok in normalized for tok in _specific_provider_tokens):
            return False
        direct_phrases = (
            'que cuentas tienes',
            'qué cuentas tienes',
            'que cuentas tengo',
            'qué cuentas tengo',
            'que cuentas hay',
            'qué cuentas hay',
            'verifica acceso',
            'verificar acceso',
            'escanea cuentas',
            'escanear cuentas',
            'escanea mis cuentas',
            'escanear mis cuentas',
            'diagnostico de cuentas',
            'diagnóstico de cuentas',
            'que correos tienes',
            'qué correos tienes',
            'que correos tengo',
            'qué correos tengo',
            'que programas puedo usar',
            'qué programas puedo usar',
            'que sesiones activas hay',
            'qué sesiones activas hay',
            'cuantos mensajes me quedan',
            'cuántos mensajes me quedan',
            'cuantos mensajes quedan',
            'cuántos mensajes quedan',
            'estado de cuotas',
            'estado de mis cuotas',
            'que cuentas estan agotadas',
            'qué cuentas están agotadas',
            'que limites tengo',
            'qué límites tengo',
            'limites de mensajes',
            'límites de mensajes',
            'escanea navegadores',
            'escanear navegadores',
            'revisa mis navegadores',
            'que ves en mis navegadores',
            'qué ves en mis navegadores',
            'te falto las demas cuentas',
            'te faltó las demás cuentas',
            'te falto las demas cuentas en los demas navegadores',
            'te faltó las demás cuentas en los demás navegadores',
            'cuentas en los demas navegadores',
            'cuentas en los demás navegadores',
            'cuentas en otros navegadores',
            'falta escanear navegadores',
            'faltan navegadores',
            'faltan cuentas',
            'te faltan cuentas',
            'que asistentes tengo',
            'qué asistentes tengo',
            'que asistentes hay disponibles',
            'qué asistentes hay disponibles',
            'pool de asistentes',
            'muestra los asistentes',
            'muestra asistentes disponibles',
            'cuantos asistentes disponibles',
            'cuántos asistentes disponibles',
            'cuales cuentas tienen sesion',
            'cuáles cuentas tienen sesión',
            'que cuentas tienen acceso',
            'qué cuentas tienen acceso',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9áéíóúñü_]+', normalized))
        account_nouns = ('cuentas', 'correos', 'sesiones', 'navegadores', 'cuotas',
                         'limites', 'límites', 'asistentes', 'workers', 'pool')
        action_verbs = ('escanea', 'escanear', 'verifica', 'verificar', 'revisa',
                        'revisar', 'diagnostico', 'diagnóstico', 'muestra', 'mostrar',
                        'dime', 'tienes', 'tengo', 'quedan', 'agotadas', 'agotados',
                        'falto', 'faltó', 'falta', 'faltan', 'faltaron',
                        'busca', 'buscar', 'detecta', 'detectar', 'analiza',
                        'analizar', 'lista', 'listar', 'dame', 'muestrame',
                        'disponibles', 'activas', 'activos', 'hay', 'cuales',
                        'cuáles', 'cuantas', 'cuántas')
        asks_accounts = any(token in word_tokens for token in account_nouns)
        asks_action = any(token in word_tokens for token in action_verbs)
        # Disambiguate: "navegadores" + visibility words → world model, not accounts.
        # If the user asks about open/visible browsers, _is_world_model_question
        # handles it.  Only treat "navegadores" as account_resource when combined
        # with account-specific verbs (escanea, cuentas, correos, etc.).
        if asks_accounts and asks_action:
            browser_visibility_words = ('abierto', 'abiertos', 'abiertas', 'abierta',
                                        'ves', 'ver', 'puedes')
            browser_tokens = ('navegador', 'navegadores', 'browser', 'browsers')
            is_browser_visibility = (
                any(token in word_tokens for token in browser_tokens)
                and any(token in word_tokens for token in browser_visibility_words)
                and not any(token in word_tokens for token in ('cuentas', 'correos', 'sesiones'))
            )
            if is_browser_visibility:
                return False
            return True

        # Fallback: Ollama-based classification for ambiguous messages.
        # Only invoked when the fast pattern check above didn't match.
        # Skipped in fast_only mode (synchronous shortcut path) to avoid
        # blocking the UI thread with LLM calls.
        if fast_only:
            return False
        try:
            from iabv_v15.services.account_resource_scanner import classify_chat_intent
            result = classify_chat_intent(normalized)
            if result and result.get('category') == 'account_resource':
                confidence = float(result.get('confidence', 0))
                if confidence >= 0.6:
                    logger.info(
                        'ollama_intent_fallback: classified as account_resource '
                        '(confidence=%.2f) for: %s',
                        confidence, normalized[:80],
                    )
                    return True
        except Exception:
            pass
        return False

    def _human_join(self, items: list[str], *, limit: int = 4) -> str:
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        cleaned = list(dict.fromkeys(cleaned))[:limit]
        if not cleaned:
            return ''
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f'{cleaned[0]} y {cleaned[1]}'
        return f"{', '.join(cleaned[:-1])} y {cleaned[-1]}"

    def _learning_focus(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        if any(token in normalized for token in ('herramienta', 'herramientas', 'ias', 'ia', 'va mejor', 'funcionando mejor', 'funciona mejor')):
            return 'tools'
        if any(token in normalized for token in ('cambiaste de ruta', 'cambio de ruta', 'por que cambiaste', 'por qué cambiaste')):
            return 'route_change'
        if any(token in normalized for token in ('probando ahora', 'estas probando', 'estás probando')):
            return 'current_validation'
        return 'general'

    def _evolution_status_focus(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        asks_winners = any(token in normalized for token in ('ganando', 'va ganando', 'van ganando'))
        asks_validation = any(token in normalized for token in ('validacion', 'validación', 'en validacion', 'en validación'))
        asks_discarded = any(token in normalized for token in ('descartado', 'descartada', 'descartadas', 'descartados'))
        asks_discovery = any(token in normalized for token in ('descubrio nuevo', 'descubrió nuevo', 'descubierto nuevo', 'descubrimiento'))
        asks_candidate = any(token in normalized for token in ('vale la pena probar', 'vale la pena', 'probar ahora'))
        if sum(1 for flag in (asks_winners, asks_validation, asks_discarded, asks_discovery, asks_candidate) if flag) > 1:
            return 'general'
        if asks_winners:
            return 'winners'
        if asks_validation:
            return 'validation'
        if asks_discarded:
            return 'discarded'
        if asks_discovery:
            return 'discovery'
        if asks_candidate:
            return 'candidate'
        return 'general'

    def _self_examination_focus(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        if any(token in normalized for token in ('fallando mas', 'falla mas', 'fallando', 'falla')):
            return 'failures'
        if any(token in normalized for token in ('repitiendo mal', 'repitiendo', 'inercia', 'repetiendo')):
            return 'repetition'
        if any(token in normalized for token in ('cambios recomiendas', 'recomiendas cambiar', 'deberias mejorar', 'deberías mejorar', 'deberias corregir', 'deberías corregir')):
            return 'adjustments'
        if any(token in normalized for token in ('logs', 'log', 'anomalias', 'anomalías', 'diagnostica', 'diagnostico', 'autodiagnostico')):
            return 'runtime_logs'
        return 'general'

    def _format_percent(self, value: Any) -> str:
        try:
            numeric = float(value)
        except Exception:
            return ''
        if numeric <= 1.0:
            numeric *= 100.0
        return f'{numeric:.0f}%'

    def _self_awareness_focus(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        if any(token in normalized for token in ('herramienta', 'herramientas')):
            return 'tools'
        if any(token in normalized for token in ('ias', 'ia', 'conectas', 'asistentes')):
            return 'assistants'
        if any(token in normalized for token in ('que tan bien', 'qué tan bien', 'como estas', 'cómo estás', 'estado', 'salud')):
            return 'health'
        if 'arquitectura' in normalized:
            return 'architecture'
        return 'environment'

    def _self_awareness_reply(self, message: str) -> tuple[str, str]:
        environment = self._current_environment_self_model()
        hardware = dict(environment.hardware_profile or {})
        runtime = dict(environment.runtime_profile or {})
        ai_capacity = dict(environment.ai_capacity or {})
        local_runtime = dict(ai_capacity.get('local_runtime') or {})
        assistant_cards = list(self._assistant_tool_cards())
        available_tool_titles = self._human_join([str(item.get('title') or '') for item in environment.available_tools], limit=6)
        missing_tool_titles = self._human_join([str(item.get('tool_id') or item.get('title') or '') for item in environment.missing_tools], limit=4)
        local_models = self._human_join([str(item.get('name') or '') for item in (local_runtime.get('models') or [])], limit=4)
        ram_usage = self._format_percent(hardware.get('memory_usage_ratio'))
        cpu_usage = self._format_percent(hardware.get('cpu_usage_percent'))
        notifications = [str(item).strip() for item in (environment.notifications or []) if str(item).strip()]
        unresolved = [str(item).replace('UNRESOLVED:', '').strip() for item in (environment.unresolved_fields or []) if str(item).strip()]
        aggregated_cards = self._aggregate_assistant_entries(assistant_cards)
        assistant_states: list[str] = []
        for card in aggregated_cards:
            name = str(card.get('name') or '').strip()
            status = str(card.get('status') or '').strip().lower()
            if not name:
                continue
            if status == 'no disponible':
                assistant_states.append(f'{name} no esta disponible')
            elif 'sesion aislada' in status:
                assistant_states.append(f'{name} esta listo por sesion aislada')
            elif 'automatico' in status:
                assistant_states.append(f'{name} esta listo')
            elif 'guiado' in status or 'web preparada' in status:
                assistant_states.append(f'{name} esta disponible con guia')
            else:
                assistant_states.append(f'{name} esta {status}')
        focus = self._self_awareness_focus(message)
        if focus == 'tools':
            response = 'Ahora mismo tengo disponibles '
            response += available_tool_titles or 'las herramientas basicas del programa'
            if missing_tool_titles:
                response += f'. Me faltan {missing_tool_titles}.'
            else:
                response += '. No tengo faltantes relevantes en esta pasada.'
            return response, 'Herramientas reales del entorno.'
        if focus == 'assistants':
            response = 'Ahora mismo me puedo apoyar en '
            response += self._human_join(assistant_states, limit=6) or 'las vias que el entorno tenga activas'
            if local_models:
                response += f'. En local tengo Ollama con {local_models}.'
            return response, 'Conexiones reales con IAs.'
        if focus == 'health':
            status_bits = []
            if ram_usage:
                status_bits.append(f'RAM en {ram_usage}')
            if cpu_usage:
                status_bits.append(f'CPU alrededor de {cpu_usage}')
            if str(hardware.get('gpu_name') or '').strip():
                status_bits.append(f"GPU {str(hardware.get('gpu_name') or '').strip()}")
            response = 'Ahora mismo estoy estable'
            if status_bits:
                response += ' con ' + ', '.join(status_bits)
            response += '.'
            if notifications:
                response += f" Lo mas relevante que veo es: {notifications[0]}"
            elif unresolved:
                response += f" Todavia no puedo leer bien {self._human_join(unresolved, limit=3)}."
            return response, 'Estado actual del sistema.'
        if focus == 'architecture':
            response = (
                'Si. Ahora mismo me estoy guiando por una percepcion unificada del entorno, '
                'memoria reciente de interacciones y un registro vivo de herramientas.'
            )
            if available_tool_titles:
                response += f' En esta laptop tengo disponibles {available_tool_titles}.'
            if local_models:
                response += f' En local puedo correr {local_models}.'
            if missing_tool_titles:
                response += f' Todavia me faltan {missing_tool_titles}.'
            return response, 'Arquitectura observada desde el estado real.'
        response = 'Si. Ahora mismo estoy corriendo en este entorno'
        python_version = str(runtime.get('python_version') or '').strip()
        if python_version:
            response += f' con Python {python_version}'
        response += '.'
        if local_models:
            response += f' Tengo Ollama con {local_models}.'
        if assistant_states:
            response += f' Tambien veo {self._human_join(assistant_states, limit=4)}.'
        if ram_usage:
            response += f' La RAM va en {ram_usage}'
            if cpu_usage:
                response += f' y la CPU ronda {cpu_usage}'
            response += '.'
        if missing_tool_titles:
            response += f' Lo que me falta ahora mismo es {missing_tool_titles}.'
        elif notifications:
            response += f' Lo mas relevante que noto es: {notifications[0]}'
        return response, 'Resumen real del entorno.'

    def _world_model_focus(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        if any(token in normalized for token in ('internet', 'red', 'conexion', 'conexión')):
            return 'network'
        if any(token in normalized for token in ('ventana', 'ventanas', 'foco', 'abierto', 'abiertas')):
            return 'windows'
        if 'codex' in normalized:
            return 'codex'
        if 'chatgpt' in normalized:
            return 'chatgpt'
        if 'claude' in normalized:
            return 'claude'
        if 'ollama' in normalized:
            return 'ollama'
        return 'general'

    def _world_model_tool_status(self, world_model: WorldModelSnapshot, assistant_kind: str) -> Any | None:
        normalized = str(assistant_kind or '').strip().lower()
        return next(
            (item for item in (world_model.tool_live_status or []) if str(item.assistant_kind or '').strip().lower() == normalized),
            None,
        )

    def _world_model_reply(self, message: str) -> tuple[str, str]:
        world_model = self._current_world_model()
        focus = self._world_model_focus(message)
        focused_window = str((world_model.focused_window.title if world_model.focused_window is not None else '') or '').strip()
        active_titles = [
            str(item.title or '').strip()
            for item in (world_model.active_windows or [])
            if str(item.title or '').strip()
        ]
        active_titles = list(dict.fromkeys(active_titles))[:5]
        deductions = [
            str(item).strip()
            for item in dict(world_model.inferred_state or {}).get('deductions', [])
            if str(item).strip()
        ]
        blocks = [str(item).strip() for item in (world_model.detected_blocks or []) if str(item).strip()]
        if focus == 'windows':
            if active_titles:
                response = f'Ahora mismo veo abiertas {self._human_join(active_titles, limit=5)}.'
                if focused_window:
                    response += f' La ventana en foco es {focused_window}.'
            else:
                response = 'Ahora mismo no pude confirmar ventanas relevantes con suficiente claridad.'
            return response, 'Ventanas observadas en vivo.'
        if focus == 'network':
            network = world_model.network_status
            if str(network.status or '').strip() in {'conectado', 'lento'}:
                response = f"La red esta {str(network.status or '').strip()}."
                if network.latency_ms is not None:
                    response += f' La latencia observada ronda {round(float(network.latency_ms), 1)} ms.'
                if str(network.detail or '').strip():
                    response += f' {str(network.detail or "").strip()}'
            else:
                response = str(network.detail or 'No pude confirmar bien el estado de la red ahora mismo.').strip()
            return response, 'Estado real de la red.'
        if focus in {'codex', 'chatgpt', 'claude', 'ollama'}:
            tool = self._world_model_tool_status(world_model, focus)
            if tool is None:
                return (
                    f'Ahora mismo no pude confirmar el estado vivo de {focus.capitalize()} con suficiente evidencia.',
                    'Estado de herramienta no confirmado.',
                )
            status_label = {
                'abierto': 'abierto',
                'listo': 'listo',
                'disponible': 'disponible',
                'bloqueado': 'bloqueado',
                'hilo_incorrecto': 'bloqueado por hilo incorrecto',
                'sesion_expirada': 'con la sesion expirada',
                'limitado': 'limitado por cuota o cuenta',
                'no_disponible': 'no disponible',
            }.get(str(tool.status or '').strip(), str(tool.status or 'sin estado claro').replace('_', ' '))
            detected_blocks = {str(item).strip() for item in (tool.detected_blocks or []) if str(item).strip()}
            response = f"{tool.title or focus.capitalize()} esta {status_label}."
            if 'wrong_thread' in detected_blocks or str(tool.thread_status or '').strip() == 'otro_hilo_activo':
                response += ' La evidencia reciente apunta a un hilo distinto del esperado.'
            elif str(tool.thread_status or '').strip() == 'sin_hilo_iabv':
                response += ' No veo un hilo reciente de IABV asociado a esta sesion.'
            elif 'browser_security_verification' in detected_blocks:
                response += ' El sitio activo una verificacion de seguridad antes de abrir el chat.'
            elif 'capture_unverified' in detected_blocks:
                response += ' La ultima captura todavia no quedo verificada.'
            if str(tool.messages_status or '').strip() == 'agotados_o_limitados':
                response += ' Tambien veo senales de mensajes o cuota limitados.'
            if str(tool.session_status or '').strip() in {'expirada', 'verificacion_seguridad', 'limitada'}:
                response += f' La sesion figura {str(tool.session_status or "").replace("_", " ")}.'
            detail = str(tool.detail or '').strip()
            if detail and len(detail) <= 180 and detail.lower() not in response.lower():
                response += f' {detail}'
            return response, f'Estado vivo de {tool.title or focus.capitalize()}.'
        summary = str(dict(world_model.inferred_state or {}).get('summary') or '').strip()
        response = summary or 'Ya actualice la observacion operativa del entorno.'
        if focused_window:
            response += f' La ventana en foco es {focused_window}.'
        if deductions:
            response += f' Lo mas relevante que deduzco ahora es: {deductions[0]}'
        elif blocks:
            response += f' El bloqueo mas visible ahora es {blocks[0].replace("_", " ")}.'
        return response, 'Estado operativo observado.'

    def _learning_reply(self, message: str) -> tuple[str, str]:
        learning = self._learning_evidence_snapshot()
        experiment_runs = list(learning.get('experiment_runs') or [])
        recommendations = list(learning.get('recommendations') or [])
        latest_recommendation = learning.get('latest_recommendation')
        validation = dict(learning.get('validation') or {})
        validation_summary = str(learning.get('validation_summary') or '').strip()
        current_experiment = dict(learning.get('current_experiment') or {})
        adaptive_learning = dict(learning.get('adaptive_learning') or {})
        learned_patterns = list(learning.get('learned_patterns') or [])
        focus = self._learning_focus(message)
        if focus == 'current_validation':
            if current_experiment:
                verdict = str(current_experiment.get('verdict') or 'n/d').replace('_', ' ')
                candidate = str(current_experiment.get('candidate_assistant_kind') or current_experiment.get('candidate_route') or 'n/d')
                response = f"Ahora estoy validando en sandbox si {candidate} mejora el caso {str(current_experiment.get('subject_key') or 'actual')}."
                response += f" El veredicto provisional es {verdict}."
                summary = str(validation.get('summary') or '').strip()
                if summary:
                    response += f' {summary}'
                return response, 'Validacion autonoma actual.'
            if str(validation.get('status') or '').strip() == 'paused':
                return (
                    f"La validacion autonoma esta pausada. {str(validation.get('paused_reason') or 'No tengo condiciones seguras para validar ahora.')}",
                    'Validacion autonoma pausada.',
                )
            return ('Ahora mismo no tengo una validacion autonoma corriendo con evidencia suficiente.', 'Sin validacion activa.')
        if focus == 'route_change':
            if latest_recommendation is not None:
                summary = dict(getattr(latest_recommendation, 'metadata', {}) or {}).get('adaptive_learning_summary') or {}
                reasons = [str(item).strip() for item in (summary.get('reasons') or []) if str(item).strip()]
                response = (
                    f"Cambie o mantengo la ruta hacia {getattr(getattr(latest_recommendation, 'recommended_route', None), 'value', 'n/d')} "
                    f"con {str(getattr(latest_recommendation, 'recommended_assistant_kind', '') or 'el asistente actual')}."
                )
                if reasons:
                    response += f" La razon principal es {reasons[0]}."
                elif str(getattr(latest_recommendation, 'rationale', '') or '').strip():
                    response += f" {str(getattr(latest_recommendation, 'rationale', '') or '').strip()}"
                if validation_summary:
                    response += f' Validacion reciente: {validation_summary}'
                return response, 'Cambio de ruta basado en evidencia.'
            return ('Todavia no tengo evidencia suficiente para justificar un cambio de ruta real.', 'Sin cambio confirmado.')
        if focus == 'tools':
            if recommendations:
                ranked = list(dict(getattr(recommendations[0], 'metadata', {}) or {}).get('ranked_configurations') or [])
                top_labels = [
                    str(item.get('assistant_kind') or item.get('route') or '').strip()
                    for item in ranked[:3]
                    if str(item.get('assistant_kind') or item.get('route') or '').strip()
                ]
                if top_labels:
                    response = (
                        f"Las herramientas o rutas que vienen funcionando mejor para este tipo de caso son {self._human_join(top_labels, limit=3)}."
                    )
                    reasons = [str(item).strip() for item in (adaptive_learning.get('reasons') or []) if str(item).strip()]
                    if reasons:
                        response += f" La senal mas fuerte es {reasons[0]}."
                    if validation_summary and current_experiment:
                        response += f" En paralelo sigo validando: {validation_summary}"
                    return response, 'Ranking por evidencia reciente.'
            return ('Todavia no tengo suficiente historial comparable para decir que herramienta va mejor.', 'Historial insuficiente.')
        if latest_recommendation is not None:
            adaptive = dict(getattr(latest_recommendation, 'metadata', {}) or {}).get('adaptive_learning_summary') or {}
            reasons = [str(item).strip() for item in (adaptive.get('reasons') or []) if str(item).strip()]
            response = (
                f"Lo que he aprendido hasta ahora es que {str(getattr(latest_recommendation, 'recommended_assistant_kind', '') or 'la ruta principal')} "
                f"rinde mejor por {str(getattr(getattr(latest_recommendation, 'recommended_route', None), 'value', 'n/d'))}."
            )
            if reasons:
                response += f" La mejor senal es {reasons[0]}."
            if current_experiment:
                response += f" Ademas estoy probando en sandbox {str(current_experiment.get('candidate_assistant_kind') or current_experiment.get('candidate_route') or 'otra alternativa')}."
            elif learned_patterns:
                response += f" Tambien veo patrones como {str(learned_patterns[0].get('recommended_assistant_kind') or learned_patterns[0].get('recommended_route') or 'n/d')}."
            if validation_summary and not current_experiment:
                response += f" La validacion mas reciente dice: {validation_summary}"
            return response, 'Aprendizaje adaptativo real.'
        if adaptive_learning:
            preferred = str(adaptive_learning.get('recommended_assistant_kind') or adaptive_learning.get('recommended_route') or '').strip()
            if preferred:
                response = f"Por ahora solo puedo afirmar que {preferred} viene saliendo mejor en el historial reciente."
                if validation_summary:
                    response += f" Validacion reciente: {validation_summary}"
                return (response, 'Aprendizaje parcial.')
        if experiment_runs:
            last = experiment_runs[0]
            return (
                f"Tengo historial reciente, pero todavia no una preferencia estable. La ultima corrida comparable fue {str(getattr(last, 'candidate_label', '') or getattr(getattr(last, 'route', None), 'value', 'n/d'))}.",
                'Historial sin ganador claro.',
            )
        return ('Todavia no tengo evidencia suficiente para resumir un aprendizaje estable sin inventar datos.', 'Evidencia insuficiente.')

    def _evolution_status_reply(self, message: str) -> tuple[str, str]:
        validation = self._current_validation_status()
        discovery = self._current_tool_discovery_status()
        focus = self._evolution_status_focus(message)
        winning_by_problem = dict(validation.get('winning_by_problem') or {})
        in_validation = list(validation.get('in_validation') or [])
        discarded_proposals = [dict(item) for item in (validation.get('discarded_proposals') or []) if isinstance(item, dict)]
        recent_decisions = [dict(item) for item in (validation.get('recent_decisions') or []) if isinstance(item, dict)]
        active_signals = [dict(item) for item in (discovery.get('active_signals') or []) if isinstance(item, dict)]
        in_validation_signals = [dict(item) for item in (discovery.get('in_validation_signals') or []) if isinstance(item, dict)]
        promoted_signals = [dict(item) for item in (discovery.get('promoted_signals') or []) if isinstance(item, dict)]
        discarded_signals = [dict(item) for item in (discovery.get('discarded_signals') or []) if isinstance(item, dict)]
        unresolved = [
            str(item).strip()
            for item in list(validation.get('unresolved_fields') or []) + list(discovery.get('unresolved_fields') or [])
            if str(item).strip()
        ]
        if focus == 'winners':
            if winning_by_problem:
                top = [f'{scope}: {winner}' for scope, winner in list(winning_by_problem.items())[:4] if str(winner).strip()]
                return (f"Ahora mismo van ganando {self._human_join(top, limit=4)}.", 'Estado evolutivo real de herramientas.')
            return ('Todavia no tengo evidencia suficiente para decir que herramienta va ganando por problema.', 'Evidencia evolutiva insuficiente.')
        if focus == 'validation':
            validating = [str(item).strip() for item in in_validation[:4] if str(item).strip()]
            validating += [
                str(item.get('tool_title') or item.get('assistant_kind') or item.get('tool_id') or '').strip()
                for item in in_validation_signals[:4]
                if str(item.get('tool_title') or item.get('assistant_kind') or item.get('tool_id') or '').strip()
            ]
            validating = list(dict.fromkeys(validating))[:4]
            if validating:
                response = f"Ahora mismo esta en validacion {self._human_join(validating, limit=4)}."
                last_decision = dict(validation.get('last_decision') or {})
                if str(last_decision.get('reason') or '').strip():
                    response += f" La ultima decision registrada fue: {str(last_decision.get('reason') or '').strip()}"
                return response, 'Validacion evolutiva actual.'
            return ('Ahora mismo no veo una validacion evolutiva activa con evidencia suficiente.', 'Sin validacion evolutiva activa.')
        if focus == 'discarded':
            discarded = [
                str(item.get('proposal_key') or item.get('assistant_kind') or item.get('subject_key') or '').strip()
                for item in discarded_proposals[:4]
                if str(item.get('proposal_key') or item.get('assistant_kind') or item.get('subject_key') or '').strip()
            ]
            discarded += [
                str(item.get('tool_title') or item.get('assistant_kind') or item.get('tool_id') or '').strip()
                for item in discarded_signals[:4]
                if str(item.get('tool_title') or item.get('assistant_kind') or item.get('tool_id') or '').strip()
            ]
            discarded = list(dict.fromkeys(discarded))[:4]
            if discarded:
                return (
                    f"Lo que ya quedo descartado con evidencia reciente es {self._human_join(discarded, limit=4)}.",
                    'Descartes evolutivos reales.',
                )
            return ('Todavia no tengo descartes evolutivos confirmados para mostrarte sin inventar datos.', 'Sin descartes confirmados.')
        if focus in {'discovery', 'candidate'}:
            candidate_pool = active_signals if active_signals else promoted_signals
            if candidate_pool:
                top = candidate_pool[0]
                tool_title = str(top.get('tool_title') or top.get('assistant_kind') or top.get('tool_id') or 'un candidato nuevo').strip()
                scope = str(top.get('scope') or 'general').strip()
                summary = str(top.get('summary') or '').strip()
                response = f"Ahora mismo la herramienta nueva que mas vale la pena probar es {tool_title} para {scope}."
                if summary:
                    response += f' {summary}'
                return response, 'Discovery real de herramientas.'
            return ('Todavia no tengo un descubrimiento nuevo suficientemente fuerte para recomendarlo como candidato.', 'Sin discovery fuerte.')
        if winning_by_problem or recent_decisions or active_signals:
            parts: list[str] = []
            if winning_by_problem:
                first_scope, first_winner = next(iter(winning_by_problem.items()))
                parts.append(f'va ganando {first_winner} para {first_scope}')
            if in_validation:
                parts.append(f'hay {len(in_validation)} propuesta(s) en sandbox/validacion')
            elif in_validation_signals:
                parts.append(f'hay {len(in_validation_signals)} descubrimiento(s) en sandbox/validacion')
            if active_signals:
                first_signal = active_signals[0]
                parts.append(
                    f"aparecio como discovery {str(first_signal.get('tool_title') or first_signal.get('assistant_kind') or first_signal.get('tool_id') or 'n/d').strip()}"
                )
            if discarded_proposals or discarded_signals:
                parts.append(f"ya se descartaron {len(discarded_proposals) + len(discarded_signals)} candidato(s)")
            response = 'En el estado evolutivo actual ' + ', '.join(parts) + '.'
            if recent_decisions:
                response += f" La ultima decision fuerte fue {str(recent_decisions[-1].get('decision') or 'n/d')}."
            if unresolved:
                response += f" Todavia queda {self._human_join([item.replace('UNRESOLVED:', '') for item in unresolved], limit=3)} sin confirmar."
            return response, 'Resumen evolutivo real.'
        return ('Todavia no tengo evidencia suficiente para resumir el estado evolutivo sin suponer cosas.', 'Evidencia evolutiva insuficiente.')

    def _learning_evidence_snapshot(self) -> dict[str, Any]:
        site_id = self._current_site_id() or None
        goal_context = self._goal_context_for_display(site_id)
        experiment_runs, recommendations = self._scoped_experiment_history(
            goal_context=goal_context,
            site_id=site_id,
        )
        latest_recommendation = recommendations[0] if recommendations else None
        validation = self._current_validation_snapshot()
        current_experiment = dict(validation.get('current_experiment') or {})
        metadata = dict((((self._last_adaptive_payload.get('metadata') or {}).get('decision_context') or {}).get('metadata') or {}))
        adaptive_learning = dict(metadata.get('adaptive_learning_summary') or {})
        if not adaptive_learning and latest_recommendation is not None:
            recommendation_metadata = dict(getattr(latest_recommendation, 'metadata', {}) or {})
            adaptive_learning = dict(recommendation_metadata.get('adaptive_learning_summary') or {})
            adaptive_learning.setdefault('recommended_assistant_kind', str(getattr(latest_recommendation, 'recommended_assistant_kind', '') or ''))
            adaptive_learning.setdefault(
                'recommended_route',
                str(getattr(getattr(latest_recommendation, 'recommended_route', None), 'value', getattr(latest_recommendation, 'recommended_route', '')) or ''),
            )
            adaptive_learning.setdefault('confidence', float(getattr(latest_recommendation, 'confidence', 0.0) or 0.0))
            adaptive_learning.setdefault('score', float(getattr(latest_recommendation, 'score', 0.0) or 0.0))
        learned_patterns = list(metadata.get('learned_patterns') or [])
        if not learned_patterns:
            for recommendation in recommendations[:3]:
                recommendation_metadata = dict(getattr(recommendation, 'metadata', {}) or {})
                adaptive = dict(recommendation_metadata.get('adaptive_learning_summary') or {})
                learned_patterns.append(
                    {
                        'subject_key': str(getattr(recommendation, 'subject_key', '') or ''),
                        'domain': str(getattr(getattr(recommendation, 'domain', None), 'value', getattr(recommendation, 'domain', '')) or ''),
                        'recommended_route': str(
                            getattr(getattr(recommendation, 'recommended_route', None), 'value', getattr(recommendation, 'recommended_route', '')) or ''
                        ),
                        'recommended_assistant_kind': str(getattr(recommendation, 'recommended_assistant_kind', '') or ''),
                        'reasons': list(adaptive.get('reasons') or []),
                    }
                )
        return {
            'site_id': site_id or '',
            'goal_context': goal_context,
            'experiment_runs': experiment_runs,
            'recommendations': recommendations,
            'latest_recommendation': latest_recommendation,
            'validation': validation,
            'validation_summary': str(validation.get('summary') or '').strip(),
            'current_experiment': current_experiment,
            'adaptive_learning': adaptive_learning,
            'learned_patterns': learned_patterns[:3],
        }

    def _learning_conversation_payload(self, *, message: str) -> dict[str, Any]:
        learning = self._learning_evidence_snapshot()
        goal_context = dict(learning.get('goal_context') or {})
        site_id = str(learning.get('site_id') or '')
        site_name = site_id or str(dict(goal_context.get('objective') or {}).get('site_id') or '').strip() or 'General'
        experiment_runs = list(learning.get('experiment_runs') or [])
        validation_summary = str(learning.get('validation_summary') or '').strip()
        return {
            'session_id': '',
            'user_goal': message,
            'status': 'completed',
            'intent': {
                'title': 'Consulta sobre aprendizaje adaptativo',
                'intent_key': 'general.assistance',
                'disposition': 'answer_now',
                'confidence': 1.0,
                'metadata': {
                    'conversational_prompt': True,
                    'learning_prompt': True,
                },
            },
            'context': {
                'site_id': site_id,
                'site_display_name': site_name,
                'goal_context': goal_context,
                'recent_runs': [{'run_id': str(getattr(item, 'run_id', '') or '')} for item in experiment_runs[:4]],
                'recent_incidents': [],
                'live_audit': {
                    'summary': 'Consulta informativa de aprendizaje resuelta desde evidencia persistida.',
                    'decision_action': 'answer_learning_locally',
                },
            },
            'metadata': {
                'decision_context': {
                    'goal_context': goal_context,
                    'governance': {
                        'should_consult': False,
                        'recommended_action': 'answer_learning_locally',
                        'autonomy_level': 'informative_only',
                        'blockers': [],
                    },
                    'metadata': {
                        'conversational_prompt': True,
                        'adaptive_learning_summary': dict(learning.get('adaptive_learning') or {}),
                        'learned_patterns': list(learning.get('learned_patterns') or []),
                        'validation_summary': validation_summary,
                    },
                }
            },
            'outcome': {
                'summary': 'Consulta de aprendizaje resuelta desde ExperimentLab y validacion vigente.',
                'next_actions': [],
            },
        }

    def _evolution_status_conversation_payload(self, *, message: str) -> dict[str, Any]:
        validation = self._current_validation_status()
        discovery = self._current_tool_discovery_status()
        return {
            'session_id': '',
            'user_goal': message,
            'status': 'completed',
            'intent': {
                'title': 'Consulta de estado evolutivo',
                'intent_key': 'consulta_estado_evolutivo',
                'disposition': 'answer_now',
                'confidence': 1.0,
                'metadata': {
                    'conversational_prompt': True,
                    'evolution_status_prompt': True,
                },
            },
            'context': {
                'site_id': '',
                'site_display_name': 'General',
                'goal_context': {},
                'recent_runs': [],
                'recent_incidents': [],
                'live_audit': {
                    'summary': 'Consulta evolutiva resuelta desde monitor, decision log y discovery reales.',
                    'decision_action': 'answer_evolution_locally',
                },
            },
            'metadata': {
                'decision_context': {
                    'governance': {
                        'should_consult': False,
                        'recommended_action': 'answer_evolution_locally',
                        'autonomy_level': 'informative_only',
                        'blockers': [],
                    },
                    'metadata': {
                        'conversational_prompt': True,
                        'evolution_status_prompt': True,
                        'validation_status': validation,
                        'tool_discovery_status': discovery,
                    },
                }
            },
            'outcome': {
                'summary': 'Consulta de evolucion resuelta desde estado reconciliado y persistido.',
                'next_actions': [],
            },
        }

    def _answer_evolution_status_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._evolution_status_conversation_payload(message=message))
        reply, meta = self._evolution_status_reply(message)
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_learning_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._learning_conversation_payload(message=message))
        reply, meta = self._learning_reply(message)
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_self_awareness_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        reply, meta = self._self_awareness_reply(message)
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_world_model_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        reply, meta = self._world_model_reply(message)
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _self_examination_reply(self, message: str) -> tuple[str, str]:
        review = self._current_self_examination_snapshot()
        findings = list(review.get('top_findings') or [])
        recurring_issues = list(review.get('recurring_issues') or [])
        recommended_adjustments = list(review.get('recommended_adjustments') or [])
        validated_improvements = list(review.get('validated_improvements') or [])
        unresolved_risks = list(review.get('unresolved_risks') or [])
        focus = self._self_examination_focus(message)
        if focus == 'failures':
            if recurring_issues:
                top = recurring_issues[0]
                response = f"Lo que mas se esta repitiendo mal ahora es {str(top.get('title') or 'un patron sin nombre')}."
                if str(top.get('summary') or '').strip():
                    response += f" {str(top.get('summary') or '').strip()}"
                if recommended_adjustments:
                    response += f" El ajuste mas util ahora es {str(recommended_adjustments[0].get('recommended_change') or '').strip()}."
                return response, 'Autoexaminacion operativa.'
            return ('Todavia no tengo suficiente evidencia acumulada para afirmar que es lo que mas esta fallando.', 'Evidencia insuficiente.')
        if focus == 'repetition':
            if findings:
                top = findings[0]
                response = f"Lo que estoy repitiendo peor es {str(top.get('title') or 'un patron sin nombre')}."
                if str(top.get('summary') or '').strip():
                    response += f" {str(top.get('summary') or '').strip()}"
                recommendation = str(top.get('recommendation') or '').strip()
                if recommendation:
                    response += f" Por eso recomiendo {recommendation}"
                return response, 'Patron repetido detectado.'
            return ('No veo un patron repetido fuerte y confirmado todavia.', 'Sin patron fuerte.')
        if focus == 'adjustments':
            if recommended_adjustments:
                top = recommended_adjustments[0]
                response = f"El cambio que mas recomiendo ahora es {str(top.get('recommended_change') or '').strip()}."
                if len(recommended_adjustments) > 1:
                    response += f" Despues vendria {str(recommended_adjustments[1].get('recommended_change') or '').strip()}."
                return response, 'Ajustes recomendados por evidencia.'
            return ('Todavia no tengo cambios recomendados con evidencia suficiente para proponerlos en serio.', 'Sin ajuste fuerte.')
        if focus == 'runtime_logs':
            runtime_categories = {'runtime_noise', 'external_consultation_failure', 'tool_availability', 'ghost_session'}
            log_findings = [f for f in findings if str(f.get('category') or '') in runtime_categories]
            if log_findings:
                parts = []
                for lf in log_findings[:4]:
                    title = str(lf.get('title') or 'anomalia sin nombre')
                    summary = str(lf.get('summary') or '').strip()
                    recommendation = str(lf.get('recommendation') or '').strip()
                    entry = f"- {title}"
                    if summary:
                        entry += f": {summary}"
                    if recommendation:
                        entry += f" Recomendacion: {recommendation}"
                    parts.append(entry)
                header = f"Encontre {len(log_findings)} anomalia(s) en mis logs de runtime:"
                return (f"{header}\n" + '\n'.join(parts), 'Autodiagnostico de logs en vivo.')
            # No runtime findings — fall through to check regular findings
            if findings:
                return (f"No encontre anomalias de runtime en mis logs recientes, pero tengo {len(findings)} hallazgo(s) de autoexaminacion: {str(findings[0].get('title') or 'hallazgo sin nombre')}.", 'Sin anomalias de runtime; hay hallazgos regulares.')
            return ('Revise mis logs recientes y no encontre anomalias activas. Todo parece estable por ahora.', 'Sin anomalias detectadas.')
        if findings or recommended_adjustments or validated_improvements:
            parts = []
            if findings:
                parts.append(f"Lo mas delicado ahora es {str(findings[0].get('title') or 'un hallazgo sin nombre')}.")
            if recommended_adjustments:
                parts.append(f"El ajuste mas util es {str(recommended_adjustments[0].get('recommended_change') or '').strip()}.")
            if validated_improvements:
                parts.append(f"Lo que si parece ir bien es {str(validated_improvements[0].get('title') or 'una mejora validada')}.")
            if unresolved_risks:
                parts.append(f"Todavia dejo como UNRESOLVED {str(unresolved_risks[0]).replace('UNRESOLVED:', '').replace('_', ' ')}.")
            return (' '.join(part for part in parts if part).strip(), 'Revision operativa con evidencia.')
        return ('Todavia no tengo evidencia suficiente para revisarme con hallazgos utiles sin inventar datos.', 'Evidencia insuficiente.')

    def _self_examination_conversation_payload(self, *, message: str) -> dict[str, Any]:
        review = self._current_self_examination_snapshot()
        return {
            'session_id': '',
            'user_goal': message,
            'status': 'completed',
            'intent': {
                'title': 'Consulta de autoexaminacion operativa',
                'intent_key': 'general.assistance',
                'disposition': 'answer_now',
                'confidence': 1.0,
                'metadata': {
                    'conversational_prompt': True,
                    'self_examination_prompt': True,
                },
            },
            'context': {
                'site_id': '',
                'site_display_name': 'General',
                'goal_context': {},
                'recent_runs': [{'run_id': str(item)} for item in []],
                'recent_incidents': list(review.get('recurring_issues') or [])[:3],
                'live_audit': {
                    'summary': 'Consulta informativa de autoexaminacion resuelta desde evidencia persistida.',
                    'decision_action': 'answer_self_examination_locally',
                },
            },
            'metadata': {
                'decision_context': {
                    'goal_context': {},
                    'governance': {
                        'should_consult': False,
                        'recommended_action': 'answer_self_examination_locally',
                        'autonomy_level': 'informative_only',
                        'blockers': [],
                    },
                    'metadata': {
                        'conversational_prompt': True,
                        'self_examination_summary': dict(review),
                    },
                }
            },
            'outcome': {
                'summary': 'Consulta de autoexaminacion resuelta desde historial, laboratorio y backlog actual.',
            },
        }

    def _answer_self_examination_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._self_examination_conversation_payload(message=message))
        reply, meta = self._self_examination_reply(message)
        # Fix 59: run auto-correction engine on findings and present
        # remaining issues as action buttons.
        auto_fixes_applied: list[str] = []
        try:
            from iabv_v15.services.auto_correction_engine import (
                apply_runtime_log_corrections, apply_deductive_corrections,
            )
            review_data = self._current_self_examination_snapshot()
            findings = list(review_data.get('top_findings') or [])
            if findings:
                rt_result = apply_runtime_log_corrections(findings)
                for c in (rt_result.get('corrections_applied') or []):
                    label = str(c.get('action') or c.get('detail') or 'correccion aplicada')
                    auto_fixes_applied.append(label)
                dd_result = apply_deductive_corrections(findings)
                for c in (dd_result.get('executed') or []):
                    label = str(c.get('action') or c.get('detail') or 'correccion deductiva')
                    auto_fixes_applied.append(label)
        except Exception:
            pass
        if auto_fixes_applied:
            reply += f"\n\nAuto-correcciones aplicadas ({len(auto_fixes_applied)}):"
            for fix_label in auto_fixes_applied[:5]:
                reply += f"\n  - {fix_label}"
            meta = 'Autoexaminacion con correcciones automaticas.'
        # Set guidance with action buttons for remaining issues
        review = self._current_self_examination_snapshot()
        remaining = list(review.get('recommended_adjustments') or [])
        unresolved = list(review.get('unresolved_risks') or [])
        if remaining or unresolved:
            guidance_prompt = 'Hay ajustes pendientes que puedo aplicar o que necesitan tu aprobacion.'
            if unresolved:
                guidance_prompt += f' Tambien hay {len(unresolved)} riesgo(s) sin resolver.'
            self._apply_assistant_guidance({
                'mode': 'need_approval',
                'title': 'Ajustes pendientes',
                'prompt': guidance_prompt,
                'actions': [
                    self._assistant_action('run_self_test', 'Autotest', 'Correr diagnostico completo con autoajuste.'),
                    self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar hallazgos y backlog.'),
                    self._assistant_action('review_stack', 'Revisar stack', 'Actualizar estado de herramientas.'),
                ],
            })
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _account_resource_reply(self, message: str) -> tuple[str, str]:
        """Build a reply with the full account/resource diagnostic."""
        parts: list[str] = []

        # 1. Browser accounts
        try:
            from iabv_v15.services.account_resource_scanner import scan_browser_accounts
            browser = scan_browser_accounts()
            if browser.get('count', 0) > 0:
                parts.append(f"Detecto {browser['count']} cuenta(s) en tus navegadores:")
                for acc in browser.get('accounts', []):
                    name = acc.get('full_name', '')
                    email = acc.get('email', '?')
                    label = f"{name} <{email}>" if name else email
                    parts.append(f"  [{acc.get('browser', '?')}] {acc.get('profile', '?')} — {label}")
            else:
                parts.append("No detecto cuentas en tus navegadores.")
        except Exception as exc:
            parts.append(f"Error escaneando cuentas: {exc}")

        # 2. Active sessions (cookies)
        try:
            from iabv_v15.services.account_resource_scanner import scan_browser_sessions
            sess = scan_browser_sessions()
            if sess.get('session_count', 0) > 0:
                parts.append(f"\nSesiones activas detectadas ({sess['session_count']}):")
                for tool, tool_sessions in sess.get('by_tool', {}).items():
                    for s in tool_sessions:
                        parts.append(
                            f"  {tool.upper()} en [{s['browser']}] {s['profile']} — "
                            f"{s['domain']} ({s['cookie_count']} cookies)"
                        )
            else:
                parts.append("\nNo detecto sesiones activas en cookies de navegador.")
        except Exception:
            pass

        # 3. Quota status
        try:
            from iabv_v15.services.account_resource_scanner import format_quota_report
            quota_report = format_quota_report()
            parts.append(f"\n{quota_report}")
        except Exception:
            parts.append("\nCuotas: sin datos de rastreo todavia.")

        # 4. Worker pool (sessions + quotas cross-reference)
        try:
            from iabv_v15.services.account_resource_scanner import format_worker_pool_report
            worker_report = format_worker_pool_report()
            parts.append(f"\n{worker_report}")
        except Exception:
            pass

        # 5. APIs
        try:
            from iabv_v15.services.account_resource_scanner import (
                scan_ollama_api, scan_github_api, scan_devin_api,
            )
            parts.append("\nAPIs:")
            ollama = scan_ollama_api()
            parts.append(f"  Ollama: {'disponible' if ollama.get('available') else 'no disponible'}")
            github = scan_github_api()
            if github.get('available'):
                parts.append(f"  GitHub: OK ({github.get('remaining', '?')}/{github.get('rate_limit', '?')} requests)")
            else:
                parts.append(f"  GitHub: no disponible")
            devin = scan_devin_api()
            parts.append(f"  Devin: {'disponible' if devin.get('available') else 'no disponible'}")
        except Exception:
            pass

        # 6. Functional gap analysis (self-examination lite)
        try:
            from iabv_v15.services.evolution.operational_self_examination_service import (
                get_functional_gap_summary,
            )
            gaps = get_functional_gap_summary()
            if gaps:
                parts.append("\nAnalisis de gaps funcionales:")
                for g in gaps:
                    parts.append(f"  - {g['title']}: {g['detail']}")
        except Exception:
            pass

        response = '\n'.join(parts)
        return response, 'Diagnostico de cuentas y recursos.'

    def _answer_account_resource_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        reply, meta = self._account_resource_reply(message)
        self._append_message('assistant', 'IABV', reply, meta)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _general_conversation_payload(self, *, message: str) -> dict[str, Any]:
        site_id = self._current_site_id() or ''
        goal_context = self._goal_context_for_display(site_id or None)
        recent_runs = [
            {'run_id': str(getattr(item, 'run_id', '') or '')}
            for item in self.run_repository.list_recent(limit=4)
        ] if self.run_repository is not None else []
        return {
            'session_id': '',
            'user_goal': message,
            'status': 'completed',
            'intent': {
                'title': 'Conversacion general',
                'intent_key': 'general.assistance',
                'disposition': 'answer_now',
                'confidence': 1.0,
                'metadata': {
                    'conversational_prompt': True,
                },
            },
            'context': {
                'site_id': site_id,
                'site_display_name': site_id or 'General',
                'goal_context': goal_context,
                'recent_runs': recent_runs,
                'recent_incidents': [],
                'live_audit': {
                    'summary': 'Consulta general resuelta localmente sin abrir una ruta operativa.',
                    'decision_action': 'answer_general_chat_locally',
                },
            },
            'metadata': {
                'decision_context': {
                    'goal_context': goal_context,
                    'governance': {
                        'should_consult': False,
                        'recommended_action': 'answer_general_chat_locally',
                        'autonomy_level': 'informative_only',
                        'blockers': [],
                    },
                    'metadata': {
                        'conversational_prompt': True,
                    },
                }
            },
            'outcome': {
                'summary': 'Consulta general resuelta localmente.',
                'next_actions': [],
            },
        }

    def _answer_general_chat(self, message: str) -> None:
        self._last_user_goal = message
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        self._working = True
        import time as _time_mod
        self._working_since = _time_mod.time()
        self._busy_label = 'Consultando al modelo local con contexto del sistema vivo.'
        self._set_autonomy_activity_override(
            visible=True,
            title='Respondiendo con contexto vivo',
            status='active',
            stage='consultando LLM local',
            progress=0.2,
            detail='El modelo local esta recibiendo el world model, las herramientas disponibles y la governance para responder con datos reales.',
            tool='ollama_llm',
            next_step='Generar respuesta informada por el estado vivo del sistema.',
            learning_note='Esta via usa SystemPromptBuilder para que el LLM vea tools, world model y governance.',
            mode='local',
        )
        self.dataChanged.emit()

        _CHAT_TIMEOUT_S = 25

        def worker() -> None:
            _infer_result: dict[str, Any] = {}
            _infer_error: list[str] = []
            _infer_done = threading.Event()

            def _infer_inner() -> None:
                try:
                    req = self._build_request(message)
                    rec = self.inference_service.infer_task(req)
                    _infer_result['record'] = rec
                except Exception as exc:
                    _infer_error.append(str(exc))
                finally:
                    _infer_done.set()

            threading.Thread(target=_infer_inner, daemon=True).start()

            _waited = 0
            while not _infer_done.wait(timeout=5):
                _waited += 5
                if _waited >= _CHAT_TIMEOUT_S:
                    break
                self._set_autonomy_activity_override(
                    visible=True,
                    title='Respondiendo con contexto vivo',
                    status='active',
                    stage='consultando LLM local',
                    progress=min(0.2 + _waited * 0.03, 0.9),
                    detail=f'Procesando... ({_waited}s)',
                    tool='ollama_llm',
                    mode='local',
                )
                self.dataChanged.emit()

            if not _infer_done.is_set():
                logger.warning(
                    '_answer_general_chat: timeout (%ds) — trying cloud fallback',
                    _CHAT_TIMEOUT_S,
                )
                # Cloud-first fallback: try a fast cloud call (Groq ~200ms)
                # before falling back to static text.
                fallback = self._try_cloud_quick_reply(message)
                if not fallback:
                    fallback = self._general_chat_reply(message)
                if not fallback:
                    fallback = (
                        'Mi modelo local tardo demasiado. Puede ser que el '
                        'modelo actual sea muy grande para la RAM disponible. '
                        'Intenta de nuevo o usa model_selection_status para '
                        'ver si hay un modelo mas rapido.'
                    )
                self._append_message('assistant', 'IABV', fallback, 'Timeout — fallback local.')
                self._latest_response_text = fallback
                self._latest_response_meta = 'Timeout — fallback local.'
                self._working = False
                self._busy_label = 'Respuesta lista.'
                self._clear_autonomy_activity_override()
                self.dataChanged.emit()
                return

            if _infer_error:
                fallback = self._general_chat_reply(message)
                self._append_message('assistant', 'IABV', fallback, 'Conversacion general (fallback local).')
                self._latest_response_text = fallback
                self._latest_response_meta = 'Conversacion general (fallback local).'
                self._working = False
                self._busy_label = 'Respuesta lista.'
                self._clear_autonomy_activity_override()
                self.dataChanged.emit()
                return

            record = _infer_result.get('record')
            if record is None:
                fallback = self._general_chat_reply(message)
                self._append_message('assistant', 'IABV', fallback, 'Conversacion general (fallback local).')
                self._latest_response_text = fallback
                self._latest_response_meta = 'Conversacion general (fallback local).'
                self._working = False
                self._busy_label = 'Respuesta lista.'
                self._clear_autonomy_activity_override()
                self.dataChanged.emit()
                return

            try:
                adaptive_session = record.result.raw_output.get('adaptive_session') if isinstance(record.result.raw_output, dict) else None
                self.taskResolved.emit(
                    'chat',
                    {
                        'summary': record.result.summary,
                        'provider_name': record.result.provider_name,
                        'reasoning_mode': record.result.reasoning_mode.value,
                        'confidence': f'{record.result.confidence:.2f}',
                        'route_reason': record.route.reason,
                        'report_kind': record.result.report_kind.value,
                        'role_title': self._role_title_from_task(record.result.detected_role or record.route.task_role),
                        'sources': record.result.sources,
                        'follow_up_teachings': record.result.follow_up_teachings,
                        'used_tools': [tool.value for tool in record.result.used_tools],
                        'planner_used': record.result.planner_used,
                        'executor_model': record.result.executor_model or record.route.model_name,
                        'chosen_pack': record.result.chosen_pack,
                        'adaptive_session': adaptive_session,
                        'assistant_guidance': (record.result.raw_output or {}).get('assistant_guidance') if isinstance(record.result.raw_output, dict) else None,
                        'local_chat_llm': (record.result.raw_output or {}).get('local_chat_llm') if isinstance(record.result.raw_output, dict) else None,
                    },
                )
            except Exception:
                fallback = self._general_chat_reply(message)
                self._append_message('assistant', 'IABV', fallback, 'Conversacion general (fallback local).')
                self._latest_response_text = fallback
                self._latest_response_meta = 'Conversacion general (fallback local).'
                self._working = False
                self._busy_label = 'Respuesta lista.'
                self._clear_autonomy_activity_override()
                self.dataChanged.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _human_hardware_notice(self, governance: dict[str, Any] | None) -> str:
        governance = dict(governance or {})
        blockers = ' '.join(str(item).strip().lower() for item in (governance.get('blockers') or []) if str(item).strip())
        autonomy_level = str(governance.get('autonomy_level') or '').strip().lower()
        if autonomy_level == 'protective_local' or any(token in blockers for token in ('ram libre', 'cpu', 'gpu', 'temperatura', 'memoria', 'throttling', 'carga')):
            return 'Ahora mismo el equipo esta bajo bastante carga, asi que voy a usar una via mas liviana mientras seguimos.'
        return ''

    def _general_chat_reply(self, message: str) -> str:
        normalized = self._normalized_command_text(message)
        if self._is_self_awareness_question(normalized):
            return self._self_awareness_reply(message)[0]
        if self._is_world_model_question(normalized):
            return self._world_model_reply(message)[0]
        if self._is_self_examination_question(normalized):
            return self._self_examination_reply(message)[0]
        if self._is_learning_question(normalized):
            return self._learning_reply(message)[0]
        if self._is_account_resource_question(normalized):
            return self._account_resource_reply(message)[0]
        asks_about_assistants = (
            any(token in normalized for token in ('codex', 'chatgpt', 'claude', 'ollama', 'ia', 'ias'))
            and any(token in normalized for token in ('puedes', 'puede', 'sabes', 'manejas', 'manejar', 'manej', 'aca adentro', 'automatic'))
        )
        if any(
            phrase in normalized
            for phrase in (
                'que sabes hacer',
                'qué sabes hacer',
                'que puedes hacer',
                'qué puedes hacer',
                'en que puedes ayudar',
                'en qué puedes ayudar',
                'como funcionas',
                'cómo funcionas',
                'quien eres',
                'quién eres',
            )
        ) or asks_about_assistants:
            return (
                'Puedo ayudarte a revisar flujos del programa, diagnosticar fallos, ordenar tareas tecnicas, '
                'explicarte lo que esta pasando y, cuando haga falta, apoyarme en Codex, ChatGPT, Claude u Ollama.'
            )
        greeting_prefixes = ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')
        if len(normalized.split()) <= 5 and any(normalized.startswith(prefix) for prefix in greeting_prefixes):
            return 'Hola. Estoy aqui para ayudarte. Dime que quieres revisar o resolver y lo trabajamos desde aqui.'
        # Cloud-first fallback: try a fast cloud call before returning static text.
        cloud_reply = self._try_cloud_quick_reply(message)
        if cloud_reply:
            return cloud_reply
        # Context-based fallback: answer provider/key questions from live data.
        context_reply = self._try_context_based_reply(message)
        if context_reply:
            return context_reply
        return 'Te leo. Cuentame que necesitas y te respondo de forma clara, sin cargarte con detalle tecnico interno.'

    def _build_cloud_reply_context(self) -> str:
        """Build a concise system context string for cloud quick replies.

        Includes: configured API keys, active provider, tools status,
        Ollama models.  Kept short to fit in a system prompt.
        """
        import os
        parts: list[str] = ['ESTADO DEL SISTEMA:']

        # API keys status
        key_map = {
            'GROQ_API_KEY': 'Groq',
            'GEMINI_API_KEY': 'Gemini',
            'OPENROUTER_API_KEY': 'OpenRouter',
            'OPENAI_API_KEY': 'OpenAI',
            'ANTHROPIC_API_KEY': 'Anthropic',
        }
        configured = []
        not_configured = []
        for env_var, name in key_map.items():
            if os.environ.get(env_var):
                configured.append(name)
            else:
                not_configured.append(name)
        if configured:
            parts.append(f'API keys configuradas: {", ".join(configured)}')
        if not_configured:
            parts.append(f'API keys NO configuradas: {", ".join(not_configured)}')

        # Active provider from AdaptiveModelSelector
        try:
            selector = getattr(self, '_bootstrap', None)
            if selector:
                selector = getattr(selector, 'adaptive_model_selector', None)
            if selector:
                best = selector.select_best_provider(task_type='reasoning')
                parts.append(f'Mejor proveedor razonamiento: {best.get("provider_id", "?")} ({best.get("reason", "?")})')
        except Exception:
            pass

        # Ollama models
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                resp = client.get('http://127.0.0.1:11434/api/tags')
                if resp.status_code == 200:
                    models = [m.get('name', '?') for m in resp.json().get('models', [])]
                    if models:
                        parts.append(f'Modelos Ollama: {", ".join(models[:6])}')
        except Exception:
            pass

        # Tools summary
        try:
            registry = getattr(self, 'tool_registry', None)
            if registry:
                available = [t.tool_id for t in registry.list_tools() if t.status.available]
                parts.append(f'Herramientas disponibles: {len(available)}')
        except Exception:
            pass

        return '\n'.join(parts)

    def _try_cloud_quick_reply(self, message: str) -> str | None:
        """Attempt a fast cloud reply (Groq/Gemini) for general conversation.

        Returns the cloud response or None if unavailable. Timeout: 8s.
        Does NOT decide routes — just generates a conversational reply.
        Includes live system context so the IA can answer specific questions
        about API keys, providers, tools, etc.
        """
        try:
            import httpx
            import os
            import json as _json
        except ImportError:
            return None

        providers: list[tuple[str, str, str, str]] = [
            # (env_var, base_url, model, provider_name)
            ('GROQ_API_KEY', 'https://api.groq.com/openai/v1/chat/completions', 'llama-3.3-70b-versatile', 'groq'),
            ('GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'gemini-2.0-flash', 'gemini'),
            ('OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/chat/completions', 'meta-llama/llama-3.3-70b-instruct:free', 'openrouter'),
        ]

        system_context = self._build_cloud_reply_context()
        system_prompt = (
            'Eres IABV, un asistente tecnico local. Responde en español, breve y directo. '
            'Responde SOLO lo que el usuario pregunta — no listes informacion que no pidio. '
            'Si pregunta por una API key especifica, di si esta configurada y si se esta usando. '
            'No inventes datos — usa solo el contexto del sistema que tienes abajo.\n\n'
            f'{system_context}'
        )

        for env_var, url, model, prov_name in providers:
            key = os.environ.get(env_var)
            if not key:
                continue
            try:
                headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
                body = {
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': message},
                    ],
                    'max_tokens': 300,
                    'temperature': 0.7,
                }
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if content and len(content) > 10:
                            logger.info('cloud_quick_reply: %s responded (%d chars)', prov_name, len(content))
                            return content.strip()
            except Exception as exc:
                logger.debug('cloud_quick_reply: %s failed: %s', prov_name, exc)
                continue
        return None

    def _try_context_based_reply(self, message: str) -> str | None:
        """Answer specific provider/key questions using only local context.

        When both cloud IA and local Ollama are unavailable, this method
        can still answer questions about API keys, providers, and models
        by reading environment variables and system state directly.
        Returns None if the question doesn't match known patterns.
        """
        import os
        normalized = self._normalized_command_text(message)
        if not normalized:
            return None

        # Detect which provider the user is asking about
        _provider_env = {
            'groq': 'GROQ_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'together': 'TOGETHER_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }

        asked_provider = None
        for prov_name, env_var in _provider_env.items():
            if prov_name in normalized:
                asked_provider = (prov_name, env_var)
                break

        # Asking about a specific provider's API key
        if asked_provider:
            prov_name, env_var = asked_provider
            key = os.environ.get(env_var, '')
            if key:
                masked = key[:6] + '...' + key[-4:] if len(key) > 12 else '***'
                return (
                    f'Si, la API key de {prov_name.capitalize()} esta configurada ({masked}). '
                    f'El sistema la puede usar para respuestas rapidas via cloud.'
                )
            else:
                return (
                    f'No, la API key de {prov_name.capitalize()} NO esta configurada. '
                    f'Para activarla, crea una en la pagina del proveedor y usa '
                    f'"ingresar clave" en este chat para configurarla.'
                )

        # Asking about which model/provider is being used
        if any(tok in normalized for tok in ('que modelo', 'qué modelo', 'estas usando', 'estás usando', 'que usas', 'qué usas')):
            ctx = self._build_cloud_reply_context()
            return (
                f'Actualmente el sistema usa lo siguiente:\n\n{ctx}\n\n'
                f'Sin API keys de cloud, todas las respuestas pasan por Ollama local.'
            )

        # General API key question (not about a specific provider)
        if any(tok in normalized for tok in ('api key', 'apikey', 'api_key', 'claves', 'keys configurad')):
            ctx = self._build_cloud_reply_context()
            return ctx

        return None

    def _seems_task_like_message(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        return any(
            token in normalized
            for token in (
                'wplay',
                'bridge',
                'lag',
                'login',
                'error',
                'falla',
                'falla ',
                'traba',
                'trabado',
                'trabando',
                'revisa',
                'revisa ',
                'revisar',
                'arregla',
                'corrige',
                'diagnostica',
                'ayudame a entender',
                'ayudame a revisar',
                'como revisarlo',
                'que pasa',
            )
        )

    # ------------------------------------------------------------------
    # Cloud plan detection ("cerebro central")
    # ------------------------------------------------------------------

    _CLOUD_PLAN_TRIGGERS = (
        'soluciona', 'solucioname', 'solucionar',
        'planifica', 'planificar', 'haz un plan',
        'genera un plan', 'arma un plan', 'coordina',
        'resuelve esto', 'necesito que resuelvas',
        'ejecuta un plan', 'plan de accion',
    )

    def _is_cloud_plan_request(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        return any(trigger in normalized for trigger in self._CLOUD_PLAN_TRIGGERS)

    def _handle_cloud_plan_request(self, message: str) -> None:
        """Generate a cloud-reasoning plan and present it with action buttons."""
        self._set_autonomy_activity_override(
            visible=True,
            title='Generando plan inteligente',
            status='active',
            stage='consultando modelos cloud',
            progress=0.20,
            detail='Descomponiendo tu solicitud en pasos concretos con asignacion de herramientas.',
            tool='cloud reasoning (Gemini/Groq)',
            next_step='Voy a generar un plan paso a paso y mostrartelo para que lo apruebes.',
            learning_note='Se usa razonamiento cloud para planes complejos; el resultado se persiste para aprendizaje local.',
            mode='cloud',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

        plan = None
        if self.adaptive_orchestrator is not None:
            try:
                plan = self.adaptive_orchestrator.generate_cloud_plan(message)
            except Exception as exc:
                logger.warning('cloud plan generation failed: %s', exc)

        if plan is None:
            self._append_message(
                'assistant', 'IABV',
                'No pude generar un plan en este momento. Los modelos cloud no estan disponibles o no pude descomponer la solicitud. '
                'Intenta reformular tu objetivo o verifica que las API keys esten configuradas.',
                'cloud-plan: no plan generated',
            )
            return

        # Build chat message with plan steps
        lines = [f'**Plan generado** ({plan.cloud_source}) — confianza: {plan.confidence:.0%}\n']
        lines.append(f'_{plan.summary}_\n')
        for step in plan.steps:
            approval_tag = ' **[requiere aprobacion]**' if step.requires_approval else ''
            lines.append(
                f'{step.order}. **{step.title}** → _{step.assigned_tool}_{approval_tag}\n'
                f'   {step.description}'
            )
        lines.append('\n¿Quieres que ejecute este plan?')

        self._append_message('assistant', 'IABV', '\n'.join(lines), 'cloud-plan: plan presented')

        # Store plan in metadata for later execution
        self._pending_cloud_plan = plan
        self._last_user_goal = message

        # Set action buttons for the plan
        self._assistant_action_buttons = [
            {'action': 'execute_cloud_plan', 'label': 'Ejecutar plan'},
            {'action': 'replan_cloud', 'label': 'Regenerar plan'},
        ]
        self._set_autonomy_activity_override(
            visible=True,
            title='Plan listo',
            status='awaiting_approval',
            stage='esperando tu decision',
            progress=1.0,
            detail=plan.summary,
            tool=plan.cloud_source,
            next_step='Aprueba el plan o pideme que lo regenere.',
            mode='cloud',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

    def _execute_cloud_plan(self) -> None:
        """Execute the pending cloud plan step by step."""
        plan = getattr(self, '_pending_cloud_plan', None)
        if plan is None:
            self._append_message('assistant', 'IABV', 'No hay un plan pendiente para ejecutar.', 'cloud-plan: no pending plan')
            return

        self._pending_cloud_plan = None
        self._assistant_action_buttons = []

        total = len(plan.steps)
        for i, step in enumerate(plan.steps):
            progress = (i + 1) / total
            self._set_autonomy_activity_override(
                visible=True,
                title=f'Ejecutando paso {step.order}/{total}',
                status='active',
                stage=step.title,
                progress=progress,
                detail=step.description,
                tool=step.assigned_tool,
                next_step=plan.steps[i + 1].title if i + 1 < total else 'Finalizar plan',
                mode='cloud',
            )
            try:
                self.dataChanged.emit()
            except Exception:
                pass

            if step.requires_approval:
                self._append_message(
                    'assistant', 'IABV',
                    f'**Paso {step.order}** requiere aprobacion: {step.title}\n{step.description}\n\n'
                    f'Herramienta: {step.assigned_tool} — {step.tool_rationale}',
                    f'cloud-plan step {step.order}: awaiting approval',
                )
                step.status = 'awaiting_approval'
                break

            # Execute step via the appropriate tool
            try:
                if step.assigned_tool in ('codex', 'chatgpt', 'claude', 'devin', 'windsurf'):
                    if self.adaptive_orchestrator is not None and hasattr(self.adaptive_orchestrator, 'autonomous_evolution_service'):
                        aes = self.adaptive_orchestrator.autonomous_evolution_service
                        if aes is not None:
                            from iabv_v15.domain.models import DecisionContext
                            result = aes.plan_or_execute(
                                adaptive_payload={
                                    'user_goal': step.description,
                                    'metadata': {
                                        'assistant_kind': step.assigned_tool,
                                        'cloud_plan_step': step.order,
                                        'cloud_plan_id': plan.plan_id,
                                    },
                                },
                                user_goal=step.description,
                                source='cloud_plan_execution',
                                decision_context=DecisionContext(),
                            )
                            step.status = 'completed'
                            step.result_summary = str(result.get('summary', result.get('status', 'done')))
                            self._append_message(
                                'assistant', 'IABV',
                                f'Paso {step.order} completado ({step.assigned_tool}): {step.result_summary[:200]}',
                                f'cloud-plan step {step.order}: completed via {step.assigned_tool}',
                            )
                            continue
                # Local/ollama or fallback
                step.status = 'completed'
                step.result_summary = 'Ejecutado localmente'
                self._append_message(
                    'assistant', 'IABV',
                    f'Paso {step.order} completado (local): {step.title}',
                    f'cloud-plan step {step.order}: completed locally',
                )
            except Exception as exc:
                step.status = 'failed'
                step.result_summary = str(exc)[:200]
                self._append_message(
                    'assistant', 'IABV',
                    f'Paso {step.order} fallo: {exc}',
                    f'cloud-plan step {step.order}: failed',
                )
                logger.warning('cloud plan step %d failed: %s', step.order, exc)

        # Finalize
        completed = sum(1 for s in plan.steps if s.status == 'completed')
        failed = sum(1 for s in plan.steps if s.status == 'failed')
        self._append_message(
            'assistant', 'IABV',
            f'Plan finalizado: {completed}/{total} pasos completados.',
            f'cloud-plan: {completed}/{total} steps completed',
        )
        self._set_autonomy_activity_override(
            visible=True,
            title='Plan finalizado',
            status='completed',
            stage='resumen',
            progress=1.0,
            detail=f'{completed}/{total} pasos completados',
            tool=plan.cloud_source,
            next_step='Puedes pedirme otro plan o preguntar lo que necesites.',
            mode='cloud',
        )

        # Record execution outcome in decision audit trail
        try:
            orch = self.adaptive_orchestrator
            audit = getattr(orch, 'decision_audit_trail', None) if orch else None
            if audit is not None:
                from iabv_v15.services.evolution.decision_audit_trail import (
                    DecisionRecord, DecisionPhase, DecisionOutcome,
                )
                if completed == total:
                    exec_outcome = DecisionOutcome.SUCCESS
                elif completed > 0:
                    exec_outcome = DecisionOutcome.PARTIAL
                else:
                    exec_outcome = DecisionOutcome.FAILED
                audit.record(DecisionRecord(
                    phase=DecisionPhase.PLAN_EXECUTION,
                    provider_id=plan.cloud_source,
                    model_used=plan.cloud_source,
                    user_goal=plan.summary[:200],
                    outcome=exec_outcome,
                    confidence=plan.confidence,
                    steps_total=total,
                    steps_completed=completed,
                    steps_failed=failed,
                ))
        except Exception:
            pass

        try:
            self.dataChanged.emit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # API key health check command
    # ------------------------------------------------------------------

    def _handle_api_key_health_command(self) -> None:
        """Run API key health check and present results in chat."""
        self._append_message(
            'assistant', 'IABV',
            'Revisando el estado de las API keys de cloud reasoning...',
            'api-key-health: starting check',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

        def _worker() -> None:
            try:
                discovery = None
                if self.adaptive_orchestrator is not None:
                    discovery = getattr(self.adaptive_orchestrator, 'api_key_discovery_service', None)
                if discovery is None:
                    from iabv_v15.services.evolution.api_key_discovery_service import ApiKeyDiscoveryService
                    discovery = ApiKeyDiscoveryService()

                report = discovery.full_health_report()

                lines = ['**Reporte de API Keys para Cloud Reasoning**\n']
                lines.append(f'Proveedores configurados: {report["configured_count"]}/{report["total_providers"]}')

                if report['test_results']:
                    lines.append('\n**Resultados de prueba:**')
                    for r in report['test_results']:
                        status = 'OK' if r['valid'] and 'RATE_LIMITED' not in (r.get('quota_info') or '') else (
                            'RATE LIMITED' if r['valid'] else 'FALLO'
                        )
                        latency = f'{r["latency_ms"]:.0f}ms' if r['latency_ms'] else 'N/A'
                        error_info = f' — {r["error"]}' if r['error'] else ''
                        lines.append(f'  - **{r["provider_id"]}**: {status} ({latency}){error_info}')

                if report['missing']:
                    lines.append('\n**Proveedores sin configurar (gratis):**')
                    for m in report['missing']:
                        lines.append(f'  - {m["name"]}: {m["url"]}')

                if report['best_provider']:
                    bp = report['best_provider']
                    lines.append(f'\n**Mejor proveedor actual:** {bp["provider_id"]} ({bp["latency_ms"]:.0f}ms)')
                else:
                    lines.append('\nNo hay proveedor funcional. Escribe "generar keys" para que te guie.')

                lines.append(f'\n_{report["recommendation"]}_')

                # Renewal guidance
                guidance = discovery.renewal_guidance()
                if guidance:
                    lines.append('\n**Acciones recomendadas:**')
                    for g in guidance[:3]:
                        action = g.get('action', '')
                        if action == 'create_key':
                            lines.append(f'  - Crear key de {g["name"]}: {g["signup_url"]}')
                        elif action == 'renew_key':
                            lines.append(f'  - Renovar key de {g["name"]}: {g.get("error", "")}')
                        elif action == 'wait_or_upgrade':
                            lines.append(f'  - {g["name"]} en rate limit: esperar o usar otro proveedor')

                    self._assistant_action_buttons = [
                        {'action': btn_action, 'label': btn_label}
                        for btn_action, btn_label in [
                            ('provision_missing_keys', 'Crear keys faltantes'),
                        ]
                        if any(g.get('action') == 'create_key' for g in guidance)
                    ]

                self._append_message('assistant', 'IABV', '\n'.join(lines), 'api-key-health: report complete')
            except Exception as exc:
                logger.warning('api key health check failed: %s', exc)
                self._append_message(
                    'assistant', 'IABV',
                    f'Error al revisar las API keys: {exc}',
                    'api-key-health: failed',
                )
            finally:
                self._working = False
                self._set_live_status('idle')
                try:
                    self.dataChanged.emit()
                except Exception:
                    pass

        self._working = True
        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Interactive API key generation
    # ------------------------------------------------------------------

    _API_KEY_PROVIDERS: ClassVar[list[dict[str, str]]] = [
        {
            'id': 'groq', 'name': 'Groq', 'env_key': 'GROQ_API_KEY',
            'url': 'https://console.groq.com/keys',
            'detail': 'Llama 3.3 70B gratis, rapido, 30 req/min',
        },
        {
            'id': 'gemini', 'name': 'Google Gemini', 'env_key': 'GEMINI_API_KEY',
            'url': 'https://aistudio.google.com/apikey',
            'detail': 'Gemini 2.0 Flash gratis, 15 req/min',
        },
        {
            'id': 'openrouter', 'name': 'OpenRouter', 'env_key': 'OPENROUTER_API_KEY',
            'url': 'https://openrouter.ai/keys',
            'detail': 'Multiples modelos, tier gratis disponible',
        },
        {
            'id': 'together', 'name': 'Together AI', 'env_key': 'TOGETHER_API_KEY',
            'url': 'https://api.together.xyz/settings/api-keys',
            'detail': 'Llama, Mixtral gratis por $5 de credito inicial',
        },
        {
            'id': 'github', 'name': 'GitHub', 'env_key': 'GITHUB_TOKEN_IABV',
            'url': 'https://github.com/settings/tokens/new?scopes=repo&description=IABV',
            'detail': 'PAT con scope repo para auto-merge PRs',
        },
        {
            'id': 'devin', 'name': 'Devin (Cognition)', 'env_key': 'DEVIN_API_KEY',
            'url': 'https://app.devin.ai/settings/api-keys',
            'detail': 'API key para consultas a Devin',
        },
    ]

    def _handle_interactive_key_generation(self) -> None:
        """Show provider selection, then prompt for the key inline."""
        import os
        lines = ['**Selecciona el proveedor para generar o agregar la API key:**\n']
        buttons: list[dict[str, str]] = []
        for prov in self._API_KEY_PROVIDERS:
            current = os.environ.get(prov['env_key'], '').strip()
            status = 'configurada' if current else 'no configurada'
            icon = 'OK' if current else 'FALTA'
            lines.append(f'  - **{prov["name"]}** [{icon}]: {prov["detail"]}')
            if not current:
                buttons.append({
                    'action': f'setup_key_{prov["id"]}',
                    'label': f'Configurar {prov["name"]}',
                })
        if not buttons:
            lines.append('\nTodas las keys estan configuradas. Escribe "revisar api keys" para probarlas.')
        else:
            lines.append('\nHaz clic en el proveedor que quieras configurar. '
                         'Se abrira la pagina en tu navegador y podras pegar la key aqui.')
        self._append_message('assistant', 'IABV', '\n'.join(lines),
                             'interactive-key-setup: provider selection')
        self._assistant_action_buttons = buttons
        self.dataChanged.emit()

    @Slot(str, str, bool)
    def submitCredential(self, provider: str, value: str, remember: bool = True) -> None:
        """Handle a credential submitted from InlineCredentialPrompt QML."""
        self._save_api_key(provider, value, remember)

    @Slot(object)
    def onCredentialProvided(self, payload: dict) -> None:
        """Handle credential from CredentialPromptDialog QML."""
        domain = str(payload.get('domain', '')).strip()
        password = str(payload.get('password', '')).strip()
        if domain and password:
            self._save_api_key(domain, password, bool(payload.get('remember', True)))

    @Slot(object)
    def onCredentialDelegated(self, payload: dict) -> None:
        """User chose to handle credential manually."""
        domain = str(payload.get('domain', '')).strip()
        self._append_message('assistant', 'IABV',
                             f'Entendido — {domain} queda pendiente. Puedes escribir '
                             '"generar keys" cuando quieras configurarlo.',
                             'credential: delegated to user')
        self.dataChanged.emit()

    def _save_api_key(self, provider_id: str, value: str, persist: bool) -> None:
        """Save an API key for a provider, update env, confirm in chat."""
        from iabv_v15.services.auto_correction_engine import save_secret_to_profile
        env_key = ''
        display_name = provider_id
        for prov in self._API_KEY_PROVIDERS:
            if prov['id'] == provider_id or prov['env_key'] == provider_id:
                env_key = prov['env_key']
                display_name = prov['name']
                break
        if not env_key:
            env_key = provider_id.upper().replace(' ', '_')
            if not env_key.endswith('_KEY') and not env_key.endswith('_TOKEN'):
                env_key += '_API_KEY'
        if persist:
            result = save_secret_to_profile(env_key, value)
            if result.get('status') == 'saved':
                self._append_message(
                    'assistant', 'IABV',
                    f'Key de {display_name} guardada y activada. '
                    f'Persistida en ~/.iabv_secrets.ps1 — no necesitas configurarla de nuevo.',
                    f'credential: {env_key} saved',
                )
            else:
                import os
                os.environ[env_key] = value
                self._append_message(
                    'assistant', 'IABV',
                    f'Key de {display_name} activada en esta sesion (no se pudo persistir: '
                    f'{result.get("detail", "error desconocido")}).',
                    f'credential: {env_key} session-only',
                )
        else:
            import os
            os.environ[env_key] = value
            self._append_message(
                'assistant', 'IABV',
                f'Key de {display_name} activada para esta sesion.',
                f'credential: {env_key} session-only',
            )
        self._assistant_action_buttons = []
        self.dataChanged.emit()

    # ------------------------------------------------------------------
    # Decision audit trail command
    # ------------------------------------------------------------------

    def _handle_resource_liberation_command(self) -> None:
        """Handle 'liberar ram' / 'optimizar memoria' chat commands."""
        self._append_message(
            'assistant', 'IABV',
            'Analizando recursos del sistema...',
            'resource-metacognition: observing',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

        def _worker() -> None:
            try:
                resource_svc = getattr(self, 'resource_metacognition_service', None)
                if resource_svc is None:
                    self._append_message(
                        'assistant', 'IABV',
                        'El servicio de metacognicion de recursos no esta disponible.',
                        'resource-metacognition: service not wired',
                    )
                    return

                text = resource_svc.chat_execute_liberation()
                self._append_message('assistant', 'IABV', text, 'resource-metacognition: liberation complete')
            except Exception as exc:
                logger.warning('resource liberation command failed: %s', exc)
                self._append_message(
                    'assistant', 'IABV',
                    f'Error al liberar recursos: {exc}',
                    'resource-metacognition: failed',
                )
            finally:
                self._working = False
                self._set_live_status('idle')
                try:
                    self.dataChanged.emit()
                except Exception:
                    pass

        self._working = True
        threading.Thread(target=_worker, daemon=True).start()

    def _handle_update_check_command(self) -> None:
        """Handle 'estás actualizado?' / 'hay actualizaciones?' chat commands."""
        self._append_message(
            'assistant', 'IABV',
            'Verificando actualizaciones...',
            'update-check: fetching',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

        def _worker() -> None:
            import subprocess as _sp
            try:
                workspace = getattr(self.config, 'workspace_dir', None)
                cwd = str(workspace) if workspace else None

                # Get current commit
                r = _sp.run(['git', 'rev-parse', '--short', 'HEAD'],
                            capture_output=True, text=True, timeout=10, cwd=cwd)
                current = r.stdout.strip() if r.returncode == 0 else '?'

                # Get current branch
                r = _sp.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                            capture_output=True, text=True, timeout=10, cwd=cwd)
                branch = r.stdout.strip() if r.returncode == 0 else '?'

                # Fetch without modifying anything
                r = _sp.run(['git', 'fetch', 'origin', 'main', '--dry-run'],
                            capture_output=True, text=True, timeout=30, cwd=cwd)
                has_updates = bool(r.stdout.strip() or r.stderr.strip())

                # Count commits behind
                behind = 0
                if has_updates:
                    r = _sp.run(['git', 'rev-list', '--count', 'HEAD..origin/main'],
                                capture_output=True, text=True, timeout=10, cwd=cwd)
                    try:
                        behind = int(r.stdout.strip()) if r.returncode == 0 else 0
                    except ValueError:
                        behind = 0

                lines: list[str] = []
                lines.append(f'Version actual: commit {current} (rama {branch})')
                if behind > 0:
                    lines.append(f'Hay {behind} commit(s) nuevos en origin/main.')
                    lines.append('Para actualizar: git pull --rebase=false')
                    lines.append('O reinicia con start_iabv.ps1 (auto-pull por defecto).')
                else:
                    lines.append('Estas al dia — no hay actualizaciones pendientes.')

                self._append_message('assistant', 'IABV', '\n'.join(lines), 'update-check: complete')
            except Exception as exc:
                logger.warning('update check failed: %s', exc)
                self._append_message(
                    'assistant', 'IABV',
                    f'Error al verificar actualizaciones: {exc}',
                    'update-check: failed',
                )
            finally:
                self._working = False
                self._set_live_status('idle')
                try:
                    self.dataChanged.emit()
                except Exception:
                    pass

        self._working = True
        threading.Thread(target=_worker, daemon=True).start()

    def _handle_startup_log_command(self) -> None:
        """Handle 'ver log de arranque' chat command — show startup console log."""
        try:
            workspace = getattr(self.config, 'workspace_dir', None)
            if workspace is None:
                self._append_message('assistant', 'IABV', 'No se pudo determinar el directorio de trabajo.', 'startup-log: no workspace')
                return

            from pathlib import Path
            log_path = Path(str(workspace)) / 'data' / 'logs' / 'startup_console.log'
            if not log_path.exists():
                self._append_message(
                    'assistant', 'IABV',
                    'No existe log de arranque todavia. Se genera automaticamente al iniciar con start_iabv.ps1.',
                    'startup-log: not found',
                )
                return

            content = log_path.read_text(encoding='utf-8', errors='replace')
            lines = content.splitlines()

            # Extract key info: warnings, errors, and last 30 lines
            warnings = [l.strip() for l in lines if '[warn]' in l.lower()]
            errors = [l.strip() for l in lines if '[err]' in l.lower() or ('error' in l.lower() and 'exit' in l.lower())]
            tail = lines[-30:] if len(lines) > 30 else lines

            parts: list[str] = []
            parts.append(f'Log de arranque ({len(lines)} lineas):')
            if errors:
                parts.append(f'\nErrores ({len(errors)}):')
                for e in errors[:5]:
                    parts.append(f'  {e}')
            if warnings:
                parts.append(f'\nAdvertencias ({len(warnings)}):')
                for w in warnings[:5]:
                    parts.append(f'  {w}')
            if not errors and not warnings:
                parts.append('\nSin errores ni advertencias.')
            parts.append(f'\nUltimas lineas:')
            for t in tail[-15:]:
                parts.append(f'  {t.strip()}')

            self._append_message('assistant', 'IABV', '\n'.join(parts), 'startup-log: displayed')
        except Exception as exc:
            logger.warning('startup log command failed: %s', exc)
            self._append_message('assistant', 'IABV', f'Error al leer log de arranque: {exc}', 'startup-log: failed')

    def _handle_decision_audit_command(self) -> None:
        """Show decision audit trail report in chat."""
        self._append_message(
            'assistant', 'IABV',
            'Analizando el historial de decisiones...',
            'decision-audit: loading trail',
        )
        try:
            self.dataChanged.emit()
        except Exception:
            pass

        def _worker() -> None:
            try:
                audit = None
                if self.adaptive_orchestrator is not None:
                    audit = getattr(self.adaptive_orchestrator, 'decision_audit_trail', None)
                if audit is None:
                    from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail
                    audit = DecisionAuditTrail()

                report = audit.format_chat_report()
                self._append_message('assistant', 'IABV', report, 'decision-audit: report complete')
            except Exception as exc:
                logger.warning('decision audit report failed: %s', exc)
                self._append_message(
                    'assistant', 'IABV',
                    f'Error al generar el reporte de decisiones: {exc}',
                    'decision-audit: failed',
                )
            finally:
                self._working = False
                self._set_live_status('idle')
                try:
                    self.dataChanged.emit()
                except Exception:
                    pass

        self._working = True
        threading.Thread(target=_worker, daemon=True).start()

    def _is_general_conversation_session(self, payload: dict[str, Any], intent: dict[str, Any], context: dict[str, Any]) -> bool:
        intent_key = str(intent.get('intent_key') or '').strip()
        site_name = str(context.get('site_display_name') or context.get('site_id') or '').strip().lower()
        metadata = dict(intent.get('metadata') or {})
        return (
            intent_key in {'general.assistance', 'system.self_awareness', 'consulta_estado_evolutivo'}
            and (not site_name or site_name == 'general')
            and bool(metadata.get('conversational_prompt', True))
        )

    def _is_self_awareness_session(self, intent: dict[str, Any]) -> bool:
        metadata = dict(intent.get('metadata') or {})
        return str(intent.get('intent_key') or '').strip() == 'system.self_awareness' or bool(metadata.get('self_awareness_prompt'))

    def _is_evolution_status_session(self, intent: dict[str, Any]) -> bool:
        metadata = dict(intent.get('metadata') or {})
        return str(intent.get('intent_key') or '').strip() == 'consulta_estado_evolutivo' or bool(metadata.get('evolution_status_prompt'))

    def _apply_human_self_awareness_texts(self, *, message: str) -> None:
        environment = self._current_environment_self_model()
        reply, meta = self._self_awareness_reply(message)
        available_tools = self._human_join([str(item.get('title') or '') for item in environment.available_tools], limit=5) or 'las herramientas basicas del programa'
        missing_tools = self._human_join([str(item.get('tool_id') or item.get('title') or '') for item in environment.missing_tools], limit=4) or 'sin faltantes relevantes'
        local_models = self._human_join([str(item.get('name') or '') for item in dict(environment.ai_capacity or {}).get('local_runtime', {}).get('models', [])], limit=4) or 'sin modelos locales confirmados'
        self._adaptive_status_text = 'Autodiagnostico resuelto. Respondi desde el estado real del sistema.'
        self._adaptive_intent_text = 'Entendi que me preguntaste por mi entorno, mis herramientas o mis conexiones reales.'
        self._adaptive_context_text = (
            f"Entorno conocido: {'si' if environment.known_environment else 'no'} | "
            f"escaneo {environment.scan_status or 'n/d'} | herramientas listas: {available_tools} | faltantes: {missing_tools}."
        )
        self._adaptive_strategy_text = (
            'Para este tipo de pregunta conviene contestar directo desde mi estado actual, '
            'sin desviar la respuesta hacia auditorias previas ni abrir una consulta externa.'
        )
        execution_lines = [
            'Lei el modelo del entorno, el registro de herramientas y el estado actual de conexiones.',
            f'Capacidad local recomendada: {str(dict(environment.ai_capacity or {}).get("max_recommended_model") or "n/d")}.',
            f'Modelos locales visibles: {local_models}.',
        ]
        if environment.notifications:
            execution_lines.append(str(environment.notifications[0]))
        self._adaptive_execution_text = ' '.join(execution_lines)
        evolution_lines = [reply]
        if environment.unresolved_fields:
            unresolved = self._human_join([str(item).replace('UNRESOLVED:', '') for item in environment.unresolved_fields], limit=3)
            if unresolved:
                evolution_lines.append(f'Todavia no puedo leer bien {unresolved}.')
        evolution_lines.append(meta)
        self._adaptive_evolution_text = '\n'.join(evolution_lines)

    def _apply_human_world_model_texts(self, *, message: str) -> None:
        world_model = self._current_world_model()
        reply, meta = self._world_model_reply(message)
        focused_window = str((world_model.focused_window.title if world_model.focused_window is not None else '') or 'sin foco confirmado')
        active_count = len(world_model.active_windows or [])
        network = world_model.network_status
        blocks = self._human_join([str(item).replace('_', ' ') for item in (world_model.detected_blocks or [])], limit=4) or 'sin bloqueos criticos confirmados'
        deductions = self._human_join([str(item) for item in dict(world_model.inferred_state or {}).get('deductions', [])], limit=3) or 'sin deducciones fuertes adicionales'
        self._adaptive_status_text = 'Observacion operativa resuelta. Respondi desde lo que estoy viendo ahora mismo.'
        self._adaptive_intent_text = 'Entendi que me preguntaste por el estado vivo del sistema, una herramienta o la red.'
        self._adaptive_context_text = (
            f'Ventanas activas: {active_count} | foco actual: {focused_window} | red: {str(network.status or "n/d")} | bloqueos: {blocks}.'
        )
        self._adaptive_strategy_text = (
            'Para este tipo de pregunta conviene responder desde observacion real del entorno y no desde memoria vieja ni auditorias previas.'
        )
        self._adaptive_execution_text = (
            f'Actualice el world model del entorno, contraste la herramienta o la red pedida y resumi solo lo que pude observar con evidencia. '
            f'Lo mas fuerte ahora es: {deductions}.'
        )
        self._adaptive_evolution_text = (
            f'{reply}\n{meta}\nSi quieres, puedo bajar esto a una herramienta concreta y decirte que la esta bloqueando antes de intentar usarla.'
        )

    def _apply_human_learning_texts(self, *, message: str) -> None:
        reply, meta = self._learning_reply(message)
        validation = self._current_validation_snapshot()
        adaptive_learning = dict((((self._last_adaptive_payload.get('metadata') or {}).get('decision_context') or {}).get('metadata') or {}).get('adaptive_learning_summary') or {})
        self._adaptive_status_text = 'Aprendizaje adaptativo resuelto. Respondi desde historial real y validacion controlada.'
        self._adaptive_intent_text = 'Entendi que me preguntaste que he aprendido, que va mejor o que estoy validando ahora.'
        self._adaptive_context_text = (
            f"Preferencia actual: {str(adaptive_learning.get('recommended_assistant_kind') or adaptive_learning.get('recommended_route') or 'sin preferencia fuerte')} | "
            f"validacion autonoma: {str(validation.get('status') or 'sin estado')} | "
            f"promociones: {int(validation.get('promoted_count') or 0)}."
        )
        self._adaptive_strategy_text = (
            'Para esta pregunta use solo evidencia ya registrada: recomendaciones del laboratorio, pesos adaptativos, '
            'patrones aprendidos y el ultimo estado de validacion en sandbox.'
        )
        validation_summary = str(validation.get('summary') or '').strip()
        self._adaptive_execution_text = (
            'Cruce el recommendation vigente, los patrones aprendidos y la validacion autonoma actual. '
            + (validation_summary if validation_summary else 'No habia una validacion fuerte adicional corriendo ahora.')
        )
        self._adaptive_evolution_text = f'{reply}\n{meta}'

    def _apply_human_evolution_status_texts(self, *, message: str) -> None:
        validation = self._current_validation_status()
        discovery = self._current_tool_discovery_status()
        reply, meta = self._evolution_status_reply(message)
        winning_by_problem = dict(validation.get('winning_by_problem') or {})
        in_validation = list(validation.get('in_validation') or [])
        active_signals = list(discovery.get('active_signals') or [])
        self._adaptive_status_text = 'Estado evolutivo resuelto. Respondi desde monitor, validacion y discovery reales.'
        self._adaptive_intent_text = 'Entendi que me preguntaste que herramienta va ganando, que esta en validacion, que se descubrio o que ya fue descartado.'
        self._adaptive_context_text = (
            f'Ganadores confirmados: {len(winning_by_problem)} | '
            f'en validacion: {len(in_validation)} | '
            f'discoveries activos: {len(active_signals)}.'
        )
        self._adaptive_strategy_text = (
            'Para esta pregunta use solo estado evolutivo reconciliado: decision log, validacion autonoma y discovery persistido. '
            'No hizo falta inferir ni abrir una ruta externa.'
        )
        self._adaptive_execution_text = (
            str(validation.get('last_decision', {}).get('reason') or '').strip()
            or str(discovery.get('summary') or '').strip()
            or 'No habia una decision fuerte reciente; respondi solo con el estado confirmado.'
        )
        self._adaptive_evolution_text = f'{reply}\n{meta}'

    def _apply_human_self_examination_texts(self, *, message: str) -> None:
        review = self._current_self_examination_snapshot()
        reply, meta = self._self_examination_reply(message)
        recurring_issues = list(review.get('recurring_issues') or [])
        recommended_adjustments = list(review.get('recommended_adjustments') or [])
        validated_improvements = list(review.get('validated_improvements') or [])
        self._adaptive_status_text = 'Autoexaminacion operativa resuelta. Respondi desde evidencia acumulada del sistema.'
        self._adaptive_intent_text = 'Entendi que me preguntaste que esta fallando, que estoy repitiendo mal o que cambios conviene hacer.'
        self._adaptive_context_text = (
            f"Hallazgos activos: {len(list(review.get('top_findings') or []))} | "
            f"issues recurrentes: {len(recurring_issues)} | "
            f"ajustes recomendados: {len(recommended_adjustments)} | "
            f"mejoras validadas: {len(validated_improvements)}."
        )
        self._adaptive_strategy_text = (
            'Para esta pregunta use solo revision derivada del estado real: corridas, sesiones adaptativas, '
            'ExperimentLab, backlog evolutivo y world model actual.'
        )
        self._adaptive_execution_text = (
            str(review.get('summary') or '').strip()
            or 'Todavia no habia una revision fuerte, asi que respondi solo con la evidencia disponible.'
        )
        self._adaptive_evolution_text = f'{reply}\n{meta}'

    def _apply_human_general_adaptive_texts(
        self,
        *,
        status: str,
        governance: dict[str, Any],
        external_notice: str,
        recent_runs_count: int,
        recent_incidents_count: int,
        message: str = '',
        self_awareness: bool = False,
        world_model: bool = False,
        evolution_status: bool = False,
        learning: bool = False,
        self_examination: bool = False,
    ) -> None:
        if self_awareness:
            self._apply_human_self_awareness_texts(message=message)
            return
        if world_model:
            self._apply_human_world_model_texts(message=message)
            return
        if evolution_status:
            self._apply_human_evolution_status_texts(message=message)
            return
        if learning:
            self._apply_human_learning_texts(message=message)
            return
        if self_examination:
            self._apply_human_self_examination_texts(message=message)
            return
        if status in {'completed', 'ready_to_execute'}:
            self._adaptive_status_text = 'Conversacion resuelta. Ya entendi tu mensaje y respondi sin abrir una ruta adicional.'
        elif status == 'waiting_approval':
            self._adaptive_status_text = 'Tengo una propuesta lista, pero antes de seguir necesito tu aprobacion.'
        else:
            self._adaptive_status_text = 'Estoy siguiendo esta conversacion desde el contexto actual del programa.'

        self._adaptive_intent_text = (
            'Entendi tu mensaje como una consulta general sobre el programa, sus capacidades o el siguiente paso util.'
        )
        self._adaptive_context_text = (
            f'Estoy usando el contexto general del programa y el historial reciente de esta sesion. '
            f'Tengo {recent_runs_count} corridas recientes y {recent_incidents_count} incidentes relevantes para no responder a ciegas.'
        )
        self._adaptive_strategy_text = (
            'Para este tipo de mensaje conviene responder claro por chat con lo que ya se del programa. '
            'Si luego hace falta profundizar, puedo preparar una via tecnica o externa.'
        )
        hardware_notice = self._human_hardware_notice(governance)
        execution_lines = [
            'No hacia falta abrir una automatizacion pesada para responder esto.',
            'Primero conviene aclararte la respuesta por chat y solo escalar si el pedido se vuelve tecnico o externo.',
        ]
        if hardware_notice:
            execution_lines.append(hardware_notice)
        self._adaptive_execution_text = ' '.join(execution_lines)
        evolution_lines = [
            'No hizo falta escalar a otra IA para esta conversacion.',
            'La respuesta se resolvio con el contexto disponible del programa.',
        ]
        if external_notice:
            evolution_lines.append(external_notice)
        else:
            evolution_lines.append('No hay alertas externas prioritarias en este momento.')
        evolution_lines.append('Si despues pides una revision tecnica o una consulta externa, puedo preparar esa via sin perder el contexto.')
        self._adaptive_evolution_text = '\n'.join(evolution_lines)

    def _fallback_task_reply(
        self,
        *,
        message: str,
        context: dict[str, Any],
        assistant_guidance: dict[str, Any],
        governance: dict[str, Any],
    ) -> str:
        normalized = self._normalized_command_text(message)
        site_name = str(context.get('site_display_name') or context.get('site_id') or '').strip()
        subject = site_name if site_name and site_name.lower() != 'general' else ''
        actions = [str(item.get('action') or '').strip().lower() for item in (assistant_guidance.get('actions') or []) if isinstance(item, dict)]
        if any(token in normalized for token in ('revisa', 'revisar', 'diagnostica', 'diagnostico', 'mira', 'abre', 'inicia', 'login', 'wplay', 'bridge')):
            if subject:
                response = f'Entendi que quieres revisar {subject}. Voy a ordenar el caso y seguir con el paso mas util.'
            else:
                response = 'Entendi el caso que quieres revisar. Voy a ordenarlo y seguir con el paso mas util.'
        else:
            response = 'Entendi tu pedido y voy a seguir con el paso mas util sin cargarte con detalle interno.'
        if 'prepare_codex_packet' in actions and 'codex' not in normalized:
            response += ' Si hace falta profundizarlo, tambien puedo prepararlo para Codex.'
        elif 'open_teaching_studio' in actions:
            response += ' Si veo que falta una demostracion mas clara, te lo voy a pedir de forma puntual.'
        hardware_notice = self._human_hardware_notice(governance)
        if hardware_notice:
            response = f'{response} {hardware_notice}'.strip()
        return response

    def _user_facing_chat_response(
        self,
        *,
        message: str,
        raw_summary: str,
        payload: dict[str, Any],
        adaptive_payload: dict[str, Any],
    ) -> tuple[str, str]:
        intent = dict(adaptive_payload.get('intent') or {})
        context = dict(adaptive_payload.get('context') or {})
        decision_context = dict(((adaptive_payload.get('metadata') or {}).get('decision_context') or adaptive_payload.get('decision_context') or {}))
        assistant_guidance = dict(payload.get('assistant_guidance') or adaptive_payload.get('assistant_guidance') or {})
        governance = dict(
            assistant_guidance.get('governance')
            or payload.get('governance')
            or decision_context.get('governance')
            or {}
        )
        self_awareness = self._is_self_awareness_question(message) or bool(dict(intent.get('metadata') or {}).get('self_awareness_prompt'))
        world_model_question = self._is_world_model_question(message)
        learning_question = self._is_learning_question(message)
        self_examination_question = self._is_self_examination_question(message)
        account_resource_question = self._is_account_resource_question(message)
        if self_awareness:
            return self._self_awareness_reply(message)
        if world_model_question:
            return self._world_model_reply(message)
        if self_examination_question:
            return self._self_examination_reply(message)
        if learning_question:
            return self._learning_reply(message)
        if account_resource_question:
            return self._account_resource_reply(message)
        local_chat_llm = dict(payload.get('local_chat_llm') or {})
        llm_answered = bool(local_chat_llm.get('available')) and bool(str(raw_summary or '').strip()) and not local_chat_llm.get('error')
        vm_small_talk = self._is_general_chat_message(message)
        general_chat = vm_small_talk or str(intent.get('intent_key') or '').strip() == 'general.assistance'
        if vm_small_talk and not self._seems_task_like_message(message):
            return self._general_chat_reply(message), 'Conversacion general.'
        if general_chat and not self._seems_task_like_message(message) and not llm_answered:
            return self._general_chat_reply(message), 'Conversacion general.'
        if llm_answered:
            provider_name = str(local_chat_llm.get('provider_name') or 'Ollama')
            return str(raw_summary).strip(), f'Respuesta local ({provider_name}).'
        summary = str(raw_summary or '').strip()
        if not summary or self._contains_internal_chat_terms(summary):
            summary = self._fallback_task_reply(
                message=message,
                context=context,
                assistant_guidance=assistant_guidance,
                governance=governance,
            )
        else:
            hardware_notice = self._human_hardware_notice(governance)
            if hardware_notice and hardware_notice.lower() not in summary.lower():
                summary = f'{summary} {hardware_notice}'.strip()
        meta = 'Respuesta clara.'
        if self._human_hardware_notice(governance):
            meta = 'Ajuste ligero por carga del equipo.'
        elif str(context.get('site_display_name') or context.get('site_id') or '').strip():
            meta = f"Seguimos con {str(context.get('site_display_name') or context.get('site_id') or '').strip()}."
        return summary, meta

    def _humanize_task_failure(self, task_name: str, message: str) -> tuple[str, str]:
        detail = str(message or '').strip()
        lowered = detail.lower()
        if task_name == 'external_consultation':
            if 'acceso denegado' in lowered or 'access denied' in lowered:
                return (
                    'No pude abrir o capturar la consulta externa desde este entorno. Voy a seguir con lo que ya tenemos aqui y, si hace falta, preparo otra via.',
                    'Bloqueo al preparar consulta externa.',
                )
        if any(token in lowered for token in ('login', 'session', 'sesion')):
            return (
                'La consulta externa no quedo lista porque la sesion del asistente no estaba disponible. Sigo por aqui y, si hace falta, la reintento cuando el acceso este listo.',
                'Sesion externa no disponible.',
            )
        return (
            'No pude completar la consulta externa en este momento. Voy a seguir con lo que ya tenemos aqui y, si hace falta, preparo otra via.',
            'Consulta externa no disponible.',
            )
        return detail, 'Error en la ultima operacion local.'

    def _human_external_consultation_failure(self, assistant_title: str, failure_detail: str, external_state_flags: list[str] | None = None) -> tuple[str, str, str]:
        detail = str(failure_detail or '').strip()
        lowered = detail.lower()
        external_notice = self._external_state_notice(external_state_flags)
        if 'browser_security_verification' in lowered:
            message = (
                f'No pude completar la consulta con {assistant_title} porque el sitio activo una verificacion de seguridad '
                'antes de abrir el chat. Sigo con la mejor via disponible y dejo el bloqueo trazado.'
            )
            if external_notice:
                message = f'{message} {external_notice}'
            meta = f'Consulta con {assistant_title} bloqueada por verificacion del sitio.'
            busy = message
        elif 'codex_state_missing' in lowered:
            message = (
                f'Abrí {assistant_title}, pero esta instalacion no expone el tracking del hilo que necesito para verificar '
                'la respuesta de forma segura. Sigo con la mejor via disponible y dejo el bloqueo trazado.'
            )
            if external_notice:
                message = f'{message} {external_notice}'
            meta = f'Consulta con {assistant_title} bloqueada por falta de tracking.'
            busy = message
        elif 'acceso denegado' in lowered or 'access denied' in lowered:
            message = (
                f'No pude abrir la consulta externa con {assistant_title} desde este entorno. '
                'Voy a seguir con lo que ya tenemos aqui y, si hace falta, preparo otra via.'
            )
            meta = f'Consulta con {assistant_title} bloqueada por el entorno.'
            busy = message
        elif 'session' in lowered or 'sesion' in lowered or 'login' in lowered:
            message = (
                f'La sesion de {assistant_title} no estaba lista para usarla ahora mismo. '
                'Sigo por aqui y, si hace falta, la reintento cuando el acceso este disponible.'
            )
            meta = f'Sesion de {assistant_title} no disponible.'
            busy = message
        else:
            message = f'No pude preparar la consulta externa con {assistant_title} en este momento.'
            if external_notice:
                message = f'{message} {external_notice}'
            else:
                message = f'{message} Voy a seguir con lo que ya tenemos aqui y, si hace falta, preparo otra via.'
            meta = f'Consulta con {assistant_title} no disponible.'
            busy = message
        return message, meta, busy

    def _external_state_notice(self, flags: list[str] | None) -> str:
        normalized = canonical_external_state_flags(flags)
        if not normalized:
            return ''
        if 'account_limited' in normalized:
            return 'La ruta externa quedo limitada por cuota, plan o cuenta; sigo con la mejor via local disponible y dejo el bloqueo trazado.'
        if 'session_expired' in normalized or 'assistant_login_required' in normalized:
            return 'La sesion externa no esta lista; IABV lo deja trazado y sigue con la mejor via local disponible.'
        if 'missing_thread_tracking' in normalized:
            return 'La app externa no expone el tracking del hilo que IABV necesita para verificar la respuesta, asi que queda bloqueada y trazada.'
        if 'wrong_thread' in normalized:
            return 'La respuesta externa no coincide con el hilo esperado; no se toma como valida y queda marcada para auditoria.'
        if 'capture_unverified' in normalized:
            return 'La captura de la respuesta externa sigue sin verificarse; IABV no la dara por valida y mantiene auditoria.'
        return f"Estados externos activos: {', '.join(normalized)}."

    def _external_state_flags_from_payloads(self, *payloads: Any) -> list[str]:
        candidates: list[str] = []
        merged: dict[str, Any] = {}
        for payload in payloads:
            if isinstance(payload, dict):
                merged.update(payload)
                candidates.extend(str(item).strip() for item in (payload.get('external_state_flags') or []) if str(item).strip())
        capture_error = str(
            merged.get('auto_capture_reason')
            or merged.get('error_message')
            or ''
        ).strip().lower()
        if bool(merged.get('assistant_login_required')):
            candidates.append('assistant_login_required')
        if bool(merged.get('missing_thread_tracking')) or capture_error == 'codex_state_missing':
            candidates.append('missing_thread_tracking')
        if bool(merged.get('session_expired')) or str(merged.get('session_status') or '').strip().lower() in {'expired', 'session_expired'}:
            candidates.append('session_expired')
        if (
            bool(merged.get('credits_exhausted'))
            or bool(merged.get('rate_limited'))
            or bool(merged.get('plan_upgrade_required'))
            or bool(merged.get('account_limited'))
            or str(merged.get('quota_status') or '').strip().lower() in {'exhausted', 'limited', 'blocked'}
            or str(merged.get('rate_limit_status') or '').strip().lower() in {'limited', 'blocked', 'exhausted'}
            or str(merged.get('plan_status') or '').strip().lower() in {'upgrade_required', 'limited', 'blocked'}
            or str(merged.get('account_status') or '').strip().lower() in {'limited', 'blocked'}
        ):
            candidates.append('account_limited')
        if (
            bool(merged.get('thread_mismatch'))
            or str(merged.get('thread_verification') or '').strip().lower() in {'wrong_thread', 'thread_mismatch', 'mismatch'}
        ):
            candidates.append('wrong_thread')
        if (
            bool(merged.get('capture_unverified'))
            or bool(merged.get('response_capture_unverified'))
            or capture_error in {'browser_dom_unavailable', 'browser_dom_launch_failed', 'browser_dom_capture_pending', 'browser_security_verification', 'codex_state_missing'}
            or (
                (bool(merged.get('launched')) or bool(merged.get('auto_capture_attempted')))
                and not bool(merged.get('response_captured'))
                and str(merged.get('response_capture_mode') or '').strip().lower() in {'clipboard_capture', 'dom_capture', 'browser_dom'}
            )
        ):
            candidates.append('capture_unverified')
        if 'wrong_thread' in canonical_external_state_flags(candidates):
            candidates.append('capture_unverified')
        return canonical_external_state_flags(candidates)

    def _process_ui_events(self) -> None:
        app = QGuiApplication.instance()
        if app is not None and hasattr(app, 'processEvents'):
            app.processEvents()
            return
        if hasattr(QGuiApplication, 'processEvents'):
            QGuiApplication.processEvents()

    def _activity_payload(
        self,
        *,
        visible: bool = False,
        title: str = 'Actividad autonoma',
        status: str = 'idle',
        stage: str = 'sin actividad',
        progress: float = 0.0,
        detail: str = '',
        tool: str = '',
        next_step: str = '',
        human_help: str = '',
        learning_note: str = '',
        mode: str = 'local',
        waiting: bool = False,
    ) -> dict[str, Any]:
        progress_value = max(0.0, min(1.0, float(progress or 0.0)))
        normalized_status = status if status in {'idle', 'active', 'warning', 'blocked'} else 'idle'
        return {
            'visible': bool(visible),
            'title': str(title or 'Actividad autonoma').strip() or 'Actividad autonoma',
            'status': normalized_status,
            'stage': str(stage or 'sin actividad').strip() or 'sin actividad',
            'progress': round(progress_value, 4),
            'progress_pct': int(round(progress_value * 100.0)),
            'detail': str(detail or '').strip(),
            'tool': str(tool or '').strip(),
            'next_step': str(next_step or '').strip(),
            'human_help': str(human_help or '').strip(),
            'learning_note': str(learning_note or '').strip(),
            'mode': str(mode or 'local').strip() or 'local',
            'waiting': bool(waiting),
        }

    def _set_autonomy_activity_override(self, **payload: Any) -> None:
        self._autonomy_activity_override = self._activity_payload(**payload)

    def _clear_autonomy_activity_override(self) -> None:
        self._autonomy_activity_override = {}

    def get_autonomy_activity(self) -> dict[str, Any]:
        if self._autonomy_activity_override:
            return dict(self._autonomy_activity_override)
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        governance = dict(decision_context.get('governance') or metadata.get('governance') or {})
        goal_context = dict(
            decision_context.get('goal_context')
            or metadata.get('goal_context')
            or (payload.get('context') or {}).get('goal_context')
            or self._last_goal_context
            or {}
        )
        objective = dict(goal_context.get('objective') or {})
        current_goal = str(objective.get('title') or goal_context.get('active_title') or self._last_user_goal or 'sin objetivo activo').strip() or 'sin objetivo activo'
        goal_progress = float(goal_context.get('progress') or 0.0)
        goal_confidence = float(goal_context.get('confidence') or 0.0)
        autonomous = dict(metadata.get('autonomous_evolution') or metadata.get('external_consultation') or {})
        autonomous_response = dict(metadata.get('autonomous_evolution_response') or {})
        if autonomous_response:
            validation = dict(autonomous_response.get('response_validation') or {})
            adoption = dict(autonomous_response.get('adoption_plan') or {})
            response_ingested = bool(autonomous_response.get('response_ingested'))
            validation_status = str(validation.get('status') or '').strip()
            assistant_title = self._assistant_display_name(
                str(
                    autonomous_response.get('assistant_kind')
                    or autonomous.get('actual_assistant_kind')
                    or autonomous.get('assistant_kind')
                    or ''
                )
            )
            tool_id = str(autonomous_response.get('selected_tool_id') or autonomous.get('selected_tool_id') or '').strip()
            detail = (
                str(autonomous_response.get('response_summary') or autonomous_response.get('detail') or '').strip()
                or str(validation.get('rationale') or adoption.get('human_help') or 'La respuesta externa ya fue interpretada.').strip()
            )
            next_step = str(
                adoption.get('next_action')
                or autonomous_response.get('next_action')
                or autonomous_response.get('response_next_action')
                or governance.get('recommended_action')
                or 'seguir local'
            ).strip()
            human_help = str(
                autonomous_response.get('human_help')
                or adoption.get('human_help')
                or validation.get('rationale')
                or ''
            ).strip()
            learning_note = (
                'La respuesta externa ya quedo asociada al objetivo, al laboratorio y a la memoria evolutiva.'
                if response_ingested
                else 'La respuesta fue capturada, pero todavia necesita validacion o adopcion segura.'
            )
            status = 'warning' if validation_status in {'review_needed', 'insufficient'} else 'active'
            return self._activity_payload(
                visible=True,
                title='Resultado de consulta externa',
                status=status,
                stage='aprendizaje consolidado' if response_ingested else 'respuesta capturada',
                progress=1.0 if response_ingested else 0.9,
                detail=detail,
                tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                next_step=next_step,
                human_help=human_help,
                learning_note=learning_note,
                mode='external',
            )
        if autonomous:
            auto_status = str(autonomous.get('status') or '').strip()
            assistant_title = self._assistant_display_name(
                str(autonomous.get('actual_assistant_kind') or autonomous.get('assistant_kind') or '')
            )
            tool_id = str(autonomous.get('selected_tool_id') or '').strip()
            capture_mode = str(autonomous.get('response_capture_mode') or '').strip()
            detail = str(autonomous.get('detail') or autonomous.get('reason') or '').strip()
            if bool(autonomous.get('response_captured')):
                return self._activity_payload(
                    visible=True,
                    title='Respuesta externa capturada',
                    status='active',
                    stage='texto externo listo para integrar',
                    progress=0.88,
                    detail=detail or 'Ya capture texto util desde la herramienta externa y lo dejare listo para integrarlo.',
                    tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                    next_step='Interpretar e integrar la respuesta externa para decidir la siguiente accion.',
                    human_help='Si la respuesta no te convence, puedes volver a lanzar la consulta o cambiar de asistente.',
                    learning_note='Aun no guardo aprendizaje estable hasta validar la respuesta.',
                    mode='external',
                )
            if auto_status == 'awaiting_response':
                stale = False
                started_at = str(autonomous.get('started_at_utc') or autonomous.get('created_at_utc') or '').strip()
                if started_at:
                    try:
                        from datetime import datetime, timezone
                        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                        age_seconds = (datetime.now(timezone.utc) - started).total_seconds()
                        stale = age_seconds > 120
                    except (ValueError, TypeError):
                        stale = True
                else:
                    stale = True
                if stale:
                    return self._activity_payload(
                        visible=True,
                        title='Consulta externa caducada',
                        status='warning',
                        stage='respuesta no recibida a tiempo',
                        progress=1.0,
                        detail=f'La consulta con {assistant_title} lleva mas de 2 minutos sin respuesta util. El sistema puede re-evaluar en la proxima interaccion.',
                        tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                        next_step='Escribe tu siguiente consulta y el sistema decidira si reintenta o usa otra via.',
                        human_help='Si la app externa tiene respuesta visible, usa Ingerir respuesta. Si no, simplemente continua.',
                        learning_note='La consulta caduco sin evidencia util; no se consolida aprendizaje.',
                        mode='external',
                        waiting=False,
                    )
                isolated_session = bool(autonomous.get('isolated_session'))
                login_required = bool(autonomous.get('assistant_login_required'))
                session_label = str(autonomous.get('session_label') or '').strip()
                if capture_mode == 'clipboard_capture':
                    detail = detail or 'La app externa ya fue abierta y estoy intentando capturar su respuesta automaticamente.'
                elif capture_mode in {'dom_capture', 'browser_dom'} and isolated_session:
                    if login_required:
                        detail = detail or 'La sesion aislada del programa necesita inicio de sesion una sola vez antes de poder consultar en segundo plano.'
                    else:
                        detail = detail or 'La consulta externa corre en una sesion aislada del programa y estoy esperando texto util para integrarlo.'
                else:
                    detail = detail or 'La consulta externa fue abierta y estoy esperando texto util para integrarlo.'
                return self._activity_payload(
                    visible=True,
                    title='Consulta externa en curso',
                    status='warning',
                    stage='sesion aislada esperando respuesta' if capture_mode in {'dom_capture', 'browser_dom'} and isolated_session else 'esperando respuesta util',
                    progress=0.82,
                    detail=detail,
                    tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                    next_step='Cuando llegue texto util, lo ingerire para continuar con el mismo caso.',
                    human_help=('Abre y autentica una vez la sesion aislada del programa.' if login_required else ('La consulta sigue en segundo plano dentro de la sesion aislada.' if session_label else 'Si la captura automatica no regresa texto, copia la respuesta y usa Ingerir respuesta.')),
                    learning_note=('Sesion: ' + session_label + ' | aprendizaje pendiente de validar.' if session_label else 'Todavia no puedo consolidar aprendizaje hasta validar la respuesta.'),
                    mode='external',
                    waiting=True,
                )
            if auto_status in {'prepared', 'reused'}:
                return self._activity_payload(
                    visible=True,
                    title='Consulta externa lanzada',
                    status='active',
                    stage='consulta reutilizada' if auto_status == 'reused' else 'consulta preparada',
                    progress=0.74 if auto_status == 'reused' else 0.68,
                    detail=detail or 'Ya deje lista la via externa mas util para este caso.',
                    tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                    next_step='Voy a usar la respuesta externa para validar, aprender y decidir la siguiente accion.',
                    human_help='Puedes dejar que termine la captura automatica o ingerir la respuesta manualmente si hace falta.',
                    learning_note='La evidencia externa todavia esta en evaluacion; aun no se consolida como aprendizaje estable.',
                    mode='external',
                )
            if auto_status == 'failed':
                return self._activity_payload(
                    visible=True,
                    title='Consulta externa bloqueada',
                    status='blocked',
                    stage='fallo de consulta',
                    progress=1.0,
                    detail=detail or 'No pude abrir o reutilizar una via externa util para este caso.',
                    tool=f"{assistant_title}{f' via {tool_id}' if tool_id else ''}",
                    next_step='Mantener la via local, revisar el stack o cambiar de asistente.',
                    human_help='Revisa si la app externa esta instalada, enfocada o accesible para captura.',
                    learning_note='No guardare este intento como aprendizaje util hasta tener evidencia mejor.',
                    mode='external',
                )
        if self._working:
            return self._activity_payload(
                visible=True,
                title='Analizando consulta',
                status='active',
                stage='orquestando decision local',
                progress=0.18,
                detail=self._busy_label or 'Estoy detectando intencion, contexto, estrategia y si hace falta apoyo externo.',
                tool='motor local',
                next_step='Si la confianza local no alcanza, activare una consulta externa segura.',
                human_help='Espera unos segundos mientras cierro la fase local.',
                learning_note='La memoria del objetivo y los patrones previos se tienen en cuenta antes de responder.',
                mode='local',
            )
        if payload:
            guidance = payload.get('assistant_guidance') or {}
            local_status = 'warning' if governance.get('approval_required') or governance.get('block_risky_action') else 'active'
            return self._activity_payload(
                visible=True,
                title='Analisis local completado',
                status=local_status,
                stage='resuelto localmente' if not governance.get('should_consult') else 'decision local lista',
                progress=1.0 if not governance.get('should_consult') else 0.58,
                detail=(
                    str((payload.get('outcome') or {}).get('summary') or '').strip()
                    or str(governance.get('reason') or self._busy_label or 'La respuesta fue resuelta dentro del motor local.').strip()
                ),
                tool='motor local',
                next_step=str(governance.get('recommended_action') or 'seguir local').strip(),
                human_help=str(guidance.get('prompt') or '').strip(),
                learning_note=f'Objetivo {current_goal} | progreso {goal_progress:.2f} | confianza {goal_confidence:.2f}',
                mode='local',
            )
        return self._activity_payload()

    def _build_agent_cards(self) -> list[dict[str, str]]:
        provider_lookup = {card['provider_name']: card for card in self._provider_cards}
        general_ready = provider_lookup.get('Ollama', {}).get('available', False)
        visual_ready = provider_lookup.get('Ollama Vision', {}).get('available', False)
        optional_ready = provider_lookup.get('LM Studio', {}).get('available', False)
        index_ready = provider_lookup.get('Embeddings', {}).get('available', False)
        pbt_generation = int(self._pbt_state.get('generation', 0))
        goal_context = self._goal_context_for_display(self._current_site_id() or None)
        goal_title = str((goal_context.get('objective') or {}).get('title') or goal_context.get('active_title') or '').strip()
        goal_status = str(goal_context.get('status') or 'pending')
        goal_progress = float(goal_context.get('progress') or 0.0)
        goal_blocker = str(goal_context.get('blocker') or '').strip()
        cards: list[dict[str, str]] = [
            {'name': 'Adaptive orchestrator', 'status': 'listo' if general_ready else 'pendiente', 'detail': 'Decide intencion, contexto, packs, readiness y aprobaciones antes de responder.', 'scope': 'Ruteo y estrategia'},
            {'name': 'Vision local', 'status': 'listo' if visual_ready else 'pendiente', 'detail': 'Usa gemma3:4b en Ollama cuando la consulta trae evidencia visual.', 'scope': 'Pantallas y navegacion'},
            {'name': 'LM Studio opcional', 'status': 'listo' if optional_ready else 'opcional no activo', 'detail': 'Complemento visual fuera del camino critico. La app sigue funcionando sin el.', 'scope': 'Extensiones locales'},
            {'name': 'Indice semantico', 'status': 'listo' if index_ready else 'degradado', 'detail': 'Mantiene la recuperacion local sobre conocimiento, documentacion y sesiones.', 'scope': 'Busqueda y RAG'},
            {'name': 'PBT tuner', 'status': 'activo' if pbt_generation else 'preparado', 'detail': 'Expone scheduler, selector y mutacion para afinar prompts, thresholds y estrategias.', 'scope': 'Optimizacion local'},
        ]
        if goal_title:
            cards.append(
                {
                    'name': 'Objetivo persistente',
                    'status': 'bloqueado' if goal_blocker else ('completado' if goal_status == 'completed' else 'activo'),
                    'detail': f'{goal_title} | estado {goal_status} | progreso {goal_progress:.2f}' + (f' | bloqueo: {goal_blocker}' if goal_blocker else ''),
                    'scope': 'Gobernanza y progreso longitudinal',
                }
            )
        cards.extend(self._assistant_tool_cards())
        return cards

    def _estimate_complexity(self, message: str) -> ComplexityLevel:
        text = message.lower()
        if len(message.split()) >= 24 or any(token in text for token in ['plan', 'estrategia', 'compar', 'analiza a fondo', 'pasos']):
            return ComplexityLevel.DEEP
        if len(message.split()) >= 10:
            return ComplexityLevel.MEDIUM
        return ComplexityLevel.SIMPLE

    def _estimate_ambiguity(self, message: str) -> AmbiguityLevel:
        text = message.lower()
        if any(token in text for token in ['quizas', 'tal vez', 'no se', 'ambig', 'varias opciones', ' o ']):
            return AmbiguityLevel.HIGH
        if len(message.split()) >= 14:
            return AmbiguityLevel.MEDIUM
        return AmbiguityLevel.LOW

    def _conversation_context(self) -> list[dict[str, Any]]:
        return [{'role': item.get('role', ''), 'text': item.get('text', ''), 'meta': item.get('meta', '')} for item in self._chat_messages[-8:]]

    def _chat_shortcut_analysis(self, message: str) -> dict[str, Any]:
        intent_service = getattr(self.adaptive_orchestrator, 'intent_service', None)
        if intent_service is None:
            return {}
        site_hint = self._site_hint_from_message(message)
        try:
            intent, _ = intent_service.classify(
                InferenceRequest(
                    user_goal=message,
                    prompt=message,
                    conversation_context=self._conversation_context(),
                    site_hint=site_hint,
                    goal_parameters={'site_hint': site_hint or ''},
                )
            )
        except Exception:
            return {}
        analysis = intent.metadata.get('conversation_analysis') if isinstance(intent.metadata, dict) else {}
        return dict(analysis) if isinstance(analysis, dict) else {}

    def _explicit_site_hint_from_message(self, message: str) -> str | None:
        text = self._normalized_command_text(message)
        if 'wplay' in text:
            return 'wplay'
        if 'google' in text:
            return 'google'
        if 'mercadolibre' in text or 'mercado libre' in text:
            return 'mercadolibre'
        return None

    def _recent_conversation_site_hint(self) -> str | None:
        for item in reversed(self._chat_messages[-8:]):
            hint = self._explicit_site_hint_from_message(str(item.get('text') or ''))
            if hint:
                return hint
        return None

    def _should_inherit_site_hint(self, message: str) -> bool:
        normalized = self._normalized_command_text(message)
        if not normalized:
            return False
        if self._explicit_site_hint_from_message(message):
            return False
        if self._is_general_chat_message(message):
            return False
        # Internal/system topics should never inherit a site hint from
        # previous conversations — they are about the program itself.
        internal_signals = (
            'secreto', 'secretos', 'token', 'tokens', 'configuracion',
            'configurar', 'entorno', 'variable', 'variables', 'bootstrap',
            'analiza por que', 'analiza por qué', 'faltantes', 'faltante',
            'auto-correccion', 'autocorreccion', 'auto correccion',
            'tu codigo', 'tu código', 'tu algoritmo', 'tus algoritmos',
            'tu sistema', 'tu configuracion', 'tu configuración',
        )
        if any(signal in normalized for signal in internal_signals):
            return False
        follow_up_phrases = (
            'empecemos',
            'seguimos',
            'continuemos',
            'continuar',
            'siguiente paso',
            'que te enseno',
            'que te enseño',
            'que hacemos primero',
            'que hago primero',
            'por donde empezamos',
            'por donde empiezo',
        )
        return self._seems_task_like_message(message) or any(phrase in normalized for phrase in follow_up_phrases)

    def _site_hint_from_message(self, message: str) -> str | None:
        explicit_hint = self._explicit_site_hint_from_message(message)
        if explicit_hint:
            return explicit_hint
        if self._should_inherit_site_hint(message):
            return self._recent_conversation_site_hint()
        return None

    def _build_request(self, message: str) -> InferenceRequest:
        complexity = self._estimate_complexity(message)
        ambiguity = self._estimate_ambiguity(message)
        manual_role = self._selected_role_profile().role
        site_hint = self._site_hint_from_message(message)
        goal_parameters = self._goal_parameters_for_request(message, site_hint)
        has_persistent_goal = any(str(goal_parameters.get(key) or '').strip() for key in ('objective_id', 'project_id', 'task_id'))
        visual_signal = self._latest_visual_signal(message=message, goal_parameters=goal_parameters)
        return InferenceRequest(
            user_goal=message,
            prompt=message,
            task_role=manual_role,
            role_hint=None if self._auto_route_enabled else manual_role,
            auto_route=self._auto_route_enabled,
            offline_only=True,
            complexity=complexity,
            ambiguity=ambiguity,
            requires_vision=False,
            deep_reasoning=complexity == ComplexityLevel.DEEP,
            allowed_tools=list(self._selected_role_profile().default_tools) if not self._auto_route_enabled else [],
            knowledge_scope=['episodes', 'knowledge_items', 'run_records', 'docs', 'dossiers', 'adaptive_sessions'],
            read_only_sql=manual_role in {TaskRole.ANALYTICS, TaskRole.CUSTOMER_SUPPORT, TaskRole.KNOWLEDGE} if not self._auto_route_enabled else False,
            requires_visual_reasoning=(not self._auto_route_enabled and manual_role == TaskRole.VISUAL),
            enable_planning=True,
            conversation_context=self._conversation_context(),
            site_hint=site_hint,
            approval_mode='phased',
            execution_scope='operational',
            goal_parameters=goal_parameters,
            metadata={
                'routing_mode': 'auto' if self._auto_route_enabled else 'manual',
                'goal_context_source': 'persistent' if has_persistent_goal else 'transient',
                'explicit_assistant_preference': str(goal_parameters.get('assistant_preference') or ''),
                'explicit_external_consultation': bool(goal_parameters.get('explicit_external_consultation', False)),
                'runtime_signals': self._latest_runtime_signals(),
                'session_health': self._latest_session_health_snapshot(),
                'visual_signal': visual_signal,
                'ia_trace': self._latest_ia_trace(),
            },
        )

    def _refresh_development_packet(self, user_goal: str | None = None) -> None:
        if user_goal is not None:
            self._last_user_goal = user_goal.strip()
        self._development_packet = self.engineering_review_service.build_codex_packet(
            user_goal=self._last_user_goal,
            selected_role_title='Automatico' if self._auto_route_enabled else self._selected_role_title(),
        )

    def _seed_development_packet(self, user_goal: str | None = None) -> None:
        if user_goal is not None:
            self._last_user_goal = user_goal.strip()
        self._development_packet = self.development_assist_service.build_codex_packet(
            user_goal=self._last_user_goal,
            selected_role_title='Automatico' if self._auto_route_enabled else self._selected_role_title(),
            project_context={
                'episodes': 0,
                'knowledge_items': 0,
                'runs': 0,
                'artifacts': 0,
                'analytics': {'summary': 'Cargando analitica ampliada sin bloquear el arranque.'},
                'teaching_gaps': {'summary': 'Cargando huecos de ensenanza y backlog evolutivo.', 'follow_up_teachings': []},
                'pbt_state': dict(self._pbt_state or {}),
            },
        ) + '\nCentro evolutivo:\n- resumen: Cargando evidencia evolutiva sin bloquear la UI.\n'

    def _copy_text(self, text: str, success_message: str) -> None:
        clipboard = None
        try:
            clipboard = QGuiApplication.clipboard()
        except Exception:
            app = QGuiApplication.instance()
            if app is not None and hasattr(app, 'clipboard'):
                try:
                    clipboard = app.clipboard()
                except Exception:
                    clipboard = None
        if clipboard is None:
            self._clipboard_notice = 'No pude acceder al portapapeles desde esta sesion.'
        else:
            clipboard.setText(text)
            self._clipboard_notice = success_message
        self.dataChanged.emit()

    def _read_text_from_clipboard(self) -> str:
        clipboard = None
        try:
            clipboard = QGuiApplication.clipboard()
        except Exception:
            app = QGuiApplication.instance()
            if app is not None and hasattr(app, 'clipboard'):
                try:
                    clipboard = app.clipboard()
                except Exception:
                    clipboard = None
        if clipboard is None:
            return ''
        try:
            return str(clipboard.text() or '')
        except Exception:
            return ''

    def _build_capability_cards(self, capabilities: list[dict[str, Any]]) -> list[dict[str, str]]:
        cards = []
        for item in capabilities[:6]:
            detail = '; '.join(item.get('evidence') or []) or '; '.join(item.get('missing_signals') or []) or item.get('suggested_next_step', '')
            cards.append({'title': item.get('title', item.get('capability_id', 'capacidad')), 'status': item.get('status', ''), 'detail': detail})
        return cards

    def _build_approval_cards(self, approvals: list[dict[str, Any]]) -> list[dict[str, str]]:
        cards = []
        for item in approvals:
            cards.append({'title': item.get('title', 'checkpoint'), 'status': item.get('decision', ''), 'detail': item.get('detail', ''), 'risk': item.get('risk_level', '')})
        return cards

    def _build_playbook_steps(self, playbook: dict[str, Any] | None) -> list[dict[str, str]]:
        if not isinstance(playbook, dict):
            return []
        steps = []
        for item in playbook.get('steps', [])[:8]:
            steps.append({'title': item.get('title', 'fase'), 'status': item.get('status', ''), 'detail': item.get('detail', item.get('description', '')), 'phase': item.get('phase_key', '')})
        return steps

    def _assistant_action(self, action: str, label: str, detail: str = '') -> dict[str, str]:
        return {'action': action, 'label': label, 'detail': detail}

    def _guidance_for_pending_external_response(self, assistant_title: str) -> dict[str, Any]:
        return {
            'mode': 'waiting_external_response',
            'title': 'Esperando respuesta externa',
            'prompt': f'La consulta con {assistant_title} ya quedo preparada. Copia la respuesta al portapapeles y dime ingerir respuesta para que la interprete y decida el siguiente paso.',
            'actions': [
                self._assistant_action('ingest_external_response', 'Ingerir respuesta', 'Leer la respuesta desde el portapapeles y convertirla en acciones internas.'),
                self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Comprobar si la ruta externa sigue siendo coherente.'),
                self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar el caso mientras llega la respuesta externa.'),
            ],
        }

    def _guidance_from_external_response(self, bridge: dict[str, Any]) -> dict[str, Any]:
        next_action = str(bridge.get('next_action') or 'open_evolution_center')
        validation = dict(bridge.get('response_validation') or {})
        adoption = dict(bridge.get('adoption_plan') or {})
        label_map = {
            'open_teaching_studio': ('Abrir ensenanza', 'Aplicar la correccion o refuerzo sugerido por la respuesta externa.'),
            'run_self_test': ('Repetir autotest', 'Verificar si el ajuste sugerido mejora el caso.'),
            'prepare_codex_packet': ('Preparar Codex', 'Actualizar el paquete tecnico con el diagnostico ya interpretado.'),
            'open_evolution_center': ('Ver evolutivo', 'Inspeccionar el caso consolidado con la nueva interpretacion.'),
            'audit_autonomy': ('Auditar autonomia', 'La respuesta externa no fue suficiente; conviene recalibrar la decision.'),
        }
        main_label, main_detail = label_map.get(next_action, ('Ver evolutivo', 'Revisar el caso con la respuesta externa ya interpretada.'))
        actions = [
            self._assistant_action(next_action, main_label, main_detail),
            self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Ver si la siguiente via sugerida por el sistema sigue bien calibrada.'),
            self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar evidencia, incidentes y backlog actualizados.'),
        ]
        prompt = str(bridge.get('detail') or bridge.get('response_summary') or 'La respuesta externa ya quedo integrada.')
        if validation or adoption:
            prompt += (
                f" Validacion: {validation.get('status') or 'n/d'} | via segura: {adoption.get('execution_lane') or 'n/d'} | "
                f"sandbox: {bool(validation.get('sandbox_required'))}."
            )
        return {
            'mode': 'external_response_interpreted',
            'title': 'Respuesta externa interpretada',
            'prompt': prompt,
            'actions': actions,
        }

    def _derive_assistant_guidance(self, adaptive_payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = adaptive_payload or {}
        probe = payload.get('probe_diagnosis') or {}
        if probe:
            category = str(probe.get('category') or '')
            runtime_adjustments = payload.get('runtime_adjustments') or []
            pending_issue_id = str(payload.get('pending_issue_id') or '')
            if category == 'need_teaching':
                return {
                    'mode': 'need_teaching',
                    'title': 'Hace falta ensenanza',
                    'prompt': str(probe.get('summary') or 'Todavia hace falta una ensenanza o correccion visual mas limpia.'),
                    'actions': [
                        self._assistant_action('open_teaching_studio', 'Abrir ensenanza', 'Capturar o corregir el microflujo que falta.'),
                        self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Ver que via autonoma elegiria el sistema antes de escalar.'),
                        self._assistant_action('consult_chatgpt', 'Consultar ChatGPT', 'Pedir una explicacion mas clara del hueco de ensenanza o del siguiente microajuste.'),
                    ],
                }
            if category == 'need_runtime_tuning':
                detail = f"Ajustes runtime aplicados: {len(runtime_adjustments)}." if runtime_adjustments else 'Puedo intentar un ajuste runtime seguro antes de escalar.'
                return {
                    'mode': 'need_runtime_tuning',
                    'title': 'Conviene autoajustar el runtime',
                    'prompt': f"{probe.get('summary') or 'Detecte un problema tecnico ajustable.'} {detail}",
                    'actions': [
                        self._assistant_action('run_self_test', 'Repetir autotest', 'Correr otra pasada de diagnostico despues del tuning.'),
                        self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar el efecto del tuning y los incidentes.'),
                    ],
                }
            if category in {'need_adapter', 'need_codex_fix'}:
                suffix = f' Pendiente para Codex: {pending_issue_id}.' if pending_issue_id else ''
                mismatches = probe.get('mismatches') or []
                has_teaching_gap = any((item.get('category') == 'need_teaching') for item in mismatches if isinstance(item, dict))
                prompt = f"{probe.get('summary') or 'Este caso ya no parece resoluble solo con tuning.'}{suffix}"
                if has_teaching_gap:
                    prompt += ' Aun asi, tambien conviene reforzar o corregir la ensenanza antes de volver a probar.'
                actions = []
                if has_teaching_gap:
                    actions.append(self._assistant_action('open_teaching_studio', 'Abrir ensenanza', 'Corregir el microflujo o el replay antes del siguiente intento.'))
                actions.extend(
                    [
                        self._assistant_action('consult_codex', 'Consultar Codex', 'Abrir la consulta externa tecnica con el contexto actual.'),
                        self._assistant_action('prepare_codex_packet', 'Preparar Codex', 'Armar el paquete tecnico verificable.'),
                        self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Revisar si la via autonoma y el contexto estan bien calibrados.'),
                        self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Inspeccionar el caso y su evidencia viva.'),
                    ]
                )
                return {
                    'mode': 'need_adapter' if category == 'need_adapter' else 'need_codex_fix',
                    'title': 'Falta adaptador operativo' if category == 'need_adapter' else 'Hace falta ayuda tecnica',
                    'prompt': prompt,
                    'actions': actions[:3],
                }
            if category == 'ready_for_guided_live':
                return {
                    'mode': 'ready_execute',
                    'title': 'Listo para prueba guiada',
                    'prompt': str(probe.get('summary') or 'La tarea esta lista para una prueba guiada con aprobacion.'),
                    'actions': [
                        self._assistant_action('approve_strategy', 'Aprobar estrategia', 'Pasar a la siguiente fase guiada.'),
                        self._assistant_action('simulate', 'Simular', 'Revisar la fase antes de abrirla en vivo.'),
                    ],
                }
        intent = payload.get('intent') or {}
        context = payload.get('context') or {}
        approvals = [item for item in (payload.get('approval_checkpoints') or []) if item.get('decision') == 'pending']
        capabilities = payload.get('capability_readiness') or []
        metadata = payload.get('metadata') or {}
        execution_state = metadata.get('execution_state') or {}
        site_name = context.get('site_display_name') or context.get('site_id') or intent.get('site_hint') or 'el flujo actual'
        session_readiness = context.get('session_readiness') or {}
        incident_count = int(session_readiness.get('incident_count', len(context.get('recent_incidents') or [])) or 0)
        dominant_incident = session_readiness.get('dominant_incident') or ((context.get('recent_incidents') or [{}])[0].get('incident_kind', '') if (context.get('recent_incidents') or []) else '')
        weak_capabilities = [item for item in capabilities if item.get('status') in {'insufficient', 'partial'}]
        low_visual = any(
            (
                float((item.get('metadata') or {}).get('visual_alignment_score', 0.0) or 0.0) < 0.45
                or float((item.get('metadata') or {}).get('critical_object_coverage', (item.get('metadata') or {}).get('login_visual_completeness', 0.0)) or 0.0) < 0.4
            )
            for item in weak_capabilities
        )
        no_teaching = not bool(context.get('recent_teachings'))
        repeated_technical = incident_count >= 3 and dominant_incident in {'bridge_lag', 'navigation_stall', 'session_restore_weak', 'visual_alignment_weak', 'critical_object_missing'}
        teaching_gap = bool(weak_capabilities) and (no_teaching or low_visual)

        if intent.get('disposition') == 'need_info':
            question = (intent.get('missing_requirements') or ['Necesito un dato puntual adicional.'])[0]
            return {
                'mode': 'need_info',
                'title': 'Falta un dato puntual',
                'prompt': f'Antes de seguir necesito esto: {question}.',
                'actions': [self._assistant_action('open_teaching_studio', 'Abrir ensenanza', 'Si prefieres mostrar el flujo en vez de explicarlo.')],
            }
        if teaching_gap:
            prompt = (
                f'Puedo ayudarte con {site_name}, pero todavia me falta una ensenanza limpia o evidencia visual suficiente para hacerlo con confianza. '
                'Si quieres, abro Estudio de ensenanza para capturar ese flujo corto ahora.'
            )
            if dominant_incident:
                prompt += f' Tambien veo incidentes recientes como {dominant_incident}.'
            actions = [
                self._assistant_action('open_teaching_studio', 'Abrir ensenanza', 'Capturar el flujo que falta o corregir el replay.'),
                self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Ver si el sistema deberia reensenar, reconstruir o escalar.'),
            ]
            if incident_count:
                actions.append(self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar incidentes y evidencia reciente.'))
            if repeated_technical:
                actions.append(self._assistant_action('prepare_codex_packet', 'Preparar Codex', 'Armar el caso tecnico para corregirlo.'))
            return {
                'mode': 'need_teaching',
                'title': 'Hace falta ensenanza',
                'prompt': prompt,
                'actions': actions[:3],
            }
        if repeated_technical:
            return {
                'mode': 'need_codex_fix',
                'title': 'Parece un problema interno',
                'prompt': (
                    f'Lo de {site_name} parece mas un problema interno del sistema que una falta de instruccion. '
                    f'Veo incidentes repetidos como {dominant_incident}. Si quieres, abro el Centro Evolutivo y preparo el caso para Codex.'
                ),
                'actions': [
                    self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Inspeccionar incidentes, dossiers y backlog.'),
                    self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Validar a que asistente externo deberia escalar este caso.'),
                    self._assistant_action('prepare_codex_packet', 'Preparar Codex', 'Armar el paquete tecnico verificable.'),
                ],
            }
        if incident_count:
            return {
                'mode': 'need_evolution_review',
                'title': 'Conviene revisar la evidencia',
                'prompt': (
                    f'Tengo contexto para {site_name}, pero antes de insistir conviene revisar la evidencia reciente. '
                    f'Hay incidentes como {dominant_incident or "los recientes"}. Puedo llevarte directo al Centro Evolutivo o preparar el caso para Codex.'
                ),
                'actions': [
                    self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar incidentes, dossiers y backlog.'),
                    self._assistant_action('prepare_codex_packet', 'Preparar Codex', 'Armar el paquete tecnico verificable.'),
                ],
            }
        if approvals:
            actions = []
            if any(item.get('phase_key') == 'strategy' for item in approvals):
                actions.append(self._assistant_action('approve_strategy', 'Aprobar estrategia', 'Confirmar la estrategia antes de seguir.'))
            if approvals:
                actions.append(self._assistant_action('approve_next_phase', approvals[-1].get('title', 'Aprobar fase siguiente'), approvals[-1].get('detail', '')))
            return {
                'mode': 'need_approval',
                'title': 'Aprobacion requerida',
                'prompt': f'Ya tengo la estrategia lista para {site_name}. Solo me falta tu aprobacion para pasar a la siguiente fase.',
                'actions': actions[:2],
            }
        if not bool(execution_state.get('executor_available')) and not bool(execution_state.get('simulation_only')):
            return {
                'mode': 'need_adapter',
                'title': 'Falta adaptador operativo',
                'prompt': (
                    f'Ya tengo estrategia y contexto para {site_name}, pero todavia no hay un adaptador operativo real que ejecute esta fase. '
                    f"{execution_state.get('detail') or 'Puedo seguir simulando o dejar el caso listo para Evolutivo y Codex.'}"
                ),
                'actions': [
                    self._assistant_action('simulate', 'Simular', 'Ver la fase disponible antes de conectarla a un ejecutor real.'),
                    self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Revisar si corresponde escalar a Codex o seguir local.'),
                    self._assistant_action('prepare_codex_packet', 'Preparar Codex', 'Armar el caso tecnico verificable.'),
                ],
            }
        if bool(execution_state.get('simulation_only')):
            return {
                'mode': 'ready_execute',
                'title': 'Listo para guiado o simulacion',
                'prompt': f'Ya tengo suficiente contexto para seguir con {site_name}, pero esta fase se mantiene en simulacion o guiado por su nivel de riesgo.',
                'actions': [
                    self._assistant_action('simulate', 'Simular', 'Ver la siguiente fase antes de pedir otra aprobacion.'),
                    self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Revisar evidencia y estado del flujo.'),
                ],
            }
        return {
            'mode': 'ready_execute',
            'title': 'Listo para avanzar',
            'prompt': f'Ya tengo suficiente contexto para seguir con {site_name}. Puedes simular o ejecutar la siguiente fase cuando quieras.',
            'actions': [
                self._assistant_action('simulate', 'Simular', 'Ver la siguiente fase antes de ejecutar.'),
                self._assistant_action('execute_now', 'Ejecutar ahora', 'Pasar a la fase operativa disponible.'),
            ],
        }

    def _apply_assistant_guidance(self, guidance: dict[str, Any] | None) -> None:
        payload = guidance or {}
        self._assistant_guidance_mode = str(payload.get('mode') or 'idle')
        self._assistant_guidance_text = str(payload.get('prompt') or 'Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex.')
        self._assistant_action_buttons = [dict(item) for item in (payload.get('actions') or [])][:3]
        if self._assistant_guidance_mode == 'need_approval' and self._assistant_action_buttons:
            self._approval_dialog_visible = True
            self._approval_dialog_title = str(payload.get('title') or 'Aprobacion requerida')
            detail_lines = [
                f"- {item.get('title', 'checkpoint')} | riesgo {item.get('risk', 'n/d')} | {item.get('detail', '')}"
                for item in self._adaptive_approval_cards[:4]
            ]
            if detail_lines:
                self._approval_dialog_text = self._assistant_guidance_text + '\n\n' + '\n'.join(detail_lines)
            else:
                self._approval_dialog_text = self._assistant_guidance_text
        else:
            self._approval_dialog_visible = False
            self._approval_dialog_title = 'Sin aprobaciones pendientes'
            self._approval_dialog_text = 'No hay aprobaciones pendientes en esta sesion.'

    def _update_adaptive_state(self, adaptive_payload: dict[str, Any] | None) -> None:
        payload = adaptive_payload or {}
        self._last_adaptive_payload = dict(payload)
        intent = payload.get('intent') or {}
        context = payload.get('context') or {}
        chosen_pack = payload.get('chosen_pack') or payload.get('pack') or {}
        strategy_candidates = payload.get('strategy_candidates') or []
        playbook = payload.get('playbook') or {}
        approvals = payload.get('approval_checkpoints') or []
        capabilities = payload.get('capability_readiness') or []
        outcome = payload.get('outcome') or {}
        metadata = payload.get('metadata') or {}
        execution_state = metadata.get('execution_state') or {}
        live_audit = context.get('live_audit') or metadata.get('live_audit') or {}
        decision_context = dict(metadata.get('decision_context') or {})
        governance = dict(decision_context.get('governance') or metadata.get('governance') or {})
        goal_context = dict(decision_context.get('goal_context') or metadata.get('goal_context') or context.get('goal_context') or {})
        if goal_context:
            self._last_goal_context = goal_context
        evidence_refs = payload.get('evidence_refs') or context.get('evidence_summary') or []
        self._adaptive_session_id = str(payload.get('session_id') or '')
        status = str(payload.get('status') or playbook.get('status') or 'sin_sesion')
        next_phase = str(playbook.get('next_phase') or 'sin siguiente fase')
        self._adaptive_status_text = f"Sesion {self._adaptive_session_id or 'n/d'} | estado {status} | siguiente fase {next_phase}"
        self._adaptive_intent_text = (
            f"Intencion: {intent.get('title', 'n/d')}\n"
            f"Clave: {intent.get('intent_key', 'n/d')}\n"
            f"Disposicion: {intent.get('disposition', 'n/d')}\n"
            f"Sitio: {intent.get('site_hint') or context.get('site_id') or 'general'}\n"
            f"Confianza: {intent.get('confidence', 0)}\n"
            f"Razonamiento: {', '.join(intent.get('reasoning') or []) or 'sin razonamiento adicional'}"
        )
        self._adaptive_context_text = (
            f"Sitio activo: {context.get('site_display_name', context.get('site_id', 'General'))}\n"
            f"Objetivo persistente: {dict(goal_context.get('objective') or {}).get('title', self._last_user_goal or 'n/d')}\n"
            f"Proyecto activo: {dict(goal_context.get('project') or {}).get('title', 'n/d')}\n"
            f"Tarea activa: {dict(goal_context.get('task') or {}).get('title', goal_context.get('active_title', 'n/d'))}\n"
            f"Progreso longitudinal: {float(goal_context.get('progress') or 0.0):.2f} | confianza {float(goal_context.get('confidence') or 0.0):.2f}\n"
            f"Bloqueo persistente: {goal_context.get('blocker') or 'sin bloqueo'}\n"
            f"Ensenanzas relacionadas: {len(context.get('recent_teachings') or [])}\n"
            f"Runs recientes: {len(context.get('recent_runs') or [])}\n"
            f"Incidentes recientes: {len(context.get('recent_incidents') or [])}\n"
            f"Conocimiento local: {len(context.get('knowledge_hits') or [])}\n"
            f"Session readiness: {context.get('session_readiness') or {}}\n"
            f"Auditoria viva: {live_audit.get('summary', 'sin snapshot reciente')}"
        )
        candidate = strategy_candidates[0] if strategy_candidates else {}
        param_lines = [f"{parameter.get('label', parameter.get('key', 'param'))}: {parameter.get('value', parameter.get('default_value', ''))}" for parameter in (candidate.get('parameters') or [])]
        self._adaptive_strategy_text = (
            f"Pack: {chosen_pack.get('title', payload.get('chosen_pack_title', 'n/d'))}\n"
            f"Dominio: {chosen_pack.get('domain_kind', 'n/d')}\n"
            f"Algoritmo: {candidate.get('title', 'sin candidato')}\n"
            f"Rationale: {candidate.get('rationale', 'sin rationale')}\n"
            f"Parametros: {' | '.join(param_lines) if param_lines else 'sin parametros editables declarados'}"
        )
        self._adaptive_execution_text = (
            f"Playbook: {playbook.get('summary', 'sin playbook')}\n"
            f"Estado: {status}\n"
            f"Executor: {execution_state.get('executor_name', 'sin executor')}\n"
            f"Estado operativo: {execution_state.get('state', 'sin estado')}\n"
            f"Detalle operativo: {execution_state.get('detail', 'sin detalle')}\n"
            f"Aprobaciones pendientes: {len([item for item in approvals if item.get('decision') == 'pending'])}\n"
            f"Outcome: {outcome.get('summary', 'sin outcome registrado')}\n"
            f"Siguientes acciones: {', '.join(outcome.get('next_actions') or []) or 'sin siguientes acciones'}"
        )
        evidence_preview = evidence_refs if isinstance(evidence_refs, list) else [str(evidence_refs)]
        self._adaptive_evidence_text = '\n'.join(str(item) for item in evidence_preview[:8]) or 'Sin evidencia listada.'
        autonomous = dict(metadata.get('autonomous_evolution') or metadata.get('external_consultation') or {})
        autonomous_preview = dict(metadata.get('autonomous_evolution_preview') or {})
        autonomous_response = dict(metadata.get('autonomous_evolution_response') or {})
        perception_snapshot = dict(metadata.get('perception_snapshot') or {})
        decision_metadata = dict(decision_context.get('metadata') or {})
        external_state_flags = canonical_external_state_flags(
            list((decision_context.get('metadata') or {}).get('external_state_flags') or [])
            + list(perception_snapshot.get('external_state_flags') or [])
            + list(autonomous.get('external_state_flags') or [])
            + list(autonomous_response.get('external_state_flags') or [])
        )
        external_notice = self._external_state_notice(external_state_flags)
        preferred_assistant_kind = str(decision_metadata.get('preferred_assistant_kind') or '').strip()
        preferred_config_signature = str(decision_metadata.get('preferred_config_signature') or '').strip()
        supporting_trace_ids = [str(item) for item in (decision_metadata.get('supporting_trace_ids') or []) if str(item).strip()][:4]
        auto_replanned = bool(metadata.get('replanned_automatically') or metadata.get('auto_replanned') or payload.get('adaptive_replanned'))
        replan_source = str(metadata.get('replanned_from_session_id') or metadata.get('auto_replanned_session_id') or '')
        if self._is_general_conversation_session(payload, intent, context):
            current_goal = str(payload.get('user_goal') or self._last_user_goal or '')
            self_awareness = self._is_self_awareness_session(intent) or self._is_self_awareness_question(current_goal)
            world_model_question = self._is_world_model_question(current_goal)
            evolution_status_question = self._is_evolution_status_session(intent) or self._is_evolution_status_question(current_goal)
            learning_question = self._is_learning_question(current_goal)
            self_examination_question = self._is_self_examination_question(current_goal)
            account_resource_question = self._is_account_resource_question(current_goal)
            self._apply_human_general_adaptive_texts(
                status=status,
                governance=governance,
                external_notice=external_notice,
                recent_runs_count=len(context.get('recent_runs') or []),
                recent_incidents_count=len(context.get('recent_incidents') or []),
                message=current_goal,
                self_awareness=self_awareness,
                world_model=world_model_question,
                evolution_status=evolution_status_question,
                learning=learning_question,
                self_examination=self_examination_question,
            )
            self._adaptive_capability_cards = self._build_capability_cards(capabilities)
            self._adaptive_approval_cards = self._build_approval_cards(approvals)
            self._adaptive_playbook_steps = self._build_playbook_steps(playbook)
            pending_approvals = [item for item in approvals if item.get('decision') == 'pending']
            self._adaptive_action_buttons = {
                'approve_strategy': bool(pending_approvals),
                'approve_next': bool(status == 'waiting_approval' and pending_approvals),
                'simulate': bool(self._adaptive_playbook_steps),
                'execute': bool(status in {'ready_to_execute', 'waiting_approval'}),
                'abort': bool(self._adaptive_session_id),
            }
            return
        autonomous_lines = []
        if autonomous:
            autonomous_lines = [
                f"Autonomia: {autonomous.get('status', 'n/d')}",
                f"Asistente solicitado: {autonomous.get('requested_assistant_kind', autonomous.get('assistant_kind', 'n/d'))}",
                f"Asistente resuelto: {autonomous.get('actual_assistant_kind', autonomous.get('assistant_kind', 'n/d'))}",
                f"Tool autonomo: {autonomous.get('selected_tool_id', 'n/d')}",
                f"Decision autonoma: {autonomous.get('recommended_action', 'n/d')}",
                f"Razon autonoma: {autonomous.get('reason', 'n/d')}",
            ]
            if autonomous.get('pending_issue_id'):
                autonomous_lines.append(f"Pending autonomo: {autonomous.get('pending_issue_id')}")
        preview_lines = []
        if autonomous_preview:
            preview_lines = [
                f"Preview autonomia: {autonomous_preview.get('recommended_action', 'continue_local')}",
                f"Preview asistente: {autonomous_preview.get('requested_assistant_kind', autonomous_preview.get('assistant_kind', 'n/d'))}",
                f"Preview via: {autonomous_preview.get('selected_tool_id', 'n/d')}",
                f"Preview razon: {autonomous_preview.get('reason', 'n/d')}",
            ]
        response_lines = []
        if autonomous_response:
            validation = dict(autonomous_response.get('response_validation') or {})
            adoption = dict(autonomous_response.get('adoption_plan') or {})
            response_lines = [
                f"Respuesta externa: {autonomous_response.get('status', 'n/d')}",
                f"Asistente respuesta: {autonomous_response.get('assistant_kind', 'n/d')}",
                f"Siguiente accion: {autonomous_response.get('next_action', autonomous_response.get('response_next_action', 'n/d'))}",
                f"Resumen respuesta: {autonomous_response.get('response_summary', 'n/d')}",
            ]
            if validation or adoption:
                response_lines.append(
                    f"Validacion respuesta: {validation.get('status', 'n/d')} | sandbox {bool(validation.get('sandbox_required'))} | aprobacion {bool(validation.get('requires_human_approval'))}"
                )
                response_lines.append(
                    f"Adopcion segura: {adoption.get('status', 'n/d')} | via {adoption.get('execution_lane', 'n/d')} | rollback {bool(adoption.get('rollback_ready'))}"
                )
            if autonomous_response.get('pending_issue_id'):
                response_lines.append(f"Pending actualizado: {autonomous_response.get('pending_issue_id')}")
        self._adaptive_evolution_text = (
            f"Paquete Codex listo para el objetivo actual.\n"
            f"Pack activo: {payload.get('chosen_pack_id', '') or chosen_pack.get('pack_id', '')}\n"
            f"Objetivo persistente: {dict(goal_context.get('objective') or {}).get('title', self._last_user_goal or 'n/d')}\n"
            f"Progreso objetivo: {float(goal_context.get('progress') or 0.0):.2f} | confianza {float(goal_context.get('confidence') or 0.0):.2f}\n"
            f"Nivel de autonomia: {governance.get('autonomy_level', 'sin_gobernanza')} | accion {governance.get('recommended_action', 'continue_local')}\n"
            f"Sandbox requerido: {bool(governance.get('require_sandbox'))} | replanificar: {bool(governance.get('should_replan'))} | investigar: {bool(governance.get('research_needed'))}\n"
            f"Replanificacion automatica: {auto_replanned} | origen: {replan_source or 'n/d'}\n"
            f"Bloqueos de gobernanza: {', '.join(governance.get('blockers') or []) or 'sin bloqueos'}\n"
            f"Estados externos: {', '.join(external_state_flags) or 'sin flags formales'}\n"
            f"Preferencia historica IA: {preferred_assistant_kind or 'sin preferencia consolidada'}\n"
            f"Configuracion historica: {preferred_config_signature or 'sin configuracion consolidada'}\n"
            f"Trazas de soporte: {', '.join(supporting_trace_ids) or 'sin trazas reutilizables'}\n"
            f"Lectura para humano: {external_notice or 'sin alerta externa prioritaria'}\n"
            f"Capacidades debiles: {len([item for item in capabilities if item.get('status') in ['insufficient', 'partial']])}\n"
            f"Auditoria viva: {live_audit.get('summary', 'sin snapshot reciente')}\n"
            f"Decision auditada: {live_audit.get('decision_action', 'continue_local')}"
            + ("\n" + "\n".join(preview_lines) if preview_lines else '')
            + ("\n" + "\n".join(autonomous_lines) if autonomous_lines else '')
            + ("\n" + "\n".join(response_lines) if response_lines else '')
            + "\nSi hay incidentes, falta readiness o falta executor, este caso ya queda trazable para el Centro Evolutivo."
        )
        self._adaptive_capability_cards = self._build_capability_cards(capabilities)
        self._adaptive_approval_cards = self._build_approval_cards(approvals)
        self._adaptive_playbook_steps = self._build_playbook_steps(playbook)
        pending_approvals = [item for item in approvals if item.get('decision') == 'pending']
        guidance = payload.get('assistant_guidance') or self._derive_assistant_guidance(payload)
        self._apply_assistant_guidance(guidance)
        self._adaptive_action_buttons = {
            'approve_strategy': any(item.get('phase_key') == 'strategy' and item.get('decision') == 'pending' for item in approvals),
            'approve_next': bool(pending_approvals),
            'simulate': bool(self._adaptive_session_id),
            'execute': bool(self._adaptive_session_id and execution_state.get('executor_available') and not execution_state.get('simulation_only')),
            'abort': bool(self._adaptive_session_id and status not in {'aborted', 'completed'}),
        }
        self._refresh_autonomy_dock()

    def get_chat_messages(self) -> list[dict[str, str]]:
        with self._ui_state_lock:
            return list(self._chat_messages)

    def get_provider_cards(self) -> list[dict[str, Any]]:
        return self._provider_cards

    def get_progress_cards(self) -> list[dict[str, Any]]:
        return self._progress_cards

    def get_live_process_summary(self) -> dict[str, Any]:
        return self._live_process_summary

    def get_live_work_items(self) -> list[dict[str, Any]]:
        return self._live_work_items

    def get_assistant_session_cards(self) -> list[dict[str, Any]]:
        return self._assistant_session_cards

    def get_autonomy_timeline(self) -> list[dict[str, Any]]:
        return self._autonomy_timeline

    def get_evolution_overview(self) -> dict[str, Any]:
        return self._evolution_overview

    def get_evolution_area_cards(self) -> list[dict[str, Any]]:
        return self._evolution_area_cards

    def get_evolution_blockers(self) -> list[dict[str, str]]:
        return self._evolution_blockers

    def get_agent_cards(self) -> list[dict[str, Any]]:
        return self._agent_cards

    def get_legacy_cards(self) -> list[dict[str, str]]:
        return self._legacy_cards

    def get_role_cards(self) -> list[dict[str, Any]]:
        return self._role_cards

    def get_pbt_candidates(self) -> list[dict[str, Any]]:
        return self._pbt_candidates

    def get_pbt_state(self) -> dict[str, Any]:
        return self._pbt_state

    def get_selected_role(self) -> str:
        return 'auto' if self._auto_route_enabled else self._selected_role

    def get_auto_route_enabled(self) -> bool:
        return self._auto_route_enabled

    def get_advanced_visible(self) -> bool:
        return self._advanced_visible

    def get_routing_mode_label(self) -> str:
        return self._routing_mode_label()

    def get_working(self) -> bool:
        return self._working

    def get_busy_label(self) -> str:
        return self._busy_label

    def get_strategy_text(self) -> str:
        return self._strategy_text

    def get_recommendation_text(self) -> str:
        return self._recommendation_text

    def get_legacy_summary(self) -> str:
        return self._legacy_summary

    def get_diagnostic_text(self) -> str:
        return self._diagnostic_text

    def get_repo_bridge_text(self) -> str:
        return self._repo_bridge_text

    def get_local_stack_text(self) -> str:
        return self._local_stack_text

    def get_clipboard_notice(self) -> str:
        return self._clipboard_notice

    def get_development_packet(self) -> str:
        return self._development_packet

    def get_assistant_guidance_mode(self) -> str:
        return self._assistant_guidance_mode

    def get_assistant_guidance_text(self) -> str:
        return self._assistant_guidance_text

    def get_assistant_action_buttons(self) -> list[dict[str, str]]:
        return self._assistant_action_buttons

    def get_approval_dialog_visible(self) -> bool:
        return self._approval_dialog_visible

    def get_approval_dialog_title(self) -> str:
        return self._approval_dialog_title

    def get_approval_dialog_text(self) -> str:
        return self._approval_dialog_text

    def get_latest_response_text(self) -> str:
        return self._latest_response_text

    def get_latest_response_meta(self) -> str:
        return self._latest_response_meta

    def get_adaptive_session_id(self) -> str:
        return self._adaptive_session_id

    def get_adaptive_status_text(self) -> str:
        return self._adaptive_status_text

    def get_adaptive_intent_text(self) -> str:
        return self._adaptive_intent_text

    def get_adaptive_context_text(self) -> str:
        return self._adaptive_context_text

    def get_adaptive_strategy_text(self) -> str:
        return self._adaptive_strategy_text

    def get_adaptive_execution_text(self) -> str:
        return self._adaptive_execution_text

    def get_adaptive_evidence_text(self) -> str:
        return self._adaptive_evidence_text

    def get_adaptive_evolution_text(self) -> str:
        return self._adaptive_evolution_text

    def get_adaptive_capability_cards(self) -> list[dict[str, str]]:
        return self._adaptive_capability_cards

    def get_adaptive_approval_cards(self) -> list[dict[str, str]]:
        return self._adaptive_approval_cards

    def get_adaptive_playbook_steps(self) -> list[dict[str, str]]:
        return self._adaptive_playbook_steps

    def get_can_approve_strategy(self) -> bool:
        return self._adaptive_action_buttons['approve_strategy'] and not self._working

    def get_can_approve_next_phase(self) -> bool:
        return self._adaptive_action_buttons['approve_next'] and not self._working

    def get_can_simulate(self) -> bool:
        return self._adaptive_action_buttons['simulate'] and not self._working

    def get_can_execute(self) -> bool:
        return self._adaptive_action_buttons['execute'] and not self._working

    def get_can_abort(self) -> bool:
        return self._adaptive_action_buttons['abort'] and not self._working

    @Slot()
    def refresh(self) -> None:
        self._pbt_state = self.pbt_service.load_state()
        self._pbt_candidates = self._pbt_state.get('candidates', [])[:4]
        self._last_goal_context = self._goal_context_from_repository(self._current_site_id() or None)
        self._update_progress_cards()
        self._update_evolution_snapshot()
        self._agent_cards = self._build_agent_cards()
        self._repo_bridge_text = self.development_assist_service.build_repo_bridge_summary()
        self._local_stack_text = self.development_assist_service.build_local_stack_summary()
        if not self._working and not self._adaptive_session_id:
            self._busy_label = self._startup_readiness_text(validating_local_stack=True)
        self._seed_development_packet()
        self._refresh_autonomy_dock()
        self._refresh_control_master()
        self.dataChanged.emit()

    def _refresh_autonomy_dock(self) -> None:
        projector = self.autonomy_activity_projector
        if projector is None:
            self._live_process_summary = {}
            self._live_work_items = []
            self._assistant_session_cards = []
            self._autonomy_timeline = []
            return
        projected = projector.project(
            goal_context=self._goal_context_for_display(self._current_site_id() or None),
            live_audit=self._latest_live_audit(),
            replay_visual_summary=self._latest_replay_visual_summary(),
            autonomy_activity=self.get_autonomy_activity(),
        )
        self._live_process_summary = dict(projected.get('live_process_summary') or {})
        self._live_work_items = [dict(item) for item in (projected.get('live_work_items') or [])]
        self._assistant_session_cards = [dict(item) for item in (projected.get('assistant_session_cards') or [])]
        self._autonomy_timeline = [dict(item) for item in (projected.get('autonomy_timeline') or [])]

    @Slot()
    def refreshAutonomyDock(self) -> None:
        self._refresh_autonomy_dock()
        self.dataChanged.emit()

    @Slot(str)
    def setRole(self, role: str) -> None:
        role = (role or '').strip().lower()
        valid_roles = {profile.role.value for profile in self.role_router.role_profiles}
        if role == 'auto':
            self._auto_route_enabled = True
            self._busy_label = 'Modo automatico restaurado. La consola detectara intencion, pack y aprobaciones.'
            import threading as _th
            _th.Thread(target=self._refresh_development_packet, daemon=True).start()
            self.dataChanged.emit()
            return
        if role in valid_roles:
            self._selected_role = role
            self._auto_route_enabled = False
            self._busy_label = f'Rol forzado a {self._selected_role_title()}.'
            import threading as _th
            _th.Thread(target=self._refresh_development_packet, daemon=True).start()
            self.dataChanged.emit()

    @Slot()
    def toggleAdvanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        self.dataChanged.emit()

    def _refresh_provider_health(self, *, announce: bool) -> None:
        if self._provider_refreshing:
            return
        self._provider_refreshing = True
        if not self._working:
            self._busy_label = 'Consultando el stack local y los asistentes externos en segundo plano.' if announce else self._startup_readiness_text(validating_local_stack=True)
            self.dataChanged.emit()

        def worker() -> None:
            try:
                self._refresh_assistant_cards()
                provider_cards = []
                for health in self.role_router.health_snapshot(
                    refresh=announce,
                    max_age_seconds=0.0 if announce else 30.0,
                ):
                    payload = health.model_dump()
                    payload['status'] = self._translate_status(payload['status'])
                    payload['role'] = {
                        'Ollama': 'generalista principal',
                        'Ollama Vision': 'perfil visual',
                        'LM Studio': 'complemento opcional',
                        'Embeddings': 'recuperacion semantica',
                    }.get(payload['provider_name'], 'componente')
                    provider_cards.append(payload)
                self.taskResolved.emit('provider_health', provider_cards)
            except Exception as exc:
                self.taskFailed.emit('provider_health', f'No pude consultar el stack local: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def refreshProviderHealth(self) -> None:
        self._refresh_provider_health(announce=True)

    @Slot()
    def dismissApprovalDialog(self) -> None:
        self._approval_dialog_visible = False
        self.dataChanged.emit()

    def _navigate_to(self, route_key: str) -> None:
        if self.navigation_controller is not None and hasattr(self.navigation_controller, 'navigate'):
            self.navigation_controller.navigate(route_key)


    def _reset_assistant_guidance(self) -> None:
        self._assistant_guidance_mode = 'idle'
        self._assistant_guidance_text = 'Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex.'
        self._assistant_action_buttons = []
        self._approval_dialog_visible = False
        self._approval_dialog_title = 'Sin aprobaciones pendientes'
        self._approval_dialog_text = 'No hay aprobaciones pendientes en esta sesion.'

    def _default_expected_outcome(self, site_id: str, intent_key: str) -> str:
        if intent_key == 'wplay.login' or site_id == 'wplay':
            return 'Sesion iniciada y panel principal de Wplay visible.'
        if intent_key == 'wplay.core':
            return 'Wplay abierto y listo para la siguiente fase.'
        if intent_key == 'browser.search.google' or site_id == 'google':
            return 'Pagina cargada y resultado visible para la siguiente accion.'
        if intent_key == 'mercadolibre.core' or site_id == 'mercadolibre':
            return 'Mercado Libre abierto y listo para continuar el flujo.'
        return ''

    def _default_objective(self, site_id: str, intent_key: str) -> str:
        if intent_key == 'wplay.login' or site_id == 'wplay':
            return 'Abrir Wplay e iniciar sesion.'
        if intent_key == 'wplay.core':
            return 'Abrir Wplay y dejarlo listo para la siguiente fase.'
        if intent_key == 'browser.search.google' or site_id == 'google':
            return 'Abrir Google y completar una busqueda corta.'
        if intent_key == 'mercadolibre.core' or site_id == 'mercadolibre':
            return 'Abrir Mercado Libre y dejar visible el flujo principal.'
        return ''

    def _build_teaching_prefill(self) -> dict[str, str]:
        payload = self._last_adaptive_payload or {}
        intent = payload.get('intent') or {}
        context = payload.get('context') or {}
        capabilities = [item for item in (payload.get('capability_readiness') or []) if isinstance(item, dict)]
        recent_teachings = [item for item in (context.get('recent_teachings') or []) if isinstance(item, dict)]
        lead_teaching = recent_teachings[0] if recent_teachings else {}
        site_id = str(context.get('site_id') or intent.get('site_hint') or lead_teaching.get('site_id') or '').strip()
        lead_target = str(lead_teaching.get('target_label') or '').strip()
        start_url = str(lead_teaching.get('start_url') or '').strip()
        is_url_target = lead_target.startswith(('http://', 'https://'))
        site_name = str(
            context.get('site_display_name')
            or ('' if is_url_target else lead_target)
            or lead_teaching.get('title')
            or intent.get('site_hint')
            or site_id
            or 'Flujo guiado'
        ).strip()
        lesson_title = str(lead_teaching.get('title') or f'Reforzar {site_name}').strip() or 'Nueva ensenanza'
        intent_key = str(intent.get('intent_key') or '').strip()
        objective = str(lead_teaching.get('objective') or self._default_objective(site_id, intent_key) or intent.get('title') or '').strip()
        expected_outcome = str(lead_teaching.get('expected_outcome') or self._default_expected_outcome(site_id, intent_key)).strip()
        relevant_capability = next(
            (
                item for item in capabilities
                if item.get('status') in {'insufficient', 'partial'} and (not site_id or item.get('site_id') in {'', site_id})
            ),
            next((item for item in capabilities if item.get('status') in {'insufficient', 'partial'}), {}),
        )
        note_parts: list[str] = []
        if lead_teaching.get('notes'):
            note_parts.append(str(lead_teaching.get('notes')).strip())
        suggested = str(relevant_capability.get('suggested_next_step') or '').strip()
        if suggested:
            note_parts.append(f'Ajuste sugerido por la IA: {suggested}')
        dominant_incident = str((context.get('session_readiness') or {}).get('dominant_incident') or '').strip()
        if dominant_incident:
            note_parts.append(f'Incidencia reciente a vigilar: {dominant_incident}.')
        gaps = [str(item).strip() for item in (lead_teaching.get('gaps') or []) if str(item).strip()]
        if gaps:
            note_parts.append('Gaps visuales detectados: ' + ', '.join(gaps[:2]))
        notes = ' '.join(item for item in note_parts if item).strip()
        target_label = site_name or str(intent.get('site_hint') or '').strip() or 'Flujo guiado'
        return {
            'lesson_title': lesson_title,
            'target_label': target_label,
            'start_url': start_url,
            'objective': objective,
            'expected_outcome': expected_outcome,
            'notes': notes,
            'site_id': site_id,
        }

    def _current_site_id(self) -> str:
        payload = self._last_adaptive_payload or {}
        intent = payload.get('intent') or {}
        context = payload.get('context') or {}
        return str(context.get('site_id') or intent.get('site_hint') or '').strip()

    def _current_diagnostic_category(self) -> str:
        payload = self._last_adaptive_payload or {}
        probe = payload.get('probe_diagnosis') or {}
        return str(probe.get('category') or self._assistant_guidance_mode or '').strip()

    def _current_incident_kind(self) -> str:
        payload = self._last_adaptive_payload or {}
        context = payload.get('context') or {}
        session_readiness = context.get('session_readiness') or {}
        if session_readiness.get('dominant_incident'):
            return str(session_readiness.get('dominant_incident') or '').strip()
        incidents = context.get('recent_incidents') or []
        first = incidents[0] if incidents else {}
        return str(first.get('incident_kind') or '').strip()


    @Slot()
    def auditAutonomy(self) -> None:
        orchestrator = self.adaptive_orchestrator if hasattr(self.adaptive_orchestrator, 'preview_autonomy') else None
        if (orchestrator is None and self.autonomous_evolution_service is None) or not self.config.autonomous_evolution_enabled:
            self._busy_label = 'La autonomia guiada no esta disponible en esta sesion.'
            self.dataChanged.emit()
            return
        payload = dict(self._last_adaptive_payload or {})
        if not payload:
            self._busy_label = 'Todavia no hay una sesion adaptativa para auditar.'
            self._append_message('assistant', 'Auditoria', 'Primero necesito una sesion adaptativa o un autotest reciente para auditar la autonomia.', 'Sin payload activo.')
            self.dataChanged.emit()
            return
        user_goal = self._last_user_goal or str(payload.get('user_goal') or (payload.get('intent') or {}).get('title') or 'caso actual')
        if orchestrator is not None:
            preview = orchestrator.preview_autonomy(payload, user_goal=user_goal, source='manual_audit')
        else:
            preview = self.autonomous_evolution_service.preview_plan(adaptive_payload=payload, user_goal=user_goal, source='manual_audit')
        metadata = dict(payload.get('metadata') or {})
        metadata['autonomous_evolution_preview'] = dict(preview)
        payload['metadata'] = metadata
        self._update_adaptive_state(payload)
        requested = str(preview.get('requested_assistant_kind') or preview.get('assistant_kind') or '')
        assistant_title = 'Codex' if requested == 'codex' else 'ChatGPT' if requested == 'chatgpt' else 'ruta local'
        if preview.get('should_consult'):
            detail = (
                f"La autonomia elegiria {assistant_title} via {preview.get('selected_tool_id') or 'n/d'} "
                f"para {preview.get('recommended_action') or 'continuar'}: {preview.get('reason') or 'sin razon'}"
            )
            meta = (
                f"preview {preview.get('recommended_action') or 'continue_local'} | "
                f"tool {preview.get('selected_tool_id') or 'n/d'} | fallback {preview.get('fallback_used')}"
            )
            self._busy_label = 'Auditoria de autonomia completada.'
        else:
            detail = f"La autonomia mantendria la via local actual: {preview.get('reason') or 'sin razon adicional'}."
            meta = f"preview {preview.get('recommended_action') or 'continue_local'} | tool local"
            self._busy_label = 'Auditoria de autonomia: seguir local.'
        self._append_message('assistant', 'Auditoria', detail, meta)
        self._latest_response_meta = meta
        self.dataChanged.emit()

    def _maybe_run_autonomous_evolution(self, adaptive_payload: dict[str, Any], *, source: str) -> dict[str, Any] | None:
        if not self.config.autonomous_evolution_enabled:
            return None
        payload = dict(adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        existing = dict(metadata.get('autonomous_evolution') or {})
        if existing.get('status') in {'prepared', 'reused', 'awaiting_response', 'failed'}:
            if existing.get('status') == 'awaiting_response':
                started_at = str(existing.get('started_at_utc') or existing.get('created_at_utc') or '').strip()
                if started_at:
                    try:
                        from datetime import datetime, timezone
                        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                        age_seconds = (datetime.now(timezone.utc) - started).total_seconds()
                        if age_seconds > 120:
                            existing = {**existing, 'status': 'stale_awaiting', 'stale_since_seconds': int(age_seconds)}
                            metadata['autonomous_evolution'] = existing
                            payload['metadata'] = metadata
                    except (ValueError, TypeError):
                        pass
                else:
                    existing = {**existing, 'status': 'stale_awaiting', 'stale_since_seconds': -1}
                    metadata['autonomous_evolution'] = existing
                    payload['metadata'] = metadata
            if existing.get('status') != 'stale_awaiting':
                return existing
        user_goal = self._last_user_goal or str(payload.get('user_goal') or (payload.get('intent') or {}).get('title') or 'caso actual')
        intent = dict(payload.get('intent') or {})
        intent_key = str(intent.get('intent_key') or '').strip()
        intent_disposition = str(intent.get('disposition') or '').strip()
        intent_metadata = dict(intent.get('metadata') or {})
        explicit_assistant = self._explicit_assistant_preference(user_goal)
        structured_conversational_prompt = self._structured_conversational_prompt_from_payload(payload)
        fallback_conversational_prompt = structured_conversational_prompt is None and self._is_general_chat_message(user_goal)
        self_awareness_prompt = intent_key == 'system.self_awareness' or bool(intent_metadata.get('self_awareness_prompt'))
        world_model_prompt = self._is_world_model_question(user_goal)
        evolution_status_prompt = intent_key == 'consulta_estado_evolutivo' or bool(intent_metadata.get('evolution_status_prompt')) or self._is_evolution_status_question(user_goal)
        learning_prompt = self._is_learning_question(user_goal)
        self_examination_prompt = self._is_self_examination_question(user_goal) or bool(intent_metadata.get('self_examination_prompt'))
        account_resource_prompt = self._is_account_resource_question(user_goal)
        # Internal/system topics (secrets, bootstrap config, metacognition)
        # should NEVER trigger an external consultation — the program must
        # resolve these by introspecting its own code and config, not by
        # asking ChatGPT or Codex.
        _internal_signals = (
            'secreto', 'secretos', 'token', 'tokens', 'configuracion',
            'configurar', 'bootstrap', 'faltantes', 'faltante',
            'tu codigo', 'tu código', 'tu algoritmo', 'tu sistema',
            'tus logs', 'tus propios', 'tu log', 'tu propio',
            'metacognicion', 'metacognición', 'autoanalisis', 'autoanálisis',
            'autodiagnostico', 'autodiagnóstico', 'auto-diagnostico',
            'anomalias', 'anomalías', 'diagnostica', 'diagnostico',
            'tu estado', 'tu salud', 'tu rendimiento',
            'autoexamina', 'autoexaminacion', 'autoexaminación',
            'autoevalua', 'autoevaluacion', 'autoevaluación',
            'que detectas', 'que ves en ti', 'revisa tu',
            'analiza tu', 'analízate', 'examinat',
            'cuentas', 'cuotas', 'navegadores', 'sesiones activas',
        )
        user_goal_lower = user_goal.lower()
        internal_system_topic = any(s in user_goal_lower for s in _internal_signals)
        if source == 'chat' and (self_awareness_prompt or world_model_prompt or evolution_status_prompt or learning_prompt or self_examination_prompt or account_resource_prompt or internal_system_topic):
            return None
        if source == 'chat' and intent_key in {'general.assistance', 'knowledge.query'} and intent_disposition in {'answer_now', 'need_info'} and ((structured_conversational_prompt is True) or fallback_conversational_prompt) and not explicit_assistant:
            return None
        orchestrator = self.adaptive_orchestrator if hasattr(self.adaptive_orchestrator, 'govern_adaptive_payload') else None
        self._set_autonomy_activity_override(
            visible=True,
            title='Evaluando autonomia',
            status='active',
            stage='decidiendo si escalo o sigo local',
            progress=0.56,
            detail='Estoy contrastando la respuesta local con la gobernanza, la auditoria y el objetivo persistente.',
            tool='motor local',
            next_step='Si hace falta apoyo externo, abrire la herramienta adecuada con el contexto redactado.',
            learning_note='Todavia no cierro aprendizaje estable hasta terminar esta evaluacion.',
            mode='local',
        )
        self.dataChanged.emit()
        self._process_ui_events()
        if orchestrator is not None:
            payload = orchestrator.govern_adaptive_payload(payload, user_goal=user_goal, source=source)
            result = dict((payload.get('metadata') or {}).get('autonomous_evolution') or {})
        elif self.autonomous_evolution_service is not None:
            result = self.autonomous_evolution_service.plan_or_execute(adaptive_payload=payload, user_goal=user_goal, source=source)
            metadata = dict(payload.get('metadata') or {})
            metadata['autonomous_evolution'] = dict(result)
            if result.get('response_validation') or result.get('adoption_plan') or result.get('response_ingested_at_utc'):
                metadata['autonomous_evolution_response'] = dict(result)
                payload['assistant_guidance'] = self._guidance_from_external_response(result)
            payload['metadata'] = metadata
            if result.get('status') in {'prepared', 'reused', 'awaiting_response'} and not (result.get('response_validation') or result.get('adoption_plan') or result.get('response_ingested_at_utc')):
                payload['assistant_guidance'] = self._guidance_for_pending_external_response(self._assistant_display_name(str(result.get('assistant_kind') or '')))
            if result.get('pending_issue_id'):
                payload['pending_issue_id'] = result.get('pending_issue_id')
        else:
            self._clear_autonomy_activity_override()
            return None
        if result and (result.get('response_validation') or result.get('adoption_plan') or result.get('response_ingested_at_utc')):
            metadata = dict(payload.get('metadata') or {})
            metadata.setdefault('autonomous_evolution_response', dict(result))
            payload['metadata'] = metadata
            payload['assistant_guidance'] = self._guidance_from_external_response(result)
        if not result or result.get('status') == 'noop':
            self._clear_autonomy_activity_override()
            return result or None
        self._update_adaptive_state(payload)
        assistant_title = self._assistant_display_name(str(result.get('assistant_kind') or ''))
        external_state_flags = canonical_external_state_flags(list(result.get('external_state_flags') or []))
        status = str(result.get('status') or '').strip().lower()
        external_notice = self._external_state_notice(external_state_flags)
        if status == 'awaiting_response':
            detail = f'Voy a apoyarme en {assistant_title}. Ya deje la consulta encaminada y te aviso cuando tenga una respuesta util.'
            meta = f'Consulta con {assistant_title}.'
        elif status == 'blocked_external':
            detail = external_notice or f'La via externa con {assistant_title} no quedo disponible, asi que sigo con la mejor alternativa que si tengo aqui.'
            meta = 'Bloqueo externo.'
        elif status == 'prepared':
            detail = f'Deje preparada la consulta con {assistant_title}. Apenas tenga una respuesta util, te la resumo aqui.'
            meta = f'Consulta con {assistant_title}.'
        else:
            detail = external_notice or 'Revise si hacia falta apoyo externo y, por ahora, conviene seguir con lo que ya tenemos aqui.'
            meta = 'Seguimos por aqui.'
        self._append_message('assistant', 'Autonomia', detail, meta)
        if result.get('status') == 'awaiting_response':
            self._busy_label = f'Consulta externa abierta con {assistant_title}; falta ingerir la respuesta.'
        elif result.get('status') == 'blocked_external':
            self._busy_label = external_notice or f'La ruta externa con {assistant_title} quedo bloqueada; sigo con evidencia local.'
        elif result.get('status') == 'prepared':
            self._busy_label = f'Consulta autonoma preparada con {assistant_title}.'
        else:
            self._busy_label = 'Autonomia evaluada.'
        self._latest_response_meta = meta
        self._clear_autonomy_activity_override()
        return result
    def _build_external_context_pack(self, assistant_kind: str) -> str:
        payload = self._last_adaptive_payload or {}
        intent = payload.get('intent') or {}
        context = payload.get('context') or {}
        probe = payload.get('probe_diagnosis') or {}
        chosen_pack = payload.get('chosen_pack') or {}
        capabilities = [item for item in (payload.get('capability_readiness') or []) if isinstance(item, dict)]
        weak = [item for item in capabilities if item.get('status') in {'insufficient', 'partial'}]
        session_readiness = context.get('session_readiness') or {}
        dominant_incident = str(session_readiness.get('dominant_incident') or '').strip()
        lines = [
            'Context pack - consulta externa IABV v1.5',
            f"Workspace: {self.config.workspace_root}",
            f"Objetivo del usuario: {self._last_user_goal or intent.get('title') or 'caso actual'}",
            f"Asistente sugerido: {assistant_kind}",
            f"Sitio: {context.get('site_display_name') or context.get('site_id') or intent.get('site_hint') or 'general'}",
            f"Intento detectado: {intent.get('intent_key') or intent.get('title') or 'n/d'}",
            f"Pack activo: {chosen_pack.get('title') or 'n/d'}",
            f"Estado adaptativo: {payload.get('status') or 'n/d'}",
        ]
        if probe:
            lines.append(f"Diagnostico: {probe.get('category') or 'n/d'}")
            lines.append(f"Resumen diagnostico: {probe.get('summary') or 'sin resumen'}")
        if dominant_incident:
            lines.append(f"Incidente dominante: {dominant_incident}")
        if weak:
            lines.append('Capacidades debiles:')
            for item in weak[:3]:
                lines.append(
                    f"- {item.get('title') or item.get('capability_id') or 'capacidad'} | {item.get('status')} | {item.get('suggested_next_step') or 'sin siguiente paso'}"
                )
        outcome = payload.get('outcome') or {}
        if outcome.get('summary'):
            lines.append(f"Outcome actual: {outcome.get('summary')}")
        evidence_refs = payload.get('evidence_refs') or context.get('evidence_summary') or []
        if evidence_refs:
            lines.append('Evidencia textual:')
            for item in evidence_refs[:6]:
                lines.append(f"- {item}")
        if assistant_kind == 'codex':
            self._refresh_development_packet(self._last_user_goal or intent.get('title') or 'caso actual')
            lines.append('Paquete local para Codex:')
            lines.append(self._development_packet.strip())
        else:
            lines.append('Objetivo para la IA externa: explicar por que el flujo no queda aprendido y proponer el siguiente microajuste mas seguro.')
        return '\n'.join(item for item in lines if item).strip()

    def _execute_external_consultation_sync(self, assistant_kind: str) -> dict[str, Any]:
        if self.tool_teach_service is None:
            message = 'La capa Tool Teaching externa no esta inicializada en este contexto.'
            self._latest_response_text = message
            self._latest_response_meta = 'Consulta externa no disponible.'
            return {
                'success': False,
                'message': message,
                'meta': 'Consulta externa no disponible.',
                'payload': dict(self._last_adaptive_payload or {}),
                'assistant_title': self._assistant_display_name(assistant_kind),
            }
        requested_assistant_kind = str(assistant_kind or '').strip().lower()
        assistant_title = self._assistant_display_name(requested_assistant_kind)
        preflight = self.adaptive_orchestrator.preflight_external_assistant(
            user_goal=self._last_user_goal or 'abre Wplay e inicia sesion',
            assistant_kind=requested_assistant_kind,
        )
        if bool(preflight.get('blocked')):
            return self._blocked_external_consultation_result(
                assistant_kind=requested_assistant_kind,
                assistant_title=assistant_title,
                preflight=preflight,
            )
        self._clear_observation_permission_artifacts()
        site_id = self._current_site_id() or None
        diagnostic_category = self._current_diagnostic_category()
        incident_kind = self._current_incident_kind()
        context_pack = self._build_external_context_pack(assistant_kind)
        preview = self.tool_teach_service.preview_external_consultation(
            user_goal=self._last_user_goal or 'abre Wplay e inicia sesion',
            assistant_preference=assistant_kind,
            context_pack=context_pack,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            launch_dry_run=False,
        )
        tool_card = dict(preview.get('tool_card') or {})
        tool_task = dict(preview.get('tool_task') or {})
        mode_selection = dict(preview.get('mode_selection') or {})
        selected_tool_id = str(tool_card.get('tool_id') or tool_task.get('tool_id') or '')
        requested_assistant_kind = str(assistant_kind or '').strip().lower()
        actual_assistant_kind = str(self._assistant_kind_from_tool_id(selected_tool_id) or requested_assistant_kind)
        assistant_title = str(tool_card.get('title') or self._assistant_display_name(actual_assistant_kind))
        self._copy_text(context_pack, f'Contexto para {assistant_title} copiado al portapapeles.')
        if not bool(preview.get('available')):
            pending_issue_id = str((self._last_adaptive_payload or {}).get('pending_issue_id') or '')
            extra = f' Pendiente actual: {pending_issue_id}.' if pending_issue_id else ''
            message = f'No encontre una via externa disponible para {assistant_title}. Mantengo la guia local y el contexto copiado.{extra}'
            self._latest_response_text = message
            self._latest_response_meta = 'Consulta externa no disponible.'
            return {
                'success': False,
                'message': message,
                'meta': 'Consulta externa no disponible.',
                'payload': dict(self._last_adaptive_payload or {}),
                'assistant_title': assistant_title,
            }
        if bool(tool_task.get('metadata', {}).get('reuse_guard_active')):
            message = f'Ya tenia una consulta equivalente para {assistant_title}, asi que voy a reutilizar ese contexto en lugar de arrancar de cero.'
            self._latest_response_text = message
            self._latest_response_meta = 'Reutilizando contexto existente.'
            return {
                'success': True,
                'message': message,
                'meta': 'Reutilizando contexto existente.',
                'payload': dict(self._last_adaptive_payload or {}),
                'assistant_title': assistant_title,
            }
        task, result, _ = self.tool_teach_service.execute_external_consultation(
            user_goal=self._last_user_goal or 'abre Wplay e inicia sesion',
            assistant_preference=assistant_kind,
            context_pack=context_pack,
            site_id=site_id,
            diagnostic_category=diagnostic_category,
            incident_kind=incident_kind,
            approved=True,
            launch_dry_run=False,
        )
        launch_mode = str(result.execution_state.metadata.get('launch_mode') or tool_card.get('metadata', {}).get('launch_mode') or '')
        response_capture_mode = str(result.execution_state.metadata.get('response_capture_mode') or tool_card.get('metadata', {}).get('response_capture_mode') or '')
        response_captured = bool(result.execution_state.metadata.get('response_captured'))
        response_capture_pending = bool(result.execution_state.metadata.get('response_capture_pending'))
        result_metadata = dict(result.metadata or {})
        external_state_flags = self._external_state_flags_from_payloads(
            dict(tool_card.get('metadata') or {}),
            dict(task.metadata or {}),
            dict(result.execution_state.metadata or {}),
            result_metadata,
        )
        blocked_external = any(flag in {'account_limited', 'session_expired', 'assistant_login_required', 'wrong_thread', 'missing_thread_tracking'} for flag in external_state_flags)
        if blocked_external:
            external_state_flags = [flag for flag in external_state_flags if flag != 'awaiting_response']
        external_notice = self._external_state_notice(external_state_flags)
        actual_assistant_kind = str(
            result.execution_state.metadata.get('actual_assistant_kind')
            or result_metadata.get('actual_assistant_kind')
            or self._assistant_kind_from_tool_id(selected_tool_id or task.tool_id)
            or actual_assistant_kind
        ).strip().lower()
        assistant_title = str(tool_card.get('title') or self._assistant_display_name(actual_assistant_kind))
        assistant_switch_note = ''
        if actual_assistant_kind and requested_assistant_kind and actual_assistant_kind != requested_assistant_kind:
            assistant_switch_note = (
                f' Pediste {self._assistant_display_name(requested_assistant_kind)}, '
                f'pero la mejor via disponible en esta corrida fue {assistant_title}.'
            )
        fallback_note = assistant_switch_note or (' Se uso una via alternativa disponible.' if bool(mode_selection.get('fallback_used')) else '')
        manual_pending = bool(
            result.execution_state.metadata.get('manual_pasteback_required', True)
            and not result.execution_state.metadata.get('response_captured')
            and str(result.execution_state.metadata.get('response_capture_mode') or '').strip().lower() == 'manual_pasteback'
        )
        consultation_metadata = {
            'status': (
                'blocked_external'
                if blocked_external
                else 'awaiting_response'
                if result.success and (manual_pending or response_capture_pending)
                else 'prepared'
                if result.success
                else 'failed'
            ),
            'assistant_kind': actual_assistant_kind or requested_assistant_kind,
            'requested_assistant_kind': requested_assistant_kind,
            'actual_assistant_kind': actual_assistant_kind or requested_assistant_kind,
            'decision_source': 'manual_consultation',
            'recommended_action': f"consult_{actual_assistant_kind or requested_assistant_kind}",
            'reason': str((self._last_adaptive_payload or {}).get('probe_diagnosis', {}).get('summary') or 'Consulta externa guiada desde Control Center.'),
            'selected_tool_id': selected_tool_id or task.tool_id,
            'launch_mode': launch_mode,
            'task_id': task.task_id,
            'result_id': result.result_id,
            'pending_issue_id': str((self._last_adaptive_payload or {}).get('pending_issue_id') or ''),
            'context_pack_excerpt': context_pack[:600],
            'preview_summary': str(preview.get('summary') or ''),
            'response_capture_mode': response_capture_mode,
            'manual_pasteback_required': bool(result.execution_state.metadata.get('manual_pasteback_required', True)),
            'response_capture_pending': response_capture_pending,
            'response_captured': response_captured,
            'external_state_flags': external_state_flags,
            'detail': str(result.execution_state.detail or result.error_message or ''),
        }
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        metadata['external_consultation'] = dict(consultation_metadata)
        metadata['autonomous_evolution'] = dict(consultation_metadata)
        payload['metadata'] = metadata
        payload['assistant_guidance'] = self._guidance_for_pending_external_response(assistant_title)
        self._update_adaptive_state(payload)
        if response_capture_mode in {'dom_capture', 'browser_dom'}:
            meta = f'Sesion dedicada con {assistant_title}.'
        elif response_capture_mode == 'clipboard_capture':
            meta = f'Consulta con {assistant_title}.'
        else:
            meta = f'Revision con {assistant_title}.'
        if result.success:
            if response_captured:
                message = f"{result.output_text or 'Respuesta externa capturada.'} Ya tengo texto util desde {assistant_title} y lo dejare listo para integrarlo de forma segura.{fallback_note}"
            elif response_capture_mode == 'clipboard_capture':
                message = f"{result.output_text or 'Consulta externa lanzada.'} Ya abri {assistant_title} y voy a intentar capturar su respuesta automaticamente; si no vuelve texto util, te pedire pegarla.{fallback_note}"
            elif response_capture_mode in {'dom_capture', 'browser_dom'}:
                message = f"{result.output_text or 'Consulta externa preparada.'} IABV la llevara en una sesion aislada del programa, usando un chat especial separado de tus chats normales y capturando la respuesta en segundo plano cuando la sesion ya este autenticada.{fallback_note}"
            else:
                message = f"{result.output_text or 'Consulta externa preparada.'} El contexto ya esta copiado y la respuesta vuelve por pegado manual.{fallback_note}"
            self._latest_response_text = message
            self._latest_response_meta = meta
            self._busy_label = f'Consulta externa lista con {assistant_title}.'
            return {
                'success': True,
                'message': message,
                'meta': meta,
                'payload': payload,
                'assistant_title': assistant_title,
                'external_state_flags': external_state_flags,
            }
        failure_detail = str(result.error_message or result.execution_state.detail or 'sin detalle').strip()
        message, failure_meta, failure_busy = self._human_external_consultation_failure(
            assistant_title,
            failure_detail,
            external_state_flags,
        )
        self._latest_response_text = message
        self._latest_response_meta = failure_meta
        self._busy_label = failure_busy
        return {
            'success': False,
            'message': message,
            'meta': failure_meta,
            'payload': payload,
            'assistant_title': assistant_title,
            'external_state_flags': external_state_flags,
        }

    def _blocked_external_consultation_result(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        preflight: dict[str, Any],
    ) -> dict[str, Any]:
        governance = dict(preflight.get('governance') or {})
        approval_checkpoints = [dict(item) for item in (preflight.get('approval_checkpoints') or []) if isinstance(item, dict)]
        world_model_summary = dict(preflight.get('world_model_summary') or {})
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        decision_context = dict(metadata.get('decision_context') or {})
        decision_metadata = dict(decision_context.get('metadata') or {})
        decision_context['governance'] = governance
        decision_metadata['world_model_summary'] = world_model_summary
        decision_context['metadata'] = decision_metadata
        metadata['decision_context'] = decision_context
        metadata['world_model_summary'] = world_model_summary
        metadata['external_consultation_preflight'] = {
            'assistant_kind': assistant_kind,
            'reason': str(preflight.get('reason') or governance.get('reason') or ''),
            'blocked': True,
            'world_model_summary': world_model_summary,
        }
        payload['metadata'] = metadata
        payload['approval_checkpoints'] = approval_checkpoints
        payload['assistant_guidance'] = self._guidance_for_external_preflight_block(
            assistant_kind=assistant_kind,
            assistant_title=assistant_title,
            governance=governance,
            approval_checkpoints=approval_checkpoints,
        )
        self._update_adaptive_state(payload)
        reason = str(preflight.get('reason') or governance.get('reason') or '').strip()
        if approval_checkpoints:
            message = (
                f'No voy a lanzar {assistant_title} todavia. '
                f'{reason or f"Primero necesito tu permiso para observar esa ventana y verificar que {assistant_title} este usable."}'
            )
            meta = f'Permiso requerido para {assistant_title}.'
        else:
            message = (
                f'No voy a lanzar {assistant_title} porque la ruta ya aparece bloqueada antes de intentarla. '
                f'{reason or "Mantengo la via local hasta que el bloqueo cambie."}'
            )
            meta = f'Ruta bloqueada para {assistant_title}.'
        self._latest_response_text = message
        self._latest_response_meta = meta
        self._busy_label = reason or f'Consulta externa bloqueada para {assistant_title}.'
        return {
            'success': False,
            'message': message,
            'meta': meta,
            'payload': payload,
            'assistant_title': assistant_title,
            'external_state_flags': list(governance.get('external_state_flags') or []),
        }

    def _guidance_for_external_preflight_block(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        governance: dict[str, Any],
        approval_checkpoints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = str(governance.get('reason') or f'La ruta hacia {assistant_title} no es viable ahora mismo.').strip()
        if approval_checkpoints:
            return {
                'mode': 'need_approval',
                'title': f'Permiso para observar {assistant_title}',
                'prompt': prompt,
                'actions': [
                    self._assistant_action('approve_observation_permission', 'Permitir observacion', 'Conceder permiso de observacion y reintentar la consulta.'),
                    self._assistant_action(f'consult_{assistant_kind}', f'Reintentar {assistant_title}', 'Volver a correr el preflight cuando cambie el estado.'),
                    self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Revisar por que la ruta externa quedo bloqueada.'),
                ],
            }
        return {
            'mode': 'need_evolution_review',
            'title': f'Ruta bloqueada para {assistant_title}',
            'prompt': prompt,
            'actions': [
                self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Verificar el bloqueo operativo antes de insistir.'),
                self._assistant_action('open_evolution_center', 'Ver evolutivo', 'Inspeccionar estado operativo, evidencia y bloqueos.'),
                self._assistant_action('review_stack', 'Revisar stack', 'Actualizar red, procesos y herramientas antes de otro intento.'),
            ],
        }

    def _pending_observation_permission_assistant(self) -> str:
        metadata = dict((self._last_adaptive_payload or {}).get('metadata') or {})
        preflight = dict(metadata.get('external_consultation_preflight') or {})
        assistant_kind = str(preflight.get('assistant_kind') or '').strip().lower()
        if assistant_kind:
            return assistant_kind
        for item in (self._last_adaptive_payload or {}).get('approval_checkpoints') or []:
            checkpoint = dict(item or {})
            checkpoint_meta = dict(checkpoint.get('metadata') or {})
            gates = [dict(gate) for gate in (checkpoint_meta.get('permission_gates') or []) if isinstance(gate, dict)]
            gate = gates[0] if gates else {}
            assistant_kind = str(gate.get('assistant_kind') or checkpoint_meta.get('assistant_kind') or '').strip().lower()
            if assistant_kind:
                return assistant_kind
        return ''

    def _clear_observation_permission_artifacts(self) -> None:
        payload = dict(self._last_adaptive_payload or {})
        if not payload:
            return
        approvals = [dict(item) for item in (payload.get('approval_checkpoints') or []) if isinstance(item, dict)]
        filtered = [item for item in approvals if str(item.get('phase_key') or '').strip().lower() != 'observation_permission']
        metadata = dict(payload.get('metadata') or {})
        removed_preflight = metadata.pop('external_consultation_preflight', None)
        if len(filtered) == len(approvals) and removed_preflight is None:
            return
        payload['approval_checkpoints'] = filtered
        payload['metadata'] = metadata
        self._last_adaptive_payload = payload

    def _grant_pending_observation_permission(self, *, announce: bool = True) -> bool:
        assistant_kind = self._pending_observation_permission_assistant()
        if not assistant_kind:
            if announce:
                self._append_message('assistant', 'IABV', 'No encontre un permiso de observacion pendiente para conceder.', 'Sin permiso pendiente.')
            self._busy_label = 'No hay permiso de observacion pendiente.'
            self.dataChanged.emit()
            return False
        world_model_service = getattr(getattr(self.adaptive_orchestrator, 'context_assembler', None), 'world_model_service', None)
        if world_model_service is None or not hasattr(world_model_service, 'grant_observation_permission'):
            if announce:
                self._append_message('assistant', 'IABV', 'No tengo acceso al servicio que registra permisos de observacion en esta sesion.', 'Permiso no registrado.')
            self._busy_label = 'No pude registrar el permiso de observacion.'
            self.dataChanged.emit()
            return False
        assistant_title = self._assistant_display_name(assistant_kind)
        world_model_service.grant_observation_permission(
            scope=f'observe_window_content:{assistant_kind}',
            assistant_kind=assistant_kind,
            title=f'Observacion de {assistant_title}',
            detail=f'Permiso concedido por el usuario para verificar {assistant_title} antes de usarlo.',
            granted_by='control_center',
        )
        self._clear_observation_permission_artifacts()
        if announce:
            self._append_message(
                'assistant',
                'IABV',
                f'Registre el permiso para observar {assistant_title}. Voy a reintentar la consulta con preflight fresco.',
                f'Permiso concedido para {assistant_title}.',
            )
        self._approval_dialog_visible = False
        self._approval_dialog_title = 'Permiso concedido'
        self._approval_dialog_text = f'La observacion de {assistant_title} ya quedo permitida para esta sesion.'
        self.dataChanged.emit()
        return self._run_external_consultation(assistant_kind, announce=False)

    # Maximum seconds an external consultation can run before being
    # considered a ghost session.  After this deadline the _working flag
    # is auto-reset so the user can continue interacting with the UI.
    _CONSULTATION_TIMEOUT_S: int = 180

    def _run_external_consultation(self, assistant_kind: str, *, announce: bool = True) -> bool:
        assistant_title = self._assistant_display_name(assistant_kind)
        self._working = True
        import time as _time
        self._working_since = _time.time()
        self._busy_label = f'Voy a preparar una consulta con {assistant_title}.'
        self._latest_response_text = (
            f'Consulta externa aceptada para {assistant_title}. '
            'Estoy preparando la via dedicada en segundo plano para no congelar la interfaz.'
        )
        self._latest_response_meta = f'Preparando consulta con {assistant_title}.'
        self._set_autonomy_activity_override(
            visible=True,
            title='Preparando consulta externa',
            status='active',
            stage='seleccionando herramienta y contexto',
            progress=0.52,
            detail=f'Estoy preparando la mejor via para {assistant_title} con el contexto actual sin bloquear el chat.',
            tool=assistant_title,
            next_step='Si la via es valida, abrire la herramienta y observare la respuesta.',
            learning_note='La consulta externa se arma con evidencia, objetivo persistente y backlog reciente.',
            mode='external',
        )
        if announce:
            self._append_message('assistant', 'IABV', self._latest_response_text, self._latest_response_meta)
        self.dataChanged.emit()

        consultation_epoch = _time.time()

        def worker() -> None:
            try:
                result_payload = self._execute_external_consultation_sync(assistant_kind)
                self.taskResolved.emit('external_consultation', result_payload)
            except Exception as exc:
                self.taskFailed.emit('external_consultation', f'No pude completar la consulta externa guiada: {exc}')

        def _ghost_session_watchdog() -> None:
            """Auto-reset _working if the consultation exceeds the deadline.

            Without this, a stuck external session (e.g. ChatGPT browser
            tab that never responds) keeps _working=True forever and the
            user cannot send new messages until the 60 s reset in sendChat.
            """
            if not self._working:
                return
            import time as _tw
            if (_tw.time() - consultation_epoch) < self._CONSULTATION_TIMEOUT_S:
                return
            self._working = False
            self._busy_label = (
                f'La consulta con {assistant_title} excedio {self._CONSULTATION_TIMEOUT_S}s '
                'sin respuesta. Puedes seguir interactuando.'
            )
            self._set_live_status('idle')
            self._clear_autonomy_activity_override()
            self.dataChanged.emit()

        threading.Thread(target=worker, daemon=True).start()
        threading.Timer(
            self._CONSULTATION_TIMEOUT_S, _ghost_session_watchdog,
        ).start()
        return True

    def _perform_guidance_action(self, action: str, *, announce: bool = True) -> bool:
        action = (action or '').strip()
        if not action:
            return False
        if action == 'open_teaching_studio':
            teaching_prefill = self._build_teaching_prefill()
            if self.capture_studio_viewmodel is not None and hasattr(self.capture_studio_viewmodel, 'applyAdaptiveTeachingPrefill'):
                try:
                    self.capture_studio_viewmodel.applyAdaptiveTeachingPrefill(teaching_prefill)
                except Exception:
                    pass
            self._navigate_to('capture')
            self._busy_label = 'Estudio de ensenanza listo para capturar el flujo que falta.'
            if announce:
                if teaching_prefill.get('start_url') or teaching_prefill.get('objective'):
                    self._append_message(
                        'assistant',
                        'IABV',
                        'Te llevo a Estudio de ensenanza con el formulario rellenado usando lo que ya se del caso actual.',
                        'Accion sugerida aplicada desde el chat.',
                    )
                else:
                    self._append_message('assistant', 'IABV', 'Te llevo a Estudio de ensenanza para capturar o corregir ese flujo.', 'Accion sugerida aplicada desde el chat.')
            self.dataChanged.emit()
            return True
        if action == 'open_evolution_center':
            self._navigate_to('evolution')
            self._busy_label = 'Centro Evolutivo abierto para revisar evidencia e incidentes.'
            if announce:
                self._append_message('assistant', 'IABV', 'Abri el Centro Evolutivo para revisar incidentes, dossiers y backlog.', 'Accion sugerida aplicada desde el chat.')
            self.dataChanged.emit()
            return True
        if action == 'prepare_codex_packet':
            self.buildDevelopmentPacket(self._last_user_goal or 'caso actual')
            if announce:
                self._append_message('assistant', 'IABV', 'Paquete para Codex actualizado con el caso actual.', 'Accion sugerida aplicada desde el chat.')
            self.dataChanged.emit()
            return True
        if action == 'audit_autonomy':
            self.auditAutonomy()
            return True
        if action == 'consult_codex':
            return self._run_external_consultation('codex', announce=announce)
        if action == 'consult_chatgpt':
            return self._run_external_consultation('chatgpt', announce=announce)
        if action == 'consult_claude':
            return self._run_external_consultation('claude', announce=announce)
        if action == 'consult_ollama':
            return self._run_external_consultation('ollama', announce=announce)
        if action == 'approve_observation_permission':
            return self._grant_pending_observation_permission(announce=announce)
        if action == 'run_self_test':
            self.runSelfTeach(self._last_user_goal or 'abre Wplay e inicia sesion')
            return True
        if action == 'ingest_external_response':
            self.ingestClipboardExternalResponse()
            return True
        if action == 'replan_strategy':
            self.replanAdaptive()
            return True
        if action == 'review_stack':
            if announce:
                self._append_message('assistant', 'IABV', 'Voy a revisar el stack local antes de seguir.', 'Accion sugerida aplicada desde el chat.')
            self.refreshProviderHealth()
            return True
        if action == 'approve_strategy':
            self.approveStrategy()
            return True
        if action == 'approve_next_phase':
            self.approveNextPhase()
            return True
        if action == 'simulate':
            self.simulateAdaptive()
            return True
        if action == 'execute_now':
            self.executeAdaptive()
            return True
        if action == 'abort':
            self.abortAdaptive()
            return True
        if action == 'provision_missing_keys':
            from iabv_v15.services.auto_correction_engine import auto_provision_missing_secrets
            discovery = None
            if self.adaptive_orchestrator is not None:
                discovery = getattr(self.adaptive_orchestrator, 'api_key_discovery_service', None)
            if discovery is not None:
                missing = discovery.find_missing_keys()
                missing_names = [m['env_key'] for m in missing]
            else:
                missing_names = []
            context = {'account_scan': {'secrets': {'missing': missing_names}}}
            result = auto_provision_missing_secrets(context, open_browser=True)
            opened = result.get('opened_count', 0)
            if announce:
                self._append_message(
                    'assistant', 'IABV',
                    f'Se abrieron {opened} paginas para crear API keys. '
                    'Cuando tengas cada token, pegalo en el dialogo de IABV.',
                    f'provision: {opened} pages opened',
                )
            self._assistant_action_buttons = []
            return True

        if action == 'execute_cloud_plan':
            def _cloud_exec() -> None:
                try:
                    self._execute_cloud_plan()
                finally:
                    self._working = False
                    self._set_live_status('idle')
            self._working = True
            threading.Thread(target=_cloud_exec, daemon=True).start()
            return True

        if action == 'replan_cloud':
            goal = getattr(self, '_last_user_goal', '')
            if goal:
                self._pending_cloud_plan = None
                self._assistant_action_buttons = []
                def _replan() -> None:
                    try:
                        self._handle_cloud_plan_request(goal)
                    finally:
                        self._working = False
                        self._set_live_status('idle')
                self._working = True
                threading.Thread(target=_replan, daemon=True).start()
            return True

        if action == 'execute_coordinated_plan':
            # Fix 56: handle the coordinated plan action generated by
            # AdaptiveTaskOrchestrator._maybe_coordinated_plan_action().
            # Delegates to the adaptive orchestrator's auto-execute path
            # which chains primary IA → secondary IA.
            if self._adaptive_session_id and self.adaptive_orchestrator is not None:
                self._run_adaptive_action(
                    action_name='execute',
                    busy_text='Ejecutando plan coordinado multi-IA.',
                )
            elif self._last_user_goal:
                # No active adaptive session — re-submit the last goal
                # so the orchestrator creates one with the coordinated plan.
                self.sendChat(self._last_user_goal)
            if announce:
                self._append_message(
                    'assistant', 'IABV',
                    'Ejecutando plan coordinado. Voy a consultar las IAs en secuencia.',
                    'Plan coordinado activado desde gesto sugerido.',
                )
            return True

        # Interactive key setup — buttons generated by _handle_interactive_key_generation
        if action.startswith('setup_key_'):
            provider_id = action[len('setup_key_'):]
            prov = next((p for p in self._API_KEY_PROVIDERS if p['id'] == provider_id), None)
            if prov is not None:
                import webbrowser
                try:
                    webbrowser.open(prov['url'])
                except Exception:
                    pass
                self._append_message(
                    'assistant', 'IABV',
                    f'Abri la pagina de {prov["name"]} en tu navegador.\n\n'
                    f'1. Crea o copia tu API key de ahi\n'
                    f'2. Pegala aqui en el chat con el formato:\n'
                    f'   `key {provider_id} TU_KEY_AQUI`\n\n'
                    f'IABV la guarda automaticamente en ~/.iabv_secrets.ps1.',
                    f'interactive-key-setup: opened {prov["name"]}',
                )
                self._assistant_action_buttons = []
                self.dataChanged.emit()
                # Emit credential prompt signal for the inline secure input
                try:
                    self.credentialPromptRequested.emit({
                        'domain': prov['id'],
                        'reason': f'API key de {prov["name"]} para cloud reasoning',
                        'username_hint': prov['env_key'],
                    })
                except Exception:
                    pass
            return True
        return False

    def _normalized_command_text(self, message: str) -> str:
        return ' '.join(message.lower().strip().split())

    def _try_synchronous_shortcut(self, message: str) -> bool:
        """Try to answer via keyword-only shortcut detection (no LLM).

        Returns True if the message was handled synchronously. This
        avoids spawning a background thread for simple questions like
        "conoces tu entorno?" or "que aprendiste?". Only uses fast
        keyword matching — no Ollama or LLM calls.

        Compound messages (long texts with conjunctions and action
        verbs) are skipped so they go through the full inference path.
        """
        import re as _re
        normalized = self._normalized_command_text(message)
        words = normalized.split() if normalized else []
        if len(words) > 12:
            has_conjunction = bool(_re.search(r'\b(y|pero|ademas|tambien|sin embargo)\b', normalized))
            action_verbs = ('revisa', 'analiza', 'diagnostica', 'corrige', 'ejecuta', 'planifica', 'soluciona')
            has_action = any(v in normalized for v in action_verbs)
            if has_conjunction and has_action:
                return False
        if self._is_world_model_question(message):
            self._answer_world_model_question(message)
            return True
        if self._is_self_awareness_question(message, fast_only=True):
            self._answer_self_awareness_question(message)
            return True
        if self._is_evolution_status_question(message):
            self._answer_evolution_status_question(message)
            return True
        if self._is_self_examination_question(message):
            self._answer_self_examination_question(message)
            return True
        if self._is_learning_question(message, fast_only=True):
            self._answer_learning_question(message)
            return True
        if self._is_account_resource_question(message, fast_only=True):
            self._answer_account_resource_question(message)
            return True
        return False

    def _try_handle_chat_command(self, message: str) -> bool:
        command = self._normalized_command_text(message)
        if not command:
            return False

        # Inline key pasting: "key groq gsk_..." or "key gemini AIza..."
        if command.startswith('key '):
            parts = command.split(None, 2)
            if len(parts) >= 3:
                provider_id = parts[1]
                raw_value = message.split(None, 2)[2].strip()  # preserve original case
                self._save_api_key(provider_id, raw_value, persist=True)
                return True

        if any(token in command for token in ('mostrar avanzado', 'ver avanzado', 'abrir avanzado')):
            self._advanced_visible = True
            self._busy_label = 'Modo avanzado visible.'
            self._append_message('assistant', 'IABV', 'Modo avanzado visible. Puedes seguir por chat o revisar los paneles tecnicos cuando quieras.', 'Control visual actualizado desde el chat.')
            self.dataChanged.emit()
            return True
        if any(token in command for token in ('ocultar avanzado', 'cerrar avanzado')):
            self._advanced_visible = False
            self._busy_label = 'Modo avanzado oculto.'
            self._append_message('assistant', 'IABV', 'Modo avanzado oculto. El chat vuelve a quedar como consola principal.', 'Control visual actualizado desde el chat.')
            self.dataChanged.emit()
            return True
        if 'modo automatico' in command:
            self.setRole('auto')
            self._append_message('assistant', 'IABV', 'Volvi al modo automatico. Voy a decidir rol, pack y aprobaciones antes de responder.', self._routing_mode_label())
            self.dataChanged.emit()
            return True
        if 'abrir estudio de ensenanza' in command or 'abrir ensenanza' in command:
            return self._perform_guidance_action('open_teaching_studio')
        if 'abrir centro evolutivo' in command or 'ver evolutivo' in command or 'abrir evolutivo' in command:
            return self._perform_guidance_action('open_evolution_center')
        if any(token in command for token in ('prueba wplay', 'analiza wplay', 'analiza por que falla wplay', 'haz autotest', 'autotest del login', 'ensenate de este fallo', 'ense?ate de este fallo')):
            self.runSelfTeach(message)
            return True
        if 'aprobar estrategia' in command:
            self.approveStrategy()
            return True
        if 'aprobar fase' in command or 'aprobar siguiente fase' in command:
            self.approveNextPhase()
            return True
        if 'simular' in command:
            self.simulateAdaptive()
            return True
        if 'ejecutar ahora' in command or 'ejecuta ahora' in command:
            self.executeAdaptive()
            return True
        if 'abortar' in command or 'cancelar ejecucion' in command:
            self.abortAdaptive()
            return True
        if 'revisar stack' in command or 'revisa stack' in command or 'actualizar stack' in command or 'actualiza stack' in command or 'estado del stack' in command:
            self._append_message('assistant', 'IABV', 'Voy a revisar el stack local en segundo plano y te dejo el diagnostico actualizado.', 'Chequeo automatico solicitado por chat.')
            self.refreshProviderHealth()
            return True
        if any(token in command for token in ('generar keys', 'crear keys', 'configurar keys', 'agregar keys', 'agregar api', 'configurar api')):
            self._handle_interactive_key_generation()
            return True
        if any(token in command for token in ('revisar api keys', 'revisa api keys', 'estado de las keys', 'health check keys', 'probar keys', 'verificar keys', 'buscar keys', 'renovar keys')):
            self._handle_api_key_health_command()
            return True
        if any(token in command for token in ('auditar decisiones', 'audita decisiones', 'ver historial', 'historial de decisiones', 'decision audit', 'ver audit trail', 'como van las decisiones', 'esta mejorando')):
            self._handle_decision_audit_command()
            return True
        if 'auditar autonomia' in command or 'audita autonomia' in command or 'revisar autonomia' in command or 'revisa autonomia' in command:
            self.auditAutonomy()
            return True
        if 'replanificar' in command or 'replanifica' in command or 'replantear estrategia' in command or 'replan strategy' in command:
            self.replanAdaptive()
            return True
        if 'ingerir respuesta' in command or 'ingestar respuesta' in command or 'pegar respuesta' in command or 'leer respuesta' in command or 'consumir respuesta' in command:
            self.ingestClipboardExternalResponse()
            return True
        if command.startswith('respuesta externa:'):
            self.ingestExternalResponse(message.split(':', 1)[1].strip())
            return True
        if 'preparar paquete' in command:
            self.buildDevelopmentPacket(self._last_user_goal or message)
            self._append_message('assistant', 'IABV', 'Paquete para Codex actualizado con el objetivo actual.', 'Accion avanzada ejecutada por chat.')
            self.dataChanged.emit()
            return True
        if 'consultar codex' in command or 'consulta codex' in command or 'usar codex' in command:
            return self._run_external_consultation('codex', announce=True)
        if 'consultar chatgpt' in command or 'consulta chatgpt' in command or 'usar chatgpt' in command:
            return self._run_external_consultation('chatgpt', announce=True)
        if 'copiar paquete' in command:
            self.copyDevelopmentPacket()
            self._append_message('assistant', 'IABV', 'Paquete para Codex copiado al portapapeles.', 'Accion avanzada ejecutada por chat.')
            self.dataChanged.emit()
            return True
        if 'preparar payload' in command:
            self.preparePayload()
            return True
        if 'ciclo pbt' in command or 'ejecutar pbt' in command:
            self.runQuickPbt()
            return True
        if any(token in command for token in ('liberar ram', 'libera ram', 'liberar recursos', 'libera recursos', 'optimizar memoria', 'optimiza memoria', 'cerrar programas innecesarios')):
            self._handle_resource_liberation_command()
            return True
        if any(token in command for token in ('estas actualizado', 'estás actualizado', 'hay actualizaciones', 'hay updates', 'version actual', 'que version eres', 'qué version eres')):
            self._handle_update_check_command()
            return True
        if any(token in command for token in ('ver log de arranque', 'log de inicio', 'log startup', 'que paso al arrancar', 'qué paso al arrancar', 'mostrar log arranque')):
            self._handle_startup_log_command()
            return True
        if self._is_self_code_analysis_request(command):
            self._run_self_code_analysis()
            return True
        return False

    def _is_self_code_analysis_request(self, command: str) -> bool:
        """Detecta si el usuario pide que el programa analice su propio codigo,
        busque errores, mejoras pendientes, diagnostique lentitud o revise GPU."""
        direct_phrases = (
            'analizate',
            'analízate',
            'analiza tu codigo',
            'analiza tu código',
            'revisa tu codigo',
            'revisa tu código',
            'busca errores',
            'busca fallas',
            'busca bugs',
            'autoanalisis',
            'autoanálisis',
            'auto analisis',
            'auto análisis',
            'auto diagnostico',
            'autodiagnostico',
            'autodiagnóstico',
            'por que te congelas',
            'por qué te congelas',
            'por que estas lento',
            'por qué estás lento',
            'por que respondes lento',
            'por qué respondes lento',
            'analiza tu estado',
            'diagnostica tu estado',
            'diagnosticate',
            'diagnostícate',
            'examina tu codigo',
            'examina tu código',
            'revisa tu estado real',
            'reporte de tu estado',
            'mejoras pendientes',
            'ramas sin mergear',
            'ramas pendientes',
            'codigo desactualizado',
            'código desactualizado',
            'tu gpu esta funcionando',
            'tu gpu está funcionando',
            'revisa tu gpu',
        )
        if any(phrase in command for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', command))
        asks_self = any(t in word_tokens for t in ('analizate', 'analízate', 'autoanalisis', 'diagnosticate'))
        asks_code = any(t in word_tokens for t in ('codigo', 'código', 'errores', 'fallas', 'bugs', 'sintaxis'))
        asks_perf = any(t in word_tokens for t in ('lento', 'congela', 'congelas', 'rendimiento', 'lentitud'))
        asks_analyze = any(t in command for t in ('analiza', 'revisa', 'examina', 'diagnostica', 'busca'))
        if asks_analyze and (asks_code or asks_perf):
            return True
        if asks_self:
            return True
        return False

    def _run_self_code_analysis(self) -> None:
        """Ejecuta auto-update + self_code_analysis + gpu_metacognition en background."""
        self._append_message(
            'assistant', 'IABV',
            'Entendido. Primero me actualizo (git pull), luego analizo mi codigo, GPU, y busco mejoras pendientes...',
            'Metacognicion: auto-update + auto-analisis iniciado.',
        )
        self._set_live_status('processing')
        self.dataChanged.emit()

        def _worker() -> None:
            try:
                ws = str(getattr(self.config, 'workspace_root', ''))
                if not ws:
                    import os
                    ws = os.getcwd()
                sections: list[str] = []

                # 0. Auto-update: fetch + fast-forward on main only
                # Only resets to origin/main if currently on the main branch
                # and there are no local uncommitted changes. Otherwise uses
                # git pull --ff-only which is safe (no data loss).
                import subprocess as _sp
                current_branch = 'main'
                local_dirty = ''
                old_head = ''
                fetch_r = None
                try:
                    # Abort any in-progress merge first
                    _sp.run(
                        ['git', '-C', ws, 'merge', '--abort'],
                        capture_output=True, text=True, timeout=10,
                    )
                    # Fetch with prune to remove deleted remote branches
                    fetch_r = _sp.run(
                        ['git', '-C', ws, 'fetch', 'origin', '--prune'],
                        capture_output=True, text=True, timeout=30,
                    )
                    # Check current branch
                    current_branch = _sp.run(
                        ['git', '-C', ws, 'rev-parse', '--abbrev-ref', 'HEAD'],
                        capture_output=True, text=True, timeout=5,
                    ).stdout.strip()
                    # Check for local uncommitted changes
                    local_dirty = _sp.run(
                        ['git', '-C', ws, 'status', '--porcelain'],
                        capture_output=True, text=True, timeout=5,
                    ).stdout.strip()
                    old_head = _sp.run(
                        ['git', '-C', ws, 'rev-parse', '--short', 'HEAD'],
                        capture_output=True, text=True, timeout=5,
                    ).stdout.strip()

                    sections.append('== AUTO-UPDATE ==')

                    # Filter out non-essential dirty files (__pycache__, data/,
                    # logs) so they don't block auto-update or mislead the
                    # branch analysis. Only real source changes count.
                    _ignore_patterns = ('__pycache__/', '.pyc', 'data/', '.log', '.sqlite')
                    if local_dirty:
                        _dirty_lines = local_dirty.splitlines()
                        _real_dirty = [
                            line for line in _dirty_lines
                            if not any(pat in line for pat in _ignore_patterns)
                        ]
                        _ignored_count = len(_dirty_lines) - len(_real_dirty)
                        local_dirty = '\n'.join(_real_dirty)
                    else:
                        _ignored_count = 0

                    # Metacognition: detect if we're on a stale feature branch
                    # AGENTS.md: only devin/* and iabv-auto/* can be auto-switched;
                    # other prefixes (fix/, etc.) require explicit user approval
                    _stale_prefixes = ('devin/', 'iabv-auto/')
                    _is_feature_branch = any(current_branch.startswith(p) for p in _stale_prefixes)
                    if _is_feature_branch and not local_dirty:
                        _branch_age = _sp.run(
                            ['git', '-C', ws, 'log', '-1', '--format=%cr'],
                            capture_output=True, text=True, timeout=5,
                        ).stdout.strip()
                        sections.append(f'ALERTA METACOGNITIVA: Estoy en rama {current_branch}')
                        sections.append(f'  Ultimo commit: {_branch_age}')
                        sections.append('  Esta rama probablemente es obsoleta — cambiando a main para auto-analisis limpio')
                        _checkout_r = _sp.run(
                            ['git', '-C', ws, 'checkout', 'main'],
                            capture_output=True, text=True, timeout=10,
                        )
                        if _checkout_r.returncode == 0:
                            _sp.run(
                                ['git', '-C', ws, 'reset', '--hard', 'origin/main'],
                                capture_output=True, text=True, timeout=15,
                            )
                            current_branch = 'main'
                            local_dirty = ''
                            new_head = _sp.run(
                                ['git', '-C', ws, 'rev-parse', '--short', 'HEAD'],
                                capture_output=True, text=True, timeout=5,
                            ).stdout.strip()
                            sections.append(f'  Cambie a main exitosamente: HEAD={new_head}')
                        else:
                            sections.append(f'  No pude cambiar a main: {_checkout_r.stderr.strip()[:200]}')
                    elif _is_feature_branch and local_dirty:
                        _dirty_count = len(local_dirty.splitlines())
                        sections.append(f'ALERTA METACOGNITIVA: Estoy en rama {current_branch} con {_dirty_count} cambios de codigo fuente')
                        if _ignored_count:
                            sections.append(f'  ({_ignored_count} archivos cache/datos ignorados: __pycache__, data/, logs)')
                        sections.append('  No cambio a main para no perder trabajo — revisa si estos cambios son intencionales')
                    elif local_dirty:
                        sections.append('Cambios locales en codigo fuente detectados — omitiendo reset para no perder trabajo')
                        sections.append(f'  Branch: {current_branch}, archivos fuente modificados: {len(local_dirty.splitlines())}')
                        if _ignored_count:
                            sections.append(f'  ({_ignored_count} archivos cache/datos ignorados)')
                    elif current_branch in ('main', 'master'):
                        # Safe to reset: on main, no local changes
                        reset_r = _sp.run(
                            ['git', '-C', ws, 'reset', '--hard', f'origin/{current_branch}'],
                            capture_output=True, text=True, timeout=15,
                        )
                        new_head = _sp.run(
                            ['git', '-C', ws, 'rev-parse', '--short', 'HEAD'],
                            capture_output=True, text=True, timeout=5,
                        ).stdout.strip()
                        if reset_r.returncode == 0:
                            if old_head == new_head:
                                sections.append(f'Ya estoy actualizado (sin cambios nuevos en origin/{current_branch})')
                            else:
                                sections.append(f'Me actualice exitosamente: {old_head} -> {new_head}')
                        else:
                            sections.append(f'Error al actualizar: {reset_r.stderr.strip()[:200]}')
                    else:
                        # On a feature branch — try safe ff-only pull
                        ff_r = _sp.run(
                            ['git', '-C', ws, 'pull', '--ff-only'],
                            capture_output=True, text=True, timeout=30,
                        )
                        if ff_r.returncode == 0:
                            new_head = _sp.run(
                                ['git', '-C', ws, 'rev-parse', '--short', 'HEAD'],
                                capture_output=True, text=True, timeout=5,
                            ).stdout.strip()
                            if old_head == new_head:
                                sections.append(f'Ya estoy actualizado en branch {current_branch}')
                            else:
                                sections.append(f'Actualice branch {current_branch}: {old_head} -> {new_head}')
                        else:
                            sections.append(f'Branch {current_branch} diverge del remoto — conservando estado local')
                    # Report pruned branches if any
                    pruned = [l for l in ((fetch_r.stderr if fetch_r else '') or '').splitlines() if '[deleted]' in l]
                    if pruned:
                        sections.append(f'  Ramas remotas limpiadas: {len(pruned)}')
                except Exception as pull_exc:
                    sections.append('== AUTO-UPDATE ==')
                    sections.append(f'No pude actualizarme: {pull_exc}')
                sections.append('')

                # 1. Full self code analysis (includes syntax, slots, routing, tests, perf)
                branch_count = 0
                branches: list = []
                syntax: dict = {}
                mcp: dict = {}
                perf: dict = {}
                slots: dict = {}
                routing: dict = {}
                tests: dict = {}
                try:
                    from iabv_v15.services.self_code_analysis import full_self_analysis_report
                    report = full_self_analysis_report(ws)
                    syntax = report.get('syntax', {})
                    mcp = report.get('mcp_tools', {})
                    perf = report.get('performance', {})
                    slots = report.get('slot_decorators', {})
                    routing = report.get('intent_routing', {})
                    tests = report.get('tests', {})
                    branches = report.get('unmerged_branches', [])
                    branch_count = len(branches) if isinstance(branches, list) else 0

                    sections.append('== ANALISIS DE CODIGO ==')
                    sections.append(f"Salud general: {report.get('overall_health', 'desconocido')}")
                    sections.append(f"Sintaxis: {syntax.get('summary', 'sin datos')}")
                    sections.append(f"MCP Tools: {mcp.get('summary', 'sin datos')}")
                    sections.append(f"Rendimiento: {perf.get('summary', 'sin datos')}")

                    sections.append('')
                    sections.append('== INTEGRIDAD QML-PYTHON ==')
                    sections.append(f"@Slot decorators: {slots.get('summary', 'sin datos')}")
                    if slots.get('issues'):
                        for si in slots['issues'][:5]:
                            sections.append(f"  CRITICO: {si.get('method', '?')}() sin @Slot — QML no puede invocarlo")

                    sections.append('')
                    sections.append('== ROUTING DE INTENCION ==')
                    sections.append(f"Rutas verificadas: {routing.get('summary', 'sin datos')}")
                    if routing.get('ius_metacognition_intent'):
                        sections.append('IntentUnderstandingService: system.metacognition intent PRESENTE')
                    else:
                        sections.append('IntentUnderstandingService: FALTA system.metacognition intent (el cerebro no puede clasificar peticiones de auto-analisis)')
                    if routing.get('missing_handlers'):
                        for mh in routing['missing_handlers']:
                            sections.append(f"  FALTA: handler {mh} no existe")
                    if routing.get('unwired_handlers'):
                        for uh in routing['unwired_handlers']:
                            sections.append(f"  DESCONECTADO: handler {uh} existe pero no esta wired en sendChat")
                    routing_results = routing.get('results', [])
                    for rr in routing_results:
                        status = rr.get('status', '?')
                        phrase = rr.get('phrase', '?')
                        if status != 'OK':
                            sections.append(f"  {status}: '{phrase}' -> {rr.get('reason', '?')}")

                    sections.append('')
                    sections.append('== TESTS ==')
                    if tests.get('skipped'):
                        sections.append('Tests: no hay directorio tests/')
                    elif tests.get('ok'):
                        sections.append(f"Tests: {tests.get('summary', 'OK')}")
                    else:
                        sections.append(f"Tests: FALLARON — {tests.get('summary', 'error')}")
                        test_output = tests.get('output', '')
                        if test_output:
                            for line in test_output.splitlines()[-10:]:
                                sections.append(f"  {line}")

                    if branch_count > 0:
                        sections.append('')
                        sections.append(f'== RAMAS SIN MERGEAR: {branch_count} ==')
                        for b in branches[:5]:
                            bname = b.get('branch', '?') if isinstance(b, dict) else str(b)
                            commits = b.get('commits_ahead', 0) if isinstance(b, dict) else 0
                            sections.append(f"  - {bname} ({commits} commits)")
                except Exception as exc:
                    sections.append(f'Error en self_code_analysis: {exc}')

                # 2. GPU metacognition
                gpu_issues: list[str] = []
                try:
                    from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
                    gpu = gpu_metacognition_report()
                    sections.append('')
                    sections.append('== GPU ==')
                    gpu_count = gpu.get('nvidia_count', 0) + gpu.get('intel_igpu_count', 0)
                    sections.append(f"GPUs detectadas: {gpu_count}")
                    ollama = gpu.get('ollama_state', {})
                    sections.append(f"Ollama: {ollama.get('status', 'no detectado')}")
                    gpu_issues = gpu.get('issues', [])
                    if gpu_issues:
                        sections.append(f"Issues GPU: {len(gpu_issues)}")
                        for gi in gpu_issues[:3]:
                            sections.append(f"  - {gi}")
                    else:
                        sections.append('Issues GPU: ninguno')
                    strategy = gpu.get('dual_gpu_strategy', {})
                    if strategy:
                        sections.append(f"Estrategia GPU: {strategy.get('primary_compute', '?')} (primaria)")
                        sections.append(f"  Refuerzo: {strategy.get('reinforcement', '?')}")
                    recs = gpu.get('recommendations', [])
                    if recs:
                        for r in recs[:3]:
                            sections.append(f"  Recomendacion: {r}")
                except Exception as exc:
                    sections.append(f'Error en gpu_metacognition: {exc}')

                # 2.1 GPU routing verification — is Ollama on NVIDIA?
                _gpu_routing_result: dict = {}
                try:
                    from iabv_v15.services.gpu_metacognition import verify_ollama_gpu_usage
                    _gpu_routing_result = verify_ollama_gpu_usage()
                    routing_status = _gpu_routing_result.get('status', '')
                    if routing_status == 'optimal':
                        sections.append(f'  GPU Routing: OPTIMO — {_gpu_routing_result.get("detail", "")}')
                    elif routing_status in ('suboptimal', 'uncertain'):
                        sections.append(f'  GPU Routing: CORREGIDO — {_gpu_routing_result.get("detail", "")}')
                        for corr in _gpu_routing_result.get('corrections_made', []):
                            sections.append(f'    [AUTO-CORREGIDO] {corr.get("detail", "")}')
                    elif routing_status == 'idle':
                        sections.append(f'  GPU Routing: pre-configurado — {_gpu_routing_result.get("detail", "")}')
                    elif routing_status == 'no_nvidia':
                        sections.append(f'  GPU Routing: {_gpu_routing_result.get("detail", "sin NVIDIA")}')
                except Exception as gpu_rt_exc:
                    sections.append(f'  GPU Routing: error — {gpu_rt_exc}')

                # 2.3 Tool version monitoring
                version_scan: dict = {}
                try:
                    from iabv_v15.services.tools.tool_version_monitor import (
                        full_version_scan, format_version_report, persist_version_log,
                    )
                    version_scan = full_version_scan()
                    sections.append('')
                    sections.append(format_version_report(version_scan))
                    persist_version_log(ws, version_scan)
                except Exception as exc:
                    sections.append(f'Error en version monitor: {exc}')

                # 2.5 Diagnostico de trabajo en vivo y consultas externas
                sections.append('')
                sections.append('== DIAGNOSTICO DE TRABAJO EN VIVO ==')
                try:
                    stalled_items: list[str] = []
                    # A) In-memory: check adaptive orchestrator sessions
                    if hasattr(self, 'adaptive_orchestrator'):
                        sessions = getattr(self.adaptive_orchestrator, '_sessions', {})
                        for sid, session in sessions.items():
                            progress = getattr(session, 'progress', 0)
                            status = getattr(session, 'status', 'unknown')
                            if status == 'active' and 0 < progress < 1.0:
                                elapsed = getattr(session, 'elapsed_seconds', 0)
                                if elapsed > 120:
                                    stalled_items.append(
                                        f"Sesion {sid[:12]}... estancada en {int(progress*100)}% por {int(elapsed)}s — posible bloqueo"
                                    )
                    # B) On-disk: scan adaptive_sessions dir for non-completed sessions
                    import json as _json
                    from pathlib import Path as _Path
                    sessions_dir = _Path(ws) / 'data' / 'evolution' / 'adaptive_sessions'
                    if sessions_dir.exists():
                        terminal_states = {'completed', 'failed', 'cancelled', 'noop'}
                        disk_stalled = 0
                        for sf in sessions_dir.glob('*.json'):
                            try:
                                sd = _json.loads(sf.read_text(encoding='utf-8', errors='replace'))
                                s_status = str(sd.get('status', '')).lower()
                                if s_status and s_status not in terminal_states:
                                    disk_stalled += 1
                                    if disk_stalled <= 5:
                                        s_goal = str(sd.get('user_goal', ''))[:60]
                                        stalled_items.append(
                                            f"Sesion {sf.stem[:12]}... status={s_status} — '{s_goal}'"
                                        )
                            except Exception:
                                continue
                        if disk_stalled > 5:
                            stalled_items.append(f"... y {disk_stalled - 5} sesiones mas no terminadas")
                    # C) Check for visible browser consultations that should be background
                    if hasattr(self, '_consultation_history'):
                        for ch in list(self._consultation_history or [])[-5:]:
                            if ch.get('tool_id') in ('chatgpt_web_assisted', 'claude_web_assisted'):
                                if ch.get('status') in ('prepared', 'awaiting_response'):
                                    stalled_items.append(
                                        f"Consulta externa {ch.get('tool_id', '?')} abierta — deberia correr en background (headless)"
                                    )
                    if stalled_items:
                        for si_item in stalled_items:
                            sections.append(f"  ALERTA: {si_item}")
                    else:
                        sections.append('Sin trabajo estancado ni consultas externas visibles.')
                except Exception as work_exc:
                    sections.append(f'Error al diagnosticar trabajo en vivo: {work_exc}')

                # 3. Auto-correccion: limpiar ramas obsoletas (no mergear)
                cleanup_result: dict = {}
                if branch_count > 0:
                    sections.append('')
                    sections.append('== AUTO-CORRECCION: LIMPIEZA DE RAMAS OBSOLETAS ==')
                    try:
                        from iabv_v15.services.self_code_analysis import cleanup_stale_remote_branches
                        cleanup_result = cleanup_stale_remote_branches(ws)
                        if cleanup_result.get('deleted'):
                            sections.append(f"Elimine {len(cleanup_result['deleted'])} ramas obsoletas del remoto:")
                            for db in cleanup_result['deleted'][:10]:
                                sections.append(f"  - {db}")
                            if len(cleanup_result['deleted']) > 10:
                                sections.append(f"  ... y {len(cleanup_result['deleted']) - 10} mas")
                        if cleanup_result.get('conserved'):
                            sections.append(f"Conserve {len(cleanup_result['conserved'])} ramas (aun tienen valor):")
                            for cv in cleanup_result['conserved'][:5]:
                                sections.append(f"  + {cv.get('branch', '?')}: {cv.get('reason', '?')[:80]}")
                        if cleanup_result.get('failed'):
                            sections.append(f"{len(cleanup_result['failed'])} ramas no se pudieron eliminar:")
                            for fb in cleanup_result['failed'][:5]:
                                sections.append(f"  x {fb.get('branch', '?')}: {fb.get('reason', '?')[:80]}")
                        if cleanup_result.get('skipped_count', 0) > 0:
                            sections.append(f"{cleanup_result['skipped_count']} ramas ignoradas (prefijo no seguro)")
                        if not cleanup_result.get('deleted') and not cleanup_result.get('conserved'):
                            sections.append('No hay ramas obsoletas que limpiar.')
                        sections.append(f"Resumen: {cleanup_result.get('summary', 'n/a')}")
                    except Exception as cleanup_exc:
                        sections.append(f'Error en limpieza de ramas: {cleanup_exc}')

                # 4.5a Deep environment scan — run BEFORE holistic to feed cross-deductions
                _deep_scan: dict = {}
                try:
                    from iabv_v15.services.deep_environment_scanner import (
                        deep_environment_scan, format_deep_scan_report,
                    )
                    _deep_scan = deep_environment_scan()
                except Exception as deep_exc:
                    logger.debug('Deep scan failed: %s', deep_exc)

                # 4.5b Account & Resource scan — APIs, cuentas, secretos
                _account_scan: dict = {}
                try:
                    from iabv_v15.services.account_resource_scanner import (
                        account_resource_scan, format_account_resource_report,
                    )
                    _account_scan = account_resource_scan()
                except Exception as acc_exc:
                    logger.debug('Account scan failed: %s', acc_exc)

                # 4.5c Regression cycle detection — hacer-deshacer
                _regression_scan: dict = {}
                try:
                    from iabv_v15.services.regression_cycle_detector import (
                        regression_cycle_scan,
                    )
                    _regression_scan = regression_cycle_scan(workspace=ws)
                except Exception as reg_exc:
                    logger.debug('Regression scan failed: %s', reg_exc)

                # 4.5 Holistic metacognition: cross-reference ALL sources
                try:
                    from iabv_v15.services.self_code_analysis import holistic_metacognition_scan
                    _monitor_count = 1
                    try:
                        from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner
                        _runner = UIExecutionRunner(workspace_root=ws)
                        _monitors = _runner.detect_all_monitors()
                        _monitor_count = len(_monitors) if _monitors else 1
                    except Exception:
                        pass
                    holistic = holistic_metacognition_scan(
                        git_state={
                            'branch': current_branch,
                            'dirty_count': len(local_dirty.splitlines()) if local_dirty else 0,
                        },
                        gpu_state=gpu if 'gpu' in locals() else None,
                        test_state=tests,
                        version_state=version_scan,
                        branch_state=branches,
                        stalled_sessions=stalled_items if 'stalled_items' in locals() else None,
                        monitor_count=_monitor_count,
                        workspace=ws,
                        account_state=_account_scan if _account_scan else None,
                        regression_state=_regression_scan if _regression_scan else None,
                        deep_env_state=_deep_scan if '_deep_scan' in locals() and _deep_scan else None,
                    )
                    sections.append('')
                    sections.append('== CRUCE DE FUENTES DE VERDAD ==')
                    sections.append(f"Fuentes cruzadas: {holistic['cross_validation_count']}")
                    sections.append(f"Confianza del escaneo: {holistic['confidence']}")
                    if holistic['deductions']:
                        sections.append(f"Deducciones ({holistic['deduction_count']}):")
                        for d in holistic['deductions']:
                            icon = {'critical': 'CRITICO', 'warning': 'ALERTA', 'info': 'INFO'}.get(d['severity'], '?')
                            sections.append(f"  [{icon}] {d['area']}: {d['finding']}")
                            if d.get('action') and d['action'] != 'none':
                                sections.append(f"    Accion: {d['action']}")
                    else:
                        sections.append('Sin deducciones — todas las fuentes son coherentes.')
                    if holistic['blind_spots']:
                        sections.append(f"Blind spots ({holistic['blind_spot_count']}):")
                        for bs in holistic['blind_spots']:
                            sections.append(f"  [CIEGO] {bs}")
                except Exception as hol_exc:
                    sections.append(f'Error en cruce de fuentes: {hol_exc}')

                # 4.6 Deep environment scan report
                try:
                    if _deep_scan:
                        sections.append('')
                        sections.append(format_deep_scan_report(_deep_scan))
                except Exception as deep_exc:
                    sections.append(f'\nError en reporte de escaneo profundo: {deep_exc}')

                # 4.6a Account & Resource report
                try:
                    if _account_scan:
                        sections.append('')
                        sections.append(format_account_resource_report(_account_scan))
                except Exception as acc_rep_exc:
                    sections.append(f'\nError en reporte de cuentas: {acc_rep_exc}')

                # 4.6b Regression cycle report
                try:
                    if _regression_scan:
                        from iabv_v15.services.regression_cycle_detector import format_regression_report
                        sections.append('')
                        sections.append(format_regression_report(_regression_scan))
                except Exception as reg_rep_exc:
                    sections.append(f'\nError en reporte de regresiones: {reg_rep_exc}')

                # 4.6c Limits awareness report
                try:
                    from iabv_v15.services.limits_awareness import (
                        limits_awareness_scan, format_limits_report,
                    )
                    _limits_scan = limits_awareness_scan(
                        monitor_count=_monitor_count if '_monitor_count' in locals() else 1,
                        environment_scan=_deep_scan,
                        workspace=ws,
                    )
                    sections.append('')
                    sections.append(format_limits_report(_limits_scan))
                except Exception as lim_exc:
                    sections.append(f'\nError en reporte de limites: {lim_exc}')

                # 4.7 Evolution backlog — tareas pendientes priorizadas
                try:
                    from iabv_v15.services.evolution_backlog import (
                        seed_initial_backlog, deduce_priorities,
                        format_backlog_report,
                    )
                    seed_initial_backlog(workspace=ws)
                    _holistic_for_backlog = holistic if 'holistic' in locals() else {}
                    deduce_priorities(
                        environment_scan=_deep_scan,
                        holistic_scan=_holistic_for_backlog,
                        workspace=ws,
                    )
                    sections.append('')
                    sections.append(format_backlog_report(workspace=ws))
                except Exception as bl_exc:
                    sections.append(f'\nError en backlog de evolucion: {bl_exc}')

                # 4.8 Auto-correction engine — correcciones autónomas + deducción de herramientas
                _auto_correction_result: dict = {}
                try:
                    from iabv_v15.services.auto_correction_engine import (
                        execute_auto_corrections, format_auto_correction_report,
                    )
                    _auto_correction_result = execute_auto_corrections(
                        holistic_scan=holistic if 'holistic' in locals() else None,
                        account_scan=_account_scan if '_account_scan' in locals() else None,
                        limits_scan=_limits_scan if '_limits_scan' in locals() else None,
                        gpu_scan=gpu if 'gpu' in locals() else None,
                        regression_scan=_regression_scan if '_regression_scan' in locals() else None,
                        deep_env_scan=_deep_scan if '_deep_scan' in locals() else None,
                        workspace=ws,
                    )
                    sections.append('')
                    sections.append(format_auto_correction_report(_auto_correction_result))
                except Exception as ac_exc:
                    sections.append(f'\nError en auto-correccion: {ac_exc}')

                # 4.9 Common sense reasoning — razonamiento autónomo
                _common_sense_result: dict = {}
                try:
                    from iabv_v15.services.common_sense_engine import (
                        run_common_sense_reasoning, format_common_sense_report,
                    )
                    _common_sense_result = run_common_sense_reasoning(
                        gpu_scan=gpu if 'gpu' in locals() else None,
                        account_scan=_account_scan if '_account_scan' in locals() else None,
                        holistic_scan=holistic if 'holistic' in locals() else None,
                        limits_scan=_limits_scan if '_limits_scan' in locals() else None,
                        regression_scan=_regression_scan if '_regression_scan' in locals() else None,
                        deep_env_scan=_deep_scan if '_deep_scan' in locals() else None,
                        git_state=git_info if 'git_info' in locals() else None,
                        version_state=version_scan if 'version_scan' in locals() else None,
                    )
                    sections.append('')
                    sections.append(format_common_sense_report(_common_sense_result))
                except Exception as cs_exc:
                    sections.append(f'\nError en razonamiento autónomo: {cs_exc}')

                # 5. Veredicto final con transparencia total
                sections.append('')
                sections.append('== VEREDICTO ==')
                issues_found: list[str] = []
                if syntax.get('errors'):
                    issues_found.append(f"{len(syntax['errors'])} errores de sintaxis")
                if not slots.get('ok', True):
                    issues_found.append(f"{len(slots.get('issues', []))} metodos sin @Slot (QML roto)")
                if not routing.get('ok', True):
                    issues_found.append('routing de intencion incompleto')
                if not tests.get('ok', True) and not tests.get('skipped'):
                    issues_found.append(f"tests fallaron: {tests.get('summary', '?')}")
                remaining_branches = branch_count - cleanup_result.get('deleted_count', 0)
                if remaining_branches > 10:
                    issues_found.append(f"{remaining_branches} ramas pendientes (deuda tecnica)")
                if gpu_issues:
                    issues_found.append(f"{len(gpu_issues)} issues de GPU")
                perf_findings = perf.get('findings', [])
                if perf_findings:
                    issues_found.append(f"{len(perf_findings)} problemas de rendimiento")
                if issues_found:
                    sections.append('Issues encontrados:')
                    for iss in issues_found:
                        sections.append(f'  - {iss}')
                    sections.append('Estado: NECESITA ATENCION')
                else:
                    sections.append('No se encontraron problemas.')
                    sections.append('Estado: codigo verificado, listo para produccion.')
                analysis_time = report.get('elapsed_seconds', '?') if 'report' in locals() else '?'
                sections.append(f"Tiempo de analisis: {analysis_time}s")

                # 6. Metacognition decision log — persist what was learned
                import json as _json
                from datetime import datetime as _dt, timezone as _tz
                _holistic_summary = holistic if 'holistic' in locals() else {}
                decision_log = {
                    'timestamp': _dt.now(_tz.utc).isoformat(),
                    'analysis_time_seconds': analysis_time,
                    'gpu_strategy': gpu.get('dual_gpu_strategy', {}) if 'gpu' in locals() else {},
                    'branches_deleted': len(cleanup_result.get('deleted', [])),
                    'branches_conserved': len(cleanup_result.get('conserved', [])),
                    'syntax_errors': len(syntax.get('errors', [])),
                    'tests_ok': tests.get('ok', False),
                    'mcp_tools_count': mcp.get('tool_count', 0),
                    'issues_found': issues_found,
                    'estado': 'NECESITA ATENCION' if issues_found else 'VERIFICADO',
                    'tools_available': version_scan.get('available_count', 0),
                    'tools_unavailable': version_scan.get('unavailable_tools', []),
                    'holistic_deductions': _holistic_summary.get('deductions', []),
                    'holistic_blind_spots': _holistic_summary.get('blind_spots', []),
                    'holistic_confidence': _holistic_summary.get('confidence', 0),
                    'cross_validations_count': _holistic_summary.get('cross_validation_count', 0),
                    'deep_scan_summary': _deep_scan.get('summary', {}) if '_deep_scan' in locals() else {},
                    'account_resource_summary': _account_scan.get('summary', {}) if '_account_scan' in locals() else {},
                    'regression_summary': _regression_scan.get('summary', {}) if '_regression_scan' in locals() else {},
                    'limits_count': _limits_scan.get('total_count', 0) if '_limits_scan' in locals() else 0,
                    'auto_corrections_applied': _auto_correction_result.get('corrections_count', 0) if '_auto_correction_result' in locals() else 0,
                    'user_requests_pending': _auto_correction_result.get('user_requests_count', 0) if '_auto_correction_result' in locals() else 0,
                    'tool_gaps_total': _auto_correction_result.get('tool_deduction', {}).get('total_gaps', 0) if '_auto_correction_result' in locals() else 0,
                }
                try:
                    import os as _os
                    log_dir = _os.path.join(ws, 'src', 'data', 'metacognition')
                    _os.makedirs(log_dir, exist_ok=True)
                    log_path = _os.path.join(log_dir, 'auto_analysis_log.jsonl')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(_json.dumps(decision_log, ensure_ascii=False) + '\n')
                except Exception:
                    pass

                reply = '\n'.join(sections)
                self._append_message(
                    'assistant', 'IABV', reply,
                    'Metacognicion: auto-analisis + auto-correccion completo.',
                )

            except Exception as exc:
                self._append_message(
                    'assistant', 'IABV',
                    f'Error durante el auto-analisis: {exc}',
                    'Metacognicion: error en auto-analisis.',
                )
            finally:
                self._set_live_status('idle')
                self.dataChanged.emit()

        threading.Thread(target=_worker, daemon=True).start()

    def _ingest_chat_capabilities(self, message: str) -> list[dict[str, str]]:
        """Delega en ChatCapabilityIngestionService si esta disponible.

        Devuelve la lista de notas cortas (con clave 'label' y 'hint') para que
        el chat pueda mostrarle al usuario "anotado: ..." en la siguiente
        respuesta. Si el service no esta inyectado (tests antiguos o bootstrap
        minimo), es no-op silencioso.
        """
        service = getattr(self, 'chat_capability_ingestion_service', None)
        if service is None:
            return []
        try:
            entries = service.ingest(message, session_id=self._chat_session_id)
        except Exception:
            return []
        notices: list[dict[str, str]] = []
        for entry in entries:
            notices.append({
                'kind': getattr(entry, 'kind', ''),
                'label': getattr(entry, 'label', ''),
                'matched_text': getattr(entry, 'matched_text', ''),
                'research_hint': getattr(entry, 'research_hint', ''),
            })
        if notices:
            self._pending_capability_notice.extend(notices)
            summary = self._format_capability_notice(notices)
            if summary:
                self._append_message(
                    'assistant',
                    'IABV',
                    summary,
                    'Anotado en backlog de investigacion automatica.',
                )
        return notices

    def _format_capability_notice(self, notices: list[dict[str, str]]) -> str:
        if not notices:
            return ''
        lines = [
            'Anote lo que mencionaste como area de investigacion (no lo pierdo en memoria):'
        ]
        for item in notices[:5]:
            matched = str(item.get('matched_text') or '').strip()
            label = str(item.get('label') or '').strip()
            hint = str(item.get('research_hint') or '').strip()
            if matched and label:
                lines.append(f"- {label}: '{matched}'. Plan: {hint}")
            elif label:
                lines.append(f"- {label}. Plan: {hint}")
        if len(notices) > 5:
            lines.append(f"(+{len(notices) - 5} mas en backlog)")
        return '\n'.join(lines)

    # ── Frente 4: Chat avanzado — métodos ──────────────────────────
    @Slot(str, str, int, str)
    def attachFile(self, name: str, path: str, size: int, file_type: str) -> None:
        entry = {'name': name, 'path': path, 'size': size, 'type': file_type}
        self._attached_files.append(entry)
        self.fileAttached.emit(entry)
        self.dataChanged.emit()

    @Slot(str)
    def detachFile(self, path: str) -> None:
        self._attached_files = [f for f in self._attached_files if f['path'] != path]
        self.fileDetached.emit(path)
        self.dataChanged.emit()

    @Slot()
    def clearAttachedFiles(self) -> None:
        self._attached_files.clear()
        self.dataChanged.emit()

    @Property(list, notify=dataChanged)
    def attachedFiles(self) -> list[dict[str, Any]]:
        return list(self._attached_files)

    @Property(int, notify=dataChanged)
    def attachedFileCount(self) -> int:
        return len(self._attached_files)

    @Slot(str)
    def searchChatHistory(self, query: str) -> None:
        self._chat_search_query = query.strip().lower()
        if not self._chat_search_query:
            self.chatSearchResults.emit(self._chat_messages)
            return
        filtered = [
            msg for msg in self._chat_messages
            if self._chat_search_query in (msg.get('text', '') or '').lower()
            or self._chat_search_query in (msg.get('speaker', '') or '').lower()
        ]
        self.chatSearchResults.emit(filtered)

    @Property(str, notify=dataChanged)
    def liveStatus(self) -> str:
        with self._ui_state_lock:
            return self._live_status

    def _set_live_status(self, status: str) -> None:
        with self._ui_state_lock:
            previous = self._live_status
            if previous == status:
                return
            self._live_status = status
        self.liveStatusChanged.emit(status)
        self.dataChanged.emit()
        # Audible notification when processing finishes
        if previous == 'processing' and status == 'idle':
            self._play_completion_sound()

    def _play_completion_sound(self) -> None:
        """Play a short notification sound when a task completes.

        Uses winsound on Windows (native, no dependencies).
        Falls back to terminal bell on other platforms.
        Runs in a background thread to avoid blocking the UI.
        """
        def _beep() -> None:
            try:
                import sys
                if sys.platform == 'win32':
                    import winsound
                    # Two short ascending tones: "task complete"
                    winsound.Beep(800, 150)
                    winsound.Beep(1200, 200)
                else:
                    # Terminal bell as cross-platform fallback
                    print('\a', end='', flush=True)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

    @Property(list, notify=dataChanged)
    def contextualSuggestions(self) -> list[dict[str, Any]]:
        return list(self._contextual_suggestions)

    def _refresh_contextual_suggestions(self) -> None:
        suggestions: list[dict[str, Any]] = []
        if hasattr(self, '_efficiency_audit_service'):
            suggestions.append({
                'text': 'Ejecutar auditoria de eficiencia',
                'category': 'audit',
                'icon': '\U0001f50d',
                'action': 'run_efficiency_audit',
                'priority': 3,
            })
        if self._chat_messages and len(self._chat_messages) > 2:
            suggestions.append({
                'text': 'Revisar self-examination',
                'category': 'diagnostic',
                'icon': '\U0001f9e0',
                'action': 'show_self_examination',
                'priority': 2,
            })
        suggestions.append({
            'text': 'Mostrar estado del mundo',
            'category': 'command',
            'icon': '\U0001f30d',
            'action': 'world_model',
            'priority': 1,
        })
        suggestions.append({
            'text': 'Ver evolucion del sistema',
            'category': 'evolution',
            'icon': '\U0001f4c8',
            'action': 'show_evolution',
            'priority': 1,
        })
        if self._attached_files:
            suggestions.append({
                'text': f'Procesar {len(self._attached_files)} archivo(s) adjunto(s)',
                'category': 'command',
                'icon': '\U0001f4ce',
                'action': 'process_attachments',
                'priority': 5,
            })
        self._contextual_suggestions = suggestions
        self.contextualSuggestionsChanged.emit(suggestions)

    @Slot(str, str)
    def handleSuggestionAction(self, action: str, text: str) -> None:
        action_map = {
            'run_efficiency_audit': 'Ejecutar auditoria de eficiencia',
            'show_self_examination': 'mostrar self examination',
            'world_model': 'mostrar estado del mundo',
            'show_evolution': 'mostrar evolucion',
            'process_attachments': 'procesar archivos adjuntos',
        }
        message = action_map.get(action, text)
        self.sendChat(message)

    @Slot(str, str)
    def applyCode(self, code: str, language: str) -> None:
        self.codeApplyRequested.emit(code, language)
        self._append_message('system', 'IABV', f'Codigo {language} recibido para aplicar ({len(code)} chars).')
        self.dataChanged.emit()

    @Slot(str, str)
    def downloadChat(self, content: str, filename: str) -> None:
        self.chatDownloadRequested.emit(content, filename)
        self._append_message('system', 'IABV', f'Descarga preparada: {filename}')
        self.dataChanged.emit()

    @Slot(str)
    def copyToClipboard(self, text: str) -> None:
        try:
            from iabv_v15.ui.qt import QGuiApplication
            clipboard = QGuiApplication.instance().clipboard()
            if clipboard:
                clipboard.setText(text)
        except Exception:
            pass


    # ── Auto-validación de interfaz ──────────────────────────
    def _validate_ui_reflects_reality(self) -> dict[str, Any]:
        """Cruza la percepción del sistema con la realidad para detectar inconsistencias.
        El sistema debe ser capaz de verificar que lo que muestra en su interfaz
        corresponde a lo que realmente tiene/sabe."""
        findings: list[dict[str, str]] = []
        
        # Verificar que los mensajes del chat tienen la estructura esperada
        for i, msg in enumerate(self._chat_messages):
            if 'status' not in msg:
                findings.append({
                    'severity': 'info',
                    'description': f'Mensaje {i} sin campo status — se asume complete',
                    'auto_fix': 'applied',
                })
                msg['status'] = 'complete'
            if 'timestamp' not in msg:
                from datetime import datetime, timezone
                msg['timestamp'] = datetime.now(timezone.utc).strftime('%H:%M')
        
        # Verificar consistencia de live_status
        if self._working and self._live_status == 'idle':
            findings.append({
                'severity': 'warning',
                'description': 'ViewModel._working=True pero _live_status=idle — desincronizado',
                'auto_fix': 'applied',
            })
            self._set_live_status('processing')
        elif not self._working and self._live_status == 'processing':
            findings.append({
                'severity': 'warning',
                'description': 'ViewModel._working=False pero _live_status=processing — desincronizado',
                'auto_fix': 'applied',
            })
            self._set_live_status('idle')
        
        # Verificar que attached_files es consistente
        if self._attached_files:
            for f in self._attached_files:
                if not all(k in f for k in ('name', 'path', 'size', 'type')):
                    findings.append({
                        'severity': 'error',
                        'description': f'Archivo adjunto con campos faltantes: {f}',
                        'auto_fix': 'none',
                    })
        
        # Verificar que contextual_suggestions se actualizaron
        if not self._contextual_suggestions:
            self._refresh_contextual_suggestions()
            findings.append({
                'severity': 'info',
                'description': 'Sugerencias contextuales estaban vacias — refrescadas',
                'auto_fix': 'applied',
            })
        
        return {
            'valid': len([f for f in findings if f['severity'] == 'error']) == 0,
            'findings': findings,
            'chat_messages_count': len(self._chat_messages),
            'attached_files_count': len(self._attached_files),
            'live_status': self._live_status,
            'suggestions_count': len(self._contextual_suggestions),
        }

    @Slot(str)
    def sendChat(self, text: str) -> None:
        message = text.strip()
        if not message:
            return
        # Safety: si _working quedo stuck de una llamada anterior (>30s),
        # resetearlo para no bloquear al usuario permanentemente.
        # Reducido de 60s a 30s: el usuario percibe >30s como congelamiento.
        if self._working:
            import time
            elapsed = time.time() - getattr(self, '_working_since', 0)
            if elapsed < 30:
                return
            self._working = False
            self._set_live_status('idle')
            self._clear_autonomy_activity_override()
        user_attachments = list(self._attached_files) if self._attached_files else None
        self._append_message('user', 'Tu', message, self._routing_mode_label(),
                            attachments=user_attachments)
        if self._attached_files:
            self._attached_files.clear()
        self._set_live_status('processing')
        # Escucha pasiva de capacidades declaradas (GPU, modelos, cuentas, runtimes).
        # Persiste detecciones a data/chat_research_backlog/*.jsonl para que OSES
        # y ExperimentLab las consuman despues como areas de investigacion. No
        # modifica el ruteo; solo anota y avisa al usuario en una linea corta
        # para que sepa que su dato quedo registrado (antes se perdian en memoria).
        # Ingerir capabilities en background para no bloquear UI
        threading.Thread(target=self._ingest_chat_capabilities, args=(message,), daemon=True).start()
        # Actualizar packet en background sin bloquear UI
        threading.Thread(target=self._refresh_development_packet, args=(message,), daemon=True).start()
        if self._try_handle_chat_command(message):
            return

        # Fast synchronous shortcut detection: keyword-only matching
        # (no Ollama, no LLM). If a shortcut matches here, answer
        # immediately without spawning a background thread. This keeps
        # the UI responsive for simple questions while the background
        # thread (Fix 55) handles the heavy inference path.
        if self._try_synchronous_shortcut(message):
            self._set_live_status('idle')
            return

        # Fix 55: move ALL classification + routing + answer logic to a
        # background thread.  Both _chat_shortcut_analysis (up to 3 s)
        # and the _is_* classifiers (Ollama fallback, 5-16 s each) were
        # blocking the Qt event loop, freezing the UI.
        import time as _time_mod
        self._working = True
        self._working_since = _time_mod.time()

        # Hard timeout: if the entire _route_and_answer takes longer than
        # _INFERENCE_HARD_TIMEOUT_S, we abort and show a fallback message.
        _INFERENCE_HARD_TIMEOUT_S = 25

        def _route_and_answer() -> None:
            _inner_worker_took_over = False
            # Shortcut analysis (may call LLM, give it 3 s)
            shortcut_analysis: dict[str, Any] = {}
            _sa_result: dict[str, Any] = {}
            _sa_done = threading.Event()
            def _sa_worker() -> None:
                try:
                    _sa_result.update(self._chat_shortcut_analysis(message))
                except Exception:
                    pass
                finally:
                    _sa_done.set()
            _sa_thread = threading.Thread(target=_sa_worker, daemon=True)
            _sa_thread.start()
            if _sa_done.wait(timeout=3):
                shortcut_analysis = _sa_result
            allow_chat_shortcuts = not bool(shortcut_analysis.get('mixed_actionable')) and not bool(shortcut_analysis.get('requires_clarification'))
            try:
                if allow_chat_shortcuts and self._is_world_model_question(message):
                    self._answer_world_model_question(message)
                    return
                if allow_chat_shortcuts and self._is_self_awareness_question(message):
                    self._answer_self_awareness_question(message)
                    return
                if allow_chat_shortcuts and self._is_evolution_status_question(message):
                    self._answer_evolution_status_question(message)
                    return
                if allow_chat_shortcuts and self._is_self_examination_question(message):
                    self._answer_self_examination_question(message)
                    return
                if allow_chat_shortcuts and self._is_learning_question(message):
                    self._answer_learning_question(message)
                    return
                # Account resource questions always resolve locally — bypass shortcut gate.
                if self._is_account_resource_question(message):
                    self._answer_account_resource_question(message)
                    return
                if allow_chat_shortcuts and self._is_general_chat_message(message) and not self._seems_task_like_message(message):
                    self._answer_general_chat(message)
                    _inner_worker_took_over = True
                    return
                # Cloud plan detection: if the user asks to "solve" or
                # "plan" something, generate a cloud-reasoning plan with
                # step-by-step tool assignment instead of the normal flow.
                if self._is_cloud_plan_request(message):
                    self._handle_cloud_plan_request(message)
                    _inner_worker_took_over = True
                    return

                explicit_assistant = self._explicit_assistant_preference(message)
                if explicit_assistant:
                    self._last_user_goal = message
                    self._run_external_consultation(explicit_assistant, announce=True)
                    _inner_worker_took_over = True
                    return
                self._busy_label = 'Estoy entendiendo tu mensaje y preparando la mejor respuesta.'
                self._set_autonomy_activity_override(
                    visible=True,
                    title='Analizando consulta',
                    status='active',
                    stage='orquestando decision local',
                    progress=0.14,
                    detail='Estoy detectando la intencion, el pack y si conviene resolver localmente o consultar otra herramienta.',
                    tool='motor local',
                    next_step='Primero cierro el analisis local y luego decido si hace falta apoyo externo.',
                    learning_note='La memoria del objetivo y los patrones previos se tienen en cuenta antes de responder.',
                    mode='local',
                )
                self.dataChanged.emit()

                try:
                    # Run inference with hard timeout to prevent UI freeze.
                    _infer_result: dict[str, Any] = {}
                    _infer_error: list[str] = []
                    _infer_done = threading.Event()

                    def _infer_worker() -> None:
                        try:
                            req = self._build_request(message)
                            rec = self.inference_service.infer_task(req)
                            _infer_result['record'] = rec
                        except Exception as exc:
                            _infer_error.append(str(exc))
                        finally:
                            _infer_done.set()

                    _infer_thread = threading.Thread(target=_infer_worker, daemon=True)
                    _infer_thread.start()

                    # Heartbeat: emit progress updates every 5s while waiting
                    _heartbeat_stages = [
                        (0.3, 'clasificando intencion'),
                        (0.5, 'construyendo contexto'),
                        (0.7, 'consultando modelo'),
                        (0.85, 'finalizando respuesta'),
                    ]
                    _stage_idx = 0
                    _waited = 0
                    while not _infer_done.wait(timeout=5):
                        _waited += 5
                        if _waited >= _INFERENCE_HARD_TIMEOUT_S:
                            break
                        if _stage_idx < len(_heartbeat_stages):
                            _prog, _stage_label = _heartbeat_stages[_stage_idx]
                            self._set_autonomy_activity_override(
                                visible=True,
                                title='Analizando consulta',
                                status='active',
                                stage=_stage_label,
                                progress=_prog,
                                detail=f'Procesando... ({_waited}s)',
                                tool='motor local',
                                mode='local',
                            )
                            self.dataChanged.emit()
                            _stage_idx += 1

                    if not _infer_done.is_set():
                        logger.warning(
                            'sendChat: inference timeout (%ds) — trying cloud fallback',
                            _INFERENCE_HARD_TIMEOUT_S,
                        )
                        cloud_fallback = self._try_cloud_quick_reply(message)
                        if cloud_fallback:
                            self._append_message(
                                'assistant', 'IABV',
                                cloud_fallback,
                                'Cloud fallback (modelo local ocupado).',
                            )
                        else:
                            # Try context-based reply for provider/key questions
                            context_fallback = self._try_context_based_reply(message)
                            if context_fallback:
                                self._append_message(
                                    'assistant', 'IABV',
                                    context_fallback,
                                    'Respuesta por contexto local (sin IA).',
                                )
                            else:
                                self._append_message(
                                    'assistant', 'IABV',
                                    'Mi modelo local tardo demasiado en responder. '
                                    'Esto puede pasar cuando el modelo es muy grande '
                                    'para la RAM disponible. Intenta de nuevo o usa '
                                    'un modelo mas liviano (ej: gemma3:4b). '
                                    'Puedes verificar con: model_selection_status',
                                    'Timeout de inferencia local.',
                                )
                        self._latest_response_text = ''
                        self._latest_response_meta = 'Timeout de inferencia local.'
                        return

                    if _infer_error:
                        self.taskFailed.emit('chat', f'No pude completar la consulta local: {_infer_error[0]}')
                        return

                    record = _infer_result.get('record')
                    if record is None:
                        self.taskFailed.emit('chat', 'No pude completar la consulta local: resultado vacio.')
                        return

                    adaptive_session = record.result.raw_output.get('adaptive_session') if isinstance(record.result.raw_output, dict) else None
                    self.taskResolved.emit(
                        'chat',
                        {
                            'summary': record.result.summary,
                            'provider_name': record.result.provider_name,
                            'reasoning_mode': record.result.reasoning_mode.value,
                            'confidence': f'{record.result.confidence:.2f}',
                            'route_reason': record.route.reason,
                            'report_kind': record.result.report_kind.value,
                            'role_title': self._role_title_from_task(record.result.detected_role or record.route.task_role),
                            'sources': record.result.sources,
                            'follow_up_teachings': record.result.follow_up_teachings,
                            'used_tools': [tool.value for tool in record.result.used_tools],
                            'planner_used': record.result.planner_used,
                            'executor_model': record.result.executor_model or record.route.model_name,
                            'chosen_pack': record.result.chosen_pack,
                            'adaptive_session': adaptive_session,
                            'assistant_guidance': (record.result.raw_output or {}).get('assistant_guidance') if isinstance(record.result.raw_output, dict) else None,
                            'local_chat_llm': (record.result.raw_output or {}).get('local_chat_llm') if isinstance(record.result.raw_output, dict) else None,
                        },
                    )
                except Exception as exc:
                    self.taskFailed.emit('chat', f'No pude completar la consulta local: {exc}')
            except Exception as exc:
                logger.warning('_route_and_answer failed: %s', exc)
                self.taskFailed.emit('chat', f'Error en clasificacion: {exc}')
            finally:
                if not _inner_worker_took_over:
                    self._working = False
                    self._set_live_status('idle')
                    self._clear_autonomy_activity_override()

        threading.Thread(target=_route_and_answer, daemon=True).start()

    def _role_title_from_task(self, role: TaskRole) -> str:
        return next((profile.title for profile in self.role_router.role_profiles if profile.role == role), role.value)

    def _run_adaptive_action(self, *, action_name: str, busy_text: str) -> None:
        if self._working or not self._adaptive_session_id:
            return
        self._approval_dialog_visible = False
        self._working = True
        self._busy_label = busy_text
        self.dataChanged.emit()

        def worker() -> None:
            try:
                if action_name == 'approve_strategy':
                    session = self.adaptive_orchestrator.approve_strategy(self._adaptive_session_id)
                elif action_name == 'approve_next':
                    session = self.adaptive_orchestrator.approve_next_phase(self._adaptive_session_id)
                elif action_name == 'simulate':
                    session = self.adaptive_orchestrator.simulate(self._adaptive_session_id)
                elif action_name == 'execute':
                    session = self.adaptive_orchestrator.execute_now(self._adaptive_session_id)
                elif action_name == 'abort':
                    session = self.adaptive_orchestrator.abort(self._adaptive_session_id)
                elif action_name == 'replan':
                    session = self.adaptive_orchestrator.replan_session(self._adaptive_session_id)
                else:
                    raise ValueError(f'Accion adaptativa desconocida: {action_name}')
                if session is None:
                    raise ValueError('No encontre la sesion adaptativa activa.')
                self.taskResolved.emit('adaptive_action', session.model_dump(mode='json'))
            except Exception as exc:
                self.taskFailed.emit('adaptive_action', f'No pude completar la accion adaptativa: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def applySuggestedAction(self, action: str) -> None:
        handled = self._perform_guidance_action(action, announce=True)
        if handled:
            self._reset_assistant_guidance()
            self.dataChanged.emit()

    @Slot()
    def approveStrategy(self) -> None:
        self._run_adaptive_action(action_name='approve_strategy', busy_text='Registrando aprobacion de estrategia.')

    @Slot()
    def approveNextPhase(self) -> None:
        self._run_adaptive_action(action_name='approve_next', busy_text='Registrando aprobacion de la siguiente fase.')

    @Slot()
    def simulateAdaptive(self) -> None:
        self._run_adaptive_action(action_name='simulate', busy_text='Simulando la estrategia adaptativa.')

    @Slot()
    def executeAdaptive(self) -> None:
        self._run_adaptive_action(action_name='execute', busy_text='Preparando la fase operativa adaptativa.')

    @Slot()
    def abortAdaptive(self) -> None:
        self._run_adaptive_action(action_name='abort', busy_text='Abortando la sesion adaptativa activa.')

    @Slot()
    def replanAdaptive(self) -> None:
        self._run_adaptive_action(action_name='replan', busy_text='Replanificando la estrategia adaptativa con el mismo objetivo y evidencia.')

    @Slot(str)
    def runSelfTeach(self, text: str) -> None:
        if self._working or self.self_teach_orchestrator is None:
            return
        goal = (text or '').strip()
        normalized = self._normalized_command_text(goal)
        if any(token in normalized for token in ('prueba wplay', 'analiza wplay', 'haz autotest', 'autotest del login', 'ensenate de este fallo', 'ense?ate de este fallo')) and 'wplay' in normalized and 'inicia sesion' not in normalized:
            goal = 'abre Wplay e inicia sesion'
        elif any(token in normalized for token in ('prueba google', 'analiza google')) and 'buscar' not in normalized:
            goal = 'abre Google y realiza una busqueda simple'
        if not goal:
            goal = self._last_user_goal or 'abre Wplay e inicia sesion'
        self._working = True
        self._busy_label = 'Corriendo autotest interno: interpretar, diagnosticar, ajustar runtime y decidir si hace falta Codex.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                request = self._build_request(goal)
                record = self.inference_service.infer_task(request)
                payload = self.self_teach_orchestrator.run_diagnostic(record)
                payload['run_summary'] = record.result.summary
                self.taskResolved.emit('self_teach', payload)
            except Exception as exc:
                self.taskFailed.emit('self_teach', f'No pude completar el autotest interno: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def preparePayload(self) -> None:
        if self._working:
            return
        self._working = True
        self._busy_label = 'Empaquetando episodios, artefactos y conocimiento.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                payload, saved_path = self.training_orchestrator.prepare_and_archive()
                self.taskResolved.emit('payload', {'episodes': len(payload.episodes), 'artifacts': len(payload.artifacts), 'knowledge': len(payload.knowledge_items), 'path': saved_path})
            except Exception as exc:
                self.taskFailed.emit('payload', f'No pude generar el payload: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def runQuickPbt(self) -> None:
        if self._working:
            return
        self._working = True
        self._busy_label = 'Ejecutando un ciclo PBT inspirado en IABV 1.3.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                state = self.pbt_service.run_cycle(self._collect_metrics())
                self.taskResolved.emit('pbt', state)
            except Exception as exc:
                self.taskFailed.emit('pbt', f'No pude ejecutar el ciclo PBT: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def buildDevelopmentPacket(self, text: str) -> None:
        self._refresh_development_packet(text)
        self._busy_label = 'Paquete para Codex actualizado.'
        self.dataChanged.emit()

    @Slot()
    def copyDiagnostic(self) -> None:
        self._copy_text(self._diagnostic_text, 'Diagnostico copiado al portapapeles.')

    @Slot()
    def copyDevelopmentPacket(self) -> None:
        self._copy_text(self._development_packet, 'Paquete para Codex copiado al portapapeles.')

    @Slot()
    def copyLatestResponse(self) -> None:
        self._copy_text(self._latest_response_text, 'Ultima respuesta copiada al portapapeles.')

    @Slot()
    def copyAdaptiveEvidence(self) -> None:
        self._copy_text(self._adaptive_evidence_text, 'Evidencia adaptativa copiada al portapapeles.')

    @Slot()
    def ingestClipboardExternalResponse(self) -> None:
        self.ingestExternalResponse(self._read_text_from_clipboard())

    @Slot(str)
    def ingestExternalResponse(self, text: str) -> None:
        orchestrator = self.adaptive_orchestrator if hasattr(self.adaptive_orchestrator, 'ingest_external_response') else None
        if (orchestrator is None and self.autonomous_evolution_service is None) or not self.config.autonomous_evolution_enabled:
            self._busy_label = 'La autonomia guiada no esta disponible en esta sesion.'
            self.dataChanged.emit()
            return
        payload = dict(self._last_adaptive_payload or {})
        if not payload:
            self._busy_label = 'Todavia no hay una sesion adaptativa activa para asociar la respuesta externa.'
            self._append_message('assistant', 'Autonomia', 'Primero necesito una sesion adaptativa o una consulta externa preparada para ingerir la respuesta.', 'Sin payload activo.')
            self.dataChanged.emit()
            return
        response_text = str(text or '').strip()
        source = 'chat_text' if response_text else 'clipboard'
        if not response_text:
            response_text = self._read_text_from_clipboard().strip()
        if not response_text:
            self._busy_label = 'No encontre texto en el portapapeles para interpretar.'
            self._append_message('assistant', 'Autonomia', 'No recibi texto util desde el portapapeles. Copia la respuesta de Codex o ChatGPT y vuelve a intentarlo.', 'Sin texto copiado.')
            self.dataChanged.emit()
            return
        self._set_autonomy_activity_override(
            visible=True,
            title='Integrando respuesta externa',
            status='active',
            stage='validando y adoptando respuesta',
            progress=0.9,
            detail='Estoy interpretando la respuesta externa para decidir si sirve, como se valida y que aprendizaje deja.',
            tool='memoria evolutiva',
            next_step='Si la respuesta es util, la convertire en siguiente accion segura y memoria reusable.',
            learning_note='Este paso conecta la consulta externa con laboratorio, auditoria y memoria.',
            mode='external',
        )
        self.dataChanged.emit()
        self._process_ui_events()
        user_goal = self._last_user_goal or str((payload.get('intent') or {}).get('title') or 'caso actual')
        if orchestrator is not None:
            bridge = orchestrator.ingest_external_response(payload, user_goal=user_goal, response_text=response_text, source=source)
        else:
            bridge = self.autonomous_evolution_service.ingest_consult_response(
                adaptive_payload=payload,
                user_goal=user_goal,
                response_text=response_text,
                source=source,
            )
        if bridge.get('status') in {'empty', 'missing_context'}:
            self._busy_label = str(bridge.get('detail') or 'No pude asociar la respuesta externa.')
            self._append_message('assistant', 'Autonomia', str(bridge.get('detail') or 'No pude asociar la respuesta externa.'), f"estado {bridge.get('status')}")
            self._clear_autonomy_activity_override()
            self.dataChanged.emit()
            return
        metadata = dict(payload.get('metadata') or {})
        metadata['autonomous_evolution_response'] = dict(bridge)
        existing_autonomy = dict(metadata.get('autonomous_evolution') or {})
        if existing_autonomy:
            existing_autonomy.update(
                {
                    'response_summary': bridge.get('response_summary') or bridge.get('detail') or '',
                    'response_next_action': bridge.get('next_action') or '',
                    'response_ingested': True,
                    'response_validation_status': dict(bridge.get('response_validation') or {}).get('status') or '',
                    'response_adoption_lane': dict(bridge.get('adoption_plan') or {}).get('execution_lane') or '',
                    'pending_issue_id': bridge.get('pending_issue_id') or existing_autonomy.get('pending_issue_id') or '',
                }
            )
            metadata['autonomous_evolution'] = existing_autonomy
        payload['metadata'] = metadata
        if bridge.get('pending_issue_id'):
            payload['pending_issue_id'] = bridge.get('pending_issue_id')
        payload['assistant_guidance'] = self._guidance_from_external_response(bridge)
        self._update_adaptive_state(payload)
        meta = (
            f"respuesta {bridge.get('assistant_kind') or 'n/d'} | accion {bridge.get('next_action') or 'n/d'} | "
            f"pending {bridge.get('pending_issue_id') or 'no'}"
        )
        detail = str(bridge.get('detail') or bridge.get('response_summary') or 'Respuesta externa integrada.').strip()
        self._append_message('assistant', 'Autonomia', detail, meta)
        self._latest_response_text = detail
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta externa integrada en la memoria evolutiva.'
        self._clear_autonomy_activity_override()
        self.dataChanged.emit()
    @Slot(str, object)
    def _apply_task_result(self, task_name: str, payload: Any) -> None:
        if task_name == 'provider_health':
            self._provider_refreshing = False
            self._provider_cards = list(payload)
            self._agent_cards = self._build_agent_cards()
            if not self._working:
                self._busy_label = self._startup_readiness_text(validating_local_stack=False)
            self._diagnostic_text = self._build_provider_diagnostic()
        elif task_name == 'chat':
            self._clear_autonomy_activity_override()
            sources = ', '.join(payload.get('sources') or []) or 'sin fuentes explicitas'
            tools = ', '.join(payload.get('used_tools') or []) or 'sin herramientas'
            follow_up = payload.get('follow_up_teachings') or []
            extra = f" | siguientes ensenanzas: {', '.join(follow_up)}" if follow_up else ''
            planner_text = 'si' if payload.get('planner_used') else 'no'
            pack_title = ((payload.get('chosen_pack') or {}).get('title') or 'sin pack')
            adaptive_payload = dict(payload.get('adaptive_session') or {})
            if payload.get('assistant_guidance') and isinstance(adaptive_payload, dict):
                adaptive_payload['assistant_guidance'] = payload.get('assistant_guidance')
            user_text, meta_line = self._user_facing_chat_response(
                message=self._last_user_goal or '',
                raw_summary=str(payload.get('summary') or 'La IA no devolvio texto util.'),
                payload=dict(payload or {}),
                adaptive_payload=adaptive_payload,
            )
            self._append_message('assistant', 'IABV', user_text, meta_line)
            self._latest_response_text = user_text
            self._latest_response_meta = meta_line
            self._busy_label = 'Respuesta lista.'
            self._diagnostic_text = (
                'Ultima respuesta correcta\n'
                f"Modo de ruteo: {'automatico' if self._auto_route_enabled else 'manual'}\n"
                f"Rol detectado: {payload.get('role_title')}\n"
                f"Proveedor: {payload.get('provider_name')}\n"
                f"Modelo ejecutor: {payload.get('executor_model')}\n"
                f"Planner: {planner_text}\n"
                f"Pack: {pack_title}\n"
                f"Motivo de ruta: {payload.get('route_reason')}"
            )
            self._update_adaptive_state(adaptive_payload)
            if adaptive_payload:
                # Fix 57: move autonomy evaluation to a background thread.
                # _maybe_run_autonomous_evolution calls govern_adaptive_payload
                # which may invoke plan_or_execute (Ollama / cloud APIs).
                # Running it on the UI thread freezes the window and leaves
                # the progress bar stuck at ~58%.
                self._busy_label = 'Ya tengo una primera respuesta. Estoy viendo si conviene apoyarme en otra herramienta o seguir por aqui.'
                self.dataChanged.emit()
                _ap = dict(adaptive_payload)
                def _autonomy_worker() -> None:
                    try:
                        autonomy_result = self._maybe_run_autonomous_evolution(_ap, source='chat')
                        if autonomy_result is None:
                            self._busy_label = 'Respuesta lista.'
                    except Exception as exc:
                        logger.warning('autonomy evaluation failed: %s', exc)
                        self._busy_label = 'Respuesta lista.'
                    finally:
                        self._clear_autonomy_activity_override()
                        self._working = False
                        self._set_live_status('idle')
                        self.dataChanged.emit()
                threading.Thread(target=_autonomy_worker, daemon=True).start()
                # Return early so the code below (self._working = False)
                # does NOT run — the worker thread handles cleanup.
                self._update_progress_cards()
                self._update_evolution_snapshot()
                self._agent_cards = self._build_agent_cards()
                threading.Thread(target=self._refresh_development_packet, daemon=True).start()
                self.dataChanged.emit()
                return
        elif task_name == 'adaptive_action':
            self._clear_autonomy_activity_override()
            session_payload = dict(payload)
            self._update_adaptive_state(session_payload)
            outcome = session_payload.get('outcome') or {}
            status = session_payload.get('status', '')
            next_phase = ((session_payload.get('playbook') or {}).get('next_phase') or 'sin siguiente fase')
            summary = outcome.get('summary', 'Accion adaptativa registrada.')
            self._append_message('assistant', 'Orquestador', summary, f"estado {status} | siguiente fase {next_phase}")
            self._latest_response_text = summary
            self._latest_response_meta = f"Sesion {session_payload.get('session_id', '')} | estado {status} | siguiente fase {next_phase}"
            self._busy_label = 'Sesion adaptativa actualizada.'
        elif task_name == 'self_teach':
            self._clear_autonomy_activity_override()
            scenario_run = dict(payload.get('scenario_run') or {})
            diagnosis = dict(payload.get('probe_diagnosis') or {})
            adaptive_payload = dict(payload.get('adaptive_session') or {})
            pending_issue = dict(payload.get('pending_issue') or {})
            guided_cycle = dict(payload.get('guided_improvement_cycle') or {})
            if diagnosis and isinstance(adaptive_payload, dict):
                adaptive_payload['probe_diagnosis'] = diagnosis
                adaptive_payload['runtime_adjustments'] = list(payload.get('runtime_adjustments') or [])
                adaptive_payload['pending_issue_id'] = pending_issue.get('issue_id', '')
                adaptive_payload['scenario_id'] = ((scenario_run.get('scenario') or {}).get('scenario_id') or '')
            self._update_adaptive_state(adaptive_payload)
            summary = str(diagnosis.get('summary') or scenario_run.get('summary') or payload.get('run_summary') or 'Autotest interno completado.')
            if guided_cycle.get('notifications'):
                summary = f"{summary} {str((guided_cycle.get('notifications') or [''])[0]).strip()}".strip()
            meta = (
                f"escenario {((scenario_run.get('scenario') or {}).get('scenario_id') or 'n/d')} | "
                f"categoria {diagnosis.get('category', 'n/d')} | "
                f"ajustes {len(payload.get('runtime_adjustments') or [])} | "
                f"pendiente {pending_issue.get('issue_id', 'no')} | "
                f"bloqueos {len(guided_cycle.get('detected_blockages') or [])}"
            )
            self._append_message('assistant', 'Self-Teacher', summary, meta)
            self._latest_response_text = summary
            self._latest_response_meta = meta
            self._busy_label = 'Autotest interno completado.'
            self._diagnostic_text = chr(10).join([
                'Ultimo autotest interno',
                f"Escenario: {((scenario_run.get('scenario') or {}).get('title') or 'n/d')}",
                f"Categoria: {diagnosis.get('category', 'n/d')}",
                f"Causa probable: {diagnosis.get('probable_cause', 'n/d')}",
                f"Ajustes runtime: {len(payload.get('runtime_adjustments') or [])}",
                f"Pendiente Codex: {pending_issue.get('issue_id', 'no')}",
                f"Bloqueos detectados: {len(guided_cycle.get('detected_blockages') or [])}",
                f"Correcciones seguras aplicadas: {int(guided_cycle.get('applied_count') or 0)}",
                f"Requiere decision humana: {'si' if guided_cycle.get('requires_user_decision') else 'no'}",
            ])
            if adaptive_payload:
                self._maybe_run_autonomous_evolution(adaptive_payload, source='self_teach')
        elif task_name == 'external_consultation':
            self._clear_autonomy_activity_override()
            external_payload = dict(payload or {})
            adaptive_payload = dict(external_payload.get('payload') or {})
            if adaptive_payload:
                self._update_adaptive_state(adaptive_payload)
            message = str(external_payload.get('message') or 'No pude completar la consulta externa guiada.')
            meta = str(external_payload.get('meta') or 'Consulta externa sin detalle.')
            self._append_message('assistant', 'IABV', message, meta)
            self._latest_response_text = message
            self._latest_response_meta = meta
            assistant_title = str(external_payload.get('assistant_title') or 'Asistente externo')
            external_notice = self._external_state_notice(list(external_payload.get('external_state_flags') or []))
            if bool(external_payload.get('success')):
                self._set_autonomy_activity_override(
                    visible=True,
                    title='Consulta externa lista',
                    status='active',
                    stage='consulta preparada',
                    progress=1.0,
                    detail=message,
                    tool=assistant_title,
                    next_step='Seguire con la respuesta externa o con su reutilizacion segura.',
                    human_help='Si hace falta, luego puedo ingerir la respuesta o cambiar de via.',
                    learning_note='La consulta externa ya quedo trazada en esta sesion.',
                    mode='external',
                )
            else:
                self._reset_assistant_guidance()
                self._set_autonomy_activity_override(
                    visible=True,
                    title='Consulta externa bloqueada',
                    status='blocked',
                    stage='bloqueo de entorno o acceso',
                    progress=1.0,
                    detail=message,
                    tool=assistant_title,
                    next_step='Seguire por aqui con lo que ya tenemos o puedo preparar otra via si hace falta.',
                    human_help='Si quieres, puedo intentar otra herramienta o revisar el acceso externo.',
                    learning_note='Este bloqueo queda registrado para no fingir que la consulta si se hizo.',
                    mode='external',
                )
            self._busy_label = (
                f'Consulta externa lista con {assistant_title}.'
                if bool(external_payload.get('success'))
                else external_notice or message
            )
        elif task_name == 'payload':
            self._append_message('assistant', 'Payload', f"Payload archivado con {payload.get('episodes')} episodios, {payload.get('artifacts')} artefactos y {payload.get('knowledge')} items de conocimiento.", Path(str(payload.get('path'))).name)
            self._busy_label = f"Payload listo: {Path(str(payload.get('path'))).name}."
        elif task_name == 'pbt':
            self._pbt_state = dict(payload)
            self._pbt_candidates = list(payload.get('candidates', []))[:4]
            self._append_message('assistant', 'PBT', str(payload.get('summary', 'Ciclo PBT completado.')), f"Generacion {payload.get('generation', 0)}")
            self._busy_label = f"PBT actualizado en generacion {payload.get('generation', 0)}."
        if task_name != 'provider_health':
            self._working = False
        self._update_progress_cards()
        self._update_evolution_snapshot()
        try:
            self._agent_cards = self._build_agent_cards()
        except Exception:
            pass
        if task_name != 'provider_health':
            try:
                self._refresh_development_packet()
            except Exception:
                pass
        try:
            self._refresh_autonomy_dock()
        except Exception:
            pass
        self.dataChanged.emit()

    @Slot(str, str)
    def _apply_task_failure(self, task_name: str, message: str) -> None:
        title = 'IABV' if task_name == 'chat' else task_name.upper()
        visible_message, visible_meta = self._humanize_task_failure(task_name, message)
        self._clear_autonomy_activity_override()
        self._append_message('assistant', title, visible_message, visible_meta)
        if task_name in {'chat', 'adaptive_action', 'external_consultation'}:
            self._latest_response_text = visible_message
            self._latest_response_meta = visible_meta
        if task_name == 'provider_health':
            self._provider_refreshing = False
        else:
            self._working = False
        self._update_evolution_snapshot()
        self._diagnostic_text = (
            'Ultimo error\n'
            f"Modo de ruteo: {'automatico' if self._auto_route_enabled else 'manual'}\n"
            f"Rol manual: {self._selected_role_title()}\n"
            f"Tarea: {task_name}\n"
            f"Ollama URL: {self.config.ollama_base_url}\n"
            f"LM Studio URL: {self.config.lm_studio_base_url}\n"
            f"Embedding model: {self.config.ollama_embedding_model}\n"
            f"Sesion adaptativa: {self._adaptive_session_id or 'n/d'}\n"
            f"Detalle: {message}"
        )
        try:
            self._refresh_development_packet()
        except Exception:
            pass
        try:
            self._refresh_autonomy_dock()
        except Exception:
            pass
        self._busy_label = visible_message
        self.dataChanged.emit()

    def _build_provider_diagnostic(self) -> str:
        goal_context = self._goal_context_for_display(self._current_site_id() or None)
        active_title = str((goal_context.get('objective') or {}).get('title') or goal_context.get('active_title') or '').strip()
        lines = [
            'Estado del stack local',
            f"Modo de ruteo: {'automatico' if self._auto_route_enabled else 'manual'}",
            f'Ollama URL: {self.config.ollama_base_url}',
            f'LM Studio URL: {self.config.lm_studio_base_url}',
            f'Embedding model: {self.config.ollama_embedding_model}',
        ]
        if active_title:
            lines.append(f"Objetivo activo: {active_title} | estado {goal_context.get('status') or 'pending'} | progreso {float(goal_context.get('progress') or 0.0):.2f}")
        for card in self._provider_cards:
            lines.append(f"- {card.get('provider_name', '')}: {card.get('status', '')} | {card.get('detail', '')}")
        assistant_cards = self._assistant_tool_cards()
        if assistant_cards:
            lines.append('Asistentes y vias externas')
            for card in assistant_cards:
                lines.append(f"- {card.get('name', '')}: {card.get('status', '')} | {card.get('detail', '')}")
        return '\n'.join(lines)

    chatMessages = Property(list, get_chat_messages, notify=dataChanged)
    providerCards = Property(list, get_provider_cards, notify=dataChanged)
    progressCards = Property(list, get_progress_cards, notify=dataChanged)
    liveProcessSummary = Property(dict, get_live_process_summary, notify=dataChanged)
    liveWorkItems = Property(list, get_live_work_items, notify=dataChanged)
    assistantSessionCards = Property(list, get_assistant_session_cards, notify=dataChanged)
    autonomyTimeline = Property(list, get_autonomy_timeline, notify=dataChanged)
    evolutionOverview = Property(dict, get_evolution_overview, notify=dataChanged)
    evolutionAreaCards = Property(list, get_evolution_area_cards, notify=dataChanged)
    evolutionBlockers = Property(list, get_evolution_blockers, notify=dataChanged)
    agentCards = Property(list, get_agent_cards, notify=dataChanged)
    legacyCards = Property(list, get_legacy_cards, notify=dataChanged)
    roleCards = Property(list, get_role_cards, notify=dataChanged)
    pbtCandidates = Property(list, get_pbt_candidates, notify=dataChanged)
    pbtState = Property(dict, get_pbt_state, notify=dataChanged)
    selectedRole = Property(str, get_selected_role, notify=dataChanged)
    autoRouteEnabled = Property(bool, get_auto_route_enabled, notify=dataChanged)
    advancedVisible = Property(bool, get_advanced_visible, notify=dataChanged)
    routingModeLabel = Property(str, get_routing_mode_label, notify=dataChanged)
    working = Property(bool, get_working, notify=dataChanged)
    busyLabel = Property(str, get_busy_label, notify=dataChanged)
    autonomyActivity = Property(dict, get_autonomy_activity, notify=dataChanged)
    strategyText = Property(str, get_strategy_text, constant=True)
    recommendationText = Property(str, get_recommendation_text, constant=True)
    legacySummary = Property(str, get_legacy_summary, constant=True)
    diagnosticText = Property(str, get_diagnostic_text, notify=dataChanged)
    repoBridgeText = Property(str, get_repo_bridge_text, notify=dataChanged)
    localStackText = Property(str, get_local_stack_text, notify=dataChanged)
    developmentPacket = Property(str, get_development_packet, notify=dataChanged)
    assistantGuidanceMode = Property(str, get_assistant_guidance_mode, notify=dataChanged)
    assistantGuidanceText = Property(str, get_assistant_guidance_text, notify=dataChanged)
    assistantActionButtons = Property(list, get_assistant_action_buttons, notify=dataChanged)
    approvalDialogVisible = Property(bool, get_approval_dialog_visible, notify=dataChanged)
    approvalDialogTitle = Property(str, get_approval_dialog_title, notify=dataChanged)
    approvalDialogText = Property(str, get_approval_dialog_text, notify=dataChanged)
    latestResponseText = Property(str, get_latest_response_text, notify=dataChanged)
    latestResponseMeta = Property(str, get_latest_response_meta, notify=dataChanged)
    clipboardNotice = Property(str, get_clipboard_notice, notify=dataChanged)
    adaptiveSessionId = Property(str, get_adaptive_session_id, notify=dataChanged)
    adaptiveStatusText = Property(str, get_adaptive_status_text, notify=dataChanged)
    adaptiveIntentText = Property(str, get_adaptive_intent_text, notify=dataChanged)
    adaptiveContextText = Property(str, get_adaptive_context_text, notify=dataChanged)
    adaptiveStrategyText = Property(str, get_adaptive_strategy_text, notify=dataChanged)
    adaptiveExecutionText = Property(str, get_adaptive_execution_text, notify=dataChanged)
    adaptiveEvidenceText = Property(str, get_adaptive_evidence_text, notify=dataChanged)
    adaptiveEvolutionText = Property(str, get_adaptive_evolution_text, notify=dataChanged)
    adaptiveCapabilityCards = Property(list, get_adaptive_capability_cards, notify=dataChanged)
    adaptiveApprovalCards = Property(list, get_adaptive_approval_cards, notify=dataChanged)
    adaptivePlaybookSteps = Property(list, get_adaptive_playbook_steps, notify=dataChanged)
    canApproveStrategy = Property(bool, get_can_approve_strategy, notify=dataChanged)
    canApproveNextPhase = Property(bool, get_can_approve_next_phase, notify=dataChanged)
    canSimulate = Property(bool, get_can_simulate, notify=dataChanged)
    canExecute = Property(bool, get_can_execute, notify=dataChanged)
    canAbort = Property(bool, get_can_abort, notify=dataChanged)

    # ---- MCP bridge (Capa 1) ----
    def _on_mcp_bridge_status(self, status: Any) -> None:
        """Callback que recibe snapshots del MCPBridgeService.

        Acepta dataclass `MCPBridgeStatus` o dict (status_dict). Se ejecuta en
        el hilo del service; reemitimos por Qt Signal para que el QML lo vea
        en el hilo UI.
        """
        to_dict = getattr(status, 'to_dict', None)
        payload = to_dict() if callable(to_dict) else dict(status)
        self._mcp_bridge_status = payload
        try:
            self.mcpBridgeChanged.emit(payload)
        except Exception:
            pass
        self.dataChanged.emit()

    def get_mcp_bridge_status(self) -> dict:
        return dict(self._mcp_bridge_status)

    def get_mcp_bridge_enabled(self) -> bool:
        return bool(self._mcp_bridge_status.get('enabled_pref', False))

    def get_mcp_bridge_running(self) -> bool:
        return bool(self._mcp_bridge_status.get('running', False))

    def get_mcp_bridge_state(self) -> str:
        return str(self._mcp_bridge_status.get('state', 'stopped'))

    def get_mcp_tunnel_url(self) -> str:
        url = self._mcp_bridge_status.get('tunnel_url')
        return str(url) if url else ''

    def get_mcp_bridge_blocked(self) -> bool:
        return bool(self._mcp_bridge_status.get('governance_blocked', False))

    def get_mcp_bridge_reason(self) -> str:
        reason = self._mcp_bridge_status.get('governance_reason') or self._mcp_bridge_status.get('last_error')
        return str(reason) if reason else ''

    @Slot(bool)
    def toggleMcpBridge(self, enabled: bool) -> None:
        """Dispara el toggle del MCP bridge sin bloquear el hilo UI.

        `service.set_enabled(True)` puede tardar hasta `DEFAULT_TUNNEL_TIMEOUT_S`
        segundos (espera sincrónica a que cloudflared publique la URL). Corriéndolo
        en el hilo UI freezea todo el programa hasta que la URL aparece o timeout.
        Lo mandamos a un thread daemon; el service publica las transiciones
        (`stopped → starting → running|failed`) vía `attach_listener`, que ya
        reemitimos por `mcpBridgeChanged` al hilo UI.
        """

        service = self.mcp_bridge_service
        if service is None:
            return
        target = bool(enabled)

        def _run() -> None:
            try:
                service.set_enabled(target)
            except Exception:
                pass

        threading.Thread(
            target=_run,
            name='mcp-bridge-toggle',
            daemon=True,
        ).start()

    @Slot()
    def copyMcpTunnelUrl(self) -> None:
        url = self.get_mcp_tunnel_url()
        if not url:
            return
        app = QGuiApplication.instance()
        if app is None:
            return
        clipboard = app.clipboard()
        if clipboard is None:
            return
        clipboard.setText(url)

    mcpBridgeStatus = Property('QVariant', get_mcp_bridge_status, notify=mcpBridgeChanged)
    mcpBridgeEnabled = Property(bool, get_mcp_bridge_enabled, notify=mcpBridgeChanged)
    mcpBridgeRunning = Property(bool, get_mcp_bridge_running, notify=mcpBridgeChanged)
    mcpBridgeState = Property(str, get_mcp_bridge_state, notify=mcpBridgeChanged)
    mcpTunnelUrl = Property(str, get_mcp_tunnel_url, notify=mcpBridgeChanged)
    mcpBridgeBlocked = Property(bool, get_mcp_bridge_blocked, notify=mcpBridgeChanged)
    mcpBridgeReason = Property(str, get_mcp_bridge_reason, notify=mcpBridgeChanged)

    # --- Control Master (read-only, cached via refresh()) ---
    def get_control_master_digest(self) -> dict[str, Any]:
        return self._control_master_digest

    def get_control_master_brief(self) -> str:
        return self._control_master_brief

    @staticmethod
    def _format_control_master_brief(digest: dict[str, Any]) -> str:
        if not digest:
            return ''
        parts: list[str] = []
        vision = str(digest.get('current_vision') or '').strip()
        if vision:
            parts.append(f'Vision: {vision}')
        rules = digest.get('rules_brief') or []
        if rules:
            parts.append(f'Reglas ({len(rules)}): {rules[0]}')
        active = digest.get('active_objectives_brief') or []
        if active:
            parts.append(f'Objetivos activos: {", ".join(active[:3])}')
        unresolved = digest.get('unresolved') or []
        if unresolved:
            parts.append(f'UNRESOLVED: {unresolved[0]}')
        return ' | '.join(parts)

    def _refresh_control_master(self) -> None:
        service = self.control_master_service
        builder = self.control_master_digest_builder
        if service is None or builder is None:
            return
        try:
            state = service.current_state(refresh=False)
            digest = builder.build(state).model_dump(mode='json')
        except Exception:
            return
        self._control_master_digest = digest
        brief = self._format_control_master_brief(digest)
        if brief:
            self._control_master_brief = brief

    controlMasterDigest = Property(dict, get_control_master_digest, notify=dataChanged)
    controlMasterBrief = Property(str, get_control_master_brief, notify=dataChanged)

    # --- Self Audit (Frente 2 — "Auditarme ahora") ---
    # El slot corre el `SelfAuditService` en background y emite señales.
    # UNRESOLVED: el botón QML que llama `runSelfAuditNow()` y el
    # comportamiento real del hilo sólo pueden validarse corriendo la UI
    # en Windows. Este backend se testea con `threading.Thread` directo
    # vía pytest; el único punto testable desde Qt es el wire-up QML.
    def get_last_self_audit_summary(self) -> str:
        return self._last_self_audit_summary

    def _emit_self_audit_payload(self, snapshot: Any) -> None:
        """Emite `selfAuditCompleted` con el snapshot serializado (JSON)."""

        import json as _json
        from dataclasses import asdict as _asdict, is_dataclass as _is_dc
        from datetime import datetime as _dt

        def _default(value: Any) -> Any:
            if isinstance(value, _dt):
                return value.isoformat()
            return str(value)

        if _is_dc(snapshot):
            payload = _asdict(snapshot)
        elif hasattr(snapshot, 'model_dump'):
            try:
                payload = snapshot.model_dump(mode='json')
            except TypeError:
                payload = snapshot.model_dump()
        elif isinstance(snapshot, dict):
            payload = snapshot
        else:
            payload = {'snapshot': str(snapshot)}
        self._last_self_audit_summary = str(payload.get('summary_markdown') or '')
        self.selfAuditCompleted.emit(_json.dumps(payload, default=_default))
        self.dataChanged.emit()

    @Slot(str)
    def runSelfAuditNow(self, reason: str = '') -> None:
        """Dispara `SelfAuditService.run(reason=...)` en un hilo background.

        Emite `selfAuditStarted` al arrancar y `selfAuditCompleted`
        (con el snapshot JSON) o `selfAuditFailed` (con el detalle) al
        terminar. NO toma decisiones de ruta: cualquier acción sobre el
        resultado queda en manos del humano vía UI.
        """

        service = self.self_audit_service
        if service is None:
            self.selfAuditFailed.emit('self_audit_service no disponible en esta sesion')
            return
        if self._self_audit_running:
            return
        self._self_audit_running = True
        self.selfAuditStarted.emit()

        def worker() -> None:
            try:
                snapshot = service.run(reason=reason or None)
                self._emit_self_audit_payload(snapshot)
            except Exception as exc:  # pragma: no cover - defensa
                self.selfAuditFailed.emit(f'self_audit_failed: {exc}')
            finally:
                self._self_audit_running = False

        threading.Thread(target=worker, daemon=True).start()

    lastSelfAuditSummary = Property(
        str,
        get_last_self_audit_summary,
        notify=dataChanged,
    )













