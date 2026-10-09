# CHAT-ARCH-2026-10-08-184 — RQ21 P1 INTEGRITY-GUARD STOP AND DETECTOR READINESS

## PURPOSE

Reconcile the first diagnostic process created after the canonical RQ21 P1 contract was retrieved and verified. Preserve the correct pre-load stop and identify the next discriminating action without misclassifying it as a DLL/API failure.

## PROVENANCE

- User-pasted Codex result: approximately 2026-10-08 19:51 America/Bogota / 2026-10-09 00:51 UTC.
- Remote `main` read-back before this writeback: `2a7b02c2960eaca231265bebe14eb6b86e1280be`.
- Canonical experiment contract: `CHAT-ARCH-2026-10-08-182-rq21-p1-load-only-owner-authorization-and-experiment-contract.md`.
- Contract blob SHA: `7184f7822920ee9068a21ab75c3564b10e32ea83`; direct remote GitHub fetch returns that blob SHA. Codex reports that the fetched bytes independently hash to this Git blob.
- The prior RQ21.183 reconciliation had already established that the contract exists remotely and the preceding Codex run did not execute anything.

## OBSERVATION — ACTOR-REPORTED DIAGNOSTIC RESULT

Codex reports that it read the immutable contract at commit `384db92d380ddb49e5f437e2ada35b2af677a75d`, verified the expected blob, checked the scope and created one non-elevated PowerShell 7.6.5 diagnostic process.

Reported preflight:
- Host `MSI`; Windows `10.0.26300.9550`; OS/process architecture `X64`.
- Exact DLL path, SHA-256 `B684425DEB9013F1741BDFBB9CF1E3D2395C26996111D4C022495367FDFEEBCC`, Authenticode `Valid`, Microsoft Windows signer: reported checks passed in the diagnostic process.
- `is_administrator=false`.
- `integrity_sid=UNKNOWN`; `medium_integrity=false`; `all_checks_passed=false`.
- Process PID `19072`; exit code `20`.
- Diagnostic script: `C:\Users\faber\AppData\Local\Temp\rq21-p1-load-1791507015374-25122.ps1`; actor-reported SHA-256 `34BF0FAE29712A2340C76B7CBFB53D872A728E2E47B993DFCEEC69711A8BF7E9`.
- Stdout JSONL actor-reported SHA-256 `29A18379EBA84F6885EEB63F0B726CD5B96BCF892ACD2A75A380F94E3885FE82`.
- Evidence report actor-reported SHA-256 `B71FBA4D12AEB2A0F7BBCC98BA5420072A68ABDE25094D32A863DA1A28121FE4`.
- Codex reports no DLL load, no export resolution or invocation, no candidate launch, no retry and no IABV/Git modification.

These local temporary artifact bytes have not been independently read back by the coordinator; their paths and digests remain actor-reported.

## ADJUDICATION

**Primary classification: `STOP_READINESS_MISMATCH`.**

This is a correct fail-closed result under the frozen contract. The contract requires the diagnostic child itself to verify integrity SID `S-1-16-8192` (MEDIUM) before the sole permitted loader call. `UNKNOWN` cannot satisfy that precondition.

The earlier observation of MEDIUM integrity in a separate console does not establish the security token of PID `19072` and must not be substituted. Likewise, `is_administrator=false` does not prove MEDIUM integrity.

This is **not** `LOAD_FAILED`, `LOAD_SUCCEEDED_SYMBOL_MISSING`, or evidence of an absent/defective export: `LoadLibraryExW` and `GetProcAddress` were not called. Dynamic loadability and symbol resolution remain unobserved.

## CURRENT EPISTEMIC BOUNDARY

- **FACT from the supplied output:** the diagnostic emitted `integrity_sid=UNKNOWN` and stopped before loading.
- **ACTOR-REPORTED:** the process/environment, DLL identity/signature, script/report hashes and retrieval/hash-validation details above.
- **INFERENCE:** either the integrity-query implementation failed to obtain/interpret the token integrity SID, or the process context genuinely did not satisfy the contract. The available output does not distinguish these explanations.
- **UNPROVEN:** the integrity token of PID `19072` itself; the root cause in the detector; DLL loadability; both dynamic symbol resolutions; API operation and all containment/seven-guarantee claims.

## FIRST OPEN EDGE

Determine why the exact diagnostic script maps integrity to `UNKNOWN`, using **static inspection only** of the reported script bytes and the relevant guard/query logic.

### Next discriminating action

**IA DESTINO = CODEX**

**CAPABILITY REQUIRED = exact-artifact, non-mutating PowerShell/token-integrity detector inspection**

**WHY THIS AI NOW =** the script and its temporary artifacts are in Codex's Windows execution environment, and the open question is the detector's concrete implementation and error path, not general Windows guidance.

Codex should:
1. Read the exact reported script path and compute its actual SHA-256 from bytes; compare with the actor-reported `34BF...` digest.
2. Trace only how the script obtains, parses, and classifies the process integrity SID, including any caught exception, native return status, buffer/structure interpretation, output parsing or null/empty handling that can yield `UNKNOWN`.
3. Report the minimal evidence-backed root-cause hypothesis and exact relevant source lines/expressions; distinguish proven code path from speculation.
4. Make no file/source/Git changes; do not execute the script, query/alter system security settings, call `LoadLibraryExW` or `GetProcAddress`, load the DLL, invoke exports, launch a candidate, or run a new experiment.
5. If the script is absent or its bytes do not match the reported digest, stop and report the provenance mismatch rather than recreating it.

Do not ask the user to repeat manual token checks. Do not bypass the MEDIUM-integrity guard or reuse a token observation from another process.

## EXECUTION-AUTHORIZATION BOUNDARY

The previous run did not reach the sole permitted `LoadLibraryExW` operation. This record does **not** authorize a load attempt or broaden the existing Owner authorization. After static detector diagnosis, reconcile the exact cause and decide whether a minimal correction preserves the frozen contract or requires an explicit Owner decision before any subsequent load. No dynamic retry is authorized by this writeback.

## DELTAS

### Knowledge Delta
A real one-process attempt now exists, but it is a fail-closed preflight stop. The integrity detector's `UNKNOWN` result is not evidence that the token was non-MEDIUM and not evidence that the DLL load failed. The actual token state and cause of the `UNKNOWN` remain unresolved.

### Method Delta
When a guarded experiment stops because a required identity/token observation is `UNKNOWN`, preserve the stop and inspect the exact detector implementation before rerunning. Do not replace an in-process precondition with an observation from another process; distinguish sensor/detector failure from target-state mismatch.

### Routing Delta
Codex remains the fit actor for read-only inspection of the exact temporary Windows script. No second experimenter or broad platform research is needed yet. Recompute routing only after the detector cause and authorization boundary are reconciled.

END OF RECORD
