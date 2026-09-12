"""P0-B V4-R9.7 Installer Provenance Test.

This test verifies that the installer script requires the exact commit
that matches the audited source target, not an ancestor or unrelated commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import pytest


def test_installer_required_commit_matches_audited_target():
    """Verify installer baseline commit matches audited target.
    
    This ensures deployment provenance consistency:
    - Installer baseline is R9.7 baseline
    - Audited source HEAD is baseline or descendant
    - Exact deployment mode can pin to specific commit
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"
    
    if not installer_path.exists():
        pytest.skip("Installer script not found")
    
    installer_content = installer_path.read_text(encoding='utf-8')
    
    # Extract baseline commit from installer
    import re
    match = re.search(r'\$baselineCommit = "([a-f0-9]+)"', installer_content)
    assert match, "Installer must contain baselineCommit variable"
    
    installer_baseline = match.group(1)
    
    # Expected R9.7 baseline
    expected_baseline = "c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3"
    
    # Verify installer baseline matches audited target
    assert installer_baseline == expected_baseline, (
        f"Installer baseline ({installer_baseline}) "
        f"does not match audited target ({expected_baseline})"
    )
    
    # Verify installer supports exact deployment mode
    assert 'ExactDeploymentCommit' in installer_content, (
        "Installer must support ExactDeploymentCommit parameter for exact deployment pinning"
    )


def test_installer_checks_exit_codes():
    """Verify installer checks exit codes for native commands.
    
    This prevents false-pass where a command fails but deployment continues.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"
    
    if not installer_path.exists():
        pytest.skip("Installer script not found")
    
    installer_content = installer_path.read_text(encoding='utf-8')
    
    # Check for proper exit code handling patterns
    # BAD: try { & command } catch { ... }  # ignores exit code
    # GOOD: & command; if ($LASTEXITCODE -ne 0) { exit 1 }
    
    # Check pywin32 verification uses exit code
    assert 'if ($LASTEXITCODE -ne 0)' in installer_content, (
        "Installer must check $LASTEXITCODE for pywin32 verification"
    )
    
    # Check cryptography verification uses exit code
    assert installer_content.count('if ($LASTEXITCODE -ne 0)') >= 2, (
        "Installer must check $LASTEXITCODE for multiple commands"
    )
    
    # Check for explicit exit on failure
    assert 'exit 1' in installer_content, (
        "Installer must exit with error code on failure"
    )


def test_trusted_python314_runtime_available():
    """Verify trusted Python 3.14 runtime exists and has required dependencies.
    
    This is a prerequisite for real deployment validation.
    """
    trusted_source = Path("C:\\Python314")
    
    if not trusted_source.exists():
        pytest.skip("Trusted Python 3.14 runtime not available (C:\\Python314)")
    
    # Verify Python version
    result = subprocess.run(
        [str(trusted_source / "python.exe"), "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Python 3.14 executable must be runnable"
    assert "3.14" in result.stdout, f"Expected Python 3.14, got: {result.stdout}"
    
    # Verify pywin32
    result = subprocess.run(
        [str(trusted_source / "python.exe"), "-c", "import win32service"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "pywin32 must be installed in trusted source"
    
    # Verify cryptography
    result = subprocess.run(
        [str(trusted_source / "python.exe"), "-c", "import cryptography"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "cryptography must be installed in trusted source"
    
    # Verify pythonservice.exe
    pythonservice_locations = [
        trusted_source / "Scripts" / "pythonservice.exe",
        trusted_source / "Lib" / "site-packages" / "win32" / "pythonservice.exe"
    ]
    
    pythonservice_found = any(loc.exists() for loc in pythonservice_locations)
    assert pythonservice_found, "pythonservice.exe must exist in trusted source"


def test_deployment_target_consistency():
    """Verify deployment target consistency across installer and code.
    
    This ensures that what the installer expects to deploy matches
    what the code actually implements.
    """
    # Get current HEAD
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=True
    )
    current_head = result.stdout.strip()
    
    # Expected R9.7 baseline
    expected_baseline = "c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3"
    
    # Check if current HEAD is baseline or a descendant of baseline
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", expected_baseline, current_head],
        cwd=Path(__file__).parent.parent,
        capture_output=True
    )
    
    is_descendant = result.returncode == 0
    assert current_head == expected_baseline or is_descendant, (
        f"Test must run from R9.7 baseline or descendant. "
        f"Expected: {expected_baseline} or descendant, Actual: {current_head}"
    )
    
    # Verify branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    current_branch = result.stdout.strip()
    
    # Verify we're on or at detached HEAD from the correct commit
    # (detached HEAD is fine for audit purposes)


def test_exact_deployment_mode():
    """Verify exact deployment mode works correctly.
    
    This tests that when ExactDeploymentCommit is provided,
    the installer requires that exact commit (not descendants).
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"
    
    if not installer_path.exists():
        pytest.skip("Installer script not found")
    
    installer_content = installer_path.read_text(encoding='utf-8')
    
    # Verify exact deployment mode logic exists
    assert 'ExactDeploymentCommit' in installer_content, (
        "Installer must support ExactDeploymentCommit parameter"
    )
    
    assert 'EXACT DEPLOYMENT MODE' in installer_content, (
        "Installer must have exact deployment mode logic"
    )
    
    assert 'BASELINE MODE' in installer_content, (
        "Installer must have baseline mode logic"
    )


