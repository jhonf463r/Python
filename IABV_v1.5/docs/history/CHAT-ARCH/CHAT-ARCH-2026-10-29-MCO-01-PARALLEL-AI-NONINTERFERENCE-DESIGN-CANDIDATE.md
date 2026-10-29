# MCO-01 — Multi-AI Parallel Work and Non-Interference Contract (Design Candidate)

**Date:** 2026-10-29  
**Status:** `PROPOSED / DRAFT PR / NOT CANONICAL / NOT ACTIVE`  
**Task ID:** `MCO_01_PARALLEL_AI_NONINTERFERENCE_20261029`  
**Scope:** repository-grounded design and coordination contract only  
**Baseline observed:** `main@1430ad5062298a8dd5719ccb2882e2ce4877b283`  
**Code/tests/build/runtime changed or run:** `NO`  
**Canonical routing file changed:** `NO`  
**G1/G2/G3, MCP bridge, protected reads, tunnel, PRs #555/#556/#557:** `NOT TOUCHED`

> This is a candidate lane contract, not a new routing authority. It does not override `CURRENT-STATE.md`, activate implementation, or claim that IABV can autonomously dispatch multiple external AIs. It becomes canonical only if accepted and merged through the existing governed process.

## 1. Owner objective

Enable ChatGPT, Codex and other participating agents to contribute to different IABV layers or organs concurrently **without competing over task authority, writing the same resources, losing provenance, silently replacing one another's decisions, or merging incompatible changes**.

The goal is governed parallelism, not uncontrolled concurrency and not another central brain.

## 2. Current-source evidence

All observations below are bounded to the listed source files on the pinned `main` baseline. They do not assert that every possible implementation path in the whole repository has been exhaustively disproven.

| Surface | Verified source observation | Consequence |
|---|---|---|
| Canonical route | `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` declares itself the sole authority for active task, next action, gates and permissions. Exact current blob was recovered after the normal fetch returned empty. | Keep one root route; never add a competing project-state router. |
| Focus/coordination protocol | `CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md` calls for exactly one active project task and says milestones are ordered dependencies rather than independent parallel prompts. | The current method prioritizes focus and serialization. Parallel child work needs an explicit contract change; it cannot be inferred from the existing wording. |
| Collaboration protocol | `IABV-COLLABORATION-COORDINATION-PROTOCOL-2026-10-04.md` defines one GitHub-backed coordination frame, capability-fit actor selection, bounded task packets, evidence-bearing handoffs and independent reconciliation. It forbids a second coordinator brain. | Existing authorities should be composed; no new universal dispatcher should be added merely to support parallelism. |
| Pending-task queue | `src/iabv_v15/services/evolution/platform_pending_queue.py`, blob `48a262d677f4bd8a01dfe2d74afac8e1e306fe59`, exposes `upsert/get/list_all/list_actionable/list_blocked/mark_status/summary`. Its inspected surface contains no explicit claim, lease, reservation, owner or path-lock operation. | It is a durable pending-work queue, not demonstrated exclusive task ownership for concurrent agents. |
| Platform-pending data model | `src/iabv_v15/domain/models.py`, blob `a9033d21052c519e09f482097599c704a62ea916`, defines `PlatformPendingTask` with identity, title, description, dependency, priority, status, next action, timestamps, resume hint and generic metadata. | The model is useful for pending work but does not declare a first-class concurrent work-lane/path-reservation contract. |
| Tool task model | The same `models.py` defines `ToolTask` with `task_id`, `tool_id`, objective, status, actions, scope, approval, sandbox flag, session/run/pack IDs, expected outcome and metadata. | These fields support tool tasks, but the inspected schema does not bind a task to a canonical parent lane, baseline commit, owned repository paths, branch/PR, or expiring exclusive claim. Metadata is not proof that these semantics are enforced. |
| Task/result persistence | `src/iabv_v15/infra/persistence/tool_record_repository.py`, blob `0576b5c91d10319a3b7b81d3d2f07ce4c4c27ffe`, persists ToolTask and ToolResult records. | Persistence alone is not a concurrency-control or merge-conflict protocol. |

Sources:
- [Canonical routing authority](./CURRENT-STATE.md)
- [Focus and coordination protocol](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md)
- [GitHub-backed collaboration protocol](./IABV-COLLABORATION-COORDINATION-PROTOCOL-2026-10-04.md)
- [PlatformPendingQueue source](../../../src/iabv_v15/services/evolution/platform_pending_queue.py)
- [Task model source](../../../src/iabv_v15/domain/models.py)
- [Task/result repository source](../../../src/iabv_v15/infra/persistence/tool_record_repository.py)

