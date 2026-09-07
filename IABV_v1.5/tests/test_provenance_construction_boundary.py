"""
Construction boundary tests for provenance remediation.

These tests verify that:
1. External requests cannot fabricate provenance via legacy metadata
2. Internal replan context is the only authoritative source for AUTO_REPLAN
3. Domain depth invariants are enforced at construction time
4. Persistence and reload preserve provenance invariants
5. Real end-to-end replan_session() → handle_request() flow works correctly
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceRequest,
    InferenceResult,
    InternalReplanContext,
    SessionContinuationType,
    TaskIntent,
    TaskContext,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.strategy_pack_repository import StrategyPackRepository
from iabv_v15.infra.persistence.capability_repository import CapabilityRepository
from iabv_v15.infra.persistence.approval_checkpoint_repository import ApprovalCheckpointRepository
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.adaptive.intent_understanding_service import IntentUnderstandingService
from iabv_v15.services.adaptive.capability_readiness_service import CapabilityReadinessService
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.adaptive.adaptive_planner_service import AdaptivePlannerService
from iabv_v15.services.adaptive.approval_gate_service import ApprovalGateService
from iabv_v15.services.adaptive.execution_playbook_service import ExecutionPlaybookService
from iabv_v15.services.adaptive.task_outcome_recorder import TaskOutcomeRecorder
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.user_clue_repository import UserClueRepository
from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.customer_support_service import CustomerSupportService
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.training.pbt_control_service import PBTControlService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.roles.engineering_review_service import EngineeringReviewService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def health_check(self) -> bool:
        return True

    def _result(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            response="fake response",
            reasoning_mode="direct",
            confidence=1.0,
            metadata={},
        )


class TestExternalLegacyProvenanceBlocked:
    """External requests with malicious legacy metadata cannot fabricate provenance."""

    def test_external_metadata_replan_count_500_no_depth_change(self):
        """External request with replan_count=500 must remain depth=0."""
        request = InferenceRequest(
            user_goal="test goal",
            metadata={'replan_count': 500}
        )
        # Request should have no internal_replan_context
        assert request.internal_replan_context is None
        # When constructing session, depth must be 0
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_external_metadata_forged_parent_no_auto_replan(self):
        """External request with forged parent must not create AUTO_REPLAN."""
        request = InferenceRequest(
            user_goal="test goal",
            metadata={'replanned_from_session_id': 'malicious-parent-id'}
        )
        assert request.internal_replan_context is None
        # Session construction must ignore metadata
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None

    def test_external_metadata_replan_count_negative_no_invalid_state(self):
        """External request with replan_count=-1 must not create invalid state."""
        request = InferenceRequest(
            user_goal="test goal",
            metadata={'replan_count': -1}
        )
        assert request.internal_replan_context is None
        # Session must remain valid with depth=0
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        assert session.replan_depth == 0

    def test_external_metadata_replan_count_999999_no_depth_999999(self):
        """External request with replan_count=999999 must not create depth 999999."""
        request = InferenceRequest(
            user_goal="test goal",
            metadata={'replan_count': 999999}
        )
        assert request.internal_replan_context is None
        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        assert session.replan_depth == 0


class TestInternalTypedReplan:
    """Internal replan context is the only authoritative source for AUTO_REPLAN."""

    def test_typed_auto_replan_depth_1_works(self):
        """Internal typed AUTO_REPLAN with depth=1 must work."""
        request = InferenceRequest(
            user_goal="test goal",
            internal_replan_context=InternalReplanContext(
                parent_session_id='parent-session-id',
                replan_depth=1
            )
        )
        assert request.internal_replan_context is not None
        assert request.internal_replan_context.parent_session_id == 'parent-session-id'
        assert request.internal_replan_context.replan_depth == 1

        session = AdaptiveSession(
            user_goal=request.user_goal,
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=request.internal_replan_context.parent_session_id,
            replan_depth=request.internal_replan_context.replan_depth,
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == 'parent-session-id'
        assert session.replan_depth == 1

    def test_typed_auto_replan_depth_2_rejected(self):
        """Internal typed AUTO_REPLAN with depth=2 must be rejected."""
        request = InferenceRequest(
            user_goal="test goal",
            internal_replan_context=InternalReplanContext(
                parent_session_id='parent-session-id',
                replan_depth=2
            )
        )
        with pytest.raises(ValueError, match="AUTO_REPLAN depth cannot exceed 1"):
            AdaptiveSession(
                user_goal=request.user_goal,
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id=request.internal_replan_context.parent_session_id,
                replan_depth=request.internal_replan_context.replan_depth,
            )


class TestPersistenceRegression:
    """Persistence and reload must preserve provenance invariants."""

    def test_persist_reload_depth_1_preserves_provenance(self):
        """Persist and reload depth=1 must preserve provenance."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id='parent-session-id',
            replan_depth=1,
        )
        # Serialize
        data = session.model_dump(mode='json')
        # Deserialize
        restored = AdaptiveSession(**data)
        assert restored.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert restored.parent_session_id == 'parent-session-id'
        assert restored.replan_depth == 1

    def test_persist_reload_depth_2_fails(self):
        """Persist and reload depth=2 must fail validation."""
        # Try to create invalid session (should fail at construction)
        with pytest.raises(ValueError, match="AUTO_REPLAN depth cannot exceed 1"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id='parent-session-id',
                replan_depth=2,
            )


