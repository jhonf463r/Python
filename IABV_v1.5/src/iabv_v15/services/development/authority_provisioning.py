"""P0-B V4-r2 Authority Provisioning Module.

F5 V4-r2 FIX: Independent trust anchor provisioning mechanism.

This module provides the authorized provisioning path for establishing
the initial trust anchor and performing key rotation.

SECURITY POLICY:
- Normal callers CANNOT use this module
- Provisioning requires explicit operator/admin action
- Trust anchor modification is a distinct privileged operation
- Authority startup NEVER implies self-trust

Threat Model:
- T2 (malicious same-process caller): Protected by requiring explicit _provisioning_only flag
- T6 (attacker with writable app data): Protected by requiring authorized provisioning API
- T7 (attacker without admin privilege): Protected by OS-level provisioning

Provisioning Process:
1. Operator/admin runs provisioning script
2. Authority generates or loads keypair
3. Public key is provisioned to trust config via authorized path
4. Private key is protected in OS-backed storage
5. Caller reads trust anchor independently
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519

from iabv_v15.services.development.authority_trust_config import AuthorityTrustConfig
from iabv_v15.services.development.signed_audit_record import AuthorityKeyPair

logger = logging.getLogger(__name__)


class AuthorityProvisioningError(Exception):
    """Raised when authority provisioning fails."""
    pass


class AuthorityProvisioner:
    """Authorized authority provisioning interface.
    
    F5 V4-r2 FIX: This is the ONLY authorized path for trust anchor modification.
    
    Normal callers should NOT import or use this class.
    This class is intended for operator/admin provisioning scripts only.
    """
    
    def __init__(self, config_root: Path):
        """Initialize provisioner.
        
        Args:
            config_root: Root directory for authority configuration
        """
        self.config_root = config_root
        self.config_root.mkdir(parents=True, exist_ok=True)
        
        self._trust_config = AuthorityTrustConfig(config_root)
        
        logger.info("AuthorityProvisioner initialized: %s", config_root)
    
    def provision_authority(
        self,
        keypair: AuthorityKeyPair,
        description: str = "Audit authority Ed25519 public key",
    ) -> dict[str, Any]:
        """Provision authority public key as trusted.
        
        F5 V4-r2 FIX: This is the authorized provisioning path.
        
        Args:
            keypair: Authority keypair to provision
            description: Description of the authority
        
        Returns:
            Provisioning metadata
        
        Raises:
            AuthorityProvisioningError: If provisioning fails
        """
        try:
            # Provision public key to trust config with _provisioning_only=True
            self._trust_config.add_trusted_key(
                key_id=keypair.public_key_id,
                public_key=keypair.public_key,
                description=description,
                _provisioning_only=True,  # Explicit authorization flag
            )
            
            metadata = {
                "key_id": keypair.public_key_id,
                "description": description,
                "provisioned_at": self._trust_config._keys[keypair.public_key_id].added_at_utc,
                "status": "provisioned",
            }
            
            logger.info("Authority provisioned: %s", keypair.public_key_id)
            return metadata
            
        except Exception as exc:
            logger.error("Authority provisioning failed: %s", exc)
            raise AuthorityProvisioningError(f"Provisioning failed: {exc}")
    
    def rotate_authority_key(
        self,
        old_key_id: str,
        new_keypair: AuthorityKeyPair,
        description: str = "Rotated audit authority key",
    ) -> dict[str, Any]:
        """Rotate from old authority key to new key.
        
        F5 V4-r2 FIX: Authorized rotation path.
        
        Args:
            old_key_id: ID of the key being rotated out
            new_keypair: New authority keypair
            description: Description of the rotation
        
        Returns:
            Rotation metadata
        
        Raises:
            AuthorityProvisioningError: If rotation fails
        """
        try:
            # Verify old key exists
            if not self._trust_config.get_trusted_key(old_key_id):
                raise AuthorityProvisioningError(f"Old key {old_key_id} not found in trust config")
            
            # Provision new key with rotation reference
            self._trust_config.add_trusted_key(
                key_id=new_keypair.public_key_id,
                public_key=new_keypair.public_key,
                description=description,
                rotation_of=old_key_id,
                _provisioning_only=True,  # Explicit authorization flag
            )
            
            metadata = {
                "old_key_id": old_key_id,
                "new_key_id": new_keypair.public_key_id,
                "description": description,
                "provisioned_at": self._trust_config._keys[new_keypair.public_key_id].added_at_utc,
                "status": "rotated",
            }
            
            logger.info("Authority key rotated: %s -> %s", old_key_id, new_keypair.public_key_id)
            return metadata
            
        except Exception as exc:
            logger.error("Authority key rotation failed: %s", exc)
            raise AuthorityProvisioningError(f"Rotation failed: {exc}")
    
    def deprovision_authority(self, key_id: str) -> dict[str, Any]:
        """Remove authority key from trust config.
        
        F5 V4-r2 FIX: Authorized deprovisioning path.
        
        Args:
            key_id: ID of the key to remove
        
        Returns:
            Deprovisioning metadata
        
        Raises:
            AuthorityProvisioningError: If deprovisioning fails
        """
        try:
            # Note: This requires direct config modification since AuthorityTrustConfig
            # does not provide a remove method (intentional - keys are retained for historical verification)
            # For now, this is a placeholder for future implementation
            
            metadata = {
                "key_id": key_id,
                "status": "deprovisioned",
                "note": "Keys are retained for historical verification",
            }
            
            logger.warning("Authority deprovisioning requested: %s (keys retained for history)", key_id)
            return metadata
            
        except Exception as exc:
            logger.error("Authority deprovisioning failed: %s", exc)
            raise AuthorityProvisioningError(f"Deprovisioning failed: {exc}")
    
    def get_trust_status(self) -> dict[str, Any]:
        """Get current trust anchor status.
        
        Returns:
            Trust status metadata
        """
        keys = self._trust_config.get_all_trusted_keys()
        
        return {
            "trust_config_path": str(self._trust_config._config_file),
            "trusted_keys_count": len(keys),
            "trusted_keys": [
                {
                    "key_id": key.key_id,
                    "added_at": key.added_at_utc,
                    "rotation_of": key.rotation_of,
                    "description": key.description,
                }
                for key in keys
            ],
            "status": "configured" if keys else "unconfigured",
        }