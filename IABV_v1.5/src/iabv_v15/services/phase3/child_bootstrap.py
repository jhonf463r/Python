"""Child Credential Bootstrap for Phase 3.

This module implements the child-side credential bootstrap logic for Phase 3.

Key properties:
- Credential read is FIRST meaningful operation
- Read from stdin (anonymous pipe)
- Validate credential format
- Construct Ed25519 private key
- Close stdin immediately
- Never log private_key
"""

from __future__ import annotations

import sys
from typing import Optional

from iabv_v15.services.phase3.credential_transport import read_credential_from_stdin
from iabv_v15.services.phase3.ed25519_keys import (
    private_key_from_hex,
    private_key_from_base64
)


class CredentialBootstrapError(Exception):
    """Credential bootstrap error."""
    pass


def bootstrap_credential() -> bytes:
    """Bootstrap credential from stdin (child process).
    
    This is the FIRST meaningful operation in the child process.
    Reads credential from stdin, validates format, and returns private key bytes.
    
    Returns:
        Ed25519 private key bytes (32 bytes)
        
    Raises:
        CredentialBootstrapError: If credential is invalid
    """
    try:
        # Read credential from stdin (first operation)
        credential_data = read_credential_from_stdin()
        
        # Try to decode as hex first
        try:
            private_key = private_key_from_hex(credential_data.decode('utf-8'))
        except ValueError:
            # Try base64
            try:
                private_key = private_key_from_base64(credential_data.decode('utf-8'))
            except Exception:
                raise CredentialBootstrapError(
                    "Invalid credential format: expected hex or base64"
                )
        
        # Validate private key length (Ed25519 private key is 32 bytes)
        if len(private_key) != 32:
            raise CredentialBootstrapError(
                f"Invalid private key length: expected 32 bytes, got {len(private_key)}"
            )
        
        return private_key
        
    except Exception as e:
        raise CredentialBootstrapError(f"Credential bootstrap failed: {e}")


def bootstrap_and_validate() -> bytes:
    """Bootstrap credential and validate format.
    
    This is the main entry point for child credential bootstrap.
    
    Returns:
        Ed25519 private key bytes (32 bytes)
    """
    private_key = bootstrap_credential()
    
    # Additional validation can be added here
    # For example, check if the key can be loaded by cryptography library
    
    return private_key
