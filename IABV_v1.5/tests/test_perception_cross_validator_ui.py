"""Tests for PerceptionCrossValidator._cross_ui_self_awareness().

Verifies the program can detect its own UI state anomalies:
- Missing IABV window
- Zombie windows ("No responde")
- Duplicate IABV instances
"""

from __future__ import annotations

import os

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from iabv_v15.domain.models import WindowObservation, WorldModelSnapshot
from iabv_v15.services.evolution.perception_cross_validator import (
    PerceptionCrossValidator,
)


def _make_validator(
    windows: list[WindowObservation] | None = None,
) -> PerceptionCrossValidator:
    wm_svc = MagicMock()
    snapshot = WorldModelSnapshot(
        active_windows=windows or [],
    )
    wm_svc.current_snapshot.return_value = snapshot
    wm_svc.current_model.return_value = snapshot
    validator = PerceptionCrossValidator(
        world_model_service=wm_svc,
        tool_registry=None,
    )
    validator._enumerate_window_titles = lambda: [
        str(window.title).strip().casefold()
        for window in snapshot.active_windows
        if str(window.title or '').strip()
    ]  # type: ignore[method-assign]
    return validator


def test_no_iabv_window_detected() -> None:
    """When no IABV window exists, flag it as missing."""
    validator = _make_validator(windows=[
        WindowObservation(title='Microsoft Edge', pid=100),
        WindowObservation(title='Explorer', pid=200),
    ])
    # Backdate _created_at so the timing heuristic considers this a
    # non-early-startup scan (>60s uptime) and severity stays HIGH.
    validator._created_at -= 120.0
    issues = validator._cross_ui_self_awareness()
    assert len(issues) == 1
    assert issues[0]['check'] == 'ui_self_awareness'
    assert issues[0]['severity'] == 'high'
    assert 'No IABV window' in issues[0]['actual']


def test_healthy_iabv_window_no_issues() -> None:
    """When a single healthy IABV window exists, no issues."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5', pid=100),
        WindowObservation(title='Edge', pid=200),
    ])
    issues = validator._cross_ui_self_awareness()
    assert len(issues) == 0


def test_zombie_iabv_window_detected() -> None:
    """Detect a zombie IABV window ('No responde')."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5 (No responde)', pid=1864),
        WindowObservation(title='IABV v1.5', pid=9576),
    ])
    issues = validator._cross_ui_self_awareness()
    assert len(issues) == 1
    assert issues[0]['check'] == 'ui_self_awareness'
    assert issues[0]['severity'] == 'high'
    assert 'zombie' in issues[0]['expected'].lower()
    assert 1864 in issues[0]['zombie_pids']


def test_zombie_only_no_healthy_window() -> None:
    """When only zombie windows exist, report zombie but not missing."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5 (No responde)', pid=1864),
    ])
    issues = validator._cross_ui_self_awareness()
    zombie_issues = [i for i in issues if 'zombie' in i.get('expected', '').lower()]
    missing_issues = [i for i in issues if 'visible' in i.get('expected', '').lower()]
    assert len(zombie_issues) == 1
    assert len(missing_issues) == 0


def test_duplicate_iabv_windows_detected() -> None:
    """Detect multiple IABV instances running simultaneously."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5', pid=100),
        WindowObservation(title='Centro de Control - IABV', pid=200),
        WindowObservation(title='Edge', pid=300),
    ])
    issues = validator._cross_ui_self_awareness()
    assert len(issues) == 1
    assert issues[0]['check'] == 'ui_self_awareness'
    assert issues[0]['severity'] == 'medium'
    assert '2' in issues[0]['actual']


def test_centro_vivo_title_recognized() -> None:
    """Centro Vivo window title is recognized as IABV."""
    validator = _make_validator(windows=[
        WindowObservation(title='Centro Vivo', pid=100),
    ])
    issues = validator._cross_ui_self_awareness()
    assert len(issues) == 0


