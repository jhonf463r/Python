# CHAT-ARCH-2026-10-07-134 — CAPABILITY IDENTITY LOSS / CROSS-CALLER RECONCILIATION

## PURPOSE

Reconcile the Codex episode-133 contrast against the already-audited external consultation path and determine whether an existing normal caller already preserves structured capability/readiness into concrete realization selection.

## PROVENANCE

Source-bearing baseline:
`07ebffc8f866fc99a3f78091dcd1edd456a0da00`
Tree:
`f0e1294982479426b140eab21f16f2f839504413`

Inspection mode:
static source archaeology only.
No IABV runtime, tests or implementation changes were performed.

Current documentation HEAD before this writeback:
`60d994b6b5b75b9fc1a84d5b2272025fa5bee7eb`

Direct GitHub comparison `07ebffc8...` → `60d994b6...` is documentation/history-only; no executable Python source changes are introduced by the coordination writebacks.

## CODEX RESULT RECONCILIATION

The alternative normal caller is real:

`AdaptiveTaskOrchestrator.execute_now()`
→ `ExecutionPlaybookService.execute(session)`
→ `ToolOperationalExecutor.execute(session)`
→ `ToolOperationalExecutor.build_task_for_session()`
→ `ToolTeachService`
→ `ToolRegistry.pick_card_for_task()`.

The session does contain structured capability/readiness:

`CapabilityReadinessService`
→ `context.capability_snapshot`
→ `AdaptiveSession.capability_readiness`.

However, `build_task_for_session()` does not explicitly transfer `session.capability_readiness` or `session.context.capability_snapshot` into the `ToolTask` or picker inputs.

The concrete picker receives selection signals based on:
- explicit `tool_id`;
- `synaptic_preferred_assistant_kind`;
- task title/objective and ToolCard text/capability labels;
- fallback ordering.

Therefore the explicit structured capability/readiness identity is **LOST at the session → ToolTask/picker boundary** for this caller.

## A VS B RECONCILIATION

### A — AutonomousEvolutionService external consultation

Previously established:
`AutonomousEvolutionService.plan_or_execute()`
→ external consultation construction
→ `ToolTeachService.build_task_from_request()`
→ `ToolTeachService.execute_task()`
→ `ToolRegistry.pick_card_for_task()`.

The external consultation path also does not pass a first-class required-capability/readiness object into picker selection.

### B — AdaptiveSession / ToolOperationalExecutor

The new Codex contrast independently reaches the same shared composition point and shows the same absence of first-class capability/readiness at selection time.

### Combined conclusion

For these two normal callers:

`capability/readiness exists upstream`
→ `ToolTask`
→ `ToolRegistry.pick_card_for_task()`

does **not** preserve a first-class required-capability identity into concrete ToolCard selection.

Both callers still reuse the same lower-level infrastructure:
`ToolTeachService → ToolRegistry → adapters`.

That means the useful reusable substrate already exists, but it is not currently capability-aware at the concrete realization-selection boundary.

## STATUS

`STATIC / TWO-NORMAL-CALLER CONVERGENCE / SHARED GAP BETTER LOCALIZED / INDEPENDENT VERIFICATION OPEN`

This is stronger localization than episode 132/133, but it is **not** a repository-wide proof that no other caller or contract preserves capability identity.

## KNOWLEDGE DELTA

- Two normal caller paths now converge on the same realization-selection mechanism without a first-class required-capability/readiness input.
- `session.capability_readiness` can influence upstream execution/playbook decisions without proving that the same capability identity survives into concrete ToolCard selection.
- Reusable infrastructure is present; the missing property is semantic identity preservation at the common task/picker boundary.
- `same common composition point ≠ universal absence proof`.

New invariants reinforced:
- `upstream capability influence ≠ capability identity at realization selection`;
- `shared infrastructure reuse ≠ shared semantic contract`;
- `two caller losses ≠ repository-wide absence`.

## METHOD DELTA

After one targeted caller shows capability loss, contrast a second normal caller before proposing a new bridge.

If both callers converge on the same capability-blind composition point, treat that as a stronger structural-gap candidate, but require an independent verifier to challenge:
1. hidden alternative callers;
2. indirect capability encodings;
3. legitimate capability→tool identity mappings already present elsewhere.

## ROUTING DELTA

Current immediate actor:
**SONNET / CLAUDE**, independent adversarial static verification.

Required capability:
repository-wide source audit focused on whether any existing normal contract preserves a named required capability into ToolCard/assistant/adapter realization selection, and whether the apparent shared gap can be composed from existing organs without a new universal registry.

No runtime.
No production change.
No new architecture.

## FACT / INFERENCE / ASSUMPTION

**FACT**
- `AdaptiveSession` contains `capability_readiness`.
- `build_task_for_session()` does not explicitly copy that structured identity into `ToolTask`.
- the picker does not read `session.capability_readiness` directly.
- the external consultation path likewise lacks a first-class required-capability picker input.
- both paths converge on `ToolTeachService` / `ToolRegistry`.

**INFERENCE**
The capability-to-realization semantic gap is now more strongly localized to the shared task/picker composition boundary.

**ASSUMPTION**
No claim is made that there is no other capability-aware caller elsewhere in the repository, nor that indirect task text/tool IDs never encode equivalent semantics.

## NEXT FRONTIER

`independent verification of shared capability-blind realization-selection boundary`

Then, only if the verifier confirms the gap:
`smallest existing-organ REUSE/COMPOSE option → controlled implementation design`.

