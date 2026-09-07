"""
Tests for DevelopmentOutcomeAttributionBuilder.

These tests verify that the application-layer construction gate prevents
false cross-layer evidence graphs by validating coherence between real objects.

All tests use REAL instantiated objects, not arbitrary string IDs.
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
from iabv_v15.services.development.development_outcome_attribution_builder import (
    DevelopmentOutcomeAttributionBuilder,
    DevelopmentOutcomeAttributionError,
)


class TestRealCoherentGraph:
    """TEST 1 — REAL COHERENT GRAPH: DTR-A -> DEE-A -> DAR-A -> TaskOutcome"""

    def test_real_coherent_graph_passes(self):
        """A fully coherent evidence graph should be accepted."""
        # Layer 1: DevelopmentTestResult-A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Layer 2: DevelopmentExecutionEvidence-A (references DTR-A)
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        # Layer 3: DevelopmentAuditResult-A (references DEE-A)
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build TaskOutcome with coherent graph
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Verify attribution is correct
        assert outcome.development_audit_result_id == audit_result_a.audit_id
        assert outcome.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert outcome.development_test_result_id == test_result_a.test_result_id
        assert outcome.status == RunStatus.SUCCESS


class TestAuditAExecutionB:
    """TEST 2 — AUDIT A + EXECUTION B: Reject cross-graph incoherence."""

    def test_audit_a_with_execution_b_rejected(self):
        """Audit referencing execution A cannot be combined with execution B."""
        # Create execution evidence A
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
        )
        
        # Create execution evidence B (different object)
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
        )
        
        # Create audit referencing execution A
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Attempt to build with audit A but execution B
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cross-graph incoherence"):
            builder.build(
                audit_result=audit_result_a,
                execution_evidence=execution_evidence_b,
            )


class TestExecutionATestResultB:
    """TEST 3 — EXECUTION A + TEST RESULT B: Reject cross-graph incoherence."""

    def test_execution_a_with_test_result_b_rejected(self):
        """Execution referencing test A cannot be combined with test B."""
        # Create test result A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create test result B (different object)
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create execution evidence referencing test A
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        # Attempt to build with execution A but test B
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cross-graph incoherence"):
            builder.build(
                execution_evidence=execution_evidence_a,
                test_result=test_result_b,
            )


class TestAuditAExecutionATestB:
    """TEST 4 — AUDIT A + EXECUTION A + TEST B: Reject cross-graph incoherence."""

    def test_audit_a_execution_a_with_test_b_rejected(self):
        """Audit and execution are coherent, but test result is from different graph."""
        # Create test result A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create test result B (different object)
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create execution evidence referencing test A
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        # Create audit referencing execution A
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Attempt to build with audit A, execution A, but test B
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cross-graph incoherence"):
            builder.build(
                audit_result=audit_result_a,
                execution_evidence=execution_evidence_a,
                test_result=test_result_b,
            )


class TestAuditAExecutionBTestB:
    """TEST 5 — AUDIT A + EXECUTION B + TEST B: Reject due to audit↔execution incoherence."""

    def test_audit_a_with_execution_b_test_b_rejected(self):
        """Audit↔execution incoherence should be detected first."""
        # Create test result B
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create execution evidence B (references test B)
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
            test_result_id=test_result_b.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_b.test_result_id,
                )
            ],
        )
        
        # Create execution evidence A (different object)
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
        )
        
        # Create audit referencing execution A
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Attempt to build with audit A, execution B, test B
        # Should reject due to audit↔execution incoherence
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cross-graph incoherence"):
            builder.build(
                audit_result=audit_result_a,
                execution_evidence=execution_evidence_b,
                test_result=test_result_b,
            )


class TestIndependentRealIds:
    """TEST 6 — INDEPENDENT REAL IDS: All IDs valid but from different graphs."""

    def test_independent_real_ids_rejected(self):
        """Objects from different evidence graphs should be rejected."""
        # Create test result A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create test result B (different object)
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create execution evidence A (references test A)
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        # Create execution evidence B (references test B)
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
            test_result_id=test_result_b.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_b.test_result_id,
                )
            ],
        )
        
        # Create audit referencing execution A
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Attempt to build with audit A, execution B, test B
        # This should reject because audit references execution A but we provide execution B
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cross-graph incoherence"):
            builder.build(
                audit_result=audit_result_a,
                execution_evidence=execution_evidence_b,
                test_result=test_result_b,
            )


class TestValidPartialAttribution:
    """TEST 7 — VALID PARTIAL ATTRIBUTION: Only execution evidence, no audit or test."""

    def test_valid_partial_attribution_execution_only(self):
        """Partial attribution with only execution evidence should be allowed."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            execution_evidence=execution_evidence,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert outcome.development_audit_result_id is None
        assert outcome.development_test_result_id is None

    def test_valid_partial_attribution_execution_and_test(self):
        """Partial attribution with execution and test should be allowed if coherent."""
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
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.development_execution_evidence_id == execution_evidence.evidence_id
        assert outcome.development_test_result_id == test_result.test_result_id
        assert outcome.development_audit_result_id is None


