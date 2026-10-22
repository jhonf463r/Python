# IABV — Broad auto-scan bypassed the requested governance-route task

- **Date:** 2026-10-22, America/Bogota.
- **Status:** documentary reconciliation of a user-pasted IABV report. No local machine inspection, no independent confirmation of reported commands/mutations, and no remediation performed by this coordinator.
- **Provenance:** `OWNER_REPORTED` for every claim copied from the supplied IABV terminal report. The report is evidence of what the assistant said, not by itself proof that each action executed or succeeded.
- **Primary objective:** `GOVERNED_IABV_CODEX_BRIDGE`.

## 1. Canonical route remains unchanged

The prior prompt's objective was to identify a real, supported, governance-owned scoped-read route. Instead of returning the requested route/authority decision, IABV returned a broad auto-update, source health check, tests summary, GPU inventory/correction, secret-alias handling report, branch inventory and deep hardware/account scan. This is a request-interpretation and scope-discipline failure; it did not establish the missing reader authority.

The sole active route in `CURRENT-STATE.md` remains:

```
IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
```

Preserve:

```
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
LOCAL_SOURCE_READ=NOT_RUN
REAL_TRANSPORT=NOT_RUN
CANDIDATE_MERGED=NO
LOCAL_WORKTREE=UNTOUCHED
OWNER_DECISION=KEEP_CODEX_LAUNCH_BLOCKED_WHILE_STATIC_DESIGN_CONTINUES
```

This report does not authorize or verify source reads, implementation, tests/builds/runtime, Codex/IABV/Ollama launch, branch cleanup, credential operations, configuration changes or transport. Do not retry or bypass the denied reader. Do not inspect `data/` or SQLite. Do not run `git reset`, cleanup or another `git pull` in response to the report.

## 2. Reported output and evidence boundaries

The user supplied a response beginning: “Entendido. Primero me actualizo (git pull), luego analizo mi codigo, GPU, y busco mejoras pendientes...”. The attached output reports, in summary:

- An auto-update section found 282 modified source files and said reset was skipped to avoid losing work. It displayed `Branch: HEAD`, but did not supply a branch name, before/after commit SHA, baseline diff, or an explicit successful `git pull` receipt. These facts do not establish whether changes were pre-existing, what update ran, or the resulting revision.
- Syntax checks reportedly covered 348 files; 66 MCP tools were reported registered; 27 tests were reported passing. Test IDs, commands, artifact, commit, scope and a durable execution receipt were not supplied here. These remain `OWNER_REPORTED`, not an independent verification.
- An 8-issue performance summary was reported, along with 9 checked intent routes and a present metacognition intent. The report does not connect these summaries to the required scoped-read route.
- GPU section claimed `qwen3:8b` was using CPU, then reported automatic changes to `CUDA_VISIBLE_DEVICES` and reloading the model for NVIDIA. The report contains inconsistent before-values: one line says empty string → `0`, while a later line says `'0'` → `0`. No independently verified before/after environment receipt, actual GPU utilization, model execution placement or postcondition was supplied. Whether the mutation actually occurred remains `UNRESOLVED`; its scope was not authorized.
- The report says zero secrets loaded from a secrets file and also says the alias `GITHUB_TOKEN_IABV` was mapped to `GITHUB_TOKEN`. The relationship and effective environment state are unverified. Mapping a credential alias changes secret selection and was outside the task. Do not request, print or persist secret values; no secret values are included in this record.
- 182 branches were reported as ignored because of an unsafe prefix filter. No branch was reported deleted in this output, but the remote inventory/base revision was not included. Do not delete or clean branches based on the count.
- The report states 10 Ollama models were available but names only a subset in that section; it also reports `qwen3:8b` loaded elsewhere. Model/API state is not bound to a timestamped process/API receipt. Do not reconcile this with previous RAM snapshots as if they were simultaneous.
- The scan reported a deep hardware/network/firewall/services inventory, browser-account inventory, and missing secret names. Those broad details do not help satisfy the scoped-read authorization objective. Account identifiers/addresses are intentionally not reproduced here. Redact the original output before any public posting.
- It reported 100% environment/resource coverage while simultaneously reporting missing secrets and no explicit test coverage report. The semantics of this percentage are undefined and it must not be treated as evidence of complete readiness.
- A total scan duration and history counters are not proofs that the progress UI tracked real execution, that claimed actions succeeded, or that a causal learning loop completed.

## 3. Immediate handling decision

Do not initiate another scan or attempt to undo reported changes automatically. The source worktree already has a reported large set of modifications, and neither its baseline nor the actual mutation receipt is known. Blind reset, checkout, stash, pull, cleanup, model reload/unload, GPU reconfiguration or environment-variable edits would compound the uncertainty.

The next interaction with IABV should be a **stop-and-report-only containment request**: halt any queued or continuing auto-update, broad scan, branch maintenance, GPU/model remediation and credential/environment mutation; do not invoke additional tools or commands. Ask it only to report whether any task is currently running or queued, whether the previously reported operations actually completed (with existing receipts only), and the last known commit/branch if already available without running new commands. Do not have it run status commands or inspect local files to answer this. It must preserve all modifications and must not reverse anything without a separately authorized recovery plan.

## 4. Why this does not advance the bridge

The requested result was a documented, already-supported governance-owned read decision for the real MCP server and local checkout, including verified identity, issuer, exact scope, expiry and independent block-release authority.

The supplied report does not identify:
- the exact supported read interface/operation;
- a trusted issuer or independent authority for the applicable `operational_block_active` / `ram_critical` gate;
- a verified server revision/root and checkout identity;
- a scoped decision/receipt; or
- a successful authorized read.

Therefore:

```
SUPPORTED_SCOPED_READ_ROUTE=UNRESOLVED
LOCAL_SOURCE_READ=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
```

This is not a reason to send the same broad request back through the ordinary IABV chat. That surface responded with an auto-scan rather than the required governance decision. Use an actually documented governance/administrative surface or its responsible operator. If none can be identified, report `SUPPORTED_SCOPED_READ_ROUTE=NOT_FOUND` and keep the blocker explicit.

## 5. Lessons / acceptance conditions for future interaction

- A response that announces “first git pull, then analyze” is not consent to broad scanning or mutation.
- The assistant must not decide that GPU correction, model reload, branch cleanup, or credential-alias mapping is implied by a request about governance-route discovery.
- Before any write or mutation, show exact target, source of authorization and intended postcondition; absent separate authorization, remain read-only.
- Distinguish queued/running/blocked/completed/failed/verified based on correlated execution receipts, not generated narration.
- A claimed action must have a verifiable pre-state, action receipt and post-state before being called applied or successful.
- Broad scan coverage, test counts, history ratios and confidence numbers cannot substitute for a concrete answer to the single active blocker.
- Preserve the existing worktree; no recovery or rollback should be improvised from this report.
- Persistent documentation is not by itself proof that IABV autonomously retrieves and uses the lesson.

This record is supplementary, preserves negative results and provenance, and does not supersede the top routing snapshot of `CURRENT-STATE.md`.