## 3. Diagnosis

The project already has:
- one canonical root routing/state document;
- objective-conditioned context assembly and portable-context composition;
- a task queue and persisted tool-task/result records;
- tool/capability discovery and readiness surfaces;
- source/evidence/decision history;
- GitHub branches and pull requests for isolated candidate changes;
- a capability-fit cross-AI handoff protocol.

The gap demonstrated by this audit is narrower:

1. The human collaboration protocol currently specifies one active task, not an explicit parent objective with multiple authorized child packets.
2. The inspected pending queue does not itself claim work exclusively for an agent or reserve a resource/file scope.
3. The inspected ToolTask schema does not make repository baseline, branch/PR, path ownership and agent claim first-class execution-contract fields.
4. Git branches isolate commit histories, but they do not by themselves prevent two agents from editing the same logical responsibility or prove that a merge is semantically compatible.
5. The external IABV-to-AI dispatch/approval path is subject to a separate active governance/bridge lane. This candidate must not implement around, weaken or duplicate that route.

Therefore, the best first step is to define and trial a **GitHub-native, branch-isolated child-work contract**. Runtime concurrency, automated dispatch and any new reservation service require a later bounded design decision and separate authorization.

## 4. Proposed operating model

### 4.1 One root objective, multiple bounded child packets

- `CURRENT-STATE.md` remains the sole authority for the one active parent objective, current route, gates and permissions.
- A parent objective may authorize multiple child packets only when their dependency relationships and write scopes are explicit.
- A child packet is not a second router, a second project-state file or permission to change the parent route.
- Unrelated ideas remain in the existing idea inbox/backlog; they do not become active merely because an agent discovers them.
- This is a proposed refinement of the current one-task rule. It is **not effective until the owner accepts the change**.

### 4.2 Minimum child-work packet

Every child task must declare:

1. A unique `CHILD_TASK_ID` for this immutable packet revision and a `PARENT_TASK_ID` linking it to the parent objective. Follow `TASK_ID_POLICY=NEW_TASK_PER_REVISION`: if the base, scope, accountable actor, dependencies, permissions or acceptance contract materially changes, mint a new child task ID and link `SUPERSEDES_CHILD_TASK_ID`; never reuse an ID for a changed contract.
2. Exact base `main` SHA and, if relevant, candidate branch/HEAD SHA plus PR URL/number or `NOT_CREATED`.
3. One objective, one expected outcome and one acceptance criterion.
4. Named actor or accountable agent, required capability and reason for selection.
5. Allowed paths (or a precise, non-overlapping source scope) and forbidden paths.
6. Dependencies, prior evidence to reuse, and known closed edges that must not be repeated.
7. Action class: documentation, source-read-only, implementation, test, build or runtime.
8. Exact permissions and prohibited side effects.
9. Expected artifacts and provenance, verification method, and explicit stop condition.
10. Return format: observed action, source/commit, artifact, what is proved, what is not proved, blocker, and next open edge.
11. `CURRENT_STATE_SHA` and `observed_at_utc` for the route/snapshot used to create the packet. If either cannot be verified, record `UNKNOWN` and stop any consequential handoff until the missing source is reconciled.

A task without a baseline, owner, scope or acceptance criterion is not eligible for parallel execution; keep it queued or blocked.

### 4.3 Isolation and ownership

- One child work packet uses one isolated Git branch and, where local execution is involved, one isolated worktree.
- The branch begins at the packet's declared base SHA; the report must identify the actual resulting HEAD.
- Parallel children may write concurrently only when their owned paths and semantic responsibilities do not overlap and their dependencies are satisfied.
- A shared file, canonical route, shared contract, bootstrap path, authorization gate or common semantic owner has one writer at a time. Other tasks may review it read-only.
- No child writes directly to `main`, silently resets another worktree, overwrites another branch, merges a candidate, or changes another task's status.
- If a child discovers that its scope overlaps another task, it stops before writing and reports the collision. The root coordinator resolves the conflict or serializes the tasks.
- GitHub branch/PR separation is the first isolation boundary; it is not a claim of operating-system sandboxing or complete runtime confinement.

### 4.4 State and integration

