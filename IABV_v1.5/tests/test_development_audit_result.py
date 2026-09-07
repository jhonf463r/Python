"""
Unit tests for DevelopmentAuditResult domain model.

Tests cover:
- DevelopmentAuditVerdict enum (PASS, FAIL, INCONCLUSIVE)
- DevelopmentAuditFinding model
- DevelopmentAuditCriterion model
- Minimal/complete audit result construction
- Target evidence ID validation
- EvidenceRef coherence (matching, mismatched, multiple refs)
- Findings handling (PASS with no findings, FAIL with findings, INCONCLUSIVE with explanation)
- JSON round-trip persistence
- Real three-layer evidence graph test (DevelopmentTestResult -> DevelopmentExecutionEvidence -> DevelopmentAuditResult)
"""

import pytest
from datetime import datetime, timezone
from iabv_v15.domain.models import (
    DevelopmentAuditResult,
    DevelopmentAuditVerdict,
    DevelopmentAuditFinding,
    DevelopmentAuditCriterion,
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    EvidenceRef,
    EvidenceKind,
    IssueSeverity,
)


class TestDevelopmentAuditVerdict:
    """Test DevelopmentAuditVerdict enum."""

    def test_pass_verdict(self):
        """PASS verdict exists."""
        assert DevelopmentAuditVerdict.PASS == "pass"

    def test_fail_verdict(self):
        """FAIL verdict exists."""
        assert DevelopmentAuditVerdict.FAIL == "fail"

    def test_inconclusive_verdict(self):
        """INCONCLUSIVE verdict exists."""
        assert DevelopmentAuditVerdict.INCONCLUSIVE == "inconclusive"


class TestDevelopmentAuditFinding:
    """Test DevelopmentAuditFinding model."""

    def test_minimal_finding(self):
        """Finding can be constructed with minimal fields."""
        finding = DevelopmentAuditFinding(
            severity=IssueSeverity.HIGH,
            summary="Test coverage below threshold",
        )
        assert finding.severity == IssueSeverity.HIGH
        assert finding.summary == "Test coverage below threshold"
        assert finding.criterion is None
        assert finding.details == ""
        assert finding.location is None

    def test_complete_finding(self):
        """Finding can be constructed with all fields."""
        finding = DevelopmentAuditFinding(
            severity=IssueSeverity.MEDIUM,
            summary="Documentation incomplete",
            criterion="documentation",
            details="Missing docstrings in 3 modules",
            location="src/module.py",
            metadata={"line_count": 150},
        )
        assert finding.severity == IssueSeverity.MEDIUM
        assert finding.summary == "Documentation incomplete"
        assert finding.criterion == "documentation"
        assert finding.details == "Missing docstrings in 3 modules"
        assert finding.location == "src/module.py"
        assert finding.metadata == {"line_count": 150}


class TestDevelopmentAuditCriterion:
    """Test DevelopmentAuditCriterion model."""

    def test_minimal_criterion(self):
        """Criterion can be constructed with minimal fields."""
        criterion = DevelopmentAuditCriterion(
            criterion_id="criterion-1",
            name="Test Coverage",
            status="satisfied",
        )
        assert criterion.criterion_id == "criterion-1"
        assert criterion.name == "Test Coverage"
        assert criterion.status == "satisfied"
        assert criterion.description == ""

    def test_complete_criterion(self):
        """Criterion can be constructed with all fields."""
        criterion = DevelopmentAuditCriterion(
            criterion_id="criterion-1",
            name="Test Coverage",
            status="satisfied",
            description="Minimum 80% test coverage required",
            metadata={"threshold": 0.8},
        )
        assert criterion.criterion_id == "criterion-1"
        assert criterion.name == "Test Coverage"
        assert criterion.status == "satisfied"
        assert criterion.description == "Minimum 80% test coverage required"
        assert criterion.metadata == {"threshold": 0.8}


