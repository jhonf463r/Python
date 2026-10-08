# CHAT-ARCH-2026-10-08-143 — RQ21.30 CALLER PROVENANCE / CUMULATIVE ROUTING METHOD

## PURPOSE

Absorb the RQ21.30 Codex result and strengthen the cross-chat continuity protocol so every material actor result changes the canonical graph, routing decision and next prompt construction.

## PROVENANCE

- Documentation main before this writeback: 87b241a5508777011705c25a8ce8a90e325955f0.
- Executable source baseline remains 5b1d89022ee4cdc63c1f88e050f086b40a42875c, tree ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61.
- RQ21.30 is a static source audit; no executable source changed.

## RQ21.30 ADJUDICATION

Global classification: C — mixed semantic/tool-specific input.

For the actual UI callers examined, goal_parameters.actions is D: the UI does not create typed actions before selection.

Direct facts:
- ControlCenterViewModel._build_request() places the user message into InferenceRequest.user_goal and builds goal parameters from role/site/context; it does not create goal_parameters.actions.
- IntentUnderstandingService classifies tools.local_workflow and tools.sandbox from text/role.
- system.metacognition can produce requires_mcp_tools in TaskIntent.metadata.
- AdaptiveSession → ToolOperationalExecutor → build_task_for_session() copies objective/role/parameters/site but loses intent_key and intent.metadata.
- InteractionModeSelector consumes user_goal and context for selection but has no action→capability transformation.
- _build_actions() validates explicit actions when present and can generate tool-specific actions after tool_id is fixed.

## IMPORTANT REFINEMENT

The prior statement 'pre-selection actions can exist' must be narrowed:

- generic callers/requests may be capable of carrying goal_parameters.actions before selection;
- the three real UI callers traced in RQ21.30 do not produce that typed action representation;
- therefore the operative product path currently depends primarily on user_goal/intent semantics before selection, not on a stable typed operation contract;
- no pre-selection operation→abstract-capability transformation was found.

This is a stronger localization than RQ21.29, not a contradiction.

## CAUSAL GRAPH

Current observed normal UI path:

user message
→ InferenceRequest.user_goal
→ intent classification
→ session/readiness/pack/playbook
→ build_task_for_session projection
→ suggested tool / selector / overrides
→ final tool_id
→ tool-specific action construction
→ ToolTask
→ downstream re-resolution
→ adapter

The capability demand edge is absent between pre-selection task semantics and realization eligibility.

## LOSS MAP

1. user_goal survives into selection, but remains free-form semantic text.
2. TaskIntent.intent_key exists upstream but is not transported into the reconstructed InferenceRequest.
3. TaskIntent.metadata, including requires_mcp_tools, can be lost at session→request projection.
4. goal_parameters.actions is not produced by the focal UI callers.
5. tool-specific actions are reconstructed after tool selection.
6. no abstract required-capability identity reaches the eligibility boundary.

## NEW HARD INVARIANTS

- caller text ≠ typed operation contract
- typed operation availability in a model ≠ typed operation production by the real caller
- metadata producer ≠ metadata transport ≠ metadata consumer
- intent classification ≠ requirement derivation
- pre-selection semantic signal ≠ abstract R_task unless an operative transform consumes it
- downstream generated action ≠ independent demand oracle
- existence of a field in a generic request model ≠ existence of that field in the production caller path

## METHOD DELTA — CUMULATIVE CONTINUITY PROTOCOL

Every material actor response must now be processed in this order before generating the next prompt:

1. RECEIPT — preserve the actor, task ID, provenance and exact result.
2. RECONCILE — compare result against current canonical source and prior hypothesis.
3. ADJUDICATE — classify FACT / INFERENCE / ASSUMPTION / UNPROVEN and close only what is actually closed.
4. DELTA — record Knowledge Delta, Method Delta and Routing Delta.
5. PROMOTE — write the durable delta into CURRENT-STATE, SYMBIOSIS-MAP, UNRESOLVED-KNOWLEDGE, CONTEXT-INDEX and archive registry when material.
6. ROUTE — state explicitly the next actor, required capability and why that actor is the capability-fit choice.
7. PROMPT — construct the next request from the newly reconciled open edge, not from the previous prompt.
8. VERIFY — after the next actor responds, repeat the cycle.

Thus:

actor result → canonical writeback → new first-open edge → actor selection → next prompt

not:

actor result → immediate next prompt → documentation later.

## ROUTING DELTA

Next actor remains CODEX.

Reason:
- the remaining uncertainty is exact source/call-site provenance and semantic transport;
- the needed intervention is read-only static tracing;
- runtime is unnecessary;
- Sonnet/Claude is not yet the highest information-gain actor because the immediate question is still source-order/producer provenance rather than adversarial interpretation.

## NEXT EDGE

One concrete real caller must now be traced from the user objective through intent/session/request projection to the first selection consumer.

Preferred narrowing:
- start with tools.local_workflow because it is representative of the local execution route;
- then use sandbox/metacognition only if the first trace reveals a reusable branch or ambiguity that changes the contract.

This replaces the prior requirement to trace all three callers in parallel unless the first trace leaves unresolved branch semantics.

## INFORMATION-GAIN REASON

The three-caller batch produced the strongest immediate discriminator already: the actual UI path does not create typed pre-selection actions.

Therefore a second three-caller archaeology pass would have diminishing information gain.

The next single-caller trace now tests whether user_goal + intent classification already form a stable task semantic unit or whether another existing pre-selection structure carries the missing operation semantics.

## CURRENT STATUS

RQ21.28 = CLOSED / D
RQ21.29 = CLOSED / C
RQ21.30 = CLOSED / C globally, D for goal_parameters.actions in the real UI callers
CAPABILITY → REALIZATION = BLOCKED
DEMAND-SIDE R_task CONTRACT = OPEN
RUNTIME = NOT AUTHORIZED
IMPLEMENTATION = NOT AUTHORIZED
NEXT = RQ21.31 SINGLE-CALLER TASK-SEMANTICS TRACE

## NO-GO

- no required_capability_ids implementation yet;
- no ToolCard realization declaration implementation yet;
- no selector scoring changes;
- no new capability registry/manager;
- no runtime;
- no repeat of RQ21.27C;
- no parallel broad re-archaeology after the focused caller trace has already established the relevant branch.