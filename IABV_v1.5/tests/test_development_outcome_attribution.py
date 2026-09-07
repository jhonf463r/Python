"""
Unit tests for TaskOutcome development outcome attribution.

Tests cover:
- Ordinary TaskOutcome without development attribution
- TaskOutcome with full/partial attribution
- Validation (empty/whitespace rejection, audit requires execution evidence)
- Real four-layer evidence graph (DTR -> DEE -> DAR -> TaskOutcome)
- Audit/outcome semantic separation (FAIL audit + SUCCESS outcome, etc.)
- JSON round-trip persistence
- Optional attribution (all None by default, partial allowed)
- No payload duplication (only IDs stored, not full objects)
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


class TestTaskOutcomeOrdinary:
    """Test ordinary TaskOutcome without development attribution."""

    def test_ordinary_outcome_no_attribution(self):
        """Ordinary TaskOutcome has no development attribution."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Ordinary task",
        )
        assert outcome.development_audit_result_id is None
        assert outcome.development_execution_evidence_id is None
        assert outcome.development_test_result_id is None


class TestTaskOutcomeAttribution:
    """Test TaskOutcome with development attribution."""

    def test_full_attribution(self):
        """TaskOutcome can have full development attribution."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Development task",
            development_audit_result_id="audit-123",
            development_execution_evidence_id="exec-456",
            development_test_result_id="test-789",
        )
        assert outcome.development_audit_result_id == "audit-123"
        assert outcome.development_execution_evidence_id == "exec-456"
        assert outcome.development_test_result_id == "test-789"

    def test_partial_attribution_execution_only(self):
        """TaskOutcome can have partial attribution (execution only)."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            development_execution_evidence_id="exec-456",
        )
        assert outcome.development_execution_evidence_id == "exec-456"
        assert outcome.development_audit_result_id is None
        assert outcome.development_test_result_id is None

    def test_partial_attribution_test_only(self):
        """TaskOutcome can have partial attribution (test only)."""
        outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            development_test_result_id="test-789",
        )
        assert outcome.development_test_result_id == "test-789"
        assert outcome.development_audit_result_id is None
        assert outcome.development_execution_evidence_id is None


class TestTaskOutcomeValidation:
    """Test TaskOutcome validation."""

    def test_audit_requires_execution_evidence(self):
        """development_audit_result_id requires development_execution_evidence_id."""
        with pytest.raises(ValueError, match="development_audit_result_id requires development_execution_evidence_id"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_audit_result_id="audit-123",
                development_execution_evidence_id=None,  # Missing
            )

    def test_empty_audit_id_rejected(self):
        """Empty development_audit_result_id is rejected."""
        with pytest.raises(ValueError, match="development_audit_result_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_audit_result_id="",
            )

    def test_whitespace_audit_id_rejected(self):
        """Whitespace-only development_audit_result_id is rejected."""
        with pytest.raises(ValueError, match="development_audit_result_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_audit_result_id="   ",
            )

    def test_empty_execution_id_rejected(self):
        """Empty development_execution_evidence_id is rejected."""
        with pytest.raises(ValueError, match="development_execution_evidence_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_execution_evidence_id="",
            )

    def test_whitespace_execution_id_rejected(self):
        """Whitespace-only development_execution_evidence_id is rejected."""
        with pytest.raises(ValueError, match="development_execution_evidence_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_execution_evidence_id="   ",
            )

    def test_empty_test_id_rejected(self):
        """Empty development_test_result_id is rejected."""
        with pytest.raises(ValueError, match="development_test_result_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_test_result_id="",
            )

    def test_whitespace_test_id_rejected(self):
        """Whitespace-only development_test_result_id is rejected."""
        with pytest.raises(ValueError, match="development_test_result_id must be non-empty when present"):
            TaskOutcome(
                status=RunStatus.SUCCESS,
                development_test_result_id="   ",
            )


class TestTaskOutcomeRealEvidenceGraph:
    """Test real four-layer evidence graph."""

    def test_four_layer_evidence_graph(self):
        """Demonstrate DTR -> DEE -> DAR -> TaskOutcome linkage."""
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
            summary="Development task completed",
            development_audit_result_id=audit_result.audit_id,
            development_execution_evidence_id=execution_evidence.evidence_id,
            development_test_result_id=test_result.test_result_id,
        )
        
        # Verify the linkage chain
        assert outcome.development_test_result_id == test_result.test_result_id
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert outcome.development_audit_result_id == audit_result.audit_id
        
        # Verify no duplication of payloads
        assert outcome.development_test_result_id == test_result.test_result_id
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert outcome.development_audit_result_id == audit_result.audit_id
        assert "findings" not in outcome.metadata
        assert "repository" not in outcome.metadata
        assert "stdout" not in outcome.metadata


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