Use the existing coordination progress vocabulary where possible (`QUEUED`, `RUNNING`, `BLOCKED`, `WAITING_OWNER`, `COMPLETED_UNVERIFIED`, `VERIFIED`, `FAILED`, `PARKED`) and GitHub PR state. Do not create a duplicate state database.

- A child report cannot mark itself integrated or change the canonical next action.
- Each PR returns its base SHA, head SHA, changed paths, result evidence, tests actually run (or `NOT_RUN`) and unresolved risks.
- A single integration/reconciliation activity processes accepted children serially. Re-read live `main`, check staleness and path conflicts, review the exact diff, run only authorized validation, merge only under existing approval gates, then fetch back the merged content.
- If a base becomes stale, a scope overlaps, the required evidence is missing, or the integration conflicts, classify the packet as blocked/stale rather than force-merging.
- Any proposed claim/lease/heartbeat, idempotency, cancellation or automatic requeue mechanism requires a separate explicit contract. Do not infer it from file persistence or a status enum.

## 5. No second brain / no bypass

This design must reuse the existing ownership boundaries:
- `CURRENT-STATE.md` — sole current project route;
- existing collaboration and Space-Time continuity protocols — task framing, evidence and adjudication;
- `PlatformPendingQueue` / evolution backlog — relevant existing pending-work surfaces after an ownership/composition check;
- `ToolTask` / `ToolRecordRepository` / existing orchestrator — only for tool-execution semantics they actually support;
- GitHub branches and PRs — first bounded isolation and review surfaces.

Do not create a new `ResearchOrchestrator`, `ParallelBrain`, `UniversalTaskManager`, second memory, second task router, or new queue merely because current ownership is difficult to trace. A runtime component may be considered only if the next bounded audit demonstrates an irreducible ownership gap in the existing organs.

## 6. Relationship to RSK-01 and system evolution

RSK-01 already specifies the separate product-level objective of objective-conditioned, provenance-aware retrieval across code, memory, capabilities, relations, currentness, outcomes and negative knowledge. This candidate does not replace RSK-01 and does not re-run its historical static audit.

The two concerns must remain distinct:
- **MCO-01:** prevent concurrent work from colliding and make every child result attributable and integrable.
- **RSK-01:** retrieve the right knowledge and organs for a given objective.

MCO-01 can use GitHub PRs and explicit scopes without waiting for the runtime bridge. RSK-01 may continue as a separate read-only/design lane when selected by the canonical route. Neither should be used to bypass the other one's dependencies.

## 7. Explicit exclusion of the separate G1/G2/G3 lane

This candidate does not:
- modify, relaunch or adjudicate the other chat's G1/G2/G3 task;
- edit or merge PRs #555, #556 or #557;
- change `OPTION_D`, `MCP_TOOL_ALLOWLIST`, protected-read policy, tunnel policy, bridge status, credentials or authorization gates;
- activate MCP transport or automate external-agent launch;
- inspect secrets, use the local dirty checkout, execute source, run tests/builds or change product code;
- claim automatic GitHub memory boot, autonomous delegation or runtime parallelism.

Current observed main route remains the D021 documentation-closeout route; this file does not replace it. Separate owner authorization is required before product implementation, test/build/runtime or changes to technical gates.

## 8. Acceptance criteria for the design lane

MCO-01 is ready to leave design review only when all criteria are met:

1. The parent/child model preserves one canonical route while explicitly permitting authorized independent child work.
2. The packet fields above are sufficient to identify exact baseline, actor, scope, permissions, dependencies and evidence.
3. The contract specifies one writer per shared path/semantic responsibility, collision detection, stop-before-write and serialized integration; automatic runtime enforcement is not claimed.
4. A bounded conflict matrix covers at least: disjoint paths, overlapping paths, stale base, missing dependency, canceled child, duplicate submission, unavailable actor, blocked authorization and integration conflict.
5. The design reuses current records and GitHub objects where adequate and names no new runtime organ without proof.
6. A first low-risk pilot is specified with separate child branches/PRs, disjoint owned paths, exact baseline evidence and explicit stop/merge gates, without touching the G1/G2/G3 lane or changing protected gates.
7. Runtime dispatch, ownership leases and automated concurrency are marked unproven until separate evidence exists.

### 8.1 Reconciliation with the current route and adjacent proposals

