# UAAL-D020 — Verified Progress Utility, Strategy Switching, and Preparation-Debt Control

**Date:** 2026-10-28  
**Root:** `UAAL-ROOT-001`  
**Parent:** `UAAL-D019` — Space-Time Anti-Loop and First-Open Causal Frontier  
**Conceptual lineage:** `UAAL-D014` — Meta-Method Plasticity / Failure-to-Evolution Loop  
**Refines:** `UAAL-D019` and `UAAL-D018`  
**Status:** `DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT_AND_CAUSAL_REUSE_NOT_PROVEN`

## 1. Observed failure and narrow diagnosis

During `M1B_CONTEXT_EXPORT_READONLY_READER_IMPLEMENTATION`, Codex reported that it stopped before modifying files because the authorized SHA was not available in the local Git object store and no isolated worktree existed. The previous clone attempt had failed with a filename-length error. The report explicitly said no fetch, file change, tests, build or runtime occurred.

The next proposed action was another local preparation recipe (short path, shallow/no-checkout clone, sparse materialization) and a new Codex prompt. That route was plausible but had not been executed, and its superiority had not been established against the already available GitHub repository API for documentation changes. The response therefore increased preparation work without yet proving that it reduced a dependency of the bridge.

**Diagnosis:** the existing UAAL-D019 anti-loop and dual-track rules were directionally correct but insufficiently operationalized at the progress-selection point. The coordinator can avoid repeating an identical attempt yet still choose a succession of plausible *preparatory* steps instead of the shortest admissible action that closes or discriminates the target dependency. This record is scoped to that observed episode; it does not claim a repository-wide measurement of every past loop.

## 2. Universal invariant: every action needs an advance contract

Before an action, bind it to the current objective using this compact contract:

```text
ADVANCE_CONTRACT = {
  objective_and_acceptance,
  target_open_dependency_edge,
  current_evidence_state,
  action_class,
  exact_preconditions_and_authority,
  expected_observable,
  acceptance_or_stop_condition,
  strategy_switch_condition,
  owner_effort_and_risk
}
```

The action must do at least one of the following:

1. **CLOSE:** move the named critical dependency from open to verified closed.
2. **DISCRIMINATE:** resolve an uncertainty or falsify a hypothesis that changes the next action.
3. **ENABLE:** remove a demonstrated necessary prerequisite for one of the above, when no simpler authorized route is available.
4. **PRESERVE SAFETY:** prevent a material unsafe transition while naming what remains blocked.

A prompt, plan, checkout, inventory, status note or design is not progress merely because it exists. Treat it as preparation unless its acceptance criterion demonstrates a real dependency change or a necessary prerequisite has been verified.

## 3. Lexicographic selection: usefulness before activity

Apply this order; do not replace it with an arbitrary numerical score that could trade away a safety gate:

1. **Authorization and hard constraints:** reject inadmissible actions first.
2. **Verified target-edge closure:** prefer an action that directly closes the first open critical edge.
3. **Decision-changing information gain:** otherwise prefer the smallest action whose possible outcomes distinguish between live hypotheses.
4. **Necessary enablement:** preparation is allowed only when its causal link to a target edge is explicit and no supported, lower-dependency realization can do the work directly.
5. **Operational economy:** among otherwise equivalent actions, minimize new dependencies, owner manual effort, environmental mutation, cost, irreversibility and verification burden.
6. **Learning claim:** promote a method as *causally reused* only after a later non-identical task proves it changed action selection and yielded independently verified results.

After execution, calculate the qualitative delta:

```text
ADVANCE_DELTA = {
  target_edge_before_and_after,
  hypothesis_before_and_after,
  new_verified_capability_or_prerequisite,
  dependencies_added_or_removed,
  owner_effort_and_risk,
  evidence_and_fetchback
}
```

Set `VERIFIED_PROGRESS=TRUE` only when a target edge closes or decision-relevant uncertainty is materially reduced. Otherwise record `PREPARATION_ONLY` or `NO_PROGRESS`; do not inflate the status.

## 4. Strategy-switch algorithm after a blocker

A terminal failure closes the attempted route under its observed fingerprint, not necessarily the objective. Preserve the exact result and then perform one bounded capability-fit comparison:

