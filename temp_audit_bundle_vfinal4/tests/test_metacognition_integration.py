"""Integration tests for the metacognition pipeline.

Verifies the full chain:
  DecisionAuditTrail → OSES._cloud_reasoning_findings() →
  PortableContextService._cloud_reasoning_section() →
  AdaptiveTaskOrchestrator.generate_cloud_plan() pre-scan →
  AutonomousValidationCycle._cloud_provider_health_pass()
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp_data_root() -> Path:
    p = Path(tempfile.mkdtemp(prefix='iabv_metacog_'))
    return p


# ---------------------------------------------------------------------------
# 1. DecisionAuditTrail → OSES findings
# ---------------------------------------------------------------------------


class TestAuditTrailToOSES:
    """OSES must read DecisionAuditTrail and produce cloud reasoning findings."""

    def test_oses_produces_cloud_findings_from_audit_trail(self):
        from iabv_v15.services.evolution.decision_audit_trail import (
            DecisionAuditTrail,
            DecisionOutcome,
            DecisionPhase,
            DecisionRecord,
        )

        root = _tmp_data_root()
        try:
            audit = DecisionAuditTrail(data_root=str(root))
            # Record enough decisions to trigger findings:
            # gemini always fails → no functional provider finding
            for i in range(4):
                audit.record(DecisionRecord(
                    phase=DecisionPhase.PLAN_GENERATION,
                    provider_id='gemini',
                    model_used='gemini-2.0-flash',
                    user_goal=f'test goal fail {i}',
                    outcome=DecisionOutcome.RATE_LIMITED,
                    latency_ms=0.0,
                    confidence=0.0,
                    error_detail='429 quota exceeded',
                ))

            # Build OSES with the audit trail injected
            from iabv_v15.services.evolution.operational_self_examination_service import (
                OperationalSelfExaminationService,
            )

            oses = OperationalSelfExaminationService.__new__(
                OperationalSelfExaminationService
            )
            oses.decision_audit_trail = audit

            findings = oses._cloud_reasoning_findings()
            assert isinstance(findings, list)
            assert len(findings) > 0

            categories = [f.category for f in findings]
            has_cloud = any(c.startswith('cloud_') for c in categories)
            assert has_cloud, f'Expected cloud_ findings, got: {categories}'
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_oses_returns_empty_when_no_audit_trail(self):
        from iabv_v15.services.evolution.operational_self_examination_service import (
            OperationalSelfExaminationService,
        )

        oses = OperationalSelfExaminationService.__new__(
            OperationalSelfExaminationService
        )
        oses.decision_audit_trail = None

        findings = oses._cloud_reasoning_findings()
        assert findings == []


# ---------------------------------------------------------------------------
# 2. PortableContextService cloud reasoning section
# ---------------------------------------------------------------------------


class TestPortableContextCloudSection:
    """PortableContextService must export cloud reasoning status."""

    def test_cloud_reasoning_snapshot_returns_audit_summary(self):
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )

        root = _tmp_data_root()
        try:
            from iabv_v15.services.evolution.decision_audit_trail import (
                DecisionAuditTrail,
                DecisionOutcome,
                DecisionPhase,
                DecisionRecord,
            )

            audit = DecisionAuditTrail(data_root=str(root))
            audit.record(DecisionRecord(
                phase=DecisionPhase.PLAN_GENERATION,
                provider_id='groq',
                model_used='llama-3.3-70b-versatile',
                user_goal='snapshot test',
                outcome=DecisionOutcome.SUCCESS,
                latency_ms=300.0,
                confidence=0.9,
            ))

            storage = MagicMock()
            pcs = PortableContextService.__new__(PortableContextService)
            pcs.decision_audit_trail = audit

            snapshot = pcs._cloud_reasoning_snapshot()
            assert snapshot['status'] == 'analyzed'
            assert snapshot['total_decisions'] == 1
            assert snapshot['health_score'] > 0
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_cloud_reasoning_snapshot_returns_not_configured_without_trail(self):
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )

        pcs = PortableContextService.__new__(PortableContextService)
        pcs.decision_audit_trail = None

        snapshot = pcs._cloud_reasoning_snapshot()
        assert snapshot['status'] == 'not_configured'

    def test_cloud_reasoning_section_builds_valid_section(self):
        from iabv_v15.services.evolution.portable_context_service import (
            PortableContextService,
        )
        from iabv_v15.domain.models import utc_now

        root = _tmp_data_root()
        try:
            from iabv_v15.services.evolution.decision_audit_trail import (
                DecisionAuditTrail,
                DecisionOutcome,
                DecisionPhase,
                DecisionRecord,
            )

            audit = DecisionAuditTrail(data_root=str(root))
            for i in range(5):
                audit.record(DecisionRecord(
                    phase=DecisionPhase.PLAN_GENERATION,
                    provider_id='groq',
                    model_used='llama-3.3-70b-versatile',
                    user_goal=f'section test {i}',
                    outcome=DecisionOutcome.SUCCESS,
                    latency_ms=200.0 + i * 50,
                    confidence=0.8,
                ))

            from iabv_v15.infra.persistence.storage import ArtifactStorage

            storage_mock = MagicMock(spec=ArtifactStorage)
            pcs = PortableContextService.__new__(PortableContextService)
            pcs.decision_audit_trail = audit

            status = pcs._cloud_reasoning_snapshot()
            section = pcs._cloud_reasoning_section(status=status, now=utc_now())

            assert section.section_id == 'cloud_reasoning'
            assert 'Cloud reasoning' in section.summary or 'decisiones' in section.summary
            assert section.confidence > 0
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. Orchestrator pre-scan injects audit + OSES context
# ---------------------------------------------------------------------------


class TestOrchestratorPreScan:
    """generate_cloud_plan must inject audit trail + OSES findings as context."""

    def test_prescan_injects_audit_summary_into_planner_context(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )

        root = _tmp_data_root()
        try:
            from iabv_v15.services.evolution.decision_audit_trail import (
                DecisionAuditTrail,
                DecisionOutcome,
                DecisionPhase,
                DecisionRecord,
            )

            audit = DecisionAuditTrail(data_root=str(root))
            for i in range(3):
                audit.record(DecisionRecord(
                    phase=DecisionPhase.PLAN_GENERATION,
                    provider_id='groq',
                    model_used='llama-3.3-70b-versatile',
                    user_goal=f'prescan test {i}',
                    outcome=DecisionOutcome.SUCCESS,
                    latency_ms=300.0,
                    confidence=0.85,
                ))

            # Create a minimal orchestrator with mock planner
            orch = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
            orch.decision_audit_trail = audit
            orch.self_examination_service = None

            captured_context = {}

            class FakePlanner:
                def generate_plan(self, goal, *, context=''):
                    captured_context['context'] = context
                    return None

            orch.cloud_reasoning_planner = FakePlanner()

            orch.generate_cloud_plan('test goal')

            ctx = captured_context.get('context', '')
            assert 'Cloud reasoning status' in ctx
            assert 'health=' in ctx
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_prescan_injects_oses_cloud_findings(self):
        from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
            AdaptiveTaskOrchestrator,
        )

        orch = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
        orch.decision_audit_trail = None

        # Mock OSES with cloud findings
        mock_review = MagicMock()
        finding = MagicMock()
        finding.category = 'cloud_provider_degradation'
        finding.title = 'Gemini degrading'
        finding.recommendation = 'Rotate to Groq'
        mock_review.findings = [finding]

        mock_oses = MagicMock()
        mock_oses.current_review.return_value = mock_review
        orch.self_examination_service = mock_oses

        captured_context = {}

        class FakePlanner:
            def generate_plan(self, goal, *, context=''):
                captured_context['context'] = context
                return None

        orch.cloud_reasoning_planner = FakePlanner()

        orch.generate_cloud_plan('test goal')

        ctx = captured_context.get('context', '')
        assert 'OSES finding' in ctx
        assert 'Gemini degrading' in ctx


# ---------------------------------------------------------------------------
# 4. ValidationCycle cloud provider health pass
# ---------------------------------------------------------------------------


class TestValidationCycleCloudHealth:
    """_cloud_provider_health_pass must test keys and register in ExperimentLab."""

    def test_cloud_health_pass_skips_when_no_api_service(self):
        from iabv_v15.services.self_teach.autonomous_validation_cycle import (
            AutonomousValidationCycleService,
        )

        cycle = AutonomousValidationCycleService.__new__(
            AutonomousValidationCycleService
        )
        cycle.api_key_discovery_service = None
        cycle.decision_audit_trail = None
        cycle._cloud_health_tick_counter = 9  # next tick triggers

        # Should not raise
        cycle._cloud_provider_health_pass()

    def test_cloud_health_pass_runs_at_correct_interval(self):
        from iabv_v15.services.self_teach.autonomous_validation_cycle import (
            AutonomousValidationCycleService,
        )

        cycle = AutonomousValidationCycleService.__new__(
            AutonomousValidationCycleService
        )
        cycle.api_key_discovery_service = MagicMock()
        cycle.api_key_discovery_service.compare_all.return_value = []
        cycle.decision_audit_trail = None
        cycle._cloud_health_tick_counter = 0

        # tick 1-9 should NOT call compare_all
        for _ in range(9):
            cycle._cloud_provider_health_pass()
        cycle.api_key_discovery_service.compare_all.assert_not_called()

        # tick 10 should call it
        cycle._cloud_provider_health_pass()
        cycle.api_key_discovery_service.compare_all.assert_called_once()

    def test_cloud_health_pass_records_in_audit_trail(self):
        from iabv_v15.services.self_teach.autonomous_validation_cycle import (
            AutonomousValidationCycleService,
        )

        root = _tmp_data_root()
        try:
            from iabv_v15.services.evolution.decision_audit_trail import (
                DecisionAuditTrail,
            )

            audit = DecisionAuditTrail(data_root=str(root))

            mock_result = {
                'provider_id': 'groq',
                'latency_ms': 250.0,
                'status': 'valid',
                'model': 'llama-3.3-70b-versatile',
                'error': '',
            }
            mock_api = MagicMock()
            mock_api.compare_all.return_value = [mock_result]

            cycle = AutonomousValidationCycleService.__new__(
                AutonomousValidationCycleService
            )
            cycle.api_key_discovery_service = mock_api
            cycle.decision_audit_trail = audit
            cycle.experiment_lab = MagicMock()
            cycle._cloud_health_tick_counter = 9

            cycle._cloud_provider_health_pass()

            decisions = audit.load_recent(10)
            assert len(decisions) >= 1
            last = decisions[-1]
            assert last['provider_id'] == 'groq'
            assert last['phase'] == 'key_validation'
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_cloud_health_pass_registers_in_experiment_lab(self):
        from iabv_v15.services.self_teach.autonomous_validation_cycle import (
            AutonomousValidationCycleService,
        )

        mock_result = {
            'provider_id': 'gemini',
            'latency_ms': 500.0,
            'status': 'valid',
            'model': 'gemini-2.0-flash',
            'error': '',
        }
        mock_api = MagicMock()
        mock_api.compare_all.return_value = [mock_result]

        mock_lab = MagicMock()

        cycle = AutonomousValidationCycleService.__new__(
            AutonomousValidationCycleService
        )
        cycle.api_key_discovery_service = mock_api
        cycle.decision_audit_trail = None
        cycle.experiment_lab = mock_lab
        cycle._cloud_health_tick_counter = 9

        cycle._cloud_provider_health_pass()

        mock_lab.run_experiment.assert_called_once()
        call_kwargs = mock_lab.run_experiment.call_args
        assert 'CLOUD_REASONING' in str(call_kwargs)
        assert 'cloud_provider:gemini' in str(call_kwargs)


# ---------------------------------------------------------------------------
# 5. Full pipeline end-to-end
# ---------------------------------------------------------------------------


class TestFullPipelineE2E:
    """End-to-end: record decisions → OSES analyzes → PortableContext exports → Orchestrator reads."""

    def test_full_pipeline_from_decision_to_prescan(self):
        root = _tmp_data_root()
        try:
            from iabv_v15.services.evolution.decision_audit_trail import (
                DecisionAuditTrail,
                DecisionOutcome,
                DecisionPhase,
                DecisionRecord,
            )
            from iabv_v15.services.evolution.operational_self_examination_service import (
                OperationalSelfExaminationService,
            )
            from iabv_v15.services.evolution.portable_context_service import (
                PortableContextService,
            )
            from iabv_v15.domain.models import utc_now

            # Step 1: Record decisions
            audit = DecisionAuditTrail(data_root=str(root))
            for i in range(6):
                audit.record(DecisionRecord(
                    phase=DecisionPhase.PLAN_GENERATION,
                    provider_id='groq',
                    model_used='llama-3.3-70b-versatile',
                    user_goal=f'e2e test {i}',
                    outcome=DecisionOutcome.SUCCESS,
                    latency_ms=300.0,
                    confidence=0.85,
                ))
            # Add a degraded provider
            audit.record(DecisionRecord(
                phase=DecisionPhase.PLAN_GENERATION,
                provider_id='gemini',
                model_used='gemini-2.0-flash',
                user_goal='e2e test gemini',
                outcome=DecisionOutcome.RATE_LIMITED,
                latency_ms=0.0,
                confidence=0.0,
                error_detail='429',
            ))

            # Step 2: OSES reads audit and produces findings
            oses = OperationalSelfExaminationService.__new__(
                OperationalSelfExaminationService
            )
            oses.decision_audit_trail = audit
            findings = oses._cloud_reasoning_findings()
            assert len(findings) > 0

            # Step 3: PortableContext reads audit and builds section
            pcs = PortableContextService.__new__(PortableContextService)
            pcs.decision_audit_trail = audit
            snapshot = pcs._cloud_reasoning_snapshot()
            assert snapshot['status'] == 'analyzed'
            assert snapshot['total_decisions'] == 7
            section = pcs._cloud_reasoning_section(status=snapshot, now=utc_now())
            assert section.section_id == 'cloud_reasoning'
            assert section.confidence > 0

            # Step 4: Orchestrator pre-scan reads audit + OSES
            from iabv_v15.services.adaptive.adaptive_task_orchestrator import (
                AdaptiveTaskOrchestrator,
            )

            orch = AdaptiveTaskOrchestrator.__new__(AdaptiveTaskOrchestrator)
            orch.decision_audit_trail = audit
            orch.self_examination_service = None

            captured = {}

            class FakePlanner:
                def generate_plan(self, goal, *, context=''):
                    captured['context'] = context
                    return None

            orch.cloud_reasoning_planner = FakePlanner()
            orch.generate_cloud_plan('final e2e goal')

            ctx = captured.get('context', '')
            assert 'Cloud reasoning status' in ctx
            assert 'groq' in ctx.lower() or 'health=' in ctx
        finally:
            shutil.rmtree(root, ignore_errors=True)
