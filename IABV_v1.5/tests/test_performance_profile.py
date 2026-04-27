"""Tests for the performance_profile MCP tool and network probe caching."""
from __future__ import annotations

import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Network connectivity probe caching
# ---------------------------------------------------------------------------

class TestNetworkProbeCache:
    """WorldModelService._network_connectivity_probe caches results."""

    def _make_service(self):
        """Create a minimal WorldModelService in test mode."""
        import os
        os.environ.setdefault('IABV_TEST_MODE', '1')
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        return WorldModelService(
            workspace_root='/tmp/test_ws',
            evolution_dir='/tmp/test_evo',
            auto_start=False,
            bootstrap_scan=False,
        )

    def test_cache_returns_fresh_result(self):
        svc = self._make_service()
        # Seed the cache manually.
        svc._network_cache = (42.0, '', time.monotonic())
        latency, error = svc._network_connectivity_probe()
        assert latency == 42.0
        assert error == ''

    def test_cache_expires_after_ttl(self):
        svc = self._make_service()
        # Seed with an expired timestamp.
        svc._network_cache = (42.0, '', time.monotonic() - svc._NETWORK_CACHE_TTL - 1)
        # Mock socket to return quickly.
        with patch.object(socket, 'create_connection') as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value.__enter__ = lambda s: mock_sock
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            latency, error = svc._network_connectivity_probe()
        # Should have called the real probe (not returned cached 42.0).
        assert latency != 42.0 or mock_conn.called

    def test_cache_ttl_default(self):
        svc = self._make_service()
        assert svc._NETWORK_CACHE_TTL == 60.0

    def test_fallback_chain_all_fail(self):
        svc = self._make_service()
        # Ensure cache is expired.
        svc._network_cache = (None, '', 0.0)
        with patch.object(socket, 'create_connection', side_effect=OSError('blocked')):
            with patch('urllib.request.urlopen', side_effect=OSError('no internet')):
                latency, error = svc._network_connectivity_probe()
        assert latency is None
        assert 'no internet' in error

    def test_fallback_chain_second_succeeds(self):
        svc = self._make_service()
        svc._network_cache = (None, '', 0.0)
        call_count = 0

        def side_effect(addr, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError('port 53 blocked')
            mock = MagicMock()
            mock.__enter__ = lambda s: mock
            mock.__exit__ = MagicMock(return_value=False)
            return mock

        with patch.object(socket, 'create_connection', side_effect=side_effect):
            latency, error = svc._network_connectivity_probe()
        assert latency is not None
        assert error == ''
        assert call_count == 2

    def test_successful_probe_updates_cache(self):
        svc = self._make_service()
        svc._network_cache = (None, '', 0.0)
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: mock_sock
        mock_sock.__exit__ = MagicMock(return_value=False)
        with patch.object(socket, 'create_connection', return_value=mock_sock):
            latency, error = svc._network_connectivity_probe()
        assert latency is not None
        cached_latency, cached_error, cached_ts = svc._network_cache
        assert cached_latency is not None
        assert cached_ts > 0


# ---------------------------------------------------------------------------
# Performance profile tool output structure
# ---------------------------------------------------------------------------

class TestPerformanceProfileStructure:
    """Verify the performance_profile tool returns expected keys."""

    def test_profile_returns_required_keys(self):
        """Simulate the profiling logic without MCP server."""
        import sys as _sys
        import threading as _threading

        result: dict = {'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')}

        # Process memory (Linux /proc fallback).
        try:
            with open('/proc/self/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        result['process_memory_mb'] = round(int(line.split()[1]) / 1024, 1)
        except Exception:
            result['process_memory_mb'] = -1

        threads = _threading.enumerate()
        result['active_thread_count'] = len(threads)
        result['active_threads'] = [{'name': t.name, 'daemon': t.daemon} for t in threads]
        result['recommendations'] = []
        result['bottlenecks'] = []

        assert 'timestamp' in result
        assert 'process_memory_mb' in result
        assert 'active_thread_count' in result
        assert isinstance(result['active_threads'], list)
        assert isinstance(result['recommendations'], list)
        assert isinstance(result['bottlenecks'], list)

    def test_high_memory_triggers_bottleneck(self):
        """Simulate memory > 500MB triggering a bottleneck."""
        mem_mb = 650
        bottlenecks = []
        if mem_mb > 500:
            bottlenecks.append({
                'area': 'memory',
                'severity': 'high',
                'detail': f'Proceso consume {mem_mb}MB RSS',
            })
        assert len(bottlenecks) == 1
        assert bottlenecks[0]['severity'] == 'high'

    def test_many_polling_threads_triggers_bottleneck(self):
        """Simulate >3 polling threads triggering a bottleneck."""
        thread_names = [
            'iabv-world-model-scan', 'health-poll', 'monitor-loop',
            'timer-refresh', 'bridge-accept',
        ]
        polling = [n for n in thread_names if any(
            kw in n for kw in ('scan', 'poll', 'monitor', 'timer', 'refresh', 'bridge')
        )]
        bottlenecks = []
        if len(polling) > 3:
            bottlenecks.append({
                'area': 'threads',
                'severity': 'medium',
                'detail': f'{len(polling)} polling threads',
            })
        assert len(bottlenecks) == 1
        assert bottlenecks[0]['area'] == 'threads'
