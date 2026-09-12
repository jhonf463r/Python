# IABV v1.5 — Unresolved / Latent Knowledge Register

## PURPOSE

This file exists for ideas, deductions, questions and strategically important gaps that may never have become tickets or formal decisions.

A future chat must consult this register when the active objective overlaps a listed topic. An item is not an implementation commitment merely because it is recorded here.

A future system-level objective should also distinguish **missing implementation** from **missing integration of already-existing organs**. The latter is often the higher-value frontier because it can increase development velocity without adding architectural mass.

## ACTIVE HIGH-VALUE UNRESOLVED ITEMS

### UK-01 — Real causal external-agent cognition

QUESTION: Does canonical IABV state actually alter a real external AI's decision or action?

CURRENT STATUS: NOT PROVEN.

WHY IMPORTANT: This is the principal boundary between context delivery and a genuine cognitive control plane.

DISCRIMINATING EXPERIMENT: Compare materially equivalent executions with/without canonical IABV context while holding task, agent and environment stable enough to establish whether the decision/action changes because of IABV state. Capture pre-state, delivered context, action, result, verification and post-state.

### UK-02 — Causal learning / decision influence

QUESTION: After a verified experience is persisted, does a later decision change because of that experience?

CURRENT STATUS: NOT PROVEN.

REQUIRED CHAIN:

`experience → provenance → persistence → later retrieval → decision influence → independently observed changed action`

Persistence alone is insufficient.

### UK-03 — Second-agent continuity

QUESTION: Can a second external agent continue from the canonical state produced by the first agent without manual history reconstruction?

CURRENT STATUS: NOT PROVEN.

WHY IMPORTANT: This is the concrete test of cross-agent continuity as a system property rather than a prompt convention.

### UK-04 — Prediction and calibration loop

QUESTION: Does IABV produce a pre-execution prediction, uncertainty/confidence signal, and later calibration against observed outcome?

CURRENT STATUS: Historical records identify this as an important metacognitive gap; exact end-to-end causal implementation remains unresolved.

TARGET LOOP:

`predict → execute → observe → compare → calibrate → update strategy`

### UK-05 — AdaptiveSession typed provenance canonicalization

QUESTION: Do typed fields actually own runtime decisions and reconstruction?

CURRENT STATUS: Current historical audit found FAIL because legacy metadata remained causally active.

REQUIRED DIRECTION:

`typed canonical fields → runtime decisions → persistence/reconstruction`

Legacy metadata must become compatibility-only and historical sessions may require migration/reconstruction.

### UK-06 — P0-B adversarial Windows validation

QUESTION: Does the hardened authority chain survive the registered Windows attack suite on the latest target?

TARGET:

`origin/audit/p0-b-repopath-on-hardened-base`

`c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3`

STATUS: Pending independent runtime validation in the recorded project state.

ATTACK FAMILIES: pre-registration, trust-root replacement, forged authority/certification, request spoofing, invocation cross-binding, RunRecord cross-binding, SelfAudit forgery, replay/concurrent replay, DB record forgery, runtime code injection, RepoPath substitution, service binary/config replacement.

### UK-07 — Runtime-integrity boundary of cryptographic authority

QUESTION: Can an attacker execute modified code inside the runtime that holds cryptographic authority despite protected keys and trust roots?

CURRENT STATUS: This boundary was explicitly identified as necessary in P0-B hardening.

REQUIRED EVIDENCE: `python314._pth`, user-site isolation, package/site-packages integrity, `RepoPath` integrity, service identity, ACLs, and replacement resistance must be tested together with the authority chain.

### UK-08 — Dynamic historical-context activation

QUESTION: Can a new chat discover the right historical knowledge from GitHub based on its objective without loading the complete archive?

CURRENT STATUS: Navigation layer now exists; operational proof should come from use and subsequent reconciliation.

SUCCESS CONDITION: Objective → domain routing → relevant source archives → current reconciliation → activated context → work without unnecessary historical flooding.