1. **Name the failure edge.** State what failed, what did not run, and what is still unknown. Do not turn “route unavailable” into “resource absent.”
2. **Test causal fit.** Answer: (a) which observed blocker does the proposed next route address? (b) which relevant precondition or operation differs from the failed attempt? (c) what observable result would prove that the change helped? If these cannot be answered, do not start that route.
3. **Discover actual available realizations.** Inspect the tools, connected repository surfaces, local/cloud agents and artifacts that are genuinely available in this session. Do not assume the local checkout is the only way to edit a repository; do not assume a connector or agent has capabilities that its live tool contract does not expose.
4. **Compare only viable candidates.** Prefer `REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`. Compare target fit, causal fit, authority, prerequisites, expected information gain, risks, owner effort and independent verification path. Avoid a broad inventory if a small comparison answers the question.
5. **Take one discriminating action** on the best supported route. Define the stop/switch condition before acting.
6. **Reconcile the result.** Verify the exact output against the exact target and revision; update the owning rule/router only when the evidence supports it.
7. **Bound route hopping.** Before a third attempt at the same target edge, require an explicit material delta and evidence explaining why the new route is causally different. Otherwise return to hypothesis/route selection and identify the first missing prerequisite instead of generating another prompt.

For example, a local Git object missing from one checkout does not by itself require syncing or replacing that checkout. For a documentation-only GitHub change, first check whether the authorized GitHub connector can perform the change directly on an isolated branch. For a task that requires local execution or tests, a clean local checkout may still be necessary. The general rule is capability-based selection, not preference for a particular platform.

## 5. Preparation-debt detector and recursive decomposition

Mark a step `PREPARATION_ONLY=TRUE` when it creates instructions, plans, scaffolding, a fresh environment or an additional handoff without changing the target edge or resolving a decision-changing uncertainty.

- One preparation-only step requires a stated causal justification and an observable acceptance condition.
- Two consecutive preparation-only steps on the same objective trigger a mandatory strategy reset before any third such step.
- A child task must name its parent objective and the exact edge it can close. Do not recursively decompose a child that cannot demonstrate that relationship.
- If a subtask only restates the parent blocker, stop recursion and revise the realization/hypothesis.
- Never let a progress metric override authorization, privacy, no-bootstrap, or fail-closed requirements.

This rule limits *unproductive recursion*, not useful iterative reasoning. Re-enter the loop only after new evidence, a material state change or a genuinely different falsifiable experiment.

## 6. Distinguish project progress from useful housekeeping

Use these status classes:

- `TARGET_EDGE_CLOSED` — closure independently verified.
- `DECISION_UNCERTAINTY_REDUCED` — new evidence changes the optimal next action.
- `NECESSARY_PREREQUISITE_VERIFIED` — the required enabler is proven and linked to a named target edge.
- `PREPARATION_ONLY` — an artifact or setup was produced, but no target dependency changed.
- `NO_PROGRESS` — activity did not close an edge or improve the decision.
- `BLOCKED_NO_ADMISSIBLE_ROUTE` — after the bounded strategy comparison, no action is both authorized and useful.
- `NOT_RUN` — action was not executed.
- `NOT_VERIFIED` — an output exists but its claimed effect is not established.

Housekeeping and method documentation can be the target when the Owner explicitly requests them. They must not be misrepresented as bridge implementation or operational readiness.

## 7. Application to this incident

```text
TASK=M1B_CONTEXT_EXPORT_READONLY_READER_IMPLEMENTATION
RESULT=BLOCKED_BEFORE_FILE_MODIFICATION; OWNER_CODEX_REPORTED
LOCAL_CHECKOUT=NOT_CREATED_FOR_THIS_ATTEMPT
C_CODEX_IMPLEMENTATION=NOT_STARTED
TESTS_BUILD_RUNTIME=NOT_RUN
PREVIOUS_ROUTE=LOCAL_ISOLATED_CHECKOUT_PREPARATION
CAUSAL_SUPERIORITY_OF_RETRY=NOT_ESTABLISHED
METHOD_GAP=NO_EXPLICIT_PROGRESS_UTILITY_GATE_OR_REQUIRED_CAPABILITY_SURFACE_COMPARISON
CORRECTION=UAAL-D020; DOCUMENTATION_METHOD_ONLY
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
CAUSAL_REUSE=NOT_TESTED
```

The existing G1 terminal result remains terminal under its original conditions. This method correction neither reopens the G1 assessment nor authorizes implementation, tests, runtime, credentials, trust bootstrap, protected reads, tunnel or deployment. The separately authorized task here is documentation-level method evolution only.