class TestAuditWithoutExecution:
    """TEST 8 — AUDIT WITHOUT EXECUTION: Reject audit without execution evidence."""

    def test_audit_without_execution_rejected(self):
        """Audit result requires execution evidence."""
        audit_result = DevelopmentAuditResult(
            execution_evidence_id="some-execution-id",  # Has an ID, but we don't provide the object
            verdict=DevelopmentAuditVerdict.PASS,
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="requires DevelopmentExecutionEvidence"):
            builder.build(
                audit_result=audit_result,
            )


class TestOrdinaryOutcome:
    """TEST 9 — ORDINARY OUTCOME: TaskOutcome without development attribution."""

    def test_ordinary_outcome_without_attribution(self):
        """TaskOutcome without any development attribution should be allowed."""
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(outcome_status=RunStatus.SUCCESS)
        
        assert outcome.development_audit_result_id is None
        assert outcome.development_execution_evidence_id is None
        assert outcome.development_test_result_id is None
        assert outcome.status == RunStatus.SUCCESS


class TestPersistence:
    """TEST 10 — PERSISTENCE: Serialize and reconstruct with references intact."""

    def test_persistence_round_trip(self):
        """Build coherent attributed TaskOutcome, serialize, reconstruct, verify references."""
        # Create coherent graph
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
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        # Build TaskOutcome
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Serialize
        json_data = outcome.model_dump(mode='json')
        
        # Reconstruct
        reconstructed = TaskOutcome(**json_data)
        
        # Verify references survive unchanged
        assert reconstructed.development_audit_result_id == audit_result.audit_id
        assert reconstructed.development_execution_evidence_id == execution_evidence.evidence_id
        assert reconstructed.development_test_result_id == test_result.test_result_id


class TestSemanticSeparation:
    """TEST 11 — SEMANTIC SEPARATION: Audit verdict and outcome status remain independent."""

    def test_fail_audit_with_success_outcome(self):
        """FAIL audit verdict can coexist with SUCCESS outcome status."""
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
            verdict=DevelopmentAuditVerdict.FAIL,  # FAIL verdict
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        # Build with SUCCESS outcome status
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Both facts are preserved independently
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == audit_result.audit_id
        # No automatic mapping from FAIL audit to FAILED outcome

    def test_inconclusive_audit_with_success_outcome(self):
        """INCONCLUSIVE audit verdict can coexist with SUCCESS outcome status."""
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
            verdict=DevelopmentAuditVerdict.INCONCLUSIVE,  # INCONCLUSIVE verdict
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == audit_result.audit_id
        # INCONCLUSIVE does not automatically become FAILED

    def test_pass_audit_with_failure_outcome(self):
        """PASS audit verdict can coexist with FAILED outcome status."""
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
            verdict=DevelopmentAuditVerdict.PASS,  # PASS verdict
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        # Build with FAILED outcome status
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            task_outcome=TaskOutcome(status=RunStatus.FAILED, summary="Operational failure"),
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
        )
        
        assert outcome.status == RunStatus.FAILED
        assert outcome.development_audit_result_id == audit_result.audit_id
        # PASS audit does not force SUCCESS outcome


