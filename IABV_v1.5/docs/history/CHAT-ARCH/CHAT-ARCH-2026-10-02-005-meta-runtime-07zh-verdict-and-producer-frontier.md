# IABV v1.5 — CHAT-ARCH-2026-10-02-005
# META-RUNTIME-07ZH — Independent Consumer Audit, Semantic Boundary and Producer Frontier

## PROVENANCE

Source: user-provided independent forensic audit result for 07ZH.

Technical baseline audited:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Execution under review:
`META-RUNTIME-07ZG-20261002-30dd0bc458b24a3baeebcafcb3c26581`

Current canonical memory parent:
`ef7edbf7752f6aa1db64e0a32c52786f55ce9a52`

## VERDICT

07ZH independently strengthens the downstream conclusion:

`generic pending-queue read = CONFIRMED`

and:

`semantic startui_defer consumer = NOT PRESENT in the audited Python call-sites at 5238e85`.

No productive call-site was found that:
- branches on `category=startui_defer`;
- executes `next_action`;
- interprets `metadata` as an executable instruction;
- converts `PlatformPendingTask` into `RuntimeSignal`, `PerceptionSnapshot`, `TaskContext` or a decision input;
- passes the task to `AdaptiveTaskOrchestrator`;
- reaches `start_iabv.ps1` or another UI launcher.

Therefore the hypothesis equivalent to "an existing semantic consumer was merely missed by 07ZG" is not supported within the audited Python tree at this SHA.

## CRITICAL EVIDENCE BOUNDARY

The reader attribution remains source/runtime-correlated rather than kernel-level:

`python.exe PID 22380`

is plausible from chronology and source path, but no kernel-level PID+path+stack receipt exists because WPR FileIO was unavailable.

The absence of a second reader is also scoped to the audited production Python tree and the observed execution. It is not a universal claim about unversioned external tooling.

## PLATFORMPENDINGTASK SEMANTICS

The strongest supported interpretation is:

`PlatformPendingTask = generic backlog/context unit`.

Evidence:
- `category` exists but no audited call-site changes behavior according to its value;
- `next_action` is stored/displayed/descriptive and is not dispatched as executable code;
- `metadata` is carried as data without a discovered semantic execution path;
- `mark_status` is used for existing installation/dependency task completion, not StartUI continuation.

Therefore:

`stored instruction-like text != executable instruction`.

## IABV SELF-OBSERVATION

The correct evidence state remains:

DEFINED = YES
WIRED = PARTIAL
INVOKED = YES
OBSERVED = YES
CAUSED = NO

The startup path observes aggregate pending-task state, but the specific `startui_defer` episode is not shown to become an IABV semantic object, decision input, or changed next decision.

Therefore:

`startup self-observation != semantic recognition != decision causality`.

## PRIMARY FRONTIER RECONCILIATION

07ZH's proposed "consumer seam" must not replace the already established upstream first open edge.

The full chain is:

`natural StartUI DEFER`
→ **durable semantic StartUI intent [PRIMARY OPEN]**
→ semantic consumer
→ trigger/wake
→ fresh resource observation
→ policy recomputation
→ reauthorization
→ existing `start_iabv.ps1` launch authority
→ UI outcome.

07ZH proves that the existing queue currently lacks the semantic consumer needed downstream. But the actual upstream producer is also still unresolved.

Thus the next task is NOT to modify `startup_summary()` merely because it already reads the queue.

In particular:

`generic context summarizer != decision owner`.

Before assigning semantic ownership to `AutonomyCycleService.startup_summary()`, the natural producer and existing decision/ownership boundaries must be re-audited.

## IMPORTANT CORRECTION ON PROPOSED 07ZE FIELDS

The independent report mentioned fields:

`requested_action`, `requested_time`, `source_context`, `expires_at`, `cancelled`.

A search of the currently audited repository tree did not find those exact identifiers.

Therefore these fields are NOT canonical facts of `5238e85` and must not be carried into implementation prompts as if they already exist.

They may be an external design proposal or a reference to another artifact, but their origin and provenance are not established by this audit.

## ROUTING

The next capability required is not another consumer-observation experiment and not implementation.

Required capability:

**deep source/provenance/ownership archaeology of the natural StartUI DEFER producer and the smallest existing-organ semantic boundary.**

Selected actor:

**CODEX**

Reason:
- locate the exact natural DEFER call-site;
- determine which existing owner actually has authority to persist a deferred UI intent;
- verify whether the queue model can carry the required semantics without schema invention;
- identify an implementation-ready seam only after the producer ownership is established;
- reconcile any proposed fields against the exact SHA rather than relying on historical references.

After Codex provides an implementation-ready contract, route to Devin only if a bounded Windows implementation/runtime intervention is actually required.

## NEXT EDGE

`natural StartUI DEFER call-site → existing durable representation with explicit StartUI semantics`.

Do not yet implement:
- wake/scheduler;
- resource watcher;
- recheck;
- reauthorization;
- automatic launch;
- new UI authority.

## REQUIRED NEGATIVE CONTROLS

The next audit must avoid the previous false-positive class:

- do not identify `Invoke-UIResourcePreflight` from its definition only;
- prove the real call-site and branch that produces `DEFER`;
- distinguish existing UI request metadata from actual persistence;
- distinguish a proposed data field from a field present in the target SHA;
- distinguish queue storage from semantic dispatch.

## KNOWLEDGE DELTA

### Knowledge
The Python tree at 07ZH's target SHA contains no discovered semantic dispatcher for `startui_defer`, `next_action` or task metadata.

### Relation
`PlatformPendingTask` is connected to startup/backlog/context delivery, not to StartUI execution.

### Method
Call-site coverage over the complete relevant tree is now stronger evidence than symbol-presence inspection.

### Routing
After independent consumer verification closes, return to source/provenance archaeology of the first upstream producer edge. Do not rotate directly to implementation.

## WHAT REMAINS UNPROVEN

- exact natural StartUI DEFER producer call-site and its complete runtime ownership;
- whether an existing model/metadata field can represent semantic StartUI intent;
- whether the producer can reuse `PlatformPendingQueue` without schema changes;
- any semantic consumer after a producer exists;
- trigger/wake;
- post-DEFER re-observation;
- policy recomputation;
- reauthorization;
- automatic UI resume;
- cross-AI runtime ingestion and changed next decision.

END OF RECORD.
