"""IntentScopedBriefingService: decide si una consulta a un asistente externo
es `low` (se manda tal cual) o `high` (se envia briefing personalizado segun
el asistente destino) y compone el prompt final.

La idea es la que pidio el usuario:

    "si es una consulta simple no se hace el resto; cuando sea de alto nivel
     o el programa lo determine segun su aprendizaje con cada una, cada IA
     sepa que hacer"

AGENTS.md:
- No crea otro cerebro ni otro orquestador: usa el `TaskIntent` que ya
  produjo `IntentUnderstandingService`.
- No duplica `PortableContextPackage`: delega en `SessionStartBriefingService`
  para el briefing base.
- No decide rutas: solo compone el prompt final para el asistente elegido.
- `ExperimentLab` puede inyectar `style_overrides` despues; por ahora hay
  defaults razonables por asistente y el override es opcional.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

from iabv_v15.domain.models import (
    BootstrapStatus,
    CognitiveBootstrapResult,
    ContextResolutionMode,
)


IMPACT_LOW = "low"
IMPACT_HIGH = "high"

ASSISTANT_CODEX = "codex"
ASSISTANT_CLAUDE = "claude"
ASSISTANT_CHATGPT = "chatgpt"
ASSISTANT_DEVIN = "devin"
ASSISTANT_WINDSURF = "windsurf"
ASSISTANT_OLLAMA = "ollama"


_HIGH_IMPACT_INTENT_KEYS: frozenset[str] = frozenset(
    {
        "project.evolution",
        "research.external_consultation",
        "tools.local_workflow",
        "tools.sandbox",
        "analytics.strategy",
    }
)

_HIGH_IMPACT_ROLES: frozenset[str] = frozenset(
    {
        "project_evolution",
        "browser_automation",
        "project.evolution",
        "PROJECT_EVOLUTION",
    }
)


@dataclass(frozen=True)
class IntentImpact:
    """Clasificacion high/low con las razones que empujaron la decision."""

    level: str
    reasons: tuple[str, ...] = ()

    @property
    def is_high(self) -> bool:
        return self.level == IMPACT_HIGH


@dataclass(frozen=True)
class AssistantBriefingStyle:
    """Configuracion estable para un asistente externo."""

    assistant_id: str
    headline: str
    style_guide: str
    include_lessons: bool = True
    include_recommendations: bool = True
    include_unresolved: bool = True
    include_assistant_brief: bool = True
    max_chars: int = 2000


@dataclass(frozen=True)
class ScopedBriefingResult:
    """Resultado compuesto listo para enviar al asistente externo."""

    assistant_id: str
    impact_level: str
    impact_reasons: tuple[str, ...]
    composed_prompt: str
    briefing_chars: int
    prompt_chars: int
    used_briefing: bool
    briefing_truncated: bool
    generated_at_epoch: float
    bootstrap_result: CognitiveBootstrapResult | None = None


DEFAULT_STYLES: dict[str, AssistantBriefingStyle] = {
    ASSISTANT_CODEX: AssistantBriefingStyle(
        assistant_id=ASSISTANT_CODEX,
        headline="Codex (code-focused assistant)",
        style_guide=(
            "Devuelve patches minimos y ejecutables. Respeta contratos existentes. "
            "Incluye tests focalizados. No refactor masivo sin pedido explicito."
        ),
        include_lessons=True,
        include_recommendations=True,
        include_unresolved=True,
        include_assistant_brief=True,
        max_chars=2400,
    ),
    ASSISTANT_CLAUDE: AssistantBriefingStyle(
        assistant_id=ASSISTANT_CLAUDE,
        headline="Claude (architecture & reasoning)",
        style_guide=(
            "Prioriza razonamiento arquitectonico. Cita contratos y capas cerradas "
            "(P1-P4). Explica trade-offs. Si hay `UNRESOLVED` propone plan para "
            "cerrarlos sin inventar observacion."
        ),
        include_lessons=True,
        include_recommendations=True,
        include_unresolved=True,
        include_assistant_brief=True,
        max_chars=3000,
    ),
    ASSISTANT_CHATGPT: AssistantBriefingStyle(
        assistant_id=ASSISTANT_CHATGPT,
        headline="ChatGPT (explanatory)",
        style_guide=(
            "Explica con ejemplos concretos. Mantenlo accesible para un humano "
            "no-tecnico si aplica. No repitas el briefing; usalo solo como contexto."
        ),
        include_lessons=False,
        include_recommendations=True,
        include_unresolved=True,
        include_assistant_brief=True,
        max_chars=2000,
    ),
    ASSISTANT_DEVIN: AssistantBriefingStyle(
        assistant_id=ASSISTANT_DEVIN,
        headline="Devin (autonomous execution)",
        style_guide=(
            "Trabaja autonomo salvo bloqueo real. Abre UN PR focalizado con tests. "
            "Respeta AGENTS.md y capas cerradas. No entres en test_mode si el user "
            "no lo pide; usa `python -m pytest` como comando oficial."
        ),
        include_lessons=True,
        include_recommendations=True,
        include_unresolved=True,
        include_assistant_brief=True,
        max_chars=3000,
    ),
    ASSISTANT_WINDSURF: AssistantBriefingStyle(
        assistant_id=ASSISTANT_WINDSURF,
        headline="Windsurf (workspace-aware)",
        style_guide=(
            "Contexto del workspace y del issue. Cambios minimos, verificables. "
            "Evita tocar archivos fuera del slice salvo necesidad."
        ),
        include_lessons=True,
        include_recommendations=True,
        include_unresolved=True,
        include_assistant_brief=False,
        max_chars=2200,
    ),
    ASSISTANT_OLLAMA: AssistantBriefingStyle(
        assistant_id=ASSISTANT_OLLAMA,
        headline="Ollama (local, short context)",
        style_guide=(
            "Se breve. Una sola pregunta o tarea por vez. No incluyas contexto "
            "irrelevante; la ventana es estrecha."
        ),
        include_lessons=False,
        include_recommendations=False,
        include_unresolved=False,
        include_assistant_brief=False,
        max_chars=800,
    ),
}


class IntentScopedBriefingService:
    """Compone prompts por IA usando `TaskIntent` + `SessionStartBriefingService`."""

    def __init__(
        self,
        *,
        session_start_briefing_service: Any,
        clock: Callable[[], float] | None = None,
        style_overrides: Mapping[str, AssistantBriefingStyle] | None = None,
    ) -> None:
        self._briefing = session_start_briefing_service
        self._clock = clock or time.time
        self._style_overrides: dict[str, AssistantBriefingStyle] = dict(style_overrides or {})

    # ---- API publica -----------------------------------------------------

    def classify_impact(self, intent: Any) -> IntentImpact:
        """Determina si la consulta es low/high a partir del TaskIntent."""
        if intent is None:
            return IntentImpact(level=IMPACT_LOW, reasons=("no_intent",))
        reasons: list[str] = []
        intent_key = str(getattr(intent, "intent_key", "") or "")
        role = str(getattr(intent, "detected_role", "") or "")
        sensitive = bool(getattr(intent, "sensitive", False))
        monetary = bool(getattr(intent, "monetary", False))
        multi_step = bool(getattr(intent, "multi_step", False))
        missing = list(getattr(intent, "missing_requirements", []) or [])
        if intent_key in _HIGH_IMPACT_INTENT_KEYS:
            reasons.append(f"intent_key={intent_key}")
        role_text = getattr(role, "value", role)
        if str(role_text) in _HIGH_IMPACT_ROLES:
            reasons.append(f"role={role_text}")
        if sensitive:
            reasons.append("sensitive=true")
        if monetary:
            reasons.append("monetary=true")
        if multi_step:
            reasons.append("multi_step=true")
        if missing:
            reasons.append(f"missing_requirements={len(missing)}")
        if reasons:
            return IntentImpact(level=IMPACT_HIGH, reasons=tuple(reasons))
        return IntentImpact(
            level=IMPACT_LOW,
            reasons=(f"intent_key={intent_key or 'unknown'}", f"role={role_text or 'unknown'}"),
        )

    def register_style(self, style: AssistantBriefingStyle) -> None:
        """Permite a `ExperimentLab` inyectar un estilo aprendido en runtime."""
        if not style.assistant_id:
            return
        self._style_overrides[style.assistant_id] = style

    def style_for(self, assistant_id: str) -> AssistantBriefingStyle:
        """Devuelve el estilo vigente (override sobre default) para un asistente."""
        normalized = (assistant_id or "").strip().lower()
        if normalized in self._style_overrides:
            return self._style_overrides[normalized]
        if normalized in DEFAULT_STYLES:
            return DEFAULT_STYLES[normalized]
        return AssistantBriefingStyle(
            assistant_id=normalized or "unknown",
            headline=f"External assistant: {normalized or 'unknown'}",
            style_guide=(
                "Responde con la informacion que tengas. No inventes contexto. "
                "Si algo no esta claro, pide clarificacion."
            ),
            include_lessons=True,
            include_recommendations=True,
            include_unresolved=True,
            include_assistant_brief=True,
            max_chars=1600,
        )

    def compose_for_assistant(
        self,
        *,
        assistant_id: str,
        user_prompt: str,
        intent: Any = None,
        task_context: Any = None,
        force_impact: Optional[str] = None,
        task_id: str = "",
    ) -> ScopedBriefingResult:
        """Compone el prompt final para el asistente destino."""
        user_prompt = (user_prompt or "").strip()
        impact = (
            IntentImpact(level=force_impact, reasons=("forced",))
            if force_impact in (IMPACT_LOW, IMPACT_HIGH)
            else self.classify_impact(intent)
        )
        now = self._clock()
        style = self.style_for(assistant_id)
        if impact.level == IMPACT_LOW:
            bootstrap_result = CognitiveBootstrapResult(
                task_id=task_id,
                assistant_id=assistant_id,
                impact_level=IMPACT_LOW,
                bootstrap_status=BootstrapStatus.READY,
                context_resolution_mode=ContextResolutionMode.CANONICAL,
                used_briefing=False,
                briefing_chars=0,
                composed_prompt_chars=len(user_prompt),
                generated_at_utc=datetime.now(timezone.utc),
            )
            return ScopedBriefingResult(
                assistant_id=style.assistant_id,
                impact_level=IMPACT_LOW,
                impact_reasons=impact.reasons,
                composed_prompt=user_prompt,
                briefing_chars=0,
                prompt_chars=len(user_prompt),
                used_briefing=False,
                briefing_truncated=False,
                generated_at_epoch=now,
                bootstrap_result=bootstrap_result,
            )

        briefing = None
        bootstrap_error = ""
        bootstrap_status = BootstrapStatus.READY
        if self._briefing is not None:
            try:
                briefing = self._briefing.build_briefing(task_context=task_context)
            except TypeError:
                try:
                    briefing = self._briefing.build_briefing()
                except Exception as e:
                    briefing = None
                    bootstrap_error = f"TypeError fallback failed: {e}"
                    bootstrap_status = BootstrapStatus.DEGRADED
            except Exception as e:
                briefing = None
                bootstrap_error = f"Briefing construction failed: {e}"
                bootstrap_status = BootstrapStatus.DEGRADED
        else:
            bootstrap_error = "SessionStartBriefingService not configured"
            bootstrap_status = BootstrapStatus.DEGRADED

        briefing_text, truncated = self._render_briefing_for_style(briefing, style)
        composed = self._compose_prompt(
            headline=style.headline,
            style_guide=style.style_guide,
            briefing_text=briefing_text,
            user_prompt=user_prompt,
        )

        # Derive final bootstrap status from evidence, not just exception presence
        used_briefing = bool(briefing_text.strip())
        if not used_briefing and bootstrap_status == BootstrapStatus.READY:
            # Briefing was expected (IMPACT_HIGH) but not produced without exception
            bootstrap_status = BootstrapStatus.DEGRADED
            if not bootstrap_error:
                bootstrap_error = "briefing_not_available"
                if briefing is None:
                    bootstrap_error = "briefing_empty"
                elif not briefing_text.strip():
                    bootstrap_error = "briefing_empty_rendered"

        bootstrap_result = CognitiveBootstrapResult(
            task_id=task_id,
            assistant_id=assistant_id,
            impact_level=IMPACT_HIGH,
            bootstrap_status=bootstrap_status,
            context_resolution_mode=ContextResolutionMode.CANONICAL,
            used_briefing=used_briefing,
            briefing_chars=len(briefing_text),
            composed_prompt_chars=len(composed),
            bootstrap_error=bootstrap_error,
            degraded_reason=bootstrap_error if bootstrap_status == BootstrapStatus.DEGRADED else "",
            generated_at_utc=datetime.now(timezone.utc),
        )

        return ScopedBriefingResult(
            assistant_id=style.assistant_id,
            impact_level=IMPACT_HIGH,
            impact_reasons=impact.reasons,
            composed_prompt=composed,
            briefing_chars=len(briefing_text),
            prompt_chars=len(composed),
            used_briefing=bool(briefing_text.strip()),
            briefing_truncated=truncated,
            generated_at_epoch=now,
            bootstrap_result=bootstrap_result,
        )

    # ---- internals -------------------------------------------------------

    def _render_briefing_for_style(
        self,
        briefing: Any,
        style: AssistantBriefingStyle,
    ) -> tuple[str, bool]:
        if briefing is None:
            return "", False
        summary = str(getattr(briefing, "summary", "") or "").strip()
        assistant_brief = str(getattr(briefing, "assistant_brief", "") or "").strip()
        lessons = tuple(getattr(briefing, "lessons", ()) or ())
        recommendations = tuple(getattr(briefing, "recommendations", ()) or ())
        unresolved = tuple(getattr(briefing, "unresolved", ()) or ())

        lines: list[str] = []
        if summary:
            lines.append("## Resumen operativo")
            lines.append(summary)
        if style.include_assistant_brief and assistant_brief:
            if lines:
                lines.append("")
            lines.append("## Brief para el asistente")
            lines.append(assistant_brief)
        if style.include_lessons and lessons:
            if lines:
                lines.append("")
            lines.append("## Lecciones")
            lines.extend(f"- {item}" for item in lessons)
        if style.include_recommendations and recommendations:
            if lines:
                lines.append("")
            lines.append("## Recomendaciones")
            lines.extend(f"- {item}" for item in recommendations)
        if style.include_unresolved and unresolved:
            if lines:
                lines.append("")
            lines.append("## UNRESOLVED")
            lines.extend(f"- {item}" for item in unresolved)

        raw = "\n".join(lines).strip()
        if not raw:
            return "", False
        max_chars = max(200, style.max_chars)
        if len(raw) <= max_chars:
            return raw + "\n", False
        marker = "\n\n[truncated]\n"
        cut = max_chars - len(marker)
        if cut <= 0:
            return marker.strip() + "\n", True
        return raw[:cut] + marker, True

    @staticmethod
    def _compose_prompt(
        *,
        headline: str,
        style_guide: str,
        briefing_text: str,
        user_prompt: str,
    ) -> str:
        segments: list[str] = []
        segments.append(f"# {headline}")
        if style_guide:
            segments.append("")
            segments.append("## Guia de interaccion")
            segments.append(style_guide)
        if briefing_text.strip():
            segments.append("")
            segments.append("## Contexto IABV")
            segments.append(briefing_text.strip())
        segments.append("")
        segments.append("---")
        segments.append("")
        segments.append("## Peticion del humano")
        segments.append(user_prompt or "(vacio)")
        return "\n".join(segments).strip() + "\n"
