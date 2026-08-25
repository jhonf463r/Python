"""Tests for per-worker block-risk granularity.

Covers:
- _resolve_worker_signals: email:tool, browser:profile:tool, tool fallback
- per-worker signal only penalises the targeted worker
- other workers of the same tool remain unpenalised
- backward compatibility: tool-only signals still penalise all workers
- rank_workers_for_target reorders with per-worker risk
- top_worker_for_target respects per-worker risk
"""
from __future__ import annotations

from iabv_v15.services.account_resource_scanner import (
    _compute_block_risk,
    _resolve_worker_signals,
    _score_worker,
    _BLOCK_SIGNAL_WEIGHTS,
    _MAX_BLOCK_RISK,
    rank_workers_for_target,
    top_worker_for_target,
)


def _worker(
    tool: str = 'chatgpt',
    email: str = 'a@test.com',
    remaining: int = 40,
    limit: int = 40,
    exhausted: bool = False,
    browser: str = 'Chrome',
    profile: str = 'Default',
) -> dict:
    return {
        'tool': tool,
        'email': email,
        'remaining_messages': remaining,
        'limit': limit,
        'exhausted': exhausted,
        'browser': browser,
        'profile': profile,
    }


def _pool(workers: list[dict]) -> dict:
    return {
        'workers': workers,
        'exhausted': [],
        'available_count': len(workers),
        'exhausted_count': 0,
        'by_tool': {},
        'total_remaining_messages': sum(w['remaining_messages'] for w in workers),
    }


# ─── _resolve_worker_signals ────────────────────────────────


def test_resolve_email_tool_key() -> None:
    """email:tool key is the most specific and wins over tool fallback."""
    w = _worker(email='risky@t.com', tool='chatgpt')
    signals = {
        'risky@t.com:chatgpt': ['wrong_thread'],
        'chatgpt': ['auth_expired'],
    }
    resolved = _resolve_worker_signals(w, signals)
    assert resolved == ['wrong_thread']


def test_resolve_browser_profile_tool_key() -> None:
    """browser:profile:tool wins when email:tool is absent."""
    w = _worker(tool='chatgpt', browser='Chrome', profile='Profile 2')
    signals = {
        'chrome:profile 2:chatgpt': ['capture_unverified'],
        'chatgpt': ['auth_expired'],
    }
    resolved = _resolve_worker_signals(w, signals)
    assert resolved == ['capture_unverified']


def test_resolve_fallback_to_tool() -> None:
    """If no specific key matches, fall back to tool key."""
    w = _worker(email='other@t.com', tool='chatgpt')
    signals = {
        'risky@t.com:chatgpt': ['wrong_thread'],
        'chatgpt': ['awaiting_response'],
    }
    resolved = _resolve_worker_signals(w, signals)
    assert resolved == ['awaiting_response']


def test_resolve_no_match_returns_empty() -> None:
    w = _worker(tool='chatgpt')
    signals = {'codex': ['wrong_thread']}
    assert _resolve_worker_signals(w, signals) == []


def test_resolve_case_insensitive() -> None:
    w = _worker(email='User@T.com', tool='ChatGPT')
    signals = {'user@t.com:chatgpt': ['rate_limited']}
    resolved = _resolve_worker_signals(w, signals)
    assert resolved == ['rate_limited']


def test_resolve_email_tool_beats_browser_profile_tool() -> None:
    """email:tool is higher priority than browser:profile:tool."""
    w = _worker(email='a@t.com', tool='chatgpt', browser='Chrome', profile='Default')
    signals = {
        'a@t.com:chatgpt': ['wrong_thread'],
        'chrome:default:chatgpt': ['auth_expired'],
    }
    resolved = _resolve_worker_signals(w, signals)
    assert resolved == ['wrong_thread']


# ─── per-worker block_risk isolation ─────────────────────────


def test_per_worker_risk_does_not_degrade_others() -> None:
    """Signal keyed to one email:tool must NOT penalise a different email."""
    risky = _worker(email='risky@t.com', tool='chatgpt')
    clean = _worker(email='clean@t.com', tool='chatgpt')

    signals = {'risky@t.com:chatgpt': ['wrong_thread']}

    assert _compute_block_risk(risky, signals) > 0
    assert _compute_block_risk(clean, signals) == 0.0


def test_per_browser_profile_risk_isolates() -> None:
    """Signal keyed to browser:profile:tool only hits that profile."""
    risky = _worker(tool='chatgpt', browser='Chrome', profile='Profile 2')
    clean = _worker(tool='chatgpt', browser='Chrome', profile='Default')

    signals = {'chrome:profile 2:chatgpt': ['capture_unverified']}

    assert _compute_block_risk(risky, signals) > 0
    assert _compute_block_risk(clean, signals) == 0.0


