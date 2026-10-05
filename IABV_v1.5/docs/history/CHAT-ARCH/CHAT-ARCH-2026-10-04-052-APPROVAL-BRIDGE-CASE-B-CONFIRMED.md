# CHAT-ARCH-2026-10-04-052 — APPROVAL BRIDGE CASE B CONFIRMED

## OBJECTIVE

Independently reconcile Codex's approval-continuation audit and determine whether the missing direct-`ToolTask` approval bridge is a true absence or can be expressed through existing organs.

## CANONICAL STATE

Remote `main` before this writeback was:

`f6cc8fb7d610520c3d8bbb5b14ac5f686320ea8a`

Relevant episode:

- task `f7689caf-00ef-4a49-a7d4-c38e27fd6ec8`
- result `15c940dc-65f6-4285-bf6f-1b8f02a4d5b1`
- target runtime commit `be97b989559cc04cebc9eb62890d6bc73e03dd7a`

## INDEPENDENT RECONCILIATION

Source inspection confirms:

### Direct ToolTask path

`AutonomousEvolutionService.plan_or_execute()`
→ `ToolTeachService.execute_external_consultation()`
→ direct `ToolTask`
→ `ToolApprovalPolicy`
→ sandbox
→ `waiting_approval`.

`ToolRecordRepository.get_task(task_id)` can recover persisted tasks.

`ToolTeachService.execute_task(task)` is the existing execution owner.

### Session/playbook approval path

`AdaptiveTaskOrchestrator.approve_next_phase(session_id)`
→ `ExecutionPlaybookService.approve_next_phase(session)`
→ approval checkpoint update
→ session executor
→ `ToolOperationalExecutor.execute(session)`
→ task reconstructed from the session
→ `ToolTeachService.execute_task(task, approved=approved)`.

The checkpoint model is session/playbook-oriented and does not establish identity by direct `ToolTask.task_id`.

### Generic human approval infrastructure

`HumanApprovalBroker` is a real existing organ. It creates `ApprovalRequest` objects with:

- `request_id`
- `kind`
- `reason`
- arbitrary string `scope`

and exposes:

- `request(...)`
- `approve(request_id, ...)`
- `reject(request_id)`
- `pending_requests()`
- post-resolution handlers.

Its documented scope can describe the exact decision being approved, and the broker contains a reason code `external_call_authorization`.

However, source search found no verified call in the direct IABV external-consultation path that creates a HumanApprovalBroker request scoped to the concrete ToolTask and then feeds the resulting approval back into that task's execution.

`ApprovalGateService` exists but evaluates `AdaptiveSession` checkpoints; it is not currently the missing direct-task bridge.

## CASE

**CASE B — EXISTING ORGAN CAN EXPRESS IT, WIRING MISSING**

This classification is independently reinforced.

## MINIMUM MISSING RELATION

The smallest missing relation is not a new approval subsystem.

It is:

`direct ToolTask requiring approval`
→ existing human-approval mechanism with a stable approval scope containing `task_id`
→ verified human result
→ existing task retrieval/state transition
→ existing `ToolTeachService.execute_task()`
→ real adapter execution.

The exact ownership of the bridge still requires a design decision. The strongest existing ownership candidate is `ToolTeachService` because it already owns:

- task construction for direct consultations;
- governance evaluation;
- task persistence/retrieval access through its memory repository;
- execution entry into the adapter.

The `HumanApprovalBroker` remains the approval transport/UI mechanism rather than a new coordinator.

## IMPORTANT LIMIT

This does not authorize implementation.

A synchronous broker request inside `execute_task()` could block the runtime waiting for UI resolution, while an asynchronous UI flow would require a persisted approval correlation and explicit resumption contract. The correct lifecycle must therefore be designed before coding.

## WHAT THIS PROVES

- Existing approval transport can represent a task-scoped authorization conceptually through `scope`.
- Existing task persistence can recover by `task_id`.
- Existing task execution is already centralized in `ToolTeachService.execute_task()`.
- The direct-task approval bridge is absent/not proven as current wiring.

## WHAT THIS DOES NOT PROVE

- that `HumanApprovalBroker` is already suitable operationally for this exact asynchronous continuation without lifecycle changes;
- that the bridge should be synchronous or asynchronous;
- that UI currently exposes an approval control for this direct task;
- real Codex launch or response capture.

## KNOWLEDGE DELTA

The repository has the three necessary building blocks:

`HumanApprovalBroker` + `ToolRecordRepository` + `ToolTeachService`

but their direct-task approval lifecycle is not composed.

## METHOD DELTA

Before implementation, specify the smallest lifecycle contract:

`Task requiring approval → ApprovalRequest(task-scoped) → human resolution → correlation/verification → same task reloaded → execution`

Do not use `approved=True` as the correlation mechanism.

## RELATION DELTA

Current relations are:

`AdaptiveSession → ApprovalCheckpoint → session approval → session executor → ToolTask`

and separately:

`ToolTask → ToolApprovalPolicy → waiting_approval`

The missing relation is:

`ToolTask → HumanApprovalBroker(scope={task_id,...}) → ApprovalResult → same ToolTask execution`.

## ROUTING DELTA

The current domain frontier is no longer pure archaeology.

Required capability:
**smallest safe approval-lifecycle design using existing organs**.

Immediate actor:
**ChatGPT / synthesis-adjudication**, because source truth has now been independently reconciled and the remaining uncertainty is a design contract rather than missing repository facts.

After design adjudication, Codex should implement only the approved minimal seam, followed by independent runtime verification.

## NEW OPEN EDGE

`approved task-scoped approval lifecycle contract → implementation decision`

## IMPLEMENTATION AUTHORITY

**NOT AUTHORIZED**

## WRITEBACK

This record is the independent reconciliation of the Codex audit.

END OF RECORD
