# CHAT-ARCH-2026-10-07-138 — CLAUDE EMPTY-SET DESIGN CLOSURE RECONCILIATION

## PROVENANCE

Input: Sonnet/Claude independent audit result received 2026-10-07 13:34 local.
Executable baseline: 07ebffc8f866fc99a3f78091dcd1edd456a0da00
Tree: f0e1294982479426b140eab21f16f2f839504413
Current documentation main before this writeback: 88b26679c61d74b626c4473e192ea5a9faaa1815.

## RECONCILED RESULT

Claude closes the first-open conceptual edge:
capability-eligible realization set = ∅ → explicit NO_ELIGIBLE_REALIZATION outcome → governed defer/fail-closed → no fallback resurrection.

Existing domain state ToolTaskStatus.DEFERRED is confirmed reusable, but it was previously only defined; its propagation through the capability-aware selection path remains an implementation wiring task.

Required local contract extensions/wiring are now sufficiently specified for implementation review:
- typed selector outcome for NO_ELIGIBLE_REALIZATION;
- ToolTeachService propagation that prevents suggested/Synaptic/preference resurrection;
- conditional ToolRegistry enforcement for constrained tasks;
- ToolOperationalExecutor/preflight recognition of capability-empty as deferred rather than adapter_missing;
- no adapter invocation for deferred capability-empty tasks.

## IMPORTANT CORRECTION TO CLAUDE'S RESPONSE

Claude's section 6 proposes storing/using eligible_tool_ids on ToolTask. This contradicts the already reconciled 136 invariant:
candidate eligibility is selection-context state, not durable Task truth.

Therefore implementation must NOT add durable ToolTask.eligible_tool_ids solely for this purpose.

Use one of the following only:
- recompute eligibility from required_capability_ids + current inventory at each constrained resolution; or
- pass an ephemeral candidate set as an internal selection/resolution argument and record it in structured trace.

Do not persist an eligibility set as if it were an invariant of the task.

## REMAINING DEPENDENCIES

Two questions remain real but are not the current first-open edge:
1. Mapping session-level capability_readiness to the subset of capabilities belonging to each ToolTask.
2. Circularity risk for tools.local.* where readiness may derive from the ToolCard inventory.

Implementation must not silently invent semantics for either. If the selected task has no well-defined requirement subset, the implementation should preserve the unresolved boundary rather than fabricate a mapping.

## CURRENT CLASSIFICATION

STATIC / INDEPENDENTLY VERIFIED / EMPTY-SET CONTRACT CLOSED / IMPLEMENTATION REVIEW READY

Construction remains:
REUSE + COMPOSE + WIRE/REPAIR + NARROW EXTEND

No new registry, manager, routing brain or universal capability organ is justified.

## CURRENT FIRST OPEN IMPLEMENTATION EDGE

Exact minimal implementation diff that realizes the closed contract without introducing durable eligible_tool_ids task state.

Next actor: CODEX.
Capability: exact call-site implementation review and minimal diff design.
No source changes, tests or runtime until fresh human implementation authorization.
