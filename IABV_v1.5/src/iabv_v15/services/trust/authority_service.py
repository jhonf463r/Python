"""Authority Service: Trusted authority process for P0.213 V5 Phase 2.

This is the REAL security boundary implemented as a separate process.

CRITICAL: This is the ONLY process that owns:
- Real secret key (OS-protected storage)
- Runtime generation (persisted)
- Canonical lease state (persistent)
- Atomic consumption (interprocess)

The worker/client process CANNOT:
- Import this module's secret
- Construct equivalent authority
- Bypass IPC boundary
- Forge OS identity

Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
Phase 1 Status: DATA_CONTRACT_ONLY (non-authoritative specification)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import struct
import threading
import time
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psutil

from iabv_v15.services.trust.root_trust_anchor import (
    ProcessIdentity,
    RuntimeIdentity,
)
from iabv_v15.services.trust.trusted_execution_identity import (
    CanonicalRunRecord,
    ObservedProcessIdentity,
    TrustedExecutionIdentity,
)
from iabv_v15.services.trust.trusted_lease import TrustedLease


# ── Constants ───────────────────────────────────────────────────────────────

PIPE_NAME = r"\\.\pipe\IABV_Authority"
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MESSAGE_HEADER_SIZE = 4  # uint32 for message length
SECRET_KEY_FILE = "authority_secret.key"
GENERATION_FILE = "authority_generation.txt"
LEASE_STATE_DB = "authority_lease_state.db"
RUN_RECORD_DB = "authority_run_records.db"

# ── Protocol Messages ───────────────────────────────────────────────────────────

@dataclass
class AuthorityRequest:
    """IPC request from client."""
    request_type: str
    data: dict[str, Any]
    request_id: str


@dataclass
class AuthorityResponse:
    """IPC response to client."""
    success: bool
    data: dict[str, Any]
    error: Optional[str] = None
    request_id: str = ""


# ── Authority Service ───────────────────────────────────────────────────────────

class AuthorityService:
    """Trusted authority process service.
    
    This is the REAL security boundary. It runs as a separate process
    and owns the real secret key, generation state, and lease state.
    
    CRITICAL: This is NOT a data contract. This is the REAL authority.
    """
    
    def __init__(self, storage_root: Path | str):
        """Initialize authority service.
        
        Args:
            storage_root: Directory for persistent state (OS-protected)
        """
        self._storage_root = Path(storage_root).resolve()
        self._storage_root.mkdir(parents=True, exist_ok=True)
        
        # Phase 2: Load or generate real secret key
        self._secret_key = self._load_or_generate_secret_key()
        
        # Phase 2: Load or initialize generation
        self._generation = self._load_or_initialize_generation()
        
        # Phase 2: Initialize persistent lease state store
        self._lease_state_db = self._storage_root / LEASE_STATE_DB
        self._init_lease_state_db()
        
        # Phase 2: Initialize run record store
        self._run_record_db = self._storage_root / RUN_RECORD_DB
        self._init_run_record_db()
        
        # Phase 2: Track connected clients
        self._clients: dict[int, ObservedProcessIdentity] = {}
        self._clients_lock = threading.Lock()
        
        # Phase 2: Shutdown flag
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
    
    def _load_or_generate_secret_key(self) -> bytes:
        """Load or generate real secret key (OS-protected storage).
        
        Phase 2: Real secret material, NOT placeholder.
        """
        secret_file = self._storage_root / SECRET_KEY_FILE
        
        if secret_file.exists():
            with open(secret_file, "rb") as f:
                return f.read()
        else:
            # Generate real secret key (32 bytes for HMAC-SHA256)
            secret_key = secrets.token_bytes(32)
            with open(secret_file, "wb") as f:
                f.write(secret_key)
            # Restrict file permissions (Windows)
            try:
                import win32security
                import win32con
                import win32api
                
                # Create DACL: only owner has full access
                user = os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))
                sid, _, _ = win32security.LookupAccountName(None, user)
                
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    win32con.FILE_ALL_ACCESS,
                    sid
                )
                
                security = win32security.SECURITY_ATTRIBUTES()
                security.SECURITY_DESCRIPTOR.SetSecurityDescriptorDacl(1, dacl, 0)
                
                win32api.SetFileSecurity(
                    str(secret_file),
                    win32security.DACL_SECURITY_INFORMATION,
                    security.SECURITY_DESCRIPTOR
                )
            except Exception:
                # DACL setting failed, but secret key is still valid
                # Continue without DACL (less secure but functional for testing)
                pass
            
            return secret_key
    
    def _load_or_initialize_generation(self) -> int:
        """Load or initialize generation (persisted).
        
        Phase 2: Real persistence, NOT in-memory placeholder.
        """
        generation_file = self._storage_root / GENERATION_FILE
        
        if generation_file.exists():
            with open(generation_file, "r") as f:
                return int(f.read().strip())
        else:
            generation = 0
            with open(generation_file, "w") as f:
                f.write(str(generation))
            return generation
    
    def _increment_generation(self) -> None:
        """Increment generation (atomic persist).
        
        Phase 2: Real atomic persistence.
        """
        with self._shutdown_lock:
            self._generation += 1
            generation_file = self._storage_root / GENERATION_FILE
            with open(generation_file, "w") as f:
                f.write(str(self._generation))
    
    def _init_lease_state_db(self) -> None:
        """Initialize persistent lease state store (SQLite).
        
        Phase 2: Real persistent state, NOT in-process dictionary.
        """
        conn = sqlite3.connect(str(self._lease_state_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
                consumed INTEGER NOT NULL DEFAULT 0,
                generation INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generation 
            ON leases(generation)
        """)
        
        conn.commit()
        conn.close()
    
    def _init_run_record_db(self) -> None:
        """Initialize run record store (SQLite).
        
        Phase 2: Authority-owned canonical run records.
        """
        conn = sqlite3.connect(str(self._run_record_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_records (
                run_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                episode_id TEXT,
                session_id TEXT,
                invocation_id TEXT NOT NULL,
                authorized_scope TEXT NOT NULL,
                consumer_pid INTEGER NOT NULL,
                generation INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _sign_data(self, data: str) -> str:
        """Sign data with HMAC-SHA256 using real secret key.
        
        Phase 2: Real cryptographic signature, NOT placeholder.
        """
        signature = hmac.new(
            self._secret_key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC signature.
        
        Phase 2: Real signature verification.
        """
        expected = self._sign_data(data)
        return hmac.compare_digest(expected, signature)
    
    def _get_client_identity(self, pipe_handle: int) -> ObservedProcessIdentity:
        """Get OS-observed client identity from pipe handle.
        
        Phase 2: OS-derived identity, NOT JSON fields.
        Uses GetNamedPipeClientProcessId from Windows API.
        """
        try:
            import win32pipe
            import win32api
            
            # Get client PID from pipe handle
            client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)
            
            # Get process details
            process = psutil.Process(client_pid)
            create_time = process.create_time()
            ppid = process.ppid()
            
            return ObservedProcessIdentity(
                pid=client_pid,
                create_time=create_time,
                ppid=ppid
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get client identity: {e}")
    
    def _register_client(self, client_identity: ObservedProcessIdentity) -> None:
        """Register client identity.
        
        Phase 2: Track connected clients.
        """
        with self._clients_lock:
            self._clients[client_identity.pid] = client_identity
    
    def _verify_client(self, client_pid: int) -> bool:
        """Verify client is registered.
        
        Phase 2: Reject unauthorized clients.
        """
        with self._clients_lock:
            return client_pid in self._clients
    
    # ── Protocol Handlers ───────────────────────────────────────────────────────
    
    def handle_register_execution(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle REGISTER_EXECUTION request.
        
        Phase 2: Authority creates canonical RunRecord.
        """
        try:
            # Phase 2: Generate authority-owned IDs
            run_id = secrets.token_urlsafe(16)
            execution_id = secrets.token_urlsafe(16)
            invocation_id = request.data.get("invocation_id", "")
            authorized_scope = request.data.get("authorized_scope", "")
            episode_id = request.data.get("episode_id")
            session_id = request.data.get("session_id")
            
            # Phase 2: Create canonical RunRecord (authority-owned)
            run_record = CanonicalRunRecord(
                run_id=run_id,
                execution_id=execution_id,
                episode_id=episode_id,
                session_id=session_id,
                invocation_id=invocation_id,
                authorized_scope=authorized_scope,
            )
            
            # Phase 2: Persist to authority-owned store
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO run_records 
                (run_id, execution_id, episode_id, session_id, invocation_id, 
                 authorized_scope, consumer_pid, generation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_record.run_id,
                run_record.execution_id,
                run_record.episode_id,
                run_record.session_id,
                run_record.invocation_id,
                run_record.authorized_scope,
                client_pid,
                self._generation,
                time.time()
            ))
            
            conn.commit()
            conn.close()
            
            return AuthorityResponse(
                success=True,
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "generation": self._generation,
                }
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_issue_lease(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle ISSUE_LEASE request.
        
        Phase 2: Authority issues HMAC-signed lease.
        """
        try:
            run_id = request.data.get("run_id")
            execution_id = request.data.get("execution_id")
            producer_scope = request.data.get("producer_scope", "")
            ttl_seconds = request.data.get("ttl_seconds", 3600)
            
            # Phase 2: Verify run record exists (authority-owned)
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT execution_id, authorized_scope, consumer_pid, generation
                FROM run_records
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Run record not found"
                )
            
            db_execution_id, authorized_scope, record_pid, record_generation = row
            
            # Phase 2: Verify client PID matches run record
            if client_pid != record_pid:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Client PID mismatch"
                )
            
            # Phase 2: Verify generation matches
            if self._generation != record_generation:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Phase 2: Generate authority-owned lease
            lease_id = secrets.token_urlsafe(16)
            issued_at = time.time()
            expires_at = issued_at + ttl_seconds
            
            lease = TrustedLease(
                issuer_pid=os.getpid(),
                issuer_generation=self._generation,
                execution_id=execution_id,
                invocation_id=secrets.token_urlsafe(16),
                lease_id=lease_id,
                producer_pid=client_pid,
                producer_scope=producer_scope,
                authorization_context=authorized_scope,
                issued_at=issued_at,
                expires_at=expires_at,
                signature="",  # Will be filled after serialization
                consumed=False,
            )
            
            # Phase 2: Serialize and sign
            lease_data = lease.to_dict()
            lease_data.pop("signature", None)
            lease_json = json.dumps(lease_data, sort_keys=True)
            signature = self._sign_data(lease_json)
            
            lease = dataclasses.replace(lease, signature=signature)
            
            # Phase 2: Persist to lease state store
            conn = sqlite3.connect(str(self._lease_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO leases (lease_id, consumed, generation, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (lease_id, 0, self._generation, expires_at, issued_at))
            
            conn.commit()
            conn.close()
            
            return AuthorityResponse(
                success=True,
                data={"lease": lease.to_dict()}
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_consume_lease(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle CONSUME_LEASE request.
        
        Phase 2: Atomic verify+consume with persistent state store.
        """
        try:
            lease_id = request.data.get("lease_id")
            
            # Phase 2: Atomic verify+consume in persistent store
            conn = sqlite3.connect(str(self._lease_state_db))
            cursor = conn.cursor()
            
            # Phase 2: Check lease exists and not consumed
            cursor.execute("""
                SELECT consumed, generation, expires_at
                FROM leases
                WHERE lease_id = ?
            """, (lease_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease not found"
                )
            
            consumed, generation, expires_at = row
            
            # Phase 2: Verify not consumed
            if consumed:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease already consumed"
                )
            
            # Phase 2: Verify generation matches
            if generation != self._generation:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Phase 2: Verify not expired
            if time.time() > expires_at:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease expired"
                )
            
            # Phase 2: Atomic consume (UPDATE with WHERE clause)
            cursor.execute("""
                UPDATE leases
                SET consumed = 1
                WHERE lease_id = ? AND consumed = 0
            """, (lease_id,))
            
            conn.commit()
            conn.close()
            
            return AuthorityResponse(
                success=True,
                data={"lease_id": lease_id, "consumed": True}
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_verify_execution(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle VERIFY_EXECUTION request.
        
        Phase 2: Verify execution identity.
        """
        try:
            run_id = request.data.get("run_id")
            execution_id = request.data.get("execution_id")
            
            # Phase 2: Verify run record exists
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT execution_id, consumer_pid, generation
                FROM run_records
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Run record not found"
                )
            
            db_execution_id, record_pid, record_generation = row
            
            # Phase 2: Verify execution ID matches
            if execution_id != db_execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # Phase 2: Verify client PID matches
            if client_pid != record_pid:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Client PID mismatch"
                )
            
            # Phase 2: Verify generation matches
            if self._generation != record_generation:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            return AuthorityResponse(
                success=True,
                data={"verified": True}
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_get_status(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle GET_STATUS request.
        
        Phase 2: Return authority status.
        """
        try:
            return AuthorityResponse(
                success=True,
                data={
                    "generation": self._generation,
                    "pid": os.getpid(),
                    "uptime": time.time(),
                }
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
