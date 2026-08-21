"""TrustedExecutionIdentity: Data contract for execution identity (P0.213 V5).

CRITICAL: This is a DATA CONTRACT, NOT a security boundary.

In-process Python objects cannot be security boundaries because any caller
can import and invoke public constructors, methods, and deserializers.
The real security boundary will be implemented in Phase 2 using a separate
trusted authority process and OS/IPC enforcement.

This module defines the DATA MODEL for:
- Observed process identity (OS-derived in Phase 2)
- Canonical run record (authority-owned in Phase 2)
- Execution identity (cryptographically signed in Phase 2)

DATA OBJECT != AUTHORITY:
- Immutable dataclass prevents mutation, but does NOT confer authenticity
- HMAC signature proves not tampered (Phase 2), but Phase 1 has no signature
- from_dict() is deserialization ONLY, NOT automatic trust
- Deserialized objects are NEVER automatically authoritative

Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)

SECURITY WARNING:
- DO NOT treat this Python object as a security boundary
- DO NOT rely on class name "Trusted" for security
- DO NOT assume immutability provides authenticity
- DO NOT use verify_identity() -> False as fake security
- Phase 2 will implement real authority boundary
"""

from __future__ import annotations

import dataclasses
import json
import time
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from iabv_v15.services.trust.root_trust_anchor import (
    ProcessIdentity,
    RootTrustAnchor,
    RuntimeIdentity,
)


@dataclass(frozen=True)
class ObservedProcessIdentity:
    """Data contract for OS-derived process identity.
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    Phase 2: Trusted authority process will obtain from OS via psutil/Windows API
    Phase 1: Data structure defined for contract specification
    
    SECURITY WARNING:
    - Caller-constructed instances are NOT authoritative
    - Phase 2 will enforce OS-derived values in trusted authority process
    - This is a data model, not an authority
    """
    
    pid: int
    create_time: float
    ppid: int


@dataclass(frozen=True)
class CanonicalRunRecord:
    """Data contract for authority-owned canonical run record.
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    Phase 2: Trusted authority process will create and own this state
    Phase 1: Data structure defined for contract specification
    
    SECURITY WARNING:
    - Caller-constructed instances are NOT authoritative
    - Phase 2 will enforce authority-owned values in trusted authority process
    - This is a data model, not an authority
    """
    
    run_id: str
    execution_id: str
    episode_id: Optional[str]
    session_id: Optional[str]
    invocation_id: str
    authorized_scope: str


