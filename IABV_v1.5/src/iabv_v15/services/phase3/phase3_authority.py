"""Phase 3 Authority Extensions.

This module extends the AuthorityService with Phase 3 specific handlers
for Ed25519-based proof-of-possession authorization.

Key properties:
- REQUEST_JOIN: Pin public_key, generate join_token
- REQUEST_CHALLENGE: Generate challenge, return pinned public_key
- REDEEM_JOIN: Verify Ed25519 signature, redeem join token
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from typing import Any, Optional

from iabv_v15.services.phase3.phase3_protocol import (
    RequestJoinRequest,
    RequestJoinResponse,
    RequestChallengeRequest,
    RequestChallengeResponse,
    RedeemJoinRequest,
    RedeemJoinResponse,
    generate_challenge,
    verify_challenge_freshness,
)
from iabv_v15.services.phase3.ed25519_keys import (
    public_key_from_hex,
    public_key_from_base64,
    verify_signature,
)
from iabv_v15.services.phase3.authentication_layer import AuthenticationLayer


class Phase3AuthorityExtension:
    """Phase 3 extension for AuthorityService."""
    
    def __init__(self, storage_root: str, db_connection: sqlite3.Connection):
        """Initialize Phase 3 extension.
        
        Args:
            storage_root: Directory for persistent state
            db_connection: Connection to run_records database (canonical generation source)
        """
        from pathlib import Path
        self._storage_root = Path(storage_root)
        self._db_connection = db_connection
        self._join_state_db = self._storage_root / "phase3_join_state.db"
        self._challenge_state_db = self._storage_root / "phase3_challenge_state.db"
        self._init_join_state_db()
        self._init_challenge_state_db()
        self._auth_layer = AuthenticationLayer(storage_root)
    
    def _init_join_state_db(self) -> None:
        """Initialize join state store (SQLite)."""
        conn = sqlite3.connect(str(self._join_state_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS join_tokens (
                join_token TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                public_key TEXT NOT NULL,
                pinned INTEGER NOT NULL DEFAULT 0,
                redeemed INTEGER NOT NULL DEFAULT 0,
                generation INTEGER NOT NULL,
                pinned_at REAL NOT NULL,
                redeemed_at REAL,
                consumer_pid INTEGER,
                task_context TEXT,
                episode_id TEXT,
                session_id TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _init_challenge_state_db(self) -> None:
        """Initialize challenge state store (SQLite)."""
        conn = sqlite3.connect(str(self._challenge_state_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                challenge_id TEXT PRIMARY KEY,
                join_token TEXT NOT NULL,
                challenge TEXT NOT NULL,
                generation INTEGER NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                subject_id TEXT,
                execution_id TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_current_generation(self, execution_id: str) -> int:
        """Read canonical generation from run_records.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Current generation from run_records.generation
        """
        cursor = self._db_connection.cursor()
        cursor.execute("""
            SELECT generation
            FROM run_records
            WHERE execution_id = ?
        """, (execution_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Execution {execution_id} not found")
        
        return row[0]
    
    def handle_request_join(
        self,
        request_data: dict[str, Any],
        client_pid: int,
        execution_id: str
    ) -> dict[str, Any]:
        """Handle REQUEST_JOIN request.
        
        DEPRECATED: This legacy path is being replaced by the unified transport
        path in AuthorityService.handle_phase3_request_join(). Use the new
        authenticated transport boundary instead.
        
        Phase 3 Unified Path:
        - AuthorityService.handle_phase3_request_join()
        - Uses OS-observed client_pid from transport layer
        - Uses canonical authority_join_authorizations.db
        
        Args:
            request_data: Request data
            client_pid: Client process ID
            execution_id: Execution identifier for canonical generation
            
        Returns:
            Response data
        """
        import warnings
        warnings.warn(
            "Phase3AuthorityExtension.handle_request_join is DEPRECATED. "
            "Use AuthorityService.handle_phase3_request_join with authenticated transport.",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Parse request
            request = RequestJoinRequest.from_dict(request_data)
            
            # Get canonical generation
            generation = self._get_current_generation(execution_id)
            
            # Authentication: Verify caller identity
            caller_verified, caller_sid = self._auth_layer.verify_caller_identity(client_pid)
            if not caller_verified:
                return {
                    "success": False,
                    "error": "Caller identity verification failed"
                }
            
            # Authentication: Validate subject/key binding
            if not self._auth_layer.validate_subject_key_binding(
                request.subject_id,
                request.public_key,
                caller_sid
            ):
                return {
                    "success": False,
                    "error": "Subject/key binding not authorized"
                }
            
            # Generate join token
            join_token = secrets.token_urlsafe(16)
            
            # Pin public key
            pinned_at = time.time()
            
            # Store in database
            conn = sqlite3.connect(str(self._join_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO join_tokens 
                (join_token, subject_id, public_key, pinned, redeemed, generation, 
                 pinned_at, consumer_pid, task_context, episode_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                join_token,
                request.subject_id,
                request.public_key,
                1,  # pinned
                0,  # not redeemed
                generation,
                pinned_at,
                client_pid,
                request.task_context,
                request.episode_id,
                request.session_id
            ))
            
            conn.commit()
            conn.close()
            
            # Return response
            return RequestJoinResponse(
                join_token=join_token,
                subject_id=request.subject_id,
                pinned=True,
                generation=generation,
                pinned_at=pinned_at
            ).to_dict()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_request_challenge(
        self,
        request_data: dict[str, Any],
        client_pid: int,
        execution_id: str
    ) -> dict[str, Any]:
        """Handle REQUEST_CHALLENGE request.
        
        DEPRECATED: This legacy path is being replaced by the unified transport
        path in AuthorityService.handle_phase3_request_challenge(). Use the new
        authenticated transport boundary instead.
        
        Phase 3 Unified Path:
        - AuthorityService.handle_phase3_request_challenge()
        - Uses OS-observed client_pid from transport layer
        - Uses canonical authority_challenge_state.db
        
        Args:
            request_data: Request data
            client_pid: Client process ID
            execution_id: Execution identifier for canonical generation
            
        Returns:
            Response data
        """
        import warnings
        warnings.warn(
            "Phase3AuthorityExtension.handle_request_challenge is DEPRECATED. "
            "Use AuthorityService.handle_phase3_request_challenge with authenticated transport.",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Parse request
            request = RequestChallengeRequest.from_dict(request_data)
            
            # Get canonical generation
            generation = self._get_current_generation(execution_id)
            
            # Verify join token exists and is not redeemed
            conn = sqlite3.connect(str(self._join_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT public_key, subject_id, consumer_pid, generation, redeemed
                FROM join_tokens
                WHERE join_token = ?
            """, (request.join_token,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {
                    "success": False,
                    "error": "Join token not found"
                }
            
            public_key, subject_id, record_pid, record_generation, redeemed = row
            
            # Verify not redeemed
            if redeemed:
                return {
                    "success": False,
                    "error": "Join token already redeemed"
                }
            
            # Verify generation matches canonical
            if record_generation != generation:
                return {
                    "success": False,
                    "error": "Generation mismatch"
                }
            
            # Generate challenge
            challenge = generate_challenge()
            challenge_issued_at = time.time()
            challenge_expires_at = challenge_issued_at + 300  # 5 minutes
            
            # Store challenge
            challenge_id = secrets.token_urlsafe(16)
            
            conn = sqlite3.connect(str(self._challenge_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO challenges 
                (challenge_id, join_token, challenge, generation, issued_at, expires_at, 
                 subject_id, execution_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                challenge_id,
                request.join_token,
                challenge,
                generation,
                challenge_issued_at,
                challenge_expires_at,
                subject_id,
                request.execution_id
            ))
            
            conn.commit()
            conn.close()
            
            # Return response with pinned public key
            return RequestChallengeResponse(
                challenge=challenge,
                pinned_public_key=public_key,
                generation=generation,
                challenge_issued_at=challenge_issued_at,
                challenge_expires_at=challenge_expires_at
            ).to_dict()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_redeem_join(
        self,
        request_data: dict[str, Any],
        client_pid: int,
        execution_id: str
    ) -> dict[str, Any]:
        """Handle REDEEM_JOIN request.
        
        DEPRECATED: This legacy path is being replaced by the unified transport
        path in AuthorityService.handle_phase3_redeem_join(). Use the new
        authenticated transport boundary instead.
        
        Phase 3 Unified Path:
        - AuthorityService.handle_phase3_redeem_join()
        - Uses OS-observed client_pid from transport layer
        - Uses canonical authority_join_authorizations.db and authority_challenge_state.db
        
        Args:
            request_data: Request data
            client_pid: Client process ID
            execution_id: Execution identifier for canonical generation
            
        Returns:
            Response data
        """
        import warnings
        warnings.warn(
            "Phase3AuthorityExtension.handle_redeem_join is DEPRECATED. "
            "Use AuthorityService.handle_phase3_redeem_join with authenticated transport.",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Parse request
            request = RedeemJoinRequest.from_dict(request_data)
            
            # Get canonical generation
            generation = self._get_current_generation(execution_id)
            
            # Verify join token exists and get pinned public key
            conn = sqlite3.connect(str(self._join_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT public_key, subject_id, consumer_pid, generation, redeemed
                FROM join_tokens
                WHERE join_token = ?
            """, (request.join_token,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {
                    "success": False,
                    "error": "Join token not found"
                }
            
            public_key_str, subject_id, record_pid, record_generation, redeemed = row
            
            # Verify not redeemed
            if redeemed:
                conn.close()
                return {
                    "success": False,
                    "error": "Join token already redeemed"
                }
            
            # Verify generation matches canonical
            if record_generation != generation:
                conn.close()
                return {
                    "success": False,
                    "error": "Generation mismatch"
                }
            
            # Get challenge
            cursor.execute("""
                SELECT challenge, issued_at, expires_at
                FROM challenges
                WHERE join_token = ?
                ORDER BY issued_at DESC
                LIMIT 1
            """, (request.join_token,))
            
            challenge_row = cursor.fetchone()
            
            if not challenge_row:
                conn.close()
                return {
                    "success": False,
                    "error": "Challenge not found"
                }
            
            challenge_str, issued_at, expires_at = challenge_row
            
            # Verify challenge freshness
            if not verify_challenge_freshness(challenge_str):
                conn.close()
                return {
                    "success": False,
                    "error": "Challenge expired"
                }
            
            # Convert public key to bytes
            try:
                public_key = public_key_from_hex(public_key_str)
            except ValueError:
                try:
                    public_key = public_key_from_base64(public_key_str)
                except ValueError:
                    conn.close()
                    return {
                        "success": False,
                        "error": "Invalid public key format"
                    }
            
            # Verify signature
            signature_bytes = bytes.fromhex(request.signature)
            challenge_bytes = challenge_str.encode('utf-8')
            
            if not verify_signature(public_key, challenge_bytes, signature_bytes):
                conn.close()
                return {
                    "success": False,
                    "error": "Invalid signature"
                }
            
            # Atomic redeem
            cursor.execute("""
                UPDATE join_tokens
                SET redeemed = 1, redeemed_at = ?
                WHERE join_token = ? 
                  AND redeemed = 0 
                  AND generation = ?
            """, (time.time(), request.join_token, generation))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    "success": False,
                    "error": "Join token already redeemed or expired"
                }
            
            conn.commit()
            conn.close()
            
            # Generate membership ID
            membership_id = secrets.token_urlsafe(16)
            
            # Return response
            return RedeemJoinResponse(
                redeemed=True,
                redeemed_at=time.time(),
                membership_id=membership_id
            ).to_dict()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
