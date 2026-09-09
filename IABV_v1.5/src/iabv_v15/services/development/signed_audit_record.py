"""P0-B V4 Signed Audit Record for Process-Separated Authority.

This module defines the canonical signed audit record schema and cryptographic
verification for the separate audit authority process.

P0-B V4 Authority Model:
- Authority process: separate process with Ed25519 keypair
- Caller process: cannot access private key
- Signed record: binds Git evidence, audit semantics, and producer authenticity
- Trust anchor: trusted public key (not from record itself)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption,
)


@dataclass
class SignedAuditRecord:
    """Canonical signed audit record from authority process.
    
    This record contains:
    - Git evidence (verified by authority)
    - Audit semantics (derived by authority)
    - Producer authenticity (Ed25519 signature)
    - Evidence fingerprint (SHA-256 for replay prevention)
    
    P0-B V4: Authority process signs this with private key.
    Caller process verifies with trusted public key.
    """
    
    # Required fields (no defaults)
    audit_id: str
    evidence_id: str
    repository_identity: str
    repository: str
    base_commit: str
    result_commit: str
    actual_changed_files: list[str]
    execution_status: str
    criteria: list[dict[str, Any]]
    verdict: str
    audited_at_utc: str
    producer_public_key_id: str
    evidence_fingerprint: str
    signature: bytes
    
    # Optional field with default (after required fields)
    schema_version: str = "1.0"
    
    def to_canonical_bytes(self) -> bytes:
        """Serialize record to canonical bytes for signing.
        
        Canonicalization ensures:
        - Same logical record → same bytes
        - Deterministic field ordering
        - Consistent encoding
        """
        # Create canonical representation (without signature)
        canonical_dict = {
            "schema_version": self.schema_version,
            "audit_id": self.audit_id,
            "evidence_id": self.evidence_id,
            "repository_identity": self.repository_identity,
            "repository": self.repository,
            "base_commit": self.base_commit,
            "result_commit": self.result_commit,
            "actual_changed_files": sorted(self.actual_changed_files),  # Sorted for determinism
            "execution_status": self.execution_status,
            "criteria": self._canonicalize_criteria(self.criteria),
            "verdict": self.verdict,
            "audited_at_utc": self.audited_at_utc,
            "producer_public_key_id": self.producer_public_key_id,
            "evidence_fingerprint": self.evidence_fingerprint,
        }
        
        # Use JSON with sorted keys and no whitespace for determinism
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))
        return canonical_json.encode('utf-8')
    
    def _canonicalize_criteria(self, criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Canonicalize criteria list for deterministic serialization."""
        canonical = []
        for criterion in criteria:
            # Sort dict keys and ensure consistent structure
            canonical_criterion = {k: criterion[k] for k in sorted(criterion.keys())}
            canonical.append(canonical_criterion)
        # Sort criteria by criterion_id for determinism
        canonical.sort(key=lambda x: x.get('criterion_id', ''))
        return canonical
    
    @classmethod
    def calculate_evidence_fingerprint(
        cls,
        repository_identity: str,
        evidence_id: str,
        base_commit: str,
        result_commit: str,
        actual_changed_files: list[str],
        execution_status: str,
    ) -> str:
        """Calculate SHA-256 fingerprint of evidence for replay prevention.
        
        P0-B V4: This fingerprint must be unique per distinct evidence.
        Same evidence → same fingerprint.
        Different evidence → different fingerprint.
        """
        fingerprint_data = {
            "repository_identity": repository_identity,
            "evidence_id": evidence_id,
            "base_commit": base_commit,
            "result_commit": result_commit,
            "actual_changed_files": sorted(actual_changed_files),
            "execution_status": execution_status,
        }
        
        # Canonical JSON for determinism
        canonical_json = json.dumps(fingerprint_data, sort_keys=True, separators=(',', ':'))
        fingerprint_bytes = canonical_json.encode('utf-8')
        
        # SHA-256 hash
        sha256_hash = hashlib.sha256(fingerprint_bytes).hexdigest()
        return sha256_hash
    
    def verify_signature(self, trusted_public_key: ed25519.Ed25519PublicKey) -> bool:
        """Verify that the record was signed by the trusted authority.
        
        Args:
            trusted_public_key: The trusted authority's public key (not from record)
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get canonical bytes (without signature)
            canonical_bytes = self.to_canonical_bytes()
            
            # Verify signature
            trusted_public_key.verify(self.signature, canonical_bytes)
            return True
        except Exception:
            return False


class AuthorityKeyPair:
    """Ed25519 keypair for audit authority process.
    
    P0-B V4 Security Requirements:
    - Private key MUST NEVER leave authority process
    - Private key MUST NOT be logged or serialized
    - Public key can be distributed to callers
    - Keys are ephemeral per authority lifecycle (V4)
    """
    
    def __init__(self):
        """Generate new Ed25519 keypair."""
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self._public_key_id = self._public_key.public_bytes(
            Encoding.Raw,
            PublicFormat.Raw
        ).hex()[:16]  # Short ID for identification
    
    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Get public key (safe to share)."""
        return self._public_key
    
    @property
    def public_key_id(self) -> str:
        """Get public key identifier."""
        return self._public_key_id
    
    def sign(self, data: bytes) -> bytes:
        """Sign data with private key (authority-only operation).
        
        Args:
            data: Bytes to sign (typically canonical record bytes)
        
        Returns:
            Ed25519 signature bytes
        """
        return self._private_key.sign(data)
    
    def get_public_key_bytes(self) -> bytes:
        """Get public key in raw format for distribution."""
        return self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    
    @classmethod
    def public_key_from_bytes(cls, key_bytes: bytes) -> ed25519.Ed25519PublicKey:
        """Reconstruct public key from bytes (caller-side operation)."""
        return ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)