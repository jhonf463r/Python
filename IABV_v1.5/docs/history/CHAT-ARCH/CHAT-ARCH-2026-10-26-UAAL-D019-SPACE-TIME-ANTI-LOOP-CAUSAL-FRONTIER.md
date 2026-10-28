# UAAL-D019 — Space-Time Anti-Loop and First-Open Causal Frontier

**Date:** 2026-10-26  
**Root:** `UAAL-ROOT-001`  
**Parent:** `UAAL-D014` — Meta-Method Plasticity / Failure-to-Evolution Loop  
**Refines:** `UAAL-D018` — Execution-to-Evidence Stage Separation / Observability  
**Status:** `DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT_AND_CAUSAL_REUSE_NOT_PROVEN`  
**Observed baseline:** live `main=54c3e45ec497c83e839bdd6971d33fadbd4ec644`  
**Historical technical candidate at the 2026-10-26 observation:** PR #531, `OPEN/DRAFT/UNMERGED`, HEAD `bc2baf525a70d66628809360a197f25a069aa328`.

## 1. Why this refinement exists

The existing space-time protocol already requires fresh canonical state, terminal-result consumption, negative knowledge, evidence-stage separation and avoiding repetition of closed paths. This refinement does not claim those principles were absent. It makes them more operational at the moment a new chat chooses its next action.

The recurring failure mode is a reasoning loop in which an AI retrieves history but does not bind the prior result to the proposed action; repeats an action with unchanged causal preconditions; receives the same blocker or an output that never reaches the intended test/consumer; and reports activity without crossing a dependency. Another summary alone does not fix that loop.

The correction is to require every proposed action to demonstrate that it is the **next discriminating step**, not merely a plausible next step.

## 2. Core algorithm

Reuse the existing memory, current-state router, evidence receipts and operating protocol. Do not create a second memory store, coordinator, agent, router or parallel orchestration layer.

```text
REFRESH_LIVE_STATE
  → BIND_OBJECTIVE_AND_SUCCESS_CRITERIA
  → RETRIEVE_RELEVANT_EPISODES_AND_TERMINAL_RESULTS
  → BUILD_EVIDENCE_AND_DEPENDENCY_GRAPH
  → CLASSIFY_KNOWN / UNKNOWN / CONFLICTED / CLOSED
  → FINGERPRINT_PROPOSED_EXPERIMENT
  → LOCATE_FIRST_OPEN_CAUSAL_EDGE
  → FILTER_AUTHORIZATION_AND_HARD_PRECONDITIONS
  → SELECT_ONE_DISCRIMINATING_ACTION_OR_TRUTHFUL_WAIT
  → ACT_WITH_OBSERVABILITY_CONTRACT
  → CLASSIFY_RESULT_AT_ITS_ACTUAL_STAGE
  → VERIFY_AND_RECONCILE
  → UPDATE_OWNING_RULE_AND_CURRENT_ROUTE_WHEN_JUSTIFIED
  → FETCH_BACK_CANONICAL_WRITE
  → TEST_REUSE_IN_A_LATER_NON_IDENTICAL_TASK
```

Repeat the loop only after the observed result changes the state, reveals new evidence, or a valid new premise authorizes a different experiment.

## 3. Experiment fingerprint and anti-loop detector

Before an action, record the decision-relevant fingerprint:

```text
EXPERIMENT_FINGERPRINT = {
  objective_and_acceptance,
  target_object_and_exact_revision_or_digest,
  operation_and_material_inputs,
  actor_and_execution_route,
  authorization_and_hard_preconditions,
  relevant_environment_and_runtime_state,
  expected_observation_and_stop_condition
}
```

Attempt ID, chat ID, timestamp, rewritten wording or a new branch name identifies an event but is not evidence that the causal experiment is different. Compare the decision-relevant dimensions and mark the proposal `SAME_EXPERIMENT` unless a relevant precondition, hypothesis, operation, evidence source or authorization has materially changed.

**No-repeat rule:** after the same action returns the same terminal blocker without producing new discriminating evidence, do not execute it again unchanged. Reopen only if at least one condition is documented:

- a relevant precondition changed and that change is observed;
- the next attempt tests a different explicit hypothesis and predicts a different observable;
- independently observed evidence supports a transient failure and a bounded retry plan is defined in advance;
- a new authorized scope or Owner decision changes the permitted action.

A new chat, new task number, changed wording, passage of time alone or pressure to make progress is not a material delta. A retry can be correct, but the retry must state what it is expected to teach that the previous attempt could not.

## 4. First open causal edge

Represent the route as a dependency chain, not a flat checklist:

```text
AUTHORITY_AND_PRECONDITIONS
  → ROUTE_AND_EXECUTOR_AVAILABLE
  → ACTION_INVOKED
  → JOB_PROCESS_OR_REQUEST_STARTED
  → EXPECTED_WORK_EXECUTED
  → RESULT_OBSERVED
  → RESULT_CORRELATED_TO_EXACT_INPUT_AND_REVISION
  → ACCEPTANCE_CHECKED
  → RESULT_INDEPENDENTLY_VERIFIED
  → CANONICAL_MEMORY_FETCH_BACK_VERIFIED
  → LATER_DECISION_CAUSALLY_REUSES_THE_DELTA
```

At each edge, name the required evidence and the earliest state that lacks it. Do not infer downstream stages from earlier success: source exists does not mean it ran; a workflow run exists does not mean a job started; a job starting does not mean tests passed; tests passing do not establish a production authority chain; persistence does not prove later reuse.

Choose the first open edge that blocks the active objective and can be addressed by an authorized action. Independent work may proceed only where already authorized and without bypassing that edge.

## 5. Stage-specific outcomes

Avoid collapsing a route into a generic `FAILED` or `SUCCESS`. Record the furthest directly supported stage:

- `NOT_INVOKED`
- `INVOKED_NO_OBSERVATION`
- `STARTUP_FAILURE_ZERO_JOBS`
- `EXECUTED_ASSERTION_FAILURE`
- `OBSERVED_UNVERIFIED`
- `PASS_WITH_SCOPE`
- `BLOCKED_AUTHORIZATION`
- `BLOCKED_PRECONDITION`
- `CANONICAL_FETCH_BACK_VERIFIED`
- `CAUSAL_REUSE_NOT_TESTED` / `CAUSAL_REUSE_VERIFIED`

No stage inherits success from the one before or after it. A visible blocker may be verified while its underlying root cause remains unknown.

## 6. Selection policy — localized blocker, dual-track progress

1. Exclude every action lacking authorization or an essential prerequisite; this filter cannot be overridden by a productivity score or explicit desire to move faster.
2. Identify the first open causal edge **for the specific target operation**, not a project-wide generic blocker. Record the terminal fingerprint and do not retry that same edge unchanged.
3. Build two lanes:
   - **Lane A — blocked technical frontier:** preserve its terminal result and wait for the exact changed precondition/evidence/authority needed to reopen it. Do not retry a terminal asset assessment, reconfigure Entra, substitute a tool/transport or infer that a local route failure proves global absence.
   - **Lane B — independent authorized progress:** scan the current Owner instruction, canonical router, relevant memory/backlog and permitted tool surfaces for work that advances the same North Star without crossing or depending on Lane A's gate. Include process/memory/documentation work only when directly requested or otherwise authorized. Prefer an existing work item over inventing a new one.
4. Rank admissible Lane B candidates by: relevance to the Owner's current objective; independence from the blocked edge; expected discriminating value; reversibility/safety; cost and time; reduction in Owner burden. Authorization and hard gates are filters, never soft scores.
5. For the selected action, record exact input/revision, prior-result fingerprint, why it is not the prohibited repeat, expected observation, stop condition and how each plausible result changes the route. Carry out one bounded action, then reconcile.
6. Wait only when no action is both authorized and usefully independent. The wait record must name the precise missing external input and distinguish it from other work that remains possible. Never manufacture an action just to avoid waiting; never use a blocked subtask to avoid doing an already authorized independent task.

**Owner continuation intent:** a request to “continue/proceed/evolve/organize” after a terminal result reopens selection for a new, explicitly bounded task in the requested scope. It does not reopen the same terminal task unless its decision-relevant preconditions changed, and it does not create trust authority or product implementation permission by implication.

