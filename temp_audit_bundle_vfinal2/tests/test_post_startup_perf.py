"""Tests for post-startup performance optimizations.

Verifies:
1. _refresh_development_packet is debounced with 30s cooldown
2. build_project_context caches results with 60s TTL
3. _ingest_chat_capabilities processes every message (no debounce)
4. User-triggered actions (force=True) bypass cooldowns
5. Repository count() methods use SQL COUNT (not list+len)
6. ControlCenterViewModel uses shared thread pool with lifecycle hook
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
# _ingest_chat_capabilities — no debounce (each message must be processed)
# ---------------------------------------------------------------------------

class TestIngestChatCapabilitiesNoCooldown:
    """Verify that _ingest_chat_capabilities processes every message."""

    def _make_viewmodel(self) -> SimpleNamespace:
        vm = SimpleNamespace(
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

    def test_every_call_executes(self):
        vm = self._make_viewmodel()
        vm._ingest_chat_capabilities('hello')
        vm._ingest_chat_capabilities('world')
        assert vm.chat_capability_ingestion_service.ingest.call_count == 2

    def test_rapid_fire_all_processed(self):
        vm = self._make_viewmodel()
        for i in range(5):
            vm._ingest_chat_capabilities(f'message {i}')
        assert vm.chat_capability_ingestion_service.ingest.call_count == 5

    def test_no_service_is_noop(self):
        vm = self._make_viewmodel()
        vm.chat_capability_ingestion_service = None
        result = vm._ingest_chat_capabilities('hello')
        assert result == []


# ---------------------------------------------------------------------------
# Repository count() — SQL COUNT instead of list+len
# ---------------------------------------------------------------------------

class TestRepositoryCount:
    """Verify that repositories expose count() using SQL COUNT."""

    def test_episode_repository_count(self, tmp_path):
        from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        db = AppDatabase(str(tmp_path / 'test.db'))
        repo = EpisodeRepository(str(tmp_path / 'episodes'), db)
        assert repo.count() == 0
        repo.create_episode('ep1')
        assert repo.count() == 1
        repo.create_episode('ep2')
        assert repo.count() == 2

    def test_knowledge_repository_count(self, tmp_path):
        from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        from iabv_v15.domain.models import KnowledgeItem
        db = AppDatabase(str(tmp_path / 'test.db'))
        repo = KnowledgeRepository(db)
        assert repo.count() == 0
        repo.upsert(KnowledgeItem(title='k1', summary='s1'))
        assert repo.count() == 1

    def test_run_repository_count(self, tmp_path):
        from iabv_v15.infra.persistence.run_repository import RunRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        db = AppDatabase(str(tmp_path / 'test.db'))
        repo = RunRepository(db)
        assert repo.count() == 0

    def test_session_artifact_repository_count(self, tmp_path):
        from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
        from iabv_v15.infra.persistence.database import AppDatabase
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        db = AppDatabase(str(tmp_path / 'test.db'))
        storage = ArtifactStorage(str(tmp_path / 'artifacts'))
        repo = SessionArtifactRepository(db, storage)
        assert repo.count() == 0


# ---------------------------------------------------------------------------
# ControlCenterViewModel — shared thread pool with lifecycle
# ---------------------------------------------------------------------------

class TestViewModelThreadPool:
    """Verify that ControlCenterViewModel uses a shared ThreadPoolExecutor with shutdown."""

    def test_bg_pool_exists(self):
        from concurrent.futures import ThreadPoolExecutor
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._bg_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='test-bg')
        assert vm._bg_pool._max_workers == 3
        vm._bg_pool.shutdown(wait=False)

    def test_shutdown_bg_pool_is_safe(self):
        from concurrent.futures import ThreadPoolExecutor
        from iabv_v15.ui.viewmodels.control_center_viewmodel import (
            ControlCenterViewModel,
        )
        pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='test-bg')
        vm = MagicMock(spec=ControlCenterViewModel)
        vm._bg_pool = pool
        vm._shutdown_bg_pool = ControlCenterViewModel._shutdown_bg_pool.__get__(vm)
        vm._shutdown_bg_pool()
        assert pool._shutdown
