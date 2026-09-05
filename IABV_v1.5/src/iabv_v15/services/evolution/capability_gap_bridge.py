"""Capability gap bridge: minimal adapter to project capability gaps from existing state.

This is NOT a new service. It is a simple function that composes existing
self-model data (EnvironmentSelfAwarenessService, CapabilityReadinessService)
into a structured capability gap representation that can be consumed by
ControlMasterService for next-best-work recommendation.

Design principle: state-based, not time-based. The bridge only projects
what is already known; it does not perform new observations.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from iabv_v15.domain.models import CapabilityStatus


class Freshness:
    """Freshness classification for evidence."""
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class CapabilityGapStatus:
    """Status classification for capability gaps."""
    MISSING = "MISSING"
    DEGRADED = "DEGRADED"
    UNCERTAIN = "UNCERTAIN"
    AVAILABLE = "AVAILABLE"


def classify_freshness(
    *,
    last_validated_at_utc: str | None,
    reference_time: datetime | None = None,
    max_freshness_seconds: float = 3600.0,
) -> str:
    """Classify evidence freshness based on validation timestamp.
    
    Args:
        last_validated_at_utc: ISO timestamp of last validation, or None
        reference_time: Reference time for freshness calculation (deterministic if provided)
        max_freshness_seconds: Maximum age for evidence to be considered fresh
        
    Returns:
        One of Freshness.FRESH, Freshness.STALE, or Freshness.UNKNOWN
    """
    if last_validated_at_utc is None:
        return Freshness.UNKNOWN
    
    try:
        last_validated = datetime.fromisoformat(last_validated_at_utc.replace('Z', '+00:00'))
        if last_validated.tzinfo is None:
            last_validated = last_validated.replace(tzinfo=timezone.utc)
        
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        elif reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        
        age = reference_time - last_validated
        if age.total_seconds() <= max_freshness_seconds:
            return Freshness.FRESH
        return Freshness.STALE
    except Exception:
        return Freshness.UNKNOWN


def project_capability_gaps(
    *,
    environment_self_model: dict[str, Any] | None = None,
    capability_readiness: list[dict[str, Any]] | None = None,
    tool_cards: dict[str, dict[str, Any]] | None = None,
    reference_time: datetime | None = None,
    max_freshness_seconds: float = 3600.0,
) -> list[dict[str, Any]]:
    """Project capability gaps from existing self-model data.
    
    This function composes data from multiple existing sources into a unified
    capability gap representation. It does NOT perform new observations.
    
    Args:
        environment_self_model: Data from EnvironmentSelfAwarenessService.current_model()
        capability_readiness: Data from CapabilityReadinessService.evaluate()
        tool_cards: Tool card data with availability and freshness information
        reference_time: Reference time for freshness calculation (deterministic if provided)
        max_freshness_seconds: Maximum age for evidence to be considered fresh
        
    Returns:
        List of capability gap projections with structure:
        {
            "capability": str,
            "status": "MISSING|DEGRADED|UNCERTAIN|AVAILABLE",
            "reason": str,
            "evidence_refs": list[str],
            "freshness": "fresh|stale|unknown",
            "heuristic_score": float,
            "provenance": {
                "source": str,
                "timestamp": str | None,
                "evidence_type": str,
            }
        }
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    
    gaps: list[dict[str, Any]] = []
    
    # Process tool cards (primary source for capability availability)
    if tool_cards:
        for tool_id, card in tool_cards.items():
            available = card.get('available')
            last_validated = card.get('last_validated_at_utc')
            freshness = classify_freshness(
                last_validated_at_utc=last_validated,
                reference_time=reference_time,
                max_freshness_seconds=max_freshness_seconds,
            )
            
            # Determine status based on availability and freshness
            if freshness == Freshness.UNKNOWN:
                status = CapabilityGapStatus.UNCERTAIN
                reason = "No validation timestamp available - cannot determine current state"
            elif freshness == Freshness.STALE:
                status = CapabilityGapStatus.UNCERTAIN
                reason = "Evidence is stale - current state unknown"
            else:  # FRESH
                if available is True:
                    status = CapabilityGapStatus.AVAILABLE
                    reason = "Fresh evidence confirms availability"
                elif available is False:
                    status = CapabilityGapStatus.MISSING
                    reason = "Fresh evidence confirms unavailability"
                else:
                    status = CapabilityGapStatus.UNCERTAIN
                    reason = "Availability field is missing or ambiguous"
            
            # Build provenance - do NOT fabricate timestamp
            provenance = {
                'source': 'tool_card',
                'timestamp': last_validated,  # None if missing, not fabricated
                'evidence_type': 'persisted_tool_card',
            }
            
            # Calculate heuristic score based on freshness (NOT calibrated probability)
            if freshness == Freshness.FRESH:
                heuristic_score = 0.9 if available is not None else 0.5
            elif freshness == Freshness.STALE:
                heuristic_score = 0.4
            else:  # UNKNOWN
                heuristic_score = 0.2
            
            gap = {
                'capability': tool_id,
                'status': status,
                'reason': reason,
                'evidence_refs': [f'tool_card:{tool_id}'],
                'freshness': freshness,
                'heuristic_score': heuristic_score,
                'provenance': provenance,
            }
            gaps.append(gap)
    
    # Process capability readiness (secondary source for domain-specific capabilities)
    if capability_readiness:
        for cap in capability_readiness:
            capability_id = cap.get('capability_id')
            status = cap.get('status')
            score = cap.get('score', 0.0)
            evidence = cap.get('evidence', [])
            
            # Map CapabilityStatus to gap status
            if status == CapabilityStatus.READY.value:
                gap_status = CapabilityGapStatus.AVAILABLE
                reason = "Capability readiness service reports READY"
            elif status == CapabilityStatus.READY_WITH_APPROVAL.value:
                gap_status = CapabilityGapStatus.DEGRADED
                reason = "Capability available but requires approval"
            elif status == CapabilityStatus.PARTIAL.value:
                gap_status = CapabilityGapStatus.DEGRADED
                reason = "Capability partially available"
            elif status == CapabilityStatus.INSUFFICIENT.value:
                gap_status = CapabilityGapStatus.MISSING
                reason = "Capability readiness service reports INSUFFICIENT"
            else:
                gap_status = CapabilityGapStatus.UNCERTAIN
                reason = f"Unknown capability status: {status}"
            
            # Build provenance - propagate existing metadata, do NOT fabricate
            # If source doesn't provide timestamp/type, mark as unknown
            provenance = {
                'source': 'capability_readiness_service',
                'timestamp': cap.get('last_updated_at_utc'),  # Propagate if exists
                'evidence_type': 'derived',  # Derived from service evaluation, not direct observation
            }
            
            gap = {
                'capability': capability_id,
                'status': gap_status,
                'reason': reason,
                'evidence_refs': evidence[:3],  # Limit to top 3 evidence refs
                'freshness': Freshness.FRESH,  # Service evaluation is fresh by definition
                'heuristic_score': min(score + 0.1, 1.0),  # Use service score as heuristic
                'provenance': provenance,
            }
            gaps.append(gap)
    
    # Process environment self-model (tertiary source for infrastructure capabilities)
    if environment_self_model:
        model = environment_self_model
        model_timestamp = model.get('last_scan_at_utc')
        model_freshness = classify_freshness(
            last_validated_at_utc=model_timestamp,
            reference_time=reference_time,
            max_freshness_seconds=max_freshness_seconds,
        )
        
        # Check for critical infrastructure gaps
        gpu_info = model.get('gpu', {})
        gpu_available = gpu_info.get('available') if gpu_info else None
        
        if gpu_available is False:
            # GPU explicitly marked as unavailable
            if model_freshness == Freshness.FRESH:
                status = CapabilityGapStatus.MISSING
                reason = 'GPU not available (fresh scan confirms)'
            elif model_freshness == Freshness.STALE:
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'GPU unavailable data is stale - current state unknown'
            else:  # UNKNOWN
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'GPU scan timestamp missing - cannot determine current state'
            
            gap = {
                'capability': 'gpu_compute',
                'status': status,
                'reason': reason,
                'evidence_refs': ['environment_self_model:gpu'],
                'freshness': model_freshness,
                'heuristic_score': 0.8 if model_freshness == Freshness.FRESH else 0.4,
                'provenance': {
                    'source': 'environment_self_awareness_service',
                    'timestamp': model_timestamp,  # None if missing
                    'evidence_type': 'derived',  # Derived from persisted model
                },
            }
            gaps.append(gap)
        elif not gpu_info or gpu_available is None:
            # GPU info missing or availability unknown
            if model_freshness == Freshness.FRESH:
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'GPU not detected in environment (fresh scan, but availability unknown)'
            elif model_freshness == Freshness.STALE:
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'GPU scan data is stale - current state unknown'
            else:  # UNKNOWN
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'GPU scan timestamp missing - cannot determine current state'
            
            gap = {
                'capability': 'gpu_compute',
                'status': status,
                'reason': reason,
                'evidence_refs': ['environment_self_model:gpu'],
                'freshness': model_freshness,
                'heuristic_score': 0.5 if model_freshness == Freshness.FRESH else 0.4,
                'provenance': {
                    'source': 'environment_self_awareness_service',
                    'timestamp': model_timestamp,  # None if missing
                    'evidence_type': 'derived',  # Derived from persisted model
                },
            }
            gaps.append(gap)
        
        # Check RAM pressure
        ram_info = model.get('ram', {})
        ram_pressure = ram_info.get('pressure')
        if ram_pressure in ('critical', 'high'):
            # Apply freshness discipline
            if model_freshness == Freshness.FRESH:
                status = CapabilityGapStatus.DEGRADED
                reason = f'RAM pressure is {ram_pressure} - may affect performance (fresh scan)'
            elif model_freshness == Freshness.STALE:
                status = CapabilityGapStatus.UNCERTAIN
                reason = f'RAM pressure data is stale - current state unknown (was {ram_pressure})'
            else:  # UNKNOWN
                status = CapabilityGapStatus.UNCERTAIN
                reason = 'RAM scan timestamp missing - cannot determine current state'
            
            gap = {
                'capability': 'ram_capacity',
                'status': status,
                'reason': reason,
                'evidence_refs': ['environment_self_model:ram'],
                'freshness': model_freshness,
                'heuristic_score': 0.9 if model_freshness == Freshness.FRESH else 0.4,
                'provenance': {
                    'source': 'environment_self_awareness_service',
                    'timestamp': model_timestamp,  # None if missing
                    'evidence_type': 'derived',  # Derived from persisted model
                },
            }
            gaps.append(gap)
    
    return gaps


