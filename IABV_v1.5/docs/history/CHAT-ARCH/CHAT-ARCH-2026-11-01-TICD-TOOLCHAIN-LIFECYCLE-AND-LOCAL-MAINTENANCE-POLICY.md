# TICD — Toolchain Lifecycle and Local Maintenance Policy

**TASK_ID:** `IABV_TICD_TOOLCHAIN_LIFECYCLE_2026_11_01`  
**Status:** design proposal; no IABV source, dependency, runtime or canonical state changed.  
**Source baseline:** `jhonf463r/Python` main `a64f9e331ccbf13225ed5a3d945e16586e8756db`.  
**Local evidence cut:** MSI / `C:\IABV-TICD-LAB`, reports observed 2026-11-01.

## 1. Purpose

TICD must keep the development/support toolchain useful, secure, compatible and current without making the Owner manually discover, compare, install, configure and verify every tool. It must maintain the apps, CLIs, extensions, protocols and developer utilities that help build IABV, while keeping them distinct from IABV's own runtime dependencies.

The lane has two complementary execution contexts:

- **Cloud research and continuity:** the existing ChatGPT monthly TICD review researches public releases, advisories, documentation and technology candidates; GitHub is the shared, versioned store for public-safe findings.
- **Local MSI maintenance:** T3 Scheduled Tasks (when available in the selected local environment) or the external Codex operator inspect the actual local inventory, compare installed versions, run approved checks and return evidence. A cloud chat cannot see local installations or update the MSI by itself.

Do not create another technology registry, memory, scheduler, agent orchestrator or update service. Compose the existing TICD and governance owners.

## 2. Existing IABV owners to reuse

The current-main source shows the following distinct responsibilities:

- `ToolDiscoveryService` (`src/iabv_v15/services/evolution/tool_discovery_service.py`, blob `cb07b7ba418c1bd8cc7cb22780a09f0db2bbad1e`) builds and reconciles discovery signals from ExperimentLab recommendations/runs, existing ToolRegistry cards and WorldModel state. It is not, by itself, a federated external web/catalog crawler.
- `ToolRegistry` and `ToolCard` are the existing operational tool catalogue and identity surface. A catalog lookup is not authorization.
- `CapabilityReadinessService` represents task-required capability/readiness. It must be reconciled with the selected viable realization, not replaced by a second capability registry.
- `InteractionModeSelector` (`src/iabv_v15/services/tools/interaction_mode_selector.py`, blob `ac3b2d62e4a30bc1d87626ce03a57fd9f01a78af`) performs existing selection among available tool cards/modes for a request.
- `SynapticRouter` is an existing provider/assistant-fit signal; do not assume it alone resolves every required capability to an executable realization.
- `ExperimentLab`, `SandboxExperimentService` and `AutonomousValidationCycleService` are existing experiment/validation owners. Their presence in source does not prove runtime activation or an OS-isolated sandbox.
- `PortableContextService`, `UnifiedMemoryLayer`, `TaskContextAssembler`, `DecisionAuditTrail` and the existing audit/evolution components are the memory, context and evidence surfaces to inspect before proposing additions.

The external discovery gap is the intake and reconciliation of trustworthy external catalog/release/advisory evidence into these existing owners. Keep external candidates quarantined until provenance, license, permissions, compatibility and security are established. Do not add a second ToolDiscoveryService or a parallel technology database.

**Current-main bounded source trace (source-level observation, not runtime proof):**

- `CapabilityReadinessService.evaluate(intent, context)` is called by `AdaptiveTaskOrchestrator`; its result is retained in `AdaptiveSession.capability_readiness` and the context capability snapshot.
- The normal `ToolOperationalExecutor.execute(session)` path calls `ToolTeachService.build_task_for_session(session)`.
- In the inspected current-main implementation, that method reconstructs an `InferenceRequest` from the session goal, detected role, `metadata.goal_parameters`, site and session ID; it does not explicitly carry `session.capability_readiness` into the request or resulting task.
- The current `ToolTask` model has no typed `required_capability_ids` field. `ToolTeachService.execute_task()` resolves the card again through `ToolRegistry.pick_card_for_task()`, whose selection order is concrete task tool ID, preferred assistant family, lexical overlap and finally the first registered card. That picker has no required-capability argument or hard eligibility check against the readiness snapshot.
- Relevant current-main source blobs: `adaptive_task_orchestrator.py` `41f6f7b6157226a1c6004591ddff4e36ff6f6da5`; `tool_operational_executor.py` `840addd3dd8a017e83788950ad5ed0205e7b0037`; `tool_teach_service.py` `7f0412627c98074b1e3df0d0f6e76ab5998e3505`; `domain/models.py` `a9033d21052c519e09f482097599c704a62ea916`; `tool_registry.py` `17a0f7cc82dfb6722d4f2d7b231ac61551eb7ac2`; `capability_readiness_service.py` `b4f60d1fb58183765ff232cc58f0c2ef3f1c9704`.

