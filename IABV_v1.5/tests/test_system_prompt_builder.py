"""Tests for SystemPromptBuilder.

Verifies that the builder includes live state data (windows, tool cards)
in the generated system prompt with priority-based truncation.
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    EnvironmentSelfModel,
    ToolCard,
    ToolType,
    WindowObservation,
    WorldModelSnapshot,
)
from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder


def test_prompt_includes_windows_and_tool_cards() -> None:
    """2 windows + 3 tool cards -> prompt includes all 3 card names and 2 window titles."""
    builder = SystemPromptBuilder()

    world_model = WorldModelSnapshot(
        active_windows=[
            WindowObservation(title='Chrome - Google', app_name='chrome.exe'),
            WindowObservation(title='Terminal - bash', app_name='WindowsTerminal.exe'),
        ],
    )
    env = EnvironmentSelfModel(
        environment_id='test-env',
        hardware_profile={'cpu': 'i7-12700', 'ram_total_gb': 32},
        runtime_profile={'python_version': '3.13', 'os': 'Windows 11'},
    )
    cards = [
        ToolCard(
            tool_id='playwright_browser',
            title='Playwright browser',
            tool_type=ToolType.BROWSER,
            description='Automatizacion web local.',
            adapter_key='playwright',
            capabilities=['open_url', 'click'],
        ),
        ToolCard(
            tool_id='ollama_llm',
            title='Ollama local',
            tool_type=ToolType.LLM_LOCAL,
            description='Proveedor local para inferencia.',
            adapter_key='ollama',
            capabilities=['llm_query', 'summarize'],
        ),
        ToolCard(
            tool_id='shell_command',
            title='Shell local seguro',
            tool_type=ToolType.SHELL,
            description='Wrapper para comandos locales.',
            adapter_key='shell',
            capabilities=['run_command'],
        ),
    ]

    prompt = builder.build(
        perception=None,
        world_model=world_model,
        env_self_model=env,
        portable_context=None,
        tool_registry=cards,
    )

    assert 'Chrome - Google' in prompt
    assert 'Terminal - bash' in prompt

    assert 'Playwright browser' in prompt
    assert 'Ollama local' in prompt
    assert 'Shell local seguro' in prompt

    assert 'Herramientas disponibles' in prompt
    assert 'Estado vivo' in prompt


def test_prompt_hash_is_stable() -> None:
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    h1 = SystemPromptBuilder.prompt_hash(prompt)
    h2 = SystemPromptBuilder.prompt_hash(prompt)
    assert h1 == h2
    assert len(h1) == 16


def test_prompt_truncation_respects_limit() -> None:
    builder = SystemPromptBuilder()
    huge_cards = [
        ToolCard(
            tool_id=f'tool_{i}',
            title=f'Tool {i} with a very long name to fill space',
            tool_type=ToolType.CUSTOM,
            description='x' * 500,
            adapter_key='test',
            capabilities=[f'cap_{j}' for j in range(10)],
        )
        for i in range(100)
    ]
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=huge_cards,
    )
    assert len(prompt) <= 15_000
