"""P0-B V4-r5 Authority Trust Anchor Configuration.

F5 V4-r3 FIX: Trust anchor stored in OS-protected location.
F5 V4-r5 FIX: Verify directory was created by authorized provisioning (first-writer attack).

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
- T7: Attacker without admin/provisioning privilege - Protected by UAC requirement
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
    F5 V4-r6 FIX: Verify cryptographic signature instead of declarative marker.
    F5 V4-r9 FIX: Load provisioner public key from machine-level independent location.
    
    The trust anchor is stored in a protected directory with Windows ACL:
    - Ordinary callers: READ ONLY
    - Authority runtime: READ ONLY
    - OS-authorized provisioner: WRITE (requires admin privilege)
    
    This class provides READ-ONLY access to the trust store for the authority
    and verifiers. Modification is ONLY possible via OSAuthorityProvisioner.
    
    F5 V4-r6: Trust store authenticity is verified via cryptographic signature
    from the provisioner keypair, not via declarative "provisioned_by" marker.
    
    F5 V4-r9: Provisioner public key loaded from machine-level location
    (C:\ProgramData\IABV\provisioner_trust\) to break circular trust dependency.
    """
    
    def __init__(
        self,
        protected_root: Path,
        provisioner_trust_anchor_path_or_public_key: Path | ed25519.Ed25519PublicKey | None = None,
        provisioner_public_key: ed25519.Ed25519PublicKey | None = None,
    ):
        """Initialize trust anchor configuration (READ-ONLY).
        
        F5 V4-r5 FIX: Runtime does NOT create directory - fail-closed if missing.
        F5 V4-r5 FIX: Verify directory was created by authorized provisioning.
        F5 V4-r6 FIX: Verify cryptographic signature of trust store.
        F5 V4-r9 FIX: Load provisioner public key from machine-level independent location.
        
        Args:
            protected_root: Root directory for protected trust store
                           (separate from ordinary application data)
            provisioner_trust_anchor_path_or_public_key: Machine-level path for provisioner public key
                                         (C:\ProgramData\IABV\provisioner_trust\)
                                         OR Ed25519PublicKey for backward compatibility (legacy mode)
                                         If None, uses legacy single-directory layout (for test compatibility)
            provisioner_public_key: Optional provisioner public key for signature verification.
                                   If None, loads from machine-level location (or legacy location).
        
        Raises:
            ValueError: If protected directory does not exist (not provisioned)
            ValueError: If directory exists but was not created by authorized provisioning
            ValueError: If trust store signature is invalid
        """
        self.protected_root = protected_root
        
        # F5 V4-r9 FIX: Backward compatibility - detect if second arg is Path or PublicKey
        if isinstance(provisioner_trust_anchor_path_or_public_key, ed25519.Ed25519PublicKey):
            # Legacy mode: second arg is public key
            self.provisioner_trust_anchor_path = None
            provisioner_public_key = provisioner_trust_anchor_path_or_public_key
        else:
            # V4-r9 mode: second arg is path (or None)
            self.provisioner_trust_anchor_path = provisioner_trust_anchor_path_or_public_key
        
        # F5 V4-r4 FIX: Runtime does NOT create directory - must be pre-created by provisioning
        if not self.protected_root.exists():
            raise ValueError(
                f"Protected trust root directory does not exist: {self.protected_root}. "
                "Authority runtime cannot create the protected directory. "
                "Trust root must be established via OS-authorized provisioning first. "
                "Run OSAuthorityProvisioner.setup_protected_directory() with admin privileges."
            )
        
        self._config_file = self.protected_root / "authority_trust.json"
        
        # F5 V4-r9 FIX: Provisioner public key loaded from machine-level location if provided
        # Otherwise, use legacy single-directory layout (for test compatibility)
        if self.provisioner_trust_anchor_path:
            self._provisioner_public_key_path = self.provisioner_trust_anchor_path / "provisioner_public_key.json"
        else:
            # Legacy layout: provisioner public key in same directory
            self._provisioner_public_key_path = self.protected_root / "provisioner_keypair.json"
        
        self._keys: dict[str, TrustedAuthorityKey] = {}
        
        # F5 V4-r5 FIX: Verify directory was created by authorized provisioning
        # Check if trust store exists and has valid provisioning marker
        if not self._config_file.exists():
            raise ValueError(
                f"Protected directory exists but trust store not found: {self._config_file}. "
                "Directory may have been created by unauthorized process. "
                "Trust root must be established via OS-authorized provisioning first."
            )
        
        # F5 V4-r6 FIX: Load or get provisioner public key for signature verification
        if provisioner_public_key is None:
            provisioner_public_key = self._load_provisioner_public_key()
        
        # F5 V4-r3 FIX: Load trust store with tamper detection and signature verification
        self._load_config_with_signature_verification(provisioner_public_key)
        
        logger.info("AuthorityTrustConfig initialized (READ-ONLY): %s", self._config_file)
    
    def _load_provisioner_public_key(self) -> ed25519.Ed25519PublicKey:
        """Load provisioner public key from machine-level independent location or legacy location.
        
        F5 V4-r6 FIX: Load provisioner public key for signature verification.
        F5 V4-r9 FIX: Load from machine-level location to break circular trust.
        
        Returns:
            Ed25519 public key of the provisioner
        
        Raises:
            ValueError: If provisioner public key file is missing or corrupted
        """
        if not self._provisioner_public_key_path.exists():
            if self.provisioner_trust_anchor_path:
                # V4-r9 machine-level location
                raise ValueError(
                    f"Provisioner public key not found at machine-level location: {self._provisioner_public_key_path}. "
                    "Trust root must be established via OS-authorized provisioning first. "
                    "Run OSAuthorityProvisioner.setup_provisioner_trust_anchor() with admin privileges."
                )
            else:
                # Legacy single-directory layout
                raise ValueError(
                    f"Provisioner keypair not found: {self._provisioner_public_key_path}. "
                    "Trust root must be established via OS-authorized provisioning first."
                )
        
        try:
            with open(self._provisioner_public_key_path, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            
            public_key_hex = key_data["public_key_hex"]
            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            if self.provisioner_trust_anchor_path:
                logger.info("Loaded provisioner public key from machine-level trust anchor: %s", key_data["public_key_id"])
            else:
                logger.info("Loaded provisioner public key from legacy location: %s", key_data["public_key_id"])
            return public_key
            
        except Exception as exc:
            logger.error("Failed to load provisioner public key: %s", exc)
            raise ValueError(f"Failed to load provisioner public key: {exc}")
    
    def _load_config_with_signature_verification(self, provisioner_public_key: ed25519.Ed25519PublicKey) -> None:
        """Load trusted keys from protected trust store with signature verification.
        
        F5 V4-r3 FIX: Fail closed on trust store corruption/tampering.
        F5 V4-r6 FIX: Verify cryptographic signature instead of declarative marker.
        
        Args:
            provisioner_public_key: Provisioner public key for signature verification
        
        Raises:
            ValueError: If trust store is corrupted, tampered, or signature is invalid
        """
        if not self._config_file.exists():
            logger.info("No existing trust store (NOT PROVISIONED)")
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # F5 V4-r6 FIX: Verify cryptographic signature
            if "provisioner_signature" not in config_data:
                raise ValueError(
                    "Trust store missing cryptographic signature. "
                    "Trust root must be established via OS-authorized provisioning with V4-r6 or later."
                )
            
            signature_hex = config_data["provisioner_signature"]
            
            # Extract signature from config for verification
            # Remove signature field (it was added after signing)
            config_copy = config_data.copy()
            config_copy.pop("provisioner_signature", None)
            # Note: provisioner_public_key_id is included in the signature (added before signing)
            
            # Verify signature
            try:
                canonical = json.dumps(config_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
                signature = bytes.fromhex(signature_hex)
                provisioner_public_key.verify(signature, canonical)
                logger.info("Trust store signature verified")
            except Exception as exc:
                logger.error("Trust store signature verification failed: %s", exc)
                raise ValueError(
                    f"Trust store signature verification failed: {exc}. "
                    "Trust store may have been tampered with or was not signed by authorized provisioner."
                )
            
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