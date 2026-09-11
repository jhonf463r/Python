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
- identification of latent/unimplemented knowledge.

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
- implementation of scoped fixes.

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
- independent read-back surface.

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
- an epistemic boundary.

## FUTURE OBJECTIVE ACTIVATION

For a new objective, retrieve only the symbiosis entries that can change the strategy for that objective.

Example:

- security objective → activate authority/provenance transfers;
- runtime integration objective → activate exact-runtime and test-boundary transfers;
- cognitive objective → activate receipt-vs-cognition and persistence-vs-learning transfers;
- continuity objective → activate archive/deletion and dynamic-context transfers.

The objective determines which lessons become active constraints.
