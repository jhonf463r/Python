# IABV v1.5 — Collective AI Coordination Audit Checkpoint

- Date: 2026-10-25 (America/Bogota)
- Status: **DOCUMENTARY CHECKPOINT / DRAFT; NOT CANONICAL UNTIL ADOPTED**
- Repository: `jhonf463r/Python`
- Inspected canonical baseline: `main@5965735167b50d12bc98543d132d70022fb73803`
- Canonical route at baseline: `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`, blob `e51fdc0e6a3d49a83a8619ea864d2cec1b8651b1`
- Purpose: preserve what the recent static review actually established about IABV's ability to coordinate multiple AIs/chats, what remains missing, what has not been tested, and the safe order for resuming without repeating closed investigations.
- Scope boundary: this checkpoint is supplementary. It **does not change or supersede** canonical `CURRENT-STATE.md`, authorize product-source edits/tests/runtime, close trust gates, or approve a commit/push/merge to `main`.

## 1. Executive verdict

**IABV has substantial architectural foundations for collective AI coordination, but end-to-end operation as one reliable organism is NOT YET DEMONSTRATED.**

The repository contains intent/context assembly, multiple model/tool selectors, a bounded parallel candidate comparison path, a portable-context/memory chain, session briefing support, audit/self-examination components and a Space-Time continuity protocol. Source existence and some source wiring are verified. They do not prove that every independent ChatGPT/Codex/Claude/Devin/local model session can be given the right current context, return a correlated result, be reconciled with other workers and influence the next task.

Use these status distinctions:
- `SOURCE_VERIFIED`: exact source/docs were fetched from the pinned baseline.
- `STATIC_RISK`: code structure allows a failure/misalignment; runtime impact not established.
- `HISTORICAL_RECEIPT`: prior audit recorded a result against its own named baseline; reuse it, but don't imply it proves today's runtime.
- `NOT_RUN`: the action was not executed in this audit.
- `NOT_PROVEN`: evidence is insufficient for the stronger claim.
- `OWNER_REPORTED`: supplied by the Owner/another session but not independently reproduced by this checkpoint.
- `PROPOSED`: design recommendation, not accepted implementation.

This review is source/doc inspection only. **No IABV runtime, browser session, external AI delivery, build, tests, protected read or cross-chat end-to-end exercise was performed here.** This is not a complete repository-wide audit.

## 2. Canonical route and immediate prerequisite — DO NOT SKIP

At the inspected live-main baseline, the sole canonical route says:

```text
ACTIVE_TASK=M1A_G1_RECONCILE_CANDIDATE_PRETASK_DIFF_PROVENANCE_20261025
ACTIVE_TASK_STATUS=CURRENT_TREE_DELTA_AND_PRESERVATION_PACKAGE_REQUIRED; NO_SOURCE_EDIT
NEXT_ACTION=PRODUCER_GENERATE_ONE_CURRENT_DIRECTORY_TO_DIRECTORY_DELTA_AND_PRESERVATION_PACKAGE
NEXT_ACTION_SEMANTICS=CURRENT_TREE_DELTA_ONLY; NOT_HISTORICAL_TASK_ATTRIBUTION
REPOSITORIES=INDEPENDENT_CLONES_CONFIRMED
INDEX_BLOBS=MATCH_REPORTED_FOR_SIX_TRACKED_PATHS
WORKTREE_CONTENTS=DIVERGENT_REPORTED; EIGHT_PATHS_LISTED
UNTRACKED_PATHS=2_REPORTED
DROPBOX_OR_SYNC=UNKNOWN
PATH_INVENTORY=RECONCILE_GITHUB_OWNER_MERGE_BOOTSTRAP_PY_MENTION
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PROTECTED_READS=FAIL_CLOSED
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
HANDOFF=PREPARED_NOT_SENT
```

The current route reports the independent-clone diagnosis from an Owner-supplied Windows Codex diagnostic; it is not an independent observation of both local worktrees by this ChatGPT review. No Dropbox root or filesystem alias was confirmed in the paths examined; sync causality remains `UNKNOWN`. The diagnostic mentions `github_owner_merge_bootstrap.py` as an additional `MM` path that is not in its eight-row table.

### Required next evidence action

