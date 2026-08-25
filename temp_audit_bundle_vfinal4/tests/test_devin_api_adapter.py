"""Tests for DevinApiToolAdapter and its integration with ToolTeachService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card() -> ToolCard:
    return ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='devin_api',
        metadata={'assistant_kind': 'devin'},
    )


def _make_task(objective: str = 'Fix bug #42', context_pack: str = '') -> ToolTask:
    metadata: dict = {}
    if context_pack:
        metadata['context_pack'] = context_pack
    return ToolTask(
        tool_id='devin_api',
        title='Test task',
        objective=objective,
        actions=[],
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestDevinApiAdapterIsAvailable:
    def test_unavailable_without_credentials(self) -> None:
        adapter = DevinApiToolAdapter(api_key='', org_id='')
        assert adapter.is_available(_make_card()) is False

    def test_unavailable_without_api_key(self) -> None:
        adapter = DevinApiToolAdapter(api_key='', org_id='org-123')
        assert adapter.is_available(_make_card()) is False

    def test_available_without_org_id(self) -> None:
        # v1 API no usa org_id; Bearer identifica la org.
        adapter = DevinApiToolAdapter(api_key='cog_xxx', org_id='')
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.get.return_value = mock_response
            assert adapter.is_available(_make_card()) is True

    def test_available_with_credentials_and_successful_api(self) -> None:
        adapter = DevinApiToolAdapter(api_key='cog_xxx', org_id='org-123')
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.get.return_value = mock_response
            assert adapter.is_available(_make_card()) is True
            mock_httpx.get.assert_called_once()
            call_args = mock_httpx.get.call_args
            # v1 endpoint real: /v1/sessions (Bearer token identifica la org).
            assert call_args[0][0] == 'https://api.devin.ai/v1/sessions'

    def test_unavailable_when_api_returns_error(self) -> None:
        adapter = DevinApiToolAdapter(api_key='cog_xxx', org_id='org-123')
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.get.return_value = mock_response
            assert adapter.is_available(_make_card()) is False

    def test_unavailable_when_api_raises(self) -> None:
        adapter = DevinApiToolAdapter(api_key='cog_xxx', org_id='org-123')
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.get.side_effect = ConnectionError('timeout')
            assert adapter.is_available(_make_card()) is False


# ---------------------------------------------------------------------------
# run — session lifecycle
# ---------------------------------------------------------------------------

class TestDevinApiAdapterRun:
    def test_run_returns_error_without_credentials(self) -> None:
        adapter = DevinApiToolAdapter(api_key='', org_id='')
        result = adapter.run(_make_card(), _make_task())
        assert result['success'] is False
        assert 'no configurado' in result['error_message']

    def test_run_creates_session_and_polls(self) -> None:
        adapter = DevinApiToolAdapter(
            api_key='cog_xxx',
            org_id='org-123',
            timeout_seconds=10,
            poll_interval_seconds=0.01,
        )
        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {
            'session_id': 'sess-abc',
            'status': 'running',
        }
        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            'status': 'finished',
            'structured_output': 'Bug fixed successfully.',
        }
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.post.return_value = create_response
            mock_httpx.get.return_value = poll_response
            result = adapter.run(_make_card(), _make_task())

        assert result['success'] is True
        assert result['output_text'] == 'Bug fixed successfully.'
        assert result['extracted_data']['session_id'] == 'sess-abc'
        assert result['extracted_data']['session_url'] == 'https://app.devin.ai/sessions/sess-abc'
        assert result['metadata']['devin_session_status'] == 'finished'

        mock_httpx.post.assert_called_once()
        post_call = mock_httpx.post.call_args
        assert post_call[0][0] == 'https://api.devin.ai/v1/sessions'
        body = post_call[1]['json']
        assert 'Fix bug #42' in body['prompt']

        # poll usa /v1/session/{id} (singular, sin 's').
        get_call = mock_httpx.get.call_args
        assert get_call[0][0] == 'https://api.devin.ai/v1/session/sess-abc'

    def test_run_appends_context_pack_to_prompt(self) -> None:
        adapter = DevinApiToolAdapter(
            api_key='cog_xxx',
            org_id='org-123',
            timeout_seconds=10,
            poll_interval_seconds=0.01,
        )
        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {'session_id': 'sess-1', 'status': 'finished'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.post.return_value = create_response
            adapter.run(_make_card(), _make_task(context_pack='repo: jhonf463r/Python'))

        body = mock_httpx.post.call_args[1]['json']
        assert '--- context ---' in body['prompt']
        assert 'jhonf463r/Python' in body['prompt']

    def test_run_handles_create_failure(self) -> None:
        adapter = DevinApiToolAdapter(
            api_key='cog_xxx',
            org_id='org-123',
            timeout_seconds=5,
            poll_interval_seconds=0.01,
        )
        create_response = MagicMock()
        create_response.status_code = 500
        create_response.text = 'Internal Server Error'
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.post.return_value = create_response
            result = adapter.run(_make_card(), _make_task())

        assert result['success'] is False
        assert 'HTTP 500' in result['error_message']

    def test_run_handles_exception(self) -> None:
        adapter = DevinApiToolAdapter(
            api_key='cog_xxx',
            org_id='org-123',
            timeout_seconds=5,
            poll_interval_seconds=0.01,
        )
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as mock_httpx:
            mock_httpx.post.side_effect = ConnectionError('network down')
            result = adapter.run(_make_card(), _make_task())

        assert result['success'] is False
        assert 'ConnectionError' in result['error_message']


# ---------------------------------------------------------------------------
# ToolTeachService integration
# ---------------------------------------------------------------------------

class TestToolTeachServiceDevinIntegration:
    def test_assistant_family_for_devin_api(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService

        svc = ToolTeachService.__new__(ToolTeachService)
        assert svc._assistant_family_for_tool_id('devin_api') == 'devin'

    def test_assistant_family_for_devin_variant(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService

        svc = ToolTeachService.__new__(ToolTeachService)
        assert svc._assistant_family_for_tool_id('devin_web_v2') == 'devin'

    def test_external_tool_ids_includes_devin_for_devin_preference(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService

        svc = ToolTeachService.__new__(ToolTeachService)
        ids = svc._external_tool_ids(assistant_preference='devin')
        assert ids == ['devin_api']

    def test_external_tool_ids_default_includes_devin(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService

        svc = ToolTeachService.__new__(ToolTeachService)
        ids = svc._external_tool_ids(assistant_preference='')
        assert 'devin_api' in ids

    def test_preferred_external_tool_id_for_devin(self) -> None:
        from iabv_v15.services.tools.tool_teach_service import ToolTeachService

        svc = ToolTeachService.__new__(ToolTeachService)
        tool_id = svc._preferred_external_tool_id(
            assistant_preference='devin',
            diagnostic_category='',
            incident_kind='',
            lab_recommendation=None,
            allow_local_automatic_consultation=False,
            explicit_external_consultation=False,
        )
        assert tool_id == 'devin_api'
