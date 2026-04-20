"""Traductor determinístico de `PerceptionSnapshot` a frame cognitivo.

Dado un perception vivo y un ``assistant_kind``, el translator elige el
``AssistantFrameKind`` óptimo (vía ``AssistantCapabilityRegistry`` PCS) y
produce un ``CognitiveFramePayload`` con ``sections`` estructuradas +
``plain_text_rendering`` listo para inyectar como system prompt.

No hace inferencia, no consulta red, no muta estado. Si falta un dato,
se marca en ``unresolved_fields`` en vez de inventar.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    AssistantFrameKind,
    CognitiveFramePayload,
    IATraceEntry,
    PerceptionSnapshot,
)
from iabv_v15.services.roles.assistant_capability_registry import (
    AssistantCapabilityRegistry,
)

# Heurística local para estimar tokens (aprox 4 chars por token). Evita
# sumar una dependencia externa pesada sólo para un contador barato.
_CHARS_PER_TOKEN = 4
_MAX_IA_TRACE_PREVIEW = 5
_MAX_RUNTIME_SIGNAL_PREVIEW = 5


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _join_lines(parts: list[str]) -> str:
    return "\n".join(p for p in parts if p is not None)


def _world_model_summary(perception: PerceptionSnapshot) -> dict[str, Any]:
    wm = perception.world_model
    tool_statuses = wm.tool_live_status or []
    kinds = sorted({t.assistant_kind for t in tool_statuses if t.assistant_kind})
    return {
        "external_state_flags": [str(f) for f in wm.detected_blocks or []],
        "tool_live_status_known": len(tool_statuses) > 0,
        "tool_live_kinds": kinds,
    }


def _failed_ia_traces(perception: PerceptionSnapshot) -> list[IATraceEntry]:
    return [
        entry
        for entry in perception.ia_trace
        if entry.success is False and (entry.state or entry.detail or entry.outcome_summary)
    ]


def _recent_ia_traces(perception: PerceptionSnapshot, limit: int) -> list[IATraceEntry]:
    if not perception.ia_trace:
        return []
    return list(perception.ia_trace[-limit:])


def _goal_summary(perception: PerceptionSnapshot) -> dict[str, Any]:
    goal = perception.goal_context
    return {
        "active_title": goal.active_title or "",
        "status": goal.status or "",
        "progress": goal.progress,
        "priority": goal.priority,
        "blocker": goal.blocker or "",
    }


def _decision_summary(perception: PerceptionSnapshot) -> dict[str, Any]:
    decision = perception.decision_context
    route = decision.route_decision
    intent = decision.intent
    intent_label = (
        getattr(intent, "title", None)
        or getattr(intent, "intent_key", None)
        or ""
    )
    detected_role = getattr(route, "detected_role", None)
    route_label = getattr(detected_role, "value", "") if detected_role is not None else ""
    return {
        "user_goal": decision.user_goal or "",
        "intent": intent_label,
        "chosen_pack_id": decision.chosen_pack_id or "",
        "site_id": decision.site_id or "",
        "route": route_label,
        "route_reason": getattr(route, "reason", "") or "",
    }


class CognitiveFrameTranslator:
    """Convierte un `PerceptionSnapshot` al frame cognitivo de cada IA.

    El frame se elige por ``AssistantCapabilityRegistry.get_or_default``.
    Si el kind es desconocido, cae a ``STRUCTURED_QA`` (invariante del
    registry, no de esta clase).
    """

    def __init__(self, capability_registry: AssistantCapabilityRegistry) -> None:
        self._registry = capability_registry

    def translate(
        self,
        *,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
    ) -> CognitiveFramePayload:
        profile = self._registry.get_or_default(target_assistant_kind)
        frame = profile.optimal_frame

        if frame == AssistantFrameKind.DIFF_AND_TESTS:
            return self._render_diff_and_tests(perception, target_assistant_kind, frame)
        if frame == AssistantFrameKind.LONG_NARRATIVE:
            return self._render_long_narrative(perception, target_assistant_kind, frame)
        if frame == AssistantFrameKind.TASK_LIST_AND_PR:
            return self._render_task_list_and_pr(perception, target_assistant_kind, frame)
        if frame == AssistantFrameKind.JSON_TOOL_CALLS:
            return self._render_json_tool_calls(perception, target_assistant_kind, frame)
        return self._render_structured_qa(perception, target_assistant_kind, frame)

    # ------------------------------------------------------------------
    # Renderers

    def _render_diff_and_tests(
        self,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
        frame: AssistantFrameKind,
    ) -> CognitiveFramePayload:
        goal = _goal_summary(perception)
        decision = _decision_summary(perception)
        wm = _world_model_summary(perception)
        failed = _failed_ia_traces(perception)

        failed_section = [
            {
                "trace_id": t.trace_id,
                "assistant_kind": t.assistant_kind,
                "state": t.state,
                "detail": t.detail,
                "outcome_summary": t.outcome_summary,
                "tool_id": t.tool_id,
            }
            for t in failed[-_MAX_IA_TRACE_PREVIEW:]
        ]
        sections = [
            {"section": "goal", "data": goal},
            {"section": "decision", "data": decision},
            {"section": "world_model", "data": wm},
            {"section": "failed_ia_trace", "data": failed_section},
            {
                "section": "suggested_body_tools",
                "data": ["run_pytest", "read_repo_file", "world_model_snapshot"],
            },
        ]

        header = f"# Frame: diff_and_tests (target={target_assistant_kind})"
        lines = [header, ""]
        lines.append(f"Goal: {goal['active_title'] or '(sin título)'} — status={goal['status']}")
        lines.append(f"User goal: {decision['user_goal']}")
        lines.append(
            "World model flags: "
            + (", ".join(wm["external_state_flags"]) or "sin flags")
        )
        lines.append("")
        lines.append("Últimos fallos en IA trace:")
        if not failed_section:
            lines.append("- (ninguno)")
        else:
            for entry in failed_section:
                lines.append(
                    f"- [{entry['assistant_kind'] or '?'}] {entry['state']}: "
                    f"{entry['detail'] or entry['outcome_summary']}"
                )
        lines.append("")
        lines.append("Tools del cuerpo sugeridas antes de editar: run_pytest, read_repo_file.")

        rendering = _join_lines(lines)
        return CognitiveFramePayload(
            frame=frame,
            target_assistant_kind=target_assistant_kind,
            sections=sections,
            plain_text_rendering=rendering,
            token_estimate=_estimate_tokens(rendering),
            unresolved_fields=list(perception.unresolved_fields),
        )

    def _render_long_narrative(
        self,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
        frame: AssistantFrameKind,
    ) -> CognitiveFramePayload:
        goal = _goal_summary(perception)
        decision = _decision_summary(perception)
        wm = _world_model_summary(perception)
        recent = _recent_ia_traces(perception, _MAX_IA_TRACE_PREVIEW)

        sections = [
            {"section": "narrative_goal", "data": goal},
            {"section": "narrative_decision", "data": decision},
            {"section": "narrative_world_model", "data": wm},
            {
                "section": "recent_ia_trace",
                "data": [
                    {
                        "trace_id": t.trace_id,
                        "assistant_kind": t.assistant_kind,
                        "route": t.route,
                        "state": t.state,
                        "verdict": t.verdict,
                        "outcome_summary": t.outcome_summary,
                    }
                    for t in recent
                ],
            },
        ]

        lines = [
            f"# Frame: long_narrative (target={target_assistant_kind})",
            "",
            "## Contexto del objetivo",
            f"Estamos trabajando sobre: {goal['active_title'] or '(sin título)'}.",
            f"El estado declarado es '{goal['status']}' con progreso {goal['progress']:.2f}.",
            f"Bloqueador actual: {goal['blocker'] or '(ninguno)'}",
            "",
            "## Qué decidió el orquestador",
            f"User goal: {decision['user_goal']}",
            f"Intent: {decision['intent']}.",
            f"Ruta elegida: {decision['route'] or '(sin ruta)'}",
            f"Pack: {decision['chosen_pack_id'] or '(sin pack)'}; site={decision['site_id'] or '(sin site)'}",
            "",
            "## World model vivo",
            f"Flags externos: {', '.join(wm['external_state_flags']) or 'sin flags'}.",
            f"Tool live status conocido: {'sí' if wm['tool_live_status_known'] else 'no'}.",
            f"Tool kinds observados: {', '.join(wm['tool_live_kinds']) or '(ninguno)'}",
            "",
            "## Traza reciente de IAs",
        ]
        if not recent:
            lines.append("- (sin interacciones previas en este snapshot)")
        else:
            for entry in recent:
                lines.append(
                    f"- {entry.assistant_kind or '?'} / {entry.route or '?'}: "
                    f"{entry.state or '?'} — {entry.outcome_summary or entry.verdict or ''}"
                )
        lines.append("")
        lines.append(
            "Preferí las tools del cuerpo (world_model_snapshot, "
            "self_examination_current, read_repo_file) antes de asumir estado."
        )

        rendering = _join_lines(lines)
        return CognitiveFramePayload(
            frame=frame,
            target_assistant_kind=target_assistant_kind,
            sections=sections,
            plain_text_rendering=rendering,
            token_estimate=_estimate_tokens(rendering),
            unresolved_fields=list(perception.unresolved_fields),
        )

    def _render_task_list_and_pr(
        self,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
        frame: AssistantFrameKind,
    ) -> CognitiveFramePayload:
        goal = _goal_summary(perception)
        decision = _decision_summary(perception)
        subtasks = perception.goal_context.subtasks or []
        recent = _recent_ia_traces(perception, _MAX_IA_TRACE_PREVIEW)

        todos: list[dict[str, Any]] = []
        for idx, sub in enumerate(subtasks, start=1):
            todos.append(
                {
                    "index": idx,
                    "title": str(sub.get("title") or sub.get("name") or ""),
                    "status": str(sub.get("status") or ""),
                    "node_id": str(sub.get("node_id") or sub.get("id") or ""),
                }
            )

        sections = [
            {"section": "active_goal", "data": goal},
            {"section": "decision", "data": decision},
            {"section": "todos", "data": todos},
            {
                "section": "previous_pr_refs",
                "data": [
                    ref for ref in perception.decision_context.evidence_refs if "pr" in ref.lower()
                ],
            },
            {
                "section": "recent_ia_trace",
                "data": [
                    {
                        "trace_id": t.trace_id,
                        "assistant_kind": t.assistant_kind,
                        "verdict": t.verdict,
                        "success": t.success,
                    }
                    for t in recent
                ],
            },
        ]

        lines = [
            f"# Frame: task_list_and_pr (target={target_assistant_kind})",
            "",
            f"Objetivo activo: {goal['active_title'] or '(sin título)'} [status={goal['status']}]",
            f"User goal: {decision['user_goal']}",
            "",
            "## TODOs",
        ]
        if not todos:
            lines.append("1. (sin subtasks declaradas en el perception actual)")
        else:
            for item in todos:
                status = item["status"] or "pending"
                lines.append(f"{item['index']}. [{status}] {item['title']}")
        lines.append("")
        lines.append("## Evidencia previa")
        refs = [ref for ref in perception.decision_context.evidence_refs if "pr" in ref.lower()]
        if refs:
            for ref in refs:
                lines.append(f"- {ref}")
        else:
            lines.append("- (sin PRs previos registrados)")
        lines.append("")
        lines.append(
            "Al crear el PR, seguí la convención del repo "
            "(devin/<timestamp>-<slug>, usar git_pr fetch_template + create)."
        )

        rendering = _join_lines(lines)
        return CognitiveFramePayload(
            frame=frame,
            target_assistant_kind=target_assistant_kind,
            sections=sections,
            plain_text_rendering=rendering,
            token_estimate=_estimate_tokens(rendering),
            unresolved_fields=list(perception.unresolved_fields),
        )

    def _render_json_tool_calls(
        self,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
        frame: AssistantFrameKind,
    ) -> CognitiveFramePayload:
        wm = _world_model_summary(perception)
        signals = perception.runtime_signals[-_MAX_RUNTIME_SIGNAL_PREVIEW:]

        tool_catalog = [
            {"name": "world_model_snapshot", "purpose": "estado vivo del sistema"},
            {"name": "self_examination_current", "purpose": "salud y patrones operativos"},
            {"name": "run_pytest", "purpose": "ejecutar pytest del repo"},
            {"name": "read_repo_file", "purpose": "leer archivo del repo"},
            {"name": "probe_assistant_login", "purpose": "verificar login de IA externa"},
        ]

        sections = [
            {"section": "schema", "data": {"protocol": "PCS-v1", "frame": frame.value}},
            {"section": "world_model", "data": wm},
            {
                "section": "runtime_signals",
                "data": [
                    {
                        "kind": getattr(s, "kind", ""),
                        "severity": getattr(s, "severity", ""),
                        "detail": getattr(s, "detail", ""),
                    }
                    for s in signals
                ],
            },
            {"section": "tools_available", "data": tool_catalog},
        ]

        lines = [
            f"# Frame: json_tool_calls (target={target_assistant_kind})",
            "",
            "Estructura esperada: el asistente debe emitir tool_calls JSON.",
            "Tools disponibles del cuerpo (preferí estas antes que las nativas):",
        ]
        for tool in tool_catalog:
            lines.append(f"- {tool['name']}: {tool['purpose']}")
        lines.append("")
        lines.append(
            f"Estado actual: flags={', '.join(wm['external_state_flags']) or 'sin flags'}; "
            f"tool_live_kinds={', '.join(wm['tool_live_kinds']) or '(ninguno)'}"
        )

        rendering = _join_lines(lines)
        return CognitiveFramePayload(
            frame=frame,
            target_assistant_kind=target_assistant_kind,
            sections=sections,
            plain_text_rendering=rendering,
            token_estimate=_estimate_tokens(rendering),
            unresolved_fields=list(perception.unresolved_fields),
        )

    def _render_structured_qa(
        self,
        perception: PerceptionSnapshot,
        target_assistant_kind: str,
        frame: AssistantFrameKind,
    ) -> CognitiveFramePayload:
        goal = _goal_summary(perception)
        decision = _decision_summary(perception)
        wm = _world_model_summary(perception)

        qa_pairs = [
            {"q": "¿Cuál es el objetivo activo?", "a": goal["active_title"] or "(sin título)"},
            {"q": "¿Cuál es el user goal?", "a": decision["user_goal"] or "(no declarado)"},
            {"q": "¿Qué ruta eligió el orquestador?", "a": decision["route"] or "(sin ruta)"},
            {
                "q": "¿Qué flags externos hay?",
                "a": ", ".join(wm["external_state_flags"]) or "sin flags",
            },
            {"q": "¿Hay bloqueador declarado?", "a": goal["blocker"] or "(ninguno)"},
        ]
        sections = [
            {"section": "qa_pairs", "data": qa_pairs},
            {"section": "world_model", "data": wm},
            {
                "section": "body_tools_recommended",
                "data": ["world_model_snapshot", "self_examination_current"],
            },
        ]

        lines = [f"# Frame: structured_qa (target={target_assistant_kind})", ""]
        for pair in qa_pairs:
            lines.append(f"Q: {pair['q']}")
            lines.append(f"A: {pair['a']}")
            lines.append("")
        lines.append(
            "Antes de asumir estado, consultá las tools del cuerpo: "
            "world_model_snapshot, self_examination_current."
        )

        rendering = _join_lines(lines)
        return CognitiveFramePayload(
            frame=frame,
            target_assistant_kind=target_assistant_kind,
            sections=sections,
            plain_text_rendering=rendering,
            token_estimate=_estimate_tokens(rendering),
            unresolved_fields=list(perception.unresolved_fields),
        )
