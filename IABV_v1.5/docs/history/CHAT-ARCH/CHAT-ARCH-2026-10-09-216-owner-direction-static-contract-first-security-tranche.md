# CHAT-ARCH-2026-10-09-216 — OWNER DIRECTION: DRAFT STATIC CONTRACT FOR FIRST SECURITY TRANCHE

## PURPOSE AND OWNER DIRECTION

The Human Domain Owner replied "si procede" ("yes, proceed") after RQ215 recommended moving to a bounded implementation-contract decision before any code changes. This is interpreted narrowly as authorization to prepare a source-grounded design/contract proposal for the first security-critical tranche only.

It is NOT authorization to edit code, change the worktree, execute tests/builds, run packages, start/reconnect MCP, inspect processes, or perform runtime verification.

Repository: jhonf463r/Python.
Canonical main confirmed immediately before this record: 98506d9579a8a398b7685e2279a3a005dfe04b62.
Prior gate: [RQ215 — RQ214 adjudication and next owner gate](https://github.com/jhonf463r/Python/blob/98506d9579a8a398b7685e2279a3a005dfe04b62/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-215-rq214-adjudication-symbiosis-and-next-owner-gate.md).

## TASK TO PREPARE

Prepare a read-only, source-grounded contract proposal for exactly this first tranche:

1. Mutation authorization: define a mandatory fail-closed decision for each MCP self-update mutation, bound to the operation, target resource, and permitted scope. The proposal must identify who/what is allowed to approve each mutation class and what evidence of approval is required. Do not assume the existing observation-permission gate is suitable for mutation authorization.
2. Filesystem scope: unify protected-path and workspace-root checks across every in-scope file-mutating handler; address canonical path resolution and Windows case-insensitivity. Identify the paths/operations already implicated by RQ207-S, without broadening into unrelated APIs.
3. Git scope: propose explicit file selection/allowlisting and safe diff review; default to no push in the first tranche. Broad defaults such as staging the whole workspace must not remain implicitly authorized.
4. Network-required governance: when a route requires network access, unknown/missing network state should be treated as not approved unless a direct, source-proven alternative exists. Keep network availability separate from permission to perform a mutation.

Use only directly relevant, already-known files and symbols such as the existing MCP self-update handlers, their existing governance callback/current-model gate, WorldModelSnapshot/permission model only as needed to explain why the current gate does or does not satisfy the desired contract, and the reported dirty server.py as source context with a loud provenance warning. Do not conduct another broad dependency audit.

## CONTRACT OUTPUT REQUIRED

Produce a proposal, not a patch, with:

- Operation inventory: each existing mutator and each effect class it can perform.
- Proposed authorization data contract: operation/action, target resource, scope, approver identity/authority, grant/decision state, expiry or freshness semantics, denial reason and auditable decision receipt. Mark any field that cannot be grounded in existing design as a proposal requiring Owner acceptance; do not pretend these fields exist today.
- Decision table for valid approval, missing approval, unknown/stale state, mismatched operation/resource/scope, explicit denial, callback exception, malformed data and unavailable WorldModel.
- Required ordering: authorization resolution and target/path validation must occur before the first mutation side effect; any inability to establish authorization must return/block without mutation.
- Filesystem invariants: containment under an approved root, protected-path policy, Windows case-insensitive comparisons, safe handling of symlinks/reparse points, rejection of path traversal and consistent enforcement by all in-scope handlers.
- Git invariants: explicit files, verified diff, no implicit repository-wide staging, and no push for the first tranche.
- Network invariant: unknown connectivity must not pass a network-required gate.
- Source-grounded current-vs-target comparison: what the supplied RQ207-S/RQ210 findings say exists now versus what the proposed contract requires.
- Acceptance criteria that can later be checked statically without executing project code.
- Known residual risks, exact missing dependencies and decisions that only the Owner can make.

Keep current-state findings and proposed design decisions visibly separate. For every current-state claim, supply file path, line range and actor-reported local SHA-256 where available; state explicitly when the hash is unavailable or only comes from the prior Codex report. Do not replace dirty-worktree evidence with remote-main hashes.

## OWNER POLICY DECISIONS TO PRESENT, NOT SILENTLY INVENT

The report must present a concise set of decisions for Owner approval before implementation:
- Who/what can approve the mutation classes (human-only vs separately defined policy authority).
- Whether permission is required per operation and per resource/scope (recommended: yes).
- Behavior on absent, unknown, stale, malformed or mismatched permission (recommended: deny).
- Which workspace roots and protected paths are in scope.
- Whether remote Git push is excluded from the first tranche (recommended: yes).
- Whether the next authorization, if approved, permits code edits only and forbids runtime/tests/builds (recommended first implementation phase: source edits only; separately authorize any verification phase).
- Whether a new clean isolated worktree must be prepared from an explicitly selected baseline before implementation. The existing dirty/detached worktree MUST remain untouched; this task may not create or alter another worktree.

If a choice cannot safely be inferred, mark it OWNER_DECISION_REQUIRED. Do not pause the contract proposal merely because a policy value is unspecified; provide a conservative recommendation and clearly preserve the decision boundary.

## PROVENANCE PRECONDITION

The prior Codex worktree was reported at C:\Users\faber\.codex\worktrees\universal-ui-structure\Python, detached at e46d8304167708bed0764d3bf2be8fd6643e8944, tree 52e51064967b8923dc7f200c10809971af9c558a, with 386 status entries and a modified server.py. These values are actor-reported. If local static inspection is needed, confirm current identity/status first and preserve all changes. If identity materially differs or the needed local file is unavailable, stop and document that gap. The contract may rely on the already-adjudicated reports as prior evidence but must state their provenance limits.

## STRICTLY NOT AUTHORIZED

No code edits, patches, worktree creation/cleanup/switch/reset/stash/rebase, Git mutation, tests, compilation, build, package manager/install/download, runtime imports or execution, MCP start/restart/reconnect/tool call/list, process/window inspection, health checks, network probes, scans, refreshes, environment dumps, DB/secrets/snapshot reads, or operational data disclosure.

Do not perform a broad repository-wide search or recurse into unrelated governance, lifecycle, RQ13-111 causal learning, or RQ21.200 DLL consumer. Stop at any new material dependency and name it.

## NEXT GATE

Return the contract proposal to the coordinator. The coordinator will adjudicate it and present the explicit Owner decisions. A subsequent source-edit task requires a separate clear authorization naming baseline, worktree, files, exact permitted edits and prohibited side effects. This record authorizes design only.

## GLOBAL STATUS

RQ214 remains STATIC_REMEDIATION_PLAN_COMPLETE_WITHIN_SCOPE as a planning deliverable. Overall MCP readiness remains TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES; isolation is not established. RQ21.200 remains separate.

END OF RECORD