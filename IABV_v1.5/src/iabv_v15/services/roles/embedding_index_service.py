from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Iterable

from iabv_v15.domain.models import ProviderHealth, ProviderStatus

try:  # pragma: no cover - optional import in runtime
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

logger = logging.getLogger(__name__)

_MAX_SEMANTIC_DOCUMENTS = 100


class EmbeddingIndexService:
    def __init__(
        self,
        *,
        base_url: str,
        primary_model: str,
        lightweight_model: str,
        state_path: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.primary_model = primary_model
        self.lightweight_model = lightweight_model
        self.state_path = Path(state_path)
        self.timeout_seconds = timeout_seconds
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._preferred_model: str | None = None

    def _resolve_model(self) -> str | None:
        """Return the best available embedding model, or ``None``."""
        if self._preferred_model is not None:
            return self._preferred_model
        if httpx is None:
            return None
        try:
            with httpx.Client(timeout=min(self.timeout_seconds, 8.0)) as client:
                response = client.get(f'{self.base_url}/models')
                response.raise_for_status()
                payload = response.json()
            models = self._extract_model_names(payload)
            if self.primary_model in models:
                self._preferred_model = self.primary_model
            elif self.lightweight_model in models:
                self._preferred_model = self.lightweight_model
            return self._preferred_model
        except Exception:
            return None

    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        """Call Ollama ``/api/embed`` to get vectors for *texts*.

        Returns a list of embedding vectors (one per input text), or
        ``None`` when the service is unreachable or the model is not
        available.  Uses the batch-capable ``/api/embed`` endpoint.
        """
        if httpx is None or not texts:
            return None
        model = self._resolve_model()
        if not model:
            return None
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(
                    f'{self.base_url}/api/embed',
                    json={'model': model, 'input': texts},
                )
                resp.raise_for_status()
                data = resp.json()
            embeddings = data.get('embeddings')
            if isinstance(embeddings, list) and len(embeddings) == len(texts):
                return embeddings
            return None
        except Exception as exc:
            logger.debug('Embedding call failed, falling back to lexical: %s', exc)
            return None

    def refresh_metadata(self, *, knowledge_count: int, artifact_count: int, last_query: str = '') -> dict[str, object]:
        model = self._resolve_model()
        mode = 'semantic' if model else 'lexical-fallback'
        payload = {
            'knowledge_count': knowledge_count,
            'artifact_count': artifact_count,
            'index_mode': mode,
            'primary_model': self.primary_model,
            'lightweight_model': self.lightweight_model,
            'last_query': last_query,
            'active_model': model or '',
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return payload

    def health_check(self) -> ProviderHealth:
        if httpx is None:
            return ProviderHealth(provider_name='Embeddings', status=ProviderStatus.DEGRADED, available=False, detail='httpx no esta instalado.')
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=min(self.timeout_seconds, 8.0)) as client:
                response = client.get(f'{self.base_url}/models')
                response.raise_for_status()
                payload = response.json()
            models = self._extract_model_names(payload)
            preferred = self.primary_model if self.primary_model in models else self.lightweight_model if self.lightweight_model in models else None
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if preferred is None:
                return ProviderHealth(
                    provider_name='Embeddings',
                    status=ProviderStatus.DEGRADED,
                    available=False,
                    latency_ms=latency_ms,
                    detail=f'Ningun modelo de embeddings disponible. Esperados: {self.primary_model} o {self.lightweight_model}.',
                )
            self._preferred_model = preferred
            return ProviderHealth(
                provider_name='Embeddings',
                status=ProviderStatus.READY,
                available=True,
                latency_ms=latency_ms,
                detail=f'Indexado semantico listo con {preferred}.',
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name='Embeddings',
                status=ProviderStatus.DEGRADED,
                available=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
                detail=str(exc),
            )

    def search(self, query: str, documents: Iterable[dict[str, str]], limit: int = 5) -> list[dict[str, object]]:
        doc_list = list(documents)
        if doc_list and len(doc_list) <= _MAX_SEMANTIC_DOCUMENTS:
            result = self._search_semantic(query, doc_list, limit)
            if result is not None:
                return result
        return self._search_lexical(query, doc_list, limit)

    def _search_semantic(self, query: str, documents: list[dict[str, str]], limit: int) -> list[dict[str, object]] | None:
        """Rank documents by cosine similarity of their embeddings to *query*.

        Returns ``None`` when the embedding service is unavailable so the
        caller can fall back to lexical search.
        """
        texts = [
            ' '.join([d.get('title', ''), d.get('summary', ''), d.get('body', '')]).strip()
            for d in documents
        ]
        all_texts = [query, *texts]
        vectors = self._embed(all_texts)
        if vectors is None:
            return None
        query_vec = vectors[0]
        scored: list[dict[str, object]] = []
        for idx, document in enumerate(documents):
            doc_vec = vectors[idx + 1]
            similarity = self._cosine_similarity(query_vec, doc_vec)
            if similarity <= 0.0:
                continue
            scored.append({
                'title': document.get('title', 'Documento'),
                'summary': document.get('summary', ''),
                'score': round(similarity, 4),
                'source': document.get('source', document.get('title', 'Documento')),
                'search_mode': 'semantic',
            })
        return sorted(scored, key=lambda item: float(item['score']), reverse=True)[:limit]

    def _search_lexical(self, query: str, documents: list[dict[str, str]], limit: int) -> list[dict[str, object]]:
        query_terms = self._tokenize(query)
        scored: list[dict[str, object]] = []
        for document in documents:
            haystack = ' '.join([document.get('title', ''), document.get('summary', ''), document.get('body', '')]).strip()
            hay_terms = self._tokenize(haystack)
            overlap = len(query_terms & hay_terms)
            if overlap <= 0 and query_terms:
                continue
            scored.append({
                'title': document.get('title', 'Documento'),
                'summary': document.get('summary', ''),
                'score': overlap / max(len(query_terms), 1),
                'source': document.get('source', document.get('title', 'Documento')),
                'search_mode': 'lexical',
            })
        return sorted(scored, key=lambda item: float(item['score']), reverse=True)[:limit]

    def describe_index(self) -> dict[str, object]:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        model = self._resolve_model()
        return {
            'knowledge_count': 0,
            'artifact_count': 0,
            'index_mode': 'semantic' if model else 'lexical-fallback',
            'primary_model': self.primary_model,
            'lightweight_model': self.lightweight_model,
            'last_query': '',
            'active_model': model or '',
        }

    def _extract_model_names(self, payload: object) -> set[str]:
        names: set[str] = set()
        if isinstance(payload, dict):
            for item in payload.get('data', []) or payload.get('models', []) or []:
                if isinstance(item, dict):
                    model_name = item.get('id') or item.get('name') or item.get('model')
                    if model_name:
                        names.add(str(model_name))
        return names

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r'[a-z0-9_]+', text.lower()) if len(token) > 2}

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
