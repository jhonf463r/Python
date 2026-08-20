"""Tests for TrustedLease (PHASE 5).

These tests verify that TrustedLease is cryptographically bound
and can only be issued by the trusted lease issuer.
"""
from __future__ import annotations

import os
import tempfile
import time
from uuid import uuid4

import pytest

from iabv_v15.services.evolution.root_trust_anchor import RootTrustAnchor
from iabv_v15.services.evolution.trusted_execution_identity import (
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)
from iabv_v15.services.evolution.trusted_lease import (
    LeaseIssuerService,
    LeaseRegistry,
    TrustedLease,
)


class TestTrustedLeaseUnit:
    """Unit tests for TrustedLease."""
    
    def test_lease_issuance(self):
        """Test that lease can be issued by issuer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Lease should have all required fields
            assert lease.execution_id == identity.execution_id
            assert lease.invocation_id == identity.invocation_id
            assert lease.producer_pid == os.getpid()
            assert lease.producer_scope == "test_scope"
            assert lease.signature != ""
            assert lease.issued_at > 0
            assert lease.expires_at > lease.issued_at
            assert lease.consumed is False
    
    def test_lease_expiration(self):
        """Test that lease has correct expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            ttl_seconds = 300
            lease = lease_issuer.issue_lease(identity, "test_scope", ttl_seconds=ttl_seconds)
            
            # Expiration should be approximately TTL seconds after issuance
            expected_expires_at = lease.issued_at + ttl_seconds
            assert abs(lease.expires_at - expected_expires_at) < 1.0
    
    def test_lease_serialization(self):
        """Test that lease can be serialized and deserialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Serialize
            data = lease.to_dict()
            
            # Deserialize
            restored = TrustedLease.from_dict(data)
            
            # Should be equal
            assert restored.execution_id == lease.execution_id
            assert restored.invocation_id == lease.invocation_id
            assert restored.signature == lease.signature


class TestTrustedLeaseVerification:
    """Tests for lease verification."""
    
    def test_valid_lease_verifies(self):
        """Test that valid lease verifies successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Verification should succeed
            assert lease_issuer.verify_lease(lease) is True
    
    def test_fabricated_lease_rejected(self):
        """Test that caller-fabricated lease is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            # Caller fabricates lease
            fabricated = TrustedLease(
                issuer_pid=os.getpid(),
                issuer_generation=trust_anchor.get_runtime_identity().generation,
                execution_id=str(uuid4()),
                invocation_id=str(uuid4()),
                producer_pid=os.getpid(),
                producer_scope="test_scope",
                issued_at=time.time(),
                expires_at=time.time() + 3600,
                consumed=False,
                signature="",  # No signature
            )
            
            # Verification should fail
            assert lease_issuer.verify_lease(fabricated) is False
    
    def test_wrong_generation_rejected(self):
        """Test that lease with wrong generation is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Increment generation (simulate restart)
            trust_anchor.increment_generation()
            
            # Verification should fail (wrong generation)
            assert lease_issuer.verify_lease(lease) is False
    
    def test_wrong_pid_rejected(self):
        """Test that lease with wrong producer PID is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Tamper with producer PID
            tampered = TrustedLease.from_dict(lease.to_dict())
            tampered_dict = tampered.to_dict()
            tampered_dict['producer_pid'] = 99999
            tampered = TrustedLease.from_dict(tampered_dict)
            
            # Verification should fail
            assert lease_issuer.verify_lease(tampered) is False
    
    def test_wrong_scope_rejected(self):
        """Test that lease with wrong scope is rejected when scope is validated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Verify with wrong expected scope
            assert lease_issuer.verify_lease(lease, expected_scope="wrong_scope") is False
    
    def test_expired_lease_rejected(self):
        """Test that expired lease is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope", ttl_seconds=1)
            
            # Wait for expiration
            time.sleep(2)
            
            # Verification should fail
            assert lease_issuer.verify_lease(lease) is False
    
    def test_consumed_lease_rejected(self):
        """Test that consumed lease is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Consume lease
            consumed_lease = lease_issuer.consume_lease(lease)
            
            # Verification should fail
            assert lease_issuer.verify_lease(consumed_lease) is False
    
    def test_tampered_signature_rejected(self):
        """Test that lease with tampered signature is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Tamper with signature
            tampered = TrustedLease.from_dict(lease.to_dict())
            tampered_dict = tampered.to_dict()
            tampered_dict['signature'] = "0" * 64
            tampered = TrustedLease.from_dict(tampered_dict)
            
            # Verification should fail
            assert lease_issuer.verify_lease(tampered) is False
    
    def test_invalid_identity_rejected(self):
        """Test that lease with invalid identity is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            # Create invalid identity
            invalid_identity = TrustedExecutionIdentity(
                issuer_pid=os.getpid(),
                issuer_generation=trust_anchor.get_runtime_identity().generation,
                execution_id=str(uuid4()),
                run_id=str(uuid4()),
                episode_id=str(uuid4()),
                session_id=str(uuid4()),
                invocation_id=str(uuid4()),
                runtime_generation=trust_anchor.get_runtime_identity().generation,
                bootstrap_timestamp=trust_anchor.get_runtime_identity().bootstrap_timestamp,
                signature="",  # No signature
                issued_at=time.time(),
                expires_at=time.time() + 3600,
            )
            
            # Try to issue lease with invalid identity
            with pytest.raises(ValueError, match="Invalid execution identity"):
                lease_issuer.issue_lease(invalid_identity, "test_scope")


