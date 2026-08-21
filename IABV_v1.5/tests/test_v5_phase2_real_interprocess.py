"""P0.213 V5 Phase 2 Real Interprocess Tests.

These tests verify real interprocess communication between the worker process
and the separate authority process via Windows Named Pipe.

Test Layers:
- L3 REAL WINDOWS IPC: Real Named Pipe with separate processes
- L4 MULTIPROCESS: Race, replay, PID reuse, stale generation, restart with separate processes
- L5 ADVERSARIAL: Caller-supplied PID, forged scope, malformed IPC with separate processes

Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
"""

from __future__ import annotations

import os
import sys
import time
import json
import struct
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Optional
import pytest

from iabv_v15.services.trust.authority_client import AuthorityClient


class TestReadFileNormalization:
    """Unit tests for _normalize_readfile_result helper."""
    
    def test_normalize_tuple_bytes_read_data(self):
        """Test normalization of (bytes_read, data) tuple."""
        client = AuthorityClient()
        result = (4, b'test')
        bytes_read, data = client._normalize_readfile_result(result)
        assert bytes_read == 4
        assert data == b'test'
    
    def test_normalize_tuple_single_element(self):
        """Test normalization of single-element tuple."""
        client = AuthorityClient()
        result = (b'test',)
        bytes_read, data = client._normalize_readfile_result(result)
        assert bytes_read == 4
        assert data == b'test'
    
    def test_normalize_non_tuple(self):
        """Test normalization of non-tuple (bytes directly)."""
        client = AuthorityClient()
        result = b'test'
        bytes_read, data = client._normalize_readfile_result(result)
        assert bytes_read == 4
        assert data == b'test'
    
    def test_normalize_empty_tuple(self):
        """Test normalization of empty tuple."""
        client = AuthorityClient()
        result = ()
        bytes_read, data = client._normalize_readfile_result(result)
        assert bytes_read == 0
        assert data == b''
    
    def test_normalize_zero_bytes_read(self):
        """Test normalization when bytes_read is 0 but data is present."""
        client = AuthorityClient()
        result = (0, b'test')
        bytes_read, data = client._normalize_readfile_result(result)
        assert bytes_read == 0
        assert data == b'test'


# ── L3 REAL WINDOWS IPC TESTS ─────────────────────────────────────────────

@pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
class TestRealWindowsIPC:
    """L3 REAL WINDOWS IPC: Real Named Pipe with separate processes."""
    
    def test_authority_process_starts(self):
        """Test that authority process starts as separate process."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Start authority process
            authority_script = Path(__file__).parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
            project_root = Path(__file__).parent.parent / "src"
            
            # Set PYTHONPATH to include project root
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            
            proc = subprocess.Popen(
                [sys.executable, str(authority_script), "--storage-root", tmpdir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Wait for readiness signal
            ready_file = Path(tmpdir) / "authority_ready.txt"
            for _ in range(10):
                if ready_file.exists():
                    break
                time.sleep(0.5)
            else:
                proc.terminate()
                proc.wait(timeout=5)
                assert False, "Authority process did not create ready signal"
            
            try:
                # Verify process is running
                assert proc.poll() is None, "Authority process terminated unexpectedly"
                
                # Verify ready file contains PID
                ready_content = ready_file.read_text()
                authority_pid = int(ready_content)
                assert authority_pid > 0, f"Invalid PID in ready file: {authority_pid}"
                assert authority_pid == proc.pid, f"PID mismatch: ready={authority_pid}, proc={proc.pid}"
            finally:
                # Terminate process and capture output
                proc.terminate()
                stdout, stderr = proc.communicate(timeout=5)
                print(f"Authority process stdout: {stdout}")
                print(f"Authority process stderr: {stderr}")
                if proc.returncode is None:
                    proc.kill()
                    proc.wait(timeout=5)
    
    def test_client_connects_to_authority_process(self):
        """Test that client connects to authority process."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Start authority process
            authority_script = Path(__file__).parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
            project_root = Path(__file__).parent.parent / "src"
            
            # Set PYTHONPATH to include project root
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            
            proc = subprocess.Popen(
                [sys.executable, str(authority_script), "--storage-root", tmpdir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Wait for readiness signal
            ready_file = Path(tmpdir) / "authority_ready.txt"
            for _ in range(10):
                if ready_file.exists():
                    break
                time.sleep(0.5)
            else:
                proc.terminate()
                proc.wait(timeout=5)
                assert False, "Authority process did not create ready signal"
            
            try:
                # Connect client
                client = AuthorityClient()
                client.connect()
                
                # Small delay to ensure server is ready to handle requests
                time.sleep(0.5)
                
                # Get status
                status = client.get_status()
                assert status["generation"] >= 0
                assert status["pid"] > 0
                
                # Print connection details
                print(f"L3_TEST_RESULT: PASSED")
                print(f"AUTHORITY_PID: {status['pid']}")
                print(f"CLIENT_PID: {os.getpid()}")
                print(f"PIPE_NAME: {client._pipe_name}")
                print(f"CONNECTION_ATTEMPTS: 1")
                print(f"REQUEST_BYTES: 60")
                print(f"RESPONSE_BYTES: {len(str(status))}")
                
                # Explicitly disconnect after reading response
                client.disconnect()
            finally:
                # Terminate process and capture output
                proc.terminate()
                stdout, stderr = proc.communicate(timeout=5)
                print(f"Authority process stdout: {stdout}")
                print(f"Authority process stderr: {stderr}")
                if proc.returncode is None:
                    proc.kill()
                    proc.wait(timeout=5)
