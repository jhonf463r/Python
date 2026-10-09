# CHAT-ARCH-2026-10-08-180 — RQ21 P0 CODEX CAPABILITY ROUTING

## PURPOSE

Reconcile the user's corrected local P0 output and route the remaining static export corroboration to the right capability-fit actor, avoiding repeat manual work when a tool can perform it.

## PROVENANCE

Console output pasted by the user:
- Local timestamp: `2026-10-08T19:20:25.4790531-05:00` (`America/Bogota`)
- UTC: `2026-10-09T00:20:25.4790531Z`
- Host: `MSI`
- PowerShell: `5.1.26100.9549`
- Account: `MSI\faber`
- `whoami /groups` exit code: 0
- Integrity SID: `S-1-16-8192`
- Integrity level: `MEDIUM`
- DLL path: `C:\WINDOWS\System32\processmodel.dll`
- Rechecked SHA-256: `B684425DEB9013F1741BDFBB9CF1E3D2395C26996111D4C022495367FDFEEBCC`
- Authenticode: `Valid`; signer subject reports Microsoft Windows.
- `DUMPBIN_AVAILABLE=False`; `STOP_REASON=NO_ALREADY_INSTALLED_INDEPENDENT_PE_TOOL`.

This is a user-pasted local console result, not an independently reproduced host execution. GitHub main was verified before this writeback at `f5d67b147ac785008f109c3adf9db2daf18267ca`. Pinned executable baseline remains `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`.

## ADJUDICATION

**P0 UPDATE: local medium-integrity read-only context and stable reported file identity are now supported by the latest console transcript. Independent export corroboration remains OPEN because `dumpbin.exe` was not found.**

The result closes the previous diagnostic's null-SID failure: `whoami` successfully returned the medium integrity SID. The DLL SHA-256 and Authenticode status match the prior reported result. No export-table check was performed by this second run.

The correct next action is not to make the user repeat OS/token/hash/signature commands. The next missing capability is **independent static PE-export inspection**. Codex is a potential actor for this bounded task only if it proves that its execution channel is bound to the same host `MSI`, OS build `10.0.26300.9550`, and non-elevated medium-integrity context. A Codex environment merely being available, or its code capabilities, does not establish access to this host.

## CODEX ROUTING CONTRACT — READ-ONLY, CONDITIONAL

Codex may execute a bounded channel/readiness check:
1. Identify hostname, OS build/UBR, OS/process architecture, and current token integrity using its own execution environment.
2. If it is not the same host/build and cannot prove the target binding, return `CHANNEL_MISMATCH` and STOP. Do not inspect a substitute computer or imply the local result was independently checked.
3. If target identity and non-elevated medium token match, recheck the known DLL path, SHA-256 and signature, then discover pre-existing independent static PE parsers (`dumpbin`, LLVM PE tools, GNU `objdump`, or an already-installed PE parser with version/path/hash provenance). Do not install packages or tools.
4. Use one suitable existing independent reader to check for both exact export names. Save raw output outside the repository and calculate its SHA-256; report tool path/version/hash/signature where applicable and exit code.
5. If no suitable reader already exists, report `NO_PREINSTALLED_INDEPENDENT_PE_READER` and STOP. Do not substitute the previous hand-authored parser or an unreviewed same-source reimplementation as independent corroboration.
6. Make no repository/source changes; do not load `processmodel.dll`, call either experimental API, run a candidate, or attempt P1.

Codex is not assigned implementation. This is a read-only evidence-collection task; no source change or runtime experiment is authorized.

## CLAIM BOUNDARIES

- [REPORTED FACT] The local user's second transcript identifies a medium-integrity token and repeats the DLL hash/signature.
- [REPORTED FACT] That transcript explicitly says `dumpbin.exe` was unavailable.
- [UNPROVEN] Codex can execute on the same MSI target; availability of another independent installed PE reader; independently corroborated export names; artifact-custody completeness.
- [UNPROVEN] API loadability, successful API behavior, effective containment, complete E observation, hidden-X confidentiality, evidence integrity/custody, quiescence, artifact/environment binding, and any seven-guarantee PASS.

## FIRST OPEN EDGE / ROUTING

`local medium-integrity channel observed → Codex target-channel readiness test → (same target confirmed) independent static PE export check → independent evidence reconciliation`.

If Codex cannot prove exact-target access, do not route around the mismatch by running on a different machine. Select another already-existing executor only if its target access is evidenced; otherwise the owner must choose an available local read-only tool or a bounded alternative inspection method. Do not ask the user to repeat checks already completed.

## DELTAS

### Knowledge Delta
The second local transcript confirms `S-1-16-8192`, and the DLL hash/signature remain unchanged; the attempted independent tool is absent.

### Method Delta
Route based on the missing capability rather than actor sequence. Separate actor availability from execution-channel access and exact-target binding. Reuse existing installed tools before considering any installation; preserve stop conditions.

### Routing Delta
Codex is the first *candidate* for this narrow read-only task, conditional on proving it sees the exact target. This does not override RQ21.58's prohibition on DLL loading, API invocation, candidate execution or implementation.

END OF RECORD
