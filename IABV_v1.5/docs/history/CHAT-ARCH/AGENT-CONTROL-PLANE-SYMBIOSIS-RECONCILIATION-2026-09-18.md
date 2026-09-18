# IABV — Agent Control Plane / Symbiosis Reconciliation — 2026-09-18

## Scope
Reconciliación del estado actual de main contra la investigación 2026 sobre Agent Control Plane, agentic engineering, harness/context engineering, multi-agent orchestration, governance, handoffs, verification and observability.

Canonical rule:
DEFINED → WIRED → INVOKED → OBSERVED → CAUSED
IDEA → DESIGN → CODE → WIRED → TESTED → PRODUCTION_PATH → RUNTIME_OBSERVED → INDEPENDENTLY_VERIFIED → CAUSAL_EFFECT → LEARNED_REUSED

## Current repository state
Repository: jhonf463r/Python
Branch: main
Reconciled HEAD: 66a30fcf3ae1d30364eb4f5b860f95cebde38e81

The current AGENTS.md establishes a single-authority orchestration model with AdaptiveTaskOrchestrator as decision/execution authority; AutonomyCycleService + PlatformPendingQueue as queue/state substrate; TaskContextAssembler, WorldModelSnapshot, EnvironmentSelfModel and PortableContext; governance and approval gates; ToolRegistry/ToolCard, LocalRoleRouter and SynapticRouter; TaskOutcomeRecorder, ExperimentLab, StrategySelector and AdaptiveWeightLayer; OperationalSelfExaminationService and AutonomousValidationCycleService; external execution through AutonomousEvolutionService.plan_or_execute / ToolTeachService; and AgentHandoffTrail for append-only handoff evidence.

## What is already materially present

- Objective/work state: ObjectiveNode.objective_id, GoalEngine, ControlMasterService.current_work_queue(), PlatformPendingQueue.
- Canonical context: TaskContextAssembler plus world/self state, evidence, memory and portable context.
- Governance: AutonomyGovernancePolicy, approval gates and worker-health gating.
- Capability registry/routing: ToolRegistry/ToolCard, LocalRoleRouter and SynapticRouter.
- External execution boundary: AutonomousEvolutionService.plan_or_execute() can reach ToolTeachService.execute_external_consultation().
- Proactive autonomy: G1 sync-pulse action_ready proposals can reach AdaptiveTaskOrchestrator.auto_execute_from_sync_pulse().
- Cross-agent handoff evidence: AgentHandoffRecord / AgentHandoffTrail persist executor, auditor, repository and synchronization state.
- Learning substrate: TaskOutcomeRecorder, ExperimentLab, StrategySelector and AdaptiveWeightLayer are wired into the application.
- Observability: RuntimeAuditTracer and DecisionAuditTrail provide structured runtime/decision evidence.

## What has strong test-level support but is not end-to-end causal proof

tests/test_e28_winner_to_delegation_trace.py documents and tests:
SynapticRouter.decide() → selected_assistant_kind=devin → assistant_kind→tool_id mapping → ToolCard → DevinApiToolAdapter boundary.

This is evidence of selector-to-adapter reachability in the tested path. It is not proof that a live external Devin session performed the requested work because of IABV context, nor that the resulting world state changed and caused the next decision.

## Unresolved frontier

1. Generic queue activation: the canonical queue exists and feeds state/context, but a general autonomous consumer that turns arbitrary actionable PlatformPendingTask items into the executive decision loop is not directly proven.
2. I2 real external closure: objective → context → governance → selection → task packet → real external run → observed result → independent verification → post-state → next decision is not yet proven as one live causal episode.
3. Cross-agent continuity: handoff evidence exists, but automatic A→B continuation without human transport is not independently demonstrated end-to-end.
4. Verification closure: outcome recording and automatic replan exist in parts of the orchestrator, but a universal mandatory external-result→independent-verification→authoritative-post-state route is not yet proven across all external paths.
5. Next-decision causality: internal learning/selector experiments provide selector-level evidence, but persistence != causal learning; score change != decision change; decision change != world outcome remain active negative knowledge.
6. Provenance normalization: current traces contain useful task/session/route/interaction/dispatch/build information, but there is not yet one homogeneous runtime contract spanning workflow, agent-run, tool-call, span and causal provenance fields.
7. L5 closure: current canonical state keeps L5 below full closure until the remote runtime artifact is reconciled byte-for-byte and the independent audit is complete.

## Symbiosis stages

I0 — manual transport reduction: substantially implemented structurally; live workflow proof remains useful.
I1 — IABV selects and delegates: strong structural/test support; live invocation from the IABV executive path still needs runtime evidence.
I2 — delegate → receive → verify → learn/replan → delegate next: CANDIDATE / NOT CLOSED.

## Current task

Issue #459: I2 — Cierre causal de simbiosis IABV con agentes externos

Required evidence:
human objective → canonical state/context → governance → capability selection → task packet → real external run → runtime observation → independent verification → post-state → knowledge delta → next decision

Sub-work:
- I2.1 — connect the canonical actionable work queue to the existing orchestrator without a second executor/brain.
- I2.2 — prove a real external-agent run initiated from the IABV executive path, including identity and delivered context.
- I2.3 — prove independent verification and post-state reconciliation on the tested route.
- I2.4 — prove verified post-state changes the next IABV decision/action.
- I2.5 — prove A→B continuity without human context reconstruction.
- I2.6 — normalize runtime provenance against OpenTelemetry GenAI concepts without replacing IABV audit authority.
- I2.7 — measure human coordination reduction versus manual baseline.
- L5.Closure — reconcile remote runtime artifact and independent audit before promotion.

## Implementation rule

Do not create another orchestrator, router, memory system or symbiosis brain.
Prefer composition of existing ControlMaster / AutonomyCycleService → AdaptiveTaskOrchestrator → existing external execution boundary → verification/outcome → existing learning/portable-context machinery.
The human remains authoritative for objectives, permissions, contradictions, destructive/high-risk actions and escalation.

## Negative knowledge preserved

- Code exists != capability proven.
- Green tests != production runtime proof.
- Direct adapter invocation != production routing proof.
- Persistence != learning.
- Score change != decision change.
- Decision change != behavior change.
- Behavior change != world outcome.
- Handoff record != automatic handoff.
- Observability != causality.
- Historical report != current repository state.

## Exit criterion

I2 may be promoted only after one independently auditable live episode shows the full causal chain and the evidence can be reconstructed from repository/runtime artifacts without relying on an agent narrative report alone.