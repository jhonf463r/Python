# CHAT-ARCH-2026-10-08-189 — RQ21 P1 V2 INDEPENDENT STATIC REVIEW ADJUDICATION

## PURPOSE

Reconcile the supplied independent static review result for the complete v2 integrity-detector source. Accept its source-level findings without promoting a review of inline text into byte-level verification or runtime evidence; choose minimal repairs and explicitly adjudicate the owner authorization boundary.

## PROVENANCE

- User-pasted reviewer report: time not explicitly included in this result.
- Latest remote `main` tip observed before this writeback: `5481202014878b3c844106453613f354b55e1207`.
- Existing v2 source adjudication: `CHAT-ARCH-2026-10-08-187-rq21-p1-integrity-detector-v2-static-adjudication.md`.
- Source-handoff stop: `CHAT-ARCH-2026-10-08-188-rq21-p1-v2-independent-review-source-handoff-stop.md`.
- Candidate v2 local path as reported by Codex: `C:\Users\faber\AppData\Local\Temp\rq21-p1-integrity-detector-candidate-v2.ps1`.
- Candidate v2 size and SHA-256 as reported by Codex: 11,467 bytes; `0F24FC0E88B17205512A786683F869E59694CC815C8399502FCD076E8D552A94`.
- Review scope: complete v2 source supplied inline in the conversation. The reviewer expressly disclaims access to the actual Windows temporary-file bytes and did not verify the saved candidate's identity. No compile, execution, token query, DLL load or repository mutation was performed.

## ADJUDICATION

**Primary classification: `STATIC_REVIEW_PASS_WITH_REPAIRS`, for supplied source text only.**

No `DEFINITE_DEFECT` was established by the supplied review. It reports structurally consistent `TOKEN_MANDATORY_LABEL` / `SID_AND_ATTRIBUTES` layout and P/Invoke types, expected two-call `GetTokenInformation` handling, bounded pointer/length checks before SID reading, validated SID formatting, and separate cleanup fields preserving the primary integrity result.

This agrees with the relevant Windows API contracts:
- `GetTokenInformation` retrieves the specified token-information class; ordinary classes require `TOKEN_QUERY`, and failure is reported via its Boolean return and `GetLastError`: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- `TokenIntegrityLevel` corresponds to a `TOKEN_MANDATORY_LABEL` result: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class
- `TOKEN_MANDATORY_LABEL` contains `SID_AND_ATTRIBUTES Label`: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_label
- `IsValidSid` validates SID structure and provides no extended-error value: https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-isvalidsid
- `CloseHandle` returns nonzero on success; on failure the caller should capture `GetLastError`: https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- PowerShell `Add-Type` compiles supplied source into an in-memory .NET assembly; type names must remain unique in a session: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/add-type

The reviewer result is an independent source-level challenge **as reported**; it is not coordinator verification of the saved artifact bytes, compiler acceptance, or runtime behavior.

## FINDINGS RECONCILED

| Finding | Coordinator adjudication |
|---|---|
| F1: gate token closure on successful token acquisition | Accept as minimal robustness repair. Track an explicit successful-open state (or zero the out value on failed open) so a failure path cannot cause `CloseHandle` on an unconfirmed handle. |
| F2: cleanup failure does not alter primary `outcome` | Preserve the primary measurement result; additionally provide or enforce a derived cleanup status. The future consumer must gate on `outcome == MEDIUM_CONFIRMED` **and** clean resource handling; cleanup failure must prevent the protected load. |
| F3: two-call sizing race | No blocking repair required. The data-call failure is captured and fails closed; no retry is authorized. |
| F4: requested/static metadata can be misread as observed | Clarify that token source/access are requested operation metadata, not proof of successful token acquisition. Prefer names such as `token_source_requested`, `token_access_requested`, plus an explicit `token_open_succeeded`. |
| F5: zero Win32 error overlaps success and non-Win32 failures | Improve the output contract so “no Win32 error applicable” is distinct from actual error code zero. Preserve stage/outcome as the principal classifier and capture real API errors immediately. |
| F6: expandable C# here-string | Use a literal single-quoted here-string to avoid accidental future PowerShell interpolation. This is preventive hardening, not a current defect in the supplied C# text. |
| F7: PowerShell/Add-Type environment assumptions | Preserve fresh, non-profiled, one-shot PowerShell 7.6.5 as a readiness condition. Do not treat Add-Type source plausibility as runtime evidence; the current task remains non-executing. |
| F8: Windows little-endian and architecture | Accept for the specified Windows target. Do not generalize beyond the Windows environment without a new requirement. |
| F9: overflow boundary, SID revision check, integrity attribute | No additional change required for current bounded SID-recognition objective on this target from the supplied evidence. Preserve as unproven/defence-in-depth rather than inventing a defect. |
| F10: output does not establish consumer readiness or DLL loadability | Important boundary, not a defect in the detector-only candidate. The actual pre-load consumer must be reviewed/formed so all required fields are used and every non-pass/unclean outcome stops. |

