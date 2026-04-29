"""Focused tests for ``iabv_v15.infra.startup_timeline``.

Covers:
- mark() records phase, monotonically increasing t_ms, and an rss_mb field
- JSONL persistence is opt-in (only when log_dir is configured)
- IABV_STARTUP_TIMELINE=0 disables the JSONL sink even when log_dir is set
- get_global_timeline() returns a singleton; reset_global_timeline_for_tests
  produces a fresh anchor
- mark() never raises, even if the log_dir is unwritable
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from iabv_v15.infra.startup_timeline import (
    StartupTimeline,
    configure_global_timeline,
    get_global_timeline,
    reset_global_timeline_for_tests,
)


def test_mark_records_event_with_phase_and_elapsed():
    tl = StartupTimeline()
    first = tl.mark('first')
    time.sleep(0.005)
    second = tl.mark('second', detail='x')
    assert first['phase'] == 'first'
    assert second['phase'] == 'second'
    assert 'rss_mb' in first
    assert second['t_ms_from_start'] >= first['t_ms_from_start']
    # extra detail surfaces under "extra"
    assert second['extra'] == {'detail': 'x'}
    assert tl.events() == [first, second]


def test_jsonl_sink_writes_one_line_per_mark(tmp_path: Path):
    tl = StartupTimeline(log_dir=tmp_path)
    tl.mark('alpha')
    tl.mark('beta', count=2)
    target = tmp_path / 'startup_timeline.jsonl'
    assert target.exists()
    lines = [json.loads(line) for line in target.read_text().splitlines() if line.strip()]
    assert [event['phase'] for event in lines] == ['alpha', 'beta']
    assert lines[1]['extra'] == {'count': 2}


def test_jsonl_sink_disabled_via_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('IABV_STARTUP_TIMELINE', '0')
    tl = StartupTimeline(log_dir=tmp_path)
    tl.mark('event')
    target = tmp_path / 'startup_timeline.jsonl'
    # Sink is disabled, so no file is created — but events still recorded in memory.
    assert not target.exists()
    assert [event['phase'] for event in tl.events()] == ['event']


def test_global_timeline_is_singleton():
    reset_global_timeline_for_tests()
    a = get_global_timeline()
    b = get_global_timeline()
    assert a is b
    reset_global_timeline_for_tests()
    c = get_global_timeline()
    assert c is not a


def test_configure_global_timeline_attaches_log_dir(tmp_path: Path):
    reset_global_timeline_for_tests()
    tl = configure_global_timeline(tmp_path)
    tl.mark('cfg')
    assert (tmp_path / 'startup_timeline.jsonl').exists()


def test_configure_global_timeline_backfills_events_recorded_before_log_dir(tmp_path: Path):
    reset_global_timeline_for_tests()
    tl = get_global_timeline()
    tl.mark('bootstrap_init_start')
    tl.mark('bootstrap_mid')
    configure_global_timeline(tmp_path)
    tl.mark('bootstrap_init_done')
    target = tmp_path / 'startup_timeline.jsonl'
    lines = [json.loads(line) for line in target.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert [event['phase'] for event in lines] == [
        'bootstrap_init_start',
        'bootstrap_mid',
        'bootstrap_init_done',
    ]


def test_mark_never_raises_when_log_dir_is_unwritable(tmp_path: Path):
    bogus = tmp_path / 'nonexistent' / 'subdir'
    tl = StartupTimeline(log_dir=bogus)
    # Should not raise even though the parent doesn't exist; instead the
    # sink does mkdir(parents=True) — verify we still get an event back.
    event = tl.mark('safe')
    assert event['phase'] == 'safe'


def test_reset_clears_events_and_reanchors():
    tl = StartupTimeline()
    tl.mark('a')
    tl.mark('b')
    assert len(tl.events()) == 2
    tl.reset()
    assert tl.events() == []
    new_event = tl.mark('c')
    assert new_event['t_ms_from_start'] < 100.0


def test_mark_logs_unicode_extra_safely(tmp_path: Path):
    tl = StartupTimeline(log_dir=tmp_path)
    tl.mark('phase', message='listo — splash 0-20%')
    line = (tmp_path / 'startup_timeline.jsonl').read_text(encoding='utf-8').strip()
    parsed = json.loads(line)
    assert parsed['extra']['message'] == 'listo — splash 0-20%'
