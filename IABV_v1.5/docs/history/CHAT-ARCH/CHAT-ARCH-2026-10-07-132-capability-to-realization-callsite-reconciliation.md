# CHAT-ARCH-2026-10-07-132 — CAPABILITY → REALIZATION CALL-SITE RECONCILIATION

## PURPOSE
Reconcile the targeted capability-to-realization audit after episode 131 and select the smallest next source-level trace that directly informs IABV's universal adaptive routing and future multi-AI delegation.

## PROVENANCE
Source baseline: `07ebffc8f866fc99a3f78091dcd1edd456a0da00` / tree `f0e1294982479426b140eab21f16f2f839504413`.
Latest reasoning is based on committed source inspection only; no IABV runtime or production-source modification was performed.

## KNOWLEDGE DELTA
Episode 131 establishes:
- the required capability identity is not carried into `ToolRegistry.pick_card_for_task()`;
- local/browser realization paths select through tool ID, assistant kind, task text or card metadata;
- external-AI composition can preserve `assistant_kind → ToolCard → adapter`, but that is not a proof that a required capability caused the choice;
- `SynapticRouter` ranks by task kind, AssistantStrength, weights and availability, while ATO's Synaptic result does not replace the operative route decision;
- `ToolTeachService.execute_task()` is a common execution point for registered ToolCards/adapters, but not yet a common capability-to-realization resolver.

Therefore the current open edge is:
`required capability + viable realization → specific candidate → operative routing`.

## INTERPRETIVE CORRECTION
Do not call this a generic 'missing capability system'. The existing system already has capability, readiness, task-kind, assistant-profile, ToolCard and adapter mechanisms. The demonstrated gap is the absence of a proven common causal join preserving an abstract required capability into a concrete realization choice.

## PLASTICITY / UNIVERSAL ALGORITHM
This edge matters because a universal adaptive substrate should separate abstract capability from any one provider or application:
`abstract capability → multiple realizations → context/constraint-conditioned selection`.

Longer-term developmental target:
`verified experience → updated reusable capability knowledge → altered realization selection → verified improvement → non-identical reuse`.

No autonomous learning, biological neuroplasticity or general intelligence claim is made by this static result.

## NEXT DISCRIMINATING TRACE
Pick one concrete required capability whose normal caller constructs a ToolTask and follow it to the realization-selection inputs. Prefer an external-assistant-relevant capability/path because the product goal is IABV-mediated use of Codex/Claude/ChatGPT, but keep the trace narrow.

Minimum trace:
`named capability → producing request/intent → caller constructing ToolTask → inputs passed to ToolRegistry.pick_card_for_task() or equivalent → selected ToolCard/assistant kind → route → adapter invocation boundary`.

Determine exactly where capability identity disappears or whether an explicit semantic transformation preserves it.

## ROUTING
Next actor: **CODEX**, targeted static call-site audit.
After a concrete trace exists: **SONNET/CLAUDE**, fresh independent adversarial verification.
No runtime, code modification or new architecture yet.