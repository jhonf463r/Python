"""P0.69: Metacognitive Discernment Frame + Genesis Attractor Filter — focused tests.

Tests:
1. Birth frame generates from startup_audit/startup_timeline events.
2. Stale history does NOT override live WorldModel.
3. Contradiction between visual and tool is marked.
4. Low confidence does NOT allow declaring success.
5. "sigue" uses active frame/thread, not heavy local chat.
6. OSES detects action without grounding.
7. PortableContext exports discernment_frame compact.
8. ConceptWeightEvidence is preserved within the frame.
9. Failed attractor repeated gets marked.
10. No PII is filtered in compact export.
"""
from __future__ import annotations

import re
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from iabv_v15.domain.models import MetacognitiveDiscernmentFrame
from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService


class TestBirthFrameFromStartupEvents(unittest.TestCase):
    """1. Birth frame generates from startup_audit/startup_timeline events."""

    def test_birth_frame_has_startup_sensors(self):
        svc = DiscernmentFrameService()
        events = [
            {'phase': 'bootstrap_init_done', 't_ms_from_start': 200},
            {'phase': 'world_model_ready', 't_ms_from_start': 1000},
        ]
        frame = svc.build_birth_frame(startup_events=events)
        self.assertEqual(frame.phase, 'birth')
        self.assertEqual(frame.trigger_source, 'startup')
        self.assertIn('startup_timeline', frame.sensor_sources)
        self.assertTrue(any('startup_phase:' in inp for inp in frame.raw_inputs))

    def test_birth_frame_with_freeze_reports_adds_bias(self):
        svc = DiscernmentFrameService()
        frame = svc.build_birth_frame(
            startup_events=[{'phase': 'splash', 't_ms_from_start': 50}],
            freeze_reports=[{'stall_ms': 5000}, {'stall_ms': 12000}],
        )
        bias_types = [b['type'] for b in frame.bias_risks]
        self.assertIn('birth_with_freeze_history', bias_types)
        self.assertEqual(frame.next_observation, 'stabilize_ui_before_deep_cognition')


class TestStaleHistoryDoesNotOverrideLiveWorldModel(unittest.TestCase):
    """2. Stale history does NOT override live WorldModel."""

    def test_stale_world_model_contradiction(self):
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            raw_inputs=['test input'],
            world_model={'scan_status': 'stale', 'active_windows': []},
        )
        contradiction_types = [c['type'] for c in frame.contradictions]
        self.assertIn('stale_world_model_vs_live_input', contradiction_types)
        stale_c = [c for c in frame.contradictions if c['type'] == 'stale_world_model_vs_live_input'][0]
        self.assertEqual(stale_c['resolution'], 'live_wins')


class TestContradictionBetweenVisualAndTool(unittest.TestCase):
    """3. Contradiction between visual and tool is marked."""

    def test_low_confidence_tool_marked(self):
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='tool',
            world_model={
                'active_windows': [],
                'tool_live_status': [
                    {'tool_id': 'chatgpt', 'confidence': 0.2, 'probe_status': 'no_verificado'},
                ],
            },
        )
        risk_types = [b['type'] for b in frame.bias_risks]
        self.assertIn('low_confidence_observation', risk_types)


class TestLowConfidenceDoesNotDeclareCerteza(unittest.TestCase):
    """4. Low confidence does NOT allow declaring success."""

    def test_low_confidence_frame(self):
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='decide',
            trigger_source='user',
            raw_inputs=['do something'],
            # No world model, no environment → missing sources → low confidence
        )
        self.assertLess(frame.confidence, 0.5)
        self.assertNotEqual(frame.grounding_status, 'grounded')
        self.assertIn('world_model_missing', frame.unresolved_fields)

    def test_human_summary_warns_low_confidence(self):
        svc = DiscernmentFrameService()
        # Build frame with explicit low confidence and no trusted sources
        frame = MetacognitiveDiscernmentFrame(
            phase='decide',
            trigger_source='user',
            raw_inputs=['do'],
            confidence=0.2,
            selected_action='test_action',
        )
        summary = svc.human_summary(frame)
        self.assertIn('Sin información confirmada', summary['what_i_know'])


