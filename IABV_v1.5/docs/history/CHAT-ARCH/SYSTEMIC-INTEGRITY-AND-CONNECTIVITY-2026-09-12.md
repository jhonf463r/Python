# IABV v1.5 — Systemic Integrity & Connectivity Synthesis

## PURPOSE

This document is the canonical synthesis for the emerging **systemic integrity / organ connectivity** problem discovered during the P040 and UK-15 investigations.

Its purpose is to prevent future chats, IABV self-analysis, and external AIs from restarting the same investigation from zero.

It must be treated as a living knowledge artifact. New evidence may mark parts obsolete, refuted, superseded, or more strongly proven. A later state must never silently erase the historical state that produced the finding.

## CURRENT HIGH-LEVEL MODEL

IABV does **not** start from an empty architecture-integrity layer.

Existing organs already perform substantial pieces of:

- perception and cross-validation;
- operational self-examination;
- source-of-truth and identity registration;
- state aggregation;
- responsibility inference;
- signal reconciliation;
- anomaly detection and correction;
- runtime audit;
- decision recording;
- context assembly;
- discernment and contradiction handling.

The unresolved architectural question is therefore **not** simply "does IABV need a system nervous system?".

The active question is:

> Which parts of systemic integrity already exist, where are they connected, what responsibilities became fragmented during historical evolution, and what minimal missing connection prevents IABV from detecting cross-organ contract drift by itself?

## KNOWN EXISTING ORGANS / ALGORITHMS

The following mechanisms have been identified in prior source/runtime audits:

1. `SystemIdentityRegistry` — subsystem identity/status and dependency-oriented state.
2. `PerceptionCrossValidator` — cross-validates environment observations and reconciles availability inconsistencies.
3. `OperationalSelfExaminationService (OSES)` — recurring operational findings, temporal/anomaly observations, finding deduplication and self-examination.
4. `SelfCodeAnalysis` — source-level analysis such as Python syntax/threading/slot/intent-related checks.
5. `ToolDiscoveryService.reconcile_signals()` — reconciles tool signals with decision history.
6. `CommonSenseEngine` — expected-vs-real anomaly reasoning and corrective actions.
7. `RuntimeAuditTracer` — runtime event/timeline and terminal-state observability.
8. `DecisionAuditTrail` — decision/outcome history with provenance/timestamps.
9. `OrganismStateSnapshot` — unified read-only organism state view.
10. `DiscernmentFrameService` — evidence/sensor/attractor/bias/contradiction framing.
11. `TaskContextAssembler` — contextual aggregation for task execution.
12. `UniversalPerceptionService` — normalization of perception signals.
13. `CodeResponsibilityInferencer` — responsibility inference from code, currently identified mainly in construction tooling.
14. `SystemKnowledgeRegistry` — canonical system-relationship/knowledge registry.
15. `SystemHealthRegistry` — canonical operational-health registry.
16. `ProjectSteeringRegistry` — canonical project-steering state.
17. `CanonicalSourceRegistry` plus claim-verification tooling — source-of-truth and claim verification infrastructure.

## HISTORICAL INTEGRATOR

A historical `UniversalMetacognitiveScanner` existed in an earlier code lineage and was described as a central integrator of metacognitive organs (World Model, environment self-awareness, OSES, ToolRegistry, DecisionAuditTrail and metacognitive evolution).

The active codebase later removed/commented its import, construction and wiring because that module was no longer present in the active tree.

This fact is important but must not be interpreted as an instruction to restore it.

The correct question is what responsibilities were:

- absorbed by existing organs;
- distributed among several organs;
- lost;
- or left only as historical/documentary intent.

## P040 RUNTIME EVIDENCE

A real runtime episode exposed two previously hidden caller/implementation mismatches in the UI chat path.

First failure:

`sendChat()` called `_generate_dispatch_id('chat')` while the active implementation exposed `_new_dispatch_id('chat')`.

After that was corrected, a second runtime failure appeared because `_set_autonomy_activity_override()` imported `utc_now` from `iabv_v15.infra.clock` while the actual function was located in `iabv_v15.domain.models`.

Only after both fixes did the live UI path complete sufficiently to produce an interaction, dispatch, worker activity, terminal cleanup and a contemporary ExperimentRun/Recommendation.

This is direct evidence for the invariant:

`DECLARED REPAIR != EFFECTIVE RUNTIME REPAIR`

and a strong example of contract drift being discovered only after a real path traverses multiple organs.

## UK-15 RUNTIME EVIDENCE

A contemporary ExperimentRun and Recommendation were observed for the real UI request:

- ExperimentRun: `9cf6efb2-f210-41fb-b768-8d0bfaeb2515`
- Recommendation: `d6281ca5-d07c-4ef2-a680-0ca91d85798a`

The reported timestamps show the Recommendation occurring about 28 ms after the ExperimentRun record.

The current forensic conclusion is that `TaskOutcomeRecorder` attempts to use a previous recommendation as a prediction source, but the recommendation generated for the current episode is created later.

This proves a temporal/data-contract mismatch at the currently observed boundary, but it does **not** by itself establish whether the correct long-term contract is:

