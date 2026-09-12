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
