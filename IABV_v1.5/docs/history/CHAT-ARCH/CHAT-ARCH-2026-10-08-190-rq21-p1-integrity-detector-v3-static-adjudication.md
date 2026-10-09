# CHAT-ARCH-2026-10-08-190 — RQ21 P1 INTEGRITY DETECTOR V3 STATIC ADJUDICATION

## PURPOSE

Reconcile the new detector-only v3 artifact after the v2 independent static review and hardening cycle. Adjudicate only the complete source text supplied in the conversation, preserve artifact/runtime evidence boundaries, and route a source-bound independent challenge before any runtime or protected operation.

## PROVENANCE

- User-pasted Codex deliverable time: approximately 2026-10-08 20:36 America/Bogota / 2026-10-09 01:36 UTC.
- Latest remote `main` tip observed immediately before this writeback: `308f0722679bf5cb3f818e185346e4497b1912b5`.
- Active predecessor: record 189, `CHAT-ARCH-2026-10-08-189-rq21-p1-v2-independent-static-review-adjudication.md`; its audit covered the complete v2 inline source only.
- Reported v2 input SHA-256: `0F24FC0E88B17205512A786683F869E59694CC815C8399502FCD076E8D552A94`.
- v3 path reported: `C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v3.ps1`.
- v3 size reported: 14,281 bytes.
- v3 SHA-256 reported by Codex as independently computed from saved bytes by two methods: `B6460A3CCB4C830822A75B262CE3F053C589EF847C1EBD69BEFA15AFFF4CD4C6`.
- Codex states v3 was not compiled or executed, no process token was queried, no DLL was loaded, and no repository/original-candidate file was changed.
- The complete v3 source is included in the user message. Coordinator's source review is based on that pasted text, not an independent read-back of the Windows temporary artifact. File identity, saved size/hash and line-ending/BOM details remain actor-reported.

## STATIC ADJUDICATION

**Classification: `STATIC_REVIEW_PASS_WITH_REPAIRS` for the pasted source; compile/runtime and saved-artifact identity remain UNPROVEN.**

The source incorporates the previous hardening requests:
- On a reported `OpenProcessToken` failure it explicitly zeros the output handle and records acquisition failure; closure is attempted only when acquisition was affirmatively observed as successful and the handle is non-null.
- The primary measurement outcome remains distinct from cleanup details.
- `CloseHandle` success/failure is recorded; the Win32 error is retrieved immediately when it returns false; exceptions are reported separately.
- Buffer-release exceptions are recorded separately.
- `cleanup_clean` is derived independently, and the stated consumer contract requires both `outcome == MEDIUM_CONFIRMED` and `cleanup_clean == true`.
- Request metadata is labelled `token_source_requested` / `token_access_requested`; acquisition observation is separately represented.
- Nullable `win32_error` distinguishes no-applicable-error from an actual reported native error.
- The C# source uses a literal PowerShell here-string.

The token measurement still uses the intended current process token via `OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY)`, asks `GetTokenInformation` for `TokenIntegrityLevel`, checks the returned length and SID placement/encoded length before copying, validates the SID with `IsValidSid`, formats it, and distinguishes exact MEDIUM from another valid integrity SID and query/validation failure.

Microsoft's API contracts align with the broad design: `GetTokenInformation` requires `TOKEN_QUERY` for this information class and reports failure through a zero return plus `GetLastError`; `TOKEN_MANDATORY_LABEL.Label` is a `SID_AND_ATTRIBUTES`; `CloseHandle` returns nonzero on success and zero on failure with extended failure data from `GetLastError`; `IsValidSid` validates the SID and has no extended-error contract:
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-isvalidsid

This is not a compiler, runtime, token observation, or validation of the saved file bytes.

## RESIDUAL SOURCE-LEVEL REPORTING CONCERN

The unexpected-exception path around `OpenProcessToken` is not fully explicit. `tokenOpenSucceeded` begins null and `token_acquisition_observed` begins `NOT_ATTEMPTED`; both are updated only after the call returns normally. If an exception occurs during that P/Invoke, the catch records a generic `Managed/native interop` failure while these fields may still imply that acquisition was not attempted. The `finally` calculation `tokenOpenSucceeded != true` also makes `cleanup_clean` true for a null acquisition state when no cleanup exception was recorded.

That path cannot satisfy the stated consumer gate because the primary outcome becomes `INTEGRITY_QUERY_FAILED`, so this is not a demonstrated fail-open into the DLL load. It is nevertheless a useful robustness/evidence-clarity issue: represent an attempted-but-unresolved acquisition separately from a confirmed failure and do not report cleanup clean where resource ownership/acquisition remains unknown. Preserve the conservative rule that only a confirmed-acquired handle is closed. The independent reviewer should assess whether this warrants a further minimal revision.

## CONSUMER AND EXECUTION BOUNDARY

The supplied consumer contract is:
`outcome == MEDIUM_CONFIRMED && cleanup_clean == true`.

This is the right shape for the detector's result gate, but no consuming runner source has been inspected here and no invocation of the consumer is evidenced. Treat it as a declared contract, not proof it is wired or enforced. The runner must separately check exact host/build/UBR/architecture, exact DLL path/hash/signature, the only allowed flags `0x00000900`, target identity and all frozen scope restrictions before the one permitted loader call. Any missing/error/incomplete/exceptional/unclean result must stop pre-load.

The frozen P1 contract (record 182, Git blob `7184f7822920ee9068a21ab75c3564b10e32ea83`) and previously recorded Owner authorization still bound the operation. This candidate's existence does not authorize a load; no such operation occurred. Current remote routing says the unchanged one-shot authorization may be scope-valid only after the corrected detector, consuming gate and all target preconditions are accepted. There is no authorization for a second load invocation, alternate host/flags, exports, candidate launch or broader experiment.

## NEXT EDGE / ROUTING

`v3 complete inline source → independent source-bound static challenge → reconcile residual acquisition/cleanup semantics → saved artifact byte/hash provenance → verify actual consumer gate → target-bound readiness → one bounded action only if all gates pass under existing authorization`.

**IA DESTINO = SONNET / CLAUDE**

**CAPABILITY REQUIRED = independent adversarial Win32/.NET interop source audit**

**WHY THIS AI NOW =** Codex made the requested change; the remaining high-value uncertainty is independent falsification of the new acquisition-state/cleanup semantics and native layout/pointer/error paths, not another self-review by the artifact author.

Give the reviewer the **entire v3 source inline**, exactly as supplied below in the handoff prompt. The reviewer must audit pasted source only; v3 file path/size/hash remain actor-reported until bytes are actually read. No compile/run, token query, filesystem search, file/Git mutation, DLL load, export resolution/invocation or candidate launch. If source context is missing, stop with `SOURCE_UNAVAILABLE_OR_INCOMPLETE` and make no technical claim.

## DELTAS

### Knowledge Delta
v3 incorporates the primary/cleanup result separation, close-status capture, acquisition metadata and nullable error semantics requested by the v2 audit. A possible remaining reporting ambiguity exists if the acquisition P/Invoke throws before its state variables are updated. Neither v3 artifact bytes nor runtime behavior are independently verified.

### Method Delta
Audit each revised candidate against its previous findings and preserve the source-text / saved-bytes / compile / runtime / consumer / authorization distinctions. A safe-looking predicate in a description is not proof that the consuming runner enforces it.

### Routing Delta
Sonnet/Claude is next for a fresh source-bound static challenge of v3. After adjudication, reconcile whether a minimal source repair is needed, then verify artifact identity and the consuming gate. No protected operation is authorized by this writeback.

END OF RECORD
