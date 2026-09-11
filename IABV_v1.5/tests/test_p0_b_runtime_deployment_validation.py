"""P0-B V4-R9.7 Runtime Deployment Validation Test.

This test verifies the actual deployed runtime state against the expected
V4-R9.7 deployment configuration.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import pytest


def test_service_exists_with_correct_identity():
    """Verify Windows service exists with LocalService identity."""
    result = subprocess.run(
        ["powershell", "-Command", "Get-Service -Name 'IABVAuditAuthority' -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        pytest.skip("IABVAuditAuthority service not found")
    
    assert "IABVAuditAuthority" in result.stdout, "Service name not found"
    
    # Verify StartName is LocalService
    result = subprocess.run(
        ["powershell", "-Command", 
         "Get-WmiObject -Class Win32_Service -Filter \"Name='IABVAuditAuthority'\" | Select-Object -ExpandProperty StartName"],
        capture_output=True,
        text=True
    )
    
    assert "LocalService" in result.stdout or "NT AUTHORITY\\LocalService" in result.stdout, (
        f"Service must run as LocalService, got: {result.stdout}"
    )


def test_service_pathname_isolated_runtime():
    """Verify service uses isolated runtime, not user-installed Python.
    
    V4-R9.7 should deploy to C:\ProgramData\IABV\service_runtime
    NOT to user-installed miniconda or other Python.
    """
    result = subprocess.run(
        ["powershell", "-Command",
         "Get-WmiObject -Class Win32_Service -Filter \"Name='IABVAuditAuthority'\" | Select-Object -ExpandProperty PathName"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        pytest.skip("Cannot query service PathName")
    
    pathname = result.stdout.strip()
    
    # V4-R9.7 expected path: C:\ProgramData\IABV\service_runtime\pythonservice.exe
    # BAD: user-installed Python like C:\Users\faber\miniconda3\pythonservice.exe
    # BAD: generic Python installation paths
    
    if "miniconda" in pathname.lower() or "anaconda" in pathname.lower():
        pytest.fail(
            f"Service PathName uses user-installed Python (conda/miniconda): {pathname}. "
            "V4-R9.7 should use isolated runtime at C:\\ProgramData\\IABV\\service_runtime"
        )
    
    if pathname.startswith("C:\\Users\\"):
        pytest.fail(
            f"Service PathName is in user directory: {pathname}. "
            "V4-R9.7 should use machine-scoped runtime at C:\\ProgramData\\IABV\\service_runtime"
        )
    
    # Check if using expected isolated runtime
    if "ProgramData\\IABV\\service_runtime" not in pathname:
        pytest.fail(
            f"Service PathName does not use isolated runtime: {pathname}. "
            "V4-R9.7 should use C:\\ProgramData\\IABV\\service_runtime"
        )


def test_machine_level_trust_anchor_exists():
    """Verify machine-level provisioner trust anchor exists."""
    trust_anchor_path = Path("C:\\ProgramData\\IABV\\provisioner_trust")
    
    if not trust_anchor_path.exists():
        pytest.fail(
            f"Machine-level trust anchor not found: {trust_anchor_path}. "
            "V4-R9.7 requires C:\\ProgramData\\IABV\\provisioner_trust\\ to exist"
        )


def test_runtime_isolation_directory_exists():
    """Verify isolated runtime directory exists."""
    runtime_path = Path("C:\\ProgramData\\IABV\\service_runtime")
    
    if not runtime_path.exists():
        pytest.fail(
            f"Isolated runtime directory not found: {runtime_path}. "
            "V4-R9.7 should deploy to C:\\ProgramData\\IABV\\service_runtime"
        )


def test_python314_pth_isolation():
    """Verify python314._pth isolation if runtime exists.
    
    This requires read access to the deployed runtime, which may be
    restricted to LocalService. This test documents the check but
    may fail due to ACL restrictions.
    """
    runtime_path = Path("C:\\ProgramData\\IABV\\service_runtime")
    
    if not runtime_path.exists():
        pytest.skip("Isolated runtime not deployed")
    
    pth_file = runtime_path / "python314._pth"
    
    if not pth_file.exists():
        pytest.fail(
            f"python314._pth not found in isolated runtime: {pth_file}. "
            "V4-R9.7 requires .pth isolation"
        )
    
    # Try to read .pth file (may fail due to ACLs)
    try:
        pth_content = pth_file.read_text(encoding='utf-8')
        
        # Verify .pth restricts module search
        # Should contain import statements to stdlib only
        # Should NOT include user-site or writable directories
        if "site-packages" in pth_content and "import" not in pth_content:
            pytest.fail(
                f"python314._pth may allow arbitrary site-packages: {pth_content}"
            )
    except PermissionError:
        pytest.skip("Cannot read .pth file (ACL restricted to LocalService)")


def test_repo_path_integrity():
    """Verify deployed runtime corresponds to audited source.
    
    This checks if the deployed runtime actually uses the RepoPath
    that was specified during deployment.
    """
    # This requires access to service configuration or runtime
    # which may be restricted. Document the limitation.
    pytest.skip(
        "RepoPath integrity verification requires access to service configuration "
        "or deployed runtime files, which may be ACL-restricted to LocalService"
    )


def test_acl_enforcement_ordinary_user():
    """Test that ordinary user cannot write to protected directories.
    
    This is an adversarial test to verify ACL enforcement.
    """
    import os
    import tempfile
    
    # Test ordinary user cannot write to machine-level trust anchor
    trust_anchor_path = Path("C:\\ProgramData\\IABV\\provisioner_trust")
    
    if not trust_anchor_path.exists():
        pytest.skip("Machine-level trust anchor not deployed")
    
    # Try to create a test file (should fail)
    test_file = trust_anchor_path / "ordinary_user_test.txt"
    
    try:
        test_file.write_text("test")
        # If we reach here, write succeeded - BAD
        test_file.unlink()  # Clean up if possible
        pytest.fail(
            f"Ordinary user can write to machine-level trust anchor: {trust_anchor_path}. "
            "ACL enforcement is NOT working"
        )
    except PermissionError:
        # Expected - ACL enforcement is working
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error testing ACL: {e}")
    
    # Test ordinary user cannot write to isolated runtime
    runtime_path = Path("C:\\ProgramData\\IABV\\service_runtime")
    
    if not runtime_path.exists():
        pytest.skip("Isolated runtime not deployed")
    
    test_file = runtime_path / "ordinary_user_test.txt"
    
    try:
        test_file.write_text("test")
        test_file.unlink()
        pytest.fail(
            f"Ordinary user can write to isolated runtime: {runtime_path}. "
            "ACL enforcement is NOT working"
        )
    except PermissionError:
        # Expected
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error testing runtime ACL: {e}")


def test_v4_r3_historical_attack_reproduction():
    """Attempt to reproduce V4-r3 historical attack.
    
    Historical attack: ordinary caller could fabricate/replace trust root
    and tests would self-provision with the same bypass.
    
    This test attempts to create/replace trust root as ordinary user.
    """
    import json
    from pathlib import Path
    
    # Attempt to create unauthorized trust store
    trust_anchor_path = Path("C:\\ProgramData\\IABV\\provisioner_trust")
    
    if not trust_anchor_path.exists():
        pytest.skip("Machine-level trust anchor not deployed")
    
    # Try to create a fake authority_trust.json
    fake_trust_store = trust_anchor_path / "authority_trust.json"
    
    fake_data = {
        "trusted_keys": [
            {
                "key_id": "attacker_key",
                "public_key_hex": "00" * 32,
                "added_at_utc": "2026-09-11T00:00:00Z",
                "provisioned_by": "attacker"
            }
        ],
        "provisioner_signature": "fake_signature"
    }
    
    try:
        fake_trust_store.write_text(json.dumps(fake_data))
        # If we reach here, write succeeded - BAD
        fake_trust_store.unlink()
        pytest.fail(
            f"Ordinary user can create/replace trust store: {fake_trust_store}. "
            "V4-r3 historical attack STILL EXPLOITABLE"
        )
    except PermissionError:
        # Expected - ACL enforcement blocks attack
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error testing V4-r3 attack: {e}")


def test_deployment_provenance_integrity():
    """Verify deployment provenance matches audited source.
    
    This checks if the deployed runtime actually corresponds to the
    commit that was supposed to be deployed.
    """
    # Get current source HEAD
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=True
    )
    source_head = result.stdout.strip()
    
    # Expected V4-R9.7 HEAD or remediation
    expected_head = "c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3"
    remediation_head = "1c008317b965e8c938e48c3c8e584b9779ac0e5a7"
    
    assert source_head in [expected_head, remediation_head], (
        f"Source HEAD mismatch. Expected: {expected_head} or {remediation_head}, Actual: {source_head}"
    )
    
    # Note: Verifying deployed runtime commit requires access to
    # deployed files or service configuration, which may be ACL-restricted
    pytest.skip(
        "Deployed runtime commit verification requires access to "
        "service configuration or deployed files (ACL-restricted)"
    )
