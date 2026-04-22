"""Tests for MCP server probe fix and semantic embeddings."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. MCPToolAdapter probe tests
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = 'ok') -> None:
        self.status_code = status_code
        self.text = text
        self.is_success = 200 <= status_code < 300

    def json(self) -> dict[str, Any]:
        return {}


class _FakeClient:
    def __init__(self, *, fail_paths: set[str] | None = None, fail_all: bool = False) -> None:
        self._fail_paths = fail_paths or set()
        self._fail_all = fail_all

    def get(self, url: str, **kw: Any) -> _FakeResponse:
        if self._fail_all:
            raise ConnectionError('refused')
        for path in self._fail_paths:
            if url.endswith(path):
                raise ConnectionError(f'{path} refused')
        return _FakeResponse(405, 'Method Not Allowed')

    def post(self, url: str, **kw: Any) -> _FakeResponse:
        if self._fail_all:
            raise ConnectionError('refused')
        return _FakeResponse(200, '{}')

    def __enter__(self) -> '_FakeClient':
        return self

    def __exit__(self, *a: object) -> None:
        pass


def _make_card(server_url: str = 'http://127.0.0.1:8000') -> Any:
    from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
    from iabv_v15.domain.models import ToolCard, ToolType
    card = ToolCard(
        tool_id='mcp_client',
        title='MCP client',
        tool_type=ToolType.MCP_CLIENT,
        description='test',
        adapter_key='mcp',
        metadata={'server_url': server_url},
    )
    return card


class TestMCPProbe:
    def test_available_when_server_responds(self) -> None:
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        adapter = MCPToolAdapter()
        card = _make_card()
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.Client.return_value = _FakeClient()
            assert adapter.is_available(card) is True

    def test_unavailable_when_server_down(self) -> None:
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        adapter = MCPToolAdapter()
        card = _make_card()
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.Client.return_value = _FakeClient(fail_all=True)
            assert adapter.is_available(card) is False

    def test_unavailable_when_no_server_url(self) -> None:
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        from iabv_v15.domain.models import ToolCard, ToolType
        adapter = MCPToolAdapter()
        card = ToolCard(
            tool_id='mcp_client',
            title='MCP client',
            tool_type=ToolType.MCP_CLIENT,
            description='test',
            adapter_key='mcp',
            metadata={},
        )
        assert adapter.is_available(card) is False

    def test_available_when_mcp_path_responds_but_root_fails(self) -> None:
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        adapter = MCPToolAdapter()
        card = _make_card()
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.Client.return_value = _FakeClient(fail_paths={'/'})
            # /mcp works, / fails -> should be available
            assert adapter.is_available(card) is True

    def test_available_via_root_when_mcp_path_fails(self) -> None:
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        adapter = MCPToolAdapter()
        card = _make_card()
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.Client.return_value = _FakeClient(fail_paths={'/mcp'})
            # /mcp fails, / works -> should be available
            assert adapter.is_available(card) is True

    def test_probe_accepts_any_http_status(self) -> None:
        """Even 404/405 proves the server is alive."""
        from iabv_v15.services.tools.tool_adapters import MCPToolAdapter
        adapter = MCPToolAdapter()
        card = _make_card()
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.Client.return_value = _FakeClient()
            assert adapter.is_available(card) is True


# ---------------------------------------------------------------------------
# 2. EmbeddingIndexService semantic search tests
# ---------------------------------------------------------------------------

class TestCosineSimlarity:
    def test_identical_vectors(self) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        assert EmbeddingIndexService._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        assert EmbeddingIndexService._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        sim = EmbeddingIndexService._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert sim == pytest.approx(-1.0)

    def test_empty_vectors(self) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        assert EmbeddingIndexService._cosine_similarity([], []) == 0.0

    def test_mismatched_lengths(self) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        assert EmbeddingIndexService._cosine_similarity([1.0], [1.0, 2.0]) == 0.0


class TestSemanticSearch:
    def _make_service(self, tmp_path: Path) -> Any:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        return EmbeddingIndexService(
            base_url='http://127.0.0.1:11434',
            primary_model='qwen3-embedding:0.6b',
            lightweight_model='embeddinggemma',
            state_path=str(tmp_path / 'state.json'),
        )

    def test_semantic_search_ranks_by_similarity(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        docs = [
            {'title': 'Python loops', 'summary': 'For and while loops in Python', 'body': ''},
            {'title': 'Cooking pasta', 'summary': 'How to boil spaghetti', 'body': ''},
            {'title': 'Python functions', 'summary': 'Defining functions in Python', 'body': ''},
        ]
        fake_embeddings = [
            [1.0, 0.0, 0.0],   # query: "Python programming"
            [0.9, 0.1, 0.0],   # doc0: Python loops — close
            [0.0, 0.0, 1.0],   # doc1: Cooking — far
            [0.95, 0.05, 0.0], # doc2: Python functions — closest
        ]
        with patch.object(service, '_embed', return_value=fake_embeddings):
            results = service.search('Python programming', docs, limit=3)
        assert len(results) >= 2
        assert results[0]['title'] == 'Python functions'
        assert results[1]['title'] == 'Python loops'
        assert results[0]['search_mode'] == 'semantic'

    def test_falls_back_to_lexical_when_embed_fails(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        docs = [
            {'title': 'Python loops', 'summary': 'for while loops python', 'body': ''},
            {'title': 'Cooking pasta', 'summary': 'boil spaghetti water', 'body': ''},
        ]
        with patch.object(service, '_embed', return_value=None):
            results = service.search('python loops', docs, limit=5)
        assert len(results) >= 1
        assert results[0]['title'] == 'Python loops'
        assert results[0].get('search_mode') == 'lexical'

    def test_lexical_still_works_standalone(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        docs = [
            {'title': 'Git commands', 'summary': 'commit push pull branch', 'body': ''},
            {'title': 'Docker', 'summary': 'container image build', 'body': ''},
        ]
        results = service._search_lexical('git commit push', list(docs), limit=5)
        assert len(results) >= 1
        assert results[0]['title'] == 'Git commands'

    def test_refresh_metadata_reports_semantic_mode(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        service._preferred_model = 'qwen3-embedding:0.6b'
        meta = service.refresh_metadata(knowledge_count=10, artifact_count=3)
        assert meta['index_mode'] == 'semantic'
        assert meta['active_model'] == 'qwen3-embedding:0.6b'

    def test_refresh_metadata_reports_lexical_when_no_model(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        service._preferred_model = None
        with patch.object(service, '_resolve_model', return_value=None):
            meta = service.refresh_metadata(knowledge_count=10, artifact_count=3)
        assert meta['index_mode'] == 'lexical-fallback'
        assert meta['active_model'] == ''

    def test_health_check_sets_preferred_model(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)

        class FakeResp:
            status_code = 200
            def raise_for_status(self) -> None:
                pass
            def json(self) -> dict[str, Any]:
                return {'models': [{'name': 'qwen3-embedding:0.6b'}]}

        class FakeClient:
            def get(self, url: str, **kw: Any) -> FakeResp:
                return FakeResp()
            def __enter__(self) -> 'FakeClient':
                return self
            def __exit__(self, *a: object) -> None:
                pass

        with patch('iabv_v15.services.roles.embedding_index_service.httpx') as mock_httpx:
            mock_httpx.Client.return_value = FakeClient()
            mock_httpx.__bool__ = lambda self: True
            health = service.health_check()
        assert health.available is True
        assert 'semantico' in (health.detail or '')
        assert service._preferred_model == 'qwen3-embedding:0.6b'

    def test_embed_calls_ollama_api(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        service._preferred_model = 'qwen3-embedding:0.6b'

        class FakeResp:
            status_code = 200
            def raise_for_status(self) -> None:
                pass
            def json(self) -> dict[str, Any]:
                return {'embeddings': [[0.1, 0.2], [0.3, 0.4]]}

        class FakeClient:
            def post(self, url: str, **kw: Any) -> FakeResp:
                assert '/api/embed' in url
                return FakeResp()
            def __enter__(self) -> 'FakeClient':
                return self
            def __exit__(self, *a: object) -> None:
                pass

        with patch('iabv_v15.services.roles.embedding_index_service.httpx') as mock_httpx:
            mock_httpx.Client.return_value = FakeClient()
            mock_httpx.__bool__ = lambda self: True
            result = service._embed(['hello', 'world'])
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_embed_returns_none_when_api_fails(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        service._preferred_model = 'qwen3-embedding:0.6b'

        class FakeClient:
            def post(self, url: str, **kw: Any) -> None:
                raise ConnectionError('refused')
            def __enter__(self) -> 'FakeClient':
                return self
            def __exit__(self, *a: object) -> None:
                pass

        with patch('iabv_v15.services.roles.embedding_index_service.httpx') as mock_httpx:
            mock_httpx.Client.return_value = FakeClient()
            mock_httpx.__bool__ = lambda self: True
            result = service._embed(['hello'])
        assert result is None

    def test_describe_index_shows_active_model(self, tmp_path: Path) -> None:
        service = self._make_service(tmp_path)
        service._preferred_model = 'qwen3-embedding:0.6b'
        desc = service.describe_index()
        assert desc['index_mode'] == 'semantic'
        assert desc['active_model'] == 'qwen3-embedding:0.6b'


# ---------------------------------------------------------------------------
# 3. Integration: search_mode tag propagates correctly
# ---------------------------------------------------------------------------

class TestSearchModeTag:
    def test_semantic_results_have_mode_tag(self, tmp_path: Path) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        service = EmbeddingIndexService(
            base_url='http://localhost:11434',
            primary_model='test-model',
            lightweight_model='test-light',
            state_path=str(tmp_path / 'state.json'),
        )
        docs = [{'title': 'A', 'summary': 'test doc', 'body': ''}]
        fake_vecs = [[1.0, 0.0], [0.9, 0.1]]
        with patch.object(service, '_embed', return_value=fake_vecs):
            results = service.search('test', docs, limit=5)
        assert all(r.get('search_mode') == 'semantic' for r in results)

    def test_lexical_results_have_mode_tag(self, tmp_path: Path) -> None:
        from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
        service = EmbeddingIndexService(
            base_url='http://localhost:11434',
            primary_model='test-model',
            lightweight_model='test-light',
            state_path=str(tmp_path / 'state.json'),
        )
        docs = [{'title': 'test doc', 'summary': 'test content here', 'body': ''}]
        with patch.object(service, '_embed', return_value=None):
            results = service.search('test content', docs, limit=5)
        assert all(r.get('search_mode') == 'lexical' for r in results)
