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
    2. execution.test_result_id == test_result.test_result_id (when both provided)
    3. execution.test_result_id must not be None when test_result is supplied
    4. audit requires execution evidence
    5. test_result alone is invalid (must be accompanied by execution evidence)
    6. Augmentation preserves existing attribution unless explicitly replaced
    7. No cross-graph incoherence (e.g., audit referencing execution A but execution B provided)
    8. Mixed graph augmentation is rejected (existing graph A + execution B)
    9. Audit identity is preserved (cannot be silently swapped)
    10. TaskOutcome.status must be explicitly provided for new outcomes (not derived from audit verdict)
    """

    def build(
        self,
        *,
        task_outcome: TaskOutcome | None = None,
        audit_result: DevelopmentAuditResult | None = None,
        execution_evidence: DevelopmentExecutionEvidence | None = None,
        test_result: DevelopmentTestResult | None = None,
        outcome_status: RunStatus | None = None,
    ) -> TaskOutcome:
        """
        Build a TaskOutcome with validated development attribution.
        
        Args:
            task_outcome: Existing TaskOutcome to augment, or None to create new
            audit_result: DevelopmentAuditResult for attribution (optional)
            execution_evidence: DevelopmentExecutionEvidence for attribution (optional)
            test_result: DevelopmentTestResult for attribution (optional)
            outcome_status: RunStatus for new TaskOutcome (required when task_outcome is None)
            
        Returns:
            TaskOutcome with validated development attribution
            
        Raises:
            DevelopmentOutcomeAttributionError: If the evidence graph is incoherent or outcome_status is missing for new outcome
        """
        # Validate cross-graph coherence including existing attribution
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
            # Create new TaskOutcome - require explicit outcome_status
            if outcome_status is None:
                raise DevelopmentOutcomeAttributionError(
                    "outcome_status is required when creating a new TaskOutcome. "
                    "The builder cannot fabricate a default status. "
                    "TaskOutcome.status must be explicitly provided by the caller."
                )
            return TaskOutcome(
                status=outcome_status,
                summary="Development task completed",
                development_audit_result_id=audit_id,
                development_execution_evidence_id=execution_id,
                development_test_result_id=test_id,
            )
        else:
            # Augment existing TaskOutcome
            # Preserve existing status and attribution unless explicitly replaced
            update_dict = {}
            
            # Only update fields that are explicitly provided in this call
            if audit_result is not None:
                update_dict["development_audit_result_id"] = audit_id
            if execution_evidence is not None:
                update_dict["development_execution_evidence_id"] = execution_id
            if test_result is not None:
                update_dict["development_test_result_id"] = test_id
            
            # If no development objects provided, preserve existing attribution
            if not update_dict:
                return task_outcome.model_copy()
            
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
        # REMEDIATION: Reject when execution.test_result_id is None but test_result is supplied
        if execution_evidence is not None and test_result is not None:
            if execution_evidence.test_result_id is None:
                raise DevelopmentOutcomeAttributionError(
                    "Cannot establish test result attribution: execution_evidence.test_result_id is None. "
                    "The execution evidence does not identify a test result, so the builder cannot verify "
                    "that the supplied test_result belongs to this execution."
                )
            if execution_evidence.test_result_id != test_result.test_result_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Cross-graph incoherence: execution.test_result_id='{execution_evidence.test_result_id}' "
                    f"does not match test_result.test_result_id='{test_result.test_result_id}'. "
                    f"The execution evidence references a different test result than the one provided."
                )
        
        # Rule 4: Validate against existing attribution (augmentation integrity)
        if task_outcome is not None:
            self._validate_augmentation_coherence(
                task_outcome=task_outcome,
                audit_result=audit_result,
                execution_evidence=execution_evidence,
                test_result=test_result,
            )
        
        # Rule 5: test-only attribution is invalid
        # A test result alone cannot establish a complete development attribution chain
        if test_result is not None and execution_evidence is None and audit_result is None:
            raise DevelopmentOutcomeAttributionError(
                "Test result alone is invalid for development attribution. "
                "A test result must be accompanied by execution evidence to establish "
                "which execution it belongs to."
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
        Validate that augmentation does not corrupt existing attribution.
        
        When task_outcome already has development attribution, ensure that:
        - New objects are coherent with existing attribution
        - Omitted objects do not silently erase existing attribution
        - Audit identity is preserved (cannot be silently swapped)
        
        Raises:
            DevelopmentOutcomeAttributionError: If augmentation would corrupt attribution
        """
        existing_audit_id = task_outcome.development_audit_result_id
        existing_execution_id = task_outcome.development_execution_evidence_id
        existing_test_id = task_outcome.development_test_result_id
        
        # AUDIT IDENTITY PRESERVATION: Reject audit swap
        # Existing audit=A + new audit=B must be rejected even if B references same execution
        if existing_audit_id is not None and audit_result is not None:
            if audit_result.audit_id != existing_audit_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Augmentation would corrupt existing attribution: existing audit_id='{existing_audit_id}' "
                    f"but new audit_result.audit_id='{audit_result.audit_id}'. "
                    f"Cannot replace audit identity with a different audit object. "
                    f"The audit object is itself a distinct evidence identity that must remain stable."
                )
        
        # CASE A: Reject mixed graph augment (existing execution A + execution B)
        # This applies regardless of whether audit exists
        if existing_execution_id is not None and execution_evidence is not None:
            if execution_evidence.evidence_id != existing_execution_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Augmentation would corrupt existing attribution: existing execution_evidence_id='{existing_execution_id}' "
                    f"but new execution_evidence.evidence_id='{execution_evidence.evidence_id}'. "
                    f"Cannot replace one layer of a coherent graph with an object from another graph."
                )
        
        # CASE B: Reject partial overwrite (existing graph A + only test B)
        if existing_audit_id is not None and test_result is not None and execution_evidence is None:
            if test_result.test_result_id != existing_test_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Augmentation would corrupt existing attribution: existing test_result_id='{existing_test_id}' "
                    f"but new test_result.test_result_id='{test_result.test_result_id}'. "
                    f"Cannot partially replace attribution from a different graph."
                )
        
        # CASE C: Reject test B when execution A exists but doesn't reference it
        if existing_execution_id is not None and test_result is not None and execution_evidence is None:
            # If we're not providing execution evidence, but the existing outcome has it,
            # and we're providing a test result, we need to verify coherence
            if existing_test_id is not None and test_result.test_result_id != existing_test_id:
                raise DevelopmentOutcomeAttributionError(
                    f"Augmentation would corrupt existing attribution: existing test_result_id='{existing_test_id}' "
                    f"but new test_result.test_result_id='{test_result.test_result_id}'. "
                    f"Cannot replace test attribution with an unrelated test result."
                )
        
        # CASE D: Accept same-graph augment (existing execution A + test A)
        # This is valid if execution.test_result_id == test.test_result_id
        if existing_execution_id is not None and execution_evidence is not None and test_result is not None:
            if execution_evidence.evidence_id == existing_execution_id:
                # Same execution, verify test coherence
                if execution_evidence.test_result_id != test_result.test_result_id:
                    raise DevelopmentOutcomeAttributionError(
                        f"Augmentation incoherence: execution.test_result_id='{execution_evidence.test_result_id}' "
                        f"does not match test_result.test_result_id='{test_result.test_result_id}'."
                    )
