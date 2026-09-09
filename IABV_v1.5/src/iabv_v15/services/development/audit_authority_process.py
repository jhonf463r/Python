"""P0-B V4 Separate Audit Authority Process.

This module implements the authority process that runs separately from the caller
process and provides cryptographically signed audit records via IPC.

P0-B V4 Authority Process:
- Separate process from caller
- Owns Ed25519 private key (never shared)
- Verifies Git evidence independently
- Derives audit semantics
- Signs and returns SignedAuditRecord
- Stores audit records locally (replay prevention)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption,
)

# F14 V4-r3 FIX: Windows DPAPI for private key protection
# F14 V4-r3 FIX: NO plaintext fallback - fail closed if DPAPI unavailable
try:
    import win32crypt
    DPAPI_AVAILABLE = True
except ImportError:
    DPAPI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("win32crypt not available - private key protection not available on this platform")

# F14 V4-r3 TEST MODE: Allow test-only mode that skips DPAPI for unit tests
DPAPI_TEST_MODE = os.environ.get("IABV_DPAPI_TEST_MODE", "0") == "1"

# F1 FIX: Self-contained V4 IPC implementation (no cross-branch dependency)
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuthorityIpcMessage:
    """IPC message for audit authority communication."""
    
    message_type: str  # "CERTIFY", "GET_PUBLIC_KEY", "HEALTH"
    payload: dict[str, Any]


class AuthorityNamedPipe:
    """Self-contained Windows named pipe for audit authority IPC.
    
    F1 FIX: Minimal implementation specific to V4 authority process.
    No dependency on unrelated IPC infrastructure.
    """
    
    def __init__(self, pipe_name: str, timeout_seconds: int = 30):
        """Initialize authority named pipe.
        
        Args:
            pipe_name: Windows named pipe name
            timeout_seconds: Timeout for connection operations
        """
        self.pipe_name = pipe_name
        self.timeout_seconds = timeout_seconds
        self._handle = None
    
    def create_server(self) -> "_AuthorityNamedPipeServer":
        """Create authority named pipe server."""
        return _AuthorityNamedPipeServer(self.pipe_name, self.timeout_seconds)
    
    def create_client(self) -> "_AuthorityNamedPipeClient":
        """Create authority named pipe client."""
        return _AuthorityNamedPipeClient(self.pipe_name, self.timeout_seconds)


class _AuthorityNamedPipeServer:
    """Authority named pipe server."""
    
    def __init__(self, pipe_name: str, timeout_seconds: int):
        self.pipe_name = pipe_name
        self.timeout_seconds = timeout_seconds
        self._handle = None
    
    def wait_for_connection(self) -> bool:
        """Wait for client connection."""
        try:
            import win32pipe
            import win32file
            import win32security
            
            # Create security descriptor (restrict to local user)
            security_descriptor = win32security.SECURITY_DESCRIPTOR()
            security_descriptor.Initialize()
            security_descriptor.SetSecurityDescriptorOwner(
                win32security.GetUserNameEx(win32security.NameSamCompatible),
                False
            )
            
            dacl = win32security.ACL()
            user_sid = win32security.LookupAccountName(None, win32security.GetUserNameEx(win32security.NameSamCompatible))[0]
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                user_sid
            )
            security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)
            
            # Create named pipe
            self._handle = win32pipe.CreateNamedPipe(
                self.pipe_name,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1,  # max instances
                65536,  # output buffer
                65536,  # input buffer
                0,  # default timeout
                security_descriptor,
            )
            
            # Wait for client connection
            win32pipe.ConnectNamedPipe(self._handle, None)
            logger.info("Authority IPC server: client connected")
            return True
            
        except Exception as exc:
            logger.error("Authority IPC server: connection failed: %s", exc)
            return False
    
    def send_message(self, message: AuthorityIpcMessage) -> bool:
        """Send message to client."""
        try:
            import win32file
            
            message_dict = {
                "message_type": message.message_type,
                "payload": message.payload
            }
            message_json = json.dumps(message_dict).encode('utf-8')
            win32file.WriteFile(self._handle, message_json)
            logger.info("Authority IPC server: sent message")
            return True
            
        except Exception as exc:
            logger.error("Authority IPC server: send failed: %s", exc)
            return False
    
    def receive_message(self) -> AuthorityIpcMessage | None:
        """Receive message from client."""
        try:
            import win32file
            
            _, data = win32file.ReadFile(self._handle, 65536)
            message_dict = json.loads(data.decode('utf-8'))
            
            message = AuthorityIpcMessage(
                message_type=message_dict["message_type"],
                payload=message_dict["payload"]
            )
            logger.info("Authority IPC server: received message")
            return message
            
        except Exception as exc:
            logger.error("Authority IPC server: receive failed: %s", exc)
            return None
    
    def disconnect(self) -> None:
        """Disconnect client."""
        try:
            import win32pipe
            win32pipe.DisconnectNamedPipe(self._handle)
            logger.info("Authority IPC server: disconnected")
        except Exception:
            pass
    
    def close(self) -> None:
        """Close named pipe."""
        if self._handle is not None:
            try:
                import win32file
                win32file.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None


class _AuthorityNamedPipeClient:
    """Authority named pipe client."""
    
    def __init__(self, pipe_name: str, timeout_seconds: int):
        self.pipe_name = pipe_name
        self.timeout_seconds = timeout_seconds
        self._handle = None
    
    def connect(self) -> bool:
        """Connect to authority pipe."""
        try:
            import win32file
            import pywintypes
            
            start_time = time.time()
            while True:
                try:
                    self._handle = win32file.CreateFile(
                        self.pipe_name,
                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                        0,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None,
                    )
                    logger.info("Authority IPC client: connected")
                    return True
                except pywintypes.error as e:
                    if e.winerror == 2:  # File not found (pipe not ready)
                        if time.time() - start_time > self.timeout_seconds:
                            logger.error("Authority IPC client: timeout waiting for pipe")
                            return False
                        time.sleep(0.1)
                    else:
                        raise
            
        except Exception as exc:
            logger.error("Authority IPC client: connection failed: %s", exc)
            return False
    
    def send_message(self, message: AuthorityIpcMessage) -> bool:
        """Send message to authority."""
        try:
            import win32file
            
            message_dict = {
                "message_type": message.message_type,
                "payload": message.payload
            }
            message_json = json.dumps(message_dict).encode('utf-8')
            win32file.WriteFile(self._handle, message_json)
            logger.info("Authority IPC client: sent message")
            return True
            
        except Exception as exc:
            logger.error("Authority IPC client: send failed: %s", exc)
            return False
    
    def receive_message(self) -> AuthorityIpcMessage | None:
        """Receive message from authority."""
        try:
            import win32file
            
            _, data = win32file.ReadFile(self._handle, 65536)
            message_dict = json.loads(data.decode('utf-8'))
            
            message = AuthorityIpcMessage(
                message_type=message_dict["message_type"],
                payload=message_dict["payload"]
            )
            logger.info("Authority IPC client: received message")
            return message
            
        except Exception as exc:
            logger.error("Authority IPC client: receive failed: %s", exc)
            return None
    
    def close(self) -> None:
        """Close named pipe."""
        if self._handle is not None:
            try:
                import win32file
                win32file.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
from iabv_v15.services.development.authority_trust_config import AuthorityTrustConfig
from iabv_v15.services.development.git_evidence_verifier import GitEvidenceVerifier
from iabv_v15.services.development.signed_audit_record import (
    AuthorityKeyPair,
    SignedAuditRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class AuthorityRequest:
    """Request from caller to authority process."""
    
    request_type: str  # "CERTIFY", "GET_PUBLIC_KEY", "HEALTH"
    repository_path: str
    base_commit: str
    result_commit: str
    execution_status: str
    evidence_id: str
    claimed_changed_files: list[str] | None = None


@dataclass
class AuthorityResponse:
    """Response from authority process to caller."""
    
    response_type: str  # "CERTIFIED_RECORD", "PUBLIC_KEY", "HEALTH", "ERROR"
    success: bool
    signed_record: dict[str, Any] | None = None
    public_key: str | None = None
    error_message: str | None = None


class AuditAuthorityProcess:
    """Separate audit authority process with Ed25519 signing.
    
    P0-B V4: This process runs independently from the caller process.
    It owns the private key and provides signed audit records via IPC.
    """
    
    def __init__(
        self,
        storage_root: Path,
        pipe_name: str = r"\\.\pipe\IABV_AuditAuthority",
        expected_repository_identity: str | None = None,
    ):
        """Initialize audit authority process.
        
        Args:
            storage_root: Root directory for authority storage (record cache, trust config)
            pipe_name: Windows named pipe name for IPC
            expected_repository_identity: Expected repository identity for Git verification
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        self.pipe_name = pipe_name
        self.expected_repository_identity = expected_repository_identity
        
        # F7 FIX: Durable authority identity via trust config
        # F5 V4-r3 FIX: Use protected trust store location
        # Protected location: separate from ordinary application data
        protected_root = storage_root / "authority_protected"
        self._trust_config = AuthorityTrustConfig(protected_root)
        
        # Initialize or load durable keypair
        # F5 V4-r3 FIX: Store keypair in protected location
        config_root = storage_root / "authority_protected"
        config_root.mkdir(parents=True, exist_ok=True)
        self._keypair_file = config_root / "authority_keypair.json"
        
        self._keypair = self._load_or_create_keypair()
        
        # F5 V4-r3 FIX: Authority MUST be provisioned and identity must match for certification
        # Check if trust anchor exists and matches authority identity
        self._is_provisioned = False
        if self._trust_config.get_all_trusted_keys():
            if self._trust_config.verify_authority_identity_match(
                self._keypair.public_key_id,
                self._keypair.public_key
            ):
                self._is_provisioned = True
            else:
                logger.warning(
                    "Trust anchor exists but does not match authority identity. "
                    "Authority will fail closed during certification."
                )
        
        # Initialize record storage (SQLite for replay prevention)
        # F5 V4-r3 FIX: Store DB in protected location
        self._db_path = storage_root / "authority_protected" / "audit_records.db"
        self._init_database()
        
        logger.info("AuditAuthorityProcess initialized")
        logger.info("Public key ID: %s", self._keypair.public_key_id)
        logger.info("Durable identity: %s", self._keypair_file)
    
    def _load_or_create_keypair(self) -> AuthorityKeyPair:
        """Load durable keypair from storage or create new one.
        
        F7 FIX: Authority identity survives restart via durable key storage.
        F14 V4-r3 FIX: Private key protected with Windows DPAPI (NO plaintext fallback).
        
        Returns:
            AuthorityKeyPair (existing or newly created)
        
        Raises:
            RuntimeError: If private key protection unavailable or corrupted
        """
        # F14 V4-r3 TEST MODE: Allow test-only mode that skips DPAPI for unit tests
        if not DPAPI_AVAILABLE and not DPAPI_TEST_MODE:
            raise RuntimeError(
                "Private key protection requires Windows DPAPI (win32crypt). "
                "This platform is not supported for production authority operation."
            )
        
        if self._keypair_file.exists():
            try:
                with open(self._keypair_file, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                
                # F14 V4-r3 FIX: Decrypt private key using DPAPI
                if "private_key_protected" in key_data and DPAPI_AVAILABLE and not DPAPI_TEST_MODE:
                    encrypted_bytes = bytes.fromhex(key_data["private_key_protected"])
                    decrypted = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None, 0)
                    # CryptUnprotectData returns (data, description) tuple
                    if isinstance(decrypted, tuple):
                        decrypted_bytes = decrypted[0]
                    else:
                        decrypted_bytes = decrypted
                    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(decrypted_bytes)
                elif "private_key_hex" in key_data and DPAPI_TEST_MODE:
                    # F14 V4-r3 TEST MODE: Allow plaintext for tests only
                    private_key_bytes = bytes.fromhex(key_data["private_key_hex"])
                    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
                else:
                    # F14 V4-r3 FIX: No plaintext key allowed in production
                    raise RuntimeError(
                        "Protected key data not found in keypair file. "
                        "Plaintext key storage is not supported in V4-r3 production."
                    )
                
                # Reconstruct AuthorityKeyPair
                keypair = AuthorityKeyPair.__new__(AuthorityKeyPair)
                keypair._private_key = private_key
                keypair._public_key = private_key.public_key()
                keypair._public_key_id = key_data["public_key_id"]
                
                logger.info("Loaded durable keypair from: %s", self._keypair_file)
                return keypair
                
            except Exception as exc:
                logger.error("Failed to load keypair from storage: %s", exc)
                raise RuntimeError(f"Failed to load authority keypair: {exc}")
        
        # Create new keypair
        keypair = AuthorityKeyPair()
        
        # F14 V4-r3 FIX: Protect private key with DPAPI (no fallback in production)
        private_key_bytes = keypair._private_key.private_bytes(
            Encoding.Raw,
            PrivateFormat.Raw,
            NoEncryption()
        )
        
        if DPAPI_AVAILABLE and not DPAPI_TEST_MODE:
            encrypted_result = win32crypt.CryptProtectData(private_key_bytes, None, None, None, None, 0)
            if isinstance(encrypted_result, tuple):
                encrypted_bytes = encrypted_result[0]
            else:
                encrypted_bytes = encrypted_result
            protected_key_hex = encrypted_bytes.hex()
            key_data = {
                "public_key_id": keypair.public_key_id,
                "private_key_protected": protected_key_hex,
                "protection": "DPAPI",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        elif DPAPI_TEST_MODE:
            # F14 V4-r3 TEST MODE: Allow plaintext for tests only
            logger.warning("TEST MODE: Storing private key in plaintext")
            key_data = {
                "public_key_id": keypair.public_key_id,
                "private_key_hex": private_key_bytes.hex(),
                "protection": "plaintext_test_mode",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        else:
            raise RuntimeError(
                "Private key protection requires Windows DPAPI (win32crypt). "
                "This platform is not supported for production authority operation."
            )
        
        with open(self._keypair_file, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)
        
        logger.info("Created and stored durable keypair with %s protection: %s", 
                   key_data["protection"], self._keypair_file)
        return keypair
    
    def _init_database(self) -> None:
        """Initialize SQLite database for record storage (replay prevention)."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_records (
                audit_id TEXT PRIMARY KEY,
                evidence_fingerprint TEXT UNIQUE NOT NULL,
                record_json TEXT NOT NULL,
                created_at_utc TEXT NOT NULL
            )
        """)
        
        # Index for fingerprint lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fingerprint 
            ON audit_records(evidence_fingerprint)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Authority database initialized: %s", self._db_path)
    
    def _store_record(self, record: SignedAuditRecord) -> SignedAuditRecord:
        """Store signed record in database (replay prevention).
        
        F4 V4-r2 FIX: Atomic replay prevention with transaction.
        
        F4 FIX: Return authoritative record (new or existing) to caller.
        
        P0-B V4 Policy:
        - Same fingerprint → return previously stored authoritative record
        - Same audit_id + different fingerprint → reject
        - New fingerprint → create/sign/store/return new record
        - F4 V4-r2: Use atomic transaction to prevent race conditions
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        try:
            # F4 V4-r2 FIX: Use transaction for atomicity
            conn.execute("BEGIN TRANSACTION")
            
            # Check if same fingerprint already exists (replay)
            cursor.execute(
                "SELECT audit_id, record_json FROM audit_records WHERE evidence_fingerprint = ?",
                (record.evidence_fingerprint,)
            )
            existing = cursor.fetchone()
            
            if existing:
                existing_audit_id, existing_record_json = existing
                logger.info("Replay prevention: returning existing record for fingerprint %s", record.evidence_fingerprint)
                
                # Deserialize existing record and return it
                existing_dict = json.loads(existing_record_json)
                existing_record = SignedAuditRecord(
                    audit_id=existing_dict["audit_id"],
                    evidence_id=existing_dict["evidence_id"],
                    repository_identity=existing_dict["repository_identity"],
                    repository=existing_dict["repository"],
                    base_commit=existing_dict["base_commit"],
                    result_commit=existing_dict["result_commit"],
                    actual_changed_files=existing_dict["actual_changed_files"],
                    execution_status=existing_dict["execution_status"],
                    criteria=existing_dict["criteria"],
                    verdict=existing_dict["verdict"],
                    audited_at_utc=existing_dict["audited_at_utc"],
                    producer_public_key_id=existing_dict["producer_public_key_id"],
                    evidence_fingerprint=existing_dict["evidence_fingerprint"],
                    signature=bytes.fromhex(existing_dict["signature"]),
                    schema_version=existing_dict.get("schema_version", "1.0"),
                )
                conn.commit()
                conn.close()
                return existing_record
            
            # Check if audit_id already exists with different fingerprint (tampering)
            cursor.execute(
                "SELECT evidence_fingerprint FROM audit_records WHERE audit_id = ?",
                (record.audit_id,)
            )
            tampering_check = cursor.fetchone()
            
            if tampering_check:
                existing_fingerprint = tampering_check[0]
                if existing_fingerprint != record.evidence_fingerprint:
                    logger.error("Tampering detected: audit_id %s has different fingerprint", record.audit_id)
                    conn.rollback()
                    conn.close()
                    raise ValueError(f"audit_id {record.audit_id} already exists with different fingerprint")
            
            # Store new record
            record_dict = {
                "schema_version": record.schema_version,
                "audit_id": record.audit_id,
                "evidence_id": record.evidence_id,
                "repository_identity": record.repository_identity,
                "repository": record.repository,
                "base_commit": record.base_commit,
                "result_commit": record.result_commit,
                "actual_changed_files": record.actual_changed_files,
                "execution_status": record.execution_status,
                "criteria": record.criteria,
                "verdict": record.verdict,
                "audited_at_utc": record.audited_at_utc,
                "producer_public_key_id": record.producer_public_key_id,
                "evidence_fingerprint": record.evidence_fingerprint,
                "signature": record.signature.hex(),
            }
            
            record_json = json.dumps(record_dict)
            created_at = datetime.now(timezone.utc).isoformat()
            
            cursor.execute(
                "INSERT INTO audit_records (audit_id, evidence_fingerprint, record_json, created_at_utc) VALUES (?, ?, ?, ?)",
                (record.audit_id, record.evidence_fingerprint, record_json, created_at)
            )
            
            conn.commit()
            logger.info("Stored new audit record: %s", record.audit_id)
            return record
            
        except sqlite3.IntegrityError as exc:
            # F4 V4-r2 FIX: Handle concurrent duplicate fingerprint attempts
            logger.warning("Concurrent duplicate fingerprint detected: %s", record.evidence_fingerprint)
            conn.rollback()
            
            # Retry to fetch the existing record
            cursor.execute(
                "SELECT audit_id, record_json FROM audit_records WHERE evidence_fingerprint = ?",
                (record.evidence_fingerprint,)
            )
            existing = cursor.fetchone()
            
            if existing:
                existing_audit_id, existing_record_json = existing
                existing_dict = json.loads(existing_record_json)
                existing_record = SignedAuditRecord(
                    audit_id=existing_dict["audit_id"],
                    evidence_id=existing_dict["evidence_id"],
                    repository_identity=existing_dict["repository_identity"],
                    repository=existing_dict["repository"],
                    base_commit=existing_dict["base_commit"],
                    result_commit=existing_dict["result_commit"],
                    actual_changed_files=existing_dict["actual_changed_files"],
                    execution_status=existing_dict["execution_status"],
                    criteria=existing_dict["criteria"],
                    verdict=existing_dict["verdict"],
                    audited_at_utc=existing_dict["audited_at_utc"],
                    producer_public_key_id=existing_dict["producer_public_key_id"],
                    evidence_fingerprint=existing_dict["evidence_fingerprint"],
                    signature=bytes.fromhex(existing_dict["signature"]),
                    schema_version=existing_dict.get("schema_version", "1.0"),
                )
                conn.close()
                return existing_record
            else:
                conn.close()
                raise exc
                
        except Exception as exc:
            conn.rollback()
            conn.close()
            raise
    
    def certify(
        self,
        repository_path: str,
        base_commit: str,
        result_commit: str,
        execution_status: str,
        evidence_id: str,
        claimed_changed_files: list[str] | None = None,
    ) -> SignedAuditRecord:
        """Certify audit evidence and return signed record.
        
        F5 V4-r3 FIX: Authority must be provisioned before certification.
        
        F9 FIX: Authority-derived semantics only. Caller inputs are hints only.
        
        FIELD ORIGIN DOCUMENTATION:
        | Field                  | Origin          | Validation       | Signed? |
        | ---------------------- | --------------- | ---------------- | ------- |
        | repository_path        | caller          | authority        | yes     |
        | base_commit            | caller          | Git authority    | yes     |
        | result_commit          | caller          | Git authority    | yes     |
        | claimed_changed_files  | caller          | NOT trusted      | no as fact |
        | actual_changed_files   | Git authority   | authority        | yes     |
        | execution_status       | caller/context  | authority/domain | yes     |
        | criteria               | authority       | authority        | yes     |
        | verdict                | authority       | authority        | yes     |
        | evidence_fingerprint   | authority       | derived          | yes     |
        | signature              | authority       | cryptographic    | yes     |
        | producer_public_key_id | authority       | trust anchor     | yes     |
        
        P0-B V4 Authority-Side Validation:
        1. Validate request
        2. Verify repository identity
        3. Verify base/result commits
        4. Verify object types
        5. Verify ancestry
        6. Verify changed files (Git-derived, NOT caller-claimed)
        7. Verify diff classification
        8. Evaluate execution criteria
        9. Derive verdict
        10. Calculate fingerprint
        11. Canonicalize record
        12. Sign
        13. Return signed record
        """
        logger.info("Certifying evidence: %s", evidence_id)
        
        # F5 V4-r3 FIX: Authority must be provisioned before certification
        if not self._is_provisioned:
            raise RuntimeError(
                "Authority not provisioned. "
                "Trust anchor must be established via OS-authorized provisioning before authority can certify records. "
                "Run OSAuthorityProvisioner with administrative privileges to establish trust anchor."
            )
        
        # Step 1-6: Verify Git evidence (reusing existing GitEvidenceVerifier)
        verifier = GitEvidenceVerifier(repository_path, self.expected_repository_identity)
        git_verification = verifier.verify_execution(
            base_commit=base_commit,
            result_commit=result_commit,
            claimed_changed_files=claimed_changed_files,
        )
        
        # Step 7: Verify diff classification
        if git_verification.classification in [
            "INVALID_GIT_STATE",
            "UNVERIFIABLE_GIT_STATE",
        ]:
            raise ValueError(f"Git verification failed: {git_verification.classification}")
        
        # Step 8: Evaluate execution criteria (P0-A preservation)
        from iabv_v15.domain.models import GitDiffClassification, DevelopmentExecutionStatus
        
        try:
            status = DevelopmentExecutionStatus(execution_status)
        except ValueError:
            raise ValueError(f"Invalid execution_status: {execution_status}")
        
        criteria = []
        
        # Criterion 1: Execution completed (P0-A)
        # F3 V4-r2 FIX: Only COMPLETED status can satisfy execution_completed criterion
        completed_criterion = {
            "criterion_id": "execution_completed",
            "name": "Execution Completed",
            "description": "Development execution completed successfully (not failed, cancelled, error, timeout, or not_run)",
            "required": True,
            "status": "satisfied" if status == DevelopmentExecutionStatus.COMPLETED else "not_satisfied",
        }
        criteria.append(completed_criterion)
        
        # Criterion 2: Git state verifiable
        git_verifiable = {
            "criterion_id": "git_state_verifiable",
            "name": "Git State Verifiable",
            "description": "Git state could be verified",
            "required": True,
            "status": "satisfied" if git_verification.classification not in [
                GitDiffClassification.INVALID_GIT_STATE,
                GitDiffClassification.UNVERIFIABLE_GIT_STATE,
            ] else "not_satisfied",
        }
        criteria.append(git_verifiable)
        
        # Criterion 3: Valid change (if commits differ)
        if git_verification.classification == GitDiffClassification.NO_OP:
            no_op_criterion = {
                "criterion_id": "valid_change",
                "name": "Valid Change",
                "description": "Base and result commits differ with actual changes",
                "required": True,
                "status": "not_satisfied",
            }
            criteria.append(no_op_criterion)
        
        # Step 9: Derive verdict
        required_criteria = [c for c in criteria if c.get("required")]
        any_not_satisfied = any(c.get("status") == "not_satisfied" for c in required_criteria)
        
        verdict = "FAIL" if any_not_satisfied else "PASS"
        
        # Step 10: Calculate evidence fingerprint
        # F8 FIX: Use Git-derived actual_changed_files, NOT caller-supplied claimed_changed_files
        # Caller may provide claimed_changed_files for hinting, but authority must use Git facts
        actual_changed_files = git_verification.actual_changed_files or []
        fingerprint = SignedAuditRecord.calculate_evidence_fingerprint(
            repository_identity=git_verification.repository_identity or "unknown",
            evidence_id=evidence_id,
            base_commit=base_commit,
            result_commit=result_commit,
            actual_changed_files=actual_changed_files,
            execution_status=execution_status,
        )
        
        # Step 11-12: Create and sign record
        audit_id = str(uuid4())
        audited_at = datetime.now(timezone.utc).isoformat()
        
        record = SignedAuditRecord(
            schema_version="1.0",
            audit_id=audit_id,
            evidence_id=evidence_id,
            repository_identity=git_verification.repository_identity or "unknown",
            repository=repository_path,
            base_commit=base_commit,
            result_commit=result_commit,
            actual_changed_files=actual_changed_files,
            execution_status=execution_status,
            criteria=criteria,
            verdict=verdict,
            audited_at_utc=audited_at,
            producer_public_key_id=self._keypair.public_key_id,
            evidence_fingerprint=fingerprint,
            signature=b"",  # Placeholder, will be set after canonicalization
        )
        
        # Canonicalize and sign
        canonical_bytes = record.to_canonical_bytes()
        signature = self._keypair.sign(canonical_bytes)
        record.signature = signature
        
        # Step 13: Store record (replay prevention) and return authoritative record
        authoritative_record = self._store_record(record)
        
        logger.info("Certified: %s -> %s", authoritative_record.audit_id, authoritative_record.verdict)
        return authoritative_record
    
    def get_public_key(self) -> str:
        """Get public key in hex format for distribution."""
        return self._keypair.get_public_key_bytes().hex()
    
    def health(self) -> dict[str, Any]:
        """Health check for authority process."""
        return {
            "status": "healthy",
            "public_key_id": self._keypair.public_key_id,
            "storage_root": str(self.storage_root),
        }
    
    def run_ipc_server(self) -> None:
        """Run IPC server to handle certify requests.
        
        P0-B V4: This is the main entry point for the authority process.
        It uses Windows Named Pipes to receive requests and return signed records.
        """
        logger.info("Starting IPC server on %s", self.pipe_name)
        
        import win32pipe
        import win32file
        import win32security
        
        # Create security descriptor (restrict to local user)
        security_descriptor = win32security.SECURITY_DESCRIPTOR()
        security_descriptor.Initialize()
        security_descriptor.SetSecurityDescriptorOwner(
            win32security.GetUserNameEx(win32security.NameSamCompatible),
            False
        )
        
        dacl = win32security.ACL()
        user_sid = win32security.LookupAccountName(None, win32security.GetUserNameEx(win32security.NameSamCompatible))[0]
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            user_sid
        )
        security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)
        
        # Create named pipe
        pipe_handle = win32pipe.CreateNamedPipe(
            self.pipe_name,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1,  # max instances
            65536,  # output buffer
            65536,  # input buffer
            0,  # default timeout
            security_descriptor,
        )
        
        logger.info("IPC server ready, waiting for connections...")
        
        try:
            while True:
                # Wait for client connection
                win32pipe.ConnectNamedPipe(pipe_handle, None)
                
                try:
                    # Read request
                    _, data = win32file.ReadFile(pipe_handle, 65536)
                    request_dict = json.loads(data.decode('utf-8'))
                    
                    request = AuthorityRequest(**request_dict)
                    
                    # Handle request
                    if request.request_type == "CERTIFY":
                        record = self.certify(
                            repository_path=request.repository_path,
                            base_commit=request.base_commit,
                            result_commit=request.result_commit,
                            execution_status=request.execution_status,
                            evidence_id=request.evidence_id,
                            claimed_changed_files=request.claimed_changed_files,
                        )
                        
                        response = AuthorityResponse(
                            response_type="CERTIFIED_RECORD",
                            success=True,
                            signed_record={
                                "schema_version": record.schema_version,
                                "audit_id": record.audit_id,
                                "evidence_id": record.evidence_id,
                                "repository_identity": record.repository_identity,
                                "repository": record.repository,
                                "base_commit": record.base_commit,
                                "result_commit": record.result_commit,
                                "actual_changed_files": record.actual_changed_files,
                                "execution_status": record.execution_status,
                                "criteria": record.criteria,
                                "verdict": record.verdict,
                                "audited_at_utc": record.audited_at_utc,
                                "producer_public_key_id": record.producer_public_key_id,
                                "evidence_fingerprint": record.evidence_fingerprint,
                                "signature": record.signature.hex(),
                            },
                        )
                    
                    elif request.request_type == "GET_PUBLIC_KEY":
                        response = AuthorityResponse(
                            response_type="PUBLIC_KEY",
                            success=True,
                            public_key=self.get_public_key(),
                        )
                    
                    elif request.request_type == "HEALTH":
                        response = AuthorityResponse(
                            response_type="HEALTH",
                            success=True,
                            signed_record=self.health(),
                        )
                    
                    else:
                        response = AuthorityResponse(
                            response_type="ERROR",
                            success=False,
                            error_message=f"Unknown request type: {request.request_type}",
                        )
                    
                    # Send response
                    response_dict = {
                        "response_type": response.response_type,
                        "success": response.success,
                        "signed_record": response.signed_record,
                        "public_key": response.public_key,
                        "error_message": response.error_message,
                    }
                    response_json = json.dumps(response_dict).encode('utf-8')
                    win32file.WriteFile(pipe_handle, response_json)
                    
                except Exception as exc:
                    logger.error("Error handling request: %s", exc)
                    error_response = AuthorityResponse(
                        response_type="ERROR",
                        success=False,
                        error_message=str(exc),
                    )
                    error_dict = {
                        "response_type": error_response.response_type,
                        "success": error_response.success,
                        "error_message": error_response.error_message,
                    }
                    error_json = json.dumps(error_dict).encode('utf-8')
                    win32file.WriteFile(pipe_handle, error_json)
                
                finally:
                    # Disconnect client
                    win32pipe.DisconnectNamedPipe(pipe_handle)
        
        finally:
            win32file.CloseHandle(pipe_handle)
            logger.info("IPC server stopped")


def main():
    """Main entry point for authority process."""
    import argparse
    
    parser = argparse.ArgumentParser(description="IABV Audit Authority Process")
    parser.add_argument("--storage-root", required=True, help="Storage root directory")
    parser.add_argument("--pipe-name", default=r"\\.\pipe\IABV_AuditAuthority", help="Named pipe name")
    parser.add_argument("--expected-repository-identity", help="Expected repository identity")
    
    args = parser.parse_args()
    
    # Initialize authority process
    authority = AuditAuthorityProcess(
        storage_root=Path(args.storage_root),
        pipe_name=args.pipe_name,
        expected_repository_identity=args.expected_repository_identity,
    )
    
    # Run IPC server
    authority.run_ipc_server()


if __name__ == "__main__":
    main()