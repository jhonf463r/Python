"""Tests del MCP server que expone servicios core de IABV v1.5.

Verifica que el adaptador:
- registra las 6 tools esperadas sobre FastMCP;
- enruta cada tool al servicio correcto del container;
- serializa pydantic / dataclasses / dicts anidados a JSON plano;
- respeta `reingest_only=True` en chatgpt_web_capture (no reinventa contrato);
- falla explícito si el container no expone un servicio requerido;
- orchestrator_preview no ejecuta, sólo previsualiza.
"""

from __future__ import annotations

import pytest

mcp = pytest.importorskip("mcp")

from iabv_v15.domain.models import (  # noqa: E402
    EnvironmentSelfModel,
    NetworkStatusSnapshot,
    ObservationPermissionGate,
    OperationalBlockRecord,
    PortableContextPackage,
    SelfExaminationSnapshot,
    WorldModelSnapshot,
)
from iabv_v15.infra.mcp.server import IABVMCPServer, _to_jsonable  # noqa: E402
from iabv_v15.services.tools.site_exploration_service import (  # noqa: E402
    SiteExplorationResult,
    SitePageSnapshot,
)


class _FakeWorldModelService:
    def __init__(self, snapshot: WorldModelSnapshot) -> None:
        self._snapshot = snapshot
        self.calls: list[tuple[str, bool]] = []

    def current_model(self) -> WorldModelSnapshot:
        self.calls.append(("current", False))
        return self._snapshot

    def request_refresh(self, *, reason: str = "manual", full: bool = False) -> WorldModelSnapshot:
        self.calls.append(("refresh", full))
        return self._snapshot


class _FakePortableContextService:
    def __init__(self, package: PortableContextPackage) -> None:
        self._package = package
        self.calls: list[tuple[bool, int]] = []

    def current_package(self, *, refresh: bool = False, max_age_seconds: int = 300, **_: object) -> PortableContextPackage:
        self.calls.append((refresh, max_age_seconds))
        return self._package


class _FakeSelfExaminationService:
    def __init__(self, review: SelfExaminationSnapshot) -> None:
        self._review = review
        self.calls: list[bool] = []

    def current_review(self, *, refresh: bool = False) -> SelfExaminationSnapshot:
        self.calls.append(refresh)
        return self._review

    def review_summary(self, review: SelfExaminationSnapshot | None = None) -> dict[str, object]:
        return {"patterns_detected": 0, "risks_flagged": 0}


class _FakeSiteExplorationService:
    def __init__(self, result: SiteExplorationResult) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def explore(self, *, start_url: str, max_pages: int | None = None, priority_keywords: list[str] | None = None) -> SiteExplorationResult:
        self.calls.append({"start_url": start_url, "max_pages": max_pages, "priority_keywords": priority_keywords})
        return self._result


class _FakeSiteManualRepository:
    def __init__(self) -> None:
        self.saved: list[SiteExplorationResult] = []

    def save(self, result: SiteExplorationResult) -> None:
        self.saved.append(result)


class _FakeOrchestrator:
    def __init__(self, decision: dict[str, object]) -> None:
        self._decision = decision
        self.calls: list[object] = []

    def build_decision_context_preview(self, request: object) -> dict[str, object]:
        self.calls.append(request)
        return self._decision