class TestAugmentExistingOutcome:
    """Test augmenting an existing TaskOutcome with development attribution."""

    def test_augment_existing_outcome(self):
        """Builder should be able to augment an existing TaskOutcome."""
        existing_outcome = TaskOutcome(
            status=RunStatus.SUCCESS,
            summary="Existing outcome",
            next_actions=["action-1"],
            metadata={"key": "value"},
        )
        
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
        
        builder = DevelopmentOutcomeAttributionBuilder()
        augmented = builder.build(
            task_outcome=existing_outcome,
            execution_evidence=execution_evidence,
            test_result=test_result,
        )
        
        # Original fields preserved
        assert augmented.status == existing_outcome.status
        assert augmented.summary == existing_outcome.summary
        assert augmented.next_actions == existing_outcome.next_actions
        assert augmented.metadata == existing_outcome.metadata
        
        # Attribution added
        assert augmented.development_execution_evidence_id == execution_evidence.evidence_id
        assert augmented.development_test_result_id == test_result.test_result_id


class TestAugmentationIntegrity:
    """TEST A — REJECT MIXED GRAPH AUGMENT: Existing graph A + execution B."""

    def test_reject_mixed_graph_augment(self):
        """Existing coherent graph A cannot be augmented with execution B."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build attributed outcome A
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Create execution B (different graph)
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
        )
        
        # Attempt to augment with execution B
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Augmentation would corrupt existing attribution"):
            builder.build(
                task_outcome=outcome_a,
                execution_evidence=execution_evidence_b,
            )


class TestPreserveExistingGraph:
    """TEST B — PRESERVE EXISTING GRAPH: Existing graph A + no new attribution objects."""

    def test_preserve_existing_graph(self):
        """Existing attribution must be preserved when no new objects provided."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Augment with no new objects
        augmented = builder.build(task_outcome=outcome_a)
        
        # All existing IDs must be preserved
        assert augmented.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert augmented.development_test_result_id == test_result_a.test_result_id


class TestRejectPartialOverwrite:
    """TEST C — REJECT PARTIAL OVERWRITE: Existing graph A + only test B."""

    def test_reject_partial_overwrite(self):
        """Existing graph A cannot be partially overwritten with test B."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Create test B
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Attempt to augment with only test B
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Augmentation would corrupt existing attribution"):
            builder.build(
                task_outcome=outcome_a,
                test_result=test_result_b,
            )


class TestAcceptSameGraphAugment:
    """TEST D — ACCEPT SAME-GRAPH AUGMENT: Existing execution A + test A."""

    def test_accept_same_graph_augment(self):
        """Existing execution A can be augmented with test A if coherent."""
        # Create test A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        # Create execution A (references test A)
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            execution_evidence=execution_evidence_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Augment with test A
        augmented = builder.build(
            task_outcome=outcome_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
        )
        
        # Should succeed and include test attribution
        assert augmented.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert augmented.development_test_result_id == test_result_a.test_result_id


class TestRejectExecutionWithoutTestReference:
    """TEST E — REJECT EXECUTION WITHOUT TEST REFERENCE: DEE-A.test_result_id=None + TEST-B."""

    def test_reject_execution_without_test_reference(self):
        """Execution with test_result_id=None cannot be combined with any test_result."""
        # Create execution A with no test reference
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=None,  # No test reference
        )
        
        # Create test B
        test_result_b = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="execution_evidence.test_result_id is None"):
            builder.build(
                execution_evidence=execution_evidence_a,
                test_result=test_result_b,
            )


class TestRejectTestOnlyAttribution:
    """TEST G — REJECT TEST-ONLY ATTRIBUTION: test_result only without execution."""

    def test_reject_test_only_attribution(self):
        """Test result alone is invalid for development attribution."""
        test_result = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Test result alone is invalid"):
            builder.build(
                test_result=test_result,
            )


class TestOriginalOutcomeImmutableAfterFailedAugment:
    """TEST H — ORIGINAL OUTCOME IMMUTABLE AFTER FAILED AUGMENT."""

    def test_original_outcome_immutable_after_failed_augment(self):
        """Original outcome must remain unchanged after rejected augmentation."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Store original IDs
        original_execution_id = outcome_a.development_execution_evidence_id
        original_test_id = outcome_a.development_test_result_id
        
        # Create execution B (different graph)
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
        )
        
        # Attempt invalid augment
        with pytest.raises(DevelopmentOutcomeAttributionError):
            builder.build(
                task_outcome=outcome_a,
                execution_evidence=execution_evidence_b,
            )
        
        # Original outcome must remain unchanged
        assert outcome_a.development_execution_evidence_id == original_execution_id
        assert outcome_a.development_test_result_id == original_test_id


