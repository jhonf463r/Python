"""Development Audit Engine for F-01 Remediation.

This engine provides the trusted authority for audit verdicts.
It derives verdicts from verified evidence, preventing caller-declared results.

F-01: Audit Verdict Caller-Declared Remediation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

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


@dataclass
class DevelopmentAuditReceipt:
    """Trusted receipt of a development audit execution.
    
    This represents that an audit was actually executed by the authority
    and produced a result from verified evidence.
    
    A DevelopmentAuditResult can be constructed by anyone, but a
    DevelopmentAuditReceipt can only be produced by the audit engine.
    """
    
    receipt_id: str
    audit_id: str
    execution_evidence_id: str
    verdict: DevelopmentAuditVerdict
    audited_at_utc: datetime
    auditor_id: str | None = None
    git_verification: GitVerificationResult | None = None
    metadata: dict[str, Any] | None = None
    
    def to_audit_result(self) -> DevelopmentAuditResult:
        """Convert receipt to a persistent audit result record."""
        return DevelopmentAuditResult(
            audit_id=self.audit_id,
            execution_evidence_id=self.execution_evidence_id,
            verdict=self.verdict,
            auditor_id=self.auditor_id,
            audited_at_utc=self.audited_at_utc,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Development Execution Evidence",
                    ref_id=self.execution_evidence_id,
                )
            ],
            metadata=self.metadata or {},
        )


class DevelopmentAuditEngine:
    """Trusted authority for development audit verdicts.
    
    This engine derives audit verdicts from verified evidence.
    It does not accept caller-declared verdicts as authority.
    
    The flow is:
    1. Receive execution evidence
    2. Verify Git state (via GitEvidenceVerifier)
    3. Evaluate audit criteria
    4. Derive verdict
    5. Produce trusted receipt
    """
    
    def __init__(self, repository_path: str | None = None):
        self.repository_path = repository_path
    
    def audit_execution(
        self,
        evidence: DevelopmentExecutionEvidence,
        auditor_id: str | None = None,
    ) -> DevelopmentAuditReceipt:
        """Audit development execution evidence.
        
        This is the ONLY way to produce a trusted audit receipt.
        Caller-constructed DevelopmentAuditResult objects are NOT
        considered authoritative.
        
        Args:
            evidence: Development execution evidence to audit
            auditor_id: Optional auditor identifier
        
        Returns:
            DevelopmentAuditReceipt representing the trusted audit result
        """
        from uuid import uuid4
        
        receipt_id = str(uuid4())
        audit_id = str(uuid4())
        audited_at = datetime.now(timezone.utc)
        
        # Verify Git evidence
        git_verification = None
        if self.repository_path and evidence.base_commit and evidence.result_commit:
            verifier = GitEvidenceVerifier(self.repository_path)
            git_verification = verifier.verify_execution(
                base_commit=evidence.base_commit,
                result_commit=evidence.result_commit,
                claimed_changed_files=evidence.changed_files if evidence.changed_files else None,
            )
        
        # Evaluate criteria and derive verdict
        criteria = self._evaluate_criteria(evidence, git_verification)
        findings = self._generate_findings(evidence, git_verification, criteria)
        verdict = self._derive_verdict(criteria, git_verification)
        
        # Build receipt
        receipt = DevelopmentAuditReceipt(
            receipt_id=receipt_id,
            audit_id=audit_id,
            execution_evidence_id=evidence.evidence_id,
            verdict=verdict,
            audited_at_utc=audited_at,
            auditor_id=auditor_id,
            git_verification=git_verification,
            metadata={
                "repository": evidence.repository,
                "base_commit": evidence.base_commit,
                "result_commit": evidence.result_commit,
                "execution_status": evidence.execution_status.value,
            },
        )
        
        return receipt
    
    def _evaluate_criteria(
        self,
        evidence: DevelopmentExecutionEvidence,
        git_verification: GitVerificationResult | None,
    ) -> list[DevelopmentAuditCriterion]:
        """Evaluate audit criteria against evidence."""
        criteria = []
        
        # Criterion 1: Execution completed
        completed_criterion = DevelopmentAuditCriterion(
            criterion_id="execution_completed",
            name="Execution Completed",
            description="Development execution reached a terminal state",
            required=True,
            status="satisfied" if evidence.execution_status.value in ["completed", "failed", "cancelled"] else "not_satisfied",
        )
        criteria.append(completed_criterion)
        
        # Criterion 2: Git state verifiable
        if git_verification:
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
        if git_verification and git_verification.classification == GitDiffClassification.NO_OP:
            no_op_criterion = DevelopmentAuditCriterion(
                criterion_id="valid_change",
                name="Valid Change",
                description="Base and result commits differ with actual changes",
                required=True,
                status="not_satisfied",
            )
            criteria.append(no_op_criterion)
        
        # Criterion 4: Changed files match (if verification available)
        if git_verification and git_verification.classification == GitDiffClassification.MISMATCHED_FILE_SET:
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
        git_verification: GitVerificationResult | None,
        criteria: list[DevelopmentAuditCriterion],
    ) -> list[DevelopmentAuditFinding]:
        """Generate audit findings from evaluation."""
        findings = []
        
        # Git-related findings
        if git_verification:
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
        git_verification: GitVerificationResult | None,
    ) -> DevelopmentAuditVerdict:
        """Derive audit verdict from criteria and Git verification."""
        
        # If Git state is invalid or unverifiable, verdict is INCONCLUSIVE
        if git_verification and git_verification.classification in [
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
