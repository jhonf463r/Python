"""
Tests for development outcome attribution on TaskOutcome.

Tests verify:
- Ordinary TaskOutcome without development attribution
- TaskOutcome with development audit attribution
- Audit → execution evidence linkage
- Execution evidence → test result linkage
- JSON round-trip
- FAIL audit + SUCCESS outcome (semantic separation)
- INCONCLUSIVE audit + SUCCESS outcome
- Generated IDs remain distinct
- No payload duplication
- Attribution remains optional
- Existing TaskOutcomeRecorder behavior remains valid
"""

import pytest
from iabv_v15.domain.models import (
    TaskOutcome,
    RunStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentAuditResult,
    DevelopmentAuditVerdict,
    EvidenceRef,
    EvidenceKind,
)


class TestTaskOutcomeWithoutDevelopmentAttribution:
    """Test that ordinary TaskOutcome works without development attribution."""

    def test_minimal_outcome(self):
        """TaskOutcome can be created without any development attribution."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Task completed successfully",
        )
        assert outcome.outcome_id is not None
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id is None
        assert outcome.development_execution_evidence_id is None
        assert outcome.development_test_result_id is None

    def test_outcome_with_evidence_refs(self):
        """TaskOutcome with evidence_refs but no development attribution."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Task completed",
            evidence_refs=["evidence-1", "evidence-2"],
        )
        assert len(outcome.evidence_refs) == 2
        assert outcome.development_audit_result_id is None


class TestTaskOutcomeWithDevelopmentAttribution:
    """Test TaskOutcome with development attribution."""

    def test_outcome_with_full_attribution(self):
        """TaskOutcome with all three development attribution fields."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Development task completed",
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
            development_test_result_id="test-789",
        )
        assert outcome.development_audit_result_id == "audit-123"
        assert outcome.development_execution_evidence_id == "exec-456"
        assert outcome.development_test_result_id == "test-789"

    def test_outcome_with_only_execution_evidence(self):
        """TaskOutcome with only execution evidence (no audit or test)."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Execution evidence only",
            development_execution_evidence_id="exec-456",
        )
        assert outcome.development_execution_evidence_id == "exec-456"
        assert outcome.development_audit_result_id is None
        assert outcome.development_test_result_id is None

    def test_outcome_with_audit_requires_execution_evidence(self):
        """Audit result ID requires execution evidence ID."""
        with pytest.raises(ValueError, match="development_audit_result_id requires development_execution_evidence_id"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                summary="Invalid attribution",
                development_audit_result_id="audit-123",
            )


class TestTaskOutcomeAttributionValidation:
    """Test validation of development attribution fields."""

    def test_empty_audit_result_id_rejected(self):
        """Empty audit_result_id is rejected."""
        with pytest.raises(ValueError, match="development_audit_result_id cannot be empty"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_audit_result_id="",
                development_execution_evidence_id="exec-456",
            )

    def test_whitespace_audit_result_id_rejected(self):
        """Whitespace-only audit_result_id is rejected."""
        with pytest.raises(ValueError, match="development_audit_result_id cannot be empty"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_audit_result_id="   ",
                development_execution_evidence_id="exec-456",
            )

    def test_empty_execution_evidence_id_rejected(self):
        """Empty execution_evidence_id is rejected."""
        with pytest.raises(ValueError, match="development_execution_evidence_id cannot be empty"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_execution_evidence_id="",
            )

    def test_empty_test_result_id_rejected(self):
        """Empty test_result_id is rejected."""
        with pytest.raises(ValueError, match="development_test_result_id cannot be empty"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_test_result_id="",
            )


class TestRealDevelopmentAttributionGraph:
    """Test real four-layer evidence graph: DTR -> DEE -> DAR -> TaskOutcome."""

    def test_four_layer_attribution_graph(self):
        """Demonstrate complete evidence graph with generated IDs."""
        # Layer 1: DevelopmentTestResult
        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
            duration_seconds=5.0,
        )
        
        # Layer 2: DevelopmentExecutionEvidence
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result.test_result_id,
                )
            ],
        )
        
        # Layer 3: DevelopmentAuditResult
        audit_result = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        # Layer 4: TaskOutcome
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Development task completed successfully",
            development_audit_result_id=audit_result.audit_id,
            development_execution_evidence_id=execution_evidence.evidence_id,
            development_test_result_id=test_result.test_result_id,
        )
        
        # Verify the linkage chain
        assert test_result.test_result_id == execution_evidence.test_result_id
        assert execution_evidence.evidence_refs[0].ref_id == test_result.test_result_id
        assert audit_result.execution_evidence_id == execution_evidence.evidence_id
        assert audit_result.evidence_refs[0].ref_id == execution_evidence.evidence_id
        assert outcome.development_test_result_id == test_result.test_result_id
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert outcome.development_audit_result_id == audit_result.audit_id
        
        # Verify no duplication of payloads
        assert outcome.development_test_result_id == test_result.test_result_id
        assert "test_result" not in outcome.metadata
        assert "repository" not in outcome.metadata
        assert "verdict" not in outcome.metadata
        
        # Verify IDs are distinct
        assert test_result.test_result_id != execution_evidence.evidence_id
        assert execution_evidence.evidence_id != audit_result.audit_id
        assert audit_result.audit_id != outcome.outcome_id


