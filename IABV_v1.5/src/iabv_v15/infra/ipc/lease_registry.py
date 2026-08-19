"""P0.213: LeaseRegistry for InternalMcpInvocation lease storage and lifecycle.

DESIGN_RECONSTRUCTION: This module is a new implementation reconstructed from
experimental design evidence. It is NOT recovered historical code.

Purpose: Thread-safe storage and lifecycle management of InternalMcpInvocation leases
in the parent runtime.

Contract Requirements:
- LeaseRegistry: responsible for storage and consumption tracking
- LeaseIssuerService: responsible for issuance and canonical identity resolution
- KEEP_SEPARATE: No consolidation of responsibilities
"""
from __future__ import annotations

import threading
from typing import Any
from iabv_v15.domain.models import InternalMcpInvocation


class LeaseRegistry:
    """Thread-safe registry for InternalMcpInvocation leases.

    This class is responsible for:
    - Storage of InternalMcpInvocation leases
    - Consumption tracking (single-use enforcement)
    - Lease lifecycle management
    
    Contract Compliance:
    - Storage and consumption tracking responsibility
    - Thread-safe operation
    - Separation from LeaseIssuerService
    """
    _instance = None
    _lock = threading.Lock()
    _storage: dict[str, InternalMcpInvocation] = {}
    
    def __new__(cls):
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, invocation: InternalMcpInvocation) -> bool:
        """Register a new invocation lease.
        
        Args:
            invocation: The InternalMcpInvocation to register
            
        Returns:
            True if successfully registered, False if invocation_id already exists
        """
        with self._lock:
            if invocation.invocation_id in self._storage:
                return False
            self._storage[invocation.invocation_id] = invocation
            return True
    
    def consume(self, invocation_id: str) -> InternalMcpInvocation | None:
        """Consume an invocation lease (single-use).
        
        Args:
            invocation_id: The invocation_id to consume
            
        Returns:
            The consumed invocation, or None if not found or already consumed
        """
        with self._lock:
            invocation = self._storage.get(invocation_id)
            if invocation is None:
                return None
            
            if invocation.consume():
                return invocation
            return None
    
    def get(self, invocation_id: str) -> InternalMcpInvocation | None:
        """Get an invocation lease without consuming it.
        
        Args:
            invocation_id: The invocation_id to retrieve
            
        Returns:
            The invocation, or None if not found
        """
        with self._lock:
            return self._storage.get(invocation_id)
    
    def get_current(self) -> InternalMcpInvocation | None:
        """Get the current (most recently registered) invocation.
        
        Returns:
            The most recent invocation, or None if no invocations exist
        """
        with self._lock:
            if not self._storage:
                return None
            # Return the last registered invocation
            return list(self._storage.values())[-1]
    
    def clear(self) -> None:
        """Clear all invocations from the registry.
        
        This is useful for testing or cleanup scenarios.
        """
        with self._lock:
            self._storage.clear()
    
    def remove(self, invocation_id: str) -> bool:
        """Remove an invocation from the registry.
        
        Args:
            invocation_id: The invocation_id to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if invocation_id in self._storage:
                del self._storage[invocation_id]
                return True
            return False
    
    def size(self) -> int:
        """Get the number of invocations in the registry.
        
        Returns:
            The count of registered invocations
        """
        with self._lock:
            return len(self._storage)
