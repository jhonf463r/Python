"""Tests for PerceptionCrossValidator._cross_ui_self_awareness().

Verifies the program can detect its own UI state anomalies:
- Missing IABV window
- Zombie windows ("No responde")
- Duplicate IABV instances
"""

from __future__ import annotations

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
    return PerceptionCrossValidator(
        world_model_service=wm_svc,
        tool_registry=None,
    )


def test_no_iabv_window_detected() -> None:
    """When no IABV window exists, flag it as missing."""
    validator = _make_validator(windows=[
        WindowObservation(title='Microsoft Edge', pid=100),
        WindowObservation(title='Explorer', pid=200),
    ])
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