class TestAuditIdentityPreservation:
    """MANDATORY TEST — AUDIT SWAP REJECTION: Existing audit=A + new audit=B with same execution."""

    def test_reject_audit_swap_with_same_execution(self):
        """Audit identity cannot be swapped even when new audit references same execution."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build attributed outcome A
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Create audit B (different audit, same execution reference, different verdict)
        audit_result_b = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,  # Same execution
            verdict=DevelopmentAuditVerdict.FAIL,  # Different verdict
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Store original IDs
        original_audit_id = outcome_a.development_audit_result_id
        original_execution_id = outcome_a.development_execution_evidence_id
        original_test_id = outcome_a.development_test_result_id
        
        # Attempt audit swap
        with pytest.raises(DevelopmentOutcomeAttributionError, match="Cannot replace audit identity"):
            builder.build(
                task_outcome=outcome_a,
                audit_result=audit_result_b,
                execution_evidence=execution_evidence_a,
            )
        
        # Original outcome must remain unchanged
        assert outcome_a.development_audit_result_id == original_audit_id
        assert outcome_a.development_execution_evidence_id == original_execution_id
        assert outcome_a.development_test_result_id == original_test_id


class TestSameAuditAugment:
    """MANDATORY TEST — SAME AUDIT: Existing audit=A + new audit=A."""

    def test_accept_same_audit_augment(self):
        """Augmenting with the same audit object must be allowed."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build attributed outcome A
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Augment with same audit and execution
        augmented = builder.build(
            task_outcome=outcome_a,
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
        )
        
        # Audit identity must remain A
        assert augmented.development_audit_result_id == audit_result_a.audit_id
        assert augmented.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert augmented.development_test_result_id == test_result_a.test_result_id


