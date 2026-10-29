"""Contract tests for the MCP bridge's current fail-closed profile.

Public-tunnel startup is intentionally disabled in this tranche. Lifecycle
success, tunnel URL publication, and start/stop race tests belong to a future
explicitly authorized local-only profile and must not simulate a permissive
alternate tunnel runner in this code path.
"""
from __future__ import annotations

import json
import os
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
    CloudflaredTunnelRunner,
    FastMCPServerRunner,
    MCPBridgeService,
)


class _FakeServerRunner:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        self.started += 1
        thread = threading.Thread(target=lambda: None, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self.stopped += 1


class _UnsafeInjectedTunnelRunner:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self, bind_host: str, bind_port: int) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1

    def wait_for_url(self, timeout_s: float) -> str | None:
        return "https://unexpected.example"


class _FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot | None) -> None:
        self._snapshot = snapshot

    def current_model(self) -> WorldModelSnapshot | None:
        return self._snapshot


class _FakeContainer:
    def __init__(self, snapshot: WorldModelSnapshot | None = None) -> None:
        self.world_model_service = _FakeWorldModelService(snapshot) if snapshot is not None else None


def _default_snapshot(*, blocks: list[OperationalBlockRecord] | None = None) -> WorldModelSnapshot:
    return WorldModelSnapshot(
        external_state_flags=[],
        environment=EnvironmentSelfModel(),
        network_status=NetworkStatusSnapshot(connected=True, status="ok"),
        block_records=blocks or [],
    )


def _build_service(
    tmp_path: Path,
    *,
    snapshot: WorldModelSnapshot | None = None,
    server_runner: _FakeServerRunner | None = None,
) -> tuple[MCPBridgeService, _FakeServerRunner]:
    server = server_runner or _FakeServerRunner()
    service = MCPBridgeService(
        container=_FakeContainer(snapshot if snapshot is not None else _default_snapshot()),
        workspace_root=tmp_path,
        server_runner=server,
    )
    return service, server


def test_server_runner_passes_the_same_sealed_preflight_to_server(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    marker = object()
    seen: list[object] = []

    def preflight(transport: str, *, bind_host: str, bind_port: int) -> object:
        assert (transport, bind_host, bind_port) == ("streamable-http", "127.0.0.1", 8000)
        return marker

    class FakeServer:
        def __init__(self, container: object, *, _startup_preflight: object) -> None:
            seen.append(_startup_preflight)

        def validate_transport_configuration(self, transport: str) -> None:
            assert transport == "streamable-http"

        def run(self, *, transport: str) -> None:
            raise AssertionError("thread target is not executed by this source contract test")

    class FakeThread:
        def __init__(self, *, target, name: str, daemon: bool) -> None:  # type: ignore[no-untyped-def]
            self.target = target
            self.name = name
            self.daemon = daemon
            self.started = False

        def start(self) -> None:
            self.started = True

    server_module = types.ModuleType("iabv_v15.infra.mcp.server")
    server_module.IABVMCPServer = FakeServer
    server_module.preflight_mcp_startup_configuration = preflight
    monkeypatch.setitem(sys.modules, "iabv_v15.infra.mcp.server", server_module)
    monkeypatch.setattr(threading, "Thread", FakeThread)

    runner = FastMCPServerRunner(_FakeContainer())
    thread = runner.run_threaded("streamable-http", "127.0.0.1", 8000)
    assert seen == [marker]
    assert thread.started is True


def test_server_runner_rejects_invalid_preflight_before_starting_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FastMCPServerRunner(_FakeContainer())
    monkeypatch.setenv("FASTMCP_HOST", "unchanged-host")
    monkeypatch.setenv("FASTMCP_PORT", "8765")

    def forbidden_thread_start(self: threading.Thread) -> None:
        pytest.fail("invalid MCP configuration must be rejected before a thread starts")

    monkeypatch.setattr(threading.Thread, "start", forbidden_thread_start)
    with pytest.raises(RuntimeError, match="127.0.0.1:8000"):
        runner.run_threaded("streamable-http", "0.0.0.0", 8000)
    assert runner._server is None
    assert os.environ["FASTMCP_HOST"] == "unchanged-host"
    assert os.environ["FASTMCP_PORT"] == "8765"


def test_production_cloudflared_runner_is_disabled_without_spawning_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_popen(*args: object, **kwargs: object) -> object:
        pytest.fail("public tunnel process must not be created in this phase")

    monkeypatch.setattr("iabv_v15.services.evolution.mcp_bridge_service.subprocess.Popen", forbidden_popen)
    runner = CloudflaredTunnelRunner(cloudflared_bin="cloudflared")
    runner.start("127.0.0.1", 8000)
    assert runner.last_error == "public_tunnel_disabled_by_policy"
    assert runner.url is None


def test_production_bridge_is_blocked_before_starting_server(tmp_path: Path) -> None:
    server = _FakeServerRunner()
    service, _ = _build_service(tmp_path, server_runner=server)
    status = service.set_enabled(True)
    assert server.started == 0
    assert status.running is False
    assert status.state == "failed"
    assert status.last_error == "public_tunnel_disabled_by_policy; bridge remains not ready"


def test_injected_tunnel_runner_is_rejected_at_construction(tmp_path: Path) -> None:
    server = _FakeServerRunner()
    tunnel = _UnsafeInjectedTunnelRunner()
    with pytest.raises(ValueError, match="public_tunnel_runner_injection_disabled_by_policy"):
        MCPBridgeService(
            container=_FakeContainer(_default_snapshot()),
            workspace_root=tmp_path,
            server_runner=server,
            tunnel_runner=tunnel,
        )
    assert tunnel.started == 0
    assert tunnel.stopped == 0
    assert server.started == 0


def test_enabled_pref_starts_false_when_no_config(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    assert service.status().enabled_pref is False
    assert service.status().running is False


def test_set_enabled_persists_preference_across_instances(tmp_path: Path) -> None:
    service, server = _build_service(tmp_path)
    status = service.set_enabled(True)
    assert status.state == "failed"
    assert status.enabled_pref is True
    assert server.started == 0

    service2, _ = _build_service(tmp_path)
    assert service2.status().enabled_pref is True
    assert service2.status().running is False


def test_config_file_shape(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    service.set_enabled(True)
    config = tmp_path / "data" / "evolution" / "config" / "mcp_bridge.json"
    assert config.exists()
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data == {"enabled_pref": True}


def test_governance_gate_detects_active_bridge_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="autonomy_disabled",
                assistant_kind="mcp_bridge",
                title="Autonomía externa desactivada por el usuario",
                status="active",
            ),
        ]
    )
    service, _ = _build_service(tmp_path, snapshot=snapshot)
    reason = service._governance_gate_block()
    assert reason is not None
    assert "Autonomía" in reason


