"""TrustedLease: Data contract for lease/capability (P0.213 V5).

CRITICAL: This is a DATA CONTRACT, NOT a security boundary.

In-process Python objects cannot be security boundaries because any caller
can import and invoke public constructors, methods, and deserializers.
The real security boundary will be implemented in Phase 2 using a separate
trusted authority process and OS/IPC enforcement.

This module defines the DATA MODEL for:
- Lease/capability (cryptographically signed in Phase 2)
- Lease issuance protocol (Phase 2)
- Lease state ownership contract (Phase 2)

IMMUTABLE OBJECT != AUTHENTIC OBJECT != AUTHORIZED OBJECT:
- IMMUTABILITY: dataclass(frozen=True) prevents mutation (serialization operation)
- AUTHENTICITY: HMAC signature proves not tampered (Phase 2 only)
- AUTHORITY: Only trusted authority process can issue (Phase 2 only)
- from_dict() is deserialization ONLY, NOT automatic trust
- Deserialized objects are NEVER automatically authoritative

Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)

SECURITY WARNING:
- DO NOT treat this Python object as a security boundary
- DO NOT rely on class name "Trusted" for security
- DO NOT assume immutability provides authenticity
- Phase 2 will implement real authority boundary
"""

from __future__ import annotations

import dataclasses
import json
import time
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from iabv_v15.services.trust.root_trust_anchor import RootTrustAnchor
from iabv_v15.services.trust.trusted_execution_identity import (
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)


