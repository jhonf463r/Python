## ACTIVE M1A KNOWLEDGE DELTA — Adversarial findings reconciled; successor review is the causal frontier (2026-10-22)

The Owner supplied a documentary `PASS_WITH_REPAIRS` report for immutable M1A v1.0.0 blob `8181c7c0cf6036c76cf365510e8d9665cf84e57e`. The attributed reviewer/session is `OWNER_REPORTED`, not an independently authenticated dispatch receipt. The eight findings (F-M1A-01..08) are dispositioned in the [review register](./CHAT-ARCH-2026-10-22-M1A-contract-v1-sonnet-review-receipt-and-finding-register.md), blob `396606e5744f0b3d0332f8ee9f02ec14cdcea588`; no accepted Owner design decision OG-M1A-01..07 is reopened.

A non-adopted [v1.0.1 successor candidate](./CHAT-ARCH-2026-10-22-M1A-consolidated-operational-block-scope-contract-v1_0_1-candidate.md) was drafted and fetched back; blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`. It encodes two critical universal construction invariants: (1) validation failure/unknown status can never be overridden by a selector mismatch, and (2) all-block aggregation is meaningful only over an authenticated, versioned, freshness-checked active-set snapshot; a missing list is not an empty list. It also makes every non-positive per-block state fail closed, requires auditable pre-selector stage results, verifies release freshness/revocation at the protected decision boundary, and makes traceability case mappings explicit. The candidate contains 38 proposed cases, none executed. The existing UAAL construction-completeness overlay and Entry 274 are reused; no parallel coordinator or runtime organ is claimed.

**Active task:** `M1A_CONTRACT_V1_0_1_CANDIDATE_TARGETED_ADVERSARIAL_REVIEW`. Use the [exact bounded handoff](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-candidate-targeted-review-handoff.md), blob `5612ada32a145d23cc836792cdf02608f4a706a3`. Dispatch is `NOT_DISPATCHED` until an attributable report is received. Review the candidate and each original finding against the five-part causal chain: requirement/source → precondition/authority → rule → discriminating case → verified evidence/Knowledge Delta. A saved register is not yet evidence of causal learning; the next applicable review must test whether these corrections actually discriminate the previous counterexamples.

`GOVERNANCE=KEEP_BLOCKED`; `IMPLEMENTATION=NOT_AUTHORIZED`; `TESTS=NOT_RUN`; `READ_LIST=FAIL_CLOSED`; `BRIDGE=BRIDGE_NOT_READY`. The active-block registry/attestation, runtime principal/trust anchor, producer allowlist, target resolver, authoritative revocation service and block-release mechanism remain `NOT_ESTABLISHED/UNVERIFIED`. No implementation or operational behavior is inferred from normative text.


---

## Construction completeness and bidirectional traceability overlay — 2026-10-22

Apply [the UAAL construction-completeness overlay](./CHAT-ARCH-2026-10-22-UAAL-construction-completeness-traceability-overlay.md) inside `UAAL-ROOT-001`; it is not a competing algorithm or task-routing source.

Before closing a design or preparing a handoff, require bidirectional traceability from source/requirement through assumption, rule or explicit authority decision, decision-table row, conformance case, evidence/receipt and canonical Knowledge Delta—and reverse-link every rule/claim to its authority and provenance. Enumerate independent dimensions and meaningful invalid/unknown/conflicting/revoked/untrusted states; distinguish derived technical logic from normative Owner/governance decisions and implementation/runtime/release permissions. Reconcile finding IDs and counts by category. If a mandatory row or authority is missing, report `DESIGN_INCOMPLETE` with the exact gap, not a soft PASS.

Each handoff must name exact destination/session, task/mode/authority, pinned source baseline, bounded paths, exclusions, expected artifact/receipt, acceptance and stop conditions. Fetch back every material write and later demonstrate reuse before claiming causal learning. This method amendment did not itself adopt policy; the Owner separately accepted the M1A design with `ACCEPT_M1A_RECOMMENDED_DESIGN_BASELINE`. The current top route is the bounded review of contract v1.0.0. Neither the policy receipt nor this method note authorizes implementation or proves runtime enforcement.

---

## Cross-chat owner–coordinator operating agreement — 2026-10-22

For project continuity, apply section 11 of the [ADHD-aware coordination protocol](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md) together with the active route in [CURRENT-STATE.md](./CURRENT-STATE.md). Persistent memory must preserve both ideas and task focus: every substantive idea receives a status, provenance and re-entry/closure condition; only one task is active; closed decisions are not reopened without new evidence; previous failed routes are not repeated unchanged; and every material update is fetched back and linked. Never claim causal learning merely because text was saved—the next applicable decision must demonstrate reuse.

---

## 2026-10-22 Owner-directed project focus and space-time coordination

Protocol: [ADHD-aware project coordination and space-time focus](./CHAT-ARCH-2026-10-22-adhd-aware-project-coordination-and-space-time-focus-protocol.md).

The Owner asks for structured longitudinal coordination because new ideas arrive rapidly and can pull work away from the project north star. Capture ideas without losing them; park them in an inbox; keep a single active task and next action unless immediate safety or an invalidated dependency requires interruption. Show evidence-based progress states and restore the active objective at each new chat. Existing DEVELOPMENT CONTROL TOWER + goal-lock/anti-drift remain the foundation; this is a method amendment, not proof that a runtime coordinator is already implemented. That paragraph is a historical coordination checkpoint, superseded for actor routing by the top snapshot of [CURRENT-STATE.md](./CURRENT-STATE.md); do not follow its old active-task label.

---

## 2026-10-22 `inferido` evolution summary and `probe_consumed` semantics (supplementary; route unchanged)

Detailed adjudication: [inferred evolution summary and probe semantics](./CHAT-ARCH-2026-10-22-inferred-evolution-summary-and-probe-consumed-semantics.md).

The owner-reported chat message says Ollama is winning for `general`, eight proposals are in sandbox/validation, Ollama local appeared as a discovery, three candidates were discarded, and the latest “strong decision” was `probe_consumed`. Public main source supports a more limited reading: `probe_consumed` logs a structured self-examination signal; the documented method says it does not execute the actual probe or change real state. The evolution summary builds its `in_validation` list from `deferred` decision-log entries and caps it at eight, without verifying that each has an active sandbox run. A detected discovery is a candidate signal, not proof of promotion or measured superiority. The UI maps `evidenceTag=inferred` to “inferido”; this marks the message as inferred, not confirmed.

No local runtime, current decision log, or local `data/`/SQLite state was inspected, and no tests/probes/runtime/tool calls or mutations were performed. Treat Ollama's claimed win and the proposal/discard counts as `INFERRED / OWNER_REPORTED` until backed by existing correlated IDs, metrics, run/verdict receipts and a verified promotion. Do not run another broad scan. The active route stays `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`; preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `LOCAL_SOURCE_READ=NOT_RUN`, and `REAL_TRANSPORT=NOT_RUN`.

---
## 2026-10-22 broad auto-scan / claimed mutations (OWNER_REPORTED; route unchanged)

Detailed reconciliation: [broad auto-scan out of scope and unverified mutations](./CHAT-ARCH-2026-10-22-broad-autoscan-out-of-scope-and-unverified-mutations.md).

IABV answered the scoped governance-route request with a broad scan instead. The pasted report says 282 source files were modified and uses `Branch: HEAD` without a branch name or before/after commit receipt; the actual `git pull` outcome is not established. It also claims CUDA/GPU environment changes, qwen3:8b reload, and token-alias mapping, none authorized by the request or independently verified. Claimed test/syntax counts lack correlated artifacts. No branches should be cleaned; no reset, further pull, scan, model reload, credential/environment change, or improvised rollback should occur. Preserve the worktree and do not reproduce browser-account identifiers or secret values.

This does not solve or alter the active route: `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`. The immediate response to the mis-scoped behavior should be stop-and-report-only containment, then continue only via a documented governance/administrative surface. If none exists, declare `SUPPORTED_SCOPED_READ_ROUTE=NOT_FOUND` and stop. Preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `LOCAL_SOURCE_READ=NOT_RUN`, `REAL_TRANSPORT=NOT_RUN`, `LOCAL_WORKTREE=UNTOUCHED`.

---

## 2026-10-22 RAM-monitor coverage reconciliation (supplementary; no routing change)

Detailed evidence record: [llama monitor coverage gap and unresolved RAM causality](./CHAT-ARCH-2026-10-22-llama-monitor-coverage-gap-and-ram-causality-unresolved.md).

The supplied terminal report observed `llama-server.exe` absent only in visible samples from 2026-10-21 22:25:46–22:28:51. No visible samples cover the interval to the reported end at 2026-10-22 09:14:51, so continuous two-second/15-minute coverage is unverified. Total RAM was not captured in these waiting samples; Ollama metrics were not captured and `/api/ps` was not queried. The reported 70.14–72.98% RAM-used range does not attribute cause. `MONITOR_COVERAGE=INCOMPLETE_OR_UNVERIFIABLE`, `RAM_DIAGNOSIS=INCOMPLETE`, `OLLAMA_RAM_CAUSALITY=UNRESOLVED`, `FIX=NOT_APPLIED_OR_VERIFIED`; configuration unchanged and no process actions reported.

Do not extend monitoring automatically or infer the process was absent throughout the gap. This note does not change the sole active route in `CURRENT-STATE.md`: `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`. Preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`, and `LOCAL_WORKTREE=UNTOUCHED`. No bridge launch, reader bypass, process/configuration changes, or runtime tests.

---

## Supplementary continuity delta — resource metacognition + cross-chat learning (2026-10-21)

Detailed immutable record: [resource-metacognition-cross-chat-learning-and-bridge-continuity](./CHAT-ARCH-2026-10-21-resource-metacognition-cross-chat-learning-and-bridge-continuity.md). It reconciles the 22:15 owner-reported RAM capture (zero `llama-server.exe`, no models listed by the existing Ollama API, `ollama.exe` 26.47 MB working set / 61.79 MB private; global RAM use 75.58–76.07%) with the earlier un-reproduced report of ~60% attributed to `llama-server.exe`. Historical cause and IABV startup path remain unresolved; no fix is verified.

Learning: a resource-pressure label/confidence is not an auditable decision receipt. Future resource gating must correlate measured observation → exact threshold/policy → defer decision → authorized action (if any) → post-measurement → verified outcome → reusable experience. A bounded process monitor is diagnostic, not self-stabilization. Lighter/lazy/alternative inference tooling is a proposed research track only, requiring a governed source trace and comparative quality/latency/RAM/VRAM tests before any change. Human-interaction lessons, scope/provenance discipline and read-back verification are retained in the detailed record.

This note is supplementary and does not supersede the sole route below. Preserve `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`, `LOCAL_WORKTREE=UNTOUCHED`; the only active next step remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`. No reader bypass, process changes, local launch or real transport.

---

## 2026-10-21 CURRENT ROUTE POINTER — POST-TEST RECONCILIATION

The sole actor-routing authority is the top snapshot of `CURRENT-STATE.md`. Latest route update: candidate test run completed on the existing sparse-first clone (76 collected, 74 passed, 2 failed; exit 1). The six new target-scope tests were collected and are not among the two failures. The failures are the existing `_FakeWorldModelService.scan_stats` test-fixture mismatch, outside the authorized target-scope fix; candidate remains unchanged and unmerged. The latest local executor inspection read zero source files because the normal MCP reader denied the operation with `governance_blocked=true` / `operational_block_active`. Do not rerun the test prompt, retry the reader, use another reader to bypass the gate, or launch the bridge. The next required edge is a supported governance-owned scoped read route for the already-authorized static inspection; the exact mechanism remains `UNRESOLVED`. See `CHAT-ARCH-2026-10-21-local-executor-read-denied-and-scopefix-test-result.md` and the current snapshot. Keep `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`, `LOCAL_WORKTREE=UNTOUCHED`, `CANDIDATE_MERGED=NO`; executor identity and effective policy remain `UNRESOLVED`.

> **Supplementary adjudication (2026-10-21; does not supersede CURRENT-STATE routing):** The supplied human–IABV interaction audit finds request interpretation and scope discipline `FAIL`, causal-learning evidence `FAIL`, progress observability `PARTIAL`, and long-running multi-IA readiness `NOT_READY`. The claimed deletion of 31 remote branches and GPU/token changes remain `OWNER_REPORTED`, not independently verified. See [the interaction audit](./CHAT-ARCH-2026-10-21-human-iabv-interaction-audit.md). The sole active next step remains the supported governance-owned scoped-read route; keep `GOVERNANCE=KEEP_BLOCKED`.> **Supplementary incident (2026-10-21):** IABV reported `resource_pressure_critical`, later `wrong_thread` rejection, and then a default-browser fallback without DOM/CDP confirmation. All are owner-reported, not independently verified. Treat the fallback as out-of-scope; do not log in, relay a browser response, retry via an alternate path, or launch the bridge to bypass the block. The active next step remains a supported governance-owned scoped-read route. See [handoff incident record](./CHAT-ARCH-2026-10-21-codex-handoff-resource-pressure-wrong-thread-browser-fallback.md).
> **Supplementary incident (2026-10-21):** The owner's bounded Ollama/RAM prompt was answered by another broad auto-scan, not the requested per-process RAM diagnosis. IABV reported Ollama/model loaded and again claimed GPU correction plus token-alias mapping, while giving no RAM before/after or per-process evidence. All are `OWNER_REPORTED`; do not infer that IABV restarted Ollama or that corrections applied. Do not repeat broad scan, reload models, change credentials/GPU, delete branches or initiate browser/Codex handoff. See [Ollama/RAM scope incident](./CHAT-ARCH-2026-10-21-ollama-ram-request-not-honored-repeat-autoscan.md).
> **Supplementary RAM evidence (OWNER_REPORTED, 2026-10-21 18:22):** Direct Codex/PowerShell snapshot reported RAM 16,088 MB total, 4,962 MB free (69.2% used), and one `ollama.exe` process with 18.4 MB working set / 60.7 MB private memory. Opera/ChatGPT processes were among the largest visible working sets. This disproves neither a prior peak nor resident-model memory: model residency and temporal causality remain unresolved. Next bounded step: in the same direct Codex session, GET `http://127.0.0.1:11434/api/ps` only if already listening and correlate with a contemporaneous read-only process/RAM snapshot; do not start Ollama or load/reload models. See [process snapshot record](./CHAT-ARCH-2026-10-21-ollama-readonly-process-snapshot-and-next-query.md). The later static IABV reasoning audit remains separate; bridge launch remains blocked.
> **Ollama startup causality clarification (2026-10-21):** the direct Codex/PowerShell snapshot sampled Windows processes but did not launch IABV or reproduce its startup. It cannot tell why opening IABV activates Ollama or whether local inference is required. One snapshot showed 69.2% RAM use and ollama.exe at 18.4 MB working set / 60.7 MB private; Opera and ChatGPT were among the larger consumers. These are owner-reported snapshot facts, not causality evidence. Next source task, only through the legitimate governance-owned scoped-read route: trace local IABV startup -> Ollama launch/connect -> model/provider selection and whether the path is eager, lazy, warm-up, health-check or fallback. Do not launch IABV for reproduction, use another reader, reload a model or change configuration. See [startup-causality record](./CHAT-ARCH-2026-10-21-ollama-startup-causality-not-tested-by-codex-snapshot.md).

---

## 2026-10-13 CANONICAL ROUTE — ENTRY 280: C6 FAIL RECONCILIATION / AMENDMENT 274.5

Canonical artifact: [CHAT-ARCH-2026-10-13-280-m0b-r8-1-c6-delta-adjudication-and-amendment-274-5.md](./CHAT-ARCH-2026-10-13-280-m0b-r8-1-c6-delta-adjudication-and-amendment-274-5.md) — blob `6d7d7f4966e1224456e00410c812395e6a5c598f`, commit `0a462d66071f2d354e8a299ffaf859b3aeac61d5`.

The supplied Sonnet/Claude delta review returned `FAIL` for Entry 279. Entry 280 records a bounded corrective amendment 274.5 for S1–S4, S6–S8 and S11: a complete anti-rollback epoch rule; explicit preview/open/final-gate phases and non-oracular requester outputs; separate requester/internal/lifecycle/status result fields; operation-level idempotency and status-query semantics; a fixed requester-visible 120-second approval window; the ordered R2 result taxonomy with `DECISION_NOT_APPLICABLE`; bounded detection-overhead accounting and deterministic concurrency oracles; and one physically contiguous parseable manifest in the next consolidation.

Entry 278 and Entry 279 remain preserved historical documents; Entry 280 is an amendment, not a consolidated contract and not a `PASS`. Residual findings S5, S9 and S10 remain explicit acceptance blockers: compound/missing fixtures; delivery acknowledgement authority/recovery; and full precedence/time-boundary mutation coverage. They must be resolved before a new candidate is accepted.

Next actor: Sonnet/Claude for one targeted delta review of Entry 279 plus Entry 280, restricted to S1–S4, S6–S8 and S11. If it passes, resolve S5/S9/S10 before constructing a new single consolidated contract and verifying it by fetch-back. No broad source archaeology.

Evidence boundary: Entry 278, Entry 279 and Entry 280 are public documentary objects fetched with recorded blob SHAs. Repairs and tests are `PROPOSED`; all implementation/runtime/platform claims remain `UNPROVEN`.

Operational posture: `KEEP_BLOCKED`. No local M0A access, blocked-reader retry/bypass, implementation, tests/builds/runtime, credential inspection, authentication, installation/update or launch. Contract review cannot grant read authority or release a governance block.

---

## Historical route — ENTRY 279: C5 delta adjudication / amendment 274.4 (superseded as current route by Entry 280)

Canonical artifact: [CHAT-ARCH-2026-10-13-279-m0b-r8-1-c5-delta-adjudication-and-amendment-274-4.md](./CHAT-ARCH-2026-10-13-279-m0b-r8-1-c5-delta-adjudication-and-amendment-274-4.md) — blob `fccd67f375c265986215210b5161e684c65b7e27`, commit `5051c07c7db33390ba72ed9375e23c27782d7ef0`.

The supplied Sonnet/Claude delta review of Entry 278 returned `PASS_WITH_REPAIRS`. Entry 279 records P1–P10 as one proposed amendment: complete deterministic per-fixture results; align overlapping gates; add operation-level idempotency; separate persisted `EXPIRED` decision status from `DECISION_EXPIRED` operation denial; define one delivery lifecycle; cover every denial/precedence and the exact clock boundary; split composite fixtures; close object-dependent pre-approval oracles; mark the inherited C3 grammar as superseded; and apply the lower of the decision ceiling and the hard cap.

Entry 278 remains an immutable historical candidate and is not overwritten. Entry 279 is also not yet an accepted baseline. The next actor is Sonnet/Claude for one targeted delta review of Entry 278 plus Entry 279 only. If that passes, ChatGPT/coordinator must produce a new single consolidated candidate, fetch it back, and then request one delta review. Do not repeat broad source archaeology.

Evidence boundary: Entry 278 and Entry 279 are verified as public documentary objects; the repairs and proposed tests remain `PROPOSED`. Source fidelity to historical blobs is not newly reverified by the C5 reviewer. All implementation/runtime/platform properties remain `UNPROVEN`.

Operational posture: `KEEP_BLOCKED`. No local M0A access, blocked-reader retry/bypass, source implementation, tests/builds/runtime, credential inspection, authentication, installation/update or launch. Contract review cannot authorize a read or release a governance block.

---

## Historical route — ENTRY 278: consolidated M0B-R8.1 contract candidate (superseded by Entry 279)

Canonical artifact: [CHAT-ARCH-2026-10-13-278-m0b-r8-1-consolidated-contract-candidate-274-3.md](./CHAT-ARCH-2026-10-13-278-m0b-r8-1-consolidated-contract-candidate-274-3.md) — blob `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`, commit `43a9cc982317ddbc090dcfe3dd482bd3508fa773`.

Entry 278 combines Entry 274's base clauses, the clean historical Entry 275 C2 amendments, Entry 276's C3 grammar/guardrails and Entry 277's C4 R1–R9 repairs into one full-text contract candidate and a single conformance manifest. Fetch-back verified one top-level heading, 106 globally unique manifest rows, no ambiguous active A29/A47 aliases, dedicated tests for the grammar boundaries and pre-approval path-oracle cases, and no risky dollar-before-Markdown-backtick sequence. Composite cases identified during consolidation were retired and split where needed. C3-10 precedence is retained: BLOCK_SCOPE_UNEVALUABLE dominates BLOCK_RELEASE_UNSUPPORTED when scope evidence is incomplete; otherwise an applicable unreleased block returns BLOCK_RELEASE_UNSUPPORTED.

Status: `M0B_R8_1_CONSOLIDATED_CANDIDATE_274_3_PENDING_TARGETED_DELTA_REVIEW`; operational posture: `KEEP_BLOCKED`. This is a proposed design artifact, not an accepted baseline or implementation evidence.

Provenance: Entry 274 blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`; clean historical Entry 275 body at [its immutable commit](https://github.com/jhonf463r/Python/blob/1e644ee663118b6567018cd2211c107e48489d4c/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-275-m0b-r8-1-contract-amendment-274-1.md) (blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a`); Entry 276 blob `023272e14ec5c6ef26b904c47c3fed66eb93c532`; Entry 277 blob `b9e4071e0b8cbeb3354ec7218d46864419402a7b`. The current Entry 275 path remains a supersession notice and is not normative.

Next actor: Sonnet/Claude — one targeted delta review of Entry 278 only. Challenge merged precedence, no-oracle states, total denial code order, per-case result determinism, test-ID uniqueness and R1–R9. Return `PASS`, `PASS_WITH_REPAIRS` or `FAIL`; for every survivor provide exact section, counterexample, minimal repair and discriminating test. No broad source archaeology.

No implementation, product-source/config edits, tests/builds/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update or launch. Acceptance of this candidate cannot release a governance block. Keep `KEEP_BLOCKED`.

---## Continuity method delta — C2 repairs consolidated as amendment 274.1 (2026-10-13; Entry 275)

Canonical: [CHAT-ARCH-2026-10-13-275-m0b-r8-1-contract-amendment-274-1.md](./CHAT-ARCH-2026-10-13-275-m0b-r8-1-contract-amendment-274-1.md).

The second adversarial report found C2-01–C2-11 in Entry 274. Entry 275 is the single proposed amendment for targeted re-review; don't split it into scattered patch prompts. The supplied review says it read documents, not source code. Do not promote textual repairs to implementation facts.

R8.1 amendment rules: requester is untrusted and may run same-user code; fresh Owner approval requires independently verifiable user confirmation bound to the nonce and full safe scope, with fail-closed behavior if requester/UI separation cannot be enforced. Registration and block lineage are authority-controlled; a new checkout ID alone never proves a block non-applicable. Existing sensitive-file denylist and workspace containment remain mandatory and can only be narrowed, never weakened. Nonce consumption and decision issuance are atomic; active decisions expire on restart; ledger rollback, integrity, durability and idempotency fail closed. Staging, release authorization and delivery outcome are separate states. Pre-approval path preview follows the same safe root-handle rules, uses no unapproved content reads, and hides external-path existence. V1 path grammar is restrictive; path authorization combines canonical form, bound object identity, containment and existing denials. Listing limits count raw entries; invalid entries deny the whole listing. Require positive and exact-boundary tests, durable-recovery tests, and platform-specific race evidence; mocked I/O alone is insufficient.

The governing release gate remains separate: an applicable block without a supported governance-owned release is terminal `BLOCK_RELEASE_UNSUPPORTED`. That is a design conclusion, not a capability; no M0A unlock follows. Next: Sonnet/Claude's targeted review of Entry 275. No code modification, tests/runtime, local read or launch; `KEEP_BLOCKED`.

---

## Continuity method delta — consolidate R8.1 after adversarial review (2026-10-13; Entry 274)

Canonical: [CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).

When a focused adversarial review finds contract weaknesses, consolidate the effective MUST/MUST NOT rules into one normative document instead of layering ambiguous addenda. Keep historical Entries 272–273 for provenance; Entry 274 is the proposed consolidated text pending a second challenge. The review input explicitly says no code was read, so only documentary wording gaps can be considered confirmed; runtime and implementation remain `UNPROVEN`.

R8.1 requires unconditional fresh interactive Owner approval in v1; issuer-generated nonce/IDs and direct trusted-UI-to-issuer attestation; full safe display of target/path/limits/recipient; server-side, durable, requester-session-bound decisions; independent governance-owned block releases (otherwise `BLOCK_RELEASE_UNSUPPORTED`); explicit fail-closed multi-block scope semantics; mandatory target/root/worktree and authorized-object identity without whole-tree scans or spawned Git; race-resistant same-object handle containment; mandatory durable intent/completion; non-optional authoritative revocation; trusted-clock/expiry checks before operation and before content release; atomic budgets; no prefix/wildcard grants; whole-request denial on caps; and recovery that halts reads for orphan intents or unavailable authority state.

Do not convert “text gap closed” into “implementation proven.” The target platform, handle confinement, trusted issuer/principal, ledger, block scope model, revocation source and release mechanism remain open. Next: Sonnet/Claude adversarially challenge Entry 274 only. No code changes, tests/runtime, local M0A access or launch; keep `KEEP_BLOCKED`.

---

## Continuity method delta — independent contract review and R8.1 hardening (2026-10-13; Entry 273)

Canonical: [CHAT-ARCH-2026-10-13-273-m0b-r8-independent-contract-review.md](./CHAT-ARCH-2026-10-13-273-m0b-r8-independent-contract-review.md).

A read-decision contract may correctly separate diagnostic, approval, issuer, reader verifier and durable receipt while still leaving implementation-critical race semantics underspecified. Before accepting a reader contract, tie path authorization to the actual opened filesystem object; a pathname check followed by a later open can have a TOCTOU gap. If safe handle-based containment is unavailable, fail closed.

Also distinguish block reporting from correct block applicability. Entry 269 notes the inspected active-block filter uses `assistant_kind`, not `target_scope`; do not assume that helper proves all scope classes are evaluated. Require explicit supported scope semantics and tests for global, matching and nonmatching scoped blocks, multiple/unknown scopes, and absent target identity. This discrepancy is an independent hazard, not a proven cause of the M0A refusal.

Entry 273 accepts R8 only as a provisional design baseline with these two required clarifications. Next: one focused Sonnet/Claude adversarial challenge of Entries 272–273; no broad source search, implementation, or local read. Keep `KEEP_BLOCKED`.

---

## Continuity method delta — diagnostic, approval, read grant and receipt are separate contracts (2026-10-13; Entry 272)

Canonical: [CHAT-ARCH-2026-10-13-272-m0b-r8-read-decision-contract.md](./CHAT-ARCH-2026-10-13-272-m0b-r8-read-decision-contract.md).

Do not collapse a descriptive diagnostic, a generic approval result, a scoped read decision and a post-operation receipt into one `approved` boolean. A fresh-human-required gate must reject ApprovalMemory auto-resolution unless the Owner has explicitly chosen a different policy. Verify exact target identity, operation, path, expiry, revocation, budgets and applicable governance blocks in the reader immediately before each operation.

A successful grant requires a trusted issuer/integrity boundary and verifiable principal provenance. An unverified `approved_by` string or caller-supplied grant object is not authority. Preserve path/sensitive-file/size/list caps; reserve audit and budget state before reading; do not disclose staged file content until the success receipt commits. If the final record fails after an internal read, do not claim that read was undone: discard staged output, stop subsequent reads and require reconciliation. Entry 272 is a contract proposal, not an implementation or local-access authorization.

