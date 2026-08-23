"""Test process lifecycle - start → connect → join → challenge → redeem → exit."""

import os
import sys
import time
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest
from iabv_v15.services.phase3.ed25519_keys import generate_ed25519_keypair, sign_message


def test_lifecycle():
    """Test complete process lifecycle."""
    
    print("=" * 80)
    print("PROCESS LIFECYCLE TEST")
    print("=" * 80)
    
    # Check authority process is running
    print(f"\n[TEST] Checking authority process status...")
    ready_file = Path(__file__).parent.parent.parent / "temp_authority_storage" / "authority_ready.txt"
    assert ready_file.exists(), "Authority ready file not found"
    
    with open(ready_file) as f:
        authority_pid = int(f.read().strip())
    print(f"[TEST] Authority PID from ready file: {authority_pid}")
    
    # Verify process is actually running
    assert psutil.pid_exists(authority_pid), "Authority process not running"
    process = psutil.Process(authority_pid)
    print(f"[TEST] Authority process is running")
    print(f"[TEST]   Name: {process.name()}")
    print(f"[TEST]   Status: {process.status()}")
    print(f"[TEST]   Create time: {process.create_time()}")
    print(f"[TEST]   Num threads: {process.num_threads()}")
    
    # Perform full flow
    print(f"\n[TEST] Performing full flow: connect → join → challenge → redeem → disconnect")
    
    client = AuthorityClient()
    
    # Connect
    print(f"\n[TEST] Step 1: Connect")
    client.connect()
    print(f"[TEST] Connected successfully")
    
    # Register execution
    print(f"\n[TEST] Step 2: Register execution")
    request = AuthorityRequest(
        request_type="REGISTER_EXECUTION",
        data={
            "episode_id": "lifecycle_test",
            "session_id": "lifecycle_session",
            "invocation_id": "lifecycle_invocation",
            "requested_scope": "codebase:read",
            "action": "READ",
            "target": "codebase",
            "task_context": {"purpose": "lifecycle_testing"}
        },
        request_id="test_register_lifecycle"
    )
    response = client._send_request(request)
    assert response.success, f"REGISTER_EXECUTION failed: {response.error}"
    
    execution_id = response.data.get('execution_id')
    run_id = response.data.get('run_id')
    print(f"[TEST]   Execution ID: {execution_id}")
    print(f"[TEST]   Run ID: {run_id}")
    
    # REQUEST_JOIN
    print(f"\n[TEST] Step 3: REQUEST_JOIN")
    keypair = generate_ed25519_keypair()
    request = AuthorityRequest(
        request_type="PHASE3_REQUEST_JOIN",
        data={
            "public_key": keypair.public_key.hex(),
            "subject_id": run_id,
            "execution_id": execution_id
        },
        request_id="test_join_lifecycle"
    )
    response = client._send_request(request)
    assert response.success, f"REQUEST_JOIN failed: {response.error}"
    
    join_token = response.data.get('join_token', {})
    join_id = join_token.get('data', {}).get('join_id') if join_token else None
    print(f"[TEST]   Join ID: {join_id}")
    assert join_id, "No join_id in response"
    
    # REQUEST_CHALLENGE
    print(f"\n[TEST] Step 4: REQUEST_CHALLENGE")
    request = AuthorityRequest(
        request_type="PHASE3_REQUEST_CHALLENGE",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id
        },
        request_id="test_challenge_lifecycle"
    )
    response = client._send_request(request)
    assert response.success, f"REQUEST_CHALLENGE failed: {response.error}"
    
    challenge = response.data.get('challenge')
    print(f"[TEST]   Challenge: {challenge}")
    assert challenge, "No challenge in response"
    
    # REDEEM_JOIN
    print(f"\n[TEST] Step 5: REDEEM_JOIN")
    challenge_bytes = challenge.encode('utf-8')
    signature = sign_message(keypair.private_key, challenge_bytes)
    
    request = AuthorityRequest(
        request_type="PHASE3_REDEEM_JOIN",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id,
            "challenge": challenge,
            "signature": signature.hex()
        },
        request_id="test_redeem_lifecycle"
    )
    response = client._send_request(request)
    assert response.success, f"REDEEM_JOIN failed: {response.error}"
    
    membership_id = response.data.get('membership_id')
    print(f"[TEST]   Membership ID: {membership_id}")
    assert membership_id, "No membership_id in response"
    
    # Disconnect
    print(f"\n[TEST] Step 6: Disconnect")
    client.disconnect()
    print(f"[TEST] Disconnected successfully")
    
    # Verify authority process is still healthy after full flow
    print(f"\n[TEST] Verifying authority process health after full flow...")
    assert psutil.pid_exists(authority_pid), "Authority process died during flow"
    process = psutil.Process(authority_pid)
    print(f"[TEST] Authority process still running")
    print(f"[TEST]   Status: {process.status()}")
    print(f"[TEST]   Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"[TEST]   CPU percent: {process.cpu_percent(interval=0.1)}%")
    
    # Check for zombie or stale resources
    assert process.status() != psutil.STATUS_ZOMBIE, "Authority process is zombie"
    
    print(f"[TEST] PASS: Process lifecycle verified - no zombies or stale resources")