The bounded first-open design seam for this caller is therefore:

`AdaptiveSession.capability_readiness → typed per-ToolTask capability demand → candidate eligibility gate → selected ToolCard/adapter`.

Status: `SOURCE_GAP_OBSERVED_FOR_TOOL_OPERATIONAL_EXECUTOR_PATH; OTHER_CALLERS_NOT_EXHAUSTIVELY_TRACED; RUNTIME_NOT_TESTED`. This is a source-contract finding, not proof of a live runtime failure or a universal absence across all callers. A separate narrow caller census and semantic design review should precede any proposal. Do not implement, add a parallel selector, invent task-to-capability partition semantics or run tests/build/runtime under this documentation-only task.

## 3. Tool classes and inventory model

Maintain one source-bound inventory with a `tool_class` field. Do not mix these categories:

1. `DEVELOPMENT_OPERATOR`: T3 Desktop, Codex CLI, Computer Use and repository/development interfaces.
2. `EXTERNAL_DISCOVERY_SOURCE`: HF Discover/ARD, MCP Registry and official release/advisory sources.
3. `QUALITY_AND_OBSERVABILITY`: test/evaluation, security scanning and tracing utilities.
4. `IABV_RUNTIME_DEPENDENCY`: packages actually required by IABV at runtime, proven from the current product manifest.
5. `OPTIONAL_EXPERIMENT`: candidate library, model, extension, agent or service not yet approved.

For each item retain: canonical ID, class, purpose/capability, publisher, official source, exact installed version, latest stable version, pre-release status, observed-at, OS/runtime compatibility, package manager, source/artifact digest or signer, license, dependencies, security advisories, permission/network/data scope, disk/CPU/RAM requirement, cost, update path, rollback path, verification method, current disposition and next review date.

Keep `UNKNOWN` separate from `NOT_INSTALLED`, `NOT_CHECKED` and `NOT_APPLICABLE`. A release page is evidence of availability, not of local installation. A command inventory is not evidence that a feature is authenticated or usable in the active T3 thread.

## 4. Lifecycle

```
NEED_OR_GAP
  -> SOURCE_RESEARCHED
  -> CANDIDATE_NORMALIZED_AND_DEDUPLICATED
  -> PROVENANCE_LICENSE_SECURITY_COMPATIBILITY_ASSESSED
  -> ELIGIBILITY_GATE
  -> SANDBOXED_EVALUATION (only when authorized and isolated)
  -> RECOMMENDATION
  -> OWNER_OR_POLICY_APPROVAL
  -> INSTALL_OR_CONFIGURE (bounded scope)
  -> POST_CHANGE_VERIFICATION
  -> ROLLBACK_IF_NEEDED
  -> EVIDENCE_RECEIPT_AND_NEXT_REVIEW
```

Discovery must not fetch or execute candidate payloads automatically. Do not treat popularity, ranking, catalog presence, a successful package install or an agent report as proof of safety or usefulness. Compare the candidate against the existing capability first; prefer reuse/adaptation over another framework.

## 5. Update and autonomy tiers

