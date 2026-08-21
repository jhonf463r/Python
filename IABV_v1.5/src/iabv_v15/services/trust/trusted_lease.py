"""TrustedLease: Cryptographically bound capability for P0.213 V5.

This module provides the trusted lease/capability that can ONLY be issued
by the trusted lease issuer and verified against the trust anchor.

Design Principles:
- Issued by trusted lease issuer only
- Cryptographically signed with HMAC-SHA256
- Bound to trusted execution identity
- Bound to process identity (producer PID)
- Bound to runtime incarnation (generation)
- Bound to producer scope (authorization)
- Single-use semantics
- Expiration-based validity
- Fail-closed verification

LEASE BINDING CONTRACT:
- Issuer owns issuer/producer authority fields (NOT caller-controlled)
- Caller CANNOT choose issuer_pid, producer_pid, issuer_generation
- Unique lease ID is authority-generated (NOT caller-controlled)
- Authorization context is authority-owned (NOT caller-controlled)

IMMUTABILITY vs AUTHENTICITY vs AUTHORITY:
- IMMUTABILITY: dataclass(frozen=True) prevents mutation
- AUTHENTICITY: HMAC signature proves not tampered (Phase 2)
- AUTHORITY: Only LeaseIssuerService can issue (Phase 1 ownership model)
- from_dict() is deserialization ONLY, NOT automatic trust

Phase 1 Status: DESIGNED (ownership model defined, NOT_IMPLEMENTED)
Phase 2 Status: RUNTIME_VERIFIED (HMAC signature, OS identity)
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
    """Cryptographically bound lease/capability.
    
    This lease can ONLY be issued by LeaseIssuerService and verified
    against the trust anchor. Caller-constructed leases will be rejected.
    
    Design Principles:
    - Issuer: Trusted lease issuer (authority-owned, NOT caller-controlled)
    - Identity: Bound to trusted execution identity
    - Process: Bound to producer PID (OS-controlled, NOT caller-controlled)
    - Runtime: Bound to runtime generation (authority-owned)
    - Authorization: Bound to producer scope (authority-owned)
    - Lifecycle: Issued at, expires at, consumed flag
    - Cryptographic proof: HMAC-SHA256 signature (Phase 2)
    
    LEASE BINDING CONTRACT:
    - Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
    - Unique lease_id is authority-generated (NOT caller-controlled)
    - Authorization context is authority-owned (NOT caller-controlled)
    
    IMMUTABILITY vs AUTHENTICITY vs AUTHORITY:
    - IMMUTABILITY: dataclass(frozen=True) prevents mutation
    - AUTHENTICITY: HMAC signature proves not tampered (Phase 2)
    - AUTHORITY: Only LeaseIssuerService can issue (Phase 1 ownership model)
    - from_dict() is deserialization ONLY, NOT automatic trust
    
    The verifier must establish:
    - ISSUED_BY_TRUSTED_ISSUER (signature verification)
    - NOT_TAMPERED (signature verification)
    - CORRECT_IDENTITY (execution_id matches)
    - CORRECT_PROCESS (producer_pid matches OS PID)
    - CORRECT_RUNTIME (generation matches)
    - CORRECT_SCOPE (producer_scope matches)
    - NOT_EXPIRED (expiration check)
    - NOT_CONSUMED (single-use check)
    
    Phase 1 Status: DESIGNED (ownership model defined, NOT_IMPLEMENTED)
    Phase 2 Status: RUNTIME_VERIFIED (HMAC signature, OS identity)
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
    """Service that issues and verifies trusted leases.
    
    This service is the ONLY source of valid TrustedLease instances.
    It uses the RuntimeIdentityAuthority to verify execution identity.
    
    LEASE BINDING CONTRACT:
    - Issuer owns issuer_pid, producer_pid, issuer_generation (NOT caller-controlled)
    - Caller CANNOT choose authoritative lease fields
    - Unique lease_id is authority-generated (NOT caller-controlled)
    
    CANONICAL REJECTION CONDITIONS:
    - Invalid signature
    - Invalid issuer
    - Stale generation
    - Mismatched issuer
    - Mismatched execution identity
    - Expired lease
    - Consumed lease
    - Invalid binding
    
    Phase 1 Status: DESIGNED (ownership model defined, NOT_IMPLEMENTED)
    Phase 2 Status: RUNTIME_VERIFIED (HMAC signature, OS identity)
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
        """Verify a trusted lease.
        
        This is a FAIL-CLOSED verification. Any failure returns False.
        
        CANONICAL REJECTION CONDITIONS:
        - Invalid signature
        - Invalid issuer
        - Stale generation
        - Mismatched issuer
        - Mismatched execution identity
        - Expired lease
        - Consumed lease
        - Invalid binding
        
        Phase 2: Full implementation with signature verification.
        Phase 1: Always returns False (fail-closed, NOT_IMPLEMENTED)
        
        Args:
            lease: Lease to verify
            expected_scope: Optional scope to validate against
            
        Returns:
            True if lease is valid, False otherwise
        """
        # Phase 1: Always returns False (fail-closed, NOT_IMPLEMENTED)
        # Phase 2: Will verify signature, generation, binding, expiration
        return False
    
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
    """Registry for tracking issued leases.
    
    This registry is responsible for:
    - Storage of issued leases
    - Tracking lease consumption (single-use)
    - Tracking lease expiration
    - Invalidating stale leases on runtime restart
    
    LEASE STATE OWNERSHIP CONTRACT:
    - ONE AUTHORITY: LeaseRegistry is the ONLY authoritative lease state owner
    - ONE LEASE STATE OWNER: No duplicate registries
    - ONE CONSUMPTION OWNER: Only LeaseRegistry can authorize consumption
    - Rejects: invalid signature, expired lease, stale generation, duplicate lease ID, mismatched issuer, mismatched execution identity
    
    CANONICAL REJECTION CONDITIONS:
    - Invalid signature
    - Expired lease
    - Stale generation
    - Duplicate lease ID
    - Mismatched issuer
    - Mismatched execution identity
    - Already consumed
    
    SINGLE-USE SEMANTICS CONTRACT:
    - Single-use is an authority invariant
    - Phase 2 will provide OS/interprocess atomic enforcement
    - Phase 1: Placeholder (NOT_IMPLEMENTED)
    - dict.pop() is NOT interprocess exactly-once
    
    Phase 1 Status: DESIGNED (ownership model defined, NOT_IMPLEMENTED)
    Phase 2 Status: RUNTIME_VERIFIED (interprocess atomicity)
    """
    
    def __init__(self, trust_anchor: RootTrustAnchor):
        """Initialize lease registry.
        
        LEASE STATE OWNERSHIP: This is the ONLY authoritative lease state owner.
        
        Args:
            trust_anchor: Root trust anchor for generation tracking
        """
        self._trust_anchor = trust_anchor
        self._leases: dict[str, TrustedLease] = {}
    
    def register(self, lease: TrustedLease) -> None:
        """Register a lease in the registry.
        
        LEASE STATE OWNERSHIP: Only this registry can authorize lease state.
        
        CANONICAL REJECTION CONDITIONS:
        - Invalid signature
        - Expired lease
        - Stale generation
        - Duplicate lease ID
        - Mismatched issuer
        - Mismatched execution identity
        - Already consumed
        
        Phase 2: Full implementation with rejection checks.
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Args:
            lease: Lease to register
            
        Raises:
            ValueError: If lease is invalid or already consumed
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will check signature, generation, expiration, duplicates
        self._leases[lease.lease_id] = lease
    
    def consume(self, lease_id: str) -> TrustedLease | None:
        """Consume a lease (mark as used).
        
        SINGLE-USE SEMANTICS CONTRACT:
        - Single-use is an authority invariant
        - Phase 2 will provide OS/interprocess atomic enforcement
        - Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Args:
            lease_id: Lease ID of lease to consume
            
        Returns:
            Consumed lease, or None if not found
        """
        if lease_id not in self._leases:
            return None
        
        lease = self._leases.pop(lease_id)
        # Mark as consumed
        return dataclasses.replace(lease, consumed=True)
    
    def cleanup_expired(self) -> int:
        """Clean up expired leases.
        
        Phase 2: Full implementation with expiration check.
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Returns:
            Number of leases cleaned up
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will check expiration and remove expired leases
        return 0
    
    def invalidate_stale(self) -> int:
        """Invalidate leases from previous generation (runtime restart).
        
        Phase 2: Full implementation with generation check.
        Phase 1: Placeholder (NOT_IMPLEMENTED)
        
        Returns:
            Number of leases invalidated
        """
        # Phase 1: Placeholder (NOT_IMPLEMENTED)
        # Phase 2: Will check generation and invalidate stale leases
        return 0
    
    def count(self) -> int:
        """Count active leases.
        
        Returns:
            Number of active leases
        """
        return len(self._leases)
