"""Test transport failure - authority unavailable, pipe closed, etc."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest


def test_transport_failure(authority_service):
    """Test that transport failures are handled gracefully."""
    
    print("=" * 80)
    print("TRANSPORT FAILURE TEST")
    print("=" * 80)
    
    # Test 1: Connect to non-existent pipe (authority not running)
    print(f"\n[TEST] Test 1: Connecting to non-existent pipe...")
    print(f"[TEST] Using a non-existent pipe name to simulate authority unavailable")
    
    client = AuthorityClient(pipe_name=r"\\.\pipe\IABV_Authority_NonExistent")
    try:
        client.connect()
        assert False, "Connected to non-existent pipe (unexpected)"
    except RuntimeError as e:
        print(f"[TEST] EXPECTED: Connection failed with RuntimeError")
        print(f"[TEST]   Error: {e}")
        print(f"[TEST] PASS: Transport failure handled correctly")
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e).__name__}: {e}"
    
    # Test 2: Connect to real authority, then disconnect and try to send request
    print(f"\n[TEST] Test 2: Send request after disconnect...")
    client = AuthorityClient()
    client.connect()
    print(f"[TEST] Connected to authority")
    client.disconnect()
    print(f"[TEST] Disconnected")
    
    # Try to send request after disconnect
    request = AuthorityRequest(
        request_type="GET_STATUS",
        data={},
        request_id="test_after_disconnect"
    )
    try:
        response = client._send_request(request)
        assert False, "Request succeeded after disconnect (unexpected)"
    except RuntimeError as e:
        print(f"[TEST] EXPECTED: Request failed after disconnect")
        print(f"[TEST]   Error: {e}")
        print(f"[TEST] PASS: Post-disconnect failure handled correctly")
    
    # Test 3: Verify real authority is still responsive
    print(f"\n[TEST] Test 3: Verify real authority is still responsive...")
    client = AuthorityClient()
    client.connect()
    print(f"[TEST] Connected to authority")
    
    request = AuthorityRequest(
        request_type="GET_STATUS",
        data={},
        request_id="test_status"
    )
    response = client._send_request(request)
    print(f"[TEST] GET_STATUS response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"GET_STATUS failed: {response.error}"
    print(f"[TEST]   Generation: {response.data.get('generation')}")
    print(f"[TEST]   PID: {response.data.get('pid')}")
    print(f"[TEST] PASS: Authority is still responsive after failure tests")
    
    client.disconnect()
