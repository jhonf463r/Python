# P0-B V4-R9.2 Security Test Plan

## TEST OVERVIEW

This document describes the security test plan for P0-B V4-r9.2, including unit tests, integration tests, Windows runtime tests, and adversarial tests.

---

## TEST CLASSIFICATION

### UNIT TESTS
- Test individual functions and classes in isolation
- Run in any environment (Windows, Linux, macOS)
- Do not require Administrator privileges
- Do not require Windows Service deployment

### STRUCTURAL TESTS
- Test architectural components
- Verify code structure and interfaces
- Do not require runtime deployment

### INTEGRATION TESTS
- Test interaction between components
- Verify integration points (provisioning + trust store + authority)
- Do not require Administrator privileges

### WINDOWS RUNTIME TESTS
- Test actual Windows behavior (ACL, DPAPI, Named Pipe)
- Require Windows platform
- May require Administrator privileges for some tests
- Collect runtime evidence

### WINDOWS ADVERSARIAL TESTS
- Test attack scenarios against implementation
- Require Administrator deployment first
- Require normal user context for attack simulation
- Collect adversarial runtime evidence

---

## F5 TESTS

### Test 1: First-Writer Attack (Unit/Integration)
**File:** `test_p0_b_v4_runtime_windows.py::test_1_first_writer_attack`

**Purpose:** Verify ordinary caller cannot create trust root

**Scenario:**
- Ordinary process attempts to create trust directory
- Ordinary process attempts to create trust file with attacker-provisioned marker
- Runtime should reject attacker-provisioned trust

**Expected:** PASS (runtime rejects attacker provisioning)

**Classification:** Unit/Integration

**Status:** PASS (V4-r9.2)

---

### Test 2: Runtime Cannot Write Trust (Unit/Integration)
**File:** `test_p0_b_v4_runtime_windows.py::test_2_runtime_cannot_write_trust`

**Purpose:** Verify runtime has no write API for trust store

**Scenario:**
- Check for write methods in AuthorityTrustConfig
- Verify no add_trusted_key, rotate_key, write_config, etc.

**Expected:** PASS (no write methods exist)

**Classification:** Unit/Integration

**Status:** PASS (V4-r9.2)

---

### Test 3: ACL Application and Verification (Windows Runtime)
**File:** `test_p0_b_v4_runtime_windows.py::test_3_acl_application_and_verification`

**Purpose:** Verify ACL can be applied and verified

**Scenario:**
- Administrator calls setup_protected_directory()
- Apply ACL via icacls
- Verify effective ACL with icacls

**Expected:** PROVEN (if admin) or NOT_PROVEN (if not admin)

**Classification:** Windows Runtime

**Status:** NOT_PROVEN (requires Administrator)

---

### Test 4: Trust Store Deletion Fail-Closed (Unit/Integration)
**File:** `test_p0_b_v4_runtime_windows.py::test_4_trust_store_deletion_fail_closed`

**Purpose:** Verify trust store deletion causes fail-closed

**Scenario:**
- Create valid trust store with signature
- Delete trust file
- Runtime should fail to initialize

**Expected:** PASS (ValueError raised)

**Classification:** Unit/Integration

**Status:** PASS (V4-r9.2)

---

### Test 5: Trust Store Corruption Fail-Closed (Unit/Integration)
**File:** `test_p0_b_v4_runtime_windows.py::test_5_trust_store_corruption_fail_closed`

**Purpose:** Verify corruption causes fail-closed

**Scenario:**
- Write malformed JSON to trust file
- Runtime should fail to load

**Expected:** PASS (ValueError raised)

**Classification:** Unit/Integration

**Status:** PASS (V4-r9.2)

---

### Test 6: DPAPI Runtime (Windows Runtime)
**File:** `test_p0_b_v4_runtime_windows.py::test_6_dpapi_runtime`

**Purpose:** Verify DPAPI is available and works

**Scenario:**
- Test DPAPI protect/unprotect of test data
- Verify encrypted data != plaintext
- Verify unprotect recovers original data

**Expected:** PROVEN (DPAPI available and functional)

**Classification:** Windows Runtime

**Status:** PROVEN (V4-r9.2)

---

### Test 7: DPAPI Same-User Threat Model (Windows Runtime)
**File:** `test_p0_b4_runtime_windows.py::test_7_dpapi_same_user_threat_model`

**Purpose:** Verify DPAPI same-user decryption behavior

**Scenario:**
- Process A protects data with DPAPI
- Process B (same user) attempts to decrypt
- Verify if same-user processes can decrypt each other's data

**Expected:** FAILED (DPAPI allows same-user decryption - security limitation)

**Classification:** Windows Runtime

**Status:** FAILED (V4-r9.2 - DPAPI limitation confirmed)

---

### Test 8: Windows ACL Real Enforcement (Windows Runtime)
**File:** `test_p0_b_v4_runtime_windows.py::test_8_windows_acl_real_enforcement`