**One active parent route, subordinate child work only.** The live `CURRENT-STATE.md` fetched from main at `1430ad5062298a8dd5719ccb2882e2ce4877b283` remains the sole routing authority; its current blob SHA is `b5fbf879e95d92869e51fa2ae29d4fce5ca56bdb`. Its active route is still the UAAL-D021 continuity-documentation closeout, with technical gates unchanged. This MCO-01 review is a separately requested, documentation-only consultation. It does not replace that route, create a second active integration route, or authorize a pilot by implication.

The focus protocol at the same main baseline defines exactly one active project task and treats milestones as ordered dependencies rather than independent parallel prompts. MCO-01 must be read as a bounded refinement: there remains one active parent/integration route; child packets are subordinate and may run in parallel only when the parent task/Owner explicitly authorizes them, the current route allows the operation, dependencies are satisfied, and write scopes are disjoint. In the absence of those conditions, the existing one-task/serial rule controls. A child packet never updates `CURRENT-STATE.md` or changes technical permissions.

**PR #522 — useful but stale proposal, not a governing route.** At this review snapshot, #522 is open/draft, has no requested reviewers, and adds only `CHAT-ARCH-2026-10-25-COLLECTIVE-IA-COORDINATION-DIRECTIVE.md`. Its base is `5965735167b50d12bc98543d132d70022fb73803`, its HEAD is `8fd2e3f02f13ab75e828c9ae6ee33565ab90b2c6`, and comparison to live main returns `diverged`, 4 ahead / 173 behind. Reuse its intent classification, task-packet fields and delivery/receipt distinctions as design input to the existing Space-Time/MOP protocol. Do not copy its entire routing taxonomy into MCO-01 or merge its stale branch as a shortcut.

**PR #523 — historical audit checkpoint, not current state.** At this review snapshot, #523 is open/draft, has no requested reviewers, and adds only `CHAT-ARCH-2026-10-25-COLLECTIVE-COORDINATION-AUDIT-CHECKPOINT.md`. Its base is `5965735167b50d12bc98543d132d70022fb73803`, its HEAD is `abf90cd3dbdb2fff1ce2c47310cfa5888d24b1f6`, and comparison to live main returns `diverged`, 4 ahead / 172 behind. Reuse its bounded static findings as historical evidence with their original baseline and evidence labels; do not promote its copied route, W0–W6 queue or historical SHAs to current routing authority.

The three candidate PRs have different changed paths, so there is no exact-path collision between the one-file candidates #522, #523 and #569 at this snapshot. Their overlap is semantic: #522 addresses conversation intent and delegation/receipt framing; #523 preserves earlier findings and a dependency-ordered review queue; MCO-01 addresses concurrent child-scope ownership and integration collisions. Keep those responsibilities distinct and consolidate accepted rules into the existing owning protocol only after review and authorization. `CURRENT-STATE.md` remains the one route; MCO-01 is not a new service, queue, memory or router.

## 8.2 Required conflict and acceptance matrix

The following matrix closes criterion 4 at the design level. Status labels below reuse existing coordination states; `reason` is evidence attached to the existing record, not a new state database or runtime state machine. The matrix specifies a human/integrator-enforced contract and does not claim that software currently enforces it automatically.