class _FakeUIExecutionRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def _capture_browser_dom_response(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {
            "launched": True,
            "prompt_pasted": not bool(kwargs.get("reingest_only")),
            "response_captured": True,
            "captured_text": "pong-iabv-mcp",
            "capture_source": "browser_dom_reingest" if kwargs.get("reingest_only") else "browser_dom",
        }


class _FakeContainer:
    def __init__(
        self,
        *,
        world_model_service: object | None = None,
        portable_context_service: object | None = None,
        operational_self_examination_service: object | None = None,
        site_exploration_service: object | None = None,
        adaptive_task_orchestrator: object | None = None,
        ui_execution_runner: object | None = None,
        site_manual_repository: object | None = None,
        workspace_root: str | None = None,
        ui_screenshot_provider: object | None = None,
    ) -> None:
        self.world_model_service = world_model_service
        self.portable_context_service = portable_context_service
        self.operational_self_examination_service = operational_self_examination_service
        self.site_exploration_service = site_exploration_service
        self.adaptive_task_orchestrator = adaptive_task_orchestrator
        self.ui_execution_runner = ui_execution_runner
        self.site_manual_repository = site_manual_repository
        # Audit tools leen `container.config.workspace_root` (o
        # `container.workspace_root` como fallback). Usamos el fallback
        # directo para no replicar AppConfig en los tests.
        self.workspace_root = workspace_root
        self.ui_screenshot_provider = ui_screenshot_provider


def _default_snapshot(
    *,
    connected: bool = True,
    blocks: list[OperationalBlockRecord] | None = None,
    gates: list[ObservationPermissionGate] | None = None,
) -> WorldModelSnapshot:
    """Arma un WorldModelSnapshot controlable para los tests.

    Por defecto la red está conectada y no hay bloqueos ni gates pendientes,
    así las tools write-capable (site_exploration_explore / chatgpt_web_capture)
    no se bloquean por governance. Los tests específicos de bloqueo pasan
    overrides explícitos.
    """

    return WorldModelSnapshot(
        external_state_flags=[],
        environment=EnvironmentSelfModel(),
        network_status=NetworkStatusSnapshot(connected=connected, status="ok" if connected else "offline"),
        block_records=blocks or [],
        permission_gates=gates or [],
    )


def _build_container(**overrides: object) -> _FakeContainer:
    snapshot = overrides.pop("_snapshot", None) or _default_snapshot()  # type: ignore[assignment]
    package = PortableContextPackage()
    review = SelfExaminationSnapshot()
    result = SiteExplorationResult(
        hostname="example.com",
        start_url="https://example.com",
        pages=[SitePageSnapshot(url="https://example.com", title="Example")],
        success=True,
    )
    defaults: dict[str, object] = {
        "world_model_service": _FakeWorldModelService(snapshot),
        "portable_context_service": _FakePortableContextService(package),
        "operational_self_examination_service": _FakeSelfExaminationService(review),
        "site_exploration_service": _FakeSiteExplorationService(result),
        "adaptive_task_orchestrator": _FakeOrchestrator({"route": "local_chat", "reason": "preview"}),
        "ui_execution_runner": _FakeUIExecutionRunner(),
        "site_manual_repository": _FakeSiteManualRepository(),
    }
    defaults.update(overrides)
    return _FakeContainer(**defaults)


def _get_tool(server: IABVMCPServer, name: str):
    registry = server.mcp._tool_manager._tools  # fastmcp exposed internal
    assert name in registry, f"tool {name} no registrada (existentes: {sorted(registry)})"
    return registry[name]


def _call_tool(server: IABVMCPServer, name: str, **kwargs: object) -> object:
    tool = _get_tool(server, name)
    return tool.fn(**kwargs)


def test_server_registers_six_core_tools() -> None:
    server = IABVMCPServer(_build_container())
    registered = set(server.mcp._tool_manager._tools.keys())
    expected = {
        "world_model_snapshot",
        "orchestrator_preview",
        "site_exploration_explore",
        "portable_context_get",
        "self_examination_current",
        "chatgpt_web_capture",
    }
    assert expected <= registered, f"faltan tools: {expected - registered}"


def test_world_model_snapshot_returns_current_without_refresh() -> None:
    wm = _FakeWorldModelService(
        WorldModelSnapshot(external_state_flags=[], environment=EnvironmentSelfModel()),
    )
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "world_model_snapshot")
    assert isinstance(payload, dict)
    assert wm.calls == [("current", False)]


def test_world_model_snapshot_refresh_triggers_request_refresh() -> None:
    wm = _FakeWorldModelService(
        WorldModelSnapshot(external_state_flags=[], environment=EnvironmentSelfModel()),
    )
    server = IABVMCPServer(_build_container(world_model_service=wm))
    _call_tool(server, "world_model_snapshot", refresh=True, full=True)
    assert wm.calls == [("refresh", True)]


