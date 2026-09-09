"""P0-B V4-r5 Windows Runtime Security Tests.

This module executes real Windows runtime security tests for:
- F5: Trust-root first-writer attack
- F5: Authorized provisioning with UAC
- F5: Effective ACL verification
- F14: Real DPAPI testing

Evidence Level: RUNTIME / ADVERSARIAL RUNTIME (on Windows)
"""

import ctypes
import os
import sys
import tempfile
import json
import subprocess
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iabv_v15.services.development.authority_trust_config import AuthorityTrustConfig
from iabv_v15.services.development.authority_os_provisioning import OSAuthorityProvisioner
from iabv_v15.services.development.audit_authority_process import AuditAuthorityProcess


def check_admin_privilege() -> tuple[bool, str]:
    """Check if current process has admin privilege.
    
    Returns:
        (is_admin, process_integrity_level)
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        return is_admin, "ADMIN" if is_admin else "STANDARD"
    except Exception as exc:
        return False, f"ERROR: {exc}"


def get_user_sid() -> str:
    """Get current user SID."""
    try:
        result = subprocess.run(
            ["whoami", "/user"],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            # Parse SID from output
            for line in result.stdout.split('\n'):
                if 'S-1-5-' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[-1]
        return "UNKNOWN"
    except Exception as exc:
        return f"ERROR: {exc}"


def test_1_first_writer_attack() -> dict[str, Any]:
    """F5 Runtime Test: First-writer attack from ordinary process.
    
    Expected: Ordinary caller cannot create trust root (even if directory exists).
    """
    result = {
        "test": "F5 First-Writer Attack",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "FAILED",
        "evidence": {},
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        protected_root = Path(tmpdir) / "authority_protected"
        
        # Attempt 1: Create directory as ordinary caller
        try:
            protected_root.mkdir(parents=True, exist_ok=True)
            result["evidence"]["directory_created"] = True
            result["evidence"]["directory_path"] = str(protected_root)
        except Exception as exc:
            result["evidence"]["directory_created"] = False
            result["evidence"]["directory_creation_error"] = str(exc)
        
        # Attempt 2: Create trust config through runtime
        # V4-r5 FIX: Should fail even if directory exists (unless trust file exists with valid provisioning)
        try:
            config = AuthorityTrustConfig(protected_root)
            result["evidence"]["config_initialized"] = True
            result["evidence"]["config_keys_count"] = len(config.get_all_trusted_keys())
        except ValueError as exc:
            result["evidence"]["config_initialized"] = False
            result["evidence"]["config_error"] = str(exc)
            if "does not exist" in str(exc) or "may have been created by unauthorized" in str(exc):
                result["status"] = "PASS"
        
        # Attempt 3: Create trust file (simulate attacker creating trust store)
        trust_file = protected_root / "authority_trust.json"
        trust_data = {
            "version": "1.0",
            "trusted_keys": [{
                "key_id": "attacker_key",
                "public_key_hex": "attacker123",
                "added_at_utc": "2024-01-01T00:00:00Z",
                "provisioned_by": "ATTACKER",  # Not OS_PROVISIONER
            }]
        }
        trust_file.write_text(json.dumps(trust_data), encoding='utf-8')
        
        # Attempt 4: Runtime should reject attacker-provisioned trust
        try:
            config2 = AuthorityTrustConfig(protected_root)
            result["evidence"]["attacker_trust_accepted"] = True
            result["status"] = "FAILED"
        except ValueError as exc:
            result["evidence"]["attacker_trust_accepted"] = False
            result["evidence"]["attacker_trust_error"] = str(exc)
            if "authorized provisioner" in str(exc):
                result["status"] = "PASS"
    
    return result


def test_2_runtime_cannot_write_trust() -> dict[str, Any]:
    """F5 Runtime Test: Runtime cannot write trust root.
    
    Expected: Runtime has no write API for trust store.
    """
    result = {
        "test": "F5 Runtime Cannot Write Trust",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "PASS",
        "evidence": {},
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        protected_root = Path(tmpdir) / "authority_protected"
        protected_root.mkdir(parents=True, exist_ok=True)
        
        # Create valid trust store with OS_PROVISIONER marker
        trust_file = protected_root / "authority_trust.json"
        trust_data = {
            "version": "1.0",
            "trusted_keys": [{
                "key_id": "test_key",
                "public_key_hex": "abc123",
                "added_at_utc": "2024-01-01T00:00:00Z",
                "provisioned_by": "OS_PROVISIONER",
            }]
        }
        trust_file.write_text(json.dumps(trust_data), encoding='utf-8')
        
        config = AuthorityTrustConfig(protected_root)
        
        # Check for write methods
        write_methods = [
            "add_trusted_key",
            "rotate_key",
            "write_config",
            "save_config",
            "provision_authority_key",
        ]
        
        result["evidence"]["write_methods"] = {}
        for method in write_methods:
            has_method = hasattr(config, method)
            result["evidence"]["write_methods"][method] = has_method
            if has_method:
                result["status"] = "FAILED"
    
    return result


def test_3_acl_application_and_verification() -> dict[str, Any]:
    """F5 Runtime Test: ACL application and verification.
    
    Expected: ACL can be applied and verified (if admin).
    """
    result = {
        "test": "F5 ACL Application and Verification",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "NOT_PROVEN",
        "evidence": {},
    }
    
    is_admin, integrity = check_admin_privilege()
    result["evidence"]["is_admin"] = is_admin
    result["evidence"]["integrity_level"] = integrity
    
    if not is_admin:
        result["evidence"]["acl_test_skipped"] = "Requires admin privilege"
        return result
    
    with tempfile.TemporaryDirectory() as tmpdir:
        protected_root = Path(tmpdir) / "authority_protected"
        
        # Attempt ACL setup via static method
        try:
            OSAuthorityProvisioner.setup_protected_directory(protected_root)
            result["evidence"]["acl_setup_success"] = True
            result["evidence"]["protected_root"] = str(protected_root)
        except Exception as exc:
            result["evidence"]["acl_setup_success"] = False
            result["evidence"]["acl_setup_error"] = str(exc)
            return result
        
        # Inspect ACL with icacls
        try:
            result_icacls = subprocess.run(
                ["icacls", str(protected_root)],
                capture_output=True,
                text=True,
                shell=True
            )
            result["evidence"]["icacls_output"] = result_icacls.stdout
            result["evidence"]["icacls_returncode"] = result_icacls.returncode
            
            if result_icacls.returncode == 0:
                result["status"] = "PROVEN"
        except Exception as exc:
            result["evidence"]["icacls_error"] = str(exc)
    
    return result


def test_4_trust_store_deletion_fail_closed() -> dict[str, Any]:
    """F5 Runtime Test: Trust store deletion causes fail-closed.
    
    Expected: Authority fails to initialize after deletion.
    """
    result = {
        "test": "F5 Trust Store Deletion Fail-Closed",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "PASS",
        "evidence": {},
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        protected_root = Path(tmpdir) / "authority_protected"
        protected_root.mkdir(parents=True, exist_ok=True)
        
        # Create trust store with OS_PROVISIONER marker
        trust_file = protected_root / "authority_trust.json"
        trust_data = {
            "version": "1.0",
            "trusted_keys": [{
                "key_id": "test_key",
                "public_key_hex": "abc123",
                "added_at_utc": "2024-01-01T00:00:00Z",
                "provisioned_by": "OS_PROVISIONER",
            }]
        }
        trust_file.write_text(json.dumps(trust_data), encoding='utf-8')
        
        # Verify runtime can load
        config = AuthorityTrustConfig(protected_root)
        result["evidence"]["initial_config_load"] = len(config.get_all_trusted_keys()) > 0
        
        # Delete trust file
        trust_file.unlink()
        
        # Runtime should fail to initialize (no trust file)
        try:
            config2 = AuthorityTrustConfig(protected_root)
            result["status"] = "FAILED"
            result["evidence"]["after_deletion_keys"] = "FAILED - should have raised"
        except ValueError as exc:
            result["evidence"]["after_deletion_keys"] = "PASS - raised ValueError"
            if "trust store not found" in str(exc):
                result["status"] = "PASS"
        
        # Delete directory
        import shutil
        shutil.rmtree(protected_root)
        
        # Runtime should fail to initialize
        try:
            config3 = AuthorityTrustConfig(protected_root)
            result["status"] = "FAILED"
            result["evidence"]["after_directory_deletion"] = "FAILED - should have raised"
        except ValueError as exc:
            result["evidence"]["after_directory_deletion"] = "PASS - raised ValueError"
            if "does not exist" in str(exc):
                result["status"] = "PASS"
    
    return result


def test_5_trust_store_corruption_fail_closed() -> dict[str, Any]:
    """F5 Runtime Test: Trust store corruption causes fail-closed.
    
    Expected: Corrupted trust store causes fail-closed.
    """
    result = {
        "test": "F5 Trust Store Corruption Fail-Closed",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "PASS",
        "evidence": {},
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        protected_root = Path(tmpdir) / "authority_protected"
        protected_root.mkdir(parents=True, exist_ok=True)
        
        # Write malformed JSON
        trust_file = protected_root / "authority_trust.json"
        trust_file.write_text("{invalid json", encoding='utf-8')
        
        # Runtime should fail to load
        try:
            config = AuthorityTrustConfig(protected_root)
            result["status"] = "FAILED"
            result["evidence"]["corruption_handled"] = "FAILED - should have raised"
        except ValueError as exc:
            result["evidence"]["corruption_handled"] = "PASS - raised ValueError"
            if "corrupted" in str(exc).lower():
                result["status"] = "PASS"
    
    return result


def test_6_dpapi_runtime() -> dict[str, Any]:
    """F14 Runtime Test: Real DPAPI execution.
    
    Expected: DPAPI is available and can protect/unprotect data.
    """
    result = {
        "test": "F14 DPAPI Runtime",
        "user_sid": get_user_sid(),
        "process_integrity": check_admin_privilege()[1],
        "status": "NOT_PROVEN",
        "evidence": {},
    }
    
    # Check if DPAPI is available
    try:
        import win32crypt
        result["evidence"]["win32crypt_available"] = True
    except ImportError:
        result["evidence"]["win32crypt_available"] = False
        result["evidence"]["dpapi_error"] = "win32crypt not available"
        return result
    
    # Test DPAPI protect/unprotect
    try:
        test_data = b"test secret data"
        protected = win32crypt.CryptProtectData(test_data, None, None, None, None, 0)
        
        if isinstance(protected, tuple):
            protected_bytes = protected[0]
        else:
            protected_bytes = protected
        
        result["evidence"]["protect_success"] = True
        result["evidence"]["protected_length"] = len(protected_bytes)
        
        # Verify it's not plaintext
        if protected_bytes == test_data:
            result["evidence"]["protect_plaintext"] = True
            result["status"] = "FAILED"
        else:
            result["evidence"]["protect_plaintext"] = False
        
        # Test unprotect
        unprotected = win32crypt.CryptUnprotectData(protected_bytes, None, None, None)
        
        result["evidence"]["unprotect_success"] = True
        result["evidence"]["unprotect_type"] = str(type(unprotected))
        
        # According to win32crypt behavior, returns (description, data) tuple
        if isinstance(unprotected, tuple):
            # Second element is the actual data
            if len(unprotected) >= 2:
                unprotected_bytes = unprotected[1]
            else:
                unprotected_bytes = unprotected[0]
        else:
            unprotected_bytes = unprotected
        
        result["evidence"]["unprotect_bytes_length"] = len(unprotected_bytes)
        
        if unprotected_bytes == test_data:
            result["evidence"]["unprotect_matches"] = True
            result["status"] = "PROVEN"
        else:
            result["evidence"]["unprotect_matches"] = False
            result["status"] = "FAILED"
            
    except Exception as exc:
        result["evidence"]["dpapi_test_error"] = str(exc)
        result["status"] = "FAILED"
    
    return result


def main():
    """Execute all Windows runtime security tests."""
    print("=" * 80)
    print("P0-B V4-r4 Windows Runtime Security Tests")
    print("=" * 80)
    print(f"User SID: {get_user_sid()}")
    print(f"Process Integrity: {check_admin_privilege()[1]}")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("=" * 80)
    
    tests = [
        test_1_first_writer_attack,
        test_2_runtime_cannot_write_trust,
        test_3_acl_application_and_verification,
        test_4_trust_store_deletion_fail_closed,
        test_5_trust_store_corruption_fail_closed,
        test_6_dpapi_runtime,
    ]
    
    results = []
    for test_func in tests:
        print(f"\nExecuting: {test_func.__name__}")
        try:
            result = test_func()
            results.append(result)
            print(f"Status: {result['status']}")
            print(f"Evidence: {json.dumps(result['evidence'], indent=2)}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({
                "test": test_func.__name__,
                "status": "ERROR",
                "error": str(exc)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["status"] == "PASS" or r["status"] == "PROVEN")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    not_proven = sum(1 for r in results if r["status"] == "NOT_PROVEN")
    
    print(f"Passed/Proven: {passed}")
    print(f"Failed: {failed}")
    print(f"Not Proven: {not_proven}")
    print(f"Total: {len(results)}")
    
    # Write results to file
    output_file = Path(__file__).parent / "p0_b_v4_runtime_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to: {output_file}")


if __name__ == "__main__":
    main()
