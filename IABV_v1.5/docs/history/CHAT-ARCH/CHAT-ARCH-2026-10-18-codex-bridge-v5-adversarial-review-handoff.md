# IABV→CODEX bridge continuity — v5 adversarial review and next-step handoff

- **Record date:** 2026-10-18 (America/Bogota)
- **Repository:** `jhonf463r/Python`
- **Published source snapshot inspected for route reconciliation:** `main @ 9e0ce66768aedd7422e0d3551affd398f44a7532`
- **Current document status:** continuity/handoff record; it is not a v5 contract, acceptance decision, or implementation authorization.
- **Governance:** `KEEP_BLOCKED`
- **Bridge:** `BRIDGE_NOT_READY`
- **Implementation / local preflight / runtime:** `NOT_AUTHORIZED`
- **Immediate technical frontier:** `CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED`
- **Immediate governance/access frontier:** `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`
- **Local dirty-source frontier:** `LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED`

## 1. Canonical continuation rule

Start with this record, then reconcile the current remote `main` SHA and read the current overlays in:

1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md)
4. Entry 258 — owner decision C (keep Codex launch blocked while static design continues)
5. Entries 247–257 for the `codex exec`/home/rules/model/cost boundary
6. Entries 259–261 for local dirty-source handoff and governance-reader block

Use the canonical route, not broad archaeology. The GitHub connector sees published repository objects, not the owner's Windows checkout or desktop. A public `main` source snapshot must not replace local dirty/unpublished source.

## 2. Owner decision and non-negotiable boundaries

The owner's previously selected **C** remains binding: keep Codex launch blocked while static design and documentary review continue. C is not a choice of authentication/home option A or B, and not a selection of external executor architecture C.

No permission is implied for:
- Codex CLI/App Server launch, a model turn, any command beyond separately authorized read-only documentary work, local preflight, inventory/materialization of a candidate, tests, builds, runtime, or a canary;
- access to M0A or the blocked MCP reader, retrying/bypassing a governance-denied read, or a broad source dump;
- inspection or copying of credentials, new login/OAuth/API-key setup, installation/update/download, new plan, quota query, credit purchase, or additional spend;
- implementation, local configuration/source edits, commit/push, merge, or code promotion;
- inspecting `data/`, SQLite, Packages B–E, or `relay-staging\\IABV_v1.5\\data`; resetting, restoring, cleaning, or overwriting a dirty checkout.

Keep evidence classes distinct: `PROVEN_BY_SOURCE`, `OWNER_REPORTED`, `PROPOSED`, `UNPROVEN`, `UNRESOLVED`, `NOT_FOUND`, `NOT_RUN`, `CONFIRMED_LOCAL`, `HEAD_SOURCE`, and `WORKTREE_SOURCE` must not be substituted for one another.

## 3. Actual target outcome

The desired bridge is a governed development handoff, not a text-only consultation:

`IABV task → exact owner-authorized operation/prompt → isolated Codex candidate → terminal status + independently verifiable baseline/diff/changed-path artifacts → correlation of authorization/task/thread/turn/attempt/result → existing or explicitly authorized IABV verifier/consumer → separate owner accept/reject/promote decision`.

A task ID, narrative answer, persisted experiment result, generic artifact string, or documentation PR is not a coding receipt and does not establish causally linked learning. A prompt instruction or path-only copy is not a security boundary.

The public source findings recorded in prior entries remain bounded: tool selection is routing, not authorization; generic ToolTask/ToolResult do not establish a typed baseline-bound diff receipt; SandboxExperimentService evaluates route/configuration recommendations rather than Git candidates; ToolSandbox's flag is not OS confinement; PromotionPrPublisher publishes documentary evidence rather than executable-code promotion. Autonomous validation code paths exist in source, but current runtime state/wiring was not measured.

## 4. Latest adversarial review supplied by the owner: v5

**Evidence class:** `OWNER_REPORTED` review text supplied in this conversation. The reviewer reports reading a 623-line v5 file in read-only mode. The v5 file itself and its blob SHA were not independently fetched/verified in this continuation, and the review explicitly says it did not reopen public sources or inspect local state. Do not upgrade these statements to source-verified facts.

