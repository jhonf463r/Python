# IABV v1.5 — Cross-IA Symbiosis / Knowledge-Transfer Map

## PURPOSE

This file records **how the participating AIs changed one another's working model**, not just what each one produced.

Roles are historical capability observations. They are not fixed identities. A future objective should select the most useful role configuration from the evidence available at that time.

## CORE PATTERN

```text
AI / IABV observation
      ↓
interpretation or hypothesis
      ↓
independent challenge
      ↓
implementation / experiment
      ↓
runtime observation
      ↓
reconciliation
      ↓
new project knowledge
      ↓
update of future roles / tests / gates
```

## OBSERVED CAPABILITY PATTERNS

### ChatGPT

Strong historical function:

- meta-orchestration;
- synthesis across long evidence chains;
- epistemic boundary setting;
- reconciliation of conflicting AI reports;
- architecture-level reframing;
- identification of latent/unimplemented knowledge;
- recognizing when an apparently local bug is evidence of a broader systemic contract problem.

Constraint learned: synthesis must not be treated as runtime evidence.

### Claude

Strong historical function:

- adversarial source audit;
- challenge to causal interpretations;
- detection of false positives;
- independent reconstruction of architecture and canonicality;
- separation of structural defects from imperative/runtime defects.

Representative correction: Claude disproved the supposed structural dependency cycle around `ToolTeachService` / `IntentScopedBriefingService`, showing that the real defect was construction order and supporting explicit late binding.

### Devin

Strong historical function:

- runtime operator;
- MCP/environment observation;
- exact-runtime startup checks;
- practical integration evidence;
- implementation of scoped fixes;
- tracing concrete producer→consumer paths when supplied with a forensic objective.

Representative learning: static wiring was insufficient; exact-runtime startup exposed a bootstrap regression that unit tests had not caught.

### Codex

Strong historical function:

- focused implementation;
- controlled experiments;
- targeted regression tests;
- rapid exploration of implementation hypotheses.

Representative correction pattern: an implementation hypothesis can be useful without being accepted as architectural truth; independent audit remains necessary.

### GitHub

Function:

- external provenance anchor;
- branch/commit/file-history adjudication;
- durable publication layer for historical knowledge;
- independent read-back surface;
- canonical memory surface when knowledge is intentionally absorbed into `main`.

GitHub is evidence infrastructure, not an oracle for runtime behavior.

### IABV runtime

Function:

- canonical operational state source where actually observed;
- world/self-model source;
- execution and governance state;
- target environment whose real behavior must eventually close the evidence loop.

## IMPORTANT TRANSFERS OF KNOWLEDGE

### Transfer 1 — Real transport is not cognition

R5 loopback evidence demonstrated real local HTTP transport, but later reasoning separated this from real external-agent cognition, decision influence and learning.

New invariant:

`receipt != cognition`

### Transfer 2 — Exact runtime provenance is a prerequisite

A live IABV instance at `dd44c844...` was initially observed while the intended R5 target was `0ac668878...`. Git ancestry reconciled the relationship, but the experience established that runtime state must not be attributed to a target revision without fingerprint evidence.

New invariant:

`repository target != runtime target until proven`

### Transfer 3 — Construction order is not architecture

The ToolTeach/briefing incident showed that an imperative lifecycle bug can imitate a structural dependency cycle.

New invariant:

`imperative initialization defect != structural class dependency cycle`

### Transfer 4 — Canonicality is behavioral

The `aa3ff2c2` AdaptiveSession change created typed provenance fields, but independent audit found legacy metadata still controlled runtime decisions.

New invariant:

`field existence != canonicality; decision ownership must follow the canonical field`

### Transfer 5 — Persistence is not learning

Across self-development, continuity and cognitive-control discussions, stored records repeatedly risked being interpreted as causal learning.

New invariant:

`persisted experience must be shown to affect a later decision before learning is claimed`

### Transfer 6 — Security and cognition must remain orthogonal

The P0-B authority boundary demonstrated that cognitive context must not become a source of security authority. Trust-root ownership, provisioning identity, key protection and runtime integrity remain separate security invariants.

