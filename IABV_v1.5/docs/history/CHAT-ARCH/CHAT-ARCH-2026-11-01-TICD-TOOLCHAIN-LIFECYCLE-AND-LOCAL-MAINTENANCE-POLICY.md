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

## 6. Local maintenance through T3

T3 Code v0.1.6 documents recurring Scheduled Tasks under **Settings → Scheduled tasks**. Each task runs on the selected environment with that environment's project, model and workspace settings; it can be edited, paused, resumed, run immediately or deleted. Use this existing local facility rather than building another scheduler.

Recommended local task:

- **Name:** `TICD — MSI support-tool inventory and maintenance`
- **Environment/project:** MSI local environment / `C:\IABV-TICD-LAB`
- **Provider:** Codex as currently configured; use `Supervised`.
- **Cadence:** monthly, after the cloud TICD research review.
- **Job:** refresh the local inventory, compare installed versions with official stable releases/advisories, identify incompatibility/security issues, assess disk budget, and prepare a bounded update plan. Execute only updates already covered by an explicit allowlist; otherwise request approval for the exact change.
- **Receipt:** inventory timestamp, environment identity, commands and exit codes, before/after versions, official source URLs, signatures/hashes, audit findings, disk change, artifacts changed, verification result and rollback status.

Do not use webhook scheduling for this local maintenance task: T3's webhook route requires T3 Connect/tunnel. Keep T3 Connect, public ports, tunnels and Android disabled unless separately authorized. T3's child agents receive their supplied task prompt and role, not the parent conversation history; include the matching D021 profile/manifest in every delegated task. A child cannot receive a broader runtime mode than its parent. Do not delegate when source/path restrictions cannot be enforced and verified.

The existing ChatGPT monthly TICD automation is the cloud research companion, not the local updater. It must not claim that local programs were inspected or updated. The local T3 receipt can be retrieved by the coordinator through an authorized shared artifact route; if local-only, its producer must package the exact evidence once.

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

The cloud review researches public changes and adjusts priorities; the local T3 task observes the installed MSI stack. Reconcile their outputs by source, project, version, environment and time, not by assuming that one report updates the other.

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

## 9. Acceptance conditions for a real maintenance capability

A recurring task is not proven merely because it was saved. Require:
1. task exists in T3 and names the MSI/local environment and correct project;
2. a real run is observed with a durable task/run ID;
3. the run reads local installed versions and records observation times;
4. official release/advisory sources are cited and exact versions compared;
5. no out-of-scope installation or permission change occurs;
6. report and manifest are produced and read back;
7. a later run demonstrates that the process is reusable and reduces manual work.

**Non-claim:** this document does not implement TICD's external adapter, connect local IABV runtime to cloud memory, enable automatic installation, or prove an unattended maintenance task. It defines the minimum contract for those future steps.
