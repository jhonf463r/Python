# IABV v1.5 — DEVELOPMENT CONTROL TOWER
## Estado global, tracks, gates, pendientes y routing — 2026-09-21

**Purpose:** mapa operativo global para futuros chats. Reconciliación entre intención estratégica y evidencia conocida. Requiere fresh check de branch/runtime antes de claims operativos.

## Latest target_scope candidate checkpoint — 2026-10-22

Sonnet 4.6 returned an Owner-supplied static-review PASS for the candidate fragment: the open consult_-prefix exception was removed and unknown consult scopes remain fail-closed. This does not mean tests passed or the live server adopted the candidate. Current routing, findings, exact refs and start-of-next-chat instructions are captured in [post-Sonnet target_scope next-chat handoff](./CHAT-ARCH-2026-10-22-post-sonnet-target-scope-next-chat-handoff.md) and [candidate review record](./CHAT-ARCH-2026-10-22-candidate-target-scope-repaired-review.md).

At the pre-Tower-update checkpoint, main was 262461e5b35aa1aeae3441e9be33434c96a21589; compare against fix/iabv-operational-block-target-scope-repair-20261022 returned diverged, ahead_by=1, behind_by=4, merge base e61c5043bbdd8ea536ed5c9e642d80ff228ee897. The branch has not been merged or rebased. Treat these counts as a snapshot before this document-only update and refresh before any integration decision.

CURRENT-STATE.md remains the sole routing authority. The one active task is M1 — IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE. Tests=NOT_RUN; local source read=NOT_RUN; governance=KEEP_BLOCKED; implementation=NOT_AUTHORIZED; bridge=BRIDGE_NOT_READY; real transport=NOT_RUN; local worktree=UNTOUCHED.


## 2026-10-22 ADHD-aware focus and space-time project coordination (documented method; runtime not proven)

Detailed owner-directed protocol: [ADHD-aware project coordination and space-time focus](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md).

The Owner explicitly reports ADHD and asks for structured project coordination because useful new ideas arise rapidly and can divert attention from the primary objective. Treat this as an owner-directed interaction-design requirement, not as a limitation to infer beyond what the Owner stated. Capture new ideas in a persistent inbox/parking lot; do not switch the active task automatically. Maintain one primary outcome, one active task, one acceptance criterion and one next action. Interrupt only for immediate safety or a dependency that invalidates the active work; otherwise triage the idea as direct dependency, later, duplicate/resolved, or out of scope. Give a brief progress dashboard and distinguish queued/running/blocked/completed-unverified/verified using evidence, not narration.

The existing DEVELOPMENT CONTROL TOWER and goal-lock/anti-drift protocol are the foundation; this addendum does not create a competing route or claim the runtime coordinator is implemented. The sole active task remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`; preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `LOCAL_SOURCE_READ=NOT_RUN`, `REAL_TRANSPORT=NOT_RUN`, `LOCAL_WORKTREE=UNTOUCHED`. The latest IABV response repeated a broad scan instead of the stop-and-report-only request; containment and all claimed mutations remain unverified. Do not repeat the scan, pull/clean/reset, alter GPU/models/credentials, or attempt improvised rollback.

---

## Working agreement: owner–coordinator operating contract — 2026-10-22

The full operating rules are maintained in [the canonical ADHD-aware project coordination protocol, section 11](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md). Use this Tower as the global dashboard and idea parking lot; use [CURRENT-STATE.md](./CURRENT-STATE.md) for the one active task and next actor. Never create a competing active-task source. New ideas must be captured and triaged, not dropped or automatically promoted. Progress is evidence-backed state change, not narration or invented percentages. Known failed routes must not be repeated unless a named precondition changes.

Episode-level handoff for the 2026-10-22 chat: [reality-aligned bridge continuity handoff](./CHAT-ARCH-2026-10-22-coordinator-reality-aligned-bridge-continuity-handoff.md). It records the Owner's explicit expectation that every idea be persisted, that documentary progress is distinguished from operational readiness, and that a new chat continue from evidence rather than restart.

## 0. LIVE PROJECT FOCUS DASHBOARD — 2026-10-22

This block is the current operational projection of this Tower. The top snapshot in `CURRENT-STATE.md` remains the sole actor-routing authority.

```
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
CURRENT_PHASE=M1_GOVERNED_SCOPED_READ_ROUTE
ACTIVE_TASK_ID=M1
ACTIVE_TASK=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
CURRENT_STATUS=BLOCKED_WAITING_FOR_SUPPORTED_AUTHORITY_OR_ROUTE
SESSION_EXPOSED_SUPPORTED_ADMIN_READ_TOOL=NOT_FOUND
GLOBAL_ROUTE_EXISTENCE=UNRESOLVED
NEXT_ACTOR=OPENCODE_EXISTING_CONFIGURED_SESSION_IF_AVAILABLE
NEXT_SINGLE_ACTION=Send complete successor v0.2 text inline to the same OpenCode session for one bounded documentary review; no local read, alternate reader, implementation, tests, builds or launch
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

