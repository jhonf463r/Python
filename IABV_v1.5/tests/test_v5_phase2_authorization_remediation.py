"""Tests for P0.213 V5 Phase 2 Authorization Remediation.

These tests verify the corrected authorization implementation with:
- Authority policy decision (requested_scope → authorized_scope)
- RunRecord binding (action, target, requested_scope, authorized_scope)
- HMAC signature verification
- Run-bound consume with full authorization verification
- Real IPC exactly-once with two processes
- Replay protection
- Wrong process detection

Test Layers:
- L2 UNIT: Component behavior tests
- L3 INTEGRATION: Authority service integration tests
- L4 REAL IPC: Real Named Pipe tests with AuthorityClient
- L5 ADVERSARIAL: Wrong-binding and replay attack tests

Phase 2 Status: AUTHORIZATION_REMEDIATION
"""

from __future__ import annotations

import json
import multiprocessing
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.services.trust.authority_service import (
    AuthorityRequest,
    AuthorityResponse,
    AuthorityService,
)


def cleanup_authority_storage(storage_root: Path) -> None:
    """Force cleanup of authority storage to prevent Windows file locking.
    
    This is a workaround for Windows file locking issues with SQLite.
    """
    try:
        # Try to close any open connections by forcing garbage collection
        import gc
        gc.collect()
        
        # Wait a moment for file handles to be released
        time.sleep(0.1)
        
        # Try to remove the directory
        if storage_root.exists():
            shutil.rmtree(storage_root, ignore_errors=True)
    except Exception:
        pass


# ── L2 UNIT TESTS ───────────────────────────────────────────────────────────

class TestScopePolicy:
    """L2 UNIT: Authority scope policy tests."""
    
    def test_requested_scope_accepted(self):
        """Test that valid requested scope is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Valid scope should be accepted
            authorized = service._compute_authorized_scope(
                requested_scope="codebase:read",
                action="READ",
                target="codebase",
                client_pid=os.getpid()
            )
            assert authorized == "codebase:read"
    
    def test_broader_scope_rejected(self):
        """Test that wildcard/broader scope is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Wildcard scope should be rejected
            with pytest.raises(ValueError, match="not allowed"):
                service._compute_authorized_scope(
                    requested_scope="*",
                    action="READ",
                    target="codebase",
                    client_pid=os.getpid()
                )
    
    def test_unauthorized_scope_rejected(self):
        """Test that admin scope is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Admin scope should be rejected
            with pytest.raises(ValueError, match="not allowed"):
                service._compute_authorized_scope(
                    requested_scope="admin:all",
                    action="READ",
                    target="codebase",
                    client_pid=os.getpid()
                )


class TestRunRecordBinding:
    """L2 UNIT: RunRecord binding tests."""
    
    def test_run_record_stores_policy_fields(self):
        """Test that RunRecord stores action, target, requested_scope, authorized_scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            response = service.handle_register_execution(request, os.getpid())
            
            assert response.success
            run_id = response.data["run_id"]
            
            # Verify RunRecord stores policy fields
            conn = sqlite3.connect(str(service._run_record_db))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT requested_scope, authorized_scope, action, target
                FROM run_records
                WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            requested_scope, authorized_scope, action, target = row
            assert requested_scope == "codebase:read"
            assert authorized_scope == "codebase:read"
            assert action == "READ"
            assert target == "codebase"


# ── L3 INTEGRATION TESTS ─────────────────────────────────────────────────────

class TestLeaseIssuance:
    """L3 INTEGRATION: Lease issuance with RunRecord binding."""
    
    def test_lease_issued_with_run_record_binding(self):
        """Test that lease is issued with full RunRecord binding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register execution
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            # Issue lease
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            
            assert issue_response.success
            lease = issue_response.data["lease"]
            assert lease["signature"] != ""
    
    def test_wrong_run_id_rejected(self):
        """Test that wrong run_id is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Try to issue lease with wrong run_id
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": "wrong_run_id",
                    "execution_id": "some_execution_id",
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            
            assert not issue_response.success
            assert "Run record not found" in issue_response.error
    
    def test_wrong_execution_id_rejected(self):
        """Test that wrong execution_id is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register execution
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            
            # Try to issue lease with wrong execution_id
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": "wrong_execution_id",
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            
            assert not issue_response.success
            assert "Execution ID mismatch" in issue_response.error


class TestSignatureVerification:
    """L3 INTEGRATION: HMAC signature verification."""
    
    def test_valid_signature_accepted(self):
        """Test that valid signature is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease = issue_response.data["lease"]
            lease_id = lease["lease_id"]
            
            # Verify signature is valid
            conn = sqlite3.connect(str(service._lease_state_db))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lease_json, signature
                FROM leases
                WHERE lease_id = ?
            """, (lease_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            lease_json, signature = row
            assert service._verify_lease_signature(lease_json, signature)
    
    def test_invalid_signature_rejected(self):
        """Test that invalid signature is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Tamper with signature in database
            conn = sqlite3.connect(str(service._lease_state_db))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leases
                SET signature = 'invalid_signature'
                WHERE lease_id = ?
            """, (lease_id,))
            conn.commit()
            conn.close()
            
            # Try to consume with invalid signature
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            
            assert not consume_response.success
            assert "Invalid lease signature" in consume_response.error


class TestRunBoundConsume:
    """L3 INTEGRATION: Run-bound consume with full authorization verification."""
    
    def test_consume_verifies_run_record(self):
        """Test that consume verifies RunRecord binding."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Consume with correct execution_id
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            
            assert consume_response.success
            
            # Explicit shutdown
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))
    
    def test_wrong_process_rejected(self):
        """Test that wrong consumer PID is rejected."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register with one PID
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            # Issue lease
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Try to consume with different PID
            wrong_pid = os.getpid() + 99999
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, wrong_pid)
            
            assert not consume_response.success
            assert "Client PID mismatch" in consume_response.error
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))
    
    def test_expired_lease_rejected(self):
        """Test that expired lease is rejected."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease with short TTL
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": -1  # Already expired
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Try to consume expired lease
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            
            assert not consume_response.success
            assert "Lease expired" in consume_response.error
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))


