# CHAT-ARCH-2026-10-06-074 — UAAL-RQ13 PORTABLE-CONTEXT PRECONDITION RECONCILIATION

## STATUS

CANONICAL RECONCILIATION / RUNTIME-INPUT PRECONDITION / ACTOR REROUTING

## OBJECTIVE

Reconcile the Codex RQ13 runtime-preflight block and determine the first actionable edge before attempting `handle_request` again.

## CURRENT STATE

- Executable baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`.
- RQ12 clean baseline MCP → PerceptionSnapshot is closed and attributable.
- RQ13 Phase 1 static audit narrowed the earlier block.
- RQ13 Phase 2 did not enter `handle_request`; no runtime observation or request-process authorization was consumed by execution.
- The fresh RQ13 worktree is not being treated as a reusable clean runtime-state fixture merely because its Git tree is clean.

## CODEX PREFLIGHT RESULT

Codex selected the request:

`What is photosynthesis?`

Static preflight established:

- intent `general.assistance`;
- role `KNOWLEDGE`;
- `_synaptic_task_kind_from_intent(intent) == ''`.

Therefore the request satisfies the known source-level bypass condition for `_parallel_ia_comparison`.

However, the actual `handle_request` was not invoked.

The worktree contains a stale:

`data/evolution/portable_context/latest.json`

with semantic `updated_at_utc = 2026-04-18T16:43:21.614937Z`.

## INDEPENDENT SOURCE RECONCILIATION

Direct baseline read-back confirms:

1. `TaskContextAssembler._build_task_context()` calls `_portable_context_summary(task_context=context)` before returning the TaskContext.
2. `build_perception_snapshot()` calls `_build_task_context()` before it creates and returns P0.
3. `_portable_context_summary()` calls `PortableContextService.current_package()`.
4. `current_package()` defaults to `max_age_seconds=300` and `allow_stale=False`.
5. `_is_fresh()` computes age from `utc_now() - package.updated_at_utc`.
6. When the cached package is stale and `allow_stale=False`, `current_package()` calls `build_package()`.
7. `build_package()` persists archive JSON, archive Markdown, `latest.json`, and `latest.md` through storage writes.

Therefore the reported stale-package condition is not merely a timestamp assumption: the source contract confirms that a sufficiently stale `latest.json` can cause synchronous package reconstruction/persistence during task-context construction, before P0 exists.

## ADJUDICATION

The immediate runtime blocker is:

`stale portable-context runtime input → current_package() → build_package() → persistence before P0`.

This is a genuine precondition/evidence-boundary problem.

It is distinct from:

- `_parallel_ia_comparison` bypass;
- post-governance DecisionContext reconstruction;
- `TaskOutcomeRecorder.record`.

Those later questions remain open, but they cannot be tested until the P0 construction boundary is made experimentally valid.

## FIRST OPEN ACTIONABLE EDGE

The first actionable edge is now:

`portable-context stale state`
→ `safe experiment preconditioning / existing baseline refresh mechanism`
→ `P0 construction without unexpected out-of-scope persistence`.

The question is not whether the package is stale; that is established.

The question is whether the baseline already provides a way to precondition or observe the package so that:

1. the precondition can be established separately from the target request;
2. the preconditioning does not alter production source;
3. the resulting package state is explicitly recorded as an experiment input;
4. the later `handle_request` observation does not confound preconditioning with the reconstruction being measured.

## ACTOR REROUTING

The next actor is **SONNET/CLAUDE — independent adversarial static audit**.

Reason:

- Codex has already established the Windows preflight and identified the environmental blocker.
- ChatGPT independently verified the relevant baseline source semantics.
- The remaining uncertainty is whether the blocker can be legitimately preconditioned using an existing baseline lifecycle path, or whether any such preconditioning would contaminate the experiment.
- Independent source audit provides more information than repeating Codex's preflight.

Do not yet execute another runtime experiment.

## REQUIRED AUDIT

Sonnet/Claude should inspect exact baseline `e46d830...` and determine:

- all existing calls to `PortableContextService.current_package()`, `build_package()`, and any startup/session refresh paths;
- whether any existing startup lifecycle refreshes portable context before request handling;
- whether such refresh is synchronous/asynchronous and whether it persists;
- whether an existing read-only/stale-allowed mode can supply the package without persistence;
- whether there is an existing configuration or state condition that avoids stale rebuild;
- whether a separate preconditioning operation can be used without modifying production source;
- what exact persistent/runtime state must be recorded before and after preconditioning;
- whether preconditioning changes the semantic baseline of RQ13;
- the first safe boundary for later `handle_request` execution.

No runtime execution is authorized by this audit.

## KNOWLEDGE DELTA

A clean Git worktree is insufficient for RQ13 because the portable-context package is itself a live runtime input and may trigger synchronous persistence during P0 construction.

The experiment must therefore separate:

`source-artifact cleanliness`
from
`portable-context runtime-input readiness`.

## NEGATIVE KNOWLEDGE

Do not infer:

- that a package refresh has already occurred;
- that startup automatically refreshes portable context;
- that a stale package can safely be normalized before the experiment;
- that the same request is now executable;
- that P0 or DecisionContext reconstruction has been observed.

## AUTHORIZATION

The previous RQ13 runtime authorization was not exercised because `handle_request` was never entered. Do not assume it authorizes a separate package-preconditioning action.

## TRACEABILITY

Predecessors:

- `CHAT-ARCH-2026-10-06-073-uaal-rq13-sonnet-static-adversarial-reconciliation.md`
- RQ13 Codex bounded-runtime preflight from current collaboration episode.

Independent source verification:

- `IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py`
- `IABV_v1.5/src/iabv_v15/services/evolution/portable_context_service.py`
- baseline `e46d8304167708bed0764d3bf2be8fd6643e8944`.