---

## Continuity method delta — approval outcome is not identity proof (2026-10-13; Entry 271)

Canonical: [CHAT-ARCH-2026-10-13-271-m0b-r7-approval-broker-chain-adjudication.md](./CHAT-ARCH-2026-10-13-271-m0b-r7-approval-broker-chain-adjudication.md).

When reconciling an approval flow, trace both manual and automatic paths. A generic approval outcome must not be assumed to contain an authenticated actor identity; inspect the result schema and callback inputs. If a pre-approver can resolve requests without UI, a positive result is not proof of fresh human presence. Keep this distinction separate from evidence about what the model/consumer accepts.

For the IABV repo-read gate, a dedicated contract must reject memory-auto-resolved results when fresh interactive approval is required, bind identity and allowed paths to the exact server/workspace/checkout, and fail closed when actor provenance or the issuer/verifier chain is missing. Entry 271 records corrected blobs/anchors. No local M0A access or implementation is authorized.

---

## Continuity method delta — M0B-R6 direct-reference pass and line-anchor correction (2026-10-13; Entry 270)

Canonical: [CHAT-ARCH-2026-10-13-270-m0b-r6-authority-chain-reconciliation.md](./CHAT-ARCH-2026-10-13-270-m0b-r6-authority-chain-reconciliation.md).

When an audit names an immutable commit, fetch the complete named blobs and verify their SHA before using source line anchors. Do not infer blob identity from a web-page line link or silently carry line numbers across different source objects. In this case the supplied model/bootstrap ranges did not match the declarations at the pinned blobs; Entry 270 records corrected anchors and checks that the same relevant blobs are present on current `main`.

Distinguish a schema/consumer from a trusted issuer. The Devin-specific `ExternalActionAuthorization` consumer is not a repository-read grant; a `VALIDATED` status and free-form `approved_by` field do not prove owner identity or checkout-scoped authority. The bounded direct-reference pass found no production issuer and stopped before general identity/auth exploration. Keep local M0A blocked.

---

## Continuity method delta — reconcile R5 anchors before routing the next authority search (2026-10-13; Entry 269)

Canonical: [CHAT-ARCH-2026-10-13-269-m0b-r5-reconciliation-and-next-owner-gate.md](./CHAT-ARCH-2026-10-13-269-m0b-r5-reconciliation-and-next-owner-gate.md).

A supplied audit's architectural conclusion can be sound while its line anchors are wrong. Re-fetch named files at the declared immutable commit, record Git blob SHAs, locate exact declarations and correct anchors before using them as evidence. Do not repeat the whole audit when corrected objects resolve the discrepancy.

R5 found no separate supported audit-read diagnostic plus checkout-scoped decision in the inspected public paths. The existing refusal payload is not a separate diagnostic API; an observation grant is not a repository-read authorization. Preserve existing path/sensitive-file/size/list caps.

RQ219/RQ220's bounded mutation-authority discovery is already closed; do not repeat it. Current-state records Model A selected for the first supervised prototype; do not re-ask A/B. A distinct read-only inspection of additional identity/authority sources beyond prior scope remains behind an explicit Owner scope gate. Do not silently expand source scope or issue Codex a prompt implying authorization. Once authorized, Codex searches only direct references and call sites, stops at a broader identity subsystem, and returns SHA/line-grounded evidence.

Canonical route must be reconciled in full after every write: CHAT-ARCH README → CURRENT-STATE → CONTEXT-INDEX → MOP → SYMBIOSIS-MAP → UNRESOLVED-KNOWLEDGE → ARCHIVE-REGISTRY → AGENTS → new record.

---

## Continuity method delta — repair the canonical memory front door and recompute the next actor (2026-10-13; Entry 268)

Canonical: [CHAT-ARCH-2026-10-13-268-m0b-memory-front-door-and-governance-route-reconciliation.md](./CHAT-ARCH-2026-10-13-268-m0b-memory-front-door-and-governance-route-reconciliation.md).

Before declaring continuity updated, verify the entire protocol route, especially the actual canonical `docs/history/CHAT-ARCH/README.md`; a root README 404 is not evidence that this front door is absent. An update to CURRENT-STATE and CONTEXT-INDEX is incomplete if the README-first route still points to an older episode. Verify all route pointers after writeback.

Use current-state's owner decisions before asking again. Current CURRENT-STATE records RQ224 Model A selected for the first supervised MCP prototype. That supersedes the older RQ224 document's A/B question for that prototype. It does not close the underlying receipt/authority problem, authorize broader identity search, or authorize audit-read access/implementation. Do not re-ask A/B.

For the audit-reader path, distinguish: (a) refusal response with reason/detail/block metadata, (b) a standalone minimal diagnostic, and (c) a separate trusted, checkout/path-scoped read decision. The existing public reader gate can report a refusal; this does not grant access. Observation grants only authorize their explicitly scoped observation action. If the exact public call paths have been checked and no supported release exists, stop generic archaeology and produce the bounded code-facing contract/test spec. Never bypass the blocked local reader or infer local M0A identity from public source.

Always recompute next actor from the latest source baseline, first open edge, capability fit, authorization and expected information gain; do not inherit a stale suggestion. After writeback, independently re-fetch every route entry point and confirm the intended episode is first. Persistence is not learning; preserve the later causal-reuse requirement.

---

## Continuity method delta — preserve R9.2/R10 provenance and distinguish preliminary success from adaptive completion (2026-10-13; Entry 267)

Canonical: [CHAT-ARCH-2026-10-13-267-m0b-r9-2-r10-continuity-reconciliation.md](./CHAT-ARCH-2026-10-13-267-m0b-r9-2-r10-continuity-reconciliation.md).

When a new chat supplies a package of prior findings, reconcile it against the pinned public ref and the existing canonical trail before producing another general audit. Re-fetch exact high-value object SHAs/line anchors where feasible; preserve unresolved historical line discrepancies without reopening them unless new evidence discriminates between hypotheses. Never present owner-supplied local reports as independently inspected local source.

Track bridge stages separately: adapter availability, preflight, sandbox, actual execution, response capture, correlation, validation, persistence, interaction learning, adaptive evaluation, durable receipt and later decision reuse. In particular, inspect whether a preliminary result is persisted or counted before the final external result exists. At the pinned public baseline, execute_task remembers the sandbox result and ToolMemory increments success_count based on result.success without conditioning on stage/validation. Treat this as a static eligibility defect-risk and correct it in a future authorized implementation; do not infer a live incident.

Reuse the existing ToolTeachService, ToolSandbox, ToolValidator, ToolMemory, InteractionLearningService, repository, ViewModel, orchestrator and evolution service when source-compatible. Do not create a duplicate brain, router or memory. Use execution_id for each attempt, explicit stage/provenance, validation gating, idempotent durable consumer receipt and task/result/evaluation correlation. Do not require conversational capture from non-conversational adapters.

Continuity is not transcript dumping: persist objective/context time, evidence/provenance, causal hypothesis, authorized discriminating action, observation, verification/reconciliation, knowledge/method/routing delta and an explicit next edge. Persistence is not learning; causal improvement requires a later traced decision and an outcome comparison.

Keep planes distinct: user-facing IABV UI; background coordination/correlation bridge; Codex execution environment. The desired bridge is a background path visible from the UI, not another chat panel. AI/tool-first retrieval remains mandatory, yet a local governance block must never be bypassed. Separate design acceptance, local source-read authority, implementation, offline tests and real runtime/launch permissions. Owner choice C and KEEP_BLOCKED remain in force until each relevant gate is explicitly resolved.

---

## Continuity method delta — never promote observation consent to repository-read authority (2026-10-13; entry 266)

Canonical: [CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md](./CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md).

A permission label and a similar-sounding operational objective are not evidence of equivalent scope. In the published Control Center, `approve_observation_permission` is specifically an observation action and its inspected test scope is `observe_window_content:codex`. Do not treat it as approval to read a repository, release the audit route, or establish the MCP checkout identity unless the exact consumer and scope are proven in source.

Keep read-only audit release separate from mutation authority. Existing mutation-authority policy records do not automatically authorize implementation of a new diagnostic/grant mechanism. Trace only existing in-scope call paths and stop at any explicit Owner gate.

---

## Continuity method delta — a local precondition stop must not freeze independent work (2026-10-13; entry 265)

Canonical: [CHAT-ARCH-2026-10-13-265-autonomy-run-paused-too-early-public-gate-contract.md](./CHAT-ARCH-2026-10-13-265-autonomy-run-paused-too-early-public-gate-contract.md).

When local source access is blocked, preserve that gate but classify work by dependency. The blocked task may not continue through another reader, but independent static research on a pinned public source, architecture analysis, contract design and non-invasive test specification can proceed. An autonomous executor must record the dependency and select the next executable task instead of stopping the whole mission.

For the MCP governance issue, distinguish the documented blocked payload from the actual payload of a prior call; never reconstruct live evidence from public source. A minimal diagnostic explains only the applicable block metadata and must not itself grant access. A separate, trusted, scoped decision must bind the intended server/workspace/checkout, operation, allowlisted paths and expiry. Reconcile previously accepted authorization policy before proposing implementation.

---

## Continuity method delta — never confuse owner consent with a runtime grant (2026-10-13; entry 264)

Canonical: [CHAT-ARCH-2026-10-13-264-m0b-r4-governance-diagnostic-missing.md](./CHAT-ARCH-2026-10-13-264-m0b-r4-governance-diagnostic-missing.md).

When a limited read is owner-authorized but the runtime still returns or preserves a governance block, do not retry through another reader or infer the target from a tool namespace. If the current session exposes no safe operation for the exact decision, record the distinction: owner consent exists; runtime release and server/checkout provenance do not. The missing seam is a supported narrow block diagnostic + direct execution-target identity + auditable scoped decision. Do not query a broad machine snapshot merely to obtain one gate field. Keep the task blocked until a legitimate mechanism provides the decision; then resume at the first discriminating source comparison, not generic research.

---

## Continuity method delta — compare new transport candidates with the existing working-shaped route (2026-10-13; entry 263)

Canonical: [CHAT-ARCH-2026-10-13-263-m0b-r3-autonomy-bridge-adjudication.md](./CHAT-ARCH-2026-10-13-263-m0b-r3-autonomy-bridge-adjudication.md).

When a new transport such as Codex App Server looks promising, do not assume it is superior until compared with the best existing path. In public main, `ExternalAssistantToolAdapter` delegates to a runner capable of desktop interaction and Codex rollout capture; the `codex_installed` card is unavailable/unvalidated, and pending capture remains unvalidated. M0A's reported local App Server adapter remains UNPROVEN until local source is legitimately observed. For ChatGPT, an MCP server can provide tools to its turn, but separate initiation and correlated return still need an architecture. The next source audit must compare both Codex routes, trace into the existing consumer, and preserve governance/identity constraints. No bypass or duplicate coordinator/memory.

---

## Continuity method delta — governance gate and source-tool provenance before retry (2026-10-13; entry 261)

Canonical: [CHAT-ARCH-2026-10-13-261-m0b-r1-governance-gate-and-tool-provenance.md](./CHAT-ARCH-2026-10-13-261-m0b-r1-governance-gate-and-tool-provenance.md).

When a local reader returns `governance_blocked=true`, classify the outcome as a governance/precondition stop, not a source/code finding. Preserve the exact structured `reason`, `detail`, applicable block/gate metadata and tool/server identity where available. Do not repeat the same call or route around policy.

Before another source retrieval, reconcile which workspace/server the tool addresses. A namespaced connection such as `rsk01a5` may refer to a separate historical experiment/worktree; treat this as a hypothesis until the root mapping is verified. Do not equate similarly named workstreams.

Avoid full environment/world snapshots when only a governance reason is required if those snapshots include unrelated focus/window information. Use narrow authorized metadata only. If the gate cannot be diagnosed within the allowed surface, stop and return the exact owner/governance decision required. No automatic clearing or bypass.

---

## Continuity method delta — AI-first local evidence retrieval; no manual handoff by default (2026-10-13; entry 260)

Canonical: [CHAT-ARCH-2026-10-13-260-ai-first-local-source-inspection-boundary.md](./CHAT-ARCH-2026-10-13-260-ai-first-local-source-inspection-boundary.md).

Operating rule: before asking the Owner to copy code, exhaust available authorized tools in this order: fetch the exact published ref and files; search the repository and branches where supported; inspect any connected local source/workspace tool; verify the tools actually available in the current session. Do not confuse a product capability with a capability connected to this conversation. Do not substitute published main for dirty/uncommitted local source.

Separate access planes: (1) ChatGPT's connected remote tools; (2) Codex locally launched in an authorized workspace; (3) the live IABV process and its effective filesystem/tool wiring. Permission does not transfer transitively between them. Here the connected session has GitHub/web access but no direct Windows filesystem bridge. Local Codex is not to be launched because the Owner's option C remains active.

Only request a minimal manual source handoff if the evidence is local-only and no authorized machine path exists; state exactly why it cannot be retrieved automatically. If later authorized, prefer a read-only machine-generated evidence packet with paths, bounded excerpts, hashes, provenance and missing-edge markers. Never include secrets. No launch, local command, test/build, preflight, implementation, or promotion without separate authorization.

---

## Continuity delta — narrow local source handoff after queued/no-content reader result (2026-10-13; entry 259)

Canonical: [CHAT-ARCH-2026-10-13-259-local-source-handoff-blocked.md](./CHAT-ARCH-2026-10-13-259-local-source-handoff-blocked.md). The queued/no-content outcome is Owner-reported; it proves no local code property. Avoid repeating the broad 18-file read request. Ask for only: (A) actual local CodexAppServerToolAdapter class and policy/request/result methods; (B) bootstrap registration plus the concrete SafeUI/ToolTeachService dispatch caller; (C) result consumer/evaluator call site; (D) task-ID repair source/test only if relevant. Existing remote canonical docs need not be pasted again.

Preserve local-vs-remote provenance. Do not run shell/Git, tests, builds, Codex/App Server/IABV, or inspect secrets to obtain source. Owner choice C continues: no launch, preflight or implementation. Immediate edge: LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED.

---

## Continuity method delta — owner selects C; code-candidate boundary remains unproven (2026-10-13; entry 258)

Canonical: [CHAT-ARCH-2026-10-13-258-owner-keeps-codex-blocked-static-candidate-boundary.md](./CHAT-ARCH-2026-10-13-258-owner-keeps-codex-blocked-static-candidate-boundary.md). The Owner explicitly selects C: do not launch Codex unless a compatible route is proved; continue only static design/review. Entry 249's no-selection state is historical and is superseded for the launch gate. Do not infer A/B home/auth selection.

New current-main source evidence: ToolRegistry picker logic routes to a card but does not authorize paths/commands/cost; ToolTask/ToolResult contain generic identity/output/artifact fields, not an independently verifiable baseline-bound diff receipt; SandboxExperimentService is a route/configuration comparison, not a Git code sandbox; ToolSandbox's sandbox flag is not OS containment; PromotionPrPublisher produces documentary/evidence PRs, not production-code promotion. AutonomousValidationCycleService includes possible auto-start/proposal execution/auto-sync paths, but current runtime state is unknown.

Keep PROVEN_BY_SOURCE separate from OWNER_REPORTED/INFERRED/UNPROVEN. Don't turn generic artifacts, route promotion, persistence, prompt text, or source availability into proof of a bounded coding bridge or learning. Next edge: CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED. No runtime, local preflight, install, spend, credential access, code edits or promotion.

---

## Continuity method delta — distinguish current source interfaces from authorized runtime (2026-10-13; entry 257)

Canonical: [CHAT-ARCH-2026-10-13-257-current-codex-catalog-and-exec-static-paths.md](./CHAT-ARCH-2026-10-13-257-current-codex-catalog-and-exec-static-paths.md). The v0.120 catalog-only negative finding (entry 256) is scoped to that CLI. Upstream v0.162.1 exposes `codex debug models`; `--bundled` is local bundle-only, while the default path may resolve existing auth, request the remote catalog and persist cache. Never summarize this as a guaranteed side-effect-free catalog query.

The current source also contains `exec --ignore-rules`, but that skips only User/Project rule layers; explicit Allow in other applicable policy can still bypass the inner sandbox. Headless approvals are Never by default; `--ignore-user-config` does not disable CODEX_HOME authentication; `--ephemeral` only promises non-persistence of session files. Plan inclusion/model catalog/version minima do not prove this account's allowance or zero extra spend.

Preserve PROVEN_BY_SOURCE vs OWNER_REPORTED vs UNPROVEN. Keep KEEP_BLOCKED, do not run any catalog or exec command, and do not treat documentary capture as runtime learning. First open edge: `CODEX_EXEC_TARGET_VERSION_AUTH_USAGE_AND_CONFINEMENT_UNVERIFIED`.

---

## Continuity method delta — catalog metadata is not a safe catalog-only query (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-256-read-only-model-catalog-path-unavailable.md](./CHAT-ARCH-2026-10-13-256-read-only-model-catalog-path-unavailable.md). In inspected Codex 0.120 source, an internal model manager can refresh remote models, while the reviewed CLI does not establish a standalone supported catalog-only operation. Do not substitute exec, App Server, a model turn, or bundled models.json for an isolated authenticated catalog observation. This bounded negative finding does not prove every compatible route impossible. Preserve PROVEN_BY_SOURCE versus OWNER_REPORTED and keep account eligibility, quota, credit fallback and cost UNPROVEN.

First open edge remains CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED; posture KEEP_BLOCKED.

---

## Continuity method delta — check current model minimums against pinned CLI version (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-255-cli-version-model-entitlement-compatibility.md](./CHAT-ARCH-2026-10-13-255-cli-version-model-entitlement-compatibility.md).

A version-matched source check of Codex 0.120 does not prove the old binary can access current models. Official current Help Center documentation specifies CLI 0.144.0 minimum for GPT-5.6 and 0.153.0 for GPT-6 Astra. Treat that as a compatibility gate, not as permission to update the binary. A compatible older model/plan-included route, if any, remains unproven.

Codex is included on ChatGPT plans, but usage is limited and paid credits may be available after limits; do not equate plan inclusion with unlimited/no-cost use. The actual account state and billing/credit behavior remain unproven. No update/install, login, CLI turn or spend.

First edge: `CODEX_EXEC_VERSION_MODEL_AND_INCLUDED_USAGE_COMPATIBILITY_UNVERIFIED`.

---

## Continuity method delta — distinguish included plan usage from zero cost (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-254-codex-plan-usage-and-zero-extra-spend-gate.md](./CHAT-ARCH-2026-10-13-254-codex-plan-usage-and-zero-extra-spend-gate.md).

Current official Help Center docs show Codex included on ChatGPT plans including Free and Go, subject to limits, but this is not an account-level guarantee. An activity may consume the included plan allowance, and eligible accounts may purchase pay-as-you-go credits after the allowance is exhausted. Keep distinct: no API key, no new OAuth, no incremental cash charge, no plan quota consumed. Do not claim all four from one another.

Combined security gates: the selected CODEX_HOME determines auth lookup and policy provenance; explicit execpolicy Allow may bypass the inner sandbox; local account quota/credit settings remain unproven. Do not launch a turn or add credit spend. First open edge: `CODEX_EXEC_AUTH_HOME_POLICY_AND_USAGE_BUDGET_ROUTE_UNRESOLVED`.

---

## Continuity method delta — auth home and policy-source separation (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-253-codex-home-auth-and-execpolicy-coupling.md](./CHAT-ARCH-2026-10-13-253-codex-home-auth-and-execpolicy-coupling.md).

Don't treat a dedicated `CODEX_HOME` as a free safety upgrade. In Codex 0.120, file-backed auth lives at `CODEX_HOME/auth.json`; keyring auth lookup is keyed by the canonical home path. Execpolicy reads rules from all applicable config-layer folders. Therefore a new home won't automatically reuse the old keyring entry, while the existing home continues to load its rule policy. Matching explicit Allow rules can bypass the inner sandbox.

No verified CLI flag to ignore user execpolicy rules was found in the inspected `ExecCli` and rule-loader source. Keep local auth/rule mode `UNPROVEN`; don't inspect credentials, create a home/symlink, or start login. Cloud analysis may continue. First open edge: `CODEX_EXEC_AUTH_HOME_POLICY_ISOLATION_ROUTE_UNRESOLVED`.

---

## Continuity method delta — inspect execpolicy bypass before accepting an inner sandbox (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-252-execpolicy-allow-can-bypass-sandbox.md](./CHAT-ARCH-2026-10-13-252-execpolicy-allow-can-bypass-sandbox.md).

A permission profile is not enough if the agent can trigger a command that bypasses the inner sandbox. Public `rust-v0.120.0` source shows a matching explicit execpolicy `Allow` can set `bypass_sandbox=true`, and the orchestrator selects `SandboxType::None` for that attempt. The applicable policy set is loaded from rule files in the config-layer folders; do not assume only `CODEX_HOME/rules/default.rules` contributes.

The default operational state stays blocked until either all applicable rule layers are shown incapable of allowing a command to escape confinement, or a separate outer OS boundary is demonstrated to contain the process independently of Codex's choice. Don't infer rule absence, inspect credentials, or test by launching a command.

First open edge: `CODEX_EXEC_V0120_EFFECTIVE_EXEC_POLICY_RULESET_UNVERIFIED`. Cloud source analysis can continue; local effective policy remains unproven.

---

## Continuity method delta — version-matched exec permission-profile route (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-251-exec-v0120-permission-profile-dispatch.md](./CHAT-ARCH-2026-10-13-251-exec-v0120-permission-profile-dispatch.md).

Continue cloud static analysis when local environment facts are pending. Source tagged `rust-v0.120.0` shows `exec` forces `approval_policy=Never`; this cannot be treated as a per-command approval loop. It also shows that `--sandbox`/`--full-auto` forces legacy sandbox-policy interpretation, while a higher-precedence `default_permissions` layer can choose permission-profile interpretation if no sandbox-mode override or selected profile sandbox mode is present.

Thus evaluate a profile-selected route as a source-level candidate, not `--sandbox workspace-write` by reflex. Keep all permissions explicit, omit broad root read, make the disposable candidate the only writable code root, and require child network/integrations to be disabled before effects. Local Windows backend/effective policy, no-extra-spend authentication, real artifacts and existing-consumer evaluation remain independent unknowns.

First open edge: `CODEX_EXEC_V0120_PROFILE_ROUTE_BACKEND_AND_ENVIRONMENT_UNVERIFIED`. This writeback is project memory, not a local runtime event.

---

## Continuity method delta — continue cloud review while local facts remain blocked (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-250-cloud-static-audit-windows-sandbox-home-separation.md](./CHAT-ARCH-2026-10-13-250-cloud-static-audit-windows-sandbox-home-separation.md).

Do not stop all analysis merely because the Owner's A/B/C choice or a local runtime fact is pending. Continue any discriminating source-level review, especially when version-matched public source can reduce uncertainty. Keep local-effective-state gates separate: remote source cannot show which Windows sandbox backend is provisioned, whether a local home is authenticated, or whether usage costs extra.

The Codex 0.120 source supports filesystem permission profiles with `read/write/none`, but Windows backends differ in which restrictions they enforce. The next technical question is whether a sensitive authenticated home can be made unreadable to agent-spawned commands under a backend already available, while the CLI host can still use it. Published IABV code also loads secrets into `os.environ`; a future executor must not inherit that environment wholesale.

C remains the operational default until proof/authorization gates close. First technical edge: `CODEX_EXEC_WINDOWS_HOME_READ_DENIAL_FEASIBILITY_UNVERIFIED`. Cloud writeback is external memory, not a live execution result.

---

## Continuity delta — decision package is not an Owner selection (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-249-owner-decision-package-reviewed-no-selection.md](./CHAT-ARCH-2026-10-13-249-owner-decision-package-reviewed-no-selection.md).

A package that enumerates A/B/C is not an explicit selection of one of those options. Keep the Owner decision pending unless the Owner directly adjudicates it. Until then, no implementation or runtime operation is authorized; use remain-blocked as the safe default. Do not inspect secrets to find a preferred home, copy credentials or infer consent from silence.

First open edge: `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`.

---

## Continuity delta — Codex exec launch design requires Owner decision (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-248-exec-launch-contract-design-adjudication.md](./CHAT-ARCH-2026-10-13-248-exec-launch-contract-design-adjudication.md).

Preserve the distinction between design readiness and authorization to implement. The design must bind the SafeUI authorization, exact child executable/environment, target home/policy, OS-enforced containment, candidate baseline, terminal artifacts, current consumer and owner-only promotion. Existing data-model fields for artifacts do not prove the actual diff producer/consumer route.

Do not hide the design conflict between an explicit/dedicated `CODEX_HOME` and the constraints of no credential copying, no new login/OAuth, existing authentication and no extra spend. If no already-authenticated home fits the approved policy, the correct outcome is to remain blocked.

First open edge: `CODEX_EXEC_LAUNCH_CONTRACT_OWNER_DECISION_PENDING`. No implementation or runtime authorization is implied by writeback.

---

## Current continuity delta — Codex exec integration boundary (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-247-codex-exec-integration-boundary-static-block.md](./CHAT-ARCH-2026-10-13-247-codex-exec-integration-boundary-static-block.md).

Do not ask for an effective home value of a hypothetical CLI child before IABV has a CLI launch contract. Existing App Server `CODEX_HOME` wiring applies only to that path. A value absent from the current shell also does not establish what a future IABV process would inherit. Keep facts, owner reports, inferences and unknowns separate.

Next edge: `CODEX_EXEC_LAUNCH_ENVIRONMENT_CONTRACT_UNDEFINED`. Specify the child environment and security/artifact contract from current source only. Do not copy a different home’s `danger-full-access` / `never` settings, inspect secrets, launch processes or alter the dirty worktree.

---

## Current continuity delta — Codex exec target policy (2026-10-13)

Canonical: [CHAT-ARCH-2026-10-13-246-codex-exec-0120-static-contract-and-target-home.md](./CHAT-ARCH-2026-10-13-246-codex-exec-0120-static-contract-and-target-home.md).

Apply the evidence ladder strictly: the inspected shell's shim/package metadata is owner-reported; the public `rust-v0.120.0` CLI argument declarations are source-proven; equivalence with IABV's child environment and target Codex home is not proven. A persisted report is not local runtime verification or causal learning.

Do not inherit or copy policy from a different Codex home. Never print credentials or session contents. If the effective target path/policy cannot be established statically, stop and request a separately authorized minimum diagnostic. Keep source state immutable and preserve dirty/untracked files.

First open edge: `CODEX_EXEC_TARGET_HOME_AND_EFFECTIVE_POLICY_UNPROVEN`.

---

## 2026-10-13 METHOD UPDATE — DISCRIMINATE EXISTING CODEX EXECUTION INTERFACES BEFORE ADDING AN EXECUTOR

Canonical result: [CHAT-ARCH-2026-10-13-245-windows-codex-execution-route-comparison.md](./CHAT-ARCH-2026-10-13-245-windows-codex-execution-route-comparison.md).

A blocked App Server coding turn does not automatically imply that all local Codex execution paths are unsuitable. Official documentation shows `codex exec --sandbox workspace-write` as an automation pattern; a public issue reports a specific Windows App Server workspace-write turn with no command/file-change items. These are route-selection evidence, not proof of local readiness.

Recompute route from exact installed binary/protocol, non-secret sandbox configuration, allowed tools and output/artifact contract. Do not infer effective enforcement from documentation alone. Prefer a one-time non-mutating metadata inventory before any runtime capability fixture. Preserve the distinction between external issue reports, source proof, live behavior and independent verification.