| Tier | Permitted automation | Boundary |
|---|---|---|
| **T0 — observe** | Read installed versions, official stable releases, release notes, end-of-life notices and security advisories; deduplicate and prepare recommendations. | Read-only; may run automatically in an authorized local/cloud context. |
| **T1 — isolate and evaluate** | Download metadata or place a candidate in a disposable sandbox; run bounded tests only when the existing policy permits the environment and network scope. | No candidate execution merely because it was found. Current low disk space is a reason to avoid large sandboxes/VMs. |
| **T2 — routine user-scope maintenance** | A future Owner-approved allowlist may permit patch/minor updates of named user-local support tools. | Requires a one-time explicit policy authorization per allowed class/tool, signed/pinned official source, compatibility check, backup/rollback, no admin/system install, no permission expansion, and post-update verification. This tier is **not yet authorized by this document**. |
| **T3 — material changes** | Prepare and execute with explicit Owner approval. | Major/minor breaking upgrades, new providers, extensions, MCP servers, dependency-tree changes, changed scopes/network/data behavior, or updates without reliable rollback. |
| **T4 — privileged/external actions** | Prepare a plan only. | Elevation, system-wide installs, credentials, external account linking, remote services, tunnels, data transfer, Android/T3 Connect and production services require separate explicit authorization. |
| **T5 — IABV core** | Research and prepare review packages. | Product code, `C:\Python`, protected reads, trust roots, gates, `CURRENT-STATE.md`, MCP bridge/allowlist, tests/build/runtime and core promotion remain under their independent authorization gates. |

An approval-required provider mode is not itself Owner authorization. A preapproved update allowlist, if ever adopted, must name exact tool IDs, update classes, allowed source/signature, version range, paths, stop conditions, and rollback behavior. Anything outside the allowlist returns for approval.

## 6. Local maintenance scheduling and execution path

T3 Scheduled Tasks is one possible local execution surface, not an assumption or universal scheduler. Select the mechanism from the required trigger semantics, host lifecycle and actual environment. A T3 task is appropriate only when its observed UI/API supports the required cadence and its local server/environment availability has been demonstrated. A T3 provider permission belongs only to that T3 thread.

**Episode update (2026-11-01):** the Owner-supplied transcript records that the T3 v0.1.6 UI inspected by the local operator exposed weekday scheduling and minute intervals, but no monthly day-of-month selector. It also records uncertainty about execution after the last T3 window closes on Windows. This is scoped to that observed UI/install and is not proof that every T3 release or backend lacks a monthly scheduler. The R2 handoff then incorrectly required T3 `Supervised` while the recipient was external Codex Desktop; that cross-surface mismatch caused a premature block. See the [execution-surface handoff learning receipt](./CHAT-ARCH-2026-11-01-UAAL-TICD-EXECUTION-SURFACE-HANDOFF-LEARNING-RECEIPT.md).

**Capability-matched Windows alternative:** when exact monthly calendar triggers are needed and T3's selected surface cannot provide them, a native Windows Task Scheduler job may be used if its trigger, account mode and lifecycle fit the Owner's requirements. This does not create a new scheduler service; it uses the OS scheduler already present. The task must run under the intended local user with least privilege, and its behavior when the machine is off or the user is logged out must be stated and verified rather than assumed.

**Two-process design for the authorized MSI inventory candidate:**

```text
WINDOWS_TASK_SCHEDULER
  -> bounded PowerShell runner
      -> CODEX_CLI_CHILD: codex exec --sandbox read-only
          -> local read-only inventory; returns text
      -> runner writes the authorized report/manifest and hashes
```

The external Codex Desktop operator that installs the runner/registers the task is a separate actor from the `codex exec` child. The Owner's authorization must name the exact runner path, one task name, monthly trigger, run identity and immediate test. The child CLI sandbox constrains only the child process; it does not constrain the outer operator's creation of files or registration of the Windows task. Those outer side effects remain separately authorized and bounded. Conversely, external Codex Desktop `Full Access` does not prove the child CLI is read-only; validate the CLI arguments/effective execution separately.

At the initial evidence cut, the supplied transcript contained R2=`BLOCKED` and an R3 prompt prepared after the Owner explicitly authorized the Windows-native route. A later R3 operator receipt (2026-11-01, 12:54 p.m. America/Bogota) reports `BLOCKED`: the Windows timezone/project/task-name preflight passed, but no `codex exec` run, runner, task, report or manifest was created. The new blocker was a prompt-contract error: it required `--ask-for-approval never`, which the installed `codex-cli 0.166.0` exec subcommand does not expose. The exact release source confirms that headless `codex exec` sets `approval_policy=Never` by default while allowing `--sandbox read-only`. Treat the CLI and authentication observations as operator-reported local evidence; the exact upstream source behavior was independently fetched from release tag `rust-v0.166.0` commit `6ff1e1c`. See the execution-surface learning receipt for source paths and blob IDs.

