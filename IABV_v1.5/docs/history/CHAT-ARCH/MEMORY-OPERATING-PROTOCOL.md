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
## 2026-09-21 PROTOCOL ADDENDUM — STRATEGIC IDEAS MUST BECOME RETRIEVABLE WORK

When a conversation identifies a material unimplemented capability that can advance the project objective, do not leave it only in the transcript.

Persist it in the appropriate canonical layer:
- `UNRESOLVED-KNOWLEDGE.md` for the reasoning and uncertainty;
- `data/evolution/backlog.json` for an executable pending task with priority and dependencies;
- `CONTEXT-INDEX.md` when retrieval/routing changes;
- a dated roadmap when multiple pending ideas require dependency-aware prioritization.

A task entering the backlog is not evidence that its premise is proven. The backlog records an actionable hypothesis or known gap and must retain its evidence basis.

## 2026-09-21 PROTOCOL ADDENDUM — SELF-ASSESSMENT MODE

When the objective is to understand IABV itself, the default reasoning mode becomes:

`objective → selective memory activation → exact repository/runtime reconciliation → native self-assessment → uncertainty map → code/architecture introspection → first open causal edge → smallest discriminating experiment → capability-fit routing → independent verification → Knowledge Delta`.

Do not treat IABV's own report as self-verifying.

Preserve:
`self-awareness ≠ systemic metacognition`
`organ exists ≠ integrated circuit`
`deep introspection ≠ causal learning`
`metacognitive report ≠ future decision change`.

## 2026-09-21 PROTOCOL ADDENDUM — REMOTE PROVENANCE GATE

For every external-agent report that claims a material modification, require before auditor handoff:

`REPORT → ARTIFACT → exact branch/ref → exact SHA → relevant working-tree provenance → remote read-back → claimed content present → runtime provenance when applicable → independent verification`.

Minimum remote gate:
1. SHA resolves remotely;
2. branch/ref contains that SHA;
3. changed file exists in the remote tree;
4. remote content contains the claimed change;
5. any claimed runtime artifact is tied to the exact tested revision.

If any gate fails:
- do not promote the implementation claim;
- do not ask another actor to audit a nonexistent object;
- preserve the provenance contradiction as negative knowledge;
- route only to artifact recovery/publication.

A successfully published artifact closes provenance identity, not runtime truth or causal closure.

## 2026-09-21 PROTOCOL ADDENDUM — FIRST OPEN EDGE DISCIPLINE

Once a claim reaches a stronger evidence state, advance only to the first still-open causal edge.

For I0 M3 this currently means:
`remote artifact verified → independent M3 audit`
then, only if valid:
`real Windows runtime`
then:
`observed external behavior`
then:
`independent verification`.

Do not restart earlier archaeology or conflate unit/mutation evidence with runtime evidence.

## 2026-09-21 PROTOCOL ADDENDUM — LINEAGE-SCOPE RECONCILIATION

For every material commit used as evidence, distinguish two scopes:

1. **Immediate commit scope**
`direct parent → target commit`

2. **Narrative/historical scope**
`named baseline → target commit`

Both must be reconciled when the claim depends on continuity from the older baseline.

Promotion rule:
- If immediate scope is test-only but cumulative scope contains production changes, state both facts.
- Never use a commit message such as "production source unchanged" as proof of ancestry-wide immutability.
- If a test is independently valid at the exact target SHA, it may close the tested property at that SHA even when the branch lineage is not minimal relative to an older baseline.
- Generalization across revisions requires additional evidence.

This becomes part of the evidence promotion gate:
`claim → target SHA → direct parent → historical baseline → cumulative diff → exact source/test at target`.



## 2026-09-21 PROTOCOL ADDENDUM — BIOSOFÍA ARTIFICIAL / DEVELOPMENTAL SUBSTRATE

For objectives touching biosofía artificial, artificial life, autoconstrucción, autoevolución, digital organisms, developmental robotics, generational learning or recursive capability growth, treat the canonical developmental thesis as an objective-conditioned research source:

`IABV_v1.5/docs/history/CHAT-ARCH/BIOSOFIA-ARTIFICIAL-DEVELOPMENTAL-AUTOPOIETIC-THESIS-2026-09-21.md`

Activate it after current-state orientation and before implementation planning.

Use the following reasoning model:

`
objective
→ developmental level
→ current substrate
→ existing organ capability
→ first open causal edge
→ minimum discriminating experiment
→ independent verification
→ Knowledge Delta
→ next developmental cycle
`

The biological analogy must remain a hypothesis generator, never evidence by itself.

Preserve these distinctions:

`
automation != development
memory != learning
learning != heredity
persistence != reproduction
reproduction != evolution
cooperation != higher-level individuality
many organs != integrated organism
complexity != open-ended evolution
self-modification != self-construction
`

Before introducing new architecture, perform organ/contract archaeology and determine whether an existing composition already supplies the required developmental function.

For critical developmental claims, require:

`
report
→ artifact
→ exact revision
→ runtime provenance
→ observation
→ independent verification
→ causal attribution
`

The development target is not uncontrolled self-modification. It is governed, observable, reversible acquisition and organization of new capabilities.

## 2026-09-21 PROTOCOL ADDENDUM — GLOBAL DEVELOPMENT CONTINUITY

For objectives involving biosofía artificial, autonomous development, scientific self-analysis, developmental acceleration, or reduction of routine human coordination, activate first:

`00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md`

Then reconcile `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md`, the relevant biosofía thesis/roadmap, and the exact current branch/SHA/runtime.

