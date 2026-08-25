"""Tests de ``PromotionPrPublisher`` (F2.3 thin).

Cubre:
    * Genera markdown + rama + commit + publish cuando todo OK.
    * Respeta ``enabled=False`` y retorna ``skipped=True``.
    * Fallo de ``git checkout`` se captura y retorna ``error`` sin reventar.
    * ``subject_key`` vacio se rechaza temprano.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from iabv_v15.services.self_teach.promotion_pr_publisher import (
    PromotionPrPublisher,
    _slugify_subject,
)


class _FakeGitRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.failures: dict[tuple[str, ...], subprocess.CompletedProcess] = {}
        self.default_returncode = 0

    def __call__(self, argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
        self.calls.append(list(argv))
        key = tuple(argv[:3])
        if key in self.failures:
            return self.failures[key]
        return subprocess.CompletedProcess(
            args=argv, returncode=self.default_returncode, stdout='main\n', stderr=''
        )


class _FakeGithubRemoteService:
    def __init__(self, *, result: SimpleNamespace | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result or SimpleNamespace(
            success=True, branch='iabv-auto/promote-x-1',
            base='main', pr_number=999, pr_url='https://example/pr/999',
            blocked_by_policy=False, required_approval=False, error='',
        )

    def publish_branch_as_pr(self, **kwargs):
        self.calls.append(dict(kwargs))
        return self._result


def _build_publisher(tmp_path: Path, runner: _FakeGitRunner | None = None,
                     remote: _FakeGithubRemoteService | None = None,
                     enabled: bool = True,
                     clock: float = 1700000000.0) -> tuple[PromotionPrPublisher, _FakeGitRunner, _FakeGithubRemoteService]:
    repo = tmp_path / 'repo'
    repo.mkdir(parents=True, exist_ok=True)
    runner = runner or _FakeGitRunner()
    remote = remote or _FakeGithubRemoteService()
    pub = PromotionPrPublisher(
        repo_root=repo,
        github_remote_service=remote,
        output_dir=repo / 'data' / 'evolution' / 'promoted',
        git_runner=runner,
        clock=lambda: clock,
        enabled=enabled,
    )
    return pub, runner, remote


def test_publish_promotion_writes_markdown_branches_and_delegates(tmp_path: Path) -> None:
    pub, runner, remote = _build_publisher(tmp_path)

    result = pub.publish_promotion(
        subject_key='ollama:llama3',
        proposal_kind='assistant_route',
        current_route='fallback',
        current_assistant_kind='ollama-llama2',
        candidate_route='primary',
        candidate_assistant_kind='ollama-llama3',
        verdict='promote',
        summary='Llama3 gana en latencia',
        metrics={'score_margin': 0.18},
        evidence_refs=['run-1', 'run-2'],
        sandbox_experiment_id='exp-1',
        proposal_id='prop-1',
    )

    assert result.success is True
    assert result.branch.startswith('iabv-auto/promote-ollama-llama3-')
    md_path = Path(result.markdown_path)
    assert md_path.exists()
    content = md_path.read_text(encoding='utf-8')
    assert '# iabv-auto: promocion de ollama:llama3' in content
    assert 'proposal_kind: `assistant_route`' in content
    assert 'candidata' not in content  # sin typos heredados
    # checkout -B + add + commit + rev-parse + rev-parse HEAD (inicial)
    git_cmds = [tuple(call[:3]) for call in runner.calls]
    assert ('git', 'checkout', '-B') in git_cmds
    assert ('git', 'add', '--') in git_cmds
    assert ('git', 'commit', '-m') in git_cmds
    assert remote.calls, 'github_remote_service.publish_branch_as_pr deberia haber sido llamado'
    payload = remote.calls[0]
    assert payload['branch'] == result.branch
    assert payload['base'] == 'main'
    assert payload['title'].startswith('iabv-auto: promocion de ')
    assert payload['draft'] is False
    evidence_path = Path(result.evidence_path)
    assert evidence_path.exists()
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    assert evidence['subject_key'] == 'ollama:llama3'
    assert evidence['publish']['pr_number'] == 999


def test_publish_promotion_respects_enabled_false(tmp_path: Path) -> None:
    pub, runner, remote = _build_publisher(tmp_path, enabled=False)
    result = pub.publish_promotion(
        subject_key='x',
        proposal_kind='',
        current_route='a', current_assistant_kind='',
        candidate_route='b', candidate_assistant_kind='',
        verdict='promote', summary='', metrics={},
    )
    assert result.success is False
    assert result.skipped is True
    assert not remote.calls
    assert not runner.calls


def test_publish_promotion_rejects_empty_subject(tmp_path: Path) -> None:
    pub, runner, remote = _build_publisher(tmp_path)
    result = pub.publish_promotion(
        subject_key='   ',
        proposal_kind='',
        current_route='a', current_assistant_kind='',
        candidate_route='b', candidate_assistant_kind='',
        verdict='promote', summary='', metrics={},
    )
    assert result.success is False
    assert 'subject_key' in result.error
    assert not remote.calls


def test_publish_promotion_captures_git_failure(tmp_path: Path) -> None:
    runner = _FakeGitRunner()
    # Simular fallo de ``git checkout -B``.
    runner.failures[('git', 'checkout', '-B')] = subprocess.CompletedProcess(
        args=['git', 'checkout', '-B'], returncode=1, stdout='',
        stderr='fatal: something bad',
    )
    pub, runner, remote = _build_publisher(tmp_path, runner=runner)
    result = pub.publish_promotion(
        subject_key='ollama:llama3',
        proposal_kind='',
        current_route='a', current_assistant_kind='',
        candidate_route='b', candidate_assistant_kind='',
        verdict='promote', summary='', metrics={},
    )
    assert result.success is False
    assert 'git checkout' in result.error
    assert not remote.calls  # no se llamo al servicio porque git fallo
    # Pero si se escribio evidence con el error
    assert Path(result.evidence_path).exists()


def test_slugify_subject() -> None:
    assert _slugify_subject('ollama:llama3') == 'ollama-llama3'
    assert _slugify_subject('  Hola / Mundo  ') == 'hola-mundo'
    assert _slugify_subject('') == 'unknown'
    # Truncado a 48 chars.
    assert len(_slugify_subject('x' * 100)) == 48
