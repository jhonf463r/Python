"""P0.69/P0.70: Discernment Frame Wiring + Metacognitive Roadmap Matrix — focused tests.

Tests:
1.  concept_weight_evidence (dict from existing service) feeds DiscernmentFrame.
2.  If concept_weight_evidence missing, frame has UNRESOLVED marker.
3.  TaskContextAssembler includes discernment_frame_summary in metadata.
4.  PortableContext exports roadmap matrix section.
5.  OSES detects discernment_frame_missing_in_task_context.
6.  OSES detects stale_external_data_overrode_live_world_model.
7.  'por donde vamos?' detected as roadmap question, not generic LLM.
8.  No PII in compact_export (preserved from P0.69).
9.  No ConceptWeightEvidence model in domain/models.py (uses existing service dict).
10. compact_export includes detected_concepts and concept_weight_count.
11. discernment_frame_summary returns compact dict for TCA.
12. Frame unresolved_fields preserved (extend, not overwrite).
13. DiscernmentFrameService accepts dict CWE (not typed model).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from iabv_v15.domain.models import MetacognitiveDiscernmentFrame
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService


class TestConceptWeightEvidenceFeedsFrame(unittest.TestCase):
    """1. concept_weight_evidence dict feeds DiscernmentFrame."""

    def test_concept_weights_populated_from_evidence(self):
        svc = DiscernmentFrameService()
        evidence = {
            'concepts': ['intent_classification', 'tool_selection'],
            'weights': {'intent_classification': 0.95, 'tool_selection': 0.7},
            'sources': ['adaptive_weight_layer', 'experiment_lab'],
        }
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
        evidence = {
            'concepts': ['route_a'],
            'weights': {'route_a': 0.8},
            'sources': ['experiment_lab'],
            'contradictions': [{
                'type': 'weight_vs_performance',
                'detail': 'route_a has high weight but low recent performance',
            }],
        }
        frame = svc.build_frame(
            phase='decide',
            trigger_source='background',
            concept_weight_evidence=evidence,
            world_model={'active_windows': []},
        )
        contradiction_types = [c['type'] for c in frame.contradictions]
        self.assertIn('weight_vs_performance', contradiction_types)


class TestMissingConceptWeightEvidenceMarked(unittest.TestCase):
    """2. If concept_weight_evidence missing, frame has UNRESOLVED marker."""

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
        evidence = {
            'concepts': ['test'],
            'weights': {'test': 0.5},
            'sources': ['test_source'],
        }
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

        mock_self = SimpleNamespace(workspace_root='')
        findings = _discernment_frame_findings_impl(mock_self)
        categories = [f.category for f in findings]
        self.assertIn('discernment_frame_missing_in_task_context', categories)


class TestOSESDetectsStaleOverride(unittest.TestCase):
    """6. OSES detects stale_external_data_overrode_live_world_model."""

    def test_stale_override_detected(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            _discernment_frame_findings_impl,
        )

        svc = DiscernmentFrameService()
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
    """7. 'por donde vamos?' is detected as roadmap question."""

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
    """8. No PII in compact_export (preserved from P0.69)."""

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


class TestNoConceptWeightEvidenceModelDuplicated(unittest.TestCase):
    """9. No ConceptWeightEvidence model in domain/models.py — uses existing service dict."""

    def test_no_cwe_model_in_domain(self):
        """ConceptWeightEvidence should NOT exist as a Pydantic model in domain/models.py.
        The existing concept_weight_evidence.py service produces dicts that
        DiscernmentFrameService consumes directly."""
        import iabv_v15.domain.models as models_mod
        self.assertFalse(
            hasattr(models_mod, 'ConceptWeightEvidence'),
            'ConceptWeightEvidence model should not exist in domain/models.py — '
            'use the existing concept_weight_evidence service dict output instead',
        )

    def test_discernment_service_accepts_dict(self):
        """DiscernmentFrameService.build_frame accepts concept_weight_evidence as dict."""
        import inspect
        sig = inspect.signature(DiscernmentFrameService.build_frame)
        param = sig.parameters['concept_weight_evidence']
        annotation = str(param.annotation)
        self.assertIn('dict', annotation)
        self.assertNotIn('ConceptWeightEvidence', annotation)


class TestCompactExportIncludesConcepts(unittest.TestCase):
    """10. compact_export includes detected_concepts and concept_weight_count."""

    def test_compact_export_with_concepts(self):
        svc = DiscernmentFrameService()
        evidence = {
            'concepts': ['a', 'b', 'c'],
            'weights': {'a': 0.9, 'b': 0.7, 'c': 0.5},
            'sources': ['test'],
        }
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
    """11. discernment_frame_summary returns compact dict for TCA."""

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


class TestUnresolvedFieldsPreserved(unittest.TestCase):
    """12. Frame unresolved_fields are extended, not overwritten."""

    def test_cwe_missing_marker_survives_collect_unresolved(self):
        """When no CWE is passed, _apply_concept_weight_evidence adds
        'concept_weight_evidence_missing'. Then _collect_unresolved extends
        (not overwrites) so the marker survives."""
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            # no concept_weight_evidence → marker added
        )
        self.assertIn('concept_weight_evidence_missing', frame.unresolved_fields)
        # Also has other unresolved from _collect_unresolved
        self.assertIn('world_model_missing', frame.unresolved_fields)

    def test_cwe_present_no_overwrite(self):
        svc = DiscernmentFrameService()
        evidence = {
            'concepts': ['x'],
            'weights': {'x': 1.0},
            'sources': ['src'],
        }
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence=evidence,
        )
        self.assertNotIn('concept_weight_evidence_missing', frame.unresolved_fields)
        # Still has world_model_missing from _collect_unresolved
        self.assertIn('world_model_missing', frame.unresolved_fields)


class TestDiscernmentServiceAcceptsDict(unittest.TestCase):
    """13. DiscernmentFrameService accepts dict CWE, not typed model."""

    def test_empty_dict_treated_as_present(self):
        """An empty dict is still 'present' — no unresolved marker."""
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence={'concepts': [], 'weights': {}, 'sources': []},
        )
        self.assertNotIn('concept_weight_evidence_missing', frame.unresolved_fields)

    def test_dict_with_extra_keys_ignored(self):
        """Dict from existing service may have extra keys; they should not break."""
        svc = DiscernmentFrameService()
        evidence = {
            'concepts': ['a'],
            'weights': {'a': 0.5},
            'sources': ['src'],
            'extra_field': 'should_be_ignored',
            'next_action': 'verify',
        }
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            concept_weight_evidence=evidence,
        )
        self.assertEqual(frame.detected_concepts, ['a'])


if __name__ == '__main__':
    unittest.main()
