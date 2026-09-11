# IABV v1.5 — CHAT-ARCH Context Index

## FUNCTION

This is the **objective-driven retrieval map** for historical IABV knowledge.

A future chat must not start by reading the archive chronologically. It should start from the new objective, map that objective to one or more knowledge domains below, inspect the cited source records, then reconcile the activated history against the current source/branch/runtime state.

## RETRIEVAL ALGORITHM

```text
NEW OBJECTIVE
  ↓
IDENTIFY CLAIMS / BOUNDARIES / RISKS IMPLIED BY THE OBJECTIVE
  ↓
MATCH OBJECTIVE TO DOMAINS BELOW
  ↓
READ PRIMARY SYNTHESIS RECORDS
  ↓
READ ONLY THE MOST RELEVANT SOURCE ARCHIVES
  ↓
RECONCILE HISTORICAL CLAIMS AGAINST CURRENT GITHUB STATE
  ↓
ACTIVATE RELEVANT FAILURES + NEGATIVE KNOWLEDGE + UNIMPLEMENTED IDEAS
  ↓
IDENTIFY CURRENT GATE + LAST VERIFIED STATE
  ↓
SELECT MINIMAL DISCRIMINATING NEXT ACTION
```

## DOMAIN ROUTING

| Domain / objective | Activate first | Also inspect | Key questions |
|---|---|---|---|
| Cognitive control plane / external-agent cognition | `CURRENT-STATE.md`, `SYMBIOSIS-MAP.md` | `CHAT-ARCH-2026-09-11-001-cognitive-symbiosis.md`, `...cognitive-control-plane-p0b-symbiosis.md`, `2026-09-03_CHAT-ARCH-2026-011_multi-tool-scientific-metacognition-coordination.md` | Does IABV context causally change a real agent decision? Is the loop closed? |
| Cross-chat continuity / historical memory | `README.md`, `ARCHIVE-REGISTRY.md` | `2026-09-03_CHAT-ARCH-2026-010_cacp-local-scientific-continuity.md`, `2026-09-03_conversation_knowledge_sync.md`, all records tagged continuity | Can the next chat reconstruct the relevant state without the previous transcript? |
| P0-B authority / provenance / security | `CURRENT-STATE.md` | P0.213 authority/trust records, P0-B/cognitive-control-plane record, current P0-B branch evidence | Is legitimate authority independently bound to trust root, identity, runtime and invocation? |
| AdaptiveSession provenance / replan lineage | `CURRENT-STATE.md` | current provenance records and `aa3ff2c2` history | Are typed fields actually canonical in runtime decisions, or only persisted mirrors? |
| R3 / Devin adapter / tool execution | `CURRENT-STATE.md` | R5/R3 loopback records and current test evidence | Does the production path select and invoke the adapter rather than bypassing it? |
| Runtime/bootstrap/provenance | `CURRENT-STATE.md` | `...runtime-integration-and-stabilization.md`, `...0903-001_p0213-phase3-windows-runtime-forensic.md`, cognitive symbiosis record | Is the exact intended commit actually running? Is package origin/workspace/runtime aligned? |
| Evidence adequacy / verification | `CURRENT-STATE.md` | `...007_adaptive-evidence-adequacy-and-forensic-continuity.md`, persistence/deletion records | What does the evidence actually prove, and what remains merely asserted? |
| Scientific metacognition / prediction / calibration | `CURRENT-STATE.md` | `...011_multi-tool-scientific-metacognition-coordination.md`, resource/metacognition records | Are predictions made before execution and calibrated against later outcomes? |
| Self-development / autoevolution | `CURRENT-STATE.md` | cognitive metabolism, self-operation, lifecycle/autoevolution, authority/execution records | Is a self-modification or learning claim causally proven and legitimately governed? |
| Architecture-to-runtime construction | `CURRENT-STATE.md` | `...0903-002_iabv-architecture-to-runtime-construction.md` | Which architectural claims are actually implemented and runtime proven? |
| Windows runtime / hardening | `CURRENT-STATE.md` | Windows forensic and P0-B records | What security claims survive adversarial Windows execution? |
| Historical deletion safety | `README.md`, `ARCHIVE-REGISTRY.md` | persistence verification + GitHub deletion-gate records | Is the knowledge reconstructible remotely, or is the chat still needed? |

## CROSS-CUTTING ACTIVATION — ALWAYS CONSIDER

Regardless of objective, activate these only when materially relevant:

### Provenance

- exact branch/commit;
- local vs remote distinction;
- workspace/package/runtime fingerprint;
- historical claim vs current verification.

### False positives

Use prior failures as active constraints, not merely historical anecdotes. Important recurring examples include test-boundary substitution, provenance drift, constructor-order fallacy, persistence mistaken for learning, signature mistaken for authority, and canonical fields that are not behaviorally canonical.

### Negative knowledge

Retrieve what previous experiments proved **not** to prove. This is often more valuable than another positive test because it prevents repeating the same false closure.

### Ideas without implementation

Search the activated history for:

`IDEA`, `PROPOSAL`, `FUTURE`, `OPEN`, `UNIMPLEMENTED`, `LATENT`, `LEFT_IN_AIR`, `WITHOUT_TASK`, `CONSEQUENCE`, `QUESTION`, `NEXT_EXPERIMENT`.

A future chat must not assume that only ticketed work matters.

### Cross-IA transfer

Retrieve prior disagreements and corrections when the new objective touches the same boundary. The point is to inherit the **method learned**, not to blindly inherit one AI's conclusion.

## RELEVANCE TEST

A historical record is relevant when at least one of the following can materially change today's work:

1. it contains evidence about the same boundary;
2. it contains a prior failed or discriminating experiment;
3. it contains an unresolved contradiction;
4. it contains an unimplemented idea directly applicable to the objective;
5. it defines a provenance/authority invariant needed by the objective;
6. it records how another AI's observation corrected the working model;
7. it establishes the last known gate/blocker for the same subsystem.

Otherwise do not activate it by default.

## DEEP-RECONSTRUCTION MODE

When the new objective is broad (for example, "audit the whole cognitive architecture"), expand retrieval in layers:

`current state → domain syntheses → domain source archives → neighboring domains → historical contradictions → unresolved ideas → raw chronology only if needed`.

This prevents context flooding while retaining a path to the full record.

## IMPORTANT DISTINCTION

This index is not a static list of tasks. It is a **routing mechanism** from present objective to historically relevant knowledge.

The routing map must evolve when new work creates new boundaries, failure modes, experiments, concepts, or cross-IA learning.