| Case | Detection / precondition | Mandatory behavior | Result state and required evidence |
|---|---|---|---|
| **1. Disjoint paths** | Each child has the same declared baseline, satisfied dependencies, an explicit allowed/forbidden path set, and no exact-path or semantic-owner overlap after comparison. | Parallel work is permitted only when parent authorization and current route allow it. Use separate branches/worktrees; each child must report its actual HEAD and complete changed-path list. | `QUEUED` → `RUNNING` → `COMPLETED_UNVERIFIED`; record parent/child task IDs, `CURRENT_STATE_SHA`, observation time, base SHA, branch/HEAD, changed paths and evidence. Independent adjudication is still required before `VERIFIED` or integration. |
| **2. Overlapping paths or shared semantic responsibility** | Exact path intersection, rename collision, generated artifact collision, or shared contract/owner such as `CURRENT-STATE.md`, bootstrap, authorization or common API, even if path names differ. | No concurrent writers. Assign one writer for the shared scope; other work may remain read-only. If overlap is discovered after work starts, stop before the next write, preserve the candidate and report the collision. | `BLOCKED`, reason `OVERLAP_UNRESOLVED`; attach intersecting paths or semantic rationale, affected task IDs and the authorized resolution/serialization decision. |
| **3. Stale base** | Live `refs/heads/main` or the current route changed after the packet's recorded snapshot, or the candidate cannot be compared against the recorded base. | Re-fetch live main and `CURRENT-STATE.md`; recompare base/HEAD/path sets and dependencies. Mark the candidate stale for publication/integration until re-adjudicated. Do not automatically rebase, reset or retarget it. Work may continue read-only only if still in scope and authorized. | `BLOCKED`, reason `STALE_BASE` / `STALE_FOR_INTEGRATION`; record old and current SHAs, observation time, compare result and the decision to resume or stop. |
| **4. Missing dependency** | A declared predecessor is missing, not accepted, not independently verified where required, or its exact artifact SHA cannot be retrieved. | Do not start dependent writing or integration. Do not substitute a narrative handoff or newer unrelated artifact for the declared dependency. | `BLOCKED`, reason `DEPENDENCY_UNMET`; identify the required predecessor task ID and exact SHA/evidence still missing. |
| **5. Canceled child** | Owner/coordinator cancels the child, parent authority is withdrawn, or a required precondition no longer holds. | Stop work, preserve the branch/artifacts and current evidence, and exclude the child from integration. Do not auto-requeue it; any later restart needs a new authorized task revision. Ignore a late result for execution purposes unless explicitly re-adjudicated. | Use the existing `PARKED` status with `terminal_reason=CANCELLED`; retain cancel source/time, last observed HEAD and preserved artifacts. |
| **6. Duplicate submission** | Same task revision or artifact appears twice, or separate IDs claim the same parent/base/scope/objective without a justified distinction. | For identical ID + contract + artifact SHA, handle idempotently and keep one authoritative result. For divergent outputs under the same ID, stop and adjudicate; do not choose the latest response automatically. A material contract change requires a new task ID linked by `SUPERSEDES_CHILD_TASK_ID`. | `BLOCKED` when divergent or semantically duplicate; record both IDs, base/HEAD/artifact hashes and the adjudication. No new database or automatic retry is implied. |
| **7. Actor unavailable** | The selected actor, capability, destination or supported delivery route cannot be verified as available. | Keep the packet queued or waiting for an Owner decision. Do not claim dispatch/receipt. Reassign only through an authorized decision; if actor, permissions or scope materially changes, create a new task revision and link the superseded ID. | `QUEUED` or `WAITING_OWNER`; record `HANDOFF=PREPARED_NOT_SENT` / unavailable route, capability required and the exact prerequisite for resumption. |
| **8. Authorization blocked** | The current route does not authorize the requested action, a technical gate is not established, or the only proposed method bypasses a blocked route. | Stop. Do not try another tool, transport, branch or actor to evade the denial. Preserve all existing gates; the MCO child contract cannot grant permission. | `BLOCKED`, reason `AUTHORIZATION_NOT_ESTABLISHED`; cite the exact current-state blob/field, disallowed operation and missing authorization. No code, protected read, test, runtime, credential or merge action follows implicitly. |
| **9. Integration conflict** | Git reports a conflict, shared semantics are incompatible, `main` moved after review, acceptance evidence is absent, required checks fail, or required branch policy/merge authority cannot be verified. | Do not force-merge or declare compatibility from `mergeable=true` alone. Preserve both candidates; one integrator re-fetches live main, resolves the exact conflict with an authorized owner, serializes integration and revalidates each remaining candidate afterwards. | `BLOCKED`, reason `INTEGRATION_CONFLICT`; record exact main/base/HEAD SHAs, affected paths, checks/reviews, the unresolved decision and stop condition. Merge/fetch-back remains a separate authorized action. |

## 8.3 Design acceptance adjudication

| Criterion | Outcome from this revision | Boundary that remains |
|---|---|---|
| 1. One canonical route and explicitly authorized child work | `PASS_DESIGN` — one parent/integration route; subordinate children do not route or grant permission. | The existing focus/one-task rule remains in force unless child work is separately authorized. |
| 2. Exact packet identity, baseline, actor, scope, dependencies and evidence | `PASS_DESIGN` after adding the current-state blob and observation time. | No packet may claim an unavailable source SHA or delivery receipt. |
| 3. Single-writer scope and serialized integration | `PASS_POLICY_SPECIFIED` — collision detection, stop-before-write and serial reconciliation are explicit. | Runtime enforcement/locking is `NOT_PROVEN`; the control is procedural until an authorized implementation and evidence exist. |
| 4. Nine required conflict cases | `PASS_DESIGN` — all nine cases are specified in §8.2. | This is a decision matrix, not evidence that all cases have been exercised in a pilot. |
| 5. Reuse existing records/GitHub without a new organ | `PASS_DESIGN` — use `CURRENT-STATE`, current coordination protocols, existing queue/task records and PR/branch metadata. | A new lease, reservation, idempotency service or scheduler needs a separate gap demonstration and authorization. |
| 6. A bounded low-risk pilot is specified | `PASS_PLAN_ONLY` — §9 defines prerequisites, child isolation, evidence and integration stop gates. | No pilot is dispatched or run by this document; selection of real tasks and any merge need separate authorization. |
| 7. Runtime dispatch/concurrency remains unproven absent evidence | `PASS_BOUNDARY` — no autonomous coordination claim is made. | `DISPATCH`, `RECEIPT`, runtime behavior and later causal reuse require their own evidence stages. |