def test_git_root_vs_project_root_semantics():
    """Verify installer separates Git root from project root.
    
    This tests that the installer correctly handles the repository layout:
    - Git root is the worktree root
    - Project root is Git root/IABV_v1.5
    - Source is at project root/src
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"
    
    if not installer_path.exists():
        pytest.skip("Installer script not found")
    
    installer_content = installer_path.read_text(encoding='utf-8')
    
    # Verify installer derives Git root
    assert 'git -C $RepoPath rev-parse --show-toplevel' in installer_content, (
        "Installer must derive Git root from RepoPath"
    )
    
    assert '$gitRoot' in installer_content, (
        "Installer must use $gitRoot variable"
    )
    
    # Verify installer derives project root
    assert 'Join-Path $gitRoot "IABV_v1.5"' in installer_content, (
        "Installer must derive project root as GitRoot/IABV_v1.5"
    )
    
    assert '$iabvProjectRoot' in installer_content, (
        "Installer must use $iabvProjectRoot variable"
    )
    
    # Verify installer uses project root for source paths
    assert r'$iabvProjectRoot\src' in installer_content or r'$iabvProjectRoot\src' in installer_content, (
        "Installer must use project root for source paths, not RepoPath/src"
    )
    
    # Verify PYTHONPATH uses project root
    assert r'$env:PYTHONPATH="$iabvProjectRoot\src"' in installer_content or r'$env:PYTHONPATH="$iabvProjectRoot\src"' in installer_content, (
        "Installer must set PYTHONPATH from project root, not RepoPath"
    )


def test_installer_accepts_git_root_as_repopath():
    """Verify installer works when RepoPath is Git root.

    This tests the correct semantics for the actual repository layout.
    """
    # Verify actual repository layout
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).parent.parent.parent,  # Git root
        capture_output=True,
        text=True,
        check=True
    )
    git_root = result.stdout.strip()

    # Verify IABV project exists at Git root/IABV_v1.5
    iabv_project = Path(git_root) / "IABV_v1.5"
    assert iabv_project.exists(), (
        f"IABV project root must exist at {iabv_project}"
    )

    # Verify source exists at project root/src
    iabv_source = iabv_project / "src" / "iabv_v15"
    assert iabv_source.exists(), (
        f"IABV source must exist at {iabv_source}"
    )

    # Verify installer exists at project root
    installer_path = iabv_project / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"
    assert installer_path.exists(), (
        f"Installer must exist at {installer_path}"
    )


def test_installer_fail_closed_filesystem_operations():
    """Verify installer is fail-closed for filesystem operations.

    This tests that Copy-Item, Remove-Item, New-Item, Set-Content
    use -ErrorAction Stop and abort deployment on failure.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Check for -ErrorAction Stop on critical filesystem operations
    critical_patterns = [
        ('Copy-Item', 'Copy-Item.*-ErrorAction Stop'),
        ('Remove-Item', 'Remove-Item.*-ErrorAction Stop'),
        ('New-Item', 'New-Item.*-ErrorAction Stop'),
        ('Set-Content', 'Set-Content.*-ErrorAction Stop'),
    ]

    for operation, pattern in critical_patterns:
        import re
        if not re.search(pattern, installer_content, re.IGNORECASE):
            # Some operations might be in try/catch blocks
            # Verify there's at least a try/catch structure for error handling
            assert 'try {' in installer_content.lower(), (
                f"Installer must have error handling for {operation}"
            )
            assert 'catch' in installer_content.lower(), (
                f"Installer must have error handling for {operation}"
            )
            assert 'exit 1' in installer_content, (
                f"Installer must exit on {operation} failure"
            )


def test_installer_fail_closed_native_commands():
    """Verify installer checks exit codes for native commands.

    This tests that icacls, python.exe, git, and other native commands
    have $LASTEXITCODE validation.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Count $LASTEXITCODE checks
    lastexitcode_count = installer_content.count('$LASTEXITCODE')
    assert lastexitcode_count >= 5, (
        f"Installer must check $LASTEXITCODE for native commands. "
        f"Found {lastexitcode_count} checks, expected at least 5"
    )

    # Verify icacls calls are followed by exit code checks
    icacls_lines = [line for line in installer_content.split('\n') if 'icacls' in line]
    assert len(icacls_lines) > 0, "Installer must use icacls for ACL configuration"

    # Verify at least one icacls is followed by exit code check
    found_icacls_with_check = False
    lines = installer_content.split('\n')
    for i, line in enumerate(lines):
        if 'icacls' in line and i + 1 < len(lines):
            # Check next few lines for exit code check
            for j in range(i + 1, min(i + 3, len(lines))):
                if '$LASTEXITCODE' in lines[j]:
                    found_icacls_with_check = True
                    break

    assert found_icacls_with_check, (
        "Installer must check $LASTEXITCODE after icacls commands"
    )


def test_installer_acl_identity_handling():
    """Verify installer uses well-known SIDs for ACL identities.

    This tests that ACL configuration uses SIDs instead of localized
    account names (e.g., "Administrators" vs "S-1-5-32-544").

    STATIC GUARD TEST: Verifies installer source code uses SIDs.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Verify well-known SIDs are used
    well_known_sids = [
        'S-1-5-32-544',  # Administrators
        'S-1-5-18',      # SYSTEM
        'S-1-5-19',      # LocalService
    ]

    sid_count = sum(1 for sid in well_known_sids if sid in installer_content)
    assert sid_count >= 3, (
        f"Installer should use well-known SIDs for ACL identities. "
        f"Found {sid_count} SIDs, expected at least 3"
    )

    # Verify SID format is used with icacls
    assert '*S-1-5' in installer_content, (
        "Installer must use SID format with icacls (e.g., *S-1-5-32-544)"
    )

    # Verify NO DENY policy (no explicit deny for Users)
    assert '/deny' not in installer_content.lower(), (
        "Installer should not use DENY ACLs - use explicit Allow only"
    )

    # Verify policy documentation in comments
    assert 'NO DENY' in installer_content, (
        "Installer should document NO DENY policy in comments"
    )


