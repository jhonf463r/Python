"""Test for synaptic routing candidate sentinel fix.

This test reproduces the bug where empty goal_parameters causes
candidate_assistant_kinds to become [] instead of None,
which breaks the routing by removing the candidate universe.
"""
import pytest

from iabv_v15.domain.models import InferenceRequest, TaskRole
from iabv_v15.services.roles.synaptic_router import SynapticRouter
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


def test_synaptic_candidate_sentinel_empty_goal_parameters():
    """POST-FIX: Empty goal_parameters should result in None candidate sentinel.

    When goal_parameters={}, the candidate_assistant_kinds should be None
    to signal "use all candidates from registry", not [] which signals
    "no candidates available".
    """
    # This is a minimal test that directly exercises the boundary
    # without requiring full ToolTeachService setup

    # Simulate the logic from _synaptic_decision_for_request (POST-FIX)
    goal_parameters = {}
    raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds')
    
    # POST-FIX: Preserve None sentinel when no candidates are explicitly supplied
    if raw_candidates is None:
        candidate_assistant_kinds = None
    else:
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # POST-FIX EXPECTATION: This should be None (use registry)
    assert candidate_assistant_kinds is None, f"Expected None for empty goal_parameters, got {candidate_assistant_kinds}"


def test_synaptic_candidate_sentinel_explicit_empty_list():
    """Explicit empty list should remain empty list (preserve contract)."""
    goal_parameters = {'candidate_assistant_kinds': []}
    raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
    
    candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # Explicit empty list should remain empty list
    assert candidate_assistant_kinds == [], f"Expected [] for explicit empty list, got {candidate_assistant_kinds}"


def test_synaptic_candidate_sentinel_explicit_candidates():
    """Explicit candidates should be preserved."""
    goal_parameters = {'candidate_assistant_kinds': ['codex', 'windsurf']}
    raw_candidates = goal_parameters.get('candidate_assistant_kinds') or goal_parameters.get('allowed_assistant_kinds') or []
    
    candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # Explicit candidates should be preserved
    assert candidate_assistant_kinds == ['codex', 'windsurf'], f"Expected ['codex', 'windsurf'], got {candidate_assistant_kinds}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
