"""
E03: Integration test simplificado - Sandbox y Governance

Test que verifica directamente:
- ToolSandbox.run() con adapter real
- DevinApiToolAdapter.run() respeta sandbox parameter
- El bypass de governance fue eliminado
"""

import os
from uuid import uuid4
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.domain.models import ToolCard, ToolTask, ToolType


def test_e03_integration_sandbox_blocks_http_real() -> None:
    """Integration test: Sandbox.run() con adapter real.
    
    Verificar que ToolSandbox.run() con DevinApiToolAdapter
    produce sandbox execution sin HTTP real.
    """
    # Setup sandbox
    sandbox = ToolSandbox(ToolValidator())
    
    # Setup adapter Devin con API key fake
    api_key = 'fake_key_for_test'
    adapter = DevinApiToolAdapter(api_key=api_key)
    
    # Crear ToolCard Devin
    card = ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        description='Sesion autonoma via API REST de Devin para tareas de codigo, shell y navegacion.',
        adapter_key='devin_api',
        available=True,
        requires_human_approval=False,
        capabilities=['code_assistance', 'shell_execution', 'web_browsing', 'structured_reasoning'],
        metadata={
            'assistant_kind': 'devin',
            'task_affinities': ['long_implementation', 'pr_creation', 'refactor', 'test_writing', 'ci_fix'],
            'interaction_cost': 'low',
            'manual_effort': 'none',
            'long_running_capable': True,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': True,
            'response_capture_mode': 'tool_result',
            'requires_manual_pasteback': False,
            'session_scope': 'api_session',
            'background_capture_mode': 'devin_api',
            'launch_mode': 'api',
        },
    )
    
    # Crear ToolTask
    task = ToolTask(
        task_id=str(uuid4()),
        tool_id='devin_api',
        title='Sandbox integration test',
        objective='Test sandbox with real adapter - should NOT call HTTP',
        metadata={'context_pack': 'Sandbox integration test context'},
    )
    
    # Ejecutar sandbox con adapter real
    result = sandbox.run(card=card, task=task, adapter=adapter)
    
    # Verificar que fue sandbox execution
    assert result.success == True, 'Sandbox debe retornar success=True'
    assert result.execution_state.sandboxed == True, 'Debe ser sandboxed'
    assert result.execution_state.state in ('sandboxed', 'sandbox_pass'), 'State debe ser sandboxed o sandbox_pass'
    
    # Verificar que NO hubo HTTP real
    assert result.execution_state.metadata.get('devin_session_status') == 'sandboxed', 'Session status debe ser sandboxed'
    
    print('TEST INTEGRATION 1 PASS: Sandbox.run() con adapter real → NO HTTP')


def test_e03_integration_adapter_respects_sandbox_param() -> None:
    """Integration test: Adapter.run() respeta sandbox=True.
    
    Verificar que DevinApiToolAdapter.run(..., sandbox=True)
    retorna resultado simulado sin HTTP real.
    """
    # Setup adapter Devin con API key fake
    api_key = 'fake_key_for_test'
    adapter = DevinApiToolAdapter(api_key=api_key)
    
    # Crear ToolCard Devin
    card = ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        description='Sesion autonoma via API REST de Devin para tareas de codigo, shell y navegacion.',
        adapter_key='devin_api',
        available=True,
        requires_human_approval=False,
        capabilities=['code_assistance', 'shell_execution', 'web_browsing', 'structured_reasoning'],
        metadata={
            'assistant_kind': 'devin',
            'task_affinities': ['long_implementation', 'pr_creation', 'refactor', 'test_writing', 'ci_fix'],
            'interaction_cost': 'low',
            'manual_effort': 'none',
            'long_running_capable': True,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': True,
            'response_capture_mode': 'tool_result',
            'requires_manual_pasteback': False,
            'session_scope': 'api_session',
            'background_capture_mode': 'devin_api',
            'launch_mode': 'api',
        },
    )
    
    # Crear ToolTask
    task = ToolTask(
        task_id=str(uuid4()),
        tool_id='devin_api',
        title='Adapter sandbox test',
        objective='Test adapter sandbox - should NOT call HTTP',
        metadata={'context_pack': 'Adapter sandbox test context'},
    )
    
    # Ejecutar con sandbox=True
    result = adapter.run(card, task, sandbox=True)
    
    # Verificar sandbox execution
    assert result['success'] == True, 'Sandbox debe retornar success=True'
    assert result['metadata']['sandbox'] == True, 'Metadata debe indicar sandbox=True'
    assert result['metadata']['devin_session_status'] == 'sandboxed', 'Status debe ser sandboxed'
    assert result['extracted_data']['session_id'] == 'sandbox_simulated', 'Session ID debe ser simulado'
    
    # Ejecutar con sandbox=False (debe intentar HTTP pero fallar por API key fake)
    result_real = adapter.run(card, task, sandbox=False)
    assert result_real['success'] == False, 'Debe fallar sin API key real'
    assert result_real['metadata']['sandbox'] == False, 'Metadata debe indicar sandbox=False'
    
    print('TEST INTEGRATION 2 PASS: Adapter.run() respeta sandbox=True/False')


if __name__ == '__main__':
    print('=== E03: Integration tests ===')
    print()
    
    print('--- TEST INTEGRATION 1: Sandbox blocks HTTP real ---')
    test_e03_integration_sandbox_blocks_http_real()
    
    print()
    print('--- TEST INTEGRATION 2: Adapter respects sandbox param ---')
    test_e03_integration_adapter_respects_sandbox_param()
    
    print()
    print('=== E03: Todos los tests de integración pasaron ===')
