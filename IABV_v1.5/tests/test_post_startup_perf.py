"""Tests for post-startup performance optimizations.

Verifies:
1. _refresh_development_packet is debounced with 30s cooldown
2. build_project_context caches results with 60s TTL
3. _ingest_chat_capabilities is debounced with 10s cooldown
4. User-triggered actions (force=True) bypass cooldowns
"""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# EngineeringReviewService.build_project_context TTL cache
# ---------------------------------------------------------------------------

class TestBuildProjectContextCache:
    """Verify that build_project_context uses a TTL cache."""

    def _make_service(self) -> SimpleNamespace:
        from iabv_v15.services.roles.engineering_review_service import (
            EngineeringReviewService,
        )
        svc = EngineeringReviewService(
            workspace_root='/tmp/test_workspace',
            episode_repository=MagicMock(list_recent=MagicMock(return_value=[])),
            knowledge_repository=MagicMock(list_recent=MagicMock(return_value=[])),
            run_repository=MagicMock(list_recent=MagicMock(return_value=[])),
            artifact_repository=MagicMock(list_recent=MagicMock(return_value=[])),
            analytics_service=MagicMock(build_report=MagicMock(return_value={})),
            teaching_gap_analyzer=MagicMock(analyze=MagicMock(return_value={})),
            pbt_service=MagicMock(load_state=MagicMock(return_value={})),
            development_assist_service=MagicMock(),
        )
        return svc

    def test_second_call_uses_cache(self):
        svc = self._make_service()
        ctx1 = svc.build_project_context()
        ctx2 = svc.build_project_context()
        assert ctx1 is ctx2
        # list_recent called only once per repo (first call)
        assert svc.episode_repository.list_recent.call_count == 1

    def test_force_bypasses_cache(self):
        svc = self._make_service()
        ctx1 = svc.build_project_context()
        ctx2 = svc.build_project_context(force=True)
        assert ctx2 is not ctx1
        assert svc.episode_repository.list_recent.call_count == 2

    def test_cache_expires_after_ttl(self):
        svc = self._make_service()
        svc._context_cache_ttl = 0.05  # 50ms for test speed
        ctx1 = svc.build_project_context()
        time.sleep(0.06)
        ctx2 = svc.build_project_context()
        assert ctx2 is not ctx1
        assert svc.episode_repository.list_recent.call_count == 2

    def test_cache_starts_empty(self):
        svc = self._make_service()
        assert svc._context_cache is None
        assert svc._context_cache_ts == 0.0


# ---------------------------------------------------------------------------
# _refresh_development_packet cooldown
# ---------------------------------------------------------------------------

class TestRefreshDevelopmentPacketCooldown:
    """Verify that _refresh_development_packet is debounced."""

    def _make_viewmodel(self) -> SimpleNamespace:
        """Build a minimal mock with the debounce fields."""
        vm = SimpleNamespace(
            _dev_packet_last_ts=0.0,
            _dev_packet_cooldown_s=30.0,
            _last_user_goal='test goal',
            _auto_route_enabled=True,
            _development_packet='',
            engineering_review_service=MagicMock(
                build_codex_packet=MagicMock(return_value='packet-text'),
            ),
        )
        # Bind the real method to our namespace
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        vm._refresh_development_packet = ControlCenterViewModel._refresh_development_packet.__get__(vm)
        vm._selected_role_title = lambda: 'Test'
        return vm

    def test_first_call_executes(self):
        vm = self._make_viewmodel()
        vm._refresh_development_packet()
        assert vm._development_packet == 'packet-text'
        assert vm.engineering_review_service.build_codex_packet.call_count == 1

    def test_second_call_within_cooldown_is_skipped(self):
        vm = self._make_viewmodel()
        vm._refresh_development_packet()
        vm._refresh_development_packet()
        assert vm.engineering_review_service.build_codex_packet.call_count == 1

    def test_force_bypasses_cooldown(self):
        vm = self._make_viewmodel()
        vm._refresh_development_packet()
        vm._refresh_development_packet(force=True)
        assert vm.engineering_review_service.build_codex_packet.call_count == 2

    def test_call_after_cooldown_executes(self):
        vm = self._make_viewmodel()
        vm._dev_packet_cooldown_s = 0.05
        vm._refresh_development_packet()
        time.sleep(0.06)
        vm._refresh_development_packet()
        assert vm.engineering_review_service.build_codex_packet.call_count == 2

    def test_user_goal_stored_even_when_skipped(self):
        vm = self._make_viewmodel()
        vm._refresh_development_packet('first goal')
        vm._refresh_development_packet('second goal')
        assert vm._last_user_goal == 'second goal'
        assert vm.engineering_review_service.build_codex_packet.call_count == 1


# ---------------------------------------------------------------------------
# _ingest_chat_capabilities cooldown
# ---------------------------------------------------------------------------

class TestIngestChatCapabilitiesCooldown:
    """Verify that _ingest_chat_capabilities is debounced."""

    def _make_viewmodel(self) -> SimpleNamespace:
        vm = SimpleNamespace(
            _capability_ingest_last_ts=0.0,
            _capability_ingest_cooldown_s=10.0,
            chat_capability_ingestion_service=MagicMock(
                ingest=MagicMock(return_value=[]),
            ),
            _chat_session_id='test-session',
            _pending_capability_notice=[],
        )
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        vm._ingest_chat_capabilities = ControlCenterViewModel._ingest_chat_capabilities.__get__(vm)
        vm._format_capability_notice = lambda notices: ''
        vm._append_message = lambda *a, **kw: None
        return vm

    def test_first_call_executes(self):
        vm = self._make_viewmodel()
        vm._ingest_chat_capabilities('hello')
        assert vm.chat_capability_ingestion_service.ingest.call_count == 1

    def test_second_call_within_cooldown_is_skipped(self):
        vm = self._make_viewmodel()
        vm._ingest_chat_capabilities('hello')
        vm._ingest_chat_capabilities('world')
        assert vm.chat_capability_ingestion_service.ingest.call_count == 1

    def test_call_after_cooldown_executes(self):
        vm = self._make_viewmodel()
        vm._capability_ingest_cooldown_s = 0.05
        vm._ingest_chat_capabilities('hello')
        time.sleep(0.06)
        vm._ingest_chat_capabilities('world')
        assert vm.chat_capability_ingestion_service.ingest.call_count == 2

    def test_no_service_is_noop(self):
        vm = self._make_viewmodel()
        vm.chat_capability_ingestion_service = None
        result = vm._ingest_chat_capabilities('hello')
        assert result == []
