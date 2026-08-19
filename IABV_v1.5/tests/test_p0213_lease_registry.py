"""P0.213 Tests for LeaseRegistry.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for thread-safe lease registry for InternalMcpInvocation storage.
"""
import pytest
from iabv_v15.infra.ipc.lease_registry import LeaseRegistry
from iabv_v15.domain.models import InternalMcpInvocation, CanonicalExecutionIdentity


class TestLeaseRegistry:
    """Test LeaseRegistry storage and lifecycle management."""

    def test_singleton_pattern(self):
        """Test A: singleton pattern ensures single instance."""
        registry1 = LeaseRegistry()
        registry2 = LeaseRegistry()
        
        assert registry1 is registry2

    def test_register_invocation(self):
        """Test B: register new invocation lease."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        result = registry.register(invocation)
        
        assert result is True
        assert registry.size() == 1

    def test_register_duplicate_invocation(self):
        """Test C: duplicate invocation_id rejected."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        # First registration succeeds
        assert registry.register(invocation) is True
        
        # Second registration with same invocation_id fails
        assert registry.register(invocation) is False

    def test_consume_invocation(self):
        """Test D: consume invocation lease (single-use)."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        registry.register(invocation)
        
        # Consume succeeds
        consumed = registry.consume(invocation.invocation_id)
        assert consumed is not None
        assert consumed.consumed is True
        
        # Second consume fails (single-use)
        consumed_again = registry.consume(invocation.invocation_id)
        assert consumed_again is None

    def test_get_invocation(self):
        """Test E: get invocation without consuming."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        registry.register(invocation)
        
        # Get without consuming
        retrieved = registry.get(invocation.invocation_id)
        assert retrieved is not None
        assert retrieved.consumed is False

    def test_get_current_invocation(self):
        """Test F: get current (most recently registered) invocation."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity1 = CanonicalExecutionIdentity(
            run_id="test_run_id_1",
            episode_id="test_episode_id_1",
            session_id="test_session_id_1"
        )
        
        identity2 = CanonicalExecutionIdentity(
            run_id="test_run_id_2",
            episode_id="test_episode_id_2",
            session_id="test_session_id_2"
        )
        
        invocation1 = InternalMcpInvocation(
            canonical_identity=identity1,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        invocation2 = InternalMcpInvocation(
            canonical_identity=identity2,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        registry.register(invocation1)
        registry.register(invocation2)
        
        # Get current should return the most recently registered
        current = registry.get_current()
        assert current is not None
        assert current.invocation_id == invocation2.invocation_id

    def test_remove_invocation(self):
        """Test G: remove invocation from registry."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        registry.register(invocation)
        assert registry.size() == 1
        
        # Remove succeeds
        assert registry.remove(invocation.invocation_id) is True
        assert registry.size() == 0
        
        # Remove non-existent fails
        assert registry.remove(invocation.invocation_id) is False

    def test_clear_all_invocations(self):
        """Test H: clear all invocations."""
        registry = LeaseRegistry()
        registry.clear()
        
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        registry.register(invocation)
        assert registry.size() == 1
        
        registry.clear()
        assert registry.size() == 0
