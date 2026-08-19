"""P0.213 Tests for InternalMcpInvocation.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for internal MCP invocation lease for canonical identity transport.
"""
import pytest
from datetime import datetime, timezone, timedelta
from iabv_v15.domain.models import InternalMcpInvocation, CanonicalExecutionIdentity


class TestInternalMcpInvocation:
    """Test InternalMcpInvocation lease lifecycle."""

    def test_valid_invocation(self):
        """Test A: valid invocation lease."""
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
        
        assert invocation.validate() is True
        assert invocation.invocation_id is not None
        assert invocation.consumed is False

    def test_single_use_consumption(self):
        """Test B: single-use invocation_id prevents replay."""
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
        
        # First consume succeeds
        assert invocation.consume() is True
        assert invocation.consumed is True
        
        # Second consume fails (single-use)
        assert invocation.consume() is False
        
        # Validation fails after consumption
        assert invocation.validate() is False

    def test_expiration(self):
        """Test C: expiration for security."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        # Create expired invocation
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope",
            expires_at_utc=expires_at
        )
        
        assert invocation.is_expired() is True
        assert invocation.validate() is False

    def test_producer_pid_validation(self):
        """Test D: producer PID validation."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        # Invalid PID (zero)
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=0,
            producer_scope="test_scope"
        )
        assert invocation.validate() is False
        
        # Invalid PID (negative)
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=-1,
            producer_scope="test_scope"
        )
        assert invocation.validate() is False

    def test_producer_scope_validation(self):
        """Test E: producer scope validation."""
        identity = CanonicalExecutionIdentity(
            run_id="test_run_id",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        # Empty scope
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope=""
        )
        assert invocation.validate() is False
        
        # Whitespace-only scope
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="   "
        )
        assert invocation.validate() is False

    def test_serialization_roundtrip(self):
        """Test F: serialization roundtrip for IPC."""
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
        
        # Serialize
        data = invocation.to_dict()
        
        # Deserialize
        restored = InternalMcpInvocation.from_dict(data)
        
        assert restored.invocation_id == invocation.invocation_id
        assert restored.canonical_identity.run_id == invocation.canonical_identity.run_id
        assert restored.producer_pid == invocation.producer_pid
        assert restored.producer_scope == invocation.producer_scope

    def test_invalid_canonical_identity(self):
        """Test G: invalid canonical identity fails validation."""
        # Invalid identity (empty run_id)
        identity = CanonicalExecutionIdentity(
            run_id="",
            episode_id="test_episode_id",
            session_id="test_session_id"
        )
        
        invocation = InternalMcpInvocation(
            canonical_identity=identity,
            producer_pid=12345,
            producer_scope="test_scope"
        )
        
        assert invocation.validate() is False
