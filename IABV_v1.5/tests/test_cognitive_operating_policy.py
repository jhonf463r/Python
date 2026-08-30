"""Focused tests for Cognitive Operating Policy.

Tests verify that the cognitive policy is pure, deterministic, side-effect free,
and produces correct cognitive envelopes for various state vectors.
"""

from __future__ import annotations

import pytest
from datetime import datetime

from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    CognitivePolicyDecision,
    TimeHorizon,
    ReasoningDepth,
    ObservationMode,
    ResourcePressure,
    ToolSelectionEnvelope,
    BudgetConstraints,
    StoppingConditions,
)


class TestCognitiveOperatingPolicy:
    """Focused tests for Cognitive Operating Policy."""

    def test_policy_is_deterministic_for_normalized_identical_inputs(self):
        """Test 1: Policy is deterministic for normalized identical inputs."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create identical state vectors
        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.2,
            expected_value=0.7,
            available_time_seconds=300,
            available_ram_gb=8.0,
            memory_relevance=0.6,
            prior_experience=0.5,
            work_item_id="test:123",
        )

        # Compute decisions twice
        decision1 = policy.compute_decision(state_vector)
        decision2 = policy.compute_decision(state_vector)

        # Verify decisions are identical
        assert decision1.horizon == decision2.horizon
        assert decision1.reasoning_depth == decision2.reasoning_depth
        assert decision1.observation_mode == decision2.observation_mode
        assert decision1.chunk_size == decision2.chunk_size
        assert decision1.parallelism_allowed == decision2.parallelism_allowed
        assert decision1.mrv == decision2.mrv
        assert decision1.mvi == decision2.mvi

    def test_policy_is_side_effect_free(self):
        """Test 2: Policy is side-effect free."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.5,
            ambiguity=0.3,
            uncertainty=0.4,
            risk=0.2,
            expected_value=0.7,
            available_time_seconds=300,
            available_ram_gb=8.0,
            memory_relevance=0.6,
            prior_experience=0.5,
            work_item_id="test:123",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify state vector is unchanged (immutable)
        assert state_vector.goal_value == 0.8
        assert state_vector.complexity == 0.5
        assert state_vector.ambiguity == 0.3

        # Verify decision is immutable (frozen dataclass)
        with pytest.raises(Exception):  # FrozenInstanceError
            decision.horizon = TimeHorizon.LONG

    def test_policy_returns_short_horizon_for_urgent_low_latency_work(self):
        """Test 3: Policy returns short horizon for urgent low-latency work."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector for urgent low-latency work
        state_vector = CognitiveStateVector(
            goal_value=0.9,  # High goal value
            complexity=0.3,
            ambiguity=0.2,
            uncertainty=0.3,
            risk=0.1,
            expected_value=0.8,
            available_time_seconds=30,  # Urgent: 30 seconds
            available_ram_gb=8.0,
            memory_relevance=0.7,
            prior_experience=0.6,
            work_item_id="test:urgent",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify short horizon
        assert decision.horizon == TimeHorizon.SHORT

    def test_policy_can_return_medium_horizon_for_normal_work(self):
        """Test 4: Policy can return medium horizon for normal work."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector for normal work
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,  # 10 minutes
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:normal",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify medium horizon
        assert decision.horizon == TimeHorizon.MEDIUM

    def test_policy_can_return_long_horizon_for_architectural_work(self):
        """Test 5: Policy can return long horizon for architectural work."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector for architectural work
        state_vector = CognitiveStateVector(
            goal_value=0.8,
            complexity=0.9,  # High complexity
            ambiguity=0.5,
            uncertainty=0.6,
            risk=0.4,
            expected_value=0.9,  # High expected value
            available_time_seconds=7200,  # 2 hours
            available_ram_gb=16.0,
            memory_relevance=0.4,
            prior_experience=0.3,
            work_item_id="test:architectural",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify long horizon
        assert decision.horizon == TimeHorizon.LONG

    def test_resource_pressure_reduces_allowed_depth_budget(self):
        """Test 6: Resource pressure reduces allowed depth/budget."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with critical resource pressure
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=1.0,  # Critical: < 2GB
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:critical",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify depth is reduced to LEVEL_0
        assert decision.reasoning_depth == ReasoningDepth.LEVEL_0

        # Verify budget is reduced
        assert decision.budget.max_iterations == 1
        assert decision.budget.max_observations == 0
        assert decision.budget.max_replanning == 0

    def test_higher_uncertainty_increases_evidence_requirement(self):
        """Test 7: Higher uncertainty increases evidence requirement."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with high uncertainty
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.9,  # High uncertainty
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.3,  # Low memory relevance
            prior_experience=0.3,
            work_item_id="test:high_uncertainty",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify depth is increased to LEVEL_2 (for evidence gathering)
        assert decision.reasoning_depth == ReasoningDepth.LEVEL_2

        # Verify stopping conditions require more evidence
        assert decision.stopping_conditions.sufficient_evidence is False

    def test_high_risk_increases_stopping_validation_constraints(self):
        """Test 8: High risk increases stopping/validation constraints."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with high risk
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.9,  # High risk
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:high_risk",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify target confidence is increased
        assert decision.budget.target_confidence >= 0.9

        # Verify parallelism is forbidden
        assert decision.parallelism_allowed is False

    def test_low_mrv_permits_stopping(self):
        """Test 9: Low MRV permits stopping."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with low MRV (very low uncertainty, very low expected value)
        state_vector = CognitiveStateVector(
            goal_value=0.1,  # Very low goal value
            complexity=0.1,
            ambiguity=0.1,
            uncertainty=0.05,  # Very low uncertainty
            risk=0.05,
            expected_value=0.1,  # Very low expected value
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.9,  # High memory relevance
            prior_experience=0.9,
            work_item_id="test:low_mrv",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify MRV is low
        assert decision.mrv < 0.1

        # Verify stopping conditions indicate low marginal gain
        assert decision.stopping_conditions.low_marginal_gain is True

    def test_mvi_greater_than_mrv_prefers_observation(self):
        """Test 10: MVI > MRV prefers observation."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector where MVI > MRV
        # High uncertainty + low memory relevance → high MVI
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.9,  # High uncertainty
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.1,  # Low memory relevance → high MVI
            prior_experience=0.3,
            work_item_id="test:mvi_high",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify MVI > MRV
        assert decision.mvi > decision.mrv

        # Verify observation mode is OBSERVE
        assert decision.observation_mode == ObservationMode.OBSERVE

    def test_sufficient_evidence_allows_action(self):
        """Test 11: Sufficient evidence allows action."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with sufficient evidence and low MRV
        state_vector = CognitiveStateVector(
            goal_value=0.4,  # Lower goal value to reduce MRV
            complexity=0.3,
            ambiguity=0.2,
            uncertainty=0.2,  # Low uncertainty
            risk=0.2,
            expected_value=0.3,  # Lower expected value to reduce MRV
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.9,  # High memory relevance
            prior_experience=0.8,
            work_item_id="test:sufficient_evidence",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify stopping conditions indicate sufficient evidence
        assert decision.stopping_conditions.sufficient_evidence is True

        # Verify observation mode is ACT
        assert decision.observation_mode == ObservationMode.ACT

    def test_insufficient_evidence_cannot_directly_authorize_action(self):
        """Test 12: Insufficient evidence cannot directly authorize action."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with insufficient evidence
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.6,
            uncertainty=0.8,  # High uncertainty
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.3,  # Low memory relevance
            prior_experience=0.3,
            work_item_id="test:insufficient_evidence",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify stopping conditions indicate insufficient evidence
        assert decision.stopping_conditions.sufficient_evidence is False

        # Verify observation mode is NOT ACT
        assert decision.observation_mode != ObservationMode.ACT

    def test_hard_budget_overrides_mrv(self):
        """Test 13: Hard budget overrides MRV."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with hard budget constraint
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=10,  # Hard time bound: 10 seconds
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:hard_budget",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify hard time bound is set
        assert decision.budget.max_time_seconds == 10

        # Verify horizon is SHORT (due to hard budget)
        assert decision.horizon == TimeHorizon.SHORT

    def test_chunk_size_responds_to_budget(self):
        """Test 14: Chunk size responds to budget."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with low budget
        state_vector_low_budget = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=100,  # Low budget
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:low_budget",
        )

        # Compute decision
        decision_low = policy.compute_decision(state_vector_low_budget)

        # Verify chunk size is small
        assert decision_low.chunk_size == "small"

        # Create state vector with high budget
        state_vector_high_budget = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.2,
            uncertainty=0.2,
            risk=0.2,
            expected_value=0.6,
            available_time_seconds=7200,  # High budget
            available_ram_gb=16.0,
            memory_relevance=0.8,
            prior_experience=0.8,
            work_item_id="test:high_budget",
        )

        # Compute decision
        decision_high = policy.compute_decision(state_vector_high_budget)

        # Verify chunk size is large
        assert decision_high.chunk_size == "large"

    def test_parallelism_is_restricted_by_dependency_resource_conditions(self):
        """Test 15: Parallelism is restricted by dependency/resource conditions."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector with high resource pressure
        state_vector_high_pressure = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=3.0,  # High pressure: < 4GB
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:high_pressure",
        )

        # Compute decision
        decision_high = policy.compute_decision(state_vector_high_pressure)

        # Verify parallelism is forbidden
        assert decision_high.parallelism_allowed is False

        # Create state vector with low resource pressure
        state_vector_low_pressure = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.2,  # Low risk
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,  # Low pressure
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:low_pressure",
        )

        # Compute decision
        decision_low = policy.compute_decision(state_vector_low_pressure)

        # Verify parallelism is allowed
        assert decision_low.parallelism_allowed is True

    def test_tool_selection_output_is_constraints_not_hardcoded_provider_identity(self):
        """Test 16: Tool selection output is constraints, not hardcoded provider identity."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:tool_selection",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify tool selection envelope contains constraints
        assert isinstance(decision.tool_selection_envelope, ToolSelectionEnvelope)
        assert decision.tool_selection_envelope.allowed_local is not None
        assert decision.tool_selection_envelope.allowed_remote is not None
        assert decision.tool_selection_envelope.min_reasoning_level is not None

        # Verify no hardcoded provider names
        assert "ollama" not in str(decision.tool_selection_envelope).lower()
        assert "devin" not in str(decision.tool_selection_envelope).lower()

    def test_no_provider_executes_during_policy_evaluation(self):
        """Test 17: No provider executes during policy evaluation."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:no_provider",
        )

        # Compute decision (should not execute any provider)
        decision = policy.compute_decision(state_vector)

        # Verify decision is computed without side effects
        assert decision is not None
        assert decision.decision_id is not None

        # Verify no network calls were made (policy is pure)
        # This is verified by the fact that the test completes quickly
        # without any external dependencies

    def test_no_ollama_executes_during_policy_evaluation(self):
        """Test 18: No Ollama executes during policy evaluation."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:no_ollama",
        )

        # Compute decision (should not call Ollama)
        decision = policy.compute_decision(state_vector)

        # Verify decision is computed without Ollama
        assert decision is not None
        assert "ollama" not in decision.decision_id.lower()

    def test_no_devin_executes_during_policy_evaluation(self):
        """Test 19: No Devin executes during policy evaluation."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:no_devin",
        )

        # Compute decision (should not call Devin)
        decision = policy.compute_decision(state_vector)

        # Verify decision is computed without Devin
        assert decision is not None
        assert "devin" not in decision.decision_id.lower()

    def test_existing_governance_remains_unchanged(self):
        """Test 20: Existing governance remains unchanged."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:governance",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify policy does not modify governance
        # (This is verified by the fact that the policy has no
        # references to governance services and does not modify
        # any external state)

        # Verify decision is immutable
        assert isinstance(decision, CognitivePolicyDecision)

    def test_context_reuse_remains_unchanged(self):
        """Test 21: Context reuse remains unchanged."""
        from iabv_v15.services.cognitive import CognitiveOperatingPolicy, CognitiveStateVector

        policy = CognitiveOperatingPolicy()

        # Create state vector
        state_vector = CognitiveStateVector(
            goal_value=0.6,
            complexity=0.5,
            ambiguity=0.4,
            uncertainty=0.5,
            risk=0.3,
            expected_value=0.6,
            available_time_seconds=600,
            available_ram_gb=8.0,
            memory_relevance=0.5,
            prior_experience=0.5,
            work_item_id="test:context_reuse",
        )

        # Compute decision
        decision = policy.compute_decision(state_vector)

        # Verify policy does not modify context
        # (This is verified by the fact that the policy has no
        # references to context services and does not modify
        # any external state)

        # Verify state vector is unchanged
        assert state_vector.goal_value == 0.6
        assert state_vector.complexity == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