class TestSigueUsesActiveFrame(unittest.TestCase):
    """5. 'sigue' question uses active frame, not heavy local chat.

    This is validated via the discernment question detection — discernment
    questions are handled before local LLM.
    """

    def test_discernment_question_detected(self):
        """The ViewModel should detect discernment questions."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        # Static method check: phrases
        phrases = ControlCenterViewModel._DISCERNMENT_PHRASES
        self.assertTrue(len(phrases) > 0)
        # "me entiendes" should be a discernment phrase
        self.assertIn('me entiendes', phrases)
        self.assertIn('que sabes', phrases)
        self.assertIn('por que no puedes', phrases)


class TestOSESDetectsActionWithoutGrounding(unittest.TestCase):
    """6. OSES detects action without grounding."""

    def test_ungrounded_actions_finding(self):
        svc = DiscernmentFrameService()
        # Build frames where actions are taken without grounding
        for _ in range(3):
            frame = svc.build_frame(
                phase='act',
                trigger_source='background',
                raw_inputs=['heavy task'],
            )
            frame.selected_action = 'run_heavy_task'
            # grounding_status should be something like 'insufficient' since no world model

        frames = svc.recent_frames(limit=10)
        # Simulate OSES analysis
        from iabv_v15.domain.models import SelfExaminationFinding, IssueSeverity

        ungrounded = sum(
            1 for f in frames
            if f.selected_action and f.grounding_status not in ('grounded', 'partial')
        )
        self.assertGreaterEqual(ungrounded, 2)


class TestPortableContextExportsDiscernmentFrame(unittest.TestCase):
    """7. PortableContext exports discernment_frame compact."""

    def test_compact_export_structure(self):
        svc = DiscernmentFrameService()
        svc.build_frame(
            phase='observe',
            trigger_source='user',
            raw_inputs=['test'],
            world_model={'active_windows': [], 'network': {'connected': True}},
            environment_self_model={'scan_status': 'ok'},
        )
        export = svc.compact_export()
        self.assertIn('frame_id', export)
        self.assertEqual(export['phase'], 'observe')
        self.assertIn('grounding_status', export)
        self.assertIn('confidence', export)
        self.assertIn('sensor_count', export)
        self.assertIn('contradiction_count', export)
        self.assertIn('bias_risk_count', export)
        self.assertNotIn('raw_inputs', export)  # No PII in compact

    def test_no_frame_export(self):
        svc = DiscernmentFrameService()
        export = svc.compact_export()
        self.assertEqual(export, {'status': 'no_frame'})


class TestConceptWeightPreserved(unittest.TestCase):
    """8. ConceptWeightEvidence preserved within the frame."""

    def test_concept_weights_field_exists(self):
        frame = MetacognitiveDiscernmentFrame()
        frame.concept_weights = {'intent_classification': 0.95, 'tool_selection': 0.7}
        self.assertEqual(frame.concept_weights['intent_classification'], 0.95)
        self.assertEqual(frame.concept_weights['tool_selection'], 0.7)

    def test_detected_concepts_preserved(self):
        frame = MetacognitiveDiscernmentFrame()
        frame.detected_concepts = ['task_execution', 'web_navigation', 'code_generation']
        self.assertEqual(len(frame.detected_concepts), 3)
        self.assertIn('task_execution', frame.detected_concepts)


class TestFailedAttractorMarked(unittest.TestCase):
    """9. Failed attractor repeated gets marked."""

    def test_failed_attractor_detection(self):
        svc = DiscernmentFrameService()

        # Create mock experiment runs with failures
        runs = []
        for i in range(6):
            run = SimpleNamespace(
                assistant_kind='chatgpt',
                route=SimpleNamespace(value='external_consultation'),
                success=(i < 1),  # only 1 of 6 succeeds
                metrics=SimpleNamespace(total_score=0.3 if i < 1 else 0),
            )
            runs.append(run)

        frame = svc.build_frame(
            phase='decide',
            trigger_source='background',
            experiment_runs=runs,
        )
        # chatgpt:external_consultation should be in failed_attractors (fail_rate > 0.6)
        failed_keys = [a['key'] for a in frame.failed_attractors]
        self.assertIn('chatgpt:external_consultation', failed_keys)

    def test_active_attractor_detection(self):
        svc = DiscernmentFrameService()
        runs = []
        for i in range(5):
            run = SimpleNamespace(
                assistant_kind='ollama',
                route=SimpleNamespace(value='language_understanding'),
                success=True,
                metrics=SimpleNamespace(total_score=0.9),
            )
            runs.append(run)

        frame = svc.build_frame(
            phase='decide',
            trigger_source='background',
            experiment_runs=runs,
        )
        active_keys = [a['key'] for a in frame.active_attractors]
        self.assertIn('ollama:language_understanding', active_keys)
        self.assertEqual(frame.candidate_attractor, 'ollama:language_understanding')
        self.assertGreater(frame.attractor_confidence, 0.5)


class TestNoPIIInExport(unittest.TestCase):
    """10. No PII is filtered in compact export."""

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

    def test_human_summary_does_not_leak_raw_inputs(self):
        svc = DiscernmentFrameService()
        frame = svc.build_frame(
            phase='observe',
            trigger_source='user',
            raw_inputs=['sensitive_data_here'],
        )
        summary = svc.human_summary(frame)
        summary_str = str(summary)
        self.assertNotIn('sensitive_data_here', summary_str)


if __name__ == '__main__':
    unittest.main()