def convert_gap_to_work_candidate(gap: dict[str, Any]) -> dict[str, Any]:
    """Convert a capability gap into a work candidate compatible with ControlMasterService.
    
    This is a COMPATIBLE PROJECTION: the output format matches ControlMasterService
    work items, but there is no actual integration/consumer yet.
    
    Args:
        gap: Capability gap from project_capability_gaps()
        
    Returns:
        Work candidate with format compatible with ControlMasterService.current_work_queue()
    """
    status = gap.get('status')
    
    # Map gap status to work item status
    if status == CapabilityGapStatus.MISSING:
        work_status = 'needs_implementation'
        next_action = f"Implement missing capability: {gap['capability']}"
        score_components = {'capability_missing': 80, 'base': 10}
    elif status == CapabilityGapStatus.DEGRADED:
        work_status = 'needs_improvement'
        next_action = f"Improve degraded capability: {gap['capability']}"
        score_components = {'capability_degraded': 60, 'base': 10}
    elif status == CapabilityGapStatus.UNCERTAIN:
        work_status = 'needs_validation'
        next_action = f"Validate uncertain capability: {gap['capability']}"
        score_components = {'capability_uncertain': 40, 'base': 10}
    else:  # AVAILABLE
        work_status = 'available'
        next_action = f"Capability available: {gap['capability']}"
        score_components = {'capability_available': 0, 'base': 0}
    
    return {
        'id': f"capability_gap:{gap['capability']}",
        'title': f"Capability Gap: {gap['capability']} ({status})",
        'status': work_status,
        'source': 'capability_gap_bridge',
        'evidence_refs': gap.get('evidence_refs', []),
        'next_action': next_action,
        'acceptance_tests': [
            f"Validate {gap['capability']} is operational",
            f"Confirm {gap['capability']} meets requirements",
        ],
        'dependencies': '',
        'parallelizable': True,
        'updated_at': gap.get('provenance', {}).get('timestamp') or reference_time.isoformat() if 'reference_time' in locals() else '',
        'reason': gap.get('reason', ''),
        'score_breakdown': score_components,
        'metadata': {
            'capability': gap['capability'],
            'gap_status': status,
            'freshness': gap.get('freshness'),
            'heuristic_score': gap.get('heuristic_score'),
            'provenance': gap.get('provenance'),
        },
    }


