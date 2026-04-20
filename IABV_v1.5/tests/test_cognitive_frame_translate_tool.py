"""End-to-end tests para la MCP tool ``cognitive_frame_translate`` (PCS v1).

Cubre el camino que faltaba en #64: la tool consumía un método inexistente
sobre ``UniversalPerceptionService``. Ahora construye el
``PerceptionSnapshot`` vía ``TaskContextAssembler.build_perception_snapshot``.

Estos tests usan el translator real + un fake muy delgado del context
assembler para ejercitar el wiring sin arrastrar repositorios completos.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from iabv_v15.domain.models import (
    DecisionContext,
    GoalContext,
    InferenceRequest,
    IntentRouteDecision,
    PerceptionSnapshot,
    TaskContext,
    TaskIntent,
    TaskRole,
)
from iabv_v15.infra.mcp.server import IABVMCPServer
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)
from iabv_v15.services.roles.cognitive_frame_translator import (
    CognitiveFrameTranslator,
)


class _FakeTaskContextAssembler:
    """Implementa `build_perception_snapshot` con un snapshot mínimo."""

    def __init__(self) -> None:
        self.calls: list[tuple[InferenceRequest, TaskIntent]] = []

    def build_perception_snapshot(
        self,
        *,
        request: InferenceRequest,
        intent: TaskIntent,
        **_: Any,
    ) -> PerceptionSnapshot:
        self.calls.append((request, intent))
        return PerceptionSnapshot(
            task_context=TaskContext(),
            decision_context=DecisionContext(
                user_goal=request.user_goal,
                intent=intent,
                route_decision=IntentRouteDecision(detected_role=TaskRole.KNOWLEDGE),
            ),
            goal_context=GoalContext(),
        )


def _build_server(
    *,
    include_translator: bool = True,
    include_assembler: bool = True,
) -> tuple[IABVMCPServer, _FakeTaskContextAssembler | None]:
    assembler = _FakeTaskContextAssembler() if include_assembler else None
    registry = AssistantCapabilityRegistry.with_defaults()
    translator = (
        CognitiveFrameTranslator(capability_registry=registry)
        if include_translator
        else None
    )
    container = SimpleNamespace(
        assistant_capability_registry=registry,
        cognitive_frame_translator=translator,
        task_context_assembler=assembler,
    )
    return IABVMCPServer(container), assembler


def _call(server: IABVMCPServer, **kwargs: Any) -> dict[str, Any]:
    tool = server.mcp._tool_manager._tools["cognitive_frame_translate"]
    return tool.fn(**kwargs)


def test_cognitive_frame_translate_returns_payload_for_known_kind() -> None:
    server, assembler = _build_server()
    payload = _call(server, target_assistant_kind="codex")
    assert "error" not in payload, payload
    assert payload["target_assistant_kind"] == "codex"
    assert payload["frame"] == "diff_and_tests"
    assert isinstance(payload["sections"], list) and payload["sections"]
    assert isinstance(payload["plain_text_rendering"], str)
    assert payload["token_estimate"] >= 0
    assert assembler is not None and len(assembler.calls) == 1


def test_cognitive_frame_translate_falls_back_to_structured_qa() -> None:
    server, _ = _build_server()
    payload = _call(server, target_assistant_kind="bogus_kind_xyz")
    assert "error" not in payload, payload
    assert payload["frame"] == "structured_qa"


def test_cognitive_frame_translate_propagates_snapshot_hint() -> None:
    server, _ = _build_server()
    payload = _call(
        server,
        target_assistant_kind="claude_web",
        snapshot_hint="audit-2026-04-20",
    )
    assert "error" not in payload
    assert payload["frame"] == "long_narrative"
    assert payload["metadata"]["snapshot_hint"] == "audit-2026-04-20"


def test_cognitive_frame_translate_reports_translator_unavailable() -> None:
    server, _ = _build_server(include_translator=False)
    payload = _call(server, target_assistant_kind="codex")
    assert payload["error"] == "translator_unavailable"
    assert payload["target_assistant_kind"] == "codex"


def test_cognitive_frame_translate_reports_perception_unavailable_when_assembler_missing() -> None:
    server, _ = _build_server(include_assembler=False)
    payload = _call(server, target_assistant_kind="codex")
    assert payload["error"] == "perception_unavailable"
    assert "TaskContextAssembler" in payload["detail"]


def test_cognitive_frame_translate_reports_perception_unavailable_when_assembler_returns_none() -> None:
    server, assembler = _build_server()
    assert assembler is not None
    assembler.build_perception_snapshot = lambda **_: None  # type: ignore[assignment]
    payload = _call(server, target_assistant_kind="codex")
    assert payload["error"] == "perception_unavailable"
    assert "devolvió None" in payload["detail"]


def test_cognitive_frame_translate_reports_perception_error_on_assembler_crash() -> None:
    server, assembler = _build_server()
    assert assembler is not None

    def _boom(**_: Any) -> PerceptionSnapshot:
        raise RuntimeError("assembler exploded")

    assembler.build_perception_snapshot = _boom  # type: ignore[assignment]
    payload = _call(server, target_assistant_kind="codex")
    assert payload["error"] == "perception_error"
    assert "assembler exploded" in payload["detail"]
