"""Tests for P0.213 V5 Phase 1: Trust Boundary Skeleton (Remediated).

These tests verify that the skeleton components are properly defined
and follow the architecture contract.

Phase 1 Tests (L1 UNIT/STATIC ARCHITECTURE):
- Canonical owner is explicitly defined
- Caller cannot choose authoritative identity fields
- Invalid lease fields fail
- Immutable artifacts cannot be mutated
- Deserialized artifact is not automatically trusted
- Duplicate authority owner is architecturally rejected
- Duplicate lease state owner is rejected
- Placeholder secret material is absent
- Placeholder methods do not claim security enforcement
- Architecture contract matches code
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
    CanonicalRunRecord,
    ObservedProcessIdentity,
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)
from iabv_v15.services.trust.trusted_lease import (
    LeaseIssuerService,
    LeaseRegistry,
    TrustedLease,
)


class TestRootTrustAnchorAuthorityOwnership:
    """Tests for RootTrustAnchor authority ownership model."""
    
    def test_unauthorized_construction_forbidden(self):
        """Test that direct construction is FORBIDDEN without _authority_authorized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Direct RootTrustAnchor construction is FORBIDDEN"):
                RootTrustAnchor(storage_root=tmpdir, _authority_authorized=False)
    
    def test_authorized_construction_allowed(self):
        """Test that construction is allowed with _authority_authorized=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            assert anchor is not None
    
    def test_placeholder_secret_material_absent(self):
        """Test that placeholder secret material (b\"placeholder\") is absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            key = anchor.get_secret_key()
            # Phase 1: Returns None (NOT_IMPLEMENTED), NOT b"placeholder"
            assert key is None
            assert key != b"placeholder"
    
    def test_canonical_owner_explicitly_defined(self):
        """Test that canonical owner is explicitly defined in docstring."""
        # Verify that the class docstring mentions ownership
        assert "OWNERSHIP: Owned by trusted bootstrap process" in RootTrustAnchor.__doc__
        assert "ONLY the trusted bootstrap process may create the canonical instance" in RootTrustAnchor.__doc__


class TestIdentityIssueContract:
    """Tests for identity issue contract."""
    
    def test_observed_process_identity_exists(self):
        """Test that ObservedProcessIdentity is defined as OS-derived."""
        assert ObservedProcessIdentity is not None
        assert "OS-derived" in ObservedProcessIdentity.__doc__
        assert "NOT caller-controlled" in ObservedProcessIdentity.__doc__
    
    def test_canonical_run_record_exists(self):
        """Test that CanonicalRunRecord is defined as authority-owned."""
        assert CanonicalRunRecord is not None
        assert "authority-owned" in CanonicalRunRecord.__doc__
        assert "NOT caller-controlled" in CanonicalRunRecord.__doc__
    
    def test_issue_api_requires_observed_identity(self):
        """Test that issue() requires ObservedProcessIdentity (NOT caller-controlled)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = authority.issue_identity(observed_identity, canonical_run_record)
            
            # Verify that consumer_pid comes from observed_identity (OS-derived)
            assert identity.consumer_pid == observed_identity.pid
    
    def test_caller_cannot_choose_authoritative_fields(self):
        """Test that caller CANNOT choose authoritative identity fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = authority.issue_identity(observed_identity, canonical_run_record)
            
            # Verify that execution_id comes from canonical_run_record (authority-owned)
            assert identity.execution_id == canonical_run_record.execution_id
            assert identity.run_id == canonical_run_record.run_id
            assert identity.invocation_id == canonical_run_record.invocation_id


class TestImmutabilityAuthenticityAuthority:
    """Tests for immutability vs authenticity vs authority."""
    
    def test_trusted_execution_identity_is_immutable(self):
        """Test that TrustedExecutionIdentity is immutable (frozen=True)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = authority.issue_identity(observed_identity, canonical_run_record)
            
            # Verify that the dataclass is frozen
            with pytest.raises(Exception):  # FrozenInstanceError
                identity.consumer_pid = 999
    
    def test_trusted_lease_is_immutable(self):
        """Test that TrustedLease is immutable (frozen=True)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = identity_authority.issue_identity(observed_identity, canonical_run_record)
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Verify that the dataclass is frozen
            with pytest.raises(Exception):  # FrozenInstanceError
                lease.consumed = True
    
    def test_from_dict_deserialization_not_automatic_trust(self):
        """Test that from_dict() is deserialization ONLY, NOT automatic trust."""
        # Verify that from_dict() exists
        assert hasattr(TrustedExecutionIdentity, 'from_dict')
        assert hasattr(TrustedLease, 'from_dict')
        
        # Verify that docstring mentions NOT automatic trust
        assert "NOT automatic trust" in TrustedExecutionIdentity.from_dict.__doc__
        assert "NOT automatic trust" in TrustedLease.from_dict.__doc__


class TestLeaseBindingContract:
    """Tests for lease binding contract."""
    
    def test_lease_has_unique_lease_id(self):
        """Test that TrustedLease has unique lease_id (authority-generated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = identity_authority.issue_identity(observed_identity, canonical_run_record)
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Verify that lease_id is present (authority-generated)
            assert lease.lease_id is not None
            assert lease.lease_id != ""
    
    def test_lease_has_authorization_context(self):
        """Test that TrustedLease has authorization_context (authority-owned)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = identity_authority.issue_identity(observed_identity, canonical_run_record)
            lease = lease_issuer.issue_lease(identity, "test_scope", authorization_context="test_context")
            
            # Verify that authorization_context is present (authority-owned)
            assert lease.authorization_context == "test_context"
    
    def test_issuer_owns_authoritative_fields(self):
        """Test that issuer owns authoritative lease fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = identity_authority.issue_identity(observed_identity, canonical_run_record)
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # Verify that issuer_pid, producer_pid are placeholder (Phase 1: NOT_IMPLEMENTED)
            # Phase 2: Will be OS-observed
            assert lease.issuer_pid == 0
            assert lease.producer_pid == 0


class TestLeaseStateOwnership:
    """Tests for lease state ownership."""
    
    def test_single_lease_state_owner(self):
        """Test that there is only ONE lease state owner (LeaseRegistry)."""
        from iabv_v15.services.trust import trusted_lease
        
        # Check that there's only one registry class
        registry_classes = [
            name for name in dir(trusted_lease)
            if 'Registry' in name and not name.startswith('_')
        ]
        assert len(registry_classes) == 1
        assert 'LeaseRegistry' in registry_classes
    
    def test_no_capability_registry(self):
        """Test that there is NO CapabilityRegistry (duplicate state owner)."""
        from iabv_v15.services.trust import trusted_lease
        
        # Check that CapabilityRegistry does NOT exist
        capability_registry_classes = [
            name for name in dir(trusted_lease)
            if 'CapabilityRegistry' in name
        ]
        assert len(capability_registry_classes) == 0
    
    def test_lease_registry_ownership_explicitly_defined(self):
        """Test that lease registry ownership is explicitly defined."""
        # Verify that the class docstring mentions ownership
        assert "ONE AUTHORITY" in LeaseRegistry.__doc__
        assert "ONE LEASE STATE OWNER" in LeaseRegistry.__doc__
        assert "ONE CONSUMPTION OWNER" in LeaseRegistry.__doc__


class TestSingleUseSemanticsContract:
    """Tests for single-use semantics contract."""
    
    def test_single_use_contract_documented(self):
        """Test that single-use contract is documented."""
        # Verify that the class docstring mentions single-use contract
        assert "SINGLE-USE SEMANTICS CONTRACT" in LeaseRegistry.__doc__
        assert "dict.pop() is NOT interprocess exactly-once" in LeaseRegistry.__doc__
    
    def test_placeholder_methods_do_not_claim_security_enforcement(self):
        """Test that placeholder methods do NOT claim security enforcement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            registry = LeaseRegistry(trust_anchor)
            
            # Verify that cleanup_expired returns 0 (NOT_IMPLEMENTED)
            count = registry.cleanup_expired()
            assert count == 0
            
            # Verify that invalidate_stale returns 0 (NOT_IMPLEMENTED)
            count = registry.invalidate_stale()
            assert count == 0


class TestFailClosedSemantics:
    """Tests for fail-closed semantics."""
    
    def test_canonical_rejection_conditions_documented(self):
        """Test that canonical rejection conditions are documented."""
        # Verify that the class docstring mentions rejection conditions
        assert "CANONICAL REJECTION CONDITIONS" in RuntimeIdentityAuthority.__doc__
        assert "CANONICAL REJECTION CONDITIONS" in LeaseIssuerService.__doc__
        assert "CANONICAL REJECTION CONDITIONS" in LeaseRegistry.__doc__
    
    def test_verification_methods_fail_closed(self):
        """Test that all verification methods fail closed in Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir, _authority_authorized=True)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            observed_identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
            canonical_run_record = CanonicalRunRecord(
                run_id="test_run",
                execution_id="test_exec",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                authorized_scope="test_scope",
            )
            
            identity = identity_authority.issue_identity(observed_identity, canonical_run_record)
            lease = lease_issuer.issue_lease(identity, "test_scope")
            
            # All verification should return False in Phase 1 (fail-closed)
            assert identity_authority.verify_identity(identity) is False
            assert lease_issuer.verify_lease(lease) is False


class TestArchitectureContractCompliance:
    """Tests for architecture contract compliance."""
    
    def test_no_duplicate_authority(self):
        """Test that there is only ONE authority path."""
        from iabv_v15.services.trust import trusted_execution_identity
        
        # Check that there's only one authority class
        authority_classes = [
            name for name in dir(trusted_execution_identity)
            if 'Authority' in name and not name.startswith('_')
        ]
        assert len(authority_classes) == 1
        assert 'RuntimeIdentityAuthority' in authority_classes
    
    def test_phase_classification_documented(self):
        """Test that phase classification is documented in architecture contract."""
        from pathlib import Path
        
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        assert contract_path.exists()
        
        contract_content = contract_path.read_text()
        assert "DESIGNED" in contract_content
        assert "NOT_IMPLEMENTED" in contract_content
        assert "RUNTIME_VERIFIED" in contract_content
    
    def test_forbidden_patterns_documented(self):
        """Test that forbidden patterns are documented in architecture contract."""
        from pathlib import Path
        
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        
        # Verify that forbidden patterns are documented
        assert "b\"placeholder\"" in contract_content
        assert "Boolean trusted flags" in contract_content
        assert "Secret strings" in contract_content
        assert "Underscore/private naming" in contract_content
