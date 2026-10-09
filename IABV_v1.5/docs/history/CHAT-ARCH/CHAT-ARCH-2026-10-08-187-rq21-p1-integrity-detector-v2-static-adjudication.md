# CHAT-ARCH-2026-10-08-187 — RQ21 P1 INTEGRITY DETECTOR V2 STATIC ADJUDICATION

## PURPOSE

Adjudicate the revised unexecuted detector-only artifact v2, including the cleanup-status change identified in record 186. Close only the source-level cleanup reporting gap to the extent visible in the supplied source. Preserve artifact-provenance limits and keep execution/Owner authorization as a separate decision.

## PROVENANCE

- User-pasted Codex deliverable: approximately 2026-10-08 20:14 America/Bogota / 2026-10-09 01:14 UTC.
- Latest remote `main` tip observed before this writeback: `f702b483b71551a1add7a83105453e9c4659c0f4`.
- v1: SHA-256 `80C060A2FDFC969D9C175BB338D10F2AC02A3DA7CF012264628B8792AE112D16`, actor reports two provenance/hash checks matched.
- v2 path reported: `C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v2.ps1`.
- v2 reported size: 11,467 bytes.
- v2 reported SHA-256: `0F24FC0E88B17205512A786683F869E59694CC815C8399502FCD076E8D552A94`; Codex says it was recomputed independently from saved bytes with two hash methods agreeing.
- Codex explicitly reports that v2 was not compiled or executed, no process token was queried, no DLL was loaded, and no repository or original candidate was modified.
- The complete source was included in the user message and reviewed statically here. The coordinator has not directly read the local temp file bytes, independently recomputed the file hash, compiled the source or exercised the interop. The v2 file/hash remain actor-reported, not coordinator-byte-verified.

## STATIC SOURCE REVIEW

**Adjudication: `V2_STATIC_REVIEW_PASS_WITH_RUNTIME_AND_ARTIFACT_IDENTITY_UNPROVEN`.**

The pasted v2 source closes the specific cleanup-reporting gap identified in record 186:

- It retains the primary measurement result object through the `finally` block and returns it after cleanup.
- If a token handle was acquired, it sets `token_close_attempted`, records the `CloseHandle` Boolean return, and immediately captures `Marshal.GetLastWin32Error()` if closure returns false.
- If the call raises a managed/interop exception, it preserves that exception separately in `token_close_exception`.
- Buffer release exceptions are recorded separately in `buffer_release_exception`.
- Cleanup fields do not overwrite `MEDIUM_CONFIRMED`, `INTEGRITY_CONFIRMED_NON_MEDIUM`, or the primary query failure stage/error.

The earlier detector design also remains directionally sound on static inspection: `OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY)` chooses the current process's token; `GetTokenInformation` requests `TokenIntegrityLevel`; and the code checks returned lengths and the SID's location/encoded size within the returned buffer before calling `IsValidSid` and formatting it.

Official API reference alignment:
- Microsoft defines `TokenIntegrityLevel` as returning a `TOKEN_MANDATORY_LABEL` that specifies the token's integrity level: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class
- `TOKEN_MANDATORY_LABEL.Label` is a `SID_AND_ATTRIBUTES` identifying the mandatory integrity level: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
- For `GetTokenInformation`, non-`TokenSource` classes require `TOKEN_QUERY`; success is nonzero and failure is zero, with extended error from `GetLastError`: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- `CloseHandle` returns nonzero on success and zero on failure; `GetLastError` supplies extended error on failure: https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- `IsValidSid` validates SID structure and explicitly has no extended-error result; the candidate does not read `GetLastError` for that validation failure: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-isvalidsid

This review supports source-level plausibility only. It does not establish compiler acceptance, ABI/layout correctness in the running PowerShell/.NET environment, or any token observation.

## REMAINING STATIC REVIEW ITEMS

No additional definite defect was established from the pasted v2 source, but independent adversarial review remains appropriate before any execution:
1. Confirm the `TOKEN_MANDATORY_LABEL` native layout and alignment for the exact x64 process architecture.
2. Challenge the pointer/buffer-boundary checks, returned-length semantics, SID format conversion and every early-return path.
3. Confirm cleanup fields remain coherent when the primary query fails, when token opening fails, and when cleanup itself fails.
4. Confirm no result consumer may treat a query result as execution readiness while ignoring the separate cleanup fields. The integrity observation and cleanup status are distinct; callers must inspect both according to their contract.

A cleanup failure does not retroactively change what the token query observed, but it must not be silently interpreted as fully clean diagnostic completion. No compiler/runtime result exists.

## CURRENT P1 EVIDENCE BOUNDARY

The last real P1 diagnostic emitted `integrity_sid=UNKNOWN` and stopped before the DLL load. Static source review of v1/v2 does not establish the prior process's actual SID. The candidate does not call `LoadLibraryExW` or `GetProcAddress`, and its existence is not evidence of dynamic loadability or export resolution.

## FIRST OPEN EDGE / ROUTING

`v2 source + actor-reported saved-file hash → independent adversarial static review → reconcile source/artifact identity → reassess execution authorization → readiness gate → any allowed protected operation`.

### Next actor

**IA DESTINO = SONNET / CLAUDE**

**CAPABILITY REQUIRED = independent adversarial Win32/.NET interop source audit**

**WHY THIS AI NOW =** the basic correction is now present in the supplied source; the highest-value remaining uncertainty is independent falsification of ABI, pointer bounds, error paths and cleanup semantics before treating the candidate as review-ready.

Review the complete v2 source reproduced in the handoff. Treat its file path, byte size and SHA-256 as Codex-reported unless bytes can be independently obtained. Static review only; do not execute or compile it, query a token, modify any file/Git ref, load the DLL, resolve/invoke exports or launch a candidate. Return concrete issues or a reasoned no-defect-found result, distinguishing definite defects from portability/robustness concerns.

After that challenge, the coordinator must reconcile the authorization boundary separately. The earlier Owner authorization is bounded to the load-only experiment, but record 184/185/186 explicitly leaves a corrected follow-up process subject to authorization reconciliation. Do not infer that this review or artifact creation authorizes a load.

## DELTAS

### Knowledge Delta
The v2 source adds independent fields for token-handle cleanup status/error and buffer-release exceptions without overwriting the primary integrity result. The specific record-186 cleanup reporting gap is closed at source level based on the pasted code. Artifact identity and runtime behavior remain unproven by the coordinator.

### Method Delta
Native interop diagnostics should retain primary measurement results and cleanup results as separate evidence dimensions. Require exact source review plus artifact provenance, and independent static challenge for pointer/ABI-sensitive code before an operational experiment. Do not conflate static plausibility, compilation, execution, observed result and authorization.

### Routing Delta
Sonnet/Claude is now the fit actor for independent falsification of the complete source. Codex need not perform another same-perspective source synthesis before that challenge. No compilation, token query or DLL load is authorized by this writeback.

END OF RECORD