def test_portable_context_get_passes_refresh_and_max_age() -> None:
    pc = _FakePortableContextService(PortableContextPackage())
    server = IABVMCPServer(_build_container(portable_context_service=pc))
    _call_tool(server, "portable_context_get", refresh=True, max_age_seconds=42)
    assert pc.calls == [(True, 42)]


def test_self_examination_current_returns_review_and_summary() -> None:
    server = IABVMCPServer(_build_container())
    payload = _call_tool(server, "self_examination_current")
    assert isinstance(payload, dict)
    assert "review" in payload and "summary" in payload


def test_site_exploration_explore_persists_manual_when_success() -> None:
    repo = _FakeSiteManualRepository()
    result = SiteExplorationResult(
        hostname="example.com",
        start_url="https://example.com",
        pages=[SitePageSnapshot(url="https://example.com", title="Example")],
        success=True,
    )
    svc = _FakeSiteExplorationService(result)
    server = IABVMCPServer(_build_container(site_exploration_service=svc, site_manual_repository=repo))
    payload = _call_tool(server, "site_exploration_explore", start_url="https://example.com", max_pages=3)
    assert payload["manual_persisted"] is True
    assert len(repo.saved) == 1
    assert svc.calls[0]["start_url"] == "https://example.com"
    assert svc.calls[0]["max_pages"] == 3


def test_site_exploration_explore_does_not_persist_when_failure() -> None:
    repo = _FakeSiteManualRepository()
    failing = SiteExplorationResult(
        hostname="",
        start_url="https://bad",
        pages=[],
        success=False,
        error_message="boom",
    )
    svc = _FakeSiteExplorationService(failing)
    server = IABVMCPServer(_build_container(site_exploration_service=svc, site_manual_repository=repo))
    payload = _call_tool(server, "site_exploration_explore", start_url="https://bad")
    assert repo.saved == []
    assert "manual_persisted" not in payload or payload["manual_persisted"] is False


def test_orchestrator_preview_calls_build_decision_context_preview() -> None:
    orch = _FakeOrchestrator({"route": "external_consultation", "reason": "preview"})
    server = IABVMCPServer(_build_container(adaptive_task_orchestrator=orch))
    payload = _call_tool(
        server,
        "orchestrator_preview",
        user_goal="Consultar a ChatGPT sobre X",
        offline_only=False,
    )
    assert payload == {"route": "external_consultation", "reason": "preview"}
    assert len(orch.calls) == 1


def test_chatgpt_web_capture_respects_reingest_only_true() -> None:
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(ui_execution_runner=runner))
    payload = _call_tool(
        server,
        "chatgpt_web_capture",
        prompt_text="NO-DEBE-PEGARSE",
        reingest_only=True,
    )
    assert payload["prompt_pasted"] is False
    assert payload["capture_source"] == "browser_dom_reingest"
    assert runner.calls[0]["reingest_only"] is True


def test_chatgpt_web_capture_pastes_prompt_when_not_reingesting() -> None:
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(ui_execution_runner=runner))
    payload = _call_tool(
        server,
        "chatgpt_web_capture",
        prompt_text="Responde 'pong'",
        reingest_only=False,
    )
    assert payload["prompt_pasted"] is True
    assert payload["capture_source"] == "browser_dom"
    assert runner.calls[0]["reingest_only"] is False


def test_chatgpt_web_capture_uses_official_selectors_by_default() -> None:
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(ui_execution_runner=runner))
    _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    sent = runner.calls[0]
    assert "textarea" in sent["input_selectors"]
    assert '[data-message-author-role="assistant"]' in sent["response_selectors"]
    assert 'button[data-testid="send-button"]' in sent["submit_selectors"]


def test_container_missing_world_model_raises() -> None:
    server = IABVMCPServer(_build_container(world_model_service=None))
    tool = _get_tool(server, "world_model_snapshot")
    with pytest.raises(RuntimeError, match="world_model_service"):
        tool.fn()


