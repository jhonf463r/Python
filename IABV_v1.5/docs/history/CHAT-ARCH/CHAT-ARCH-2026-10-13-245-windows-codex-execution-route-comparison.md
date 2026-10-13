# CHAT-ARCH-2026-10-13-245 — Windows Codex execution route comparison after App Server coding-mode block

- **Episode ID:** `CHAT-ARCH-2026-10-13-245`
- **Timestamp (America/Bogota):** `2026-10-13T12:26:26-05:00`
- **Timestamp (UTC):** `2026-10-13T17:26:26Z`
- **Canonical remote baseline at intake:** `main @ 201873dfa749aefca332181cb47828b9996c9e81`
- **Prior input:** Owner-supplied local Codex report `CODEX_NATIVE_WINDOWS_SANDBOX_PATH_STATICALLY_BLOCKED`
- **Related records:** entries 241, 242, 243 and 244.
- **Classification:** External-source route refinement; no local runtime, source, configuration or worktree inspected by this writer.

## 1. Adjudication of the latest Owner report

Accept `CODEX_NATIVE_WINDOWS_SANDBOX_PATH_STATICALLY_BLOCKED` for the **existing IABV App Server adapter composition**, based on the Owner-supplied source audit. Its current route describes a text consultation, builds an empty-root read-only scope, returns final text and IDs rather than a candidate diff, and has not established effective native Windows sandboxing or a writable worktree boundary. The Windows Job Object reported in source governs process-tree lifetime/containment; it is not proof of filesystem, credential or network isolation.