- pre-execution prediction;
- post-execution recommendation update;
- distinct Recommendation and Prediction contracts;
- or preservation of a genuinely previous recommendation from an earlier episode.

Therefore do not fix UK-15 by simply manufacturing a prediction field.

## REPEATED DRIFT PATTERN

Historical and current evidence contains several examples of a common failure family:

```text
architecture evolves / refactor occurs
        ↓
producer or implementation contract changes
        ↓
consumer retains older assumption
        ↓
partial tests or documentation still pass
        ↓
real path exposes the mismatch
```

Known examples include:

- `_generate_dispatch_id` vs `_new_dispatch_id`;
- `iabv_v15.infra.clock.utc_now` vs `iabv_v15.domain.models.utc_now`;
- `StrategySelector` Recommendation timing vs `TaskOutcomeRecorder` previous-recommendation expectation;
- historical `AssistantCapabilityRegistry.get_profile()` consumer assumption vs actual `all_profiles` interface;
- historical `AccountInventoryEntry.success_count` consumer assumption where that field was absent.

These examples are not automatically one root cause, but together justify investigating **cross-organ contract drift as a first-class systemic phenomenon**.

## CURRENT CAPABILITY MATRIX

This matrix is a working audit result, not a permanently valid score. Scores must be updated when direct source/runtime evidence changes them.

Scoring guideline:

- `0.00` = absent;
- `0.25` = documented/conceptual or very limited;
- `0.50` = implemented;
- `0.75` = implemented and executed/proven on a relevant path;
- `1.00` = runtime-proven and effective for the target claim.

### Duplication

- textual duplication detection: currently not demonstrated;
- structural duplication detection: currently not demonstrated;
- behavioral duplication detection: currently not demonstrated;
- semantic duplication detection: currently not demonstrated;
- responsibility duplication: partial;
- architecture duplication: currently not demonstrated;
- finding deduplication: proven within OSES findings;
- signal reconciliation/deduplication: partial.

### Drift

Currently not demonstrated as a general cross-organ capability:

- stale method names;
- moved-module imports;
- signature drift;
- field/enum drift;
- lifecycle-order drift;
- semantic contract drift.

Existing monitoring can detect some operational strategy/latency degradation, but those are not equivalent to general contract-drift detection.

### Temporal coherence

Existing infrastructure demonstrates:

- latency/outlier monitoring;
- stalled-operation monitoring;
- timestamped audit trails;
- runtime event timelines.

What is not yet demonstrated:

- producer-before-consumer contract checks;
- explicit event-order invariants across organ boundaries;
- causal lineage across producer → consumer → decision → outcome.

### Semantic coherence

Existing capabilities include discernment framing, semantic normalization and perception cross-validation.

Not yet demonstrated:

- general Recommendation-vs-Prediction semantic contract checking;
- general producer/consumer meaning equivalence;
- responsibility equivalence detection for differently named methods/services.

### Provenance/causal continuity

IABV has substantial provenance, audit and state-tracing infrastructure, but the end-to-end claim remains open whenever the question is whether a signal actually changed a downstream decision.

## WHAT THIS MEANS ARCHITECTURALLY

The system is better described as:

```text
many partially connected integrity organs
        ↓
shared observations / registries / audits
        ↓
no demonstrated universal cross-organ contract authority
```

This is stronger and more precise than saying "multiple isolated organs".

Some organs are demonstrably connected; the missing property is **system-wide reconciliation of the relationships themselves**.

## CURRENT SELF-PERCEPTION GAP

IABV can already observe many facts about itself:

- current environment;
- process/window/file state;
- organism state;
- operational findings;
- decision history;
- timestamps;
- task context;
- code-level properties;
- tool signals.

The unresolved question is whether IABV can combine those facts to infer:

> "these two organs are connected, but their contract, timing, semantics or causal relationship is no longer coherent."

That is the target capability to measure before creating any new subsystem.

## CRITICAL METHODOLOGICAL RULE

Do not replace this question with static typing alone.

Static type checking may catch some stale names/signatures, but it does not prove:

- temporal correctness;
- semantic equivalence;
- producer/consumer causality;
- runtime/source alignment;
- learning continuity.

Likewise, do not treat observability as contract validation:

`event recorded != connection validated`

## REQUIRED SYMBIOTIC RETRIEVAL BEHAVIOR

When a future objective touches architecture integrity, runtime drift, self-audit, metacognition, duplication, routing, context continuity, or cross-organ failures, retrieve this document together with:

- `CURRENT-STATE.md`
- `CONTEXT-INDEX.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`
- relevant P040 / UK-15 source records

Then reconcile them against the current repository branch/commit and, when runtime claims matter, the exact runtime fingerprint.

Do not assume this document's current assessment remains valid after subsequent refactors.

## CURRENT NEXT GATE

Before implementing a new contract-coordination mechanism, determine whether an existing organ or combination of organs can already perform the required cross-organ comparison when their outputs are composed.

The next investigation must therefore inspect the actual algorithms and execution boundaries, not merely search for class names.

## UPDATE RULE

Whenever a new audit proves, refutes, supersedes or materially changes any part of this model, update this document and then update the routing/current-state records that point to it.
