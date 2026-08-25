"""Tests for httpx/httpcore log noise suppression.

Verifies that:
1. suppress_noisy_http_loggers() sets the right loggers to WARNING
2. configure_logging() always suppresses even with pre-existing handlers
3. The auto-correction safety net re-applies suppression if levels reset
4. _NOISY_HTTP_LOGGERS covers all expected logger names
"""
from __future__ import annotations

import logging

import pytest


class TestSuppressNoisyHttpLoggers:
    """Direct tests for the suppress_noisy_http_loggers function."""

    def test_sets_httpx_to_warning(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        httpx_logger = logging.getLogger('httpx')
        httpx_logger.setLevel(logging.DEBUG)
        suppress_noisy_http_loggers()
        assert httpx_logger.level >= logging.WARNING

    def test_sets_httpcore_to_warning(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        httpcore_logger = logging.getLogger('httpcore')
        httpcore_logger.setLevel(logging.DEBUG)
        suppress_noisy_http_loggers()
        assert httpcore_logger.level >= logging.WARNING

    def test_sets_httpcore_children_to_warning(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        for child in ('httpcore.http11', 'httpcore.connection'):
            lg = logging.getLogger(child)
            lg.setLevel(logging.DEBUG)
        suppress_noisy_http_loggers()
        for child in ('httpcore.http11', 'httpcore.connection'):
            assert logging.getLogger(child).level >= logging.WARNING

    def test_sets_urllib3_to_warning(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.DEBUG)
        suppress_noisy_http_loggers()
        assert urllib3_logger.level >= logging.WARNING

    def test_idempotent(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        suppress_noisy_http_loggers()
        suppress_noisy_http_loggers()
        assert logging.getLogger('httpx').level >= logging.WARNING

    def test_does_not_touch_iabv_loggers(self):
        from iabv_v15.infra.logging import suppress_noisy_http_loggers
        iabv_logger = logging.getLogger('iabv_v15.services')
        iabv_logger.setLevel(logging.DEBUG)
        suppress_noisy_http_loggers()
        assert iabv_logger.level == logging.DEBUG


class TestConfigureLoggingSuppression:
    """Verify configure_logging always suppresses HTTP noise."""

    def test_suppresses_even_with_existing_handlers(self, tmp_path):
        from iabv_v15.infra.logging import configure_logging
        root = logging.getLogger()
        dummy_handler = logging.StreamHandler()
        root.addHandler(dummy_handler)
        httpx_logger = logging.getLogger('httpx')
        httpx_logger.setLevel(logging.DEBUG)
        try:
            configure_logging(str(tmp_path / 'logs'))
            assert httpx_logger.level >= logging.WARNING
        finally:
            root.removeHandler(dummy_handler)

    def test_suppresses_on_fresh_logger(self, tmp_path):
        from iabv_v15.infra.logging import configure_logging
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        for h in original_handlers:
            root.removeHandler(h)
        httpx_logger = logging.getLogger('httpx')
        httpx_logger.setLevel(logging.DEBUG)
        try:
            configure_logging(str(tmp_path / 'logs'))
            assert httpx_logger.level >= logging.WARNING
        finally:
            for h in list(root.handlers):
                root.removeHandler(h)
            for h in original_handlers:
                root.addHandler(h)


class TestNoisyLoggerList:
    """Verify the canonical list covers known noisy loggers."""

    def test_covers_httpx_and_httpcore(self):
        from iabv_v15.infra.logging import _NOISY_HTTP_LOGGERS
        assert 'httpx' in _NOISY_HTTP_LOGGERS
        assert 'httpcore' in _NOISY_HTTP_LOGGERS

    def test_covers_urllib3(self):
        from iabv_v15.infra.logging import _NOISY_HTTP_LOGGERS
        assert 'urllib3' in _NOISY_HTTP_LOGGERS


class TestAutoCorrectionSafetyNet:
    """Verify _correct_http_noise re-applies suppression as safety net."""

    def test_below_threshold_no_action(self):
        from iabv_v15.services.auto_correction_engine import _correct_http_noise
        result = _correct_http_noise(
            {'occurrences': 5, 'category': 'http_noise'},
            {},
        )
        assert result['status'] == 'no_action_needed'

    def test_above_threshold_already_suppressed(self):
        from iabv_v15.services.auto_correction_engine import _correct_http_noise
        logging.getLogger('httpx').setLevel(logging.WARNING)
        result = _correct_http_noise(
            {'occurrences': 50, 'category': 'http_noise'},
            {},
        )
        assert result['status'] == 'no_action_needed'
        assert 'already at WARNING' in result['detail']

    def test_above_threshold_resets_levels(self):
        from iabv_v15.services.auto_correction_engine import _correct_http_noise
        logging.getLogger('httpx').setLevel(logging.DEBUG)
        result = _correct_http_noise(
            {'occurrences': 50, 'category': 'http_noise'},
            {},
        )
        assert result['status'] == 'corrected'
        assert logging.getLogger('httpx').level >= logging.WARNING
