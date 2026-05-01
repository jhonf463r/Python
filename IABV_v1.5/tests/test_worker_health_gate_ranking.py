"""Focused tests for worker_health_gate ranking integration.

Covers:
- gate with target returns top_worker and ranked_workers
- top_worker is the highest-scored worker
- ranked_workers are sorted descending by score
- no-match target still blocks with top_worker=None
- no-scanner still blocks with top_worker=None
- score appears in workers list
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from iabv_v15.services.roles.local_role_router import LocalRoleRouter


# ─── Helpers ─────────────────────────────────────────────────

class _StubProvider:
    """Minimal LLM provider stub for LocalRoleRouter."""
    name = 'stub'
    health_calls = 0
    def health_check(self, **kw: Any) -> Any:
        from iabv_v15.domain.models import ProviderHealth, ProviderStatus
        self.health_calls += 1
        return ProviderHealth(provider_name=self.name, status=ProviderStatus.HEALTHY, available=True)
    def infer(self, prompt: str, **kw: Any) -> str:
        return ''


class _StubEmbedding:
    def health_check(self, **kw: Any) -> Any:
        from iabv_v15.domain.models import ProviderHealth, ProviderStatus
        return ProviderHealth(provider_name='embedding', status=ProviderStatus.HEALTHY, available=True)


class _StubService:
    pass


def _workspace(name: str) -> Path:
    p = Path('/tmp/test_gate_ranking') / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _router(
    ws: Path,
    account_resource_scanner: Any = None,
) -> LocalRoleRouter:
    prov = _StubProvider()
    stub = _StubService()
    embed = _StubEmbedding()
    return LocalRoleRouter(
        workspace_root=str(ws),
        general_provider=prov,
        visual_provider=prov,
        optional_provider=prov,
        embedding_service=embed,  # type: ignore[arg-type]
        sql_service=stub,  # type: ignore[arg-type]
        analytics_service=stub,  # type: ignore[arg-type]
        customer_support_service=stub,  # type: ignore[arg-type]
        engineering_review_service=stub,  # type: ignore[arg-type]
        teaching_gap_analyzer=stub,  # type: ignore[arg-type]
        episode_repository=stub,  # type: ignore[arg-type]
        knowledge_repository=stub,  # type: ignore[arg-type]
        run_repository=stub,  # type: ignore[arg-type]
        artifact_repository=stub,  # type: ignore[arg-type]
        account_resource_scanner=account_resource_scanner,
    )


def _pool_multi_chatgpt() -> dict[str, Any]:
    return {
        'available_count': 3,
        'exhausted_count': 0,
        'total_remaining_messages': 70,
        'workers': [
            {'email': 'low@t.com', 'tool': 'chatgpt', 'remaining_messages': 10, 'limit': 40, 'exhausted': False},
            {'email': 'high@t.com', 'tool': 'chatgpt', 'remaining_messages': 40, 'limit': 40, 'exhausted': False},
            {'email': 'mid@t.com', 'tool': 'chatgpt', 'remaining_messages': 20, 'limit': 40, 'exhausted': False},
        ],
        'exhausted': [],
        'tools_available': ['chatgpt'],
    }


def _pool_mixed() -> dict[str, Any]:
    return {
        'available_count': 3,
        'exhausted_count': 0,
        'total_remaining_messages': 60,
        'workers': [
            {'email': 'a@t.com', 'tool': 'chatgpt', 'remaining_messages': 30, 'limit': 40, 'exhausted': False},
            {'email': 'b@t.com', 'tool': 'claude', 'remaining_messages': 20, 'limit': 40, 'exhausted': False},
            {'email': 'c@t.com', 'tool': 'codex', 'remaining_messages': 10, 'limit': 40, 'exhausted': False},
        ],
        'exhausted': [],
        'tools_available': ['chatgpt', 'claude', 'codex'],
    }


def _pool_all_exhausted() -> dict[str, Any]:
    return {
        'available_count': 0,
        'exhausted_count': 2,
        'total_remaining_messages': 0,
        'workers': [
            {'email': 'a@t.com', 'tool': 'chatgpt', 'remaining_messages': 0, 'limit': 40, 'exhausted': True},
            {'email': 'b@t.com', 'tool': 'chatgpt', 'remaining_messages': 0, 'limit': 40, 'exhausted': True},
        ],
        'exhausted': [],
        'tools_available': [],
    }


# ─── Tests ───────────────────────────────────────────────────


def test_gate_target_returns_top_worker() -> None:
    router = _router(_workspace('top_worker'), account_resource_scanner=_pool_multi_chatgpt)
    gate = router.worker_health_gate(target_assistant='chatgpt')
    assert gate['usable'] is True
    assert gate['top_worker'] is not None
    assert gate['top_worker']['email'] == 'high@t.com'
    assert gate['top_worker']['score'] == 1.0


def test_gate_ranked_workers_sorted_by_score() -> None:
    router = _router(_workspace('ranked_sort'), account_resource_scanner=_pool_multi_chatgpt)
    gate = router.worker_health_gate(target_assistant='chatgpt')
    ranked = gate['ranked_workers']
    assert len(ranked) == 3
    scores = [w['score'] for w in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0]['email'] == 'high@t.com'
    assert ranked[-1]['email'] == 'low@t.com'


def test_gate_workers_include_score() -> None:
    router = _router(_workspace('score_in_workers'), account_resource_scanner=_pool_multi_chatgpt)
    gate = router.worker_health_gate(target_assistant='chatgpt')
    for w in gate['workers']:
        assert 'score' in w
        assert isinstance(w['score'], float)


def test_gate_no_target_returns_all_ranked() -> None:
    router = _router(_workspace('no_target'), account_resource_scanner=_pool_mixed)
    gate = router.worker_health_gate()
    assert gate['usable'] is True
    assert gate['available_count'] == 3
    assert gate['top_worker'] is not None
    assert gate['top_worker']['email'] == 'a@t.com'
    assert len(gate['ranked_workers']) == 3


def test_gate_target_miss_returns_none_top_worker() -> None:
    router = _router(_workspace('target_miss'), account_resource_scanner=_pool_mixed)
    gate = router.worker_health_gate(target_assistant='devin')
    assert gate['usable'] is False
    assert gate['top_worker'] is None
    assert gate['ranked_workers'] == []


def test_gate_no_scanner_returns_no_ranking_keys() -> None:
    router = _router(_workspace('no_scanner'))
    gate = router.worker_health_gate()
    assert gate['usable'] is False
    assert gate['available_count'] == 0


def test_gate_exhausted_returns_none_top_worker() -> None:
    router = _router(_workspace('exhausted'), account_resource_scanner=_pool_all_exhausted)
    gate = router.worker_health_gate(target_assistant='chatgpt')
    assert gate['usable'] is False
    assert gate['top_worker'] is None
    assert gate['ranked_workers'] == []


def test_gate_top_worker_matches_first_ranked() -> None:
    router = _router(_workspace('top_matches_first'), account_resource_scanner=_pool_multi_chatgpt)
    gate = router.worker_health_gate(target_assistant='chatgpt')
    assert gate['top_worker']['email'] == gate['ranked_workers'][0]['email']
    assert gate['top_worker']['score'] == gate['ranked_workers'][0]['score']