**Mandatory local-runner receipt:** include task name and scheduler ID, exact XML/trigger or equivalent query output, Windows principal and logon policy, timezone, first/next run, runner hash/version, Codex CLI version and exact sandbox arguments, headless approval-policy source/default for that exact release, auth outcome (without secrets), process exit code, task run/result code, start/end times, report/manifest SHA-256 and independent read-back. On Windows, verify whether `Get-Command codex` resolves to a PowerShell `.ps1` shim; the runner must invoke it through a tested PowerShell host or a verified native shim and prove that redirected stdin reaches `codex exec`. Record `IMMEDIATE_RUN_VERIFIED` separately from `MONTHLY_RECURRENCE_REPEATED`; one immediate test does not prove a later monthly occurrence.

**Preflight and route rules:**

- Resolve `DESTINATION_ACTOR_TYPE`, `DESTINATION_APP_AND_VERSION`, `EXECUTION_SURFACE`, `CONTROL_PLANE`, `HOST_AND_OS`, `PROCESS_ACTOR`, `SCHEDULER_OR_TRIGGER_OWNER` and `T3_INVOLVEMENT` before issuing a prompt.
- Query only the permission source for the selected application/process. Never require T3 `Supervised` when T3 is not involved; never infer Windows rights from a Codex UI permission indicator.
- Keep the exact read-only CLI sandbox even when the outer operator is permitted to write the one runner and create the one scheduled task. Pin CLI behavior to the exact version and subcommand. For Codex CLI 0.166.0, `codex exec` is headless and its source defaults the approval policy to `Never`; the `exec` parser does not expose the interactive `--ask-for-approval` flag. Use `--sandbox read-only` explicitly and do not add that unsupported flag as a preflight requirement. Do not use `--approve-for-me`: it maps to `workspace-write` and `on-request`.
- If CLI authentication needs a human login, the scheduled run cannot complete unattended under this design; stop and report the condition rather than changing credentials or weakening controls.
- Use the current user's interactive logon only if that matches the Owner's preference. If the user is not logged in or the device is powered off at trigger time, describe the actual missed-run behavior and test `StartWhenAvailable`; do not promise execution while offline.
- Do not use T3 Connect, webhooks, tunnels, Android, SYSTEM, elevation or a service unless separately authorized.
- Do not publish local MSI reports or manifests into the public `jhonf463r/Python` repository. Use the D021 artifact retrieval ladder and an access-controlled private transport; if no authorized route exists, prepare one bounded producer package and identify the exact manual handoff.

**Acceptance:** verify the registered task from Windows after creation; start that exact registered task for an immediate test; inspect task result and logs; read back report and manifest; recompute hashes; inspect scope of all changes. A created task is not a successful run, an immediate run is not proof of future recurrence, and a local receipt is not yet evidence that the cloud coordinator retrieved or consumed it.

## 7. Current MSI support-stack disposition (2026-11-01 evidence cut)

| Item | Last local evidence | Current public release evidence | Decision |
|---|---|---|---|
| T3 Desktop / CLI | v0.1.6 installed; local bootstrap report verified MSI project and Supervised thread | v0.1.6 stable; v0.1.7 builds are prereleases/nightlies | Retain stable; do not move to nightly merely to get new features. |
| Codex CLI | v0.166.0 installed and authenticated in external CLI and T3 provider | v0.166.0 reported as the latest stable npm release at this evidence cut | No update needed; recheck on next maintenance run. |
| Hugging Face Discover | hf-discover v1.3.7 installed; five search results saved; no candidate executed | v1.3.7 release; ARD v0.5 is a draft/proposal | Retain as read-only discovery source; do not trust or install results automatically. |
| Promptfoo | v0.125.1 project-local; no evaluation run | v0.125.1 available; local npm audit recorded 8 findings (3 moderate, 5 high) | Security hold: inspect exact dependency paths and compatible fixes; do not run `npm audit fix`, downgrade, or blindly upgrade. |
| Extra memory/orchestration frameworks | Not installed/approved by this lane | No demonstrated gap requiring them | Do not add Mem0, Cognee, Graphiti, PydanticAI, LangGraph, CrewAI, Agno, LiteLLM or another orchestration/memory stack yet. |

