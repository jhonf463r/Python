R3.3 C2 FORENSIC REBUILD - SECURITY SEMANTICS
=============================================

PRODUCTION DIFF REVIEW
----------------------

Modified files:
1. capability_lifecycle.py
2. conftest.py
3. test_lifecycle.py

VERIFICATION OF NO REGRESSIONS:
--------------------------------

F10/F11: NOT MODIFIED
- No changes to Ed25519 key handling
- No changes to exactly-once enforcement
- No changes to replay protection
- No changes to concurrency handling
- No changes to atomic rollback
- No changes to Named Pipe protocol
- No changes to Authority DB semantics

FAIL-CLOSED: NOT WEAKENED
- capability_lifecycle.py change only adds missing parameters (session_id, episode_id)
- This strengthens the contract, does not weaken it
- conftest.py change removes ignore_errors=True, which strengthens cleanup
- test_lifecycle.py change is purely cosmetic (Unicode to ASCII)

SESSION/EPISODE ENFORCEMENT: STRENGTHENED
- acquire_capability_for_existing_execution now correctly passes session_id and episode_id
- This ensures the Authority can enforce session/episode binding
- Previously, these parameters were missing, which was a bug

PID ENFORCEMENT: UNCHANGED
- No changes to PID verification logic
- GetNamedPipeClientProcessId still used for OS-observed identity
- Process separation still enforced via multiprocessing.Process

NAMED PIPE TRANSPORT: UNCHANGED
- No changes to Named Pipe implementation
- Pipe name still \\.\pipe\IABV_Authority
- Protocol unchanged

EXACTLY-ONCE: UNCHANGED
- Lease consumption logic unchanged
- AuthorityService.consume_lease still enforces single-use

REPLAY SEMANTICS: UNCHANGED
- Replay protection logic unchanged
- Lease cannot be reused after consumption

CONCLUSION
----------
The changes are PURELY BUG FIXES with NO SECURITY SEMANTIC CHANGES.
The changes STRENGTHEN the security model by:
1. Adding missing session_id/episode_id parameters
2. Removing error hiding in cleanup

No regressions introduced.
