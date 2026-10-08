# CHAT-ARCH-2026-10-08-177 — RQ21.58 FOCUSED WINDOWS SUBSTRATE AUDIT ADJUDICATION

## PURPOSE

Reconcile the submitted focused feasibility audit of Microsoft's experimental `Experimental_CreateProcessInSandbox` family and current IABV organs against the frozen RQ21.57 seven-guarantee contract. Preserve new findings, correct overclaims, and recompute the first open edge before any execution or implementation.

## PROVENANCE AND CURRENT TRUTH

Temporal anchor: 2026-10-08 18:49 America/Bogota / 23:49Z (coordination time).

Repository: `jhonf463r/Python`.

Verified remote `main` tip before this writeback:
`c9df3ca393c1b7528f48988d0c4baf405c88cf16`
Commit: `docs: promote RQ21.57 owner scope closure and next feasibility route`, committed at 2026-10-08T23:27:04Z.

Pinned executable baseline:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
Tree: `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`.

GitHub compare baseline → verified main: main is 196 commits ahead, 44 changed files, and zero changed files under `IABV_v1.5/src/`. Thus the reported documentation-only delta for executable source is VERIFIED for this comparison; main is not itself the pinned executable baseline.

Read-back of seven current source files also found identical content blob SHAs between main and the pinned baseline:
- `services/tools/tool_sandbox.py`: `18aff921ae8f429be4d785d8155203b44ec84f88`
- `services/tools/tool_validator.py`: `f60a8182f57f19fa600578ff13ab9fc4e224dd70`
- `services/tools/tool_adapters.py`: `f8ce508342d2da96f30b2152ffa242f08b187987`
- `services/tools/tool_teach_service.py`: `7f0412627c98074b1e3df0d0f6e76ab5998e3505`
- `services/tools/tool_registry.py`: `17a0f7cc82dfb6722d4f2d7b231ac61551eb7ac2`
- `services/lab/experiment_lab.py`: `05b57d1dde101d5e7ff11955829a9e1d07d1d901`
- `services/self_teach/sandbox_experiment_service.py`: `a6723261ce31f71a9fcd5433ce3e1e419230440c`

Canonical contract remains RQ21.57, record 176. The Human Domain Owner has closed normative scope. All seven guarantees are frozen; technology selection, realization proof and runtime proof remain open. The base trust boundary excludes OS/kernel compromise and a host administrator acting outside that boundary. That exclusion is a canonical FACT, not an assumption.

## ADJUDICATION

**RQ21.58 = ACCEPTED AS A BOUNDED FEASIBILITY AUDIT WITH REPAIRS; P0 EXECUTION READINESS NOT ESTABLISHED.**

The result makes useful progress: it maps the candidate API and current IABV organs to the seven guarantees, names uncovered channels and failure semantics, and separates documented capabilities from exact-target unknowns. It does not establish a complete substrate and does not authorize implementation, P1 loading, candidate execution, or a behavior experiment.

The submitted text does not independently establish its own actor/tool provenance. Its claims that no runtime was run are taken as report scope; no runtime evidence was supplied here.

## SOURCE-AUDITED FINDINGS

### Microsoft experimental API

Primary source:
https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox

**FACT — documented API contract**
- `Experimental_CreateProcessInSandbox` and `Experimental_CreateProcessAsUserInSandbox` are experimental, subject to change, exported from `processmodel.dll`, and have no public header.
- The sandbox specification is a versioned FlatBuffer; the documented spec version must be `0.1.0`.
- With AppContainer-dependent features such as explicit capabilities, file restrictions or proxy configuration, AppContainer must be enabled.
- `processAttributes` and `threadAttributes` are reserved; non-NULL values are rejected with `ERROR_NOT_SUPPORTED`. `inheritHandles=TRUE` is also rejected. The signature accepts `STARTUPINFOW`, not an independently documented attribute-list parameter.
- A caller already running in AppContainer is rejected; nested-sandbox threat semantics are not finalized.

**INFERENCE — bounded use**
The API is a candidate for a subset of launch-side restrictions relevant to guarantees 1 and 4. It is not proof of effective containment across attributable descendants/delegation, hidden-X secrecy, E observation, evidence custody, deterministic comparison, quiescence closure or evidence binding. Its exact export and runtime behavior on target `10.0.26300.0` remain UNPROVEN.

