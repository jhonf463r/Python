# CHAT-ARCH 2026-10-08-155 — RQ21.41 SOURCE RECONCILIATION / BOUNDED EXTENSION

## 1. Provenance

Actor: CODEX.
Inspected source baseline:
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- TREE: `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`
- worktree reported dirty under `data/evolution/control_master/rules/`;
- source claims derived from pinned commit;
- no runtime, tests, or modifications.

RQ21.40 semantic result remains PASS WITH ONE LOCAL REPAIR.

## 2. Source reconciliation result

Adjudication:
**C — existing organs are reusable but the semantic bridge requires a bounded extension.**

Strongest existing chain:
`IntentUnderstandingService → TaskIntent → CapabilityReadinessService._required_capabilities() → CapabilityReadiness → StrategyPackRegistry`

This chain is useful but is not exact R_task:
- TaskIntent preserves broad intent/ambiguity metadata;
- `_required_capabilities()` maps `intent_key` to fixed readiness IDs;
- StrategyPack consumes those readiness IDs;
- no exact operation-level result/success-predicate/envelope/demand-state contract reaches ToolCard selection.

## 3. Existing vocabulary adjudication

### Capability identity
`CapabilityReadiness.capability_id` can be reused as candidate capability IDs where semantically appropriate, but it must not be declared universal solely because it exists.

`ToolCapability`, `CapabilityReadiness.capability_id`, `EnvironmentCapability.capability_id`, and `ToolCard.capabilities` are distinct vocabularies with only partial conceptual overlap in the baseline.

`CapabilityDescriptor` exists structurally but no operative producer/consumer was demonstrated in the inspected Python source. It cannot be promoted to an operative bridge.

### Readiness/evidence
`CapabilityReadiness` is reusable infrastructure for readiness/evidence state, but readiness must remain distinct from demand identity.

### Realization declaration
`ToolCard.capabilities` is heterogeneous and realization-facing. It cannot be promoted as authoritative abstract capability realization declaration without a semantic repair.

### Selection
`InteractionModeSelector` and `ToolRegistry.pick_card_for_task()` are existing operative selection organs, but neither currently consumes a first-class abstract capability requirement as a hard eligibility gate.

## 4. Unknown-demand mismatch

Current `_required_capabilities()` falls back unknown `intent_key` values to `assistant.local.chat`, while the repaired semantic contract requires UNKNOWN to remain epistemically distinct from a known generic capability requirement.

Therefore the current fallback cannot be preserved as the semantic meaning of UNKNOWN.

This is a routing/contract mismatch, not a runtime proof.

## 5. Candidate-set independence

`_required_capabilities()` itself does not receive the candidate set, selected tool, suggested tool, assistant kind or ranking. For the bounded path inspected, its returned IDs are candidate-independent.

However, readiness evaluation for some local-tool capabilities inspects available ToolCards. This changes readiness evidence/status, not the task requirement ID list.

Therefore candidate-set leakage is not the current primary demand-side defect.

## 6. Exact first open edge

`semantic task demand + demand_state + bounded envelope → stable required-capability identity → realization capability declaration → hard capability eligibility at existing selection boundary`.

This is the first implementation-contract edge.

## 7. Reuse-first adjudication

| Layer | Result |
| --- | --- |
| Demand | EXTEND |
| Capability identity | REUSE, bounded by semantic validation |
| Readiness/evidence | REUSE |
| Realization declaration | EXTEND |
| Selection boundary | EXTEND / WIRE-REPAIR |

Do not create a second readiness subsystem.
Do not create a new universal registry unless source evidence later proves existing composition impossible.

## 8. Minimum implementation contract still required

Before any implementation prompt, freeze a narrow code-facing contract that answers:

1. What exact field carries `R_task` and its demand_state across the pre-selection path?
2. Which existing capability ID vocabulary is authoritative for this first implementation slice?
3. How does a ToolCard declare realization of those IDs without conflating them with current heterogeneous action labels?
4. Where is the hard eligibility filter applied before preference, Synaptic routing, explicit tool choice and lexical fallback can bypass it?
5. What happens when demand_state = UNKNOWN / AMBIGUOUS / EMPTY_CAPABILITY_DEMAND?
6. What is preserved as readiness evidence versus capability identity?
7. How is the empty eligible set propagated without fallback resurrection?

Implementation remains blocked until this contract is written and independently challenged.

## 9. FACT / INFERENCE / DESIGN JUDGMENT / UNPROVEN

FACT:
- CODEX found no current first-class task-level R_task field in the inspected baseline;
- current readiness mapping is intent-key driven;
- current ToolCard capability labels are heterogeneous realization-facing strings;
- current selector/registry paths lack a proven abstract capability hard gate;
- CapabilityReadiness is existing readiness/evidence infrastructure;
- unknown intent currently falls back to `assistant.local.chat`.

INFERENCE:
- a bounded semantic bridge can likely compose existing TaskIntent/readiness/selector organs;
- a new parallel capability subsystem would violate reuse-first without further proof.

DESIGN JUDGMENT:
- freeze the code-facing contract before choosing field names or modifying models.

UNPROVEN:
- exact minimal field placement;
- whether an existing dormant model such as CapabilityDescriptor can be activated instead of extending ToolCard/ToolTask;
- exact hard-gate insertion point across all selection/override/fallback routes;
- runtime behavior of the repaired contract.

## 10. Symbiosis / Method Delta

Knowledge Delta:
source reconciliation converted the abstract semantic problem into a bounded engineering seam.

Method Delta:
once semantics stabilize, reconcile every conceptual term against real producer/consumer positions before naming fields or authorizing implementation.

Routing Delta:
next actor is ChatGPT/coordinator to formulate the minimum code-facing contract. Then use Sonnet/Claude for one source-aware adversarial challenge of that contract before Codex implementation.

## 11. Implementation status

**DO NOT IMPLEMENT.**