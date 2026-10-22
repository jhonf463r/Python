# IABV→Codex — Goal-Locked Routing and Anti-Drift Protocol v1.0

- **Date:** 2026-10-20 (America/Bogota)
- **Status:** active routing/method amendment; documentary only
- **Canonical current-state authority:** `CURRENT-STATE.md`, top routing snapshot
- **Primary objective:** deliver a real, governed IABV→Codex→IABV bridge, not an endless sequence of contract reviews.
- **Current route (updated 2026-10-21):** candidate test execution has occurred: 76 collected, 74 passed, 2 failed; overall module `FAIL`. The local executor inspection then read no source because the normal MCP reader returned `operational_block_active`. No new Codex test or source-inspection prompt is actionable until a supported governance-owned scoped read route is identified. Candidate remains unmerged, launch remains blocked, and transport is `NOT_RUN`.
- **Latest handoff incident (2026-10-21; OWNER_REPORTED):** IABV reported resource-pressure deferral, then `wrong_thread` rejection, then a default-browser fallback that it could not read/verify via DOM/CDP. Treat browser fallback as out-of-scope; do not log in, relay browser responses, use an alternate route or launch transport. See `CHAT-ARCH-2026-10-21-codex-handoff-resource-pressure-wrong-thread-browser-fallback.md`. Sole next step remains governance-owned scoped-read route.
- **Latest RAM-scope failure (2026-10-21; OWNER_REPORTED):** the focused Ollama/RAM prompt returned a broad auto-scan rather than measurements; output again claims GPU correction and token mapping without a measured postcondition. Do not repeat general scans. See `CHAT-ARCH-2026-10-21-ollama-ram-request-not-honored-repeat-autoscan.md`. Owner priority: diagnose resource pressure with existing bounded read-only evidence, then perform the independent static Codex audit.
- **Latest direct-Codex resource snapshot (OWNER_REPORTED, 2026-10-21 18:22):** system RAM 69.2% used, but observed `ollama.exe` itself was 18.4 MB working set; Opera and ChatGPT appeared as major visible consumers. Model residency and startup causality remain unresolved. Next resource step is one read-only GET to `/api/ps` only if Ollama is already listening, correlated to a contemporaneous process snapshot. No model load/reload or process start. See `CHAT-ARCH-2026-10-21-ollama-readonly-process-snapshot-and-next-query.md`.
> **Ollama startup causality clarification (2026-10-21):** the direct Codex/PowerShell snapshot sampled Windows processes but did not launch IABV or reproduce its startup. It cannot tell why opening IABV activates Ollama or whether local inference is required. One snapshot showed 69.2% RAM use and ollama.exe at 18.4 MB working set / 60.7 MB private; Opera and ChatGPT were among the larger consumers. These are owner-reported snapshot facts, not causality evidence. Next source task, only through the legitimate governance-owned scoped-read route: trace local IABV startup -> Ollama launch/connect -> model/provider selection and whether the path is eager, lazy, warm-up, health-check or fallback. Do not launch IABV for reproduction, use another reader, reload a model or change configuration. See [startup-causality record](./CHAT-ARCH-2026-10-21-ollama-startup-causality-not-tested-by-codex-snapshot.md).
- **Supplementary human–IABV interaction audit (2026-10-21):** documentary adjudication finds request interpretation and scope discipline `FAIL`, causal-learning evidence `FAIL`, progress observability `PARTIAL`, and multi-IA readiness `NOT_READY`; the declared remote branch deletion and runtime mutations are not independently verified. See `CHAT-ARCH-2026-10-21-human-iabv-interaction-audit.md`. This finding does not supersede the sole next step in `CURRENT-STATE.md`.
- **Current owner constraints:** `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = AUTHORIZED_FOR_NARROW_SCOPE_ONLY_ON_ISOLATED_REMOTE_BRANCH`; `BRIDGE_NOT_READY`; owner decision C keeps Codex launch blocked.
- **Owner gate decision:** `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE`. Acts requiring a second independent human remain `BLOCKED_BY_CURRENT_CONSTRAINTS`. Do not ask this again unless the owner explicitly changes the decision.

## 2026-10-22 ADHD-aware focus and space-time project coordination (documented method; runtime not proven)

Detailed owner-directed protocol: [ADHD-aware project coordination and space-time focus](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md).

The Owner explicitly reports ADHD and asks for structured project coordination because useful new ideas arise rapidly and can divert attention from the primary objective. Treat this as an owner-directed interaction-design requirement, not as a limitation to infer beyond what the Owner stated. Capture new ideas in a persistent inbox/parking lot; do not switch the active task automatically. Maintain one primary outcome, one active task, one acceptance criterion and one next action. Interrupt only for immediate safety or a dependency that invalidates the active work; otherwise triage the idea as direct dependency, later, duplicate/resolved, or out of scope. Give a brief progress dashboard and distinguish queued/running/blocked/completed-unverified/verified using evidence, not narration.

