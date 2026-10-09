# CHAT-ARCH-2026-10-08-182 — RQ21 P1 LOAD-ONLY OWNER AUTHORIZATION AND EXPERIMENT CONTRACT

## PURPOSE

Record the Human Domain Owner's explicit authorization and freeze the minimal P1 experiment contract after RQ21 P0 static export presence was adjudicated PASS in record 181. This record authorizes only a local DLL load/symbol-resolution diagnostic, not the exported API calls or the seven-guarantee candidate-validation experiment.

## PROVENANCE / AUTHORIZATION

Repository: `jhonf463r/Python`.
Verified remote `main` immediately before writeback: `42df33007c6796b095909107b12447228702060c`.
Pinned executable baseline: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`.

Explicit Human Domain Owner message: `P1_LOAD_ONLY = AUTORIZADO` (2026-10-08, America/Bogota). Authorization is bounded by the prior discussion: load the identified DLL and resolve both names only; do not invoke either export or run a candidate.

P0 evidence (reported by Codex, record 181):
- Target: `MSI`, Windows 11 build `10.0.26300.9550`, x64, MEDIUM integrity `S-1-16-8192`.
- DLL: `C:\Windows\System32\processmodel.dll`.
- SHA-256: `B684425DEB9013F1741BDFBB9CF1E3D2395C26996111D4C022495367FDFEEBCC`.
- Authenticode: `Valid`, Microsoft Windows signer.
- Static `dumpbin /EXPORTS` reports both `Experimental_CreateProcessInSandbox` and `Experimental_CreateProcessAsUserInSandbox` present (exit 0).

## FROZEN EXPERIMENT CONTRACT

### Objective

On the exact P0 target, determine whether the file can be loaded by a fresh short-lived non-elevated process and whether `GetProcAddress` resolves each of the two exact export names. Do not infer that the functions work or that the API is a viable containment substrate.

### Readiness / preconditions

Immediately before the test, the diagnostic child process must verify:
1. Computer name `MSI`; Windows current build `26300`, UBR `9550`; OS and process architecture x64.
2. Current integrity SID `S-1-16-8192` (MEDIUM). Any elevation, mismatch or unknown result must stop before DLL loading.
3. DLL exists at the exact full path and SHA-256 matches the P0 value above; Authenticode reports `Valid` and expected Microsoft Windows signer. Any mismatch must stop before loading.
4. No network operations, installation, repository checkout/write, elevation or other setup work.

The executor must use a fresh one-shot process without user/profile initialization where possible. Save the exact diagnostic script/tool identity and hash before running.

### Single permitted operation

In the child process, call `LoadLibraryExW` once with the exact fully qualified DLL path and flags `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32` (`0x00000900`). Immediately record success/failure and `GetLastError` if it returns NULL.

Only if load succeeds, call `GetProcAddress` for the two exact ASCII export names. Do not call through either returned address. Capture for each symbol whether the pointer is NULL, and capture `GetLastError` immediately for any NULL result. Do not execute any export.

Do not explicitly call `FreeLibrary`; terminate the diagnostic child after results are captured. Record that process teardown may execute DLL detach handling. If the loader flags are unsupported, do not retry with broader/default search paths; stop and report the exact error.

### Side-effect / threat boundary

Loading a DLL can execute its module initialization entry point (`DllMain`) and may run dependency initialization. The target is reported as a validly signed Microsoft Windows component, but signature validity does not make initialization side-effect-free. This experiment is deliberately limited to the exact Windows component, exact path/hash, non-elevated medium token and one-shot process. It is **not a containment test**, and there is no claim that the current IABV substrate confines initialization side effects. If any unanticipated prompt, elevation request, environment mismatch, hash/signature discrepancy, or unrelated side effect is detected, stop; do not retry through alternative methods.

### Evidence contract

Preserve outside the repository:
- start/end timestamps in local time and UTC;
- computer/build/UBR, OS/process architecture, token integrity;
- exact DLL path, version, file length, SHA-256, Authenticode status/signer;
- exact script/source hash, process ID, PowerShell/runtime version and command line;
- load flags, return status, immediate Win32 error when relevant;
- both exact symbol names, non-NULL/NULL resolution result, immediate Win32 error when relevant;
- exit code, stdout, stderr, unfiltered raw report, report SHA-256, and explicit stop/result classification.

Codex must return the full report and artifact paths/hashes. An artifact hash reported by Codex remains actor-reported until the bytes are available for independent read-back.

## PASS / FAIL / UNKNOWN SEMANTICS

- `LOAD_AND_BOTH_SYMBOLS_RESOLVED`: the one-shot process loaded the exact identified file and both pointers were non-NULL. This passes only the P1 load/resolution objective.
- `LOAD_FAILED`: `LoadLibraryExW` returned NULL; preserve error. No symbol checks follow.
- `LOAD_SUCCEEDED_SYMBOL_MISSING`: load succeeded but at least one exact symbol returned NULL; preserve per-symbol errors.
- `STOP_READINESS_MISMATCH`: target/token/file precondition failed; no DLL load occurred.
- `UNKNOWN`: missing/untrusted output, unhandled exception, tool failure, unexpected environment or incomplete evidence. UNKNOWN never means PASS.

A successful load/symbol resolution does not prove either function can be called successfully, the documented parameter contract is met, a child can be launched, containment exists, effects E are completely observed, X remains secret, evidence is tamper-resistant, quiescence holds, or any seven-guarantee PASS.

## SCOPE EXCLUSIONS

Explicitly forbidden in this experiment:
- invoking either export;
- creating/launching any candidate or test process via the experimental API;
- testing or assuming descendants, delegation, IPC, loopback, networking or filesystem containment;
- adding attributes, inheriting handles, or widening DLL search paths to make the test pass;
- changing IABV source, tests, configuration, Git working tree or canonical contracts;
- installing/downloading tools or contacting external services;
- changing system security settings, using elevation, or repeating with another machine;
- treating a load result as a technology-selection or implementation decision.

## NEXT DECISION

After this experiment, reconcile its raw evidence independently. If load and both symbol resolutions succeed, the next edge is still design/feasibility: a separate seven-guarantee composition audit and experiment contract, not immediate API invocation or implementation. If load fails, classify the bounded failure and decide whether the experimental API route should be closed or investigated only through a separately authorized hypothesis. This record itself authorizes no subsequent experiment.

## DELTAS

### Knowledge Delta
P0 static export presence has been accepted. The Human Domain Owner explicitly authorizes a separate load-only/symbol-resolution probe within the exact target and side-effect boundaries above.

### Method Delta
A dynamic load probe is a new experiment because DLL initialization may execute. Record a frozen contract, precondition gates, one-shot medium-integrity process, system-directory search restrictions, precise error capture, and bounded PASS semantics before execution.

### Routing Delta
**NEXT ACTOR: CODEX**, for this read-only bounded execution on the exact verified host only. If target/token/hash/signature differ or any readiness condition fails, stop without loading. No Sonnet, Devin or Deep Research handoff is needed at this edge. No API invocation, candidate execution, implementation or system changes.

END OF RECORD
