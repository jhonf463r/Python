"""ProviderHealthRouter: poll periodico de salud de proveedores externos/locales.

Cada probe describe un endpoint (Ollama /api/tags, embeddings, asistentes). El
router expone snapshot() (sincronico, util en tests) y start_polling(interval_s)
(hilo demonio). Emite providerHealthChanged con lista de dicts:
    {name, status (verde|amarillo|rojo|gris), latency_ms, detail}.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:  # pragma: no cover - httpx disponible en runtime del proyecto
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


HealthListener = Callable[[list[dict]], None]
ClientFactory = Callable[[float], Any]
Clock = Callable[[], float]


STATUS_COLOR_MAP: dict[str, str] = {
    "ready": "verde",
    "available": "verde",
    "green": "verde",
    "degraded": "amarillo",
    "warning": "amarillo",
    "yellow": "amarillo",
    "optional_inactive": "gris",
    "idle": "gris",
    "gray": "gris",
    "unavailable": "rojo",
    "error": "rojo",
    "failed": "rojo",
    "red": "rojo",
}


@dataclass
class ProviderProbe:
    name: str
    url: str
    timeout_s: float = 3.0
    optional: bool = False
    expect_status: int = 200
    detail_ok: str = "Disponible."
    headers: dict[str, str] = field(default_factory=dict)


class ProviderHealthRouter:
    def __init__(
        self,
        *,
        probes: list[ProviderProbe] | None = None,
        client_factory: ClientFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._probes: list[ProviderProbe] = list(probes or [])
        self._client_factory = client_factory or self._default_client_factory
        self._clock: Clock = clock or time.perf_counter
        self._listener: Optional[HealthListener] = None
        self._lock = threading.RLock()
        self._last_snapshot: list[dict] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ---- public API -------------------------------------------------

    def register_probe(self, probe: ProviderProbe) -> None:
        with self._lock:
            self._probes.append(probe)

    def register_health_listener(self, listener: HealthListener) -> None:
        with self._lock:
            self._listener = listener

    def snapshot(self) -> list[dict]:
        with self._lock:
            probes = list(self._probes)
        results = [self._probe_one(probe) for probe in probes]
        with self._lock:
            self._last_snapshot = list(results)
            listener = self._listener
        if listener is not None:
            listener(list(results))
        return results

    def last_snapshot(self) -> list[dict]:
        with self._lock:
            return list(self._last_snapshot)

    def start_polling(self, interval_s: float = 30.0) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _run() -> None:
            while not self._stop_event.is_set():
                try:
                    self.snapshot()
                except Exception:
                    # Silenciado a proposito: los errores de cada probe ya se
                    # traducen a status rojo dentro de _probe_one.
                    pass
                if self._stop_event.wait(interval_s):
                    return

        thread = threading.Thread(target=_run, name="ProviderHealthRouter", daemon=True)
        self._thread = thread
        thread.start()

    def stop_polling(self, timeout_s: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout_s)
        self._thread = None

    # ---- internals --------------------------------------------------

    def _probe_one(self, probe: ProviderProbe) -> dict:
        start = self._clock()
        try:
            client = self._client_factory(probe.timeout_s)
            try:
                response = client.get(probe.url, headers=probe.headers)
                status_code = getattr(response, "status_code", None)
                if status_code is not None and status_code != probe.expect_status:
                    raise RuntimeError(f"HTTP {status_code}")
            finally:
                closer = getattr(client, "close", None)
                if closer is not None:
                    try:
                        closer()
                    except Exception:
                        pass
            latency_ms = round((self._clock() - start) * 1000, 2)
            return {
                "name": probe.name,
                "status": STATUS_COLOR_MAP["ready"],
                "latency_ms": latency_ms,
                "detail": probe.detail_ok,
            }
        except Exception as exc:
            latency_ms = round((self._clock() - start) * 1000, 2)
            status = STATUS_COLOR_MAP["degraded"] if probe.optional else STATUS_COLOR_MAP["unavailable"]
            return {
                "name": probe.name,
                "status": status,
                "latency_ms": latency_ms,
                "detail": str(exc) or "Sin respuesta",
            }

    def _default_client_factory(self, timeout_s: float):
        if httpx is None:  # pragma: no cover - dependencia declarada en pyproject
            raise RuntimeError("httpx no esta instalado")
        return httpx.Client(timeout=timeout_s)


def default_local_probes(
    *,
    ollama_base_url: str = "http://127.0.0.1:11434",
    embeddings_base_url: str | None = "http://127.0.0.1:11434",
    external_assistant_urls: dict[str, str] | None = None,
) -> list[ProviderProbe]:
    """Probes por defecto: Ollama + embeddings + asistentes externos configurados."""
    probes: list[ProviderProbe] = [
        ProviderProbe(
            name="ollama",
            url=f"{ollama_base_url.rstrip('/')}/api/tags",
            optional=False,
            detail_ok="Ollama responde /api/tags.",
        )
    ]
    if embeddings_base_url:
        probes.append(
            ProviderProbe(
                name="embeddings",
                url=f"{embeddings_base_url.rstrip('/')}/api/embeddings",
                optional=True,
                detail_ok="Servicio de embeddings disponible.",
            )
        )
    for name, url in (external_assistant_urls or {}).items():
        probes.append(
            ProviderProbe(
                name=name,
                url=url,
                optional=True,
                detail_ok=f"{name} responde.",
            )
        )
    return probes
