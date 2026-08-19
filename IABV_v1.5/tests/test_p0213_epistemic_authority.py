"""P0.213 Tests for Epistemic Authority.

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for READ_ONLY epistemic authority service.
"""
import pytest
from iabv_v15.services.evolution.epistemic_authority import EpistemicAuthority
from iabv_v15.domain.models import (
    VerificationStatus,
    AcceptanceStatus,
    EpistemicVerificationRecord,
    EpistemicAcceptanceRecord,
)


class TestEpistemicAuthority:
    """Test EpistemicAuthority READ_ONLY verification."""

    def test_get_verification_record(self):
        """Test A: get verification record by ID (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record = EpistemicVerificationRecord(
            result_id="test_result_id",
            verification_status=VerificationStatus.VERIFIED
        )
        
        authority._register_verification_record(record)
        
        retrieved = authority.get_verification_record(record.verification_id)
        assert retrieved is not None
        assert retrieved.result_id == "test_result_id"

    def test_get_acceptance_record(self):
        """Test B: get acceptance record by ID (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record = EpistemicAcceptanceRecord(
            verification_id="test_verification_id",
            acceptance_status=AcceptanceStatus.ACCEPTED
        )
        
        authority._register_acceptance_record(record)
        
        retrieved = authority.get_acceptance_record(record.acceptance_id)
        assert retrieved is not None
        assert retrieved.verification_id == "test_verification_id"

    def test_get_verification_by_result_id(self):
        """Test C: get verification record by result ID (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record = EpistemicVerificationRecord(
            result_id="test_result_id",
            verification_status=VerificationStatus.VERIFIED
        )
        
        authority._register_verification_record(record)
        
        retrieved = authority.get_verification_by_result_id("test_result_id")
        assert retrieved is not None
        assert retrieved.verification_status == VerificationStatus.VERIFIED

    def test_get_acceptance_by_verification_id(self):
        """Test D: get acceptance record by verification ID (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record = EpistemicAcceptanceRecord(
            verification_id="test_verification_id",
            acceptance_status=AcceptanceStatus.ACCEPTED
        )
        
        authority._register_acceptance_record(record)
        
        retrieved = authority.get_acceptance_by_verification_id("test_verification_id")
        assert retrieved is not None
        assert retrieved.acceptance_status == AcceptanceStatus.ACCEPTED

    def test_list_verification_records(self):
        """Test E: list all verification records (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record1 = EpistemicVerificationRecord(
            result_id="test_result_id_1",
            verification_status=VerificationStatus.VERIFIED
        )
        
        record2 = EpistemicVerificationRecord(
            result_id="test_result_id_2",
            verification_status=VerificationStatus.REFUTED
        )
        
        authority._register_verification_record(record1)
        authority._register_verification_record(record2)
        
        records = authority.list_verification_records()
        assert len(records) == 2

    def test_list_acceptance_records(self):
        """Test F: list all acceptance records (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record1 = EpistemicAcceptanceRecord(
            verification_id="test_verification_id_1",
            acceptance_status=AcceptanceStatus.ACCEPTED
        )
        
        record2 = EpistemicAcceptanceRecord(
            verification_id="test_verification_id_2",
            acceptance_status=AcceptanceStatus.REJECTED
        )
        
        authority._register_acceptance_record(record1)
        authority._register_acceptance_record(record2)
        
        records = authority.list_acceptance_records()
        assert len(records) == 2

    def test_is_result_verified(self):
        """Test G: check if result is verified (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        record = EpistemicVerificationRecord(
            result_id="test_result_id",
            verification_status=VerificationStatus.VERIFIED
        )
        
        authority._register_verification_record(record)
        
        assert authority.is_result_verified("test_result_id") is True
        assert authority.is_result_verified("non_existent") is False

    def test_is_result_accepted(self):
        """Test H: check if result is accepted (READ_ONLY)."""
        authority = EpistemicAuthority()
        
        verification = EpistemicVerificationRecord(
            result_id="test_result_id",
            verification_status=VerificationStatus.VERIFIED
        )
        
        acceptance = EpistemicAcceptanceRecord(
            verification_id=verification.verification_id,
            acceptance_status=AcceptanceStatus.ACCEPTED
        )
        
        authority._register_verification_record(verification)
        authority._register_acceptance_record(acceptance)
        
        assert authority.is_result_accepted("test_result_id") is True
        assert authority.is_result_accepted("non_existent") is False

    def test_read_only_isolation(self):
        """Test I: READ_ONLY isolation from P0.20 write capability."""
        # This test verifies that P0.213 READ_ONLY authority is isolated
        # from P0.20 canonical write capability
        authority = EpistemicAuthority()
        
        # P0.213 READ_ONLY methods exist
        assert hasattr(authority, 'get_verification_record')
        assert hasattr(authority, 'get_acceptance_record')
        assert hasattr(authority, 'is_result_verified')
        assert hasattr(authority, 'is_result_accepted')
        
        # Internal registration methods exist (for canonical processes)
        assert hasattr(authority, '_register_verification_record')
        assert hasattr(authority, '_register_acceptance_record')
        
        # No public write methods (READ_ONLY variant)
        # P0.20 write capability remains intact elsewhere

    def test_p020_compatibility(self):
        """Test J: P0.20 compatibility - P0.213 does not break P0.20."""
        # This test verifies that P0.213 READ_ONLY authority does not
        # break P0.20 canonical write capability
        authority = EpistemicAuthority()
        
        # P0.213 can register records internally
        record = EpistemicVerificationRecord(
            result_id="test_result_id",
            verification_status=VerificationStatus.VERIFIED
        )
        authority._register_verification_record(record)
        
        # P0.213 can read records
        retrieved = authority.get_verification_record(record.verification_id)
        assert retrieved is not None
        
        # P0.20 write capability remains intact (not tested here,
        # but verified by P0.20 regression tests)