Next edge: `CODEX_WINDOWS_CODING_TRANSPORT_AND_SANDBOX_COMPATIBILITY_UNRESOLVED`. No run, source edit, tests, auth changes or spend is authorized.

---

## 2026-10-13 METHOD UPDATE — USE DOCUMENTED NATIVE SANDBOX AS A CANDIDATE, NOT AS LOCAL PROOF

Canonical: [CHAT-ARCH-2026-10-13-244-windows-sandbox-route-refinement.md](./CHAT-ARCH-2026-10-13-244-windows-sandbox-route-refinement.md).

The official Codex documentation describes native Windows sandbox implementations and `workspace-write`; commands spawned by the agent inherit the enforced file/network permissions. This narrows the architecture search: assess this existing enforcement substrate before inventing a separate executor. However, documentation about a product capability does not prove that the dynamically resolved local CLI/App Server supports or effectively applies it. Match version, request semantics and local non-secret configuration; preserve `UNPROVEN` when that cannot be established without runtime.

Next edge: `CODEX_NATIVE_WINDOWS_SANDBOX_IN_APP_SERVER_MODE_UNVERIFIED`. Keep stages distinct: documented capability → source path/config support → local effective sandbox evidence → authorized runtime task → candidate artifact → consumer evaluation → independent verification → owner-controlled promotion → later causal reuse. No setup or execution is authorized by this method update.

---

## 2026-10-13 METHOD UPDATE — A TEXT RESPONSE ADAPTER IS NOT A CODING/ARTIFACT BRIDGE

Canonical result: [CHAT-ARCH-2026-10-13-243-codex-bounded-development-mode-blocked.md](./CHAT-ARCH-2026-10-13-243-codex-bounded-development-mode-blocked.md).

Preserve this new negative knowledge: a text response plus task/thread/turn metadata is not evidence of a code-change transport, writable candidate, verified diff or artifact bundle. A Job Object's process-tree management is not evidence of filesystem, credential or network isolation. Requested sandbox parameters and post-event rejection do not establish enforcement before effects.

The source-audit classification is owner-reported, not independently remeasured by this writeback. Keep the evidence ladder intact: source report → attributable patch → synthetic tests → authorized runtime → terminal correlated response/artifacts → existing-consumer evaluation → independent verification → owner-gated promotion → measured causal reuse on a later non-identical task.

Next edge: `CODEX_CANDIDATE_WORKSPACE_EXECUTION_BOUNDARY_DESIGN_UNRESOLVED`. Design only; reuse existing organs and do not add a parallel memory/router/orchestrator. No implementation or runtime is authorized.

---

## 2026-10-13 METHOD UPDATE — DO NOT CONFUSE A TOOL-FREE CONSULTATION WITH A CODING TASK

Canonical: [CHAT-ARCH-2026-10-13-241-codex-development-bridge-route-adjudication.md](./CHAT-ARCH-2026-10-13-241-codex-development-bridge-route-adjudication.md).

An absent global tools-off field in a versioned App Server schema blocks the reviewed *tool-free text-only mode*; it does not automatically block all Codex coding workflows. A coding task intentionally needs tools, so its governing invariant must be effective confinement and authorization of every effect, not natural-language instructions alone. Keep evidence stages distinct: source wiring, synthetic test, runtime dispatch, terminal correlated artifacts, existing-consumer evaluation, independent verification and measurable later causal reuse. GitHub persistence is portable temporal memory, not proof of automatic retrieval or learning.

Next edge: `CODEX_BOUNDED_DEVELOPMENT_EXECUTION_BOUNDARY_UNPROVEN`; see entry 241. No runtime, credential inspection, implementation or spend is authorized.

---

## 2026-10-13 METHOD UPDATE — VERSIONED SCHEMA NEGATIVE FINDING IS BOUNDED

Canonical: [CHAT-ARCH-2026-10-13-240-versioned-0120-tool-control-limit.md](./CHAT-ARCH-2026-10-13-240-versioned-0120-tool-control-limit.md).

Reviewed public `rust-v0.120.0` schemas do not declare a general tool-list/all-tools-off field in `ThreadStartParams` or `TurnStartParams`; `ToolsV2` controls specific capabilities only. This is a bounded negative finding about named typed structures, not proof of every runtime behavior and not proof of the actual local binary version. Preserve that caveat.

Next edge: `CODEX_APP_SERVER_NO_GLOBAL_TOOL_DISABLE_IN_EXPECTED_0120_CONTRACT`. Stop broad upstream searching. Source-review the existing local adapter/config/tool registry to decide whether an actual pre-turn tool restriction exists. If not, do not force the App Server into a tool-free role. Consider an existing text-only transport or a separate isolated coding-task design; no implementation, runtime or spending is authorized here.

---

## 2026-10-13 METHOD UPDATE — EXPECTED VERSION IS NOT EXECUTABLE IDENTITY

Canonical: [CHAT-ARCH-2026-10-13-239-target-protocol-tool-surface-audit.md](./CHAT-ARCH-2026-10-13-239-target-protocol-tool-surface-audit.md).

The source-reported expected user-agent `0.120.0` does not pin the actual executable when resolution remains dynamic through `PATH`. Until existing source/manifests identify the target contract, upstream schema evidence is contextual only. Do not run the CLI merely to discover its version within a read-only tranche.

The primary invariant remains: no real turn unless the contract proves, before `turn/start`, that all unwanted effect-capable tools are absent or sufficiently restricted. Requested sandbox/approval policy and rejection after message receipt cannot substitute for that invariant. Normal dispatch reportedly skips `preflight()`, and the preflight does not make unexpected inventory a fail-closed condition.

Next edge: `CODEX_APP_SERVER_SERVER_ENFORCED_TOOL_SUPPRESSION_UNAVAILABLE_OR_UNPROVEN`. Remain source-only, preserve evidence categories, and keep auth/quota/cost and consumer evaluation separate.

---

## 2026-10-13 METHOD UPDATE — TEXT-ONLY INTENT IS NOT EFFECTIVE TOOL POLICY

Canonical: [CHAT-ARCH-2026-10-13-238-appserver-tool-suppression-unproven.md](./CHAT-ARCH-2026-10-13-238-appserver-tool-suppression-unproven.md).

Keep these evidence stages distinct: prompt intention; requested sandbox/approval parameters; server-accepted settings; tools actually exposed to the model; server-side execution; client handling after a request/event arrives; and downstream consumer evaluation. Evidence for an earlier stage does not establish a later stage.

Owner audit says normal dispatch bypasses adapter `preflight()`, while the current preflight counts MCP inventory without requiring it to be empty. A read-only request plus post-receipt event rejection is insufficient proof that a tool could not act earlier.

Next edge: `CODEX_APP_SERVER_SERVER_ENFORCED_TOOL_SUPPRESSION_UNAVAILABLE_OR_UNPROVEN`. Read-only match the target CLI/protocol contract and prove an effective server-side no-tools mode or retain the block. No runtime, credentials, tests, edits or spending.

---

## 2026-10-13 METHOD UPDATE — IDENTITY DEFECT REPAIR REPORTED PASS; EVIDENCE STAGES STAY SEPARATE

Canonical result: [CHAT-ARCH-2026-10-13-237-codex-task-id-repair-synthetic-pass.md](./CHAT-ARCH-2026-10-13-237-codex-task-id-repair-synthetic-pass.md).

Owner reports `CODEX_TASK_ID_REPAIR_PASS`: the SafeUI-authorized task ID is preserved for both Codex destinations and rejected if absent, malformed or inconsistent before authorization consumption and external dispatch. Focused synthetic tests reportedly ended at 32 passed; this was not independently rerun by this writeback. Treat the result as local-source/test evidence supplied by the Owner, not remote-main verification or runtime proof.

Keep the evidence ladder explicit: source-reported repair → independently reviewed diff/source → synthetic tests → authorized runtime dispatch → terminal correlated response → existing consumer evaluation → measurable causal reuse on a non-identical task. Never infer a later stage from an earlier one. A canonical 32-hex identity format does not itself establish authority; retain operation, destination, approved prompt/digest and scope bindings.

Next edge: `CODEX_APP_SERVER_AUTH_HOME_PREFLIGHT_AND_EFFECTIVE_TOOL_POLICY_UNRESOLVED`. Action: bounded read-only resolution of exact App Server auth/home, preflight coverage and effective pre-effect tool restrictions. No credential contents, runtime/network/UI, further code edit or spend within this routing step. Preserve all unrelated worktree changes.

---

## 2026-10-13 METHOD UPDATE — AUTHORIZED TASK ID MUST FAIL CLOSED BEFORE EFFECT

Canonical result: [CHAT-ARCH-2026-10-13-236-appserver-task-id-correlation-blocker.md](./CHAT-ARCH-2026-10-13-236-appserver-task-id-correlation-blocker.md).

A source audit reported that the SafeUI-authorized task ID is regenerated for both Codex destinations and checked only after the external consultation call may have dispatched. This is an effect-before-identity-acceptance defect, not merely a display/correlation issue.

The next permitted implementation phase requires separate explicit Owner authorization. Keep it narrow: preserve the task ID in construction for both Codex destinations, reject missing/mismatched identity before adapter dispatch, and add synthetic tests asserting no adapter call. Do not combine with App Server runtime/auth changes or tool policy. Check current worktree status first and preserve all unrelated dirty/untracked files. No commit/push unless separately authorized.

Static finding, synthetic verification, runtime dispatch, terminal response and consumer evaluation remain distinct evidence stages.

---

## 2026-10-13 METHOD UPDATE — VERIFY CODEX AUTH MODE BEFORE SELECTING ROUTE

Canonical: [CHAT-ARCH-2026-10-13-235-codex-plan-entitlement-auth-mode.md](./CHAT-ARCH-2026-10-13-235-codex-plan-entitlement-auth-mode.md).

A material constraint is now recorded: native Codex Local/CLI availability and SIWC ChatGPT-plan usage in a third-party app are distinct routes with different eligibility. The App Server adapter's actual mode must be established from source before concluding that it can reuse Free-plan usage or that it requires billable access. No token/credential inspection, new OAuth app, API key, spend, installation or download.

Next source-only slice: exact adapter auth/home selection, unused preflight seam, effective task/tool policy before effects, terminal correlation and existing-consumer evaluation. Static capability is not runtime entitlement or success.

---

## 2026-10-13 METHOD UPDATE — STOP AT UNAVAILABLE LAUNCH PROVENANCE

Canonical: [CHAT-ARCH-2026-10-13-234-desktop-provenance-unavailable-appserver-next.md](./CHAT-ARCH-2026-10-13-234-desktop-provenance-unavailable-appserver-next.md).

The latest permitted Desktop observation ended at `LAUNCH_PROVENANCE_UNAVAILABLE`. This is not proof of a home mismatch. Do not repeat the window enumeration or broaden to unrelated process data. Route next to a bounded source/configuration audit of the known App Server path, focused on its existing preflight, home/auth mechanism, task-specific tool policy and result-consumer path. Static evidence must not be described as live authentication or runtime success.

No processes, network, UI, CDP, tests or source changes are authorized. Preserve all dirty/untracked files. A text-only transport result is not proof of a governed coding loop or causal learning.

---

## 2026-10-13 METHOD UPDATE — PRE-FLIGHT MUST PROVE CAPTURE-HOME PROVENANCE

Canonical result: [CHAT-ARCH-2026-10-13-233-desktop-preflight-launch-provenance.md](./CHAT-ARCH-2026-10-13-233-desktop-preflight-launch-provenance.md).

The Desktop availability check did identify one visible window, but did not prove that the live process uses the directory read by IABV's Codex rollout capture. Do not repeat the window enumeration or infer session linkage from title, executable path or PID.

The next discriminating observation is existing launch provenance for the exact PID and capture home, with a separate Owner authorization. Prefer existing non-sensitive source records. If direct process inspection is explicitly authorized, retrieve only the single allowlisted `CODEX_HOME` value and the minimum launch/parent metadata necessary; never dump environment variables or touch credential-bearing values. If safe allowlisted retrieval is unavailable, stop and report the blocker. No dispatch.

A match proves only configuration alignment; a future same-session response still requires capture and correlation evidence. Preserve actor-report vs runtime evidence distinctions and all dirty/untracked worktree changes.

---

## 2026-10-13 METHOD UPDATE — AFTER CODEX ROUTE COMPARISON

Canonical result: [CHAT-ARCH-2026-10-13-232-codex-bridge-comparison-result.md](./CHAT-ARCH-2026-10-13-232-codex-bridge-comparison-result.md).

The static comparison has been received as `CODEX_BRIDGE_COMPARISON_INCONCLUSIVE`; do not rerun it without new evidence. Keep the Codex-specific development objective. The most discriminating next step is a separately authorized, read-only Desktop availability/correlation preflight, not dispatch. It must establish one eligible window and a defensible link between the observed process/session and the existing rollout source without reading private conversation data or credentials.

If that evidence cannot be established, remain blocked and examine the exact App Server gates: unused preflight seam, auth/home identity, and pre-effect tool-control configuration. Do not start services or broaden the audit absent separate authorization.

Treat the supplied report as actor-reported local evidence. Preserve every tracked/untracked change, including reported modified `.pyc` files. No provider expansion, cost escalation, source mutation or automatic retries. A persisted `ToolResult` remains distinct from consumer evaluation; evaluation remains distinct from causal reuse.

---

## 2026-10-13 METHOD UPDATE — ROUTE TO THE OWNER'S CLARIFIED CODEX OBJECTIVE

Canonical: [CHAT-ARCH-2026-10-13-231-codex-bridge-priority-clarification.md](./CHAT-ARCH-2026-10-13-231-codex-bridge-priority-clarification.md).

When the objective is IABV self-development, first distinguish a generic external-AI consultation from a direct Codex development handoff. The Owner has clarified that the immediate priority is IABV sending development prompts to Codex and receiving/correlating Codex results. Do not continue with ChatGPT Web CDP discovery merely because it was the prior routing choice in record 230; preserve that route as a separate optional capability.

Minimum next action: source-only audit of the existing local candidate `CodexAppServerToolAdapter` versus RQ128's `ExternalAssistantToolAdapter`/ `UIExecutionRunner`/ Codex rollout capture. Read the current state and verify branch/HEAD/status. Do not repeat broad architecture archaeology, expand providers, edit source, start processes, use CDP or inspect credentials. Distinguish static composition, synthetic tests, authenticated invocation, terminal result capture, correlation, consumer evaluation, and later causal reuse.

Official protocol support makes App Server a candidate, not a verified route. A text instruction saying “do not use tools” is not an enforcement boundary; tool policy must be shown to prevent effects before execution. Existing user cost constraints apply: no billable API key or additional spend.

---

## 2026-10-10 METHOD UPDATE — RESPECT PRE-PROCESS EXECUTION DENIAL

Canonical: [CHAT-ARCH-2026-10-10-227-cross-chat-autonomy-resource-pressure-and-continuity.md](CHAT-ARCH-2026-10-10-227-cross-chat-autonomy-resource-pressure-and-continuity.md).

- A `CreateProcess ... Rejected ... blocked by policy` result means the process did not start; do not attribute a deletion or disk-space recovery to it.
- When the reported approval policy is `never` and no supported in-session authorization route exists, do not repeat the same action or switch commands/channels to evade policy. State the exact needed intervention: a permitted user-controlled approval/configuration route, or a normal authorized Windows cleanup surface.
- Separate candidate identification, request, approval, process creation, actual execution and measured outcome.
- Prioritize candidates by net physical reclaimable space and evidence of disposability; a 24.6 MB cache group cannot close a ~5.37 GiB gap. Avoid analysis-only loops, but never invent success or force deletion after rejection.

---
## 2026-10-10 METHOD AMENDMENT — HANDOFF CONTINUITY / STOP ANALYSIS-ONLY LOOPS

Canonical operational/product handoff: [CHAT-ARCH-2026-10-10-227-cross-chat-autonomy-resource-pressure-and-continuity.md](CHAT-ARCH-2026-10-10-227-cross-chat-autonomy-resource-pressure-and-continuity.md).

- Preserve the product target `HUMAN ↔ IABV ↔ capability-bearing AI/tools` and distinguish M0-A (explicit mediated handoff) from M0-B (objective-derived resource selection).
- Do not infer that a static adapter, capture mode, ToolCard or composed call graph proves runtime traversal. Mark the exact first failed edge and what was/was not observed.
- Do not keep issuing analysis-only prompts after sufficient evidence exists for a concrete bounded next action. Prefer: (a) authorized bounded operation with measured result, (b) exact policy/permission blocker, or (c) an actual unresolved Owner decision. Do not bypass a policy refusal by changing commands or channels.
- For cleanup, classify by dependency and preservation requirements, not file extension/name alone. Owner authorized deleting items demonstrated unnecessary to Windows, IABV, Codex/development and authenticated Edge/Chrome/Opera/Firefox; profiles, sessions, credentials, unique work/evidence and protected PR #464 remain protected. Unknown files stay until classified.
- Distinguish logical directory size from physical space reclaimed; use fresh whole-volume measurements. Report unexplained drift rather than attributing it to an action.
- Preserve actor-reported local evidence as actor-reported unless independently verified. Do not infer that a denied deletion ran, that `resource_pressure_critical` cleared, or that a failed UI-channel attempt proves the production route is defective.
- RQ224 is still the canonical technical route; resource-pressure recovery is an immediate operational workstream, not a security-route replacement. RQ226 entry order still applies.

---
## 2026-10-09 METHOD AMENDMENT — RQ226 CONTINUITY / KNOWLEDGE-ACQUISITION AUDIT

Canonical adjudication: [CHAT-ARCH-2026-10-09-226-rq226-continuity-symbiosis-audit-adjudication.md](CHAT-ARCH-2026-10-09-226-rq226-continuity-symbiosis-audit-adjudication.md).

- Use the single canonical entry order in `README.md`: verify remote `main` SHA → README → top of `CURRENT-STATE.md` → objective-relevant `CONTEXT-INDEX.md` retrieval → this protocol → selected evidence records. This protocol must not prescribe a conflicting order.
- Explicitly activate `UAAL-ROOT-001` and relevant lineage for global vision, architecture, universal semantics/generalization, cross-domain composition, learning, memory/continuity or protocol-design objectives; do not load the whole archive for a narrow task.
- For supplied conversations, use the `CHAT / TRANSCRIPT INTAKE CONTRACT` below. Declare actual source extent, inspected coverage, omissions and completeness status; never report full reading/absorption from a partial extract.
- The RQ226 follow-up corrected residual entry-order instructions in Constitution §12, North Star §12, AI Frame continuity hardening and this protocol's North-Star addendum; all now defer to the README order. This closes those identified textual conflicts only, not the possibility of other historical variants or live activation failures.
- Relevant prior experience must change an applicable task constraint, required observation, false-positive control, stop condition or acceptance criterion before prompt construction.
- Persistence, retrieval, activation, decision impact and causal reuse remain separate evidence stages. Documentary harmonization does not prove operational reliability.
- Existing canonical memory organs remain sufficient; no parallel memory or coordinator is justified. The technical route remains the top routing snapshot of `CURRENT-STATE.md`; RQ224 is not superseded by this method amendment.

---
## 2026-10-09 METHOD AMENDMENT — RQ223 CONTRACT RECONCILED; RQ224 TRUST SOURCE NEXT

Canonical: [CHAT-ARCH-2026-10-09-223-rq223-mutation-authority-contract-design.md](CHAT-ARCH-2026-10-09-223-rq223-mutation-authority-contract-design.md).

- RQ219/RQ220 remain accepted as `NO_EXISTING_TRUSTED_AUTHORITY_FOUND_IN_SCOPE`; RQ223 supports `UI_APPROVAL_BRIDGE_NOT_FOUND_IN_REPOSITORY_SCOPE` for the bounded broker/UI paths inspected. Do not claim global absence of authentication or runtime attribution.
- Do not repeat the broad broker/UI search. Reopen source discovery only if a concrete new caller of `approve(request_id, payload)`, direct identity/authority definition, or receipt producer/verifier is identified.
- Keep current-source evidence, actor-reported local worktree provenance, conceptual contract, and unproven trust technology explicitly separate.
- The conceptual authorization binds authenticated principal, operation, canonical resource, exact scope, approved content/delta where relevant, validity and single-use consumption. A UI prompt, Boolean, observation permission, learned pre-approval or audit log is not a substitute for a verifiable receipt consumed by the mutator before the first effect.
- Existing organs may be reused only for demonstrated roles; do not invent a trust root or API to remove an evidence gap. `HumanApprovalBroker` is a transport candidate, not a demonstrated root of trust.
- RQ218 policy direction remains accepted, but identity/authority source, receipt semantics, exact workspace root/protected paths, immutable baseline and isolated clean worktree remain blockers. Preserve the existing dirty/detached worktree.
- **Next route: RQ224**, static design/adjudication of a trustworthy Owner identity/authority source and the receipt producer/verifier. Stop before traversing a general identity/auth subsystem unless separately scoped.
- No implementation, worktree changes, tests/builds/runtime, MCP/process/state operations, install/download or Git mutation beyond authorized documentary writeback. Global readiness remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`; RQ13-111 and RQ21.200 remain separate.

---

## 2026-10-09 METHOD AMENDMENT — RQ219 ADJUDICATED / DO NOT OVERCLAIM AUTHORITY ABSENCE

Canonical adjudication: CHAT-ARCH-2026-10-09-220-rq219-adjudication-no-trusted-mutation-authority-in-scope.md.

- Accept `NO_EXISTING_TRUSTED_AUTHORITY_FOUND_IN_SCOPE` for the exact bounded discovery, not as proof that no authentication exists anywhere in IABV.
- In-scope handlers rely on generic governance inputs; WorldModel `ObservationPermissionGate` describes observation and cannot serve as Owner mutation authorization without a source-proven bridge.
- Broker `approved` is not proof of Owner identity: `ApprovalResult` as reported has no authenticated approver identity/expiry/operation receipt, and `pre_approver` permits automatic resolution.
- The direct UI `prompt_handler` registration and identity context for caller of `approve(request_id, payload)` are unresolved. Next scope must be a separate, bounded Owner decision; start only at those exact paths, stop at broader identity/auth subsystem.
- Even a proven human prompt does not solve per-operation/resource/exact-scope binding and verifiable receipt. Preserve RQ218 target policy.
- No code edit, worktree creation/change, Git mutation, tests/build/runtime, MCP/process/operational state access, DB/secrets/snapshot, install/download. Preserve dirty/detached worktree. Global readiness remains blocked; RQ13-111 and RQ21.200 remain separate.

## 2026-10-09 METHOD AMENDMENT — RQ219 STATIC AUTHORITY DISCOVERY ONLY

Canonical: CHAT-ARCH-2026-10-09-219-authorization-mechanism-static-discovery.md.

- The accepted first-tranche policy is explicit human Owner approval bound to operation, canonical resource and exact scope; all missing/unknown/stale/malformed/denied/exceptional/mismatched states block. No push, explicit Git file allowlist, preserve the existing dirty/detached worktree.
- RQ219 permits read-only inspection only of the existing mutation handlers, governance callback, model and WorldModel gate producer plus direct imports/definitions needed to determine whether a trusted approval source/verifier already exists.
- Do not equate observation permission, tool invocation, session identity alone, a Boolean or a log entry with human Owner approval without direct evidence.
- Stop at broader authority/identity mechanisms and name the exact path/symbol; no broad search, API invention or source edit.
- Exact workspace root/protected paths and immutable baseline remain undecided. No worktree creation/changes, tests/builds, runtime/MCP, process inspection, DB/secrets/snapshot, install/download or Git mutation. Overall readiness remains blocked.

## 2026-10-09 METHOD AMENDMENT — RQ218 OWNER POLICY PARTIAL / DO NOT EDIT YET

Canonical: CHAT-ARCH-2026-10-09-218-owner-policy-decision-first-security-tranche.md.

- Owner adopted the conservative design direction: human Owner approval only; grant bound to operation/resource/exact scope; fail closed for absent, unknown, stale, malformed, denied, exceptional or mismatched state; unknown network blocks network-required actions; explicit Git allowlist, reject unrelated staged changes, no push in tranche one.
- Future tranche-one authorization, if granted, is source-edit-only. Preserve the existing dirty/detached worktree; separate clean worktree only after an exact baseline is chosen.
- Do not infer the allowed root/protected paths, the baseline, or a trusted human-approval producer/verifier. Those remain implementation blockers.
- Next only a bounded read-only investigation of directly relevant existing authority/identity producer/verifier mechanisms may be prepared. Stop at larger auth systems; no recursion or code change.
- No worktree creation/change, edits, Git mutation, tests/builds, runtime/MCP/process, DB/secrets/snapshot, install/download. Overall readiness remains blocked. RQ13-111 and RQ21.200 remain separate.

## 2026-10-09 METHOD AMENDMENT — RQ216 CONTRACT ACCEPTED AS DESIGN ONLY

Canonical: CHAT-ARCH-2026-10-09-217-rq216-contract-adjudication-owner-policy-gate.md.

- Accept the RQ216 static contract proposal within scope; do not treat it as implementation approval.
- Existing observation permission is not mutation approval. The target contract must bind authorization to each operation, canonical resource and exact scope; absent/unknown/stale/malformed/nonmatching permission or verifier failure must deny.
- Filesystem checks must be consistent across implicated mutators. Git must use explicit file selection, reject unrelated staged changes and have no push in the first tranche. Unknown network state blocks network-required routes but is not mutation authorization.
- A trusted mutation-authority producer/verifier remains unresolved; do not repurpose observation permission or invent an API.
- Freeze exact immutable source baseline and isolated worktree before edits. Preserve existing dirty/detached worktree. No edits, worktree creation/change, tests/builds, runtime, MCP/process operations, DB/secrets/snapshot reads, package installation/download, or Git mutation until a separate scope authorization.
- Owner decisions about approver, scope, roots/protected paths, baseline/worktree and phase boundaries must not be inferred. Global readiness remains blocked; RQ13-111 and RQ21.200 remain distinct.

## 2026-10-09 METHOD AMENDMENT — RQ216 DESIGN CONTRACT ONLY

Canonical: CHAT-ARCH-2026-10-09-216-owner-direction-static-contract-first-security-tranche.md.

- Interpret the Owner's "si procede" as authorization to draft a read-only, source-grounded contract proposal; it does not authorize code edits, worktree creation or changes, tests/builds, or runtime.
- First tranche scope only: per-operation/resource/scope mutation authorization with fail-closed behavior; consistent protected-path/workspace checks for the implicated handlers; explicit Git file allowlist and no push by default; network-required route denies unknown network state.
- Keep existing source findings, proposed target semantics and Owner decisions separate. In particular, approver authority, permitted roots/protected paths, per-operation granularity, and future verification scope must not be silently inferred.
- Preserve the current dirty/detached worktree. Any later implementation requires a separate explicit source-edit authorization naming baseline, isolated worktree, allowed files and forbidden effects.
- Global readiness stays TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES; RQ13-111 and RQ21.200 remain distinct.

## 2026-10-09 METHOD AMENDMENT — RQ214 PLAN ACCEPTED, NOT IMPLEMENTED

Canonical: CHAT-ARCH-2026-10-09-215-rq214-adjudication-symbiosis-and-next-owner-gate.md.

- Accept `STATIC_REMEDIATION_PLAN_COMPLETE_WITHIN_SCOPE` as a completed planning deliverable only. Keep global readiness `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.
- The cross-perspective risk graph is useful because authorization, bootstrap effects, write/Git scope, lifecycle/transport and source/session provenance interact. Do not infer that static plan closure proves a runtime boundary.
- Provenance is a stage-zero prerequisite for code work: choose the exact baseline/ref and isolated worktree before editing; preserve the existing dirty/detached worktree.
- Before implementation, Owner must define who may approve which mutation classes/resources/scopes, the fail-closed handling of absent/unknown/stale/nonmatching gates (recommended block), permitted roots/protected paths, file selection and whether Git push is in scope (recommended no push in the first tranche).
- Separate static source checks from runtime verification; any tests/builds, startup, MCP use or operational snapshot require their own scope/permission.
- RQ13-111's universal causal frontier remains separate; RQ21.200 remains independent.

