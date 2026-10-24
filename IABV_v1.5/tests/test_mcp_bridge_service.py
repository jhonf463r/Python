"""Fail-closed tests for the UI-owned MCP bridge lifecycle.

The service cannot own a client-managed stdio pipe, and network transports are
disabled until transport authentication and independent operation-level
authorization are implemented. Collaborators below are inert fakes: no process,
network, FastMCP server, or production storage is used.
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
    DEFAULT_TRANSPORT,
    CloudflaredTunnelRunner,
    FastMCPServerRunner,
    MCPBridgeService,
    MCPBridgeStatus,
)
from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel


class _FakeServerRunner:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def run_threaded(self, transport: str, host: str, port: int) -> threading.Thread:
        self.started += 1
        raise AssertionError("Fail-closed bridge must not start a server runner")

    def stop(self) -> None:
        self.stopped += 1


class _FakeTunnelRunner:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self, bind_host: str, bind_port: int) -> None:
        self.started += 1
        raise AssertionError("Fail-closed bridge must not start a tunnel")

    def stop(self) -> None:
        self.stopped += 1

    def wait_for_url(self, timeout_s: float) -> str | None:
        raise AssertionError("Fail-closed bridge must not wait for a tunnel")

    @property
    def url(self) -> str | None:
        return None

    @property
    def last_error(self) -> str | None:
        return None


class _FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot | None) -> None:
        self._snapshot = snapshot
        self.current_model_calls = 0

    def current_model(self) -> WorldModelSnapshot | None:
        self.current_model_calls += 1
        return self._snapshot


class _FakeContainer:
    def __init__(self, snapshot: WorldModelSnapshot | None = None) -> None:
        self.world_model_service = _FakeWorldModelService(snapshot)


def _default_snapshot(
    *, blocks: list[OperationalBlockRecord] | None = None,
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
    snapshot: WorldModelSnapshot | None = None,
    transport: str = DEFAULT_TRANSPORT,
) -> tuple[MCPBridgeService, _FakeServerRunner, _FakeTunnelRunner]:
    server = _FakeServerRunner()
    tunnel = _FakeTunnelRunner()
    svc = MCPBridgeService(
        container=_FakeContainer(snapshot or _default_snapshot()),
        workspace_root=tmp_path,
        server_runner=server,
        tunnel_runner=tunnel,
        transport=transport,
    )
    return svc, server, tunnel


def _assert_no_dispatch(
    status: MCPBridgeStatus,
    server: _FakeServerRunner,
    tunnel: _FakeTunnelRunner,
) -> None:
    assert status.running is False
    assert status.state == "failed"
    assert status.tunnel_url is None
    assert server.started == 0
    assert tunnel.started == 0


def test_enabled_pref_starts_false_when_no_config(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    assert svc.status().enabled_pref is False
    assert svc.status().running is False


def test_set_enabled_persists_preference_across_instances(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    svc2, _, _ = _build_service(tmp_path)
    assert svc2.status().enabled_pref is True
    assert svc2.status().running is False


def test_disabling_bridge_persists_false_without_starting_runners(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    svc.set_enabled(True)
    status = svc.set_enabled(False)

    assert status.enabled_pref is False
    assert status.running is False
    assert status.state == "stopped"
    assert server.started == 0
    assert tunnel.started == 0


def test_config_file_shape(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    svc.set_enabled(True)
    config = tmp_path / "data" / "evolution" / "config" / "mcp_bridge.json"
    assert config.exists()
    assert json.loads(config.read_text(encoding="utf-8")) == {"enabled_pref": True}


def test_ui_service_refuses_stdio_without_starting_runners(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path, transport="stdio")
    status = svc.set_enabled(True)
    _assert_no_dispatch(status, server, tunnel)
    assert "canal stdio" in (status.last_error or "")
    assert svc._container.world_model_service.current_model_calls == 0


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
def test_ui_service_refuses_network_transports_without_starting_runners(
    tmp_path: Path, transport: str
) -> None:
    svc, server, tunnel = _build_service(tmp_path, transport=transport)
    status = svc.set_enabled(True)
    _assert_no_dispatch(status, server, tunnel)
    assert "autorización" in (status.last_error or "")
    assert svc._container.world_model_service.current_model_calls == 0


def test_unknown_transport_falls_back_to_safe_default(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path, transport="pigeon-carrier")
    assert svc.status().transport == DEFAULT_TRANSPORT == "stdio"
    _assert_no_dispatch(svc.set_enabled(True), server, tunnel)


def test_default_runner_compatibility_shims_refuse_direct_start() -> None:
    server_runner = FastMCPServerRunner(container=object())
    with pytest.raises(RuntimeError, match="client-managed local stdio"):
        server_runner.run_threaded(transport="stdio", host="127.0.0.1", port=0)

    tunnel_runner = CloudflaredTunnelRunner()
    with pytest.raises(RuntimeError, match="Public tunnels are disabled"):
        tunnel_runner.start("127.0.0.1", 0)
    assert tunnel_runner.url is None


def test_active_bridge_block_does_not_trigger_world_model_lookup_or_runner(tmp_path: Path) -> None:
    snapshot = _default_snapshot(blocks=[OperationalBlockRecord(
        block_type="autonomy_disabled",
        assistant_kind="mcp_bridge",
        title="Autonomía externa desactivada por el usuario",
        status="active",
    )])
    svc, server, tunnel = _build_service(tmp_path, snapshot=snapshot)
    status = svc.set_enabled(True)
    assert status.governance_blocked is None
    assert status.governance_reason is None
    assert "autorización independiente" in (status.last_error or "")
    assert svc._container.world_model_service.current_model_calls == 0
    _assert_no_dispatch(status, server, tunnel)


def test_global_block_does_not_trigger_world_model_lookup_or_runner(tmp_path: Path) -> None:
    snapshot = _default_snapshot(blocks=[OperationalBlockRecord(
        block_type="global_shutdown",
        assistant_kind="*",
        title="Sistema en modo seguro",
        status="active",
    )])
    svc, server, tunnel = _build_service(tmp_path, snapshot=snapshot)
    status = svc.set_enabled(True)
    assert status.governance_blocked is None
    assert status.governance_reason is None
    assert "autorización independiente" in (status.last_error or "")
    assert svc._container.world_model_service.current_model_calls == 0
    _assert_no_dispatch(status, server, tunnel)


def test_unrelated_or_inactive_block_does_not_release_or_start_bridge(tmp_path: Path) -> None:
    snapshot = _default_snapshot(blocks=[
        OperationalBlockRecord(
            block_type="cloudflare", assistant_kind="chatgpt_web", status="active"
        ),
        OperationalBlockRecord(
            block_type="autonomy_disabled", assistant_kind="mcp_bridge", status="resolved"
        ),
    ])
    svc, server, tunnel = _build_service(tmp_path, snapshot=snapshot)
    status = svc.set_enabled(True)
    assert status.governance_blocked is None
    _assert_no_dispatch(status, server, tunnel)


def test_listeners_receive_initial_and_fail_closed_state(tmp_path: Path) -> None:
    svc, server, tunnel = _build_service(tmp_path)
    events: list[dict[str, object]] = []
    svc.attach_listener(lambda payload: events.append(dict(payload)))
    assert events[0]["state"] == "stopped"
    status = svc.set_enabled(True)
    assert events[-1]["state"] == "failed"
    _assert_no_dispatch(status, server, tunnel)


def test_status_dict_is_serializable_and_copy_isolated(tmp_path: Path) -> None:
    svc, _, _ = _build_service(tmp_path)
    payload = json.loads(json.dumps(svc.status_dict()))
    assert payload["state"] == "stopped"
    assert payload["transport"] == "stdio"
    status = svc.status()
    status.state = "MUTATED"
    assert svc.status().state == "stopped"


@pytest.mark.parametrize("blocked", [True, False, None])
def test_status_serialization_preserves_governance_tristate(blocked: bool | None) -> None:
    payload = json.loads(json.dumps(MCPBridgeStatus(governance_blocked=blocked).to_dict()))
    assert payload["governance_blocked"] is blocked


@pytest.mark.parametrize("blocked", [True, False, None])
def test_viewmodel_preserves_governance_tristate(blocked: bool | None) -> None:
    from types import SimpleNamespace

    viewmodel = SimpleNamespace(_mcp_bridge_status={"governance_blocked": blocked})
    assert ControlCenterViewModel.get_mcp_bridge_blocked(viewmodel) is blocked


def test_qml_renders_uninspected_governance_separately() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "iabv_v15" / "ui" / "qml" / "pages" / "ControlCenterPage.qml"
    qml = qml_path.read_text(encoding="utf-8")
    assert "blocked === true" in qml
    assert 'var governancePrefix = "Gobernanza comprobada: sin bloqueo. "' in qml
    assert "blocked === null || blocked === undefined" in qml
    assert "Gobernanza no inspeccionada" in qml
    assert "Iniciando servidor MCP y tunnel" not in qml
    assert "Activar para exponer el programa" not in qml
