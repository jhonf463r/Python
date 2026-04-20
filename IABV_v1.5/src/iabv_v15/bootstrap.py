from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
import sys

from iabv_v15.domain.models import ProviderConfig, ProviderKind
from iabv_v15.infra.config import load_app_config, load_theme_config
from iabv_v15.infra.logging import configure_logging

logger = logging.getLogger(__name__)
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
from iabv_v15.infra.persistence.control_master_repository import ControlMasterRepository
from iabv_v15.services.evolution.control_master_digest_builder import ControlMasterDigestBuilder
from iabv_v15.services.evolution.control_master_service import ControlMasterService
from iabv_v15.services.evolution.git_sync_service import GitSyncService
from iabv_v15.services.evolution.mcp_bridge_service import (
    MCPBridgeService,
    build_mcp_bridge_service,
)
from iabv_v15.services.evolution.portable_context_service import PortableContextService
from iabv_v15.services.evolution.self_audit_service import SelfAuditService
from iabv_v15.services.evolution.tool_discovery_service import ToolDiscoveryService
from iabv_v15.services.evolution.tool_evolution_monitor import ToolEvolutionMonitor
from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector
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
from iabv_v15.services.tools.tool_adapters import AiderToolAdapter, DesktopHumanToolAdapter, ExternalAssistantToolAdapter, MCPToolAdapter, OllamaToolAdapter, PlaywrightToolAdapter, ShellToolAdapter, SiteExplorerToolAdapter
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
from iabv_v15.ui.viewmodels.run_history_viewmodel import RunHistoryViewModel


class AppBootstrap:
    def __init__(self, workspace_root: str | None = None) -> None:
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
            'site_explorer': SiteExplorerToolAdapter(
                self.site_exploration_service,
                self.site_manual_repository,
            ),
        }
        self.tool_validator = ToolValidator()
        self.tool_sandbox = ToolSandbox(self.tool_validator)
        self.tool_registry = ToolRegistry(self.tool_record_repository, self.tool_adapters)
        self.universal_perception_service = UniversalPerceptionService(tool_registry=self.tool_registry)
        self.environment_self_awareness_service = EnvironmentSelfAwarenessService(
            workspace_root=self.config.workspace_root,
            evolution_dir=self.config.evolution_dir,
            role_router=None,
            tool_registry=self.tool_registry,
        )
        self.world_model_service = WorldModelService(
            workspace_root=self.config.workspace_root,
            evolution_dir=self.config.evolution_dir,
            tool_registry=self.tool_registry,
            tool_record_repository=self.tool_record_repository,
            environment_self_awareness_service=self.environment_self_awareness_service,
            universal_perception_service=self.universal_perception_service,
            role_router=None,
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
        self.experiment_lab = ExperimentLab(
            repository=self.experiment_lab_repository,
            registry=self.algorithm_benchmark_registry,
            scoring_engine=self.decision_scoring_engine,
            strategy_selector=self.lab_strategy_selector,
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
        )
        self.self_audit_service = SelfAuditService(
            tool_registry=self.tool_registry,
            environment_self_model_provider=self.environment_self_awareness_service.current_model,
            world_model_service=self.world_model_service,
            operational_self_examination_service=self.operational_self_examination_service,
            portable_context_service=self.portable_context_service,
            workspace_root=self.config.workspace_root,
        )
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
        )
        self.portable_context_service.task_context_assembler = self.task_context_assembler
        self.portable_context_service.adaptive_task_orchestrator = self.adaptive_task_orchestrator
        self.adaptive_task_orchestrator.control_master_service = self.control_master_service
        self.adaptive_task_orchestrator.control_master_digest_builder = self.control_master_digest_builder
        self._seed_control_master_from_agents_md()
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
        self.control_center_viewmodel.refreshAutonomyDock()
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
        )
        self.knowledge_base_viewmodel = KnowledgeBaseViewModel(self.knowledge_repository)
        self.provider_settings_viewmodel = ProviderSettingsViewModel(self.provider_configs, self.role_router, self.embedding_service)
        self.run_history_viewmodel = RunHistoryViewModel(self.run_repository, self.execution_dossier_repository)

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

        main_qml = Path(__file__).resolve().parent / 'ui' / 'qml' / 'Main.qml'
        engine.load(QUrl.fromLocalFile(str(main_qml)))
        if not engine.rootObjects():
            raise RuntimeError('Failed to load Main.qml.')
        return app, engine

    def run(self) -> int:
        app, _engine = self.create_engine()
        return app.exec()