### Latest bounded M1 surface-check delta — 2026-10-22

The Owner-supplied builder-grant draft is now adjudicated DESIGN_VERDICT=PASS_WITH_REPAIRS; see the M1 follow-up for required repairs and the exact OpenCode review prompt. The Owner has supplied the predecessor review PASS_WITH_REPAIRS for requirements-baseline quality only; its five HIGH blockers plus BA-07/BA-08 MEDIUM additions are preserved in the independent-review record. Successor v0.2 explicitly marks critical mechanisms not implementable on current evidence and BA-05 AUTHORITY_UNAVAILABLE. The earlier 404 attempt is historical. Next is a review of the complete successor text inline to the same OpenCode session, not a different reader or URL probe. This grant remains PROPOSED_NOT_IMPLEMENTED and is not a substitute for M1's supported scoped-read route. The current ChatGPT callable-tool catalogue exposes no IABV-local governance/read-decision action, and the current content of issue [#470](https://github.com/jhonf463r/Python/issues/470) identifies no executable route or responsible operator. Full evidence: [governance-surface inventory follow-up](./CHAT-ARCH-2026-10-22-governance-surface-inventory-followup.md). Record `NOT_FOUND` only for the surfaces actually examined; keep `GLOBAL_ROUTE_EXISTENCE=UNRESOLVED`. The task, governance gate and no-bypass constraints do not change.

### Milestones

- **M0 — Focus/continuity method:** the ADHD-aware idea-inbox and one-active-task protocol is documented and indexed. Runtime activation remains `NOT_PROVEN`.
- **M1 — Active:** identify a supported governance-owned scoped-read route. The ordinary IABV general-chat responses have repeated broad auto-scans instead of supplying the required route decision; do not repeat that path as a workaround.
- **M2 — Dependent / not run:** after M1 is verified, trace Codex executor registration, invocation, consumer and only permitted non-secret effective policy.
- **M3 — Dependent / not run:** through the same legitimate route, trace IABV→Ollama startup/connect/model-provider selection and whether local inference is required.
- **M4 — Pending dependencies:** reconcile one bounded bridge path/contract map from actual source edges and receipts.
- **M5/M6 — Not authorized / not run:** implementation and end-to-end bridge validation each require separate authorization and satisfaction of their gates.

### Idea inbox / parking lot

Ideas are captured here rather than silently replacing M1. This is a triage lane, not an execution queue.

| ID | Idea / observation | Disposition | Re-entry condition |
|---|---|---|---|
| IDEA-001 | ADHD-aware space-time coordinator: persist ideas, focus one active task and expose verifiable progress | `DOCUMENTED_METHOD`; runtime capability not proven | Revisit implementation only through a separately authorized scope |
| IDEA-002 | Reduce unnecessary Ollama/model startup, RAM footprint and investigate lazy/local-vs-remote inference | `PARKED` | M1 opens legitimate static source trace; use existing evidence first |
| IDEA-003 | Validate the inferred claim that Ollama is winning for `general` and clarify `probe_consumed` | `PARKED` | Existing correlated IDs, metrics and receipts are available through an authorized path; no broad scan |
| IDEA-004 | Reconcile the broad auto-scan's claimed GPU/model/credential mutations and the reported 282 dirty source files | `OWNER_REPORTED / UNVERIFIED`; preserve worktree | A safe, separately authorized recovery/verification plan; no blind pull/reset/cleanup/reload |
| IDEA-005 | Reality-aligned coordination: keep moving on authorized documentary edges without implying operational readiness; repair stale next-actor pointers and verify cross-chat reuse | `DOCUMENTED_PROCESS_CORRECTION`; runtime reuse unproven | At next chat startup, verify CURRENT-STATE is restored, stale routing is not acted on, the same broad IABV route is not repeated, and parked ideas remain parked |

### Progress rules for this human–AI project

