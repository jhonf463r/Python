# CHAT-ARCH-2026-10-08-200 — RQ21 P1 CONSUMER CONTRACT DRAFT ADJUDICATION

## PURPOSE AND PROVENANCE

Adjudicate the user-supplied Codex design-only draft for the missing RQ21 P1 consumer, following RQ21.199.

Repository: jhonf463r/Python.
Observed predecessor tip: 3dac496448b8c00a8be8391573a7e8aecda77cce.
Predecessor technical adjudication: CHAT-ARCH-2026-10-08-199-rq21-p1-consumer-not-implemented-adjudication.md.
Input: user-supplied Codex draft, reported 2026-10-08 22:45 America/Bogota.
No local source, runner, process, token or DLL was inspected or executed during this adjudication.

## CLASSIFICATION

**ACCEPT THE ARCHITECTURE AS A SOUND DESIGN DRAFT, WITH BLOCKING CONTRACT QUESTIONS OPEN. NOT IMPLEMENTATION-READY. NO EXECUTION AUTHORIZATION.**

The draft addresses the first open edge from RQ21.199: it proposes one fresh, short-lived, non-elevated PowerShell process which invokes the exact v5 script with the call operator, validates the current invocation's output, and—only after all gates pass—performs the one permitted LoadLibraryExW call itself. The outer launcher may observe this process but must never perform the load.

This is the correct direction for the same-process/PID requirement. The detector's process_id must equal the PID of the very process that calls LoadLibraryExW; a result from a different process is not a substitute for checking the loader process. PID equality is a consistency check, while the actual same-process execution path and fresh in-memory capture establish the causal relationship.

The draft correctly preserves the required conjunction outcome == MEDIUM_CONFIRMED AND cleanup_clean == true; requires separate identity, schema, environment and DLL checks; places GetProcAddress only after a successful load; limits lookups to the two exact names; and prohibits export invocation, FreeLibrary, retry, alternate host/path/flags and candidate launch. These limits match RQ21.182. Its evidence plan and explicit statement that no implementation or runtime work occurred are also accepted.

## CONTRACT QUESTIONS THAT BLOCK IMPLEMENTATION

### 1. Thread impersonation / effective security context

RQ21.195 explicitly limits the v5 result to the queried process primary token; it does not prove the absence or integrity level of a thread impersonation token. The draft correctly identifies this as unresolved.

Recommended fail-closed default for owner adjudication: the thread that performs the detector gate and protected call must not be impersonating. Check this condition at the relevant pre-load boundary; if a thread token is present, the check fails, or the state cannot be established, stop before LoadLibraryExW. Do not silently call RevertToSelf and continue, because that changes security context rather than proving the frozen precondition.

The owner must ratify this restriction or specify an alternative contract. A process-token MEDIUM result alone cannot close this question.

### 2. File identity and time-of-check/time-of-use

Hashing and verifying the signature of the exact System32 path immediately before LoadLibraryExW narrows the race window but does not prove that the image mapped by the loader contains the exact same bytes that were hashed. The frozen RQ21.182 contract specifies path, digest and signature checks but does not specify an atomic mechanism binding verification to the mapped image.

The owner must explicitly choose between:
- accepting and documenting this residual race as a limitation of the narrowly bounded, one-shot load-only probe; or
- requiring a stronger file-identity guarantee, in which case implementation and execution remain blocked until a concrete mechanism is designed and independently reviewed.

Do not state that the loaded image's byte identity is cryptographically bound merely because the preceding path hash matched.

### 3. Exact JSON schema and PowerShell stream policy

The draft gives the correct core predicate and required semantic checks, but the implementation contract must freeze the exact allowed JSON keys and their types against the reviewed v5 source. At minimum, require the exact expected outcome string, Boolean true cleanup_clean, a positive integer process_id equal to the current loader PID, the exact MEDIUM integrity SID, and mutually consistent acquisition/cleanup fields. Do not invent field names or assume unverified fields exist.