def test_governance_gate_detects_global_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="global_shutdown",
                assistant_kind="*",
                title="Sistema en modo seguro",
                status="active",
            ),
        ]
    )
    service, _ = _build_service(tmp_path, snapshot=snapshot)
    assert service._governance_gate_block() is not None


def test_governance_gate_ignores_unrelated_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="cloudflare",
                assistant_kind="chatgpt_web",
                status="active",
            ),
        ]
    )
    service, _ = _build_service(tmp_path, snapshot=snapshot)
    assert service._governance_gate_block() is None


def test_governance_gate_ignores_inactive_block(tmp_path: Path) -> None:
    snapshot = _default_snapshot(
        blocks=[
            OperationalBlockRecord(
                block_type="autonomy_disabled",
                assistant_kind="mcp_bridge",
                title="Bloqueo resuelto",
                status="resolved",
            ),
        ]
    )
    service, _ = _build_service(tmp_path, snapshot=snapshot)
    assert service._governance_gate_block() is None


def test_listener_observes_fail_closed_startup(tmp_path: Path) -> None:
    service, server = _build_service(tmp_path)
    events: list[dict[str, object]] = []
    service.attach_listener(lambda payload: events.append(dict(payload)))
    status = service.set_enabled(True)
    assert server.started == 0
    assert events and events[0]["state"] == "stopped"
    assert any(event["state"] == "failed" for event in events)
    assert status.state == "failed"


def test_status_dict_is_serializable_and_copy_isolated(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    snapshot = service.status_dict()
    json.dumps(snapshot)
    snapshot["running"] = True
    assert service.status().running is False


def test_invalid_transport_falls_back_to_default(tmp_path: Path) -> None:
    service = MCPBridgeService(container=_FakeContainer(_default_snapshot()), workspace_root=tmp_path, transport="invalid")
    assert service.status().transport == "streamable-http"
    assert service.status().running is False


def test_stop_does_not_clear_enabled_preference(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    service.set_enabled(True)
    status = service.stop()
    assert status.enabled_pref is True
    assert status.running is False
    assert status.state == "stopped"
