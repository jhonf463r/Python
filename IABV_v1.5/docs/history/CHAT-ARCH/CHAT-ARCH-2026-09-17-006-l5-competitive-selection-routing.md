# IABV v1.5 — CHAT-ARCH 2026-09-17-006
## L5 Competitive Selection Routing / Devin-First Capability Optimization

## PURPOSE

Preserve the latest independent Sonnet audit and derive the next smallest discriminating action while explicitly optimizing AI intervention cost.

## CURRENT VERIFIED STATE

The L5 evidence artifact is remotely preserved and readable:

- branch: `audit/l5-artifact-evidence-2026-09-17`
- commit: `f3e8a21c58fd73ad1b09ae11abae0cce915138cb`
- file: `IABV_v1.5/tests/test_l5_causal_decision.py`
- Git blob: `2844537f80c190a1351dac3a95f35f80cf79dc19`
- SHA-256: `E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`

The artifact's fresh Windows execution was reported as passing with:

- Windows 11
- Python 3.14.4
- pytest 9.0.3
- `1 passed in 2.72s`
- exit code 0

Historical execution provenance remains not recovered.

## SONNET INDEPENDENT ADJUDICATION

Sonnet independently confirmed:

- artifact identity/provenance is genuine and stable;
- persistence uses production `InteractionLearningService` and SQLite-backed repository;
- reload creates a new repository/DB/storage object graph at repository level;
- learned-pattern scoring changes from `0.0` to `1.0`;
- total score changes from `7.545` to `10.095`;
- the `+2.55` delta is exactly derivable from production scoring terms:
  - learned-pattern contribution `+1.8`;
  - stability contribution `+0.675`;
  - frequency contribution `+0.075`;
- no mocks/monkeypatches/fake persistence were detected in the preserved artifact.

Sonnet also confirmed the material limitations:

- the test directly calls private `_assess_candidate()`;
- the test has only one candidate;
- therefore it demonstrates score-level influence, not a competitive selected-decision change;
- the `VerifiedTransition` is constructed manually and therefore is a synthetic verified input rather than an independently observed world episode;
- the `ToolRegistry` instance is retained across treatment while the selector receives a new repository; Sonnet classified this as a real methodological asymmetry but not material to the measured card/scoring result because learning updates patterns rather than ToolCard counters.

## CURRENT L5 STATUS

`L5 = NOT PROVEN under the strong canonical definition`.

Strong target:

`legitimate verified experience`
→ `persistence`
→ `reload`
→ `normal production selector`
→ `multiple competing candidates`
→ `future selected decision changes`
→ `specific causal attribution`

Current evidence reaches:

`verified experience fixture`
→ `persistence`
→ `reload`
→ `internal selector scoring`
→ `score changes`

## FIRST OPEN CAUSAL EDGE

The first unresolved causal edge is now exactly:

`InteractionModeSelector.select()`
→ `multiple competing candidates`
→ `ranking`
→ `winner changes between control and treatment`
→ `difference attributable only to prior verified experience`

This is narrower than “audit all of L5”.

## DIRECT SOURCE CONFIRMATION

Production `InteractionModeSelector.select()` is real and:

1. refreshes candidate cards through the registry;
2. builds candidate assessments;
3. sorts assessments by `total_score` descending;
4. returns a `ModeSelectionDecision` containing `selected_tool_id` and score metadata.

Existing selector tests already exercise `select()` and use deterministic availability adapters for test isolation. This makes a small competitive-selection experiment feasible without changing production semantics.

`ToolTeachService` also calls `self.mode_selector.select(...)`, confirming that `select()` is part of the production tool-teaching path. This must still be traced by the experiment/report rather than assumed equivalent to every higher-level workflow.

## NEXT ACTOR — CAPABILITY OPTIMIZATION

Next actor: **DEVIN**.

Reasoning:

The remaining work is a small, concrete test addition plus Windows execution. Devin's demonstrated capability covers both:

- local repository/test implementation;
- exact Windows runtime reproduction.

There is no current need for Codex-specific repository archaeology or broader ambiguous implementation.

The capability-routing policy is therefore:

`small bounded implementation + Windows execution`
→ Devin first.

Do NOT consume a Codex intervention merely because Codex historically performed repository archaeology or focused implementation.

If Devin reports a genuine capability/access/implementation blocker that materially requires Codex's strengths, then route to Codex. Otherwise preserve the Codex budget.

## OPUS BUDGET

Three Opus 5 interventions remain reserved.

Do not consume Opus for this routine bounded selector experiment.

Use Opus only if independent evidence produces a genuine architecture-level contradiction or higher-order causal ambiguity that cannot be reduced by the current experiment.

## DEFINED NEXT EXPERIMENT

Create a NEW test. Do not modify or rewrite the preserved artifact.

Use the real production `InteractionModeSelector.select()` path.

Use at least two candidates whose non-learning conditions are controlled.

Desired structure:

CONTROL:

`candidate A score > candidate B score`

`winner = A`

TREATMENT:

same request
same candidate universe
same relevant non-learning state
same availability
same mode constraints

but:

`candidate B has one legitimate persisted/reloaded learned experience`

Then establish:

`candidate B score rises because of learned state`

and, critically:

`winner(control) = A`

`winner(treatment) = B`

The winning change must be attributable specifically to the prior verified experience.

Do not force `selected_tool_id`.
Do not call `_assess_candidate()` directly as the decision test.
Do not call `_best_pattern()` directly as the decision test.
Do not manually inject the final score.
Do not manually inject the winner.
Do not create a replacement architecture.

## IMPORTANT EXPERIMENTAL DESIGN CONDITION

The control/treatment difference should be constructed so that the learning contribution is large enough to cross the decision boundary but no other material variable crosses it.

Because the current scoring code has a `learned_pattern` contribution of `1.8` plus pattern-derived stability/frequency effects, the test should deliberately choose a baseline score gap smaller than the observed learning delta while retaining otherwise equivalent candidate conditions.

First verify mathematically that the selected candidates can produce a winner flip before coding the assertions.

## EXPERIENCE LEGITIMACY BOUNDARY

This experiment may still use the existing verified-transition learning fixture if that is the only minimal way to isolate selector causality.

If so, explicitly state:

`selector decision influence proven conditional on a valid verified-transition learning input`.

Do NOT claim this alone proves a real-world observation/verification → L5 loop.

G3 remains the prior evidence for real verified-transition persistence.

## FALSE-POSITIVE CONTROLS

Must verify absence of:

- direct `_assess_candidate()` as the final decision path;
- one-candidate design;
- forced winner;
- hard-coded score;
- manually injected learned score;
- stale mutable state that changes candidate attributes;
- uncontrolled availability differences;
- differing request text between arms;
- hidden preferred-tool shortcut;
- `consultation_scope=external_assistant` or another preferred-external path that bypasses scoring;
- candidate-specific configuration changes unrelated to learning;
- test-only selector replacement.

## REQUIRED EVIDENCE

Capture:

- branch and full HEAD;
- files modified;
- exact test code path;
- candidate identities;
- control ranking;
- treatment ranking;
- control selected_tool_id;
- treatment selected_tool_id;
- score components for both candidates in both arms;
- learning-state delta;
- persistence/reload evidence;
- exact `InteractionModeSelector.select()` invocation;
- test command;
- OS/Python/pytest;
- stdout/stderr/exit code;
- artifact/test hashes;
- no production-code modifications.

## EPISTEMIC GATE

Even if the new test passes, classify separately:

`STATE_CHANGE`
`SCORE_CHANGE`
`DECISION_CHANGE`
`BEHAVIOR_CHANGE`
`WORLD_OUTCOME_CHANGE`

Do not collapse them.

Strong L5 may be adjudicated only after the independent audit determines that the decision change is genuinely causal and satisfies the chosen definition.

## SYMBIOSIS MEASUREMENT

This episode also updates the AI capability model.

The desired rule is:

`actor capability × access × uncertainty reduction ÷ intervention cost`

not model-name prestige.

Current evidence:

- Sonnet removed the methodological ambiguity and identified the first open decision edge.
- Devin has the demonstrated access needed for the next bounded implementation + Windows runtime task.
- Codex has a saved intervention budget and should only be used if Devin cannot materially execute the required scope.
- Opus 5 has three interventions reserved for real architectural contradictions.

Track:

`ΔK` = new knowledge about causal selection
`Δπ` = method/protocol change
`ΔB` = observable behavior change
`ΔY` = world outcome change

## STOP CONDITIONS

STOP if:

- production code would need to change;
- the experiment requires inventing a new architecture;
- the winner must be hard-coded;
- the two candidates cannot be controlled adequately;
- the normal selector cannot be invoked faithfully;
- the environment blocks faithful reproduction.

In these cases report the first causal blocker and route by capability.

Otherwise stop after:

`new competitive-selection test created`
+
`fresh Windows execution captured`
+
`control/treatment winner comparison captured`
+
`full provenance recorded`

Do not advance to L6.

Do not modify the preserved L5 artifact.

Do not consume Codex unless a genuine blocker requires it.

Do not consume Opus for routine implementation.

END
