# Mente Espacio-Tiempo — continuity audit delta after whole-candidate review

- Date: 2026-10-24, America/Bogota
- Direct GitHub source baseline: live `refs/heads/main` = `2cecd5e9b9e175584d65bbb1198a53bc2346d095`
- Existing protocol inspected: `CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md`, blob `da2cb8e1ccda2c0827b1903af430592af3946334`
- Existing static audit inspected: `CHAT-ARCH-2026-10-24-CONTINUITY-ALGORITHMS-STATIC-AUDIT.md`, blob `05f63f43349ebc7a942fa28e7f9e710c67086ab9`
- Method: read-only review of direct-GitHub source and canonical continuity documents. No test, runtime or active application session was run.
- Status: `STATIC_AUDIT_DELTA`; proposal branch only.

## 1. Purpose and conceptual boundary

The Mente Espacio-Tiempo is the project-level layer for cross-chat continuity, temporal/provenance navigation, causal reasoning, state reconciliation and context delivery to the right actor. It is not the same subsystem as IABV's in-process learning/evolution organs. Its job is to help the project carry forward verified state and lessons—not to invent authorization, skip a gate, or claim model-weight changes from documentation.

The existing Space-Time operating protocol is already a strong base: it requires live-main revalidation, five-file intake, `CURRENT-STATE.md` as the sole route authority, a temporal evidence map, prior-art reuse, anti-loop checks, bounded delegation, epistemic labels, durable receipts and fetch-back verification. The right design choice is **repair and verify that architecture**, not create a second memory or orchestrator.

## 2. Current-source findings

### A. Route-intake summaries conflict with the canonical router

The first sections of four other files—`AGENTS.md`, `README.md`, `CONTEXT-INDEX.md` and `MEMORY-OPERATING-PROTOCOL.md`—still contain stale G1 front-matter summaries with `ACTIVE_TASK=M1A_G1_WAIT_FOR_INDEPENDENT_ROOT_EVIDENCE` and the old wait-for-root `NEXT_ACTION`. The live `CURRENT-STATE.md` at this same main SHA says `ACTIVE_TASK=M1A_G1_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY` and `NEXT_ACTION=CONTINUE_EXISTING_LOCAL_CANDIDATE_WITH_OWNER_CONTROLLED_BOOTSTRAP_ISSUER_BOUNDARY`.

Because the protocol correctly declares `CURRENT-STATE.md` the sole router, the stale summaries do not override the route. However, they create contradictory initial context and increase the chance that an agent copies a stale task before reading the canonical router. The correction should be minimal: make front-door summaries explicitly defer to the live `CURRENT-STATE.md`, or update their route summary only when the same change set reconciles all five files. Never let these mirrors become independent authorities.

### B. The persisted portable-context freshness contract can return old context without an explicit freshness state

In `IABV_v1.5/src/iabv_v15/infra/mcp/server.py:724-764`, `portable_context_get(refresh=False)` sets `effective_max_age=max(max_age_seconds, 86400)` and prefers a persisted rich package when rebuilding without an active task context would create empty sections. The response carries package data including its update timestamp, but the handler does not compute and expose a clear `age_seconds`, `stale`, `degraded` or current-objective-binding status. The consumer can therefore receive a deliberately older package without an explicit freshness verdict.

This is a documented trade-off rather than proof that the active Windows package is stale. The tracked GitHub snapshot age and the live workspace age must not be conflated. The small contract improvement is to preserve rich content while exposing timestamp, age, source package ID, objective/session binding, refresh outcome and an explicit freshness state. Do not solve this by silently rebuilding and replacing a rich package with an empty one.

### C. Initial perception is constructed before session goal context is attached

In `IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`, the `_handle_request_body` path builds `perception` around lines 1482–1485; it calls `goal_engine.attach_session_goal_context(...)` around lines 1623–1626 and then patches `perception.goal_context` and `perception.task_context.goal_context`.

That order is a genuine source-level ordering risk: the initial snapshot is built before the session goal is materialized, even though the object is patched later. It does not alone prove a wrong runtime decision. The minimum follow-up is to inspect accepted RQ13 terminal receipts and identify which consumers read the pre-attachment snapshot versus the patched object; do not restart the old broad investigation. Prefer attaching the resolved goal before the first perception snapshot if compatible with the accepted contract.

### D. Session briefing has a narrow transport and no durable delivery receipt