**Purpose:** Test actual file access attempts

**Scenario:**
- Attempt to create file in protected directory
- Attempt to write to existing file
- Attempt to delete file
- Attempt to rename directory

**Expected:** NOT_PROVEN (requires ACL setup first)

**Classification:** Windows Runtime

**Status:** NOT_PROVEN (V4-r9.2 - requires ACL setup)

---

### Test 9: F5 Machine-Level Trust Anchor Write (Windows Adversarial)
**File:** `test_p0_b_v4_runtime_windows.py::test_9_f5_machine_level_trust_anchor_write`

**Purpose:** Verify normal user cannot write to C:\ProgramData

**Scenario:**
- Normal user attempts to create directory in C:\ProgramData
- Normal user attempts to write file
- Verify ACCESS_DENIED

**Expected:** PASS (normal user gets ACCESS_DENIED)

**Classification:** Windows Adversarial

**Status:** NOT_PROVEN (V4-r9.2 - requires actual C:\ProgramData with ACL)

---

### Test 10: F5 Combined Replacement Attack (Windows Adversarial)
**File:** `test_p0_b_v4_runtime_windows.py::test_10_f5_combined_replacement_attack`

**Purpose:** Verify attacker cannot replace both trust anchor and trust store

**Scenario:**
- Attacker attempts to replace trust anchor
- Attacker attempts to replace trust store
- Verify both cannot be replaced without admin

**Expected:** PASS (cannot replace both without admin)

**Classification:** Windows Adversarial

**Status:** NOT_PROVEN (V4-r9.2 - requires actual C:\ProgramData with ACL)

---

## F14 TESTS

### Test 11: F14 Service Key Access (Windows Adversarial)
**File:** `test_p0_b_v4_runtime_windows.py::test_11_f14_service_key_access`

**Purpose:** Verify normal user cannot access service-scoped key

**Scenario:**
- Normal user attempts to read C:\ProgramData\IABV\authority_keys\
- Normal user attempts to read authority_private_key.json
- Verify ACCESS_DENIED

**Expected:** PASS (normal user gets ACCESS_DENIED)

**Classification:** Windows Adversarial

**Status:** NOT_PROVEN (V4-r9.2 - service not deployed)

---

### Test 12: F14 IPC Unauthorized (Windows Adversarial)
**File:** `test_p0_b_v4_runtime_windows.py::test_12_f14_ipc_unauthorized`

**Purpose:** Verify unauthorized caller gets denied by service

**Scenario:**
- Attacker attempts to connect to Named Pipe
- Attacker attempts to send CERTIFY request
- Verify service denies unauthorized caller

**Expected:** PASS (service denies or pipe not found)

**Classification:** Windows Adversarial

**Status:** NOT_PROVEN (V4-r9.2 - service not deployed)

---

## REPLAY TESTS

### Test: Replay Protection (Integration)
**File:** `test_p0_b_v4_authority.py` (existing tests)

**Purpose:** Verify replay protection under concurrency

**Scenario:**
- Simulate concurrent certification attempts with identical evidence
- Verify exactly one authoritative record
- Verify no inconsistent duplicates

**Expected:** PASS (replay protection works)

**Classification:** Integration

**Status:** PASS (inherited from V4-r6)

---

## GIT RUNTIME TESTS

### Test: Real Git Verification (Windows Runtime)
**File:** `test_p0_b_v4_runtime_windows.py` (future)

**Purpose:** Verify Git repository verification

**Scenario:**
- Verify repository root
- Verify HEAD
- Verify branch
- Verify changed files
- Verify working tree
- Verify commit relationship

**Expected:** PROVEN (Git verification works)

**Classification:** Windows Runtime

**Status:** NOT_TESTED (V4-r9.2 - requires implementation)

---

## TEST EXECUTION INSTRUCTIONS

### Unit Tests (No Administrator Required)

```powershell
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_authority.py -q
```

### Windows Runtime Tests (Administrator May Be Required)

```powershell
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_runtime_windows.py -v
```

### Adversarial Tests (Administrator Deployment Required First)

**Prerequisites:**
1. Deploy Windows Service (see Windows Deployment Guide)
2. Configure ACLs (see Windows Deployment Guide)
3. Start service
4. Generate authority key (requires implementation)

**Execution:**
```powershell
# Run as normal user (not Administrator)
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_runtime_windows.py::test_9_f5_machine_level_trust_anchor_write -v
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_runtime_windows.py::test_10_f5_combined_replacement_attack -v
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_runtime_windows.py::test_11_f14_service_key_access -v
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_p0_b_v4_runtime_windows.py::test_12_f14_ipc_unauthorized -v
```

---

## TEST RESULTS EXPECTED

### V4-r9.2 Expected Results (Without Deployment)

