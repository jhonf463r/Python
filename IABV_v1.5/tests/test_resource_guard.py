"""Tests for resource guard - preventive control for IABV's own expensive work."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.services.resource_guard import (
    ResourceDecision,
    ResourceGuard,
    ResourcePressure,
    get_resource_guard,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_snapshot(ram_used_pct: float = 50.0) -> MagicMock:
    """Create a mock resource snapshot."""
    snap = MagicMock()
    snap.ram_used_pct = ram_used_pct
    snap.ram_available_mb = 8000 - (ram_used_pct / 100 * 8000)
    snap.ram_total_mb = 8000
    return snap


# ---------------------------------------------------------------------------
# Pressure classification tests
# ---------------------------------------------------------------------------

class TestPressureClassification:
    def test_classify_low_pressure(self) -> None:
        """Verify LOW pressure classification (< 50%)."""
        guard = ResourceGuard()
        assert guard._classify_pressure(30.0) == ResourcePressure.LOW
        assert guard._classify_pressure(49.9) == ResourcePressure.LOW

    def test_classify_moderate_pressure(self) -> None:
        """Verify MODERATE pressure classification (50-75%)."""
        guard = ResourceGuard()
        assert guard._classify_pressure(50.0) == ResourcePressure.MODERATE
        assert guard._classify_pressure(60.0) == ResourcePressure.MODERATE
        assert guard._classify_pressure(74.9) == ResourcePressure.MODERATE

    def test_classify_high_pressure(self) -> None:
        """Verify HIGH pressure classification (75-90%)."""
        guard = ResourceGuard()
        assert guard._classify_pressure(75.0) == ResourcePressure.HIGH
        assert guard._classify_pressure(80.0) == ResourcePressure.HIGH
        assert guard._classify_pressure(89.9) == ResourcePressure.HIGH

    def test_classify_critical_pressure(self) -> None:
        """Verify CRITICAL pressure classification (> 90%)."""
        guard = ResourceGuard()
        assert guard._classify_pressure(90.0) == ResourcePressure.CRITICAL
        assert guard._classify_pressure(95.0) == ResourcePressure.CRITICAL
        assert guard._classify_pressure(100.0) == ResourcePressure.CRITICAL


# ---------------------------------------------------------------------------
# LOW pressure behavior tests
# ---------------------------------------------------------------------------

class TestLowPressureBehavior:
    def test_low_allows_normal_optional_work(self) -> None:
        """Verify LOW pressure allows normal optional work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=30.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=100,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is True
            assert decision.pressure == ResourcePressure.LOW
            assert "normal" in decision.reason.lower()

    def test_low_allows_expensive_optional_work(self) -> None:
        """Verify LOW pressure allows expensive optional work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=30.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=1000,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is True


# ---------------------------------------------------------------------------
# MODERATE pressure behavior tests
# ---------------------------------------------------------------------------

class TestModeratePressureBehavior:
    def test_moderate_reduces_heavy_optional_work(self) -> None:
        """Verify MODERATE pressure suppresses heavy optional work (> 500MB)."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=60.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=600,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is False
            assert decision.pressure == ResourcePressure.MODERATE
            assert "suppressed" in decision.reason.lower()

    def test_moderate_allows_lightweight_optional_work(self) -> None:
        """Verify MODERATE pressure allows lightweight optional work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=60.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=100,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is True

    def test_moderate_allows_goal_required_work(self) -> None:
        """Verify MODERATE pressure allows goal-required work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=60.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=1000,
                goal_required=True,
                essential=False,
            )
            
            assert decision.allowed is True
            assert "goal_required" in decision.reason.lower()


# ---------------------------------------------------------------------------
# HIGH pressure behavior tests
# ---------------------------------------------------------------------------

