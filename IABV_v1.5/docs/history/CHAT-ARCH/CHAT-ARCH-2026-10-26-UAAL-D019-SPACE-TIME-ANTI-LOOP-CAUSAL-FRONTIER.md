# UAAL-D019 — Space-Time Anti-Loop and First-Open Causal Frontier

**Date:** 2026-10-26  
**Root:** `UAAL-ROOT-001`  
**Parent:** `UAAL-D014` — Meta-Method Plasticity / Failure-to-Evolution Loop  
**Refines:** `UAAL-D018` — Execution-to-Evidence Stage Separation / Observability  
**Status:** `DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT_AND_CAUSAL_REUSE_NOT_PROVEN`  
**Observed baseline:** live `main=54c3e45ec497c83e839bdd6971d33fadbd4ec644`  
**Active technical candidate:** PR #531, `OPEN/DRAFT/UNMERGED`, HEAD `bc2baf525a70d66628809360a197f25a069aa328`.

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

## 6. Selection policy

1. Exclude actions lacking authorization or hard prerequisites.
2. Select the earliest open causal dependency blocking the active objective.
3. Among admissible actions, prefer the smallest reversible action that distinguishes live hypotheses, produces attributable evidence and uses the least justified cost.
4. State expected observations, stop condition, and how each likely result changes the route.
5. If no admissible action can reduce uncertainty, enter an explicit wait state and name the missing external input.

A blocked route is not a global stop when an already-authorized independent action exists. Conversely, switching tools, AIs, branches, transports, workflows or prompts does not make a prohibited or causally identical action admissible.

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

## 10. Required new-chat handoff

The next chat should start from live `main` and the canonical front doors, then:

1. Reconstruct only the bridge-relevant state from the current router and linked receipts.
2. Verify whether the account-level Actions billing-lock warning has changed; do not assume an old observation is current.
3. If unchanged, keep validation blocked and do not repeat the same failed zero-job workflow.
4. If the warning or execution precondition has changed, refresh live `main`, PR #531 and exact candidate HEAD before the three focused suites on the approved Windows/Python 3.11 executor.
5. Keep source authority gates G1/G2/G3 open unless their own evidence contracts are independently met.
6. Record the observed stage, evidence delta and one next action. No merge/rebase or protected-read enablement follows automatically.

```text
CONCEPT_ID=UAAL-D019
PARENT_CONCEPT_ID=UAAL-D014
REFINES=UAAL-D018
ROOT=UAAL-ROOT-001
STATUS=DOCUMENTED_METHOD; RUNTIME_ENFORCEMENT=NOT_PROVEN
ACTIVE_ROUTE=OWNER_RESOLVE_OR_GET_EXPLANATION_FOR_VISIBLE_GITHUB_ACTIONS_BILLING_LOCK
TESTS=NOT_RUN
CAUSAL_REUSE=NOT_ESTABLISHED
ALGORITHM_LEARNED=NOT_PROVEN
NEXT_ACTION=CHECK_CURRENT_BILLING_LOCK_STATE_THEN_FOLLOW_CURRENT_STATE_MD
```
