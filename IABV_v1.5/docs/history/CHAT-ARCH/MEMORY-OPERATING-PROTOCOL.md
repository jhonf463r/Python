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

Defines continuity rules and epistemic boundaries.

### M1 — Objective router

`CONTEXT-INDEX.md`

Maps a current objective to relevant domains and source records.

### M2 — Current operational state

`CURRENT-STATE.md`

Provides the compact reconciled bridge between historical knowledge and current project state.

### M3 — Cross-IA capability and transfer model

`SYMBIOSIS-MAP.md`

Records useful AI capabilities, knowledge transfers, corrections and collaboration patterns.

### M4 — Latent/unresolved knowledge

`UNRESOLVED-KNOWLEDGE.md`

Preserves ideas, deductions, questions, future experiments and strategically important work that never became tickets or commits.

### M5 — Historical source records

All registered `CHAT-ARCH-*`, reconciliation, persistence and forensic records.

These are evidence-bearing historical sources, not merely background reading.

### M6 — Current repository/runtime evidence

Current code, tests, branches, commits, runtime fingerprints and independently observed state.

M6 outranks historical claims when answering what is true **now**.

### M7 — Systemic integrity / connectivity synthesis

`SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`

This layer is the routed synthesis for cross-organ contract integrity, temporal/semantic coherence, duplication/drift detection and the history of which maintenance responsibilities are already present versus fragmented or missing.

M7 is not an authority replacing M6. It is a high-value reasoning aid that tells the next investigation **which existing organs to inspect before creating new architecture**.

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
M5 RELEVANT SOURCE RECORDS OR CANONICAL ABSORPTION
  ↓
M7 SYSTEMIC INTEGRITY SYNTHESIS WHEN MATERIAL
  ↓
M6 CURRENT REPOSITORY / RUNTIME RECONCILIATION
  ↓
ACTIVE CONTEXT PACKET
```

The retrieval result is **not** `all history`. It is the minimum context set whose omission could materially alter the current decision.

## CANONICAL ABSORPTION

A source archive does not have to be directly reachable from `main` to contribute to canonical operational memory.

A branch-only or legacy source may be canonically absorbed when:

1. the source branch/ref and source record are identified;
2. the source was remotely verified or otherwise independently recovered;
3. materially decision-relevant knowledge is explicitly transferred into the canonical memory layer;
4. the transfer preserves the source provenance and does not rewrite the historical source silently;
5. contradictions and unresolved status are preserved;
6. the absorption record itself is remotely readable from canonical `main`.

This allows archival provenance to remain faithful without merging unrelated implementation branches merely to place a historical Markdown file on `main`.

Canonical absorption is therefore an alternative to direct canonical source reachability for the purpose of cross-chat continuity and deletion safety.

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
RELEVANT_SYSTEMIC_INTEGRITY_ORGAN_MAP
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
8. establishes the latest independently verified gate for the same subsystem;
9. changes which AI capability should be selected;
10. identifies an existing organ that can replace a proposed new component, reducing unnecessary architecture creation.

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
systemic connectivity analysis
```

Then select available AIs according to demonstrated capability for that boundary.

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

When the objective touches cross-organ integrity, add M7 here.

### Depth 2 — Evidence

Read the most relevant M5 records **or their canonical absorption record**, then current source/commit evidence.

### Depth 3 — Contradiction reconstruction

Expand into neighboring domains, prior failed experiments and conflicting historical interpretations.

### Depth 4 — Full forensic reconstruction

Read broad chronology only when the objective genuinely requires it or when lower depths leave unresolved contradictions.

## NEGATIVE KNOWLEDGE HAS PRIORITY

When historical evidence says an experiment did not prove a tempting claim, activate that limitation before repeating the experiment.

Examples:

`test pass != production proof`

`receipt != cognition`

`persistence != learning`

`signature != legitimate authority`

`field existence != canonicality`

`repository target != runtime target until proven`

`archive exists != deletion safe`

`event recorded != connection validated`

`local observation != cross-organ coherence`

`recommendation exists != prediction exists`

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
- the collaboration strategy itself;
- the canonical absorption/routing state;
- a cross-organ integrity/contract/temporal/semantic finding;
- the identification of an existing organ that can replace a proposed new component;
- a provenance discrepancy that changes whether evidence can be promoted.

Routine repetition should not generate redundant history.

## SYNTHESIS UPDATE RULE

When new knowledge changes the operational model:

