"""LeaseRegistry: Storage and tracking for InternalMcpInvocation leases.

This registry is responsible for:
- Storage of issued leases
- Tracking lease consumption (single-use)
- Tracking lease expiration
- Invalidating stale leases on runtime restart

This is part of P0.213 V3 corrected implementation based on Codex security
boundary failure analysis.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict

from iabv_v15.infra.ipc.lease_issuer_service import InternalMcpInvocation, LeaseIssuerService


class LeaseRegistry:
    """Registry for storing and tracking InternalMcpInvocation leases.
    
    This class is responsible for:
    - Storage of issued leases
    - Consumption tracking (single-use)
    - Expiration tracking
    - Stale lease invalidation
    
    Contract Compliance:
    - Storage and consumption tracking responsibility
    - Thread-safe operation
    - Separation from LeaseIssuerService
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'LeaseRegistry':
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize LeaseRegistry."""
        # Avoid re-initialization in singleton pattern
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._lock = threading.Lock()
        self._leases: Dict[str, InternalMcpInvocation] = {}
        self._lease_issuer = LeaseIssuerService()
    
    def register(self, lease: InternalMcpInvocation) -> bool:
        """Register a lease in the registry.
        
        Args:
            lease: The lease to register
            
        Returns:
            True if registration succeeded, False otherwise
            
        Raises:
            ValueError: If lease is invalid or registration fails
        """
        with self._lock:
            # Validate lease format
            if not self._lease_issuer.validate_lease(lease):
                raise ValueError("Invalid lease")
            
            # Check for stale incarnation
            from iabv_v15.services.evolution.runtime_identity_authority import RuntimeIdentityAuthority
            authority = RuntimeIdentityAuthority()
            current_incarnation = authority.get_incarnation()
            
            if lease.runtime_incarnation_hash != current_incarnation.incarnation_hash:
                raise ValueError("Stale lease: runtime incarnation mismatch")
            
            # Store lease
            self._leases[lease.invocation_id] = lease
            return True
    
    def consume(self, invocation_id: str) -> bool:
        """Mark a lease as consumed (single-use).
        
        Args:
            invocation_id: The invocation ID of the lease to consume
            
        Returns:
            True if consumption succeeded, False otherwise
        """
        with self._lock:
            if invocation_id not in self._leases:
                return False
            
            lease = self._leases[invocation_id]
            
            # Check if already consumed
            if lease.consumed:
                return False
            
            # Check if expired
            if lease.expires_at_utc and datetime.now(timezone.utc) > lease.expires_at_utc:
                return False
            
            # Check if stale
            from iabv_v15.services.evolution.runtime_identity_authority import RuntimeIdentityAuthority
            authority = RuntimeIdentityAuthority()
            current_incarnation = authority.get_incarnation()
            
            if lease.runtime_incarnation_hash != current_incarnation.incarnation_hash:
                return False
            
            # Mark as consumed
            # Note: InternalMcpInvocation is frozen, so we need to create a new instance
            from dataclasses import replace
            consumed_lease = replace(lease, consumed=True)
            self._leases[invocation_id] = consumed_lease
            
            return True
    
    def get(self, invocation_id: str) -> InternalMcpInvocation | None:
        """Get a lease by invocation ID.
        
        Args:
            invocation_id: The invocation ID of the lease to get
            
        Returns:
            The lease if found, None otherwise
        """
        with self._lock:
            return self._leases.get(invocation_id)
    
    def invalidate_stale(self) -> int:
        """Invalidate all leases with stale runtime incarnation.
        
        Returns:
            Number of leases invalidated
        """
        with self._lock:
            from iabv_v15.services.evolution.runtime_identity_authority import RuntimeIdentityAuthority
            authority = RuntimeIdentityAuthority()
            current_incarnation = authority.get_incarnation()
            
            stale_invocation_ids = [
                invocation_id
                for invocation_id, lease in self._leases.items()
                if lease.runtime_incarnation_hash != current_incarnation.incarnation_hash
            ]
            
            for invocation_id in stale_invocation_ids:
                del self._leases[invocation_id]
            
            return len(stale_invocation_ids)
    
    def cleanup_expired(self) -> int:
        """Clean up expired leases.
        
        Returns:
            Number of leases cleaned up
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_invocation_ids = [
                invocation_id
                for invocation_id, lease in self._leases.items()
                if lease.expires_at_utc and now > lease.expires_at_utc
            ]
            
            for invocation_id in expired_invocation_ids:
                del self._leases[invocation_id]
            
            return len(expired_invocation_ids)
    
    def count(self) -> int:
        """Get the number of active leases.
        
        Returns:
            Number of active leases
        """
        with self._lock:
            return len(self._leases)