## MINIMUM REPAIR CONTRACT

Before this source is reused inside the P1 diagnostic, Codex should produce a separate, unexecuted detector candidate that applies F1, F2, F4, F5 and F6 only. Preserve:
- primary `MEDIUM_CONFIRMED` / `INTEGRITY_CONFIRMED_NON_MEDIUM` / `INTEGRITY_QUERY_FAILED` semantics;
- separate cleanup status, without overwriting the primary observation;
- immediately captured Win32 error where applicable;
- no attempt to infer token integrity from admin membership or group-list enumeration;
- all native handle/buffer lifetime guards.

No new architecture, broad token policy or unneeded telemetry is requested. F3/F8/F9 are not scope-expansion invitations.

The eventual one-shot P1 consumer gate must require:
`outcome == MEDIUM_CONFIRMED` and cleanup status clean, plus the exact host/build/architecture and DLL hash/signature preconditions. Every other result—including query failure, confirmed non-MEDIUM, incomplete evidence, exception or unclean cleanup—must stop before `LoadLibraryExW`. The load call remains separate from symbol lookup: only after a successful load may `GetProcAddress` be called for the two exact names; neither function pointer may ever be invoked.

## OWNER-AUTHORIZATION RECONCILIATION

Record 182 freezes the explicit Human Domain Owner authorization `P1_LOAD_ONLY = AUTORIZADO` for the exact host/file, one `LoadLibraryExW` call with flags `0x00000900), and resolution of both exact symbol names only.

**Adjudication:** the authorized loader operation has not occurred in any reported attempt; every prior run stopped before `LoadLibraryExW`. Therefore the prior authorization is still scope-valid for **at most one** loader call within the frozen target and method once the corrected in-process readiness check passes. This adjudication does not broaden the authorized scope and does not authorize retries after that load call, alternative loader flags, other hosts, API invocation, candidate creation or implementation. The pre-load stops do not count as a DLL-load result.

This is not permission to execute the current v2 candidate as-is. First produce and inspect the minimally corrected detector and its consuming gate. A separate fresh Owner decision is required if any proposed change expands the target, the loader operation/flags, the exported API actions, or the risk/scope frozen in record 182.

## CURRENT EVIDENCE BOUNDARY

- Previous diagnostic: reported `STOP_READINESS_MISMATCH`; `LoadLibraryExW` and `GetProcAddress` were not called.
- v2: actor-reported saved path/size/hash; source reviewed inline; not byte-verified by the coordinator; not compiled or executed.
- Integrity SID of the prior failed process: still unproven.
- DLL loadability and the two dynamic export resolutions: still unobserved.
- Any API function behavior or containment/seven-guarantee property: entirely outside the current evidence.

## NEXT EDGE / ROUTING

**IA DESTINO = CODEX**

**CAPABILITY REQUIRED = exact Windows temp-artifact refinement, native interop and provenance/hash capture**

**WHY THIS AI NOW =** Codex owns the exact temporary artifact and can create a separate byte-hashed candidate without involving IABV source or requiring user-mediated file copying. The remaining work is a bounded source hardening/consumer-gate preparation task, not a runtime experiment.

Deliver the minimally corrected detector candidate as a separate temporary file outside the repository, with complete source, exact path, byte size and SHA-256. Also state the consuming readiness predicate in explicit source or as a small pseudocode contract. Do not compile, execute, query any token, load the DLL, resolve exports, invoke an export, launch a candidate, or modify repository/Git state. Stop after returning the artifact and report.

The coordinator then reviews the supplied source and provenance distinction before preparing any protected P1 run.

## DELTAS

### Knowledge Delta
The independent challenge reports no definite defect in v2's SID recognition logic. It identifies robustness/evidence-clarity repairs and confirms that artifact identity, compilation, runtime token state, and the consumer path remain separate unresolved properties.

### Method Delta
Accept a source-level pass only at the scope actually reviewed. Fold minimal robustness/evidence repairs before composition; require the consumer to gate on primary measurement and cleanup state separately. A reviewer source-handoff failure contributes no technical evidence; the complete inline source resolves that input gap but does not verify local bytes.

### Routing Delta
Codex now owns a minimal, unexecuted hardening pass (F1/F2/F4/F5/F6), not another static review of an unavailable path and not P1 execution. The original owner-authorized single loader call remains unused and can be considered only after corrected source, consuming gate and readiness are reconciled.

END OF RECORD
