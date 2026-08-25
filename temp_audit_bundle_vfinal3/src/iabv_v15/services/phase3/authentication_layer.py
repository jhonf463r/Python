"""Authentication Layer for Phase 3 Authorization.

This module implements the authentication boundary between untrusted callers
and Phase3AuthorityExtension, enforcing caller identity verification,
AuthorizationSubject validation, and parent authority checks.

Key properties:
- OS identity verification using Windows security API
- AuthorizationSubject registry validation
- Subject → public key binding enforcement
- Parent authority verification
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional
from pathlib import Path


class AuthenticationLayer:
    """Authentication layer for Phase 3 authorization.
    
    This layer enforces:
    - OS identity verification
    - AuthorizationSubject registry validation
    - Subject → public key binding validation
    - Parent authority verification
    """
    
    def __init__(self, storage_root: str):
        """Initialize authentication layer.
        
        Args:
            storage_root: Directory for persistent state
        """
        self._storage_root = Path(storage_root)
        self._subjects_db = self._storage_root / "authorized_subjects.db"
        self._init_subjects_db()
    
    def _init_subjects_db(self) -> None:
        """Initialize authorized subjects database with lifecycle states."""
        conn = sqlite3.connect(str(self._subjects_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_subjects (
                subject_id TEXT PRIMARY KEY,
                windows_sid TEXT NOT NULL,
                allowed_public_keys TEXT NOT NULL,
                parent_authority TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                revoked_at REAL,
                revoked_by TEXT,
                revocation_reason TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_subject(
        self,
        subject_id: str,
        windows_sid: str,
        allowed_public_keys: list[str],
        parent_authority: str,
        registering_authority: str
    ) -> bool:
        """Register a new authorized subject with lifecycle state.
        
        Args:
            subject_id: Subject identifier
            windows_sid: Windows SID of authorized user
            allowed_public_keys: List of allowed public keys
            parent_authority: Parent process authority
            registering_authority: Authority performing registration
            
        Returns:
            True if registration succeeded, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self._subjects_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO authorized_subjects
                (subject_id, windows_sid, allowed_public_keys, parent_authority, lifecycle_state, created_at)
                VALUES (?, ?, ?, ?, 'ACTIVE', ?)
            """, (
                subject_id,
                windows_sid,
                json.dumps(allowed_public_keys),
                parent_authority,
                time.time()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            return False
    
    def revoke_subject(
        self,
        subject_id: str,
        revoking_authority: str,
        reason: str
    ) -> bool:
        """Revoke an authorized subject.
        
        Args:
            subject_id: Subject identifier to revoke
            revoking_authority: Authority performing revocation
            reason: Reason for revocation
            
        Returns:
            True if revocation succeeded, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self._subjects_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE authorized_subjects
                SET lifecycle_state = 'REVOKED',
                    revoked_at = ?,
                    revoked_by = ?,
                    revocation_reason = ?
                WHERE subject_id = ?
            """, (time.time(), revoking_authority, reason, subject_id))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            return False
    
    def verify_caller_identity(self, client_pid: int) -> tuple[bool, Optional[str]]:
        """Verify caller's OS identity using Windows security API.
        
        This implementation uses pywin32 to:
        1. Open process handle for client_pid
        2. Get process token
        3. Extract user SID from token
        4. Verify token is valid
        
        Args:
            client_pid: Client process ID
            
        Returns:
            (success, windows_sid) tuple
        """
        try:
            import win32api
            import win32security
            import win32con
            import winerror
            
            # Open process handle with TOKEN_QUERY access
            process_handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION,
                False,
                client_pid
            )
            
            if process_handle is None:
                return (False, None)
            
            try:
                # Get process token
                token_handle = win32security.OpenProcessToken(
                    process_handle,
                    win32con.TOKEN_QUERY
                )
                
                if token_handle is None:
                    return (False, None)
                
                try:
                    # Get token information (TokenUser)
                    token_user = win32security.GetTokenInformation(
                        token_handle,
                        win32security.TokenUser
                    )
                    
                    # Extract SID from token user
                    sid = token_user[0]
                    sid_string = str(sid)
                    
                    return (True, sid_string)
                    
                finally:
                    win32api.CloseHandle(token_handle)
                    
            finally:
                win32api.CloseHandle(process_handle)
                
        except Exception as e:
            # Log error for debugging
            import sys
            print(f"[AuthenticationLayer] verify_caller_identity failed for PID {client_pid}: {e}", file=sys.stderr)
            return (False, None)
    
    def validate_subject_key_binding(
        self,
        subject_id: str,
        public_key: str,
        caller_sid: Optional[str]
    ) -> bool:
        """Validate that subject_id and public_key are authorized for caller.
        
        Args:
            subject_id: Subject identifier
            public_key: Public key to validate
            caller_sid: Windows SID of caller (if available)
            
        Returns:
            True if binding is authorized, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self._subjects_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT windows_sid, allowed_public_keys, lifecycle_state
                FROM authorized_subjects
                WHERE subject_id = ?
            """, (subject_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return False
            
            windows_sid, allowed_public_keys_json, lifecycle_state = row
            
            # Verify subject is ACTIVE (not REVOKED)
            if lifecycle_state != 'ACTIVE':
                return False
            
            # FAIL CLOSED: Verify caller SID matches
            # Reject if caller SID is unavailable (identity verification failed)
            if caller_sid is None:
                return False
            if windows_sid is None:
                return False
            if caller_sid != windows_sid:
                return False
            
            # Verify public key is in allowed list
            allowed_public_keys = json.loads(allowed_public_keys_json)
            if public_key not in allowed_public_keys:
                return False
            
            return True
            
        except Exception:
            return False
    
    def verify_parent_authority(
        self,
        client_pid: int,
        parent_authority: str
    ) -> bool:
        """Verify that caller has required parent authority.
        
        This implementation uses Windows process tree traversal to:
        1. Get parent PID of client_pid
        2. Verify parent PID matches expected parent_authority
        3. Verify parent process is authorized Authority process
        
        Args:
            client_pid: Client process ID
            parent_authority: Expected parent authority (PID or process name)
            
        Returns:
            True if parent authority is verified, False otherwise
        """
        try:
            import psutil
            
            # Get client process
            client_process = psutil.Process(client_pid)
            
            # Get parent process
            parent_process = client_process.parent()
            if parent_process is None:
                return False
            
            parent_pid = parent_process.pid
            
            # Check if parent_authority is a PID or process name
            try:
                expected_pid = int(parent_authority)
                # Verify parent PID matches expected
                if parent_pid != expected_pid:
                    return False
            except ValueError:
                # parent_authority is a process name
                if parent_process.name() != parent_authority:
                    return False
            
            # Verify parent process is still running
            if not parent_process.is_running():
                return False
            
            return True
            
        except Exception as e:
            import sys
            print(f"[AuthenticationLayer] verify_parent_authority failed for PID {client_pid}: {e}", file=sys.stderr)
            return False
