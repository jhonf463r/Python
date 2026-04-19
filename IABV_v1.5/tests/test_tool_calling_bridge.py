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
