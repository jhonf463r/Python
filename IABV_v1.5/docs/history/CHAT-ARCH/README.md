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
4. `CURRENT-STATE-OVERRIDE-2026-09-17.md` — latest append-only operational corrections for the 2026-09-17 causal-learning frontier.
5. `SYMBIOSIS-MAP.md` — cross-IA capability and knowledge transfer.
6. `UNRESOLVED-KNOWLEDGE.md` — ideas, deductions and unresolved boundaries.
7. `CANONICAL-ABSORPTION-2026-09-11.md` — source reachability, absorption and deletion-readiness audit.
8. `ARCHIVE-REGISTRY.md` — source-history locations and identities.
9. Relevant historical source records selected by the objective.

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

The historical hardening target remains recorded separately:

`origin/audit/p0-b-repopath-on-hardened-base`

`c7abe9abcbf91d2cf31d7e3cdee37c19100a2fb3`

This is not the 2026-09-17 P0-B code baseline.

## 2026-09-17 ACTIVE MEMORY CHECKPOINT

The canonical current-state bridge and source record for the latest causal investigation are:

`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-17-001-symbiosis-causal-execution-learning.md`

The independent provenance audit of the reported L5 experiment is:

`IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-09-17-002-sonnet-l5-provenance-audit.md`

The active technical code baseline for that investigation is:

`main code baseline = 4b04566686c40cc6d48d64edb411b36867c54dcf`

Experimental branches are pinned separately:

`p0b-first-causal-break = 2d472ccaaf5a37773fed1d8e389e580812599c03`

`codex/world-grounded-learning-bridge = 55d3e2c93807202ec5d0177eda163e8de10418ef`

The latest independent audit found that the reported `tests/test_l5_causal_decision.py` does not exist at the cited SHA, in the clean working tree, or in the observable repository history/branch set searched. Therefore the reported L5 results are **NOT PROVEN / ARTIFACT-ABSENT** until the provenance contradiction is resolved.

For future prompts, the next actor is selected from the current uncertainty. At this checkpoint the best-fit actor is **Codex** for provenance reconciliation because the disputed report and cited branch are attributed to Codex work. Codex must first locate a verifiable artifact/commit, identify the actual runtime artifact provenance, or explicitly retract the L5 report. It must not redesign L5 at this stage.

If the artifact is recovered, route back to **Sonnet** for independent forensic audit before accepting L5. If a genuine architectural contradiction emerges, use **Opus 5**. If a concrete local runtime/test fix is needed after adjudication, use **Devin**. Do not invoke an actor merely to repeat a closed causal edge.

The required future prompt pattern is:

`OBJECTIVE → CURRENT VERIFIED STATE → EXACT PROVENANCE → CLOSED EDGES (do not reopen) → FIRST OPEN CAUSAL EDGE → EVIDENCE REQUIRED → FALSE-POSITIVE CONTROLS → STOP CONDITION → REQUIRED REPORT → NEXT ACTOR`

This prevents future AIs from reconstructing old prompt context from scratch and prevents an AI report from being promoted above the artifact actually verified.

## 2026-09-17 LATEST OVERLAY — PROVENANCE GAP CLOSED / L5 STILL OPEN

The preceding checkpoint above is historical and contains the **pre-recovery** state. It must not be used as the current routing instruction for the L5 artifact.

The latest append-only corrections are:

- `CHAT-ARCH-2026-09-17-004-cross-chat-symbiosis-reconciliation.md`
- `CURRENT-STATE-OVERRIDE-2026-09-17.md`

The recovered L5 artifact is now remotely verified on:

`audit/l5-artifact-evidence-2026-09-17`

with branch HEAD:

`f3e8a21c58fd73ad1b09ae11abae0cce915138cb`

Artifact path:

`IABV_v1.5/tests/test_l5_causal_decision.py`

Git blob:

`2844537f80c190a1351dac3a95f35f80cf79dc19`

SHA-256:

`E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`

Direct remote read-back now succeeds. The former artifact-location/provenance gap is therefore **CLOSED AT PUBLICATION LEVEL**.

Devin's fresh Windows result is preserved as reported runtime evidence: the byte-identical artifact passed the focused test with Python 3.14.4 / pytest 9.0.3 and produced `learned_pattern 0.0 → 1.0`, `total_score 7.545 → 10.095`, with a pattern id appearing after the learned state was persisted and reloaded.

This still does **not** promote L5 to proven under the strong definition, because the test directly evaluates `InteractionModeSelector._assess_candidate()` and uses one candidate rather than a competitive normal application selection. The treatment `VerifiedTransition` is also constructed in the test, so the test itself does not establish a fresh real-world episode as the source of the learned state.

CURRENT ROUTING:

`SONNET → independent forensic audit`

If that audit confirms only selector-level scoring influence, route the minimal competitive/multi-candidate normal-selector experiment to `DEVIN`. Use `OPUS 5` only for a genuine architecture contradiction. Do not spend `CODEX` on the already closed artifact-location problem.

The durable method is:

`objective → boundary → relevant memory → current read-back → capability/access fit → smallest discriminating experiment → independent verification → knowledge delta → writeback`

END OF LATEST OVERLAY

## PRIMARY STRATEGIC ENTRYPOINT — BIOSOFÍA / DEVELOPMENT

For future chats about biosofía artificial, self-use of IABV, autonomous development, scientific development loops, developmental acceleration, or reducing routine human coordination, start with:

`00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md`

Then follow `MEMORY-OPERATING-PROTOCOL.md` and `CONTEXT-INDEX.md` to activate only the relevant knowledge.

This entrypoint is strategic/research direction, not proof of achieved autonomy, consciousness, evolution or open-ended development.
