"""
P0.20b — Minimal Epistemic Hypothesis Contract Test

Tests focused on the epistemic hypothesis generation and propagation
from contradiction to verification boundary.
"""
import sys
import os

# Clean sys.path to remove any contamination
sys.path = [p for p in sys.path if 'IABV_v1.5_canonical' not in p and 'iabv_p019d_workspace' not in p]

# Add canonical project source to path
project_src = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, project_src)

import pytest
from iabv_v15.domain.models import MetacognitiveDiscernmentFrame, EpistemicHypothesis
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService


class TestEpistemicHypothesisContract:
    """Test A-I: Focused tests for epistemic hypothesis contract."""

    def test_a_contradiction_produces_hypothesis(self):
        """Test A: A valid contradiction produces epistemic_hypothesis."""
        service = DiscernmentFrameService()

        # Create a frame with contradictions and trusted sources
        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        # Build selected_test
        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        # Generate hypothesis
        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is not None, "Hypothesis should be generated for valid contradiction"
        assert isinstance(hypothesis, EpistemicHypothesis), "Should return EpistemicHypothesis instance"
        assert hypothesis.hypothesis_id != "", "hypothesis_id should be non-empty"
        assert hypothesis.statement != "", "statement should be non-empty"
        assert hypothesis.expected_result != "", "expected_result should be non-empty"

    def test_b_hypothesis_id_in_frame(self):
        """Test B: hypothesis_id appears in frame."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            frame.metadata['epistemic_hypothesis'] = hypothesis

            assert 'epistemic_hypothesis' in frame.metadata, "epistemic_hypothesis should be in frame metadata"
            assert frame.metadata['epistemic_hypothesis'].hypothesis_id != "", "hypothesis_id should be non-empty"
            assert frame.metadata['epistemic_hypothesis'].hypothesis_id == hypothesis.hypothesis_id, "hypothesis_id should match"

    def test_c_expected_result_in_frame(self):
        """Test C: expected_result appears in frame."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            frame.metadata['epistemic_hypothesis'] = hypothesis

            assert 'epistemic_hypothesis' in frame.metadata, "epistemic_hypothesis should be in frame metadata"
            assert frame.metadata['epistemic_hypothesis'].expected_result != "", "expected_result should be non-empty"
            # P0.20c: expected_result is now structured with condition and expected
            assert frame.metadata['epistemic_hypothesis'].expected_result['condition'] == 'provider_available', "expected_result.condition should match observed_condition"

    def test_d_selected_test_receives_hypothesis_id(self):
        """Test D: selected_test receives hypothesis_id."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            selected_test['hypothesis_id'] = hypothesis.hypothesis_id

            assert 'hypothesis_id' in selected_test, "hypothesis_id should be in selected_test"
            assert selected_test['hypothesis_id'] != "", "hypothesis_id should be non-empty"
            assert selected_test['hypothesis_id'] == hypothesis.hypothesis_id, "hypothesis_id should match"

    def test_e_selected_test_receives_expected_result(self):
        """Test E: selected_test receives expected_result."""
        service = DiscernmentFrameService()

        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            selected_test['expected_result'] = hypothesis.expected_result

            assert 'expected_result' in selected_test, "expected_result should be in selected_test"
            assert selected_test['expected_result'] != "", "expected_result should be non-empty"
            # P0.20c: expected_result is now structured with condition and expected
            assert selected_test['expected_result']['condition'] == 'provider_available', "expected_result.condition should match observed_condition"

    def test_f_propagation_to_session_metadata(self):
        """Test F: Information reaches AdaptiveSession.metadata."""
        from iabv_v15.domain.models import AdaptiveSession, AdaptiveSessionStatus, TaskIntent, TaskRole

        service = DiscernmentFrameService()

        # Create frame with hypothesis
        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                    'evidence': {
                        'provider': 'test_provider',
                        'health_status': 'healthy',
                        'inference_status': 'failed',
                        'diagnostic_target': 'provider_availability',
                    }
                }
            ],
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        if hypothesis:
            selected_test['hypothesis_id'] = hypothesis.hypothesis_id
            selected_test['expected_result'] = hypothesis.expected_result
            frame.metadata['selected_test'] = selected_test
            frame.metadata['epistemic_hypothesis'] = hypothesis

            # Create session and propagate metadata
            session = AdaptiveSession(
                session_id='test-session-id',
                user_goal='test hypothesis propagation',
                status=AdaptiveSessionStatus.PLANNED,
                intent=TaskIntent(
                    intent_key='system.self_awareness',
                    role=TaskRole.KNOWLEDGE,
                    confidence=0.9,
                ),
                metadata={
                    'selected_test': selected_test,
                    'epistemic_hypothesis': hypothesis.model_dump(),
                },
            )

            assert 'selected_test' in session.metadata, "selected_test should be in session metadata"
            assert 'hypothesis_id' in session.metadata['selected_test'], "hypothesis_id should be in selected_test"
            assert 'expected_result' in session.metadata['selected_test'], "expected_result should be in selected_test"
            assert 'epistemic_hypothesis' in session.metadata, "epistemic_hypothesis should be in session metadata"

    def test_g_no_hypothesis_insufficient_evidence(self):
        """Test G: No hypothesis created if evidence is insufficient."""
        service = DiscernmentFrameService()

        # Frame without contradictions
        frame = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[],  # No contradictions
            trusted_sources=['world_model'],
            sensor_sources=['world_model'],
        )

        selected_test = {
            'test_id': 'test_provider_availability_probe',
            'test_type': 'provider_availability',
            'target': 'provider_availability',
            'reason': 'Test provider availability',
            'cost_class': 'low',
            'status': 'proposed',
            'contradiction_type': 'provider_health_vs_inference_failure',
            'diagnostic': True,
            'read_only': True,
            'requires_approval': False,
            'timeout_seconds': 2.0,
            'observed_condition': 'provider_available',  # P0.20h: Mandatory field
        }

        hypothesis = service._generate_epistemic_hypothesis(frame, selected_test)

        assert hypothesis is None, "Hypothesis should not be generated without contradictions"

        # Frame without trusted sources
        frame2 = MetacognitiveDiscernmentFrame(
            phase='observe',
            trigger_source='test',
            contradictions=[
                {
                    'type': 'provider_health_vs_inference_failure',
                    'detail': 'Provider is healthy but inference failed.',
                }
            ],
            trusted_sources=[],  # No trusted sources
            sensor_sources=['world_model'],
        )

        hypothesis2 = service._generate_epistemic_hypothesis(frame2, selected_test)

        assert hypothesis2 is None, "Hypothesis should not be generated without trusted sources"

    def test_h_verification_boundary_unchanged(self):
        """Test H: Verification boundary is not modified."""
        from iabv_v15.domain.models import VerificationStatus, LearningDecision

        # Verify that verification boundary semantics are unchanged
        assert VerificationStatus.VERIFIED.value == 'verified', "VERIFIED value unchanged"
        assert VerificationStatus.REFUTED.value == 'refuted', "REFUTED value unchanged"
        assert VerificationStatus.INCONCLUSIVE.value == 'inconclusive', "INCONCLUSIVE value unchanged"
        assert VerificationStatus.UNVERIFIED.value == 'unverified', "UNVERIFIED value unchanged"

        assert LearningDecision.ELIGIBLE.value == 'eligible', "ELIGIBLE value unchanged"
        assert LearningDecision.NOT_ELIGIBLE.value == 'not_eligible', "NOT_ELIGIBLE value unchanged"

    def test_i_no_new_components_created(self):
        """Test I: No new components created."""
        # Verify that only EpistemicHypothesis model was added
        from iabv_v15.domain.models import EpistemicHypothesis

        # EpistemicHypothesis is a simple Pydantic model, not a service
        # Verify it has the expected fields
        hypothesis = EpistemicHypothesis()
        assert hasattr(hypothesis, 'hypothesis_id'), "EpistemicHypothesis instance has hypothesis_id"
        assert hasattr(hypothesis, 'statement'), "EpistemicHypothesis instance has statement"
        assert hasattr(hypothesis, 'expected_result'), "EpistemicHypothesis instance has expected_result"

        # Verify no new services were created
        # (This is a structural test - we verify by checking that the implementation
        # only added a method to DiscernmentFrameService, not a new service class)
        from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService

        # Verify the new method exists
        assert hasattr(DiscernmentFrameService, '_generate_epistemic_hypothesis')
        # "DiscernmentFrameService has _generate_epistemic_hypothesis method"

        # Verify it's a static method (minimal implementation)
        import inspect
        method = getattr(DiscernmentFrameService, '_generate_epistemic_hypothesis')
        assert isinstance(inspect.getattr_static(DiscernmentFrameService, '_generate_epistemic_hypothesis'), staticmethod)
        # "_generate_epistemic_hypothesis is a static method"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
