"""Regression test for AccountApprovalLedger path in LocalRoleRouter.worker_health_gate.

This test exercises the branch that caused NameError: name 'target' is not defined
when AccountApprovalLedger is non-null.
"""

import pytest
from typing import Any
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.domain.models import UniversalResource, ResourceKind


class MockAccountApprovalLedger:
    """Mock AccountApprovalLedger for testing."""

    def __init__(self):
        self.approved_accounts = {}

    def add_approved(self, target: str, email: str, tool: str):
        """Add an approved account."""
        self.approved_accounts[target] = {
            'email': email,
            'tool': tool,
            'approved_at': None,
            'origin': 'test',
        }

    def get_approved(self, target: str):
        """Get approved account for target."""
        from types import SimpleNamespace
        approval = self.approved_accounts.get(target)
        if approval:
            return SimpleNamespace(**approval)
        return None

    def mark_validated(self, target: str, valid: bool):
        """Mark account as validated."""
        pass


class TestLocalRoleRouterApprovalLedger:
    """Test the AccountApprovalLedger path in worker_health_gate."""

    @pytest.fixture
    def approval_ledger(self):
        """Create a mock AccountApprovalLedger."""
        ledger = MockAccountApprovalLedger()
        # Add an approved account for testing
        ledger.add_approved(
            target='devin',
            email='test@example.com',
            tool='devin_api',
        )
        return ledger

    @pytest.fixture
    def router(self, approval_ledger, tmp_path):
        """Create a LocalRoleRouter with non-null AccountApprovalLedger."""
        class MockRunRepository:
            pass

        class MockArtifactRepository:
            pass

        def mock_scanner():
            # Return a pool with an eligible worker matching the approved account
            return {
                'workers': [],
                'universal_resources': [
                    UniversalResource(
                        resource_id='devin_test',
                        provider='devin',
                        tool_id='devin_api',
                        resource_kind=ResourceKind.API_CREDENTIAL,
                        credential_ref='opaque-test-ref',
                        routing_eligible=True,
                    )
                ],
                'available_count': 1,
            }

        router = LocalRoleRouter(
            workspace_root=str(tmp_path),
            general_provider=None,
            visual_provider=None,
            optional_provider=None,
            embedding_service=None,
            sql_service=None,
            analytics_service=None,
            customer_support_service=None,
            engineering_review_service=None,
            teaching_gap_analyzer=None,
            episode_repository=None,
            knowledge_repository=None,
            run_repository=MockRunRepository(),
            artifact_repository=MockArtifactRepository(),
            tool_teach_service=None,
            tool_registry=None,
            account_resource_scanner=mock_scanner,
            account_approval_ledger=approval_ledger,
        )
        return router

    def test_approval_ledger_path_no_nameerror(self, router):
        """Test that worker_health_gate with approval ledger does not raise NameError.

        This test exercises the branch that caused:
        NameError: name 'target' is not defined
        during external route acceptance.
        """
        # This should not raise NameError
        result = router.worker_health_gate(target_assistant='devin')

        # Verify the gate executed successfully
        assert 'usable' in result
        assert 'reason' in result
        # The exact outcome depends on the ranking logic, but no NameError should occur
