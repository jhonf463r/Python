from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import ToolAction, ToolActionType, ToolCard, ToolTask, ToolType
from iabv_v15.services.tools import ui_execution_runner as module
from iabv_v15.services.tools.ui_execution_runner import UIExecutionRunner


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_ui_execution_runner_returns_visual_evidence_in_sandbox_mode() -> None:
    root = _workspace('ui_execution_runner')
    try:
        runner = UIExecutionRunner(str(root))
        card = ToolCard(
            tool_id='desktop_human_runner',
            title='Desktop human runner',
            tool_type=ToolType.CUSTOM,
            adapter_key='desktop_human',
            metadata={'workspace_root': str(root)},
        )
        task = ToolTask(
            tool_id='desktop_human_runner',
            title='Click demo',
            objective='Probar click simulado sobre la interfaz.',
            actions=[
                ToolAction(
                    action_type=ToolActionType.CLICK_POINT,
                    label='Click demo',
                    parameters={'x': 120, 'y': 80},
                )
            ],
        )

        result = runner.run(card, task, sandbox=True)

        assert result['success'] is True
        assert result['metadata']['simulation_mode'] == 'simulated'
        assert result['metadata']['simulation_reason'] == 'sandbox_mode'
        assert result['extracted_data']['cross_check_summary']['frame_count'] == 1
        assert len(result['metadata']['visual_teaching_frames']) == 1
        assert result['metadata']['teaching_evidence']
        assert 'simulado' in result['output_text'].lower()
        assert result['metadata']['visual_teaching_frames'][0]['cross_check']['status'] in {'confirmed', 'doubtful', 'insufficient'}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_uses_shell_start_for_windows_alias(monkeypatch) -> None:
    root = _workspace('ui_execution_runner_windows_alias')
    calls: list[list[str]] = []
    try:
        runner = UIExecutionRunner(str(root))

        def _fake_popen(args, cwd=None, **kwargs):
            calls.append(list(args))
            class _Proc:
                pass
            return _Proc()

        monkeypatch.setattr(module.os, 'name', 'nt', raising=False)
        monkeypatch.setattr(module.subprocess, 'Popen', _fake_popen)

        assert runner._launch_target('codex') is True
        assert calls
        assert calls[0][:3] == ['cmd', '/c', 'start']
        assert calls[0][-1] == 'codex'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_extracts_codex_response_from_rollout_session() -> None:
    import json
    import sqlite3

    root = _workspace('ui_execution_runner_codex_rollout')
    codex_root = root / 'fake_codex_home'
    sessions_root = codex_root / 'sessions' / '2026' / '04' / '06'
    sessions_root.mkdir(parents=True, exist_ok=True)
    rollout_path = sessions_root / 'rollout-2026-04-06T10-00-00-test.jsonl'
    records = [
        {
            'timestamp': '2026-04-06T10:00:00Z',
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'user',
                'content': [{'type': 'input_text', 'text': 'Pending issue: issue-123\nDiagnostico breve: bridge lag'}],
            },
        },
        {
            'timestamp': '2026-04-06T10:00:05Z',
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'Causa raiz probable: El bridge visible acumula eventos. Cambio vertical recomendado: Ajustar drenado y sondeo.'}],
            },
        },
    ]
    with rollout_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    state_path = codex_root / 'state_5.sqlite'
    conn = sqlite3.connect(state_path)
    try:
        conn.execute('CREATE TABLE threads (rollout_path TEXT, updated_at INTEGER, cwd TEXT, title TEXT, archived INTEGER DEFAULT 0)')
        conn.execute(
            'INSERT INTO threads (rollout_path, updated_at, cwd, title, archived) VALUES (?, ?, ?, ?, 0)',
            (str(rollout_path), 1_900_000_000, str(root), 'Codex',),
        )
        conn.commit()
    finally:
        conn.close()

    runner = UIExecutionRunner(str(root))
    captured = runner._capture_codex_rollout_response(
        session_state_path=str(state_path),
        session_rollouts_root=str(codex_root / 'sessions'),
        fallback_session_state_path='',
        fallback_session_rollouts_root='',
        correlation_markers=['issue-123'],
        prompt_text='Pending issue: issue-123\nDiagnostico breve: bridge lag',
        started_after_unix=1_899_999_900,
    )

    assert captured['response_captured'] is True
    assert 'Causa raiz probable' in captured['captured_text']
    assert captured['focused_title'] == 'Codex'



