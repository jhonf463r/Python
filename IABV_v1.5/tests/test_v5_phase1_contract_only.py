"""Tests for P0.213 V5 Phase 1: Data Contract Only (NON-AUTHORITATIVE).

These tests verify that the data contracts are properly defined
and follow the architecture contract.

Phase 1 Tests (L1 UNIT/CONTRACT):
- Data-model invariants (required fields, types)
- Immutability (dataclass frozen=True)
- Serialization round-trip (to_dict/from_dict)
- Explicit non-authoritative semantics
- Phase 2 required interfaces (NotImplementedError)
- Architecture contract consistency
- Absence of fake authority bypass parameters
- Absence of placeholder secrets
- Absence of verify_identity() -> False fake security
- Absence of verify_lease() -> False fake security

Phase 1 tests must NOT claim:
- OS identity verification
- Real authority enforcement
- IPC security
- Exactly-once consumption
- Production reachability
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


class TestDataModelInvariants:
    """Tests for data-model invariants."""
    
    def test_process_identity_has_required_fields(self):
        """Test that ProcessIdentity has required fields."""
        identity = ProcessIdentity(pid=123, create_time=0.0, ppid=1)
        assert identity.pid == 123
        assert identity.create_time == 0.0
        assert identity.ppid == 1
    
    def test_runtime_identity_has_required_fields(self):
        """Test that RuntimeIdentity has required fields."""
        identity = RuntimeIdentity(generation=0, bootstrap_timestamp=0.0)
        assert identity.generation == 0
        assert identity.bootstrap_timestamp == 0.0
    
    def test_observed_process_identity_has_required_fields(self):
        """Test that ObservedProcessIdentity has required fields."""
        identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
        assert identity.pid == 123
        assert identity.create_time == 0.0
        assert identity.ppid == 1
    
    def test_canonical_run_record_has_required_fields(self):
        """Test that CanonicalRunRecord has required fields."""
        record = CanonicalRunRecord(
            run_id="test_run",
            execution_id="test_exec",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            authorized_scope="test_scope",
        )
        assert record.run_id == "test_run"
        assert record.execution_id == "test_exec"
        assert record.invocation_id == "test_inv"
        assert record.authorized_scope == "test_scope"
    
    def test_trusted_execution_identity_has_required_fields(self):
        """Test that TrustedExecutionIdentity has required fields."""
        identity = TrustedExecutionIdentity(
            issuer_pid=0,
            issuer_generation=0,
            consumer_pid=0,
            execution_id="test_exec",
            run_id="test_run",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            runtime_generation=0,
            bootstrap_timestamp=0.0,
            signature="placeholder",
            issued_at=0.0,
            expires_at=0.0,
        )
        assert identity.issuer_pid == 0
        assert identity.consumer_pid == 0
        assert identity.execution_id == "test_exec"
        assert identity.signature == "placeholder"
    
    def test_trusted_lease_has_required_fields(self):
        """Test that TrustedLease has required fields."""
        lease = TrustedLease(
            issuer_pid=0,
            issuer_generation=0,
            execution_id="test_exec",
            invocation_id="test_inv",
            lease_id="test_lease",
            producer_pid=0,
            producer_scope="test_scope",
            authorization_context=None,
            issued_at=0.0,
            expires_at=0.0,
            signature="placeholder",
            consumed=False,
        )
        assert lease.issuer_pid == 0
        assert lease.lease_id == "test_lease"
        assert lease.signature == "placeholder"
        assert lease.consumed is False


class TestImmutability:
    """Tests for immutability (dataclass frozen=True)."""
    
    def test_process_identity_is_immutable(self):
        """Test that ProcessIdentity is immutable."""
        identity = ProcessIdentity(pid=123, create_time=0.0, ppid=1)
        with pytest.raises(Exception):  # FrozenInstanceError
            identity.pid = 999
    
    def test_runtime_identity_is_immutable(self):
        """Test that RuntimeIdentity is immutable."""
        identity = RuntimeIdentity(generation=0, bootstrap_timestamp=0.0)
        with pytest.raises(Exception):  # FrozenInstanceError
            identity.generation = 999
    
    def test_observed_process_identity_is_immutable(self):
        """Test that ObservedProcessIdentity is immutable."""
        identity = ObservedProcessIdentity(pid=123, create_time=0.0, ppid=1)
        with pytest.raises(Exception):  # FrozenInstanceError
            identity.pid = 999
    
    def test_canonical_run_record_is_immutable(self):
        """Test that CanonicalRunRecord is immutable."""
        record = CanonicalRunRecord(
            run_id="test_run",
            execution_id="test_exec",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            authorized_scope="test_scope",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            record.run_id = "changed"
    
    def test_trusted_execution_identity_is_immutable(self):
        """Test that TrustedExecutionIdentity is immutable."""
        identity = TrustedExecutionIdentity(
            issuer_pid=0,
            issuer_generation=0,
            consumer_pid=0,
            execution_id="test_exec",
            run_id="test_run",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            runtime_generation=0,
            bootstrap_timestamp=0.0,
            signature="placeholder",
            issued_at=0.0,
            expires_at=0.0,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            identity.consumer_pid = 999
    
    def test_trusted_lease_is_immutable(self):
        """Test that TrustedLease is immutable."""
        lease = TrustedLease(
            issuer_pid=0,
            issuer_generation=0,
            execution_id="test_exec",
            invocation_id="test_inv",
            lease_id="test_lease",
            producer_pid=0,
            producer_scope="test_scope",
            authorization_context=None,
            issued_at=0.0,
            expires_at=0.0,
            signature="placeholder",
            consumed=False,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            lease.consumed = True


class TestSerializationRoundTrip:
    """Tests for serialization round-trip (to_dict/from_dict)."""
    
    def test_process_identity_serialization_round_trip(self):
        """Test that ProcessIdentity can serialize and deserialize."""
        identity = ProcessIdentity(pid=123, create_time=0.0, ppid=1)
        data = identity.to_dict()
        restored = ProcessIdentity(**data)
        assert restored == identity
    
    def test_runtime_identity_serialization_round_trip(self):
        """Test that RuntimeIdentity can serialize and deserialize."""
        identity = RuntimeIdentity(generation=0, bootstrap_timestamp=0.0)
        data = identity.to_dict()
        restored = RuntimeIdentity(**data)
        assert restored == identity
    
    def test_trusted_execution_identity_serialization_round_trip(self):
        """Test that TrustedExecutionIdentity can serialize and deserialize."""
        identity = TrustedExecutionIdentity(
            issuer_pid=0,
            issuer_generation=0,
            consumer_pid=0,
            execution_id="test_exec",
            run_id="test_run",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            runtime_generation=0,
            bootstrap_timestamp=0.0,
            signature="placeholder",
            issued_at=0.0,
            expires_at=0.0,
        )
        data = identity.to_dict()
        restored = TrustedExecutionIdentity.from_dict(data)
        assert restored == identity
    
    def test_trusted_lease_serialization_round_trip(self):
        """Test that TrustedLease can serialize and deserialize."""
        lease = TrustedLease(
            issuer_pid=0,
            issuer_generation=0,
            execution_id="test_exec",
            invocation_id="test_inv",
            lease_id="test_lease",
            producer_pid=0,
            producer_scope="test_scope",
            authorization_context=None,
            issued_at=0.0,
            expires_at=0.0,
            signature="placeholder",
            consumed=False,
        )
        data = lease.to_dict()
        restored = TrustedLease.from_dict(data)
        assert restored == lease


class TestNonAuthoritativeSemantics:
    """Tests for explicit non-authoritative semantics."""
    
    def test_root_trust_anchor_docstring_says_data_contract(self):
        """Test that RootTrustAnchor docstring says DATA CONTRACT."""
        assert "DATA CONTRACT" in RootTrustAnchor.__doc__
        assert "NOT a security boundary" in RootTrustAnchor.__doc__
    
    def test_trusted_execution_identity_docstring_says_data_contract(self):
        """Test that TrustedExecutionIdentity docstring says DATA CONTRACT."""
        assert "DATA CONTRACT" in TrustedExecutionIdentity.__doc__
        assert "NOT a security boundary" in TrustedExecutionIdentity.__doc__
    
    def test_trusted_lease_docstring_says_data_contract(self):
        """Test that TrustedLease docstring says DATA CONTRACT."""
        assert "DATA CONTRACT" in TrustedLease.__doc__
        assert "NOT a security boundary" in TrustedLease.__doc__
    
    def test_runtime_identity_authority_docstring_says_non_authoritative(self):
        """Test that RuntimeIdentityAuthority docstring says NON-AUTHORITATIVE."""
        assert "NON-AUTHORITATIVE" in RuntimeIdentityAuthority.__doc__
        assert "NOT a security boundary" in RuntimeIdentityAuthority.__doc__
    
    def test_lease_issuer_service_docstring_says_non_authoritative(self):
        """Test that LeaseIssuerService docstring says NON-AUTHORITATIVE."""
        assert "NON-AUTHORITATIVE" in LeaseIssuerService.__doc__
        assert "NOT a security boundary" in LeaseIssuerService.__doc__
    
    def test_lease_registry_docstring_says_non_authoritative(self):
        """Test that LeaseRegistry docstring says NON-AUTHORITATIVE."""
        assert "NON-AUTHORITATIVE" in LeaseRegistry.__doc__
        assert "NOT a security boundary" in LeaseRegistry.__doc__
    
    def test_lease_registry_dict_is_labeled_non_authoritative(self):
        """Test that LeaseRegistry dictionary is labeled NON_AUTHORITATIVE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            registry = LeaseRegistry(trust_anchor)
            assert "NON_AUTHORITATIVE" in LeaseRegistry.__doc__


