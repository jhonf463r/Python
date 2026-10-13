# CHAT-ARCH-2026-10-13-247 — Current IABV integration cannot establish a future exec environment

- **Episode ID:** `CHAT-ARCH-2026-10-13-247`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline at intake:** `main @ d869c75b350d4c5c8f70873021330727a6492251`
- **Input:** Owner-supplied local source-audit report `CODEX_EXECUTION_INTERFACE_STATICALLY_BLOCKED`
- **Related records:** entries 243–246.
- **Adjudication:** `CODEX_EXECUTION_INTERFACE_STATICALLY_BLOCKED` for the current IABV integration.
- **First open edge:** `CODEX_EXEC_LAUNCH_ENVIRONMENT_CONTRACT_UNDEFINED`

## 1. Intake and evidence boundary

Accept the provided static findings as owner-supplied source-audit evidence:

- Worktree reported as `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`, branch `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`, 56 tracked files modified and 6 untracked. Preserve all changes, including `.pyc` modifications. These are report-only for this writer.
- The user reported no remote calls, process launches, Codex invocation, tests, inference or local file/config changes in that audit.
- The previously identified shell shim/package resolving to Codex `0.120.0` identifies only the inspected session. The IABV process's future CLI path and environment are not established.
- The local checkout lacks entry 246 because this record is present on remote `main` and was not in the older local checkout; that is not evidence that the remote record is missing. The local audit deliberately did not query remote `main`.

## 2. Adjudication

The report is accepted for the **current IABV code path**. The distinction is structural:

- **Current App Server path:** source is reported to read `IABV_CODEX_HOME` through application config, pass the value through Bootstrap, validate an explicit home and construct a constrained child environment with `CODEX_HOME` set. It creates an operation-specific environment for App Server, requests `read-only` and returns final text plus correlation metadata. The code's own indicators reportedly leave effective sandbox, effective approval policy and turn tool surface unobserved. Requested policy is not proof of OS enforcement.
- **Candidate CLI path:** the installed CLI package exists in the inspected shell, but no IABV `exec` adapter/argument construction/launch-environment contract was found in scope. There is therefore no future IABV `exec` child whose actual target `CODEX_HOME` can presently be read off from source. Inferring a value from the interactive shell or the existing App Server path would be a category error.
- **Configuration:** previously observed `sandbox_mode = "danger-full-access"` and `approval_policy = "never"` belong to another observed default home, not an established IABV exec target. They are neither an effective-policy finding nor a recommendation. Do not copy those settings.
- **Versioned contract:** entry 246 records public source declarations for `rust-v0.120.0`; the latest local audit could not independently review them because its mission prohibited network access and the canonical record was absent from its checkout. It correctly left the runtime acceptance of CLI arguments `UNPROVEN` within that local task. The earlier source citations in entry 246 remain source evidence for the named public tag; they do not prove which binary IABV will execute.
- **Runtime/auth/cost/consumer:** no actual task, session availability, plan entitlement, quota, no-extra-spend eligibility, Windows enforcement, result/diff capture or consumer ingestion is proven.

## 3. Evidence ledger

| Claim | Evidence class | Consequence |
|---|---|---|
| Local branch/HEAD/tree and dirty counts as listed above | `OWNER_REPORTED` | Preserve; do not reset/clean or claim fresh observation |
| Existing code reads `IABV_CODEX_HOME` and hands the configuration value to the App Server adapter | `PROVEN_BY_SOURCE` within the reported inspected paths | Applies to the reported App Server composition only |
| The shell inspected earlier resolves a Codex 0.120.0 package/native binary | `OWNER_REPORTED` / source metadata reported by the owner | Do not infer IABV-child identity |
| Current inspected scope found no IABV CLI `exec` integration | `PROVEN_BY_SOURCE` within the inspected scope | Current integration is blocked; absence beyond that scope is not claimed |
| Effective policy/config of a future `exec` child | `UNPROVEN` | Cannot infer it from an environment that does not yet exist in the integration |
| Native Windows sandbox enforcement, network/MCP/plugin suppression, existing auth, quota/cost, candidate diff and consumer result | `UNPROVEN` | No coding turn authorized |

## 4. Corrected next frontier

**First open edge:** `CODEX_EXEC_LAUNCH_ENVIRONMENT_CONTRACT_UNDEFINED`.

Do not repeat a search for the value of a nonexistent future child environment. The smallest justified next task is a **design-only, source-grounded launch-contract specification** for a possible `exec` adapter. It must specify, without implementation:

1. How the existing SafeUI operation authorization, task identity, prompt/digest and permitted scope bind to a proposed CLI dispatch before any external effect.
2. How the executable is selected/pinned and how a mismatch from the authorized version/path fails closed; do not trust the interactive shell's `PATH` by implication.
3. Whether the proposed CLI uses an explicit, dedicated `CODEX_HOME` distinct from unrelated interactive homes; how that home is initialized from already existing non-secret config; and how no credentials are copied or exposed. Do not make up a live home path/value.
4. The desired sandbox/approval policy and Windows enforcement dependency, candidate-root and command boundaries, network policy, and how MCP/plugin/app effects are excluded unless separately authorized.
5. The already-supported `0.120.0` arguments from entry 246 versus options that remain unresolved. No runtime probing or invocation is part of this design.
6. The artifact contract: exit/terminal status, final response, JSONL if applicable, baseline and candidate diff, provenance/digests and failure handling; distinguish the final-message file from a source diff.
7. How artifacts enter the existing IABV consumer/verifier and how the Owner remains the sole promotion/rejection authority.
8. Independent gates for existing authentication/session, entitlement/quota and zero additional spend. If the no-extra-spend condition cannot be demonstrated, the route remains blocked.

Use current source only. If the design depends on facts not present in source, mark them `UNPROVEN`; do not launch CLI, run tests, inspect secrets or make edits to prove them. Return the design for adjudication before any implementation authorization.

## 5. Explicit non-authorization

This entry does **not** authorize a coding turn, CLI/App Server invocation, process launch, tests/build, network request, UI/CDP action, credential or session inspection, install/update/download, config/source changes, API/OAuth setup, additional spending, commit, push or promotion. No local dirty/untracked content may be changed. No claim is made that IABV → Codex → IABV has completed.

## 6. Durable continuity consequence

The first open edge moves from trying to identify the effective policy of a not-yet-integrated CLI child to defining the missing **launch environment and execution contract**. The project must first design how that environment would be created and bound to authorization; only a later, separately authorized implementation/diagnostic could yield an actual effective home/policy.

GitHub documentation is external persistent project memory. This writeback is not automatic model learning, a runtime exchange, a validated artifact handoff or causal reuse.
