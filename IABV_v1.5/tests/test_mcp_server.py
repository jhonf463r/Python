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

from types import SimpleNamespace

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
    IATraceEntry,
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


class _FakeConsensusService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def fuse(self, *, candidate_traces: list[IATraceEntry], strategy: str = "weighted_vote"):
        self.calls.append({"candidate_traces": candidate_traces, "strategy": strategy})
        from iabv_v15.domain.models import ConsensusResult

        return ConsensusResult(
            comparison_scope_key=candidate_traces[0].comparison_scope_key,
            winning_trace_id=candidate_traces[0].trace_id,
            winning_assistant_kind=candidate_traces[0].assistant_kind,
            winning_label=candidate_traces[0].result_label,
            strategy_used=strategy,
            considered_trace_ids=[trace.trace_id for trace in candidate_traces],
        )


class _FakeExperimentLab:
    def __init__(self, traces: list[IATraceEntry]) -> None:
        self.traces = traces
        self.calls: list[str] = []

    def list_candidate_traces_for_scope(self, scope_key: str) -> list[IATraceEntry]:
        self.calls.append(scope_key)
        return [trace for trace in self.traces if trace.comparison_scope_key == scope_key]


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
        environment_self_model: object | None = None,
        config: object | None = None,
        self_audit_service: object | None = None,
        capability_audit_harness: object | None = None,
        perception_ground_truth_comparator: object | None = None,
        consensus_fusion_service: object | None = None,
        experiment_lab: object | None = None,
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
        self.environment_self_model = environment_self_model
        self.config = config
        self.self_audit_service = self_audit_service
        self.capability_audit_harness = capability_audit_harness
        self.perception_ground_truth_comparator = perception_ground_truth_comparator
        self.consensus_fusion_service = consensus_fusion_service
        self.experiment_lab = experiment_lab
        # F2.1 — se inyecta solo cuando el test lo pide.
        self.github_remote_service: object | None = None


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


def test_server_registers_core_tools() -> None:
    server = IABVMCPServer(_build_container())
    registered = set(server.mcp._tool_manager._tools.keys())
    expected = {
        "world_model_snapshot",
        "orchestrator_preview",
        "site_exploration_explore",
        "portable_context_get",
        "self_examination_current",
        "chatgpt_web_capture",
        "run_self_audit",
        "probe_assistant_login",
        "audit_capability",
        "compare_perception_vs_ground_truth",
        "embodiment_manifest",
        "embodiment_violations_current",
        "cognitive_frame_translate",
        "assistant_capabilities_list",
        "synaptic_route",
        "consensus_fuse",
    }
    assert expected <= registered, f"faltan tools: {expected - registered}"


def test_consensus_fuse_loads_candidate_traces_from_experiment_lab_scope() -> None:
    trace = IATraceEntry(
        trace_id="trace-1",
        assistant_kind="devin",
        comparison_scope_key="iabv:scope",
        result_label="pass",
        confidence=0.9,
        success=True,
    )
    consensus = _FakeConsensusService()
    lab = _FakeExperimentLab([trace])
    server = IABVMCPServer(
        _build_container(consensus_fusion_service=consensus, experiment_lab=lab)
    )

    payload = _call_tool(server, "consensus_fuse", scope_key="iabv:scope")

    assert payload["winning_trace_id"] == "trace-1"
    assert lab.calls == ["iabv:scope"]
    assert consensus.calls[0]["strategy"] == "weighted_vote"


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


def test_run_pytest_tool_signature_rejects_python_executable() -> None:
    """El MCP tool `run_pytest` NO debe exponer `python_executable` a los
    clientes remotos; la elección del intérprete es decisión del host.

    Regresión de la finding Devin Review
    BUG_pr-review-job-1f9ba1f9056944b0b4f49844ab925503_0001.
    """

    import inspect

    server = IABVMCPServer(_build_container())
    tool = _get_tool(server, "run_pytest")
    sig = inspect.signature(tool.fn)
    assert "python_executable" not in sig.parameters
    assert set(sig.parameters) <= {"suite", "keyword"}