The local state remains report-only:
- Worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`
- Branch: `codex/m0a-safe-ui-boot`
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- 56 tracked modifications, 6 untracked files, including existing `.pyc` modifications.
- The report says it did not modify files or run processes, tests, preflight or external calls.

These local facts were not freshly observed by the canonical writer. Preserve all local changes. Entry 243/244 were created on remote `main` after the reported local HEAD, so their absence from this older local worktree is expected and does not mean the remote records are absent.

## 2. New external evidence affecting route selection

### A. Official Codex automation example uses `codex exec`

The official OpenAI Cookbook, “Build iterative repair loops with Codex,” demonstrates launching `codex exec` from a script with `--sandbox workspace-write`, a structured output schema and a file path for the last message. It uses the CLI as a subprocess and validates the resulting artifact in a separate phase.

Reference: https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex

This is a documented candidate interface for an automated coding workflow. It does **not** prove that the Owner's installed CLI/authentication can use it, that its Windows sandbox is provisioned/effective, or that its usage is available at no additional cost. It also does not remove the need for a disposable candidate, least privilege, artifact verification or owner-controlled promotion.

### B. Public Windows App Server report matches the key concern

Open public issue [openai/codex #37818](https://github.com/openai/codex/issues/37818), opened 2026-08-10, reports that Codex CLI `0.147.0-alpha.6.5` on Windows, using App Server stdio with `workspace-write`, explicit `writableRoots` and networking disabled, completed a turn without exposing `commandExecution` or `fileChange` items. The report states that no file was created. The issue was open at the time of this review.

That is an actor-reported community issue for a specific version/environment, not proof of a universal App Server defect. It does show that a syntactically valid `workspace-write` request and a completed turn do not guarantee the expected coding tools are actually exposed.

### C. Public Windows sandbox spawn failures are a separate operational risk

Public issue [openai/codex #39276](https://github.com/openai/codex/issues/39276), opened 2026-08-18 and closed as a duplicate on 2026-10-12, reports `CreateProcessAsUserW failed: 5 (Access is denied.)` with the Windows sandbox on Codex CLI 0.147.0. The thread attributes that particular report to a packaged PowerShell alias and points to a narrower duplicate; it does not establish a universal sandbox failure. It is evidence that shell/package path compatibility can determine whether in-sandbox commands are actually spawned.

Reference: https://github.com/openai/codex/issues/39276

### D. The 0.120.0 Windows packaging report must be interpreted narrowly

Public issue [openai/codex #17423](https://github.com/openai/codex/issues/17423) reported missing Windows package variants on 2026-04-11, but a maintainer replied that publication was delayed and the variants were subsequently published; the issue was closed as completed that day. This is **not** evidence that today's local CLI is broken. It reinforces the requirement to identify the actual resolved binary/package instead of equating a version string expected by the adapter with the installed executable.

## 3. Consequence: do not assume App Server is the only or shortest coding interface

The candidate execution interfaces within the same Codex product should now be compared on the exact local installation:

| Candidate | What it may provide | Unresolved gate |
|---|---|---|
| Existing App Server adapter | Structured thread/turn lifecycle and event correlation, already wired to SafeUI | Current mode is read-only text consultation; Windows App Server may not expose coding items under some version/config combinations; candidate diff path absent |
| Existing Codex CLI `exec` capability | Officially documented scripted coding via `workspace-write` and structured output | Actual installed version/path, native Windows sandbox provisioning, authenticated plan mode/quota/cost and artifact/result integration are all unproven |
| Separate OS-enforced executor | A distinct, explicitly confined candidate workspace if neither existing interface can provide it | More new code/infrastructure; do not build it before the two existing Codex interfaces are discriminated |

This does not select `codex exec` yet. It prevents premature commitment to App Server or premature creation of a new executor.

## 4. Next edge

Updated first open edge: `CODEX_WINDOWS_CODING_TRANSPORT_AND_SANDBOX_COMPATIBILITY_UNRESOLVED`.

The smallest next step is a **one-time, non-mutating local capability inventory**. Its purpose is to identify, without starting an agent turn:
1. the precise executable/shim that the current Windows resolver would launch, its resolved package/binary version and executable identity;
2. the non-secret, effective sandbox selection and relevant Windows mode/config keys already present;
3. the existing CLI's documented/scriptable `exec` support versus the App Server mode actually wired into IABV;
4. the locally present, non-secret config needed to decide the next compatibility check, without reading tokens, credential stores, sessions or dumping the full process environment.

Prefer static inspection of existing files, path resolution and package metadata. Do not install/update anything or edit configuration. If the exact binary identity or effective sandbox state cannot be proven without executing a command, stop and report the exact one-time diagnostic that would be needed; do not launch a Codex turn to learn the version.

After the inventory, select the smallest candidate capability check for a future separately authorized test. Such test, if eventually approved, must use a disposable candidate fixture, a single fixed harmless file change, no original-worktree access, no secret access, no external tool/MCP/browser integrations, network policy explicitly verified, no tests beyond the pre-authorized local fixture, and no commit/push/promotion. Do not execute that test within this inventory task.

## 5. Evidence boundary and cost constraints

- Current adapter blocked for a coding task: `OWNER_REPORTED` source-audit result.
- Official Cookbook has a `codex exec --sandbox workspace-write` scripted example: `PROVEN_BY_SOURCE` for the documented example, not local readiness.
- Issue #37818 and #39276 describe specific user-reported cases: external operational warning evidence, not universal proof.
- Actual local binary/protocol, Windows sandbox provisioning/effectiveness, enabled coding tools, authentication, plan entitlement/quota/cost and IABV consumer evaluation: `UNPROVEN`.

No billable API key, new OAuth setup, credit purchase, installation, download or extra spend. Do not claim Free-plan use is unlimited. Do not read credential contents.

## 6. Memory/learning consequence

The durable routing delta is: **compare App Server against the installed CLI's `exec` path before implementing a separate executor**. The goal remains the governed coding handoff, not another text provider.

This record is external persistent project memory only. It does not prove automatic memory retrieval, local runtime operation, real coding exchange or causal learning. Preserve the evidence ladder and existing dirty worktree.

Stop after the one-time non-mutating capability inventory. No agent turn, source edit, test, build, network call, commit, push or promotion is authorized by this record.
