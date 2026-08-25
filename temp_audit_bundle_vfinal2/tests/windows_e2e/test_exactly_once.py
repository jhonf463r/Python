"""Test exactly-once semantics - repeat redeem must FAIL."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest
from iabv_v15.services.phase3.ed25519_keys import generate_ed25519_keypair, sign_message


def test_exactly_once():
    """Test that repeating a redeem fails (exactly-once semantics)."""
    
    print("=" * 80)
    print("EXACTLY-ONCE SEMANTICS TEST")
    print("=" * 80)
    
    # Connect to authority
    print(f"\n[TEST] Connecting to authority...")
    client = AuthorityClient()
    client.connect()
    print("[TEST] Connected successfully")
    
    # Register execution for this test
    print(f"\n[TEST] Registering execution...")
    request = AuthorityRequest(
        request_type="REGISTER_EXECUTION",
        data={
            "episode_id": "exactly_once_test",
            "session_id": "exactly_once_session",
            "invocation_id": "exactly_once_invocation",
            "requested_scope": "codebase:read",
            "action": "READ",
            "target": "codebase",
            "task_context": {"purpose": "exactly_once_testing"}
        },
        request_id="test_register_exactly_once"
    )
    response = client._send_request(request)
    print(f"[TEST] REGISTER_EXECUTION response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"REGISTER_EXECUTION failed: {response.error}"
    
    execution_id = response.data.get('execution_id')
    run_id = response.data.get('run_id')
    print(f"[TEST]   Execution ID: {execution_id}")
    print(f"[TEST]   Run ID: {run_id}")
    
    # Generate Ed25519 keypair
    print(f"\n[TEST] Generating Ed25519 keypair...")
    keypair = generate_ed25519_keypair()
    public_key = keypair.public_key
    private_key = keypair.private_key
    
    # REQUEST_JOIN
    print(f"\n[TEST] REQUEST_JOIN...")
    request = AuthorityRequest(
        request_type="PHASE3_REQUEST_JOIN",
        data={
            "public_key": public_key.hex(),
            "subject_id": run_id,
            "execution_id": execution_id
        },
        request_id="test_join_exactly_once"
    )
    response = client._send_request(request)
    print(f"[TEST] REQUEST_JOIN response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"REQUEST_JOIN failed: {response.error}"
    
    join_token = response.data.get('join_token', {})
    join_id = join_token.get('data', {}).get('join_id') if join_token else None
    print(f"[TEST]   Join ID: {join_id}")
    assert join_id, "No join_id in response"
    
    # REQUEST_CHALLENGE
    print(f"\n[TEST] REQUEST_CHALLENGE...")
    request = AuthorityRequest(
        request_type="PHASE3_REQUEST_CHALLENGE",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id
        },
        request_id="test_challenge_exactly_once"
    )
    response = client._send_request(request)
    print(f"[TEST] REQUEST_CHALLENGE response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"REQUEST_CHALLENGE failed: {response.error}"
    
    challenge = response.data.get('challenge')
    print(f"[TEST]   Challenge: {challenge}")
    
    # Sign challenge
    print(f"\n[TEST] Signing challenge...")
    challenge_bytes = challenge.encode('utf-8')
    signature = sign_message(private_key, challenge_bytes)
    
    # REDEEM_JOIN - first time (should succeed)
    print(f"\n[TEST] REDEEM_JOIN - first attempt (should succeed)...")
    request = AuthorityRequest(
        request_type="PHASE3_REDEEM_JOIN",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id,
            "challenge": challenge,
            "signature": signature.hex()
        },
        request_id="test_redeem_exactly_once_1"
    )
    response = client._send_request(request)
    print(f"[TEST] REDEEM_JOIN response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"First REDEEM_JOIN failed: {response.error}"
    
    membership_id = response.data.get('membership_id')
    print(f"[TEST]   Membership ID: {membership_id}")
    
    # REDEEM_JOIN - second time with same join_id (should fail)
    print(f"\n[TEST] REDEEM_JOIN - second attempt with same join_id (should fail)...")
    request = AuthorityRequest(
        request_type="PHASE3_REDEEM_JOIN",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id,
            "challenge": challenge,
            "signature": signature.hex()
        },
        request_id="test_redeem_exactly_once_2"
    )
    response = client._send_request(request)
    print(f"[TEST] REDEEM_JOIN response:")
    print(f"[TEST]   Success: {response.success}")
    assert not response.success, "Second REDEEM_JOIN should have failed (exactly-once violation)"
    assert "already consumed" in response.error.lower() or "consumed" in response.error.lower(), \
        f"Expected 'consumed' error, got: {response.error}"
    print(f"[TEST]   Error: {response.error}")
    print(f"[TEST] EXPECTED: Second redeem failed due to consumed state")
    
    client.disconnect()
    print("[TEST] Exactly-once semantics verified")
