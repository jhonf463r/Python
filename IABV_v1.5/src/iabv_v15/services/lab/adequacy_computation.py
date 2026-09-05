"""Adequacy computation for learning eligibility.

This module provides conservative adequacy classification based on
objective evidence. It distinguishes between TEXTUAL MATCH and
INDEPENDENT OBJECTIVE VALIDATION.

Epistemic rule: TEXTUAL_CONTAINMENT != OBJECTIVE_WORLD_EVIDENCE
"""

from enum import Enum
from typing import Tuple


class AdequacyClassification(Enum):
    """Classification of learning adequacy."""
    ADEQUATE = "ADEQUATE"
    NOT_ADEQUATE = "NOT_ADEQUATE"
    INCONCLUSIVE = "INCONCLUSIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def compute_adequacy(
    *,
    expected_summary: str = "",
    observed_summary: str = "",
    success: bool = False,
    precision: float = 0.0,
    robustness: float = 0.0,
    user_progress: float = 0.0,
    objective_addressed: bool = False,
    objective_addressed_is_observed: bool = False,
) -> Tuple[AdequacyClassification, str]:
    """Compute adequacy classification based on objective evidence.

    This is a conservative gate for learning eligibility. It requires:
    1. Expected objective is defined
    2. Objective was independently observed as addressed
    3. Evidence is not merely caller assertion

    Epistemic semantics:
    - TEXTUAL_MATCH: expected text appears in observed text
    - INDEPENDENT_OBSERVATION: evidence from external world validation
    - OBJECTIVE_VALIDATION: objective was actually satisfied in the world
    - LEARNING_ELIGIBILITY: adequate for learning from this outcome

    Args:
        expected_summary: The expected outcome from task objective
        observed_summary: The actual observed result summary
        success: Execution success status (NOT sufficient for objective validation)
        precision: Model precision (NOT sufficient for objective validation)
        robustness: Execution robustness (NOT sufficient for objective validation)
        user_progress: User-reported progress (NOT sufficient for objective validation)
        objective_addressed: Whether objective appears to be addressed
        objective_addressed_is_observed: Whether evidence is independently observed

    Returns:
        Tuple of (classification, reason)
    """
    # No expected objective: cannot establish adequacy
    if not expected_summary or not expected_summary.strip():
        return AdequacyClassification.INCONCLUSIVE, "no expected objective defined"

    # Caller assertion without independent observation is rejected
    if objective_addressed and not objective_addressed_is_observed:
        return AdequacyClassification.INCONCLUSIVE, "caller assertion without independent observation"

    # Independent observation of objective addressed: adequate for learning
    if objective_addressed and objective_addressed_is_observed:
        return AdequacyClassification.ADEQUATE, "independently observed objective addressed"

    # No independent observation: not adequate for learning
    # Even if success=True, precision=high, etc., without objective evidence
    # we cannot claim learning eligibility
    return AdequacyClassification.NOT_ADEQUATE, "no independent observation of objective addressed"
