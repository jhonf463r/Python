R3.3 C2 FINAL FORENSIC - LIMITATIONS
====================================

LIMITATIONS OF CURRENT EVIDENCE:
--------------------------------

1. Repository state not captured
   - The production path test does not capture git state before/after the action
   - 07_REPOSITORY_BEFORE.txt and 08_REPOSITORY_AFTER.txt are empty
   - The test verifies capability acquisition but does not log git state

2. Negative test git state not captured
   - Negative tests do not capture git state before/after
   - 10_NEGATIVE_TEST_RAW.txt only reports test pass/fail
   - No direct evidence of "REJECTED + NO MUTATION" via git

3. Production path test simplified
   - The new test (test_real_production_path_existing_execution) only verifies capability acquisition
   - It does NOT perform the full write_repo_file operation
   - This is because write_repo_file_impl requires additional authorization that would consume the lease
   - The test focuses on verifying the acquire_capability_for_existing_execution path with correct parameters

4. No direct instrumentation of authorization → effect flow
   - The test does not have explicit logging at function entry/exit points
   - Evidence is inferred from test assertions and capability acquisition success
   - Cannot directly prove authorize_action() was called

5. No verification of lease consumption
   - The test does not verify that the lease was marked as consumed
   - Only checks that the lease was issued successfully

6. No verification of Named Pipe IPC usage
   - The test assumes AuthorityClient uses Named Pipe
   - No direct proof of IPC mechanism in logs

7. No verification of clean process exit
   - Teardown does not check process exit code
   - Only relies on join() timeout behavior

8. Unicode encoding error in test_lifecycle
   - Fixed by replacing Unicode arrows with ASCII
   - This is a cosmetic fix, not a security issue

9. Pipe busy errors in logs
   - ERROR_PIPE_BUSY (Win32 error 231) appears in logs
   - This is expected behavior due to sequential connection handling
   - Tests eventually pass due to client retry logic

10. No commit created
    - The test only verifies capability acquisition, does not create commit
    - This is intentional but limits the evidence to capability-level verification

CONCLUSION
----------
The evidence is STRONG for:
- Real process separation (PID evidence from OS APIs)
- Authorization enforcement (negative tests pass)
- Bug fix for session_id/episode_id
- Production path capability acquisition (new test)

The evidence is MODERATE for:
- Capability acquisition via acquire_capability_for_existing_execution
- Session/episode ID parameter passing

The evidence is WEAK for:
- Direct instrumentation of authorization calls
- Git state before/after for negative tests
- Verification of lease consumption
- Verification of IPC mechanism

The new test DOES exercise the real production path (acquire_capability_for_existing_execution)
but does NOT perform the full write operation due to lease consumption constraints.
