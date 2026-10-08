# CHAT-ARCH-2026-10-08-147 — RQ21.34 GENERIC ACTION TRANSPORT / NO PRE-SELECTION CONSUMER

## PURPOSE

Reconcile RQ21.34 against direct source checks and localize the demand-side semantic gap without overclaiming from a bounded producer census.

## PROVENANCE

- Executable baseline: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- Executable tree: `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`
- Static only; no IABV runtime or tests executed.
- No executable source modified.

## RQ21.34 RESULT

**C — ONLY GENERIC/PREVIEW TRANSPORT EXISTS** within the bounded production census.

Direct source verification confirms:

1. `InferenceRequest.goal_parameters` is a generic dictionary and `ToolAction` is a structured model.
2. The real UI request producer `ControlCenterViewModel._goal_parameters_for_request()` does not populate typed `actions`.
3. `AdaptiveTaskOrchestrator` preserves the received `goal_parameters` into `AdaptiveSession.metadata`.
4. `ToolTeachService.build_task_for_session()` reconstructs an `InferenceRequest` carrying those parameters.
5. `ToolTeachService.build_task_from_request()` calls selection first:
   `_select_mode() → selection/tool_id`.
6. Only after selection does it call `_build_actions()`.
7. `_build_actions()` can consume pre-supplied `goal_parameters.actions`, but that consumption occurs after realization selection.
8. When no actions are supplied, `_build_actions()` may derive actions from reusable patterns or the selected `tool_id`, reinforcing the MIXED classification of `ToolTask.actions`.
9. `orchestrator_preview` accepts arbitrary `goal_parameters`, but terminates at `build_decision_context_preview()`; it does not establish an operative pre-selection action consumer.
10. The bounded production census found no real production caller that was observed constructing typed `goal_parameters.actions` and carrying them into operative selection.

## IMPORTANT EPISTEMIC LIMIT

The result is:

`C = generic/preview transport only in inspected production surfaces`

not:

`C = repository-wide proof that no external caller can ever supply actions`.

Preserve:

`bounded producer census != universal caller absence`.

## R_task ADJUDICATION

`request.goal_parameters.actions` fails as the current `R_task` source because:

- there is no observed production producer on the focal operative path;
- the selector does not consume it;
- the existing consumer occurs after tool selection;
- no transformation maps those actions to required capability identity.

Therefore the channel is **transport-capable but semantically non-operative for current pre-selection eligibility**.

## KNOWLEDGE DELTA

- Generic action transport exists.
- Action transport is not action semantics at the selection boundary.
- `ToolTask.actions` remains MIXED and cannot be used as a universal independent demand oracle.
- Preview acceptance of actions is not operative selection.
- The missing edge is now localized to a **pre-selection demand interpreter / operation-to-capability join**, but before designing one we must verify whether any existing structured operation vocabulary already has an operative consumer elsewhere.

## METHOD DELTA

New reusable rule:

`transport-capable` ≠ `semantically consumed at required boundary`.

For any candidate semantic source, prove:
`produced → transported → consumed at correct causal boundary → semantically scoped → mapped to requirement`.

A post-selection consumer does not satisfy a pre-selection contract merely because the same payload survives into the task.

## ROUTING DELTA

Next actor: **CODEX**.

Capability-fit:
- static source archaeology of existing operation vocabularies and their consumers;
- identify whether an existing pre-selection semantic discriminator/operation vocabulary already reaches operative selection;
- no runtime needed.

Do not route to implementation yet.
Do not route to Sonnet/Claude until a concrete existing semantic discriminator or candidate composition is identified.

## STATUS

- RQ21.28 = CLOSED / D
- RQ21.29 = CLOSED / C
- RQ21.30 = CLOSED / C-GLOBAL / D-ACTIONS-REAL-UI
- RQ21.31 = CLOSED / C
- RQ21.32 = CLOSED / B
- RQ21.33 = CLOSED / PAIR-NOT-AVAILABLE
- RQ21.34 = CLOSED / C-GENERIC-PREVIEW-TRANSPORT
- R_task = OPEN
- CAPABILITY → REALIZATION = BLOCKED
- IMPLEMENTATION = NOT AUTHORIZED
- RUNTIME = NOT AUTHORIZED

## CURRENT FIRST OPEN EDGE

`existing pre-selection operation vocabulary/semantic discriminator → operative consumer → exact R_task`

## NO-GO

- no `required_capability_ids` implementation;
- no ToolCard realization implementation;
- no selector scoring changes;
- no new semantic registry/class;
- no runtime;
- no universal absence claim;
- no architectural solution before existing-vocabulary reuse/composition is checked.