def test_ui_execution_runner_prefers_explicit_codex_marker_over_prompt_similarity() -> None:
    import json
    import sqlite3

    root = _workspace('ui_execution_runner_codex_marker_priority')
    codex_root = root / 'fake_codex_home'
    sessions_root = codex_root / 'sessions' / '2026' / '04' / '06'
    sessions_root.mkdir(parents=True, exist_ok=True)
    wrong_rollout = sessions_root / 'rollout-2026-04-06T09-59-59-wrong.jsonl'
    correct_rollout = sessions_root / 'rollout-2026-04-06T10-00-00-correct.jsonl'
    wrong_records = [
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'user',
                'content': [{'type': 'input_text', 'text': 'Diagnostico breve: bridge lag en wplay pero sin marcador unico'}],
            },
        },
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'Respuesta equivocada del hilo parecido.'}],
            },
        },
    ]
    correct_records = [
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'user',
                'content': [{'type': 'input_text', 'text': 'Pending issue: issue-123\nDiagnostico breve: bridge lag en wplay'}],
            },
        },
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'Respuesta correcta del hilo con marcador unico.'}],
            },
        },
    ]
    for rollout_path, records in ((wrong_rollout, wrong_records), (correct_rollout, correct_records)):
        with rollout_path.open('w', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    state_path = codex_root / 'state_5.sqlite'
    conn = sqlite3.connect(state_path)
    try:
        conn.execute('CREATE TABLE threads (rollout_path TEXT, updated_at INTEGER, cwd TEXT, title TEXT, archived INTEGER DEFAULT 0)')
        conn.execute(
            'INSERT INTO threads (rollout_path, updated_at, cwd, title, archived) VALUES (?, ?, ?, ?, 0)',
            (str(wrong_rollout), 1_900_000_100, str(root), 'Codex',),
        )
        conn.execute(
            'INSERT INTO threads (rollout_path, updated_at, cwd, title, archived) VALUES (?, ?, ?, ?, 0)',
            (str(correct_rollout), 1_900_000_050, str(root), 'Codex',),
        )
        conn.commit()
    finally:
        conn.close()

    runner = UIExecutionRunner(str(root))
    captured = runner._capture_codex_rollout_response(
        session_state_path=str(state_path),
        session_rollouts_root=str(codex_root / 'sessions'),
        fallback_session_state_path='',
        fallback_session_rollouts_root='',
        correlation_markers=['issue-123', 'Pending issue: issue-123'],
        prompt_text='Pending issue: issue-123\nDiagnostico breve: bridge lag en wplay',
        started_after_unix=1_899_999_900,
    )

    assert captured['response_captured'] is True
    assert captured['captured_text'] == 'Respuesta correcta del hilo con marcador unico.'


def test_ui_execution_runner_marks_fallback_codex_rollout_as_unverified() -> None:
    import json
    import sqlite3

    root = _workspace('ui_execution_runner_codex_fallback_unverified')
    isolated_root = root / 'isolated_codex_home'
    fallback_root = root / 'fallback_codex_home'
    fallback_sessions = fallback_root / 'sessions' / '2026' / '04' / '12'
    fallback_sessions.mkdir(parents=True, exist_ok=True)
    rollout_path = fallback_sessions / 'rollout-2026-04-12T10-00-00-fallback.jsonl'
    records = [
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'user',
                'content': [{'type': 'input_text', 'text': 'IABV_THREAD_KEY: iabv::codex::audit::case-1\nDiagnostico breve: validar captura'}],
            },
        },
        {
            'type': 'response_item',
            'payload': {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'Respuesta encontrada en rollout fallback no verificado.'}],
            },
        },
    ]
    with rollout_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    fallback_state = fallback_root / 'state_5.sqlite'
    conn = sqlite3.connect(fallback_state)
    try:
        conn.execute('CREATE TABLE threads (rollout_path TEXT, updated_at INTEGER, cwd TEXT, title TEXT, archived INTEGER DEFAULT 0)')
        conn.execute(
            'INSERT INTO threads (rollout_path, updated_at, cwd, title, archived) VALUES (?, ?, ?, ?, 0)',
            (str(rollout_path), 1_900_000_000, str(root), 'Codex',),
        )
        conn.commit()
    finally:
        conn.close()

    runner = UIExecutionRunner(str(root))
    captured = runner._capture_codex_rollout_response(
        session_state_path=str(isolated_root / 'state_5.sqlite'),
        session_rollouts_root=str(isolated_root / 'sessions'),
        fallback_session_state_path=str(fallback_state),
        fallback_session_rollouts_root=str(fallback_root / 'sessions'),
        correlation_markers=['iabv::codex::audit::case-1'],
        prompt_text='IABV_THREAD_KEY: iabv::codex::audit::case-1\nDiagnostico breve: validar captura',
        started_after_unix=1_899_999_900,
    )

    assert captured['response_captured'] is True
    assert captured['thread_verified'] is False
    assert captured['used_fallback_capture'] is True
    assert captured['captured_text'] == 'Respuesta encontrada en rollout fallback no verificado.'


