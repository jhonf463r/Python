# CHAT-ARCH-2026-10-09-217 — RQ216 CONTRACT ADJUDICATION / OWNER POLICY GATE

## PROVENANCE AND CANON

Repository: `jhonf463r/Python`.
Canonical `main` confirmed immediately before adjudication: `7b8ad5198a9bbc71b67f912c07a2b7b920f044aa`.
Input direction: [RQ216 — Owner direction for static first-tranche contract](https://github.com/jhonf463r/Python/blob/7b8ad5198a9bbc71b67f912c07a2b7b920f044aa/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-216-owner-direction-static-contract-first-security-tranche.md).
Prior gate: [RQ215 — RQ214 plan adjudication](https://github.com/jhonf463r/Python/blob/7b8ad5198a9bbc71b67f912c07a2b7b920f044aa/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-215-rq214-adjudication-symbiosis-and-next-owner-gate.md).

The Owner-supplied RQ216 report states that the target worktree is `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`, detached at `e46d8304167708bed0764d3bf2be8fd6643e8944`, tree `52e51064967b8923dc7f200c10809971af9c558a`, with 386 status entries. The reported source hashes were measured locally by Codex. The coordinator did not independently access the Windows worktree bytes. The current local `server.py` is modified; source anchors used for baseline-only behavior were read from Git blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`. Do not attribute the modified local bytes to the historical executable.

## CLASSIFICATION

**ACCEPT RQ216 AS A SOURCE-GROUNDED CONTRACT PROPOSAL COMPLETE WITH OWNER POLICY DECISIONS PENDING. NO IMPLEMENTATION IS AUTHORIZED.**

The proposal meets RQ216's design-only deliverable: it enumerates the implicated mutators, explains why observation gates are not mutation approvals, proposes fail-closed authorization bound to operation/resource/scope, identifies inconsistent path controls, makes Git file scope explicit and excludes push from the initial tranche, and treats network eligibility separately from mutation authorization.

It is not yet implementation-ready because the approval authority, exact workspace roots/protected paths, source baseline and isolated worktree, and any future verification scope remain Owner decisions. These policy values must not be inferred by Codex or by the coordinator.

Global MCP readiness remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. Isolation is not established. RQ13-111 and RQ21.200 remain separate.

## SOURCE FINDINGS ACCEPTED WITH PROVENANCE LIMITS

The submitted report's source analysis states:
- Registered mutators include `write_repo_file`, `apply_text_patch`, `git_commit_and_push`, `self_merge_branch` and `self_update` (with checkout/pull effects).
- Current `ObservationPermissionGate` is produced from observation-permission state; it lacks an explicit mutation operation/resource/approver/vigency contract.
- The baseline governance callback rejects absent WorldModel/service/snapshot and errors obtaining `current_model()`, but gate matching is based on required status and `assistant_kind`, not a concrete mutation approval. An empty or non-applicable set may pass.
- Unknown/missing network state can fail to block a route that requires network. Network eligibility is separate from mutation authorization.
- File path protections differ between handlers; the reported string denylist is not uniform, and Git staging/push defaults are too broad for a security-sensitive mutator.
- The dirty local `server.py` cannot be used as baseline proof; the report anchors relevant baseline functions in the HEAD blob.

These are accepted as actor-reported/local-source findings from this bounded task. They are not a new runtime observation, do not prove an actual mutation occurred, and do not independently identify source loaded by the historical process.

## CONTRACT ADJUDICATION

### Target authorization contract

The following are appropriate target properties, not claims that they exist in current code:
1. Every mutating effect is authorized before its first side effect.
2. The decision is bound to a concrete operation and canonical target resource plus exact permitted scope.
3. Approver authority is explicit and verifiable; observation permission is not accepted as mutation approval.
4. Missing, unknown, stale, malformed, explicitly denied or non-matching authorization blocks.
5. Callback/verifier exception cannot turn into approval.
6. Composed operations are split for authorization: stage, commit, push, checkout, pull and merge have distinct effects; default first tranche has no remote push.
7. Filesystem checks share the same canonical root/protected-path policy across all implicated handlers and address Windows case behavior, traversal, links/reparse points and race risk.
8. Git operations select explicit files and review the staged diff against the authorized set; already-staged or concurrent unexpected changes block.
9. For a route that requires network, absent/unknown/disconnected state blocks that route. Connectivity never substitutes for mutation permission.
10. The receipt/audit record records the decision context and denial reason but is not itself the trust anchor.

### Missing material dependency

The report does not identify a trusted producer/verifier of mutating authority or how the human/policy authority is authenticated and bound to the decision. This is a material design dependency. Existing `permission_snapshot` must not be repurposed as proof of mutation authority merely because it exists. The Owner must define the authority policy before any implementation task; if a verified implementation source for that authority is needed, create a separate narrowly scoped audit rather than broadening RQ216 retrospectively.

### Filesystem/Git caveat

String-based path checks are insufficient as a contract. The eventual implementation must define a uniform path canonicalization/containment rule and how to handle Windows junctions/reparse points and validation/write races. Git scope also needs to account for pre-existing staged changes, not merely the current command's path argument.

These are target requirements only; RQ216 did not test them and did not modify files.

## OWNER DECISIONS REQUIRED BEFORE IMPLEMENTATION

Codex correctly surfaced these choices. Coordinator recommends the conservative defaults below but does not decide them on the Owner's behalf.

1. **Approver identity and authority:** recommended first tranche = human Owner approval only, represented by an explicitly verifiable decision; do not permit an inferred policy route unless separately defined and approved.
2. **Authorization granularity:** recommended = per operation, canonical resource and exact scope; compound Git/worktree effects require separate decisions.
3. **Unknown/invalid permission:** recommended = deny if missing, unknown, stale, malformed, explicitly denied, exceptional or non-matching.
4. **Workspace/protected paths:** Owner must explicitly supply the canonical allowed root(s) and protected-path policy. Do not infer from current process CWD or the dirty worktree's location.
5. **Git:** recommended = explicit file allowlist, pre-commit staged-diff verification, reject unrelated pre-staged changes, and no push in tranche one.
6. **Implementation baseline:** must be explicitly chosen. Options already visible in prior records include the previously named pinned executable baseline `5b1d89022ee4cdc63c1f88e050f086b40a42875c` and the current reported dirty worktree HEAD `e46d8304167708bed0764d3bf2be8fd6643e8944`. Do not treat the latter's current dirty files as a clean baseline. Coordinator recommends choosing an exact immutable commit and preserving the existing worktree.
7. **Implementation worktree:** recommended = a separate clean isolated worktree prepared from the chosen commit in a future task; this RQ216 task has not created or changed any worktree.
8. **Next-phase permissions:** recommended = a future authorization for source edits only, explicitly excluding tests/builds/runtime. Any tests/build or runtime verification would require a separate authorization.

## NEXT GATE

Do not issue a source-edit task until the Owner has adjudicated items 1–8, at least the authority policy, roots/protected paths, baseline and isolated-worktree choice. After those decisions, the coordinator can prepare a narrowly scoped source-edit contract naming exact paths and exact prohibited side effects. The existing dirty/detached worktree remains untouched.

No code edits, worktree creation/changes, Git mutation, tests/builds, imports/execution, MCP use/start/reconnect, process inspection, probes, scans/refresh, DB/secrets/snapshot reads, dependency installation/download or RQ21.200 work was performed or authorized here.

END OF RECORD