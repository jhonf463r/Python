"""R8-G4: Need Formulation Tests.

Tests for transforming SelfExaminationFinding into StructuredNeed.
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from iabv_v15.domain.models import (
    SelfExaminationFinding,
    IssueSeverity,
    StructuredNeed,
    NeedStatus,
)
from iabv_v15.services.evolution.need_formulation_service import NeedFormulationService
from iabv_v15.services.evolution.structured_need_repository import StructuredNeedRepository


class TestNeedFormulationPositive(unittest.TestCase):
    """Positive test: capability-shaped finding → structured need."""

    def test_capability_discovery_creates_need(self):
        """Capability discovery category should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="capability_discovery",
            title="Cannot perform visual inspection",
            summary="I cannot perform visual inspection of UI elements",
            severity=IssueSeverity.HIGH,
            recommendation="Implement visual inspection capability",
            evidence_refs=["run_123", "episode_456"],
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "Capability-shaped finding should produce a need")
        self.assertEqual(need.source_finding_id, finding.finding_id)
        self.assertEqual(need.category, "capability_discovery")
        self.assertEqual(need.capability_gap, "Cannot perform visual inspection")
        self.assertIn("cannot", need.current_state.lower())
        self.assertEqual(need.desired_state, "Implement visual inspection capability")
        self.assertEqual(need.knowledge_required, "knowledge_in_capability_discovery")
        self.assertEqual(need.priority, "high")
        self.assertEqual(need.status, NeedStatus.PENDING)
        self.assertEqual(need.evidence, ["run_123", "episode_456"])

    def test_missing_capability_creates_need(self):
        """Missing capability category should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="missing_capability",
            title="Unable to execute shell commands",
            summary="I am unable to execute shell commands on Windows",
            severity=IssueSeverity.CRITICAL,
            recommendation="Add shell command execution capability",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "Missing capability should produce a need")
        self.assertEqual(need.category, "missing_capability")
        self.assertEqual(need.capability_gap, "Unable to execute shell commands")
        self.assertEqual(need.priority, "critical")

    def test_uncertainty_creates_need(self):
        """Uncertainty category should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="uncertainty",
            title="Unknown how to handle API rate limits",
            summary="I am uncertain how to handle API rate limits gracefully",
            severity=IssueSeverity.MEDIUM,
            recommendation="Learn rate limit handling patterns",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "Uncertainty should produce a need")
        self.assertEqual(need.category, "uncertainty")
        self.assertEqual(need.priority, "medium")

    def test_keyword_based_detection(self):
        """Findings with capability keywords should create needs even without explicit category."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="generic",
            title="I cannot parse JSON responses",
            summary="System cannot parse JSON responses from external APIs",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "Keyword 'cannot' should trigger need creation")
        self.assertIn("cannot", need.capability_gap.lower())


class TestNeedFormulationNegative(unittest.TestCase):
    """Negative test: operational findings → no need."""

    def test_provider_latency_no_need(self):
        """Provider latency finding should NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="provider_underperformance",
            title="Provider latency is high",
            summary="Cloud provider showing 5000ms latency",
            severity=IssueSeverity.MEDIUM,
            recommendation="Switch to faster provider",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Operational finding should NOT produce a need")

    def test_route_failure_no_need(self):
        """Route failure finding should NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="route_failure",
            title="Route to Claude failed",
            summary="Network route to Claude API failed",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Route failure should NOT produce a need")

    def test_performance_degradation_no_need(self):
        """Performance degradation finding should NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="performance_degradation",
            title="System is slow",
            summary="UI response time degraded to 2s",
            severity=IssueSeverity.MEDIUM,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Performance degradation should NOT produce a need")


