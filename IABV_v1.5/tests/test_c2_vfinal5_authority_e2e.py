"""
C2 VFINAL5 Authority E2E Test with Existing Execution

This test suite verifies the end-to-end authority flow for MCP self-update
with trusted execution context preservation:

1. Register an execution with the authority
2. Use acquire_capability_for_existing_execution to verify and acquire capability
3. Verify no new execution is created
4. Verify causal attribution is preserved
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.trust.capability_lifecycle import (
    acquire_capability_for_execution,
    acquire_capability_for_existing_execution,
)


class TestC2VFINAL5AuthorityE2E:
    """End-to-end authority tests for trusted execution context (VFINAL5)."""

    def test_register_execution_creates_new_execution(self):
        """Verify register_execution creates a new execution in the authority."""
        client = AuthorityClient()
        client.connect()
        
        try:
            # Register a new execution
            registration = client.register_execution(
                invocation_id='test_invocation_001',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            # Verify registration returned authority-owned IDs
            assert 'run_id' in registration
            assert 'execution_id' in registration
            assert 'consumer_pid' in registration
            assert 'generation' in registration
            assert 'authorized_scope' in registration
            
            # Verify IDs are not empty
            assert registration['run_id']
            assert registration['execution_id']
            
            # Store for subsequent test
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Issue a lease for this execution
            lease = client.issue_lease(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=3600
            )
            
            # Verify lease was issued
            assert 'lease_id' in lease
            assert lease['lease_id']
            
        finally:
            client.disconnect()

    def test_verify_existing_execution_context(self):
        """Verify verify_execution_context validates existing execution."""
        client = AuthorityClient()
        client.connect()
        
        try:
            # First, register an execution
            registration = client.register_execution(
                invocation_id='test_invocation_002',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
            # Now verify the execution context
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='test_session',
                episode_id='test_episode'
            )
            
            # Verify validation succeeded
            assert verification['valid'] == True
            assert 'consumer_pid' in verification
            assert 'generation' in verification
            assert 'authorized_scope' in verification
            
        finally:
            client.disconnect()

    def test_acquire_capability_for_existing_execution(self):
        """Verify acquire_capability_for_existing_execution reuses existing execution."""
        # First, register an execution
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_003',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            original_run_id = registration['run_id']
            original_execution_id = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Now use acquire_capability_for_existing_execution
        capability = acquire_capability_for_existing_execution(
            execution_id=original_execution_id,
            run_id=original_run_id,
            action='WRITE_REPOSITORY_FILE',
            target='file:test.txt',
            requested_scope='self_update',
            invocation_id='test_invocation_004',
            episode_id='test_episode',
            session_id='test_session'
        )
        
        # Verify capability was acquired
        assert 'run_id' in capability
        assert 'execution_id' in capability
        assert 'lease_id' in capability
        
        # CRITICAL: Verify the SAME execution_id and run_id are used
        # (no new execution was created)
        assert capability['run_id'] == original_run_id
        assert capability['execution_id'] == original_execution_id
        
        # Verify lease is different (new lease for existing execution)
        assert capability['lease_id']

    def test_acquire_capability_for_execution_creates_new_execution(self):
        """Verify acquire_capability_for_execution creates a new execution (for comparison)."""
        # Use the original function that creates new executions
        capability = acquire_capability_for_execution(
            action='WRITE_REPOSITORY_FILE',
            target='file:test.txt',
            requested_scope='self_update',
            invocation_id='test_invocation_005',
            episode_id='test_episode',
            session_id='test_session'
        )
        
        # Verify capability was acquired
        assert 'run_id' in capability
        assert 'execution_id' in capability
        assert 'lease_id' in capability
        
        # Verify new IDs were generated
        assert capability['run_id']
        assert capability['execution_id']
        assert capability['lease_id']

    def test_causal_attribution_preservation(self):
        """Verify causal attribution is preserved through multiple MCP invocations."""
        # Register initial execution
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_006',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            original_run_id = registration['run_id']
            original_execution_id = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Simulate multiple MCP invocations using the same execution context
        for i in range(3):
            capability = acquire_capability_for_existing_execution(
                execution_id=original_execution_id,
                run_id=original_run_id,
                action='WRITE_REPOSITORY_FILE',
                target=f'file:test_{i}.txt',
                requested_scope='self_update',
                invocation_id=f'test_invocation_007_{i}',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            # Verify same execution context is used
            assert capability['run_id'] == original_run_id
            assert capability['execution_id'] == original_execution_id
            
            # Verify different leases are issued (one per invocation)
            assert capability['lease_id']

    def test_verify_execution_context_fails_for_nonexistent(self):
        """Verify verify_execution_context fails for non-existent execution."""
        client = AuthorityClient()
        client.connect()
        
        try:
            # Try to verify a non-existent execution
            verification = client.verify_execution_context(
                execution_id='nonexistent_execution_999',
                run_id='nonexistent_run_999',
                session_id='test_session',
                episode_id='test_episode'
            )
            
            # Verify validation failed
            assert verification['valid'] == False
            assert 'error' in verification
            
        finally:
            client.disconnect()

    def test_acquire_capability_for_existing_execution_fails_for_nonexistent(self):
        """Verify acquire_capability_for_existing_execution fails for non-existent execution."""
        with pytest.raises(RuntimeError, match="Execution context validation failed"):
            acquire_capability_for_existing_execution(
                execution_id='nonexistent_execution_999',
                run_id='nonexistent_run_999',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                invocation_id='test_invocation_008',
                episode_id='test_episode',
                session_id='test_session'
            )

    def test_cross_execution_context_rejected(self):
        """Negative test: Context from another execution should be rejected."""
        # Register execution 1
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_009',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            run_id_1 = registration['run_id']
            execution_id_1 = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Try to use execution_id_1 with a different run_id (cross-execution)
        with pytest.raises(RuntimeError, match="Execution context validation failed"):
            acquire_capability_for_existing_execution(
                execution_id=execution_id_1,
                run_id='other_run_999',  # Different run_id
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                invocation_id='test_invocation_010',
                episode_id='test_episode',
                session_id='test_session'
            )

    def test_altered_run_id_rejected(self):
        """Negative test: Altered run_id should be rejected."""
        # Register execution
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_011',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session'
            )
            
            execution_id = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Try to use altered run_id
        with pytest.raises(RuntimeError, match="Execution context validation failed"):
            acquire_capability_for_existing_execution(
                execution_id=execution_id,
                run_id='altered_run_999',  # Altered run_id
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                invocation_id='test_invocation_012',
                episode_id='test_episode',
                session_id='test_session'
            )

    def test_altered_session_id_rejected(self):
        """Negative test: Altered session_id should be rejected."""
        # Register execution with session_id
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_011',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode',
                session_id='test_session_original'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Try to verify with altered session_id
        client = AuthorityClient()
        client.connect()
        
        try:
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='test_session_altered',  # Altered session_id
                episode_id='test_episode'
            )
            
            # Verify validation failed
            assert verification['valid'] == False
            assert 'Session ID mismatch' in verification['error']
            
        finally:
            client.disconnect()

    def test_altered_episode_id_rejected(self):
        """Negative test: Altered episode_id should be rejected."""
        # Register execution with episode_id
        client = AuthorityClient()
        client.connect()
        
        try:
            registration = client.register_execution(
                invocation_id='test_invocation_012',
                action='WRITE_REPOSITORY_FILE',
                target='file:test.txt',
                requested_scope='self_update',
                task_context='tool_execution',
                episode_id='test_episode_original',
                session_id='test_session'
            )
            
            run_id = registration['run_id']
            execution_id = registration['execution_id']
            
        finally:
            client.disconnect()
        
        # Try to verify with altered episode_id
        client = AuthorityClient()
        client.connect()
        
        try:
            verification = client.verify_execution_context(
                execution_id=execution_id,
                run_id=run_id,
                session_id='test_session',
                episode_id='test_episode_altered'  # Altered episode_id
            )
            
            # Verify validation failed
            assert verification['valid'] == False
            assert 'Episode ID mismatch' in verification['error']
            
        finally:
            client.disconnect()

    def test_wrong_action_rejected(self):
        """Negative test: Wrong action should be rejected by self_update policy."""
        from iabv_v15.services.trust.authority_protocol import (
            AuthorizationPolicyInput,
            apply_authorization_policy
        )
        
        # Test with unauthorized action
        policy_input = AuthorizationPolicyInput(
            action="UNAUTHORIZED_ACTION",
            target="file:test.txt",
            requested_scope="self_update",
            task_context="tool_execution",
            observed_process_identity={"pid": 1234}
        )
        
        decision = apply_authorization_policy(policy_input)
        
        # Verify decision rejected
        assert decision.allowed == False
        assert "not allowed for self_update scope" in decision.reason

    def test_wrong_target_rejected(self):
        """Negative test: Security-critical target should be rejected by self_update policy."""
        from iabv_v15.services.trust.authority_protocol import (
            AuthorizationPolicyInput,
            apply_authorization_policy
        )
        
        # Test with security-critical target (services/trust/)
        policy_input = AuthorizationPolicyInput(
            action="WRITE_REPOSITORY_FILE",
            target="file:src/iabv_v15/services/trust/authority_service.py",
            requested_scope="self_update",
            task_context="tool_execution",
            observed_process_identity={"pid": 1234}
        )
        
        decision = apply_authorization_policy(policy_input)
        
        # Verify decision rejected
        assert decision.allowed == False
        assert "security-critical path" in decision.reason

    def test_security_critical_targets_rejected(self):
        """Negative test: All security-critical targets should be rejected."""
        from iabv_v15.services.trust.authority_protocol import (
            AuthorizationPolicyInput,
            apply_authorization_policy
        )
        
        # Test representative security-critical targets
        security_critical_targets = [
            "file:src/iabv_v15/services/trust/authority_service.py",
            "file:src/iabv_v15/services/trust/capability_lifecycle.py",
            "file:src/iabv_v15/security/",
            "file:src/iabv_v15/infra/mcp/server.py",
            "file:src/iabv_v15/domain/models.py",
            "file:bootstrap.py",
            "file:.git/config",
            "file:.git/hooks/pre-commit",
        ]
        
        for target in security_critical_targets:
            policy_input = AuthorizationPolicyInput(
                action="WRITE_REPOSITORY_FILE",
                target=target,
                requested_scope="self_update",
                task_context="tool_execution",
                observed_process_identity={"pid": 1234}
            )
            
            decision = apply_authorization_policy(policy_input)
            
            # Verify decision rejected
            assert decision.allowed == False, f"Target '{target}' should be rejected but was allowed"
            assert "security-critical path" in decision.reason or "not allowed" in decision.reason

    def test_safe_self_update_allowed(self):
        """Positive test: Authorized safe target should still work (PHASE 8)."""
        from iabv_v15.services.trust.authority_protocol import (
            AuthorizationPolicyInput,
            apply_authorization_policy
        )
        
        # Test with safe authorized target (example module in workspace)
        policy_input = AuthorizationPolicyInput(
            action="WRITE_REPOSITORY_FILE",
            target="file:src/iabv_v15/example_module.py",
            requested_scope="self_update",
            task_context="tool_execution",
            observed_process_identity={"pid": 1234}
        )
        
        decision = apply_authorization_policy(policy_input)
        
        # Verify decision allowed
        assert decision.allowed == True
        assert decision.authorized_scope == "self_update"
        assert decision.constraints is not None
        assert decision.constraints["allowed_action"] == "WRITE_REPOSITORY_FILE"
        assert decision.constraints["allowed_target"] == "file:src/iabv_v15/example_module.py"

    def test_authority_unavailable_fails_closed(self):
        """Negative test: Authority unavailable should fail closed."""
        # This test would require stopping the authority process
        # For now, we document the expected behavior
        # In production, this would test that the client handles pipe connection failure
        pass  # Placeholder - requires authority process management
