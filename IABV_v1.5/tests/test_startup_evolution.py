"""Test startup evolution cycle and brain optimization."""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from uuid import uuid4

import pytest

from iabv_v15.bootstrap import AppBootstrap


def _make_bootstrap() -> tuple[AppBootstrap, Path]:
    workspace = Path.cwd() / 'data' / f'test_startup_evo_{uuid4().hex}'
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap = AppBootstrap(str(workspace))
    return bootstrap, workspace


class TestScheduleStartupEvolution:

    def test_no_crash_when_services_missing(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            bootstrap.metacognition_evolution = None
            bootstrap.api_key_discovery_service = None
            bootstrap._schedule_startup_evolution()
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_spawns_thread(self) -> None:
        import threading
        bootstrap, workspace = _make_bootstrap()
        try:
            mock_metacog = MagicMock()
            mock_metacog.run_evolution_cycle.return_value = {
                'findings_count': 2,
                'actions_taken': ['rotated provider X'],
            }
            bootstrap.metacognition_evolution = mock_metacog
            bootstrap._schedule_startup_evolution()
            names = [t.name for t in threading.enumerate()]
            assert 'startup-evolution' in names
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


class TestAutoOptimizeBrain:

    def test_no_crash_without_selector(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            bootstrap.adaptive_model_selector = None
            bootstrap._auto_optimize_brain()
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_benchmarks_available_providers(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            mock_selector = MagicMock()
            mock_selector.select_best_provider.return_value = {
                'provider_id': 'groq',
                'reason': 'lowest_latency',
            }
            bootstrap.adaptive_model_selector = mock_selector

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response

            with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
                with patch('httpx.Client', return_value=mock_client):
                    bootstrap._auto_optimize_brain()

            assert mock_selector.record_result.called
            call_kwargs = mock_selector.record_result.call_args[1]
            assert call_kwargs['provider_id'] == 'groq'
            assert call_kwargs['task_type'] == 'reasoning'
            assert call_kwargs['success'] is True
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_records_failure_on_exception(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            mock_selector = MagicMock()
            mock_selector.select_best_provider.return_value = {
                'provider_id': 'ollama_local',
                'reason': 'all_failed',
            }
            bootstrap.adaptive_model_selector = mock_selector

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = Exception('network error')

            with patch.dict('os.environ', {'GROQ_API_KEY': 'k1'}):
                with patch('httpx.Client', return_value=mock_client):
                    bootstrap._auto_optimize_brain()

            assert mock_selector.record_result.called
            call_kwargs = mock_selector.record_result.call_args[1]
            assert call_kwargs['success'] is False
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_skips_unconfigured_providers(self) -> None:
        bootstrap, workspace = _make_bootstrap()
        try:
            mock_selector = MagicMock()
            mock_selector.select_best_provider.return_value = {
                'provider_id': 'ollama_local',
                'reason': 'no_keys',
            }
            bootstrap.adaptive_model_selector = mock_selector

            with patch.dict('os.environ', {}, clear=True):
                bootstrap._auto_optimize_brain()

            assert not mock_selector.record_result.called
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
