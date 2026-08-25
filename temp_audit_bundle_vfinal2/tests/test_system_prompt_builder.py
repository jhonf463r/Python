"""Tests for SystemPromptBuilder.

Verifies that the builder includes live state data (windows, tool cards)
in the generated system prompt with priority-based truncation, meta-cognition
instructions, and self-examination findings.
"""

from __future__ import annotations

from iabv_v15.domain.models import (
    ControlMasterDigest,
    EnvironmentSelfModel,
    IssueSeverity,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
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


def test_prompt_includes_control_master_section_when_digest_present() -> None:
    builder = SystemPromptBuilder()
    digest = ControlMasterDigest(
        current_vision='IABV v1.5 local-first',
        rules_brief=['[IRREVOCABLE] No crear otro cerebro'],
        active_objectives_brief=['obj-1: Cerrar capa world model'],
        top_backlog=['Integrar digest en prompt'],
        current_risks=['falta permiso de observacion'],
        recent_decisions_brief=['2026-04-18: migrar a PySide6'],
        unresolved=['validar Codex vivo en Windows'],
        tests_state_brief='390 passed / 28 failed (Linux)',
    )
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
        control_master_digest=digest,
    )
    assert 'Control Maestro' in prompt
    assert 'IABV v1.5 local-first' in prompt
    assert 'No crear otro cerebro' in prompt
    assert 'obj-1: Cerrar capa world model' in prompt
    assert 'validar Codex vivo en Windows' in prompt
    assert 'UNRESOLVED' in prompt


def test_prompt_falls_back_when_no_digest() -> None:
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    assert 'Control Maestro' in prompt
    assert 'No disponible en esta sesion' in prompt


def test_prompt_includes_meta_cognition_section() -> None:
    """Meta-cognition section is always present and teaches second-order reasoning."""
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    assert 'Meta-cognicion' in prompt
    assert 'segundo orden' in prompt
    assert 'Autoconciencia operativa' in prompt
    assert 'desajustes' in prompt
    assert 'Coordinacion entre IAs' in prompt
    assert 'Evolucion autonoma' in prompt


def test_prompt_identity_declares_operational_permissions() -> None:
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )

    assert 'cerebro local' in prompt
    assert 'Control Maestro' in prompt
    assert 'PERMISOS OPERATIVOS' in prompt
    assert 'acciones reversibles' in prompt
    assert 'sin pedir permiso' in prompt
    assert 'UNRESOLVED' in prompt


def test_compact_prompt_keeps_identity_and_live_contract_under_budget() -> None:
    builder = SystemPromptBuilder()
    world_model = WorldModelSnapshot(
        active_windows=[
            WindowObservation(title='ChatGPT - Chrome', app_name='chrome.exe'),
            WindowObservation(title='IABV v1.5', app_name='python.exe'),
        ],
    )
    env = EnvironmentSelfModel(
        environment_id='test-env',
        hardware_profile={'cpu': 'i7', 'ram_total_gb': 16},
        runtime_profile={'python_version': '3.13', 'os': 'Windows 11'},
    )

    prompt = builder.build_compact(
        world_model=world_model,
        env_self_model=env,
        governance_rules={'autonomy_level': 'autonomous_local', 'recommended_action': 'continue_local'},
    )

    assert len(prompt) <= 3500
    assert 'PERMISOS OPERATIVOS' in prompt
    assert 'Contrato de razonamiento compacto' in prompt
    assert 'ChatGPT - Chrome' in prompt
    assert 'Herramientas disponibles' not in prompt