**Review status:** `DESIGN_SPEC_COMPLETENESS=PASS_WITH_BOUNDARIES`; `INDEPENDENT_REVIEW=NOT_DONE`; `OWNER_ADOPTION=NOT_DONE`; `CANONICAL=NO`; `PILOT=NOT_AUTHORIZED_NOT_RUN`. This is enough to submit the design package for independent review, not to mark the PR ready, merge it, or update the current route.

## 9. Recommended next action

Review this candidate against live `main` and the owner’s active direction. If independently reviewed and accepted, adopt only the accepted child-packet policy in the existing owning coordination protocol—not as a second protocol or router—using a separately authorized, bounded documentary update and exact fetch-back verification. Then, separately, authorize a low-risk isolated pilot. Do not proceed directly to a runtime scheduler or external-AI dispatcher.

### Bounded low-risk pilot specification (proposal only; not dispatched or run)

**Preconditions.** First refresh live `main` and the exact `CURRENT-STATE.md` blob; preserve the single parent route and all technical gates. Identify two genuinely useful, already authorized child tasks from the live backlog with distinct source/semantic scopes. Do not invent work merely to test parallelism, reopen closed findings, or derive task authority from this proposal. Verify that two suitable actors/destinations are actually available; if no supported destination exists, return `PILOT_BLOCKED_ACTOR_OR_ROUTE` and keep any handoff `PREPARED_NOT_SENT`.

**Packet A and Packet B.** Each packet gets a unique immutable child ID, the same recorded `main` base SHA, `CURRENT_STATE_SHA`, observation time, separate branch/worktree, explicit allowed/forbidden paths, dependencies, acceptance oracle, permissions, evidence output and stop condition. The output paths must be different new non-canonical evidence artifacts selected after preflight; neither packet may edit `CURRENT-STATE.md`, this MCO-01 contract, `AGENTS.md`, the shared collaboration protocol, G1/G2/G3 artifacts, MCP/bridge/security gates, or files owned by another active PR. If no safe non-overlapping work exists, do not launch the pilot.

**Execution and reconciliation.** The two children may work in parallel only after an explicit authorization for the pilot and only on their isolated branches. Each returns its exact base/HEAD, complete changed-path set, evidence provenance, actions/tests actually executed (or `NOT_RUN`), unresolved risks and status. The integrator compares both outputs against the same pinned baseline, checks exact and semantic overlap, adjudicates each result independently and processes integration serially: accept/reconcile one child, re-read live `main`, re-evaluate the remaining child, and proceed only if its scope and acceptance remain valid. A conflict, stale base, missing dependency, absent receipt or authorization uncertainty stops the sequence. Never force-merge.

**Observable pass condition.** Two separately identified child packets start from the same recorded baseline; their normalized scopes and actual changed paths are disjoint; each result is attributable to its own task/HEAD; the integrator revalidates `main` between integrations; and the accepted content is fetched back from the exact resulting `main` SHA without altering canonical gates. If protected-branch rules or merge authority cannot be verified when required, the pilot stops before merge and must not be reported as fully passed. This is a future acceptance oracle, not a claim that the pilot has been executed.

The first useful proof is not “several agents answered.” It is: two independent bounded child packets start from recorded baselines, work on non-overlapping scopes, return attributable evidence, and are integrated sequentially without overwriting one another or changing canonical gates. A later proof of runtime automation is a separate milestone.

## 10. Evidence boundary

This document is a static design candidate derived from live repository source at `main@1430ad5062298a8dd5719ccb2882e2ce4877b283` and the user’s stated objective in the current conversation. No product code, tests, build, runtime, MCP transport, protected read, PR merge, or canonical route update was performed for this candidate.
