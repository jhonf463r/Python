# CHAT-ARCH-2026-10-07-136 — CAPABILITY → REALIZATION CONTRACT RECONCILIATION

## PROVENANCE

Design input:
Codex response received 2026-10-07 12:30 local.

Executable source baseline independently checked:
`07ebffc8f866fc99a3f78091dcd1edd456a0da00`
Tree:
`f0e1294982479426b140eab21f16f2f839504413`

Independent GitHub source checks in this reconciliation confirmed the cited baseline contracts. No runtime, tests, or executable-source changes were performed by this reconciliation.

## VERIFIED SOURCE FACTS

- `CapabilityReadiness` already carries exact abstract capability IDs, status, score, site and evidence.
- `AdaptiveSession` and `TaskContext` already retain capability readiness upstream.
- `ToolTask` currently has no first-class required-capability or realization-eligibility fields.
- `ToolCard.capabilities` is heterogeneous implementation/action labeling and is not an established abstract capability-ID contract.
- `InteractionModeSelector.select()` is an actual normal operative selector and receives the candidate inventory before final task route fixation.
- `_preferred_external_decision()` can return a preferred external card early.
- `ToolTeachService.build_task_from_request()` can let SynapticRouter-derived selection become authoritative.
- `ToolRegistry.pick_card_for_task()` currently prioritizes `task.tool_id`, then assistant family, lexical overlap, then first registered card.

Therefore the future capability gate must constrain every route/override/fallback path before an ineligible concrete card can become operative.

## RECONCILED DESIGN

### 1. Required capability identity

Preserve the exact readiness-produced `capability_id` as an opaque canonical identifier.

Do not rename it, infer it from text, or translate it through `task_kind`, `AssistantStrength`, `assistant_kind`, or existing `ToolCard.capabilities` labels.

### 2. Realization declaration

The proposed first-class `ToolCard.realizes_capability_ids: list[str]` is accepted as the smallest clear contract.

Semantics:
- exact equality against required capability IDs;
- no textual inference;
- unique/non-empty string validation is appropriate;
- do not impose an invented regex on the identifier format.

`ToolCard.capabilities` remains implementation/action capability data and is not silently reinterpreted.

### 3. ToolTask transport

Accept a first-class `ToolTask.required_capability_ids` so the invariant survives task construction and execution.

Readiness should be represented as a **decision-time snapshot**, not implied to be live mutable state. Prefer explicit snapshot semantics (for example a `capability_readiness_snapshot` field or equivalent structured trace) with provenance/timestamp.

Do **not** make `eligible_tool_ids` a durable semantic property of the task. The capability-eligible candidate set is a selection-context/result artifact and can become stale as cards, availability, policy or allowed-tool scope change. It should be computed at selection time and persisted in the selection trace.

### 4. Multiple requirements

For the minimum contract, a list of required IDs has conjunctive semantics:
`required_capability_ids ⊆ ToolCard.realizes_capability_ids`.

Do not infer OR/disjunctive alternatives from a flat list. Alternative requirement groups require a separate explicit contract and are out of this minimal change.

### 5. Eligibility versus readiness/availability

Keep separate layers:

`required capability identity` → static realization eligibility

then independently:

`readiness / availability / adapter / authorization / context / cost / history / quota` → current viability/ranking/governance.

A card that cannot realize the required capability is never eligible, regardless of availability or preference.

A card that can realize it but is currently unavailable remains a known realization but is not an executable-now candidate unless the existing policy explicitly models a wait/defer state.

### 6. Preference / override semantics

Assistant preference remains a strong preference with fallback **inside the capability-eligible set**.

Therefore:
- explicit `tool_id` cannot bypass capability eligibility;
- preferred external branch cannot bypass it;
- SynapticRouter cannot bypass it;
- assistant-family fallback cannot bypass it;
- `ToolRegistry` fallback cannot escape it when required-capability constraints are present.

SynapticRouter remains a complementary preference mechanism:
`task_kind → assistant fit`
not a universal required-capability resolver.

### 7. Route preservation

The invariant after selection must be:

`selected ToolCard.tool_id == ToolTask.tool_id == resolved route tool_id`

and:

`resolved adapter == selected ToolCard.adapter_key`.

If a constrained task carries required capability IDs and the explicit/current `task.tool_id` is not eligible, resolution must fail closed rather than fall back to an unrelated card.

### 8. Provenance

The minimum structured selection trace must retain:
- required capability IDs;
- readiness snapshot and evidence refs;
- candidate ToolCard IDs considered;
- capability-based exclusions;
- allowed-tool intersection;
- availability/adapter/authorization results;
- ranking dimensions;
- preference/override/fallback path taken;
- selected ToolCard/tool ID and adapter key;
- declaration identity/version/hash;
- session/correlation/provenance IDs.

Text rationale may accompany this trace but must not substitute for structured evidence.

## CLASSIFICATION

`STATIC / DESIGN RECONCILED / IMPLEMENTATION NOT AUTHORIZED`

Construction class:
`REUSE + COMPOSE + WIRE/REPAIR + NARROW EXTEND`

No new registry, routing organ, capability brain, or universal manager is justified.

## REMAINING MICRO-GATE BEFORE IMPLEMENTATION

Independent adversarial review should verify four exact semantics against the baseline:

1. flat required-ID list = conjunction, with no hidden OR behavior;
2. readiness is a decision-time snapshot, not a substitute for requirement identity;
3. capability-eligible candidate set is ephemeral selection state, not a stale task-owned truth;
4. every preference/override/fallback path remains bounded by the capability-eligible set.

Also enumerate existing `ToolCard` construction/registration sites so implementation cannot accidentally leave every relevant realization undeclared.

Next actor:
**SONNET / CLAUDE**, independent static contract challenge.

No runtime. No implementation. No code modification.
