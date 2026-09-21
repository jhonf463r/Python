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

CURRENT STATUS: NOT FULLY PROVEN AT SYSTEM LEVEL. A 2026-09-17 L5 report claims selector-level causal change, but the reported test artifact is not present in the remote branch tip used as provenance. Treat the claim as candidate evidence pending independent audit.

REQUIRED CHAIN:

`experience → provenance → persistence → later retrieval → decision influence → independently observed changed action`

Persistence alone is insufficient. Selector-level influence is not yet equivalent to downstream behavioral change.

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

### UK-15 — Selector-level causal reuse / L5 provenance gate

QUESTION: Does the reported 2026-09-17 L5 experiment actually prove that a persisted verified experience reaches a future selector decision and changes that decision under controlled conditions?

CURRENT STATUS: **CANDIDATE / PENDING INDEPENDENT AUDIT.**

REPORTED RESULT:

- Control: `learned_pattern=0.0`, `total_score=7.545`, no selected pattern.
- Treatment: fresh reload, `learned_pattern=1.0`, `total_score=10.095`, selected pattern `8e8f6695-8bdb-4d6b-922d-fa6a11728245`.
- Reported causal variable: persisted and reloaded verified experience.

PROVEN PRECONDITION:
G3 established verified transition → persistence → fresh reader → `verified_transition_success_count` mutation `0 → 1` in a Windows/Ollama runtime.

PROVENANCE WARNING:
The remote branch `codex/world-grounded-learning-bridge` currently points to `55d3e2c93807202ec5d0177eda163e8de10418ef`. Direct GitHub read-back of that commit shows a G3 observation-wrapper diff in `test_g2_goal_to_action_plan.py`; the reported `tests/test_l5_causal_decision.py` is not present at that remote tip. The runtime report may therefore have used an uncommitted or otherwise separate artifact. This must be reconciled before promoting L5 to canonical evidence.

REQUIRED AUDIT:

1. identify the exact artifact actually executed;
2. reconcile commit SHA vs working-tree state;
3. verify the test did not fabricate `InteractionPattern`, counters or decision scores;
4. verify persistence/reload are real and not memory-only;
5. identify whether the normal production decision path (`ToolTeachService` or equivalent) was exercised or whether `InteractionModeSelector` was called directly;
6. verify Control/Treatment are matched except for the intended verified-experience variable;
7. verify the observed score difference is causally attributable to that variable;
8. classify the maximum justified claim as selector-level, production-decision-level, or not proven.

NEXT ACTOR:
**SONNET** for independent forensic audit.

NEXT AFTER AUDIT:
If L5 survives, design L6 as a controlled behavioral-change experiment; if a local defect is found, route the minimal fix to Devin; if an architectural contradiction appears, route to Opus before implementation.

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
- use Codex as the first detector of errors that a validated IABV benchmark can detect itself;
- promote a runtime claim to a commit claim without direct artifact read-back.

## USE OF THIS REGISTER

A future chat should retrieve this file when its objective overlaps an unresolved item. It should then determine whether the current repository has since resolved, refuted, superseded or still preserves that item.

For UK-11 / UK-12 work, the future chat should prefer an **acceleration experiment** over another general architecture review: identify one real delegated workflow, capture state-before, let IABV prepare and delegate the work, capture state-after, independently verify the effect, and determine whether the resulting experience changes the next routing decision.

For UK-13, the first implementation question is **ownership and activation**, not creation of another decision service: trace `AutonomyCycleService → AdaptiveTaskOrchestrator → existing external-consultation path → Devin → verification → outcome/replan` and implement only the smallest missing edge that prevents the causal loop from closing.

For UK-14, the benchmark becomes a gate before expensive external audit cycles: first measure IABV, compare against relevant agent capabilities, identify the smallest learning opportunity, verify the correction independently, and remeasure before spending Codex effort on implementation/audit that the benchmark indicates IABV should already be able to reason about.

For UK-15, never promote L5 from a report alone. First reconcile the exact artifact/commit and independently audit the control/treatment causal chain.

Resolution requires evidence, not a status edit based only on a later claim.

