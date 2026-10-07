# CHAT-ARCH-2026-10-07-130 — CAPABILITY CONTRACT IMPACT RECONCILIATION

## PURPOSE

Reconcile the latest Codex contract audit after the independent Sonnet challenge and determine whether the identified readiness/StrategyPack mismatches are merely representational/rationale defects or materially affect operative decision routing.

## PROVENANCE

Source-bearing baseline:
`07ebffc8f866fc99a3f78091dcd1edd456a0da00`
Tree:
`f0e1294982479426b140eab21f16f2f839504413`

Current documentation tip at this reconciliation is later than the source-bearing baseline and consists of documentation writebacks only with respect to this line of reasoning. Do not treat documentation HEAD movement as executable-source change.

## CURRENT CLAIM STATUS

Latest Codex verdict:
`PARTIALLY CONFIRMED`.

Durable correction:
The earlier claim that the first edge is a generic `intent → capability ID` data-flow break was too strong. The source actually uses a common string vocabulary across readiness and pack requirements in many cases, but separate handwritten tables and pack mappings are not a single authoritative contract.

More importantly:
`StrategyPack.required_capabilities` is consumed by `_candidate_rationale` and contributes to candidate explanation/state aggregation, but the latest audit did not establish that the mismatch changes the operative final route.

Therefore:
`contract inconsistency ≠ decision impact`.

## CLOSED STATIC KNOWLEDGE

- Several intent → required-capability mappings and pack requirements match exactly.
- Several concrete intents have mismatched requirements or mismatched pack defaults.
- No explicit general mapping from ToolCard capability labels or EnvironmentCapability IDs into readiness IDs was found in the inspected path.
- SynapticRouter has a separate task-kind → AssistantStrength → candidate-ranking path and uses WorldModel-derived assistant availability.
- ToolRegistry has a realization-selection path based on tool ID, assistant kind, and textual/capability token overlap.
- These mechanisms remain partially parallel rather than a proven common capability contract.

## OPEN QUESTION

Do the observed pack/capability mismatches affect an operative decision, or are they limited to candidate rationale / descriptive metadata / unconsumed contract declarations?

The immediate discriminating trace is:
`session.chosen_pack_id` and pack selection/consumption of `browser.generic` for fallback or mismatched intents → downstream consumer → final route/strategy actually used.

## DEVELOPMENTAL SIGNIFICANCE

This edge is relevant to universal plasticity only if the contract affects real capability activation or realization selection.

The long-horizon developmental target remains:
`experience/observation → verified capability knowledge → composition/refinement/generalization → context-conditioned activation → later non-identical reuse → changed future decision/implementation`.

Do not elevate a rationale defect into a plasticity bottleneck without decision evidence.

## PRODUCT / SYMBIOSIS CONSEQUENCE

The nearer practical target remains:
`human objective → IABV capability/resource selection → governed external round trip → capture → verification → continue`.

ChatGPT, Codex, Claude and other tools remain resources/realizations inside this broader system.

If the pack mismatch has no operative effect, the project should pivot toward the more central unresolved composition:
`required capability + viable realization → specific candidate → operative route`,
because that directly bears on IABV's ability to choose among heterogeneous resources.

## NEXT ACTION

Independent Sonnet/Claude audit of the downstream consumers of:
- `session.chosen_pack_id`;
- `pack_id == 'browser.generic'`;
- fallback intents;
- candidate/strategy fields produced by `StrategyPackRegistry.build_candidates`.

The audit must determine whether the mismatch changes an operative route, an executable strategy, or only descriptive rationale/metadata.

No code change or runtime yet.

## ROUTING

Next actor:
**SONNET / CLAUDE**, fresh independent adversarial verifier.

If operative impact is NOT demonstrated:
pivot to `required capability → viable realization → operative routing`.

If operative impact IS demonstrated:
only then consider a minimal existing-organ wire/repair.