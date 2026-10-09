# CHAT-ARCH-2026-10-08-192 — RQ21 P1 V4 STATIC SOURCE RECONCILIATION

## PURPOSE

Reconcile the user-supplied v4 detector candidate against RQ21.191's bounded repair contract before a fresh independent static challenge. This record adjudicates only the complete inline source and the claims that accompany it. It does not verify saved bytes, compilation, runtime behavior, or consumer enforcement.

## PROVENANCE

- Repository: jhonf463r/Python.
- Remote main parent observed before writeback: 6b98002517d338a7c6a14765c0be809707db4e54.
- Active predecessor: CHAT-ARCH-2026-10-08-191-rq21-p1-v3-independent-challenge-adjudication.md.
- User-reported deliverable time: approximately 2026-10-08 21:01 America/Bogota.
- User supplied the complete v4 source inline.
- Codex reports v3 input size 14,281 bytes and SHA-256 B6460A3CCB4C830822A75B262CE3F053C589EF847C1EBD69BEFA15AFFF4CD4C6; claims this matched before deriving v4.
- Codex reports v4 path C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v4.ps1, size 16,998 bytes, SHA-256 DECC9BD4C030CB897A29EE1A474DC5F9828473EADF7CE36107758C385A8E2ADD, with two hashing methods agreeing.
- The saved Windows artifact bytes have not been independently read back by this coordinator. Input/output identities above remain actor-reported from the coordinator's perspective.
- The user and Codex report that neither v3 nor v4 was compiled or executed, no token was queried, no DLL/export operation occurred, and no repository/original artifact was changed before this reconciliation.

## PRIMARY ADJUDICATION

**Classification: STATIC_SOURCE_RECONCILIATION_PASS_WITH_BOUNDED_RESIDUALS** for the complete v4 source pasted in the conversation.

The v4 source visibly implements the two repairs required by RQ21.191:
- F1: explicit acquisition states; ATTEMPT_IN_PROGRESS is set before OpenProcessToken; an exception while that state persists changes it to UNRESOLVED; an unresolved acquisition makes cleanup_clean false; only a CONFIRMED_SUCCEEDED non-null token is closed.
- F7: the code checks x64 pointer width and Marshal.SizeOf(TOKEN_MANDATORY_LABEL) == 16 before continuing; it checks requiredLength against a small upper bound before AllocHGlobal and rechecks returnedLength against both allocated and maximum lengths.

Microsoft documents GetTokenInformation's ReturnLength as the number of bytes needed and documents TokenIntegrityLevel as returning TOKEN_MANDATORY_LABEL:
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class
TOKEN_MANDATORY_LABEL contains SID_AND_ATTRIBUTES:
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
Microsoft documents the maximum-sized SID as 68 bytes:
- https://learn.microsoft.com/en-us/windows/win32/secbiomet/general-constants
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_se_sid

The arithmetic 16-byte x64 TOKEN_MANDATORY_LABEL plus a maximum 68-byte SID yields 84 bytes as the proposed upper bound. This is statically plausible for the intended bounded result layout, but the independent challenge must verify that the exact TokenIntegrityLevel output/ReturnLength contract needs no additional padding or bytes and that the proposed bound is correctly derived. This source review is not a runtime validation.

## SOURCE FINDINGS TO PRESERVE FOR THE INDEPENDENT CHALLENGE

### F1 — Acquisition and cleanup state

The main source-level defect from v3 is addressed: acquisition is marked ATTEMPT_IN_PROGRESS before the P/Invoke; it is changed to UNRESOLVED in the catch if the call did not finish the state transition; unresolved acquisition makes cleanup_clean false and cleanup_state UNRESOLVED. A handle is closed only after normal confirmation of successful acquisition and a non-null value.

Residual nuance: the catch explicitly zeros the local token when acquisition is unresolved. If an asynchronous interruption were to occur after the native call wrote a handle but before the managed success state was committed, the handle would not be closed. The report remains fail-closed (cleanup_clean false), and the code avoids closing an unconfirmed handle, but the reviewer should assess whether this is an unavoidable conservative ownership ambiguity or a robustness issue requiring further treatment. No such runtime event was observed.

### F7 — Bounded allocation

The pre-allocation upper bound is enforced before AllocHGlobal; the returned length is also capped. Anomalous size fails closed before SID parsing. The reviewer must challenge the 84-byte derivation against the exact native layout/output contract. If alignment/padding requirements differ, propose only the smallest correct bound; do not widen the cap speculatively.

