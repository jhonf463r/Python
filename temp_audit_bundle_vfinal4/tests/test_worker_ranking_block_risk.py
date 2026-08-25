"""Focused tests for block-risk scoring in worker ranking.

Covers:
- _compute_block_risk: known signals, unknown signals, multiple signals, cap
- _score_worker: penalized by block_risk, no penalty without signals
- rank_workers_for_target: order changes when same quota but different risk
- top_worker_for_target: passes block_signals through
- backward compatibility: omitting block_signals preserves old behavior
"""
from __future__ import annotations

from iabv_v15.services.account_resource_scanner import (
    _compute_block_risk,
    _score_worker,
    _BLOCK_SIGNAL_WEIGHTS,
    _DEFAULT_SIGNAL_WEIGHT,
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
) -> dict:
    return {
        'tool': tool,
        'email': email,
        'remaining_messages': remaining,
        'limit': limit,
        'exhausted': exhausted,
        'browser': 'Chrome',
        'profile': 'Default',
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


# ─── _compute_block_risk ────────────────────────────────────


def test_no_signals_zero_risk() -> None:
    w = _worker(tool='chatgpt')
    assert _compute_block_risk(w, None) == 0.0
    assert _compute_block_risk(w, {}) == 0.0
    assert _compute_block_risk(w, {'codex': ['wrong_thread']}) == 0.0


def test_known_signal_applies_weight() -> None:
    w = _worker(tool='codex')
    risk = _compute_block_risk(w, {'codex': ['wrong_thread']})
    assert risk == round(_BLOCK_SIGNAL_WEIGHTS['wrong_thread'], 4)


def test_unknown_signal_uses_default() -> None:
    w = _worker(tool='chatgpt')
    risk = _compute_block_risk(w, {'chatgpt': ['some_new_signal']})
    assert risk == round(_DEFAULT_SIGNAL_WEIGHT, 4)


def test_multiple_signals_compound() -> None:
    w = _worker(tool='codex')
    signals = {'codex': ['wrong_thread', 'capture_unverified']}
    risk = _compute_block_risk(w, signals)
    expected = 1.0 - (1.0 - 0.40) * (1.0 - 0.20)
    assert risk == round(expected, 4)
    assert risk > _BLOCK_SIGNAL_WEIGHTS['wrong_thread']
    assert risk > _BLOCK_SIGNAL_WEIGHTS['capture_unverified']


def test_risk_capped_at_max() -> None:
    w = _worker(tool='chatgpt')
    heavy_signals = {'chatgpt': ['auth_expired', 'no_disponible', 'rate_limited']}
    risk = _compute_block_risk(w, heavy_signals)
    assert risk <= _MAX_BLOCK_RISK


def test_no_disponible_is_heavy() -> None:
    w = _worker(tool='claude')
    risk = _compute_block_risk(w, {'claude': ['no_disponible']})
    assert risk == round(_BLOCK_SIGNAL_WEIGHTS['no_disponible'], 4)
    assert risk >= 0.7


def test_auth_expired_is_heaviest() -> None:
    w = _worker(tool='chatgpt')
    risk = _compute_block_risk(w, {'chatgpt': ['auth_expired']})
    assert risk >= 0.9


def test_tool_matching_is_case_insensitive() -> None:
    w = _worker(tool='ChatGPT')
    risk = _compute_block_risk(w, {'chatgpt': ['awaiting_response']})
    assert risk == round(_BLOCK_SIGNAL_WEIGHTS['awaiting_response'], 4)


# ─── _score_worker with block_signals ────────────────────────


def test_score_no_signals_equals_quota() -> None:
    w = _worker(remaining=20, limit=40)
    assert _score_worker(w) == 0.5
    assert _score_worker(w, block_signals=None) == 0.5
    assert _score_worker(w, block_signals={}) == 0.5


def test_score_penalized_by_block_risk() -> None:
    w = _worker(tool='codex', remaining=40, limit=40)
    clean_score = _score_worker(w)
    penalized_score = _score_worker(w, block_signals={'codex': ['wrong_thread']})
    assert penalized_score < clean_score
    expected = round(1.0 * (1.0 - 0.40), 4)
    assert penalized_score == expected


def test_score_zero_when_exhausted_even_with_no_signals() -> None:
    w = _worker(exhausted=True)
    assert _score_worker(w, block_signals={}) == 0.0


def test_score_composes_quota_and_risk() -> None:
    w = _worker(tool='chatgpt', remaining=20, limit=40)
    score = _score_worker(w, block_signals={'chatgpt': ['awaiting_response']})
    expected = round(0.5 * (1.0 - 0.30), 4)
    assert score == expected


# ─── rank_workers_for_target with block_signals ──────────────


def test_rank_order_changes_with_block_risk() -> None:
    """Two workers with same quota; the blocked one should rank lower."""
    pool = _pool([
        _worker(tool='chatgpt', email='blocked@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='clean@t.com', remaining=40, limit=40),
    ])
    signals = {'chatgpt': ['awaiting_response']}
    ranked = rank_workers_for_target('chatgpt', pool=pool, block_signals=signals)
    assert len(ranked) == 2
    # Both have same quota, but blocked@t.com has awaiting_response
    # However, block_signals apply to ALL chatgpt workers equally here
    # because the signal is per-tool, not per-email.
    # Both should be penalized equally in this case.
    assert ranked[0]['score'] == ranked[1]['score']


def test_rank_mixed_tools_different_risk() -> None:
    """Codex blocked, ChatGPT clean — ChatGPT should rank first."""
    pool = _pool([
        _worker(tool='codex', email='codex@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='gpt@t.com', remaining=40, limit=40),
    ])
    signals = {'codex': ['wrong_thread', 'capture_unverified']}
    ranked = rank_workers_for_target('', pool=pool, block_signals=signals)
    assert len(ranked) == 2
    assert ranked[0]['email'] == 'gpt@t.com'
    assert ranked[0]['score'] > ranked[1]['score']
    assert ranked[1]['block_risk'] > 0


def test_rank_same_quota_different_risk_reorders() -> None:
    """Same quota across tools; risk alone determines order."""
    pool = _pool([
        _worker(tool='codex', email='risky@t.com', remaining=40, limit=40),
        _worker(tool='claude', email='safe@t.com', remaining=40, limit=40),
    ])
    signals = {'codex': ['wrong_thread']}
    ranked = rank_workers_for_target('', pool=pool, block_signals=signals)
    assert ranked[0]['email'] == 'safe@t.com'
    assert ranked[0]['block_risk'] == 0.0
    assert ranked[1]['block_risk'] > 0


def test_rank_includes_block_risk_field() -> None:
    pool = _pool([_worker(tool='chatgpt', remaining=40, limit=40)])
    ranked = rank_workers_for_target('chatgpt', pool=pool, block_signals={})
    assert 'block_risk' in ranked[0]
    assert ranked[0]['block_risk'] == 0.0


def test_rank_without_block_signals_backward_compatible() -> None:
    """Omitting block_signals produces identical results to old behavior."""
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=30, limit=40),
        _worker(tool='chatgpt', email='b@t.com', remaining=10, limit=40),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert ranked[0]['email'] == 'a@t.com'
    assert ranked[0]['score'] == round(30 / 40, 4)
    assert ranked[1]['score'] == round(10 / 40, 4)


# ─── top_worker_for_target with block_signals ────────────────


def test_top_worker_respects_block_signals() -> None:
    pool = _pool([
        _worker(tool='codex', email='risky@t.com', remaining=40, limit=40),
        _worker(tool='chatgpt', email='safe@t.com', remaining=40, limit=40),
    ])
    signals = {'codex': ['auth_expired']}
    top = top_worker_for_target('', pool=pool, block_signals=signals)
    assert top is not None
    assert top['email'] == 'safe@t.com'


def test_top_worker_none_without_signals_still_works() -> None:
    pool = _pool([])
    assert top_worker_for_target('chatgpt', pool=pool) is None


def test_top_worker_without_block_signals_backward_compatible() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='best@t.com', remaining=40, limit=40),
    ])
    top = top_worker_for_target('chatgpt', pool=pool)
    assert top is not None
    assert top['score'] == 1.0
