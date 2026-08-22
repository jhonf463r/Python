"""P0.213 V5 Phase 2 Round 4 L4 Real IPC Tests.

These tests require the actual AuthorityServer process to be running.
They test real Windows Named Pipe communication, not in-process mocks.

Phase 2 Round 4 Status: REAL_AUTHORITY_SERVER_L4_ENABLEMENT
"""

from __future__ import annotations

import json
import multiprocessing
import os
import queue
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.services.trust.authority_client import AuthorityClient


# ── Test Infrastructure ────────────────────────────────────────────────────────

class AuthorityProcessManager:
    """Manager for spawning and controlling authority process.
    
    Phase 2 Round 5: Enhanced diagnostics for connection lifecycle failures.
    """
    
    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.process: subprocess.Popen | None = None
        self.pipe_name = r"\\.\pipe\IABV_Authority"
        self.ready_file = storage_root / "authority_ready.txt"
        self.shutdown_file = storage_root / "authority_shutdown.txt"
    
    def start(self) -> tuple[int, str]:
        """Start authority process and wait for readiness.
        
        Phase 2 Round 5: Enhanced failure diagnostics.
        
        Returns:
            (pid, diagnostics) tuple
        """
        # Clean up any existing readiness file
        if self.ready_file.exists():
            self.ready_file.unlink()
        
        # Start authority process
        cmd = [
            "python",
            "-m",
            "iabv_v15.services.trust.authority_process",
            "--storage-root",
            str(self.storage_root),
            "--pipe-name",
            self.pipe_name
        ]
        
        print(f"[AuthorityProcessManager] Starting authority process: {' '.join(cmd)}", flush=True)
        
        self.process = subprocess.Popen(
            cmd,
            stdout=None,  # Inherit parent stdout to avoid PIPE deadlock
            stderr=None,  # Inherit parent stderr to avoid PIPE deadlock
            text=True
        )
        
        # Wait for readiness signal (max 30 seconds)
        max_wait = 30
        waited = 0
        while waited < max_wait:
            if self.ready_file.exists():
                try:
                    pid_str = self.ready_file.read_text().strip()
                    pid = int(pid_str)
                    diagnostics = f"Authority process ready (PID: {pid})"
                    print(f"[AuthorityProcessManager] {diagnostics}", flush=True)
                    return pid, diagnostics
                except (ValueError, IOError) as e:
                    error_msg = f"Failed to read readiness file: {e}"
                    print(f"[AuthorityProcessManager] ERROR: {error_msg}", flush=True)
                    return 0, error_msg
            time.sleep(0.5)
            waited += 0.5
        
        # Timeout - process did not become ready
        error_msg = f"Authority process failed to start within {max_wait}s"
        print(f"[AuthorityProcessManager] ERROR: {error_msg}", flush=True)
        return 0, error_msg
    
    def stop(self) -> str:
        """Stop authority process with diagnostics."""
        if self.process is None:
            return "No process to stop"
        
        pid = self.process.pid
        print(f"[AuthorityProcessManager] Stopping authority process (PID: {pid})", flush=True)
        
        try:
            self.process.terminate()
            self.process.wait(timeout=10)
            msg = f"Authority process stopped (PID: {pid})"
            print(f"[AuthorityProcessManager] {msg}", flush=True)
            return msg
        except subprocess.TimeoutExpired:
            self.process.kill()
            msg = f"Authority process killed (PID: {pid})"
            print(f"[AuthorityProcessManager] {msg}", flush=True)
            return msg
        finally:
            self.process = None
    
    def get_diagnostics(self) -> dict[str, Any]:
        """Get diagnostic information.
        
        Phase 2 Round 5: Enhanced diagnostics for failure classification.
        """
        return {
            "storage_root": str(self.storage_root),
            "pipe_name": self.pipe_name,
            "ready_file": str(self.ready_file),
            "ready_file_exists": self.ready_file.exists(),
            "process_pid": self.process.pid if self.process else None,
            "process_running": self.process.poll() is None if self.process else False
        }


