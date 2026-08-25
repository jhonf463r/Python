from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import ToolAction, ToolActionType, ToolCard, ToolTask, ToolType
from iabv_v15.services.capture.browser_session_controller import BrowserSessionController, sync_playwright
from iabv_v15.services.tools.tool_adapters import PlaywrightToolAdapter


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_playwright_tool_adapter_supports_local_file_harness() -> None:
    if sync_playwright is None:
        pytest.skip('Playwright no esta instalado en este entorno.')
    root = _workspace('tool_playwright_local_harness')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        html_path = root / 'index.html'
        screenshot_path = root / 'capture.png'
        html_path.write_text(
            '<html><body><h1 id="message">hola local-first</h1></body></html>',
            encoding='utf-8',
        )
        task = ToolTask(
            tool_id='playwright_browser',
            title='Harness local playwright',
            objective='Abrir una pagina local y extraer texto.',
            actions=[
                ToolAction(action_type=ToolActionType.OPEN_URL, label='Abrir harness', target=html_path.as_uri()),
                ToolAction(action_type=ToolActionType.EXTRACT_TEXT, label='message', target='#message'),
                ToolAction(action_type=ToolActionType.SCREENSHOT, label='Captura', parameters={'path': str(screenshot_path)}),
            ],
            execution_scope='read_only',
        )
        card = ToolCard(
            tool_id='playwright_browser',
            title='Playwright browser',
            tool_type=ToolType.BROWSER,
            description='Harness local de Playwright.',
            adapter_key='playwright',
            available=True,
            supports_sandbox=True,
            supports_write=True,
            supports_rollback=True,
        )
        adapter = PlaywrightToolAdapter(BrowserSessionController(headless=True))
        payload = adapter.run(card, task, sandbox=True)
        if not payload.get('success'):
            error = str(payload.get('error_message') or '')
            if 'Playwright is not installed' in error or 'Executable doesn' in error or 'browserType.launch' in error or '[WinError 5]' in error or 'Acceso denegado' in error:
                pytest.skip(error)
        assert payload['success'] is True
        assert payload['extracted_data']['message'] == 'hola local-first'
        assert screenshot_path.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)

