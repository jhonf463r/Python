"""Builds a system prompt that gives the local LLM full awareness of IABV state.

SystemPromptBuilder is a **pure helper** — it assembles text from live data
but never decides routes or replaces the orchestrator.  The output is a single
string (~4 k tokens max) suitable as the ``system`` message in an
OpenAI-compatible chat completion call.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from iabv_v15.domain.models import (
    ControlMasterDigest,
    EnvironmentSelfModel,
    PerceptionSnapshot,
    PortableContextPackage,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    ToolCard,
    WorldModelSnapshot,
)

_MAX_CHARS = 14_000  # rough ~4k-token cap (3.5 chars/token avg)


class SystemPromptBuilder:
    """Assemble a context-rich system prompt for the local chat LLM."""

    def build(
        self,
        perception: PerceptionSnapshot | None,
        world_model: WorldModelSnapshot | None,
        env_self_model: EnvironmentSelfModel | None,
        portable_context: PortableContextPackage | None,
        tool_registry: list[ToolCard] | None,
        *,
        governance_rules: dict[str, Any] | None = None,
        control_master_digest: ControlMasterDigest | None = None,
        self_examination: SelfExaminationSnapshot | None = None,
    ) -> str:
        sections: list[tuple[int, str]] = []

        sections.append((0, self._section_identity()))
        sections.append((1, self._section_meta_cognition()))
        sections.append((2, self._section_live_state(world_model)))
        sections.append((3, self._section_hardware(env_self_model)))
        sections.append((4, self._section_control_master(control_master_digest)))
        sections.append((5, self._section_self_examination(self_examination)))
        sections.append((6, self._section_portable_context(portable_context)))
        sections.append((7, self._section_tools(tool_registry)))
        sections.append((8, self._section_governance(governance_rules)))

        return self._truncate(sections)

    @staticmethod
    def prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Sections (ordered by priority — lower number = kept first)
    # ------------------------------------------------------------------

    @staticmethod
    def _section_identity() -> str:
        return (
            '## Quien eres\n'
            'Eres el cerebro local de IABV v1.5 — el Control Maestro que '
            'coordina Devin, Codex, Claude, ChatGPT y Ollama. Respondes en '
            'espanol claro y directo. Tienes acceso al estado vivo del '
            'sistema, herramientas registradas, autoexaminacion operativa '
            'y contexto portable acumulado. No inventas datos que no esten '
            'en el contexto proporcionado.'
        )

    @staticmethod
    def _section_live_state(wm: WorldModelSnapshot | None) -> str:
        if wm is None:
            return '## Estado vivo\nNo disponible.'
        parts: list[str] = ['## Estado vivo']

        windows = wm.active_windows or []
        if windows:
            titles = [w.title or w.app_name or '(sin titulo)' for w in windows]
            parts.append(f'Ventanas abiertas ({len(windows)}): {", ".join(titles)}')
        else:
            parts.append('Ventanas abiertas: ninguna detectada')

        if wm.focused_window is not None:
            parts.append(f'Foco: {wm.focused_window.title or wm.focused_window.app_name}')

        net = wm.network_status
        parts.append(f'Red: {net.status} ({"conectado" if net.connected else "sin conexion"})')

        if wm.detected_blocks:
            parts.append(f'Bloqueos detectados: {", ".join(wm.detected_blocks[:5])}')

        return '\n'.join(parts)

    @staticmethod
    def _section_hardware(env: EnvironmentSelfModel | None) -> str:
        if env is None:
            return '## Hardware / Runtime\nNo disponible.'
        parts: list[str] = ['## Hardware / Runtime']
        hw = env.hardware_profile or {}
        rt = env.runtime_profile or {}
        if hw:
            cpu = hw.get('cpu', '')
            ram = hw.get('ram_total_gb', '')
            gpu = hw.get('gpu', '')
            items = [f'CPU: {cpu}' if cpu else '', f'RAM: {ram} GB' if ram else '', f'GPU: {gpu}' if gpu else '']
            parts.append(', '.join(i for i in items if i))
        if rt:
            py = rt.get('python_version', '')
            os_name = rt.get('os', '')
            items = [f'Python: {py}' if py else '', f'OS: {os_name}' if os_name else '']
            parts.append(', '.join(i for i in items if i))
        risks = env.risk_signals or []
        if risks:
            parts.append(f'Riesgos: {", ".join(r.summary for r in risks[:3])}')
        return '\n'.join(parts)

    @staticmethod
    def _section_portable_context(pc: PortableContextPackage | None) -> str:
        if pc is None:
            return '## Contexto portable\nNo disponible.'
        parts: list[str] = ['## Contexto portable condensado']
        if pc.summary:
            parts.append(pc.summary[:800])
        for section in (pc.sections or [])[:4]:
            if section.title:
                parts.append(f'- {section.title}: {section.summary[:200]}')
        return '\n'.join(parts)

    _TOOL_INSTALL_HINTS: dict[str, str] = {
        'aider_coder': 'Instalar: pip install aider-chat',
        'claude_installed': 'Instalar: https://claude.ai/download (alternativa: claude_web_assisted)',
        'mcp_client': 'Iniciar MCP server (default: http://127.0.0.1:8000) o ajustar server_url en metadata',
    }

    _TOOL_WEB_ALTERNATIVES: dict[str, str] = {
        'claude_installed': 'claude_web_assisted',
        'chatgpt_installed': 'chatgpt_web_assisted',
    }

    @classmethod
    def _section_tools(cls, cards: list[ToolCard] | None) -> str:
        if not cards:
            return '## Herramientas disponibles\nNinguna registrada.'
        parts: list[str] = ['## Herramientas disponibles']
        parts.append(
            'Puedes invocar herramientas usando el formato: '
            '<tool_call name="TOOL_ID" args=\'{"key": "value"}\'/>\n'
        )
        available_ids = {c.tool_id for c in cards if c.available}
        for card in cards:
            available_tag = 'disponible' if card.available else 'no disponible'
            approval_tag = ' (requiere aprobacion)' if card.requires_human_approval else ''
            parts.append(
                f'- **{card.title}** (`{card.tool_id}`): {card.description} '
                f'[{available_tag}{approval_tag}]'
            )
            if card.capabilities:
                parts.append(f'  Capacidades: {", ".join(card.capabilities[:6])}')
            if not card.available:
                hint = cls._TOOL_INSTALL_HINTS.get(card.tool_id)
                if hint:
                    parts.append(f'  → {hint}')
                alt = cls._TOOL_WEB_ALTERNATIVES.get(card.tool_id, '')
                if alt and alt in available_ids:
                    parts.append(f'  → Ruta alternativa lista: {alt}')
        return '\n'.join(parts)

    @staticmethod
    def _section_control_master(digest: ControlMasterDigest | None) -> str:
        if digest is None:
            return '## Control Maestro\nNo disponible en esta sesion.'
        parts: list[str] = ['## Control Maestro (digest)']
        if digest.current_vision:
            parts.append(f'Vision: {digest.current_vision}')
        if digest.rules_brief:
            parts.append('Reglas estrictas:')
            for item in digest.rules_brief:
                parts.append(f'- {item}')
        if digest.active_objectives_brief:
            parts.append(
                f'Objetivos activos: {", ".join(digest.active_objectives_brief)}',
            )
        if digest.top_backlog:
            parts.append('Backlog prioritario:')
            for item in digest.top_backlog:
                parts.append(f'- {item}')
        if digest.current_risks:
            parts.append('Riesgos actuales:')
            for item in digest.current_risks:
                parts.append(f'- {item}')
        if digest.recent_decisions_brief:
            parts.append('Decisiones recientes:')
            for item in digest.recent_decisions_brief:
                parts.append(f'- {item}')
        if digest.unresolved:
            parts.append('UNRESOLVED:')
            for item in digest.unresolved:
                parts.append(f'- {item}')
        if digest.tests_state_brief:
            parts.append(f'Tests: {digest.tests_state_brief}')
        return '\n'.join(parts)

    @staticmethod
    def _section_meta_cognition() -> str:
        return (
            '## Meta-cognicion (razonamiento de segundo orden)\n'
            'NO te quedes dentro de tu marco. Antes de responder, examina '
            'el problema desde FUERA de tu frame habitual:\n'
            '1. **Autoconciencia operativa**: revisa tu propio estado — que '
            'herramientas estan disponibles, cuales fallan, que patrones se '
            'repiten. Usa la seccion de autoexaminacion para detectar '
            'degradaciones.\n'
            '2. **Deteccion de programas instalados**: no te limites a '
            'verificar si una tool esta "disponible" en el ToolRegistry. '
            'Revisa activamente que programas estan instalados en el sistema '
            '(via WorldModel, ventanas abiertas, procesos, rutas conocidas). '
            'Si un programa esta instalado pero no conectado, indica COMO '
            'conectarlo. Si no esta instalado, sugiere el comando de '
            'instalacion concreto (ej: pip install, winget install, URL de '
            'descarga).\n'
            '3. **Rutas alternativas**: cada herramienta puede tener multiples '
            'rutas (desktop app, web asistida, API, CLI). Si la ruta desktop '
            'no esta disponible, usa la ruta web. No declares una herramienta '
            'como "no disponible" si tiene una ruta alternativa funcionando. '
            'Ejemplo: si claude_installed no esta, usa claude_web_assisted.\n'
            '4. **Razonamiento de segundo orden**: no solo respondas la '
            'pregunta literal — preguntate si el enfoque actual es el '
            'correcto o si hay una ruta mejor que no se ha considerado.\n'
            '5. **Deteccion proactiva de desajustes**: si detectas que algo '
            'no funciona como deberia (tool con confianza baja, fallo '
            'recurrente, ruta bloqueada), reportalo como desajuste aunque '
            'nadie lo haya preguntado.\n'
            '6. **Coordinacion entre IAs**: cuando una tarea puede beneficiarse '
            'de comparar rutas (Devin vs Codex vs Claude), propone la '
            'comparacion via ExperimentLab. No asumas que una sola IA '
            'es siempre la mejor.\n'
            '7. **Evolucion autonoma**: propone mejoras concretas basadas en '
            'evidencia real — no esperes instrucciones para cada ajuste. '
            'Si la evidencia muestra que una ruta falla consistentemente, '
            'recomienda el cambio.\n'
            '8. **Persistencia**: no abandones un problema sin evidencia de '
            'que se resolvio. Si un desajuste persiste, escalalo con datos.\n'
            '9. **Grounding obligatorio**: cuando cites hallazgos de '
            'autoexaminacion, SIEMPRE incluye los numeros concretos de '
            'metadata (ms, %, conteos, umbrales). No digas solo el titulo '
            'del hallazgo — di "Bootstrap init lento: 4500ms (umbral 3000ms)" '
            'en vez de "hay un hallazgo de startup lento". Si no tienes '
            'datos concretos, di explicitamente "sin metricas disponibles". '
            'Nunca generalices cuando tienes datos especificos.'
        )

    @staticmethod
    def _metrics_tag(finding: SelfExaminationFinding) -> str:
        """Compact metrics suffix so the LLM sees concrete numbers."""
        meta = dict(finding.metadata or {})
        parts: list[str] = []
        observed_ms = meta.get('observed_ms')
        if observed_ms is not None:
            parts.append(f'{observed_ms}ms')
        threshold_ms = meta.get('threshold_ms')
        if threshold_ms is not None:
            parts.append(f'umbral {threshold_ms}ms')
        starvation_s = meta.get('starvation_seconds')
        if starvation_s is not None:
            parts.append(f'bloqueo {starvation_s}s')
        if not parts:
            return ''
        return f' [{", ".join(parts)}]'

    @staticmethod
    def _section_self_examination(
        snapshot: SelfExaminationSnapshot | None,
    ) -> str:
        if snapshot is None:
            return '## Autoexaminacion operativa\nNo disponible en esta sesion.'
        parts: list[str] = ['## Autoexaminacion operativa (OSES)']
        if snapshot.summary:
            parts.append(snapshot.summary[:400])

        findings = snapshot.findings or []
        if findings:
            parts.append(f'Hallazgos ({len(findings)}):')
            for f in findings[:5]:
                sev = getattr(f.severity, 'value', str(f.severity))
                metrics_tag = SystemPromptBuilder._metrics_tag(f)
                parts.append(
                    f'- [{sev}] {f.title}: {f.summary[:120]}{metrics_tag}'
                )
                if f.recommendation:
                    parts.append(f'  Recomendacion: {f.recommendation[:100]}')

        recurring = snapshot.recurring_issues or []
        if recurring:
            parts.append('Patrones recurrentes:')
            for issue in recurring[:3]:
                label = issue.get('title') or issue.get('pattern', '')
                count = issue.get('count', issue.get('occurrences', '?'))
                parts.append(f'- {label} (x{count})')

        adjustments = snapshot.recommended_adjustments or []
        if adjustments:
            parts.append('Ajustes recomendados:')
            for adj in adjustments[:3]:
                parts.append(
                    f'- {adj.get("title", adj.get("adjustment", ""))[:100]}'
                )

        validated = snapshot.validated_improvements or []
        if validated:
            parts.append(f'Mejoras validadas: {len(validated)}')

        unresolved = snapshot.unresolved_risks or []
        if unresolved:
            parts.append('Riesgos sin resolver:')
            for risk in unresolved[:3]:
                parts.append(f'- {risk[:100]}')

        return '\n'.join(parts)

    @staticmethod
    def _section_governance(rules: dict[str, Any] | None) -> str:
        parts: list[str] = ['## Reglas de gobernanza (AutonomyGovernancePolicy)']
        if rules:
            level = rules.get('autonomy_level', '')
            action = rules.get('recommended_action', '')
            blockers = rules.get('blockers', [])
            if level:
                parts.append(f'Nivel de autonomia: {level}')
            if action:
                parts.append(f'Accion recomendada: {action}')
            if rules.get('block_risky_action'):
                parts.append('Las acciones riesgosas estan BLOQUEADAS.')
            if rules.get('approval_required'):
                parts.append('Se requiere aprobacion humana antes de ejecutar.')
            if rules.get('require_sandbox'):
                parts.append('Se requiere sandbox antes de ejecutar.')
            if blockers:
                parts.append(f'Bloqueos: {"; ".join(str(b) for b in blockers[:4])}')
        else:
            parts.append(
                'Antes de usar herramientas destructivas, verifica permisos. '
                'Si falta evidencia o permiso, informa al usuario en lugar de actuar.'
            )
        return '\n'.join(parts)

    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(sections: list[tuple[int, str]]) -> str:
        sections.sort(key=lambda t: t[0])
        result: list[str] = []
        total = 0
        for _, text in sections:
            if total + len(text) > _MAX_CHARS:
                remaining = _MAX_CHARS - total
                if remaining > 100:
                    result.append(text[:remaining] + '\n...(truncado por limite)')
                break
            result.append(text)
            total += len(text)
        return '\n\n'.join(result)
