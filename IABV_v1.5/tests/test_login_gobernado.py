"""Tests for Brecha 2.3 — Governed login flow for free web accounts.

Validates:
1. _SECRET_PROVIDERS includes CHATGPT_WEB, CLAUDE_WEB, GEMINI_WEB
2. check_web_session_health returns 'active' for valid cookie
3. check_web_session_health returns 'expired' for expired cookie
4. check_web_session_health returns 'expired' when no cookie file
5. OSES emits web_session_expired finding for expired sessions
6. AdaptiveModelSelector penalizes providers with expired web session
7. record_web_session_refresh persists and updates state
8. Without web accounts configured, existing flows work unchanged
"""
from __future__ import annotations

import json
import os
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from iabv_v15.services.auto_correction_engine import (
    _SECRET_PROVIDERS,
    check_web_session_health,
)
from iabv_v15.services.account_resource_scanner import (
    get_web_session_status,
    record_web_session_refresh,
)
from iabv_v15.services.adaptive.adaptive_model_selector import (
    AdaptiveModelSelector,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_selector(tmp_path) -> AdaptiveModelSelector:
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
    gates: list[SimpleNamespace] | None = None,
    tools: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        permission_gates=gates or [],
        worker_pool_snapshot={'tools': tools or {}},
    )


# ──────────────────────────────────────────────────────────────
# Test 1: _SECRET_PROVIDERS includes web accounts
# ──────────────────────────────────────────────────────────────

def test_secret_providers_include_web_accounts():
    for key in ('CHATGPT_WEB', 'CLAUDE_WEB', 'GEMINI_WEB'):
        assert key in _SECRET_PROVIDERS, f'{key} not in _SECRET_PROVIDERS'
        url, description, auto_openable = _SECRET_PROVIDERS[key]
        assert url, f'{key} has empty URL'
        assert 'cookie' in description.lower() or 'session' in description.lower(), (
            f'{key} description should mention cookie/session'
        )
        assert auto_openable is True


# ──────────────────────────────────────────────────────────────
# Test 2: Session health — active cookie
# ──────────────────────────────────────────────────────────────

def test_session_health_active(tmp_path):
    cookie_file = tmp_path / 'cookies.json'
    future_ts = time.time() + 86400  # 24h from now
    cookie_file.write_text(json.dumps([
        {'domain': '.openai.com', 'name': 'session', 'expirationDate': future_ts},
    ]))

    result = check_web_session_health('chatgpt_web', cookie_path=str(cookie_file))

    assert result['provider'] == 'chatgpt_web'
    assert result['status'] == 'active'
    assert result['needs_human'] is False
    assert result['expires_hint'] is not None


# ──────────────────────────────────────────────────────────────
# Test 3: Session health — expired cookie
# ──────────────────────────────────────────────────────────────

def test_session_health_expired(tmp_path):
    cookie_file = tmp_path / 'cookies.json'
    past_ts = time.time() - 86400  # 24h ago
    cookie_file.write_text(json.dumps([
        {'domain': '.openai.com', 'name': 'session', 'expirationDate': past_ts},
    ]))

    result = check_web_session_health('chatgpt_web', cookie_path=str(cookie_file))

    assert result['provider'] == 'chatgpt_web'
    assert result['status'] == 'expired'
    assert result['needs_human'] is True
    assert 'expired' in result['reason'].lower()


# ──────────────────────────────────────────────────────────────
# Test 4: Session health — missing cookie file
# ──────────────────────────────────────────────────────────────

def test_session_health_missing(tmp_path):
    result = check_web_session_health(
        'claude_web',
        cookie_path=str(tmp_path / 'nonexistent.json'),
    )

    assert result['provider'] == 'claude_web'
    assert result['status'] == 'expired'
    assert result['needs_human'] is True
    assert 'not found' in result['reason'].lower()


# ──────────────────────────────────────────────────────────────
# Test 5: Expired session triggers OSES finding
# ──────────────────────────────────────────────────────────────

def test_expired_session_triggers_finding():
    """OSES._web_session_findings emits web_session_expired when session is dead."""
    from iabv_v15.services.evolution.operational_self_examination_service import (
        OperationalSelfExaminationService,
    )

    oses = OperationalSelfExaminationService.__new__(
        OperationalSelfExaminationService,
    )

    expired_health = {
        'provider': 'chatgpt_web',
        'status': 'expired',
        'expires_hint': None,
        'needs_human': True,
        'reason': 'No active browser session found',
    }

    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        return_value=expired_health,
    ):
        findings = oses._web_session_findings()

    expired_findings = [f for f in findings if f.category == 'web_session_expired']
    assert len(expired_findings) >= 1, 'Expected at least one web_session_expired finding'
    finding = expired_findings[0]
    assert finding.metadata['needs_human'] is True
    assert finding.severity in ('medium', 'high', 'critical')


# ──────────────────────────────────────────────────────────────
# Test 6: Selector penalizes expired web session
# ──────────────────────────────────────────────────────────────