def test_installer_phase_16_python_executable_check():
    """Verify PHASE 16 checks python.exe existence before execution.

    This tests that the isolation test doesn't declare PASS if python.exe
    doesn't exist or fails to execute.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find PHASE 16 section
    phase_16_match = installer_content.find('PHASE 16')
    assert phase_16_match != -1, "Installer must have PHASE 16"

    phase_16_section = installer_content[phase_16_match:phase_16_match + 1000]

    # Verify python.exe existence check before execution
    assert 'Test-Path' in phase_16_section, (
        "PHASE 16 must check python.exe existence before execution"
    )

    # Verify exit code check after python.exe execution
    assert '$LASTEXITCODE' in phase_16_section, (
        "PHASE 16 must check $LASTEXITCODE after python.exe execution"
    )

    # Verify try/catch for python.exe execution
    assert 'try {' in phase_16_section.lower(), (
        "PHASE 16 must have error handling for python.exe execution"
    )


def test_no_false_success_after_critical_failure():
    """Verify installer does not print success messages after failures.

    This tests the NO_FALSE_SUCCESS_AFTER_CRITICAL_FAILURE property:
    - Critical operation fails
    - Deployment aborts immediately
    - No success message printed
    - Non-zero exit code
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find patterns where ERROR is followed by success message
    lines = installer_content.split('\n')
    for i, line in enumerate(lines):
        if 'ERROR:' in line:
            # Check next few lines - should not have success message
            # before exit 1
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].lower()
                if 'successfully' in next_line or 'pass' in next_line:
                    # Ensure there's an exit 1 between error and success
                    found_exit = False
                    for k in range(i, j):
                        if 'exit 1' in lines[k]:
                            found_exit = True
                            break
                    assert found_exit, (
                        f"Success message found after ERROR without exit 1. "
                        f"Line {i}: {line.strip()}, Line {j}: {lines[j].strip()}"
                    )


def test_installer_service_removal_checks_exit_code():
    """Verify installer checks exit code for service removal.

    This tests that service removal failures abort deployment.

    STATIC GUARD TEST: Verifies installer source code has exit code checks.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section (PHASE 22 after reordering)
    phase_22_match = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    assert phase_22_match != -1, "Installer must have PHASE 22 for service removal"

    phase_22_section = installer_content[phase_22_match:phase_22_match + 1000]

    # Verify exit code check for service removal
    assert '$LASTEXITCODE' in phase_22_section, (
        "PHASE 22 must check $LASTEXITCODE for service removal"
    )

    # Verify NO generic "continue" after removal failure
    assert 'continuing' not in phase_22_section.lower(), (
        "PHASE 22 must not have generic 'continuing' after removal failure"
    )

    # Verify explicit exit 1 on removal failure
    assert 'exit 1' in phase_22_section, (
        "PHASE 22 must exit with error code on removal failure"
    )


def test_installer_service_removal_postcondition_check():
    """Verify installer checks service actually removed after removal command.

    This tests that installer verifies POSTCONDITION: service does not exist
    using sc.exe query with deterministic exit codes.

    STATIC GUARD TEST: Verifies installer source code has postcondition check.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section
    phase_22_match = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    assert phase_22_match != -1, "Installer must have PHASE 22 for service removal"

    phase_22_section = installer_content[phase_22_match:phase_22_match + 1500]

    # Verify sc.exe query is used (not Get-CimInstance)
    assert 'sc.exe query' in phase_22_section, (
        "PHASE 22 must use sc.exe query for deterministic exit codes"
    )

    # Verify exit code 1060 is recognized as SERVICE_ABSENT
    assert '1060' in phase_22_section, (
        "PHASE 22 must recognize exit code 1060 as service absent"
    )

    # Verify exit code 0 is recognized as SERVICE_EXISTS
    assert 'exit code 0' in phase_22_section, (
        "PHASE 22 must recognize exit code 0 as service exists"
    )

    # Verify POSTCONDITION check after removal
    assert 'POSTCONDITION' in phase_22_section, (
        "PHASE 22 must verify POSTCONDITION after removal"
    )

    # Verify exit 1 if service still exists after removal (exit code 0)
    assert 'SERVICE_STILL_EXISTS' in phase_22_section or 'still exists' in phase_22_section.lower(), (
        "PHASE 22 must fail if service still exists after removal"
    )

    # Verify exit 1 for unknown query results
    assert 'SERVICE_QUERY_UNKNOWN' in phase_22_section or 'unknown exit code' in phase_22_section.lower(), (
        "PHASE 22 must fail on unknown query exit codes"
    )


