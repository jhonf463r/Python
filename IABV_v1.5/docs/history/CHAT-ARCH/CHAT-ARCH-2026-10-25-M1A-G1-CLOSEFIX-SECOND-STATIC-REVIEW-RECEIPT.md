# M1A G1 close-fix — second static review receipt

- **Review ID:** `M1A_G1_CLOSEFIX_SECOND_STATIC_REVIEW_20261025`
- **Date:** 2026-10-25, America/Bogota.
- **Task reviewed:** `M1A_G1_BOUNDED_HANDLE_CLOSE_AND_DETERMINISTIC_CONCURRENCY_FIX_20261025`
- **Reviewer mode:** static inspection of the patch and report fetched directly from the shared Dropbox OUTBOX; no execution of the candidate in this ChatGPT environment.
- **Canonical base observed for this reconciliation:** live `main` = `4ac6045792e93c9a3033ebbfb7a34792dbf94f61`.
- **Candidate base reported by Codex:** `1c86dcb43ceabf149dae3edb8b5f9530536e4ff6`.
- **Disposition:** `STATIC_REVIEW_NOT_ACCEPTED_FOR_INTEGRATION`.

## 1. Evidence intake

The following files were found in the shared Dropbox folder `/IABV-IA-BRIDGE/OUTBOX` and their text content was fetched for review:

| Artifact | Dropbox file ID | Reported/listed size |
|---|---|---:|
| `M1A_G1_CLOSEFIX_RESULT_20261025.md` | `id:5f9kJIcSlJAAAAAAAAADpw` | 3,877 bytes |
| `M1A_G1_CLOSEFIX.patch` | `id:5f9kJIcSlJAAAAAAAAADpQ` | 31,703 bytes |
| `M1A_G1_CLOSEFIX_EVIDENCE_20261025.zip.b64.txt` | `id:5f9kJIcSlJAAAAAAAAADpg` | 16,252 bytes |

Dropbox listing metadata supports the existence of those three entries at the reported paths and sizes. The ZIP is stored as Base64 text, not a binary ZIP. In this review, the full Base64 ZIP was not independently decoded and its internal manifest/member hashes were not independently recalculated. Hash values in the report remain Codex-reported. The patch and result report themselves were fetched and read.

## 2. Codex-reported execution outcome

The report identifies candidate branch `codex/iabv-g1-closefix-20261025` based on `1c86dcb43ceabf149dae3edb8b5f9530536e4ff6`, with local candidate checkout at `C:\Users\faber\AppData\Local\Temp\iabv-closefix-1792965656930-e0da0380`.

Codex reports that the candidate contains only these two new files:
- `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py`
- `IABV_v1.5/tests/test_windows_handle_reader.py`

Codex reports:
- Initial `pytest ... -q` invocation exited 1 because `pytest` was not found on PATH; that invocation did not start the test.
- `python -c "import pytest"` exited 0 with pytest 9.0.3.
- `python -m pytest IABV_v1.5/tests/test_windows_handle_reader.py -q` exited 0 with 15 passed.
- `git diff --check` exited 0.
- Seven tracked `.pyc` files temporarily changed and were restored; final status reportedly contained only the two candidate files as untracked and no staged changes.
- No commit, push, merge, PR, real protected read, IABV runtime, or production transport was run.
- Existing clones were not modified.

These execution/preservation statements are classified as `OWNER_SUPPLIED_CODEX_REPORT`; this ChatGPT review did not run those commands or directly access the Windows checkout.

## 3. Positive findings in the supplied patch

The supplied `OwnedWindowsHandle.close()` implementation now delays `_closed = True` until the native `CloseHandle` call succeeds. On failure, it clears `_closing`, notifies waiters and re-raises, allowing the next `close()` call to retry. The included synthetic test simulates native failure followed by success, verifies the handle's retryable state and verifies idempotence after successful close.