@dataclass(frozen=True)
class TrustedExecutionIdentity:
    """Data contract for cryptographically bound execution identity.
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    
    IMMUTABLE OBJECT != AUTHENTIC OBJECT != AUTHORIZED OBJECT:
    - IMMUTABILITY: dataclass(frozen=True) prevents mutation (serialization operation)
    - AUTHENTICITY: HMAC signature proves not tampered (Phase 2 only)
    - AUTHORITY: Only trusted authority process can issue (Phase 2 only)
    
    Phase 2: Trusted authority process will issue with HMAC signature
    Phase 1: Data structure defined for contract specification
    
    SECURITY WARNING:
    - Caller-constructed instances are NOT authoritative
    - Class name "Trusted" does NOT confer security
    - Immutability does NOT provide authenticity
    - from_dict() is deserialization ONLY, NOT automatic trust
    - Deserialized objects are NEVER automatically authoritative
    - Phase 2 will implement real authority boundary
    
    Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
    Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
    """
    
    # Issuer (authority-owned, NOT caller-controlled)
    issuer_pid: int
    issuer_generation: int
    
    # Consumer (OS-derived, NOT caller-controlled)
    consumer_pid: int
    
    # Execution (authority-generated, NOT caller-controlled)
    execution_id: str
    run_id: str
    episode_id: str | None
    session_id: str | None
    invocation_id: str
    
    # Runtime binding (authority-owned, NOT caller-controlled)
    runtime_generation: int
    bootstrap_timestamp: float
    
    # Cryptographic proof (Phase 2: HMAC signature)
    signature: str
    
    # Metadata (authority-owned)
    issued_at: float
    expires_at: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        IMMUTABILITY: This is a serialization operation, NOT mutation.
        """
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TrustedExecutionIdentity':
        """Create from dictionary (deserialization).
        
        AUTHORITY: This creates an object, but does NOT make it authoritative.
        The resulting object MUST be verified against canonical authority state
        before it can be trusted.
        
        from_dict() is deserialization ONLY, NOT automatic trust.
        
        Phase 1: Deserialization only (NOT_IMPLEMENTED verification)
        Phase 2: Verification against canonical authority state
        """
        return cls(**data)
    
    def _serialize_for_signature(self) -> str:
        """Serialize identity fields for HMAC signing.
        
        Phase 2: Used for HMAC signature computation
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Returns:
            JSON string of all fields except signature
        """
        # Create dict without signature
        data = self.to_dict()
        data.pop('signature', None)
        
        # Sort keys for deterministic serialization
        return json.dumps(data, sort_keys=True)


class RuntimeIdentityAuthority:
    """Data contract for identity authority protocol (NON-AUTHORITATIVE).
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    
    This class defines the PROTOCOL INTERFACE for identity issuance,
    but does NOT implement real security enforcement in Phase 1.
    
    IDENTITY ISSUE CONTRACT (Phase 2):
    - ObservedProcessIdentity is OS-derived (NOT caller-controlled)
    - CanonicalRunRecord is authority-owned (NOT caller-controlled)
    - issue(observed_identity, canonical_run_record) is the canonical API
    - Caller CANNOT choose authoritative identity fields
    
    Phase 1: Data contract and protocol interface (non-authoritative)
    Phase 2: Trusted authority process implements real security enforcement
    
    SECURITY WARNING:
    - DO NOT use this class as a security boundary
    - DO NOT rely on issue() for real authority in Phase 1
    - DO NOT use verify_identity() -> False as fake security
    - Phase 2 will implement real authority boundary
    
    Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative protocol)
    Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
    """
    
    def __init__(self, trust_anchor: RootTrustAnchor):
        """Initialize identity authority.
        
        Args:
            trust_anchor: Root trust anchor for OS-controlled state
        """
        self._trust_anchor = trust_anchor
    
    def issue_identity(
        self,
        observed_identity: ObservedProcessIdentity,
        canonical_run_record: CanonicalRunRecord,
        ttl_seconds: int = 3600,
    ) -> TrustedExecutionIdentity:
        """Issue a trusted execution identity.
        
        IDENTITY ISSUE CONTRACT:
        - observed_identity: OS-derived (NOT caller-controlled)
        - canonical_run_record: Authority-owned (NOT caller-controlled)
        - Caller CANNOT choose authoritative identity fields
        
        Phase 2: Full implementation with cryptographic signing.
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Args:
            observed_identity: OS-derived process identity (NOT caller-controlled)
            canonical_run_record: Authority-owned run record (NOT caller-controlled)
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            TrustedExecutionIdentity with cryptographic signature (Phase 2)
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will bind to OS-observed identity and authority-owned run record
        return TrustedExecutionIdentity(
            issuer_pid=0,  # Phase 2: Will be OS-observed issuer PID
            issuer_generation=0,  # Phase 2: Will be from trust anchor
            consumer_pid=observed_identity.pid,  # OS-derived
            execution_id=canonical_run_record.execution_id,  # Authority-owned
            run_id=canonical_run_record.run_id,  # Authority-owned
            episode_id=canonical_run_record.episode_id,  # Authority-owned
            session_id=canonical_run_record.session_id,  # Authority-owned
            invocation_id=canonical_run_record.invocation_id,  # Authority-owned
            runtime_generation=0,  # Phase 2: Will be from trust anchor
            bootstrap_timestamp=0.0,  # Phase 2: Will be from trust anchor
            signature="placeholder",  # Phase 2: Will be HMAC signature
            issued_at=time.time(),
            expires_at=time.time() + ttl_seconds,
        )
    
    def verify_identity(self, identity: TrustedExecutionIdentity) -> bool:
        """Verify a trusted execution identity (Phase 2 only).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement signature verification.
        Phase 1: Raises Phase2Required (explicit, not fake security).
        
        SECURITY WARNING:
        - DO NOT use this method for real security in Phase 1
        - DO NOT rely on return False as fail-closed security
        - Phase 2 will implement real verification
        
        Args:
            identity: Identity to verify
            
        Returns:
            True if identity is valid (Phase 2 only)
            
        Raises:
            Phase2Required: Real verification requires Phase 2 authority process
        """
        # Phase 1: Explicit Phase2Required (NOT fake security)
        # Phase 2: Trusted authority process will implement real verification
        raise NotImplementedError(
            "Identity verification requires Phase 2 trusted authority process. "
            "This is a data contract method, not real security enforcement."
        )
