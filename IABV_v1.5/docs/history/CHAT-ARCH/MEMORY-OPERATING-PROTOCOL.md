# IABV v1.5 — Operational Memory Protocol

## PURPOSE

This document defines how the GitHub historical layer functions as **operational memory** for IABV across chats and across participating AIs.

It is not a transcript archive and not a second brain. It is the control protocol that turns distributed historical records into objective-conditioned context.

## CORE PROPERTY

Continuity is not:

`old chat → copy old prompt → continue`

Continuity is:

`new objective → discover relevant memory → reconcile with current reality → activate context → select capabilities/roles → act → verify → learn → write back`

The same objective may activate different historical knowledge at different times because the current repository, runtime, evidence state, unresolved risks and available AI capabilities change.

## MEMORY LAYERS

### M0 — Entry contract

`README.md`

Defines the continuity rules and epistemic boundaries.

### M1 — Objective router

`CONTEXT-INDEX.md`

Maps a current objective to relevant domains and source records.

### M2 — Current operational state

`CURRENT-STATE.md`

Provides the compact reconciled bridge between historical knowledge and current project state.

### M3 — Cross-IA capability and transfer model

`SYMBIOSIS-MAP.md`

Records which AI capabilities have historically been useful, how one AI changed another's model, and which collaboration patterns should be reused or rejected.

### M4 — Latent/unresolved knowledge

`UNRESOLVED-KNOWLEDGE.md`

Preserves ideas, deductions, questions, future experiments and strategically important work that never became tickets or commits.

### M5 — Historical source records

All registered `CHAT-ARCH-*`, reconciliation, persistence and forensic records.

These are evidence-bearing historical sources, not merely background reading.

### M6 — Current repository/runtime evidence

Current code, tests, branches, commits, runtime fingerprints and independently observed state.

M6 outranks historical claims when answering what is true **now**.

## OBJECTIVE-CONDITIONED MEMORY RETRIEVAL

A new chat must perform retrieval in this order:

```text
OBJECTIVE
  ↓
BOUNDARY IDENTIFICATION
  ↓
CLAIMS THAT MUST BE TRUE
  ↓
RISKS / FAILURE MODES IMPLIED
  ↓
OBJECTIVE DOMAIN MATCH
  ↓
M1 ROUTING
  ↓
M2 CURRENT STATE
  ↓
M3 SYMBIOSIS / ROLE EVIDENCE
  ↓
M4 UNRESOLVED / LATENT KNOWLEDGE
  ↓
M5 RELEVANT SOURCE RECORDS
  ↓
M6 CURRENT REPOSITORY / RUNTIME RECONCILIATION
  ↓
ACTIVE CONTEXT PACKET
```

The retrieval result is **not** "all history". It is the minimum context set whose omission could materially alter the current decision.

## ACTIVE CONTEXT PACKET

For each new objective, the activated memory should contain:

```text
OBJECTIVE
CURRENT_TRUTH
RELEVANT_HISTORY
RELEVANT_EXPERIMENTS
RELEVANT_FAILURES
NEGATIVE_KNOWLEDGE
RELEVANT_UNIMPLEMENTED_IDEAS
ACTIVE_CONTRADICTIONS
PROVENANCE_REQUIREMENTS
CURRENT_GATE
LAST_INDEPENDENTLY_VERIFIED_STATE
RELEVANT_CROSS_IA_LESSONS
AVAILABLE_CAPABILITY_EVIDENCE
SMALLEST_DISCRIMINATING_NEXT_ACTION
```

If a historical item cannot affect one of those fields, it normally remains inactive unless deep reconstruction is requested.

## RELEVANCE SCORING PRINCIPLE

Do not use a purely lexical match. Historical relevance should be judged by causal usefulness.

A record has high activation priority when it:

1. concerns the same architectural/security/runtime boundary;
2. contains a prior failure that can recur;
3. changes the interpretation of a current claim;
4. identifies a prerequisite or invariant;
5. contains an experiment that discriminates between today's competing hypotheses;
6. contains unimplemented knowledge directly applicable now;
7. records a cross-IA correction that changes the proper method;
8. establishes the latest independently verified gate for the same subsystem.

## TEMPORAL RECONCILIATION

Historical memory is not immutable current truth.

For every material activated claim:

```text
historical claim
    ↓
current source inspection
    ↓
branch/commit provenance
    ↓
runtime evidence when required
    ↓
status = CONFIRMED / SUPERSEDED / REFUTED / UNRESOLVED
```

Never promote a historical claim solely because it appears in multiple archives.

## CROSS-IA SYMBIOSIS AS MEMORY

The system must preserve not only outputs but **knowledge transfer**.

For a material collaboration event, preserve:

```text
SOURCE_AI
→ INITIAL_INTERPRETATION
→ CHALLENGER_AI
→ CONTRADICTION / SUPPORT
→ IMPLEMENTER / EXPERIMENTER
→ OBSERVATION
→ RECONCILIATION
→ NEW INVARIANT
→ FUTURE METHOD CHANGE
```