def test_tool_level_signal_still_penalises_all() -> None:
    """Backward compat: tool-only key penalises every worker of that tool."""
    w1 = _worker(email='a@t.com', tool='chatgpt')
    w2 = _worker(email='b@t.com', tool='chatgpt')
    signals = {'chatgpt': ['awaiting_response']}

    r1 = _compute_block_risk(w1, signals)
    r2 = _compute_block_risk(w2, signals)
    assert r1 > 0
    assert r1 == r2


# ─── _score_worker with per-worker signals ───────────────────


def test_score_per_worker_signal_penalises_only_target() -> None:
    risky = _worker(email='risky@t.com', tool='chatgpt', remaining=40, limit=40)
    clean = _worker(email='clean@t.com', tool='chatgpt', remaining=40, limit=40)

    signals = {'risky@t.com:chatgpt': ['wrong_thread']}

    score_risky = _score_worker(risky, block_signals=signals)
    score_clean = _score_worker(clean, block_signals=signals)

    assert score_risky < score_clean
    assert score_clean == 1.0
    expected = round(1.0 * (1.0 - _BLOCK_SIGNAL_WEIGHTS['wrong_thread']), 4)
    assert score_risky == expected


# ─── rank_workers_for_target per-worker ──────────────────────


def test_rank_same_quota_per_worker_risk_reorders() -> None:
    """Same tool, same quota; per-worker signal changes order."""
    pool = _pool([
        _worker(tool='chatgpt', email='risky@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='clean@t.com', remaining=40, limit=40),
    ])
    signals = {'risky@t.com:chatgpt': ['awaiting_response']}
    ranked = rank_workers_for_target('chatgpt', pool=pool, block_signals=signals)

    assert len(ranked) == 2
    assert ranked[0]['email'] == 'clean@t.com'
    assert ranked[0]['block_risk'] == 0.0
    assert ranked[1]['email'] == 'risky@t.com'
    assert ranked[1]['block_risk'] > 0


def test_rank_per_worker_risk_does_not_degrade_all() -> None:
    """Three workers, only one signalled; the other two keep full score."""
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='b@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='risky@t.com', remaining=40, limit=40),
    ])
    signals = {'risky@t.com:chatgpt': ['auth_expired']}
    ranked = rank_workers_for_target('chatgpt', pool=pool, block_signals=signals)

    assert len(ranked) == 3
    # The two clean workers should have score 1.0
    assert ranked[0]['score'] == 1.0
    assert ranked[1]['score'] == 1.0
    # The risky one is last
    assert ranked[2]['email'] == 'risky@t.com'
    assert ranked[2]['block_risk'] >= 0.9


def test_rank_tool_fallback_backward_compatible() -> None:
    """Tool-only signals still penalise all workers of that tool."""
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='b@t.com', remaining=40, limit=40),
    ])
    signals = {'chatgpt': ['awaiting_response']}
    ranked = rank_workers_for_target('chatgpt', pool=pool, block_signals=signals)

    assert len(ranked) == 2
    assert ranked[0]['score'] == ranked[1]['score']
    assert ranked[0]['block_risk'] > 0


def test_rank_no_signals_backward_compatible() -> None:
    """Omitting block_signals is identical to pre-change behaviour."""
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=30, limit=40),
        _worker(tool='chatgpt', email='b@t.com', remaining=10, limit=40),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert ranked[0]['email'] == 'a@t.com'
    assert ranked[0]['score'] == round(30 / 40, 4)
    assert ranked[1]['score'] == round(10 / 40, 4)


# ─── top_worker_for_target per-worker ────────────────────────


def test_top_worker_respects_per_worker_signal() -> None:
    """Per-worker signal demotes the risky worker; clean one wins."""
    pool = _pool([
        _worker(tool='chatgpt', email='risky@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='clean@t.com', remaining=40, limit=40),
    ])
    signals = {'risky@t.com:chatgpt': ['auth_expired']}
    top = top_worker_for_target('chatgpt', pool=pool, block_signals=signals)
    assert top is not None
    assert top['email'] == 'clean@t.com'


def test_top_worker_browser_profile_signal() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=40, limit=40,
                browser='Chrome', profile='Profile 2'),
        _worker(tool='chatgpt', email='b@t.com', remaining=40, limit=40,
                browser='Chrome', profile='Default'),
    ])
    signals = {'chrome:profile 2:chatgpt': ['no_disponible']}
    top = top_worker_for_target('chatgpt', pool=pool, block_signals=signals)
    assert top is not None
    assert top['email'] == 'b@t.com'
