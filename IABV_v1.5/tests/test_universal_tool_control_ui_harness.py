from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.domain.models import TaskRole, ToolAction, ToolActionType, ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter
from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner


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

    result = ExternalAssistantToolAdapter(
        runner_factory=lambda workspace_root: UIExecutionRunner(
            workspace_root,
            browser_launch_authorizer=lambda launch_args: launch_args == ['--no-sandbox'],
        )
    ).run(card, task, sandbox=False)

    assert result['success'] is True
    assert result['output_text'] == 'CONTROLLED_BROWSER_RESPONSE'
    metadata = result['metadata']['browser_dom_metadata']
    assert metadata['browser_launch_security_mode'] == 'explicit_no_sandbox_test'
    assert metadata['browser_launch_args'] == ['--no-sandbox']


def test_browser_dom_rejects_no_sandbox_without_injected_authorization(tmp_path) -> None:
    runner = UIExecutionRunner(str(tmp_path))

    result = runner._capture_browser_dom_response(
        launch_target='file:///controlled-fixture.html',
        prompt_text='irrelevant',
        response_wait_seconds=0.1,
        browser_profile_dir=str(tmp_path / 'profile'),
        browser_headless=True,
        browser_launch_args=['--no-sandbox'],
        input_selectors=[],
        response_selectors=[],
        submit_selectors=[],
    )

    assert result['launched'] is False
    assert result['error_message'] == 'browser_insecure_launch_unauthorized'
    assert result['metadata']['browser_launch_security_mode'] == 'insecure_launch_rejected'


@pytest.mark.parametrize('launch_arg', ['--no-sandbox=1', '--disable-setuid-sandbox'])
def test_browser_dom_rejects_obvious_insecure_flag_variants(tmp_path, launch_arg: str) -> None:
    result = UIExecutionRunner(str(tmp_path))._capture_browser_dom_response(
        launch_target='file:///controlled-fixture.html',
        prompt_text='irrelevant',
        response_wait_seconds=0.1,
        browser_profile_dir=str(tmp_path / 'profile'),
        browser_headless=True,
        browser_launch_args=[launch_arg],
        input_selectors=[],
        response_selectors=[],
        submit_selectors=[],
    )

    assert result['error_message'] == 'browser_insecure_launch_unauthorized'
    assert result['launched'] is False


def test_normal_browser_launch_args_do_not_require_authorization(tmp_path) -> None:
    pytest.importorskip('playwright.sync_api')
    fixture = tmp_path / 'normal_args_fixture.html'
    fixture.write_text(
        '''<!doctype html><textarea id="prompt"></textarea><button id="submit">Send</button><div id="response"></div>
        <script>document.querySelector('#submit').onclick = () => document.querySelector('#response').textContent = 'NORMAL_BROWSER_RESPONSE_CONFIRMED';</script>''',
        encoding='utf-8',
    )

    result = UIExecutionRunner(str(tmp_path))._capture_browser_dom_response(
        launch_target=fixture.as_uri(),
        prompt_text='normal args',
        response_wait_seconds=3.0,
        browser_profile_dir=str(tmp_path / 'profile'),
        browser_headless=True,
        browser_launch_args=['--window-size=1280,720'],
        input_selectors=['#prompt'],
        response_selectors=['#response'],
        submit_selectors=['#submit'],
    )

    assert result['response_captured'] is True, result['error_message']
    assert result['captured_text'] == 'NORMAL_BROWSER_RESPONSE_CONFIRMED'
    assert result['metadata']['browser_launch_security_mode'] == 'sandboxed_default'


def test_metadata_cannot_autoauthorize_insecure_browser_launch(tmp_path) -> None:
    card = ToolCard(
        tool_id='untrusted_browser_fixture',
        title='Untrusted browser fixture',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'controlled_fixture',
            'launch_mode': 'web_assisted',
            'response_capture_mode': 'browser_dom',
            'background_capture_mode': 'browser_dom',
            'browser_launch_args': ['--no-sandbox'],
            'allow_insecure_browser': True,
            'browser_launch_security_mode': 'explicit_no_sandbox_test',
            'web_url': 'file:///controlled-fixture.html',
            'workspace_root': str(tmp_path),
        },
    )
    task = ToolTask(
        tool_id=card.tool_id,
        title='Untrusted browser interaction',
        objective='Attempt metadata-only authorization.',
        requested_by_role=TaskRole.TOOL_USE,
        metadata={'workspace_root': str(tmp_path), 'allow_insecure_browser': True},
    )

    result = ExternalAssistantToolAdapter().run(card, task, sandbox=False)

    assert result['success'] is False
    assert result['error_message'] == 'browser_insecure_launch_unauthorized'
    assert result['metadata']['browser_dom_metadata']['browser_launch_security_mode'] == 'insecure_launch_rejected'
