"""Tests del perfil local-only de MCPBridgeService.

Verifica preferencias, lifecycle, governance fail-closed, loopback binding y
que no sea posible inyectar un túnel público mientras el perfil remoto
autenticado no esté implementado. Los runners son fakes; no se toca red,
subprocesos ni FastMCP.
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
from iabv_v15.services.security.read_authorization import ReadAuthorizationCoordinator
from iabv_v15.services.evolution.mcp_bridge_service import (
    CloudflaredTunnelRunner,
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


def _dependency_only_test_coordinator() -> ReadAuthorizationCoordinator:
    """Test sentinels are dependency presence only, never startup authority."""

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
        _dependency_only_test_coordinator()
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
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


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
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


def test_bridge_stays_stopped_without_approved_workspace_root_provider(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc._container.approved_workspace_root_provider = None

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


def test_bridge_stays_stopped_with_invalid_approved_workspace_root_provider(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc._container.approved_workspace_root_provider = object()

    status = svc.set_enabled(True)

    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_blocked is True
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


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


def test_set_enabled_true_is_denied_without_established_start_authority(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    status = svc.set_enabled(True)
    assert server.started == 0
    assert tunnel.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"
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


def test_ensure_started_cannot_start_with_dependency_only_fixtures(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.set_enabled(True)
    svc.ensure_started()
    svc.ensure_started()
    assert server.started == 0
    assert tunnel.started == 0
    assert svc.status().governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


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
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"
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


def test_block_for_unrelated_assistant_kind_does_not_override_missing_start_authority(tmp_path: Path) -> None:
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
    assert server.started == 0
    assert svc.status().running is False
    assert svc.status().governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


def test_inactive_block_does_not_establish_start_authority(tmp_path: Path) -> None:
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
    assert server.started == 0
    assert svc.status().governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


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
    assert "failed" in states
    assert "starting" not in states
    assert "running" not in states


# ----------------------------------------------------------------------
# R-07 transport profile: public tunneling is not configured


def test_public_tunnel_injection_is_rejected_until_remote_profile_exists(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="R07_REMOTE_TUNNEL_PROFILE_NOT_IMPLEMENTED"):
        MCPBridgeService(
            container=_FakeContainer(_default_snapshot()),
            workspace_root=tmp_path,
            read_authorization_coordinator=_dependency_only_test_coordinator(),
            server_runner=_FakeServerRunner(),
            tunnel_runner=_FakeTunnelRunner(),
        )


def test_direct_cloudflared_runner_start_is_denied_before_popen(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from iabv_v15.services.evolution import mcp_bridge_service as bridge_module

    popen_calls: list[object] = []
    monkeypatch.setattr(
        bridge_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )
    runner = CloudflaredTunnelRunner()

    with pytest.raises(RuntimeError, match="MCP_TUNNEL_AUTHORIZATION_NOT_ESTABLISHED"):
        runner.start("127.0.0.1", 8765)
    assert popen_calls == []


def test_common_sense_tunnel_action_is_denied_before_popen(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from iabv_v15.services import common_sense_engine

    popen_calls: list[object] = []
    monkeypatch.setattr(
        common_sense_engine.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    result = common_sense_engine._exec_start_tunnel({})

    assert result == {
        "executed": False,
        "blocked_by_policy": True,
        "reason": "G1_G2_G3_NOT_ESTABLISHED",
    }
    assert popen_calls == []


def test_non_loopback_bind_host_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="R07_LOCAL_ONLY_BIND_HOST_MUST_BE_LOOPBACK"):
        MCPBridgeService(
            container=_FakeContainer(_default_snapshot()),
            workspace_root=tmp_path,
            read_authorization_coordinator=_dependency_only_test_coordinator(),
            server_runner=_FakeServerRunner(),
            bind_host="0.0.0.0",
        )


def test_block_for_empty_assistant_kind_does_not_establish_start_authority(tmp_path: Path) -> None:
    """Generic world-model records do not replace the missing start authority."""

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
    assert status.governance_blocked is True
    assert server.started == 0
    assert status.state == "failed"
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


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


def test_dependency_only_coordinator_does_not_reach_server_runner(tmp_path: Path) -> None:
    server = _FakeServerRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(_default_snapshot()),
        workspace_root=tmp_path,
        read_authorization_coordinator=_dependency_only_test_coordinator(),
        server_runner=server,
        transport="sse",
        bind_host="127.0.0.1",
        bind_port=9123,
    )
    status = svc.set_enabled(True)
    assert server.last_args is None
    assert server.started == 0
    assert status.governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


def test_direct_server_runner_denies_before_env_or_thread(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from iabv_v15.services.evolution import mcp_bridge_service as bridge_module

    monkeypatch.setenv("FASTMCP_HOST", "unchanged-host")
    monkeypatch.setenv("FASTMCP_PORT", "1234")
    thread_calls: list[object] = []
    monkeypatch.setattr(
        bridge_module.threading,
        "Thread",
        lambda *args, **kwargs: thread_calls.append((args, kwargs)),
    )
    runner = FastMCPServerRunner(_FakeContainer())

    with pytest.raises(RuntimeError, match="MCP_START_AUTHORIZATION_NOT_ESTABLISHED"):
        runner.run_threaded("stdio", "127.0.0.1", 8765)
    assert thread_calls == []
    assert bridge_module.os.environ["FASTMCP_HOST"] == "unchanged-host"
    assert bridge_module.os.environ["FASTMCP_PORT"] == "1234"


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


def test_concurrent_disable_candidate_cannot_reach_server_runner(tmp_path: Path) -> None:
    svc, server, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    assert server.started == 0
    assert svc.status().governance_reason == "G1_G2_G3_NOT_ESTABLISHED"


def test_stop_after_denied_start_keeps_bridge_stopped(tmp_path: Path) -> None:
    svc, server, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    svc.stop()
    assert server.started == 0
    assert svc.status().running is False


if __name__ == "__main__":  # pragma: no cover - debugging helper
    pytest.main([__file__, "-q"])