### UK-09 — Archive completeness beyond commits/tasks

QUESTION: Can the archive reliably preserve knowledge that never became code, a ticket or a formal decision?

REQUIRED CONTENT: ideas left in the air, rejected paths, false positives, cross-IA corrections, methodological changes, conceptual breakthroughs and unresolved questions.

CURRENT STATUS: Dedicated register and routing layer now exist; completeness still requires repeated comparison against source conversations when deletion is at stake.

### UK-10 — True D0 external communication frontier

QUESTION: Can IABV demonstrate real authenticated external communication and the symbolic cycle `perspective_before → external observation → reconciliation → perspective_after → persisted delta`?

CURRENT STATUS: Infrastructure and selectors have existed historically, but real authenticated browser/shared-CDP communication was not proven in the available evidence.

### UK-11 — Accelerated metacognitive orchestration / executive synthesis

QUESTION: Can the existing IABV organs be composed into a low-friction executive loop that continuously determines what matters now, what evidence is sufficient, which actor should be delegated, what must be verified, and what knowledge must be written back — without requiring the human to manually repackage every prompt?

CURRENT STATUS: ARCHITECTURALLY PLAUSIBLE / CAUSAL LOOP NOT PROVEN.

IMPORTANT DISTINCTION:
This is not a proposal for another monolithic brain. It is a hypothesis that IABV's existing perception, world-model, self-examination, governance, routing, adaptive-weight, outcome, memory and external-agent adapters can already support a higher-order control loop if their outputs become causally connected at the right boundaries.

TARGET LOOP:

`objective → active context → current reality → uncertainty map → information-gain ranking → actor/action selection → delegated execution → observation → independent verification → knowledge delta → next objective state`

KEY ACCELERATION HYPOTHESIS:

The human should ideally specify the objective and intervene at real decision boundaries. IABV should handle routine context retrieval, prompt packaging, evidence collection, delegation, status correlation, verification routing and memory writeback when the required capabilities and permissions are available.

NON-CLAIM:
This does not prove autonomous control of Devin or any other external agent. The capability remains unresolved until a real end-to-end experiment demonstrates that IABV state determines a delegated action and the resulting feedback changes a subsequent decision.

### UK-12 — Devin delegation as an executive control path

QUESTION: Can IABV's existing Devin adapter, briefing/context path and routing/governance layers safely act as a delegated execution path so the human provides the objective while IABV prepares, sends, monitors and verifies the implementation work?

CURRENT STATUS: INFRASTRUCTURE EXISTS / FULL EXECUTIVE LOOP NOT PROVEN.

CURRENT EVIDENCE:
- `DevinApiToolAdapter` exists as a REST integration;
- bootstrap wires a Devin message sender;
- `SessionStartBriefingService` accepts a `message_sender(session_id, content)` abstraction that can be supplied by the Devin adapter;
- historical R3 work established the importance of production-path context propagation;
- `SynapticRouter` currently ranks candidates from fit, adaptive history and live World Model availability but explicitly does not execute the route;
- `AdaptiveTaskOrchestrator` uses the synaptic ranking as informative while `LocalRoleRouter` remains the operational route decision authority.

REQUIRED DISCRIMINATING EXPERIMENT:

`IABV objective → canonical context → approved Devin task packet → Devin session/message → observable Devin action/result → independent verification → writeback → next decision influenced by result`

Success must be proven at the causal boundary, not inferred from adapter availability or successful HTTP receipt.

### UK-13 — Existing-orchestrator ownership of the executive loop

QUESTION: Is the remaining acceleration gap a missing decision algorithm, or a missing autonomous trigger/feedback connection around decision machinery that already exists?

CURRENT STATUS: INITIAL RECONCILIATION INDICATES **EXISTING DECISION ORG / MISSING CLOSED ACTIVATION PATH**, not a proven need for a new delegation service.

