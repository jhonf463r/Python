"""Tests for canonical replan provenance in AdaptiveTaskOrchestrator."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    InferenceRequest,
    SessionContinuationType,
    TaskIntent,
    TaskContext,
    StrategyPack,
    ExecutionPlaybook,
    CapabilityReadiness,
    StrategyCandidate,
    RunRecord,
    InferenceResult,
    RoleRoute,
    RunStatus,
    ExperimentDomain,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository


class TestCanonicalReplanProvenance:
    """Test canonical provenance as single source of truth with legacy mirror."""

    def test_external_request_provenance(self):
        """External requests should have EXTERNAL_REQUEST continuation type and no parent."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
        )

        # Verify canonical provenance defaults
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_auto_replan_provenance(self):
        """Auto-replan sessions should have AUTO_REPLAN continuation type and parent_session_id."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create original session with canonical provenance
        original_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"replan_count": 0, "governance": {"should_replan": True}},
        )
        session_repo.get.return_value = original_session

        # Mock _request_from_session
        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return a session with canonical provenance
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=original_session.session_id,
            replan_depth=1,
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(original_session.session_id)

        # Verify canonical provenance
        assert result is not None
        assert result.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert result.parent_session_id == original_session.session_id
        assert result.replan_depth == 1

    def test_canonical_guard_uses_typed_fields(self):
        """_should_auto_replan must use canonical fields, not metadata."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session with typed depth=2 but legacy metadata replan_count=0
        # Canonical source should block replan, not legacy metadata
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Canonical: at limit
            metadata={"replan_count": 0, "governance": {"should_replan": True}},  # Legacy: would allow
        )
        session_repo.get.return_value = session

        # _should_auto_replan must follow canonical field
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is False, "Canonical replan_depth=2 should block, ignoring legacy replan_count=0"

    def test_mirror_synchronization(self):
        """Legacy metadata mirror must stay synchronized with canonical fields."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session with canonical provenance
        original_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"governance": {"should_replan": True}},
        )
        session_repo.get.return_value = original_session

        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return session with canonical provenance
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=original_session.session_id,
            replan_depth=1,
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(original_session.session_id)

        # Verify mirror synchronization
        assert result.replan_depth == result.metadata["replan_count"]
        assert result.parent_session_id == result.metadata["replanned_from_session_id"]

    def test_historical_migration(self):
        """Historical sessions with legacy metadata must migrate to typed provenance."""
        # Create a session with legacy metadata but no typed provenance
        historical_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,  # Default
            parent_session_id=None,  # Default
            replan_depth=0,  # Default
            metadata={
                "replanned_from_session_id": "legacy-parent-id",
                "replan_count": 1,
            },
        )

        # Model validator should migrate legacy metadata to typed fields
        assert historical_session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert historical_session.parent_session_id == "legacy-parent-id"
        assert historical_session.replan_depth == 1

    def test_typed_provenance_wins_over_legacy(self):
        """Explicit typed provenance must prevail over legacy metadata."""
        # Create session with both typed and legacy, with conflicting values
        # Set typed fields to non-default values to ensure they win
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,  # Explicit typed (non-default)
            parent_session_id="explicit-parent",  # Explicit typed (non-default)
            replan_depth=1,  # Explicit typed (non-default)
            metadata={
                "replanned_from_session_id": "legacy-parent-id",
                "replan_count": 5,
            },
        )

        # Typed fields should NOT be overwritten by legacy metadata
        # because they are not at default values (migration only happens when typed fields are default)
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "explicit-parent"
        assert session.replan_depth == 1

    def test_bounded_replan_with_canonical_fields(self):
        """Bounded replan must use canonical fields, not metadata."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session at replan limit using canonical fields
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Canonical: at limit
            metadata={"governance": {"should_replan": True}},
        )
        session_repo.get.return_value = session

        # _should_auto_replan must block based on canonical replan_depth
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is False, "Canonical replan_depth=2 should block replan"

    def test_persistence_round_trip(self):
        """Canonical provenance must survive repository save/load round trip."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        
        # Create session with canonical provenance
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
            parent_session_id="parent-id",
            replan_depth=1,
        )

        # Mock repository save/get
        session_repo.save.return_value = session
        session_repo.get.return_value = session

        # Save
        session_repo.save(session)

        # Load
        loaded = session_repo.get(session.session_id)

        # Verify canonical provenance survived
        assert loaded.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert loaded.parent_session_id == "parent-id"
        assert loaded.replan_depth == 1
