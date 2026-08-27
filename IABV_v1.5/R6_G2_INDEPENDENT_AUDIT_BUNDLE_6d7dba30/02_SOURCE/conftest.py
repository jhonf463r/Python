"""Windows E2E test fixtures - start AuthorityService with Named Pipe IPC."""

import os
import sys
import time
import tempfile
import multiprocessing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from iabv_v15.services.trust.authority_service import AuthorityService
from iabv_v15.services.trust.authority_server import AuthorityServer


@pytest.fixture(scope="function")
def workspace_root():
    """Provide the workspace root path for E2E tests."""
    return Path(__file__).parent.parent.parent


def _run_authority_server(storage_root: str):
    """Run authority server in a separate process."""
    service = AuthorityService(storage_root=storage_root)
    server = AuthorityServer(service)
    server.start()


@pytest.fixture(scope="function")
def authority_service():
    """Start AuthorityService with Named Pipe IPC for Windows E2E tests.
    
    This fixture starts the real authority service as a SEPARATE PROCESS
    with Windows Named Pipe IPC, ensuring real process separation between
    client and authority for proper security boundary testing.
    
    Returns a tuple: (service, authority_pid)
    """
    if os.name != "nt":
        pytest.skip("Windows E2E tests require Windows")
    
    # Create temporary storage for authority service
    tmpdir_path = Path(tempfile.mkdtemp(prefix="authority_"))
    
    # Initialize authority service (for test access to storage root)
    service = AuthorityService(storage_root=str(tmpdir_path))
    
    # Start authority server in separate process
    authority_process = multiprocessing.Process(
        target=_run_authority_server,
        args=(str(tmpdir_path),),
        daemon=False
    )
    authority_process.start()
    
    authority_pid = authority_process.pid
    print(f"[conftest] Authority process started with PID: {authority_pid}", flush=True)
    
    # Wait for server to start without pipe availability check
    # The pipe availability check causes the AuthorityServer to close the connection
    # when we close the test handle, leading to race conditions
    # Just wait for the process to initialize (AuthorityServer creates pipe on startup)
    time.sleep(2.0)
    print(f"[conftest] Authority process ready after 2.0s", flush=True)
    
    yield (service, authority_pid)
    
    # Cleanup
    print("[conftest] Stopping authority server process...", flush=True)
    authority_process.terminate()
    authority_process.join(timeout=5.0)
    
    if authority_process.is_alive():
        print("[conftest] Authority process still alive, killing...", flush=True)
        authority_process.kill()
        authority_process.join(timeout=2.0)
    
    print("[conftest] Authority server stopped", flush=True)
    
    # Cleanup temp directory
    import shutil
    if tmpdir_path.exists():
        shutil.rmtree(tmpdir_path)
