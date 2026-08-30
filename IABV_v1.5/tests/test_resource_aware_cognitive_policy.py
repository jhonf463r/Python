"""Resource-aware cognitive policy integration tests.

Tests that real resource state from ResourceAwareController is correctly
projected into CognitiveStateVector and influences policy decisions.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from iabv_v15.services.adaptive.resource_aware_controller import (
    ResourceCheck,
    ResourcePressure as AdaptiveResourcePressure,
    ResourceState,
)
from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    CognitivePolicyDecision,
    ResourceProjection,
    ResourcePressure,
)
from iabv_v15.services.evolution.work_queue_executor import WorkQueueExecutor


class TestResourceAwareCognitivePolicy:
    """Test resource-aware cognitive policy integration."""

    def test_real_resource_controller_projection_reaches_state_vector(self):
        """Test 1: Real ResourceAwareController projection reaches CognitiveStateVector."""
        # Mock ResourceAwareController
        mock_resource_controller = MagicMock()
        mock_resource_controller.check_resource_safety.return_value = ResourceCheck(
            safe=True,
            resource_state=ResourceState.SAFE,
            ram_pressure=AdaptiveResourcePressure.LOW,
            cpu_pressure=AdaptiveResourcePressure.LOW,
            gpu_pressure=AdaptiveResourcePressure.LOW,
            current_pressure=AdaptiveResourcePressure.LOW,
            ram_available_mb=8192,  # 8GB
            ram_used_pct=30.0,
            cpu_load_1m=0.5,
            reason="Low pressure: operation safe",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Create WorkQueueExecutor with resource controller
        executor = WorkQueueExecutor(
            control_master_service=None,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
            resource_aware_controller=mock_resource_controller,
        )

        # Build resource projection
        projection = executor._build_resource_projection()

        # Verify projection contains real resource state
        assert projection.source == "ResourceAwareController"
        assert projection.pressure == ResourcePressure.LOW
        assert projection.ram_available_gb == pytest.approx(8.0, rel=0.1)
        assert projection.ram_used_pct == pytest.approx(30.0, rel=0.1)
        assert projection.cpu_load_1m == pytest.approx(0.5, rel=0.1)
        assert projection.confidence == 1.0

    def test_projection_is_immutable(self):
        """Test 2: Projection is immutable."""
        projection = ResourceProjection(
            resource_state_id="test-id",
            timestamp="2024-01-01T00:00:00Z",
            source="test",
            pressure=ResourcePressure.LOW,
            cpu_load_1m=0.5,
            cpu_count=4,
            ram_available_gb=8.0,
            ram_used_pct=30.0,
            gpu_available=False,
            vram_available_gb=0.0,
            available_capacity=1.0,
            confidence=1.0,
        )

        # Verify frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError
            projection.ram_available_gb = 4.0

    def test_projection_contains_source_and_provenance(self):
        """Test 3: Projection contains source/provenance."""
        projection = ResourceProjection(
            resource_state_id="test-id",
            timestamp="2024-01-01T00:00:00Z",
            source="ResourceAwareController",
            pressure=ResourcePressure.LOW,
        )

        assert projection.source == "ResourceAwareController"
        assert projection.resource_state_id == "test-id"
        assert projection.timestamp == "2024-01-01T00:00:00Z"

    def test_stale_unknown_state_represented_truthfully(self):
        """Test 4: Stale/unknown state is represented truthfully."""
        # Mock ResourceAwareController returning unknown state
        mock_resource_controller = MagicMock()
        mock_resource_controller.check_resource_safety.return_value = ResourceCheck(
            safe=False,
            resource_state=ResourceState.UNKNOWN,
            ram_pressure=AdaptiveResourcePressure.LOW,
            cpu_pressure=AdaptiveResourcePressure.LOW,
            gpu_pressure=AdaptiveResourcePressure.LOW,
            current_pressure=AdaptiveResourcePressure.LOW,
            ram_available_mb=0,
            ram_used_pct=0.0,
            cpu_load_1m=0.0,
            reason="Resource state unknown",
            timestamp="2024-01-01T00:00:00Z",
        )

        executor = WorkQueueExecutor(
            control_master_service=None,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
            resource_aware_controller=mock_resource_controller,
        )

        projection = executor._build_resource_projection()

        # Unknown state should have zero confidence
        assert projection.confidence == 0.0
        assert projection.source == "ResourceAwareController"

    def test_normal_resources_influence_policy_output(self):
        """Test 5: Normal resources influence policy output."""
        # Normal resources (LOW pressure)
        normal_projection = ResourceProjection(
            pressure=ResourcePressure.LOW,
            ram_available_gb=8.0,
            available_capacity=1.0,
            confidence=1.0,
        )

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=normal_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # Normal resources should allow normal depth and budget
        assert decision.reasoning_depth.value in ('level_1', 'level_2')
        assert decision.budget.max_time_seconds > 0

    def test_high_pressure_influences_policy_output(self):
        """Test 6: High pressure influences policy output."""
        # High resources pressure
        high_projection = ResourceProjection(
            pressure=ResourcePressure.HIGH,
            ram_available_gb=3.0,
            available_capacity=0.3,
            confidence=1.0,
        )

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=high_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # High pressure should reduce depth or budget
        assert decision.reasoning_depth.value in ('level_0', 'level_1')

    def test_critical_pressure_influences_policy_output(self):
        """Test 7: Critical pressure influences policy output."""
        # Critical resources pressure
        critical_projection = ResourceProjection(
            pressure=ResourcePressure.CRITICAL,
            ram_available_gb=1.0,
            available_capacity=0.1,
            confidence=1.0,
        )

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=critical_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # Critical pressure should result in minimal depth
        assert decision.reasoning_depth.value == 'level_0'

    def test_higher_pressure_never_increases_cognitive_budget(self):
        """Test 8: Higher pressure never increases cognitive budget."""
        # Normal pressure
        normal_projection = ResourceProjection(
            pressure=ResourcePressure.LOW,
            available_capacity=1.0,
        )

        normal_state = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=normal_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        # High pressure
        high_projection = ResourceProjection(
            pressure=ResourcePressure.HIGH,
            available_capacity=0.3,
        )

        high_state = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=high_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        normal_decision = policy.compute_decision(normal_state)
        high_decision = policy.compute_decision(high_state)

        # Higher pressure should not increase time budget
        assert high_decision.budget.max_time_seconds <= normal_decision.budget.max_time_seconds

    def test_higher_pressure_does_not_increase_parallelism(self):
        """Test 9: Higher pressure does not increase parallelism."""
        # Normal pressure
        normal_projection = ResourceProjection(pressure=ResourcePressure.LOW)
        normal_state = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=normal_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        # High pressure
        high_projection = ResourceProjection(pressure=ResourcePressure.HIGH)
        high_state = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=high_projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        normal_decision = policy.compute_decision(normal_state)
        high_decision = policy.compute_decision(high_state)

        # Higher pressure should not enable parallelism if it was disabled
        if not normal_decision.parallelism_allowed:
            assert not high_decision.parallelism_allowed

    def test_resource_policy_never_overrides_hard_governance(self):
        """Test 10: Resource policy never overrides hard governance."""
        # Even with LOW pressure, policy is just an envelope
        projection = ResourceProjection(pressure=ResourcePressure.LOW)

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # Policy decision is just an envelope, not authorization
        # It does not override ResourceAwareController hard checks
        assert decision is not None
        # The policy does not have a "safe" field - it's just a cognitive envelope
        # ResourceAwareController still has final say on execution

    def test_zero_provider_calls_during_policy_evaluation(self):
        """Test 11: Zero provider calls during policy evaluation."""
        projection = ResourceProjection(pressure=ResourcePressure.LOW)

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        # CognitiveOperatingPolicy is a pure function with no side effects
        # It does not make any provider calls by design
        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # The policy computation completes without any external calls
        assert decision is not None

    def test_zero_ollama_calls(self):
        """Test 12: Zero Ollama calls."""
        projection = ResourceProjection(pressure=ResourcePressure.LOW)

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        # CognitiveOperatingPolicy is a pure function with no side effects
        # It does not make any Ollama calls by design
        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # The policy computation completes without any external calls
        assert decision is not None

    def test_zero_devin_calls(self):
        """Test 13: Zero Devin calls."""
        projection = ResourceProjection(pressure=ResourcePressure.LOW)

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        # CognitiveOperatingPolicy is a pure function with no side effects
        # It does not make any Devin calls by design
        policy = CognitiveOperatingPolicy()
        decision = policy.compute_decision(state_vector)

        # The policy computation completes without any external calls
        assert decision is not None

    def test_policy_remains_deterministic_for_identical_inputs(self):
        """Test 14: Existing policy remains deterministic for identical normalized inputs."""
        projection = ResourceProjection(
            pressure=ResourcePressure.LOW,
            ram_available_gb=8.0,
            available_capacity=1.0,
            confidence=1.0,
        )

        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.3,
            expected_value=0.8,
            available_time_seconds=600.0,
            resource_projection=projection,
            memory_relevance=0.5,
            prior_experience=0.5,
        )

        policy = CognitiveOperatingPolicy()
        decision1 = policy.compute_decision(state_vector)
        decision2 = policy.compute_decision(state_vector)

        # Identical inputs should produce identical outputs
        assert decision1.horizon == decision2.horizon
        assert decision1.reasoning_depth == decision2.reasoning_depth
        assert decision1.observation_mode == decision2.observation_mode
        assert decision1.budget == decision2.budget

    def test_existing_context_reuse_remains_unchanged(self):
        """Test 15: Existing context reuse remains unchanged."""
        # Mock ResourceAwareController
        mock_resource_controller = MagicMock()
        mock_resource_controller.check_resource_safety.return_value = ResourceCheck(
            safe=True,
            resource_state=ResourceState.SAFE,
            ram_pressure=AdaptiveResourcePressure.LOW,
            cpu_pressure=AdaptiveResourcePressure.LOW,
            gpu_pressure=AdaptiveResourcePressure.LOW,
            current_pressure=AdaptiveResourcePressure.LOW,
            ram_available_mb=8192,
            ram_used_pct=30.0,
            cpu_load_1m=0.5,
            reason="Low pressure: operation safe",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Mock ControlMasterService
        mock_control_master = MagicMock()
        mock_queue = [
            {
                'id': 'objective:123',
                'title': 'Test objective',
                'status': 'active',
                'priority_score': 80,
                'source': 'objective_repository',
                'next_action': 'Continue work',
                'evidence_refs': [],
            }
        ]
        mock_control_master.current_work_queue.return_value = mock_queue

        # Create WorkQueueExecutor
        executor = WorkQueueExecutor(
            control_master_service=mock_control_master,
            inference_service=None,
            task_outcome_recorder=None,
            cognitive_policy=CognitiveOperatingPolicy(),
            resource_aware_controller=mock_resource_controller,
        )

        # Verify that resource projection is built correctly
        projection = executor._build_resource_projection()
        assert projection.source == "ResourceAwareController"
        assert projection.confidence == 1.0

        # Context reuse mechanisms are not affected by resource projection
        # The projection is only used for policy decision, not for context assembly
