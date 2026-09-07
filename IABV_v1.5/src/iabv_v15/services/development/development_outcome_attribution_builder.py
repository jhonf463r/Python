"""
DevelopmentOutcomeAttributionBuilder: Application-layer construction gate for development-attributed TaskOutcome.

This builder ensures cross-graph coherence when creating TaskOutcome objects with development attribution.
It accepts REAL typed objects (not arbitrary string IDs) and validates that the evidence graph is internally coherent.

The canonical evidence chain is:
DevelopmentTestResult -> DevelopmentExecutionEvidence -> DevelopmentAuditResult -> TaskOutcome

This builder prevents false cross-layer graphs where IDs from different evidence graphs are combined.
"""

from iabv_v15.domain.models import (
    TaskOutcome,
    RunStatus,
    DevelopmentTestResult,
    DevelopmentExecutionEvidence,
    DevelopmentAuditResult,
)


class DevelopmentOutcomeAttributionError(Exception):
    """Raised when development attribution is incoherent across the evidence graph."""
    pass


class DevelopmentOutcomeAttributionBuilder:
    """
    Application-layer construction gate for development-attributed TaskOutcome.
    
    This builder ensures that when a TaskOutcome is created with development attribution,
    the referenced evidence objects form a coherent graph.
    
    Usage:
        builder = DevelopmentOutcomeAttributionBuilder()
        outcome = builder.build(
            task_outcome=existing_outcome,
            audit_result=real_audit,
            execution_evidence=real_execution,
            test_result=real_test_result,
        )
    
    The builder validates:
    1. audit.execution_evidence_id == execution.evidence_id (when both provided)
    2. execution.test_result_id must match test_result.test_result_id (when both provided)
    3. audit requires execution evidence
    4. execution.test_result_id cannot be None when test_result is supplied
    5. test_result alone is invalid (requires execution_evidence)
    6. Augmentation preserves existing attribution unless explicitly replaced
    7. Augmentation rejects mixed graph (existing graph A + new objects from graph B)
    8. Augmentation rejects partial overwrite (existing graph A + only test B)
    """

    def build(
        self,
        *,
        task_outcome: TaskOutcome | None = None,
        outcome_status: RunStatus | None = None,
        audit_result: DevelopmentAuditResult | None = None,
        execution_evidence: DevelopmentExecutionEvidence | None = None,
        test_result: DevelopmentTestResult | None = None,
    ) -> TaskOutcome:
        """
        Build a TaskOutcome with validated development attribution.
        
        Args:
            task_outcome: Existing TaskOutcome to augment, or None to create new
            outcome_status: Required when task_outcome is None (new outcome). Must be explicit.
            audit_result: DevelopmentAuditResult for attribution (optional)
            execution_evidence: DevelopmentExecutionEvidence for attribution (optional)
            test_result: DevelopmentTestResult for attribution (optional)
            
        Returns:
            TaskOutcome with validated development attribution
            
        Raises:
            DevelopmentOutcomeAttributionError: If the evidence graph is incoherent or outcome_status missing
        """
        # Rule: outcome_status is required when creating new outcome
        if task_outcome is None and outcome_status is None:
            raise DevelopmentOutcomeAttributionError(
                "outcome_status is required when creating a new TaskOutcome. "
                "The builder cannot fabricate a default status. "
                "DevelopmentAuditVerdict ≠ TaskOutcome.status. "
                "TaskOutcome.status must represent the ACTUAL operational outcome."
            )
        
        # Validate cross-graph coherence
        self._validate_coherence(
            task_outcome=task_outcome,
            audit_result=audit_result,
            execution_evidence=execution_evidence,
            test_result=test_result,
        )
        
        # Extract IDs from real objects
        audit_id = audit_result.audit_id if audit_result else None
        execution_id = execution_evidence.evidence_id if execution_evidence else None
        test_id = test_result.test_result_id if test_result else None
        
        # Build or augment the TaskOutcome
        if task_outcome is None:
            # Create new TaskOutcome with explicit status
            return TaskOutcome(
                status=outcome_status,  # Explicit status, not fabricated
                summary="Development task completed",
                development_audit_result_id=audit_id,
                development_execution_evidence_id=execution_id,
                development_test_result_id=test_id,
            )
        else:
            # Augment existing TaskOutcome
            # Preserve existing attribution unless explicitly replaced
            update_dict = {}
            if audit_result is not None:
                update_dict["development_audit_result_id"] = audit_id
            if execution_evidence is not None:
                update_dict["development_execution_evidence_id"] = execution_id
            if test_result is not None:
                update_dict["development_test_result_id"] = test_id
            
            # Create a copy with attribution added (status preserved)
            return task_outcome.model_copy(update=update_dict)

    def _validate_coherence(
        self,
        *,
        task_outcome: TaskOutcome | None,
        audit_result: DevelopmentAuditResult | None,
        execution_evidence: DevelopmentExecutionEvidence | None,
        test_result: DevelopmentTestResult | None,
    ) -> None:
        """
        Validate that the evidence graph is internally coherent.
        
        Raises:
            DevelopmentOutcomeAttributionError: If incoherence is detected
        """
        # Rule 1: audit requires execution evidence
        if audit_result is not None and execution_evidence is None:
            raise DevelopmentOutcomeAttributionError(
                "DevelopmentAuditResult requires DevelopmentExecutionEvidence "
                "(audit cannot exist without execution evidence to audit)"
            )
        
        # Rule 2: audit.execution_evidence_id must match execution.evidence_id
        if audit_result is not None and execution_evidence is not None:
            if audit_result.execution_evidence_id != execution_evidence.evidence_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Cross-graph incoherence: audit.execution_evidence_id='{audit_result.execution_evidence_id}' "
                   f"does not match execution.evidence_id='{execution_evidence.evidence_id}'. "
                    f"The audit references a different execution evidence than the one provided."
                )
        
        # Rule 3: execution.test_result_id must match test_result.test_result_id
        if execution_evidence is not None and test_result is not None:
            if execution_evidence.test_result_id is not None:
                if execution_evidence.test_result_id != test_result.test_result_id:
                    raise DevelopmentOutcomeAttributionError(
                        f"Cross-graph incoherence: execution.test_result_id='{execution_evidence.test_result_id}' "
                        f"does not match test_result.test_result_id='{test_result.test_result_id}'. "
                        f"The execution evidence references a different test result than the one provided."
                    )
            else:
                # Rule 3 remediation: Reject when execution.test_result_id is None but test_result is supplied
                raise DevelopmentOutcomeAttributionError(
                    "execution_evidence.test_result_id is None. The execution evidence does not identify a test result, "
                    "so the builder cannot verify that the supplied test_result belongs to this execution."
                )
        
        # Rule 4: If execution has test_result_id but test_result is None, that's allowed
        # (partial attribution is valid)
        
        # Rule 5: test_result alone is invalid (requires execution_evidence)
        if test_result is not None and execution_evidence is None:
            raise DevelopmentOutcomeAttributionError(
                "Test result alone is invalid for development attribution. "
                "A test result alone cannot establish which execution evidence and audit it belongs to. "
                "Provide execution_evidence (and optionally audit_result) to establish the evidence graph."
            )
        
        # Validate augmentation coherence if augmenting existing outcome
        if task_outcome is not None:
            self._validate_augmentation_coherence(
                task_outcome=task_outcome,
                audit_result=audit_result,
                execution_evidence=execution_evidence,
                test_result=test_result,
            )

    def _validate_augmentation_coherence(
        self,
        *,
        task_outcome: TaskOutcome,
        audit_result: DevelopmentAuditResult | None,
        execution_evidence: DevelopmentExecutionEvidence | None,
        test_result: DevelopmentTestResult | None,
    ) -> None:
        """
        Validate that augmentation preserves existing attribution coherence.
        
        Raises:
            DevelopmentOutcomeAttributionError: If augmentation would corrupt existing attribution
        """
        # Rule 6: Reject mixed graph augmentation
        # If outcome has execution A, cannot augment with execution B
        if task_outcome.development_execution_evidence_id is not None:
            if execution_evidence is not None:
                if task_outcome.development_execution_evidence_id != execution_evidence.evidence_id:
                    raise DevelopmentOutcomeAttributionError(
                        f"Augmentation would corrupt existing attribution: "
                        f"existing execution_evidence_id='{task_outcome.development_execution_evidence_id}' "
                        f"does not match new execution.evidence_id='{execution_evidence.evidence_id}'. "
                        f"Cannot mix different evidence graphs in the same TaskOutcome."
                    )
        
        # Rule 7: Reject partial overwrite
        # If outcome has full graph A, cannot augment with only test B
        if task_outcome.development_execution_evidence_id is not None:
            if execution_evidence is None and test_result is not None:
                raise DevelopmentOutcomeAttributionError(
                    "Augmentation would corrupt existing attribution: "
                    "existing outcome has execution_evidence_id but augmentation provides only test_result. "
                    "This would create a mixed graph where the test result is not verified against the existing execution evidence."
                )
        
        # Rule 8: Accept same-graph augmentation
        # If outcome has execution A, can augment with test A if execution.test_result_id matches test A
        if task_outcome.development_execution_evidence_id is not None:
            if execution_evidence is not None and test_result is not None:
                if execution_evidence.evidence_id == task_outcome.development_execution_evidence_id:
                    # Same execution, verify test coherence
                    if execution_evidence.test_result_id is not None:
                        if execution_evidence.test_result_id != test_result.test_result_id:
                            raise DevelopmentOutcomeAttributionError(
                                f"Augmentation would corrupt existing attribution: "
                                f"execution.test_result_id='{execution_evidence.test_result_id}' "
                                f"does not match test_result.test_result_id='{test_result.test_result_id}'."
                            )
        
        # Rule 9: Audit identity preservation
        # If outcome has audit A, cannot replace with audit B even if new audit references same execution
        # The audit object is itself a distinct evidence identity that must remain stable
        if task_outcome.development_audit_result_id is not None:
            if audit_result is not None:
                if audit_result.audit_id != task_outcome.development_audit_result_id:
                    raise DevelopmentOutcomeAttributionError(
                        f"Cannot replace audit identity with a different audit object. "
                        f"existing audit_id='{task_outcome.development_audit_result_id}' "
                        f"does not match new audit.audit_id='{audit_result.audit_id}'. "
                        f"The audit object is itself a distinct evidence identity that must remain stable."
                    )
