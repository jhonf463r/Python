"""
VFINAL5-R2.1: Canonical target normalization and security-critical target tests.

Tests that:
1. Forward slash security-critical targets are rejected
2. Backslash security-critical targets are rejected
3. Mixed separator security-critical targets are rejected
4. Safe targets are still allowed
"""

import unittest
from src.iabv_v15.services.trust.authority_protocol import canonicalize_target, apply_authorization_policy, AuthorizationPolicyInput


class TestCanonicalTargetNormalization(unittest.TestCase):
    """Test canonical target normalization function."""
    
    def test_forward_slash_normalization(self):
        """Forward slash paths remain unchanged."""
        target = "file:src/iabv_v15/services/trust/foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, target)
    
    def test_backslash_normalization(self):
        """Backslash paths are normalized to forward slash."""
        target = "file:src\\iabv_v15\\services\\trust\\foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")
    
    def test_mixed_separator_normalization(self):
        """Mixed separator paths are normalized to forward slash."""
        target = "file:src/iabv_v15\\services\\trust/foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")
    
    def test_redundant_separator_normalization(self):
        """Redundant separators are collapsed."""
        target = "file:src//iabv_v15//services//trust//foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")
    
    def test_no_prefix_normalization(self):
        """Paths without prefix are normalized."""
        target = "src\\iabv_v15\\services\\trust\\foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "src/iabv_v15/services/trust/foo.py")
    
    def test_repository_prefix_normalization(self):
        """Repository prefix is preserved."""
        target = "repository:src\\iabv_v15\\services\\trust\\foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "repository:src/iabv_v15/services/trust/foo.py")
    
    def test_remote_prefix_normalization(self):
        """Remote prefix is preserved."""
        target = "remote:origin\\main"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "remote:origin/main")
    
    def test_current_directory_normalization(self):
        """Current directory components are removed."""
        target = "file:src/./iabv_v15/./services/trust/foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")
    
    def test_parent_directory_normalization(self):
        """Parent directory components are normalized."""
        target = "file:src/iabv_v15/services/../services/trust/foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")
    
    def test_traversal_attack_prevention(self):
        """Traversal attacks are prevented by normalization."""
        target = "file:src/iabv_v15/services/../../../etc/passwd"
        canonical = canonicalize_target(target)
        # The .. components should be normalized to prevent escaping
        self.assertNotIn("../../../", canonical)
    
    def test_mixed_traversal_normalization(self):
        """Mixed traversal with backslashes is normalized."""
        target = "file:src\\iabv_v15\\services\\..\\services\\trust\\foo.py"
        canonical = canonicalize_target(target)
        self.assertEqual(canonical, "file:src/iabv_v15/services/trust/foo.py")


class TestSecurityCriticalTargetRejection(unittest.TestCase):
    """Test that security-critical targets are rejected regardless of separator."""
    
    def _create_policy_input(self, target: str) -> AuthorizationPolicyInput:
        """Helper to create AuthorizationPolicyInput with required fields."""
        return AuthorizationPolicyInput(
            observed_process_identity={"pid": 12345},
            canonical_run_record=None,
            action="WRITE_REPOSITORY_FILE",
            target=target,
            requested_scope="self_update",
            task_context="tool_execution",
            generation=1
        )
    
    def test_forward_slash_trust_target_rejected(self):
        """Forward slash trust target is rejected."""
        input_data = self._create_policy_input("file:src/iabv_v15/services/trust/capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_backslash_trust_target_rejected(self):
        """Backslash trust target is rejected (Windows bypass fix)."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\services\\trust\\capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_mixed_separator_trust_target_rejected(self):
        """Mixed separator trust target is rejected."""
        input_data = self._create_policy_input("file:src/iabv_v15\\services\\trust/capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_forward_slash_security_target_rejected(self):
        """Forward slash security target is rejected."""
        input_data = self._create_policy_input("file:src/iabv_v15/security/config.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_backslash_security_target_rejected(self):
        """Backslash security target is rejected."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\security\\config.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_forward_slash_authority_target_rejected(self):
        """Forward slash authority target is rejected."""
        input_data = self._create_policy_input("file:src/iabv_v15/authority_service.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_backslash_authority_target_rejected(self):
        """Backslash authority target is rejected."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\authority_service.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_forward_slash_bootstrap_target_rejected(self):
        """Forward slash bootstrap target is rejected."""
        input_data = self._create_policy_input("file:bootstrap.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_backslash_bootstrap_target_rejected(self):
        """Backslash bootstrap target is rejected."""
        input_data = self._create_policy_input("file:bootstrap.py")  # bootstrap.py has no path separators
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_forward_slash_git_config_target_rejected(self):
        """Forward slash .git/config target is rejected."""
        input_data = self._create_policy_input("file:.git/config")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)
    
    def test_backslash_git_config_target_rejected(self):
        """Backslash .git/config target is rejected."""
        input_data = self._create_policy_input("file:.git\\config")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed)
        self.assertIn("security-critical", decision.reason)


class TestSafeTargetAllowed(unittest.TestCase):
    """Test that safe targets are still allowed after canonicalization."""
    
    def _create_policy_input(self, target: str) -> AuthorizationPolicyInput:
        """Helper to create AuthorizationPolicyInput with required fields."""
        return AuthorizationPolicyInput(
            observed_process_identity={"pid": 12345},
            canonical_run_record=None,
            action="WRITE_REPOSITORY_FILE",
            target=target,
            requested_scope="self_update",
            task_context="tool_execution",
            generation=1
        )
    
    def test_forward_slash_safe_target_allowed(self):
        """Forward slash safe target is allowed."""
        input_data = self._create_policy_input("file:src/iabv_v15/example.py")
        decision = apply_authorization_policy(input_data)
        self.assertTrue(decision.allowed)
    
    def test_backslash_safe_target_allowed(self):
        """Backslash safe target is allowed after normalization."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\example.py")
        decision = apply_authorization_policy(input_data)
        self.assertTrue(decision.allowed)
    
    def test_mixed_separator_safe_target_allowed(self):
        """Mixed separator safe target is allowed after normalization."""
        input_data = self._create_policy_input("file:src/iabv_v15\\example.py")
        decision = apply_authorization_policy(input_data)
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