def test_to_jsonable_handles_dataclass_and_pydantic() -> None:
    snap = WorldModelSnapshot(external_state_flags=[], environment=EnvironmentSelfModel())
    site = SiteExplorationResult(hostname="a", start_url="b", pages=[], success=True)
    payload = _to_jsonable({"snap": snap, "site": site, "list": [1, "x"], "none": None})
    assert isinstance(payload["snap"], dict)
    assert isinstance(payload["site"], dict)
    assert payload["list"] == [1, "x"]
    assert payload["none"] is None


def test_server_rejects_unknown_transport() -> None:
    server = IABVMCPServer(_build_container())
    with pytest.raises(ValueError, match="transport"):
        server.run(transport="does-not-exist")


def test_server_requires_container() -> None:
    with pytest.raises(ValueError, match="container"):
        IABVMCPServer(container=None)


# ----------------------------------------------------------------------
# Governance gate: las tools write-capable deben consultar WorldModelSnapshot
# antes de actuar (AGENTS.md "Política Operativa Actual"). Estos tests cubren
# el finding de Devin Review: red caída, bloqueo operativo activo o gate
# `requerido` sin conceder deben resultar en `governance_blocked=True` y la
# ruta externa NO debe ejecutarse.


def test_site_exploration_blocked_when_network_offline() -> None:
    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    svc = _FakeSiteExplorationService(
        SiteExplorationResult(hostname="x", start_url="https://x", pages=[], success=True),
    )
    server = IABVMCPServer(_build_container(world_model_service=wm, site_exploration_service=svc))
    payload = _call_tool(server, "site_exploration_explore", start_url="https://x")
    assert payload["governance_blocked"] is True
    assert payload["reason"] == "network_unavailable"
    assert svc.calls == []  # el servicio jamás se ejecutó


def test_chatgpt_web_capture_blocked_when_permission_gate_required() -> None:
    gate = ObservationPermissionGate(
        scope="chatgpt_web",
        assistant_kind="chatgpt_web",
        title="Permiso de observación",
        status="requerido",
        granted=False,
    )
    wm = _FakeWorldModelService(_default_snapshot(gates=[gate]))
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(world_model_service=wm, ui_execution_runner=runner))
    payload = _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    assert payload["governance_blocked"] is True
    assert payload["reason"] == "permission_gate_required"
    assert runner.calls == []  # el runner jamás se llamó


def test_chatgpt_web_capture_blocked_when_operational_block_active() -> None:
    block = OperationalBlockRecord(
        block_type="cloudflare_turnstile",
        assistant_kind="chatgpt_web",
        title="Cloudflare bloquea la VM",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(world_model_service=wm, ui_execution_runner=runner))
    payload = _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"
    assert runner.calls == []


def test_governance_allows_route_when_network_ok_and_no_blocks() -> None:
    """Camino feliz: snapshot con red ok y sin bloqueos no debe bloquear."""

    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(ui_execution_runner=runner))
    payload = _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    assert "governance_blocked" not in payload
    assert runner.calls and runner.calls[0]["prompt_text"] == "hola"


def test_governance_ignores_blocks_scoped_to_other_assistant_kinds() -> None:
    """Un block_record para otro assistant_kind no debe bloquear esta ruta."""

    unrelated = OperationalBlockRecord(
        block_type="auth_missing",
        assistant_kind="codex",  # otra ruta
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[unrelated]))
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(world_model_service=wm, ui_execution_runner=runner))
    payload = _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    assert "governance_blocked" not in payload
    assert runner.calls  # sí se ejecutó porque el bloqueo no aplicaba


def test_governance_ignores_permission_gates_already_granted() -> None:
    """Un gate con granted=True no debe bloquear."""

    gate = ObservationPermissionGate(
        scope="chatgpt_web",
        assistant_kind="chatgpt_web",
        status="requerido",
        granted=True,  # ya aprobado
    )
    wm = _FakeWorldModelService(_default_snapshot(gates=[gate]))
    runner = _FakeUIExecutionRunner()
    server = IABVMCPServer(_build_container(world_model_service=wm, ui_execution_runner=runner))
    payload = _call_tool(server, "chatgpt_web_capture", prompt_text="hola")
    assert "governance_blocked" not in payload
    assert runner.calls


