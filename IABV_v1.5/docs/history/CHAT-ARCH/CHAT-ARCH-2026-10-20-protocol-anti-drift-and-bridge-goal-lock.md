# IABV→Codex — Goal-Locked Routing and Anti-Drift Protocol v1.0

- **Date:** 2026-10-20 (America/Bogota)
- **Status:** active routing/method amendment; documentary only
- **Canonical current-state authority:** `CURRENT-STATE.md`, top routing snapshot
- **Primary objective:** deliver a real, governed IABV→Codex→IABV bridge, not an endless sequence of contract reviews.
- **Current mode:** static-only; implementation and Codex launch remain unauthorized.
- **Current owner constraints:** `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE_NOT_READY`; owner decision C remains binding.
- **Owner gate decision:** `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE`. Acts requiring a second independent human remain `BLOCKED_BY_CURRENT_CONSTRAINTS`. Do not ask this again unless the owner explicitly changes the decision.

## 1. Why this protocol changed

The recent continuation repeatedly allowed a nearby prerequisite or a completed review to replace the primary goal. After N-88 passed a bounded documentary review, the workflow moved into a broad gate triage and then asked the owner to decide the same quorum question. These actions preserved safety language but did not progress the bridge's technical path.

A second source of drift is conflicting dated routing text. Several repository front doors began at an older Entry 280 / M0B route, while this conversation had already reached v11 and the bridge-goal discussion. A new actor could obey a historically valid but obsolete “next actor” instruction.

This amendment prevents those failures without relaxing any authorization or safety constraint.

## 2. Goal lock: do not substitute a prerequisite for the objective

The desired bridge outcome remains this end-to-end chain:

`IABV task and intent
→ typed authorization and correlation
→ isolated Codex candidate execution (only after separate authorization)
→ terminal status plus independently verifiable baseline/diff/changed-path receipt
→ correlation of task/thread/turn/attempt/result
→ identified IABV verifier/consumer
→ separate owner acceptance/rejection/promotion decision`

Every task must state which link it advances. A governance or evidence blocker is a constraint on one or more links, not automatically a replacement objective. Do not turn the entire continuation into a review of all blockers merely because one gate is unresolved.

A blocked link must be recorded at the narrowest applicable scope:
- A missing second human blocks acts requiring independent human authority.
- It does not invalidate the already-completed N-88 documentary review.
- It does not authorize execution or implementation.
- It must not repeatedly become the next prompt after the owner has answered.
- Other static technical analysis may continue only when it directly improves the bridge specification or identifies the exact source-to-source seam, within the current permissions.

## 3. Separate four dimensions on every turn

Never collapse these into one status:

1. **Goal:** the outcome the owner is trying to achieve.
2. **Authorization:** actions allowed now.
3. **Blocker:** the condition preventing one or more transitions.
4. **Progress:** the concrete artifact or verified source edge completed in this turn.

A documentary `PASS` changes only the verdict for its stated documentary scope. It does not imply implementation, runtime validity, security, consumer integration, or readiness.

Use these evidence labels without substitution: `PROVEN_BY_SOURCE`, `OWNER_REPORTED`, `PROPOSED`, `UNPROVEN`, `UNRESOLVED`, `NOT_FOUND_IN_BOUNDED_SCOPE`, `NOT_RUN`, `NOT_AUTHORIZED`, `BLOCKED_BY_CURRENT_CONSTRAINTS`, `CONFIRMED_LOCAL`, `HEAD_SOURCE`, and `WORKTREE_SOURCE`. Public source is not evidence of private/dirty local state. A design name is not proof that a component exists.

## 4. Mode gate: ambition never silently elevates authority

At the start of each task, choose exactly one operating mode:
- `STATIC_SOURCE_MAPPING`: read authorized public source and documents; trace actual call sites and identify missing edges.
- `DOCUMENTARY_DESIGN`: author a bounded contract/plan for a specific known gap.
- `IMPLEMENTATION`: source modifications, which require separate explicit authorization.
- `EXECUTION_OR_VERIFICATION`: tests/build/runtime/preflight/launch, which require their own separate authorization and preconditions.

Current mode is `STATIC_SOURCE_MAPPING` / `DOCUMENTARY_DESIGN` only. Owner decision C is still binding. Do not launch Codex, execute code, run tests/builds/runtime/preflight/canaries, inspect the local checkout/M0A/`data/`/SQLite/secrets, install/update, authenticate, query quota, spend, or write product code. This protocol does not grant those permissions.

If the owner says “build the bridge”, treat that as confirmation of the primary objective, not as implicit approval to cross an existing execution/implementation gate. Do not pretend an implementation task can be performed under static-only authority. Instead choose the highest-value, source-backed step that genuinely narrows the bridge gap.