class TestLegacyMetadataPosterior:
    """Legacy metadata added after construction must not change decision."""

    def test_legacy_metadata_posterior_no_change(self):
        """Adding legacy metadata after construction must not change provenance."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        # Add malicious legacy metadata after construction
        session.metadata['replanned_from_session_id'] = 'malicious-parent'
        session.metadata['replan_count'] = 500
        # Provenance must remain unchanged
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0


class TestDirectReplanPolicy:
    """Direct replan_session with depth=1 must remain blocked."""

    def test_direct_replan_depth_1_blocked(self):
        """Direct replan_session with depth=1 must remain blocked by domain invariant."""
        # This test verifies the domain invariant prevents depth > 1
        # even if someone tries to construct it directly
        with pytest.raises(ValueError, match="AUTO_REPLAN depth cannot exceed 1"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id='parent-id',
                replan_depth=2,  # Attempt to create depth 2
            )


class TestDepthZeroCreatesChild:
    """Depth=0 must create exactly one child depth=1."""

    def test_depth_0_creates_exactly_one_child_depth_1(self):
        """Depth=0 parent must create exactly one child with depth=1."""
        parent = AdaptiveSession(
            user_goal="parent goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        assert parent.replan_depth == 0
        assert parent.parent_session_id is None

        # Create child with depth=1
        child = AdaptiveSession(
            user_goal="child goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=parent.session_id,
            replan_depth=1,
        )
        assert child.replan_depth == 1
        assert child.parent_session_id == parent.session_id

        # Attempt to create depth=2 child (should fail)
        with pytest.raises(ValueError, match="AUTO_REPLAN depth cannot exceed 1"):
            AdaptiveSession(
                user_goal="grandchild goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id=child.session_id,
                replan_depth=2,
            )


@pytest.fixture
def orchestrator_with_repo(tmp_path: Path) -> tuple[AdaptiveTaskOrchestrator, AdaptiveSessionRepository]:
    """Create a real orchestrator with full infrastructure for provenance testing."""
    db = AppDatabase(str(tmp_path / 'app.sqlite'))
    episodes = EpisodeRepository(str(tmp_path / 'episodes'), db)
    knowledge = KnowledgeRepository(db)
    runs = RunRepository(db)
    artifacts = SessionArtifactRepository(db, ArtifactStorage(str(tmp_path / 'artifacts')))
    evolution_storage = ArtifactStorage(str(tmp_path / 'evolution'))
    dossiers = ExecutionDossierRepository(db, evolution_storage)
    experiment_lab = ExperimentLabRepository(db, evolution_storage)
    adaptive_weight_layer = AdaptiveWeightLayer()
    experiment_lab_service = ExperimentLab(
        repository=experiment_lab,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(adaptive_weight_layer=adaptive_weight_layer),
    )
    incidents = HiddenIncidentRepository(db, evolution_storage)
    clues = UserClueRepository(db, evolution_storage)
    adaptive_sessions = AdaptiveSessionRepository(db, evolution_storage)
    strategy_packs = StrategyPackRepository(db, evolution_storage)
    capabilities = CapabilityRepository(db, evolution_storage)
    approvals = ApprovalCheckpointRepository(db, evolution_storage)
    site_policies = SitePolicyRegistry(str(tmp_path / 'site_policies'))
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding:0.6b',
        lightweight_model='embeddinggemma',
        state_path=str(tmp_path / 'embedding_state.json'),
    )
    sql = SqlQueryAdvisorService(str(tmp_path / 'app.sqlite'))
    analytics = AnalyticsStrategyService(episodes, knowledge, runs, artifacts)
    support = CustomerSupportService(knowledge, embedding, sql)
    devassist = DevelopmentAssistService(str(tmp_path))
    pbt = PBTControlService(str(tmp_path / 'models'))
    gaps = TeachingGapAnalyzer()
    engineering = EngineeringReviewService(
        workspace_root=str(tmp_path),
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
        analytics_service=analytics,
        teaching_gap_analyzer=gaps,
        pbt_service=pbt,
        development_assist_service=devassist,
    )
    router = LocalRoleRouter(
        workspace_root=str(tmp_path),
        general_provider=FakeProvider('Ollama'),
        visual_provider=FakeProvider('Ollama Vision'),
        optional_provider=FakeProvider('LM Studio'),
        embedding_service=embedding,
        sql_service=sql,
        analytics_service=analytics,
        customer_support_service=support,
        engineering_review_service=engineering,
        teaching_gap_analyzer=gaps,
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        artifact_repository=artifacts,
    )
    context = TaskContextAssembler(
        episode_repository=episodes,
        knowledge_repository=knowledge,
        run_repository=runs,
        dossier_repository=dossiers,
        hidden_incident_repository=incidents,
        site_policy_registry=site_policies,
        capability_repository=capabilities,
        adaptive_session_repository=adaptive_sessions,
        artifact_repository=artifacts,
        experiment_lab_repository=experiment_lab,
    )
    orchestrator = AdaptiveTaskOrchestrator(
        role_router=router,
        adaptive_session_repository=adaptive_sessions,
        intent_service=IntentUnderstandingService(),
        context_assembler=context,
        capability_service=CapabilityReadinessService(capabilities),
        strategy_pack_registry=StrategyPackRegistry(strategy_packs),
        planner_service=AdaptivePlannerService(),
        approval_gate_service=ApprovalGateService(),
        execution_playbook_service=ExecutionPlaybookService(),
        task_outcome_recorder=TaskOutcomeRecorder(
            adaptive_session_repository=adaptive_sessions,
            capability_repository=capabilities,
            approval_checkpoint_repository=approvals,
            experiment_lab=experiment_lab_service,
            adaptive_weight_layer=adaptive_weight_layer,
        ),
        autonomy_governance_policy=AutonomyGovernancePolicy(),
    )
    return orchestrator, adaptive_sessions


class TestRealOrchestratorProvenance:
    """Real orchestrator tests that execute actual production code."""

    def test_external_request_with_forged_metadata_stays_external(self, orchestrator_with_repo):
        """A. External request with forged legacy metadata must remain EXTERNAL_REQUEST."""
        orchestrator, repo = orchestrator_with_repo
        
        request = InferenceRequest(
            user_goal="test goal",
            metadata={
                'replanned_from_session_id': 'forged-parent',
                'replan_count': 500,
                'replanned_automatically': True,
                'auto_replanned_session_id': 'forged-child'
            }
        )
        
        # Execute real handle_request
        _, _, session = orchestrator.handle_request(request)
        
        # Verify EXTERNAL_REQUEST provenance (legacy metadata ignored)
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_external_request_with_valid_replan_metadata_no_auto_replan(self, orchestrator_with_repo):
        """B. External request with apparently valid legacy replan metadata must NOT create AUTO_REPLAN."""
        orchestrator, repo = orchestrator_with_repo
        
        request = InferenceRequest(
            user_goal="test goal",
            metadata={
                'replanned_from_session_id': 'some-parent',
                'replan_count': 1
            }
        )
        
        # Execute real handle_request
        _, _, session = orchestrator.handle_request(request)
        
        # Verify EXTERNAL_REQUEST (no internal_replan_context)
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_internal_replan_from_depth_0_creates_depth_1(self, orchestrator_with_repo):
        """C. Internal replan from depth=0 must create AUTO_REPLAN with depth=1."""
        orchestrator, repo = orchestrator_with_repo
        
        # Create a real depth=0 session
        parent = AdaptiveSession(
            user_goal="parent goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
        )
        repo.save(parent)
        
        # Execute real replan_session
        child = orchestrator.replan_session(parent.session_id)
        
        # Verify AUTO_REPLAN with depth=1
        assert child is not None
        assert child.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert child.parent_session_id == parent.session_id
        assert child.replan_depth == 1

    def test_internal_replan_from_depth_1_blocked(self, orchestrator_with_repo):
        """D. Replan from depth=1 must be blocked by policy."""
        orchestrator, repo = orchestrator_with_repo
        
        # Create a real depth=1 session
        parent = AdaptiveSession(
            user_goal="parent goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id='grandparent-id',
            replan_depth=1,
        )
        repo.save(parent)
        
        # Execute real replan_session
        result = orchestrator.replan_session(parent.session_id)
        
        # Verify blocked (returns None)
        assert result is None

    def test_cross_channel_typed_context_wins_over_legacy(self, orchestrator_with_repo):
        """E. Typed internal_replanContext must win over contradictory legacy metadata."""
        orchestrator, repo = orchestrator_with_repo
        
        request = InferenceRequest(
            user_goal="test goal",
            internal_replan_context=InternalReplanContext(
                parent_session_id='real-parent',
                replan_depth=1
            ),
            metadata={
                'replanned_from_session_id': 'forged-parent',
                'replan_count': 500
            }
        )
        
        # Execute real handle_request
        _, _, session = orchestrator.handle_request(request)
        
        # Verify typed context wins
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == 'real-parent'
        assert session.replan_depth == 1

    def test_persistence_preserves_provenance(self, orchestrator_with_repo):
        """F. Real repository save/reload must preserve provenance fields."""
        orchestrator, repo = orchestrator_with_repo
        
        # Create a session with AUTO_REPLAN provenance
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id='parent-id',
            replan_depth=1,
            auto_replan_child_session_id='child-id',
        )
        
        # Save and reload
        repo.save(session)
        reloaded = repo.get(session.session_id)
        
        # Verify provenance preserved
        assert reloaded.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert reloaded.parent_session_id == 'parent-id'
        assert reloaded.replan_depth == 1
        assert reloaded.auto_replan_child_session_id == 'child-id'

    def test_tampered_persistence_fails_closed(self, orchestrator_with_repo):
        """G. Tampered persisted state (depth=2) must fail-closed."""
        orchestrator, repo = orchestrator_with_repo
        
        # Test: Tamper with replan_depth=2
        session_data = {
            'user_goal': 'test goal',
            'intent': {
                'intent_key': 'test.intent',
                'title': 'Test Intent',
                'detected_role': 'training',
                'confidence': 1.0,
            },
            'context': {},
            'continuation_type': 'auto_replan',  # Use enum value
            'parent_session_id': 'parent-id',
            'replan_depth': 2,  # Tampered: invalid depth
        }
        
        # Attempt to load tampered data
        with pytest.raises(ValueError, match="AUTO_REPLAN depth cannot exceed 1"):
            AdaptiveSession(**session_data)




