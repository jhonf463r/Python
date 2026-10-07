# CHAT-ARCH-2026-10-07-133 — TOOL OPERATIONAL EXECUTOR / CAPABILITY CONTRAST

## PURPOSE
Compare one alternative normal execution caller against the external consultation path to determine whether any existing caller already preserves `session.capability_readiness` into ToolTask/tool selection.

## CURRENT KNOWLEDGE
Episode 132 established that the examined external consultation path:
- derives an external assistant preference/task data from intent, goal, diagnosis and governance;
- builds a ToolTask without a first-class required-capability field;
- reaches `ToolRegistry.pick_card_for_task()` using tool ID, assistant kind and task text;
- reaches external-assistant adapters through existing ToolCards;
- does not carry a required-capability ID into that realization selection path.

The current question is deliberately narrow:
`AdaptiveSession → ToolOperationalExecutor.build_task_for_session()`
Does this alternative normal caller preserve capability/readiness identity into the concrete realization selection?

## WHY THIS EDGE MATTERS
The product goal remains `human objective → IABV resource selection → governed external/local realization → capture → verification`.
The broader universal/plasticity target remains `abstract capability → multiple realizations → context-conditioned selection`, followed later by verified learning/reuse.
If another existing caller already carries capability identity, we should REUSE/COMPOSE it rather than introduce a new bridge. If not, the missing join becomes better localized.

## ROUTING
Next actor: **CODEX**, read-only targeted contrast only.
After the contrast, if a common capability-to-realization contract/gap is established, use **SONNET/CLAUDE** for independent verification before any implementation.
No runtime and no source modification yet.