"""P0-B V4-r1 Audit Record Verifier.

This module implements the caller-side verification boundary for signed audit records.

F6 FIX: Real verify_signed_record capability with explicit trust anchor.

The verifier validates:
- signature against trusted authority key
- canonical representation
- producer key identifier consistency
- evidence fingerprint consistency
- record schema/version
- required fields
- criteria coherence
- verdict coherence

The verifier does NOT discover trust from the record itself.
It requires an independently trusted authority public key.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from iabv_v15.services.development.signed_audit_record import SignedAuditRecord

logger = logging.getLogger(__name__)


class AuditRecordVerificationError(Exception):
    """Raised when audit record verification fails."""
    pass


class AuditRecordVerifier:
    """Caller-side verifier for signed audit records.
    
    F6 FIX: Explicit verification boundary with independent trust anchor.
    
    The verification process:
    1. Validate record schema and required fields
    2. Reconstruct canonical bytes
    3. Verify signature against trusted authority key
    4. Validate producer_public_key_id matches trusted key
    5. Validate evidence fingerprint consistency
    6. Validate criteria/verdict coherence
    """
    
    def __init__(self, trusted_authority_key: ed25519.Ed25519PublicKey):
        """Initialize verifier with trusted authority public key.
        
        Args:
            trusted_authority_key: The trusted authority's public key (from independent trust anchor)
        """
        self._trusted_key = trusted_authority_key
        self._trusted_key_id = trusted_authority_key.public_bytes(
            Encoding.Raw,
            PublicFormat.Raw
        ).hex()[:16]
        
        logger.info("AuditRecordVerifier initialized with trusted key ID: %s", self._trusted_key_id)
    
    def verify(self, record: SignedAuditRecord) -> bool:
        """Verify a signed audit record.
        
        Args:
            record: SignedAuditRecord to verify
        
        Returns:
            True if record is valid and trusted, False otherwise
        """
        try:
            # Step 1: Validate schema version
            if record.schema_version != "1.0":
                logger.warning("Unknown schema version: %s", record.schema_version)
                return False
            
            # Step 2: Validate required fields
            self._validate_required_fields(record)
            
            # Step 3: Validate producer key matches trusted key
            if record.producer_public_key_id != self._trusted_key_id:
                logger.warning(
                    "Producer key ID mismatch: record=%s, trusted=%s",
                    record.producer_public_key_id,
                    self._trusted_key_id
                )
                return False
            
            # Step 4: Validate evidence fingerprint consistency
            calculated_fingerprint = SignedAuditRecord.calculate_evidence_fingerprint(
                repository_identity=record.repository_identity,
                evidence_id=record.evidence_id,
                base_commit=record.base_commit,
                result_commit=record.result_commit,
                actual_changed_files=record.actual_changed_files,
                execution_status=record.execution_status,
            )
            
            if calculated_fingerprint != record.evidence_fingerprint:
                logger.warning(
                    "Evidence fingerprint mismatch: calculated=%s, record=%s",
                    calculated_fingerprint,
                    record.evidence_fingerprint
                )
                return False
            
            # Step 5: Validate criteria/verdict coherence
            if not self._validate_criteria_verdict_coherence(record):
                logger.warning("Criteria/verdict coherence check failed")
                return False
            
            # Step 6: Verify signature
            if not record.verify_signature(self._trusted_key):
                logger.warning("Signature verification failed")
                return False
            
            logger.info("Audit record verified successfully: %s", record.audit_id)
            return True
            
        except Exception as exc:
            logger.error("Verification error: %s", exc)
            return False
    
    def _validate_required_fields(self, record: SignedAuditRecord) -> None:
        """Validate that all required fields are present and non-empty."""
        required_fields = [
            "audit_id",
            "evidence_id",
            "repository_identity",
            "repository",
            "base_commit",
            "result_commit",
            "actual_changed_files",
            "execution_status",
            "criteria",
            "verdict",
            "audited_at_utc",
            "producer_public_key_id",
            "evidence_fingerprint",
            "signature",
        ]
        
        for field in required_fields:
            value = getattr(record, field, None)
            if value is None:
                raise AuditRecordVerificationError(f"Missing required field: {field}")
            
            # Check non-empty for string fields
            if isinstance(value, str) and not value:
                raise AuditRecordVerificationError(f"Empty required field: {field}")
            
            # Check non-empty for list fields
            if isinstance(value, list) and not value and field in ["actual_changed_files", "criteria"]:
                raise AuditRecordVerificationError(f"Empty required field: {field}")
    
    def _validate_criteria_verdict_coherence(self, record: SignedAuditRecord) -> bool:
        """Validate that verdict is coherent with criteria.
        
        Rules:
        - PASS verdict requires all required criteria to be satisfied
        - FAIL verdict is valid for any criteria state
        """
        required_criteria = [c for c in record.criteria if c.get("required", False)]
        
        if record.verdict == "PASS":
            # All required criteria must be satisfied
            for criterion in required_criteria:
                if criterion.get("status") != "satisfied":
                    logger.warning(
                        "PASS verdict with unsatisfied required criterion: %s",
                        criterion.get("criterion_id")
                    )
                    return False
        
        # FAIL verdict is always valid
        return True