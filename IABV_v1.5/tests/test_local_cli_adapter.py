from __future__ import annotations

import stat
import sys
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolTask,
    ToolType,
)
from iabv_v15.services.tools.tool_adapters import LocalCliToolAdapter


def _card(**overrides: object) -> ToolCard:
    base = dict(
        tool_id='git_cli',
        title='Git CLI (test)',
        tool_type=ToolType.SHELL,
        adapter_key='local_cli',
        requires_human_approval=True,
        metadata={
            'command_name': 'git',
            'allowed_verbs': ['--version', 'status', 'log'],
            'version_command': '--version',
        },
    )
    base.update(overrides)
    return ToolCard(**base)


def _task(args: str = '') -> ToolTask:
    return ToolTask(
        task_id=str(uuid4()),
        tool_id='git_cli',
        title='probe',
        objective='probe',
        actions=[
            ToolAction(
                action_type=ToolActionType.RUN_COMMAND,
                label='run cli',
                value=args,
            )
        ],
    )


def test_existing_explicit_executable_path_is_not_trusted(tmp_path: Path) -> None:
    stub = tmp_path / 'git.exe'
    stub.write_text('wrapper that could start MCP or a tunnel', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        'allowed_verbs': ['--version'],
    })
    adapter = LocalCliToolAdapter()
    assert stub.exists()
    assert adapter.is_available(card) is False
    assert adapter._resolve_executable(card) == ''


def test_is_available_returns_false_when_binary_missing(monkeypatch) -> None:
    card = _card(metadata={
        'command_name': 'definitely-not-a-real-binary-abc-123',
        'allowed_verbs': ['--version'],
    })
    monkeypatch.setattr('shutil.which', lambda _name: None)
    adapter = LocalCliToolAdapter()
    assert adapter.is_available(card) is False


def test_run_fails_closed_before_resolution_or_subprocess(monkeypatch) -> None:
    card = _card(metadata={
        'command_name': 'definitely-not-a-real-binary-xyz-987',
        'allowed_verbs': ['--version'],
    })
    monkeypatch.setattr('shutil.which', lambda _name: None)
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('--version'))
    assert result['success'] is False
    assert result['error_message'] == 'local_cli_executable_identity_unverified'
    assert result['metadata']['executable'] == ''


def test_run_does_not_trust_allowed_verbs_without_executable_identity(tmp_path: Path) -> None:
    stub = tmp_path / 'git.exe'
    stub.write_text('wrapper', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        'allowed_verbs': ['--version', 'status', 'log'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('push origin main'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert result['error_message'] == 'local_cli_executable_identity_unverified'


def test_run_blocks_before_argument_allowlist_or_subprocess(tmp_path: Path) -> None:
    stub = tmp_path / 'git.exe'
    stub.write_text('wrapper', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        # Even an allowed or destructive verb cannot reach an unverified file.
        'allowed_verbs': ['--version', 'reset'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('reset --hard HEAD~1'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert result['error_message'] == 'local_cli_executable_identity_unverified'


def test_run_blocks_whitelisted_verb_even_when_file_exists(monkeypatch, tmp_path: Path) -> None:
    from iabv_v15.services.tools.tool_adapters import subprocess

    stub = tmp_path / 'probe_cli.exe'
    stub.write_text('wrapper', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['--version'],
        'version_command': '--version',
    })
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('--version'))
    assert result['success'] is False
    assert result['error_message'] == 'local_cli_executable_identity_unverified'
    assert calls == []


def test_run_blocks_default_version_probe_for_unverified_executable(tmp_path: Path) -> None:
    stub = tmp_path / 'probe_cli.exe'
    stub.write_text('wrapper', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['--version'],
        'version_command': '--version',
    })
    adapter = LocalCliToolAdapter()
    task = ToolTask(
        task_id=str(uuid4()),
        tool_id='git_cli',
        title='probe',
        objective='probe',
        actions=[],
    )
    result = adapter.run(card, task)
    assert result['success'] is False
    assert result['error_message'] == 'local_cli_executable_identity_unverified'


def test_windows_default_paths_and_path_lookup_are_not_identity_proofs(tmp_path: Path, monkeypatch) -> None:
    user_profile = tmp_path / 'userprofile'
    iabv_gh = user_profile / '.iabv' / 'tools' / 'gh' / 'bin'
    iabv_gh.mkdir(parents=True)
    exe = iabv_gh / 'gh.exe'
    exe.write_text('stub', encoding='utf-8')
    monkeypatch.setenv('USERPROFILE', str(user_profile))
    monkeypatch.setenv('PATH', str(iabv_gh))
    monkeypatch.setattr('shutil.which', lambda _name: str(exe))

    candidate = r'{userprofile}\.iabv\tools\gh\bin\gh.exe' if sys.platform == 'win32' else r'{userprofile}/.iabv/tools/gh/bin/gh'
    card = _card(metadata={
        'command_name': 'gh-never-exists-in-path',
        'windows_default_paths': [candidate],
        'allowed_verbs': ['--version'],
    })
    adapter = LocalCliToolAdapter()
    resolved = adapter._resolve_executable(card)
    assert resolved == ''
    assert adapter.is_available(card) is False


def test_quoted_read_only_args_do_not_bypass_unverified_executable_block(monkeypatch, tmp_path: Path) -> None:
    from iabv_v15.services.tools.tool_adapters import subprocess

    stub = tmp_path / 'git.exe'
    stub.write_text('wrapper', encoding='utf-8')
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['log'],
    })
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('log --format="%H %s"'))
    assert result['success'] is False
    assert result['error_message'] == 'local_cli_executable_identity_unverified'
    assert calls == []