class TestStructuredNeedPersistence(unittest.TestCase):
    """Test persistence of structured needs."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo = StructuredNeedRepository(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upsert_and_get(self):
        """Test upsert and get operations."""
        need = StructuredNeed(
            source_finding_id="finding_123",
            category="capability_discovery",
            capability_gap="Cannot do X",
            current_state="unable_to_perform",
            desired_state="able_to_perform",
            knowledge_required="knowledge_in_capability_discovery",
            reason="Need to perform X for user goals",
            evidence=["evidence_1"],
            priority="high",
        )

        persisted = self.repo.upsert(need)
        retrieved = self.repo.get(persisted.need_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.need_id, persisted.need_id)
        self.assertEqual(retrieved.source_finding_id, "finding_123")
        self.assertEqual(retrieved.capability_gap, "Cannot do X")

    def test_list_all(self):
        """Test listing all needs."""
        need1 = StructuredNeed(
            source_finding_id="finding_1",
            category="capability_discovery",
            capability_gap="Gap 1",
            reason="Reason 1",
        )
        need2 = StructuredNeed(
            source_finding_id="finding_2",
            category="missing_capability",
            capability_gap="Gap 2",
            reason="Reason 2",
        )

        self.repo.upsert(need1)
        self.repo.upsert(need2)

        needs = self.repo.list_all()
        self.assertEqual(len(needs), 2)

    def test_list_pending(self):
        """Test listing pending needs."""
        need_pending = StructuredNeed(
            source_finding_id="finding_1",
            category="capability_discovery",
            capability_gap="Gap 1",
            reason="Reason 1",
            status=NeedStatus.PENDING,
        )
        need_resolved = StructuredNeed(
            source_finding_id="finding_2",
            category="missing_capability",
            capability_gap="Gap 2",
            reason="Reason 2",
            status=NeedStatus.RESOLVED,
        )

        self.repo.upsert(need_pending)
        self.repo.upsert(need_resolved)

        pending = self.repo.list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].status, NeedStatus.PENDING)


class TestHumanReadableOutput(unittest.TestCase):
    """Test human-readable formatting of needs."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo = StructuredNeedRepository(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_human_readable(self):
        """Test formatting a single need."""
        need = StructuredNeed(
            source_finding_id="finding_123",
            category="capability_discovery",
            capability_gap="Cannot perform visual inspection",
            current_state="unable_to_perform_action",
            desired_state="able_to_perform_action",
            knowledge_required="knowledge_in_capability_discovery",
            reason="Need to inspect UI elements for user goals",
            evidence=["run_123", "episode_456"],
            priority="high",
            status=NeedStatus.PENDING,
        )

        formatted = self.repo.format_human_readable(need)

        self.assertIn("NECESITO:", formatted)
        self.assertIn("Cannot perform visual inspection", formatted)
        self.assertIn("PORQUE:", formatted)
        self.assertIn("Need to inspect UI elements for user goals", formatted)
        self.assertIn("EVIDENCIA:", formatted)
        self.assertIn("PRIORIDAD: HIGH", formatted)
        self.assertIn("ESTADO: PENDING", formatted)

    def test_format_all_pending(self):
        """Test formatting all pending needs."""
        need1 = StructuredNeed(
            source_finding_id="finding_1",
            category="capability_discovery",
            capability_gap="Gap 1",
            reason="Reason 1",
            status=NeedStatus.PENDING,
        )
        need2 = StructuredNeed(
            source_finding_id="finding_2",
            category="missing_capability",
            capability_gap="Gap 2",
            reason="Reason 2",
            status=NeedStatus.PENDING,
        )

        self.repo.upsert(need1)
        self.repo.upsert(need2)

        formatted = self.repo.format_all_pending()

        self.assertIn("NECESIDADES PENDIENTES (2):", formatted)
        self.assertIn("--- NECESIDAD 1 ---", formatted)
        self.assertIn("--- NECESIDAD 2 ---", formatted)

    def test_format_all_pending_empty(self):
        """Test formatting when no pending needs."""
        formatted = self.repo.format_all_pending()
        self.assertEqual(formatted, "No hay necesidades pendientes.")


if __name__ == "__main__":
    unittest.main()
