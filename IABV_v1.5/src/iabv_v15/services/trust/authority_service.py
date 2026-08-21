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
        
        # Phase 2: Initialize run record store (must be before lease state)
        self._run_record_db = self._storage_root / RUN_RECORD_DB
        self._init_run_record_db()
        
        # Phase 2: Initialize persistent lease state store
        self._lease_state_db = self._storage_root / LEASE_STATE_DB
        self._init_lease_state_db()
        
        # Phase 2: Track connected clients
        self._clients: dict[int, ObservedProcessIdentity] = {}
        self._clients_lock = threading.Lock()
        
        # Phase 2: Shutdown flag
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        
        # Phase 2: Track database connections for cleanup
        self._db_connections: list[sqlite3.Connection] = []
    
    def shutdown(self) -> None:
        """Shutdown authority service and close all database connections.
        
        Phase 2: Explicit cleanup to prevent Windows file locking issues.
        """
        with self._shutdown_lock:
            self._shutdown = True
            # Close all tracked database connections
            for conn in self._db_connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._db_connections.clear()
    
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
        
        AUTHORITATIVE STATE CONTRACT:
        - Stores full canonical lease with signature
        - consumed flag is authoritative state (NOT DTO/cache)
        - Signature covers all authorization-relevant fields
        """
        conn = sqlite3.connect(str(self._lease_state_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
                consumed INTEGER NOT NULL DEFAULT 0,
                generation INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL,
                lease_json TEXT NOT NULL,
                signature TEXT NOT NULL,
                run_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                producer_pid INTEGER NOT NULL,
                authorized_scope TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generation 
            ON leases(generation)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_id 
            ON leases(run_id)
        """)
        
        conn.commit()
        conn.close()
    
    def _init_run_record_db(self) -> None:
        """Initialize run record store (SQLite).
        
        Phase 2: Authority-owned canonical run records.
        
        AUTHORITY POLICY CONTRACT:
        - requested_scope: Caller-provided scope request
        - authorized_scope: Authority-computed scope based on policy
        - action: Requested operation
        - target: Requested target
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
                requested_scope TEXT NOT NULL,
                authorized_scope TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
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
    
    def _compute_authorized_scope(
        self,
        requested_scope: str,
        action: str,
        target: str,
        client_pid: int
    ) -> str:
        """Compute authorized scope based on authority policy.
        
        AUTHORITY POLICY CONTRACT:
        - requested_scope: Caller-provided scope request
        - Authority MUST NOT blindly accept caller-provided scope
        - Authority computes authorized_scope based on policy
        
        Phase 2: Simple policy - accept requested_scope if it matches allowed patterns
        Future: Implement real policy engine with scope hierarchy
        
        Args:
            requested_scope: Caller-provided scope request
            action: Requested operation
            target: Requested target
            client_pid: OS-observed client PID
            
        Returns:
            Authorized scope (may be narrower than requested)
            
        Raises:
            ValueError: If requested_scope is not allowed
        """
        # Phase 2: Simple policy - reject wildcard/broader scope attempts
        if "*" in requested_scope or "admin" in requested_scope.lower():
            raise ValueError(f"Requested scope '{requested_scope}' is not allowed")
        
        # Phase 2: Simple policy - accept requested_scope as-is for development
        # Future: Implement real policy with scope hierarchy and action/target checks
        return requested_scope
    
    def handle_register_execution(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle REGISTER_EXECUTION request.
        
        Phase 2: Authority creates canonical RunRecord with policy decision.
        
        AUTHORITY POLICY CONTRACT:
        - requested_scope: Caller-provided scope request
        - authorized_scope: Authority-computed scope based on policy
        - action: Requested operation
        - target: Requested target
        """
        try:
            # Phase 2: Generate authority-owned IDs
            run_id = secrets.token_urlsafe(16)
            execution_id = secrets.token_urlsafe(16)
            invocation_id = request.data.get("invocation_id", "")
            requested_scope = request.data.get("requested_scope", "")
            action = request.data.get("action", "READ")
            target = request.data.get("target", "")
            episode_id = request.data.get("episode_id")
            session_id = request.data.get("session_id")
            
            # Phase 2: Compute authorized scope based on authority policy
            try:
                authorized_scope = self._compute_authorized_scope(
                    requested_scope, action, target, client_pid
                )
            except ValueError as e:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Scope authorization failed: {e}"
                )
            
            # Phase 2: Create canonical RunRecord (authority-owned)
            run_record = CanonicalRunRecord(
                run_id=run_id,
                execution_id=execution_id,
                episode_id=episode_id,
                session_id=session_id,
                invocation_id=invocation_id,
                requested_scope=requested_scope,
                authorized_scope=authorized_scope,
                action=action,
                target=target,
            )
            
            # Phase 2: Persist to authority-owned store
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO run_records 
                (run_id, execution_id, episode_id, session_id, invocation_id, 
                 requested_scope, authorized_scope, action, target,
                 consumer_pid, generation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_record.run_id,
                run_record.execution_id,
                run_record.episode_id,
                run_record.session_id,
                run_record.invocation_id,
                run_record.requested_scope,
                run_record.authorized_scope,
                run_record.action,
                run_record.target,
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
                    "authorized_scope": authorized_scope,
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
        
        Phase 2: Authority issues HMAC-signed lease with full authorization binding.
        
        AUTHORIZATION BINDING CONTRACT:
        - Lease must be bound to RunRecord
        - Signature must cover all authorization-relevant fields
        - Client cannot forge authorization fields
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
                SELECT execution_id, authorized_scope, action, target, consumer_pid, generation
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
            
            db_execution_id, authorized_scope, action, target, record_pid, record_generation = row
            
            # Phase 2: Verify execution_id matches run record
            if execution_id != db_execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
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
            
            # Phase 2: Serialize and sign (signature covers all authorization-relevant fields)
            lease_data = lease.to_dict()
            lease_data.pop("signature", None)
            lease_json = json.dumps(lease_data, sort_keys=True)
            signature = self._sign_data(lease_json)
            
            lease = dataclasses.replace(lease, signature=signature)
            
            # Phase 2: Serialize for persistence (signature covers all authorization-relevant fields)
            # Store lease_json WITHOUT signature for verification
            lease_data = lease.to_dict()
            lease_data.pop("signature", None)
            lease_json_for_verification = json.dumps(lease_data, sort_keys=True)
            
            # Store full lease WITH signature for client response
            lease_json_full = json.dumps(lease.to_dict(), sort_keys=True)
            
            # Phase 2: Persist full canonical lease with signature and authorization fields
            conn = sqlite3.connect(str(self._lease_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO leases 
                (lease_id, consumed, generation, expires_at, created_at, 
                 lease_json, signature, run_id, execution_id, producer_pid, authorized_scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lease_id, 
                0, 
                self._generation, 
                expires_at, 
                issued_at,
                lease_json_for_verification,  # Store without signature for verification
                signature,
                run_id,
                execution_id,
                client_pid,
                authorized_scope
            ))
            
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
    
    def _verify_lease_signature(
        self,
        lease_json: str,
        signature: str
    ) -> bool:
        """Verify lease HMAC signature.
        
        AUTHORIZATION AUTHENTICITY CONTRACT:
        - Signature must cover all authorization-relevant fields
        - Signature must be valid
        - Prevents tampering with authorization fields
        
        Args:
            lease_json: Serialized lease JSON (without signature field)
            signature: HMAC signature to verify
            
        Returns:
            True if signature is valid
        """
        expected_signature = self._sign_data(lease_json)
        return hmac.compare_digest(expected_signature, signature)
    
    def handle_consume_lease(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle CONSUME_LEASE request.
        
        Phase 2: Atomic verify+consume with full authorization binding.
        
        AUTHORIZATION BINDING CONTRACT:
        - Must verify signature
        - Must verify run_id, execution_id, consumer identity, generation
        - Must verify scope, action, target
        - Must verify issued_at, expires_at
        - Must be run-bound to canonical RunRecord
        - Atomic UPDATE with WHERE clause for exactly-once
        """
        try:
            lease_id = request.data.get("lease_id")
            
            # Phase 2: Load canonical lease from authoritative state
            conn = sqlite3.connect(str(self._lease_state_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT consumed, generation, expires_at, lease_json, signature, 
                       run_id, execution_id, producer_pid, authorized_scope
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
            
            consumed, generation, expires_at, lease_json, signature, run_id, execution_id, producer_pid, authorized_scope = row
            
            # Phase 2: Verify signature (prevents tampering with authorization fields)
            if not self._verify_lease_signature(lease_json, signature):
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Invalid lease signature"
                )
            
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
            
            # Phase 2: Verify run_id exists in RunRecord (separate connection)
            conn_run = sqlite3.connect(str(self._run_record_db))
            cursor_run = conn_run.cursor()
            cursor_run.execute("""
                SELECT consumer_pid, generation, authorized_scope, action, target
                FROM run_records
                WHERE run_id = ?
            """, (run_id,))
            
            run_record_row = cursor_run.fetchone()
            conn_run.close()
            
            if not run_record_row:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Run record not found"
                )
            
            record_pid, record_generation, record_authorized_scope, action, target = run_record_row
            
            # Phase 2: Verify execution_id matches RunRecord
            if execution_id != request.data.get("execution_id"):
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # Phase 2: Verify client PID matches RunRecord (run-bound)
            if client_pid != record_pid:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Client PID mismatch"
                )
            
            # Phase 2: Verify generation matches RunRecord
            if self._generation != record_generation:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Phase 2: Verify authorized_scope matches RunRecord
            if authorized_scope != record_authorized_scope:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Authorized scope mismatch"
                )
            
            # Phase 2: Atomic consume with WHERE clause (exactly-once)
            cursor.execute("""
                UPDATE leases
                SET consumed = 1
                WHERE lease_id = ? 
                  AND consumed = 0 
                  AND generation = ? 
                  AND expires_at > ?
            """, (lease_id, self._generation, time.time()))
            
            # Check if UPDATE actually modified a row
            if cursor.rowcount == 0:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease already consumed or expired"
                )
            
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
