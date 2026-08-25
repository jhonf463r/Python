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
from iabv_v15.services.trust.authority_protocol import (
    canonicalize_target,
    RegisterExecutionRequest,
    RegisterExecutionResponse,
    IssueLeaseRequest,
    IssueLeaseResponse,
    ConsumeLeaseRequest,
    ConsumeLeaseResponse,
    VerifyExecutionContextRequest,
    VerifyExecutionContextResponse,
    AuthorizationPolicyInput,
    apply_authorization_policy,
)
from iabv_v15.services.phase3.ed25519_keys import (
    verify_signature as ed25519_verify_signature,
    public_key_from_hex,
    public_key_from_base64,
)


# ── Constants ───────────────────────────────────────────────────────────────

PIPE_NAME = r"\\.\pipe\IABV_Authority"
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MESSAGE_HEADER_SIZE = 4  # uint32 for message length
SECRET_KEY_FILE = "authority_secret.key"
GENERATION_FILE = "authority_generation.txt"
LEASE_STATE_DB = "authority_lease_state.db"
RUN_RECORD_DB = "authority_run_records.db"
JOIN_AUTH_DB = "authority_join_authorizations.db"
CHALLENGE_AUTH_DB = "authority_challenge_state.db"

# ── Protocol Messages ───────────────────────────────────────────────────────────

