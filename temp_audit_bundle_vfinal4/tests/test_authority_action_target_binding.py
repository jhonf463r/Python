"""Security Tests for Action/Target Binding in AuthorityService::handle_consume_lease

Tests that the canonical authority enforces action and target binding during capability consumption.
"""

import hashlib
import hmac
import sqlite3
import tempfile
import time
from pathlib import Path

from iabv_v15.services.trust.authority_protocol import ConsumeLeaseRequest
from iabv_v15.services.trust.authority_service import AuthorityRequest, AuthorityService


def test_action_target_binding():
    """Test that action and target binding is enforced during lease consumption."""
    
    print("=" * 80)
    print("SECURITY TEST: Action/Target Binding")
    print("=" * 80)
    
    # Setup test databases
    storage_root = Path("temp_test_authority")
    storage_root.mkdir(exist_ok=True)
    
    # Initialize AuthorityService
    authority = AuthorityService(storage_root=storage_root)
    
    # Get database paths from authority
    lease_db = authority._lease_state_db
    run_record_db = authority._run_record_db
    
    # Create a test RunRecord with authorized action/target
    import uuid
    run_id = f"test_run_id_{uuid.uuid4().hex}"
    execution_id = f"test_execution_id_{uuid.uuid4().hex}"
    authorized_action = "READ"
    authorized_target = "codebase"
    client_pid = 12345
    
    conn = sqlite3.connect(str(run_record_db))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO run_records (run_id, execution_id, episode_id, session_id, invocation_id, requested_scope, authorized_scope, action, target, consumer_pid, parent_authority, generation, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, execution_id, "test_episode", "test_session", "test_invocation", "codebase:read", "codebase:read", authorized_action, authorized_target, client_pid, 0, 0, time.time()))
    conn.commit()
    conn.close()
    
    # Create a test lease
    lease_id = f"test_lease_id_{uuid.uuid4().hex}"
    lease_json = '{"test": "data"}'
    # Generate valid signature using authority's secret key
    signature = hmac.new(authority._secret_key, lease_json.encode('utf-8'), hashlib.sha256).hexdigest()
    expires_at = time.time() + 300
    created_at = time.time()
    
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leases (lease_id, consumed, generation, expires_at, created_at, lease_json, signature, run_id, execution_id, producer_pid, authorized_scope)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (lease_id, 0, 0, expires_at, created_at, lease_json, signature, run_id, execution_id, client_pid, "codebase:read"))
    conn.commit()
    conn.close()
    
    # TEST A: Valid action/target should be accepted
    print(f"\n[TEST A] Valid action/target (READ/codebase)")
    request_a = AuthorityRequest(
        request_type="CONSUME_LEASE",
        data=ConsumeLeaseRequest(
            lease_id=lease_id,
            execution_id=execution_id,
            requested_action="READ",
            requested_target="codebase"
        ).to_dict(),
        request_id="test_a"
    )
    response_a = authority.handle_consume_lease(request_a, client_pid)
    print(f"[TEST A] Success: {response_a.success}")
    print(f"[TEST A] Error: {response_a.error}")
    
    # Verify lease was consumed
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("SELECT consumed FROM leases WHERE lease_id = ?", (lease_id,))
    consumed_a = cursor.fetchone()[0]
    conn.close()
    print(f"[TEST A] Lease consumed: {consumed_a}")
    
    # TEST B: Wrong action should be rejected
    print(f"\n[TEST B] Wrong action (WRITE/codebase)")
    # Create fresh lease for test B
    lease_id_b = f"test_lease_id_{uuid.uuid4().hex}"
    signature_b = hmac.new(authority._secret_key, lease_json.encode('utf-8'), hashlib.sha256).hexdigest()
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leases (lease_id, consumed, generation, expires_at, created_at, lease_json, signature, run_id, execution_id, producer_pid, authorized_scope)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (lease_id_b, 0, 0, expires_at, created_at, lease_json, signature_b, run_id, execution_id, client_pid, "codebase:read"))
    conn.commit()
    conn.close()
    
    request_b = AuthorityRequest(
        request_type="CONSUME_LEASE",
        data=ConsumeLeaseRequest(
            lease_id=lease_id_b,
            execution_id=execution_id,
            requested_action="WRITE",  # Wrong action
            requested_target="codebase"
        ).to_dict(),
        request_id="test_b"
    )
    response_b = authority.handle_consume_lease(request_b, client_pid)
    print(f"[TEST B] Success: {response_b.success}")
    print(f"[TEST B] Error: {response_b.error}")
    
    # Verify lease was NOT consumed
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("SELECT consumed FROM leases WHERE lease_id = ?", (lease_id_b,))
    consumed_b = cursor.fetchone()[0]
    conn.close()
    print(f"[TEST B] Lease consumed: {consumed_b}")
    
    # TEST C: Wrong target should be rejected
    print(f"\n[TEST C] Wrong target (READ/unauthorized_target)")
    # Create fresh lease for test C
    lease_id_c = f"test_lease_id_{uuid.uuid4().hex}"
    signature_c = hmac.new(authority._secret_key, lease_json.encode('utf-8'), hashlib.sha256).hexdigest()
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leases (lease_id, consumed, generation, expires_at, created_at, lease_json, signature, run_id, execution_id, producer_pid, authorized_scope)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (lease_id_c, 0, 0, expires_at, created_at, lease_json, signature_c, run_id, execution_id, client_pid, "codebase:read"))
    conn.commit()
    conn.close()
    
    request_c = AuthorityRequest(
        request_type="CONSUME_LEASE",
        data=ConsumeLeaseRequest(
            lease_id=lease_id_c,
            execution_id=execution_id,
            requested_action="READ",
            requested_target="unauthorized_target"  # Wrong target
        ).to_dict(),
        request_id="test_c"
    )
    response_c = authority.handle_consume_lease(request_c, client_pid)
    print(f"[TEST C] Success: {response_c.success}")
    print(f"[TEST C] Error: {response_c.error}")
    
    # Verify lease was NOT consumed
    conn = sqlite3.connect(str(lease_db))
    cursor = conn.cursor()
    cursor.execute("SELECT consumed FROM leases WHERE lease_id = ?", (lease_id_c,))
    consumed_c = cursor.fetchone()[0]
    conn.close()
    print(f"[TEST C] Lease consumed: {consumed_c}")
    
    # EVIDENCE TABLE
    print(f"\n{'=' * 80}")
    print(f"EVIDENCE TABLE")
    print(f"{'=' * 80}")
    print(f"| Test | Authorized Action | Requested Action | Authorized Target | Requested Target | Result | Lease Consumed |")
    print(f"|------|-------------------|------------------|-------------------|------------------|--------|----------------|")
    print(f"| A    | READ              | READ             | codebase          | codebase         | {'ACCEPT' if response_a.success else 'REJECT':<6} | {consumed_a:14} |")
    print(f"| B    | READ              | WRITE            | codebase          | codebase         | {'ACCEPT' if response_b.success else 'REJECT':<6} | {consumed_b:14} |")
    print(f"| C    | READ              | READ             | codebase          | unauthorized_tgt | {'ACCEPT' if response_c.success else 'REJECT':<6} | {consumed_c:14} |")
    
    # ANALYSIS
    print(f"\n{'=' * 80}")
    print(f"ANALYSIS")
    print(f"{'=' * 80}")
    
    if response_a.success and consumed_a:
        print(f"[ANALYSIS] TEST A: Valid action/target ACCEPTED and consumed (CORRECT)")
    else:
        print(f"[ANALYSIS] TEST A: Valid action/target FAILED (INCORRECT)")
    
    if not response_b.success and not consumed_b:
        print(f"[ANALYSIS] TEST B: Wrong action REJECTED and NOT consumed (CORRECT)")
    elif response_b.success:
        print(f"[ANALYSIS] TEST B: Wrong action ACCEPTED (SECURITY BUG)")
    elif consumed_b:
        print(f"[ANALYSIS] TEST B: Wrong action consumed lease (SECURITY BUG)")
    
    if not response_c.success and not consumed_c:
        print(f"[ANALYSIS] TEST C: Wrong target REJECTED and NOT consumed (CORRECT)")
    elif response_c.success:
        print(f"[ANALYSIS] TEST C: Wrong target ACCEPTED (SECURITY BUG)")
    elif consumed_c:
        print(f"[ANALYSIS] TEST C: Wrong target consumed lease (SECURITY BUG)")
    
    print(f"\n{'=' * 80}")
    print(f"CONCLUSION")
    print(f"{'=' * 80}")
    print(f"ACTION_BINDING: {'PROVEN' if not response_b.success and not consumed_b else 'NOT PROVEN'}")
    print(f"TARGET_BINDING: {'PROVEN' if not response_c.success and not consumed_c else 'NOT PROVEN'}")


if __name__ == "__main__":
    test_action_target_binding()
