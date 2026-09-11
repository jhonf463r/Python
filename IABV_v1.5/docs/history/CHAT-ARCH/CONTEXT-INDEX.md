# IABV v1.5 — CHAT-ARCH Context Index

## FUNCTION

This is the **objective-driven retrieval map** for historical IABV knowledge.

The operational protocol is defined in `MEMORY-OPERATING-PROTOCOL.md`.

A future chat must not start by reading the archive chronologically. It should start from the new objective, map that objective to one or more knowledge domains below, inspect the cited source records, then reconcile the activated history against the current source/branch/runtime state.

## RETRIEVAL ALGORITHM

```text
NEW OBJECTIVE
  ↓
IDENTIFY CLAIMS / BOUNDARIES / RISKS IMPLIED BY THE OBJECTIVE
  ↓
MATCH OBJECTIVE TO DOMAINS BELOW
  ↓
READ README + MEMORY-OPERATING-PROTOCOL + CURRENT-STATE
  ↓
READ ONLY THE MOST RELEVANT SOURCE ARCHIVES
  ↓
RECONCILE HISTORICAL CLAIMS AGAINST CURRENT GITHUB STATE
  ↓
ACTIVATE RELEVANT FAILURES + NEGATIVE KNOWLEDGE + UNIMPLEMENTED IDEAS
  ↓
ACTIVATE RELEVANT CROSS-IA TRANSFERS / CAPABILITY EVIDENCE
  ↓
IDENTIFY CURRENT GATE + LAST VERIFIED STATE
  ↓
SELECT MINIMAL DISCRIMINATING NEXT ACTION
```

## DOMAIN ROUTING

| Domain / objective | Activate first | Also inspect | Key questions |
|---|---|---|---|
| Cognitive control plane / external-agent cognition | `CURRENT-STATE.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md` | R5 cognitive records, multi-tool/metacognition records | Does IABV context causally change a real agent decision? Is the loop closed? |
| Cross-chat continuity / operational memory | `MEMORY-OPERATING-PROTOCOL.md`, `README.md`, `ARCHIVE-REGISTRY.md` | CACP continuity, knowledge-sync, all continuity-tagged records | Can a new chat reconstruct only the relevant state from GitHub? |
| P0-B authority / provenance / security | `CURRENT-STATE.md` | P0.213 authority/trust records, P0-B records, current P0-B branch evidence | Is legitimate authority independently bound to trust root, identity, runtime and invocation? |
| AdaptiveSession provenance / replan lineage | `CURRENT-STATE.md` | provenance records and `aa3ff2c2` history | Are typed fields actually canonical in runtime decisions, or only persisted mirrors? |
| R3 / Devin adapter / tool execution | `CURRENT-STATE.md` | R5/R3 loopback records and current test evidence | Does the production path select and invoke the adapter rather than bypassing it? |
| Runtime/bootstrap/provenance | `CURRENT-STATE.md` | runtime-integration, Windows forensic, cognitive symbiosis records | Is the exact intended commit actually running? Is package origin/workspace/runtime aligned? |
| Evidence adequacy / verification | `CURRENT-STATE.md` | adaptive-evidence, persistence and deletion records | What does evidence actually prove, and what remains merely asserted? |
| Scientific metacognition / prediction / calibration | `CURRENT-STATE.md` | multi-tool scientific metacognition, resource/metacognition records | Are predictions made before execution and calibrated against later outcomes? |
| Self-development / autoevolution | `CURRENT-STATE.md`, `UNRESOLVED-KNOWLEDGE.md` | cognitive metabolism, self-operation, lifecycle/autoevolution, authority records | Is self-modification or learning causally proven and legitimately governed? |
| Architecture-to-runtime construction | `CURRENT-STATE.md` | architecture-to-runtime construction history | Which architectural claims are actually implemented and runtime proven? |
| Windows runtime / hardening | `CURRENT-STATE.md` | Windows forensic and P0-B records | What security claims survive adversarial Windows execution? |
| Historical deletion safety | `README.md`, `ARCHIVE-REGISTRY.md`, `UNRESOLVED-KNOWLEDGE.md` | persistence verification + deletion-gate records | Is the knowledge reconstructible remotely, or is the chat still needed? |
| Cross-IA capability selection | `SYMBIOSIS-MAP.md`, `MEMORY-OPERATING-PROTOCOL.md` | records containing disagreements, corrections and implementation/verification traces | Which available AI capability is strongest for this uncertainty, and where is independent challenge required? |

## CROSS-CUTTING ACTIVATION — ALWAYS CONSIDER WHEN MATERIAL

### Provenance

- exact branch/commit;
- local vs remote distinction;
- workspace/package/runtime fingerprint;
- historical claim vs current verification.

### False positives

Use prior failures as active constraints, not merely historical anecdotes. Recurring examples include test-boundary substitution, provenance drift, constructor-order fallacy, persistence mistaken for learning, signature mistaken for authority, canonical fields that are not behaviorally canonical, and fixed-role symbiosis.

### Negative knowledge

Retrieve what previous experiments proved **not** to prove. This often prevents false closure better than another positive test.

### Ideas without implementation

Search activated history for concepts such as:

`IDEA`, `PROPOSAL`, `FUTURE`, `OPEN`, `UNIMPLEMENTED`, `LATENT`, `LEFT_IN_AIR`, `WITHOUT_TASK`, `CONSEQUENCE`, `QUESTION`, `NEXT_EXPERIMENT`, `LOST_LINK`.

Do not assume ticketed work is the complete knowledge boundary.

### Cross-IA transfer

Retrieve prior disagreements and corrections when the new objective touches the same boundary. Inherit the **method learned**, not an AI's conclusion by reputation.

## RELEVANCE TEST

A historical record is relevant when at least one of the following can materially change today's work:

1. it contains evidence about the same boundary;
2. it contains a prior failed or discriminating experiment;
3. it contains an unresolved contradiction;
4. it contains an unimplemented idea directly applicable to the objective;
5. it defines a provenance/authority invariant needed by the objective;
6. it records how another AI's observation corrected the working model;
7. it establishes the last known gate/blocker for the same subsystem;
8. it changes which AI capability should be used for the objective.

Otherwise do not activate it by default.

## ACTIVATION DEPTH

`Depth 0: README + MEMORY-OPERATING-PROTOCOL + CURRENT-STATE`

`Depth 1: domain routing + symbiosis + unresolved knowledge`

`Depth 2: relevant source records + current GitHub evidence`

`Depth 3: neighboring domains + contradictions + failed experiments`

`Depth 4: broad chronology / full forensic reconstruction only when needed`

## DEEP-RECONSTRUCTION MODE

When the new objective is broad, expand retrieval in layers rather than dumping the complete archive:

`current state → domain syntheses → domain source archives → neighboring domains → historical contradictions → unresolved ideas → raw chronology only if needed`.

## IMPORTANT DISTINCTION

This index is not a static list of tasks. It is a **routing mechanism from present objective to historically relevant knowledge and collaboration capability**.

The routing map must evolve when new work creates boundaries, failure modes, experiments, concepts, cross-IA learning, or new evidence about AI capabilities.
