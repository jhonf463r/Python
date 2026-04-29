"""Tests for ``defer_services=True`` bootstrap speedup.

When ``defer_services=True``, ``AppBootstrap.__init__`` only sets up
config, logging and timeline — all service construction is deferred
to ``_wire_services()`` which ``run()`` calls after the splash is visible.

This tests the new contract:
- ``defer_services=False`` (default) behaves like before — all services
  are wired during ``__init__``.
- ``defer_services=True`` skips service wiring — services are ``None``
  until ``_wire_services()`` is called.
- ``_wire_services()`` is idempotent.
- Lazy module imports via ``_load_service_modules()`` are transparent.
- Timeline events record both the fast-init and deferred wiring phases.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_global_timeline():
    from iabv_v15.infra.startup_timeline import reset_global_timeline_for_tests
    reset_global_timeline_for_tests()
    yield
    reset_global_timeline_for_tests()


def test_default_bootstrap_wires_services_immediately(
    tmp_path: Path,
) -> None:
    """Default (defer_services=False) wires all services in __init__."""
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap = AppBootstrap(str(tmp_path))

    assert bootstrap._services_wired is True
    assert hasattr(bootstrap, 'db')
    assert hasattr(bootstrap, 'tool_registry')
    assert hasattr(bootstrap, 'world_model_service')
    assert bootstrap.world_model_service is not None


def test_deferred_bootstrap_skips_services(
    tmp_path: Path,
) -> None:
    """defer_services=True only does config/logging, no service wiring."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), defer_services=True)

    assert bootstrap._services_wired is False
    assert bootstrap.config is not None
    assert bootstrap.theme is not None
    # Services should not be wired yet
    assert not hasattr(bootstrap, 'db')
    assert not hasattr(bootstrap, 'tool_registry')
    assert not hasattr(bootstrap, 'world_model_service')


def test_wire_services_after_defer(
    tmp_path: Path,
) -> None:
    """Calling _wire_services() after defer populates everything."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), defer_services=True)
    assert bootstrap._services_wired is False

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services()

    assert bootstrap._services_wired is True
    assert bootstrap.db is not None
    assert bootstrap.tool_registry is not None
    assert bootstrap.world_model_service is not None


def test_wire_services_is_idempotent(
    tmp_path: Path,
) -> None:
    """Calling _wire_services() twice does not re-wire."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path), defer_services=True)

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services()
        first_db = bootstrap.db
        bootstrap._wire_services()
        assert bootstrap.db is first_db, 'Second call should be a no-op'


def test_deferred_bootstrap_records_timeline_events(
    tmp_path: Path,
) -> None:
    """Deferred bootstrap records init_done with services_deferred=True,
    then wire_services_start when wiring happens."""
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    bootstrap = AppBootstrap(str(tmp_path), defer_services=True)

    timeline = get_global_timeline()
    phases = [e['phase'] for e in timeline.events()]
    assert 'bootstrap_init_start' in phases
    assert 'bootstrap_init_done' in phases

    # Check that services_deferred flag is in the init_done event
    init_done_events = [e for e in timeline.events() if e['phase'] == 'bootstrap_init_done']
    assert len(init_done_events) == 1
    extra = init_done_events[0].get('extra', init_done_events[0])
    assert extra.get('services_deferred') is True

    # Wire services and check new timeline events
    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services()

    phases = [e['phase'] for e in timeline.events()]
    assert 'wire_services_start' in phases


def test_splash_callback_receives_messages(
    tmp_path: Path,
) -> None:
    """The splash_callback receives progress messages during wiring."""
    from iabv_v15.bootstrap import AppBootstrap

    messages: list[str] = []

    bootstrap = AppBootstrap(str(tmp_path), defer_services=True)

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        bootstrap._wire_services(splash_callback=messages.append)

    assert len(messages) >= 3, f'Expected >=3 progress messages, got {len(messages)}: {messages}'
    assert any('base de datos' in m.lower() for m in messages)
    assert any('herramientas' in m.lower() for m in messages)


def test_lazy_import_idempotent() -> None:
    """_load_service_modules() is idempotent and injects names."""
    from iabv_v15.bootstrap import _load_service_modules, _SERVICE_MODULES_LOADED
    import iabv_v15.bootstrap as bmod

    # Reset for test
    original = bmod._SERVICE_MODULES_LOADED
    try:
        bmod._SERVICE_MODULES_LOADED = False
        _load_service_modules()
        assert bmod._SERVICE_MODULES_LOADED is True
        # Key names should be in module globals
        assert hasattr(bmod, 'AppDatabase')
        assert hasattr(bmod, 'ToolRegistry')
        assert hasattr(bmod, 'WorldModelService')
        # Second call is a no-op
        _load_service_modules()
        assert bmod._SERVICE_MODULES_LOADED is True
    finally:
        bmod._SERVICE_MODULES_LOADED = original
