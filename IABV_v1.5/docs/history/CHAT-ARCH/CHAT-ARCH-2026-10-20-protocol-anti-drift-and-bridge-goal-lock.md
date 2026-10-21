# IABV→Codex — Goal-Locked Routing and Anti-Drift Protocol v1.0

- **Date:** 2026-10-20 (America/Bogota)
- **Status:** active routing/method amendment; documentary only
- **Canonical current-state authority:** `CURRENT-STATE.md`, top routing snapshot
- **Primary objective:** deliver a real, governed IABV→Codex→IABV bridge, not an endless sequence of contract reviews.
- **Current mode:** bounded implementation + regression-test authoring on isolated remote branch `fix/iabv-operational-block-target-scope-20261021` only. Tests are not run; local checkout adoption/merge and Codex launch remain unauthorized.
- **Current owner constraints:** `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = AUTHORIZED_FOR_NARROW_SCOPE_ONLY_ON_ISOLATED_REMOTE_BRANCH`; `BRIDGE_NOT_READY`; owner decision C keeps Codex launch blocked.
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

Current authorized mode is narrowly bounded implementation and regression-test authoring on isolated remote branch `fix/iabv-operational-block-target-scope-20261021` only, as explicitly authorized by the Owner on 2026-10-21. This exception covers only the `OperationalBlockRecord` target-scope applicability fix and its focused tests. Candidate HEAD is `433d993df71e02c041b562e80110d7b46fb11bb7`; tests are `NOT_RUN`. It does not authorize edits to the dirty local checkout, adopting/merging the remote candidate, clearing the live RAM block, launching Codex CLI/App Server, tests/builds/runtime on the local environment, preflight/canary, authentication, quota checks, installation/update, spend, or real transport. Owner decision C remains binding for Codex launch. Preserve `GOVERNANCE=KEEP_BLOCKED` and `BRIDGE=BRIDGE_NOT_READY`.

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
- **Owner-supplied local-read observation (2026-10-21):** Codex read zero source files; the existing result from `list_repo_directory` on server `iabv_v15_rsk01a5` reported active block `72b8697f-7291-473b-a43c-eb7a989a059d`, `ram_critical`, `target_scope=heavy_local_model`, empty `assistant_kind`.
- **Source-backed adjudication:** public `server.py` blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`, lines 448–450, applies active records based on `assistant_kind` only, while public `world_model_service.py` blob `ba0b5f5d6233330b549e09863975c77c0db735d6`, around line 1311, emits resource-risk records with `target_scope='heavy_local_model'` and empty `assistant_kind`. The public-main scope mismatch is proven; the exact RSK runtime source/root remain unverified.
- **Owner authorization + candidate:** the Owner authorized the narrow scope-filter correction and regression-test additions. Isolated branch `fix/iabv-operational-block-target-scope-20261021` is based on `6a231f7f8edd80753444b05c06729c4c4b184673`, with source commit `5032fe892e963c931aac93cda66ebb1f676c850e` and test commit/head `433d993df71e02c041b562e80110d7b46fb11bb7`. Only `server.py` and `test_mcp_server.py` changed on that branch; six regression tests were added. Candidate contents were fetched back.
- **Attempts 1–4:** full checkout failed under `IABV_v1.5/data/`; the earlier `--no-checkout` sparse clone has empty index output while status lists 17,757 `D ` entries. Both old copies are off-limits and must not be cleaned or inspected.
- **Sparse-first clone:** Owner reports `C:\\_iabv_sf3_20261021` is clean at exact candidate HEAD `433d993df71e02c041b562e80110d7b46fb11bb7`, with cone mode selecting only `IABV_v1.5/src` and `IABV_v1.5/tests`, no `data/`, and exactly the two intended changed files.
- **Preflight correction (Owner-supplied):** the test preflight used `import pytest, mcp, fastmcp` and stopped on `No module named 'fastmcp'`. That check was incorrect for this source: `server.py` imports `FastMCP` from `mcp.server.fastmcp`, while tests call `pytest.importorskip('mcp')`. This false gate is not evidence the relevant SDK module is missing. `IABV_v1.5/pyproject.toml` does not declare `mcp` among project dependencies; note this packaging reproducibility gap, but do not expand the currently authorized two-file fix without separate authorization.
- **Sole next step:** in the existing sparse-first clone, verify exact HEAD and clean status (count only), no `data/`, exact two-file diff, and run `C:\\Python314\\python.exe -c "import pytest; print('pytest', pytest.__version__); from mcp.server.fastmcp import FastMCP; print('MCP_FASTMCP_IMPORT=OK')"`. Do not attempt top-level `import fastmcp`. If the correct import succeeds, run only `IABV_v1.5/tests/test_mcp_server.py` from a separate short temporary cwd with existing dependencies and no package install; verify all six new tests are collected. If the nested import fails or another real dependency is absent, stop and report that exact failure.
- **Readiness boundary:** candidate remains unmerged and untested until actual pytest output is captured. Even passing unit tests validate only isolated source; live server revision/root and executor remain unresolved, `REAL_TRANSPORT=NOT_RUN`, and Owner decision C blocks launch. No local checkout access or bridge startup.
## 7. Anti-drift invariants

- The user's primary bridge objective outranks adjacent documentation tasks.
- An unanswered blocker must be handled; an answered blocker must not be re-asked.
- A documentary pass is never an implementation receipt.
- A source-level candidate is never a connected or tested bridge.
- A gate table is not progress unless it changes a decision or selects a materially better next technical step.
- No repeated review unless new bytes, source, contradiction, or scope justify it.
- Never violate `KEEP_BLOCKED` to appear helpful; never use `KEEP_BLOCKED` as an excuse to abandon all permitted technical design work.
- A local read denied with `governance_blocked=true` and zero source reads must change the route. Once refusal metadata identifies a concrete source seam, make only the authorized bounded correction on an isolated candidate. If full checkout fails under `data/`, never repeat it; for test validation prefer correcting the existing sparse clone to cone mode with only source/tests selected. Capture status output internally without printing excluded path names; never clean or reset to force a clean result. Leave failed partial directories untouched. Do not repeat the reader, infer local/runtime identity from public `main`, merge an untested candidate, or bypass the gate.
- Report uncertainty honestly and preserve exact evidence provenance.

## 8. Acceptance test for this protocol

A future continuation fails this protocol if it (a) asks again whether the second human is available, (b) sends another generic gate triage after the bounded triage is complete, (c) reopens N-88 without new contradictory evidence, (d) routes a task to Codex without implementation/launch authorization, (e) leaves the top-level routing snapshot pointing to an older active task, or (f) reports progress without identifying a bridge edge advanced by source-backed evidence.

**Authoritative current actor routing remains the top snapshot in `CURRENT-STATE.md`; this protocol defines the method, not new execution authority.**
