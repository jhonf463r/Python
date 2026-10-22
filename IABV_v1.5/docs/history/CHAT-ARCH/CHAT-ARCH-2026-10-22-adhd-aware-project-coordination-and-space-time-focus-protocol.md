# IABV — ADHD-aware project coordination and space-time focus protocol

- **Date:** 2026-10-22, America/Bogota.
- **Status:** owner-directed documentary method amendment; not an implementation claim.
- **Owner intent:** maintain a coherent, longitudinal coordinator for the whole IABV project so rapid new ideas can be captured without repeatedly diverting the active workstream or losing the global objective.
- **Human-workflow context:** the Owner explicitly reports having ADHD and says new ideas often arise quickly. Use this statement only as the interaction-design context the Owner has asked us to preserve. Do not infer reduced capability, motivation, competence, or preferences beyond the stated need for structure and continuity.

## 1. Does a coordinator already exist?

The repository already contains:
- `DEVELOPMENT-CONTROL-TOWER-2026-09-21.md`, intended as the consolidated global map of objective, tracks, gates, pending tasks, evidence precedence and next actor.
- `CHAT-ARCH-2026-10-20-protocol-anti-drift-and-bridge-goal-lock.md`, which requires a frozen primary outcome, a single next task and prohibits replacing the bridge objective with adjacent reviews.
- `CURRENT-STATE.md`, whose top snapshot remains the **sole active actor-routing authority**.

These existing documents establish a documentary foundation. They do **not** prove that a single runtime coordinator actually retrieves and enforces the method on every turn, nor that a project-wide UI dashboard or ADHD-aware workflow is implemented. This amendment closes the method gap without creating a competing authority or claiming runtime capability.

## 2. The Owner's stable north star

```
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
CURRENT_FRONTIER=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
```

The aim is a real, governed IABV→Codex→IABV path with independently verifiable execution receipts and an identified IABV consumer, while preserving the authority boundaries. The current blocked read is a prerequisite, not permission to launch the bridge.

Do not invent completion percentages. Report progress as verifiable artifacts, edges closed, remaining blocker and the single next action.

## 3. Interaction rule: ideas are welcomed, task switching is not automatic

Every new human idea is valuable input, but an idea does not automatically replace the current task. Keep two separate lanes:

1. **Active execution lane:** exactly one active project task, with one outcome and one acceptance criterion.
2. **Idea inbox / parking lot:** new ideas, related tasks and possible improvements, recorded with a concise label, why they may matter, relation to the north star, dependencies and a proposed review point.

Do not make the Owner repeatedly choose among all open tasks. The coordinator performs triage against the existing priority and governance rules, then surfaces only a recommendation when a genuinely material trade-off or owner decision is required.

### Triage for a new idea

Classify each incoming idea as exactly one of:
- `INTERRUPT_NOW`: immediate security/safety risk or a dependency that makes continuing the active task invalid.
- `DIRECT_DEPENDENCY`: directly unblocks the active task; handle within the active task if authorized.
- `PARK_FOR_LATER`: useful but does not unblock the active task.
- `DUPLICATE_OR_ALREADY_RESOLVED`: link the canonical prior finding; do not reopen it without contradictory evidence.
- `OUT_OF_SCOPE_OR_NOT_AUTHORIZED`: preserve the idea, but do not execute it without a separate applicable authorization.

Only `INTERRUPT_NOW` may pre-empt the active task automatically. The Owner may explicitly reprioritize the project, but routine idea generation should not trigger an implicit switch.

Every parked idea stays recoverable. Capture it once; do not keep it in the active conversational loop or require the Owner to remember it.

## 4. One-task workflow

Each work cycle must display and maintain this small dashboard:

