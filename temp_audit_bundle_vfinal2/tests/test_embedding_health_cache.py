"""Tests for EmbeddingIndexService.health_check() TTL cache.

Validates that the HTTP probe to Ollama /models is cached within the
default 30 s TTL and that explicit refresh (max_age_seconds=0) bypasses
the cache.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import ProviderHealth, ProviderStatus
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService


@pytest.fixture()
def svc(tmp_path: Path) -> EmbeddingIndexService:
    return EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding',
        lightweight_model='all-minilm',
        state_path=str(tmp_path / 'embedding_state.json'),
    )


# ------------------------------------------------------------------
# TTL cache behaviour
# ------------------------------------------------------------------

def test_first_call_does_http_probe(svc: EmbeddingIndexService) -> None:
    with patch.object(svc, '_probe_health', return_value=ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='ok',
    )) as probe:
        result = svc.health_check()
        assert probe.call_count == 1
        assert result.available is True


def test_second_call_within_ttl_returns_cached(svc: EmbeddingIndexService) -> None:
    probe_result = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='cached',
    )
    with patch.object(svc, '_probe_health', return_value=probe_result) as probe:
        first = svc.health_check()
        second = svc.health_check()
        assert probe.call_count == 1
        assert first.detail == 'cached'
        assert second.detail == 'cached'
        assert first is not second  # deep copy


def test_explicit_refresh_bypasses_cache(svc: EmbeddingIndexService) -> None:
    cached = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='old',
    )
    fresh = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='new',
    )
    with patch.object(svc, '_probe_health', side_effect=[cached, fresh]) as probe:
        svc.health_check()
        result = svc.health_check(max_age_seconds=0.0)
        assert probe.call_count == 2
        assert result.detail == 'new'


def test_cache_expires_after_ttl(svc: EmbeddingIndexService) -> None:
    svc._HEALTH_TTL = 0.1  # 100 ms for test speed
    old = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.DEGRADED,
        available=False, detail='old',
    )
    new = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='new',
    )
    with patch.object(svc, '_probe_health', side_effect=[old, new]) as probe:
        svc.health_check()
        time.sleep(0.15)
        result = svc.health_check()
        assert probe.call_count == 2
        assert result.detail == 'new'


def test_cache_not_populated_when_no_httpx(svc: EmbeddingIndexService) -> None:
    """When httpx is missing, health_check returns degraded and still caches."""
    with patch('iabv_v15.services.roles.embedding_index_service.httpx', None):
        result = svc.health_check()
        assert result.available is False
        assert 'httpx' in result.detail
        # Cached — second call doesn't re-check
        result2 = svc.health_check()
        assert result2.detail == result.detail


def test_custom_max_age_seconds(svc: EmbeddingIndexService) -> None:
    probe_result = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    with patch.object(svc, '_probe_health', return_value=probe_result) as probe:
        svc.health_check(max_age_seconds=60.0)
        svc.health_check(max_age_seconds=60.0)
        assert probe.call_count == 1


# ------------------------------------------------------------------
# Thread safety
# ------------------------------------------------------------------

def test_concurrent_calls_share_cache(svc: EmbeddingIndexService) -> None:
    import threading

    probe_result = ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='shared',
    )
    with patch.object(svc, '_probe_health', return_value=probe_result) as probe:
        # Prime the cache
        svc.health_check()

        results: list[ProviderHealth] = []
        barrier = threading.Barrier(4)

        def worker() -> None:
            barrier.wait()
            results.append(svc.health_check())

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # First call primed cache; 4 threads should all hit cache
        assert probe.call_count == 1
        assert all(r.detail == 'shared' for r in results)


# ------------------------------------------------------------------
# LocalRoleRouter integration
# ------------------------------------------------------------------

def test_health_snapshot_passes_ttl_to_embedding(tmp_path: Path) -> None:
    from iabv_v15.services.roles.local_role_router import LocalRoleRouter

    general = MagicMock()
    general.health_check.return_value = ProviderHealth(
        provider_name='Ollama', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    visual = MagicMock()
    visual.health_check.return_value = ProviderHealth(
        provider_name='Ollama Vision', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding',
        lightweight_model='all-minilm',
        state_path=str(tmp_path / 'state.json'),
    )

    router = LocalRoleRouter(
        workspace_root=str(tmp_path),
        general_provider=general,
        visual_provider=visual,
        optional_provider=None,
        embedding_service=embedding,
        sql_service=MagicMock(),
        analytics_service=MagicMock(),
        customer_support_service=MagicMock(),
        engineering_review_service=MagicMock(),
        teaching_gap_analyzer=MagicMock(),
        episode_repository=MagicMock(),
        knowledge_repository=MagicMock(),
        run_repository=MagicMock(),
        artifact_repository=MagicMock(),
        tool_teach_service=MagicMock(),
        account_resource_scanner=MagicMock(),
    )

    with patch.object(embedding, '_probe_health', return_value=ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='probed',
    )) as probe:
        # First snapshot — cache empty, should probe
        snap1 = router.health_snapshot(refresh=False, max_age_seconds=30.0)
        assert probe.call_count == 1
        assert any(h.provider_name == 'Embeddings' for h in snap1)

        # Second snapshot within TTL — router cache returns immediately,
        # embedding probe not called again
        snap2 = router.health_snapshot(refresh=False, max_age_seconds=30.0)
        assert probe.call_count == 1  # router-level cache hit

        # Explicit refresh — bypasses both router and embedding caches
        snap3 = router.health_snapshot(refresh=True, max_age_seconds=0.0)
        assert probe.call_count == 2  # forced refresh


def test_health_snapshot_refresh_true_forces_embedding_probe(tmp_path: Path) -> None:
    from iabv_v15.services.roles.local_role_router import LocalRoleRouter

    general = MagicMock()
    general.health_check.return_value = ProviderHealth(
        provider_name='Ollama', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    visual = MagicMock()
    visual.health_check.return_value = ProviderHealth(
        provider_name='Ollama Vision', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding',
        lightweight_model='all-minilm',
        state_path=str(tmp_path / 'state.json'),
    )

    router = LocalRoleRouter(
        workspace_root=str(tmp_path),
        general_provider=general,
        visual_provider=visual,
        optional_provider=None,
        embedding_service=embedding,
        sql_service=MagicMock(),
        analytics_service=MagicMock(),
        customer_support_service=MagicMock(),
        engineering_review_service=MagicMock(),
        teaching_gap_analyzer=MagicMock(),
        episode_repository=MagicMock(),
        knowledge_repository=MagicMock(),
        run_repository=MagicMock(),
        artifact_repository=MagicMock(),
        tool_teach_service=MagicMock(),
        account_resource_scanner=MagicMock(),
    )

    with patch.object(embedding, '_probe_health', return_value=ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='fresh',
    )) as probe:
        router.health_snapshot(refresh=True, max_age_seconds=0.0)
        router.health_snapshot(refresh=True, max_age_seconds=0.0)
        assert probe.call_count == 2  # each refresh=True forces a probe


# ------------------------------------------------------------------
# Parallel health checks
# ------------------------------------------------------------------

def test_parallel_health_checks_preserves_order(tmp_path: Path) -> None:
    """Parallel health checks must return results in deterministic order."""
    from iabv_v15.services.roles.local_role_router import LocalRoleRouter

    general = MagicMock()
    general.health_check.return_value = ProviderHealth(
        provider_name='Ollama', status=ProviderStatus.READY,
        available=True, detail='general',
    )
    visual = MagicMock()
    visual.health_check.return_value = ProviderHealth(
        provider_name='Ollama Vision', status=ProviderStatus.READY,
        available=True, detail='visual',
    )
    optional = MagicMock()
    optional.health_check.return_value = ProviderHealth(
        provider_name='LM Studio', status=ProviderStatus.READY,
        available=True, detail='optional',
    )
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding',
        lightweight_model='all-minilm',
        state_path=str(tmp_path / 'state.json'),
    )

    router = LocalRoleRouter(
        workspace_root=str(tmp_path),
        general_provider=general,
        visual_provider=visual,
        optional_provider=optional,
        embedding_service=embedding,
        sql_service=MagicMock(),
        analytics_service=MagicMock(),
        customer_support_service=MagicMock(),
        engineering_review_service=MagicMock(),
        teaching_gap_analyzer=MagicMock(),
        episode_repository=MagicMock(),
        knowledge_repository=MagicMock(),
        run_repository=MagicMock(),
        artifact_repository=MagicMock(),
        tool_teach_service=MagicMock(),
        account_resource_scanner=MagicMock(),
    )

    with patch.object(embedding, '_probe_health', return_value=ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='embedding',
    )):
        snap = router.health_snapshot(refresh=True, max_age_seconds=0.0)

    assert len(snap) == 4
    assert snap[0].provider_name == 'Ollama'
    assert snap[1].provider_name == 'Ollama Vision'
    assert snap[2].provider_name == 'LM Studio'
    assert snap[3].provider_name == 'Embeddings'


def test_parallel_health_checks_handles_provider_exception(tmp_path: Path) -> None:
    """If one provider raises, the snapshot still contains all entries."""
    from iabv_v15.services.roles.local_role_router import LocalRoleRouter

    general = MagicMock()
    general.health_check.side_effect = RuntimeError('connection refused')
    visual = MagicMock()
    visual.health_check.return_value = ProviderHealth(
        provider_name='Ollama Vision', status=ProviderStatus.READY,
        available=True, detail='ok',
    )
    embedding = EmbeddingIndexService(
        base_url='http://127.0.0.1:11434/v1',
        primary_model='qwen3-embedding',
        lightweight_model='all-minilm',
        state_path=str(tmp_path / 'state.json'),
    )

    router = LocalRoleRouter(
        workspace_root=str(tmp_path),
        general_provider=general,
        visual_provider=visual,
        optional_provider=None,
        embedding_service=embedding,
        sql_service=MagicMock(),
        analytics_service=MagicMock(),
        customer_support_service=MagicMock(),
        engineering_review_service=MagicMock(),
        teaching_gap_analyzer=MagicMock(),
        episode_repository=MagicMock(),
        knowledge_repository=MagicMock(),
        run_repository=MagicMock(),
        artifact_repository=MagicMock(),
        tool_teach_service=MagicMock(),
        account_resource_scanner=MagicMock(),
    )

    with patch.object(embedding, '_probe_health', return_value=ProviderHealth(
        provider_name='Embeddings', status=ProviderStatus.READY,
        available=True, detail='ok',
    )):
        snap = router.health_snapshot(refresh=True, max_age_seconds=0.0)

    assert len(snap) == 3
    assert snap[0].available is False
    assert 'connection refused' in snap[0].detail
    assert snap[1].provider_name == 'Ollama Vision'
    assert snap[2].provider_name == 'Embeddings'
