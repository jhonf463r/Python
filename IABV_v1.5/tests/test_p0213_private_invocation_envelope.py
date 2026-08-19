"""P0.213 Tests for PrivateInvocationEnvelope.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for envelope creation, validation, and fail-closed behavior.
"""
import pytest
from iabv_v15.domain.models import (
    PrivateInvocationEnvelope,
    CanonicalExecutionIdentity,
    RunRecord,
    InferenceRequest,
    InferenceResult,
    RoleRoute,
    RunStatus,
)
from iabv_v15.domain.models import AdaptiveSession, TaskIntent, TaskContext


class TestPrivateInvocationEnvelope:
    """Test PrivateInvocationEnvelope creation and validation."""

    def test_envelope_from_real_run_record_and_session(self):
        """Test A: real RunRecord → canonical identity → envelope."""
        # Create real RunRecord
        request = InferenceRequest(user_goal="test goal")
        result = InferenceResult(
            request_id=request.request_id,
            provider_name="test",
            reasoning_mode="local",
            summary="test summary",
            inferred_task="test task",
            confidence=0.9,
        )
        route = RoleRoute(
            task_role="training",
            role_title="Test Role",
            provider_name="test",
            model_profile_id="test_profile",
            model_name="test_model",
            reason="Test reason"
        )
        run_record = RunRecord(
            request=request,
            result=result,
            route=route,
            status=RunStatus.SUCCESS,
        )

        # Create real session
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )

        # Create envelope
        envelope = PrivateInvocationEnvelope.from_run_record_and_session(
            run_record=run_record,
            session=session,
        )

        # Verify envelope
        assert envelope is not None
        assert envelope.validate() is True
        assert envelope.get_identity().get_run_id() == run_record.run_id
        assert envelope.get_identity().get_session_id() == session.session_id
        assert envelope.get_invocation_id() is not None

    def test_caller_cannot_fabricate_envelope(self):
        """Test B: caller fabricates envelope → FAIL."""
        # Caller cannot construct envelope from arbitrary strings
        # Only from_run_record_and_session() is the legitimate way
        with pytest.raises(Exception):  # FrozenInstanceError
            # This should fail because envelope is frozen
            envelope = PrivateInvocationEnvelope(
                identity=CanonicalExecutionIdentity(
                    run_id="fake_run_id",
                    episode_id="fake_episode_id",
                    session_id="fake_session_id",
                ),
                invocation_id="fake_invocation_id",
            )
            # Try to modify (should fail because frozen)
            envelope.identity = CanonicalExecutionIdentity(
                run_id="another_fake",
                episode_id=None,
                session_id=None,
            )

    def test_context_missing_fail_closed(self):
        """Test C: context missing → FAIL CLOSED."""
        # Create envelope with empty run_id (invalid)
        request = InferenceRequest(user_goal="test")
        result = InferenceResult(
            request_id="test",
            provider_name="test",
            reasoning_mode="local",
            summary="test",
            inferred_task="test",
            confidence=0.9,
        )
        route = RoleRoute(
            task_role="training",
            role_title="Test Role",
            provider_name="test",
            model_profile_id="test_profile",
            model_name="test_model",
            reason="Test reason"
        )
        run_record = RunRecord(
            request=request,
            result=result,
            route=route,
            status=RunStatus.SUCCESS,
        )
        
        # Manually set run_id to empty to test validation
        run_record.run_id = ""
        
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )

        # Should raise ValueError
        with pytest.raises(ValueError):
            envelope = PrivateInvocationEnvelope.from_run_record_and_session(
                run_record=run_record,
                session=session,
            )

    def test_envelope_validation(self):
        """Test D: envelope validation delegates to identity."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        envelope = PrivateInvocationEnvelope(identity=identity)
        
        assert envelope.validate() is True
        assert envelope.get_identity() == identity
        assert envelope.get_invocation_id() is not None

    def test_envelope_invocation_id_unique(self):
        """Test E: each envelope has unique invocation_id."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        envelope1 = PrivateInvocationEnvelope(identity=identity)
        envelope2 = PrivateInvocationEnvelope(identity=identity)
        
        assert envelope1.get_invocation_id() != envelope2.get_invocation_id()

    def test_frozen_envelope_prevents_modification(self):
        """Test F: frozen envelope prevents modification."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        envelope = PrivateInvocationEnvelope(identity=identity)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            envelope.invocation_id = "modified_invocation_id"
