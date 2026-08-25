"""Tests del MCPBridgeService (Capa 1: auto-arranque dentro del programa).

Verifica:
  - preferencia persistida (`enabled_pref`) sobrevive reinicios;
  - `ensure_started` es idempotente y respeta la preferencia;
  - `set_enabled(True)` arranca server + tunnel y publica URL;
  - `set_enabled(False)` detiene ambos y limpia URL;
  - governance gate: si el WorldModelSnapshot tiene un block para `mcp_bridge`
    (o global), el bridge NO arranca;
  - listeners reciben el estado en cada transición (stopped → starting → running);
  - si cloudflared no imprime URL antes del timeout, queda `failed` sin crashear.

Los colaboradores reales (`FastMCPServerRunner`, `CloudflaredTunnelRunner`) se
sustituyen por fakes inyectados; no se toca red, subprocesos ni FastMCP.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    NetworkStatusSnapshot,
    OperationalBlockRecord,
    WorldModelSnapshot,
)
from iabv_v15.services.evolution.mcp_bridge_service import (
    MCPBridgeService,
    MCPBridgeStatus,
)


class _FakeServerRunner:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.last_args: dict[str, object] | None = None

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        self.started += 1
        self.last_args = {"transport": transport, "host": host, "port": port}

        def _target() -> None:
            return None

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        self.stopped += 1


class _FakeTunnelRunner:
    def __init__(self, url: str | None = "https://fake-abc.trycloudflare.com", error: str | None = None) -> None:
        self._url = url
        self._error = error
        self.started = 0
        self.stopped = 0
        self._ready = threading.Event()
        if url:
            self._ready.set()

    def start(self, bind_host: str, bind_port: int) -> None:
        self.started += 1
        if self._url:
            self._ready.set()

    def stop(self) -> None:
        self.stopped += 1
        self._ready.clear()

    def wait_for_url(self, timeout_s: float) -> str | None:
        self._ready.wait(timeout=timeout_s)
        return self._url

    @property
    def url(self) -> str | None:
        return self._url

    @property
    def last_error(self) -> str | None:
        return self._error


class _FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot | None) -> None:
        self._snapshot = snapshot

    def current_model(self) -> WorldModelSnapshot | None:
        return self._snapshot


class _FakeContainer:
    def __init__(self, snapshot: WorldModelSnapshot | None = None) -> None:
        self.world_model_service = _FakeWorldModelService(snapshot) if snapshot is not None else None


def _default_snapshot(
    *,
    blocks: list[OperationalBlockRecord] | None = None,
) -> WorldModelSnapshot:
    return WorldModelSnapshot(
        external_state_flags=[],
        environment=EnvironmentSelfModel(),
        network_status=NetworkStatusSnapshot(connected=True, status="ok"),
        block_records=blocks or [],
    )


def _build_service(
    tmp_path: Path,
    *,
    tunnel_runner: _FakeTunnelRunner | None = None,
    snapshot: WorldModelSnapshot | None = None,
) -> tuple[MCPBridgeService, _FakeServerRunner, _FakeTunnelRunner]:
    server = _FakeServerRunner()
    tunnel = tunnel_runner or _FakeTunnelRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(snapshot or _default_snapshot()),
        workspace_root=tmp_path,
        server_runner=server,
        tunnel_runner=tunnel,
        tunnel_timeout_s=0.5,
    )
    return svc, server, tunnel


# ----------------------------------------------------------------------
# Preferencia persistida


def test_enabled_pref_starts_false_when_no_config(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    assert svc.status().enabled_pref is False
    assert svc.status().running is False


def test_set_enabled_persists_preference_across_instances(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    # Nueva instancia debe leer el archivo y arrancar con la preferencia.
    svc2, _, _ = _build_service(tmp_path)
    assert svc2.status().enabled_pref is True


def test_config_file_shape(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    config = tmp_path / "data" / "evolution" / "config" / "mcp_bridge.json"
    assert config.exists()
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data == {"enabled_pref": True}


# ----------------------------------------------------------------------
# Lifecycle


def test_set_enabled_true_starts_server_and_tunnel(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    status = svc.set_enabled(True)
    assert server.started == 1
    assert tunnel.started == 1
    assert status.running is True
    assert status.state == "running"
    assert status.tunnel_url == "https://fake-abc.trycloudflare.com"


def test_set_enabled_false_stops_server_and_tunnel(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.set_enabled(True)
    status = svc.set_enabled(False)
    assert tunnel.stopped == 1
    assert server.stopped == 1
    assert status.running is False
    assert status.state == "stopped"
    assert status.tunnel_url is None


def test_ensure_started_is_idempotent_when_already_running(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.set_enabled(True)
    # Un segundo ensure_started no debe re-arrancar nada.
    svc.ensure_started()
    assert server.started == 1
    assert tunnel.started == 1


def test_ensure_started_does_nothing_when_pref_false(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.ensure_started()
    assert server.started == 0
    assert tunnel.started == 0
    assert svc.status().state == "stopped"


# ----------------------------------------------------------------------
# Governance gate


def test_bridge_blocked_when_world_model_has_active_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="autonomy_disabled",
                assistant_kind="mcp_bridge",
                title="Autonomía externa desactivada por el usuario",
                status="active",
            ),
        ],
    )
    svc, server, tunnel = _build_service(tmp_path, snapshot=snapshot)
    status = svc.set_enabled(True)
    assert status.governance_blocked is True
    assert "Autonomía" in (status.governance_reason or "")
    assert server.started == 0
    assert tunnel.started == 0
    assert status.state == "failed"


def test_global_block_also_blocks_bridge(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="global_shutdown",
                assistant_kind="*",
                title="Sistema en modo seguro",
                status="active",
            ),
        ],
    )
    svc, server, _ = _build_service(tmp_path, snapshot=snapshot)
    svc.set_enabled(True)
    assert server.started == 0
    assert svc.status().governance_blocked is True


def test_block_for_unrelated_assistant_kind_does_not_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="cloudflare",
                assistant_kind="chatgpt_web",
                status="active",
            ),
        ],
    )
    svc, server, _ = _build_service(tmp_path, snapshot=snapshot)
    svc.set_enabled(True)
    assert server.started == 1
    assert svc.status().running is True


def test_inactive_block_does_not_stop_bridge(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="autonomy_disabled",
                assistant_kind="mcp_bridge",
                status="resolved",  # ya no está activo
            ),
        ],
    )
    svc, server, _ = _build_service(tmp_path, snapshot=snapshot)
    svc.set_enabled(True)
    assert server.started == 1


# ----------------------------------------------------------------------
# Observadores


def test_listeners_receive_initial_state_and_transitions(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    events: list[dict[str, object]] = []
    svc.attach_listener(lambda payload: events.append(dict(payload)))
    # El primer evento es el snapshot inicial (stopped, pref=False).
    assert events and events[0]["state"] == "stopped"
    events.clear()
    svc.set_enabled(True)
    states = [e["state"] for e in events]
    # starting -> running al menos (stopped puede no emitirse si pref ya era False).
    assert "starting" in states
    assert "running" in states


# ----------------------------------------------------------------------
# Errores del tunnel


def test_failed_tunnel_marks_status_failed_without_crashing(tmp_path: Path) -> None:
    tunnel = _FakeTunnelRunner(url=None, error="cloudflared not found")
    svc, server, _ = _build_service(tmp_path, tunnel_runner=tunnel)
    status = svc.set_enabled(True)
    assert status.running is False
    assert status.state == "failed"
    assert "cloudflared" in (status.last_error or "")
    # el server debe haberse intentado levantar y luego detenerse al fallar tunnel.
    assert server.started == 1


def test_tunnel_timeout_releases_server_and_tunnel_resources(tmp_path: Path) -> None:
    """Si wait_for_url() timeoutea, server + tunnel deben liberarse para permitir reintento.

    Sin esta limpieza, el proceso cloudflared seguiría vivo con el puerto ocupado
    y un reintento via set_enabled(True) quedaría en un estado irrecuperable.
    """

    tunnel = _FakeTunnelRunner(url=None, error=None)
    svc, server, _ = _build_service(tmp_path, tunnel_runner=tunnel)
    status = svc.set_enabled(True)
    assert status.state == "failed"
    assert "Timeout" in (status.last_error or "")
    assert server.started == 1
    assert server.stopped >= 1, "MCP server debe detenerse al timeout del tunnel"
    assert tunnel.stopped >= 1, "cloudflared debe detenerse al timeout del tunnel"


def test_block_for_empty_assistant_kind_does_not_block_bridge(tmp_path: Path) -> None:
    """`assistant_kind=""` es el default del modelo y se usa para condiciones
    operativas generales (network_slow, ram_pressure, focus_unresolved, etc.)
    que NO deben bloquear el MCP bridge. Sólo `*` o `mcp_bridge` bloquean.
    """

    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="network_slow",
                assistant_kind="",  # default para condiciones genéricas
                title="Red lenta detectada",
                status="active",
            ),
        ],
    )
    svc, server, _ = _build_service(tmp_path, snapshot=snapshot)
    status = svc.set_enabled(True)
    assert status.governance_blocked is False
    assert server.started == 1
    assert status.state == "running"


# ----------------------------------------------------------------------
# Shutdown


def test_shutdown_stops_bridge_without_touching_preference(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    svc.shutdown()
    status = svc.status()
    assert status.running is False
    # preferencia intacta: si el usuario habilitó, sigue habilitada para el próximo arranque.
    assert status.enabled_pref is True


def test_status_dict_is_serializable(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    payload = svc.status_dict()
    # round-trip JSON.
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["state"] == "stopped"
    assert round_tripped["transport"] in {"stdio", "sse", "streamable-http"}


def test_status_is_a_copy_not_internal_ref(tmp_path: Path) -> None:
    """status() devuelve MCPBridgeStatus nuevo para evitar mutaciones externas."""

    svc, _, _ = _build_service(tmp_path)
    s1 = svc.status()
    s1.state = "MUTATED"
    assert svc.status().state != "MUTATED"
    assert isinstance(s1, MCPBridgeStatus)


# ----------------------------------------------------------------------
# Transport / bind overrides


def test_service_passes_transport_and_bind_to_server_runner(tmp_path: Path) -> None:
    server = _FakeServerRunner()
    tunnel = _FakeTunnelRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        server_runner=server,
        tunnel_runner=tunnel,
        transport="sse",
        bind_host="0.0.0.0",
        bind_port=9123,
        tunnel_timeout_s=0.5,
    )
    svc.set_enabled(True)
    assert server.last_args == {"transport": "sse", "host": "0.0.0.0", "port": 9123}


def test_invalid_transport_falls_back_to_default(tmp_path: Path) -> None:
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        server_runner=_FakeServerRunner(),
        tunnel_runner=_FakeTunnelRunner(),
        transport="pigeon-carrier",  # no soportado
        tunnel_timeout_s=0.5,
    )
    assert svc.status().transport == "streamable-http"


# ----------------------------------------------------------------------
# Race: set_enabled(False) concurrente con start en vuelo
# Regresión del finding de Devin Review en PR #33


class _SlowTunnelRunner(_FakeTunnelRunner):
    """Tunnel fake que libera la URL sólo cuando un evento externo lo permite.

    Sirve para simular que `wait_for_url()` está colgado esperando a cloudflared
    mientras otro hilo llama `set_enabled(False)`.
    """

    def __init__(self, url: str = "https://slow.trycloudflare.com") -> None:
        super().__init__(url=url, error=None)
        self._ready.clear()

    def start(self, bind_host: str, bind_port: int) -> None:
        # NO auto-release the URL — el test la libera con release_url().
        self.started += 1

    def release_url(self) -> None:
        self._ready.set()

    def wait_for_url(self, timeout_s: float) -> str | None:
        self._ready.wait(timeout=timeout_s)
        return self._url if self._ready.is_set() else None


def test_concurrent_disable_during_start_leaves_bridge_stopped(tmp_path: Path) -> None:
    """Regresión del finding de Devin Review en PR #33.

    Escenario:
      1. Thread autostart llama `ensure_started()` → entra a `_start_locked()`
         → queda bloqueado en `wait_for_url()`.
      2. Thread toggle llama `set_enabled(False)` → persiste pref=False y
         entra a `_stop_locked()` tras el operation_lock.
      3. El tunnel publica URL después de (2) pero antes de que el start
         termine de commitear el estado.

    Resultado esperado: la intención del usuario (OFF) gana. El bridge queda
    `state=stopped`, `running=False`, `enabled_pref=False` y cloudflared
    detenido (no queda expuesto).
    """

    tunnel = _SlowTunnelRunner()
    svc, server, _ = _build_service(tmp_path, tunnel_runner=tunnel)
    svc.set_enabled(True)  # persiste pref y arranca sincrónicamente
    # Reset al estado "start en vuelo": como el test anterior no bloquea, usamos
    # otro flow. Simulamos una nueva operación donde el disable llega mientras
    # el start está esperando URL.
    tunnel._ready.clear()
    tunnel._url = "https://slow.trycloudflare.com"

    # Relanza un start (que se quedará esperando release_url).
    start_done = threading.Event()
    start_status: dict[str, MCPBridgeStatus] = {}

    def _start_worker() -> None:
        start_status["s"] = svc.ensure_started()
        start_done.set()

    threading.Thread(target=_start_worker, daemon=True, name="test-start").start()

    # Esperamos un poco para que el thread entre a _start_locked y quede en wait_for_url.
    # El lock de operación no está disponible para set_enabled(False) hasta que start termine.
    import time
    time.sleep(0.05)

    # Mientras start está en vuelo, persistimos pref=False. El stop queda bloqueado
    # esperando el operation_lock; liberamos la URL para que el start commitee.
    def _disable_worker() -> None:
        svc.set_enabled(False)

    disable_thread = threading.Thread(target=_disable_worker, daemon=True, name="test-disable")
    disable_thread.start()
    time.sleep(0.05)  # let set_enabled persist pref before we release the URL
    tunnel.release_url()

    assert start_done.wait(timeout=3.0), "start thread nunca terminó"
    disable_thread.join(timeout=3.0)

    final = svc.status()
    assert final.enabled_pref is False, "la intención del usuario (OFF) debe ganar"
    assert final.running is False, "bridge NO debe quedar running tras disable concurrente"
    assert final.state == "stopped", f"estado final debe ser stopped, no {final.state}"
    # cloudflared debe estar detenido (no expuesto) — al menos una vez por el
    # teardown de _start_locked o por el _stop_locked.
    assert tunnel.stopped >= 1, "cloudflared debe detenerse tras el race"
    assert server.stopped >= 1, "MCP server debe detenerse tras el race"


def test_stop_serialized_after_start_in_flight(tmp_path: Path) -> None:
    """Si un stop llega durante un start en vuelo, el operation_lock los serializa.

    La métrica clave: ambos completan sin crash y el estado final es coherente
    con el último intent (disable → stopped).
    """

    tunnel = _SlowTunnelRunner()
    svc, _, _ = _build_service(tmp_path, tunnel_runner=tunnel)
    svc._status.enabled_pref = True  # fuerza pref ON para disparar ensure_started
    svc._persist_enabled_preference(True)

    start_done = threading.Event()

    def _start_worker() -> None:
        svc.ensure_started()
        start_done.set()

    threading.Thread(target=_start_worker, daemon=True).start()

    import time
    time.sleep(0.05)
    # stop() debería quedar esperando el operation_lock hasta que start termine.
    stop_done = threading.Event()

    def _stop_worker() -> None:
        svc.stop()
        stop_done.set()

    threading.Thread(target=_stop_worker, daemon=True).start()
    time.sleep(0.05)
    # stop aún no debe haber completado (está esperando el operation_lock).
    assert not stop_done.is_set(), "stop() no debe poder ejecutar mientras start tiene el operation_lock"

    tunnel.release_url()
    assert start_done.wait(timeout=3.0)
    assert stop_done.wait(timeout=3.0)

    final = svc.status()
    assert final.running is False
    assert final.state == "stopped"


if __name__ == "__main__":  # pragma: no cover - debugging helper
    pytest.main([__file__, "-q"])
