# VFINAL5-R3 Regression Test Results

**Date:** 2026-08-25
**Status:** PARTIAL - Test Updates Required

---

## Regression Tests Run

### Test Suite
- test_f14_authority_down_fail_closed.py: PASSED
- test_f15_autonomous_evolution_execution.py: PASSED (4 skipped)
- test_f16_rollback_authorization.py: PASSED
- test_critical2_github_remote_authorization.py: 3 FAILED, 4 skipped
- test_actionrequest_contract.py: PASSED

### Results Summary
- **Total Tests:** 34
- **Passed:** 27
- **Failed:** 3
- **Skipped:** 4

---

## Failed Tests

### test_critical2_github_remote_authorization.py

**Test 1:** test_github_remote_requires_capability
- **Error:** "PR creation requires separate capability (pr_lease_id). No capability provided."
- **Cause:** Implementation requires separate pr_lease_id, test only provides lease_id
- **Status:** Test update required

**Test 2:** test_github_remote_wrong_action_rejects
- **Error:** "PR creation requires separate capability (pr_lease_id). No capability provided."
- **Cause:** Implementation requires separate pr_lease_id, test only provides lease_id
- **Status:** Test update required

**Test 3:** test_github_remote_replay_rejects
- **Error:** "PR creation requires separate capability (pr_lease_id). No capability provided."
- **Cause:** Implementation requires separate pr_lease_id, test only provides lease_id
- **Status:** Test update required

---

## Analysis

The GitHubRemoteService implementation has evolved since the test was written. The service now requires a separate pr_lease_id for PR creation, in addition to the lease_id for git push.

**Impact:** These are test failures, not code failures. The implementation is correct (it enforces separate capabilities for git push and PR creation), but the tests need to be updated to provide both capabilities.

**Recommendation:** Update tests to provide both lease_id (for git push) and pr_lease_id (for PR creation).

---

## Conclusion

Core regression tests (F14, F15, F16, ActionRequest) are passing. GitHubRemoteService tests need updates to match current implementation.

**Status:** PARTIAL - Test updates required for GitHubRemoteService
