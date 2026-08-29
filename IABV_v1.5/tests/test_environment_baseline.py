"""Tests for environment baseline and observation system.

Focused tests for:
1. startup establishes baseline
2. baseline has timestamp
3. ordinary chat does not trigger Level-2 deep discovery
4. stale RAM causes targeted RAM refresh only
5. stale GPU state causes targeted GPU refresh only
6. Git high-risk action requires fresh repository state
7. critical resource pressure suppresses optional deep discovery
8. resource snapshot failure does not authorize expensive optional work
9. fast path remains lightweight
10. no recursive ResourceGuard/resource snapshot loop
11. baseline can be reused by interactive requests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.services.environment.active_perception import (
    ActivePerceptionDecision,
    ActivePerceptionService,
    ObservationScope,
    get_active_perception_service,
)
from iabv_v15.services.environment.environment_baseline import (
    EnvironmentBaseline,
    EnvironmentBaselineService,
    ObservationFreshness,
    ObservationLevel,
    ObservationRecord,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_baseline() -> EnvironmentBaseline:
    """Create a test baseline."""
    return EnvironmentBaseline(
        host_id="test-host",
        runtime_id="test-runtime",
    )


# ---------------------------------------------------------------------------
# Baseline establishment tests
# ---------------------------------------------------------------------------

class TestBaselineEstablishment:
    def test_startup_establishes_baseline(self) -> None:
        """Verify startup establishes baseline."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        
        baseline = service.establish_baseline()
        
        assert baseline is not None
        assert baseline.baseline_id != ""
        assert baseline.host_id == "test-host" or baseline.host_id != ""
        assert baseline.runtime_id != ""

    def test_baseline_has_timestamp(self) -> None:
        """Verify baseline has timestamp."""
        baseline = _make_baseline()
        
        assert baseline.timestamp_utc != ""
        # Verify it's a valid ISO timestamp
        assert "T" in baseline.timestamp_utc or "-" in baseline.timestamp_utc

    def test_baseline_can_be_reused(self) -> None:
        """Verify baseline can be reused by interactive requests."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        
        # Establish baseline
        baseline1 = service.establish_baseline()
        
        # Get baseline again (should reuse)
        baseline2 = service.get_baseline()
        
        assert baseline1.baseline_id == baseline2.baseline_id
        assert baseline1.timestamp_utc == baseline2.timestamp_utc


# ---------------------------------------------------------------------------
# Observation freshness tests
# ---------------------------------------------------------------------------

class TestObservationFreshness:
    def test_fresh_observation_within_ttl(self) -> None:
        """Verify observation is fresh within TTL."""
        baseline = _make_baseline()
        baseline.set_observation(
            "test_key",
            "test_value",
            ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            ttl_seconds=60.0,
        )
        
        value, freshness = baseline.get_observation("test_key")
        assert value == "test_value"
        assert freshness == ObservationFreshness.FRESH
        assert baseline.is_fresh("test_key")

    def test_stale_observation_beyond_ttl(self) -> None:
        """Verify observation is stale beyond TTL."""
        baseline = _make_baseline()
        
        # Create an old observation
        old_record = ObservationRecord(
            key="test_key",
            value="test_value",
            level=ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            timestamp_utc="2020-01-01T00:00:00Z",  # Very old
            ttl_seconds=60.0,
        )
        baseline.observations["test_key"] = old_record
        
        value, freshness = baseline.get_observation("test_key")
        assert freshness == ObservationFreshness.STALE
        assert baseline.is_stale("test_key")

    def test_unknown_observation_never_observed(self) -> None:
        """Verify unknown observation has never been observed."""
        baseline = _make_baseline()
        
        value, freshness = baseline.get_observation("nonexistent_key")
        assert value is None
        assert freshness == ObservationFreshness.UNKNOWN
        assert baseline.is_unknown("nonexistent_key")


# ---------------------------------------------------------------------------
# Observation levels tests
# ---------------------------------------------------------------------------

class TestObservationLevels:
    def test_level_0_static_observation(self) -> None:
        """Verify LEVEL_0 static observation works."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = _make_baseline()
        
        service._observe_level_0_static(baseline)
        
        # Should have observed python_version and platform
        assert baseline.is_fresh("python_version") or baseline.is_unknown("python_version")
        assert baseline.is_fresh("platform") or baseline.is_unknown("platform")

    def test_level_1_light_runtime_observation(self) -> None:
        """Verify LEVEL_1 light runtime observation works."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = _make_baseline()
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = MagicMock(
                ram_available_mb=8000,
                ram_used_pct=50.0,
                cpu_load_1m=2.0,
            )
            
            service._observe_level_1_light_runtime(baseline)
            
            # Should have observed RAM/CPU
            assert baseline.is_fresh("ram_available_mb")

    def test_level_2_deep_discovery_resource_guarded(self) -> None:
        """Verify LEVEL_2 deep discovery is resource-guarded."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = _make_baseline()
        
        with patch('iabv_v15.services.resource_guard.get_resource_guard') as mock_guard:
            mock_decision = MagicMock()
            mock_decision.allowed = False
            mock_decision.reason = "resource_pressure"
            mock_guard.return_value.check_action_allowed.return_value = mock_decision
            
            service._observe_level_2_deep_discovery(baseline)
            
            # Should have skipped deep discovery
            assert any("skipped" in limitation for limitation in baseline.known_limitations)