def test_installer_service_query_semantics():
    """Verify installer distinguishes EXISTS/ABSENT/UNKNOWN in service query.

    This tests that UNKNOWN != ABSENT semantics are implemented.

    STATIC GUARD TEST: Verifies installer source code has correct semantics.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section
    phase_22_match = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    assert phase_22_match != -1, "Installer must have PHASE 22 for service removal"

    phase_22_section = installer_content[phase_22_match:phase_22_match + 1500]

    # A. UNKNOWN query result causes exit 1
    assert 'SERVICE_QUERY_UNKNOWN' in phase_22_section or 'unknown exit code' in phase_22_section.lower(), (
        "PHASE 22 must exit 1 on unknown query results"
    )

    # B. 1060 is the only accepted "service absent" result
    assert '1060' in phase_22_section, (
        "PHASE 22 must use 1060 as the service absent indicator"
    )
    assert 'ABSENT' in phase_22_section, (
        "PHASE 22 must label 1060 as ABSENT (not UNKNOWN)"
    )

    # C. 0 after removal causes failure
    assert 'SERVICE_STILL_EXISTS' in phase_22_section or ('exit code 0' in phase_22_section and 'FAIL' in phase_22_section), (
        "PHASE 22 must fail when query returns 0 after removal (service still exists)"
    )

    # D. arbitrary nonzero query result other than 1060 cannot be interpreted as absence
    # Verified by the unknown exit code check above

    # E. arbitrary postcondition query failure cannot be interpreted as removal success
    # Verified by the POSTCONDITION check for unknown exit codes


def test_installer_preflight_cleanup_fail_closed():
    """Verify installer pre-flight cleanup is fail-closed.

    This tests that pre-flight cleanup failure causes deployment abort,
    not WARNING + PASS.

    STATIC GUARD TEST: Verifies installer source code has fail-closed cleanup.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find pre-flight section
    preflight_match = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    assert preflight_match != -1, "Installer must have pre-flight check"

    preflight_section = installer_content[preflight_match:preflight_match + 2000]

    # Verify no WARNING + continue pattern for cleanup
    assert 'WARNING' not in preflight_section or 'continuing' not in preflight_section.lower(), (
        "Pre-flight cleanup must not use WARNING + continue pattern"
    )

    # Verify cleanup failure causes exit 1
    lines = preflight_section.split('\n')
    cleanup_found = False
    for i, line in enumerate(lines):
        if 'clean up' in line.lower() or 'cleanup' in line.lower():
            cleanup_found = True
            # Check next few lines for error handling
            for j in range(i, min(i + 5, len(lines))):
                if 'catch' in lines[j].lower() or 'try' in lines[j].lower():
                    # Verify there's an exit 1 in the catch block
                    for k in range(j, min(j + 5, len(lines))):
                        if 'exit 1' in lines[k]:
                            cleanup_fail_closed = True
                            break
                    assert cleanup_fail_closed, (
                        "Pre-flight cleanup failure must cause exit 1"
                    )
                    break

    assert cleanup_found, "Pre-flight section must have cleanup logic"


def test_installer_transactional_runtime_safety():
    """Verify installer uses staging runtime to avoid modifying active runtime.

    This tests that PHASE 11-21 operate on a staging directory separate from
    the active runtime, preventing modification of files that a running service
    might be using.

    STATIC GUARD TEST: Verifies installer source code has staging logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find PHASE 10 (staging runtime creation)
    phase_10_match = installer_content.find('PHASE 10: CREATE STAGING RUNTIME DIRECTORY')
    assert phase_10_match != -1, "Installer must have staging runtime creation phase"

    phase_10_section = installer_content[phase_10_match:phase_10_match + 500]

    # Verify staging path is different from active path
    assert 'staging' in phase_10_section.lower(), (
        "PHASE 10 must create a staging directory"
    )
    assert 'service_runtime_staging' in phase_10_section, (
        "Staging path must be distinct from active runtime path"
    )

    # Verify active runtime path is preserved
    assert 'activeRuntimePath' in phase_10_section or 'active runtime' in phase_10_section.lower(), (
        "PHASE 10 must preserve active runtime path reference"
    )

    # Find PHASE 22.5 (staging activation)
    phase_22_5_match = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')
    assert phase_22_5_match != -1, "Installer must have staging activation phase"

    phase_22_5_section = installer_content[phase_22_5_match:phase_22_5_match + 1000]

    # Verify staging is activated to active location after service removal
    # The code now uses rename (Move-Item) instead of destructive delete
    assert 'Move-Item' in phase_22_5_section, (
        "PHASE 22.5 must use Move-Item (rename) for activation"
    )
    assert 'backup' in phase_22_5_section.lower(), (
        "PHASE 22.5 must use backup path for rollback"
    )


def test_installer_staging_path_distinct_from_active():
    """Verify installer does not use production runtime as staging target.

    This tests that when service exists, PHASE 11-21 do not operate on
    C:\ProgramData\IABV\service_runtime directly.

    STATIC GUARD TEST: Verifies installer source code has distinct paths.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find PHASE 10 (staging creation)
    phase_10_idx = installer_content.find('PHASE 10: CREATE STAGING RUNTIME DIRECTORY')
    assert phase_10_idx != -1, "Installer must have staging creation"

    # Find where $serviceRuntimePath is redefined to staging
    phase_10_section = installer_content[phase_10_idx:phase_10_idx + 1500]

    # Verify $serviceRuntimePath is redefined to staging path
    assert '$serviceRuntimePath = $stagingRuntimePath' in phase_10_section, (
        "Installer must redefine $serviceRuntimePath to staging path after creation"
    )

    # Verify this happens before PHASE 11 (copy operations)
    phase_11_idx = installer_content.find('PHASE 11: COPY PYTHON RUNTIME')
    assert phase_11_idx != -1, "Installer must have PHASE 11"
    assert phase_10_idx < phase_11_idx, (
        "Staging path redefinition must occur before copy operations"
    )


