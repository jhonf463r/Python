"""
VFINAL5-R2.2: Case-sensitivity bypass reproduction tests.

Claude independently verified that uppercase/mixed-case security paths
bypass the lowercase-only denylist in VFINAL5-R2.1.
"""

import unittest
from src.iabv_v15.services.trust.authority_protocol import (
    canonicalize_target,
    apply_authorization_policy,
    AuthorizationPolicyInput
)


class TestCaseSensitivityBypass(unittest.TestCase):
    """Reproduce case-sensitivity bypass in VFINAL5-R2.1."""
    
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
    
    def test_lowercase_trust_path_rejected(self):
        """Lowercase trust path should be rejected (baseline)."""
        input_data = self._create_policy_input("file:src/iabv_v15/services/trust/capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Lowercase trust path should be rejected")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_backslash_trust_path_rejected(self):
        """Backslash trust path should be rejected (VFINAL5-R2.1 fix)."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\services\\trust\\capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        self.assertFalse(decision.allowed, "Backslash trust path should be rejected")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_uppercase_trust_path_bypass(self):
        """UPPERCASE trust path should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:src/IABV_V15/SERVICES/TRUST/capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "UPPERCASE trust path should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_mixed_case_trust_path_bypass(self):
        """Mixed-case trust path should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:src\\iabv_v15\\SERVICES\\TRUST\\capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "Mixed-case trust path should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_partial_uppercase_trust_path_bypass(self):
        """Partial uppercase trust path should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:src/iabv_v15/services/TRUST/capability_action_bridge.py")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "Partial uppercase trust path should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_uppercase_security_path_bypass(self):
        """UPPERCASE security path should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:src/IABV_V15/SECURITY/config.py")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "UPPERCASE security path should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_uppercase_bootstrap_bypass(self):
        """UPPERCASE bootstrap should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:BOOTSTRAP.PY")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "UPPERCASE bootstrap should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())
    
    def test_uppercase_git_bypass(self):
        """UPPERCASE .git should be rejected after case normalization fix."""
        input_data = self._create_policy_input("file:.GIT/config")
        decision = apply_authorization_policy(input_data)
        # FIXED: Case normalization now prevents this bypass
        self.assertFalse(decision.allowed, "UPPERCASE .git should be rejected after case normalization")
        self.assertIn("security-critical", decision.reason.lower())


if __name__ == "__main__":
    unittest.main()
