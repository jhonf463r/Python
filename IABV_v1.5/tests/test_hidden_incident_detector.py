from __future__ import annotations

from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector
from iabv_v15.services.evolution.runtime_signal_collector import RuntimeSignalCollector


def test_hidden_incident_detector_flags_capture_starvation() -> None:
    detector = HiddenIncidentDetector()
    collector = RuntimeSignalCollector()
    snapshot = {
        'status': 'capturing',
        'heartbeat_count': 3,
        'visible_step_count': 0,
        'screenshot_count': 0,
        'seconds_since_session_start': 8.2,
        'seconds_since_last_visible_progress': 8.2,
        'queue_depth': 2,
        'last_active_url': 'https://example.com/dashboard',
        'recent_urls': ['https://example.com/dashboard'],
    }

    signals = collector.capture_tick(episode_id='episode-1', site_id='generic_web', runtime_snapshot=snapshot)
    incidents = detector.detect_from_snapshot(
        episode_id='episode-1',
        site_id='generic_web',
        runtime_snapshot=snapshot,
        signals=signals,
        existing_incidents=[],
    )

    assert any(item.incident_kind == 'capture_starvation' for item in incidents)


def test_hidden_incident_detector_flags_navigation_stall() -> None:
    detector = HiddenIncidentDetector()
    collector = RuntimeSignalCollector()
    snapshot = {
        'status': 'capturing',
        'page_count': 3,
        'observed_page_count': 3,
        'active_navigation_stall_seconds': 11.4,
        'last_active_url': 'https://www.google.com/search?q=mercadolibre',
        'recent_urls': ['https://www.google.com', 'https://www.google.com/search?q=mercadolibre'],
        'visible_step_count': 2,
        'screenshot_count': 1,
    }

    signals = collector.capture_tick(episode_id='episode-2', site_id='generic_web', runtime_snapshot=snapshot)
    incidents = detector.detect_from_snapshot(
        episode_id='episode-2',
        site_id='generic_web',
        runtime_snapshot=snapshot,
        signals=signals,
        existing_incidents=[],
    )

    assert any(item.incident_kind == 'navigation_stall' for item in incidents)
