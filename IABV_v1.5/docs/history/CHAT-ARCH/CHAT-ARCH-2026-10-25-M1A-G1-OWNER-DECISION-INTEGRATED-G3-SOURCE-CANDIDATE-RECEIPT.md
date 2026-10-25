# Owner decision receipt — integrated G3 authorization-to-handle source candidate

- Date: 2026-10-25 (America/Bogota).
- Repository: https://github.com/jhonf463r/Python
- Decision provenance: explicit Owner message in this conversation, replying to the request for one integrated G3 source-only task.
- Baseline route read live from `main`: `672e4b94302eb968721f3185e712cd832428004e`.
- Decision: **AUTHORIZED**, exactly one integrated source-candidate task, with the condition that the Space-Time continuity/control records be analyzed and reconciled first.
- Task ID: `M1A_G1_G3_INTEGRATED_AUTHORIZATION_TO_HANDLE_SOURCE_CANDIDATE_20261025`.

## 1. Owner decision and exact scope

The Owner authorized one integrated source-only candidate spanning only the direct authorization-to-consumption call chain needed to bind the same opened filesystem object to the decision and reader. The scope may include, as justified by inspected direct dependencies:

- the approved workspace-root capability/configuration contract;
- the target resolver and opened-target capability;
- `ReadAuthorizationCoordinator` decision/permission binding;
- server guard and handler propagation;
- handle-backed file reads and handle-backed directory enumeration;
- directly related source tests.

This is not permission to invent or provision an IABV trust root, custodian, mandate, issuer, credentials, platform configuration or production authority. A workspace-root capability is only a filesystem-containment anchor; it is not G1 authority.

## 2. Required invariant and fail-closed result

The decision, permission and consumer must bind to the same live opened object. A path string, canonical path, copied file ID, native handle opened after a text-only authorization, or post-authorization path resolution does not satisfy this invariant.

The candidate must default-deny reparse points and unsupported/ambiguous paths, define handle ownership/lifetime/close-once semantics, and consume the exact authorized file or directory handle. If the approved root identity is unavailable or native semantics cannot be established without guessing, stop with a precise blocker and preserve the existing denial. Do not implement a path-based fallback or synthetic trust provider.

## 3. Required prior reconciliation — completed as documentation route work

The Owner asked to audit the Space-Time memory/continuity logic before moving forward. Review of the living protocol `CONTINUITY_SPACE_TIME_ANTI_LOOP` revision 2.0 confirms that its core already prescribes the needed process: reconstruct evidence with provenance; separate event/observation/record time; keep immutable history while evolving the current route; record explicit Owner authorization transitions; synchronize the front doors; and verify adoption by fetching back from live `main`. No duplicate protocol, memory service or orchestrator is justified.

The static continuity audit also records separate product-level risks (portable-context freshness/status, goal-before-perception ordering, destination-specific delivery receipts and end-to-end later reuse). Those remain static findings, not runtime proof and not part of this G3 task. They must not be folded into the G3 source scope without a separate authorization.

This decision receipt and route update preserve the prior terminal task and its evidence provenance. Codex/local Windows claims in the previous blocker receipt remain `OWNER_SUPPLIED_CODEX_REPORT`, not independently verified local state in this environment.

## 4. Explicit boundaries

```text
TASK=M1A_G1_G3_INTEGRATED_AUTHORIZATION_TO_HANDLE_SOURCE_CANDIDATE_20261025
OWNER_DECISION=AUTHORIZED; ONE_TASK_ONLY; SPACE_TIME_RECONCILIATION_FIRST
CODEX_HANDOFF=PREPARED_NOT_SENT
TEST_SOURCE_AUTHORING=ALLOWED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
WORKSPACE_ROOT_IDENTITY_BOUND_TO_APPROVED_POLICY=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
```

No code task was executed by creating this receipt. This documentation transition does not establish a runtime principal, trust root, Windows-kernel guarantee, test result or bridge readiness. The next step is to prepare one bounded prompt for the existing Windows Codex session; this interface does not directly control that session. After its one terminal report, stop for separate reconciliation and a new explicit decision before any follow-on.