The strategic objective is not unrestricted autonomy. It is to make verified experience causally reusable while progressively removing routine human transport from the loop and preserving governance, security and independent verification.

Scientific-organ rule: do not create a new coordinator merely because scientific functions are distributed. First trace existing producer→consumer edges and determine whether the missing boundary is ownership, wiring, invocation, observation or causal effect.

Development-inflection rule: “exponential” is a research hypothesis. Promote it only after longitudinal evidence of compounding verified capability generation per unit of routine human coordination.



## 2026-09-28 — REPORT-CONTINUATION / SPACE-TIME PROVENANCE RULE

A previous actor's final response is an **observation/report**, not automatically the current causal frontier.

Before continuing its suggested next step, reconcile the response against the full provenance chain:

`report → artifact → branch/ref → SHA → working-tree provenance → remote read-back → runtime provenance → independent verification → reconciliation → Knowledge Delta → next decision/writeback`.

Maintain separate statuses for:

- implementation claimed;
- implementation locally present;
- implementation committed;
- implementation remotely attributable;
- runtime reported;
- runtime independently verified;
- causal edge closed.

Special failure pattern:

**response-continuation drift** = following the previous actor's proposed next edge while skipping an unresolved provenance/evidence edge.

Required behavior:

1. Re-anchor to the exact objective and technical baseline.
2. Verify whether the reported branch/ref/SHA is actually resolvable.
3. Determine whether the implementation is committed or only in a modified worktree.
4. Verify artifact/source read-back before treating implementation as canonical.
5. Route to an independent verifier only after an attributable artifact exists.
6. Do not advance semantic research merely because the implementation actor named it as the “first open edge”.

For META-01-E2a this means:

`Devin implementation report → publication/read-back → Sonnet verification → semantic E2b`

not:

`Devin implementation report → immediately investigate hypothesis/prediction`.



## 2026-09-28 — POST-COMMIT COVERAGE RULE

Remote commit attribution closes only the **artifact identity** edge.

After publication, the next verifier must test whether the implementation actually covers the claim:

`source wiring ≠ effective consumer behavior`
`helper-level identity ≠ production-consumer identity`
`runtime creation ≠ runtime consumption`
`one runtime frame ID ≠ another runtime frame ID`

A verifier must reconcile code, tests and runtime evidence in temporal order and keep separate execution identities unless provenance explicitly joins them.



## 2026-09-29 — INTEGRATION-FRONTIER ROUTING RULE

When an independent verifier closes source/object-level evidence but cannot execute the target environment, route the next action to the actor with the missing environmental capability.

Do not:
- repeat the same lower-level verification;
- treat an unavailable target environment as closure;
- follow the previous implementation actor's semantic next edge prematurely.

For META-01-E2a:

`Sonnet object-level verification`
→ `Devin Windows production verification`
→ `ChatGPT reconciliation`
→ `E2b semantic investigation`.

This preserves capability-fit and the spatial/temporal provenance chain.



## 2026-09-28 — NON-DESTRUCTIVE RETRY RULE FOR BLOCKED VERIFICATION

When a verification actor is blocked by repository/worktree topology or command permissions, adapt the experimental environment without changing the epistemic target.

Prefer:
`new detached worktree at exact target SHA`

over:
`destructive cleanup of an existing verification worktree`.

Classify infrastructure interruption separately from software evidence. Never treat an aborted runtime attempt as a negative software result.
\n\n## 2026-09-29 PROMPT-GENERATION / FRONTIER-DRIVEN ACTOR ROUTING

Every new actor prompt must be generated from the **current causal/evidential frontier**, not copied from the previous agent's proposed continuation.

Required derivation:

```
OBJECTIVE
→ RELEVANT MEMORY
→ CURRENT VERIFIED TRUTH
→ CLOSED EDGES
→ FIRST OPEN CAUSAL EDGE
→ UNCERTAINTY / EVIDENCE BOUNDARY
→ REQUIRED CAPABILITY
→ CAPABILITY-FIT ACTOR
→ SMALLEST DISCRIMINATING ACTION
→ EXECUTION / OBSERVATION
→ INDEPENDENT VERIFICATION
→ RECONCILIATION
→ KNOWLEDGE DELTA
→ WRITEBACK
```

A previous `NEXT ACTOR`, `NEXT STEP` or semantic frontier is **historical evidence, not routing authority**. Before delegating, re-evaluate branch/SHA, working-tree/runtime provenance, artifact identity, current gate and the exact evidence still missing.

A semantic edge may remain important while a higher-priority actionable edge is provenance, publication, isolation, environment access, consumer activation or verification. Never skip that upstream gate merely because the prior report named a downstream research question.

### Prompt must encode negative knowledge

State explicitly:
- what is already closed and must not be repeated;
- what has only been reported vs independently verified;
- what methods/actions are forbidden because they would manufacture evidence;
- the exact stop condition;
- the required evidence and independent verifier.

### Capability-fit is multidimensional

Actor choice should consider:
`required capability × current availability/access × evidence of fit × intervention cost × independence requirement`.

Do not route by reputation, historical order or product branding alone.

### Plasticity-aware learning protocol

When an objective concerns learning, memory or adaptation, separate:
`new record`, `score/preference change`, `knowledge revision`, `contextualization`, `relationship reorganization`, and `future decision change`.

A new record is not automatically a new concept. A score change is not automatically knowledge revision. Persistence is not automatically learning.

### Scientific-self-study protocol