## 2026-09-19 UK-15 RESOLUTION — L5 PROVEN

The previous UK-15 status `CANDIDATE / PENDING INDEPENDENT AUDIT` is superseded by the independent Sonnet 5 Low adjudication recorded in:
`CHAT-ARCH-2026-09-19-001-l5-final-independent-audit.md`.

**CURRENT STATUS: PROVEN — SELECTOR-LEVEL CAUSAL LEARNING.**

Verified chain:
`real G3 effect → independently observed verification → VerifiedTransition → persisted InteractionPattern → cold reload → production InteractionModeSelector.select() → fixed two-candidate universe → winner change → score delta attributable to the verified experience`.

The prior `cost 0.40 → 0.75` confound was a false longitudinal comparison of different round winners, not a mutation of one candidate. For the same `mcp_client` candidate, non-learning score inputs were constant and the observed delta was reconstructed from InteractionPattern-derived stability, frequency and learned-pattern terms.

REMAINING BOUNDARIES:
- L6 behavioral causality remains open;
- L7 later external-world causal closure remains open;
- P0-B authority/security closure remains open;
- I0/I1/I2 external-agent orchestration remains unproven;
- real Devin cognitive influence remains unproven.

NEXT DISCRIMINATING ACTION:
Run a minimal I0/I1 experiment through existing IABV external-agent adapter/briefing/orchestration paths, with state-before, delegated action, received result, provenance binding and independent verification. Do not create a new delegation service unless source evidence proves no existing owner can close the edge without duplication.

## 2026-09-20 RESOLUTION — ASSISTANT↔TOOL OWNERSHIP

Resolved by independent Codex adjudication:

**CANONICAL OWNER = ToolCard declaration + ToolRegistry resolution.**

Resolved boundary:

`assistant_kind → ToolRegistry → candidate ToolCard(s) → canonical tool_id(s) → resource ranking`

The previous uncertainty over whether `ToolTeachService` should own this semantic mapping is closed.

Remaining open implementation seam:

`assistant_kind → ToolRegistry resolution → normalized tool identity set → rank_workers_for_target() → selected UniversalResource → credential_ref`

The resource scanner must not become a global assistant-alias resolver or depend on ToolTeachService.

Next actor: **DEVIN** for the bounded implementation, followed by independent **SONNET** audit.

Canonical adjudication:
`CHAT-ARCH-2026-09-20-001-canonical-tool-owner-adjudication.md`



## 2026-09-20 RESOLUTION — I0 ASSISTANT↔TOOL RESOURCE-RESOLUTION SEAM

The implementation seam left open in the 2026-09-20 ownership adjudication is now closed by the independently audited remote artifact:

Branch: `devin/i0-canonical-tool-registry-resolution-fix-2026-09-20`

Commit: `4710a668541225ffe3b9d1335d31bb5da8b1e685`

Independent status: **A — VERIFIED EFFECTIVE SEAM**

Verified boundary:

`assistant_kind → ToolRegistry → canonical tool_id(s) → rank_workers_for_target() → UniversalResource → credential_ref`

This item is no longer an unresolved ownership/resolution problem.

Required negative knowledge remains preserved: the predecessor introduced a reachable `NameError`, broke no-target ranking, failed to wire the registry in bootstrap, and had insufficient router-level test coverage.

Remaining I0 question:

`credential availability → authentication/authorization → transport → external effect → independent verification`

Overall I0/I1 external-agent execution remains open until the real runtime credential/authentication boundary is experimentally closed.


## 2026-09-20 I0 PHASE A — RUNTIME EVIDENCE PROVENANCE GAP

Current status: **C — INCONCLUSIVE** at independent-audit level.

The reported Windows runtime says all supported Devin credential variables are absent and therefore no authentication request occurred. Independent review verified the production resolver and the pre-HTTP empty-key gate, but could not independently inspect the effective remote process environment or the uncommitted JSON artifact.

Required next evidence:

`exact Windows process → raw non-secret runtime capture → artifact preservation/read-back → independent reconciliation`.

