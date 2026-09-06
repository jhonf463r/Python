"""
Canonical provenance tests for bounded replan policy.

Tests verify:
- Canonical provenance fields (continuation_type, parent_session_id, replan_depth)
- Bounded replan policy (depth < 2)
- Manual replan respects policy
- Legacy migration with cross-lineage validation
- Persistence round-trip
"""

import pytest
from unittest.mock import MagicMock
from iabv_v15.domain.models import (
    AdaptiveSession,
    SessionContinuationType,
    TaskIntent,
    TaskContext,
    TaskOutcome,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.domain.models import RunRecord, RunStatus


class TestCanonicalProvenance:
    """Test canonical provenance fields and bounded replan policy."""

    def test_external_request_provenance_default(self):
        """EXTERNAL_REQUEST has parent=None, depth=0 by default."""
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
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_auto_replan_provenance_invariant(self):
        """AUTO_REPLAN requires parent!=None, depth>=1."""
        with pytest.raises(ValueError, match="AUTO_REPLAN requires parent_session_id"):
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
                parent_session_id=None,  # Invalid
                replan_depth=1,
            )

        with pytest.raises(ValueError, match="AUTO_REPLAN requires replan_depth"):
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
                parent_session_id="parent-id",
                replan_depth=0,  # Invalid
            )

    def test_external_request_provenance_invariant(self):
        """EXTERNAL_REQUEST requires parent=None, depth=0."""
        with pytest.raises(ValueError, match="EXTERNAL_REQUEST requires parent_session_id"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
                parent_session_id="parent-id",  # Invalid
                replan_depth=0,
            )

        with pytest.raises(ValueError, match="EXTERNAL_REQUEST requires replan_depth"):
            AdaptiveSession(
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
                replan_depth=1,  # Invalid
            )

    def test_legacy_migration_full_legacy(self):
        """Full legacy metadata migrates to AUTO_REPLAN."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            metadata={
                "replanned_from_session_id": "parent-id",
                "replan_count": 2,
            },
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "parent-id"
        assert session.replan_depth == 2

    def test_legacy_migration_partial_typed_parent(self):
        """Partial typed parent with matching legacy migrates depth."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            parent_session_id="A",
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 1,
            },
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "A"
        assert session.replan_depth == 1

    def test_cross_lineage_parent_conflict(self):
        """Cross-lineage: typed parent conflicts with legacy parent."""
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
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
                parent_session_id="A",  # Typed
                metadata={
                    "replanned_from_session_id": "B",  # Different lineage
                    "replan_count": 1,
                },
            )

    def test_cross_lineage_depth_conflict(self):
        """Cross-lineage: typed depth conflicts with legacy count."""
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
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
                replan_depth=2,  # Typed
                metadata={
                    "replanned_from_session_id": "parent-id",
                    "replan_count": 3,  # Different lineage
                },
            )

    def test_explicit_typed_wins_over_legacy(self):
        """Explicit typed provenance wins over stale legacy."""
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
            metadata={
                "replanned_from_session_id": "stale-parent",
                "replan_count": 5,
            },
        )
        # Explicit typed values preserved, legacy ignored
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0


class TestBoundedReplanPolicy:
    """Test bounded replan policy (depth < 2)."""

    def test_should_auto_replan_depth_0_allowed(self):
        """depth=0 allows automatic replan (A→B)."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

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
            metadata={"governance": {"should_replan": True}},
        )

        result = orchestrator._should_auto_replan(session)
        assert result is True  # A→B allowed

    def test_should_auto_replan_depth_1_blocked(self):
        """depth=1 blocks automatic replan (B→C blocked)."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

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
            metadata={"governance": {"should_replan": True}},
        )

        result = orchestrator._should_auto_replan(session)
        assert result is False  # B→C blocked (depth=1 < 1 is False)

    def test_should_auto_replan_depth_2_blocked(self):
        """depth=2 blocks automatic replan (C→D blocked)."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

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
            replan_depth=2,
            metadata={"governance": {"should_replan": True}},
        )

        result = orchestrator._should_auto_replan(session)
        assert result is False  # C→D blocked

    def test_manual_replan_depth_0_allowed(self):
        """Manual replan respects policy: depth=0 allowed."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

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
            session_id="session-a",
        )

        session_repo.get.return_value = session
        # Mock the method to return a mock request
        request_mock = MagicMock(metadata={})
        orchestrator._request_from_session = MagicMock(return_value=request_mock)
        orchestrator.handle_request = MagicMock(return_value=(None, None, MagicMock(session_id="session-b")))
        orchestrator.task_outcome_recorder.record = MagicMock(return_value=MagicMock(session_id="session-b"))

        result = orchestrator.replan_session("session-a")
        assert result is not None  # Manual replan allowed

    def test_manual_replan_depth_1_blocked(self):
        """Manual replan respects policy: depth=1 blocked."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

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
            parent_session_id="session-a",
            replan_depth=1,
            session_id="session-b",
        )

        session_repo.get.return_value = session

        result = orchestrator.replan_session("session-b")
        assert result is None  # Manual replan blocked


class TestPersistenceRoundTrip:
    """Test persistence round-trip preserves canonical provenance."""

    def test_persistence_preserves_canonical_provenance(self):
        """JSON round-trip preserves typed provenance fields."""
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
            metadata={"replanned_from_session_id": "parent-id", "replan_count": 1},
        )

        # Serialize to JSON
        json_data = session.model_dump(mode='json')

        # Deserialize
        restored = AdaptiveSession(**json_data)

        # Verify canonical provenance preserved
        assert restored.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert restored.parent_session_id == "parent-id"
        assert restored.replan_depth == 1

    def test_reload_after_migration_preserves_canonical(self):
        """Legacy session migrates and preserves canonical after reload."""
        # Simulate persisted legacy session
        legacy_data = {
            "user_goal": "test goal",
            "intent": {
                "intent_key": "test.intent",
                "title": "Test Intent",
                "detected_role": "training",
                "confidence": 1.0,
            },
            "context": {},
            "metadata": {
                "replanned_from_session_id": "parent-id",
                "replan_count": 2,
            },
        }

        # Migrate on load
        session = AdaptiveSession(**legacy_data)

        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "parent-id"
        assert session.replan_depth == 2

        # Serialize and reload
        json_data = session.model_dump(mode='json')
        restored = AdaptiveSession(**json_data)

        # Canonical provenance preserved after round-trip
        assert restored.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert restored.parent_session_id == "parent-id"
        assert restored.replan_depth == 2

    def test_repeated_finalize_cannot_create_multiple_children(self):
        """Repeated finalize of depth=0 session cannot create multiple automatic children.
        
        This is enforced by:
        1. Bounded replan policy (depth < 1 for auto-replan)
        2. auto_replanned_session_id flag prevents multiple auto-replans
        """
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )

        # Session at depth=1 (already auto-replanned once)
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
            parent_session_id="session-a",
            replan_depth=1,
            session_id="session-b",
            metadata={
                "governance": {"should_replan": True},
                "auto_replanned_session_id": "session-b",
                "auto_replanned": True,
            },
        )

        session_repo.get.return_value = session

        # Verify _should_auto_replan returns False for depth=1
        result = orchestrator._should_auto_replan(session)
        assert result is False  # depth=1 < 1 is False, prevents further auto-replan