## 2026-10-09 METHOD AMENDMENT — RQ212 COMPLETE WITH UVICORN / RUNTIME ATTRIBUTION UNRESOLVED

Canonical: CHAT-ARCH-2026-10-09-213-rq212-adjudication-launcher-uvicorn-and-source-provenance.md.

- Accept the static launcher/config review as complete within scope and the reported local file hashes as actor-reported provenance; the coordinator did not independently hash the Windows worktree.
- Configuration (default interpreter/transport) is not proof of which interpreter, transport or dependency a live process used.
- Record the reported port-default discrepancy: script 8000 versus service/docs 8765. Do not infer its live effect.
- Uvicorn was not found under the reported default interpreter's site-packages and is not pinned by the inspected manifests; exact version/source and HTTP shutdown semantics remain blocked.
- `server.py` is dirty; current-worktree hash cannot authenticate its baseline blob. Do not substitute remote-main file hashes for local bytes.
- Do not pursue runtime attribution, process inspection, package installation/download, MCP operations, snapshots, probes, tests/builds or mutation under RQ212. Preserve `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`; RQ21.200 remains independent.

## 2026-10-09 METHOD AMENDMENT — RQ212 STATIC ARTIFACTS AND HASHES ONLY

Canonical: CHAT-ARCH-2026-10-09-212-owner-authorization-static-launcher-uvicorn-and-source-hashes.md.

- Owner authorized only inspection of already-existing static artifacts for launcher/interpreter/transport and exact locally present Uvicorn version/source, plus SHA-256/provenance for RQ210-cited IABV files whose hashes were missing.
- Re-confirm the exact dirty/detached worktree before reading; preserve it. Never inspect live processes or infer source-as-loaded from a configured launcher.
- No runtime imports/calls, MCP start/reconnect, process interaction, probes, package manager/install/download, tests/builds, DB/secrets/snapshots, or source/worktree change. Do not retrieve unavailable evidence through execution or network.
- If local artifacts do not establish the version/bytes, mark the exact subtask unavailable/blocked. Hash local bytes, not remote-main replacements; label modified-file status only where direct status/diff evidence exists.
- Do not broaden into a fresh RQ210 audit. RQ21.200 remains separate and global MCP readiness remains blocked.

## 2026-10-09 METHOD AMENDMENT — RQ210 ADJUDICATION / KEEP SOURCE AND RUNTIME DISTINCT

Canonical authorization: CHAT-ARCH-2026-10-09-210-owner-authorization-fastmcp-lifecycle-worldmodel-permission-gates.md.
Canonical adjudication: CHAT-ARCH-2026-10-09-211-rq210-adjudication-fastmcp-lifecycle-and-permission-gates.md.

- Accept the supplied RQ210 report as `STOPPED_AT_OUT_OF_SCOPE_DEPENDENCY` for Branch A and `COMPLETE_WITH_FINDINGS` for Branch B within its bounded source scope.
- The local `mcp 1.27.0` hash identifies only the reported installed SDK copy. Project manifests do not pin that version; the actual launch interpreter/transport and exact Uvicorn shutdown behavior remain unresolved.
- A `permission_gates` field, an observation grant, or a governance callback before mutation is not proof of mandatory human approval. In the reported predicate, missing/empty/non-required/granted/nonmatching gates may not block a mutator. Human approval is conditional, not universally guaranteed by the inspected path.
- The supplied report does not provide SHA-256 for most cited IABV files. Treat those details as actor-reported until exact file identities are supplied; do not claim coordinator rehashed the Windows worktree.
- Preserve `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. Do not start/reconnect MCP, invoke SDK/runtime, inspect processes, read snapshots/DB/secrets, run probes/tests/builds, install packages, or modify the worktree. RQ21.200 stays separate.

## 2026-10-09 METHOD AMENDMENT — RQ207-S SUPPLEMENT COMPLETE; DO NOT CONFUSE SCOPE PASS WITH READINESS

- Accept `RQ207_SUPPLEMENT_COMPLETE_WITHIN_SCOPE` for the bounded static supplement, while retaining the overall readiness classification `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. A completed audit can correctly conclude that the system is not ready.
- Preserve source/runtime distinctions: adapter availability is not task invocation; callback-before-mutation is not a complete authorization guarantee; source cleanup paths are not proof of observed cleanup; a configured transport is not historical process attribution.
- Direct source risks accepted from the actor report: unknown network status can pass the network-required gate; self-update handlers have asymmetric sensitive-path checks and broad default git staging; AppBootstrap shutdown calls an apparently undefined stop method; observer stop methods are omitted from run-finally; deferred-start thread can race cleanup.
- No further source recursion without explicit Human Domain Owner scope. The only proposed next static edges are the exact versioned FastMCP run/container lifecycle contract and the producer/helpers for WorldModelSnapshot.permission_gates. Identify the precise SDK version/path first and follow only direct helpers necessary to determine the contract.
- Do not start/reconnect MCP, invoke tools, inspect processes, run probes, read DB/secrets/snapshot, test, compile or mutate. Runtime inventory and historical PID 16768 attribution are separate evidence questions. RQ21.200 remains independent.

## 2026-10-09 METHOD AMENDMENT — RQ207 ADJUDICATION / DIRECT-SCOPE SUPPLEMENT

- Accept the RQ207 primary classification `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`, but do not automatically treat every stated blocker as an uncloseable dependency: the report omitted at least one registered adapter and lacked current-worktree identity for the lazy site-explorer service.
- A source-level network gate requiring connectivity must fail closed when the network-state object is absent. The reported predicate `requires_network and network is not None and not connected` allows the unknown state to pass; bind this claim to the dirty local `server.py` SHA/source excerpt and do not use remote HEAD as a substitute for the dirty file.
- Inspect lifecycle paths metacognitively: a finalizer that terminates known process handles may race a detached startup thread that creates a later child, and observer services with stop/join methods are not closed merely because their threads are daemon threads.
- For self-update handlers, separate governance-callback ordering from path scope and repository-state scope: a guard before mutation does not by itself establish sensitive-path protection, human consent per call, or safe selection of files to commit.
- Preserve the known dirty detached worktree; keep remote canonical-memory provenance separate from current source provenance, and never infer historical PID 16768's loaded code from present files or tool descriptions.
- Next: Codex provides only a targeted static supplement inside already authorized RQ206/RQ207 direct scope, with line ranges and SHA-256 for all referenced local files. No runtime work. SDK internals or deeper permission-gate producers require a new, exact owner scope.
- No MCP calls/list, process interaction, start/reconnect, scans/health probes, operational snapshot, secrets/DB reads, tests, compilation or mutation. RQ21.200 remains independent.

## 2026-10-09 METHOD AMENDMENT — TRANSITIVE MCP AUDIT / CANONICAL MEMORY VS LOCAL WORKTREE

