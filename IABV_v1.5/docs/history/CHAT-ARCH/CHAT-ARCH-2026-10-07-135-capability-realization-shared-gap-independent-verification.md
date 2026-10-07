# CHAT-ARCH-2026-10-07-135 — CAPABILITY → REALIZATION SHARED GAP / INDEPENDENT VERIFICATION

## PROVENANCE
Executable source baseline:
`07ebffc8f866fc99a3f78091dcd1edd456a0da00`
Tree:
`f0e1294982479426b140eab21f16f2f839504413`
Static only: no runtime, tests or source modifications.

## INDEPENDENT VERIFICATION
Sonnet/Claude confirms that the two inspected normal paths:
- AutonomousEvolutionService → ToolTeachService → ToolRegistry
- AdaptiveSession → ToolOperationalExecutor → ToolTeachService → ToolRegistry

both lack first-class required-capability/readiness identity at concrete ToolCard selection.

A reusable partial bridge exists:
`task_kind → SynapticRouter → AssistantStrength → assistant_kind → ToolRegistry`.

This is not equivalent to:
`required capability/readiness → viable realization → operative route`.

Additional static closures:
- ToolDiscoveryService is discovery/status/reporting, not the operative selector.
- EvolutionCenterViewModel._run_tool_sandbox() is explicit tool_id selection, not abstract capability routing.
- InteractionModeSelector is an actual normal selector used by ToolTeachService._select_mode(), but its current inputs are suggested tool, task kind, availability, cost, history and related dimensions; it does not receive the readiness capability identity.

## CLASSIFICATION
`COMPOSE + WIRE/REPAIR`, not NEW.

Existing reusable substrate:
CapabilityReadinessService, AdaptiveSession, ToolTask/metadata, InteractionModeSelector, SynapticRouter, AssistantCapabilityRegistry, ToolRegistry and adapters.

Missing semantic join:
`required capability/readiness ID → existing realization-fit representation → viable realization → operative route`.

## NEXT DESIGN GATE
Before implementation, determine the smallest exact contract that preserves:
capability identity, readiness, availability, candidate identity, route identity and provenance.

Do not treat task_kind, AssistantStrength, ToolCard action labels or assistant_kind as interchangeable with required capability IDs.

Next actor: **CODEX**, minimal design archaeology only.
No runtime and no implementation yet.
