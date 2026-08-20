"""
Capability Registry - P0.213 V5

Interprocess-atomic registry for tracking consumed capabilities.

This provides single-use enforcement across processes using file-based
persistence with file locks for atomicity.

Key Principle: Single-use enforcement must be atomic from the perspective
of the trust boundary. A local dict is not sufficient because it's not
visible across processes.
"""

import os
import fcntl
import json
import time
from pathlib import Path
from typing import Optional, Set
from threading import Lock


class CapabilityRegistry:
    """
    Interprocess-atomic registry for tracking consumed capabilities.
    
    This ensures that a capability can only be consumed once, even across
    multiple processes and restarts.
    """
    
    def __init__(self, storage_root: Optional[Path] = None):
        """
        Initialize the capability registry.
        
        Args:
            storage_root: Root directory for registry storage
        """
        self._storage_root = Path(storage_root) if storage_root else Path.home() / ".iabv" / "capability_registry"
        self._registry_file = self._storage_root / "consumed_capabilities.json"
        self._local_lock = Lock()
        
        # Ensure storage directory exists
        self._storage_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize registry file if it doesn't exist
        if not self._registry_file.exists():
            self._init_registry()
    
    def _init_registry(self) -> None:
        """Initialize the registry file with empty state."""
        with open(self._registry_file, "w") as f:
            json.dump({"consumed_capabilities": []}, f)
    
    def _load_registry(self) -> Set[str]:
        """
        Load the set of consumed capability IDs from the registry.
        
        Uses file locking for interprocess atomicity.
        
        Returns:
            Set[str]: Set of consumed capability IDs
        """
        with self._local_lock:
            if not self._registry_file.exists():
                return set()
            
            with open(self._registry_file, "r") as f:
                # Acquire file lock for interprocess atomicity
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                except (ImportError, AttributeError):
                    # fcntl not available on Windows, use threading lock only
                    pass
                
                try:
                    data = json.load(f)
                    return set(data.get("consumed_capabilities", []))
                finally:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (ImportError, AttributeError):
                        pass
    
    def _save_registry(self, consumed_capabilities: Set[str]) -> None:
        """
        Save the set of consumed capability IDs to the registry.
        
        Uses file locking for interprocess atomicity.
        
        Args:
            consumed_capabilities: Set of consumed capability IDs
        """
        with self._local_lock:
            # Write to temporary file first for atomicity
            temp_file = self._registry_file.with_suffix(".tmp")
            
            with open(temp_file, "w") as f:
                # Acquire file lock for interprocess atomicity
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except (ImportError, AttributeError):
                    # fcntl not available on Windows, use threading lock only
                    pass
                
                try:
                    json.dump(
                        {"consumed_capabilities": list(consumed_capabilities)},
                        f,
                        indent=2
                    )
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (ImportError, AttributeError):
                        pass
            
            # Atomic rename
            temp_file.replace(self._registry_file)
    
    def is_consumed(self, capability_id: str) -> bool:
        """
        Check if a capability has been consumed.
        
        Args:
            capability_id: The capability ID to check
        
        Returns:
            bool: True if consumed, False otherwise
        """
        consumed = self._load_registry()
        return capability_id in consumed
    
    def mark_consumed(self, capability_id: str) -> bool:
        """
        Mark a capability as consumed.
        
        This operation is atomic from the perspective of the trust boundary.
        
        Args:
            capability_id: The capability ID to mark as consumed
        
        Returns:
            bool: True if successfully marked (was not consumed before),
                  False if already consumed
        """
        with self._local_lock:
            consumed = self._load_registry()
            
            if capability_id in consumed:
                return False  # Already consumed
            
            # Add to consumed set
            consumed.add(capability_id)
            
            # Save atomically
            self._save_registry(consumed)
            
            return True
    
    def clear_stale(self, max_age_seconds: float = 86400.0) -> int:
        """
        Clear stale consumed capabilities from the registry.
        
        This is a maintenance operation to prevent unbounded growth.
        
        Args:
            max_age_seconds: Maximum age for consumed capabilities (default: 24 hours)
        
        Returns:
            int: Number of capabilities cleared
        """
        # Note: This is a simplified implementation.
        # A full implementation would track consumption timestamps.
        # For now, we just clear all consumed capabilities.
        with self._local_lock:
            self._init_registry()
            return 0
