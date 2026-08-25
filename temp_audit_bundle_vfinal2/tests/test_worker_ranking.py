"""Focused tests for worker ranking functions.

Covers:
- _score_worker: exhausted → 0, full quota → 1, partial quota → proportional
- rank_workers_for_target: filters by target, sorts by score, excludes exhausted
- top_worker_for_target: returns best or None
- empty pool / no matching target
"""
from __future__ import annotations

from iabv_v15.services.account_resource_scanner import (
    _score_worker,
    rank_workers_for_target,
    top_worker_for_target,
)


def _worker(
    tool: str = 'chatgpt',
    email: str = 'a@test.com',
    remaining: int = 10,
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


def _pool(workers: list[dict], exhausted: list[dict] | None = None) -> dict:
    return {
        'workers': workers,
        'exhausted': exhausted or [],
        'available_count': len(workers),
        'exhausted_count': len(exhausted or []),
        'by_tool': {},
        'total_remaining_messages': sum(w['remaining_messages'] for w in workers),
    }


# ─── _score_worker ───────────────────────────────────────────


def test_score_exhausted_worker_is_zero() -> None:
    assert _score_worker(_worker(exhausted=True)) == 0.0


def test_score_full_quota() -> None:
    w = _worker(remaining=40, limit=40)
    assert _score_worker(w) == 1.0


def test_score_half_quota() -> None:
    w = _worker(remaining=20, limit=40)
    assert _score_worker(w) == 0.5


def test_score_zero_remaining() -> None:
    w = _worker(remaining=0, limit=40, exhausted=False)
    assert _score_worker(w) == 0.0


def test_score_zero_limit_no_crash() -> None:
    w = _worker(remaining=5, limit=0)
    score = _score_worker(w)
    assert score >= 0.0


# ─── rank_workers_for_target ─────────────────────────────────


def test_rank_filters_by_target() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=30, limit=40),
        _worker(tool='claude', email='b@t.com', remaining=20, limit=40),
        _worker(tool='chatgpt', email='c@t.com', remaining=10, limit=40),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert len(ranked) == 2
    assert all(r['tool'] == 'chatgpt' for r in ranked)


def test_rank_sorted_descending_by_score() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='low@t.com', remaining=5, limit=40),
        _worker(tool='chatgpt', email='high@t.com', remaining=35, limit=40),
        _worker(tool='chatgpt', email='mid@t.com', remaining=20, limit=40),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    scores = [r['score'] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0]['email'] == 'high@t.com'
    assert ranked[-1]['email'] == 'low@t.com'


def test_rank_excludes_exhausted() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='good@t.com', remaining=30, limit=40),
        _worker(tool='chatgpt', email='dead@t.com', remaining=0, limit=40, exhausted=True),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert len(ranked) == 1
    assert ranked[0]['email'] == 'good@t.com'


def test_rank_empty_target_returns_all() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=10, limit=40),
        _worker(tool='claude', email='b@t.com', remaining=20, limit=40),
    ])
    ranked = rank_workers_for_target('', pool=pool)
    assert len(ranked) == 2


def test_rank_no_matching_target() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=10, limit=40),
    ])
    ranked = rank_workers_for_target('codex', pool=pool)
    assert ranked == []


def test_rank_empty_pool() -> None:
    pool = _pool([])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert ranked == []


def test_rank_case_insensitive() -> None:
    pool = _pool([
        _worker(tool='ChatGPT', email='a@t.com', remaining=10, limit=40),
    ])
    ranked = rank_workers_for_target('CHATGPT', pool=pool)
    assert len(ranked) == 1


# ─── top_worker_for_target ───────────────────────────────────


def test_top_returns_best() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='low@t.com', remaining=5, limit=40),
        _worker(tool='chatgpt', email='best@t.com', remaining=40, limit=40),
    ])
    top = top_worker_for_target('chatgpt', pool=pool)
    assert top is not None
    assert top['email'] == 'best@t.com'
    assert top['score'] == 1.0


def test_top_returns_none_when_empty() -> None:
    pool = _pool([])
    assert top_worker_for_target('chatgpt', pool=pool) is None


def test_top_returns_none_when_no_match() -> None:
    pool = _pool([
        _worker(tool='claude', email='a@t.com', remaining=10, limit=40),
    ])
    assert top_worker_for_target('codex', pool=pool) is None


def test_score_included_in_ranked_output() -> None:
    pool = _pool([
        _worker(tool='chatgpt', email='a@t.com', remaining=20, limit=40),
    ])
    ranked = rank_workers_for_target('chatgpt', pool=pool)
    assert len(ranked) == 1
    assert 'score' in ranked[0]
    assert ranked[0]['score'] == 0.5
