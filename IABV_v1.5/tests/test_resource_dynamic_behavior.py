"""Verification test for resource-aware policy dynamic behavior.

This test verifies that the same work item produces meaningfully different
CognitivePolicyDecision results under controlled resource states.
"""
from iabv_v15.services.cognitive import (
    CognitiveOperatingPolicy,
    CognitiveStateVector,
    ResourceProjection,
    ResourcePressure,
)


def test_resource_pressure_affects_policy_decision():
    """Verify that resource pressure affects policy decision output."""
    # Same work item state
    base_state = {
        'goal_value': 0.8,
        'complexity': 0.5,
        'ambiguity': 0.3,
        'uncertainty': 0.4,
        'risk': 0.3,
        'expected_value': 0.8,
        'available_time_seconds': 600.0,
        'memory_relevance': 0.5,
        'prior_experience': 0.5,
    }

    # Normal pressure
    normal_projection = ResourceProjection(
        pressure=ResourcePressure.LOW,
        ram_available_gb=8.0,
        available_capacity=1.0,
        confidence=1.0,
    )
    normal_state = CognitiveStateVector(
        resource_projection=normal_projection,
        **base_state,
    )

    # High pressure
    high_projection = ResourceProjection(
        pressure=ResourcePressure.HIGH,
        ram_available_gb=3.0,
        available_capacity=0.3,
        confidence=1.0,
    )
    high_state = CognitiveStateVector(
        resource_projection=high_projection,
        **base_state,
    )

    # Critical pressure
    critical_projection = ResourceProjection(
        pressure=ResourcePressure.CRITICAL,
        ram_available_gb=1.0,
        available_capacity=0.1,
        confidence=1.0,
    )
    critical_state = CognitiveStateVector(
        resource_projection=critical_projection,
        **base_state,
    )

    policy = CognitiveOperatingPolicy()
    normal_decision = policy.compute_decision(normal_state)
    high_decision = policy.compute_decision(high_state)
    critical_decision = policy.compute_decision(critical_state)

    # Verify that resource pressure affects at least one decision attribute
    differences = []

    # Check reasoning depth
    if normal_decision.reasoning_depth != high_decision.reasoning_depth:
        differences.append('reasoning_depth')
    if normal_decision.reasoning_depth != critical_decision.reasoning_depth:
        differences.append('reasoning_depth_critical')

    # Check budget
    if normal_decision.budget.max_iterations != high_decision.budget.max_iterations:
        differences.append('max_iterations')
    if normal_decision.budget.max_iterations != critical_decision.budget.max_iterations:
        differences.append('max_iterations_critical')

    if normal_decision.budget.max_observations != high_decision.budget.max_observations:
        differences.append('max_observations')
    if normal_decision.budget.max_observations != critical_decision.budget.max_observations:
        differences.append('max_observations_critical')

    # Check parallelism
    if normal_decision.parallelism_allowed != high_decision.parallelism_allowed:
        differences.append('parallelism')
    if normal_decision.parallelism_allowed != critical_decision.parallelism_allowed:
        differences.append('parallelism_critical')

    # Check chunk size
    if normal_decision.chunk_size != high_decision.chunk_size:
        differences.append('chunk_size')
    if normal_decision.chunk_size != critical_decision.chunk_size:
        differences.append('chunk_size_critical')

    # Check tool selection envelope
    if normal_decision.tool_selection_envelope.allowed_remote != high_decision.tool_selection_envelope.allowed_remote:
        differences.append('allowed_remote')
    if normal_decision.tool_selection_envelope.allowed_remote != critical_decision.tool_selection_envelope.allowed_remote:
        differences.append('allowed_remote_critical')

    # At least one attribute should differ between pressure levels
    assert len(differences) > 0, f"Resource pressure should affect policy decision. Differences: {differences}"

    # Higher pressure should never increase cognitive budget
    assert high_decision.budget.max_iterations <= normal_decision.budget.max_iterations
    assert critical_decision.budget.max_iterations <= high_decision.budget.max_iterations

    # Higher pressure should not enable parallelism if it was disabled
    if not normal_decision.parallelism_allowed:
        assert not high_decision.parallelism_allowed
        assert not critical_decision.parallelism_allowed

    print(f"Resource pressure affects: {', '.join(set(differences))}")
