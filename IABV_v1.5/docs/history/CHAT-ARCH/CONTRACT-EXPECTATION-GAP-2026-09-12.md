# IABV v1.5 — Contract Expectation Gap / Generalization Audit

## STATUS

**State:** RECONCILED AFTER DEVIN + CLAUDE + UK-15 RUNTIME FORENSICS
**Date:** 2026-09-12
**Purpose:** preserve the current evidence about the transition from narrow local contract checks to generalized cross-organ integrity verification.

## CURRENT VERDICT

The active leading gap is **MISSING_EXPECTATION_MODEL**.

This is not equivalent to saying that IABV has no contract verification.

A real narrow precedent exists:

`SelfCodeAnalysis.verify_intent_routing()`

It implements a limited pattern:

`EXPECTATION → DISCOVER ACTUAL → COMPARE → DETECT`

but its expectations are hardcoded, its scope is narrow, and it is tied to intent-routing/handler semantics.

Therefore the current architectural hypothesis is:

> IABV may need a generalized representation of expectations/contracts before its existing integrity organs can be composed into general cross-organ verification.

This remains a **leading hypothesis**, not yet an implementation authorization.

## KEY EVIDENCE

### 1. Four previously overdeclared registries are not current organs

Direct reconciliation established that these names are not present in the current code:

- `SystemKnowledgeRegistry`
- `SystemHealthRegistry`
- `ProjectSteeringRegistry`
- `CanonicalSourceRegistry`

Treat them as historical/documentary unless new source evidence proves otherwise.

### 2. P040

Real runtime execution exposed two stale source/consumer assumptions that had escaped prior checks:

- `_generate_dispatch_id()` vs `_new_dispatch_id()`
- `iabv_v15.infra.clock.utc_now` vs `iabv_v15.domain.models.utc_now`

These are historical/resolved defects. Their architectural value is evidence for:

`DECLARED/STATIC ASSUMPTION != EFFECTIVE RUNTIME REALITY`

They do not prove that every form of contract verification is absent.

### 3. UK-15

The real P040 ExperimentRun:

- run `9cf6efb2-f210-41fb-b768-8d0bfaeb2515`
- domain `language`
- subject `general`
- run timestamp `2026-09-12T23:20:19.716220Z`

used a real previous recommendation from April. The new recommendation was generated after the run and represents a future-facing update.

Therefore:

`R_prev → prediction → Run_N → R_new`

is the correct lifecycle. The earlier interpretation of `Run_N → R_new` as a temporal contract bug is superseded.

The five-month age of `R_prev` is not, by itself, a retrieval or lifecycle bug. The observed route mismatch was part of prediction-vs-actual evaluation, not proof of a broken recommendation lifecycle.

### 4. `verify_intent_routing()`

This is a genuine partial seed for contract verification.

It uses a curated expectation list and checks actual source definitions/wiring. It reaches detection for a narrow producer/consumer relationship.

It does not provide a generalized model for:

- arbitrary call-sites;
- arbitrary imports;
- dataclass fields/types;
- runtime event contracts;
- lifecycle ordering;
- semantic contracts;
- episode lineage;
- runtime-vs-source reconciliation.

## IMPORTANT ARCHITECTURAL DISTINCTION

The current gap should not be described as:

> "No contract verification exists."

It should be described as:

> "No generalized expectation/contract representation and cross-organ composition capability is demonstrated."

The distinction is important because a new coordinator could duplicate existing responsibilities.

## CURRENT CAPABILITY MODEL

```text
individual integrity organs
        ↓
partial local contract guards
        ↓
shared observations / source inspection / runtime traces
        ↓
NO GENERALIZED EXPECTATION MODEL DEMONSTRATED
        ↓
NO GENERALIZED CROSS-ORGAN CONTRACT VERIFICATION DEMONSTRATED
```

## MAIN BOTTLENECK

**MISSING_EXPECTATION_MODEL**

Current expectations can live implicitly in:

- hardcoded test cases;
- method names;
- import statements;
- data structures;
- lifecycle assumptions;
- runtime assumptions;
- naming conventions;
- tests.

The system lacks a demonstrated general representation that can express:

- producer;
- consumer;
- artifact/data being transferred;
- expected contract;
- actual contract;
- contract type;
- temporal invariant;
- semantic invariant;
- provenance/episode identity;
- verification evidence.

## PROBES REPORTED BY DEVIN

The following probes showed that relevant local information exists but is not generally composed into effective contract verification:

1. `TaskContextAssembler.build_perception_snapshot` → `AdaptiveTaskOrchestrator`
2. import of `utc_now` → `domain.models`
3. `ExperimentRun` → `TaskOutcomeRecorder`
4. `RuntimeAuditTracer.trace_causal_event` → consumer call-site
5. `StrategySelector.recommend` → `ExperimentLab`
6. previous recommendation → current `ExperimentRun` lifecycle

Most have source-level discovery but no generalized expectation, composition, detection, diagnosis or reconciliation path.

## WHAT IS ACTUALLY PROVEN

### IABV CAN SELF-DETECT

- intent-routing handler absence/wiring problems;
- MCP tool registration issues;
- missing QML slot decorators;
- Python syntax errors;
- stale remote branches;
- selected latency anomalies/regressions/stalls;
- selected tool-availability inconsistencies;
- selected decision/strategy degradation.

### IABV DOES NOT YET DEMONSTRATE GENERAL SELF-DETECTION OF

- arbitrary method rename drift across consumers;
- arbitrary import-location drift;
- signature drift across arbitrary boundaries;
- field/enum drift;
- arbitrary producer-consumer lifecycle violations;
- semantic contract drift;
- generalized cross-file relationship drift;
- generalized runtime-to-source contract drift;
- causal continuity across producer → consumer → decision → outcome.

## CURRENT ARCHITECTURAL QUESTION

Before implementation, determine whether the missing expectation model can be represented using existing IABV structures or whether a genuinely new representation is necessary.

The question is NOT yet:

> "How do we implement a ContractCoordinator?"

The correct question is:

> "What is the smallest representation of an expectation/contract that allows existing IABV organs to expose and verify relationships without duplicating their responsibilities?"

## CURRENT NEXT GATE

The next step is **design-only analysis** of the expectation/contract representation.

It must inspect existing models and records first, and determine whether any current type, dataclass, registry, context object, audit record, claim structure, or other artifact can serve as the seed.

NO implementation yet.

## METHOD

Use the following evidence ladder:

`CURRENT SOURCE → REAL RUNTIME → EXECUTED TEST → HISTORICAL RECORD → AI INFERENCE`

Do not convert an architectural hypothesis into an implementation requirement without evidence.

## ACTIVE INVARIANTS

- `DECLARED STATE != EFFECTIVE STATE`
- `TEST PASS != RUNTIME PROOF`
- `event recorded != connection validated`
- `timestamp exists != temporal contract validated`
- `local guard != generalized contract verification`
- `persistence != learning`
- `context available != context influenced decision`

## SYMBIOTIC RETRIEVAL

Future objectives involving architecture integrity, contract drift, cross-organ connectivity, self-audit, duplication, runtime/source reconciliation, or expectation modeling should retrieve this record together with:

- `CURRENT-STATE.md`
- `CONTEXT-INDEX.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`
- `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`
- relevant P040 and UK-15 records

Then reconcile all claims against current code and runtime.
