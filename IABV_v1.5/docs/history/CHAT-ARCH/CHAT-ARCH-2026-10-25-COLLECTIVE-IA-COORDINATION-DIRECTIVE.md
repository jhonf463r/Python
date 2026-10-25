# Collective IA coordination — Space-Time operating addendum

- Date: 2026-10-25, America/Bogota
- Status: **DRAFT / OWNER-DIRECTED COORDINATION PROPOSAL** on branch `docs/space-time-collective-ai-coordination-20261025`; not canonical until accepted into live `main` and fetched back.
- Parent protocol: `CURRENT-STATE.md` (sole routing authority), `MEMORY-OPERATING-PROTOCOL.md`, `CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md`, `SYMBIOSIS-MAP.md`, and the existing central Space-Time coordinator reconciliation.
- Scope: coordinate multiple independent AI chat sessions/workers on one IABV project without inventing a second orchestrator, duplicating memory, colliding in the same working tree, confusing candidate branches with canonical source, or overstating what a model received or verified.
- This is an operating contract, not evidence that external chats are already connected, that an automatic dispatcher exists, or that runtime behavior has been tested.

## 1. Owner direction and architectural boundary

The Owner has asked the Space-Time Mente to coordinate collective development with three or more separate ChatGPT helper chats plus other appropriate assistants. Their outputs should contribute to one shared project history and one reconciled plan. The intended coordinator restores the objective, recovers relevant prior evidence, assigns disjoint work, reconciles returned artifacts, records what actually changed, and prevents repeated investigations.

**Reuse the existing Space-Time/MOP architecture. Do not create a new “supermind service”, second task router, independent memory database, or competing source of truth.** This addendum tightens the collaboration protocol at the human/chat/task boundary; it does not claim to implement an autonomous runtime coordinator.

The following sources remain distinct:
- `CURRENT-STATE.md` is the only authority for the active task, scope, permission and next action.
- `README.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md` and the archive are navigation, methods, capability-transfer evidence and history. They do not override the live current route.
- A branch, a draft PR, an assistant response or an audit document is a candidate/evidence object, not a canonical change until its status and adoption are verified.
- A message sent to an assistant is not proof of receipt; receipt is not proof of comprehension; comprehension is not proof of use; saved prose is not proof of learning. Label each stage separately.

## 2. Operating model: one coordinator, many bounded workers

### Space-Time Coordinator (integrator)
The coordinator owns:
1. the north-star objective and the single active integration route;
2. preflight against live `main` and the exact `CURRENT-STATE.md`;
3. retrieval and reuse of relevant prior records, including closed findings and failed approaches;
4. task decomposition, dependency ordering, work allocation and collision prevention;
5. the evidence ledger and cross-worker reconciliation;
6. decision about whether work meets acceptance criteria;
7. proposed canonical writeback and fetch-back verification;
8. later confirmation that a lesson changed a decision in a different task.

The coordinator can derive technical consequences from evidence and existing policy. It must not invent Owner authority, mark permissions open, merge a PR or describe another chat as contacted unless the corresponding action is actually authorized and evidenced.

### Worker chats / assistants
Each worker gets one unique task ID, one bounded question, an explicit read/write boundary, a named output contract and a stop condition. Workers do not redefine the north star, change `CURRENT-STATE.md`, edit the same file concurrently, or start an automatic follow-on. They report facts, source locations, uncertainties, proposed changes and exact tests/commands executed (or explicitly `NOT_RUN`).

Use ChatGPT, Codex, Claude/Sonnet, Devin, local models or other workers based on the *required capability and verified availability*, not brand preference alone. A worker's role is a current capability assignment supported by evidence, not a permanent identity.

## 3. Required preflight for every new chat

Before doing project work, each new chat/worker must:

1. Fetch live `main`; record the commit SHA and time of observation.
2. Read the current route from `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`. Do not reuse an old pasted route or infer authorization from a historical entry.
3. Read `IABV_v1.5/AGENTS.md` and apply the source-scope, safety, cost, branch and verification restrictions.
4. Retrieve only task-relevant context through `README.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md`, `ARCHIVE-REGISTRY.md` and named prior receipts. Start with the current route, then deepen retrieval by relevance; do not read or paste the entire archive by default.
5. Match supplied outputs to their exact `TASK_ID`, base SHA, branch/HEAD and acceptance criteria. A response from a stale task is historical evidence, not the current instruction.
6. State the lane's allowed actions, prohibited actions, expected evidence and stop condition before acting. If no matching authorized route exists, return `BLOCKED_ROUTE_OR_AUTHORITY` with the exact missing prerequisite instead of inventing work.

**Current inherited blocker (do not silently bypass):** live `CURRENT-STATE.md` at the start of this proposal records `ACTIVE_TASK=M1A_G1_RECONCILE_CANDIDATE_PRETASK_DIFF_PROVENANCE_20261025`, requiring a repository-relative current directory-to-directory delta and preservation package. It also records `PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED`, `PROTECTED_READS=FAIL_CLOSED`, `G1/G2/G3=NOT_ESTABLISHED`, and `AUTOMATIC_FOLLOW_ON=FALSE`. This proposal does not itself cancel that route or authorize product-source edits, tests against the product runtime, protected reads, credentials, deployments, merges or spending. The Owner's new collective-coordination direction can be developed as a documentary candidate and read-only work allocation while those limits remain in force.

