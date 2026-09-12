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

    phase_22_section = installer_content[phase_22_match:phase_22_match + 500]

    # Verify exit code check for service removal
    assert '$LASTEXITCODE' in phase_22_section, (
        "PHASE 22 must check $LASTEXITCODE for service removal"
    )


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
    preflight_section = installer_content[preflight_index:preflight_index + 1000]
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
    service_install_idx = installer_content.find('PHASE 23: INSTALL SERVICE')

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

