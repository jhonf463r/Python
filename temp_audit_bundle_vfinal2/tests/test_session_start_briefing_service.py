"""Tests focalizados para SessionStartBriefingService."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from iabv_v15.services.evolution.session_start_briefing_service import (
    BriefingDeliveryResult,
    NewSessionBriefingResult,
    SessionBriefing,
    SessionStartBriefingService,
    UNRESOLVED_DELIVERY,
    UNRESOLVED_PORTABLE_CONTEXT,
)


# ---- fakes minimos reemplazando PortableContextPackage/Section ---------


@dataclass
class FakeSection:
    section_id: str = ""
    title: str = ""
    summary: str = ""
    items: list = field(default_factory=list)
    source_kind: str = ""
    unresolved_fields: list = field(default_factory=list)


@dataclass
class FakePackage:
    package_id: str = "pkg-123"
    summary: str = ""
    assistant_brief: str = ""
    sections: list = field(default_factory=list)
    unresolved_fields: list = field(default_factory=list)


class FakePortableContextService:
    def __init__(self, package: FakePackage | None, *, raise_exc: Exception | None = None):
        self._package = package
        self._raise = raise_exc
        self.calls: list[dict] = []

    def current_package(self, *, task_context: Any = None, **kwargs):
        self.calls.append({"task_context": task_context, **kwargs})
        if self._raise is not None:
            raise self._raise
        return self._package


# ---- tests -------------------------------------------------------------


def test_build_briefing_uses_summary_and_assistant_brief():
    pkg = FakePackage(
        summary="Project is mid-evolution; 3 frentes en curso",
        assistant_brief="Devin: trabajar secuencial, respetar AGENTS.md",
    )
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        clock=lambda: 1000.0,
    )
    briefing = svc.build_briefing()
    assert briefing.summary == "Project is mid-evolution; 3 frentes en curso"
    assert briefing.assistant_brief == "Devin: trabajar secuencial, respetar AGENTS.md"
    assert briefing.generated_at_epoch == 1000.0
    assert briefing.package_id == "pkg-123"
    assert briefing.truncated is False
    assert "# IABV Session Briefing" in briefing.text
    assert "Resumen operativo" in briefing.text
    assert "Brief para el asistente" in briefing.text


def test_build_briefing_collects_lessons_from_learning_sections():
    pkg = FakePackage(
        sections=[
            FakeSection(
                section_id="adaptive_learning",
                title="Adaptive learning summary",
                summary="Rutas locales rinden mejor que externas en tareas simples",
                items=[
                    {"summary": "Codex lento en main, retry=1"},
                    {"title": "Claude brief mejor para arquitectura"},
                ],
                source_kind="learning",
            ),
            FakeSection(
                section_id="unrelated",
                title="Other",
                items=[{"summary": "no debe aparecer"}],
            ),
        ],
    )
    svc = SessionStartBriefingService(portable_context_service=FakePortableContextService(pkg))
    briefing = svc.build_briefing()
    assert "Rutas locales rinden mejor que externas en tareas simples" in briefing.lessons
    assert "Codex lento en main, retry=1" in briefing.lessons
    assert "Claude brief mejor para arquitectura" in briefing.lessons
    assert "no debe aparecer" not in briefing.lessons


def test_build_briefing_collects_recommendations_from_recommendation_sections():
    pkg = FakePackage(
        sections=[
            FakeSection(
                section_id="recommendations",
                title="Next steps",
                summary="Validar live tunnel antes de PR final",
                items=[{"recommendation": "Priorizar F3.3 sobre F3.1"}],
                source_kind="recommendation",
            ),
        ],
    )
    svc = SessionStartBriefingService(portable_context_service=FakePortableContextService(pkg))
    briefing = svc.build_briefing()
    assert "Validar live tunnel antes de PR final" in briefing.recommendations
    assert "Priorizar F3.3 sobre F3.1" in briefing.recommendations


def test_build_briefing_collects_unresolved_from_package_and_sections():
    pkg = FakePackage(
        unresolved_fields=["wrong_thread"],
        sections=[
            FakeSection(unresolved_fields=["ui_screenshot_provider"]),
            FakeSection(unresolved_fields=["ui_screenshot_provider", "external_probe"]),
        ],
    )
    svc = SessionStartBriefingService(portable_context_service=FakePortableContextService(pkg))
    briefing = svc.build_briefing()
    assert briefing.unresolved == ("wrong_thread", "ui_screenshot_provider", "external_probe")
    assert "## UNRESOLVED" in briefing.text
    assert "wrong_thread" in briefing.text


def test_build_briefing_is_empty_when_portable_context_missing():
    svc = SessionStartBriefingService(portable_context_service=None)
    briefing = svc.build_briefing()
    assert briefing.unresolved == (UNRESOLVED_PORTABLE_CONTEXT,)
    assert briefing.summary == ""
    assert briefing.assistant_brief == ""
    assert "# IABV Session Briefing" in briefing.text
    assert UNRESOLVED_PORTABLE_CONTEXT.split(":", 1)[1] in briefing.text


def test_build_briefing_tolerates_portable_context_exception():
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(None, raise_exc=RuntimeError("boom")),
    )
    briefing = svc.build_briefing()
    assert briefing.unresolved == (UNRESOLVED_PORTABLE_CONTEXT,)


def test_build_briefing_respects_section_kind_by_title_even_without_source_kind():
    pkg = FakePackage(
        sections=[
            FakeSection(
                title="Learned patterns",
                items=[{"summary": "Estrategia alpha ganadora"}],
            ),
            FakeSection(
                title="Recomendaciones",
                items=[{"summary": "Cerrar F3.3 antes que F3.1"}],
            ),
        ],
    )
    svc = SessionStartBriefingService(portable_context_service=FakePortableContextService(pkg))
    briefing = svc.build_briefing()
    assert "Estrategia alpha ganadora" in briefing.lessons
    assert "Cerrar F3.3 antes que F3.1" in briefing.recommendations


def test_build_briefing_honors_max_chars_and_marks_truncated():
    big_summary = "lorem ipsum " * 500
    pkg = FakePackage(summary=big_summary)
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        max_briefing_chars=500,
    )
    briefing = svc.build_briefing()
    assert briefing.truncated is True
    assert len(briefing.text) <= 500
    assert "[truncated]" in briefing.text


def test_build_briefing_caps_list_sizes():
    sections = []
    # lessons section with 20 items; cap at max_lessons
    lessons_items = [{"summary": f"leccion {i}"} for i in range(20)]
    sections.append(FakeSection(title="Learning", items=lessons_items))
    # recommendations section with 20 items; cap at max_recommendations
    recs_items = [{"recommendation": f"rec {i}"} for i in range(20)]
    sections.append(FakeSection(title="Recommendations", items=recs_items))
    pkg = FakePackage(
        unresolved_fields=[f"unres_{i}" for i in range(20)],
        sections=sections,
    )
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        max_lessons=3,
        max_recommendations=2,
        max_unresolved=4,
    )
    briefing = svc.build_briefing()
    assert len(briefing.lessons) == 3
    assert len(briefing.recommendations) == 2
    assert len(briefing.unresolved) == 4


def test_deliver_to_existing_session_invokes_sender_with_text():
    pkg = FakePackage(summary="test")
    sent: list[tuple[str, str]] = []

    def sender(sid: str, content: str) -> bool:
        sent.append((sid, content))
        return True

    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        message_sender=sender,
    )
    briefing = svc.build_briefing()
    result = svc.deliver_to_existing_session(session_id="devin-session-abc", briefing=briefing)
    assert result.delivered is True
    assert result.session_id == "devin-session-abc"
    assert result.error == ""
    assert result.briefing_chars == len(briefing.text)
    assert sent == [("devin-session-abc", briefing.text)]


def test_deliver_with_no_message_sender_returns_unresolved():
    pkg = FakePackage(summary="hi")
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
    )
    result = svc.deliver_to_existing_session(session_id="devin-x")
    assert result.delivered is False
    assert UNRESOLVED_DELIVERY in result.error


def test_deliver_with_empty_session_id_fails_fast():
    pkg = FakePackage()
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        message_sender=lambda sid, content: True,
    )
    result = svc.deliver_to_existing_session(session_id="")
    assert result.delivered is False
    assert "session_id vacio" in result.error


def test_deliver_catches_sender_exception():
    pkg = FakePackage()

    def boom(sid: str, content: str) -> bool:
        raise RuntimeError("network")

    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        message_sender=boom,
    )
    result = svc.deliver_to_existing_session(session_id="devin-x")
    assert result.delivered is False
    assert "message_sender_raised" in result.error


def test_deliver_reports_false_when_sender_returns_false():
    pkg = FakePackage()
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        message_sender=lambda sid, content: False,
    )
    result = svc.deliver_to_existing_session(session_id="devin-x")
    assert result.delivered is False
    assert result.error == "message_sender_returned_false"


def test_brief_new_session_prefixes_user_prompt_with_briefing():
    pkg = FakePackage(summary="ctx", assistant_brief="")
    created: list[str] = []

    def creator(prompt: str):
        created.append(prompt)
        return "devin-new-123"

    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        session_creator=creator,
    )
    result = svc.brief_new_session(user_prompt="please audit F3.3")
    assert result.created is True
    assert result.session_id == "devin-new-123"
    assert result.error == ""
    assert len(created) == 1
    composed = created[0]
    assert "# IABV Session Briefing" in composed
    assert "please audit F3.3" in composed
    assert "---" in composed
    assert result.composed_prompt_chars == len(composed)


def test_brief_new_session_without_creator_is_unresolved():
    pkg = FakePackage(summary="ctx")
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
    )
    result = svc.brief_new_session(user_prompt="hi")
    assert result.created is False
    assert UNRESOLVED_DELIVERY in result.error
    assert result.session_id == ""


def test_brief_new_session_handles_creator_returning_empty():
    pkg = FakePackage()
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        session_creator=lambda prompt: None,
    )
    result = svc.brief_new_session(user_prompt="hi")
    assert result.created is False
    assert result.session_id == ""
    assert "session_creator_returned_empty" in result.error


def test_brief_new_session_catches_creator_exception():
    pkg = FakePackage()

    def boom(prompt: str):
        raise RuntimeError("api down")

    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        session_creator=boom,
    )
    result = svc.brief_new_session(user_prompt="hi")
    assert result.created is False
    assert "session_creator_raised" in result.error


def test_compose_prompt_with_empty_user_prompt_yields_only_briefing():
    pkg = FakePackage(summary="ctx")
    creator_captured: list[str] = []
    svc = SessionStartBriefingService(
        portable_context_service=FakePortableContextService(pkg),
        session_creator=lambda p: (creator_captured.append(p), "sess-1")[1],
    )
    result = svc.brief_new_session(user_prompt="")
    assert result.created is True
    assert "---" not in creator_captured[0]


def test_build_briefing_passes_task_context_through():
    pkg = FakePackage()
    svc_ctx = FakePortableContextService(pkg)
    svc = SessionStartBriefingService(portable_context_service=svc_ctx)
    svc.build_briefing(task_context={"goal": "audit"})
    assert svc_ctx.calls and svc_ctx.calls[0]["task_context"] == {"goal": "audit"}
