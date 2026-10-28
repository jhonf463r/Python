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

## 8. Acceptance and falsification

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
