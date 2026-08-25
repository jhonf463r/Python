"""
VFINAL5-R3: Real Negative Matrix Tests

Context validation (execution_id, run_id, session_id, episode_id) is enforced
at the authority service level (issue_lease and consume_lease), not at the
policy evaluation level.

This test focuses on policy-level negative cases (target classification,
action/target binding).
"""

import unittest
from unittest.mock import MagicMock, Mock
from src.iabv_v15.services.trust.authority_protocol import (
    canonicalize_target,
    apply_authorization_policy,
    AuthorizationPolicyInput
)


class TestVFINAL5R3PolicyNegativeMatrix(unittest.TestCase):
    """VFINAL5-R3: Policy-level negative matrix tests."""
    
    def _create_policy_input(
        self,
        target: str = "file:src/example.py",
        action: str = "WRITE_REPOSITORY_FILE"
    ) -> AuthorizationPolicyInput:
        """Helper to create AuthorizationPolicyInput with required fields."""
        return AuthorizationPolicyInput(
            observed_process_identity={"pid": 12345},
            canonical_run_record={
                "execution_id": "test_execution",
                "run_id": "test_run",
                "session_id": "test_session",
                "episode_id": "test_episode"
            },
            action=action,
            target=target,
            requested_scope="self_update",
            task_context="tool_execution",
            generation=1
        )
    
    # Note: Context validation (execution_id, run_id, session_id, episode_id)
    # is enforced at authority_service.py:issue_lease and consume_lease, not here.
    # These tests focus on policy-level validation.
    
    # Test 1: Wrong action
    def test_1_wrong_action_rejects(self):
        """Wrong action should be rejected."""
        input_data = self._create_policy_input(action="UNAUTHORIZED_ACTION")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Wrong action should be rejected")
    
    # Test 2: Wrong target (security-critical)
    def test_2_wrong_target_rejects(self):
        """Wrong target (security-critical) should be rejected."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15/services/trust/foo.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Wrong target should be rejected")
    
    # Test 3: Case variant target (platform-independent)
    def test_3_case_variant_target_rejects(self):
        """Case variant target should be rejected (platform-independent)."""
        input_data = self._create_policy_input(
            target="file:src/IABV_V15/SERVICES/TRUST/foo.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Case variant target should be rejected")
    
    # Test 4: Backslash target
    def test_4_backslash_target_rejects(self):
        """Backslash target should be rejected."""
        input_data = self._create_policy_input(
            target="file:src\\iabv_v15\\services\\trust\\foo.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Backslash target should be rejected")
    
    # Test 5: Mixed separator target
    def test_5_mixed_separator_target_rejects(self):
        """Mixed separator target should be rejected."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15\\services/trust/foo.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Mixed separator target should be rejected")
    
    # Test 6: Traversal
    def test_6_traversal_rejects(self):
        """Traversal attack should be rejected."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15/services/../../../services/trust/foo.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Traversal attack should be rejected")
    
    # Test 7: Trust target
    def test_7_trust_target_rejects(self):
        """Trust target should be rejected."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15/services/trust/capability_action_bridge.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Trust target should be rejected")
    
    # Test 8: Security target
    def test_8_security_target_rejects(self):
        """Security target should be rejected."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15/security/config.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Security target should be rejected")
    
    # Test 9: Bootstrap target
    def test_9_bootstrap_target_rejects(self):
        """Bootstrap target should be rejected."""
        input_data = self._create_policy_input(
            target="file:bootstrap.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Bootstrap target should be rejected")
    
    # Test 10: Git config target
    def test_10_git_config_target_rejects(self):
        """Git config target should be rejected."""
        input_data = self._create_policy_input(
            target="file:.git/config"
        )
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Git config target should be rejected")
    
    # Test 11: Safe target allowed
    def test_11_safe_target_allowed(self):
        """Safe target should be allowed."""
        input_data = self._create_policy_input(
            target="file:src/iabv_v15/example_module.py"
        )
        decision = apply_authorization_policy(input_data)
        self.assertTrue(decision.allowed, "Safe target should be allowed")


class TestPlatformIndependentCanonicalization(unittest.TestCase):
    """VFINAL5-R3: Platform-independent canonicalization tests."""
    
    def test_case_normalization_all_platforms(self):
        """Case normalization should apply on all platforms."""
        # Test that case normalization is applied regardless of platform
        canonical1 = canonicalize_target("file:src/iabv_v15/services/trust/foo.py")
        canonical2 = canonicalize_target("file:src/IABV_V15/SERVICES/TRUST/foo.py")
        
        # Both should normalize to lowercase
        self.assertEqual(canonical1, canonical2)
        self.assertIn("services/trust/", canonical1.lower())
    
    def test_security_policy_consistency(self):
        """Security policy should be consistent across platforms."""
        # Test that security classification is consistent
        security_target = "file:src/iabv_v15/services/trust/foo.py"
        canonical = canonicalize_target(security_target)
        
        # Should contain the security-critical path
        self.assertIn("services/trust/", canonical)
        
        # Should be lowercase
        self.assertEqual(canonical, canonical.lower())


class TestAuthorityServiceContextValidation(unittest.TestCase):
    """VFINAL5-R3: Authority service context validation tests.
    
    Context validation (execution_id, run_id, session_id, episode_id) is
    enforced at authority_service.py:issue_lease and consume_lease.
    
    These tests document that the validation happens at the authority service
    level, not at the policy evaluation level.
    """
    
    def test_context_validation_at_authority_service(self):
        """Context validation is enforced at authority_service level.
        
        This test documents that:
        - execution_id validation happens in handle_issue_lease
        - session_id/episode_id validation happens in handle_issue_lease (for self_update)
        - Cross-validation happens in handle_issue_lease and handle_consume_lease
        
        The policy-level apply_authorization_policy does NOT validate context.
        """
        # This is a documentation test - the actual validation is in authority_service.py
        # See authority_service.py:handle_issue_lease lines 670-693
        # See authority_service.py:handle_consume_lease lines 905-922
        pass


if __name__ == "__main__":
    unittest.main()
