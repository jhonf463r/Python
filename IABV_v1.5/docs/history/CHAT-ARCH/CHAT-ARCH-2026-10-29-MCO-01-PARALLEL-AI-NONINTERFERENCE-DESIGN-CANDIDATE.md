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
- [PlatformPendingQueue source](../../src/iabv_v15/services/evolution/platform_pending_queue.py)
- [Task model source](../../src/iabv_v15/domain/models.py)
- [Task/result repository source](../../src/iabv_v15/infra/persistence/tool_record_repository.py)

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

1. Stable `CHILD_TASK_ID` and `PARENT_TASK_ID`.
2. Exact base `main` SHA and, if relevant, candidate branch/HEAD SHA.
3. One objective, one expected outcome and one acceptance criterion.
4. Named actor or accountable agent, required capability and reason for selection.
5. Allowed paths (or a precise, non-overlapping source scope) and forbidden paths.
6. Dependencies, prior evidence to reuse, and known closed edges that must not be repeated.
7. Action class: documentation, source-read-only, implementation, test, build or runtime.
8. Exact permissions and prohibited side effects.
9. Expected artifacts and provenance, verification method, and explicit stop condition.
10. Return format: observed action, source/commit, artifact, what is proved, what is not proved, blocker, and next open edge.

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
3. Path ownership and serialized integration prevent silent shared-file contention.
4. A bounded conflict matrix covers at least: disjoint paths, overlapping paths, stale base, missing dependency, canceled child, duplicate submission, unavailable actor, blocked authorization and integration conflict.
5. The design reuses current records and GitHub objects where adequate and names no new runtime organ without proof.
6. A first low-risk pilot can be run as isolated PRs without touching the G1/G2/G3 lane or changing protected gates.
7. Runtime dispatch, ownership leases and automated concurrency are marked unproven until separate evidence exists.

## 9. Recommended next action

Review this candidate against live `main` and the owner’s active direction. If accepted, adopt the child-packet policy in the existing owning coordination protocol—not as a second protocol or router—using a bounded documentary update and fetch-back verification. Then, separately, authorize a low-risk isolated pilot. Do not proceed directly to a runtime scheduler or external-AI dispatcher.

The first useful proof is not “several agents answered.” It is: two independent bounded child packets start from recorded baselines, work on non-overlapping scopes, return attributable evidence, and are integrated sequentially without overwriting one another or changing canonical gates. A later proof of runtime automation is a separate milestone.

## 10. Evidence boundary

This document is a static design candidate derived from live repository source at `main@1430ad5062298a8dd5719ccb2882e2ce4877b283` and the user’s stated objective in the current conversation. No product code, tests, build, runtime, MCP transport, protected read, PR merge, or canonical route update was performed for this candidate.
