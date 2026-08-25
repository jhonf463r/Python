from __future__ import annotations

from iabv_v15.services.providers.provider_health_router import (
    ProviderHealthRouter,
    ProviderProbe,
    default_local_probes,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, *, response: _FakeResponse | Exception) -> None:
        self._response = response
        self.closed = False
        self.get_calls: list[tuple[str, dict]] = []

    def get(self, url, headers=None):
        self.get_calls.append((url, dict(headers or {})))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    def close(self) -> None:
        self.closed = True


def _factory_returning(clients: list[_FakeClient]):
    iterator = iter(clients)

    def factory(timeout_s: float):
        return next(iterator)

    return factory


def test_snapshot_green_when_ollama_responds() -> None:
    probes = [ProviderProbe(name="ollama", url="http://127.0.0.1:11434/api/tags")]
    client = _FakeClient(response=_FakeResponse(200))
    router = ProviderHealthRouter(
        probes=probes, client_factory=_factory_returning([client])
    )

    snapshot = router.snapshot()

    assert snapshot[0]["name"] == "ollama"
    assert snapshot[0]["status"] == "verde"
    assert snapshot[0]["latency_ms"] is not None
    assert client.closed is True


def test_snapshot_red_when_probe_fails() -> None:
    probes = [ProviderProbe(name="ollama", url="http://127.0.0.1:11434/api/tags")]
    client = _FakeClient(response=RuntimeError("conn refused"))
    router = ProviderHealthRouter(
        probes=probes, client_factory=_factory_returning([client])
    )

    snapshot = router.snapshot()

    assert snapshot[0]["status"] == "rojo"
    assert "conn refused" in snapshot[0]["detail"]


def test_optional_probe_maps_to_yellow_on_failure() -> None:
    probes = [
        ProviderProbe(
            name="embeddings",
            url="http://127.0.0.1:11434/api/embeddings",
            optional=True,
        )
    ]
    client = _FakeClient(response=RuntimeError("nope"))
    router = ProviderHealthRouter(
        probes=probes, client_factory=_factory_returning([client])
    )

    snapshot = router.snapshot()
    assert snapshot[0]["status"] == "amarillo"


def test_snapshot_emits_to_listener() -> None:
    probes = [ProviderProbe(name="ollama", url="http://127.0.0.1:11434/api/tags")]
    client = _FakeClient(response=_FakeResponse(200))
    router = ProviderHealthRouter(
        probes=probes, client_factory=_factory_returning([client])
    )
    received: list[list[dict]] = []
    router.register_health_listener(received.append)

    router.snapshot()

    assert received
    assert received[0][0]["name"] == "ollama"
    assert received[0][0]["status"] == "verde"


def test_default_local_probes_includes_ollama_tags() -> None:
    probes = default_local_probes(
        ollama_base_url="http://127.0.0.1:11434",
        embeddings_base_url="http://127.0.0.1:11434",
        external_assistant_urls={"chatgpt": "https://chat.openai.com/"},
    )
    names = [p.name for p in probes]
    assert "ollama" in names
    assert "embeddings" in names
    assert "chatgpt" in names
    ollama = next(p for p in probes if p.name == "ollama")
    assert ollama.url.endswith("/api/tags")
    assert ollama.optional is False
    embeddings = next(p for p in probes if p.name == "embeddings")
    assert embeddings.optional is True


def test_start_and_stop_polling_runs_at_least_once() -> None:
    probes = [ProviderProbe(name="ollama", url="http://127.0.0.1:11434/api/tags")]
    clients = [_FakeClient(response=_FakeResponse(200)) for _ in range(5)]
    router = ProviderHealthRouter(
        probes=probes, client_factory=_factory_returning(clients)
    )

    router.start_polling(interval_s=0.05)
    # Esperar al menos una iteracion.
    import time

    time.sleep(0.1)
    router.stop_polling(timeout_s=1.0)

    last = router.last_snapshot()
    assert last and last[0]["status"] == "verde"
