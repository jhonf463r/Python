# Mente Espacio-Tiempo — Owner-context and turn-boundary continuity audit receipt

- Date: 2026-10-25, America/Bogota.
- Task: `M1A_G1_SPACETIME_OWNER_CONTEXT_AND_TURN_BOUNDARY_AUDIT_20261025`.
- Scope: read-only live-main source/documentation audit and bounded method/documentation corrections, explicitly requested by the Owner.
- Baseline live `main`: `74b47561ebddfc113bd8cf869430c3991f206003`.
- Existing living-protocol blob before edit: `a27eed5b2a6afa6e8f6ce006a5babac51c998dd5`.
- Result: `STATIC_AUDIT_WITH_DOCUMENTATION_METHOD_DELTA`.
- Product source edits: none. Tests/build/runtime/MCP/real transport: not run.

## Executive finding

The protocol already defines the core architecture: objective and authority, temporal evidence graph, adaptive role facets, gated action, result adjudication, durable writeback, canonical fetch-back and later non-identical reuse. It already defines Navigator, Domain Specialist, Adversarial Reviewer, Evidence Custodian, Executor, Independent Verifier and Archivist/Learning Synthesizer roles. The main gap is **not a shortage of named personalities**. Several requirements remain documentary rather than enforced across route refresh, context construction and destination delivery.

“Mente/Supermente Espacio-Tiempo” remains an architectural metaphor for governed continuity. The inspected material does not establish consciousness, universal cross-model shared memory or autonomous model-weight learning.

## Findings

### 1. Route drift within one chat/handoff

This conversation observed main advance from `9078bf1f1e9b9d3e4f9e682def78af7bfe19a3fa` to `74b47561ebddfc113bd8cf869430c3991f206003` during audit preparation. The refreshed `CURRENT-STATE.md` selected `M1A_G1_INDEPENDENT_STATIC_REVIEW_OF_INTEGRATED_ORGAN_CANDIDATE_20261025`, while the consolidated handoff still opened with an earlier missing-root wait. This is a direct documentation mismatch. The revised handoff puts the active route first and marks previous routes as history; `CURRENT-STATE.md` remains authoritative.

### 2. Owner constraints need to be bound at each material transition

The method already weighs cost/risk and prefers one evidence bundle, but did not explicitly require rebinding the Owner's immediate goal and constraints—`ZERO_BUDGET`, free/connected tools, access boundaries, desired output and manual effort—at material turn boundaries. This can produce technically plausible steps that miss the human objective or repeat requests already answered.

The correction adds this check to the existing Space-Time Navigator and action-selection contract, not as a new persona or memory service. It does not override authorization or security gates.

### 3. Portable Context freshness

Current source: [`portable_context_get`](https://github.com/jhonf463r/Python/blob/74b47561ebddfc113bd8cf869430c3991f206003/IABV_v1.5/src/iabv_v15/infra/mcp/server.py#L724-L764), blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`.

When `refresh=False`, the handler raises the effective age threshold to at least 86,400 seconds and prefers a persisted rich package over rebuilding an empty package without task context. It does not visibly provide an explicit age/stale/degraded verdict or current-objective/session binding. This is a static contract risk, not proof that active Windows runtime data is stale.

### 4. Goal context follows initial perception construction

Source: [`AdaptiveTaskOrchestrator`](https://github.com/jhonf463r/Python/blob/74b47561ebddfc113bd8cf869430c3991f206003/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1482-L1485) and later [`attach_session_goal_context`](https://github.com/jhonf463r/Python/blob/74b47561ebddfc113bd8cf869430c3991f206003/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1623-L1626), blob `41f6f7b6157226a1c6004591ddff4e36ff6f6da5`.

The first `PerceptionSnapshot` is built before session goal attachment; goal fields are patched later. This is a source-level ordering risk, not proof of a wrong runtime decision. Reuse accepted RQ13 records and trace decision-bearing consumers before changing code.

### 5. Briefing is adapter-conditional and lacks a full destination-bound receipt

[`SessionStartBriefingService`](https://github.com/jhonf463r/Python/blob/74b47561ebddfc113bd8cf869430c3991f206003/IABV_v1.5/src/iabv_v15/services/evolution/session_start_briefing_service.py) returns session ID, a boolean-style outcome and character count, not a durable receipt binding package ID/digest, objective, destination/provider, timestamp, remote message ID and acknowledgment. [Bootstrap](https://github.com/jhonf463r/Python/blob/74b47561ebddfc113bd8cf869430c3991f206003/IABV_v1.5/src/iabv_v15/bootstrap.py#L1138-L1165) wires send/create only when the Devin API adapter exists. This does not deliver automatically to every ChatGPT/Codex session.

### 6. Later causal reuse is not verified

Persisted notes and source wiring do not demonstrate that a named new chat consumed a fresh package, used a lesson in a later decision, and improved an attributable outcome. Runtime delivery and causal reuse were not tested here.

## Method delta proposed in the existing living protocol

Revision 2.2 adds material turn-boundary refresh, Owner goal/budget/access/manual-effort binding, a concise current-context envelope, destination-specific receipt states and separate outcome metrics for stale-route reuse, repeated questions, transfers, freshness/goal provenance, delivery receipts, causal reuse and attributable rework.

## Product-code follow-up priorities — not authorized by this audit

After the current G3 candidate diff is independently reviewed and the route is reconciled:
- **P1:** expose package age, package ID/digest, current goal/session binding, refresh outcome and freshness/degraded state without discarding rich cached content.
- **P2:** reuse RQ13 receipts and ensure the first perception contains the resolved goal, or prove decision-bearing consumers use the goal-bound replacement before acting.
- **P3:** persist a destination-bound briefing receipt and distinguish `DELIVERY_ACCEPTED` from `RECEIPT_CONFIRMED`; do not claim consumed/reused without evidence.
- **P4:** measure a later non-identical task where the lesson changes routing, with a baseline for rework/manual effort.

These are candidate priorities, not permission to modify product code. The active route remains the task in live `CURRENT-STATE.md`.

## Terminal state

```text
TASK=M1A_G1_SPACETIME_OWNER_CONTEXT_AND_TURN_BOUNDARY_AUDIT_20261025
TASK_RESULT=STATIC_AUDIT_WITH_DOCUMENTATION_METHOD_DELTA
BASELINE_MAIN=74b47561ebddfc113bd8cf869430c3991f206003
PROTOCOL_REVISION=2.2; PROPOSED_ON_DOCUMENTATION_BRANCH
PRODUCT_CODE=UNCHANGED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
COST_POLICY=ZERO_BUDGET
ACTIVE_TECHNICAL_TASK=M1A_G1_INDEPENDENT_STATIC_REVIEW_OF_INTEGRATED_ORGAN_CANDIDATE_20261025
NEXT_ACTION=MAKE_EXACT_CANDIDATE_VS_PRETASK_DIFF_AVAILABLE_FOR_INDEPENDENT_STATIC_REVIEW
AUTOMATIC_FOLLOW_ON=FALSE
```

This receipt records a static audit/method proposal only; it does not dispatch Codex, run checks or unlock trust gates.