@dataclass(frozen=True)
class TrustedLease:
    """Data contract for cryptographically bound lease/capability.
    
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
    
    # Identity binding (authority-owned)
    execution_id: str
    invocation_id: str
    
    # Unique lease ID (authority-generated, NOT caller-controlled)
    lease_id: str
    
    # Process binding (authority-owned, NOT caller-controlled)
    producer_pid: int
    
    # Authorization (authority-owned, NOT caller-controlled)
    producer_scope: str
    authorization_context: Optional[str]  # Phase 2: Additional authorization context
    
    # Lifecycle (authority-owned)
    issued_at: float
    expires_at: float
    
    # Cryptographic proof (Phase 2: HMAC signature)
    signature: str
    
    # Consumption flag (has default)
    consumed: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        IMMUTABILITY: This is a serialization operation, NOT mutation.
        """
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TrustedLease':
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
        """Serialize lease fields for HMAC signing.
        
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


class LeaseIssuerService:
    """Data contract for lease issuer protocol (NON-AUTHORITATIVE).
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    
    This class defines the PROTOCOL INTERFACE for lease issuance,
    but does NOT implement real security enforcement in Phase 1.
    
    LEASE BINDING CONTRACT (Phase 2):
    - Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
    - Caller CANNOT choose authoritative lease fields
    - Unique lease_id is authority-generated (NOT caller-controlled)
    
    Phase 1: Data contract and protocol interface (non-authoritative)
    Phase 2: Trusted authority process implements real security enforcement
    
    SECURITY WARNING:
    - DO NOT use this class as a security boundary
    - DO NOT rely on issue_lease() for real authority in Phase 1
    - DO NOT use verify_lease() -> False as fake security
    - Phase 2 will implement real authority boundary
    
    Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative protocol)
    Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
    """
    
    def __init__(
        self,
        trust_anchor: RootTrustAnchor,
        identity_authority: RuntimeIdentityAuthority,
    ):
        """Initialize lease issuer service.
        
        Args:
            trust_anchor: Root trust anchor for OS-controlled state
            identity_authority: Runtime identity authority for identity verification
        """
        self._trust_anchor = trust_anchor
        self._identity_authority = identity_authority
    
    def issue_lease(
        self,
        identity: TrustedExecutionIdentity,
        authorized_scope: str,
        authorization_context: Optional[str] = None,
        ttl_seconds: int = 300,
    ) -> TrustedLease:
        """Issue a trusted lease.
        
        LEASE BINDING CONTRACT:
        - Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
        - Caller CANNOT choose authoritative lease fields
        - Unique lease_id is authority-generated (NOT caller-controlled)
        
        Phase 2: Full implementation with cryptographic signing.
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Args:
            identity: Trusted execution identity to bind to
            authorized_scope: Authorized scope (authority-owned, NOT caller-controlled)
            authorization_context: Additional authorization context (authority-owned)
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            TrustedLease with cryptographic signature (Phase 2)
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will bind to authority-owned issuer/producer fields
        return TrustedLease(
            issuer_pid=0,  # Phase 2: Will be OS-observed issuer PID
            issuer_generation=0,  # Phase 2: Will be from trust anchor
            execution_id=identity.execution_id,
            invocation_id=identity.invocation_id,
            lease_id=str(uuid4()),  # Authority-generated (NOT caller-controlled)
            producer_pid=0,  # Phase 2: Will be OS-observed producer PID
            producer_scope=authorized_scope,  # Authority-owned
            authorization_context=authorization_context,  # Authority-owned
            issued_at=time.time(),
            expires_at=time.time() + ttl_seconds,
            signature="placeholder",  # Phase 2: Will be HMAC signature
            consumed=False,
        )
    
    def verify_lease(
        self,
        lease: TrustedLease,
        expected_scope: str | None = None,
    ) -> bool:
        """Verify a trusted lease (Phase 2 only).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement signature verification.
        Phase 1: Raises Phase2Required (explicit, not fake security).
        
        SECURITY WARNING:
        - DO NOT use this method for real security in Phase 1
        - DO NOT rely on return False as fail-closed security
        - Phase 2 will implement real verification
        
        Args:
            lease: Lease to verify
            expected_scope: Optional scope to validate against
            
        Returns:
            True if lease is valid (Phase 2 only)
            
        Raises:
            Phase2Required: Real verification requires Phase 2 authority process
        """
        # Phase 1: Explicit Phase2Required (NOT fake security)
        # Phase 2: Trusted authority process will implement real verification
        raise NotImplementedError(
            "Lease verification requires Phase 2 trusted authority process. "
            "This is a data contract method, not real security enforcement."
        )
    
    def consume_lease(self, lease: TrustedLease) -> TrustedLease:
        """Mark lease as consumed (single-use semantics).
        
        SINGLE-USE SEMANTICS CONTRACT:
        - Single-use is an authority invariant
        - Phase 2 will provide OS/interprocess atomic enforcement
        - Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Args:
            lease: Lease to consume
            
        Returns:
            Consumed lease (with consumed=True)
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will be atomic with OS/interprocess enforcement
        return dataclasses.replace(lease, consumed=True)


class LeaseRegistry:
    """Data contract for lease state store (NON-AUTHORITATIVE).
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    
    Phase 1 must NOT pretend a Python dictionary is the authoritative
    security registry. The real security boundary will be implemented in
    Phase 2 using a separate trusted authority process.
    
    LEASE STATE OWNERSHIP CONTRACT (Phase 2):
    - Phase 2 authority process is the sole authoritative lease state owner
    - Phase 2 authority process is the sole consumption owner
    - Phase 2: OS/interprocess atomic enforcement for single-use
    
    Phase 1: In-process data structure for contract specification (NON_AUTHORITATIVE)
    Phase 2: Trusted authority process implements real security enforcement
    
    SECURITY WARNING:
    - DO NOT treat this Python dictionary as authoritative
    - DO NOT assume dict.pop() is interprocess exactly-once
    - DO NOT use this class as a security boundary
    - Phase 2 will implement real authority boundary
    
    Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative test model)
    Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
    """
    
    def __init__(self, trust_anchor: RootTrustAnchor):
        """Initialize lease state store (NON-AUTHORITATIVE).
        
        CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
        Phase 2: Trusted authority process will be the sole authoritative owner.
        Phase 1: In-process data structure for contract specification.
        
        Args:
            trust_anchor: Root trust anchor for generation tracking
        """
        self._trust_anchor = trust_anchor
        self._leases: dict[str, TrustedLease] = {}  # NON_AUTHORITATIVE_TEST_MODEL
    
    def register(self, lease: TrustedLease) -> None:
        """Register a lease in the state store (NON-AUTHORITATIVE).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement canonical rejection.
        Phase 1: In-process storage for contract specification.
        
        SECURITY WARNING:
        - DO NOT rely on this for real security in Phase 1
        - Phase 2 will implement real rejection checks
        
        Args:
            lease: Lease to register
        """
        # Phase 1: In-process storage (NON_AUTHORITATIVE_TEST_MODEL)
        # Phase 2: Trusted authority process will implement canonical rejection
        self._leases[lease.lease_id] = lease
    
    def consume(self, lease_id: str) -> TrustedLease | None:
        """Consume a lease (NON-AUTHORITATIVE).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement OS/interprocess atomicity.
        Phase 1: dict.pop() is NOT interprocess exactly-once.
        
        SECURITY WARNING:
        - DO NOT rely on dict.pop() for interprocess exactly-once
        - DO NOT use this for real security in Phase 1
        - Phase 2 will implement real atomic enforcement
        
        Args:
            lease_id: Lease ID of lease to consume
            
        Returns:
            Consumed lease, or None if not found
        """
        # Phase 1: dict.pop() is NOT interprocess exactly-once (NON_AUTHORITATIVE_TEST_MODEL)
        # Phase 2: Trusted authority process will implement OS/interprocess atomicity
        if lease_id not in self._leases:
            return None
        
        lease = self._leases.pop(lease_id)
        return dataclasses.replace(lease, consumed=True)
    
    def cleanup_expired(self) -> int:
        """Clean up expired leases (NON-AUTHORITATIVE).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement expiration check.
        Phase 1: Returns 0 (placeholder).
        
        Returns:
            Number of leases cleaned up (Phase 1: 0 placeholder)
        """
        # Phase 1: Returns 0 (NON_AUTHORITATIVE_TEST_MODEL)
        # Phase 2: Trusted authority process will implement expiration check
        return 0
    
    def invalidate_stale(self) -> int:
        """Invalidate leases from previous generation (NON-AUTHORITATIVE).
        
        CRITICAL: This is a DATA CONTRACT method, NOT real security enforcement.
        Phase 2: Trusted authority process will implement generation check.
        Phase 1: Returns 0 (placeholder).
        
        Returns:
            Number of leases invalidated (Phase 1: 0 placeholder)
        """
        # Phase 1: Returns 0 (NON_AUTHORITATIVE_TEST_MODEL)
        # Phase 2: Trusted authority process will implement generation check
        return 0
    
    def count(self) -> int:
        """Count active leases.
        
        Returns:
            Number of active leases
        """
        return len(self._leases)
