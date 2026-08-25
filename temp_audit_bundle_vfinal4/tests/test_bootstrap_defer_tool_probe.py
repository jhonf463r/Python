"""Regression: AppBootstrap defers ``_log_tool_availability`` from ``__init__``.

The probe issues HTTP pings (Devin / GitHub / Ollama) and triggers
``auto_fix_missing_tools`` (which can run ``pip install mcp_client``).
Running it inside ``__init__`` blocked splash rendering for 1-2s on
Linux and far longer on Windows with cold pip.  The new contract:

- by default the probe is skipped during ``__init__`` and run later
  via ``_run_deferred_post_window_setup`` (scheduled by ``run()``)
- legacy synchronous behavior is restorable via
  ``IABV_DEFER_TOOL_PROBE=0`` so existing test suites that rely on
  the side effects still work
- ``_run_deferred_post_window_setup`` is idempotent
- the global ``StartupTimeline`` records ``bootstrap_init_start`` and
  ``bootstrap_init_done`` whenever a bootstrap is constructed
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


def test_bootstrap_init_does_not_run_tool_probe_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 0, (
            'Tool-availability probe should be deferred from __init__ by '
            'default to keep the splash → shell critical path light.'
        )
        assert bootstrap._tool_availability_logged is False


def test_bootstrap_init_runs_probe_when_defer_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('IABV_DEFER_TOOL_PROBE', '0')
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        assert probe.call_count == 1
        assert bootstrap._tool_availability_logged is True


def test_run_deferred_post_window_setup_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    import threading
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(
        AppBootstrap, '_log_tool_availability', autospec=True
    ) as probe:
        bootstrap = AppBootstrap(str(tmp_path))
        bootstrap._run_deferred_post_window_setup()
        bootstrap._run_deferred_post_window_setup()
        bootstrap._run_deferred_post_window_setup()
        # The method runs _log_tool_availability in a background thread;
        # wait for all daemon threads spawned by the method to finish.
        for t in threading.enumerate():
            if t.name == 'iabv-deferred-post-window' and t.is_alive():
                t.join(timeout=5)
        assert probe.call_count == 1, (
            'Deferred probe must run at most once even if scheduled twice.'
        )
        assert bootstrap._tool_availability_logged is True


def test_bootstrap_records_init_start_and_init_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    from iabv_v15.bootstrap import AppBootstrap
    from iabv_v15.infra.startup_timeline import get_global_timeline

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        AppBootstrap(str(tmp_path))

    phases = [event['phase'] for event in get_global_timeline().events()]
    assert 'bootstrap_init_start' in phases
    assert 'bootstrap_init_done' in phases
    assert phases.index('bootstrap_init_start') < phases.index(
        'bootstrap_init_done'
    )


def test_bootstrap_jsonl_timeline_persisted_under_logs_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('IABV_DEFER_TOOL_PROBE', raising=False)
    monkeypatch.setenv('IABV_STARTUP_TIMELINE', '1')
    from iabv_v15.bootstrap import AppBootstrap

    with patch.object(AppBootstrap, '_log_tool_availability', autospec=True):
        AppBootstrap(str(tmp_path))

    jsonl = tmp_path / 'data' / 'logs' / 'startup_timeline.jsonl'
    assert jsonl.exists(), (
        f'Expected startup_timeline.jsonl at {jsonl}; bootstrap should '
        'attach the JSONL sink to the global timeline once logs_dir exists.'
    )
    lines = jsonl.read_text(encoding='utf-8').splitlines()
    assert any('bootstrap_init_done' in line for line in lines)