The Producer/Owner-side local session must compare the two surviving working-directory trees using repository-relative paths and preserve staged, unstaged and untracked state separately. Reconcile the union of status paths, including the missing path mention. This can establish the **current directory-to-directory delta**; it cannot by itself prove historical task-only attribution without a contemporaneous pre-task receipt.

Do not repeat Dropbox/sync searches, broad source inventories or source tests to fill that provenance gap. Do not attribute the differences to Dropbox without evidence. Do not overwrite either clone or destroy/normalize staged, unstaged or untracked changes before capturing the preservation package.

This checkpoint records the coordination audit as supplementary knowledge; it does not change the active route above.

## 3. Review scope and artifacts actually reused

### Canonical route / governance
- [`CURRENT-STATE.md`](./CURRENT-STATE.md), live main blob `e51fdc0e6a3d49a83a8619ea864d2cec1b8651b1`.
- [`AGENTS.md`](../../AGENTS.md), live main blob `50d5843f9d9eb1b81f350a43adbf4881435a9ad3`.
- [`SYMBIOSIS-MAP.md`](./SYMBIOSIS-MAP.md), live main blob `64ea4d572a3d823f5e9fbaf663b8096979864e43`.

### Prior static continuity work (reuse; do not restart from zero)
- [`CHAT-ARCH-2026-10-24-CONTINUITY-ALGORITHMS-STATIC-AUDIT.md](./CHAT-ARCH-2026-10-24-CONTINUITY-ALGORITHMS-STATIC-AUDIT.md), blob `05f63f43349ebc7a942fa28e7f9e710c67086ab9`.
- [`CHAT-ARCH-2026-10-24-MENTE-ESPACIO-TIEMPO-CONTINUITY-AUDIT-DELTA.md](./CHAT-ARCH-2026-10-24-MENTE-ESPACIO-TIEMPO-CONTINUITY-AUDIT-DELTA.md), blob `4d22cca12a5256a77c2566b6a0d988099fcad4ac`.
- [`CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md](./CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md).
- Existing RQ21.40–RQ21.44 and capability-identity cross-caller receipts referenced by `ARCHIVE-REGISTRY.md`. Reopen only the precise artifact needed to adjudicate a new source change; don't replay the entire historical investigation.

### Current source paths fetched from live `main`
- `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`, blob `41f6f7b6157226a1c6004591ddff4e36ff6f6da5`.
- `src/iabv_v15/services/tools/tool_teach_service.py`, blob `7f0412627c98074b1e3df0d0f6e76ab5998e3505`.
- `src/iabv_v15/services/tools/interaction_mode_selector.py`, blob `ac3b2d62e4a30bc1d87626ce03a57fd9f01a78af`.
- `src/iabv_v15/services/tools/tool_registry.py`, blob `17a0f7cc82dfb6722d4f2d7b231ac61551eb7ac2`.
- `src/iabv_v15/services/evolution/session_start_briefing_service.py`, blob `b6b292d6b8739d833a74461c7fb96a424f53dd67`.
- `src/iabv_v15/infra/mcp/server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`.
- `src/iabv_v15/domain/models.py), blob `a9033d21052c519e09f482097599c704a62ea916` (the fetched range contained `GoalContext` and `DecisionContext`; not a full-model review).

Only the listed paths/ranges and linked audit receipts were inspected in this checkpoint. No claim of whole-repository completeness is made.

## 4. Findings — source verified or previously evidenced

### F-01 — Intent/context/orchestration organs exist, but their existence is not proof of unified conversational awareness
**Status:** `SOURCE_VERIFIED_PARTIAL`

The existing orchestrator classifies the request with `IntentUnderstandingService`, builds a perception snapshot through `TaskContextAssembler`, uses routing and capability readiness components, and records session/decision metadata. The Space-Time protocols define cross-chat continuity, route authority, prior-art reuse and evidence discipline.

**Remaining question:** does every new consultation actually get classified as active-task execution, meta-coordination consultation, related side question or unrelated objective, and does that classification preserve the active route? The newly proposed model in PR #522 is a **draft**, not canonical code behavior. Do not claim the intent-aware coordination proposal has already been integrated or runtime validated.

### F-02 — Capability/readiness identity does not reach the concrete tool picker as a typed mandatory requirement
**Status:** `SOURCE_VERIFIED_GAP` for the inspected normal path; repo-wide absence not claimed.

