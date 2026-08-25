"""Tests for deferred bootstrap service wiring.

The split of ``AppBootstrap.__init__`` into a fast config phase and a
deferred ``_wire_services()`` phase is the main mechanism for getting the
splash visible before 19-22 s of service construction.

Contract:
- ``_defer_services=False`` (default, used by tests): ``__init__`` wires
  everything synchronously — backward compat, no regression.
- ``_defer_services=True`` (used by ``main.py``): ``__init__`` finishes
  in <1 s (config + logging only), ``_wire_services()`` is idempotent and
  called from ``run()`` after the splash is visible.
- When scans are deferred, ``WorldModelService`` and
  ``EnvironmentSelfAwarenessService`` skip their blocking bootstrap scans
  and instead rely on their background threads + an async refresh signal.
- Timeline records ``wire_services_start`` / ``wire_services_done`` when
  the wiring phase runs, with ``scans_deferred`` metadata.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_global_timeline():
    from iabv_v15.infra.startup_timeline import reset_global_timeline_for_tests
    reset_global_timeline_for_tests()
    yield
    reset_global_timeline_for_tests()


# ------------------------------------------------------------------
# 1. Default (non-deferred) keeps old behaviour
# ------------------------------------------------------------------

def test_default_init_wires_services_immediately(tmp_path: Path) -> None:
    """Without ``_defer_services``, services are wired in ``__init__``."""
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    assert bootstrap._services_wired is True
    assert hasattr(bootstrap, 'db')
    assert hasattr(bootstrap, 'tool_registry')
    assert hasattr(bootstrap, 'world_model_service')
    assert hasattr(bootstrap, 'operational_self_examination_service')


def test_default_init_records_wire_services_in_timeline(tmp_path: Path) -> None:
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        AppBootstrap(str(tmp_path))

    phases = [e['phase'] for e in get_global_timeline().events()]
    assert 'wire_services_start' in phases
    assert 'wire_services_done' in phases
    assert phases.index('bootstrap_init_start') < phases.index('wire_services_start')
    assert phases.index('wire_services_done') < phases.index('bootstrap_init_done')


# ------------------------------------------------------------------
# 2. Deferred mode: __init__ is fast, services wired later
# ------------------------------------------------------------------

def test_deferred_init_does_not_wire_services(tmp_path: Path) -> None:
    """With ``_defer_services=True``, __init__ skips heavy wiring."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)

    assert bootstrap._services_wired is False
    assert not hasattr(bootstrap, 'db')
    assert not hasattr(bootstrap, 'tool_registry')
    assert not hasattr(bootstrap, 'world_model_service')


def test_deferred_init_is_fast(tmp_path: Path) -> None:
    """Deferred __init__ should complete in well under 2 seconds."""
    from iabv_v15.bootstrap import AppBootstrap

    t0 = time.monotonic()
    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)
    elapsed = time.monotonic() - t0

    assert bootstrap._services_wired is False
    assert elapsed < 2.0, (
        f'Deferred __init__ took {elapsed:.2f}s — should be <2s '
        '(config + logging only, no service construction).'
    )


def test_deferred_init_sets_vm_placeholders(tmp_path: Path) -> None:
    """Even when deferred, VM placeholders must exist for create_engine."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)

    assert bootstrap.navigation_controller is None
    assert bootstrap.control_center_viewmodel is None
    assert bootstrap.dashboard_viewmodel is None
    assert bootstrap.evolution_center_viewmodel is None


def test_deferred_init_timeline_marks_services_deferred(tmp_path: Path) -> None:
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    AppBootstrap(str(tmp_path), _defer_services=True)

    events = get_global_timeline().events()
    init_done = [e for e in events if e['phase'] == 'bootstrap_init_done']
    assert len(init_done) == 1
    extra = init_done[0].get('extra', {})
    assert extra.get('services_deferred') is True

    phases = [e['phase'] for e in events]
    assert 'wire_services_start' not in phases


# ------------------------------------------------------------------
# 3. _wire_services() is idempotent and callable after deferred init
# ------------------------------------------------------------------

def test_wire_services_after_deferred_init(tmp_path: Path) -> None:
    """Calling _wire_services() after deferred init wires everything."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)
    assert bootstrap._services_wired is False

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services()

    assert bootstrap._services_wired is True
    assert hasattr(bootstrap, 'db')
    assert hasattr(bootstrap, 'tool_registry')
    assert hasattr(bootstrap, 'world_model_service')


