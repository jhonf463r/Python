"""Regression coverage for the platform learning promotion boundary."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from iabv_v15.services.evolution.decision_simplifier_engine import DecisionSimplifierEngine
from iabv_v15.services.evolution.platform_learning_orchestrator import (
    ObjectiveEvidence,
    PlatformLearningOrchestrator,
)


class PlatformLearningEvidenceTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.service = PlatformLearningOrchestrator(data_root=directory.name)
        self.service.decision_simplifier = DecisionSimplifierEngine(data_root=directory.name)
        self.service.decision_simplifier.tool_registry = object()
        self.platform = self.service.get_platform('groq_console')
        self.platform.confidence = 0.8

    def test_dry_run_with_high_confidence_never_learns(self):
        attempt = self.service.learn_platform('groq_console', 'login')
        self.assertEqual(attempt.outcome, 'UNVERIFIED')
        self.assertFalse(attempt.success)
        self.assertEqual(self.platform.success_count, 0)
        self.assertEqual(self.platform.confidence, 0.8)
        self.assertFalse(self.service.decision_simplifier._history)
        self.assertFalse(self.service.decision_simplifier._history_path().exists())

    def test_rejected_action_does_not_verify_or_promote(self):
        def verify(*args):
            self.fail('A rejected action must not reach verification')

        attempt = self.service.learn_platform(
            'groq_console', 'login', lambda *args: False, verify_objective=verify,
        )
        self.assertEqual(attempt.outcome, 'FAILED')
        self.assertEqual(self.platform.success_count, 0)
        self.assertEqual(self.platform.failure_count, 1)

    def test_wrong_attempt_platform_or_goal_does_not_promote(self):
        for index in range(3):
            with self.subTest(index=index):
                def verify(*identity):
                    unrelated = list(identity)
                    unrelated[index] = 'unrelated'
                    return ObjectiveEvidence(*unrelated, source='session observation')

                attempt = self.service.learn_platform(
                    'groq_console', 'login', lambda *args: True, verify_objective=verify,
                )
                self.assertEqual(attempt.outcome, 'UNVERIFIED')
                self.assertEqual(self.platform.success_count, 0)
                self.assertEqual(self.platform.confidence, 0.8)

    def test_completed_execution_with_own_postcondition_promotes_once(self):
        observed_attempts = set()

        def execute(action, context):
            if action == 'verify':
                observed_attempts.add(context['attempt_id'])
            return True

        def verify(attempt_id, platform_id, goal):
            if attempt_id in observed_attempts:
                return ObjectiveEvidence(attempt_id, platform_id, goal, 'synthetic session probe')
            return None

        attempt = self.service.learn_platform(
            'groq_console', 'login', execute, verify_objective=verify,
        )
        self.assertTrue(attempt.success)
        self.assertEqual(attempt.outcome, 'VERIFIED_SUCCESS')
        self.assertEqual(self.platform.success_count, 1)
        self.assertAlmostEqual(self.platform.confidence, 0.9)
        self.assertFalse(self.service.decision_simplifier._history)
        path = self.root / 'evolution' / 'platform_learning' / 'learning_attempts.jsonl'
        self.assertEqual(json.loads(path.read_text())['attempt_id'], attempt.attempt_id)

    def test_completed_execution_without_postcondition_stays_unverified(self):
        attempt = self.service.learn_platform('groq_console', 'login', lambda *args: True)
        self.assertEqual(attempt.outcome, 'UNVERIFIED')
        self.assertEqual(self.platform.success_count, 0)
        self.assertEqual(self.platform.failure_count, 0)
        self.assertEqual(self.platform.confidence, 0.8)
