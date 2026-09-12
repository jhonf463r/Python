# IABV v1.5 — Executive Loop Traceability / 2026-09-12

STATUS=CANONICAL_OPERATIONAL_KNOWLEDGE
PURPOSE=Preserve the current causal-traceability state of the IABV → Devin acceleration experiment so a future chat can resume without reconstructing the analysis manually.

## 1. SOURCE REPORT / AUDIT CUT

The attached Devin inspection report identified this audited cut:

- Branch reported by Devin: `devin/p040-runtime-progress-observability`
- Commit reported by Devin: `a5eae19aed08a7e1b9f46e816f8fadf290bc615d`
- Runtime target reported: `C:\Python\IABV_v1.5`
- Report status: clean / declared state matched its audited effective state.

IMPORTANT PROVENANCE RECONCILIATION:
The remote branch `devin/p040-runtime-progress-observability` currently points to `083eed36f59b9ee6cf7282e8e362deb48a075779`, not `a5eae19...`.
Therefore `a5eae19...` is preserved here as the **Devin audit cut**, while `083eed...` is the current remote branch tip. Do not silently substitute one for the other.

## 2. EXISTING ORGANS IDENTIFIED IN THE AUDIT

The audited stack contains:

- `AutonomyCycleService` — queue bridge, resume hints, capability seeding, startup summary.
- `AdaptiveTaskOrchestrator` — request handling, resume context, automatic/coordinated execution paths.
- `ControlMasterService` — current state and unified work queue.
- `PortableContextService` — portable context package.
- `SessionStartBriefingService` — external-agent briefing/session creation/delivery.
- `DevinApiToolAdapter` — Devin API execution/transport.
- `AutonomousValidationCycleService` — monitoring loop and automatic validation/proposal execution paths.
- `TaskOutcomeRecorder` — result persistence and ControlMaster propagation.
- `AutonomousEvolutionService` — `plan_or_execute` external-consultation boundary.
- `ToolTeachService` — external-tool execution path.

Additional current repository evidence establishes that `SynapticRouter`, `GoalEngine`, `TaskContextAssembler`, `AutonomyGovernancePolicy`, `CapabilityReadinessService`, `AdaptiveWeightLayer`, and `StrategySelector` also already participate in the broader orchestration/routing substrate.

## 3. AUDITED CAUSAL CHAIN AT THE A5E CUT

Reported chain:

```text
HUMAN OBJECTIVE
→ ControlCenterViewModel.sendChat()
→ AdaptiveTaskOrchestrator.handle_request()
→ LocalRoleRouter.build_decision_from_intent()
→ TaskContextAssembler.build_perception_snapshot()
→ SynapticRouter.decide()
→ AutonomousEvolutionService.plan_or_execute()
→ DevinApiToolAdapter.run()
→ RESULT
→ TaskOutcomeRecorder.record()
→ UPDATED STATE
→ NO AUTOMATIC NEXT DECISION PROVEN
```

The key evidence boundary is not existence. The question is whether the downstream transitions are automatically invoked and causally responsible for the next state/decision.

## 4. FOCUS OF THE MISSING CAUSAL EDGE

The Devin report identified:

```text
ControlMasterService.current_work_queue()
    → automatic consumer
    → automatic delegation decision
    → SessionStartBriefingService.brief_new_session()
    → automatic result processing
    → changed next decision
```

as NOT PROVEN.

The report therefore identified the missing executive continuity as:

```text
QUEUE / STATE
→ DECISION
→ DELEGATION
→ OBSERVATION
→ VERIFICATION
→ POST-STATE
→ NEXT DECISION
```

## 5. CRITICAL RECONCILIATION WITH CURRENT CODE

Do NOT freeze the first report's proposed implementation as architectural truth.

Current repository code already states:

- `AutonomyCycleService` is a state substrate and explicitly leaves autonomous decisions to `AdaptiveTaskOrchestrator`.
- `AdaptiveTaskOrchestrator` already owns operational orchestration and contains automatic/coordinated execution paths.
- `AutonomousEvolutionService.plan_or_execute()` already contains the external consultation decision/execution boundary.
- `SessionStartBriefingService` already builds a briefing from `PortableContextService` and exposes injected session/message transport.
- `SynapticRouter` is currently descriptive and does not own operational routing.

Therefore the correct unresolved question is **not** “which new delegation service should be created?” but:

> Which existing activation/feedback edge is actually missing, and which existing organ already owns it?

The earlier proposal to extend `AutonomousValidationCycleService._monitor_loop()` is a **hypothesis**, not yet proven to be the correct owner. Before changing it, trace whether `AdaptiveTaskOrchestrator`, its existing `auto_execute_*` paths, or another already-wired lifecycle is the smallest legitimate owner.

