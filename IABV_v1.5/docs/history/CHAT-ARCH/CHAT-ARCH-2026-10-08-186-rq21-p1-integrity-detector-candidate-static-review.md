# CHAT-ARCH-2026-10-08-186 — RQ21 P1 INTEGRITY-DETECTOR CANDIDATE STATIC REVIEW

## PURPOSE

Adjudicate the unexecuted detector-only PowerShell/C# candidate reported by Codex. Determine whether its static design is plausible, preserve known gaps, and define a safe next decision without conflating the candidate's existence with runtime verification or permission to resume P1.

## PROVENANCE

- User-pasted Codex deliverable: approximately 2026-10-08 20:05 America/Bogota / 2026-10-09 01:05 UTC.
- Latest remote main tip observed before this writeback: `8b32b489a153f3ec98a8da69d2f2a51583c83a18`.
- Candidate path reported by Codex: `C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate.ps1`.
- Candidate SHA-256 reported by Codex: `80C060A2FDFC969D9C175BB338D10F2AC02A3DA7CF012264628B8792AE112D16`.
- Candidate size reported by Codex: 8,254 bytes.
- Codex states the candidate was saved and hashed, but not executed or compiled.
- Original diagnostic script hash `34BF0FAE29712A2340C76B7CBFB53D872A728E2E47B993DFCEEC69711A8BF7E9` is reported as independently recomputed by Codex and matching the earlier digest.
- The complete candidate source was included in the user's message and statically reviewed from that pasted text. The coordinator has not read the temporary candidate bytes or independently recomputed its file hash. The candidate path/hash therefore remain actor-reported.

## CONTRACTUAL CONTEXT

RQ21 P1's canonical frozen owner authorization remains record 182:
`CHAT-ARCH-2026-10-08-182-rq21-p1-load-only-owner-authorization-and-experiment-contract.md`, Git blob `7184f7822920ee9068a21ab75c3564b10e32ea83`.

The prior real diagnostic stopped before loading because its integrity detector emitted `UNKNOWN`. Record 185 identified, from Codex-reported static inspection, that the original script searched `WindowsIdentity.GetCurrent().Groups` for an `S-1-16-*` SID instead of directly querying `TokenIntegrityLevel`.

The new candidate is explicitly detector-only. It does not load the DLL or call either experimental export. It has not been compiled or run.

## STATIC REVIEW OF THE PASTED SOURCE

**Adjudication: `PROVISIONAL_STATIC_PLAUSIBILITY_WITH_CLEANUP_EVIDENCE_GAP`.**

The main design is directionally consistent with the Win32 token API contract:

- `OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, ...)` makes the source token the current diagnostic process's token.
- `GetTokenInformation(TokenIntegrityLevel, ...)` uses a two-call sizing/query pattern and captures the Win32 error immediately on the data-query failure path.
- The native `TOKEN_MANDATORY_LABEL` layout is modeled as a SID pointer plus attributes, corresponding to its `SID_AND_ATTRIBUTES Label` member.
- The code rejects inadequate/oversized returned lengths, checks the SID pointer is within the returned buffer after the label header, checks the SID's encoded length before reading it, and calls `IsValidSid` before formatting.
- It distinguishes an exact `S-1-16-8192` result, another valid SID, and a query/validation failure. It does not infer integrity from administrator membership or `WindowsIdentity.Groups`.

Microsoft API references:
- `GetTokenInformation` documents the token-information query, `TOKEN_QUERY` access requirement for ordinary information classes, returned buffer length, Boolean success/failure and `GetLastError`: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- `TOKEN_MANDATORY_LABEL` contains a `SID_AND_ATTRIBUTES` member specifying the token's mandatory integrity level: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
- `OpenProcessToken` opens a process's access token and documents closing the returned token handle with `CloseHandle`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocesstoken
- `IsValidSid` validates SID structure; its documentation says not to rely on `GetLastError` for its failure result. The candidate correctly routes this into a local validation failure rather than reading a Win32 last error for that call: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-isvalidsid

This is a coordinator static review of the pasted source, not compiler validation, execution, or byte-for-byte verification of the saved candidate artifact.

## KNOWN GAP AND REQUIRED REPAIR

The `finally` block attempts `CloseHandle(token)` but ignores its Boolean return and does not record the immediate error if closure fails. The candidate's returned result therefore cannot say whether native handle cleanup succeeded. Because the diagnostic is intended to be short-lived, process teardown ultimately reclaims process-owned handles, but the report should still preserve whether explicit cleanup succeeded.

Before treating a corrected detector as a review-ready artifact, minimally capture the `CloseHandle` result and its immediate last-error value into a separate cleanup-status field without overwriting the primary integrity-query result. Ensure the reporting flow can represent cleanup failure on both success and failure return paths. Keep buffer release and token-handle cleanup on all paths. Do not make a cleanup failure silently look like full diagnostic success.

No other defect has been demonstrated from the pasted source. That is not a claim that all possible interop defects are absent: the candidate has never been compiled or executed, and the source bytes on disk were not read back by the coordinator.

## ADJUDICATION

The candidate is **not approved for execution on this evidence alone**. The source is statically plausible as a token-integrity detector, with cleanup reporting to repair. Compilation/interop behavior remains unverified. It does not establish the old PID's actual token SID and does not retroactively change the prior `STOP_READINESS_MISMATCH`.

No `GetTokenInformation` call was performed by the coordinator. The candidate was not executed or compiled during this review; no token was queried; no DLL was loaded; no export was resolved or invoked; no candidate process was launched; no repository source or Git worktree was changed by Codex for this deliverable.

## FIRST OPEN EDGE

`candidate's static API/layout plausibility → cleanup-result reporting correction → independent candidate byte/hash read-back → execution/authorization boundary reconciliation`.

### Next actor

**IA DESTINO = CODEX**

**CAPABILITY REQUIRED = exact Windows temporary-artifact refinement and provenance/hash capture**

**WHY THIS AI NOW =** Codex owns the reported Windows temp artifact and can preserve a byte-verifiable candidate without involving the IABV repo or running it.

Codex's next bounded deliverable is to revise the candidate **as a separate temporary file only** to record `CloseHandle` success/failure and any immediate error in a cleanup field, preserving the primary `outcome`. Hash the saved bytes and return the complete revised source plus path/size/hash. Do not execute, compile, or query a token. Do not modify the original diagnostic, repository files, Git refs, or the frozen contract.

After that, the coordinator can independently reconcile the returned source/artifact identity and the owner-authorization question. No dynamic load attempt is authorized by this record.

## DELTAS

### Knowledge Delta
A direct process-token query is a suitable measurement design for the missing integrity property. The pasted candidate's API signatures and buffer/SID checks look structurally plausible; the actual binary/source artifact identity is actor-reported, and compile/runtime behavior is unproven. Explicit handle-close status is not currently represented in the result.

### Method Delta
For native diagnostic proposals, review the source's API contract and pointer/length invariants, then separately retain cleanup success/error. A complete static candidate and a matching hash do not substitute for compile/runtime evidence, and no protected operation may be inferred as authorized by an unexecuted candidate.

### Routing Delta
Codex remains the fit actor for the minimal temp-artifact cleanup-reporting refinement. No independent runtime actor should be used yet; first preserve the exact revised source and its provenance without executing it. The later loader authorization must be reconciled separately.

END OF RECORD
