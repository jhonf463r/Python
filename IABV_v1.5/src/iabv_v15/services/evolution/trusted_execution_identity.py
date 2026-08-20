"""TrustedExecutionIdentity: Cryptographically bound execution identity for P0.213 V4.

This module provides the trusted execution identity that can ONLY be issued
by the trusted runtime authority and verified against the trust anchor.

Design Principles:
- Issued by trusted runtime authority only
- Cryptographically signed with HMAC-SHA256
- Bound to runtime incarnation (generation, bootstrap timestamp)
- Bound to process identity (issuer PID)
- Fail-closed verification (rejects all invalid identities)

This is part of P0.213 V4 corrected implementation with real security controls.
"""
from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from iabv_v15.services.evolution.root_trust_anchor import (
    ProcessIdentity,
    RootTrustAnchor,
    RuntimeIdentity,
)


@dataclass(frozen=True)
class TrustedExecutionIdentity:
    """Cryptographically bound execution identity.
    
    This identity can ONLY be issued by RuntimeIdentityAuthority and verified
    against the trust anchor. Caller-constructed identities will be rejected.
    
    Design Principles:
    - Issuer: Trusted runtime authority
    - Execution: Authority-generated UUIDs
    - Runtime binding: Generation and bootstrap timestamp
    - Process binding: Issuer PID
    - Cryptographic proof: HMAC-SHA256 signature
    - Expiration: Time-based validity
    
    The verifier must establish:
    - ISSUED_BY_TRUSTED_AUTHORITY (signature verification)
    - NOT_TAMPERED (signature verification)
    - CORRECT_RUNTIME (generation and bootstrap match)
    - CORRECT_PROCESS_CONTEXT (issuer PID matches)
    - NOT_STALE (expiration check)
    """
    
    # Issuer
    issuer_pid: int
    issuer_generation: int
    
    # Consumer (process for which this identity is valid)
    consumer_pid: int
    
    # Execution (authority-generated)
    execution_id: str
    run_id: str
    episode_id: str | None
    session_id: str | None
    invocation_id: str
    
    # Runtime binding
    runtime_generation: int
    bootstrap_timestamp: float
    
    # Cryptographic proof
    signature: str
    
    # Metadata
    issued_at: float
    expires_at: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TrustedExecutionIdentity':
        """Create from dictionary (deserialization)."""
        return cls(**data)
    
    def _serialize_for_signature(self) -> str:
        """Serialize identity fields for HMAC signing.
        
        Returns:
            JSON string of all fields except signature
        """
        # Create dict without signature
        data = self.to_dict()
        data.pop('signature', None)
        
        # Sort keys for deterministic serialization
        return json.dumps(data, sort_keys=True)


class RuntimeIdentityAuthority:
    """Authority that issues and verifies trusted execution identities.
    
    This authority is the ONLY source of valid TrustedExecutionIdentity instances.
    It uses the RootTrustAnchor to provide OS-controlled trust anchor.
    """
    
    def __init__(self, trust_anchor: RootTrustAnchor):
        """Initialize identity authority.
        
        Args:
            trust_anchor: Root trust anchor for OS-controlled state
        """
        self._trust_anchor = trust_anchor
    
    def issue_identity(
        self,
        consumer_pid: int | None = None,
        run_id: str | None = None,
        episode_id: str | None = None,
        session_id: str | None = None,
        ttl_seconds: int = 3600,
    ) -> TrustedExecutionIdentity:
        """Issue a trusted execution identity.
        
        Args:
            consumer_pid: PID of the consumer process (child). If None, defaults to current PID (self-issued).
            run_id: Optional run ID (generated if not provided)
            episode_id: Optional episode ID
            session_id: Optional session ID
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            TrustedExecutionIdentity with cryptographic signature
            
        Raises:
            RuntimeError: If trust anchor is not available
        """
        # Get runtime state (OS-controlled)
        process_identity = self._trust_anchor.get_process_identity()
        runtime_identity = self._trust_anchor.get_runtime_identity()
        
        # Generate authority-controlled UUIDs
        execution_id = str(uuid4())
        invocation_id = str(uuid4())
        
        # Use provided run_id or generate
        if run_id is None:
            run_id = execution_id
        
        # Default consumer_pid to current PID if not provided (self-issued identity)
        if consumer_pid is None:
            consumer_pid = process_identity.pid
        
        # Create identity (unsigned)
        identity = TrustedExecutionIdentity(
            issuer_pid=process_identity.pid,
            issuer_generation=runtime_identity.generation,
            consumer_pid=consumer_pid,
            execution_id=execution_id,
            run_id=run_id,
            episode_id=episode_id,
            session_id=session_id,
            invocation_id=invocation_id,
            runtime_generation=runtime_identity.generation,
            bootstrap_timestamp=runtime_identity.bootstrap_timestamp,
            signature="",  # Will be filled
            issued_at=time.time(),
            expires_at=time.time() + ttl_seconds,
        )
        
        # Sign identity
        signature = self._sign_identity(identity)
        identity = dataclasses.replace(identity, signature=signature)
        
        return identity
    
    def verify_identity(self, identity: TrustedExecutionIdentity) -> bool:
        """Verify a trusted execution identity.
        
        This is a FAIL-CLOSED verification. Any failure returns False.
        
        Args:
            identity: Identity to verify
            
        Returns:
            True if identity is valid, False otherwise
        """
        try:
            # 1. Verify signature
            if not self._verify_signature(identity):
                return False
            
            # 2. Verify runtime generation
            current_generation = self._trust_anchor.get_runtime_identity().generation
            if identity.runtime_generation != current_generation:
                return False
            
            # 3. Verify bootstrap timestamp
            current_bootstrap = self._trust_anchor.get_runtime_identity().bootstrap_timestamp
            if identity.bootstrap_timestamp != current_bootstrap:
                return False
            
            # 4. Verify consumer PID (identity is valid only for the specified consumer)
            current_pid = self._trust_anchor.get_process_identity().pid
            if identity.consumer_pid != current_pid:
                # Identity is not valid for this process
                return False
            
            # 5. Verify issuer is parent of consumer (parent-child relationship)
            # Skip verification for self-issued identities (issuer_pid == consumer_pid)
            if identity.issuer_pid != identity.consumer_pid:
                try:
                    import psutil
                    current_process = psutil.Process(current_pid)
                    parent_pid = current_process.ppid()
                    
                    # Identity must have been issued by parent process
                    if identity.issuer_pid != parent_pid:
                        # Identity was not issued by parent
                        return False
                except Exception:
                    # If psutil is not available or fails, reject (fail-closed)
                    return False
            
            # 5. Verify expiration
            if time.time() > identity.expires_at:
                return False
            
            return True
        except Exception:
            # Any exception means verification failed
            return False
    
    def _sign_identity(self, identity: TrustedExecutionIdentity) -> str:
        """Sign identity with HMAC-SHA256.
        
        Args:
            identity: Identity to sign
            
        Returns:
            Hex-encoded HMAC signature
        """
        message = identity._serialize_for_signature()
        return self._trust_anchor.compute_hmac(message)
    
    def _verify_signature(self, identity: TrustedExecutionIdentity) -> bool:
        """Verify HMAC signature.
        
        Args:
            identity: Identity to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        message = identity._serialize_for_signature()
        return self._trust_anchor.verify_hmac(message, identity.signature)