class TestAuditOutcomeSemanticSeparation:
    """Test that audit verdict and outcome status remain distinct."""

    def test_fail_audit_with_success_outcome(self):
        """FAIL audit verdict can coexist with SUCCESS outcome status."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Operational success despite audit failure",
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
        )
        # The audit verdict would be FAIL (stored in DevelopmentAuditResult)
        # but the operational outcome is SUCCESS
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == "audit-123"
        # No automatic mapping - both facts are preserved

    def test_inconclusive_audit_with_success_outcome(self):
        """INCONCLUSIVE audit verdict can coexist with SUCCESS outcome status."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Operational success with inconclusive audit",
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
        )
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == "audit-123"
        # INCONCLUSIVE does not automatically become FAILED

    def test_pass_audit_with_failed_outcome(self):
        """PASS audit verdict can coexist with FAILED outcome status."""
        outcome = TaskOutcome(
            status=RunStatus.FAILED,
            summary="Operational failure despite audit pass",
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
        )
        assert outcome.status == RunStatus.FAILED
        assert outcome.development_audit_result_id == "audit-123"
        # PASS audit does not force SUCCESS outcome


class TestTaskOutcomePersistence:
    """Test JSON round-trip persistence with attribution."""

    def test_json_round_trip_with_attribution(self):
        """JSON serialization preserves all attribution fields."""
        original = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Development task",
            next_actions=["action-1", "action-2"],
            evidence_refs=["ev-1"],
            metadata={"key": "value"},
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
            development_test_result_id="test-789",
        )
        
        json_data = original.model_dump(mode='json')
        restored = TaskOutcome(**json_data)
        
        assert restored.outcome_id == original.outcome_id
        assert restored.status == original.status
        assert restored.summary == original.summary
        assert restored.next_actions == original.next_actions
        assert restored.evidence_refs == original.evidence_refs
        assert restored.metadata == original.metadata
        assert restored.development_audit_result_id == original.development_audit_result_id
        assert restored.development_execution_evidence_id == original.development_execution_evidence_id
        assert restored.development_test_result_id == original.development_test_result_id

    def test_json_round_trip_without_attribution(self):
        """JSON serialization works for non-development outcomes."""
        original = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Ordinary task",
        )
        
        json_data = original.model_dump(mode='json')
        restored = TaskOutcome(**json_data)
        
        assert restored.development_audit_result_id is None
        assert restored.development_execution_evidence_id is None
        assert restored.development_test_result_id is None


class TestTaskOutcomeOptionalAttribution:
    """Test that attribution is truly optional."""

    def test_attribution_all_none_by_default(self):
        """All attribution fields default to None."""
        outcome = TaskOutcome()
        assert outcome.development_audit_result_id is None
        assert outcome.development_execution_evidence_id is None
        assert outcome.development_test_result_id is None

    def test_partial_attribution_allowed(self):
        """Partial attribution (only some fields) is allowed."""
        outcome = TaskOutcome(
            development_execution_evidence_id="exec-456",
        )
        assert outcome.development_execution_evidence_id == "exec-456"
        assert outcome.development_audit_result_id is None
        assert outcome.development_test_result_id is None


class TestNoPayloadDuplication:
    """Test that TaskOutcome does not duplicate evidence payloads."""

    def test_outcome_does_not_contain_full_audit_result(self):
        """TaskOutcome only stores audit ID, not full audit result."""
        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result.test_result_id,
                )
            ],
        )
        audit_result = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            findings=[],  # Findings are NOT copied to TaskOutcome
        )
        
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            development_audit_result_id=audit_result.audit_id,
            development_execution_evidence_id=execution_evidence.evidence_id,
        )
        
        # Verify only IDs are stored
        assert outcome.development_audit_result_id == audit_result.audit_id
        assert "findings" not in outcome.metadata
        assert "verdict" not in outcome.metadata
        assert "criteria" not in outcome.metadata

    def test_outcome_does_not_contain_full_execution_evidence(self):
        """TaskOutcome only stores execution evidence ID, not full evidence."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            base_commit="abc123",
            result_commit="def456",
            changed_files=["file1.py", "file2.py"],
        )
        
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            development_execution_evidence_id=execution_evidence.evidence_id,
        )
        
        # Verify only ID is stored
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert "repository" not in outcome.metadata
        assert "base_commit" not in outcome.metadata
        assert "changed_files" not in outcome.metadata

    def test_outcome_does_not_contain_full_test_result(self):
        """TaskOutcome only stores test result ID, not full result."""
        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
            stdout="Test output...",
            stderr="",
            test_count=100,
            passed_count=100,
            failed_count=0,
        )
        
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            development_test_result_id=test_result.test_result_id,
        )
        
        # Verify only ID is stored
        assert outcome.development_test_result_id == test_result.test_result_id
        assert "stdout" not in outcome.metadata
        assert "test_count" not in outcome.metadata
        assert "passed_count" not in outcome.metadata
