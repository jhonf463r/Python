"""Tests for P0.213 V5 Phase 1: Trust Boundary Skeleton.

These tests verify that the skeleton components are properly defined
and follow the architecture contract.

Phase 1 Tests (L1 UNIT):
- Component interface verification
- Architecture contract compliance
- No duplicate authority
- Fail-closed placeholder behavior
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from iabv_v15.services.trust.root_trust_anchor import (
    ProcessIdentity,
    RootTrustAnchor,
    RuntimeIdentity,
)
from iabv_v15.services.trust.trusted_execution_identity import (
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)
from iabv_v15.services.trust.trusted_lease import (
    LeaseIssuerService,
    LeaseRegistry,
    TrustedLease,
)


class TestRootTrustAnchorSkeleton:
    """Tests for RootTrustAnchor skeleton."""
    
    def test_initialization_requires_storage_root(self):
        """Test that RootTrustAnchor requires storage_root."""
        with pytest.raises(ValueError, match="storage_root is required"):
            RootTrustAnchor(storage_root=None)
    
    def test_initialization_creates_storage_directory(self):
        """Test that RootTrustAnchor creates storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            assert Path(tmpdir).exists()
    
    def test_get_process_identity_returns_placeholder(self):
        """Test that get_process_identity returns placeholder (Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            identity = anchor.get_process_identity()
            assert identity.pid == 0
            assert identity.create_time == 0.0
            assert identity.ppid == 0
    
    def test_get_runtime_identity_returns_placeholder(self):
        """Test that get_runtime_identity returns placeholder (Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            identity = anchor.get_runtime_identity()
            assert identity.generation == 0
            assert identity.bootstrap_timestamp == 0.0
    
    def test_increment_generation_increments(self):
        """Test that increment_generation increments counter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            initial_generation = anchor.get_runtime_identity().generation
            anchor.increment_generation()
            new_generation = anchor.get_runtime_identity().generation
            assert new_generation == initial_generation + 1
    
    def test_get_secret_key_returns_placeholder(self):
        """Test that get_secret_key returns placeholder (Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            key = anchor.get_secret_key()
            assert key == b"placeholder"


class TestTrustedExecutionIdentitySkeleton:
    """Tests for TrustedExecutionIdentity skeleton."""
    
    def test_identity_issuance_returns_placeholder(self):
        """Test that issue_identity returns placeholder (Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            
            # Phase 1: Placeholder values
            assert identity.issuer_pid == 0
            assert identity.issuer_generation == 0
            assert identity.consumer_pid == 0
            assert identity.signature == "placeholder"
            assert identity.runtime_generation == 0
            assert identity.bootstrap_timestamp == 0.0
    
    def test_identity_verification_fails_closed(self):
        """Test that verify_identity returns False (fail-closed, Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = authority.issue_identity()
            is_valid = authority.verify_identity(identity)
            
            # Phase 1: Fail-closed
            assert is_valid is False


class TestTrustedLeaseSkeleton:
    """Tests for TrustedLease skeleton."""
    
    def test_lease_issuance_returns_placeholder(self):
        """Test that issue_lease returns placeholder (Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Phase 1: Placeholder values
            assert lease.signature == "placeholder"
            assert lease.issuer_generation == 0
            assert lease.consumed is False
    
    def test_lease_verification_fails_closed(self):
        """Test that verify_lease returns False (fail-closed, Phase 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            is_valid = lease_issuer.verify_lease(lease)
            
            # Phase 1: Fail-closed
            assert is_valid is False
    
    def test_lease_consumption_marks_consumed(self):
        """Test that consume_lease marks lease as consumed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            consumed_lease = lease_issuer.consume_lease(lease)
            
            assert consumed_lease.consumed is True


class TestLeaseRegistrySkeleton:
    """Tests for LeaseRegistry skeleton."""
    
    def test_registry_initialization(self):
        """Test that LeaseRegistry can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            registry = LeaseRegistry(trust_anchor)
            assert registry.count() == 0
    
    def test_registry_register(self):
        """Test that register adds lease to registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            registry.register(lease)
            
            assert registry.count() == 1
    
    def test_registry_consume(self):
        """Test that consume removes lease from registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            registry = LeaseRegistry(trust_anchor)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            registry.register(lease)
            
            consumed_lease = registry.consume(lease.invocation_id)
            assert consumed_lease is not None
            assert consumed_lease.consumed is True
            assert registry.count() == 0


class TestArchitectureContractCompliance:
    """Tests for architecture contract compliance."""
    
    def test_no_duplicate_authority(self):
        """Test that there is only one authority path."""
        # Phase 1: Verify only RuntimeIdentityAuthority exists
        from iabv_v15.services.trust import trusted_execution_identity
        
        # Check that there's only one authority class
        authority_classes = [
            name for name in dir(trusted_execution_identity)
            if 'Authority' in name and not name.startswith('_')
        ]
        assert len(authority_classes) == 1
        assert 'RuntimeIdentityAuthority' in authority_classes
    
    def test_fail_closed_verification(self):
        """Test that all verification methods fail closed in Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            identity = identity_authority.issue_identity()
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # All verification should return False in Phase 1
            assert identity_authority.verify_identity(identity) is False
            assert lease_issuer.verify_lease(lease) is False
    
    def test_single_lease_registry(self):
        """Test that there is only one lease registry."""
        from iabv_v15.services.trust import trusted_lease
        
        # Check that there's only one registry class
        registry_classes = [
            name for name in dir(trusted_lease)
            if 'Registry' in name and not name.startswith('_')
        ]
        assert len(registry_classes) == 1
        assert 'LeaseRegistry' in registry_classes
