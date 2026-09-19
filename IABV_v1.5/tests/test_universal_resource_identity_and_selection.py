"""Tests for resource identity preservation and operational selection.

Tests:
- No duplicate resources in ranked result
- API resource identity survives worker_health_gate
- Multiple API resources remain distinguishable
- Selected resource identity survives downstream
- Browser compatibility preserved
- Blocked/exhausted resources not selected
- Secret hygiene maintained
"""

import pytest
from typing import Any

from iabv_v15.domain.models import (
    UniversalResource,
    ResourceKind,
    AuthenticationState,
    AccountStatus,
    QuotaScope,
    utc_now,
)
from iabv_v15.services.account_resource_scanner import (
    build_universal_resource_pool,
    universal_resource_to_worker,
    rank_workers_for_target,
)


class TestNoDuplicateResources:
    """Test that one UniversalResource produces one effective ranked candidate."""

    def test_no_duplicate_resource_in_ranked_result(self):
        """Test: One UniversalResource → one effective ranked candidate."""
        # Create an API resource
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

        # Build pool as done in _get_worker_pool (resources stored separately)
        pool = {
            'workers': [],  # Browser workers empty
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [api_resource],
        }

        # Rank with both pool and universal_resources
        ranked = rank_workers_for_target(
            'devin_api',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Verify only one candidate appears (no duplication)
        assert len(ranked) == 1
        assert ranked[0]['resource_id'] == 'devin_credential_0'

    def test_two_resources_two_candidates(self):
        """Test: Two UniversalResources → two ranked candidates."""
        resource_a = UniversalResource(
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

        resource_b = UniversalResource(
            resource_id="devin_credential_1",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
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

        pool = {
            'workers': [],
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [resource_a, resource_b],
        }

        ranked = rank_workers_for_target(
            '',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Verify two candidates appear (no duplication)
        assert len(ranked) == 2
        resource_ids = {w['resource_id'] for w in ranked}
        assert 'devin_credential_0' in resource_ids
        assert 'devin_credential_1' in resource_ids


class TestAPIIdentitySurvivesGate:
    """Test that API resource identity survives worker_health_gate compaction."""

    def test_api_identity_survives_compaction(self):
        """Test: API resource without email/browser/profile preserves identity through gate."""
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

        pool = {
            'workers': [],
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [api_resource],
        }

        # Rank as done in worker_health_gate
        ranked = rank_workers_for_target(
            'devin_api',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Simulate compaction as done in worker_health_gate
        _WORKER_KEYS = ('tool', 'email', 'browser', 'profile', 'remaining_messages', 'score', 'block_risk')
        _UNIVERSAL_KEYS = ('resource_id', 'provider', 'credential_ref')

        def _compact(w: dict[str, Any]) -> dict[str, Any]:
            d: dict[str, Any] = {}
            for k in _WORKER_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            for k in _UNIVERSAL_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            if 'remaining_messages' in d:
                d['remaining'] = d.pop('remaining_messages')
            return d

        compacted = _compact(ranked[0])

        # Verify universal identity survives compaction
        assert 'resource_id' in compacted
        assert compacted['resource_id'] == 'devin_credential_0'
        assert 'provider' in compacted
        assert compacted['provider'] == 'devin'
        assert 'credential_ref' in compacted
        assert compacted['credential_ref'] == 'devin:credential_0:DEVIN_API_KEY'

        # Verify email/browser/profile are empty (as expected for API credentials)
        assert compacted.get('email', '') == ""
        assert compacted.get('browser', '') == ""
        assert compacted.get('profile', '') == ""


class TestMultipleResourcesDistinguishable:
    """Test that multiple API resources remain distinguishable."""

    def test_two_devin_resources_distinguishable(self):
        """Test: Two distinct Devin resources remain distinguishable after selection."""
        resource_a = UniversalResource(
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

        resource_b = UniversalResource(
            resource_id="devin_credential_1",
            provider="devin",
            tool_id="devin_api",
            resource_kind=ResourceKind.API_CREDENTIAL,
            credential_ref="devin:credential_1:IABV_DEVIN_API_KEY",
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

        pool = {
            'workers': [],
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [resource_a, resource_b],
        }

        ranked = rank_workers_for_target(
            '',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Simulate compaction
        _WORKER_KEYS = ('tool', 'email', 'browser', 'profile', 'remaining_messages', 'score', 'block_risk')
        _UNIVERSAL_KEYS = ('resource_id', 'provider', 'credential_ref')

        def _compact(w: dict[str, Any]) -> dict[str, Any]:
            d: dict[str, Any] = {}
            for k in _WORKER_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            for k in _UNIVERSAL_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            if 'remaining_messages' in d:
                d['remaining'] = d.pop('remaining_messages')
            return d

        compacted = [_compact(w) for w in ranked]

        # Verify both resources remain distinguishable
        resource_ids = {c['resource_id'] for c in compacted}
        assert 'devin_credential_0' in resource_ids
        assert 'devin_credential_1' in resource_ids

        credential_refs = {c['credential_ref'] for c in compacted}
        assert 'devin:credential_0:DEVIN_API_KEY' in credential_refs
        assert 'devin:credential_1:IABV_DEVIN_API_KEY' in credential_refs


class TestBrowserCompatibility:
    """Test that browser resource selection remains unchanged."""

    def test_browser_resource_preserves_email_browser_profile(self):
        """Test: Browser resource preserves email/browser/profile through gate."""
        browser_worker = {
            'email': 'user1@example.com',
            'full_name': 'Test User',
            'tool': 'chatgpt_web',
            'browser': 'chrome',
            'profile': 'Default',
            'remaining_messages': 10,
            'used_in_window': 30,
            'limit': 40,
            'window_hours': 3,
            'exhausted': False,
            'label': 'ChatGPT',
            'resets_at': None,
        }

        pool = {
            'workers': [browser_worker],
            'exhausted': [],
            'available_count': 1,
            'exhausted_count': 0,
            'universal_resources': [],
        }

        ranked = rank_workers_for_target(
            'chatgpt_web',
            pool=pool,
            block_signals=None,
            universal_resources=[],
        )

        # Simulate compaction
        _WORKER_KEYS = ('tool', 'email', 'browser', 'profile', 'remaining_messages', 'score', 'block_risk')
        _UNIVERSAL_KEYS = ('resource_id', 'provider', 'credential_ref')

        def _compact(w: dict[str, Any]) -> dict[str, Any]:
            d: dict[str, Any] = {}
            for k in _WORKER_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            for k in _UNIVERSAL_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            if 'remaining_messages' in d:
                d['remaining'] = d.pop('remaining_messages')
            return d

        compacted = _compact(ranked[0])

        # Verify browser-specific fields are preserved
        assert compacted['email'] == 'user1@example.com'
        assert compacted['browser'] == 'chrome'
        assert compacted['profile'] == 'Default'
        assert compacted['tool'] == 'chatgpt_web'


class TestBlockedExhaustedResources:
    """Test that blocked/exhausted resources are not selected."""

    def test_exhausted_api_resource_not_selected(self):
        """Test: Exhausted API resource is excluded from selection."""
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
            routing_eligible=False,
            score=0.0,
            block_reason="out_of_quota",
            email="",
            browser="",
            profile="",
            exhausted=True,
            status=AccountStatus.EXHAUSTED,
        )

        pool = {
            'workers': [],
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [exhausted_resource],
        }

        ranked = rank_workers_for_target(
            'devin_api',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Verify exhausted resource is excluded
        assert not any(w['resource_id'] == 'devin_credential_0' for w in ranked)

    def test_blocked_api_resource_not_selected(self):
        """Test: Blocked API resource is excluded from selection."""
        blocked_resource = UniversalResource(
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
            routing_eligible=False,
            score=0.0,
            block_signals=["auth_failure"],
            block_reason="auth_failure",
            email="",
            browser="",
            profile="",
            exhausted=False,
            status=AccountStatus.ACTIVE,
        )

        pool = {
            'workers': [],
            'exhausted': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [blocked_resource],
        }

        ranked = rank_workers_for_target(
            'devin_api',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Verify blocked resource is excluded
        assert not any(w['resource_id'] == 'devin_credential_0' for w in ranked)


class TestSecretHygiene:
    """Test that secret values never appear in routing/selection structures."""

    def test_secret_never_in_compacted_worker(self):
        """Test: Compacted worker dict never contains secret values."""
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

        pool = {
            'workers': [],
            'available_count': 0,
            'exhausted_count': 0,
            'universal_resources': [api_resource],
        }

        ranked = rank_workers_for_target(
            'devin_api',
            pool=pool,
            block_signals=None,
            universal_resources=pool.get('universal_resources', []),
        )

        # Simulate compaction
        _WORKER_KEYS = ('tool', 'email', 'browser', 'profile', 'remaining_messages', 'score', 'block_risk')
        _UNIVERSAL_KEYS = ('resource_id', 'provider', 'credential_ref')

        def _compact(w: dict[str, Any]) -> dict[str, Any]:
            d: dict[str, Any] = {}
            for k in _WORKER_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            for k in _UNIVERSAL_KEYS:
                v = w.get(k)
                if v is not None and v != '':
                    d[k] = v
            if 'remaining_messages' in d:
                d['remaining'] = d.pop('remaining_messages')
            return d

        compacted = _compact(ranked[0])

        # Verify no secret fields
        assert 'secret' not in compacted
        assert 'api_key' not in compacted
        assert 'token' not in compacted
        assert 'password' not in compacted

        # Verify credential_ref is opaque reference, not value
        assert 'credential_ref' in compacted
        assert compacted['credential_ref'] == "devin:credential_0:DEVIN_API_KEY"
        # The reference contains the environment variable name, not the actual secret value
