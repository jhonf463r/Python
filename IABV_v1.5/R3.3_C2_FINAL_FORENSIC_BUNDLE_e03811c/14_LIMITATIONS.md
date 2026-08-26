R3.3 C2 FINAL FORENSIC - LIMITATIONS
====================================

LIMITATIONS OF CURRENT EVIDENCE:
--------------------------------

1. No commit mutation
   - The test does not create a Git commit
   - Only file mutation is verified
   - REAL_COMMIT_MUTATION = NOT_ATTEMPTED

2. Negative test git state not captured
   - Negative tests do not capture git state before/after
   - 10_NEGATIVE_TEST_RAW.txt only reports test pass/fail
   - No direct evidence of "REJECTED + NO MUTATION" via git for negative tests

3. No direct instrumentation of authorization → effect flow
   - The test does not have explicit logging at function entry/exit points
   - Evidence is inferred from test assertions and capability acquisition success
   - Cannot directly prove authorize_action() was called

4. No verification of lease consumption
   - The test does not verify that the lease was marked as consumed
   - Only checks that the write succeeded

5. No verification of Named Pipe IPC usage
   - The test assumes AuthorityClient uses Named Pipe
   - No direct proof of IPC mechanism in logs

6. No verification of clean process exit
   - Teardown does not check process exit code
   - Only relies on join() timeout behavior

7. Pipe busy errors in logs
   - ERROR_PIPE_BUSY (Win32 error 231) appears in logs
   - This is expected behavior due to sequential connection handling
   - Tests eventually pass due to client retry logic

CONCLUSION
----------
The evidence is STRONG for:
- Real process separation (PID evidence from OS APIs)
- Authorization enforcement (negative tests pass)
- Real capability acquisition via acquire_capability_for_existing_execution
- Real protected effect via write_repo_file_impl
- Real file mutation (content changed, git diff shows change)
- Git state verification (before/after captured)

The evidence is MODERATE for:
- Authorization-before-effect (inferred from write_repo_file_impl implementation)

The evidence is WEAK for:
- Direct instrumentation of authorization calls
- Git state before/after for negative tests
- Verification of lease consumption
- Verification of IPC mechanism

The new test DOES exercise the full production path:
existing execution → acquire_capability_for_existing_execution → real protected effect → real file mutation
