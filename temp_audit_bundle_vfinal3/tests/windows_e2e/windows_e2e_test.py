"""Windows E2E Test for Phase 3.

This script tests the REAL Windows Named Pipe transport and Phase 3 flow.
"""

import os
import sys
import time
from pathlib import Path

# Add src to path (go up to tests, then to src)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest
from iabv_v15.services.phase3.ed25519_keys import generate_ed25519_keypair, sign_message


def test_windows_e2e():
    """Test Windows E2E flow through real Named Pipe transport."""
    
    print("=" * 80)
    print("WINDOWS E2E TEST - Phase 3")
    print("=" * 80)
    
    # Wait for authority to be ready
    storage_root = Path(__file__).parent.parent.parent / "temp_authority_storage"
    ready_file = storage_root / "authority_ready.txt"
    
    print(f"\n[TEST] Waiting for authority ready signal: {ready_file}")
    for i in range(30):
        if ready_file.exists():
            print(f"[TEST] Authority ready signal found")
            with open(ready_file) as f:
                authority_pid = f.read().strip()
            print(f"[TEST] Authority PID: {authority_pid}")
            break
        time.sleep(0.5)
    else:
        print("[TEST] ERROR: Authority not ready after 15 seconds")
        assert False, "Authority not ready after 15 seconds"
    
    # Get client process identity
    print(f"\n[TEST] Client process identity:")
    print(f"[TEST]   PID: {os.getpid()}")
    print(f"[TEST]   Username: {os.environ.get('USERNAME', 'unknown')}")
    
    # Connect to authority via real Named Pipe
    print(f"\n[TEST] Connecting to authority via Named Pipe...")
    client = AuthorityClient()
    try:
        client.connect()
        print("[TEST] Connected successfully")
    except Exception as e:
        print(f"[TEST] ERROR: Failed to connect: {e}")
        assert False, f"Failed to connect: {e}"
    
    # Generate real Ed25519 keypair
    print(f"\n[TEST] Generating real Ed25519 keypair...")
    keypair = generate_ed25519_keypair()
    public_key = keypair.public_key
    private_key = keypair.private_key
    print(f"[TEST] Public key (hex): {public_key.hex()[:32]}...")
    print(f"[TEST] Private key (hex): {private_key.hex()[:32]}...")
    
    # Test REGISTER_EXECUTION first (required for Phase 2)
    print(f"\n[TEST] Testing REGISTER_EXECUTION...")
    try:
        request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data={
                "episode_id": "windows_e2e_test",
                "session_id": "windows_e2e_session",
                "invocation_id": "windows_e2e_invocation",
                "requested_scope": "codebase:read",
                "action": "READ",
                "target": "codebase",
                "task_context": {"purpose": "windows_e2e_testing"}
            },
            request_id="test_register_1"
        )
        response = client._send_request(request)
        print(f"[TEST] REGISTER_EXECUTION response:")
        print(f"[TEST]   Success: {response.success}")
        print(f"[TEST]   Data: {response.data}")
        assert response.success, f"REGISTER_EXECUTION failed: {response.error}"
        
        execution_id = response.data.get('execution_id')
        run_id = response.data.get('run_id')
        print(f"[TEST]   Execution ID: {execution_id}")
        print(f"[TEST]   Run ID: {run_id}")
        assert execution_id, "No execution_id in response"
        assert run_id, "No run_id in response"
    except Exception as e:
        print(f"[TEST] ERROR: REGISTER_EXECUTION failed: {e}")
        client.disconnect()
        assert False, f"REGISTER_EXECUTION failed: {e}"
    
    # Test REQUEST_JOIN
    print(f"\n[TEST] Testing REQUEST_JOIN...")
    try:
        request = AuthorityRequest(
            request_type="PHASE3_REQUEST_JOIN",
            data={
                "public_key": public_key.hex(),
                "subject_id": run_id,
                "execution_id": execution_id
            },
            request_id="test_join_1"
        )
        response = client._send_request(request)
        print(f"[TEST] REQUEST_JOIN response:")
        print(f"[TEST]   Success: {response.success}")
        print(f"[TEST]   Data: {response.data}")
        assert response.success, f"REQUEST_JOIN failed: {response.error}"
        
        join_token = response.data.get('join_token', {})
        join_id = join_token.get('data', {}).get('join_id') if join_token else None
        print(f"[TEST]   Join ID: {join_id}")
        assert join_id, "No join_id in response"
    except Exception as e:
        print(f"[TEST] ERROR: REQUEST_JOIN failed: {e}")
        client.disconnect()
        assert False, f"REQUEST_JOIN failed: {e}"
    
    # Test REQUEST_CHALLENGE
    print(f"\n[TEST] Testing REQUEST_CHALLENGE...")
    try:
        request = AuthorityRequest(
            request_type="PHASE3_REQUEST_CHALLENGE",
            data={
                "join_id": join_id,
                "subject_id": run_id,
                "execution_id": execution_id
            },
            request_id="test_challenge_1"
        )
        response = client._send_request(request)
        print(f"[TEST] REQUEST_CHALLENGE response:")
        print(f"[TEST]   Success: {response.success}")
        print(f"[TEST]   Data: {response.data}")
        assert response.success, f"REQUEST_CHALLENGE failed: {response.error}"
        
        challenge = response.data.get('challenge')
        print(f"[TEST]   Challenge: {challenge}")
        assert challenge, "No challenge in response"
    except Exception as e:
        print(f"[TEST] ERROR: REQUEST_CHALLENGE failed: {e}")
        client.disconnect()
        assert False, f"REQUEST_CHALLENGE failed: {e}"
    
    # Sign challenge with real private key
    print(f"\n[TEST] Signing challenge with real private key...")
    challenge_bytes = challenge.encode('utf-8')
    signature = sign_message(private_key, challenge_bytes)
    print(f"[TEST] Signature (hex): {signature.hex()[:32]}...")
    
    # Test REDEEM_JOIN
    print(f"\n[TEST] Testing REDEEM_JOIN...")
    try:
        request = AuthorityRequest(
            request_type="PHASE3_REDEEM_JOIN",
            data={
                "join_id": join_id,
                "subject_id": run_id,
                "execution_id": execution_id,
                "challenge": challenge,
                "signature": signature.hex()
            },
            request_id="test_redeem_1"
        )
        response = client._send_request(request)
        print(f"[TEST] REDEEM_JOIN response:")
        print(f"[TEST]   Success: {response.success}")
        print(f"[TEST]   Data: {response.data}")
        assert response.success, f"REDEEM_JOIN failed: {response.error}"
        
        membership_id = response.data.get('membership_id')
        print(f"[TEST]   Membership ID: {membership_id}")
        assert membership_id, "No membership_id in response"
    except Exception as e:
        print(f"[TEST] ERROR: REDEEM_JOIN failed: {e}")
        client.disconnect()
        assert False, f"REDEEM_JOIN failed: {e}"
    
    # Disconnect
    print(f"\n[TEST] Disconnecting...")
    client.disconnect()
    print("[TEST] Disconnected successfully")
    
    print("\n" + "=" * 80)
    print("WINDOWS E2E TEST PASSED")
    print("=" * 80)
