"""
Real test execution to produce DevelopmentTestResult from actual test run.

This test executes a real pytest command and constructs a DevelopmentTestResult
from the actual execution data, including real Git commit capture.
"""

import subprocess
import time
from pathlib import Path
from iabv_v15.domain.models import DevelopmentTestResult, DevelopmentTestStatus


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
        # Git not available, not in a Git repo, or other error
        # This is acceptable - the model allows commit=None
        return None


def test_real_pytest_execution_produces_development_test_result():
    """Execute real pytest and construct DevelopmentTestResult from actual data."""
    # Portable path resolution: derive project root from test file location
    test_file = Path(__file__).resolve()
    project_root = test_file.parent.parent  # Go from tests/ to project root
    
    # Execute a small, stable test using portable paths
    command = "pytest tests/test_development_test_result.py::TestDevelopmentTestResultStatus::test_passed_complete -v --tb=no"
    
    start_time = time.time()
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(project_root)  # Use portable project root
    )
    duration_seconds = time.time() - start_time
    
    # Capture real Git commit from the repository
    commit = get_git_commit(project_root)
    
    # Determine status from exit code
    if result.returncode == 0:
        status = DevelopmentTestStatus.PASSED
    else:
        status = DevelopmentTestStatus.FAILED
    
    # Construct DevelopmentTestResult from actual execution data
    # Note: We don't have a parser yet, so test counts are None
    test_result = DevelopmentTestResult(
        status=status,
        command=command,
        exit_code=result.returncode,
        duration_seconds=round(duration_seconds, 2),
        stdout=result.stdout,
        stderr=result.stderr,
        test_count=None,  # No parser yet - prefer None over invented counts
        passed_count=None,
        failed_count=None,
        error_count=None,
        skipped_count=None,
        commit=commit,  # Real Git commit or None if not available
    )
    
    # Verify the result was constructed
    assert test_result.status == DevelopmentTestStatus.PASSED
    assert test_result.exit_code == 0
    assert test_result.duration_seconds > 0
    assert test_result.command == command
    assert "test_passed_complete" in test_result.stdout
    
    print(f"\nReal test execution result:")
    print(f"  Status: {test_result.status}")
    print(f"  Exit code: {test_result.exit_code}")
    print(f"  Duration: {test_result.duration_seconds}s")
    print(f"  Command: {test_result.command}")
    print(f"  Commit: {test_result.commit}")
    print(f"  CWD strategy: portable (derived from test file location)")

