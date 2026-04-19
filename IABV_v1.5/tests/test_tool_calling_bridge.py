"""Tests for ToolCallingBridge.

Verifies parsing of ``<tool_call …/>`` markup, execution via executor,
and governance-based blocking.
"""

from __future__ import annotations

from iabv_v15.services.llm.tool_calling_bridge import ToolCall, ToolCallingBridge


def test_parse_single_tool_call() -> None:
    text = 'Voy a buscar eso. <tool_call name="shell_command" args=\'{"cmd": "ls"}\'/>'
    calls = ToolCallingBridge.parse(text)
    assert len(calls) == 1
    assert calls[0].name == 'shell_command'
    assert calls[0].args == {'cmd': 'ls'}


def test_parse_multiple_tool_calls() -> None:
    text = (
        '<tool_call name="ollama_llm" args=\'{"prompt": "hola"}\'/> '
        'y tambien <tool_call name="shell_command" args=\'{"cmd": "pwd"}\'/>'
    )
    calls = ToolCallingBridge.parse(text)
    assert len(calls) == 2
    assert calls[0].name == 'ollama_llm'
    assert calls[1].name == 'shell_command'


def test_parse_no_tool_calls() -> None:
    text = 'Solo texto normal sin herramientas.'
    calls = ToolCallingBridge.parse(text)
    assert calls == []


def test_execute_blocked_by_governance_risky() -> None:
    bridge = ToolCallingBridge(governance_snapshot={'block_risky_action': True})
    tc = ToolCall(name='shell_command', args={'cmd': 'rm -rf /'})
    result = bridge.execute(tc)
    assert result.blocked is True
    assert result.success is False
    assert 'Bloqueado' in result.error


def test_execute_blocked_by_governance_approval() -> None:
    bridge = ToolCallingBridge(governance_snapshot={'approval_required': True})
    tc = ToolCall(name='playwright_browser', args={'url': 'https://example.com'})
    result = bridge.execute(tc)
    assert result.blocked is True
    assert result.success is False
    assert 'aprobacion' in result.error.lower()


def test_execute_no_executor() -> None:
    bridge = ToolCallingBridge(tool_executor=None, governance_snapshot={})
    tc = ToolCall(name='shell_command', args={})
    result = bridge.execute(tc)
    assert result.success is False
    assert result.blocked is False
    assert 'executor' in result.error.lower()


def test_parse_empty_args() -> None:
    text = '<tool_call name="some_tool" args=\'\'/>'
    calls = ToolCallingBridge.parse(text)
    assert len(calls) == 1
    assert calls[0].name == 'some_tool'
    assert calls[0].args == {}


def test_parse_malformed_json_args() -> None:
    text = '<tool_call name="some_tool" args=\'not json\'/>'
    calls = ToolCallingBridge.parse(text)
    assert len(calls) == 1
    assert calls[0].args == {}


# ---------------------------------------------------------------------------
# Regression tests for Devin Review findings on PR #6
# ---------------------------------------------------------------------------


class _RecordingInferenceRequest:
    """Minimal request double that records what the provider receives."""

    def __init__(self, user_goal: str = 'hola') -> None:
        self.request_id = 'req-1'
        self.user_goal = user_goal
        self.prompt = ''
        self.metadata: dict[str, object] = {}
        self.conversation_context: list[dict[str, str]] = []

    def model_copy(self, *, update: dict[str, object] | None = None) -> '_RecordingInferenceRequest':
        clone = _RecordingInferenceRequest(self.user_goal)
        clone.request_id = self.request_id
        clone.prompt = self.prompt
        clone.metadata = dict(self.metadata)
        clone.conversation_context = [dict(item) for item in self.conversation_context]
        if update:
            for key, value in update.items():
                setattr(clone, key, value)
        return clone


class _RecordingProvider:
    """Captures each request it receives and returns scripted summaries."""

    def __init__(self, summaries: list[str]) -> None:
        self.summaries = list(summaries)
        self.received: list[_RecordingInferenceRequest] = []

    def answer_user(self, request: _RecordingInferenceRequest) -> object:
        self.received.append(request)
        summary = self.summaries.pop(0) if self.summaries else ''

        class _Result:
            def __init__(self, s: str) -> None:
                self.summary = s
        return _Result(summary)


class _NoopExecutor:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def supports(self, session: object) -> bool:
        return True

    def execute(self, session: object) -> object:
        self.calls.append(session)

        class _Res:
            executed = True
            summary = 'herramienta ejecutada ok'
        return _Res()


