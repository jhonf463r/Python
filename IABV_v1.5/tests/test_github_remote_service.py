"""Tests for ``GitHubRemoteService`` (sin red real; adapter y git mockeados).

Cubre:
- happy path ``iabv-auto/*``: policy auto-aprueba, push, create_pr, evidencia.
- ``devin/*``: policy exige humano, broker otorga -> continua.
- ``devin/*`` sin broker -> bloqueado sin abrir PR.
- approval rechazada -> bloqueado sin push.
- ``git push`` fallido -> no se llama al adapter.
- ``create_pr`` fallido -> result.success=False pero evidencia se guarda.
- diff demasiado grande en ``iabv-auto/*`` sin broker -> bloqueado.
- evidencia JSON se persiste en evidence_dir por cada intento.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
)
from iabv_v15.services.tools.github_remote_service import (
    GitHubRemoteService,
    PublishResult,
)
from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_git_runner(returncode: int = 0, stderr: str = '', stdout: str = ''):
    calls: list[tuple[list[str], Path]] = []

    def runner(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
        calls.append((list(argv), Path(cwd)))
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout=stdout, stderr=stderr,
        )

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def _adapter_success_response(
    *, number: int = 123, html_url: str = 'https://github.com/x/y/pull/123'
) -> dict[str, Any]:
    return {
        'success': True,
        'output_text': html_url,
        'extracted_data': {'number': number, 'html_url': html_url},
        'artifacts': [],
        'error_message': '',
        'execution_ms': 10,
        'metadata': {
            'sandbox': False,
            'tool_id': 'github_api',
            'github_action': 'create_pr',
            'github_http_status': 201,
        },
    }


def _adapter_failure_response(
    *, http_status: int = 422, error: str = 'HTTP 422: validation_failed'
) -> dict[str, Any]:
    return {
        'success': False,
        'output_text': '',
        'extracted_data': {},
        'artifacts': [],
        'error_message': error,
        'execution_ms': 10,
        'metadata': {
            'sandbox': False,
            'tool_id': 'github_api',
            'github_action': 'create_pr',
            'github_http_status': http_status,
        },
    }


def _make_service(
    tmp_path: Path,
    *,
    adapter_response: dict[str, Any] | None = None,
    git_returncode: int = 0,
    git_stderr: str = '',
    approval_broker: Any | None = None,
) -> tuple[GitHubRemoteService, MagicMock, Any]:
    adapter = MagicMock()
    adapter.run.return_value = adapter_response or _adapter_success_response()
    runner = _make_git_runner(returncode=git_returncode, stderr=git_stderr)
    
    # Mock CapabilityActionBridge for F15 authority integration
    mock_capability_bridge = MagicMock(spec=CapabilityActionBridge)
    mock_capability_bridge.authorize_action.return_value = MagicMock(success=True)
    
    service = GitHubRemoteService(
        repo_root=tmp_path,
        adapter=adapter,
        governance_policy=AutonomyGovernancePolicy(),
        approval_broker=approval_broker,
        evidence_dir=tmp_path / 'pr_history',
        git_runner=runner,
        clock=lambda: 1_700_000_000.0,
        capability_action_bridge=mock_capability_bridge,
    )
    return service, adapter, runner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_iabv_auto_small_diff_publishes_pr(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(tmp_path)

    result = service.publish_branch_as_pr(
        branch='iabv-auto/test-slice',
        title='Add slice',
        body='body',
        base='main',
        diff_lines=40,
    )

    assert result.success is True
    assert result.pr_number == 123
    assert result.pr_url.endswith('/pull/123')
    assert result.pushed is True
    assert result.blocked_by_policy is False
    assert result.required_approval is False
    assert result.evidence_path
    assert adapter.run.call_count == 1
    # git push fue llamado con la rama correcta
    pushed_argv, pushed_cwd = runner.calls[0]  # type: ignore[attr-defined]
    assert pushed_argv[:3] == ['git', 'push', '--set-upstream']
    assert pushed_argv[-2:] == ['origin', 'iabv-auto/test-slice']
    assert pushed_cwd == tmp_path
    # evidencia persistida
    snapshot = json.loads(Path(result.evidence_path).read_text(encoding='utf-8'))
    assert snapshot['branch'] == 'iabv-auto/test-slice'
    assert snapshot['policy']['auto_approved'] is True
    assert snapshot['push']['returncode'] == 0
    assert snapshot['api']['success'] is True
    assert snapshot['result']['pr_number'] == 123


def test_devin_branch_without_broker_blocked(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(tmp_path)

    result = service.publish_branch_as_pr(
        branch='devin/1776797946-feature',
        title='Add feature',
        base='main',
        diff_lines=50,
    )

    assert result.success is False
    assert result.required_approval is True
    assert result.blocked_by_policy is True
    assert result.approval_granted is False
    # no push, no api
    assert runner.calls == []  # type: ignore[attr-defined]
    assert adapter.run.called is False
    # evidencia existe y deja traza del bloqueo
    snapshot = json.loads(Path(result.evidence_path).read_text(encoding='utf-8'))
    assert snapshot['policy']['auto_approved'] is False


def test_devin_branch_with_broker_approval_proceeds(tmp_path: Path) -> None:
    broker = MagicMock()
    approval = MagicMock()
    approval.approved = True
    approval.rejected = False
    approval.timed_out = False
    approval.auto_resolved = False
    broker.request.return_value = approval

    service, adapter, runner = _make_service(tmp_path, approval_broker=broker)

    result = service.publish_branch_as_pr(
        branch='devin/1776797946-feature',
        title='Add feature',
        base='main',
        diff_lines=50,
        approval_context={'requested_by': 'ui'},
    )

    assert result.success is True
    assert result.required_approval is True
    assert result.approval_granted is True
    assert result.pushed is True
    broker.request.assert_called_once()
    kwargs = broker.request.call_args.kwargs
    assert kwargs['kind'] == 'external_call_authorization'
    assert kwargs['scope']['kind'] == 'open_pr'
    assert kwargs['scope']['branch'] == 'devin/1776797946-feature'
    assert kwargs['scope']['requested_by'] == 'ui'


def test_broker_rejects_approval_blocks(tmp_path: Path) -> None:
    broker = MagicMock()
    approval = MagicMock()
    approval.approved = False
    approval.rejected = True
    approval.timed_out = False
    approval.auto_resolved = False
    broker.request.return_value = approval

    service, adapter, runner = _make_service(tmp_path, approval_broker=broker)

    result = service.publish_branch_as_pr(
        branch='devin/1776797946-feature',
        title='Add feature',
        base='main',
        diff_lines=10,
    )

    assert result.success is False
    assert result.required_approval is True
    assert result.approval_granted is False
    assert result.blocked_by_policy is True
    # no push ni api
    assert runner.calls == []  # type: ignore[attr-defined]
    assert adapter.run.called is False


def test_git_push_failure_does_not_create_pr(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(
        tmp_path, git_returncode=128, git_stderr='remote: Permission denied',
    )

    result = service.publish_branch_as_pr(
        branch='iabv-auto/foo',
        title='T',
        base='main',
        diff_lines=10,
    )

    assert result.success is False
    assert result.pushed is False
    assert 'git push fallo' in result.error
    assert adapter.run.called is False
    # evidencia refleja el fallo de push
    snapshot = json.loads(Path(result.evidence_path).read_text(encoding='utf-8'))
    assert snapshot['push']['returncode'] == 128


def test_create_pr_api_failure_returns_failure_but_logs_evidence(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(
        tmp_path, adapter_response=_adapter_failure_response(),
    )

    result = service.publish_branch_as_pr(
        branch='iabv-auto/foo',
        title='T',
        base='main',
        diff_lines=10,
    )

    assert result.success is False
    assert result.pushed is True
    assert result.http_status == 422
    assert 'HTTP 422' in result.error
    snapshot = json.loads(Path(result.evidence_path).read_text(encoding='utf-8'))
    assert snapshot['api']['success'] is False
    assert snapshot['api']['http_status'] == 422


def test_missing_title_rejected_before_policy(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(tmp_path)

    result = service.publish_branch_as_pr(
        branch='iabv-auto/foo', title='   ', diff_lines=10,
    )

    assert result.success is False
    assert result.error == 'title vacio.'
    assert runner.calls == []  # type: ignore[attr-defined]
    assert adapter.run.called is False


def test_large_diff_on_iabv_auto_without_broker_blocked(tmp_path: Path) -> None:
    service, adapter, runner = _make_service(tmp_path)

    result = service.publish_branch_as_pr(
        branch='iabv-auto/big',
        title='Big change',
        base='main',
        diff_lines=500,
    )

    assert result.success is False
    assert result.blocked_by_policy is True
    assert result.required_approval is True
    # diff grande: la razon debe contener el numero
    assert '500' in result.error
