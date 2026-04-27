from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
import sys

from iabv_v15.domain.models import ProviderConfig, ProviderKind, WorldModelSnapshot
from iabv_v15.infra.config import load_app_config, load_theme_config
from iabv_v15.infra.logging import configure_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-carga de secretos desde ~/.iabv_secrets.ps1
# ---------------------------------------------------------------------------
# Cuando el usuario arranca la app directamente (python -m iabv_v15) sin
# haber cargado start_iabv.ps1 antes, los env vars de tokens quedan vacios
# y todos los tool adapters reportan "missing". Esta funcion parsea el
# archivo PowerShell de secretos y los inyecta en os.environ SOLO si no
# estan ya seteados (los valores de entorno explicitos siempre ganan).
#
# Patron reconocido:  $env:NOMBRE = 'valor'   o   $env:NOMBRE = "valor"
# Se ignoran lineas comentadas (#), placeholders con REEMPLAZAR, y valores
# vacios.

_PS1_ENV_RE = re.compile(
    r"""^\s*\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['"](.+?)['"]\s*$"""
)


def _auto_load_secrets() -> int:
    """Carga secretos desde ``~/.iabv_secrets.ps1`` si existe.

    Retorna la cantidad de variables inyectadas en ``os.environ``.
    No sobreescribe variables que ya tengan valor en el entorno.
    """
    secrets_path = Path.home() / '.iabv_secrets.ps1'
    if not secrets_path.is_file():
        return 0
    injected = 0
    try:
        for line in secrets_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            m = _PS1_ENV_RE.match(stripped)
            if not m:
                continue
            name, value = m.group(1), m.group(2)
            if 'REEMPLAZAR' in value:
                continue
            if not value.strip():
                continue
            if name not in os.environ or not os.environ[name].strip():
                os.environ[name] = value
                injected += 1
    except Exception as exc:
        logger.warning('auto_load_secrets: no pude leer %s: %s', secrets_path, exc)
    if injected:
        logger.info('auto_load_secrets: %d variables cargadas desde %s', injected, secrets_path)
    return injected


_GITHUB_TOKEN_ENV_VARS: tuple[str, ...] = (
    'GITHUB_TOKEN_IABV',
    'IABV_GITHUB_TOKEN',
    'GITHUB_TOKEN',
    'GH_TOKEN',
)

# Los nombres aceptados para el API key de Devin (Cognition AI). El primario
# historico era ``DEVIN_API_KEY`` (leido sin fallback), pero eso obligaba a
# duplicar el valor si el usuario ya tenia otro nombre en su entorno. Con este
# fallback, ``run_self_audit`` deja de reportar ``devin_api [missing]`` cuando
# el valor esta disponible bajo un alias comun.
_DEVIN_API_KEY_ENV_VARS: tuple[str, ...] = (
    'DEVIN_API_KEY_IABV',
    'IABV_DEVIN_API_KEY',
    'DEVIN_API_KEY',
)


def _resolve_devin_api_key(environ: dict[str, str] | None = None) -> str:
    """Resuelve el API key de Devin para ``DevinApiToolAdapter``.

    Prioridad (orden): ``DEVIN_API_KEY_IABV``, ``IABV_DEVIN_API_KEY``,
    ``DEVIN_API_KEY``. Devuelve string vacio si ninguno tiene valor no-vacio.
    """

    env = environ if environ is not None else os.environ
    for name in _DEVIN_API_KEY_ENV_VARS:
        value = env.get(name)
        if value:
            stripped = value.strip()
            if stripped:
                return stripped
    return ''


def _resolve_github_token(environ: dict[str, str] | None = None) -> str:
    """Resuelve el PAT de GitHub para ``GitHubApiToolAdapter``.

    Prioridad (orden): ``GITHUB_TOKEN_IABV``, ``IABV_GITHUB_TOKEN``,
    ``GITHUB_TOKEN``, ``GH_TOKEN``. Devuelve string vacio si ninguno
    tiene valor no-vacio. Aceptar varios nombres evita que el usuario
    tenga que duplicar su PAT en la laptop: ``gh`` CLI y muchas CIs ya
    exportan ``GITHUB_TOKEN`` por default, y antes el adapter quedaba
    inservible ("missing" en ``run_self_audit``) aunque el token
    estuviera disponible.
    """

    env = environ if environ is not None else os.environ
    for name in _GITHUB_TOKEN_ENV_VARS:
        value = env.get(name)
        if value:
            stripped = value.strip()
            if stripped:
                return stripped
    return ''