# ----------------------------------------------------------------------
# Audit tools (Frente 1). El wiring en `server.py` delega en el módulo
# `audit_tools` — acá cubrimos 1) registro, 2) governance bloqueando,
# 3) happy path degradado.


def test_server_registers_audit_tools() -> None:
    server = IABVMCPServer(_build_container())
    registered = set(server.mcp._tool_manager._tools.keys())
    audit = {
        "run_pytest",
        "read_repo_file",
        "list_repo_directory",
        "capture_ui_screenshot",
        "git_status_and_log",
    }
    assert audit <= registered, f"faltan audit tools: {audit - registered}"


def test_read_repo_file_happy_path_via_server(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "hello.md").write_text("hola", encoding="utf-8")
    server = IABVMCPServer(_build_container(workspace_root=str(tmp_path)))
    payload = _call_tool(server, "read_repo_file", relative_path="docs/hello.md")
    assert payload["content"] == "hola"
    assert payload["path"] == "docs/hello.md"


def test_read_repo_file_returns_error_payload_on_invalid(tmp_path) -> None:  # type: ignore[no-untyped-def]
    server = IABVMCPServer(_build_container(workspace_root=str(tmp_path)))
    payload = _call_tool(server, "read_repo_file", relative_path="/etc/passwd")
    assert payload["error"] == "absolute_path_forbidden"


def test_list_repo_directory_via_server(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / ".env").write_text("S")
    server = IABVMCPServer(_build_container(workspace_root=str(tmp_path)))
    payload = _call_tool(server, "list_repo_directory", relative_path="")
    names = {entry["name"]: entry for entry in payload["entries"]}
    assert ".env" in names and names[".env"]["sensitive"] is True


def test_capture_ui_screenshot_without_provider_degrades_via_server() -> None:
    server = IABVMCPServer(_build_container())
    payload = _call_tool(server, "capture_ui_screenshot")
    assert payload["error"] == "ui_not_running"


def test_audit_tools_blocked_when_audit_block_active(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Un `OperationalBlockRecord` con assistant_kind='audit' debe bloquear
    todas las audit tools (fail-closed)."""

    block = OperationalBlockRecord(
        block_type="audit_paused",
        assistant_kind="audit",
        title="Auditoría pausada manualmente",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(
        _build_container(world_model_service=wm, workspace_root=str(tmp_path)),
    )
    for tool_name, kwargs in [
        ("read_repo_file", {"relative_path": "README.md"}),
        ("list_repo_directory", {"relative_path": ""}),
        ("capture_ui_screenshot", {}),
        ("git_status_and_log", {}),
        ("run_pytest", {}),
    ]:
        payload = _call_tool(server, tool_name, **kwargs)
        assert payload["governance_blocked"] is True, f"{tool_name} no respetó el block"
        assert payload["reason"] == "operational_block_active"


def test_audit_tools_blocked_when_global_wildcard_block_active(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Un bloqueo con assistant_kind='*' también debe detener las audit tools."""

    block = OperationalBlockRecord(
        block_type="freeze_all",
        assistant_kind="*",
        title="Freeze global",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(
        _build_container(world_model_service=wm, workspace_root=str(tmp_path)),
    )
    payload = _call_tool(server, "read_repo_file", relative_path="README.md")
    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"


def test_audit_tools_allow_when_only_unrelated_block(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Si el block es para otra ruta (ej. chatgpt_web), audit debe pasar."""

    (tmp_path / "file.md").write_text("contenido")
    unrelated = OperationalBlockRecord(
        block_type="cloudflare",
        assistant_kind="chatgpt_web",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[unrelated]))
    server = IABVMCPServer(
        _build_container(world_model_service=wm, workspace_root=str(tmp_path)),
    )
    payload = _call_tool(server, "read_repo_file", relative_path="file.md")
    assert "governance_blocked" not in payload
    assert payload["content"] == "contenido"