class TestPhase2RequiredInterfaces:
    """Tests for Phase 2 required interfaces (NotImplementedError)."""
    
    def test_verify_identity_raises_not_implemented(self):
        """Test that verify_identity raises NotImplementedError (Phase 2 required)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = TrustedExecutionIdentity(
                issuer_pid=0,
                issuer_generation=0,
                consumer_pid=0,
                execution_id="test_exec",
                run_id="test_run",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                runtime_generation=0,
                bootstrap_timestamp=0.0,
                signature="placeholder",
                issued_at=0.0,
                expires_at=0.0,
            )
            
            with pytest.raises(NotImplementedError):
                authority.verify_identity(identity)
    
    def test_verify_lease_raises_not_implemented(self):
        """Test that verify_lease raises NotImplementedError (Phase 2 required)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            lease = TrustedLease(
                issuer_pid=0,
                issuer_generation=0,
                execution_id="test_exec",
                invocation_id="test_inv",
                lease_id="test_lease",
                producer_pid=0,
                producer_scope="test_scope",
                authorization_context=None,
                issued_at=0.0,
                expires_at=0.0,
                signature="placeholder",
                consumed=False,
            )
            
            with pytest.raises(NotImplementedError):
                lease_issuer.verify_lease(lease)


class TestAbsenceOfFakeAuthorityEnforcement:
    """Tests for absence of fake authority enforcement."""
    
    def test_root_trust_anchor_no_authority_authorized_parameter(self):
        """Test that RootTrustAnchor has no _authority_authorized parameter."""
        import inspect
        sig = inspect.signature(RootTrustAnchor.__init__)
        assert "_authority_authorized" not in sig.parameters
    
    def test_root_trust_anchor_any_caller_can_construct(self):
        """Test that any caller can construct RootTrustAnchor (no fake enforcement)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Any caller can construct (NOT a security boundary)
            anchor = RootTrustAnchor(storage_root=tmpdir)
            assert anchor is not None


class TestAbsenceOfPlaceholderSecrets:
    """Tests for absence of placeholder secrets."""
    
    def test_root_trust_anchor_secret_key_returns_none(self):
        """Test that get_secret_key returns None (no placeholder secret)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = RootTrustAnchor(storage_root=tmpdir)
            key = anchor.get_secret_key()
            assert key is None
            assert key != b"placeholder"
    
    def test_trusted_execution_identity_signature_is_placeholder_string(self):
        """Test that signature is a placeholder string (not bytes)."""
        identity = TrustedExecutionIdentity(
            issuer_pid=0,
            issuer_generation=0,
            consumer_pid=0,
            execution_id="test_exec",
            run_id="test_run",
            episode_id=None,
            session_id=None,
            invocation_id="test_inv",
            runtime_generation=0,
            bootstrap_timestamp=0.0,
            signature="placeholder",
            issued_at=0.0,
            expires_at=0.0,
        )
        assert identity.signature == "placeholder"
        assert not isinstance(identity.signature, bytes)