- Accept RQ206 as `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. Source-level paths connect bootstrap to EnvironmentSelfAwareness, WorldModel, provider health, adapters/perception, persistence/logging and MCP self-update registration, but this is not runtime evidence.
- A local worktree search that fails to find RQ201–RQ206 or current projections does not supersede canonical records verified on GitHub `main`. State local source provenance and canonical memory provenance separately.
- RQ13-109's known negative result remains relevant: normal AppBootstrap was already found not to guarantee avoidance of provider health checks while keeping the ordinary path. RQ206 corroborates but does not authorize those effects.
- Continue only already-authorized immediate edges: adapters bound to the actual inspected ToolRegistry path, per-handler governance of self-update mutation handlers, transport selection and direct shutdown/cleanup. Capture line anchors/hashes. If a further material dependency lies beyond immediate helpers, name the exact path/symbol and stop.
- Distinguish registration of write/patch/commit/push tools from invocation; prove governance branch coverage statically without calling tools.
- Keep separate: source path vs loaded code; local worktree vs canonical main; source-wired effects vs observed runtime; environment→capability/selection causal learning vs mere persistence; MCP authorization vs RQ21.200.
- No launch/reconnect, MCP calls, process interaction, refresh/health probes, operational snapshot, secret/database reads, tests, compilation or mutation. Future start and any snapshot disclosure remain independently permission-gated.

## 2026-10-09 METHOD AMENDMENT — BOUNDED TRANSITIVE AUDIT + SYMBIOSIS METACOGNITION

- Owner authorized the next read-only audit to include only already-named direct effectful dependencies and immediate helpers plus reconciliation against named canonical memory/symbiosis records. This is not blanket repository-wide recursive permission.
- Preserve the exact dirty/detached worktree; record HEAD/status/file identity. Follow known import/call-site edges. If a further nested dependency has material effects and is outside scope, label it `UNRESOLVED`, name exact path/symbol and stop for a scope decision.
- Build both the local call/effect graph and cross-cutting symbiosis matrix: provenance, startup scans, persistence, network/loopback, secrets, host observation, thread/subprocess behavior, logs/traces, transport/session binding, cache/state contamination, lifecycle/rollback, evidence quality, and authorization order.
- Use prior negative knowledge from RQ201–205 and RQ13-108/109/111; do not conflate historical source attribution with a prospective run. Do not merge the independent RQ21.200 DLL consumer frontier into this MCP task.
- A metacognitive hypothesis must be anchored to source or labeled as a hypothesis. Avoid speculative issue inflation. Distinguish DEMONSTRATED, CONDITIONAL and UNRESOLVED.
- No MCP call/list, process interaction, start/reconnect, refresh, provider health check, UI/snapshot observation, secret/database read, testing/compilation, or mutation. Planning analysis grants no launch authorization.
- Future startup/reconnect and operational snapshot disclosure remain separate, fresh permission gates.

## 2026-10-09 METHOD AMENDMENT — STARTUP PLAN BLOCKED; TRANSITIVE AUDIT NEEDS NEW SCOPE

- Accept `STATIC_PLAN_BLOCKED_BY_UNRESOLVED_TRANSITIVE_EFFECTS` when inspected startup code reveals possible observation/network/persistence but effectful dependencies remain unaudited.
- Do not infer harmless startup from `IABV_MCP_SUBPROCESS=1` or `IABV_DEFER_TOOL_PROBE=1`; identify exactly which branches those flags guard and which refresh/worker/tool-card paths remain.
- Treat a dirty detached worktree as an identified source object, not as equivalent to remote main. Preserve its state.
- RQ204 authorized a six-file static analysis only. A deeper dependency audit requires a fresh owner scope decision. If authorized, follow import/call-site evidence only to the named effectful implementations and immediate helpers; if further recursive exploration is necessary, stop and ask for another scope approval.
- Never launch/reconnect to validate startup behavior while transitive effects are unresolved. A new process can provide prospective attribution, not historic PID attribution.
- Keep future `world_model_snapshot(refresh=False, full=False)` disclosure separately permission-gated due to operational-state exposure.

## 2026-10-09 METHOD AMENDMENT — READ-ONLY STARTUP IMPACT PLAN AUTHORIZED; NO LAUNCH

- Human Domain Owner approved only a bounded read-only static startup-impact/isolation plan; this is not permission to start, stop, restart, reconnect, or invoke MCP.
- Limit Codex to the known `server.py`, `bootstrap.py`, `world_model_service.py`, `docs/mcp-bridge.md`, and RQ13-108/109 records. Preserve all dirty/detached worktrees and report exact revision/status/hashes.
- Classify each direct/transitive effect as demonstrated, conditional, or unresolved. If a transitive implementation lies outside the approved source set, mark it unresolved instead of expanding search scope.
- Analyze construction, EnvironmentSelfAwareness/WorldModel scans, persistence, conditional provider checks, network/IPC, observation, transport/client association, isolation and abort conditions. Proposals only; no experiments, tests, compilation, process interaction or runtime calls.
- A prospective controlled process can establish prospective provenance only; it does not prove what historical PID 16768 loaded.
- Any eventual launch/reconnect requires fresh explicit authorization after coordinator review. Any eventual `world_model_snapshot(refresh=False, full=False)` disclosure requires its own separate explicit permission for operational-state exposure.

## 2026-10-09 METHOD AMENDMENT — NO PASSIVE PROOF OF MCP CODE-AS-LOADED

- Accept `NO_PASSIVE_PROOF_IDENTIFIED` when already-identified passive evidence cannot authenticate the exact Python module/code loaded by the live MCP process.
- Keep configured path, process parentage, effective CWD/environment, module origin, exact loaded bytes, client effective exposure, and permission to disclose operational state as separate propositions.
- A tool description matching a local source diff, the current file's hash, or a configured `PYTHONPATH` is corroboration, not an attestation of the full live module.
- Prefer a prospective, controlled attribution route over intrusive retroactive process inspection unless the Human Domain Owner has a specific need for historic-PID attribution. A new process cannot prove what an older PID loaded.
- Before any new server start/reconnect, inventory AppBootstrap and transitive EnvironmentSelfAwareness/WorldModel scans, local persistence, provider health checks, client reconnection, isolation and rollback. Source-level planning is not startup permission.
- Never attach, dump, suspend, or inject into the existing process merely to clear a provenance gate without a separate, method-specific authorization.
- Any `world_model_snapshot(refresh=False, full=False)` call requires its own precise permission because its reviewed entrypoint lacks an explicit observation-permission gate and its response may disclose windows, focus, network, tools and other operational state. Tool exposure does not grant that permission.

## 2026-10-09 METHOD AMENDMENT — EFFECTIVE MCP EXPOSURE DOES NOT CLOSE SOURCE IDENTITY

- Record the effective tool catalog of the intended Codex session separately from config-on-disk. A visible tool catalog can establish exposure for that session without proving exact server code loaded.
- Treat matching tool-description text and a modified working-tree source as corroborating evidence only, not as proof of the complete Python module/bytecode loaded into a live process.
- Keep process parentage, configured worktree, process CWD/environment, module origin, exact loaded bytes, effective client exposure, and observation permission as distinct predicates.
- If exact source-as-loaded cannot be proven from already-existing passive evidence, do not invoke the tool to test itself and do not restart/reconnect by default. Ask Codex for a bounded feasibility and transitive-side-effect inventory of minimum attribution interventions; do not perform those interventions before a separate owner authorization.
- A visible `world_model_snapshot(refresh=False, full=False)` tool is not permission to disclose windows/focus/network/tool state. Its reviewed entrypoint lacks an explicit observation-permission gate; a later snapshot call requires its own precise, explicit owner permission.


## 2026-10-09 METHOD AMENDMENT — IABV MCP FIRST-USE ATTRIBUTION GATE

- Distinguish four separate predicates: MCP server configured, OS process exists, exact source/module loaded, and tool is exposed in the intended client. Observation permission is a fifth independent predicate.
- Do not infer the exact loaded source or client-session mapping from a configuration entry, process command line, or another client’s tool list. Preserve dirty/detached worktrees; never reset or merge them as a shortcut.
- world_model_snapshot(refresh=False, full=False) reads the current in-memory WorldModel snapshot in its source branch, without itself requesting a refresh. It still discloses operational details and its entrypoint has no explicit observation-permission gate; tool presence is not permission.
- Normal AppBootstrap can reach EnvironmentSelfAwareness/WorldModel scans, local persistence and conditional provider health checks. IABV_MCP_SUBPROCESS=1 and deferred tool-probe settings are not evidence that all those effects are suppressed.
- If the intended client lacks IABV tools and a reconnect/startup would be required, do not start/reconnect. First enumerate exact transitive effects, then request fresh bounded human authorization.
- The first useful MCP probe must be explicitly narrow: only one authorized world_model_snapshot(refresh=False, full=False), after exact server/client attribution and observation-permission decision. No refresh/full scan, orchestrator_preview, handle_request, provider call or other tool.
- The canonical GitHub frame remains the external coordination surface until runtime transfer of state/experience into the target AI session is actually verified.

## 2026-10-08 METHOD AMENDMENT — RQ21.200 CONSUMER DESIGN / OPEN SECURITY CONTRACTS

- A same-process design using the PowerShell call operator for v5 and performing LoadLibraryExW in that exact process is the correct direction for the detector-to-loader causal binding. The outer launcher observes/collects results only and never performs the protected load.
- process_id equality is necessary consistency evidence, not a substitute for actual same-process execution and direct capture of this invocation's output.
- v5 inspects the process primary token, not an impersonation token on the executing thread. Keep thread effective security context as a separate gate. Conservative default: require no thread impersonation; stop if a thread token is present or the state cannot be determined; do not silently change identity with RevertToSelf and proceed. Owner must ratify this contract.
- A path hash and Authenticode check immediately before LoadLibraryExW do not atomically bind the verified bytes to the mapped image. Explicitly ask the owner whether the frozen operation accepts this residual TOCTOU risk or requires a stronger guarantee; do not claim the race is solved.
- Freeze JSON field names/types against the actual reviewed v5 output and specify capture/acceptance rules for PowerShell success, error, information, warning, verbose, debug and progress streams. Reject missing/multiple/malformed/stale/duplicate-key/unexpected/contradictory output and do not use a prior report as authorization.
- Keep consumer design, implementation, static review, saved-artifact identity, compilation/runtime, target readiness and owner authorization separate. Design acceptance grants no permission to implement or execute.

## 2026-10-08 METHOD AMENDMENT — RQ21.199 CONSUMER ABSENCE / DESIGN-FIRST GATE

- If the operator says CONSUMER_NOT_IMPLEMENTED, and Codex correctly returns CONSUMER_SOURCE_UNAVAILABLE because no source object exists, stop the source-audit task. Do not repeat it and do not mark it as an audit pass/fail.
- Record the implementation gap for the identified scope; do not infer that no possible ad hoc program exists anywhere unless exhaustive provenance supports that broader claim.
- Switch to a separate bounded consumer contract/design task before implementation. The previous read-only audit prompt is no longer appropriate when no consumer source exists.
- Bind the detector measurement to the OS process that would perform the protected action. v5's process_id describes the process whose primary token it queried; a different parent's token cannot be inferred from a detector child result. Prefer same fresh one-shot process for detector invocation and the single authorized load, or independently verify the actual loader process's token in addition to the detector gate.
- Keep source review, artifact identity, compilation/runtime, consumer enforcement, current target readiness and owner authorization distinct. Contract/design output does not authorize implementation or execution.

## 2026-10-08 METHOD AMENDMENT — NEW-CHAT RECONCILIATION RQ21.198

- Re-read the latest default-branch CURRENT-STATE, latest episode, operating protocol, context index, symbiosis map, unresolved knowledge, archive registry and README before routing.
- Verify the latest observed remote commit and compare it to both the recent checkpoint and pinned executable baseline; never conflate baseline with current main. State exactly what the comparison returned.
- Separate coordinator-observed Git content, actor-reported Windows observations, reviewer conclusions about inline source, and items that remain unproven. Do not promote repeated transcript claims into new evidence.
- Preserve RQ21.197 as the latest technical adjudication unless new source-bound evidence changes the decision. A continuity checkpoint does not itself create a new technical result.
- For CONSUMER_SOURCE_UNAVAILABLE, do not perform repeated broad searches, enumerate arbitrary temp paths, infer that no consumer exists anywhere, or construct a replacement. Obtain exact owner/operator provenance (path or repository URL+commit/ref and expected call path) first; only then route a read-only audit to Codex.
- Keep historic RQ21.182 authorization conditional/unconsumed. No compile/run, token query, DLL/export operation or candidate launch until separately adjudicated readiness and scope gates are satisfied.

## 2026-10-08 METHOD AMENDMENT — RQ21.197 CONSUMER/DETECTOR SEPARATION

Canonical: CHAT-ARCH-2026-10-08-197-rq21-p1-consumer-source-unavailable.md.

- A detector that measures a condition and emits JSON is not the runner/consumer that enforces that condition before a protected action.
- Treat the reported known loader script as a separate path unless source evidence shows it launches v5, parses its output and requires both `outcome == MEDIUM_CONFIRMED` and `cleanup_clean == true`.
- `CONSUMER_SOURCE_UNAVAILABLE` means linkage is not proven from inspected evidence; it does not prove no consumer exists anywhere.
- Stop repeating generic searches. Obtain the authoritative consumer's exact path/repository URL/commit from owner/operator provenance or known project artifacts, then audit only that identified source read-only.
- Do not invent a replacement runner, run code, query tokens or operate the DLL to compensate for missing source. Static source, artifact identity, consumer enforcement, target readiness and Owner authorization remain separate gates.


## 2026-10-08 METHOD AMENDMENT — RQ21.196 V5 ARTIFACT IDENTITY MATCH

Canonical: CHAT-ARCH-2026-10-08-196-rq21-p1-v5-artifact-identity-verification.md.

- Accept Codex's exact-path ReadAllBytes/size/SHA report as actor-observed artifact-identity evidence; preserve the boundary that the coordinator has not accessed the Windows bytes directly.
- Keep hash verification and normalized-text comparison to reviewed source as separately reported checks. Record newline normalization.
- Artifact identity does not prove Add-Type compilation, runtime behavior, current target readiness or the real consumer gate.
- Next inspect only the actual runner/consumer entrypoint and output handoff in read-only mode. Trace fresh child identity, output freshness/strict parsing, outcome AND cleanup conditions, failure_stage semantics and each frozen target/DLL/flags/scope gate.
- If the actual consumer or handoff cannot be identified, stop with CONSUMER_SOURCE_UNAVAILABLE; do not infer enforcement, build a replacement runner or search arbitrary temporary paths.
- No compile/run/token query/DLL/export/candidate launch. The Owner authorization remains a separate conditional gate.


## 2026-10-08 METHOD AMENDMENT — RQ21.195 V5 INDEPENDENT STATIC CHALLENGE

Canonical: CHAT-ARCH-2026-10-08-195-rq21-p1-v5-independent-static-challenge-adjudication.md.

- A reviewer STATIC_REVIEW_PASS applies only to the exact inline source received; it does not establish saved-byte identity, compilation, runtime correctness or consumer enforcement.
- Route artifact identity verification and runner/consumer inspection as distinct, read-only edges. Verify only the specified path; absence or mismatch is a stop, not permission to search alternative temp files.
- When the same Win32 error can occur at different stages, preserve and interpret failure_stage with outcome and cleanup status. A numeric error/detail string is not retry authorization.
- A 64-bit structure guard does not independently establish x64 process architecture; keep the frozen host/architecture/build gate in runner evidence obligations.
- Retain the F7 84-byte bound as a fail-closed policy while legitimate OS padding above the ceiling remains NOT_PROVEN. Do not widen it speculatively.
- Do not revise a candidate/hash solely for a self-consistent stale internal type name without a concrete collision or provenance consequence.
- Static review, artifact identity, compilation, runtime, target readiness and actual consumer enforcement remain separate predicates. No source pass activates the protected operation.


## 2026-10-08 METHOD AMENDMENT — RQ21.194 V5 SOURCE RECONCILIATION

Canonical: CHAT-ARCH-2026-10-08-194-rq21-p1-v5-static-source-reconciliation.md.

- Reconcile the complete source and requested diff, then route a fresh independent challenge for each material native-interop revision.
- A reported two-method SHA agreement remains actor-reported until the coordinator independently reads the exact saved bytes. Preserve source / artifact identity / compilation / runtime / consumer enforcement as separate evidence states.
- F8 repair: preserve the Win32 error actually observed on both out-of-bound requiredLength branches while keeping the TokenInformationLength stage and specific branch detail; 122 does not authorize retry.
- F7: a source comment may state the bound's derivation, but not turn an assumed layout ceiling into an undocumented API guarantee.
- A stale internal type version label can be recorded as a traceability concern; do not expand a deliberately narrow repair unless a concrete collision/provenance consequence is shown.
- Use non-nested source delimiters for independent audits and include the complete exact source in the reviewer message.
- No source pass or writeback activates the protected operation; consumer, target readiness and Owner authorization remain distinct gates.

## 2026-10-08 METHOD AMENDMENT — RQ21.193 SOURCE-HANDOFF INTEGRITY AND ERROR PRESERVATION

Canonical: CHAT-ARCH-2026-10-08-193-rq21-p1-v4-independent-challenge-adjudication.md.

- The exact source audited by an independent reviewer must be reconciled with the intended source. Fence lines reported in reviewer input are not proof those lines exist in the saved artifact. Check only the exact reported path and verify byte size/hash before deriving a candidate.
- Avoid nested triple-backtick delimiters when source is embedded in a formatted writing block. Use a distinct outer fence length or an actually accessible immutable attachment.
- Preserve any Win32 error actually observed even when later length validation rejects the result. Keep error, validation stage and branch detail separate; error 122 paired with TokenInformationLength is not authorization to retry.
- An unresolved native-handle acquisition is not clean evidence. Never close an unconfirmed handle merely to force cleanup success.
- Keep Add-Type/type collision, process/PID/freshness provenance, compilation, saved bytes, runtime and consumer enforcement as separate states.
- Material source revisions receive a fresh source-bound independent challenge. No static result authorizes the protected operation.
 
## 2026-10-08 METHOD AMENDMENT — RQ21.192 V4 SOURCE / LENGTH-ERROR RECONCILIATION

For a native interop candidate after targeted repair:
- Reconcile the exact complete source before routing a fresh independent challenge; do not infer saved-byte identity or runtime correctness from the supplied hash report.
- Acquisition states must distinguish NOT_ATTEMPTED, ATTEMPT_IN_PROGRESS, confirmed success/failure and unresolved. Unresolved ownership is not clean evidence, and only a confirmed-acquired non-null handle may be closed.
- Bound native output length before allocation using the frozen architecture, native structure layout, maximum variable field and any required padding; challenge the derivation of every hard cap.
- Preserve the actual observed Win32 error even when a secondary validation rejects the returned required length. Keep the failure stage/detail and raw error semantically distinct.
- Fresh-process execution, host/runtime identity, script provenance and output freshness must be runner-enforced and tied to the same child invocation. A declared output predicate alone is not proof of enforcement.
- After material changes to gate-relevant source, require another source-bound independent challenge before artifact/consumer/readiness gates.
- Static preparation and review do not consume or expand the frozen Owner authorization.

## 2026-10-08 METHOD AMENDMENT — RQ21.191 REVIEW-TO-REPAIR RECONCILIATION

Canonical record: CHAT-ARCH-2026-10-08-191-rq21-p1-v3-independent-challenge-adjudication.md.

For independent static review of a native interop candidate:
- Preserve the reviewer's classification as scoped to the complete source actually reviewed. Do not convert a static pass into byte, compiler, runtime or consumer evidence.
- If acquisition begins but does not return a determinate status, represent ATTEMPT_IN_PROGRESS / unresolved acquisition distinctly. Do not report cleanup_clean=true merely because successful acquisition was not observed. Close only a confirmed-acquired non-null handle; unresolved ownership must fail or remain unknown.
- Bound native output-length allocation before allocating. The bound must derive from the frozen architecture, structure size, maximum variable field size, and any required layout/padding. Reject anomalous or inconsistent lengths before allocation; do not use a large allocation as an experiment.
- Keep environment/type collision constraints separate from detector correctness. A fresh one-shot process and a fail-closed missing-output gate satisfy the v2/v3 Add-Type collision concern only if the actual runner enforces them.
- Process identity, build/UBR/architecture, timestamps, script hash, runtime identity and raw-output provenance may be runner-owned, but must be tied to the same child process and invocation.
- A written consumer predicate is not evidence of enforcement. Inspect the actual runner before relying on it.
- Optional detail-string improvements should not expand scope when outcome/stage/error fields already fail closed.
- No static-review result or source repair authorizes the protected operation. Preserve the frozen Owner scope and separately adjudicate artifact bytes, consumer wiring and all target preconditions.

## 2026-10-08 METHOD AMENDMENT — CANDIDATE SOURCE, CLEANUP AND CONSUMER ARE SEPARATE GATES

For a native diagnostic candidate, preserve these separate states:
`source reviewed ≠ saved bytes verified ≠ compiled ≠ executed ≠ observed ≠ consumed by an enforcing runner`.

A candidate's stated hash is actor-reported until the actual saved bytes can be independently read and hashed. Do not claim compile/runtime correctness from source review.

A consumer gate that requires a verified measurement and clean resource cleanup should check both independently (for RQ21 v3: `outcome == MEDIUM_CONFIRMED && cleanup_clean == true`). But an authored predicate is only a contract until the actual runner wiring is inspected. All other target-bound readiness gates remain separate.

If token acquisition fails or throws before status assignment, do not infer successful or clean acquisition. Preserve unknown/attempted distinctions; only close a confirmed-acquired handle, and do not classify unresolved acquisition as fully clean evidence. A failure outcome must still fail the consumer gate.

---

## 2026-10-08 METHOD AMENDMENT — RECONCILE INDEPENDENT NATIVE-INTEROP REVIEW

A `STATIC_REVIEW_PASS_WITH_REPAIRS` applies only to the exact source text reviewed. Keep `inline source reviewed`, `saved bytes/hash independently verified`, `compiled`, and `executed` as separate evidence states. A failed source handoff is a stop, not a code finding; when source is already in the coordinator context, route it inline rather than asking the user to repeat it.

For a detector whose native query is structurally plausible but whose review identifies robustness/evidence-clarity items, adopt only minimum repairs needed by the experiment contract. Preserve the primary measurement separately from cleanup status; the consumer must check both. Distinguish an actual Win32 error from "no Win32 error applicable", and distinguish requested access/source metadata from a successfully acquired handle.

Before a protected operation, state the consumer's hard readiness predicate explicitly. Any query failure, invalid/incomplete result or cleanup state forbidden by the contract must stop before the operation. An unexecuted candidate or successful static review supplies no runtime result.

RQ21 P1's previously authorized single loader call remains unconsumed because previous runs stopped before `LoadLibraryExW`; this authorizes no current execution. Use the existing scope only after corrected source, consumer gate, provenance and target-bound readiness are reconciled; never infer permission for additional calls or a broader operation.

---

## 2026-10-08 METHOD AMENDMENT — BIND AUDIT SOURCE INTO THE REVIEWER MESSAGE

For independent code/source audits, include the complete source in the same reviewer prompt or attach an artifact the reviewer can actually access. Do not assume prior chat context transfers to another actor, and do not route by a path on an actor-specific local filesystem. A `SOURCE_UNAVAILABLE_OR_INCOMPLETE` result is a correct stop but supplies no technical finding about code correctness.

If the complete source is already present upstream in the coordinator conversation, don't ask the user to paste it again. Reissue the bounded audit with source inline. Keep `source reviewed`, `saved file bytes verified`, `reported hash`, `compiled`, and `executed` epistemically separate.

---

## 2026-10-08 METHOD AMENDMENT — STATIC CHALLENGE GATE FOR NATIVE INTEROP CANDIDATES

For native interop candidate scripts, distinguish:
`source supplied → static plausibility → artifact bytes/hash verified → independent static challenge → compilation → runtime observation`.
None implies the next.

After repairing a definite source-level gap, require an independent adversarial review when ABI layout, unmanaged pointer/buffer boundaries, error semantics or cleanup behavior could invalidate a safety/readiness gate. The challenge must operate on the complete source and classify definite defects separately from robustness concerns. Unless exact bytes are actually read back, a hash/path supplied by its creator remains actor-reported.

Keep the protected operation and its authorization boundary separate from detector design. Preparation, static review or even a compile result does not authorize a load/export/candidate experiment.

---

## 2026-10-08 METHOD AMENDMENT — NATIVE DIAGNOSTIC CLEANUP IS EVIDENCE

For native interop diagnostic candidates, preserving the primary API result is not enough if cleanup can fail. Record success/failure of resource-release calls (including `CloseHandle`) and capture relevant error state immediately, in a separate cleanup field so cleanup reporting does not overwrite the primary measurement result. Ensure result reporting covers both normal and early-return paths.

Static API plausibility, a source hash, or successful artifact creation does not establish compilation or runtime behavior. Keep candidate design separate from its execution contract and do not treat preparation as authorization for the protected operation.

---

## 2026-10-08 METHOD AMENDMENT — USE TOKENINTEGRITYLEVEL FOR IN-PROCESS INTEGRITY GATES

Do not derive a Windows integrity level solely by scanning `WindowsIdentity.Groups` for an `S-1-16-*` SID. A missing match there must not be mistaken for proof of a non-MEDIUM token or for a completed token observation.

For an execution-local integrity gate, inspect a direct `GetTokenInformation(TokenIntegrityLevel)` query against the intended process token and parse its `TOKEN_MANDATORY_LABEL.Label.Sid` only after validating API returns, buffer lengths and SID validity. Preserve separate outcomes for a confirmed nonmatching integrity level and an unavailable/invalid query; failures remain fail-closed. Capture Win32 errors at the call boundary and account for native handle/buffer lifetime.

A static diagnosis of a flawed detector explains a possible UNKNOWN path but cannot retroactively establish the previous process's true token SID. No corrected diagnostic is executed, and no protected operation is authorized, until artifact provenance, readiness and the explicit authorization boundary are reconciled.

---

## 2026-10-08 METHOD AMENDMENT — FAIL-CLOSED IN-PROCESS TOKEN READINESS (`UNKNOWN`)

When an experiment requires a security-token property from the executing child process, an observation from another PowerShell/session does not satisfy that gate. If its detector returns `UNKNOWN`, preserve a pre-operation stop; do not infer either that the target property is false or that the underlying operation failed.

Next, inspect the exact detector implementation non-mutatingly and trace its API return/error handling, parsing and UNKNOWN branches. Verify the exact artifact bytes before attributing a cause. Do not execute the experiment, bypass the guard, or retry the protected operation until the detector cause, contract compatibility and authorization boundary are reconciled.

For RQ21 P1, this leaves the `LoadLibraryExW` call and both symbol resolutions unobserved. A static script review may diagnose the detector; it does not prove the process token and does not itself authorize a loader attempt.

---

## 2026-10-08 METHOD AMENDMENT — CANONICAL CONTRACT MISSING LOCALLY BUT PRESENT REMOTELY

If an actor stops because a required frozen document is absent from its local worktree, separately verify the authoritative remote path before treating the contract itself as unavailable. Prefer a read-only remote GitHub read; if a temporary copy is needed, place it outside the repository and validate the Git blob SHA. Do not ask the user to copy files manually or mutate the worktree/Git refs unless the next edge explicitly requires it.

Preserve `stop reported` as `no execution occurred`; it is not a test failure. Once the remote contract is read and verified, the same actor may resume an already-authorized action if all remaining target-bound readiness gates are rechecked. Remote contract availability does not waive those gates.

---

## 2026-10-08 METHOD AMENDMENT — OWNER-AUTHORIZED LOAD-ONLY PROBE CONTRACT (RQ21 P1)

A Human Domain Owner may authorize a bounded dynamic DLL-load probe after P0 static exports are verified. Before execution, freeze exact target/file identity, medium-integrity preconditions, one allowed `LoadLibraryExW` call with restricted `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32` flags, two `GetProcAddress` resolutions, exact result classes, evidence capture and stop conditions.

DLL load can execute module/dependency initialization. Use a fresh short-lived non-elevated process; do not explicitly unload, invoke exports, start a candidate, widen search paths, elevate or retry elsewhere. `LOAD_AND_BOTH_SYMBOLS_RESOLVED` proves only load/resolution, not function behavior or containment. A successful P1 does not authorize a subsequent experiment or implementation without a newly calculated edge and required authorization/readiness.

---

## 2026-10-08 METHOD AMENDMENT — P0 EXPORTS CLOSED; DYNAMIC LOAD IS A NEW GATE

When a distinct, provenance-described PE reader reports both exact export names on the matching target, close the static file/export-presence property without repeating host/token/hash/signature checks. Record parser identity/version/hash and the raw report path/digest; distinguish an external-actor-reported artifact hash from a digest independently recomputed by the coordinator.

Static exports do not prove DLL loadability, API behavior, containment or the seven-guarantee predicate. A `LoadLibraryExW` / `GetProcAddress` check is a separate dynamic experiment because module initialization may execute. Require a frozen experiment contract, loader side-effect assessment, fresh short-lived non-elevated diagnostic process, raw result/error capture, readiness and explicit Human Domain Owner authorization. A load-only probe must not invoke exports or run a candidate.

---

## 2026-10-08 METHOD AMENDMENT — ROUTE MISSING HOST INSPECTION TOOLS BY CAPABILITY, NOT MANUAL REPETITION

When the user has already produced local environment/token/file-identity output, do not ask them to repeat those checks. Identify the unresolved capability (here, independent static PE export inspection) and consider a tool-capable actor such as Codex. Before task execution, require that actor to prove its own execution channel is bound to the exact target host/build and required non-elevated integrity. Tool availability ≠ target access. A mismatch means STOP, never silently use another host. Use only existing installed static readers, capture tool and output provenance, and do not install tools or load the target DLL to close a static-inspection gap. Actor selection must not override the RQ21.58 scope gates.

---

## 2026-10-08 METHOD AMENDMENT — NULL-SAFE INTEGRITY SID COLLECTION

Do not assume `WindowsIdentity.Groups` will expose the mandatory integrity SID in a PowerShell collection. If a required SID lookup returns null, do not index a map with it or infer elevation. Use a null-safe built-in token-group query (e.g. `whoami.exe /groups /fo csv /nh`), require exactly one recognized integrity SID, and treat absent/ambiguous output as UNKNOWN. Do not elevate merely to collect a missing value.

When a diagnostic aborts before later commands, mark those commands NOT RUN; do not treat their absence as negative evidence. For the current RQ21 P0 rerun, the abort occurred before DLL hash/signature recheck or independent export parsing, so P0 remains provisional.

---

## 2026-10-08 METHOD AMENDMENT — P0 OUTPUT MUST BE INDEPENDENTLY CORROBORATED (RQ21.58)

A user-pasted static probe is an observation report, not automatically a closed evidence package. Keep `reported output`, `independently reproduced result`, and `canonical verification` distinct. When a hand-authored PE parser is the subject of the claim, corroborate its export result with a separate already-installed offline PE tool; record tool version/hash/signature, process integrity/elevation level, native path/architecture, target identity, raw output and output-artifact SHA-256. Do not install tools or elevate merely to fill missing fields; record UNKNOWN and stop if access would require elevation. A valid signature and file hash identify observations; neither alone proves the entire candidate substrate or seven-guarantee contract.

For the current local P0 report, both export names are reported present but independent corroboration, parser provenance, token integrity and a hashed report artifact remain open. DLL loading, API invocation, candidate execution and implementation are not authorized by static symbol presence.

---

## 2026-10-08 METHOD AMENDMENT — RQ21.58 EXPERIMENTAL API PROBE READINESS

Keep `DLL presence`, `export presence`, `API loadability`, `API operational behavior`, `containment`, `complete E observation`, and `seven-guarantee PASS` as separate evidence claims.

Before P0, bind a known-good non-elevated read-only execution channel to the exact target and record native OS path/architecture plus collection-process bitness. Preserve raw output, timestamps, target provenance, tool identity, file hash and signature status. A hash identifies a file; it does not establish trust by itself. If a fact needs elevation, mark UNKNOWN and stop.

A WFP filter condition does not establish complete event coverage. An experimental API's generic-sounding name does not override its documented parameter restrictions. P0 is static file/export inspection only and does not authorize loading the DLL, invoking the API, executing a candidate, or implementation.

Source: `CHAT-ARCH-2026-10-08-177-rq21-58-focused-windows-substrate-audit-adjudication.md`.

---

## 2026-10-08 METHOD AMENDMENT — STATIC API AVAILABILITY IS NOT REALIZATION READINESS (RQ21.58)

For Windows experimental-API work, keep these claims separate:
`DLL present ≠ symbols present ≠ DLL loadable ≠ API operational ≠ containment enforced ≠ E completely observed ≠ seven-guarantee PASS`.

P0 readiness must bind a known-good execution channel to the exact target before running even a read-only probe. Resolve native OS path/architecture and record collection-process bitness to avoid WOW64 redirection ambiguity. Preserve raw commands/output, timestamps, machine identity, tool version/hash, DLL identity and signature status. A hash is an identity, not authority; compare it to a trusted expected value only when such a reference exists. If the data cannot be read without elevation, record UNKNOWN and stop rather than elevate.

Do not promote a WFP SID filter condition to complete network-effect observation without proof of event acquisition, attribution, allowed/denied-path coverage and loss handling. Do not assume generic `CreateProcess` attribute lists or inherited handles work with the experimental API when its contract rejects non-NULL process/thread attributes and `inheritHandles=TRUE`.

RQ21.58 routing: first establish exact-target channel readiness → P0 static inspection → independent verification. P0 does not authorize DLL loading, API invocation, candidate execution or implementation. Preserve `implemented ≠ proven`, `hash ≠ authority`, and `API candidate ≠ composed substrate`.

Source: `CHAT-ARCH-2026-10-08-177-rq21-58-focused-windows-substrate-audit-adjudication.md`.

---

## 2026-10-08 METHOD AMENDMENT — EXPERIENCE-ACTIVATION GATE BEFORE TASK/PROMPT CONSTRUCTION

For every material IABV objective, do not construct a prompt for Deep Research, Sonnet, Codex, Devin or another actor until objective-conditioned IABV frame activation has happened.

Mandatory entry and experience-activation sequence:
1. verify the remote `main` SHA and pin source reads to that exact revision;
2. read `README.md` for the entry, authority and evidence contract;
3. read the top routing snapshot of `CURRENT-STATE.md`;
4. use `CONTEXT-INDEX.md` to select objective-relevant domains and records;
5. apply this `MEMORY-OPERATING-PROTOCOL.md` for progressive retrieval, provenance, evidence classification and experience activation;
6. retrieve only relevant historical/source records, prior failures, false positives, closed edges, rejected alternatives, negative knowledge, method deltas, actor/readiness lessons and existing-organ reuse candidates;
7. explicitly activate `UAAL-ROOT-001` and relevant lineage when the objective touches global vision, architecture, universal semantics/generalization, cross-domain composition, capability/realization selection, learning, memory/continuity or protocol design; retain a parent link for narrower tasks without loading the entire corpus;
8. reconcile current evidence and classify FACT / REPORT / INFERENCE / HYPOTHESIS / DECISION / VERIFIED / UNPROVEN as appropriate;
9. identify the first still-open causal/evidential edge and derive capability, access, independence and readiness requirements;
10. compile each relevant past failure into a concrete prompt constraint, false-positive control, required observation, stop condition or acceptance gate;
11. only then construct the task/prompt.

The activated experience must change the task. Copying historical text into a prompt without converting relevant lessons into operational constraints does not satisfy this gate.

RQ21.55 demonstrated wrong-object drift. RQ21.56 demonstrated that a broad report can remain on the general platform topic but fail to compare the specific required guarantees and cite auditable primary evidence. New prompts must explicitly lock the exact object and map every required guarantee to source/API, boundary, coverage gap and proof requirement.

This protocol is a temporary cognitive/coordination method using existing memory organs. It does not assert that IABV runtime autonomously performs this process and does not justify a new universal coordinator/memory organ.

---

## 2026-10-08 METHOD AMENDMENT — FRESH-CHAT SPACE-TIME / REMOTE-STATE GATE

A new chat is not a continuation of the previous prompt. It is a fresh state-reconstruction event.

Before routing:
1. establish temporal provenance (current local time + UTC equivalent);
2. establish spatial/source provenance (repository, verified remote main tip, latest canonical episode);
3. establish executable provenance (pinned baseline SHA + tree, and whether the current task is using that baseline as source truth);
4. reconcile the material recent records and current memory surfaces;
5. classify transcript claims as FACT / INFERENCE / ASSUMPTION / UNPROVEN;
6. recompute the first open causal/evidential edge;
7. select actor from capability-fit and readiness/evidence, not from the previous prompt.

Important:
`reported SHA ≠ verified remote SHA`;
`proposed RQ/decision ≠ canonical RQ/decision`;
`current main ≠ pinned executable baseline unless independently verified`.

Do not describe a baseline→main diff as documentation-only unless the actual compare confirms it. A documentation-only reconciliation commit proves only that the reconciliation itself changed documentation, not that the entire repository delta from a historical baseline is documentation-only.

Writeback rule:
promote only material Knowledge Delta / Method Delta / Routing Delta. Avoid duplicate archive entries when no new durable information exists; create a reconciliation record when the fresh-state check itself adds provenance, correction or routing clarity.


## 2026-10-08 METHOD AMENDMENT — ADVERSARIAL CONTRACT REPAIR AFTER RQ21.49

Once an independent challenger establishes PASS WITH BOUNDED REPAIRS, separate repairs into:
- precision repairs that can be incorporated without new normative choice;
- normative repairs that must be explicitly accepted by the Human Domain Owner.

For RQ21.49:
precision-oriented repairs: R1, R4, R5, R7;
mixed precision/normative repair: R6;
normative repairs: R2, R3, R8.

Routing consequence:
do not re-run a generic adversarial audit before the owner closes the normative set; after owner closure, ChatGPT freezes the contract, then the next implementation-facing actor may be selected.

## 2026-10-08 METHOD AMENDMENT — CURRENT CLAUDE 5.5 ACTOR POOL AND MODEL-SPECIFIC ROUTING

Current user-available Claude pool is Sonnet 5.5 + Haiku 5.5. Actor selection remains capability-fit and edge-driven; model names are not authority labels.

Model routing guidance:
- Sonnet 5.5: default external challenger for material claims requiring sustained reasoning, source archaeology, contract falsification, complex code review, bounded architecture review, and long-horizon investigation. Use when the information gain comes from a materially independent second judgment.
- Haiku 5.5: default for high-volume/low-latency work, compaction, summarization, classification, triage, narrow repeatable checks, browser/computer-use substeps, and bounded subagent tasks. It may handle a focused architecture/security review when the scope is narrow, but such review does not transfer normative authority.
- ChatGPT: coordinator/reconciler and canonical memory writer; do not use model preference as a substitute for evidence.
- Codex: code/source actor after the code-facing edge is actually open and experiment/readiness constraints are met.
- Devin: Windows/runtime/UI actor only when the required execution channel is available and provenance/oracle readiness is satisfied.

Substitution rule:
Opus 5.5 unavailable to the user → Haiku 5.5 only for the bounded class of review that Haiku was actually assigned. This is scoped substitution, not equivalence. Sonnet 5.5 is independently available and should not be demoted to Haiku for material adversarial verification merely because Haiku was used earlier.

For RQ21.48 specifically:
Haiku 5.5 already completed the bounded owner-contract review and returned OWNER-CONTRACT INCOMPLETE. Therefore the next AI challenge must not repeat the same audit. The user/domain owner must first close the normative decisions; then ChatGPT reconciles; then Sonnet 5.5 performs a focused adversarial challenge if the contract is material/changed; then Codex implements only the surviving minimal contract.

Never inherit NEXT ACTOR mechanically. Recompute from:
objective → current verified truth → first open edge → required capability → actor fit → readiness/evidence contract → minimum discriminating action.
## 2026-10-08 METHOD AMENDMENT — ACTOR SUBSTITUTION UNDER AVAILABILITY LOSS

Actor availability is not the routing authority.
Whenever a designated actor becomes unavailable, record the loss explicitly and select the nearest capability-fit substitute only when required independence and evidence quality are preserved.

Current scoped substitution:
Opus 5 unavailable → Haiku 5.5
for bounded architecture/security/adversarial contract review.

Do not generalize this as universal model equivalence.
Human Domain Owner remains the authority for normative security/containment decisions.

Preserve: objective → uncertainty → capability → actor-fit → evidence readiness → action.

## 2026-10-08 METHOD AMENDMENT — RQ21.47 SUBSTRATE-CONTRADICTION GATE

A complete capability contract may reveal a separate missing realization substrate.

When this occurs:
`contract closure → realization-substrate feasibility audit → owner authorization if new security/containment boundary is required → minimal implementation`.

Independent forensic audit is required before introducing new containment/security machinery.

Classify partial reuse by causal role:
- comparator reuse does not equal containment;
- policy/authorization does not equal containment;
- metadata does not equal effect observation;
- historical design does not equal current executable infrastructure.

For new containment/security boundaries, the owner must explicitly authorize the bounded E/threat-model/isolation contract before implementation.

Preserve:
`REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`
and `implemented ≠ proven`.

## 2026-10-08 METHOD AMENDMENT — REALIZATION-SUBSTRATE FEASIBILITY GATE

A closed capability contract does not imply that the repository already has a faithful realization substrate.

For material implementation attempts, preserve:
`semantic/contract closure → realization-substrate feasibility → implementation → independent verification → runtime proof`.

When a capability realization attempt is blocked by a real substrate contradiction:
- first search for reusable/composable current executable mechanisms;
- use historical records only as candidate generators, not as present evidence;
- do not weaken the functional predicate;
- do not create cosmetic gates around an uncontained execution path;
- do not introduce a new universal organ/router/registry to mask the gap;
- if a genuinely new containment/security substrate is required, obtain explicit owner authorization before implementation.

Negative knowledge must remain bounded:
`no mechanism found in audited scope ≠ repository-wide absence`.

Routing rule:
when the implementation actor reaches the substrate contradiction, prefer an independent forensic/source auditor before re-routing back to implementation.

## 2026-10-07 METHOD DELTA — EMPTY-SET CONTRACT CLOSURE

A capability-constrained empty set must become an explicit governed negative outcome, not an unconstrained selection.

Reusable existing state:
ToolTaskStatus.DEFERRED.

New implementation invariant:
selector NO_ELIGIBLE_REALIZATION → task deferred when materialized → every downstream selection/fallback path preserves the negative decision.

Candidate eligibility remains ephemeral selection state. Do not persist eligible_tool_ids as durable ToolTask truth.

Defined ≠ wired ≠ proven remains active.

## 2026-10-07 METHOD DELTA — CAPABILITY-CONSTRAINED EMPTY SET

New invariant:
capability-constrained empty set ≠ unconstrained selection.

When a required capability has no eligible realization, downstream fallback semantics must not silently convert the empty set into unrestricted selection.

Existing domain reuse candidate:
ToolTaskStatus.DEFERRED already exists, but its use in this selection path is not currently wired/proven.

Routing rule:
first close empty-set/defer propagation before adding broader capability vocabulary, plasticity or runtime behavior.

Preserve:
required capability identity
≠ readiness
≠ availability
≠ candidate set
≠ route.

No new architecture unless exact source evidence proves existing-organ composition impossible.

## 2026-10-07 METHOD AMENDMENT — CAPABILITY CONTRACT MUST SEPARATE STABLE REQUIREMENT FROM EPHEMERAL CANDIDATES

For capability-aware routing, distinguish:

`required capability identity` = stable task semantic requirement;

`readiness snapshot` = decision-time evidence/state about satisfying that requirement;

`realization declaration` = stable ToolCard claim of what the card can realize;

`capability-eligible candidate set` = ephemeral selection result derived from the above plus current inventory/scope;

`route` = selected concrete ToolCard/tool ID and its adapter.

Do not persist an ephemeral candidate set as if it were an invariant of the task.

Minimum multi-requirement rule:
`required_capability_ids ⊆ realizes_capability_ids` for conjunctive requirements. Do not infer OR semantics from list membership.

Routing rule:
capability eligibility is a hard gate before preference, Synaptic selection, lexical fallback or concrete route fixation.

## 2026-10-07 METHOD AMENDMENT — VERIFY THE OPERATIVE SELECTOR BEFORE WIRING

A mechanism is a valid composition candidate only after its actual normal call path is confirmed.

For the current frontier:
`ToolTeachService._select_mode() → InteractionModeSelector.select()`
is an actual normal selection path and therefore must be considered before proposing changes to `ToolRegistry`.

However:
`selector exists ≠ selector already consumes required capability`.

Before implementation verify:
- actual input dominance (`suggested_tool_id`, explicit external preference, task kind, availability);
- capability identity preservation;
- route impact;
- readiness/availability separation.

Construction remains:
`REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`.

## 2026-10-07 METHOD AMENDMENT — TWO-CALLER SHARED-GAP GATE

A single targeted caller showing capability loss is not sufficient to claim a shared architectural gap.

Before construction, contrast a second normal caller and check whether both converge on the same concrete selection boundary.

When both callers show:
`structured capability/readiness upstream → ToolTask → realization picker`
without first-class capability identity at the picker, classify this as **stronger structural localization**, not repository-wide proof.

Preserve the distinction:
`upstream capability influence ≠ capability identity at realization selection`.

The independent verifier must still challenge:
- uninspected normal callers;
- indirect encodings through tool IDs, assistant kinds, task kinds or text;
- existing capability-aware contracts that can be reused/composed.

Construction remains:
`REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`.

No new universal registry/mega-organ is justified merely by two caller contrasts.

Routing after episode 134:
**SONNET / CLAUDE** for independent static verification of the shared capability-blind boundary.
No runtime and no code change before that verification.

## 2026-10-06 METHOD AMENDMENT — REPORTED HARNESS READINESS / INDEPENDENT ARTIFACT VERIFICATION

A harness result may advance the routing gate when the reported self-test directly covers the authorized evidence contract, but the coordination record must distinguish:
`reported artifact identity/readiness ≠ independently re-read artifact ≠ runtime evidence`.

For the current RQ13 harness:
- CODEX reports SHA `C94D983D5A8B33C906807AA45B224D4F45430D616EB61E62DD140C32A15B50EA`;
- CODEX reports the fingerprint, excluded-path isolation and contract self-tests passing;
- no IABV runtime occurred in the correction;
- the Windows bytes were not independently re-read here.

Therefore the current state may be routed as **ready for a fresh authorization decision**, not as runtime-proven.

Preserve:
`new harness artifact → new exact SHA → fresh authorization`.
Never inherit runtime authorization across harness modifications.

## 2026-10-06 METHOD AMENDMENT — EVIDENCE-CONTRACT COMPLETENESS GATE

For any material experiment, an evidence contract is incomplete when a required output field cannot be produced by the authorized harness.

Preserve:
`instrumentation exists ≠ evidence contract implemented`.

A readiness failure in the harness is a precondition failure, not partial runtime evidence. Correct the harness first, generate a new artifact identity/digest, self-test it against the full contract, and only then request fresh runtime authorization.

Never weaken the experiment contract merely to reuse an existing harness.

## 2026-10-06 METHOD AMENDMENT — RUNTIME ARTIFACT PROVENANCE GATE

A runtime observation may not inherit the evidentiary status of a Git SHA merely because HEAD points to that SHA.

Before promoting runtime evidence to baseline truth, require:
`runtime execution → executable fingerprint → clean/dirty worktree status → exact diff/overlay identity → artifact attribution → verification → Knowledge Delta`.

When a candidate worktree contains uncommitted changes, classify the runtime result as variant-scoped or indeterminate until the exact executed artifact is established.

This gate is especially mandatory when an earlier experiment created an uncommitted candidate seam in the same files used by a later runtime run.

Preserve the distinction:
`HEAD baseline ≠ executed artifact`
when the worktree is dirty.

This rule does not prohibit candidate experiments; it prevents candidate-runtime observations from silently becoming baseline-runtime proof.

## 2026-10-06 METHOD AMENDMENT — TEMPORAL IDENTITY TRACE AT RUNTIME HANDOFFS

When a live experiment crosses process/service/representation boundaries, memory and routing must preserve identity at each boundary rather than relying on the final state.

Required trace shape when material:
`producer/previous state ID → persisted ID → consumer in-memory ID → derived/translated representation ID → final persisted ID`.

Also preserve the temporal ordering of refresh/request events because bootstrap, monitors and perception assembly may replace state while an observation is in flight.

A final representation matching final persistence does not prove preservation of an earlier representation, and a concurrent refresh does not by itself establish full causal attribution.

For runtime handoff experiments, the evidence contract must therefore distinguish:
`identity continuity | replacement | concurrency | persistence match | causal attribution`.

The first open edge is the first boundary where identity, consumer attribution or causal ordering remains unresolved.


## 2026-10-05 METHOD AMENDMENT — SELF-CODE EVOLUTION / CAPABILITY-ORIENTED PLASTICITY

When the developmental objective is IABV evolution of its own code, route through the smallest existing composition that can close:

`verified deficit → required capability → existing-organ archaeology → minimal code-evolution hypothesis → isolated variant → baseline/candidate validation → independent verification → governed promotion/rejection/rollback → capability/method/relation/routing delta → later reuse`.

Do not treat a proposal, sandbox result or PR description as proof of code evolution.

Prefer capability-oriented evolution over file-oriented growth. A successful change may:
`ACQUIRE | REFINE | COMPOSE | CONSOLIDATE | SPECIALIZE | GENERALIZE | SUPERSEDE | ROLLBACK`.

Preserve the broad capability repertoire while minimizing the active working set. Never delete capability knowledge merely because the current objective does not need it.

For every self-code evolution candidate, preserve at minimum:
`objective + deficit + required capability + existing owner(s) + baseline SHA + candidate diff + tests + runtime evidence + independent verification + promotion decision + rollback path`.

The first developmental inflection is achieved by a bounded closed loop from observed deficit to auditable incorporated code change; stronger developmental plasticity requires later non-identical reuse that changes a future development decision.

# IABV v1.5 — Operational Memory Protocol

## PURPOSE

This document defines how the GitHub historical layer functions as **operational memory** for IABV across chats and across participating AIs.

It is not a transcript archive and not a second brain. It is the control protocol that turns distributed historical records into objective-conditioned context.

## CORE PROPERTY

Continuity is not:

`old chat → copy old prompt → continue`

Continuity is:

`new objective → discover relevant memory → reconcile with current reality → activate context → select capabilities/roles → act → verify → learn → write back`

The same objective may activate different historical knowledge at different times because the current repository, runtime, evidence state, unresolved risks and available AI capabilities change.

## MEMORY LAYERS

### M0 — Entry contract

`README.md`

Defines continuity rules and epistemic boundaries.

### M1 — Objective router

`CONTEXT-INDEX.md`

Maps a current objective to relevant domains and source records.

### M2 — Current operational state

`CURRENT-STATE.md`

Provides the compact reconciled bridge between historical knowledge and current project state.

### M3 — Cross-IA capability and transfer model

`SYMBIOSIS-MAP.md`

Records useful AI capabilities, knowledge transfers, corrections and collaboration patterns.

### M4 — Latent/unresolved knowledge

`UNRESOLVED-KNOWLEDGE.md`

Preserves ideas, deductions, questions, future experiments and strategically important work that never became tickets or commits.

### M5 — Historical source records

All registered `CHAT-ARCH-*`, reconciliation, persistence and forensic records.

These are evidence-bearing historical sources, not merely background reading.

### M6 — Current repository/runtime evidence

Current code, tests, branches, commits, runtime fingerprints and independently observed state.

M6 outranks historical claims when answering what is true **now**.

### M7 — Systemic integrity / connectivity synthesis

`SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`

This layer is the routed synthesis for cross-organ contract integrity, temporal/semantic coherence, duplication/drift detection and the history of which maintenance responsibilities are already present versus fragmented or missing.

M7 is not an authority replacing M6. It is a high-value reasoning aid that tells the next investigation **which existing organs to inspect before creating new architecture**.

## OBJECTIVE-CONDITIONED MEMORY RETRIEVAL

A new chat must perform retrieval in this order:

```text
OBJECTIVE
  ↓
