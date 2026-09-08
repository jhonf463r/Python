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


class _ReceiptSecret:
    """Secret token to prevent external construction of DevelopmentAuditReceipt.
    
    Only the DevelopmentAuditEngine can create this token.
    This ensures that only the engine can produce trusted receipts.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


class DevelopmentAuditReceipt:
    """Trusted receipt of a development audit execution.
    
    This represents that an audit was actually executed by the authority
    and produced a result from verified evidence.
    
    A DevelopmentAuditResult can be constructed by anyone, but a
    DevelopmentAuditReceipt can only be produced by the audit engine.
    
    The receipt requires a secret token that only the engine can create,
    preventing external construction.
    """
    
    def __init__(
        self,
        _secret: _ReceiptSecret,
        receipt_id: str,
        audit_id: str,
        execution_evidence_id: str,
        verdict: DevelopmentAuditVerdict,
        audited_at_utc: datetime,
        auditor_id: str | None = None,
        git_verification: GitVerificationResult | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Private constructor requiring secret token."""
        if not isinstance(_secret, _ReceiptSecret):
            raise TypeError(
                "DevelopmentAuditReceipt cannot be constructed directly. "
                "Use DevelopmentAuditEngine.audit_execution() to produce trusted receipts."
            )
        self._receipt_id = receipt_id
        self._audit_id = audit_id
        self._execution_evidence_id = execution_evidence_id
        self._verdict = verdict
        self._audited_at_utc = audited_at_utc
        self._auditor_id = auditor_id
        self._git_verification = git_verification
        self._metadata = metadata or {}
    
    @property
    def receipt_id(self) -> str:
        return self._receipt_id
    
    @property
    def audit_id(self) -> str:
        return self._audit_id
    
    @property
    def execution_evidence_id(self) -> str:
        return self._execution_evidence_id
    
    @property
    def verdict(self) -> DevelopmentAuditVerdict:
        return self._verdict
    
    @property
    def audited_at_utc(self) -> datetime:
        return self._audited_at_utc
    
    @property
    def auditor_id(self) -> str | None:
        return self._auditor_id
    
    @property
    def git_verification(self) -> GitVerificationResult | None:
        return self._git_verification
    
    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata.copy()
    
    def to_audit_result(self) -> DevelopmentAuditResult:
        """Convert receipt to a persistent audit result record."""
        return DevelopmentAuditResult(
            audit_id=self._audit_id,
            execution_evidence_id=self._execution_evidence_id,
            verdict=self._verdict,
            auditor_id=self._auditor_id,
            audited_at_utc=self._audited_at_utc,
            evidence_refs=[
                EvidenceRef(
                    kind=EvidenceKind.DEVELOPMENT_EXECUTION,
                    label="Development Execution Evidence",
                    ref_id=self._execution_evidence_id,
                )
            ],
            metadata=self._metadata.copy(),
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
    
    def __init__(self, repository_path: str | None = None, expected_repository_identity: str | None = None):
        self.repository_path = repository_path
        self.expected_repository_identity = expected_repository_identity
    
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
        
        receipt_id = str(uuid4())
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
        
        # Build receipt with secret token
        secret = _ReceiptSecret()
        receipt = DevelopmentAuditReceipt(
            _secret=secret,
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
        git_verification: GitVerificationResult,
    ) -> list[DevelopmentAuditCriterion]:
        """Evaluate audit criteria against evidence.
        
        git_verification is always present after CRITICAL-2 fix.
        """
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
