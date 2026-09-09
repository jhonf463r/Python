"""Test-only key backend for unit tests.

F14 V4-r4 FIX: Test adapter for unit tests that cannot use DPAPI.

This module provides a fake key backend for unit tests that cannot run
on Windows with actual DPAPI. This is explicitly marked as TEST-ONLY and
must not be used in production runtime configuration.

The test backend uses plaintext key storage (INSECURE) and is only acceptable
for unit tests that do not involve real security scenarios.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

logger = logging.getLogger(__name__)


@dataclass
class TestAuthorityKeyPair:
    """Test-only authority keypair (INSECURE - for testing only)."""
    
    _private_key: ed25519.Ed25519PrivateKey
    _public_key: ed25519.Ed25519PublicKey
    _public_key_id: str
    
    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        return self._public_key
    
    @property
    def public_key_id(self) -> str:
        return self._public_key_id
    
    @classmethod
    def generate(cls) -> "TestAuthorityKeyPair":
        """Generate a new test keypair."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_key_id = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()[:16]
        
        keypair = cls.__new__(cls)
        keypair._private_key = private_key
        keypair._public_key = public_key
        keypair._public_key_id = public_key_id
        
        return keypair


class TestKeyStorage:
    """Test-only key storage (INSECURE - for testing only).
    
    F14 V4-r4 FIX: Test adapter for unit tests.
    
    This provides a fake key backend that uses plaintext storage for testing.
    This is ONLY acceptable for unit tests and must not be used in production.
    """
    
    def __init__(self, storage_root: Path):
        """Initialize test key storage.
        
        Args:
            storage_root: Root directory for test key storage
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._keypair_file = self.storage_root / "test_authority_keypair.json"
        
        logger.warning("TEST KEY STORAGE: Using INSECURE plaintext storage for testing only")
    
    def load_or_create_keypair(self) -> TestAuthorityKeyPair:
        """Load or create test keypair (INSECURE).
        
        Returns:
            TestAuthorityKeyPair
        """
        if self._keypair_file.exists():
            try:
                with open(self._keypair_file, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                
                # Load plaintext key (INSECURE - test only)
                private_key_bytes = bytes.fromhex(key_data["private_key_hex"])
                private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
                
                # Reconstruct TestAuthorityKeyPair
                keypair = TestAuthorityKeyPair.__new__(TestAuthorityKeyPair)
                keypair._private_key = private_key
                keypair._public_key = private_key.public_key()
                keypair._public_key_id = key_data["public_key_id"]
                
                logger.info("Loaded test keypair from: %s", self._keypair_file)
                return keypair
                
            except Exception as exc:
                logger.error("Failed to load test keypair: %s", exc)
                raise RuntimeError(f"Failed to load test keypair: {exc}")
        
        # Create new test keypair
        keypair = TestAuthorityKeyPair.generate()
        
        # Store plaintext key (INSECURE - test only)
        private_key_bytes = keypair._private_key.private_bytes(
            Encoding.Raw,
            PrivateFormat.Raw,
            NoEncryption()
        )
        
        key_data = {
            "public_key_id": keypair.public_key_id,
            "private_key_hex": private_key_bytes.hex(),
            "protection": "plaintext_test_only",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(self._keypair_file, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)
        
        logger.warning("Created and stored test keypair with INSECURE plaintext: %s", self._keypair_file)
        return keypair


class TestTrustStore:
    """Test-only trust store (INSECURE - for testing only).
    
    F14 V4-r4 FIX: Test adapter for unit tests.
    F5 V4-r6 FIX: Added signature-based verification for tests.
    
    This provides a fake trust store for testing that does not require
    OS-level ACL protection. This is ONLY acceptable for unit tests.
    """
    
    def __init__(self, storage_root: Path):
        """Initialize test trust store.
        
        Args:
            storage_root: Root directory for test trust storage
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._trust_store_path = self.storage_root / "authority_trust.json"  # Match production name
        self._provisioner_keypair_path = self.storage_root / "provisioner_keypair.json"
        
        # F5 V4-r6 FIX: Create or load test provisioner keypair
        self._provisioner_keypair = self._load_or_create_provisioner_keypair()
        
        logger.warning("TEST TRUST STORE: Using INSECURE filesystem storage for testing only")
    
    def _load_or_create_provisioner_keypair(self) -> TestAuthorityKeyPair:
        """Load or create test provisioner keypair for signing trust stores.
        
        F5 V4-r6 FIX: Separate keypair for cryptographic signature.
        F14 V4-r7 FIX: Support DPAPI-protected format, fallback to plaintext for tests.
        
        Returns:
            TestAuthorityKeyPair (reused as provisioner keypair for tests)
        """
        if self._provisioner_keypair_path.exists():
            try:
                with open(self._provisioner_keypair_path, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                
                # F14 V4-r7 FIX: Support DPAPI-protected format
                if "private_key_protected" in key_data:
                    # Try DPAPI decrypt if available
                    try:
                        import win32crypt
                        encrypted_bytes = bytes.fromhex(key_data["private_key_protected"])
                        decrypted = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None)
                        decrypted_bytes = decrypted[1] if isinstance(decrypted, tuple) else decrypted
                        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(decrypted_bytes)
                    except (ImportError, Exception):
                        # Fallback: try loading legacy plaintext for test compatibility
                        logger.warning("DPAPI decrypt failed or unavailable, trying legacy plaintext for test compatibility")
                        if "private_key_hex" in key_data:
                            private_key_bytes = bytes.fromhex(key_data["private_key_hex"])
                            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
                        else:
                            raise RuntimeError("Cannot load provisioner key: neither DPAPI nor plaintext available")
                elif "private_key_hex" in key_data:
                    # Legacy plaintext format (INSECURE - test only)
                    logger.warning("Loading legacy plaintext provisioner key (INSECURE - test only)")
                    private_key_bytes = bytes.fromhex(key_data["private_key_hex"])
                    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
                else:
                    raise RuntimeError("Provisioner key has no private key data")
                
                keypair = TestAuthorityKeyPair.__new__(TestAuthorityKeyPair)
                keypair._private_key = private_key
                keypair._public_key = private_key.public()
                keypair._public_key_id = key_data["public_key_id"]
                
                logger.info("Loaded test provisioner keypair from: %s", self._provisioner_keypair_path)
                return keypair
                
            except Exception as exc:
                logger.error("Failed to load test provisioner keypair: %s", exc)
                raise RuntimeError(f"Failed to load test provisioner keypair: {exc}")
        
        # Create new provisioner keypair
        keypair = TestAuthorityKeyPair.generate()
        
        private_key_bytes = keypair._private_key.private_bytes(
            Encoding.Raw,
            PrivateFormat.Raw,
            NoEncryption()
        )
        
        # F14 V4-r7 FIX: Store as plaintext for test compatibility (INSECURE)
        # Production uses DPAPI, tests use plaintext for simplicity
        key_data = {
            "public_key_id": keypair.public_key_id,
            "public_key_hex": keypair.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
            "private_key_hex": private_key_bytes.hex(),
            "protection": "plaintext_test_only",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(self._provisioner_keypair_path, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)
        
        logger.warning("Created and stored test provisioner keypair with INSECURE plaintext: %s", self._provisioner_keypair_path)
        return keypair
    
    def _sign_trust_store(self, trust_data: dict[str, Any]) -> str:
        """Sign trust store with provisioner keypair.
        
        F5 V4-r6 FIX: Cryptographic signature instead of declarative marker.
        
        Args:
            trust_data: Trust store dictionary to sign
        
        Returns:
            Hex string of Ed25519 signature
        """
        # Make a copy and remove signature field if present before signing
        trust_copy = trust_data.copy()
        trust_copy.pop("provisioner_signature", None)
        
        # Debug logging
        canonical = json.dumps(trust_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        logger.debug(f"Signing trust store with canonical: {canonical}")
        
        signature = self._provisioner_keypair._private_key.sign(canonical)
        signature_hex = signature.hex()
        
        logger.debug(f"Generated signature: {signature_hex}")
        return signature_hex
    
    def provision_authority_key(
        self,
        key_id: str,
        public_key: ed25519.Ed25519PublicKey,
        description: str = "Test authority key",
    ) -> dict[str, Any]:
        """Provision authority key in test trust store (INSECURE).
        
        F5 V4-r6 FIX: Sign trust store with provisioner keypair.
        
        Args:
            key_id: Public key identifier
            public_key: Ed25519 public key
            description: Description
        
        Returns:
            Provisioning metadata
        """
        if not self._trust_store_path.exists():
            trust_data = {"version": "1.0", "trusted_keys": []}
        else:
            with open(self._trust_store_path, 'r', encoding='utf-8') as f:
                trust_data = json.load(f)
        
        public_key_hex = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        
        trust_data.setdefault("trusted_keys", []).append({
            "key_id": key_id,
            "public_key_hex": public_key_hex,
            "added_at_utc": datetime.now(timezone.utc).isoformat(),
            "provisioned_by": "TEST_PROVISIONER",
            "description": description,
        })
        
        # F5 V4-r6 FIX: Add provisioner_public_key_id BEFORE signing (so it's included in signature)
        trust_data["provisioner_public_key_id"] = self._provisioner_keypair.public_key_id
        
        # F5 V4-r6 FIX: Sign trust store (includes provisioner_public_key_id in signature)
        signature_hex = self._sign_trust_store(trust_data)
        trust_data["provisioner_signature"] = signature_hex
        
        with open(self._trust_store_path, 'w', encoding='utf-8') as f:
            json.dump(trust_data, f, indent=2)
        
        logger.warning("Provisioned test trust key: %s (INSECURE - test only)", key_id)
        
        return {
            "key_id": key_id,
            "description": description,
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
            "provisioned_by": "TEST_PROVISIONER",
            "status": "provisioned",
        }
    
    def load_trust_config(self) -> dict[str, Any]:
        """Load test trust configuration (INSECURE).
        
        Returns:
            Trust configuration data
        """
        if not self._trust_store_path.exists():
            return {"version": "1.0", "trusted_keys": []}
        
        with open(self._trust_store_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @property
    def provisioner_public_key(self) -> ed25519.Ed25519PublicKey:
        """Get provisioner public key for signature verification."""
        return self._provisioner_keypair.public_key


class TestAuditAuthorityProcess:
    """Test-only audit authority process (INSECURE - for testing only).
    
    F14 V4-r4 FIX: Test adapter for unit tests.
    
    This provides a fake authority process that uses the test key backend
    instead of requiring Windows DPAPI. This is ONLY acceptable for unit tests.
    """
    
    def __init__(self, storage_root: Path, key_storage: TestKeyStorage):
        """Initialize test authority process.
        
        Args:
            storage_root: Root directory for authority storage
            key_storage: Test-only key storage
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        self._keypair = key_storage.load_or_create_keypair()
        self._public_key_id = self._keypair.public_key_id
        self._public_key = self._keypair.public_key
        
        logger.warning("Test authority process initialized with INSECURE backend (testing only)")
    
    @property
    def public_key_id(self) -> str:
        return self._public_key_id
    
    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        return self._public_key