The concurrency test uses a test-only `threading.Condition` subclass to signal when a closing thread reaches its wait. The signal, rather than the passage of 50 ms, coordinates release of the synthetic in-flight operation. A timeout remains a hang guard.

These findings support the narrow claim that the two named source/test changes are promising candidate improvements. They do not establish native Windows behavior or production acceptance.

## 4. Blocking static finding

The same close-failure invariant remains broken in the new module's outer owner, `OpenedTargetCapability.close()`:

```python
with self._condition:
    if self._closed:
        return
    self._close_requested = True
    while self._active_operations:
        self._condition.wait()
    if self._closed:
        return
    self._closed = True
self._handle.close()
```

The code sets `self._closed = True` **before** calling `self._handle.close()`. If that underlying close raises `WindowsHandleReaderError` or another exception, the `OpenedTargetCapability` object stays falsely marked closed. A later `target.close()` returns immediately and will not retry the still-open underlying handle. The wrapper's `_close_requested` also remains true, preventing further consumption; this is safe for access denial, but does not repair cleanup/retry.

The included `test_closing_opened_target_waits_for_active_read_and_closes_once` replaces the underlying handle's `close` with a successful append-only lambda. It does not test a lower-level close failure and a subsequent retry through `OpenedTargetCapability.close()`. The 15 reported passes therefore do not cover this observed invariant.

**Required before accepting this candidate for integration:** correct the wrapper's close state transition so a failed lower-level close does not set the wrapper's terminal `_closed` state, preserve serialization/idempotence for concurrent close callers, and add a synthetic regression test in which the underlying handle close fails once and then succeeds when `target.close()` is retried. Verify that subsequent close after success does not duplicate a native close. This is a newly identified follow-up source task, not a change made in this review.

## 5. Why the authorization organ is not ready

The delivered patch is a candidate source delta consisting of new reader and test files; it was not committed or integrated into `main`. Its own module docstring states that a host must inject a policy-approved `WorkspaceRootCapability` and that the current `AppBootstrap` does not provide one, so production protected reads remain denied. The fetched report likewise says no protected read or runtime was performed.

This task's passing synthetic tests cannot establish:
- that a real, independent trust root and authority/mandate exist;
- that G1, G2 or G3 is established;
- that production composition supplies a policy-approved workspace-root capability;
- that the authorization decision, permission and consumer are bound to the same opened object end-to-end;
- native Windows ABI/kernel semantics, production integration or real transport;
- closure of the eight implementation prerequisites.

No missing trust provider should be invented to force a positive read. Keep the denial fail-closed.

## 6. Result and routing

```text
TASK_ID=M1A_G1_BOUNDED_HANDLE_CLOSE_AND_DETERMINISTIC_CONCURRENCY_FIX_20261025
CODEX_REPORTED_FOCUSED_TESTS=15_PASSED
CHATGPT_TEST_EXECUTION=NOT_RUN
PATCH_FETCHED_FROM_DROPBOX=YES
ZIP_INTERNAL_MANIFEST_RECALCULATION=NOT_RUN
STATIC_REVIEW=BLOCKED_BY_OPENED_TARGET_CLOSE_FAILURE_RETRY_DEFECT
CANDIDATE_INTEGRATION=NOT_ACCEPTED
PRODUCT_CODE_MAIN=UNCHANGED_BY_THIS_TASK
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_ON_ONE_BOUNDED_FOLLOWUP_FIX_OR_KEEP_BLOCKED
```

The next safe technical step is one explicitly authorized, isolated, synthetic-test-only correction for `OpenedTargetCapability.close()` and its retry regression test, followed by another static review. Even after that correction, the whole authorization organ remains unaccepted until the existing policy-approved root/authority composition and remaining prerequisites are established through their own authorized evidence.

This receipt documents the current candidate review only. It does not modify product source, execute tests, authorize runtime/transport, commit/push/merge the product code, or release governance gates.
