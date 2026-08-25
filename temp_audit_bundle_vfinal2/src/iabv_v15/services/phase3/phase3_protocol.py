"""Phase 3 Authorization Protocol Extensions.

This module extends the Phase 2 authority protocol with Phase 3 specific messages
for Ed25519-based proof-of-possession authorization.

Key properties:
- REQUEST_JOIN: Parent sends public_key to Authority for pinning
- REQUEST_CHALLENGE: Child requests challenge from Authority
- REDEEM_JOIN: Child redeems join token with Ed25519 signature
- Authority pins public_key during REQUEST_JOIN
- Authority uses pinned public_key for signature verification
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Optional
import time
import secrets


# ── Phase 3 Request Contracts ────────────────────────────────────────────────────

@dataclass
class RequestJoinRequest:
    """REQUEST_JOIN request for Phase 3.
    
    CALLER REQUEST FIELDS (caller-provided):
    - subject_id: Subject identifier
    - public_key: Ed25519 public key (hex or base64)
    - task_context: Task/development objective context
    - episode_id: Optional episode identifier
    - session_id: Optional session identifier
    
    AUTHORITY DERIVED FIELDS (authority-provided in response):
    - join_token: Authority-owned join token
    - subject_id: Authority-validated subject identifier
    - pinned: Whether public_key was successfully pinned
    - generation: Authority generation
    """
    subject_id: str
    public_key: str
    task_context: Optional[str] = None
    episode_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "subject_id": self.subject_id,
            "public_key": self.public_key,
            "task_context": self.task_context,
            "episode_id": self.episode_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestJoinRequest":
        """Create from dictionary for IPC."""
        return cls(
            subject_id=data["subject_id"],
            public_key=data["public_key"],
            task_context=data.get("task_context"),
            episode_id=data.get("episode_id"),
            session_id=data.get("session_id")
        )


@dataclass
class RequestJoinResponse:
    """REQUEST_JOIN response for Phase 3.
    
    AUTHORITY DERIVED FIELDS:
    - join_token: Authority-owned join token
    - subject_id: Authority-validated subject identifier
    - pinned: Whether public_key was successfully pinned
    - generation: Authority generation
    - pinned_at: Authority timestamp
    """
    join_token: str
    subject_id: str
    pinned: bool
    generation: int
    pinned_at: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "join_token": self.join_token,
            "subject_id": self.subject_id,
            "pinned": self.pinned,
            "generation": self.generation,
            "pinned_at": self.pinned_at
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestJoinResponse":
        """Create from dictionary for IPC."""
        return cls(
            join_token=data["join_token"],
            subject_id=data["subject_id"],
            pinned=data["pinned"],
            generation=data["generation"],
            pinned_at=data["pinned_at"]
        )


@dataclass
class RequestChallengeRequest:
    """REQUEST_CHALLENGE request for Phase 3.
    
    CALLER REQUEST FIELDS (caller-provided):
    - join_token: Authority-owned join token (from REQUEST_JOIN)
    - subject_id: Subject identifier
    - execution_id: Execution identifier
    
    AUTHORITY DERIVED FIELDS (authority-provided in response):
    - challenge: Authority-generated challenge (nonce + timestamp)
    - pinned_public_key: Pinned public key (for verification)
    - generation: Authority generation
    - challenge_issued_at: Authority timestamp
    """
    join_token: str
    subject_id: str
    execution_id: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "join_token": self.join_token,
            "subject_id": self.subject_id,
            "execution_id": self.execution_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestChallengeRequest":
        """Create from dictionary for IPC."""
        return cls(
            join_token=data["join_token"],
            subject_id=data["subject_id"],
            execution_id=data["execution_id"]
        )


@dataclass
class RequestChallengeResponse:
    """REQUEST_CHALLENGE response for Phase 3.
    
    AUTHORITY DERIVED FIELDS:
    - challenge: Authority-generated challenge (nonce + timestamp)
    - pinned_public_key: Pinned public key (for verification)
    - generation: Authority generation
    - challenge_issued_at: Authority timestamp
    - challenge_expires_at: Authority timestamp
    """
    challenge: str
    pinned_public_key: str
    generation: int
    challenge_issued_at: float
    challenge_expires_at: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "challenge": self.challenge,
            "pinned_public_key": self.pinned_public_key,
            "generation": self.generation,
            "challenge_issued_at": self.challenge_issued_at,
            "challenge_expires_at": self.challenge_expires_at
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestChallengeResponse":
        """Create from dictionary for IPC."""
        return cls(
            challenge=data["challenge"],
            pinned_public_key=data["pinned_public_key"],
            generation=data["generation"],
            challenge_issued_at=data["challenge_issued_at"],
            challenge_expires_at=data["challenge_expires_at"]
        )


@dataclass
class RedeemJoinRequest:
    """REDEEM_JOIN request for Phase 3.
    
    CALLER REQUEST FIELDS (caller-provided):
    - join_token: Authority-owned join token
    - subject_id: Subject identifier
    - execution_id: Execution identifier
    - signature: Ed25519 signature of challenge
    
    AUTHORITY DERIVED FIELDS (authority retrieves from canonical state):
    - pinned_public_key: From join state
    - challenge: From challenge state
    - generation: Authority generation
    - redeemed: Whether join was successfully redeemed
    - redeemed_at: Authority timestamp (if redeemed)
    
    NOTE: The authority derives/retrieves all authoritative fields from
    canonical state. The client does NOT resend authoritative fields.
    """
    join_token: str
    subject_id: str
    execution_id: str
    signature: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "join_token": self.join_token,
            "subject_id": self.subject_id,
            "execution_id": self.execution_id,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RedeemJoinRequest":
        """Create from dictionary for IPC."""
        return cls(
            join_token=data["join_token"],
            subject_id=data["subject_id"],
            execution_id=data["execution_id"],
            signature=data["signature"]
        )


@dataclass
class RedeemJoinResponse:
    """REDEEM_JOIN response for Phase 3.
    
    AUTHORITY DERIVED FIELDS:
    - redeemed: Whether join was successfully redeemed
    - redeemed_at: Authority timestamp (if redeemed)
    - membership_id: Authority-owned membership identifier (if redeemed)
    """
    redeemed: bool
    redeemed_at: Optional[float] = None
    membership_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "redeemed": self.redeemed,
            "redeemed_at": self.redeemed_at,
            "membership_id": self.membership_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RedeemJoinResponse":
        """Create from dictionary for IPC."""
        return cls(
            redeemed=data["redeemed"],
            redeemed_at=data.get("redeemed_at"),
            membership_id=data.get("membership_id")
        )


# ── Challenge Generation ───────────────────────────────────────────────────────────

def generate_challenge() -> str:
    """Generate a challenge for Ed25519 signature.
    
    The challenge includes:
    - Nonce (cryptographically random)
    - Timestamp (to prevent replay)
    
    Returns:
        Challenge string (nonce:timestamp format)
    """
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    return f"{nonce}:{timestamp}"


def parse_challenge(challenge: str) -> tuple[str, int]:
    """Parse a challenge string.
    
    Args:
        challenge: Challenge string (nonce:timestamp format)
        
    Returns:
        (nonce, timestamp) tuple
    """
    parts = challenge.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid challenge format")
    
    nonce = parts[0]
    timestamp = int(parts[1])
    
    return nonce, timestamp


def verify_challenge_freshness(challenge: str, max_age_seconds: int = 300) -> bool:
    """Verify that a challenge is fresh (not replayed).
    
    Args:
        challenge: Challenge string (nonce:timestamp format)
        max_age_seconds: Maximum age of challenge in seconds
        
    Returns:
        True if challenge is fresh, False otherwise
    """
    try:
        nonce, timestamp = parse_challenge(challenge)
        current_time = int(time.time())
        age = current_time - timestamp
        return 0 <= age <= max_age_seconds
    except Exception:
        return False