1. preserve the source historical record;
2. update `CURRENT-STATE.md` when current truth changed;
3. update `CONTEXT-INDEX.md` when routing changed;
4. update `SYMBIOSIS-MAP.md` when a capability/interaction lesson changed;
5. update `UNRESOLVED-KNOWLEDGE.md` when latent knowledge changes status;
6. update `CANONICAL-ABSORPTION-2026-09-11.md` when source reachability/absorption status changes;
7. update `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md` when a systemic-integrity finding changes;
8. register new source records in `ARCHIVE-REGISTRY.md`.

Do not silently rewrite historical records to make contradictions disappear.

## EVIDENCE PROMOTION GATE

A report produced by an AI is not automatically evidence at the same level as the artifact it describes.

Before promoting a result to a stronger epistemic state, reconcile:

```text
reported claim
  ↓
reported artifact
  ↓
exact branch/ref
  ↓
exact commit SHA
  ↓
working-tree state, when relevant
  ↓
artifact read-back
  ↓
runtime provenance
  ↓
independent verification
```

If the reported artifact is absent from the cited commit, preserve the discrepancy and downgrade the claim to the highest state actually supported. Do not silently infer that the report used committed code.

## CAUSAL EDGE DISCIPLINE

Treat each meaningful arrow as an independent evidentiary edge.

Examples:

`selection proven != execution proven`

`adapter invoked != authorization accepted`

`authorization accepted != transport transmitted`

`transport transmitted != external effect`

`external effect != independently verified outcome`

`verified outcome != learning`

`learning state != future decision influence`

`future decision influence != behavioral change`

`behavioral change != improvement`

A future investigation should advance to the **first open causal edge**, not restart already closed edges, unless new contradictory evidence appears.

## SYMBIOSIS MEASUREMENT

A cross-IA collaboration is materially successful when it creates an observable delta in the working method/system, not merely agreement.

Track qualitatively or quantitatively where possible:

`ΔK = demonstrated knowledge delta`

`Δπ = policy/method change`

`ΔB = observable behavior change`

`ΔY = observable outcome change`

Agreement among agents is not a proxy for ΔK, Δπ, ΔB or ΔY.

## DYNAMIC MESSAGE ECONOMY

Use the minimum number of external AI interventions required to remove the current material uncertainty.

Do not invoke an agent to repeat an edge already closed with stronger evidence.

Prefer a single actor to combine compatible execution tasks when doing so preserves audit independence and provenance. Split roles when independence or materially different capability is required.

Reserve high-cost/high-reasoning interventions for:

- genuine architectural contradiction;
- policy adjudication under competing valid interpretations;
- higher-order causal ambiguity;
- a failure that cannot be reconciled by the current runtime/source auditor.

## ROLE-ROUTING EXAMPLE — 2026-09-17

For the current causal learning/P0-B frontier:

`ChatGPT → Sonnet → (Opus only if contradiction) → Devin if fix needed → Sonnet re-audit`

This is an example of capability-driven routing, not a permanent sequence.

## REPORT-TO-CANONICAL-STATE RULE

Every material external-agent report that changes the project model should be converted into a structured delta before the next actor is selected.

The conversion should include:

```text
REPORT
→ OBSERVED FACTS
→ CLAIMS
→ EVIDENCE LEVEL
→ PROVENANCE
→ CONTRADICTIONS
→ NEGATIVE KNOWLEDGE
→ KNOWLEDGE DELTA
→ POLICY / ROLE CHANGE
→ NEXT CAUSAL EDGE
```

This prevents the next prompt from accidentally carrying forward assertions as facts.

## MEMORY DECAY / SUPERSESSION

A historical item may become:

`ACTIVE | DORMANT | SUPERSEDED | REFUTED | RESOLVED | RELEVANT_AGAIN`

Status changes require evidence.

A superseded item remains historically accessible because it may explain why the current design exists.

When current code or runtime contradicts an older memory item, do not delete the older item. Mark the older item SUPERSEDED/REFUTED and update the current synthesis, routing and unresolved register as appropriate.

This is the mechanism by which a new architecture state can **replace the active interpretation without losing the lineage that explains the change**.

## DELETION SAFETY

Deletion safety is a **knowledge-preservation gate**, not a technical-task-closure gate.

A chat can be deleted while an engineering task remains OPEN if the open state, failures, evidence boundaries, decisions, provenance, pending experiments and next actions are durably preserved.

For a historical chat, the canonical preservation condition is:

```text
DIRECT_CANONICAL_SOURCE
OR
CANONICAL_KNOWLEDGE_ABSORPTION
```

plus:

```text
PROVENANCE_TO_SOURCE
REMOTE_READBACK
KNOWLEDGE_LOSS_TEST=PASS
BLIND_RECONSTRUCTION=PASS
NO_MATERIAL_KNOWLEDGE_ONLY_IN_CHAT=YES
```

An exact source archive remaining on a non-canonical branch is not, by itself, a deletion blocker when the material knowledge has been canonically absorbed and the source provenance remains recoverable.

Conversely, a technical task being closed does not make a chat deletable if material historical knowledge is still only in the transcript.

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
8. identifies existing organs before proposing new architecture;
9. produces a new knowledge delta;
10. writes that delta back into the appropriate durable layer.

That is the operational definition of **cross-chat continuity** for IABV.

## 2026-09-17 PROTOCOL AMENDMENT — CAUSAL SYMBIOSIS / PROVENANCE

This amendment is active for future chats.

### A. Treat provenance as part of the evidence, not metadata decoration

A claim may not be promoted merely because an AI report contains a SHA. The exact artifact must be recoverable from that SHA/ref, or the report must explicitly identify the uncommitted working-tree state used.

### B. Treat discrepancies as useful state

A contradiction such as:

`reported test exists`

versus

`remote commit does not contain test`

must become an explicit unresolved/provenance item and must affect the next actor's task.

### C. Route by uncertainty, not habit

Before assigning an actor, ask which capability is the bottleneck now:

`architecture | source audit | runtime | controlled experiment | implementation | verification | reconciliation`

Then choose the least redundant capable actor and add an independent challenger only when the claim warrants it.

### D. Advance monotonically through causal edges

Do not repeatedly reprove a closed edge because a new prompt is easier to write that way. Preserve its evidence level and move to the first still-open edge.

### E. Convert reports into durable operational state

After a material report, update current state, routing, capability evidence, unresolved status and source registry as appropriate before starting another cross-IA cycle.

### F. Preserve explicit claim granularity

Future prompts must distinguish at least:

`SOURCE-PROVEN`
`UNIT-TEST-PROVEN`
`INTEGRATION-TEST-PROVEN`
`PRIMARY-RUNTIME-PROVEN`
`INDEPENDENTLY-RUNTIME-VERIFIED`
`NOT PROVEN`
`CONTRADICTED`

Do not use vague closure language such as “basically proven”.

## 2026-09-20/21 PROTOCOL AMENDMENT — METACOGNITIVE SELF-USE

### A. Use IABV itself as the first analyzer for deep self-assessment

When the objective is self-state, architecture, metacognition, causal diagnosis or development acceleration, retrieve the relevant memory and invoke the existing IABV self-observation/metacognition organs before routing immediately to an external AI.

This is not a claim that IABV is correct. It is a deliberate experiment to make IABV a participant in its own method.

### B. Deep self-assessment contract

A valid preflight should attempt:

`objective`
→ depth
→ current reality
→ architecture/code introspection
→ change-surface analysis
→ uncertainty
→ hypotheses
→ discriminating experiment
→ verification boundary
→ first broken edge
→ Knowledge Delta.

### C. Maintain independent verification

For critical claims:

`IABV self-assessment = producer`
and
`independent external audit = verifier`.

Do not allow the self-auditing system to become its own sole evidence authority.

### D. Separate observe from mutate

Preserve:

`OBSERVE → REASON → HYPOTHESIZE → EXPERIMENT → VERIFY → AUTHORIZE → CHANGE → REVERIFY → LEARN`.

Any mutation performed during analysis must be represented as an explicit action and excluded from the pure observation claim.

### E. Add changed-surface analysis

For any material change, search beyond the modified function/file:

`symbol → callers → producers → consumers → contracts → fallbacks → alternate routes → negative cases → downstream effects`.

### F. Distinguish health from metacognition

`system.self_awareness` may report how IABV is doing.

`system.metacognition` should explain why, what is unknown, what changed, what may fail next and what experiment best distinguishes hypotheses.

Do not introduce another brain or intent merely to represent this.

### G. Development-inflection test

The method should only be considered to accelerate when verified experience produces reusable knowledge and a later observable decision/strategy change while routine human coordination decreases.

### H. Cross-IA knowledge transfer

Preserve:

`SOURCE_AI → INTERPRETATION → CHALLENGER → CONTRADICTION/SUPPORT → IMPLEMENTER → OBSERVATION → RECONCILIATION → NEW INVARIANT → METHOD CHANGE`.

The durable object is the changed method, not the agreement or prestige of any model.


