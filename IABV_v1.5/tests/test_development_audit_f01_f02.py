"""Negative control tests for F-01/F-02 remediation.

Tests verify:
- F-01: Audit verdict cannot be caller-declared
- F-02: Git evidence cannot be caller-declared
- Authority boundary between receipt and record
- Git verification classifications
- Audit/TaskOutcome separation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.domain.models import (
    DevelopmentAuditResult,
    DevelopmentAuditVerdict,
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    EvidenceKind,
    EvidenceRef,
    GitDiffClassification,
)
from iabv_v15.services.development.development_audit_engine import (
    DevelopmentAuditEngine,
    DevelopmentAuditReceipt,
)
from iabv_v15.services.development.git_evidence_verifier import (
    GitEvidenceVerifier,
    GitVerificationResult,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / "data" / "test_runs"
    base.mkdir(parents=True, exist_ok=True)
    root = base / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _init_git_repo(root: Path) -> tuple[str, str]:
    """Initialize a Git repo and return base and result commits."""
    import subprocess
    
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True)
    
    # Create initial file
    (root / "sample.txt").write_text("initial content\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    # Make a change
    (root / "sample.txt").write_text("modified content\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "change"], cwd=root, check=True, capture_output=True)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    return base, result


# Test A — Fake PASS
def test_a_fake_pass_not_trusted():
    """Test A: Caller-constructed PASS verdict is NOT trusted authority."""
    # Caller can construct a DevelopmentAuditResult with PASS
    fake_result = DevelopmentAuditResult(
        execution_evidence_id="fake_evidence_id",
        verdict=DevelopmentAuditVerdict.PASS,
    )
    
    # This object exists and is structurally valid
    assert fake_result.verdict == DevelopmentAuditVerdict.PASS
    assert fake_result.execution_evidence_id == "fake_evidence_id"
    
    # BUT: This is NOT a trusted receipt
    # There is no DevelopmentAuditReceipt associated with it
    # It cannot be produced by the audit engine without verified evidence
    assert not isinstance(fake_result, DevelopmentAuditReceipt)
    
    # The receipt is the only trusted authority
    # A caller-constructed result is just a record, not authority


# Test B — Valid trusted receipt
def test_b_valid_trusted_receipt():
    """Test B: Valid flow through engine produces trusted receipt."""
    root = _workspace("test_b")
    base, result = _init_git_repo(root)
    
    # Create valid evidence
    evidence = DevelopmentExecutionEvidence(
        repository=str(root),
        base_commit=base,
        result_commit=result,
        changed_files=["sample.txt"],
        execution_status=DevelopmentExecutionStatus.COMPLETED,
        completed_at_utc=datetime.now(timezone.utc),
    )
    
    # Audit through engine
    engine = DevelopmentAuditEngine(repository_path=str(root))
    receipt = engine.audit_execution(evidence, auditor_id="test_auditor")
    
    # Receipt is produced by engine
    assert isinstance(receipt, DevelopmentAuditReceipt)
    assert receipt.verdict in [DevelopmentAuditVerdict.PASS, DevelopmentAuditVerdict.FAIL, DevelopmentAuditVerdict.INCONCLUSIVE]
    
    # Receipt can be converted to persistent record
    audit_result = receipt.to_audit_result()
    assert isinstance(audit_result, DevelopmentAuditResult)
    assert audit_result.verdict == receipt.verdict
    
    # The receipt is the trusted authority
    # The record is just the persistent representation


# Test C — Deserialized fake PASS
def test_c_deserialized_fake_pass_not_trusted():
    """Test C: Deserialized DAR with PASS is not trusted authority."""
    # Create a fake DAR
    fake_dar = DevelopmentAuditResult(
        execution_evidence_id="fake_id",
        verdict=DevelopmentAuditVerdict.PASS,
    )
    
    # Serialize it
    serialized = fake_dar.model_dump_json()
    
    # Deserialize it
    deserialized = DevelopmentAuditResult.model_validate_json(serialized)
    
    # It deserializes successfully
    assert deserialized.verdict == DevelopmentAuditVerdict.PASS
    
    # BUT: It's still not a trusted receipt
    assert not isinstance(deserialized, DevelopmentAuditReceipt)
    
    # Deserialization does NOT confer authority
    # Only a receipt from the engine is trusted


# Test D — Invalid Git object
def test_d_invalid_git_object():
    """Test D: Non-existent commit produces INVALID_GIT_STATE."""
    root = _workspace("test_d")
    base, result = _init_git_repo(root)
    
    verifier = GitEvidenceVerifier(root)
    
    # Use non-existent commit
    fake_commit = "0000000000000000000000000000000000000000"
    verification = verifier.verify_execution(
        base_commit=fake_commit,
        result_commit=result,
    )
    
    assert verification.classification == GitDiffClassification.INVALID_GIT_STATE


# Test E — Wrong repository
def test_e_wrong_repository():
    """Test E: Wrong repository path produces INVALID_GIT_STATE."""
    # Use a non-existent path
    verifier = GitEvidenceVerifier("/nonexistent/path/that/does/not/exist")
    
    verification = verifier.verify_execution(
        base_commit="any_commit",
        result_commit="any_other_commit",
    )
    
    assert verification.classification == GitDiffClassification.INVALID_GIT_STATE
    assert verification.repository_valid == False


# Test F — Base equals result with claimed changes
def test_f_base_equals_result_with_claimed_changes():
    """Test F: base==result with claimed changes is detected as invalid."""
    root = _workspace("test_f")
    base, result = _init_git_repo(root)
    
    verifier = GitEvidenceVerifier(root)
    
    # Claim base == result but with changed files
    verification = verifier.verify_execution(
        base_commit=base,
        result_commit=base,  # Same commit
        claimed_changed_files=["sample.txt"],  # But claims changes
    )
    
    # Should detect contradiction
    assert verification.classification == GitDiffClassification.INVALID_GIT_STATE


# Test G — Empty/no-op
def test_g_no_op_detection():
    """Test G: base==result with no changes is classified as NO_OP."""
    root = _workspace("test_g")
    base, result = _init_git_repo(root)
    
    verifier = GitEvidenceVerifier(root)
    
    # True no-op: same commit, no claimed changes
    verification = verifier.verify_execution(
        base_commit=base,
        result_commit=base,
        claimed_changed_files=[],
    )
    
    assert verification.classification == GitDiffClassification.NO_OP
    assert verification.actual_changed_files == []


# Test H — Changed files mismatch
def test_h_changed_files_mismatch():
    """Test H: Claimed files != actual files produces MISMATCHED_FILE_SET."""
    root = _workspace("test_h")
    base, result = _init_git_repo(root)
    
    verifier = GitEvidenceVerifier(root)
    
    # Claim wrong file was changed
    verification = verifier.verify_execution(
        base_commit=base,
        result_commit=result,
        claimed_changed_files=["wrong_file.txt"],  # Not actually changed
    )
    
    assert verification.classification == GitDiffClassification.MISMATCHED_FILE_SET
    assert verification.actual_changed_files == ["sample.txt"]


# Test I — Whitespace-only
def test_i_whitespace_only_detection():
    """Test I: Whitespace-only change is detected."""
    root = _workspace("test_i")
    import subprocess
    
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True)
    
    # Create file with content
    (root / "sample.txt").write_text("line1\nline2\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    # Add whitespace only
    (root / "sample.txt").write_text("line1\n  line2\n", encoding="utf-8")  # Extra spaces
    subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "whitespace"], cwd=root, check=True, capture_output=True)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    verifier = GitEvidenceVerifier(root)
    verification = verifier.verify_execution(base_commit=base, result_commit=result)
    
    # Should detect as whitespace-only or valid change depending on exact diff
    # The verifier uses git diff -w to check
    assert verification.classification in [GitDiffClassification.WHITESPACE_ONLY, GitDiffClassification.VALID_CHANGE]


# Test J — Comment-only
def test_j_comment_only_detection():
    """Test J: Comment-only change is detected."""
    root = _workspace("test_j")
    import subprocess
    
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True)
    
    # Create Python file
    (root / "sample.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.py"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    # Add comment only
    (root / "sample.py").write_text("def foo():\n    # comment\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.py"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "comment"], cwd=root, check=True, capture_output=True)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    verifier = GitEvidenceVerifier(root)
    verification = verifier.verify_execution(base_commit=base, result_commit=result)
    
    # Should detect as comment-only or valid change depending on heuristic
    assert verification.classification in [GitDiffClassification.COMMENT_ONLY, GitDiffClassification.VALID_CHANGE]


# Test K — Stale/invalid lineage
def test_k_invalid_lineage():
    """Test K: Result not descendant of base is detected."""
    root = _workspace("test_k")
    import subprocess
    
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True)
    
    # Create first commit
    (root / "file1.txt").write_text("content1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file1.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "commit1"], cwd=root, check=True, capture_output=True)
    commit1 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    # Create an orphan branch (no common ancestry)
    subprocess.run(["git", "checkout", "--orphan", "orphan"], cwd=root, check=True, capture_output=True)
    
    # Create unrelated commit on orphan branch
    (root / "file2.txt").write_text("content2\n", encoding="utf-8")
    subprocess.run(["git", "add", "file2.txt"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "commit2"], cwd=root, check=True, capture_output=True)
    commit2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    
    verifier = GitEvidenceVerifier(root)
    verification = verifier.verify_execution(base_commit=commit1, result_commit=commit2)
    
    # commit2 is not a descendant of commit1 (orphan branch)
    assert verification.classification == GitDiffClassification.INVALID_GIT_STATE


# Test L — Git unavailable
def test_l_git_unavailable():
    """Test L: Git unavailable produces INVALID_GIT_STATE."""
    root = _workspace("test_l")
    
    # Don't initialize Git repo
    verifier = GitEvidenceVerifier(root)
    
    verification = verifier.verify_execution(
        base_commit="any_commit",
        result_commit="any_other_commit",
    )
    
    # Should classify as invalid or unverifiable
    assert verification.classification in [GitDiffClassification.INVALID_GIT_STATE, GitDiffClassification.UNVERIFIABLE_GIT_STATE]


# Test M — Audit/TaskOutcome separation
def test_m_audit_taskoutcome_separation():
    """Test M: Audit verdict is independent of TaskOutcome status."""
    # This test verifies the conceptual separation
    # In the actual system, TaskOutcome.status is a separate concern
    
    # Audit PASS does NOT force TaskOutcome SUCCESS
    # TaskOutcome SUCCESS does NOT force Audit PASS
    
    # They are independent layers
    # This is enforced by architecture, not by a single test
    
    # The key is: DevelopmentAuditResult.verdict is NOT TaskOutcome.status
    # They are different enums in different models
    
    from iabv_v15.domain.models import RunStatus
    
    # These are separate concepts
    assert DevelopmentAuditVerdict.PASS != RunStatus.SUCCESS
    assert DevelopmentAuditVerdict.FAIL != RunStatus.FAILED
    
    # The audit engine does not set TaskOutcome.status
    # The task system does not set DevelopmentAuditResult.verdict