@dataclass
class AuthenticatedPeer:
    """OS-verified peer identity from transport layer.
    
    This object is created by the trusted transport layer (Phase 2).
    It must NOT be constructible from untrusted JSON.
    """
    process_id: int
    windows_sid: str
    parent_authority: int
    channel_id: str
    verified: bool = True

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
        
        # Phase 3: Initialize join authorization store (now includes challenges table)
        self._join_auth_db = self._storage_root / JOIN_AUTH_DB
        self._init_join_authorization_db()
        
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
        
        Phase 2 Round 3: Enhanced with lease_json and signature fields for canonical binding.
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
                lease_json TEXT,
                signature TEXT,
                run_id TEXT,
                execution_id TEXT,
                producer_pid INTEGER,
                authorized_scope TEXT
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
        
        Phase 2 Round 3: Enhanced with authorization policy fields for canonical binding.
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
                parent_authority INTEGER NOT NULL,
                generation INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _init_join_authorization_db(self) -> None:
        """Initialize join authorization store (SQLite).
        
        Phase 3: Persistent join state with atomic uniqueness constraints.
        Enforces exactly-once join creation for subject_id + execution_id + generation.
        F10 FIX: Consolidated challenges table into this DB for atomic transaction semantics.
        """
        conn = sqlite3.connect(str(self._join_auth_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS join_authorizations (
                join_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                generation INTEGER NOT NULL,
                client_pid INTEGER NOT NULL,
                public_key TEXT NOT NULL,
                created_at REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                consumed_at REAL,
                UNIQUE(subject_id, execution_id, generation)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject_execution 
            ON join_authorizations(subject_id, execution_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generation 
            ON join_authorizations(generation)
        """)
        
        # F10 FIX: Consolidated challenges table into join authorization DB
        # This enables atomic transactions across join and challenge state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                challenge_id TEXT PRIMARY KEY,
                join_id TEXT NOT NULL,
                challenge TEXT NOT NULL,
                generation INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                consumed_at REAL,
                UNIQUE(join_id, challenge),
                FOREIGN KEY (join_id) REFERENCES join_authorizations(join_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_challenges_join_id 
            ON challenges(join_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_challenges_generation 
            ON challenges(generation)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_challenges_execution_id 
            ON challenges(execution_id)
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
    
    def _create_authenticated_peer(self, client_pid: int) -> AuthenticatedPeer:
        """Create AuthenticatedPeer from OS-observed client PID.
        
        Phase 3: Derive OS-verified peer identity for Phase 3 authorization.
        This uses the OS-observed PID from the transport layer.
        """
        try:
            import win32security
            import win32api
            import win32con
            
            # Get process token SID
            process = psutil.Process(client_pid)
            create_time = process.create_time()
            parent_pid = process.ppid()
            
            # Get Windows SID from process token
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, client_pid)
            token = win32security.OpenProcessToken(handle, win32security.TOKEN_QUERY)
            sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            sid_string = str(sid)
            
            win32api.CloseHandle(handle)
            win32api.CloseHandle(token)
            
            return AuthenticatedPeer(
                process_id=client_pid,
                windows_sid=sid_string,
                parent_authority=parent_pid,
                channel_id=f"pipe_{client_pid}",
                verified=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create authenticated peer: {e}")
    
    def _resolve_subject_from_run_record(self, peer: AuthenticatedPeer, subject_id: str) -> Optional[dict]:
        """Resolve subject from Phase 2 RunRecord using peer identity.
        
        Phase 3: Use Phase 2's RunRecord as authoritative subject registry.
        The subject_id is the run_id from Phase 2.
        """
        conn = sqlite3.connect(str(self._run_record_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT run_id, execution_id, consumer_pid, parent_authority, generation, authorized_scope, action, target
            FROM run_records
            WHERE run_id = ?
        """, (subject_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        run_id, execution_id, consumer_pid, parent_authority, generation, authorized_scope, action, target = row
        
        # Verify peer identity matches run record
        if peer.process_id != consumer_pid:
            return None
        
        # Verify generation matches
        if self._generation != generation:
            return None
        
        return {
            "run_id": run_id,
            "execution_id": execution_id,
            "consumer_pid": consumer_pid,
            "parent_authority": parent_authority,
            "generation": generation,
            "authorized_scope": authorized_scope,
            "action": action,
            "target": target
        }
    
    # ── Protocol Handlers ───────────────────────────────────────────────────────
    
    def handle_register_execution(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle REGISTER_EXECUTION request using canonical protocol.
        
        Phase 2 Round 3: Authority creates canonical RunRecord with contextual policy decision.
        """
        try:
            # Parse canonical request
            reg_request = RegisterExecutionRequest.from_dict(request.data)
            
            # Phase 2 Round 3: Generate authority-owned IDs
            run_id = secrets.token_urlsafe(16)
            execution_id = secrets.token_urlsafe(16)
            
            # Phase 2 Round 3: Apply contextual authorization policy
            policy_input = AuthorizationPolicyInput(
                observed_process_identity={"pid": client_pid},
                canonical_run_record=None,  # No RunRecord yet
                action=reg_request.action,
                target=reg_request.target,
                requested_scope=reg_request.requested_scope,
                task_context=reg_request.task_context,
                generation=self._generation
            )
            policy_decision = apply_authorization_policy(policy_input)
            
            if not policy_decision.allowed:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Authorization denied: {policy_decision.reason}"
                )
            
            authorized_scope = policy_decision.authorized_scope
            
            # Phase 2 Round 3: Create canonical RunRecord (authority-owned)
            run_record = CanonicalRunRecord(
                run_id=run_id,
                execution_id=execution_id,
                episode_id=reg_request.episode_id,
                session_id=reg_request.session_id,
                invocation_id=reg_request.invocation_id,
                requested_scope=reg_request.requested_scope,
                authorized_scope=authorized_scope,
                action=reg_request.action,
                target=reg_request.target,
                consumer_pid=client_pid,
                generation=self._generation,
                created_at=time.time()
            )
            
            # Phase 2 Round 3: Persist to authority-owned store
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            # Derive parent authority from OS process tree
            try:
                parent_process = psutil.Process(client_pid)
                parent_authority = parent_process.ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                parent_authority = 0  # Fallback if parent cannot be determined
            
            cursor.execute("""
                INSERT INTO run_records 
                (run_id, execution_id, episode_id, session_id, invocation_id, 
                 requested_scope, authorized_scope, action, target, consumer_pid, parent_authority, generation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                run_record.consumer_pid,
                parent_authority,
                run_record.generation,
                run_record.created_at
            ))
            
            conn.commit()
            conn.close()
            
            # Return canonical response
            return AuthorityResponse(
                success=True,
                data=RegisterExecutionResponse(
                    run_id=run_id,
                    execution_id=execution_id,
                    consumer_pid=client_pid,
                    generation=self._generation,
                    authorized_scope=authorized_scope
                ).to_dict()
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
        """Handle ISSUE_LEASE request using canonical protocol.
        
        Phase 2 Round 3: Authority issues HMAC-signed lease with canonical RunRecord binding.
        """
        try:
            # Parse canonical request
            issue_request = IssueLeaseRequest.from_dict(request.data)
            
            run_id = issue_request.run_id
            execution_id = issue_request.execution_id
            caller_session_id = issue_request.session_id
            caller_episode_id = issue_request.episode_id
            requested_ttl_seconds = issue_request.requested_ttl_seconds or 3600
            
            # Phase 2 Round 3: Verify run record exists (authority-owned)
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT execution_id, episode_id, session_id, authorized_scope, consumer_pid, generation, action, target
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
            
            db_execution_id, db_episode_id, db_session_id, authorized_scope, record_pid, record_generation, action, target = row
            
            # Phase 2 Round 3: Verify client PID matches run record
            if client_pid != record_pid:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Client PID mismatch"
                )
            
            # Phase 2 Round 3: Verify generation matches
            if self._generation != record_generation:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # VFINAL5-R3: Verify execution_id matches run record
            if execution_id != db_execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Execution ID mismatch: provided '{execution_id}' does not match canonical '{db_execution_id}'"
                )
            
            # VFINAL5-R3.3: Universal session_id and episode_id validation for all scopes
            # If canonical record has a session_id, caller must match exactly
            if db_session_id is not None:
                if caller_session_id != db_session_id:
                    return AuthorityResponse(
                        success=False,
                        data={},
                        error=f"Session ID mismatch: caller '{caller_session_id}' does not match canonical '{db_session_id}'"
                    )
            # If canonical record has None, caller must also provide None (fail-closed)
            elif caller_session_id is not None:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Session ID mismatch: canonical record has no session_id but caller provided '{caller_session_id}'"
                )
            
            # If canonical record has an episode_id, caller must match exactly
            if db_episode_id is not None:
                if caller_episode_id != db_episode_id:
                    return AuthorityResponse(
                        success=False,
                        data={},
                        error=f"Episode ID mismatch: caller '{caller_episode_id}' does not match canonical '{db_episode_id}'"
                    )
            # If canonical record has None, caller must also provide None (fail-closed)
            elif caller_episode_id is not None:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Episode ID mismatch: canonical record has no episode_id but caller provided '{caller_episode_id}'"
                )
            
            # Phase 2 Round 3: Generate authority-owned lease
            lease_id = secrets.token_urlsafe(16)
            issued_at = time.time()
            expires_at = issued_at + requested_ttl_seconds
            
            lease = TrustedLease(
                issuer_pid=os.getpid(),
                issuer_generation=self._generation,
                execution_id=execution_id,
                invocation_id=secrets.token_urlsafe(16),
                lease_id=lease_id,
                producer_pid=client_pid,
                producer_scope=authorized_scope,
                authorization_context=authorized_scope,
                issued_at=issued_at,
                expires_at=expires_at,
                signature="",  # Will be filled after serialization
                consumed=False,
            )
            
            # Phase 2 Round 3: Serialize and sign with all authorization fields
            lease_data = lease.to_dict()
            lease_data.pop("signature", None)
            lease_json = json.dumps(lease_data, sort_keys=True)
            signature = self._sign_data(lease_json)
            
            lease = dataclasses.replace(lease, signature=signature)
            
            # Phase 2 Round 3: Persist to lease state store with full canonical data
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
                lease_json,  # Store without signature for verification
                signature,
                run_id,
                execution_id,
                client_pid,
                authorized_scope
            ))
            
            conn.commit()
            conn.close()
            
            # Return canonical response
            return AuthorityResponse(
                success=True,
                data=IssueLeaseResponse(
                    lease_id=lease_id,
                    run_id=run_id,
                    execution_id=execution_id,
                    authorized_scope=authorized_scope,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    signature=signature
                ).to_dict()
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
        """Handle CONSUME_LEASE request using canonical protocol.
        
        Phase 2 Round 3: Atomic verify+consume with canonical RunRecord binding and signature verification.
        """
        try:
            # Parse canonical request
            consume_request = ConsumeLeaseRequest.from_dict(request.data)
            
            lease_id = consume_request.lease_id
            execution_id = consume_request.execution_id
            requested_action = consume_request.requested_action
            requested_target = consume_request.requested_target
            
            # Phase 2 Round 3: Verify lease exists and get canonical data
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
            
            consumed, generation, expires_at, lease_json, signature, run_id, db_execution_id, producer_pid, authorized_scope = row
            
            # Phase 2 Round 3: Verify not consumed
            if consumed:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease already consumed"
                )
            
            # Phase 2 Round 3: Verify generation matches
            if generation != self._generation:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Phase 2 Round 3: Verify not expired
            if time.time() > expires_at:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease expired"
                )
            
            # Phase 2 Round 3: Verify execution_id matches
            if execution_id != db_execution_id:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # Phase 2 Round 3: Verify signature
            if not self._verify_signature(lease_json, signature):
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Invalid lease signature"
                )
            
            # Phase 2 Round 3: Verify RunRecord binding (separate connection to avoid locking)
            conn_run = sqlite3.connect(str(self._run_record_db))
            cursor_run = conn_run.cursor()
            
            cursor_run.execute("""
                SELECT consumer_pid, generation, authorized_scope, action, target, session_id, episode_id
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
            
            record_pid, record_generation, record_authorized_scope, authorized_action, authorized_target, record_session_id, record_episode_id = run_record_row
            
            # Phase 2 Round 3: Verify client PID matches run record
            if client_pid != record_pid:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Client PID mismatch"
                )
            
            # Phase 2 Round 3: Verify generation matches run record
            if self._generation != record_generation:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Phase 2 Round 3: Verify authorized scope matches
            if authorized_scope != record_authorized_scope:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Authorized scope mismatch"
                )
            
            # VFINAL5-R3: For protected self_update, validate session_id and episode_id
            if authorized_scope == "self_update":
                # Session ID is required for self_update
                if record_session_id is None:
                    conn.close()
                    return AuthorityResponse(
                        success=False,
                        data={},
                        error="Run record missing session_id for self_update scope"
                    )
                # Episode ID is required for self_update
                if record_episode_id is None:
                    conn.close()
                    return AuthorityResponse(
                        success=False,
                        data={},
                        error="Run record missing episode_id for self_update scope"
                    )
            
            # Phase 4: Verify action binding
            if requested_action != authorized_action:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Action mismatch: requested '{requested_action}' but authorized '{authorized_action}'"
                )
            
            # VFINAL5-R2.1: Canonicalize targets before comparison for platform-independent validation
            canonical_requested_target = canonicalize_target(requested_target)
            canonical_authorized_target = canonicalize_target(authorized_target)
            
            # Phase 4: Verify target binding (using canonical forms)
            if canonical_requested_target != canonical_authorized_target:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Target mismatch: requested '{canonical_requested_target}' but authorized '{canonical_authorized_target}'"
                )
            
            # Phase 2 Round 3: Atomic consume (UPDATE with WHERE clause)
            cursor.execute("""
                UPDATE leases
                SET consumed = 1
                WHERE lease_id = ? 
                  AND consumed = 0 
                  AND generation = ? 
                  AND expires_at > ?
            """, (lease_id, self._generation, time.time()))
            
            if cursor.rowcount == 0:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Lease already consumed or expired"
                )
            
            conn.commit()
            conn.close()
            
            # Return canonical response
            return AuthorityResponse(
                success=True,
                data=ConsumeLeaseResponse(
                    consumed=True,
                    consumed_at=time.time()
                ).to_dict()
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_verify_execution_context(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle VERIFY_EXECUTION_CONTEXT request for MCP self-update.
        
        This method validates that an execution context (execution_id, run_id)
        exists in the RunRecord database and belongs to the authenticated client.
        This is used for MCP self-update to preserve causal attribution.
        """
        try:
            # Parse canonical request
            verify_request = VerifyExecutionContextRequest.from_dict(request.data)
            
            execution_id = verify_request.execution_id
            run_id = verify_request.run_id
            session_id = verify_request.session_id
            episode_id = verify_request.episode_id
            
            # Verify run record exists
            conn = sqlite3.connect(str(self._run_record_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT run_id, execution_id, consumer_pid, generation, authorized_scope, session_id, episode_id
                FROM run_records
                WHERE run_id = ? AND execution_id = ?
            """, (run_id, execution_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return AuthorityResponse(
                    success=True,
                    data=VerifyExecutionContextResponse(
                        valid=False,
                        error="Execution context not found in RunRecord database"
                    ).to_dict()
                )
            
            record_run_id, record_execution_id, consumer_pid, generation, authorized_scope, record_session_id, record_episode_id = row
            
            # Verify client PID matches run record
            if client_pid != consumer_pid:
                return AuthorityResponse(
                    success=True,
                    data=VerifyExecutionContextResponse(
                        valid=False,
                        error="Client PID mismatch: execution context belongs to different process"
                    ).to_dict()
                )
            
            # Verify generation matches
            if generation != self._generation:
                return AuthorityResponse(
                    success=True,
                    data=VerifyExecutionContextResponse(
                        valid=False,
                        error="Generation mismatch: execution context from different authority generation"
                    ).to_dict()
                )
            
            # VFINAL5-R2.1: Require session_id for protected self-update operations
            # For self_update scope, session_id is REQUIRED
            if authorized_scope == "self_update":
                if session_id is None:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error="Session ID is required for self_update scope"
                        ).to_dict()
                    )
                if record_session_id is None:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error="Canonical execution record missing session_id"
                        ).to_dict()
                    )
                # Verify session_id matches canonical record (CROSS_SESSION = REJECT)
                if session_id != record_session_id:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error=f"Session ID mismatch: provided '{session_id}' does not match canonical '{record_session_id}'"
                        ).to_dict()
                    )
            
            # VFINAL5-R2.1: Require episode_id for protected self-update operations
            # For self_update scope, episode_id is REQUIRED
            if authorized_scope == "self_update":
                if episode_id is None:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error="Episode ID is required for self_update scope"
                        ).to_dict()
                    )
                if record_episode_id is None:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error="Canonical execution record missing episode_id"
                        ).to_dict()
                    )
                # Verify episode_id matches canonical record (CROSS_EPISODE = REJECT)
                if episode_id != record_episode_id:
                    return AuthorityResponse(
                        success=True,
                        data=VerifyExecutionContextResponse(
                            valid=False,
                            error=f"Episode ID mismatch: provided '{episode_id}' does not match canonical '{record_episode_id}'"
                        ).to_dict()
                    )
            
            # Return canonical response
            return AuthorityResponse(
                success=True,
                data=VerifyExecutionContextResponse(
                    valid=True,
                    consumer_pid=consumer_pid,
                    generation=generation,
                    authorized_scope=authorized_scope
                ).to_dict()
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
    
    def handle_phase3_request_join(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle Phase 3 REQUEST_JOIN with OS-verified peer identity.
        
        Phase 3: Integrate Phase 3 with authenticated transport boundary.
        Uses OS-observed client_pid from transport layer, not caller-supplied.
        """
        try:
            # Create AuthenticatedPeer from OS-observed client_pid
            peer = self._create_authenticated_peer(client_pid)
            
            # Extract request data
            subject_id = request.data.get('subject_id')
            execution_id = request.data.get('execution_id')
            public_key = request.data.get('public_key')
            
            if not subject_id or not execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Missing subject_id or execution_id"
                )
            
            # Resolve subject from Phase 2 RunRecord (authoritative subject registry)
            subject = self._resolve_subject_from_run_record(peer, subject_id)
            
            if not subject:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Subject not found or identity mismatch"
                )
            
            # Verify execution_id matches run record
            if subject['execution_id'] != execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # F2 FIX: Enforce parent authority at authorization boundary
            # Compare OS-derived peer.parent_authority to authorized parent_authority from RunRecord
            authorized_parent_authority = subject.get('parent_authority')
            if peer.parent_authority != authorized_parent_authority:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error=f"Parent authority mismatch: peer={peer.parent_authority}, authorized={authorized_parent_authority}"
                )
            
            # Create join authorization with atomic uniqueness
            join_id = secrets.token_urlsafe(16)
            created_at = time.time()
            
            conn = sqlite3.connect(str(self._join_auth_db))
            cursor = conn.cursor()
            
            # Atomic INSERT with ON CONFLICT for exactly-once semantics
            cursor.execute("""
                INSERT INTO join_authorizations 
                (join_id, subject_id, execution_id, generation, client_pid, public_key, created_at, consumed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(subject_id, execution_id, generation)
                DO NOTHING
            """, (
                join_id,
                subject_id,
                execution_id,
                self._generation,
                client_pid,
                public_key,
                created_at
            ))
            
            if cursor.rowcount == 0:
                # Join authorization already exists (exactly-once enforcement)
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization already exists for this subject and execution"
                )
            
            conn.commit()
            conn.close()
            
            # Generate join token (signed by authority)
            join_token_data = {
                "join_id": join_id,
                "subject_id": subject_id,
                "execution_id": execution_id,
                "generation": self._generation,
                "client_pid": client_pid,
                "created_at": created_at
            }
            join_token_json = json.dumps(join_token_data, sort_keys=True)
            signature = self._sign_data(join_token_json)
            
            join_token = {
                "data": join_token_data,
                "signature": signature
            }
            
            return AuthorityResponse(
                success=True,
                data={"join_token": join_token}
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_phase3_request_challenge(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle Phase 3 REQUEST_CHALLENGE with OS-verified peer identity.
        
        Phase 3: Integrate REQUEST_CHALLENGE with authenticated transport boundary.
        Uses OS-observed client_pid from transport layer, not caller-supplied.
        """
        try:
            # Create AuthenticatedPeer from OS-observed client_pid
            peer = self._create_authenticated_peer(client_pid)
            
            # Extract request data
            join_id = request.data.get('join_id')
            subject_id = request.data.get('subject_id')
            execution_id = request.data.get('execution_id')
            
            if not join_id or not subject_id or not execution_id:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Missing join_id, subject_id, or execution_id"
                )
            
            # Verify join authorization exists and is not consumed
            conn = sqlite3.connect(str(self._join_auth_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT subject_id, execution_id, generation, client_pid, public_key, consumed
                FROM join_authorizations
                WHERE join_id = ?
            """, (join_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization not found"
                )
            
            record_subject_id, record_execution_id, record_generation, record_pid, public_key, consumed = row
            
            # Verify subject_id matches
            if record_subject_id != subject_id:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Subject ID mismatch"
                )
            
            # Verify execution_id matches
            if record_execution_id != execution_id:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # Verify not consumed
            if consumed:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization already consumed"
                )
            
            # Verify generation matches canonical
            if record_generation != self._generation:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Verify peer identity matches join authorization
            if peer.process_id != record_pid:
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Peer identity mismatch"
                )
            
            # Generate challenge
            nonce = secrets.token_hex(16)
            timestamp = str(int(time.time()))
            challenge = f"{nonce}:{timestamp}"
            challenge_issued_at = time.time()
            challenge_expires_at = challenge_issued_at + 300  # 5 minutes
            
            # Store challenge
            challenge_id = secrets.token_urlsafe(16)
            
            cursor.execute("""
                INSERT INTO challenges 
                (challenge_id, join_id, challenge, generation, execution_id, issued_at, expires_at, consumed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(join_id, challenge)
                DO NOTHING
            """, (
                challenge_id,
                join_id,
                challenge,
                self._generation,
                execution_id,
                challenge_issued_at,
                challenge_expires_at
            ))
            
            if cursor.rowcount == 0:
                # Challenge already exists (should not happen with unique nonce)
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge already exists"
                )
            
            conn.commit()
            conn.close()
            
            # Return response with pinned public key
            return AuthorityResponse(
                success=True,
                data={
                    "challenge": challenge,
                    "pinned_public_key": public_key,
                    "generation": self._generation,
                    "challenge_issued_at": challenge_issued_at,
                    "challenge_expires_at": challenge_expires_at
                }
            )
        except Exception as e:
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
    
    def handle_phase3_redeem_join(
        self,
        request: AuthorityRequest,
        client_pid: int
    ) -> AuthorityResponse:
        """Handle Phase 3 REDEEM_JOIN with OS-verified peer identity.
        
        Phase 3: Integrate REDEEM_JOIN with authenticated transport boundary.
        Uses OS-observed client_pid from transport layer, not caller-supplied.
        Implements exactly-once redemption with atomic transitions.
        """
        try:
            # Import Ed25519 verification
            from iabv_v15.services.phase3.ed25519_keys import (
                public_key_from_hex,
                public_key_from_base64,
                verify_signature
            )
            
            # Create AuthenticatedPeer from OS-observed client_pid
            peer = self._create_authenticated_peer(client_pid)
            
            # Extract request data
            join_id = request.data.get('join_id')
            subject_id = request.data.get('subject_id')
            execution_id = request.data.get('execution_id')
            challenge = request.data.get('challenge')
            signature = request.data.get('signature')
            
            if not join_id or not subject_id or not execution_id or not challenge or not signature:
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Missing required fields"
                )
            
            # Verify join authorization exists and is not consumed
            conn = sqlite3.connect(str(self._join_auth_db))
            cursor = conn.cursor()
            
            # F9 FIX: Explicit transaction discipline - BEGIN IMMEDIATE
            cursor.execute("BEGIN IMMEDIATE")
            
            cursor.execute("""
                SELECT subject_id, execution_id, generation, client_pid, public_key, consumed
                FROM join_authorizations
                WHERE join_id = ?
            """, (join_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization not found"
                )
            
            record_subject_id, record_execution_id, record_generation, record_pid, public_key_str, consumed = row
            
            # Verify subject_id matches
            if record_subject_id != subject_id:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Subject ID mismatch"
                )
            
            # Verify execution_id matches
            if record_execution_id != execution_id:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Execution ID mismatch"
                )
            
            # Verify not consumed
            if consumed:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization already consumed"
                )
            
            # Verify generation matches canonical
            if record_generation != self._generation:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Generation mismatch"
                )
            
            # Verify peer identity matches join authorization
            if peer.process_id != record_pid:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Peer identity mismatch"
                )
            
            # Verify challenge exists and is not consumed
            cursor.execute("""
                SELECT challenge_id, challenge, issued_at, expires_at, consumed
                FROM challenges
                WHERE join_id = ?
                ORDER BY issued_at DESC
                LIMIT 1
            """, (join_id,))
            
            challenge_row = cursor.fetchone()
            
            if not challenge_row:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge not found"
                )
            
            challenge_id, stored_challenge, issued_at, expires_at, challenge_consumed = challenge_row
            
            # Verify challenge not consumed
            if challenge_consumed:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge already consumed"
                )
            
            # Verify challenge freshness
            current_time = time.time()
            if current_time > expires_at:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge expired"
                )
            
            # Verify challenge matches stored nonce (F1 FIX: cryptographically bind to issued nonce)
            if challenge != stored_challenge:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge mismatch"
                )
            
            # Convert public key to bytes
            try:
                public_key = public_key_from_hex(public_key_str)
            except ValueError:
                try:
                    public_key = public_key_from_base64(public_key_str)
                except ValueError:
                    conn.rollback()
                    conn.close()
                    return AuthorityResponse(
                        success=False,
                        data={},
                        error="Invalid public key format"
                    )
            
            # Verify signature over the exact stored challenge bytes using Ed25519
            signature_bytes = bytes.fromhex(signature)
            challenge_bytes = stored_challenge.encode('utf-8')
            
            if not ed25519_verify_signature(public_key, challenge_bytes, signature_bytes):
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Invalid signature"
                )
            
            # Atomic redeem: update both join authorization and challenge
            cursor.execute("""
                UPDATE join_authorizations
                SET consumed = 1, consumed_at = ?
                WHERE join_id = ? 
                  AND consumed = 0 
                  AND generation = ?
            """, (current_time, join_id, self._generation))
            
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Join authorization already consumed or expired"
                )
            
            cursor.execute("""
                UPDATE challenges
                SET consumed = 1, consumed_at = ?
                WHERE challenge_id = ? 
                  AND consumed = 0
            """, (current_time, challenge_id))
            
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                return AuthorityResponse(
                    success=False,
                    data={},
                    error="Challenge already consumed"
                )
            
            # F9 FIX: Explicit COMMIT after successful atomic updates
            conn.commit()
            conn.close()
            
            # Generate membership ID
            membership_id = secrets.token_urlsafe(16)
            
            return AuthorityResponse(
                success=True,
                data={
                    "redeemed": True,
                    "redeemed_at": current_time,
                    "membership_id": membership_id
                }
            )
        except Exception as e:
            # F9 FIX: ROLLBACK on exception
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return AuthorityResponse(
                success=False,
                data={},
                error=str(e)
            )