## 8. Cross-AI activation and causal reuse contract

UAAL-D020 applies to the **participating AI sessions that consume the shared GitHub memory**, not only to the IABV product or its local runtime. This includes ChatGPT, Codex and other collaborators when they have an actual, permitted way to retrieve the repository context. The shared memory is an external context substrate: it can condition a session's reasoning when retrieved and applied, but does not automatically alter model weights, guarantee delivery to another session or prove that another agent consumed the lesson.

For material routing, implementation-planning, continuity or protocol decisions, use this activation chain:

```text
VERIFY_LIVE_MAIN
→ RETRIEVE_CURRENT_ROUTE_AND_OBJECTIVE_RELEVANT_METHOD
→ BIND_RELEVANT_MEMORY_TO_CURRENT_FRONTIER
→ COMPARE_CANDIDATE_ACTIONS_WITH_AND_WITHOUT_THE_RULE
→ SELECT_ONE_AUTHORIZED_DISCRIMINATING_ACTION
→ OBSERVE_AND_VERIFY_OUTCOME
→ WRITE_BACK_KNOWLEDGE/METHOD/ROUTING_DELTA
→ LATER_NONIDENTICAL_REUSE
```

Keep these stages distinct:

- `MEMORY_RETRIEVED`: the actual live source/ref was retrieved; record exact path/revision or commit/blob when relevant.
- `METHOD_ACTIVATED`: explain which rule applies to the current objective and why.
- `METHOD_APPLIED`: state how the rule changed the candidate set, rejected a loop, changed the selected actor/channel or otherwise changed the next decision. When useful, record the plausible action that would have been selected without the rule; do not invent a counterfactual after the result.
- `OUTCOME_VERIFIED`: the action's result was correlated with the exact target and acceptance condition.
- `LATER_CAUSAL_REUSE`: only claim this when a later non-identical task, session or context retrieves the durable rule, changes its decision for the relevant reason, and produces an independently supported outcome.

Retrieval is not activation; activation is not application; application is not successful outcome; writeback is not delivery; delivery attempt is not recipient receipt; a similar answer is not proof of causal reuse. If stage evidence is absent, report `UNKNOWN`, `NOT_OBSERVED` or `NOT_TESTED`, rather than infer success.

Every material inter-agent handoff must preserve the exact task/target revision, the relevant evidence classes and terminal results, one target causal edge, authorization boundaries, expected receipt/acceptance, and the reason the destination AI is selected. Specify `IA DESTINO`, `CAPABILITY REQUIRED` and `WHY THIS AI NOW` near the top. Actor order remains dynamic: choose by current frontier, demonstrated capability, actual access and independent-verification need—not by a fixed historical sequence.

Do not make every small task pay the cost of a full archive audit. Use the canonical current route and activate only relevant memory. For a material task, a concise activation/application receipt is sufficient; do not duplicate the entire history. Consolidate verified reusable lessons into the existing owning method and `SYMBIOSIS-MAP.md`, synchronize routing front doors when necessary, and fetch back canonical writeback. Do not create a second memory store, router or agent to solve a memory-use problem.

**Observed scope correction (2026-10-28):** the Owner clarified that the intended developmental target is the shared method used by AIs consulting GitHub memory, not only IABV's local/product algorithms. The previous D020 writeback improved generic task selection but did not make the cross-AI consumption/application contract explicit in the symbiosis method. This extension repairs that connection; it does not prove that another session has consumed or reused the rule.

### Code-candidate evidence and security-boundary gate — applied lessons from M1B/M1A (2026-10-28/29)

The M1B reader and M1A authorization-composition episodes show that a staged source/test gate needs a claim-by-claim security-boundary vector. Do not promote a narrow fixture success into a wider trust or production claim.

