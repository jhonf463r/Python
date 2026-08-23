"""Test replay rejection - repeat credential material must REJECT."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest
from iabv_v15.services.phase3.ed25519_keys import generate_ed25519_keypair, sign_message


def test_replay_rejection():
    """Test that repeating credential material is rejected."""
    
    print("=" * 80)
    print("REPLAY REJECTION TEST")
    print("=" * 80)
    
    # Connect to authority
    print(f"\n[TEST] Connecting to authority...")
    client = AuthorityClient()
    client.connect()
    print("[TEST] Connected successfully")
    
    # Register execution for a new test
    print(f"\n[TEST] Registering new execution...")
    request = AuthorityRequest(
        request_type="REGISTER_EXECUTION",
        data={
            "episode_id": "replay_test",
            "session_id": "replay_session",
            "invocation_id": "replay_invocation",
            "requested_scope": "codebase:read",
            "action": "READ",
            "target": "codebase",
            "task_context": {"purpose": "replay_testing"}
        },
        request_id="test_register_replay"
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
    
    # REQUEST_JOIN with this public key
    print(f"\n[TEST] REQUEST_JOIN with public key...")
    request = AuthorityRequest(
        request_type="PHASE3_REQUEST_JOIN",
        data={
            "public_key": public_key.hex(),
            "subject_id": run_id,
            "execution_id": execution_id
        },
        request_id="test_join_replay"
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
        request_id="test_challenge_replay"
    )
    response = client._send_request(request)
    print(f"[TEST] REQUEST_CHALLENGE response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"REQUEST_CHALLENGE failed: {response.error}"
    
    challenge = response.data.get('challenge')
    print(f"[TEST]   Challenge: {challenge}")
    
    # Sign the challenge
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
        request_id="test_redeem_replay_1"
    )
    response = client._send_request(request)
    print(f"[TEST] REDEEM_JOIN response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"First REDEEM_JOIN failed: {response.error}"
    
    membership_id = response.data.get('membership_id')
    print(f"[TEST]   Membership ID: {membership_id}")
    
    # Now try to REDEEM again with the SAME credential material (replay attack)
    print(f"\n[TEST] REDEEM_JOIN - second attempt with SAME signature (replay attack)...")
    request = AuthorityRequest(
        request_type="PHASE3_REDEEM_JOIN",
        data={
            "join_id": join_id,
            "subject_id": run_id,
            "execution_id": execution_id,
            "challenge": challenge,
            "signature": signature.hex()  # SAME signature
        },
        request_id="test_redeem_replay_2"
    )
    response = client._send_request(request)
    print(f"[TEST] REDEEM_JOIN response:")
    print(f"[TEST]   Success: {response.success}")
    assert not response.success, "Replay succeeded (VIOLATION - replay attack not prevented)"
    assert "already consumed" in response.error.lower() or "consumed" in response.error.lower(), \
        f"Expected 'consumed' error, got: {response.error}"
    print(f"[TEST]   Error: {response.error}")
    print(f"[TEST] EXPECTED: Replay rejected because join is already consumed")
    
    client.disconnect()
    print("[TEST] Replay rejection verified")
