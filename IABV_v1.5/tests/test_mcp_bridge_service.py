"""Tests del perfil local-only de MCPBridgeService.

Verifica preferencias, lifecycle, governance fail-closed, loopback binding y
que no sea posible inyectar un túnel público mientras el perfil remoto
autenticado no esté implementado. Los runners son fakes; no se toca red,
subprocesos ni FastMCP.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    NetworkStatusSnapshot,
    OperationalBlockRecord,
    WorldModelSnapshot,
)
from iabv_v15.services.security.read_authorization import ReadAuthorizationCoordinator
from iabv_v15.services.evolution.mcp_bridge_service import (
    FastMCPServerRunner,
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


class _PresenceOnlyRootProvider:
    """Dependency-presence sentinel; it never supplies an approved root."""

    def current_workspace_root(self) -> None:
        raise AssertionError("bridge startup preflight must not resolve or open a workspace root")


class _FakeContainer:
    def __init__(self, snapshot: WorldModelSnapshot | None = None) -> None:
        self.world_model_service = _FakeWorldModelService(snapshot) if snapshot is not None else None
        self.approved_workspace_root_provider = _PresenceOnlyRootProvider()


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


_USE_TEST_COORDINATOR = object()


def _fully_wired_test_coordinator() -> ReadAuthorizationCoordinator:
    """Satisfy the dependency-presence preflight only; never used to authorize a read."""

    return ReadAuthorizationCoordinator(
        trust_provider=object(),  # type: ignore[arg-type]
        mandate_provider=object(),  # type: ignore[arg-type]
        merge_evidence_provider=object(),  # type: ignore[arg-type]
        policy_provider=object(),  # type: ignore[arg-type]
        target_resolver=object(),  # type: ignore[arg-type]
        issuer_client=object(),  # type: ignore[arg-type]
        replay_consumer=object(),  # type: ignore[arg-type]
        request_context_provider=object(),  # type: ignore[arg-type]
    )


def _build_service(
    tmp_path: Path,
    *,
    snapshot: WorldModelSnapshot | None = None,
    read_authorization_coordinator: object = _USE_TEST_COORDINATOR,
) -> tuple[MCPBridgeService, _FakeServerRunner, _FakeTunnelRunner]:
    server = _FakeServerRunner()
    # Sentinel only: the service does not receive or start a tunnel runner.
    tunnel = _FakeTunnelRunner()
    coordinator = (
        _fully_wired_test_coordinator()
        if read_authorization_coordinator is _USE_TEST_COORDINATOR
        else read_authorization_coordinator
    )
    svc = MCPBridgeService(
        container=_FakeContainer(snapshot or _default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=coordinator,
        server_runner=server,
    )
    return svc, server, tunnel

# ----------------------------------------------------------------------
# Preferencia persistida


def test_bridge_stays_stopped_without_read_authorization_coordinator(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path, read_authorization_coordinator=None)

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason == "AUTHORIZATION_COORDINATOR_UNAVAILABLE"


def test_bridge_stays_stopped_when_authorization_coordinator_is_unconfigured(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(
        tmp_path,
        read_authorization_coordinator=ReadAuthorizationCoordinator.unconfigured(),
    )

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason is not None
    assert status.governance_reason.startswith("AUTHORIZATION_PREREQUISITES_MISSING:")
    assert "INDEPENDENT_TRUST_ROOT_PROVIDER" in status.governance_reason


def test_bridge_stays_stopped_without_approved_workspace_root_provider(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc._container.approved_workspace_root_provider = None

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason == "APPROVED_WORKSPACE_ROOT_PROVIDER_UNAVAILABLE"


def test_bridge_stays_stopped_with_invalid_approved_workspace_root_provider(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc._container.approved_workspace_root_provider = object()

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason == "APPROVED_WORKSPACE_ROOT_PROVIDER_INVALID"


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


def test_set_enabled_true_starts_local_server_without_public_tunnel(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    status = svc.set_enabled(True)
    assert server.started == 1
    assert tunnel.started == 0
    assert status.running is True
    assert status.state == "running"
    assert status.tunnel_url is None
    assert status.bind_host == "127.0.0.1"


def test_set_enabled_false_stops_local_server_without_tunnel(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.set_enabled(True)
    status = svc.set_enabled(False)
    assert tunnel.started == 0
    assert tunnel.stopped == 0
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
    assert tunnel.started == 0


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
# R-07 transport profile: public tunneling is not configured


def test_public_tunnel_injection_is_rejected_until_remote_profile_exists(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="R07_REMOTE_TUNNEL_PROFILE_NOT_IMPLEMENTED"):
        MCPBridgeService(
            container=_FakeContainer(_default_snapshot()),
            workspace_root=tmp_path,
            read_authorization_coordinator=_fully_wired_test_coordinator(),
            server_runner=_FakeServerRunner(),
            tunnel_runner=_FakeTunnelRunner(),
        )


def test_non_loopback_bind_host_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="R07_LOCAL_ONLY_BIND_HOST_MUST_BE_LOOPBACK"):
        MCPBridgeService(
            container=_FakeContainer(_default_snapshot()),
            workspace_root=tmp_path,
            read_authorization_coordinator=_fully_wired_test_coordinator(),
            server_runner=_FakeServerRunner(),
            bind_host="0.0.0.0",
        )


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


def test_service_passes_transport_and_loopback_bind_to_server_runner(tmp_path: Path) -> None:
    server = _FakeServerRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=_fully_wired_test_coordinator(),
        server_runner=server,
        transport="sse",
        bind_host="127.0.0.1",
        bind_port=9123,
    )
    svc.set_enabled(True)
    assert server.last_args == {"transport": "sse", "host": "127.0.0.1", "port": 9123}


def test_mcp_bridge_passes_registered_read_authority_explicitly_to_server(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from iabv_v15.infra.mcp import server as server_module

    coordinator = object()
    service = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=coordinator,
    )
    assert type(service._server_runner) is FastMCPServerRunner
    assert service._server_runner._read_authorization_coordinator is coordinator

    captured: dict[str, object] = {}

    class _Server:
        def __init__(self, container, *, read_authorization_coordinator):
            captured["container"] = container
            captured["coordinator"] = read_authorization_coordinator

    monkeypatch.setattr(server_module, "IABVMCPServer", _Server, raising=False)
    service._server_runner._build_server()
    assert captured == {
        "container": service._container,
        "coordinator": coordinator,
    }


def test_invalid_transport_falls_back_to_default(tmp_path: Path) -> None:
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        server_runner=_FakeServerRunner(),
        transport="pigeon-carrier",  # no soportado
    )
    assert svc.status().transport == "streamable-http"


# ----------------------------------------------------------------------
# Race: set_enabled(False) concurrente con server start en vuelo


class _SlowServerRunner(_FakeServerRunner):
    """Runner de prueba que permite observar el toggle OFF durante el start."""

    def __init__(self) -> None:
        super().__init__()
        self.start_entered = threading.Event()
        self.release_start = threading.Event()

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        self.start_entered.set()
        if not self.release_start.wait(timeout=3.0):
            raise TimeoutError("test did not release local server start")
        return super().run_threaded(transport, host, port)


def test_concurrent_disable_during_local_start_leaves_bridge_stopped(tmp_path: Path) -> None:
    server = _SlowServerRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=_fully_wired_test_coordinator(),
        server_runner=server,
    )
    start_done = threading.Event()
    disable_done = threading.Event()

    def _start_worker() -> None:
        svc.set_enabled(True)
        start_done.set()

    threading.Thread(target=_start_worker, daemon=True, name="test-local-start").start()
    assert server.start_entered.wait(timeout=1.0), "server start did not begin"

    def _disable_worker() -> None:
        svc.set_enabled(False)
        disable_done.set()

    threading.Thread(target=_disable_worker, daemon=True, name="test-local-disable").start()
    deadline = time.monotonic() + 2.0
    while svc.status().enabled_pref and time.monotonic() < deadline:
        time.sleep(0.005)
    assert svc.status().enabled_pref is False, "OFF preference was not persisted during start"
    assert not disable_done.is_set(), "disable should wait on the in-flight start operation"
    server.release_start.set()

    assert start_done.wait(timeout=3.0), "start thread never completed"
    assert disable_done.wait(timeout=3.0), "disable thread never completed"
    final = svc.status()
    assert final.enabled_pref is False
    assert final.running is False
    assert final.state == "stopped"
    assert server.started == 1
    assert server.stopped >= 1


def test_stop_serialized_after_local_start_in_flight(tmp_path: Path) -> None:
    server = _SlowServerRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=_fully_wired_test_coordinator(),
        server_runner=server,
    )
    svc._status.enabled_pref = True
    svc._persist_enabled_preference(True)
    start_done = threading.Event()
    stop_entered = threading.Event()
    stop_done = threading.Event()

    def _start_worker() -> None:
        svc.ensure_started()
        start_done.set()

    threading.Thread(target=_start_worker, daemon=True, name="test-local-start").start()
    assert server.start_entered.wait(timeout=1.0), "server start did not begin"

    def _stop_worker() -> None:
        stop_entered.set()
        svc.stop()
        stop_done.set()

    threading.Thread(target=_stop_worker, daemon=True, name="test-local-stop").start()
    assert stop_entered.wait(timeout=1.0), "stop thread did not start"
    assert not stop_done.is_set(), "stop should wait while start owns the operation lock"
    server.release_start.set()

    assert start_done.wait(timeout=3.0)
    assert stop_done.wait(timeout=3.0)
    final = svc.status()
    assert final.running is False
    assert final.state == "stopped"
    assert server.stopped >= 1


if __name__ == "__main__":  # pragma: no cover - debugging helper
    pytest.main([__file__, "-q"])