## 7. Worked application — IABV-to-Codex bridge on 2026-10-26

### Verified current boundary

- Live `main` before this documentary refinement: `54c3e45ec497c83e839bdd6971d33fadbd4ec644`.
- PR #531 is `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`; candidate HEAD `bc2baf525a70d66628809360a197f25a069aa328`.
- A visible repository Actions UI warning says workflows cannot execute because the account billing is locked.
- Run #40406668947 is `startup_failure`, path `BuildFailed`, unnamed workflow and `jobs=[]`; no Python step or product test ran.
- The general Billing & Plans view did not show the same warning. The underlying account-lock cause remains `UNKNOWN`; usage minutes remain `UNKNOWN`.
- A public Community reply offered billing/index/ARC theories but was not an official diagnosis. Those explanations remain hypotheses; its suggested dummy workflow/diagnostic branch is not adopted.
- The focused suites still need an approved Windows/Python 3.11 executor. The available local environment is not that executor.
- Production `AppBootstrap` remains `ReadAuthorizationCoordinator.unconfigured()`; G1/G2/G3 and all eight implementation prerequisites remain open; protected reads remain fail-closed.

### Correct decision trace

```text
LAST_OBSERVED_ACTION=GITHUB_ACTIONS_FOCUSED_CANDIDATE_RUN
OBSERVED_RESULT=STARTUP_FAILURE_ZERO_JOBS
TESTS=NOT_RUN
EXPECTED_TEST_INFORMATION=NOT_PRODUCED
SAME_WORKFLOW_AND_SAME_ACCOUNT_WARNING=NO_NEW_DISCRIMINATING_EVIDENCE
NEXT_ACTION=OWNER_INSPECTS_BILLING_AND_LICENSING_OR_REQUESTS_OFFICIAL_REVIEW
RETRY_GATE=NEW_VERIFIED_EXECUTION_PRECONDITION_REQUIRED
AFTER_GATE_CLEARS=REFRESH_MAIN_AND_PR_HEAD; RUN_THREE_FOCUSED_SUITES_ON_APPROVED_EXECUTOR
SOURCE_ACCEPTANCE=SEPARATE; G1/G2/G3_NOT_ESTABLISHED
```

The immediate route is not “change workflow YAML and try again.” It is to resolve or obtain an explanation for the observed account restriction, without sharing payment details in chat or changing billing merely to test a theory. Only after the execution precondition genuinely changes should the exact candidate and focused test run be revalidated.

This does not imply that the account warning is the only bridge blocker. Even after tests run, production trust/mandate, policy, resolver, platform identity, anti-rollback and independent acceptance remain separate obligations.

## 8. Acceptance test for this method

A later, non-identical task must demonstrate, with correlated evidence, that it:
1. retrieves this rule and the exact relevant terminal receipt;
2. identifies the previous attempt's true result stage and evidence boundary;
3. compares the next action with the prior experiment fingerprint;
4. refuses an unchanged low-information repeat or supplies an observed material delta;
5. identifies the earliest open causal edge and selects an action able to cross or discriminate it;
6. states expected observations and routes each plausible result correctly;
7. updates the owning rule/router only where justified and fetches back the canonical result;
8. changes a later decision because it used the retained evidence, with the consequence independently checked.

Mentioning `UAAL-D019`, repeating its wording or linking to this file is retrieval/documentation—not causal reuse.

## 9. Falsifiers and scope limits

Revise, narrow or revert this rule if a non-identical task demonstrates that fingerprint comparison suppresses a valid retry, incorrectly merges materially different experiments, misses a genuine state change or routes around the true earliest dependency. Preserve the counterexample and former rule; do not rationalize the contradiction.

This is a coordination/design artifact. It does not prove automatic runtime enforcement, model-weight change, consciousness, sentience, universal adaptation or causal learning.

## 9A. Observed application episode — authenticated UI recheck (2026-10-26)

In a subsequent continuity task, the current route was refreshed, the newer run #40408992195 was discovered with `startup_failure` and `jobs=[]`, and an unchanged workflow retry was not selected. After explicit Owner authorization, the next action was a read-only authenticated check of the repository Actions page.

