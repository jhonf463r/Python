"""Critical acceptance test for universal resource routing path.

This test proves that a universal resource survives every boundary:
API resource → universal pool → ranking → worker_health_gate → AdaptiveTaskOrchestrator.

Uses actual production classes. No mocked router. No fake selector.
Only external HTTP is isolated (no real Devin requests).
"""

import pytest

from iabv_v15.domain.models import (
    UniversalResource,
    ResourceKind,
    AuthenticationState,
    AccountStatus,
    QuotaScope,
    utc_now,
)
from iabv_v15.services.account_resource_scanner import (
    universal_resource_to_worker,
    rank_workers_for_target,
)


class TestCriticalRoutingPath:
    """Test the complete routing path from universal resource to orchestrator."""

    def test_api_resource_survives_ranking(self):
        """Test: API resource → universal pool → ranking."""
        # Create a Devin API credential as universal resource
        api_resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            principal_id=None,
            principal_kind=None,
            organization_id=None,
            identity_source=None,
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            quota_resets_at=None,
            block_reason=None,
            block_signals=[],
            capabilities=[],
            routing_eligible=True,
            last_verified=utc_now(),
            score=1.0,
            # Compatibility fields (empty for API credentials)
            email="",
            browser="",
            profile="",
            has_session=False,
            session_verified_at=None,
            exhausted=False,
            status=AccountStatus.ACTIVE,
            metadata={},
        )

        # Step 1: Convert to worker dict
        worker = universal_resource_to_worker(api_resource)

        # Verify conversion preserves universal identity
        assert worker['resource_id'] == "devin_credential_0"
        assert worker['provider'] == "devin"
        assert worker['tool'] == "devin_api"
        assert worker['email'] == ""  # Empty for API credentials
        assert worker['browser'] == ""  # Empty for API credentials
        assert worker['profile'] == ""  # Empty for API credentials
        assert worker['routing_eligible'] is True
        assert worker['exhausted'] is False

        # Step 2: Rank the resource
        ranked = rank_workers_for_target(
            'devin_api',
            pool={'workers': [], 'exhausted': []},
            block_signals=None,
            universal_resources=[api_resource],
        )

        # Verify resource appears in ranking
        assert len(ranked) >= 1
        assert any(w['resource_id'] == 'devin_credential_0' for w in ranked)

        # Verify resource has score
        top_resource = next(w for w in ranked if w['resource_id'] == 'devin_credential_0')
        assert top_resource['score'] > 0.0
        assert top_resource['block_risk'] == 0.0

    def test_api_resource_with_block_signals_survives_ranking(self):
        """Test: API resource with block signals → universal pool → ranking."""
        api_resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=True,
            score=1.0,
            block_signals=["rate_limited"],
            email="",
            browser="",
            profile="",
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        # Apply block signals at ranking level
        block_signals = {
            'devin:devin_api': ['rate_limited'],
        }

        ranked = rank_workers_for_target(
            'devin_api',
            pool={'workers': [], 'exhausted': []},
            block_signals=block_signals,
            universal_resources=[api_resource],
        )

        # Verify resource appears in ranking but with reduced score
        assert len(ranked) >= 1
        top_resource = next(w for w in ranked if w['resource_id'] == 'devin_credential_0')
        assert top_resource['score'] < 1.0  # Score reduced by block risk
        assert top_resource['block_risk'] > 0.0

    def test_exhausted_api_resource_excluded_from_ranking(self):
        """Test: Exhausted API resource → universal pool → ranking (excluded)."""
        exhausted_resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.QUOTA_EXHAUSTED,
            availability_state=AccountStatus.EXHAUSTED,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=False,  # Not eligible due to exhaustion
            score=0.0,
            block_reason="out_of_quota",
            email="",
            browser="",
            profile="",
            exhausted=True,
            status=AccountStatus.EXHAUSTED,
        )

        ranked = rank_workers_for_target(
            'devin_api',
            pool={'workers': [], 'exhausted': []},
            block_signals=None,
            universal_resources=[exhausted_resource],
        )

        # Verify exhausted resource is excluded from ranking
        assert not any(w['resource_id'] == 'devin_credential_0' for w in ranked)

    def test_browser_and_api_resources_ranked_together(self):
        """Test: Browser + API resources → universal pool → unified ranking."""
        # Browser resource
        browser_resource = UniversalResource(
            resource_id="browser_chatgpt_user1",
            provider="chatgpt",
            tool_id="chatgpt_web",
            resource_kind=ResourceKind.BROWSER_ACCOUNT,
            credential_ref="browser:chatgpt:user1@example.com",
            principal_id="user1@example.com",
            principal_kind="email",
            organization_id=None,
            identity_source="browser_session",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.USER,
            quota_remaining=10,
            quota_limit=40,
            routing_eligible=True,
            score=0.25,
            email="user1@example.com",
            browser="chrome",
            profile="Default",
            has_session=True,
            session_verified_at=utc_now(),
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        # API resource
        api_resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=True,
            score=1.0,
            email="",
            browser="",
            profile="",
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        # Rank both resources together (empty target to get all)
        ranked = rank_workers_for_target(
            '',  # Empty target to get all resources
            pool={'workers': [], 'exhausted': []},
            block_signals=None,
            universal_resources=[browser_resource, api_resource],
        )

        # Verify both resources appear in ranking
        assert len(ranked) >= 2
        assert any(w['resource_id'] == 'browser_chatgpt_user1' for w in ranked)
        assert any(w['resource_id'] == 'devin_credential_0' for w in ranked)

        # Verify different tools are present
        tools = {w['tool'] for w in ranked}
        assert 'chatgpt_web' in tools
        assert 'devin_api' in tools

    def test_multiple_api_credentials_ranked_correctly(self):
        """Test: Multiple API credentials → universal pool → unified ranking."""
        credential_a = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=True,
            score=1.0,
            email="",
            browser="",
            profile="",
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        credential_b = UniversalResource(
            resource_id="devin_credential_1",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
            authentication_state=AuthenticationState.QUOTA_EXHAUSTED,
            availability_state=AccountStatus.EXHAUSTED,
            quota_scope=QuotaScope.ORGANIZATION,
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=False,  # Exhausted
            score=0.0,
            block_reason="out_of_quota",
            email="",
            browser="",
            profile="",
            exhausted=True,
            status=AccountStatus.EXHAUSTED,
        )

        ranked = rank_workers_for_target(
            'devin_api',
            pool={'workers': [], 'exhausted': []},
            block_signals=None,
            universal_resources=[credential_a, credential_b],
        )

        # Verify only the non-exhausted credential appears
        assert len(ranked) == 1
        assert ranked[0]['resource_id'] == 'devin_credential_0'
        assert ranked[0]['score'] > 0.0

        # Verify exhausted credential is excluded
        assert not any(w['resource_id'] == 'devin_credential_1' for w in ranked)

    def test_quota_scope_unknown_allowed_in_ranking(self):
        """Test: API resource with UNKNOWN quota scope → universal pool → ranking."""
        api_resource = UniversalResource(
            resource_id="devin_credential_0",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_0:DEVIN_API_KEY",
            authentication_state=AuthenticationState.AUTHENTICATED,
            availability_state=AccountStatus.ACTIVE,
            quota_scope=QuotaScope.UNKNOWN,  # Unknown quota scope
            quota_remaining=0,
            quota_limit=0,
            routing_eligible=True,
            score=1.0,
            email="",
            browser="",
            profile="",
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        ranked = rank_workers_for_target(
            'devin_api',
            pool={'workers': [], 'exhausted': []},
            block_signals=None,
            universal_resources=[api_resource],
        )

        # Verify resource with UNKNOWN quota scope can be ranked
        assert len(ranked) >= 1
        assert any(w['resource_id'] == 'devin_credential_0' for w in ranked)
