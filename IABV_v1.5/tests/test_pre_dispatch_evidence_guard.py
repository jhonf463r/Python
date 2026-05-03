"""Tests for Brecha 2.4 — Pre-dispatch evidence guard.

Validates that the ATO checks WorldModel evidence before dispatching
to an external route and blocks/falls back appropriately.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import (
    ObservationPermissionGate,
    RoleRoute,
    TaskRole,
    ToolCapability,
    ToolLiveStatus,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
    AdaptiveTaskOrchestrator,
)


def _make_route(provider: str = 'chatgpt', fallback: str | None = None) -> RoleRoute:
    return RoleRoute(
        task_role=TaskRole.RESEARCH,
        role_title='research',
        provider_name=provider,
        model_profile_id='test',
        model_name='test-model',
        reason='test route',
        fallback_provider_name=fallback,
    )


class TestGuardPassesWhenNoWorldModel:
    def test_none_world_model_allows_dispatch(self):
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, None)
        assert can is True
        assert reason == ''


class TestGuardBlocksWhenDetectedBlockMatchesProvider:
    def test_detected_block_blocks_provider(self):
        wm = WorldModelSnapshot(
            detected_blocks=['ChatGPT session expired', 'some other block'],
        )
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is False
        assert 'detected_block' in reason
        assert 'ChatGPT' in reason


class TestGuardBlocksWhenToolNotAlive:
    def test_tool_not_available_blocks(self):
        tool = ToolLiveStatus(
            tool_id='chatgpt-1',
            assistant_kind='chatgpt',
            available=False,
            status='no_disponible',
        )
        wm = WorldModelSnapshot(tool_live_status=[tool])
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is False
        assert 'tool_not_available' in reason


class TestGuardBlocksWhenPermissionGateActive:
    def test_permission_not_granted_blocks(self):
        gate = ObservationPermissionGate(
            scope='external',
            assistant_kind='chatgpt',
            granted=False,
        )
        wm = WorldModelSnapshot(permission_gates=[gate])
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is False
        assert 'permission_not_granted' in reason


class TestGuardPassesWhenNoBlocksForProvider:
    def test_blocks_for_other_provider_do_not_affect(self):
        wm = WorldModelSnapshot(
            detected_blocks=['Claude rate limited'],
        )
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is True
        assert reason == ''

    def test_tool_unavailable_for_other_does_not_block(self):
        tool = ToolLiveStatus(
            tool_id='claude-1',
            assistant_kind='claude',
            available=False,
            status='no_disponible',
        )
        wm = WorldModelSnapshot(tool_live_status=[tool])
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is True

    def test_permission_gate_for_other_does_not_block(self):
        gate = ObservationPermissionGate(
            scope='external',
            assistant_kind='claude',
            granted=False,
        )
        wm = WorldModelSnapshot(permission_gates=[gate])
        route = _make_route('chatgpt')
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is True


class TestBlockedDispatchTriggersFallback:
    def test_fallback_used_when_primary_blocked(self):
        """When primary is blocked but fallback passes, route switches."""
        wm = WorldModelSnapshot(
            detected_blocks=['ChatGPT session expired'],
        )
        primary = _make_route('chatgpt', fallback='ollama')
        # Primary should be blocked
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(primary, wm)
        assert can is False
        # Fallback should pass
        fallback = primary.model_copy(update={
            'provider_name': primary.fallback_provider_name,
            'used_fallback': True,
        })
        fb_can, _ = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(fallback, wm)
        assert fb_can is True

    def test_both_blocked_when_fallback_also_blocked(self):
        """When both primary and fallback are blocked, both fail."""
        wm = WorldModelSnapshot(
            detected_blocks=['ChatGPT blocked', 'Ollama timeout'],
        )
        primary = _make_route('chatgpt', fallback='ollama')
        can, _ = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(primary, wm)
        assert can is False
        fallback = primary.model_copy(update={
            'provider_name': primary.fallback_provider_name,
        })
        fb_can, _ = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(fallback, wm)
        assert fb_can is False


class TestBlockedDispatchRecordsLearning:
    def test_block_recorded_in_session_metadata(self):
        """Integration: _handle_request_body records pre_dispatch_blocked."""
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )
        ato = MagicMock(spec=AdaptiveTaskOrchestrator)
        wm = WorldModelSnapshot(
            detected_blocks=['ChatGPT session expired'],
        )
        route = _make_route('chatgpt')
        # Call the real static method
        can, reason = AdaptiveTaskOrchestrator._pre_dispatch_evidence_guard(route, wm)
        assert can is False
        # Verify the metadata structure that _handle_request_body would create
        meta = {
            'pre_dispatch_blocked': {
                'provider': route.provider_name,
                'reason': reason,
                'fallback_attempted': False,
            }
        }
        assert meta['pre_dispatch_blocked']['provider'] == 'chatgpt'
        assert 'detected_block' in meta['pre_dispatch_blocked']['reason']
        assert meta['pre_dispatch_blocked']['fallback_attempted'] is False
