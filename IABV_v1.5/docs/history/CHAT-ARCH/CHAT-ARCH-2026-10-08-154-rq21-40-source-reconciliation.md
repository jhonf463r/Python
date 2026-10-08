# CHAT-ARCH 2026-10-08-154 — RQ21.40 SOURCE RECONCILIATION

## 1. Provenance

Source baseline independently inspected:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`

Tree baseline:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

Inspection was read-only through pinned Git source. No runtime or source modification.

## 2. RQ21.40 reconciliation

RQ21.40 semantic verdict was PASS WITH ONE LOCAL REPAIR, adding a method-invariant definition of necessary demand and preserving the scope boundary.

The source reconciliation now checks the three code-facing questions identified by the challenger.

### A. Does current code derive demand by operation-level decomposition?

Observed source fact:
`CapabilityReadinessService._required_capabilities(intent)` maps `TaskIntent.intent_key` directly to hard-coded capability ID lists.

Examples observed in the baseline include:
- `browser.search` → `browser.search.google`
- `browser.navigate` → `browser.generic.navigation`
- `tools.local_workflow` → `tools.local.registry`, `tools.local.execution`
- `tools.sandbox` → `tools.local.registry`, `tools.local.sandbox`
- unknown intent keys → `assistant.local.chat`.

Adjudication:
this is a readiness capability mapping keyed by broad intent, not a demonstrated operation→capability transformation with exact task-level R_task semantics.

### B. Are capability/envelope dimensions declared by capability or created from each task?

Observed source facts:
- `CapabilityReadiness` contains `capability_id`, status, score, evidence, missing_signals and metadata;
- `ToolCapability` is a fixed enum containing broad capability concepts;
- `ToolCard.capabilities` is `list[str]` and currently contains implementation/action labels such as `open_url`, `llm_query`, `code_assistance`, `web_browsing`, etc.;
- there is no first-class `required_capability_ids` field on `ToolTask` in this baseline;
- there is no first-class capability-envelope structure attached to the task/capability contract in the inspected models.

Adjudication:
the baseline has multiple capability vocabularies, but no proven common operation-level requirement vocabulary with declared envelope dimensions. The proposed semantic contract therefore cannot yet be instantiated directly from existing fields without a documented semantic join.

### C. Does current demand derivation produce UNKNOWN in the required sense?

Observed source fact:
`_required_capabilities()` always returns a mapping result and falls back to `assistant.local.chat` for unknown intent keys.

Adjudication:
the current readiness path does not expose the proposed `KNOWN / AMBIGUOUS / UNKNOWN / EMPTY_CAPABILITY_DEMAND` demand-state semantics. Its fallback behavior can convert unresolved semantic demand into a concrete readiness capability.

This is a material mismatch with the repaired contract and must not be treated as implementation-ready.

## 3. Existing route remains causal

Observed source fact in `ToolTeachService.build_task_from_request()`:
`_select_mode()` and tool/synaptic selection occur before `_build_actions()` and before `ToolTask` construction.

`ToolTask` currently contains `tool_id`, `objective`, `actions`, `execution_scope`, expected outcome and metadata, but not first-class task-level required capability identity.

`ToolRegistry.pick_card_for_task()` receives the `ToolTask` and currently resolves by concrete task/tool/assistant/lexical paths rather than an authoritative abstract capability requirement.

## 4. Source reconciliation verdict

Overall:
**SEMANTIC CONTRACT = READY FOR CODE-FACING CONTRACT RECONCILIATION, BUT NOT IMPLEMENTATION-READY.**

What can be reused:
- `TaskIntent` as an existing broad semantic input;
- `CapabilityReadinessService` as existing readiness/evidence infrastructure;
- `CapabilityReadiness` as an existing readiness-domain record;
- existing `ToolTeachService → InteractionModeSelector → ToolRegistry` selection path;
- existing ToolTaskStatus.DEFERRED for a later empty-eligibility outcome.

What is not yet proven reusable as the demand contract:
- `_required_capabilities()` mapping as exact R_task;
- `ToolCapability` as the universal abstract capability vocabulary;
- `ToolCard.capabilities` as realization declarations for the new contract;
- `ToolTask.actions` as pre-selection demand;
- current fallback-to-`assistant.local.chat` as a valid UNKNOWN policy;
- any current envelope representation.

## 5. First open implementation-contract edge

`existing demand/readiness inputs + explicit operation semantics → exact versioned R_task → existing readiness/candidate filtering → constrained ToolCard selection`.

Before implementation, determine the smallest code-facing contract that can preserve the semantic invariants without duplicating existing capability/readiness machinery.

## 6. FACT / INFERENCE / DESIGN JUDGMENT / UNPROVEN

FACT:
- source baseline contains `CapabilityReadinessService._required_capabilities()` hard-coded intent→capability mappings;
- `CapabilityReadiness` exists;
- `ToolCapability` is a distinct enum;
- `ToolCard.capabilities` is a string list;
- `ToolTask` has no first-class required capability field in the inspected baseline;
- current selection precedes action construction.

INFERENCE:
- current readiness mapping is not exact realization-independent R_task;
- current fallback can hide unknown demand by selecting a generic capability;
- the semantic contract needs an explicit code-facing join before implementation.

DESIGN JUDGMENT:
- preserve existing readiness and selector organs and add only the minimum semantic wiring after the contract is closed.

UNPROVEN:
- whether another uninspected source path already provides the required semantic join;
- exact minimum set of existing types/fields that can express the repaired contract without extension;
- runtime impact and learning behavior.

## 7. Implementation status

DO NOT IMPLEMENT.
Next actor: CODEX for one narrow source-level contract census and reuse/composition decision, using the exact questions below.