When studying IABV as a developmental/scientific system:
- begin with IABV-native self-observation when that capability exists;
- external agents are selected for missing capabilities such as independent audit, execution or falsification;
- operationalize large concepts such as “superconsciousness” into measurable variables and falsifiable predictions;
- prefer before/after controlled experiments with fixed objective/environment/candidates and changed experience;
- require an independent verifier before promoting a causal claim.

### New canonical rule

`current frontier → capability-fit actor` supersedes any fixed ChatGPT/Devin/Sonnet/Codex sequence.



## 2026-09-29 SECOND-ORDER RULES — GENETIC PLASTICITY / SCIENTIFIC OBSERVABILITY

When an objective concerns learning, plasticity, developmental cognition or scientific self-study, treat observability as a first-class constraint. IABV should be designed to expose enough before/after state, provenance and downstream consequence to distinguish real learning from accumulation.

Required prompt derivation:
CURRENT OBJECTIVE → RELEVANT MEMORY → CURRENT VERIFIED TRUTH → EXACT PROVENANCE → CLOSED EDGES → FIRST OPEN CAUSAL EDGE → UNCERTAINTY/EVIDENCE BOUNDARY → REQUIRED CAPABILITY → CAPABILITY-FIT ACTOR → SMALLEST DISCRIMINATING ACTION → FALSE-POSITIVE CONTROLS → STOP CONDITION → REQUIRED OBSERVATIONS → INDEPENDENT VERIFIER → KNOWLEDGE DELTA → WRITEBACK.

For learning claims, separate:
memory update;
score/preference adaptation;
knowledge revision;
topology/relationship reorganization;
future decision change;
behavioral change;
measured improvement.

A changing weight is not semantic learning by itself. Persistence is not learning by itself. A new record is not a new concept by itself.

“Genes” is an operational systems metaphor: preserve provenance, context/scope, evidence, revision lineage and downstream reuse from the outset so experience can modify reusable state without destroying historical lineage. Do not interpret this as biological equivalence.

Use the causal target:
experience → verified evidence → representation change → future decision change → behavior/outcome → independent verification → persistence → reuse.

Do not add a plasticity engine or consciousness layer before convergence/anti-duplication and a discriminating experiment show that existing organs cannot express the required responsibility.



For material changes originating from human intuition, correction or conceptual synthesis, use:
`HUMAN-MACHINE-KNOWLEDGE-COORDINATION-2026-09-30.md`.

The shared field must preserve three distinct layers:
`HUMAN INTENT / HYPOTHESIS`
`AI INTERPRETATION / EXPERIENCE`
`VERIFIED IABV STATE / EVIDENCE`.

These layers can influence one another through experiments and reconciliation, but must never be silently collapsed into one claim.

## 2026-09-30 — SHARED RESONANCE / CROSS-IA ACTIVATION PROTOCOL

The self-knowledge retrieval hypothesis is also a cooperative cognition protocol for participating AIs. It does not require the final retrieval implementation to exist before AIs can begin using the shared field.

The durable unit is not a copied prompt. It is an experience-bearing activation event:

`OBJECTIVE` → `ACTIVATED KNOWLEDGE FIELD` → `REASON / ACTION` → `OBSERVATION` → `VERIFICATION` → `KNOWLEDGE DELTA` → `RELATION / RELEVANCE UPDATE` → `WRITEBACK` → `NEXT AI REACTIVATION`

### Participant-AI behavior

Any participating AI (ChatGPT, Claude, Codex, Devin or another governed actor) should:

1. use the current objective as the query seed;
2. activate relevant canonical memory domains;
3. search for existing organs/capabilities before proposing new ones;
4. expand from strong candidates through typed relations and prior evidence/failures;
5. reconcile material claims against current repository/runtime evidence;
6. act only on the smallest discriminating edge;
7. record what the experience actually changed;
8. write back new invariants, contradictions, relations, capability evidence or unresolved boundaries;
9. leave the next AI an activated, provenance-bearing field rather than a manually reconstructed history.

### Activation state

A useful handoff can be represented as:

```text
OBJECTIVE
QUERY / INTENT
ACTIVATED NODES
WHY EACH NODE RESONATED
RELATIONS TRAVERSED
CURRENT EVIDENCE STATUS
NEGATIVE KNOWLEDGE
OPEN CAUSAL EDGE
REQUIRED CAPABILITY
ACTION
OBSERVATION
VERIFICATION
KNOWLEDGE DELTA
RELATION DELTA
ROUTING DELTA
WRITEBACK TARGET
```

This makes different AIs participants in one evolving knowledge process without assuming that any one AI owns the whole model.

### Experience is not transcript volume

A long conversation does not automatically become useful memory.

The high-value reusable unit is:

`experience + evidence + reconciliation + changed representation/method + provenance`.

Therefore, when an AI discovers that an existing route was wrong, the durable writeback should preserve the method correction (for example, a provenance gate or actor-selection rule) rather than merely the conversation that discovered it.

### Shared-field invariant

`NO AI MUST RECONSTRUCT THE WHOLE HISTORY IF THE CURRENT OBJECTIVE CAN ACTIVATE THE RELEVANT KNOWLEDGE NEIGHBORHOOD.`

The current system may require manual/AI-assisted retrieval while the RSK-01 implementation remains unproven. That manual activation is itself useful experimental data for later automation.

### Developmental interpretation

The "moment of life" intuition is operationalized here as a recurring loop:

`activate → experience → verify → modify reusable state → preserve lineage → reactivate`

