from __future__ import annotations

import os
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


def test_is_available_uses_explicit_executable_path(tmp_path: Path) -> None:
    stub = tmp_path / 'git'
    stub.write_text('#!/bin/sh\necho 1.0\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        'allowed_verbs': ['--version'],
    })
    adapter = LocalCliToolAdapter()
    assert adapter.is_available(card) is True
    assert adapter._resolve_executable(card) == str(stub)


def test_is_available_returns_false_when_binary_missing(monkeypatch) -> None:
    card = _card(metadata={
        'command_name': 'definitely-not-a-real-binary-abc-123',
        'allowed_verbs': ['--version'],
    })
    monkeypatch.setattr('shutil.which', lambda _name: None)
    adapter = LocalCliToolAdapter()
    assert adapter.is_available(card) is False


def test_run_returns_failure_when_executable_missing(monkeypatch) -> None:
    card = _card(metadata={
        'command_name': 'definitely-not-a-real-binary-xyz-987',
        'allowed_verbs': ['--version'],
    })
    monkeypatch.setattr('shutil.which', lambda _name: None)
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('--version'))
    assert result['success'] is False
    assert result['error_message'] == 'executable_not_found'
    assert result['metadata']['executable'] == ''


def test_run_blocks_verb_outside_allowed_list(tmp_path: Path) -> None:
    stub = tmp_path / 'git'
    stub.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        'allowed_verbs': ['--version', 'status', 'log'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('push origin main'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert "'push'" in result['error_message']


def test_run_blocks_destructive_tokens_even_if_verb_is_allowed(tmp_path: Path) -> None:
    stub = tmp_path / 'git'
    stub.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'git',
        'executable_path': str(stub),
        # `reset` is deliberately added to the allowlist to prove that the
        # BLOCKED_TOKENS failsafe still fires regardless of allowed_verbs.
        'allowed_verbs': ['--version', 'reset'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('reset --hard HEAD~1'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert 'read-only' in result['error_message']


def test_run_executes_whitelisted_verb_and_captures_stdout(tmp_path: Path) -> None:
    stub = tmp_path / 'probe_cli'
    if sys.platform == 'win32':
        stub = tmp_path / 'probe_cli.bat'
        stub.write_text('@echo probe 1.0\r\n', encoding='utf-8')
    else:
        stub.write_text('#!/bin/sh\necho probe 1.0\n', encoding='utf-8')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['--version'],
        'version_command': '--version',
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('--version'))
    assert result['success'] is True, result
    assert 'probe 1.0' in result['output_text']
    assert result['extracted_data']['returncode'] == 0
    assert result['extracted_data']['args'] == '--version'
    assert result['metadata']['blocked'] is False


def test_run_defaults_to_version_command_when_task_has_no_args(tmp_path: Path) -> None:
    stub = tmp_path / 'probe_cli'
    stub.write_text('#!/bin/sh\necho default-version\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
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
    assert result['success'] is True
    assert result['extracted_data']['args'] == '--version'


def test_windows_default_paths_expand_userprofile_token(tmp_path: Path, monkeypatch) -> None:
    user_profile = tmp_path / 'userprofile'
    iabv_gh = user_profile / '.iabv' / 'tools' / 'gh' / 'bin'
    iabv_gh.mkdir(parents=True)
    exe = iabv_gh / ('gh.exe' if sys.platform == 'win32' else 'gh')
    exe.write_text('stub', encoding='utf-8')
    monkeypatch.setenv('USERPROFILE', str(user_profile))
    monkeypatch.setattr('shutil.which', lambda _name: None)

    candidate = r'{userprofile}\.iabv\tools\gh\bin\gh.exe' if sys.platform == 'win32' else r'{userprofile}/.iabv/tools/gh/bin/gh'
    card = _card(metadata={
        'command_name': 'gh-never-exists-in-path',
        'windows_default_paths': [candidate],
        'allowed_verbs': ['--version'],
    })
    adapter = LocalCliToolAdapter()
    resolved = adapter._resolve_executable(card)
    assert Path(resolved) == exe
    assert adapter.is_available(card) is True


def test_run_preserves_quoted_arguments_via_shlex(tmp_path: Path) -> None:
    # Captura los argv reales pasados al subprocess para verificar que un
    # arg con espacios entre comillas llega como un solo token y no se
    # parte en dos. Es la regresion que motivo el fix de shlex.split.
    capture = tmp_path / 'argv.txt'
    stub = tmp_path / 'probe_cli'
    stub.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "' + str(capture) + '"\n',
        encoding='utf-8',
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['log'],
    })
    adapter = LocalCliToolAdapter()
    result = adapter.run(card, _task('log --format="%H %s"'))
    assert result['success'] is True, result
    captured = capture.read_text(encoding='utf-8').splitlines()
    assert captured == ['log', '--format=%H %s']


def test_run_blocks_malformed_shlex_input(tmp_path: Path) -> None:
    stub = tmp_path / 'probe_cli'
    stub.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    card = _card(metadata={
        'command_name': 'probe_cli',
        'executable_path': str(stub),
        'allowed_verbs': ['log'],
    })
    adapter = LocalCliToolAdapter()
    # Comilla sin cerrar → shlex.split lanza ValueError → adapter bloquea.
    result = adapter.run(card, _task('log --format="unterminated'))
    assert result['success'] is False
    assert result['metadata']['blocked'] is True
    assert 'args malformados' in result['error_message']


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
        "read-only y solo pasar por ToolApprovalPolicy cuando haga falta."
    )


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
