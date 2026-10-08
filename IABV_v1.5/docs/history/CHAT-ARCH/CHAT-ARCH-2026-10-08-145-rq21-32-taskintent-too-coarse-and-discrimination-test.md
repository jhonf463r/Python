# CHAT-ARCH-2026-10-08-145 — RQ21.32 TASKINTENT TOO COARSE / DISCRIMINATION TEST

## PURPOSE

Absorb the RQ21.32 Codex result and refine the demand-side capability frontier using the existing semantic surfaces instead of inventing a new task model.

## PROVENANCE

- Documentation main before this writeback: 47572dd23099d00c98a0840f0e21d82eb1596dbf
- Executable baseline: 5b1d89022ee4cdc63c1f88e050f086b40a42875c
- Executable tree: ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61
- RQ21.32 is static/read-only; no executable source changed.

## RQ21.32 ADJUDICATION

**B — an existing structured semantic unit exists but is too coarse.**

`TaskIntent` is an existing semantic normalizer. For `tools.local_workflow` it produces `intent_key='tools.local_workflow'`, role `TOOL_USE`, disposition `PLAN_THEN_EXECUTE`, and a generic summary.

It is consumed upstream by readiness, pack and playbook planning, but the production session→request projection does not carry the structured intent into the selector path.

The selector later reconstructs broad signals from free-form `user_goal`, including `desired_modes` and `task_kind`.

These selector features may affect score, but they are not demonstrated to encode an exact operational demand or a required capability identity.

## SEMANTIC LAYERING

The current system already has multiple semantic resolutions:

1. free-form `user_goal` — rich but unnormalized;
2. `TaskIntent` — structured but coarse;
3. readiness capability IDs — structured but intent/system-level;
4. `desired_modes` — selector heuristic for modality;
5. `task_kind` — selector heuristic/category;
6. `suggested_tool_id` — realization preference;
7. `ToolTask.actions` — partly generated after realization selection.

These are not interchangeable authorities.

## CLOSED EDGE

`user_goal → TaskIntent` is an existing semantic normalization path.

It does not close:

`TaskIntent / selector features → exact operational demand → R_task`.

## INFORMATION LOSS / TRANSFORMATION MAP

- `user_goal`: PRESERVED.
- `TaskIntent`: TRANSFORMED from free-form input into broad intent classification.
- `TaskIntent.intent_key` for tools.local_workflow: TOO COARSE for operation discrimination.
- `CapabilityReadiness`: TRANSFORMED from intent into broad readiness IDs; not task-operation demand.
- `desired_modes`: HEURISTIC modality interpretation.
- `task_kind`: HEURISTIC category used in selector scoring.
- `suggested_tool_id`: HEURISTIC realization preference.
- `ToolTask.actions`: RECONSTRUCTED after tool selection.

## IMPORTANT INVARIANTS

- `TaskIntent ≠ exact task semantic unit`.
- `intent_key ≠ operation identity`.
- `desired_modes ≠ operational demand`.
- `task_kind ≠ required capability ID`.
- `suggested_tool_id ≠ R_task`.
- a selector feature can change ranking without being a capability contract.
- semantic normalization ≠ capability derivation.
- structured ≠ sufficiently discriminating.

## CURRENT FIRST OPEN EDGE

`TaskIntent / desired_modes / task_kind → discriminating operational representation independent of realization → exact R_task`

## NEXT EXPERIMENT

RQ21.33 should perform one static pairwise discrimination test using two source-grounded messages that both classify as `tools.local_workflow` but represent materially different requested operations.

For each message, trace:

`user_goal → TaskIntent → readiness → desired_modes → task_kind → suggested_tool_id → selector inputs`

Then compare whether any pre-selection value:

1. differs reliably between the two messages;
2. is caused by operation semantics rather than lexical coincidence;
3. remains independent of selected realization;
4. has an existing consumer capable of becoming an authoritative demand signal.

Do not require the pair to prove R_task by itself. The immediate purpose is to measure **discriminating information already present in existing semantic surfaces**.

## METHOD DELTA

The protocol now distinguishes two questions that were previously too close:

A. Does a structured semantic object exist?
B. Is that object sufficiently discriminating to represent the operational task?

Both must be answered before the object is treated as a candidate task contract.

A future prompt must therefore include a **discrimination test** whenever a candidate semantic object is proposed as a task boundary.

## ROUTING DELTA

Next actor: **CODEX**.

Reason:
- current uncertainty is still source-level causal/semantic discrimination;
- the next intervention is a bounded static A/B over existing representations;
- no runtime is needed;
- no implementation is justified;
- Sonnet/Claude becomes useful after the pairwise source evidence exists, to challenge whether the observed discriminator is genuinely semantic rather than lexical/heuristic.

## CUMULATIVE METHOD RULE

Do not ask whether a structure exists and stop.

Always progress:

`exists → operative → semantically scoped → discriminating → realization-independent → capability-bearing`.

Only the final state can justify treating an object as `R_task` source.

## STATUS

RQ21.28 = CLOSED / D
RQ21.29 = CLOSED / C
RQ21.30 = CLOSED / C-GLOBAL-D-ACTIONS-REAL-UI
RQ21.31 = CLOSED / C
RQ21.32 = CLOSED / B
CAPABILITY → REALIZATION = BLOCKED
CURRENT OPEN = DISCRIMINATING OPERATIONAL SEMANTICS → R_task
IMPLEMENTATION = NOT AUTHORIZED
RUNTIME = NOT AUTHORIZED
NEXT = RQ21.33 / CODEX

## NO-GO

- no new task semantic class;
- no required_capability_ids implementation;
- no realization declaration implementation;
- no selector scoring change;
- no runtime;
- no RQ21.27C repetition;
- no broad re-archaeology.