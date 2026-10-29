# M1A G1 — bounded Windows handle-reader repair and synthetic-test receipt

- **TASK_ID:** `M1A_G1_F556_01_02_BOUNDED_REPAIR_AND_CONFORMANCE_20261029`
- **Receipt date:** 2026-10-29 (America/Bogota)
- **Status:** `OWNER_CODEX_REPORTED_LOCAL_REPAIR_AND_FOCUSED_TESTS_PASS; INDEPENDENT_DIFF_REVIEW_PENDING`
- **Evidence source:** Owner-provided Codex receipt in the conversation. This document records the report; it does not independently validate local bytes or command execution.

## Candidate and publication boundary

Codex reports the local worktree `C:\_w\m1a-composition-r3-20261028`, branch `codex/m1a-current-main-fail-closed-20261028`, with HEAD before and after `e1b430956146c4aa0cadc1df2c3df92150b7f7ea`, and base `79ab8c50eaa7518120d5ebed9db4747d395a21cb`. The source/test changes remain uncommitted and unpublished. The receipt says the worktree still contains the exact diff. These local-ref and worktree-state facts are `OWNER_REPORTED` here; they have not been read directly by this ChatGPT session.

The scope is reported as exactly two files, 235 insertions and 3 deletions, with `git diff --check` exit code 0:

| File | Reported final SHA-256 | Reported local Git blob |
|---|---|---|
| `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py` | `59ede3b64cc20bb71fc6e0300572aab174221e8e9d5abd723b6b62efad46690e` | `2facf2a4447d1acff69b1845390355902160dbfa` |
| `IABV_v1.5/tests/test_windows_handle_reader.py` | `ac8b5c101f2cb832debce53586bbffc6dc8272e9cc75e15897479235d56237ff` | `1e72fc6e50a91678964bed38b05b82a9d8a4683f` |

Codex reports initial SHA-256 mismatches were due to CRLF versus LF; normalizing CRLF to LF matched the original Git blobs byte for byte. This reconciliation is retained as `OWNER_REPORTED`, not independently recomputed here.

## Reported source changes

### F-556-01 — directory enumeration cap

When the enumerator observes cap+1, the candidate raises `WindowsHandleReaderError("AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED")` instead of returning a partial directory list. The effective limit of 200 and sorting of a valid in-limit result are reported unchanged.

The report says the added synthetic cases cover three entries with the exact limit, and cap+1 at limit 2. The denial case checks the MCP response has no `entries` field and reveals no names.

### F-556-02 — hard-link count

The candidate now queries `_FILE_STANDARD_INFO` and raises `WindowsHandleReaderError("HARD_LINK_DENIED")` when `standard.NumberOfLinks != 1`, before the target-type check. The report says tests cover a single link proceeding, multiple links being denied, and failure to query `FILE_STANDARD_INFO` failing closed; the tests also check handle closure.

These are reported synthetic/native-call simulations. They do **not** establish complete Windows API semantics, hard-link containment under native Windows, or runtime safety.

## Test and execution evidence

Codex reports this command ran from `IABV_v1.5`:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='C:\_w\m1a-composition-r3-20261028\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_windows_handle_reader.py -q
```

Reported environment/output: Python 3.13.2, pytest 9.0.3, `30 passed in 0.85s`, exit code 0. `git diff --check` is also reported exit 0. These execution facts are `OWNER_CODEX_REPORTED` until the exact diff and receipt are independently reconciled. No tests were run by this ChatGPT session.

## Evidence classification

- `OWNER_REPORTED`: worktree path/branch, HEAD before and after, base, local blob IDs and SHA-256 values, CRLF/LF reconciliation, 2-file diff statistics, `git diff --check`, test command/environment/results, no commit/push/merge, no temporary cleanup, and `C:\Python` not touched.
- `OWNER_CODEX_REPORTED`: F-556-01/F-556-02 changes and synthetic test outcomes.
- `INFERENCE`: the stubbed server path converting the exception to a response without `entries`; must be confirmed against the exact final source/test diff.
- `UNKNOWN`: native Windows enumeration and hard-link semantics in the candidate; unreviewed caller/context behavior beyond the reported synthetic path.
- `NOT_RUN`: native Windows conformance, build, product runtime, live MCP server, protected reads, tests outside `test_windows_handle_reader.py`, broader integration, and CI.
- `HYPOTHESIS`: none asserted.

## Adjudication and next causal edge

The result closes neither finding independently yet. The reported implementation is directionally consistent with the two confirmed static findings, and the focused suite is reported passing, but the final local diff is not available to this reviewer through the current GitHub candidate because no commit or push occurred.

**First open edge:** make the exact two-file unified diff and final test additions available to an independent reviewer without changing/publishing the worktree; then adjudicate the actual changed bytes and their acceptance oracle. The review should specifically verify:
1. cap+1 denial cannot return partial names through any branch, while exactly-cap results remain sorted;
2. `NumberOfLinks` rejection happens before any protected content/list operation, all failure paths close handles, and the single-link pass-through is not accidentally over-broad;
3. the new error reason `AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED` matches the existing error vocabulary/response contract, or is deliberately mapped without leaking names;
4. the tests genuinely distinguish the cap boundary and hard-link/error cleanup, with no accidental bypass from stubs.
Do not repeat the entire R1 review or the targeted test run unchanged. Do not publish source changes merely to make them visible unless separately authorized.

```text
F556_01=FIX_REPORTED_LOCAL; INDEPENDENT_DIFF_REVIEW_PENDING
F556_02=FIX_REPORTED_LOCAL; INDEPENDENT_DIFF_REVIEW_PENDING
TESTS=30_PASSED; OWNER_CODEX_REPORTED
GIT_DIFF_CHECK=PASS; OWNER_CODEX_REPORTED
EXACT_FINAL_SOURCE_FETCHBACK=NOT_DONE
NATIVE_WINDOWS_VALIDATION=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\Python=DO_NOT_TOUCH
```
