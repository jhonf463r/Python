"""
Invocation Capability - P0.213 V5

A cryptographically bound token that authorizes a specific process to execute
within a specific scope for a single invocation.

This is the core authority mechanism for P0.213, replacing the V4 approach
where identity verification was treated as the primary authority.

Key Principle: Identity ≠ Authorization. A verified identity doesn't prove
the current invocation is authorized to execute within a specific scope.
"""

import os
import time
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass(frozen=True)
class InvocationCapability:
    """
    A cryptographically bound capability that authorizes a specific process
    to execute within a specific scope for a single invocation.
    
    This is NOT an identity. This is an authorization token.
    """
    # Issuer information
    issuer_pid: int  # PID of the process that issued this capability (parent)
    
    # Authorized consumer
    authorized_consumer_pid: int  # PID of the process authorized to consume (child)
    
    # Capability identifiers
    capability_id: str  # Unique identifier for this capability
    invocation_id: str  # Unique identifier for the authorized invocation
    
    # Authorization scope
    scope: str  # Authorized execution scope (e.g., "tool_execution", "learning_update")
    
    # Temporal validity
    issued_at: float  # Timestamp when capability was issued
    expires_at: float  # Timestamp when capability becomes invalid
    
    # Runtime binding
    runtime_incarnation: int  # Runtime generation identifier (prevents cross-run replay)
    
    # Optional session binding
    session_id: Optional[str] = None  # Session identifier (prevents cross-session replay)
    
    # Cryptographic signature
    signature: str = field(default="")  # Signature binding all fields
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.capability_id:
            raise ValueError("capability_id is required")
        if not self.invocation_id:
            raise ValueError("invocation_id is required")
        if not self.scope:
            raise ValueError("scope is required")
        if self.issued_at <= 0:
            raise ValueError("issued_at must be positive")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.runtime_incarnation <= 0:
            raise ValueError("runtime_incarnation must be positive")
    
    def is_expired(self) -> bool:
        """Check if capability is expired."""
        return time.time() > self.expires_at
    
    def is_valid_for_consumer(self, consumer_pid: int) -> bool:
        """Check if capability is valid for the specified consumer."""
        return self.authorized_consumer_pid == consumer_pid
    
    def is_valid_for_scope(self, requested_scope: str) -> bool:
        """Check if capability is valid for the requested scope."""
        return self.scope == requested_scope
    
    def is_valid_for_runtime(self, current_runtime_incarnation: int) -> bool:
        """Check if capability is valid for the current runtime incarnation."""
        return self.runtime_incarnation == current_runtime_incarnation
    
    def to_dict(self) -> dict:
        """Convert capability to dictionary for serialization."""
        return {
            "issuer_pid": self.issuer_pid,
            "authorized_consumer_pid": self.authorized_consumer_pid,
            "capability_id": self.capability_id,
            "invocation_id": self.invocation_id,
            "scope": self.scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "runtime_incarnation": self.runtime_incarnation,
            "session_id": self.session_id,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InvocationCapability":
        """Create capability from dictionary."""
        return cls(
            issuer_pid=data["issuer_pid"],
            authorized_consumer_pid=data["authorized_consumer_pid"],
            capability_id=data["capability_id"],
            invocation_id=data["invocation_id"],
            scope=data["scope"],
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            runtime_incarnation=data["runtime_incarnation"],
            session_id=data.get("session_id"),
            signature=data.get("signature", ""),
        )
    
    def compute_signature(self, secret_key: bytes) -> str:
        """
        Compute HMAC signature over all capability fields.
        
        This binds the capability to the issuer and prevents forgery.
        """
        # Create a canonical string representation of all fields
        canonical = (
            f"{self.issuer_pid}|"
            f"{self.authorized_consumer_pid}|"
            f"{self.capability_id}|"
            f"{self.invocation_id}|"
            f"{self.scope}|"
            f"{self.issued_at}|"
            f"{self.expires_at}|"
            f"{self.runtime_incarnation}|"
            f"{self.session_id or ''}"
        )
        
        # Compute HMAC-SHA256 signature
        signature = hmac.new(
            secret_key,
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_signature(self, secret_key: bytes) -> bool:
        """
        Verify the capability signature.
        
        Returns True if signature is valid, False otherwise.
        """
        if not self.signature:
            return False
        
        expected_signature = self.compute_signature(secret_key)
        return hmac.compare_digest(self.signature, expected_signature)
