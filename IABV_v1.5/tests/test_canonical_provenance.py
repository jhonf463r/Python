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
        """Full legacy metadata migrates to AUTO_REPLAN with depth capped at 1."""
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
        assert session.replan_depth == 1  # Capped at 1 by domain invariant

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
        """depth=2 is rejected at domain construction (C→D blocked by invariant)."""
        # With the new domain invariant, depth=2 is rejected at construction time
        # This test verifies the domain-level rejection
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
                parent_session_id="parent-id",
                replan_depth=2,
                metadata={"governance": {"should_replan": True}},
            )

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
        """Legacy session migrates with depth capped at 1 and preserves canonical after reload."""
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

        # Migrate on load (depth capped at 1 by domain invariant)
        session = AdaptiveSession(**legacy_data)

        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "parent-id"
        assert session.replan_depth == 1  # Capped at 1

        # Serialize and reload
        json_data = session.model_dump(mode='json')
        restored = AdaptiveSession(**json_data)

        # Canonical provenance preserved after round-trip
        assert restored.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert restored.parent_session_id == "parent-id"
        assert restored.replan_depth == 1

    def test_repeated_finalize_cannot_create_multiple_children(self):
        """Repeated finalize of depth=0 session cannot create multiple automatic children.
        
        This is enforced by typed idempotency state (auto_replan_child_session_id).
        After first finalize creates child B, second finalize should not create B2.
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

        # Session at depth=0 (eligible for auto-replan)
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
            metadata={
                "governance": {"should_replan": True},
            },
        )

        session_repo.get.return_value = session

        # First call: idempotency state is None, should allow auto-replan
        result = orchestrator._should_auto_replan(session)
        assert result is True  # depth=0 < 1 is True, idempotency=None

        # After first replan, idempotency state would be set
        session_with_child = session.model_copy(update={
            'auto_replan_child_session_id': 'session-b'
        })
        session_repo.get.return_value = session_with_child

        # Second call: idempotency state is set, should block even though depth=0
        result = orchestrator._should_auto_replan(session_with_child)
        assert result is False  # idempotency guard blocks re-entry

    def test_idempotency_guard_independent_from_legacy_metadata(self):
        """Typed idempotency guard is independent from legacy metadata flags.
        
        Even if legacy metadata indicates previous replan, typed idempotency
        state is the authoritative guard.
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

        # Session with legacy metadata but NO typed idempotency state
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
            auto_replan_child_session_id=None,  # Typed idempotency is None
            metadata={
                "governance": {"should_replan": True},
                "auto_replanned_session_id": "session-b",  # Legacy flag present
                "auto_replanned": True,  # Legacy flag present
            },
        )

        session_repo.get.return_value = session

        # Should allow auto-replan because typed idempotency is None
        # Legacy metadata is ignored for the guard decision
        result = orchestrator._should_auto_replan(session)
        assert result is True  # Typed idempotency=None allows, legacy ignored

    def test_persistence_preserves_idempotency_state(self):
        """JSON round-trip preserves typed idempotency state."""
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
            auto_replan_child_session_id="session-b",
        )

        # Serialize to JSON
        json_data = session.model_dump(mode='json')

        # Deserialize
        restored = AdaptiveSession(**json_data)

        # Verify idempotency state preserved
        assert restored.auto_replan_child_session_id == "session-b"

    def test_legacy_idempotency_migration(self):
        """Legacy auto_replanned_session_id migrates to typed field."""
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
                "auto_replanned_session_id": "session-b",
            },
        }

        session = AdaptiveSession(**legacy_data)

        # Should migrate legacy to typed field
        assert session.auto_replan_child_session_id == "session-b"

    def test_legacy_idempotency_without_child_id_no_invention(self):
        """Legacy replanned_automatically=True without child ID does NOT invent child ID."""
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
                "replanned_automatically": True,  # No child ID
            },
        }

        session = AdaptiveSession(**legacy_data)

        # Should NOT invent a child ID
        assert session.auto_replan_child_session_id is None


