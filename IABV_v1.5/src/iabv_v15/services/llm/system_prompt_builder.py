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
    ) -> str:
        sections: list[tuple[int, str]] = []

        sections.append((0, self._section_identity()))
        sections.append((1, self._section_control_master(control_master_digest)))
        sections.append((2, self._section_live_state(world_model)))
        sections.append((3, self._section_hardware(env_self_model)))
        sections.append((4, self._section_portable_context(portable_context)))
        sections.append((5, self._section_tools(tool_registry)))
        sections.append((6, self._section_governance(governance_rules)))

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
            'Eres el asistente local de IABV v1.5. Respondes en espanol claro '
            'y directo. Tienes acceso al estado vivo del sistema, herramientas '
            'registradas y contexto portable acumulado. No inventas datos que '
            'no esten en el contexto proporcionado.'
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

    @staticmethod
    def _section_tools(cards: list[ToolCard] | None) -> str:
        if not cards:
            return '## Herramientas disponibles\nNinguna registrada.'
        parts: list[str] = ['## Herramientas disponibles']
        parts.append(
            'Puedes invocar herramientas usando el formato: '
            '<tool_call name="TOOL_ID" args=\'{"key": "value"}\'/>\n'
        )
        for card in cards:
            available_tag = 'disponible' if card.available else 'no disponible'
            approval_tag = ' (requiere aprobacion)' if card.requires_human_approval else ''
            parts.append(
                f'- **{card.title}** (`{card.tool_id}`): {card.description} '
                f'[{available_tag}{approval_tag}]'
            )
            if card.capabilities:
                parts.append(f'  Capacidades: {", ".join(card.capabilities[:6])}')
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