**Repair to the submitted report:** do not treat `PROC_THREAD_ATTRIBUTE_CHILD_PROCESS_POLICY`, inherited anonymous-pipe stdio, or a general process-attribute list as composable with this experimental API. The documented function contract disallows non-NULL process/thread attributes and inherited handles. Any alternative child restriction/output channel is a separate design question to prove; it cannot be assumed from generic `CreateProcess` APIs.

### Windows observation/containment primitives

Primary references:
- AppContainer isolation: https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation
- Job Objects: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- WFP filtering conditions: https://learn.microsoft.com/en-us/windows-hardware/drivers/network/filtering-condition-identifiers
- ETW properties/loss counters: https://learn.microsoft.com/en-us/windows/desktop/ETW/event-trace-properties
- Named pipe security: https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights

**FACT**
- AppContainer's file-read access is less restricted than file-write access; file/registry write access may be granted to specific locations. Therefore, AppContainer alone does not establish complete confidentiality of X.
- ETW exposes event-loss counters, including `EventsLost`, `LogBuffersLost` and `RealTimeBuffersLost`; Microsoft documents loss scenarios.
- WFP defines a filter condition for the AppContainer SID (`FWPM_CONDITION_ALE_PACKAGE_ID`).
- Named pipes have a configurable security descriptor; the default grants full control to LocalSystem, administrators and creator-owner, plus read access to Everyone and anonymous.
- Job Objects provide process-lifecycle controls, but the cited API candidate's engine-owned UI-restriction Job Object is not proof that IABV can authoritatively enumerate and close every attributable activity.

**Correction:** the cited WFP condition identifier proves that a filter can match an AppContainer SID. It does **not**, by itself, prove a complete event stream or observation of every allowed/denied network effect. WFP event acquisition, filter/action semantics, permissions, loss, attribution and coverage must be separately specified and evidenced. Therefore network observation is not promoted above PARTIAL/UNPROVEN on this evidence.

Job roster snapshots, ETW, WFP, ACLs, service SIDs and CNG key properties are candidate mechanisms, not a composed evidence authority. A presence claim, a filter condition, or a hash is not evidence of completeness, trust, or authorization.

### Existing IABV path

Verified current-source references:
- `tool_sandbox.py:13`: calls `adapter.run(card, task, sandbox=True)`; line 23 marks `sandboxed=True`; line 35 invokes validator.
- `tool_validator.py:25-28`: `sandbox and result.success` yields `SANDBOX_PASS`; line 42 records `validated=result.success`.
- `tool_adapters.py:1758`: `ShellToolAdapter` calls `subprocess.run(command, capture_output=True, text=True, shell=True, check=False)`.
- `experiment_lab.py:40+`: experiment metrics and comparison use `metric.total_score`; this is not the frozen deterministic hidden-X acceptor.
- `sandbox_experiment_service.py:16+`: existing service validates recommendation experiments; it does not realize the full candidate/X/E validation boundary.

Reuse classification:
- `ToolSandbox`: repair/re-realize semantics; the current flag is not containment.
- `ToolValidator`: repair; `success` is not sufficient for PASS, and E/X plus coverage/evidence acceptance are missing.
- `ShellToolAdapter`: not suitable as the candidate executor merely by forwarding `sandbox=True`.
- `ToolTeachService` and the existing selection/registry path: reuse only as routing integration points; validation must be distinct from ordinary execution/promotion.
- `ToolRegistry`/`ToolCard`: potential catalogue/integration seam, not evidence.
- `ExperimentLab`: potential partial experiment/score reuse, not the RQ21 deterministic acceptor.
- `SandboxExperimentService`: not the candidate execution substrate.
- `ExecutionState`/`ToolResult`: possible evidence transport seam, not a trust boundary.

**INFERENCE:** some bounded coordination/orchestration and independent acceptance authority will need to be added or composed in IABV; exactly which Windows observation primitives compose into a faithful substrate remains open. Do not announce a complete seven-guarantee implementation design until coverage and boundary membership can be shown. No code has been changed.

## P0 — MINIMAL TARGET AVAILABILITY OBSERVATION

