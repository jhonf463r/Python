"""Tests for WorldModelService cadence changes (PR B).

Verifies:
1. Default intervals are 45s/180s (relaxed from 18s/120s)
2. Minimum scan interval floor of 8s is respected
3. scan_stats property exposes counters correctly
4. scan_now increments counters
"""
from __future__ import annotations

import pytest


class TestWorldModelCadenceDefaults:
    """Verify relaxed default intervals."""

    def test_default_scan_interval_is_45s(self):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        assert WorldModelService._DEFAULT_SCAN_INTERVAL == 45.0

    def test_default_full_scan_interval_is_180s(self):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        assert WorldModelService._DEFAULT_FULL_SCAN_INTERVAL == 180.0

    def test_min_scan_interval_is_8s(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
            scan_interval_seconds=1.0,
        )
        assert svc.scan_interval_seconds == 8.0


class TestScanStats:
    """Verify scan_stats counter property."""

    def test_initial_stats_zero(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
        )
        stats = svc.scan_stats
        assert stats['scan_count'] == 0
        assert stats['scan_count_full'] == 0
        assert stats['scan_interval_s'] == 45.0
        assert stats['full_scan_interval_s'] == 180.0

    def test_scan_now_increments_light(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
        )
        svc.scan_now(reason='test', full=False)
        stats = svc.scan_stats
        assert stats['scan_count'] == 1
        assert stats['scan_count_full'] == 0

    def test_scan_now_increments_full(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
        )
        svc.scan_now(reason='test', full=True)
        stats = svc.scan_stats
        assert stats['scan_count'] == 1
        assert stats['scan_count_full'] == 1

    def test_multiple_scans_accumulate(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
        )
        svc.scan_now(reason='t1', full=False)
        svc.scan_now(reason='t2', full=False)
        svc.scan_now(reason='t3', full=True)
        stats = svc.scan_stats
        assert stats['scan_count'] == 3
        assert stats['scan_count_full'] == 1

    def test_last_scan_ago_populated(self, tmp_path):
        from iabv_v15.services.evolution.world_model_service import WorldModelService
        svc = WorldModelService(
            workspace_root=str(tmp_path),
            evolution_dir=str(tmp_path / 'evo'),
            auto_start=False,
            bootstrap_scan=False,
        )
        svc.scan_now(reason='test')
        stats = svc.scan_stats
        assert stats['last_scan_ago_s'] is not None
        assert stats['last_scan_ago_s'] >= 0.0