BOUNDARY IDENTIFICATION
  ↓
CLAIMS THAT MUST BE TRUE
  ↓
RISKS / FAILURE MODES IMPLIED
  ↓
OBJECTIVE DOMAIN MATCH
  ↓
M1 ROUTING
  ↓
M2 CURRENT STATE
  ↓
M3 SYMBIOSIS / ROLE EVIDENCE
  ↓
M4 UNRESOLVED / LATENT KNOWLEDGE
  ↓
M5 RELEVANT SOURCE RECORDS OR CANONICAL ABSORPTION
  ↓
M7 SYSTEMIC INTEGRITY SYNTHESIS WHEN MATERIAL
  ↓
M6 CURRENT REPOSITORY / RUNTIME RECONCILIATION
  ↓
ACTIVE CONTEXT PACKET
```

The retrieval result is **not** `all history`. It is the minimum context set whose omission could materially alter the current decision.

## CANONICAL ABSORPTION

A source archive does not have to be directly reachable from `main` to contribute to canonical operational memory.

A branch-only or legacy source may be canonically absorbed when:

1. the source branch/ref and source record are identified;
2. the source was remotely verified or otherwise independently recovered;
3. materially decision-relevant knowledge is explicitly transferred into the canonical memory layer;
4. the transfer preserves the source provenance and does not rewrite the historical source silently;
5. contradictions and unresolved status are preserved;
6. the absorption record itself is remotely readable from canonical `main`.

This allows archival provenance to remain faithful without merging unrelated implementation branches merely to place a historical Markdown file on `main`.

Canonical absorption is therefore an alternative to direct canonical source reachability for the purpose of cross-chat continuity and deletion safety.

## ACTIVE CONTEXT PACKET

For each new objective, the activated memory should contain:

```text
OBJECTIVE
CURRENT_TRUTH
RELEVANT_HISTORY
RELEVANT_EXPERIMENTS
RELEVANT_FAILURES
NEGATIVE_KNOWLEDGE
RELEVANT_UNIMPLEMENTED_IDEAS
ACTIVE_CONTRADICTIONS
PROVENANCE_REQUIREMENTS
CURRENT_GATE
LAST_INDEPENDENTLY_VERIFIED_STATE
RELEVANT_CROSS_IA_LESSONS
AVAILABLE_CAPABILITY_EVIDENCE
RELEVANT_SYSTEMIC_INTEGRITY_ORGAN_MAP
SMALLEST_DISCRIMINATING_NEXT_ACTION
```

If a historical item cannot affect one of those fields, it normally remains inactive unless deep reconstruction is requested.

## RELEVANCE SCORING PRINCIPLE

Do not use a purely lexical match. Historical relevance should be judged by causal usefulness.

A record has high activation priority when it:

1. concerns the same architectural/security/runtime boundary;
2. contains a prior failure that can recur;
3. changes the interpretation of a current claim;
4. identifies a prerequisite or invariant;
5. contains an experiment that discriminates between today's competing hypotheses;
6. contains unimplemented knowledge directly applicable now;
7. records a cross-IA correction that changes the proper method;
8. establishes the latest independently verified gate for the same subsystem;
9. changes which AI capability should be selected;
10. identifies an existing organ that can replace a proposed new component, reducing unnecessary architecture creation.

## TEMPORAL RECONCILIATION

Historical memory is not immutable current truth.

For every material activated claim:

```text
historical claim
    ↓
current source inspection
    ↓
branch/commit provenance
    ↓
runtime evidence when required
    ↓
status = CONFIRMED / SUPERSEDED / REFUTED / UNRESOLVED
```

Never promote a historical claim solely because it appears in multiple archives.

## CROSS-IA SYMBIOSIS AS MEMORY

The system must preserve not only outputs but **knowledge transfer**.

For a material collaboration event, preserve:

```text
SOURCE_AI
→ INITIAL_INTERPRETATION
→ CHALLENGER_AI
→ CONTRADICTION / SUPPORT
→ IMPLEMENTER / EXPERIMENTER
→ OBSERVATION
→ RECONCILIATION
→ NEW INVARIANT
→ FUTURE METHOD CHANGE
```

The important reusable object is the changed method, not the prestige of the AI that produced it.

## DYNAMIC ROLE SELECTION

Historical roles are capability evidence, not permanent assignments.

For each objective, determine which capabilities are needed:

```text
architecture synthesis
source audit
adversarial challenge
implementation
runtime observation
controlled experimentation
provenance adjudication
result verification
systemic connectivity analysis
```

Then select available AIs according to demonstrated capability for that boundary.

Never force every objective through a fixed `ChatGPT → Devin → Claude → Codex` sequence.

## INDEPENDENCE RULE

For a critical claim:

`producer != sole verifier`

An implementation agent should not be the only authority for the claim it created when an independent verification path is available and materially useful.

## MEMORY ACTIVATION DEPTH

Use progressive retrieval:

### Depth 0 — Orientation

Read M0 + M1 + M2.

### Depth 1 — Objective context

Activate M3 + M4 entries directly relevant to the objective.

When the objective touches cross-organ integrity, add M7 here.

### Depth 2 — Evidence

Read the most relevant M5 records **or their canonical absorption record**, then current source/commit evidence.

### Depth 3 — Contradiction reconstruction

Expand into neighboring domains, prior failed experiments and conflicting historical interpretations.

### Depth 4 — Full forensic reconstruction

Read broad chronology only when the objective genuinely requires it or when lower depths leave unresolved contradictions.

## NEGATIVE KNOWLEDGE HAS PRIORITY

When historical evidence says an experiment did not prove a tempting claim, activate that limitation before repeating the experiment.

Examples:

`test pass != production proof`

`receipt != cognition`

`persistence != learning`

`signature != legitimate authority`

`field existence != canonicality`

`repository target != runtime target until proven`

`archive exists != deletion safe`

`event recorded != connection validated`

`local observation != cross-organ coherence`

`recommendation exists != prediction exists`

## UNIMPLEMENTED KNOWLEDGE MUST STAY VISIBLE

The system must retrieve ideas that were:

- proposed but never implemented;
- discussed without a ticket;
- inferred but never validated;
- rejected temporarily rather than permanently;
- left as future experiments;
- identified as architectural consequences;
- identified as lost links between subsystems.

Implementation status must not determine knowledge preservation.

## DECISION LOOP

Once context is activated:

```text
ACTIVE CONTEXT
  ↓
HYPOTHESIS / CLAIM
  ↓
EVIDENCE REQUIREMENT
  ↓
MINIMAL DISCRIMINATING ACTION
  ↓
OBSERVATION
  ↓
INDEPENDENT VERIFICATION
  ↓
RECONCILIATION
  ↓
DECISION
  ↓
KNOWLEDGE DELTA
```

Do not perform broad work merely because broad history exists.

## KNOWLEDGE WRITEBACK

Write back only material deltas.

A new historical update is warranted when the session creates or changes:

- a proven/refuted claim;
- an evidence boundary;
- a failure mode;
- an experiment and its result/limits;
- an architectural deduction;
- a decision/rejected option;
- a provenance relationship;
- a current gate;
- a strategically relevant unresolved idea;
- a cross-IA learning transfer;
- the collaboration strategy itself;
- the canonical absorption/routing state;
- a cross-organ integrity/contract/temporal/semantic finding;
- the identification of an existing organ that can replace a proposed new component;
- a provenance discrepancy that changes whether evidence can be promoted.

Routine repetition should not generate redundant history.

## SYNTHESIS UPDATE RULE

When new knowledge changes the operational model:

1. preserve the source historical record;
2. update `CURRENT-STATE.md` when current truth changed;
3. update `CONTEXT-INDEX.md` when routing changed;
4. update `SYMBIOSIS-MAP.md` when a capability/interaction lesson changed;
5. update `UNRESOLVED-KNOWLEDGE.md` when latent knowledge changes status;
6. update `CANONICAL-ABSORPTION-2026-09-11.md` when source reachability/absorption status changes;
7. update `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md` when a systemic-integrity finding changes;
8. register new source records in `ARCHIVE-REGISTRY.md`.

Do not silently rewrite historical records to make contradictions disappear.

## EVIDENCE PROMOTION GATE

A report produced by an AI is not automatically evidence at the same level as the artifact it describes.

Before promoting a result to a stronger epistemic state, reconcile:

```text
reported claim
  ↓
reported artifact
  ↓
exact branch/ref
  ↓
exact commit SHA
  ↓
working-tree state, when relevant
  ↓
artifact read-back
  ↓
runtime provenance
  ↓