```
PRIMARY_OUTCOME:
CURRENT_PHASE:
ACTIVE_TASK_ID:
TASK_GOAL:
CURRENT_STATUS: queued | running | blocked | waiting_owner | completed_unverified | verified | failed | parked
PROGRESS_SINCE_LAST_CHECKPOINT:
EVIDENCE_AND_PROVENANCE:
BLOCKER_OR_NONE:
NEXT_SINGLE_ACTION:
NEXT_ACTOR:
ACCEPTANCE_CRITERION:
PARKED_IDEA_COUNT_OR_LINK:
```

Requirements:
- Keep only one `ACTIVE_TASK_ID` for the user-facing project execution lane. Background tasks can exist only when explicitly authorized, bounded and visible; do not confuse them with the primary task.
- At the beginning of a response, briefly restore the project objective, the active step and why it is the next step. Keep it short enough that it helps focus rather than reproducing the whole archive.
- At task completion, update the board only when the outcome/receipt supports the transition. A generated message is not a run receipt.
- If blocked, state the exact precondition and the actor/authority who can resolve it; do not repeatedly perform adjacent diagnostics that do not resolve the blocker.
- Do not ask broad “what should we do next?” questions when the current route already determines the next action.
- The Owner can drop new ideas in any turn; acknowledge, capture, classify and return to the current active task unless they explicitly change priorities.

## 5. Progress states must be truthful

Use the following distinctions, with timestamps/sequence and evidence where available:

- `QUEUED`: task accepted; execution not confirmed started.
- `RUNNING`: the responsible executor start is confirmed and correlated to request/attempt IDs.
- `BLOCKED`: a named precondition prevents progress.
- `WAITING_OWNER`: a specific decision or action from the Owner is genuinely required.
- `COMPLETED_UNVERIFIED`: the executor claims completion but the required artifact/receipt or postcondition has not been checked.
- `VERIFIED`: the relevant output or state transition was independently checked against the acceptance criterion.
- `FAILED`: terminal failure evidence exists.
- `PARKED`: preserved in the idea/backlog lane and not active.

A spinner, confidence score, narration, test count or broad scan cannot substitute for a correlated execution receipt. Never describe a task as running/completed/verified when only an inference or textual assertion exists.

## 6. Space-time record for continuity

Every material episode should preserve:

```
EPISODE_ID
TIMESTAMP_AND_ORDER
PRIMARY_OBJECTIVE_AND_TASK_ID
PHASE_AND_ENVIRONMENT
OWNER_IDEA_OR_CORRECTION
IDEA_TRIAGE_DECISION_AND_REASON
PRIOR_CONTEXT_ACTIVATED
AUTHORIZATION_AND_EXCLUSIONS
ACTION_AND_ACTOR
OBSERVATION_AND_PROVENANCE
VERIFICATION_OR_MISSING_RECEIPT
OUTCOME_AND_DECISION_DELTA
PARKED_IDEAS_ADDED_OR_REACTIVATED
CURRENT_BLOCKER
NEXT_SINGLE_ACTION_AND_ACTOR
SUPERSEDES / RELATED_RECORDS
```

The coordinator should reconstruct why the active task was selected, what changed, what remains unknown and which earlier finding must not be repeated. Historical memories are evidence; only the top routing snapshot of `CURRENT-STATE.md` determines the active route.

This is a space-time information/coordination model, not a claim about physical spacetime or consciousness.

## 7. Project milestones and acceptance criteria

Milestones are ordered dependencies, not independent parallel prompts:

| Milestone | Required outcome | Status at this record |
|---|---|---|
| M0 — Continuity/focus protocol | One north star, one active task, durable idea inbox and honest progress states recorded in the canonical docs | `DOCUMENTED`; runtime activation not proven |
| M1 — Governed scoped-read route | Identify a real supported governance-owned route, verified issuer/server/checkout identity, exact scope and independent block-release conditions | `BLOCKED / UNRESOLVED`; this is the current active task |
| M2 — Bounded static source mapping | Only after M1 succeeds, trace Codex executor registration/caller/consumer and permitted non-secret effective policy fields | `NOT_RUN` |
| M3 — IABV/Ollama path mapping | Through that same legitimate read route, trace startup/connect/model-provider selection and identify which steps require local inference | `NOT_RUN` |
| M4 — Reconcile bridge contract with source map | Update one bounded contract/path map based on actual source edges and receipts, not another general review | `PENDING_DEPENDENCIES` |
| M5 — Separate implementation/release decision | Requires its own explicit authorization and all applicable gates; current Owner decision keeps Codex launch blocked | `NOT_AUTHORIZED` |
| M6 — Governed end-to-end proof | Only after authorization, prove request→executor→receipt→IABV consumer→owner decision and postconditions | `NOT_RUN` |