In `ToolTeachService.build_task_for_session(session)`, the reconstructed `InferenceRequest` takes `session.user_goal`, prompt, role, goal parameters and site hint. Its metadata is only `{'adaptive_session_id': session.session_id}`. The function then calls `build_task_from_request(request)` and adds session/run/pack/site identity. It does not explicitly pass `session.capability_readiness` or `session.context.capability_snapshot` as a first-class required-capability contract into that request/task path.

The inspected `ToolRegistry.pick_card_for_task()` selects by an already specified `tool_id`, then preferred assistant family, then lexical token overlap, and ultimately the first registered card. `refresh_card()` recalculates availability, but the picker shown in source does not take a typed set of required capability IDs and use it as a hard eligibility filter.

Existing `ToolTeachService.build_task_from_request()` and synaptic-selection paths choose a tool before final task construction and can have different effective precedence. Capability descriptors and readiness evidence already exist elsewhere; the gap is their operational join to realization selection, not a request to invent another readiness service.

**Consequence:** lexical/preferred/explicit fallback can select a card without proving that it satisfies the task's required capability contract. This is a source-level contract gap; runtime impact and all bypass paths still need bounded call-site verification.

**Minimum repair candidate after route/provenance prerequisites:** freeze the task-demand contract (required capability IDs + operation/success predicate + provenance/status), carry it through all normal construction paths, and apply hard eligibility *before* preferences/scores/fallback. If no card is eligible, defer/block with explicit evidence instead of choosing the first card. Reuse existing `CapabilityReadiness` and capability-descriptor work; no parallel capability service.

### F-03 — Tool/model selection is spread across several selectors with partially different authority
**Status:** `SOURCE_VERIFIED_PARTIAL`

Source classes and call sites include `LocalRoleRouter`, `AdaptiveModelSelector`, `SynapticRouter`, `InteractionModeSelector`, `ToolTeachService` and `ToolRegistry`. In `build_task_from_request()`, the synaptic decision can be treated as authoritative when there is no explicit `goal_parameters.tool_id`; the selected card can then be used directly while the mode selector is invoked for metadata. Other paths apply `_enforce_explicit_external_selection()`. These rules are not one obvious universal precedence contract.

**Minimum repair candidate:** document and test a single precedence table shared by operative callers: hard capability eligibility and governance first; actual availability/health and resource/quota limits next; then explicit user constraints and policy-permitted preferences; then learned ranking among eligible candidates; finally safe defer/block. Record why a candidate was chosen and why others were ineligible. Do not collapse the existing selectors into a new duplicate router until caller-level evidence proves that consolidation is necessary.

### F-04 — A bounded parallel comparison/chained-consultation path exists; a general multi-worker project scheduler is not demonstrated
**Status:** `SOURCE_VERIFIED_BOUNDED_PATH`; `GENERAL_MULTI_WORKER_EXECUTION=NOT_PROVEN`.

The inspected `AdaptiveTaskOrchestrator._handle_request_body` ranks SynapticRouter candidates, can invoke `_parallel_ia_comparison` when at least two candidates exist and policy/resource gates allow it, and stores comparison results in session/decision metadata. The comparison implementation can synthesize returned results and, under its own conditions, initiate a chained consultation. Resource pressure can suppress the comparison.

This is a meaningful multi-IA path, but it is not evidence of arbitrary task decomposition and execution across a dependency graph. The reviewed path does not establish a complete general work-DAG contract with durable subtask IDs, worker isolation/locks, bounded concurrency and quota accounting, cancellation/retry recovery, correlation of every return, independent merge policy and end-to-end verification.

**Next evidence needed:** inspect the existing coordinator/worker abstractions and actual callers only after the current route's preservation prerequisite is complete. Determine whether current facilities already cover each missing scheduler property before proposing another component.

### F-05 — Portable context can deliberately return a richer but older package without a clear freshness verdict
**Status:** `SOURCE_VERIFIED_STATIC_RISK`.

In `infra/mcp/server.py: portable_context_get(refresh=False)`, the code raises the effective maximum age to at least 86,400 seconds and prefers the persisted rich package when a rebuild without live task context may produce empty sections. This preserves useful information, but the response path does not establish a clear `age_seconds`, `stale`, `degraded` and current-objective-binding verdict at this consumer boundary.

