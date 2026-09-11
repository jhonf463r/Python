# IABV v1.5 — CHAT-ARCH: Canonical Historical Knowledge Entry Point

This directory is the canonical historical-memory layer for IABV. It preserves knowledge from ChatGPT / Claude / Devin / Codex and related engineering conversations without requiring future chats to retain the original transcript.

## OPERATIONAL MEMORY

The archive is not a flat collection of summaries. It functions as an objective-driven operational memory.

Primary protocol:

`MEMORY-OPERATING-PROTOCOL.md`

Core retrieval:

`new objective → discover relevant memory → reconcile current reality → activate context → select capabilities/roles → act → verify → learn → write back`

## ENTRY ORDER FOR A NEW CHAT

1. `README.md` — continuity contract and evidence rules.
2. `CONTEXT-INDEX.md` — objective-driven routing.
3. `CURRENT-STATE.md` — current project state and active gates.
4. `SYMBIOSIS-MAP.md` — cross-IA capability and knowledge transfer.
5. `UNRESOLVED-KNOWLEDGE.md` — ideas, deductions and unresolved boundaries.
6. `CANONICAL-ABSORPTION-2026-09-11.md` — source reachability, absorption and deletion-readiness audit.
7. `ARCHIVE-REGISTRY.md` — source-history locations and identities.
8. Relevant historical source records selected by the objective.

Do **not** read every historical record by default.

## OBJECTIVE-CONDITIONED ACTIVATION

The objective determines which history is active. Historical context is retrieved because it can change the present decision, not because it exists.

Activate a record when it contains relevant evidence, prior failure, contradiction, prerequisite/invariant, discriminating experiment, unimplemented idea, cross-IA correction, or current gate for the objective.

Use progressive retrieval from orientation → objective context → evidence → contradiction reconstruction → full forensic reconstruction only when needed.

## TWO-LAYER HISTORY MODEL

### Layer A — Operational memory / navigation

- `MEMORY-OPERATING-PROTOCOL.md`
- `CONTEXT-INDEX.md`
- `CURRENT-STATE.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`
- `CANONICAL-ABSORPTION-2026-09-11.md`
- `ARCHIVE-REGISTRY.md`

These synthesize, route and reconcile knowledge. They do not replace source history.

### Layer B — Historical source records

Existing `CHAT-ARCH-*` files under:

- `IABV_v1.5/docs/history/CHAT-ARCH/`
- `IABV_v1.5/docs/history/`
- `IABV_v1.5/docs/CHAT-ARCH-*.md`
- historical working branches when provenance requires them

remain historical source records unless explicitly superseded by evidence.

## CROSS-IA CONTINUITY

Roles are historical capability observations, not permanent assignments.

For each objective, select the strongest available capabilities for architecture synthesis, adversarial review, implementation, runtime observation, experimentation, provenance adjudication and verification.

The reusable object is the **knowledge transfer**:

`initial interpretation → challenge → experiment/implementation → observation → reconciliation → changed model → new method`

The implementing AI is not the sole verifier of a critical claim when independent verification is available.

## EPISTEMIC RULES

Always distinguish:

`idea → design → code → wired → tests → production path → runtime → adversarial verification → causal effect → independent reproduction`

Historical repetition never upgrades evidence.

Current source/contracts/runtime evidence outrank historical claims for current technical truth. Historical records remain authoritative for what was believed, discovered, rejected and learned at the time.

Do not confuse:

- test pass with runtime proof;
- runtime execution with cognition;
- receipt with cognition;
- persistence with learning;
- cryptographic validity with legitimate authority;
- field existence with canonicality;
- repository state with runtime state;
- archive existence with deletion safety.

## KNOWLEDGE PRESERVATION

Durable history must include more than completed tasks:

- observations and evidence;
- claims and epistemic status;
- failures and false positives;
- negative knowledge;
- experiments and limits;
- decisions and rejected alternatives;
- ideas left in the air;
- ideas without tickets or commits;
- architectural deductions;
- lost links and conceptual breakthroughs;
- unresolved questions;
- cross-IA disagreements/corrections;
- methodology changes;
- provenance and runtime identity;
- current gates and blockers.

## MEMORY WRITEBACK

Create/update durable memory when a session produces materially new knowledge or changes the operational model. Routine repetition does not require another archive.

When the operational model changes:

1. preserve the source historical record;
2. update `CURRENT-STATE.md` if current truth changed;
3. update `CONTEXT-INDEX.md` if routing changed;
4. update `SYMBIOSIS-MAP.md` if collaboration/capability learning changed;
5. update `UNRESOLVED-KNOWLEDGE.md` if latent knowledge changes status;
6. update `CANONICAL-ABSORPTION-2026-09-11.md` if source reachability or absorption status changes;
7. register new source records in `ARCHIVE-REGISTRY.md`.

Never silently erase contradictions from source history.

## DELETION SAFETY

`DELETE_SAFE=YES` is a **knowledge-preservation decision**, not a statement that the underlying engineering objective is closed.

The minimum condition is:

`DIRECT_CANONICAL_SOURCE=YES`
OR
`CANONICAL_KNOWLEDGE_ABSORPTION=YES`

plus provenance to the source, remote read-back, `KNOWLEDGE_LOSS_TEST=PASS`, `BLIND_RECONSTRUCTION=PASS`, and `NO_MATERIAL_KNOWLEDGE_ONLY_IN_CHAT=YES`.

A branch-only source archive may remain outside `main` when its material knowledge has been canonically absorbed and its source provenance remains recoverable. Do not merge an unrelated implementation branch only to relocate historical documents.

An open technical task does not by itself block historical-chat deletion. Unpreserved knowledge does.

## CURRENT REPOSITORY FACT

The operational-memory layer is on `main`. The exact current `main` HEAD must be checked from GitHub at use time; this file deliberately does not become the authority for a mutable branch tip.

The latest recorded P0-B validation target remains outside `main`:

`origin/audit/p0-b-repopath-on-hardened-base`

`c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3`

This distinction must be preserved.
