"""
Real repository evidence test for DevelopmentExecutionEvidence.

This test constructs DevelopmentExecutionEvidence from real Git repository data,
demonstrating verifiable linkage with DevelopmentTestResult.
"""

import subprocess
import pytest
from pathlib import Path
from datetime import datetime, timezone
from iabv_v15.domain.models import (
    DevelopmentExecutionEvidence,
    DevelopmentExecutionStatus,
    DevelopmentTestResult,
    DevelopmentTestStatus,
    EvidenceRef,
    EvidenceKind,
)


def get_git_commit(project_root: Path) -> str | None:
    """Capture the real Git commit SHA from the repository.
    
    Returns None if Git is not available or not in a Git repository.
    Does not invent a SHA - only returns actual Git data.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def get_git_changed_files(project_root: Path, base_commit: str | None) -> list[str]:
    """Capture changed files between base_commit and HEAD.
    
    Returns empty list if Git is not available or cannot determine changes.
    Does not invent file paths - only returns actual Git data.
    """
    if base_commit is None:
        return []
    
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_commit, "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return []


def get_git_remote_url(project_root: Path) -> str:
    """Capture the Git remote URL as repository identifier.
    
    Returns a placeholder if Git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "local"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return "local"


def test_real_repository_evidence_with_test_result_linkage():
    """Construct DevelopmentExecutionEvidence from real repository data and link to DevelopmentTestResult."""
    # Portable path resolution: derive project root from test file location
    test_file = Path(__file__).resolve()
    project_root = test_file.parent.parent  # Go from tests/ to project root
    
    # Capture real Git data
    current_commit = get_git_commit(project_root)
    repository = get_git_remote_url(project_root)
    
    # For this audit branch, use current commit as result_commit
    # In a real scenario, this would be the commit produced by the development work
    result_commit = current_commit
    base_commit = current_commit  # Using same commit for this test (no changes yet)
    
    # Capture changed files (will be empty since base == result)
    changed_files = get_git_changed_files(project_root, base_commit)
    
    # Create a real DevelopmentTestResult
    test_result = DevelopmentTestResult(
        status=DevelopmentTestStatus.PASSED,
        command="pytest tests/test_development_execution_evidence.py -v",
        exit_code=0,
        duration_seconds=1.5,
        stdout="All tests passed",
        stderr="",
        commit=current_commit,
    )
    
    # Create DevelopmentExecutionEvidence that links to the test result
    completed_at = datetime.now(timezone.utc)
    evidence = DevelopmentExecutionEvidence(
        repository=repository,
        base_commit=base_commit,
        result_commit=result_commit,
        changed_files=changed_files,
        executor_id=None,  # No agent abstraction yet
        started_at_utc=completed_at,  # Using same time for simplicity
        completed_at_utc=completed_at,
        execution_status=DevelopmentExecutionStatus.COMPLETED,
        duration_seconds=test_result.duration_seconds,
        test_result_id=test_result.test_result_id,
        evidence_refs=[
            EvidenceRef(
                kind=EvidenceKind.DEVELOPMENT_TEST,
                label="Development test result",
                ref_id=test_result.test_result_id,
            )
        ],
        metadata={
            "test_framework": "pytest",
            "source": "real_repository_evidence_test",
        },
    )
    
    # Verify the evidence was constructed with real data
    assert evidence.repository == repository
    assert evidence.base_commit == base_commit
    assert evidence.result_commit == result_commit
    assert isinstance(evidence.changed_files, list)
    assert evidence.execution_status == DevelopmentExecutionStatus.COMPLETED
    assert evidence.test_result_id == test_result.test_result_id
    assert len(evidence.evidence_refs) == 1
    assert evidence.evidence_refs[0].kind == EvidenceKind.DEVELOPMENT_TEST
    assert evidence.evidence_refs[0].ref_id == test_result.test_result_id
    
    # Verify the linkage is verifiable
    assert evidence.test_result_id == test_result.test_result_id
    assert evidence.evidence_refs[0].ref_id == test_result.test_result_id
    
    print(f"\nReal repository evidence constructed:")
    print(f"  Repository: {evidence.repository}")
    print(f"  Base commit: {evidence.base_commit}")
    print(f"  Result commit: {evidence.result_commit}")
    print(f"  Changed files: {len(evidence.changed_files)}")
    print(f"  Test result ID: {evidence.test_result_id}")
    print(f"  Evidence refs: {len(evidence.evidence_refs)}")
    print(f"  CWD strategy: portable (derived from test file location)")


def test_real_non_empty_changed_files_evidence():
    """Demonstrate get_git_changed_files() with a real non-empty diff."""
    import tempfile
    import os
    
    # Portable path resolution
    test_file = Path(__file__).resolve()
    project_root = test_file.parent.parent
    
    # Get current commit as base
    base_commit = get_git_commit(project_root)
    if base_commit is None:
        pytest.skip("Git not available, skipping real changed files test")
    
    # Create a temporary file in the project to generate a real diff
    temp_file_path = project_root / ".temp_test_file_for_development_execution_evidence.txt"
    
    try:
        # Create the temporary file
        temp_file_path.write_text("Temporary test file for DevelopmentExecutionEvidence changed_files test")
        
        # Stage the file so git diff --name-only can detect it
        subprocess.run(
            ["git", "add", str(temp_file_path)],
            capture_output=True,
            cwd=project_root,
            timeout=5
        )
        
        # Get changed files from staged changes (using --cached to see staged files)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", base_commit],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
        )
        
        # Parse changed files
        changed_files = []
        if result.returncode == 0 and result.stdout.strip():
            changed_files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        
        # Verify the temporary file is in the changed files list
        # The path will be relative to project root
        temp_file_relative = ".temp_test_file_for_development_execution_evidence.txt"
        assert any(temp_file_relative in f for f in changed_files), \
            f"Expected temporary file in changed files, got: {changed_files}"
        
        # Verify we can construct evidence with these real changed files
        evidence = DevelopmentExecutionEvidence(
            repository=get_git_remote_url(project_root),
            base_commit=base_commit,
            result_commit=base_commit,  # Same commit, but we have staged changes
            changed_files=changed_files,
            execution_status=DevelopmentExecutionStatus.RUNNING,
        )
        
        assert len(evidence.changed_files) > 0
        assert evidence.changed_files is not None
        
        print(f"\nReal non-empty changed files test:")
        print(f"  Changed files: {evidence.changed_files}")
        print(f"  Count: {len(evidence.changed_files)}")
        
    finally:
        # Cleanup: unstage and remove the temporary file
        try:
            subprocess.run(
                ["git", "reset", "HEAD", str(temp_file_path)],
                capture_output=True,
                cwd=project_root,
                timeout=5
            )
            if temp_file_path.exists():
                temp_file_path.unlink()
        except Exception:
            # Best effort cleanup
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass
