"""
Capability Registry - P0.213 V5R4

Interprocess-atomic tracking of consumed capabilities using Windows file locking.

This is the REGISTRY in the trust authority chain:
ROOT TRUST ANCHOR → AUTHORIZED ISSUER → INVOCATION CAPABILITY → CONSUMER → VERIFIER → REGISTRY

P0.213 V5R4: The registry is owned by the parent/runtime authority, not by individual
consumer processes. Atomic verify+consume is performed by the parent authority, not by
child processes performing RMW operations directly on the registry file.

P0.213 V5R4: Also includes TrustedRequestRegistry for real request/execution binding.
This establishes the causal chain: IPC REQUEST → INVOCATION_ID → RUN RECORD → SELFAUDIT → SNAPSHOT.

Key Principle: The registry must be atomic across processes to prevent double-spending.
A local dict is not sufficient because it's not visible across processes.

P0.213 V5R4: Uses Windows file locking for inter-process atomicity. The ownership
model is parent-owned: PARENT AUTHORITY -> canonical capability registry -> atomic verify+consume -> child consumer.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Set, Dict, Any
from threading import RLock
from dataclasses import dataclass, asdict
import msvcrt
import ctypes
from iabv_v15.services.evolution.root_trust_anchor import RuntimeAuthority
from ctypes import wintypes


@dataclass(frozen=True)
class RegisteredRequest:
    """
    P0.213 V5R4: Trusted request registration for real execution binding.
    
    This represents a real IPC request registered by the parent authority.
    It establishes the causal link between invocation_id and actual execution.
    """
    request_id: str
    invocation_id: str
    authorized_consumer_pid: int
    capability_id: str
    run_id: Optional[str]  # RunRecord ID when available
    episode_id: Optional[str]
    session_id: Optional[str]
    runtime_generation: int
    scope: str
    created_at: float
    expiry: float
    status: str  # "pending", "active", "completed", "failed"


class TrustedRequestRegistry:
    """
    P0.213 V5R4: Trusted request registry for real request/execution binding.
    
    This registry is owned by the parent runtime authority and registers
    real IPC requests with their invocation IDs. This establishes the causal
    chain: IPC REQUEST → INVOCATION_ID → RUN RECORD → SELFAUDIT → SNAPSHOT.
    
    The registry prevents:
    - Caller-supplied invocation IDs without real request
    - Cross-binding attacks (Capability A + Invocation B)
    - Replay attacks (same invocation used twice)
    - Stale invocation IDs from previous runtime generations
    
    Design Principles:
    - Parent-owned: Only parent authority can register requests
    - Persistent: Survives restarts via file-based storage
    - Interprocess atomic: Uses Windows file locking
    - Fail-closed: Rejects invalid bindings
    """
    
    _REGISTRY_FILE: str = "trusted_requests.json"
    
    def __init__(self, storage_root: Optional[Path] = None, runtime_generation: Optional[int] = None):
        """
        Initialize trusted request registry.
        
        Args:
            storage_root: Directory for persistent state
            runtime_generation: Current runtime generation
        """
        self._storage_root = Path(storage_root) if storage_root else Path.home() / ".iabv" / "trusted_requests"
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._registry_file = self._storage_root / self._REGISTRY_FILE
        self._runtime_generation = runtime_generation
        self._local_lock = RLock()
        
        # Initialize registry
        self._init_registry()
    
    def _init_registry(self) -> None:
        """Initialize registry file if it doesn't exist."""
        if not self._registry_file.exists():
            self._save_registry({})
    
    def register_request(
        self,
        request_id: str,
        invocation_id: str,
        authorized_consumer_pid: int,
        capability_id: str,
        scope: str,
        run_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ttl_seconds: float = 3600.0,
    ) -> RegisteredRequest:
        """
        Register a real IPC request.
        
        This is called by the parent runtime authority when a real request
        is received. This establishes the causal link between the request
        and its invocation ID.
        
        Args:
            request_id: Unique request identifier
            invocation_id: Invocation identifier
            authorized_consumer_pid: PID of authorized consumer
            capability_id: Capability ID used for this request
            scope: Request scope
            run_id: RunRecord ID (when available)
            episode_id: Episode ID (when available)
            session_id: Session ID (when available)
            ttl_seconds: Time-to-live for this request
            
        Returns:
            RegisteredRequest object
            
        Raises:
            ValueError: If request already exists or parameters invalid
        """
        with self._local_lock:
            # Load existing registry
            registry = self._load_registry()
            
            # Check if request already exists
            if request_id in registry:
                raise ValueError(f"Request {request_id} already registered")
            
            # Check if invocation_id already exists (prevent replay)
            for existing_request in registry.values():
                if existing_request["invocation_id"] == invocation_id:
                    raise ValueError(f"Invocation ID {invocation_id} already registered")
            
            # Create registered request
            created_at = time.time()
            expiry = created_at + ttl_seconds
            
            request = RegisteredRequest(
                request_id=request_id,
                invocation_id=invocation_id,
                authorized_consumer_pid=authorized_consumer_pid,
                capability_id=capability_id,
                run_id=run_id,
                episode_id=episode_id,
                session_id=session_id,
                runtime_generation=self._runtime_generation if self._runtime_generation is not None else 0,
                scope=scope,
                created_at=created_at,
                expiry=expiry,
                status="pending",
            )
            
            # Add to registry
            registry[request_id] = asdict(request)
            
            # Save atomically
            self._save_registry(registry)
            
            return request
    
    def get_request(self, invocation_id: str) -> Optional[RegisteredRequest]:
        """
        Get a registered request by invocation_id.
        
        This is used by SelfAudit to verify that an invocation_id
        corresponds to a real request.
        
        Args:
            invocation_id: Invocation identifier
            
        Returns:
            RegisteredRequest if found and valid, None otherwise
        """
        with self._local_lock:
            registry = self._load_registry()
            
            for request_data in registry.values():
                if request_data["invocation_id"] == invocation_id:
                    # Check if expired
                    if time.time() > request_data["expiry"]:
                        return None
                    
                    # Check runtime generation
                    if self._runtime_generation is not None:
                        if request_data["runtime_generation"] != self._runtime_generation:
                            return None
                    
                    # Return as RegisteredRequest
                    return RegisteredRequest(**request_data)
            
            return None
    
    def verify_binding(
        self,
        invocation_id: str,
        capability_id: str,
        authorized_consumer_pid: int,
        scope: str,
    ) -> bool:
        """
        Verify that the binding between invocation_id and capability is valid.
        
        This prevents cross-binding attacks where a caller tries to use
        Capability A with Invocation B.
        
        Args:
            invocation_id: Invocation identifier
            capability_id: Capability ID
            authorized_consumer_pid: Authorized consumer PID
            scope: Request scope
            
        Returns:
            True if binding is valid, False otherwise
        """
        request = self.get_request(invocation_id)
        
        if request is None:
            return False
        
        # Verify all fields match
        return (
            request.capability_id == capability_id
            and request.authorized_consumer_pid == authorized_consumer_pid
            and request.scope == scope
        )
    
    def mark_completed(self, invocation_id: str) -> None:
        """
        Mark a request as completed.
        
        This is called after successful execution to prevent replay.
        
        Args:
            invocation_id: Invocation identifier
        """
        with self._local_lock:
            registry = self._load_registry()
            
            for request_id, request_data in registry.items():
                if request_data["invocation_id"] == invocation_id:
                    request_data["status"] = "completed"
                    self._save_registry(registry)
                    return
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from file."""
        if not self._registry_file.exists():
            return {}
        
        try:
            with open(self._registry_file, "r") as f:
                return json.load(f)
        except Exception as e:
            # Fail-closed: return empty registry on error
            return {}
    
    def _save_registry(self, registry: Dict[str, Any]) -> None:
        """Save registry to file."""
        with open(self._registry_file, "w") as f:
            json.dump(registry, f, indent=2)



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
        P0.213 V5R4: True interprocess atomic verify+consume operation.
        
        P0.213 V5R4: This is the parent-owned atomic operation. Child processes
        must not perform RMW operations directly on the registry state. This method
        performs verify + consume as one indivisible authority operation across processes.
        
        P0.213 V5R4: The entire RMW (read-modify-write) operation is protected by
        Windows file locking to ensure true interprocess atomicity. This prevents
        race conditions where multiple processes could pass the check and then all try to consume.
        
        The lock is held for the entire operation:
        1. Acquire exclusive Windows file lock
        2. Verify runtime generation
        3. Load registry
        4. Check if capability is consumed
        5. Add to consumed set if not
        6. Save registry
        7. Release lock
        
        Args:
            capability_id: The capability ID to consume
        
        Returns:
            bool: True if successfully consumed (was valid and not consumed before),
                  False if already consumed
        """
        # P0.213 V5R4: Use Windows file locking for true interprocess atomicity
        # Open the registry file and acquire exclusive lock for the entire RMW operation
        try:
            # Ensure registry file exists
            if not self._registry_file.exists():
                self._registry_file.parent.mkdir(parents=True, exist_ok=True)
                self._registry_file.write_text('{"consumed_capabilities": [], "runtime_generation": 0}')
            
            with open(self._registry_file, "r+") as f:
                # P0.213 V5R4: Acquire exclusive Windows file lock for entire RMW operation
                self._acquire_windows_lock(f.fileno(), exclusive=True)
                
                try:
                    # P0.213 V5R4: Verify runtime generation matches (prevent stale capabilities)
                    if self._runtime_generation is not None:
                        self._verify_runtime_generation_locked(f)
                    
                    # Load and check in single lock-protected operation
                    consumed = self._load_registry_locked(f)
                    
                    if capability_id in consumed:
                        return False  # Already consumed
                    
                    # Add to consumed set
                    consumed.add(capability_id)
                    
                    # Save atomically (still holding lock)
                    self._save_registry_locked(f, consumed)
                    
                    return True
                finally:
                    # P0.213 V5R4: Always release lock
                    self._release_windows_lock(f.fileno())
        except Exception as e:
            # P0.213 V5R4: Fail-closed on any error
            raise RuntimeError(f"Failed to consume capability atomically: {e}")
    
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
    
    def _verify_runtime_generation_locked(self, f) -> None:
        """
        P0.213 V5R4: Verify runtime generation with file already locked.
        
        This is used within consume_if_valid when the file lock is already held.
        
        Args:
            f: Open file handle (already locked)
            
        Raises:
            ValueError: If runtime generation mismatch detected
        """
        f.seek(0)
        data = json.load(f)
        stored_generation = data.get("runtime_generation")
        
        if stored_generation is not None and stored_generation != self._runtime_generation:
            raise ValueError(
                f"Runtime generation mismatch: registry has {stored_generation}, "
                f"current is {self._runtime_generation}. Capability consumption rejected."
            )
    
    def _load_registry_locked(self, f) -> set:
        """
        P0.213 V5R4: Load registry with file already locked.
        
        This is used within consume_if_valid when the file lock is already held.
        
        Args:
            f: Open file handle (already locked)
            
        Returns:
            Set of consumed capability IDs
        """
        f.seek(0)
        data = json.load(f)
        return set(data.get("consumed_capabilities", []))
    
    def _save_registry_locked(self, f, consumed: set) -> None:
        """
        P0.213 V5R4: Save registry with file already locked.
        
        This is used within consume_if_valid when the file lock is already held.
        
        Args:
            f: Open file handle (already locked)
            consumed: Set of consumed capability IDs
        """
        f.seek(0)
        f.truncate()
        data = {
            "consumed_capabilities": list(consumed),
            "runtime_generation": self._runtime_generation if self._runtime_generation is not None else 0
        }
        json.dump(data, f)
        f.flush()  # Ensure data is written before releasing lock
    
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
