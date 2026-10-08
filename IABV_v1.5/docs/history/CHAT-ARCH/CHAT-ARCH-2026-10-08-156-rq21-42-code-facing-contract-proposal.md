# CHAT-ARCH 2026-10-08-156 — RQ21.42 CODE-FACING CONTRACT PROPOSAL

## 1. Status

RQ21.41 source reconciliation = CLOSED-C / bounded extension.

This record is the coordinator's **PROVISIONAL code-facing contract proposal**. It is not an implementation authorization.

Next validation actor: Sonnet/Claude, source-aware adversarial challenge.

## 2. Design objective

Preserve the semantic contract at the existing operative selection boundary using the smallest possible extension of existing organs.

Target chain:
`pre-selection semantic demand → frozen R_task → capability eligibility → existing selector/ranking → realization`.

Do not create a second readiness subsystem, universal registry or parallel router.

## 3. Proposed authoritative capability identity for first implementation slice

Use the existing `CapabilityReadiness.capability_id` namespace as the **bounded authoritative capability-ID vocabulary for the first slice**, but only for IDs whose semantic meaning is explicitly validated against the repaired contract.

Important limits:
- this does not establish that every current readiness ID is a universal capability;
- `ToolCapability` remains a separate vocabulary unless a semantic join is explicitly proven;
- `EnvironmentCapability.capability_id` is not automatically demand identity;
- `ToolCard.capabilities` is not automatically the authoritative abstract vocabulary.

This is deliberately a bounded reuse decision, not a global ontology decision.

## 4. Proposed demand contract

Introduce one typed, first-class task-demand representation that can survive the pre-selection path and later be persisted on the task.

Minimum conceptual payload:
`required_capability_ids` + `demand_state` + `vocabulary_version` + optional bounded envelope values.

Semantic states:
- KNOWN: complete justified requirements for the current decision;
- AMBIGUOUS: multiple complete requirement sets remain plausible;
- UNKNOWN: no complete justified set; known necessary lower-bound requirements may be retained but cannot certify sufficiency;
- EMPTY_CAPABILITY_DEMAND: explicit success-predicate claim that this capability dimension requires no functional competence.

Do not encode UNKNOWN as `assistant.local.chat` or another concrete capability.

## 5. Proposed placement rule

The demand must exist **before** any realization selection.

The exact implementation placement remains a challenge point, but semantically the flow must be:
`semantic demand derivation → frozen requirements → selector/eligibility input → selection → ToolTask persistence`.

Do not wait until `ToolTask` construction to derive requirements because the current code selects before constructing the task.

## 6. Proposed realization declaration

Add a distinct semantic declaration on `ToolCard` equivalent to:
`realizes_capability_ids: list[str]`.

This must remain separate from existing:
`ToolCard.capabilities: list[str]`.

`ToolCard.capabilities` continues to represent the current heterogeneous/action-oriented labels until separately reconciled.

A realization is functionally eligible only if its declared capability IDs cover the KNOWN required IDs for this decision under the bounded semantic contract.

Minimum conjunction:
`required_capability_ids ⊆ realizes_capability_ids`.

Do not introduce OR/weights/hierarchy in this first slice.

## 7. Proposed evidence/readiness separation

Keep `CapabilityReadiness` as the existing readiness/evidence state.

Do not use:
- readiness score;
- availability;
- approval state;
- ToolCard availability;
as substitutes for demand identity.

Selection should evaluate capability sufficiency first, then existing readiness/availability/governance conditions.

Do not learn functional incapability from a permission/readiness/availability failure.

## 8. Proposed hard eligibility boundary

The capability eligibility filter must be applied before any path can make a concrete realization authoritative.

Therefore it must constrain, not merely advise:
- InteractionModeSelector scoring;
- external/preferred realization decisions;
- Synaptic routing authority;
- explicit tool preference;
- lexical/tool-ID fallback;
- ToolRegistry first-card fallback.

Any route that bypasses the hard filter is a semantic correctness defect.

Do not assume the insertion point; source-aware reconciliation must identify the smallest common boundary or prove why more than one boundary is required.

## 9. UNKNOWN / AMBIGUOUS / EMPTY behavior

Minimum semantic rule:
- UNKNOWN: do not claim capability eligibility from a false KNOWN requirement set;
- AMBIGUOUS: do not silently collapse interpretations into one requirement set;
- EMPTY_CAPABILITY_DEMAND: only if explicitly justified; it must not mean 'no realization found'.

The exact runtime response (clarification, governed defer, safe fallback, or other policy) is not part of the semantic identity contract unless source evidence requires it.

Known capability demand with no eligible realization must remain a governed negative outcome and must not resurrect unconstrained fallback selection.

Existing `ToolTaskStatus.DEFERRED` is a reuse candidate for this negative propagation.

## 10. Persistence / anti-circularity

Once a demand version is used for a selection decision, preserve its exact semantic inputs/provenance/version.

The later action/result must not rewrite the demand that justified the earlier selection.

Any later reinterpretation is a new demand version.

## 11. Reuse-first classification of the proposed seam

| Layer | Proposed treatment |
| --- | --- |
| Demand semantics | bounded EXTEND |
| Existing capability-ID namespace | REUSE with semantic validation |
| Readiness/evidence | REUSE |
| ToolCard realization declaration | bounded EXTEND |
| Selection | WIRE/REPAIR existing selector/registry paths |
| Deferred negative outcome | REUSE existing ToolTaskStatus.DEFERRED if the existing propagation can be wired |

No new registry is justified by current evidence.

## 12. Critical unresolved questions for adversarial review

1. Is it semantically safe to reuse `CapabilityReadiness.capability_id` for the first implementation slice when some existing IDs may encode readiness/system preconditions rather than pure functional capabilities?
2. Can the demand be carried in one existing typed object or must a bounded new task-demand value be introduced?
3. Can a single common hard-eligibility boundary constrain all current selection/override/fallback routes without duplicating logic?
4. Is `realizes_capability_ids` sufficient without an immediate first-class envelope implementation, given that the first slice may choose capabilities whose parameters are currently simple/non-parameterized?
5. Can UNKNOWN/AMBIGUOUS be preserved without contaminating existing intent/readiness fallback semantics?
6. Can the existing empty-set/deferred path be reused without creating fallback resurrection?
7. Does the proposed namespace remain realization-independent in concrete current examples?

## 13. FACT / INFERENCE / DESIGN JUDGMENT / UNPROVEN

FACT:
- existing CapabilityReadiness capability IDs exist;
- existing ToolCard.capabilities is a heterogeneous string list;
- ToolTask is constructed after selection in the traced path;
- existing ToolTaskStatus.DEFERRED exists.

INFERENCE:
- a typed first-class demand representation before selection is required by the repaired semantic contract;
- realization declarations must be separated from current action labels.

DESIGN JUDGMENT:
- reuse the bounded readiness-ID namespace for the first slice only where semantics are explicitly validated;
- add a distinct ToolCard realization declaration rather than repurposing ToolCard.capabilities.

UNPROVEN:
- exact field/type placement;
- exact authoritative capability subset;
- exact common eligibility boundary;
- whether an envelope can remain deferred for the first slice without compromising the contract.

## 14. Implementation status

**DO NOT IMPLEMENT.**