class TestCausalIndependence:
    """Test causal independence: canonical fields are authoritative over legacy metadata."""

    def test_canonical_fields_win_over_conflicting_legacy(self):
        """TEST A: Canonical fields valid + conflicting legacy metadata.
        
        Expected: canonical typed fields win.
        """
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
                "replanned_from_session_id": "stale-parent",  # Conflicts with typed
                "replan_count": 5,  # Conflicts with typed
                "replanned_automatically": True,  # Conflicts with typed
            },
        )
        # Canonical typed fields win
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_canonical_fields_without_legacy_same_decision(self):
        """TEST B: Canonical fields valid + legacy metadata removed.
        
        Expected: same canonical decision.
        """
        # With legacy metadata
        session_with_legacy = AdaptiveSession(
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
                "replanned_from_session_id": "parent-id",
                "replan_count": 1,
            },
        )

        # Without legacy metadata
        session_without_legacy = AdaptiveSession(
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

        # Same canonical decision
        assert session_with_legacy.continuation_type == session_without_legacy.continuation_type
        assert session_with_legacy.parent_session_id == session_without_legacy.parent_session_id
        assert session_with_legacy.replan_depth == session_without_legacy.replan_depth

    def test_canonical_fields_with_changed_legacy_same_decision(self):
        """TEST C: Canonical fields valid + legacy metadata changed.
        
        Expected: same canonical decision.
        """
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
                "replanned_from_session_id": "parent-id",
                "replan_count": 1,
            },
        )

        # Change legacy metadata
        session.metadata["replanned_from_session_id"] = "different-parent"
        session.metadata["replan_count"] = 99

        # Canonical decision unchanged
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_auto_replan_with_self_parent_rejected(self):
        """TEST D: AUTO_REPLAN with parent_session_id == session_id.
        
        Expected: rejection.
        """
        session_id = "session-a"
        with pytest.raises(ValueError, match="parent_session_id cannot equal session_id"):
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
                parent_session_id=session_id,  # Self-parent cycle
                replan_depth=1,
                session_id=session_id,
            )

    def test_auto_replan_child_self_reference_rejected(self):
        """TEST E: auto_replan_child_session_id == session_id.
        
        Expected: rejection.
        """
        session_id = "session-a"
        with pytest.raises(ValueError, match="auto_replan_child_session_id cannot equal session_id"):
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
                replan_depth=0,
                auto_replan_child_session_id=session_id,  # Self-child cycle
                session_id=session_id,
            )

    def test_change_legacy_metadata_no_change_to_canonical_decision(self):
        """TEST K: Change legacy metadata after canonical construction.
        
        Expected: no change to canonical replan decision.
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
            metadata={"governance": {"should_replan": True}},
        )

        session_repo.get.return_value = session

        # Initial decision
        result_initial = orchestrator._should_auto_replan(session)
        assert result_initial is True

        # Change legacy metadata
        session.metadata["replanned_from_session_id"] = "some-parent"
        session.metadata["replan_count"] = 5
        session.metadata["replanned_automatically"] = True

        # Canonical decision unchanged (still based on typed fields)
        result_after = orchestrator._should_auto_replan(session)
        assert result_after is True  # Still depth=0 < 1

    def test_depth_0_automatic_replan_allowed(self):
        """TEST F: depth=0 automatic replan.
        
        Expected: allowed.
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
        assert result is True  # depth=0 < 1 allows

    def test_depth_1_automatic_replan_blocked(self):
        """TEST G: depth=1 automatic replan.
        
        Expected: blocked.
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
        assert result is False  # depth=1 < 1 is False, blocked

    def test_depth_2_auto_replan_canonical_construction_rejected(self):
        """TEST H: depth=2 AUTO_REPLAN canonical construction is rejected by domain invariant.
        
        Expected: deterministic rejection (depth >= MAX_AUTO_REPLAN_DEPTH violates policy).
        """
        # depth=2 with AUTO_REPLAN is now rejected at domain construction time
        # by the new depth invariant (max depth = 1)
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
                parent_session_id="parent-id",
                replan_depth=2,
            )

    def test_persist_reload_preserves_canonical(self):
        """TEST I: Persist + reload AdaptiveSession.
        
        Expected: typed provenance and idempotency identity preserved exactly.
        """
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
            auto_replan_child_session_id="child-id",
            metadata={"replanned_from_session_id": "parent-id", "replan_count": 1},
        )

        # Serialize to JSON
        json_data = session.model_dump(mode='json')

        # Deserialize
        restored = AdaptiveSession(**json_data)

        # Verify typed provenance preserved exactly
        assert restored.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert restored.parent_session_id == "parent-id"
        assert restored.replan_depth == 1
        # Verify idempotency identity preserved exactly
        assert restored.auto_replan_child_session_id == "child-id"

    def test_direct_replan_session_depth_1_blocked(self):
        """TEST J: Call replan_session() directly at depth=1.
        
        Expected: cannot bypass the depth policy.
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

        # Direct replan_session() call at depth=1
        result = orchestrator.replan_session("session-b")
        assert result is None  # Blocked by depth policy (depth >= MAX_AUTO_REPLAN_DEPTH)