CURRENT EVIDENCE:
- `AdaptiveTaskOrchestrator` already owns operational task orchestration, intent/context assembly, governance, worker gating, task execution and outcome application;
- `AutonomyCycleService` already consolidates perception-derived findings into pending work, resume hints and actionable startup summary, while explicitly leaving autonomous decisions to `AdaptiveTaskOrchestrator`;
- `AdaptiveTaskOrchestrator` is already wired to `AutonomyCycleService`, `GoalEngine`, `CapabilityReadinessService`, `AutonomyGovernancePolicy`, `TaskContextAssembler`, `TaskOutcomeRecorder` and optional `SynapticRouter`;
- `AutonomousEvolutionService.plan_or_execute()` already contains the external-consultation decision/execution boundary and can invoke `ToolTeachService.execute_external_consultation()`;
- `SessionStartBriefingService` already converts `PortableContextService` state into an external-agent briefing and can deliver/create sessions through injected callables;
- current code still treats `SynapticRouter` as descriptive and does not prove that canonical world/self/history state automatically causes a Devin delegation;
- current evidence does not prove a runtime trigger that consumes the actionable autonomy queue and closes the chain through Devin → observed result → verified post-state → changed next decision.

IMPORTANT DEDUCTION:
Do **not** create `DevinDelegationDecisionService` merely because the first forensic report named it. That would risk duplicating `AdaptiveTaskOrchestrator` and fragmenting decision authority. First trace and test whether the smallest missing edge is an activation/feedback connection into the existing orchestrator and external-consultation path.

ACCELERATION HYPOTHESIS:
The highest-value intervention is likely to make the existing orchestration stack consume the autonomous work queue and produce a traceable executive task packet, while preserving `AutonomyCycleService` as state substrate, `AdaptiveTaskOrchestrator` as decision authority, `SessionStartBriefingService` as briefing/transport bridge, and `TaskOutcomeRecorder` as outcome persistence. Only create a new component if code-level evidence proves no existing contract can own the missing edge without duplication.

DISCRIMINATING EXPERIMENT:

`human objective → current canonical state/context → active uncertainty/gate → existing orchestrator decision → Devin selection/packet → existing external-consultation path → observable Devin action/result → independent verification → post-state → next orchestrator decision`

The experiment must report the first causally broken edge using `DEFINED | WIRED | INVOKED | OBSERVED | CAUSED`, plus the smallest implementation needed to close that edge. It must not expand into a general architecture rewrite.

SUCCESS CONDITION:
A real development objective can be supplied once by the human; IABV assembles relevant context and evidence, invokes its existing decision machinery, delegates through the existing Devin path when governance allows, captures the result, verifies the outcome, and returns to the same decision machinery with a materially different next state/decision — reducing routine manual prompt transport without weakening provenance or independent verification.

### UK-14 — Comparative metacognitive benchmark / external-agent capability baseline

QUESTION: Can IABV establish a reproducible baseline of its reasoning/metacognitive capabilities against external agents such as Claude, Devin and ChatGPT, then demonstrate measurable improvement after verified learning — while reducing unnecessary Codex interventions?

CURRENT STATUS: STRATEGICALLY RELEVANT / BENCHMARK DESIGN REGISTERED / RUNTIME BASELINE NOT YET EXECUTED.

WHY IMPORTANT:
The project should not spend Codex effort rediscovering obvious reasoning or architecture errors that IABV could learn to detect itself. A benchmark provides an empirical guardrail for the desired development acceleration and makes "IABV is improving" testable rather than aspirational.

TARGET CAPABILITIES:

- observation accuracy;
- uncertainty calibration;
- contradiction detection;
- causal-trace reconstruction;
- minimal discriminating action;
- stop discipline;
- governance awareness;
- self-audit;
- verification discipline;
- learning/reuse;
- external-agent escalation quality;
- development efficiency / avoidable external work.

TARGET IMPROVEMENT LOOP:

`baseline IABV → external comparison → verified correction → canonical knowledge → repeat case → improved IABV decision/action → less avoidable external intervention`

IMPORTANT BOUNDARY:
A later Codex PASS is evidence about the audited implementation or hypothesis, not by itself proof that IABV's internal reasoning was correct. The meaningful metacognitive claim requires measured improvement and changed downstream behavior.

BENCHMARK GUIDANCE:
`IABV_v1.5/docs/history/CHAT-ARCH/AGENT-REASONING-BENCHMARK-2026-09-12.md`

The benchmark should prefer fixed/reproducible cases, dimension-level evidence, negative controls, provenance and before/after learning comparisons. It must not become a new parallel reasoning engine.

NEXT DISCRIMINATING ACTION:
Before another Codex implementation/audit cycle, inspect existing evaluation infrastructure and build/run the smallest reproducible comparative benchmark using the existing IABV evaluation mechanisms where possible. If live provider access is unavailable, use fixed recorded external outputs so benchmark design is not blocked by API connectivity.

## DEFERRED BUT IMPORTANT DESIGN IDEAS

These are intentionally recorded without forcing implementation:

- objective-conditioned context packets rather than universal context dumps;
- capability-driven dynamic role allocation across external AIs;
- automatic activation of only the historical lessons that can affect the current claim;
- explicit "negative knowledge" as a first-class retrieval target;
- claim/evidence ledgers linked to current code and runtime fingerprints;
- causal continuity metrics based on changed downstream decisions rather than message receipt;
- blind reconstruction as a deletion-safety test;
- historical migration of legacy provenance records into typed canonical provenance;
- runtime provenance as a first-class evidence object across tool execution;
- learned collaboration policy: which AI should challenge, implement, observe or adjudicate for a given class of uncertainty;
- executive synthesis that minimizes routine human coordination by delegating context assembly, prompt construction, evidence capture and post-action verification to existing IABV organs;
- explicit intervention thresholds so the human is surfaced only when a real decision, permission, contradiction or unresolved evidence gap exists;
- state-before/state-after experiment packets as the standard unit for proving causal improvement in development workflow;
- objective-conditioned work queues generated from active uncertainty rather than fixed phase lists;
- a frozen comparative agent benchmark used as a longitudinal measure of IABV's metacognitive progress.

## REJECTED / DO-NOT-REPEAT IDEAS

- create another brain/orchestrator when existing organs can be wired;
- assume a green unit test proves runtime integration;
- treat a direct adapter call as proof of production routing;
- treat persisted data as proof of causal learning;
- treat a valid signature as proof of legitimate authority;
- treat a new field as canonical while legacy fields still control behavior;
- treat a local archive as sufficient for deletion safety;
- force every objective through the same fixed AI role sequence;
- use Codex as the first detector of errors that a validated IABV benchmark can detect itself.

## USE OF THIS REGISTER

A future chat should retrieve this file when its objective overlaps an unresolved item. It should then determine whether the current repository has since resolved, refuted, superseded or still preserves that item.

For UK-11 / UK-12 work, the future chat should prefer an **acceleration experiment** over another general architecture review: identify one real delegated workflow, capture state-before, let IABV prepare and delegate the work, capture state-after, independently verify the effect, and determine whether the resulting experience changes the next routing decision.

For UK-13, the first implementation question is **ownership and activation**, not creation of another decision service: trace `AutonomyCycleService → AdaptiveTaskOrchestrator → existing external-consultation path → Devin → verification → outcome/replan` and implement only the smallest missing edge that prevents the causal loop from closing.

For UK-14, the benchmark becomes a gate before expensive external audit cycles: first measure IABV, compare against relevant agent capabilities, identify the smallest learning opportunity, verify the correction independently, and remeasure before spending Codex effort on implementation/audit that the benchmark indicates IABV should already be able to reason about.

Resolution requires evidence, not a status edit based only on a later claim.
