# IABV v1.5 — COLLABORATION COORDINATION PROTOCOL
# GitHub-backed operational coordination for human + participating AIs

## PURPOSE

IABV should progressively reduce routine human coordination by maintaining a canonical, evidence-oriented development frame in GitHub.

This protocol makes that frame usable during ordinary IABV work by ChatGPT, Codex, Sonnet/Claude, Devin and other participating AIs.

The objective is not to create a new coordinator brain or to make every AI blindly follow another AI.

The coordinator is the existing IABV knowledge/control protocol:

`CURRENT-STATE + objective-conditioned memory retrieval + evidence discipline + capability-fit routing + frame entry/exit + writeback`.

Until equivalent runtime behavior is causally proven inside IABV itself, GitHub-backed coordination is the externalized control surface.

## MANDATORY PRE-TASK EXPERIENCE-ACTIVATION GATE

The normal collaboration flow has a strict precondition: before constructing a task/prompt for another actor, use the one canonical entry sequence in `README.md` (`verify remote main SHA → README → CURRENT-STATE → CONTEXT-INDEX → MEMORY-OPERATING-PROTOCOL → objective-specific retrieval`) and activate prior experience.

For objectives touching global vision, architecture, universal semantics/generalization, cross-domain composition, learning, memory/continuity or protocol design, explicitly activate `UAAL-ROOT-001` and the relevant concept lineage. For a supplied chat, use the `CHAT / TRANSCRIPT INTAKE CONTRACT` in `MEMORY-OPERATING-PROTOCOL.md` and state any coverage limitations.

`objective → canonical entry → objective-conditioned retrieval → failure/false-positive history → negative knowledge + method deltas → first open edge → capability/actor/readiness → task/prompt`.

This harmonizes the collaboration protocol with the entry contract; it does not create a new coordinator or supersede `CURRENT-STATE.md` as routing authority.

Relevant prior failures must alter at least one concrete part of the task contract when applicable: object lock, scope exclusions, source requirements, test matrix, evidence requirement, stop condition or acceptance gate. Merely quoting history does not count.

## UAAL-D021 route-realization and artifact-identity gate (proposed, 2026-10-28)

Before constructing a handoff for any publish/update/retest/clone/implementation action, query the live repository for an existing branch, commit, pull request, exact file blobs and reviews that can satisfy the objective. Bind each expected hash to an exact artifact revision and evidence stage; never compare an R3 receipt with R4 bytes as though they were the same candidate. If an entry snapshot conflicts with live `CURRENT-STATE.md`, the canonical route wins and the stale snapshot must be reconciled before action selection. Record existing route alternatives and why the selected action has greater target-edge utility. This refinement is proposed in the current documentation PR and is not canonical on `main` until integrated and fetched back.


## G1 enrollment handoff correction — exact evidence, no circular manifest (proposed 2026-10-28)

When the current route concerns an initial trust enrollment, the coordinator must make a task contract that separates source/test implementation from one-time enrollment execution. A prompt for Codex must state which of these stages is authorized, its exact side-effect budget, prohibited actions, evidence to return and stop condition. Do not let “proceed” expand the scope to bridge activation, protected reads or tool grants.

The just-completed preflight illustrates scoped proof:
- the existing private GitHub repository and main reference were readable via the Owner/Codex-reported authenticated route, and this session independently verified the repository metadata, main SHA and CURRENT-STATE blob identifier through GitHub;
- manifest-specific byte verification remains not applicable until the manifest exists;
- branch protection/ruleset status remains UNKNOWN because the reported API inspection returned HTTP 403;
- neither a successful existing-file fetch nor the presence of a GitHub App PEM proves G1, branch protection or the existence of a usable future manifest route.

Do not ask the Owner to choose the trust mechanism again: it has been selected as an Owner-approved, version-pinned enrollment manifest with a subordinate local Windows CNG key. The manifest must not contain its own containing commit SHA, Git blob SHA or whole-file digest; store those post-merge identities in a separate local receipt after exact canonical fetch-back. The manifest must contain public-key metadata only, never a private key or credential.

For source/test work, reuse and inspect the existing PR #556 M1A composition candidate before writing. Verify its live head and exact base; do not fork a duplicate security-organ candidate. Do not create the local key or enrollment manifest in the source/test task. Exercise positive and negative enrollment contracts with synthetic fixtures only, and keep:
G1=NOT_ESTABLISHED; G2/G3=NOT_ESTABLISHED; MCP_TOOL_ALLOWLIST=EMPTY; PROTECTED_READS=FAIL_CLOSED; TUNNEL=DISABLED; BRIDGE=BRIDGE_NOT_READY.
A later one-time enrollment operation is a separate, narrowly authorized step. An approved G1 identity alone grants no tool capability.


The current result adjudication examples are:
- RQ21.55: the report changed the object to research about Deep Research itself;
- RQ21.56: the report remained in the broad Windows sandbox domain but failed the required seven-guarantee composition and source contract.

Historical actor order and historical `NEXT ACTOR` fields are not routing authority. Recompute from the first current open edge. Use existing organs; do not create another coordinator brain.

---

## DEFAULT OPERATING MODE — NORMAL IABV WORK