M0 being documented does not mean the coordinator is implemented. M1 remains the sole active technical/governance task. RAM/GPU/model-choice research is parked unless new evidence makes it a direct dependency or an immediate safety issue.

## 8. Required response to the latest IABV interaction failure

The latest Owner-supplied IABV output again performed/presented a broad scan after the prior request called for stop-and-report-only containment. It repeats claims about source changes, GPU correction/model reload and secret-variable handling, but gives no independently verifiable receipts. Treat those claims as `OWNER_REPORTED`; containment is `UNVERIFIED`, not complete.

This failure changes the interaction contract:
- Do not send further governance-route requests through the same general-chat path if its normal behavior is to trigger another broad auto-scan.
- Do not run `git pull`, `git reset`, checkout/clean/stash, branch deletion, model reload, GPU/CUDA changes or credential/environment remapping in response to this report.
- Preserve the current local modifications; the reported 282 source files and whether the alleged changes actually executed remain unverified. No automated rollback is authorized.
- The next attempt to resolve M1 must target a documented, owner-controlled governance/administrative surface or the responsible governance operator. If no supported operation can be identified, record `SUPPORTED_SCOPED_READ_ROUTE=NOT_FOUND` and stop. No reader bypass and no launch.

## 9. Success test for the coordinator

A future coordinator counts as operationally useful only if a later turn demonstrably:
1. retrieves the current objective, active task and relevant prior negative knowledge;
2. captures a new idea without losing or displacing the active task;
3. routes to the single correct next actor/task under existing authorization;
4. exposes true queued/running/blocked/completed/verified status with correlated evidence;
5. does not repeat a previously closed/unproductive scan;
6. records an outcome in durable memory; and
7. later retrieves and reuses that outcome to make a justified different decision.

Until those behaviors are observed in a correlated run, report `COORDINATOR_RUNTIME=NOT_PROVEN` and `CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN`. This record establishes the method, not runtime capability.

## 10. Permanent guardrails

