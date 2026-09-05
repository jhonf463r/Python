"""Tests for capability gap bridge - minimal adapter for self-diagnosis and next-best-work.

Tests cover:
A. fresh evidence → correctly classified
B. stale evidence → not represented as fresh
C. unknown evidence → stays unknown
D. capability state → capability gap projection
E. capability gap → work candidate without creating new queue
F. identical inputs → deterministic result
G. missing evidence → no false confidence
"""

from datetime import datetime, timezone, timedelta

import pytest

from iabv_v15.services.evolution.capability_gap_bridge import (
    Freshness,
    CapabilityGapStatus,
    classify_freshness,
    project_capability_gaps,
    convert_gap_to_work_candidate,
    build_decision_record,
)


class TestFreshnessClassification:
    """Test A: fresh evidence → correctly classified."""
    
    def test_fresh_evidence_classified_as_fresh(self) -> None:
        """Fresh evidence (within max_freshness_seconds) is classified as FRESH."""
        now = datetime.now(timezone.utc)
        last_validated = (now - timedelta(seconds=300)).isoformat()  # 5 minutes ago
        
        result = classify_freshness(last_validated_at_utc=last_validated)
        assert result == Freshness.FRESH
    
    def test_fresh_boundary_case(self) -> None:
        """Evidence just under max_freshness_seconds boundary is classified as FRESH."""
        now = datetime.now(timezone.utc)
        last_validated = (now - timedelta(seconds=3599)).isoformat()  # Just under 1 hour
        
        result = classify_freshness(
            last_validated_at_utc=last_validated,
            max_freshness_seconds=3600.0,
        )
        assert result == Freshness.FRESH


class TestStaleEvidence:
    """Test B: stale evidence → not represented as fresh."""
    
    def test_stale_evidence_classified_as_stale(self) -> None:
        """Stale evidence (beyond max_freshness_seconds) is classified as STALE."""
        now = datetime.now(timezone.utc)
        last_validated = (now - timedelta(seconds=7200)).isoformat()  # 2 hours ago
        
        result = classify_freshness(last_validated_at_utc=last_validated)
        assert result == Freshness.STALE
    
    def test_stale_boundary_case(self) -> None:
        """Evidence just beyond max_freshness_seconds is classified as STALE."""
        now = datetime.now(timezone.utc)
        last_validated = (now - timedelta(seconds=3601)).isoformat()  # Just over 1 hour
        
        result = classify_freshness(
            last_validated_at_utc=last_validated,
            max_freshness_seconds=3600.0,
        )
        assert result == Freshness.STALE


class TestUnknownEvidence:
    """Test C: unknown evidence → stays unknown."""
    
    def test_null_timestamp_classified_as_unknown(self) -> None:
        """Missing timestamp (None) is classified as UNKNOWN."""
        result = classify_freshness(last_validated_at_utc=None)
        assert result == Freshness.UNKNOWN
    
    def test_invalid_timestamp_classified_as_unknown(self) -> None:
        """Invalid timestamp format is classified as UNKNOWN."""
        result = classify_freshness(last_validated_at_utc="invalid-timestamp")
        assert result == Freshness.UNKNOWN
    
    def test_empty_string_timestamp_classified_as_unknown(self) -> None:
        """Empty string timestamp is classified as UNKNOWN."""
        result = classify_freshness(last_validated_at_utc="")
        assert result == Freshness.UNKNOWN


