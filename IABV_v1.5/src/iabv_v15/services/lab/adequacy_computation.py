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
    evidence_source: str = "",
    observer_identity: str = "",
    evidence_reference: str = "",
) -> Tuple[AdequacyClassification, str]:
    """Compute adequacy classification based on objective evidence.

    This is a conservative gate for learning eligibility. It requires:
    1. Expected objective is defined
    2. Objective was independently observed as addressed
    3. Evidence is from a verifiable provenance-bearing source
    4. Evidence is not merely caller assertion

    Epistemic semantics:
    - TEXTUAL_MATCH: expected text appears in observed text
    - INDEPENDENT_OBSERVATION: evidence from external world validation with provenance
    - OBJECTIVE_VALIDATION: objective was actually satisfied in the world
    - LEARNING_ELIGIBILITY: adequate for learning from this outcome

    CRITICAL: CALLER_SUPPLIED_TRUE != INDEPENDENT_OBSERVATION
    A caller passing objective_addressed=True, objective_addressed_is_observed=True
    WITHOUT providing evidence_source, observer_identity, or evidence_reference
    is treated as FORGED ASSERTION and rejected.

    Args:
        expected_summary: The expected outcome from task objective
        observed_summary: The actual observed result summary
        success: Execution success status (NOT sufficient for objective validation)
        precision: Model precision (NOT sufficient for objective validation)
        robustness: Execution robustness (NOT sufficient for objective validation)
        user_progress: User-reported progress (NOT sufficient for objective validation)
        objective_addressed: Whether objective appears to be addressed
        objective_addressed_is_observed: Whether evidence is independently observed
        evidence_source: Source of observation (e.g., "filesystem", "browser", "test_runner")
        observer_identity: Identity of observer (e.g., "pytest", "playwright", "user")
        evidence_reference: Reference to verifiable evidence artifact (e.g., test_id, file_path)

    Returns:
        Tuple of (classification, reason)
    """
    # No expected objective: cannot establish adequacy
    if not expected_summary or not expected_summary.strip():
        return AdequacyClassification.INCONCLUSIVE, "no expected objective defined"

    # Caller assertion without independent observation is rejected
    if objective_addressed and not objective_addressed_is_observed:
        return AdequacyClassification.INCONCLUSIVE, "caller assertion without independent observation"

    # Caller-supplied True/True WITHOUT provenance is FORGED ASSERTION
    # This prevents: caller → True, True → ADEQUATE (the Codex finding)
    if objective_addressed and objective_addressed_is_observed:
        # Require at least one provenance marker to accept the observation
        has_provenance = bool(evidence_source) or bool(observer_identity) or bool(evidence_reference)
        if not has_provenance:
            return AdequacyClassification.INCONCLUSIVE, "caller-supplied observation without verifiable provenance (forged assertion)"
        # With provenance, accept as independently observed
        return AdequacyClassification.ADEQUATE, "independently observed objective addressed with provenance"

    # No independent observation: not adequate for learning
    # Even if success=True, precision=high, etc., without objective evidence
    # we cannot claim learning eligibility
    return AdequacyClassification.NOT_ADEQUATE, "no independent observation of objective addressed"