## 4. Task packet contract

Every worker assignment must carry these fields. Do not assign a vague request such as “audit IABV deeply”.

```text
TASK_ID=
NORTH_STAR=GOVERNED_IABV_CODEX_BRIDGE
PARENT_TASK_ID=
BASE_REF=main
BASE_SHA=
CURRENT_STATE_SHA=
WORKER_ROLE=
QUESTION_TO_RESOLVE=
IN_SCOPE_FILES_OR_CONTRACTS=
OUT_OF_SCOPE=
READ_WRITE_SCOPE=READ_ONLY | ISOLATED_BRANCH_SOURCE_CANDIDATE | DOCUMENTATION_ONLY
PRECONDITIONS=
EXISTING_EVIDENCE_TO_REUSE=
ACCEPTANCE_CRITERIA=
EXPECTED_OUTPUT=
REQUIRED_PROVENANCE=
STOP_CONDITION=
COST_BUDGET=ZERO_BY_DEFAULT
AUTOMATIC_FOLLOW_ON=FALSE
```

For source work, add the exact working branch, file ownership, expected tests, protected surfaces, rollback/preservation plan, and who independently reviews the change. The coordinator must not mark a task “active” just because it wrote the packet; assignment/dispatch and acceptance have separate states.

## 5. Parallelism and workspace isolation

Parallel work is permitted only where dependencies and collision risk are explicit.

- **Read-only analysis:** multiple workers may analyze separate questions against the same pinned commit in parallel.
- **Implementation:** each worker uses its own branch and isolated checkout/worktree. One file or semantic contract has one active implementation owner at a time. Never let multiple workers independently edit the same live branch or the same shared Windows worktree.
- **No silent cherry-picking:** workers submit commits/branches/patches/PRs with base SHA, HEAD, changed-file list and test receipts. The integrator checks divergence, staged/unstaged/untracked files and overlap before composing changes.
- **Dependency-first integration:** merge or accept a foundational contract before dependent work starts. Independent tests/reviews can be parallel; source transformations across the same contract cannot.
- **Resource-aware concurrency:** set worker count from verified resources, quota, task complexity and review capacity. If parallel output exceeds integration capacity, reduce concurrency.
- **No speculative execution:** do not launch paid models, external browser sessions, code changes, system commands or follow-on workers unless the specific route permits them.
- **One integration route:** multiple branches can exist, but only one reconciled active integration task is represented by `CURRENT-STATE.md`.

## 6. Three disjoint first-pass work packets

These packets are deliberately **read-only**. Their purpose is to supply independent, non-overlapping evidence before any proposed source changes. They may be sent to separate helper chats. If this addendum is not yet canonical, use it as a draft handoff only; live `CURRENT-STATE.md` still governs permissions.

### `SPACE-COORD-01-CAPABILITY-TRANSPORT` — Helper A
**Question:** Where and why is task-level capability/readiness identity lost between `AdaptiveSession` and concrete `ToolTask`/tool selection on current live `main`?

Inspect only the narrow producer → transformation → consumer path in:
- `domain/models.py` (`AdaptiveSession`, `CapabilityReadiness`, `ToolTask`, `ToolCard`);
- `services/adaptive/adaptive_task_orchestrator.py`;
- `services/tools/tool_operational_executor.py`;
- `services/tools/tool_teach_service.py`;
- `services/tools/interaction_mode_selector.py` and the one immediate picker boundary if required.

Reuse the existing RQ21.40–RQ21.44 source reconciliations and capability-realization receipts. Do not repeat the broad repository inventory. Report exact current-main source facts, fields preserved/lost, each bypass/fallback path relevant to eligibility, the smallest candidate contract, unresolved semantics, and test cases. **Do not edit source or tests.**

### `SPACE-COORD-02-ROUTING-POLICY` — Helper B
**Question:** Which components actually influence the final model/tool/assistant choice, in which precedence order, and which score inputs are absent at operative call sites?

Inspect only:
- `services/roles/local_role_router.py`;
- `services/adaptive/adaptive_model_selector.py` and the current production call sites;
- `services/roles/synaptic_router.py`;
- `services/tools/interaction_mode_selector.py`;
- `services/tools/tool_teach_service.py` selection calls;
- `services/tools/tool_registry.py` fallback/picker behavior.

Return a decision table covering hard constraints, availability, quota, explicit user preference, historical learning, lexical fallback, unknown capability and empty eligible set. Trace operative callers, not merely class existence. Reuse prior routing reconciliations and report any newer contrary source. **Do not edit source or tests.**

### `SPACE-COORD-03-SPACE-TIME-DELIVERY` — Helper C
**Question:** What are the exact current-main links and gaps in objective-bound context retrieval, freshness, external session delivery, return correlation and later causal reuse?