The important reusable object is the changed method, not the prestige of the AI that produced it.

## DYNAMIC ROLE SELECTION

Historical roles are capability evidence, not permanent assignments.

For each objective, determine which capabilities are needed:

```text
architecture synthesis
source audit
adversarial challenge
implementation
runtime observation
controlled experimentation
provenance adjudication
result verification
```

Then select available AIs according to demonstrated capability for that boundary.

Possible configuration examples:

- one AI may be enough for a low-risk implementation;
- two independent AIs may be required for a critical claim;
- runtime work may favor the agent with real environment access;
- adversarial review may favor the historically strongest challenger;
- broad synthesis may favor the best cross-record reconciler.

Never force every objective through a fixed `ChatGPT → Devin → Claude → Codex` sequence.

## INDEPENDENCE RULE

For a critical claim:

`producer != sole verifier`

An implementation agent should not be the only authority for the claim it created when an independent verification path is available and materially useful.

## MEMORY ACTIVATION DEPTH

Use progressive retrieval:

### Depth 0 — Orientation

Read M0 + M1 + M2.

### Depth 1 — Objective context

Activate M3 + M4 entries directly relevant to the objective.

### Depth 2 — Evidence

Read the most relevant M5 records and current source/commit evidence.

### Depth 3 — Contradiction reconstruction

Expand into neighboring domains, prior failed experiments and conflicting historical interpretations.

### Depth 4 — Full forensic reconstruction

Read broad chronology only when the objective genuinely requires it or when lower depths leave unresolved contradictions.

## NEGATIVE KNOWLEDGE HAS PRIORITY

When historical evidence says an experiment did **not** prove a tempting claim, activate that limitation before repeating the experiment.

Examples:

`test pass != production proof`

`receipt != cognition`

`persistence != learning`

`signature != legitimate authority`

`field existence != canonicality`

`repository target != runtime target until proven`

`archive exists != deletion safe`

## UNIMPLEMENTED KNOWLEDGE MUST STAY VISIBLE

The system must retrieve ideas that were:

- proposed but never implemented;
- discussed without a ticket;
- inferred but never validated;
- rejected temporarily rather than permanently;
- left as future experiments;
- identified as architectural consequences;
- identified as lost links between subsystems.

Implementation status must not determine knowledge preservation.

## DECISION LOOP

Once context is activated:

```text
ACTIVE CONTEXT
  ↓
HYPOTHESIS / CLAIM
  ↓
EVIDENCE REQUIREMENT
  ↓
MINIMAL DISCRIMINATING ACTION
  ↓
OBSERVATION
  ↓
INDEPENDENT VERIFICATION
  ↓
RECONCILIATION
  ↓
DECISION
  ↓
KNOWLEDGE DELTA
```

Do not perform broad work merely because broad history exists.

## KNOWLEDGE WRITEBACK

Write back only material deltas.

A new historical update is warranted when the session creates or changes:

- a proven/refuted claim;
- an evidence boundary;
- a failure mode;
- an experiment and its result/limits;
- an architectural deduction;
- a decision/rejected option;
- a provenance relationship;
- a current gate;
- a strategically relevant unresolved idea;
- a cross-IA learning transfer;
- the collaboration strategy itself.

Routine repetition should not generate redundant history.

## SYNTHESIS UPDATE RULE

When new knowledge changes the operational model:

1. preserve the source historical record;
2. update `CURRENT-STATE.md` when current truth changed;
3. update `CONTEXT-INDEX.md` when routing changed;
4. update `SYMBIOSIS-MAP.md` when a capability/interaction lesson changed;
5. update `UNRESOLVED-KNOWLEDGE.md` when an idea becomes newly relevant, resolved, superseded or refuted;
6. register any new source record in `ARCHIVE-REGISTRY.md`.

Do not silently rewrite historical records to make contradictions disappear.

## MEMORY DECAY / SUPERSESSION

A historical item may become:

`ACTIVE | DORMANT | SUPERSEDED | REFUTED | RESOLVED | RELEVANT_AGAIN`

Status changes require evidence.

A superseded item remains historically accessible because it may explain why the current design exists.

## CHAT-TO-CHAT CONTRACT

A new chat must be able to enter IABV with only:

```text
CURRENT OBJECTIVE + GITHUB ACCESS
```

and reconstruct the relevant operational memory without requesting the previous transcript.

The previous transcript is supplemental evidence, not a mandatory dependency.

## SUCCESS CONDITION

This memory architecture is successful only when a genuinely new chat:

1. identifies its objective;
2. discovers the relevant historical domains itself;
3. activates the right history without a universal dump;
4. reconstructs the current gate and provenance;
5. inherits prior negative knowledge and unimplemented ideas;
6. selects roles/capabilities according to the current uncertainty;
7. avoids repeating obsolete work;
8. produces a new knowledge delta;
9. writes that delta back into the appropriate durable layer.

That is the operational definition of **cross-chat continuity** for IABV.