class TestHighPressureBehavior:
    def test_high_suppresses_expensive_optional_work(self) -> None:
        """Verify HIGH pressure suppresses expensive optional work (> 100MB)."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=80.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=200,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is False
            assert decision.pressure == ResourcePressure.HIGH
            assert "suppressed" in decision.reason.lower()

    def test_high_allows_lightweight_optional_work(self) -> None:
        """Verify HIGH pressure allows lightweight optional work (< 100MB)."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=80.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=50,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is True
            assert "lightweight" in decision.reason.lower()

    def test_high_allows_goal_required_work(self) -> None:
        """Verify HIGH pressure allows goal-required work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=80.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=500,
                goal_required=True,
                essential=False,
            )
            
            assert decision.allowed is True


# ---------------------------------------------------------------------------
# CRITICAL pressure behavior tests
# ---------------------------------------------------------------------------

class TestCriticalPressureBehavior:
    def test_critical_suppresses_all_optional_work(self) -> None:
        """Verify CRITICAL pressure suppresses all optional work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=95.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=10,
                goal_required=False,
                essential=False,
            )
            
            assert decision.allowed is False
            assert decision.pressure == ResourcePressure.CRITICAL
            assert "suppressed" in decision.reason.lower()

    def test_critical_allows_essential_work(self) -> None:
        """Verify CRITICAL pressure allows essential work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=95.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=1000,
                goal_required=False,
                essential=True,
            )
            
            assert decision.allowed is True
            assert "essential" in decision.reason.lower()

    def test_critical_checks_ram_for_goal_required(self) -> None:
        """Verify CRITICAL pressure checks RAM availability for goal-required work."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=95.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=10000,  # More than available
                goal_required=True,
                essential=False,
            )
            
            assert decision.allowed is False
            assert "insufficient_ram" in decision.reason.lower()

    def test_critical_allows_goal_required_with_sufficient_ram(self) -> None:
        """Verify CRITICAL pressure allows goal-required work with sufficient RAM."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=95.0)
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=100,  # Less than available
                goal_required=True,
                essential=False,
            )
            
            assert decision.allowed is True


# ---------------------------------------------------------------------------
# Historical action resource guard tests
# ---------------------------------------------------------------------------

class TestHistoricalActionResourceGuard:
    def test_historical_success_alone_does_not_override_pressure(self) -> None:
        """Verify historical success alone does not override resource pressure."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=95.0)
            
            # Simulate an action that historically succeeded
            decision = guard.check_action_allowed(
                action="historical_action",
                estimated_ram_mb=200,
                goal_required=False,  # Not currently goal-required
                essential=False,
            )
            
            # Should still be blocked by CRITICAL pressure
            assert decision.allowed is False
            assert decision.pressure == ResourcePressure.CRITICAL


# ---------------------------------------------------------------------------
# Cache and performance tests
# ---------------------------------------------------------------------------

class TestCacheAndPerformance:
    def test_snapshot_cache_used_within_ttl(self) -> None:
        """Verify snapshot cache is used within TTL."""
        import time
        
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=50.0)
            
            # First call
            guard.check_action_allowed(action="test1", estimated_ram_mb=100)
            assert mock_snap.call_count == 1
            
            # Second call within TTL (should use cache)
            guard.check_action_allowed(action="test2", estimated_ram_mb=100)
            assert mock_snap.call_count == 1  # No new call

    def test_snapshot_cache_expired_after_ttl(self) -> None:
        """Verify snapshot cache expires after TTL."""
        import time
        
        guard = ResourceGuard()
        guard._cache_ttl_seconds = 0.1  # Short TTL for testing
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=50.0)
            
            # First call
            guard.check_action_allowed(action="test1", estimated_ram_mb=100)
            assert mock_snap.call_count == 1
            
            # Wait for cache to expire
            time.sleep(0.15)
            
            # Second call after TTL (should refresh cache)
            guard.check_action_allowed(action="test2", estimated_ram_mb=100)
            assert mock_snap.call_count == 2  # New call

    def test_fail_safe_on_snapshot_failure(self) -> None:
        """Verify fail-safe allows action when snapshot fails."""
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.side_effect = Exception("Snapshot failed")
            
            decision = guard.check_action_allowed(
                action="test_action",
                estimated_ram_mb=100,
                goal_required=False,
                essential=False,
            )
            
            # Should allow action (fail-safe)
            assert decision.allowed is True
            assert "snapshot_failed" in decision.reason.lower()


# ---------------------------------------------------------------------------
# Global instance tests
# ---------------------------------------------------------------------------

class TestGlobalInstance:
    def test_get_resource_guard_returns_singleton(self) -> None:
        """Verify get_resource_guard returns singleton instance."""
        guard1 = get_resource_guard()
        guard2 = get_resource_guard()
        
        assert guard1 is guard2

    def test_get_current_pressure(self) -> None:
        """Verify get_current_pressure returns pressure without decision logic."""
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=80.0)
            
            guard = get_resource_guard()
            pressure = guard.get_current_pressure()
            
            assert pressure == ResourcePressure.HIGH


# ---------------------------------------------------------------------------
# Fast path protection tests
# ---------------------------------------------------------------------------

class TestFastPathProtection:
    def test_fast_chat_remains_lightweight(self) -> None:
        """Verify fast chat path is not slowed by resource checks."""
        import time
        
        guard = ResourceGuard()
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=30.0)
            
            start = time.perf_counter()
            for _ in range(10):
                guard.check_action_allowed(
                    action="fast_chat",
                    estimated_ram_mb=10,
                    goal_required=False,
                    essential=False,
                )
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            # Should complete quickly (< 50ms for 10 checks)
            assert elapsed_ms < 50.0


# ---------------------------------------------------------------------------
# No duplicate governor tests
# ---------------------------------------------------------------------------

class TestNoDuplicateGovernor:
    def test_guard_reuses_existing_snapshot_infrastructure(self) -> None:
        """Verify guard reuses existing ResourceSnapshot infrastructure."""
        guard = ResourceGuard()
        
        # The guard should use take_resource_snapshot from intelligent_resource_manager
        # This test verifies the import path is correct
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = _make_snapshot(ram_used_pct=30.0)
            
            decision = guard.check_action_allowed(
                action="test",
                estimated_ram_mb=100,
            )
            
            # Should have called the existing snapshot function
            assert mock_snap.called
            assert decision.pressure == ResourcePressure.LOW