class TestDevelopmentAuditResultConstruction:
    """Test audit result construction."""

    def test_minimal_audit_result(self):
        """Audit result can be constructed with minimal fields."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
        )
        assert audit_result.execution_evidence_id == "exec-evidence-123"
        assert audit_result.verdict == DevelopmentAuditVerdict.PASS
        assert audit_result.auditor_id is None
        assert audit_result.findings == []
        assert audit_result.criteria == []
        assert audit_result.evidence_refs == []

    def test_complete_audit_result(self):
        """Audit result can be constructed with all fields."""
        audited_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.FAIL,
            auditor_id="auditor-001",
            audited_at_utc=audited_at,
            findings=[
                DevelopmentAuditFinding(
                    severity=IssueSeverity.HIGH,
                    summary="Test coverage below threshold",
                    criterion="test_coverage",
                )
            ],
            criteria=[
                DevelopmentAuditCriterion(
                    criterion_id="criterion-1",
                    name="Test Coverage",
                    status="not_satisfied",
                )
            ],
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id="exec-evidence-123",
                )
            ],
            metadata={"audit_type": "manual"},
        )
        
        assert audit_result.execution_evidence_id == "exec-evidence-123"
        assert audit_result.verdict == DevelopmentAuditVerdict.FAIL
        assert audit_result.auditor_id == "auditor-001"
        assert audit_result.audited_at_utc == audited_at
        assert len(audit_result.findings) == 1
        assert len(audit_result.criteria) == 1
        assert len(audit_result.evidence_refs) == 1
        assert audit_result.metadata == {"audit_type": "manual"}


class TestDevelopmentAuditResultValidation:
    """Test audit result validation."""

    def test_empty_execution_evidence_id_rejected(self):
        """Empty execution_evidence_id is rejected."""
        with pytest.raises(ValueError, match="execution_evidence_id must be non-empty"):
            DevelopmentAuditResult(
                execution_evidence_id="",
                verdict=DevelopmentAuditVerdict.PASS,
            )

    def test_whitespace_execution_evidence_id_rejected(self):
        """Whitespace-only execution_evidence_id is rejected."""
        with pytest.raises(ValueError, match="execution_evidence_id must be non-empty"):
            DevelopmentAuditResult(
                execution_evidence_id="   ",
                verdict=DevelopmentAuditVerdict.PASS,
            )

    def test_matching_development_exec_ref_allowed(self):
        """Matching DEVELOPMENT_EXECUTION EvidenceRef is allowed."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id="exec-evidence-123",
                )
            ],
        )
        assert len(audit_result.evidence_refs) == 1

    def test_mismatched_development_exec_ref_rejected(self):
        """Mismatched DEVELOPMENT_EXECUTION EvidenceRef is rejected."""
        with pytest.raises(ValueError, match="DEVELOPMENT_EXECUTION evidence_ref must match execution_evidence_id"):
            DevelopmentAuditResult(
                execution_evidence_id="exec-evidence-123",
                verdict=DevelopmentAuditVerdict.PASS,
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                        label="Execution evidence",
                        ref_id="exec-evidence-456",  # Mismatch
                    )
                ],
            )

    def test_multiple_development_exec_refs_rejected(self):
        """Multiple DEVELOPMENT_EXECUTION EvidenceRefs are rejected."""
        with pytest.raises(ValueError, match="Multiple DEVELOPMENT_EXECUTION evidence_refs not allowed"):
            DevelopmentAuditResult(
                execution_evidence_id="exec-evidence-123",
                verdict=DevelopmentAuditVerdict.PASS,
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                        label="Execution evidence 1",
                        ref_id="exec-evidence-123",
                    ),
                    EvidenceRef(
                        kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                        label="Execution evidence 2",
                        ref_id="exec-evidence-123",
                    )
                ],
            )

    def test_non_development_exec_refs_allowed(self):
        """Non-DEVELOPMENT_EXECUTION EvidenceRefs are allowed."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
                ),
                EvidenceRef(
                    kind=EvidenceKind.ARTIFACT,
                    label="Build artifact",
                    ref_id="artifact-789",
                )
            ],
        )
        assert len(audit_result.evidence_refs) == 2

    def test_no_development_exec_ref_allowed(self):
        """No DEVELOPMENT_EXECUTION EvidenceRef is allowed."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.LOG,
                    label="Execution log",
                    ref_id="log-456",
                )
            ],
        )
        assert len(audit_result.evidence_refs) == 1


