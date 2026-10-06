## SOURCE ADDENDUM — DECISION-CONTEXT RECONSTRUCTION BOUNDARY

Subsequent direct inspection of executable baseline `e46d830...` identified an important source-level boundary after the RQ10 live observation.

`AdaptiveTaskOrchestrator._refresh_session_metadata()` rebuilds a DecisionContext using the supplied PerceptionSnapshot, and `_refresh_perception_snapshot()` returns a copy of that snapshot with the reconstructed DecisionContext.

Thus the normal orchestration path does not simply pass the exact pre-governance DecisionContext object unchanged through later stages. A runtime experiment must compare the evidence before and after this reconstruction.

This refines, but does not close, the RQ10 open edge.

# CHAT-ARCH-2026-10-06-066 — UAAL-RQ10 MCP → PERCEPTION SNAPSHOT RECONCILIATION

## TYPE

Canonical reconciliation / runtime evidence / symbiosis / routing.

## OBJECTIVE

Close the first open edge inherited from RQ09:

`fresh persisted producer snapshot → fresh MCP bootstrap/consumer → exact consumer WorldModel snapshot → PerceptionSnapshot`

while preserving the distinction between:

- producer snapshot identity;
- MCP startup replacement;
- PerceptionSnapshot identity/provenance;
- DecisionContext construction inside the PerceptionSnapshot;
- observed runtime fact versus source-consistent inference.

## EXECUTION

