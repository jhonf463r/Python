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
class ChangedFilesResult:
    """Result of getting changed files between commits."""
    success: bool
    files: list[str]
    error: str = ""


@dataclass
class GitVerificationResult:
    """Result of Git evidence verification."""
    
    classification: GitDiffClassification
    actual_base_commit: str | None = None
    actual_result_commit: str | None = None
    actual_changed_files: list[str] | None = None
    repository_valid: bool = False
    repository_identity: str | None = None
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
    
    def __init__(self, repository_path: str | Path, expected_repository_identity: str | None = None):
        self.repository_path = Path(repository_path)
        self.expected_repository_identity = expected_repository_identity
    
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
        
        # CRITICAL-3: Verify repository identity
        actual_identity = self._get_repository_identity()
        metadata["actual_repository_identity"] = actual_identity
        
        if self.expected_repository_identity and actual_identity != self.expected_repository_identity:
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message=(
                    f"Repository identity mismatch: "
                    f"expected '{self.expected_repository_identity}', "
                    f"actual '{actual_identity}'"
                ),
                metadata=metadata,
            )
        
        # MAJOR-3: Verify base commit is a commit object (not blob, tree, etc.)
        if base_commit and not self._is_commit_object(base_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message=f"Base commit is not a commit object: {base_commit}",
                metadata=metadata,
            )
        
        # MAJOR-3: Verify result commit is a commit object
        if result_commit and not self._is_commit_object(result_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message=f"Result commit is not a commit object: {result_commit}",
                metadata=metadata,
            )
        
        # Verify base commit exists
        if base_commit and not self._commit_exists(base_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message=f"Base commit does not exist: {base_commit}",
                metadata=metadata,
            )
        
        # Verify result commit exists
        if result_commit and not self._commit_exists(result_commit):
            return GitVerificationResult(
                classification=GitDiffClassification.INVALID_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message=f"Result commit does not exist: {result_commit}",
                metadata=metadata,
            )
        
        # If both commits are None, cannot verify
        if not base_commit or not result_commit:
            return GitVerificationResult(
                classification=GitDiffClassification.UNVERIFIABLE_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                error_message="Base or result commit not provided",
                metadata=metadata,
            )
        
        # Check for no-op (base == result)
        if base_commit == result_commit:
            # If base == result, there should be no changed files
            actual_changed_result = self._get_changed_files(base_commit, result_commit)
            
            # MAJOR-1: Handle git diff failure
            if not actual_changed_result.success:
                return GitVerificationResult(
                    classification=GitDiffClassification.UNVERIFIABLE_GIT_STATE,
                    repository_valid=repository_valid,
                    repository_identity=actual_identity,
                    actual_base_commit=base_commit,
                    actual_result_commit=result_commit,
                    error_message=f"Git diff failed: {actual_changed_result.error}",
                    metadata=metadata,
                )
            
            actual_changed = actual_changed_result.files
            
            # If caller claims changed files but base == result, that's invalid
            if claimed_changed_files and claimed_changed_files:
                return GitVerificationResult(
                    classification=GitDiffClassification.INVALID_GIT_STATE,
                    repository_valid=repository_valid,
                    repository_identity=actual_identity,
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
                repository_identity=actual_identity,
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
                repository_identity=actual_identity,
                actual_base_commit=base_commit,
                actual_result_commit=result_commit,
                error_message=f"Result commit {result_commit} is not a descendant of base commit {base_commit}",
                metadata=metadata,
            )
        
        # Get actual changed files
        actual_changed_result = self._get_changed_files(base_commit, result_commit)
        
        # MAJOR-1: Handle git diff failure
        if not actual_changed_result.success:
            return GitVerificationResult(
                classification=GitDiffClassification.UNVERIFIABLE_GIT_STATE,
                repository_valid=repository_valid,
                repository_identity=actual_identity,
                actual_base_commit=base_commit,
                actual_result_commit=result_commit,
                error_message=f"Git diff failed: {actual_changed_result.error}",
                metadata=metadata,
            )
        
        actual_changed = actual_changed_result.files
        
        # Check for mismatched file set
        if claimed_changed_files is not None:
            if set(claimed_changed_files) != set(actual_changed):
                return GitVerificationResult(
                    classification=GitDiffClassification.MISMATCHED_FILE_SET,
                    repository_valid=repository_valid,
                    repository_identity=actual_identity,
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
            repository_identity=actual_identity,
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
    
    def _get_repository_identity(self) -> str:
        """Get repository identity from remote origin URL.
        
        Returns normalized GitHub owner/name or remote URL.
        This provides a deterministic identity independent of local path.
        """
        try:
            # Try to get remote origin URL
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                # Normalize GitHub URLs to owner/name format
                if "github.com" in url:
                    # Extract owner/repo from various GitHub URL formats
                    # https://github.com/owner/repo.git
                    # git@github.com:owner/repo.git
                    if "/" in url:
                        parts = url.split("/")
                        repo_part = parts[-1].replace(".git", "")
                        owner_part = parts[-2]
                        return f"{owner_part}/{repo_part}"
                return url
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        # Fallback: use directory name as identity (less ideal but deterministic)
        return self.repository_path.name
    
    def _is_commit_object(self, commit: str) -> bool:
        """Check if the given SHA is a commit object (not blob, tree, tag, etc.).
        
        MAJOR-3: Prevents non-commit objects from being accepted as commits.
        """
        try:
            result = subprocess.run(
                ["git", "cat-file", "-t", commit],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                # Only accept if object type is "commit"
                return result.stdout.strip() == "commit"
            return False
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
    
    def _get_changed_files(self, base: str, result: str) -> ChangedFilesResult:
        """Get the list of changed files between two commits.
        
        MAJOR-1: Returns ChangedFilesResult to distinguish success from failure.
        Never returns [] for command failure - uses UNVERIFIABLE_GIT_STATE instead.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base, result],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return ChangedFilesResult(
                    success=False,
                    files=[],
                    error=result.stderr.strip() or f"git diff failed with exit code {result.returncode}",
                )
            
            files = [f for f in result.stdout.strip().split("\n") if f]
            return ChangedFilesResult(success=True, files=files)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            return ChangedFilesResult(
                success=False,
                files=[],
                error=str(e),
            )
    
    def _classify_diff(
        self,
        base: str,
        result: str,
        changed_files: list[str],
    ) -> GitDiffClassification:
        """Classify the diff between two commits.
        
        MAJOR-2: Deterministic classification.
        - WHITESPACE_ONLY: Only whitespace changes (verified with git diff -w)
        - COMMENT_ONLY: Only comment changes in supported languages (Python)
        - VALID_CHANGE: Real content changes
        - UNVERIFIABLE_GIT_STATE: Cannot determine classification
        
        For unsupported languages, returns VALID_CHANGE rather than guessing.
        """
        if not changed_files:
            return GitDiffClassification.NO_OP
        
        # MAJOR-2: Deterministic whitespace detection
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
            if diff_result.returncode == 0 and not diff_result.stdout.strip():
                return GitDiffClassification.WHITESPACE_ONLY
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # If we can't determine, return UNVERIFIABLE_GIT_STATE
            return GitDiffClassification.UNVERIFIABLE_GIT_STATE
        
        # MAJOR-2: Deterministic comment detection for Python only
        # Only attempt comment detection for Python files
        python_files = [f for f in changed_files if f.endswith('.py')]
        
        if python_files and len(changed_files) == len(python_files):
            # All changed files are Python - attempt comment detection
            try:
                diff_result = subprocess.run(
                    ["git", "diff", base, result],
                    cwd=self.repository_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if diff_result.returncode == 0:
                    diff_lines = diff_result.stdout.split("\n")
                    # Check if all added/removed lines are comments
                    non_comment_changes = 0
                    for line in diff_lines:
                        if line.startswith("+") and not line.startswith("+++"):
                            stripped = line[1:].lstrip()
                            # Python comment starts with #
                            if stripped and not stripped.startswith("#"):
                                non_comment_changes += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            stripped = line[1:].lstrip()
                            # Python comment starts with #
                            if stripped and not stripped.startswith("#"):
                                non_comment_changes += 1
                    
                    if non_comment_changes == 0:
                        return GitDiffClassification.COMMENT_ONLY
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                # If we can't determine, return UNVERIFIABLE_GIT_STATE
                return GitDiffClassification.UNVERIFIABLE_GIT_STATE
        
        # For non-Python files or mixed file types, return VALID_CHANGE
        # MAJOR-2: Don't guess for unsupported languages
        return GitDiffClassification.VALID_CHANGE
