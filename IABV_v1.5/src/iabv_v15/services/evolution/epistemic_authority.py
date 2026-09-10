"""P0.213: Epistemic Authority service for READ_ONLY verification.

DESIGN_RECONSTRUCTION: This module is a new implementation reconstructed from
experimental design evidence. It is NOT recovered historical code.

Purpose: Provide READ_ONLY verification of epistemic evidence from trusted sources.
P0.213 introduces a READ_ONLY variant that must not conflict with P0.20's write capabilities.

Contract Requirements:
- P0.213 READ_ONLY behavior without breaking P0.20 capabilities
- P0.20 behavior must remain intact
- Do NOT eliminate/change existing P0.20 methods/contracts
- Isolate P0.213 READ_ONLY authority from P0.20 canonical write capability
"""
from __future__ import annotations

from typing import Any
from iabv_v15.domain.models import (
    VerificationStatus,
    AcceptanceStatus,
    EpistemicVerificationRecord,
    EpistemicAcceptanceRecord,
)


class EpistemicAuthority:
    """P0.213: READ_ONLY verifier aggregating evidence from trusted sources.
    
    This service provides READ_ONLY access to epistemic verification and acceptance
    records. It does not allow arbitrary writing of verification/acceptance records.
    
    Contract Compliance:
    - READ_ONLY variant for P0.213
    - Does NOT break P0.20 write capabilities
    - P0.20 canonical write capability remains intact
    - Isolated from P0.20 methods
    """
    
    def __init__(self):
        """Initialize the epistemic authority service."""
        self._verification_records: dict[str, EpistemicVerificationRecord] = {}
        self._acceptance_records: dict[str, EpistemicAcceptanceRecord] = {}
    
    def get_verification_record(self, verification_id: str) -> EpistemicVerificationRecord | None:
        """Get a verification record by ID (READ_ONLY).
        
        Args:
            verification_id: The verification record ID
            
        Returns:
            The verification record, or None if not found
        """
        return self._verification_records.get(verification_id)
    
    def get_acceptance_record(self, acceptance_id: str) -> EpistemicAcceptanceRecord | None:
        """Get an acceptance record by ID (READ_ONLY).
        
        Args:
            acceptance_id: The acceptance record ID
            
        Returns:
            The acceptance record, or None if not found
        """
        return self._acceptance_records.get(acceptance_id)
    
    def get_verification_by_result_id(self, result_id: str) -> EpistemicVerificationRecord | None:
        """Get verification record by result ID (READ_ONLY).
        
        Args:
            result_id: The result ID to search for
            
        Returns:
            The verification record, or None if not found
        """
        for record in self._verification_records.values():
            if record.result_id == result_id:
                return record
        return None
    
    def get_acceptance_by_verification_id(self, verification_id: str) -> EpistemicAcceptanceRecord | None:
        """Get acceptance record by verification ID (READ_ONLY).
        
        Args:
            verification_id: The verification ID to search for
            
        Returns:
            The acceptance record, or None if not found
        """
        for record in self._acceptance_records.values():
            if record.verification_id == verification_id:
                return record
        return None
    
    def list_verification_records(self) -> list[EpistemicVerificationRecord]:
        """List all verification records (READ_ONLY).
        
        Returns:
            List of all verification records
        """
        return list(self._verification_records.values())
    
    def list_acceptance_records(self) -> list[EpistemicAcceptanceRecord]:
        """List all acceptance records (READ_ONLY).
        
        Returns:
            List of all acceptance records
        """
        return list(self._acceptance_records.values())
    
    def is_result_verified(self, result_id: str) -> bool:
        """Check if a result is verified (READ_ONLY).
        
        Args:
            result_id: The result ID to check
            
        Returns:
            True if verified, False otherwise
        """
        record = self.get_verification_by_result_id(result_id)
        if record is None:
            return False
        return record.verification_status == VerificationStatus.VERIFIED
    
    def is_result_accepted(self, result_id: str) -> bool:
        """Check if a result is accepted (READ_ONLY).
        
        Args:
            result_id: The result ID to check
            
        Returns:
            True if accepted, False otherwise
        """
        verification = self.get_verification_by_result_id(result_id)
        if verification is None:
            return False
        
        acceptance = self.get_acceptance_by_verification_id(verification.verification_id)
        if acceptance is None:
            return False
        
        return acceptance.acceptance_status == AcceptanceStatus.ACCEPTED
    
    # NOTE: These methods are for internal use by P0.213 canonical processes
    # They are NOT part of the public READ_ONLY API for external callers
    
    def _register_verification_record(self, record: EpistemicVerificationRecord) -> None:
        """Register a verification record (internal use only).
        
        This method is for internal use by P0.213 canonical processes.
        It is NOT part of the public READ_ONLY API.
        
        Args:
            record: The verification record to register
        """
        self._verification_records[record.verification_id] = record
    
    def _register_acceptance_record(self, record: EpistemicAcceptanceRecord) -> None:
        """Register an acceptance record (internal use only).
        
        This method is for internal use by P0.213 canonical processes.
        It is NOT part of the public READ_ONLY API.
        
        Args:
            record: The acceptance record to register
        """
        self._acceptance_records[record.acceptance_id] = record
