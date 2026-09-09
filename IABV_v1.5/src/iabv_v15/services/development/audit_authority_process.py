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

from iabv_v15.infra.ipc.ipc_channel import IpcMessage, WindowsNamedPipe
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
            storage_root: Root directory for authority storage (record cache, etc.)
            pipe_name: Windows named pipe name for IPC
            expected_repository_identity: Expected repository identity for Git verification
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        self.pipe_name = pipe_name
        self.expected_repository_identity = expected_repository_identity
        
        # Initialize keypair (authority-only, never shared)
        self._keypair = AuthorityKeyPair()
        
        # Initialize record storage (SQLite for replay prevention)
        self._db_path = self.storage_root / "authority_records.db"
        self._init_database()
        
        logger.info("AuditAuthorityProcess initialized")
        logger.info("Public key ID: %s", self._keypair.public_key_id)
    
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
    
    def _store_record(self, record: SignedAuditRecord) -> None:
        """Store signed record in database (replay prevention).
        
        P0-B V4 Policy:
        - Same fingerprint → return existing record
        - Same audit_id + different fingerprint → reject
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        try:
            # Check if same fingerprint already exists (replay)
            cursor.execute(
                "SELECT audit_id, record_json FROM audit_records WHERE evidence_fingerprint = ?",
                (record.evidence_fingerprint,)
            )
            existing = cursor.fetchone()
            
            if existing:
                existing_audit_id, existing_record_json = existing
                logger.info("Replay prevention: returning existing record for fingerprint %s", record.evidence_fingerprint)
                conn.close()
                return existing_record_json
            
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
            
        finally:
            conn.close()
    
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
        
        P0-B V4 Authority-Side Validation:
        1. Validate request
        2. Verify repository identity
        3. Verify base/result commits
        4. Verify object types
        5. Verify ancestry
        6. Verify changed files
        7. Verify diff classification
        8. Evaluate execution criteria
        9. Derive verdict
        10. Calculate fingerprint
        11. Canonicalize record
        12. Sign
        13. Return signed record
        """
        logger.info("Certifying evidence: %s", evidence_id)
        
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
        from iabv_v15.domain.models import GitDiffClassification, DevelopmentTestStatus
        
        try:
            status = DevelopmentTestStatus(execution_status)
        except ValueError:
            raise ValueError(f"Invalid execution_status: {execution_status}")
        
        criteria = []
        
        # Criterion 1: Execution completed (P0-A)
        completed_criterion = {
            "criterion_id": "execution_completed",
            "name": "Execution Completed",
            "description": "Development execution completed successfully (not failed or cancelled)",
            "required": True,
            "status": "satisfied" if status.value == "completed" else "not_satisfied",
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
        
        # Step 13: Store record (replay prevention)
        self._store_record(record)
        
        logger.info("Certified: %s -> %s", audit_id, verdict)
        return record
    
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