## 5. The task-selection algorithm

Run this loop in order:

### Step 0 — Reconcile current authority

Fetch the current repository `main` SHA, then read the current route in this order:
`AGENTS.md → CHAT-ARCH/README.md → CHAT-ARCH/CURRENT-STATE.md → relevant CONTEXT-INDEX → MEMORY-OPERATING-PROTOCOL → exact task sources`.

Only the top route snapshot in `CURRENT-STATE.md` selects the current actor. Historical “next actor” text is non-routable unless the current snapshot explicitly reactivates it. If front doors disagree, fix the routing mismatch before assigning work; do not choose whichever stale note is easiest to follow.

### Step 1 — Freeze the outcome and record progress

Write one line for `PRIMARY_OUTCOME`, one for `CURRENT_AUTHORIZED_MODE`, one for `CURRENT_FRONTIER`, and one for `NEXT_DELIVERABLE`. Carry forward the most recent adjudicated status. Do not repeat an accepted review or ask an answered owner question.

### Step 2 — Locate the earliest missing technical edge

Map the end-to-end bridge chain and identify the earliest unproven transition that can be investigated within the current mode. Separate “component named”, “component source exists”, “actual caller/callee linked”, “receipt/consumer contract linked”, and “behavior verified”. Never promote one to another.

### Step 3 — Rank candidate tasks by goal contribution

Choose the single task with the greatest direct contribution to a missing bridge edge that:
- is within current authorization;
- can use sources already available or can retrieve them through an authorized AI/tool route;
- produces concrete source locations, call edges, schemas/IDs or an actionable minimal design;
- reduces uncertainty relevant to the next engineering step;
- does not repeat a completed search/review;
- does not create a new global matrix when a bounded source map would advance the technical path.

Do not optimize for number of documents, number of gates listed, prompt length, or another “PASS”. Optimize for verified reduction in distance to the bridge's end-to-end chain.

### Step 4 — Bound the investigation and stop on evidence exhaustion

Use a pinned commit and a bounded path/query list. Trace direct callers/callees and the relevant output/receipt boundary only. Record exact path, blob SHA, line or symbol anchors, claim and provenance.

If a source is absent or does not establish a link after the authorized bounded search, record `NOT_FOUND_IN_BOUNDED_SCOPE` or `UNRESOLVED`. Do not repeat the same search with synonyms, widen to unrelated identity/auth/gate subsystems, or ask the owner to copy/paste information the available tools can retrieve. Expand scope only for a concrete new source reference, a contradiction, or a new explicit authorization.

### Step 5 — Treat blockers as constraints, not as the new objective

Record each blocker once with: affected transition, required evidence/authority, status, and whether an independently useful static task remains. If the blocker cannot be cleared under current restrictions, do not re-triage every gate. Continue the best allowed task that advances a separate bridge edge, or say plainly that no such task remains.

For the current quorum decision, `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE` is settled. Do not ask it again. Keep the affected acts blocked. Do not infer an exception or turn the known answer into an endless owner-gate prompt.

### Step 6 — Produce the smallest useful deliverable

Prefer one source-backed bridge path map, one adapter contract, or one exact missing seam over another whole-contract rewrite. No new version (v12 etc.) or finding ID (N-89 etc.) merely to memorialize a pass or repeat known facts. Preserve historical artifacts immutably.

### Step 7 — Verify what actually changed

For public-repository documentation changes, verify the intended parent/head, update only bounded documentation paths, fetch back the exact committed content, and report commit/blob identities. Never describe a local or Library artifact as committed to GitHub until verified there. Keep public `HEAD_SOURCE`, local `WORKTREE_SOURCE`, and `OWNER_REPORTED` claims separate.

### Step 8 — Route exactly one next task

Every completion report must state:
- primary goal and current stage;
- what concrete bridge edge moved and what did not;
- next actor and exact destination IA;
- one exact prompt/task;
- exact attachments/source commit;
- expected output and acceptance criterion;
- stop condition;
- governing prohibitions and current mode.

Do not conclude with an ambiguous “what do you want to do?” where the next authorized task can be selected objectively. Ask the owner only for a decision that genuinely cannot be inferred or delegated.

## 6. Current routing snapshot — 2026-10-21 (latest adjudication)