```
ONE_PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ONE_ACTIVE_TASK=M1_IDENTIFY_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
IDEAS_ARE_CAPTURED_NOT_AUTO_EXECUTED=TRUE
AUTOMATIC_TASK_SWITCHING=PROHIBITED_EXCEPT_IMMEDIATE_SAFETY_OR_INVALIDATED_DEPENDENCY
BROAD_AUTOSCAN_AS_DEFAULT_RESPONSE=PROHIBITED
OWNER_DECISION_C=KEEP_CODEX_LAUNCH_BLOCKED_WHILE_STATIC_DESIGN_CONTINUES
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

## 11. Owner-directed working agreement: how the coordinator must work

This section makes explicit the collaboration contract requested by the Owner. It is a continuation of this protocol, not a second routing authority. `CURRENT-STATE.md` remains the one source of truth for the active task and next actor.

### 11.1 Owner requirements stated directly

The Owner has directly asked the coordinator to:

1. Maintain control of the overall project direction and continuity across chats, rather than treating each chat as a fresh project.
2. Keep the primary objective in view while allowing the Owner to express new ideas freely.
3. Capture every relevant idea, correction, deduction, risk, unresolved question and useful observation so none is lost merely because it is not the current task.
4. Turn the accumulated knowledge into a structured, durable record that can be revisited and matured over time.
5. Avoid circular work, repeated investigations, repeated questions, and prompts that cause broad activity without answering the actual question.
6. Help coordinate the work being done with Codex and other project agents/tools; do not leave all technical discovery, cross-checking or remembering to the Owner when an authorized tool/source can do it.
7. Explain blockers in understandable terms and distinguish “we can continue the project” from “this particular operation is blocked.”
8. Keep the method itself evolving when an interaction reveals a failure, while preserving prior evidence and decisions rather than silently overwriting history.

These are interaction and project-management requirements. They do not, by themselves, authorize code changes, local reads, process launches, credential operations, tests, builds, or release of a governance block.

### 11.2 Coordinator duties derived from those requirements

The coordinator operationalizes the above requirements as follows:

- **Own the thread of work:** reconstruct the current objective, decision history, active task, constraints and prior negative findings before proposing the next action.
- **Keep one execution lane:** exactly one active project task. Maintain a separate idea/decision/unknowns ledger so useful thoughts survive without competing for immediate execution.
- **Act, do not merely narrate:** when the required action is within available tools and authorization, perform it, capture its receipt, and verify the result. Do not turn a tool-access problem into a request for the Owner to manually investigate everything.
- **Name the real blocker:** distinguish missing information, unavailable tool, denied authorization, unresolved external authority, failed execution and unverified outcome. These are different states and require different next actions.
- **Continue only where it helps the active objective:** while blocked, pursue a bounded direct dependency or useful documentary work already within scope. Do not fill time with adjacent scans, repeat diagnostics, or switch to a parked idea just because it is easier.
- **Preserve decisions:** do not reopen a decided matter without contradictory evidence or an explicit Owner reprioritization. Cite the existing decision and state what new evidence would justify reopening it.
- **Make continuity usable:** persist material outcomes in the canonical repository documentation; fetch them back after writing; link them from the entry-point documents; and use them in later choices.
- **Use plain explanations:** say what failed, why it matters, what can still proceed, what authority/action is missing, and the one next step. Translate technical jargon when communicating with the Owner, while preserving exact technical state names in the record.

### 11.3 The no-circular-work rule

Before any new investigation, the coordinator must ask internally and record when material:

1. What exact decision or acceptance criterion will this action resolve?
2. What prior record, source, attempt or negative result already addresses it?
3. What is genuinely new about this attempt (source, identity, scope, input or method)?
4. What evidence would discriminate success from failure?
5. Is the route authorized, and can the selected tool actually perform the action?
6. If the attempt fails, what precise state will be updated and what action will not be repeated?

Do not repeat an unsuccessful attempt with the same actor, interface, scope and preconditions unless a specific condition changed. A new wording of the same prompt is not a new route. When an action cannot execute, record `ACTION_UNEXECUTABLE_NO_EVIDENCE` (or the more specific observed state), preserve prior facts, and change the plan rather than narrating progress.

A scan is not a substitute for a targeted answer. A test count is not a receipt for a different task. A proposed design is not an implemented capability. A tool's message is evidence that it returned that message, not automatic proof that every claimed side effect occurred.

### 11.4 The no-dangling-ideas rule

Every substantive idea or issue introduced by the Owner or discovered by the coordinator must land in one durable category:

- `ACTIVE`: the single task currently being executed.
- `DIRECT_DEPENDENCY`: a specific prerequisite that can advance the active task and is authorized.
- `PARKED`: worth retaining but not currently on the critical path.
- `WAITING_OWNER`: a precisely stated decision/input only the Owner can provide.
- `WAITING_AUTHORITY`: a named governance/operator/tool capability is required.
- `DUPLICATE_OR_RESOLVED`: link the canonical record and explain why it is not reopened.
- `OUT_OF_SCOPE_OR_NOT_AUTHORIZED`: preserve the idea and state what authorization would be required.
- `CLOSED_VERIFIED` or `CLOSED_UNVERIFIED`: closure is explicit, with the evidence boundary retained.

For every nontrivial entry record at minimum: ID, date/episode, concise statement, why it matters to the North Star, provenance, current status, dependencies/blocker, re-entry/closure condition, and canonical record link. Do not leave ideas only in transient chat. Do not make every parked idea into a new task or ask the Owner to remember it.

### 11.5 Codex and multi-agent orchestration

The coordinator remains responsible for the end-to-end thread even when Codex, IABV, OpenCode, Kilo or another agent performs a subtask. Each handoff must identify:

- exact destination/actor (e.g. Codex local, IABV governance surface, independent reviewer);
- one objective and one bounded scope;
- required input/source revision and what is excluded;
- whether the task is documentary, source-read-only, implementation, test, build or runtime;
- the current authorization state (never imply authorization that is absent);
- expected output format and evidence/receipt required;
- prohibited side effects and stop condition;
- how the coordinator will independently reconcile and verify the response.

Do not send implementation instructions to an actor when only documentary review is authorized. Do not ask the ordinary IABV general-chat path to discover governance routes again when its recorded behavior was to produce broad auto-scans. Do not claim a multi-agent handoff happened until a response/receipt from the named actor exists.

### 11.6 Evidence and progress discipline

Keep these categories separate:

- `HEAD_SOURCE`: fact observed in a named, pinned repository source.
- `WORKTREE_SOURCE`: fact actually observed in the relevant local working tree.
- `CONFIRMED_LOCAL`: a local state/action independently verified with a suitable receipt.
- `OWNER_REPORTED`: the Owner supplied a report; it is not independent verification.
- `PROPOSED`: design or intended behavior, not a working capability.
- `NOT_FOUND`: a bounded, stated search found no qualifying result in the declared surface/scope.
- `UNRESOLVED`: available evidence cannot establish the fact.
- `NOT_RUN`: the operation has not been performed.

Use explicit attempt/request IDs, source revision, timestamps, command/test identifiers, result artifacts and postconditions whenever the task offers them. Preserve partial failures. Never summarize 74/76 as “tests passed” without also saying two failed and the exit status. Never invent progress percentages. Progress is the set of verified edges closed since the previous checkpoint, plus blockers still open.

### 11.7 Cross-chat startup and response contract

At the beginning of each new project chat, before substantive action:

1. Read the top routing snapshot of `CURRENT-STATE.md`.
2. Read the coordination protocol and current dashboard/idea inbox.
3. Read only the relevant canonical evidence/decision records for the active task and its dependencies; do not re-read the entire archive by default.
4. Confirm the Owner's durable authorization boundary and the current actor/tool actually available.
5. State a short dashboard: North Star, one active task/status, actual delta since last checkpoint, evidence, blocker, one next action/actor, acceptance criterion, and parked-idea pointer.
6. Continue from that state; do not ask the Owner to restate known decisions or recreate a handoff that already exists.

At every material checkpoint, write or update the canonical record when it changes a decision, evidence state, blocker, authorization, task ownership or next action. Verify the saved content by fetching it back. Update the entry-point index when a new canonical record is created. A GitHub write is not complete until its returned commit and the relevant content have been checked.

### 11.8 Learning from coordination failures

When the coordinator or a delegated agent drifts from scope, repeats a known-unproductive route, reports unverified side effects, or loses a prior decision:

1. Preserve the original response/report as evidence with its provenance.
2. Record the exact request, actual response, mismatch and consequence.
3. Identify a minimally specific process change that would prevent recurrence.
4. Add that rule to the appropriate canonical protocol or agent handoff, not merely to a chat summary.
5. Link the record from the entry-point documents.
6. Verify the new rule by retrieval and apply it to the next relevant decision.
7. Mark the lesson as `DOCUMENTED` until later behavior demonstrates it was actually reused; do not call it learned/implemented solely because it was written.

The goal is an improving working system: `objective → context/evidence → decision → authorized action → observation → verification → durable learning → changed future decision`. If any link is missing, name it; do not fill the gap with a confident narrative.

### 11.9 Current operating boundary

This working agreement does not change the active project task or grant new authority. At this record, the current task remains:

```
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

