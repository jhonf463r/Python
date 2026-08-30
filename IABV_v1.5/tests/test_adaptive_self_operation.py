"""Focused behavioral tests for adaptive self-operation.

Tests cover:
A. INITIAL DISCOVERY: baseline establishment, deferral, resume
B. RESOURCE CONTROL: pressure-based gating, cost measurement
C. REFLECTION: evidence reuse, quoted terms, observe-now
D. MODEL SELECTION: goal/capability/resources, local vs remote
E. LEARNING: experience persistence, adaptive protocol
F. REGRESSION: lightweight chat, no duplicates, security constraints

Uses mocks where necessary to avoid real system calls.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.services.adaptive.self_discovery_baseline import (
    BaselineStatus,
    DiscoveryLevel,
    HostBaseline,
    OllamaBaseline,
    ResourceState,
    RuntimeBaseline,
    SelfDiscoveryBaseline,
    build_host_baseline,
    build_ollama_baseline,
    build_runtime_baseline,
)
from iabv_v15.services.adaptive.self_discovery_service import (
    DiscoveryResult,
    SelfDiscoveryService,
)
from iabv_v15.services.adaptive.resource_aware_controller import (
    OperationCost,
    OperationCostEstimate,
    ResourceCheck,
    ResourcePressure,
    ResourceState as ControllerResourceState,
    ResourceAwareController,
)
from iabv_v15.services.adaptive.cost_measurement import (
    CostMeasurementService,
    OperationCostRecord,
    ResourceMeasurement,
)
from iabv_v15.services.adaptive.resource_aware_model_selector import (
    Capability,
    ModelCapability,
    ModelSelectionCriteria,
    ModelSelectionDecision,
    ProviderKind,
    ResourceAwareModelSelector,
)
from iabv_v15.services.adaptive.experience_storage import (
    AdaptiveRuleUpdate,
    ExecutionExperience,
    ExperienceStorageService,
    ModelSelectionExperience,
)
from iabv_v15.services.adaptive.adaptive_protocol import (
    AdaptiveProtocolService,
    AdaptiveRule,
    ProtocolRecommendation,
)
from iabv_v15.services.adaptive.reflection_routing import (
    EvidenceMetadata,
    EvidenceState,
    EvidenceSufficiency,
    ReflectionDecision,
    ReflectionRoute,
    ReflectionRoutingService,
)


# =============================================================================
# A. INITIAL DISCOVERY TESTS
# =============================================================================

class TestInitialDiscovery:
    """Tests for initial self-discovery baseline establishment."""

    def test_startup_establishes_baseline(self, tmp_path):
        """Test 1: startup establishes baseline."""
        workspace = tmp_path / "workspace"
        data_dir = tmp_path / "data"
        evolution_dir = tmp_path / "evolution"
        workspace.mkdir()
        data_dir.mkdir()
        evolution_dir.mkdir()

        service = SelfDiscoveryService(
            workspace_root=str(workspace),
            data_dir=str(data_dir),
            evolution_dir=str(evolution_dir),
            auto_start=False,
        )

        baseline = service._initial_discovery()

        assert baseline.baseline_id != ""
        assert baseline.status in (BaselineStatus.COMPLETE, BaselineStatus.PARTIAL)
        assert baseline.host.hostname != ""
        assert baseline.host.os_name != ""
        assert len(baseline.levels_completed) >= 1  # At least LEVEL_0

    def test_baseline_records_timestamp_source_confidence(self, tmp_path):
        """Test 2: baseline records timestamp/source/confidence."""
        workspace = tmp_path / "workspace"
        data_dir = tmp_path / "data"
        evolution_dir = tmp_path / "evolution"
        workspace.mkdir()
        data_dir.mkdir()
        evolution_dir.mkdir()

        service = SelfDiscoveryService(
            workspace_root=str(workspace),
            data_dir=str(data_dir),
            evolution_dir=str(evolution_dir),
            auto_start=False,
        )

        baseline = service._initial_discovery()

        # Host baseline (LEVEL_0)
        assert baseline.host.timestamp != ""
        assert baseline.host.source == "static"
        assert baseline.host.confidence == 1.0

        # Runtime baseline (LEVEL_1)
        assert baseline.runtime.timestamp != ""
        assert baseline.runtime.source == "runtime"
        assert 0.0 <= baseline.runtime.confidence <= 1.0

    def test_deep_work_deferred_safely(self, tmp_path):
        """Test 3: deep work can be deferred safely."""
        workspace = tmp_path / "workspace"
        data_dir = tmp_path / "data"
        evolution_dir = tmp_path / "evolution"
        workspace.mkdir()
        data_dir.mkdir()
        evolution_dir.mkdir()

        # Simulate high resource pressure
        with patch.object(
            SelfDiscoveryService,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 8192,
                "ram_available_mb": 1024,  # Only 1GB available
                "ram_used_pct": 87.5,
                "cpu_count": 4,
                "cpu_load_1m": 3.0,
            },
        ):
            service = SelfDiscoveryService(
                workspace_root=str(workspace),
                data_dir=str(data_dir),
                evolution_dir=str(evolution_dir),
                auto_start=False,
            )

            baseline = service._initial_discovery()

            assert DiscoveryLevel.LEVEL_2_DEEP in baseline.levels_deferred
            assert baseline.status == BaselineStatus.PARTIAL

    def test_partial_baseline_can_resume(self, tmp_path):
        """Test 4: partial baseline can resume."""
        workspace = tmp_path / "workspace"
        data_dir = tmp_path / "data"
        evolution_dir = tmp_path / "evolution"
        workspace.mkdir()
        data_dir.mkdir()
        evolution_dir.mkdir()

        # First run: defer LEVEL_2
        with patch.object(
            SelfDiscoveryService,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 8192,
                "ram_available_mb": 1024,
                "ram_used_pct": 87.5,
                "cpu_count": 4,
                "cpu_load_1m": 3.0,
            },
        ):
            service = SelfDiscoveryService(
                workspace_root=str(workspace),
                data_dir=str(data_dir),
                evolution_dir=str(evolution_dir),
                auto_start=False,
            )
            baseline = service._initial_discovery()

        # Second run: request LEVEL_2 with safe resources
        with patch.object(
            SelfDiscoveryService,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 8192,
                "ram_available_mb": 6144,
                "ram_used_pct": 25.0,
                "cpu_count": 4,
                "cpu_load_1m": 0.5,
            },
        ):
            service2 = SelfDiscoveryService(
                workspace_root=str(workspace),
                data_dir=str(data_dir),
                evolution_dir=str(evolution_dir),
                auto_start=False,
            )
            result = service2.request_level_2_discovery()

            assert result.success
            assert DiscoveryLevel.LEVEL_2_DEEP not in result.baseline.levels_deferred


# =============================================================================
# B. RESOURCE CONTROL TESTS
# =============================================================================

class TestResourceControl:
    """Tests for resource-aware self-control."""

    def test_expensive_work_suppressed_at_unsafe_pressure(self):
        """Test 5: expensive work suppressed at unsafe pressure."""
        controller = ResourceAwareController()

        with patch.object(
            controller,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 8192,
                "ram_available_mb": 512,  # Critical pressure
                "ram_used_pct": 94.0,
                "cpu_count": 4,
                "cpu_load_1m": 4.0,
            },
        ):
            check = controller.check_resource_safety(
                operation_cost=OperationCost.EXPENSIVE,
                force_refresh=True,
            )

            assert not check.safe
            assert check.resource_state == ControllerResourceState.UNSAFE
            assert check.current_pressure == ResourcePressure.CRITICAL

    def test_cheap_work_remains_possible(self):
        """Test 6: cheap work remains possible even at high pressure."""
        controller = ResourceAwareController()

        with patch.object(
            controller,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 8192,
                "ram_available_mb": 2048,  # High pressure
                "ram_used_pct": 75.0,
                "cpu_count": 4,
                "cpu_load_1m": 2.0,
            },
        ):
            check = controller.check_resource_safety(
                operation_cost=OperationCost.CHEAP,
                force_refresh=True,
            )

            assert check.safe  # Cheap work allowed

    def test_unknown_resource_state_no_expensive_work(self):
        """Test 7: unknown resource state does not authorize expensive optional work."""
        controller = ResourceAwareController()

        with patch.object(
            controller,
            '_take_resource_snapshot',
            return_value={
                "ram_total_mb": 0,  # Unknown state
                "ram_available_mb": 0,
                "ram_used_pct": 0.0,
                "cpu_count": 4,
                "cpu_load_1m": 0.0,
            },
        ):
            check = controller.check_resource_safety(
                operation_cost=OperationCost.EXPENSIVE,
                force_refresh=True,
            )

            assert not check.safe
            assert check.resource_state == ControllerResourceState.UNKNOWN

    def test_action_cost_is_measured(self, tmp_path):
        """Test 8: action cost is measured."""
        evolution_dir = tmp_path / "evolution"
        evolution_dir.mkdir()

        service = CostMeasurementService(evolution_dir=str(evolution_dir))

        def dummy_operation():
            return "result"

        result, record = service.measure_operation("test_action", dummy_operation)

        assert result == "result"
        assert record.action == "test_action"
        assert record.duration_ms > 0
        assert record.result == "success"
        assert record.ram_before.timestamp != ""
        assert record.ram_after.timestamp != ""


# =============================================================================
# C. REFLECTION TESTS
# =============================================================================

class TestReflectionRouting:
    """Tests for reflection routing."""

    def test_reflection_reuses_existing_evidence(self):
        """Test 9: reflection reuses existing evidence."""
        service = ReflectionRoutingService()

        # Mock world model with fresh evidence
        mock_world_model = MagicMock()
        mock_world_model.freshness_ms = 30000  # 30s old
        mock_world_model.last_updated = datetime.now(timezone.utc) - timedelta(seconds=30)
        mock_world_model.confidence = 0.8

        decision = service.route_request(
            request_text="reflexiona sobre el estado actual",
            world_model=mock_world_model,
        )

        assert decision.route == ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
        assert decision.evidence_sufficiency == EvidenceSufficiency.SUFFICIENT
        assert not decision.requires_targeted_refresh

    def test_quoted_terms_do_not_trigger_observation(self):
        """Test 10: quoted terms do not trigger observation."""
        service = ReflectionRoutingService()

        decision = service.route_request(
            request_text='¿están las "red" y "conexión" disponibles?',
        )

        assert decision.route == ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
        assert not decision.requires_targeted_refresh

    def test_stale_evidence_triggers_targeted_refresh(self):
        """Test 11: stale evidence triggers targeted refresh."""
        service = ReflectionRoutingService()

        # Mock world model with stale evidence
        mock_world_model = MagicMock()
        mock_world_model.freshness_ms = 120000  # 120s old (> 90s TTL)
        mock_world_model.last_updated = datetime.now(timezone.utc) - timedelta(seconds=120)
        mock_world_model.confidence = 0.8

        decision = service.route_request(
            request_text="reflexiona sobre el estado actual",
            world_model=mock_world_model,
        )

        assert decision.route == ReflectionRoute.REFLECT_ON_EXISTING_EVIDENCE
        assert decision.evidence_sufficiency == EvidenceSufficiency.STALE
        assert decision.requires_targeted_refresh

    def test_explicit_observe_now_still_works(self):
        """Test 12: explicit observe-now still works."""
        service = ReflectionRoutingService()

        decision = service.route_request(
            request_text="¿qué está pasando ahora mismo?",
        )

        assert decision.route == ReflectionRoute.OBSERVE_NOW
        assert decision.evidence_sufficiency == EvidenceSufficiency.MISSING


# =============================================================================
# D. MODEL SELECTION TESTS
# =============================================================================

class TestModelSelection:
    """Tests for resource-aware model selection."""

    def test_model_selection_uses_goal_capability_resources(self):
        """Test 13: model selection uses goal + capability + resources."""
        selector = ResourceAwareModelSelector()

        criteria = ModelSelectionCriteria(
            goal="code_generation",
            required_capability=Capability.ADVANCED,
            ram_available_mb=8192,
            vram_available_mb=2048,
            resource_pressure=ResourcePressure.LOW,
            resource_state=ControllerResourceState.SAFE,
        )

        decision = selector.select_model(criteria)

        assert decision.selected_model is not None
        assert decision.selected_model.capability_level >= Capability.ADVANCED
        assert decision.resource_safe

    def test_oversized_local_model_rejected_when_unsafe(self):
        """Test 14: oversized local model rejected when unsafe."""
        selector = ResourceAwareModelSelector()

        criteria = ModelSelectionCriteria(
            goal="code_generation",
            required_capability=Capability.EXPERT,
            ram_available_mb=2048,  # Only 2GB available
            vram_available_mb=512,
            resource_pressure=ResourcePressure.HIGH,
            resource_state=ControllerResourceState.UNSAFE,
        )

        decision = selector.select_model(criteria)

        # Should select smaller model or fallback
        if decision.selected_model:
            assert decision.selected_model.ram_requirement_mb <= criteria.ram_available_mb
        assert decision.fallback_used or not decision.resource_safe

    def test_lightweight_model_preferred_for_low_cost_task(self):
        """Test 15: lightweight model preferred for low-cost task."""
        selector = ResourceAwareModelSelector()

        criteria = ModelSelectionCriteria(
            goal="simple_question",
            required_capability=Capability.BASIC,
            ram_available_mb=8192,
            vram_available_mb=2048,
            resource_pressure=ResourcePressure.LOW,
            resource_state=ControllerResourceState.SAFE,
        )

        decision = selector.select_model(criteria)

        assert decision.selected_model is not None
        # Should prefer basic capability model
        assert decision.selected_model.capability_level == Capability.BASIC

    def test_stronger_model_allowed_when_resources_support(self):
        """Test 16: stronger model allowed when resources support it."""
        selector = ResourceAwareModelSelector()

        criteria = ModelSelectionCriteria(
            goal="complex_reasoning",
            required_capability=Capability.ADVANCED,
            ram_available_mb=16384,  # Plenty of RAM
            vram_available_mb=8192,
            resource_pressure=ResourcePressure.LOW,
            resource_state=ControllerResourceState.SAFE,
        )

        decision = selector.select_model(criteria)

        assert decision.selected_model is not None
        assert decision.selected_model.capability_level >= Capability.ADVANCED
        assert decision.resource_safe

    def test_provider_availability_affects_selection(self):
        """Test 17: provider availability affects selection."""
        selector = ResourceAwareModelSelector()

        # Set all models as unavailable
        for model in selector._models:
            model.available = False

        criteria = ModelSelectionCriteria(
            goal="code_generation",
            required_capability=Capability.STANDARD,
            ram_available_mb=8192,
            resource_pressure=ResourcePressure.LOW,
            resource_state=ControllerResourceState.SAFE,
        )

        decision = selector.select_model(criteria)

        # Should have no suitable model
        assert decision.selected_model is None or decision.fallback_used

    def test_local_vs_remote_distinction_exists(self):
        """Test 18: local vs remote distinction exists."""
        selector = ResourceAwareModelSelector()

        # Check that models have provider kind
        for model in selector._models:
            assert model.provider_kind in (ProviderKind.LOCAL, ProviderKind.REMOTE)

        # Test offline-only mode
        criteria = ModelSelectionCriteria(
            goal="code_generation",
            required_capability=Capability.STANDARD,
            ram_available_mb=8192,
            offline_only=True,
            resource_pressure=ResourcePressure.LOW,
            resource_state=ControllerResourceState.SAFE,
        )

        decision = selector.select_model(criteria)

        if decision.selected_model:
            assert decision.selected_model.provider_kind == ProviderKind.LOCAL


# =============================================================================
# E. LEARNING TESTS
# =============================================================================

class TestLearning:
    """Tests for experience storage and adaptive protocol."""

    def test_execution_outcome_is_persisted(self, tmp_path):
        """Test 19: execution outcome is persisted."""
        evolution_dir = tmp_path / "evolution"
        evolution_dir.mkdir()

        service = ExperienceStorageService(evolution_dir=str(evolution_dir))

        experience = service.record_execution(
            action="test_action",
            goal="test_goal",
            model_used="gemma3:1b",
            provider_kind="local",
            resource_state={"ram_available_mb": 8192},
            outcome="success",
            duration_ms=500.0,
            ram_delta_mb=10.0,
        )

        assert experience.experience_id != ""
        assert experience.action == "test_action"
        assert experience.outcome == "success"

        # Verify persistence
        history = service.get_execution_history(action="test_action")
        assert len(history) > 0
        assert history[0].action == "test_action"

    def test_measured_experience_affects_future_recommendation(self, tmp_path):
        """Test 20: measured experience can affect future recommendation."""
        evolution_dir = tmp_path / "evolution"
        evolution_dir.mkdir()

        experience_service = ExperienceStorageService(evolution_dir=str(evolution_dir))
        protocol_service = AdaptiveProtocolService(
            evolution_dir=str(evolution_dir),
            experience_storage=experience_service,
        )

        # Record successful outcomes
        for _ in range(5):
            experience_service.record_execution(
                action="model_selection",
                goal="code_generation",
                model_used="gemma3:4b",
                provider_kind="local",
                resource_state={"ram_available_mb": 8192},
                outcome="success",
                duration_ms=800.0,
            )

        # Learn from outcomes
        rule = protocol_service.learn_from_outcome(
            old_rule="use_default_model",
            observation="gemma3:4b performed well",
            actual_result="success",
            new_rule="prefer_gemma3:4b_for_code",
            rule_key="code_generation_model",
        )

        assert rule.confidence > 0.0
        assert rule.observation_count >= 1

    def test_historical_success_alone_does_not_authorize_action(self, tmp_path):
        """Test 21: historical success alone does not authorize action."""
        evolution_dir = tmp_path / "evolution"
        evolution_dir.mkdir()

        experience_service = ExperienceStorageService(evolution_dir=str(evolution_dir))
        protocol_service = AdaptiveProtocolService(
            evolution_dir=str(evolution_dir),
            experience_storage=experience_service,
        )

        # Record only 2 successful outcomes (below threshold)
        for _ in range(2):
            experience_service.record_execution(
                action="model_selection",
                goal="code_generation",
                model_used="gemma3:4b",
                provider_kind="local",
                resource_state={"ram_available_mb": 8192},
                outcome="success",
                duration_ms=800.0,
            )

        # Learn from outcomes
        rule = protocol_service.learn_from_outcome(
            old_rule="use_default_model",
            observation="gemma3:4b performed well",
            actual_result="success",
            new_rule="prefer_gemma3:4b_for_code",
            rule_key="code_generation_model",
        )

        # Get recommendation
        recommendation = protocol_service.get_recommendation("code_generation_model")

        # Should not apply due to insufficient observations
        assert not recommendation.apply
        assert "Insufficient observations" in recommendation.reason


# =============================================================================
# F. REGRESSION TESTS
# =============================================================================

class TestRegression:
    """Regression tests to ensure no unintended side effects."""

    def test_ordinary_chat_remains_lightweight(self):
        """Test 22: ordinary chat remains lightweight."""
        controller = ResourceAwareController()

        # Ordinary chat should be cheap
        cost = controller.estimate_operation_cost("ordinary_chat")

        assert cost.cost_level in (OperationCost.TRIVIAL, OperationCost.CHEAP)
        assert cost.expected_duration_ms < 1000

    def test_no_duplicate_world_model(self):
        """Test 23: no duplicate WorldModel - verify we reuse existing."""
        # This test verifies that our implementation references existing models
        # rather than creating duplicates
        from iabv_v15.domain.models import WorldModelSnapshot, EnvironmentSelfModel

        # Verify the models exist and are the expected types
        assert hasattr(WorldModelSnapshot, '__annotations__')
        assert hasattr(EnvironmentSelfModel, '__annotations__')

        # Our reflection routing service should accept these models
        service = ReflectionRoutingService()
        mock_world = WorldModelSnapshot()
        mock_env = EnvironmentSelfModel()

        decision = service.route_request("test", mock_world, mock_env)
        assert decision is not None

    def test_hard_security_constraints_unchanged(self):
        """Test 24: hard security constraints unchanged."""
        # Verify that our adaptive components do not modify security constraints
        # This is a structural test - we verify that no security-related
        # constants or policies are exposed for modification

        from iabv_v15.services.adaptive.resource_aware_controller import (
            ResourceAwareController,
        )

        # Check that thresholds are private (prefixed with _)
        assert hasattr(ResourceAwareController, '_RAM_CRITICAL_MB')
        assert hasattr(ResourceAwareController, '_CPU_CRITICAL_PCT')

        # Verify they are not easily modifiable from outside
        controller = ResourceAwareController()
        assert not hasattr(controller, 'RAM_CRITICAL_MB')  # Not exposed
        assert not hasattr(controller, 'CPU_CRITICAL_PCT')  # Not exposed