def test_run_tool_loop_sends_system_prompt_and_history_to_provider() -> None:
    """Regression for Devin Review BUG 1: run_tool_loop dead code.

    The provider must receive an enriched request with the system prompt
    override injected via metadata and the accumulated assistant + tool
    messages in ``conversation_context`` — not the original unmodified
    request that would drop the system prompt silently.
    """
    initial = '<tool_call name="shell_command" args=\'{"cmd": "ls"}\'/>'
    bridge = ToolCallingBridge(tool_executor=_NoopExecutor(), governance_snapshot={})
    provider = _RecordingProvider(summaries=['respuesta final sin tool calls'])
    request = _RecordingInferenceRequest(user_goal='lista archivos')

    final, tool_calls_made, iterations = bridge.run_tool_loop(
        provider=provider,
        request=request,
        system_prompt='PROMPT SISTEMA COMPLETO',
        initial_response=initial,
        session=object(),
    )

    assert iterations == 1
    assert final == 'respuesta final sin tool calls'
    assert len(provider.received) == 1
    enriched = provider.received[0]
    assert enriched.metadata.get('system_prompt_override') == 'PROMPT SISTEMA COMPLETO'
    roles = [msg['role'] for msg in enriched.conversation_context]
    assert 'assistant' in roles
    assert 'tool' in roles
    assert tool_calls_made[0]['success'] is True


def test_run_tool_loop_passes_session_to_execute() -> None:
    """Regression for Devin Review BUG 2: execute(tc) called without session.

    Without a session, the executor gate (``session is not None and ...``)
    falls through and every tool call reports failure. The loop must forward
    the session supplied by the orchestrator so execution can actually run.
    """
    executor = _NoopExecutor()
    bridge = ToolCallingBridge(tool_executor=executor, governance_snapshot={})
    provider = _RecordingProvider(summaries=['final'])
    request = _RecordingInferenceRequest()
    sentinel_session = object()

    _, tool_calls_made, _ = bridge.run_tool_loop(
        provider=provider,
        request=request,
        system_prompt='X',
        initial_response='<tool_call name="shell_command" args=\'{}\'/>',
        session=sentinel_session,
    )

    assert executor.calls == [sentinel_session]
    assert tool_calls_made[0]['success'] is True


class _RoutingExecutor:
    """Executor that honours the tool identity via ``execute_tool_call``."""

    def __init__(self) -> None:
        self.invocations: list[tuple[str, dict[str, object], object]] = []

    def supports(self, session: object) -> bool:
        return True

    def execute_tool_call(self, tool_call: object, *, session: object = None) -> object:
        name = getattr(tool_call, 'name', '')
        args = dict(getattr(tool_call, 'args', {}) or {})
        self.invocations.append((name, args, session))

        class _Res:
            executed = True
            summary = f'ran:{name}:{sorted(args.items())}'
        return _Res()

    def execute(self, session: object) -> object:  # pragma: no cover - fallback
        class _Res:
            executed = False
            summary = 'generic'
        return _Res()


def test_execute_forwards_tool_call_identity_to_executor() -> None:
    """Regression for Devin Review BUG on tool_calling_bridge.execute.

    The bridge previously dropped ``tool_call.name`` and ``tool_call.args``
    and always called ``executor.execute(session)``. Every tool call was
    therefore silently misrouted. When the executor exposes
    ``execute_tool_call`` the bridge must forward the parsed ToolCall so
    routing reaches the correct adapter.
    """
    executor = _RoutingExecutor()
    bridge = ToolCallingBridge(tool_executor=executor, governance_snapshot={})
    sentinel_session = object()

    tc = ToolCall(name='shell_command', args={'cmd': 'ls -la'})
    result = bridge.execute(tc, session=sentinel_session)

    assert result.success is True
    assert result.blocked is False
    assert 'shell_command' in result.output
    assert "'cmd'" in result.output and "'ls -la'" in result.output
    assert len(executor.invocations) == 1
    name, args, forwarded_session = executor.invocations[0]
    assert name == 'shell_command'
    assert args == {'cmd': 'ls -la'}
    assert forwarded_session is sentinel_session


def test_execute_distinguishes_between_tool_calls() -> None:
    """The bridge must not collapse different tool calls onto the same route."""
    executor = _RoutingExecutor()
    bridge = ToolCallingBridge(tool_executor=executor, governance_snapshot={})

    bridge.execute(ToolCall(name='shell_command', args={'cmd': 'ls'}), session=object())
    bridge.execute(ToolCall(name='playwright_browser', args={'url': 'https://example.com'}), session=object())

    assert [inv[0] for inv in executor.invocations] == ['shell_command', 'playwright_browser']
    assert executor.invocations[0][1] == {'cmd': 'ls'}
    assert executor.invocations[1][1] == {'url': 'https://example.com'}
