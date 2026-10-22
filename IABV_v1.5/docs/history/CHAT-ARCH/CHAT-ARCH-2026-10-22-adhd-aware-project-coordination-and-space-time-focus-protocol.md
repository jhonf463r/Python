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