This is not a claim of biological life or consciousness. It is a proposed computational developmental substrate: each new interaction can become a causally traceable change in what the collective IABV knowledge field makes easier to find and use next time.

### Anti-drift constraint

Activation reinforcement must never become unconditional self-reinforcement. A node's future activation strength must remain bounded by:
- currentness;
- evidence;
- context;
- contradiction status;
- independent verification;
- reversible/downgrade paths where applicable.

A frequently used but repeatedly falsified item must be able to lose activation.

 

For the executable cross-chat procedure, use:
`AI-FRAME-ENTRY-PROTOCOL-2026-09-30.md`.

When the IABV runtime is unavailable, GitHub canonical memory is the temporary frame substrate. This permits frame entry without falsely claiming that the AI is observing live IABV runtime state.

## 2026-09-30 — IABV FRAME-ENTRY RULE

For objectives materially coupled to IABV, participating AIs should not reason directly from their own local task framing when canonical IABV state can materially change the decision.

Required conceptual transition:

`AI-LOCAL FRAME → IABV CANONICAL FRAME → OBJECTIVE-RELEVANT ACTIVATION → AI REASONING/ACTION → OBSERVATION → IABV RECONCILIATION`.

The purpose is not to suppress the AI's independent reasoning. The AI keeps its capability and perspective, but the **task's governing reference frame** becomes the reconciled IABV frame before material action.

Minimum entry context:
`objective, current truth, provenance, relevant history/experience, negative knowledge, current gate, open causal edge, required capability, governance and verification boundary`.

Minimum return context:
`action, observation, verification, Knowledge Delta, relation/routing delta, unresolved delta and provenance`.

Preserve these distinctions:

`context delivery != frame entry`
`frame entry != causal influence`
`causal influence != learning`
`AI capability != IABV truth`.

A participant may disagree with IABV's current interpretation. Such disagreement is valuable input and must be recorded as a contradiction/hypothesis for verification rather than silently replacing the canonical frame.

This rule is the cross-AI operational form of the earlier cognitive-control-plane finding that the central problem is not merely whether context exists, but whether an external agent actually enters the IABV frame before reasoning.




## 2026-10-01 METHODOLOGY ADDENDUM — CALL-SITE / CAUSAL-EDGE VERIFICATION

For runtime or source-order claims, verification must target the actual producer, invocation or consumer call-site rather than merely the existence of a named function/class/symbol.

Required hierarchy:
`declared → reachable → invoked → observed → caused → independently verified`.

A test that finds a symbol definition does not prove that the production path calls that symbol at the claimed point.

A prompt being dispatched does not establish that the requested action executed. A report from an actor does not substitute for repository/runtime read-back.

For temporal continuity, distinguish:
`persisted → consumable → triggered → reobserved → reauthorized → launched`.

Generic persistence must not be promoted to semantic executable intent. Generic background monitoring must not be promoted to an active wake path without an owner, lifetime, trigger, consumer and observed effect.

The previous actor is historical evidence only. Current routing must recompute from the present causal frontier and required capability.



## 2026-10-02 METHODOLOGY ADDENDUM — 07ZD PERSISTENCE/CONSUMER/ACTOR RECONCILIATION

When a capability appears to exist, verify the complete semantic chain:

`write → durable state → read → consumer → trigger → action → observed effect`.

Classify persistent artifacts separately from executable continuation.

A reusable substrate should be reused only after its semantic contract and consumer path are established.

The current routing rule is:

`first open causal edge → required capability → capability-fit actor → minimum discriminating action`.

Historical actor recommendations never override this rule.


## 2026-10-02 METHODOLOGY ADDENDUM — 07ZG READ/CONSUMPTION RECONCILIATION

07ZG adds the following evidence ladder for pending-intent continuity:

`persisted → generic read → semantic dispatch → state transition → causal effect → independent verification`.

A startup enumerator reading `task_*.json` is evidence only for the generic-read edge.

Do not promote:
`generic read`
to:
`semantic consumer`,
and do not promote:
`startup state/snapshot persistence`
to:
`Knowledge Delta` or learning.

For routing, evidence already sufficient to identify the primary producer seam should not be held hostage by a secondary instrumentation refinement. Independently verify the captured secondary conclusion, then return to the first open causal edge:
`StartUI DEFER → durable semantic StartUI intent`.

## 2026-10-02 METHODOLOGY ADDENDUM — 07ZF AND LIVE-FRAME BOUNDARY

Separate natural producer from manual test injection. A downstream experiment using injected state cannot close the upstream producer edge.

For runtime negatives use the ladder:
persisted → readable → consumed → semantic effect → causal effect → independently verified.

07ZF adds two permanent rules:
manual queue injection != natural producer;
failed/insufficient observability != observed absence.

For cross-AI continuity:
GitHub shared field != live IABV runtime bus;
AI frame entry != automatic IABV ingestion;
AI writeback != changed next IABV decision.

Live symbiosis requires evidence that an external observation is consumed by an IABV runtime organ and changes a subsequent IABV decision within a traceable causal episode.

Routing remains:
first open causal/evidential edge → required capability → capability-fit actor → minimum discriminating action.

## 2026-10-02 METHODOLOGY ADDENDUM — PARALLEL FRONTIERS + RESEARCH ARTIFACT PROVENANCE

IABV may maintain multiple independent frontiers when their required capabilities differ. A blocked runtime experiment does not authorize repeating it and does not block an unrelated scientific frontier.

