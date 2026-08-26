"""Test real Windows concurrency - two threads from same process, ONE SUCCESS / ONE FAILURE."""

import os
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.authority_service import AuthorityRequest
from iabv_v15.services.phase3.ed25519_keys import generate_ed25519_keypair, sign_message


def attempt_redeem_thread(join_id, run_id, execution_id, challenge, private_key, thread_id, results):
    """Separate thread function to attempt redeem."""
    print(f"[Thread {thread_id}] Starting redeem attempt", flush=True)
    
    # Connect to authority
    client = AuthorityClient()
    try:
        client.connect()
        print(f"[Thread {thread_id}] Connected", flush=True)
    except Exception as e:
        print(f"[Thread {thread_id}] ERROR: Failed to connect: {e}", flush=True)
        results[thread_id] = (False, f"Connection failed: {e}")
        return
    
    # Small delay to ensure both threads are ready
    time.sleep(0.1)
    
    # Sign the challenge
    challenge_bytes = challenge.encode('utf-8')
    signature = sign_message(private_key, challenge_bytes)
    
    # Attempt redeem
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
            request_id=f"redeem_thread_{thread_id}"
        )
        response = client._send_request(request)
        
        print(f"[Thread {thread_id}] REDEEM_JOIN response:", flush=True)
        print(f"[Thread {thread_id}]   Success: {response.success}", flush=True)
        if response.success:
            print(f"[Thread {thread_id}]   Membership ID: {response.data.get('membership_id')}", flush=True)
        else:
            print(f"[Thread {thread_id}]   Error: {response.error}", flush=True)
        
        client.disconnect()
        results[thread_id] = (response.success, response.error if not response.success else None)
    except Exception as e:
        print(f"[Thread {thread_id}] ERROR: REDEEM_JOIN failed: {e}", flush=True)
        try:
            client.disconnect()
        except:
            pass
        results[thread_id] = (False, str(e))


def test_concurrency(authority_service):
    """Test that two concurrent threads result in ONE SUCCESS and ONE FAILURE."""
    
    # Unpack authority_service tuple
    service, authority_pid = authority_service
    
    print("=" * 80)
    print("WINDOWS CONCURRENCY TEST - Two Threads")
    print("=" * 80)
    print(f"[TEST] Authority PID: {authority_pid}")
    
    # Connect to authority to set up the test
    print(f"\n[TEST] Connecting to authority for setup...")
    client = AuthorityClient()
    client.connect()
    print("[TEST] Connected successfully")
    
    # Register execution for the test
    print(f"\n[TEST] Registering execution...")
    request = AuthorityRequest(
        request_type="REGISTER_EXECUTION",
        data={
            "episode_id": "concurrency_test",
            "session_id": "concurrency_session",
            "invocation_id": "concurrency_invocation",
            "requested_scope": "codebase:read",
            "action": "READ",
            "target": "codebase",
            "task_context": {"purpose": "concurrency_testing"}
        },
        request_id="test_register_concurrency"
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
        request_id="test_join_concurrency"
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
        request_id="test_challenge_concurrency"
    )
    response = client._send_request(request)
    print(f"[TEST] REQUEST_CHALLENGE response:")
    print(f"[TEST]   Success: {response.success}")
    assert response.success, f"REQUEST_CHALLENGE failed: {response.error}"
    
    challenge = response.data.get('challenge')
    print(f"[TEST]   Challenge: {challenge}")
    
    client.disconnect()
    
    # Now spawn two threads to attempt concurrent redeem
    print(f"\n[TEST] Spawning two threads for concurrent redeem...")
    
    results = {}
    thread1 = threading.Thread(
        target=attempt_redeem_thread,
        args=(join_id, run_id, execution_id, challenge, private_key, 1, results)
    )
    thread2 = threading.Thread(
        target=attempt_redeem_thread,
        args=(join_id, run_id, execution_id, challenge, private_key, 2, results)
    )
    
    # Start both threads simultaneously
    thread1.start()
    thread2.start()
    
    # Wait for both to complete
    thread1.join()
    thread2.join()
    
    print(f"\n[TEST] Both threads completed")
    print(f"[TEST] Thread 1 result: {results.get(1)}")
    print(f"[TEST] Thread 2 result: {results.get(2)}")
    
    # Verify that exactly one succeeded
    success_count = sum(1 for result in results.values() if result[0])
    print(f"\n[TEST] Success count: {success_count}")
    
    assert success_count == 1, f"Expected exactly one success, got {success_count}"
    print(f"[TEST] EXPECTED: Exactly one thread succeeded")
    
    # Verify database state
    print(f"\n[TEST] Verifying database state...")
    import sqlite3
    # Use the same storage directory as the authority service
    db_path = Path(service._storage_root) / "authority_join_authorizations.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT consumed FROM join_authorizations WHERE join_id = ?", (join_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row, "Join not found in database"
    consumed = row[0]
    print(f"[TEST] Join consumed state: {consumed}")
    assert consumed == 1, f"Expected consumed == 1, got {consumed}"
    print(f"[TEST] EXPECTED: Exactly one thread succeeded (consumed == 1)")
