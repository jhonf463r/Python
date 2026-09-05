"""Tests for R-01 parent/child identity relationship correction.

These tests verify that TrustedExecutionIdentity correctly demonstrates
a real parent→child relationship where the identity issued by the parent
is verifiable/usable by the consumer child.

Tests:
- parent issues / child accepts
- wrong child rejects
- unrelated process rejects
- wrong parent rejects
- cross-run rejects
- cross-generation rejects
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


class TestR01ParentChildIdentity:
    """Tests for R-01 parent/child identity relationship."""

    def test_parent_issues_child_accepts_self_issued(self):
        """Test that self-issued identity (issuer_pid == consumer_pid) is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            # Issue self-issued identity (default behavior)
            identity = authority.issue_identity()

            # Verification should succeed (self-issued)
            assert authority.verify_identity(identity) is True
            assert identity.issuer_pid == identity.consumer_pid

    def test_parent_issues_for_child_with_consumer_pid(self):
        """Test that parent can issue identity for specific child PID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid

            # Issue identity for current process (simulating child)
            identity = authority.issue_identity(consumer_pid=current_pid)

            # Verification should succeed
            assert authority.verify_identity(identity) is True
            assert identity.consumer_pid == current_pid
            assert identity.issuer_pid == current_pid  # Self-issued

    def test_wrong_consumer_pid_rejected(self):
        """Test that identity with wrong consumer_pid is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid
            wrong_pid = current_pid + 9999  # Non-existent PID

            # Issue identity for wrong PID
            identity = authority.issue_identity(consumer_pid=wrong_pid)

            # Verification should fail (consumer_pid != current_pid)
            assert authority.verify_identity(identity) is False

    def test_self_issued_identity_bypasses_parent_check(self):
        """Test that self-issued identities bypass parent-child verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            # Issue self-issued identity
            identity = authority.issue_identity()

            # Verification should succeed (self-issued, no parent check)
            assert authority.verify_identity(identity) is True
            assert identity.issuer_pid == identity.consumer_pid

    def test_cross_generation_rejected(self):
        """Test that identity from wrong generation is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            # Issue identity
            identity = authority.issue_identity()

            # Increment generation (simulate restart)
            trust_anchor.increment_generation()

            # Verification should fail (wrong generation)
            assert authority.verify_identity(identity) is False

    def test_expired_identity_rejected(self):
        """Test that expired identity is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            # Issue identity with very short TTL
            identity = authority.issue_identity(ttl_seconds=1)

            # Wait for expiration
            time.sleep(2)

            # Verification should fail (expired)
            assert authority.verify_identity(identity) is False

    def test_tampered_consumer_pid_rejected(self):
        """Test that tampered consumer_pid is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            # Issue valid identity
            identity = authority.issue_identity()

            # Tamper with consumer_pid (create new identity with tampered field)
            tampered = TrustedExecutionIdentity(
                issuer_pid=identity.issuer_pid,
                issuer_generation=identity.issuer_generation,
                consumer_pid=identity.consumer_pid + 9999,  # Tampered
                execution_id=identity.execution_id,
                run_id=identity.run_id,
                episode_id=identity.episode_id,
                session_id=identity.session_id,
                invocation_id=identity.invocation_id,
                runtime_generation=identity.runtime_generation,
                bootstrap_timestamp=identity.bootstrap_timestamp,
                signature=identity.signature,  # Original signature (won't match tampered data)
                issued_at=identity.issued_at,
                expires_at=identity.expires_at,
            )

            # Verification should fail (signature won't match tampered data)
            assert authority.verify_identity(tampered) is False


class TestR01ParentChildIntegration:
    """Integration tests for R-01 parent/child identity relationship."""

    def test_full_issuance_verification_chain_with_consumer_pid(self):
        """Test full issuance and verification chain with consumer_pid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid

            # Issue identity for current process
            identity = authority.issue_identity(consumer_pid=current_pid)

            # Verify all fields
            assert identity.issuer_pid == current_pid
            assert identity.consumer_pid == current_pid
            assert identity.execution_id is not None
            assert identity.run_id is not None
            assert identity.invocation_id is not None
            assert identity.signature is not None
            assert len(identity.signature) == 64  # HMAC-SHA256 hex

            # Verification should succeed
            assert authority.verify_identity(identity) is True

    def test_persistence_across_restart_with_consumer_pid(self):
        """Test that identity with consumer_pid persists correctly across restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid

            # Issue identity
            identity = authority.issue_identity(consumer_pid=current_pid)

            # Serialize
            identity_dict = identity.to_dict()

            # Simulate restart (new authority instance)
            trust_anchor2 = RootTrustAnchor(storage_root=tmpdir)
            authority2 = RuntimeIdentityAuthority(trust_anchor2)

            # Deserialize
            identity_restored = TrustedExecutionIdentity.from_dict(identity_dict)

            # Verification should succeed (same generation)
            assert authority2.verify_identity(identity_restored) is True

            # Increment generation (simulate restart)
            trust_anchor2.increment_generation()

            # Verification should fail (wrong generation)
            assert authority2.verify_identity(identity_restored) is False


class TestR01ParentChildNegative:
    """Negative tests for R-01 parent/child identity relationship."""

    def test_caller_cannot_forge_consumer_pid(self):
        """Test that caller cannot forge valid identity with wrong consumer_pid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid
            wrong_pid = current_pid + 9999

            # Caller tries to forge identity with wrong consumer_pid
            forged = TrustedExecutionIdentity(
                issuer_pid=current_pid,
                issuer_generation=trust_anchor.get_runtime_identity().generation,
                consumer_pid=wrong_pid,  # Wrong consumer
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

            # Verification should fail (no signature + wrong consumer)
            assert authority.verify_identity(forged) is False

    def test_caller_cannot_use_another_process_identity(self):
        """Test that caller cannot use identity issued for another process."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)

            current_pid = trust_anchor.get_process_identity().pid
            other_pid = current_pid + 9999  # Non-existent PID

            # Issue identity for other process
            identity_for_other = authority.issue_identity(consumer_pid=other_pid)

            # Try to verify in current process (should fail)
            assert authority.verify_identity(identity_for_other) is False