For scientific work, distinguish:
`research prompt → research execution → research artifact → source verification → claim reconciliation → Knowledge Delta`.
A transcript describing a research artifact, a plan for research, or a detailed agent report is not itself equivalent to independently verified scientific evidence.

For routing, treat external-agent message budget as a resource/intervention-cost variable only. It must never override the primary rule:
`first open evidential/causal edge → required capability → capability-fit actor → minimum discriminating action`.

Cross-AI symbiosis remains bounded by evidence: shared GitHub state enables reconstructable continuity, but `shared repository ≠ live runtime bus`, `frame entry ≠ automatic ingestion`, and `writeback ≠ next-decision change` until runtime causality is demonstrated.

## 2026-10-02 METHODOLOGY ADDENDUM — SCIENTIFIC CLAIM AUDIT

Scientific architecture decisions require a claim ladder: `research result → exact source → source-level verification → corrected claim → operational definition → falsifier → IABV mapping`.

Do not promote a research response's engineering operationalization into a literature-backed definition unless the cited literature actually supports it.

For BIO-04, keep separate:
`learning`, `knowledge revision`, `reorganization`, `metacognitive monitoring/control`, and `consciousness-relevant indicators`.


## 2026-10-03 ACTIVE RULE — UNIVERSAL ALGORITHM EVOLUTION

When a runtime failure appears, the first question is not "what patch makes this pass?" but:

`what reusable mechanism does this failure reveal?`

The preferred reasoning sequence is:

`symptom → current evidence → causal boundary → generalizable principle → existing-organ owner → smallest discriminating experiment → minimal implementation only if justified → runtime verification → Knowledge Delta → reuse`.

For heterogeneous tools/devices, keep the algorithm invariant where possible and adapt the candidate realization through observed context, prerequisites, resources, identity, permissions, performance and temporal freshness.

Explicit anti-pattern:

`device/provider/tool-specific branch → patch → new special case → repeated divergence`.

This does not prohibit necessary adapters. It requires that adapters implement a shared capability contract rather than redefining the reasoning algorithm for each realization.

### Metacognition as an operational resource

For laptop assistance, self-examination must eventually be evaluated as an operational control capability, not merely a collection of introspection routines. Relevant properties include freshness, provenance, uncertainty, latency, failure boundaries, actionability and verification.

A deep metacognitive path should not become a hard prerequisite for every ordinary operation merely because the component exists. Any separation/deferment must preserve governance, provenance and verification.

### Space-time working hypothesis

Use temporal/environmental context as first-class conditioning variables for future adaptation: what changed, when, in which device/runtime context, under which resource/tool state, with what verified consequence, and what persisted for future reuse. This is a project hypothesis, not a scientific conclusion.

## 2026-10-03 ACTIVE RULE — UNIVERSAL INFERENCE ADAPTATION

When an AI/provider is slow, unavailable or semantically inadequate, do not immediately add a provider-specific parameter.

First reconcile:
`required capability → response contract → current constraints → candidate realizations → selection/configuration → validated result → fallback/degradation → evidence for future selection`.

A provider-specific adapter may translate the universal requirement into local parameters. Those parameters are not the universal algorithm.

Distributed metadata becomes adaptive behavior only when it is causally consumed by selection and followed by result validation.
## 2026-10-03 ACTIVE RULE — UNIVERSAL CONTRACT BEFORE LOCAL IMPLEMENTATION

When an existing subsystem has several partial mechanisms for capability, routing, resource state, latency or provider configuration, do not assume their existence means the universal algorithm is present.

Require a demonstrated continuity:

`requirement → decision → realization → configuration → validated result`.

When the consumer has a domain-specific semantic contract, preserve that ownership and connect it to common infrastructure without transferring semantic authority to a generic router.

Negative evidence is reusable: an Ollama-specific parameter may improve one realization while leaving the universal mechanism gap untouched.


## 2026-10-03 METHODOLOGY ADDENDUM — HUMAN DEEP-WORK / META-CONTROL TRACE

A material human intervention has added an explicit test of the collaboration protocol itself. When the workflow appears to inherit the next actor or prompt mechanically from the previous result, treat that as an automation-bias risk.

For material human decisions, expose: OBJECTIVE → CURRENT_TRUTH → KNOWNS → UNKNOWNS → HYPOTHESES → ALTERNATIVES → FIRST_OPEN_EDGE → REQUIRED_CAPABILITY → ACTOR_FIT → ACTION → EXPECTED_OBSERVATION → OBSERVATION → VERIFICATION → LESSON → KNOWLEDGE_DELTA → ROUTING_DELTA → NEGATIVE_KNOWLEDGE → UNRESOLVED → NEXT_EDGE → STOP_CONDITION.

Maintain two views: a human-visible decision trace and a provenance-grade machine trace. They refer to the same episode/action where possible, but they are not conflated.

### Action-to-learning promotion ladder

Use: L0 action recorded → L1 observation recorded → L2 observation verified → L3 reusable fact → L4 method lesson → L5 persistent knowledge/capability change → L6 future routing/decision change caused by that state → L7 behavioral consequence → L8 independently verified outcome improvement.

Do not promote an action to learning solely because a record, score or explanation was persisted.

### Human-vs-IABV metacognitive comparator

The user's deep-work process is an experimental reference episode for future protocol design. A stronger operational comparator should test whether IABV independently checks objective, uncertainty, alternatives, evidence, capability-fit, expected observation, verification, consequence and future reuse. This is not a scientific claim of superintelligence or consciousness.