def test_wire_services_idempotent(tmp_path: Path) -> None:
    """Calling _wire_services() twice is safe — second call is a no-op."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    assert bootstrap._services_wired is True
    wire_count_before = sum(
        1 for e in get_global_timeline().events()
        if e['phase'] == 'wire_services_start'
    )

    bootstrap._wire_services()  # should be no-op

    wire_count_after = sum(
        1 for e in get_global_timeline().events()
        if e['phase'] == 'wire_services_start'
    )
    assert wire_count_before == wire_count_after == 1


# ------------------------------------------------------------------
# 4. Deferred scans: WorldModel + EnvironmentSelf skip bootstrap_scan
# ------------------------------------------------------------------

def test_deferred_scans_skip_bootstrap_scan(tmp_path: Path) -> None:
    """When services are deferred, blocking bootstrap scans are skipped."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.services.evolution.world_model_service import WorldModelService
    from iabv_v15.services.evolution.environment_self_awareness_service import (
        EnvironmentSelfAwarenessService,
    )

    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)

    wm_scan_calls = []
    esa_scan_calls = []

    orig_wm_init = WorldModelService.__init__
    orig_esa_init = EnvironmentSelfAwarenessService.__init__

    def patched_wm_init(self_wm, **kwargs):
        wm_scan_calls.append(kwargs.get('bootstrap_scan', True))
        orig_wm_init(self_wm, **kwargs)

    def patched_esa_init(self_esa, **kwargs):
        esa_scan_calls.append(kwargs.get('bootstrap_scan', True))
        orig_esa_init(self_esa, **kwargs)

    with (
        patch.object(WorldModelService, '__init__', patched_wm_init),
        patch.object(EnvironmentSelfAwarenessService, '__init__', patched_esa_init),
        patch.object(AppBootstrap, '_log_tool_availability', autospec=True),
    ):
        bootstrap._wire_services()

    assert wm_scan_calls == [False], (
        f'WorldModelService should receive bootstrap_scan=False when deferred; got {wm_scan_calls}'
    )
    assert esa_scan_calls == [False], (
        f'EnvironmentSelfAwarenessService should receive bootstrap_scan=False when deferred; got {esa_scan_calls}'
    )


def test_non_deferred_scans_run_bootstrap_scan(tmp_path: Path) -> None:
    """Without deferral, blocking bootstrap scans run as before."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.services.evolution.world_model_service import WorldModelService

    wm_scan_calls = []
    orig_wm_init = WorldModelService.__init__

    def patched_wm_init(self_wm, **kwargs):
        wm_scan_calls.append(kwargs.get('bootstrap_scan', True))
        orig_wm_init(self_wm, **kwargs)

    with (
        patch.object(WorldModelService, '__init__', patched_wm_init),
        patch.object(AppBootstrap, '_log_tool_availability', autospec=True),
    ):
        AppBootstrap(str(tmp_path))

    assert wm_scan_calls == [True], (
        f'WorldModelService should receive bootstrap_scan=True by default; got {wm_scan_calls}'
    )


# ------------------------------------------------------------------
# 5. Timeline evidence: wire_services has scans_deferred metadata
# ------------------------------------------------------------------

def test_wire_services_done_records_scans_deferred(tmp_path: Path) -> None:
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    bootstrap = AppBootstrap(str(tmp_path), _defer_services=True)
    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services()

    events = get_global_timeline().events()
    wire_done = [e for e in events if e['phase'] == 'wire_services_done']
    assert len(wire_done) == 1
    extra = wire_done[0].get('extra', {})
    assert extra.get('scans_deferred') is True
