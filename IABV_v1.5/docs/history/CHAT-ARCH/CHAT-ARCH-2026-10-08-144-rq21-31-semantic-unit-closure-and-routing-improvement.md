# CHAT-ARCH-2026-10-08-144 — RQ21.31 SEMANTIC-UNIT CLOSURE / ROUTING IMPROVEMENT

## PURPOSE

Absorb the RQ21.31 Codex result, narrow the capability-demand frontier, and improve the cumulative cross-chat routing protocol.

## PROVENANCE

- Documentation main before this writeback: 1345b9dba1f885fc4e0725691c21d0de09fcec4f
- Executable baseline: 5b1d89022ee4cdc63c1f88e050f086b40a42875c
- Executable tree: ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61
- RQ21.31 is static/read-only; no executable source changed.

## RQ21.31 ADJUDICATION

**C — semantic unit exists only as free-form text / heuristic interpretation.**

The real tools.local_workflow UI path:
- preserves the original user message in InferenceRequest.user_goal;
- does not create typed goal_parameters.actions;
- classifies the intent broadly as tools.local_workflow;
- produces generic readiness/pack/playbook semantics;
- projects the session back into InferenceRequest without intent_key or intent metadata;
- selects the realization using text-derived heuristics/selector signals;
- generates tool-specific ToolTask.actions only after tool_id is fixed.

Therefore no stable structured pre-selection task unit with exact R_task authority exists on this path.

## CAUSAL CHAIN

user message
→ user_goal
→ broad intent classification
→ session/readiness/pack/playbook
→ session→request projection
→ suggested tool / selector / overrides
→ tool_id
→ tool-specific actions
→ ToolTask
→ downstream resolution
→ adapter

The missing edge remains between pre-selection semantic intent and exact demand-side capability identity.

## FIRST OPEN EDGE

user_goal / heuristic intent representation → stable structured task semantic unit → exact R_task

## HARD INVARIANTS REINFORCED

- free-form semantic text ≠ normalized operational task contract
- intent label ≠ operation identity
- broad task role ≠ exact operational capability requirement
- readiness-by-intent ≠ per-task demand
- model supports typed actions ≠ real caller produces typed actions
- generated post-selection actions ≠ pre-selection demand oracle
- metadata producer ≠ metadata transport ≠ metadata consumer
- heuristic selector signal ≠ hard capability eligibility

## KNOWLEDGE DELTA

1. RQ21.28: exact existing ToolTask R_task contract absent (D).
2. RQ21.29: pre-selection operation semantics can exist in generic requests, but no operative operation→capability transform found (C).
3. RQ21.30: actual UI callers do not provide typed actions; user_goal remains the main pre-selection semantic signal.
4. RQ21.31: on the actual tools.local_workflow path, no stable structured semantic task unit exists before realization selection.
5. The missing contract is therefore not merely capability translation; it begins one level earlier at task-semantic normalization.

## METHOD DELTA

Before asking for an operation→capability transform, establish that the production caller has a normalized operation/task semantic unit to transform.

New mandatory order:

caller semantics
→ semantic normalization
→ required capability derivation
→ hard eligibility
→ scoring
→ realization
→ tool-specific action generation

Do not invert this order.

## ROUTING DELTA

The previous three-caller batch is complete.

Next actor remains **CODEX**, but the task is narrower than RQ21.31.

Reason:
- uncertainty is still source-level causal semantics;
- the relevant question is whether an EXISTING semantic normalizer already operates on user_goal before selector choice;
- no runtime is needed;
- Sonnet/Claude is not yet the highest-information actor because we first need to identify the actual existing transformation, if any.

## CURRENT NEXT EXPERIMENT

RQ21.32 — trace the first concrete text-derived semantic feature consumed by InteractionModeSelector for tools.local_workflow.

Determine whether existing code already computes an operationally meaningful representation such as task kind, mode, objective operation, action intent, or another structured discriminator before ToolCard selection.

Do not invent a field. Locate the actual producer and consumer.

## CUMULATIVE ROUTING PROTOCOL IMPROVEMENT

A next prompt must explicitly contain:
- ACTOR
- ROUTING REASON
- CURRENT CANONICAL PROVENANCE
- CLOSED EDGES
- FIRST OPEN EDGE
- WHY THIS EXPERIMENT HAS HIGHER INFORMATION GAIN THAN ALTERNATIVES
- NO-GO CONDITIONS
- EXPECTED OUTPUT / ADJUDICATION

A result is not considered integrated until it has:
RECEIPT → RECONCILIATION → ADJUDICATION → Knowledge/Method/Routing Delta → WRITEBACK → ROUTING → NEXT PROMPT.

## STATUS

RQ21.28 = CLOSED / D
RQ21.29 = CLOSED / C
RQ21.30 = CLOSED / C-GLOBAL, D-ACTIONS-REAL-UI
RQ21.31 = CLOSED / C
CAPABILITY → REALIZATION = BLOCKED
CURRENT OPEN EDGE = TASK-SEMANTIC NORMALIZATION → R_task
IMPLEMENTATION = NOT AUTHORIZED
RUNTIME = NOT AUTHORIZED
NEXT = RQ21.32 / CODEX

## NO-GO

- no required_capability_ids implementation
- no ToolCard realization field implementation
- no selector score changes
- no runtime
- no new capability registry
- no broad repository re-archaeology
- no repeat of earlier three-caller trace
- no RQ21.27C repetition