1. **Separate evidence stages:** LOCAL_CANDIDATE_REPORTED → EXACT_FINAL_SOURCE_AVAILABLE → STATIC_REVIEWED → TESTS_EXECUTED → SOURCE_PUBLISHED_BRANCH → PR_DIFF_REVIEWED → MAIN_FETCHBACK_VERIFIED. Do not collapse these into implemented or done.
2. **Identify exact bytes and Git state.** Record base SHA, branch, git status, path, size and SHA-256 for each file. Untracked files are not part of a normal HEAD diff; do not claim they are in GitHub. A hash is not a substitute for reviewer access to that content.
3. **Review the final version, not a prior draft.** If source changes after review, re-review the changed lines and bind the review to the final source hash. When the final source is not available in full, label the review partial.
4. **Validate schema against reality.** Compare validators with live domain-model definitions and actual versioned artifact shapes. Test malformed cases and legitimate examples. Dates labelled UTC must include an explicit timezone; test Z/offset acceptance and naive-datetime rejection.
5. **Treat tests as an authorized, distinct action.** Record exact interpreter, version, command, scope, counts and exit code. A targeted suite pass does not prove the full suite, build, runtime, race resistance, publication or bridge authorization. The final command and collection count must refer to the final source bytes; preserve intermediate contradictory results as history instead of blending them into the final result.
6. **Promote by verifiable evidence.** When the local candidate exists and tests are reported passing, do not reclone or reimplement. Publish that exact candidate to an isolated branch/PR, review the actual diff and fetch back the exact merged result if/when merge is authorized.
7. **Preserve provenance.** Mark execution received from Codex OWNER_CODEX_REPORTED until independently reproduced or corroborated by retrievable CI evidence. A detailed receipt alone does not elevate the result to independently VERIFIED.

#### Security-boundary vector — required for authorization, file and directory capabilities

For a security-sensitive code change, freeze the acceptance oracle before implementation and adjudicate each claim separately:

| Claim | Evidence needed | Must not infer |
|---|---|---|
| OPENED_OBJECT_IDENTITY | Native identity derived from the exact live handle | That the object is under an approved root |
| ROOT_PROVENANCE | Host-owned root provider with independently justified trust/custody | That a temporary test root is the Owner-approved production root |
| ROOT_TO_TARGET_CONTAINMENT | Source-backed opening/containment mechanism relative to the trusted root; escape and reparse-point failure semantics covered | That path normalization, a textual prefix or the target's file ID proves containment |
| AUTHORIZATION_BOUND_TO_CAPABILITY | The decision evaluates the same operation/context and capability later supplied to the consumer | That a deny-only coordinator or a type declaration proves a positive authorization sequence |
| SAME_CAPABILITY_CONSUMED | An observable identity/instance binding plus tests that the consumer does not resolve or reopen by name | That a low-level handle-read fixture proves the whole authorization-to-consumption chain |
| PRODUCTION_PROVIDER_AUTHENTICITY | Real host-owned providers and mandatory bindings validated at composition | That synthetic providers or passing unit tests establish G1/G2/G3 |
| NATIVE_ACCEPTANCE | Authorized native-platform acceptance evidence on the exact final candidate | That a simulated ABI, fixture or source inspection proves native behavior |
| STABLE_DIRECTORY_VIEW | Separate, documented proof for stable enumeration under the stated threat model | That opening a directory handle or proving target identity establishes an atomic/stable listing |

Use only the vector entries applicable to the change, but never merge adjacent claims into one. In particular, R3's reported temporary-fixture result supports only the limited OPENED_OBJECT_IDENTITY and low-level same-handle consumption claims. It does not close ROOT_PROVENANCE, ROOT_TO_TARGET_CONTAINMENT, or AUTHORIZATION_BOUND_TO_CAPABILITY; consequently it cannot establish production readiness.

#### Authority edge versus implementation edge

When the next unresolved dependency requires an Owner-held trust choice (for example OWNER_ROOT_SELECTION=NOT_PROVIDED), do not fabricate a root or provider to keep coding moving. Continue only with bounded mechanics/tests whose result is useful regardless of the real choice, keep production deny-only, and state the exact Owner/authority prerequisite. Conversely, do not use that missing production decision to stop independent, authorized contract work that can still discriminate an engineering question.

Before directing an actor to implement a native security boundary, verify the primary API contract and name the exact property the experiment will prove. If the experiment can prove only a fixture-level mechanism, scope its acceptance accordingly; do not request a full root-bound-composition closure from a test that lacks a trusted root or production decision path.

The episode is bounded evidence of this method correction, not proof that the protocol is automatically enforced or that the model has changed weights. Receipt for the original reader-specific gate: [M1B implementation and test receipt](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-28-M1B-CONTEXT-READER-IMPLEMENTATION-AND-TEST-RECEIPT.md).


## 8.1 Claude and cross-product GitHub-memory symbiosis (2026-11-03)

