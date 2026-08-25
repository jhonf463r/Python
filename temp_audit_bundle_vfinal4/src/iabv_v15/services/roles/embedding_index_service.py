from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Iterable

from iabv_v15.domain.models import ProviderHealth, ProviderStatus

try:  # pragma: no cover - optional import in runtime
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


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
        self._health_cache: ProviderHealth | None = None
        self._health_cached_at: float = 0.0
        self._health_lock = threading.Lock()
        self._HEALTH_TTL: float = 30.0

    def refresh_metadata(self, *, knowledge_count: int, artifact_count: int, last_query: str = '') -> dict[str, object]:
        payload = {
            'knowledge_count': knowledge_count,
            'artifact_count': artifact_count,
            'index_mode': 'lexical-fallback',
            'primary_model': self.primary_model,
            'lightweight_model': self.lightweight_model,
            'last_query': last_query,
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return payload

    def health_check(self, *, max_age_seconds: float | None = None) -> ProviderHealth:
        """Check embedding provider health, with optional TTL cache.

        When *max_age_seconds* is ``None`` (default) the instance-level
        ``_HEALTH_TTL`` (30 s) is used.  Pass ``0`` to force a fresh HTTP
        probe — this is what explicit user-initiated refreshes should do.
        """
        ttl = self._HEALTH_TTL if max_age_seconds is None else max(float(max_age_seconds), 0.0)
        if ttl > 0.0:
            with self._health_lock:
                if self._health_cache is not None and (time.monotonic() - self._health_cached_at) <= ttl:
                    return self._health_cache.model_copy(deep=True)
        result = self._probe_health()
        with self._health_lock:
            self._health_cache = result
            self._health_cached_at = time.monotonic()
        return result

    def _probe_health(self) -> ProviderHealth:
        """Perform the actual HTTP probe against the Ollama ``/models`` endpoint."""
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
            return ProviderHealth(
                provider_name='Embeddings',
                status=ProviderStatus.READY,
                available=True,
                latency_ms=latency_ms,
                detail=f'Indexado local listo con {preferred}.',
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
            })
        return sorted(scored, key=lambda item: float(item['score']), reverse=True)[:limit]

    def describe_index(self) -> dict[str, object]:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        return {
            'knowledge_count': 0,
            'artifact_count': 0,
            'index_mode': 'lexical-fallback',
            'primary_model': self.primary_model,
            'lightweight_model': self.lightweight_model,
            'last_query': '',
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
