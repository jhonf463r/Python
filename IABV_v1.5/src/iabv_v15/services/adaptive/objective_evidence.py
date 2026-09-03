"""Conservative objective evidence extraction for adequacy computation.

This module provides the smallest deterministic evidence extraction
required to determine whether a task's declared objective was
independently observed as satisfied.

DO NOT introduce LLM evaluation or probabilistic reasoning.
This is conservative deterministic comparison only.
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

    The logic is:
    1. If expected_summary is empty/missing: no evidence (False, False)
    2. If expected_summary exists and observed_summary contains deterministic
       textual evidence supporting it: (True, True)
    3. If expected_summary exists but cannot be deterministically established:
       (False, False)

    Args:
        expected_summary: The expected outcome from the task objective
        observed_summary: The actual observed result summary

    Returns:
        Tuple of (objective_addressed, objective_addressed_is_observed)
        - objective_addressed: True if evidence suggests objective was addressed
        - objective_addressed_is_observed: True if evidence is independently observed

    Examples:
        >>> extract_objective_evidence(expected_summary="file created", observed_summary="file created successfully")
        (True, True)

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
    # consider it as evidence that the objective was addressed.
    # This is conservative because it requires explicit textual presence.
    expected_normalized = expected_summary.strip().lower()
    observed_normalized = observed_summary.strip().lower()

    # Check for direct containment (conservative)
    if expected_normalized in observed_normalized:
        return True, True

    # No deterministic evidence found
    return False, False