The intended symbiosis is a **shared external context substrate plus explicit retrieval and decision application**, not a hidden shared model, automatic memory injection or model-weight update. Claude can participate in the same GitHub-backed memory method as ChatGPT and Codex only when the actual Claude session has an authorized route to the repository, or when a bounded, provenance-labelled source package is transferred to it. The coordinator's GitHub access does not imply that Claude has the same access; Claude's inability to retrieve a source does not prevent the coordinator from retrieving it through its own connected tools.

For every material Claude or other external-AI handoff, the coordinator and recipient each perform their own side of the activation:

1. **Coordinator side — compile from live memory.** Refresh the owning project's canonical route and exact `main` revision. Retrieve the relevant D019/D020/D021, Space-Time and SYMBIOSIS method slices plus the objective-relevant project state. Check the coordinator's actual connected GitHub/file capabilities and retrieve public repository material directly when authorized. Do not ask the Owner to paste or upload public content that the coordinator can fetch.
2. **Destination side — identify actual access.** Record the exact provider, product surface, session continuity and model-label provenance. Probe only the source-access capabilities required by the task. Claude.ai web/app, Claude Code and Claude API are distinct destinations; neither GitHub, shell nor outbound network is implied by “Claude Sonnet 5.5”.
3. **Select the transfer route.** Prefer recipient live retrieval when it is actually available and required for independence. Otherwise transfer the smallest pinned package/diff the coordinator can verify, label it as coordinator-exported/attested, and restrict the conclusion to the evidence that route supports. Never claim independent live retrieval from a copied prompt, URL or package.
4. **Bind and activate the method.** Give the recipient the exact source revisions and only the relevant memory slice. Ask it to identify the method that applies, the candidate action it rules out or confirms, the decision delta, and the first remaining edge. The receiver must use the live source it actually retrieved, not the coordinator's assertion that a link was sent.
5. **Reconcile the returned result.** Treat the pasted response as actor-reported until its source evidence is adjudicated. Verify its claims against the exact task/ref and acceptance condition. Write back only the reusable, evidence-supported knowledge/method delta to the existing owning records.

Use the following as a compact prompt-compiler contract for external-AI tasks:

```text
CROSS_AI_PROMPT_COMPILER
TASK_AND_ACCEPTANCE=
CANONICAL_PROJECT_ROUTE_AND_REVISION=
RELEVANT_GITHUB_MEMORY_SLICES=
COORDINATOR_CAPABILITY_EVIDENCE=
RECIPIENT_PROVIDER_SURFACE_SESSION_MODEL=
RECIPIENT_CAPABILITY_EVIDENCE=
TASK_SPECIFICATION_PROVENANCE=
SOURCE_TRANSPORT_ROUTE=
SOURCE_MANIFEST_AND_COVERAGE=
CONTEXT_SEPARATION_IF_REVIEW=
AUTHORIZED_SCOPE_AND_EXCLUSIONS=
FIRST_OPEN_CAUSAL_EDGE=
EXPECTED_RETURN_AND_RECEIPT=
STOP_CONDITION=
PROMPT_STATUS=PREPARED_NOT_SENT|SENT_UNVERIFIED|RECIPIENT_ACKNOWLEDGED
```

The receiver's method-activation receipt must distinguish `MEMORY_RETRIEVED`, `METHOD_ACTIVATED`, `METHOD_APPLIED`, `OUTCOME_VERIFIED` and `LATER_CAUSAL_REUSE`. A concise rationale is sufficient: name the applicable rule, the decision it changed/confirmed and its evidence. Do not request or publish private chain-of-thought. Retrieval alone is not application, and one successful handoff is not proof of generalization.

### Optional Claude Sonnet 5.5 prompt profile

Use this profile only when the model is actually identified as Claude Sonnet 5.5, and re-check the official guide before relying on version-specific settings. Anthropic's guide (checked 2026-11-03) describes Sonnet 5.5 as adaptive-thinking, and recommends calibrating effort to workload: for well-specified multi-step agentic work, start at medium; for harder or longer work, use high; for latency-sensitive chat, medium or low may be suitable. Higher effort may take longer and can be more expansive, so pair it with exact scope, exclusions and stop conditions. At low/medium effort, a long agentic task may check in before completion; a clear instruction to finish the authorized deliverable unless a real dependency or risky step requires user input can reduce avoidable pauses. Use explicit tool instructions for current facts rather than relying on training knowledge.