New invariant:

`cognitive influence != security authority`

### Transfer 7 — Archive is knowledge, not transcript

The archive effort exposed information loss outside commits/tasks: rejected options, false positives, ideas left in the air, latent architectural deductions and cross-IA corrections.

New invariant:

`durable continuity requires knowledge reconstruction, not transcript storage alone`

### Transfer 8 — Runtime repair must be closed through the real path

P040 demonstrated that a source-level repair can expose a second latent contract/import break only after the UI traverses the actual path.

New invariant:

`first visible fix != full path integrity until the path runs and terminal state is reconciled`

### Transfer 9 — Cross-organ observations are not system-wide coherence

The systemic-integrity audit found that IABV has many local integrity mechanisms, but it has not yet demonstrated a universal comparison of producer, consumer, contract, timing and causal effect.

New invariant:

`local observability != cross-organ coherence`

### Transfer 10 — Preserve the current synthesis in canonical memory

A chat-specific discovery should not remain only in the conversational context. When it can affect future routing, verification, architecture interpretation or AI role selection, it should be written to the canonical `CHAT-ARCH` layer and routed by `CONTEXT-INDEX.md`.

New invariant:

`important discovery in chat != durable project knowledge until canonically written and routable`

## SYMBIOSIS DYNAMICS TO PRESERVE

### Dynamic role assignment

Do not begin every project with a fixed script such as "ChatGPT plans → Devin codes → Claude audits".

Instead:

```text
objective
→ boundary and evidence requirements
→ identify strongest available source/role for each requirement
→ assign independent challenge where necessary
→ execute
→ reconcile
→ update capability model
```

### Independence must be protected

The AI implementing a change should not be the sole authority for declaring the change correct when the claim is critical.

The strongest historical pattern is:

`implementation → independent verification → adjudication`

### Negative results are transferable knowledge

A failed experiment is useful when it explains why a tempting interpretation was wrong and how to avoid repeating it.

### Cross-IA learning must update the method

A cross-IA interaction is significant when it changes any of:

- the current architectural model;
- a verification rule;
- a provenance requirement;
- a test boundary;
- a role assignment strategy;
- a future experiment;
- an epistemic boundary;
- a system-integrity/connectivity interpretation.

## CURRENT SYSTEMIC-INTEGRITY ACTIVATION RULE

When an objective touches runtime drift, broken UI/integration paths, duplicate responsibilities, producer/consumer contracts, temporal ordering, stale references, cross-organ contradictions, or architecture maintenance:

1. activate `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`;
2. activate `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, and `UNRESOLVED-KNOWLEDGE.md`;
3. identify existing integrity algorithms before proposing new architecture;
4. use IABV's own organs as evidence sources where possible;
5. preserve distinctions between observation, diagnosis, reconciliation and correction;
6. reconcile the canonical memory against the current branch/commit/runtime before implementation.

The objective is to discover and reuse existing integrity capacity, not to manufacture a new central brain automatically.

## FUTURE OBJECTIVE ACTIVATION

For a new objective, retrieve only the symbiosis entries that can change the strategy for that objective.

Example:

- security objective → activate authority/provenance transfers;
- runtime integration objective → activate exact-runtime and test-boundary transfers;
- cognitive objective → activate receipt-vs-cognition and persistence-vs-learning transfers;
- continuity objective → activate archive/deletion and dynamic-context transfers;
- systemic-integrity objective → activate cross-organ coherence, runtime-repair and durable-memory transfer rules.

## 2026-09-17 TRANSFER 11 — PROVENANCE DISCREPANCY IS ITSELF KNOWLEDGE

A reported experiment cannot be promoted to canonical evidence until the artifact actually executed is reconciled with its reported commit/branch.

Observed case:

`reported L5 test → reported SHA 55d3e2c...`

but direct GitHub read-back showed the `55d3e2c...` committed diff did not contain the reported `tests/test_l5_causal_decision.py`.

New invariant:

`reported artifact != committed artifact until remotely verified`

Therefore, a provenance discrepancy is not noise. It is a Knowledge Delta that must alter the audit method and future prompt requirements.

## 2026-09-17 TRANSFER 12 — RUNTIME EVIDENCE CAN CLOSE A ROUTE WITHOUT ARCHITECTURE CHANGES

Sonnet runtime evidence demonstrated that:

`ToolTask.tool_id → execute_task() → get_card(task.tool_id) → correct adapter → adapter.run()`

and that the correct adapter was actually invoked for baseline, known Synaptic assistants and the unknown-assistant baseline-preservation case.

Method change:

Do not spend another AI intervention re-auditing an edge once stronger runtime evidence has closed it, unless a new contradictory observation appears.

New invariant:

`stronger causal evidence → retire redundant audit work → advance to first open edge`

## 2026-09-17 TRANSFER 13 — ROLE SELECTION IS A CAPABILITY OPTIMIZATION PROBLEM

Current routing lesson:

`objective → uncertainty → required capability → best-fit actor → independent challenge → reconciliation`

For this cycle:

- ChatGPT: adjudication, synthesis, evidence-boundary definition and memory writeback;
- Sonnet: forensic independent audit;
- Devin: Windows/runtime execution and minimal local test/fixture implementation;
- Opus 5: reserve for architectural contradictions or higher-order policy/causal adjudication;
- Codex: reserve for broader or ambiguous implementation work.

This is evidence-based capability routing, not permanent role identity.

New invariant:

`role label != role authority; capability fit is selected per objective`

## 2026-09-17 TRANSFER 14 — SYMBIOSIS IS MEASURED BY METHOD/STATE CHANGE

Agreement between AIs is not enough.

A stronger symbiosis event has:

`agent observation → independent reconciliation → changed experiment/method/system → observed delta → durable writeback → future behavior affected`

Useful measurements remain:

`ΔK = demonstrated knowledge delta`

`Δπ = policy/method change`

`ΔB = observable behavior change`

`ΔY = observable outcome change`

A cycle may have ΔK without Δπ, ΔB or ΔY. Do not infer higher-order symbiosis from agreement or from a green test.

## 2026-09-17 CURRENT ROLE ROUTING STATE

The present route is:

`ChatGPT → Sonnet → (Opus only if architectural contradiction) → Devin if minimal fix is required → Sonnet re-audit`

After a valid L5 audit:

`Devin → L6 runtime behavioral experiment → Sonnet audit → ChatGPT adjudication`

The route must be recomputed when the active uncertainty changes.


## 2026-09-20 TRANSFER 15 — BIOSOFÍA ARTIFICIAL AS A MEASURED DEVELOPMENT OBJECTIVE

The long-horizon objective is broader than AI-to-AI symbiosis.

IABV is intended to become an experimentally observable substrate for tracking the progressive emergence of artificial cognitive/organizational capabilities:

`perception → representation → interpretation → decision → action → observation → verification → memory → learning → adaptation → self-regulation → collaboration → self-directed development`

This is a research/engineering objective, not a claim of consciousness or personhood.

### Development inflection

The desired development inflection is measured by:

`verified experience → reusable knowledge → changed future decision → reduced routine human coordination → more efficient experimentation → new verified experience`

Code volume is not the target metric.

### Universal capability principle

The architecture should prefer:

`same concept → same canonical concept/owner`

`same function → same canonical organ`

and specialize only when semantics genuinely differ.

A new assistant/tool/resource should normally enter through existing contracts rather than create a parallel brain, router or delegation subsystem.

### Cross-IA role learning

Current role assignments remain capability hypotheses:

- ChatGPT: synthesis/adjudication/reconciliation/writeback;
- Sonnet: independent forensic audit;
- Devin: bounded Windows/runtime implementation and evidence;
- Codex: narrow technical ambiguity/implementation seam adjudication;
- Opus: genuine architecture/ownership contradiction.

Future evidence may revise these.

### Current universal-substrate gate

The next material seam is the continuity:

`assistant_kind → tool_id → resource_id → credential_ref → authorization`

The current Devin case exposes `devin → devin_api` as a namespace boundary. The next implementation must not create duplicate semantic authority merely to close this one case.

See:
`BIOSOFIA-ARTIFICIAL-DEVELOPMENT-INFLECTION-2026-09-20.md`



## 2026-09-20 TRANSFER 16 — CANONICAL TOOL IDENTITY BELONGS TO TOOL CATALOG

Codex independently resolved the ownership ambiguity exposed by the I0 Devin resource seam.

Canonical source:

`ToolCard` declares `assistant_kind`, `tool_id`, `adapter_key` and capability/availability facts.

Canonical resolver:

`ToolRegistry` resolves `assistant_kind → candidate ToolCard(s) → canonical tool_id(s)`.

The resource scanner remains responsible for resource discovery/ranking and must not interpret assistant aliases.

New invariant:

`assistant identity resolution != resource ranking authority`

Accepted implementation path:

`assistant_kind → ToolRegistry → normalized tool_id set → rank_workers_for_target() → UniversalResource → credential_ref`

This is a reusable architectural lesson for future assistants/tools, not a Devin-only mapping.

Canonical adjudication:
`CHAT-ARCH-2026-09-20-001-canonical-tool-owner-adjudication.md`

## 2026-09-20/21 TRANSFER 17 — IABV MUST BEGIN USING ITS OWN SYMBIOTIC ORGANS

The latest absorbed analysis adds a material methodological transition.

### External versus internal symbiosis

External symbiosis is operationally effective as a collaboration method:

`ChatGPT ↔ GitHub ↔ Devin ↔ Sonnet ↔ runtime`.

Internal symbiosis is only partially composed. IABV has the required organs, but a general causal circuit is not proven.

### Reusable target circuit

`objective → IABV self-assessment → uncertainty → capability-fit → actor/tool/resource → governed execution → observation → independent verification → Knowledge Delta → future selection`.

The human should increasingly stop serving as the routine transport layer for context, prompt packaging, actor selection, result transport, routine verification routing and memory writeback. Human authority remains appropriate for permissions, security boundaries, substantive contradictions and insufficient evidence.

### New capability-use rule

When the user requests a deep current-state assessment of IABV, prefer the native IABV metacognitive organs as the **first analyzer** rather than immediately outsourcing the analysis to another AI.

External AIs remain:
- independent verifiers;
- architectural adjudicators;
- bounded implementers;
- runtime observers;
- narrow technical specialists.

### New verification rule

`AI agreement != symbiosis learning`.

A cross-IA collaboration becomes durable knowledge only when it creates a demonstrable delta in:
- `ΔK` knowledge;
- `Δπ` method/policy;
- `ΔB` observable behavior;
- `ΔY` observable outcome.

### P041 systemic lesson

A local predicate change can alter classification, metadata, response routing, UI and guidance. Therefore self-assessment should include changed-surface and adversarial-neighbor analysis.

### Role hypothesis update

Keep the current capability model:
- ChatGPT = synthesis/reconciliation/writeback;
- Sonnet = independent audit;
- Devin = bounded implementation/runtime;
- Codex = difficult technical seam;
- Opus 5 = genuine architecture/ownership contradiction.

These are capability hypotheses, not fixed order or rankings.

### Strategic inflection

The next meaningful acceleration is not “connect more AIs”. It is “make IABV capable of finding its own next smallest discriminating experiment, then prove that the result changes a later decision.”

## 2026-09-21 TRANSFER 18 — SELF-USE + PROVENANCE-GATED HANDOFFS

The symbiosis method now has an explicit two-level use.

### Level 1 — IABV as subject

When the objective is a deep assessment of IABV itself, prefer:
`IABV native perception/self-model/introspection/metacognition → uncertainty → discriminating experiment`
before external delegation.

External AIs remain independent verifiers or specialists rather than automatic substitutes for IABV's own self-model.

### Level 2 — IABV as control plane

The target loop remains:
`objective → IABV context/memory → uncertainty → capability fit → actor/tool/resource → governed execution → observation → independent verification → Knowledge Delta → later decision`.

### Provenance as a symbiosis boundary

A cross-AI handoff is not complete merely because the implementer reports a result.

New reusable invariant:
`actor report != transferable evidence until artifact identity and remote content are verified`.

Required handoff gate:
`report → artifact → branch/ref → SHA → remote read-back → content check → independent verification`.

The I0 M3 artifact at `7753ce5632370b2a03726aeff63dbcd1ac7afc42` is the current positive example of this gate being crossed. Its claimed mutation result is still pending independent reproduction.

### Symbiosis measurement

Agreement is still insufficient. Durable symbiosis requires an observable change in:
`ΔK / Δπ / ΔB / ΔY`.

The new provenance gate is itself a method change (`Δπ`) but has not yet been shown to alter an IABV future decision causally.

## 2026-09-21 TRANSFER 19 — INDEPENDENT CAUSAL AUDIT REVEALS LINEAGE SCOPE

M3 is now stronger than "implementer says mutation failed".

The independent auditor reports:
`source reconstruction → direct test execution → discriminating mutation → exact failing assertion → false-positive checks → persistence check`.

This is a genuine forensic challenge, not model agreement.

New reusable symbiosis lesson:
`independent challenge → causal reproduction → provenance refinement → narrower claim`
is more valuable than:
`agent A conclusion → agent B agreement`.

### New Git provenance rule

Always distinguish:
`parent → head` from `named historical baseline → head`.

A commit can be test-only relative to its direct parent while its branch has materially changed production code relative to the historical baseline used in the narrative.

New invariants:
- `commit-local diff scope != cumulative branch lineage scope`;
- `direct parent != named historical baseline`;
- `commit message claim != ancestry-wide invariant`.

The I0 M3 artifact at `7753ce563...` demonstrates remote artifact provenance and independently reported mutation sensitivity. It does not close Windows runtime or I0.



## 2026-09-21 TRANSFER 20 — BIOSOFÍA ARTIFICIAL AS DEVELOPMENTAL ORGANIZATION

The collaboration model is now extended from AI-to-AI symbiosis to **developmental organization**.

New strategic distinction:

`symbiosis = coordination/knowledge transfer among actors`
`development = causal acquisition of new reusable capability`
`evolution = repeated generational variation + selection with heritable state`

The target is to make existing IABV organs behave as a developmental substrate without prematurely creating a parallel brain.

Candidate mapping:
- environment coupling → EnvironmentSelfAwareness / WorldModel / Perception;
- identity/boundary → SystemIdentityRegistry / OrganismStateSnapshot / governance;
- memory/heredity substrate → InteractionLearning / ExperimentLab / PortableContext / provenance;
- action → ToolRegistry / ToolCard / adapters / orchestration;
- viability/control → SelfAudit / OSES / governance / authority;
- selection → InteractionModeSelector / CapabilityReadiness / StrategySelector / AdaptiveWeightLayer;
- experimentation → ExperimentLab / SandboxExperimentService / validation;
- lineage → Git + evidence/provenance + future developmental lineage model.

The new knowledge is not "these organs already form a digital organism". The knowledge is that they provide candidate substrate functions whose **causal composition** can now be tested.

Persistent invariant:
`organ exists != organ integrated into developmental circuit`

New developmental invariant:
`verified result → reusable capability → ability to participate in the next developmental cycle`

The next important cross-IA transfer is therefore not another architecture report. It is evidence about whether IABV can use one verified capability to construct or enable another capability.

## 2026-09-21 TRANSFER 21 — DEVELOPMENTAL ACCELERATION AS SYMBIOSIS OUTPUT

The symbiosis objective now extends beyond collaboration efficiency: the collaboration itself should produce a progressively more capable IABV with less routine human coordination.

Core causal loop:

`verified experience → reusable knowledge → future decision change → lower routine coordination → more efficient experiment → new capability`

A symbiosis event is strategically valuable when it creates a durable `ΔK`, `Δπ`, `ΔB` or `ΔY` that changes a later cycle.

When the objective is IABV self-understanding, the first analyzer should be IABV-native introspection/metacognition. External AIs should serve as independent verification/specialization according to current capability fit.

Do not confuse:
- symbiosis with development;
- development with evolution;
- AI agreement with learning;
- persistence with future decision influence.

The global entrypoint is `00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md`.
