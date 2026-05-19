from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import os
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import threading
import time
import uuid
from typing import Any, ClassVar

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
from iabv_v15.ui.qt import QObject, Property, QGuiApplication, QTimer, Signal, Slot


class ControlCenterViewModel(QObject):
    # --- Timeout constants for worker threads (Sub-objective A) ---
    _CHAT_WORKER_TIMEOUT_S: float = 120.0
    _EXTERNAL_WORKER_TIMEOUT_S: float = 180.0
    _POST_RECAPTURE_RESPONSE_RETRY_TIMEOUT_S: float = 12.0

    # --- Terminal dispatch states (Sub-objective A) ---
    # Every dispatch MUST end in one of these states visible to the user.
    # --- Stale-result guard ---
    # Each worker receives a unique dispatch_id at spawn time.  The watchdog
    # and the worker itself check ``_active_dispatch_ids[task_name]`` before
    # emitting any signal.  If the id no longer matches (because a new
    # dispatch started or a timeout already fired), the emission is silently
    # discarded and an audit log entry is written.
    _TERMINAL_DISPATCH_STATES: frozenset[str] = frozenset({
        'success',
        'blocked_by_permission',
        'blocked_by_security_verification',
        'blocked_by_quota',
        'timeout',
        'cancelled',
        'failed_with_actionable_reason',
        'needs_human_handoff',
    })

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
    bridgeChatRequested = Signal(str)     # texto inyectado por UIBridgeServer

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
        chat_message_repository: Any | None = None,
        defer_initial_refresh: bool = False,
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
        self.chat_message_repository = chat_message_repository
        self._chat_session_id = _generate_chat_session_id()
        self._pending_capability_notice: list[str] = []
        self._last_reasoning_path: str = ''

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
        self._active_dispatch_ids: dict[str, str] = {}
        self._bg_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='ccvm-bg')
        atexit.register(self._shutdown_bg_pool)
        self._chat_messages: list[dict[str, str]] = []
        self._attached_files: list[dict[str, Any]] = []
        self._live_status: str = 'idle'
        self._contextual_suggestions: list[dict[str, Any]] = []
        self._chat_search_query: str = ''
        self._pbt_state: dict[str, Any] = {}
        self._pbt_candidates: list[dict[str, Any]] = []
        self._diagnostic_text = 'Diagnostico pendiente. La consola revisa el stack local automaticamente y puedes pedirme ajustes o aprobaciones por chat.'
        self._diagnostic_truth_state = 'unresolved'
        self._strategy_text = 'La consola adaptativa decide intencion, arma contexto, mide readiness, propone estrategia y deja checkpoints claros antes de ejecutar.'
        self._recommendation_text = 'qwen3:8b queda como motor principal, pero ahora el Centro de Control usa packs por dominio y aprobaciones por fases.'
        self._legacy_summary = 'Se mantiene lo mejor del legado: PBT y snapshots de IABV 1.3, captura persistente de IABV 1.4 y ahora una capa adaptativa auditable por encima.'
        self._repo_bridge_text = ''
        self._local_stack_text = ''
        self._last_user_goal = ''
        self._last_goal_context: dict[str, Any] = {}
        self._clipboard_notice = 'Todavia no se ha copiado nada al portapapeles.'
        self._development_packet = ''
        self._dev_packet_last_ts: float = 0.0
        self._dev_packet_cooldown_s: float = 30.0
        self._dev_packet_refresh_pending: bool = False
        self._latest_response_text = 'Todavia no hay respuesta final en esta sesion.'
        self._latest_response_meta = 'Cuando completes una consulta, aqui veras el rol detectado, el pack usado y si hubo aprobaciones.'
        self._last_external_failure_payload: dict[str, Any] = {}
        self._last_external_failure_ts: float = 0.0
        self._dock_skip_last_trace: dict[str, float] = {}
        self._approval_dialog_visible = False
        self._approval_dialog_title = 'Aprobacion requerida'
        self._approval_dialog_text = 'No hay aprobaciones pendientes.'
        self._assistant_guidance_mode = 'idle'
        self._assistant_guidance_text = 'Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex.'
        self._assistant_action_buttons: list[dict[str, str]] = []
        self._last_adaptive_payload: dict[str, Any] = {}
        self._active_incident_frame: dict[str, Any] | None = None
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
            'approve_observation': False,
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
        self.taskResolved.connect(self._apply_task_result)
        self.taskFailed.connect(self._apply_task_failure)
        self.bridgeChatRequested.connect(self._dispatch_bridge_chat)
        self._seed_messages()
        # Always defer heavy work to keep constructor fast and avoid
        # blocking the main thread (~3733ms measured).  Data loading
        # runs on _bg_pool via _deferred_initial_refresh.  Only
        # lightweight signal connections happen on main thread via
        # _deferred_heavy_init.
        if not self._working and not self._adaptive_session_id:
            self._busy_label = self._startup_readiness_text(validating_local_stack=True)
        QTimer.singleShot(0, self._deferred_heavy_init)
        QTimer.singleShot(250, self._deferred_initial_refresh)
        QTimer.singleShot(900, lambda: self._refresh_provider_health(announce=False))

    def _deferred_heavy_init(self) -> None:
        """Attach lightweight listeners that need main-thread affinity.

        Called via QTimer.singleShot(0) from __init__.  Heavy work
        (_seed_development_packet, DB queries, evolution snapshots)
        runs on _bg_pool in _deferred_initial_refresh — NOT here —
        so the event loop stays free for lazy VM prebuild.
        """
        if self.mcp_bridge_service is not None:
            try:
                self.mcp_bridge_service.attach_listener(self._on_mcp_bridge_status)
            except Exception:
                pass

    def _shutdown_bg_pool(self) -> None:
        """Gracefully shutdown the background thread pool on process exit."""
        self._bg_pool.shutdown(wait=False)

    def _deferred_initial_refresh(self) -> None:
        """Run initial data load on background thread to keep main thread free.

        Delegates to ``_refresh_all_data`` on ``_bg_pool`` so the event
        loop stays free for lazy VM prebuild.  This eliminates the code
        duplication that existed between refresh() and this method.
        """
        self._bg_pool.submit(self._refresh_all_data)

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
        loaded = self._load_previous_chat_history()
        if loaded:
            self._chat_messages = loaded
            return
        self._chat_messages = [
            {
                'role': 'assistant',
                'speaker': 'IABV',
                'text': 'Chat operativo listo. Describe tu objetivo y voy a detectar la intencion, el pack y el siguiente paso util sin preguntas genericas. Tambien puedes escribir mostrar avanzado, aprobar estrategia o revisar stack.',
                'meta': self._routing_mode_label(),
            }
        ]

    def _load_previous_chat_history(self) -> list[dict[str, Any]]:
        repo = self.chat_message_repository
        if repo is None:
            return []
        try:
            rows = repo.list_recent(limit=30)
            if not rows:
                return []
            messages: list[dict[str, Any]] = []
            for row in rows:
                msg: dict[str, Any] = {
                    'role': row['role'],
                    'speaker': row['speaker'],
                    'text': row['text'],
                    'meta': row.get('meta', ''),
                    'timestamp': row.get('created_at_utc', '')[:5],
                }
                if row.get('evidence_tag'):
                    msg['evidenceTag'] = row['evidence_tag']
                if row.get('reasoning_path'):
                    msg['reasoningPath'] = row['reasoning_path']
                messages.append(msg)
            repo.apply_retention()
            return messages
        except Exception:
            return []

    @staticmethod
    def _classify_evidence_tag(
        *,
        has_live_observation: bool = False,
        has_persisted_evidence: bool = False,
    ) -> str:
        """Return ``'observed'``, ``'inferred'`` or ``'unresolved'``.

        - **observed**: the reply is backed by live runtime data (WorldModel,
          EnvironmentSelfModel, active window scan, real-time tool probe).
        - **inferred**: the reply is derived from persisted evidence (OSES
          findings, ExperimentLab history, learning records, portable context).
        - **unresolved**: neither live observation nor persisted evidence could
          confirm the claim — the system is honest about the gap.
        """
        if has_live_observation:
            return 'observed'
        if has_persisted_evidence:
            return 'inferred'
        return 'unresolved'

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
                        reasoning: str = '',
                        evidence_tag: str = '',
                        reasoning_path: str = '',
                        trace_metadata: dict[str, Any] | None = None) -> None:
        msg: dict[str, Any] = {'role': role, 'speaker': speaker, 'text': text, 'meta': meta,
                               'status': status, 'timestamp': datetime.now(timezone.utc).strftime('%H:%M')}
        if attachments:
            msg['attachments'] = attachments
        if code_blocks:
            msg['codeBlocks'] = code_blocks
        if reasoning:
            msg['reasoning'] = reasoning
        if evidence_tag in ('observed', 'inferred', 'unresolved'):
            msg['evidenceTag'] = evidence_tag
        effective_reasoning_path = reasoning_path or self._last_reasoning_path
        if effective_reasoning_path:
            msg['reasoningPath'] = effective_reasoning_path
        with self._ui_state_lock:
            self._chat_messages.append(msg)
            self._chat_messages = self._chat_messages[-30:]
        self._persist_chat_message(
            role=role, speaker=speaker, text=text, meta=meta,
            evidence_tag=evidence_tag,
            reasoning_path=effective_reasoning_path,
            trace_metadata=trace_metadata,
        )
        self._last_reasoning_path = ''
        self._refresh_contextual_suggestions()
        self._validate_ui_reflects_reality()

    def _persist_chat_message(
        self,
        *,
        role: str,
        speaker: str,
        text: str,
        meta: str,
        evidence_tag: str,
        reasoning_path: str,
        trace_metadata: dict[str, Any] | None,
    ) -> None:
        repo = self.chat_message_repository
        if repo is None:
            return
        try:
            repo.save(
                chat_session_id=self._chat_session_id,
                role=role,
                speaker=speaker,
                text=text,
                meta=meta,
                evidence_tag=evidence_tag,
                reasoning_path=reasoning_path,
                metadata=trace_metadata,
            )
        except Exception:
            pass

    def _record_chat_audit(
        self,
        *,
        reasoning_path: str,
        provider_id: str = 'local',
        model_used: str = '',
        latency_ms: float = 0.0,
        outcome: Any = None,
        user_goal: str = '',
        confidence: float = 0.0,
        error_detail: str = '',
        metadata: dict[str, Any] | None = None,
    ) -> None:
        trail = getattr(self, 'decision_audit_trail', None)
        if trail is None:
            return
        try:
            from iabv_v15.services.evolution.decision_audit_trail import DecisionOutcome
            if outcome is None:
                outcome = DecisionOutcome.SUCCESS
            trail.record_chat_routing(
                reasoning_path=reasoning_path,
                provider_id=provider_id,
                model_used=model_used,
                latency_ms=latency_ms,
                outcome=outcome,
                user_goal=user_goal,
                confidence=confidence,
                error_detail=error_detail,
                metadata=metadata,
            )
        except Exception:
            pass

    def _count_payloads(self) -> int:
        payload_dir = Path(self.config.payloads_dir)
        return len(list(payload_dir.glob('*.json'))) if payload_dir.exists() else 0

    def _collect_metrics(self) -> dict[str, int]:
        return {
            'episodes': self.episode_repository.count(),
            'knowledge': self.knowledge_repository.count(),
            'artifacts': self.artifact_repository.count(),
            'runs': self.run_repository.count(),
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
            'que puedes ver en mi pantalla',
            'qué puedes ver en mi pantalla',
            'que ves en mi pantalla',
            'qué ves en mi pantalla',
            'puedes ver mi pantalla',
            'puedes ver los navegadores que tengo',
            'puedes ver que navegadores tengo',
            'que navegadores tengo abiertos',
            'qué navegadores tengo abiertos',
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
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_about_windows = any(token in word_tokens for token in ('ventana', 'ventanas', 'foco', 'abierto', 'abiertas'))
        asks_about_screen = any(token in word_tokens for token in ('pantalla', 'monitor', 'monitores', 'escritorio'))
        asks_about_browsers = (
            any(token in word_tokens for token in ('navegador', 'navegadores', 'browser', 'browsers', 'chrome', 'edge', 'firefox', 'opera', 'brave'))
            and any(token in word_tokens for token in ('ver', 'ves', 'abierto', 'abiertos', 'tengo', 'tienes'))
        )
        asks_about_network = any(token in word_tokens for token in ('internet', 'red', 'conexion', 'conexión'))
        asks_about_live_tool = (
            any(token in word_tokens for token in ('codex', 'chatgpt', 'claude', 'ollama'))
            and any(token in word_tokens for token in ('responde', 'bloqueado', 'hilo', 'mensajes', 'agotados', 'abierto', 'abierta'))
        )
        asks_current_state = any(phrase in normalized for phrase in ('que esta pasando', 'qué está pasando'))
        return asks_about_windows or asks_about_screen or asks_about_browsers or asks_about_network or asks_about_live_tool or asks_current_state

    def _is_self_awareness_question(self, message: str) -> bool:
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
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_system_state = any(token in word_tokens for token in ('entorno', 'arquitectura', 'herramienta', 'herramientas', 'ias', 'ia', 'estado', 'conexiones'))
        asks_directly = any(token in normalized for token in ('conoces', 'sabes', 'tienes', 'disponibles', 'te conectas', 'te puedes conectar', 'consciente', 'que tan bien', 'como estas', 'cómo estás'))
        return asks_system_state and asks_directly

    def _is_learning_question(self, message: str) -> bool:
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
        return (
            'aprend' in normalized
            or (
                any(token in word_tokens for token in ('herramienta', 'herramientas', 'rutas', 'ruta', 'ias', 'ia', 'probando', 'funcionando'))
                and any(token in word_tokens for token in ('mejor', 'mejores', 'aprendido', 'cambiaste', 'aprendiste'))
            )
        )

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
            'como fue mi startup',
            'cómo fue mi startup',
            'como fue mi arranque',
            'cómo fue mi arranque',
            'como fue mi inicio',
            'cómo fue mi inicio',
            'como arranco',
            'cómo arrancó',
            'como inicio',
            'cómo inició',
            'startup timeline',
            'como estuvo el arranque',
            'cómo estuvo el arranque',
            'que paso en el startup',
            'qué pasó en el startup',
            'que paso en el arranque',
            'qué pasó en el arranque',
            'tiempos de arranque',
            'tiempos de inicio',
            'metricas de startup',
            'métricas de startup',
            'auditar autonomia',
            'auditar autonomía',
        )
        if any(phrase in normalized for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        asks_review = any(token in word_tokens for token in ('fallando', 'falla', 'repitiendo', 'mejorar', 'cambios', 'cambiar', 'corregir', 'revisarte', 'autoexaminacion'))
        asks_meta = any(token in word_tokens for token in ('recomiendas', 'recomendar', 'aprendiste', 'aprendido', 'deberias', 'debería', 'deberias'))
        if asks_review and asks_meta:
            return True
        asks_startup = any(token in word_tokens for token in ('startup', 'arranque', 'inicio', 'arranco', 'arrancó'))
        asks_how = any(token in word_tokens for token in ('como', 'cómo', 'que', 'qué', 'cuanto', 'cuánto', 'tiempos', 'metricas', 'métricas'))
        return asks_startup and asks_how

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
        word_tokens = set(re.findall(r'[a-z0-9_]+', normalized))
        if any(token in word_tokens for token in ('startup', 'arranque', 'inicio', 'arranco', 'arrancó', 'timeline', 'auditar')):
            return 'startup'
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
        if any(token in normalized for token in ('ventana', 'ventanas', 'foco', 'abierto', 'abiertas', 'pantalla', 'monitor', 'monitores', 'escritorio', 'navegador', 'navegadores', 'browser', 'chrome', 'edge', 'firefox', 'opera', 'brave')):
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

    def _learning_reply(self, message: str) -> tuple[str, str, str]:
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
                return response, 'Validacion autonoma actual.', 'inferred'
            if str(validation.get('status') or '').strip() == 'paused':
                return (
                    f"La validacion autonoma esta pausada. {str(validation.get('paused_reason') or 'No tengo condiciones seguras para validar ahora.')}",
                    'Validacion autonoma pausada.',
                    'inferred',
                )
            return ('Ahora mismo no tengo una validacion autonoma corriendo con evidencia suficiente.', 'Sin validacion activa.', 'unresolved')
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
                return response, 'Cambio de ruta basado en evidencia.', 'inferred'
            return ('Todavia no tengo evidencia suficiente para justificar un cambio de ruta real.', 'Sin cambio confirmado.', 'unresolved')
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
                    return response, 'Ranking por evidencia reciente.', 'inferred'
            return ('Todavia no tengo suficiente historial comparable para decir que herramienta va mejor.', 'Historial insuficiente.', 'unresolved')
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
            return response, 'Aprendizaje adaptativo real.', 'inferred'
        if adaptive_learning:
            preferred = str(adaptive_learning.get('recommended_assistant_kind') or adaptive_learning.get('recommended_route') or '').strip()
            if preferred:
                response = f"Por ahora solo puedo afirmar que {preferred} viene saliendo mejor en el historial reciente."
                if validation_summary:
                    response += f" Validacion reciente: {validation_summary}"
                return (response, 'Aprendizaje parcial.', 'inferred')
        if experiment_runs:
            last = experiment_runs[0]
            return (
                f"Tengo historial reciente, pero todavia no una preferencia estable. La ultima corrida comparable fue {str(getattr(last, 'candidate_label', '') or getattr(getattr(last, 'route', None), 'value', 'n/d'))}.",
                'Historial sin ganador claro.',
                'inferred',
            )
        return ('Todavia no tengo evidencia suficiente para resumir un aprendizaje estable sin inventar datos.', 'Evidencia insuficiente.', 'unresolved')

    def _evolution_status_reply(self, message: str) -> tuple[str, str, str]:
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
                return (f"Ahora mismo van ganando {self._human_join(top, limit=4)}.", 'Estado evolutivo real de herramientas.', 'inferred')
            return ('Todavia no tengo evidencia suficiente para decir que herramienta va ganando por problema.', 'Evidencia evolutiva insuficiente.', 'unresolved')
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
                return response, 'Validacion evolutiva actual.', 'inferred'
            return ('Ahora mismo no veo una validacion evolutiva activa con evidencia suficiente.', 'Sin validacion evolutiva activa.', 'unresolved')
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
                    'inferred',
                )
            return ('Todavia no tengo descartes evolutivos confirmados para mostrarte sin inventar datos.', 'Sin descartes confirmados.', 'unresolved')
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
                return response, 'Discovery real de herramientas.', 'inferred'
            return ('Todavia no tengo un descubrimiento nuevo suficientemente fuerte para recomendarlo como candidato.', 'Sin discovery fuerte.', 'unresolved')
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
            return response, 'Resumen evolutivo real.', 'inferred'
        return ('Todavia no tengo evidencia suficiente para resumir el estado evolutivo sin suponer cosas.', 'Evidencia evolutiva insuficiente.', 'unresolved')

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
        reply, meta, evidence_tag = self._evolution_status_reply(message)
        self._append_message('assistant', 'IABV', reply, meta, evidence_tag=evidence_tag,
                             reasoning_path='evolution_status')
        self._record_chat_audit(reasoning_path='evolution_status', user_goal=message)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_learning_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._learning_conversation_payload(message=message))
        reply, meta, evidence_tag = self._learning_reply(message)
        self._append_message('assistant', 'IABV', reply, meta, evidence_tag=evidence_tag,
                             reasoning_path='learning')
        self._record_chat_audit(reasoning_path='learning', user_goal=message)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_self_awareness_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        reply, meta = self._self_awareness_reply(message)
        self._append_message('assistant', 'IABV', reply, meta, evidence_tag='observed',
                             reasoning_path='self_awareness')
        self._record_chat_audit(reasoning_path='self_awareness', user_goal=message)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _answer_world_model_question(self, message: str) -> None:
        self._last_user_goal = message
        self._clear_autonomy_activity_override()
        self._update_adaptive_state(self._general_conversation_payload(message=message))
        reply, meta = self._world_model_reply(message)
        self._append_message('assistant', 'IABV', reply, meta, evidence_tag='observed',
                             reasoning_path='world_model')
        self._record_chat_audit(reasoning_path='world_model', user_goal=message)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    @staticmethod
    def _startup_timeline_summary() -> str:
        """Read the startup timeline and build a grounded summary with real data."""
        try:
            from iabv_v15.infra.startup_timeline import get_global_timeline
            events = get_global_timeline().events()
        except Exception:
            events = []
        if not events:
            return ''
        diagnostic_phases = (
            'bootstrap_init_start', 'bootstrap_init_done',
            'app_object_created', 'engine_created',
            'main_window_shown', 'main_window_raised_after_ready',
            'page_loader_ready', 'shell_loader_ready',
            'populate_ui_vm_dashboard',
            'dashboard_vm_refresh_start', 'dashboard_vm_refresh_done',
            'dashboard_vm_refresh_failed',
            'deferred_post_window_setup_start', 'deferred_post_window_setup_done',
        )
        parts: list[str] = []
        key_events: dict[str, dict] = {}
        for ev in events:
            phase = ev.get('phase', '')
            if phase in diagnostic_phases:
                key_events[phase] = ev
        if not key_events:
            return ''
        parts.append('Timeline de arranque (datos reales):')
        for phase in diagnostic_phases:
            ev = key_events.get(phase)
            if ev is not None:
                t_ms = ev.get('t_ms_from_start', 0)
                rss = ev.get('rss_mb', 0)
                parts.append(f'  {phase}: {t_ms:.0f}ms (RSS {rss:.0f}MB)')
        refresh_start = key_events.get('dashboard_vm_refresh_start')
        refresh_done = key_events.get('dashboard_vm_refresh_done')
        if refresh_start and refresh_done:
            duration = refresh_done['t_ms_from_start'] - refresh_start['t_ms_from_start']
            parts.append(f'  Dashboard refresh duration: {duration:.0f}ms (background thread)')
        refresh_failed = key_events.get('dashboard_vm_refresh_failed')
        if refresh_failed:
            parts.append(f'  Dashboard refresh FAILED @ {refresh_failed["t_ms_from_start"]:.0f}ms')
        page_ready = key_events.get('page_loader_ready')
        if page_ready:
            parts.append(f'  Ventana lista para interaccion: {page_ready["t_ms_from_start"]:.0f}ms')
        first_ev = events[0] if events else None
        last_ev = events[-1] if events else None
        if first_ev and last_ev:
            total = last_ev.get('t_ms_from_start', 0) - first_ev.get('t_ms_from_start', 0)
            parts.append(f'  Tiempo total de startup: {total:.0f}ms')
            rss_start = first_ev.get('rss_mb', 0)
            rss_end = last_ev.get('rss_mb', 0)
            parts.append(f'  RSS: {rss_start:.0f}MB -> {rss_end:.0f}MB')
        return '\n'.join(parts)

    @staticmethod
    def _finding_metrics_suffix(finding: dict) -> str:
        """Extract concrete metrics from a finding's metadata for grounded responses."""
        meta = dict(finding.get('metadata') or {})
        parts: list[str] = []
        observed_ms = meta.get('observed_ms')
        if observed_ms is not None:
            parts.append(f'{observed_ms}ms')
        threshold_ms = meta.get('threshold_ms')
        if threshold_ms is not None:
            parts.append(f'umbral {threshold_ms}ms')
        starvation_s = meta.get('starvation_seconds')
        if starvation_s is not None:
            parts.append(f'bloqueo {starvation_s}s')
        wall_clock_ms = meta.get('wall_clock_ms')
        if wall_clock_ms is not None and observed_ms is None:
            parts.append(f'wall_clock {wall_clock_ms}ms')
        if not parts:
            return ''
        return f' ({", ".join(parts)})'

    def _build_metacognition_context(self, message: str, focus: str) -> str:
        """Assemble ALL metacognition data sources into a compact context for the LLM.

        This is the 'full panorama' — everything the system knows about itself
        so the LLM can reason with real data, not generics.
        """
        sections: list[str] = []

        # 1. Timeline data (highest priority for startup questions)
        timeline = self._startup_timeline_summary()
        if timeline:
            sections.append(timeline)

        # 2. OSES findings with FULL metadata
        review = self._current_self_examination_snapshot()
        findings = list(review.get('top_findings') or [])
        if findings:
            parts = ['Hallazgos de autoexaminacion (OSES):']
            for f in findings[:6]:
                title = str(f.get('title') or '')
                summary = str(f.get('summary') or '').strip()
                metrics = self._finding_metrics_suffix(f)
                recommendation = str(f.get('recommendation') or '').strip()
                parts.append(f'  - {title}{metrics}')
                if summary:
                    parts.append(f'    {summary[:300]}')
                if recommendation:
                    parts.append(f'    Recomendacion: {recommendation[:200]}')
                meta = dict(f.get('metadata') or {})
                meta_items = []
                for mk in ('observed_ms', 'threshold_ms', 'starvation_seconds',
                            'wall_clock_ms', 'phases_seen', 'rss_delta_mb',
                            'count', 'provider', 'latency_ms'):
                    mv = meta.get(mk)
                    if mv is not None:
                        meta_items.append(f'{mk}={mv}')
                if meta_items:
                    parts.append(f'    Metadata: {", ".join(meta_items)}')
            sections.append('\n'.join(parts))

        # 3. Recurring issues
        recurring = list(review.get('recurring_issues') or [])
        if recurring:
            parts = ['Patrones recurrentes detectados:']
            for issue in recurring[:4]:
                label = issue.get('title') or issue.get('pattern', '')
                count = issue.get('count', issue.get('occurrences', '?'))
                parts.append(f'  - {label} (x{count})')
            sections.append('\n'.join(parts))

        # 4. Recommended adjustments
        adjustments = list(review.get('recommended_adjustments') or [])
        if adjustments:
            parts = ['Ajustes recomendados por evidencia:']
            for adj in adjustments[:3]:
                parts.append(f'  - {str(adj.get("recommended_change") or adj.get("title") or "").strip()[:200]}')
            sections.append('\n'.join(parts))

        # 5. Environment & hardware state
        try:
            env = self._current_environment_self_model()
            hw = env.hardware_profile or {}
            rt = env.runtime_profile or {}
            env_parts = ['Estado del entorno:']
            if hw:
                cpu = hw.get('cpu', '')
                ram = hw.get('ram_total_gb', '')
                gpu = hw.get('gpu', '')
                if cpu:
                    env_parts.append(f'  CPU: {cpu}')
                if ram:
                    env_parts.append(f'  RAM total: {ram} GB')
                if gpu:
                    env_parts.append(f'  GPU: {gpu}')
            if rt:
                py = rt.get('python_version', '')
                os_name = rt.get('os', '')
                if py:
                    env_parts.append(f'  Python: {py}')
                if os_name:
                    env_parts.append(f'  OS: {os_name}')
            risks = env.risk_signals or []
            if risks:
                for r in risks[:3]:
                    env_parts.append(f'  Riesgo: {r.summary}')
            if len(env_parts) > 1:
                sections.append('\n'.join(env_parts))
        except Exception:
            pass

        # 6. World model state
        try:
            wm = self._current_world_model()
            wm_parts = ['Estado vivo del sistema (WorldModel):']
            windows = wm.active_windows or []
            if windows:
                wm_parts.append(f'  Ventanas abiertas: {len(windows)}')
                for w in windows[:4]:
                    wm_parts.append(f'    - {w.title or w.app_name or "(sin titulo)"}')
            net = wm.network_status
            wm_parts.append(f'  Red: {net.status} ({"conectado" if net.connected else "sin conexion"})')
            if wm.detected_blocks:
                wm_parts.append(f'  Bloqueos: {", ".join(wm.detected_blocks[:4])}')
            if len(wm_parts) > 1:
                sections.append('\n'.join(wm_parts))
        except Exception:
            pass

        # 7. Experiment lab recent results
        if self.experiment_lab_repository is not None:
            try:
                runs = self.experiment_lab_repository.list_runs(limit=6)
                if runs:
                    lab_parts = ['Resultados recientes de ExperimentLab:']
                    for run in runs[:4]:
                        run_dict = run if isinstance(run, dict) else (run.model_dump(mode='json') if hasattr(run, 'model_dump') else {})
                        subject = str(run_dict.get('subject_key') or run_dict.get('experiment_id') or '?')
                        winner = str(run_dict.get('winner') or run_dict.get('result') or '?')
                        lab_parts.append(f'  - {subject}: ganador={winner}')
                    sections.append('\n'.join(lab_parts))
            except Exception:
                pass

        # 8. Conversation flow (what the user asked and what was answered)
        chat = self._chat_messages[-8:] if self._chat_messages else []
        if chat:
            chat_parts = ['Flujo de la conversacion reciente:']
            for msg in chat:
                role = msg.get('role', '?')
                text = str(msg.get('text') or '')[:150]
                tag = msg.get('evidence_tag', '')
                tag_suffix = f' [{tag}]' if tag else ''
                chat_parts.append(f'  [{role}]{tag_suffix}: {text}')
            sections.append('\n'.join(chat_parts))

        return '\n\n'.join(sections) if sections else ''

    def _invoke_llm_for_self_examination(self, message: str, metacognition_context: str, focus: str) -> str | None:
        """Invoke the local LLM (Ollama) with full metacognition context.

        Returns the LLM response text, or None if unavailable.
        Does NOT create a new brain — delegates reasoning to the existing provider.
        """
        provider = getattr(self.role_router, 'general_provider', None)
        if provider is None:
            return None
        try:
            health = provider.health_check()
            if not bool(getattr(health, 'available', False)):
                return None
        except Exception:
            return None

        focus_instruction = {
            'startup': (
                'El usuario pregunta sobre el arranque/startup del sistema. '
                'Tu respuesta DEBE citar los tiempos exactos del timeline (en ms) '
                'y las metricas de RSS (en MB). Ejemplo: "page_loader_ready @ 7768ms, '
                'dashboard refresh tardo 274ms". NO generalices cuando tienes datos concretos.'
            ),
            'failures': (
                'El usuario pregunta sobre fallos y problemas. '
                'Cita los hallazgos de OSES con sus metricas concretas. '
                'NO inventes datos — usa solo lo que aparece en el contexto.'
            ),
            'repetition': (
                'El usuario pregunta sobre patrones repetidos. '
                'Cita los patrones recurrentes con su conteo exacto.'
            ),
            'adjustments': (
                'El usuario pregunta sobre ajustes recomendados. '
                'Cita las recomendaciones con la evidencia que las respalda.'
            ),
        }.get(focus, (
            'Responde con datos concretos del contexto proporcionado. '
            'NO generalices cuando tienes metricas especificas.'
        ))

        system_prompt = (
            '## Quien eres\n'
            'Eres el cerebro local de IABV v1.5. Respondes en espanol claro.\n\n'
            '## Instruccion especifica\n'
            f'{focus_instruction}\n\n'
            '## DATOS REALES DISPONIBLES (usa estos numeros en tu respuesta)\n'
            f'{metacognition_context}\n\n'
            '## Reglas de respuesta\n'
            '1. SIEMPRE cita numeros concretos del contexto (ms, MB, conteos, umbrales)\n'
            '2. Si un dato existe en el contexto, DEBES mencionarlo — no lo omitas\n'
            '3. Estructura tu respuesta: primero los datos clave, luego tu analisis\n'
            '4. NO inventes datos que no esten en el contexto proporcionado\n'
            '5. Si algo no tiene datos, di "sin metricas disponibles"\n'
            '6. Responde en maximo 4 parrafos concisos'
        )

        request = InferenceRequest(
            user_goal=message,
            prompt=message,
            conversation_context=self._conversation_context(),
            metadata={'system_prompt_override': system_prompt},
        )
        try:
            result = provider.answer_user(request)
            text = str(getattr(result, 'summary', '') or '').strip()
            return text if text else None
        except Exception:
            return None

    @staticmethod
    def _extract_grounding_anchors(metacognition_context: str) -> list[str]:
        """Extract concrete numeric values from context that should appear in a grounded response."""
        import re as _re
        anchors: list[str] = []
        for match in _re.finditer(r'(\d+(?:\.\d+)?)\s*ms\b', metacognition_context):
            val = match.group(1)
            if float(val) > 100:
                anchors.append(f'{val}ms')
        for match in _re.finditer(r'(\d+(?:\.\d+)?)\s*MB\b', metacognition_context):
            anchors.append(f'{match.group(1)}MB')
        for match in _re.finditer(r'x(\d+)\)', metacognition_context):
            anchors.append(f'x{match.group(1)}')
        return anchors[:20]

    @staticmethod
    def _validate_response_grounding(response: str, anchors: list[str]) -> tuple[bool, list[str]]:
        """Check whether the LLM response cites concrete data points from available sources.

        Returns (is_grounded, missing_anchors).  A response is grounded when
        it mentions at least 40% of the available numeric anchors.
        """
        if not anchors:
            return True, []
        missing: list[str] = []
        found = 0
        for anchor in anchors:
            numeric_part = anchor.rstrip('msMB').rstrip('x')
            if numeric_part in response:
                found += 1
            else:
                missing.append(anchor)
        ratio = found / len(anchors) if anchors else 1.0
        return ratio >= 0.4, missing

    def _self_examination_reply(self, message: str) -> tuple[str, str, str]:
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
                metrics = self._finding_metrics_suffix(top)
                response = f"Lo que mas se esta repitiendo mal ahora es {str(top.get('title') or 'un patron sin nombre')}{metrics}."
                if str(top.get('summary') or '').strip():
                    response += f" {str(top.get('summary') or '').strip()}"
                if recommended_adjustments:
                    response += f" El ajuste mas util ahora es {str(recommended_adjustments[0].get('recommended_change') or '').strip()}."
                return response, 'Autoexaminacion operativa.', 'inferred'
            return ('Todavia no tengo suficiente evidencia acumulada para afirmar que es lo que mas esta fallando.', 'Evidencia insuficiente.', 'unresolved')
        if focus == 'repetition':
            if findings:
                top = findings[0]
                metrics = self._finding_metrics_suffix(top)
                response = f"Lo que estoy repitiendo peor es {str(top.get('title') or 'un patron sin nombre')}{metrics}."
                if str(top.get('summary') or '').strip():
                    response += f" {str(top.get('summary') or '').strip()}"
                recommendation = str(top.get('recommendation') or '').strip()
                if recommendation:
                    response += f" Por eso recomiendo {recommendation}"
                return response, 'Patron repetido detectado.', 'inferred'
            return ('No veo un patron repetido fuerte y confirmado todavia.', 'Sin patron fuerte.', 'unresolved')
        if focus == 'adjustments':
            if recommended_adjustments:
                top = recommended_adjustments[0]
                response = f"El cambio que mas recomiendo ahora es {str(top.get('recommended_change') or '').strip()}."
                if len(recommended_adjustments) > 1:
                    response += f" Despues vendria {str(recommended_adjustments[1].get('recommended_change') or '').strip()}."
                return response, 'Ajustes recomendados por evidencia.', 'inferred'
            return ('Todavia no tengo cambios recomendados con evidencia suficiente para proponerlos en serio.', 'Sin ajuste fuerte.', 'unresolved')
        if focus == 'startup':
            timeline_summary = self._startup_timeline_summary()
            parts: list[str] = []
            if timeline_summary:
                parts.append(timeline_summary)
            startup_findings = [
                f for f in findings
                if any(
                    kw in str(f.get('title') or '').lower()
                    for kw in ('startup', 'arranque', 'bootstrap', 'dashboard', 'refresh', 'loader', 'splash')
                )
            ]
            if startup_findings:
                parts.append('Hallazgos de OSES relevantes:')
                for sf in startup_findings[:4]:
                    metrics = self._finding_metrics_suffix(sf)
                    parts.append(f'  - {sf.get("title", "?")}{metrics}: {str(sf.get("summary") or "").strip()[:200]}')
            if not startup_findings and findings:
                parts.append('Hallazgos activos de OSES:')
                for sf in findings[:3]:
                    metrics = self._finding_metrics_suffix(sf)
                    parts.append(f'  - {sf.get("title", "?")}{metrics}')
            if recommended_adjustments:
                top_adj = recommended_adjustments[0]
                parts.append(f'Ajuste recomendado: {str(top_adj.get("recommended_change") or "").strip()[:200]}')
            if parts:
                return '\n'.join(parts), 'Reporte de startup con datos reales del timeline.', 'observed'
            return ('No tengo datos de startup en el timeline para este arranque.', 'Sin datos de timeline.', 'unresolved')
        if findings or recommended_adjustments or validated_improvements:
            parts = []
            if findings:
                top = findings[0]
                metrics = self._finding_metrics_suffix(top)
                parts.append(f"Lo mas delicado ahora es {str(top.get('title') or 'un hallazgo sin nombre')}{metrics}.")
            if recommended_adjustments:
                parts.append(f"El ajuste mas util es {str(recommended_adjustments[0].get('recommended_change') or '').strip()}.")
            if validated_improvements:
                parts.append(f"Lo que si parece ir bien es {str(validated_improvements[0].get('title') or 'una mejora validada')}.")
            if unresolved_risks:
                parts.append(f"Todavia dejo como UNRESOLVED {str(unresolved_risks[0]).replace('UNRESOLVED:', '').replace('_', ' ')}.")
            return (' '.join(part for part in parts if part).strip(), 'Revision operativa con evidencia.', 'inferred')
        return ('Todavia no tengo evidencia suficiente para revisarme con hallazgos utiles sin inventar datos.', 'Evidencia insuficiente.', 'unresolved')

    def _self_examination_conversation_payload(self, *, message: str) -> dict[str, Any]:
        review = self._current_self_examination_snapshot()
        timeline_summary = self._startup_timeline_summary()
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
                        'startup_timeline_summary': timeline_summary,
                        'assistant_brief': str(review.get('assistant_brief') or ''),
                        'llm_grounded_reasoning': True,
                        'conversation_flow_turns': len(self._chat_messages),
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

        # Build full panorama context for LLM reasoning
        focus = self._self_examination_focus(message)
        metacognition_context = self._build_metacognition_context(message, focus)

        # Try LLM-grounded reasoning first
        llm_reply = self._invoke_llm_for_self_examination(message, metacognition_context, focus)

        trace: dict[str, Any] = {'focus': focus, 'anchors_total': 0, 'anchors_cited': 0}
        if llm_reply:
            # Validate that the LLM actually used the real data
            anchors = self._extract_grounding_anchors(metacognition_context)
            is_grounded, missing = self._validate_response_grounding(llm_reply, anchors)
            trace['anchors_total'] = len(anchors)
            trace['anchors_cited'] = len(anchors) - len(missing)

            if is_grounded:
                reply = llm_reply
                meta = 'Razonamiento con metacognicion completa (LLM + datos reales).'
                evidence_tag = 'observed'
                reasoning_path = 'llm_grounded'
            else:
                # LLM responded but didn't ground in data — supplement with template
                template_reply, template_meta, template_tag = self._self_examination_reply(message)
                reply = (
                    f'{llm_reply}\n\n'
                    f'--- Datos concretos del sistema ---\n'
                    f'{template_reply}'
                )
                meta = 'Razonamiento LLM + suplemento con datos reales (grounding parcial).'
                evidence_tag = 'inferred'
                reasoning_path = 'llm_supplemented'
                trace['missing_anchors'] = missing[:10]
        else:
            # LLM unavailable — fall back to template (still has real data)
            reply, meta, evidence_tag = self._self_examination_reply(message)
            reasoning_path = 'template_fallback'

        self._append_message('assistant', 'IABV', reply, meta, evidence_tag=evidence_tag,
                             reasoning_path=reasoning_path, trace_metadata=trace)
        self._record_chat_audit(reasoning_path=reasoning_path, user_goal=message)
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
        self._clear_autonomy_activity_override()
        reply, meta, evidence_tag = self._general_chat_reply(message)
        self._append_message('assistant', 'IABV', reply, meta, evidence_tag=evidence_tag,
                             reasoning_path='general_chat')
        self._record_chat_audit(reasoning_path='general_chat', user_goal=message)
        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._working = False
        self._set_live_status('idle')
        self._busy_label = 'Respuesta lista.'
        self.dataChanged.emit()

    def _human_hardware_notice(self, governance: dict[str, Any] | None) -> str:
        governance = dict(governance or {})
        blockers = ' '.join(str(item).strip().lower() for item in (governance.get('blockers') or []) if str(item).strip())
        autonomy_level = str(governance.get('autonomy_level') or '').strip().lower()
        if autonomy_level == 'protective_local' or any(token in blockers for token in ('ram libre', 'cpu', 'gpu', 'temperatura', 'memoria', 'throttling', 'carga')):
            return 'Ahora mismo el equipo esta bajo bastante carga, asi que voy a usar una via mas liviana mientras seguimos.'
        return ''

    def _general_chat_reply(self, message: str) -> tuple[str, str, str]:
        normalized = self._normalized_command_text(message)
        if self._is_self_awareness_question(normalized):
            return (*self._self_awareness_reply(message), 'observed')
        if self._is_world_model_question(normalized):
            return (*self._world_model_reply(message), 'observed')
        if self._is_self_examination_question(normalized):
            return self._self_examination_reply(message)
        if self._is_learning_question(normalized):
            return self._learning_reply(message)
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
                'explicarte lo que esta pasando y, cuando haga falta, apoyarme en Codex, ChatGPT, Claude u Ollama.',
                'Conversacion general local.',
                'unresolved',
            )
        greeting_prefixes = ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')
        if len(normalized.split()) <= 5 and any(normalized.startswith(prefix) for prefix in greeting_prefixes):
            return ('Hola. Estoy aqui para ayudarte. Dime que quieres revisar o resolver y lo trabajamos desde aqui.', 'Conversacion general local.', 'unresolved')
        return ('Te leo. Cuentame que necesitas y te respondo de forma clara, sin cargarte con detalle tecnico interno.', 'Conversacion general local.', 'unresolved')

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

    def _is_general_conversation_session(self, payload: dict[str, Any], intent: dict[str, Any], context: dict[str, Any]) -> bool:
        intent_key = str(intent.get('intent_key') or '').strip()
        site_name = str(context.get('site_display_name') or context.get('site_id') or '').strip().lower()
        metadata = dict(intent.get('metadata') or {})
        return (
            intent_key in {'general.assistance', 'system.self_awareness', 'system.metacognition', 'consulta_estado_evolutivo'}
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
        reply, meta, _evidence_tag = self._learning_reply(message)
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
        reply, meta, _evidence_tag = self._evolution_status_reply(message)
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
        reply, meta, _evidence_tag = self._self_examination_reply(message)
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
    ) -> tuple[str, str, str]:
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
        if self_awareness:
            return (*self._self_awareness_reply(message), 'observed')
        if world_model_question:
            return (*self._world_model_reply(message), 'observed')
        if self_examination_question:
            return self._self_examination_reply(message)
        if learning_question:
            return self._learning_reply(message)
        local_chat_llm = dict(payload.get('local_chat_llm') or {})
        llm_answered = bool(local_chat_llm.get('available')) and bool(str(raw_summary or '').strip()) and not local_chat_llm.get('error')
        vm_small_talk = self._is_general_chat_message(message)
        general_chat = vm_small_talk or str(intent.get('intent_key') or '').strip() == 'general.assistance'
        if vm_small_talk and not self._seems_task_like_message(message):
            return self._general_chat_reply(message)
        if general_chat and not self._seems_task_like_message(message) and not llm_answered:
            return self._general_chat_reply(message)
        if llm_answered:
            provider_name = str(local_chat_llm.get('provider_name') or 'Ollama')
            llm_tag = self._classify_evidence_tag(
                has_live_observation=True,
                has_persisted_evidence=bool(payload.get('sources')),
            )
            return str(raw_summary).strip(), f'Respuesta local ({provider_name}).', llm_tag
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
        fallback_tag = self._classify_evidence_tag(
            has_persisted_evidence=bool(payload.get('sources')),
        )
        return summary, meta, fallback_tag

    def _humanize_task_failure(self, task_name: str, message: str) -> tuple[str, str]:
        detail = str(message or '').strip()
        lowered = detail.lower()
        if 'supero el tiempo maximo' in lowered or 'timeout' in lowered:
            return (
                f'{detail} Puedes verificar la conexion o reenviar tu consulta.',
                'timeout',
            )
        if task_name == 'external_consultation':
            if 'acceso denegado' in lowered or 'access denied' in lowered:
                return (
                    f'Herramienta externa bloqueada por permisos. {detail[:200]}',
                    'blocked_by_permission',
                )
        if any(token in lowered for token in ('login', 'session', 'sesion')):
            return (
                f'Sesion del asistente no disponible. Accion: inicia sesion en la herramienta y reintenta. {detail[:200]}',
                'blocked_by_permission',
            )
        if any(token in lowered for token in ('cuota', 'quota', 'rate limit')):
            return (
                f'Cuota o limite alcanzado. Accion: espera o cambia de herramienta. {detail[:200]}',
                'blocked_by_quota',
            )
        # Strip Python exception traces from user-visible messages.
        _has_traceback = any(t in lowered for t in (
            'traceback', 'nonetype', 'attributeerror', 'keyerror',
            'typeerror', 'valueerror', 'object has no attribute',
        ))
        if _has_traceback or not detail:
            visible = (
                'No pude completar la consulta externa en este momento. '
                'Voy a seguir con lo que ya tenemos aqui y, si hace falta, preparo otra via.'
            )
        else:
            visible = f'{detail} Sigo con la via local.'
        return visible, 'failed_with_actionable_reason'

    def _human_external_consultation_failure(self, assistant_title: str, failure_detail: str, external_state_flags: list[str] | None = None) -> tuple[str, str, str]:
        detail = str(failure_detail or '').strip()
        lowered = detail.lower()
        external_notice = self._external_state_notice(external_state_flags)
        # --- Sub-objective C: structured handoff on external tool failure ---
        # Each branch now tells the user: WHAT tool, WHAT block, WHAT evidence,
        # WHAT human action is needed, and whether local fallback is viable.
        if 'browser_security_verification' in lowered:
            # P0.32: probe CDP availability to offer session selection
            try:
                cdp_probe = self._detect_cdp_available()
            except Exception:
                cdp_probe = {'available': False, 'error': 'probe_failed'}
            cdp_ok = cdp_probe.get('available', False)
            cdp_option = (
                'Tambien puedes escribir "usar mi chrome" '
                'para que IABV observe tu Chrome normal via CDP '
                '(sin leer cookies ni tokens).'
            ) if cdp_ok else (
                'Si prefieres usar tu Chrome normal, abre Chrome con '
                '"--remote-debugging-port=9222" y escribe "usar mi chrome".'
            )
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: verificacion de seguridad del sitio (captcha / challenge). '
                f'Evidencia: IABV esta mirando una ventana/perfil controlado por IABV '
                f'(chatgpt_program_session/browser_profile), '
                f'no necesariamente tu Chrome normal. '
                f'Tu navegador real tiene cookies y sesion activa que este perfil '
                f'aislado no comparte; que tu hayas iniciado sesion en tu Chrome '
                f'no prueba que esta sesion controlada este lista. '
                f'Accion humana: '
                f'1) Inicia sesion o resuelve la verificacion en la ventana que abrio IABV. '
                f'2) Cuando este lista, escribe "ya lo hice" para un retest gobernado. '
                f'{cdp_option} '
                f'3) Pegado manual: copia la respuesta y pegala aqui. '
                'Sigo con la mejor via local disponible.'
            )
            if external_notice:
                message = f'{message} {external_notice}'
            meta = f'{assistant_title}: blocked_by_security_verification'
            busy = f'Verificacion de seguridad pendiente para {assistant_title}.'
            # P0.32: trace with CDP availability + session selection state
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                tracer = get_runtime_tracer()
                tracer.trace(
                    'assistant_profile_context_reported',
                    assistant_title=assistant_title,
                    profile_label='chatgpt_program_session/browser_profile',
                    block_type='browser_security_verification',
                    user_chrome_bridge='cdp_available' if cdp_ok else 'governed_user_chrome_bridge_missing',
                    cdp_available=cdp_ok,
                )
                tracer.trace_user_browser_bridge(
                    'cdp_probe_attempted',
                    assistant_kind=assistant_title.lower().replace(' ', '_'),
                    cdp_available=cdp_ok,
                    reason=cdp_probe.get('error', '') or 'ok',
                )
            except Exception:
                pass
        elif 'codex_state_missing' in lowered:
            human_action = 'Verifica que la extension de Codex este instalada y autenticada en este entorno.'
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: falta tracking del hilo de conversacion. '
                f'Evidencia: la instalacion no expone el estado del hilo. '
                f'Accion humana: {human_action} '
                'Sigo con la via local.'
            )
            if external_notice:
                message = f'{message} {external_notice}'
            meta = f'{assistant_title}: needs_human_handoff'
            busy = message
        elif 'acceso denegado' in lowered or 'access denied' in lowered:
            human_action = 'Revisa permisos o credenciales para acceder a la herramienta externa.'
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: acceso denegado desde este entorno. '
                f'Evidencia: {detail[:120] or "sin detalle adicional"}. '
                f'Accion humana: {human_action} '
                'Sigo con la via local.'
            )
            meta = f'{assistant_title}: blocked_by_permission'
            busy = message
        elif 'session' in lowered or 'sesion' in lowered or 'login' in lowered:
            human_action = 'Inicia sesion en la herramienta externa y vuelve a intentar.'
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: sesion no activa o expirada. '
                f'Evidencia: {detail[:120] or "sin detalle adicional"}. '
                f'Accion humana: {human_action} '
                'Sigo con la via local mientras tanto.'
            )
            meta = f'{assistant_title}: blocked_by_permission'
            busy = message
        elif 'timeout' in lowered or 'timed out' in lowered or 'tiempo' in lowered:
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: la operacion tomo demasiado tiempo. '
                f'Evidencia: {detail[:120] or "timeout sin detalle adicional"}. '
                'Accion humana: verifica que la herramienta este respondiendo y reintenta. '
                'Sigo con la via local.'
            )
            meta = f'{assistant_title}: timeout'
            busy = message
        elif 'cuota' in lowered or 'quota' in lowered or 'rate' in lowered or 'limit' in lowered:
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: cuota o limite de uso alcanzado. '
                f'Evidencia: {detail[:120] or "sin detalle adicional"}. '
                'Accion humana: espera a que se renueve la cuota o usa otra herramienta. '
                'Sigo con la via local.'
            )
            meta = f'{assistant_title}: blocked_by_quota'
            busy = message
        else:
            message = (
                f'Herramienta: {assistant_title}. '
                f'Bloqueo: fallo no clasificado. '
                f'Evidencia: {detail[:120] or "sin detalle"}. '
            )
            if external_notice:
                message = f'{message}{external_notice} '
            message = f'{message}Sigo con la via local.'
            meta = f'{assistant_title}: failed_with_actionable_reason'
            busy = message
        return message, meta, busy

    # ── Task A: window-rect capturability classification ────────
    @staticmethod
    def _window_rect_is_captureable(rect: list[int] | tuple[int, ...] | None) -> bool:
        """Return True only if *rect* represents a visible, capturable window.

        A window is NOT capturable when:
        - rect is absent or has fewer than 4 elements,
        - left or top are <= -30000 (offscreen / minimized on Windows),
        - computed width or height are too small for a real page (< 50 px).
        """
        if not rect or not isinstance(rect, (list, tuple)) or len(rect) < 4:
            return False
        try:
            left, top = int(rect[0]), int(rect[1])
        except (TypeError, ValueError, IndexError):
            return False
        if left <= -30000 or top <= -30000:
            return False
        try:
            right, bottom = int(rect[2]), int(rect[3])
        except (TypeError, ValueError, IndexError):
            return False
        width = right - left if right > left else int(rect[2])
        height = bottom - top if bottom > top else int(rect[3])
        if width < 50 or height < 50:
            return False
        return True

    @staticmethod
    def _capture_is_low_information(capture_meta: dict[str, Any] | None) -> bool:
        """Return True if the capture metadata indicates a black/blank image."""
        if not capture_meta or not isinstance(capture_meta, dict):
            return False
        blank_prob = float(capture_meta.get('blank_probability') or 0.0)
        if blank_prob >= 0.90:
            return True
        dynamic_range = capture_meta.get('dynamic_range')
        if dynamic_range is not None and int(dynamic_range) == 0:
            return True
        unique_colors = capture_meta.get('unique_color_count')
        if unique_colors is not None and int(unique_colors) <= 2:
            return True
        if capture_meta.get('useful') is False:
            return True
        return False

    def _target_window_capture_state(
        self,
        target_window: dict[str, Any] | None,
        capture_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Classify a target window + capture result for visual evidence.

        Returns a dict with:
        - captureable: bool
        - reason: str (why not captureable, or 'ok')
        - low_information: bool
        - unresolved: list[str] of UNRESOLVED tags
        - user_message: str (actionable guidance for the user)
        - suggested_actions: list[str]
        """
        result: dict[str, Any] = {
            'captureable': True,
            'reason': 'ok',
            'low_information': False,
            'unresolved': [],
            'user_message': '',
            'suggested_actions': [],
        }
        if target_window is None:
            result['captureable'] = False
            result['reason'] = 'no_target_window'
            result['unresolved'] = ['UNRESOLVED:visual_capture_no_target_window']
            result['user_message'] = 'No encontre una ventana objetivo para capturar.'
            result['suggested_actions'] = ['select_visible_window']
            return result
        rect = target_window.get('rect')
        title = str(target_window.get('title') or '').strip()
        hwnd = target_window.get('hwnd')
        if not self._window_rect_is_captureable(rect):
            result['captureable'] = False
            result['reason'] = 'target_window_minimized_or_offscreen'
            result['unresolved'] = [
                'UNRESOLVED:external_target_window_minimized_or_offscreen',
                'UNRESOLVED:visual_capture_low_information',
            ]
            result['user_message'] = (
                f'Encontre {title or "la ventana objetivo"}, pero esta minimizada o fuera de pantalla. '
                f'Mi captura salio negra. Restaura esa ventana o pulsa abrir {title or "la herramienta"} y reintenta.'
            )
            result['suggested_actions'] = [
                'restore_target_window',
                'select_visible_window',
                'retry_capture',
            ]
            return result
        if capture_meta and self._capture_is_low_information(capture_meta):
            result['low_information'] = True
            result['unresolved'] = ['UNRESOLVED:visual_capture_low_information']
            result['user_message'] = (
                f'Capture la ventana de {title or "la herramienta"}, pero la imagen tiene muy poca informacion (negra o casi vacia). '
                'Verifica que la herramienta este mostrando contenido visible y reintenta la captura.'
            )
            result['suggested_actions'] = [
                'restore_target_window',
                'retry_capture',
            ]
            return result
        return result

    # ── Task B+C: visual evidence validation in external consultation ──
    def _validate_visual_evidence_result(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        result_metadata: dict[str, Any],
        consultation_metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Check if external consultation visual evidence is valid.

        If the target window was offscreen/minimized or capture was
        low-information, returns a modified result dict with:
        - status='visual_unresolved' (not visual_captured)
        - unresolved tags
        - user-facing guided handoff message

        Returns None if the evidence is valid (no override needed).
        """
        target_window = result_metadata.get('target_window')
        capture_meta = result_metadata.get('visual_evidence_snapshot') or result_metadata.get('capture_meta') or {}
        if not target_window and not capture_meta:
            capture_meta_from_exec = {}
            for key in ('blank_probability', 'dynamic_range', 'unique_color_count', 'useful'):
                if key in result_metadata:
                    capture_meta_from_exec[key] = result_metadata[key]
            if capture_meta_from_exec:
                capture_meta = capture_meta_from_exec
            else:
                return None
        capture_state = self._target_window_capture_state(target_window, capture_meta)
        if capture_state['captureable'] and not capture_state['low_information']:
            return None
        unresolved_tags = list(capture_state.get('unresolved') or [])
        reason = capture_state['reason']
        user_message = capture_state['user_message']
        suggested_actions = list(capture_state.get('suggested_actions') or [])
        consultation_metadata['status'] = 'visual_unresolved'
        existing_unresolved = list(consultation_metadata.get('unresolved') or [])
        for tag in unresolved_tags:
            if tag not in existing_unresolved:
                existing_unresolved.append(tag)
        consultation_metadata['unresolved'] = existing_unresolved
        consultation_metadata['visual_capture_reason'] = reason
        consultation_metadata['suggested_actions'] = suggested_actions
        # Task D: trace invalid visual evidence to runtime audit
        self._trace_visual_evidence_invalid(
            assistant_kind=assistant_kind,
            assistant_title=assistant_title,
            target_window=target_window,
            capture_meta=capture_meta,
            reason=reason,
            suggested_actions=suggested_actions,
        )
        return {
            'visual_unresolved': True,
            'user_message': user_message,
            'reason': reason,
            'unresolved': unresolved_tags,
            'suggested_actions': suggested_actions,
        }

    # ── Task D: runtime audit trace for invalid visual evidence ─────
    def _trace_visual_evidence_invalid(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        target_window: dict[str, Any] | None,
        capture_meta: dict[str, Any] | None,
        reason: str,
        suggested_actions: list[str] | None = None,
    ) -> None:
        """Log a visual_evidence_invalid event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tw = target_window or {}
            cm = capture_meta or {}
            get_runtime_tracer().trace(
                'visual_evidence_snapshot',
                status='unresolved',
                assistant_kind=assistant_kind,
                assistant_title=assistant_title,
                target_title=str(tw.get('title') or ''),
                hwnd=tw.get('hwnd'),
                rect=tw.get('rect'),
                capture_scope=str(cm.get('capture_scope') or 'external_target_window_bbox'),
                blank_probability=float(cm.get('blank_probability') or 0.0),
                dynamic_range=cm.get('dynamic_range'),
                unique_color_count=cm.get('unique_color_count'),
                useful=False,
                reason=reason,
                next_action=', '.join(suggested_actions or ['restore_target_window', 'retry_capture']),
            )
        except Exception:
            pass

    # ── Task C: guided visual handoff message builder ───────────
    def _visual_handoff_message(
        self,
        *,
        assistant_title: str,
        target_window: dict[str, Any] | None,
        capture_state: dict[str, Any],
        local_fallback_available: bool = True,
    ) -> str:
        """Build a structured handoff message when visual evidence fails.

        Tells the user: what tool, what window, what coordinates/state,
        what was actually seen, what user action is needed, and whether
        a local fallback route exists.
        """
        tw = target_window or {}
        title = str(tw.get('title') or assistant_title)
        hwnd = tw.get('hwnd', 'desconocido')
        rect = tw.get('rect', 'no disponible')
        reason = capture_state.get('reason', 'unknown')
        parts = [
            f'Herramienta: {assistant_title}.',
            f'Ventana objetivo: {title}.',
            f'Coordenadas detectadas: hwnd={hwnd}, rect={rect}.',
        ]
        if reason == 'target_window_minimized_or_offscreen':
            parts.append('Estado: la ventana esta minimizada o fuera de pantalla.')
            parts.append('Lo que vi: captura negra / sin informacion visual.')
        elif reason == 'no_target_window':
            parts.append('Estado: no se encontro ventana objetivo.')
            parts.append('Lo que vi: ninguna ventana coincide con la herramienta solicitada.')
        else:
            parts.append(f'Estado: {reason}.')
            parts.append('Lo que vi: captura con muy poca informacion visual.')
        actions = capture_state.get('suggested_actions') or []
        action_labels = {
            'restore_target_window': f'restaurar/abrir la ventana de {assistant_title}',
            'select_visible_window': 'seleccionar una ventana visible manualmente',
            'retry_capture': 'reintentar la captura despues de restaurar',
        }
        action_texts = [action_labels.get(a, a) for a in actions]
        if action_texts:
            parts.append(f'Accion necesaria: {"; ".join(action_texts)}.')
        if local_fallback_available:
            parts.append('Mientras tanto, sigo con la mejor via local disponible.')
        return ' '.join(parts)

    # ── P0.4 Task A: shared reality causal handoff package ───────
    def _build_shared_reality_handoff(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        target_window: dict[str, Any] | None,
        capture_meta: dict[str, Any] | None,
        capture_state: dict[str, Any],
        user_claim: str = '',
        evidence_path: str = '',
    ) -> dict[str, Any]:
        """Build a causal handoff package explaining the gap between what the
        user sees and what IABV sees.

        Returns a plain dict (not a new model) with all fields required for
        the shared reality explanation.
        """
        tw = target_window or {}
        cm = capture_meta or {}
        target_title = str(tw.get('title') or '').strip()
        hwnd = tw.get('hwnd')
        rect = tw.get('rect')
        capture_scope = str(cm.get('capture_scope') or 'unknown')
        capture_useful = bool(cm.get('useful', True))
        blank_prob = float(cm.get('blank_probability') or 0.0)
        dynamic_range = cm.get('dynamic_range')
        unique_colors = cm.get('unique_color_count')
        reason = capture_state.get('reason', 'unknown')
        browser_label = 'unknown'
        if target_title:
            title_lower = target_title.lower()
            if 'chrome for testing' in title_lower:
                browser_label = 'Chrome for Testing (sesión aislada de IABV)'
            elif 'chrome' in title_lower:
                browser_label = 'Google Chrome (sesión controlada)'
            elif 'firefox' in title_lower:
                browser_label = 'Firefox'
            elif 'edge' in title_lower:
                browser_label = 'Microsoft Edge'
            else:
                browser_label = 'navegador/sesión controlada por IABV'
        mismatch_reason = 'unknown'
        if reason == 'target_window_minimized_or_offscreen':
            mismatch_reason = (
                'La ventana que IABV usa está minimizada o fuera de pantalla. '
                'Tú probablemente ves tu navegador/sesión normal, pero IABV '
                'usa una sesión aislada que no está visible.'
            )
        elif reason == 'no_target_window':
            mismatch_reason = (
                'IABV no encontró la ventana objetivo. Es posible que la '
                'herramienta esté abierta en tu navegador personal pero no en '
                'la sesión controlada por IABV.'
            )
        elif reason in ('low_information_pixels', 'low_information'):
            mismatch_reason = (
                'La ventana de IABV está visible pero la captura tiene muy '
                'poca información (negra o casi vacía). La herramienta puede '
                'funcionar en tu navegador pero no en la sesión de IABV.'
            )
        else:
            mismatch_reason = (
                'IABV no pudo verificar el estado de la herramienta. '
                'Puede funcionar en tu navegador pero no en la sesión de IABV.'
            )
        causal_explanation = self._build_causal_explanation(
            assistant_title=assistant_title,
            browser_label=browser_label,
            target_title=target_title,
            reason=reason,
            rect=rect,
            blank_prob=blank_prob,
        )
        user_action_needed = list(capture_state.get('suggested_actions') or [])
        if 'authorize_visible_browser' not in user_action_needed:
            user_action_needed.append('authorize_visible_browser')
        unresolved_tags = list(capture_state.get('unresolved') or [])
        if not any('shared_reality' in t for t in unresolved_tags):
            unresolved_tags.append('UNRESOLVED:shared_reality_mismatch_pending_live_proof')
        return {
            'user_claim': user_claim or 'unknown',
            'requested_tool': assistant_kind,
            'selected_tool': assistant_kind,
            'selected_browser_or_profile': browser_label,
            'target_window_title': target_title or 'unknown',
            'hwnd': hwnd,
            'rect': rect,
            'capture_scope': capture_scope,
            'capture_useful': capture_useful,
            'capture_quality': {
                'blank_probability': blank_prob,
                'dynamic_range': dynamic_range,
                'unique_color_count': unique_colors,
                'useful': capture_useful,
            },
            'mismatch_reason': mismatch_reason,
            'causal_explanation': causal_explanation,
            'user_action_needed': user_action_needed,
            'fallback_available': True,
            'unresolved': unresolved_tags,
            'evidence_path': evidence_path or 'no_disponible',
        }

    # ── P0.4 Task B: detect user/IABV mismatch claims ─────────
    _USER_MISMATCH_PATTERNS: ClassVar[list[str]] = [
        'a mí sí me funciona',
        'a mi si me funciona',
        'yo sí lo veo',
        'yo si lo veo',
        'en mi navegador sí',
        'en mi navegador si',
        'por qué a mí sí',
        'por que a mi si',
        'a él no',
        'a el no',
        'a iabv no',
        'yo lo veo bien',
        'a mí me funciona',
        'a mi me funciona',
        'funciona en mi',
        'yo sí puedo',
        'yo si puedo',
    ]

    @staticmethod
    def _detect_user_mismatch_claim(user_text: str) -> str:
        """Return the matching claim phrase if the user is saying 'it works for
        me but not for IABV', or empty string if no match."""
        if not user_text:
            return ''
        normalized = ' '.join(user_text.lower().strip().split())
        for pattern in ControlCenterViewModel._USER_MISMATCH_PATTERNS:
            if pattern in normalized:
                return pattern
        return ''

    # ── P0.4 Task C: causal comparative message ────────────────
    def _build_causal_explanation(
        self,
        *,
        assistant_title: str,
        browser_label: str,
        target_title: str,
        reason: str,
        rect: Any = None,
        blank_prob: float = 0.0,
    ) -> str:
        """Build the 'Tu vista vs Vista de IABV' causal explanation."""
        parts = []
        parts.append(f'Tu vista: probablemente ves {assistant_title} funcionando en tu navegador o sesión normal.')
        parts.append(
            f'Vista de IABV: estoy usando {browser_label}'
            f'{f" (ventana: {target_title})" if target_title else ""}.'
        )
        if reason == 'target_window_minimized_or_offscreen':
            parts.append(
                f'Esa ventana está minimizada o fuera de pantalla '
                f'(coordenadas: {rect or "no disponible"}).'
            )
            parts.append('Mi captura salió negra / sin información visual.')
        elif reason == 'no_target_window':
            parts.append('No encontré la ventana objetivo en mi sesión.')
        else:
            if blank_prob >= 0.90:
                parts.append(f'La captura tiene muy poca información (blank_probability={blank_prob:.2f}).')
            else:
                parts.append('La captura no tiene suficiente información para verificar el estado.')
        parts.append(f'Por eso no puedo confirmar {assistant_title} desde mi sesión.')
        parts.append(
            'Necesito que restaures esa ventana, selecciones la ventana correcta '
            'o autorices usar el navegador visible.'
        )
        return ' '.join(parts)

    # ── P0.4 Task C: shared reality user message ───────────────
    def _shared_reality_user_message(
        self,
        *,
        handoff: dict[str, Any],
        user_claim: str = '',
    ) -> str:
        """Build the full user-facing message for shared reality handoff.

        Includes: tool, window, coordinates, what IABV saw, the difference,
        why IABV cannot proceed, what user must do, and fallback info.
        """
        parts = []
        if user_claim:
            parts.append(f'Entiendo que a ti sí te funciona ("{user_claim}").')
        parts.append(f'Herramienta: {handoff.get("requested_tool", "unknown")}.')
        target = handoff.get('target_window_title', 'unknown')
        hwnd = handoff.get('hwnd', 'desconocido')
        rect = handoff.get('rect', 'no disponible')
        parts.append(f'Ventana que intenté usar: {target} (hwnd={hwnd}, rect={rect}).')
        cq = handoff.get('capture_quality') or {}
        blank_prob = float(cq.get('blank_probability') or 0.0)
        if blank_prob >= 0.90:
            parts.append(f'Qué vi: captura negra / baja información (blank_probability={blank_prob:.2f}).')
        elif not cq.get('useful', True):
            parts.append('Qué vi: captura sin información útil.')
        else:
            parts.append('Qué vi: no pude verificar el estado real.')
        parts.append(f'Diferencia probable: {handoff.get("mismatch_reason", "desconocida")}.')
        parts.append(f'Por qué no avanzo: no puedo verificar estado real de {handoff.get("requested_tool", "la herramienta")}.')
        actions = handoff.get('user_action_needed') or []
        action_labels = {
            'restore_target_window': 'restaurar/abrir la ventana objetivo',
            'select_visible_window': 'seleccionar una ventana visible manualmente',
            'retry_capture': 'reintentar la captura después de restaurar',
            'authorize_visible_browser': 'autorizar que use el navegador visible en tu pantalla',
        }
        action_texts = [action_labels.get(a, a) for a in actions]
        if action_texts:
            parts.append(f'Qué necesito: {"; ".join(action_texts)}.')
        evidence_path = handoff.get('evidence_path', '')
        if evidence_path and evidence_path != 'no_disponible':
            parts.append(f'Evidencia de captura: {evidence_path} (useful=false, reason={handoff.get("capture_quality", {}).get("reason", "low_information_pixels")}).')
        if handoff.get('fallback_available'):
            parts.append('Qué haré mientras tanto: sigo con la mejor vía local disponible.')
        return ' '.join(parts)

    # ── P0.4 Task D: evidence path exposure ────────────────────
    def _attach_evidence_to_handoff(
        self,
        handoff: dict[str, Any],
        result_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach screenshot evidence path to handoff if available."""
        evidence_path = ''
        for key in ('screenshot_path', 'capture_path', 'evidence_path', 'image_path'):
            path_val = str(result_metadata.get(key) or '').strip()
            if path_val:
                evidence_path = path_val
                break
        if evidence_path:
            handoff['evidence_path'] = evidence_path
            handoff['evidence_metadata'] = {
                'path': evidence_path,
                'useful': False,
                'reason': 'low_information_pixels',
                'description': 'Esto fue lo que capturé',
            }
        return handoff

    # ── P0.4 Task E: runtime audit trace for shared reality ────
    def _trace_shared_reality_handoff(
        self,
        handoff: dict[str, Any],
    ) -> None:
        """Log a shared_reality_handoff event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            cq = handoff.get('capture_quality') or {}
            get_runtime_tracer().trace(
                'shared_reality_handoff',
                assistant_kind=handoff.get('requested_tool', ''),
                user_claim=handoff.get('user_claim', 'unknown'),
                target_window_title=handoff.get('target_window_title', ''),
                browser_profile=handoff.get('selected_browser_or_profile', 'unknown'),
                hwnd=handoff.get('hwnd'),
                rect=handoff.get('rect'),
                capture_scope=handoff.get('capture_scope', 'unknown'),
                capture_path=handoff.get('evidence_path', 'no_disponible'),
                capture_useful=handoff.get('capture_useful', False),
                blank_probability=float(cq.get('blank_probability') or 0.0),
                mismatch_reason=handoff.get('mismatch_reason', ''),
                causal_explanation_summary=str(handoff.get('causal_explanation') or '')[:500],
                user_action_needed=handoff.get('user_action_needed', []),
                unresolved=handoff.get('unresolved', []),
            )
        except Exception:
            pass

    # ── P0.4 wiring: handle shared reality followup in chat ──────
    def _try_handle_shared_reality_followup(self, message: str) -> bool:
        """If the user says 'it works for me' and there is a recent
        shared_reality_handoff in the adaptive payload, respond with
        the causal explanation. Returns True if handled."""
        claim = self._detect_user_mismatch_claim(message)
        if not claim:
            return False
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        handoff = metadata.get('shared_reality_handoff')
        if not handoff or not isinstance(handoff, dict):
            return False
        handoff = dict(handoff)
        handoff['user_claim'] = claim
        msg = self._shared_reality_user_message(handoff=handoff, user_claim=claim)
        self._trace_shared_reality_handoff(handoff)
        tool_name = handoff.get('requested_tool', 'herramienta externa')
        self._latest_response_text = msg
        self._latest_response_meta = f'{tool_name}: shared_reality_followup'
        self._busy_label = ''
        self._append_message(
            'assistant', 'IABV', msg,
            'shared_reality_followup',
        )
        self._set_live_status('idle')
        return True

    # -- P0.16: explain recent external failure without heavy local inference --
    _EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S: float = 600.0
    _EXTERNAL_FAILURE_FOLLOWUP_PATTERNS: tuple[str, ...] = (
        'intente nuevamente', 'intenta nuevamente', 'reintenta', 'reintentar',
        'analiza bien', 'analiza el error', 'cual es el error', 'cuál es el error',
        'que paso', 'qué paso', 'que pasó', 'qué pasó', 'por que', 'por qué',
        'no pudo', 'no pudo hacer', 'fallo', 'falló', 'error', 'chatgpt',
        'a mi si', 'a mi sí', 'a mí si', 'a mí sí',
        # P0.27: deictic follow-up patterns after external failure
        'solucionar eso', 'soluciona eso', 'arregla eso', 'arreglalo',
        'ayudame con eso', 'ayúdame con eso',
        'pueddes solucionar', 'puedes solucionar',
        'ese problema', 'ese fallo', 'ese error',
        'eso de chatgpt', 'eso de chat gpt',
        'no pudo consultar', 'sigue sin consultar',
        'porque sigue fallando', 'por qué sigue fallando',
        'por que no consulta', 'por qué no consulta',
        'hazlo con la ventana', 'hazlo con mi ventana',
    )
    # P0.27: deictic references that only match within recent external failure window.
    # Short tokens like 'eso' are too broad without external failure context.
    _EXTERNAL_FAILURE_DEICTIC_TOKENS: tuple[str, ...] = (
        'solucionar eso', 'soluciona eso', 'arregla eso',
        'ayudame con eso', 'ayúdame con eso',
        'pueddes solucionar eso', 'puedes solucionar eso',
    )
    # P0.27: patterns where the user says they see ChatGPT in their own browser
    _USER_BROWSER_HANDOFF_PATTERNS: tuple[str, ...] = (
        'yo veo chatgpt', 'yo veo chat gpt',
        'yo veo bien la ventana', 'yo veo la ventana',
        'yo si veo chatgpt', 'yo si veo chat gpt',
        'a mi si me abre', 'a mi me abre',
        'yo ya inicie sesion', 'yo ya inicié sesión',
        'ya inicie sesion en chatgpt', 'ya inicié sesión en chatgpt',
    )

    def _remember_external_failure(
        self,
        *,
        assistant_title: str,
        message: str,
        meta: str,
        outcome: str = 'failed',
        success: bool = False,
        assistant_kind: str = '',
        terminal_state: str = '',
        dispatch_id: str = '',
    ) -> None:
        """Keep the latest external failure as local evidence for follow-up chat.

        This is not routing state. It only prevents a second heavy local
        inference when the user immediately asks what happened after an
        external tool timeout/block.
        """
        self._last_external_failure_payload = {
            'assistant_title': str(assistant_title or 'Asistente externo'),
            'message': str(message or '')[:1200],
            'meta': str(meta or '')[:1200],
            'outcome': str(outcome or 'failed'),
            'success': bool(success),
            'at': time.time(),
            'assistant_kind': str(assistant_kind or ''),
            'terminal_state': str(terminal_state or ''),
            'dispatch_id': str(dispatch_id or ''),
        }
        self._last_external_failure_ts = time.time()
        # P0.37: create active incident frame for blocked terminal states
        try:
            ts = str(terminal_state or '')
            meta_lower = str(meta or '').lower()
            block_type = ''
            if 'blocked_by_security_verification' in ts or 'browser_security_verification' in meta_lower:
                block_type = 'browser_security_verification'
            elif 'visible_timeout' in ts or 'visible_timeout' in meta_lower:
                block_type = 'visible_timeout'
            elif 'blocked' in ts:
                block_type = ts
            if block_type:
                # Extract real payload context from latest adaptive payload
                _ap = getattr(self, '_last_adaptive_payload', None) or {}
                _handoff = dict((_ap.get('metadata') or {}).get('shared_reality_handoff') or {})
                _tw_title = str(_handoff.get('target_window_title', '') or '')
                _hwnd_raw = _handoff.get('hwnd')
                _hwnd = int(_hwnd_raw) if _hwnd_raw is not None else None
                _browser_label = str(_handoff.get('selected_browser_or_profile', '') or '')
                _browser_profile = str(_handoff.get('browser_profile', '') or '')
                self._create_active_incident_frame(
                    assistant_kind=str(assistant_kind or ''),
                    assistant_title=str(assistant_title or 'Asistente externo'),
                    terminal_state=ts,
                    block_type=block_type,
                    last_user_goal=str(getattr(self, '_last_user_goal', '') or ''),
                    dispatch_id=str(dispatch_id or ''),
                    browser_profile=_browser_profile,
                    selected_browser_or_profile=_browser_label,
                    browser_label=_browser_label,
                    target_window_title=_tw_title,
                    hwnd=_hwnd,
                )
        except Exception:
            pass

    def _clear_external_failure_memory(self) -> None:
        self._last_external_failure_payload = {}
        self._last_external_failure_ts = 0.0

    # -- P0.30 Task B: structured self-audit guard --
    _STRUCTURED_SELF_AUDIT_PATTERNS: tuple[str, ...] = (
        'autoauditoria', 'autoauditoría', 'auto auditoria', 'auto auditoría',
        'estado de tests', 'estado de pruebas',
        'self audit', 'self-audit',
        'portable context', 'contexto portable',
        'control master',
        'que evidencia tienes', 'qué evidencia tienes',
        'que algoritmos se ejecutaron', 'qué algoritmos se ejecutaron',
        'que fallo en la ultima interaccion', 'qué falló en la última interacción',
        'dime el estado de', 'muestra el estado',
        'test evidence', 'evidencia de tests',
        'runtime audit', 'audit trail',
    )

    def _try_handle_structured_self_audit(self, message: str) -> bool:
        """P0.30 Task B: answer self-audit questions from structured artifacts.

        Reads ONLY from persisted evidence files — never invokes Ollama or
        the Adaptive local orchestrator.  Must respond in <5s.
        """
        lowered = ' '.join(message.strip().lower().split())
        if not any(p in lowered for p in self._STRUCTURED_SELF_AUDIT_PATTERNS):
            return False

        import json as _json
        workspace = str(getattr(self.config, 'workspace_root', '') or '')
        if not workspace:
            workspace = str(Path.cwd())
        root = Path(workspace)

        sections: list[str] = []
        evidence_tag = 'observed'
        missing: list[str] = []

        # 1. Test evidence
        te_path = root / 'data' / 'evolution' / 'test_evidence' / 'latest.json'
        if te_path.exists():
            try:
                te = _json.loads(te_path.read_text(encoding='utf-8'))
                sections.append(
                    f"**Tests**: passed={te.get('passed', '?')}, "
                    f"failed={te.get('failed', '?')}, "
                    f"total={te.get('total', '?')}, "
                    f"timestamp={te.get('timestamp', '?')}"
                )
            except Exception:
                missing.append('test_evidence (parse error)')
        else:
            sections.append('**Tests**: no ejecute tests ahora — no hay test_evidence/latest.json.')
            missing.append('test_evidence')

        # 2. Self examination
        se_path = root / 'data' / 'evolution' / 'self_examination' / 'latest.json'
        if se_path.exists():
            try:
                se = _json.loads(se_path.read_text(encoding='utf-8'))
                status = se.get('status', '?')
                summary = str(se.get('summary', ''))[:300]
                updated = se.get('updated_at_utc', '?')
                n_findings = len(se.get('findings', []))
                sections.append(
                    f"**SelfAudit**: status={status}, "
                    f"findings={n_findings}, "
                    f"updated={updated}. "
                    f"Resumen: {summary}"
                )
            except Exception:
                missing.append('self_examination (parse error)')
        else:
            missing.append('self_examination')

        # 3. Portable context
        pc_path = root / 'data' / 'evolution' / 'portable_context' / 'latest.json'
        if pc_path.exists():
            try:
                pc = _json.loads(pc_path.read_text(encoding='utf-8'))
                updated = pc.get('updated_at_utc', '?')
                section_ids = [s.get('section_id', '?') for s in pc.get('sections', [])[:8]]
                sections.append(
                    f"**PortableContext**: updated={updated}, "
                    f"secciones={section_ids}"
                )
            except Exception:
                missing.append('portable_context (parse error)')
        else:
            missing.append('portable_context')

        # 4. Control master
        cm_path = root / 'data' / 'evolution' / 'control_master' / 'latest.json'
        if cm_path.exists():
            try:
                cm = _json.loads(cm_path.read_text(encoding='utf-8'))
                tests_state = cm.get('current_tests_state', {})
                if tests_state:
                    sections.append(
                        f"**ControlMaster tests_state**: "
                        f"passed={tests_state.get('passed', '?')}, "
                        f"failed={tests_state.get('failed', '?')}, "
                        f"total={tests_state.get('total', '?')}"
                    )
                else:
                    sections.append('**ControlMaster**: sin snapshot de tests.')
            except Exception:
                missing.append('control_master (parse error)')
        else:
            missing.append('control_master')

        # 5. Last dispatch from runtime_audit tail
        audit_path = root / 'data' / 'logs' / 'runtime_audit.jsonl'
        if audit_path.exists():
            try:
                lines = audit_path.read_text(encoding='utf-8').strip().splitlines()
                last_dispatch = None
                for line in reversed(lines[-50:]):
                    entry = _json.loads(line)
                    if entry.get('kind') == 'dispatch_terminal':
                        last_dispatch = entry
                        break
                if last_dispatch:
                    d = last_dispatch.get('data', {})
                    sections.append(
                        f"**Ultimo dispatch**: {d.get('task_name', '?')} "
                        f"-> {d.get('terminal_state', '?')} "
                        f"(dispatch_id={d.get('dispatch_id', '?')[:12]})"
                    )
            except Exception:
                pass

        if missing:
            sections.append(f"**UNRESOLVED**: {', '.join(missing)}")
            evidence_tag = 'inferred'

        reply = (
            'Autoauditoria directa desde artefactos estructurados '
            '(no ejecute LLM local ni tests ahora):\n\n'
            + '\n'.join(sections)
        )
        meta = 'structured_self_audit (artifacts only, no Ollama)'

        self._latest_response_text = reply
        self._latest_response_meta = meta
        self._busy_label = 'Autoauditoria desde evidencia.'
        self._working = False
        self._append_message(
            'assistant', 'IABV', reply, meta,
            reasoning_path='structured_self_audit',
            evidence_tag=evidence_tag,
        )
        self._set_live_status('idle')
        self._clear_autonomy_activity_override()
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'structured_self_audit_answered' if not missing else 'structured_self_audit_missing_evidence',
                artifacts_found=len(sections) - (1 if missing else 0),
                missing=missing[:5],
                user_message_excerpt=message[:120],
            )
        except Exception:
            pass
        try:
            self.dataChanged.emit()
        except Exception:
            pass
        return True

    def _try_handle_external_failure_followup(self, message: str) -> bool:
        """Answer immediate follow-ups about a recent external failure cheaply.

        P0.16: after a ChatGPT timeout the next message entered normal local
        inference and froze the UI.  This guard keeps that explanation on the
        GUI path and uses only the already recorded failure payload.

        P0.27: extended with deictic binding ("solucionar eso", "arregla eso")
        and user-browser handoff ("yo veo chatgpt") so follow-ups never fall
        through to Adaptive local orchestrator.

        P0.30 Task D: if the message expresses an explicit NEW external
        consultation intent ("haz una consulta a ChatGPT", "consulta
        chatgpt"), skip follow-up and let sendChat route it as a fresh
        external consultation.  Only deictic references ("eso",
        "soluciona eso") without an explicit assistant name qualify as
        follow-ups.
        """
        payload = dict(getattr(self, '_last_external_failure_payload', {}) or {})
        last_ts = float(getattr(self, '_last_external_failure_ts', 0.0) or 0.0)
        if not payload or not last_ts:
            return False
        if (time.time() - last_ts) > self._EXTERNAL_FAILURE_FOLLOWUP_WINDOW_S:
            return False
        lowered = message.strip().lower()
        if not any(pattern in lowered for pattern in self._EXTERNAL_FAILURE_FOLLOWUP_PATTERNS):
            return False
        # P0.30 Task D: explicit new consultation intent wins over follow-up.
        # If the user says "haz una consulta a ChatGPT: responde solo S"
        # that is a new request, not a follow-up of the old failure.
        explicit_new = self._explicit_assistant_preference(message)
        if explicit_new:
            # Trace that we are forcing a new request instead of follow-up
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'external_consultation_new_request_forced',
                    previous_failure_assistant=str(payload.get('assistant_title', '')),
                    new_target=explicit_new,
                    user_message_excerpt=message[:120],
                )
            except Exception:
                pass
            return False

        assistant_title = str(payload.get('assistant_title') or 'Asistente externo')
        previous_message = str(payload.get('message') or 'No hubo respuesta externa util.').strip()
        previous_meta = str(payload.get('meta') or 'sin metadata').strip()
        outcome = str(payload.get('outcome') or 'failed').strip()
        previous_terminal = str(payload.get('terminal_state') or '').strip()
        previous_kind = str(payload.get('assistant_kind') or '').strip()
        previous_dispatch = str(payload.get('dispatch_id') or '').strip()

        # P0.27 Task D: user says they see ChatGPT in their own browser →
        # offer manual handoff instead of repeating the isolated profile.
        is_handoff = any(p in lowered for p in self._USER_BROWSER_HANDOFF_PATTERNS)
        if is_handoff:
            return self._handle_user_browser_manual_handoff(
                message=message,
                assistant_title=assistant_title,
                assistant_kind=previous_kind,
                previous_terminal=previous_terminal,
                previous_dispatch=previous_dispatch,
            )

        # P0.27 Task A/B: deictic or keyword follow-up — explain without
        # heavy local inference.
        followup_path = 'external_failure_followup'
        if any(p in lowered for p in self._EXTERNAL_FAILURE_DEICTIC_TOKENS):
            followup_path = 'external_failure_followup_deictic'

        summary = (
            f"Revise el fallo reciente de {assistant_title}. No quedo sin cierre: "
            f"el ciclo externo termino como {outcome}. "
            f"Lo que vio IABV fue: {previous_message[:320]} "
            f"Evidencia tecnica: {previous_meta[:260]}. "
            "No voy a lanzar razonamiento local pesado para explicar el mismo bloqueo, "
            "porque eso fue lo que dejo la UI congelada. "
            "El siguiente paso correcto es reintentar solo con la ventana de ChatGPT visible y enfocada, "
            "o completar la verificacion/captcha si aparece. Si quieres, escribe 'reintentar ChatGPT ahora' "
            "despues de dejar esa ventana lista."
        )
        self._latest_response_text = summary
        self._latest_response_meta = f'{assistant_title}: {followup_path}'
        self._busy_label = 'Fallo externo explicado desde evidencia reciente.'
        self._working = False
        self._append_message(
            'assistant',
            'IABV',
            summary,
            followup_path,
            reasoning_path=followup_path,
            evidence_tag='observed',
        )
        self._set_live_status('idle')
        self._clear_autonomy_activity_override()
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'external_failure_followup_answered',
                assistant_title=assistant_title,
                outcome=outcome,
                previous_meta=previous_meta[:240],
                user_message=message[:240],
                followup_path=followup_path,
                previous_assistant_kind=previous_kind,
                previous_terminal_state=previous_terminal,
                dispatch_id=previous_dispatch,
            )
            # P0.27 Task E: trace that local fallback was suppressed
            tracer.trace(
                'local_fallback_suppressed_for_external_failure',
                previous_assistant_kind=previous_kind,
                previous_terminal_state=previous_terminal,
                user_message_excerpt=message[:120],
                selected_followup_path=followup_path,
                dispatch_id=previous_dispatch,
                interaction_id=str(getattr(self, '_active_interaction_id', '') or ''),
            )
        except Exception:
            pass
        try:
            self.dataChanged.emit()
        except Exception:
            pass
        return True

    def _handle_user_browser_manual_handoff(
        self,
        *,
        message: str,
        assistant_title: str,
        assistant_kind: str,
        previous_terminal: str,
        previous_dispatch: str,
    ) -> bool:
        """P0.27 Task D: user says they see ChatGPT — offer manual pasteback.

        IABV cannot verify the user's browser session without CDP/permission.
        Instead of repeating the isolated profile, copy the prompt to clipboard
        and explain the limitation.
        """
        user_goal = str(getattr(self, '_last_user_goal', '') or '')
        prompt_text = user_goal[:500] if user_goal else ''
        if prompt_text:
            try:
                self._copy_text(prompt_text, 'Prompt copiado al portapapeles para pegado manual.')
            except Exception:
                pass

        clipboard_note = (
            ' Ya copie el prompt al portapapeles para que lo pegues directamente.'
            if prompt_text else ''
        )
        summary = (
            f'Entendido — tu ves {assistant_title} en tu navegador, pero IABV '
            'no puede comprobar esa sesion sin CDP/permiso de observacion. '
            'Por eso la consulta anterior fallo con perfil aislado. '
            f'{clipboard_note} '
            'Pega el prompt en la ventana de ChatGPT que ves, '
            'obtiene la respuesta y escribeme lo que dijo, '
            'o escribe "ya lo hice" para que IABV intente un retest gobernado. '
            'No voy a fingir que recibí respuesta.'
        )
        self._latest_response_text = summary
        self._latest_response_meta = f'{assistant_title}: user_browser_manual_handoff'
        self._busy_label = ''
        self._working = False
        self._append_message(
            'assistant', 'IABV', summary,
            'user_browser_manual_handoff',
            reasoning_path='user_browser_manual_handoff',
            evidence_tag='observed',
        )
        self._set_live_status('idle')
        self._clear_autonomy_activity_override()
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'user_browser_handoff_required',
                previous_assistant_kind=assistant_kind,
                previous_terminal_state=previous_terminal,
                user_message_excerpt=message[:120],
                selected_followup_path='user_browser_manual_handoff',
                dispatch_id=previous_dispatch,
                interaction_id=str(getattr(self, '_active_interaction_id', '') or ''),
                prompt_copied=bool(prompt_text),
            )
            tracer.trace(
                'local_fallback_suppressed_for_external_failure',
                previous_assistant_kind=assistant_kind,
                previous_terminal_state=previous_terminal,
                user_message_excerpt=message[:120],
                selected_followup_path='user_browser_manual_handoff',
                dispatch_id=previous_dispatch,
                interaction_id=str(getattr(self, '_active_interaction_id', '') or ''),
            )
        except Exception:
            pass
        try:
            self.dataChanged.emit()
        except Exception:
            pass
        return True

    # ── P0.12: Security verification retest handler ──
    _SECURITY_RETEST_PATTERNS: tuple[str, ...] = (
        'ya lo hice', 'ya lo hise', 'ya complete', 'a mi si me funciona',
        'a mi me funciona', 'ya pase el captcha', 'ya verifique',
        'ya esta listo', 'ya lo resolvi', 'done', 'i did it',
    )

    def _try_handle_security_verification_retest(self, message: str) -> bool:
        """If the user claims they completed security verification, do a single governed retest.

        The background worker only produces a result dict; UI updates are
        routed through taskResolved/taskFailed so Qt state is never
        touched from a non-GUI thread.
        """
        lowered = message.strip().lower()
        if not any(p in lowered for p in self._SECURITY_RETEST_PATTERNS):
            return False
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        ext_meta = metadata.get('external_consultation') or {}
        if not isinstance(ext_meta, dict):
            return False
        last_meta = str(ext_meta.get('detail') or ext_meta.get('status') or '')
        if 'browser_security_verification' not in last_meta and ext_meta.get('status') != 'blocked_external':
            flags = ext_meta.get('external_state_flags') or []
            if 'capture_unverified' not in flags:
                return False
        if getattr(self, '_security_retest_done', False):
            self._append_message(
                'assistant', 'IABV',
                'Ya hice un retest gobernado despues de tu confirmacion y sigue bloqueado. '
                'Para intentar otra vez, selecciona otro perfil de navegador o reinicia la sesion.',
                'security_retest_already_done',
            )
            self._set_live_status('idle')
            return True
        self._security_retest_done = True
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                'security_verification_retest',
                user_claim=message[:200],
                assistant_kind=str(ext_meta.get('assistant_kind') or ''),
            )
        except Exception:
            pass
        assistant_kind = str(ext_meta.get('assistant_kind') or ext_meta.get('requested_assistant_kind') or 'chatgpt')
        assistant_title = str(ext_meta.get('assistant_title', '') or self._assistant_display_name(assistant_kind))
        self._append_message(
            'assistant', 'IABV',
            f'Entendido — ejecutando un solo retest gobernado de {assistant_title} '
            f'despues de tu confirmacion.',
            'security_retest_initiated',
        )
        self._working = True
        self._set_live_status('processing')
        self.dataChanged.emit()

        def _retest_worker() -> None:
            try:
                result = self._execute_external_consultation_sync(
                    assistant_kind, dispatch_id=f'security_retest_{uuid.uuid4().hex[:8]}',
                )
                result_payload = {
                    'success': bool(result.get('success')),
                    'detail': str(result.get('detail', '') or result.get('meta', '')),
                    'assistant_kind': assistant_kind,
                    'assistant_title': assistant_title,
                }
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace(
                        'security_verification_retest_result',
                        **result_payload,
                    )
                except Exception:
                    pass
                self.taskResolved.emit('security_retest', result_payload)
            except Exception as exc:
                self.taskFailed.emit('security_retest', str(exc))

        self._bg_pool.submit(_retest_worker)
        return True

    # ══════════════════════════════════════════════════════════════════
    # P0.32 — Governed User Chrome Bridge / External Session Selection
    # ══════════════════════════════════════════════════════════════════

    _CHROME_BRIDGE_PATTERNS: tuple[str, ...] = (
        'usar mi chrome', 'use my chrome', 'mi navegador', 'my browser',
        'chrome normal', 'usar chrome', 'mi sesion', 'my session',
    )
    _CDP_REVOKE_PATTERNS: tuple[str, ...] = (
        'revocar permiso cdp', 'revocar cdp', 'revoke cdp',
        'desactivar cdp', 'disable cdp', 'no usar mi chrome',
    )

    @staticmethod
    def _detect_cdp_available(
        cdp_url: str = '',
        timeout: float = 2.0,
    ) -> dict[str, Any]:
        """Probe CDP endpoint without reading cookies/tokens/credentials.

        Returns ``{'available': True/False, 'browser_version': ..., ...}``.
        Only reads ``/json/version`` — never accesses page content,
        cookies, localStorage, or any user data.
        """
        import urllib.request
        import urllib.error

        url = cdp_url or os.environ.get(
            'IABV_SHARED_CDP_URL', 'http://localhost:9222',
        )
        version_url = f'{url}/json/version'
        result: dict[str, Any] = {
            'available': False,
            'cdp_url': url,
            'browser_version': '',
            'error': '',
        }
        try:
            req = urllib.request.Request(version_url, method='GET')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                import json
                data = json.loads(resp.read().decode('utf-8', errors='replace'))
                result['available'] = True
                result['browser_version'] = str(
                    data.get('Browser', data.get('browser', '')),
                )[:100]
        except urllib.error.URLError as exc:
            result['error'] = f'connection_failed: {exc.reason}'
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
        return result

    def _build_session_selection_message(
        self,
        assistant_title: str,
        cdp_probe: dict[str, Any],
    ) -> str:
        """Build a user-facing message explaining the available session options.

        Options depend on CDP availability:
        - If CDP is available: isolated profile, user Chrome (with permission), manual pasteback.
        - If CDP is not available: isolated profile, manual pasteback, instructions to enable CDP.
        """
        cdp_ok = cdp_probe.get('available', False)
        browser_ver = cdp_probe.get('browser_version', '')

        options = [
            '1) Perfil aislado de IABV: la sesion controlada por IABV '
            '(puede requerir login/captcha separado).',
        ]
        if cdp_ok:
            ver_note = f' (detecte: {browser_ver})' if browser_ver else ''
            options.append(
                f'2) Tu Chrome normal{ver_note}: IABV observaria tu navegador '
                f'(requiere tu permiso explicito). Escribe "usar mi chrome" '
                f'para activar esta opcion. No leere cookies ni tokens, '
                f'solo observare el contenido visible de la pagina.'
            )
            options.append(
                '3) Pegado manual: copia la respuesta de ChatGPT y pegala '
                'aqui, o escribe lo que dijo.'
            )
        else:
            options.append(
                '2) Tu Chrome normal: no esta disponible ahora. '
                'Para activarla, abre Chrome con '
                '"--remote-debugging-port=9222" y reinicia la consulta.'
            )
            options.append(
                '3) Pegado manual: copia la respuesta de ChatGPT y pegala '
                'aqui, o escribe lo que dijo.'
            )

        return (
            f'Herramienta: {assistant_title}.\n'
            f'IABV esta usando un perfil aislado '
            f'(chatgpt_program_session/browser_profile) '
            f'que no comparte tu sesion de Chrome normal. '
            f'Por eso la verificacion de seguridad te bloquea a ti pero no al perfil real.\n\n'
            f'Opciones disponibles:\n'
            + '\n'.join(options)
        )

    _USER_CHROME_BRIDGE_PATTERNS: tuple[str, ...] = (
        'usar mi chrome', 'use my chrome', 'usar chrome normal',
    )

    def _verify_chrome_bridge_capability(self) -> bool:
        """P0.32+P0.37 metacognitive guard: verify Chrome bridge is wired."""
        return (
            hasattr(self, '_try_handle_user_chrome_bridge_selection')
            and hasattr(self, '_detect_cdp_available')
            and callable(getattr(self, '_try_handle_user_chrome_bridge_selection', None))
            and callable(getattr(self, '_detect_cdp_available', None))
        )

    def _try_handle_user_chrome_bridge_selection(self, message: str) -> bool:
        """Handle user request to switch to their Chrome via CDP.

        Gates on explicit permission. Never reads cookies/tokens.
        Sets IABV_PREFER_CDP_SESSION=1 so the next consultation
        uses the shared CDP controller.

        Includes metacognitive guard: if P0.32 handlers are not wired,
        responds with UNRESOLVED instead of promising the capability.
        """
        lowered = message.strip().lower()
        if not any(p in lowered for p in self._CHROME_BRIDGE_PATTERNS):
            return False

        if not self._verify_chrome_bridge_capability():
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'capability_promised_but_unavailable',
                    capability='user_chrome_bridge',
                    reason='p032_handlers_not_wired',
                )
            except Exception:
                pass
            msg = (
                'La ruta de Chrome del usuario no esta disponible '
                'en este build; queda UNRESOLVED.'
            )
            self._latest_response_text = msg
            self._latest_response_meta = 'capability_promised_but_unavailable'
            self._append_message(
                'assistant', 'IABV', msg,
                'capability_promised_but_unavailable',
                reasoning_path='metacognitive_capability_guard',
            )
            return True

        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace_user_browser_bridge(
                'permission_requested',
                assistant_kind='chatgpt',
                reason='user_requested_chrome_bridge',
            )
        except Exception:
            pass

        cdp_probe = self._detect_cdp_available()

        try:
            tracer.trace_user_browser_bridge(
                'cdp_probe_result',
                assistant_kind='chatgpt',
                cdp_available=cdp_probe.get('available', False),
                reason=cdp_probe.get('error', '') or 'ok',
            )
        except Exception:
            pass

        if not cdp_probe.get('available', False):
            os.environ.pop('IABV_PREFER_CDP_SESSION', None)
            msg = (
                'No puedo conectarme a tu Chrome. '
                'Para usar tu sesion activa, abre Chrome con: '
                '"chrome.exe --remote-debugging-port=9222" '
                'y despues escribe "usar mi chrome" otra vez. '
                'Mientras tanto, puedes pegar la respuesta manualmente.'
            )
            self._latest_response_text = msg
            self._latest_response_meta = 'user_chrome_bridge: cdp_unavailable'
            self._append_message(
                'assistant', 'IABV', msg,
                'user_chrome_bridge_cdp_unavailable',
                reasoning_path='governed_chrome_bridge',
            )
            try:
                tracer.trace_user_browser_bridge(
                    'bridge_result',
                    assistant_kind='chatgpt',
                    cdp_available=False,
                    session_selected='none',
                    reason='cdp_unavailable',
                )
            except Exception:
                pass
            self.dataChanged.emit()
            return True

        os.environ['IABV_PREFER_CDP_SESSION'] = '1'

        try:
            tracer.trace_user_browser_bridge(
                'permission_granted',
                assistant_kind='chatgpt',
                cdp_available=True,
                session_selected='user_chrome_cdp',
            )
            tracer.trace_user_browser_bridge(
                'session_selected',
                assistant_kind='chatgpt',
                cdp_available=True,
                session_selected='user_chrome_cdp',
                reason='user_explicit_permission',
            )
        except Exception:
            pass

        msg = (
            'Activado: IABV usara tu Chrome normal para la proxima consulta '
            'a ChatGPT (via CDP). No leere cookies, tokens ni credenciales — '
            'solo observare el contenido visible de la pagina. '
            'Puedes escribir "revocar permiso cdp" en cualquier momento para '
            'volver al perfil aislado.'
        )
        self._latest_response_text = msg
        self._latest_response_meta = 'user_chrome_bridge: cdp_activated'
        self._append_message(
            'assistant', 'IABV', msg,
            'user_chrome_bridge_activated',
            reasoning_path='governed_chrome_bridge',
        )
        self.dataChanged.emit()
        return True

    def _try_handle_cdp_permission_revoke(self, message: str) -> bool:
        """Handle user request to revoke CDP permission.

        Clears IABV_PREFER_CDP_SESSION so subsequent consultations
        return to the isolated profile.
        """
        lowered = message.strip().lower()
        if not any(p in lowered for p in self._CDP_REVOKE_PATTERNS):
            return False

        os.environ.pop('IABV_PREFER_CDP_SESSION', None)

        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_user_browser_bridge(
                'permission_denied',
                assistant_kind='chatgpt',
                cdp_available=False,
                session_selected='isolated_profile',
                reason='user_revoked_cdp_permission',
            )
        except Exception:
            pass

        msg = (
            'CDP desactivado. IABV vuelve al perfil aislado para consultas externas. '
            'Si necesitas usar tu Chrome otra vez, escribe "usar mi chrome".'
        )
        self._latest_response_text = msg
        self._latest_response_meta = 'user_chrome_bridge: cdp_revoked'
        self._append_message(
            'assistant', 'IABV', msg,
            'user_chrome_bridge_revoked',
            reasoning_path='governed_chrome_bridge',
        )
        self.dataChanged.emit()
        return True

    # ══════════════════════════════════════════════════════════════════

    # P0.37 — Active Incident Frame + Guided Human Assistance Resolver
    # ══════════════════════════════════════════════════════════════════

    _INCIDENT_FRAME_TTL_S: float = 900.0  # 15 min

    def _create_active_incident_frame(
        self,
        *,
        assistant_kind: str,
        assistant_title: str,
        terminal_state: str,
        block_type: str,
        profile_label: str = 'chatgpt_program_session',
        cdp_available: bool = False,
        last_user_goal: str = '',
        dispatch_id: str = '',
        browser_profile: str = '',
        selected_browser_or_profile: str = '',
        browser_label: str = '',
        target_window_title: str = '',
        hwnd: int | None = None,
    ) -> dict[str, Any]:
        """Build and store an active incident frame (read-only metadata).

        Not a new service — just structured metadata in the ViewModel so
        subsequent user messages can be resolved against the real incident.
        """
        # Resolve cdp_available from live probe if not explicitly set
        if not cdp_available:
            try:
                cdp_available = bool(self._detect_cdp_available())
            except Exception:
                pass
        frame: dict[str, Any] = {
            'incident_id': f'inc_{uuid.uuid4().hex[:8]}',
            'assistant_kind': assistant_kind,
            'assistant_title': assistant_title,
            'terminal_state': terminal_state,
            'block_type': block_type,
            'profile_label': profile_label,
            'cdp_available': cdp_available,
            'last_user_goal': last_user_goal[:300],
            'user_help_needed': self._describe_user_help_needed(block_type),
            'available_actions': self._describe_available_actions(
                block_type, cdp_available,
                bridge_wired=self._verify_chrome_bridge_capability(),
            ),
            'created_at': time.time(),
            'expires_at': time.time() + self._INCIDENT_FRAME_TTL_S,
            'dispatch_id': dispatch_id,
            'resolved': False,
            'browser_profile': browser_profile or profile_label,
            'selected_browser_or_profile': selected_browser_or_profile or browser_label,
            'browser_label': browser_label,
            'target_window_title': target_window_title,
            'hwnd': hwnd,
        }
        self._active_incident_frame = frame
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                'active_incident_frame_created',
                incident_id=frame['incident_id'],
                terminal_state=terminal_state,
                block_type=block_type,
                assistant_kind=assistant_kind,
                cdp_available=cdp_available,
                target_window_title=target_window_title,
                hwnd_available=hwnd is not None,
            )
        except Exception:
            pass
        return frame

    @staticmethod
    def _describe_user_help_needed(block_type: str) -> str:
        if block_type == 'browser_security_verification':
            return (
                'Completar la verificacion de seguridad (captcha/login) '
                'en la ventana del perfil puente de IABV, o activar '
                'CDP para usar tu Chrome normal.'
            )
        if block_type == 'visible_timeout':
            return 'Verificar que la ventana del asistente esta visible y responde.'
        return 'Revisar el estado de la herramienta externa.'

    @staticmethod
    def _describe_available_actions(
        block_type: str,
        cdp_available: bool,
        *,
        bridge_wired: bool = True,
    ) -> list[str]:
        actions = []
        if block_type == 'browser_security_verification':
            actions.append('retest_after_user_confirms')
            actions.append('show_problem_window')
            if cdp_available and bridge_wired:
                actions.append('switch_to_user_chrome_cdp')
            actions.append('manual_pasteback')
        elif block_type == 'visible_timeout':
            actions.append('retest_after_user_confirms')
            actions.append('manual_pasteback')
        else:
            actions.append('manual_pasteback')
        return actions

    def _get_active_incident(self) -> dict[str, Any] | None:
        """Return active incident frame if still valid, else None."""
        frame = getattr(self, '_active_incident_frame', None)
        if not frame:
            return None
        if frame.get('resolved'):
            return None
        if time.time() > frame.get('expires_at', 0):
            return None
        return frame

    def _resolve_incident_frame(self, resolution: str = 'resolved') -> None:
        frame = getattr(self, '_active_incident_frame', None)
        if frame:
            frame['resolved'] = True
            frame['resolution'] = resolution
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'incident_followup_resolved_or_unresolved',
                    incident_id=frame.get('incident_id', ''),
                    resolution=resolution,
                    terminal_state=frame.get('terminal_state', ''),
                )
            except Exception:
                pass

    # -- Intent tokens with weights for semantic scoring --
    _HELP_OFFER_TOKENS: tuple[str, ...] = (
        'como te ayudo', 'cómo te ayudo', 'como te puedo ayudar',
        'cómo te puedo ayudar', 'que necesitas de mi', 'qué necesitas de mí',
        'en que te ayudo', 'en qué te ayudo', 'como ayudo', 'cómo ayudo',
        'que puedo hacer', 'qué puedo hacer', 'te ayudo',
        'how can i help', 'what do you need',
        # P0.40 Task C: guided human assistance phrases
        'yo te ayudo', 'yo te ayudo con eso', 'te ayudo con eso',
        'yo te puedo ayudar', 'cuenta conmigo',
    )
    _SHOW_PROBLEM_TOKENS: tuple[str, ...] = (
        'abreme la ventana', 'ábreme la ventana', 'muestrame',
        'muéstrame', 'donde esta', 'dónde está', 'donde esta el problema',
        'dónde está el problema', 'abrelo', 'ábrelo', 'ensenname',
        'enséñame', 'show me', 'open the window',
        'muestrame la ventana', 'muéstrame la ventana',
        'donde tienes el problema', 'dónde tienes el problema',
        'abreme donde', 'ábreme donde',
        # P0.40 Task C: "abre esa verificación" / incident window phrases
        'abre esa verificacion', 'abre esa verificación',
        'abreme esa verificacion', 'ábreme esa verificación',
        'abre la verificacion', 'abre la verificación',
        'muestrame donde necesitas mi ayuda', 'muéstrame dónde necesitas mi ayuda',
        'abre la ventana donde necesitas mi ayuda',
        'muestrame eso', 'muéstrame eso',
    )
    _VISIBILITY_DISPUTE_TOKENS: tuple[str, ...] = (
        'no veo la verificacion', 'no veo la verificación',
        'no veo esa ventana', 'no veo eso', 'no veo el problema',
        'yo no veo', 'a mi no me aparece', 'a mí no me aparece',
        'yo si veo chatgpt', 'yo sí veo chatgpt',
        'a mi si me funciona', 'a mí sí me funciona',
        'yo no tengo ese problema',
    )
    _PROFILE_MISMATCH_TOKENS: tuple[str, ...] = (
        'yo ya inicie sesion', 'yo ya inicié sesión',
        'ya inicie sesion en chrome', 'ya inicié sesión en chrome',
        'yo estoy logueado', 'yo estoy logeado',
        'en mi chrome si funciona', 'en mi chrome sí funciona',
        'mi chrome esta bien', 'mi chrome está bien',
        'mi navegador si funciona', 'mi navegador sí funciona',
    )
    _RETRY_DONE_TOKENS: tuple[str, ...] = (
        'ya lo hice', 'ya lo hise', 'ya complete', 'ya completé',
        'ya pase la verificacion', 'ya pasé la verificación',
        'ya verifique', 'ya verifiqué', 'ya esta listo', 'ya está listo',
        'ya lo resolvi', 'ya lo resolví', 'done', 'i did it',
        'ya pase el captcha', 'ya pasé el captcha',
    )

    @staticmethod
    def _classify_incident_followup_intent(
        message: str,
        active_incident: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify user intent relative to an active incident frame.

        Returns ``{'intent': <str>, 'score': <float>, 'tokens_matched': [...]}``
        where intent is one of: help_offer, show_problem, visibility_dispute,
        profile_mismatch, retry_done, new_request, unrelated.
        """
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel as _Cls

        lowered = message.strip().lower()
        scores: dict[str, float] = {
            'help_offer': 0.0,
            'show_problem': 0.0,
            'visibility_dispute': 0.0,
            'profile_mismatch': 0.0,
            'retry_done': 0.0,
        }
        matched: dict[str, list[str]] = {k: [] for k in scores}

        token_map: dict[str, tuple[str, ...]] = {
            'help_offer': _Cls._HELP_OFFER_TOKENS,
            'show_problem': _Cls._SHOW_PROBLEM_TOKENS,
            'visibility_dispute': _Cls._VISIBILITY_DISPUTE_TOKENS,
            'profile_mismatch': _Cls._PROFILE_MISMATCH_TOKENS,
            'retry_done': _Cls._RETRY_DONE_TOKENS,
        }

        for intent_name, tokens in token_map.items():
            for tok in tokens:
                if tok in lowered:
                    scores[intent_name] += 1.0
                    matched[intent_name].append(tok)

        # Boost scores for contextual signals
        has_deictic = any(d in lowered for d in (
            'eso', 'ese', 'ahi', 'ahí', 'esa ventana', 'ese problema',
        ))
        assistant_ref = any(a in lowered for a in (
            'chatgpt', 'chat gpt', 'chrome', 'navegador', 'ventana', 'browser',
        ))

        if has_deictic:
            for k in scores:
                if scores[k] > 0:
                    scores[k] += 0.3
        if assistant_ref:
            for k in scores:
                if scores[k] > 0:
                    scores[k] += 0.2

        # Recency boost: more recent incidents get stronger classification
        age = time.time() - active_incident.get('created_at', 0)
        if age < 120:
            for k in scores:
                if scores[k] > 0:
                    scores[k] += 0.3
        elif age < 300:
            for k in scores:
                if scores[k] > 0:
                    scores[k] += 0.1

        best_intent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_intent]

        if best_score < 0.5:
            return {'intent': 'unrelated', 'score': 0.0, 'tokens_matched': []}

        return {
            'intent': best_intent,
            'score': round(best_score, 2),
            'tokens_matched': matched[best_intent],
        }

    def _try_handle_incident_followup(self, message: str) -> bool:
        """P0.37: Handle user messages in context of an active incident frame.

        This catches help-offer, show-problem, visibility-dispute, and
        profile-mismatch intents that the older pattern-based handlers
        miss, preventing them from falling to local chat.
        """
        incident = self._get_active_incident()
        if not incident:
            return False

        classification = self._classify_incident_followup_intent(message, incident)
        intent = classification['intent']
        if intent == 'unrelated':
            return False

        # Trace the classification
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'incident_followup_intent_classified',
                incident_id=incident.get('incident_id', ''),
                intent=intent,
                score=classification['score'],
                block_type=incident.get('block_type', ''),
                terminal_state=incident.get('terminal_state', ''),
            )
        except Exception:
            tracer = None

        # Dispatch to action
        action_taken = 'none'
        response_text = ''

        assistant_title = incident.get('assistant_title', 'Asistente externo')
        block_type = incident.get('block_type', '')
        profile_label = incident.get('profile_label', '')
        user_help = incident.get('user_help_needed', '')

        if intent == 'help_offer':
            response_text = self._build_incident_help_response(incident)
            action_taken = 'explained_help_needed'

        elif intent == 'show_problem':
            window_opened = self._try_focus_incident_window(incident)
            action_taken = 'window_open_attempted'
            # P0.40 Task E: record learning note when user requests window
            self._record_show_window_learning(incident)
            if window_opened:
                response_text = (
                    f'Enfoque la ventana del perfil puente ({profile_label}). '
                    f'Lo que yo veo: {block_type}. '
                    f'Lo que necesito de ti: {user_help} '
                    'Cuando lo hagas, escribe "ya lo hice".'
                )
            else:
                response_text = (
                    f'UNRESOLVED: No tengo hwnd/tab observable para '
                    f'el perfil puente ({profile_label}). '
                    f'El problema es: {block_type}. '
                    f'Lo que necesito de ti: {user_help} '
                    'Siguiente accion humana: busca la ventana de Chrome '
                    f'con titulo que contenga "verificacion" o "{assistant_title}" '
                    'y resuelve la verificacion ahi. '
                    'O escribe "usar mi chrome" para activar el puente CDP.'
                )

        elif intent == 'visibility_dispute':
            response_text = (
                f'Es normal que tu Chrome funcione pero IABV no pueda usarlo. '
                f'IABV usa un perfil aislado ({profile_label}) que no comparte '
                f'tu sesion de {assistant_title}. '
                'Por eso tu ves todo bien pero IABV ve verificacion de seguridad. '
                'Opciones: (1) completar verificacion en la ventana puente de IABV, '
                '(2) escribir "usar mi chrome" para que IABV use tu Chrome via CDP, '
                '(3) copiar la respuesta y pegarla aqui.'
            )
            action_taken = 'explained_profile_difference'

        elif intent == 'profile_mismatch':
            cdp_available = incident.get('cdp_available', False)
            if cdp_available:
                response_text = (
                    'Perfecto — tu Chrome tiene sesion activa pero IABV usa un perfil aislado. '
                    'Escribe "usar mi chrome" y IABV usara tu Chrome normal via CDP '
                    'sin leer cookies ni tokens. '
                    'Eso deberia resolver el bloqueo.'
                )
            else:
                response_text = (
                    'Tu Chrome tiene sesion pero IABV usa un perfil aislado diferente. '
                    'Para que IABV use tu Chrome, abrelo con: '
                    '"chrome.exe --remote-debugging-port=9222" '
                    'y luego escribe "usar mi chrome". '
                    'Mientras tanto, puedes pegar la respuesta manualmente.'
                )
            action_taken = 'offered_cdp_bridge'

        elif intent == 'retry_done':
            # Delegate to existing retest handler
            if self._try_handle_security_verification_retest(message):
                action_taken = 'retest_delegated'
                try:
                    if tracer:
                        tracer.trace(
                            'incident_followup_retest_started',
                            incident_id=incident.get('incident_id', ''),
                        )
                except Exception:
                    pass
                return True
            response_text = (
                'No puedo ejecutar un retest ahora. '
                f'Verificacion necesaria: {user_help}'
            )
            action_taken = 'retest_unavailable'

        # Trace the action selected
        try:
            if tracer:
                tracer.trace(
                    'incident_followup_action_selected',
                    incident_id=incident.get('incident_id', ''),
                    intent=intent,
                    action_taken=action_taken,
                )
        except Exception:
            pass

        if response_text:
            self._latest_response_text = response_text
            self._latest_response_meta = f'incident_followup: {intent}/{action_taken}'
            self._busy_label = ''
            self._working = False
            self._append_message(
                'assistant', 'IABV', response_text,
                f'incident_followup_{intent}',
                reasoning_path=f'incident_followup_{intent}',
                evidence_tag='observed',
            )
            self._set_live_status('idle')
            self._clear_autonomy_activity_override()
            try:
                self.dataChanged.emit()
            except Exception:
                pass

        return True

    def _build_incident_help_response(self, incident: dict[str, Any]) -> str:
        """Build a structured help response for the active incident."""
        block_type = incident.get('block_type', 'unknown')
        assistant_title = incident.get('assistant_title', 'Asistente externo')
        profile_label = incident.get('profile_label', '')
        user_help = incident.get('user_help_needed', '')
        actions = incident.get('available_actions', [])

        lines = [
            f'El problema esta en la consulta a {assistant_title}.',
            f'Lo que yo veo: {block_type} en el perfil {profile_label}.',
            f'Lo que necesito de ti: {user_help}',
        ]
        if 'switch_to_user_chrome_cdp' in actions:
            lines.append(
                'Opcion rapida: escribe "usar mi chrome" para usar tu Chrome normal.'
            )
        if 'show_problem_window' in actions:
            lines.append(
                'Puedo intentar abrir/enfocar la ventana del perfil puente '
                'si escribes "ábreme la ventana".'
            )
        lines.append('Cuando lo hayas resuelto, escribe "ya lo hice".')
        return ' '.join(lines)

    def _try_focus_incident_window(self, incident: dict[str, Any]) -> bool:
        """P0.40 Task D: Try to bring the incident browser window to the front.

        Priority:
        1. hwnd stored in incident frame -> Win32 ShowWindow/SetForegroundWindow
        2. WorldModelService active_windows -> search by title
        3. Isolated browser profile -> launch/focus via profile path
        4. CDP available + user chose "usar mi chrome" -> list/select tab
        5. None possible -> UNRESOLVED with clear next human action

        Does NOT automate login or read cookies/tokens.
        """
        incident_id = incident.get('incident_id', '')
        profile_label = incident.get('profile_label', '')
        focus_method = 'none'

        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'incident_problem_window_focus_attempted',
                incident_id=incident_id,
                profile_label=profile_label,
            )
        except Exception:
            tracer = None

        target_hwnd: int | None = None

        # 1. Try hwnd stored directly in the incident frame
        stored_hwnd = incident.get('hwnd')
        if stored_hwnd is not None:
            try:
                target_hwnd = int(stored_hwnd)
            except (ValueError, TypeError):
                pass

        # 2. If no stored hwnd, search WorldModelService.current_model()
        if target_hwnd is None:
            try:
                snapshot = self._current_world_model()
                for win in (snapshot.active_windows or []):
                    title = str(win.title or '').lower()
                    if 'chatgpt' in title or 'chrome' in title or 'verificat' in title:
                        win_hwnd = win.metadata.get('hwnd')
                        if win_hwnd is not None:
                            target_hwnd = int(win_hwnd)
                            break
            except Exception:
                pass

        # 3. Attempt focus via Win32 API
        if target_hwnd is not None:
            try:
                import ctypes
                SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(target_hwnd, SW_RESTORE)
                ctypes.windll.user32.SetForegroundWindow(target_hwnd)
                focus_method = 'win32_hwnd'
                self._trace_window_focus_result(tracer, incident_id, focus_method, True)
                return True
            except Exception:
                pass

        # 4. Try to open isolated browser profile if path is known
        browser_profile_path = incident.get('browser_profile_path', '')
        if browser_profile_path and not target_hwnd:
            try:
                import subprocess
                import os
                chrome_exe = os.environ.get('IABV_CHROME_PATH', 'chrome.exe')
                subprocess.Popen(
                    [chrome_exe, f'--user-data-dir={browser_profile_path}'],
                    creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0),
                )
                focus_method = 'browser_profile_launch'
                self._trace_window_focus_result(tracer, incident_id, focus_method, True)
                return True
            except Exception:
                pass

        # 5. CDP available — list tabs if user chose "usar mi chrome"
        import os as _os
        if _os.environ.get('IABV_PREFER_CDP_SESSION') == '1':
            try:
                cdp_available = self._detect_cdp_available()
                if cdp_available:
                    focus_method = 'cdp_tab_list'
                    self._trace_window_focus_result(tracer, incident_id, focus_method, True)
                    return True
            except Exception:
                pass

        # 6. UNRESOLVED — no hwnd, no profile, no CDP
        focus_method = 'unresolved'
        self._trace_window_focus_result(tracer, incident_id, focus_method, False)
        return False

    def _trace_window_focus_result(
        self,
        tracer: Any,
        incident_id: str,
        method: str,
        success: bool,
    ) -> None:
        """P0.40 Task G: trace window focus result."""
        try:
            if tracer is not None:
                tracer.trace(
                    'incident_problem_window_focus_result',
                    incident_id=incident_id,
                    method=method,
                    success=success,
                )
        except Exception:
            pass

    def _record_show_window_learning(self, incident: dict[str, Any]) -> None:
        """P0.40 Task E: record a learning note + PortableContext policy.

        When the user explicitly asks to see the problem window, record
        the pattern so OSES and PortableContext remember:
        'cuando haya security verification, mostrar/focalizar ventana
        antes de explicar genericamente'.
        """
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            tracer.trace(
                'incident_human_assistance_requested',
                incident_id=incident.get('incident_id', ''),
                block_type=incident.get('block_type', ''),
                user_action='show_problem_window_requested',
                policy='when_security_verification_show_window_first',
            )
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════
    # P0.6 — Shared Reality Remediation / Window Target Recovery
    # ══════════════════════════════════════════════════════════════════

    def _assess_visual_remediation(
        self,
        *,
        target_window: dict[str, Any] | None,
        capture_meta: dict[str, Any] | None,
        capture_state: dict[str, Any],
        browser_profile: str = '',
    ) -> dict[str, Any]:
        """Evaluate whether a failed visual capture can be remediated.

        Returns a dict with:
        - status: no_action_needed | remediation_available
                  | needs_user_selection | unresolved
        - reason, target_window_title, rect, proposed_action,
          safe_to_auto_try, user_message
        """
        tw = target_window or {}
        cm = capture_meta or {}
        title = str(tw.get('title') or '').strip()
        hwnd = tw.get('hwnd')
        rect = tw.get('rect')
        reason = capture_state.get('reason', 'unknown')

        # Visible window + useful capture → nothing to do
        is_low_info = bool(capture_state.get('low_information'))
        if capture_state.get('captureable') and not is_low_info:
            return {
                'status': 'no_action_needed',
                'reason': 'capture_valid',
                'target_window_title': title or 'unknown',
                'rect': rect,
                'proposed_action': 'none',
                'safe_to_auto_try': False,
                'user_message': '',
            }

        # Normalize reason: when window is captureable but image is black,
        # the capture_state reason is 'ok' — override for remediation.
        if is_low_info and reason == 'ok':
            reason = 'low_information'

        # Classify remediable scenarios
        proposed_action = 'request_user_restore'
        safe_to_auto = False
        user_msg = ''

        if reason == 'target_window_minimized_or_offscreen':
            if hwnd and isinstance(hwnd, int) and hwnd > 0:
                proposed_action = 'restore_window_by_hwnd'
                safe_to_auto = True
                user_msg = (
                    f'La ventana "{title or "objetivo"}" esta minimizada/offscreen. '
                    f'Intentare restaurarla automaticamente antes de recapturar.'
                )
            else:
                proposed_action = 'request_user_restore'
                safe_to_auto = False
                user_msg = (
                    f'La ventana objetivo esta minimizada/offscreen pero no tengo un '
                    f'hwnd valido para restaurarla. Restaura la ventana manualmente y reintenta.'
                )
            status = 'remediation_available'

        elif reason in ('low_information_pixels', 'low_information'):
            blank_prob = float(cm.get('blank_probability') or 0.0)
            if hwnd and isinstance(hwnd, int) and hwnd > 0:
                proposed_action = 'restore_and_recapture'
                safe_to_auto = True
                user_msg = (
                    f'La captura de "{title or "la ventana"}" salio negra '
                    f'(blank_probability={blank_prob:.2f}). Intentare restaurar y recapturar.'
                )
            else:
                proposed_action = 'request_user_restore'
                safe_to_auto = False
                user_msg = (
                    f'La captura salio negra (blank_probability={blank_prob:.2f}) '
                    f'y no tengo hwnd valido. Restaura la ventana y reintenta.'
                )
            status = 'remediation_available'

        elif reason == 'no_target_window':
            proposed_action = 'request_user_selection'
            safe_to_auto = False
            user_msg = (
                'No encontre la ventana objetivo. Selecciona la ventana correcta '
                'o permite usar tu navegador visible.'
            )
            status = 'needs_user_selection'

        else:
            proposed_action = 'request_user_help'
            safe_to_auto = False
            user_msg = (
                f'No pude determinar el estado de la ventana (razon: {reason}). '
                'Verifica que la herramienta este visible y reintenta.'
            )
            status = 'unresolved'

        # Detect controlled session mismatch
        bp = browser_profile or str(tw.get('title') or '')
        bp_lower = bp.lower()
        if any(kw in bp_lower for kw in ('chrome for testing', 'aislada', 'controlada')):
            if proposed_action == 'request_user_help':
                proposed_action = 'recommend_browser_selector'
            user_msg += (
                ' Tu navegador visible puede estar funcionando, pero IABV '
                'estaba mirando otra sesion. Puedes autorizar usar tu navegador visible.'
            )

        return {
            'status': status,
            'reason': reason,
            'target_window_title': title or 'unknown',
            'hwnd': hwnd,
            'rect': rect,
            'proposed_action': proposed_action,
            'safe_to_auto_try': safe_to_auto,
            'user_message': user_msg,
        }

    def _attempt_safe_remediation(
        self,
        assessment: dict[str, Any],
    ) -> dict[str, Any]:
        """Attempt a safe, reversible remediation action.

        On a real Windows desktop, calls ShowWindow(hwnd, SW_RESTORE) and
        SetForegroundWindow(hwnd) to bring a minimized/offscreen window back.
        Success is only True if the Win32 calls were made with a valid hwnd.

        Returns dict with action_taken, success, detail.
        """
        if not assessment.get('safe_to_auto_try'):
            return {
                'action_taken': 'none',
                'success': False,
                'detail': 'No safe auto-remediation available; user action required.',
            }

        proposed = assessment.get('proposed_action', '')
        if proposed not in ('restore_window_by_hwnd', 'restore_and_recapture'):
            return {
                'action_taken': 'none',
                'success': False,
                'detail': f'Action "{proposed}" is not auto-remediable.',
            }

        hwnd = assessment.get('hwnd')
        if not hwnd or not isinstance(hwnd, int) or hwnd <= 0:
            return {
                'action_taken': 'none',
                'success': False,
                'detail': 'hwnd is missing or invalid; cannot attempt Win32 restore.',
            }

        # Attempt Win32 window restore with real hwnd
        try:
            import ctypes
            SW_RESTORE = 9
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            show_result = user32.ShowWindow(hwnd, SW_RESTORE)
            fg_result = user32.SetForegroundWindow(hwnd)
            return {
                'action_taken': proposed,
                'success': True,
                'detail': (
                    f'Win32 ShowWindow({hwnd}, SW_RESTORE)={show_result}, '
                    f'SetForegroundWindow({hwnd})={fg_result}.'
                ),
            }
        except (AttributeError, OSError):
            # Not on Windows or ctypes.windll not available
            return {
                'action_taken': proposed,
                'success': False,
                'detail': 'Win32 API not available (not running on Windows desktop). '
                          'Remediation flagged for user handoff.',
            }

    def _attempt_post_remediation_recapture(
        self,
        *,
        remediation_result: dict[str, Any],
        assessment: dict[str, Any],
    ) -> dict[str, Any]:
        """Attempt ONE recapture after a successful remediation.

        Conditions (all must be true):
        - remediation_result['success'] is True
        - hwnd is a valid positive int
        - proposed_action was restore_window_by_hwnd or restore_and_recapture

        Uses PIL ImageGrab.grab(bbox=rect) if rect is available and valid,
        otherwise falls back to full-screen grab. The captured image is
        analysed in-memory (no disk write) for blank_probability.

        Returns dict with:
        - recapture_attempted: bool
        - recapture_status: 'improved' | 'still_low_information' | 'skipped' | 'error'
        - capture_useful_after: bool | None
        - blank_probability_after: float | None
        - recapture_unresolved: list[str]
        - detail: str
        """
        noop: dict[str, Any] = {
            'recapture_attempted': False,
            'recapture_status': 'skipped',
            'capture_useful_after': None,
            'blank_probability_after': None,
            'recapture_unresolved': [],
            'detail': '',
        }

        if not remediation_result.get('success'):
            noop['detail'] = 'remediation_success is False; skipping recapture.'
            return noop

        hwnd = assessment.get('hwnd')
        if not hwnd or not isinstance(hwnd, int) or hwnd <= 0:
            noop['detail'] = 'hwnd is missing or invalid; skipping recapture.'
            noop['recapture_unresolved'] = [
                'UNRESOLVED:visual_remediation_recapture_invalid_hwnd',
            ]
            return noop

        proposed = assessment.get('proposed_action', '')
        if proposed not in ('restore_window_by_hwnd', 'restore_and_recapture'):
            noop['detail'] = (
                f'proposed_action "{proposed}" does not qualify for recapture.'
            )
            return noop

        # Attempt recapture via PIL ImageGrab
        try:
            from PIL import ImageGrab  # type: ignore[import-untyped]
        except ImportError:
            noop['detail'] = 'PIL ImageGrab not available; recapture UNRESOLVED.'
            noop['recapture_unresolved'] = [
                'UNRESOLVED:visual_remediation_recapture_no_imagegrab',
            ]
            return noop

        rect = assessment.get('rect')
        try:
            if rect and isinstance(rect, (list, tuple)) and len(rect) >= 4:
                left, top, right, bottom = (
                    int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]),
                )
                if left > -30000 and top > -30000:
                    image = ImageGrab.grab(bbox=(left, top, right, bottom))
                else:
                    image = ImageGrab.grab(all_screens=True)
            else:
                image = ImageGrab.grab(all_screens=True)
        except Exception as exc:
            return {
                'recapture_attempted': True,
                'recapture_status': 'error',
                'capture_useful_after': None,
                'blank_probability_after': None,
                'recapture_unresolved': [
                    'UNRESOLVED:visual_remediation_recapture_grab_failed',
                ],
                'detail': f'ImageGrab.grab raised: {type(exc).__name__}',
            }

        # Analyse the recaptured image in-memory without optional numerical
        # dependencies.  ``ImageGrab`` returns a PIL image, whose histogram and
        # extrema are enough for the same low-information gate used elsewhere.
        try:
            rgb = image.convert('RGB')
            histogram = list(rgb.histogram())
            total_values = max(sum(histogram), 1)
            blank_values = (
                sum(histogram[0:5])
                + sum(histogram[256:261])
                + sum(histogram[512:517])
            )
            blank_probability = round(blank_values / total_values, 4)
            extrema = rgb.getextrema()
            mins = [int(pair[0]) for pair in extrema]
            maxs = [int(pair[1]) for pair in extrema]
            dynamic_range = max(maxs) - min(mins)
            colors = rgb.getcolors(maxcolors=100000)
            unique_colors = 99999 if colors is None else len(colors)
        except Exception:
            return {
                'recapture_attempted': True,
                'recapture_status': 'error',
                'capture_useful_after': None,
                'blank_probability_after': None,
                'recapture_unresolved': [
                    'UNRESOLVED:visual_remediation_recapture_analysis_failed',
                ],
                'detail': 'Recapture completed but image analysis failed.',
            }

        recapture_meta: dict[str, Any] = {
            'blank_probability': blank_probability,
            'dynamic_range': dynamic_range,
            'unique_color_count': unique_colors,
            'useful': True,
        }
        is_low = self._capture_is_low_information(recapture_meta)
        if is_low:
            recapture_meta['useful'] = False
            return {
                'recapture_attempted': True,
                'recapture_status': 'still_low_information',
                'capture_useful_after': False,
                'blank_probability_after': blank_probability,
                'recapture_unresolved': [
                    'UNRESOLVED:visual_remediation_recapture_still_low_information',
                ],
                'detail': (
                    f'Recapture completed but image is still low-information '
                    f'(blank_probability={blank_probability}).'
                ),
            }

        return {
            'recapture_attempted': True,
            'recapture_status': 'improved',
            'capture_useful_after': True,
            'blank_probability_after': blank_probability,
            'recapture_unresolved': [],
            'detail': (
                f'Recapture improved: blank_probability={blank_probability}, '
                f'dynamic_range={dynamic_range}, unique_colors={unique_colors}.'
            ),
        }

    # ------------------------------------------------------------------
    # P0.9: post-recapture response verification helpers
    # ------------------------------------------------------------------

    def _build_post_recapture_response_proof(
        self,
        *,
        response_captured: bool,
        response_capture_pending: bool,
        response_capture_mode: str,
        assistant_title: str,
        target_window: dict[str, Any] | None,
        assessment: dict[str, Any],
        capture_useful_before: bool,
        capture_useful_after: bool | None,
        recapture: dict[str, Any],
        evidence_path: str = '',
    ) -> dict[str, Any]:
        """Build compact proof dict differentiating window-observable
        from response-captured after a post-remediation recapture.

        Fields exposed:
        - target_window_title, hwnd, rect
        - capture_useful_before, capture_useful_after
        - response_captured, response_capture_pending
        - response_capture_mode
        - evidence_path (if exists)
        - window_observable (always True here — called only when recapture improved)
        - status: 'response_captured' | 'response_pending' | 'response_not_captured'
        """
        tw = target_window or {}
        hwnd = assessment.get('hwnd') or tw.get('hwnd')
        rect = assessment.get('rect') or tw.get('rect')
        title = assessment.get('target_window_title') or tw.get('title') or assistant_title

        is_pending = (
            response_capture_pending
            or response_capture_mode in {'clipboard_capture', 'dom_capture', 'browser_dom'}
        ) and not response_captured

        if response_captured:
            status = 'response_captured'
        elif is_pending:
            status = 'response_pending'
        else:
            status = 'response_not_captured'

        safe_evidence_path: str | None = None
        if evidence_path:
            try:
                from pathlib import PureWindowsPath
                safe_evidence_path = PureWindowsPath(str(evidence_path)).name or 'available'
            except Exception:
                safe_evidence_path = 'available'

        return {
            'target_window_title': title,
            'hwnd': hwnd,
            'rect': rect,
            'capture_useful_before': capture_useful_before,
            'capture_useful_after': bool(capture_useful_after),
            'response_captured': response_captured,
            'response_capture_pending': is_pending,
            'response_capture_mode': response_capture_mode,
            'evidence_path': safe_evidence_path,
            'window_observable': True,
            'status': status,
        }

    def _post_recapture_response_pending_message(
        self,
        *,
        assistant_title: str,
        response_proof: dict[str, Any],
    ) -> str:
        """Build user-facing guidance when window is observable but response
        was NOT captured."""
        title = response_proof.get('target_window_title') or assistant_title
        parts: list[str] = []
        parts.append(
            f'La ventana de {assistant_title} fue restaurada y la captura visual mejoro.'
        )
        parts.append(
            f'Sin embargo, la respuesta externa de {title} aun no fue capturada por IABV.'
        )
        mode = response_proof.get('response_capture_mode', '')
        if response_proof.get('response_capture_pending'):
            if mode in ('dom_capture', 'browser_dom'):
                parts.append(
                    'IABV intentara capturar la respuesta automaticamente desde la sesion aislada.'
                )
            elif mode == 'clipboard_capture':
                parts.append(
                    'IABV intentara capturar la respuesta desde el portapapeles.'
                )
            else:
                parts.append(
                    'La captura de respuesta queda pendiente.'
                )
        else:
            parts.append(
                f'Para completar: abre {title}, copia la respuesta y pegala en IABV, '
                f'o permite que IABV reintente la captura.'
            )
        return ' '.join(parts)

    def _trace_post_recapture_response_verification(
        self,
        *,
        assistant_kind: str,
        response_proof: dict[str, Any],
    ) -> None:
        """Log a post_recapture_response_verification event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                'post_recapture_response_verification',
                assistant_kind=assistant_kind,
                target_window_title=response_proof.get('target_window_title', ''),
                hwnd_present=response_proof.get('hwnd') is not None and response_proof.get('hwnd') != 0,
                window_observable=response_proof.get('window_observable', False),
                response_captured=response_proof.get('response_captured', False),
                response_capture_pending=response_proof.get('response_capture_pending', False),
                response_capture_mode=response_proof.get('response_capture_mode', ''),
                status=response_proof.get('status', ''),
                capture_useful_before=response_proof.get('capture_useful_before', False),
                capture_useful_after=response_proof.get('capture_useful_after', False),
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # P0.10: post-recapture response capture retry
    # ------------------------------------------------------------------

    def _compact_response_retry_reason(self, reason: Any) -> str:
        """Keep retry reasons useful without leaking local paths or emails."""
        text = str(reason or '').strip()
        if not text:
            return ''
        text = re.sub(
            r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*([^\\/:*?"<>|\r\n]+)',
            r'...\\\1',
            text,
        )
        text = re.sub(r'/(?:[^/\s]+/)+([^/\s]+)', r'.../\1', text)
        text = re.sub(r'[\w.+-]+@[\w.-]+', '[email]', text)
        return text[:240]

    def _attempt_post_recapture_response_retry(
        self,
        *,
        consultation_metadata: dict[str, Any],
        payload: dict[str, Any],
        assistant_title: str,
        assistant_kind: str,
        dispatch_id: str,
    ) -> dict[str, Any]:
        """Attempt ONE response capture retry via reingest_existing_session.

        Uses AutonomousEvolutionService.reingest_existing_session() which
        re-captures from the existing browser session without re-sending
        the original consultation.  Returns a dict with:
        - retry_attempted: bool
        - response_captured: bool
        - retry_status: 'success' | 'no_response' | 'error' | 'unavailable'
        - reason: str
        """
        self._trace_response_capture_retry(
            event='response_capture_retry_started',
            assistant_kind=assistant_kind,
            dispatch_id=dispatch_id,
            status='started',
            reason='',
        )
        service = getattr(self, 'autonomous_evolution_service', None)
        if service is None:
            result = {
                'retry_attempted': False,
                'response_captured': False,
                'retry_status': 'unavailable',
                'reason': 'autonomous_evolution_service_not_available',
            }
            self._trace_response_capture_retry(
                event='response_capture_retry_result',
                assistant_kind=assistant_kind,
                dispatch_id=dispatch_id,
                status='unavailable',
                reason='service_not_available',
            )
            return result

        existing_consultation = {
            'selected_tool_id': str(consultation_metadata.get('selected_tool_id') or ''),
            'assistant_kind': str(consultation_metadata.get('assistant_kind') or assistant_kind),
            'response_capture_mode': str(consultation_metadata.get('response_capture_mode') or ''),
            'session_scope': str(consultation_metadata.get('session_scope') or ''),
            'session_label': str(consultation_metadata.get('session_label') or ''),
            'session_profile_dir': str(consultation_metadata.get('session_profile_dir') or ''),
            'thread_key': str(consultation_metadata.get('thread_key') or ''),
            'thread_title': str(consultation_metadata.get('thread_title') or ''),
            'isolated_session': bool(consultation_metadata.get('isolated_session')),
            'site_id': str(consultation_metadata.get('site_id') or ''),
            'diagnostic_category': str(consultation_metadata.get('diagnostic_category') or ''),
            'incident_kind': str(consultation_metadata.get('incident_kind') or ''),
            'pending_issue_id': str(consultation_metadata.get('pending_issue_id') or ''),
        }
        user_goal = str(self._last_user_goal or '').strip() or f'respuesta de {assistant_title}'

        executor: ThreadPoolExecutor | None = None
        try:
            executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix='ccvm-response-retry',
            )
            future = executor.submit(
                service.reingest_existing_session,
                existing_consultation=existing_consultation,
                adaptive_payload=dict(payload),
                user_goal=user_goal,
                source=f'post_recapture_retry_{dispatch_id}',
            )
            reingest = future.result(
                timeout=self._POST_RECAPTURE_RESPONSE_RETRY_TIMEOUT_S,
            )
        except FutureTimeoutError:
            try:
                future.cancel()  # type: ignore[name-defined]
            except Exception:
                pass
            result = {
                'retry_attempted': True,
                'response_captured': False,
                'retry_status': 'timeout',
                'reason': 'reingest_timeout',
            }
            self._trace_response_capture_retry(
                event='response_capture_retry_result',
                assistant_kind=assistant_kind,
                dispatch_id=dispatch_id,
                status='timeout',
                reason=result['reason'],
            )
            return result
        except Exception as exc:
            result = {
                'retry_attempted': True,
                'response_captured': False,
                'retry_status': 'error',
                'reason': f'reingest_exception: {type(exc).__name__}',
            }
            self._trace_response_capture_retry(
                event='response_capture_retry_result',
                assistant_kind=assistant_kind,
                dispatch_id=dispatch_id,
                status='error',
                reason=result['reason'],
            )
            return result
        finally:
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)

        captured = bool(reingest.get('pre_capture_ingested'))
        reason = self._compact_response_retry_reason(
            reingest.get('reason') or ('captured' if captured else 'no_response')
        )
        status = 'success' if captured else 'no_response'

        result = {
            'retry_attempted': True,
            'response_captured': captured,
            'retry_status': status,
            'reason': reason,
        }
        self._trace_response_capture_retry(
            event='response_capture_retry_result',
            assistant_kind=assistant_kind,
            dispatch_id=dispatch_id,
            status=status,
            reason=reason,
        )
        return result

    def _trace_response_capture_retry(
        self,
        *,
        event: str,
        assistant_kind: str,
        dispatch_id: str,
        status: str,
        reason: str,
    ) -> None:
        """Log response_capture_retry_started / _result to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                event,
                assistant_kind=assistant_kind,
                dispatch_id=dispatch_id,
                status=status,
                reason=reason,
            )
        except Exception:
            pass

    def _trace_visual_remediation_attempted(
        self,
        *,
        assistant_kind: str,
        target_window_title: str,
        hwnd: Any,
        rect: Any,
        reason: str,
        proposed_action: str,
        action_taken: str,
        result_status: str,
        capture_useful_before: bool,
        capture_useful_after: bool | None = None,
        blank_probability_before: float = 0.0,
        blank_probability_after: float | None = None,
        remediation_success: bool | None = None,
        remediation_detail_code: str = '',
        recapture_status: str = 'skipped',
        unresolved: list[str] | None = None,
    ) -> None:
        """Log a visual_remediation_attempted event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(
                'visual_remediation_attempted',
                assistant_kind=assistant_kind,
                target_window_title=target_window_title,
                hwnd_present=hwnd is not None and hwnd != 0,
                rect=rect,
                reason=reason,
                proposed_action=proposed_action,
                action_taken=action_taken,
                result_status=result_status,
                capture_useful_before=capture_useful_before,
                capture_useful_after=capture_useful_after,
                blank_probability_before=blank_probability_before,
                blank_probability_after=blank_probability_after,
                remediation_success=remediation_success,
                remediation_detail_code=remediation_detail_code,
                recapture_status=recapture_status,
                unresolved=unresolved or [],
            )
        except Exception:
            pass

    def _remediation_user_message(
        self,
        *,
        assistant_title: str,
        assessment: dict[str, Any],
        remediation_result: dict[str, Any],
    ) -> str:
        """Build a practical, non-technical message for the user after
        a remediation attempt."""
        parts: list[str] = []
        title = assessment.get('target_window_title', 'la herramienta')
        parts.append(f'Yo intente capturar: {assistant_title}')

        reason = assessment.get('reason', '')
        if 'minimized' in reason or 'offscreen' in reason:
            parts.append(
                f'La ventana "{title}" estaba minimizada/offscreen o devolvio imagen negra.'
            )
        elif 'low_information' in reason:
            parts.append(f'La captura de "{title}" salio negra o sin informacion util.')
        elif 'no_target' in reason:
            parts.append('No encontre la ventana objetivo.')
        else:
            parts.append(f'La captura de "{title}" no fue valida ({reason}).')

        action = remediation_result.get('action_taken', 'none')
        success = remediation_result.get('success', False)
        if action != 'none' and success:
            parts.append(
                'Intente restaurar la ventana automaticamente; necesito reintentar la consulta/captura para verificar.'
            )
        elif action != 'none':
            parts.append(
                'Intente restaurar la ventana pero no fue posible en este entorno.'
            )

        parts.append(
            'Tu navegador visible puede estar funcionando, pero IABV estaba mirando otra sesion.'
        )
        parts.append(
            'Accion recomendada: restaura/selecciona esta ventana o permite usar tu navegador visible.'
        )
        parts.append('Puedo reintentar despues de eso.')
        return '\n'.join(parts)

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
        entries: list[dict[str, Any]] = []
        for item in self._chat_messages[-8:]:
            entry: dict[str, Any] = {
                'role': item.get('role', ''),
                'text': item.get('text', ''),
                'meta': item.get('meta', ''),
            }
            evidence_tag = item.get('evidenceTag', item.get('evidence_tag', ''))
            if evidence_tag:
                entry['evidence_tag'] = evidence_tag
            entries.append(entry)
        return entries

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

    _CHAT_STALL_THRESHOLD_MS = 1500.0  # perceptible stall threshold

    def _trace_chat_stall(
        self,
        *,
        elapsed_ms: float,
        timed_out: bool,
        message_summary: str,
    ) -> None:
        """Trace a chat stall / query freeze via RuntimeAuditTracer.

        If the shortcut analysis wait exceeded the perceptible threshold
        or timed out, also fire FreezeIncidentReporter for structured
        incident capture.
        """
        if elapsed_ms < self._CHAT_STALL_THRESHOLD_MS and not timed_out:
            return
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import (
                get_runtime_tracer,
            )
            tracer = get_runtime_tracer()
            iid = getattr(self, '_active_interaction_id', None)
            tracer.trace_freeze_incident(
                'chat_stall',
                severity='high' if timed_out else 'medium',
                duration_ms=elapsed_ms,
                dominant_phase='_chat_shortcut_analysis',
                interaction_id=iid or '',
            )
        except Exception:
            pass
        # Record stall in the active interaction lifecycle
        iid = getattr(self, '_active_interaction_id', None)
        if iid:
            lifecycle = getattr(self, '_chat_interaction_lifecycle', None)
            if lifecycle is not None:
                try:
                    lifecycle.record_stall(iid, {
                        'duration_ms': elapsed_ms,
                        'timestamp': '',
                    })
                except Exception:
                    pass
        reporter = getattr(self, '_freeze_incident_reporter', None)
        if reporter is None:
            return
        try:
            reporter.capture_chat_stall(
                duration_ms=elapsed_ms,
                timed_out=timed_out,
                message_summary=message_summary,
            )
        except Exception:
            pass

    # Outcomes that count as final episode closure.
    _FINAL_INTERACTION_OUTCOMES: frozenset[str] = frozenset({
        'resolved', 'failed', 'blocked',
    })

    def _resolve_active_interaction(
        self,
        *,
        outcome: str = 'resolved',
        provider: str = '',
    ) -> None:
        """Close the active interaction episode and reset watchdog state.

        Non-final outcomes (``prepared``, ``awaiting_external_response``,
        ``reused_context``) record the outcome in the lifecycle but
        keep the interaction_id and watchdog state active so that the
        episode stays open until true resolution.

        Terminal non-successful outcomes (``blocked``, ``failed``) close
        the episode and clear watchdog state, but ``resolved=False``.
        """
        interaction_id = getattr(self, '_active_interaction_id', None)
        if not interaction_id:
            return
        is_final = outcome in self._FINAL_INTERACTION_OUTCOMES
        lifecycle = getattr(self, '_chat_interaction_lifecycle', None)
        if lifecycle is not None:
            try:
                lifecycle.resolve_interaction(
                    interaction_id,
                    outcome=outcome,
                    provider=provider,
                )
            except Exception:
                pass
        if is_final:
            self._active_interaction_id = None
            watchdog = getattr(self, '_ui_heartbeat_watchdog', None)
            if watchdog is not None:
                watchdog.set_query_pending(False)
                watchdog.set_active_interaction(None)
            self._set_live_status('idle')
            self._promote_metacognition_after_resolution()

    # ── Dispatch-id helpers (stale-result guard) ────────────────
    def _new_dispatch_id(self, task_name: str) -> str:
        """Create a unique dispatch id for *task_name* and register it."""
        import uuid
        did = uuid.uuid4().hex
        self._active_dispatch_ids[task_name] = did
        return did

    def _is_dispatch_active(self, task_name: str, dispatch_id: str) -> bool:
        return self._active_dispatch_ids.get(task_name) == dispatch_id

    def _invalidate_dispatch(self, task_name: str) -> None:
        self._active_dispatch_ids.pop(task_name, None)

    # ── Runtime audit helpers for dispatch lifecycle events ─────
    def _trace_dispatch_started(
        self,
        *,
        task_name: str,
        dispatch_id: str = '',
        provider: str = '',
        source: str = '',
        user_goal_excerpt: str = '',
        visible_busy_label: str = '',
    ) -> None:
        """Log a dispatch started event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_dispatch_started(
                task_name=task_name,
                dispatch_id=dispatch_id,
                interaction_id=getattr(self, '_active_interaction_id', '') or '',
                provider=provider,
                source=source,
                user_goal_excerpt=user_goal_excerpt,
                visible_busy_label=visible_busy_label,
            )
        except Exception:
            pass

    def _trace_dispatch_terminal(
        self,
        *,
        task_name: str,
        dispatch_id: str = '',
        terminal_state: str,
        provider: str = '',
        reason: str = '',
        user_visible_message: bool = True,
    ) -> None:
        """Log a dispatch terminal event to RuntimeAuditTracer."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_dispatch_terminal(
                task_name=task_name,
                dispatch_id=dispatch_id,
                terminal_state=terminal_state,
                interaction_id=getattr(self, '_active_interaction_id', '') or '',
                provider=provider,
                reason=reason,
                user_visible_message_present=user_visible_message,
            )
        except Exception:
            pass

    # ── Worker timeout watchdog (Sub-objective A) ──────────────
    def _schedule_worker_timeout(
        self,
        *,
        done_event: threading.Event,
        task_name: str,
        timeout_s: float,
        dispatch_id: str = '',
    ) -> None:
        """Fire taskFailed if *done_event* is not set within *timeout_s*.

        Runs a lightweight daemon thread that waits on the event; if it
        times out and ``_working`` is still True, it emits ``taskFailed``
        so the UI never stays in "consultando..." indefinitely.

        When *dispatch_id* is provided the watchdog also invalidates it
        so that a late-finishing worker with the same id will be discarded.
        """
        def _watchdog() -> None:
            if done_event.wait(timeout=timeout_s):
                return  # worker finished in time
            if not self._working:
                return  # already resolved by other path
            if dispatch_id and not self._is_dispatch_active(task_name, dispatch_id):
                return  # superseded by a newer dispatch
            if dispatch_id:
                self._invalidate_dispatch(task_name)
            self._trace_dispatch_terminal(
                task_name=task_name,
                dispatch_id=dispatch_id,
                terminal_state='timeout',
                reason=f'watchdog fired after {int(timeout_s)}s',
            )
            self.taskFailed.emit(
                task_name,
                f'La operacion ({task_name}) supero el tiempo maximo de {int(timeout_s)}s. '
                'Puedes intentar de nuevo o verificar que las herramientas esten accesibles.',
            )

        threading.Thread(target=_watchdog, daemon=True, name=f'{task_name}-timeout').start()

    # ── Pressure gating for deferred heavy work (Sub-objective B) ──
    def _should_defer_heavy_work(self) -> bool:
        """Return True when heavy background ops should be skipped.

        Uses AdaptiveTaskOrchestrator._assess_resource_pressure() to read
        live environment risk signals.  Under HIGH or CRITICAL pressure
        the UI thread must stay free for user interaction.
        """
        try:
            pressure = self.adaptive_orchestrator._assess_resource_pressure()
            return bool(pressure.get('under_pressure'))
        except Exception:
            return False

    # ── P0.38: Resource Quiescence Gate ──

    def _evaluate_consultation_quiescence(
        self, assistant_kind: str,
    ) -> dict[str, Any]:
        """Decide whether an external consultation can run now.

        Returns dict with:
        - decision: run_now | defer | ask_user | cleanup_needed
        - pressure_level: none | high | critical
        - reason: human-readable explanation
        - retry_after_s: suggested delay before retry (0 if run_now)
        """
        result: dict[str, Any] = {
            'decision': 'run_now',
            'pressure_level': 'none',
            'reason': '',
            'retry_after_s': 0,
        }
        try:
            pressure = self.adaptive_orchestrator._assess_resource_pressure()
        except Exception:
            return result
        if not pressure.get('under_pressure'):
            return result
        critical = bool(pressure.get('critical'))
        result['pressure_level'] = 'critical' if critical else 'high'
        signals = list(pressure.get('active_signals') or [])
        if critical:
            if any(s in signals for s in ('disk_critical', 'disk_space_critical')):
                result['decision'] = 'cleanup_needed'
                result['reason'] = (
                    'Disco critico. No puedo abrir herramientas externas '
                    'hasta liberar espacio.'
                )
                result['retry_after_s'] = 60
            else:
                result['decision'] = 'defer'
                result['reason'] = (
                    'Presion critica de recursos (RAM/CPU). '
                    'Diferire la consulta hasta que baje la presion.'
                )
                result['retry_after_s'] = 30
        else:
            result['decision'] = 'defer'
            result['reason'] = (
                'Presion alta de recursos. Diferire brevemente '
                'la consulta externa.'
            )
            result['retry_after_s'] = 15
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_consultation_quiescence(
                decision=result['decision'],
                assistant_kind=assistant_kind,
                pressure_level=result['pressure_level'],
                reason=result['reason'],
            )
        except Exception:
            pass
        return result

    # ── P0.39: Universal Capability Readiness ──

    def _assess_external_readiness(
        self, assistant_kind: str,
    ) -> dict[str, Any]:
        """Build a universal readiness contract before external consultation.

        Assembles from existing pieces:
        WorldModelSnapshot, RuntimeAuditTracer, _build_assistant_web_skill_profile,
        _evaluate_consultation_quiescence, _detect_cdp_available.

        Returns a dict with action_possible=True/False plus structured
        blocking_reason and next_human_action when not ready.
        Does NOT create a new service — read-only assembly from existing sources.
        """
        now = time.time()
        title = self._assistant_display_name(assistant_kind)
        readiness: dict[str, Any] = {
            'tool_id': f'external_assistant_{self._normalize_provider(assistant_kind)}',
            'assistant_kind': assistant_kind,
            'assistant_title': title,
            'device_state': 'unknown',
            'build_state': 'unknown',
            'resource_pressure': 'none',
            'session_mode': 'unknown',
            'session_selected': 'unknown',
            'auth_state': 'unknown',
            'security_block_state': 'none',
            'observation_permission': 'unknown',
            'action_possible': True,
            'capture_possible': False,
            'response_capture_mode': 'manual_pasteback',
            'confidence': 0.0,
            'blocking_reason': '',
            'next_human_action': '',
            'evidence_refs': [],
            'last_verified_at': now,
        }
        blockers: list[str] = []

        # 1. Build staleness check
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            fp = tracer.trace_build_fingerprint(
                workspace=str(getattr(self.config, 'workspace_root', '')),
            )
            if fp.get('stale'):
                readiness['build_state'] = 'stale'
                blockers.append('build_stale')
                readiness['evidence_refs'].append(f'build_head={fp.get("head", "?")[:12]}')
            else:
                readiness['build_state'] = 'current'
                readiness['evidence_refs'].append(f'build_head={fp.get("head", "?")[:12]}')
        except Exception:
            readiness['build_state'] = 'unknown'

        # 2. Resource pressure
        quiescence = self._evaluate_consultation_quiescence(assistant_kind)
        readiness['resource_pressure'] = quiescence['pressure_level']
        if quiescence['decision'] != 'run_now':
            blockers.append(f'resource_pressure_{quiescence["pressure_level"]}')
            readiness['evidence_refs'].append(f'quiescence={quiescence["decision"]}')
            readiness['retry_after_s'] = quiescence.get('retry_after_s', 15)

        # 3. Web skill profile (session, auth, window, CDP)
        profile = self._build_assistant_web_skill_profile(assistant_kind)
        readiness['session_mode'] = profile['active_session_mode']
        readiness['auth_state'] = profile['auth_status']

        # 4. CDP probe
        cdp_status = profile.get('cdp_status', 'unknown')
        readiness['evidence_refs'].append(f'cdp={cdp_status}')
        if cdp_status == 'available':
            readiness['capture_possible'] = True
            readiness['response_capture_mode'] = 'cdp'
            readiness['observation_permission'] = 'cdp_available'

        # 5. Session selected
        import os as _os
        if _os.environ.get('IABV_PREFER_CDP_SESSION') == '1' and cdp_status == 'available':
            readiness['session_selected'] = 'governed_user_chrome_cdp'
        elif profile['active_session_mode'] == 'isolated_profile':
            readiness['session_selected'] = 'isolated_profile'
        elif profile['active_session_mode'] == 'manual_pasteback':
            readiness['session_selected'] = 'manual_handoff'
        else:
            readiness['session_selected'] = profile['active_session_mode']

        # 6. Window / hwnd
        if profile.get('window_status') == 'found':
            readiness['device_state'] = 'window_found'
            readiness['evidence_refs'].append(f'hwnd={profile.get("window_hwnd", "?")}')
        else:
            readiness['device_state'] = 'no_window'

        # 7. Security block from recent history
        if profile.get('last_block_reason'):
            if 'security_verification' in profile['last_block_reason']:
                readiness['security_block_state'] = 'security_verification'
                blockers.append('blocked_by_security_verification')
            elif 'blocked' in profile['last_block_reason']:
                readiness['security_block_state'] = profile['last_block_reason']
                blockers.append(profile['last_block_reason'])

        # 8. Capture possible without CDP
        if not readiness['capture_possible']:
            if readiness['auth_state'] == 'authenticated' and readiness['device_state'] == 'window_found':
                readiness['capture_possible'] = True
                readiness['response_capture_mode'] = 'dom_observation'

        # 9. Confidence score
        confidence = 1.0
        if readiness['build_state'] == 'stale':
            confidence -= 0.3
        if readiness['resource_pressure'] in ('high', 'critical'):
            confidence -= 0.2
        if readiness['security_block_state'] != 'none':
            confidence -= 0.3
        if readiness['auth_state'] in ('security_verification', 'logged_out'):
            confidence -= 0.2
        if not readiness['capture_possible']:
            confidence -= 0.1
        readiness['confidence'] = max(0.0, round(confidence, 2))

        # 10. Overall action_possible + blocking_reason + next_human_action
        if blockers:
            if 'build_stale' in blockers:
                readiness['action_possible'] = False
                readiness['blocking_reason'] = 'build_stale'
                readiness['next_human_action'] = (
                    'El runtime no esta actualizado. Alinea el runtime con '
                    'origin/main antes de intentar consultas externas.'
                )
            elif any('resource_pressure' in b for b in blockers):
                readiness['action_possible'] = False
                readiness['blocking_reason'] = f'resource_pressure_{readiness["resource_pressure"]}'
                readiness['next_human_action'] = quiescence.get('reason', '')
            elif 'blocked_by_security_verification' in blockers:
                readiness['action_possible'] = False
                readiness['blocking_reason'] = 'security_verification_recent'
                profile_path = profile.get('browser_profile_path', '')
                profile_label = 'chatgpt_program_session/browser_profile'
                if profile_path:
                    parts = str(profile_path).replace('\\', '/').split('/')
                    if len(parts) >= 2:
                        profile_label = '/'.join(parts[-2:])
                readiness['next_human_action'] = (
                    f'IABV usa un perfil aislado ({profile_label}), '
                    f'no tu Chrome normal. '
                    f'Resuelve la verificacion/login en la ventana que abrio IABV '
                    f'y escribe "ya lo hice". '
                    f'O escribe "usar mi chrome" si tienes Chrome con '
                    f'--remote-debugging-port abierto.'
                )

        # Trace the readiness assessment
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_external_readiness(
                assistant_kind=assistant_kind,
                action_possible=readiness['action_possible'],
                confidence=readiness['confidence'],
                blocking_reason=readiness['blocking_reason'],
                session_selected=readiness['session_selected'],
                security_block=readiness['security_block_state'],
                capture_mode=readiness['response_capture_mode'],
            )
        except Exception:
            pass

        return readiness

    def _queue_ui_call(self, method_name: str, *args: object) -> None:
        """Thread-safe UI call: QMetaObject if QObject, direct call otherwise.

        - If self is a QObject, uses QMetaObject.invokeMethod with QueuedConnection.
        - If self is a test stub (SimpleNamespace), calls method directly.
        - Captures all exceptions and traces retry_queue_failed.
        """
        try:
            from PySide6.QtCore import QObject
            is_qobject = isinstance(self, QObject)
        except ImportError:
            is_qobject = False

        if is_qobject:
            try:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                q_args = [Q_ARG(str, str(a)) for a in args]
                QMetaObject.invokeMethod(
                    self, method_name,
                    Qt.ConnectionType.QueuedConnection,
                    *q_args,
                )
                return
            except (RuntimeError, TypeError) as exc:
                # Object deleted or wrong signature — trace and fall through
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace(
                        'retry_queue_failed',
                        method=method_name,
                        error=str(exc)[:120],
                        path='qobject_deleted_or_type_error',
                    )
                except Exception:
                    pass
                return

        # Not a QObject (test stub / SimpleNamespace) — call directly
        method = getattr(self, method_name, None)
        if method is not None and callable(method):
            try:
                method(*[str(a) for a in args])
            except Exception as exc:
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace(
                        'retry_queue_failed',
                        method=method_name,
                        error=str(exc)[:120],
                        path='direct_call_fallback',
                    )
                except Exception:
                    pass

    _deferred_retry_generation: int = 0
    _DEFERRED_RETRY_COOLDOWN_S: float = 10.0
    _DEFERRED_RETRY_MAX: int = 3
    _deferred_retry_count: int = 0
    _deferred_retry_last_ts: float = 0.0

    def _schedule_deferred_consultation_retry(
        self, assistant_kind: str, delay_s: float,
        *, dispatch_id: str = '',
    ) -> None:
        """Schedule a background retry — Qt-safe: never mutates UI from thread."""
        now = time.time()
        if now - self._deferred_retry_last_ts < self._DEFERRED_RETRY_COOLDOWN_S:
            return
        if self._deferred_retry_count >= self._DEFERRED_RETRY_MAX:
            return
        self._deferred_retry_generation += 1
        gen = self._deferred_retry_generation
        self._deferred_retry_count += 1
        self._deferred_retry_last_ts = now

        def _retry() -> None:
            import time as _t
            _t.sleep(max(delay_s, 5.0))
            if gen != self._deferred_retry_generation:
                return
            quiescence = self._evaluate_consultation_quiescence(assistant_kind)
            if quiescence['decision'] == 'run_now':
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace_consultation_quiescence(
                        decision='retry_triggered',
                        assistant_kind=assistant_kind,
                        pressure_level='none',
                        reason='quiescence retry after deferred',
                    )
                except Exception:
                    pass
                self._queue_ui_call('_on_deferred_retry_ready', assistant_kind)
            else:
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace_consultation_quiescence(
                        decision='retry_still_deferred',
                        assistant_kind=assistant_kind,
                        pressure_level=quiescence['pressure_level'],
                        reason=quiescence['reason'],
                    )
                except Exception:
                    pass
                self._queue_ui_call('_on_deferred_retry_still_blocked', assistant_kind)
        threading.Thread(target=_retry, daemon=True, name='quiescence-retry').start()

    @Slot(str)
    def _on_deferred_retry_ready(self, assistant_kind: str) -> None:
        """Qt main-thread slot: retry consultation after quiescence cleared."""
        self._run_external_consultation(assistant_kind, announce=True)

    @Slot(str)
    def _on_deferred_retry_still_blocked(self, assistant_kind: str) -> None:
        """Qt main-thread slot: inform user retry still deferred."""
        msg = (
            f'Intente reintentar la consulta a '
            f'{self._assistant_display_name(assistant_kind)} '
            f'pero la presion de recursos sigue alta. '
            f'Puedes intentar de nuevo cuando baje la presion.'
        )
        self._latest_response_text = msg
        self._latest_response_meta = 'consultation_retry_still_deferred'
        self._append_message('assistant', 'IABV', msg, 'consultation_retry_still_deferred')
        self._working = False
        self.dataChanged.emit()

    # ── P0.38: AssistantWebSkillProfile ──

    _PROVIDER_ALIASES: dict[str, str] = {
        'chatgpt': 'chatgpt', 'ChatGPT': 'chatgpt',
        'chatgpt_web': 'chatgpt', 'openai': 'chatgpt',
        'claude': 'claude', 'Claude': 'claude',
        'gemini': 'gemini', 'Gemini': 'gemini',
    }

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        """Normalize provider/assistant_kind to canonical lowercase form."""
        if not provider:
            return ''
        canonical = ControlCenterViewModel._PROVIDER_ALIASES.get(provider)
        if canonical:
            return canonical
        return provider.strip().lower().replace(' ', '_')

    _WEB_SKILL_SESSION_MODES = (
        'isolated_profile', 'governed_user_bridge',
        'manual_pasteback', 'api_if_available',
    )
    _WEB_SKILL_AUTH_STATES = (
        'unknown', 'authenticated', 'security_verification', 'logged_out',
    )

    def _build_assistant_web_skill_profile(
        self, assistant_kind: str,
    ) -> dict[str, Any]:
        """Build a structured web skill profile for an assistant.

        Not a new service — structured metadata built from existing sources:
        ToolRegistry, WorldModel, ExternalAssistantToolAdapter, RuntimeAuditTracer.
        """
        title = self._assistant_display_name(assistant_kind)
        profile: dict[str, Any] = {
            'assistant_kind': assistant_kind,
            'assistant_title': title,
            'session_modes': list(self._WEB_SKILL_SESSION_MODES),
            'active_session_mode': 'unknown',
            'browser_profile_path': '',
            'cdp_status': 'unknown',
            'window_status': 'unknown',
            'auth_status': 'unknown',
            'capture_modes': ['manual_pasteback'],
            'last_scan_ts': 0.0,
            'last_block_reason': '',
            'action_grammar': [
                'open_profile', 'focus_window', 'ask_question',
                'wait_for_response', 'capture_response', 'verify_response',
                'retry_after_user_done', 'fallback_manual',
            ],
        }
        # Enrich from WorldModel — use active_windows contract, not wm.windows
        try:
            wm = self._current_world_model()
            if wm:
                windows = list(wm.active_windows or [])
                kind_lower = self._normalize_provider(assistant_kind)
                for w in windows:
                    w_title = str(getattr(w, 'title', '') or '').lower()
                    if kind_lower in w_title or title.lower() in w_title:
                        profile['window_status'] = 'found'
                        meta = getattr(w, 'metadata', None) or {}
                        profile['window_hwnd'] = meta.get('hwnd') or getattr(w, 'hwnd', None)
                        break
        except Exception:
            pass
        # Enrich from CDP probe
        try:
            if hasattr(self, '_detect_cdp_available'):
                cdp_result = self._detect_cdp_available()
                if isinstance(cdp_result, dict):
                    profile['cdp_status'] = 'available' if cdp_result.get('available') else 'unavailable'
                    if cdp_result.get('available'):
                        profile['capture_modes'].insert(0, 'cdp')
                        profile['active_session_mode'] = 'governed_user_bridge'
        except Exception:
            pass
        # Enrich from recent dispatch history
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            lifecycles = tracer.recent_dispatch_lifecycles(limit=10)
            for lc in lifecycles:
                if lc.get('provider') == assistant_kind:
                    ts = lc.get('terminal_state', '')
                    if ts == 'blocked_by_security_verification':
                        profile['auth_status'] = 'security_verification'
                        profile['last_block_reason'] = 'security_verification'
                    elif ts == 'response_captured':
                        profile['auth_status'] = 'authenticated'
                    elif 'blocked' in ts:
                        profile['last_block_reason'] = ts
                    break
        except Exception:
            pass
        # Browser profile path
        try:
            profile['browser_profile_path'] = str(
                Path(self.config.workspace_root)
                / 'data' / 'tool_teaching' / 'external_assistants'
                / f'{assistant_kind}_program_session' / 'browser_profile'
            )
        except Exception:
            pass
        if profile['active_session_mode'] == 'unknown':
            if profile['window_status'] == 'found':
                profile['active_session_mode'] = 'isolated_profile'
            else:
                profile['active_session_mode'] = 'manual_pasteback'
        profile['last_scan_ts'] = time.time()
        return profile

    def _scan_assistant_web_skill(
        self, assistant_kind: str,
    ) -> dict[str, Any]:
        """P0.38 Task D: Governed scan of a web tool's availability.

        OBSERVE → SELECT_SESSION → VERIFY_ACCESS → report result.
        Does not ACT — only observes and reports. Never reads cookies/tokens.
        """
        profile = self._build_assistant_web_skill_profile(assistant_kind)
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_assistant_web_skill_scan(
                assistant_kind=assistant_kind,
                phase='scan_complete',
                auth_status=profile['auth_status'],
                session_mode=profile['active_session_mode'],
                cdp_available=profile['cdp_status'] == 'available',
                window_found=profile['window_status'] == 'found',
                detail=profile.get('last_block_reason', ''),
            )
        except Exception:
            pass
        return profile

    # ── P0.38: Devin Repair Worker ──

    def _build_repair_packet(self, issue_summary: str) -> dict[str, Any]:
        """Build a structured repair request packet from PortableContext cache.

        Uses latest cache/latest.json — never calls build_package() synchronously
        to avoid freezing the UI thread.
        No PII, no cookies, no tokens.
        """
        packet: dict[str, Any] = {
            'type': 'repair_request',
            'issue_summary': issue_summary[:500],
            'timestamp': time.time(),
            'portable_context_excerpt': {},
            'recent_failures': [],
            'recommended_action': '',
        }
        try:
            pcs = getattr(self, 'portable_context_service', None)
            if pcs:
                # Use cached package — never heavy rebuild in UI path
                pkg = getattr(pcs, 'current_package', None)
                if pkg is None and hasattr(pcs, 'latest_cache'):
                    pkg = pcs.latest_cache
                if pkg is None:
                    latest_path = Path(self.config.workspace_root) / 'data' / 'evolution' / 'portable_context' / 'latest.json'
                    if latest_path.exists():
                        import json as _json
                        try:
                            raw = _json.loads(latest_path.read_text(encoding='utf-8'))
                            pkg = raw
                        except Exception:
                            pass
                if pkg is not None:
                    ctx = pkg.get('context', None) if isinstance(pkg, dict) else (getattr(pkg, 'context', None) or {})
                    if isinstance(ctx, dict):
                        packet['portable_context_excerpt'] = {
                            k: v for k, v in ctx.items()
                            if k in (
                                'cloud_reasoning', 'external_consultation',
                                'startup_health', 'web_skill_status',
                                'devin_repair_status',
                            )
                        }
                    else:
                        packet['portable_context_excerpt'] = {'status': 'UNRESOLVED_no_fresh_context'}
                else:
                    packet['portable_context_excerpt'] = {'status': 'UNRESOLVED_no_cached_context'}
        except Exception:
            pass
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            lifecycles = tracer.recent_dispatch_lifecycles(limit=5)
            failed = [
                {
                    'task': lc['task_name'],
                    'terminal': lc['terminal_state'],
                    'provider': lc['provider'],
                }
                for lc in lifecycles
                if lc.get('terminal_state') and 'blocked' in lc.get('terminal_state', '')
            ]
            packet['recent_failures'] = failed[:3]
        except Exception:
            pass
        return packet

    @staticmethod
    def _sanitize_for_repair(text: str) -> str:
        """Strip potential PII/tokens from repair packet text."""
        import re
        sanitized = re.sub(r'[A-Za-z0-9_\-]{20,}', '<REDACTED>', text)
        sanitized = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '<EMAIL>', sanitized)
        return sanitized[:500]

    def _try_devin_repair(
        self, issue_summary: str, *, user_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Attempt to create a Devin repair task if the API is available.

        Returns result dict with phase/available/session_id.
        Does not use browser credentials — only the Devin REST API.
        Requires user_confirmed=True to actually create the session.
        """
        result: dict[str, Any] = {
            'phase': 'check_availability',
            'available': False,
            'session_id': '',
            'detail': '',
        }
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
        except Exception:
            tracer = None
        try:
            devin_adapter = self.tool_adapters.get('devin_api')
            if devin_adapter is None or not getattr(devin_adapter, 'api_key', ''):
                result['detail'] = 'devin_api adapter not available or no API key'
                result['phase'] = 'unavailable'
                if tracer:
                    tracer.trace_devin_repair(
                        phase='devin_repair_unavailable',
                        available=False,
                        detail=result['detail'],
                    )
                return result
            result['available'] = True
            # Trace the request
            if tracer:
                tracer.trace_devin_repair(
                    phase='devin_repair_requested',
                    available=True,
                    detail=self._sanitize_for_repair(issue_summary),
                )
            if not user_confirmed:
                result['phase'] = 'awaiting_confirmation'
                result['detail'] = 'Devin repair available but requires user confirmation'
                return result
            result['phase'] = 'preparing_packet'
            packet = self._build_repair_packet(issue_summary)
            prompt = (
                f'IABV v1.5 Repair Request:\n'
                f'Issue: {self._sanitize_for_repair(issue_summary)}\n'
                f'Recent failures: {packet.get("recent_failures", [])}\n'
                f'Context: {json.dumps(packet.get("portable_context_excerpt", {}), default=str)[:500]}'
            )
            result['phase'] = 'creating_session'
            try:
                from iabv_v15.bootstrap import _devin_create_session
                session_id = _devin_create_session(devin_adapter, prompt)
                if session_id:
                    result['session_id'] = session_id
                    result['phase'] = 'session_created'
                    result['detail'] = f'Devin session {session_id[:12]} created'
                    if tracer:
                        tracer.trace_devin_repair(
                            phase='devin_repair_created',
                            available=True,
                            session_id=session_id[:12],
                            detail=result['detail'],
                        )
                else:
                    result['phase'] = 'session_creation_failed'
                    result['detail'] = 'Devin API returned empty session_id'
                    if tracer:
                        tracer.trace_devin_repair(
                            phase='devin_repair_failed',
                            available=True,
                            detail=result['detail'],
                        )
            except Exception as exc:
                result['phase'] = 'session_creation_failed'
                result['detail'] = str(exc)[:200]
                if tracer:
                    tracer.trace_devin_repair(
                        phase='devin_repair_failed',
                        available=True,
                        detail=result['detail'],
                    )
        except Exception as exc:
            result['phase'] = 'error'
            result['detail'] = str(exc)[:200]
        return result

    # ── P0.38: Follow-up intent classification for active incidents ──

    _FOLLOWUP_RETRY_PATTERNS: tuple[str, ...] = (
        'intenta nuevamente', 'intenta de nuevo', 'intentalo de nuevo',
        'intentalo otra vez', 'reintenta', 'vuelve a intentar',
        'prueba otra vez', 'prueba de nuevo', 'retry',
        'hazlo otra vez', 'hazlo de nuevo',
    )
    _FOLLOWUP_QUERY_PATTERNS: tuple[str, ...] = (
        'puedes hacer la consulta', 'puedes consultar',
        'si o no', 'sí o no', 'puedes o no',
        'que necesitas', 'qué necesitas',
        'que te falta', 'qué te falta',
        'por que no puedes', 'por qué no puedes',
    )
    _FOLLOWUP_WINDOW_PATTERNS: tuple[str, ...] = (
        'abre la ventana', 'abreme la ventana', 'ábreme la ventana',
        'muestra la ventana', 'muestrame la ventana', 'muéstrame la ventana',
        'enfoca la ventana', 'focus window',
    )

    def _try_handle_consultation_followup(self, message: str) -> bool:
        """P0.38 Task F: Handle follow-up messages for active consultations.

        Messages like 'intenta nuevamente', 'puedes hacer la consulta',
        'abre la ventana' should NOT fall to local chat if there is an
        active external incident or recent failure memory.
        Integrates with ActiveIncidentFrame (P0.37) when available.
        """
        lowered = message.strip().lower()
        # Check both ActiveIncidentFrame (P0.37) and failure memory
        incident = getattr(self, '_active_incident_frame', None)
        failure_memory = getattr(self, '_external_failure_memory', None)
        if not failure_memory and not incident:
            return False
        if incident and not incident.get('resolved') and time.time() < incident.get('expires_at', 0):
            assistant_kind = str(incident.get('assistant_kind', ''))
            assistant_title = str(incident.get('assistant_title', ''))
        elif failure_memory:
            assistant_kind = str(failure_memory.get('assistant_kind', ''))
            assistant_title = str(failure_memory.get('assistant_title', '') or self._assistant_display_name(assistant_kind))
        else:
            return False
        # Retry patterns
        if any(p in lowered for p in self._FOLLOWUP_RETRY_PATTERNS):
            profile = self._scan_assistant_web_skill(assistant_kind or 'chatgpt')
            quiescence = self._evaluate_consultation_quiescence(assistant_kind or 'chatgpt')
            if quiescence['decision'] != 'run_now':
                msg = (
                    f'Quiero reintentar la consulta a {assistant_title}, '
                    f'pero {quiescence["reason"]} '
                    f'Programare un reintento automatico.'
                )
                self._latest_response_text = msg
                self._latest_response_meta = 'consultation_retry_deferred'
                self._append_message('assistant', 'IABV', msg, 'consultation_retry_deferred')
                self._schedule_deferred_consultation_retry(
                    assistant_kind or 'chatgpt',
                    quiescence['retry_after_s'],
                )
                self.dataChanged.emit()
                return True
            self._run_external_consultation(assistant_kind or 'chatgpt', announce=True)
            return True
        # Query patterns — explain state, don't fall to local
        if any(p in lowered for p in self._FOLLOWUP_QUERY_PATTERNS):
            profile = self._scan_assistant_web_skill(assistant_kind or 'chatgpt')
            lines = [f'Estado actual de {assistant_title}:']
            lines.append(f'- Sesion: {profile["active_session_mode"]}')
            lines.append(f'- Autenticacion: {profile["auth_status"]}')
            lines.append(f'- Ventana: {profile["window_status"]}')
            lines.append(f'- CDP: {profile["cdp_status"]}')
            if profile['last_block_reason']:
                lines.append(f'- Ultimo bloqueo: {profile["last_block_reason"]}')
            quiescence = self._evaluate_consultation_quiescence(assistant_kind or 'chatgpt')
            if quiescence['decision'] == 'run_now':
                lines.append('Puedo intentar la consulta ahora. Escribe "intenta nuevamente".')
            else:
                lines.append(f'Debo esperar: {quiescence["reason"]}')
            msg = '\n'.join(lines)
            self._latest_response_text = msg
            self._latest_response_meta = 'consultation_status_report'
            self._append_message('assistant', 'IABV', msg, 'consultation_status_report')
            self.dataChanged.emit()
            return True
        # Window patterns — use ActiveIncidentFrame hwnd when available
        if any(p in lowered for p in self._FOLLOWUP_WINDOW_PATTERNS):
            # Prefer hwnd from ActiveIncidentFrame (P0.37), fall back to web skill profile
            hwnd = None
            if incident and incident.get('hwnd') is not None:
                hwnd = incident['hwnd']
            if hwnd is None:
                profile = self._scan_assistant_web_skill(assistant_kind or 'chatgpt')
                hwnd = profile.get('window_hwnd')
            if hwnd is not None:
                try:
                    import ctypes
                    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
                    user32.ShowWindow(hwnd, 9)
                    user32.SetForegroundWindow(hwnd)
                    msg = f'Enfoque la ventana de {assistant_title}.'
                    self._latest_response_text = msg
                    self._latest_response_meta = 'window_focused'
                    self._append_message('assistant', 'IABV', msg, 'window_focused')
                except Exception:
                    msg = (
                        f'No pude enfocar la ventana de {assistant_title}. '
                        f'Busca la ventana manualmente.'
                    )
                    self._latest_response_text = msg
                    self._latest_response_meta = 'window_focus_failed'
                    self._append_message('assistant', 'IABV', msg, 'window_focus_failed')
            else:
                msg = (
                    f'No encontre una ventana activa de {assistant_title}. '
                    f'Abre {assistant_title} manualmente y luego escribe "intenta nuevamente".'
                )
                self._latest_response_text = msg
                self._latest_response_meta = 'window_not_found'
                self._append_message('assistant', 'IABV', msg, 'window_not_found')
            self.dataChanged.emit()
            return True
        return False

    @staticmethod
    def _derive_external_consultation_outcome(payload: Any) -> str:
        """Derive semantic outcome from external_consultation payload.

        Returns one of: ``resolved``, ``prepared``,
        ``awaiting_external_response``, ``reused_context``, ``blocked``.
        """
        if not isinstance(payload, dict):
            return 'resolved'
        success = bool(payload.get('success'))
        if not success:
            return 'blocked'
        # Check if the consultation actually captured a useful response.
        ext_payload = dict(payload.get('payload') or {})
        ext_meta = dict(ext_payload.get('metadata') or {})
        ext_consultation = dict(
            ext_meta.get('external_consultation')
            or ext_meta.get('autonomous_evolution')
            or {},
        )
        status = str(ext_consultation.get('status') or '').strip().lower()
        has_response = bool(
            ext_consultation.get('response_captured')
            or ext_consultation.get('response_ingested_at_utc')
            or ext_consultation.get('response_validation')
        )
        if has_response:
            return 'resolved'
        if status in ('prepared', 'reused'):
            # Check message for reuse patterns
            message = str(payload.get('message') or '').lower()
            if any(kw in message for kw in ('ya ten', 'equivalente', 'reutiliz', 'reused')):
                return 'reused_context'
            return 'prepared'
        if status == 'awaiting_response':
            return 'awaiting_external_response'
        if status in ('blocked_external', 'failed'):
            return 'blocked'
        # Default: check if the message looks like a dispatch/preparation
        message = str(payload.get('message') or '').lower()
        if any(kw in message for kw in ('aceptada', 'preparando', 'preparada', 'encaminada', 'accepted')):
            return 'prepared'
        if any(kw in message for kw in ('ya ten', 'equivalente', 'reutiliz', 'reused')):
            return 'reused_context'
        return 'resolved'

    def _set_external_consultation_activity(
        self,
        *,
        external_payload: dict[str, Any],
        adaptive_payload: dict[str, Any],
        assistant_title: str,
        message: str,
        external_notice: str,
        outcome: str,
    ) -> None:
        """Project external-consultation state into the visible activity panel.

        ``payload.success`` means the external path was launched/prepared; it
        does not guarantee a verified answer.  The semantic lifecycle outcome
        is the source of truth for the UI state.
        """
        success = bool(external_payload.get('success'))
        if outcome == 'blocked' or not success:
            _has_actionable_guidance = (
                self._assistant_guidance_mode == 'need_approval'
                or bool(self._assistant_action_buttons)
                or bool(adaptive_payload.get('approval_checkpoints'))
            )
            if not _has_actionable_guidance:
                self._reset_assistant_guidance()
            self._set_autonomy_activity_override(
                visible=True,
                title='Consulta externa bloqueada',
                status='blocked',
                stage='bloqueo de entorno, acceso o captura',
                progress=1.0,
                detail=external_notice or message,
                tool=assistant_title,
                next_step='Seguire por aqui con lo que ya tenemos o puedo preparar otra via si hace falta.',
                human_help='Si quieres, puedo intentar otra herramienta o revisar el acceso externo.',
                learning_note='Este bloqueo queda registrado para no fingir que la consulta si se hizo.',
                mode='external',
            )
            return
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

    def _promote_metacognition_after_resolution(self) -> None:
        """Refresh OSES and PortableContext after a resolved interaction."""
        import threading as _thr
        def _refresh() -> None:
            try:
                oses = getattr(self, '_oses_ref', None)
                if oses is not None:
                    oses.build_review()
            except Exception:
                pass
            try:
                pcs = getattr(self, '_portable_context_ref', None)
                if pcs is not None:
                    pcs.build_package()
            except Exception:
                pass
        _thr.Thread(target=_refresh, name='iabv-resolve-promote', daemon=True).start()

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

    def _refresh_development_packet(
        self, user_goal: str | None = None, *, force: bool = False,
    ) -> None:
        import time as _time
        if user_goal is not None:
            self._last_user_goal = user_goal.strip()
        now = _time.monotonic()
        if not force and (now - self._dev_packet_last_ts) < self._dev_packet_cooldown_s:
            return
        self._dev_packet_last_ts = now
        self._development_packet = self.engineering_review_service.build_codex_packet(
            user_goal=self._last_user_goal,
            selected_role_title='Automatico' if self._auto_route_enabled else self._selected_role_title(),
            force=force,
        )

    # ── P0.42: Idle-Budgeted Development Packet Refresh ──
    _IDLE_REFRESH_BUDGET_MS: float = 1500.0
    _IDLE_REFRESH_COOLDOWN_S: float = 5.0
    _IDLE_REFRESH_STALL_COOLDOWN_S: float = 15.0
    _NON_CRITICAL_TASK_NAMES: frozenset[str] = frozenset({
        'provider_health', 'self_teach', 'pbt', 'payload',
        'security_retest', 'adaptive_action',
    })

    def _has_recent_ui_stall(self, threshold_ms: float = 2000.0, window_ms: float = 30_000.0) -> bool:
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            now_elapsed = tracer.current_elapsed_ms()
            recent = tracer.events(kind='ui_event', limit=20)
            return any(
                e.get('data', {}).get('event_type') == 'ui_event_loop_stall'
                and e.get('data', {}).get('duration_ms', 0) > threshold_ms
                and (now_elapsed - e.get('elapsed_ms', 0)) < window_ms
                for e in recent
            )
        except Exception:
            return False

    def _should_defer_dev_packet_refresh(self, task_name: str) -> str:
        if self._working:
            return 'query_pending'
        if self._has_recent_ui_stall():
            return 'recent_ui_stall'
        if self._should_defer_heavy_work():
            return 'resource_pressure'
        if task_name in self._NON_CRITICAL_TASK_NAMES:
            return 'non_critical_task'
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            now_elapsed = tracer.current_elapsed_ms()
            if now_elapsed < 10_000:
                return 'startup_followup_active'
        except Exception:
            pass
        return ''

    def _schedule_idle_dev_packet_refresh(self, task_name: str) -> None:
        defer_reason = self._should_defer_dev_packet_refresh(task_name)
        if defer_reason:
            self._dev_packet_refresh_pending = True
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'development_packet_refresh_deferred',
                    task_name=task_name,
                    reason=defer_reason,
                )
            except Exception:
                pass
            if defer_reason == 'recent_ui_stall':
                delay_ms = int(self._IDLE_REFRESH_STALL_COOLDOWN_S * 1000)
            else:
                delay_ms = int(self._IDLE_REFRESH_COOLDOWN_S * 1000)
            try:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(delay_ms, self._run_idle_dev_packet_refresh)
            except Exception:
                self._bg_pool.submit(self._run_idle_dev_packet_refresh)
            return
        self._bg_pool.submit(self._run_budgeted_dev_packet_refresh)

    def _run_idle_dev_packet_refresh(self) -> None:
        if not getattr(self, '_dev_packet_refresh_pending', False):
            return
        stall_reason = self._should_defer_dev_packet_refresh('')
        if stall_reason in ('recent_ui_stall', 'query_pending'):
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'development_packet_refresh_skipped_due_to_stall',
                    reason=stall_reason,
                )
            except Exception:
                pass
            return
        self._dev_packet_refresh_pending = False
        self._bg_pool.submit(self._run_budgeted_dev_packet_refresh)

    def _run_budgeted_dev_packet_refresh(self) -> None:
        import time as _time
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
        except Exception:
            tracer = None
        if tracer:
            tracer.trace('development_packet_refresh_started')
        start = _time.monotonic()
        try:
            self._refresh_development_packet()
        except Exception:
            pass
        elapsed_ms = (_time.monotonic() - start) * 1000
        if tracer:
            if elapsed_ms > self._IDLE_REFRESH_BUDGET_MS:
                tracer.trace(
                    'development_packet_refresh_budget_exceeded',
                    elapsed_ms=round(elapsed_ms, 1),
                    budget_ms=self._IDLE_REFRESH_BUDGET_MS,
                )
                self._development_packet = (self._development_packet or '') + (
                    '\nmetadata: development_packet_partial=true\n'
                    'unresolved: UNRESOLVED:development_packet_full_refresh_budget_exceeded\n'
                )
            else:
                tracer.trace(
                    'development_packet_refresh_finished',
                    elapsed_ms=round(elapsed_ms, 1),
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
            observation_approvals = [
                item for item in pending_approvals
                if str(item.get('phase_key') or '').strip().lower() == 'observation_permission'
            ]
            self._adaptive_action_buttons = {
                'approve_strategy': bool(pending_approvals),
                'approve_next': bool(status == 'waiting_approval' and pending_approvals),
                'approve_observation': bool(observation_approvals),
                'simulate': bool(self._adaptive_playbook_steps),
                'execute': bool(status in {'ready_to_execute', 'waiting_approval'}),
                'abort': bool(self._adaptive_session_id),
            }
            guidance = payload.get('assistant_guidance')
            if guidance:
                self._apply_assistant_guidance(guidance)
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
        observation_approvals = [
            item for item in pending_approvals
            if str(item.get('phase_key') or '').strip().lower() == 'observation_permission'
        ]
        self._adaptive_action_buttons = {
            'approve_strategy': any(item.get('phase_key') == 'strategy' and item.get('decision') == 'pending' for item in approvals),
            'approve_next': bool(pending_approvals),
            'approve_observation': bool(observation_approvals),
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

    def get_diagnostic_truth_state(self) -> str:
        return self._diagnostic_truth_state

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

    def get_can_approve_observation(self) -> bool:
        return self._adaptive_action_buttons.get('approve_observation', False) and not self._working

    def get_can_simulate(self) -> bool:
        return self._adaptive_action_buttons['simulate'] and not self._working

    def get_can_execute(self) -> bool:
        return self._adaptive_action_buttons['execute'] and not self._working

    def get_can_abort(self) -> bool:
        return self._adaptive_action_buttons['abort'] and not self._working

    def _refresh_all_data(self) -> None:
        """Core refresh logic.  Can run on any thread."""
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
        self._check_stale_build_gate()
        self.dataChanged.emit()

    @Slot()
    def refresh(self) -> None:
        """Synchronous refresh (used by tests and programmatic callers).

        For the startup path, ``_deferred_initial_refresh`` already runs
        equivalent work on ``_bg_pool``.  This method stays synchronous
        for backward compatibility with the test suite.
        """
        self._refresh_all_data()

    @Slot()
    def refreshAsync(self) -> None:
        """Non-blocking refresh — runs heavy work on ``_bg_pool``.

        Exposed as a QML Slot so the UI button doesn't freeze the event
        loop.  The synchronous ``refresh()`` is still available for
        programmatic callers that need immediate results.
        """
        self._bg_pool.submit(self._refresh_all_data)

    def _check_stale_build_gate(self) -> None:
        """Show a one-time warning if the build fingerprint is stale."""
        if getattr(self, '_stale_build_warned', False):
            return
        fp = self.latestRuntimeBuildFingerprint
        if not fp or not fp.get('stale'):
            return
        self._stale_build_warned = True
        missing = ', '.join(fp.get('missing_markers') or [])
        branch = fp.get('branch', '?')
        self._append_message(
            'assistant',
            'IABV',
            f'Estas probando codigo viejo (rama {branch}); '
            'esta prueba viva no valida los fixes recientes. '
            f'Markers faltantes: {missing}.',
            'Stale-Code Gate: build sin features P0.8-P0.11.',
        )

    # ── P0.12 Refresh budget: coalesce timestamps ──
    _DOCK_REFRESH_BUDGET_MS: float = 2000.0
    _DOCK_REFRESH_MIN_INTERVAL_S: float = 1.0
    _DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S: float = 30.0
    _DOCK_REFRESH_BUDGET_COOLDOWN_S: float = 10.0
    _DOCK_SKIP_TRACE_COOLDOWN_S: float = 15.0

    def _should_skip_dock_refresh(self) -> str:
        """Return a non-empty reason string if dock refresh should be skipped."""
        now = time.time()
        last_refresh = getattr(self, '_last_dock_refresh_ts', 0.0)
        if now - last_refresh < self._DOCK_REFRESH_MIN_INTERVAL_S:
            return 'coalesced'
        budget_cooldown_until = getattr(self, '_dock_budget_cooldown_until', 0.0)
        if now < budget_cooldown_until:
            return 'budget_cooldown'
        if self._working:
            return 'query_pending'
        if self._should_defer_heavy_work():
            return 'resource_pressure'
        last_ext = getattr(self, '_last_external_consultation_ts', 0.0)
        if last_ext and (now - last_ext) < self._DOCK_REFRESH_POST_CONSULTATION_COOLDOWN_S:
            return 'post_external_consultation'
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            now_elapsed = tracer.current_elapsed_ms()
            recent_stalls = tracer.events(kind='ui_event', limit=20)
            heavy_stalls = [
                e for e in recent_stalls
                if e.get('data', {}).get('event_type') == 'ui_event_loop_stall'
                and e.get('data', {}).get('duration_ms', 0) > 2000
                and (now_elapsed - e.get('elapsed_ms', 0)) < 30_000
            ]
            if heavy_stalls:
                return 'recent_heavy_stall'
        except Exception:
            pass
        return ''

    def _should_trace_dock_skip(self, reason: str) -> bool:
        """Rate-limit repeated skip telemetry while preserving first evidence."""
        now = time.time()
        last_by_reason = getattr(self, '_dock_skip_last_trace', None)
        if not isinstance(last_by_reason, dict):
            last_by_reason = {}
            self._dock_skip_last_trace = last_by_reason
        last = float(last_by_reason.get(reason, 0.0) or 0.0)
        if now - last < self._DOCK_SKIP_TRACE_COOLDOWN_S:
            return False
        last_by_reason[reason] = now
        return True

    def _refresh_autonomy_dock(self) -> None:
        skip_reason = self._should_skip_dock_refresh()
        if skip_reason:
            if self._should_trace_dock_skip(skip_reason):
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    trace_kind = {
                        'coalesced': 'control_autonomy_dock_refresh_deferred',
                        'query_pending': 'control_autonomy_dock_refresh_skipped_due_to_pressure',
                        'resource_pressure': 'control_autonomy_dock_refresh_skipped_due_to_pressure',
                        'recent_heavy_stall': 'control_autonomy_dock_refresh_deferred',
                        'post_external_consultation': 'control_autonomy_dock_refresh_deferred',
                        'budget_cooldown': 'control_autonomy_dock_refresh_deferred',
                    }.get(skip_reason, 'control_autonomy_dock_refresh_deferred')
                    get_runtime_tracer().trace(trace_kind, reason=skip_reason)
                except Exception:
                    pass
            return
        t0 = time.perf_counter()
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
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._last_dock_refresh_ts = time.time()
        if elapsed_ms > self._DOCK_REFRESH_BUDGET_MS:
            self._dock_budget_cooldown_until = time.time() + self._DOCK_REFRESH_BUDGET_COOLDOWN_S
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'control_autonomy_dock_refresh_budget_exceeded',
                    elapsed_ms=round(elapsed_ms, 1),
                    budget_ms=self._DOCK_REFRESH_BUDGET_MS,
                    cooldown_s=self._DOCK_REFRESH_BUDGET_COOLDOWN_S,
                )
            except Exception:
                pass

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
            self._bg_pool.submit(self._refresh_development_packet)
            self.dataChanged.emit()
            return
        if role in valid_roles:
            self._selected_role = role
            self._auto_route_enabled = False
            self._busy_label = f'Rol forzado a {self._selected_role_title()}.'
            self._bg_pool.submit(self._refresh_development_packet)
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
            try:
                startup_text = self._startup_readiness_text(validating_local_stack=True)
            except Exception:
                startup_text = 'Consultando el stack local y los asistentes externos en segundo plano.'
            self._busy_label = 'Consultando el stack local y los asistentes externos en segundo plano.' if announce else startup_text
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
        metacognition_prompt = intent_key == 'system.metacognition' or bool(intent_metadata.get('metacognition_prompt'))
        world_model_prompt = self._is_world_model_question(user_goal)
        evolution_status_prompt = intent_key == 'consulta_estado_evolutivo' or bool(intent_metadata.get('evolution_status_prompt')) or self._is_evolution_status_question(user_goal)
        learning_prompt = self._is_learning_question(user_goal)
        self_examination_prompt = self._is_self_examination_question(user_goal) or bool(intent_metadata.get('self_examination_prompt'))
        if source == 'chat' and (self_awareness_prompt or metacognition_prompt or world_model_prompt or evolution_status_prompt or learning_prompt or self_examination_prompt):
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
            self._refresh_development_packet(self._last_user_goal or intent.get('title') or 'caso actual', force=True)
            lines.append('Paquete local para Codex:')
            lines.append(self._development_packet.strip())
        else:
            lines.append('Objetivo para la IA externa: explicar por que el flujo no queda aprendido y proponer el siguiente microajuste mas seguro.')
        return '\n'.join(item for item in lines if item).strip()

    def _execute_external_consultation_sync(
        self,
        assistant_kind: str,
        *,
        dispatch_id: str = '',
    ) -> dict[str, Any]:
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
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace_permission(
                    permission_id=f'external_consultation:{requested_assistant_kind}',
                    action='blocked',
                    granted=False,
                    reason=str(preflight.get('reason') or 'ruta bloqueada por gobernanza'),
                    dialog_shown=True,
                )
            except Exception:
                pass
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
        # ── Task B+C: validate visual evidence before treating as success ──
        # The live observation data (target_window, blank_probability, etc.)
        # may live in result.execution_state.metadata rather than
        # result.metadata — combine both to ensure the validator sees all
        # available evidence regardless of where the adapter stored it.
        # execution_state.metadata prevails on conflict (live capture data).
        combined_result_metadata = {
            **result_metadata,
            **dict(result.execution_state.metadata or {}),
        }
        visual_override = self._validate_visual_evidence_result(
            assistant_kind=actual_assistant_kind or requested_assistant_kind,
            assistant_title=assistant_title,
            result_metadata=combined_result_metadata,
            consultation_metadata=consultation_metadata,
        )
        if visual_override is not None:
            # Evidence is invalid: do NOT report as success
            payload = dict(self._last_adaptive_payload or {})
            metadata = dict(payload.get('metadata') or {})
            metadata['external_consultation'] = dict(consultation_metadata)
            metadata['autonomous_evolution'] = dict(consultation_metadata)
            payload['metadata'] = metadata
            self._update_adaptive_state(payload)
            target_window = combined_result_metadata.get('target_window')
            capture_meta = (
                combined_result_metadata.get('visual_evidence_snapshot')
                or combined_result_metadata.get('capture_meta')
                or {}
            )
            capture_state = self._target_window_capture_state(
                target_window, capture_meta,
            )
            # ── P0.6: attempt remediation before giving up ──
            assessment = self._assess_visual_remediation(
                target_window=target_window,
                capture_meta=capture_meta,
                capture_state=capture_state,
            )
            remediation_result = self._attempt_safe_remediation(assessment)
            capture_useful_before = bool(
                (capture_meta or {}).get('useful', False)
            )
            blank_prob_before = float(
                (capture_meta or {}).get('blank_probability') or 0.0
            )
            remediation_unresolved = list(capture_state.get('unresolved') or [])
            remediation_detail = str(remediation_result.get('detail') or '')
            remediation_detail_lower = remediation_detail.lower()
            remediation_detail_code = (
                'win32_api_not_available'
                if 'win32' in remediation_detail_lower and 'not available' in remediation_detail_lower
                else ''
            )
            # ── P0.8: attempt ONE post-remediation recapture ──
            recapture = self._attempt_post_remediation_recapture(
                remediation_result=remediation_result,
                assessment=assessment,
            )
            capture_useful_after = recapture.get('capture_useful_after')
            blank_prob_after = recapture.get('blank_probability_after')
            recapture_status = recapture.get('recapture_status', 'skipped')
            if recapture.get('recapture_unresolved'):
                remediation_unresolved.extend(recapture['recapture_unresolved'])
            if not recapture.get('recapture_attempted'):
                if 'UNRESOLVED:visual_remediation_recapture_not_available' not in remediation_unresolved:
                    remediation_unresolved.append('UNRESOLVED:visual_remediation_recapture_not_available')
            self._trace_visual_remediation_attempted(
                assistant_kind=actual_assistant_kind or requested_assistant_kind,
                target_window_title=assessment.get('target_window_title', ''),
                hwnd=(target_window or {}).get('hwnd'),
                rect=assessment.get('rect'),
                reason=assessment.get('reason', ''),
                proposed_action=assessment.get('proposed_action', ''),
                action_taken=remediation_result.get('action_taken', 'none'),
                result_status=assessment.get('status', 'unresolved'),
                capture_useful_before=capture_useful_before,
                capture_useful_after=capture_useful_after,
                blank_probability_before=blank_prob_before,
                blank_probability_after=blank_prob_after,
                remediation_success=bool(remediation_result.get('success', False)),
                remediation_detail_code=remediation_detail_code,
                recapture_status=recapture_status,
                unresolved=remediation_unresolved,
            )
            metadata['visual_remediation'] = {
                'assessment': assessment,
                'result': remediation_result,
                'recapture': recapture,
            }
            payload['metadata'] = metadata
            self._update_adaptive_state(payload)
            # P0.8: if recapture improved, the visual target is now
            # observable; but it is not, by itself, a verified external answer.
            # P0.9: differentiate window-observable from response-captured.
            visual_recaptured = recapture_status == 'improved' and bool(capture_useful_after)
            if visual_recaptured:
                consultation_metadata['visual_evidence_recovered'] = True
                consultation_metadata['visual_recapture_status'] = recapture_status
                # ── P0.9: verify response was actually captured ──
                response_proof = self._build_post_recapture_response_proof(
                    response_captured=response_captured,
                    response_capture_pending=response_capture_pending,
                    response_capture_mode=response_capture_mode,
                    assistant_title=assistant_title,
                    target_window=target_window,
                    assessment=assessment,
                    capture_useful_before=capture_useful_before,
                    capture_useful_after=capture_useful_after,
                    recapture=recapture,
                    evidence_path=str(
                        combined_result_metadata.get('evidence_path')
                        or combined_result_metadata.get('screenshot_path')
                        or ''
                    ),
                )
                consultation_metadata['response_proof'] = response_proof
                self._trace_post_recapture_response_verification(
                    assistant_kind=actual_assistant_kind or requested_assistant_kind,
                    response_proof=response_proof,
                )
                metadata['external_consultation'] = dict(consultation_metadata)
                metadata['autonomous_evolution'] = dict(consultation_metadata)
                payload['metadata'] = metadata
                self._update_adaptive_state(payload)
                if not response_proof.get('response_captured'):
                    # ── P0.10: attempt ONE response capture retry ──
                    retry_result = self._attempt_post_recapture_response_retry(
                        consultation_metadata=consultation_metadata,
                        payload=payload,
                        assistant_title=assistant_title,
                        assistant_kind=actual_assistant_kind or requested_assistant_kind,
                        dispatch_id=dispatch_id or 'external_consultation_untracked',
                    )
                    if retry_result.get('response_captured'):
                        # Retry succeeded — update proof and allow success
                        response_proof['response_captured'] = True
                        response_proof['status'] = 'response_captured'
                        response_proof['response_capture_retry'] = 'success'
                        consultation_metadata['response_proof'] = response_proof
                        consultation_metadata['response_captured'] = True
                        consultation_metadata['status'] = 'prepared'
                        metadata['external_consultation'] = dict(consultation_metadata)
                        metadata['autonomous_evolution'] = dict(consultation_metadata)
                        payload['metadata'] = metadata
                        self._update_adaptive_state(payload)
                        # Fall through to normal success path below
                    else:
                        # Retry failed or unavailable — UNRESOLVED with guidance
                        response_proof['response_capture_retry'] = retry_result.get('retry_status', 'unavailable')
                        consultation_metadata['response_proof'] = response_proof
                        guidance_msg = self._post_recapture_response_pending_message(
                            assistant_title=assistant_title,
                            response_proof=response_proof,
                        )
                        remediation_unresolved.append(
                            'UNRESOLVED:window_observable_response_not_captured'
                        )
                        if not retry_result.get('retry_attempted'):
                            remediation_unresolved.append(
                                'UNRESOLVED:post_recapture_response_retry_api_missing'
                            )
                        consultation_metadata['status'] = 'window_observable_response_pending'
                        metadata['external_consultation'] = dict(consultation_metadata)
                        payload['metadata'] = metadata
                        self._update_adaptive_state(payload)
                        self._latest_response_text = guidance_msg
                        self._latest_response_meta = f'{assistant_title}: response_pending'
                        self._busy_label = ''
                        return {
                            'success': False,
                            'message': guidance_msg,
                            'meta': f'{assistant_title}: response_pending',
                            'payload': payload,
                            'assistant_title': assistant_title,
                            'external_state_flags': external_state_flags,
                            'visual_unresolved': False,
                            'window_observable': True,
                            'response_captured': False,
                            'response_capture_pending': response_proof.get('response_capture_pending', False),
                            'response_proof': response_proof,
                            'visual_remediation': {
                                'assessment': assessment,
                                'result': remediation_result,
                                'recapture': recapture,
                            },
                        }
            else:
                # P0.4: build shared reality causal handoff
                shared_handoff = self._build_shared_reality_handoff(
                    assistant_kind=actual_assistant_kind or requested_assistant_kind,
                    assistant_title=assistant_title,
                    target_window=target_window,
                    capture_meta=capture_meta,
                    capture_state=capture_state,
                )
                self._attach_evidence_to_handoff(shared_handoff, combined_result_metadata)
                self._trace_shared_reality_handoff(shared_handoff)
                metadata['shared_reality_handoff'] = shared_handoff
                payload['metadata'] = metadata
                self._update_adaptive_state(payload)
                handoff_msg = self._remediation_user_message(
                    assistant_title=assistant_title,
                    assessment=assessment,
                    remediation_result=remediation_result,
                )
                self._latest_response_text = handoff_msg
                self._latest_response_meta = f'{assistant_title}: visual_unresolved'
                self._busy_label = f'Captura visual no valida para {assistant_title}.'
                return {
                    'success': False,
                    'message': handoff_msg,
                    'meta': f'{assistant_title}: visual_unresolved',
                    'payload': payload,
                    'assistant_title': assistant_title,
                    'external_state_flags': external_state_flags,
                    'visual_unresolved': True,
                    'shared_reality_handoff': shared_handoff,
                    'visual_remediation': {
                        'assessment': assessment,
                        'result': remediation_result,
                        'recapture': recapture,
                    },
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
        # ── P0.12 Stale-Code Gate: invalidate live proof if build is stale ──
        _fp = self.latestRuntimeBuildFingerprint
        _build_is_stale = bool(_fp.get('stale')) if _fp else False
        if _build_is_stale:
            consultation_metadata['stale_build'] = True
            consultation_metadata['stale_missing_markers'] = _fp.get('missing_markers', [])
            metadata['external_consultation'] = dict(consultation_metadata)
            payload['metadata'] = metadata
            self._update_adaptive_state(payload)
        if result.success:
            if response_captured:
                message = f"{result.output_text or 'Respuesta externa capturada.'} Ya tengo texto util desde {assistant_title} y lo dejare listo para integrarlo de forma segura.{fallback_note}"
            elif response_capture_mode == 'clipboard_capture':
                message = f"{result.output_text or 'Consulta externa lanzada.'} Ya abri {assistant_title} y voy a intentar capturar su respuesta automaticamente; si no vuelve texto util, te pedire pegarla.{fallback_note}"
            elif response_capture_mode in {'dom_capture', 'browser_dom'}:
                message = f"{result.output_text or 'Consulta externa preparada.'} IABV la llevara en una sesion aislada del programa, usando un chat especial separado de tus chats normales y capturando la respuesta en segundo plano cuando la sesion ya este autenticada.{fallback_note}"
            else:
                message = f"{result.output_text or 'Consulta externa preparada.'} El contexto ya esta copiado y la respuesta vuelve por pegado manual.{fallback_note}"
            if _build_is_stale:
                message += ' [Stale-Code Gate: esta prueba viva no valida fixes recientes — actualiza main y vuelve a probar.]'
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
                'stale_build': _build_is_stale,
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

    @staticmethod
    def _is_resource_pressure_block(preflight: dict[str, Any]) -> bool:
        """Check if a preflight block is caused by resource pressure."""
        governance = dict(preflight.get('governance') or {})
        reason = str(preflight.get('reason') or governance.get('reason') or '').lower()
        diag = str(governance.get('diagnostic_category') or '').lower()
        resource_pressure_signals = (
            'presion de recursos',
            'presión de recursos',
            'resource pressure',
            'resource_pressure',
            'degradar con gracia',
        )
        if diag in ('environment_guard', 'resource_pressure'):
            return True
        return any(sig in reason for sig in resource_pressure_signals)

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

        # P0.22: detect resource_pressure to set correct preflight metadata.
        is_resource_pressure = self._is_resource_pressure_block(preflight)

        metadata['external_consultation_preflight'] = {
            'assistant_kind': assistant_kind,
            'reason': str(preflight.get('reason') or governance.get('reason') or ''),
            'blocked': True,
            'world_model_summary': world_model_summary,
            'block_type': 'resource_pressure' if is_resource_pressure else 'governance',
            'requires_observation_permission': False if is_resource_pressure else bool(approval_checkpoints),
            'retry_when_pressure_clears': is_resource_pressure,
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

        # P0.22: resource pressure gets explicit deferred message.
        if is_resource_pressure:
            message = (
                f'No hice la consulta a {assistant_title}. '
                'La bloquee antes de abrir la herramienta porque el entorno esta bajo presion de recursos. '
                'No es problema de login ni captura. '
                'Puedo reintentar cuando baje la presion o usar ruta local.'
            )
            meta = f'Consulta diferida por presion de recursos ({assistant_title}).'
            terminal_state = 'blocked_by_resource_pressure'
        elif approval_checkpoints:
            message = (
                f'No voy a lanzar {assistant_title} todavia. '
                f'{reason or f"Primero necesito tu permiso para observar esa ventana y verificar que {assistant_title} este usable."}'
            )
            meta = f'Permiso requerido para {assistant_title}.'
            terminal_state = 'failed_with_actionable_reason'
        else:
            message = (
                f'No voy a lanzar {assistant_title} porque la ruta ya aparece bloqueada antes de intentarla. '
                f'{reason or "Mantengo la via local hasta que el bloqueo cambie."}'
            )
            meta = f'Ruta bloqueada para {assistant_title}.'
            terminal_state = 'failed_with_actionable_reason'
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
            'terminal_state': terminal_state,
            'block_type': 'resource_pressure' if is_resource_pressure else 'governance',
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
        diag = str(governance.get('diagnostic_category') or '').strip().lower()
        if diag == 'assistant_unavailable':
            return {
                'mode': 'need_approval',
                'title': f'{assistant_title} no disponible',
                'prompt': prompt,
                'actions': [
                    self._assistant_action(f'consult_{assistant_kind}', f'Reintentar {assistant_title}', 'Volver a verificar disponibilidad y reintentar.'),
                    self._assistant_action('review_stack', 'Abrir / verificar herramienta', 'Revisar si la herramienta esta abierta y disponible.'),
                    self._assistant_action('audit_autonomy', 'Auditar autonomia', 'Ver detalle del bloqueo operativo.'),
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
        """Return assistant_kind only when a real observation_permission checkpoint exists.

        P0.22 fix: previously this returned assistant_kind from any
        external_consultation_preflight, even when the block was
        resource_pressure/environment_guard — NOT observation permission.
        Now it only returns a value when:
        1. An approval_checkpoint with phase_key=='observation_permission' exists, OR
        2. The preflight metadata explicitly says requires_observation_permission==True.
        If the preflight was blocked by resource_pressure, returns '' so that
        _try_resolve_pending_observation_permission() won't misinterpret user
        messages as permission grants.
        """
        payload = dict(self._last_adaptive_payload or {})
        metadata = dict(payload.get('metadata') or {})
        preflight = dict(metadata.get('external_consultation_preflight') or {})

        # Check approval_checkpoints for a real observation_permission gate.
        for item in payload.get('approval_checkpoints') or []:
            checkpoint = dict(item or {})
            phase_key = str(checkpoint.get('phase_key') or '').strip().lower()
            if phase_key != 'observation_permission':
                continue
            checkpoint_meta = dict(checkpoint.get('metadata') or {})
            gates = [dict(gate) for gate in (checkpoint_meta.get('permission_gates') or []) if isinstance(gate, dict)]
            gate = gates[0] if gates else {}
            assistant_kind = str(
                gate.get('assistant_kind')
                or checkpoint_meta.get('assistant_kind')
                or preflight.get('assistant_kind')
                or '',
            ).strip().lower()
            if assistant_kind:
                return assistant_kind

        # Explicit metadata flag from preflight.
        if preflight.get('requires_observation_permission') is True:
            assistant_kind = str(preflight.get('assistant_kind') or '').strip().lower()
            if assistant_kind:
                return assistant_kind

        # P0.22: do NOT fall through to preflight.assistant_kind when the
        # block reason is resource_pressure or environment_guard.
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
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace_permission(
                permission_id=f'observe_window_content:{assistant_kind}',
                action='granted',
                granted=True,
                reason=f'Usuario concedio permiso para observar {assistant_title}',
                dialog_shown=True,
            )
        except Exception:
            pass
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

    def _run_external_consultation(self, assistant_kind: str, *, announce: bool = True) -> bool:
        assistant_title = self._assistant_display_name(assistant_kind)

        # P0.39: Universal readiness check before attempting consultation
        readiness = self._assess_external_readiness(assistant_kind)
        if not readiness['action_possible']:
            msg = (
                f'No puedo iniciar la consulta a {assistant_title} ahora.\n'
                f'Razon: {readiness["blocking_reason"]}\n'
            )
            if readiness['next_human_action']:
                msg += f'Accion requerida: {readiness["next_human_action"]}\n'
            msg += (
                f'Sesion: {readiness["session_selected"]} | '
                f'Build: {readiness["build_state"]} | '
                f'Presion: {readiness["resource_pressure"]} | '
                f'Confianza: {readiness["confidence"]}'
            )
            self._latest_response_text = msg
            self._latest_response_meta = f'readiness_blocked:{readiness["blocking_reason"]}'
            self._working = False
            if announce:
                self._append_message(
                    'assistant', 'IABV', msg,
                    f'readiness_blocked:{readiness["blocking_reason"]}',
                    reasoning_path='capability_readiness',
                    evidence_tag='observed',
                )
            self._set_live_status('idle')
            try:
                self.dataChanged.emit()
            except Exception:
                pass
            if readiness['blocking_reason'].startswith('resource_pressure'):
                self._schedule_deferred_consultation_retry(
                    assistant_kind,
                    readiness.get('retry_after_s', 15),
                )
            return False

        self._working = True
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

        _ext_done = threading.Event()
        _dispatch_id = self._new_dispatch_id('external_consultation')
        self._trace_dispatch_started(
            task_name='external_consultation',
            dispatch_id=_dispatch_id,
            provider=assistant_kind,
            source='_run_external_consultation',
            user_goal_excerpt=self._last_user_goal or '',
            visible_busy_label=self._busy_label,
        )

        def worker() -> None:
            try:
                result_payload = self._execute_external_consultation_sync(
                    assistant_kind,
                    dispatch_id=_dispatch_id,
                )
                if not self._is_dispatch_active('external_consultation', _dispatch_id):
                    import logging
                    logging.getLogger(__name__).debug('external_consultation worker %s discarded (stale)', _dispatch_id[:8])
                    self._trace_dispatch_terminal(
                        task_name='external_consultation', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', provider=assistant_kind,
                        reason='stale_discarded: worker finished after dispatch invalidated',
                        user_visible_message=False,
                    )
                    return
                self.taskResolved.emit('external_consultation', result_payload)
            except Exception as exc:
                if not self._is_dispatch_active('external_consultation', _dispatch_id):
                    import logging
                    logging.getLogger(__name__).debug('external_consultation worker %s error discarded (stale)', _dispatch_id[:8])
                    self._trace_dispatch_terminal(
                        task_name='external_consultation', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', provider=assistant_kind,
                        reason=f'stale_discarded: error discarded: {exc}',
                        user_visible_message=False,
                    )
                    return
                # P0.23 Task D: detect browser_security_verification errors and
                # convert them into a structured handoff result instead of a
                # generic NoneType exception.
                exc_str = str(exc).lower()
                if 'browser_security_verification' in exc_str or (
                    "'nonetype'" in exc_str and "'get'" in exc_str
                ):
                    security_result = {
                        'success': False,
                        'message': (
                            'No pude consultar ChatGPT todavia. Si intente abrir la sesion, '
                            'pero ChatGPT mostro verificacion de seguridad o una pagina no usable. '
                            'Necesito que completes esa verificacion o selecciones el navegador/perfil correcto. '
                            'No voy a fingir que recibi respuesta.'
                        ),
                        'meta': f'ChatGPT: blocked_by_security_verification (dispatch {_dispatch_id[:12]})',
                        'terminal_state': 'blocked_by_security_verification',
                        'assistant_title': self._assistant_display_name(assistant_kind),
                        'assistant_kind': assistant_kind,
                        'external_state_flags': [],
                        'payload': {
                            'metadata': {
                                'external_consultation': {
                                    'status': 'blocked_by_security_verification',
                                    'assistant_kind': assistant_kind,
                                    'requires_human_verification': True,
                                    'next_action': (
                                        'abre la sesion controlada o tu navegador y completa '
                                        'la verificacion; luego escribe "ya lo hice"'
                                    ),
                                },
                            },
                        },
                        'evidence_refs': [
                            f'browser_dom_capture failed (browser_security_verification)',
                            f'dispatch_id={_dispatch_id[:12]}',
                            f'original_error={str(exc)[:120]}',
                        ],
                    }
                    self.taskResolved.emit('external_consultation', security_result)
                else:
                    self.taskFailed.emit('external_consultation', f'No pude completar la consulta externa guiada: {exc}')
            finally:
                _ext_done.set()

        threading.Thread(target=worker, daemon=True).start()
        self._schedule_worker_timeout(
            done_event=_ext_done,
            task_name='external_consultation',
            timeout_s=self._EXTERNAL_WORKER_TIMEOUT_S,
            dispatch_id=_dispatch_id,
        )
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
        return False

    # P0.23: action verbs that signal external consultation intent.
    # When these appear alongside a known assistant target, the message
    # must NOT be captured as operational_status — it is an action request.
    _EXTERNAL_ACTION_VERBS_FOR_EXCLUSION: tuple[str, ...] = (
        'haz', 'hacer', 'hazle', 'hazla',
        'consulta', 'consultar',
        'pregunta', 'preguntale', 'pregúntale',
        'pidele', 'pídele',
        'envia', 'envía', 'manda',
        'prueba con',
    )

    _EXTERNAL_TARGETS_FOR_EXCLUSION: tuple[str, ...] = (
        'chatgpt', 'chat gpt', 'chat-gpt', 'chatgo',
        'codex', 'claude', 'ollama', 'devin', 'windsurf',
    )

    def _is_operational_status_question(self, message: str) -> bool:
        """Detect messages that are operational status questions, not permission grants.

        P0.22: messages like "si puedes hacer la consulta si o no?" are
        asking whether IABV *can* perform the consultation — they are NOT
        granting observation permission.  This guard prevents
        _try_resolve_pending_observation_permission() from misinterpreting
        status inquiries as affirmative permission responses.

        P0.23: messages containing an action verb + external assistant target
        (e.g. "pero a chatgpt hazla para saber si te entiende") must NOT be
        captured here — they are explicit external consultation requests.
        """
        lower = message.lower().strip()

        # P0.23: if the message has an action verb + assistant target, it is
        # an external consultation request, NOT an operational status question.
        has_action = any(v in lower for v in self._EXTERNAL_ACTION_VERBS_FOR_EXCLUSION)
        has_target = any(t in lower for t in self._EXTERNAL_TARGETS_FOR_EXCLUSION)
        if has_action and has_target:
            return False

        question_markers = ('?', '¿')
        has_question = any(m in lower for m in question_markers)

        status_patterns = (
            'puedes hacer',
            'puedes realizar',
            'puedes consultar',
            'si o no',
            'sí o no',
            'por que no',
            'por qué no',
            'que paso',
            'qué pasó',
            'que sucedio',
            'qué sucedió',
            'que fallo',
            'qué falló',
            'funciona o no',
            'va a funcionar',
            'se puede o no',
            'que esta pasando',
            'qué está pasando',
            'esta funcionando',
            'está funcionando',
            'sigue bloqueado',
            'sigue fallando',
            'lo vas a hacer',
            'lo puedes hacer',
            'lo hiciste',
            'lo lograste',
            'ya lo hiciste',
        )
        if has_question and any(p in lower for p in status_patterns):
            return True
        if any(p in lower for p in ('si o no', 'sí o no')):
            return True
        return False

    def _try_resolve_pending_observation_permission(self, message: str) -> bool:
        """Auto-grant observation permission only for explicit permission replies.

        P0.22 hardened version:
        - Rejects operational status questions ("si puedes hacer la consulta?")
        - Only grants when a real observation_permission checkpoint exists
          AND the user sends an explicit permission phrase.
        - A bare "sí" only works when the last visible guidance was an
          observation permission dialog, not a resource-pressure block.
        """
        assistant_kind = self._pending_observation_permission_assistant()
        if not assistant_kind:
            return False

        if self._is_operational_status_question(message):
            return False

        lower = message.lower().strip()

        # Explicit permission phrases — unambiguous observation permission grants.
        explicit_permission_phrases = (
            'permito observar',
            'autoriza la captura',
            'autorizo la captura',
            'acepto el permiso',
            'puedes observar',
            'permitir observacion',
            'permitir observación',
            'concedo permiso',
            'concedo el permiso',
            'apruebo la observacion',
            'apruebo la observación',
            'grant observation',
            'approve observation',
            'allow observation',
            'acepto observacion',
            'acepto observación',
        )
        if any(phrase in lower for phrase in explicit_permission_phrases):
            self._grant_pending_observation_permission(announce=True)
            self._set_live_status('idle')
            self.dataChanged.emit()
            return True

        # Short affirmatives only if guidance was explicitly a permission dialog.
        short_affirmatives = {
            'si', 'sí', 'ok', 'dale', 'permite', 'permiso', 'aprueba',
            'aprobar', 'adelante', 'hazlo', 'acepto', 'aceptar',
            'grant', 'approve', 'yes', 'go', 'proceed',
        }
        tokens = set(lower.replace(',', ' ').replace('.', ' ').split())
        if tokens.intersection(short_affirmatives):
            last_guidance = str(getattr(self, '_last_guidance_action', '') or '').lower()
            if last_guidance == 'approve_observation_permission':
                self._grant_pending_observation_permission(announce=True)
                self._set_live_status('idle')
                self.dataChanged.emit()
                return True

        return False

    def _normalized_command_text(self, message: str) -> str:
        return ' '.join(message.lower().strip().split())

    def _try_handle_chat_command(self, message: str) -> bool:
        command = self._normalized_command_text(message)
        if not command:
            return False

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
            'secretos faltantes',
            'secretos que me pide',
            'tokens faltantes',
            'por que no los encuentra',
            'por qué no los encuentra',
            'analiza por que no',
            'analiza por qué no',
        )
        if any(phrase in command for phrase in direct_phrases):
            return True
        word_tokens = set(re.findall(r'[a-z0-9_]+', command))
        asks_self = any(t in word_tokens for t in ('analizate', 'analízate', 'autoanalisis', 'diagnosticate'))
        asks_code = any(t in word_tokens for t in ('codigo', 'código', 'errores', 'fallas', 'bugs', 'sintaxis'))
        asks_perf = any(t in word_tokens for t in ('lento', 'congela', 'congelas', 'rendimiento', 'lentitud'))
        asks_config = any(t in word_tokens for t in ('secretos', 'secreto', 'tokens', 'token', 'faltantes', 'faltante', 'bootstrap', 'configurados'))
        asks_analyze = any(t in command for t in ('analiza', 'revisa', 'examina', 'diagnostica', 'busca'))
        if asks_analyze and (asks_code or asks_perf or asks_config):
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
            reasoning_path='self_code_analysis', evidence_tag='observed',
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
                    reasoning_path='self_code_analysis', evidence_tag='observed',
                )
                self._record_chat_audit(
                    reasoning_path='self_code_analysis',
                    user_goal=self._last_user_goal or 'auto-analisis',
                )

            except Exception as exc:
                self._append_message(
                    'assistant', 'IABV',
                    f'Error durante el auto-analisis: {exc}',
                    'Metacognicion: error en auto-analisis.',
                    reasoning_path='self_code_analysis_failure',
                )
                self._record_chat_audit(
                    reasoning_path='self_code_analysis_failure',
                    user_goal=self._last_user_goal or 'auto-analisis',
                    error_detail=str(exc)[:200],
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

        NOTE: NO debounce here — each message carries unique text that must be
        processed individually. Skipping messages would permanently lose
        capability detections (e.g. "tengo GPU RTX 4090").
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

    # P0.23 Task F: threshold (seconds) above which a task result is
    # considered "heavy" and the subsequent _set_live_status('idle')
    # should defer its dataChanged.emit to avoid a UI stall.
    _HEAVY_RESULT_THRESHOLD_S: float = 10.0

    def _set_live_status(self, status: str) -> None:
        with self._ui_state_lock:
            previous = self._live_status
            if previous == status:
                return
            self._live_status = status
        self.liveStatusChanged.emit(status)
        # P0.23 Task F: if we are transitioning to idle right after a heavy
        # task result, defer the dataChanged.emit so the main thread is not
        # blocked for tens of seconds.
        if status == 'idle' and getattr(self, '_heavy_result_guard_active', False):
            self._heavy_result_guard_active = False
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'ui_status_emit_deferred',
                    detail='dataChanged.emit deferred after heavy task result',
                )
            except Exception:
                pass
            import threading as _thr
            def _deferred_emit() -> None:
                import time as _time
                _time.sleep(0.05)
                try:
                    self.dataChanged.emit()
                except Exception:
                    pass
            _thr.Thread(target=_deferred_emit, name='iabv-deferred-emit', daemon=True).start()
        else:
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

    @Property('QVariant', notify=dataChanged)
    def latestDispatchLifecycle(self) -> dict[str, Any]:
        """Read-only summary of the most recent dispatch lifecycle.

        ``recent_dispatch_lifecycles`` returns dispatched entries
        (correlated and unresolved) sorted by ``started_at`` desc,
        followed by orphan terminals.  The first entry with a non-empty
        ``dispatch_id`` is the newest real lifecycle.  Falls back to
        orphan only if no dispatched entry exists.
        """
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            cycles = get_runtime_tracer().recent_dispatch_lifecycles(limit=20)
            if not cycles:
                return {}
            best = cycles[0]
            for c in cycles:
                if c.get('dispatch_id'):
                    best = c
                    break
            return {
                'task_name': best.get('task_name', ''),
                'terminal_state': best.get('terminal_state', ''),
                'duration_ms': best.get('duration_ms', 0.0),
                'unresolved': best.get('unresolved', False),
                'provider': best.get('provider', ''),
                'dispatch_id': best.get('dispatch_id', ''),
                'orphan_terminal': best.get('orphan_terminal', False),
            }
        except Exception:
            return {}

    @Property('QVariant', notify=dataChanged)
    def latestRuntimeBuildFingerprint(self) -> dict[str, Any]:
        """Read-only build fingerprint from the last runtime_build_fingerprint event."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            fps = get_runtime_tracer().events(kind='runtime_build_fingerprint', limit=1)
            if not fps:
                return {}
            data = dict(fps[-1].get('data', {}))
            return {
                'branch': data.get('branch', ''),
                'head': data.get('head', ''),
                'dirty': data.get('dirty', False),
                'origin_main_head': data.get('origin_main_head', ''),
                'stale': data.get('stale', False),
                'missing_markers': data.get('missing_markers', []),
                'feature_markers': data.get('feature_markers', {}),
            }
        except Exception:
            return {}

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

    def send_message_from_bridge(self, text: str) -> dict[str, Any]:
        """Acepta texto del bridge TCP y lo encola hacia el hilo de UI.

        El UIBridgeServer corre en un hilo de background; emitir una signal
        permite despachar el envio real al chat sin tocar QML desde ese hilo.

        Marca dos hitos en el ``startup_timeline`` para diagnosticar la
        latencia de la queued connection:
        - ``bridge_chat_queued`` en el hilo del bridge (al emitir la senal).
        - ``bridge_chat_dispatched`` en ``_dispatch_bridge_chat`` cuando
          el hilo GUI atiende la senal.  La diferencia de
          ``t_ms_from_start`` entre ambos es la latencia real de la
          queued connection — si es enorme, el GUI thread esta bloqueado.
        """
        message = (text or '').strip()
        if not message:
            return {'status': 'error', 'detail': 'text is required'}
        try:
            from iabv_v15.infra.startup_timeline import get_global_timeline
            get_global_timeline().mark(
                'bridge_chat_queued',
                text_len=len(message),
                chat_session_id=self._chat_session_id,
            )
        except Exception:
            pass
        self.bridgeChatRequested.emit(message)
        return {
            'status': 'queued',
            'text': message,
            'chat_session_id': self._chat_session_id,
        }

    @Slot(str)
    def _dispatch_bridge_chat(self, text: str) -> None:
        try:
            from iabv_v15.infra.startup_timeline import get_global_timeline
            get_global_timeline().mark(
                'bridge_chat_dispatched',
                text_len=len(text or ''),
                chat_session_id=self._chat_session_id,
            )
        except Exception:
            pass
        self.sendChat(text)

    def _try_handle_lightweight_chat(self, message: str) -> bool:
        if self._is_world_model_question(message):
            self._answer_world_model_question(message)
            return True
        if self._is_self_awareness_question(message):
            self._answer_self_awareness_question(message)
            return True
        if self._is_evolution_status_question(message):
            self._answer_evolution_status_question(message)
            return True
        if self._is_self_examination_question(message):
            self._answer_self_examination_question(message)
            return True
        if self._is_learning_question(message):
            self._answer_learning_question(message)
            return True
        if self._is_general_chat_message(message) and not self._seems_task_like_message(message):
            self._answer_general_chat(message)
            return True
        return False

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
        # --- Open canonical interaction episode ---
        self._interaction_has_pending_followup = False
        lifecycle = getattr(self, '_chat_interaction_lifecycle', None)
        interaction_id: str | None = None
        if lifecycle is not None:
            try:
                watchdog = getattr(self, '_ui_heartbeat_watchdog', None)
                # Capture current window state at episode start
                initial_window_active = True
                initial_window_visible = True
                if watchdog is not None:
                    initial_window_active = getattr(watchdog, '_window_active', True)
                    initial_window_visible = getattr(watchdog, '_window_visible', True)
                interaction_id = lifecycle.open_interaction(
                    message,
                    initial_window_active=initial_window_active,
                    initial_window_visible=initial_window_visible,
                )
                self._active_interaction_id = interaction_id
                if watchdog is not None:
                    watchdog.set_query_pending(True)
                    watchdog.set_active_interaction(interaction_id)
            except Exception:
                pass
        # Safety: si _working quedo stuck de una llamada anterior (>60s),
        # resetearlo para no bloquear al usuario permanentemente.
        # APRENDIDO: _working puede quedar en True si worker() lanza excepcion
        # no capturada o si el signal taskFailed no se emite correctamente.
        if self._working:
            import time
            elapsed = time.time() - getattr(self, '_working_since', 0)
            if elapsed < 60:
                self._resolve_active_interaction(outcome='abandoned')
                return
            # Reset forzado: _working stuck por mas de 60 segundos
            self._working = False
            self._set_live_status('idle')
            self._clear_autonomy_activity_override()
        user_attachments = list(self._attached_files) if self._attached_files else None
        self._append_message('user', 'Tu', message, self._routing_mode_label(),
                            attachments=user_attachments)
        if self._attached_files:
            self._attached_files.clear()
        self._set_live_status('processing')
        if self._try_handle_chat_command(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_resolve_pending_observation_permission(message):
            # P0.22: if permission grant fired _run_external_consultation(),
            # the external worker is now alive — keep the interaction open
            # so dispatch_terminal inherits the interaction_id.
            if self._working:
                self._resolve_active_interaction(outcome='awaiting_external_response', provider='local')
            else:
                self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_handle_shared_reality_followup(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # P0.37: Active Incident Frame resolver — catches help-offer,
        # show-problem, visibility-dispute, and profile-mismatch intents
        # that the older pattern-based handlers would miss.
        if self._try_handle_incident_followup(message):
            if self._working:
                self._resolve_active_interaction(outcome='awaiting_external_response', provider='local')
            else:
                self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_handle_security_verification_retest(message):
            # P0.22: security retest spawns a background worker — keep
            # interaction open until the worker reaches terminal state.
            if self._working:
                self._resolve_active_interaction(outcome='awaiting_external_response', provider='local')
            else:
                self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # P0.32: governed user Chrome bridge — session selection
        if self._try_handle_user_chrome_bridge_selection(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_handle_cdp_permission_revoke(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # P0.38 Task F: consultation follow-ups must not fall to local chat.
        if self._try_handle_consultation_followup(message):
            if self._working:
                self._resolve_active_interaction(outcome='awaiting_external_response', provider='local')
            else:
                self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_handle_external_failure_followup(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # P0.40 Task A: External Intent Sovereignty — any message with
        # explicit external assistant intent MUST pass through readiness
        # gate before anything else can claim it.  This prevents
        # _try_handle_lightweight_chat / _is_general_chat_message from
        # resolving "haz una consulta a ChatGPT: ..." locally.
        _p040_explicit = self._explicit_assistant_preference(message)
        if _p040_explicit:
            try:
                from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                get_runtime_tracer().trace(
                    'external_intent_detected',
                    assistant_kind=_p040_explicit,
                    message_excerpt=message[:120],
                    source='sendChat_sovereignty_guard',
                )
            except Exception:
                pass
            self._last_user_goal = message
            self._interaction_has_pending_followup = True
            self._run_external_consultation(_p040_explicit, announce=True)
            return
        # P0.30 Task B: structured self-audit guard — answer from artifacts,
        # not from Adaptive local orchestrator / Ollama.
        if self._try_handle_structured_self_audit(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if self._try_handle_lightweight_chat(message):
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # Escucha pasiva de capacidades declaradas (GPU, modelos, cuentas, runtimes).
        # Persiste detecciones a data/chat_research_backlog/*.jsonl para que OSES
        # y ExperimentLab las consuman despues como areas de investigacion. No
        # modifica el ruteo; solo anota y avisa al usuario en una linea corta
        # para que sepa que su dato quedo registrado (antes se perdian en memoria).
        # Ingerir capabilities y actualizar packet en background (thread pool
        # compartido — evita crear 2+ threads por mensaje).
        self._bg_pool.submit(self._ingest_chat_capabilities, message)
        self._bg_pool.submit(self._refresh_development_packet, message)
        # _chat_shortcut_analysis puede llamar a LLM — ejecutar con timeout
        # APRENDIDO: NO usar 'with ThreadPoolExecutor' en hilo de UI porque
        # pool.shutdown(wait=True) bloquea al salir del with aunque el timeout
        # se haya cumplido. Usar Thread + Event en su lugar.
        import time as _time_mod
        shortcut_analysis = {}
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
        _sa_t0 = _time_mod.perf_counter()
        _sa_completed = _sa_done.wait(timeout=3)
        _sa_elapsed_ms = (_time_mod.perf_counter() - _sa_t0) * 1000.0
        if _sa_completed:
            shortcut_analysis = _sa_result
        self._trace_chat_stall(
            elapsed_ms=_sa_elapsed_ms,
            timed_out=not _sa_completed,
            message_summary=message[:120],
        )
        allow_chat_shortcuts = not bool(shortcut_analysis.get('mixed_actionable')) and not bool(shortcut_analysis.get('requires_clarification'))
        if allow_chat_shortcuts and self._is_world_model_question(message):
            self._answer_world_model_question(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if allow_chat_shortcuts and self._is_self_awareness_question(message):
            self._answer_self_awareness_question(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if allow_chat_shortcuts and self._is_evolution_status_question(message):
            self._answer_evolution_status_question(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if allow_chat_shortcuts and self._is_self_examination_question(message):
            self._answer_self_examination_question(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if allow_chat_shortcuts and self._is_learning_question(message):
            self._answer_learning_question(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        if allow_chat_shortcuts and self._is_general_chat_message(message) and not self._seems_task_like_message(message):
            self._answer_general_chat(message)
            self._resolve_active_interaction(outcome='resolved', provider='local')
            return
        # NOTE: explicit_assistant check was here pre-P0.40 but is now
        # handled earlier in the sovereignty guard (line ~11576).
        # If we reach this point the message has no external intent.
        import time as _time
        self._working = True
        self._working_since = _time.time()
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

        _worker_done = threading.Event()
        _dispatch_id = self._new_dispatch_id('chat')
        self._trace_dispatch_started(
            task_name='chat',
            dispatch_id=_dispatch_id,
            source='sendChat',
            user_goal_excerpt=message,
            visible_busy_label=self._busy_label,
        )

        def worker() -> None:
            try:
                # Mark lifecycle phase: first_technical_response
                if interaction_id and lifecycle is not None:
                    try:
                        lifecycle.mark_phase(interaction_id, 'first_technical_response')
                    except Exception:
                        pass
                request = self._build_request(message)
                record = self.inference_service.infer_task(request)
                adaptive_session = record.result.raw_output.get('adaptive_session') if isinstance(record.result.raw_output, dict) else None
                if not self._is_dispatch_active('chat', _dispatch_id):
                    import logging
                    logging.getLogger(__name__).debug('chat worker %s discarded (stale)', _dispatch_id[:8])
                    self._trace_dispatch_terminal(
                        task_name='chat', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', reason='stale_discarded: worker finished after dispatch invalidated',
                        user_visible_message=False,
                    )
                    return
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
                if not self._is_dispatch_active('chat', _dispatch_id):
                    import logging
                    logging.getLogger(__name__).debug('chat worker %s error discarded (stale)', _dispatch_id[:8])
                    self._trace_dispatch_terminal(
                        task_name='chat', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', reason=f'stale_discarded: error discarded: {exc}',
                        user_visible_message=False,
                    )
                    return
                self.taskFailed.emit('chat', f'No pude completar la consulta local: {exc}')
            finally:
                _worker_done.set()

        threading.Thread(target=worker, daemon=True).start()
        self._schedule_worker_timeout(
            done_event=_worker_done,
            task_name='chat',
            timeout_s=self._CHAT_WORKER_TIMEOUT_S,
            dispatch_id=_dispatch_id,
        )

    def _role_title_from_task(self, role: TaskRole) -> str:
        return next((profile.title for profile in self.role_router.role_profiles if profile.role == role), role.value)

    def _run_adaptive_action(self, *, action_name: str, busy_text: str) -> None:
        if self._working or not self._adaptive_session_id:
            return
        self._approval_dialog_visible = False
        self._working = True
        self._busy_label = busy_text
        self.dataChanged.emit()

        _aa_done = threading.Event()
        _dispatch_id = self._new_dispatch_id('adaptive_action')
        self._trace_dispatch_started(
            task_name='adaptive_action',
            dispatch_id=_dispatch_id,
            source=f'_run_adaptive_action:{action_name}',
            visible_busy_label=busy_text,
        )

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
                if not self._is_dispatch_active('adaptive_action', _dispatch_id):
                    self._trace_dispatch_terminal(
                        task_name='adaptive_action', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', reason='stale_discarded: adaptive worker finished after dispatch invalidated',
                        user_visible_message=False,
                    )
                    return
                self.taskResolved.emit('adaptive_action', session.model_dump(mode='json'))
            except Exception as exc:
                if not self._is_dispatch_active('adaptive_action', _dispatch_id):
                    self._trace_dispatch_terminal(
                        task_name='adaptive_action', dispatch_id=_dispatch_id,
                        terminal_state='cancelled', reason=f'stale_discarded: adaptive error discarded: {exc}',
                        user_visible_message=False,
                    )
                    return
                self.taskFailed.emit('adaptive_action', f'No pude completar la accion adaptativa: {exc}')
            finally:
                _aa_done.set()

        threading.Thread(target=worker, daemon=True).start()
        self._schedule_worker_timeout(
            done_event=_aa_done,
            task_name='adaptive_action',
            timeout_s=self._CHAT_WORKER_TIMEOUT_S,
            dispatch_id=_dispatch_id,
        )

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
        self._refresh_development_packet(text, force=True)
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
            self._diagnostic_truth_state = 'observed'
        elif task_name == 'chat':
            self._clear_autonomy_activity_override()
            # Mark lifecycle phase: first_useful_response
            _iid = getattr(self, '_active_interaction_id', None)
            _lc = getattr(self, '_chat_interaction_lifecycle', None)
            if _iid and _lc is not None:
                try:
                    _lc.mark_phase(_iid, 'first_useful_response')
                except Exception:
                    pass
            sources = ', '.join(payload.get('sources') or []) or 'sin fuentes explicitas'
            tools = ', '.join(payload.get('used_tools') or []) or 'sin herramientas'
            follow_up = payload.get('follow_up_teachings') or []
            extra = f" | siguientes ensenanzas: {', '.join(follow_up)}" if follow_up else ''
            planner_text = 'si' if payload.get('planner_used') else 'no'
            pack_title = ((payload.get('chosen_pack') or {}).get('title') or 'sin pack')
            adaptive_payload = dict(payload.get('adaptive_session') or {})
            if payload.get('assistant_guidance') and isinstance(adaptive_payload, dict):
                adaptive_payload['assistant_guidance'] = payload.get('assistant_guidance')
            user_text, meta_line, _chat_evidence_tag = self._user_facing_chat_response(
                message=self._last_user_goal or '',
                raw_summary=str(payload.get('summary') or 'La IA no devolvio texto util.'),
                payload=dict(payload or {}),
                adaptive_payload=adaptive_payload,
            )
            _inference_path = 'orchestrator_inference'
            self._append_message('assistant', 'IABV', user_text, meta_line, evidence_tag=_chat_evidence_tag,
                                 reasoning_path=_inference_path,
                                 trace_metadata={
                                     'provider': payload.get('provider_name', ''),
                                     'model': payload.get('executor_model', ''),
                                     'confidence': payload.get('confidence', ''),
                                     'route_reason': payload.get('route_reason', ''),
                                     'pack': pack_title,
                                     'planner_used': payload.get('planner_used', False),
                                 })
            self._record_chat_audit(
                reasoning_path=_inference_path,
                provider_id=payload.get('provider_name', 'local'),
                model_used=payload.get('executor_model', ''),
                user_goal=self._last_user_goal or '',
                confidence=float(payload.get('confidence') or 0),
            )
            if adaptive_payload and isinstance(adaptive_payload, dict):
                _ap_meta = adaptive_payload.setdefault('metadata', {})
                if isinstance(_ap_meta, dict):
                    _ap_meta['chat_evidence_tag'] = _chat_evidence_tag
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
            self._diagnostic_truth_state = 'observed'
            self._update_adaptive_state(adaptive_payload)
            if adaptive_payload:
                self._busy_label = 'Ya tengo una primera respuesta. Estoy viendo si conviene apoyarme en otra herramienta o seguir por aqui.'
                self._set_autonomy_activity_override(
                    visible=True,
                    title='Evaluando autonomia',
                    status='active',
                    stage='decidiendo si escalo o sigo local',
                    progress=0.56,
                    detail='Ya resolvi la primera respuesta local. Ahora contrasto gobernanza, evidencia y objetivo persistente antes de cerrar la respuesta.',
                    tool='motor local',
                    next_step='Si la evidencia lo pide, abrire Codex, ChatGPT, Claude u Ollama con el contexto redactado.',
                    learning_note='La respuesta local aun puede enriquecerse con consulta externa antes de consolidarse.',
                    mode='local',
                )
                self.dataChanged.emit()
                self._process_ui_events()
                autonomy_result = self._maybe_run_autonomous_evolution(adaptive_payload, source='chat')
                if autonomy_result is None:
                    self._busy_label = 'Respuesta lista.'
                # Track if follow-up work is pending for lifecycle closure.
                _autonomy_status = str((autonomy_result or {}).get('status') or '')
                if _autonomy_status in {'awaiting_response', 'prepared'}:
                    self._interaction_has_pending_followup = True
                self._clear_autonomy_activity_override()
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
            self._diagnostic_truth_state = 'observed'
            if adaptive_payload:
                self._maybe_run_autonomous_evolution(adaptive_payload, source='self_teach')
        elif task_name == 'external_consultation':
            self._last_external_consultation_ts = time.time()
            self._clear_autonomy_activity_override()
            external_payload = dict(payload or {})
            adaptive_payload = dict(external_payload.get('payload') or {})
            if adaptive_payload:
                self._update_adaptive_state(adaptive_payload)
            message = str(external_payload.get('message') or 'No pude completar la consulta externa guiada.')
            meta = str(external_payload.get('meta') or 'Consulta externa sin detalle.')
            _ext_success = bool(external_payload.get('success'))
            _ext_path = 'external_consultation' if _ext_success else 'external_blocked'
            _ext_evidence = 'observed' if _ext_success else 'inferred'
            _ext_assistant = str(external_payload.get('assistant_title') or 'external')
            self._append_message('assistant', 'IABV', message, meta,
                                 reasoning_path=_ext_path, evidence_tag=_ext_evidence,
                                 trace_metadata={'assistant': _ext_assistant, 'blocked': not _ext_success})
            self._record_chat_audit(
                reasoning_path=_ext_path,
                user_goal=self._last_user_goal or '',
                metadata={'assistant': _ext_assistant, 'blocked': not _ext_success},
            )
            self._latest_response_text = message
            self._latest_response_meta = meta
            assistant_title = str(external_payload.get('assistant_title') or 'Asistente externo')
            external_notice = self._external_state_notice(list(external_payload.get('external_state_flags') or []))
            _external_consultation_outcome = self._derive_external_consultation_outcome(external_payload)
            if _ext_success and _external_consultation_outcome != 'blocked':
                self._clear_external_failure_memory()
                try:
                    self._resolve_incident_frame('resolved')
                except Exception:
                    pass
            else:
                self._remember_external_failure(
                    assistant_title=assistant_title,
                    message=message,
                    meta=meta,
                    outcome=_external_consultation_outcome,
                    success=_ext_success,
                    assistant_kind=str(external_payload.get('assistant_kind') or ''),
                    terminal_state=str(external_payload.get('terminal_state') or ''),
                    dispatch_id=str(self._active_dispatch_ids.get('external_consultation', '') or ''),
                )
            self._set_external_consultation_activity(
                external_payload=external_payload,
                adaptive_payload=adaptive_payload,
                assistant_title=assistant_title,
                message=message,
                external_notice=external_notice,
                outcome=_external_consultation_outcome,
            )
            self._busy_label = (
                f'Consulta externa lista con {assistant_title}.'
                if bool(external_payload.get('success')) and _external_consultation_outcome != 'blocked'
                else external_notice or message
            )
        elif task_name == 'payload':
            self._append_message('assistant', 'Payload', f"Payload archivado con {payload.get('episodes')} episodios, {payload.get('artifacts')} artefactos y {payload.get('knowledge')} items de conocimiento.", Path(str(payload.get('path'))).name)
            self._busy_label = f"Payload listo: {Path(str(payload.get('path'))).name}."
        elif task_name == 'security_retest':
            retest_data = dict(payload) if isinstance(payload, dict) else {}
            _rt_title = str(retest_data.get('assistant_title', 'herramienta'))
            if retest_data.get('success'):
                self._append_message(
                    'assistant', 'IABV',
                    f'Retest de {_rt_title} exitoso — la verificacion de seguridad ya no bloquea.',
                    'security_retest_success',
                )
            else:
                _rt_detail = str(retest_data.get('detail', ''))[:200]
                self._append_message(
                    'assistant', 'IABV',
                    f'Retest de {_rt_title} sigue bloqueado. Evidencia: {_rt_detail}. '
                    'Queda UNRESOLVED — prueba con otro perfil de navegador o reinicia la sesion del navegador.',
                    'security_retest_still_blocked',
                )
            self._set_live_status('idle')
        elif task_name == 'pbt':
            self._pbt_state = dict(payload)
            self._pbt_candidates = list(payload.get('candidates', []))[:4]
            self._append_message('assistant', 'PBT', str(payload.get('summary', 'Ciclo PBT completado.')), f"Generacion {payload.get('generation', 0)}")
            self._busy_label = f"PBT actualizado en generacion {payload.get('generation', 0)}."
        if task_name != 'provider_health':
            self._working = False
        # --- Trace dispatch terminal audit ---
        if task_name in ('chat', 'external_consultation', 'adaptive_action', 'self_teach'):
            _dispatch_id_for_trace = self._active_dispatch_ids.get(task_name, '')
            _trace_provider = ''
            if isinstance(payload, dict):
                _trace_provider = str(
                    payload.get('provider_name')
                    or payload.get('assistant_title')
                    or payload.get('assistant_kind')
                    or '',
                )
            _trace_terminal = 'success'
            _trace_reason = 'resolved'
            if task_name == 'external_consultation' and isinstance(payload, dict) and not payload.get('success'):
                _meta_raw = str(payload.get('meta') or '')
                # P0.22: use explicit terminal_state from result payload when available
                # (e.g. blocked_by_resource_pressure from _blocked_external_consultation_result).
                _trace_terminal = str(payload.get('terminal_state') or 'failed_with_actionable_reason')
                if _trace_terminal == 'failed_with_actionable_reason':
                    for _candidate in (
                        'blocked_by_permission', 'blocked_by_security_verification',
                        'blocked_by_quota', 'timeout', 'needs_human_handoff',
                        'blocked_by_resource_pressure',
                        'failed_with_actionable_reason',
                    ):
                        if _candidate in _meta_raw:
                            _trace_terminal = _candidate
                            break
                _trace_reason = f'external_consultation_blocked: {_meta_raw[:120]}'
            self._trace_dispatch_terminal(
                task_name=task_name,
                dispatch_id=_dispatch_id_for_trace,
                terminal_state=_trace_terminal,
                provider=_trace_provider,
                reason=_trace_reason,
                user_visible_message=True,
            )
            if _dispatch_id_for_trace:
                self._invalidate_dispatch(task_name)
        # --- Close canonical interaction episode on resolution ---
        # Do NOT close the interaction if follow-up work is still pending
        # (external consultation dispatched, autonomy awaiting_response, etc.).
        # The episode must stay open until the *real* final resolution.
        _has_pending_followup = getattr(self, '_interaction_has_pending_followup', False)
        if task_name == 'external_consultation':
            # Derive semantic outcome from external consultation status.
            _ext_outcome = (
                _external_consultation_outcome
                if '_external_consultation_outcome' in locals()
                else self._derive_external_consultation_outcome(payload)
            )
            if isinstance(payload, dict):
                _provider = str(
                    payload.get('assistant_title')
                    or payload.get('assistant_kind')
                    or '',
                )
            else:
                _provider = ''
            if _ext_outcome in self._FINAL_INTERACTION_OUTCOMES:
                self._interaction_has_pending_followup = False
                self._resolve_active_interaction(
                    outcome=_ext_outcome,
                    provider=_provider,
                )
            else:
                # Non-final: record the semantic outcome but keep the
                # interaction open for eventual true resolution.
                self._resolve_active_interaction(
                    outcome=_ext_outcome,
                    provider=_provider,
                )
        elif task_name == 'adaptive_action':
            self._interaction_has_pending_followup = False
            if isinstance(payload, dict):
                _provider = str(
                    payload.get('provider_name') or payload.get('assistant_kind') or '',
                )
            else:
                _provider = ''
            self._resolve_active_interaction(outcome='resolved', provider=_provider)
        elif _has_pending_followup:
            # Mark lifecycle phase but keep episode open
            _lc = getattr(self, '_chat_interaction_lifecycle', None)
            _iid = getattr(self, '_active_interaction_id', None)
            if _iid and _lc is not None:
                try:
                    _lc.mark_phase(_iid, 'dispatch_pending')
                except Exception:
                    pass
        else:
            # Derive provider: other tasks use provider_name.
            if isinstance(payload, dict):
                _provider = str(
                    payload.get('provider_name')
                    or payload.get('assistant_title')
                    or payload.get('assistant_kind')
                    or '',
                )
            else:
                _provider = ''
            self._resolve_active_interaction(
                outcome='resolved',
                provider=_provider,
            )
        self._update_progress_cards()
        # P0.23 Task F: activate heavy result guard when the chat task took
        # longer than the threshold.  The guard is consumed by _set_live_status
        # so the subsequent dataChanged.emit in _resolve_active_interaction is
        # deferred to avoid a UI stall.
        if task_name == 'chat':
            _task_elapsed = time.time() - getattr(self, '_task_start_ts', time.time())
            if _task_elapsed > self._HEAVY_RESULT_THRESHOLD_S:
                self._heavy_result_guard_active = True
                try:
                    from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
                    get_runtime_tracer().trace(
                        'post_result_ui_update_coalesced',
                        detail=f'chat result took {_task_elapsed:.1f}s, guard activated',
                    )
                except Exception:
                    pass
        # Gate heavy deferred work under resource pressure (Sub-objective B).
        if not self._should_defer_heavy_work():
            self._update_evolution_snapshot()
            self._agent_cards = self._build_agent_cards()
            # P0.42: never call _refresh_development_packet synchronously
            # from _apply_task_result — schedule via idle budget instead.
            self._schedule_idle_dev_packet_refresh(task_name)
            self._refresh_autonomy_dock()
        else:
            # Even under pressure, mark refresh as pending for later.
            self._dev_packet_refresh_pending = True
        self.dataChanged.emit()

    @Slot(str, str)
    def _apply_task_failure(self, task_name: str, message: str) -> None:
        if task_name == 'security_retest':
            self._append_message(
                'assistant', 'IABV',
                f'Error en retest de seguridad: {message[:200]}. Queda UNRESOLVED.',
                'security_retest_error',
            )
            self._working = False
            self._set_live_status('idle')
            self.dataChanged.emit()
            return
        title = 'IABV' if task_name == 'chat' else task_name.upper()
        visible_message, visible_meta = self._humanize_task_failure(task_name, message)
        if task_name == 'external_consultation':
            self._remember_external_failure(
                assistant_title='Asistente externo',
                message=visible_message,
                meta=visible_meta,
                outcome='failed',
                success=False,
                dispatch_id=str(self._active_dispatch_ids.get(task_name, '') or ''),
            )
        # P0.23 Task E: preserve the active dispatch_id so the terminal trace
        # carries the same id that dispatch_started recorded.
        _failure_dispatch_id = self._active_dispatch_ids.get(task_name, '')
        self._trace_dispatch_terminal(
            task_name=task_name,
            dispatch_id=_failure_dispatch_id,
            terminal_state=visible_meta,
            reason=message[:200],
            user_visible_message=True,
        )
        self._clear_autonomy_activity_override()
        _failure_path = f'{task_name}_failure'
        self._append_message('assistant', title, visible_message, visible_meta,
                             reasoning_path=_failure_path)
        if task_name in ('chat', 'external_consultation'):
            from iabv_v15.services.evolution.decision_audit_trail import DecisionOutcome
            self._record_chat_audit(
                reasoning_path=_failure_path,
                outcome=DecisionOutcome.FAILED,
                user_goal=self._last_user_goal or '',
                error_detail=message[:200],
            )
        if task_name in {'chat', 'adaptive_action', 'external_consultation'}:
            self._latest_response_text = visible_message
            self._latest_response_meta = visible_meta
        if task_name == 'provider_health':
            self._provider_refreshing = False
        else:
            self._working = False
        # --- Close canonical interaction episode on failure ---
        self._interaction_has_pending_followup = False
        self._resolve_active_interaction(outcome='failed')
        self._busy_label = visible_message
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
        self._diagnostic_truth_state = 'observed'
        # Gate heavy deferred work under resource pressure (Sub-objective B).
        if not self._should_defer_heavy_work():
            self._update_evolution_snapshot()
            # P0.42: schedule via idle budget instead of sync call.
            self._schedule_idle_dev_packet_refresh(task_name)
            self._refresh_autonomy_dock()
        else:
            self._dev_packet_refresh_pending = True
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
            lines.append(f"- {card['provider_name']}: {card['status']} | {card['detail']}")
        assistant_cards = self._assistant_tool_cards()
        if assistant_cards:
            lines.append('Asistentes y vias externas')
            for card in assistant_cards:
                lines.append(f"- {card['name']}: {card['status']} | {card['detail']}")
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
    diagnosticTruthState = Property(str, get_diagnostic_truth_state, notify=dataChanged)
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
    canApproveObservation = Property(bool, get_can_approve_observation, notify=dataChanged)
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
            try:
                work_queue = service.current_work_queue(limit=10)
            except Exception:
                work_queue = []
            digest = builder.build(state, work_queue=work_queue).model_dump(mode='json')
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