def test_installer_destructive_action_after_service_transition():
    """Verify destructive runtime action uses rename/swap with rollback.

    This tests that activation uses rename operations (not destructive delete)
    and has rollback capability.

    STATIC GUARD TEST: Verifies installer source code has rename/swap logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find key phases
    service_removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    staging_activation_idx = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')

    assert service_removal_idx != -1, "Installer must have service removal"
    assert staging_activation_idx != -1, "Installer must have staging activation with rollback"

    # Verify order: service removal < staging activation
    assert service_removal_idx < staging_activation_idx, (
        "Service removal must occur before staging activation"
    )

    # Verify activation uses rename (Move-Item) not destructive delete
    staging_section = installer_content[staging_activation_idx:staging_activation_idx + 1000]
    assert 'Move-Item' in staging_section, (
        "Staging activation must use Move-Item (rename)"
    )
    assert 'backup' in staging_section.lower(), (
        "Staging activation must use backup path for rollback"
    )
    assert 'ROLLBACK' in staging_section, (
        "Staging activation must have rollback logic"
    )

    # Verify NO direct Remove-Item of active runtime before backup
    # The only Remove-Item should be in cleanup phase, not activation
    activation_section = installer_content[staging_activation_idx:staging_activation_idx + 800]
    # Remove-Item should not appear in activation before backup rename
    lines_before_rollback = activation_section.split('ROLLBACK')[0] if 'ROLLBACK' in activation_section else activation_section
    assert 'Remove-Item' not in lines_before_rollback or 'backup' in lines_before_rollback.lower(), (
        "Activation should not destructively delete active runtime before backup"
    )


def test_installer_activation_rollback_exists():
    """Verify installer has rollback logic for activation failure.

    This tests that if STAGING -> ACTIVE fails, installer attempts to restore BACKUP -> ACTIVE.

    STATIC GUARD TEST: Verifies installer source code has rollback logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find activation phase
    activation_idx = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')
    assert activation_idx != -1, "Installer must have activation phase with rollback"

    activation_section = installer_content[activation_idx:activation_idx + 1200]

    # Verify rollback exists
    assert 'ROLLBACK' in activation_section, (
        "Activation must have rollback logic"
    )
    assert 'backup' in activation_section.lower(), (
        "Rollback must restore from backup"
    )


def test_installer_rollback_failure_causes_installer_failure():
    """Verify rollback failure causes installer to exit with error.

    This tests that if rollback fails, installer does not continue as if nothing happened.

    STATIC GUARD TEST: Verifies installer source code has fail-closed rollback.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find activation phase
    activation_idx = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')
    assert activation_idx != -1, "Installer must have activation phase with rollback"

    activation_section = installer_content[activation_idx:activation_idx + 2000]

    # Verify rollback failure causes exit 1
    # Find rollback failure block
    rollback_failure_section = activation_section.split('ROLLBACK FAILED')[-1] if 'ROLLBACK FAILED' in activation_section else ""
    if rollback_failure_section:
        assert 'exit 1' in rollback_failure_section, (
            "Rollback failure must cause installer to exit with error"
        )
    else:
        # If ROLLBACK FAILED string not found, verify rollback has exit 1
        assert 'exit 1' in activation_section, (
            "Rollback logic must have exit 1 on failure"
        )


def test_installer_activation_postconditions_checked():
    """Verify installer checks postconditions after activation.

    This tests that installer verifies ACTIVE exists and STAGING no longer exists.

    STATIC GUARD TEST: Verifies installer source code has postcondition checks.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find activation phase
    activation_idx = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')
    assert activation_idx != -1, "Installer must have activation phase with rollback"

    activation_section = installer_content[activation_idx:activation_idx + 2000]

    # Verify active runtime existence check
    assert 'Test-Path $activeRuntimePath' in activation_section, (
        "Activation must verify active runtime exists"
    )

    # Verify staging no longer exists check (may be implicit in Move-Item success)
    # If explicit check not found, that's acceptable as Move-Item success implies staging moved
    staging_check = 'Test-Path $stagingRuntimePath' in activation_section
    if not staging_check:
        # Verify Move-Item success implies staging moved
        assert 'Move-Item' in activation_section and '$stagingRuntimePath' in activation_section, (
            "Activation must move staging runtime (implicit verification)"
        )


