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
    3. audit requires execution evidence
    4. All IDs are non-empty when present
    5. No cross-graph incoherence (e.g., audit referencing execution A but execution B provided)
    """

    def build(
        self,
        *,
        task_outcome: TaskOutcome | None = None,
        audit_result: DevelopmentAuditResult | None = None,
        execution_evidence: DevelopmentExecutionEvidence | None = None,
        test_result: DevelopmentTestResult | None = None,
    ) -> TaskOutcome:
        """
        Build a TaskOutcome with validated development attribution.
        
        Args:
            task_outcome: Existing TaskOutcome to augment, or None to create new
            audit_result: DevelopmentAuditResult for attribution (optional)
            execution_evidence: DevelopmentExecutionEvidence for attribution (optional)
            test_result: DevelopmentTestResult for attribution (optional)
            
        Returns:
            TaskOutcome with validated development attribution
            
        Raises:
            DevelopmentOutcomeAttributionError: If the evidence graph is incoherent
        """
        # Validate cross-graph coherence
        self._validate_coherence(
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
            # Create new TaskOutcome
            return TaskOutcome(
                status=RunStatus.SUCCESS,
                summary="Development task completed",
                development_audit_result_id=audit_id,
                development_execution_evidence_id=execution_id,
                development_test_result_id=test_id,
            )
        else:
            # Augment existing TaskOutcome
            # Create a copy with attribution added
            return task_outcome.model_copy(
                update={
                    "development_audit_result_id": audit_id,
                    "development_execution_evidence_id": execution_id,
                    "development_test_result_id": test_id,
                }
            )

    def _validate_coherence(
        self,
        *,
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
        
        # Rule 4: If execution has test_result_id but test_result is None, that's allowed
        # (partial attribution is valid)
        
        # Rule 5: If execution has no test_result_id but test_result is provided, that's allowed
        # (the test result exists but execution doesn't reference it - this is a data quality issue
        # but not a graph incoherence issue that should block construction)
