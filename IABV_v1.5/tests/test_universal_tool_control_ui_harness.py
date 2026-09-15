from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.domain.models import TaskRole, ToolAction, ToolActionType, ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter


def test_external_assistant_browser_dom_harness_uses_explicit_test_launch_args(tmp_path) -> None:
    pytest.importorskip('playwright.sync_api')
    fixture = tmp_path / 'assistant_fixture.html'
    fixture.write_text(
        '''<!doctype html><html><body>
        <textarea id="prompt"></textarea><button id="submit">Send</button><div id="response"></div>
        <script>document.querySelector('#submit').onclick = () => {
          document.querySelector('#response').textContent = 'CONTROLLED_BROWSER_RESPONSE';
        };</script></body></html>''',
        encoding='utf-8',
    )
    card = ToolCard(
        tool_id='controlled_browser_fixture',
        title='Controlled browser fixture',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'controlled_fixture',
            'launch_mode': 'web_assisted',
            'response_capture_mode': 'browser_dom',
            'background_capture_mode': 'browser_dom',
            'background_headless': True,
            'browser_launch_args': ['--no-sandbox'],
            'input_selectors': ['#prompt'],
            'submit_selectors': ['#submit'],
            'response_selectors': ['#response'],
            'web_url': fixture.as_uri(),
            'workspace_root': str(tmp_path),
        },
    )
    task = ToolTask(
        tool_id=card.tool_id,
        title='Controlled browser interaction',
        objective='Send a controlled prompt to the local HTML fixture.',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Controlled prompt', value='hello fixture')],
        metadata={'workspace_root': str(tmp_path), 'response_wait_seconds': 3.0},
    )

    result = ExternalAssistantToolAdapter().run(card, task, sandbox=False)

    assert result['success'] is True
    assert result['output_text'] == 'CONTROLLED_BROWSER_RESPONSE'
    metadata = result['metadata']['browser_dom_metadata']
    assert metadata['browser_launch_security_mode'] == 'explicit_no_sandbox_test'
    assert metadata['browser_launch_args'] == ['--no-sandbox']