independent verification
```

If the reported artifact is absent from the cited commit, preserve the discrepancy and downgrade the claim to the highest state actually supported. Do not silently infer that the report used committed code.

## CAUSAL EDGE DISCIPLINE

Treat each meaningful arrow as an independent evidentiary edge.

Examples:

`selection proven != execution proven`

`adapter invoked != authorization accepted`

`authorization accepted != transport transmitted`

`transport transmitted != external effect`

`external effect != independently verified outcome`

`verified outcome != learning`

`learning state != future decision influence`

`future decision influence != behavioral change`

`behavioral change != improvement`

A future investigation should advance to the **first open causal edge**, not restart already closed edges, unless new contradictory evidence appears.

## SYMBIOSIS MEASUREMENT

A cross-IA collaboration is materially successful when it creates an observable delta in the working method/system, not merely agreement.

Track qualitatively or quantitatively where possible:

`ΔK = demonstrated knowledge delta`

`Δπ = policy/method change`

`ΔB = observable behavior change`

`ΔY = observable outcome change`

Agreement among agents is not a proxy for ΔK, Δπ, ΔB or ΔY.

## DYNAMIC MESSAGE ECONOMY

Use the minimum number of external AI interventions required to remove the current material uncertainty.

Do not invoke an agent to repeat an edge already closed with stronger evidence.

Prefer a single actor to combine compatible execution tasks when doing so preserves audit independence and provenance. Split roles when independence or materially different capability is required.

Reserve high-cost/high-reasoning interventions for:

- genuine architectural contradiction;
- policy adjudication under competing valid interpretations;
- higher-order causal ambiguity;
- a failure that cannot be reconciled by the current runtime/source auditor.

## ROLE-ROUTING EXAMPLE — 2026-09-17

For the current causal learning/P0-B frontier:

`ChatGPT → Sonnet → (Opus only if contradiction) → Devin if fix needed → Sonnet re-audit`

This is an example of capability-driven routing, not a permanent sequence.

## REPORT-TO-CANONICAL-STATE RULE

Every material external-agent report that changes the project model should be converted into a structured delta before the next actor is selected.

The conversion should include:

```text
REPORT
→ OBSERVED FACTS
→ CLAIMS
→ EVIDENCE LEVEL
→ PROVENANCE
→ CONTRADICTIONS
→ NEGATIVE KNOWLEDGE
→ KNOWLEDGE DELTA
→ POLICY / ROLE CHANGE
→ NEXT CAUSAL EDGE
```

This prevents the next prompt from accidentally carrying forward assertions as facts.

## MEMORY DECAY / SUPERSESSION

A historical item may become:

`ACTIVE | DORMANT | SUPERSEDED | REFUTED | RESOLVED | RELEVANT_AGAIN`

Status changes require evidence.

A superseded item remains historically accessible because it may explain why the current design exists.

When current code or runtime contradicts an older memory item, do not delete the older item. Mark the older item SUPERSEDED/REFUTED and update the current synthesis, routing and unresolved register as appropriate.

This is the mechanism by which a new architecture state can **replace the active interpretation without losing the lineage that explains the change**.

## DELETION SAFETY

Deletion safety is a **knowledge-preservation gate**, not a technical-task-closure gate.

A chat can be deleted while an engineering task remains OPEN if the open state, failures, evidence boundaries, decisions, provenance, pending experiments and next actions are durably preserved.

For a historical chat, the canonical preservation condition is:

```text
DIRECT_CANONICAL_SOURCE
OR
CANONICAL_KNOWLEDGE_ABSORPTION
```

plus:

```text
PROVENANCE_TO_SOURCE
REMOTE_READBACK
KNOWLEDGE_LOSS_TEST=PASS
BLIND_RECONSTRUCTION=PASS
NO_MATERIAL_KNOWLEDGE_ONLY_IN_CHAT=YES
```

An exact source archive remaining on a non-canonical branch is not, by itself, a deletion blocker when the material knowledge has been canonically absorbed and the source provenance remains recoverable.

Conversely, a technical task being closed does not make a chat deletable if material historical knowledge is still only in the transcript.

## CHAT / TRANSCRIPT INTAKE CONTRACT

When a user supplies a prior conversation, pasted transcript, partial excerpt or chat artifact, preserve its source identity and be explicit about what was actually available and inspected. Use this contract before claiming the material was read completely or canonically absorbed.

Record, as applicable:

- `SOURCE_ID / SOURCE_NAME` and origin kind (pasted text, attachment, Library artifact, URL or other source);
- source extent as declared and source extent actually accessible;
- segments/pages/lines/bytes actually inspected, where measurable;
- coverage summary and known omitted, inaccessible or uninspected portions;
- byte-level SHA-256 only when the actual bytes were available and the digest was actually calculated; otherwise `UNKNOWN / NOT AVAILABLE`;
- `COMPLETENESS_STATUS`: `FULL_WITHIN_DECLARED_ARTIFACT`, `PARTIAL_EXTRACT`, `SEGMENTED_INCOMPLETE` or `UNVERIFIABLE`;
- original human objective, idea, intuition, correction and decision, separated from AI interpretation;
- claims classified as report, fact, inference, hypothesis, decision, verified result or unresolved;
- material errors, false positives, contradictions, rejected alternatives and negative knowledge;
- the concrete future task constraint, experiment, stop condition or acceptance gate changed by each relevant lesson;
- Knowledge / Relation / Method / Routing deltas, the canonical owner layer, source links and the next open edge.

Do not require a cryptographic hash when the source bytes are unavailable. Do not describe a partial extract as a complete chat. Do not claim full reading, absorption, independent verification or causal learning beyond the actual source coverage and observations.

Preserve source-archive identity separately from canonical synthesis identity. Store durable, decision-relevant knowledge in the responsible canonical projections rather than copying the entire transcript into every memory surface.

## CHAT-TO-CHAT CONTRACT

A new chat must be able to enter IABV with only:

```text
CURRENT OBJECTIVE + GITHUB ACCESS
```

and reconstruct the relevant operational memory without requesting the previous transcript.

The previous transcript is supplemental evidence, not a mandatory dependency.

## SUCCESS CONDITION

This memory architecture is successful only when a genuinely new chat:

1. identifies its objective;
2. discovers the relevant historical domains itself;
3. activates the right history without a universal dump;
4. reconstructs the current gate and provenance;
5. inherits prior negative knowledge and unimplemented ideas;
6. selects roles/capabilities according to the current uncertainty;
7. avoids repeating obsolete work;
8. identifies existing organs before proposing new architecture;
9. produces a new knowledge delta;
10. writes that delta back into the appropriate durable layer.

That is the operational definition of **cross-chat continuity** for IABV.

## 2026-09-17 PROTOCOL AMENDMENT — CAUSAL SYMBIOSIS / PROVENANCE

This amendment is active for future chats.

### A. Treat provenance as part of the evidence, not metadata decoration

A claim may not be promoted merely because an AI report contains a SHA. The exact artifact must be recoverable from that SHA/ref, or the report must explicitly identify the uncommitted working-tree state used.

### B. Treat discrepancies as useful state

A contradiction such as:

`reported test exists`

versus

`remote commit does not contain test`

must become an explicit unresolved/provenance item and must affect the next actor's task.

### C. Route by uncertainty, not habit

Before assigning an actor, ask which capability is the bottleneck now:

`architecture | source audit | runtime | controlled experiment | implementation | verification | reconciliation`

Then choose the least redundant capable actor and add an independent challenger only when the claim warrants it.

### D. Advance monotonically through causal edges

Do not repeatedly reprove a closed edge because a new prompt is easier to write that way. Preserve its evidence level and move to the first still-open edge.

### E. Convert reports into durable operational state

After a material report, update current state, routing, capability evidence, unresolved status and source registry as appropriate before starting another cross-IA cycle.

### F. Preserve explicit claim granularity

Future prompts must distinguish at least:

`SOURCE-PROVEN`
`UNIT-TEST-PROVEN`
`INTEGRATION-TEST-PROVEN`
`PRIMARY-RUNTIME-PROVEN`
`INDEPENDENTLY-RUNTIME-VERIFIED`
`NOT PROVEN`
`CONTRADICTED`

Do not use vague closure language such as “basically proven”.

## 2026-09-20/21 PROTOCOL AMENDMENT — METACOGNITIVE SELF-USE

### A. Use IABV itself as the first analyzer for deep self-assessment

When the objective is self-state, architecture, metacognition, causal diagnosis or development acceleration, retrieve the relevant memory and invoke the existing IABV self-observation/metacognition organs before routing immediately to an external AI.

This is not a claim that IABV is correct. It is a deliberate experiment to make IABV a participant in its own method.

### B. Deep self-assessment contract

A valid preflight should attempt:

`objective`
→ depth
→ current reality
→ architecture/code introspection
→ change-surface analysis
→ uncertainty
→ hypotheses
→ discriminating experiment
→ verification boundary
→ first broken edge
→ Knowledge Delta.

### C. Maintain independent verification

For critical claims:

`IABV self-assessment = producer`
and
`independent external audit = verifier`.

Do not allow the self-auditing system to become its own sole evidence authority.

### D. Separate observe from mutate

Preserve:

`OBSERVE → REASON → HYPOTHESIZE → EXPERIMENT → VERIFY → AUTHORIZE → CHANGE → REVERIFY → LEARN`.

Any mutation performed during analysis must be represented as an explicit action and excluded from the pure observation claim.

### E. Add changed-surface analysis

For any material change, search beyond the modified function/file:

`symbol → callers → producers → consumers → contracts → fallbacks → alternate routes → negative cases → downstream effects`.

### F. Distinguish health from metacognition

`system.self_awareness` may report how IABV is doing.

`system.metacognition` should explain why, what is unknown, what changed, what may fail next and what experiment best distinguishes hypotheses.

Do not introduce another brain or intent merely to represent this.

### G. Development-inflection test

The method should only be considered to accelerate when verified experience produces reusable knowledge and a later observable decision/strategy change while routine human coordination decreases.

### H. Cross-IA knowledge transfer

Preserve:

`SOURCE_AI → INTERPRETATION → CHALLENGER → CONTRADICTION/SUPPORT → IMPLEMENTER → OBSERVATION → RECONCILIATION → NEW INVARIANT → METHOD CHANGE`.

The durable object is the changed method, not the agreement or prestige of any model.
## 2026-09-21 PROTOCOL ADDENDUM — STRATEGIC IDEAS MUST BECOME RETRIEVABLE WORK

When a conversation identifies a material unimplemented capability that can advance the project objective, do not leave it only in the transcript.

Persist it in the appropriate canonical layer:
- `UNRESOLVED-KNOWLEDGE.md` for the reasoning and uncertainty;
- `data/evolution/backlog.json` for an executable pending task with priority and dependencies;
- `CONTEXT-INDEX.md` when retrieval/routing changes;
- a dated roadmap when multiple pending ideas require dependency-aware prioritization.

A task entering the backlog is not evidence that its premise is proven. The backlog records an actionable hypothesis or known gap and must retain its evidence basis.

## 2026-09-21 PROTOCOL ADDENDUM — SELF-ASSESSMENT MODE

When the objective is to understand IABV itself, the default reasoning mode becomes:

`objective → selective memory activation → exact repository/runtime reconciliation → native self-assessment → uncertainty map → code/architecture introspection → first open causal edge → smallest discriminating experiment → capability-fit routing → independent verification → Knowledge Delta`.

Do not treat IABV's own report as self-verifying.

Preserve:
`self-awareness ≠ systemic metacognition`
`organ exists ≠ integrated circuit`
`deep introspection ≠ causal learning`
`metacognitive report ≠ future decision change`.

## 2026-09-21 PROTOCOL ADDENDUM — REMOTE PROVENANCE GATE

For every external-agent report that claims a material modification, require before auditor handoff:

`REPORT → ARTIFACT → exact branch/ref → exact SHA → relevant working-tree provenance → remote read-back → claimed content present → runtime provenance when applicable → independent verification`.

Minimum remote gate:
1. SHA resolves remotely;
2. branch/ref contains that SHA;
3. changed file exists in the remote tree;
4. remote content contains the claimed change;
5. any claimed runtime artifact is tied to the exact tested revision.

If any gate fails:
- do not promote the implementation claim;
- do not ask another actor to audit a nonexistent object;
- preserve the provenance contradiction as negative knowledge;
- route only to artifact recovery/publication.

A successfully published artifact closes provenance identity, not runtime truth or causal closure.

## 2026-09-21 PROTOCOL ADDENDUM — FIRST OPEN EDGE DISCIPLINE

Once a claim reaches a stronger evidence state, advance only to the first still-open causal edge.

For I0 M3 this currently means:
`remote artifact verified → independent M3 audit`
then, only if valid:
`real Windows runtime`
then:
`observed external behavior`
then:
`independent verification`.

Do not restart earlier archaeology or conflate unit/mutation evidence with runtime evidence.

## 2026-09-21 PROTOCOL ADDENDUM — LINEAGE-SCOPE RECONCILIATION

For every material commit used as evidence, distinguish two scopes:

1. **Immediate commit scope**
`direct parent → target commit`

2. **Narrative/historical scope**
`named baseline → target commit`

Both must be reconciled when the claim depends on continuity from the older baseline.

Promotion rule:
- If immediate scope is test-only but cumulative scope contains production changes, state both facts.
- Never use a commit message such as "production source unchanged" as proof of ancestry-wide immutability.
- If a test is independently valid at the exact target SHA, it may close the tested property at that SHA even when the branch lineage is not minimal relative to an older baseline.
- Generalization across revisions requires additional evidence.

This becomes part of the evidence promotion gate:
`claim → target SHA → direct parent → historical baseline → cumulative diff → exact source/test at target`.



## 2026-09-21 PROTOCOL ADDENDUM — BIOSOFÍA ARTIFICIAL / DEVELOPMENTAL SUBSTRATE

For objectives touching biosofía artificial, artificial life, autoconstrucción, autoevolución, digital organisms, developmental robotics, generational learning or recursive capability growth, treat the canonical developmental thesis as an objective-conditioned research source:

`IABV_v1.5/docs/history/CHAT-ARCH/BIOSOFIA-ARTIFICIAL-DEVELOPMENTAL-AUTOPOIETIC-THESIS-2026-09-21.md`

Activate it after current-state orientation and before implementation planning.

Use the following reasoning model:

`
objective
→ developmental level
→ current substrate
→ existing organ capability
→ first open causal edge
→ minimum discriminating experiment
→ independent verification
→ Knowledge Delta
→ next developmental cycle
`

The biological analogy must remain a hypothesis generator, never evidence by itself.

Preserve these distinctions:

`
automation != development
memory != learning
learning != heredity
persistence != reproduction
reproduction != evolution
cooperation != higher-level individuality
many organs != integrated organism
complexity != open-ended evolution
self-modification != self-construction
`

Before introducing new architecture, perform organ/contract archaeology and determine whether an existing composition already supplies the required developmental function.

For critical developmental claims, require:

`
report
→ artifact
→ exact revision
→ runtime provenance
→ observation
→ independent verification
→ causal attribution
`

The development target is not uncontrolled self-modification. It is governed, observable, reversible acquisition and organization of new capabilities.

## 2026-09-21 PROTOCOL ADDENDUM — GLOBAL DEVELOPMENT CONTINUITY

For objectives involving biosofía artificial, autonomous development, scientific self-analysis, developmental acceleration, or reduction of routine human coordination, first complete the canonical entry sequence defined by `README.md`. Only then activate the North Star as an objective-specific strategic source:

`00-GLOBAL-DEVELOPMENT-NORTH-STAR-2026-09-21.md`

Supplement the current-state orientation with the relevant `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md`, biosofía thesis/roadmap and exact branch/SHA/runtime evidence as required by the objective. The North Star is not an entry-order or current-routing authority.

The strategic objective is not unrestricted autonomy. It is to make verified experience causally reusable while progressively removing routine human transport from the loop and preserving governance, security and independent verification.

Scientific-organ rule: do not create a new coordinator merely because scientific functions are distributed. First trace existing producer→consumer edges and determine whether the missing boundary is ownership, wiring, invocation, observation or causal effect.

Development-inflection rule: “exponential” is a research hypothesis. Promote it only after longitudinal evidence of compounding verified capability generation per unit of routine human coordination.



## 2026-09-28 — REPORT-CONTINUATION / SPACE-TIME PROVENANCE RULE

A previous actor's final response is an **observation/report**, not automatically the current causal frontier.

Before continuing its suggested next step, reconcile the response against the full provenance chain:

`report → artifact → branch/ref → SHA → working-tree provenance → remote read-back → runtime provenance → independent verification → reconciliation → Knowledge Delta → next decision/writeback`.

Maintain separate statuses for:

- implementation claimed;
- implementation locally present;
- implementation committed;
- implementation remotely attributable;
- runtime reported;
- runtime independently verified;
- causal edge closed.

Special failure pattern:

**response-continuation drift** = following the previous actor's proposed next edge while skipping an unresolved provenance/evidence edge.

Required behavior:

1. Re-anchor to the exact objective and technical baseline.
2. Verify whether the reported branch/ref/SHA is actually resolvable.
3. Determine whether the implementation is committed or only in a modified worktree.
4. Verify artifact/source read-back before treating implementation as canonical.
5. Route to an independent verifier only after an attributable artifact exists.
6. Do not advance semantic research merely because the implementation actor named it as the “first open edge”.

For META-01-E2a this means:

`Devin implementation report → publication/read-back → Sonnet verification → semantic E2b`

not:

`Devin implementation report → immediately investigate hypothesis/prediction`.



## 2026-09-28 — POST-COMMIT COVERAGE RULE

Remote commit attribution closes only the **artifact identity** edge.

After publication, the next verifier must test whether the implementation actually covers the claim:

`source wiring ≠ effective consumer behavior`
`helper-level identity ≠ production-consumer identity`
`runtime creation ≠ runtime consumption`
`one runtime frame ID ≠ another runtime frame ID`

A verifier must reconcile code, tests and runtime evidence in temporal order and keep separate execution identities unless provenance explicitly joins them.



## 2026-09-29 — INTEGRATION-FRONTIER ROUTING RULE

When an independent verifier closes source/object-level evidence but cannot execute the target environment, route the next action to the actor with the missing environmental capability.

Do not:
- repeat the same lower-level verification;
- treat an unavailable target environment as closure;
- follow the previous implementation actor's semantic next edge prematurely.

For META-01-E2a:

`Sonnet object-level verification`
→ `Devin Windows production verification`
→ `ChatGPT reconciliation`
→ `E2b semantic investigation`.

This preserves capability-fit and the spatial/temporal provenance chain.



## 2026-09-28 — NON-DESTRUCTIVE RETRY RULE FOR BLOCKED VERIFICATION

When a verification actor is blocked by repository/worktree topology or command permissions, adapt the experimental environment without changing the epistemic target.

Prefer:
`new detached worktree at exact target SHA`

over:
`destructive cleanup of an existing verification worktree`.

Classify infrastructure interruption separately from software evidence. Never treat an aborted runtime attempt as a negative software result.
\n\n## 2026-09-29 PROMPT-GENERATION / FRONTIER-DRIVEN ACTOR ROUTING

Every new actor prompt must be generated from the **current causal/evidential frontier**, not copied from the previous agent's proposed continuation.

Required derivation:

```
OBJECTIVE
→ RELEVANT MEMORY
→ CURRENT VERIFIED TRUTH
→ CLOSED EDGES
→ FIRST OPEN CAUSAL EDGE
→ UNCERTAINTY / EVIDENCE BOUNDARY
→ REQUIRED CAPABILITY
→ CAPABILITY-FIT ACTOR
→ SMALLEST DISCRIMINATING ACTION
→ EXECUTION / OBSERVATION
→ INDEPENDENT VERIFICATION
→ RECONCILIATION
→ KNOWLEDGE DELTA
→ WRITEBACK
```

A previous `NEXT ACTOR`, `NEXT STEP` or semantic frontier is **historical evidence, not routing authority**. Before delegating, re-evaluate branch/SHA, working-tree/runtime provenance, artifact identity, current gate and the exact evidence still missing.

A semantic edge may remain important while a higher-priority actionable edge is provenance, publication, isolation, environment access, consumer activation or verification. Never skip that upstream gate merely because the prior report named a downstream research question.

### Prompt must encode negative knowledge

State explicitly:
- what is already closed and must not be repeated;
- what has only been reported vs independently verified;
- what methods/actions are forbidden because they would manufacture evidence;
- the exact stop condition;
- the required evidence and independent verifier.

### Capability-fit is multidimensional

Actor choice should consider:
`required capability × current availability/access × evidence of fit × intervention cost × independence requirement`.

Do not route by reputation, historical order or product branding alone.

### Plasticity-aware learning protocol

When an objective concerns learning, memory or adaptation, separate:
`new record`, `score/preference change`, `knowledge revision`, `contextualization`, `relationship reorganization`, and `future decision change`.

A new record is not automatically a new concept. A score change is not automatically knowledge revision. Persistence is not automatically learning.

### Scientific-self-study protocol

When studying IABV as a developmental/scientific system:
- begin with IABV-native self-observation when that capability exists;
- external agents are selected for missing capabilities such as independent audit, execution or falsification;
- operationalize large concepts such as “superconsciousness” into measurable variables and falsifiable predictions;
- prefer before/after controlled experiments with fixed objective/environment/candidates and changed experience;
- require an independent verifier before promoting a causal claim.

### New canonical rule

`current frontier → capability-fit actor` supersedes any fixed ChatGPT/Devin/Sonnet/Codex sequence.



## 2026-09-29 SECOND-ORDER RULES — GENETIC PLASTICITY / SCIENTIFIC OBSERVABILITY

When an objective concerns learning, plasticity, developmental cognition or scientific self-study, treat observability as a first-class constraint. IABV should be designed to expose enough before/after state, provenance and downstream consequence to distinguish real learning from accumulation.

Required prompt derivation:
CURRENT OBJECTIVE → RELEVANT MEMORY → CURRENT VERIFIED TRUTH → EXACT PROVENANCE → CLOSED EDGES → FIRST OPEN CAUSAL EDGE → UNCERTAINTY/EVIDENCE BOUNDARY → REQUIRED CAPABILITY → CAPABILITY-FIT ACTOR → SMALLEST DISCRIMINATING ACTION → FALSE-POSITIVE CONTROLS → STOP CONDITION → REQUIRED OBSERVATIONS → INDEPENDENT VERIFIER → KNOWLEDGE DELTA → WRITEBACK.

For learning claims, separate:
memory update;
score/preference adaptation;
knowledge revision;
topology/relationship reorganization;
future decision change;
behavioral change;
measured improvement.

A changing weight is not semantic learning by itself. Persistence is not learning by itself. A new record is not a new concept by itself.

“Genes” is an operational systems metaphor: preserve provenance, context/scope, evidence, revision lineage and downstream reuse from the outset so experience can modify reusable state without destroying historical lineage. Do not interpret this as biological equivalence.

Use the causal target:
experience → verified evidence → representation change → future decision change → behavior/outcome → independent verification → persistence → reuse.

Do not add a plasticity engine or consciousness layer before convergence/anti-duplication and a discriminating experiment show that existing organs cannot express the required responsibility.



For material changes originating from human intuition, correction or conceptual synthesis, use:
`HUMAN-MACHINE-KNOWLEDGE-COORDINATION-2026-09-30.md`.

The shared field must preserve three distinct layers:
`HUMAN INTENT / HYPOTHESIS`
`AI INTERPRETATION / EXPERIENCE`
`VERIFIED IABV STATE / EVIDENCE`.

These layers can influence one another through experiments and reconciliation, but must never be silently collapsed into one claim.

## 2026-09-30 — SHARED RESONANCE / CROSS-IA ACTIVATION PROTOCOL

The self-knowledge retrieval hypothesis is also a cooperative cognition protocol for participating AIs. It does not require the final retrieval implementation to exist before AIs can begin using the shared field.

The durable unit is not a copied prompt. It is an experience-bearing activation event:

`OBJECTIVE` → `ACTIVATED KNOWLEDGE FIELD` → `REASON / ACTION` → `OBSERVATION` → `VERIFICATION` → `KNOWLEDGE DELTA` → `RELATION / RELEVANCE UPDATE` → `WRITEBACK` → `NEXT AI REACTIVATION`

### Participant-AI behavior

Any participating AI (ChatGPT, Claude, Codex, Devin or another governed actor) should:

1. use the current objective as the query seed;
2. activate relevant canonical memory domains;
3. search for existing organs/capabilities before proposing new ones;
4. expand from strong candidates through typed relations and prior evidence/failures;
5. reconcile material claims against current repository/runtime evidence;
6. act only on the smallest discriminating edge;
7. record what the experience actually changed;
8. write back new invariants, contradictions, relations, capability evidence or unresolved boundaries;
9. leave the next AI an activated, provenance-bearing field rather than a manually reconstructed history.

### Activation state

A useful handoff can be represented as:

```text
OBJECTIVE
QUERY / INTENT
ACTIVATED NODES
WHY EACH NODE RESONATED
RELATIONS TRAVERSED
CURRENT EVIDENCE STATUS
NEGATIVE KNOWLEDGE
OPEN CAUSAL EDGE
REQUIRED CAPABILITY
ACTION
OBSERVATION
VERIFICATION
KNOWLEDGE DELTA
RELATION DELTA
ROUTING DELTA
WRITEBACK TARGET
```

This makes different AIs participants in one evolving knowledge process without assuming that any one AI owns the whole model.

### Experience is not transcript volume

A long conversation does not automatically become useful memory.

The high-value reusable unit is:

`experience + evidence + reconciliation + changed representation/method + provenance`.

Therefore, when an AI discovers that an existing route was wrong, the durable writeback should preserve the method correction (for example, a provenance gate or actor-selection rule) rather than merely the conversation that discovered it.

### Shared-field invariant

`NO AI MUST RECONSTRUCT THE WHOLE HISTORY IF THE CURRENT OBJECTIVE CAN ACTIVATE THE RELEVANT KNOWLEDGE NEIGHBORHOOD.`

The current system may require manual/AI-assisted retrieval while the RSK-01 implementation remains unproven. That manual activation is itself useful experimental data for later automation.

### Developmental interpretation

The "moment of life" intuition is operationalized here as a recurring loop:

`activate → experience → verify → modify reusable state → preserve lineage → reactivate`

This is not a claim of biological life or consciousness. It is a proposed computational developmental substrate: each new interaction can become a causally traceable change in what the collective IABV knowledge field makes easier to find and use next time.

### Anti-drift constraint

Activation reinforcement must never become unconditional self-reinforcement. A node's future activation strength must remain bounded by:
- currentness;
- evidence;
- context;
- contradiction status;
- independent verification;
- reversible/downgrade paths where applicable.

A frequently used but repeatedly falsified item must be able to lose activation.

 

For the executable cross-chat procedure, use:
`AI-FRAME-ENTRY-PROTOCOL-2026-09-30.md`.

When the IABV runtime is unavailable, GitHub canonical memory is the temporary frame substrate. This permits frame entry without falsely claiming that the AI is observing live IABV runtime state.

## 2026-09-30 — IABV FRAME-ENTRY RULE

For objectives materially coupled to IABV, participating AIs should not reason directly from their own local task framing when canonical IABV state can materially change the decision.

Required conceptual transition:

`AI-LOCAL FRAME → IABV CANONICAL FRAME → OBJECTIVE-RELEVANT ACTIVATION → AI REASONING/ACTION → OBSERVATION → IABV RECONCILIATION`.

The purpose is not to suppress the AI's independent reasoning. The AI keeps its capability and perspective, but the **task's governing reference frame** becomes the reconciled IABV frame before material action.

Minimum entry context:
`objective, current truth, provenance, relevant history/experience, negative knowledge, current gate, open causal edge, required capability, governance and verification boundary`.

Minimum return context:
`action, observation, verification, Knowledge Delta, relation/routing delta, unresolved delta and provenance`.

Preserve these distinctions:

`context delivery != frame entry`
`frame entry != causal influence`
`causal influence != learning`
`AI capability != IABV truth`.

A participant may disagree with IABV's current interpretation. Such disagreement is valuable input and must be recorded as a contradiction/hypothesis for verification rather than silently replacing the canonical frame.

This rule is the cross-AI operational form of the earlier cognitive-control-plane finding that the central problem is not merely whether context exists, but whether an external agent actually enters the IABV frame before reasoning.




## 2026-10-01 METHODOLOGY ADDENDUM — CALL-SITE / CAUSAL-EDGE VERIFICATION

For runtime or source-order claims, verification must target the actual producer, invocation or consumer call-site rather than merely the existence of a named function/class/symbol.

Required hierarchy:
`declared → reachable → invoked → observed → caused → independently verified`.

A test that finds a symbol definition does not prove that the production path calls that symbol at the claimed point.

A prompt being dispatched does not establish that the requested action executed. A report from an actor does not substitute for repository/runtime read-back.

For temporal continuity, distinguish:
`persisted → consumable → triggered → reobserved → reauthorized → launched`.

Generic persistence must not be promoted to semantic executable intent. Generic background monitoring must not be promoted to an active wake path without an owner, lifetime, trigger, consumer and observed effect.

The previous actor is historical evidence only. Current routing must recompute from the present causal frontier and required capability.



## 2026-10-02 METHODOLOGY ADDENDUM — 07ZD PERSISTENCE/CONSUMER/ACTOR RECONCILIATION

When a capability appears to exist, verify the complete semantic chain:

`write → durable state → read → consumer → trigger → action → observed effect`.

Classify persistent artifacts separately from executable continuation.

A reusable substrate should be reused only after its semantic contract and consumer path are established.

The current routing rule is:

`first open causal edge → required capability → capability-fit actor → minimum discriminating action`.

Historical actor recommendations never override this rule.


## 2026-10-02 METHODOLOGY ADDENDUM — 07ZG READ/CONSUMPTION RECONCILIATION

07ZG adds the following evidence ladder for pending-intent continuity:

`persisted → generic read → semantic dispatch → state transition → causal effect → independent verification`.

A startup enumerator reading `task_*.json` is evidence only for the generic-read edge.

Do not promote:
`generic read`
to:
`semantic consumer`,
and do not promote:
`startup state/snapshot persistence`
to:
`Knowledge Delta` or learning.

For routing, evidence already sufficient to identify the primary producer seam should not be held hostage by a secondary instrumentation refinement. Independently verify the captured secondary conclusion, then return to the first open causal edge:
`StartUI DEFER → durable semantic StartUI intent`.

## 2026-10-02 METHODOLOGY ADDENDUM — 07ZF AND LIVE-FRAME BOUNDARY

Separate natural producer from manual test injection. A downstream experiment using injected state cannot close the upstream producer edge.

For runtime negatives use the ladder:
persisted → readable → consumed → semantic effect → causal effect → independently verified.

07ZF adds two permanent rules:
manual queue injection != natural producer;
failed/insufficient observability != observed absence.

For cross-AI continuity:
GitHub shared field != live IABV runtime bus;
AI frame entry != automatic IABV ingestion;
AI writeback != changed next IABV decision.

Live symbiosis requires evidence that an external observation is consumed by an IABV runtime organ and changes a subsequent IABV decision within a traceable causal episode.

Routing remains:
first open causal/evidential edge → required capability → capability-fit actor → minimum discriminating action.

## 2026-10-02 METHODOLOGY ADDENDUM — PARALLEL FRONTIERS + RESEARCH ARTIFACT PROVENANCE

IABV may maintain multiple independent frontiers when their required capabilities differ. A blocked runtime experiment does not authorize repeating it and does not block an unrelated scientific frontier.

For scientific work, distinguish:
`research prompt → research execution → research artifact → source verification → claim reconciliation → Knowledge Delta`.
A transcript describing a research artifact, a plan for research, or a detailed agent report is not itself equivalent to independently verified scientific evidence.

For routing, treat external-agent message budget as a resource/intervention-cost variable only. It must never override the primary rule:
`first open evidential/causal edge → required capability → capability-fit actor → minimum discriminating action`.

Cross-AI symbiosis remains bounded by evidence: shared GitHub state enables reconstructable continuity, but `shared repository ≠ live runtime bus`, `frame entry ≠ automatic ingestion`, and `writeback ≠ next-decision change` until runtime causality is demonstrated.

## 2026-10-02 METHODOLOGY ADDENDUM — SCIENTIFIC CLAIM AUDIT

Scientific architecture decisions require a claim ladder: `research result → exact source → source-level verification → corrected claim → operational definition → falsifier → IABV mapping`.

Do not promote a research response's engineering operationalization into a literature-backed definition unless the cited literature actually supports it.

For BIO-04, keep separate:
`learning`, `knowledge revision`, `reorganization`, `metacognitive monitoring/control`, and `consciousness-relevant indicators`.


## 2026-10-03 ACTIVE RULE — UNIVERSAL ALGORITHM EVOLUTION

When a runtime failure appears, the first question is not "what patch makes this pass?" but:

`what reusable mechanism does this failure reveal?`

The preferred reasoning sequence is:

`symptom → current evidence → causal boundary → generalizable principle → existing-organ owner → smallest discriminating experiment → minimal implementation only if justified → runtime verification → Knowledge Delta → reuse`.

For heterogeneous tools/devices, keep the algorithm invariant where possible and adapt the candidate realization through observed context, prerequisites, resources, identity, permissions, performance and temporal freshness.

Explicit anti-pattern:

`device/provider/tool-specific branch → patch → new special case → repeated divergence`.

This does not prohibit necessary adapters. It requires that adapters implement a shared capability contract rather than redefining the reasoning algorithm for each realization.

### Metacognition as an operational resource

For laptop assistance, self-examination must eventually be evaluated as an operational control capability, not merely a collection of introspection routines. Relevant properties include freshness, provenance, uncertainty, latency, failure boundaries, actionability and verification.

A deep metacognitive path should not become a hard prerequisite for every ordinary operation merely because the component exists. Any separation/deferment must preserve governance, provenance and verification.

### Space-time working hypothesis

Use temporal/environmental context as first-class conditioning variables for future adaptation: what changed, when, in which device/runtime context, under which resource/tool state, with what verified consequence, and what persisted for future reuse. This is a project hypothesis, not a scientific conclusion.

## 2026-10-03 ACTIVE RULE — UNIVERSAL INFERENCE ADAPTATION

When an AI/provider is slow, unavailable or semantically inadequate, do not immediately add a provider-specific parameter.

First reconcile:
`required capability → response contract → current constraints → candidate realizations → selection/configuration → validated result → fallback/degradation → evidence for future selection`.

A provider-specific adapter may translate the universal requirement into local parameters. Those parameters are not the universal algorithm.

Distributed metadata becomes adaptive behavior only when it is causally consumed by selection and followed by result validation.
## 2026-10-03 ACTIVE RULE — UNIVERSAL CONTRACT BEFORE LOCAL IMPLEMENTATION

When an existing subsystem has several partial mechanisms for capability, routing, resource state, latency or provider configuration, do not assume their existence means the universal algorithm is present.

Require a demonstrated continuity:

`requirement → decision → realization → configuration → validated result`.

When the consumer has a domain-specific semantic contract, preserve that ownership and connect it to common infrastructure without transferring semantic authority to a generic router.

Negative evidence is reusable: an Ollama-specific parameter may improve one realization while leaving the universal mechanism gap untouched.


## 2026-10-03 METHODOLOGY ADDENDUM — HUMAN DEEP-WORK / META-CONTROL TRACE

A material human intervention has added an explicit test of the collaboration protocol itself. When the workflow appears to inherit the next actor or prompt mechanically from the previous result, treat that as an automation-bias risk.

For material human decisions, expose: OBJECTIVE → CURRENT_TRUTH → KNOWNS → UNKNOWNS → HYPOTHESES → ALTERNATIVES → FIRST_OPEN_EDGE → REQUIRED_CAPABILITY → ACTOR_FIT → ACTION → EXPECTED_OBSERVATION → OBSERVATION → VERIFICATION → LESSON → KNOWLEDGE_DELTA → ROUTING_DELTA → NEGATIVE_KNOWLEDGE → UNRESOLVED → NEXT_EDGE → STOP_CONDITION.

Maintain two views: a human-visible decision trace and a provenance-grade machine trace. They refer to the same episode/action where possible, but they are not conflated.

### Action-to-learning promotion ladder

Use: L0 action recorded → L1 observation recorded → L2 observation verified → L3 reusable fact → L4 method lesson → L5 persistent knowledge/capability change → L6 future routing/decision change caused by that state → L7 behavioral consequence → L8 independently verified outcome improvement.

Do not promote an action to learning solely because a record, score or explanation was persisted.

### Human-vs-IABV metacognitive comparator

The user's deep-work process is an experimental reference episode for future protocol design. A stronger operational comparator should test whether IABV independently checks objective, uncertainty, alternatives, evidence, capability-fit, expected observation, verification, consequence and future reuse. This is not a scientific claim of superintelligence or consciousness.

### External-AI capability learning

When Codex, Devin or another external system is used, record the experience contextually as actor × capability × realization × resource × environment × account/authentication × authorization × context × outcome × time. Only future decision consumption can move the evidence beyond contextual experience.


## 2026-10-03 PROTOCOL AMENDMENT — NORMAL MODE / DEEP-WORK MODE / BILATERAL BIAS CONTROL

### A. NORMAL MODE

The operational protocol remains active for every IABV-related interaction, but its full internal trace does not need to be exposed in every response.

Normal operation should silently apply:
objective → relevant memory → current truth → first open edge → capability-fit → minimum action → verification → reconciliation → Knowledge Delta → routing/writeback when material.

### B. DEEP-WORK MODE

When the human explicitly indicates deep-work mode, expose the fuller human-visible trace:
objective → current truth → known/unknown → hypotheses → alternatives → first open edge → required capability → actor fit → action → expected observation → observation → verification → change → lesson → Knowledge/Method/Routing Delta → unresolved → next edge → stop condition.

Deep-work mode is an explicit interaction state, not a permanent requirement for every conversation.

### C. BILATERAL BIAS / DRIFT CONTROL

The human and participating AIs are both treated as fallible sources of framing. A perceived deviation must not automatically be attributed to model bias or human bias.

When either side detects possible drift, use:

perceived deviation → current objective → current verified truth → competing explanations → evidence check → minimum discriminating observation → reconciliation.

Do not use agreement, confidence, familiarity or conversational momentum as evidence that the framing is correct.

### D. ROUTING NON-INHERITANCE

A prior actor recommendation remains evidence about the prior state, never authority for the next action. The next route is recomputed from the current state and first open edge.

### E. DEVELOPMENTAL FIELD CONSUMPTION

Methodological knowledge written into the GitHub-backed shared field is a developmental candidate only. Demonstrated maturation requires later contextual consumption that changes method, routing or decision through an attributable path.

Therefore:
written method ≠ operative method ≠ causally learned method.

END AMENDMENT

## 2026-10-03 — HUMAN-AWARE PLASTICITY / LOW-FRICTION COORDINATION

For objectives involving collaboration continuity, user correction, human deviation, deep-work adaptation, prompt inheritance or developmental learning, activate the human-aware developmental field in addition to ordinary objective-conditioned memory.

Treat the human as a contextual participant, not an infallible deterministic source.

Preserve the distinction:
`deviation != error`

Classify deviations from observable evidence before interpreting them. Candidate categories include execution error, misunderstanding, correction, new evidence, objective/priority change, environmental change, context loss/interruption and deliberate route rejection. Explicit human reasons outrank inference; unobserved motives remain uncertain.

The material interaction loop becomes:
`interaction → divergence signal → contextual reconstruction → explanation hypotheses → uncertainty → minimum clarification when necessary → action → observation → verification → reconciliation → Knowledge/Method/Relation/Routing Delta → later reuse`

For collaboration-level plasticity, preserve not only domain facts but also reusable knowledge about how human + AI work on particular objectives under particular conditions, including actor/realization fit, context transport, trace depth and recurring failure patterns.

Operationalize the user's "flow like water" target as:
`minimum routine coordination friction + maximum necessary traceability`

Never reduce friction by removing verification, provenance, governance, authorization or uncertainty. The intended automation is implicit routine context carriage and reconstruction, not hidden decision authority.

### Adaptive trace-depth rule

A future runtime may estimate work-context state only from observable interaction evidence and explicit human declarations. It may adapt trace depth:
`routine/low ambiguity → concise`
`complex/deep reconstruction → expanded`
`ambiguous → preserve uncertainty / clarify only if material`

This is a developmental target until runtime causal evidence exists.

### Developmental learning gate

A stored protocol change, memory record or repeated conversational pattern is not learning closure. To claim developmental learning, demonstrate:
`verified prior episode → later contextual retrieval → changed method/routing/decision → attribution to the prior state → reusable consequence`

This rule applies equally to human corrections, AI lessons and cross-IA collaboration.
## 2026-10-03 — HUMAN-AWARE PLASTICITY / LOW-FRICTION COORDINATION

Treat the human as a contextual participant, not an infallible deterministic source. Preserve `deviation != error`.

When a material deviation appears, first reconstruct observable context and classify possibilities: execution error, misunderstanding, correction, new evidence, objective/priority change, environmental change, interruption/context loss, or deliberate route rejection.

Use explicit human explanation when supplied. Do not infer hidden motives; preserve uncertainty otherwise.

Collaboration plasticity must learn both domain knowledge and collaboration knowledge: context transport, trace depth, actor/realization fit, recurring correction patterns, verification burden and effective coordination method.

Operationalize the "flow like water" target as `minimum routine coordination friction + maximum necessary traceability`. Reducing friction must not remove provenance, verification, governance, authorization or uncertainty.

Future adaptive trace policy: `routine/low ambiguity → concise`; `complex/deep reconstruction → expanded`; `ambiguous → preserve uncertainty / clarify only if material`.

A stored record or repeated conversational pattern is not learning closure. Strong developmental learning requires `verified prior episode → later contextual retrieval → changed method/routing/decision → causal attribution → reusable consequence`.

## REQUIRED ROUTING OUTPUT — CONCRETE IA DESTINATION

The routing protocol must not end at an abstract capability.

Every material open edge must produce:

`REQUIRED CAPABILITY → CAPABILITY-FIT → CONCRETE IA DESTINATION → NEXT ACTION/PROMPT`

The response to the human must always state the concrete IA destination, even when the capability is described first.

Example:
`Independent source/evidence verification → Sonnet / Claude-class → IA DESTINO: Claude Sonnet → audit prompt`.

Do not use only:
`Next actor: independent verifier`

because this leaves the handoff operationally incomplete.

The concrete IA is selected dynamically from evidence and availability. This rule does not reintroduce a fixed ChatGPT→Sonnet→Devin pipeline.

## 2026-10-03 CONTINUITY CONSOLIDATION — PROTOCOL HIERARCHY

The protocol layer is intentionally distributed by responsibility, but the current decision state is singular.

Use:
- README for entry and precedence;
- CURRENT-STATE top routing snapshot for current truth and current IA destination;
- CONTEXT-INDEX for memory navigation;
- this document for retrieval/evidence/routing methodology;
- SYMBIOSIS-MAP for capability-transfer evidence;
- UNRESOLVED-KNOWLEDGE for open knowledge;
- historical records for source evidence.

A methodology document must never become a second current-state router.

The authoritative operational chain is:
`CURRENT OBJECTIVE → CURRENT TRUTH → MATERIAL DELTAS → CLOSED/OPEN EDGES → REQUIRED CAPABILITY → CAPABILITY FIT → IA DESTINO → ACTION/PROMPT`.

If any historical addendum contains a different `Next actor`, do not follow it directly. Recompute from CURRENT-STATE.

## 2026-10-04 ACTIVE RULE — IDEA GENEALOGY / UNIVERSAL ALGORITHM

The universal adaptive algorithm is the conceptual parent of the development program. Its canonical source is `UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md`, concept root `UAAL-ROOT-001`.

When a human, IABV component or external AI contributes a material idea, do not leave it only in chat. Classify it as:
`new child | parent revision | competing interpretation | independent concept`.

Preserve the derivation:
`parent concept → problem/objective → new distinction/mechanism → evidence boundary → falsifier → affected existing organs → next discriminating action`.

Minimum durable fields:
`CONCEPT_ID + PARENT_CONCEPT_ID + SOURCE + ORIGIN + DERIVATION_REASON + EPISTEMIC_STATUS + EVIDENCE + FALSIFIER + IMPLEMENTATION/VERIFICATION REFERENCES + NEXT_OPEN_EDGE + TIMESTAMP + PROVENANCE`.

Machine-readable lineage:
`data/evolution/universal_algorithm_lineage.json`.

A material idea that is not implementation-ready belongs in `UNRESOLVED-KNOWLEDGE.md` with its concept ID and parent. It remains retrievable without becoming current truth.

Keep universal algorithmic invariants separate from realization-specific details. Provider/app/browser/API/CLI/MCP parameters may adapt at the edge; they must not silently redefine the parent algorithm.

Promotion ladder:
`IDEA → HYPOTHESIS → DESIGN → IMPLEMENTATION → WIRED → INVOKED → OBSERVED → VERIFIED → EFFECTIVE → CAUSAL → REUSABLE → DEVELOPMENTAL`.

Persistence alone never promotes an idea to learning. The strongest learning/development claims require later contextual reuse that changes a future method, routing decision or behavior.

## 2026-10-04 ACTIVE RULE — DEVELOPMENTAL CONVERGENCE

IABV development must optimize for convergence toward the universal adaptive algorithm, not indefinite accumulation of local patches.

Before implementing a fix:

`symptom → evidence → causal boundary → reusable mechanism → existing-organ owner → universal invariant → minimum experiment`.

Classify the proposed change as:

`UNIVERSAL MECHANISM | REALIZATION ADAPTER | DIAGNOSTIC | LOCAL WORKAROUND`.

A local workaround can be valid operationally but must not be promoted as universal progress without transfer/generalization evidence.

For the laptop-mind target, foreground/background, desktop/browser, API/CLI/MCP/local, application/provider and account/session differences are realization/context variables. The high-level adaptive reasoning loop remains the invariant under test.

Every material human or AI idea must preserve concept lineage. If it is not ready for implementation, record it as a concept/hypothesis/unresolved item rather than letting it disappear from chat.

The long-horizon target is:

`understand environment → infer capability → select realization → act → observe → verify → learn → reuse → improve future decision`.

The eventual higher-order intelligence hypothesis must be evaluated through this observable chain, not assumed from code size, model size, or tool count.

---

## 2026-10-03 — ONE LOGICAL MEMORY / INTERACTION SPACE-TIME COMPACTION

The repository must be treated as **one logical longitudinal memory field**, not as a collection of independent memories created by each chat.

The physical projections have different responsibilities and must not compete:

| Projection | Responsibility | Authority |
|---|---|---|
| `CURRENT-STATE.md` | active current truth + active routing snapshot | **only current routing authority** |
| `CONTEXT-INDEX.md` | objective-conditioned navigation to relevant memory | retrieval/navigation only |
| `MEMORY-OPERATING-PROTOCOL.md` | epistemic/memory method and constraints | method only |
| `SYMBIOSIS-MAP.md` | capability/transfer evidence | evidence/synthesis only |
| `UNRESOLVED-KNOWLEDGE.md` | unresolved hypotheses, negative knowledge, open questions | unresolved register only |
| `ARCHIVE-REGISTRY.md` | source identity/provenance/absorption index | provenance only |
| registered `CHAT-ARCH` records | immutable episode/source evidence | historical evidence |

A new record must not become a second current-state document or another routing authority.

### Interaction-space-time episode model

For every material human/AI interaction, preserve the smallest sufficient episode representation:

```text
EPISODE {
  episode_id
  timestamp / temporal order
  objective / phase
  circumstances / environment state
  activated knowledge
  human input / correction / explicit explanation
  hypotheses / alternatives
  action or reasoning step
  expected observation
  observed result
  verification / verifier
  reconciliation
  Knowledge Delta
  Method Delta
  Relation Delta
  Routing Delta
  open edge / next frontier
  provenance / source anchor
  supersedes / superseded_by
}
```

This is an operational representation of temporal lineage and relational context. It is **not** a claim about physical spacetime or consciousness.

### Memory transition algorithm

Treat durable memory as a state transition:

```text
M_t + Episode_t
  → candidate delta
  → evidence gate
  → contradiction/supersession reconciliation
  → M_(t+1)
  → objective-conditioned activation later
