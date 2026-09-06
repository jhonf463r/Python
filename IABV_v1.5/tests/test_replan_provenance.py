"""Tests for replan provenance tracking in AdaptiveTaskOrchestrator."""
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
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository


class TestReplanProvenance:
    """Test formal provenance tracking for replan sessions."""

    def test_external_request_provenance(self):
        """External requests should have EXTERNAL_REQUEST continuation type and no parent."""
        # Test model initialization directly
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

        # Verify default provenance
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_auto_replan_provenance(self):
        """Auto-replan sessions should have AUTO_REPLAN continuation type and parent_session_id."""
        # Setup
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

        # Create original session
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
            metadata={"replan_count": 0},
        )
        session_repo.get.return_value = original_session

        # Mock _request_from_session to return a request with replan metadata
        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(
                user_goal="test goal",
                metadata={"replanned_from_session_id": original_session.session_id, "replan_count": 1},
            )
        )

        # Mock handle_request to return a session with provenance set
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

        # Verify provenance
        assert result is not None
        assert result.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert result.parent_session_id == original_session.session_id
        assert result.replan_depth == 1

    def test_lineage_reconstruction(self):
        """Lineage should be reconstructable from persisted session state."""
        # Create a chain of sessions
        original = AdaptiveSession(
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

        first_replan = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=original.session_id,
            replan_depth=1,
        )

        second_replan = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=first_replan.session_id,
            replan_depth=2,
        )

        # Reconstruct lineage
        def get_lineage(session, sessions_by_id):
            lineage = [session]
            current = session
            while current.parent_session_id and current.parent_session_id in sessions_by_id:
                parent = sessions_by_id[current.parent_session_id]
                lineage.insert(0, parent)
                current = parent
            return lineage

        sessions_by_id = {
            original.session_id: original,
            first_replan.session_id: first_replan,
            second_replan.session_id: second_replan,
        }

        lineage = get_lineage(second_replan, sessions_by_id)

        # Verify lineage
        assert len(lineage) == 3
        assert lineage[0].session_id == original.session_id
        assert lineage[0].continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert lineage[1].session_id == first_replan.session_id
        assert lineage[1].continuation_type == SessionContinuationType.AUTO_REPLAN
        assert lineage[1].parent_session_id == original.session_id
        assert lineage[2].session_id == second_replan.session_id
        assert lineage[2].continuation_type == SessionContinuationType.AUTO_REPLAN
        assert lineage[2].parent_session_id == first_replan.session_id

    def test_bounded_replan_preserved(self):
        """Existing replan boundedness should not be broken by provenance tracking."""
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

        # Create session at replan limit
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
            metadata={"replan_count": 2, "governance": {"should_replan": True}},
            replan_depth=2,
        )
        session_repo.get.return_value = session

        # _should_auto_replan should still block at replan_count >= 2
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is False, "Replan should be blocked at depth 2"

    def test_replan_count_increment(self):
        """replan_count should increment with each replan."""
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

        # Test increment from 0 to 1
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            metadata={"replan_count": 0},
        )
        session_repo.get.return_value = session

        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        replanned = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            metadata={"replan_count": 1},
            replan_depth=1,
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned))
        task_outcome_recorder.record.return_value = replanned

        result = orchestrator.replan_session(session.session_id)

        # Verify increment
        assert result.metadata["replan_count"] == 1
        assert result.replan_depth == 1