def test_no_world_model_service_returns_empty() -> None:
    """When world_model_service is None, return empty list gracefully."""
    validator = PerceptionCrossValidator(
        world_model_service=None,
        tool_registry=None,
    )
    issues = validator._cross_ui_self_awareness()
    assert issues == []


def test_empty_windows_returns_empty() -> None:
    """When no windows at all, return empty (can't determine anything)."""
    validator = _make_validator(windows=[])
    issues = validator._cross_ui_self_awareness()
    assert issues == []


def test_run_cross_validation_includes_ui_check() -> None:
    """run_cross_validation() includes ui_self_awareness in results."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5', pid=100),
    ])
    result = validator.run_cross_validation()
    assert result['total_checks'] == 4
    assert 'ui_self_awareness' in result['checks_passed']


def test_run_cross_validation_reports_ui_issues() -> None:
    """run_cross_validation() reports UI issues in inconsistencies."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5 (No responde)', pid=1864),
        WindowObservation(title='IABV v1.5', pid=9576),
    ])
    result = validator.run_cross_validation()
    ui_issues = [
        i for i in result['inconsistencies']
        if i['check'] == 'ui_self_awareness'
    ]
    assert len(ui_issues) >= 1
    assert 'ui_self_awareness' not in result['checks_passed']


def test_not_responding_english_detected() -> None:
    """Detect 'Not Responding' (English locale) as zombie."""
    validator = _make_validator(windows=[
        WindowObservation(title='IABV v1.5 (Not Responding)', pid=500),
    ])
    issues = validator._cross_ui_self_awareness()
    zombie_issues = [i for i in issues if 'zombie' in i.get('expected', '').lower()]
    assert len(zombie_issues) == 1


def test_unconfigured_perception_checks_are_not_reported_as_passed() -> None:
    validator = PerceptionCrossValidator(
        world_model_service=None,
        tool_registry=None,
    )

    result = validator.run_cross_validation()

    assert result['checks_passed'] == []
    assert result['checks_status'] == {
        'tools_vs_processes': 'NOT_CONFIGURED',
        'audit_vs_worldmodel': 'NOT_CONFIGURED',
        'windows_consistency': 'NOT_CONFIGURED',
        'ui_self_awareness': 'NOT_CONFIGURED',
    }
    assert set(result['checks_unavailable']) == {
        'tools_vs_processes',
        'audit_vs_worldmodel',
        'windows_consistency',
        'ui_self_awareness',
    }


def test_world_model_read_exception_is_not_reported_as_passed() -> None:
    wm_svc = MagicMock()
    wm_svc.current_snapshot.side_effect = RuntimeError('snapshot unavailable')
    validator = PerceptionCrossValidator(
        world_model_service=wm_svc,
        tool_registry=MagicMock(),
    )

    result = validator.run_cross_validation()

    for check in ('audit_vs_worldmodel', 'windows_consistency', 'ui_self_awareness'):
        assert result['checks_status'][check] == 'READ_FAILED'
        assert check not in result['checks_passed']
        assert result['checks_unavailable'][check]['reason'] == 'RuntimeError'


def test_empty_window_snapshot_is_unverified_not_a_passed_ui_check() -> None:
    validator = _make_validator(windows=[])

    result = validator.run_cross_validation()

    assert result['checks_status']['ui_self_awareness'] == 'UNVERIFIED'
    assert 'ui_self_awareness' not in result['checks_passed']
    assert result['checks_unavailable']['ui_self_awareness']['reason'] == 'no_windows_observed'