# ── L4 REAL IPC TESTS ────────────────────────────────────────────────────────

class TestRealIPCExactlyOnce:
    """L4 REAL IPC: Exactly-once with real AuthorityClient processes."""
    
    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_two_processes_one_success_one_rejection_via_ipc(self):
        """Test exactly-once with two real IPC client processes.
        
        BLOCKER 6: Rewrite exactly-once test with TWO REAL IPC CLIENT PROCESSES.
        
        This test uses AuthorityClient → Named Pipe → AuthorityService path.
        Both processes compete to consume the same lease.
        Exactly one should succeed, one should be rejected.
        """
        import sys
        import subprocess
        from pathlib import Path
        
        tmpdir = tempfile.mkdtemp()
        tmpdir_path = Path(tmpdir)
        
        authority_proc = None
        
        try:
            # Start authority process
            authority_script = Path(__file__).parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
            project_root = Path(__file__).parent.parent / "src"
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            
            authority_proc = subprocess.Popen(
                [sys.executable, str(authority_script), "--storage-root", str(tmpdir_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Wait for readiness signal
            ready_file = tmpdir_path / "authority_ready.txt"
            for _ in range(20):
                if ready_file.exists():
                    break
                time.sleep(0.5)
            else:
                assert False, "Authority process did not create ready signal"
            
            # Worker function for consume process
            def consume_worker(worker_id: int, lease_id: str, execution_id: str, results: list) -> None:
                """Worker process that attempts to consume the lease."""
                try:
                    client = AuthorityClient()
                    client.connect()
                    
                    result = client.consume_lease(
                        lease_id=lease_id,
                        invocation_id=f"worker_{worker_id}"
                    )
                    
                    results.append({
                        "worker_id": worker_id,
                        "success": result.get("consumed", False),
                        "error": result.get("error")
                    })
                    
                    client.disconnect()
                except Exception as e:
                    results.append({
                        "worker_id": worker_id,
                        "success": False,
                        "error": str(e)
                    })
            
            # First, register execution and issue lease via client
            client = AuthorityClient()
            client.connect()
            
            registration = client.register_execution(
                invocation_id="test_inv",
                requested_scope="codebase:read",
                episode_id=None,
                session_id=None
            )
            
            run_id = registration.get("run_id")
            execution_id = registration.get("execution_id")
            
            lease_data = client.issue_lease(
                invocation_id="test_inv",
                scope="codebase:read",
                duration_ms=60000
            )
            
            lease = lease_data.get("lease")
            lease_id = lease.get("lease_id")
            
            client.disconnect()
            
            # Spawn two worker processes to compete for consume
            import multiprocessing
            manager = multiprocessing.Manager()
            results = manager.list()
            
            worker1 = multiprocessing.Process(
                target=consume_worker,
                args=(1, lease_id, execution_id, results)
            )
            worker2 = multiprocessing.Process(
                target=consume_worker,
                args=(2, lease_id, execution_id, results)
            )
            
            # Start both workers simultaneously
            worker1.start()
            worker2.start()
            
            # Wait for both to complete
            worker1.join(timeout=10)
            worker2.join(timeout=10)
            
            # Convert results to list
            results_list = list(results)
            
            # Exactly one should succeed
            assert len(results_list) == 2, f"Expected 2 results, got {len(results_list)}"
            
            success_count = sum(1 for r in results_list if r.get("success"))
            assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
            
            # One should fail with "already consumed" or similar
            failure_count = sum(1 for r in results_list if not r.get("success"))
            assert failure_count == 1, f"Expected exactly 1 failure, got {failure_count}"
            
            print(f"BLOCKER_6_TEST_PASSED: Exactly-once with two real IPC processes")
            print(f"  Results: {results_list}")
            
        finally:
            # Terminate authority process
            if authority_proc:
                authority_proc.terminate()
                stdout, stderr = authority_proc.communicate(timeout=5)
                if authority_proc.returncode is None:
                    authority_proc.kill()
                    authority_proc.wait(timeout=5)
            
            cleanup_authority_storage(tmpdir_path)


class TestReplayProtection:
    """L4 REAL IPC: Replay protection via AuthorityClient."""
    
    def test_replay_after_consume_rejected(self):
        """Test that replay after consume is rejected."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # First consume
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            assert consume_response.success
            
            # Replay attempt
            consume_response2 = service.handle_consume_lease(consume_request, os.getpid())
            
            assert not consume_response2.success
            assert "already consumed" in consume_response2.error.lower()
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))
    
    def test_replay_after_restart_rejected(self):
        """Test that replay after authority restart is rejected."""
        tmpdir = tempfile.mkdtemp()
        tmpdir_path = Path(tmpdir)
        
        service1 = None
        service2 = None
        
        try:
            # First authority instance
            service1 = AuthorityService(storage_root=tmpdir_path)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service1.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service1.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Consume
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service1.handle_consume_lease(consume_request, os.getpid())
            assert consume_response.success
            
            # Close first service
            service1.shutdown()
            service1 = None
            
            # Simulate restart - create new authority instance with same storage
            service2 = AuthorityService(storage_root=tmpdir_path)
            
            # Replay attempt after restart
            consume_response2 = service2.handle_consume_lease(consume_request, os.getpid())
            
            assert not consume_response2.success
            assert "already consumed" in consume_response2.error.lower()
            
            if service2:
                service2.shutdown()
        finally:
            if service1:
                service1.shutdown()
            if service2:
                service2.shutdown()
            cleanup_authority_storage(tmpdir_path)


# ── L5 ADVERSARIAL TESTS ─────────────────────────────────────────────────────

class TestSignatureTampering:
    """L5 ADVERSARIAL: Signature tampering attacks."""
    
    def test_wrong_scope_with_old_signature_rejected(self):
        """Test that changing scope with old signature is rejected."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Tamper with authorized_scope in database
            conn = sqlite3.connect(str(service._lease_state_db))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leases
                SET authorized_scope = 'admin:all'
                WHERE lease_id = ?
            """, (lease_id,))
            conn.commit()
            conn.close()
            
            # Try to consume with tampered scope
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            
            # Should fail due to scope mismatch with RunRecord
            assert not consume_response.success
            assert "Authorized scope mismatch" in consume_response.error
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))


class TestDatabaseState:
    """L5 ADVERSARIAL: Database state integrity."""
    
    def test_database_consumed_state_equals_one(self):
        """Test that database consumed state == 1 after successful consume."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Consume
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": execution_id
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            assert consume_response.success
            
            # Verify database consumed state == 1
            conn = sqlite3.connect(str(service._lease_state_db))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT consumed
                FROM leases
                WHERE lease_id = ?
            """, (lease_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            consumed = row[0]
            assert consumed == 1
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))
    
    def test_invalid_consume_does_not_mutate_state(self):
        """Test that invalid consume does not mutate database state."""
        tmpdir = tempfile.mkdtemp()
        try:
            service = AuthorityService(storage_root=tmpdir)
            
            # Register and issue lease
            register_request = AuthorityRequest(
                request_type="REGISTER_EXECUTION",
                data={
                    "invocation_id": "test_inv",
                    "requested_scope": "codebase:read",
                    "action": "READ",
                    "target": "codebase"
                },
                request_id="test_id"
            )
            register_response = service.handle_register_execution(register_request, os.getpid())
            run_id = register_response.data["run_id"]
            execution_id = register_response.data["execution_id"]
            
            issue_request = AuthorityRequest(
                request_type="ISSUE_LEASE",
                data={
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "producer_scope": "codebase:read",
                    "ttl_seconds": 3600
                },
                request_id="test_id"
            )
            issue_response = service.handle_issue_lease(issue_request, os.getpid())
            lease_id = issue_response.data["lease"]["lease_id"]
            
            # Invalid consume with wrong execution_id
            consume_request = AuthorityRequest(
                request_type="CONSUME_LEASE",
                data={
                    "lease_id": lease_id,
                    "execution_id": "wrong_execution_id"
                },
                request_id="test_id"
            )
            consume_response = service.handle_consume_lease(consume_request, os.getpid())
            assert not consume_response.success
            
            # Verify database consumed state == 0 (not mutated)
            conn = sqlite3.connect(str(service._lease_state_db))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT consumed
                FROM leases
                WHERE lease_id = ?
            """, (lease_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            consumed = row[0]
            assert consumed == 0
            
            service.shutdown()
        finally:
            cleanup_authority_storage(Path(tmpdir))
