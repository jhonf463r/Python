from __future__ import annotations

import json
from pathlib import Path

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



def test_legacy_backlog_variant_without_id_is_reported_without_rewriting(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    legacy_task = {
        'title': 'Legacy resource deduction',
        'area': 'resource_management',
        'priority': 'high',
        'status': 'pending',
        'evidence': 'Historical task uses the added_by identity variant.',
        'added_by': 'resource_management_deduction',
    }
    original = json.dumps([legacy_task], ensure_ascii=False)
    path.write_text(original, encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))
    payload = report.to_mcp_payload()

    assert report.status == 'READ_OK'
    assert report.items == (legacy_task,)
    assert report.legacy_items_without_id == (1,)
    assert payload['legacy_items_without_id_count'] == 1
    assert payload['legacy_item_indexes_without_id'] == [1]
    assert load_backlog(str(tmp_path)) == [legacy_task]
    assert path.read_text(encoding='utf-8') == original


def test_backlog_task_missing_required_field_is_schema_unsupported(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    task = {
        'id': 'task-1',
        'area': 'integrity',
        'priority': 'high',
        'status': 'pending',
        'source': 'test',
        'created_at': '2026-11-05T00:00:00+00:00',
        'evidence': 'A title is required for task projection.',
    }
    original = json.dumps([task])
    path.write_text(original, encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))

    assert report.status == 'SCHEMA_UNSUPPORTED'
    assert report.error_type == 'InvalidBacklogSchema'
    assert 'task[1].title' in report.error_message
    assert report.to_mcp_payload()['total_all'] is None
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))
    with pytest.raises(EvolutionBacklogReadError):
        add_task(
            title='Must not overwrite malformed task',
            area='integrity',
            workspace=str(tmp_path),
        )
    assert path.read_text(encoding='utf-8') == original


def test_backlog_task_invalid_priority_and_dependency_shape_are_rejected(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    task = {
        'id': 'task-1',
        'title': 'Malformed task',
        'area': 'integrity',
        'priority': ['high'],
        'status': 'pending',
        'source': 'test',
        'created_at': '2026-11-05T00:00:00+00:00',
        'evidence': 'Priority must be a supported scalar.',
        'depends_on': [],
    }
    path.write_text(json.dumps([task]), encoding='utf-8')

    priority_report = load_backlog_with_diagnostics(str(tmp_path))

    assert priority_report.status == 'SCHEMA_UNSUPPORTED'
    assert 'task[1].priority' in priority_report.error_message
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))

    task['priority'] = 'high'
    task['depends_on'] = 'task-0'
    path.write_text(json.dumps([task]), encoding='utf-8')
    dependency_report = load_backlog_with_diagnostics(str(tmp_path))

    assert dependency_report.status == 'SCHEMA_UNSUPPORTED'
    assert 'task[1].depends_on' in dependency_report.error_message
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))


def test_backlog_duplicate_task_identity_is_schema_unsupported(tmp_path) -> None:
    path = _backlog_path(tmp_path)
    path.parent.mkdir(parents=True)
    task = {
        'id': 'duplicate-task',
        'title': 'Task',
        'area': 'integrity',
        'priority': 'medium',
        'status': 'pending',
        'source': 'test',
        'created_at': '2026-11-05T00:00:00+00:00',
        'evidence': 'Task identity must be unique.',
        'depends_on': [],
    }
    path.write_text(json.dumps([task, dict(task, title='Second task')]), encoding='utf-8')

    report = load_backlog_with_diagnostics(str(tmp_path))

    assert report.status == 'SCHEMA_UNSUPPORTED'
    assert 'duplicates an earlier task identity' in report.error_message
    with pytest.raises(EvolutionBacklogReadError):
        load_backlog(str(tmp_path))



def test_checked_in_backlog_satisfies_supported_task_schema() -> None:
    workspace = Path(__file__).resolve().parents[1]
    backlog_file = _backlog_path(workspace)
    assert backlog_file.is_file()

    report = load_backlog_with_diagnostics(str(workspace))

    assert report.status == 'READ_OK'
    assert len(report.items) > 0
    assert report.legacy_items_without_id
    assert all(index > 0 for index in report.legacy_items_without_id)