## 6. FIRST BROKEN EDGE — CURRENT STATUS

At the A5E audit cut:

`ControlMasterService.current_work_queue()` was reported as `DEFINED + WIRED + NOT_INVOKED` for automatic queue consumption.

CURRENT STATUS after repository reconciliation:

`QUEUE → AUTOMATIC EXECUTIVE DECISION` = **NOT PROVEN**

The exact first broken edge still requires code-level/runtime discrimination on the current target. The historical statement “no consumer exists” must not be generalized to mean “no automatic execution infrastructure exists anywhere,” because current `AdaptiveTaskOrchestrator` and `AutonomousValidationCycleService` already contain automatic execution mechanisms.

## 7. MINIMAL-DYNAMISM PRINCIPLE

The intended acceleration architecture is:

```text
human objective
→ active canonical context
→ current self/world state
→ uncertainty / evidence gap
→ existing IABV decision machinery
→ capability/actor selection
→ task packet
→ Devin execution
→ observation
→ independent verification
→ state delta
→ next decision
```

Only the first causal edge that blocks this loop should be modified.

No new brain, universal engine, parallel memory, or competing router should be introduced unless the existing contracts are proven insufficient.

## 8. CAUSAL TRACE MODEL

For each important transition preserve:

```text
DEFINED
WIRED
INVOKED
OBSERVED
CAUSED
```

And for epistemic status preserve:

```text
IDEA
DESIGN
CODE
WIRED
TESTED
PRODUCTION_PATH
RUNTIME_OBSERVED
INDEPENDENTLY_VERIFIED
CAUSAL_EFFECT
LEARNED_REUSED
```

Permanent boundaries:

- code exists != capability proven
- wired != invoked
- invoked != observed
- observed != caused
- test passes != runtime proof
- context exists != decision influence
- external result != truth
- persistence != learning
- repository target != runtime target until proven

## 9. EXPERIMENTAL SUCCESS CONDITION

The acceleration experiment succeeds only when a real development objective can be supplied once by the human and the following becomes causally observable:

```text
HUMAN OBJECTIVE
→ IABV CURRENT STATE / RELEVANT MEMORY
→ ACTIVE UNCERTAINTY
→ IABV DECISION
→ DEVIN SELECTION / APPROVAL
→ DEVIN TASK PACKET
→ DEVIN ACTION
→ RESULT
→ OBSERVATION
→ INDEPENDENT VERIFICATION
→ STATE_AFTER
→ KNOWLEDGE_DELTA
→ NEXT DECISION
```

The strategic metric is reduction of routine manual coordination, especially manual prompt transport and repeated context reconstruction.

Human intervention remains appropriate for real decision boundaries, permissions, contradictions, security constraints and insufficient evidence.

## 10. LEARNING CLAIM

No learning claim is valid unless:

```text
experience
→ provenance
→ interpretation
→ persistence
→ later retrieval
→ changed decision/action
→ independent observation of change
```

## 11. CURRENT NON-PROVEN ITEMS

- automatic queue → decision closure;
- automatic decision → Devin closure;
- Devin → verified post-state automatic closure;
- post-state → changed next decision;
- causal context influence on a real external-agent action;
- second-agent continuation without manual reconstruction;
- persistence producing later route/strategy change.

## 12. NEXT INVESTIGATION ORDER

1. Reconcile the current branch tip against the A5E audit cut.
2. Trace existing automatic execution paths before modifying anything.
3. Identify the first truly missing causal edge.
4. Select the smallest existing owner for that edge.
5. Implement only that edge if code change is justified.
6. Add discriminating tests.
7. Execute a real runtime experiment.
8. Independently audit the result.
9. Persist the resulting knowledge delta and update future routing.

## 13. NEXT-CHAT STARTER

A new chat with this objective should begin by activating:

- `CURRENT-STATE.md`
- `MEMORY-OPERATING-PROTOCOL.md`
- `CONTEXT-INDEX.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`
- `METACOGNITIVE-DEDUCTION-2026-09-12.md`
- this file: `EXECUTIVE-LOOP-TRACEABILITY-2026-09-12.md`

Then reconcile all historical claims against the exact active branch/commit/runtime before choosing a task.

## 14. STRATEGIC PURPOSE

The development inflection is not merely “make IABV autonomous.”

The target is to remove the human from being the routine transport layer between IABV's own cognition/state and external implementation agents.

IABV should progressively absorb:

```text
context retrieval
→ evidence selection
→ task packaging
→ actor selection
→ delegated execution
→ observation
→ verification routing
→ state reconciliation
→ memory writeback
→ next-step recommendation
```

without weakening governance, provenance, verification or causal accountability.