class TestCapabilityGapProjection:
    """Test D: capability state → capability gap projection."""
    
    def test_available_capability_with_fresh_evidence(self) -> None:
        """Available capability with fresh evidence is projected as AVAILABLE."""
        tool_cards = {
            'mcp_client': {
                'available': True,
                'last_validated_at_utc': datetime.now(timezone.utc).isoformat(),
            }
        }
        
        gaps = project_capability_gaps(tool_cards=tool_cards)
        assert len(gaps) == 1
        assert gaps[0]['capability'] == 'mcp_client'
        assert gaps[0]['status'] == CapabilityGapStatus.AVAILABLE
        assert gaps[0]['freshness'] == Freshness.FRESH
        assert gaps[0]['confidence'] >= 0.8
    
    def test_missing_capability_with_fresh_evidence(self) -> None:
        """Missing capability with fresh evidence is projected as MISSING."""
        tool_cards = {
            'mcp_client': {
                'available': False,
                'last_validated_at_utc': datetime.now(timezone.utc).isoformat(),
            }
        }
        
        gaps = project_capability_gaps(tool_cards=tool_cards)
        assert len(gaps) == 1
        assert gaps[0]['capability'] == 'mcp_client'
        assert gaps[0]['status'] == CapabilityGapStatus.MISSING
        assert gaps[0]['freshness'] == Freshness.FRESH
        assert gaps[0]['confidence'] >= 0.8
    
    def test_stale_available_capability_is_uncertain(self) -> None:
        """Available capability with stale evidence is projected as UNCERTAIN."""
        now = datetime.now(timezone.utc)
        last_validated = (now - timedelta(seconds=7200)).isoformat()  # 2 hours ago
        
        tool_cards = {
            'mcp_client': {
                'available': True,
                'last_validated_at_utc': last_validated,
            }
        }
        
        gaps = project_capability_gaps(tool_cards=tool_cards)
        assert len(gaps) == 1
        assert gaps[0]['status'] == CapabilityGapStatus.UNCERTAIN
        assert gaps[0]['freshness'] == Freshness.STALE
        assert gaps[0]['confidence'] <= 0.5
    
    def test_capability_readiness_integration(self) -> None:
        """Capability readiness data is integrated into gap projection."""
        from iabv_v15.domain.models import CapabilityStatus
        
        capability_readiness = [
            {
                'capability_id': 'wplay.login',
                'status': CapabilityStatus.READY.value,
                'score': 0.94,
                'evidence': ['login_detected', 'visual_complete'],
            }
        ]
        
        gaps = project_capability_gaps(capability_readiness=capability_readiness)
        assert len(gaps) == 1
        assert gaps[0]['capability'] == 'wplay.login'
        assert gaps[0]['status'] == CapabilityGapStatus.AVAILABLE
        assert gaps[0]['freshness'] == Freshness.FRESH
        assert 'login_detected' in gaps[0]['evidence_refs']
    
    def test_environment_self_model_integration(self) -> None:
        """Environment self-model data is integrated into gap projection."""
        environment_self_model = {
            'gpu': {'available': False},
            'ram': {'pressure': 'critical'},
        }
        
        gaps = project_capability_gaps(environment_self_model=environment_self_model)
        assert len(gaps) >= 2
        
        gpu_gap = next((g for g in gaps if g['capability'] == 'gpu_compute'), None)
        assert gpu_gap is not None
        assert gpu_gap['status'] in (CapabilityGapStatus.MISSING, CapabilityGapStatus.UNCERTAIN)
        
        ram_gap = next((g for g in gaps if g['capability'] == 'ram_capacity'), None)
        assert ram_gap is not None
        assert ram_gap['status'] == CapabilityGapStatus.DEGRADED


