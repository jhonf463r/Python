"""Tests for TrustedExecutionIdentity (PHASE 2).

These tests verify that TrustedExecutionIdentity is cryptographically bound
and can only be issued by the trusted runtime authority.
"""
from __future__ import annotations

import tempfile
import time
from uuid import uuid4

import pytest

from iabv_v15.services.evolution.root_trust_anchor import RootTrustAnchor
from iabv_v15.services.evolution.trusted_execution_identity import (
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)


class TestTrustedExecutionIdentityUnit:
    """Unit tests for TrustedExecutionIdentity."""
    
    def test_identity_issuance(self):
        """Test that identity can be issued by authority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Identity should have all required fields
            assert identity.execution_id is not None
            assert identity.run_id is not None
            assert identity.invocation_id is not None
            assert identity.runtime_generation == 0
            assert identity.bootstrap_timestamp > 0
            assert identity.signature != ""
            assert identity.issued_at > 0
            assert identity.expires_at > identity.issued_at
    
    def test_identity_with_custom_run_id(self):
        """Test that identity can be issued with custom run_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            custom_run_id = str(uuid4())
            identity = authority.issue_identity(run_id=custom_run_id)
            
            # run_id should match custom value
            assert identity.run_id == custom_run_id
    
    def test_identity_with_episode_session(self):
        """Test that identity can be issued with episode and session IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            episode_id = str(uuid4())
            session_id = str(uuid4())
            identity = authority.issue_identity(
                episode_id=episode_id,
                session_id=session_id,
            )
            
            # IDs should match
            assert identity.episode_id == episode_id
            assert identity.session_id == session_id
    
    def test_identity_expiration(self):
        """Test that identity has correct expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            ttl_seconds = 300
            identity = authority.issue_identity(ttl_seconds=ttl_seconds)
            
            # Expiration should be approximately TTL seconds after issuance
            expected_expires_at = identity.issued_at + ttl_seconds
            assert abs(identity.expires_at - expected_expires_at) < 1.0
    
    def test_identity_serialization(self):
        """Test that identity can be serialized and deserialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Serialize
            data = identity.to_dict()
            
            # Deserialize
            restored = TrustedExecutionIdentity.from_dict(data)
            
            # Should be equal
            assert restored.execution_id == identity.execution_id
            assert restored.run_id == identity.run_id
            assert restored.signature == identity.signature


class TestTrustedExecutionIdentityVerification:
    """Tests for identity verification."""
    
    def test_valid_identity_verifies(self):
        """Test that valid identity verifies successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Verification should succeed
            assert authority.verify_identity(identity) is True
    
    def test_fabricated_identity_rejected(self):
        """Test that caller-fabricated identity is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Caller fabricates identity
            fabricated = TrustedExecutionIdentity(
                issuer_pid=trust_anchor.get_process_identity().pid,
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
            
            # Verification should fail
            assert authority.verify_identity(fabricated) is False
    
    def test_wrong_generation_rejected(self):
        """Test that identity with wrong generation is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity
            identity = authority.issue_identity()
            
            # Increment generation (simulate restart)
            trust_anchor.increment_generation()
            
            # Verification should fail (wrong generation)
            assert authority.verify_identity(identity) is False
    
    def test_wrong_bootstrap_rejected(self):
        """Test that identity with wrong bootstrap timestamp is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity
            identity = authority.issue_identity()
            
            # Tamper with bootstrap timestamp
            tampered = TrustedExecutionIdentity.from_dict(identity.to_dict())
            tampered_dict = tampered.to_dict()
            tampered_dict['bootstrap_timestamp'] = 0.0
            tampered = TrustedExecutionIdentity.from_dict(tampered_dict)
            
            # Verification should fail
            assert authority.verify_identity(tampered) is False
    
    def test_wrong_pid_rejected(self):
        """Test that identity with wrong issuer PID is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity
            identity = authority.issue_identity()
            
            # Tamper with issuer PID
            tampered = TrustedExecutionIdentity.from_dict(identity.to_dict())
            tampered_dict = tampered.to_dict()
            tampered_dict['issuer_pid'] = 99999
            tampered = TrustedExecutionIdentity.from_dict(tampered_dict)
            
            # Verification should fail
            assert authority.verify_identity(tampered) is False
    
    def test_expired_identity_rejected(self):
        """Test that expired identity is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity with short TTL
            identity = authority.issue_identity(ttl_seconds=1)
            
            # Wait for expiration
            time.sleep(2)
            
            # Verification should fail
            assert authority.verify_identity(identity) is False
    
    def test_tampered_signature_rejected(self):
        """Test that identity with tampered signature is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity
            identity = authority.issue_identity()
            
            # Tamper with signature
            tampered = TrustedExecutionIdentity.from_dict(identity.to_dict())
            tampered_dict = tampered.to_dict()
            tampered_dict['signature'] = "0" * 64
            tampered = TrustedExecutionIdentity.from_dict(tampered_dict)
            
            # Verification should fail
            assert authority.verify_identity(tampered) is False


