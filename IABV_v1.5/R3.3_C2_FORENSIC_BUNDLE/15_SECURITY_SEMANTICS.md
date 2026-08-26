R3.3 SECURITY SEMANTICS DIFF
=============================

This document analyzes the security semantic changes introduced by R3.3.

authority_server.py
-------------------
1. Did the authorization contract change?
   NO_SEMANTIC_CHANGE
   The authorization contract (REGISTER_EXECUTION, VERIFY_EXECUTION_CONTEXT, ISSUE_LEASE, CONSUME_LEASE)
   remains unchanged. Only the PID logging was fixed to show the correct boolean value.

2. Did the lease contract change?
   NO_SEMANTIC_CHANGE
   The lease contract (lease_id, execution_id, run_id, TTL) remains unchanged.

3. Did the caller identity change?
   NO_SEMANTIC_CHANGE
   Caller identity is still determined by OS-observed client PID via GetNamedPipeClientProcessId.
   The logging fix only changed how the equality check is displayed, not how identity is determined.

4. Did replay protection change?
   NO_SEMANTIC_CHANGE
   Replay protection (single-use lease consumption) remains unchanged in AuthorityService.

5. Did exactly-once change?
   NO_SEMANTIC_CHANGE
   Exactly-once semantics (lease can only be consumed once) remain unchanged.

6. Did concurrency change?
   NO_SEMANTIC_CHANGE
   The server still handles connections sequentially (one at a time).
   The change from threading.Thread to multiprocessing.Process affects process separation,
   not the concurrency model of the server itself.

7. Did rollback change?
   NO_SEMANTIC_CHANGE
   Rollback mechanisms (if any) remain unchanged.

8. Did Named Pipe transport change?
   NO_SEMANTIC_CHANGE
   Named Pipe transport (\\.\pipe\IABV_Authority) remains unchanged.
   The change is in how the server process is spawned, not in the transport mechanism.

capability_lifecycle.py
----------------------
1. Did the authorization contract change?
   NO_SEMANTIC_CHANGE
   The authorization contract remains unchanged.
   The fix only added missing session_id and episode_id parameters to the issue_lease call,
   which were already part of the contract but were not being passed correctly.

2. Did the lease contract change?
   NO_SEMANTIC_CHANGE
   The lease contract remains unchanged.

3. Did the caller identity change?
   NO_SEMANTIC_CHANGE
   Caller identity is determined by the AuthorityClient connection, unchanged.

4. Did replay protection change?
   NO_SEMANTIC_CHANGE
   Replay protection is enforced by AuthorityService, unchanged.

5. Did exactly-once change?
   NO_SEMANTIC_CHANGE
   Exactly-once semantics are enforced by AuthorityService, unchanged.

6. Did concurrency change?
   NO_SEMANTIC_CHANGE
   No concurrency changes in this module.

7. Did rollback change?
   NO_SEMANTIC_CHANGE
   No rollback changes in this module.

8. Did Named Pipe transport change?
   NO_SEMANTIC_CHANGE
   Named Pipe transport is used via AuthorityClient, unchanged.

SUMMARY
-------
R3.3 introduced NO SEMANTIC CHANGES to the security model.

The changes were:
1. Process separation: Changed from threading.Thread to multiprocessing.Process
   - This improves the security boundary by ensuring real process separation
   - It does not change the authorization contract or identity verification

2. Bug fix: Added session_id and episode_id to issue_lease call
   - This was a bug fix to match the existing contract
   - It does not change the contract itself, only fixes a parameter omission

3. Logging fix: Corrected PID equality check display
   - This only affects logging, not the actual security checks
   - The identity verification logic remains unchanged

CONCLUSION
----------
R3.3 is a PURELY IMPLEMENTATION CHANGE with NO SECURITY SEMANTIC CHANGES.
The security model, authorization contract, and identity verification remain unchanged.
The changes improve the robustness of the security boundary (real process separation)
and fix bugs (missing parameters, misleading logging) without altering semantics.
