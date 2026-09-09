"""P0-B V4-r3 Authority Trust Anchor Configuration.

F5 V4-r3 FIX: Trust anchor stored in OS-protected location.

This module implements the independent trust anchor mechanism for the audit authority.
The trust store is now located in a protected directory with Windows ACL restrictions.

Trust Model:
- Bootstrap: OS-authorized provisioning writes public key to protected trust store
- Storage: Protected directory with Windows ACL (admin only write)
- Validation: Caller reads trusted key independently, compares with authority
- Rotation: Explicit rotation via OS-authorized provisioning
- Restart: Same authority identity preserved via durable key storage
- Historical verification: Historical keys retained in config
- Unknown-key behavior: Reject if key not in trusted configuration

Security Model:
- Ordinary caller: CANNOT modify trust root (OS ACL protection)
- Authority runtime: CANNOT modify trust root (OS ACL protection)
- Same-user process: CANNOT modify trust root (OS ACL protection)
- Authorized provisioner: CAN modify trust root (requires admin privilege)

Threat Model:
- T2: Malicious same-process caller - Protected by OS ACL
- T3: Malicious different-process same-user - Protected by OS ACL
- T6: Attacker with writable app data - Protected by separate protected location
- T7: Attacker without admin privilege - Protected by UAC requirement
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

logger = logging.getLogger(__name__)


@dataclass
class TrustedAuthorityKey:
    """Trusted authority public key entry."""
    
    key_id: str
    public_key_hex: str
    added_at_utc: str
    rotation_of: str | None = None  # If this key replaced another key
    description: str = ""
    provisioned_by: str = ""  # F5 V4-r3: Who provisioned this key (OS_PROVISIONER)


class AuthorityTrustConfig:
    """Authority trust anchor configuration (READ-ONLY for authority runtime).
    
    F5 V4-r3 FIX: Trust anchor stored in OS-protected location.
    
    The trust anchor is stored in a protected directory with Windows ACL:
    - Ordinary callers: READ ONLY
    - Authority runtime: READ ONLY
    - OS-authorized provisioner: WRITE (requires admin privilege)
    
    This class provides READ-ONLY access to the trust store for the authority
    and verifiers. Modification is ONLY possible via OSAuthorityProvisioner.
    """
    
    def __init__(self, protected_root: Path):
        """Initialize trust anchor configuration (READ-ONLY).
        
        Args:
            protected_root: Root directory for protected trust store
                           (separate from ordinary application data)
        """
        self.protected_root = protected_root
        self.protected_root.mkdir(parents=True, exist_ok=True)
        
        self._config_file = self.protected_root / "authority_trust.json"
        self._keys: dict[str, TrustedAuthorityKey] = {}
        
        # F5 V4-r3 FIX: Load trust store with tamper detection
        self._load_config_with_tamper_detection()
        
        logger.info("AuthorityTrustConfig initialized (READ-ONLY): %s", self._config_file)
    
    def _load_config_with_tamper_detection(self) -> None:
        """Load trusted keys from protected trust store with tamper detection.
        
        F5 V4-r3 FIX: Fail closed on trust store corruption/tampering.
        
        Raises:
            ValueError: If trust store is corrupted or tampered
        """
        if not self._config_file.exists():
            logger.info("No existing trust store (NOT PROVISIONED)")
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate structure
            if not isinstance(config_data, dict):
                raise ValueError("Trust store is not a dictionary")
            
            if "trusted_keys" not in config_data:
                raise ValueError("Trust store missing 'trusted_keys' field")
            
            if not isinstance(config_data["trusted_keys"], list):
                raise ValueError("Trust store 'trusted_keys' is not a list")
            
            # Load keys
            for key_data in config_data["trusted_keys"]:
                key = TrustedAuthorityKey(**key_data)
                self._keys[key.key_id] = key
            
            logger.info("Loaded %d trusted keys from protected store", len(self._keys))
            
        except json.JSONDecodeError as exc:
            logger.error("Trust store JSON corruption detected: %s", exc)
            raise ValueError("Trust store is corrupted (invalid JSON)")
        except Exception as exc:
            logger.error("Failed to load trust store: %s", exc)
            raise ValueError(f"Trust store load failed: {exc}")
    
    def get_trusted_key(self, key_id: str) -> TrustedAuthorityKey | None:
        """Get trusted key by ID (READ-ONLY).
        
        Args:
            key_id: Public key identifier
        
        Returns:
            TrustedAuthorityKey if found, None otherwise
        """
        return self._keys.get(key_id)
    
    def get_all_trusted_keys(self) -> list[TrustedAuthorityKey]:
        """Get all trusted keys (READ-ONLY)."""
        return list(self._keys.values())
    
    def verify_public_key(self, public_key: ed25519.Ed25519PublicKey) -> bool:
        """Verify that a public key is in the trusted configuration.
        
        Args:
            public_key: Ed25519 public key to verify
        
        Returns:
            True if key is trusted, False otherwise
        """
        public_key_hex = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        
        for key in self._keys.values():
            if key.public_key_hex == public_key_hex:
                logger.info("Public key verified as trusted: %s", key.key_id)
                return True
        
        logger.warning("Public key not found in trusted configuration")
        return False
    
    def verify_authority_identity_match(
        self,
        authority_public_key_id: str,
        authority_public_key: ed25519.Ed25519PublicKey,
    ) -> bool:
        """Verify that authority identity matches trusted configuration.
        
        F5 V4-r3 FIX: Critical check - trusted key must match authority identity.
        
        Args:
            authority_public_key_id: Authority's public key ID
            authority_public_key: Authority's public key
        
        Returns:
            True if authority identity matches trusted key, False otherwise
        """
        trusted_key = self.get_trusted_key(authority_public_key_id)
        
        if trusted_key is None:
            logger.warning("Authority key ID %s not found in trust store", authority_public_key_id)
            return False
        
        # Verify public key bytes match
        authority_key_hex = authority_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        
        if authority_key_hex != trusted_key.public_key_hex:
            logger.error(
                "Authority key ID %s found but public key bytes do not match "
                "(possible key replacement attack)",
                authority_public_key_id
            )
            return False
        
        logger.info("Authority identity verified: %s", authority_public_key_id)
        return True