**Verdict:** `PASS_WITH_REPAIRS` for documentary coherence only; `PROPOSED / NOT_TESTED`; `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE_NOT_READY`.

The reviewer reports that:
- N-01–N-25 were not readjudicated in v5 (`NOT_RECOVERED`); v5 carried forward reported statuses only.
- N-26–N-41 mostly remain `PARTIALLY_CLOSED`; only N-31 and N-41 were called `CLOSED` documentarily.
- New findings N42–N64 were reported, including 13 high severity.
- The reviewer said v6 should be `FAIL` if N53 (credentials denied yet needed), N54 (incomplete disclosure upper bound), N59 (receipt depends on parser), and N60 (owner's signed view not bound to rendered bytes) remain unresolved.
- Satisfiability constraints may conflict: account exclusivity without new plan/auth, independently rooted control-plane identities/anchors, external containment of client/descendants, and independent accept/reconcile/release roles with a single owner.
- The register must distinguish `BLOCKED`/unavailable under current project constraints from merely `UNRESOLVED`; it must analyze joint satisfiability, not only list individual requirements.

### 4.1 Priority order for the next documentary delta

Do not start a wholesale rewrite or expand source archaeology. Work against the exact v5 file, if it can be located through an authorized published artifact or supplied as an attachment, and preserve its sections/IDs.

**P0 — protocol safety / ordering**
- **N42:** anchor advancement must be part of reservation commitment; rollback of the witness must block the domain.
- **N43:** expiry and maximum gate-to-resume latency must be checked at the linearization point; define one exact `DISPATCHED` trigger.
- **N44:** define outcomes for reservation abort before process creation and confirmed gate without resume; map each `reservation_status` to `attempt_status`.
- **N45:** idempotent read-only status query before global lock on ambiguous `ReserveCAS`; reserve global block for demonstrated divergence/rollback.
- **N46 / N50 / N51:** name writers for every control-plane operation/root, anchor the trust-root registry itself, and define complete domain-state transitions and recovery.

**P1 — authorization, principals, baseline and receipt**
- **N47–N49:** canonical/versioned manifests, bounded owner-review package, source-handle opener and OS scope, and one-use semantics for every authorization class.
- **N56:** rename `effective_policy_fingerprint` to a fingerprint of declared inputs if the preflight cannot independently measure effective policy; effective policy remains `UNKNOWN` unless externally attested.
- **N57–N60:** independent no-execution evidence; independent digest recomputation over immutable bytes; a deterministic trusted display path binding the exact bytes shown to the owner’s signed decision.
- **N61–N62:** unique state names, legal cross-dimension invariants, and an explicit no-second-human deadlock outcome without silently relaxing independent review.

**P1 — disclosure and feasibility**
- **N52–N55:** enumerate/approve or exclude exact `CODEX_HOME`/environment inputs; treat authentication material as a distinct, tightly bounded channel if allowed at all; include descendant-readable bytes/output and all egress endpoints in the disclosure upper bound; identify the egress enforcement and evidence authority.
- **N63:** define project meanings of “new authentication” and “additional spend”; list prerequisites and compatibility for every row; add human reconciliation/release, egress observer and lease/suspension rows. Mark constraints `SATISFIABLE`, `CONDITIONALLY_SATISFIABLE`, `BLOCKED_BY_CURRENT_CONSTRAINTS`, or `UNRESOLVED` with evidence/reason and owner decision needed.

**P2 — lifecycle/document fidelity**
- **N64:** remove conversation-only provenance from the self-contained artifact or label it explicitly as `OWNER_REPORTED`; make the transaction description reflect the witness+ledger protocol.
- Include the actual v3/v4/v5 state history accurately. Do not claim N-01–N-25 were reverified from v5 if the text/contraexamples were not present.
- Keep all controls `PROPOSED / NOT_DEMONSTRATED` until independent implementation evidence exists.

### 4.2 Required acceptance criteria for the next review

The next candidate should:
1. Preserve each inherited N-01–N-64 ID and give every item an explicit state, source section, counterexample, minimal correction, and discriminating future criterion; distinguish `NOT_RECOVERED` from `CLOSED`.
2. Resolve the P0 items before polishing low-severity wording.
3. Include a joint satisfiability register with scope definitions and explicit owner-decision dependencies. Do not silently relax the owner's no-new-auth/no-extra-spend/no-execution boundaries.
4. Make no claim that signatures, witness, ledger, LaunchGate, watchdog, OS boundary, receipt collector, disclosure observer, consumer, or promotion gate exists or works.
5. End with `DOCUMENT_STATUS = PROPOSED_DESIGN_V6`, `SEMANTIC_ACCEPTANCE = NOT_ESTABLISHED`, `IMPLEMENTATION = NOT_AUTHORIZED`, `GOVERNANCE = KEEP_BLOCKED`, `BRIDGE_NOT_READY` unless and until an independent review says otherwise.

## 5. Local provenance — keep checkouts distinct

Known reported checkout A (historical, from Entry 260): `C:\\Users\\faber\\.codex\\worktrees\\m0a-safe-ui-boot\\Python`, branch `codex/m0a-safe-ui-boot`, HEAD `5b1d890...`, 56 tracked modified + 6 untracked. This is historical/owner-reported.

Later reported checkout B: `C:\\temp\\IABV_coordination_20261016`, branch `codex/iabv-agent-coordination-20261016`, HEAD `3926b1144bb23c1066db579da711d3cdbc1611df`, 96 tracked files modified and `data/` untracked. Do not inspect `data/` or SQLite. These are distinct checkouts; never merge their facts or infer either represents current local state.

Owner-reported CLI facts from the latest prior handoff: Codex CLI `0.120.0`; shim `C:\\Users\\faber\\AppData\\Roaming\\npm\\codex.ps1`; observed config reported `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`, `sandbox = "elevated"`. A single `codex exec --help` was reported with exit 0; no model turn started. These remain `OWNER_REPORTED`, not independently measured by this coordinator. No sandbox canary is authorized. The earlier proposed `codex sandbox windows --full-auto` is invalid as an `exec` canary and premature under decision C.

Public source evidence through main @ `9e0ce667...` reports `rust-v0.120.0`/exec policy concerns and unresolved effective local sandbox, authentication, usage/cost, environment, child-network and rule-layer behavior. Do not install/update or assume model compatibility or zero cost.

## 6. Other open deliverables (do not lose)

The latest owner-supplied review explicitly reports two unfinished documentary deliverables:
1. **Independent report for R10 v0.7.4:** the 99 row-by-row evaluations are reportedly drafted, but the complete Markdown report has not yet been assembled. Status is `OWNER_REPORTED / NOT_ASSEMBLED / NOT_PUBLISHED`; do not claim access to the 99 rows unless the source is actually available.
2. **Candidate C verdict:** access was reportedly verified and analysis completed, but the verdict has not been emitted. Status is `OWNER_REPORTED / VERDICT_NOT_EMITTED`; do not infer the verdict or reconstruct it from memory.

These are separate from the IABV→Codex bridge and must not be silently substituted for the immediate bridge frontier. Resume either only after the user explicitly prioritizes it or after the bridge review handoff is stabilized; do not lose either item.

## 7. Next action

**Next actor: ChatGPT/coordinator — documentary reconciliation only.** Locate/fetch the exact v5 artifact from an authorized source or ask for the smallest missing artifact (the exact v5 file); do not ask for a broad source dump. Then produce a focused v6 delta/consolidation addressing N42–N64 and inherited-ID fidelity, especially N42, N43, N46, N50–N55, N57, N59–N63. Keep the v5 file immutable. Fetch back any new published candidate and verify the exact committed content before sending it to Sonnet/Claude for one bounded adversarial review.

No Codex/local executor handoff, preflight, inventory, materialization, authentication, quota check, test, build, runtime, implementation, source/config edit, commit/push or promotion is authorized by this record. A documentation writeback is persistence, not proof of integration or causal learning.