Specify which PowerShell output/error/information/warning/verbose/debug/progress streams are captured and how they affect acceptance. Only one complete JSON result from that exact invocation may be accepted. Missing, multiple, malformed, stale, duplicate-key, unexpected, contradictory or unparseable output, invocation errors, or unapproved stream content must stop the operation. Capture the detector result directly for that invocation; never reuse a prior report file as authorization. This schema/stream mapping must be source-aware, not an idealized schema guessed by the implementer.

### 4. Runner identity exists only after a separately reviewed implementation

The requirement to pin the runner path, bytes and hash is accepted, but cannot be satisfied by this design document alone. After a future bounded implementation exists, reconcile its exact source, independently challenge its gate order and fail-closed behavior, then verify its saved artifact identity. Those source/artifact predicates still do not prove compilation, runtime behavior, current target readiness or authorization.

## FROZEN OPERATIONAL BOUNDARY

The eventual runner must preserve RQ21.182 without expansion:
- fresh, short-lived, non-elevated one-shot process;
- host MSI; Windows build 26300, UBR 9550; x64 OS and actual loader process;
- required MEDIUM SID S-1-16-8192, plus the separately adjudicated thread-context condition;
- exact DLL path C:\Windows\System32\processmodel.dll, SHA-256 B684425DEB9013F1741BDFBB9CF1E3D2395C26996111D4C022495367FDFEEBCC, Authenticode Valid and expected Microsoft Windows signer;
- at most one LoadLibraryExW call with the frozen flags 0x00000900;
- only after load success, GetProcAddress for Experimental_CreateProcessInSandbox and Experimental_CreateProcessAsUserInSandbox;
- never invoke either export; no FreeLibrary, retry, alternate path/flags/host, candidate launch or unrelated setup;
- preserve the possibility of DllMain/dependency/teardown side effects and do not characterize this as a containment test.

Maintain the five RQ21.182 result classes: LOAD_AND_BOTH_SYMBOLS_RESOLVED, LOAD_FAILED, LOAD_SUCCEEDED_SYMBOL_MISSING, STOP_READINESS_MISMATCH and UNKNOWN. UNKNOWN is not a pass. The historic authorization is conditional and unconsumed; this record consumes, extends or replaces none of it.

## NEXT OPEN EDGE AND ROUTING

First, Human Domain Owner adjudicates the thread-impersonation rule and the acceptable TOCTOU boundary. The recommended conservative default is no thread impersonation, stop if absent-state cannot be proved, and explicit disclosure of the existing path-check race unless the owner requires a stronger binding.

Next, the coordinator freezes the exact v5 JSON-field/type map and stream acceptance policy against the reviewed source, then issues a separate bounded implementation contract. Only after that may a separate source-creation task occur. Any implementation must be statically reconciled and independently challenged before artifact identity, target readiness and a later separately adjudicated execution gate.

Until those edges close: no source creation, code change, compilation, script execution, token query, DLL load, export lookup/invocation, candidate launch or repository implementation change.

## DELTAS

Knowledge Delta
The missing consumer now has a structurally coherent same-process design draft, but two security-contract decisions remain open: thread impersonation and the accepted file-verification race. Exact JSON schema and PowerShell stream handling must also be frozen against the actual v5 output, not guessed.

Method Delta
A sound high-level design is not an implementation contract or readiness proof. Bind measurement and action to one OS process, separate primary-process-token evidence from thread security context, and state precisely what file-identity guarantees the loader path does and does not provide. Strict output parsing needs source-derived field/type and stream semantics.

Routing Delta
NEXT: Human Domain Owner resolves the two contract decisions; coordinator then freezes the source-specific JSON/stream contract. No Codex implementation or runtime task yet.

## AUTHORIZATION BOUNDARY

This record adjudicates a design report only. It does not implement a consumer, permit compilation/execution/token query, authorize any DLL/export operation, or consume the bounded Owner authorization in RQ21.182. No protected operation occurred in this review.

END OF RECORD
