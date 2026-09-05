"""Conservative objective evidence extraction for adequacy computation.

This module provides the smallest deterministic evidence extraction
required to determine whether a task's declared objective was
independently observed as satisfied.

DO NOT introduce LLM evaluation or probabilistic reasoning.
This is conservative deterministic comparison only.

EPISTEMIC RULE: TEXTUAL_CONTAINMENT != OBJECTIVE_WORLD_EVIDENCE
"""

from typing import Tuple


def extract_objective_evidence(
    *,
    expected_summary: str = "",
    observed_summary: str = "",
) -> Tuple[bool, bool]:
    """Extract objective evidence from expected and observed summaries.

    This is a conservative deterministic comparison. It does NOT use:
    - LLM judgment
    - Model confidence
    - Execution success status
    - Fallback completion
    - Probabilistic matching

    EPISTEMIC SEMANTICS:
    - TEXTUAL_MATCH: expected text appears in observed text (this is what we check)
    - INDEPENDENT_OBSERVATION: evidence from external world validation (NOT provided here)
    - OBJECTIVE_VALIDATION: objective was actually satisfied in the world (NOT provided here)
    - LEARNING_ELIGIBILITY: adequate for learning from this outcome (requires independent observation)

    The logic is:
    1. If expected_summary is empty/missing: no evidence (False, False)
    2. If expected_summary exists and observed_summary contains textual evidence:
       (True, False) - TEXTUAL MATCH but NOT INDEPENDENT OBSERVATION
    3. If expected_summary exists but no textual match: (False, False)

    CRITICAL: This method NEVER returns (True, True) because textual containment
    is NOT equivalent to independent world observation. Independent observation
    requires external world validation (e.g., file system check, API call, etc.),
    which is outside the scope of this textual comparison.

    Args:
        expected_summary: The expected outcome from the task objective
        observed_summary: The actual observed result summary

    Returns:
        Tuple of (objective_addressed, objective_addressed_is_observed)
        - objective_addressed: True if TEXTUAL MATCH suggests objective was addressed
        - objective_addressed_is_observed: ALWAYS False (requires external world validation)

    Examples:
        >>> extract_objective_evidence(expected_summary="file created", observed_summary="file created successfully")
        (True, False)  # TEXTUAL MATCH but NOT INDEPENDENT OBSERVATION

        >>> extract_objective_evidence(expected_summary="", observed_summary="file created")
        (False, False)

        >>> extract_objective_evidence(expected_summary="file created", observed_summary="error occurred")
        (False, False)
    """
    # No expected outcome: cannot establish objective evidence
    if not expected_summary or not expected_summary.strip():
        return False, False

    # No observed summary: cannot establish objective evidence
    if not observed_summary or not observed_summary.strip():
        return False, False

    # Conservative deterministic containment check
    # If the expected outcome text appears in the observed summary,
    # consider it as TEXTUAL EVIDENCE that the objective was addressed.
    # This is NOT independent observation - it's just textual match.
    expected_normalized = expected_summary.strip().lower()
    observed_normalized = observed_summary.strip().lower()

    # Check for direct containment (conservative)
    if expected_normalized in observed_normalized:
        return True, False  # TEXTUAL MATCH but NOT INDEPENDENT OBSERVATION

    # No deterministic evidence found
    return False, False
