"""Test that selected resource identity survives into orchestrator metadata.

This test verifies that:
- selected_tool
- selected_resource_id
- selected_credential_ref
remain distinguishable through the metadata path.
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
    rank_workers_for_target,
)


class TestOrchestratorMetadataPreservation:
    """Test that selected resource identity survives into orchestrator metadata."""

    def test_selected_resource_identity_survives_compaction(self):
        """Test: Selected resource identity survives compaction for orchestrator metadata."""
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

        # Rank and select
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

        top_worker_compacted = _compact(ranked[0])

        # Simulate metadata deposit as done in AdaptiveTaskOrchestrator
        # (based on the actual pattern: _email = str((_gate.get('top_worker') or {}).get('email') or ''))
        session_metadata = {
            'selected_tool': top_worker_compacted.get('tool', ''),
            'selected_email': top_worker_compacted.get('email', ''),
            'selected_resource_id': top_worker_compacted.get('resource_id', ''),
            'selected_provider': top_worker_compacted.get('provider', ''),
            'selected_credential_ref': top_worker_compacted.get('credential_ref', ''),
        }

        # Verify resource identity survives metadata
        assert session_metadata['selected_tool'] == 'devin_api'
        assert session_metadata['selected_resource_id'] == 'devin_credential_0'
        assert session_metadata['selected_provider'] == 'devin'
        assert session_metadata['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY'
        assert session_metadata['selected_email'] == ''  # Empty for API credentials

    def test_multiple_resources_distinguishable_in_metadata(self):
        """Test: Two distinct resources remain distinguishable in metadata."""
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

        # Simulate compaction for each
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

        # Simulate metadata for each
        metadata_list = [
            {
                'selected_tool': c.get('tool', ''),
                'selected_resource_id': c.get('resource_id', ''),
                'selected_credential_ref': c.get('credential_ref', ''),
            }
            for c in compacted
        ]

        # Verify both resources remain distinguishable in metadata
        resource_ids = {m['selected_resource_id'] for m in metadata_list}
        assert 'devin_credential_0' in resource_ids
        assert 'devin_credential_1' in resource_ids

        credential_refs = {m['selected_credential_ref'] for m in metadata_list}
        assert 'devin:credential_0:DEVIN_API_KEY' in credential_refs
        assert 'devin:credential_1:IABV_DEVIN_API_KEY' in credential_refs

    def test_browser_resource_metadata_preserves_email(self):
        """Test: Browser resource metadata preserves email (compatibility)."""
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

        top_worker_compacted = _compact(ranked[0])

        # Simulate metadata deposit
        session_metadata = {
            'selected_tool': top_worker_compacted.get('tool', ''),
            'selected_email': top_worker_compacted.get('email', ''),
            'selected_resource_id': top_worker_compacted.get('resource_id', ''),
            'selected_credential_ref': top_worker_compacted.get('credential_ref', ''),
        }

        # Verify browser-specific fields are preserved
        assert session_metadata['selected_tool'] == 'chatgpt_web'
        assert session_metadata['selected_email'] == 'user1@example.com'
        assert session_metadata['selected_resource_id'] == ''  # Browser workers don't have resource_id
        assert session_metadata['selected_credential_ref'] == ''  # Browser workers don't have credential_ref
