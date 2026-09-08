"""
Real test execution to produce DevelopmentTestResult from actual test run.

This test executes a real pytest command and constructs a DevelopmentTestResult
from the actual execution data.
"""

import subprocess
import sys
import time
from pathlib import Path
from iabv_v15.domain.models import DevelopmentTestResult, DevelopmentTestStatus


def test_real_pytest_execution_produces_development_test_result():
    """Execute real pytest and construct DevelopmentTestResult from actual data."""
    # Execute a small, stable test
    command = f'"{sys.executable}" -m pytest tests/test_development_test_result.py::TestDevelopmentTestResultStatus::test_passed_complete -v --tb=no'
    
    # Derive project root from test file location for portability
    project_root = Path(__file__).resolve().parent.parent
    
    start_time = time.time()
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )
    duration_seconds = time.time() - start_time
    
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
        test_count=None,  # No parser yet
        passed_count=None,
        failed_count=None,
        error_count=None,
        skipped_count=None,
        commit=None,  # Not provided by pytest execution
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
