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
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "capability_discovery", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Cannot perform visual inspection", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Implement visual inspection capability", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "capability_discovery", "knowledge_required must come from finding.category")
        self.assertEqual(need.reason, "I cannot perform visual inspection of UI elements", "reason must come from finding.summary")
        self.assertEqual(need.evidence, ["run_123", "episode_456"], "evidence must come from finding.evidence_refs")
        self.assertEqual(need.priority, "high", "priority must map from finding.severity")
        self.assertEqual(need.status, NeedStatus.PENDING, "status must be PENDING")

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
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "missing_capability", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Unable to execute shell commands", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Add shell command execution capability", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "missing_capability", "knowledge_required must come from finding.category")
        self.assertEqual(need.priority, "critical", "priority must map from finding.severity")

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
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "uncertainty", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Unknown how to handle API rate limits", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Learn rate limit handling patterns", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "uncertainty", "knowledge_required must come from finding.category")
        self.assertEqual(need.priority, "medium", "priority must map from finding.severity")

    def test_inability_with_capability_context_creates_need(self):
        """Inability category with explicit capability context should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="inability",
            title="Unable to execute file system operations",
            summary="I am unable to execute file system operations on Windows",
            severity=IssueSeverity.HIGH,
            recommendation="Implement file system operation capability",
            evidence_refs=["run_789"],
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "Inability with capability context should produce a need")
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "inability", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Unable to execute file system operations", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Implement file system operation capability", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "inability", "knowledge_required must come from finding.category")
        self.assertEqual(need.evidence, ["run_789"], "evidence must come from finding.evidence_refs")

    def test_capability_promised_but_unavailable_creates_need(self):
        """Real OSES category: capability_promised_but_unavailable should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="capability_promised_but_unavailable",
            title="Capability promised but not wired in build",
            summary="3 veces se prometio una capacidad que no esta disponible en el build actual. Capacidades: file_system, visual_inspection.",
            severity=IssueSeverity.MEDIUM,
            recommendation="Verificar que los handlers requeridos estan presentes en el build. No prometer acciones sin verificar hasattr primero.",
            evidence_refs=["runtime_audit.jsonl"],
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "capability_promised_but_unavailable should produce a need")
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "capability_promised_but_unavailable", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Capability promised but not wired in build", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Verificar que los handlers requeridos estan presentes en el build. No prometer acciones sin verificar hasattr primero.", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "capability_promised_but_unavailable", "knowledge_required must come from finding.category")
        self.assertEqual(need.evidence, ["runtime_audit.jsonl"], "evidence must come from finding.evidence_refs")

    def test_windows_capability_missing_creates_need(self):
        """Real OSES category: windows_capability_missing should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="windows_capability_missing",
            title="Falta: file_system_operations",
            summary="file_system_operations no",
            severity=IssueSeverity.LOW,
            recommendation="Dependencia: win32api",
            source_refs=["file_system_operations"],
            metadata={
                "capability_id": "file_system_operations",
                "status": "missing",
            },
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "windows_capability_missing should produce a need")
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "windows_capability_missing", "category must match finding.category")
        self.assertEqual(need.capability_gap, "Falta: file_system_operations", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Dependencia: win32api", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "windows_capability_missing", "knowledge_required must come from finding.category")

    def test_research_gap_creates_need(self):
        """Real OSES category: research_gap should create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="research_gap",
            title="GPU capability declared but not measured",
            summary="User declared GPU capability in chat but it has not been measured against StrategySelector/ExperimentLab.",
            severity=IssueSeverity.MEDIUM,
            recommendation="Investigate GPU availability and integrate with capability measurement system.",
            evidence_refs=["chat_research_backlog/session_123.jsonl"],
            metadata={
                "kind": "gpu",
                "label": "GPU capability",
            },
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNotNone(need, "research_gap should produce a need")
        # Provenance assertions
        self.assertEqual(need.source_finding_id, finding.finding_id, "source_finding_id must match finding.finding_id")
        self.assertEqual(need.category, "research_gap", "category must match finding.category")
        self.assertEqual(need.capability_gap, "GPU capability declared but not measured", "capability_gap must come from finding.title")
        self.assertEqual(need.desired_state, "Investigate GPU availability and integrate with capability measurement system.", "desired_state must come from finding.recommendation")
        self.assertEqual(need.knowledge_required, "research_gap", "knowledge_required must come from finding.category")
        self.assertEqual(need.evidence, ["chat_research_backlog/session_123.jsonl"], "evidence must come from finding.evidence_refs")


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

    def test_provider_cannot_handle_load_no_need(self):
        """Provider with 'cannot' keyword but operational context must NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="provider_underperformance",
            title="Provider cannot handle the load",
            summary="The cloud provider cannot handle the current load",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Operational finding with 'cannot' must NOT produce a need")

    def test_we_need_faster_route_no_need(self):
        """Finding with 'need' keyword but operational context must NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="route_failure",
            title="We need a faster route",
            summary="We need a faster route to the API endpoint",
            severity=IssueSeverity.MEDIUM,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Operational finding with 'need' must NOT produce a need")

    def test_route_requires_optimization_no_need(self):
        """Route optimization finding must NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="route_failure",
            title="Route requires optimization",
            summary="Network route requires optimization for better throughput",
            severity=IssueSeverity.MEDIUM,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Route optimization must NOT produce a need")

    def test_timeout_no_need(self):
        """Timeout finding must NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="timeout",
            title="Request timeout",
            summary="API requests are timing out after 30 seconds",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Timeout must NOT produce a need")

    def test_network_failure_no_need(self):
        """Network failure finding must NOT create a need."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="network_failure",
            title="Network connection failed",
            summary="Network connection to external service failed",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Network failure must NOT produce a need")

    def test_ambiguous_with_capability_keyword_no_need(self):
        """Ambiguous finding with capability keyword must NOT create a need (fail-closed)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="generic",
            title="System cannot process request",
            summary="System cannot process request due to high load",
            severity=IssueSeverity.MEDIUM,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "Ambiguous finding with capability keyword must NOT produce a need")

    def test_functional_gap_no_need(self):
        """Real OSES category: functional_gap should NOT create a need (underutilized resources, not missing capabilities)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="functional_gap",
            title="Sesiones activas en navegadores sin cuentas asociadas",
            summary="Se detectaron sesiones activas en Opera pero no hay cuentas de Google asociadas en esos navegadores.",
            severity=IssueSeverity.LOW,
            recommendation="Considerar asociar cuentas a los navegadores con sesiones para mejor tracking de cuotas por cuenta.",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "functional_gap (underutilized resources) must NOT produce a need")

    def test_configuration_gap_no_need(self):
        """Real OSES category: configuration_gap should NOT create a need (missing config/secrets, not capability gaps)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="configuration_gap",
            title="Secretos criticos faltantes: GITHUB_TOKEN_IABV",
            summary="1 secreto(s) critico(s) no configurado(s): GITHUB_TOKEN_IABV. Esto bloquea funcionalidad esencial.",
            severity=IssueSeverity.HIGH,
            recommendation="Configurar los secretos faltantes via la UI de IABV.",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "configuration_gap (missing config/secrets) must NOT produce a need")

    def test_underutilized_resource_no_need(self):
        """Real OSES category: underutilized_resource should NOT create a need (resource available but not used)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="underutilized_resource",
            title="API key de OpenAI disponible sin ejemplos de entrenamiento",
            summary="Hay una API key de OpenAI configurada pero el clasificador dual aun no ha generado ejemplos de entrenamiento.",
            severity=IssueSeverity.LOW,
            recommendation="Usar el clasificador dual para generar ejemplos de entrenamiento.",
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "underutilized_resource must NOT produce a need")

    def test_temporal_latency_anomaly_no_need(self):
        """Real OSES category: temporal_latency_anomaly should NOT create a need (operational problem)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="temporal_latency_anomaly",
            title="Latency anomaly detected",
            summary="Sudden spike in operation latency detected.",
            severity=IssueSeverity.MEDIUM,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "temporal_latency_anomaly must NOT produce a need")

    def test_cloud_provider_degradation_no_need(self):
        """Real OSES category: cloud_provider_degradation should NOT create a need (operational problem)."""
        service = NeedFormulationService()
        finding = SelfExaminationFinding(
            category="cloud_provider_degradation",
            title="Cloud provider showing degradation",
            summary="Cloud provider success rate dropped below acceptable threshold.",
            severity=IssueSeverity.HIGH,
        )

        need = service.formulate_need_from_finding(finding)

        self.assertIsNone(need, "cloud_provider_degradation must NOT produce a need")


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
