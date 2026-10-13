# CHAT-ARCH-2026-10-13-236 — App Server task identity breaks before consumer acceptance

Date: 2026-10-13 (America/Bogota)
Classification: Owner-supplied static audit result / causal-edge adjudication / implementation authorization gate.
Canonical baseline at intake: remote `main @ 7fd4d51ebb8d8be415bb6c0d0de7167137f9a108`.
Coverage: one complete Owner-pasted Codex report `APP_SERVER_STATICALLY_BLOCKED`. No local source was independently inspected and no code, tests, processes, network or runtime were executed by this writeback.

## 1. Owner objective and lineage

The objective remains a governed `IABV → Codex → IABV` development handoff, followed by the separate D016 code-evolution loop. Preserve `UAAL-ROOT-001`, RQ128, M0-A versus M0-B, and the distinction between receipt persistence, consumer evaluation and causal reuse.

## 2. Local state — OWNER_SUPPLIED_REPORT

The report states:
- worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`;
- branch `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`;
- 56 tracked modifications and 5 untracked items preserved;
- no edits or tests during that inspection.

These values are actor-reported, not remeasured here. Preserve every modified and untracked file, including reported `.pyc` changes. The local patch is not part of remote `main`.

## 3. First concrete blocker: task identity changes after SafeUI authorization

The supplied static report says SafeUI creates and approves a `task_id` and passes it as `safe_ui_single_use_task_id`. `ToolTeachService.build_task_from_request` reuses that value only for `chatgpt_web_assisted`, `openai_api_text` and `ollama_llm`; for `codex_app_server` and `codex_installed` it generates a new UUID. The SafeUI caller then compares the returned task ID with the authorized ID only after `execute_external_consultation()`, which may already have dispatched the external prompt.

This can create a dangerous split outcome: an external effect may occur, while SafeUI subsequently rejects its result as not belonging to the authorized task. The App Server adapter reportedly does not independently validate the original authorized task ID before dispatch.

Therefore the current first code-level edge is:
`authorized SafeUI task_id → ToolTeachService task creation → adapter dispatch`.
The identity must remain stable, and any missing/mismatched task identity must fail closed **before any adapter dispatch or external side effect**.

## 4. Required first repair — separate authorization needed

The smallest next implementation tranche should be limited to the task-identity contract for both `codex_app_server` and `codex_installed`:
1. Preserve the SafeUI-authorized task ID through task construction for both destinations.
2. Reject missing, malformed or mismatched authorization/task IDs at the earliest authoritative boundary, before `execute_external_consultation()` reaches an adapter.
3. Add adapter-side defensive validation wherever the current call contract makes the original authorized ID available, without inventing a parallel authorization mechanism.
4. Add focused synthetic tests proving the ID is unchanged for both Codex destinations and mismatch/missing-ID cases result in zero adapter dispatches.
5. Add a narrow regression assertion that existing destination ID behavior remains correct.
6. Run only relevant offline tests and `git diff --check`, under the repo's no-bytecode/no-pytest-cache pattern, **only after the Owner separately authorizes the source-edit/test phase**.

Do not combine this repair with authentication setup, App Server invocation, tool-policy redesign, desktop capture, D016 self-mutation or additional provider work. Inspect the exact current code and worktree first. Make the smallest change; preserve all unrelated modifications. No commit or push unless separately authorized.

## 5. Remaining independent blockers after task-ID repair

- **Authentication / no-extra-cost mode:** `IABV_CODEX_HOME` is passed to the adapter, which launches Codex CLI App Server with a restricted child environment and no API key. The content/auth mode and entitlement of that home remain unknown. Do not inspect credentials. Static source cannot prove a valid signed-in session or available quota.
- **Adapter preflight:** the adapter's own `preflight()` checks an empty home, initialization, config read and MCP inventory; reported normal SafeUI dispatch does not call that method. Its implications must be source-reviewed before any runtime route is selected.
- **Pre-effect tool policy:** the turn asks for read-only access and an empty temporary directory, but no effective tool-disable list or guaranteed pre-effect denial was established. Rejecting server approval requests or tool events after receipt is not proof that effects were prevented before execution.
- **Result consumer:** the route persists a `ToolResult` and can feed `ingest_external_response`; the supplied audit did not execute that path. Consumer evaluation remains unproven.
- **Desktop route:** `LAUNCH_PROVENANCE_UNAVAILABLE` remains the separate state for the already-running GUI capture-home binding. Do not repeat invasive process inspection.
- **Global self-mutation authority:** RQ218/RQ223/RQ224 workspace, baseline, allowlist and operation/resource/scope receipt gates remain open. A successful consultation does not authorize code mutation or promotion.

## 6. Acceptance boundary

After the identity repair alone is validated synthetically, do not immediately dispatch to Codex. The next gates are to establish the existing auth mode without extra spend, decide a safe task-specific tool policy, and separately authorize any runtime check. A real M0-A pass still requires exactly one approved dispatch, a terminal response from the same task/thread, consistent IDs, correlation, ingestion and observed evaluation by the existing consumer.

D016 remains a separate requirement: isolated reversible code variant, comparable baseline tests, independent verification and governed promote/reject/rollback. Later causal reuse needs its own non-identical task and observable decision impact.

## 7. Next routing

Current incoming result: `APP_SERVER_STATICALLY_BLOCKED`.
Current first code-level defect: `CODEX_SAFE_UI_TASK_ID_NOT_PRESERVED_PRE_DISPATCH`.
Recommended next actor/action: Owner authorization → narrow source-edit and focused synthetic-test repair for the task identity only.
No source modification, tests, process, network, prompt dispatch, credential inspection, API setup or extra spending is authorized by this documentation record.
