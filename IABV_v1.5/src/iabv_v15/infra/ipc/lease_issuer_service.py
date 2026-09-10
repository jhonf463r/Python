"""P0.213: LeaseIssuerService for InternalMcpInvocation lease issuance.

DESIGN_RECONSTRUCTION: This module is a new implementation reconstructed from
experimental design evidence. It is NOT recovered historical code.

Purpose: Issue InternalMcpInvocation leases to MCP child processes with
canonical identity resolution.

Contract Requirements:
- LeaseRegistry: responsible for storage and consumption tracking
- LeaseIssuerService: responsible for issuance and canonical identity resolution
- KEEP_SEPARATE: No consolidation of responsibilities
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone, timedelta
from typing import Any

from iabv_v15.domain.models import (
    InternalMcpInvocation,
    CanonicalExecutionIdentity,
    RunRecord,
    AdaptiveSession,
)
from iabv_v15.infra.ipc.lease_registry import LeaseRegistry


class LeaseIssuerService:
    """Service for issuing InternalMcpInvocation leases to MCP child processes.

    This class is responsible for:
    - Issuance of InternalMcpInvocation leases
    - Canonical identity resolution from RunRecord and AdaptiveSession
    - Producer scope validation
    - PID validation
    
    Contract Compliance:
    - Issuance and canonical identity resolution responsibility
    - Thread-safe operation
    - Separation from LeaseRegistry
    """
    _instance = None
    _lock = threading.Lock()
    _registry: LeaseRegistry = None
    
    def __new__(cls):
        """Singleton pattern for global service access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._registry = LeaseRegistry()
        return cls._instance
    
    def issue_lease(
        self,
        run_record: RunRecord,
        session: AdaptiveSession,
        producer_scope: str,
        ttl_seconds: int = 300,
    ) -> InternalMcpInvocation:
        """Issue a new InternalMcpInvocation lease.
        
        Args:
            run_record: Canonical RunRecord for identity derivation
            session: Canonical AdaptiveSession for identity derivation
            producer_scope: Producer scope for authorization
            ttl_seconds: Time-to-live for the lease (default: 300 seconds)
            
        Returns:
            The issued InternalMcpInvocation lease
            
        Raises:
            ValueError: If run_record.run_id is empty
        """
        # Resolve canonical identity
        canonical_identity = CanonicalExecutionIdentity(
            run_id=run_record.run_id,
            episode_id=getattr(run_record, 'episode_id', None),
            session_id=session.session_id,
        )
        
        # Get producer PID
        producer_pid = os.getpid()
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        
        # Create invocation lease
        invocation = InternalMcpInvocation(
            canonical_identity=canonical_identity,
            producer_pid=producer_pid,
            producer_scope=producer_scope,
            expires_at_utc=expires_at,
        )
        
        # Register in lease registry
        self._registry.register(invocation)
        
        return invocation
    
    def validate_lease(self, invocation: InternalMcpInvocation) -> bool:
        """Validate an invocation lease.
        
        Args:
            invocation: The InternalMcpInvocation to validate
            
        Returns:
            True if valid, False otherwise
        """
        return invocation.validate()
    
    def consume_lease(self, invocation_id: str) -> InternalMcpInvocation | None:
        """Consume an invocation lease.
        
        Args:
            invocation_id: The invocation_id to consume
            
        Returns:
            The consumed invocation, or None if not found or already consumed
        """
        return self._registry.consume(invocation_id)
    
    def get_lease(self, invocation_id: str) -> InternalMcpInvocation | None:
        """Get an invocation lease without consuming it.
        
        Args:
            invocation_id: The invocation_id to retrieve
            
        Returns:
            The invocation, or None if not found
        """
        return self._registry.get(invocation_id)
    
    def get_current_lease(self) -> InternalMcpInvocation | None:
        """Get the current (most recently issued) lease.
        
        Returns:
            The most recent lease, or None if no leases exist
        """
        return self._registry.get_current()
    
    def revoke_lease(self, invocation_id: str) -> bool:
        """Revoke an invocation lease.
        
        Args:
            invocation_id: The invocation_id to revoke
            
        Returns:
            True if revoked, False if not found
        """
        return self._registry.remove(invocation_id)
    
    def clear_leases(self) -> None:
        """Clear all leases from the registry.
        
        This is useful for testing or cleanup scenarios.
        """
        self._registry.clear()