**Observed result:** the account billing-lock warning was still visible; the page listed 175 workflow runs, all reported as failed at startup. No workflow was run and no settings were changed. Evidence: [read-only browser run](https://agent.tinyfish.ai/runs/2fe72c49-0d19-4454-8f5d-0560942ca147), reconciled into [the active route](./CURRENT-STATE.md) and [the billing-lock receipt](./CHAT-ARCH-2026-10-26-M1F-PR531-ACTIONS-BILLING-LOCK-ROUTE.md).

This episode demonstrates that the method was explicitly applied to compare the prior zero-job attempts and select a fresh external-state observation instead of repeating the workflow. However, the Owner also directly instructed that check, so this is **not an isolated causal experiment proving that the saved method alone caused the decision**. It is one observed method-application episode; repeatability, autonomous runtime enforcement and general algorithmic learning remain unproven.

```text
METHOD_APPLICATION=OBSERVED_IN_THIS_SESSION
PRIOR_TERMINAL_OUTCOME=STARTUP_FAILURE_ZERO_JOBS
PROPOSED_UNCHANGED_RETRY=NOT_SELECTED
SELECTED_ACTION=OWNER_AUTHORIZED_READ_ONLY_UI_RECHECK
OBSERVED_DELTA=ACCOUNT_BILLING_LOCK_WARNING_STILL_VISIBLE
RESULT_ROUTE=OWNER_BILLING_AND_LICENSING_REVIEW_OR_OFFICIAL_LOCK_REVIEW
METHOD_CAUSAL_CONTRIBUTION=NOT_ISOLATED_FROM_EXPLICIT_OWNER_INSTRUCTION
AUTONOMOUS_RUNTIME_ENFORCEMENT=NOT_PROVEN
GENERAL_CAUSAL_REUSE=NOT_ESTABLISHED
MODEL_WEIGHT_CHANGE=NOT_CLAIMED
```

## 9B. External-state verification result — billing warning persists (2026-10-26)

The Owner authorized a read-only signed-in browser recheck. The repository Actions page loaded and still showed the exact account billing-lock warning. It listed 175 workflow runs, all in “failed at startup” state. No workflow was launched and no settings were changed. Receipt: [read-only UI inspection](https://agent.tinyfish.ai/runs/2fe72c49-0d19-4454-8f5d-0560942ca147).

A current official documentation check found that GitHub's [locked-account guidance](https://docs.github.com/en/billing/how-tos/troubleshooting/locked-account) says a failed authorization hold related to Copilot or budget changes can also block Actions/free-tier access, even without an active subscription or balance; this remains a possible explanation, not this account's confirmed cause. The documented next route when Billing & Licensing shows no issue is the [GitHub Support portal](https://support.github.com/contact) to request review. The public status page [currently reports all systems operational](https://www.githubstatus.com/); it lists a general incident affecting Actions, Issues, API Requests and Pull Requests from 18:48 to 18:57 UTC on October 26 as resolved. Neither the general incident nor general healthy status explains the observed account-level warning.

```text
LIVE_WARNING_RECHECK=CONFIRMED_READ_ONLY
ACTIONS_UI_RUN=2fe72c49-0d19-4454-8f5d-0560942ca147
ACTIONS_UI_RUNS_LISTED=175; ALL_LISTED=FAILED_AT_STARTUP
GITHUB_STATUS=ALL_SYSTEMS_OPERATIONAL; OCT26_1848_1857UTC_INCIDENT=RESOLVED
OFFICIAL_LOCK_CAUSE=UNKNOWN; FAILED_AUTHORIZATION_HOLD=CANDIDATE_EXPLANATION_ONLY
OWNER_NEXT_ACTION=INSPECT_BILLING_AND_LICENSING; IF_NO_ISSUE_THEN_REQUEST_GITHUB_SUPPORT_REVIEW
UNCHANGED_WORKFLOW_RETRY=NOT_JUSTIFIED
```

The method was explicitly applied in this session to avoid repeating the zero-job workflow and instead verify the changed external precondition. Because the Owner also directly instructed this browser check, the method's exclusive causal contribution is not isolated. Record one observed application, not autonomous learning or general runtime enforcement.

## 9C. Observed coordination failure — task-local blocker was treated as project-wide stop (2026-10-28)

The Owner-provided terminal result for `M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT` was `NOT_RUN; SUPPORTED_ROUTE_NOT_FOUND`. The result correctly closed that inspection route; it did not establish that all project progress was impossible. The Owner then explicitly requested deeper analysis and evolution of the existing memory/continuity algorithms. The coordinator initially repeated the wait conclusion rather than first evaluating this newly authorized process/documentation lane.

This is a directly observed coordination defect in the assistant's response, not evidence of runtime algorithm enforcement or autonomous model learning. The core protocol already said that a blocked route is not a global stop; the failure was incomplete application of that rule and failure to honor the Owner's explicit continuation intent. The corrective change therefore strengthens the owning selection rule in place rather than creating a second orchestrator or memory store.

```text
INCIDENT=OWNER_CONTINUATION_AFTER_TASK_LOCAL_TERMINAL_BLOCKER
TERMINAL_TASK=M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT
TERMINAL_RESULT=NOT_RUN; SUPPORTED_ROUTE_NOT_FOUND
COORDINATOR_MISS=PROJECT_LEVEL_PROGRESS_NOT_RECONSIDERED
OWNER_SCOPE_CHANGE=EVOLVE_EXISTING_CONTINUITY_AND_MEMORY_METHOD
CORRECTION=DUAL_TRACK_SELECTION; ROUTE_LOCALIZATION; OWNER_INTENT_PARSER
G1_REOPENED=FALSE
PRODUCT_IMPLEMENTATION_AUTHORIZED=FALSE
CAUSAL_REUSE=NOT_TESTED
MODEL_WEIGHT_CHANGE=NOT_CLAIMED
```

Acceptance for the correction: on a later non-identical task, the coordinator must (1) preserve the terminal G1 result, (2) extract the Owner's current objective, (3) enumerate authorized independent candidates from canonical memory, (4) continue a qualifying candidate without repeating an already-answered question, and (5) choose an explicit wait only if no admissible useful action remains. That later behavior—not this writeback—will be evidence of causal reuse.

## 10. Required new-chat handoff — route from current state, not stale incident snapshots

A new chat must:

1. Refresh live `main` and read the canonical five front doors in the order defined by the living continuity protocol. `CURRENT-STATE.md` alone owns the active route and permissions.
2. Reconstruct the current objective, fixed Owner decisions, terminal-result fingerprint and exact open causal edge. Treat dates and route labels in historical sections as historical unless current state reactivates them.
3. Partition the objective into a blocked technical lane and any independently authorized lanes. Do not repeat the G1 existing-asset assessment, Entra setup, closed TPM/source scans or the old Actions workflow path without genuinely new evidence and a changed precondition.
4. If the Owner has explicitly asked to continue or improve the method, search the canonical memory/backlog for a useful authorized task independent of the blocked gate and act within scope; do not treat `AUTOMATIC_FOLLOW_ON=FALSE` as cancellation of that current request.
5. If no authorized independent action can make useful progress, enter `WAIT_FOR_EXTERNAL_INPUT` and identify the exact evidence/decision needed. Do not claim that the underlying asset is absent merely because a route was unavailable.
6. After any meaningful outcome, update the owning living rule and the current route/front-door pointers as justified, preserve the terminal incident, and fetch back canonical content. A later non-identical application must establish causal reuse; document existence alone is not learning evidence.

```text
CONCEPT_ID=UAAL-D019
PARENT_CONCEPT_ID=UAAL-D014
REFINES=UAAL-D018
ROOT=UAAL-ROOT-001
STATUS=DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT=NOT_PROVEN
METHOD_UPDATE=DUAL_TRACK_CONTINUATION_AND_OWNER_INTENT_ROUTING; 2026-10-28
CURRENT_ROUTE_AUTHORITY=CURRENT-STATE.md
TASK_ID_POLICY=NEW_TASK_PER_REVISION
COMMIT_PROFILE=GATE_COMMIT
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
CAUSAL_REUSE=NOT_TESTED
ALGORITHM_LEARNED=NOT_PROVEN
MODEL_WEIGHT_CHANGE=NOT_CLAIMED
```