Do not reinterpret this as successful authentication or as I1/I2 progress. Operationally, the reported environment remains credential-blocked.

Secondary unresolved auditability observation: multiple Devin credential-check implementations exist in `account_resource_scanner.py`, including one path that omits `IABV_DEVIN_API_KEY`. This is currently a maintainability/auditability finding, not a demonstrated Phase-A causal blocker.


## 2026-09-20 I0 PHASE A R2 — PROVENANCE CLOSED, RUNTIME TRUTH PENDING

The second runtime evidence artifact is now repository-preserved in commit `99d670b0dd2ecea04bc691e09bb2444c7721bff7`, one commit after tested code `4710a668541225ffe3b9d1335d31bb5da8b1e685`.

Independent recomputation confirms artifact SHA-256 `8ed7b1e43065a85d91142350ad82b28f9d8fba82075ddeb74c330a71bd3fd074`.

Resolved uncertainty:
`reported artifact → remotely readable preserved artifact → byte/hash integrity` = CLOSED.

Remaining uncertainty:
`preserved artifact → truthful observation of exact Windows process environment/resolver/network state` = PENDING INDEPENDENT AUDIT.

Current Phase-A evidence classification remains **C — INCONCLUSIVE** until Sonnet audits R2 independently.


## 2026-09-20 I0 PHASE A R2 — CURRENT OPEN EDGE

Independent audit of the preserved R2 artifact = **B — PARTIALLY VERIFIED**.

Artifact provenance and source reconciliation are closed. The remaining uncertainty is not artifact preservation; it is whether a real securely provisioned Devin credential is available to the exact Windows runtime and, once available, which next causal boundary breaks:

`credential → authentication/authorization → transport → external effect → independently verified result`.

The multiple credential-check paths in `account_resource_scanner.py` remain a non-causal auditability finding unless future evidence links them to the active path.


## 2026-09-20 I0 REAL-CONNECTION PREFLIGHT — TWO PRECONDITIONS OPEN

The latest runtime preflight stopped before the production resolver because:

- runtime HEAD was `99d670b0dd2ecea04bc691e09bb2444c7721bff7` (artifact-preservation commit), not tested code `4710a668541225ffe3b9d1335d31bb5da8b1e685`;
- all supported Devin credential variables were absent.

No authentication/authorization/network evidence was generated.

Next discriminating execution requires the exact implementation revision plus a real securely provisioned credential. The artifact-preservation commit must remain intact; use detached checkout or a separate runtime worktree rather than rewriting the branch history.

The malformed reported value `471670b058` is not a valid replacement for the canonical tested SHA and is not accepted as evidence.


## 2026-09-20 I0 — REPEATED PREFLIGHT IS NOW REDUNDANT

The latest preflight used the exact target implementation `4710a668541225ffe3b9d1335d31bb5da8b1e685` and again found no value for any supported Devin credential variable. It correctly stopped before the production resolver.

Negative knowledge:

`repeating the same no-credential preflight without changing the environment does not reduce the current uncertainty`.

Therefore the next useful action is environmental, not code-level: securely provision a real Devin credential to the controlled Windows process. No additional runtime attempt should be made until that condition changes.


## 2026-09-20 I0 CREDENTIAL PROVISIONING — EXISTING UI PATH CONFIRMED

The project already contains an intended one-window secret-provisioning mechanism. This removes the need for manual PowerShell configuration as the default route.

For Devin, IABV can detect the missing secret, open the configured Devin API-key page when user-initiated/confirmed, and capture the resulting token through the UI into `~/.iabv_secrets.ps1` via `save_secret_to_profile()`. Full autonomous browser creation is currently implemented only for a subset of providers, so Devin account creation remains a user administrative action.

Current blocker is therefore:

`Devin account credential creation (user administrative action) → IABV secure UI capture → effective Windows environment`.

Do not treat this as a repository implementation gap unless the UI path itself fails empirically.

## 2026-09-20 I0 — REACHABLE PRODUCTION DEFECT BEFORE CREDENTIAL BOUNDARY

