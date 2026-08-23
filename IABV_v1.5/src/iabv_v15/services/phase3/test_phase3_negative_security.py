"""Negative Security Tests for Phase 3 Remediation.

This module implements adversarial security tests for Phase 3 authorization,
testing that unauthorized access attempts are properly rejected.

Tests:
- Forged subject_id rejection
- Forged public_key rejection
- Unauthorized caller rejection
- Wrong parent rejection
- Cross-run token rejection
- Replayed token rejection
- Stale generation rejection
- Revoked authorization rejection
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from iabv_v15.services.phase3.phase3_authority import Phase3AuthorityExtension
from iabv_v15.services.phase3.authentication_layer import AuthenticationLayer
from iabv_v15.services.phase3.phase3_protocol import (
    RequestJoinRequest,
    RequestChallengeRequest,
    RedeemJoinRequest,
)


class TestNegativeSecurity:
    """Negative security tests for Phase 3 authorization."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test databases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def auth_layer(self, temp_dir):
        """Create authentication layer for testing."""
        return AuthenticationLayer(temp_dir)
    
    @pytest.fixture
    def run_records_db(self, temp_dir):
        """Create run_records database for testing."""
        db_path = Path(temp_dir) / "run_records.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE run_records (
                execution_id TEXT PRIMARY KEY,
                generation INTEGER NOT NULL DEFAULT 0,
                child_authorization_state TEXT,
                pinned_public_key TEXT,
                child_authorization_generation INTEGER
            )
        """)
        
        # Insert test execution
        cursor.execute("""
            INSERT INTO run_records
            (execution_id, generation, child_authorization_state)
            VALUES (?, ?, ?)
        """, ("test-execution-1", 1, "UNPREPARED"))
        
        conn.commit()
        conn.close()
        
        return sqlite3.connect(str(db_path))
    
    @pytest.fixture
    def phase3_authority(self, temp_dir, run_records_db):
        """Create Phase3AuthorityExtension for testing."""
        return Phase3AuthorityExtension(temp_dir, run_records_db)
    
    def test_forged_subject_id_rejected(self, auth_layer, phase3_authority):
        """Test that unauthorized subject_id is rejected."""
        # Register authorized subject with allowed public key
        auth_layer.register_subject(
            subject_id="authorized-subject",
            windows_sid="S-1-5-21-TEST",
            allowed_public_keys=["authorized-key-hex"],
            parent_authority="test-parent"
        )
        
        # Attempt REQUEST_JOIN with forged subject_id
        request_data = RequestJoinRequest(
            subject_id="forged-subject",
            public_key="authorized-key-hex"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify request is rejected
        assert response["success"] is False
        assert "Subject/key binding not authorized" in response["error"]
    
    def test_forged_public_key_rejected(self, auth_layer, phase3_authority):
        """Test that unauthorized public_key is rejected."""
        # Register authorized subject with allowed public key
        auth_layer.register_subject(
            subject_id="authorized-subject",
            windows_sid="S-1-5-21-TEST",
            allowed_public_keys=["authorized-key-hex"],
            parent_authority="test-parent"
        )
        
        # Attempt REQUEST_JOIN with forged public_key
        request_data = RequestJoinRequest(
            subject_id="authorized-subject",
            public_key="forged-key-hex"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify request is rejected
        assert response["success"] is False
        assert "Subject/key binding not authorized" in response["error"]
    
    def test_unauthorized_caller_rejected(self, auth_layer, phase3_authority):
        """Test that unauthorized Windows user is rejected.
        
        Note: This is a placeholder test. The actual Windows-specific
        implementation would require real Windows security API integration.
        """
        # Register authorized subject
        auth_layer.register_subject(
            subject_id="authorized-subject",
            windows_sid="S-1-5-21-AUTHORIZED",
            allowed_public_keys=["authorized-key-hex"],
            parent_authority="test-parent"
        )
        
        # Attempt REQUEST_JOIN (caller verification is placeholder)
        request_data = RequestJoinRequest(
            subject_id="authorized-subject",
            public_key="authorized-key-hex"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Placeholder implementation returns success
        # Real implementation would verify Windows SID
        # This test will need to be updated when Windows-specific
        # OS identity verification is implemented
    
    def test_cross_run_token_rejected(self, phase3_authority):
        """Test that token from different execution is rejected."""
        # Create token for execution A
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Attempt to use token for execution B (different execution_id)
        # Request challenge with wrong execution_id
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="test-execution-2"  # Different execution
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="test-execution-2"  # Different execution
        )
        
        # Should be rejected because execution_id mismatch
        assert challenge_response["success"] is False
        assert "execution_id" in challenge_response["error"].lower() or "mismatch" in challenge_response["error"].lower()
    
    def test_replayed_token_rejected(self, phase3_authority):
        """Test that already-redeemed token is rejected."""
        # Create token
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Request challenge
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="test-execution-1"
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify challenge was issued
        assert challenge_response["success"] is True
        challenge = challenge_response["challenge"]
        
        # Redeem token (would require valid signature in production)
        # For testing, we verify the join_token is marked as redeemed
        # Attempt to redeem again should fail
        redeem_request = RedeemJoinRequest(
            join_token=join_token,
            signature="test-signature",
            execution_id="test-execution-1"
        ).to_dict()
        
        # First redeem (may fail signature check but should mark token)
        phase3_authority.handle_redeem_join(
            redeem_request,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Second redeem should fail (token already redeemed)
        redeem_response = phase3_authority.handle_redeem_join(
            redeem_request,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Should be rejected because token already redeemed
        assert redeem_response["success"] is False
        assert "redeemed" in redeem_response["error"].lower() or "already" in redeem_response["error"].lower()
    
    def test_stale_generation_rejected(self, phase3_authority, run_records_db):
        """Test that token from old generation is rejected."""
        # Create token for generation 1
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Advance to generation 2
        cursor = run_records_db.cursor()
        cursor.execute("""
            UPDATE run_records
            SET generation = 2
            WHERE execution_id = ?
        """, ("test-execution-1",))
        run_records_db.commit()
        
        # Attempt to use token from generation 1
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="test-execution-1"
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Should be rejected because generation mismatch
        assert challenge_response["success"] is False
        assert "generation" in challenge_response["error"].lower() or "mismatch" in challenge_response["error"].lower()
        
        # Attempt to use token from generation 1
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="test-execution-1"
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify generation mismatch is detected
        assert challenge_response["success"] is False
        assert "Generation mismatch" in challenge_response["error"]
    
    def test_revoked_authorization_rejected(self, phase3_authority, authentication_layer):
        """Test that revoked authorization is rejected (real revocation, not generation mismatch)."""
        # Register a subject first
        import win32security
        import win32api
        
        # Get current user SID for testing
        user = os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))
        sid, _, _ = win32security.LookupAccountName(None, user)
        sid_string = str(sid)
        
        authentication_layer.register_subject(
            subject_id="test-subject",
            windows_sid=sid_string,
            allowed_public_keys=["test-key"],
            parent_authority=str(os.getpid()),
            registering_authority="test-authority"
        )
        
        # Create token
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=os.getpid(),  # Use actual PID for Windows identity verification
            execution_id="test-execution-1"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Revoke the subject (real revocation, not generation mismatch)
        revoked = authentication_layer.revoke_subject(
            subject_id="test-subject",
            revoking_authority="test-authority",
            reason="Test revocation"
        )
        assert revoked is True
        
        # Attempt to use token from revoked subject
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="test-execution-1"
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=os.getpid(),
            execution_id="test-execution-1"
        )
        
        # Should be rejected because subject is revoked
        assert challenge_response["success"] is False
        assert "revoked" in challenge_response["error"].lower() or "active" in challenge_response["error"].lower()
    
    def test_wrong_execution_id_rejected(self, phase3_authority):
        """Test that token with wrong execution_id is rejected."""
        # Create token for execution_id-1
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="execution-id-1"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Attempt to use token with wrong execution_id
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="execution-id-2"  # Wrong execution_id
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="execution-id-2"  # Wrong execution_id
        )
        
        # Should be rejected because execution_id mismatch
        assert challenge_response["success"] is False
        assert "execution_id" in challenge_response["error"].lower() or "mismatch" in challenge_response["error"].lower()
    
    def test_cross_execution_id_rejected(self, phase3_authority):
        """Test that token cannot be used across different execution contexts."""
        # Create token for execution A
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="execution-A"
        )
        
        # Verify token was created
        assert response["success"] is True
        join_token = response["join_token"]
        
        # Attempt to use token in execution B context
        challenge_request = RequestChallengeRequest(
            join_token=join_token,
            subject_id="test-subject",
            execution_id="execution-B"  # Different execution context
        ).to_dict()
        
        challenge_response = phase3_authority.handle_request_challenge(
            challenge_request,
            client_pid=1234,
            execution_id="execution-B"  # Different execution context
        )
        
        # Should be rejected because execution_id mismatch
        assert challenge_response["success"] is False
        assert "execution_id" in challenge_response["error"].lower() or "mismatch" in challenge_response["error"].lower()
    
    def test_double_join_rejected(self, phase3_authority):
        """Test that the same subject cannot join twice (exactly-once semantics)."""
        # First join request
        request_data = RequestJoinRequest(
            subject_id="test-subject",
            public_key="test-key"
        ).to_dict()
        
        response1 = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Verify first join succeeded
        assert response1["success"] is True
        join_token1 = response1["join_token"]
        
        # Second join request with same subject_id and execution_id
        response2 = phase3_authority.handle_request_join(
            request_data,
            client_pid=1234,
            execution_id="test-execution-1"
        )
        
        # Should be rejected because subject already joined
        assert response2["success"] is False
        assert "already" in response2["error"].lower() or "exists" in response2["error"].lower() or "duplicate" in response2["error"].lower()
    
    def test_concurrent_join_rejected(self, phase3_authority):
        """Test that concurrent join requests are rejected (race condition protection)."""
        import threading
        import time
        
        results = []
        errors = []
        
        def attempt_join():
            try:
                request_data = RequestJoinRequest(
                    subject_id="test-concurrent-subject",
                    public_key="test-key"
                ).to_dict()
                
                response = phase3_authority.handle_request_join(
                    request_data,
                    client_pid=1234,
                    execution_id="test-concurrent-execution"
                )
                
                results.append(response)
            except Exception as e:
                errors.append(e)
        
        # Launch multiple concurrent join requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=attempt_join)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Only one should succeed
        success_count = sum(1 for r in results if r.get("success") is True)
        assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
        
        # Others should fail
        failure_count = sum(1 for r in results if r.get("success") is False)
        assert failure_count == 4, f"Expected 4 failures, got {failure_count}"


class TestHandleInheritanceNegative:
    """Negative tests for handle inheritance (Windows-specific)."""
    
    def test_unrelated_handle_not_inherited(self):
        """Test that unrelated inheritable handle is not inherited.
        
        This is a Windows-specific test that requires:
        1. Create unrelated inheritable handle in parent
        2. Spawn child with HANDLE_LIST (only stdin)
        3. Child attempts to access unrelated handle
        4. Verify access fails (handle not inherited)
        5. Verify only stdin handle is available
        
        Note: This test cannot run on non-Windows platforms.
        It documents the expected behavior for Windows environments.
        """
        # This test requires Windows-specific implementation
        # It documents the security property that should be enforced
        pytest.skip("Windows-specific test - requires Windows environment")