The Owner has explicitly asked for support managing frequent new ideas without losing the north star. Acknowledge and capture an idea, classify it as immediate safety/dependency, direct dependency, parked, duplicate/resolved, or out of scope, then return to M1 unless the Owner explicitly changes priorities. Do not treat the Owner's new idea as a failure or imply the Owner should suppress ideas.

Every work checkpoint must report: objective, task ID, status, actual delta since last checkpoint, evidence/provenance, blocker, one next action and actor, acceptance criterion, and pointer to parked ideas. Use `QUEUED`, `RUNNING`, `BLOCKED`, `WAITING_OWNER`, `COMPLETED_UNVERIFIED`, `VERIFIED`, `FAILED`, or `PARKED`; do not declare running/completed/verified from model narration alone. Do not invent percentage progress.

This Dashboard supplements the history below and does not replace or reorder the active route in `CURRENT-STATE.md`.

---

## 1. GLOBAL OBJECTIVE
Construir IABV como un control plane cognitivo y de desarrollo artificial observable y gobernado que use progresivamente sus propios órganos para observarse, detectar déficits, seleccionar experimentos y capacidades, ejecutar/delegar, verificar, aprender y causar decisiones posteriores, reduciendo la coordinación humana rutinaria.

North Star:
`verified experience → reusable knowledge → future decision change → lower routine human coordination → more efficient experimentation → new verified capability`

“Exponencial” es una hipótesis de aceleración longitudinal, no un estado actual.

## 2. EXISTING SUBSTRATE
Self/world observation, organism state, self-code analysis, SelfAudit, OSES, ToolCard/ToolRegistry, CapabilityReadiness, ToolTeach, ExperimentLab, SandboxExperimentService, StrategySelector, AdaptiveWeightLayer, TaskOutcomeRecorder, ReproducibilityValidationService, PortableContext, audit/provenance, Evolution/Autonomy services y resource scanning/ranking ya existen como piezas relevantes.

Regla:
`organ exists ≠ organ integrated ≠ organ causally useful for next cycle`

## 3. PROVEN / CLOSED IN CURRENT CANONICAL RECORD
R3 production adapter boundary = closed as technical production-path gate.
G3 persistence → fresh reload → learning-state mutation = demonstrated, but with always-authorized mock; not authority proof.
L5 selector-level causal learning = PROVEN after independent forensic audit. Do not reopen without contradictory evidence.
P040 UI → sendChat → interaction → dispatch → worker → terminal → ExperimentRun/Recommendation = PROVEN in canonical live record.
I0 assistant↔tool/resource-resolution seam = VERIFIED EFFECTIVE at 4710a668541225ffe3b9d1335d31bb5da8b1e685.
I0 M3 = CLOSED at unit/mutation level; Windows runtime remains open.

## 4. OPERATIONAL SYMBIOSIS STILL OPEN
`adapter.run() → real authorization → transport → external effect → observation → independent verification`

I0 full connection = NOT PROVEN.
I1 automatic round trip = NOT PROVEN.
I2 dynamic closed loop = NOT PROVEN.
Real external-agent cognitive influence = NOT PROVEN.
P0-B legitimate authority/OS enforcement = separate open security boundary.

Do not transfer L5 evidence to I0/I1/I2.

## 5. SCIENTIFIC ORGAN — FORENSIC STATUS
Audit snapshot: `f0c98ca1af756273f14a7fae65fafa9bd69a3a30`.

Scientific machinery is substantial and distributed. Observed functions include research-gap discovery, hypothesis/design, baseline/candidate experimentation, ExperimentRun/outcome capture, scientific proxies, recommendations, calibration and history-based reproducibility estimation.

Still unclear or absent in the audited path: dedicated pre-outcome Prediction, explicit falsification/qualification, canonical scientific model/theory update owner, fresh independent reproduction path, and automatic outcome/recommendation → next experiment consumer.

First scientific open causal edge:
`ExperimentRun / ExperimentRecommendation → concrete reader → next hypothesis / next SandboxExperiment`

Required next action: exhaustive repository consumer/reader sweep before any new scientific coordinator.

## 6. SELF-USE / DEVELOPMENT TRACK
Primary strategic frontier:
`IABV-native self-observation → uncertainty → first open causal edge → smallest discriminating experiment`

Development chain:
`deficit → hypothesis → variation → sandbox → independent verification → accepted capability → governed incorporation → reuse → next development decision`

Developmental A/B/C/D distinction:
A = acquisition.
B = recombination.
C = development.
D = generational development/evolution.

