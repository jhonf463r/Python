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
        )
        
        # Verify attribution is correct
        assert outcome.development_audit_result_id == audit_result_a.audit_id
        assert outcome.development_execution_evidence_id == execution_evidence_a.evidence_id
        assert outcome.development_test_result_id == test_result_a.test_result_id


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
        outcome = builder.build()
        
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