- Target actor: CODEX.
- Code-bearing baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`.
- Candidate MCP workspace: same candidate worktree used for RQ09/RQ10.
- One fresh MCP candidate process was started.
- Fresh RQ10 authorization: explicitly granted for this MCP-startup observation.
- No production source change was reported.
- The result was stopped immediately after the single `cognitive_frame_translate` observation.

## REPORTED RUNTIME OBSERVATION

The following is the Codex execution result supplied to the coordinator in chat. The Codex session PID/start metadata was not included, so freshness of the Codex client session itself is not independently established by this report.

1. `latest.json` immediately before MCP startup and the WorldModel snapshot in memory at the end of bootstrap both identified:
   `4350a718-4ec6-420c-a3bb-8062eb70f376`.

2. During bootstrap, `request_refresh` returned the same snapshot ID.

3. After that, the monitor initiated a full scan with:
   - reason: `role_router_ready`
   - resulting snapshot:
     `fa38d348-33d1-4530-99e1-9b2e2a3f7c4a`

4. The single `cognitive_frame_translate` invocation began while that scan was in progress.

5. The returned `PerceptionSnapshot` incorporated the new WorldModel snapshot:
   `fa38d348-33d1-4530-99e1-9b2e2a3f7c4a`.

6. After translation completed, both in-memory WorldModel state and `latest.json` matched:
   `fa38d348-33d1-4530-99e1-9b2e2a3f7c4a`.

7. The MCP candidate process was reported as PID `21668`.

## DIRECT SOURCE VERIFICATION AT E46

Independent GitHub source inspection of the exact code-bearing baseline confirmed:

- `infra/mcp/server.py::cognitive_frame_translate` obtains the current `WorldModelService` snapshot for runtime signals, constructs an `InferenceRequest` and `TaskIntent`, calls `TaskContextAssembler.build_perception_snapshot(...)`, and then passes that PerceptionSnapshot to the CognitiveFrameTranslator.
- `services/adaptive/task_context_assembler.py::build_perception_snapshot` creates the `DecisionContext` object inside the returned `PerceptionSnapshot`.
- `TaskContextAssembler._world_model()` first reads `current_model()` and then requests a refresh for the normal perception path. Therefore a translation invocation can observe a WorldModel state that changes during the same call.
- `services/adaptive/adaptive_task_orchestrator.py::build_decision_context_preview()` constructs a PerceptionSnapshot through the same context assembler, injects the optional synaptic result into its embedded DecisionContext, and returns `perception.decision_context`.
- `infra/mcp/server.py::orchestrator_preview` exposes that preview path as an MCP tool explicitly documented as non-executing.

## FACT / INFERENCE / ASSUMPTION

### FACTS

- RQ10 observed a fresh MCP bootstrap whose initial in-memory snapshot matched the persisted snapshot present at startup.
- A later monitor full scan produced a different snapshot ID.
- The single `cognitive_frame_translate` call returned a PerceptionSnapshot containing that later snapshot ID.
- Final in-memory and persisted WorldModel state matched that later ID.
- The exact code baseline contains the source paths described above.

### INFERENCES

- The PerceptionSnapshot observed by RQ10 was produced after, or while observing, the monitor-generated replacement state rather than preserving the original RQ09 producer snapshot unchanged.
- The runtime path is source-consistent with a bootstrap/monitor refresh replacing the persisted snapshot before or during translation.
- The observed runtime chain establishes live MCP → PerceptionSnapshot observability, but it does not independently prove that the monitor full scan caused every subsequent state transition without an event/call-stack attribution trace.

### ASSUMPTIONS

- None beyond the explicit limitation that Codex session freshness/identity was not independently established from the returned report.

## WHAT RQ10 CLOSES

RQ10 closes the previously unobserved live handoff at the PerceptionSnapshot boundary in the following bounded sense:

`fresh MCP bootstrap state → live cognitive_frame_translate → observed PerceptionSnapshot`

It also establishes that persistence after the monitor-produced replacement matched the resulting in-memory state.

## WHAT RQ10 DOES NOT CLOSE

RQ10 does NOT establish:

- that the original RQ09 producer snapshot survived MCP bootstrap unchanged;
- that the monitor replacement was causally attributed with a full event/call-stack trace;
- that the exact same PerceptionSnapshot object is passed to a downstream decision consumer;
- live `PerceptionSnapshot → DecisionContext` propagation into the normal downstream orchestrator/decision path;
- governance/external dispatch/causal learning as live consequences.

Important invariant:

`new PerceptionSnapshot != proof of preservation of the earlier producer snapshot`

and

`PerceptionSnapshot contains DecisionContext != proof that a downstream consumer used that exact live snapshot`.

## CURRENT FIRST OPEN EDGE

The domain frontier advances to:

`live PerceptionSnapshot / embedded DecisionContext → live downstream DecisionContext consumer`

More concretely, the narrowest currently attributable edge is:

`MCP cognitive_frame_translate / PerceptionSnapshot → existing orchestrator decision-context preview path`

The next question is NOT whether a DecisionContext type exists. It does.

The next question is whether the existing runtime consumer path can receive a freshly constructed live DecisionContext whose WorldModel evidence can be correlated to the PerceptionSnapshot used to construct it.

## NEXT MINIMUM EXPERIMENT

Use the existing `orchestrator_preview` MCP surface, because source shows it is intended to preview the orchestrator decision without executing the selected route.

Required capture:

1. persisted WorldModel snapshot ID immediately before invocation;
2. all WorldModel refresh/request events during the call, with reason, full flag, resulting snapshot ID and attributable call-site if available;
3. the returned DecisionContext payload;
4. WorldModel/Perception provenance fields carried into that payload;
5. correlation of the returned DecisionContext's embedded/derived WorldModel state with the actual live snapshot identity;
6. confirmation that no external execution is triggered;
7. stop at the first identity discontinuity.

Do not use a synthetic PerceptionSnapshot or bypass the existing TaskContextAssembler.
Do not modify production source merely to make the correlation easier.
Ephemeral runtime-only instrumentation is acceptable if existing read-only surfaces cannot expose identity, provided behavior is not changed and nothing is committed.

## AUTHORIZATION BOUNDARY

RQ10 authorization is consumed.

A new MCP invocation can refresh/write `latest.json`, so the next runtime observation requires a fresh explicit human authorization unless the operator independently proves the chosen invocation cannot mutate persisted WorldModel state.

Static/source archaeology may proceed without that runtime authorization.

## ROUTING DELTA

- Current technical actor remains CODEX by capability-fit: repository archaeology + MCP runtime attribution + minimal read-only instrumentation.
- ChatGPT remains coordinator/synthesizer/reconciler/writeback.
- Sonnet/Claude is not yet the next actor because the current uncertainty is still a concrete attributable runtime seam rather than an independent forensic scoring question.
- Devin is not indicated because the frontier is not currently a Windows production-lifecycle failure; it is MCP/runtime attribution on the known candidate path.

## KNOWLEDGE DELTA

### KNOWLEDGE

A fresh MCP process can begin from a persisted WorldModel snapshot, then observe a later monitor-produced snapshot during bootstrap, and `cognitive_frame_translate` can return a PerceptionSnapshot reflecting that later state with final persistence matching it.

### METHOD

For WorldModel→Perception experiments, identity must be sampled at the exact call boundaries because bootstrap/monitor refresh can replace persisted state while the observation is in flight.

### RELATION

The canonical identity chain now requires temporal event capture:

`persisted ID before bootstrap → bootstrap refresh result → monitor replacement ID → PerceptionSnapshot WorldModel ID → persisted ID after translation`

### ROUTING

Stop RQ10 at the PerceptionSnapshot boundary and move the first open edge downstream to the existing DecisionContext/orchestrator preview consumer. Do not reopen RQ09 producer scanning.

## NEGATIVE KNOWLEDGE PRESERVED

RQ10 does not prove universal environmental intelligence, autonomous learning, autonomous wake/reauthorization, external-AI ingestion, causal symbiosis, or consciousness.

---