def test_prompt_includes_self_examination_findings() -> None:
    """Self-examination snapshot with findings renders in the prompt."""
    builder = SystemPromptBuilder()
    snapshot = SelfExaminationSnapshot(
        summary='4 hallazgos detectados, 2 mejoras validadas.',
        findings=[
            SelfExaminationFinding(
                title='Tool confidence baja',
                summary='La mayoria de tools tienen confianza 0.26 porque last_verified_at es null.',
                severity=IssueSeverity.MEDIUM,
                recommendation='Ejecutar uso real de cada tool para subir confianza.',
            ),
            SelfExaminationFinding(
                title='latest_failure recurrente',
                summary='OSES detecta 7 repeticiones del patron latest_failure en la capa evolutiva.',
                severity=IssueSeverity.HIGH,
                recommendation='Investigar causa raiz del fallo recurrente.',
            ),
        ],
        recurring_issues=[
            {'title': 'latest_failure', 'count': 7},
        ],
        recommended_adjustments=[
            {'title': 'Subir confianza de tools via uso real'},
        ],
        validated_improvements=[
            {'title': 'Ollama 100% exito en language_understanding'},
            {'title': 'WorldModel detecta ventanas via Win32'},
        ],
        unresolved_risks=[
            'Codex capture_unverified + wrong_thread',
            'ChatGPT web awaiting_response',
        ],
    )
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
        self_examination=snapshot,
    )
    assert 'Autoexaminacion operativa' in prompt
    assert 'Tool confidence baja' in prompt
    assert 'latest_failure recurrente' in prompt
    assert 'Ejecutar uso real' in prompt
    assert 'latest_failure' in prompt
    assert 'x7' in prompt
    assert 'Subir confianza' in prompt
    assert 'Mejoras validadas: 2' in prompt
    assert 'Codex capture_unverified' in prompt


def test_prompt_self_examination_falls_back_when_none() -> None:
    """Without self-examination data, the section shows a fallback message."""
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    assert 'Autoexaminacion operativa' in prompt
    assert 'No disponible en esta sesion' in prompt


def test_meta_cognition_includes_installed_programs_detection() -> None:
    """Meta-cognition section teaches the LLM to detect installed programs."""
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    assert 'programas instalados' in prompt.lower() or 'Deteccion de programas' in prompt
    assert 'pip install' in prompt or 'winget install' in prompt
    assert 'Rutas alternativas' in prompt
    assert 'claude_web_assisted' in prompt


def test_tools_section_shows_install_hints_for_missing_tools() -> None:
    """When a tool is unavailable, show install hint and web alternative."""
    builder = SystemPromptBuilder()
    cards = [
        ToolCard(
            tool_id='claude_installed',
            title='Claude instalado',
            tool_type=ToolType.CUSTOM,
            description='Claude desktop app',
            adapter_key='external_assistant',
            available=False,
            capabilities=['llm_query'],
        ),
        ToolCard(
            tool_id='claude_web_assisted',
            title='Claude web',
            tool_type=ToolType.LLM_WEB_UI,
            description='Claude via browser',
            adapter_key='external_assistant',
            available=True,
            capabilities=['llm_query'],
        ),
        ToolCard(
            tool_id='aider_coder',
            title='Aider coder',
            tool_type=ToolType.CODE_EDITOR,
            description='Aider code editor',
            adapter_key='aider',
            available=False,
            capabilities=['edit_code'],
        ),
    ]
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=cards,
    )
    assert 'no disponible' in prompt
    assert 'claude.ai/download' in prompt
    assert 'pip install aider-chat' in prompt
    assert 'claude_web_assisted' in prompt
    assert 'Ruta alternativa lista' in prompt


def test_tools_section_no_hints_for_available_tools() -> None:
    """Available tools should NOT show install hints."""
    builder = SystemPromptBuilder()
    cards = [
        ToolCard(
            tool_id='ollama_llm',
            title='Ollama',
            tool_type=ToolType.LLM_LOCAL,
            description='Local LLM',
            adapter_key='ollama',
            available=True,
            capabilities=['llm_query'],
        ),
    ]
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=cards,
    )
    assert 'disponible' in prompt
    assert 'Instalar' not in prompt
    assert 'Ruta alternativa' not in prompt


def test_prompt_identity_mentions_control_maestro() -> None:
    """Identity section now identifies as the Control Maestro brain."""
    builder = SystemPromptBuilder()
    prompt = builder.build(
        perception=None,
        world_model=None,
        env_self_model=None,
        portable_context=None,
        tool_registry=None,
    )
    assert 'cerebro local' in prompt
    assert 'Control Maestro' in prompt
    assert 'Devin' in prompt
    assert 'Codex' in prompt
    assert 'Claude' in prompt
    assert 'ChatGPT' in prompt
    assert 'Ollama' in prompt
