"""Tests for ui_visibility_audit — UI visible event capture."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from iabv_v15.infra.ui_visibility_audit import (
    CAT_BACKGROUND,
    CAT_INTENTIONAL,
    CAT_UNEXPECTED,
    KIND_BG_CHECK,
    KIND_DIALOG_CLOSED,
    KIND_DIALOG_SHOWN,
    KIND_FILE_NOT_FOUND,
    KIND_INIT_CHECK,
    SRC_BOOTSTRAP,
    SRC_QML,
    SplashAuditAdapter,
    SubprocessAuditWrapper,
    VisibilityAuditLog,
)


@pytest.fixture()
def audit_log(tmp_path: Path) -> VisibilityAuditLog:
    log = VisibilityAuditLog()
    log.open(tmp_path / 'visible_events.jsonl')
    return log


class TestVisibilityAuditLog:
    def test_open_creates_jsonl_and_init_event(self, audit_log: VisibilityAuditLog, tmp_path: Path) -> None:
        path = tmp_path / 'visible_events.jsonl'
        assert path.exists()
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        ev = json.loads(lines[0])
        assert ev['kind'] == KIND_INIT_CHECK
        assert ev['event_category'] == CAT_BACKGROUND

    def test_record_intentional(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source=SRC_QML,
                         detail='Credencial requerida',
                         event_category=CAT_INTENTIONAL)
        s = audit_log.summary()
        assert s['total_events'] == 2  # init + dialog
        assert s['by_category'].get(CAT_INTENTIONAL) == 1

    def test_record_background(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record_background('provider probe', source='provider_probing')
        s = audit_log.summary()
        assert s['by_category'].get(CAT_BACKGROUND, 0) >= 2  # init + bg

    def test_record_file_not_found(self, audit_log: VisibilityAuditLog) -> None:
        try:
            raise FileNotFoundError(2, 'No such file', 'missing.exe')
        except FileNotFoundError as e:
            audit_log.record_file_not_found(e, source='test', cmd=['missing.exe'])
        s = audit_log.summary()
        assert s['file_not_found_count'] == 1
        assert s['unresolved_count'] >= 1
        fnf = s['file_not_found'][0]
        assert fnf['extra']['filename'] == 'missing.exe'

    def test_summary_categories(self, audit_log: VisibilityAuditLog) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source=SRC_QML,
                         event_category=CAT_INTENTIONAL)
        audit_log.record('win32_popup', source='watcher',
                         event_category=CAT_UNEXPECTED, unresolved=True)
        audit_log.record_background('check', source='test')
        s = audit_log.summary()
        assert CAT_INTENTIONAL in s['by_category']
        assert CAT_UNEXPECTED in s['by_category']
        assert CAT_BACKGROUND in s['by_category']

    def test_jsonl_persistence(self, audit_log: VisibilityAuditLog, tmp_path: Path) -> None:
        audit_log.record(KIND_DIALOG_SHOWN, source='test',
                         event_category=CAT_INTENTIONAL)
        audit_log.close()
        path = tmp_path / 'visible_events.jsonl'
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 2  # init + dialog


class TestSplashAuditAdapter:
    def test_splash_events(self, audit_log: VisibilityAuditLog) -> None:
        adapter = SplashAuditAdapter(audit_log)
        adapter.on_shown()
        adapter.on_closed()
        s = audit_log.summary()
        kinds = [e['kind'] for e in s['events']]
        assert KIND_DIALOG_SHOWN in kinds
        assert KIND_DIALOG_CLOSED in kinds


class TestSubprocessAuditWrapper:
    def test_captures_file_not_found(self, audit_log: VisibilityAuditLog) -> None:
        with pytest.raises(FileNotFoundError):
            with SubprocessAuditWrapper(audit_log, cmd=['nonexistent_binary'],
                                        source='test'):
                raise FileNotFoundError(2, 'not found', 'nonexistent_binary')
        s = audit_log.summary()
        assert s['file_not_found_count'] == 1

    def test_no_event_on_success(self, audit_log: VisibilityAuditLog) -> None:
        with SubprocessAuditWrapper(audit_log, cmd=['echo', 'hello'],
                                    source='test'):
            pass
        s = audit_log.summary()
        assert s['file_not_found_count'] == 0