class TestTrustedExecutionIdentityNegative:
    """Negative tests for TrustedExecutionIdentity."""
    
    def test_caller_cannot_forge_signature(self):
        """Test that caller cannot forge valid signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Caller tries to forge signature
            forged_signature = "0" * 64
            
            identity = TrustedExecutionIdentity(
                issuer_pid=trust_anchor.get_process_identity().pid,
                issuer_generation=trust_anchor.get_runtime_identity().generation,
                execution_id=str(uuid4()),
                run_id=str(uuid4()),
                episode_id=str(uuid4()),
                session_id=str(uuid4()),
                invocation_id=str(uuid4()),
                runtime_generation=trust_anchor.get_runtime_identity().generation,
                bootstrap_timestamp=trust_anchor.get_runtime_identity().bootstrap_timestamp,
                signature=forged_signature,
                issued_at=time.time(),
                expires_at=time.time() + 3600,
            )
            
            # Verification should fail
            assert authority.verify_identity(identity) is False
    
    def test_caller_cannot_forge_generation(self):
        """Test that caller cannot forge correct generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Caller tries to use wrong generation
            wrong_generation = trust_anchor.get_runtime_identity().generation + 999
            
            identity = TrustedExecutionIdentity(
                issuer_pid=trust_anchor.get_process_identity().pid,
                issuer_generation=wrong_generation,
                execution_id=str(uuid4()),
                run_id=str(uuid4()),
                episode_id=str(uuid4()),
                session_id=str(uuid4()),
                invocation_id=str(uuid4()),
                runtime_generation=wrong_generation,
                bootstrap_timestamp=trust_anchor.get_runtime_identity().bootstrap_timestamp,
                signature="",  # No signature
                issued_at=time.time(),
                expires_at=time.time() + 3600,
            )
            
            # Verification should fail
            assert authority.verify_identity(identity) is False


class TestTrustedExecutionIdentityIntegration:
    """Integration tests for TrustedExecutionIdentity."""
    
    def test_full_issuance_verification_chain(self):
        """Test full issuance and verification chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            # Issue identity
            identity = authority.issue_identity()
            
            # Verify identity
            is_valid = authority.verify_identity(identity)
            
            # Should be valid
            assert is_valid is True
    
    def test_persistence_across_restart(self):
        """Test that identity from old runtime is rejected after restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First runtime
            trust_anchor1 = RootTrustAnchor(storage_root=tmpdir)
            authority1 = RuntimeIdentityAuthority(trust_anchor1)
            identity1 = authority1.issue_identity()
            
            # Simulate restart (increment generation)
            trust_anchor1.increment_generation()
            
            # Second runtime
            trust_anchor2 = RootTrustAnchor(storage_root=tmpdir)
            authority2 = RuntimeIdentityAuthority(trust_anchor2)
            
            # Old identity should be rejected
            assert authority2.verify_identity(identity1) is False
            
            # New identity should be accepted
            identity2 = authority2.issue_identity()
            assert authority2.verify_identity(identity2) is True


class TestTrustedExecutionIdentitySecurity:
    """Security tests for TrustedExecutionIdentity."""
    
    def test_signature_length(self):
        """Test that signature is 64 characters (SHA256 hex)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Signature should be 64 characters
            assert len(identity.signature) == 64
    
    def test_signature_hex_format(self):
        """Test that signature is hex-encoded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Signature should be hex characters only
            assert all(c in '0123456789abcdef' for c in identity.signature)
    
    def test_different_identities_different_signatures(self):
        """Test that different identities have different signatures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity1 = authority.issue_identity()
            identity2 = authority.issue_identity()
            
            # Signatures should be different
            assert identity1.signature != identity2.signature