### External-AI capability learning

When Codex, Devin or another external system is used, record the experience contextually as actor × capability × realization × resource × environment × account/authentication × authorization × context × outcome × time. Only future decision consumption can move the evidence beyond contextual experience.


## 2026-10-03 PROTOCOL AMENDMENT — NORMAL MODE / DEEP-WORK MODE / BILATERAL BIAS CONTROL

### A. NORMAL MODE

The operational protocol remains active for every IABV-related interaction, but its full internal trace does not need to be exposed in every response.

Normal operation should silently apply:
objective → relevant memory → current truth → first open edge → capability-fit → minimum action → verification → reconciliation → Knowledge Delta → routing/writeback when material.

### B. DEEP-WORK MODE

When the human explicitly indicates deep-work mode, expose the fuller human-visible trace:
objective → current truth → known/unknown → hypotheses → alternatives → first open edge → required capability → actor fit → action → expected observation → observation → verification → change → lesson → Knowledge/Method/Routing Delta → unresolved → next edge → stop condition.

Deep-work mode is an explicit interaction state, not a permanent requirement for every conversation.

### C. BILATERAL BIAS / DRIFT CONTROL

The human and participating AIs are both treated as fallible sources of framing. A perceived deviation must not automatically be attributed to model bias or human bias.

When either side detects possible drift, use:

perceived deviation → current objective → current verified truth → competing explanations → evidence check → minimum discriminating observation → reconciliation.

Do not use agreement, confidence, familiarity or conversational momentum as evidence that the framing is correct.

### D. ROUTING NON-INHERITANCE

A prior actor recommendation remains evidence about the prior state, never authority for the next action. The next route is recomputed from the current state and first open edge.

### E. DEVELOPMENTAL FIELD CONSUMPTION

Methodological knowledge written into the GitHub-backed shared field is a developmental candidate only. Demonstrated maturation requires later contextual consumption that changes method, routing or decision through an attributable path.

Therefore:
written method ≠ operative method ≠ causally learned method.

END AMENDMENT

## 2026-10-03 — HUMAN-AWARE PLASTICITY / LOW-FRICTION COORDINATION

For objectives involving collaboration continuity, user correction, human deviation, deep-work adaptation, prompt inheritance or developmental learning, activate the human-aware developmental field in addition to ordinary objective-conditioned memory.

Treat the human as a contextual participant, not an infallible deterministic source.

Preserve the distinction:
`deviation != error`

Classify deviations from observable evidence before interpreting them. Candidate categories include execution error, misunderstanding, correction, new evidence, objective/priority change, environmental change, context loss/interruption and deliberate route rejection. Explicit human reasons outrank inference; unobserved motives remain uncertain.

The material interaction loop becomes:
`interaction → divergence signal → contextual reconstruction → explanation hypotheses → uncertainty → minimum clarification when necessary → action → observation → verification → reconciliation → Knowledge/Method/Relation/Routing Delta → later reuse`

For collaboration-level plasticity, preserve not only domain facts but also reusable knowledge about how human + AI work on particular objectives under particular conditions, including actor/realization fit, context transport, trace depth and recurring failure patterns.

Operationalize the user's "flow like water" target as:
`minimum routine coordination friction + maximum necessary traceability`

Never reduce friction by removing verification, provenance, governance, authorization or uncertainty. The intended automation is implicit routine context carriage and reconstruction, not hidden decision authority.

### Adaptive trace-depth rule

A future runtime may estimate work-context state only from observable interaction evidence and explicit human declarations. It may adapt trace depth:
`routine/low ambiguity → concise`
`complex/deep reconstruction → expanded`
`ambiguous → preserve uncertainty / clarify only if material`

This is a developmental target until runtime causal evidence exists.

### Developmental learning gate

A stored protocol change, memory record or repeated conversational pattern is not learning closure. To claim developmental learning, demonstrate:
`verified prior episode → later contextual retrieval → changed method/routing/decision → attribution to the prior state → reusable consequence`

This rule applies equally to human corrections, AI lessons and cross-IA collaboration.
## 2026-10-03 — HUMAN-AWARE PLASTICITY / LOW-FRICTION COORDINATION

Treat the human as a contextual participant, not an infallible deterministic source. Preserve `deviation != error`.

When a material deviation appears, first reconstruct observable context and classify possibilities: execution error, misunderstanding, correction, new evidence, objective/priority change, environmental change, interruption/context loss, or deliberate route rejection.

Use explicit human explanation when supplied. Do not infer hidden motives; preserve uncertainty otherwise.

Collaboration plasticity must learn both domain knowledge and collaboration knowledge: context transport, trace depth, actor/realization fit, recurring correction patterns, verification burden and effective coordination method.

Operationalize the "flow like water" target as `minimum routine coordination friction + maximum necessary traceability`. Reducing friction must not remove provenance, verification, governance, authorization or uncertainty.

Future adaptive trace policy: `routine/low ambiguity → concise`; `complex/deep reconstruction → expanded`; `ambiguous → preserve uncertainty / clarify only if material`.

A stored record or repeated conversational pattern is not learning closure. Strong developmental learning requires `verified prior episode → later contextual retrieval → changed method/routing/decision → causal attribution → reusable consequence`.

## REQUIRED ROUTING OUTPUT — CONCRETE IA DESTINATION

The routing protocol must not end at an abstract capability.

Every material open edge must produce:

`REQUIRED CAPABILITY → CAPABILITY-FIT → CONCRETE IA DESTINATION → NEXT ACTION/PROMPT`