**Consequence:** old context can be returned intentionally; that is not proof the active local package is stale. The correction is not to discard rich context and create an empty package. Preserve rich content while surfacing source package ID/timestamp, age, objective/session binding and freshness/degradation state.

### F-06 — Initial perception is assembled before session-goal context is attached
**Status:** `SOURCE_VERIFIED_STATIC_RISK`; runtime defect not established.

In `AdaptiveTaskOrchestrator._handle_request_body`, the initial perception/context snapshot is built before `goal_engine.attach_session_goal_context(...)`; the resulting goal context is patched into the perception objects afterward. This ordering is a real source-level sequencing risk but does not prove a wrong live decision by itself.

**Next evidence needed:** reuse the existing terminal RQ13 receipts and trace which actual downstream consumers read the pre-attach snapshot versus the patched object. Do not restart broad RQ13 archaeology. Prefer binding the resolved objective before first perception only if compatible with the existing accepted contract.

### F-07 — Session briefing transport is conditional; a boolean send result is not proof the receiving AI used the context
**Status:** `SOURCE_VERIFIED_LIMITATION`.

`SessionStartBriefingService` builds a briefing from `PortableContextService`. Delivery to an existing session requires a named `session_id` and configured `message_sender`; new-session creation requires `session_creator`. The current source returns fields including session ID, a boolean outcome, error and character counts; it does not establish a universal transport to every ChatGPT, Codex, Claude, Devin and local-model conversation. A returned `True` is adapter-level status, not proof of remote receipt, reading, comprehension or use.

The GitHub handoff/front-door path is distinct from IABV runtime briefing transport. An assistant chat cannot be treated as connected merely because an artifact is present in GitHub or a prompt was prepared.

**Minimum repair candidate:** for each actually supported destination, correlate task ID, destination/session ID, portable package ID/digest and timestamp with adapter outcome, remote message/correlation ID if available, and a distinct acknowledgment/receipt state. Mark unsupported confirmation as `UNVERIFIED`; do not claim the recipient read or understood the package. Prove later reuse in a different task before calling it learning.

### F-08 — Browser/UI automation should be treated as a separate validated transport/capability, not assumed ready from a registered card
**Status:** `NOT_END_TO_END_VERIFIED_IN_THIS_CHECKPOINT`.

This checkpoint did not execute or fully audit browser control. Earlier records identify browser/CDP selection, wrong-tab risk, configuration consistency, capability validation and card validation as items requiring targeted re-verification. Do not treat a browser adapter/card as proof of foreground, background, DOM, CDP or multi-session control. After the canonical active-task prerequisite is complete, inspect the current source and tests for one specific browser path, including destination identity and response capture, instead of repeating a general browser inventory.

## 5. What is already audited vs what must not be claimed

| Claim | Current evidence status |
|---|---|
| Principal continuity organs are present and wired in source | **Partially source-verified** by the Oct. 24 static audit |
| Space-Time is defined as a cross-chat continuity/project layer | **Documented and source-backed as design** |
| Intent/context passes through the adaptive orchestrator | **Source path exists**; not all consumers or outcomes traced end-to-end |
| A bounded parallel comparison can run for top-ranked IA candidates | **Source path verified**; runtime not run here |
| Arbitrary tasks can be decomposed and multiple chats safely edit one project simultaneously | **Not demonstrated** |
| Required capabilities always constrain the final tool selection | **Gap in the inspected normal path** |
| Fresh, task-bound context always reaches external AI chats | **Not demonstrated; freshness and transport limits documented** |
| External chats confirm receipt and their output is correlated end-to-end | **Not demonstrated universally** |
| Lessons are demonstrably reused in a later task and improve outcomes | **Not proven** |
| Coordinator runtime / causal Space-Time reuse is operational | `NOT_PROVEN` in existing canonical design records |
| The full project was audited or tests passed in this checkpoint | **False; no full repo audit or test run was performed** |

## 6. Ordered work queue after the current provenance prerequisite

This queue is **not a change to canonical routing or an authorization to implement**. Resume from the freshly fetched live `CURRENT-STATE.md` and require a new scope/permission decision where needed.