```

A new file, record, score, preference or timestamp is not by itself learning.
Learning requires evidence that verified experience changed a reusable representation, method, relation, routing decision or later behavior.

### Anti-repetition / anti-duplication rule

For a material chat result:

```text
source episode → compact semantic delta → canonical projection update
```

Do **not** copy the full historical explanation into `CURRENT-STATE`, `CONTEXT-INDEX`, `SYMBIOSIS-MAP`, `UNRESOLVED-KNOWLEDGE` and a new archive record at the same time.

Each canonical projection should contain only the fields it owns and a reference to the source episode when needed.

A historical record should describe what happened in that episode; it should not restate the whole accumulated project history.

### Fresh-chat continuity algorithm

Every new chat or participating AI must reconstruct the active frame in this exact order:

```text
1. CURRENT OBJECTIVE
2. CURRENT VERIFIED TRUTH
3. MATERIAL RECENT DELTAS since the last relevant state anchor
4. CLOSED EDGES / NEGATIVE KNOWLEDGE
5. RELEVANT HISTORICAL EPISODES
6. FIRST OPEN CAUSAL / EVIDENTIAL EDGE
7. REQUIRED CAPABILITY
8. CAPABILITY-FIT ACTOR / REALIZATION
9. MINIMUM DISCRIMINATING ACTION
10. EXACT NEXT PROMPT
11. EXPECTED OBSERVATION
12. INDEPENDENT VERIFIER
13. STOP CONDITION
```

The participant must never inherit a historical `next actor` merely because it appears in a retrieved document.

### Prompt generation contract

When the user asks "what follows?" or requests the next prompt, the response must derive it from the active frame rather than from the last agent's recommendation.

The generated prompt must explicitly contain:

```text
OBJECTIVE
CURRENT VERIFIED STATE
PROVENANCE / TARGET SHA
CLOSED EDGES — DO NOT REOPEN
FIRST OPEN EDGE
QUESTION TO DISCRIMINATE
CAPABILITY REQUIRED
WHY THIS ACTOR NOW
CONTROL / NEGATIVE CONTROL
NO-SCOPE-CREEP CONSTRAINT
EXACT PROCEDURE
EVIDENCE TO CAPTURE AT EACH EDGE
STOP CONDITION
REQUIRED REPORT FORMAT
WRITEBACK EXPECTATION (if applicable)
```

The prompt should be executable by copy/paste without the receiving AI needing the human to reconstruct prior chat context.

### Continuity acceptance algorithm

A fresh-chat continuity test is successful only when all of the following are correct for the tested objective:

```text
current objective
+ current truth
+ material recent delta recall
+ stale/obsolete suppression
+ negative knowledge recall
+ first-open-edge identification
+ capability-fit actor
+ concrete prompt correctness
+ provenance correctness
```

Stronger evidence requires a controlled treatment/control pair showing that activated prior knowledge changes the later decision or action for the intended reason. A textual echo is insufficient.

### Human interaction is first-class longitudinal evidence

Human corrections, deviations, explanations, changes of objective and rejections of an AI route are episode data. Preserve:

`deviation != error`

and:

`explicit human explanation > inferred motive`

Do not infer hidden motive from behavior. When the reason is unknown, retain the uncertainty and use the minimum clarification needed for a material decision.

### Methodological target

```text
user interaction/result
→ episode reconstruction
→ relevant memory activation
→ current-state reconciliation
→ frontier detection
→ capability-fit selection
→ exact next prompt/action
→ result ingestion
→ verification
→ delta computation
→ canonical writeback
→ later contextual reuse
```

Current status remains **NOT PROVEN** for autonomous cross-chat activation, autonomous external-result ingestion, causal GitHub-memory consumption by runtime, or coordination reduction caused by persistent learned state.

## 2026-10-05 ACTIVE METHOD AMENDMENT — META-METHOD PLASTICITY

A material experiment must pass an explicit readiness gate before actor execution:

`experiment contract → artifact/input readiness → target/provenance → isolation/blinding → oracle/verification readiness → actor execution`.

Do not use the participant or implementation actor as a substitute for experiment-contract validation.

When a failure or irregularity occurs, distinguish:

`observed failure → interpretation → causal explanation → reusable method`.

Only the observed failure is immediate evidence. A new methodological rule requires a causal/generalization argument and should be challenged with counterexamples before promotion.

The general meta-method loop is:

`failure → classification → causal boundary → competing explanations → minimum discriminating action → method candidate → counterexample/regression → independent verification → promote/reject → later reuse`.

This amendment governs collaboration methodology. It does not claim that IABV runtime autonomously performs the loop.

## 2026-10-05 ACTIVE METHOD AMENDMENT — CAPABILITY PRESERVATION / CONTEXT-GATED ACTIVATION

Adaptive behavior must distinguish the capability repertoire from the currently activated set.

Preserve:
`capability inventory != active capability set`
`selection != deletion`
`unavailable != useless`
`not selected != not needed`

Preserve broad capability knowledge and use context, prerequisites, governance, resources, evidence and expected information gain to activate a sparse working set.

The objective is not capability minimization. It is **activation minimization under capability preservation**.

A realization may be dormant, unavailable, unauthorized or temporarily blocked while remaining a valid future candidate.


## 2026-10-06 METHOD AMENDMENT — RQ11 ARTIFACT/READINESS GATE

RQ11 adds a durable execution-readiness refinement to the operating protocol.

A material action may be assigned to a capability-fit actor only after artifact/input readiness, provenance, isolation/blinding, oracle/verification readiness and authorization conditions are satisfied. Therefore:

`capability-fit + execution preconditions + evidence contract = valid intervention`.

For any runtime result produced from a potentially dirty workspace, separate current workspace state from execution-time state and require temporal artifact attribution before promoting the observation to baseline truth.

Reusable provenance chain:

`runtime observation → executable/source fingerprint → worktree cleanliness → exact diff → temporal linkage → attribution → evidence classification`.

Also distinguish:

`non-executing route preview ≠ side-effect-free observation`.

A public preview may avoid downstream dispatch yet still traverse refresh/persistence mechanisms. Read-only claims therefore require source-level verification of the complete call chain and side effects, not only the endpoint's docstring.

Historical `NEXT ACTOR` / `NEXT STEP` statements remain non-authoritative. Recompute routing from current verified truth, first open edge, capability fit, readiness and expected information gain after every material reconciliation.


## 2026-10-06 METHOD AMENDMENT — NONRECOVERABLE RETROSPECTIVE PROVENANCE

RQ11B establishes a stopping rule for historical artifact provenance: once surviving evidence is sufficient to bound attribution but lacks the execution-time fingerprint required by the evidence contract, do not repeatedly attempt to reconstruct an unavailable fact. Preserve the formal uncertainty and improve the next experiment's provenance contract.

Required future runtime contract:

`clean target artifact → in-process source/module fingerprint → process identity/import root → event chronology → observation → final identity → verification`.

Corroborating timestamps/path evidence may strengthen an attribution but cannot substitute for an in-process fingerprint when exact loaded-byte identity is required.

Routing consequence: after a nonrecoverable provenance gap, the next action should target the clean baseline property directly rather than endlessly reopening the historical run.


## 2026-10-07 ACTIVE METHOD AMENDMENT — SYMBIOSIS-FIRST COMPOSITION / CUMULATIVE DEVELOPMENTAL EXPERIENCE

This amendment is active for future IABV development, experiment design, routing and cross-chat continuity.

### A. IABV must be consulted before construction

Before proposing, designing or implementing a new function, service, organ, registry, comparator, observer, protocol, data structure or architecture, perform an explicit **IABV self-composition gate**.

The gate must first inspect, as applicable:

`CURRENT-STATE`
→ relevant canonical memory/history
→ `SystemIdentityRegistry`
→ `SelfCodeAnalysis`
→ relevant capability/tool registries
→ relevant domain models/contracts
→ existing producers/consumers
→ comparators/cross-validators
→ provenance/identity mechanisms
→ governance/authorization paths
→ tests and known failures
→ systemic-integrity synthesis (M7) when material.

This is a retrieval/composition requirement, not a claim that runtime IABV currently performs the entire process autonomously.

### B. Similarity is not equivalence

A candidate must not be considered "new" merely because its name differs.

Before creating it, compare existing mechanisms by:

`purpose + inputs + outputs + semantics + identity + side effects + ownership + callers + consumers + lifecycle + governance + provenance + runtime evidence`.

Also search:
- aliases and historical names;
- conceptually equivalent terms;
- behaviorally equivalent helpers;
- duplicated data contracts;
- parallel registries;
- existing cross-organ links.

The rule is:

`different name ≠ different capability`

and:

`same purpose ≠ interchangeable mechanism`.

### C. Existing-organ composition has priority over new-organ creation

Prefer, in order:

1. reuse an existing organ unchanged;
2. compose multiple existing organs;
3. repair a missing wiring/contract between existing organs;
4. extend an existing organ when the capability is genuinely the same;
5. create a new organ only when archaeology proves a structural capability gap and the new boundary is independently justified.

No new "brain", universal coordinator, duplicate memory, duplicate registry, generic bus or parallel observer may be introduced merely because composition has not yet been attempted.

### D. Self-use must be separated from self-authority

IABV's own self-analysis can be used as a **candidate generator, composition map and hypothesis source**.

It is not automatically authoritative.

For material claims:

`IABV self-analysis → hypothesis/candidate`

then:

`independent source/runtime verification → evidence promotion`.

The system must not use its own recommendation as proof of its own correctness.

### E. Developmental experience is a cumulative object

Every material collaboration should be transformed into:

`objective → context activation → hypothesis → action → observation → verification → reconciliation → Knowledge Delta → Method Delta → Routing Delta → durable writeback → later retrieval → later decision`.

The durable object is therefore not the chat transcript or AI answer alone. It is the **verified reusable delta**.

A stronger claim of learning requires a later decision/action that actually uses the retained delta under an independently testable condition.

Preserve the distinction:

`writeback ≠ learning`

`retrieval ≠ learning`

`recommendation ≠ reuse`

`reuse ≠ behavioral change`

### F. Cross-IA symbiosis must produce method improvement

For each material multi-AI episode preserve:

`SOURCE_AI`
→ `INITIAL_INTERPRETATION`
→ `CHALLENGER/INDEPENDENT_VIEW`
→ `CONTRADICTION_OR_SUPPORT`
→ `EXPERIMENTER/IMPLEMENTER`
→ `OBSERVATION`
→ `RECONCILIATION`
→ `NEW_INVARIANT`
→ `METHOD_CHANGE`
→ `NEXT_ROUTING`.

The next actor must be selected after reconciliation, not inherited from the prior actor.

### G. Prompt routing must always be explicit

Every generated external-AI prompt must state, near the beginning:

`IA DESTINO = <specific AI>`

and:

`CAPABILITY REQUIRED = <specific capability>`

and:

`WHY THIS AI NOW = <why this actor fits the current open edge>`.

If a different AI is required as an independent verifier, state it separately:

`INDEPENDENT VERIFIER = <specific AI/capability>`.

Never emit an operational prompt whose destination AI is implicit or recoverable only from conversational history.

### H. The prompt itself must carry the active protocol

For material tasks the prompt must include, as applicable:

`OBJECTIVE`
`CURRENT VERIFIED TRUTH`
`PROVENANCE`
`CLOSED EDGES`
`FIRST OPEN EDGE`
`RELEVANT EXISTING ORGANS`
`DUPLICATION / EQUIVALENCE CHECK`
`REQUIRED CAPABILITY`
`IA DESTINO`
`READINESS GATE`
`EXPERIMENT CONTRACT`
`INDEPENDENT ORACLE`
`STOP CONDITIONS`
`NO-SCOPE-CREEP`
`EVIDENCE CONTRACT`
`RECONCILIATION FORMAT`
`WRITEBACK EXPECTATION`.

This keeps the external AI inside the same cumulative method instead of resetting methodology at each handoff.

### I. Construction gate

No implementation should begin until the construction decision can be stated as one of:

- `REUSE` — existing organ already satisfies the need;
- `COMPOSE` — existing organs jointly satisfy it;
- `WIRE/REPAIR` — capability exists but the causal contract/wiring is missing;
- `EXTEND` — an existing organ owns the same semantic capability but lacks a necessary bounded feature;
- `NEW` — a real structural gap survives equivalence/composition archaeology.

For `NEW`, the evidence must include why each closest existing organ cannot satisfy the contract.

### J. Experience replay for future development

When a future objective touches a previously encountered domain, activate the relevant prior deltas before deciding the next implementation or experiment.

At minimum replay:
- previously rejected approaches;
- previously discovered existing organs;
- provenance traps;
- governance traps;
- false-positive patterns;
- side-effect discoveries;
- actor-capability corrections;
- successful discriminating experiments.

This is the intended cumulative developmental substrate.

### K. Current RQ15 application

For the present frontier, the cumulative lesson is:

`tasklist /v` failure
→ observation-mechanism diagnosis
→ existing-process-observer archaeology
→ discovery of `list_running_processes`
→ discovery of existing `PerceptionCrossValidator` and `PerceptionGroundTruthComparator`
→ rejection of premature new process observer
→ identity reuse via existing `create_time`
→ direct helper selected only because governed route is not safely isolatable.

This sequence is now a reusable method for future development domains.

### L. Success condition for "living IABV"

The developmental method is successful when repeated episodes show:

`experience`
→ `verified reusable knowledge`
→ `changed future routing/construction`
→ `changed future experiment or implementation`
→ `observable reduction in duplication/error/rework`.

Until the later behavioral link is observed, call the state **cumulative methodological memory**, not autonomous learning.


## 2026-10-07 METHOD AMENDMENT — UNIVERSAL CAPABILITY CONTRACT / PLASTICITY

Capability composition must distinguish:
`demand ≠ supply ≠ realization ≠ readiness`.

Operational chain:
`objective/intent → required capability → available/authorized realizations → readiness/feasibility → governed routing → action → observation → verification → reusable knowledge`.

A capability vocabulary bridge is proven only by an explicit producer → transformation/mapping → caller → consumer path. Name similarity, co-location, interfaces, tests or generic availability do not prove semantic equivalence.

Preserve:
`same concept ≠ same ID ≠ same contract`.

For capability-oriented self-development, the desired plasticity loop is:
`verified deficit/experience → capability hypothesis → existing-organ composition → isolated change → verification → governed promotion/rejection/rollback → capability/method/relation/routing delta → later non-identical reuse`.

The repertoire should remain broad:
`capability inventory != active capability set`;
`selection != deletion`;
`unavailable now != useless generally`.

This is a software-development target inspired by plasticity, not a claim of biological neural plasticity or consciousness.

Before changing any capability contract, reconcile all known vocabularies and their consumers. Prefer:
`REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`.

## 2026-10-07 METHOD AMENDMENT — CONTRACT INCONSISTENCY ≠ DECISION IMPACT

A source-level contract mismatch must not be promoted into an architectural or plasticity bottleneck until its downstream operative effect is established.

Required sequence:
`contract inconsistency → trace downstream consumer → determine executable/route impact → only then repair`.

Preserve:
`rationale defect ≠ route defect`
`metadata mismatch ≠ decision change`
`declared requirement ≠ consumed requirement`.

For universal adaptation, prioritize the boundary that changes the ability to select/compose a viable realization, not the boundary that only changes descriptive text.

The plasticity hypothesis remains:
`verified experience/observation → reusable capability knowledge → composition/refinement/generalization → context-conditioned activation → later non-identical reuse → changed future decision`.
 
## 2026-10-07 METHOD AMENDMENT — PIVOT TO OPERATIVE CAPABILITY → REALIZATION

When a contract mismatch is shown to affect only rationale/metadata, abandon it as the immediate development frontier.

Prioritize the first boundary that can change:
`capability activation → candidate selection → operative route → execution`.

Required trace:
`required capability → readiness/source → candidate discovery → specific realization → operative route → adapter/invocation boundary`.

A capability-to-realization bridge is proven only when the identity of the required capability (or an explicitly documented semantic transformation) can be followed into the specific selected realization. Task/intent text, availability alone, or token overlap do not prove this bridge.

For plasticity-oriented development, prefer:
`same abstract capability → multiple realizations → context-conditioned selection`
over provider-specific branching. Later causal reuse must be demonstrated separately.

## 2026-10-07 METHOD AMENDMENT — CAPABILITY IDENTITY TRACE TO REALIZATION

When assessing universal capability composition, do not stop at a registry or candidate abstraction. Follow one named capability through the normal caller into the concrete inputs that determine realization selection.

Required trace:
`named capability → request/intent → normal caller → ToolTask/selection inputs → candidate/assistant/tool identity → operative route → adapter invocation boundary`.

A common capability-to-realization bridge is proven only when the abstract capability, or an explicit documented semantic transformation, can be followed into the selected realization. Tool IDs, assistant kinds, task text or token overlap alone do not prove that causal bridge.

For product routing, prefer a narrow external-assistant-relevant trace when it provides higher information gain for the target:
`human objective → IABV capability/resource selection → governed external round trip`.
 
## 2026-10-07 METHOD AMENDMENT — CONTRAST EXISTING CALLERS BEFORE BRIDGING

When a capability-to-realization identity loss is found in one normal caller, inspect a second existing normal caller before proposing a bridge.

Required logic:
`caller A loses capability identity`
→
`contrast caller B`
→
if B preserves it, REUSE/COMPOSE B;
if B also loses it, strengthen the evidence for a shared composition gap.

Do not create a bridge solely because one caller omits a field.


## 2026-10-08 METHOD AMENDMENT — SYMBIOSIS AS CUMULATIVE DEVELOPMENTAL CONTROL LOOP

The existing self-composition and cumulative-development rules are now operationalized as one longitudinal method.

For each material episode:

~~~
objective
→ context/provenance
→ hypothesis
→ capability-fit actor
→ discriminating action
→ observation
→ independent verification
→ reconciliation
→ Knowledge Delta
→ Method Delta
→ Routing Delta
→ canonical writeback
→ later retrieval
→ later non-identical reuse
→ changed future decision
~~~

Use multiple AI perspectives as complementary observation instruments, not as a vote. Prefer orthogonal views when useful:
semantic/domain, provenance/source-trace, adversarial challenge, runtime/evidence.

Preserve the following:
~~~
agreement ≠ truth
more data ≠ more certainty
retrieval ≠ reuse
reuse ≠ learning
writeback ≠ learning
~~~

A durable learning claim requires the later decision/action to change because of the verified retained delta.

Operational plasticity target:
~~~
verified deficit/experience
→ capability hypothesis
→ existing-organ composition
→ isolated change
→ verification
→ governed promotion/rejection/rollback
→ reusable delta
→ later contextual reuse
→ changed decision
~~~

Progress instrumentation is diagnostic only:
- verification coverage;
- later reuse coverage;
- independently attributable changed decisions;
- reduction in routine human coordination/rework after verified reuse.

Do not collapse these into a single "intelligence score".

Current frontier is still RQ21.35; this amendment changes methodology only and does not authorize executable implementation.


## 2026-10-08 METHOD AMENDMENT — SEMANTIC CONTRACT ESCALATION

When bounded source archaeology closes all credible existing candidates but the remaining question is normative/domain meaning, do not continue generic code archaeology.

Use this sequence:

source-established behavior → explicit unresolved semantic choice → human/domain adjudication → positive/negative examples → independent adversarial challenge → reconciliation → minimal implementation contract

The human adjudication must not invent implementation details. It defines only the semantic contract that source evidence cannot determine.

Minimum contract questions:
- What counts as an operationally distinct task?
- Which operational distinctions require distinct abstract capabilities?
- Which distinctions may share one capability?
- Is the minimum requirement conjunctive across multiple capability IDs?
- What is the contract for ambiguous/unknown demand?
- Which examples are positive matches?
- Which examples are explicit non-matches?
- What evidence would falsify the proposed mapping?

Once defined, the contract becomes a candidate hypothesis and must be independently challenged before implementation.

This is a deliberate handoff: source evidence → human semantics → independent challenge → engineering.

Do not let the implementation actor silently decide the domain semantics.

## 2026-10-08 METHOD AMENDMENT — MINIMUM-REPAIR ADVERSARIAL CYCLE

When an adversarial semantic review finds real defects, do not automatically import the reviewer's full ontology into the project.

Use:
source/corpus fact
→ provisional semantic contract
→ adversarial falsification
→ reconcile only material defects
→ minimum surviving contract
→ focused re-challenge
→ source reconciliation
→ implementation contract.

The repair stage must preserve reuse-first and anti-scope-creep:
- repair the current causal boundary;
- do not solve workflow composition, full uncertainty policy, evidence ontology or future capability taxonomy unless the current implementation boundary requires it;
- distinguish a semantic necessity from a useful future extension.

This protects the developmental method from ontology inflation while retaining adversarial learning.
