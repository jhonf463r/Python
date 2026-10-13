# CHAT-ARCH-2026-10-13-243 — Existing Codex App Server adapter is not a bounded coding bridge

- **Episode ID:** `CHAT-ARCH-2026-10-13-243`
- **Timestamp (America/Bogota):** `2026-10-13T12:17:38-05:00`
- **Timestamp (UTC):** `2026-10-13T17:17:38Z`
- **Canonical remote baseline at intake:** `main @ d8ff02d1dfacbed15d20f797bdbe8c3d96bab9a0`
- **Prior routing adjudication:** [entry 241](./CHAT-ARCH-2026-10-13-241-codex-development-bridge-route-adjudication.md)
- **Continuity/intake method record:** [entry 242](./CHAT-ARCH-2026-10-13-242-inline-transcript-intake-and-continuity-audit.md)
- **Classification:** `CODEX_BOUNDED_DEV_MODE_STATICALLY_BLOCKED`
- **Evidence provenance:** Owner-supplied Codex report of a bounded local source audit; not independently remeasured against the Windows worktree in this writeback.

## 1. Current Owner objective

The goal remains the governed development bridge:

`IABV deficit/task → exact owner-authorized prompt → Codex coding task in a confined candidate workspace → terminal status + verifiable diff/artifacts → task/thread/turn correlation → existing IABV consumer + independent verifier → owner-controlled promote/reject/revert → later causal-reuse test`.

This is not merely text consultation. The current adapter's successful text-capture path is not a substitute for a coding route that can write and return verifiable artifacts.

## 2. Worktree and spatial provenance

The report observed:

- Worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`
- Branch: `codex/m0a-safe-ui-boot`
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- Inventory: 56 tracked modified files and 6 untracked files.
- Reported untracked files: `safeui_openai_text_launch.ps1` and five tests, including `test_m0a_codex_task_identity_preserved.py`.
- No tests, processes, preflight or external calls were run by the reporting actor; no files were modified in that audit.

These are actor-reported local observations, not fresh facts independently observed by the continuity writer. Preserve all existing worktree modifications, `.pyc` changes and untracked files; never use cleanup/reset/restore to make the inventory easier.

The report did not find the entry-241 Markdown file in the local worktree inventory. That file was created and registered on remote `main` after the reported local HEAD. Its absence from this older worktree is a source-location/version mismatch to account for, not proof that the canonical remote record is missing. The audit should use the remote canonical record supplied by the owner or read from GitHub; do not silently claim the local branch contains it.

## 3. Evidence reconciliation

| Claim | Status | Risk / interpretation |
|---|---|---|
| SafeUI binds operation/task/correlation IDs and prompt before dispatch | `PROVEN_BY_SOURCE` in the Owner-supplied audit | The authorization does not bind a candidate-worktree root, allowed files, allowed commands or publication policy. |
| Task ID repair is integrated through SafeUI and ToolTeachService | `PROVEN_BY_SOURCE` as reported; prior focused test PASS is `OWNER_REPORTED` | Adapter-level validation alone does not replace pre-dispatch authorization checks. No live dispatch is proven. |
| Resolver guarantees Codex CLI 0.120.0 | `UNPROVEN` for effective binary identity | Source reportedly resolves the executable/shim dynamically from `PATH`; expected `userAgent` is not binary attestation. |
| `IABV_CODEX_HOME` is wired into adapter child environment | `PROVEN_BY_SOURCE` as reported | Actual authentication, plan entitlement, quota and cost remain `UNPROVEN`; no credentials were inspected. |
| Current turn is a coding task rooted at a writable candidate checkout | `PROVEN_BY_SOURCE` false / capability absent in reviewed path | `_turn_scope()` reportedly requires an empty root and requests read-only access plus `networkAccess=False`; there is no writable candidate composition. |
| Job Object provides secure filesystem/network isolation | `UNPROVEN`; source reportedly proves process-tree containment only | Job Objects manage process groups/limits and termination; this does not itself establish ACL/token/AppContainer/VM or egress restrictions. |
| Client-side event rejection prevents server-side effects before the event | `UNPROVEN` and not a valid inference | Rejecting an event after receipt is not proof the server could not begin an operation before client handling. |
| The current adapter returns candidate artifacts/diff | `PROVEN_BY_SOURCE` false / current contract absent in reviewed path | `run()` reportedly returns `output_text` and thread/turn/message metadata, not a verified code diff or candidate artifact bundle. |
| A captured `ToolResult` was actually received and evaluated | `UNPROVEN` | Source wiring/persistence do not prove live response or consumer evaluation. |

## 4. Adjudication of the previous route

Entry 241 asked whether the existing route could support a confined coding task. The Owner-supplied report answers **no for the current composition**. It is not a matter of changing only a prompt or switching read-only to writable:

1. The approved operation is not bound to a canonical candidate root, baseline identity, allowed paths, command policy and publication boundary.
2. The current adapter's scope is a temporary empty/read-only consultation context rather than a writable candidate worktree.
3. The Job Object is a process lifecycle/containment primitive, not evidence of filesystem, credential or network isolation.
4. The protocol request does not declare an explicit tool allowlist; rejecting reported tool events client-side does not prove pre-effect prevention.
5. The adapter returns text and metadata, not a candidate diff/artifact package for independent code verification.
6. Exact executable/protocol identity and actual native auth/entitlement/quota/cost are separate open gates.

Therefore, `CODEX_BOUNDED_DEV_MODE_STATICALLY_BLOCKED` is accepted **as an Owner-reported source audit of the current adapter path**. No real Codex development bridge has been demonstrated. This finding does not prove that a differently composed, OS-confined coding route is impossible.

## 5. Additional design constraint from official Windows documentation

The following are external platform facts, not measurements of the user's device:

- Windows Job Objects group/manage processes and can enforce process/job limits or termination; that role should not be represented as a filesystem or network sandbox. [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
- Windows AppContainer is designed to isolate process access to files, registry, other processes and network, with access granted by capabilities. [Microsoft AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation).
- Windows Sandbox can disable networking and configure mapped host folders, but mapped writable folders persist changes to the host, and disabling all networking would conflict with a remote Codex service unless a separately controlled communication path exists. [Configure Windows Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file).

No one of these options is yet selected or proven available on the user's system. Do not prescribe an OS primitive as implemented merely because documentation describes it.

## 6. Minimum next task: architecture/design tranche, not more generic audits

New first open edge: `CODEX_CANDIDATE_WORKSPACE_EXECUTION_BOUNDARY_DESIGN_UNRESOLVED`.

The next step should be one bounded **design-only** task using existing IABV organs; do not make code changes yet. It must decide whether a coding route can reuse the current App Server transport with an enforceable OS boundary, or must use a separate contained executor. The design must explicitly cover:

- Canonical baseline SHA/tree and a disposable candidate worktree not writable from the normal owner process except via explicit candidate preparation/promotion steps.
- An OS-enforced write/command boundary that prevents access to the original worktree, credentials and unrelated user files.
- Explicitly bounded command execution, package/tool availability and process lifetime.
- Egress/network control that permits only the communication required for the chosen Codex/auth mode, while preventing unapproved network/MCP/app/browser effects. No credential copying, secret dump or unapproved auth setup.
- Exact one-use Owner authorization bound to operation, destination, prompt/digest, baseline, candidate root, permitted scope/commands and no-publication condition.
- Stable task ID plus thread/turn IDs, dispatch-once semantics, terminal event/failure/timeout/late-event handling, candidate tree/diff digest and test evidence capture.
- Use of the existing `ToolTeachService`, `ToolRegistry`, `ToolResult`, `SandboxExperimentService`, `AutonomousValidationCycleService` and existing consumer only where source proves the role; no new parallel brain, router or memory.
- Independent verification and Owner-gated promote/reject/revert; no automatic commit, push or `main` mutation.
- Authentication and included usage quota/cost as hard readiness gates; no billable API, new OAuth integration, installation, model download or extra spend.

Compare only a small number of concrete candidates, including whether the existing App Server's requested sandbox can be proven effective on this Windows setup and whether an OS-enforced isolated executor is viable without exposing host credentials. Do not select an option solely by its conceptual simplicity.

## 7. Required evidence and stop rule

The design report must include one selected recommendation with assumptions and rejected alternatives; map each security guarantee to an actual enforcement layer; mark unavailable host/runtime facts `UNPROVEN`; and provide the smallest separately authorized implementation task.

No source edits, tests, build, runtime, process launch, network request, prompt, credential inspection, OAuth/API setup, install/download, expense, commit, push or promotion in the design tranche.

## 8. Memory and learning status

This episode adds a durable negative fact: **the current App Server adapter is a text-response transport, not a bounded code-change/artifact transport**. It also refines the route from proving the current adapter safe to designing a separate effect-confined coding mode.

It does not prove IABV learned autonomously. The memory writeback itself is a persistence event. Later claims of learning require showing that this verified negative result is retrieved on a later, non-identical development task, changes route/decision or execution, and contributes to a better independently verified outcome.

Current route status: `CODEX_BOUNDED_DEV_MODE_STATICALLY_BLOCKED` for the existing implementation.  
Next edge: `CODEX_CANDIDATE_WORKSPACE_EXECUTION_BOUNDARY_DESIGN_UNRESOLVED`.  
Stop after the design-only report.