def test_partial_tool_registry_report_is_not_reported_as_read_ok() -> None:
    report = SimpleNamespace(
        status=SimpleNamespace(value='READ_PARTIAL'),
        records_seen=3,
        records_loaded=2,
        failed_ids=['tool-corrupt'],
        missing_ids=[],
        collection_error_type='',
        to_dict=lambda: {
            'status': 'READ_PARTIAL',
            'records_seen': 3,
            'records_loaded': 2,
            'failed_ids': ['tool-corrupt'],
        },
    )

    class ReportedReadError(RuntimeError):
        def __init__(self):
            super().__init__('partial ToolRecord read')
            self.report = report

    class FailingToolRegistry:
        def list_cards(self):
            raise ReportedReadError()

    validator = _make_validator()
    validator.tool_registry = FailingToolRegistry()

    inconsistencies = validator._cross_audit_vs_worldmodel()

    assert inconsistencies == []
    assert validator._check_statuses['audit_vs_worldmodel'] == 'READ_PARTIAL'
    assert validator._check_reports['audit_vs_worldmodel']['records_loaded'] == 2


def test_partial_process_read_does_not_trigger_availability_auto_correction() -> None:
    validator = _make_validator(windows=[])
    correction_calls: list[list[dict[str, object]]] = []

    def partial_process_check() -> list[dict[str, object]]:
        validator._set_check_status(
            'tools_vs_processes',
            'READ_PARTIAL',
            'window_enumeration_failed',
        )
        return [{
            'check': 'tools_vs_processes',
            'severity': 'high',
            'tool_id': 'codex',
        }]

    validator._cross_tools_vs_processes = partial_process_check  # type: ignore[method-assign]
    validator._auto_correct_availability = (  # type: ignore[method-assign]
        lambda items: correction_calls.append(items) or []
    )

    result = validator.run_cross_validation()

    assert correction_calls == []
    assert result['auto_corrections'] == []
    assert result['checks_status']['tools_vs_processes'] == 'READ_PARTIAL'
    assert 'tools_vs_processes' not in result['checks_passed']



@pytest.mark.skipif(os.name != 'nt', reason='live Win32 window enumeration is Windows-only')
def test_windows_consistency_compares_world_model_with_live_enumeration() -> None:
    validator = _make_validator(windows=[
        WindowObservation(title='Editor - Workspace', pid=101),
        WindowObservation(title='Terminal', pid=102),
    ])
    validator._enumerate_window_titles = lambda: [  # type: ignore[method-assign]
        'editor - workspace',
        'Browser - IABV',
    ]

    result = validator.run_cross_validation()

    report = result['checks_read_reports']['windows_consistency']
    assert result['checks_status']['windows_consistency'] == 'READ_OK'
    assert report['world_model_window_count'] == 2
    assert report['live_window_count'] == 2
    assert report['world_model_only_window_count'] == 1
    assert report['live_only_window_count'] == 1
    assert 'windows_consistency' not in result['checks_passed']
    mismatch = next(
        item for item in result['inconsistencies']
        if item['check'] == 'windows_consistency'
        and 'live-only windows' in item['actual']
    )
    assert 'WorldModel-only windows=1' in mismatch['actual']
    assert 'live-only windows=1' in mismatch['actual']
    assert 'Editor - Workspace' not in mismatch['actual']


@pytest.mark.skipif(os.name != 'nt', reason='live Win32 window enumeration is Windows-only')
def test_windows_consistency_live_enumeration_failure_is_not_a_pass() -> None:
    validator = _make_validator(windows=[
        WindowObservation(title='Editor - Workspace', pid=101),
    ])

    def fail_live_enumeration() -> list[str]:
        raise RuntimeError('synthetic EnumWindows failure')

    validator._enumerate_window_titles = fail_live_enumeration  # type: ignore[method-assign]
    result = validator.run_cross_validation()

    assert result['checks_status']['windows_consistency'] == 'READ_FAILED'
    assert result['checks_unavailable']['windows_consistency']['reason'] == 'window_enumeration_failed'
    assert 'windows_consistency' not in result['checks_passed']