### F8 — Observed Win32 error is discarded on invalid-length branches

The sizing call captures sizeCallError immediately after GetTokenInformation. If it returns FALSE with ERROR_INSUFFICIENT_BUFFER (122), but requiredLength is below 16 or above 84, the source returns Failed(..., null, ...) from the TokenInformationLength branch. The call's actual observed Win32 error 122 is consequently not preserved in win32_error.

This is not a demonstrated false-pass path: outcome remains INTEGRITY_QUERY_FAILED. It is a low-severity evidence/field-accuracy concern against the standing method of preserving actually observed Win32 errors. The independent challenge should confirm this reading and recommend the minimum fix (preserve 122 while retaining the length-validation failure stage/detail).

## OTHER BOUNDARIES

- The result measures the primary token of the process running this script at one observation point; it does not measure another PID, thread impersonation token, enduring integrity, loadability, export resolution, containment or authorization.
- F2 Add-Type type collision remains controlled only if the actual execution uses a fresh one-shot process and treats absent/unparseable output as STOP/UNKNOWN. Runner enforcement has not been inspected.
- Host/build/UBR/architecture, timestamp, runtime identity, exact script hash, process identity and output freshness must be supplied by and tied to the actual runner evidence envelope.
- Source review does not verify the reported temp-file path/size/hash. Compilation and runtime interop remain UNPROVEN.
- A declared predicate does not prove it is enforced in the runner. The intended detector predicate remains outcome == MEDIUM_CONFIRMED && cleanup_clean == true.
- The frozen Owner authorization in record 182 is separate. No protected operation is authorized by this writeback.

## NINE-AREA RECONCILIATION

1. ABI/layout: x64 16-byte structure check is present; source-level only.
2. Token acquisition: F1 appears implemented; unresolved-state ownership nuance remains.
3. Sizing/data calls: bounded and fail-closed structure appears present; test/error paths require adversarial challenge.
4. Pointer/buffer bounds: length and SID boundaries are retained; not runtime tested.
5. SID parsing/classification: inherited logic remains structurally plausible; no execution evidence.
6. Outcome/error semantics: primary failures remain ineligible; F8 discards observed error 122 on two invalid-length branches.
7. Cleanup/lifetime: close is gated on confirmed acquisition; unresolved acquisition is not reported clean.
8. Output/consumer boundary: actual runner wiring and provenance remain uninspected.
9. Environment: fresh-process/Add-Type/host prerequisites remain untested readiness gates.

## DELTAS

### Knowledge Delta
v4 visibly addresses RQ21.191 F1/F7 in the pasted source. The reported file identity has not been independently checked. One additional source-level evidence concern is that ERROR_INSUFFICIENT_BUFFER can be discarded from win32_error when the associated required length is rejected as anomalous.

### Method Delta
After targeted native-interoperability changes, reconcile the complete source/diff, then challenge that exact source independently. Preserve an actual observed Win32 error even when an additional semantic length validation fails. A correct fail-closed outcome does not make its evidence metadata complete.

### Routing Delta
NEXT ACTOR: SONNET/CLAUDE, independent static challenge of the complete v4 source embedded in the same reviewer prompt. Focus on F1 acquisition/cleanup and interruption paths, F7 exact 84-byte bound, all returned-length and allocation branches, preservation of Win32 error 122 (F8), ABI/bounds, and all nine audit areas. Static only: no compilation/execution, token query, filesystem/temp-file search, file/Git mutation, DLL load, export resolution/invocation, or runner preparation. If the reviewer cannot see the full source in its prompt, stop with SOURCE_UNAVAILABLE_OR_INCOMPLETE and no technical claim.

After the independent challenge, reconcile findings. Only then inspect saved-artifact identity and actual consumer enforcement and reconsider target-bound readiness under the frozen scope. No P1 operation is authorized by this record.

## EXECUTION / AUTHORIZATION BOUNDARY

Record 182's historic Owner authorization remains limited to at most one exact LoadLibraryExW invocation with the frozen path/hash/flags/host/token preconditions, followed only after successful load by lookup of the two exact names. The authorization has not been shown consumed and is not permission to execute now. This candidate is preparation only. No compile/run/token query/DLL/export/runner activity is performed by this record. No retry, alternate host/flags, export invocation, candidate launch or broader experiment is authorized.

END OF RECORD