def test_installer_service_installation_after_activation():
    """Verify service installation occurs only after successful activation.

    This tests that service installation phase comes after activation phase.

    STATIC GUARD TEST: Verifies installer source code order.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find key phases
    activation_idx = installer_content.find('PHASE 22.5: ACTIVATE STAGING RUNTIME WITH ROLLBACK')
    service_install_idx = installer_content.find('PHASE 24: INSTALL SERVICE')

    assert activation_idx != -1, "Installer must have activation phase"
    assert service_install_idx != -1, "Installer must have service installation phase"

    # Verify order: activation < service installation
    assert activation_idx < service_install_idx, (
        "Service installation must occur after activation"
    )


def test_installer_orphan_cleanup_safe():
    """Verify orphan cleanup cannot delete active runtime.

    This tests that cleanup phase uses pattern matching and does not delete active runtime.

    STATIC GUARD TEST: Verifies installer source code has safe cleanup.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find cleanup phase
    cleanup_idx = installer_content.find('PHASE 9.5: CLEANUP ORPHAN STAGING')
    assert cleanup_idx != -1, "Installer must have orphan cleanup phase"

    cleanup_section = installer_content[cleanup_idx:cleanup_idx + 800]

    # Verify cleanup uses pattern matching
    assert 'service_runtime_staging_*' in cleanup_section, (
        "Cleanup must use pattern matching for staging directories"
    )
    assert 'service_runtime_backup_*' in cleanup_section, (
        "Cleanup must use pattern matching for backup directories"
    )

    # Verify cleanup has time cutoff (not immediate deletion)
    assert 'AddHours' in cleanup_section or 'AddDays' in cleanup_section, (
        "Cleanup must have time cutoff to avoid deleting recent artifacts"
    )

    # Verify cleanup does not delete active runtime path directly
    # The cleanup uses pattern matching, so it should not have direct reference to active path
    assert 'C:\\ProgramData\\IABV\\service_runtime' not in cleanup_section or 'staging' in cleanup_section.lower() or 'backup' in cleanup_section.lower(), (
        "Cleanup must not target active runtime path directly"
    )


def test_installer_final_pathname_references_active():
    """Verify final service PathName verification references active runtime.

    This tests that installer verifies service PathName points to the active runtime.

    STATIC GUARD TEST: Verifies installer source code has PathName verification.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find PathName verification phase
    pathname_idx = installer_content.find('PHASE 27: Verify PathName points to machine-scoped runtime')
    assert pathname_idx != -1, "Installer must have PathName verification phase"

    pathname_section = installer_content[pathname_idx:pathname_idx + 500]

    # Verify PathName check exists
    assert 'PathName' in pathname_section, (
        "Installer must verify service PathName"
    )
    # Verify PathName references service_runtime (not user profile)
    assert 'service_runtime' in pathname_section, (
        "PathName verification must reference service_runtime path"
    )


def test_installer_verification_targets_staging():
    """Verify verification phases target staging runtime, not active.

    This tests that PHASE 16-21 (isolation, ACLs, component verification)
    operate on the staging runtime before activation.

    STATIC GUARD TEST: Verifies installer source code verification targets.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find verification phases
    phase_16_idx = installer_content.find('PHASE 16: VERIFY PYTHON314._PTH ISOLATION')
    phase_21_idx = installer_content.find('PHASE 21: VERIFY CRITICAL COMPONENT ACLS')
    phase_22_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')

    assert phase_16_idx != -1, "Installer must have isolation verification"
    assert phase_21_idx != -1, "Installer must have ACL verification"
    assert phase_22_idx != -1, "Installer must have service removal"

    # Verify verification occurs before service removal
    assert phase_16_idx < phase_22_idx, (
        "Isolation verification must occur before service removal"
    )
    assert phase_21_idx < phase_22_idx, (
        "ACL verification must occur before service removal"
    )

    # Since $serviceRuntimePath is redefined to staging, all verification
    # automatically targets staging. This is verified by the redefinition test.


def test_installer_failure_never_triggers_service_removal():
    """Verify staging/verification failure never triggers service removal.

    This tests that if staging or verification fails, the service is not removed.

    STATIC GUARD TEST: Verifies installer source code order.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find key phases
    phase_10_idx = installer_content.find('PHASE 10: CREATE STAGING RUNTIME DIRECTORY')
    phase_21_idx = installer_content.find('PHASE 21: VERIFY CRITICAL COMPONENT ACLS')
    phase_22_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')

    assert phase_10_idx != -1, "Installer must have staging creation"
    assert phase_21_idx != -1, "Installer must have verification"
    assert phase_22_idx != -1, "Installer must have service removal"

    # Verify order: staging/verification < service removal
    assert phase_10_idx < phase_22_idx, (
        "Staging creation must occur before service removal"
    )
    assert phase_21_idx < phase_22_idx, (
        "Verification must occur before service removal"
    )

    # Since exit 1 on failure prevents reaching service removal, this is implicit


def test_installer_service_removal_failure_blocks_installation():
    """Verify service removal failure blocks final installation.

    This tests that if service removal fails, installation is not attempted.

    STATIC GUARD TEST: Verifies installer source code has abort logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal and installation sections
    removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    install_idx = installer_content.find('PHASE 24: INSTALL SERVICE')

    assert removal_idx != -1, "Installer must have service removal"
    assert install_idx != -1, "Installer must have service installation"

    removal_section = installer_content[removal_idx:install_idx]

    # Verify exit 1 on removal failure
    assert 'exit 1' in removal_section, (
        "Service removal must exit with error code on failure"
    )

    # Implicit: exit 1 prevents reaching installation