`AppBootstrap` injects `session_creator` and `message_sender` only when the Devin API adapter exists. `SessionStartBriefingService` can build a briefing from Portable Context, but:
- delivery to an existing session requires an explicit session ID and configured sender;
- `BriefingDeliveryResult` records `session_id`, a boolean, an error and character count, but not the source `package_id`, payload digest, destination type, provider message ID, timestamp or acknowledgment;
- creating a new session similarly returns session/character-count status, not a durable receipt that binds the exact briefing/package to a confirmed destination;
- a sender returning `True` is adapter-level status, not independent evidence that the target assistant received and used the content.

This is not an automatic channel for every ChatGPT, Codex, Claude or other session. The GitHub front-door/handoff protocol is a separate continuity channel. Evidence that a note exists in GitHub is not proof that a particular newly opened session read or used it.

### E. Temporal reasoning is specified; closed-loop learning is not end-to-end verified

The protocol defines the required chain—observation, provenance, causal lesson, authorized decision, outcome evidence, writeback, fetch-back, later causal reuse and measurable change—and explicitly distinguishes source wiring from runtime. That is correct. The existing static audit also records the source paths linking `DecisionAuditTrail`, `OperationalSelfExaminationService`, `PortableContextService`, `TaskContextAssembler` and `AdaptiveTaskOrchestrator`.

What is missing is proof from a named task/session that the same package/version and goal arrived at the intended destination, was received, influenced a later decision, and yielded an outcome receipt that the next cycle reused. No test/runtime claim is made here. Saving this audit is a durable knowledge update, not autonomous learning or model-weight training.

## 3. Minimum correction sequence

1. **P0 — completed:** receive the exact whole-candidate staged and unstaged diff bytes, independently hash them, inspect the source delta and preserve gate status. See the linked independent whole-candidate review receipt.
2. **P1 — this audit:** reconcile stale front-door route summaries and specify explicit context freshness/objective provenance, goal-before-perception semantics, and destination-specific briefing receipts. Reuse the existing protocol, audit and RQ13 terminal evidence; do not create a duplicate memory service.
3. **P2 — after scope reconciliation:** make the smallest authorized correction supported by the audit. Documentation-only route-summary cleanup can be proposed on an isolated branch. Changes to portable-context, orchestration order or session-delivery code need an exact bounded change plan; execution checks/runtime delivery verification must follow separately authorized scope. Do not close trust or protected-read gates as a side effect of continuity work.

## 4. Required receipt model for future session delivery

For a destination that actually supports a delivery API, the minimal evidence object should bind:
- `task_id`, exact destination/provider and session/conversation ID;
- `package_id`, package creation/update timestamp, objective/session binding and package digest;
- delivery attempt timestamp, sender/adapter outcome and remote message/correlation ID if available;
- a distinct `DELIVERY_ACCEPTED` versus `RECEIPT_CONFIRMED` state; use `UNAVAILABLE`/ `UNVERIFIED` when the API gives no acknowledgment;
- later reuse reference: which next decision cites the package/lesson and what measurable outcome changed.

Do not record secrets or private credentials. Do not claim read/understanding merely from a successful send API result. The receipt contract is a proposal, not evidence that current destinations support it.

## 5. State and stop rules

```text
SOURCE_BASELINE=LIVE_MAIN_2cecd5e9b9e175584d65bbb1198a53bc2346d095
EXISTING_SPACE_TIME_PROTOCOL=PRESENT; STATICALLY_REUSED
STALE_FRONT_DOOR_ROUTE_SUMMARIES=OBSERVED_IN_4_FILES
PORTABLE_CONTEXT_FRESHNESS=STATIC_RISK; ACTIVE_WORKSPACE_AGE_UNKNOWN
INITIAL_GOAL_ORDER=STATIC_RISK; RUNTIME_EFFECT_NOT_ESTABLISHED
BRIEFING_TRANSPORT=DEVIN_ADAPTER_CONDITIONAL
DURABLE_DESTINATION_RECEIPT=NOT_ESTABLISHED
END_TO_END_CAUSAL_REUSE=NOT_VERIFIED
AUTONOMOUS_MODEL_WEIGHT_LEARNING=NOT_CLAIMED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

This is an audit delta on a documentation branch. It does not change live-main routing or authorize code execution, protected reads, credentials, OS/ACL/trust-store changes, real transport, deployment, merge or spending.
