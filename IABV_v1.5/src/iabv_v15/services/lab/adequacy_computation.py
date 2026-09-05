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
    2. Objective was independently observed as addressed by a VERIFIED source
    3. Evidence is from a verifiable provenance-bearing source (NOT caller-supplied strings)
    4. Evidence is not merely caller assertion

    Epistemic semantics:
    - TEXTUAL_MATCH: expected text appears in observed text
    - INDEPENDENT_OBSERVATION: evidence from external world validation with VERIFIED provenance
    - OBJECTIVE_VALIDATION: objective was actually satisfied in the world
    - LEARNING_ELIGIBILITY: adequate for learning from this outcome

    CRITICAL EPISTEMIC RULES:
    - CALLER_SUPPLIED_TRUE != INDEPENDENT_OBSERVATION
    - PROVENANCE_METADATA != VERIFIED_PROVENANCE
    - DECLARED_EVIDENCE != VERIFIED_EVIDENCE

    A caller passing objective_addressed=True, objective_addressed_is_observed=True
    WITH ANY caller-supplied strings (evidence_source, observer_identity, evidence_reference)
    is treated as DECLARED_PROVENANCE, NOT VERIFIED_PROVENANCE, and is rejected.

    ADEQUATE is NOT REACHABLE in this PR scope because:
    - No verified observation producer exists in the IABV architecture that can be
      directly reused without extending scope
    - PerceptionGroundTruthComparator exists but requires injection of services
      and does not produce a verified observation object
    - PerceptionCrossValidator exists but is a cross-validation service, not
      a verified evidence producer
    - Integrating these would require architectural changes outside PR #452 scope

    Future path (NOT implemented in this PR):
    REAL WORLD
    → EXISTING PERCEPTION / GROUND TRUTH (PerceptionGroundTruthComparator)
    → VERIFIED OBSERVATION
    → ADEQUACY
    → LEARNING ELIGIBILITY

    Args:
        expected_summary: The expected outcome from task objective
        observed_summary: The actual observed result summary
        success: Execution success status (NOT sufficient for objective validation)
        precision: Model precision (NOT sufficient for objective validation)
        robustness: Execution robustness (NOT sufficient for objective validation)
        user_progress: User-reported progress (NOT sufficient for objective validation)
        objective_addressed: Whether objective appears to be addressed
        objective_addressed_is_observed: Whether evidence is independently observed
        evidence_source: DECLARED source of observation (NOT verified)
        observer_identity: DECLARED identity of observer (NOT verified)
        evidence_reference: DECLARED reference to evidence artifact (NOT verified)

    Returns:
        Tuple of (classification, reason)
    """
    # No expected objective: cannot establish adequacy
    if not expected_summary or not expected_summary.strip():
        return AdequacyClassification.INCONCLUSIVE, "no expected objective defined"

    # Caller assertion without independent observation is rejected
    if objective_addressed and not objective_addressed_is_observed:
        return AdequacyClassification.INCONCLUSIVE, "caller assertion without independent observation"

    # Caller-supplied True/True is ALWAYS rejected in this PR scope
    # Even with provenance metadata, these are DECLARED strings, not VERIFIED evidence
    # PROVENANCE_METADATA != VERIFIED_PROVENANCE
    if objective_addressed and objective_addressed_is_observed:
        # Check if caller supplied any provenance metadata
        has_declared_provenance = bool(evidence_source) or bool(observer_identity) or bool(evidence_reference)
        if has_declared_provenance:
            # Caller supplied metadata, but it's DECLARED, not VERIFIED
            return AdequacyClassification.INCONCLUSIVE, "caller-supplied provenance metadata is DECLARED, not VERIFIED (ADEQUATE not reachable in this PR scope)"
        # No provenance at all
        return AdequacyClassification.INCONCLUSIVE, "caller-supplied observation without verifiable provenance (ADEQUATE not reachable in this PR scope)"

    # No independent observation: not adequate for learning
    # Even if success=True, precision=high, etc., without objective evidence
    # we cannot claim learning eligibility
    return AdequacyClassification.NOT_ADEQUATE, "no independent observation of objective addressed"