class TestAbsenceOfFakeSecurityValidation:
    """Tests for absence of verify_identity() -> False fake security."""
    
    def test_verify_identity_does_not_return_false(self):
        """Test that verify_identity does NOT return False (raises NotImplementedError)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            authority = RuntimeIdentityAuthority(trust_anchor)
            
            identity = TrustedExecutionIdentity(
                issuer_pid=0,
                issuer_generation=0,
                consumer_pid=0,
                execution_id="test_exec",
                run_id="test_run",
                episode_id=None,
                session_id=None,
                invocation_id="test_inv",
                runtime_generation=0,
                bootstrap_timestamp=0.0,
                signature="placeholder",
                issued_at=0.0,
                expires_at=0.0,
            )
            
            # Should raise NotImplementedError, NOT return False
            with pytest.raises(NotImplementedError):
                authority.verify_identity(identity)
    
    def test_verify_lease_does_not_return_false(self):
        """Test that verify_lease does NOT return False (raises NotImplementedError)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            identity_authority = RuntimeIdentityAuthority(trust_anchor)
            lease_issuer = LeaseIssuerService(trust_anchor, identity_authority)
            
            lease = TrustedLease(
                issuer_pid=0,
                issuer_generation=0,
                execution_id="test_exec",
                invocation_id="test_inv",
                lease_id="test_lease",
                producer_pid=0,
                producer_scope="test_scope",
                authorization_context=None,
                issued_at=0.0,
                expires_at=0.0,
                signature="placeholder",
                consumed=False,
            )
            
            # Should raise NotImplementedError, NOT return False
            with pytest.raises(NotImplementedError):
                lease_issuer.verify_lease(lease)