| Test | Expected Without Deployment | Actual V4-r9.2 |
|------|------------------------------|----------------|
| test_1_first_writer_attack | PASS | PASS |
| test_2_runtime_cannot_write_trust | PASS | PASS |
| test_3_acl_application_and_verification | NOT_PROVEN (not admin) | NOT_PROVEN |
| test_4_trust_store_deletion_fail_closed | PASS | PASS |
| test_5_trust_store_corruption_fail_closed | PASS | PASS |
| test_6_dpapi_runtime | PROVEN | PROVEN |
| test_7_dpapi_same_user_threat_model | FAILED | FAILED |
| test_8_windows_acl_real_enforcement | NOT_PROVEN | NOT_PROVEN |
| test_9_f5_machine_level_trust_anchor_write | NOT_PROVEN (no ACL) | NOT_PROVEN |
| test_10_f5_combined_replacement_attack | NOT_PROVEN (no ACL) | NOT_PROVEN |
| test_11_f14_service_key_access | NOT_PROVEN (no service) | NOT_PROVEN |
| test_12_f14_ipc_unauthorized | NOT_PROVEN (no service) | NOT_PROVEN |

### V4-r9.2 Expected Results (With Deployment)

| Test | Expected With Deployment | Status |
|------|--------------------------|--------|
| test_9_f5_machine_level_trust_anchor_write | PASS (ACCESS_DENIED) | NOT_TESTED |
| test_10_f5_combined_replacement_attack | PASS (cannot replace both) | NOT_TESTED |
| test_11_f14_service_key_access | PASS (ACCESS_DENIED) | NOT_TESTED |
| test_12_f14_ipc_unauthorized | PASS (service denies) | NOT_TESTED |

---

## TEST EVIDENCE COLLECTION

### Evidence Format

Each test returns a dictionary with:
```json
{
  "test": "Test name",
  "user_sid": "S-1-5-21-...",
  "process_integrity": "ADMIN" or "STANDARD",
  "status": "PASS" | "FAILED" | "PROVEN" | "NOT_PROVEN" | "ERROR",
  "evidence": {
    "key": "value",
    ...
  }
}
```

### Evidence Storage

Test results are saved to:
- `tests/p0_b_v4_runtime_results.json`

---

## FAIL-CRITERIA

### Test Failure Criteria

- **PASS:** Test demonstrates expected security behavior
- **FAILED:** Test demonstrates security vulnerability
- **PROVEN:** Test confirms security property with runtime evidence
- **NOT_PROVEN:** Test cannot confirm security property (missing prerequisites)
- **ERROR:** Test execution error (test bug, not security issue)

### Security Boundary Failure

If any critical test returns FAILED:
- F5 or F14 cannot be marked PROVEN
- P0-B remains OPEN
- Root cause must be addressed

---

## TEST PRIORITIES

### Critical Tests (Must Pass for PROVEN)

1. **test_9_f5_machine_level_trust_anchor_write:** F5 circular dependency
2. **test_10_f5_combined_replacement_attack:** F5 combined replacement
3. **test_11_f14_service_key_access:** F14 same-user isolation
4. **test_12_f14_ipc_unauthorized:** F14 IPC authorization

### Important Tests (Should Pass)

1. **test_3_acl_application_and_verification:** F5 ACL enforcement
2. **test_7_dpapi_same_user_threat_model:** F14 DPAPI limitation documentation
3. **test_8_windows_acl_real_enforcement:** F5 ACL behavioral

### Supporting Tests

1. **test_1_first_writer_attack:** F5 first-writer prevention
2. **test_2_runtime_cannot_write_trust:** F5 write API absence
3. **test_4_trust_store_deletion_fail_closed:** F5 fail-closed
4. **test_5_trust_store_corruption_fail_closed:** F5 fail-closed
5. **test_6_dpapi_runtime:** F14 DPAPI availability

---

## SECURITY VERIFICATION CHECKLIST

Before marking F5 or F14 as PROVEN, verify:

- [ ] All critical tests executed with deployment
- [ ] All critical tests return PASS or PROVEN
- [ ] No critical tests return FAILED
- [ ] Evidence collected from Windows runtime
- [ ] Evidence collected from adversarial context
- [ ] ACL configuration verified with icacls
- [ ] Service identity verified with task manager
- [ ] Named Pipe ACL verified
- [ ] Caller SID validation verified
- [ ] Fail-closed behavior verified

---

## CONTINUOUS TESTING

### Regression Testing

After any code changes:
1. Run unit tests
2. Run focused tests for changed components
3. Run full test suite if changes touch shared contracts

### Adversarial Testing

After deployment:
1. Run adversarial tests monthly
2. Verify no regression in security properties
3. Update test plan if new attack vectors discovered

---

## SUPPORT

For test failures:
1. Check test output in `tests/p0_b_v4_runtime_results.json`
2. Check Windows Event Viewer for service logs
3. Verify deployment prerequisites
4. Verify ACL configuration with icacls
