"""Tests for ``OpenAICompatLocalProvider`` system-prompt + history handling.

These guard the contract used by ``ToolCallingBridge`` and
``AdaptiveTaskOrchestrator._maybe_invoke_local_chat_llm``: when a request
carries ``metadata['system_prompt_override']`` or ``conversation_context``,
the provider must forward that content to the Ollama-compatible endpoint
instead of dropping it.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    InferenceRequest,
    ProviderConfig,
    ProviderKind,
    TaskRole,
)
from iabv_v15.services.providers import openai_compat_local_provider as mod


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {'choices': [{'message': {'content': self._content}}]}


class _FakeClient:
    def __init__(self, *, captured: dict[str, Any], content: str) -> None:
        self._captured = captured
        self._content = content

    def __enter__(self) -> '_FakeClient':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        self._captured['url'] = url
        self._captured['payload'] = json
        return _FakeResponse(self._content)


def _install_fake_httpx(monkeypatch, captured: dict[str, Any], content: str = 'ok') -> None:
    class _FakeHttpx:
        @staticmethod
        def Client(*, timeout: float) -> _FakeClient:
            return _FakeClient(captured=captured, content=content)

    monkeypatch.setattr(mod, 'httpx', _FakeHttpx)


def _build_request(**overrides: Any) -> InferenceRequest:
    base: dict[str, Any] = {
        'user_goal': 'hola',
        'prompt': '',
        'task_role': TaskRole.TRAINING,
    }
    base.update(overrides)
    return InferenceRequest(**base)


def _build_provider() -> mod.OpenAICompatLocalProvider:
    config = ProviderConfig(
        name='ollama-local',
        kind=ProviderKind.LOCAL,
        base_url='http://localhost:11434/v1',
        model='llama3.1:8b-instruct-q4_K_M',
        enabled=True,
    )
    return mod.OpenAICompatLocalProvider(config=config)


def test_answer_user_uses_system_prompt_override(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_httpx(monkeypatch, captured)
    provider = _build_provider()
    request = _build_request(metadata={'system_prompt_override': 'SOY EL SISTEMA IABV'})

    provider.answer_user(request)

    messages = captured['payload']['messages']
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'SOY EL SISTEMA IABV'


def test_answer_user_forwards_conversation_context(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_httpx(monkeypatch, captured)
    provider = _build_provider()
    request = _build_request(
        conversation_context=[
            {'role': 'assistant', 'content': '<tool_call name="x" args=\'{}\'/>'},
            {'role': 'tool', 'content': 'salida de la herramienta'},
            {'role': 'assistant', 'content': ''},  # filtered: empty content
            {'role': 'stranger', 'content': 'ignored'},  # filtered: invalid role
        ],
    )

    provider.answer_user(request)

    messages = captured['payload']['messages']
    roles = [msg['role'] for msg in messages]
    assert roles[:2] == ['system', 'user']
    forwarded = messages[2:]
    assert [msg['role'] for msg in forwarded] == ['assistant', 'tool']
    assert forwarded[1]['content'] == 'salida de la herramienta'


def test_answer_user_falls_back_to_default_system_instruction(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_httpx(monkeypatch, captured)
    provider = _build_provider()
    request = _build_request()

    provider.answer_user(request)

    messages = captured['payload']['messages']
    assert messages[0]['role'] == 'system'
    assert 'IABV v1.5' in messages[0]['content']