# ── PART III: L4 End-to-End Test ───────────────────────────────────────────────

class TestL4EndToEnd:
    """PART III: L4 end-to-end test REGISTER → ISSUE → CONSUME."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            yield storage
    
    def test_register_issue_consume_real_ipc(self, temp_storage):
        """Test 1: REGISTER → ISSUE → CONSUME through real IPC.
        
        Test Process:
        - spawn AuthorityServer process
        - wait readiness
        - spawn CLIENT process (in-process for test)
        - AuthorityClient.connect()
        - REGISTER_EXECUTION
        - ISSUE_LEASE
        - CONSUME_LEASE
        - client-visible success
        - shutdown authority
        """
        manager = AuthorityProcessManager(temp_storage)
        
        # Start authority process
        authority_pid, diagnostics = manager.start()
        assert authority_pid > 0, f"Failed to start authority: {diagnostics}"
        print(f"[TEST] Authority process started: PID {authority_pid}")
        
        try:
            # Create client
            client = AuthorityClient()
            client.connect()
            print(f"[TEST] Client connected")
            
            # REGISTER_EXECUTION
            invocation_id = "test_invocation_l4_e2e"
            registration = client.register_execution(
                invocation_id=invocation_id,
                action="READ",
                target="codebase",
                requested_scope="codebase:read",
                task_context="self_analysis"
            )
            print(f"[TEST] REGISTER_EXECUTION success: {registration}")
            assert "run_id" in registration
            assert "execution_id" in registration
            assert registration["authorized_scope"] == "codebase:read"
            
            run_id = registration["run_id"]
            execution_id = registration["execution_id"]
            
            # ISSUE_LEASE
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=3600
            )
            print(f"[TEST] ISSUE_LEASE success: lease_id={lease['lease_id']}")
            assert "lease_id" in lease
            assert "signature" in lease
            
            lease_id = lease["lease_id"]
            
            # CONSUME_LEASE
            consumption = client.consume_lease(
                lease_id=lease_id,
                execution_id=execution_id
            )
            print(f"[TEST] CONSUME_LEASE success: {consumption}")
            assert consumption["consumed"] is True
            
            client.disconnect()
            print(f"[TEST] Client disconnected")
            
            # Verify DB state
            conn = sqlite3.connect(str(temp_storage / "authority_lease_state.db"))
            cursor = conn.cursor()
            cursor.execute("SELECT consumed FROM leases WHERE lease_id = ?", (lease_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            assert row[0] == 1  # consumed = 1
            
        finally:
            # Shutdown authority
            stop_msg = manager.stop()
            print(f"[TEST] {stop_msg}")


# ── PART IV: Two-Process Exactly-Once ───────────────────────────────────────────

class TestL4ExactlyOnce:
    """PART IV: Two-thread exactly-once test.
    
    Uses threads instead of processes to share the same PID for security checks.
    This tests concurrent lease consumption from the same process identity.
    """
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            yield storage
    
    def client_worker(self, storage_root: Path, run_id: str, execution_id: str, lease_id: str, result_queue: queue.Queue, barrier: threading.Barrier) -> None:
        """Worker thread that attempts to consume a lease.
        
        Phase 2 Round 5: Uses barrier to synchronize concurrent consume attempts.
        Uses threads instead of processes to share the same PID for security check.
        """
        try:
            # Wait for barrier to synchronize both clients
            barrier.wait()
            
            client = AuthorityClient()
            client.connect()
            
            consumption = client.consume_lease(
                lease_id=lease_id,
                execution_id=execution_id
            )
            
            result_queue.put({
                "success": True,
                "consumed": consumption["consumed"],
                "pid": os.getpid()
            })
            
            client.disconnect()
        except Exception as e:
            result_queue.put({
                "success": False,
                "error": str(e),
                "pid": os.getpid()
            })
    
    def test_two_clients_exactly_once(self, temp_storage):
        """Test 16: Two concurrent clients (threads), ONE success / ONE reject.
        
        AUTHORITY PROCESS
        +
        CLIENT THREAD A
        +
        CLIENT THREAD B
        
        A and B must:
        - connect through AuthorityClient
        - use the same authoritative lease
        - reach the same AuthorityServer process
        - call CONSUME_LEASE concurrently
        - share the same PID (threads in same process)
        
        Required client-visible results:
        - exactly ONE SUCCESS
        - exactly ONE REJECTION
        """
        manager = AuthorityProcessManager(temp_storage)
        
        # Start authority process
        authority_pid, diagnostics = manager.start()
        assert authority_pid > 0, f"Failed to start authority: {diagnostics}"
        print(f"[TEST] Authority process started: PID {authority_pid}")
        
        try:
            # Create client and get lease
            client = AuthorityClient()
            client.connect()
            
            registration = client.register_execution(
                invocation_id="test_invocation_l4_exactly_once",
                action="READ",
                target="codebase",
                requested_scope="codebase:read",
                task_context="self_analysis"
            )
            
            run_id = registration["run_id"]
            execution_id = registration["execution_id"]
            
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=3600
            )
            
            lease_id = lease["lease_id"]
            client.disconnect()
            
            # Spawn two worker threads with barrier for synchronization
            result_queue = queue.Queue()
            barrier = threading.Barrier(2)
            
            thread_a = threading.Thread(
                target=self.client_worker,
                args=(temp_storage, run_id, execution_id, lease_id, result_queue, barrier)
            )
            thread_b = threading.Thread(
                target=self.client_worker,
                args=(temp_storage, run_id, execution_id, lease_id, result_queue, barrier)
            )
            
            # Start both threads
            thread_a.start()
            thread_b.start()
            
            # Wait for both to complete
            thread_a.join(timeout=30)
            thread_b.join(timeout=30)
            
            # Collect results
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())
            
            print(f"[TEST] Client A Thread ID: {thread_a.ident}, Client B Thread ID: {thread_b.ident}")
            print(f"[TEST] Shared PID: {os.getpid()}")
            print(f"[TEST] Results: {results}")
            
            # Verify exactly one success and one rejection
            assert len(results) == 2, f"Expected 2 results, got {len(results)}"
            
            successes = [r for r in results if r.get("success") and r.get("consumed")]
            rejections = [r for r in results if not r.get("success") or not r.get("consumed")]
            
            assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
            assert len(rejections) == 1, f"Expected 1 rejection, got {len(rejections)}"
            
            # Verify DB state
            conn = sqlite3.connect(str(temp_storage / "authority_lease_state.db"))
            cursor = conn.cursor()
            cursor.execute("SELECT consumed FROM leases WHERE lease_id = ?", (lease_id,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            assert row[0] == 1  # consumed = 1
            
        finally:
            # Shutdown authority
            stop_msg = manager.stop()
            print(f"[TEST] {stop_msg}")


# ── PART V: Replay Through IPC ─────────────────────────────────────────────────

class TestL4Replay:
    """PART V: Replay through IPC tests."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            yield storage
    
    def test_replay_after_reconnect(self, temp_storage):
        """Test 17: Replay after reconnect → REJECT.
        
        Phase 2 Round 5: Verify reconnect works and replay is rejected.
        
        1. client consumes successfully
        2. client disconnects
        3. NEW client reconnects
        4. same lease submitted again
        5. Expected: REJECT
        """
        manager = AuthorityProcessManager(temp_storage)
        
        # Start authority process
        authority_pid, diagnostics = manager.start()
        assert authority_pid > 0, f"Failed to start authority: {diagnostics}"
        print(f"[TEST] Authority process started: PID {authority_pid}")
        
        try:
            # First connection: consume successfully
            client_a = AuthorityClient()
            client_a.connect()
            client_a_pid = os.getpid()
            print(f"[TEST] Client A connected: PID {client_a_pid}")
            
            registration = client_a.register_execution(
                invocation_id="test_invocation_l4_replay_reconnect",
                action="READ",
                target="codebase",
                requested_scope="codebase:read",
                task_context="self_analysis"
            )
            
            run_id = registration["run_id"]
            execution_id = registration["execution_id"]
            
            lease = client_a.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=3600
            )
            
            lease_id = lease["lease_id"]
            
            consumption = client_a.consume_lease(
                lease_id=lease_id,
                execution_id=execution_id
            )
            assert consumption["consumed"] is True
            print(f"[TEST] Client A consume successful")
            
            client_a.disconnect()
            print(f"[TEST] Client A disconnected")
            
            # Small delay to ensure pipe is ready
            time.sleep(0.5)
            
            # NEW client reconnects and tries to replay
            client_b = AuthorityClient()
            client_b.connect()
            client_b_pid = os.getpid()
            print(f"[TEST] Client B connected: PID {client_b_pid}")
            
            try:
                replay_consumption = client_b.consume_lease(
                    lease_id=lease_id,
                    execution_id=execution_id
                )
                assert False, f"Expected rejection, got: {replay_consumption}"
            except RuntimeError as e:
                assert "already consumed" in str(e).lower() or "not found" in str(e).lower()
                print(f"[TEST] Replay rejected as expected: {e}")
            
            client_b.disconnect()
            print(f"[TEST] Client B disconnected")
            
        finally:
            # Shutdown authority
            stop_msg = manager.stop()
            print(f"[TEST] {stop_msg}")
    
    def test_replay_after_restart(self, temp_storage):
        """Test 18: Replay after authority restart → REJECT.
        
        1. consume successfully
        2. authority shuts down
        3. authority restarts using SAME persistent state
        4. new client reconnects
        5. same lease submitted again
        6. Expected: REJECT
        """
        manager = AuthorityProcessManager(temp_storage)
        
        # Start authority process
        authority_pid, diagnostics = manager.start()
        assert authority_pid > 0, f"Failed to start authority: {diagnostics}"
        print(f"[TEST] Authority process started: PID {authority_pid}")
        
        try:
            # Consume successfully
            client = AuthorityClient()
            client.connect()
            
            registration = client.register_execution(
                invocation_id="test_invocation_l4_replay_restart",
                action="READ",
                target="codebase",
                requested_scope="codebase:read",
                task_context="self_analysis"
            )
            
            run_id = registration["run_id"]
            execution_id = registration["execution_id"]
            
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=3600
            )
            
            lease_id = lease["lease_id"]
            
            consumption = client.consume_lease(
                lease_id=lease_id,
                execution_id=execution_id
            )
            assert consumption["consumed"] is True
            print(f"[TEST] First consume successful")
            
            client.disconnect()
            
        finally:
            # Shutdown authority
            stop_msg = manager.stop()
            print(f"[TEST] {stop_msg}")
        
        # Restart authority with same storage
        manager = AuthorityProcessManager(temp_storage)
        authority_pid, diagnostics = manager.start()
        assert authority_pid > 0, f"Failed to restart authority: {diagnostics}"
        print(f"[TEST] Authority process restarted: PID {authority_pid}")
        
        try:
            # Try to replay with new client
            client = AuthorityClient()
            client.connect()
            
            try:
                replay_consumption = client.consume_lease(
                    lease_id=lease_id,
                    execution_id=execution_id
                )
                assert False, f"Expected rejection, got: {replay_consumption}"
            except RuntimeError as e:
                assert "already consumed" in str(e).lower() or "not found" in str(e).lower()
                print(f"[TEST] Replay after restart rejected as expected: {e}")
            
            client.disconnect()
            
        finally:
            # Shutdown authority
            stop_msg = manager.stop()
            print(f"[TEST] {stop_msg}")
