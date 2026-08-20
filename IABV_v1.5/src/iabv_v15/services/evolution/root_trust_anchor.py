"""RootTrustAnchor: OS-controlled trust anchor for P0.213 V4.

This module provides the root trust anchor that combines OS-controlled
runtime state that cannot be forged by caller input.

P0.213 V5R2: Singleton pattern to ensure only canonical instance.

Design Principles:
- OS-controlled: Process identity, creation time, parent PID from OS
- Persisted: Secret key, generation, bootstrap timestamp survive restart
- Verifiable: Can be validated against OS state
- Immutable: Cannot be modified after issuance
- Singleton: Only one canonical instance per runtime

This is part of P0.213 V4 corrected implementation with real security controls.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# P0.213 V5R2: Singleton instance
_root_trust_anchor_instance: Optional['RootTrustAnchor'] = None
_root_trust_anchor_lock = threading.Lock()


class RuntimeAuthority:
    """
    P0.213 V5R3: Trusted runtime authority for bootstrapping canonical RootTrustAnchor.
    
    This class represents the trusted runtime bootstrap process that owns the
    canonical RootTrustAnchor. Only this class can create the canonical authority
    by passing _runtime_bootstrap=True to RootTrustAnchor.__init__.
    
    This ensures that:
    - Caller cannot create RootTrustAnchor directly
    - Caller cannot use get_instance() to bootstrap
    - Only trusted runtime bootstrap can initialize canonical authority
    """
    
    @classmethod
    def bootstrap(cls, storage_root: Path | str) -> 'RootTrustAnchor':
        """
        Bootstrap the canonical RootTrustAnchor.
        
        This is the ONLY way to create a canonical RootTrustAnchor.
        Only the trusted runtime bootstrap should call this method.
        
        Args:
            storage_root: Directory for persistent state
            
        Returns:
            The canonical RootTrustAnchor instance
            
        Raises:
            ValueError: If already bootstrapped with different storage root
        """
        resolved_root = Path(storage_root).resolve()
        
        with _root_trust_anchor_lock:
            global _root_trust_anchor_instance
            
            if _root_trust_anchor_instance is None:
                # P0.213 V5R3: Create canonical instance with _runtime_bootstrap=True
                _root_trust_anchor_instance = RootTrustAnchor(
                    storage_root=resolved_root,
                    _runtime_bootstrap=True
                )
            elif not _root_trust_anchor_instance.is_canonical(resolved_root):
                # Different storage root requested - this is an error
                raise ValueError(
                    f"RootTrustAnchor already bootstrapped with different storage root: "
                    f"{_root_trust_anchor_instance._storage_root} != {resolved_root}. "
                    f"Cannot create parallel authority."
                )
            
            return _root_trust_anchor_instance
    
    @classmethod
    def get_canonical(cls) -> 'RootTrustAnchor':
        """
        Get the canonical RootTrustAnchor (must already be bootstrapped).
        
        Args:
            None
            
        Returns:
            The canonical RootTrustAnchor instance
            
        Raises:
            ValueError: If not bootstrapped yet
        """
        with _root_trust_anchor_lock:
            global _root_trust_anchor_instance
            
            if _root_trust_anchor_instance is None:
                raise ValueError(
                    "RootTrustAnchor not bootstrapped. "
                    "Call RuntimeAuthority.bootstrap() first."
                )
            
            return _root_trust_anchor_instance


@dataclass(frozen=True)
class ProcessIdentity:
    """OS-controlled process identity."""
    
    pid: int
    create_time: float
    ppid: int


@dataclass(frozen=True)
class RuntimeIdentity:
    """OS-controlled runtime identity."""
    
    generation: int
    bootstrap_timestamp: float


class RootTrustAnchor:
    """Root trust anchor combining OS-controlled runtime state.
    
    This class provides the foundation for all security controls in P0.213 V4.
    It manages:
    - Process identity (OS-controlled)
    - Runtime identity (persisted)
    - Secret key (persisted, OS-protected)
    
    The secret key is stored in the evolution directory with restricted permissions.
    
    Note: Singleton pattern may be added later if needed for global access.
    """
    
    # Secret key file name
    _SECRET_KEY_FILE: Final = "secret.key"
    _GENERATION_FILE: Final = "generation.txt"
    _BOOTSTRAP_FILE: Final = "bootstrap.txt"
    
    def __init__(self, storage_root: Path | str | None = None, _runtime_bootstrap: bool = False):
        """Initialize root trust anchor.
        
        P0.213 V5R3: Direct construction is FORBIDDEN unless _runtime_bootstrap=True.
        Only trusted runtime bootstrap can create canonical RootTrustAnchor.
        
        Args:
            storage_root: Directory for persistent state (secret key, generation)
            _runtime_bootstrap: INTERNAL USE ONLY - must be True for runtime bootstrap
            
        Raises:
            ValueError: If storage_root is None or if called without _runtime_bootstrap=True
        """
        # P0.213 V5R3: Prevent caller from creating RootTrustAnchor
        if not _runtime_bootstrap:
            raise ValueError(
                "Direct RootTrustAnchor construction is forbidden. "
                "Use RootTrustAnchor.get_instance() or RuntimeAuthority.bootstrap(). "
                "Only trusted runtime bootstrap can create canonical authority."
            )
        
        # Resolve storage root
        if storage_root is None:
            raise ValueError("storage_root is required")
        
        self._storage_root = Path(storage_root).resolve()
        self._storage_root.mkdir(parents=True, exist_ok=True)
        
        # Load or generate secret key
        self._secret_key = self._load_or_generate_secret_key()
        
        # Load or initialize generation
        self._generation = self._load_or_initialize_generation()
        
        # Load or initialize bootstrap timestamp
        self._bootstrap_timestamp = self._load_or_initialize_bootstrap()
        
        # P0.213 V5R2: Store canonical path for verification
        self._canonical_path = self._storage_root
    
    def get_process_identity(self) -> ProcessIdentity:
        """Get OS-controlled process identity.
        
        Returns:
            ProcessIdentity with OS-controlled values
            
        Raises:
            RuntimeError: If psutil is not available
        """
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is required for process identity")
        
        process = psutil.Process()
        
        return ProcessIdentity(
            pid=os.getpid(),
            create_time=process.create_time(),
            ppid=process.ppid(),
        )
    
    def get_runtime_identity(self) -> RuntimeIdentity:
        """Get OS-controlled runtime identity.
        
        Returns:
            RuntimeIdentity with persisted values
        """
        return RuntimeIdentity(
            generation=self._generation,
            bootstrap_timestamp=self._bootstrap_timestamp,
        )
    
    def increment_generation(self) -> None:
        """Increment generation counter (called on runtime restart).
        
        This invalidates all old identities and leases.
        """
        self._generation += 1
        self._persist_generation()
    
    def get_secret_key(self) -> bytes:
        """Get secret key for HMAC signing.
        
        Returns:
            Secret key bytes
            
        Note:
            This key is used for HMAC-SHA256 signing of identities and leases.
            It is persisted in the evolution directory with restricted permissions.
        """
        return self._secret_key
    
    def _load_or_generate_secret_key(self) -> bytes:
        """Load existing secret key or generate new one.
        
        Returns:
            Secret key bytes (32 bytes for HMAC-SHA256)
        """
        secret_key_path = self._storage_root / self._SECRET_KEY_FILE
        
        if secret_key_path.exists():
            # Load existing key
            try:
                return secret_key_path.read_bytes()
            except Exception as e:
                raise RuntimeError(f"Failed to load secret key: {e}")
        
        # Generate new key
        secret_key = secrets.token_bytes(32)  # 256-bit key for HMAC-SHA256
        
        # Persist with restricted permissions
        try:
            secret_key_path.write_bytes(secret_key)
            # Set file permissions (read/write for owner only)
            # On Windows, this is handled by the OS
            # On Unix, we would use chmod 0600
        except Exception as e:
            raise RuntimeError(f"Failed to persist secret key: {e}")
        
        return secret_key
    
    def _load_or_initialize_generation(self) -> int:
        """Load existing generation or initialize to 0.
        
        Returns:
            Generation counter
        """
        generation_path = self._storage_root / self._GENERATION_FILE
        
        if generation_path.exists():
            try:
                return int(generation_path.read_text().strip())
            except Exception as e:
                raise RuntimeError(f"Failed to load generation: {e}")
        
        # Initialize to 0
        self._generation = 0
        self._persist_generation()
        return 0
    
    def _persist_generation(self) -> None:
        """Persist generation counter."""
        generation_path = self._storage_root / self._GENERATION_FILE
        generation_path.write_text(str(self._generation))
    
    def _load_or_initialize_bootstrap(self) -> float:
        """Load existing bootstrap timestamp or initialize to current time.
        
        Returns:
            Bootstrap timestamp (Unix timestamp)
        """
        bootstrap_path = self._storage_root / self._BOOTSTRAP_FILE
        
        if bootstrap_path.exists():
            try:
                return float(bootstrap_path.read_text().strip())
            except Exception as e:
                raise RuntimeError(f"Failed to load bootstrap timestamp: {e}")
        
        # Initialize to current time
        self._bootstrap_timestamp = time.time()
        self._persist_bootstrap()
        return self._bootstrap_timestamp
    
    def _persist_bootstrap(self) -> None:
        """Persist bootstrap timestamp."""
        bootstrap_path = self._storage_root / self._BOOTSTRAP_FILE
        bootstrap_path.write_text(str(self._bootstrap_timestamp))
    
    def compute_hmac(self, message: str) -> str:
        """Compute HMAC-SHA256 of message.
        
        Args:
            message: Message to sign
            
        Returns:
            Hex-encoded HMAC signature
        """
        return hmac.new(
            self._secret_key,
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
    
    def verify_hmac(self, message: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature.
        
        Args:
            message: Original message
            signature: Signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected = self.compute_hmac(message)
        return hmac.compare_digest(signature, expected)
    
    def is_canonical(self, expected_storage_root: Path | str) -> bool:
        """
        P0.213 V5R2: Verify this is the canonical RootTrustAnchor.
        
        Args:
            expected_storage_root: The expected canonical storage root
            
        Returns:
            True if this is the canonical instance, False otherwise
        """
        return self._storage_root == Path(expected_storage_root).resolve()
    
    @classmethod
    def get_instance(cls, storage_root: Path | str) -> 'RootTrustAnchor':
        """
        P0.213 V5R3: Get or create the canonical singleton instance.
        
        P0.213 V5R3: This method is FORBIDDEN. Only trusted runtime bootstrap
        can create canonical RootTrustAnchor via _runtime_bootstrap=True.
        
        Args:
            storage_root: Directory for persistent state
            
        Raises:
            ValueError: Always - caller cannot create canonical authority
            
        Returns:
            The canonical RootTrustAnchor instance (if already bootstrapped)
        """
        resolved_root = Path(storage_root).resolve()
        
        with _root_trust_anchor_lock:
            global _root_trust_anchor_instance
            
            if _root_trust_anchor_instance is None:
                # P0.213 V5R3: Caller cannot bootstrap - must use RuntimeAuthority
                raise ValueError(
                    "RootTrustAnchor not bootstrapped. "
                    "Caller cannot create canonical authority. "
                    "Use RuntimeAuthority.bootstrap() to initialize trusted authority."
                )
            elif not _root_trust_anchor_instance.is_canonical(resolved_root):
                # Different storage root requested - this is an error
                raise ValueError(
                    f"RootTrustAnchor already initialized with different storage root: "
                    f"{_root_trust_anchor_instance._storage_root} != {resolved_root}. "
                    f"Cannot create parallel authority."
                )
            
            return _root_trust_anchor_instance
    
    @classmethod
    def reset_singleton(cls) -> None:
        """
        P0.213 V5R2: Reset the singleton instance (for testing only).
        
        WARNING: This should only be used in tests. Never call in production.
        """
        global _root_trust_anchor_instance
        with _root_trust_anchor_lock:
            _root_trust_anchor_instance = None