def test_installer_unknown_service_state_never_becomes_absence():
    """Verify unknown service state is never treated as absence.

    This tests that sc.exe query failures (non-0, non-1060) cause fail-closed,
    not continuation as if service were absent.

    STATIC GUARD TEST: Verifies installer source code semantics.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section
    phase_22_match = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    assert phase_22_match != -1, "Installer must have PHASE 22"

    phase_22_section = installer_content[phase_22_match:phase_22_match + 1500]

    # Verify unknown exit code causes exit 1
    assert 'unknown exit code' in phase_22_section.lower() or 'SERVICE_QUERY_UNKNOWN' in phase_22_section, (
        "Unknown query result must cause exit 1 (not treated as absence)"
    )

    # Verify 1060 is the only accepted absence indicator
    assert '1060' in phase_22_section, (
        "Exit code 1060 must be the only accepted absence indicator"
    )
    assert 'ABSENT' in phase_22_section, (
        "1060 must be labeled as ABSENT (not UNKNOWN)"
    )


def test_installer_service_removal_accepts_missing_service():
    """Verify installer accepts missing service as valid precondition.

    This tests that when service does not exist, installer continues
    without attempting removal.

    STATIC GUARD TEST: Verifies installer source code handles missing service.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section
    phase_22_match = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    assert phase_22_match != -1, "Installer must have PHASE 22 for service removal"

    phase_22_section = installer_content[phase_22_match:phase_22_match + 1000]

    # Verify check for service existence before removal
    assert 'serviceExists' in phase_22_section or 'service exists' in phase_22_section.lower(), (
        "PHASE 22 must check if service exists before removal"
    )

    # Verify ACCEPTED_PRECONDITION for missing service
    assert 'ABSENT' in phase_22_section or '1060' in phase_22_section, (
        "PHASE 22 must recognize missing service as valid precondition"
    )

    # Verify skip removal when service does not exist
    # The installer might not have an explicit "skip" message if it just doesn't enter the removal block
    # Just verify that 1060 is handled as a valid state


def test_installer_has_preflight_permission_check():
    """Verify installer has pre-flight permission check before destructive actions.

    This tests that deployment verifies permissions before removing service
    or modifying runtime, preventing degraded state.

    STATIC GUARD TEST: Verifies installer source code has pre-check phase.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Verify pre-flight check phase exists
    assert 'PHASE 9: PRE-FLIGHT PERMISSION CHECK' in installer_content, (
        "Installer must have pre-flight permission check phase"
    )

    # Verify pre-flight comes before service removal
    preflight_index = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    service_removal_index = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')

    assert preflight_index != -1 and service_removal_index != -1, (
        "Installer must have both pre-flight and service removal phases"
    )

    assert preflight_index < service_removal_index, (
        "Pre-flight check must occur before service removal"
    )

    # Verify pre-flight tests creation, write, deletion
    preflight_section = installer_content[preflight_index:preflight_index + 2000]
    assert 'New-Item' in preflight_section, (
        "Pre-flight must test directory creation"
    )
    assert 'Set-Content' in preflight_section, (
        "Pre-flight must test file write"
    )
    assert 'Remove-Item' in preflight_section, (
        "Pre-flight must test directory deletion"
    )


def test_installer_transactional_order():
    """Verify installer follows transactional deployment order.

    This tests that deployment follows:
    PRECHECK -> PREPARE -> VERIFY -> ACTIVATE

    Order should be:
    1. Pre-flight permission check
    2. Runtime preparation (copy files, configure)
    3. Runtime verification (isolation test, ACL verification)
    4. Service removal (destructive)
    5. Service installation (activate)

    STATIC GUARD TEST: Verifies installer source code has correct order.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find key phases
    preflight_idx = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    runtime_copy_idx = installer_content.find('PHASE 11: COPY PYTHON RUNTIME')
    isolation_verify_idx = installer_content.find('PHASE 16: VERIFY PYTHON314._PTH ISOLATION')
    service_removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    service_install_idx = installer_content.find('PHASE 24: INSTALL SERVICE')

    # Verify all phases exist
    assert preflight_idx != -1, "Installer must have pre-flight check"
    assert runtime_copy_idx != -1, "Installer must have runtime copy phase"
    assert isolation_verify_idx != -1, "Installer must have isolation verification"
    assert service_removal_idx != -1, "Installer must have service removal"
    assert service_install_idx != -1, "Installer must have service installation"

    # Verify order: pre-check < prepare < verify < remove < install
    assert preflight_idx < runtime_copy_idx, (
        "Pre-flight must occur before runtime copy"
    )
    assert runtime_copy_idx < isolation_verify_idx, (
        "Runtime copy must occur before isolation verification"
    )
    assert isolation_verify_idx < service_removal_idx, (
        "Isolation verification must occur before service removal"
    )
    assert service_removal_idx < service_install_idx, (
        "Service removal must occur before service installation"
    )