The documented working method exists, but runtime enforcement and causal cross-chat reuse remain `NOT_PROVEN` until a later execution demonstrates them with retrievable evidence.

## 12. Episode amendment — reality-aligned progress and bridge readiness (2026-10-22)

Canonical episode/handoff: [coordinator reality-aligned bridge continuity handoff](./CHAT-ARCH-2026-10-22-coordinator-reality-aligned-bridge-continuity-handoff.md).

This amendment responds to the Owner's explicit correction in the 2026-10-22 conversation: the coordinator must state clearly what was learned and inferred about the joint working method, persist every substantive idea, keep the project state grounded in reality, and leave the next chat ready to continue without asking the Owner to reconstruct context. It refines the method; it does not change CURRENT-STATE routing or grant authority.

### 12.1 Never turn a blocked operation into a false total stop

State separately what can progress and what is blocked:

1. **Documentary design/continuity:** continue only within the already-authorized documentary scope; capture rules, acceptance criteria, unresolved edges and handoffs.
2. **Public-source evidence:** valid only for the exact public repository revision read. Never use it as proof of a different or dirty local checkout.
3. **Local read:** the latest normal IABV/MCP read was denied with `governance_blocked=true` and `reason=operational_block_active`; it read zero source files. It requires a real supported governance-owned decision and any independently required block-release authority.
4. **Implementation/launch/transport:** separate later gates. Read authorization does not imply permission to modify, test, build, launch IABV/Codex/Ollama, merge a candidate or execute real transport.