def test_selector_penalizes_expired_web_session(tmp_path):
    selector = _make_selector(tmp_path)

    world = _make_world_model(
        gates=[
            _make_gate('chatgpt', True),
            _make_gate('claude', True),
            _make_gate('gemini', True),
        ],
        tools={
            'chatgpt': {'usable': True, 'available_accounts': 1},
            'claude': {'usable': True, 'available_accounts': 1},
            'gemini': {'usable': True, 'available_accounts': 1},
        },
    )

    expired_health = {
        'provider': 'chatgpt_web',
        'status': 'expired',
        'expires_hint': None,
        'needs_human': True,
        'reason': 'No active browser session found',
    }

    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        return_value=expired_health,
    ):
        result = selector.select_best_provider(
            task_type='general',
            world_model=world,
        )

    # chatgpt_web should NOT be selected (session expired)
    assert result['provider_id'] != 'chatgpt_web', (
        'Selector should not pick chatgpt_web with expired session'
    )
    # Check that chatgpt_web has zero score
    chatgpt_scores = [
        s for s in result['scores']
        if s['provider_id'] == 'chatgpt_web'
    ]
    assert chatgpt_scores, 'chatgpt_web should still appear in scores'
    assert chatgpt_scores[0]['total_score'] == 0.0
    assert chatgpt_scores[0]['reason'] == 'web_session_expired'


# ──────────────────────────────────────────────────────────────
# Test 7: record_web_session_refresh persists state
# ──────────────────────────────────────────────────────────────

def test_session_refresh_recorded(tmp_path):
    state_file = tmp_path / 'evolution' / 'web_sessions' / 'session_state.json'

    with patch(
        'iabv_v15.services.account_resource_scanner._web_session_state_path',
        return_value=state_file,
    ):
        record_web_session_refresh('chatgpt_web', 'user@example.com')

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        entry = data['sessions']['chatgpt_web']
        assert entry['account_email'] == 'user@example.com'
        assert entry['refresh_count'] == 1
        assert 'last_refresh_utc' in entry

        # Second refresh increments count
        record_web_session_refresh('chatgpt_web', 'user@example.com')
        data = json.loads(state_file.read_text())
        assert data['sessions']['chatgpt_web']['refresh_count'] == 2


# ──────────────────────────────────────────────────────────────
# Test 8: Backward compatibility — no web accounts, everything works
# ──────────────────────────────────────────────────────────────

def test_backward_compatible(tmp_path):
    """Without web accounts configured, selector and quota work as before."""
    selector = _make_selector(tmp_path)

    # No gates, no sessions — web providers should be unavailable
    world = _make_world_model(gates=[], tools={})

    # Set at least one API key so there's a selectable provider
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key-123'}):
        result = selector.select_best_provider(
            task_type='general',
            world_model=world,
        )

    # Web providers should NOT be selected (no permission gate)
    assert result['provider_id'] not in ('chatgpt_web', 'claude_web', 'gemini_web')

    # The selection should still work (gemini or ollama_local)
    assert result['provider_id'] in ('gemini', 'groq', 'openrouter', 'together', 'ollama_local')
    assert 'scores' in result
    assert 'fallback_chain' in result


# ──────────────────────────────────────────────────────────────
# Test 6b: Unknown or unavailable session health must fail closed
# ──────────────────────────────────────────────────────────────

def _web_provider_world():
    return _make_world_model(
        gates=[
            _make_gate('chatgpt', True),
            _make_gate('claude', True),
            _make_gate('gemini', True),
        ],
        tools={
            'chatgpt': {'usable': True, 'available_accounts': 1},
            'claude': {'usable': True, 'available_accounts': 1},
            'gemini': {'usable': True, 'available_accounts': 1},
        },
    )


def _assert_web_providers_are_ineligible(result, expected_reason: str) -> None:
    web_scores = [
        score for score in result['scores']
        if score['provider_id'].endswith('_web')
    ]
    assert len(web_scores) == 3
    for score in web_scores:
        assert score['total_score'] == 0.0
        assert score['reason'] == expected_reason
    assert not result['provider_id'].endswith('_web')


def test_selector_fails_closed_when_web_session_health_is_unknown(tmp_path):
    selector = _make_selector(tmp_path)
    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        return_value={
            'status': 'unknown',
            'needs_human': False,
            'reason': 'Browser scan unavailable',
        },
    ):
        result = selector.select_best_provider(
            task_type='general',
            world_model=_web_provider_world(),
        )

    _assert_web_providers_are_ineligible(result, 'web_session_unknown')


def test_selector_fails_closed_when_web_session_health_raises(tmp_path):
    selector = _make_selector(tmp_path)
    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        side_effect=RuntimeError('scanner unavailable'),
    ):
        result = selector.select_best_provider(
            task_type='general',
            world_model=_web_provider_world(),
        )

    _assert_web_providers_are_ineligible(result, 'session_check_unavailable')


def test_selector_rejects_malformed_web_session_health(tmp_path):
    selector = _make_selector(tmp_path)
    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        return_value=None,
    ):
        result = selector.select_best_provider(
            task_type='general',
            world_model=_web_provider_world(),
        )

    _assert_web_providers_are_ineligible(result, 'web_session_health_invalid')


def test_selector_allows_web_provider_only_when_session_is_active(tmp_path):
    selector = _make_selector(tmp_path)
    with patch(
        'iabv_v15.services.auto_correction_engine.check_web_session_health',
        return_value={'status': 'active'},
    ):
        allowed, reason = selector._is_web_session_active('chatgpt_web')

    assert allowed is True
    assert reason == 'web_session_active'