### W0 — Close the current canonical evidence task
**Owner/Producer in the existing local session.** Produce the directory-to-directory delta and preservation package with staged/unstaged/untracked state kept distinct. Reconcile all paths, including `github_owner_merge_bootstrap.py` if confirmed. Establish exactly what differs now; do not claim historical cause without evidence.

**Acceptance:** reproducible manifest of both paths/revisions; complete path union; hashes for preserved artifacts; delta clearly labeled current-only vs historically attributed; no source overwritten; fetchable receipt with source/provenance.

### W1 — Freeze the capability demand → concrete tool contract
Reuse `CapabilityReadiness`, existing descriptors and source reconciliation receipts. Specify demand identity, operation/success predicate, authority/eligibility rules, evidence/provenance and status behavior. Trace all normal callers to the final picker, especially session-based execution and request-based external consultation.

**Acceptance:** every normal path preserves the same required-capability identity; no preference/selector/lexical/first-card fallback bypasses hard eligibility; no candidate yields a safe deferred/blocked result; focused synthetic tests cover eligible/ineligible/unknown/unavailable and explicit-preference conflicts.

### W2 — Reconcile selection precedence and actual input delivery
Trace actual call sites across `LocalRoleRouter`, `AdaptiveModelSelector`, `SynapticRouter`, `InteractionModeSelector`, `ToolTeachService` and `ToolRegistry`. Distinguish hard constraints from scores/preferences. Verify health, quota/resource inputs at the operative call site, not just selector method signature.

**Acceptance:** a frozen decision table matches implementation on the normal paths; constraints are hard; empty eligible set fails closed; explicit preference behavior is tested; selection trace records reasons and candidate exclusions.

### W3 — Complete task-bound Space-Time context freshness
Reuse the Oct. 24 audits and RQ13 receipts. Expose context package identity/provenance, age, objective/session binding and stale/degraded status. Resolve the goal-before-perception sequencing question by consumer-level evidence. Do not rebuild away rich history merely to force freshness.

**Acceptance:** stale context is visible and cannot silently masquerade as current objective state; every decision can identify the package/objective version it used; relevant RQ13 results are referenced rather than re-executed without cause.

### W4 — Verify one named external session handoff end-to-end
Choose one supported, authorized destination first; do not generalize from a Devin adapter to every chat. Trace producer → persisted package → loader → briefing → send attempt → receipt/correlation → returned response. Only test runtime transport when explicitly permitted by the canonical route.

**Acceptance:** exact task and destination/session identity; package ID/version/digest and timestamps; distinct send/accepted/receipt states; response correlated to the same task; unsupported acknowledgments remain unverified.

### W5 — Define/verify multi-worker scheduling only after W1–W4
First inventory existing worker/cognitive-load/parallel-comparison components. If they are insufficient, design the smallest extension to the existing coordinator: task DAG/dependencies, distinct worker/task IDs, isolated worktrees/branches, one active writer per semantic/file scope, bounded concurrency from real resources/quotas, timeout/cancellation/retry, correlation, independent review and merge rules.

**Acceptance:** a synthetic end-to-end demonstration of two disjoint workers, one deliberate conflict/failure, deterministic reconciliation, preservation of canonical route, and a later task that reuses one adjudicated lesson. Do not activate a broad worker swarm before capability selection, context provenance and authorization gates are sound.

### W6 — Reverify browser/UI paths as their own transport
After the route permits it, test the exact foreground/background/CDP/browser mode and destination mapping. Validate no wrong-tab selection, clear response capture/receipt, consistent configuration and explicit capability validation. Treat real-account/browser actions as separate permissioned runtime work.

## 7. Resume protocol: avoid wasting prior investigation

At the next session:
1. Fetch live `main`; record current SHA/time.
2. Read `CURRENT-STATE.md` first and honor its single `NEXT_ACTION`. This checkpoint and all draft PRs are secondary.
3. Complete W0 using the existing local/Owner-provided evidence route. Do not re-run unrelated audits or sync searches.
4. Retrieve only the specific receipts named above for the first authorized next stage.
5. Pin the exact base SHA and source blob SHAs; distinguish source facts, owner-reported facts, inference, and proposal.
6. Author one bounded isolated candidate at a time with acceptance tests. Do not modify a shared working tree or let two workers own the same file/semantic contract.
7. Have an independent reviewer adjudicate the candidate. Record exact test commands/results or `NOT_RUN`.
8. Update canonical route/front doors together only under the applicable authorized process, then fetch-back verify. A draft PR or saved document is not canonical.
9. Close a finding only when the acceptance evidence supports the precise claim. Keep a separate list of residual limitations.
10. Never start an automatic follow-on: `AUTOMATIC_FOLLOW_ON=FALSE`.

