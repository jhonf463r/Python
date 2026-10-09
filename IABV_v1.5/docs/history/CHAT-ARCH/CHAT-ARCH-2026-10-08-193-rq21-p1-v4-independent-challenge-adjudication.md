# CHAT-ARCH-2026-10-08-193 — RQ21 P1 V4 INDEPENDENT CHALLENGE ADJUDICATION

## PURPOSE AND PROVENANCE

Reconcile the Sonnet/Claude report supplied by the user for the v4 integrity-detector candidate. This adjudication is limited to the source text reviewed, with an explicit reviewer-input discrepancy.

Repository: jhonf463r/Python.
Predecessor: CHAT-ARCH-2026-10-08-192-rq21-p1-v4-static-source-reconciliation.md.
Report classification: STATIC_REVIEW_PASS_WITH_REPAIRS.
Reported v4 path: C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v4.ps1
Reported size: 16,998 bytes.
Reported SHA-256: DECC9BD4C030CB897A29EE1A474DC5F9828473EADF7CE36107758C385A8E2ADD
These artifact facts remain actor-reported; the coordinator has not independently read the Windows file bytes. The report says it performed no compilation/execution, token query, temp search, file/Git mutation, DLL load/export resolution, or runner preparation.

## PRIMARY ADJUDICATION

Accepted classification: STATIC_REVIEW_PASS_WITH_REPAIRS, qualified by reviewer-input provenance uncertainty.

The reviewer found no definite defect in the intended detector logic. It confirmed F8: two invalid-length branches discard observed Win32 error 122. F1 remains fail-closed with a bounded ownership/leak concern under a theoretical asynchronous interruption. F7's 84-byte ceiling is accepted as a fail-closed bound for the stated x64 target, but the comment claiming no trailing padding is guaranteed is too strong; padding remains not proven as a contract fact.

## F8 — OBSERVED ERROR PRESERVATION

After GetTokenInformation(size) returns false, the source captures ERROR_INSUFFICIENT_BUFFER (122). If requiredLength is below 16 or above 84, the code calls Failed(..., null, ...), losing the observed error.

Adjudication: low-severity evidence-accuracy concern, not a demonstrated false-pass path. outcome remains INTEGRITY_QUERY_FAILED. The minimum correction is to preserve sizeCallError (122) in win32_error on both TokenInformationLength branches while retaining that failure stage and branch-specific detail. Error 122 paired with TokenInformationLength is not authorization to retry.

## N1 — REVIEWER-INPUT DISCREPANCY

The reviewer says two standalone Markdown fence lines appeared inside the C# here-string. They are absent from the v4 source pasted to the coordinator. This is not proof the saved artifact contains them. The earlier review prompt embedded fenced source inside a formatted writing block; nested delimiters may have corrupted the reviewer handoff.

Codex must read only the exact reported v4 path, verify size and SHA-256, and inspect whether the saved file actually contains those fence lines. If identity mismatches, stop and report; do not search for alternative files. If lines exist, remove only the verified stray fence lines in the derived candidate. If absent, do not create a gratuitous fence repair. Never modify v4 in place.

## F1 — ACQUISITION AND CLEANUP

The source uses ATTEMPT_IN_PROGRESS, transitions an interrupted attempt to UNRESOLVED, reports cleanup_clean=false for unresolved state and closes only a confirmed-success non-null token. The reviewer describes a theoretical asynchronous interruption after a native handle is written but before the managed state changes. Discarding an unconfirmed handle is safer than closing an unknown handle; any leak lasts at most until the one-shot process exits. No such runtime event was observed. No F1 source change is required for the minimum next repair.

## F7 — ALLOCATION BOUND

Keep the 84-byte ceiling; do not widen it speculatively. The proposed calculation is 16-byte x64 TOKEN_MANDATORY_LABEL plus a 68-byte maximum SID. However, documentation does not prove the absence of additional trailing padding. Rephrase the comment so 84 is described as the bounded assumed/layout-derived ceiling and preserve fail-closed rejection of larger lengths. Independent review is not runtime validation.

References:
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
- https://learn.microsoft.com/en-us/windows/win32/secbiomet/general-constants
- https://learn.microsoft.com/powershell/module/microsoft.powershell.utility/add-type?view=powershell-7.6

## OTHER BOUNDARIES

- Add-Type type-name collision is controlled only if a fresh one-shot process is enforced and missing/unparseable output fails closed.
- The actual consumer has not been inspected. It must bind output to the launched PID and freshness, and require both the primary outcome and clean cleanup; a declared predicate is not evidence of enforcement.
- Compilation, saved bytes, runtime token state and output-buffer layout remain unproven.
- The result does not prove another PID's token, thread impersonation state, persistence, loadability, export resolution, containment or authorization.
- Cleanup-state granularity and unvalidated SID Attributes are not blockers for the minimum repair.

## DELTAS

### Knowledge Delta
F8 is confirmed; preserve observed error 122 on both invalid-length branches. The reviewer-input fence discrepancy is not proof of corrupt saved artifact bytes; exact-path verification is needed. F1 is fail-closed with a theoretical resource-leak residual. F7 keeps a conservative bound with a comment qualification.

### Method Delta
Do not use nested triple-backtick delimiters when inserting source into a formatted writing block. Use a distinct outer fence length or an actually accessible immutable attachment. Verify exact artifact identity before deriving a candidate. Preserve real observed native errors even if later validation fails. Keep source review, saved bytes, compilation, runtime, consumer enforcement and authorization separate.

### Routing Delta
NEXT ACTOR: CODEX. Verify only the exact v4 path, size and SHA-256; resolve whether the fence lines exist in the saved file; derive a separate v5 with F8 fixed and the F7 comment qualified. Preserve F1; do not compile/run, query tokens, search alternative artifacts, modify v4 in place, mutate Git through Codex, load DLLs, resolve/invoke exports, or prepare a runner. Return complete v5 source, path, size and SHA-256 with two-method agreement. After coordinator reconciliation, route a fresh static challenge of the exact v5 source using safe, non-nested Markdown delimiters.

## AUTHORIZATION BOUNDARY

The historical authorization in record 182 remains conditional and unconsumed. This record grants no execution permission and authorizes no load, export lookup, invocation, retry or candidate launch.

END OF RECORD