The inventory is historical evidence, not a live reading of today's machine. The environment report last recorded about 6.45 GB free on C:. Re-read disk capacity before any sandbox, VM or large package installation. Avoid adding heavyweight local services until measured benefit exceeds disk, RAM and maintenance cost.

## 8. Monthly operating loop and metrics

The cloud review researches public changes and adjusts priorities; the selected local MSI maintenance task (T3 only when its required cadence/host lifecycle is verified, otherwise a suitable OS-native scheduler) observes the installed stack. Reconcile their outputs by source, project, version, environment and time, not by assuming that one report updates the other.

Measure at minimum:
- installed versus latest stable version and release age;
- security advisories by severity, reachability, fixed version and compatibility;
- candidate duplicates, source quality, freshness and acceptance/rejection;
- task success, failure, rollback and post-update regressions;
- time saved and Owner interventions avoided;
- disk/RAM/CPU/network cost of each support tool;
- compatibility with IABV's pinned Python/Node/dependency contracts;
- evidence age, missing manifests and local/cloud reconciliation gaps.

Do not invent historical baselines where telemetry is absent. Distinguish observed figures, actor reports, inference and forecast. Re-rank tools using the existing TICD rubric and hard safety gates; never let a high utility score override provenance, license, permission or security failure.

## 9. Acceptance conditions for local maintenance and the end-to-end TICD loop

Do not collapse local task creation, a successful local inventory, cloud/local transport, cloud adjudication and recurring reliability into one success flag. They are separate milestones.

**A. Local scheduler and runner acceptance**
1. The selected scheduler (T3 Scheduled Tasks or Windows Task Scheduler) contains exactly one intended task, with the correct local host/environment, project/workspace, identity, trigger, timezone and next-run time.
2. The exact registered task is started for an immediate test and produces a durable task/run ID, start/end times, process exit code and scheduler result.
3. The run reads actual local installed versions and records observation timestamps and source paths, while respecting the declared read-only inventory scope.
4. The runner writes the authorized report and manifest, reads both back, recomputes SHA-256 and verifies the values.
5. The observed changes are confined to the explicitly authorized runner/task/report paths; no unrelated task, IABV code, dependency, credential, permission or runtime is modified.
6. The report clearly distinguishes VERIFIED, OWNER_OR_ACTOR_REPORTED, UNKNOWN, NOT_CHECKED and NOT_RUN.

**B. Controlled transport and coordinator acceptance**
1. The local report/manifest remain in an access-controlled private route; do not publish MSI inventory or personal runtime details to the public repository.
2. The receiving cloud coordinator retrieves the exact artifacts through an authorized route, verifies their revision/size/digest where bytes are available, and returns a correlated receiver acknowledgement.
3. The coordinator reconciles the local inventory with the cloud research cut by tool ID, installed version, release version, security advisory, compatibility, license, environment and observation time.
4. A decision is explicitly bound to the exact evidence and records whether it means retain, investigate, approve an update, hold, or discard. A local inventory alone does not authorize an update.

**C. Recurrence and benefit acceptance**
1. IMMEDIATE_RUN_VERIFIED is recorded separately from MONTHLY_RECURRENCE_REPEATED.
2. A later monthly occurrence is observed with a new task/run ID and produces a comparable, valid report before recurring reliability is claimed.
3. Measure manual file relays avoided, Owner interventions, failed/mismatched handoffs, inventory freshness, task success/failure, time saved, rollback and post-update regressions. Do not invent baselines before observations exist.
4. Promote the process from a successful local task to an end-to-end autonomous TICD capability only after the local run, private transport, receiver acknowledgement, cloud/local decision binding and later recurrence are all evidenced.

A task saved is not a run; an immediate run is not proof of recurrence; a local report is not a cloud receipt; a cloud receipt is not a verified decision; and an approved recommendation is not an executed update.

**Non-claim:** this document does not implement TICD's external adapter, connect local IABV runtime to cloud memory, enable automatic installation, or prove an unattended maintenance task. It defines the minimum contract for those future steps.
