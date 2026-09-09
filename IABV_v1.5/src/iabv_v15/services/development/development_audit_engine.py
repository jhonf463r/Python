"""Development Audit Engine for F-01 Remediation.

This engine provides the trusted authority for audit verdicts.
It derives verdicts from verified evidence, preventing caller-declared results.

F-01: Audit Verdict Caller-Declared Remediation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from iabv_v15.domain.models import (
    DevelopmentAuditCriterion,
    DevelopmentAuditFinding,
    DevelopmentAuditResult,
    DevelopmentAuditVerdict,
    DevelopmentExecutionEvidence,
    DevelopmentTestStatus,
    EvidenceKind,
    EvidenceRef,
    GitDiffClassification,
)
from iabv_v15.services.development.git_evidence_verifier import (
    GitEvidenceVerifier,
    GitVerificationResult,
)


# P0-B V2 FIX: Removed DevelopmentAuditReceipt class
# Authority is now based on verifiable evidence chain, not a forgeable Python object.
# Only DevelopmentAuditEngine.audit_execution() can produce results with verified Git evidence.
# Consumers verify authority by re-validating against Git evidence, not by object type.


class DevelopmentAuditEngine:
    """Trusted authority for development audit verdicts.
    
    This engine derives audit verdicts from verified evidence.
    It does not accept caller-declared verdicts as authority.
    
    P0-B V2: Authority is based on verifiable evidence chain, not a forgeable object.
    Only this engine can produce results with verified Git evidence.
    Consumers verify authority by re-validating against Git evidence.
    
    The flow is:
    1. Receive execution evidence
    2. Verify Git state (via GitEvidenceVerifier)
    3. Evaluate audit criteria
    4. Derive verdict
    5. Return DevelopmentAuditResult with verified evidence metadata
    """
    
    def __init__(self, repository_path: str | None = None, expected_repository_identity: str | None = None):
        self.repository_path = repository_path
        self.expected_repository_identity = expected_repository_identity
    
    def audit_execution(
        self,
        evidence: DevelopmentExecutionEvidence,
        auditor_id: str | None = None,
    ) -> DevelopmentAuditResult:
        """Audit development execution evidence.
        
        This is the ONLY way to produce an audit result with verified Git evidence.
        Caller-constructed DevelopmentAuditResult objects are NOT considered authoritative
        unless they can be re-verified against Git evidence.
        
        Args:
            evidence: Development execution evidence to audit
            auditor_id: Optional auditor identifier
        
        Returns:
            DevelopmentAuditResult with verified Git evidence metadata
        
        Raises:
            ValueError: If repository_path is not provided
            ValueError: If Git evidence is missing or unverifiable
        """
        # CRITICAL-2: Require repository_path for any audit
        if not self.repository_path:
            raise ValueError(
                "repository_path is required for audit execution. "
                "Cannot produce trusted verdict without Git verification."
            )
        
        audit_id = str(uuid4())
        audited_at = datetime.now(timezone.utc)
        
        # CRITICAL-2: Require Git evidence for verification
        if not evidence.base_commit or not evidence.result_commit:
            raise ValueError(
                "base_commit and result_commit are required for audit execution. "
                "Cannot produce trusted verdict without Git evidence."
            )
        
        # Verify Git evidence
        verifier = GitEvidenceVerifier(self.repository_path, self.expected_repository_identity)
        git_verification = verifier.verify_execution(
            base_commit=evidence.base_commit,
            result_commit=evidence.result_commit,
            claimed_changed_files=evidence.changed_files if evidence.changed_files else None,
        )
        
        # CRITICAL-3: Verify repository identity
        # GitEvidenceVerifier now checks repository identity
        
        # Evaluate criteria and derive verdict
        criteria = self._evaluate_criteria(evidence, git_verification)
        findings = self._generate_findings(evidence, git_verification, criteria)
        verdict = self._derive_verdict(criteria, git_verification)
        
        # P0-B V2 FIX: Return DevelopmentAuditResult with verified evidence metadata
        # Authority is in the verifiable evidence chain, not in object type
        result = DevelopmentAuditResult(
            audit_id=audit_id,
            execution_evidence_id=evidence.evidence_id,
            verdict=verdict,
            auditor_id=auditor_id,
            audited_at_utc=audited_at,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Development Execution Evidence",
                    ref_id=evidence.evidence_id,
                )
            ],
            criteria=criteria,
            findings=findings,
            metadata={
                "repository": evidence.repository,
                "base_commit": evidence.base_commit,
                "result_commit": evidence.result_commit,
                "execution_status": evidence.execution_status.value,
                "git_verification": {
                    "classification": git_verification.classification.value,
                    "actual_base_commit": git_verification.actual_base_commit,
                    "actual_result_commit": git_verification.actual_result_commit,
                    "repository_valid": git_verification.repository_valid,
                    "repository_identity": git_verification.repository_identity,
                },
            },
        )
        
        return result
    
    def verify_result(
        self,
        result: DevelopmentAuditResult,
        repository_path: str | None = None,
        expected_repository_identity: str | None = None,
    ) -> bool:
        """Re-verify an audit result against Git evidence.
        
        This method allows consumers to verify that a DevelopmentAuditResult
        was produced from legitimate Git evidence. This is the authority check:
        a result is authoritative only if its Git evidence can be re-verified.
        
        Args:
            result: DevelopmentAuditResult to verify
            repository_path: Path to Git repository (uses engine path if None)
            expected_repository_identity: Expected repository identity
        
        Returns:
            True if result can be re-verified against Git evidence, False otherwise
        """
        repo_path = repository_path or self.repository_path
        if not repo_path:
            return False
        
        # Extract Git evidence from result metadata
        metadata = result.metadata or {}
        base_commit = metadata.get("base_commit")
        result_commit = metadata.get("result_commit")
        git_meta = metadata.get("git_verification", {})
        
        if not base_commit or not result_commit:
            return False
        
        # Re-verify Git evidence
        verifier = GitEvidenceVerifier(repo_path, expected_repository_identity or self.expected_repository_identity)
        try:
            git_verification = verifier.verify_execution(
                base_commit=base_commit,
                result_commit=result_commit,
                claimed_changed_files=None,  # Re-verify without claimed files
            )
            
            # Check if Git state is valid
            if git_verification.classification in [
                GitDiffClassification.INVALID_GIT_STATE,
                GitDiffClassification.UNVERIFIABLE_GIT_STATE,
            ]:
                return False
            
            # Check if classification matches
            expected_classification = git_meta.get("classification")
            if expected_classification and git_verification.classification.value != expected_classification:
                return False
            
            # Check if repository is valid
            if git_meta.get("repository_valid") and not git_verification.repository_valid:
                return False
            
            # Check if repository identity matches
            expected_identity = git_meta.get("repository_identity")
            if expected_identity and git_verification.repository_identity != expected_identity:
                return False
            
            return True
        except Exception:
            return False
    
    def _evaluate_criteria(
        self,
        evidence: DevelopmentExecutionEvidence,
        git_verification: GitVerificationResult,
    ) -> list[DevelopmentAuditCriterion]:
        """Evaluate audit criteria against evidence.
        
        git_verification is always present after CRITICAL-2 fix.
        """
        criteria = []
        
        # Criterion 1: Execution completed
        # P0-A FIX: Only COMPLETED satisfies execution completion criterion
        # FAILED and CANCELLED are terminal states but do NOT satisfy completion
        completed_criterion = DevelopmentAuditCriterion(
            criterion_id="execution_completed",
            name="Execution Completed",
            description="Development execution completed successfully (not failed or cancelled)",
            required=True,
            status="satisfied" if evidence.execution_status.value == "completed" else "not_satisfied",
        )
        criteria.append(completed_criterion)
        
        # Criterion 2: Git state verifiable (always present after CRITICAL-2)
        git_verifiable = DevelopmentAuditCriterion(
            criterion_id="git_state_verifiable",
            name="Git State Verifiable",
            description="Git state could be verified",
            required=True,
            status="satisfied" if git_verification.classification not in [
                GitDiffClassification.INVALID_GIT_STATE,
                GitDiffClassification.UNVERIFIABLE_GIT_STATE,
            ] else "not_satisfied",
        )
        criteria.append(git_verifiable)
        
        # Criterion 3: Valid change (if commits differ)
        if git_verification.classification == GitDiffClassification.NO_OP:
            no_op_criterion = DevelopmentAuditCriterion(
                criterion_id="valid_change",
                name="Valid Change",
                description="Base and result commits differ with actual changes",
                required=True,
                status="not_satisfied",
            )
            criteria.append(no_op_criterion)
        
        # Criterion 4: Changed files match (if verification available)
        if git_verification.classification == GitDiffClassification.MISMATCHED_FILE_SET:
            files_match_criterion = DevelopmentAuditCriterion(
                criterion_id="changed_files_match",
                name="Changed Files Match",
                description="Claimed changed files match actual Git diff",
                required=True,
                status="not_satisfied",
            )
            criteria.append(files_match_criterion)
        
        return criteria
    
    def _generate_findings(
        self,
        evidence: DevelopmentExecutionEvidence,
        git_verification: GitVerificationResult,
        criteria: list[DevelopmentAuditCriterion],
    ) -> list[DevelopmentAuditFinding]:
        """Generate audit findings from evaluation.
        
        git_verification is always present after CRITICAL-2 fix.
        """
        findings = []
        
        # Git-related findings
        if git_verification.classification == GitDiffClassification.INVALID_GIT_STATE:
            findings.append(
                DevelopmentAuditFinding(
                    summary=git_verification.error_message or "Invalid Git state",
                    criterion="git_state_verifiable",
                    severity="high",
                )
            )
        elif git_verification.classification == GitDiffClassification.NO_OP:
            findings.append(
                DevelopmentAuditFinding(
                    summary="Base and result commits are identical (no-op)",
                    criterion="valid_change",
                    severity="medium",
                )
            )
        elif git_verification.classification == GitDiffClassification.MISMATCHED_FILE_SET:
            findings.append(
                DevelopmentAuditFinding(
                    summary=f"Claimed files do not match actual: {git_verification.error_message}",
                    criterion="changed_files_match",
                    severity="high",
                )
            )
        elif git_verification.classification == GitDiffClassification.WHITESPACE_ONLY:
            findings.append(
                DevelopmentAuditFinding(
                    summary="Changes are whitespace-only",
                    criterion="valid_change",
                    severity="low",
                )
            )
        elif git_verification.classification == GitDiffClassification.COMMENT_ONLY:
            findings.append(
                DevelopmentAuditFinding(
                    summary="Changes are comment-only",
                    criterion="valid_change",
                    severity="low",
                )
            )
        
        # Criterion violation findings
        for criterion in criteria:
            if criterion.status == "not_satisfied" and criterion.required:
                findings.append(
                    DevelopmentAuditFinding(
                        summary=f"Required criterion not satisfied: {criterion.name}",
                        criterion=criterion.criterion_id,
                        severity="high",
                    )
                )
        
        return findings
    
    def _derive_verdict(
        self,
        criteria: list[DevelopmentAuditCriterion],
        git_verification: GitVerificationResult,
    ) -> DevelopmentAuditVerdict:
        """Derive audit verdict from criteria and Git verification.
        
        git_verification is always present after CRITICAL-2 fix.
        """
        # If Git state is invalid or unverifiable, verdict is INCONCLUSIVE
        if git_verification.classification in [
            GitDiffClassification.INVALID_GIT_STATE,
            GitDiffClassification.UNVERIFIABLE_GIT_STATE,
        ]:
            return DevelopmentAuditVerdict.INCONCLUSIVE
        
        # Check if any required criterion is not satisfied
        required_criteria = [c for c in criteria if c.required]
        if any(c.status == "not_satisfied" for c in required_criteria):
            return DevelopmentAuditVerdict.FAIL
        
        # All required criteria satisfied
        return DevelopmentAuditVerdict.PASS