class TestOmittedAuditAugment:
    """MANDATORY TEST — OMITTED AUDIT: Existing audit=A + no new audit."""

    def test_preserve_audit_when_omitted(self):
        """Audit must be preserved when not provided in augmentation."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build attributed outcome A
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Augment with only execution (no audit)
        augmented = builder.build(
            task_outcome=outcome_a,
            execution_evidence=execution_evidence_a,
        )
        
        # Audit A must remain unchanged
        assert augmented.development_audit_result_id == audit_result_a.audit_id
        assert augmented.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert augmented.development_test_result_id == test_result_a.test_result_id


class TestCrossGraphAudit:
    """MANDATORY TEST — CROSS GRAPH AUDIT: Existing audit=A + execution=A, new audit=B + execution=B."""

    def test_reject_cross_graph_audit(self):
        """Cross-graph audit augmentation must be rejected."""
        # Create graph A
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        audit_result_a = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_a.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_a.evidence_id,
                )
            ],
        )
        
        # Build attributed outcome A
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            audit_result=audit_result_a,
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.SUCCESS,
        )
        
        # Create graph B
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
        )
        
        audit_result_b = DevelopmentAuditResult(
            execution_evidence_id=execution_evidence_b.evidence_id,
            verdict=DevelopmentAuditVerdict.PASS,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence_b.evidence_id,
                )
            ],
        )
        
        # Attempt cross-graph augment
        with pytest.raises(DevelopmentOutcomeAttributionError):
            builder.build(
                task_outcome=outcome_a,
                audit_result=audit_result_b,
                execution_evidence=execution_evidence_b,
            )


class TestExplicitOutcomeStatus:
    """MANDATORY TESTS 1-7 — EXPLICIT OUTCOME STATUS: New outcomes require explicit status."""

    def test_new_outcome_with_explicit_success(self):
        """TEST 1: New outcome with explicit SUCCESS."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            execution_evidence=execution_evidence,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.status == RunStatus.SUCCESS

    def test_new_outcome_with_explicit_failure(self):
        """TEST 2: New outcome with explicit FAILURE."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            execution_evidence=execution_evidence,
            outcome_status=RunStatus.FAILED,
        )
        
        assert outcome.status == RunStatus.FAILED

    def test_new_outcome_with_explicit_partial(self):
        """TEST 3: New outcome with explicit PARTIAL."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            execution_evidence=execution_evidence,
            outcome_status=RunStatus.PARTIAL,
        )
        
        assert outcome.status == RunStatus.PARTIAL

    def test_fail_audit_with_explicit_success_outcome(self):
        """TEST 4: FAIL audit + explicitly supplied SUCCESS outcome."""
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
            verdict=DevelopmentAuditVerdict.FAIL,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == audit_result.audit_id

    def test_pass_audit_with_explicit_failure_outcome(self):
        """TEST 5: PASS audit + explicitly supplied FAILURE outcome."""
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
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.FAILED,
        )
        
        assert outcome.status == RunStatus.FAILED
        assert outcome.development_audit_result_id == audit_result.audit_id

    def test_inconclusive_audit_with_explicit_success_outcome(self):
        """TEST 6: INCONCLUSIVE audit + explicitly supplied SUCCESS outcome."""
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
            verdict=DevelopmentAuditVerdict.INCONCLUSIVE,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Execution evidence",
                    ref_id=execution_evidence.evidence_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
            outcome_status=RunStatus.SUCCESS,
        )
        
        assert outcome.status == RunStatus.SUCCESS
        assert outcome.development_audit_result_id == audit_result.audit_id

    def test_new_outcome_without_status_rejected(self):
        """TEST 7: Attempt creating a NEW TaskOutcome without supplying the required outcome status."""
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        with pytest.raises(DevelopmentOutcomeAttributionError, match="outcome_status is required"):
            builder.build(
                execution_evidence=execution_evidence,
            )

    def test_augment_preserves_existing_status(self):
        """TEST 8: Augment an existing TaskOutcome - status remains unchanged."""
        existing_outcome = TaskOutcome(
            status=RunStatus.FAILED,
            summary="Existing outcome",
        )
        
        execution_evidence = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo",
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        augmented = builder.build(
            task_outcome=existing_outcome,
            execution_evidence=execution_evidence,
        )
        
        assert augmented.status == RunStatus.FAILED
        assert augmented.development_execution_evidence_id == execution_evidence.evidence_id

    def test_rejected_augmentation_preserves_status(self):
        """TEST 9: Rejected augmentation from previous adversarial cases - status remains unchanged."""
        test_result_a = DevelopmentTestResult(
            status=DevelopmentTestStatus.PASSED,
            command="pytest tests/",
            exit_code=0,
        )
        
        execution_evidence_a = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-a",
            test_result_id=test_result_a.test_result_id,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_TEST,
                    label="Test results",
                    ref_id=test_result_a.test_result_id,
                )
            ],
        )
        
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome_a = builder.build(
            execution_evidence=execution_evidence_a,
            test_result=test_result_a,
            outcome_status=RunStatus.PARTIAL,
        )
        
        original_status = outcome_a.status
        
        execution_evidence_b = DevelopmentExecutionEvidence(
            repository="https://github.com/example/repo-b",
        )
        
        with pytest.raises(DevelopmentOutcomeAttributionError):
            builder.build(
                task_outcome=outcome_a,
                execution_evidence=execution_evidence_b,
            )
        
        assert outcome_a.status == original_status
