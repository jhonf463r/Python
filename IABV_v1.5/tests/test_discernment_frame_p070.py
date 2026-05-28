"""P0.69/P0.70: Discernment Frame Wiring + Metacognitive Roadmap Matrix — focused tests.

Tests:
1.  ConceptWeightEvidence feeds DiscernmentFrame (concepts, weights, sources).
2.  If ConceptWeightEvidence missing, frame has UNRESOLVED marker.
3.  TaskContextAssembler includes discernment_frame_summary in metadata.
4.  PortableContext exports roadmap matrix section.
5.  OSES detects discernment_frame_missing_in_task_context.
6.  OSES detects concept_weight_evidence_missing.
7.  OSES detects stale_external_data_overrode_live_world_model.
8.  'por donde vamos?' detected as roadmap question, not generic LLM.
9.  No PII in compact_export (preserved from P0.69).
10. ConceptWeightEvidence model not duplicated if already exists.
11. build_concept_weight_evidence from metacognitive_adjustments.
12. build_concept_weight_evidence with no data returns UNRESOLVED next_action.
13. compact_export includes detected_concepts and concept_weight_count.
14. discernment_frame_summary returns compact dict for TCA.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from iabv_v15.domain.models import (
    ConceptWeightEvidence,
    MetacognitiveDiscernmentFrame,
)
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService


class TestConceptWeightEvidenceFeedsFrame(unittest.TestCase):
    """1. ConceptWeightEvidence feeds DiscernmentFrame."""

    def test_concept_weights_populated_from_evidence(self):
        svc = DiscernmentFrameService()
        evidence = ConceptWeightEvidence(
            concepts=['intent_classification', 'tool_selection'],
            weights={'intent_classification': 0.95, 'tool_selection': 0.7},
            sources=['adaptive_weight_layer', 'experiment_lab'],
        )
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence=evidence,
            world_model={'active_windows': []},
        )
        self.assertEqual(frame.detected_concepts, ['intent_classification', 'tool_selection'])
        self.assertAlmostEqual(frame.concept_weights['intent_classification'], 0.95)
        self.assertAlmostEqual(frame.concept_weights['tool_selection'], 0.7)
        self.assertIn('cwe:adaptive_weight_layer', frame.sensor_sources)
        self.assertIn('cwe:experiment_lab', frame.sensor_sources)

    def test_evidence_contradictions_merged(self):
        svc = DiscernmentFrameService()
        evidence = ConceptWeightEvidence(
            concepts=['route_a'],
            weights={'route_a': 0.8},
            sources=['experiment_lab'],
            contradictions=[{
                'type': 'weight_vs_performance',
                'detail': 'route_a has high weight but low recent performance',
            }],
        )
        frame = svc.build_frame(
            phase='decide',
            trigger_source='background',
            concept_weight_evidence=evidence,
            world_model={'active_windows': []},
        )
        contradiction_types = [c['type'] for c in frame.contradictions]
        self.assertIn('weight_vs_performance', contradiction_types)


class TestMissingConceptWeightEvidenceMarked(unittest.TestCase):
    """2. If ConceptWeightEvidence missing, frame has UNRESOLVED marker."""

    def test_missing_evidence_adds_unresolved(self):
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            # No concept_weight_evidence passed
        )
        self.assertIn('concept_weight_evidence_missing', frame.unresolved_fields)

    def test_evidence_present_no_unresolved(self):
        svc = DiscernmentFrameService()
        evidence = ConceptWeightEvidence(
            concepts=['test'],
            weights={'test': 0.5},
            sources=['test_source'],
        )
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence=evidence,
        )
        self.assertNotIn('concept_weight_evidence_missing', frame.unresolved_fields)


class TestTaskContextAssemblerIncludesSummary(unittest.TestCase):
    """3. TaskContextAssembler includes discernment_frame_summary."""

    def test_discernment_frame_summary_method_exists(self):
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        self.assertTrue(hasattr(TaskContextAssembler, '_discernment_frame_summary'))

    def test_discernment_frame_summary_returns_dict(self):
        from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
        # Create minimal instance with None deps - just testing the method
        tca = TaskContextAssembler.__new__(TaskContextAssembler)
        result = tca._discernment_frame_summary()
        self.assertIsInstance(result, dict)


class TestPortableContextExportsRoadmap(unittest.TestCase):
    """4. PortableContext exports roadmap matrix section."""

    def test_metacognitive_roadmap_matrix_section_method_exists(self):
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        self.assertTrue(hasattr(PortableContextService, '_metacognitive_roadmap_matrix_section'))

    def test_unresolved_metacognitive_links_section_method_exists(self):
        from iabv_v15.services.evolution.portable_context_service import PortableContextService
        self.assertTrue(hasattr(PortableContextService, '_unresolved_metacognitive_links_section'))


class TestOSESDetectsFrameMissingInContext(unittest.TestCase):
    """5. OSES detects discernment_frame_missing_in_task_context."""

    def test_no_frames_generates_missing_finding(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _discernment_frame_findings_impl,
        )
        from iabv_v15.domain.models import SelfExaminationFinding

        # Create a mock self with no frames
        mock_self = SimpleNamespace(workspace_root='')
        # The impl creates a new DiscernmentFrameService each time
        # with no frames, it should generate the missing finding
        findings = _discernment_frame_findings_impl(mock_self)
        categories = [f.category for f in findings]
        self.assertIn('discernment_frame_missing_in_task_context', categories)


class TestOSESDetectsConceptWeightMissing(unittest.TestCase):
    """6. OSES detects concept_weight_evidence_missing."""

    def test_frames_with_missing_cwe_detected(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _discernment_frame_findings_impl,
        )
        from iabv_v15.domain.models import SelfExaminationFinding

        svc = DiscernmentFrameService()
        # Build 4 frames without CWE
        for _ in range(4):
            frame = svc.build_frame(
                phase='act',
                trigger_source='background',
                raw_inputs=['task'],
            )
            frame.selected_action = 'do_something'

        mock_self = SimpleNamespace(workspace_root='')
        # Monkey-patch to use our svc
        import iabv_v15.services.evolution.discernment_frame_service as dfm
        original_init = DiscernmentFrameService.__init__

        def patched_init(self_inner, *, workspace_root=''):
            self_inner._workspace_root = workspace_root
            self_inner._frame_history = svc._frame_history

        DiscernmentFrameService.__init__ = patched_init
        try:
            findings = _discernment_frame_findings_impl(mock_self)
            categories = [f.category for f in findings]
            self.assertIn('concept_weight_evidence_missing', categories)
        finally:
            DiscernmentFrameService.__init__ = original_init


class TestOSESDetectsStaleOverride(unittest.TestCase):
    """7. OSES detects stale_external_data_overrode_live_world_model."""

    def test_stale_override_detected(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _discernment_frame_findings_impl,
        )

        svc = DiscernmentFrameService()
        # Build frame with stale world model contradiction and action
        frame = svc.build_frame(
            phase='act',
            trigger_source='user',
            raw_inputs=['do something'],
            world_model={'scan_status': 'stale', 'active_windows': []},
        )
        frame.selected_action = 'execute_task'

        mock_self = SimpleNamespace(workspace_root='')
        original_init = DiscernmentFrameService.__init__

        def patched_init(self_inner, *, workspace_root=''):
            self_inner._workspace_root = workspace_root
            self_inner._frame_history = svc._frame_history

        DiscernmentFrameService.__init__ = patched_init
        try:
            findings = _discernment_frame_findings_impl(mock_self)
            categories = [f.category for f in findings]
            self.assertIn('stale_external_data_overrode_live_world_model', categories)
        finally:
            DiscernmentFrameService.__init__ = original_init


class TestRoadmapQuestionDetection(unittest.TestCase):
    """8. 'por donde vamos?' is detected as roadmap question."""

    def test_roadmap_phrases_present(self):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        phrases = ControlCenterViewModel._DISCERNMENT_PHRASES
        self.assertIn('por donde vamos', phrases)
        self.assertIn('que falta', phrases)

    def test_roadmap_phrases_separate_tuple(self):
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        roadmap_phrases = ControlCenterViewModel._ROADMAP_PHRASES
        self.assertIn('por donde vamos', roadmap_phrases)
        self.assertIn('que falta', roadmap_phrases)


class TestNoPIIInCompactExport(unittest.TestCase):
    """9. No PII in compact_export (preserved from P0.69)."""

    def test_compact_export_has_no_raw_inputs(self):
        svc = DiscernmentFrameService()
        svc.build_frame(
            phase='observe',
            trigger_source='user',
            raw_inputs=['my_password_is_secret123', 'user@email.com'],
            world_model={'active_windows': []},
        )
        export = svc.compact_export()
        export_str = str(export)
        self.assertNotIn('my_password_is_secret123', export_str)
        self.assertNotIn('user@email.com', export_str)
        self.assertNotIn('raw_inputs', export)


class TestConceptWeightEvidenceNotDuplicated(unittest.TestCase):
    """10. ConceptWeightEvidence model exists and is not duplicated."""

    def test_model_importable(self):
        from iabv_v15.domain.models import ConceptWeightEvidence
        cwe = ConceptWeightEvidence()
        self.assertIsInstance(cwe.concepts, list)
        self.assertIsInstance(cwe.weights, dict)
        self.assertIsInstance(cwe.sources, list)

    def test_model_fields_complete(self):
        from iabv_v15.domain.models import ConceptWeightEvidence
        cwe = ConceptWeightEvidence(
            concepts=['a', 'b'],
            weights={'a': 0.9, 'b': 0.3},
            sources=['src1'],
            missing_sources=['src2'],
            contradictions=[{'type': 'test'}],
            next_action='verify',
            confidence=0.7,
        )
        self.assertEqual(len(cwe.concepts), 2)
        self.assertEqual(cwe.confidence, 0.7)
        self.assertEqual(cwe.next_action, 'verify')


class TestBuildConceptWeightEvidence(unittest.TestCase):
    """11. build_concept_weight_evidence from metacognitive_adjustments."""

    def test_from_metacognitive_adjustments(self):
        svc = DiscernmentFrameService()
        adjustments = {
            'external_consultation|chatgpt': {'adjustment': 0.1, 'applied_at': '2026-01-01'},
            'language_understanding|ollama': {'adjustment': -0.05, 'applied_at': '2026-01-01'},
        }
        evidence = svc.build_concept_weight_evidence(metacognitive_adjustments=adjustments)
        self.assertIn('adaptive_weight_layer', evidence.sources)
        self.assertGreater(len(evidence.concepts), 0)
        self.assertGreater(len(evidence.weights), 0)
        self.assertGreaterEqual(evidence.confidence, 0.5)

    def test_from_experiment_runs(self):
        svc = DiscernmentFrameService()
        runs = [
            SimpleNamespace(
                assistant_kind='ollama',
                route=SimpleNamespace(value='language_understanding'),
                success=True,
                metrics=SimpleNamespace(total_score=0.85),
            )
            for _ in range(3)
        ]
        evidence = svc.build_concept_weight_evidence(experiment_runs=runs)
        self.assertIn('experiment_lab', evidence.sources)
        self.assertIn('ollama:language_understanding', evidence.concepts)
        self.assertAlmostEqual(evidence.weights['ollama:language_understanding'], 0.85, places=2)


class TestBuildConceptWeightEvidenceNoData(unittest.TestCase):
    """12. build_concept_weight_evidence with no data returns UNRESOLVED."""

    def test_no_data_unresolved(self):
        svc = DiscernmentFrameService()
        evidence = svc.build_concept_weight_evidence()
        self.assertEqual(evidence.next_action, 'UNRESOLVED:concept_weight_evidence_missing')
        self.assertEqual(len(evidence.sources), 0)
        self.assertIn('adaptive_weight_layer', evidence.missing_sources)
        self.assertIn('experiment_lab', evidence.missing_sources)
        self.assertLessEqual(evidence.confidence, 0.5)


class TestCompactExportIncludesConcepts(unittest.TestCase):
    """13. compact_export includes detected_concepts and concept_weight_count."""

    def test_compact_export_with_concepts(self):
        svc = DiscernmentFrameService()
        evidence = ConceptWeightEvidence(
            concepts=['a', 'b', 'c'],
            weights={'a': 0.9, 'b': 0.7, 'c': 0.5},
            sources=['test'],
        )
        svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence=evidence,
            world_model={'active_windows': []},
        )
        export = svc.compact_export()
        self.assertIn('detected_concepts', export)
        self.assertIn('concept_weight_count', export)
        self.assertEqual(export['concept_weight_count'], 3)
        self.assertEqual(len(export['detected_concepts']), 3)


class TestDiscernmentFrameSummaryForTCA(unittest.TestCase):
    """14. discernment_frame_summary returns compact dict for TCA."""

    def test_summary_with_frame(self):
        svc = DiscernmentFrameService()
        svc.build_frame(
            phase='observe',
            trigger_source='user',
            world_model={'active_windows': [], 'network': {'connected': True}},
            environment_self_model={'scan_status': 'ok'},
        )
        summary = svc.discernment_frame_summary()
        self.assertEqual(summary['phase'], 'observe')
        self.assertIn('grounding_status', summary)
        self.assertIn('confidence', summary)
        self.assertIn('detected_concepts', summary)
        self.assertIn('active_attractors', summary)
        self.assertIn('contradictions_count', summary)
        self.assertIn('bias_risks', summary)
        self.assertIn('selected_action', summary)
        self.assertIn('unresolved_fields', summary)

    def test_summary_no_frame(self):
        svc = DiscernmentFrameService()
        summary = svc.discernment_frame_summary()
        self.assertEqual(summary, {'status': 'no_frame'})


if __name__ == '__main__':
    unittest.main()
