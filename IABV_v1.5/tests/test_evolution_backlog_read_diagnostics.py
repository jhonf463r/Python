from __future__ import annotations

import json

import pytest

from iabv_v15.services.evolution_backlog import (
    EvolutionBacklogReadError,
    add_task,
    load_backlog,
    load_backlog_with_diagnostics,
)


def _backlog_path(workspace):
    return workspace / 'data' / 'evolution' / 'backlog.json'


def test_missing_backlog_file_is_distinct_from_verified_empty(tmp_path) -> None:
    report = load_backlog_with_diagnostics(str(tmp_path))

    assert report.status == 'CONFIRMED_NOT_FOUND'
    assert report.items == ()
    payload = report.to_mcp_payload()
    assert payload['status'] == 'CONFIRMED_NOT_FOUND'
    assert payload['total_all'] is None
    assert payload['total_pending'] is None
    assert load_backlog(str(tmp_path)) == []


def test_valid_empty_backlog_is_reported_as_successful_zero(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('[]', encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))
    payload = report.to_mcp_payload()

    assert report.status == 'READ_OK'
    assert report.items == ()
    assert payload['status'] == 'READ_OK'
    assert payload['total_all'] == 0
    assert payload['total_pending'] == 0
    assert load_backlog(str(tmp_path)) == []


def test_corrupt_backlog_is_not_treated_as_empty_or_overwritten(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{', encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))
    assert report.status == 'CORRUPT'
    assert report.error_type == 'JSONDecodeError'
    payload = report.to_mcp_payload()
    assert payload['total_all'] is None
    assert payload['total_pending'] is None

    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))
    with pytest.raises(EvolutionBacklogReadError):
        add_task(
            title='Must not overwrite corrupt backlog',
            area='integrity',
            workspace=str(tmp_path),
        )

    assert path.read_text(encoding='utf-8') == '{'


def test_unsupported_backlog_schema_is_not_treated_as_empty(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'tasks': []}), encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))

    assert report.status == 'SCHEMA_UNSUPPORTED'
    assert report.error_type == 'InvalidBacklogSchema'
    assert report.to_mcp_payload()['total_all'] is None
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))


def test_backlog_read_permission_error_is_reported(monkeypatch, tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('[]', encoding='utf-8')
    original_read_text = type(path).read_text

    def fail_target_read(self, *args, **kwargs):
        if self == path:
            raise PermissionError('synthetic denied read')
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(type(path), 'read_text', fail_target_read)
    report = load_backlog_with_diagnostics(str(tmp_path))

    assert report.status == 'READ_FAILED'
    assert report.error_type == 'PermissionError'
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))