The existing DEVELOPMENT CONTROL TOWER and goal-lock/anti-drift protocol are the foundation; this addendum does not create a competing route or claim the runtime coordinator is implemented. The sole active task remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`; preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `LOCAL_SOURCE_READ=NOT_RUN`, `REAL_TRANSPORT=NOT_RUN`, `LOCAL_WORKTREE=UNTOUCHED`. The latest IABV response repeated a broad scan instead of the stop-and-report-only request; containment and all claimed mutations remain unverified. Do not repeat the scan, pull/clean/reset, alter GPU/models/credentials, or attempt improvised rollback.

---

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

The previously authorized implementation exception covered only the `OperationalBlockRecord` target-scope applicability fix and its focused tests on isolated branch `fix/iabv-operational-block-target-scope-20261021`, HEAD `433d993df71e02c041b562e80110d7b46fb11bb7`. That candidate test module has since been run: 76 collected, 74 passed, 2 failed due to `_FakeWorldModelService.scan_stats`; do not label the full module passing or change the candidate for that unrelated fixture without separate authorization. A later static inspection attempt was blocked before reading local source. The next task is to identify/use a supported governance-owned scoped read route for the already-authorized executor-source and whitelisted non-secret policy inspection. This does not authorize local checkout changes, candidate merge/adoption, clearing the active block, launching Codex CLI/App Server, local tests/build/runtime, authentication, installs/updates, spend or real transport. Owner decision C remains binding for Codex launch. Preserve `GOVERNANCE=KEEP_BLOCKED` and `BRIDGE=BRIDGE_NOT_READY`.

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

- `PRIMARY_OUTCOME = GOVERNED_IABV_CODEX_BRIDGE`; local executor/receipt inspection remains the earliest unproven edge.
- `GOVERNANCE = KEEP_BLOCKED`; `BRIDGE = BRIDGE_NOT_READY`; `REAL_TRANSPORT = NOT_RUN`.
- Owner decision C remains `KEEP_CODEX_LAUNCH_BLOCKED_WHILE_STATIC_DESIGN_CONTINUES`; do not start Codex CLI/App Server, IABV/MCP or real transport.
- `SECOND_INDEPENDENT_HUMAN = UNAVAILABLE`; do not ask again.
- Candidate branch `fix/iabv-operational-block-target-scope-20261021`, base `6a231f7f8edd80753444b05c06729c4c4b184673`, HEAD `433d993df71e02c041b562e80110d7b46fb11bb7`, remains unchanged and unmerged.
- Candidate test run (`OWNER_REPORTED`): 76 collected, 74 passed, 2 failed, 0 skipped/errors, exit 1. Six scope-fix tests were collected and are not among the two reported failures. Both failures concern `_FakeWorldModelService.scan_stats`; source comparison indicates a pre-existing fixture mismatch, but no base-suite rerun was performed.
- Latest local executor route result (`OWNER_REPORTED`): Codex read zero local source/config files because the normal MCP reader returned `governance_blocked=true`, `reason=operational_block_active`. This is a blocked precondition, not evidence that local symbols are absent.
- `LOCAL_EXECUTOR_IDENTITY = UNRESOLVED`; `LOCAL_EFFECTIVE_CONFIGURATION = UNRESOLVED`; `RSK01A5_SERVER_REVISION_AND_ROOT = UNRESOLVED`; Route A hard conditions remain unverified.
- **Sole next step:** identify and use a supported governance-owned scoped read authorization or already-supported read-only route for the static inspection already authorized by the Owner. Exact mechanism is `UNRESOLVED`. Do not rerun the denied reader, bypass it with another reader, clear the block manually, rerun the test prompt, recreate clones or modify the candidate.
- Continuity record: [CHAT-ARCH-2026-10-21-local-executor-read-denied-and-scopefix-test-result.md](./CHAT-ARCH-2026-10-21-local-executor-read-denied-and-scopefix-test-result.md).
- Preserve `LOCAL_WORKTREE=UNTOUCHED`, `CANDIDATE_MERGED=NO`, `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`.

## 7. Anti-drift invariants

- The user's primary bridge objective outranks adjacent documentation tasks.
- An unanswered blocker must be handled; an answered blocker must not be re-asked.
- A documentary pass is never an implementation receipt.
- A source-level candidate is never a connected or tested bridge.
- A gate table is not progress unless it changes a decision or selects a materially better next technical step.
- No repeated review unless new bytes, source, contradiction, or scope justify it.
- Never violate `KEEP_BLOCKED` to appear helpful; never use `KEEP_BLOCKED` as an excuse to abandon all permitted technical design work.
- A local read denied with `governance_blocked=true` and zero source reads must change the route. Once refusal metadata identifies a concrete source seam, make only the authorized bounded correction on an isolated candidate. If full checkout fails under `data/`, never repeat it. If a `--no-checkout` sparse clone produces an empty index and massive `D ` status even after cone reapply, never repeat sparse repairs against that clone: leave it untouched and use a new short-path `git clone --sparse --filter=blob:none` from the start, selecting only source/tests afterward. On a valid sparse-first clone, do not recreate it. Do not misdiagnose missing top-level `fastmcp` if the code imports `FastMCP` from `mcp.server.fastmcp`; test the exact nested import the source uses. Capture status output internally without printing excluded path names; never clean or reset to force a clean result. Leave failed partial directories untouched. Do not repeat the reader, infer local/runtime identity from public `main`, merge an untested candidate, or bypass the gate.
- Report uncertainty honestly and preserve exact evidence provenance.

## 8. Acceptance test for this protocol

A future continuation fails this protocol if it (a) asks again whether the second human is available, (b) sends another generic gate triage after the bounded triage is complete, (c) reopens N-88 without new contradictory evidence, (d) routes a task to Codex without implementation/launch authorization, (e) leaves the top-level routing snapshot pointing to an older active task, or (f) reports progress without identifying a bridge edge advanced by source-backed evidence.

**Authoritative current actor routing remains the top snapshot in `CURRENT-STATE.md`; this protocol defines the method, not new execution authority.**
