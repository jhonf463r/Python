"""Tests for Brecha 2.2 — Governed quota rotation in AdaptiveModelSelector.

Validates:
1. Provider with exhausted quota gets zero score
2. Fallback to alternative account for same tool
3. Fallback chain: web → API → local
4. Provider with more quota preferred over one with less
5. Selector works without quota data (backward compat)
6. Low quota warning logged when remaining < threshold
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from iabv_v15.services.adaptive.adaptive_model_selector import (
    AdaptiveModelSelector,
    ProviderScore,
    _LOW_QUOTA_THRESHOLD,
)


def _make_selector(tmp_path) -> AdaptiveModelSelector:
    """Build a selector with an isolated data dir."""
    return AdaptiveModelSelector(data_dir=str(tmp_path / 'data'))


def _make_gate(assistant_kind: str, granted: bool) -> SimpleNamespace:
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
    pool = {'tools': tools} if tools is not None else {}
    return SimpleNamespace(
        permission_gates=gates or [],
        worker_pool_snapshot=pool,
    )


_CLEAN_ENV = {
    'GEMINI_API_KEY': 'test-key',
    'GROQ_API_KEY': 'test-key',
    'OPENROUTER_API_KEY': 'test-key',
    'TOGETHER_API_KEY': 'test-key',
}


# ---------------------------------------------------------------
# 1. Provider with exhausted quota gets zero score
# ---------------------------------------------------------------
class TestExhaustedQuotaZeroScore:
    def test_provider_with_exhausted_quota_gets_zero_score(self, tmp_path):
        """When worker_pool_snapshot shows usable=False for a tool,
        the provider gets score=0.0 and available=False."""
        wm = _make_world_model(tools={
            'gemini': {
                'available_accounts': 0,
                'exhausted_accounts': 2,
                'total_accounts': 2,
                'usable': False,
                'top_worker': None,
            },
        })
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        gemini = next(s for s in scores if s.provider_id == 'gemini')
        assert gemini.available is False
        assert gemini.total_score == 0.0
        assert gemini.reason == 'quota_exhausted'


# ---------------------------------------------------------------
# 2. Fallback to alternative account for same tool
# ---------------------------------------------------------------
class TestFallbackAlternativeAccount:
    def test_fallback_to_alternative_account_same_tool(self, tmp_path):
        """When account A is exhausted but account B has quota,
        best_account_for_tool returns account B."""
        wm = _make_world_model(
            gates=[_make_gate('chatgpt', True)],
            tools={
                'chatgpt': {
                    'available_accounts': 1,
                    'exhausted_accounts': 1,
                    'total_accounts': 2,
                    'usable': True,
                    'top_worker': {'email': 'accountB@test.com', 'score': 15},
                },
            },
        )
        sel = _make_selector(tmp_path)
        account = sel._best_account_for_tool('chatgpt_web', wm)
        assert account is not None
        assert account['email'] == 'accountB@test.com'
        assert account['remaining'] == 15


# ---------------------------------------------------------------
# 3. Fallback chain: web → API → local
# ---------------------------------------------------------------
class TestFallbackChainWebApiLocal:
    def test_fallback_chain_web_to_api_to_local(self, tmp_path):
        """When web providers are exhausted, falls to API; when API
        also exhausted, falls to local."""
        wm = _make_world_model(
            gates=[_make_gate('chatgpt', True)],
            tools={
                'chatgpt': {'usable': False, 'top_worker': None},
                'gemini': {'usable': False, 'top_worker': None},
                'groq': {'usable': False, 'top_worker': None},
                'openrouter': {'usable': False, 'top_worker': None},
                'together': {'usable': False, 'top_worker': None},
            },
        )
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            result = sel.select_best_provider(
                task_type='general',
                world_model=wm,
            )
        assert result['provider_id'] == 'ollama_local'
        # All cloud/web providers exhausted → only local remains in fallback
        assert result['fallback_chain'] == ['ollama_local']


# ---------------------------------------------------------------
# 4. Provider with more quota preferred
# ---------------------------------------------------------------
class TestQuotaAvailablePreferred:
    def test_quota_available_provider_preferred(self, tmp_path):
        """Between two providers, the one with more remaining quota
        gets a higher score (via quota penalty on the low one)."""
        wm = _make_world_model(tools={
            'gemini': {
                'usable': True,
                'top_worker': {'email': 'a@test.com', 'score': 50},
                'available_accounts': 1,
            },
            'groq': {
                'usable': True,
                'top_worker': {'email': 'b@test.com', 'score': 2},
                'available_accounts': 1,
            },
        })
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            scores = sel._score_all_providers('general', set(), world_model=wm)
        gemini = next(s for s in scores if s.provider_id == 'gemini')
        groq = next(s for s in scores if s.provider_id == 'groq')
        assert gemini.total_score > groq.total_score, (
            f'gemini ({gemini.total_score}) should beat groq ({groq.total_score}) '
            f'because gemini has more remaining quota'
        )


# ---------------------------------------------------------------
# 5. Selector works without quota data (backward compat)
# ---------------------------------------------------------------
class TestSelectorWithoutQuotaData:
    def test_selector_works_without_quota_data(self, tmp_path):
        """Without worker_pool_snapshot, the selector still works
        and returns a valid provider (backward compatibility)."""
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            result = sel.select_best_provider(
                task_type='general',
                world_model=None,
            )
        assert 'provider_id' in result
        assert result['provider_id'] != ''
        assert 'fallback_chain' in result
        assert len(result['fallback_chain']) > 0


# ---------------------------------------------------------------
# 6. Low quota warning logged
# ---------------------------------------------------------------
class TestLowQuotaWarning:
    def test_low_quota_warning_logged(self, tmp_path, caplog):
        """When a provider's remaining quota is below threshold,
        a WARNING is emitted."""
        wm = _make_world_model(tools={
            'gemini': {
                'usable': True,
                'top_worker': {'email': 'low@test.com', 'score': 3},
                'available_accounts': 1,
            },
        })
        sel = _make_selector(tmp_path)
        with patch.dict(os.environ, _CLEAN_ENV):
            with caplog.at_level(logging.WARNING, logger='iabv_v15.services.adaptive.adaptive_model_selector'):
                sel.select_best_provider(
                    task_type='general',
                    world_model=wm,
                )
        low_quota_warnings = [
            r for r in caplog.records
            if 'messages remaining' in r.message and 'gemini' in r.message
        ]
        assert len(low_quota_warnings) >= 1, (
            f'Expected WARNING about low quota for gemini, got: {[r.message for r in caplog.records]}'
        )
