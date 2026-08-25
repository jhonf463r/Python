"""SessionStartBriefingService: inyecta lecciones del PortableContext a una
nueva sesion Devin (o cualquier asistente externo) sin depender de que el
humano copie/pegue nada.

Reglas AGENTS.md relevantes:
    - no crea otro cerebro ni orquestador: solo formatea lo que
      `PortableContextService` ya calcula y lo entrega a la capa externa
    - no duplica `PortableContextPackage`; lo consume
    - no fingle observacion: si el package no existe o no es consumible,
      marca los campos como `UNRESOLVED` en la propia briefing
    - respeta la fuente de verdad: secciones y `assistant_brief` del paquete
      vigente (PortableContextService) son la entrada autoritativa

La capa de transporte (HTTP a Devin API) se inyecta como callables:

    - `session_creator(prompt) -> session_id | None`
    - `message_sender(session_id, content) -> bool`

Esto permite testear la logica sin `httpx`. Los adapters existentes
(`DevinApiToolAdapter`) pueden proveer esos callables en produccion.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence


SessionCreator = Callable[[str], Optional[str]]
MessageSender = Callable[[str, str], bool]


DEFAULT_MAX_BRIEFING_CHARS = 2000
UNRESOLVED_PORTABLE_CONTEXT = "UNRESOLVED:portable_context_unavailable"
UNRESOLVED_DELIVERY = "UNRESOLVED:session_briefing_delivery"


@dataclass(frozen=True)
class SessionBriefing:
    """Resumen operativo listo para inyectar a una sesion externa."""

    summary: str
    assistant_brief: str
    lessons: tuple[str, ...]
    recommendations: tuple[str, ...]
    unresolved: tuple[str, ...]
    text: str
    generated_at_epoch: float
    package_id: str = ""
    truncated: bool = False


@dataclass(frozen=True)
class BriefingDeliveryResult:
    """Resultado de intentar entregar la briefing a una sesion remota."""

    session_id: str
    delivered: bool
    error: str = ""
    briefing_chars: int = 0


@dataclass(frozen=True)
class NewSessionBriefingResult:
    """Resultado de crear una sesion con briefing + prompt del usuario."""

    session_id: str
    created: bool
    briefing_chars: int
    composed_prompt_chars: int
    error: str = ""


class SessionStartBriefingService:
    """Construye la briefing y (opcional) la entrega a la sesion remota."""

    def __init__(
        self,
        *,
        portable_context_service: Any,
        session_creator: SessionCreator | None = None,
        message_sender: MessageSender | None = None,
        clock: Callable[[], float] | None = None,
        max_briefing_chars: int = DEFAULT_MAX_BRIEFING_CHARS,
        max_lessons: int = 5,
        max_recommendations: int = 5,
        max_unresolved: int = 5,
    ) -> None:
        self._portable_context = portable_context_service
        self._session_creator = session_creator
        self._message_sender = message_sender
        self._clock = clock or time.time
        self._max_chars = max(200, int(max_briefing_chars))
        self._max_lessons = max(0, int(max_lessons))
        self._max_recommendations = max(0, int(max_recommendations))
        self._max_unresolved = max(0, int(max_unresolved))

    # ---- API publica ------------------------------------------------

    def build_briefing(self, *, task_context: Any = None) -> SessionBriefing:
        """Arma la briefing leyendo el package vigente de `PortableContextService`.

        Si el package no puede leerse, devuelve una briefing minima con
        unresolved_fields poblados (NO inventa contenido).
        """
        package = self._load_package(task_context=task_context)
        now = self._clock()
        if package is None:
            return SessionBriefing(
                summary="",
                assistant_brief="",
                lessons=(),
                recommendations=(),
                unresolved=(UNRESOLVED_PORTABLE_CONTEXT,),
                text=self._format_unavailable_text(),
                generated_at_epoch=now,
                package_id="",
                truncated=False,
            )

        summary = str(getattr(package, "summary", "") or "").strip()
        assistant_brief = str(getattr(package, "assistant_brief", "") or "").strip()
        lessons = self._collect_lessons(package)[: self._max_lessons]
        recommendations = self._collect_recommendations(package)[: self._max_recommendations]
        unresolved = self._collect_unresolved(package)[: self._max_unresolved]
        text, truncated = self._format_briefing_text(
            summary=summary,
            assistant_brief=assistant_brief,
            lessons=lessons,
            recommendations=recommendations,
            unresolved=unresolved,
        )
        return SessionBriefing(
            summary=summary,
            assistant_brief=assistant_brief,
            lessons=tuple(lessons),
            recommendations=tuple(recommendations),
            unresolved=tuple(unresolved),
            text=text,
            generated_at_epoch=now,
            package_id=str(getattr(package, "package_id", "") or ""),
            truncated=truncated,
        )

    def deliver_to_existing_session(
        self,
        *,
        session_id: str,
        briefing: SessionBriefing | None = None,
        task_context: Any = None,
    ) -> BriefingDeliveryResult:
        """Envia la briefing como mensaje a una sesion ya existente."""
        if not session_id:
            return BriefingDeliveryResult(
                session_id="",
                delivered=False,
                error="session_id vacio",
                briefing_chars=0,
            )
        if self._message_sender is None:
            return BriefingDeliveryResult(
                session_id=session_id,
                delivered=False,
                error=UNRESOLVED_DELIVERY + ":no_message_sender",
                briefing_chars=0,
            )
        if briefing is None:
            briefing = self.build_briefing(task_context=task_context)
        try:
            ok = bool(self._message_sender(session_id, briefing.text))
        except Exception as exc:
            return BriefingDeliveryResult(
                session_id=session_id,
                delivered=False,
                error=f"message_sender_raised:{type(exc).__name__}",
                briefing_chars=len(briefing.text),
            )
        return BriefingDeliveryResult(
            session_id=session_id,
            delivered=ok,
            error="" if ok else "message_sender_returned_false",
            briefing_chars=len(briefing.text),
        )

    def brief_new_session(
        self,
        *,
        user_prompt: str,
        task_context: Any = None,
    ) -> NewSessionBriefingResult:
        """Crea una sesion nueva con briefing + user_prompt como prompt inicial."""
        briefing = self.build_briefing(task_context=task_context)
        composed = self._compose_new_session_prompt(briefing=briefing, user_prompt=user_prompt)
        if self._session_creator is None:
            return NewSessionBriefingResult(
                session_id="",
                created=False,
                briefing_chars=len(briefing.text),
                composed_prompt_chars=len(composed),
                error=UNRESOLVED_DELIVERY + ":no_session_creator",
            )
        try:
            session_id = self._session_creator(composed) or ""
        except Exception as exc:
            return NewSessionBriefingResult(
                session_id="",
                created=False,
                briefing_chars=len(briefing.text),
                composed_prompt_chars=len(composed),
                error=f"session_creator_raised:{type(exc).__name__}",
            )
        return NewSessionBriefingResult(
            session_id=str(session_id),
            created=bool(session_id),
            briefing_chars=len(briefing.text),
            composed_prompt_chars=len(composed),
            error="" if session_id else "session_creator_returned_empty",
        )

    # ---- internals --------------------------------------------------

    def _load_package(self, *, task_context: Any) -> Any | None:
        svc = self._portable_context
        if svc is None:
            return None
        try:
            return svc.current_package(task_context=task_context)
        except TypeError:
            try:
                return svc.current_package()
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _is_learning_section(section: Any) -> bool:
        title = (str(getattr(section, "title", "") or "")).lower()
        section_id = (str(getattr(section, "section_id", "") or "")).lower()
        source_kind = (str(getattr(section, "source_kind", "") or "")).lower()
        blob = " ".join((title, section_id, source_kind))
        return any(
            keyword in blob
            for keyword in ("learn", "leccion", "pattern", "patron", "adaptive", "experiment")
        )

    @staticmethod
    def _is_recommendation_section(section: Any) -> bool:
        title = (str(getattr(section, "title", "") or "")).lower()
        section_id = (str(getattr(section, "section_id", "") or "")).lower()
        source_kind = (str(getattr(section, "source_kind", "") or "")).lower()
        blob = " ".join((title, section_id, source_kind))
        return any(
            keyword in blob
            for keyword in ("recommend", "recomend", "sugger", "next_step", "siguiente")
        )

    def _collect_lessons(self, package: Any) -> list[str]:
        sections = getattr(package, "sections", None) or []
        out: list[str] = []
        for section in sections:
            if not self._is_learning_section(section):
                continue
            for item in self._section_items_as_text(section):
                if item and item not in out:
                    out.append(item)
        return out

    def _collect_recommendations(self, package: Any) -> list[str]:
        sections = getattr(package, "sections", None) or []
        out: list[str] = []
        for section in sections:
            if not self._is_recommendation_section(section):
                continue
            for item in self._section_items_as_text(section):
                if item and item not in out:
                    out.append(item)
        return out

    @staticmethod
    def _section_items_as_text(section: Any) -> list[str]:
        items = getattr(section, "items", None) or []
        out: list[str] = []
        summary = str(getattr(section, "summary", "") or "").strip()
        if summary:
            out.append(summary)
        for item in items:
            if isinstance(item, dict):
                text = (
                    item.get("summary")
                    or item.get("title")
                    or item.get("message")
                    or item.get("recommendation")
                    or ""
                )
                text = str(text).strip()
                if text:
                    out.append(text)
        return out

    def _collect_unresolved(self, package: Any) -> list[str]:
        top_level = getattr(package, "unresolved_fields", None) or []
        out: list[str] = [str(x).strip() for x in top_level if str(x).strip()]
        for section in getattr(package, "sections", None) or []:
            for field_name in getattr(section, "unresolved_fields", None) or []:
                text = str(field_name).strip()
                if text and text not in out:
                    out.append(text)
        return out

    def _format_briefing_text(
        self,
        *,
        summary: str,
        assistant_brief: str,
        lessons: Sequence[str],
        recommendations: Sequence[str],
        unresolved: Sequence[str],
    ) -> tuple[str, bool]:
        lines: list[str] = ["# IABV Session Briefing"]
        if summary:
            lines.append("")
            lines.append("## Resumen operativo")
            lines.append(summary)
        if assistant_brief:
            lines.append("")
            lines.append("## Brief para el asistente")
            lines.append(assistant_brief)
        if lessons:
            lines.append("")
            lines.append("## Lecciones aprendidas")
            lines.extend(f"- {item}" for item in lessons)
        if recommendations:
            lines.append("")
            lines.append("## Recomendaciones")
            lines.extend(f"- {item}" for item in recommendations)
        if unresolved:
            lines.append("")
            lines.append("## UNRESOLVED")
            lines.extend(f"- {item}" for item in unresolved)
        raw = "\n".join(lines).strip() + "\n"
        if len(raw) <= self._max_chars:
            return raw, False
        truncated_marker = "\n\n[truncated]\n"
        cut = self._max_chars - len(truncated_marker)
        if cut <= 0:
            return truncated_marker.strip() + "\n", True
        return raw[:cut] + truncated_marker, True

    @staticmethod
    def _format_unavailable_text() -> str:
        return (
            "# IABV Session Briefing\n\n"
            "## UNRESOLVED\n"
            "- portable_context_unavailable: no se pudo leer el paquete portable; "
            "la sesion arranca sin briefing de contexto.\n"
        )

    def _compose_new_session_prompt(
        self,
        *,
        briefing: SessionBriefing,
        user_prompt: str,
    ) -> str:
        user_prompt = (user_prompt or "").strip()
        if not briefing.text.strip():
            return user_prompt
        if not user_prompt:
            return briefing.text
        return f"{briefing.text}\n---\n{user_prompt}\n"
