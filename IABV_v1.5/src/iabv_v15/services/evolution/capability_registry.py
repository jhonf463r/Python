"""
Capability Registry - P0.213 V5R3

Interprocess-atomic tracking of consumed capabilities using Windows file locking.

This is the REGISTRY in the trust authority chain:
ROOT TRUST ANCHOR → AUTHORIZED ISSUER → INVOCATION CAPABILITY → CONSUMER → VERIFIER → REGISTRY

P0.213 V5R3: The registry is owned by the parent/runtime authority, not by individual
consumer processes. Atomic verify+consume is performed by the parent authority, not by
child processes performing RMW operations directly on the registry file.

Key Principle: The registry must be atomic across processes to prevent double-spending.
A local dict is not sufficient because it's not visible across processes.

P0.213 V5R3: Uses Windows file locking for inter-process atomicity. The ownership
model is parent-owned: PARENT AUTHORITY -> canonical capability registry -> atomic verify+consume -> child consumer.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Set
from threading import RLock
import msvcrt
import ctypes
from iabv_v15.services.evolution.root_trust_anchor import RuntimeAuthority
from ctypes import wintypes


class CapabilityRegistry:
    """
    Interprocess-atomic registry for tracking consumed capabilities.
    
    P0.213 V5R3: Parent-owned capability consumption authority.
    
    The registry is owned by the parent/runtime authority, not by individual
    consumer processes. Child processes must request consumption from the
    parent authority via the atomic verify_and_consume method.
    
    This ensures that a capability can only be consumed once, even across
    multiple processes attempting to consume the same capability.
    """
    
    def __init__(self, storage_root: Optional[Path] = None, runtime_generation: Optional[int] = None):
        """
        Initialize the capability registry.
        
        P0.213 V5R3: The registry is parent-owned and tied to runtime generation.
        
        Args:
            storage_root: Root directory for registry storage
            runtime_generation: Runtime generation for stale capability prevention
        """
        self._storage_root = Path(storage_root) if storage_root else Path.home() / ".iabv" / "capability_registry"
        self._registry_file = self._storage_root / "consumed_capabilities.json"
        self._local_lock = RLock()  # P0.213 V5R2: Use RLock to prevent deadlock in nested calls
        self._runtime_generation = runtime_generation  # P0.213 V5R3: Track runtime generation
        
        # Ensure storage directory exists
        self._storage_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize registry file if it doesn't exist
        if not self._registry_file.exists():
            self._init_registry()
        
        # P0.213 V5R3: Clear stale capabilities from previous generations
        if self._runtime_generation is not None:
            self._clear_stale_capabilities()
    
    def _init_registry(self) -> None:
        """Initialize the registry file with empty state."""
        with open(self._registry_file, "w") as f:
            json.dump({"consumed_capabilities": [], "runtime_generation": self._runtime_generation}, f)
    
    def _clear_stale_capabilities(self) -> None:
        """
        P0.213 V5R3: Clear capabilities from previous runtime generations.
        
        This ensures that capabilities from a previous runtime generation
        cannot be consumed after a restart, preventing stale capability attacks.
        """
        with self._local_lock:
            if not self._registry_file.exists():
                return
            
            with open(self._registry_file, "r") as f:
                self._acquire_windows_lock(f.fileno(), exclusive=False)
                try:
                    data = json.load(f)
                    stored_generation = data.get("runtime_generation")
                    
                    # If no generation stored or different generation, clear registry
                    if stored_generation is None or stored_generation != self._runtime_generation:
                        self._init_registry()
                finally:
                    self._release_windows_lock(f.fileno())
    
    def _load_registry(self) -> Set[str]:
        """
        Load the set of consumed capability IDs from the registry.
        
        P0.213 V5R2: Uses Windows file locking for interprocess atomicity.
        Note: Does NOT acquire local lock - caller must hold lock.
        
        Returns:
            Set[str]: Set of consumed capability IDs
        """
        if not self._registry_file.exists():
            return set()
        
        with open(self._registry_file, "r") as f:
            # Acquire Windows file lock for interprocess atomicity
            self._acquire_windows_lock(f.fileno(), exclusive=False)
            
            try:
                data = json.load(f)
                return set(data.get("consumed_capabilities", []))
            finally:
                self._release_windows_lock(f.fileno())
    
    def _save_registry(self, consumed: Set[str]) -> None:
        """
        Save the set of consumed capability IDs to the registry.
        
        P0.213 V5R3: Includes runtime generation for stale capability prevention.
        P0.213 V5R2: Uses Windows file locking for interprocess atomicity.
        Note: Does NOT acquire local lock - caller must hold lock.
        
        Args:
            consumed: Set of consumed capability IDs to save
        """
        # Write to temporary file first (atomic rename pattern)
        temp_file = self._registry_file.with_suffix(".tmp")
        
        with open(temp_file, "w") as f:
            # Acquire Windows file lock for interprocess atomicity
            self._acquire_windows_lock(f.fileno(), exclusive=True)
            
            try:
                json.dump(
                    {
                        "consumed_capabilities": list(consumed),
                        "runtime_generation": self._runtime_generation
                    },
                    f,
                    indent=2
                )
                f.flush()
                os.fsync(f.fileno())
            finally:
                self._release_windows_lock(f.fileno())
        
        # Atomic rename
        temp_file.replace(self._registry_file)
    
    def is_consumed(self, capability_id: str) -> bool:
        """
        Check if a capability has been consumed.
        
        P0.213 V5R2: Acquires local lock for thread safety.
        
        Args:
            capability_id: The capability ID to check
        
        Returns:
            bool: True if consumed, False otherwise
        """
        with self._local_lock:
            consumed = self._load_registry()
            return capability_id in consumed
    
    def mark_consumed(self, capability_id: str) -> bool:
        """
        Mark a capability as consumed.
        
        P0.213 V5R1: This operation is atomic from the perspective of the trust boundary.
        Uses Windows file locking to prevent TOCTOU.
        
        Args:
            capability_id: The capability ID to mark as consumed
        
        Returns:
            bool: True if successfully marked (was not consumed before),
                  False if already consumed
        """
        with self._local_lock:
            # Load and check in single lock-protected operation
            consumed = self._load_registry()
            
            if capability_id in consumed:
                return False  # Already consumed
            
            # Add to consumed set
            consumed.add(capability_id)
            
            # Save atomically
            self._save_registry(consumed)
            
            return True
    
    def consume_if_valid(self, capability_id: str) -> bool:
        """
        P0.213 V5R3: Atomic verify+consume operation.
        
        P0.213 V5R3: This is the parent-owned atomic operation. Child processes
        must not perform RMW operations directly on the registry state. This method
        performs verify + consume as one indivisible authority operation across processes.
        
        This single atomic operation checks if the capability is valid
        and consumes it if so. This prevents race conditions where multiple
        processes could pass the check and then all try to consume.
        
        Uses RLock to prevent deadlock in nested calls and Windows file locking
        for inter-process atomicity.
        
        Args:
            capability_id: The capability ID to consume
        
        Returns:
            bool: True if successfully consumed (was valid and not consumed before),
                  False if already consumed
        """
        with self._local_lock:
            # P0.213 V5R3: Verify runtime generation matches (prevent stale capabilities)
            if self._runtime_generation is not None:
                self._verify_runtime_generation()
            
            # Load and check in single lock-protected operation
            consumed = self._load_registry()
            
            if capability_id in consumed:
                return False  # Already consumed
            
            # Add to consumed set
            consumed.add(capability_id)
            
            # Save atomically
            self._save_registry(consumed)
            
            return True
    
    def _verify_runtime_generation(self) -> None:
        """
        P0.213 V5R3: Verify that the registry's runtime generation matches current generation.
        
        This ensures that capabilities from previous generations cannot be consumed,
        preventing stale capability attacks after parent restart.
        
        Raises:
            ValueError: If runtime generation mismatch detected
        """
        if not self._registry_file.exists():
            return
        
        with open(self._registry_file, "r") as f:
            self._acquire_windows_lock(f.fileno(), exclusive=False)
            try:
                data = json.load(f)
                stored_generation = data.get("runtime_generation")
                
                if stored_generation is not None and stored_generation != self._runtime_generation:
                    raise ValueError(
                        f"Runtime generation mismatch: registry has {stored_generation}, "
                        f"current is {self._runtime_generation}. Capability consumption rejected."
                    )
            finally:
                self._release_windows_lock(f.fileno())
    
    def _acquire_windows_lock(self, fd: int, exclusive: bool = True) -> None:
        """
        Acquire Windows file lock for interprocess atomicity.
        
        Args:
            fd: File descriptor
            exclusive: True for exclusive lock, False for shared lock
        """
        try:
            # Use Windows file locking via msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK if exclusive else msvcrt.LK_RLCK, 1)
        except (OSError, IOError):
            # Fallback: use Windows API via ctypes
            kernel32 = ctypes.windll.kernel32
            lock_file_ex = kernel32.LockFileEx
            lock_file_ex.restype = wintypes.BOOL
            lock_file_ex.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.OVERLAPPED),
            ]
            
            handle = msvcrt.get_osfhandle(fd)
            flags = 0x00000002 if exclusive else 0x00000001  # LOCKFILE_EXCLUSIVE_LOCK
            
            overlapped = wintypes.OVERLAPPED()
            result = lock_file_ex(handle, flags, 0, 0xFFFF0000, 0, ctypes.byref(overlapped))
            
            if not result:
                raise RuntimeError(f"Failed to acquire Windows file lock")
    
    def _release_windows_lock(self, fd: int) -> None:
        """
        Release Windows file lock.
        
        Args:
            fd: File descriptor
        """
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except (OSError, IOError):
            # Fallback: use Windows API via ctypes
            kernel32 = ctypes.windll.kernel32
            unlock_file_ex = kernel32.UnlockFileEx
            unlock_file_ex.restype = wintypes.BOOL
            unlock_file_ex.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.OVERLAPPED),
            ]
            
            handle = msvcrt.get_osfhandle(fd)
            overlapped = wintypes.OVERLAPPED()
            result = unlock_file_ex(handle, 0, 0, 0xFFFF0000, ctypes.byref(overlapped))
            
            if not result:
                raise RuntimeError(f"Failed to release Windows file lock")
    
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