def test_ui_execution_runner_detects_browser_security_verification() -> None:
    root = _workspace('ui_execution_runner_browser_security_verification')
    try:
        runner = UIExecutionRunner(str(root))

        class _Locator:
            def __init__(self, selector: str) -> None:
                self.selector = selector

            def count(self) -> int:
                return 0

            def inner_text(self, timeout: int = 0) -> str:
                return 'Performing security verification. This website verifies you are not a bot. Ray ID: abc.'

        class _Page:
            url = 'https://chatgpt.com/'

            def goto(self, *args, **kwargs) -> None:
                return None

            def wait_for_load_state(self, *args, **kwargs) -> None:
                return None

            def title(self) -> str:
                return 'Just a moment...'

            def locator(self, selector: str) -> _Locator:
                return _Locator(selector)

        assert runner._browser_page_requires_security_verification(_Page()) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_propagates_codex_state_missing_from_rollout_probe(monkeypatch) -> None:
    root = _workspace('ui_execution_runner_codex_state_missing')
    try:
        runner = UIExecutionRunner(str(root))
        monkeypatch.setattr(runner, 'is_available', lambda: True)
        monkeypatch.setattr(runner, '_launch_target', lambda *args, **kwargs: True)
        monkeypatch.setattr(runner, '_wait_and_focus_any_window', lambda *args, **kwargs: 'Codex')
        monkeypatch.setattr(runner, '_paste_text', lambda *args, **kwargs: None)
        monkeypatch.setattr(runner, '_send_virtual_key', lambda *args, **kwargs: None)
        monkeypatch.setattr(runner, 'copy_active_window_text', lambda **kwargs: '')
        monkeypatch.setattr(
            runner,
            '_capture_codex_rollout_response',
            lambda **kwargs: {
                'response_captured': False,
                'captured_text': '',
                'focused_title': 'Codex',
                'error_message': 'codex_state_missing',
            },
        )

        captured = runner.capture_response_from_app(
            launch_target='codex',
            title_hints=['Codex'],
            prompt_text='Pending issue: issue-999',
            launch_mode='desktop_app',
            background_capture_mode='codex_rollout',
            response_wait_seconds=0.5,
        )

        assert captured['response_captured'] is False
        assert captured['error_message'] == 'codex_state_missing'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_propagates_verified_rollout_capture_metadata(monkeypatch) -> None:
    root = _workspace('ui_execution_runner_codex_rollout_metadata')
    try:
        runner = UIExecutionRunner(str(root))
        monkeypatch.setattr(runner, 'is_available', lambda: True)
        monkeypatch.setattr(runner, '_launch_target', lambda *args, **kwargs: True)
        monkeypatch.setattr(runner, '_wait_and_focus_any_window', lambda *args, **kwargs: 'Codex')
        monkeypatch.setattr(runner, '_paste_text', lambda *args, **kwargs: None)
        monkeypatch.setattr(runner, '_send_virtual_key', lambda *args, **kwargs: None)
        monkeypatch.setattr(runner, 'copy_active_window_text', lambda **kwargs: '')
        monkeypatch.setattr(
            runner,
            '_capture_codex_rollout_response',
            lambda **kwargs: {
                'response_captured': True,
                'captured_text': 'Respuesta verificada del rollout.',
                'focused_title': 'Codex',
                'error_message': '',
                'rollout_path': str(root / 'rollout.jsonl'),
                'thread_verified': True,
                'used_fallback_capture': False,
            },
        )

        captured = runner.capture_response_from_app(
            launch_target='codex',
            title_hints=['Codex'],
            prompt_text='Pending issue: issue-123',
            launch_mode='desktop_app',
            response_wait_seconds=0.5,
            background_capture_mode='codex_rollout',
            session_state_path=str(root / 'state_5.sqlite'),
            session_rollouts_root=str(root / 'sessions'),
            response_match_markers=['issue-123'],
            thread_key='issue-123',
        )

        assert captured['response_captured'] is True
        assert captured['capture_source'] == 'session_rollout'
        assert captured['thread_verified'] is True
        assert captured['used_fallback_capture'] is False
        assert captured['rollout_path'].endswith('rollout.jsonl')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_decodes_clipboard_fallback_without_charmap_crash(monkeypatch) -> None:
    root = _workspace('ui_execution_runner_clipboard_decode')
    try:
        runner = UIExecutionRunner(str(root))
        try:
            from PySide6.QtGui import QGuiApplication

            monkeypatch.setattr(QGuiApplication, 'instance', staticmethod(lambda: None), raising=False)
        except Exception:
            pass

        class _Completed:
            def __init__(self, stdout: bytes) -> None:
                self.stdout = stdout
                self.stderr = b''
                self.returncode = 0

        monkeypatch.setattr(
            module.subprocess,
            'run',
            lambda *args, **kwargs: _Completed('señal lista'.encode('cp1252')),
        )

        assert runner.read_clipboard_text() == 'señal lista'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ui_execution_runner_sets_clipboard_via_stdin_safe_command(monkeypatch) -> None:
    root = _workspace('ui_execution_runner_set_clipboard')
    calls: list[dict[str, object]] = []
    try:
        runner = UIExecutionRunner(str(root))
        try:
            from PySide6.QtGui import QGuiApplication

            monkeypatch.setattr(QGuiApplication, 'instance', staticmethod(lambda: None), raising=False)
        except Exception:
            pass

        class _Completed:
            def __init__(self) -> None:
                self.stdout = b''
                self.stderr = b''
                self.returncode = 0

        def _fake_run(args, **kwargs):
            calls.append({'args': list(args), **kwargs})
            return _Completed()

        monkeypatch.setattr(module.subprocess, 'run', _fake_run)

        runner._set_clipboard_text('texto seguro')

        assert calls
        assert calls[0]['args'][:3] == ['powershell', '-NoProfile', '-Command']
        assert 'Set-Clipboard -Value ([Console]::In.ReadToEnd())' in calls[0]['args'][3]
        assert calls[0]['input'] == 'texto seguro'.encode('utf-8')
    finally:
        shutil.rmtree(root, ignore_errors=True)