- `PRIMARY_OUTCOME = GOVERNED_IABV_CODEX_BRIDGE`; `CURRENT_AUTHORIZED_MODE = STATIC_SOURCE_MAPPING / DOCUMENTARY_DESIGN`.
- `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE = BRIDGE_NOT_READY`; `REAL_TRANSPORT = NOT_RUN`.
- `DECISION_C = KEEP_CODEX_LAUNCH_BLOCKED_WHILE_STATIC_DESIGN_CONTINUES`.
- `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE` (`OWNER_REPORTED`; do not ask again).
- `IABV_CODEX_MINIMAL_BRIDGE_PATH_MAP = RECEIVED_AND_ADJUDICATED_AS_SUPPLIED_WORK_ARTIFACT`, not a pending Claude/Sonnet deliverable and not a GitHub-verified runtime receipt.
- `IABV_CODEX_CANDIDATE_EXECUTOR_RECEIPT_MINIMAL_SLICE = NOT_FOUND_IN_BOUNDED_SCOPE`, not global absence. The missing edge is `CodexTaskSpec → development executor → CodexRunResult → isolated/reversible candidate → baseline/diff-verifiable receipt → identified consumer`.
- Local executor identity remains `UNRESOLVED`; the fallback `results[0]` / `_last_adaptive_payload` correlation issue is separate and not a reason to repeat its general audit.
- Tool/model provenance is maintained in the dated matrix at the top of `CURRENT-STATE.md`. GPT-6 and the successful GitHub reads are specific to this session/turn; supplied harness and owner statements remain `OWNER_REPORTED`.
- Upstream Codex rust-v0.120.0 source comparison is complete for this bounded decision (tag object 84b1753e16766434a86ec29ab7a23984fd0f61fe; target commit 65319eb1400cbd2890c43d572263dabd25f18ba9). The coordinator recommendation is ROUTE_A_CONDITIONAL, pending Owner adjudication against NO_GO_KEEP_BLOCKED. The key pinned Codex-source blobs and conditions are recorded in the 2026-10-21 decision delta at the top of CURRENT-STATE.md. Local configuration/runtime and the IABV executor/consumer remain unresolved.
- **Owner adjudication (2026-10-21):** `ROUTE_A_CONDITIONAL` accepted as the conditional first-cut design direction; Route B deferred for the first cut. This does not authorize implementation or launch. The Owner has also authorized one static, read-only inspection of local executor source/registration and whitelisted non-secret effective Codex policy fields.
- **Owner-supplied local-read observation (2026-10-21):** Codex reports zero source files read; its normal reader returned `governance_blocked=true`, `reason=operational_block_active`. This is `ACTION_UNEXECUTABLE_NO_EVIDENCE`, not source absence. Owner-level authorization to read does not release an active IABV operational block.
- **Sole gated next step:** `CODEX_EXISTING_REFUSAL_METADATA_AND_TOOL_TARGET_PROVENANCE`, in the same Codex UI, limited to the already-returned refusal/call record. Extract only already-visible structured `blocks[]` / `permission_gates[]`, identifiers, scope/owner/expiry, plus existing MCP server/tool identity and documented workspace-root mapping. Do not invoke any tool, repeat the reader, request `world_model_snapshot`, inspect source/config/filesystem, or bypass the gate. If metadata is not retained, return `REFUSAL_METADATA_NOT_RETAINED` and stop; local facts remain `UNRESOLVED`.
- No implementation, Codex launch, tests/builds/runtime, transport, authentication, quota queries, installation/update, spend, or promotion is authorized. Preserve `KEEP_BLOCKED`.
## 7. Anti-drift invariants

- The user's primary bridge objective outranks adjacent documentation tasks.
- An unanswered blocker must be handled; an answered blocker must not be re-asked.
- A documentary pass is never an implementation receipt.
- A source-level candidate is never a connected or tested bridge.
- A gate table is not progress unless it changes a decision or selects a materially better next technical step.
- No repeated review unless new bytes, source, contradiction, or scope justify it.
- Never violate `KEEP_BLOCKED` to appear helpful; never use `KEEP_BLOCKED` as an excuse to abandon all permitted technical design work.
- A local read denied with `governance_blocked=true` and zero source reads must change the route: classify `ACTION_UNEXECUTABLE_NO_EVIDENCE`, inspect only the refusal metadata/tool-target identity already returned, and never repeat the reader or use another tool/path. Owner conversational authorization is not the governance-owned release of an active operational block.
- Report uncertainty honestly and preserve exact evidence provenance.

## 8. Acceptance test for this protocol

A future continuation fails this protocol if it (a) asks again whether the second human is available, (b) sends another generic gate triage after the bounded triage is complete, (c) reopens N-88 without new contradictory evidence, (d) routes a task to Codex without implementation/launch authorization, (e) leaves the top-level routing snapshot pointing to an older active task, or (f) reports progress without identifying a bridge edge advanced by source-backed evidence.

**Authoritative current actor routing remains the top snapshot in `CURRENT-STATE.md`; this protocol defines the method, not new execution authority.**
