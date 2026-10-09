# CHAT-ARCH-2026-10-08-191 — RQ21 P1 V3 INDEPENDENT STATIC CHALLENGE ADJUDICATION

## PURPOSE

Reconcile the user-supplied Sonnet/Claude independent static review of the complete inline v3 integrity detector. Preserve the distinction between reviewer claims, coordinator adjudication, saved-artifact identity, runtime evidence, consumer wiring, and the frozen owner authorization.

## PROVENANCE

- Repository: jhonf463r/Python.
- Remote main parent observed immediately before this writeback: 39289251f2bcfa8077b72cf9eae43a7aa8abdbff.
- Active predecessor: CHAT-ARCH-2026-10-08-190-rq21-p1-integrity-detector-v3-static-adjudication.md.
- Input: the complete Sonnet/Claude static-review report pasted by the user in this conversation.
- Review subject: the complete v3 source already embedded inline in the preceding handoff; not the Windows temp-file bytes.
- Codex-reported candidate path: C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v3.ps1.
- Codex-reported size: 14,281 bytes.
- Codex-reported SHA-256: B6460A3CCB4C830822A75B262CE3F053C589EF847C1EBD69BEFA15AFFF4CD4C6.
- Neither candidate bytes nor hash have been independently read back by this coordinator. No compile/runtime result is supplied by the reviewer.

## PRIMARY ADJUDICATION

**Accepted classification: STATIC_REVIEW_PASS_WITH_REPAIRS for the complete inline source only.**

The reviewer reports no DEFINITE_DEFECT in ABI/layout, token measurement, sizing/data-call structure, SID bounds/formatting, primary outcome semantics, or cleanup reporting on ordinary paths. The report is a static review, not a compile result, runtime observation, verified artifact identity, or proof of consumer enforcement.

The review's declared predicate is:

    outcome == MEDIUM_CONFIRMED && cleanup_clean == true

The source appears to fail closed under this predicate because query/acquisition failures retain INTEGRITY_QUERY_FAILED. This does not establish that an actual runner uses the predicate or rejects missing, stale, malformed, or untrusted output.

## FINDINGS AND COORDINATOR RECONCILIATION

### F1 — Acquisition state and cleanup_clean

Reviewer classification: ROBUSTNESS_CONCERN, low.

Accept as a required minimal reporting repair. Current initial state NOT_ATTEMPTED/null is not updated until OpenProcessToken returns normally. On an exception while the call is being attempted, the record can remain ambiguous; the finally formula can treat any not-confirmed-success state as clean. A synchronous load/entry-point failure ordinarily acquires no token, but code must not collapse “no resource was acquired” and “acquisition result unresolved.” The reviewer also describes a narrow asynchronous interruption window where a handle could have been obtained before the managed success state is recorded.

Minimal repair contract:
- Set acquisition state to ATTEMPT_IN_PROGRESS immediately before the P/Invoke.
- Replace it with CONFIRMED_FAILED or CONFIRMED_SUCCEEDED only after a normal return and the relevant handle check.
- Preserve the rule that only an affirmatively confirmed non-null token handle is closed; never close an unconfirmed handle merely to simplify cleanup.
- If acquisition remains unresolved, cleanup_clean must be false or null, not true.
- Keep the primary outcome separate; an unresolved path must not produce MEDIUM_CONFIRMED.

This is not an observed bypass of the stated combined predicate. It is a source-level evidence-accuracy gap that the protocol explicitly requires us to preserve and resolve.

### F2 — Reused Add-Type result type

Reviewer classification: ROBUSTNESS_CONCERN, low.

Accept as an environment/readiness constraint, not a required source change for the frozen one-shot design. PowerShell type names persist in a session and a duplicate definition can prevent JSON output. The existing P1 contract requires a fresh short-lived process. The actual runner must enforce a fresh process/session and treat missing or unparsable output as STOP/UNKNOWN. If any workflow intends same-session reuse, the type must be versioned or otherwise made unique first.

Microsoft reference: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/add-type?view=powershell-7.6

### F3 — Ambiguous sizing-failure detail

Reviewer classification: informational ROBUSTNESS_CONCERN.

Do not widen the immediate repair unless Codex can separate the detail strings at negligible scope. Existing stage/outcome and nullable win32_error still separate the broad cases; no false MEDIUM result is demonstrated. Keep as optional clarity, not a blocker.

### F4 — Null/boolean field overload

Reviewer classification: informational ROBUSTNESS_CONCERN.

No separate source repair required for this slice. Any consumer must gate on the canonical outcome and cleanup status; it must not accept medium_integrity alone. The runner must treat absent/malformed output, unresolved acquisition, exceptions and any non-pass result as STOP/UNKNOWN.

### F5 — Host/bitness/timestamp are not emitted by the detector

Reviewer classification: ENVIRONMENT_ASSUMPTION.