def build_decision_record(
    *,
    recommended_work: dict[str, Any],
    capability_gap: dict[str, Any] | None = None,
    evidence: list[str] | None = None,
    blocked_by: list[str] | None = None,
    resource_constraints: dict[str, Any] | None = None,
    heuristic_score: float = 0.5,
    alternatives: list[dict[str, Any]] | None = None,
    decision_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build an explicit decision record for next-best-work recommendation.
    
    This provides traceability for why a particular work item was recommended.
    Separates decision timestamp from evidence timestamps.
    
    Args:
        recommended_work: The work candidate being recommended
        capability_gap: The capability gap that motivated this recommendation
        evidence: Evidence supporting the recommendation
        blocked_by: Items that block this work
        resource_constraints: Resource limitations affecting this work
        heuristic_score: Heuristic score for this recommendation (NOT calibrated probability)
        alternatives: Alternative work items considered
        decision_timestamp: When this decision was made (deterministic if provided)
        
    Returns:
        Decision record with full provenance and justification
    """
    if decision_timestamp is None:
        decision_timestamp = datetime.now(timezone.utc)
    elif decision_timestamp.tzinfo is None:
        decision_timestamp = decision_timestamp.replace(tzinfo=timezone.utc)
    
    return {
        'recommended_work': recommended_work,
        'reason': recommended_work.get('reason', ''),
        'capability_gap': capability_gap or {},
        'evidence': evidence or [],
        'blocked_by': blocked_by or [],
        'resource_constraints': resource_constraints or {},
        'heuristic_score': heuristic_score,  # Renamed from confidence to avoid false calibration claim
        'alternatives': alternatives or [],
        'decision_timestamp': decision_timestamp.isoformat(),  # When decision was made
        'evidence_timestamps': [  # When underlying evidence was observed
            capability_gap.get('provenance', {}).get('timestamp') if capability_gap else None,
        ],
        'provenance': {
            'source': 'capability_gap_bridge',
            'decision_type': 'next_best_work',
        },
    }
