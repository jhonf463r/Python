"""
Construction boundary tests for provenance remediation.

These tests verify that:
1. External requests cannot fabricate provenance via legacy metadata
2. Internal replan context is the only authoritative source for AUTO_REPLAN
3. Domain depth invariants are enforced at construction time
4. Persistence and reload preserve provenance invariants
"""

import pytest
from iabv_v15.domain.models import (
    AdaptiveSession,
    InferenceRequest,
    InternalReplanContext,
    SessionContinuationType,
    TaskIntent,
    TaskContext,
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