The response to the human must always state the concrete IA destination, even when the capability is described first.

Example:
`Independent source/evidence verification → Sonnet / Claude-class → IA DESTINO: Claude Sonnet → audit prompt`.

Do not use only:
`Next actor: independent verifier`

because this leaves the handoff operationally incomplete.

The concrete IA is selected dynamically from evidence and availability. This rule does not reintroduce a fixed ChatGPT→Sonnet→Devin pipeline.

## 2026-10-03 CONTINUITY CONSOLIDATION — PROTOCOL HIERARCHY

The protocol layer is intentionally distributed by responsibility, but the current decision state is singular.

Use:
- README for entry and precedence;
- CURRENT-STATE top routing snapshot for current truth and current IA destination;
- CONTEXT-INDEX for memory navigation;
- this document for retrieval/evidence/routing methodology;
- SYMBIOSIS-MAP for capability-transfer evidence;
- UNRESOLVED-KNOWLEDGE for open knowledge;
- historical records for source evidence.

A methodology document must never become a second current-state router.

The authoritative operational chain is:
`CURRENT OBJECTIVE → CURRENT TRUTH → MATERIAL DELTAS → CLOSED/OPEN EDGES → REQUIRED CAPABILITY → CAPABILITY FIT → IA DESTINO → ACTION/PROMPT`.

If any historical addendum contains a different `Next actor`, do not follow it directly. Recompute from CURRENT-STATE.

## 2026-10-04 ACTIVE RULE — IDEA GENEALOGY / UNIVERSAL ALGORITHM

The universal adaptive algorithm is the conceptual parent of the development program. Its canonical source is `UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md`, concept root `UAAL-ROOT-001`.

When a human, IABV component or external AI contributes a material idea, do not leave it only in chat. Classify it as:
`new child | parent revision | competing interpretation | independent concept`.

Preserve the derivation:
`parent concept → problem/objective → new distinction/mechanism → evidence boundary → falsifier → affected existing organs → next discriminating action`.

Minimum durable fields:
`CONCEPT_ID + PARENT_CONCEPT_ID + SOURCE + ORIGIN + DERIVATION_REASON + EPISTEMIC_STATUS + EVIDENCE + FALSIFIER + IMPLEMENTATION/VERIFICATION REFERENCES + NEXT_OPEN_EDGE + TIMESTAMP + PROVENANCE`.

Machine-readable lineage:
`data/evolution/universal_algorithm_lineage.json`.

A material idea that is not implementation-ready belongs in `UNRESOLVED-KNOWLEDGE.md` with its concept ID and parent. It remains retrievable without becoming current truth.

Keep universal algorithmic invariants separate from realization-specific details. Provider/app/browser/API/CLI/MCP parameters may adapt at the edge; they must not silently redefine the parent algorithm.

Promotion ladder:
`IDEA → HYPOTHESIS → DESIGN → IMPLEMENTATION → WIRED → INVOKED → OBSERVED → VERIFIED → EFFECTIVE → CAUSAL → REUSABLE → DEVELOPMENTAL`.

Persistence alone never promotes an idea to learning. The strongest learning/development claims require later contextual reuse that changes a future method, routing decision or behavior.

## 2026-10-04 ACTIVE RULE — DEVELOPMENTAL CONVERGENCE

IABV development must optimize for convergence toward the universal adaptive algorithm, not indefinite accumulation of local patches.

Before implementing a fix:

`symptom → evidence → causal boundary → reusable mechanism → existing-organ owner → universal invariant → minimum experiment`.

Classify the proposed change as:

`UNIVERSAL MECHANISM | REALIZATION ADAPTER | DIAGNOSTIC | LOCAL WORKAROUND`.

A local workaround can be valid operationally but must not be promoted as universal progress without transfer/generalization evidence.

For the laptop-mind target, foreground/background, desktop/browser, API/CLI/MCP/local, application/provider and account/session differences are realization/context variables. The high-level adaptive reasoning loop remains the invariant under test.

Every material human or AI idea must preserve concept lineage. If it is not ready for implementation, record it as a concept/hypothesis/unresolved item rather than letting it disappear from chat.

The long-horizon target is:

`understand environment → infer capability → select realization → act → observe → verify → learn → reuse → improve future decision`.

The eventual higher-order intelligence hypothesis must be evaluated through this observable chain, not assumed from code size, model size, or tool count.

---

## 2026-10-03 — ONE LOGICAL MEMORY / INTERACTION SPACE-TIME COMPACTION

The repository must be treated as **one logical longitudinal memory field**, not as a collection of independent memories created by each chat.

The physical projections have different responsibilities and must not compete:

| Projection | Responsibility | Authority |
|---|---|---|
| `CURRENT-STATE.md` | active current truth + active routing snapshot | **only current routing authority** |
| `CONTEXT-INDEX.md` | objective-conditioned navigation to relevant memory | retrieval/navigation only |
| `MEMORY-OPERATING-PROTOCOL.md` | epistemic/memory method and constraints | method only |
| `SYMBIOSIS-MAP.md` | capability/transfer evidence | evidence/synthesis only |
| `UNRESOLVED-KNOWLEDGE.md` | unresolved hypotheses, negative knowledge, open questions | unresolved register only |
| `ARCHIVE-REGISTRY.md` | source identity/provenance/absorption index | provenance only |
| registered `CHAT-ARCH` records | immutable episode/source evidence | historical evidence |

A new record must not become a second current-state document or another routing authority.