## 8. Related in-flight documentary proposal

A separate draft, [PR #522 — propose collective Space-Time AI coordination](https://github.com/jhonf463r/Python/pull/522), adds a conversation-intent route that distinguishes active-task execution, meta-coordination consultation, side question, unrelated objective and delegation intent. It is also **not canonical**, has not been merged, and does not demonstrate runtime behavior. Its example worker packets are optional and not dispatched.

This checkpoint does not merge, replace or assume adoption of PR #522. Reconcile the two documentary proposals during review so the accepted source of truth does not grow duplicate or competing protocols. The intended final design is one existing Space-Time/MOP coordinator with conversation awareness, not a new supermind service or memory.

## 9. Explicit non-claims and stop conditions

- No product code or tests were modified by this checkpoint.
- No runtime, build, automated tests, real transport, external AI chats, browsers or OS actions were executed.
- G1/G2/G3 remain `NOT_ESTABLISHED`; `PROTECTED_READS=FAIL_CLOSED`; `BRIDGE=BRIDGE_NOT_READY` as recorded by canonical routing.
- No credential/trust asset was inspected by this checkpoint. `UNKNOWN` does not mean `ABSENT`.
- Do not merge this document into `main` or treat its queue as authorized source work until the documented current route is reconciled and the relevant Owner/governance permission exists.
- Do not bypass a blocked read or transport by using an alternate reader/path.
- If W0 cannot produce admissible evidence, stop and record the exact missing evidence/route; do not restart the same broad audit.

## 10. Compact handoff snapshot

```text
NORTH_STAR=GOVERNED_IABV_CODEX_BRIDGE
AUDIT_KIND=STATIC_SOURCE_AND_DOCUMENT_RECONCILIATION
AUDIT_BASE_MAIN=5965735167b50d12bc98543d132d70022fb73803
AUDIT_RUNTIME=NOT_RUN
AUDIT_TESTS=NOT_RUN
COORDINATOR_ARCHITECTURE=PARTIALLY_SOURCE_VERIFIED
GENERAL_MULTI_CHAT_COORDINATION=NOT_PROVEN_END_TO_END
BOUNDED_PARALLEL_IA_COMPARISON=SOURCE_PATH_PRESENT
CAPABILITY_TO_TOOL_ELIGIBILITY=GAP_IN_INSPECTED_NORMAL_PATH
SELECTOR_PRECEDENCE=PARTIAL / MULTIPLE DECISION PATHS
PORTABLE_CONTEXT_FRESHNESS=STATIC_RISK
GOAL_BEFORE_PERCEPTION=STATIC_ORDERING_RISK
UNIVERSAL_EXTERNAL_DELIVERY=NOT_PROVEN
DELIVERY_RECEIPT_AND_CAUSAL_REUSE=NOT_PROVEN
BROWSER_MULTI_MODE_CONTROL=NOT_END_TO_END_VERIFIED_HERE
CURRENT_CANONICAL_TASK=M1A_G1_RECONCILE_CANDIDATE_PRETASK_DIFF_PROVENANCE_20261025
CANONICAL_NEXT_ACTION=PRODUCER_GENERATE_ONE_CURRENT_DIRECTORY_TO_DIRECTORY_DELTA_AND_PRESERVATION_PACKAGE
PRODUCT_SOURCE_EDIT=NOT_AUTHORIZED_BY_THIS_DOCUMENT
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED_BY_CURRENT_ROUTE
PROTECTED_READS=FAIL_CLOSED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
AUTOMATIC_FOLLOW_ON=FALSE
CHECKPOINT=SUPPLEMENTARY_DRAFT; NOT_CANONICAL
```

**Closing rule:** The goal is not to add more organs to IABV. The goal is to prove and repair the interfaces between the existing organs in dependency order, preserve each result with provenance, and resume from the exact canonical route without repeating closed investigations.