Do not promote persistence, module count, automation or long-running adaptation into evidence of C or D.

## 7. AUTONOMY GRADIENT
A0 human transport → A1 continuity → A2 self-diagnosis → A3 experiment selection → A4 governed delegation → A5 automatic verification → A6 causal learning → A7 development → A8 governed construction → A9 lineage → A10 open-ended evolution.

Only demonstrated levels may be marked achieved; higher levels remain hypotheses.

## 8. PRIORITIZED PENDING WORK

### META
1. META-01: IABV-native deep self-assessment preflight.
2. META-02: evidence/provenance contract.
3. META-03: universal change-surface analysis.
4. META-04: observe/mutate separation.
5. META-05: metacognition → memory → experiment → future decision.
6. META-06: longitudinal development-inflection measurement.

### SCIENCE
7. BIO-R11: initial scientific-organ audit = partial; preserve forensic result.
8. BIO-R12: exhaustive ExperimentRun/ExperimentRecommendation reader-consumer sweep.
9. Later: Prediction semantics, falsification/qualification, independent reproduction, scientific model/theory update.

### DEVELOPMENT
10. BIO-R01 minimal substrate.
11. BIO-R02 genotype/phenotype + heredability.
12. BIO-R03 developmental unit from existing organs.
13. BIO-R04 deficit → variation → verified new capability.
14. BIO-R05 lineage + cold restart.
15. BIO-R06 differentiation/transition.
16. BIO-R07 open-ended evolution benchmark.
17. BIO-R08 longitudinal development/human coordination.
18. BIO-R09 governance/sandbox/rollback.
19. BIO-R10 metacognition as developmental engine.

### SYMBIOSIS / I0-I2
20. Secure real Devin credential availability in controlled Windows runtime.
21. Real I0 runtime execution.
22. I1 automatic round trip.
23. I2 dynamic closed loop.
24. L6 behavioral change beyond selector-level L5.
25. L7 broader external-world causal closure.

### SECURITY / PROVENANCE
26. P0-B legitimate authority and OS enforcement.
27. AdaptiveSession typed provenance becoming behaviorally canonical.
28. Preserve direct-parent vs historical-baseline vs cumulative-lineage distinctions.

## 9. DO NOT REOPEN
L5 closure, R3 closure and M3 unit-level causal closure should not be rerun merely to restate them.
Do not repeat the same missing-credential preflight unless the effective runtime prerequisite changed.
Do not treat P040 closure as scientific-loop closure.
Do not treat M3 unit/mutation as Windows runtime closure.

## 10. ROUTING
IABV-native organs = first analyzer for IABV self-state/self-development.
Sonnet = independent forensic/static/runtime audit.
Devin = bounded implementation and Windows runtime.
Codex = difficult/ambiguous technical archaeology or implementation seam.
Opus 5 = genuine architecture/ownership or high-order causal/policy contradiction.
ChatGPT = reconciliation, evidence-boundary definition, smallest discriminating action, adjudication and writeback.

Routing is dynamic: `objective → uncertainty → capability required → actor fit → evidence cost`.

## 11. CURRENT ROUTING — CURRENT-STATE IS AUTHORITATIVE

**Do not execute a stale actor route from the historical scientific-organ audit below.** The only current actor-routing authority is [CURRENT-STATE.md](./CURRENT-STATE.md), whose top snapshot keeps M1 active.