`HUMAN OBJECTIVE → IABV CANONICAL FRAME → RELEVANT KNOWLEDGE → CURRENT VERIFIED TRUTH → CLOSED EDGES → FIRST OPEN CAUSAL/EVIDENTIAL EDGE → REQUIRED CAPABILITY → CAPABILITY-FIT ACTOR/REALIZATION → EXACT TASK/PROMPT → ACTION → OBSERVATION → INDEPENDENT VERIFICATION → RECONCILIATION → KNOWLEDGE / METHOD / RELATION / ROUTING DELTA → WRITEBACK → NEXT FRONTIER`

The participating AI is normally not blind to IABV history. It should enter the IABV frame and use the relevant canonical state before acting.

The human should not have to repeatedly transport the same operational history when the required state is already available in the IABV knowledge layer.

## WHAT “IABV AS COORDINATOR” MEANS

IABV coordination means that the current canonical state determines the decision frame from which the next actor and task are derived.

It does not mean that a named AI permanently owns a role.
It does not mean that the previous AI chooses its successor.
It does not mean that a report is automatically accepted as truth.

It does mean:

- current objective is explicit;
- stale routes are distinguishable from current routing;
- closed edges are not reopened without evidence;
- the first open edge controls the next intervention;
- actor selection is capability-fit and access-aware;
- prompts carry the minimum context needed to perform the task correctly;
- results return with evidence and provenance;
- material changes are reconciled and written back.

## ACTOR RULE

Use capability-fit, not model identity:

`required capability + required access + independence requirement + intervention cost + expected information gain → selected actor`

Typical capability observations:

- ChatGPT: synthesis, reconciliation, adjudication when independent, prompt construction, writeback.
- Codex: repository/source archaeology, composition analysis, implementation or controlled repository experiments.
- Sonnet/Claude: independent forensic/source/security/contract audit and challenge.
- Devin: Windows/runtime/production lifecycle execution when that environment is required.

These are capability observations, not permanent assignments. Recompute after material reconciliation.

## USING IABV TO WORK WITH CODEX

When the current frontier requires Codex, the ordinary flow is:

`IABV CURRENT STATE → capability-fit selects CODEX → generate exact Codex task from the current frontier → Codex enters IABV frame → Codex performs the bounded action → Codex returns observation + artifact + provenance + evidence boundary → independent verification when required → IABV reconciliation/writeback → recompute next frontier`

The human may copy the exact task to Codex when direct machine-to-machine invocation is not available.

The desired developmental direction is that this transport becomes progressively less manual as IABV runtime capabilities mature.

## NORMAL MODE VS BLIND EXPERIMENT MODE

### NORMAL MODE

All participating AIs may use the canonical IABV frame and relevant historical knowledge.

The purpose is productive development, verification, routing and continuity.

### BLIND EXPERIMENT MODE

Blindness is a test condition, not the normal collaboration protocol.

Use it only when an explicit experiment is measuring whether a genuinely new AI can reconstruct IABV context without prior exposure.

For such an experiment, the experiment contract may intentionally override normal frame entry:

`no prior IABV context + isolated conversation + frozen corpus + identical task → participant reconstruction → claim-level adjudication`

The current RSK-01 fresh-blind test is such an exception.

Therefore:

`RSK-01 blind participant ≠ normal Claude/Sonnet operation`

An `INELIGIBLE — PRIOR CONTEXT PRESENT` result in blind mode means the test run is contaminated/ineligible. It does not mean Claude should normally be prevented from using IABV.

## FRAME-ENTRY REQUIREMENT FOR CODEX

When Codex is selected for an ordinary IABV task, the task should begin with a compact frame sufficient to prevent drift:

`OBJECTIVE → CURRENT MAIN HEAD → CURRENT VERIFIED TRUTH → RELEVANT MEMORY → CLOSED EDGES → FIRST OPEN EDGE → WHY CODEX FITS → EXACT ACTION → FALSE-POSITIVE / NON-GOALS → STOP CONDITION → REQUIRED EVIDENCE → INDEPENDENT VERIFIER → WRITEBACK TARGET`

Do not include unnecessary historical context merely for volume.

## FRAME-EXIT CONTRACT

A participating AI should return:

`ACTION → OBSERVATION → ARTIFACT / PROVENANCE → VERIFICATION STATUS → WHAT THE RESULT PROVES → WHAT IT DOES NOT PROVE → KNOWLEDGE DELTA → METHOD / RELATION / ROUTING DELTA → NEW OPEN EDGE → WRITEBACK TARGET`

Reported completion without evidence remains a report.

## GOVERNANCE

This protocol does not grant the AI coordinator independent authority to override the human.

Preserve:

`human objective ≠ AI interpretation ≠ verified system truth`

High-consequence authorization, security, runtime and causal claims remain evidence-gated.

## CURRENT LIMIT

GitHub-backed coordination is currently an externalized control method.

It is not yet proof that the IABV runtime itself automatically reads this state, selects the next actor, launches the actor, ingests the result and causally changes future decisions without human transport.

That stronger runtime claim remains an open developmental frontier.

## RELATION TO EXISTING PROTOCOLS

- `CURRENT-STATE.md` = current routing authority.
- `MEMORY-OPERATING-PROTOCOL.md` = retrieval and epistemic method.
- `CONTEXT-INDEX.md` = navigation from objective to relevant material.
- `AI-FRAME-ENTRY-PROTOCOL-2026-09-30.md` = temporary entry/exit contract for participating AIs.
- `SYMBIOSIS-MAP.md` = capability and transfer evidence.
- This protocol = operational coordination rule that connects those existing organs without creating a new software brain.

END OF RECORD