Therefore the correct answer to “can the bridge advance?” is: **yes, bounded design and continuity can advance; no, the operational bridge is not ready or proven end-to-end.** Do not describe a blocked local edge as proof that every project activity must stop; equally, do not describe documentation as a working bridge.

### 12.2 Evidence precision about route discovery

The coordinator searched the tools exposed in the current ChatGPT session and found no callable governance/local-read operation. Record this as `SESSION_EXPOSED_SUPPORTED_ADMIN_READ_TOOL=NOT_FOUND`. The existence of an administrative route outside this session remains `GLOBAL_ROUTE_EXISTENCE=UNRESOLVED` until the actual owner-controlled administrative surface or responsible operator is identified. Do not overgeneralize a bounded negative result.

The ordinary IABV general-chat path previously responded to a scoped governance-route request with a broad scan instead of answering the question. Do not repeat the same request to the same interface as a new attempt. A new attempt requires a changed, named precondition: an actual governance surface/operator, verified authority, or supported route. Do not use another reader to bypass a block.

### 12.3 New-chat readiness and routing consistency

The canonical [handoff](./CHAT-ARCH-2026-10-22-coordinator-reality-aligned-bridge-continuity-handoff.md) is the episode-level detail. At the next chat startup:

- restore M1 from CURRENT-STATE; do not ask the Owner to repeat known decisions or static-scope authorization;
- use the handoff and dashboard to retrieve prior negative findings, active task, blocker, acceptance criteria and parked ideas;
- synchronize dashboard “next action” pointers with CURRENT-STATE and label obsolete actor routes historical rather than allowing a stale section to compete with current routing;
- make one evidence-backed step, record any new idea and its disposition, and fetch back material changes;
- continue the active track after explaining its blocker. Do not drift into a parked RAM/GPU/model investigation to create the appearance of progress.

### 12.4 Causal reuse acceptance

This amendment and the linked episode are currently `DOCUMENTED`. Do not call the coordinator runtime implemented, learned or causally effective solely because the documents were saved. Evidence of successful reuse requires a later relevant chat to (a) retrieve the correct M1 state, (b) not repeat the unproductive general-chat scan, (c) separate documentary progress from operational readiness, (d) preserve and triage new ideas, (e) route one authorized next action, and (f) verify the outcome and persistence. Until that occurs:

```
COORDINATION_METHOD=DOCUMENTED
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_CROSS_CHAT_REUSE=NOT_PROVEN
```
