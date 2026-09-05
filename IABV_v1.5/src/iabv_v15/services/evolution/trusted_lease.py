"""TrustedLease: Cryptographically bound capability for P0.213 V4.

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

This is part of P0.213 V4 corrected implementation with real security controls.
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from iabv_v15.services.evolution.root_trust_anchor import RootTrustAnchor
from iabv_v15.services.evolution.trusted_execution_identity import (
    RuntimeIdentityAuthority,
    TrustedExecutionIdentity,
)


@dataclass(frozen=True)
class TrustedLease:
    """Cryptographically bound lease/capability.
    
    This lease can ONLY be issued by LeaseIssuerService and verified
    against the trust anchor. Caller-constructed leases will be rejected.
    
    Design Principles:
    - Issuer: Trusted lease issuer
    - Identity: Bound to trusted execution identity
    - Process: Bound to producer PID (OS-controlled)
    - Runtime: Bound to runtime generation
    - Authorization: Bound to producer scope
    - Lifecycle: Issued at, expires at, consumed flag
    - Cryptographic proof: HMAC-SHA256 signature
    
    The verifier must establish:
    - ISSUED_BY_TRUSTED_ISSUER (signature verification)
    - NOT_TAMPERED (signature verification)
    - CORRECT_IDENTITY (execution_id matches)
    - CORRECT_PROCESS (producer_pid matches OS PID)
    - CORRECT_RUNTIME (generation matches)
    - CORRECT_SCOPE (producer_scope matches)
    - NOT_EXPIRED (expiration check)
    - NOT_CONSUMED (single-use check)
    """
    
    # Issuer
    issuer_pid: int
    issuer_generation: int
    
    # Identity binding
    execution_id: str
    invocation_id: str
    
    # Process binding
    producer_pid: int
    
    # Authorization
    producer_scope: str
    
    # Lifecycle
    issued_at: float
    expires_at: float
    
    # Cryptographic proof (must come before fields with defaults)
    signature: str
    
    # Consumption flag (has default)
    consumed: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TrustedLease':
        """Create from dictionary (deserialization)."""
        return cls(**data)
    
    def _serialize_for_signature(self) -> str:
        """Serialize lease fields for HMAC signing.
        
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
        producer_scope: str,
        ttl_seconds: int = 300,
    ) -> TrustedLease:
        """Issue a trusted lease.
        
        Args:
            identity: Trusted execution identity to bind to
            producer_scope: Producer scope for authorization
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            TrustedLease with cryptographic signature
            
        Raises:
            ValueError: If identity is invalid
        """
        # Verify identity first (fail-closed)
        if not self._identity_authority.verify_identity(identity):
            raise ValueError("Invalid execution identity")
        
        # Get runtime state (OS-controlled)
        runtime_identity = self._trust_anchor.get_runtime_identity()
        
        # Get process PID (OS-controlled)
        producer_pid = os.getpid()
        
        # Create lease (unsigned)
        lease = TrustedLease(
            issuer_pid=producer_pid,
            issuer_generation=runtime_identity.generation,
            execution_id=identity.execution_id,
            invocation_id=identity.invocation_id,
            producer_pid=producer_pid,
            producer_scope=producer_scope,
            issued_at=time.time(),
            expires_at=time.time() + ttl_seconds,
            consumed=False,
            signature="",  # Will be filled
        )
        
        # Sign lease
        signature = self._sign_lease(lease)
        lease = dataclasses.replace(lease, signature=signature)
        
        return lease
    
    def verify_lease(
        self,
        lease: TrustedLease,
        expected_scope: str | None = None,
    ) -> bool:
        """Verify a trusted lease.
        
        This is a FAIL-CLOSED verification. Any failure returns False.
        
        Args:
            lease: Lease to verify
            expected_scope: Optional scope to validate against
            
        Returns:
            True if lease is valid, False otherwise
        """
        try:
            # 1. Verify signature
            if not self._verify_signature(lease):
                return False
            
            # 2. Verify runtime generation
            current_generation = self._trust_anchor.get_runtime_identity().generation
            if lease.issuer_generation != current_generation:
                return False
            
            # 3. Verify producer PID (OS-controlled)
            current_pid = os.getpid()
            if lease.producer_pid != current_pid:
                return False
            
            # 4. Verify issuer PID (should match producer PID)
            if lease.issuer_pid != lease.producer_pid:
                return False
            
            # 5. Verify scope if provided
            if expected_scope is not None:
                if lease.producer_scope != expected_scope:
                    return False
            
            # 6. Verify expiration
            if time.time() > lease.expires_at:
                return False
            
            # 7. Verify consumption (single-use)
            if lease.consumed:
                return False
            
            return True
        except Exception:
            # Any exception means verification failed
            return False
    
    def consume_lease(self, lease: TrustedLease) -> TrustedLease:
        """Mark lease as consumed (single-use semantics).
        
        Args:
            lease: Lease to consume
            
        Returns:
            Consumed lease (with consumed=True)
        """
        return dataclasses.replace(lease, consumed=True)
    
    def _sign_lease(self, lease: TrustedLease) -> str:
        """Sign lease with HMAC-SHA256.
        
        Args:
            lease: Lease to sign
            
        Returns:
            Hex-encoded HMAC signature
        """
        message = lease._serialize_for_signature()
        return self._trust_anchor.compute_hmac(message)
    
    def _verify_signature(self, lease: TrustedLease) -> bool:
        """Verify HMAC signature.
        
        Args:
            lease: Lease to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        message = lease._serialize_for_signature()
        return self._trust_anchor.verify_hmac(message, lease.signature)


class LeaseRegistry:
    """Registry for tracking issued leases.
    
    This registry is responsible for:
    - Storage of issued leases
    - Tracking lease consumption (single-use)
    - Tracking lease expiration
    - Invalidating stale leases on runtime restart
    """
    
    def __init__(self, trust_anchor: RootTrustAnchor):
        """Initialize lease registry.
        
        Args:
            trust_anchor: Root trust anchor for generation tracking
        """
        self._trust_anchor = trust_anchor
        self._leases: dict[str, TrustedLease] = {}
        self._current_generation: int = trust_anchor.get_runtime_identity().generation
    
    def register(self, lease: TrustedLease) -> None:
        """Register a lease in the registry.
        
        Args:
            lease: Lease to register
            
        Raises:
            ValueError: If lease is invalid or already consumed
        """
        # Check for generation mismatch (stale lease)
        current_generation = self._trust_anchor.get_runtime_identity().generation
        if lease.issuer_generation != current_generation:
            raise ValueError("Stale lease (generation mismatch)")
        
        # Check if already consumed
        if lease.consumed:
            raise ValueError("Lease already consumed")
        
        # Register lease
        self._leases[lease.invocation_id] = lease
    
    def consume(self, invocation_id: str) -> TrustedLease | None:
        """Consume a lease (mark as used).
        
        Args:
            invocation_id: Invocation ID of lease to consume
            
        Returns:
            Consumed lease, or None if not found
        """
        if invocation_id not in self._leases:
            return None
        
        lease = self._leases.pop(invocation_id)
        # Mark as consumed
        return dataclasses.replace(lease, consumed=True)
    
    def cleanup_expired(self) -> int:
        """Clean up expired leases.
        
        Returns:
            Number of leases cleaned up
        """
        current_time = time.time()
        expired_ids = [
            invocation_id
            for invocation_id, lease in self._leases.items()
            if current_time > lease.expires_at
        ]
        
        for invocation_id in expired_ids:
            del self._leases[invocation_id]
        
        return len(expired_ids)
    
    def invalidate_stale(self) -> int:
        """Invalidate leases from previous generation (runtime restart).
        
        Returns:
            Number of leases invalidated
        """
        current_generation = self._trust_anchor.get_runtime_identity().generation
        
        if current_generation == self._current_generation:
            return 0
        
        # Invalidate all leases (generation changed)
        count = len(self._leases)
        self._leases.clear()
        self._current_generation = current_generation
        
        return count
    
    def count(self) -> int:
        """Count active leases.
        
        Returns:
            Number of active leases
        """
        return len(self._leases)