Inspect only:
- `services/evolution/portable_context_service.py`;
- `infra/mcp/server.py` `portable_context_get` and related loader;
- `services/evolution/session_start_briefing_service.py`;
- the relevant `AppBootstrap` wiring;
- the existing Space-Time continuity algorithm audit and Oct. 24 Mente Espacio-Tiempo audit delta.

Use distinct states for source wiring, actual transport invocation, adapter acceptance, confirmed destination receipt, later decision use and measurable outcome. Preserve existing rich context; do not propose a second memory service. **Do not edit source or tests.**

## 7. Required worker return receipt

Each worker returns a single concise report with:

```text
TASK_ID=
STATUS=COMPLETE | PARTIAL | BLOCKED
OBSERVED_BASE_SHA=
OBSERVED_CURRENT_STATE_SHA=
SOURCE_PATHS_AND_SYMBOLS=
FACTS_WITH_LINE_OR_FUNCTION_REFERENCES=
PRODUCER_TO_CONSUMER_TRACE=
KNOWN_PRIOR_RECEIPTS_REUSED=
NEW_FINDINGS=
CONTRADICTIONS_OR_UNKNOWNS=
PROPOSED_MINIMUM_CORRECTION=
ACCEPTANCE_TESTS_PROPOSED=
TESTS_EXECUTED=NONE | exact commands and result
FILES_CHANGED=NONE | exact list
BRANCH_AND_HEAD=NONE | exact refs
EVIDENCE_CLASS=SOURCE_VERIFIED | REPORTED | INFERRED | PROPOSED | UNKNOWN
STOP_CONDITION_MET=
NEXT_ACTION_RECOMMENDED=
```

Workers should include short cited code fragments or line/function ranges, but not dump entire files. Do not expose secrets, tokens, credentials, personal account data or unrelated user information.

## 8. Coordinator adjudication and integration gate

The coordinator must not average conflicting conclusions or accept a class-name-only claim. Compare each return against:
1. exact `TASK_ID` and acceptance criteria;
2. the same live base SHA, or a clearly explained source delta;
3. source-level producer → transformation → consumer → decision use;
4. existing receipts and previous negative findings;
5. stated exclusions and actual changed files;
6. evidence stage reached.

Resolve differences by re-fetching the exact current source and asking one discriminator-driven follow-up, not by restarting a broad audit. When a worker's evidence is insufficient, record `PARTIAL` or `BLOCKED`. No conclusion about runtime delivery, agent receipt, protected-reader authorization or autonomous learning can be upgraded from static source presence alone.

After reconciliation:
- identify the earliest blocking dependency;
- choose one bounded correction owner per semantic/file area;
- write a small code-facing contract and independent review criteria before source edits;
- authorize an isolated candidate and its synthetic/focused tests through the current route;
- obtain an independent review;
- preserve base and worktree evidence, reconcile file overlap and build/test receipts;
- only then propose canonical adoption, update all required front doors in one reconciled change and verify fetch-back.

## 9. Criteria for claiming collective symbiosis

Use the following progressive stages; never collapse them into a single “learned” label.

1. `TASK_DEFINED`: packet exists with identity, bounds and acceptance criteria.
2. `DISPATCHED`: the owner/coordinator actually sent the packet to a named destination.
3. `RECEIPT_OBSERVED`: a destination-specific delivery receipt exists.
4. `RESULT_RETURNED`: the result is correlated with the same task ID and base revision.
5. `RESULT_ADJUDICATED`: evidence is compared with the original criteria and independently checked as needed.
6. `KNOWLEDGE_WRITTEN_BACK`: a durable, provenance-labelled delta is recorded and canonically fetched back.
7. `LATER_REUSE_OBSERVED`: a different task retrieves and cites the lesson.
8. `CAUSAL_EFFECT_DEMONSTRATED`: the later decision or outcome observably differs because of that lesson.

Only stages actually evidenced may be claimed. A ChatGPT conversation cannot silently access or control other independent ChatGPT chats. Those chats can collaborate through bounded packets and returned evidence, or through a supported transport if one is separately implemented and verified. This document does not establish such a transport.

## 10. Immediate result and stop rule

This addendum proposes a disciplined way to use the Owner's three-or-more helper chats without fragmenting the project. The three packets above form the first read-only swarm; the Space-Time coordinator remains the single integrator.

**No product-source fix is claimed by this document.** The active live-main route at the base of this proposal still requires the exact current directory-to-directory delta and preservation package. Do not bypass that requirement by editing a convenient branch, reading protected files, inventing authorization, changing production transport, or treating a stale task summary as authority.

The first implementation targets remain:
1. preserve typed capability demand through the normal task path and enforce it before preference/fallback;
2. harmonize operative routing precedence and pass only verified resource/health evidence;
3. make portable-context freshness and goal binding explicit;
4. correlate each external handoff with destination/package/task receipts and later reuse evidence.

These are candidate priorities from current source/static receipts, not authorization to implement them. The next work must follow a freshly reconciled live `CURRENT-STATE.md`.
