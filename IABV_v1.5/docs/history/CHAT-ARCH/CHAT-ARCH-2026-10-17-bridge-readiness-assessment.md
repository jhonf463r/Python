# CHAT-ARCH 2026-10-17 — Bridge readiness assessment and route lock

**Decision:** `BRIDGE_NOT_READY`  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`  
**Code/tests/build/runtime:** `NOT_RUN`  
**Nature:** cross-check of current documentary continuity and reported static traces; not an independent inspection of the Windows working tree.

## Executive decision

We have enough evidence to stop re-auditing the same broad discovery/sync-pulse routes, but **not enough evidence to declare the bridge ready**. The trace review was accepted with limitations. That is an acceptance of a narrowly scoped negative finding—not acceptance of an implemented bridge.

Two different meanings must not be conflated:

1. **Individual, causal bridge:** one discovery proposal/signal can be traced through validation and run evidence to a specific downstream OSES/sync-pulse proposal and execution attempt. This bridge is **not established**.
2. **Aggregate feedback path:** sandbox runs may feed assistant-level aggregate statistics that influence OSES proposals. This indirect dependency is reported, but its run window and particular contribution are not established, and the output lacks a consistently demonstrated typed link to a specific discovery proposal. This is better described as aggregate feedback, not individual attribution.

A static call site to `AutonomousEvolutionService.plan_or_execute()` is not proof that a bridge operation ran, was authorized, dispatched the target, succeeded, or satisfied postconditions.

## Current evidence map

### Route A — individual discovery identity

Codex reports that the working-tree chain carries `proposal_id`, `discovery_signal_id`, and `original_candidate_tool_id` through recommendation/sandbox fields into the `ExperimentRun` model. This is `CODEX_LOCAL_REPORTED / OWNER_REPORTED`, with modified-file edges classed as `WORKTREE_SOURCE`; no product runtime was executed.

Two identity warnings remain:
- In the reported sandbox construction, `candidate_id` receives the sandbox experiment ID, while `evaluated_candidate_tool_id` is `None`. This must not be treated as proof of the actual candidate/tool evaluated.
- The transfer of `evidence_refs` into `supporting_run_ids` does not by itself type-resolve those strings or prove that they are run IDs.

### Route B — OSES and sync-pulse

Codex reports OSES reads up to 60 recent ExperimentRun entries and aggregates by assistant/route/configuration. Ordinary proposal keys such as route substitution and collaborative execution are generated from assistant identities, not copied from Route A's `ToolEvolutionProposal.proposal_key`.

Some `validated_collaboration` branches may retain strings from `recommendation.supporting_run_ids`, `validation.last_experiment_id`, or `best_run.run_id` in `evidence_refs`. Their identifier namespace, producer provenance and relationship to the discovery proposal remain `UNRESOLVED`.

The reported sync-pulse projection retains `type`, `title`, `action_plan`, `estimated_confidence`, `primary_ia` and `secondary_ia`; it drops `proposal_key`, `evidence_refs` and any individual IDs not explicitly copied. Deduplication by title is textual de-duplication, not a stable causal identity.

The current Claude result is `TRACE_ACCEPTED_WITH_LIMITATIONS`: no explicit typed per-proposal adapter was found within the reviewed tracked `IABV_v1.5/src` and `IABV_v1.5/tests` routes. It is not a global absence proof. The possible two-hop `evidence_refs → ExperimentRun → proposal_id/discovery_signal_id` remains `UNRESOLVED`. Full adjudication: [trace final disposition](CHAT-ARCH-2026-10-17-r10-sync-pulse-trace-final-adjudication.md).

## Independent normative blocker

The separate R10 v0.7.2 contract/matrix audit is closed with **`FAIL`**, not PASS. Six payload hashes matched their manifest, but normative contradictions remain:
- D2 open: no clause-vs-oracle precedence; T162 conflicts with clauses §8.3/§12.
- D3 partial: T141 permits correlation without an attested parent relation; T138 adds unspecified expiry.
- D4 partial: T130/T131 add uncontracted strategy-lineage semantics.
- D6 partial: undefined vocabulary, mismatched error codes/status writers.
- 21 test-matrix rows lack explicit expected outcomes; T180's exact deadline boundary lacks a declared result.
- Atomicity and implementation dependencies remain `UNPROVEN`; all 74 cases T123–T196 are `NOT_RUN`.

Repairs M0–M5 are proposed only; no v0.7.3 exists. Full report: [R10 v0.7.2 audit closure](CHAT-ARCH-2026-10-17-r10-v072-audit-closure-fail.md).

This separate FAIL is not proof that the discovery/sync-pulse code has a particular bug, but it is a hard specification readiness blocker for any implementation that depends on this v0.7.2 contract/matrix.

## Bridge readiness gates

Do not mark the bridge ready until the relevant gates are satisfied by an authorized, evidence-backed process:

| Gate | Required property | Current state |
|---|---|---|
| G1 — Objective/semantics | Decide whether downstream proposals must carry individual causal attribution or are explicitly aggregate-derived, with no individual attribution claim. | `UNRESOLVED` |
| G2 — Canonical typed identity | Keep signal, proposal, experiment, run, candidate/tool and execution-attempt identifiers as distinct typed namespaces; no aliasing of an experiment/run ID into candidate identity. | Partial path reported; semantic candidate identity unresolved. |
| G3 — Reference resolution | Every `evidence_refs`/support reference resolves in its declared namespace and is checked against proposal, candidate/tool, domain/subject, configuration and evidence role. | `UNRESOLVED` for the potential OSES two-hop. |
| G4 — Downstream contract | Either preserve typed identity across OSES→sync-pulse, or explicitly create a new aggregate-derived proposal identity with its cohort/window/source-snapshot provenance and no false individual attribution. | Not evidenced as a complete contract. |
| G5 — Decision/side-effect gate | A governance/authorization gate must be enforced before every side effect; health checks or confidence/title filters alone do not establish authorization. | Not established by supplied trace. |
| G6 — Execution attestation | Record authorized actor, attempt/execution ID, exact candidate/config/scope, terminal result and independently checked postconditions. | `UNPROVEN` |
| G7 — Neutrality/idempotency/recovery | Sandbox evidence stays out of operational success/failure and training metrics except in a separately defined cohort; stable event identity, duplicate handling, correction/retraction and atomicity have an agreed contract. | v0.7.2 `FAIL`; implementation `UNPROVEN`. |
| G8 — Verification | A corrected normative contract, discriminating tests and independent delta review exist; tests are run only under separate authorization. | Not satisfied; all matrix tests `NOT_RUN`. |
| G9 — Governance | Explicit owner authorization for any implementation or runtime action, separately from documentary acceptance. | `KEEP_BLOCKED`; no authorization. |

## Recommended next route — no deviation

1. **Do not reopen** the already accepted broad discovery/sync-pulse trace. Keep its result `TRACE_ACCEPTED_WITH_LIMITATIONS`.
2. **Owner decision:** return M0–M5 from R10 v0.7.2 to the package author for documentary correction. This is recommended because the current normative matrix can permit behavior its contract forbids. No authoring/implementation has been performed here.
3. After a corrected package exists, request one independent **delta review** against the FAIL record; do not re-audit all historical sources or infer v0.6 equivalence.
4. Separately, only if individual causal attribution is a required objective, run one last targeted static check of the producer of the recommendation consumed by `_validated_improvements` and the declared lookup/namespace for `supporting_run_ids`, `last_experiment_id`, and `best_run.run_id`. Do not broaden the search or inspect `data/`/SQLite.
5. Only after the contract and identity semantics are settled may a bridge design be assessed for implementation readiness. Implementation and runtime remain unauthorized.

## Evidence/provenance protocol

- `CODEX_LOCAL_REPORTED / OWNER_REPORTED`: local checkout and reported worktree source observations.
- `WORKTREE_SOURCE`: reported source in locally modified paths.
- `HEAD_SOURCE`: unmodified relative to the reported local HEAD, not the same as public main.
- `GITHUB_API_VERIFIED`: only source/doc objects actually fetched from the specified public ref.
- `NOT_FOUND`: not found in the stated search scope; never global absence unless the search protocol justifies it.
- `UNRESOLVED`: an edge not decided by available evidence.
- `NOT_RUN`: a test exists/documented, but was not executed.

Public base for PR #467 is `9e0ce66768aedd7422e0d3551affd398f44a7532`; reported local checkout HEAD is `3926b1144bb23c1066db579da711d3cdbc1611df`. They are different refs. Claude's accepted trace review consumed the report from GitHub but did not inspect the source code or Windows checkout itself.

No source code or tests were changed by this assessment. No product code/tests/build/runtime/probes were executed. No `data/`, SQLite or M0A inspection.

**Final state:** `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
