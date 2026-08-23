"""P0.213 V5 Phase 3 Authorization Module.

This module implements the approved Round 9 design for Phase 3 authorization,
which adds Ed25519-based proof-of-possession to prevent same-user sibling
attacks on private key delivery.

Key security properties:
- Child process owner is SYSTEM (not user SID)
- Restrictive DACL denies dangerous rights to user SID
- Private key delivered via anonymous inherited pipe (stdin)
- Public key pinned by parent during REQUEST_JOIN
- Ed25519 signature verification against pinned public key
"""

from __future__ import annotations

__version__ = "1.0.0"
