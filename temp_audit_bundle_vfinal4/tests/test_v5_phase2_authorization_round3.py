"""P0.213 V5 Phase 2 Round 3 Authorization Tests.

Test matrix covering:
1. register → issue → consume real IPC
2. same connection lifecycle works
3. reconnect lifecycle works if supported
4. authorized identity/context → ALLOW
5. unauthorized identity/context → DENY
6. approved task context → ALLOW
7. wrong task context → DENY
8. broad scope → DENY
9. wildcard/admin scope → DENY
10. wrong run_id → DENY
11. wrong execution_id → DENY
12. wrong process → DENY
13. wrong generation → DENY
14. tampered HMAC → DENY
15. expired lease → DENY
16. TWO real clients, ONE success / ONE reject
17. replay via IPC → DENY
18. replay after restart → DENY

Phase 2 Round 3 Status: CANONICAL_PROTOCOL_WITH_CONTEXTUAL_AUTHORIZATION
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.services.trust.authority_protocol import (
    RegisterExecutionRequest,
    RegisterExecutionResponse,
    IssueLeaseRequest,
    IssueLeaseResponse,
    ConsumeLeaseRequest,
    ConsumeLeaseResponse,
    AuthorizationPolicyInput,
    apply_authorization_policy,
)
from iabv_v15.services.trust.authority_service import AuthorityService
from iabv_v15.services.trust.authority_client import AuthorityClient


# ── L2 Unit Tests: Protocol Schema and Policy ─────────────────────────────────────

class TestProtocolSchema:
    """L2: Test canonical protocol schema."""
    
    def test_register_execution_request_serialization(self):
        """Test RegisterExecutionRequest serialization."""
        request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis",
            episode_id="ep1",
            session_id="sess1"
        )
        
        data = request.to_dict()
        assert data["invocation_id"] == "test_invocation"
        assert data["action"] == "READ"
        assert data["target"] == "codebase"
        assert data["requested_scope"] == "codebase:read"
        assert data["task_context"] == "self_analysis"
        
        reconstructed = RegisterExecutionRequest.from_dict(data)
        assert reconstructed.invocation_id == request.invocation_id
        assert reconstructed.action == request.action
        assert reconstructed.target == request.target
    
    def test_issue_lease_request_serialization(self):
        """Test IssueLeaseRequest serialization."""
        request = IssueLeaseRequest(
            run_id="test_run",
            execution_id="test_exec",
            requested_ttl_seconds=3600
        )
        
        data = request.to_dict()
        assert data["run_id"] == "test_run"
        assert data["execution_id"] == "test_exec"
        assert data["requested_ttl_seconds"] == 3600
        
        reconstructed = IssueLeaseRequest.from_dict(data)
        assert reconstructed.run_id == request.run_id
        assert reconstructed.execution_id == request.execution_id
    
    def test_consume_lease_request_serialization(self):
        """Test ConsumeLeaseRequest serialization."""
        request = ConsumeLeaseRequest(
            lease_id="test_lease",
            execution_id="test_exec"
        )
        
        data = request.to_dict()
        assert data["lease_id"] == "test_lease"
        assert data["execution_id"] == "test_exec"
        
        reconstructed = ConsumeLeaseRequest.from_dict(data)
        assert reconstructed.lease_id == request.lease_id
        assert reconstructed.execution_id == request.execution_id


class TestAuthorizationPolicy:
    """L2: Test contextual authorization policy."""
    
    def test_policy_allows_authorized_context(self):
        """Test 4: authorized identity/context → ALLOW."""
        policy_input = AuthorizationPolicyInput(
            observed_process_identity={"pid": 1234},
            canonical_run_record=None,
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis",
            generation=1
        )
        
        decision = apply_authorization_policy(policy_input)
        assert decision.allowed is True
        assert decision.authorized_scope == "codebase:read"
    
    def test_policy_denies_unauthorized_identity(self):
        """Test 5: unauthorized identity/context → DENY."""
        policy_input = AuthorizationPolicyInput(
            observed_process_identity={"pid": 0},  # Invalid PID
            canonical_run_record=None,
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis",
            generation=1
        )
        
        decision = apply_authorization_policy(policy_input)
        assert decision.allowed is False
        assert "Invalid process identity" in decision.reason
    
    def test_policy_allows_approved_task_context(self):
        """Test 6: approved task context → ALLOW."""
        policy_input = AuthorizationPolicyInput(
            observed_process_identity={"pid": 1234},
            canonical_run_record=None,
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis",
            generation=1
        )
        
        decision = apply_authorization_policy(policy_input)
        assert decision.allowed is True
    
    def test_policy_denies_wrong_task_context(self):
        """Test 7: wrong task context → DENY."""
        policy_input = AuthorizationPolicyInput(
            observed_process_identity={"pid": 1234},
            canonical_run_record=None,
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="unrelated_objective",
            generation=1
        )
        
        decision = apply_authorization_policy(policy_input)
        assert decision.allowed is False
        assert "not permitted for task context" in decision.reason
    
    def test_policy_denies_broad_scope(self):
        """Test 8: broad scope → DENY."""
        policy_input = AuthorizationPolicyInput(
            observed_process_identity={"pid": 1234},
            canonical_run_record=None,
            action="READ",
            target="codebase",
            requested_scope="codebase:write",  # Write not allowed for self_analysis
            task_context="self_analysis",
            generation=1
        )
        
        decision = apply_authorization_policy(policy_input)
        assert decision.allowed is False
        assert "not allowed for self_analysis task" in decision.reason
    
    def test_policy_denies_wildcard_scope(self):
        """Test 9: wildcard/admin scope → DENY."""
        for scope in ["*", "admin", "admin:all", "root", "superuser"]:
            policy_input = AuthorizationPolicyInput(
                observed_process_identity={"pid": 1234},
                canonical_run_record=None,
                action="READ",
                target="codebase",
                requested_scope=scope,
                task_context="self_analysis",
                generation=1
            )
            
            decision = apply_authorization_policy(policy_input)
            assert decision.allowed is False
            assert "Privileged scope not allowed" in decision.reason


# ── L3 Component Tests: AuthorityService with Canonical Protocol ───────────────

class TestAuthorityServiceCanonicalProtocol:
    """L3: Test AuthorityService with canonical protocol."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            yield storage
    
    @pytest.fixture
    def authority(self, temp_storage):
        """Create AuthorityService instance."""
        service = AuthorityService(storage_root=temp_storage)
        yield service
        # Cleanup
        if hasattr(service, '_shutdown'):
            service._shutdown()
    
    def test_register_execution_with_canonical_protocol(self, authority):
        """Test REGISTER_EXECUTION with canonical protocol."""
        request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        auth_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=request,
            request_id="test_invocation"
        )
        
        response = authority.handle_register_execution(auth_request, client_pid=1234)
        assert response.success is True
        assert "run_id" in response.data
        assert "execution_id" in response.data
        assert response.data["authorized_scope"] == "codebase:read"
    
    def test_issue_lease_with_canonical_protocol(self, authority):
        """Test ISSUE_LEASE with canonical protocol."""
        # First register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Then issue lease
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        assert issue_response.success is True
        assert "lease_id" in issue_response.data
        assert "signature" in issue_response.data
    
    def test_consume_lease_with_canonical_protocol(self, authority):
        """Test CONSUME_LEASE with canonical protocol."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Issue lease
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        lease_id = issue_response.data["lease_id"]
        
        # Consume lease
        consume_request = ConsumeLeaseRequest(
            lease_id=lease_id,
            execution_id=execution_id
        ).to_dict()
        
        consume_request_auth = AuthorityRequest(
            request_type="CONSUME_LEASE",
            data=consume_request,
            request_id=lease_id
        )
        
        consume_response = authority.handle_consume_lease(consume_request_auth, client_pid=1234)
        assert consume_response.success is True
        assert consume_response.data["consumed"] is True


# ── L3 Adversarial Tests: Wrong Binding and Signature ─────────────────────────

class TestAdversarialBinding:
    """L5: Test adversarial binding scenarios."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            yield storage
    
    @pytest.fixture
    def authority(self, temp_storage):
        """Create AuthorityService instance."""
        service = AuthorityService(storage_root=temp_storage)
        yield service
        if hasattr(service, '_shutdown'):
            service._shutdown()
    
    def test_wrong_run_id_denied(self, authority):
        """Test 10: wrong run_id → DENY."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        execution_id = reg_response.data["execution_id"]
        
        # Try to issue lease with wrong run_id
        issue_request = IssueLeaseRequest(
            run_id="wrong_run_id",
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id="wrong_run_id"
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        assert issue_response.success is False
        assert "Run record not found" in issue_response.error
    
    def test_wrong_execution_id_denied(self, authority):
        """Test 11: wrong execution_id → DENY."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        
        # Try to issue lease with wrong execution_id
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id="wrong_execution_id",
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        assert issue_response.success is False
        assert "Execution ID mismatch" in issue_response.error
    
    def test_wrong_process_denied(self, authority):
        """Test 12: wrong process → DENY."""
        # Register with PID 1234
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Try to issue lease with different PID
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=5678)
        assert issue_response.success is False
        assert "Client PID mismatch" in issue_response.error
    
    def test_wrong_generation_denied(self, authority):
        """Test 13: wrong generation → DENY."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Increment generation
        authority._increment_generation()
        
        # Try to issue lease with old generation
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        assert issue_response.success is False
        assert "Generation mismatch" in issue_response.error
    
    def test_tampered_hmac_denied(self, authority):
        """Test 14: tampered HMAC → DENY."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Issue lease
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        lease_id = issue_response.data["lease_id"]
        
        # Tamper with signature in database
        conn = sqlite3.connect(str(authority._lease_state_db))
        cursor = conn.cursor()
        cursor.execute("UPDATE leases SET signature = 'tampered' WHERE lease_id = ?", (lease_id,))
        conn.commit()
        conn.close()
        
        # Try to consume lease
        consume_request = ConsumeLeaseRequest(
            lease_id=lease_id,
            execution_id=execution_id
        ).to_dict()
        
        consume_request_auth = AuthorityRequest(
            request_type="CONSUME_LEASE",
            data=consume_request,
            request_id=lease_id
        )
        
        consume_response = authority.handle_consume_lease(consume_request_auth, client_pid=1234)
        assert consume_response.success is False
        assert "Invalid lease signature" in consume_response.error
    
    def test_expired_lease_denied(self, authority):
        """Test 15: expired lease → DENY."""
        # Register
        register_request = RegisterExecutionRequest(
            invocation_id="test_invocation",
            action="READ",
            target="codebase",
            requested_scope="codebase:read",
            task_context="self_analysis"
        ).to_dict()
        
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        reg_request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=register_request,
            request_id="test_invocation"
        )
        
        reg_response = authority.handle_register_execution(reg_request, client_pid=1234)
        run_id = reg_response.data["run_id"]
        execution_id = reg_response.data["execution_id"]
        
        # Issue lease with 1 second TTL
        issue_request = IssueLeaseRequest(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=1
        ).to_dict()
        
        issue_request_auth = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=issue_request,
            request_id=run_id
        )
        
        issue_response = authority.handle_issue_lease(issue_request_auth, client_pid=1234)
        lease_id = issue_response.data["lease_id"]
        
        # Wait for expiry
        time.sleep(2)
        
        # Try to consume expired lease
        consume_request = ConsumeLeaseRequest(
            lease_id=lease_id,
            execution_id=execution_id
        ).to_dict()
        
        consume_request_auth = AuthorityRequest(
            request_type="CONSUME_LEASE",
            data=consume_request,
            request_id=lease_id
        )
        
        consume_response = authority.handle_consume_lease(consume_request_auth, client_pid=1234)
        assert consume_response.success is False
        assert "Lease expired" in consume_response.error


# ── L4 Real IPC Tests ──────────────────────────────────────────────────────────
# NOTE: L4 tests moved to test_v5_phase2_authorization_round4_l4.py
# These tests require AuthorityServer process and are in separate file