class TestWorkCandidateConversion:
    """Test E: capability gap → work candidate without creating new queue."""
    
    def test_missing_gap_converts_to_implementation_work(self) -> None:
        """MISSING capability gap converts to needs_implementation work candidate."""
        gap = {
            'capability': 'mcp_client',
            'status': CapabilityGapStatus.MISSING,
            'reason': 'Fresh evidence confirms unavailability',
            'evidence_refs': ['tool_card:mcp_client'],
            'freshness': Freshness.FRESH,
            'confidence': 0.9,
            'provenance': {'source': 'tool_card'},
        }
        
        candidate = convert_gap_to_work_candidate(gap)
        assert candidate['status'] == 'needs_implementation'
        assert candidate['source'] == 'capability_gap_bridge'
        assert 'Implement missing capability' in candidate['next_action']
        assert candidate['score_breakdown']['capability_missing'] == 80
    
    def test_degraded_gap_converts_to_improvement_work(self) -> None:
        """DEGRADED capability gap converts to needs_improvement work candidate."""
        gap = {
            'capability': 'gpu_compute',
            'status': CapabilityGapStatus.DEGRADED,
            'reason': 'RAM pressure is critical',
            'evidence_refs': ['environment_self_model:ram'],
            'freshness': Freshness.FRESH,
            'confidence': 0.9,
            'provenance': {'source': 'environment_self_awareness_service'},
        }
        
        candidate = convert_gap_to_work_candidate(gap)
        assert candidate['status'] == 'needs_improvement'
        assert 'Improve degraded capability' in candidate['next_action']
        assert candidate['score_breakdown']['capability_degraded'] == 60
    
    def test_uncertain_gap_converts_to_validation_work(self) -> None:
        """UNCERTAIN capability gap converts to needs_validation work candidate."""
        gap = {
            'capability': 'mcp_client',
            'status': CapabilityGapStatus.UNCERTAIN,
            'reason': 'Evidence is stale - current state unknown',
            'evidence_refs': ['tool_card:mcp_client'],
            'freshness': Freshness.STALE,
            'confidence': 0.4,
            'provenance': {'source': 'tool_card'},
        }
        
        candidate = convert_gap_to_work_candidate(gap)
        assert candidate['status'] == 'needs_validation'
        assert 'Validate uncertain capability' in candidate['next_action']
        assert candidate['score_breakdown']['capability_uncertain'] == 40
    
    def test_available_gap_has_low_priority(self) -> None:
        """AVAILABLE capability gap converts to available work with low priority."""
        gap = {
            'capability': 'wplay.login',
            'status': CapabilityGapStatus.AVAILABLE,
            'reason': 'Fresh evidence confirms availability',
            'evidence_refs': ['tool_card:wplay.login'],
            'freshness': Freshness.FRESH,
            'confidence': 0.9,
            'provenance': {'source': 'tool_card'},
        }
        
        candidate = convert_gap_to_work_candidate(gap)
        assert candidate['status'] == 'available'
        assert candidate['score_breakdown']['capability_available'] == 0
        assert candidate['score_breakdown']['base'] == 0
    
    def test_work_candidate_preserves_provenance(self) -> None:
        """Work candidate preserves provenance from capability gap."""
        gap = {
            'capability': 'mcp_client',
            'status': CapabilityGapStatus.MISSING,
            'reason': 'Fresh evidence confirms unavailability',
            'evidence_refs': ['tool_card:mcp_client'],
            'freshness': Freshness.FRESH,
            'confidence': 0.9,
            'provenance': {
                'source': 'tool_card',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'evidence_type': 'persisted_tool_card',
            },
        }
        
        candidate = convert_gap_to_work_candidate(gap)
        assert candidate['metadata']['provenance'] == gap['provenance']
        assert candidate['metadata']['freshness'] == gap['freshness']
        assert candidate['metadata']['confidence'] == gap['confidence']


class TestDeterminism:
    """Test F: identical inputs → deterministic result."""
    
    def test_identical_inputs_produce_identical_gaps(self) -> None:
        """Identical inputs produce identical capability gaps."""
        tool_cards = {
            'mcp_client': {
                'available': False,
                'last_validated_at_utc': datetime.now(timezone.utc).isoformat(),
            }
        }
        
        gaps1 = project_capability_gaps(tool_cards=tool_cards)
        gaps2 = project_capability_gaps(tool_cards=tool_cards)
        
        assert len(gaps1) == len(gaps2)
        assert gaps1[0]['capability'] == gaps2[0]['capability']
        assert gaps1[0]['status'] == gaps2[0]['status']
        assert gaps1[0]['freshness'] == gaps2[0]['freshness']
    
    def test_identical_gaps_produce_identical_candidates(self) -> None:
        """Identical gaps produce identical work candidates."""
        gap = {
            'capability': 'mcp_client',
            'status': CapabilityGapStatus.MISSING,
            'reason': 'Fresh evidence confirms unavailability',
            'evidence_refs': ['tool_card:mcp_client'],
            'freshness': Freshness.FRESH,
            'confidence': 0.9,
            'provenance': {'source': 'tool_card'},
        }
        
        candidate1 = convert_gap_to_work_candidate(gap)
        candidate2 = convert_gap_to_work_candidate(gap)
        
        assert candidate1['id'] == candidate2['id']
        assert candidate1['status'] == candidate2['status']
        assert candidate1['score_breakdown'] == candidate2['score_breakdown']