Current task:
```
ACTIVE_TASK_ID=M1
ACTIVE_TASK=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
STATUS=BLOCKED_WAITING_FOR_SUPPORTED_AUTHORITY_OR_ROUTE
NEXT_ACTOR=OWNER_CONTROLLED_IABV_GOVERNANCE_SURFACE_OR_RESPONSIBLE_GOVERNANCE_OPERATOR
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

The current ChatGPT session exposed no callable governance/local-read operation. This bounded result does not prove no administrative route exists outside the session. The next action is to identify the actual supported governance surface/operator and the independent authority required for the applicable block-release decision. Do not repeat the same generic question in the ordinary IABV chat; prior attempts produced broad scans rather than the required decision. Do not bypass the denied reader.

After M1, only through the supported route, the next bounded source trace is (a) Codex executor registration/caller/consumer and whitelisted non-secret effective policy and (b) IABV startup→Ollama lifecycle→provider/model selection. M1 unlocks only that static read; implementation, launches, tests/builds/runtime, candidate merge/adoption and real transport remain separately gated.

See [the reality-aligned chat handoff](./CHAT-ARCH-2026-10-22-coordinator-reality-aligned-bridge-continuity-handoff.md) for provenance, the acceptance criterion, all parked ideas and new-chat startup sequence.

### Historical route — scientific-organ audit (superseded; retain for lineage, do not execute automatically)

The previous version of this Tower assigned **SONNET** an exhaustive repository-wide reader/consumer sweep concerning whether ExperimentRun/ExperimentRecommendation has a downstream consumer that generates/selects the next scientific/developmental experiment. That route is not the active route at this checkpoint. It must not overrule CURRENT-STATE or replace M1 unless CURRENT-STATE explicitly reactivates it. Its old proposed output was:
`producer → representation → all readers → semantic owner → decision consumer → next-experiment path → evidence state`.
The historical handoff is retained to avoid losing work lineage; no new execution of it is authorized by this Tower update.

## 12. PROGRAM SUCCESS CONDITION
Repeated cycles must show:
`verified experience → reusable capability → changed later decision → lower routine human coordination → improved next-cycle efficiency`

Long-term development additionally requires:
`new capability → participation in construction of next capability`

Evidence must outrank narrative at every boundary.

## 13. SOURCE PRECEDENCE
1. Current directly observed runtime/source evidence.
2. Direct GitHub read-back at exact target SHA.
3. Independently verified artifact.
4. Canonical current-state/override.
5. Historical report or implementer claim.

Older current-status entries are historical when a later canonical addendum supersedes them.

## 2026-09-21 SCIENTIFIC CAUSAL REFINEMENT — EXISTING AUTO-EXPERIMENT CHAIN

A deeper current-source reconciliation found that the earlier statement “ExperimentRecommendation has no downstream consumer” is too broad.

Observed current-source chain:

`ExperimentRun → ExperimentLab.record_outcome/run_experiment → ExperimentRecommendation → ToolDiscoveryService/ToolEvolutionMonitor → ToolEvolutionProposal → AutonomousValidationCycleService → SandboxExperimentService.validate_recommendation → ExperimentLab.record_outcome`.

Additionally, `ExperimentRecommendation` is consumed directly by `ToolTeachService._preferred_external_tool_id()` and can change external assistant routing.

This establishes **CODE/WIRED/INVOKED paths toward later decisions and later sandbox experiments**.

It does NOT yet prove the stronger causal claim:

`different scientific outcome → different next hypothesis/experiment`

The existing `ToolEvolutionMonitor._proposal_for_subject()` derives proposals from grouped historical runs, profiles, ranking and the current recommendation. The next required evidence is therefore a controlled outcome perturbation showing that changing the prior outcome while holding the rest of the subject context constant causes a different next proposal/experiment.

Important distinction:

`automatic next experiment path exists ≠ scientific outcome causally determines next experiment`.

This refinement supersedes only the broad wording of the earlier “no consumer” hypothesis; the forensic snapshot at `f0c98ca1af756273f14a7fae65fafa9bd69a3a30` remains historical evidence.

`BIO-R13` is now the next bounded scientific/developmental experiment: prove or falsify whether changing a prior ExperimentRun outcome, under matched conditions, changes the subsequent ExperimentRecommendation → ToolEvolutionProposal → SandboxExperiment path. Next actor: DEVIN for test-only execution; then SONNET for independent audit. The broader architecture remains unchanged.

## 2026-09-21 BIO-R13 RESULT — BLOCKED, FRONTIER NARROWED

BIO-R13 execution did **not** run CONTROL/TREATMENT. Provenance reported by the executor:
- branch: `devin/i0-external-route-target-fix-2026-09-20`
- HEAD: `f0c98ca1af756273f14a7fae65fafa9bd69a3a30`
- working tree: 5738 untracked files
- runtime: Python 3.14.4 win32
- no test artifact, commit, command execution, negative control or cold restart

Verdict: **BLOCKED**.

The exact blocker is the absence of a practical deterministic runtime harness for `ToolEvolutionMonitor.build_status()` while controlling repository, storage, AdaptiveWeightLayer state and all relevant variables.

This does **not** prove the causal hypothesis false. It does not prove learning absent.

New first question:
`Can outcome→next-proposal causality be isolated at a smaller deterministic seam before building a full runtime harness?`

New next task: **BIO-R14** — audit the narrowest causal seam. First inspect whether existing functions such as grouping, adaptive-weight suggestion, ranking and proposal construction can be exercised with matched synthetic/persisted run sets using the real code path or existing fixtures.
