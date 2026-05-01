"""Focused tests for BootProfileStore — boot telemetry persistence by environment_id.

Covers:
- record_boot_session persists to correct JSONL file
- load_history reads back recorded sessions
- boot_profile_summary computes avg/median/p95/slowest phases
- all_known_profiles lists environments with data
- compare_environments cross-device comparison
- empty store edge cases
- corrupt JSONL resilience
- phase duration computation
- wiring_duration_ms vs boot_duration_ms semantic separation
- late milestones (page_loader_ready, splash_window_closing) included
- bootstrap wiring: deferred persistence at page_loader_ready
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.services.evolution.boot_profile_store import BootProfileStore


@pytest.fixture
def store(tmp_path: Path) -> BootProfileStore:
    return BootProfileStore(data_root=tmp_path)


def _sample_timeline_events() -> list[dict[str, Any]]:
    """Wiring-only events (no late milestones)."""
    return [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 96.0},
        {'phase': 'wire_services_start', 't_ms_from_start': 25.0, 'rss_mb': 97.0},
        {'phase': 'wire_services_done', 't_ms_from_start': 18170.0, 'rss_mb': 112.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': 22000.0, 'rss_mb': 115.0},
    ]


def _full_boot_timeline_events() -> list[dict[str, Any]]:
    """Full boot including late milestones that only fire after UI renders."""
    return [
        {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 96.0},
        {'phase': 'wire_services_start', 't_ms_from_start': 25.0, 'rss_mb': 97.0},
        {'phase': 'wire_services_done', 't_ms_from_start': 18170.0, 'rss_mb': 112.0},
        {'phase': 'shell_loader_ready', 't_ms_from_start': 22000.0, 'rss_mb': 115.0},
        {'phase': 'page_loader_ready', 't_ms_from_start': 24500.0, 'rss_mb': 118.0},
        {'phase': 'splash_window_closing', 't_ms_from_start': 25200.0, 'rss_mb': 118.0},
    ]


# ------------------------------------------------------------------
# record + load
# ------------------------------------------------------------------


class TestRecordAndLoad:
    def test_record_creates_file(self, store: BootProfileStore):
        record = store.record_boot_session(
            environment_id='faber-laptop-a1b2c3',
            timeline_events=_sample_timeline_events(),
        )
        assert record['environment_id'] == 'faber-laptop-a1b2c3'
        assert record['boot_duration_ms'] == 22000.0
        assert record['rss_peak_mb'] == 115.0
        assert record['phase_count'] == 4
        assert 'timestamp_utc' in record

        path = store._profile_path('faber-laptop-a1b2c3')
        assert path.exists()

    def test_load_history_returns_recorded(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        history = store.load_history('env-1')
        assert len(history) == 1
        assert history[0]['environment_id'] == 'env-1'
        assert history[0]['boot_duration_ms'] == 22000.0

    def test_multiple_sessions_append(self, store: BootProfileStore):
        for _ in range(3):
            store.record_boot_session(
                environment_id='env-1',
                timeline_events=_sample_timeline_events(),
            )
        history = store.load_history('env-1')
        assert len(history) == 3

    def test_separate_environments_separate_files(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='laptop-a',
            timeline_events=_sample_timeline_events(),
        )
        store.record_boot_session(
            environment_id='desktop-b',
            timeline_events=_sample_timeline_events(),
        )
        assert len(store.load_history('laptop-a')) == 1
        assert len(store.load_history('desktop-b')) == 1

    def test_load_history_limit(self, store: BootProfileStore):
        for _ in range(10):
            store.record_boot_session(
                environment_id='env-1',
                timeline_events=_sample_timeline_events(),
            )
        history = store.load_history('env-1', limit=3)
        assert len(history) == 3

    def test_metadata_persisted(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
            metadata={'scan_status': 'ready', 'known_environment': True},
        )
        history = store.load_history('env-1')
        assert history[0]['metadata']['scan_status'] == 'ready'
        assert history[0]['metadata']['known_environment'] is True

    def test_explicit_duration_and_rss(self, store: BootProfileStore):
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=[],
            boot_duration_ms=5000.0,
            rss_peak_mb=200.0,
        )
        assert record['boot_duration_ms'] == 5000.0
        assert record['rss_peak_mb'] == 200.0


# ------------------------------------------------------------------
# Empty / edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_history(self, store: BootProfileStore):
        assert store.load_history('nonexistent') == []

    def test_empty_timeline_events(self, store: BootProfileStore):
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=[],
        )
        assert record['boot_duration_ms'] == 0.0
        assert record['wiring_duration_ms'] == 0.0
        assert record['rss_peak_mb'] == 0.0
        assert record['phase_count'] == 0

    def test_single_event_timeline(self, store: BootProfileStore):
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=[{'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 50.0}],
        )
        assert record['boot_duration_ms'] == 0.0
        assert record['rss_peak_mb'] == 50.0

    def test_corrupt_jsonl_resilience(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        path = store._profile_path('env-1')
        with path.open('a', encoding='utf-8') as f:
            f.write('CORRUPT LINE\n')
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        history = store.load_history('env-1')
        assert len(history) == 2

    def test_all_known_profiles_empty(self, store: BootProfileStore):
        assert store.all_known_profiles() == []


# ------------------------------------------------------------------
# Phase duration computation
# ------------------------------------------------------------------


class TestPhaseDurations:
    def test_phase_durations_computed(self, store: BootProfileStore):
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        durations = record['phase_durations']
        assert len(durations) == 3
        assert durations[0] == {'phase': 'wire_services_start', 'duration_ms': 25.0}
        assert durations[1] == {'phase': 'wire_services_done', 'duration_ms': 18145.0}
        assert durations[2] == {'phase': 'shell_loader_ready', 'duration_ms': 3830.0}


# ------------------------------------------------------------------
# wiring_duration_ms vs boot_duration_ms
# ------------------------------------------------------------------


class TestWiringVsBootDuration:
    def test_wiring_duration_extracted_from_timeline(self, store: BootProfileStore):
        """wiring_duration_ms = wire_services_done - bootstrap_init_start."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert record['wiring_duration_ms'] == 18170.0

    def test_boot_duration_includes_late_milestones(self, store: BootProfileStore):
        """boot_duration_ms spans the full timeline including page_loader_ready."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert record['boot_duration_ms'] == 25200.0

    def test_wiring_shorter_than_boot(self, store: BootProfileStore):
        """wiring_duration_ms must always be <= boot_duration_ms."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert record['wiring_duration_ms'] < record['boot_duration_ms']

    def test_wiring_zero_without_phases(self, store: BootProfileStore):
        """wiring_duration_ms is 0 when phases are missing."""
        events = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'done', 't_ms_from_start': 5000.0, 'rss_mb': 90.0},
        ]
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=events,
        )
        assert record['wiring_duration_ms'] == 0.0
        assert record['boot_duration_ms'] == 5000.0

    def test_explicit_wiring_duration(self, store: BootProfileStore):
        """Explicit wiring_duration_ms overrides auto-computation."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
            wiring_duration_ms=12345.0,
        )
        assert record['wiring_duration_ms'] == 12345.0


# ------------------------------------------------------------------
# Late milestones included in profile
# ------------------------------------------------------------------


class TestLateMilestonesIncluded:
    def test_page_loader_ready_in_phases(self, store: BootProfileStore):
        """page_loader_ready must appear in the persisted phase list."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert 'page_loader_ready' in record['phases']

    def test_splash_window_closing_in_phases(self, store: BootProfileStore):
        """splash_window_closing must appear in the persisted phase list."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert 'splash_window_closing' in record['phases']

    def test_boot_duration_reflects_splash_closing(self, store: BootProfileStore):
        """boot_duration_ms must reach splash_window_closing, not stop at wiring."""
        record = store.record_boot_session(
            environment_id='env-1',
            timeline_events=_full_boot_timeline_events(),
        )
        assert record['boot_duration_ms'] == 25200.0
        assert record['boot_duration_ms'] > 18170.0

    def test_truncated_at_wiring_misses_real_boot(self, store: BootProfileStore):
        """Demonstrates that wiring-only timeline truncates boot_duration_ms."""
        wiring_only = _sample_timeline_events()
        full_boot = _full_boot_timeline_events()

        rec_truncated = store.record_boot_session(
            environment_id='env-trunc', timeline_events=wiring_only,
        )
        rec_full = store.record_boot_session(
            environment_id='env-full', timeline_events=full_boot,
        )
        assert rec_truncated['boot_duration_ms'] < rec_full['boot_duration_ms']
        assert rec_full['boot_duration_ms'] == 25200.0
        assert rec_truncated['boot_duration_ms'] == 22000.0


# ------------------------------------------------------------------
# boot_profile_summary
# ------------------------------------------------------------------


class TestBootProfileSummary:
    def test_no_data(self, store: BootProfileStore):
        summary = store.boot_profile_summary('nonexistent')
        assert summary['boot_count'] == 0
        assert summary['status'] == 'no_data'

    def test_single_boot_summary(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        summary = store.boot_profile_summary('env-1')
        assert summary['boot_count'] == 1
        assert summary['boot_duration']['avg_ms'] == 22000.0
        assert summary['boot_duration']['median_ms'] == 22000.0
        assert summary['rss_peak']['avg_mb'] == 115.0
        assert len(summary['slowest_phases']) > 0

    def test_multiple_boots_aggregation(self, store: BootProfileStore):
        events_fast = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
            {'phase': 'done', 't_ms_from_start': 10000.0, 'rss_mb': 100.0},
        ]
        events_slow = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 90.0},
            {'phase': 'done', 't_ms_from_start': 30000.0, 'rss_mb': 130.0},
        ]
        store.record_boot_session(environment_id='env-1', timeline_events=events_fast)
        store.record_boot_session(environment_id='env-1', timeline_events=events_slow)
        store.record_boot_session(environment_id='env-1', timeline_events=events_fast)

        summary = store.boot_profile_summary('env-1')
        assert summary['boot_count'] == 3
        avg = summary['boot_duration']['avg_ms']
        assert 16000.0 < avg < 17000.0

    def test_slowest_phases_ranked(self, store: BootProfileStore):
        store.record_boot_session(
            environment_id='env-1',
            timeline_events=_sample_timeline_events(),
        )
        summary = store.boot_profile_summary('env-1')
        phases = summary['slowest_phases']
        assert phases[0]['phase'] == 'wire_services_done'
        assert phases[0]['avg_ms'] == 18145.0

    def test_boot_count_not_capped_by_limit(self, store: BootProfileStore):
        """boot_count must reflect total sessions, not the windowed limit."""
        events = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'done', 't_ms_from_start': 5000.0, 'rss_mb': 90.0},
        ]
        for _ in range(60):
            store.record_boot_session(environment_id='env-many', timeline_events=events)

        summary = store.boot_profile_summary('env-many')
        assert summary['boot_count'] == 60

    def test_first_seen_accurate_beyond_limit(self, store: BootProfileStore):
        """first_seen must be from the very first boot, not the windowed tail."""
        import json as _json

        events = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'done', 't_ms_from_start': 5000.0, 'rss_mb': 90.0},
        ]
        store.record_boot_session(environment_id='env-fs', timeline_events=events)
        path = store._profile_path('env-fs')
        first_line = path.read_text(encoding='utf-8').strip().split('\n')[0]
        first_ts = _json.loads(first_line)['timestamp_utc']

        for _ in range(55):
            store.record_boot_session(environment_id='env-fs', timeline_events=events)

        summary = store.boot_profile_summary('env-fs')
        assert summary['boot_count'] == 56
        assert summary['first_seen'] == first_ts


# ------------------------------------------------------------------
# all_known_profiles + compare_environments
# ------------------------------------------------------------------


class TestCompareEnvironments:
    def test_all_known_profiles(self, store: BootProfileStore):
        store.record_boot_session(environment_id='laptop-a', timeline_events=_sample_timeline_events())
        store.record_boot_session(environment_id='desktop-b', timeline_events=_sample_timeline_events())
        profiles = store.all_known_profiles()
        assert 'desktop-b' in profiles
        assert 'laptop-a' in profiles

    def test_compare_empty(self, store: BootProfileStore):
        result = store.compare_environments()
        assert result['environments'] == []
        assert result['comparison'] == []

    def test_compare_skips_all_corrupt_environment(self, store: BootProfileStore):
        """compare_environments must not KeyError when all JSONL lines are corrupt."""
        store._profiles_dir.mkdir(parents=True, exist_ok=True)
        path = store._profile_path('corrupt-env')
        path.write_text('NOT JSON\nALSO NOT JSON\n', encoding='utf-8')

        result = store.compare_environments()
        assert result['comparison'] == []

    def test_compare_two_environments(self, store: BootProfileStore):
        fast_events = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 80.0},
            {'phase': 'done', 't_ms_from_start': 5000.0, 'rss_mb': 90.0},
        ]
        slow_events = [
            {'phase': 'start', 't_ms_from_start': 0.0, 'rss_mb': 100.0},
            {'phase': 'done', 't_ms_from_start': 25000.0, 'rss_mb': 150.0},
        ]
        store.record_boot_session(environment_id='fast-machine', timeline_events=fast_events)
        store.record_boot_session(environment_id='slow-machine', timeline_events=slow_events)

        result = store.compare_environments()
        assert len(result['comparison']) == 2
        assert result['comparison'][0]['environment_id'] == 'fast-machine'
        assert result['comparison'][0]['avg_boot_ms'] == 5000.0
        assert result['comparison'][1]['environment_id'] == 'slow-machine'
        assert result['comparison'][1]['avg_boot_ms'] == 25000.0


# ------------------------------------------------------------------
# Bootstrap wiring: deferred persistence integration
# ------------------------------------------------------------------


class TestBootstrapDeferredPersistence:
    def test_prepare_then_persist_pattern(self, tmp_path: Path):
        """Simulates the bootstrap pattern: prepare at wire_services_done,
        persist at page_loader_ready with full timeline."""
        from unittest.mock import MagicMock

        store = BootProfileStore(data_root=tmp_path)
        env_id = 'test-env-abc123'

        # Phase 1: at wire_services_done — store created, NOT persisted
        wiring_events = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 96.0},
            {'phase': 'wire_services_done', 't_ms_from_start': 18170.0, 'rss_mb': 112.0},
        ]
        assert store.load_history(env_id) == []

        # Phase 2: at page_loader_ready — late milestones added, NOW persist
        full_events = wiring_events + [
            {'phase': 'shell_loader_ready', 't_ms_from_start': 22000.0, 'rss_mb': 115.0},
            {'phase': 'page_loader_ready', 't_ms_from_start': 24500.0, 'rss_mb': 118.0},
            {'phase': 'splash_window_closing', 't_ms_from_start': 25200.0, 'rss_mb': 118.0},
        ]
        record = store.record_boot_session(
            environment_id=env_id,
            timeline_events=full_events,
            metadata={'persist_trigger': 'page_loader_ready'},
        )

        assert record['boot_duration_ms'] == 25200.0
        assert record['wiring_duration_ms'] == 18170.0
        assert 'page_loader_ready' in record['phases']
        assert 'splash_window_closing' in record['phases']
        assert record['metadata']['persist_trigger'] == 'page_loader_ready'

        history = store.load_history(env_id)
        assert len(history) == 1
        assert history[0]['boot_duration_ms'] == 25200.0

    def test_idempotent_persist(self, tmp_path: Path):
        """_persist_boot_profile is idempotent — second call is a no-op."""
        store = BootProfileStore(data_root=tmp_path)
        env_id = 'env-idem'
        events = _full_boot_timeline_events()

        store.record_boot_session(environment_id=env_id, timeline_events=events)
        store.record_boot_session(environment_id=env_id, timeline_events=events)

        history = store.load_history(env_id)
        assert len(history) == 2

    def test_persist_trigger_in_metadata(self, tmp_path: Path):
        """The persist_trigger field records which milestone triggered persistence."""
        store = BootProfileStore(data_root=tmp_path)

        store.record_boot_session(
            environment_id='env-page',
            timeline_events=_full_boot_timeline_events(),
            metadata={'persist_trigger': 'page_loader_ready'},
        )
        store.record_boot_session(
            environment_id='env-splash',
            timeline_events=_full_boot_timeline_events(),
            metadata={'persist_trigger': 'splash_window_closing'},
        )

        h_page = store.load_history('env-page')
        h_splash = store.load_history('env-splash')
        assert h_page[0]['metadata']['persist_trigger'] == 'page_loader_ready'
        assert h_splash[0]['metadata']['persist_trigger'] == 'splash_window_closing'

    def test_wiring_only_fallback_mcp(self, tmp_path: Path):
        """MCP-only sessions (no UI) persist at wire_services_done as fallback."""
        store = BootProfileStore(data_root=tmp_path)
        wiring_only = [
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0.0, 'rss_mb': 96.0},
            {'phase': 'wire_services_done', 't_ms_from_start': 18170.0, 'rss_mb': 112.0},
        ]
        record = store.record_boot_session(
            environment_id='mcp-env',
            timeline_events=wiring_only,
            metadata={'persist_trigger': 'wire_services_done_mcp_fallback'},
        )
        assert record['boot_duration_ms'] == 18170.0
        assert record['wiring_duration_ms'] == 18170.0
        assert record['metadata']['persist_trigger'] == 'wire_services_done_mcp_fallback'
