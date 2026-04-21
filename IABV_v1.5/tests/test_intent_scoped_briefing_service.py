"""Tests focalizados para IntentScopedBriefingService."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iabv_v15.services.evolution.intent_scoped_briefing_service import (
    ASSISTANT_CHATGPT,
    ASSISTANT_CLAUDE,
    ASSISTANT_CODEX,
    ASSISTANT_DEVIN,
    ASSISTANT_OLLAMA,
    ASSISTANT_WINDSURF,
    AssistantBriefingStyle,
    DEFAULT_STYLES,
    IMPACT_HIGH,
    IMPACT_LOW,
    IntentImpact,
    IntentScopedBriefingService,
)


# ---- fakes minimos -----------------------------------------------------


@dataclass
class FakeIntent:
    intent_id: str = "i1"
    intent_key: str = "general.assistance"
    detected_role: str = "knowledge"
    sensitive: bool = False
    monetary: bool = False
    multi_step: bool = False
    missing_requirements: list = field(default_factory=list)


@dataclass
class FakeBriefing:
    summary: str = ""
    assistant_brief: str = ""
    lessons: tuple = ()
    recommendations: tuple = ()
    unresolved: tuple = ()
    text: str = ""
    generated_at_epoch: float = 0.0
    package_id: str = ""
    truncated: bool = False


class FakeSessionBriefingService:
    def __init__(self, briefing: FakeBriefing | None = None, *, raise_exc: Exception | None = None):
        self._briefing = briefing
        self._raise = raise_exc
        self.calls: list[Any] = []

    def build_briefing(self, *, task_context: Any = None):
        self.calls.append(task_context)
        if self._raise:
            raise self._raise
        return self._briefing


# ---- classify_impact ---------------------------------------------------


def test_classify_none_intent_is_low():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(None)
    assert imp.level == IMPACT_LOW
    assert "no_intent" in imp.reasons


def test_classify_general_assistance_is_low():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent())
    assert imp.level == IMPACT_LOW


def test_classify_project_evolution_intent_is_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(intent_key="project.evolution"))
    assert imp.level == IMPACT_HIGH
    assert any("intent_key=project.evolution" in r for r in imp.reasons)


def test_classify_sensitive_flag_forces_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(sensitive=True))
    assert imp.level == IMPACT_HIGH
    assert "sensitive=true" in imp.reasons


def test_classify_multi_step_forces_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(multi_step=True))
    assert imp.level == IMPACT_HIGH


def test_classify_missing_requirements_forces_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(missing_requirements=["login"]))
    assert imp.level == IMPACT_HIGH


def test_classify_external_consultation_is_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(intent_key="research.external_consultation"))
    assert imp.level == IMPACT_HIGH


def test_classify_monetary_flag_forces_high():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    imp = svc.classify_impact(FakeIntent(monetary=True))
    assert imp.level == IMPACT_HIGH
    assert "monetary=true" in imp.reasons


# ---- style_for ---------------------------------------------------------


def test_style_for_known_assistants_returns_defaults():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    assert svc.style_for(ASSISTANT_CODEX).assistant_id == ASSISTANT_CODEX
    assert svc.style_for(ASSISTANT_CLAUDE).assistant_id == ASSISTANT_CLAUDE
    assert svc.style_for(ASSISTANT_CHATGPT).assistant_id == ASSISTANT_CHATGPT
    assert svc.style_for(ASSISTANT_DEVIN).assistant_id == ASSISTANT_DEVIN
    assert svc.style_for(ASSISTANT_WINDSURF).assistant_id == ASSISTANT_WINDSURF
    assert svc.style_for(ASSISTANT_OLLAMA).assistant_id == ASSISTANT_OLLAMA


def test_style_for_unknown_assistant_yields_safe_fallback():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    style = svc.style_for("totally-new-ia")
    assert style.assistant_id == "totally-new-ia"
    assert style.max_chars > 0
    assert style.style_guide


def test_ollama_style_is_shortest_by_default():
    assert (
        DEFAULT_STYLES[ASSISTANT_OLLAMA].max_chars
        < DEFAULT_STYLES[ASSISTANT_CODEX].max_chars
    )


def test_register_style_overrides_default():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    custom = AssistantBriefingStyle(
        assistant_id=ASSISTANT_CODEX,
        headline="Codex (experiment-tuned)",
        style_guide="learned",
        max_chars=1234,
    )
    svc.register_style(custom)
    assert svc.style_for(ASSISTANT_CODEX).headline == "Codex (experiment-tuned)"
    assert svc.style_for(ASSISTANT_CODEX).max_chars == 1234


def test_register_style_ignores_empty_assistant_id():
    svc = IntentScopedBriefingService(session_start_briefing_service=None)
    svc.register_style(AssistantBriefingStyle(assistant_id="", headline="x", style_guide=""))
    assert svc.style_for("").assistant_id == "unknown"


# ---- compose_for_assistant, low impact --------------------------------


def test_low_impact_returns_user_prompt_unchanged():
    briefing_svc = FakeSessionBriefingService(FakeBriefing(summary="ctx"))
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CHATGPT,
        user_prompt="what is a hashmap?",
        intent=FakeIntent(),
    )
    assert result.impact_level == IMPACT_LOW
    assert result.used_briefing is False
    assert result.composed_prompt == "what is a hashmap?"
    assert result.briefing_chars == 0
    # briefing_svc.build_briefing should NOT be called on low-impact path
    assert briefing_svc.calls == []


def test_force_impact_low_bypasses_classification():
    briefing_svc = FakeSessionBriefingService(FakeBriefing(summary="ctx"))
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CODEX,
        user_prompt="hi",
        intent=FakeIntent(intent_key="project.evolution"),
        force_impact=IMPACT_LOW,
    )
    assert result.impact_level == IMPACT_LOW
    assert result.composed_prompt == "hi"


# ---- compose_for_assistant, high impact -------------------------------


def test_high_impact_injects_briefing_and_style_guide():
    briefing = FakeBriefing(
        summary="Mid-evolution; focus on F3.3",
        assistant_brief="Devin: autonomous",
        lessons=("lesson A",),
        recommendations=("rec A",),
        unresolved=("wrong_thread",),
        text="ignored",
    )
    briefing_svc = FakeSessionBriefingService(briefing)
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CODEX,
        user_prompt="refactor orchestrator",
        intent=FakeIntent(intent_key="project.evolution"),
    )
    assert result.impact_level == IMPACT_HIGH
    assert result.used_briefing is True
    assert "# Codex" in result.composed_prompt
    assert "## Guia de interaccion" in result.composed_prompt
    assert "## Contexto IABV" in result.composed_prompt
    assert "refactor orchestrator" in result.composed_prompt
    assert "Mid-evolution; focus on F3.3" in result.composed_prompt
    assert "lesson A" in result.composed_prompt
    assert "rec A" in result.composed_prompt
    assert "wrong_thread" in result.composed_prompt
    assert result.briefing_chars > 0
    assert result.prompt_chars == len(result.composed_prompt)


def test_ollama_style_excludes_lessons_and_unresolved():
    briefing = FakeBriefing(
        summary="ctx",
        lessons=("L1",),
        recommendations=("R1",),
        unresolved=("U1",),
    )
    briefing_svc = FakeSessionBriefingService(briefing)
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_OLLAMA,
        user_prompt="resumen",
        intent=FakeIntent(multi_step=True),
    )
    assert result.impact_level == IMPACT_HIGH
    assert "L1" not in result.composed_prompt
    assert "R1" not in result.composed_prompt
    assert "U1" not in result.composed_prompt
    # still includes headline + user prompt
    assert "Ollama" in result.composed_prompt
    assert "resumen" in result.composed_prompt


def test_chatgpt_style_excludes_lessons_but_keeps_recommendations():
    briefing = FakeBriefing(
        summary="ctx",
        lessons=("secret_lesson",),
        recommendations=("public_rec",),
    )
    briefing_svc = FakeSessionBriefingService(briefing)
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CHATGPT,
        user_prompt="explain hashmap",
        intent=FakeIntent(intent_key="research.external_consultation"),
    )
    assert "secret_lesson" not in result.composed_prompt
    assert "public_rec" in result.composed_prompt


def test_high_impact_with_empty_briefing_still_composes_headline_and_user_prompt():
    briefing_svc = FakeSessionBriefingService(FakeBriefing())
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CLAUDE,
        user_prompt="review architecture",
        intent=FakeIntent(intent_key="project.evolution"),
    )
    assert result.impact_level == IMPACT_HIGH
    assert result.used_briefing is False
    assert result.briefing_chars == 0
    assert "Claude" in result.composed_prompt
    assert "review architecture" in result.composed_prompt
    # "## Contexto IABV" section should NOT appear when briefing empty
    assert "## Contexto IABV" not in result.composed_prompt


def test_briefing_truncated_flag_propagates():
    big = "lorem ipsum " * 2000
    briefing = FakeBriefing(summary=big)
    briefing_svc = FakeSessionBriefingService(briefing)
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_OLLAMA,
        user_prompt="hi",
        intent=FakeIntent(multi_step=True),
    )
    assert result.briefing_truncated is True
    assert "[truncated]" in result.composed_prompt


def test_briefing_service_exception_degrades_to_no_briefing():
    briefing_svc = FakeSessionBriefingService(None, raise_exc=RuntimeError("down"))
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_DEVIN,
        user_prompt="do it",
        intent=FakeIntent(intent_key="project.evolution"),
    )
    assert result.impact_level == IMPACT_HIGH
    assert result.used_briefing is False
    assert result.briefing_chars == 0
    assert "do it" in result.composed_prompt


def test_compose_passes_task_context_to_briefing_service():
    briefing_svc = FakeSessionBriefingService(FakeBriefing(summary="x"))
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    svc.compose_for_assistant(
        assistant_id=ASSISTANT_CODEX,
        user_prompt="q",
        intent=FakeIntent(intent_key="project.evolution"),
        task_context={"scope": "audit"},
    )
    assert briefing_svc.calls == [{"scope": "audit"}]


def test_force_impact_high_triggers_briefing_even_on_low_intent():
    briefing_svc = FakeSessionBriefingService(FakeBriefing(summary="s"))
    svc = IntentScopedBriefingService(session_start_briefing_service=briefing_svc)
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CODEX,
        user_prompt="q",
        intent=FakeIntent(),
        force_impact=IMPACT_HIGH,
    )
    assert result.impact_level == IMPACT_HIGH
    assert result.impact_reasons == ("forced",)
    assert result.used_briefing is True


def test_style_override_in_constructor_is_honored():
    custom = AssistantBriefingStyle(
        assistant_id=ASSISTANT_CODEX,
        headline="Codex (custom)",
        style_guide="foo",
        max_chars=500,
    )
    briefing_svc = FakeSessionBriefingService(FakeBriefing(summary="s"))
    svc = IntentScopedBriefingService(
        session_start_briefing_service=briefing_svc,
        style_overrides={ASSISTANT_CODEX: custom},
    )
    result = svc.compose_for_assistant(
        assistant_id=ASSISTANT_CODEX,
        user_prompt="q",
        intent=FakeIntent(intent_key="project.evolution"),
    )
    assert "# Codex (custom)" in result.composed_prompt
