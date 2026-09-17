# IABV v1.5 — CHAT-ARCH 2026-09-17-008
## L5 Competitive Selection — Hidden Candidate Confound / Devin Next Route

## PURPOSE

Preserve the independent Sonnet/Claude forensic result after Devin's competitive-selection experiment and update the active causal frontier without repeating already closed evidence.

## CURRENT EXPERIMENT

Branch:
`experiment/l5-competitive-selection-2026-09-17`

HEAD:
`d77cbc6015a8358c9005d475c9799efc9791f8f6`

Test:
`IABV_v1.5/tests/test_l5_competitive_selection.py`

Test SHA-256:
`FC516313BF125F0D52FEF3DB8B9762108DE6DE0E3471301C218A79072D3705EC`

## INDEPENDENT AUDIT RESULT

Sonnet/Claude independently verified:

- the experiment reaches the real `InteractionModeSelector.select()` path;
- the decision is produced by candidate enumeration → `_assess_candidate()` → sort by `total_score` → `ModeSelectionDecision.selected_tool_id`;
- control selects `candidate_a` and treatment selects `candidate_b`;
- persistence and repository reload are real;
- there is no forced winner, manual score injection, selector mock or preferred-external shortcut;
- the `VerifiedTransition` is a manually constructed synthetic learning input, not a real world episode executed/observed/verified by this experiment.

## CRITICAL METHODOLOGICAL FINDING

The test author intended a two-candidate universe, but `ToolRegistry.__init__()` unconditionally calls `_seed_defaults()` and seeds many additional `ToolCard` records.

The actual selector universe contained approximately 21 candidates, including `aider_coder`, which shares `adapter_key='aider'` and `ToolType.CODE_EDITOR` with the named A/B candidates.

Independent ranking reconstruction showed:

CONTROL:
`candidate_a = 9.620` winner
`candidate_b = 8.345`
`aider_coder = 8.225`

TREATMENT:
`candidate_b = 10.895` winner
`candidate_a = 9.620`
`aider_coder = 8.225`

The hidden candidates did not change the observed winner in this exact run, but they invalidate the experiment's stated two-candidate isolation. Therefore the competitive-selection result is methodologically incomplete rather than fully controlled.

## CAUSAL SCORE FINDING

The persisted pattern changes more than the direct `learned_pattern` term.

The learning-induced score delta is produced by the aggregate pattern-derived state, including:

- learned_pattern contribution: +1.8;
- pattern-derived stability contribution: +0.675;
- pattern-derived frequency contribution: +0.075;
- total observed delta: +2.55.

Therefore causal attribution must be stated as the persisted/reloaded learning state or aggregate pattern-derived score effect unless an experiment isolates one term.

## CURRENT EPISTEMIC STATUS

The new experiment materially advances beyond the previous score-only artifact because it demonstrates:

`persisted verified-transition learning input`
→ `fresh repository/registry/selector`
→ `normal InteractionModeSelector.select()`
→ `competitive ranking`
→ `winner change`

But the experiment does not yet satisfy the strongest controlled L5 gate because its candidate universe was not isolated as declared.

The experience-origin boundary also remains:

`synthetic VerifiedTransition fixture != independently observed real-world experience`

Therefore do not promote full strong L5 solely from this experiment.

## NEGATIVE KNOWLEDGE UPDATE

New invariants:

- `visible candidate pair != actual selector candidate universe`;
- `passing winner-flip != fully controlled competitive experiment`;
- `allowed_tool_ids` can be used as a native selector-level control boundary when the experiment requires an isolated candidate universe;
- `aggregate learned-state effect != learned_pattern term alone`;
- `synthetic verification fields != real observation evidence`.

Existing negative knowledge remains active:

- `score difference != decision difference`;
- `persistence != learning`;
- `decision change != behavior change`;
- `behavior change != world outcome`;
- `test pass != causal proof`;
- `report != artifact != commit != execution`;
- `fresh reproduction != historical execution proof`.

## FIRST OPEN EDGE

The immediate unresolved edge is methodological isolation:

`normal select()`
→ `only A/B admitted to the candidate set`
→ `winner flip persists`
→ `winner change remains attributable to persisted/reloaded learning state`

The real-world legitimacy edge remains separate and later:

`real observed action → independent verification → learning input`

Do not merge these two experiments.

## NEXT ACTOR

**DEVIN**

Reason:

- the next action is a bounded test-only change plus Windows execution;
- `InteractionModeSelector.select()` already supports `allowed_tool_ids` natively;
- the smallest discriminating experiment is to repeat the winner-flip with `allowed_tool_ids=['candidate_a', 'candidate_b']` in both control and treatment;
- Devin already has the exact Windows/runtime capability required;
- Codex has no demonstrated capability gap for this specific action;
- Opus remains reserved for architectural contradictions or higher-order causal ambiguity.

## CODEX ECONOMY / SYMBIOSIS LESSON

Do not use Codex merely because it can implement the same local test.

The current capability evidence supports a capability-cost rule:

`required capability × access × expected uncertainty reduction ÷ intervention cost`

For this edge, Devin can execute the required work directly. Codex should remain unused unless Devin encounters a real implementation/access blocker that materially exceeds the bounded local scope.

This is itself a symbiosis experiment: a stronger default routing to Devin reduces avoidable Codex interventions while preserving independent Sonnet verification.

## OPUS BUDGET

Three Opus 5 interventions remain reserved.

Do not consume Opus for this bounded selector-isolation experiment.

Use Opus only if the next evidence reveals a genuine architectural contradiction or higher-order causal ambiguity that cannot be reduced by a local discriminating experiment.

## REQUIRED NEXT EXPERIMENT

Create a new test variant or new test file. Do not modify the preserved L5 evidence artifact.

Use:

`InteractionModeSelector.select(..., allowed_tool_ids=['candidate_a', 'candidate_b'])`

in BOTH control and treatment.

Keep:

- same request;
- same candidate definitions;
- same adapter availability;
- same relevant non-learning state;
- treatment learning through `InteractionLearningService.learn_from_verified_transition()`;
- fresh treatment repository/registry/selector;
- normal `select()` decision boundary.

Capture:

- exact candidate universe after filtering;
- control A/B scores and winner;
- treatment A/B scores and winner;
- learned-state values affecting B;
- persistence/reload evidence;
- exact Windows command/environment;
- artifact hash;
- git HEAD/status.

Do not execute world behavior.
Do not modify production scoring.
Do not change the preserved evidence artifact.
Do not hard-code the winner.

## EXPECTED INTERPRETATION

If the isolated A/B experiment reproduces:

`control winner = A`
` treatment winner = B`

and the difference remains causally attributable to persisted/reloaded learning state, then the selector decision boundary is much stronger and the next question should be the legitimate experience-origin edge, followed only later by L6 behavioral/world effect.

If isolation fails, stop and report the first causal/methodological blocker; do not escalate to Codex or Opus automatically.

## CURRENT ROUTING

`ChatGPT → Sonnet/Claude independent audit → Devin minimal correction/experiment → Sonnet re-audit → ChatGPT adjudication`

Codex remains reserve-only for a genuine scope/capability blocker.

Opus remains reserve-only for genuine architecture-level contradiction or higher-order causal ambiguity.

END
