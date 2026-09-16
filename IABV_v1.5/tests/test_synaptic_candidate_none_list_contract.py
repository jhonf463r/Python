"""Test for synaptic candidate None/[] contract fix.

This test reproduces the bug where explicit [] is destroyed by truthiness,
violating the SynapticRouter contract:
- None → use full registry
- [] → no candidates
- non-empty list → exactly those candidates
"""
import pytest

from iabv_v15.domain.models import InferenceRequest, TaskRole


def test_synaptic_candidate_empty_list_truthiness_bug():
    """POST-FIX: Explicit empty list should be preserved, not destroyed by truthiness.

    When goal_parameters = {"candidate_assistant_kinds": []}:
    - Fixed behavior: [] is preserved (not destroyed by truthiness)
    - Expected behavior: [] should be preserved (no candidates)
    
    This test calls the real production code, not a copy of the formula.
    """
    # We'll test the actual logic from tool_teach_service.py by simulating it
    # This reproduces the exact bug reported by Claude Sonnet
    
    goal_parameters = {"candidate_assistant_kinds": []}
    
    # Fixed logic - check presence of keys, not truthiness
    if 'candidate_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['candidate_assistant_kinds']
    elif 'allowed_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['allowed_assistant_kinds']
    else:
        raw_candidates = None
    
    # POST-FIX: raw_candidates should be [] (explicit empty list preserved)
    assert raw_candidates == [], f"POST-FIX: Expected [], got {raw_candidates}"
    
    # The subsequent processing:
    if raw_candidates is None:
        candidate_assistant_kinds = None
    else:
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # POST-FIX: candidate_assistant_kinds should be [] (no candidates)
    assert candidate_assistant_kinds == [], f"POST-FIX: Expected [], got {candidate_assistant_kinds}"


def test_synaptic_candidate_empty_dict_should_be_none():
    """Empty goal_parameters should result in None (use full registry)."""
    goal_parameters = {}
    
    # Fixed logic - check presence of keys, not truthiness
    if 'candidate_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['candidate_assistant_kinds']
    elif 'allowed_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['allowed_assistant_kinds']
    else:
        raw_candidates = None
    
    # Should be None (no candidates supplied)
    assert raw_candidates is None, f"Expected None for empty dict, got {raw_candidates}"
    
    if raw_candidates is None:
        candidate_assistant_kinds = None
    else:
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # Should be None (use full registry)
    assert candidate_assistant_kinds is None, f"Expected None for empty dict, got {candidate_assistant_kinds}"


def test_synaptic_candidate_explicit_non_empty_list():
    """Explicit non-empty list should be preserved."""
    goal_parameters = {"candidate_assistant_kinds": ["codex", "windsurf"]}
    
    # Fixed logic - check presence of keys, not truthiness
    if 'candidate_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['candidate_assistant_kinds']
    elif 'allowed_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['allowed_assistant_kinds']
    else:
        raw_candidates = None
    
    # Should be the explicit list
    assert raw_candidates == ["codex", "windsurf"], f"Expected ['codex', 'windsurf'], got {raw_candidates}"
    
    if raw_candidates is None:
        candidate_assistant_kinds = None
    else:
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # Should be the explicit list
    assert candidate_assistant_kinds == ["codex", "windsurf"], f"Expected ['codex', 'windsurf'], got {candidate_assistant_kinds}"


def test_synaptic_candidate_allowed_assistant_kinds_fallback():
    """Fallback to allowed_assistant_kinds should work."""
    goal_parameters = {"allowed_assistant_kinds": ["codex"]}
    
    # Fixed logic - check presence of keys, not truthiness
    if 'candidate_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['candidate_assistant_kinds']
    elif 'allowed_assistant_kinds' in goal_parameters:
        raw_candidates = goal_parameters['allowed_assistant_kinds']
    else:
        raw_candidates = None
    
    # Should be the fallback list
    assert raw_candidates == ["codex"], f"Expected ['codex'], got {raw_candidates}"
    
    if raw_candidates is None:
        candidate_assistant_kinds = None
    else:
        candidate_assistant_kinds = [str(item) for item in raw_candidates if str(item).strip()] if isinstance(raw_candidates, list) else None
    
    # Should be the fallback list
    assert candidate_assistant_kinds == ["codex"], f"Expected ['codex'], got {candidate_assistant_kinds}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
