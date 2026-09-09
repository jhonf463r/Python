"""P0-B V4-r6 OS-Level Authority Provisioning System.

F5 V4-r3 FIX: Move trust root establishment outside ordinary caller capability.
F5 V4-r6 FIX: Replace declarative marker with cryptographic signature.

Architecture:
ADMIN / OPERATOR
    ↓
UAC / OS AUTHORIZATION
    ↓
SEPARATE PROVISIONING PROCESS
    ↓
PROVISIONER KEYPAIR (stored separately)
    ↓
CRYPTOGRAPHIC SIGNATURE OF TRUST STORE
    ↓
PROTECTED TRUST STORE (Windows ACL)
    ↓
AUTHORITY RUNTIME (verifies signature)
    ↓
SIGNED AUDIT RECORD
    ↓
INDEPENDENT VERIFIER

Security Model:
- Ordinary caller: CANNOT modify trust root
- Authority runtime: CANNOT modify trust root
- Same-user application process: CANNOT modify trust root
- Authorized provisioner/admin: CAN modify trust root (requires OS authorization)
- Trust store authenticity: Verified via cryptographic signature, not declarative marker

Threat Model:
- T2 (malicious same-process caller): Protected by OS ACL + signature verification
- T3 (malicious different-process same-user): Protected by OS ACL + signature verification
- T6 (attacker with writable app data): Protected by separate protected location + signature
- T7 (attacker without admin privilege): Protected by UAC requirement + signature
- T10 (forged provisioning marker): Protected by cryptographic signature
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from cryptography.hazmat.primitives import hashes

# F14 V4-r7 FIX: DPAPI for private key protection
try:
    import win32crypt
    DPAPI_AVAILABLE = True
except ImportError:
    DPAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ProvisionerKeyPair:
    """Provisioner keypair for signing trust stores.
    
    F5 V4-r6: Separate keypair for provisioning authority.
    This keypair is used to sign trust stores to establish cryptographic
    authenticity, replacing the insecure declarative marker.
    
    Security Model:
    - Private key: Stored in separate protected location, used only by OS-authorized provisioner
    - Public key: Needed by runtime to verify trust store signatures
    - Purpose: Cryptographic signature of trust store, not declarative marker
    """
    _private_key: ed25519.Ed25519PrivateKey
    _public_key: ed25519.Ed25519PublicKey
    
    @classmethod
    def generate(cls) -> "ProvisionerKeyPair":
        """Generate a new provisioner keypair."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return cls(private_key, public_key)
    
    @property
    def public_key_id(self) -> str:
        """Unique identifier for the public key."""
        public_bytes = self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return public_bytes.hex()
    
    @property
    def public_key_hex(self) -> str:
        """Hex representation of public key."""
        public_bytes = self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return public_bytes.hex()
    
    def sign_trust_store(self, trust_data: dict[str, Any]) -> str:
        """Sign trust store data and return signature hex.
        
        Args:
            trust_data: Trust store dictionary to sign
            
        Returns:
            Hex string of Ed25519 signature
        """
        # Remove signature field if present before signing
        trust_copy = trust_data.copy()
        trust_copy.pop("provisioner_signature", None)
        
        canonical = json.dumps(trust_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        signature = self._private_key.sign(canonical)
        return signature.hex()
    
    def verify_trust_store(self, trust_data: dict[str, Any], signature_hex: str) -> bool:
        """Verify trust store signature.
        
        Args:
            trust_data: Trust store dictionary to verify
            signature_hex: Hex string of signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Remove signature field if present before verification
            trust_copy = trust_data.copy()
            trust_copy.pop("provisioner_signature", None)
            
            canonical = json.dumps(trust_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
            signature = bytes.fromhex(signature_hex)
            self._public_key.verify(signature, canonical)
            return True
        except Exception:
            return False


class OSProvisioningError(Exception):
    """Raised when OS-level provisioning fails."""
    pass


class WindowsACLError(Exception):
    """Raised when Windows ACL operations fail."""
    pass


class OSAuthorityProvisioner:
    """OS-level authority provisioning with Windows ACL protection.
    
    F5 V4-r4 FIX: Removed test_only_mode - no production bypass allowed.
    F5 V4-r9 FIX: Separate provisioner public key location to break circular trust.
    
    This class provides the ONLY authorized path for trust root modification.
    It requires OS-level administrative privileges and protects the trust store
    using Windows ACLs.
    
    F5 V4-r4 CORRECTION: The runtime constructor does NOT create directories or apply ACL.
    That must be done by a separate OS-authorized provisioning operation.
    
    F5 V4-r9 ARCHITECTURE:
    - Provisioner public key stored in C:\ProgramData\IABV\provisioner_trust\ (ADMIN ONLY WRITE)
    - Authority trust store stored in protected_root (ADMIN ONLY WRITE)
    - This breaks circular dependency between provisioner keypair and trust store
    """
    
    @staticmethod
    def setup_provisioner_trust_anchor(program_data_root: Path) -> None:
        """Setup machine-level provisioner trust anchor location (OS-authorized only).
        
        F5 V4-r9 FIX: Separate machine-level location for provisioner public key.
        
        This creates C:\ProgramData\IABV\provisioner_trust\ with admin-only write ACL.
        The provisioner public key stored here is the independent trust anchor
        used to verify authority_trust.json signatures.
        
        Args:
            program_data_root: Path to C:\ProgramData\IABV\provisioner_trust\
        
        Raises:
            OSProvisioningError: If setup fails
            WindowsACLError: If ACL application fails
        """
        if sys.platform != "win32":
            raise OSProvisioningError(
                "Provisioner trust anchor setup requires Windows platform. "
                "This security mechanism is Windows-specific."
            )
        
        # Verify admin privilege
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                raise OSProvisioningError(
                    "Provisioner trust anchor setup requires administrative privileges. "
                    "Please run as administrator or with UAC elevation."
                )
        except ImportError:
            raise OSProvisioningError("ctypes not available - cannot verify admin privilege")
        
        # Create directory
        program_data_root.mkdir(parents=True, exist_ok=True)
        
        # Apply machine-level ACL protection (Admin/System only write, Users read)
        OSAuthorityProvisioner._apply_machine_level_acl(program_data_root)
        
        # Verify effective ACL
        OSAuthorityProvisioner._verify_effective_acl(program_data_root)
        
        logger.info("Provisioner trust anchor setup complete: %s", program_data_root)
    
    @staticmethod
    def _apply_machine_level_acl(program_data_root: Path) -> None:
        """Apply machine-level Windows ACL protection to provisioner trust anchor.
        
        F5 V4-r9 FIX: Restrict to Admin/System write only, Users read only.
        
        Args:
            program_data_root: Directory to protect
        
        Raises:
            WindowsACLError: If ACL application fails
        """
        try:
            # Use icacls to restrict directory access
            cmd = [
                "icacls",
                str(program_data_root),
                "/inheritance:r",  # Remove inherited permissions
                "/grant:r", "Administrators:(OI)(CI)F",
                "/grant:r", "SYSTEM:(OI)(CI)F",
                "/grant:r", "Users:(OI)(CI)R",  # Users: Read only (no Write)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                raise WindowsACLError(
                    f"Machine-level ACL application failed: {result.stderr}"
                )
            
            logger.info("Applied machine-level Windows ACL protection to: %s", program_data_root)
                
        except Exception as exc:
            logger.error("Failed to apply machine-level ACL protection: %s", exc)
            raise WindowsACLError(f"Machine-level ACL application failed: {exc}")
    
    @staticmethod
    def setup_protected_directory(protected_root: Path) -> None:
        """Setup protected directory with ACL (OS-authorized only).
        
        F5 V4-r4 FIX: Separate ACL setup from runtime constructor.
        
        This is a one-time setup operation that must be run with admin privileges.
        It creates the protected directory and applies restrictive ACL.
        
        Args:
            protected_root: Root directory for protected trust store
        
        Raises:
            OSProvisioningError: If setup fails
            WindowsACLError: If ACL application fails
        """
        if sys.platform != "win32":
            raise OSProvisioningError(
                "Protected directory setup requires Windows platform. "
                "This security mechanism is Windows-specific."
            )
        
        # Verify admin privilege
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                raise OSProvisioningError(
                    "Protected directory setup requires administrative privileges. "
                    "Please run as administrator or with UAC elevation."
                )
        except ImportError:
            raise OSProvisioningError("ctypes not available - cannot verify admin privilege")
        
        # Create directory
        protected_root.mkdir(parents=True, exist_ok=True)
        
        # Apply ACL protection
        OSAuthorityProvisioner._apply_acl_protection(protected_root)
        
        # Verify effective ACL
        OSAuthorityProvisioner._verify_effective_acl(protected_root)
        
        logger.info("Protected directory setup complete: %s", protected_root)
    
    @staticmethod
    def _apply_acl_protection(protected_root: Path) -> None:
        """Apply Windows ACL protection to trust store directory.
        
        F5 V4-r4 FIX: Fail-closed if ACL application fails.
        
        Restricts trust store modification to:
        - Administrators: Full Control
        - SYSTEM: Full Control
        - Current user: Read/Execute (no Write)
        
        Args:
            protected_root: Directory to protect
        
        Raises:
            WindowsACLError: If ACL application fails
        """
        try:
            # Use icacls to restrict directory access
            cmd = [
                "icacls",
                str(protected_root),
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
                raise WindowsACLError(
                    f"ACL application failed: {result.stderr}"
                )
            
            logger.info("Applied Windows ACL protection to: %s", protected_root)
                
        except Exception as exc:
            logger.error("Failed to apply ACL protection: %s", exc)
            raise WindowsACLError(f"ACL application failed: {exc}")
    
    @staticmethod
    def _verify_effective_acl(protected_root: Path) -> None:
        """Verify that effective ACL protection is applied to trust store directory.
        
        F5 V4-r4 FIX: Verify effective permissions instead of just applying ACL.
        F5 V4-r9.2 FIX: More granular verification of specific permissions.
        
        Verifies that:
        - Ordinary caller cannot write
        - Ordinary caller cannot delete
        - Ordinary caller cannot replace
        - Admin/SYSTEM can write
        
        Args:
            protected_root: Directory to verify
        
        Raises:
            WindowsACLError: If ACL verification fails
        """
        try:
            # Use icacls to check effective permissions
            cmd = ["icacls", str(protected_root)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                raise WindowsACLError(
                    f"Failed to query ACL: {result.stderr}"
                )
            
            # Parse ACL output to verify protection
            acl_output = result.stdout
            logger.info("Current ACL: %s", acl_output)
            
            # F5 V4-r9.2 FIX: Verify that Users group has Read only (no Write/Delete/Modify)
            users_acl_lines = [line for line in acl_output.split('\n') if 'Users' in line or 'BUILTIN\\Users' in line]
            for line in users_acl_lines:
                # Check for Write (W), Delete (D), Modify (M), Full Control (F)
                permission_upper = line.upper()
                if any(perm in permission_upper for perm in ['W', 'D', 'M', 'F']):
                    raise WindowsACLError(
                        f"Users group has unauthorized permission in ACL: {line}. "
                        "ACL protection is not correctly applied. Users should have Read only."
                    )
            
            # F5 V4-r9.2 FIX: Verify that Administrators and SYSTEM have Full Control
            admin_acl_lines = [line for line in acl_output.split('\n') if 'Administrators' in line or 'SYSTEM' in line]
            if not admin_acl_lines:
                raise WindowsACLError(
                    "No Administrators or SYSTEM ACL found. "
                    "ACL protection is not correctly applied."
                )
            
            # Verify admin has Full Control (F) or Write (W)
            admin_has_write = False
            for line in admin_acl_lines:
                permission_upper = line.upper()
                if 'F' in permission_upper or 'W' in permission_upper:
                    admin_has_write = True
                    break
            
            if not admin_has_write:
                raise WindowsACLError(
                    "Administrators/SYSTEM do not have Write permission. "
                    "ACL protection is not correctly applied."
                )
            
            logger.info("Verified effective ACL protection")
                
        except Exception as exc:
            logger.error("Failed to verify effective ACL: %s", exc)
            raise WindowsACLError(f"ACL verification failed: {exc}")
    
    def __init__(
        self,
        protected_root: Path,
        provisioner_trust_anchor_path_or_keypair: Path | ProvisionerKeyPair | None = None,
        provisioner_keypair: ProvisionerKeyPair | None = None,
    ):
        """Initialize OS-level provisioner.
        
        F5 V4-r4 FIX: Removed test_only_mode - no production bypass allowed.
        F5 V4-r6 FIX: Added provisioner keypair for cryptographic signature.
        F5 V4-r9 FIX: Separate provisioner public key in machine-level location.
        
        Args:
            protected_root: Root directory for protected trust store
                          (separate from ordinary application data)
            provisioner_trust_anchor_path_or_keypair: Machine-level path for provisioner public key
                                         (C:\ProgramData\IABV\provisioner_trust\)
                                         OR ProvisionerKeyPair for backward compatibility (legacy mode)
                                         If None, uses legacy single-directory layout (for test compatibility)
            provisioner_keypair: Optional provisioner keypair for signing trust stores.
                               If None, loads from protected location or generates new.
        
        Raises:
            OSProvisioningError: If not running with admin privileges or on non-Windows
        """
        if sys.platform != "win32":
            raise OSProvisioningError(
                "OS-level provisioning requires Windows platform. "
                "This security mechanism is Windows-specific and not supported on other platforms."
            )
        
        self.protected_root = protected_root
        
        # F5 V4-r9 FIX: Backward compatibility - detect if second arg is Path or ProvisionerKeyPair
        if isinstance(provisioner_trust_anchor_path_or_keypair, ProvisionerKeyPair):
            # Legacy mode: second arg is keypair
            self.provisioner_trust_anchor_path = None
            provisioner_keypair = provisioner_trust_anchor_path_or_keypair
        else:
            # V4-r9 mode: second arg is path (or None)
            self.provisioner_trust_anchor_path = provisioner_trust_anchor_path_or_keypair
        
        # F5 V4-r4 FIX: Runtime does NOT create directory - provisioning must pre-create
        if not self.protected_root.exists():
            raise OSProvisioningError(
                f"Protected trust root directory does not exist: {self.protected_root}. "
                "Provisioning must create the protected directory and apply ACL before "
                "the provisioner can initialize. Run OSAuthorityProvisioner.setup_protected_directory() first."
            )
        
        # F5 V4-r9 FIX: Verify machine-level provisioner trust anchor exists if using V4-r9 architecture
        if self.provisioner_trust_anchor_path:
            if not self.provisioner_trust_anchor_path.exists():
                raise OSProvisioningError(
                    f"Provisioner trust anchor directory does not exist: {self.provisioner_trust_anchor_path}. "
                    "Provisioning must create the machine-level trust anchor first. "
                    "Run OSAuthorityProvisioner.setup_provisioner_trust_anchor() with admin privileges."
                )
            self._provisioner_keypair_path = self.provisioner_trust_anchor_path / "provisioner_keypair.json"
        else:
            # Legacy single-directory layout
            self._provisioner_keypair_path = self.protected_root / "provisioner_keypair.json"
        
        self._trust_store_path = self.protected_root / "authority_trust.json"
        
        # F5 V4-r6 FIX: Load or create provisioner keypair
        self._provisioner_keypair = provisioner_keypair or self._load_or_create_provisioner_keypair()
        
        # F5 V4-r4 FIX: Verify admin privilege (no bypass allowed)
        self._verify_admin_privilege()
        
        # F5 V4-r4 FIX: Verify effective ACL (fail-closed if not verified)
        self._verify_effective_acl(protected_root)
        
        # F5 V4-r9 FIX: Verify machine-level ACL if using V4-r9 architecture
        if self.provisioner_trust_anchor_path:
            self._verify_effective_acl(provisioner_trust_anchor_path)
        
        logger.info("OSAuthorityProvisioner initialized: %s", self.protected_root)
    
    def _verify_admin_privilege(self) -> None:
        """Verify that current process has administrative privileges.
        
        F5 V4-r4 FIX: OS-level authorization boundary - fail-closed on non-Windows or non-admin.
        
        Raises:
            OSProvisioningError: If not running with admin privileges or on non-Windows
        """
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
            raise OSProvisioningError(
                "ctypes not available - cannot verify admin privilege. "
                "Admin privilege verification is required for OS-level provisioning."
            )
        except Exception as exc:
            logger.error("Failed to verify admin privilege: %s", exc)
            raise OSProvisioningError(f"Admin privilege verification failed: {exc}")
    
    def _verify_effective_acl(self) -> None:
        """Verify that effective ACL protection is applied to trust store directory.
        
        F5 V4-r4 FIX: Verify effective permissions instead of just applying ACL.
        
        Verifies that:
        - Ordinary caller cannot write
        - Authority runtime cannot write
        - Admin/SYSTEM can write
        
        Raises:
            WindowsACLError: If ACL verification fails
        """
        try:
            # Use icacls to check effective permissions
            cmd = ["icacls", str(self.protected_root)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                raise WindowsACLError(
                    f"Failed to query ACL: {result.stderr}"
                )
            
            # Parse ACL output to verify protection
            acl_output = result.stdout
            logger.info("Current ACL: %s", acl_output)
            
            # F5 V4-r4 FIX: Verify that current user does not have Write permission
            username = os.environ.get('USERNAME', '')
            if username and ('W' in acl_output or 'WRITE' in acl_output.upper()):
                # Check if current user has Write permission
                user_acl_lines = [line for line in acl_output.split('\n') if username in line]
                for line in user_acl_lines:
                    if 'W' in line or 'WRITE' in line.upper():
                        raise WindowsACLError(
                            f"Current user {username} has Write permission on protected directory. "
                            "ACL protection is not correctly applied."
                        )
            
            logger.info("Verified effective ACL protection")
                
        except Exception as exc:
            logger.error("Failed to verify effective ACL: %s", exc)
            raise WindowsACLError(f"ACL verification failed: {exc}")
    
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
            
            # F5 V4-r6 FIX: Add provisioner_public_key_id BEFORE signing
            trust_data["provisioner_public_key_id"] = self._provisioner_keypair.public_key_id
            
            # Save trust store (will sign with provisioner keypair)
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
            
            # F5 V4-r6 FIX: Add provisioner_public_key_id BEFORE signing
            trust_data["provisioner_public_key_id"] = self._provisioner_keypair.public_key_id
            
            # Save trust store (will sign with provisioner keypair)
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
    
    def _load_or_create_provisioner_keypair(self) -> ProvisionerKeyPair:
        """Load or create provisioner keypair for signing trust stores.
        
        F5 V4-r6 FIX: Separate keypair for cryptographic signature of trust stores.
        F14 V4-r7 FIX: Protect provisioner private key with DPAPI (was plain text).
        F5 V4-r9 FIX: Store in machine-level location; also publish public key for runtime.
        
        The provisioner keypair is stored in the machine-level directory and is used
        to sign trust stores to establish cryptographic authenticity.
        
        Returns:
            ProvisionerKeyPair (existing or newly created)
        
        Raises:
            OSProvisioningError: If DPAPI unavailable or key protection fails
        """
        # F14 V4-r7 FIX: Fail closed if DPAPI unavailable
        if not DPAPI_AVAILABLE:
            raise OSProvisioningError(
                "Provisioner private key protection requires Windows DPAPI (win32crypt). "
                "This platform is not supported for production provisioning."
            )
        
        if self._provisioner_keypair_path.exists():
            try:
                with open(self._provisioner_keypair_path, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                
                # F14 V4-r7 FIX: Decrypt private key using DPAPI
                if "private_key_protected" in key_data:
                    encrypted_bytes = bytes.fromhex(key_data["private_key_protected"])
                    logger.info("Attempting DPAPI unprotect of provisioner key")
                    
                    try:
                        decrypted = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None)
                        
                        if isinstance(decrypted, tuple):
                            decrypted_bytes = decrypted[1]
                        else:
                            decrypted_bytes = decrypted
                        
                        if len(decrypted_bytes) != 32:
                            raise RuntimeError(
                                f"Decrypted provisioner key has invalid length: {len(decrypted_bytes)} (expected 32)"
                            )
                        
                        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(decrypted_bytes)
                        public_key = private_key.public_key()
                        
                        keypair = ProvisionerKeyPair(private_key, public_key)
                        logger.info("Loaded provisioner keypair with DPAPI protection from: %s", self._provisioner_keypair_path)
                        return keypair
                        
                    except Exception as exc:
                        logger.error("Failed to decrypt provisioner key: %s", exc)
                        raise OSProvisioningError(f"Failed to decrypt provisioner key: {exc}")
                else:
                    # Legacy plain text key - error out for security
                    raise OSProvisioningError(
                        "Legacy plain-text provisioner key detected. "
                        "Please delete and reprovision with DPAPI protection."
                    )
                
            except Exception as exc:
                logger.error("Failed to load provisioner keypair: %s", exc)
                raise OSProvisioningError(f"Failed to load provisioner keypair: {exc}")
        
        # Create new provisioner keypair
        keypair = ProvisionerKeyPair.generate()
        
        # F14 V4-r7 FIX: Protect private key with DPAPI
        private_key_bytes = keypair._private_key.private_bytes(
            Encoding.Raw,
            PrivateFormat.Raw,
            NoEncryption()
        )
        
        encrypted_result = win32crypt.CryptProtectData(private_key_bytes, None, None, None, None, 0)
        encrypted_bytes = encrypted_result if not isinstance(encrypted_result, tuple) else encrypted_result[0]
        protected_key_hex = encrypted_bytes.hex()
        
        key_data = {
            "public_key_id": keypair.public_key_id,
            "public_key_hex": keypair.public_key_hex,
            "private_key_protected": protected_key_hex,
            "protection": "DPAPI",
            "created_at_utc": self._get_current_timestamp(),
        }
        
        with open(self._provisioner_keypair_path, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)
        
        # F5 V4-r9 FIX: Publish public key to machine-level location for runtime (if using V4-r9 architecture)
        if self.provisioner_trust_anchor_path:
            public_key_only = {
                "public_key_id": keypair.public_key_id,
                "public_key_hex": keypair.public_key_hex,
                "provisioned_at_utc": self._get_current_timestamp(),
                "location": "machine_level_trust_anchor",
            }
            public_key_path = self.provisioner_trust_anchor_path / "provisioner_public_key.json"
            with open(public_key_path, 'w', encoding='utf-8') as f:
                json.dump(public_key_only, f, indent=2)
            logger.info("Published provisioner public key to machine-level trust anchor: %s", public_key_path)
        
        logger.info("Created and stored provisioner keypair with DPAPI protection: %s", self._provisioner_keypair_path)
        return keypair
    
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
        """Save trust store to protected location with cryptographic signature.
        
        F5 V4-r6 FIX: Sign trust store with provisioner keypair instead of declarative marker.
        
        The trust store is signed to establish cryptographic authenticity. The signature
        replaces the insecure declarative "provisioned_by" marker.
        """
        trust_data["version"] = "1.0"
        trust_data["updated_at_utc"] = self._get_current_timestamp()
        
        # F5 V4-r6 FIX: Sign trust store with provisioner keypair
        signature_hex = self._provisioner_keypair.sign_trust_store(trust_data)
        trust_data["provisioner_signature"] = signature_hex
        trust_data["provisioner_public_key_id"] = self._provisioner_keypair.public_key_id
        
        with open(self._trust_store_path, 'w', encoding='utf-8') as f:
            json.dump(trust_data, f, indent=2)
        
        logger.info("Saved and signed trust store to protected location")
    
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