The latest live external interaction exposed a real `NameError: target is not defined` in `LocalRoleRouter.worker_health_gate()`. The defect is reachable because `account_approval_ledger` is non-null in production bootstrap and the approval branch uses an undefined `target` symbol.

This supersedes the assumption that the external route is currently blocked only by credential availability. The active implementation prerequisite is now:

`remove reachable target NameError → re-run exact runtime path → then reassess credential/authentication boundary`.

Prior router tests were insufficient because they did not force the approval-ledger branch. Preserve negative knowledge: `tested helper cases without the production ledger path can miss reachable runtime defects`.


## 2026-09-20 I0 — TARGET FIX PROVENANCE GAP

Reported fix: `target_assistant=target` changed to `target_assistant=target_assistant_normalized` in `LocalRoleRouter.worker_health_gate()`, with a claimed approval-ledger regression test.

Current independent state: **NOT YET VERIFIED REMOTELY**. The reported branch/SHA cannot currently be read back from GitHub. Preserve the rule:

`local/agent-reported commit ≠ remotely verified commit`.

Next action: publish the exact branch and full SHA, then independent audit.

## 2026-09-20/21 — NEW STRATEGIC UNRESOLVED KNOWLEDGE: METACOGNITIVE COMPOSITION

### UK-META-01 — Deep self-assessment is not causally closed

Existing organs can individually observe:
- runtime/environment state;
- WorldModel state;
- source/code state;
- audit history;
- experimental state;
- adaptive strategy state.

Still unresolved:

`combined self-assessment → first broken causal edge → verified Knowledge Delta → future decision change`.

### UK-META-02 — Deep introspection lacks proven changed-surface causal mapping

Needed reusable capability:

`DIFF/SYMBOL CHANGE → impacted consumers/producers → contracts → alternative routes → fallbacks → adversarial negatives → downstream effects`.

This should be investigated before creating new architecture.

### UK-META-03 — Introspection persistence/learning bridge is not proven

Need to verify whether a deep self-analysis result is transformed into a durable sequence such as:

`CodeAuditTrail → OSES → PortableContext → ExperimentLab/StrategySelector → future decision`.

Do not infer learning from merely storing an analysis report.

### UK-META-04 — Observation/mutation boundary in auto-analysis

Existing auto-analysis may mutate repository/worktree state. It remains unresolved whether the current implementation can guarantee a pure observation phase before mutation.

### UK-META-05 — I0 target-fix regression coverage

Remote source fix `b3e211fbbe001d6c360071c04a83ea40cff48071` is verified at source level.

The supplied independent audit reports that the regression test may return before exercising the historically failing approval-ledger branch. Treat:

`source fix verified != production-path regression test verified`.

Next useful action is direct re-audit/correction of the test fixture, not blind repetition of external runtime attempts.

### UK-META-06 — P041-R8 runtime boundary

`879605b4e17b6194868f0e4bc39a014994dc0a83` remains static/unit evidence only until independent runtime verification establishes response-routing and guidance behavior under the intended environment.

### Negative knowledge

`organ inventory != cognitive integration`

`self-analysis report != self-learning`

`positive test != affected-surface proof`

`source fix != causal regression coverage`

`observation mixed with mutation != trustworthy self-state observation`

`external AI agreement != method change`.

### Strategic next discriminating action

Run one IABV-native deep self-assessment experiment on an explicitly pinned code/runtime state, then have Sonnet independently audit the resulting artifact and claim boundary.
## 2026-09-21 — METACOGNITIVE EXECUTION BACKLOG MATERIALIZED

The previously conversational ideas around biosophia/metacognition are now persistent execution items in `IABV_v1.5/data/evolution/backlog.json` and prioritized in:
`BIOSOFIA-METACOGNITIVE-EXECUTION-ROADMAP-2026-09-21.md`.

Highest-priority unresolved chain:
`IABV-native deep self-assessment → evidence-qualified first open causal edge → discriminating experiment → Knowledge Delta → future decision change`.

This keeps proposed capabilities visible even when they are not yet implemented and prevents the current chat from becoming the sole storage location for strategic ideas.

