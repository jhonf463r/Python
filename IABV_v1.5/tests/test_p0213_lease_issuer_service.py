"""P0.213 Tests for LeaseIssuerService.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for lease issuance and canonical identity resolution.
"""
import pytest
from iabv_v15.infra.ipc.lease_issuer_service import LeaseIssuerService
from iabv_v15.domain.models import (
    InternalMcpInvocation,
    CanonicalExecutionIdentity,
    RunRecord,
    InferenceRequest,
    InferenceResult,
    RoleRoute,
    RunStatus,
    AdaptiveSession,
    TaskIntent,
    TaskContext,
)


class TestLeaseIssuerService:
    """Test LeaseIssuerService issuance and identity resolution."""

    def test_singleton_pattern(self):
        """Test A: singleton pattern ensures single instance."""
        service1 = LeaseIssuerService()
        service2 = LeaseIssuerService()
        
        assert service1 is service2

    def test_issue_lease_from_canonical_objects(self):
        """Test B: issue lease from RunRecord and AdaptiveSession."""
        service = LeaseIssuerService()
        service.clear_leases()
        
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
        
        # Issue lease
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope"
        )
        
        # Verify lease
        assert lease is not None
        assert lease.validate() is True
        assert lease.canonical_identity.get_run_id() == run_record.run_id
        assert lease.canonical_identity.get_session_id() == session.session_id
        assert lease.producer_scope == "test_scope"

    def test_issue_lease_with_custom_ttl(self):
        """Test C: issue lease with custom TTL."""
        service = LeaseIssuerService()
        service.clear_leases()
        
        # Create minimal RunRecord and session
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
        
        session = AdaptiveSession(
            user_goal="test",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )
        
        # Issue lease with 60 second TTL
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope",
            ttl_seconds=60
        )
        
        assert lease.expires_at_utc is not None
        assert lease.is_expired() is False

    def test_validate_lease(self):
        """Test D: validate lease."""
        service = LeaseIssuerService()
        service.clear_leases()
        
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
        
        session = AdaptiveSession(
            user_goal="test",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )
        
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope"
        )
        
        assert service.validate_lease(lease) is True

    def test_consume_lease(self):
        """Test E: consume lease."""
        service = LeaseIssuerService()
        service.clear_leases()
        
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
        
        session = AdaptiveSession(
            user_goal="test",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )
        
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope"
        )
        
        # Consume succeeds
        consumed = service.consume_lease(lease.invocation_id)
        assert consumed is not None
        assert consumed.consumed is True

    def test_get_current_lease(self):
        """Test F: get current lease."""
        service = LeaseIssuerService()
        service.clear_leases()
        
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
        
        session = AdaptiveSession(
            user_goal="test",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )
        
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope"
        )
        
        current = service.get_current_lease()
        assert current is not None
        assert current.invocation_id == lease.invocation_id

    def test_revoke_lease(self):
        """Test G: revoke lease."""
        service = LeaseIssuerService()
        service.clear_leases()
        
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
        
        session = AdaptiveSession(
            user_goal="test",
            intent=TaskIntent(intent_key="test"),
            context=TaskContext(),
        )
        
        lease = service.issue_lease(
            run_record=run_record,
            session=session,
            producer_scope="test_scope"
        )
        
        # Revoke succeeds
        assert service.revoke_lease(lease.invocation_id) is True
        
        # Get returns None after revocation
        retrieved = service.get_lease(lease.invocation_id)
        assert retrieved is None
