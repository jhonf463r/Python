from __future__ import annotations

from iabv_v15.domain.models import NetworkExchange
from iabv_v15.services.capture.browser_teach_session_service import BRIDGE_INSTALL_EXPR, BrowserTeachSessionService


def test_browser_teach_session_service_limits_event_screenshots_to_last_two() -> None:
    service = BrowserTeachSessionService.__new__(BrowserTeachSessionService)
    events = [
        {'type': 'click'},
        {'type': 'scroll'},
        {'type': 'change'},
        {'type': 'focus'},
        {'type': 'keydown'},
        {'type': 'submit'},
    ]

    indexes = service._select_screenshot_event_indexes(events)

    assert indexes == {3, 5}


def test_browser_teach_session_service_uses_smart_api_capture_sampling() -> None:
    service = BrowserTeachSessionService.__new__(BrowserTeachSessionService)
    service._api_seen_count = 0
    service._api_saved_count = 0
    service._api_dropped_count = 0
    service._completed_network = []
    service._saved_network_exchange_ids = set()
    service._last_network_by_endpoint = {}
    service._network_seen_by_endpoint = {}

    for index in range(5):
        service._consider_network_exchange(
            NetworkExchange(
                episode_id='episode',
                url='https://example.com/api/session',
                method='GET',
                status_code=200,
            ),
            latency_ms=120.0,
        )

    prepared = service._prepare_network_exchanges_for_persist()

    assert service._api_seen_count == 5
    assert service._api_saved_count == 3
    assert service._api_dropped_count == 3
    assert len(prepared) == 3


def test_browser_teach_session_service_prefers_controller_live_page() -> None:
    class _Controller:
        def __init__(self, page):
            self.page = page

    live_page = object()
    service = BrowserTeachSessionService.__new__(BrowserTeachSessionService)
    service.controller = _Controller(live_page)
    service.page = None

    assert service._current_page() is live_page
    assert service.page is live_page


def test_browser_teach_session_service_reads_binary_request_body_without_crashing() -> None:
    class _BinaryRequest:
        @property
        def post_data(self):
            raise UnicodeDecodeError('utf-8', b'\x8b', 0, 1, 'invalid start byte')

        def post_data_buffer(self):
            return b'\x8bPNG'

    service = BrowserTeachSessionService.__new__(BrowserTeachSessionService)

    body = service._read_request_body(_BinaryRequest())

    assert body is not None
    assert '\ufffdPNG' in body


def test_browser_teach_session_service_buffers_high_frequency_input_events() -> None:
    assert 'document.addEventListener("input"' in BRIDGE_INSTALL_EXPR
    assert 'bridge_buffered' in BRIDGE_INSTALL_EXPR
    assert 'document.addEventListener("keydown"' in BRIDGE_INSTALL_EXPR


def test_browser_teach_session_service_captures_submit_keys_for_screenshots() -> None:
    service = BrowserTeachSessionService.__new__(BrowserTeachSessionService)

    assert service._should_capture_screenshot('keydown', {'key': 'Enter'}) is True
    assert service._should_capture_screenshot('keydown', {'key': 'Tab'}) is True
    assert service._should_capture_screenshot('keydown', {'key': 'a'}) is False