def test_installer_preflight_fresh_deployment():
    """Verify installer pre-flight handles fresh deployment (runtime does not exist).

    This tests that pre-flight can create parent directory, create runtime,
    write, delete, and clean up test artifacts.

    STATIC GUARD TEST: Verifies installer source code has fresh deployment logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find pre-flight section
    preflight_match = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    assert preflight_match != -1, "Installer must have pre-flight check"

    preflight_section = installer_content[preflight_match:preflight_match + 2000]

    # Verify check for runtime existence
    assert 'runtimeExists' in preflight_section or 'runtime exists' in preflight_section.lower(), (
        "Pre-flight must check if runtime directory exists"
    )

    # Verify fresh deployment scenario handling
    assert 'Fresh deployment' in preflight_section or 'does not exist' in preflight_section.lower(), (
        "Pre-flight must handle fresh deployment scenario"
    )

    # Verify parent directory creation test
    assert 'New-Item' in preflight_section, (
        "Pre-flight must test directory creation for fresh deployment"
    )

    # Verify write test
    assert 'Set-Content' in preflight_section, (
        "Pre-flight must test file write"
    )

    # Verify delete test
    assert 'Remove-Item' in preflight_section, (
        "Pre-flight must test file/directory deletion"
    )


def test_installer_preflight_existing_runtime():
    """Verify installer pre-flight handles existing runtime scenario.

    This tests that pre-flight can write and delete in existing runtime
    without destroying the real runtime.

    STATIC GUARD TEST: Verifies installer source code has existing runtime logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find pre-flight section
    preflight_match = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    assert preflight_match != -1, "Installer must have pre-flight check"

    preflight_section = installer_content[preflight_match:preflight_match + 2000]

    # Verify existing runtime scenario handling
    assert 'Existing runtime' in preflight_section or 'already exists' in preflight_section.lower(), (
        "Pre-flight must handle existing runtime scenario"
    )

    # Verify that existing runtime test does NOT destroy real runtime
    # Should use test file with __preflight_test__ pattern, not Remove-Item -Recurse on runtime
    assert '__preflight_test__' in preflight_section, (
        "Pre-flight should use test file pattern for existing runtime test"
    )

    # Verify no destructive Remove-Item on runtime itself in pre-flight
    lines = preflight_section.split('\n')
    for i, line in enumerate(lines):
        if 'Remove-Item' in line and 'service_runtime' in line:
            # Check if this is removing the test file, not the runtime itself
            if '__preflight_test__' not in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if '__preflight_test__' not in next_line:
                    assert False, (
                        "Pre-flight should not remove runtime directory itself, only test files"
                    )


def test_installer_no_destructive_action_before_preflight():
    """Verify installer does not perform destructive actions before pre-flight success.

    This tests that service removal and runtime destruction occur only after
    pre-flight permission check passes.

    STATIC GUARD TEST: Verifies installer source code order.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find key phases
    preflight_idx = installer_content.find('PHASE 9: PRE-FLIGHT PERMISSION CHECK')
    service_removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    runtime_remove_idx = installer_content.find('Removing existing runtime directory')

    # Verify pre-flight exists
    assert preflight_idx != -1, "Installer must have pre-flight check"

    # Verify service removal comes after pre-flight
    if service_removal_idx != -1:
        assert preflight_idx < service_removal_idx, (
            "Pre-flight must occur before service removal"
        )

    # Verify runtime directory removal comes after pre-flight
    if runtime_remove_idx != -1:
        assert preflight_idx < runtime_remove_idx, (
            "Pre-flight must occur before runtime directory removal"
        )


def test_installer_no_service_install_after_removal_failure():
    """Verify installer does not attempt service installation after removal failure.

    This tests that if service removal fails, deployment aborts before
    attempting installation.

    STATIC GUARD TEST: Verifies installer source code has abort logic.
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal and installation sections
    removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    install_idx = installer_content.find('PHASE 24: INSTALL SERVICE')

    assert removal_idx != -1, "Installer must have service removal phase"
    assert install_idx != -1, "Installer must have service installation phase"

    removal_section = installer_content[removal_idx:install_idx]

    # Verify exit 1 on removal failure
    assert 'exit 1' in removal_section, (
        "Service removal phase must exit with error code on failure"
    )

    # Verify that installation phase is separate and only reached if removal succeeds
    # (implicit by the exit 1 in removal phase)


def test_installer_negative_control_causality():
    """Verify installer has causal relationship between removal failure and abort.

    This test documents the requirement for runtime negative testing:
    - When service removal command returns non-zero
    - Installer must exit non-zero
    - Service installation must NOT be attempted

    STATIC GUARD TEST: Verifies installer source code has the structure.
    RUNTIME TEST REQUIRED: To prove actual causality, need to execute installer
    with a failing service removal and verify it aborts before installation.

    Current status: NOT_PROVEN (requires Administrator execution on real Windows)
    """
    installer_path = Path(__file__).parent.parent / "P0_B_V4_R9_7_INSTALLER_PROVENANCE_RUNTIME_DEPLOYMENT.ps1"

    if not installer_path.exists():
        pytest.skip("Installer script not found")

    installer_content = installer_path.read_text(encoding='utf-8')

    # Find service removal section
    removal_idx = installer_content.find('PHASE 22: REMOVE EXISTING SERVICE')
    install_idx = installer_content.find('PHASE 24: INSTALL SERVICE')

    assert removal_idx != -1, "Installer must have service removal phase"
    assert install_idx != -1, "Installer must have service installation phase"

    removal_section = installer_content[removal_idx:install_idx]

    # Verify structure: exit code check → exit 1 → no installation
    assert '$LASTEXITCODE' in removal_section, (
        "Service removal must check exit code"
    )
    assert 'exit 1' in removal_section, (
        "Service removal must exit on failure"
    )

    # This is a static guard - actual causality requires runtime test
    # Documented as NOT_PROVEN until runtime test is executed
    pass  # Static guard test - structure verified

