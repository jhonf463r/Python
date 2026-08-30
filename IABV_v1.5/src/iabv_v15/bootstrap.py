from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
import sys


def _rss_mb() -> float:
    """Return current RSS in MB. Returns 0.0 on error."""
    try:
        import psutil  # type: ignore[import-not-found]
        return float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        pass
    try:
        import resource
        # ru_maxrss is in KB on Linux, bytes on macOS
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == 'darwin':
            return raw / (1024.0 * 1024.0)
        return raw / 1024.0
    except Exception:
        return 0.0

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
from iabv_v15.infra.persistence.chat_message_repository import ChatMessageRepository
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
from iabv_v15.services.evolution.resource_metacognition_service import ResourceMetacognitionService
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
from iabv_v15.services.evolution.code_audit_trail import CodeAuditTrail
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
from iabv_v15.services.providers.ollama_expert_provider import OllamaExpertProvider
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.account_resource_scanner import estimate_available_workers, build_inventory_snapshot
from iabv_v15.services.account_approval_ledger import AccountApprovalLedger
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.payload_archive_service import PayloadArchiveService
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.training.training_orchestrator import TrainingOrchestrator
from iabv_v15.ui.controllers.main_window_bridge import MainWindowBridge
from iabv_v15.ui.controllers.navigation_controller import NavigationController
from iabv_v15.ui.controllers.theme_controller import ThemeController
from iabv_v15.ui.qt import PYSIDE_AVAILABLE, QApplication, QGuiApplication, QQmlApplicationEngine, QQuickStyle, QTimer, QUrl
from iabv_v15.ui.splash_controller import SplashController
from iabv_v15.infra.startup_timeline import (
    configure_global_timeline,
    get_global_timeline,
)
from iabv_v15.ui.viewmodels.capture_studio_viewmodel import CaptureStudioViewModel
from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
from iabv_v15.ui.viewmodels.dashboard_viewmodel import DashboardViewModel
from iabv_v15.ui.viewmodels.evolution_center_viewmodel import EvolutionCenterViewModel
from iabv_v15.ui.viewmodels.knowledge_base_viewmodel import KnowledgeBaseViewModel
from iabv_v15.ui.viewmodels.provider_settings_viewmodel import ProviderSettingsViewModel
from iabv_v15.ui.viewmodels.centro_vivo_viewmodel import CentroVivoViewModel
from iabv_v15.ui.viewmodels.run_history_viewmodel import RunHistoryViewModel


class _LazyServiceRef:
    """Transparent proxy that defers service construction until first use.

    Wraps a zero-arg callable; attribute access on the proxy triggers the
    callable, caches the result, and forwards the lookup to the real
    service.  This lets ``_wire_services`` pass a lazy reference to
    adapters / consumers that store a service ref but only call methods
    on it at runtime (e.g. ``SiteExplorerToolAdapter.run``).
    """
    __slots__ = ('_factory', '_instance')

    def __init__(self, factory):
        object.__setattr__(self, '_factory', factory)
        object.__setattr__(self, '_instance', None)

    def _resolve(self):
        inst = object.__getattribute__(self, '_instance')
        if inst is None:
            inst = object.__getattribute__(self, '_factory')()
            object.__setattr__(self, '_instance', inst)
        return inst

    def __getattr__(self, name):
        return getattr(self._resolve(), name)

    def __setattr__(self, name, value):
        setattr(self._resolve(), name, value)

    def __repr__(self):
        inst = object.__getattribute__(self, '_instance')
        if inst is not None:
            return repr(inst)
        return f'<_LazyServiceRef(pending)>'


