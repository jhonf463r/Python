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
    ) -> None:
        self.world_model_service = world_model_service
        self.portable_context_service = portable_context_service
        self.operational_self_examination_service = operational_self_examination_service
        self.site_exploration_service = site_exploration_service
        self.adaptive_task_orchestrator = adaptive_task_orchestrator
        self.ui_execution_runner = ui_execution_runner
        self.site_manual_repository = site_manual_repository


def _build_container(**overrides: object) -> _FakeContainer:
    snapshot = WorldModelSnapshot(
        external_state_flags=[],
        environment=EnvironmentSelfModel(),
    )
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