P0 is the next **technical observation**, but it is not execution-ready until a known-good channel with access to the exact target host is identified and provenance/readiness are satisfied.

Purpose: establish whether the native target image contains `%SystemRoot%\System32\processmodel.dll` and exports both experimental names, without loading the DLL, invoking either API, or running any candidate.

Bounded collection:
1. Record exact target identity, timestamp (local and UTC), OS build/UBR/DisplayVersion, OS architecture, collection-process bitness, and any readable Developer Mode / Secure Boot / test-signing state. If a value cannot be read without elevation, record UNKNOWN; do not elevate.
2. Resolve the **native** System32 path. Avoid a 32-bit process's WOW64 redirection silently inspecting `SysWOW64`; record the process bitness and resolved path.
3. If the file exists, record length, version metadata, SHA-256 and Authenticode/catalog-signature result with signer/status. Use an approved offline PE export-table parser that reads the file without loading it; record parser/tool version and hash. Search for both exact export names.
4. Preserve commands, raw output, timestamps, target identity/provenance and hashes of collected artifacts. Do not make up a trusted expected DLL hash; a digest is an identity until compared with an independent trusted reference.

Stop rules:
- DLL absent → record unavailable and stop.
- Either export absent → record symbols unavailable and stop.
- signature verification invalid or file identity/provenance suspicious → stop; do not load.
- any elevation request or need to execute an API/candidate → stop.
- inability to resolve native path or verify tool provenance → UNKNOWN / NOT VALIDATED, not PASS.

P0 proves only file/symbol presence and recorded file identity. It does not prove that the API loads, is enabled, launches a process, enforces isolation, or satisfies any of the seven guarantees.

**P1 is not authorized by RQ21.58.** Loading the DLL and using `GetProcAddress` executes DLL initialization and is a separate, explicitly approved experiment. Any operational launch or candidate test is later still and must have a separate frozen experiment/readiness contract.

## FIRST OPEN EDGE / ROUTING

The next open edge is split into two ordered prerequisites:
1. **Execution-channel readiness:** establish a known-good, non-elevated, read-only channel with access to the exact target `10.0.26300.0`. This identity/access is currently UNPROVEN. Do not assume Devin, Codex, or the user's interactive machine is that target.
2. **P0:** once the channel/target binding is verified, collect file/export presence using the above stop rules, then independently verify the raw evidence.

After P0:
- exports absent → stop API-specific route; perform a focused source comparison of public AppContainer process-launch alternatives before choosing a substrate;
- exports present → the result only unlocks a separately scoped operational-readiness question, not a candidate launch and not implementation;
- Codex implementation remains conditional on later feasibility, full seven-guarantee coverage, independent verification and execution readiness.

NEXT ACTOR: **NOT YET ASSIGNED**. The required capability is local target inspection with exact machine access, non-elevated read-only execution and provenance capture. Actor/channel fit is not evidence that the channel exists. Human Domain Owner or a previously verified executor must establish the channel; do not inherit a historical actor assignment mechanically.

## DELTAS

### Knowledge Delta
- The seven source-code components inspected have unchanged blobs between the pinned baseline and verified main; the current executable path has no proven RQ21 substrate.
- The experimental API has explicit restrictions on process/thread attributes and handle inheritance, which constrain the output and descendant-control design.
- WFP's SID filter condition is not itself complete effect-event evidence; AppContainer, Job Objects, ETW, WFP and ACLs remain separate partial primitives.
- The Windows OS/kernel trust-boundary exclusion is already a canonical owner decision, not an assumption.

### Method Delta
- Separate `API exported`, `API loadable`, `API operational`, `containment enforced`, `E completely observed`, `evidence trusted` and `seven-guarantee predicate passed`; each needs its own evidence.
- For Windows API probes, resolve native path/architecture before interpreting DLL absence; record hashes as identity, not authority.
- Filter predicates and instrumentation availability cannot be promoted to complete observation without acquisition/coverage/loss evidence.

### Routing Delta
- RQ21.57 contract remains frozen.
- RQ21.58 does not route to Codex or authorize runtime/candidate execution.
- First: establish exact-target execution-channel readiness. Then run P0 read-only. Independently verify P0 before deciding between API-specific operational feasibility and a public AppContainer alternative.

END OF RECORD
