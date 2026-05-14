from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class _FakeMcp:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )


def _register_tools(repo: Path) -> dict[str, Any]:
    from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools

    mcp = _FakeMcp()
    register_self_update_tools(
        mcp,
        workspace_root_fn=lambda: repo,
        governance_fn=lambda **kwargs: None,
        to_jsonable_fn=lambda value: value,
    )
    return mcp.tools


def test_git_commit_and_push_default_scope_never_stages_data(tmp_path: Path) -> None:
    """Broad self-update commits must not run git add -A over runtime data."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init')
    _git(repo, 'config', 'user.email', 'iabv@example.test')
    _git(repo, 'config', 'user.name', 'IABV Test')
    (repo / 'src').mkdir()
    (repo / 'data').mkdir()
    (repo / 'src' / 'app.py').write_text('print("old")\n', encoding='utf-8')
    (repo / 'data' / 'runtime.jsonl').write_text('old\n', encoding='utf-8')
    _git(repo, 'add', '--', 'src/app.py', 'data/runtime.jsonl')
    _git(repo, 'commit', '-m', 'initial')

    (repo / 'src' / 'app.py').write_text('print("new")\n', encoding='utf-8')
    (repo / 'data' / 'runtime.jsonl').write_text('new\n', encoding='utf-8')

    tool = _register_tools(repo)['git_commit_and_push']
    result = tool(message='safe source commit', files='.', push=False)

    assert result['status'] == 'ok'
    assert result['git_add_scope'] == 'safe_source_auto_scope'
    assert result['files'] == ['src/app.py']
    show = _git(repo, 'show', '--name-only', '--format=').stdout.splitlines()
    assert 'src/app.py' in show
    assert 'data/runtime.jsonl' not in show
    assert ' M data/runtime.jsonl' in _git(repo, 'status', '--porcelain', '--', 'data/runtime.jsonl').stdout


def test_git_commit_and_push_rejects_explicit_data_path(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init')
    _git(repo, 'config', 'user.email', 'iabv@example.test')
    _git(repo, 'config', 'user.name', 'IABV Test')
    (repo / 'data').mkdir()
    (repo / 'data' / 'runtime.jsonl').write_text('new\n', encoding='utf-8')

    tool = _register_tools(repo)['git_commit_and_push']
    result = tool(message='bad broad commit', files='data/runtime.jsonl', push=False)

    assert result['status'] == 'error'
    assert 'unsafe_git_add_path:data/runtime.jsonl' in result['detail']