Keep target identity and freshness in the runner-owned evidence envelope, as required by frozen record 182. Immediately bind the output to the fresh one-shot child PID, execution times, PowerShell/runtime identity, exact script/source hash and verified host/build/UBR/architecture. Do not expand the detector-only script to replace the runner's responsibility. Output without trustworthy provenance is not admissible.

### F6 — Add-Type execution dependencies

Reviewer classification: ENVIRONMENT_ASSUMPTION.

Compilation has not been tested. Keep execution disabled during this repair stage. The future runner must satisfy the frozen non-elevated, fresh-process and target-specific prerequisites; it must fail closed on language-mode/policy/compiler failure and missing JSON. Do not infer compilation or runtime correctness from this review.

### F7 — Unbounded requiredLength allocation

Reviewer classification: ROBUSTNESS_CONCERN, informational in the review.

Accept a narrowly bounded allocation guard as an additional hardening item. The current checked uint-to-int conversion prevents values above Int32.MaxValue but can still attempt a very large allocation for smaller anomalous values. Given the frozen x64 target, the size must be bounded before AllocHGlobal by the maximum valid TOKEN_MANDATORY_LABEL plus maximum valid SID size, with any required alignment/padding explicitly accounted for. Microsoft documents SECURITY_MAX_SID_SIZE as 68 bytes, while TOKEN_MANDATORY_LABEL is SID_AND_ATTRIBUTES; the x64 structure size used by this source is 16 bytes. Use 84 bytes only if the implementation's exact output-buffer layout/length contract has been confirmed; otherwise choose a documented, still-small bound that safely accounts for the layout. Oversize or inconsistent lengths fail closed before allocation.

References:
- https://learn.microsoft.com/en-us/windows/win32/secbiomet/general-constants
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_se_sid
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label

### F8 — Evidence boundary

Accept as NOT_PROVEN rather than a code defect. The detector can establish only the integrity SID queried for its own process primary token at that observation point and the cleanup fields it actually observed. It does not establish another PID's token, a thread impersonation token, enduring integrity, elevation/privileges/AppContainer state, DLL loadability, export resolution, containment, or authorization. The actual runner has not been inspected.

## NINE-AREA SUMMARY

1. ABI/layout: PASS for the x64 source-level review; no runtime ABI validation.
2. Token acquisition: PASS with F1 reporting repair.
3. Sizing/data calls: structurally plausible; add F7 upper bound; F3 detail clarity is optional.
4. Pointer/buffer bounds: PASS as statically reviewed; no runtime behavior established.
5. SID parsing/classification: PASS as statically reviewed; returned Attributes are not independently validated and remain a residual defensive detail, not a demonstrated defect.
6. Outcome/error semantics: PASS with the requirement that consumer gates outcome, not the boolean alone.
7. Cleanup/lifetime: PASS on ordinary paths, with unresolved acquisition state requiring F1 repair.
8. Output/consumer boundary: bounded; actual runner wiring and provenance remain uninspected.
9. Environment: assumptions only; no compilation or execution result.

## DELTAS

### Knowledge Delta
The independent review found no definite defect in the inline detector's core MEDIUM SID recognition. It identified two targeted hardening items for reconciliation: make attempted/unresolved token acquisition explicit and prevent anomalously large allocation requests before AllocHGlobal. Add-Type type-name collision is controlled by the fresh one-shot process contract; runner provenance fields remain runner-owned.

### Method Delta
Preserve reviewer classifications but adjudicate against the standing protocol: source review is not byte verification, compile, runtime observation or consumer enforcement. Do not promote a clean primary result or a declared predicate without the full evidence path. Repair only the two bounded items, keep source/runner/authorization separate, and re-review the exact revised source if material.

### Routing Delta
NEXT ACTOR: CODEX for a separate v4 detector-only candidate applying F1 plus the F7 bounded-allocation guard. Include complete source, path, size and reported SHA-256; do not compile or execute it, query a token, search or mutate repository artifacts, load the DLL, resolve exports, or prepare/run a consumer runner. F2/F5/F6 remain hard runner-readiness obligations; F3 is optional clarity. Because F1/F7 change gate-relevant acquisition/cleanup and buffer-allocation logic, the exact complete v4 source must then receive coordinator source/diff reconciliation and a new independent static challenge before artifact identity, actual consumer enforcement and target readiness are reconsidered. No protected operation is authorized by this record.

## EXECUTION / AUTHORIZATION BOUNDARY

Frozen contract and owner authorization remain in record 182. The historical authorization is for at most one exact LoadLibraryExW call under the frozen path/hash/flags/host/token preconditions, followed only on successful load by lookup of the two exact names, without invoking either address. It is not permission to execute now. The detector has not been compiled or run here; no token was queried; no DLL/export operation was performed. The single operation remains unconsumed and cannot be attempted until revised source, artifact provenance, actual runner gate and all target-bound preconditions are separately accepted. No retry, alternate host/flags, export invocation or candidate launch is authorized.

END OF RECORD
