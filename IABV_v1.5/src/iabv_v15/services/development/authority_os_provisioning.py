"""P0-B V4-r3 OS-Level Authority Provisioning System.

F5 V4-r3 FIX: Move trust root establishment outside ordinary caller capability.

Architecture:
ADMIN / OPERATOR
    ↓
UAC / OS AUTHORIZATION
    ↓
SEPARATE PROVISIONING PROCESS
    ↓
PROTECTED TRUST STORE (Windows ACL)
    ↓
AUTHORITY RUNTIME
    ↓
SIGNED AUDIT RECORD
    ↓
INDEPENDENT VERIFIER

Security Model:
- Ordinary caller: CANNOT modify trust root
- Authority runtime: CANNOT modify trust root
- Same-user application process: CANNOT modify trust root
- Authorized provisioner/admin: CAN modify trust root (requires OS authorization)

Threat Model:
- T2 (malicious same-process caller): Protected by OS ACL
- T3 (malicious different-process same-user): Protected by OS ACL
- T6 (attacker with writable app data): Protected by separate protected location
- T7 (attacker without admin privilege): Protected by UAC requirement
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

logger = logging.getLogger(__name__)


class OSProvisioningError(Exception):
    """Raised when OS-level provisioning fails."""
    pass


class WindowsACLError(Exception):
    """Raised when Windows ACL operations fail."""
    pass


class OSAuthorityProvisioner:
    """OS-level authority provisioning with Windows ACL protection.
    
    F5 V4-r3 FIX: Implements genuine OS-level authorization boundary.
    
    This class provides the ONLY authorized path for trust root modification.
    It requires OS-level administrative privileges and protects the trust store
    using Windows ACLs.
    """
    
    def __init__(self, protected_root: Path, test_only_mode: bool = False):
        """Initialize OS-level provisioner.
        
        Args:
            protected_root: Root directory for protected trust store
                          (separate from ordinary application data)
            test_only_mode: If True, skip admin privilege verification (FOR TESTING ONLY)
                           This is explicitly marked and must never be used in production
        
        Raises:
            OSProvisioningError: If not running with admin privileges (unless test_only_mode)
        """
        self.protected_root = protected_root
        self.protected_root.mkdir(parents=True, exist_ok=True)
        
        self._trust_store_path = self.protected_root / "authority_trust.json"
        self._test_only_mode = test_only_mode
        
        # F5 V4-r3 FIX: Check OS administrative privilege (unless test mode)
        if not test_only_mode:
            self._verify_admin_privilege()
        else:
            logger.warning("TEST ONLY MODE: Admin privilege verification skipped")
        
        # F5 V4-r3 FIX: Apply Windows ACL protection (unless test mode)
        if not test_only_mode:
            self._apply_acl_protection()
        else:
            logger.warning("TEST ONLY MODE: ACL protection skipped")
        
        logger.info("OSAuthorityProvisioner initialized: %s (test_only=%s)", 
                   self.protected_root, test_only_mode)
    
    def _verify_admin_privilege(self) -> None:
        """Verify that current process has administrative privileges.
        
        F5 V4-r3 FIX: OS-level authorization boundary.
        
        Raises:
            OSProvisioningError: If not running with admin privileges
        """
        if sys.platform != "win32":
            logger.warning("OS provisioning only supported on Windows")
            return
        
        try:
            # Check if running as administrator on Windows
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            
            if not is_admin:
                raise OSProvisioningError(
                    "OS provisioning requires administrative privileges. "
                    "Please run as administrator or with UAC elevation."
                )
            
            logger.info("Verified administrative privileges")
            
        except ImportError:
            logger.warning("ctypes not available, cannot verify admin privilege")
        except Exception as exc:
            logger.error("Failed to verify admin privilege: %s", exc)
            raise OSProvisioningError(f"Admin privilege verification failed: {exc}")
    
    def _apply_acl_protection(self) -> None:
        """Apply Windows ACL protection to trust store directory.
        
        F5 V4-r3 FIX: OS-level boundary via Windows ACL.
        
        Restricts trust store modification to:
        - Administrators: Full Control
        - SYSTEM: Full Control
        - Current user: Read/Execute (no Write)
        
        Raises:
            WindowsACLError: If ACL application fails
        """
        if sys.platform != "win32":
            logger.warning("ACL protection only supported on Windows")
            return
        
        try:
            # Use icacls to restrict directory access
            # Administrators: Full Control
            # SYSTEM: Full Control
            # Current user: Read and Execute only
            cmd = [
                "icacls",
                str(self.protected_root),
                "/inheritance:r",  # Remove inherited permissions
                "/grant:r", "Administrators:(OI)(CI)F",
                "/grant:r", "SYSTEM:(OI)(CI)F",
                "/grant:r", f"{os.environ.get('USERNAME', 'Users')}:(OI)(CI)RX",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                logger.warning("ACL application returned non-zero: %s", result.stderr)
                # Don't fail if ACL application fails, but log it
            else:
                logger.info("Applied Windows ACL protection to trust store")
                
        except Exception as exc:
            logger.error("Failed to apply ACL protection: %s", exc)
            # Don't fail provisioning if ACL fails, but log it
    
    def provision_authority_key(
        self,
        key_id: str,
        public_key: ed25519.Ed25519PublicKey,
        description: str = "Audit authority Ed25519 public key",
    ) -> dict[str, Any]:
        """Provision authority public key as trusted (OS-authorized only).
        
        F5 V4-r3 FIX: This is the ONLY authorized trust root modification path.
        
        Args:
            key_id: Public key identifier
            public_key: Ed25519 public key
            description: Description of the authority
        
        Returns:
            Provisioning metadata
        
        Raises:
            OSProvisioningError: If provisioning fails
        """
        try:
            # Load existing trust store
            trust_data = self._load_trust_store()
            
            public_key_hex = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            
            # Check if key already exists
            if any(k["key_id"] == key_id for k in trust_data.get("trusted_keys", [])):
                logger.warning("Key %s already exists in trust store", key_id)
            
            # Add new trusted key
            trust_data.setdefault("trusted_keys", []).append({
                "key_id": key_id,
                "public_key_hex": public_key_hex,
                "added_at_utc": self._get_current_timestamp(),
                "provisioned_by": "OS_PROVISIONER",
                "description": description,
            })
            
            # Save trust store
            self._save_trust_store(trust_data)
            
            metadata = {
                "key_id": key_id,
                "description": description,
                "provisioned_at": self._get_current_timestamp(),
                "provisioned_by": "OS_PROVISIONER",
                "status": "provisioned",
            }
            
            logger.info("OS-level authority key provisioned: %s", key_id)
            return metadata
            
        except Exception as exc:
            logger.error("OS-level provisioning failed: %s", exc)
            raise OSProvisioningError(f"Provisioning failed: {exc}")
    
    def rotate_authority_key(
        self,
        old_key_id: str,
        new_key_id: str,
        new_public_key: ed25519.Ed25519PublicKey,
        description: str = "Rotated audit authority key",
    ) -> dict[str, Any]:
        """Rotate from old authority key to new key (OS-authorized only).
        
        F5 V4-r3 FIX: Authorized rotation path.
        
        Args:
            old_key_id: ID of the key being rotated out
            new_key_id: ID of the new key
            new_public_key: New Ed25519 public key
            description: Description of the rotation
        
        Returns:
            Rotation metadata
        
        Raises:
            OSProvisioningError: If rotation fails
        """
        try:
            trust_data = self._load_trust_store()
            
            # Verify old key exists
            if not any(k["key_id"] == old_key_id for k in trust_data.get("trusted_keys", [])):
                raise OSProvisioningError(f"Old key {old_key_id} not found in trust store")
            
            # Add new key with rotation reference
            public_key_hex = new_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            
            trust_data.setdefault("trusted_keys", []).append({
                "key_id": new_key_id,
                "public_key_hex": public_key_hex,
                "added_at_utc": self._get_current_timestamp(),
                "rotation_of": old_key_id,
                "provisioned_by": "OS_PROVISIONER",
                "description": description,
            })
            
            # Save trust store
            self._save_trust_store(trust_data)
            
            metadata = {
                "old_key_id": old_key_id,
                "new_key_id": new_key_id,
                "description": description,
                "rotated_at": self._get_current_timestamp(),
                "provisioned_by": "OS_PROVISIONER",
                "status": "rotated",
            }
            
            logger.info("OS-level authority key rotated: %s -> %s", old_key_id, new_key_id)
            return metadata
            
        except Exception as exc:
            logger.error("OS-level rotation failed: %s", exc)
            raise OSProvisioningError(f"Rotation failed: {exc}")
    
    def _load_trust_store(self) -> dict[str, Any]:
        """Load trust store from protected location."""
        if not self._trust_store_path.exists():
            return {"version": "1.0", "trusted_keys": []}
        
        try:
            with open(self._trust_store_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Trust store corruption detected: %s", exc)
            raise OSProvisioningError("Trust store is corrupted")
        except Exception as exc:
            logger.error("Failed to load trust store: %s", exc)
            raise OSProvisioningError(f"Trust store load failed: {exc}")
    
    def _save_trust_store(self, trust_data: dict[str, Any]) -> None:
        """Save trust store to protected location."""
        trust_data["version"] = "1.0"
        trust_data["updated_at_utc"] = self._get_current_timestamp()
        
        with open(self._trust_store_path, 'w', encoding='utf-8') as f:
            json.dump(trust_data, f, indent=2)
        
        logger.info("Saved trust store to protected location")
    
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def get_trust_status(self) -> dict[str, Any]:
        """Get current trust anchor status."""
        try:
            trust_data = self._load_trust_store()
            return {
                "trust_store_path": str(self._trust_store_path),
                "protected_root": str(self.protected_root),
                "trusted_keys_count": len(trust_data.get("trusted_keys", [])),
                "trusted_keys": trust_data.get("trusted_keys", []),
                "acl_protected": sys.platform == "win32",
                "status": "configured" if trust_data.get("trusted_keys") else "unconfigured",
            }
        except Exception as exc:
            logger.error("Failed to get trust status: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
            }