# CHAT-ARCH-2026-10-08-178 — RQ21 P0 STATIC EXPORT OBSERVATION (PROVISIONAL)

## PURPOSE

Record and reconcile the user-pasted output from the bounded P0 probe run on the local Windows host. This is an observation update under RQ21.58, not a new normative decision, not an API-operation test, and not an implementation authorization.

## TEMPORAL ANCHOR AND PROVENANCE

Pasted console run:
- Local: `2026-10-08T19:03:45.0850030-05:00` (`America/Bogota`)
- UTC: `2026-10-09T00:03:45.0850030Z`
- Reported computer: `MSI`
- Input evidence: console transcript pasted into the conversation; no separately hashed raw-output artifact was supplied.
- Classification: user-reported local observation, not independently reproduced by this assistant on the host.

Repository read-back before this writeback: `main` was identical to `b543c7cb00ed8f1e69011e9893156f8a04959aec`; the canonical RQ21.58 record is 177. The pinned executable baseline remains `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`. This episode changes documentation only.

## OBSERVATION REPORTED BY THE CONSOLE

[REPORTED FACT — transcript]
- OS caption: Windows 11 Home; display version `26H2`; reported build/UBR `10.0.26300.9550`.
- OS architecture and collection-process bitness: both 64-bit.
- Native path queried: `C:\WINDOWS\System32\processmodel.dll`.
- `DLL_PRESENT=True`; file length `417792` bytes.
- File/Product version: `10.0.26100.9549`.
- Reported SHA-256: `B684425DEB9013F1741BDFBB9CF1E3D2395C26996111D4C022495367FDFEEBCC`.
- Reported Authenticode status: `Valid`; signer subject: `CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond, S=Washington, C=US`.
- The in-script PE parser reported `EXPORT_PARSE_STATUS=COMPLETE`, `Experimental_CreateProcessInSandbox=True`, and `Experimental_CreateProcessAsUserInSandbox=True`.
- `DEVELOPER_MODE_REGISTRY=1`.
- `SECURE_BOOT=UNKNOWN`; `TESTSIGNING_BCD=UNKNOWN`.

Microsoft Support lists OS build `26300.9550` among the Windows 11 26H2 builds for KB5124010, so the pasted OS identity is consistent with a published build. Source: https://support.microsoft.com/en-us/servicing/os/windows-11/2026/09/kb5124010-windows-11-24h2-25h2-update

## ADJUDICATION

**P0 STATUS: STATIC PRESENCE/EXPORTS REPORTED; INDEPENDENT VERIFICATION PENDING. Do not mark P0 independently verified or PASS yet.**

The transcript is useful evidence that the specified local probe ran and that its parser found both export names. It is not yet a closed P0 evidence package because:
1. the two export names were found by the same hand-authored parser whose result is under evaluation; an independent, already-installed offline PE utility must corroborate them;
2. output does not report an explicit process integrity/elevation level, PowerShell version, or the version/hash/signature identity of the PE parser;
3. no separately preserved raw-output artifact and artifact hash were supplied;
4. Secure Boot and test-signing remain UNKNOWN; do not elevate to recover them. The probe does not explain whether the values are unavailable or the calls failed, so preserve UNKNOWN rather than infer a cause;
5. the reported file version (`26100.9549`) differs from the host build (`26300.9550`). This difference alone neither invalidates nor validates the component; its exact-file/catalog provenance has not been independently checked;
6. the computer name and build were reported, but the transcript alone does not independently attest target binding or prove the console was running with a non-elevated token.

A locally reported `Authenticode Valid` result and a SHA-256 are useful identity/signature observations; the hash is not authority by itself, and the pasted values have not been independently recomputed.

## CLAIM BOUNDARIES

The result does **not** prove:
- that the DLL can be loaded or initialized successfully;
- that either API can be called successfully or behaves as documented on this image;
- effective process/descendant/delegation/IPC/loopback containment;
- complete observation of effects (E), protected confidentiality of (X), independent evidence custody/integrity, quiescence, candidate/environment binding, or any of the frozen seven-guarantee PASS predicate.

Microsoft's API contract remains experimental and explicitly rejects non-NULL process/thread attributes and `inheritHandles=TRUE`; static exports do not alter those constraints. Reference: https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox

## FIRST OPEN EDGE / NEXT ACTION

1. On the same reported host, remain non-elevated and inspect the current process integrity level plus available already-installed static PE tools.
2. If `dumpbin.exe` is already installed, use it only as a static reader (`dumpbin /nologo /exports`) to corroborate both names; capture its version/hash/signature and hash the saved report. Do not install tools or load `processmodel.dll`. If no independent parser is already available, stop and report that blocker.
3. Independently read back the file hash/signature and reconcile the output; keep Secure Boot/test-signing UNKNOWN unless safely readable without elevation.
4. Only after independent static corroboration may P0 be adjudicated as a static-availability observation. Any DLL load, API invocation, candidate execution, or operational experiment is a separate later gate and is **not authorized by this record**.

## DELTAS

### Knowledge Delta
- Local P0 transcript reports the DLL and both export names present on host `MSI`, OS build `10.0.26300.9550` x64; reported file identity is recorded above.
- Independent export-table corroboration and complete provenance packaging are still missing.

### Method Delta
- A hand-authored parser's own `COMPLETE` output is not its independent verification.
- Record token integrity, parser identity/version/hash, report artifact hash and target binding; do not elevate or infer unknown security state.
- File version different from the OS UBR is a question to reconcile, not a stand-alone pass/fail predicate.

### Routing Delta
- RQ21.58 remains active; normative RQ21.57 contract remains frozen.
- First open edge is independent static corroboration and evidence/readiness closure.
- No Codex implementation, no Devin runtime assignment, no P1 loading, and no candidate execution.

END OF RECORD
