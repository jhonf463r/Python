"""Bridge between LLM text output and IABV tool execution.

ToolCallingBridge is a **pure helper** — it parses tool-call markup from
LLM responses, executes them via ``ToolOperationalExecutor``, and formats
results back as chat messages.  It never decides routes.

Wire format (emitted by the LLM, parsed here)::

    <tool_call name="tool_id" args='{"key": "value"}'/>

The bridge enforces ``AutonomyGovernancePolicy``: if ``block_risky_action``
is set the call is refused and a ``ToolCallResult`` with ``blocked=True`` is
returned instead.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSession,
    ToolTask,
    ToolCard,
)


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    tool_call: ToolCall
    success: bool
    output: str = ''
    blocked: bool = False
    error: str = ''


_TOOL_CALL_RE = re.compile(
    r'''<tool_call\s+name\s*=\s*"(?P<name>[^"]+)"\s+args\s*=\s*'(?P<args>[^']*)'\s*/>''',
    re.DOTALL,
)

_MAX_ITERATIONS = 5


class ToolCallingBridge:
    """Parse, execute, and loop tool calls between the LLM and IABV tools."""

    def __init__(
        self,
        *,
        tool_executor: Any | None = None,
        tool_registry: Any | None = None,
        governance_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self._executor = tool_executor
        self._registry = tool_registry
        self._governance = governance_snapshot or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def parse(text: str) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for match in _TOOL_CALL_RE.finditer(text):
            name = match.group('name').strip()
            raw_args = match.group('args').strip()
            try:
                args = json.loads(raw_args) if raw_args else {}
            except (json.JSONDecodeError, ValueError):
                args = {}
            calls.append(ToolCall(name=name, args=args))
        return calls

    def execute(self, tool_call: ToolCall, *, session: AdaptiveSession | None = None) -> ToolCallResult:
        if self._governance.get('block_risky_action'):
            return ToolCallResult(
                tool_call=tool_call,
                success=False,
                blocked=True,
                error='Bloqueado por AutonomyGovernancePolicy: accion riesgosa no permitida.',
            )

        if self._governance.get('approval_required'):
            return ToolCallResult(
                tool_call=tool_call,
                success=False,
                blocked=True,
                error='Bloqueado por AutonomyGovernancePolicy: requiere aprobacion humana.',
            )

        if self._executor is None:
            return ToolCallResult(
                tool_call=tool_call,
                success=False,
                error='No hay executor de herramientas configurado.',
            )

        if session is not None and hasattr(self._executor, 'supports') and not self._executor.supports(session):
            return ToolCallResult(
                tool_call=tool_call,
                success=False,
                error=f'El executor no soporta esta sesion para la herramienta {tool_call.name}.',
            )

        try:
            if session is not None and hasattr(self._executor, 'execute'):
                exec_result = self._executor.execute(session)
                return ToolCallResult(
                    tool_call=tool_call,
                    success=getattr(exec_result, 'executed', False),
                    output=getattr(exec_result, 'summary', '') or '',
                )
        except Exception as exc:
            return ToolCallResult(
                tool_call=tool_call,
                success=False,
                error=str(exc),
            )

        return ToolCallResult(
            tool_call=tool_call,
            success=False,
            error=f'No se pudo ejecutar {tool_call.name}.',
        )

    def run_tool_loop(
        self,
        *,
        provider: Any,
        request: Any,
        system_prompt: str,
        initial_response: str,
    ) -> tuple[str, list[dict[str, Any]], int]:
        """Re-invoke the LLM with tool results until no more calls or max iterations.

        Returns ``(final_summary, tool_calls_made, iterations)``.
        """
        messages: list[dict[str, str]] = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': request.user_goal},
            {'role': 'assistant', 'content': initial_response},
        ]
        tool_calls_made: list[dict[str, Any]] = []
        current_text = initial_response
        iterations = 0

        for _ in range(_MAX_ITERATIONS):
            calls = self.parse(current_text)
            if not calls:
                break
            iterations += 1
            for tc in calls:
                result = self.execute(tc)
                tool_calls_made.append({
                    'name': tc.name,
                    'args': tc.args,
                    'success': result.success,
                    'blocked': result.blocked,
                    'output': result.output[:500],
                    'error': result.error[:200],
                })
                messages.append({
                    'role': 'tool',
                    'content': self._format_tool_result(result),
                })

            try:
                llm_result = provider.answer_user(request)
                current_text = str(getattr(llm_result, 'summary', '') or '').strip()
                messages.append({'role': 'assistant', 'content': current_text})
            except Exception:
                break

        final_summary = current_text
        return final_summary, tool_calls_made, iterations

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tool_result(result: ToolCallResult) -> str:
        if result.blocked:
            return f'[BLOQUEADO] {result.error}'
        if result.success:
            return result.output or '(sin salida)'
        return f'[ERROR] {result.error}'
