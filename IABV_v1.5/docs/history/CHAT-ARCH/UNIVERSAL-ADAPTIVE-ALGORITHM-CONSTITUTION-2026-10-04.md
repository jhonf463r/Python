# IABV v1.5 — UNIVERSAL ADAPTIVE ALGORITHM CONSTITUTION
## Concept root, derivation tree, traceability and evolution protocol
### 2026-10-04

**STATUS:** CANONICAL CONCEPTUAL ROOT / DEVELOPMENT PROTOCOL
**SCOPE:** long-horizon IABV design, research, architecture, experiments and cross-AI collaboration.
**IMPORTANT:** this document defines conceptual authority and derivation discipline. It does not prove that the algorithm is fully implemented, universal in runtime, conscious, or independently evolved.

## 1. ROOT IDEA — THE IDEA FROM WHICH THE REST DERIVES

### UAAL-ROOT-001

**FUNDAMENTAL IDEA**

IABV should become an adaptive universal cognitive-operational system that can understand and navigate a heterogeneous real environment (the user's laptop and, later, other environments) through one general reasoning algorithm rather than a collection of provider/application-specific recipes.

The environment may contain operating-system state, processes, windows, desktop UI, installed applications, browsers, human browser sessions, isolated browser sessions, filesystem/runtime, local models, external AIs, APIs, CLI, MCP, accounts, identities, sessions, permissions, resources and temporal state.

**Core principle:**
`the environment can change; the realizations can change; the high-level adaptive reasoning loop should remain as invariant as the evidence allows.`

**Universal loop:**
`OBJECTIVE → PERCEIVE → REPRESENT → INTERPRET → MAINTAIN UNCERTAINTY → INFER REQUIRED CAPABILITY → DISCOVER CANDIDATE REALIZATIONS/CHANNELS → CHECK CURRENT CONSTRAINTS/ACCESS/RESOURCE STATE → SELECT → GOVERN → ACT → OBSERVE TRANSITION → VERIFY → UPDATE WORLD/SELF MODEL → STORE REUSABLE KNOWLEDGE → REUSE → ADAPT → NEXT DECISION`.

This is the parent concept. Every major future design/implementation idea must be traceable to it or explicitly marked as independent.

## 2. WHAT THIS ROOT IDEA DOES NOT MEAN

It does not mean:
- one universal implementation for every OS/app;
- one browser for every task;
- one AI provider;
- one API;
- one giant ontology;
- one mega-router;
- one process containing the whole laptop;
- unrestricted autonomy;
- consciousness as an assumed property.

Platform/provider-specific adapters are allowed when they realize a common capability contract.

## 3. HIERARCHY OF DERIVATION

All major concepts must fit this hierarchy unless explicitly justified otherwise:

`UAAL-ROOT-001`
↓
`UNIVERSAL ENVIRONMENTAL UNDERSTANDING`
↓
`CAPABILITY / AFFORDANCE INFERENCE`
↓
`REALIZATION / CHANNEL DISCOVERY AND SELECTION`
↓
`MODALITY ADAPTATION (foreground/background/browser/desktop/API/CLI/MCP/local)`
↓
`GOVERNED ACTION + OBSERVATION`
↓
`SEMANTIC / EXPERIENCE LEARNING`
↓
`REUSE / PLASTICITY`
↓
`SELF-DIAGNOSIS + SELF-DIRECTED EXPERIMENTATION`
↓
`DEVELOPMENT / SPECIALIZATION / COMPOSITION`
↓
`POTENTIAL HEREDITY / EVOLUTION / OPEN-ENDED DEVELOPMENT`

Cross-cutting branches:
`cross-chat continuity`, `human-machine collaboration`, `external-AI symbiosis`, `scientific experimentation`, `provenance/governance`.

These branches are derived mechanisms or constraints, not replacements for the root idea.

## 4. CURRENT DERIVED CONCEPTS ALREADY PRESENT IN THE PROJECT

| Concept ID | Derived idea | Parent | Current role | Evidence status | Canonical source |
|---|---|---|---|---|---|
| UAAL-D001 | Universal environmental semantics | UAAL-ROOT-001 | Understand unfamiliar objects, relations, states and capabilities | DESIGN / RESEARCH, runtime NOT PROVEN | `UNIVERSAL-ENVIRONMENTAL-SEMANTICS-2026-09-26.md` |
| UAAL-D002 | Universal experimental reality loop | UAAL-ROOT-001 | Learn environment by observe→hypothesize→test→verify→update→reuse | DESIGN / RESEARCH, universal runtime NOT PROVEN | `UNIVERSAL-EXPERIMENTAL-REALITY-LOOP-2026-09-26.md` |
| UAAL-D003 | Capability/resource fabric | UAAL-ROOT-001 | objective→capability→actor/tool/resource→constraints→execution | PARTIAL / NOT PROVEN end-to-end | `BIOSOFIA-ARTIFICIAL-DEVELOPMENT-INFLECTION-2026-09-20.md`, `SYMBIOSIS-MAP.md` |
| UAAL-D004 | Adaptive realization/modality selection | UAAL-ROOT-001 | choose among app/browser/CDP/API/CLI/MCP/local and foreground/background | PARTIAL substrate / causal universality NOT PROVEN | `UNIVERSAL-ENVIRONMENTAL-SEMANTICS-2026-09-26.md`, current code/tool cards |
| UAAL-D005 | Human browser/session as environmental resource | UAAL-D004 | reuse live browser/session when it is the best available channel | PARTIAL / specific paths evidenced | R5/R6/R7 records, shared-CDP code |
| UAAL-D006 | External AIs as interchangeable capability realizations | UAAL-D003 | Codex/ChatGPT/Claude/Devin/Ollama selected by capability-fit, not fixed sequence | PARTIAL / causal dynamic selection NOT PROVEN | `SYMBIOSIS-MAP.md`, tool registry/adapters |
| UAAL-D007 | Metacognitive self-use | UAAL-ROOT-001 | IABV uses self/world/architecture knowledge to diagnose its own next frontier | PARTIAL / runtime causal closure OPEN | `BIOSOFIA-METACOGNITIVE-EXECUTION-ROADMAP-2026-09-21.md` and related records |
| UAAL-D008 | Knowledge plasticity | UAAL-ROOT-001 | verified experience changes reusable knowledge and later decisions | selector-level evidence exists; strong future-decision change NOT PROVEN | L5 records / `SYMBIOSIS-MAP.md` |
| UAAL-D009 | Developmental acceleration | UAAL-D008 | experience reduces routine human coordination while increasing reusable capability | HYPOTHESIS / measurement program | `00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md` |

## 5. IDEA TYPES

Every material contribution must be classified as one of:

`IDEA` — conceptual proposal, including human intuition.
`HYPOTHESIS` — claim about what may be true and how it could be falsified.
`DESIGN` — proposed organization/contract/algorithm.
`IMPLEMENTATION` — code or configuration expressing a design.
`EXPERIMENT` — bounded test intended to discriminate hypotheses.
`OBSERVATION` — directly observed runtime/source/environment evidence.
`VERIFICATION` — independent check of a concrete claim.
`KNOWLEDGE_DELTA` — reconciled change in what the project should now treat as known.
`METHOD_DELTA` — change in how future work should be done.
`ROUTING_DELTA` — change in capability/actor selection logic.
`UNRESOLVED` — important idea/question that remains open.

Never promote one class into another without the required evidence transition.

## 6. REQUIRED GENEALOGY FIELDS

Every new major idea should carry, in its record or canonical absorption:

`CONCEPT_ID`
`PARENT_CONCEPT_ID`
`SOURCE_EPISODE / SOURCE_RECORD`
`ORIGIN_TYPE = HUMAN | IABV | AI | EVIDENCE-DERIVED`
`DERIVATION_REASON`
`PROBLEM_OR_OBJECTIVE`
`NEW_MECHANISM_OR_DISTINCTION`
`DEPENDENCIES_ON_EXISTING_ORGANS`
`AFFECTED_LAYER`
`EPISTEMIC_STATUS`
`EVIDENCE`
`FALSIFIER / FAILURE CONDITION`
`IMPLEMENTATION_REFERENCES`
`EXPERIMENT_REFERENCES`
`VERIFICATION_REFERENCES`
`KNOWLEDGE_DELTA`
`ROUTING_DELTA`
`SUPERSEDES / SUPERSEDED_BY`
`NEXT_OPEN_EDGE`
`TIMESTAMP`
`BRANCH / SHA` when code evidence is involved.

## 7. DERIVATION RULE

A child concept is validly derived only when the record can answer:

> What problem in the parent concept required this child?
> What part of the parent remains invariant?
> What new assumption/mechanism does the child add?
> What evidence supports it?
> What evidence would falsify it?
> Which existing IABV organ should own it?

Example:

`UAAL-ROOT-001`
→ environment is heterogeneous
→ therefore a universal reasoning layer needs platform-neutral meaning
→ `UAAL-D001` universal environmental semantics
→ therefore capability inference can operate on meaning rather than provider recipes
→ `UAAL-D003` capability/resource fabric
→ therefore channel/realization constraints must participate in selection
→ `UAAL-D004` adaptive realization/modality selection
→ therefore verified experience can change future selection
→ `UAAL-D008` plasticity
→ therefore repeated reusable change can become developmental acceleration hypothesis
→ `UAAL-D009`.

This chain is a traceable derivation, not proof that each child is already implemented.

## 8. ANTI-DRIFT RULE

A derived implementation must not silently redefine the root algorithm.

Examples of drift:

`CURRENT TASK = ChatGPT integration` → treating ChatGPT as the algorithm.
`CURRENT TASK = MCP` → treating MCP as the universal cognition mechanism.
`CURRENT TASK = browser automation` → treating browser automation as the universal environment model.
`CURRENT TASK = Devin` → treating Devin as the fixed development actor.

Correct interpretation:
`current task = one test/realization of the universal algorithm`.

## 9. UNIVERSAL INVARIANT VS REALIZATION VARIABLE

For every implementation, classify each property as either:

### UNIVERSAL / ALGORITHMIC
objective interpretation, uncertainty, semantic state, capability inference, evidence reasoning, selection, governance, observation, verification, learning, reuse.

### REALIZATION-SPECIFIC
UI selectors, browser protocol, executable path, API schema, process invocation, model/provider parameters, OS-specific accessibility APIs, session IDs, credentials and transport details.

A realization-specific detail may adapt without changing the universal algorithm.

## 10. DEVELOPMENT PROTOCOL

Every significant development cycle should follow:

`OBJECTIVE`
→ `CURRENT VERIFIED TRUTH`
→ `PARENT CONCEPT / DERIVATION POSITION`
→ `UNCERTAINTY`
→ `FIRST OPEN CAUSAL EDGE`
→ `REQUIRED CAPABILITY`
→ `CAPABILITY-FIT ACTOR / RESOURCE`
→ `SMALLEST DISCRIMINATING ACTION`
→ `EXPECTED OBSERVATION`
→ `OBSERVATION`
→ `INDEPENDENT VERIFICATION`
→ `KNOWLEDGE / METHOD / ROUTING DELTA`
→ `REUSE TEST`
→ `NEXT DERIVED IDEA OR OPEN EDGE`.

## 11. DEVELOPMENTAL PROMOTION GATES

`IDEA → HYPOTHESIS`: explicit falsifiable question exists.
`HYPOTHESIS → DESIGN`: mechanism specified without overclaiming evidence.
`DESIGN → IMPLEMENTATION`: owner/contract and minimal seam identified.
`IMPLEMENTATION → WIRED`: producer/consumer path exists.
`WIRED → INVOKED`: legitimate path is exercised.
`INVOKED → OBSERVED`: result is actually seen.
`OBSERVED → VERIFIED`: independent evidence supports the concrete claim.
`VERIFIED → EFFECTIVE`: behavior changes in the intended system.
`EFFECTIVE → CAUSAL`: counterfactual/control evidence excludes plausible alternatives.
`CAUSAL → REUSABLE`: later context retrieves and uses the learned state.
`REUSABLE → DEVELOPMENTAL`: the reused state helps produce/verify the next capability.

## 12. CROSS-AI CONTINUITY PROTOCOL

Participating AIs are temporary participants in one developmental field.

On entry, follow the single canonical sequence defined in `README.md`; this Constitution is objective-conditioned conceptual context, not a competing entry step or routing authority:

`verify remote main SHA → README → CURRENT-STATE top routing snapshot → CONTEXT-INDEX relevant records → MEMORY-OPERATING-PROTOCOL method → objective-specific evidence`

When the objective materially touches global vision, architecture, universal semantics/generalization, cross-domain composition, learning, memory/continuity or protocol design, activate `UAAL-ROOT-001`, the relevant Constitution sections and concept lineage at the objective-conditioned stage defined by README.

Each AI must preserve:
`what the human introduced → what the AI inferred → what was tested → what was observed → what was verified → what changed → what remains unresolved`.

The AI identity is secondary to the capability and provenance.


### Shared-memory use is an operational obligation, not an assumed property

For material work, every participating AI session that has an authorized repository path must apply UAAL-D020 to its own selection of reasoning and action. GitHub is the shared external memory substrate; the content reaches an agent only if that agent or its runtime actually retrieves/inherits it. The method is intended to alter **this session's task framing, route selection, action and verification**, not merely the contents of IABV's product code.

Use the stage ladder `MEMORY_RETRIEVED → METHOD_ACTIVATED → METHOD_APPLIED → OUTCOME_VERIFIED → LATER_CAUSAL_REUSE`. Keep the stages separate. A method-use claim should identify the retrieved source, applicable rule, changed decision and outcome evidence. Do not infer receipt/consumption by Codex, ChatGPT or any other session from a link, commit, upload or handoff alone.

Every handoff names its destination AI, required capability and why it is appropriate now; carries the exact task/revision, relevant memory, provenance, authorization, terminal results and acceptance/stop condition; and requests a result that can be reconciled against the canonical route. Dynamic capability-fit replaces a fixed actor sequence. A method is improved when a later non-identical task demonstrates attributable reuse, not when the file is merely persisted.

### M1B code-candidate evidence gate — applied lesson (2026-10-28)

The R1→R3 reader episode adds a specific correction to cross-agent code handoffs:

1. **Separate evidence stages:** LOCAL_CANDIDATE_REPORTED → EXACT_FINAL_SOURCE_AVAILABLE → STATIC_REVIEWED → TESTS_EXECUTED → SOURCE_PUBLISHED_BRANCH → PR_DIFF_REVIEWED → MAIN_FETCHBACK_VERIFIED.
2. **Identify exact bytes and Git state.** Record base SHA, branch, git status, path, size and SHA-256 for each file. Untracked files are not part of a normal HEAD diff; do not claim they are in GitHub. A hash is not a substitute for reviewer access to that content.
3. **Review the final version, not a prior draft.** Re-review changed source and bind the review to final hashes. If exact final content is unavailable, mark the review partial.
4. **Validate schema against reality.** Compare validators with live model definitions and real artifact shapes. Test malformed and legitimate examples. UTC-labelled dates must include timezone; test Z/offset acceptance and naive-datetime rejection.
5. **Treat tests as a distinct authorized action.** Record interpreter, version, exact command, scope, counts and exit code. Targeted tests do not prove the full suite, build, runtime, race resistance, publication or bridge authorization.
6. **Promote evidence, not more preparation.** If a local candidate exists and tests are reported passing, do not reclone/reimplement. Publish that exact candidate to an isolated branch/PR and review its actual diff.
7. **Preserve provenance.** Keep Codex execution OWNER_CODEX_REPORTED until independently reproduced or corroborated by retrievable CI evidence. A detailed receipt is not independent verification.

This refinement is documented from one bounded case; runtime enforcement and later causal reuse are not proven. See [M1B receipt](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-28-M1B-CONTEXT-READER-IMPLEMENTATION-AND-TEST-RECEIPT.md).
## 13. IDEA PRESERVATION PROTOCOL

When the human produces a new conceptual idea, do not leave it only in the chat.

Determine whether it is:
`new child of existing concept`
or
`revision of parent concept`
or
`independent concept`.

Then record it in canonical memory with:
`CONCEPT_ID + PARENT_CONCEPT_ID + DERIVATION_REASON + EPISTEMIC_STATUS + NEXT TEST/OPEN EDGE`.

If the idea is important but not yet ready for implementation, place it in `UNRESOLVED-KNOWLEDGE.md` with its concept ID and parent instead of allowing it to disappear.

## 14. IDEA RECONCILIATION

When two AIs describe the same idea differently:

`identify semantic core → compare parent concept → compare mechanism → compare evidence → merge only if semantically equivalent → otherwise preserve both as competing interpretations`.

Do not merge merely because wording is similar.

When a later implementation contradicts the original idea:

`preserve original → mark contradiction → record evidence → update child or parent explicitly → preserve lineage`.

## 15. FUTURE AUTOMATION TARGET

The long-term goal is for IABV itself to maintain this concept lineage at runtime:

`human/AI idea → concept candidate → parent matching → derivation classification → evidence linkage → promotion gate → reusable concept graph → objective-conditioned activation → future decision`.

This future mechanism must reuse existing memory, relation, graph, provenance and metacognitive organs unless an audit proves they cannot satisfy the contract.

## 16. DEVELOPMENTAL TREE CURRENTLY ENVISIONED

`UAAL-ROOT-001 Universal Adaptive Algorithm`
├─ `UAAL-D001 Universal Environmental Semantics`
├─ `UAAL-D002 Universal Experimental Reality Loop`
├─ `UAAL-D003 Capability/Resource Fabric`
│  └─ `UAAL-D004 Adaptive Realization/Modality Selection`
│     ├─ `UAAL-D005 Human Browser / Session Resource`
│     └─ `UAAL-D006 External AI as Capability Realization`
├─ `UAAL-D007 Metacognitive Self-Use`
├─ `UAAL-D008 Knowledge Plasticity`
│  └─ `UAAL-D009 Developmental Acceleration`
└─ future descendants:
   `semantic generalization → skill acquisition → composition → specialization → heredity → evolution/open-ended development`.

Future child IDs should be allocated from this ledger rather than invented ad hoc.

## 17. WHAT COUNTS AS SUCCESS

The strongest eventual demonstration is:

`IABV receives a new objective in a new environment`
→ understands the environment
→ infers what capability is needed
→ discovers more than one feasible realization
→ chooses among them based on current evidence and constraints
→ executes
→ observes the transition
→ verifies the result
→ stores reusable knowledge
→ later retrieves it in a related but non-identical situation
→ changes its method/routing/decision because of the learned state.

Repeated demonstrations across applications, browsers, local tools, external AIs and operating-system surfaces would support the stronger claim of an adaptive universal algorithm.

## 18. NON-CLAIMS

This constitution does not establish:
`consciousness`, `sentience`, `human-equivalent general intelligence`, `open-ended evolution`, or `autonomous self-development`.

Those are separate research questions requiring their own evidence.

## 19. CURRENT ROOT STATE

`UAAL-ROOT-001 = CANONICAL DESIGN INTENT`
`Universal semantic generalization = NOT PROVEN`
`Universal realization selection = PARTIAL / NOT PROVEN end-to-end`
`Universal modality adaptation = PARTIAL / NOT PROVEN end-to-end`
`Universal laptop action/observation continuity = NOT PROVEN`
`Cross-AI automatic closed loop = NOT PROVEN`
`Verified learning changing future decisions = NOT PROVEN at strong level`
`Developmental acceleration = HYPOTHESIS / measurement program`

## 20. RELATION TO CURRENT ROUTING

`CURRENT-STATE.md` remains the sole authority for current routing.
This constitution is the **conceptual parent authority**, not a routing command.
`CONTEXT-INDEX.md` remains navigation.
`MEMORY-OPERATING-PROTOCOL.md` remains the operational method.
`SYMBIOSIS-MAP.md` remains cross-IA capability/transfer evidence.
`UNRESOLVED-KNOWLEDGE.md` remains open ideas/questions.
Historical records remain evidence/history.

END OF CONSTITUTION

## 20A. CAPABILITY PRESERVATION / SPARSE ACTIVATION

Universal adaptation must preserve:
`capability repertoire != active working set`.

The algorithm should not remove capabilities merely because they are not currently selected. Instead:
`broad capability inventory → context-conditioned activation → governed candidate selection → action`.

Selection is a current-use decision, not a permanent statement about value or future necessity.

Capabilities may be `AVAILABLE | DORMANT | UNAVAILABLE | UNAUTHORIZED | RESOURCE_BLOCKED | UNSUITABLE_NOW | SELECTED` without collapsing these states into one boolean capability/not-capability classification.

Universal objective: **preserve optionality, minimize active complexity, maximize justified capability fit.**

This is conceptual; universal runtime effectiveness is not yet proven.


## 20C. DEVELOPMENTAL INFLECTION — GOVERNED SELF-CODE EVOLUTION / CAPABILITY-ORIENTED CODE PLASTICITY

### UAAL-D016

The first practical developmental inflection is reached when IABV can participate directly in the evolution of its own code through a bounded, reversible, evidence-driven loop:

`verified deficit → required capability → existing-organ archaeology → minimal code-evolution hypothesis → isolated variant → baseline/candidate test → runtime observation → independent verification → governed promotion/rejection/rollback → capability/method/relation/routing delta → later contextual reuse`.

The object of evolution is the **capability system**, not raw code volume.

Therefore preserve:

`capability repertoire != active working set`

and allow:

`ACQUIRE → REFINE → COMPOSE → CONSOLIDATE → SPECIALIZE → GENERALIZE → SUPERSEDE → ROLLBACK`.

A new capability does not necessarily require a new service. An evolution may instead improve an existing organ, compose existing organs, consolidate equivalent realizations, specialize a realization by context, or generalize a verified local lesson into a reusable contract.

The first inflection does **not** require unrestricted autonomous mutation of production code. It requires a closed enough bridge that an IABV-observed problem can become a tested, auditable, reversible code candidate and that successful candidates can be incorporated under governance.

The strongest developmental evidence begins only when a later non-identical objective measurably changes because a prior verified development state was reused.

Nonclaims remain unchanged: this does not establish consciousness, sentience, open-ended evolution or human-equivalent general intelligence.


## 20D. EXECUTION-TO-EVIDENCE STAGE SEPARATION / OBSERVABILITY (UAAL-D018)

- `CONCEPT_ID=UAAL-D018`
- `PARENT_CONCEPT_ID=UAAL-D014` (Meta-Method Plasticity / Failure-to-Evolution Loop)
- `ROOT=UAAL-ROOT-001`
- `STATUS=DOCUMENTED_METHOD_NOT_RUNTIME_PROVEN`
- `SOURCE_RECORD=CHAT-ARCH-2026-10-23-UAAL-D018-execution-to-evidence-stage-separation.md`

The parent loop remains:

`OBJECTIVE → PERCEIVE/REPRESENT/INTERPRET → MAINTAIN UNCERTAINTY → INFER CAPABILITY → DISCOVER/SELECT REALIZATION → CHECK CONSTRAINTS/ACCESS/RESOURCES → GOVERN → ACT → OBSERVE → VERIFY → UPDATE REUSABLE KNOWLEDGE → REUSE/ADAPT → NEXT DECISION`.

UAAL-D018 strengthens its observe/verify/store/reuse edges: consequential actions must separately evidence invocation, source result, output shape, safe projection, serialization/transport, coordinator reconciliation, canonical persistence/fetch-back, and later causal reuse. No stage inherits success from a previous stage.

`source success ≠ observation success ≠ projection success ≠ receipt correlation ≠ persistence ≠ causal reuse`.

This refines the existing meta-method plasticity concept and does not create a separate algorithm, memory organ, agent, or router. It reuses the Memory Operating Protocol, Development Control Tower, evidence receipts, and `CURRENT-STATE.md` routing authority. Unknown handling remains fail-closed; structured observations require field-level capture states; retries require an explicit changed precondition and valid authorization.

The method is documentary only. It does not prove runtime implementation, invocation, TPM state, automatic coordination, or learned behavior. Details and acceptance cases are in the canonical UAAL-D018 receipt.


## 20E. SPACE-TIME ANTI-LOOP AND FIRST-OPEN CAUSAL FRONTIER (UAAL-D019)

- `CONCEPT_ID=UAAL-D019`
- `PARENT_CONCEPT_ID=UAAL-D014` (Meta-Method Plasticity / Failure-to-Evolution Loop)
- `REFINES=UAAL-D018` (Execution-to-Evidence Stage Separation / Observability)
- `ROOT=UAAL-ROOT-001`
- `CANONICAL_SOURCE=CHAT-ARCH-2026-10-26-UAAL-D019-SPACE-TIME-ANTI-LOOP-CAUSAL-FRONTIER.md`
- `STATUS=DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT=NOT_PROVEN`

**Problem:** prior context can be present while the next decision still repeats an operation that cannot produce new information under unchanged relevant conditions.

**Mechanism:** before action selection, reconstruct the relevant temporal dependency graph; retrieve terminal and negative knowledge; fingerprint the decision-relevant experiment; compare it to prior attempts; select the earliest open causal edge and the smallest admissible discriminating action. If a terminal blocker recurs with the same fingerprint, do not retry unchanged. Reopening requires an observed material precondition change, a distinct falsifiable hypothesis/action, independently observed transient conditions plus a bounded retry plan, or new explicit Owner authorization.

The fingerprint is based on objective/acceptance, exact target and revision, operation/material inputs, actor/route, authorization/preconditions, relevant environment/runtime, and expected observation/stop condition. New chat/task IDs, timestamps, wording or branch names are event metadata, not new causal evidence.

Outcomes must remain stage-specific: `NOT_INVOKED`, `INVOKED_NO_OBSERVATION`, `STARTUP_FAILURE_ZERO_JOBS`, `EXECUTED_ASSERTION_FAILURE`, `OBSERVED_UNVERIFIED`, `PASS_WITH_SCOPE`, `BLOCKED_AUTHORIZATION`, `BLOCKED_PRECONDITION`, `CANONICAL_FETCH_BACK_VERIFIED`, `CAUSAL_REUSE_NOT_TESTED`, and `CAUSAL_REUSE_VERIFIED`. A visible blocker may be verified while its underlying root cause remains unknown.

**Current application:** a GitHub Actions run with `startup_failure` and `jobs=[]` did not execute IABV tests. Repeating the same workflow while the account billing-lock warning and relevant execution precondition are unchanged is not a discriminating code test. The current route is to resolve or obtain an official explanation for the account restriction; after a material precondition change, refresh live refs and execute the exact focused suites in the approved Windows/Python 3.11 environment. Source authority gates G1/G2/G3 remain separate and open.

This concept reuses the existing memory, evidence, route and governance organs; it does not create another memory store, router, coordinator or agent. It is not proof of automated anti-loop runtime, model-weight changes, consciousness or learning. A future non-identical task must demonstrate the rule was retrieved, changed the chosen action, and produced an independently verified outcome before claiming causal reuse.


## 20F. VERIFIED PROGRESS UTILITY AND STRATEGY SWITCHING (UAAL-D020)

- `CONCEPT_ID=UAAL-D020`
- `PARENT_CONCEPT_ID=UAAL-D019` (Space-Time Anti-Loop and First-Open Causal Frontier)
- `REFINES=UAAL-D019; UAAL-D018`
- `ROOT=UAAL-ROOT-001`
- `CANONICAL_SOURCE=CHAT-ARCH-2026-10-28-UAAL-D020-VERIFIED-PROGRESS-UTILITY-STRATEGY-SWITCH.md`
- `STATUS=DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT_AND_CAUSAL_REUSE_NOT_PROVEN`

**Problem:** an actor can avoid an identical retry yet still spend repeated cycles generating prompts, checkouts or plans without demonstrating that those preparations are the best authorized route to the North Star.

**Universal invariant:** every action must carry an advance contract naming its target dependency edge, current evidence, authorization/preconditions, predicted observable, acceptance/stop condition and strategy-switch condition. Prefer verified edge closure; otherwise prefer decision-changing information gain. Preparatory work is admissible only when it removes a demonstrated prerequisite and no simpler supported realization is available.

**Realization-independent method:** after a blocker, compare the actually available authorized capability surfaces rather than assuming the last actor, local checkout or transport is the only route. Select using causal fit, target reach, prerequisites, information gain, owner effort, risk/reversibility and independent verification. Do not generate another retry prompt until its causal difference and expected observable are explicit.

**Recursive termination:** two consecutive preparation-only steps on the same objective trigger a mandatory strategy reset. Before a third attempt at the same target edge, require material new evidence and a demonstrably different causal route. A child task that cannot close a parent dependency or reduce decision-relevant uncertainty must not spawn further preparation tasks.

**Required distinction:** a method/document update may be genuine progress when explicitly requested, but it is not product implementation or bridge readiness. The protocol remains documentation-only until a later non-identical task proves the method was retrieved, changed action selection and produced a verified outcome. This refinement reuses the existing route, memory and authorization organs; it creates no new coordinator or memory store.

## 20G. ROUTE TRUTH, ARTIFACT IDENTITY, AND VERIFIED-PROGRESS SELECTION (UAAL-D021)

- `CONCEPT_ID=UAAL-D021`
- `PARENT_CONCEPT_ID=UAAL-D020; UAAL-D019`
- `ROOT=UAAL-ROOT-001`
- `CANONICAL_SOURCE=CHAT-ARCH-2026-10-28-UAAL-D021-ROUTE-TRUTH-ARTIFACT-IDENTITY-AND-ADVANCE-UTILITY.md`
- `STATUS=PROPOSED_DOCUMENT_METHOD; NOT_CANONICAL_UNTIL_INTEGRATED; RUNTIME_ENFORCEMENT_AND_LATER_CAUSAL_REUSE_NOT_PROVEN`

UAAL-D021 refines progress selection where entry snapshots, current route, remote artifacts and version-specific hashes can disagree. It requires live route retrieval, discovery of existing realizations before new handoffs or publication, revision-bound identity for each digest, correction of stale entry snapshots from verified evidence, and progress labels tied to observable change at the first open edge. It reuses existing organs rather than creating a second router, memory store, coordinator or authorization authority. It must not weaken governance, human authorization, uncertainty labels, or the distinction between a published branch and canonical main.