class AppBootstrap:
    _WINDOW_LIFECYCLE_DUPLICATE_COOLDOWN_S = 0.75
    _WINDOW_LIFECYCLE_STORM_WINDOW_S = 10.0
    _WINDOW_LIFECYCLE_STORM_LIMIT = 12
    _WINDOW_LIFECYCLE_STORM_COOLDOWN_S = 15.0
    _WINDOW_LIFECYCLE_TRACE_COOLDOWN_S = 2.0

    def __init__(
        self,
        workspace_root: str | None = None,
        *,
        _defer_services: bool = False,
    ) -> None:
        # Startup timeline: anchored on the first call.  Marks 'init_start'
        # before any heavy work so even imports counted before this point
        # can be inferred from main.py.
        self._timeline = get_global_timeline()
        self._timeline.mark('bootstrap_init_start', rss_mb=_rss_mb())

        # Runtime audit tracer: continuous self-audit from boot to shutdown.
        from iabv_v15.services.evolution.runtime_audit_tracer import (
            get_runtime_tracer,
            configure_runtime_tracer,
        )
        self._tracer = get_runtime_tracer()

        # Auto-cargar secretos ANTES de leer config (que consulta os.environ).
        _auto_load_secrets()

        self.config = load_app_config(workspace_root)
        self.theme = load_theme_config()
        self._ensure_directories()
        configure_logging(self.config.logs_dir)
        # Now that logs_dir exists, attach JSONL sink so every future
        # mark() call also persists to data/logs/startup_timeline.jsonl.
        configure_global_timeline(Path(self.config.logs_dir))
        # Configure runtime tracer with the same logs dir.
        configure_runtime_tracer(Path(self.config.logs_dir))
        self._tracer.trace('boot_start', workspace=workspace_root or '')
        _fp_event = self._tracer.trace_build_fingerprint(workspace=workspace_root or '.')
        _fp_data = _fp_event.get('data', {})
        if _fp_data.get('stale'):
            self._tracer.trace_stale_build_detected(
                head=_fp_data.get('head', ''),
                branch=_fp_data.get('branch', ''),
                missing_markers=_fp_data.get('missing_markers', []),
            )
        self._build_stale = bool(_fp_data.get('stale'))
        self._build_fingerprint_data = _fp_data
        self._window_lifecycle_recent: list[float] = []
        self._window_lifecycle_last: dict[str, tuple[float, object]] = {}
        self._window_lifecycle_storm_until = 0.0
        self._window_lifecycle_last_guard_trace = 0.0
        self._own_window_offscreen_last_trace = 0.0

        self._services_wired = False
        self._defer_services = _defer_services

        # VM placeholders needed by create_engine(defer_vm_creation=True)
        # which sets context properties to these (initially None) values.
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
        self.centro_vivo_viewmodel = None

        if not _defer_services:
            self._wire_services()

        self._timeline.mark(
            'bootstrap_init_done',
            services_deferred=_defer_services,
            tool_availability_deferred=not getattr(self, '_tool_availability_logged', False),
            rss_mb=_rss_mb(),
        )

    # ------------------------------------------------------------------
    # Service wiring — extracted from __init__ to allow deferral.
    #
    # When ``_defer_services=True`` (real app via main.py), ``__init__``
    # finishes in <1 s so ``run()`` can show the splash immediately.
    # ``_wire_services()`` is then called from ``run()`` while the splash
    # is already visible.  Tests call ``AppBootstrap(tmp_path)`` without
    # the flag and get the old behaviour (everything wired in __init__).
    # ------------------------------------------------------------------
    def _trace_init(self, name: str, fn: 'Callable[[], _T]') -> '_T':
        """Execute *fn* while tracing its duration for the runtime audit."""
        import time as _time
        t0 = _time.perf_counter()
        try:
            result = fn()
            elapsed = (_time.perf_counter() - t0) * 1000.0
            self._tracer.trace_service_init(name, elapsed, status='ok')
            return result
        except Exception as exc:
            elapsed = (_time.perf_counter() - t0) * 1000.0
            self._tracer.trace_service_init(
                name, elapsed, status='error', error=str(exc),
            )
            raise

    def _wire_services(self) -> None:
        if self._services_wired:
            return
        self._services_wired = True
        self._timeline.mark('wire_services_start', rss_mb=_rss_mb())
        self._tracer.trace('wire_services_start')

        _defer_scans = self._defer_services

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
        self.chat_message_repository = ChatMessageRepository(self.db)
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
        # BrowserSessionController + BrowserTeachSessionService: lazy-loaded
        # via @property.  Not needed for splash or shell/chat basic — only
        # accessed when browser teach mode or site exploration is activated.
        self._browser_session_controller_cache = None
        self._browser_teach_session_service_cache = None
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

        self.general_provider = OllamaExpertProvider(self.provider_configs[0], timeout_seconds=30.0, model_selector=None)  # Will be set after ResourceAwareModelSelector is initialized
        self.visual_provider = OpenAICompatLocalProvider(self.provider_configs[1], self.config.provider_timeout_seconds)
        self.optional_visual_provider = OpenAICompatLocalProvider(self.provider_configs[2], self.config.provider_timeout_seconds)
        self.site_manual_repository = SiteManualRepository(
            Path(self.config.evolution_dir) / 'site_manuals'
        )
        # SiteExplorationService: lazy-loaded via @property.  Only needed
        # when the user explores external sites (not for splash/chat).
        self._site_exploration_service_cache = None
        self.tool_adapters = {
            'playwright': PlaywrightToolAdapter(),
            'ollama': OllamaToolAdapter(self.general_provider, inference_service=None),  # Wired after InferenceService is created
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
                _LazyServiceRef(lambda: self.site_exploration_service),
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
        self._tracer.trace('phase_tools_adapters_done')
        self._timeline.mark('phase_tools_adapters_done', rss_mb=_rss_mb())
        self.tool_validator = ToolValidator()
        self.tool_sandbox = ToolSandbox(self.tool_validator)
        self.tool_registry = ToolRegistry(self.tool_record_repository, self.tool_adapters)
        # Tool-availability probe is **deferred** by default: it does HTTP
        # pings (Devin/GitHub/Ollama), enumerates external assistant
        # processes, AND triggers ``auto_fix_missing_tools`` (pip install
        # mcp_client, queue aider-chat).  All that runs synchronously on
        # the main thread; left here it added ~1-2s on Linux (and far
        # more on Windows with cold pip and slow networks) BEFORE the
        # splash window can render.  Schedule it post-window via
        # ``_run_deferred_post_window_setup`` instead.  Tests / MCP
        # subprocess can opt out via ``IABV_DEFER_TOOL_PROBE=0`` to
        # preserve legacy synchronous behavior.
        self._tool_availability_logged = False
        if os.environ.get('IABV_DEFER_TOOL_PROBE', '1') == '0':
            self._log_tool_availability()
            self._tool_availability_logged = True
        self._tracer.trace('phase_tool_registry_done')
        self.universal_perception_service = UniversalPerceptionService(tool_registry=self.tool_registry)
        self.environment_self_awareness_service = EnvironmentSelfAwarenessService(
            workspace_root=self.config.workspace_root,
            evolution_dir=self.config.evolution_dir,
            role_router=None,
            tool_registry=self.tool_registry,
            bootstrap_scan=not _defer_scans,
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
            bootstrap_scan=not _is_mcp_sub and not _defer_scans,
            scan_interval_seconds=300.0 if _is_mcp_sub else WorldModelService._DEFAULT_SCAN_INTERVAL,
            full_scan_interval_seconds=600.0 if _is_mcp_sub else WorldModelService._DEFAULT_FULL_SCAN_INTERVAL,
        )
        self._tracer.trace('phase_world_model_done')
        self.interaction_learning_service = InteractionLearningService(self.tool_record_repository)
        self.interaction_mode_selector = InteractionModeSelector(self.tool_registry, self.tool_record_repository)
        self.tool_memory = ToolMemory(self.tool_record_repository, self.interaction_learning_service)
        self.tool_approval_policy = ToolApprovalPolicy()
        self.tool_rollback_manager = ToolRollbackManager()
        self.algorithm_benchmark_registry = AlgorithmBenchmarkRegistry()
        self.decision_scoring_engine = DecisionScoringEngine()
        self.adaptive_weight_layer = AdaptiveWeightLayer(
            persistence_path=str(Path(self.config.workspace_root) / 'data' / 'evolution' / 'adaptive_weights' / 'metacognitive_adjustments.json'),
        )
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

        self.account_approval_ledger = AccountApprovalLedger()
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
            account_resource_scanner=estimate_available_workers,
            account_approval_ledger=self.account_approval_ledger,
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

        self._tracer.trace('phase_oses_done')
        self._timeline.mark('phase_oses_done', rss_mb=_rss_mb())
        # Autonomy cycle: central service for pending queue, resume hints,
        # capability discovery, and OSES→queue bridge.  Replaces the
        # scattered Fix 18b/18d/18e patches with one coherent module.
        from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
        from iabv_v15.services.evolution.autonomy_cycle_service import AutonomyCycleService
        self.platform_pending_queue = PlatformPendingQueue(
            evolution_dir=self.config.evolution_dir,
        )
        self.autonomy_cycle_service = AutonomyCycleService(
            queue=self.platform_pending_queue,
        )
        try:
            self.platform_pending_queue.seed_windows_integration_tasks()
        except Exception:
            pass
        try:
            env = getattr(self, 'environment_self_awareness_service', None)
            if env is not None and hasattr(env, 'current_model'):
                model = env.current_model()
                if model is not None and model.capability_graph:
                    self.autonomy_cycle_service.seed_capabilities(
                        model.capability_graph,
                    )
        except Exception:
            pass
        # Seed permission gates from WorldModel (if any are ungranted).
        try:
            wms = getattr(self, 'world_model_service', None)
            if wms is not None:
                snapshot = wms.current_model()
                if snapshot is not None and snapshot.permission_gates:
                    self.autonomy_cycle_service.seed_permission_gaps(
                        snapshot.permission_gates,
                    )
        except Exception:
            pass
        # Freeze incident reporter — structured auto-audit for UI freezes.
        from iabv_v15.services.evolution.freeze_incident_reporter import (
            FreezeIncidentReporter,
            UIHeartbeatWatchdog,
            ChatInteractionLifecycle,
        )
        self.freeze_incident_reporter = FreezeIncidentReporter(
            evolution_dir=self.config.evolution_dir,
            db_path=self.config.sqlite_path,
        )
        # UI heartbeat watchdog — lightweight main-thread stall detector.
        self.ui_heartbeat_watchdog = UIHeartbeatWatchdog(
            freeze_reporter=self.freeze_incident_reporter,
        )
        # Canonical interaction lifecycle tracker.
        self.chat_interaction_lifecycle = ChatInteractionLifecycle()
        # Wire lifecycle reference into watchdog for stall enrichment.
        self.ui_heartbeat_watchdog.set_lifecycle(self.chat_interaction_lifecycle)

        # Seed metacognition investigation roadmap (Phases A/B/C).
        try:
            self.platform_pending_queue.seed_metacognition_investigation_phases()
        except Exception:
            pass

        # Wire AutonomyCycleService into OSES (available now).
        # TaskOutcomeRecorder wiring deferred to _wire_autonomy_cycle()
        # because task_outcome_recorder is created later in the bootstrap.
        self.operational_self_examination_service._autonomy_cycle_service = (
            self.autonomy_cycle_service
        )
        # Wire FreezeIncidentReporter into OSES so auto-capture of startup
        # freezes can fire structured incidents.  PortableContext wiring
        # deferred until after PortableContextService is created (~line 985).
        self.operational_self_examination_service._freeze_incident_reporter = (
            self.freeze_incident_reporter
        )
        # Wire UIHeartbeatWatchdog into OSES for stall findings.
        self.operational_self_examination_service._ui_heartbeat_watchdog = (
            self.ui_heartbeat_watchdog
        )

        # Fix 19b: Windows clipboard bridge — low-level ctypes-based
        # clipboard for background services that don't have QGuiApplication.
        from iabv_v15.services.platform.win_clipboard_bridge import WinClipboardBridge
        self.win_clipboard_bridge = WinClipboardBridge()

        # Fix 19a: Windows system tray bridge — created here, shown later
        # in run() after QGuiApplication is available.
        from iabv_v15.services.platform.win_systray_bridge import WinSystrayBridge
        self.win_systray_bridge = WinSystrayBridge(
            app_name=self.config.app_name,
        )

        # Fix 21: Windows toast notification bridge — tries winotify,
        # falls back to QSystemTrayIcon balloon.
        from iabv_v15.services.platform.win_toast_bridge import WinToastBridge
        self.win_toast_bridge = WinToastBridge(
            app_name=self.config.app_name,
            systray_bridge=self.win_systray_bridge,
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
            platform_pending_queue=self.platform_pending_queue,
        )
        # Wire FreezeIncidentReporter into PortableContext for promotion.
        self.portable_context_service.freeze_incident_reporter = (
            self.freeze_incident_reporter
        )
        # Wire UIHeartbeatWatchdog and ChatInteractionLifecycle into
        # PortableContext for promotion to the portable package.
        self.portable_context_service.ui_heartbeat_watchdog = (
            self.ui_heartbeat_watchdog
        )
        self.portable_context_service.chat_interaction_lifecycle = (
            self.chat_interaction_lifecycle
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
            build_llm_local_ollama_runner(self.general_provider, inference_service=None),  # Wired after InferenceService is created
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
            account_resource_scanner=build_inventory_snapshot,
            platform_pending_queue=self.platform_pending_queue,
            workspace_root=self.config.workspace_root,
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
        # Deferred wiring: AutonomyCycleService into TaskOutcomeRecorder
        # (the queue/OSES wiring happened earlier during queue construction).
        if hasattr(self, 'autonomy_cycle_service'):
            self.task_outcome_recorder.autonomy_cycle_service = (
                self.autonomy_cycle_service
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
        # credential_broker + clarification_request_service injection on
        # browser_teach_session_service is deferred to its @property getter
        # to avoid forcing eager construction here.
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
            autonomy_cycle_service=getattr(self, 'autonomy_cycle_service', None),
        )
        self.portable_context_service.task_context_assembler = self.task_context_assembler
        self.portable_context_service.adaptive_task_orchestrator = self.adaptive_task_orchestrator
        self.api_key_discovery_service = ApiKeyDiscoveryService(data_root=self.config.data_dir)
        self.code_audit_trail = CodeAuditTrail(data_root=self.config.data_dir)
        self.code_audit_trail.experiment_lab = self.experiment_lab
        self.decision_audit_trail = DecisionAuditTrail(data_root=self.config.data_dir)
        self.operational_self_examination_service.decision_audit_trail = self.decision_audit_trail
        self.operational_self_examination_service.chat_message_repository = self.chat_message_repository
        self.operational_self_examination_service.code_audit_trail = self.code_audit_trail
        self.portable_context_service.decision_audit_trail = self.decision_audit_trail
        self.portable_context_service.chat_message_repository = self.chat_message_repository
        self.portable_context_service.code_audit_trail = self.code_audit_trail
        self.portable_context_service.control_master_service = self.control_master_service
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
            self.platform_learning.browser_teach = _LazyServiceRef(lambda: self.browser_teach_session_service)
            self.platform_learning.site_exploration = _LazyServiceRef(lambda: self.site_exploration_service)
            self.platform_learning.universal_perception = self.universal_perception_service
            self.platform_learning.replay_confidence = self.replay_confidence_service
            self.platform_learning.decision_simplifier = self.decision_simplifier
            self.platform_learning.api_key_discovery = self.api_key_discovery_service
        except Exception as exc:
            logger.warning('bootstrap: PlatformLearningOrchestrator init failed: %s', exc)
            self.platform_learning = None

        try:
            self.resource_metacognition_service = ResourceMetacognitionService(
                evolution_dir=self.config.evolution_dir,
                environment_service=self.environment_self_awareness_service,
                experiment_lab=self.experiment_lab,
                decision_audit_trail=getattr(self, 'decision_audit_trail', None),
            )
        except Exception as exc:
            logger.warning('bootstrap: ResourceMetacognitionService init failed: %s', exc)
            self.resource_metacognition_service = None

        try:
            self.metacognition_evolution = MetacognitionEvolutionMixin()
            self.metacognition_evolution.decision_simplifier = self.decision_simplifier
            self.metacognition_evolution.platform_learning = self.platform_learning
            self.metacognition_evolution.api_key_discovery = self.api_key_discovery_service
            self.metacognition_evolution.auto_correction_engine = getattr(self, 'auto_correction_engine', None)
            self.metacognition_evolution.resource_metacognition = self.resource_metacognition_service
        except Exception as exc:
            logger.warning('bootstrap: MetacognitionEvolutionMixin init failed: %s', exc)
            self.metacognition_evolution = None

        # Wire metacognition into OSES so build_review() picks up evolution findings
        if self.metacognition_evolution is not None:
            self.operational_self_examination_service.metacognition_evolution = self.metacognition_evolution
        
        # Wire ReflectionRoutingService and ResourceAwareController into orchestrator
        try:
            from iabv_v15.services.adaptive.reflection_routing import ReflectionRoutingService
            from iabv_v15.services.adaptive.resource_aware_controller import ResourceAwareController
            self.reflection_routing_service = ReflectionRoutingService(
                world_model_service=self.world_model_service,
                resource_controller=None,  # Will be set after ResourceAwareController is created
            )
            self.resource_aware_controller = ResourceAwareController()
            self.reflection_routing_service.resource_controller = self.resource_aware_controller
            self.adaptive_task_orchestrator.reflection_routing_service = self.reflection_routing_service
            self.adaptive_task_orchestrator.resource_aware_controller = self.resource_aware_controller
            logger.info('bootstrap: ReflectionRoutingService and ResourceAwareController wired')
        except Exception as exc:
            logger.warning('bootstrap: ReflectionRoutingService/ResourceAwareController wiring failed: %s', exc)
            self.reflection_routing_service = None
            self.resource_aware_controller = None
        
        # Wire ResourceAwareModelSelector into bootstrap and providers
        try:
            from iabv_v15.services.adaptive.resource_aware_model_selector import ResourceAwareModelSelector
            self.resource_aware_model_selector = ResourceAwareModelSelector(
                ollama_inventory=None,  # Can be populated later from Ollama health check
            )
            # Wire ResourceAwareModelSelector into OllamaExpertProvider
            if hasattr(self, 'general_provider'):
                self.general_provider.model_selector = self.resource_aware_model_selector
            logger.info('bootstrap: ResourceAwareModelSelector initialized and wired')
        except Exception as exc:
            logger.warning('bootstrap: ResourceAwareModelSelector initialization failed: %s', exc)
            self.resource_aware_model_selector = None

        self.inference_service = InferenceService(
            self.role_router,
            self.run_repository,
            self.execution_dossier_service,
            adaptive_orchestrator=self.adaptive_task_orchestrator,
            knowledge_service=self.knowledge_service,
        )
        # Wire InferenceService into LocalRoleRouter to enforce reflection routing and resource governance
        if self.role_router is not None:
            self.role_router.inference_service = self.inference_service
        # Wire InferenceService into AdaptiveTaskOrchestrator for ToolCallingBridge re-query routing
        if self.adaptive_task_orchestrator is not None:
            self.adaptive_task_orchestrator._inference_service = self.inference_service
        # Wire InferenceService into OllamaToolAdapter to enforce reflection routing and resource governance
        ollama_adapter = self.tool_adapters.get('ollama')
        if ollama_adapter is not None:
            ollama_adapter.inference_service = self.inference_service
        # Wire InferenceService into capability audit harness for llm_local_ollama runner
        if self.capability_audit_harness is not None:
            from iabv_v15.infra.mcp.audit_tools.audit_capability import build_llm_local_ollama_runner
            self.capability_audit_harness.register(
                "llm_local_ollama",
                build_llm_local_ollama_runner(self.general_provider, inference_service=self.inference_service),
            )

        # InternalMetabolicStateService: unified internal state inspection layer
        # Composes existing self-inspection services without duplication
        from iabv_v15.services.evolution.internal_metabolic_state_service import (
            InternalMetabolicStateService,
        )
        self.internal_metabolic_state_service = InternalMetabolicStateService(
            workspace_root=self.config.workspace_root,
            operational_self_examination_service=self.operational_self_examination_service,
            control_master_service=self.control_master_service,
            environment_self_awareness_service=self.environment_self_awareness_service,
            capability_readiness_service=self.capability_readiness_service,
            role_router=self.role_router,
            inference_service=self.inference_service,
            adaptive_task_orchestrator=self.adaptive_task_orchestrator,
            task_context_assembler=self.task_context_assembler,
            reflection_routing_service=self.reflection_routing_service,
            resource_aware_controller=self.resource_aware_controller,
            unified_memory_layer=self.unified_memory_layer,
            autonomous_validation_cycle=self.autonomous_validation_cycle,
            sandbox_experiment_service=self.sandbox_experiment_service,
            tool_teach_service=self.tool_teach_service,
        )
        logger.info('bootstrap: InternalMetabolicStateService wired')

        # WorkQueueExecutor: bridge between ControlMaster work queue and canonical inference
        # Implements the executive loop bridge without owning the queue or becoming a new ControlMaster
        from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy
        self.work_queue_executor = WorkQueueExecutor(
            control_master_service=self.control_master_service,
            inference_service=self.inference_service,
            task_outcome_recorder=self.task_outcome_recorder,
            cognitive_policy=CognitiveOperatingPolicy(),
            resource_aware_controller=self.resource_aware_controller,
        )
        logger.info('bootstrap: WorkQueueExecutor wired with cognitive policy and resource-aware controller')

        self.training_orchestrator = TrainingOrchestrator(
            workspace_root=self.config.workspace_root,
            episode_repository=self.episode_repository,
            knowledge_repository=self.knowledge_repository,
            run_repository=self.run_repository,
            archive_service=self.payload_archive_service,
            artifact_repository=self.session_artifact_repository,
        )

        # If scans were deferred, trigger an async refresh now that all
        # services are wired.  The background threads (already started by
        # auto_start=True inside the constructors) will pick up the signal
        # and perform their first scan without blocking the GUI thread.
        if _defer_scans:
            try:
                self.environment_self_awareness_service.request_refresh(
                    reason='deferred_bootstrap', full=True,
                )
            except Exception:
                pass
            try:
                self.world_model_service.request_refresh(
                    reason='deferred_bootstrap', full=True,
                )
            except Exception:
                pass

        self._timeline.mark(
            'wire_services_done',
            tool_availability_deferred=not self._tool_availability_logged,
            scans_deferred=_defer_scans,
            rss_mb=_rss_mb(),
        )

        self._prepare_boot_profile_store()

    def _prepare_boot_profile_store(self) -> None:
        """Create the boot profile store and resolve environment_id.

        The store is created here (after ``wire_services_done``) so that
        ``environment_id`` is available, but persistence is deferred to
        ``_persist_boot_profile()`` which is called from
        ``_handle_page_loader_ready`` — the sovereign definition of
        "boot visible complete".

        For MCP-only sessions (no UI, no page_loader_ready signal),
        ``_persist_boot_profile`` is called as a fallback from the MCP
        server startup path or can be triggered manually.
        """
        try:
            from iabv_v15.services.evolution.boot_profile_store import BootProfileStore
            env_model = self.environment_self_awareness_service.current_model()
            environment_id = env_model.environment_id if env_model else ''
            if not environment_id:
                return
            self.boot_profile_store = BootProfileStore(data_root=self.config.data_dir)
            self.portable_context_service.boot_profile_store = self.boot_profile_store
            self.operational_self_examination_service.boot_profile_store = self.boot_profile_store
            self._boot_profile_environment_id = environment_id
            self._boot_profile_metadata = {
                'scan_status': env_model.scan_status if env_model else '',
                'known_environment': env_model.known_environment if env_model else False,
            }
            self._boot_profile_persisted = False
        except Exception as exc:
            logger.debug('boot_profile: store preparation skipped: %s', exc)

    def _persist_boot_profile(self, trigger: str = 'page_loader_ready') -> None:
        """Persist boot telemetry at the moment the visible boot is complete.

        Called from ``_handle_page_loader_ready`` (preferred) or
        ``_handle_splash_closing`` (fallback).  Idempotent: a second
        call is a no-op.  Crash-safe: any error is swallowed.

        The timeline snapshot taken here includes late milestones
        (``shell_loader_ready``, ``page_loader_ready``,
        ``splash_window_closing``) so ``boot_duration_ms`` reflects
        the full visible boot, not just wiring.  ``wiring_duration_ms``
        is recorded separately as the ``bootstrap_init_start`` →
        ``wire_services_done`` interval.
        """
        if getattr(self, '_boot_profile_persisted', True):
            return
        self._boot_profile_persisted = True
        try:
            store = getattr(self, 'boot_profile_store', None)
            env_id = getattr(self, '_boot_profile_environment_id', '')
            if not store or not env_id:
                return
            metadata = getattr(self, '_boot_profile_metadata', {}) or {}
            metadata['persist_trigger'] = trigger
            store.record_boot_session(
                environment_id=env_id,
                timeline_events=self._timeline.events(),
                metadata=metadata,
            )
        except Exception as exc:
            logger.debug('boot_profile: persistence skipped: %s', exc)

    # ------------------------------------------------------------------
    # Lazy-loaded services — constructed on first access, not at wiring
    # time.  Saves memory when these subsystems are never activated in a
    # given session (e.g. browser teach mode, site exploration).
    # ------------------------------------------------------------------

    @property
    def browser_session_controller(self):
        if self._browser_session_controller_cache is None:
            self._browser_session_controller_cache = BrowserSessionController()
        return self._browser_session_controller_cache

    @property
    def browser_teach_session_service(self):
        if self._browser_teach_session_service_cache is None:
            svc = BrowserTeachSessionService(
                controller=self.browser_session_controller,
                episode_repository=self.episode_repository,
                screenshot_store=self.screenshot_store,
                artifact_repository=self.session_artifact_repository,
                redaction_engine=self.redaction_engine,
                site_session_manager=self.site_session_manager,
            )
            if hasattr(self, 'credential_broker'):
                svc.credential_broker = self.credential_broker
            if hasattr(self, 'clarification_request_service'):
                svc.clarification_request_service = self.clarification_request_service
            self._browser_teach_session_service_cache = svc
        return self._browser_teach_session_service_cache

    @property
    def site_exploration_service(self):
        if self._site_exploration_service_cache is None:
            self._site_exploration_service_cache = SiteExplorationService()
        return self._site_exploration_service_cache

    def _run_deferred_post_window_setup(self) -> None:
        """Run heavy probes that were skipped during ``__init__``.

        Called from ``run()`` via ``QTimer.singleShot`` *after* the main
        window is shown.  The work is split into two phases:

        **Phase A** (this thread): tool availability probes + pending
        queue seeding.  This is the minimum needed for the program to
        know what tools are available.

        **Phase B** (separate thread, started after Phase A): auto-install
        of missing pip-installable tools, self-examination, common-sense
        reasoning, and GPU health check.  These are non-critical for the
        interactive shell and would otherwise add ~1-3 s of latency and
        ~50-150 MB RSS to the critical startup path.

        Both phases run in background threads so they never starve the
        Qt event loop.

        Idempotent: a second call is a no-op.
        """
        if self._tool_availability_logged:
            return
        self._tool_availability_logged = True

        self._deferred_setup_active = True
        self._push_bootstrap_flags_to_watchdog()
        bridge = self.main_window_bridge
        if bridge is not None:
            bridge.set_deferred_setup_active(True)

        def _bg_post_window_setup() -> None:
            try:
                self._timeline.mark(
                    'deferred_post_window_setup_start', rss_mb=_rss_mb(),
                )
            except Exception:
                pass
            try:
                self._read_with_retry(self._log_tool_availability)
            except Exception as exc:
                logger.warning('deferred_tool_availability_probe failed: %s', exc)
                self._record_startup_sqlite_incident(exc)
            try:
                self._timeline.mark(
                    'deferred_post_window_setup_done', rss_mb=_rss_mb(),
                )
            except Exception:
                pass
            # Issue #266: flush startup_health into portable_context/latest.json
            # so short-lived runs don't leave stale data.
            pcs = getattr(self, 'portable_context_service', None)
            if pcs is not None:
                try:
                    pcs.flush_startup_health()
                except Exception:
                    logger.debug('flush_startup_health failed', exc_info=True)

            self._deferred_setup_active = False
            self._push_bootstrap_flags_to_watchdog()
            self._check_startup_followup_done()
            if bridge is not None:
                bridge.set_deferred_setup_active(False)

            # Phase B: non-critical metacognition scans in a separate
            # thread so they don't block tool-probe completion signaling.
            self._run_deferred_metacognition_scan()

        threading.Thread(
            target=_bg_post_window_setup,
            name='iabv-deferred-post-window',
            daemon=True,
        ).start()

    def _run_deferred_metacognition_scan(self) -> None:
        """Phase B of post-window setup: non-critical metacognition scans.

        Runs self-examination, common-sense reasoning, and auto-install
        of missing tools in a **separate background thread** so they
        don't add latency to Phase A (tool probes) or block the Qt
        event loop.

        These are important for the program's self-awareness but NOT
        required for the interactive shell to function.  Deferring them
        reduces peak startup RSS by ~50-150 MB and shaves ~1-3 s off
        the visible startup time.
        """
        if getattr(self, '_metacognition_scan_started', False):
            return
        self._metacognition_scan_started = True

        def _bg_metacognition() -> None:
            # P0.40 Task F: if user query is pending, defer metacognition
            watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
            if watchdog is not None and getattr(watchdog, '_query_pending', False):
                self._tracer.trace(
                    'startup_heavy_work_deferred_due_to_user_or_stall',
                    phase='deferred_metacognition',
                    reason='query_pending',
                )
                return
            try:
                self._timeline.mark(
                    'deferred_metacognition_start', rss_mb=_rss_mb(),
                )
            except Exception:
                pass
            try:
                self._read_with_retry(self._startup_self_examination)
            except Exception as exc:
                logger.warning('deferred_self_examination failed: %s', exc)
            try:
                self._run_startup_common_sense()
            except Exception as exc:
                logger.warning('deferred_common_sense failed: %s', exc)
            try:
                self._deferred_auto_install_missing_tools()
            except Exception as exc:
                logger.debug('deferred_auto_install failed: %s', exc)
            try:
                self._timeline.mark(
                    'deferred_metacognition_done', rss_mb=_rss_mb(),
                )
            except Exception:
                pass

        threading.Thread(
            target=_bg_metacognition,
            name='iabv-deferred-metacognition',
            daemon=True,
        ).start()

    def _deferred_auto_install_missing_tools(self) -> None:
        """Auto-install missing pip-installable tools (deferred from startup).

        Moved out of ``_log_tool_availability`` so tool probes complete
        faster and the program knows what's available without waiting
        for pip install to finish.
        """
        missing = getattr(self, '_deferred_missing_tools', [])
        if not missing:
            return
        try:
            from iabv_v15.services.auto_correction_engine import auto_fix_missing_tools
            install_result = auto_fix_missing_tools(missing)
            installed_count = install_result.get('installed', 0)
            if installed_count:
                logger.info(
                    'deferred_auto_install: %d/%d tools installed',
                    installed_count, len(missing),
                )
        except Exception as exc:
            logger.debug('deferred_auto_install: failed — %s', exc)

    def _handle_shell_loader_ready(self) -> None:
        """Punto de aterrizaje honesto para el readiness real del shell.

        Disparado por ``MainWindowBridge.shellLoaderReady`` cuando QML
        confirma que ``mainShellLoader`` termino de instanciar el
        contenido real del shell.  Aqui — y solo aqui — marcamos el
        hito ``shell_loader_ready`` y disparamos
        ``splashController.set_ready()`` para que el splash empiece a
        desvanecer.

        With synchronous mainShellLoader (``asynchronous: false``), this
        fires during the first ``processEvents()`` after ``mainShellKickoff``
        triggers — typically inside Phase 2's ``_yield_to_event_loop()``.

        Also starts a safety-net timer for Phase 3: if ``page_loader_ready``
        never arrives (pageLoader stuck), Phase 3 VMs still get built
        after 5 s.  Idempotent via ``_schedule_pending_deferred_2``.

        Idempotente: solo el primer disparo cuenta.
        """
        if getattr(self, '_shell_loader_ready_handled', False):
            return
        self._shell_loader_ready_handled = True
        # Update splash to 90% before closing — honest progress.
        splash = getattr(self, '_splash', None)
        if splash is not None:
            try:
                splash.set_progress(90)
            except Exception:
                pass
        try:
            self._timeline.mark('shell_loader_ready')
        except Exception:
            pass
        self._fire_splash_ready_and_raise_main('shell_loader_ready')
        QTimer.singleShot(
            0,
            lambda: self._ensure_startup_chat_bridge_ready('shell_loader_ready'),
        )
        # Safety net: if page_loader_ready never fires (e.g. pageLoader
        # async incubation stuck), ensure Phase 3 VMs still get built.
        QTimer.singleShot(5000, self._schedule_pending_deferred_2)

    def _handle_qml_loader_event(self, loader_name: str, status: int, active_now: bool) -> None:
        """Marca cada transicion granular de un Loader QML al timeline.

        Llega desde ``MainWindowBridge.qmlLoaderEvent`` que QML emite
        en ``onStatusChanged`` y ``onActiveChanged`` de cada Loader
        relevante.  Sirve para ver en el JSONL si el QQmlIncubator
        avanza o se queda bloqueado en ``Loading=2`` en Windows.

        Safety net: if we receive ``status=1`` (Ready) for the
        ``mainShellLoader`` but ``_handle_shell_loader_ready`` was never
        called (e.g. QML signal delivery race on Windows), we trigger
        shell readiness from here.
        """
        try:
            phase = f'qml_loader_{loader_name}_status_{int(status)}'
            self._timeline.mark(
                phase,
                loader=loader_name,
                status=int(status),
                active=bool(active_now),
            )
        except Exception:
            pass
        # Belt-and-suspenders: status=1 is Loader.Ready.  If the direct
        # shellLoaderReady signal was lost (observed on some Windows runs),
        # trigger readiness from this parallel path.
        if loader_name == 'mainShellLoader' and int(status) == 1:
            if not getattr(self, '_shell_loader_ready_handled', False):
                logger.info(
                    'shell_loader_ready via qml_loader_event safety net '
                    '(direct signal was not received)',
                )
                self._handle_shell_loader_ready()

    def _handle_main_qml_completed(self) -> None:
        """Marca ``main_qml_completed`` cuando ``Main.qml`` evaluo su tree.

        Si este hito no aparece en el JSONL, significa que la
        ``ApplicationWindow`` raiz nunca llamo ``Component.onCompleted``
        y el problema esta antes del shell loader.
        """
        try:
            self._timeline.mark('main_qml_completed')
        except Exception:
            pass

    def _schedule_pending_deferred_2(self) -> None:
        """Schedule lazy VM wiring if not yet scheduled.

        Called from ``_handle_page_loader_ready`` (preferred) or
        ``_force_splash_ready_fallback`` (safety net).  The actual VM
        construction happens lazily via ``_ensure_vm_for_route`` (on
        navigation) or ``_build_all_lazy_vms`` (idle pre-build at 15 s).
        """
        if getattr(self, '_deferred_batch_2_scheduled', False):
            return
        fn = getattr(self, '_pending_deferred_2_fn', None)
        if fn is None:
            return
        self._deferred_batch_2_scheduled = True
        QTimer.singleShot(0, fn)

    def _handle_page_loader_ready(self) -> None:
        """Marca ``page_loader_ready`` (hito mas honesto aun que shell).

        Cuando esto llega, el usuario realmente esta viendo la pagina
        renderizada (Dashboard u otra ruta).  Si en una corrida
        Windows ``shell_loader_ready`` llega pero ``page_loader_ready``
        no, la incubacion del page loader es la atascada (no el shell
        exterior).  Tambien dispara raise/activate del main window
        como reasegurador del Z-order.

        Also triggers Phase 3 (deferred batch 2) VM construction so
        non-critical VMs are built only after the user sees the first
        paint — never during the pre-ready critical path.

        If ``shell_loader_ready`` never arrived, this signal is
        sufficient to close the splash and mark readiness — it is
        the MORE honest hito because the user already sees rendered
        content.
        """
        self._page_loader_ready_received = True
        try:
            self._timeline.mark('page_loader_ready')
        except Exception:
            pass
        self._persist_boot_profile('page_loader_ready')
        # If shell_loader_ready never fired, page_loader_ready is
        # sufficient to close the splash — the user is already seeing
        # rendered content.  This prevents the fallback from firing
        # after the page is already visible.
        if not getattr(self, '_shell_loader_ready_handled', False):
            self._shell_loader_ready_handled = True
            self._fire_splash_ready_and_raise_main('page_loader_ready')
        else:
            self._raise_main_window_now('page_loader_ready')
        QTimer.singleShot(
            0,
            lambda: self._ensure_startup_chat_bridge_ready('page_loader_ready'),
        )
        # Schedule Phase 3: build non-critical VMs now that the user
        # is seeing the rendered page.
        self._schedule_pending_deferred_2()
        # Final truth refresh: re-persist PortableContext and OSES now
        # that the timeline contains populate_ui_done + page_loader_ready.
        # Without this, latest.md/latest.json keep the stale early snapshot
        # that says "populate_ui never finished".
        self._truth_refresh_active = True
        self._push_bootstrap_flags_to_watchdog()
        threading.Thread(
            target=self._final_startup_truth_refresh,
            name='iabv-startup-truth-refresh',
            daemon=True,
        ).start()

    # P0.40 Task F: startup freeze budget — max ms a single startup
    # step may block the event loop before being deferred.
    _STARTUP_FREEZE_BUDGET_MS: float = 1500.0

    def _final_startup_truth_refresh(self) -> None:
        """Re-persist OSES and PortableContext after boot is truly complete.

        P0.40 Task F additions:
        - If a user query is pending (watchdog.query_pending), skip refresh
          entirely and trace startup_heavy_work_deferred_due_to_user_or_stall.
        - If recent UI stall detected (>1500 ms), defer refresh and trace.
        - OSES finding if truth refresh causes repeated stalls.

        Order matters: OSES must refresh FIRST so its review reflects
        the final boot state.  Then PortableContext persists with the
        up-to-date OSES summary — not a stale one.
        """
        # P0.40: check if user query is pending — defer heavy work
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        query_pending = False
        recent_stall = False
        if watchdog is not None:
            query_pending = getattr(watchdog, '_query_pending', False)
            recent_stall = self._has_recent_ui_stall(watchdog)

        if query_pending or recent_stall:
            defer_reason = 'query_pending' if query_pending else 'recent_ui_stall'
            logger.info(
                'startup_truth_refresh: deferred due to %s', defer_reason,
            )
            self._tracer.trace(
                'startup_heavy_work_deferred_due_to_user_or_stall',
                phase='truth_refresh',
                reason=defer_reason,
            )
            self._truth_refresh_active = False
            self._push_bootstrap_flags_to_watchdog()
            self._check_startup_followup_done()
            return

        force_refresh = self._metacognition_data_is_stale()
        if not force_refresh:
            try:
                self._tracer.trace(
                    'startup_truth_refresh_skipped_fresh',
                    reason='metacognition_artifacts_fresh',
                )
            except Exception:
                pass
            logger.info('startup_truth_refresh: skipped; metacognition artifacts are fresh')
            self._truth_refresh_active = False
            self._push_bootstrap_flags_to_watchdog()
            self._check_startup_followup_done()
            return

        # Startup must not run minutes-long metacognitive regeneration.
        # The app needs to communicate first; stale OSES/PortableContext
        # is handled by the idle/deferred maintenance loop, not by blocking
        # the birth path.
        try:
            self._tracer.trace(
                'startup_truth_refresh_deferred_stale',
                reason='stale_metacognition_deferred_to_idle',
                budget_ms=self._STARTUP_FREEZE_BUDGET_MS,
            )
        except Exception:
            pass
        logger.warning(
            'startup_truth_refresh: stale metacognition detected; '
            'deferred to idle maintenance instead of running during startup',
        )
        self._truth_refresh_active = False
        self._push_bootstrap_flags_to_watchdog()
        self._check_startup_followup_done()
        return

    def _has_recent_ui_stall(self, watchdog: Any, threshold_ms: float = 1500.0) -> bool:
        """P0.40 Task F: check if watchdog recorded a recent UI stall."""
        try:
            recent_stalls = getattr(watchdog, '_recent_stalls', [])
            if not recent_stalls:
                return False
            import time as _t
            now = _t.time()
            for stall in recent_stalls[-5:]:
                stall_at = stall.get('at', 0)
                stall_ms = stall.get('duration_ms', 0)
                if now - stall_at < 30 and stall_ms > threshold_ms:
                    return True
        except Exception:
            pass
        return False

    def _metacognition_data_is_stale(self, max_age_hours: float = 24.0) -> bool:
        """Check if OSES / PortableContext latest.json are older than *max_age_hours*."""
        import time as _time
        config = getattr(self, 'config', None)
        data_dir = getattr(config, 'data_dir', None)
        if data_dir is None:
            return False
        base = Path(data_dir) / 'evolution'
        candidates = [
            base / 'self_examination' / 'latest.json',
            base / 'portable_context' / 'latest.json',
        ]
        now = _time.time()
        max_age_s = max_age_hours * 3600
        for path in candidates:
            try:
                if path.exists():
                    age = now - path.stat().st_mtime
                    if age > max_age_s:
                        logger.info('stale metacognition: %s is %.1fh old', path.name, age / 3600)
                        return True
            except Exception:
                pass
        return False

    def _handle_splash_closing(self) -> None:
        """Marca ``splash_window_closing`` cuando QML va a llamar close().

        Si este hito aparece pero el splash sigue visible en pantalla,
        la causa es Z-order del Window Manager y no del codigo Python.
        """
        try:
            self._timeline.mark('splash_window_closing')
        except Exception:
            pass
        self._persist_boot_profile('splash_window_closing')

    def _mark_late_ui_bridge_ready_if_shell_is_visible(self, bridge) -> bool:
        """Mark a bridge created after the QML shell became interactive.

        The control VM and UIBridge can be built lazily after
        ``page_loader_ready``.  In that path ``_fire_splash_ready_and_raise_main``
        already ran before a bridge existed, so the new server would otherwise
        keep ``shell_ready=False`` forever and buffer all chat messages.
        """
        source = ''
        if getattr(self, '_page_loader_ready_received', False):
            source = 'late_bridge_start_after_page_loader_ready'
        elif getattr(self, '_shell_loader_ready_handled', False):
            source = 'late_bridge_start_after_shell_ready'
        if not source:
            return False
        try:
            bridge.mark_shell_ready(source)
            return True
        except Exception:
            logger.debug('late bridge mark_shell_ready failed from %s', source, exc_info=True)
            return False

    def _startup_chat_bridge_is_ready(self) -> bool:
        """Return True when the live chat bridge can accept UI messages."""
        if getattr(self, 'control_center_viewmodel', None) is None:
            return False
        bridge = getattr(self, 'ui_bridge_server', None)
        if bridge is None:
            return False
        status = getattr(bridge, 'status', None)
        if status is None:
            return False
        return bool(
            getattr(status, 'running', False)
            and getattr(status, 'control_vm_bound', False)
        )

    def _mark_startup_chat_bridge_ready(self, source: str, bridge: Any | None = None) -> None:
        """Persist the earliest point where UI chat is actually reachable.

        This is the user-communication contract for startup. Heavy
        metacognition, tool probes and auto-install can be useful, but the
        organism must first have a working channel to explain what it is doing.
        """
        bridge = bridge if bridge is not None else getattr(self, 'ui_bridge_server', None)
        status = getattr(bridge, 'status', None)
        running = bool(getattr(status, 'running', False))
        control_vm_bound = bool(getattr(status, 'control_vm_bound', False))
        shell_ready = bool(getattr(status, 'shell_ready', False))
        first_mark = not getattr(self, '_startup_chat_bridge_ready', False)
        self._startup_chat_bridge_ready = running and control_vm_bound
        payload = {
            'source': source,
            'running': running,
            'control_vm_bound': control_vm_bound,
            'shell_ready': shell_ready,
        }
        if first_mark and self._startup_chat_bridge_ready:
            try:
                self._timeline.mark('startup_chat_bridge_ready', **payload)
            except Exception:
                pass
        try:
            self._tracer.trace('startup_chat_bridge_ready', **payload)
        except Exception:
            pass

    def _ensure_startup_chat_bridge_ready(self, source: str = 'startup') -> bool:
        """Build only the ControlCenterVM/bridge communication path early.

        The rest of lazy VM prebuild stays governed by resource pressure and
        idle timing. This method intentionally does not make route decisions;
        it only ensures the single user communication channel exists.
        """
        if self._startup_chat_bridge_is_ready():
            self._mark_startup_chat_bridge_ready(source)
            return True

        ctx = getattr(self, '_qml_root_context', None)
        if ctx is None:
            try:
                self._timeline.mark(
                    'startup_chat_bridge_deferred',
                    source=source,
                    reason='qml_context_missing',
                )
            except Exception:
                pass
            return False

        missing_deps = [
            name for name in (
                'mcp_bridge_service',
                'ui_bridge_server',
                'chat_capability_ingestion_service',
            )
            if not hasattr(self, name)
        ]
        if missing_deps:
            try:
                self._timeline.mark(
                    'startup_chat_bridge_deferred',
                    source=source,
                    reason='deferred_ui_batch_1_pending',
                    missing_dependencies=missing_deps,
                )
            except Exception:
                pass
            return False

        try:
            self._timeline.mark('startup_chat_bridge_priority_requested', source=source)
        except Exception:
            pass
        try:
            self._ensure_vm_for_route('control')
        except Exception:
            logger.exception('startup chat bridge priority build failed')
            try:
                self._tracer.trace(
                    'startup_chat_bridge_unavailable',
                    source=source,
                    reason='control_vm_build_failed',
                )
            except Exception:
                pass
            return False

        ready = getattr(self, 'control_center_viewmodel', None) is not None
        if ready:
            try:
                ctx.setContextProperty(
                    'controlCenterViewModel',
                    self.control_center_viewmodel,
                )
            except Exception:
                logger.debug('startup chat bridge context update failed', exc_info=True)
            bridge = getattr(self, 'ui_bridge_server', None)
            if bridge is not None:
                try:
                    self._mark_late_ui_bridge_ready_if_shell_is_visible(bridge)
                except Exception:
                    logger.debug('startup chat bridge late-ready mark failed', exc_info=True)
        else:
            try:
                self._tracer.trace(
                    'startup_chat_bridge_unavailable',
                    source=source,
                    reason='control_vm_missing_after_build',
                )
            except Exception:
                pass
        return ready

    def _fire_splash_ready_and_raise_main(self, source: str) -> None:
        """Common path: ``splash.set_ready()`` + raise/activate main_win.

        Used by both honest (``_handle_shell_loader_ready``) and
        fallback (``_force_splash_ready_fallback``) entry points.

        Also notifies the UIBridgeServer that the shell is interactive
        so it can flush any messages buffered during the splash phase
        (Task 2: readiness handshake).
        """
        splash = getattr(self, '_splash', None)
        if splash is not None:
            try:
                splash.set_ready()
                self._timeline.mark('splash_set_ready', source=source)
            except Exception:
                logger.exception('splash.set_ready fallo desde %s', source)
        # Mark startup complete for the heartbeat watchdog.
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is not None:
            watchdog.set_startup_active(False)
        # Notify bridge that the shell is interactive (Task 2 handshake).
        bridge = getattr(self, 'ui_bridge_server', None)
        if bridge is not None:
            try:
                bridge.mark_shell_ready(source)
            except Exception:
                logger.debug('bridge.mark_shell_ready failed from %s', source, exc_info=True)
        self._raise_main_window_now(source)

    def _raise_main_window(self) -> None:
        """Public callback for systray 'Show IABV' action."""
        self._raise_main_window_now('systray_show')

    def _raise_main_window_now(self, source: str) -> None:
        """Fuerza Z-order del main window por encima del splash.

        En Windows pythonw.exe, ``Qt.SplashScreen | Qt.WindowStaysOnTopHint``
        del splash a veces hace que el main window quede debajo aunque
        ``main_win.show()`` ya se llamo.  Reaplicamos ``raise_()`` y
        ``activateWindow()`` cuando llegan los hitos honestos.

        Adicionalmente, en Windows, si el proceso fue lanzado con
        ``Start-Process -WindowStyle Hidden`` (que setea
        ``STARTUPINFO.wShowWindow = SW_HIDE``), el primer
        ``ShowWindow()`` que Qt hace es overrideado por el OS con
        ``SW_HIDE``.  Reaplicamos ``ShowWindow(hwnd, SW_SHOW)`` via
        ctypes para forzar visibilidad independientemente del
        ``STARTUPINFO`` del proceso padre.
        """
        main_win = getattr(self, '_main_win', None)
        if main_win is None:
            return
        try:
            main_win.raise_()
            try:
                main_win.requestActivate()
            except Exception:
                pass
            self._force_win32_visibility(main_win, source)
            self._timeline.mark('main_window_raised_after_ready', source=source)
        except Exception:
            logger.exception('main_win.raise_/activate fallo desde %s', source)

    def _force_win32_visibility(self, window: object, source: str) -> None:
        """Fuerza visibilidad Win32 del HWND nativo via ctypes.

        Cuando ``Start-Process -WindowStyle Hidden`` lanza el proceso,
        Windows setea ``STARTUPINFO.wShowWindow = SW_HIDE``.  El primer
        ``ShowWindow(hwnd, nCmdShow)`` que Qt invoca es overrideado por
        el OS con ``SW_HIDE`` en lugar del ``SW_SHOW`` que Qt pide.

        Esta funcion llama ``ShowWindow(hwnd, SW_SHOW)`` una segunda
        vez (que ya no es overrideada) para hacer visible el HWND.
        Tambien llama ``SetForegroundWindow`` para traerlo al frente.

        En plataformas no-Windows es un no-op.
        """
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            hwnd = int(window.winId())
            if not hwnd:
                self._timeline.mark(
                    'win32_force_visibility_skip',
                    source=source,
                    reason='winId_is_zero',
                )
                return
            user32 = ctypes.windll.user32
            SW_SHOW = 5
            SW_SHOWNORMAL = 1
            was_visible = user32.ShowWindow(hwnd, SW_SHOWNORMAL)
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.SetForegroundWindow(hwnd)
            self._timeline.mark(
                'win32_force_visibility_done',
                source=source,
                hwnd=hwnd,
                was_visible=bool(was_visible),
            )
        except Exception:
            logger.exception(
                'win32_force_visibility fallo desde %s', source,
            )

    def _connect_window_lifecycle_signals(self, window: object) -> None:
        """Conecta senales de ciclo de vida de la ventana principal al timeline.

        Instrumenta: visibleChanged, activeChanged, closing, y
        screenChanged para que el JSONL muestre exactamente que pasa
        con la ventana nativa en Windows.  Si la ventana se oculta, se
        destruye o cambia de screen, queda registrado.
        """
        try:
            window.visibleChanged.connect(
                lambda visible: self._on_window_lifecycle(
                    'visibleChanged', visible=visible,
                )
            )
        except Exception:
            pass
        try:
            window.activeChanged.connect(
                lambda: self._on_window_lifecycle(
                    'activeChanged',
                    active=window.isActive() if hasattr(window, 'isActive') else None,
                )
            )
        except Exception:
            pass
        try:
            window.closing.connect(
                lambda close_event: self._on_window_lifecycle(
                    'closing',
                )
            )
        except Exception:
            pass
        try:
            window.screenChanged.connect(
                lambda screen: self._on_window_lifecycle(
                    'screenChanged',
                    screen_name=screen.name() if screen and hasattr(screen, 'name') else None,
                )
            )
        except Exception:
            pass
        # Log initial state
        try:
            wid = int(window.winId()) if hasattr(window, 'winId') else 0
            top_level_count = 0
            try:
                from PySide6.QtGui import QGuiApplication as _QGA
                top_level_count = len(_QGA.topLevelWindows())
            except Exception:
                pass
            self._timeline.mark(
                'window_lifecycle_connected',
                winId=wid,
                visible=window.isVisible() if hasattr(window, 'isVisible') else None,
                top_level_windows=top_level_count,
            )
        except Exception:
            pass

    @staticmethod
    def _window_lifecycle_signal_value(event_name: str, data: dict[str, object]) -> object:
        if event_name == 'activeChanged':
            return data.get('active')
        if event_name == 'visibleChanged':
            return data.get('visible')
        if event_name == 'screenChanged':
            return data.get('screen_name')
        return None

    def _should_mark_window_lifecycle(
        self,
        event_name: str,
        data: dict[str, object],
    ) -> tuple[bool, str]:
        """Return whether this window lifecycle event should hit the timeline.

        Window active/visible signals can fire in bursts while Windows is
        restoring, minimizing or focus-cycling. The watchdog still receives
        every signal, but timeline/logging work is coalesced to protect the
        Qt main thread.
        """
        now = time.perf_counter()
        recent = getattr(self, '_window_lifecycle_recent', [])
        window_s = self._WINDOW_LIFECYCLE_STORM_WINDOW_S
        recent = [t for t in recent if now - t <= window_s]
        recent.append(now)
        self._window_lifecycle_recent = recent

        storm_until = float(getattr(self, '_window_lifecycle_storm_until', 0.0))
        if now < storm_until:
            self._trace_window_lifecycle_guard(
                event_name,
                reason='storm_cooldown',
                count=len(recent),
            )
            return False, 'storm_cooldown'

        if len(recent) > self._WINDOW_LIFECYCLE_STORM_LIMIT:
            self._window_lifecycle_storm_until = now + self._WINDOW_LIFECYCLE_STORM_COOLDOWN_S
            self._trace_window_lifecycle_guard(
                event_name,
                reason='storm_guarded',
                count=len(recent),
            )
            return False, 'storm_guarded'

        value = self._window_lifecycle_signal_value(event_name, data)
        duplicate_key = event_name
        last_by_key = getattr(self, '_window_lifecycle_last', {})
        last_t, last_value = last_by_key.get(duplicate_key, (0.0, object()))
        if (
            event_name in {'activeChanged', 'visibleChanged', 'screenChanged'}
            and value == last_value
            and now - last_t < self._WINDOW_LIFECYCLE_DUPLICATE_COOLDOWN_S
        ):
            self._trace_window_lifecycle_guard(
                event_name,
                reason='duplicate_coalesced',
                count=len(recent),
            )
            return False, 'duplicate_coalesced'
        last_by_key[duplicate_key] = (now, value)
        self._window_lifecycle_last = last_by_key
        return True, ''

    def _trace_window_lifecycle_guard(self, event_name: str, *, reason: str, count: int) -> None:
        now = time.perf_counter()
        last = float(getattr(self, '_window_lifecycle_last_guard_trace', 0.0))
        if now - last < self._WINDOW_LIFECYCLE_TRACE_COOLDOWN_S:
            return
        self._window_lifecycle_last_guard_trace = now
        try:
            self._tracer.trace(
                'window_lifecycle_storm_guarded',
                event_name=event_name,
                reason=reason,
                recent_count=count,
                window_s=self._WINDOW_LIFECYCLE_STORM_WINDOW_S,
                cooldown_s=self._WINDOW_LIFECYCLE_STORM_COOLDOWN_S,
                rss_mb=round(_rss_mb(), 1),
            )
        except Exception:
            pass

    def _trace_own_window_offscreen(self, rect: dict[str, int | None]) -> None:
        now = time.perf_counter()
        last = float(getattr(self, '_own_window_offscreen_last_trace', 0.0))
        if now - last < 30.0:
            return
        self._own_window_offscreen_last_trace = now
        try:
            self._tracer.trace(
                'own_window_offscreen',
                rect=rect,
                reason='window_rect_negative_sentinel',
                action_hint='restore_iabv_window_before_visual_proof',
            )
        except Exception:
            pass

    def _on_window_lifecycle(self, event_name: str, **kwargs: object) -> None:
        """Registra un evento de ciclo de vida de la ventana en el timeline."""
        should_mark, guard_reason = self._should_mark_window_lifecycle(event_name, dict(kwargs))
        try:
            if should_mark:
                main_win = getattr(self, '_main_win', None)
                extra = dict(kwargs)
                if guard_reason:
                    extra['guard_reason'] = guard_reason
                if main_win is not None:
                    try:
                        extra['winId'] = int(main_win.winId())
                    except Exception:
                        pass
                    try:
                        extra['visible'] = main_win.isVisible()
                    except Exception:
                        pass
                    try:
                        x = int(main_win.x()) if hasattr(main_win, 'x') else None
                        y = int(main_win.y()) if hasattr(main_win, 'y') else None
                        width = int(main_win.width()) if hasattr(main_win, 'width') else None
                        height = int(main_win.height()) if hasattr(main_win, 'height') else None
                        rect = {'left': x, 'top': y, 'width': width, 'height': height}
                        extra['rect'] = rect
                        if (x is not None and x <= -30000) or (y is not None and y <= -30000):
                            self._trace_own_window_offscreen(rect)
                    except Exception:
                        pass
                    try:
                        from PySide6.QtGui import QGuiApplication as _QGA
                        extra['top_level_windows'] = len(_QGA.topLevelWindows())
                    except Exception:
                        pass
                self._timeline.mark(f'window_{event_name}', **extra)
        except Exception:
            pass
        # Propagate window visibility and activity as SEPARATE states.
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        vm = getattr(self, 'control_center_viewmodel', None)
        if event_name == 'visibleChanged':
            is_visible = bool(kwargs.get('visible', True))
            if watchdog is not None:
                try:
                    watchdog.set_window_visible(is_visible)
                except Exception:
                    pass
        elif event_name == 'activeChanged':
            is_active = bool(kwargs.get('active', True))
            if watchdog is not None:
                try:
                    watchdog.set_window_active(is_active)
                except Exception:
                    pass
            # Record window inactive/active intervals in the interaction.
            if vm is not None:
                iid = getattr(vm, '_active_interaction_id', None)
                lc = getattr(vm, '_chat_interaction_lifecycle', None)
                if iid and lc is not None:
                    try:
                        if is_active:
                            lc.record_window_active(iid)
                        else:
                            lc.record_window_inactive(iid)
                    except Exception:
                        pass

    def _force_splash_ready_fallback(self) -> None:
        """Fallback determinista si QML nunca emite ``shellLoaderReady``.

        Llamado via ``QTimer.singleShot`` despues de un timeout
        (configurable via ``IABV_SHELL_READY_FALLBACK_MS``, default
        5000 ms).  Marca el hito como ``shell_loader_ready_fallback``
        para que la auditoria distinga un cierre honesto de uno por
        timeout.  De este modo el splash siempre cierra: nunca se queda
        congelado por una conexion QML que no llego.

        Also records ``_shell_loader_wall_clock_ms`` — the wall-clock
        elapsed since ``app_exec_about_to_start`` — so OSES can detect
        event-loop starvation (when ``wall_clock >> timer_ms``, the main
        thread was blocked by QML incubation and couldn't process the
        QTimer until it unblocked).

        Skipped if ``_shell_loader_ready_handled`` is already True
        (honest shell signal or page_loader_ready already closed the
        splash).  ``page_loader_ready`` sets this flag because it is
        the MORE honest readiness hito — the user already sees content.
        """
        if getattr(self, '_shell_loader_ready_handled', False):
            return

        # Wall-clock measurement: detect event-loop starvation
        import time as _time
        wall_ms = 0.0
        t0 = getattr(self, '_shell_ready_wall_t0', None)
        if t0 is not None:
            wall_ms = (_time.perf_counter() - t0) * 1000.0

        expected_ms = getattr(self, '_shell_ready_fallback_ms', 5000)
        starvation = wall_ms > expected_ms * 2 if wall_ms > 0 else False

        if starvation:
            logger.warning(
                'shell_loader_ready fallback: wall_clock=%.0fms vs '
                'timer=%dms — event loop was starved (QML incubation '
                'blocked main thread for %.0fs)',
                wall_ms, expected_ms, (wall_ms - expected_ms) / 1000.0,
            )
        else:
            logger.warning(
                'shell_loader_ready no llego en el timeout esperado '
                '(%dms); forzando cierre del splash via fallback',
                expected_ms,
            )

        self._shell_loader_ready_handled = True
        try:
            self._timeline.mark(
                'shell_loader_ready_fallback',
                wall_clock_ms=round(wall_ms, 1),
                expected_ms=expected_ms,
                event_loop_starved=starvation,
            )
        except Exception:
            pass
        self._fire_splash_ready_and_raise_main('shell_loader_ready_fallback')
        # Safety net: if page_loader_ready never arrived, ensure Phase 3
        # VMs still get built eventually (degraded but functional).
        self._schedule_pending_deferred_2()

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
        _lock_errors: list[str] = []

        def _probe_group(group_cards: list) -> list[tuple[str, bool, Any]]:
            out: list[tuple[str, bool, Any]] = []
            for c in group_cards:
                refreshed = self.tool_registry.refresh_card(
                    c, max_age_seconds=60.0,
                )
                out.append((refreshed.tool_id, refreshed.available, refreshed))
            return out

        max_workers = min(len(adapter_groups), 4) or 1
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
                    if 'database is locked' in str(exc):
                        _lock_errors.append(str(exc))

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
                    try:
                        self.tool_registry.repository.save_card(stamped)
                    except Exception as save_exc:
                        logger.warning('tool_probe save_card failed: %s', save_exc)
                        if 'database is locked' in str(save_exc):
                            _lock_errors.append(str(save_exc))
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
        self._tracer.trace(
            'tool_availability',
            ready=sorted(ready),
            missing=sorted(missing),
            total=len(cards),
        )

        # Stash missing tools for deferred auto-install (Phase B).
        # Auto-install is moved out of the critical tool-probe path so
        # tool availability results are available faster (Task 6).
        self._deferred_missing_tools = list(missing)

        if _lock_errors:
            self._record_startup_sqlite_incident(
                Exception(f'database is locked ({len(_lock_errors)} occurrence(s) during tool probes)')
            )

        # Bridge missing tools → pending queue so the program knows
        # what it cannot do and surfaces it as actionable work.
        self._seed_missing_tools_as_pending(missing, ready)

    @staticmethod
    def _read_with_retry(
        fn: 'Callable[[], _T]',
        *,
        max_retries: int = 3,
        base_delay: float = 0.25,
    ) -> '_T':
        """Execute *fn* with exponential-backoff retry on SQLite lock errors.

        Intended for read-only helpers called during bootstrap
        (``_log_tool_availability``, ``_startup_self_examination``, etc.)
        where a transient ``database is locked`` should not crash the
        entire startup sequence.

        Raises the last exception if all retries are exhausted.
        Non-lock errors are raised immediately without retry.
        """
        import sqlite3
        import time as _time

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return fn()
            except (sqlite3.OperationalError, OSError) as exc:
                if 'database is locked' not in str(exc):
                    raise
                last_exc = exc
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    _time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _record_startup_sqlite_incident(self, exc: Exception) -> None:
        """Promote a ``database is locked`` error to an OSES finding.

        Called from ``_bg_post_window_setup`` when
        ``_log_tool_availability`` fails with a SQLite contention error.
        The finding is persisted as a JSON file under
        ``data/evolution/self_examination/`` so that the next
        ``build_review()`` picks it up via ``_runtime_log_findings`` or
        the startup health pipeline.
        """
        if 'database is locked' not in str(exc):
            return
        try:
            incident_dir = Path(self.config.evolution_dir) / 'self_examination'
            incident_dir.mkdir(parents=True, exist_ok=True)
            incident_path = incident_dir / 'startup_sqlite_incident.json'
            import json
            from datetime import datetime, timezone
            incident = {
                'category': 'sqlite_lock_contention',
                'title': 'database is locked durante startup',
                'summary': (
                    f'deferred_tool_availability_probe fallo con: {exc}. '
                    'La contención ocurre porque UI y MCP intentan escribir '
                    'en app.sqlite simultáneamente durante arranque.'
                ),
                'severity': 'HIGH',
                'confidence': 0.95,
                'recommendation': (
                    'Verificar que WAL mode y busy_timeout estén activos. '
                    'Separar writes de _seed_defaults del arranque MCP.'
                ),
                'source_refs': [
                    'iabv_v15.infra.persistence.database',
                    'iabv_v15.services.tools.tool_registry._seed_defaults',
                ],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(exc),
            }
            incident_path.write_text(
                json.dumps(incident, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
            logger.info('startup_sqlite_incident: persisted to %s', incident_path)
        except Exception as persist_exc:
            logger.warning('startup_sqlite_incident: failed to persist: %s', persist_exc)

    def _seed_missing_tools_as_pending(
        self,
        missing: list[str],
        ready: list[str],
    ) -> None:
        """Create PENDING tasks for tools that probes found unavailable.

        Ready tools are marked COMPLETED so the queue reflects the true
        state of the environment.  This bridges ToolRegistry probes with
        the autonomy pending queue.
        """
        try:
            queue = getattr(self, 'platform_pending_queue', None)
            if queue is None:
                return
            from iabv_v15.domain.models import PendingTaskStatus, PlatformPendingTask
            from iabv_v15.services.evolution.platform_pending_queue import CATEGORY_MISSING_TOOL
            for tool_id in missing:
                task_id = f'tool_{tool_id}'
                existing = queue.get(task_id)
                if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                    continue
                guidance = self._TOOL_INSTALL_GUIDANCE.get(tool_id, '')
                queue.upsert(PlatformPendingTask(
                    id=task_id,
                    title=f'Herramienta no disponible: {tool_id}',
                    description=f'{tool_id} no fue detectada en el entorno.',
                    reason='tool_probe returned unavailable',
                    dependency_missing=guidance or tool_id,
                    priority='medium',
                    next_action=guidance or f'Instalar o configurar {tool_id}',
                    status=PendingTaskStatus.PENDING,
                    category=CATEGORY_MISSING_TOOL,
                ))
            for tool_id in ready:
                task_id = f'tool_{tool_id}'
                existing = queue.get(task_id)
                if existing is not None and existing.status != PendingTaskStatus.COMPLETED:
                    queue.mark_status(task_id, PendingTaskStatus.COMPLETED)
        except Exception:
            logger.debug('seed_missing_tools: failed', exc_info=True)

    def _run_startup_common_sense(self) -> None:
        """Run common-sense reasoning over startup timeline events.

        Reads the startup timeline to build a ``timeline_data`` dict with
        wire_services_ms, populate_ui_ms, rss_growth_mb, then passes it
        through ``run_common_sense_reasoning`` in dry-run mode.  Any rules
        that fire are logged so the metacognition loop is aware of startup
        anomalies without executing corrective actions (those are handled
        by the fixes themselves).
        """
        if os.environ.get('IABV_MCP_SUBPROCESS') == '1':
            return
        try:
            from iabv_v15.services.common_sense_engine import (
                run_common_sense_reasoning,
            )
        except ImportError:
            return

        timeline_events = self._timeline.events()
        timeline_data: dict[str, Any] = {}

        # Extract wire_services duration
        wire_start = None
        wire_end = None
        populate_start = None
        populate_end = None
        for ev in timeline_events:
            phase = ev.get('phase', '')
            elapsed = ev.get('elapsed_ms', 0)
            if phase == 'wire_services_start':
                wire_start = elapsed
            elif phase == 'wire_services_done':
                wire_end = elapsed
            elif phase == 'populate_ui_start':
                populate_start = elapsed
                timeline_data['populate_ui_started'] = True
            elif phase == 'populate_ui_done':
                populate_end = elapsed
                timeline_data['populate_ui_done'] = True

        if wire_start is not None and wire_end is not None:
            timeline_data['wire_services_ms'] = wire_end - wire_start
        if populate_start is not None and populate_end is not None:
            timeline_data['populate_ui_ms'] = populate_end - populate_start

        # RSS growth: check if recorded in timeline extras
        for ev in timeline_events:
            rss = ev.get('rss_growth_mb')
            if rss is not None:
                timeline_data['rss_growth_mb'] = rss

        # QML layer facts: detect fallback usage and event loop starvation
        for ev in timeline_events:
            phase = ev.get('phase', '')
            if phase == 'shell_loader_ready_fallback':
                timeline_data['shell_loader_fallback_used'] = True
                if ev.get('event_loop_starved'):
                    timeline_data['event_loop_starved'] = True

        if not timeline_data:
            return

        try:
            result = run_common_sense_reasoning(
                deep_env_scan={'startup_timeline': timeline_data},
                execute=False,
                dry_run=True,
            )
            fired = result.get('fired_rules', [])
            for rule in fired:
                rid = rule.get('id', '?')
                sev = rule.get('severity', 'medium')
                conclusion = rule.get('conclusion', '')
                logger.info(
                    'startup_common_sense [%s]: %s → %s',
                    sev, rid, conclusion,
                )
            if fired:
                logger.info(
                    'startup_common_sense: %d rules fired from timeline',
                    len(fired),
                )
        except Exception as exc:
            logger.debug('startup_common_sense: skipped (%s)', exc)

    def _startup_self_examination(self) -> None:
        """Run a lightweight self-examination at startup.

        Executes the perception cross-validator (if wired) to detect
        UI anomalies (zombie windows, missing IABV window, duplicates)
        and logs the results. This gives the program self-awareness
        about its own state immediately after boot.

        Also runs ``_startup_health_findings()`` from OSES to detect
        startup degradation (populate_ui freeze, RSS growth, false ready,
        shell readiness latency). Without this, those findings only appear
        when ``build_review()`` is called on-demand, which means the
        program never auto-detects its own startup freeze.
        """
        if os.environ.get('IABV_MCP_SUBPROCESS') == '1':
            return
        validator = getattr(self, 'perception_cross_validator', None)
        if validator is not None:
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

        oses = getattr(self, 'operational_self_examination_service', None)
        if oses is not None and hasattr(oses, '_startup_health_findings'):
            try:
                startup_findings = oses._startup_health_findings()
                for f in startup_findings:
                    sev = getattr(f, 'severity', None) or 'UNKNOWN'
                    title = getattr(f, 'title', '') or str(f)
                    cat = getattr(f, 'category', '') or ''
                    rec = getattr(f, 'recommendation', '') or ''
                    if str(sev) in ('CRITICAL', 'HIGH'):
                        logger.warning(
                            'startup_health [%s|%s]: %s | fix: %s',
                            sev, cat, title, rec,
                        )
                    else:
                        logger.info(
                            'startup_health [%s|%s]: %s',
                            sev, cat, title,
                        )
                if startup_findings:
                    logger.info(
                        'startup_health: %d findings detected at boot',
                        len(startup_findings),
                    )
            except Exception as exc:
                logger.debug('startup_health_findings: skipped (%s)', exc)

        # Log actionable resume hints and pending tasks so the next
        # session (or agent) knows exactly what was left incomplete.
        acs = getattr(self, 'autonomy_cycle_service', None)
        if acs is not None:
            try:
                summary = acs.startup_summary()
                hints = summary.get('resume_hints', [])
                actionable = summary.get('actionable_tasks', [])
                blocked = summary.get('blocked_tasks', [])
                if hints:
                    for h in hints[:5]:
                        logger.info(
                            'resume_hint: task=%s phase=%s last_step=%s handoff=%s',
                            h.get('task_id', ''), h.get('checkpoint_phase', ''),
                            h.get('last_step', '')[:80], h.get('handoff_required', False),
                        )
                if actionable:
                    logger.info(
                        'autonomy_pending: %d actionable tasks (top: %s)',
                        len(actionable),
                        ', '.join(t.get('title', '')[:40] for t in actionable[:3]),
                    )
                if blocked:
                    logger.info(
                        'autonomy_blocked: %d blocked tasks (top: %s)',
                        len(blocked),
                        ', '.join(t.get('title', '')[:40] for t in blocked[:3]),
                    )
            except Exception as exc:
                logger.debug('autonomy_startup_summary: skipped (%s)', exc)

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

    @staticmethod
    def _yield_to_event_loop() -> None:
        """Pump the Qt event loop once to keep the UI responsive.

        Called between heavy VM constructions in ``_build_ui_objects``
        so that the splash/window can repaint and Windows doesn't mark
        the process as Not Responding during startup (Fix 20b).
        """
        try:
            _app = QGuiApplication.instance()
            if _app is not None:
                _app.processEvents()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Phased VM construction
    # ------------------------------------------------------------------
    # populate_ui is split into three batches so that QTimer.singleShot(0)
    # returns control to the Qt event loop between each batch.  This lets
    # the QML async incubator (mainShellLoader / pageLoader) progress to
    # Ready and emit the honest shell_loader_ready signal *before* the
    # fallback timer fires.
    #
    # Phase 1 (critical): nav + theme + bridge + dashboard — minimum
    #   needed for the initial page to render.
    # Phase 2 (deferred-1): MCP side-effects + ControlCenter + Capture
    # Phase 3 (deferred-2): Evolution + Knowledge + Provider + RunHistory
    #   + CentroVivo + signal wiring
    # ------------------------------------------------------------------

    def _build_critical_ui_objects(self) -> None:
        """Phase 1: build VMs needed for first paint (Dashboard)."""
        if self.navigation_controller is not None:
            return
        if PYSIDE_AVAILABLE and QGuiApplication.instance() is None:
            self._ui_app = QApplication(sys.argv)

        try:
            self._timeline.mark('populate_ui_vm_navigation')
        except Exception:
            pass
        self.navigation_controller = NavigationController()
        self.theme_controller = ThemeController(self.theme)
        self.main_window_bridge = MainWindowBridge(self.config.app_name, self.config.workspace_root)
        try:
            self.main_window_bridge.shellLoaderReady.connect(
                self._handle_shell_loader_ready
            )
        except Exception:
            logger.exception('No se pudo conectar shellLoaderReady -> _handle_shell_loader_ready')
        try:
            self.main_window_bridge.qmlLoaderEvent.connect(
                self._handle_qml_loader_event
            )
        except Exception:
            logger.exception('No se pudo conectar qmlLoaderEvent -> _handle_qml_loader_event')
        try:
            self.main_window_bridge.mainQmlCompleted.connect(
                self._handle_main_qml_completed
            )
        except Exception:
            logger.exception('No se pudo conectar mainQmlCompleted -> _handle_main_qml_completed')
        try:
            self.main_window_bridge.pageLoaderReady.connect(
                self._handle_page_loader_ready
            )
        except Exception:
            logger.exception('No se pudo conectar pageLoaderReady -> _handle_page_loader_ready')
        try:
            self.main_window_bridge.splashClosing.connect(
                self._handle_splash_closing
            )
        except Exception:
            logger.exception('No se pudo conectar splashClosing -> _handle_splash_closing')
        self._yield_to_event_loop()

        try:
            self._timeline.mark('populate_ui_vm_dashboard')
        except Exception:
            pass
        self.dashboard_viewmodel = DashboardViewModel(
            self.episode_repository,
            self.knowledge_repository,
            self.run_repository,
            self.role_router,
            self.embedding_service,
            defer_initial_refresh=True,
        )
        self._yield_to_event_loop()

    def _build_deferred_ui_batch_1(self) -> None:
        """Phase 2: MCP side-effects only (lightweight services).

        ControlCenterVM and CaptureStudioVM are now lazy — built
        on-demand when the user navigates to their page, or pre-built
        during idle 15 s after boot.  This eliminates the 82 s main
        thread block observed in the Windsurf v2 audit.
        """
        try:
            self._timeline.mark('populate_ui_vm_mcp_side_effects')
        except Exception:
            pass
        # --- MCP bridge ---
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
        # --- UIBridgeService ---
        if getattr(self, 'ui_bridge_server', None) is None:
            try:
                from iabv_v15.services.ui_bridge_service import (
                    build_ui_bridge_server,
                )
                self.ui_bridge_server = build_ui_bridge_server()
            except Exception:
                logger.exception('No se pudo construir UIBridgeServer; bridge UI desactivado')
                self.ui_bridge_server = None
        # --- UIScreenshotProvider ---
        if getattr(self, 'ui_screenshot_provider', None) is None:
            try:
                from iabv_v15.infra.ui import build_ui_screenshot_provider
                self.ui_screenshot_provider = build_ui_screenshot_provider()
            except Exception:
                logger.exception('No se pudo construir ui_screenshot_provider; dejando None')
                self.ui_screenshot_provider = None
        # --- ChatCapabilityIngestionService ---
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

        # ControlCenterVM and CaptureStudioVM are now lazy (see
        # _ROUTE_TO_VM_ATTR).  UIBridgeServer wiring happens inside
        # _build_control_center_vm() when the VM is actually built.

    # ------------------------------------------------------------------
    # Lazy VM construction — ALL non-critical VMs (ControlCenter,
    # CaptureStudio, EvolutionCenter, KnowledgeBase, ProviderSettings,
    # RunHistory, CentroVivo) are built on-demand when the user
    # navigates to their page, or pre-built during idle 15 s after
    # boot.  Only Dashboard + Nav + Theme + Bridge are built eagerly.
    # This keeps the main thread responsive (Responding=True) and
    # avoids the 82 s block that caused Windows "Not Responding".
    # ------------------------------------------------------------------

    _ROUTE_TO_VM_ATTR: dict[str, str] = {
        'control': 'control_center_viewmodel',
        'capture': 'capture_studio_viewmodel',
        'evolution': 'evolution_center_viewmodel',
        'knowledge': 'knowledge_base_viewmodel',
        'providers': 'provider_settings_viewmodel',
        'runs': 'run_history_viewmodel',
        'centro_vivo': 'centro_vivo_viewmodel',
    }

    def _ensure_vm_for_route(self, route: str) -> None:
        """Lazily construct the VM for *route* if it hasn't been built yet.

        Called from the ``currentRouteChanged`` listener installed by
        ``_populate_ui_deferred_2``.  Each VM is built exactly once;
        subsequent navigations to the same page are no-ops.
        """
        attr = self._ROUTE_TO_VM_ATTR.get(route)
        if attr is None:
            return  # Phase 1 VM (dashboard) — already built
        if getattr(self, attr, None) is not None:
            return  # already constructed
        ctx = getattr(self, '_qml_root_context', None)
        if ctx is None:
            return
        try:
            self._timeline.mark(f'lazy_vm_{route}_start')
        except Exception:
            pass
        if route == 'control':
            self._build_control_center_vm()
            ctx.setContextProperty('controlCenterViewModel', self.control_center_viewmodel)
        elif route == 'capture':
            self._build_capture_studio_vm()
            ctx.setContextProperty('captureStudioViewModel', self.capture_studio_viewmodel)
        elif route == 'evolution':
            self._build_evolution_center_vm()
            ctx.setContextProperty('evolutionCenterViewModel', self.evolution_center_viewmodel)
        elif route == 'knowledge':
            self._build_knowledge_base_vm()
            ctx.setContextProperty('knowledgeBaseViewModel', self.knowledge_base_viewmodel)
        elif route == 'providers':
            self._build_provider_settings_vm()
            ctx.setContextProperty('providerSettingsViewModel', self.provider_settings_viewmodel)
        elif route == 'runs':
            self._build_run_history_vm()
            ctx.setContextProperty('runHistoryViewModel', self.run_history_viewmodel)
        elif route == 'centro_vivo':
            self._build_centro_vivo_vm()
            ctx.setContextProperty('centroVivoViewModel', self.centro_vivo_viewmodel)
        try:
            self._timeline.mark(f'lazy_vm_{route}_done')
        except Exception:
            pass
        logger.info('lazy_vm_constructed: %s', route)

    def _build_control_center_vm(self) -> None:
        if getattr(self, 'control_center_viewmodel', None) is not None:
            return
        try:
            self._timeline.mark('startup_chat_bridge_priority_granted')
        except Exception:
            pass
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
            chat_message_repository=self.chat_message_repository,
            reflection_routing_service=self.reflection_routing_service,
            defer_initial_refresh=True,
        )
        self.control_center_viewmodel.resource_metacognition_service = self.resource_metacognition_service
        self.control_center_viewmodel.decision_audit_trail = self.decision_audit_trail
        self.control_center_viewmodel._freeze_incident_reporter = self.freeze_incident_reporter
        self.control_center_viewmodel._ui_heartbeat_watchdog = self.ui_heartbeat_watchdog
        self.control_center_viewmodel._chat_interaction_lifecycle = self.chat_interaction_lifecycle
        self.control_center_viewmodel._oses_ref = self.operational_self_examination_service
        self.control_center_viewmodel._portable_context_ref = self.portable_context_service
        # Wire CaptureStudioVM reference if already built.
        csvm = getattr(self, 'capture_studio_viewmodel', None)
        if csvm is not None:
            self.control_center_viewmodel.capture_studio_viewmodel = csvm
        # Wire UIBridgeServer now that the VM exists — start on a
        # background thread to avoid blocking the main thread during
        # lazy VM prebuild.
        if getattr(self, 'ui_bridge_server', None) is not None:
            ccvm_ref = self.control_center_viewmodel

            def _start_bridge() -> None:
                try:
                    from iabv_v15.services.ui_bridge_service import (
                        build_ui_bridge_server,
                    )
                    bridge = build_ui_bridge_server(
                        control_center_viewmodel=ccvm_ref,
                    )
                    self.ui_bridge_server = bridge
                    bridge.start()
                    self._mark_late_ui_bridge_ready_if_shell_is_visible(bridge)
                    self._mark_startup_chat_bridge_ready('control_vm_bridge_start', bridge)
                    logger.info('UIBridgeServer started with ControlCenterViewModel')
                except Exception:
                    logger.exception('UIBridgeServer failed to start with VM wiring')
                    try:
                        self._tracer.trace(
                            'startup_chat_bridge_unavailable',
                            source='control_vm_bridge_start',
                            reason='bridge_start_failed',
                        )
                    except Exception:
                        pass
                    self.ui_bridge_server = None

            threading.Thread(
                target=_start_bridge,
                name='ui-bridge-start',
                daemon=True,
            ).start()

    def _build_capture_studio_vm(self) -> None:
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
            defer_initial_refresh=True,
        )
        # Wire back-reference if ControlCenterVM already built.
        ccvm = getattr(self, 'control_center_viewmodel', None)
        if ccvm is not None:
            ccvm.capture_studio_viewmodel = self.capture_studio_viewmodel

    def _build_evolution_center_vm(self) -> None:
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
            defer_initial_refresh=True,
        )
        self.evolution_center_viewmodel.proactive_dashboard_service = self.proactive_dashboard_service
        self.evolution_center_viewmodel.human_approval_broker = self.human_approval_broker
        self.evolution_center_viewmodel.approval_memory = self.approval_memory
        self.evolution_center_viewmodel.ui_screenshot_service = self.ui_screenshot_service

    def _build_knowledge_base_vm(self) -> None:
        self.knowledge_base_viewmodel = KnowledgeBaseViewModel(
            self.knowledge_repository,
            defer_initial_refresh=True,
        )

    def _build_provider_settings_vm(self) -> None:
        self.provider_settings_viewmodel = ProviderSettingsViewModel(
            self.provider_configs,
            self.role_router,
            self.embedding_service,
            defer_initial_refresh=True,
        )

    def _build_run_history_vm(self) -> None:
        self.run_history_viewmodel = RunHistoryViewModel(
            self.run_repository,
            self.execution_dossier_repository,
            session_repository=self.adaptive_session_repository,
            defer_initial_refresh=True,
        )

    def _build_centro_vivo_vm(self) -> None:
        self.centro_vivo_viewmodel = CentroVivoViewModel(
            adaptive_session_repository=self.adaptive_session_repository,
            experiment_lab_repository=self.experiment_lab_repository,
            tool_record_repository=self.tool_record_repository,
            world_model_service=self.world_model_service,
            self_examination_service=self.operational_self_examination_service,
            portable_context_service=self.portable_context_service,
            evolution_review_service=self.evolution_review_service,
            data_root=self.config.data_dir,
            defer_initial_refresh=True,
        )

    # -- Resource-governed lazy VM prebuild state --
    _prebuild_paused: bool = False
    _prebuild_paused_routes: list[str] = []

    # Pressure thresholds for pausing idle prebuild.
    _PREBUILD_RAM_PAUSE_THRESHOLDS: set[str] = {'high', 'critical'}
    _PREBUILD_CPU_PAUSE_THRESHOLDS: set[str] = {'high', 'critical'}
    _PREBUILD_STALL_LOOKBACK_S: float = 30.0
    # Cached snapshot is considered stale after this many seconds.
    _PREBUILD_SNAPSHOT_MAX_AGE_S: float = 60.0

    # -- Background startup phase tracking --
    # These flags track whether background startup tasks are still running.
    # Only user-visible birth work may hold the startup follow-up contract.
    # Metacognitive maintenance is idle-gated separately.
    _deferred_setup_active: bool = False
    _truth_refresh_active: bool = False
    _startup_chat_bridge_ready: bool = False
    _startup_evolution_active: bool = False
    _STARTUP_EVOLUTION_INITIAL_DELAY_MS: int = 120_000
    _STARTUP_EVOLUTION_RETRY_BASE_MS: int = 60_000
    _STARTUP_EVOLUTION_MAX_DEFERRALS: int = 6
    _STARTUP_EVOLUTION_MIN_FREE_MB: float = 4096.0
    _STARTUP_EVOLUTION_MAX_RAM_USED_PCT: float = 75.0

    # Extended startup: True until *all* background startup phases finish.
    # This is what the watchdog reads (startup_followup_active) to avoid
    # marking stalls as "startup_active=false" when boot work is ongoing.
    _startup_followup_active: bool = True

    def _check_startup_followup_done(self) -> None:
        """Clear ``_startup_followup_active`` when all background phases finish.

        Called from each background startup thread when it completes.
        Updates the watchdog so runtime_audit stalls carry the correct
        ``startup_active`` / ``startup_followup_active`` context.

        Resource snapshot refresh is not part of the birth contract.  It is
        maintenance input for idle prebuild and must not keep the first
        communication channel in "startup follow-up" mode.
        """
        self._push_bootstrap_flags_to_watchdog()
        if (self._deferred_setup_active
                or self._truth_refresh_active):
            return  # at least one phase still running
        self._startup_followup_active = False
        # Re-push flags AFTER clearing so bootstrap_flags dict and
        # top-level watchdog._startup_followup_active agree.
        self._push_bootstrap_flags_to_watchdog()
        logger.info('startup_followup_done: all background startup phases complete')

    def _push_bootstrap_flags_to_watchdog(self) -> None:
        """Push current background-phase flags to the watchdog for enrichment."""
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is None:
            return
        watchdog.set_startup_followup_active(self._startup_followup_active)
        watchdog.set_bootstrap_flags({
            'prebuild_paused': self._prebuild_paused,
            'deferred_setup_active': self._deferred_setup_active,
            'truth_refresh_active': self._truth_refresh_active,
            'startup_evolution_active': self._startup_evolution_active,
            'snapshot_refresh_in_flight': getattr(self, '_prebuild_snapshot_refresh_in_flight', False),
            'startup_followup_active': self._startup_followup_active,
        })

    # -- Timeline spam prevention --
    _PREBUILD_PAUSED_COOLDOWN_S: float = 10.0
    _prebuild_last_paused_key: str = ''
    _prebuild_last_paused_at: float = 0.0

    # ---- Cached resource snapshot (never read synchronously) --------

    def _init_prebuild_snapshot_cache(self) -> None:
        """Initialise the cache attributes (idempotent)."""
        if not hasattr(self, '_prebuild_resource_snapshot'):
            import threading
            self._prebuild_resource_snapshot: Any | None = None
            self._prebuild_resource_snapshot_at: float = 0.0
            self._prebuild_resource_snapshot_lock = threading.Lock()
            self._prebuild_snapshot_refresh_in_flight: bool = False

    def _refresh_prebuild_snapshot_async(self) -> None:
        """Kick off a background thread to refresh the cached snapshot.

        The thread calls ``take_resource_snapshot()`` (which may be slow
        on Windows — PowerShell/CIM subprocess) and stores the result
        under lock.  The UI thread never blocks on this call.

        **Coalescing:** If a refresh thread is already in-flight, this
        method returns immediately without spawning another thread.
        """
        self._init_prebuild_snapshot_cache()
        if self._prebuild_snapshot_refresh_in_flight:
            return  # coalesce: already refreshing
        self._prebuild_snapshot_refresh_in_flight = True
        self._push_bootstrap_flags_to_watchdog()
        import threading

        def _worker() -> None:
            try:
                from iabv_v15.services.intelligent_resource_manager import (
                    take_resource_snapshot,
                )
                snap = take_resource_snapshot()
                import time as _t
                with self._prebuild_resource_snapshot_lock:
                    self._prebuild_resource_snapshot = snap
                    self._prebuild_resource_snapshot_at = _t.time()
            except Exception:
                logger.debug('prebuild: background snapshot refresh failed',
                             exc_info=True)
            finally:
                self._prebuild_snapshot_refresh_in_flight = False
                self._push_bootstrap_flags_to_watchdog()
                self._check_startup_followup_done()

        t = threading.Thread(target=_worker, daemon=True,
                             name='prebuild-snap-refresh')
        t.start()

    def _get_cached_snapshot(self) -> tuple[Any | None, float]:
        """Read the cached snapshot and its age in seconds.

        Returns ``(snapshot_or_None, age_seconds)``.  Never blocks for
        more than the lock-acquire time.
        """
        self._init_prebuild_snapshot_cache()
        import time as _t
        with self._prebuild_resource_snapshot_lock:
            snap = self._prebuild_resource_snapshot
            age = (_t.time() - self._prebuild_resource_snapshot_at
                   if self._prebuild_resource_snapshot_at else float('inf'))
        return snap, age

    # ---- Decision helpers (UI-thread safe — no subprocess calls) ----

    def _should_pause_prebuild(self, route: str, remaining: list[str]) -> str | None:
        """Check resource pressure and UI health before building a lazy VM.

        Returns a reason string if prebuild should pause, or ``None`` if
        it is safe to continue.

        **IMPORTANT:** This method runs on the UI thread.  It reads only
        the cached resource snapshot (populated asynchronously by
        ``_refresh_prebuild_snapshot_async``).  It NEVER calls
        ``take_resource_snapshot()`` directly.
        """
        # 0. Deferred setup owns lightweight dependencies needed by
        # ControlCenterVM (UIBridgeService, MCP refs, screenshot provider).
        # Do not build control before that batch finishes.
        if self._deferred_setup_active:
            return 'startup_background_active:deferred_post_window_setup'

        # 0b. ControlCenterVM owns the chat bridge used for live audit,
        # user handoff, and human assistance. Once deferred setup is done,
        # it must be allowed to build even while metacognitive background
        # refresh is running; otherwise the app loses its own communication
        # channel for 40-120s after the user already sees the window.
        if route == 'control':
            try:
                self._timeline.mark('startup_chat_bridge_priority_granted')
            except Exception:
                pass
            return None

        # 0c. Background startup phases for non-control VMs. Truth refresh
        # belongs to the birth contract, so non-control VMs wait for it.
        # Startup evolution is idle-gated maintenance and must not freeze
        # non-critical prebuild by holding a startup-background label.
        if self._truth_refresh_active:
            return 'startup_background_active:startup_truth_refresh'

        # 1. Resource pressure from cached snapshot (non-blocking)
        snap, age = self._get_cached_snapshot()
        if snap is not None and age < self._PREBUILD_SNAPSHOT_MAX_AGE_S:
            if snap.ram_pressure in self._PREBUILD_RAM_PAUSE_THRESHOLDS:
                return f'ram_pressure:{snap.ram_pressure}'
            if snap.cpu_pressure in self._PREBUILD_CPU_PAUSE_THRESHOLDS:
                return f'cpu_pressure:{snap.cpu_pressure}'
        elif snap is None and getattr(self, '_prebuild_snapshot_refresh_in_flight', False):
            return 'resource_snapshot_pending'
        elif snap is None:
            self._refresh_prebuild_snapshot_async()
            return 'resource_snapshot_unavailable'

        # 2. Recent UI stall from UIHeartbeatWatchdog
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is not None:
            try:
                recent = watchdog.recent_stalls(limit=5)
                if recent:
                    import time as _time
                    now = _time.time()
                    for stall in recent:
                        ts_str = stall.get('timestamp', '')
                        if ts_str:
                            from datetime import datetime, timezone
                            try:
                                stall_t = datetime.fromisoformat(ts_str).timestamp()
                                if now - stall_t < self._PREBUILD_STALL_LOOKBACK_S:
                                    return f'recent_ui_stall:{stall.get("duration_ms", 0):.0f}ms'
                            except Exception:
                                pass
            except Exception:
                logger.debug('prebuild: watchdog query failed', exc_info=True)

        return None  # safe to continue

    def _emit_prebuild_paused(self, reason: str, route: str, remaining: list[str]) -> None:
        """Emit timeline marker and log when prebuild is paused.

        Uses the cached resource snapshot — never calls
        ``take_resource_snapshot()`` directly.

        **Spam prevention:** Does not emit to the timeline if the same
        ``reason:route`` pair was emitted within the last
        ``_PREBUILD_PAUSED_COOLDOWN_S`` seconds.  Always logs to the
        Python logger regardless of cooldown.
        """
        import time as _t
        now = _t.time()
        dedup_key = f'{reason}:{route}'

        snap_data: dict[str, Any] = {}
        snap, age = self._get_cached_snapshot()
        if snap is not None:
            snap_data = {
                'available_mb': snap.ram_available_mb,
                'memory_percent': snap.ram_used_pct,
                'snapshot_age_ms': round(age * 1000, 1),
            }

        # Only emit to timeline if reason/route changed or cooldown expired
        if (dedup_key != self._prebuild_last_paused_key
                or now - self._prebuild_last_paused_at >= self._PREBUILD_PAUSED_COOLDOWN_S):
            self._prebuild_last_paused_key = dedup_key
            self._prebuild_last_paused_at = now
            try:
                self._timeline.mark(
                    'lazy_vm_prebuild_paused',
                    reason=reason,
                    route=route,
                    remaining_routes=remaining,
                    **snap_data,
                )
            except Exception:
                pass
        logger.warning(
            'lazy_vm_prebuild_paused: reason=%s route=%s remaining=%s %s',
            reason, route, remaining, snap_data,
        )

    def _emit_prebuild_deferred(self, reason: str, route: str, remaining: list[str]) -> None:
        """Emit a lightweight idle-prebuild deferral.

        Snapshot pending/unavailable is not a user-visible freeze cause and
        should not hold the watchdog dominant phase as if the UI were actively
        waiting.  It simply means non-critical VM prebuild will retry later.
        """
        try:
            self._timeline.mark(
                'lazy_vm_prebuild_deferred',
                reason=reason,
                route=route,
                remaining_routes=remaining,
            )
        except Exception:
            pass
        logger.info(
            'lazy_vm_prebuild_deferred: reason=%s route=%s remaining=%s',
            reason, route, remaining,
        )

    # ---- Prebuild chain ----

    # How long to wait before retrying when snapshot is pending (ms).
    # This is idle maintenance; a short 2s loop polluted live stall evidence.
    _PREBUILD_SNAPSHOT_RETRY_MS: int = 15000

    def _build_all_lazy_vms(self) -> None:
        """Pre-build all lazy VMs during idle time (background timer chain).

        Each VM is constructed in its own QTimer.singleShot(0) slot to
        yield to the event loop between constructions, keeping the main
        thread responsive.  Errors in individual VMs are logged but do
        NOT break the chain — the next VM is always scheduled.

        **Resource governance (post-audit fix v3):**
        Before building each route, reads a *cached* resource snapshot
        (refreshed asynchronously in a background thread) and checks
        recent UI stalls via ``UIHeartbeatWatchdog``.  If pressure is
        high or a recent stall is detected, the prebuild chain pauses
        and emits ``lazy_vm_prebuild_paused`` to the startup timeline.

        If the snapshot is not yet available (``resource_snapshot_pending``
        or ``resource_snapshot_unavailable``), the chain does NOT build
        blindly — it schedules a retry via ``QTimer`` so the gate can
        make an informed decision once the background refresh completes.

        ``take_resource_snapshot()`` is NEVER called from the UI thread
        — it can take 15-18 s on Windows (PowerShell/CIM).

        Navigation-triggered construction (``_ensure_vm_for_route``)
        is never paused — only the idle prebuild chain.
        """
        routes = list(self._ROUTE_TO_VM_ATTR.keys())
        self._prebuild_paused = False
        self._prebuild_paused_routes = []

        # Kick off the first async snapshot refresh so the first gate
        # decision has data (it may arrive by the time QTimer fires).
        self._refresh_prebuild_snapshot_async()

        # Set dominant_phase on the heartbeat watchdog so that any
        # stall recorded during prebuild carries a meaningful phase
        # instead of an empty string.
        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is not None:
            watchdog.set_dominant_phase('lazy_vm_prebuild')
            watchdog.set_startup_followup_active(self._startup_followup_active)
        self._push_bootstrap_flags_to_watchdog()

        def _build_next(idx: int = 0) -> None:
            if idx >= len(routes):
                try:
                    self._timeline.mark('lazy_vm_prebuild_done')
                except Exception:
                    pass
                self._prebuild_paused = False
                self._prebuild_paused_routes = []
                # Clear dominant_phase now that prebuild is complete.
                wd = getattr(self, 'ui_heartbeat_watchdog', None)
                if wd is not None:
                    wd.set_dominant_phase('')
                self._push_bootstrap_flags_to_watchdog()
                self._check_startup_followup_done()
                logger.info('lazy_vm_prebuild_done: all %d routes processed', len(routes))
                return

            route = routes[idx]
            remaining = routes[idx + 1:]

            # --- Resource governance gate ---
            pause_reason = self._should_pause_prebuild(route, remaining)
            if pause_reason is not None:
                snapshot_wait = pause_reason.startswith('resource_snapshot_')
                if snapshot_wait:
                    self._prebuild_paused = False
                    self._prebuild_paused_routes = []
                    self._emit_prebuild_deferred(pause_reason, route, routes[idx:])
                else:
                    self._prebuild_paused = True
                    self._prebuild_paused_routes = routes[idx:]
                    self._emit_prebuild_paused(pause_reason, route, routes[idx:])

                # For transient reasons (snapshot pending, background
                # startup active), schedule a non-blocking retry so the
                # chain resumes once the condition clears.
                retryable = (
                    pause_reason.startswith('resource_snapshot_')
                    or pause_reason.startswith('startup_background_active:')
                )
                if retryable:
                    wd = getattr(self, 'ui_heartbeat_watchdog', None)
                    if wd is not None:
                        if snapshot_wait:
                            # The UI is not waiting; the idle chain is simply
                            # deferred until resource observation catches up.
                            wd.set_dominant_phase('')
                        else:
                            # Startup background waits remain useful context.
                            wd.set_dominant_phase(f'prebuild_waiting:{pause_reason}')
                    QTimer.singleShot(
                        self._PREBUILD_SNAPSHOT_RETRY_MS,
                        lambda: _build_next(idx),
                    )
                else:
                    # Non-transient pause (resource pressure, stall) —
                    # clear dominant_phase since we're stopping.
                    wd = getattr(self, 'ui_heartbeat_watchdog', None)
                    if wd is not None:
                        wd.set_dominant_phase('')
                return  # yield to event loop; VMs still built on-demand

            try:
                self._timeline.mark(f'lazy_vm_prebuild_{route}_start')
            except Exception:
                pass

            # Set per-route dominant_phase for watchdog context.
            wd = getattr(self, 'ui_heartbeat_watchdog', None)
            if wd is not None:
                wd.set_dominant_phase(f'lazy_vm_prebuild:{route}')

            try:
                self._ensure_vm_for_route(route)
            except Exception:
                logger.exception('lazy_vm_prebuild failed for route: %s', route)
            try:
                self._timeline.mark(f'lazy_vm_prebuild_{route}_done')
            except Exception:
                pass

            # Clear dominant_phase immediately after route_done so that
            # stalls between routes don't carry a stale phase label.
            wd = getattr(self, 'ui_heartbeat_watchdog', None)
            if wd is not None:
                wd.set_dominant_phase('')

            # Refresh snapshot asynchronously between routes so the
            # next gate decision has up-to-date data.
            self._refresh_prebuild_snapshot_async()

            QTimer.singleShot(0, lambda: _build_next(idx + 1))

        _build_next()

    def _build_deferred_ui_batch_2(self) -> None:
        """All lazy VMs + signal wiring (synchronous test path).

        Used by the synchronous test path (``_build_ui_objects``).
        The live phased path uses lazy construction via
        ``_ensure_vm_for_route`` / ``_build_all_lazy_vms``.
        """
        self._yield_to_event_loop()
        try:
            self._timeline.mark('populate_ui_vm_control_center')
        except Exception:
            pass
        self._build_control_center_vm()
        self._yield_to_event_loop()
        try:
            self._timeline.mark('populate_ui_vm_capture_studio')
        except Exception:
            pass
        self._build_capture_studio_vm()
        self._yield_to_event_loop()
        try:
            self._timeline.mark('populate_ui_vm_evolution_center')
        except Exception:
            pass
        self._build_evolution_center_vm()
        self._yield_to_event_loop()
        try:
            self._timeline.mark('populate_ui_vm_remaining')
        except Exception:
            pass
        self._build_knowledge_base_vm()
        self._build_provider_settings_vm()
        self._build_run_history_vm()
        self._build_centro_vivo_vm()
        self._wire_task_a_signals()

    def _build_ui_objects(self) -> None:
        """Synchronous path: build all VMs in one call (used by tests)."""
        self._build_critical_ui_objects()
        self._build_deferred_ui_batch_1()
        self._build_deferred_ui_batch_2()

    def _wire_task_a_signals(self) -> None:
        """Conecta handlers de los 4 servicios backend (Task A) a ambos ViewModels.

        Cada handler re-emite el payload como Qt Signal de ControlCenter y
        EvolutionCenter, para que los dialogos/paneles QML de Task B los
        reciban sin acoplar el backend a Qt ni a los ViewModels.

        VMs are read dynamically at emit-time (not captured at connect-time)
        so that lazily-constructed VMs automatically start receiving signals
        as soon as they are built.
        """

        def _emit(signal_name: str, payload):
            for vm in (self.control_center_viewmodel, self.evolution_center_viewmodel):
                if vm is None:
                    continue
                signal = getattr(vm, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.emit(payload)
                except Exception:
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
        try:
            work_queue = service.current_work_queue(limit=10)
        except Exception:
            work_queue = []
        return builder.build(state, work_queue=work_queue).model_dump(mode='json')

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

    def create_engine(self, *, defer_vm_creation: bool = False):
        if not PYSIDE_AVAILABLE:
            raise RuntimeError('PySide6 is required to run the desktop UI.')

        # Ensure PySide6's QML plugins are discoverable.  Conda/miniconda
        # installs may place them in a non-default path, causing
        # "qtquick2plugin not found" at engine load time.  Force-set (not
        # setdefault) because conda may point these to a conflicting Qt.
        try:
            import PySide6
            pyside_dir = Path(PySide6.__file__).resolve().parent
            qml_dir = pyside_dir / 'qml'
            plugin_dir = pyside_dir / 'plugins'
            if qml_dir.is_dir():
                os.environ['QML2_IMPORT_PATH'] = str(qml_dir)
                os.environ['QML_IMPORT_PATH'] = str(qml_dir)
            if plugin_dir.is_dir():
                os.environ['QT_PLUGIN_PATH'] = str(plugin_dir)
        except Exception:
            pass

        os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
        QQuickStyle.setStyle('Basic')
        app = QGuiApplication.instance() or QApplication(sys.argv)

        splash = getattr(self, '_splash', None)

        engine = QQmlApplicationEngine()

        # Add PySide6 QML import path directly on the engine as well,
        # which is more reliable than env vars for resolving QtQuick.
        try:
            import PySide6
            pyside_dir = Path(PySide6.__file__).resolve().parent
            qml_dir = pyside_dir / 'qml'
            if qml_dir.is_dir():
                engine.addImportPath(str(qml_dir))
        except Exception:
            pass

        def _set_context_properties(ctx) -> None:
            ctx.setContextProperty('navigationController', self.navigation_controller)
            ctx.setContextProperty('themeController', self.theme_controller)
            ctx.setContextProperty('mainWindowBridge', self.main_window_bridge)
            ctx.setContextProperty('dashboardViewModel', self.dashboard_viewmodel)
            ctx.setContextProperty('controlCenterViewModel', self.control_center_viewmodel)
            ctx.setContextProperty('captureStudioViewModel', self.capture_studio_viewmodel)
            ctx.setContextProperty('evolutionCenterViewModel', self.evolution_center_viewmodel)
            ctx.setContextProperty('knowledgeBaseViewModel', self.knowledge_base_viewmodel)
            ctx.setContextProperty('providerSettingsViewModel', self.provider_settings_viewmodel)
            ctx.setContextProperty('runHistoryViewModel', self.run_history_viewmodel)
            ctx.setContextProperty('centroVivoViewModel', self.centro_vivo_viewmodel)

        context = engine.rootContext()

        if defer_vm_creation:
            # Set all context properties to None so QML can load immediately.
            _vm_names = [
                'navigationController', 'themeController', 'mainWindowBridge',
                'dashboardViewModel', 'controlCenterViewModel',
                'captureStudioViewModel', 'evolutionCenterViewModel',
                'knowledgeBaseViewModel', 'providerSettingsViewModel',
                'runHistoryViewModel', 'centroVivoViewModel',
            ]
            for name in _vm_names:
                context.setContextProperty(name, None)

            if splash:
                splash.set_status('Montando motor QML...')
                try:
                    app.processEvents()
                except Exception:
                    pass

            main_qml = Path(__file__).resolve().parent / 'ui' / 'qml' / 'Main.qml'
            engine.load(QUrl.fromLocalFile(str(main_qml)))
            if not engine.rootObjects():
                raise RuntimeError('Failed to load Main.qml.')

            # --- Phased VM construction ---------------------------------
            # Build critical VMs first (Phase 1), then yield to the event
            # loop.  Loaders are now synchronous (asynchronous: false in
            # Main.qml) so shell_loader_ready fires as soon as
            # mainShellKickoff triggers — no QQmlIncubationController
            # dependency.  Deferred VMs are built in subsequent phases via
            # QTimer.singleShot(0, ...) — each call returns control to
            # the event loop, letting shell_loader_ready fire honestly.
            self._qml_root_context = context

            def _populate_ui_critical() -> None:
                try:
                    self._timeline.mark('populate_ui_start')
                except Exception:
                    pass
                if splash:
                    splash.set_status('Construyendo ViewModels criticos...')
                self._build_critical_ui_objects()
                context.setContextProperty('navigationController', self.navigation_controller)
                context.setContextProperty('themeController', self.theme_controller)
                context.setContextProperty('mainWindowBridge', self.main_window_bridge)
                context.setContextProperty('dashboardViewModel', self.dashboard_viewmodel)
                try:
                    self._timeline.mark('populate_ui_critical_done')
                except Exception:
                    pass
                logger.info('populate_ui_critical: nav + theme + bridge + dashboard ready')
                QTimer.singleShot(0, _populate_ui_deferred_1)

            def _populate_ui_deferred_1() -> None:
                try:
                    self._timeline.mark('populate_ui_deferred_1_start')
                except Exception:
                    pass
                self._build_deferred_ui_batch_1()
                # The ControlCenterVM owns the UIBridge chat endpoint.
                # Build that single communication path immediately after
                # its lightweight dependencies exist; all other VMs remain
                # lazy/on-demand or idle-prebuilt later.
                QTimer.singleShot(
                    0,
                    lambda: self._ensure_startup_chat_bridge_ready(
                        'populate_ui_deferred_1',
                    ),
                )
                try:
                    self._timeline.mark('populate_ui_deferred_1_done')
                except Exception:
                    pass
                # All remaining VMs wait for page_loader_ready (or
                # fallback) so they never block the pre-ready path.
                self._pending_deferred_2_fn = _populate_ui_deferred_2
                if getattr(self, '_page_loader_ready_received', False):
                    self._schedule_pending_deferred_2()

            def _populate_ui_deferred_2() -> None:
                if getattr(self, '_deferred_batch_2_done', False):
                    return
                self._deferred_batch_2_done = True
                try:
                    self._timeline.mark('populate_ui_deferred_2_start')
                except Exception:
                    pass
                # Wire Task A signals (reads VMs dynamically at emit-time,
                # so lazily-constructed VMs automatically receive signals).
                self._wire_task_a_signals()
                # Connect navigation listener for lazy VM construction.
                nav = getattr(self, 'navigation_controller', None)
                if nav is not None:
                    nav.currentRouteChanged.connect(
                        lambda: self._ensure_vm_for_route(nav.currentRoute)
                    )
                logger.info(
                    'ui_lazy_construction_ready: Phase 3 VMs will be '
                    'constructed on-demand when user navigates to their page'
                )
                try:
                    self._timeline.mark('populate_ui_done')
                except Exception:
                    pass
                # Fix 19a: Show system tray icon (doesn't depend on VMs)
                try:
                    self.win_systray_bridge.show(
                        on_show_window=self._raise_main_window,
                        on_quit=app.quit,
                    )
                except Exception:
                    pass
                # Start idle pre-build: after 15s, begin constructing
                # Phase 3 VMs one-by-one with event loop yields so they
                # are ready before the user navigates there.
                QTimer.singleShot(15_000, self._build_all_lazy_vms)

            QTimer.singleShot(0, _populate_ui_critical)
        else:
            # Synchronous path (used by tests that don't call app.exec()).
            if splash:
                splash.set_status('Construyendo ViewModels...')
                try:
                    app.processEvents()
                except Exception:
                    pass
            self._build_ui_objects()
            _set_context_properties(context)

            if splash:
                splash.set_status('Montando motor QML...')
                try:
                    app.processEvents()
                except Exception:
                    pass

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
        if os.name == 'nt' and python_exe.lower().endswith('pythonw.exe'):
            python_candidate = Path(python_exe).with_name('python.exe')
            if python_candidate.is_file():
                python_exe = str(python_candidate)
        workspace = str(self.config.workspace_root)
        src_dir = str(Path(workspace) / 'src')

        env = {**os.environ}
        if 'PYTHONPATH' not in env or src_dir not in env.get('PYTHONPATH', ''):
            env['PYTHONPATH'] = src_dir + os.pathsep + env.get('PYTHONPATH', '')
        env.setdefault('IABV_MCP_TRANSPORT', 'streamable-http')
        env.setdefault('IABV_MCP_NAME', 'iabv-v15')
        env.setdefault('FASTMCP_HOST', '127.0.0.1')
        env.setdefault('FASTMCP_PORT', '8000')
        env.setdefault('PYTHONUNBUFFERED', '1')
        env['IABV_WORKSPACE_ROOT'] = workspace
        # Signal that this bootstrap runs inside the MCP subprocess so it
        # can reduce redundant scans and log noise.
        env['IABV_MCP_SUBPROCESS'] = '1'
        # The startup timeline audits visible UI boot. If the MCP child writes
        # into the same JSONL, it contaminates phase ordering and breaks the
        # metacognitive snapshot for splash -> shell timings.
        env['IABV_STARTUP_TIMELINE'] = '0'

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

        creationflags = 0
        startupinfo = None
        if os.name == 'nt':
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
            startupinfo.wShowWindow = 0

        previous_handle = getattr(self, '_mcp_runtime_log_handle', None)
        if previous_handle is not None:
            try:
                previous_handle.close()
            except Exception:
                pass
            self._mcp_runtime_log_handle = None
        log_handle = None
        try:
            log_path = Path(self.config.logs_dir) / 'mcp_server_runtime.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open('ab')
            proc = subprocess.Popen(
                [python_exe, '-m', 'iabv_v15.infra.mcp.server'],
                cwd=workspace,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self._mcp_runtime_log_handle = log_handle
            logger.info('mcp_autostart: MCP server launched (PID %d)', proc.pid)
            return proc
        except Exception as exc:
            if log_handle is not None:
                try:
                    log_handle.close()
                except Exception:
                    pass
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

        creationflags = 0
        startupinfo = None
        if os.name == 'nt':
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
            startupinfo.wShowWindow = 0

        previous_handle = getattr(self, '_tunnel_runtime_log_handle', None)
        if previous_handle is not None:
            try:
                previous_handle.close()
            except Exception:
                pass
            self._tunnel_runtime_log_handle = None
        log_handle = None
        try:
            log_path = Path(self.config.logs_dir) / 'cloudflared_runtime.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open('ab')
            proc = subprocess.Popen(
                [
                    cloudflared, 'tunnel',
                    '--url', origin,
                    '--no-autoupdate',
                    '--loglevel', 'info',
                    '--http-host-header', host_header,
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self._tunnel_runtime_log_handle = log_handle
            logger.info('mcp_autostart: Cloudflare tunnel launched (PID %d)', proc.pid)
            return proc
        except Exception as exc:
            if log_handle is not None:
                try:
                    log_handle.close()
                except Exception:
                    pass
            logger.warning('mcp_autostart: failed to launch tunnel: %s', exc)
            return None

    # ------------------------------------------------------------------
    # Task 8: MCP supervision — heartbeat + auto-restart
    # ------------------------------------------------------------------

    _MCP_HEARTBEAT_INTERVAL_S: float = 15.0
    _MCP_MAX_RESTART_ATTEMPTS: int = 3
    _MCP_RESTART_COOLDOWN_S: float = 10.0

    def _mcp_supervision_loop(self) -> None:
        """Background daemon that monitors MCP + tunnel subprocesses.

        Periodically checks if the processes are alive.  When a crash is
        detected, attempts a controlled restart (up to
        ``_MCP_MAX_RESTART_ATTEMPTS``).  Status is logged so UI can
        surface dead-session detection.
        """
        import time as _time

        mcp_restarts = 0
        tunnel_restarts = 0
        last_mcp_restart: float = 0
        last_tunnel_restart: float = 0

        while getattr(self, '_mcp_supervisor_running', True):
            _time.sleep(self._MCP_HEARTBEAT_INTERVAL_S)

            if not getattr(self, '_mcp_supervisor_running', True):
                break

            now = _time.monotonic()

            # --- Check MCP subprocess ---
            mcp = getattr(self, '_mcp_proc', None)
            if mcp is not None and mcp.poll() is not None:
                exit_code = mcp.returncode
                logger.warning(
                    'mcp_supervisor: MCP server died (exit=%s, restarts=%d/%d)',
                    exit_code, mcp_restarts, self._MCP_MAX_RESTART_ATTEMPTS,
                )
                if (
                    mcp_restarts < self._MCP_MAX_RESTART_ATTEMPTS
                    and (now - last_mcp_restart) > self._MCP_RESTART_COOLDOWN_S
                ):
                    mcp_restarts += 1
                    last_mcp_restart = now
                    logger.info('mcp_supervisor: restarting MCP server (attempt %d)', mcp_restarts)
                    self._mcp_proc = self._start_mcp_subprocess()
                    if self._mcp_proc is not None:
                        logger.info(
                            'mcp_supervisor: MCP server restarted (PID %d)',
                            self._mcp_proc.pid,
                        )
                    else:
                        logger.error('mcp_supervisor: MCP server restart failed')
                elif mcp_restarts >= self._MCP_MAX_RESTART_ATTEMPTS:
                    logger.error(
                        'mcp_supervisor: MCP server max restarts (%d) reached, giving up',
                        self._MCP_MAX_RESTART_ATTEMPTS,
                    )

            # --- Check tunnel subprocess ---
            tunnel = getattr(self, '_tunnel_proc', None)
            if tunnel is not None and tunnel.poll() is not None:
                exit_code = tunnel.returncode
                logger.warning(
                    'mcp_supervisor: tunnel died (exit=%s, restarts=%d/%d)',
                    exit_code, tunnel_restarts, self._MCP_MAX_RESTART_ATTEMPTS,
                )
                if (
                    tunnel_restarts < self._MCP_MAX_RESTART_ATTEMPTS
                    and (now - last_tunnel_restart) > self._MCP_RESTART_COOLDOWN_S
                ):
                    tunnel_restarts += 1
                    last_tunnel_restart = now
                    logger.info('mcp_supervisor: restarting tunnel (attempt %d)', tunnel_restarts)
                    self._tunnel_proc = self._start_tunnel_subprocess()
                    if self._tunnel_proc is not None:
                        logger.info(
                            'mcp_supervisor: tunnel restarted (PID %d)',
                            self._tunnel_proc.pid,
                        )
                    else:
                        logger.error('mcp_supervisor: tunnel restart failed')
                elif tunnel_restarts >= self._MCP_MAX_RESTART_ATTEMPTS:
                    logger.error(
                        'mcp_supervisor: tunnel max restarts (%d) reached, giving up',
                        self._MCP_MAX_RESTART_ATTEMPTS,
                    )

            # Update supervision status for UI visibility
            self._mcp_supervision_status = {
                'mcp_alive': (
                    getattr(self, '_mcp_proc', None) is not None
                    and getattr(self, '_mcp_proc').poll() is None
                ),
                'tunnel_alive': (
                    getattr(self, '_tunnel_proc', None) is not None
                    and getattr(self, '_tunnel_proc').poll() is None
                ),
                'mcp_restarts': mcp_restarts,
                'tunnel_restarts': tunnel_restarts,
                'mcp_max_restarts_reached': mcp_restarts >= self._MCP_MAX_RESTART_ATTEMPTS,
                'tunnel_max_restarts_reached': tunnel_restarts >= self._MCP_MAX_RESTART_ATTEMPTS,
            }

        logger.info('mcp_supervisor: supervision loop exited')

    def mcp_supervision_status(self) -> dict[str, Any]:
        """Return the current MCP supervision status for UI display."""
        return getattr(self, '_mcp_supervision_status', {
            'mcp_alive': False,
            'tunnel_alive': False,
            'mcp_restarts': 0,
            'tunnel_restarts': 0,
            'mcp_max_restarts_reached': False,
            'tunnel_max_restarts_reached': False,
        })

    def _start_mcp_supervisor(self) -> None:
        """Start the MCP supervision daemon thread."""
        self._mcp_supervisor_running = True
        self._mcp_supervision_status: dict[str, Any] = {}
        self._mcp_supervisor_thread = threading.Thread(
            target=self._mcp_supervision_loop,
            name='mcp-supervisor',
            daemon=True,
        )
        self._mcp_supervisor_thread.start()
        logger.info('mcp_supervisor: supervision daemon started')

    def _stop_mcp_supervisor(self) -> None:
        """Signal the MCP supervision loop to stop."""
        self._mcp_supervisor_running = False

    def _auto_optimize_brain(self) -> None:
        """Auto-optimize the reasoning brain on startup.

        Tests each configured cloud provider with a quick inference call
        and records latency to ``AdaptiveModelSelector`` so the best
        provider is always used for reasoning tasks.

        This runs in background — no UI blocking.  Only providers with
        configured API keys are tested.
        """
        selector = getattr(self, 'adaptive_model_selector', None)
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

    def _startup_evolution_initial_delay_ms(self) -> int:
        """Return the first idle-maintenance delay for startup evolution."""
        raw = os.environ.get('IABV_STARTUP_EVOLUTION_DELAY_MS')
        if raw is None:
            return self._STARTUP_EVOLUTION_INITIAL_DELAY_MS
        try:
            return max(30_000, int(raw))
        except Exception:
            return self._STARTUP_EVOLUTION_INITIAL_DELAY_MS

    def _trace_startup_evolution(self, kind: str, **data: Any) -> None:
        tracer = getattr(self, '_tracer', None)
        if tracer is not None:
            try:
                tracer.trace(kind, **data)
            except Exception:
                pass
        try:
            self._timeline.mark(kind, **data)
        except Exception:
            pass

    def _startup_evolution_defer_reason(self) -> str | None:
        """Return why startup evolution must wait, or ``None`` if safe."""
        if str(os.environ.get('IABV_DISABLE_STARTUP_EVOLUTION', '')).lower() in {
            '1', 'true', 'yes', 'on',
        }:
            return 'disabled_by_env'

        watchdog = getattr(self, 'ui_heartbeat_watchdog', None)
        if watchdog is not None:
            try:
                if getattr(watchdog, '_query_pending', False):
                    return 'query_pending'
            except Exception:
                pass
            try:
                if self._has_recent_ui_stall(watchdog, threshold_ms=1500.0):
                    return 'recent_ui_stall'
            except Exception:
                pass

        snap, age = self._get_cached_snapshot()
        if snap is None:
            self._refresh_prebuild_snapshot_async()
            return 'resource_snapshot_unavailable'
        if age >= self._PREBUILD_SNAPSHOT_MAX_AGE_S:
            self._refresh_prebuild_snapshot_async()
            return 'resource_snapshot_stale'

        ram_pressure = str(getattr(snap, 'ram_pressure', '') or '').lower()
        cpu_pressure = str(getattr(snap, 'cpu_pressure', '') or '').lower()
        if ram_pressure in {'high', 'critical'}:
            return f'ram_pressure:{ram_pressure}'
        if cpu_pressure in {'high', 'critical'}:
            return f'cpu_pressure:{cpu_pressure}'

        try:
            available_mb = float(getattr(snap, 'ram_available_mb', 0.0) or 0.0)
            if available_mb < self._STARTUP_EVOLUTION_MIN_FREE_MB:
                return f'low_free_ram:{available_mb:.0f}mb'
        except Exception:
            pass
        try:
            used_pct = float(getattr(snap, 'ram_used_pct', 0.0) or 0.0)
            if used_pct >= self._STARTUP_EVOLUTION_MAX_RAM_USED_PCT:
                return f'high_ram_used:{used_pct:.1f}%'
        except Exception:
            pass

        return None

    def _schedule_startup_evolution_retry(self, delay_ms: int, reason: str) -> None:
        try:
            QTimer.singleShot(delay_ms, self._schedule_startup_evolution)
        except Exception:
            logger.debug('startup_evolution: retry scheduling failed', exc_info=True)
        self._trace_startup_evolution(
            'startup_evolution_deferred_until_idle',
            reason=reason,
            delay_ms=delay_ms,
            deferrals=getattr(self, '_startup_evolution_defer_count', 0),
        )

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

        reason = self._startup_evolution_defer_reason()
        if reason:
            if reason == 'disabled_by_env':
                self._trace_startup_evolution(
                    'startup_evolution_skipped',
                    reason=reason,
                )
                return
            count = int(getattr(self, '_startup_evolution_defer_count', 0) or 0) + 1
            self._startup_evolution_defer_count = count
            if count >= self._STARTUP_EVOLUTION_MAX_DEFERRALS:
                self._trace_startup_evolution(
                    'startup_evolution_skipped_after_deferrals',
                    reason=reason,
                    deferrals=count,
                )
                logger.warning(
                    'startup_evolution: skipped after %d deferrals (%s)',
                    count, reason,
                )
                return
            delay_ms = min(
                self._STARTUP_EVOLUTION_RETRY_BASE_MS * (2 ** (count - 1)),
                10 * 60_000,
            )
            logger.info(
                'startup_evolution: deferred until idle (%s, attempt %d)',
                reason, count,
            )
            self._schedule_startup_evolution_retry(delay_ms, reason)
            return

        self._startup_evolution_defer_count = 0
        self._startup_evolution_active = True
        self._push_bootstrap_flags_to_watchdog()

        def _run_startup_cycle() -> None:
            logger.info('startup_evolution: beginning background cycle')
            self._trace_startup_evolution('startup_evolution_started')
            try:
                # Step 0a: Detect if code was updated since last run
                self._detect_code_update()

                # Step 0b: Analyze startup console log for warnings/errors
                self._analyze_startup_log()

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

                # Step 4: Resource metacognition — observe, liberate, select model
                resource_meta = getattr(self, 'resource_metacognition_service', None)
                if resource_meta:
                    try:
                        snapshot = resource_meta.observe_resources()
                        plan = resource_meta.analyze_liberation_plan(snapshot)
                        if plan.should_liberate:
                            result = resource_meta.execute_liberation(plan, mode='auto')
                            resource_meta.record_outcome(result)
                            logger.info(
                                'startup_evolution: resource liberation — freed %.1fGB, model=%s',
                                result.ram_freed_gb, result.selected_model,
                            )
                        else:
                            logger.info(
                                'startup_evolution: resource check — %s',
                                plan.reason,
                            )
                    except Exception as exc:
                        logger.warning('startup_evolution: resource metacognition failed: %s', exc)

                # Step 5 (Task 10): Freeze diagnostics — analyze recent incidents
                freeze_reporter = getattr(self, 'freeze_reporter', None)
                if freeze_reporter is not None and hasattr(freeze_reporter, 'diagnose_freeze_cause'):
                    try:
                        diagnosis = freeze_reporter.diagnose_freeze_cause()
                        if diagnosis.get('incident_count', 0) > 0:
                            logger.info(
                                'startup_evolution: freeze diagnostics — %s',
                                diagnosis.get('summary', 'no summary'),
                            )
                            for rec in diagnosis.get('config_recommendations', []):
                                logger.info(
                                    'startup_evolution: freeze recommendation — %s=%s (%s)',
                                    rec.get('config'), rec.get('value'), rec.get('reason'),
                                )
                        else:
                            logger.info('startup_evolution: freeze diagnostics — no recent incidents')
                    except Exception as exc:
                        logger.debug('startup_evolution: freeze diagnostics failed: %s', exc)

                logger.info('startup_evolution: background cycle complete')
                self._trace_startup_evolution('startup_evolution_finished')
            except Exception as exc:
                logger.warning('startup_evolution: unexpected error: %s', exc)
                self._trace_startup_evolution(
                    'startup_evolution_finished',
                    error=str(exc),
                )
            finally:
                self._startup_evolution_active = False
                self._push_bootstrap_flags_to_watchdog()

        threading.Thread(
            target=_run_startup_cycle,
            name='startup-evolution',
            daemon=True,
        ).start()

    def _detect_code_update(self) -> None:
        """Detect if code was updated since last recorded commit.

        Generates an OSES finding when the commit has changed and checks
        whether critical files were modified (potential auto-restart trigger).
        """
        import subprocess as _sp
        state_file = Path(self.config.evolution_dir) / 'last_known_commit.txt'
        try:
            result = _sp.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, timeout=10,
                cwd=str(self.config.workspace_root),
            )
            if result.returncode != 0:
                return
            current_sha = result.stdout.strip()
            if not current_sha:
                return

            last_sha = ''
            if state_file.exists():
                last_sha = state_file.read_text(encoding='utf-8').strip()

            if last_sha and last_sha != current_sha:
                # Determine changed files
                diff_result = _sp.run(
                    ['git', 'diff', '--name-only', last_sha, current_sha],
                    capture_output=True, text=True, timeout=15,
                    cwd=str(self.config.workspace_root),
                )
                changed_files = diff_result.stdout.strip().splitlines() if diff_result.returncode == 0 else []
                n_files = len(changed_files)

                logger.info(
                    'startup_evolution: code updated %s -> %s (%d files)',
                    last_sha[:8], current_sha[:8], n_files,
                )

                # Generate OSES finding
                oses = getattr(self, 'operational_self_examination_service', None)
                if oses is not None:
                    try:
                        oses.add_external_finding({
                            'category': 'auto_update',
                            'title': f'Codigo actualizado: {last_sha[:8]} -> {current_sha[:8]} ({n_files} archivos)',
                            'summary': (
                                f'Se detecto actualizacion de codigo. '
                                f'Archivos cambiados: {n_files}. '
                                f'Commit anterior: {last_sha[:8]}, actual: {current_sha[:8]}.'
                            ),
                            'severity': 'LOW',
                            'confidence': 1.0,
                            'recommendation': 'Revisar cambios si hay comportamiento inesperado',
                            'metadata': {
                                'old_commit': last_sha,
                                'new_commit': current_sha,
                                'files_changed': n_files,
                                'changed_files': changed_files[:20],
                            },
                        })
                    except Exception as exc:
                        logger.debug('startup_evolution: OSES finding failed: %s', exc)

                # Check for critical file changes that warrant restart
                critical_patterns = ('bootstrap.py', 'control_center_viewmodel.py',
                                     'adaptive_task_orchestrator.py', 'domain/models.py')
                critical_changed = [f for f in changed_files if any(p in f for p in critical_patterns)]
                if critical_changed:
                    logger.warning(
                        'startup_evolution: critical files changed: %s — restart recommended',
                        critical_changed,
                    )

            # Save current commit
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(current_sha, encoding='utf-8')

        except Exception as exc:
            logger.debug('startup_evolution: code update detection failed: %s', exc)

    def _analyze_startup_log(self) -> None:
        """Read the startup console log and generate OSES findings for warnings/errors.

        The startup script (start_iabv.ps1) captures all console output to
        data/logs/startup_console.log via Start-Transcript. This method reads
        that log and surfaces any warnings or errors as OSES findings so the
        program can self-examine its own startup process.
        """
        log_path = Path(self.config.workspace_root) / 'data' / 'logs' / 'startup_console.log'
        if not log_path.exists():
            return

        try:
            content = log_path.read_text(encoding='utf-8', errors='replace')
            lines = content.splitlines()

            warnings = [l.strip() for l in lines if '[warn]' in l.lower() or '[auto-pull]' in l.lower() and 'fallo' in l.lower()]
            errors = [l.strip() for l in lines if '[err]' in l.lower() or 'error' in l.lower() and 'exit' in l.lower()]

            oses = getattr(self, 'operational_self_examination_service', None)
            if oses is None:
                return

            if errors:
                oses.add_external_finding({
                    'category': 'startup_health',
                    'title': f'Errores detectados en arranque ({len(errors)} lineas)',
                    'summary': '\n'.join(errors[:5]),
                    'severity': 'HIGH',
                    'confidence': 0.9,
                    'recommendation': 'Revisar data/logs/startup_console.log para detalles completos',
                    'metadata': {'log_file': str(log_path), 'error_lines': errors[:10]},
                })

            if warnings and not errors:
                oses.add_external_finding({
                    'category': 'startup_health',
                    'title': f'Advertencias en arranque ({len(warnings)} lineas)',
                    'summary': '\n'.join(warnings[:5]),
                    'severity': 'LOW',
                    'confidence': 0.8,
                    'recommendation': 'Revisar si las advertencias afectan funcionalidad',
                    'metadata': {'log_file': str(log_path), 'warning_lines': warnings[:10]},
                })

            logger.info(
                'startup_evolution: startup log analyzed — %d errors, %d warnings',
                len(errors), len(warnings),
            )
        except Exception as exc:
            logger.debug('startup_evolution: startup log analysis failed: %s', exc)

    def _is_mcp_port_in_use(self, port: int = 8000) -> bool:
        """Check if the MCP port is already in use (another instance running)."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def run(self) -> int:
        self._timeline.mark('run_start')
        # Holder for subprocesses; written from background thread.
        self._mcp_proc = None
        self._tunnel_proc = None
        self._mcp_runtime_log_handle = None
        self._tunnel_runtime_log_handle = None

        # Crash log: capture fatal errors so they survive even if the console
        # is hidden (launched via shortcut / pythonw / -WindowStyle Hidden).
        crash_log = Path(self.config.logs_dir) / 'ui_crash.log'

        try:
            # --- Splash screen: show immediately while services load ---
            if PYSIDE_AVAILABLE:
                # Fix 19c: DPI awareness — call SetProcessDpiAwareness(2)
                # (Per-Monitor V2) BEFORE QGuiApplication so Qt inherits
                # the correct DPI from the start.  Harmless on non-Windows.
                if os.name == 'nt':
                    try:
                        import ctypes
                        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
                    except Exception:
                        pass

                os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
                QQuickStyle.setStyle('Basic')
                self._timeline.mark('qt_style_set')
                splash_app = QGuiApplication.instance() or QApplication(sys.argv)
                self._timeline.mark('qt_app_created')
                self._splash = SplashController(
                    workspace_dir=self.config.workspace_root,
                )
                self._timeline.mark('splash_controller_created')
                # Conexion para diagnosticar Z-order: QML emite
                # ``closingNow`` antes de ``splashWindow.close()`` y
                # bootstrap marca el hito en el timeline.
                try:
                    self._splash.closingNow.connect(self._handle_splash_closing)
                except Exception:
                    logger.exception('No se pudo conectar splash.closingNow -> _handle_splash_closing')
                splash_engine = QQmlApplicationEngine()
                self._timeline.mark('splash_qml_engine_created')
                splash_engine.rootContext().setContextProperty('splashController', self._splash)
                splash_qml = Path(__file__).resolve().parent / 'ui' / 'qml' / 'SplashScreen.qml'
                splash_engine.load(QUrl.fromLocalFile(str(splash_qml)))
                self._timeline.mark('splash_qml_loaded')
                if not splash_engine.rootObjects():
                    logger.error('splash_screen: QML failed to load from %s', splash_qml)
                    if self._splash:
                        self._splash.set_error(
                            'Error cargando splash',
                            f'QML no cargó desde {splash_qml}',
                        )
                # Process events so the splash actually renders
                splash_app.processEvents()
                self._timeline.mark('splash_visible')
            else:
                self._splash = None

            # --- Wire services (deferred from __init__ when _defer_services=True) ---
            if not self._services_wired:
                if self._splash:
                    self._splash.set_status('Inicializando servicios...')
                    try:
                        QGuiApplication.instance().processEvents()
                    except Exception:
                        pass
                self._wire_services()
                if self._splash:
                    try:
                        QGuiApplication.instance().processEvents()
                    except Exception:
                        pass

            # --- MCP autostart ---
            if self._splash:
                self._splash.set_status('Verificando servicios MCP...')
                try:
                    QGuiApplication.instance().processEvents()
                except Exception:
                    pass

            skip_mcp = os.environ.get('IABV_SKIP_MCP_AUTOSTART', '') == '1'
            mcp_port = int(os.environ.get('FASTMCP_PORT', '8000'))
            if skip_mcp:
                logger.info('mcp_autostart: skipped (IABV_SKIP_MCP_AUTOSTART=1)')
            elif not self._is_mcp_port_in_use(mcp_port):
                if self._splash:
                    self._splash.set_status('Iniciando servidor MCP...')
                    try:
                        QGuiApplication.instance().processEvents()
                    except Exception:
                        pass
                def _deferred_mcp_start() -> None:
                    self._mcp_proc = self._start_mcp_subprocess()
                    if self._mcp_proc:
                        import time
                        time.sleep(2)
                        self._tunnel_proc = self._start_tunnel_subprocess()
                    # Task 8: start supervision after initial launch
                    self._start_mcp_supervisor()
                threading.Thread(
                    target=_deferred_mcp_start,
                    name='mcp-deferred-start',
                    daemon=True,
                ).start()
            else:
                logger.info('mcp_autostart: port %d already in use, skipping MCP launch', mcp_port)

            # --- Startup evolution: defer until the main event loop is alive ---
            if self._splash:
                self._splash.set_status('Preparando ciclo evolutivo...')
                try:
                    QGuiApplication.instance().processEvents()
                except Exception:
                    pass

            # --- Load main UI ---
            if self._splash:
                self._splash.set_status('Cargando interfaz principal...')
                try:
                    self._splash.set_progress(40)
                except Exception:
                    pass
                try:
                    QGuiApplication.instance().processEvents()
                except Exception:
                    pass

            self._timeline.mark('engine_load_main_qml_start')
            app, _engine = self.create_engine(defer_vm_creation=True)
            self._timeline.mark('engine_load_main_qml_done')

            # Update splash progress after QML engine is loaded.
            if self._splash:
                try:
                    self._splash.set_progress(60)
                except Exception:
                    pass
                try:
                    QGuiApplication.instance().processEvents()
                except Exception:
                    pass

            # Explicitly show + raise the main window.  Guardamos la
            # referencia en ``self._main_win`` para que los handlers de
            # readiness honestos puedan reaplicar raise/activate y pelearle
            # el Z-order al splash en Windows pythonw.exe.
            if _engine.rootObjects():
                main_win = _engine.rootObjects()[0]
                self._main_win = main_win
                self._engine = _engine
                main_win.show()
                main_win.raise_()
                main_win.requestActivate()
                self._force_win32_visibility(main_win, 'initial_show')
                self._timeline.mark('main_window_shown')
                self._connect_window_lifecycle_signals(main_win)

            # Update splash progress: main window is shown.
            if self._splash:
                try:
                    self._splash.set_progress(75)
                except Exception:
                    pass
                try:
                    QGuiApplication.instance().processEvents()
                except Exception:
                    pass

            QTimer.singleShot(
                self._startup_evolution_initial_delay_ms(),
                self._schedule_startup_evolution,
            )

            # Defer the heavy tool-availability probe (HTTP pings + pip
            # install of mcp_client).  The probe now runs in a background
            # thread (never blocks the GUI event loop), but we still
            # delay 3s so the QML shell has time to start incubating.
            if not self._tool_availability_logged:
                QTimer.singleShot(3000, self._run_deferred_post_window_setup)

            # ``splash.set_ready()`` ya NO se dispara aqui.  Antes era
            # deshonesto: la ventana visible aun era una ``ApplicationWindow``
            # con todos los VMs en ``None`` y un ``mainShellLoader`` inactivo.
            # Ahora el splash solo recibe ``ready`` cuando QML reporta
            # ``shellLoaderReady`` via ``MainWindowBridge`` (ver
            # ``_handle_shell_loader_ready``), o por fallback determinista si
            # esa senal nunca llega.
            if self._splash is not None:
                import time as _time
                fallback_ms = 3000
                try:
                    raw = os.environ.get('IABV_SHELL_READY_FALLBACK_MS')
                    if raw is not None:
                        fallback_ms = max(1000, int(raw))
                except Exception:
                    fallback_ms = 3000
                self._shell_ready_fallback_ms = fallback_ms
                self._shell_ready_wall_t0 = _time.perf_counter()
                QTimer.singleShot(fallback_ms, self._force_splash_ready_fallback)

            # Start UI heartbeat watchdog — QTimer fires on main thread.
            try:
                self._heartbeat_timer = QTimer()
                self._heartbeat_timer.setInterval(
                    self.ui_heartbeat_watchdog.DEFAULT_TICK_INTERVAL_MS,
                )
                self._heartbeat_timer.timeout.connect(
                    self.ui_heartbeat_watchdog.tick,
                )
                self._heartbeat_timer.start()
                self.ui_heartbeat_watchdog.start_sampler()
                self._timeline.mark('ui_heartbeat_watchdog_started')
            except Exception:
                logger.debug('ui_heartbeat_watchdog: failed to start', exc_info=True)

            self._timeline.mark('app_exec_about_to_start')
            return app.exec()
        except Exception as fatal:
            # Write crash log so the error survives hidden-console launches
            import traceback
            try:
                crash_log.write_text(
                    f'=== BURVE CRASH {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n'
                    f'{traceback.format_exc()}\n',
                    encoding='utf-8',
                )
            except Exception:
                pass
            logger.critical('bootstrap.run() crashed: %s', fatal, exc_info=True)
            raise
        finally:
            # Task 8: stop MCP supervisor before terminating processes
            try:
                self._stop_mcp_supervisor()
            except Exception:
                pass
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
            for handle_name in ('_tunnel_runtime_log_handle', '_mcp_runtime_log_handle'):
                handle = getattr(self, handle_name, None)
                if handle is not None:
                    try:
                        handle.close()
                    except Exception:
                        pass
                    setattr(self, handle_name, None)