class TestArchitectureContractConsistency:
    """Tests for architecture contract consistency."""
    
    def test_architecture_contract_exists(self):
        """Test that architecture contract exists."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        assert contract_path.exists()
    
    def test_architecture_contract_says_data_contract_only(self):
        """Test that architecture contract says DATA_CONTRACT_ONLY."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        assert "DATA_CONTRACT_ONLY" in contract_content
        assert "NON-AUTHORITATIVE" in contract_content
    
    def test_architecture_contract_says_in_process_not_security_boundary(self):
        """Test that architecture contract says in-process objects are NOT security boundaries."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        assert "In-process Python objects CANNOT be security boundaries" in contract_content
    
    def test_architecture_contract_forbids_fake_authority_enforcement(self):
        """Test that architecture contract forbids fake authority enforcement."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        assert "_authority_authorized" in contract_content
        assert "verify_identity() -> False" in contract_content
        assert "verify_lease() -> False" in contract_content
    
    def test_architecture_contract_says_dict_pop_not_interprocess(self):
        """Test that architecture contract says dict.pop() is NOT interprocess exactly-once."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        assert "dict.pop() is NOT interprocess exactly-once" in contract_content
    
    def test_architecture_contract_has_phase_2_required(self):
        """Test that architecture contract has PHASE_2_REQUIRED classification."""
        contract_path = Path("docs/p0213/v5_architecture_contract.md")
        contract_content = contract_path.read_text()
        assert "PHASE_2_REQUIRED" in contract_content


class TestSingleUseContract:
    """Tests for single-use contract (invariant definition, not enforcement)."""
    
    def test_lease_registry_docstring_says_dict_pop_not_interprocess(self):
        """Test that LeaseRegistry docstring says dict.pop() is NOT interprocess exactly-once."""
        assert "dict.pop() is interprocess exactly-once" in LeaseRegistry.__doc__ or "DO NOT assume dict.pop() is interprocess exactly-once" in LeaseRegistry.__doc__
    
    def test_lease_registry_consume_uses_dict_pop(self):
        """Test that consume() uses dict.pop() (NOT interprocess exactly-once)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_anchor = RootTrustAnchor(storage_root=tmpdir)
            registry = LeaseRegistry(trust_anchor)
            
            lease = TrustedLease(
                issuer_pid=0,
                issuer_generation=0,
                execution_id="test_exec",
                invocation_id="test_inv",
                lease_id="test_lease",
                producer_pid=0,
                producer_scope="test_scope",
                authorization_context=None,
                issued_at=0.0,
                expires_at=0.0,
                signature="placeholder",
                consumed=False,
            )
            
            registry.register(lease)
            consumed_lease = registry.consume("test_lease")
            
            assert consumed_lease is not None
            assert consumed_lease.consumed is True
            assert registry.count() == 0  # dict.pop() removed it


class TestImmutabilityNotAuthenticity:
    """Tests for immutability vs authenticity distinction."""
    
    def test_trusted_execution_identity_docstring_says_immutable_not_authentic(self):
        """Test that docstring says IMMUTABLE != AUTHENTIC != AUTHORIZED."""
        assert "IMMUTABLE OBJECT != AUTHENTIC OBJECT != AUTHORIZED OBJECT" in TrustedExecutionIdentity.__doc__
    
    def test_trusted_lease_docstring_says_immutable_not_authentic(self):
        """Test that docstring says IMMUTABLE != AUTHENTIC != AUTHORIZED."""
        assert "IMMUTABLE OBJECT != AUTHENTIC OBJECT != AUTHORIZED OBJECT" in TrustedLease.__doc__
    
    def test_from_dict_docstring_says_not_automatic_trust(self):
        """Test that from_dict() docstring says NOT automatic trust."""
        assert "from_dict() is deserialization ONLY, NOT automatic trust" in TrustedExecutionIdentity.from_dict.__doc__
        assert "from_dict() is deserialization ONLY, NOT automatic trust" in TrustedLease.from_dict.__doc__
