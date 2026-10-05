# CHAT-ARCH-2026-10-05-055 — SELF-CODE CANDIDATE DIFF / RECONCILIATION

**STATUS:** CANONICAL ROUTING DELTA
**SCOPE:** first IABV self-code development inflection

## OBJECTIVE
Close only the first open edge identified for UAAL-D016:

`verified improvement proposal → materialized isolated code candidate`

Do not assume this closes testing, improvement, independent verification or promotion.

## CURRENT CANONICAL MAIN
`91c4d9caab9d885a947c1b4c8d9637b498c11ac8`

The local checkout reported by Codex is not authoritative.

## CODEX FINDING — RECONCILED

Existing substrate is sufficient to express the upstream side:
`detection → proposal → structured recommendation → validation/decision → CodexTaskSpec`.

The examined flow does not currently demonstrate:
`baseline SHA → isolated code checkout/worktree → patch applied → candidate diff → candidate provenance`.

The existing `SandboxExperimentService` is a route/configuration validation sandbox, not a Git code-evolution sandbox.

`PromotionPrPublisher` is a documentation/evidence publisher, not a production-code promotion mechanism.

Therefore:

`ToolEvolutionProposal != code patch`
`CodexTaskSpec != code execution`
`ToolSandbox != Git isolation`
`promotion decision != code incorporation`

## FIRST OPEN EDGE
`verified improvement proposal → isolated executable candidate diff`

## MINIMUM IMPLEMENTATION SEAM

Extend the existing sandbox boundary with one narrow code-candidate operation that receives:
- structured change proposal;
- exact baseline SHA;
- bounded writable file scope;
- candidate-generation/apply input;
- provenance identifier.

It must return at minimum:
`candidate_id + baseline_SHA + candidate_SHA_or_diff_identity + candidate_diff + scope + execution_result + provenance`.

It must not mutate the baseline or `main`.

Use an isolated worktree/copy or equivalent repository isolation already supported by the project. Do not reuse a checkout-switching publisher path that can alter the active baseline.

## NEXT DEVELOPMENTAL CHAIN

After this edge is proven:

`candidate diff → reproducible baseline/candidate validation → objective-level behavioral comparison → independent verification → governed promotion/rejection/rollback → reusable capability/method delta → later contextual reuse`

These remain OPEN and must be attacked one at a time.

## ROUTING DECISION

**Next actor: CODEX**

Reason:
required capability = implementation + repository archaeology + Git isolation + focused regression.

No Sonnet/Claude yet. No Devin unless the implementation requires a concrete Windows/runtime capability Codex cannot exercise.

## RESTRAINT

Do not build a new evolution engine, brain, backlog, sandbox subsystem or generic patch manager. Reuse the existing evolution/self-teach/sandbox/governance composition.

## SUCCESS CONDITION FOR THIS STEP

A real bounded experiment can produce:

`known baseline → isolated candidate → concrete diff → provenance`

while leaving the baseline untouched.

This proves only candidate materialization, not that the candidate is better.