These are model/API guidance, not guaranteed controls in every Claude interface. Do not prescribe API-only parameters to claude.ai or a mobile/desktop chat. Do not equate Sonnet's advertised context window with the capacity of a single web-fetch, REST response, attachment, or tool-result. For coding tasks, require a real authorized check before reporting completion; when tests are explicitly excluded or unauthorized, preserve `NOT_RUN` and state the reason.

Official version-specific reference: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5

## 9. Decision-complete advance packets and Owner-turn minimization (2026-11-02)

UAAL-D019 §9E is the owning pre-action decision-completeness algorithm. This section binds it to D020's advance contract and lexicographic progress selector; it does not create a second selector or override authorization.

Before any Owner-facing step on a material UI/device/account task, enrich `ADVANCE_CONTRACT` with:
- actor split: what the coordinator can retrieve/verify directly, what the Owner alone must do, and what requires an external authority;
- exact target UI/account/device and current route permission;
- read-only versus mutating action classification;
- one ordered Owner sequence;
- a branch matrix for foreseeable success, unavailable option, policy denial, unsupported platform, handoff failure and unexpected result;
- exact evidence that accepts each branch and the next actor/action;
- stop/recovery behavior and the minimum number of Owner round-trips.

**Selection and interaction constraints**

1. Do not ask for information already in the Owner ledger, current conversation, a supplied screenshot, the connected repository or another available authorized source.
2. Finish coordinator-side research, state retrieval and route comparison before requesting local interaction.
3. Do not drip-feed instructions across predictable screens. Provide the entire safe action sequence and the outcome-specific next steps together. Pause only where the next action depends on an unpredictable state, a high-impact decision or a required authorization.
4. Do not interpret an available UI option as permission to use it. A mutation must pass the canonical authorization/no-bootstrap filter before it can appear as an Owner instruction.
5. Interpret screenshots directly and ask only for an omitted or unreadable fact whose value changes the route.
6. After the Owner reports or supplies the outcome, select the precomputed branch, do all newly enabled coordinator-side work and verify the resulting target-edge delta. Do not ask the Owner to perform analysis the coordinator can do.
7. A lower interaction count is not a goal at the expense of security. Retain explicit confirmation for sensitive, irreversible or separately scoped actions.

**Operational metrics**

```text
OWNER_ROUND_TRIPS=
REPEATED_FACTS_REQUESTED=
PREDICTABLE_BRANCHES_PRECOMPUTED=
UNPLANNED_MICRO_PROMPTS=
ASSISTANT_SIDE_WORK_COMPLETED_FIRST=
MUTATION_PERMISSION_PREFLIGHT=PASS|FAIL|NOT_APPLICABLE
TARGET_EDGE_DELTA=
RESULT=TARGET_EDGE_CLOSED|DECISION_UNCERTAINTY_REDUCED|NECESSARY_PREREQUISITE_VERIFIED|PREPARATION_ONLY|NO_PROGRESS|BLOCKED_NO_ADMISSIBLE_ROUTE
```

The method passes only when the decision trace demonstrates that precomputation prevented at least one avoidable Owner round-trip or premature action, while preserving all permission boundaries and independently verifying the outcome. Until such a later non-identical task is observed, mark `CAUSAL_REUSE=NOT_TESTED`; the documentation update itself is not proof that the coordinator has learned or that every future chat will enforce the rule.

## 10. Acceptance and falsification

On a later, non-identical task, evaluate this method with a decision trace. Success requires evidence that the selector (a) names the target edge, (b) compares the proposed route with actually available authorized realizations, (c) rejects unsupported preparation loops, (d) chooses a route with a predicted observable, and (e) verifies the outcome before claiming progress. The trace must show that applying the rule changed the chosen action or outcome relative to the prior default.

If it repeatedly adds material overhead without improving edge closure or decision quality, revise or reject the mechanism. The protocol itself is not proof of execution, automated enforcement, persistent model learning or model-weight change.

```text
CONCEPT_ID=UAAL-D020
PARENT_CONCEPT_ID=UAAL-D019
REFINES=UAAL-D019; UAAL-D018
ROOT=UAAL-ROOT-001
STATUS=DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT=NOT_PROVEN
TASK_ID_POLICY=NEW_TASK_PER_REVISION
COMMIT_PROFILE=GATE_COMMIT
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
CAUSAL_REUSE=NOT_TESTED
```
