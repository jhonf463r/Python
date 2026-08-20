"""
Capability Issuer - P0.213 V5

Issues invocation capabilities to authorized consumer processes.

The issuer is the parent process that authorizes a child process to execute
within a specific scope for a single invocation.

Key Principle: Only the issuer can create capabilities. Consumers cannot
issue capabilities to other processes.
"""

import os
import time
from typing import Optional
from uuid import uuid4

from iabv_v15.services.evolution.invocation_capability import InvocationCapability


class CapabilityIssuer:
    """
    Issues invocation capabilities to authorized consumer processes.
    
    This is the ISSUER in the trust authority chain:
    TRUST ANCHOR → AUTHORITY → ISSUER → INVOCATION CAPABILITY → CONSUMER
    """
    
    def __init__(
        self,
        issuer_pid: Optional[int] = None,
        secret_key: Optional[bytes] = None,
        runtime_incarnation: Optional[int] = None,
    ):
        """
        Initialize the capability issuer.
        
        Args:
            issuer_pid: PID of the issuer process (defaults to current PID)
            secret_key: Secret key for signing capabilities (defaults to random)
            runtime_incarnation: Runtime generation identifier
        """
        self._issuer_pid = issuer_pid or os.getpid()
        self._secret_key = secret_key or os.urandom(32)
        self._runtime_incarnation = runtime_incarnation or 1
    
    @property
    def issuer_pid(self) -> int:
        """Get the issuer PID."""
        return self._issuer_pid
    
    @property
    def runtime_incarnation(self) -> int:
        """Get the runtime incarnation."""
        return self._runtime_incarnation
    
    def issue_capability(
        self,
        authorized_consumer_pid: int,
        scope: str,
        ttl_seconds: float = 3600.0,
        session_id: Optional[str] = None,
    ) -> InvocationCapability:
        """
        Issue a capability to an authorized consumer.
        
        Args:
            authorized_consumer_pid: PID of the process authorized to consume
            scope: Authorized execution scope
            ttl_seconds: Time-to-live for the capability (default: 1 hour)
            session_id: Optional session identifier for cross-session replay prevention
        
        Returns:
            InvocationCapability: The issued capability
        
        Raises:
            ValueError: If authorized_consumer_pid is invalid or scope is empty
        """
        if authorized_consumer_pid <= 0:
            raise ValueError("authorized_consumer_pid must be positive")
        if not scope:
            raise ValueError("scope cannot be empty")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        
        # Generate unique identifiers
        capability_id = str(uuid4())
        invocation_id = str(uuid4())
        
        # Set temporal validity
        issued_at = time.time()
        expires_at = issued_at + ttl_seconds
        
        # Create capability without signature
        capability = InvocationCapability(
            issuer_pid=self._issuer_pid,
            authorized_consumer_pid=authorized_consumer_pid,
            capability_id=capability_id,
            invocation_id=invocation_id,
            scope=scope,
            issued_at=issued_at,
            expires_at=expires_at,
            runtime_incarnation=self._runtime_incarnation,
            session_id=session_id,
            signature="",  # Will be set below
        )
        
        # Compute and set signature
        signature = capability.compute_signature(self._secret_key)
        
        # Create new capability with signature (since dataclass is frozen)
        capability = InvocationCapability(
            issuer_pid=capability.issuer_pid,
            authorized_consumer_pid=capability.authorized_consumer_pid,
            capability_id=capability.capability_id,
            invocation_id=capability.invocation_id,
            scope=capability.scope,
            issued_at=capability.issued_at,
            expires_at=capability.expires_at,
            runtime_incarnation=capability.runtime_incarnation,
            session_id=capability.session_id,
            signature=signature,
        )
        
        return capability
    
    def verify_capability_signature(self, capability: InvocationCapability) -> bool:
        """
        Verify the signature of a capability.
        
        This is used by the verifier to confirm the capability was issued
        by this issuer.
        
        Args:
            capability: The capability to verify
        
        Returns:
            bool: True if signature is valid, False otherwise
        """
        return capability.verify_signature(self._secret_key)