class TestDevelopmentAuditResultFindings:
    """Test findings handling."""

    def test_pass_with_no_findings(self):
        """PASS verdict with zero findings is valid."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
            findings=[],
        )
        assert audit_result.verdict == DevelopmentAuditVerdict.PASS
        assert len(audit_result.findings) == 0

    def test_fail_with_findings(self):
        """FAIL verdict with findings is valid."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.FAIL,
            findings=[
                DevelopmentAuditFinding(
                    severity=IssueSeverity.HIGH,
                    summary="Test coverage below threshold",
                    criterion="test_coverage",
                ),
                DevelopmentAuditFinding(
                    severity=IssueSeverity.MEDIUM,
                    summary="Documentation incomplete",
                    criterion="documentation",
                )
            ],
        )
        assert audit_result.verdict == DevelopmentAuditVerdict.FAIL
        assert len(audit_result.findings) == 2

    def test_inconclusive_with_explanatory_finding(self):
        """INCONCLUSIVE verdict with explanatory finding is valid."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.INCONCLUSIVE,
            findings=[
                DevelopmentAuditFinding(
                    severity=IssueSeverity.LOW,
                    summary="Insufficient evidence to determine test coverage",
                    criterion="test_coverage",
                )
            ],
        )
        assert audit_result.verdict == DevelopmentAuditVerdict.INCONCLUSIVE
        assert len(audit_result.findings) == 1


class TestDevelopmentAuditResultPersistence:
    """Test JSON round-trip persistence."""

    def test_json_round_trip(self):
        """JSON serialization and deserialization preserves all fields."""
        audited_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        original = DevelopmentAuditResult(
            execution_evidence_id="exec-evidence-123",
            verdict=DevelopmentAuditVerdict.PASS,
            auditor_id="auditor-001",
            audited_at_utc=audited_at,
            findings=[
                DevelopmentAuditFinding(
                    severity=IssueSeverity.LOW,
                    summary="Minor observation",
                    criterion="documentation",
                )
            ],
            criteria=[
                DevelopmentAuditCriterion(
                    criterion_id="criterion-1",
                    name="Test Coverage",
                    status="satisfied",
                )
            ],
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id="exec-evidence-123",
                )
            ],
            metadata={"audit_type": "manual"},
        )

        json_data = original.model_dump(mode='json')
        restored = DevelopmentAuditResult(**json_data)

        assert restored.audit_id == original.audit_id
        assert restored.execution_evidence_id == original.execution_evidence_id
        assert restored.verdict == original.verdict
        assert restored.auditor_id == original.auditor_id
        assert restored.audited_at_utc == original.audited_at_utc
        assert len(restored.findings) == 1
        assert restored.findings[0].summary == "Minor observation"
        assert len(restored.criteria) == 1
        assert restored.criteria[0].name == "Test Coverage"
        assert len(restored.evidence_refs) == 1
        assert restored.evidence_refs[0].kind == EvidenceKind.DEVELOPMENT_EXECUTION
        assert restored.metadata == original.metadata


class TestDevelopmentAuditResultRealEvidenceGraph:
    """Test real evidence graph linkage."""

    def test_three_layer_evidence_graph(self):
        """Demonstrate DevelopmentTestResult -> DevelopmentExecutionEvidence -> DevelopmentAuditResult linkage."""
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
        
        # Verify the linkage chain
        assert test_result.test_result_id == execution_evidence.test_result_id
        assert execution_evidence.evidence_refs[0].ref_id == test_result.test_result_id
        assert audit_result.execution_evidence_id == execution_evidence.evidence_id
        assert audit_result.evidence_refs[0].ref_id == execution_evidence.evidence_id
        
        # Verify no duplication of payloads
        assert audit_result.execution_evidence_id == execution_evidence.evidence_id
        assert "test_result" not in audit_result.metadata
        assert "repository" not in audit_result.metadata
