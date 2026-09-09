"""P0-B V4-r1 Authority Trust Anchor Configuration.

This module implements the independent trust anchor mechanism for the audit authority.

F5 FIX: Trust anchor must be explicit and independent of GET_PUBLIC_KEY endpoint.

Trust Model:
- Bootstrap: Authority writes public key to trusted configuration file
- Storage: Local file in data/authority directory
- Validation: Caller reads trusted key independently, compares with authority
- Rotation: Explicit rotation via configuration file update
- Restart: Same authority identity preserved via durable key storage
- Historical verification: Historical keys retained in config
- Unknown-key behavior: Reject if key not in trusted configuration

Threat Model:
- T5: Fake public key - rejected if not in trusted config
- T9: Authority restart - identity preserved
- T10: Endpoint spoofing - combined with ACL + trusted key + signature
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


class AuthorityTrustConfig:
    """Authority trust anchor configuration.
    
    F5 FIX: Independent trust anchor mechanism.
    
    The trust anchor is stored in a local configuration file that:
    - Is written by the authority process on first boot
    - Is read by callers to establish trusted authority identity
    - Survives authority restarts (durable key storage)
    - Supports explicit key rotation
    - Retains historical keys for verifying old records
    """
    
    def __init__(self, config_root: Path):
        """Initialize trust anchor configuration.
        
        Args:
            config_root: Root directory for authority configuration
        """
        self.config_root = config_root
        self.config_root.mkdir(parents=True, exist_ok=True)
        
        self._config_file = self.config_root / "authority_trust.json"
        self._keys: dict[str, TrustedAuthorityKey] = {}
        
        self._load_config()
        
        logger.info("AuthorityTrustConfig initialized: %s", self._config_file)
    
    def _load_config(self) -> None:
        """Load trusted keys from configuration file."""
        if not self._config_file.exists():
            logger.info("No existing trust config, will create on first authority boot")
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for key_data in config_data.get("trusted_keys", []):
                key = TrustedAuthorityKey(**key_data)
                self._keys[key.key_id] = key
            
            logger.info("Loaded %d trusted keys from config", len(self._keys))
            
        except Exception as exc:
            logger.error("Failed to load trust config: %s", exc)
            raise
    
    def _save_config(self) -> None:
        """Save trusted keys to configuration file."""
        config_data = {
            "version": "1.0",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "trusted_keys": [
                {
                    "key_id": key.key_id,
                    "public_key_hex": key.public_key_hex,
                    "added_at_utc": key.added_at_utc,
                    "rotation_of": key.rotation_of,
                    "description": key.description,
                }
                for key in self._keys.values()
            ],
        }
        
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info("Saved trust config with %d keys", len(self._keys))
    
    def get_trusted_key(self, key_id: str) -> TrustedAuthorityKey | None:
        """Get trusted key by ID.
        
        Args:
            key_id: Public key identifier
        
        Returns:
            TrustedAuthorityKey if found, None otherwise
        """
        return self._keys.get(key_id)
    
    def add_trusted_key(
        self,
        key_id: str,
        public_key: ed25519.Ed25519PublicKey,
        description: str = "",
        rotation_of: str | None = None,
        _provisioning_only: bool = False,
    ) -> None:
        """Add a trusted public key (PROVISIONING ONLY).
        
        F5 V4-r2 FIX: This method requires explicit _provisioning_only flag.
        
        Args:
            key_id: Public key identifier
            public_key: Ed25519 public key
            description: Optional description
            rotation_of: If this key replaces another key, specify the old key_id
            _provisioning_only: MUST be True for this operation to succeed
        
        Raises:
            ValueError: If _provisioning_only is False (prevents caller self-bootstrap)
        """
        if not _provisioning_only:
            raise ValueError(
                "add_trusted_key() requires _provisioning_only=True. "
                "Trust anchor modification must go through authorized provisioning path. "
                "Normal callers cannot modify trust root."
            )
        
        public_key_hex = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        
        if key_id in self._keys:
            logger.warning("Key %s already exists in trust config, updating", key_id)
        
        key = TrustedAuthorityKey(
            key_id=key_id,
            public_key_hex=public_key_hex,
            added_at_utc=datetime.now(timezone.utc).isoformat(),
            rotation_of=rotation_of,
            description=description,
        )
        
        self._keys[key_id] = key
        self._save_config()
        
        logger.info("Provisioned trusted key: %s", key_id)
    
    def reload_config(self) -> None:
        """Reload trust config from file (for testing/provisioning scenarios)."""
        self._load_config()
    
    def get_all_trusted_keys(self) -> list[TrustedAuthorityKey]:
        """Get all trusted keys."""
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
    
    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
        new_public_key: ed25519.Ed25519PublicKey,
        description: str = "",
    ) -> None:
        """Rotate from old key to new key.
        
        Args:
            old_key_id: ID of the key being rotated out
            new_key_id: ID of the new key
            new_public_key: New Ed25519 public key
            description: Optional description
        """
        if old_key_id not in self._keys:
            raise ValueError(f"Old key {old_key_id} not found in trust config")
        
        # Add new key with rotation reference
        self.add_trusted_key(
            key_id=new_key_id,
            public_key=new_public_key,
            description=description,
            rotation_of=old_key_id,
        )
        
        logger.info("Rotated key: %s -> %s", old_key_id, new_key_id)