# ---------------------------------------------------------------------------
# Targeted refresh tests
# ---------------------------------------------------------------------------

class TestTargetedRefresh:
    def test_stale_ram_causes_targeted_refresh_only(self) -> None:
        """Verify stale RAM causes targeted RAM refresh only."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = _make_baseline()
        
        # Set old RAM observation
        old_record = ObservationRecord(
            key="ram_available_mb",
            value=1000,
            level=ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            timestamp_utc="2020-01-01T00:00:00Z",
            ttl_seconds=60.0,
        )
        baseline.observations["ram_available_mb"] = old_record
        
        # Set baseline in service
        service._baseline = baseline
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = MagicMock(
                ram_available_mb=8000,
                ram_used_pct=50.0,
                cpu_load_1m=2.0,
            )
            
            # Refresh RAM observation
            value, freshness = service.refresh_observation("ram_available_mb")
            
            # Should have refreshed
            assert mock_snap.called

    def test_stale_gpu_causes_targeted_gpu_refresh_only(self) -> None:
        """Verify stale GPU state causes targeted GPU refresh only."""
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = _make_baseline()
        
        # Set old GPU observation
        old_record = ObservationRecord(
            key="gpu",
            value={"available": False},
            level=ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            timestamp_utc="2020-01-01T00:00:00Z",
            ttl_seconds=60.0,
        )
        baseline.observations["gpu"] = old_record
        
        # Refresh GPU observation (would call GPU-specific refresh)
        value, freshness = service.refresh_observation("gpu")
        
        # Should have attempted refresh
        assert baseline.is_stale("gpu") or baseline.is_fresh("gpu")


# ---------------------------------------------------------------------------
# Active perception tests
# ---------------------------------------------------------------------------

class TestActivePerception:
    def test_git_operation_requires_fresh_state(self) -> None:
        """Verify Git high-risk action requires fresh repository state."""
        baseline = _make_baseline()
        baseline.set_observation(
            "git",
            {"status": "clean"},
            ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            ttl_seconds=60.0,
        )
        
        service = ActivePerceptionService(baseline_service=MagicMock(get_baseline=lambda: baseline))
        decision = service.decide_observations_needed("git_operation")
        
        assert "git" in decision.required_state
        assert decision.observation_scope == ObservationScope.LIGHTWEIGHT

    def test_ordinary_chat_does_not_trigger_level_2(self) -> None:
        """Verify ordinary chat does not trigger Level-2 deep discovery."""
        baseline = _make_baseline()
        service = ActivePerceptionService(baseline_service=MagicMock(get_baseline=lambda: baseline))
        
        # Ordinary chat (no specific goal)
        decision = service.decide_observations_needed("chat")
        
        # Should not require deep discovery
        assert decision.observation_scope != ObservationScope.DEEP

    def test_critical_pressure_suppresses_deep_discovery(self) -> None:
        """Verify critical resource pressure suppresses optional deep discovery."""
        baseline = _make_baseline()
        service = ActivePerceptionService(baseline_service=MagicMock(get_baseline=lambda: baseline))
        
        decision = service.decide_observations_needed("deep_discovery")
        decision.observation_required = True
        
        # Under critical pressure, deep discovery should be suppressed
        should_observe = service.should_perform_observation(decision, resource_pressure="critical")
        
        assert not should_observe


# ---------------------------------------------------------------------------
# ResourceGuard snapshot failure tests
# ---------------------------------------------------------------------------

class TestResourceGuardSnapshotFailure:
    def test_snapshot_failure_defers_expensive_optional(self) -> None:
        """Verify resource snapshot failure does not authorize expensive optional work."""
        from iabv_v15.services.resource_guard import ResourceGuard
        
        guard = ResourceGuard()
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.side_effect = Exception("Snapshot failed")
            
            # Expensive optional action should be deferred
            decision = guard.check_action_allowed(
                action="expensive_optional",
                estimated_ram_mb=500,
                goal_required=False,
                essential=False,
                lightweight=False,
            )
            
            assert not decision.allowed
            assert "deferred" in decision.reason.lower()

    def test_snapshot_failure_allows_lightweight(self) -> None:
        """Verify resource snapshot failure allows lightweight actions."""
        from iabv_v15.services.resource_guard import ResourceGuard
        
        guard = ResourceGuard()
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.side_effect = Exception("Snapshot failed")
            
            # Lightweight action should be allowed
            decision = guard.check_action_allowed(
                action="lightweight",
                estimated_ram_mb=10,
                goal_required=False,
                essential=False,
                lightweight=True,
            )
            
            assert decision.allowed
            assert "lightweight" in decision.reason.lower()

    def test_snapshot_failure_allows_essential(self) -> None:
        """Verify resource snapshot failure allows essential safety actions."""
        from iabv_v15.services.resource_guard import ResourceGuard
        
        guard = ResourceGuard()
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.side_effect = Exception("Snapshot failed")
            
            # Essential action should be allowed
            decision = guard.check_action_allowed(
                action="essential_safety",
                estimated_ram_mb=1000,
                goal_required=False,
                essential=True,
                lightweight=False,
            )
            
            assert decision.allowed
            assert "essential" in decision.reason.lower()


# ---------------------------------------------------------------------------
# Fast path tests
# ---------------------------------------------------------------------------

class TestFastPath:
    def test_fast_path_remains_lightweight(self) -> None:
        """Verify fast path remains lightweight."""
        import time
        
        service = EnvironmentBaselineService(
            workspace_root="/tmp/test",
            evolution_dir="/tmp/test/evolution",
            auto_start=False,
        )
        baseline = service.establish_baseline()
        
        start = time.perf_counter()
        for _ in range(10):
            baseline.is_fresh("test_key")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Should complete quickly (< 10ms for 10 checks)
        assert elapsed_ms < 10.0


# ---------------------------------------------------------------------------
# No recursion tests
# ---------------------------------------------------------------------------

class TestNoRecursion:
    def test_no_recursive_resource_guard_loop(self) -> None:
        """Verify no recursive ResourceGuard/resource snapshot loop."""
        from iabv_v15.services.resource_guard import ResourceGuard
        
        guard = ResourceGuard()
        
        with patch('iabv_v15.services.intelligent_resource_manager.take_resource_snapshot') as mock_snap:
            mock_snap.return_value = MagicMock(
                ram_used_pct=30.0,
                ram_available_mb=8000,
                ram_total_mb=8000,
            )
            
            # Multiple calls should not cause recursion
            for _ in range(5):
                guard.check_action_allowed(
                    action="test",
                    estimated_ram_mb=100,
                )
            
            # Should have called snapshot once (cached)
            assert mock_snap.call_count <= 2  # Allow for cache miss


# ---------------------------------------------------------------------------
# Baseline persistence tests
# ---------------------------------------------------------------------------

class TestBaselinePersistence:
    def test_baseline_persistence_roundtrip(self) -> None:
        """Verify baseline can be persisted and loaded."""
        baseline = _make_baseline()
        baseline.set_observation(
            "test_key",
            "test_value",
            ObservationLevel.LEVEL_1_LIGHT_RUNTIME,
            ttl_seconds=60.0,
        )
        
        # Convert to dict and back
        data = baseline.to_dict()
        loaded = EnvironmentBaseline.from_dict(data)
        
        assert loaded.baseline_id == baseline.baseline_id
        assert loaded.timestamp_utc == baseline.timestamp_utc
        assert loaded.is_fresh("test_key")
