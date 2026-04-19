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
            if hasattr(self._executor, 'execute_tool_call'):
                exec_result = self._executor.execute_tool_call(tool_call, session=session)
                return ToolCallResult(
                    tool_call=tool_call,
                    success=getattr(exec_result, 'executed', False),
                    output=getattr(exec_result, 'summary', '') or '',
                )
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
        session: AdaptiveSession | None = None,
    ) -> tuple[str, list[dict[str, Any]], int]:
        """Re-invoke the LLM with tool results until no more calls or max iterations.

        Builds a running ``conversation_context`` that is cloned into a new
        ``InferenceRequest`` on every re-invocation, so the provider sees the
        accumulated assistant + tool messages (not just the original goal).

        Returns ``(final_summary, tool_calls_made, iterations)``.
        """
        conversation: list[dict[str, str]] = [
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
                result = self.execute(tc, session=session)
                tool_calls_made.append({
                    'name': tc.name,
                    'args': tc.args,
                    'success': result.success,
                    'blocked': result.blocked,
                    'output': result.output[:500],
                    'error': result.error[:200],
                })
                conversation.append({
                    'role': 'tool',
                    'content': self._format_tool_result(result),
                })

            enriched_request = self._clone_request_with_context(
                request,
                system_prompt=system_prompt,
                conversation=conversation,
            )

            try:
                llm_result = provider.answer_user(enriched_request)
                current_text = str(getattr(llm_result, 'summary', '') or '').strip()
                conversation.append({'role': 'assistant', 'content': current_text})
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

    @staticmethod
    def _clone_request_with_context(
        request: Any,
        *,
        system_prompt: str,
        conversation: list[dict[str, str]],
    ) -> Any:
        """Clone the ``InferenceRequest`` injecting system prompt + history.

        Falls back to mutating the original when the request does not support
        ``model_copy`` (e.g. plain test doubles) so the provider still receives
        the enriched context.
        """
        metadata_update = {'system_prompt_override': system_prompt}
        conversation_copy = [dict(item) for item in conversation]
        model_copy = getattr(request, 'model_copy', None)
        if callable(model_copy):
            try:
                merged_metadata = dict(getattr(request, 'metadata', {}) or {})
                merged_metadata.update(metadata_update)
                return model_copy(update={
                    'metadata': merged_metadata,
                    'conversation_context': conversation_copy,
                })
            except Exception:
                pass
        try:
            existing_metadata = getattr(request, 'metadata', None)
            if isinstance(existing_metadata, dict):
                existing_metadata.update(metadata_update)
            else:
                setattr(request, 'metadata', dict(metadata_update))
            setattr(request, 'conversation_context', conversation_copy)
        except Exception:
            pass
        return request