def _devin_create_session(adapter, prompt: str) -> str:
    """Crea una sesion en Devin via `DevinApiToolAdapter`.

    Devuelve ``session_id`` o string vacio si falla. No raises: errores
    se registran como log warning y el briefing marca UNRESOLVED en
    lugar de fingir exito.
    """
    if adapter is None or not getattr(adapter, 'api_key', ''):
        return ''
    try:
        import httpx  # local import: evitar imponer dep en tests headless
    except Exception:
        return ''
    try:
        resp = httpx.post(
            adapter._sessions_url,
            headers=adapter._headers(),
            json={'prompt': str(prompt or '')},
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            logger.warning('devin create session http=%s', resp.status_code)
            return ''
        body = resp.json()
        return str(body.get('session_id') or body.get('id') or '')
    except Exception as exc:
        logger.warning('devin create session failed: %s', exc)
        return ''


def _devin_send_message(adapter, session_id: str, content: str) -> bool:
    """Envia un mensaje a una sesion Devin. True si la API respondio 2xx."""
    if adapter is None or not getattr(adapter, 'api_key', ''):
        return False
    if not session_id:
        return False
    try:
        import httpx
    except Exception:
        return False
    try:
        resp = httpx.post(
            f'{adapter.BASE_URL}/session/{session_id}/message',
            headers=adapter._headers(),
            json={'message': str(content or '')},
            timeout=30.0,
        )
        return 200 <= resp.status_code < 300
    except Exception as exc:
        logger.warning('devin send message failed: %s', exc)
        return False


from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.objective_repository import ObjectiveRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.runtime_tuning_repository import RuntimeTuningRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.infra.persistence.replay_annotation_repository import ReplayAnnotationRepository
from iabv_v15.infra.persistence.screenshot_store import ScreenshotStore
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.session_state_store import SessionStateStore
from iabv_v15.infra.persistence.snapshot_version_manager import SnapshotVersionManager
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.adaptive.adaptive_model_selector import AdaptiveModelSelector
from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.adaptive.approval_gate_service import ApprovalGateService
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService, NullOperationalExecutor
from iabv_v15.services.adaptive.goal_engine import GoalEngine
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler
from iabv_v15.services.capture.replay_annotation_service import ReplayAnnotationService
from iabv_v15.services.capture.replay_confidence_service import ReplayConfidenceService
from iabv_v15.services.capture.replay_learning_feedback_service import ReplayLearningFeedbackService
from iabv_v15.services.capture.replay_visual_assembler import ReplayVisualAssembler
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController
from iabv_v15.services.capture.browser_teach_session_service import BrowserTeachSessionService
from iabv_v15.services.capture.redaction_engine import RedactionEngine
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.environment.environment_bootstrap_service import EnvironmentBootstrapService
from iabv_v15.services.providers.provider_health_router import ProviderHealthRouter, default_local_probes
from iabv_v15.services.security.credential_broker import CredentialBroker
from iabv_v15.services.ux.clarification_request_service import ClarificationRequestService
from iabv_v15.services.capture.sensitive_field_detector import SensitiveFieldDetector
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.capture.site_session_manager import SiteSessionManager
from iabv_v15.services.capture.training_profile_manager import TrainingProfileManager
from iabv_v15.services.capture.universal_perception_service import UniversalPerceptionService
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.evolution.autonomy_activity_projector import AutonomyActivityProjector
from iabv_v15.services.evolution.environment_self_awareness_service import EnvironmentSelfAwarenessService
from iabv_v15.services.evolution.world_model_service import WorldModelService
from iabv_v15.services.evolution.execution_dossier_service import ExecutionDossierService
from iabv_v15.services.audit.audit_teach_verification_service import AuditTeachVerificationService
from iabv_v15.services.evolution.evolution_review_service import EvolutionReviewService
from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
from iabv_v15.services.evolution.embodiment_violation_detector import EmbodimentViolationDetector
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
from iabv_v15.services.evolution.control_master_digest_builder import ControlMasterDigestBuilder
from iabv_v15.services.evolution.control_master_service import ControlMasterService
from iabv_v15.services.evolution.git_sync_service import GitSyncService
from iabv_v15.services.evolution.mcp_bridge_service import (
    MCPBridgeService,
    build_mcp_bridge_service,
)
from iabv_v15.services.evolution.consensus_interpretation_service import (
    ConsensusInterpretationService,
)
from iabv_v15.services.evolution.intent_scoped_briefing_service import (
    IntentScopedBriefingService,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService
from iabv_v15.services.evolution.self_audit_service import SelfAuditService
from iabv_v15.services.evolution.token_rotation_ledger import TokenRotationLedger
from iabv_v15.services.evolution.session_start_briefing_service import (
    SessionStartBriefingService,
)
from iabv_v15.services.security.approval_memory import ApprovalMemory
from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker
from iabv_v15.services.security.proactive_dashboard_service import (
    ProactiveDashboardService,
)
from iabv_v15.services.capture.ui_screenshot_service import UIScreenshotService
from iabv_v15.services.evolution.tool_discovery_service import ToolDiscoveryService
from iabv_v15.services.evolution.tool_evolution_monitor import ToolEvolutionMonitor
from iabv_v15.services.evolution.api_key_discovery_service import ApiKeyDiscoveryService
from iabv_v15.services.evolution.decision_audit_trail import DecisionAuditTrail
from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector
from iabv_v15.services.evolution.decision_simplifier_engine import DecisionSimplifierEngine
from iabv_v15.services.evolution.platform_learning_orchestrator import PlatformLearningOrchestrator
from iabv_v15.services.evolution.metacognition_evolution_mixin import MetacognitionEvolutionMixin
from iabv_v15.services.evolution.self_check_orchestrator import SelfCheckOrchestrator
from iabv_v15.services.evolution.session_health_service import SessionHealthService
from iabv_v15.services.evolution.user_clue_service import UserClueService
from iabv_v15.services.inference.inference_service import InferenceService
from iabv_v15.services.self_teach.execution_probe_service import ExecutionProbeService
from iabv_v15.services.self_teach.expectation_matcher import ExpectationMatcher
from iabv_v15.services.self_teach.pending_issue_service import PendingIssueService
from iabv_v15.services.self_teach.result_comparator import ResultComparator
from iabv_v15.services.self_teach.runtime_tuner import RuntimeTuner
from iabv_v15.services.self_teach.scenario_auto_test_service import ScenarioAutoTestService
from iabv_v15.services.self_teach.scenario_registry import ScenarioRegistry
from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService
from iabv_v15.services.self_teach.sandbox_experiment_service import SandboxExperimentService
from iabv_v15.services.self_teach.self_teach_orchestrator import SelfTeachOrchestrator
from iabv_v15.infra.persistence.site_manual_repository import SiteManualRepository
from iabv_v15.services.tools.site_exploration_service import SiteExplorationService
from iabv_v15.services.tools.tool_adapters import AiderToolAdapter, DevinApiToolAdapter, DesktopHumanToolAdapter, ExternalAssistantToolAdapter, GitHubApiToolAdapter, LocalCliToolAdapter, MCPToolAdapter, OllamaToolAdapter, PlaywrightToolAdapter, ShellToolAdapter, SiteExplorerToolAdapter, ToolAdapter
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.gpu_model_benchmark_service import GpuModelBenchmarkService
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.knowledge.knowledge_service import KnowledgeService
from iabv_v15.services.knowledge.unified_memory_layer import UnifiedMemoryLayer
from iabv_v15.services.providers.openai_compat_local_provider import OpenAICompatLocalProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.payload_archive_service import PayloadArchiveService
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.training.training_orchestrator import TrainingOrchestrator
from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
from iabv_v15.ui.controllers.navigation_controller import NavigationController
from iabv_v15.ui.controllers.theme_controller import ThemeController
from iabv_v15.ui.qt import PYSIDE_AVAILABLE, QGuiApplication, QQmlApplicationEngine, QQuickStyle, QUrl
from iabv_v15.ui.viewmodels.capture_studio_viewmodel import CaptureStudioViewModel
from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
from iabv_v15.ui.viewmodels.evolution_center_viewmodel import EvolutionCenterViewModel
from iabv_v15.ui.viewmodels.knowledge_base_viewmodel import KnowledgeBaseViewModel
from iabv_v15.ui.viewmodels.provider_settings_viewmodel import ProviderSettingsViewModel
from iabv_v15.ui.viewmodels.centro_vivo_viewmodel import CentroVivoViewModel
from iabv_v15.ui.viewmodels.run_history_viewmodel import RunHistoryViewModel


class AppBootstrap:
    def __init__(self, workspace_root: str | None = None) -> None:
        # Auto-cargar secretos ANTES de leer config (que consulta os.environ).
        _auto_load_secrets()

        self.config = load_app_config(workspace_root)
        self.theme = load_theme_config()
        self._ensure_directories()
        configure_logging(self.config.logs_dir)

        self.db = AppDatabase(self.config.sqlite_path)
        self.screenshot_storage = ArtifactStorage(self.config.screenshots_dir)
        self.browser_artifact_storage = ArtifactStorage(self.config.browser_artifacts_dir)
        self.evolution_storage = ArtifactStorage(self.config.evolution_dir)
        self.replay_annotation_storage = ArtifactStorage(self.config.replay_annotations_dir)
        self.tool_teaching_storage = ArtifactStorage(self.config.tool_teaching_dir)
        self.episode_repository = EpisodeRepository(self.config.episodes_dir, self.db)
        self.knowledge_repository = KnowledgeRepository(self.db)
        self.run_repository = RunRepository(self.db)
        self.execution_dossier_repository = ExecutionDossierRepository(self.db, self.evolution_storage)
        self.hidden_incident_repository = HiddenIncidentRepository(self.db, self.evolution_storage)
        self.user_clue_repository = UserClueRepository(self.db, self.evolution_storage)
        self.replay_annotation_repository = ReplayAnnotationRepository(self.db, self.replay_annotation_storage)
        self.tool_record_repository = ToolRecordRepository(self.db, self.tool_teaching_storage)
        self.experiment_lab_repository = ExperimentLabRepository(self.db, self.evolution_storage)
        self.adaptive_session_repository = AdaptiveSessionRepository(self.db, self.evolution_storage)
        self.scenario_run_repository = ScenarioRunRepository(self.db, self.evolution_storage)
        self.runtime_tuning_repository = RuntimeTuningRepository(self.db, self.evolution_storage)
        self.pending_issue_repository = PendingIssueRepository(self.db, self.evolution_storage)
        self.strategy_pack_repository = StrategyPackRepository(self.db, self.evolution_storage)
        self.capability_repository = CapabilityRepository(self.db, self.evolution_storage)
        self.objective_repository = ObjectiveRepository(self.db, self.evolution_storage)
        self.approval_checkpoint_repository = ApprovalCheckpointRepository(self.db, self.evolution_storage)
        self.session_artifact_repository = SessionArtifactRepository(self.db, self.browser_artifact_storage)
        self.session_state_store = SessionStateStore()
        self.screenshot_store = ScreenshotStore(self.screenshot_storage)
        self.snapshot_manager = SnapshotVersionManager(self.config.payloads_dir)
        self.payload_archive_service = PayloadArchiveService(self.config.payloads_dir, self.snapshot_manager)

        self.training_profile_manager = TrainingProfileManager(self.config.browser_profiles_dir)
        self.site_policy_registry = SitePolicyRegistry(self.config.site_policies_dir)
        self.sensitive_field_detector = SensitiveFieldDetector()
        self.secret_vault = SecretVault()
        self.redaction_engine = RedactionEngine(self.sensitive_field_detector, self.secret_vault)
        self.site_session_manager = SiteSessionManager(self.session_state_store)
        self.replay_confidence_service = ReplayConfidenceService()
        self.replay_annotation_service = ReplayAnnotationService(self.replay_annotation_repository)
        self.replay_visual_assembler = ReplayVisualAssembler(self.replay_confidence_service)
        self.replay_learning_feedback_service = ReplayLearningFeedbackService()
        self.browser_learning_assembler = BrowserLearningAssembler(self.replay_confidence_service)
        self.browser_session_controller = BrowserSessionController()
        self.browser_teach_session_service = BrowserTeachSessionService(
            controller=self.browser_session_controller,
            episode_repository=self.episode_repository,
            screenshot_store=self.screenshot_store,
            artifact_repository=self.session_artifact_repository,
            redaction_engine=self.redaction_engine,
            site_session_manager=self.site_session_manager,
        )
        self.development_assist_service = DevelopmentAssistService(self.config.workspace_root)
        self.pbt_control_service = PBTControlService(self.config.models_dir)
        self.runtime_signal_collector = RuntimeSignalCollector()
        self.hidden_incident_detector = HiddenIncidentDetector()
        self.session_health_service = SessionHealthService()
        self.user_clue_service = UserClueService(
            clue_repository=self.user_clue_repository,
            incident_repository=self.hidden_incident_repository,
        )

        self.provider_configs = [
            ProviderConfig(name='Ollama', kind=ProviderKind.LOCAL, base_url=self.config.ollama_base_url, model=self.config.ollama_model),
            ProviderConfig(name='Ollama Vision', kind=ProviderKind.LOCAL, base_url=self.config.ollama_base_url, model=self.config.ollama_visual_model),
            ProviderConfig(name='LM Studio', kind=ProviderKind.LOCAL, base_url=self.config.lm_studio_base_url, model=self.config.lm_studio_model, optional=True),
        ]

        self.general_provider = OpenAICompatLocalProvider(self.provider_configs[0], self.config.provider_timeout_seconds)
        self.visual_provider = OpenAICompatLocalProvider(self.provider_configs[1], self.config.provider_timeout_seconds)
        self.optional_visual_provider = OpenAICompatLocalProvider(self.provider_configs[2], self.config.provider_timeout_seconds)
        self.site_manual_repository = SiteManualRepository(
            Path(self.config.evolution_dir) / 'site_manuals'
        )
        self.site_exploration_service = SiteExplorationService()
        self.tool_adapters = {
            'playwright': PlaywrightToolAdapter(),
            'ollama': OllamaToolAdapter(self.general_provider),
            'shell': ShellToolAdapter(),
            'desktop_human': DesktopHumanToolAdapter(self.config.workspace_root),
            'aider': AiderToolAdapter(),
            'mcp': MCPToolAdapter(),
            'external_assistant': ExternalAssistantToolAdapter(),
            'devin_api': DevinApiToolAdapter(
                # Igual que con ``GITHUB_TOKEN_IABV``, aceptamos varios alias
                # (``DEVIN_API_KEY_IABV`` preferido) para no forzar al usuario
                # a duplicar el valor si ya lo tiene cargado bajo otro nombre.
                # Si nada esta disponible, ``is_available`` devuelve False y
                # ``run_self_audit`` reporta ``devin_api [missing]``.
                api_key=_resolve_devin_api_key(os.environ),
                # DEVIN_ORG_ID ya no es requerido por v1; se mantiene para compat.
                org_id=os.environ.get('DEVIN_ORG_ID', ''),
            ),
            'github_api': GitHubApiToolAdapter(
                # El nombre primario historico es ``GITHUB_TOKEN_IABV``, pero
                # aceptamos fallbacks comunes (``IABV_GITHUB_TOKEN``,
                # ``GITHUB_TOKEN``, ``GH_TOKEN``) porque cuando el usuario
                # arranca el MCP en su laptop ya tiene un PAT cargado como
                # ``GITHUB_TOKEN`` para el ``gh`` CLI y no quiere duplicarlo
                # a mano. Sin esta cadena, ``is_available`` devuelve False y
                # ``run_self_audit`` reporta ``github_api [missing]`` aunque
                # el token este disponible en el entorno. El orden preserva
                # la intencion original: el scope dedicado a IABV gana si
                # existe; si no, se cae al global.
                token=_resolve_github_token(os.environ),
                # repo scoped: evita que un token amplio haga cosas en
                # repos no deseados; default al propio repo del proyecto.
                repo=os.environ.get('GITHUB_REPO', 'jhonf463r/Python'),
            ),
            'site_explorer': SiteExplorerToolAdapter(
                self.site_exploration_service,
                self.site_manual_repository,
            ),
            # Adapter read-only compartido por los ToolCards de CLIs locales
            # (``gh_cli``, ``cloudflared_cli``, ``git_cli``, ``winget_cli``).
            # Un solo adapter registrado bajo ``local_cli`` atiende a los 4
            # cards; cada card declara en su ``metadata`` el nombre del
            # binario, los ``allowed_verbs`` y rutas Windows tipicas.
            'local_cli': LocalCliToolAdapter(),
        }
        # Wire cross-process disagreement marker directory so the MCP
        # subprocess suppresses INFO logs already emitted by the UI process.
        ToolAdapter.set_disagreement_marker_dir(
            Path(self.config.data_dir) / 'logs',
        )
        self.tool_validator = ToolValidator()
        self.tool_sandbox = ToolSandbox(self.tool_validator)
        self.tool_registry = ToolRegistry(self.tool_record_repository, self.tool_adapters)
        self._log_tool_availability()
        self.universal_perception_service = UniversalPerceptionService(tool_registry=self.tool_registry)
        self.environment_self_awareness_service = EnvironmentSelfAwarenessService(
            workspace_root=self.config.workspace_root,
            evolution_dir=self.config.evolution_dir,
            role_router=None,
            tool_registry=self.tool_registry,
        )
        # The MCP subprocess inherits the persisted world model snapshot from
        # the main UI process.  It doesn't need its own aggressive 18-second
        # background scan (which re-probes Ollama, Devin API, GitHub API each
        # cycle).  Disable bootstrap_scan entirely (the snapshot on disk is
        # fresh from the UI process) and use 300s/600s intervals for the
        # background thread to cut redundant API calls from ~70/hour to ~12.
        _is_mcp_sub = os.environ.get('IABV_MCP_SUBPROCESS') == '1'
        self.world_model_service = WorldModelService(
            workspace_root=self.config.workspace_root,
            evolution_dir=self.config.evolution_dir,
            tool_registry=self.tool_registry,
            tool_record_repository=self.tool_record_repository,
            environment_self_awareness_service=self.environment_self_awareness_service,
            universal_perception_service=self.universal_perception_service,
            role_router=None,
            bootstrap_scan=not _is_mcp_sub,
            scan_interval_seconds=300.0 if _is_mcp_sub else WorldModelService._DEFAULT_SCAN_INTERVAL,
            full_scan_interval_seconds=600.0 if _is_mcp_sub else WorldModelService._DEFAULT_FULL_SCAN_INTERVAL,
        )
        self.interaction_learning_service = InteractionLearningService(self.tool_record_repository)
        self.interaction_mode_selector = InteractionModeSelector(self.tool_registry, self.tool_record_repository)
        self.tool_memory = ToolMemory(self.tool_record_repository, self.interaction_learning_service)
        self.tool_approval_policy = ToolApprovalPolicy()
        self.tool_rollback_manager = ToolRollbackManager()
        self.algorithm_benchmark_registry = AlgorithmBenchmarkRegistry()
        self.decision_scoring_engine = DecisionScoringEngine()
        self.adaptive_weight_layer = AdaptiveWeightLayer()
        self.lab_strategy_selector = StrategySelector(adaptive_weight_layer=self.adaptive_weight_layer)
        # PCS v1 dependencies are created before ToolTeachService so external
        # tool selection can consume SynapticRouter hints without replacing
        # LocalRoleRouter or AdaptiveTaskOrchestrator.
        try:
            from iabv_v15.services.adaptive.consensus_fusion_service import (
                ConsensusFusionService,
            )
            from iabv_v15.services.roles.assistant_capability_registry import (
                AssistantCapabilityRegistry,
            )
            from iabv_v15.services.roles.cognitive_frame_translator import (
                CognitiveFrameTranslator,
            )
            from iabv_v15.services.roles.synaptic_router import SynapticRouter

            self.assistant_capability_registry = AssistantCapabilityRegistry.with_defaults()
            self.cognitive_frame_translator = CognitiveFrameTranslator(
                capability_registry=self.assistant_capability_registry,
            )

            world_model_service = self.world_model_service

            def _synaptic_world_model_provider() -> WorldModelSnapshot | None:
                try:
                    return world_model_service.current_model()
                except Exception:  # pragma: no cover - defensive
                    return None

            self.synaptic_router = SynapticRouter(
                capability_registry=self.assistant_capability_registry,
                adaptive_weight_layer=self.adaptive_weight_layer,
                world_model_provider=_synaptic_world_model_provider,
                experiment_lab_repository=self.experiment_lab_repository,
                enabled_override=getattr(
                    self.config, "synaptic_routing_enabled", None
                ),
            )
            self.consensus_fusion_service = ConsensusFusionService(
                adaptive_weight_layer=self.adaptive_weight_layer,
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "No se pudo wirear PCS v1 temprano; las tools MCP PCS reportarán *_unavailable"
            )
            self.assistant_capability_registry = None
            self.cognitive_frame_translator = None
            self.synaptic_router = None
            self.consensus_fusion_service = None
        self.experiment_lab = ExperimentLab(
            repository=self.experiment_lab_repository,
            registry=self.algorithm_benchmark_registry,
            scoring_engine=self.decision_scoring_engine,
            strategy_selector=self.lab_strategy_selector,
        )
        self.gpu_model_benchmark_service = GpuModelBenchmarkService(
            experiment_lab=self.experiment_lab,
        )
        self.live_audit_supervisor = LiveAuditSupervisor(
            tool_record_repository=self.tool_record_repository,
            experiment_lab=self.experiment_lab,
        )
        self.sandbox_experiment_service = SandboxExperimentService(experiment_lab=self.experiment_lab)
        self.autonomous_validation_cycle = AutonomousValidationCycleService(
            experiment_lab=self.experiment_lab,
            experiment_lab_repository=self.experiment_lab_repository,
            sandbox_experiment_service=self.sandbox_experiment_service,
            world_model_service=self.world_model_service,
            environment_self_awareness_service=self.environment_self_awareness_service,
            storage=self.evolution_storage,
            tool_registry=self.tool_registry,
            research_backlog_root=self.config.data_dir,
        )
        self.tool_discovery_service = ToolDiscoveryService(
            storage=self.evolution_storage,
            tool_registry=self.tool_registry,
            experiment_lab_repository=self.experiment_lab_repository,
            world_model_service=self.world_model_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
        )
        self.audit_teach_verification_service = AuditTeachVerificationService(
            replay_confidence_service=self.replay_confidence_service,
            sensitive_field_detector=self.sensitive_field_detector,
        )
        self.tool_teach_service = ToolTeachService(
            registry=self.tool_registry,
            memory=self.tool_memory,
            sandbox=self.tool_sandbox,
            validator=self.tool_validator,
            approval_policy=self.tool_approval_policy,
            rollback_manager=self.tool_rollback_manager,
            adapters=self.tool_adapters,
            workspace_root=self.config.workspace_root,
            interaction_learning_service=self.interaction_learning_service,
            mode_selector=self.interaction_mode_selector,
            experiment_lab=self.experiment_lab,
            live_audit_supervisor=self.live_audit_supervisor,
            synaptic_router=self.synaptic_router,
        )
        self.embedding_service = EmbeddingIndexService(
            base_url=self.config.ollama_base_url,
            primary_model=self.config.ollama_embedding_model,
            lightweight_model=self.config.ollama_embedding_light_model,
            state_path=str(Path(self.config.models_dir) / 'embedding_index_state.json'),
            timeout_seconds=self.config.provider_timeout_seconds,
        )
        self.sql_query_service = SqlQueryAdvisorService(self.config.sqlite_path)
        self.analytics_service = AnalyticsStrategyService(
            self.episode_repository,
            self.knowledge_repository,
            self.run_repository,
            self.session_artifact_repository,
        )
        self.customer_support_service = CustomerSupportService(
            self.knowledge_repository,
            self.embedding_service,
            self.sql_query_service,
        )
        self.teaching_gap_analyzer = TeachingGapAnalyzer()
        self.engineering_review_service: EngineeringReviewService | None = None
        self.role_router: LocalRoleRouter | None = None

        self.role_router = LocalRoleRouter(
            workspace_root=self.config.workspace_root,
            general_provider=self.general_provider,
            visual_provider=self.visual_provider,
            optional_provider=self.optional_visual_provider,
            embedding_service=self.embedding_service,
            sql_service=self.sql_query_service,
            analytics_service=self.analytics_service,
            customer_support_service=self.customer_support_service,
            engineering_review_service=None,  # type: ignore[arg-type]
            teaching_gap_analyzer=self.teaching_gap_analyzer,
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            artifact_repository=self.session_artifact_repository,
            tool_teach_service=self.tool_teach_service,
        )
        self.environment_self_awareness_service.role_router = self.role_router
        self.environment_self_awareness_service.request_refresh(reason='role_router_ready', full=False)
        self.world_model_service.role_router = self.role_router
        self.world_model_service.request_refresh(reason='role_router_ready', full=False)
        from iabv_v15.services.evolution.perception_cross_validator import PerceptionCrossValidator
        self.perception_cross_validator = PerceptionCrossValidator(
            world_model_service=self.world_model_service,
            tool_registry=self.tool_registry,
        )
        self.self_check_orchestrator = SelfCheckOrchestrator(
            role_router=self.role_router,
            embedding_service=self.embedding_service,
            sql_service=self.sql_query_service,
            episode_repository=self.episode_repository,
            pbt_service=self.pbt_control_service,
        )
        self.evolution_review_service = EvolutionReviewService(
            dossier_repository=self.execution_dossier_repository,
            hidden_incident_repository=self.hidden_incident_repository,
            analytics_service=self.analytics_service,
            teaching_gap_analyzer=self.teaching_gap_analyzer,
            pbt_service=self.pbt_control_service,
            adaptive_session_repository=self.adaptive_session_repository,
            pending_issue_repository=self.pending_issue_repository,
            scenario_run_repository=self.scenario_run_repository,
        )
        # Capa 2.2 — ledger de rotacion de tokens. Persiste probe_ok /
        # probe_failed / rotated por PAT (github_api, devin_api) para que
        # ``OperationalSelfExaminationService`` pueda emitir findings
        # proactivos antes de que el usuario note el 401. Es un ledger
        # append-only read-only sobre el sistema vivo: no dispara nada.
        self.token_rotation_ledger = TokenRotationLedger(self.config.workspace_root)
        self.operational_self_examination_service = OperationalSelfExaminationService(
            workspace_root=self.config.workspace_root,
            storage=self.evolution_storage,
            run_repository=self.run_repository,
            adaptive_session_repository=self.adaptive_session_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            scenario_run_repository=self.scenario_run_repository,
            evolution_review_service=self.evolution_review_service,
            world_model_service=self.world_model_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            adaptive_weight_layer=self.adaptive_weight_layer,
            token_rotation_ledger=self.token_rotation_ledger,
        )
        # PCS v1 — PR E. Detector read-only de violaciones de encarnamiento.
        # handshake_required=False en el manifest → sólo reporta.
        # Lo enchufamos al self_examination como provider para poblar
        # ``metadata['embodiment_violations']`` del snapshot sin cambiar el
        # contrato de SelfExaminationSnapshot.
        self.embodiment_violation_detector = EmbodimentViolationDetector()
        self.operational_self_examination_service.embodiment_violation_provider = (
            self.embodiment_violation_detector
        )
        self.tool_evolution_monitor = ToolEvolutionMonitor(
            storage=self.evolution_storage,
            experiment_lab_repository=self.experiment_lab_repository,
            adaptive_weight_layer=self.adaptive_weight_layer,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            tool_discovery_service=self.tool_discovery_service,
        )
        self.autonomous_validation_cycle.tool_evolution_monitor = self.tool_evolution_monitor
        self.incident_packet_service = IncidentPacketService(
            dossier_repository=self.execution_dossier_repository,
            hidden_incident_repository=self.hidden_incident_repository,
            user_clue_repository=self.user_clue_repository,
            workspace_root=self.config.workspace_root,
            pending_issue_repository=self.pending_issue_repository,
            tool_record_repository=self.tool_record_repository,
        )
        self.engineering_review_service = EngineeringReviewService(
            workspace_root=self.config.workspace_root,
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            artifact_repository=self.session_artifact_repository,
            analytics_service=self.analytics_service,
            teaching_gap_analyzer=self.teaching_gap_analyzer,
            pbt_service=self.pbt_control_service,
            development_assist_service=self.development_assist_service,
            execution_dossier_repository=self.execution_dossier_repository,
            evolution_review_service=self.evolution_review_service,
            incident_packet_service=self.incident_packet_service,
        )
        self.role_router.engineering_review_service = self.engineering_review_service
        self.execution_dossier_service = ExecutionDossierService(
            repository=self.execution_dossier_repository,
            hidden_incident_repository=self.hidden_incident_repository,
            user_clue_repository=self.user_clue_repository,
            self_check_orchestrator=self.self_check_orchestrator,
            role_router=self.role_router,
        )
        self.autonomy_activity_projector = AutonomyActivityProjector(
            tool_record_repository=self.tool_record_repository,
            pending_issue_repository=self.pending_issue_repository,
            experiment_lab_repository=self.experiment_lab_repository,
        )

        self.intent_understanding_service = IntentUnderstandingService()
        self.autonomy_governance_policy = AutonomyGovernancePolicy()
        self.goal_engine = GoalEngine(self.objective_repository)
        self.portable_context_service = PortableContextService(
            workspace_root=self.config.workspace_root,
            storage=self.evolution_storage,
            objective_repository=self.objective_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            pending_issue_repository=self.pending_issue_repository,
            evolution_review_service=self.evolution_review_service,
            environment_self_awareness_service=self.environment_self_awareness_service,
            world_model_service=self.world_model_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            self_examination_service=self.operational_self_examination_service,
            tool_discovery_service=self.tool_discovery_service,
            tool_evolution_monitor=self.tool_evolution_monitor,
            adaptive_session_repository=self.adaptive_session_repository,
        )
        # --- Security & evolution broker stack (PR #101-#106) ---
        # Wiring minimo de los servicios que cierran el loop "el programa
        # pide lo que necesita del humano y aprende de las aprobaciones".
        # Cada servicio respeta las capas cerradas (P1-P4): no duplican
        # WorldModel/PortableContext, no deciden rutas, no crean otro cerebro.
        self.human_approval_broker = HumanApprovalBroker()
        self.approval_memory = ApprovalMemory(
            storage_path=Path(self.config.evolution_dir) / 'approvals' / 'policies.json',
        )
        self.proactive_dashboard_service = ProactiveDashboardService(
            broker=self.human_approval_broker,
            memory=self.approval_memory,
        )
        # F1.1: captura de snapshots UI de IABV persistida con retention.
        # No es otro cerebro ni orquestador; solo evidencia visual para
        # que ExecutionDossier / briefings / revision humana puedan citar.
        self.ui_screenshot_service = UIScreenshotService(
            storage_dir=Path(self.config.evolution_dir) / 'ui_snapshots',
        )
        # F1.2: cuando IABV necesita presencia humana, dejamos una foto del
        # estado de la UI para que la revision posterior pueda reconstruir
        # que estaba viendo el usuario. Best-effort; el broker sigue
        # funcionando si la captura falla.
        self.human_approval_broker.set_ui_screenshot_capturer(
            self.ui_screenshot_service
        )
        # Devin API adapter es opcional (requiere DEVIN_API_KEY). Si no esta
        # disponible, el briefing sigue siendo util como dato estructurado; las
        # callables devuelven strings vacios y el servicio marca UNRESOLVED en
        # lugar de fingir exito.
        _devin_api_adapter = self.tool_adapters.get('devin_api')
        self.session_start_briefing_service = SessionStartBriefingService(
            portable_context_service=self.portable_context_service,
            session_creator=(
                (lambda prompt: _devin_create_session(_devin_api_adapter, prompt))
                if _devin_api_adapter is not None
                else None
            ),
            message_sender=(
                (lambda sid, content: _devin_send_message(_devin_api_adapter, sid, content))
                if _devin_api_adapter is not None
                else None
            ),
        )
        self.intent_scoped_briefing_service = IntentScopedBriefingService(
            session_start_briefing_service=self.session_start_briefing_service,
        )
        self.consensus_interpretation_service = ConsensusInterpretationService(
            interpreters={},
            human_approval_broker=self.human_approval_broker,
        )
        # F2.1 GitHubRemoteService: permite que IABV abra sus propios PRs via
        # GitHubApiToolAdapter respetando AutonomyGovernancePolicy
        # (``iabv-auto/*`` auto si diff < 200; ``devin/*`` requiere humano;
        # main/master como head bloqueado siempre). Deja evidencia en
        # ``data/evolution/pr_history/`` para auditoria posterior. No decide
        # rutas: consume policy + broker + adapter ya existentes.
        from iabv_v15.services.tools.github_remote_service import GitHubRemoteService
        self.github_remote_service = GitHubRemoteService(
            repo_root=self.config.workspace_root,
            adapter=self.tool_adapters['github_api'],
            governance_policy=self.autonomy_governance_policy,
            approval_broker=self.human_approval_broker,
            evidence_dir=Path(self.config.evolution_dir) / 'pr_history',
        )
        # F2.3 (thin): cuando ``AutonomousValidationCycleService`` promueve un
        # candidato, ``PromotionPrPublisher`` escribe un markdown de traza en
        # ``data/evolution/promoted/`` y abre un PR documental contra ``main``
        # usando la rama ``iabv-auto/promote-<subject>-<ts>``. La policy
        # existente auto-aprueba (``iabv-auto/*`` con diff <= 200) salvo que
        # se configure lo contrario. Se deja en OFF por defecto via
        # ``IABV_AUTO_PROMOTION_PR_ENABLED`` para no abrir PRs no deseados en
        # instalaciones donde el ciclo arranca sin supervision.
        from iabv_v15.services.self_teach.promotion_pr_publisher import (
            PromotionPrPublisher,
        )
        _promo_enabled = str(
            os.environ.get('IABV_AUTO_PROMOTION_PR_ENABLED', '0') or '0'
        ).strip().lower() in {'1', 'true', 'yes', 'on'}
        self.promotion_pr_publisher = PromotionPrPublisher(
            repo_root=self.config.workspace_root,
            github_remote_service=self.github_remote_service,
            output_dir=Path(self.config.evolution_dir) / 'promoted',
            enabled=_promo_enabled,
        )
        self.autonomous_validation_cycle.set_promotion_pr_publisher(
            self.promotion_pr_publisher
        )
        self.self_audit_service = SelfAuditService(
            tool_registry=self.tool_registry,
            environment_self_model_provider=self.environment_self_awareness_service.current_model,
            world_model_service=self.world_model_service,
            operational_self_examination_service=self.operational_self_examination_service,
            portable_context_service=self.portable_context_service,
            workspace_root=self.config.workspace_root,
            token_rotation_ledger=self.token_rotation_ledger,
        )
        # Frente 3.2 — CapabilityAuditHarness: registra runners para las 5
        # capacidades iniciales usando piezas que ya existen en el bootstrap.
        # Se hace acá, bien tarde en el wiring, para garantizar que todas las
        # dependencias estén ya construidas. Si alguna falla (por ejemplo,
        # Playwright no está instalado), se reporta por ``harness.run()`` con
        # un error tipado; no rompemos el bootstrap.
        from iabv_v15.services.evolution.capability_audit_harness import (
            CapabilityAuditHarness,
        )
        from iabv_v15.infra.mcp.audit_tools.audit_capability import (
            build_browser_capture_runner,
            build_domain_capability_runner,
            build_llm_external_runner,
            build_llm_local_ollama_runner,
            build_ui_execution_runner,
        )
        from iabv_v15.services.evolution.capability_audit_harness import (
            DOMAIN_CAPABILITY_IDS,
        )

        self.capability_audit_harness = CapabilityAuditHarness()
        self.capability_audit_harness.register(
            "llm_local_ollama",
            build_llm_local_ollama_runner(self.general_provider),
        )

        from typing import Any as _Any

        def _probe_login_closure(kind: str) -> dict[str, _Any]:
            # Usa el entrypoint puro; el gate de governance lo aplica la MCP
            # tool, no el harness. Acá sólo ejecutamos la sonda.
            from iabv_v15.infra.mcp.audit_tools.probe_assistant_login import (
                probe_assistant_login as _probe,
            )

            return _probe(kind, use_browser_session=True, timeout_seconds=10.0)

        for _assistant_kind in ("chatgpt", "claude"):
            self.capability_audit_harness.register(
                f"llm_external_{_assistant_kind}",
                build_llm_external_runner(
                    _assistant_kind,
                    probe_login=_probe_login_closure,
                ),
            )

        def _browser_controller_factory() -> _Any:
            # Reusa el controller existente de Browser Teach Mode
            # (``BrowserSessionController``). Si Playwright no está
            # instalado o el constructor falla, devolvemos None y el
            # runner reporta ``playwright_unavailable``/``controller_init_failed``
            # sin romper el bootstrap.
            try:
                from iabv_v15.services.capture.browser_session_controller import (
                    BrowserSessionController,
                )
            except Exception:
                return None
            try:
                return BrowserSessionController(headless=True)
            except Exception:
                return None

        self.capability_audit_harness.register(
            "browser_capture",
            build_browser_capture_runner(_browser_controller_factory),
        )

        def _ui_executor(**_kwargs: _Any) -> dict[str, _Any]:
            from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner

            runner = UIExecutionRunner(workspace_root=str(self.config.workspace_root))
            return {
                "success": True,
                "output_text": f"noop@{runner.__class__.__name__}",
            }

        self.capability_audit_harness.register(
            "ui_execution",
            build_ui_execution_runner(_ui_executor),
        )

        # Frente 3.2b — Capacidades de dominio (Wplay + browser).
        #
        # El runner no ejecuta sondas externas ni consume red; lee el snapshot
        # persistido por ``CapabilityReadinessService`` vía ``capability_repository``
        # y reporta estado (``capability_pack_not_captured`` / ``partial`` / ``ready``).
        # Esto cierra el gap que quedaba: ``audit_capability`` respondía
        # ``capability_not_registered`` para ``wplay.login`` y afines, y el
        # diagnóstico estructurado de PR #110 no tenía contraparte física.
        _capability_site_map: dict[str, str | None] = {
            "wplay.login": "wplay",
            "wplay.session.restore": "wplay",
            "wplay.navigate.casino": "wplay",
            "browser.search.google": "google",
            "browser.generic.navigation": None,
        }

        def _readiness_provider(capability_id: str, site_id: str | None) -> _Any:
            repo = getattr(self, "capability_repository", None)
            if repo is None:
                return None
            try:
                return repo.get(capability_id, site_id)
            except Exception:
                return None

        for _domain_capability_id in DOMAIN_CAPABILITY_IDS:
            self.capability_audit_harness.register(
                _domain_capability_id,
                build_domain_capability_runner(
                    _domain_capability_id,
                    site_id=_capability_site_map.get(_domain_capability_id),
                    readiness_provider=_readiness_provider,
                ),
            )

        # Frente 3.3 — PerceptionGroundTruthComparator.
        #
        # Contrasta la perception que genera ``UniversalPerceptionService``
        # contra el ``WorldModelSnapshot`` vigente. No duplica contratos,
        # no consume red, no toca UI; sólo observa y compara. Es seguro
        # tenerlo siempre wireado: si alguna dependencia está caída,
        # degrada a ``ground_truth_unavailable``/``perception_error``.
        try:
            from iabv_v15.services.capture.perception_ground_truth_comparator import (
                PerceptionGroundTruthComparator,
            )

            def _world_model_snapshot_provider() -> _Any:
                svc = getattr(self, "world_model_service", None)
                if svc is None:
                    return None
                try:
                    return svc.current_model()
                except Exception:  # pragma: no cover - defensive
                    return None

            self.perception_ground_truth_comparator = PerceptionGroundTruthComparator(
                universal_perception_service=self.universal_perception_service,
                world_model_provider=_world_model_snapshot_provider,
                screenshot_provider=None,
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "No se pudo wirear PerceptionGroundTruthComparator; la MCP tool reportará comparator_unavailable"
            )
            self.perception_ground_truth_comparator = None

        self.control_master_repository = ControlMasterRepository(self.evolution_storage)
        self.control_master_service = ControlMasterService(
            repository=self.control_master_repository,
            objective_repository=self.objective_repository,
            pending_issue_repository=self.pending_issue_repository,
            self_examination_service=self.operational_self_examination_service,
            experiment_lab_repository=self.experiment_lab_repository,
        )
        self.control_master_digest_builder = ControlMasterDigestBuilder()
        self.git_sync_service = GitSyncService(
            repo_root=self.config.workspace_root,
            branch='main',
            autonomy_governance_policy=self.autonomy_governance_policy,
            control_master_service=self.control_master_service,
        )
        self.task_context_assembler = TaskContextAssembler(
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            dossier_repository=self.execution_dossier_repository,
            hidden_incident_repository=self.hidden_incident_repository,
            site_policy_registry=self.site_policy_registry,
            capability_repository=self.capability_repository,
            adaptive_session_repository=self.adaptive_session_repository,
            artifact_repository=self.session_artifact_repository,
            tool_record_repository=self.tool_record_repository,
            objective_repository=self.objective_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            live_audit_supervisor=self.live_audit_supervisor,
            environment_self_awareness_service=self.environment_self_awareness_service,
            world_model_service=self.world_model_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            portable_context_service=self.portable_context_service,
        )
        self.capability_readiness_service = CapabilityReadinessService(self.capability_repository, self.tool_record_repository)
        self.strategy_pack_registry = StrategyPackRegistry(self.strategy_pack_repository)
        self.adaptive_planner_service = AdaptivePlannerService()
        self.approval_gate_service = ApprovalGateService()
        self.operational_executor = ToolOperationalExecutor(self.tool_teach_service)
        self.execution_playbook_service = ExecutionPlaybookService(executor=self.operational_executor)
        self.task_outcome_recorder = TaskOutcomeRecorder(
            adaptive_session_repository=self.adaptive_session_repository,
            capability_repository=self.capability_repository,
            approval_checkpoint_repository=self.approval_checkpoint_repository,
            experiment_lab=self.experiment_lab,
            adaptive_weight_layer=self.adaptive_weight_layer,
            control_master_service=self.control_master_service,
            intent_understanding_service=self.intent_understanding_service,
        )
        self.scenario_registry = ScenarioRegistry()
        self.execution_probe_service = ExecutionProbeService(
            matcher=ExpectationMatcher(),
            comparator=ResultComparator(),
        )
        self.runtime_tuner = RuntimeTuner(
            repository=self.runtime_tuning_repository,
            hidden_incident_detector=self.hidden_incident_detector,
            strategy_pack_registry=self.strategy_pack_registry,
        )
        self.pending_issue_service = PendingIssueService(self.pending_issue_repository)
        self.scenario_auto_test_service = ScenarioAutoTestService(
            scenario_registry=self.scenario_registry,
            execution_probe_service=self.execution_probe_service,
            runtime_tuner=self.runtime_tuner,
            pending_issue_service=self.pending_issue_service,
            scenario_run_repository=self.scenario_run_repository,
            adaptive_session_repository=self.adaptive_session_repository,
            dossier_repository=self.execution_dossier_repository,
            task_outcome_recorder=self.task_outcome_recorder,
        )
        self.unified_memory_layer = UnifiedMemoryLayer(self.knowledge_repository)
        self.task_context_assembler.unified_memory_layer = self.unified_memory_layer
        self.self_teach_orchestrator = SelfTeachOrchestrator(
            adaptive_session_repository=self.adaptive_session_repository,
            pending_issue_repository=self.pending_issue_repository,
            scenario_auto_test_service=self.scenario_auto_test_service,
            scenario_run_repository=self.scenario_run_repository,
            experiment_lab=self.experiment_lab,
            tool_memory=self.tool_memory,
            environment_self_awareness_service=self.environment_self_awareness_service,
        )
        self.autonomous_evolution_service = AutonomousEvolutionService(
            config=self.config,
            tool_teach_service=self.tool_teach_service,
            incident_packet_service=self.incident_packet_service,
            pending_issue_repository=self.pending_issue_repository,
        )

        # --- Task A: backend services para dialogos UI (Task B) ---
        # Los 4 servicios no deciden rutas ni tocan ViewModels; solo median
        # prompts de UI, respuestas, instalaciones y salud de proveedores.
        self.credential_broker = CredentialBroker(secret_vault=self.secret_vault)
        self.clarification_request_service = ClarificationRequestService()
        self.environment_bootstrap_service = EnvironmentBootstrapService()
        self.provider_health_router = ProviderHealthRouter(
            probes=default_local_probes(
                ollama_base_url=self.config.ollama_base_url,
                embeddings_base_url=self.config.ollama_base_url,
                external_assistant_urls=getattr(self.config, 'external_assistant_urls', None) or {},
            )
        )
        # Inyectar en los servicios que los consumen (sin modificar sus ctors):
        # solo se adjuntan como atributos opcionales a disposicion de cada servicio.
        self.autonomous_evolution_service.credential_broker = self.credential_broker
        self.autonomous_evolution_service.clarification_request_service = self.clarification_request_service
        self.autonomous_evolution_service.environment_bootstrap_service = self.environment_bootstrap_service
        self.autonomous_evolution_service.provider_health_router = self.provider_health_router
        self.browser_teach_session_service.credential_broker = self.credential_broker
        self.browser_teach_session_service.clarification_request_service = self.clarification_request_service
        self.operational_executor.credential_broker = self.credential_broker
        self.operational_executor.clarification_request_service = self.clarification_request_service
        self.operational_executor.environment_bootstrap_service = self.environment_bootstrap_service
        # Inyectar credential_broker en adapters que pueden requerir login
        # externo (ChatGPT, Claude, Gemini, etc.). El adapter dispara el
        # popup de credenciales cuando la sesion aislada reporta
        # assistant_login_required, sin decidir rutas.
        external_adapter = self.tool_adapters.get('external_assistant')
        if external_adapter is not None:
            external_adapter.credential_broker = self.credential_broker

        self.knowledge_service = KnowledgeService(self.knowledge_repository, unified_memory_layer=self.unified_memory_layer)
        self.adaptive_task_orchestrator = AdaptiveTaskOrchestrator(
            role_router=self.role_router,
            adaptive_session_repository=self.adaptive_session_repository,
            intent_service=self.intent_understanding_service,
            context_assembler=self.task_context_assembler,
            capability_service=self.capability_readiness_service,
            strategy_pack_registry=self.strategy_pack_registry,
            planner_service=self.adaptive_planner_service,
            approval_gate_service=self.approval_gate_service,
            execution_playbook_service=self.execution_playbook_service,
            task_outcome_recorder=self.task_outcome_recorder,
            autonomous_evolution_service=self.autonomous_evolution_service,
            unified_memory_layer=self.unified_memory_layer,
            goal_engine=self.goal_engine,
            autonomy_governance_policy=self.autonomy_governance_policy,
            synaptic_router=self.synaptic_router,
        )
        self.portable_context_service.task_context_assembler = self.task_context_assembler
        self.portable_context_service.adaptive_task_orchestrator = self.adaptive_task_orchestrator
        self.api_key_discovery_service = ApiKeyDiscoveryService(data_root=self.config.data_dir)
        self.decision_audit_trail = DecisionAuditTrail(data_root=self.config.data_dir)
        self.operational_self_examination_service.decision_audit_trail = self.decision_audit_trail
        self.portable_context_service.decision_audit_trail = self.decision_audit_trail
        self.autonomous_validation_cycle.decision_audit_trail = self.decision_audit_trail
        self.autonomous_validation_cycle.api_key_discovery_service = self.api_key_discovery_service
        self.adaptive_model_selector = AdaptiveModelSelector(data_dir=self.config.data_dir)
        CloudReasoningPlannerService._model_selector = self.adaptive_model_selector
        self.adaptive_task_orchestrator.cloud_reasoning_planner = CloudReasoningPlannerService()
        self.operational_self_examination_service.adaptive_model_selector = self.adaptive_model_selector
        self.adaptive_task_orchestrator.api_key_discovery_service = self.api_key_discovery_service
        self.adaptive_task_orchestrator.decision_audit_trail = self.decision_audit_trail
        self.adaptive_task_orchestrator.control_master_service = self.control_master_service
        self.adaptive_task_orchestrator.control_master_digest_builder = self.control_master_digest_builder
        self.adaptive_task_orchestrator.self_examination_service = self.operational_self_examination_service
        self.adaptive_task_orchestrator.validation_cycle_service = self.autonomous_validation_cycle
        self.autonomous_validation_cycle.git_sync_service = self.git_sync_service
        # G1: wire orchestrator into validation cycle for proactive auto-execution
        self.autonomous_validation_cycle.adaptive_task_orchestrator = self.adaptive_task_orchestrator
        self.adaptive_task_orchestrator._tool_teach_service = self.tool_teach_service
        self.adaptive_task_orchestrator._tool_operational_executor = self.operational_executor
        self._seed_control_master_from_agents_md()

        # --- Evolution services: DecisionSimplifier + PlatformLearning + Metacognition ---
        try:
            self.decision_simplifier = DecisionSimplifierEngine(data_root=self.config.data_dir)
            self.decision_simplifier.world_model_service = self.world_model_service
            self.decision_simplifier.tool_registry = self.tool_registry
            self.decision_simplifier.api_key_discovery = self.api_key_discovery_service
            self.decision_simplifier.auto_correction_engine = getattr(self, 'auto_correction_engine', None)
        except Exception as exc:
            logger.warning('bootstrap: DecisionSimplifierEngine init failed: %s', exc)
            self.decision_simplifier = None

        try:
            self.platform_learning = PlatformLearningOrchestrator(data_root=self.config.data_dir)
            self.platform_learning.browser_teach = self.browser_teach_session_service
            self.platform_learning.site_exploration = self.site_exploration_service
            self.platform_learning.universal_perception = self.universal_perception_service
            self.platform_learning.replay_confidence = self.replay_confidence_service
            self.platform_learning.decision_simplifier = self.decision_simplifier
            self.platform_learning.api_key_discovery = self.api_key_discovery_service
        except Exception as exc:
            logger.warning('bootstrap: PlatformLearningOrchestrator init failed: %s', exc)
            self.platform_learning = None

        try:
            self.metacognition_evolution = MetacognitionEvolutionMixin()
            self.metacognition_evolution.decision_simplifier = self.decision_simplifier
            self.metacognition_evolution.platform_learning = self.platform_learning
            self.metacognition_evolution.api_key_discovery = self.api_key_discovery_service
            self.metacognition_evolution.auto_correction_engine = getattr(self, 'auto_correction_engine', None)
        except Exception as exc:
            logger.warning('bootstrap: MetacognitionEvolutionMixin init failed: %s', exc)
            self.metacognition_evolution = None

        # Wire metacognition into OSES so build_review() picks up evolution findings
        if self.metacognition_evolution is not None:
            self.operational_self_examination_service.metacognition_evolution = self.metacognition_evolution

        self.inference_service = InferenceService(
            self.role_router,
            self.run_repository,
            self.execution_dossier_service,
            adaptive_orchestrator=self.adaptive_task_orchestrator,
            knowledge_service=self.knowledge_service,
        )
        self.training_orchestrator = TrainingOrchestrator(
            workspace_root=self.config.workspace_root,
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            archive_service=self.payload_archive_service,
            artifact_repository=self.session_artifact_repository,
        )

        self.navigation_controller = None
        self.theme_controller = None
        self.main_window_bridge = None
        self.dashboard_viewmodel = None
        self.control_center_viewmodel = None
        self.capture_studio_viewmodel = None
        self.evolution_center_viewmodel = None
        self.knowledge_base_viewmodel = None
        self.provider_settings_viewmodel = None
        self.run_history_viewmodel = None

    _TOOL_INSTALL_GUIDANCE: dict[str, str] = {
        'aider_coder': 'pip install aider-chat (optional, heavy ~200MB; installed in background)',
        'claude_installed': 'Descargar Claude Desktop desde https://claude.ai/download',
        'mcp_client': 'Iniciar MCP server (default: http://127.0.0.1:8000) o ajustar server_url en metadata',
    }

    def _log_tool_availability(self) -> None:
        """Log de arranque: muestra que herramientas estan conectadas.

        Ademas, estampa ``last_validated_at_utc`` en las tools que pasan
        el probe de startup para que la confianza base suba por encima
        del minimo (0.26).  Solo toca cards cuyo campo era ``None``.
        Diagnostica por que cada tool faltante no esta disponible.

        Los probes de disponibilidad se ejecutan en paralelo usando un
        ``ThreadPoolExecutor`` para reducir el tiempo de arranque cuando
        hay adapters que hacen I/O de red (Ollama, Devin API, GitHub API)
        o enumeracion de procesos (ExternalAssistantToolAdapter).

        In the MCP subprocess the main UI process already did this work;
        repeating it just adds duplicate logs and redundant API calls.
        """
        if os.environ.get('IABV_MCP_SUBPROCESS') == '1':
            logger.debug('tool_availability: skipped (MCP subprocess)')
            return
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime, timezone

        cards = self.tool_registry.list_cards()
        if not cards:
            logger.info('tool_availability: sin tools registradas')

        def _run_gpu_startup_health_check() -> None:
            try:
                from iabv_v15.services.gpu_metacognition import startup_gpu_health_check
                _gpu_report = startup_gpu_health_check()
                _gpu_issues = _gpu_report.get('issues', [])
                if _gpu_issues:
                    for _issue in _gpu_issues:
                        logger.warning('gpu_startup_issue: %s', _issue)
                else:
                    logger.info('gpu_startup: healthy (%d GPU(s) detected)',
                                _gpu_report.get('nvidia_count', 0) + _gpu_report.get('intel_igpu_count', 0))
            except Exception as _gpu_exc:
                logger.warning('gpu_startup_check failed: %s', _gpu_exc)

        threading.Thread(
            target=_run_gpu_startup_health_check,
            name='iabv-gpu-startup-health',
            daemon=True,
        ).start()

        # --- Parallel tool availability probes ---
        # Group cards by adapter_key so that cards sharing the same adapter
        # (e.g. multiple ExternalAssistant cards) run sequentially within
        # their group but different adapter groups run in parallel.  This
        # avoids concurrent mutation of per-adapter state while still
        # parallelising the expensive I/O (HTTP pings, process enumeration).
        from collections import defaultdict
        adapter_groups: dict[str, list] = defaultdict(list)
        for card in cards:
            adapter_groups[card.adapter_key].append(card)

        results: dict[str, bool] = {}
        refreshed_cards: dict[str, Any] = {}

        def _probe_group(group_cards: list) -> list[tuple[str, bool, Any]]:
            out: list[tuple[str, bool, Any]] = []
            for c in group_cards:
                refreshed = self.tool_registry.refresh_card(
                    c, max_age_seconds=60.0,
                )
                out.append((refreshed.tool_id, refreshed.available, refreshed))
            return out

        max_workers = min(len(adapter_groups), 8) or 1
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='iabv-tool-probe') as pool:
            futures = {
                pool.submit(_probe_group, group_cards): adapter_key
                for adapter_key, group_cards in adapter_groups.items()
            }
            for future in as_completed(futures):
                try:
                    for tool_id, available, refreshed in future.result():
                        results[tool_id] = available
                        refreshed_cards[tool_id] = refreshed
                except Exception as exc:
                    adapter_key = futures[future]
                    logger.warning('tool_probe failed for adapter %s: %s', adapter_key, exc)

        ready = []
        missing = []
        now = datetime.now(timezone.utc)
        for card in cards:
            available = results.get(card.tool_id, False)
            refreshed = refreshed_cards.get(card.tool_id, card)
            if available:
                ready.append(card.tool_id)
                if refreshed.last_validated_at_utc is None:
                    stamped = refreshed.model_copy(
                        update={'last_validated_at_utc': now},
                    )
                    self.tool_registry.repository.save_card(stamped)
            else:
                missing.append(card.tool_id)
                guidance = self._TOOL_INSTALL_GUIDANCE.get(card.tool_id, '')
                logger.info(
                    'tool_missing: %s — adapter=%s%s',
                    card.tool_id,
                    refreshed.adapter_key if hasattr(refreshed, 'adapter_key') else card.adapter_key,
                    f' | fix: {guidance}' if guidance else '',
                )
        logger.info(
            'tool_availability: %d/%d listas — ready=[%s]%s',
            len(ready),
            len(cards),
            ', '.join(sorted(ready)),
            f' | missing=[{", ".join(sorted(missing))}]' if missing else '',
        )

        # Auto-install missing pip-installable tools (AGENTS.md: user
        # should never install tools manually).
        if missing:
            try:
                from iabv_v15.services.auto_correction_engine import auto_fix_missing_tools
                install_result = auto_fix_missing_tools(missing)
                installed_count = install_result.get('installed', 0)
                if installed_count:
                    logger.info(
                        'auto_install: %d/%d tools installed automatically',
                        installed_count, len(missing),
                    )
                    # Re-check availability for installed tools
                    for r in install_result.get('results', []):
                        if r.get('status') == 'installed':
                            tid = r.get('tool_id', '')
                            if tid in missing:
                                missing.remove(tid)
                                ready.append(tid)
            except Exception as exc:
                logger.debug('auto_install: failed — %s', exc)

        self._startup_self_examination()

    def _startup_self_examination(self) -> None:
        """Run a lightweight self-examination at startup.

        Executes the perception cross-validator (if wired) to detect
        UI anomalies (zombie windows, missing IABV window, duplicates)
        and logs the results. This gives the program self-awareness
        about its own state immediately after boot.
        """
        if os.environ.get('IABV_MCP_SUBPROCESS') == '1':
            return
        validator = getattr(self, 'perception_cross_validator', None)
        if validator is None:
            return
        try:
            result = validator.run_cross_validation()
            n_issues = result.get('total_inconsistencies', 0)
            checks = result.get('checks_passed', [])
            ui_issues = [
                i for i in result.get('inconsistencies', [])
                if i.get('check') == 'ui_self_awareness'
            ]
            if ui_issues:
                for issue in ui_issues:
                    logger.warning(
                        'startup_ui_issue: %s — %s',
                        issue.get('actual', ''),
                        issue.get('detail', ''),
                    )
            if n_issues == 0:
                logger.info(
                    'startup_self_check: %d/%d checks passed — all consistent',
                    len(checks),
                    result.get('total_checks', 0),
                )
            else:
                logger.warning(
                    'startup_self_check: %d inconsistencies found (%d/%d passed)',
                    n_issues,
                    len(checks),
                    result.get('total_checks', 0),
                )
        except Exception as exc:
            logger.debug('startup_self_check: skipped (%s)', exc)

    def _ensure_directories(self) -> None:
        for path in (
            self.config.data_dir,
            self.config.episodes_dir,
            self.config.screenshots_dir,
            self.config.browser_profiles_dir,
            self.config.replay_annotations_dir,
            self.config.tool_teaching_dir,
            self.config.browser_states_dir,
            self.config.browser_artifacts_dir,
            self.config.site_policies_dir,
            self.config.payloads_dir,
            self.config.models_dir,
            self.config.logs_dir,
            self.config.evolution_dir,
            str(Path(self.config.workspace_root) / 'assets'),
            str(Path(self.config.workspace_root) / 'docs'),
        ):
            Path(path).mkdir(parents=True, exist_ok=True)

    def _build_ui_objects(self) -> None:
        if self.navigation_controller is not None:
            return
        if PYSIDE_AVAILABLE and QGuiApplication.instance() is None:
            self._ui_app = QGuiApplication(sys.argv)
        self.navigation_controller = NavigationController()
        self.theme_controller = ThemeController(self.theme)
        self.main_window_bridge = MainWindowBridge(self.config.app_name, self.config.workspace_root)
        self.dashboard_viewmodel = DashboardViewModel(
            self.episode_repository,
            self.knowledge_repository,
            self.run_repository,
            self.role_router,
            self.embedding_service,
        )
        # --- MCP bridge (Capa 1): expone el programa a agentes externos
        # (Devin/Claude/Codex) via MCP sobre un tunnel local. El service lee
        # su preferencia persistida y, si estaba habilitado, se auto-arranca.
        # Si governance lo bloquea, queda en state=failed sin crashear.
        if getattr(self, 'mcp_bridge_service', None) is None:
            try:
                self.mcp_bridge_service = build_mcp_bridge_service(
                    self,
                    workspace_root=self.config.workspace_root,
                )
            except Exception:
                logger.exception('No se pudo inicializar MCPBridgeService; bridge desactivado')
                self.mcp_bridge_service = None
            else:
                # `ensure_started()` espera hasta DEFAULT_TUNNEL_TIMEOUT_S a que
                # cloudflared publique la URL. Corriendo en el hilo del arranque
                # freezearia el splash/UI hasta 30 s. Lo disparamos a un daemon
                # thread: el service publica transiciones vía listener y el
                # ViewModel refleja el estado apenas cambie.
                bridge_ref = self.mcp_bridge_service

                def _autostart_bridge() -> None:
                    try:
                        bridge_ref.ensure_started()
                    except Exception:
                        logger.exception('Auto-arranque de MCPBridgeService fallo')

                threading.Thread(
                    target=_autostart_bridge,
                    name='mcp-bridge-autostart',
                    daemon=True,
                ).start()

        # --- UIBridgeService: puente IPC entre MCP server y UI PySide6.
        # Permite a agentes externos (via MCP) enviar mensajes al chat,
        # leer respuestas, capturar screenshots y navegar tabs de la UI.
        # El server TCP arranca en un hilo daemon; si falla, queda None.
        if getattr(self, 'ui_bridge_server', None) is None:
            try:
                from iabv_v15.services.ui_bridge_service import (
                    build_ui_bridge_server,
                )
                self.ui_bridge_server = build_ui_bridge_server()
            except Exception:
                logger.exception('No se pudo construir UIBridgeServer; bridge UI desactivado')
                self.ui_bridge_server = None

        # --- UIScreenshotProvider: permite que la tool MCP
        # `capture_ui_screenshot` devuelva bytes reales cuando la UI está
        # corriendo en este proceso (Qt) o cuando hay display server activo
        # (mss). En headless CI / Linux sin display queda `None` y la tool
        # degrada explícito a `ui_not_running`.
        if getattr(self, 'ui_screenshot_provider', None) is None:
            try:
                from iabv_v15.infra.ui import build_ui_screenshot_provider

                self.ui_screenshot_provider = build_ui_screenshot_provider()
            except Exception:
                logger.exception('No se pudo construir ui_screenshot_provider; dejando None')
                self.ui_screenshot_provider = None

        # ChatCapabilityIngestionService: escucha pasiva del chat. Cuando el
        # usuario declara una capacidad (tengo GPU, instale qwen3, cuento con
        # Docker) escribe un entry append-only a
        # data/chat_research_backlog/<session>.jsonl. No decide rutas; solo
        # persiste para que OSES / ExperimentLab lo consuman en capas superiores.
        try:
            from iabv_v15.services.chat.capability_ingestion import (
                ChatCapabilityIngestionService,
            )

            self.chat_capability_ingestion_service = ChatCapabilityIngestionService(
                data_root=self.config.data_dir,
            )
        except Exception:
            logger.exception('No se pudo construir ChatCapabilityIngestionService; dejando None')
            self.chat_capability_ingestion_service = None

        self.control_center_viewmodel = ControlCenterViewModel(
            config=self.config,
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            artifact_repository=self.session_artifact_repository,
            inference_service=self.inference_service,
            role_router=self.role_router,
            adaptive_orchestrator=self.adaptive_task_orchestrator,
            training_orchestrator=self.training_orchestrator,
            pbt_service=self.pbt_control_service,
            development_assist_service=self.development_assist_service,
            engineering_review_service=self.engineering_review_service,
            embedding_service=self.embedding_service,
            navigation_controller=self.navigation_controller,
            self_teach_orchestrator=self.self_teach_orchestrator,
            tool_teach_service=self.tool_teach_service,
            autonomous_evolution_service=self.autonomous_evolution_service,
            evolution_review_service=self.evolution_review_service,
            experiment_lab_repository=self.experiment_lab_repository,
            tool_record_repository=self.tool_record_repository,
            scenario_run_repository=self.scenario_run_repository,
            autonomy_activity_projector=self.autonomy_activity_projector,
            objective_repository=self.objective_repository,
            universal_perception_service=self.universal_perception_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            tool_discovery_service=self.tool_discovery_service,
            self_examination_service=self.operational_self_examination_service,
            mcp_bridge_service=self.mcp_bridge_service,
            control_master_service=self.control_master_service,
            control_master_digest_builder=self.control_master_digest_builder,
            self_audit_service=self.self_audit_service,
            chat_capability_ingestion_service=self.chat_capability_ingestion_service,
        )
        self.capture_studio_viewmodel = CaptureStudioViewModel(
            config=self.config,
            episode_repository=self.episode_repository,
            artifact_repository=self.session_artifact_repository,
            site_policy_registry=self.site_policy_registry,
            profile_manager=self.training_profile_manager,
            secret_vault=self.secret_vault,
            browser_teach_session_service=self.browser_teach_session_service,
            browser_learning_assembler=self.browser_learning_assembler,
            hidden_incident_repository=self.hidden_incident_repository,
            user_clue_repository=self.user_clue_repository,
            runtime_signal_collector=self.runtime_signal_collector,
            hidden_incident_detector=self.hidden_incident_detector,
            session_health_service=self.session_health_service,
            user_clue_service=self.user_clue_service,
            execution_dossier_service=self.execution_dossier_service,
            replay_annotation_service=self.replay_annotation_service,
            replay_visual_assembler=self.replay_visual_assembler,
            replay_learning_feedback_service=self.replay_learning_feedback_service,
            interaction_learning_service=self.interaction_learning_service,
            tool_record_repository=self.tool_record_repository,
            live_audit_supervisor=self.live_audit_supervisor,
            audit_teach_verification_service=self.audit_teach_verification_service,
            universal_perception_service=self.universal_perception_service,
        )
        self.control_center_viewmodel.capture_studio_viewmodel = self.capture_studio_viewmodel

        # Wire UIBridgeServer with the ControlCenterViewModel so that
        # MCP agents can interact with the UI chat. The server starts
        # in a daemon thread; if it fails, IABV continues without it.
        if getattr(self, 'ui_bridge_server', None) is not None:
            try:
                from iabv_v15.services.ui_bridge_service import build_ui_bridge_server
                self.ui_bridge_server = build_ui_bridge_server(
                    control_center_viewmodel=self.control_center_viewmodel,
                )
                self.ui_bridge_server.start()
                logger.info('UIBridgeServer started with ControlCenterViewModel')
            except Exception:
                logger.exception('UIBridgeServer failed to start with VM wiring')
                self.ui_bridge_server = None

        # Deferred: refreshAutonomyDock runs inside the VM's deferred
        # startup thread to avoid blocking UI creation.
        self.evolution_center_viewmodel = EvolutionCenterViewModel(
            dossier_repository=self.execution_dossier_repository,
            hidden_incident_repository=self.hidden_incident_repository,
            evolution_review_service=self.evolution_review_service,
            incident_packet_service=self.incident_packet_service,
            self_check_orchestrator=self.self_check_orchestrator,
            pending_issue_repository=self.pending_issue_repository,
            scenario_run_repository=self.scenario_run_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            tool_record_repository=self.tool_record_repository,
            tool_teach_service=self.tool_teach_service,
            environment_self_awareness_service=self.environment_self_awareness_service,
            world_model_service=self.world_model_service,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            portable_context_service=self.portable_context_service,
            self_examination_service=self.operational_self_examination_service,
            control_master_service=self.control_master_service,
            control_master_digest_builder=self.control_master_digest_builder,
            github_remote_service=self.github_remote_service,
        )
        # Hook proactivo: el EvolutionCenter puede consultar el dashboard
        # para mostrar "que necesita del humano" al arrancar, sin romper
        # el contrato del ViewModel (attribute set, no constructor arg).
        self.evolution_center_viewmodel.proactive_dashboard_service = self.proactive_dashboard_service
        self.evolution_center_viewmodel.human_approval_broker = self.human_approval_broker
        self.evolution_center_viewmodel.approval_memory = self.approval_memory
        # F1.1: el VM expone snapshots recientes como Property; el servicio
        # persiste a disco y el VM solo lee la foto (AGENTS.md: el VM no
        # decide rutas ni inventa datos).
        self.evolution_center_viewmodel.ui_screenshot_service = self.ui_screenshot_service
        self.knowledge_base_viewmodel = KnowledgeBaseViewModel(self.knowledge_repository)
        self.provider_settings_viewmodel = ProviderSettingsViewModel(self.provider_configs, self.role_router, self.embedding_service)
        self.run_history_viewmodel = RunHistoryViewModel(self.run_repository, self.execution_dossier_repository)
        self.centro_vivo_viewmodel = CentroVivoViewModel(
            adaptive_session_repository=self.adaptive_session_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            tool_record_repository=self.tool_record_repository,
            world_model_service=self.world_model_service,
            self_examination_service=self.operational_self_examination_service,
            portable_context_service=self.portable_context_service,
            evolution_review_service=self.evolution_review_service,
            data_root=self.config.data_dir,
        )

        # --- Task A: conectar handlers de backend a senales de ambos ViewModels ---
        # Los servicios backend emiten via handler registrado; el handler reemite por
        # la Qt Signal del ControlCenterViewModel y EvolutionCenterViewModel para que
        # los dialogos QML (Task B) los reciban.
        self._wire_task_a_signals()

        for service_name in ('autonomous_validation_cycle', 'world_model_service', 'environment_self_awareness_service'):
            service = getattr(self, service_name, None)
            if service is None or not hasattr(service, 'stop'):
                continue
            try:
                service.stop(timeout_seconds=2.0)
            except TypeError:
                service.stop()

    def _wire_task_a_signals(self) -> None:
        """Conecta handlers de los 4 servicios backend (Task A) a ambos ViewModels.

        Cada handler re-emite el payload como Qt Signal de ControlCenter y
        EvolutionCenter, para que los dialogos/paneles QML de Task B los
        reciban sin acoplar el backend a Qt ni a los ViewModels.
        """
        view_models = [vm for vm in (self.control_center_viewmodel, self.evolution_center_viewmodel) if vm is not None]
        if not view_models:
            return

        def _emit(signal_name: str, payload):
            for vm in view_models:
                signal = getattr(vm, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.emit(payload)
                except Exception:
                    # Evitamos que un fallo en un sink UI bloquee el resto.
                    continue

        self.credential_broker.register_prompt_handler(
            lambda payload: _emit('credentialPromptRequested', payload)
        )
        self.clarification_request_service.register_prompt_handler(
            lambda payload: _emit('clarificationRequested', payload)
        )
        self.environment_bootstrap_service.register_prompt_handler(
            lambda payload: _emit('missingDependencyRequested', payload)
        )
        self.environment_bootstrap_service.register_activity_handler(
            lambda payload: _emit('backgroundActivityChanged', payload)
        )
        self.provider_health_router.register_health_listener(
            lambda payload: _emit('providerHealthChanged', payload)
        )

    def shutdown(self) -> None:
        router = getattr(self, 'provider_health_router', None)
        if router is not None:
            try:
                router.stop_polling(timeout_s=2.0)
            except Exception:
                pass
        bridge = getattr(self, 'mcp_bridge_service', None)
        if bridge is not None:
            try:
                bridge.shutdown()
            except Exception:
                logger.exception('Error al cerrar MCPBridgeService')
        ui_bridge = getattr(self, 'ui_bridge_server', None)
        if ui_bridge is not None:
            try:
                ui_bridge.stop()
            except Exception:
                logger.exception('Error al cerrar UIBridgeServer')
        self.stop()

    def export_portable_context(self, *, refresh: bool = True) -> dict[str, object]:
        if self.portable_context_service is None:
            return {}
        package = self.portable_context_service.current_package(refresh=refresh)
        return package.model_dump(mode='json')

    def export_control_master_digest(self, *, refresh: bool = False) -> dict[str, object]:
        service = getattr(self, 'control_master_service', None)
        builder = getattr(self, 'control_master_digest_builder', None)
        if service is None or builder is None:
            return {}
        state = service.current_state(refresh=refresh)
        return builder.build(state).model_dump(mode='json')

    def _seed_control_master_from_agents_md(self) -> None:
        service = getattr(self, 'control_master_service', None)
        if service is None:
            return
        workspace_root = Path(getattr(self.config, 'workspace_root', '.'))
        candidates = [
            workspace_root / 'AGENTS.md',
            workspace_root.parent / 'AGENTS.md',
            Path.cwd() / 'AGENTS.md',
        ]
        for candidate in candidates:
            try:
                if candidate.is_file():
                    service.seed_from_agents_md(candidate)
                    return
            except Exception:
                continue

    def create_engine(self):
        if not PYSIDE_AVAILABLE:
            raise RuntimeError('PySide6 is required to run the desktop UI.')

        # Ensure PySide6's QML plugins are discoverable.  Conda/miniconda
        # installs may place them in a non-default path, causing
        # "qtquick2plugin not found" at engine load time.
        try:
            import PySide6
            pyside_dir = Path(PySide6.__file__).resolve().parent
            qml_dir = pyside_dir / 'qml'
            plugin_dir = pyside_dir / 'plugins'
            if qml_dir.is_dir():
                os.environ.setdefault('QML2_IMPORT_PATH', str(qml_dir))
            if plugin_dir.is_dir():
                os.environ.setdefault('QT_PLUGIN_PATH', str(plugin_dir))
        except Exception:
            pass

        os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
        QQuickStyle.setStyle('Basic')
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        self._build_ui_objects()

        engine = QQmlApplicationEngine()
        context = engine.rootContext()
        context.setContextProperty('navigationController', self.navigation_controller)
        context.setContextProperty('themeController', self.theme_controller)
        context.setContextProperty('mainWindowBridge', self.main_window_bridge)
        context.setContextProperty('dashboardViewModel', self.dashboard_viewmodel)
        context.setContextProperty('controlCenterViewModel', self.control_center_viewmodel)
        context.setContextProperty('captureStudioViewModel', self.capture_studio_viewmodel)
        context.setContextProperty('evolutionCenterViewModel', self.evolution_center_viewmodel)
        context.setContextProperty('knowledgeBaseViewModel', self.knowledge_base_viewmodel)
        context.setContextProperty('providerSettingsViewModel', self.provider_settings_viewmodel)
        context.setContextProperty('runHistoryViewModel', self.run_history_viewmodel)
        context.setContextProperty('centroVivoViewModel', self.centro_vivo_viewmodel)

        main_qml = Path(__file__).resolve().parent / 'ui' / 'qml' / 'Main.qml'
        engine.load(QUrl.fromLocalFile(str(main_qml)))
        if not engine.rootObjects():
            raise RuntimeError('Failed to load Main.qml.')
        return app, engine

    # ------------------------------------------------------------------
    # Integrated MCP server + Cloudflare tunnel auto-start
    # ------------------------------------------------------------------
    # When the user launches ``python -m iabv_v15``, the full stack must
    # come alive autonomously: secrets, MCP server, tunnel (if internet
    # is available), and the PySide6 UI — all from a single invocation.
    # The MCP server and tunnel run as daemon subprocesses so they die
    # automatically when the UI (main process) exits.
    # ------------------------------------------------------------------

    def _start_mcp_subprocess(self) -> 'subprocess.Popen[bytes] | None':
        """Launch the MCP server as a background subprocess."""
        import shutil
        import subprocess

        python_exe = sys.executable
        workspace = str(self.config.workspace_root)
        src_dir = str(Path(workspace) / 'src')

        env = {**os.environ}
        if 'PYTHONPATH' not in env or src_dir not in env.get('PYTHONPATH', ''):
            env['PYTHONPATH'] = src_dir + os.pathsep + env.get('PYTHONPATH', '')
        env.setdefault('IABV_MCP_TRANSPORT', 'streamable-http')
        env.setdefault('IABV_MCP_NAME', 'iabv-v15')
        env.setdefault('FASTMCP_HOST', '127.0.0.1')
        env.setdefault('FASTMCP_PORT', '8000')
        env['IABV_WORKSPACE_ROOT'] = workspace
        # Signal that this bootstrap runs inside the MCP subprocess so it
        # can reduce redundant scans and log noise.
        env['IABV_MCP_SUBPROCESS'] = '1'

        # Inject portable CLI tools into PATH (same as run_mcp_bridge.ps1)
        iabv_tools = Path.home() / '.iabv' / 'tools'
        if iabv_tools.is_dir():
            extra_paths = []
            for candidate in ['gh/bin', 'cloudflared']:
                p = iabv_tools / candidate
                if p.is_dir():
                    extra_paths.append(str(p))
            if extra_paths:
                env['PATH'] = os.pathsep.join(extra_paths) + os.pathsep + env.get('PATH', '')

        try:
            proc = subprocess.Popen(
                [python_exe, '-m', 'iabv_v15.infra.mcp.server'],
                cwd=workspace,
                env=env,
                stdout=None,
                stderr=None,
            )
            logger.info('mcp_autostart: MCP server launched (PID %d)', proc.pid)
            return proc
        except Exception as exc:
            logger.warning('mcp_autostart: failed to launch MCP server: %s', exc)
            return None

    def _start_tunnel_subprocess(self) -> 'subprocess.Popen[bytes] | None':
        """Launch Cloudflare tunnel as a background subprocess if available."""
        import shutil
        import subprocess

        cloudflared = shutil.which('cloudflared')
        if not cloudflared:
            # Check portable install
            portable = Path.home() / '.iabv' / 'tools' / 'cloudflared'
            if portable.is_dir():
                for name in ('cloudflared.exe', 'cloudflared'):
                    candidate = portable / name
                    if candidate.is_file():
                        cloudflared = str(candidate)
                        break
        if not cloudflared:
            logger.info('mcp_autostart: cloudflared not found, skipping tunnel')
            return None

        bind_host = os.environ.get('FASTMCP_HOST', '127.0.0.1')
        bind_port = os.environ.get('FASTMCP_PORT', '8000')
        origin = f'http://{bind_host}:{bind_port}'
        host_header = f'{bind_host}:{bind_port}'

        try:
            proc = subprocess.Popen(
                [
                    cloudflared, 'tunnel',
                    '--url', origin,
                    '--no-autoupdate',
                    '--loglevel', 'info',
                    '--http-host-header', host_header,
                ],
                stdout=None,
                stderr=None,
            )
            logger.info('mcp_autostart: Cloudflare tunnel launched (PID %d)', proc.pid)
            return proc
        except Exception as exc:
            logger.warning('mcp_autostart: failed to launch tunnel: %s', exc)
            return None

    def _auto_optimize_brain(self) -> None:
        """Auto-optimize the reasoning brain on startup.

        Tests each configured cloud provider with a quick inference call
        and records latency to ``AdaptiveModelSelector`` so the best
        provider is always used for reasoning tasks.

        This runs in background — no UI blocking.  Only providers with
        configured API keys are tested.
        """
        selector = getattr(self, 'adaptive_model_selector', None)
        api_discovery = getattr(self, 'api_key_discovery_service', None)
        if selector is None:
            return

        logger.info('startup_evolution: optimizing brain — benchmarking configured providers')

        providers_to_test: list[tuple[str, str, str, str]] = [
            # (provider_id, env_var, url, model)
            ('groq', 'GROQ_API_KEY', 'https://api.groq.com/openai/v1/chat/completions', 'llama-3.3-70b-versatile'),
            ('gemini', 'GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'gemini-2.0-flash'),
            ('openrouter', 'OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/chat/completions', 'meta-llama/llama-3.3-70b-instruct:free'),
        ]

        test_prompt = [
            {'role': 'system', 'content': 'Respond in one sentence.'},
            {'role': 'user', 'content': 'What is 2+2?'},
        ]

        try:
            import httpx
        except ImportError:
            logger.debug('startup_evolution: httpx not available, skipping brain benchmark')
            return

        import time as _time

        for provider_id, env_var, url, model in providers_to_test:
            key = os.environ.get(env_var)
            if not key:
                continue
            try:
                headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
                body = {
                    'model': model,
                    'messages': test_prompt,
                    'max_tokens': 20,
                    'temperature': 0.0,
                }
                t0 = _time.monotonic()
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, json=body)
                latency_ms = (_time.monotonic() - t0) * 1000
                success = 200 <= resp.status_code < 400

                selector.record_result(
                    provider_id=provider_id,
                    task_type='reasoning',
                    latency_ms=latency_ms,
                    success=success,
                )
                logger.info(
                    'startup_evolution: brain benchmark %s — %s, %.0fms',
                    provider_id, 'OK' if success else f'HTTP {resp.status_code}', latency_ms,
                )
            except Exception as exc:
                logger.debug('startup_evolution: brain benchmark %s failed: %s', provider_id, exc)
                selector.record_result(
                    provider_id=provider_id,
                    task_type='reasoning',
                    latency_ms=10000.0,
                    success=False,
                )

        # Log the current best provider
        try:
            best = selector.select_best_provider(task_type='reasoning')
            logger.info(
                'startup_evolution: best reasoning provider = %s (%s)',
                best.get('provider_id', '?'), best.get('reason', '?'),
            )
        except Exception:
            pass

    def _schedule_startup_evolution(self) -> None:
        """Run evolution cycle in background after startup.

        Discovers providers, benchmarks them, runs metacognition findings,
        and logs results.  Does NOT block the UI — runs in a daemon thread
        after a 5-second delay to let the UI load first.
        """
        metacog = getattr(self, 'metacognition_evolution', None)
        api_discovery = getattr(self, 'api_key_discovery_service', None)
        if metacog is None and api_discovery is None:
            return

        def _run_startup_cycle() -> None:
            import time
            time.sleep(5)  # Let UI load first
            logger.info('startup_evolution: beginning background cycle')
            try:
                # Step 1: Scan configured API keys
                if api_discovery is not None:
                    try:
                        scan = api_discovery.scan_configured_keys()
                        configured = [s['provider_id'] for s in scan if s.get('configured')]
                        missing = [s['provider_id'] for s in scan if not s.get('configured')]
                        logger.info(
                            'startup_evolution: API keys — configured=%s, missing=%s',
                            configured or 'none', missing or 'none',
                        )
                    except Exception as exc:
                        logger.warning('startup_evolution: API key scan failed: %s', exc)

                # Step 2: Run metacognition evolution cycle
                if metacog is not None:
                    try:
                        result = metacog.run_evolution_cycle()
                        logger.info(
                            'startup_evolution: metacognition — %d findings, %d actions',
                            result.get('findings_count', 0),
                            len(result.get('actions_taken', [])),
                        )
                        for action in result.get('actions_taken', []):
                            logger.info('startup_evolution: action — %s', action)
                    except Exception as exc:
                        logger.warning('startup_evolution: metacognition cycle failed: %s', exc)

                # Step 3: Optimize brain — benchmark providers for best reasoning
                self._auto_optimize_brain()

                logger.info('startup_evolution: background cycle complete')
            except Exception as exc:
                logger.warning('startup_evolution: unexpected error: %s', exc)

        threading.Thread(
            target=_run_startup_cycle,
            name='startup-evolution',
            daemon=True,
        ).start()

    def _is_mcp_port_in_use(self, port: int = 8000) -> bool:
        """Check if the MCP port is already in use (another instance running)."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def run(self) -> int:
        # Holder for subprocesses; written from background thread.
        self._mcp_proc = None
        self._tunnel_proc = None
        try:
            # When launched via start_iabv.ps1 -StartUI, the script manages
            # MCP + tunnel externally.  Skip autostart to avoid port conflict.
            skip_mcp = os.environ.get('IABV_SKIP_MCP_AUTOSTART', '') == '1'
            mcp_port = int(os.environ.get('FASTMCP_PORT', '8000'))
            if skip_mcp:
                logger.info('mcp_autostart: skipped (IABV_SKIP_MCP_AUTOSTART=1)')
            elif not self._is_mcp_port_in_use(mcp_port):
                # Launch MCP + tunnel in background so the UI doesn't freeze
                # waiting for the 2-second MCP warm-up.
                def _deferred_mcp_start() -> None:
                    self._mcp_proc = self._start_mcp_subprocess()
                    if self._mcp_proc:
                        import time
                        time.sleep(2)
                        self._tunnel_proc = self._start_tunnel_subprocess()
                threading.Thread(
                    target=_deferred_mcp_start,
                    name='mcp-deferred-start',
                    daemon=True,
                ).start()
            else:
                logger.info('mcp_autostart: port %d already in use, skipping MCP launch', mcp_port)

            # --- Startup evolution: background cycle after services are ready ---
            self._schedule_startup_evolution()

            app, _engine = self.create_engine()
            return app.exec()
        finally:
            for proc in (self._tunnel_proc, self._mcp_proc):
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass





