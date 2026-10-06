# CHAT-ARCH-2026-10-06-075 — UAAL-RQ13 PORTABLE-CONTEXT PRECONDITIONING RECONCILIATION

## STATUS

CANONICAL RECONCILIATION / ADVERSARIAL VALIDATION / RUNTIME ROUTING

## OBJECTIVE

Reconcile Sonnet/Claude's independent audit of the RQ13 portable-context blocker and select the minimum runtime intervention needed to make the P0 construction boundary valid.

## CURRENT VERIFIED STATE

- Executable baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`.
- RQ12 clean-baseline MCP → PerceptionSnapshot is closed / baseline-attributable.
- RQ13 target remains `PerceptionSnapshot → pre-governance DecisionContext → existing post-governance reconstruction`.
- A prior Codex RQ13 attempt did not enter `handle_request` because stale portable context could trigger synchronous `build_package()` persistence before P0.
- Sonnet/Claude independently confirmed that stale state is a real blocker, but also found an existing preconditioning mechanism: MCP `portable_context_get(refresh=True)`.
- That preconditioning is not normal headless lifecycle state and may alter an input later consumed by P0/DC_pre/DC_post; therefore it must be treated as an explicit experimental precondition and fingerprinted.

## CRITICAL REFINEMENT

`portable_context_get(refresh=True)` does not accept `task_context`. It builds with `task_context=None`.

However, if the resulting package's `metadata.site_id` and `metadata.active_objective_id` are used to construct the target request's explicit context, the later `current_package(task_context=...)` can potentially return the fresh cached package without `_goal_shifted`.

The exact package identity and active objective must be discovered at runtime and then reused as explicit request state. Do not hardcode an assumed objective identity.

## FIRST OPEN ACTIONABLE EDGE

The remaining question is now:

`existing portable_context_get(refresh=True)`
→ `capture resulting package identity/site/objective + persisted fingerprint`
→ `construct a real conversational request whose explicit goal context matches those values`
→ `verify current_package does not rebuild during build_perception_snapshot`.

This is the minimum discriminating intervention before attempting the full P0 → DC reconstruction observation.

## ACTOR FIT

**CODEX** is capability-fit because the question now requires controlled Windows runtime execution, exact pre/post file fingerprints, process instrumentation, and a single bounded request.

Sonnet/Claude has completed the independent static challenge. Repeating its audit would add little information.

## AUTHORIZATION

A fresh explicit authorization is required for the preconditioning action and the subsequent single `handle_request` observation. The earlier RQ13 authorization must not be assumed to cover `portable_context_get(refresh=True)`.

## METHOD DELTA

Treat portable context as an explicit controlled runtime input:

`precondition → fingerprint → request → verify cache/no rebuild → continue to reconstruction`.

A precondition may mutate persistent state, but that mutation is not the target observation and must be separately recorded.

Do not claim the resulting P0 is 'natural from untouched state'. The correct claim is 'P0 observed under a declared portable-context precondition'.

## NEGATIVE KNOWLEDGE

Do not infer that freshness alone is sufficient; `_goal_shifted` is a second rebuild trigger.
Do not infer that `portable_context_get(refresh=True)` matches the later task context automatically.
Do not infer P0 → DC continuity until object identities are captured in the later reconstruction experiment.
