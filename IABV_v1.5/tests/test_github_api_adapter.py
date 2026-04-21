"""Tests para GitHubApiToolAdapter (sin red real; httpx mockeado)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.domain.models import ToolCard, ToolTask, ToolType
from iabv_v15.services.tools.tool_adapters import GitHubApiToolAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _card() -> ToolCard:
    return ToolCard(
        tool_id='github_api',
        title='GitHub API',
        tool_type=ToolType.MCP_CLIENT,
        adapter_key='github_api',
        metadata={'provider': 'github'},
    )


def _task(action: str = '', params: dict | None = None) -> ToolTask:
    metadata: dict = {}
    if action:
        metadata['github_action'] = action
    if params is not None:
        metadata['github_params'] = params
    return ToolTask(
        tool_id='github_api',
        title='gh op',
        objective='',
        actions=[],
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_without_token_returns_false(self) -> None:
        adapter = GitHubApiToolAdapter(token='', repo='jhonf463r/Python')
        assert adapter.is_available(_card()) is False

    def test_without_repo_returns_false(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='')
        assert adapter.is_available(_card()) is False

    def test_200_means_available(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=200)
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = resp
            assert adapter.is_available(_card()) is True
            url = httpx_mock.get.call_args[0][0]
            assert url == 'https://api.github.com/repos/jhonf463r/Python'
            headers = httpx_mock.get.call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer tok'
            assert headers['X-GitHub-Api-Version'] == '2022-11-28'

    def test_404_means_unavailable_even_with_token(self) -> None:
        # Fine-grained PAT sin scope devuelve 404 (no 401).
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=404)
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = resp
            assert adapter.is_available(_card()) is False

    def test_http_error_returns_false(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.side_effect = ConnectionError('boom')
            assert adapter.is_available(_card()) is False


# ---------------------------------------------------------------------------
# run — error paths
# ---------------------------------------------------------------------------


class TestRunGuardRails:
    def test_missing_token_error(self) -> None:
        adapter = GitHubApiToolAdapter(token='', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('read_pr', {'pull_number': 1}))
        assert out['success'] is False
        assert 'no configurados' in out['error_message']

    def test_unsupported_action(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('delete_repo'))
        assert out['success'] is False
        assert 'no soportado' in out['error_message']

    def test_read_pr_requires_pull_number(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('read_pr'))
        assert out['success'] is False
        assert 'pull_number' in out['error_message']

    def test_create_pr_requires_fields(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('create_pr', {'title': 'x'}))
        assert out['success'] is False
        assert 'create_pr falta' in out['error_message']

    def test_comment_issue_requires_body(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('comment_issue', {'issue_number': 1}))
        assert out['success'] is False
        assert 'comment_issue requiere' in out['error_message']


# ---------------------------------------------------------------------------
# run — sandbox (dry-run sin red)
# ---------------------------------------------------------------------------


class TestSandboxPlans:
    def test_sandbox_read_pr_returns_plan_and_doesnt_call_http(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            out = adapter.run(_card(), _task('read_pr', {'pull_number': 42}), sandbox=True)
            httpx_mock.get.assert_not_called()
            httpx_mock.post.assert_not_called()
            httpx_mock.put.assert_not_called()
        assert out['success'] is True
        plan = out['extracted_data']['plan']
        assert plan['method'] == 'GET'
        assert plan['url'] == 'https://api.github.com/repos/jhonf463r/Python/pulls/42'
        assert out['metadata']['sandbox'] is True

    def test_sandbox_create_pr_plan_carries_payload(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        params = {'title': 't', 'body': 'b', 'head': 'feat', 'base': 'main'}
        out = adapter.run(_card(), _task('create_pr', params), sandbox=True)
        plan = out['extracted_data']['plan']
        assert plan['method'] == 'POST'
        assert plan['url'].endswith('/pulls')
        assert plan['payload'] == params

    def test_sandbox_merge_defaults_to_squash(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(_card(), _task('merge_pr', {'pull_number': 1}), sandbox=True)
        plan = out['extracted_data']['plan']
        assert plan['method'] == 'PUT'
        assert plan['payload']['merge_method'] == 'squash'

    def test_sandbox_auto_merge_plan(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        out = adapter.run(
            _card(), _task('enable_auto_merge', {'pull_number': 92}), sandbox=True,
        )
        plan = out['extracted_data']['plan']
        assert plan['url'] == 'https://api.github.com/graphql'
        assert plan['payload']['merge_method'] == 'SQUASH'


# ---------------------------------------------------------------------------
# run — live paths (httpx mockeado)
# ---------------------------------------------------------------------------


class TestCreatePr:
    def test_success(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=201)
        resp.json.return_value = {'html_url': 'https://github.com/jhonf463r/Python/pull/99'}
        params = {'title': 't', 'head': 'h', 'base': 'main'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.post.return_value = resp
            out = adapter.run(_card(), _task('create_pr', params))
        assert out['success'] is True
        assert out['output_text'] == 'https://github.com/jhonf463r/Python/pull/99'

    def test_http_failure_surfaces(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=422)
        resp.text = 'Validation Failed'
        resp.json.return_value = {}
        params = {'title': 't', 'head': 'h', 'base': 'main'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.post.return_value = resp
            out = adapter.run(_card(), _task('create_pr', params))
        assert out['success'] is False
        assert '422' in out['error_message']
        assert out['metadata']['github_http_status'] == 422


class TestMergePr:
    def test_success_true_only_when_merged_is_true(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=200)
        resp.json.return_value = {'merged': True, 'sha': 'abc'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.put.return_value = resp
            out = adapter.run(_card(), _task('merge_pr', {'pull_number': 5}))
        assert out['success'] is True
        assert out['output_text'] == 'abc'

    def test_http_200_but_not_merged_is_failure(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=200)
        resp.json.return_value = {'merged': False}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.put.return_value = resp
            out = adapter.run(_card(), _task('merge_pr', {'pull_number': 5}))
        assert out['success'] is False


class TestEnableAutoMerge:
    def test_happy_path_does_lookup_then_graphql(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        pr_resp = MagicMock(status_code=200)
        pr_resp.json.return_value = {'node_id': 'PR_kwDO'}
        gql_resp = MagicMock(status_code=200)
        gql_resp.json.return_value = {
            'data': {
                'enablePullRequestAutoMerge': {
                    'pullRequest': {'number': 7, 'autoMergeRequest': {'enabledAt': 'x', 'mergeMethod': 'SQUASH'}},
                },
            },
        }
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = pr_resp
            httpx_mock.post.return_value = gql_resp
            out = adapter.run(_card(), _task('enable_auto_merge', {'pull_number': 7}))
        assert out['success'] is True
        gql_call = httpx_mock.post.call_args
        assert gql_call[0][0] == 'https://api.github.com/graphql'
        variables = gql_call[1]['json']['variables']
        assert variables == {'id': 'PR_kwDO', 'm': 'SQUASH'}

    def test_graphql_errors_surface_as_failure(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        pr_resp = MagicMock(status_code=200)
        pr_resp.json.return_value = {'node_id': 'PR_x'}
        gql_resp = MagicMock(status_code=200)
        gql_resp.json.return_value = {'errors': [{'message': 'Pull request is in clean status'}]}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = pr_resp
            httpx_mock.post.return_value = gql_resp
            out = adapter.run(_card(), _task('enable_auto_merge', {'pull_number': 7}))
        assert out['success'] is False
        assert 'GraphQL errors' in out['error_message']


class TestReadPr:
    def test_success(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=200)
        resp.json.return_value = {'title': 'Fix bug', 'state': 'open'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = resp
            out = adapter.run(_card(), _task('read_pr', {'pull_number': 92}))
        assert out['success'] is True
        assert out['output_text'] == 'Fix bug'
        assert out['extracted_data']['state'] == 'open'


class TestCommentIssue:
    def test_success(self) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=201)
        resp.json.return_value = {'html_url': 'https://github.com/jhonf463r/Python/issues/3#c'}
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.post.return_value = resp
            out = adapter.run(
                _card(), _task('comment_issue', {'issue_number': 3, 'body': 'hi'}),
            )
        assert out['success'] is True
        assert 'issues/3#c' in out['output_text']


class TestListCollections:
    @pytest.mark.parametrize('action,suffix', [('list_issues', 'issues'), ('list_prs', 'pulls')])
    def test_state_default_open_and_count(self, action: str, suffix: str) -> None:
        adapter = GitHubApiToolAdapter(token='tok', repo='jhonf463r/Python')
        resp = MagicMock(status_code=200)
        resp.json.return_value = [{'number': 1}, {'number': 2}, {'number': 3}]
        with patch('iabv_v15.services.tools.tool_adapters.httpx') as httpx_mock:
            httpx_mock.get.return_value = resp
            out = adapter.run(_card(), _task(action))
        assert out['success'] is True
        assert out['extracted_data']['count'] == 3
        url = httpx_mock.get.call_args[0][0]
        assert url.endswith(f'/{suffix}')
        assert httpx_mock.get.call_args[1]['params']['state'] == 'open'
