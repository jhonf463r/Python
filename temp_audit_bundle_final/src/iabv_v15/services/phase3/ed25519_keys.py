"""Ed25519 Key Management for Phase 3 Authorization.

This module implements Ed25519 key generation, signing, and verification
for the approved Round 9 design.

Key properties:
- Parent generates Ed25519 keypair
- Public key pinned by Authority during REQUEST_JOIN
- Private key delivered via anonymous pipe (stdin)
- Ed25519 signature verification against pinned public key
"""

from __future__ import annotations

import base64
from typing import Tuple
from dataclasses import dataclass

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    # Fallback will be needed if cryptography is not available


@dataclass
class Ed25519KeyPair:
    """Ed25519 key pair."""
    private_key: bytes
    public_key: bytes
    
    def get_public_key_hex(self) -> str:
        """Get public key as hex string."""
        return self.public_key.hex()
    
    def get_private_key_hex(self) -> str:
        """Get private key as hex string."""
        return self.private_key.hex()
    
    def get_public_key_base64(self) -> str:
        """Get public key as base64 string."""
        return base64.b64encode(self.public_key).decode('utf-8')
    
    def get_private_key_base64(self) -> str:
        """Get private key as base64 string."""
        return base64.b64encode(self.private_key).decode('utf-8')


def generate_ed25519_keypair() -> Ed25519KeyPair:
    """Generate a new Ed25519 key pair.
    
    Returns:
        Ed25519KeyPair containing private and public keys
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library is required for Ed25519 operations")
    
    # Generate Ed25519 key pair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Serialize keys to bytes
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return Ed25519KeyPair(
        private_key=private_bytes,
        public_key=public_bytes
    )


def sign_message(private_key: bytes, message: bytes) -> bytes:
    """Sign a message using Ed25519 private key.
    
    Args:
        private_key: Ed25519 private key (32 bytes)
        message: Message to sign
        
    Returns:
        Ed25519 signature (64 bytes)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library is required for Ed25519 operations")
    
    # Load private key
    private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
    
    # Sign message
    signature = private_key_obj.sign(message)
    
    return signature


def verify_signature(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature.
    
    Args:
        public_key: Ed25519 public key (32 bytes)
        message: Original message
        signature: Ed25519 signature (64 bytes)
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("cryptography library is required for Ed25519 operations")
    
    try:
        # Load public key
        public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        
        # Verify signature
        public_key_obj.verify(signature, message)
        
        return True
    except Exception:
        return False


def private_key_from_hex(hex_string: str) -> bytes:
    """Convert hex string to private key bytes.
    
    Args:
        hex_string: Hex string representation of private key
        
    Returns:
        Private key bytes (32 bytes)
    """
    return bytes.fromhex(hex_string)


def public_key_from_hex(hex_string: str) -> bytes:
    """Convert hex string to public key bytes.
    
    Args:
        hex_string: Hex string representation of public key
        
    Returns:
        Public key bytes (32 bytes)
    """
    return bytes.fromhex(hex_string)


def private_key_from_base64(base64_string: str) -> bytes:
    """Convert base64 string to private key bytes.
    
    Args:
        base64_string: Base64 string representation of private key
        
    Returns:
        Private key bytes (32 bytes)
    """
    return base64.b64decode(base64_string)


def public_key_from_base64(base64_string: str) -> bytes:
    """Convert base64 string to public key bytes.
    
    Args:
        base64_string: Base64 string representation of public key
        
    Returns:
        Public key bytes (32 bytes)
    """
    return base64.b64decode(base64_string)