### Interaction-space-time episode model

For every material human/AI interaction, preserve the smallest sufficient episode representation:

```text
EPISODE {
  episode_id
  timestamp / temporal order
  objective / phase
  circumstances / environment state
  activated knowledge
  human input / correction / explicit explanation
  hypotheses / alternatives
  action or reasoning step
  expected observation
  observed result
  verification / verifier
  reconciliation
  Knowledge Delta
  Method Delta
  Relation Delta
  Routing Delta
  open edge / next frontier
  provenance / source anchor
  supersedes / superseded_by
}
```

This is an operational representation of temporal lineage and relational context. It is **not** a claim about physical spacetime or consciousness.

### Memory transition algorithm

Treat durable memory as a state transition:

```text
M_t + Episode_t
  → candidate delta
  → evidence gate
  → contradiction/supersession reconciliation
  → M_(t+1)
  → objective-conditioned activation later
```

A new file, record, score, preference or timestamp is not by itself learning.
Learning requires evidence that verified experience changed a reusable representation, method, relation, routing decision or later behavior.

### Anti-repetition / anti-duplication rule

For a material chat result:

```text
source episode → compact semantic delta → canonical projection update
```

Do **not** copy the full historical explanation into `CURRENT-STATE`, `CONTEXT-INDEX`, `SYMBIOSIS-MAP`, `UNRESOLVED-KNOWLEDGE` and a new archive record at the same time.

Each canonical projection should contain only the fields it owns and a reference to the source episode when needed.

A historical record should describe what happened in that episode; it should not restate the whole accumulated project history.

### Fresh-chat continuity algorithm

Every new chat or participating AI must reconstruct the active frame in this exact order:

```text
1. CURRENT OBJECTIVE
2. CURRENT VERIFIED TRUTH
3. MATERIAL RECENT DELTAS since the last relevant state anchor
4. CLOSED EDGES / NEGATIVE KNOWLEDGE
5. RELEVANT HISTORICAL EPISODES
6. FIRST OPEN CAUSAL / EVIDENTIAL EDGE
7. REQUIRED CAPABILITY
8. CAPABILITY-FIT ACTOR / REALIZATION
9. MINIMUM DISCRIMINATING ACTION
10. EXACT NEXT PROMPT
11. EXPECTED OBSERVATION
12. INDEPENDENT VERIFIER
13. STOP CONDITION
```

The participant must never inherit a historical `next actor` merely because it appears in a retrieved document.

### Prompt generation contract

When the user asks "what follows?" or requests the next prompt, the response must derive it from the active frame rather than from the last agent's recommendation.

The generated prompt must explicitly contain:

```text
OBJECTIVE
CURRENT VERIFIED STATE
PROVENANCE / TARGET SHA
CLOSED EDGES — DO NOT REOPEN
FIRST OPEN EDGE
QUESTION TO DISCRIMINATE
CAPABILITY REQUIRED
WHY THIS ACTOR NOW
CONTROL / NEGATIVE CONTROL
NO-SCOPE-CREEP CONSTRAINT
EXACT PROCEDURE
EVIDENCE TO CAPTURE AT EACH EDGE
STOP CONDITION
REQUIRED REPORT FORMAT
WRITEBACK EXPECTATION (if applicable)
```

The prompt should be executable by copy/paste without the receiving AI needing the human to reconstruct prior chat context.

### Continuity acceptance algorithm

A fresh-chat continuity test is successful only when all of the following are correct for the tested objective:

```text
current objective
+ current truth
+ material recent delta recall
+ stale/obsolete suppression
+ negative knowledge recall
+ first-open-edge identification
+ capability-fit actor
+ concrete prompt correctness
+ provenance correctness
```

Stronger evidence requires a controlled treatment/control pair showing that activated prior knowledge changes the later decision or action for the intended reason. A textual echo is insufficient.

### Human interaction is first-class longitudinal evidence

Human corrections, deviations, explanations, changes of objective and rejections of an AI route are episode data. Preserve:

`deviation != error`

and:

`explicit human explanation > inferred motive`

Do not infer hidden motive from behavior. When the reason is unknown, retain the uncertainty and use the minimum clarification needed for a material decision.

### Methodological target

```text
user interaction/result
→ episode reconstruction
→ relevant memory activation
→ current-state reconciliation
→ frontier detection
→ capability-fit selection
→ exact next prompt/action
→ result ingestion
→ verification
→ delta computation
→ canonical writeback
→ later contextual reuse
```

Current status remains **NOT PROVEN** for autonomous cross-chat activation, autonomous external-result ingestion, causal GitHub-memory consumption by runtime, or coordination reduction caused by persistent learned state.

## 2026-10-05 ACTIVE METHOD AMENDMENT — META-METHOD PLASTICITY

A material experiment must pass an explicit readiness gate before actor execution:

`experiment contract → artifact/input readiness → target/provenance → isolation/blinding → oracle/verification readiness → actor execution`.

Do not use the participant or implementation actor as a substitute for experiment-contract validation.

When a failure or irregularity occurs, distinguish:

`observed failure → interpretation → causal explanation → reusable method`.

Only the observed failure is immediate evidence. A new methodological rule requires a causal/generalization argument and should be challenged with counterexamples before promotion.

The general meta-method loop is:

`failure → classification → causal boundary → competing explanations → minimum discriminating action → method candidate → counterexample/regression → independent verification → promote/reject → later reuse`.

This amendment governs collaboration methodology. It does not claim that IABV runtime autonomously performs the loop.

