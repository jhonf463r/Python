"""RootTrustAnchor: Data contract for OS-controlled trust anchor (P0.213 V5).

CRITICAL: This is a DATA CONTRACT, NOT a security boundary.

In-process Python objects cannot be security boundaries because any caller
can import and invoke public constructors. The real security boundary will be
implemented in Phase 2 using a separate trusted authority process and OS/IPC
enforcement.

This module defines the DATA MODEL for:
- Process identity (OS-observed in Phase 2)
- Runtime identity (persisted in Phase 2)
- Secret key requirements (OS-protected in Phase 2)
- Generation requirements (persisted in Phase 2)

Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)

SECURITY WARNING:
- DO NOT treat this Python object as a security boundary
- DO NOT rely on constructor restrictions for security
- DO NOT assume in-process immutability provides authenticity
- Phase 2 will implement the real authority boundary
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional


@dataclass(frozen=True)
class ProcessIdentity:
    """Data contract for OS-controlled process identity.
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    Phase 2: Obtained from OS via psutil/Windows API in trusted authority process
    Phase 1: Data structure defined for contract specification
    
    SECURITY WARNING:
    - Caller-constructed instances are NOT authoritative
    - Phase 2 will enforce OS-derived values in trusted authority process
    - This is a data model, not an authority
    """
    
    pid: int
    create_time: float
    ppid: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.
        
        IMMUTABILITY: This is a serialization operation, NOT mutation.
        """
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class RuntimeIdentity:
    """Data contract for OS-controlled runtime identity.
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    Phase 2: Loaded from persistent storage in trusted authority process
    Phase 1: Data structure defined for contract specification
    
    SECURITY WARNING:
    - Caller-constructed instances are NOT authoritative
    - Phase 2 will enforce persisted values in trusted authority process
    """
    
    generation: int
    bootstrap_timestamp: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.
        
        IMMUTABILITY: This is a serialization operation, NOT mutation.
        """
        return dataclasses.asdict(self)


class RootTrustAnchor:
    """Data contract for root trust anchor (NON-AUTHORITATIVE).
    
    CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
    
    In-process Python objects cannot be security boundaries. Any caller can
    import and construct this class. The real security boundary will be
    implemented in Phase 2 using a separate trusted authority process.
    
    This class defines the DATA MODEL for:
    - Process identity (OS-observed in Phase 2)
    - Runtime identity (persisted in Phase 2)
    - Secret key requirements (OS-protected in Phase 2)
    - Generation requirements (persisted in Phase 2)
    
    AUTHORITY CONTRACT:
    - Phase 2: Trusted authority process owns the real secret key
    - Phase 2: Trusted authority process owns generation state
    - Phase 2: Trusted authority process enforces OS-derived identity
    - Phase 1: This is a non-authoritative data model for contract specification
    
    SECURITY WARNING:
    - DO NOT treat this Python object as a security boundary
    - DO NOT rely on constructor restrictions for security
    - DO NOT assume in-process immutability provides authenticity
    - Phase 2 will implement the real authority boundary
    
    Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
    Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
    """
    
    def __init__(self, storage_root: Path | str):
        """Initialize root trust anchor data contract.
        
        CRITICAL: This is a DATA CONTRACT, NOT a security boundary.
        Any caller can construct this instance. The real security boundary
        will be implemented in Phase 2 using a separate trusted authority process.
        
        Args:
            storage_root: Directory for persistent state (Phase 2: OS-protected)
        """
        # Resolve storage root
        self._storage_root = Path(storage_root).resolve()
        self._storage_root.mkdir(parents=True, exist_ok=True)
        
        # Phase 1: Placeholder values for data representation (NOT secret material)
        # Phase 2: Trusted authority process will manage real secret key
        self._secret_key = None
        self._generation = 0
        self._bootstrap_timestamp = 0.0
    
    def get_process_identity(self) -> ProcessIdentity:
        """Get process identity data contract.
        
        CRITICAL: This returns a DATA CONTRACT, NOT authoritative identity.
        Phase 2: Trusted authority process will return OS-observed values.
        Phase 1: Returns placeholder for data contract specification.
        
        SECURITY WARNING:
        - Caller-constructed instances are NOT authoritative
        - Phase 2 will enforce OS-derived values in trusted authority process
        
        Returns:
            ProcessIdentity data contract (non-authoritative)
        """
        # Phase 1: Placeholder for data contract specification
        # Phase 2: Trusted authority process will return OS-observed values
        return ProcessIdentity(pid=0, create_time=0.0, ppid=0)
    
    def get_runtime_identity(self) -> RuntimeIdentity:
        """Get runtime identity data contract.
        
        CRITICAL: This returns a DATA CONTRACT, NOT authoritative identity.
        Phase 2: Trusted authority process will return persisted values.
        Phase 1: Returns placeholder for data contract specification.
        
        SECURITY WARNING:
        - Caller-constructed instances are NOT authoritative
        - Phase 2 will enforce persisted values in trusted authority process
        
        Returns:
            RuntimeIdentity data contract (non-authoritative)
        """
        # Phase 1: Placeholder for data contract specification
        # Phase 2: Trusted authority process will return persisted values
        return RuntimeIdentity(
            generation=self._generation,
            bootstrap_timestamp=self._bootstrap_timestamp,
        )
    
    def increment_generation(self) -> None:
        """Increment generation counter (data contract operation).
        
        CRITICAL: This is a DATA CONTRACT operation, NOT authoritative enforcement.
        Phase 2: Trusted authority process will persist to OS-protected storage.
        Phase 1: In-memory only for data contract specification.
        
        SECURITY WARNING:
        - In-process increment is NOT authoritative
        - Phase 2 will enforce atomic persistence in trusted authority process
        """
        self._generation += 1
        # Phase 2: Trusted authority process will persist to OS-protected storage
    
    def get_secret_key(self) -> Optional[bytes]:
        """Get secret key data contract.
        
        CRITICAL: This returns a DATA CONTRACT placeholder, NOT a real secret.
        Phase 2: Trusted authority process will manage real secret key in OS-protected storage.
        Phase 1: Returns None (no secret material in data contract).
        
        SECURITY WARNING:
        - DO NOT use this for actual HMAC signing
        - Phase 2 will provide real secret key in trusted authority process
        - This is a data contract placeholder only
        
        Returns:
            None (Phase 1: no secret material)
        """
        # Phase 1: Returns None (no secret material in data contract)
        # Phase 2: Trusted authority process will manage real secret key
        return self._secret_key