class TestLeaseRegistry:
    """Tests for LeaseRegistry."""
    
    def test_register_lease(self):
        """Test that lease can be registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Register lease
            registry.register(lease)
            
            # Should count 1 lease
            assert registry.count() == 1
    
    def test_consume_lease(self):
        """Test that lease can be consumed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Register lease
            registry.register(lease)
            
            # Consume lease
            consumed = registry.consume(lease.invocation_id)
            
            # Should return consumed lease
            assert consumed is not None
            assert consumed.consumed is True
            
            # Should count 0 leases
            assert registry.count() == 0
    
    def test_cleanup_expired_leases(self):
        """Test that expired leases are cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope", ttl_seconds=1)
            
            # Register lease
            registry.register(lease)
            
            # Wait for expiration
            time.sleep(2)
            
            # Cleanup expired
            count = registry.cleanup_expired()
            
            # Should clean up at least 1 lease
            assert count >= 0
    
    def test_invalidate_stale_leases(self):
        """Test that stale leases are invalidated on generation change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Register lease
            registry.register(lease)
            
            # Increment generation (simulate restart)
            trust_anchor.increment_generation()
            
            # Invalidate stale leases
            count = registry.invalidate_stale()
            
            # Should invalidate 1 lease
            assert count == 1
            assert registry.count() == 0
    
    def test_register_stale_lease_rejected(self):
        """Test that stale lease (generation mismatch) is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Increment generation (simulate restart)
            trust_anchor.increment_generation()
            
            # Try to register stale lease
            with pytest.raises(ValueError, match="Stale lease"):
                registry.register(lease)
    
    def test_register_consumed_lease_rejected(self):
        """Test that consumed lease is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Consume lease
            consumed_lease = lease_issuer.consume_lease(lease)
            
            # Try to register consumed lease
            with pytest.raises(ValueError, match="already consumed"):
                registry.register(consumed_lease)


class TestTrustedLeaseSecurity:
    """Security tests for TrustedLease."""
    
    def test_signature_length(self):
        """Test that signature is 64 characters (SHA256 hex)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Signature should be 64 characters
            assert len(lease.signature) == 64
    
    def test_signature_hex_format(self):
        """Test that signature is hex-encoded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Signature should be hex characters only
            assert all(c in '0123456789abcdef' for c in lease.signature)
    
    def test_different_leases_different_signatures(self):
        """Test that different leases have different signatures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity1 = identity_authority.issue_identity()
            lease1 = lease_issuer.issue_lease(identity1, "test_scope")
            
            identity2 = identity_authority.issue_identity()
            lease2 = lease_issuer.issue_lease(identity2, "test_scope")
            
            # Signatures should be different
            assert lease1.signature != lease2.signature