@pytest.mark.skipif(os.name != 'nt', reason='live Win32 window enumeration is Windows-only')
def test_windows_consistency_matching_live_enumeration_can_pass() -> None:
    validator = _make_validator(windows=[
        WindowObservation(title='Editor - Workspace', pid=101),
        WindowObservation(title='Terminal', pid=102),
    ])

    result = validator.run_cross_validation()

    assert result['checks_status']['windows_consistency'] == 'READ_OK'
    assert result['checks_read_reports']['windows_consistency']['world_model_only_window_count'] == 0
    assert result['checks_read_reports']['windows_consistency']['live_only_window_count'] == 0
    assert 'windows_consistency' in result['checks_passed']



def test_perception_validator_supports_world_model_current_model_api() -> None:
    snapshot = WorldModelSnapshot(
        active_windows=[WindowObservation(title='IABV v1.5', pid=100)],
    )

    class CurrentModelOnlyService:
        def current_model(self) -> WorldModelSnapshot:
            return snapshot

    validator = PerceptionCrossValidator(
        world_model_service=CurrentModelOnlyService(),
        tool_registry=SimpleNamespace(list_cards=lambda: []),
    )

    ui_issues = validator._cross_ui_self_awareness()
    audit_issues = validator._cross_audit_vs_worldmodel()

    assert ui_issues == []
    assert audit_issues == []
    assert validator._check_statuses['ui_self_awareness'] == 'READ_OK'
    assert validator._check_statuses['audit_vs_worldmodel'] == 'READ_OK'


@pytest.mark.skipif(os.name != 'nt', reason='live Win32 window enumeration is Windows-only')
def test_windows_consistency_uses_world_model_current_model_api() -> None:
    snapshot = WorldModelSnapshot(
        active_windows=[WindowObservation(title='IABV v1.5', pid=100)],
    )

    class CurrentModelOnlyService:
        def current_model(self) -> WorldModelSnapshot:
            return snapshot

    validator = PerceptionCrossValidator(
        world_model_service=CurrentModelOnlyService(),
        tool_registry=None,
    )
    validator._enumerate_window_titles = lambda: ['iabv v1.5']  # type: ignore[method-assign]

    issues = validator._cross_windows_consistency()

    assert issues == []
    assert validator._check_statuses['windows_consistency'] == 'READ_OK'


def test_zombie_window_diagnostics_do_not_export_private_window_titles() -> None:
    private_title = 'IABV - PRIVATE_DOCUMENT_TITLE_CANARY - Not Responding'
    validator = _make_validator(windows=[
        WindowObservation(title=private_title, pid=1864),
    ])
    issues = validator._cross_ui_self_awareness()

    assert len(issues) == 1
    assert issues[0]['actual'] == '1 zombie window(s) detected'
    assert 1864 in issues[0]['zombie_pids']
    assert 'PRIVATE_DOCUMENT_TITLE_CANARY' not in repr(issues)
    assert private_title not in repr(issues)



@pytest.mark.skipif(os.name != 'nt', reason='live Win32 window comparison is Windows-only')
def test_windows_consistency_diagnostics_do_not_export_private_window_titles() -> None:
    private_title = "PRIVATE_DOCUMENT_TITLE_CANARY — Acquisition Plan"
    validator = _make_validator(windows=[
        WindowObservation(title=private_title, pid=101),
        WindowObservation(title="Terminal", pid=102),
    ])
    validator._enumerate_window_titles = lambda: [
        "PRIVATE_DOCUMENT_TITLE_CANARY — Acquisition Plan",
        "Browser - IABV",
    ]  # type: ignore[method-assign]

    issues = validator._cross_windows_consistency()
    reports = validator._check_reports.get("windows_consistency", {})

    assert issues
    assert reports["world_model_only_window_count"] == 1
    assert reports["live_only_window_count"] == 1
    assert "PRIVATE_DOCUMENT_TITLE_CANARY" not in repr(issues)
    assert "PRIVATE_DOCUMENT_TITLE_CANARY" not in repr(reports)
