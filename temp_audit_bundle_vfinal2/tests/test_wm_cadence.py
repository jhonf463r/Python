"""Tests for WorldModelService cadence changes (PR B).

Verifies:
1. Default intervals are 45s/180s (relaxed from 18s/120s)
2. Minimum scan interval floor of 8s is respected
3. scan_stats property exposes counters correctly
4. scan_now increments counters
5. measure_wm_cadence.ps1 has no PS 5.1-incompatible syntax
"""
from __future__ import annotations

import re
from pathlib import Path

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


class TestHarnessPS51Compat:
    """Verify measure_wm_cadence.ps1 is free of PS 5.1 parser pitfalls."""

    _SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'measure_wm_cadence.ps1'

    def _read_script(self) -> str:
        assert self._SCRIPT.exists(), f'Harness script not found: {self._SCRIPT}'
        return self._SCRIPT.read_text(encoding='utf-8')

    def test_no_dollar_brace_interpolation(self):
        """${var} inside double-quoted strings breaks PS 5.1 parser."""
        text = self._read_script()
        # Match ${...} but not inside single-quoted strings or comments
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('<#'):
                continue
            # Skip single-quoted strings entirely (they don't interpolate)
            if '${' in line and not line.strip().startswith("'"):
                assert False, f'Line {i} uses ${{...}} interpolation (fragile in PS 5.1): {line.strip()}'

    def test_no_non_ascii_characters(self):
        """Em-dashes and other non-ASCII in .ps1 break PS 5.1 without BOM."""
        text = self._read_script()
        for i, line in enumerate(text.splitlines(), 1):
            for ch in line:
                assert ord(ch) < 128, (
                    f'Line {i} has non-ASCII char U+{ord(ch):04X} ({ch!r}): {line.strip()}'
                )

    def test_no_dotted_quoted_property_access(self):
        """Patterns like .snapshots.'120s'.scan_stats can confuse PS 5.1 parser."""
        text = self._read_script()
        pattern = re.compile(r"\.\w+\.'[^']+'\.")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            match = pattern.search(line)
            assert match is None, (
                f"Line {i} has dotted-quoted property chain (PS 5.1 fragile): {match.group()}"
            )
