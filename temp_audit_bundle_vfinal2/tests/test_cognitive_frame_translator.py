"""Tests del `CognitiveFrameTranslator` (PCS v1)."""

from __future__ import annotations

from iabv_v15.domain.models import (
    AssistantFrameKind,
    DecisionContext,
    GoalContext,
    IATraceEntry,
    IntentRouteDecision,
    PerceptionSnapshot,
    TaskContext,
    TaskIntent,
    TaskRole,
    WorldModelSnapshot,
)
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)
from iabv_v15.services.roles.cognitive_frame_translator import (
    CognitiveFrameTranslator,
)


def _perception(
    *,
    user_goal: str = "Validar el bootstrap en Windows",
    active_title: str = "Estabilizar suite UI",
    status: str = "in_progress",
    subtasks: list[dict[str, object]] | None = None,
    ia_trace: list[IATraceEntry] | None = None,
    flags: list[str] | None = None,
) -> PerceptionSnapshot:
    goal = GoalContext(
        active_title=active_title,
        status=status,
        progress=0.5,
        priority=10,
        blocker="",
        subtasks=subtasks or [],
    )
    decision = DecisionContext(
        user_goal=user_goal,
        intent=TaskIntent(intent_key="implement.pcs", title="Implementar PCS v1"),
        route_decision=IntentRouteDecision(
            detected_role=TaskRole.PROJECT_EVOLUTION,
            reason="local_role_router",
        ),
        chosen_pack_id="pack_dev",
        site_id="iabv-local",
        evidence_refs=["PR#62", "note:arch"],
    )
    from iabv_v15.domain.models import ToolLiveStatus

    tool_statuses = (
        [ToolLiveStatus(tool_id="ollama", assistant_kind="ollama_local", available=True)]
        if flags is None
        else []
    )
    wm = WorldModelSnapshot(
        detected_blocks=flags or [],
        tool_live_status=tool_statuses,
    )
    return PerceptionSnapshot(
        task_context=TaskContext(),
        decision_context=decision,
        goal_context=goal,
        world_model=wm,
        ia_trace=ia_trace or [],
    )


def _translator() -> CognitiveFrameTranslator:
    return CognitiveFrameTranslator(
        capability_registry=AssistantCapabilityRegistry.with_defaults(),
    )


def test_translate_codex_returns_diff_and_tests_frame() -> None:
    translator = _translator()
    payload = translator.translate(
        perception=_perception(),
        target_assistant_kind="codex",
    )
    assert payload.frame == AssistantFrameKind.DIFF_AND_TESTS
    assert payload.target_assistant_kind == "codex"
    section_names = {section["section"] for section in payload.sections}
    assert {
        "goal",
        "decision",
        "world_model",
        "failed_ia_trace",
        "suggested_body_tools",
    } <= section_names
    assert "run_pytest" in payload.plain_text_rendering
    assert payload.token_estimate > 0


def test_translate_codex_includes_failed_traces_only() -> None:
    failed = IATraceEntry(
        assistant_kind="chatgpt_web",
        tool_id="exec",
        state="failed",
        detail="timeout",
        success=False,
    )
    success = IATraceEntry(
        assistant_kind="codex",
        tool_id="exec",
        state="done",
        outcome_summary="ok",
        success=True,
    )
    payload = _translator().translate(
        perception=_perception(ia_trace=[failed, success]),
        target_assistant_kind="codex",
    )
    failed_section = next(s for s in payload.sections if s["section"] == "failed_ia_trace")
    assert len(failed_section["data"]) == 1
    assert failed_section["data"][0]["assistant_kind"] == "chatgpt_web"


def test_translate_claude_returns_long_narrative_frame() -> None:
    payload = _translator().translate(
        perception=_perception(),
        target_assistant_kind="claude_web",
    )
    assert payload.frame == AssistantFrameKind.LONG_NARRATIVE
    assert "## Contexto del objetivo" in payload.plain_text_rendering
    assert "## Qué decidió el orquestador" in payload.plain_text_rendering
    assert "## World model vivo" in payload.plain_text_rendering
    # la narrativa es más larga que un QA estructurado
    qa = _translator().translate(
        perception=_perception(),
        target_assistant_kind="ollama_local",  # cae en structured_qa
    )
    assert len(payload.plain_text_rendering) > len(qa.plain_text_rendering)


def test_translate_devin_returns_task_list_and_pr_frame() -> None:
    subtasks = [
        {"title": "Leer AGENTS.md", "status": "done"},
        {"title": "Correr pytest focalizado", "status": "in_progress"},
        {"title": "Abrir PR", "status": "pending"},
    ]
    payload = _translator().translate(
        perception=_perception(subtasks=subtasks),
        target_assistant_kind="devin",
    )
    assert payload.frame == AssistantFrameKind.TASK_LIST_AND_PR
    todos = next(s for s in payload.sections if s["section"] == "todos")["data"]
    assert len(todos) == 3
    assert todos[0]["index"] == 1 and todos[0]["status"] == "done"
    assert "## TODOs" in payload.plain_text_rendering
    # evidencia de PRs propagada
    prs = next(s for s in payload.sections if s["section"] == "previous_pr_refs")["data"]
    assert "PR#62" in prs


def test_translate_ollama_returns_structured_qa_frame() -> None:
    payload = _translator().translate(
        perception=_perception(flags=["window_minimized"]),
        target_assistant_kind="ollama_local",
    )
    assert payload.frame == AssistantFrameKind.STRUCTURED_QA
    qa = next(s for s in payload.sections if s["section"] == "qa_pairs")["data"]
    questions = {pair["q"] for pair in qa}
    assert "¿Cuál es el objetivo activo?" in questions
    assert "window_minimized" in payload.plain_text_rendering


def test_translate_unknown_kind_falls_back_to_structured_qa() -> None:
    payload = _translator().translate(
        perception=_perception(),
        target_assistant_kind="gpt_5_future",
    )
    assert payload.frame == AssistantFrameKind.STRUCTURED_QA
    assert payload.target_assistant_kind == "gpt_5_future"


def test_translate_json_tool_calls_frame_when_registered() -> None:
    registry = AssistantCapabilityRegistry.with_defaults()
    from iabv_v15.domain.models import AssistantCapabilityProfile

    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="function_call_agent",
            optimal_frame=AssistantFrameKind.JSON_TOOL_CALLS,
        )
    )
    translator = CognitiveFrameTranslator(capability_registry=registry)
    payload = translator.translate(
        perception=_perception(flags=["probe_needed"]),
        target_assistant_kind="function_call_agent",
    )
    assert payload.frame == AssistantFrameKind.JSON_TOOL_CALLS
    tool_catalog = next(s for s in payload.sections if s["section"] == "tools_available")["data"]
    names = {entry["name"] for entry in tool_catalog}
    assert {"world_model_snapshot", "run_pytest", "read_repo_file"} <= names


def test_payload_unresolved_fields_propagate_from_perception() -> None:
    perception = _perception()
    perception.unresolved_fields.append("live_memory_snapshot")
    payload = _translator().translate(
        perception=perception,
        target_assistant_kind="codex",
    )
    assert "live_memory_snapshot" in payload.unresolved_fields


def test_payload_serialization_round_trip() -> None:
    from iabv_v15.domain.models import CognitiveFramePayload

    payload = _translator().translate(
        perception=_perception(),
        target_assistant_kind="devin",
    )
    raw = payload.model_dump(mode="json")
    rebuilt = CognitiveFramePayload.model_validate(raw)
    assert rebuilt == payload
    assert raw["frame"] == AssistantFrameKind.TASK_LIST_AND_PR.value