def test_run_blocks_malformed_args_before_any_executable_resolution(tmp_path: Path) -> None:
    stub = tmp_path / 'probe_cli'
    stub.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['log'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('log --format="unterminated'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert result['error_message'] == 'local_cli_executable_identity_unverified'


def test_cloudflared_card_does_not_whitelist_update_verb(tmp_path: Path) -> None:
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.services.tools.tool_registry import ToolRegistry

    db = AppDatabase(str(tmp_path / 'app.sqlite'))
    storage = ArtifactStorage(str(tmp_path / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    registry = ToolRegistry(repository, {'local_cli': LocalCliToolAdapter()})
    registry._seed_defaults()

    cards_by_id = {c.tool_id: c for c in repository.list_cards()}
    card = cards_by_id['cloudflared_cli']
    allowed = [v.lower() for v in card.metadata.get('allowed_verbs') or []]
    assert 'update' not in allowed, (
        "'update' muta el binario en disco; debe quedar fuera del allowlist "
        "read-only; la familia Local CLI completa permanece fail-closed "
        "hasta que exista verificacion de identidad e integridad."
    )


def test_cloudflared_existing_wrapper_is_blocked_even_for_version_before_subprocess(monkeypatch, tmp_path: Path) -> None:
    from iabv_v15.services.tools.tool_adapters import subprocess

    wrapper = tmp_path / 'cloudflared.exe'
    wrapper.write_text('wrapper that could launch a tunnel', encoding='utf-8')
    assert wrapper.exists()
    card = _card(
        tool_id='cloudflared_cli',
        metadata={
            'tool_family': 'cloudflared',
            'command_name': 'cloudflared',
            'command_aliases': ['cloudflared.exe'],
            'executable_path': str(wrapper),
            'allowed_verbs': ['--version', 'version', 'tunnel', 'access', 'help'],
        },
    )
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    adapter = LocalCliToolAdapter()

    for command in (
        '--version',
        'help',
        'tunnel list',
        'tunnel info named-tunnel',
        'tunnel run',
        'TUNNEL --url http://127.0.0.1:8000',
        'tunnel   run extra',
        'service install',
        'service install --no-autoupdate',
        'access tcp --hostname example.com --url localhost:22',
    ):
        result = adapter.run(card, _task(command))
        assert result['success'] is False, command
        assert result['metadata']['blocked'] is True, command

    assert calls == []


def test_other_cli_correct_name_and_path_environment_do_not_prove_identity(monkeypatch, tmp_path: Path) -> None:
    from iabv_v15.services.tools.tool_adapters import subprocess

    wrapper = tmp_path / 'git.exe'
    wrapper.write_text('wrapper that could launch MCP or a tunnel', encoding='utf-8')
    assert wrapper.exists()
    monkeypatch.setenv('PATH', str(tmp_path))
    monkeypatch.setattr('shutil.which', lambda _name: str(wrapper))
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    card = _card(metadata={
        'command_name': 'git.exe',
        'command_aliases': ['git'],
        'executable_path': str(wrapper),
        'allowed_verbs': ['status'],
    })
    adapter = LocalCliToolAdapter()

    result = adapter.run(card, _task('status'))

    assert result['success'] is False
    assert result['error_message'] == 'local_cli_executable_identity_unverified'
    assert adapter.is_available(card) is False
    assert adapter._resolve_executable(card) == ''
    assert calls == []


def test_local_cli_blocks_direct_mcp_and_hot_reload_launches_before_subprocess(monkeypatch) -> None:
    from iabv_v15.services.tools.tool_adapters import subprocess

    card = _card(metadata={
        'command_name': 'python.exe',
        'allowed_verbs': ['-m', 'scripts'],
    })
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    adapter = LocalCliToolAdapter()

    for command in (
        '-m iabv_v15.infra.mcp.server',
        'scripts/mcp_hot_reload.py',
        'python -m iabv_v15.infra.mcp.server',
        r'C:\\repo\\scripts\\mcp_hot_reload.py',
    ):
        result = adapter.run(card, _task(command))
        assert result['success'] is False, command
        assert result['metadata']['blocked'] is True, command

    assert calls == []


def test_shell_adapter_direct_calls_are_fail_closed(monkeypatch) -> None:
    from iabv_v15.services.tools.tool_adapters import ShellToolAdapter, subprocess

    card = _card(tool_id='shell_command', adapter_key='shell')
    calls: list[object] = []
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))

    result = ShellToolAdapter().run(card, _task('cloudflared tunnel run'))

    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert calls == []


def test_seed_defaults_registers_four_local_cli_cards(tmp_path: Path) -> None:
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
    from iabv_v15.services.tools.tool_registry import ToolRegistry

    db = AppDatabase(str(tmp_path / 'app.sqlite'))
    storage = ArtifactStorage(str(tmp_path / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    adapters = {'local_cli': LocalCliToolAdapter()}
    registry = ToolRegistry(repository, adapters)
    registry._seed_defaults()

    cards_by_id = {card.tool_id: card for card in repository.list_cards()}
    for expected in ('gh_cli', 'cloudflared_cli', 'git_cli', 'winget_cli'):
        assert expected in cards_by_id, f'missing seeded card: {expected}'
        card = cards_by_id[expected]
        assert card.adapter_key == 'local_cli'
        assert card.requires_human_approval is True
        assert card.supports_write is False
        assert card.metadata.get('version_command') == '--version'
        allowed = card.metadata.get('allowed_verbs') or []
        assert '--version' in allowed
        assert adapters['local_cli'].is_available(card) is False
