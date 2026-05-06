"""Tests for Fase 6 — Unified Cloud/Local/Web selector.

Validates that:
- Web providers are formal candidates in the selector
- Permission gates and quota from WorldModelSnapshot control availability
- Priority ordering: API > web > local
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from iabv_v15.services.adaptive.adaptive_model_selector import (
    AdaptiveModelSelector,
    ProviderScore,
)


def _make_selector(tmp_path) -> AdaptiveModelSelector:
    """Build a selector with an isolated data dir."""
    return AdaptiveModelSelector(data_dir=str(tmp_path / 'data'))


def _make_gate(assistant_kind: str, granted: bool) -> SimpleNamespace:
    """Build a minimal permission gate object."""
    return SimpleNamespace(
        scope='observation',
        assistant_kind=assistant_kind,
        granted=granted,
        status='active',
    )


def _make_world_model(
    *,
    gates: list | None = None,
    tools: dict | None = None,
) -> SimpleNamespace:
    """Build a minimal WorldModelSnapshot-like object."""
    pool = {'tools': tools} if tools is not None else {}
    return SimpleNamespace(
        permission_gates=gates or [],
        worker_pool_snapshot=pool,
    )


# Patch env so no real API keys interfere with scoring
_CLEAN_ENV = {
    'GEMINI_API_KEY': 'test-key',
    'GROQ_API_KEY': 'test-key',
    'OPENROUTER_API_KEY': 'test-key',
    'TOGETHER_API_KEY': 'test-key',
}


# ---------------------------------------------------------------
# 1. Web providers in list
# ---------------------------------------------------------------
class TestWebProvidersInList:
    def test_web_providers_in_provider_list(self, tmp_path):
        """chatgpt_web, claude_web, gemini_web are in the provider list."""
        sel = _make_selector(tmp_path)
        wm = _make_world_model(gates=[
            _make_gate('chatgpt', True),
            _make_gate('claude', True),
            _make_gate('gemini', True),
        ])
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        provider_ids = [s.provider_id for s in scores]
        assert 'chatgpt_web' in provider_ids
        assert 'claude_web' in provider_ids
        assert 'gemini_web' in provider_ids


# ---------------------------------------------------------------
# 2. Web excluded without world model
# ---------------------------------------------------------------
class TestWebExcludedWithoutWorldModel:
    def test_web_excluded_without_world_model(self, tmp_path):
        """Without WorldModel, web providers have available=False."""
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=None)
        web_scores = [s for s in scores if s.provider_id.endswith('_web')]
        assert len(web_scores) == 3
        for ws in web_scores:
            assert ws.available is False
            assert ws.reason == 'no_world_model'


# ---------------------------------------------------------------
# 3. Web excluded without permission
# ---------------------------------------------------------------
class TestWebExcludedWithoutPermission:
    def test_web_excluded_without_permission(self, tmp_path):
        """With WorldModel but no granted gate, web providers are excluded."""
        wm = _make_world_model(gates=[
            _make_gate('chatgpt', False),
            _make_gate('claude', False),
        ])
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        chatgpt = next(s for s in scores if s.provider_id == 'chatgpt_web')
        claude = next(s for s in scores if s.provider_id == 'claude_web')
        gemini_w = next(s for s in scores if s.provider_id == 'gemini_web')
        assert chatgpt.available is False
        assert chatgpt.reason == 'permission_not_granted'
        assert claude.available is False
        assert claude.reason == 'permission_not_granted'
        assert gemini_w.available is False
        assert gemini_w.reason == 'no_permission_gate'


# ---------------------------------------------------------------
# 4. Web included with permission
# ---------------------------------------------------------------
class TestWebIncludedWithPermission:
    def test_web_included_with_permission(self, tmp_path):
        """With gate granted=True, web provider has available=True."""
        wm = _make_world_model(gates=[_make_gate('chatgpt', True)])
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        chatgpt = next(s for s in scores if s.provider_id == 'chatgpt_web')
        assert chatgpt.available is True
        assert chatgpt.total_score > 0


# ---------------------------------------------------------------
# 5. Quota exhausted excludes provider
# ---------------------------------------------------------------
class TestQuotaExhaustedExcludes:
    def test_quota_exhausted_excludes_provider(self, tmp_path):
        """If worker_pool_snapshot shows usable=False, provider excluded."""
        wm = _make_world_model(tools={'gemini': {'usable': False}})
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        gemini = next(s for s in scores if s.provider_id == 'gemini')
        assert gemini.available is False
        assert gemini.reason == 'quota_exhausted'


# ---------------------------------------------------------------
# 6. Quota available allows provider
# ---------------------------------------------------------------
class TestQuotaAvailableAllows:
    def test_quota_available_allows_provider(self, tmp_path):
        """If usable=True, provider is not excluded by quota check."""
        wm = _make_world_model(tools={'gemini': {'usable': True}})
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        gemini = next(s for s in scores if s.provider_id == 'gemini')
        assert gemini.available is True
        assert gemini.total_score > 0


# ---------------------------------------------------------------
# 7. Priority: API > web > local
# ---------------------------------------------------------------
class TestPriorityApiOverWebOverLocal:
    def test_priority_api_over_web_over_local(self, tmp_path):
        """API cloud_bonus=0.15 > web cloud_bonus=0.05 > local=0.0."""
        wm = _make_world_model(gates=[_make_gate('chatgpt', True)])
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)

        api_score = next(s for s in scores if s.provider_id == 'gemini')
        web_score = next(s for s in scores if s.provider_id == 'chatgpt_web')
        local_score = next(s for s in scores if s.provider_id == 'ollama_local')

        assert api_score.total_score > web_score.total_score, (
            f'API ({api_score.total_score}) should beat web ({web_score.total_score})'
        )
        assert web_score.total_score > local_score.total_score, (
            f'web ({web_score.total_score}) should beat local ({local_score.total_score})'
        )


# ---------------------------------------------------------------
# 8. All API exhausted → falls to web
# ---------------------------------------------------------------
class TestAllApiExhaustedFallsToWeb:
    def test_all_api_exhausted_falls_to_web(self, tmp_path):
        """If all API providers are excluded, web with permission is selected."""
        wm = _make_world_model(gates=[_make_gate('chatgpt', True)])
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            result = sel.select_best_provider(
                task_type='general',
                exclude=['gemini', 'groq', 'openrouter', 'together'],
                world_model=wm,
            )
        assert result['provider_id'] == 'chatgpt_web'


# ---------------------------------------------------------------
# 9. All exhausted → falls to local
# ---------------------------------------------------------------
class TestAllExhaustedFallsToLocal:
    def test_all_exhausted_falls_to_local(self, tmp_path):
        """If everything is exhausted, falls to ollama_local."""
        wm = _make_world_model()  # no gates → web excluded
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            result = sel.select_best_provider(
                task_type='general',
                exclude=['gemini', 'groq', 'openrouter', 'together'],
                world_model=wm,
            )
        assert result['provider_id'] == 'ollama_local'