def test_pytest_python_executable_prefers_environment_self_model(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """`_pytest_python_executable` debe resolver primero desde
    `container.environment_self_model.runtime_profile`, no desde el client.
    """

    fake_python = tmp_path / "python"
    fake_python.write_text("#!/bin/sh\n")
    fake_python.chmod(0o755)

    class _ESM:
        runtime_profile = {"python_executable": str(fake_python)}

    monkeypatch.delenv("IABV_PYTEST_PYTHON", raising=False)
    server = IABVMCPServer(
        _build_container(environment_self_model=_ESM()),
    )
    assert server._pytest_python_executable() == str(fake_python.resolve())


def test_pytest_python_executable_rejects_unsafe_candidates(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Si la env var trae un path con shell metachars, debe descartarse y
    caer al siguiente candidato / None, nunca devolver el valor crudo."""

    monkeypatch.setenv("IABV_PYTEST_PYTHON", "/usr/bin/python3; rm -rf /")
    server = IABVMCPServer(_build_container())
    assert server._pytest_python_executable() is None


def test_pytest_python_executable_returns_none_when_no_candidates(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("IABV_PYTEST_PYTHON", raising=False)
    server = IABVMCPServer(_build_container())
    assert server._pytest_python_executable() is None


# ----------------------------------------------------------------------
# Frente 2 — `run_self_audit`: ejecuta el SelfAuditService (read-only) con
# governance gate `assistant_kind='audit'` (fail-closed). El snapshot se
# serializa; si el service no está en el container, devuelve un payload
# degradado `{"error": "self_audit_unavailable", ...}` en vez de crashear.
from datetime import datetime, timezone  # noqa: E402

from iabv_v15.domain.models import (  # noqa: E402
    EnvironmentMatchResult,
    SelfAuditSnapshot,
    ToolCheckResult,
)


class _FakeSelfAuditService:
    def __init__(self, snapshot: SelfAuditSnapshot | None = None, *, raise_exc: Exception | None = None) -> None:
        self._snapshot = snapshot or _default_audit_snapshot()
        self._raise_exc = raise_exc
        self.calls: list[str | None] = []

    def run(self, *, reason: str | None = None) -> SelfAuditSnapshot:
        self.calls.append(reason)
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._snapshot


def _default_audit_snapshot(*, reason: str | None = None) -> SelfAuditSnapshot:
    return SelfAuditSnapshot(
        generated_at=datetime(2025, 4, 19, 12, 0, 0, tzinfo=timezone.utc),
        reason=reason,
        tool_checks=[
            ToolCheckResult(tool_id="codex", available=True, status="ready", reason=None, evidence={"adapter_key": "codex_cli"}),
            ToolCheckResult(tool_id="chatgpt_web", available=False, status="missing", reason="adapter reported tool as not available", evidence={"adapter_key": "chatgpt_web"}),
        ],
        environment_match=EnvironmentMatchResult(
            matched=True,
            mismatches=[],
            environment_digest="env-digest",
            world_model_digest="wm-digest",
        ),
        pending_issues=["issue-1"],
        world_model_digest={"available": True, "tool_live_ids": ["codex"], "network_connected": True},
        summary_markdown="# Auditoría operativa — IABV v1.5\n- Tools OK: 1 / 2",
    )


def test_run_self_audit_registered_and_returns_serialized_snapshot() -> None:
    audit = _FakeSelfAuditService(_default_audit_snapshot(reason="ok"))
    server = IABVMCPServer(_build_container(self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit", reason="ok")

    assert isinstance(payload, dict)
    assert payload.get("reason") == "ok"
    assert "tool_checks" in payload
    assert len(payload["tool_checks"]) == 2
    assert {c["tool_id"] for c in payload["tool_checks"]} == {"codex", "chatgpt_web"}
    assert payload["environment_match"]["matched"] is True
    assert payload["summary_markdown"].startswith("# Auditoría operativa")
    assert payload["world_model_digest"]["available"] is True
    # el reason se propaga al service con el mismo valor recibido por el tool.
    assert audit.calls == ["ok"]


def test_run_self_audit_without_reason_passes_none() -> None:
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit")
    assert isinstance(payload, dict)
    assert audit.calls == [None]


def test_run_self_audit_degrades_when_container_missing_service() -> None:
    server = IABVMCPServer(_build_container(self_audit_service=None))
    payload = _call_tool(server, "run_self_audit", reason="probe")

    assert payload.get("error") == "self_audit_unavailable"
    assert "container.self_audit_service" in payload.get("detail", "")


def test_run_self_audit_serializes_datetime_as_isoformat() -> None:
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit")
    # _to_jsonable convierte datetime -> ISO 8601 con separador 'T'.
    assert isinstance(payload["generated_at"], str)
    assert payload["generated_at"] == "2025-04-19T12:00:00+00:00"


def test_run_self_audit_blocked_by_operational_block_on_audit_kind() -> None:
    block = OperationalBlockRecord(
        block_type="observation_denied",
        assistant_kind="audit",
        title="Permiso denegado para autoauditoría",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(world_model_service=wm, self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit", reason="should_block")

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"
    # Gate fail-closed: el service NUNCA se ejecuta cuando governance bloquea.
    assert audit.calls == []


def test_run_self_audit_blocked_by_global_block_record() -> None:
    block = OperationalBlockRecord(
        block_type="system_paused",
        assistant_kind="*",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(world_model_service=wm, self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit")

    assert payload["governance_blocked"] is True
    assert audit.calls == []


def test_run_self_audit_blocked_by_permission_gate_for_audit() -> None:
    gate = ObservationPermissionGate(
        scope="audit",
        assistant_kind="audit",
        title="Permiso para autoauditoría",
        status="requerido",
        granted=False,
    )
    wm = _FakeWorldModelService(_default_snapshot(gates=[gate]))
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(world_model_service=wm, self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit")

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "permission_gate_required"
    assert audit.calls == []


def test_run_self_audit_ignores_blocks_scoped_to_other_assistant_kinds() -> None:
    """Un block_record para otra ruta (p.ej. chatgpt_web) NO debe bloquear audit."""

    other = OperationalBlockRecord(
        block_type="cloudflare_turnstile",
        assistant_kind="chatgpt_web",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[other]))
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(world_model_service=wm, self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit", reason="independent")

    assert "governance_blocked" not in payload
    assert audit.calls == ["independent"]


def test_run_self_audit_does_not_require_network() -> None:
    """La ruta `audit` es offline; red desconectada NO debe bloquear."""

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    audit = _FakeSelfAuditService()
    server = IABVMCPServer(_build_container(world_model_service=wm, self_audit_service=audit))
    payload = _call_tool(server, "run_self_audit")

    assert "governance_blocked" not in payload
    assert audit.calls == [None]


# ----------------------------------------------------------------------
# Frente 3 — probe_assistant_login
#
# La tool verifica login en asistentes web externos. A diferencia de las
# otras audit tools, pasa por el gate con `requires_network=True`, así
# que una red desconectada debe bloquearla. En happy path, el core
# devuelve `unknown_assistant_kind` si pasamos un kind no soportado,
# cosa que nos permite verificar que el gate dejó pasar sin montar un
# browser real.


def test_probe_assistant_login_blocked_when_audit_block_active() -> None:
    block = OperationalBlockRecord(
        block_type="audit_paused",
        assistant_kind="audit",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "probe_assistant_login", assistant_kind="chatgpt")

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"


def test_probe_assistant_login_blocked_when_network_offline() -> None:
    """`requires_network=True`: si la red está caída, bloquear antes de abrir browser."""

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "probe_assistant_login", assistant_kind="chatgpt")

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "network_unavailable"


def test_probe_assistant_login_blocked_by_global_wildcard_block() -> None:
    block = OperationalBlockRecord(
        block_type="freeze_all",
        assistant_kind="*",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "probe_assistant_login", assistant_kind="chatgpt")

    assert payload["governance_blocked"] is True


def test_probe_assistant_login_passes_gate_and_reports_unknown_kind() -> None:
    """Con red ok y sin bloqueos, el gate deja pasar; el core reporta el error
    tipado ``unknown_assistant_kind`` sin abrir un browser real."""

    server = IABVMCPServer(_build_container())
    payload = _call_tool(server, "probe_assistant_login", assistant_kind="foobar")

    assert "governance_blocked" not in payload
    assert payload["error"] == "unknown_assistant_kind"
    assert payload["assistant_kind"] == "foobar"


def test_probe_assistant_login_ignores_blocks_for_other_assistant_kinds() -> None:
    other = OperationalBlockRecord(
        block_type="cloudflare",
        assistant_kind="chatgpt_web",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[other]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "probe_assistant_login", assistant_kind="foobar")

    assert "governance_blocked" not in payload
    # Aun sin bloqueo, el core devuelve el error tipado (no abre browser).
    assert payload["error"] == "unknown_assistant_kind"


def test_run_sync_off_event_loop_direct_when_no_loop() -> None:
    """Sin event loop, corre en el hilo actual (tests y CLI)."""

    from iabv_v15.infra.mcp.server import _run_sync_off_event_loop

    import threading

    main_thread_id = threading.get_ident()
    captured_thread_id: list[int] = []

    def _op(x: int) -> int:
        captured_thread_id.append(threading.get_ident())
        return x * 2

    result = _run_sync_off_event_loop(_op, 21)
    assert result == 42
    assert captured_thread_id == [main_thread_id]


def test_run_sync_off_event_loop_thread_when_loop_running() -> None:
    """Con event loop activo, despacha a un worker distinto al hilo del loop.

    Regresión F3.1: Playwright sync API falla si se arranca en el hilo del
    event loop de uvicorn. Este helper asegura que el trabajo corre en un
    hilo sin loop corriendo.
    """

    import asyncio
    import threading

    from iabv_v15.infra.mcp.server import _run_sync_off_event_loop

    def _op() -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
            loop_visible = True
        except RuntimeError:
            loop_visible = False
        return {"thread": threading.get_ident(), "loop_visible": loop_visible}

    async def _driver() -> dict[str, Any]:
        return _run_sync_off_event_loop(_op)

    result = asyncio.run(_driver())
    # El hilo del driver (el loop) NO debe haber ejecutado _op.
    assert result["thread"] != threading.get_ident()
    # Sin loop corriendo en el worker → Playwright sync OK.
    assert result["loop_visible"] is False


# ----------------------------------------------------------------------
# Frente 3.2 — audit_capability
#
# Esta tool tiene `requires_network` dinámico: se toma de la policy de
# la capacidad. Verificamos que:
#   - capacidades externas (llm_external_*, browser_capture) se bloquean
#     con red caída;
#   - capacidades locales (llm_local_ollama, ui_execution) NO se bloquean
#     con red caída (policy.requires_network=False);
#   - bloqueo por `assistant_kind='audit'` aplica igual que en probe_*;
#   - `dry_run=True` evita el gate de red aun en capacidades externas;
#   - sin harness wireado, la tool devuelve `harness_unavailable`;
#   - con harness wireado, se delega al runner.


def _audit_harness_with_ok_runner(capability_id: str = "llm_local_ollama") -> object:
    from iabv_v15.services.evolution.capability_audit_harness import (
        CapabilityAuditHarness,
        CapabilityAuditResult,
    )

    h = CapabilityAuditHarness()
    h.register(
        capability_id,
        lambda **_: CapabilityAuditResult(
            capability_id=capability_id,
            executed=True,
            success=True,
            output_preview="OK",
        ),
    )
    return h


def test_audit_capability_blocked_when_audit_block_active() -> None:
    block = OperationalBlockRecord(
        block_type="audit_paused",
        assistant_kind="audit",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "audit_capability", capability_id="llm_local_ollama")

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"


def test_audit_capability_blocks_external_caps_when_network_offline() -> None:
    """llm_external_chatgpt tiene `requires_network=True` → red caída bloquea."""

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(
        server, "audit_capability", capability_id="llm_external_chatgpt"
    )

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "network_unavailable"


def test_audit_capability_local_caps_not_blocked_by_offline_network() -> None:
    """llm_local_ollama tiene `requires_network=False` → red caída no bloquea.

    Sin harness wireado el core responde `harness_unavailable`, lo que
    igual prueba que el gate DEJÓ pasar (no devolvió `governance_blocked`).
    """

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(server, "audit_capability", capability_id="llm_local_ollama")

    assert "governance_blocked" not in payload
    assert payload["error"] == "harness_unavailable"


def test_audit_capability_dry_run_does_not_trigger_network_gate() -> None:
    """Con `dry_run=True`, ni una capacidad externa exige red."""

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    harness = _audit_harness_with_ok_runner("llm_external_chatgpt")
    server = IABVMCPServer(
        _build_container(
            world_model_service=wm,
            capability_audit_harness=harness,
        )
    )
    payload = _call_tool(
        server,
        "audit_capability",
        capability_id="llm_external_chatgpt",
        dry_run=True,
    )
    assert "governance_blocked" not in payload
    assert payload["dry_run"] is True
    assert payload["success"] is True


def test_audit_capability_delegates_to_wired_harness() -> None:
    harness = _audit_harness_with_ok_runner("llm_local_ollama")
    server = IABVMCPServer(_build_container(capability_audit_harness=harness))
    payload = _call_tool(server, "audit_capability", capability_id="llm_local_ollama")

    assert "governance_blocked" not in payload
    assert payload["executed"] is True
    assert payload["success"] is True
    assert payload["output_preview"] == "OK"


def test_audit_capability_returns_harness_unavailable_without_wiring() -> None:
    """Sin harness en el container, se reporta degradación controlada."""

    server = IABVMCPServer(_build_container())
    payload = _call_tool(
        server, "audit_capability", capability_id="llm_local_ollama"
    )
    assert "governance_blocked" not in payload
    assert payload["error"] == "harness_unavailable"


def test_audit_capability_runner_runs_off_event_loop() -> None:
    """Regresión F3.1b: el runner de ``audit_capability`` debe ejecutarse
    fuera del hilo del event loop.

    ``browser_capture`` (y otros runners que tocan Playwright sync vía el
    ``controller_factory``) explotan con ``Please use the Async API`` si
    corren en el hilo del event loop de uvicorn. El handler MCP debe
    despachar a través de ``_run_sync_off_event_loop`` para que el runner
    vea un hilo sin loop activo.
    """

    import asyncio
    import threading

    from iabv_v15.services.evolution.capability_audit_harness import (
        CapabilityAuditHarness,
        CapabilityAuditResult,
    )

    captured: dict[str, Any] = {}

    def _probe_runner(**_kwargs: Any) -> CapabilityAuditResult:
        captured["thread"] = threading.get_ident()
        try:
            asyncio.get_running_loop()
            captured["loop_visible"] = True
        except RuntimeError:
            captured["loop_visible"] = False
        return CapabilityAuditResult(
            capability_id="llm_local_ollama",
            executed=True,
            success=True,
            output_preview="OK",
        )

    harness = CapabilityAuditHarness()
    harness.register("llm_local_ollama", _probe_runner)
    server = IABVMCPServer(_build_container(capability_audit_harness=harness))

    async def _driver() -> object:
        return _call_tool(
            server, "audit_capability", capability_id="llm_local_ollama"
        )

    payload = asyncio.run(_driver())

    assert isinstance(payload, dict)
    assert payload.get("success") is True, payload
    # Runner corrió en un hilo distinto al del event loop.
    assert captured["thread"] != threading.get_ident()
    # Y sin loop visible → Playwright sync podría arrancar si quisiera.
    assert captured["loop_visible"] is False


def test_chatgpt_web_capture_runs_off_event_loop() -> None:
    """Regresión F3.1c: ``chatgpt_web_capture`` debe despachar al worker sin loop.

    ``UIExecutionRunner._capture_browser_dom_response`` arranca Playwright
    sync vía ``BrowserSessionController``; si corre sobre el event loop de
    uvicorn explota con ``Please use the Async API``. Verificamos que el
    handler MCP despacha a ``_run_sync_off_event_loop`` y el runner ve
    un hilo sin loop activo.
    """

    import asyncio
    import threading

    captured: dict[str, Any] = {}

    class _ProbeRunner:
        def _capture_browser_dom_response(self, **kwargs: Any) -> dict[str, Any]:
            captured["thread"] = threading.get_ident()
            try:
                asyncio.get_running_loop()
                captured["loop_visible"] = True
            except RuntimeError:
                captured["loop_visible"] = False
            return {
                "launched": True,
                "prompt_pasted": True,
                "response_captured": True,
                "captured_text": "ACK",
                "capture_source": "browser_dom",
            }

    server = IABVMCPServer(_build_container(ui_execution_runner=_ProbeRunner()))

    async def _driver() -> object:
        return _call_tool(server, "chatgpt_web_capture", prompt_text="ping")

    payload = asyncio.run(_driver())

    assert isinstance(payload, dict)
    assert payload.get("captured_text") == "ACK", payload
    assert captured["thread"] != threading.get_ident()
    assert captured["loop_visible"] is False


def test_site_exploration_explore_runs_off_event_loop() -> None:
    """Regresión F3.1c: ``site_exploration_explore`` tambi\u00e9n debe despachar
    fuera del event loop porque ``SiteExplorationService`` usa Playwright sync."""

    import asyncio
    import threading

    captured: dict[str, Any] = {}

    class _ProbeService:
        def explore(self, **kwargs: Any) -> SiteExplorationResult:
            captured["thread"] = threading.get_ident()
            try:
                asyncio.get_running_loop()
                captured["loop_visible"] = True
            except RuntimeError:
                captured["loop_visible"] = False
            return SiteExplorationResult(
                hostname="example.com",
                start_url="https://example.com",
                pages=[SitePageSnapshot(url="https://example.com", title="Example")],
                success=True,
            )

    server = IABVMCPServer(_build_container(site_exploration_service=_ProbeService()))

    async def _driver() -> object:
        return _call_tool(
            server,
            "site_exploration_explore",
            start_url="https://example.com",
            max_pages=1,
        )

    payload = asyncio.run(_driver())

    assert isinstance(payload, dict)
    assert captured["thread"] != threading.get_ident()
    assert captured["loop_visible"] is False


# ----------------------------------------------------------------------
# Frente 3.3 — compare_perception_vs_ground_truth
#
# Esta tool es offline (``requires_network=False``), pero sí pasa por el
# gate de ``assistant_kind='audit'``. Verificamos que:
#   - bloqueo por audit paused aplica igual que en las otras audit tools;
#   - red caída NO bloquea (no necesita internet);
#   - sin comparator wireado, reporta ``comparator_unavailable``;
#   - con comparator wireado, delega y devuelve el payload normalizado.


class _FakeComparator:
    """Comparator de prueba que captura args y devuelve un resultado fijo."""

    def __init__(self, result: object | None = None, raise_exc: Exception | None = None) -> None:
        self._result = result
        self._raise = raise_exc
        self.calls: list[dict[str, object]] = []

    def compare(
        self,
        window_title: str,
        *,
        tool_id: str = "",
        assistant_kind: str = "",
        site_id: str = "",
    ) -> object:
        self.calls.append(
            {
                "window_title": window_title,
                "tool_id": tool_id,
                "assistant_kind": assistant_kind,
                "site_id": site_id,
            }
        )
        if self._raise is not None:
            raise self._raise
        return self._result


def test_compare_perception_blocked_when_audit_block_active() -> None:
    block = OperationalBlockRecord(
        block_type="audit_paused",
        assistant_kind="audit",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="ChatGPT",
    )

    assert payload["governance_blocked"] is True
    assert payload["reason"] == "operational_block_active"


def test_compare_perception_does_not_require_network() -> None:
    """`requires_network=False`: red caída NO debe bloquear la tool."""

    wm = _FakeWorldModelService(_default_snapshot(connected=False))
    comparator = _FakeComparator(
        result={
            "tool_id": "",
            "window_title": "ChatGPT",
            "perception_json": {},
            "ground_truth_json": {},
            "mismatches": [],
            "evidence": {},
            "error": None,
            "detail": "",
            "duration_ms": 3,
        }
    )
    server = IABVMCPServer(
        _build_container(
            world_model_service=wm,
            perception_ground_truth_comparator=comparator,
        )
    )
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="ChatGPT",
    )

    assert "governance_blocked" not in payload
    assert comparator.calls == [
        {"window_title": "ChatGPT", "tool_id": "", "assistant_kind": "", "site_id": ""}
    ]


def test_compare_perception_blocked_by_global_wildcard_block() -> None:
    block = OperationalBlockRecord(
        block_type="freeze_all",
        assistant_kind="*",
        status="active",
    )
    wm = _FakeWorldModelService(_default_snapshot(blocks=[block]))
    server = IABVMCPServer(_build_container(world_model_service=wm))
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="ChatGPT",
    )

    assert payload["governance_blocked"] is True


def test_compare_perception_returns_comparator_unavailable_without_wiring() -> None:
    """Sin comparator wireado, degradación tipada en vez de crash."""

    server = IABVMCPServer(_build_container())
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="ChatGPT",
    )

    assert "governance_blocked" not in payload
    assert payload["error"] == "comparator_unavailable"
    assert payload["window_title"] == "ChatGPT"


def test_compare_perception_invalid_title_short_circuits_before_comparator() -> None:
    comparator = _FakeComparator(result={"mismatches": []})
    server = IABVMCPServer(
        _build_container(perception_ground_truth_comparator=comparator)
    )
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="   ",
    )

    assert "governance_blocked" not in payload
    assert payload["error"] == "invalid_window_title"
    # El comparator no debe invocarse si el título es inválido.
    assert comparator.calls == []


def test_compare_perception_happy_path_delegates_and_normalizes() -> None:
    """Con red ok, sin bloqueos y comparator wireado: delega y formatea."""

    from iabv_v15.services.capture.perception_ground_truth_comparator import (
        PerceptionGroundTruthComparison,
        PerceptionMismatch,
    )

    result = PerceptionGroundTruthComparison(
        tool_id="tool-x",
        window_title="ChatGPT",
        perception_json={"latest_title": "ChatGPT"},
        ground_truth_json={"focused_window": {"title": "ChatGPT"}},
        mismatches=[
            PerceptionMismatch(
                field="capture_available",
                perceived=True,
                actual=False,
                severity="warning",
                detail="no screenshot provider",
            ),
        ],
        evidence={"ground_truth_window_matched": True},
        duration_ms=11,
    )
    comparator = _FakeComparator(result=result)
    server = IABVMCPServer(
        _build_container(perception_ground_truth_comparator=comparator)
    )
    payload = _call_tool(
        server,
        "compare_perception_vs_ground_truth",
        window_title="ChatGPT",
        tool_id="tool-x",
        assistant_kind="chatgpt_web",
        site_id="chatgpt.com",
    )

    assert "governance_blocked" not in payload
    assert payload["error"] is None
    assert payload["tool_id"] == "tool-x"
    assert payload["window_title"] == "ChatGPT"
    assert payload["mismatch_count"] == 1
    assert payload["severity_counts"] == {"critical": 0, "warning": 1, "info": 0}
    assert payload["mismatches"][0]["field"] == "capture_available"
    assert payload["duration_ms"] == 11
    assert payload["checked_at_iso"]  # iso timestamp presente
    assert comparator.calls[0]["site_id"] == "chatgpt.com"


# ---------------------------------------------------------------------------
# F2.1 — github_remote_publish_branch_as_pr
# ---------------------------------------------------------------------------


class _FakeGithubRemoteService:
    """Doble de GitHubRemoteService para el test del MCP tool."""

    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def publish_branch_as_pr(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._result


def test_github_remote_publish_branch_as_pr_delegates_and_serializes() -> None:
    # Simulamos PublishResult usando SimpleNamespace para evitar importar
    # el servicio real (el test se concentra en el adaptador MCP, no en la
    # logica del servicio, que ya cubre test_github_remote_service.py).
    result = SimpleNamespace(
        success=True,
        branch="iabv-auto/feature-x",
        base="main",
        pushed=True,
        pr_number=321,
        pr_url="https://github.com/acme/repo/pull/321",
        http_status=201,
        blocked_by_policy=False,
        required_approval=False,
        approval_granted=None,
        error=None,
        evidence_path="/tmp/evidence.json",
    )
    svc = _FakeGithubRemoteService(result)
    container = _build_container()
    container.github_remote_service = svc

    server = IABVMCPServer(container)
    payload = _call_tool(
        server,
        "github_remote_publish_branch_as_pr",
        branch="iabv-auto/feature-x",
        title="feat: algo",
        body="body",
        base="main",
        diff_lines=42,
        draft=False,
        remote="origin",
    )

    assert payload["success"] is True
    assert payload["pr_number"] == 321
    assert payload["pr_url"] == "https://github.com/acme/repo/pull/321"
    assert payload["blocked_by_policy"] is False
    assert svc.calls == [
        {
            "branch": "iabv-auto/feature-x",
            "title": "feat: algo",
            "body": "body",
            "base": "main",
            "diff_lines": 42,
            "draft": False,
            "remote": "origin",
        }
    ]


def test_github_remote_publish_branch_as_pr_returns_unavailable_without_service() -> None:
    container = _build_container()
    container.github_remote_service = None
    server = IABVMCPServer(container)
    payload = _call_tool(
        server,
        "github_remote_publish_branch_as_pr",
        branch="devin/foo",
        title="feat: x",
    )
    assert payload["error"] == "github_remote_unavailable"


# ---------------------------------------------------------------------------
# self_auto_merge MCP tool
# ---------------------------------------------------------------------------


def test_self_auto_merge_delegates_to_module_and_returns_dict(monkeypatch) -> None:
    from iabv_v15.infra.mcp import self_auto_merge as _saam

    captured: dict[str, object] = {}

    def _fake(repo, pr_number, *, method, force):
        captured["repo"] = repo
        captured["pr_number"] = pr_number
        captured["method"] = method
        captured["force"] = force
        return _saam.MergeResult(
            status="merged",
            pr_number=pr_number,
            repo=repo,
            branch="devin/1-x",
            title="feat: x",
            mergeable_state="clean",
            method=method,
            reason="ok",
            detail="ok",
            merge_sha="abc",
            branch_safe=True,
        )

    monkeypatch.setattr(_saam, "auto_merge", _fake)

    container = _build_container()
    server = IABVMCPServer(container)

    payload = _call_tool(
        server,
        "self_auto_merge",
        pr_number=77,
        repo="foo/bar",
        method="squash",
    )

    assert isinstance(payload, dict)
    assert payload["status"] == "merged"
    assert payload["merge_sha"] == "abc"
    assert payload["branch"] == "devin/1-x"
    assert payload["method"] == "squash"
    # force no se expone al MCP; siempre False
    assert captured == {
        "repo": "foo/bar",
        "pr_number": 77,
        "method": "squash",
        "force": False,
    }


def test_self_auto_merge_defaults_repo_when_none(monkeypatch) -> None:
    from iabv_v15.infra.mcp import self_auto_merge as _saam

    captured: dict[str, object] = {}

    def _fake(repo, pr_number, *, method, force):
        captured["repo"] = repo
        return _saam.MergeResult(
            status="blocked",
            pr_number=pr_number,
            repo=repo,
            method=method,
            reason="branch_not_safe",
            detail="rama feature/x no segura",
        )

    monkeypatch.setattr(_saam, "auto_merge", _fake)

    container = _build_container()
    server = IABVMCPServer(container)

    payload = _call_tool(server, "self_auto_merge", pr_number=1)

    assert captured["repo"] == "jhonf463r/Python"
    assert payload["status"] == "blocked"


def test_self_auto_merge_returns_governance_block_when_network_down() -> None:
    """Si world_model dice red caida, la tool bloquea antes de llamar a GitHub."""

    # Snapshot con red desconectada.
    snapshot = _default_snapshot()
    snapshot = snapshot.model_copy(
        update={"network_status": NetworkStatusSnapshot(connected=False, status="offline")},
    )
    container = _build_container(_snapshot=snapshot)
    server = IABVMCPServer(container)

    payload = _call_tool(server, "self_auto_merge", pr_number=5)
    assert payload.get("governance_blocked") is True
    assert payload.get("reason") == "network_unavailable"
