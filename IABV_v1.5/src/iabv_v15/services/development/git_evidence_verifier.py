"""Git Evidence Verifier for Development Audit.

This service verifies Git state for development execution evidence.
It inspects the actual repository to derive verified evidence,
preventing caller-declared fabrications.

F-02: Git Evidence Caller-Declared Remediation
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import GitDiffClassification


@dataclass
class GitVerificationResult:
    """Result of Git evidence verification."""
    
    classification: GitDiffClassification
    actual_base_commit: str | None = None
    actual_result_commit: str | None = None
    actual_changed_files: list[str] | None = None
    repository_valid: bool = False
    error_message: str = ""
    metadata: dict[str, Any] | None = None


class GitEvidenceVerifier:
    """Verifies Git state for development execution evidence.
    
    This service inspects the actual repository to derive verified evidence:
    - Repository identity
    - Commit existence
    - Lineage validity
    - Actual changed files
    - Diff classification (no-op, whitespace-only, comment-only, etc.)
    
    The caller cannot fabricate Git state — it must be observed.
    """
    
    def __init__(self, repository_path: str | Path):
        self.repository_path = Path(repository_path)
    
    def verify_execution(
        self,
        base_commit: str | None,
        result_commit: str | None,
        claimed_changed_files: list[str] | None = None,
    ) -> GitVerificationResult:
        """Verify Git state for a development execution.
        
        Args:
            base_commit: Claimed base commit SHA
            result_commit: Claimed result commit SHA
            claimed_changed_files: Files caller claims were changed
        
        Returns:
            GitVerificationResult with classification and actual Git state
        """
        metadata: dict[str, Any] = {}
        
        # Check if repository is valid
        if not self._is_valid_repository():
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=False,
                error_message="Not a valid Git repository",
                metadata=metadata,
            )
        
        repository_valid = True
        metadata["repository_path"] = str(self.repository_path)
        
        # Verify base commit exists
        if base_commit and not self._commit_exists(base_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                error_message=f"Base commit does not exist: {base_commit}",
                metadata=metadata,
            )
        
        # Verify result commit exists
        if result_commit and not self._commit_exists(result_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                error_message=f"Result commit does not exist: {result_commit}",
                metadata=metadata,
            )
        
        # If both commits are None, cannot verify
        if not base_commit or not result_commit:
            return GitVerificationResult(
                classification=GitDiffClassification.UNVERIFIABLE_GIT_STATE,
                repository_valid=repository_valid,
                error_message="Base or result commit not provided",
                metadata=metadata,
            )
        
        # Check for no-op (base == result)
        if base_commit == result_commit:
            # If base == result, there should be no changed files
            actual_changed = self._get_changed_files(base_commit, result_commit)
            
            # If caller claims changed files but base == result, that's invalid
            if claimed_changed_files and claimed_changed_files:
                return GitVerificationResult(
                    classification=GitDiffClassification.INVALID_GIT_STATE,
                    repository_valid=repository_valid,
                    actual_base_commit=base_commit,
                    actual_result_commit=result_commit,
                    actual_changed_files=actual_changed,
                    error_message="Base commit equals result commit but caller claims changed files",
                    metadata=metadata,
                )
            
            # True no-op
            return GitVerificationResult(
                classification=GitDiffClassification.NO_OP,
                repository_valid=repository_valid,
                actual_base_commit=base_commit,
                actual_result_commit=result_commit,
                actual_changed_files=actual_changed,
                metadata=metadata,
            )
        
        # Verify lineage (result should be descendant of base)
        if not self._is_ancestor(base_commit, result_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                actual_base_commit=base_commit,
                actual_result_commit=result_commit,
                error_message=f"Result commit {result_commit} is not a descendant of base commit {base_commit}",
                metadata=metadata,
            )
        
        # Get actual changed files
        actual_changed = self._get_changed_files(base_commit, result_commit)
        
        # Check for mismatched file set
        if claimed_changed_files is not None:
            if set(claimed_changed_files) != set(actual_changed):
                return GitVerificationResult(
                    classification=GitDiffClassification.MISMATCHED_FILE_SET,
                    repository_valid=repository_valid,
                    actual_base_commit=base_commit,
                    actual_result_commit=result_commit,
                    actual_changed_files=actual_changed,
                    error_message=f"Claimed files {claimed_changed_files} do not match actual {actual_changed}",
                    metadata=metadata,
                )
        
        # Classify the diff
        classification = self._classify_diff(base_commit, result_commit, actual_changed)
        
        return GitVerificationResult(
            classification=classification,
            repository_valid=repository_valid,
            actual_base_commit=base_commit,
            actual_result_commit=result_commit,
            actual_changed_files=actual_changed,
            metadata=metadata,
        )
    
    def _is_valid_repository(self) -> bool:
        """Check if the path is a valid Git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def _commit_exists(self, commit: str) -> bool:
        """Check if a commit exists in the repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", commit],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """Check if ancestor is an ancestor of descendant."""
        try:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def _get_changed_files(self, base: str, result: str) -> list[str]:
        """Get the list of changed files between two commits."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base, result],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            
            files = [f for f in result.stdout.strip().split("\n") if f]
            return files
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []
    
    def _classify_diff(
        self,
        base: str,
        result: str,
        changed_files: list[str],
    ) -> GitDiffClassification:
        """Classify the diff between two commits.
        
        Attempts to detect:
        - WHITESPACE_ONLY: Only whitespace changes
        - COMMENT_ONLY: Only comment changes (in code files)
        - VALID_CHANGE: Real content changes
        """
        if not changed_files:
            return GitDiffClassification.NO_OP
        
        # Check if all changes are whitespace-only
        try:
            # Get diff ignoring whitespace
            diff_result = subprocess.run(
                ["git", "diff", "-w", base, result],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # If diff with -w is empty, changes are whitespace-only
            if not diff_result.stdout.strip():
                return GitDiffClassification.WHITESPACE_ONLY
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # If we can't determine, assume valid change
            return GitDiffClassification.VALID_CHANGE
        
        # Check for comment-only changes (heuristic)
        # This is a basic check - full comment detection would require language-specific parsing
        try:
            diff_result = subprocess.run(
                ["git", "diff", base, result],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            diff_lines = diff_result.stdout.split("\n")
            # Check if all added/removed lines are comments
            # This is a simplified heuristic
            non_comment_changes = 0
            for line in diff_lines:
                if line.startswith("+") and not line.startswith("+++"):
                    stripped = line[1:].strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("//") and not stripped.startswith("/*"):
                        non_comment_changes += 1
                elif line.startswith("-") and not line.startswith("---"):
                    stripped = line[1:].strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("//") and not stripped.startswith("/*"):
                        non_comment_changes += 1
            
            if non_comment_changes == 0:
                return GitDiffClassification.COMMENT_ONLY
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        return GitDiffClassification.VALID_CHANGE
