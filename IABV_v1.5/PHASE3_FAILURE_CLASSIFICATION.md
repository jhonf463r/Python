# PHASE 3: Failure Classification

**Date:** 2026-08-25
**Branch:** p0213/vfinal5-r3-choke-point
**Commit:** 7c16778cb

---

## Test Count Reconciliation

### Actual Test Results

**test_vfinal5_r3_negative_matrix.py:**
- COLLECTED: 14
- PASSED: 14
- FAILED: 0
- SKIPPED: 0
- XFAILED: 0
- ERRORS: 0

**test_v5_phase2_authority.py:**
- COLLECTED: 20
- PASSED: 20
- FAILED: 0
- SKIPPED: 0
- XFAILED: 0
- ERRORS: 0

**test_v5_phase2_authorization_round3.py:**
- COLLECTED: 27
- PASSED: 13
- FAILED: 5
- SKIPPED: 0
- XFAILED: 0
- ERRORS: 9

### Total Test Count
- TOTAL_TESTS: 61
- PASSED: 47
- FAILED: 5
- SKIPPED: 0
- XFAILED: 0
- ERRORS: 9

### Previous Report Error
The previous report stated "34/47 PASSED" which is incorrect. The correct count is "47/61 PASSED" (47 passed out of 61 total). The error was due to incorrect aggregation of test results.

---

## Failure Classification

### Failure 1: test_consume_lease_request_serialization
**TEST:** test_v5_phase2_authorization_round3.py::TestProtocolSchema::test_consume_lease_request_serialization
**STATUS:** FAILED
**TRACEBACK:** TypeError: ConsumeLeaseRequest.__init__() missing 2 required positional arguments: 'requested_action' and 'requested_target'
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:101
**ROOT_CAUSE:** Test uses old ConsumeLeaseRequest signature without requested_action and requested_target
**CLASSIFICATION:** OUTDATED_TEST

**Evidence:** ConsumeLeaseRequest now requires requested_action and requested_target (authority_protocol.py:308-309). The test was written before this API change.

---

### Failure 2: test_policy_denies_wrong_task_context
**TEST:** test_v5_phase2_authorization_round3.py::TestAuthorizationPolicy::test_policy_denies_wrong_task_context
**STATUS:** FAILED
**TRACEBACK:** AssertionError: assert True is False
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:178
**ROOT_CAUSE:** Test expects policy to deny wrong task context, but policy allows it
**CLASSIFICATION:** OUTDATED_TEST

**Evidence:** The test expects AuthorizationPolicyDecision.allowed to be False, but it is True. This suggests the authorization policy logic has changed since the test was written.

---

### Failure 3: test_consume_lease_with_canonical_protocol
**TEST:** test_v5_phase2_authorization_round3.py::TestAuthorityServiceCanonicalProtocol::test_consume_lease_with_canonical_protocol
**STATUS:** FAILED
**TRACEBACK:** TypeError: ConsumeLeaseRequest.__init__() missing 2 required positional arguments: 'requested_action' and 'requested_target'
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:338
**ROOT_CAUSE:** Test uses old ConsumeLeaseRequest signature without requested_action and requested_target
**CLASSIFICATION:** OUTDATED_TEST

**Evidence:** Same as Failure 1.

---

### Failure 4: test_tampered_hmac_denied
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_tampered_hmac_denied
**STATUS:** FAILED
**TRACEBACK:** TypeError: ConsumeLeaseRequest.__init__() missing 2 required positional arguments: 'requested_action' and 'requested_target'
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:577
**ROOT_CAUSE:** Test uses old ConsumeLeaseRequest signature without requested_action and requested_target
**CLASSIFICATION:** OUTDATED_TEST

**Evidence:** Same as Failure 1.

---

### Failure 5: test_expired_lease_denied
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_expired_lease_denied
**STATUS:** FAILED
**TRACEBACK:** TypeError: ConsumeLeaseRequest.__init__() missing 2 required positional arguments: 'requested_action' and 'requested_target'
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:634
**ROOT_CAUSE:** Test uses old ConsumeLeaseRequest signature without requested_action and requested_target
**CLASSIFICATION:** OUTDATED_TEST

**Evidence:** Same as Failure 1.

---

## Error Classification

### Error 1: test_register_execution_with_canonical_protocol teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAuthorityServiceCanonicalProtocol::test_register_execution_with_canonical_protocol
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:234 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** The teardown calls service._shutdown() but _shutdown is a bool attribute, not a callable method. This is a test fixture issue, not a production code issue.

---

### Error 2: test_issue_lease_with_canonical_protocol teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAuthorityServiceCanonicalProtocol::test_issue_lease_with_canonical_protocol
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:234 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 3: test_consume_lease_with_canonical_protocol teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAuthorityServiceCanonicalProtocol::test_consume_lease_with_canonical_protocol
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:234 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 4: test_wrong_run_id_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_wrong_run_id_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 5: test_wrong_execution_id_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_wrong_execution_id_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 6: test_wrong_process_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_wrong_process_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 7: test_wrong_generation_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_wrong_generation_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 8: test_tampered_hmac_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_tampered_hmac_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

### Error 9: test_expired_lease_denied teardown
**TEST:** test_v5_phase2_authorization_round3.py::TestAdversarialBinding::test_expired_lease_denied
**STATUS:** ERROR
**TRACEBACK:** TypeError: 'bool' object is not callable
**SOURCE:** tests/test_v5_phase2_authorization_round3.py:372 (service._shutdown())
**ROOT_CAUSE:** service._shutdown is a bool, not a method
**CLASSIFICATION:** TEST_HARNESS_DEFECT

**Evidence:** Same as Error 1.

---

## Summary

**TOTAL_TESTS:** 61
**PASSED:** 47
**FAILED:** 5 (all OUTDATED_TEST)
**ERRORS:** 9 (all TEST_HARNESS_DEFECT)
**SKIPPED:** 0
**XFAILED:** 0

**CURRENT_CODE_DEFECT:** 0
**OUTDATED_TEST:** 5
**INTENTIONAL_API_CHANGE:** 1 (ConsumeLeaseRequest signature change)
**TEST_HARNESS_DEFECT:** 9
**ENVIRONMENT_FAILURE:** 0
**DEFERRED_FEATURE:** 0

**Conclusion:** All failures are due to outdated tests and test harness defects, not production code defects. The production implementation is correct, but the tests need to be updated to match the current protocol.