class TestFalseConfidencePrevention:
    """Test G: missing evidence → no false confidence."""
    
    def test_missing_timestamp_has_low_confidence(self) -> None:
        """Tool card with missing timestamp has low confidence."""
        tool_cards = {
            'mcp_client': {
                'available': True,
                'last_validated_at_utc': None,
            }
        }
        
        gaps = project_capability_gaps(tool_cards=tool_cards)
        assert gaps[0]['status'] == CapabilityGapStatus.UNCERTAIN
        assert gaps[0]['freshness'] == Freshness.UNKNOWN
        assert gaps[0]['confidence'] <= 0.3
    
    def test_stale_evidence_has_reduced_confidence(self) -> None:
        """Stale evidence has reduced confidence compared to fresh evidence."""
        now = datetime.now(timezone.utc)
        fresh_timestamp = now.isoformat()
        stale_timestamp = (now - timedelta(seconds=7200)).isoformat()
        
        tool_cards_fresh = {
            'mcp_client': {
                'available': True,
                'last_validated_at_utc': fresh_timestamp,
            }
        }
        tool_cards_stale = {
            'mcp_client': {
                'available': True,
                'last_validated_at_utc': stale_timestamp,
            }
        }
        
        gaps_fresh = project_capability_gaps(tool_cards=tool_cards_fresh)
        gaps_stale = project_capability_gaps(tool_cards=tool_cards_stale)
        
        assert gaps_fresh[0]['confidence'] > gaps_stale[0]['confidence']
    
    def test_ambiguous_availability_has_low_confidence(self) -> None:
        """Tool card with ambiguous availability field has low confidence."""
        tool_cards = {
            'mcp_client': {
                'available': None,  # Ambiguous
                'last_validated_at_utc': datetime.now(timezone.utc).isoformat(),
            }
        }
        
        gaps = project_capability_gaps(tool_cards=tool_cards)
        assert gaps[0]['status'] == CapabilityGapStatus.UNCERTAIN
        assert gaps[0]['confidence'] <= 0.5


class TestDecisionRecord:
    """Test decision record structure for traceability."""
    
    def test_decision_record_includes_all_required_fields(self) -> None:
        """Decision record includes all required fields for traceability."""
        recommended_work = {
            'id': 'capability_gap:mcp_client',
            'title': 'Capability Gap: mcp_client (MISSING)',
            'status': 'needs_implementation',
            'next_action': 'Implement missing capability: mcp_client',
        }
        capability_gap = {
            'capability': 'mcp_client',
            'status': CapabilityGapStatus.MISSING,
        }
        
        record = build_decision_record(
            recommended_work=recommended_work,
            capability_gap=capability_gap,
            evidence=['tool_card_mcp_client_unavailable'],
            blocked_by=['dependency_x'],
            resource_constraints={'ram': 'critical'},
            confidence=0.8,
            alternatives=[{'id': 'alternative_1'}],
        )
        
        assert record['recommended_work'] == recommended_work
        assert record['capability_gap'] == capability_gap
        assert record['evidence'] == ['tool_card_mcp_client_unavailable']
        assert record['blocked_by'] == ['dependency_x']
        assert record['resource_constraints'] == {'ram': 'critical'}
        assert record['confidence'] == 0.8
        assert record['alternatives'] == [{'id': 'alternative_1'}]
        assert 'timestamp' in record
        assert record['provenance']['source'] == 'capability_gap_bridge'
    
    def test_decision_record_has_minimal_defaults(self) -> None:
        """Decision record has sensible defaults when optional fields omitted."""
        recommended_work = {'id': 'test', 'title': 'Test'}
        
        record = build_decision_record(recommended_work=recommended_work)
        
        assert record['recommended_work'] == recommended_work
        assert record['capability_gap'] == {}
        assert record['evidence'] == []
        assert record['blocked_by'] == []
        assert record['resource_constraints'] == {}
        assert record['confidence'] == 0.5
        assert record['alternatives'] == []
        assert 'timestamp' in record
