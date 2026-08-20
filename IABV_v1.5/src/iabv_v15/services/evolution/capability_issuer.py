"""
Capability Issuer - P0.213 V5R1

Issues invocation capabilities to authorized consumer processes.

This is the ISSUER in the trust authority chain:
ROOT TRUST ANCHOR → AUTHORIZED ISSUER → INVOCATION CAPABILITY → CONSUMER → VERIFIER

Key Principle: The issuer must be bound to the root trust anchor to prevent
arbitrary construction of capabilities.

P0.213 V5R2: Uses RootTrustAnchor.get_instance() to ensure canonical authority.
"""

import os
import time
from typing import Optional
from uuid import uuid4
from pathlib import Path

from iabv_v15.services.evolution.invocation_capability import InvocationCapability
from iabv_v15.services.evolution.root_trust_anchor import RootTrustAnchor


class CapabilityIssuer:
    """
    P0.213 V5R2: Issues invocation capabilities bound to RootTrustAnchor.
    
    This is the ISSUER in the trust authority chain:
    ROOT TRUST ANCHOR → AUTHORIZED ISSUER → INVOCATION CAPABILITY → CONSUMER
    
    The issuer cannot be freely constructed by caller. It must be bound to
    the RootTrustAnchor, which controls:
    - Secret key material
    - Runtime incarnation
    - Process identity
    
    This prevents caller from injecting arbitrary authority.
    """
    
    def __init__(
        self,
        root_trust_anchor: RootTrustAnchor,
    ):
        """
        P0.213 V5R2: Initialize the capability issuer.
        
        Args:
            root_trust_anchor: The root trust anchor (required)
        
        Raises:
            ValueError: If root_trust_anchor is None
        """
        if root_trust_anchor is None:
            raise ValueError("root_trust_anchor is required")
        
        self._root_trust_anchor = root_trust_anchor
        self._issuer_pid = os.getpid()
        self._secret_key = root_trust_anchor.get_secret_key()
        self._runtime_incarnation = root_trust_anchor.get_runtime_identity().generation
        
        # P0.213 V5R2: Store canonical path for verification
        self._canonical_storage_root = root_trust_anchor._storage_root
    
    @property
    def issuer_pid(self) -> int:
        """Get the issuer PID (OS-controlled)."""
        return self._issuer_pid
    
    @property
    def runtime_incarnation(self) -> int:
        """Get the runtime incarnation (from RootTrustAnchor)."""
        return self._runtime_incarnation
    
    @property
    def root_trust_anchor(self) -> RootTrustAnchor:
        """Get the root trust anchor."""
        return self._root_trust_anchor
    
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
        P0.213 V5R1: Verify the signature of a capability using RootTrustAnchor.
        
        This is used by the verifier to confirm the capability was issued
        by a trusted issuer bound to the RootTrustAnchor.
        
        Args:
            capability: The capability to verify
        
        Returns:
            bool: True if signature is valid, False otherwise
        """
        return capability.verify_signature(self._secret_key)
    
    def get_issuer_identity(self) -> dict:
        """
        P0.213 V5R1: Get the issuer identity for verification.
        
        Returns:
            dict: Issuer identity including PID and runtime incarnation
        """
        return {
            "issuer_pid": self._issuer_pid,
            "runtime_incarnation": self._runtime_incarnation,
        }
    
    def is_canonical(self, expected_storage_root: Path | str) -> bool:
        """
        P0.213 V5R2: Verify this issuer is bound to the canonical RootTrustAnchor.
        
        Args:
            expected_storage_root: The expected canonical storage root
            
        Returns:
            True if bound to canonical RootTrustAnchor, False otherwise
        """
        return self._canonical_storage_root == Path(expected_storage_root).resolve()
