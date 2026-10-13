# CHAT-ARCH-2026-10-13-237 — Codex task identity repair passed synthetic tests

Date: 2026-10-13 (America/Bogota)
Classification: Owner-supplied implementation/test report; result code `CODEX_TASK_ID_REPAIR_PASS`; not independently re-run in this documentation pass.
Canonical remote baseline at intake: `main @ 578f2b2daf2609deda062ca9bd22230791a3fbf6`.
Local code evidence: report from the Owner for the existing dirty worktree only. This record does not imply the local patch is on remote `main`.

## 1. Objective and continuity

The objective remains a governed `IABV → Codex → IABV` handoff that preserves exact intent and one-use authorization, correlates the terminal response, and evaluates it through the existing consumer. This is M0-A transport/mediation work; it is not yet proof of M0-B capability selection, D016 code evolution, or causal learning.

## 2. Owner-reported local provenance

The Owner reports the worktree:
`C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`

- Branch: `codex/m0a-safe-ui-boot`
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- 56 tracked files modified and 6 untracked files, including the new focused test
- 38 modified `.pyc` files were already present; no bytecode changes were added by this intervention
- This intervention changed three files: `tool_teach_service.py`, `control_center_viewmodel.py`, and `test_m0a_codex_task_identity_preserved.py` (reported aggregate `+388/-13`)

These are reported measurements and were not remeasured here. Preserve the complete dirty worktree, including unrelated modifications, untracked files and pre-existing bytecode changes. No reset, clean, restore, commit, push, branch switch or code promotion is authorized by this record.

## 3. Repair reported

The original defect was that `ToolTeachService.build_task_from_request` generated a replacement UUID for `codex_app_server` and `codex_installed`, breaking the identity authorized by SafeUI.

The report states that:

1. Both Codex destinations now retain the literal authorized task ID rather than replacing it.
2. Validation requires the SafeUI-generated canonical form: 32 lowercase hexadecimal characters.
3. SafeUI rejects missing, malformed or mismatched IDs and compares the preview task's ID with the authorized operation ID **before consuming authorization and calling `execute_external_consultation()`**.
4. `ToolTeachService` rechecks format and equality before the task can reach the adapter.
5. Existing bindings for destination, approved prompt and prompt digest remain intact; other destinations retain their prior behavior.

A syntactically valid task ID is an identity/correlation value, not a substitute for the authorization checks or their destination/prompt/scope bindings.

## 4. Owner-reported verification

- Focused test command: final execution reported **32 passed**.
- Synthetic doubles reportedly proved zero adapter calls when IDs were invalid or discrepant and checked destination, task and prompt on the valid path.
- `git diff --check` passed.
- New test-file trailing-whitespace check passed.
- The first test-harness attempt had three failures; the report says its test data was corrected and the final run then passed.

This is owner-supplied evidence, not an independent test run in this writeback. No Codex App Server was started, no real query/prompt was sent, and no external round-trip or consumer evaluation was observed.

## 5. Adjudication

The reported result closes the first **synthetic code-level identity defect** for the narrow tested contract, subject to later independent source review. It does not close M0-A end-to-end.

The earlier hazard was effect-before-identity-acceptance: an external request could dispatch and only afterward have its result rejected for a task-ID mismatch. The reported change moves identity rejection ahead of authorization consumption and external consultation, while retaining a second check in `ToolTeachService`.

## 6. Remaining independent gates

1. **Authentication and no-extra-cost entitlement:** identify the exact existing App Server auth mode and selected `CODEX_HOME` without reading credential contents. Static configuration alone cannot prove a live session or remaining quota.
2. **Preflight:** determine what adapter `preflight()` establishes and whether normal dispatch calls the necessary checks.
3. **Pre-effect tool policy:** prove that a text-only task cannot produce unapproved tool effects before execution. Blocking an approval/event after receipt is not sufficient evidence.
4. **Response and consumer:** establish terminal task/thread/turn correlation and observe that the result reaches and is evaluated by the existing consumer, not merely persisted.
5. **Runtime authorization:** any real App Server request remains a separate, explicit decision after the source gates are resolved. No runtime, prompt dispatch, API setup or spend is authorized here.
6. **D016:** isolated candidate code evolution, comparable baseline tests, independent verification, and governed promote/reject/rollback remain separate. Later causal reuse requires a non-identical task with observable impact.

## 7. Next routing

Result: `CODEX_TASK_ID_REPAIR_PASS` (Owner-reported; synthetic only).

First remaining edge: `CODEX_APP_SERVER_AUTH_HOME_PREFLIGHT_AND_EFFECTIVE_TOOL_POLICY_UNRESOLVED`.

Next action: resume a bounded, read-only review of the already-known App Server adapter/configuration/preflight and direct task-tool policy call sites. Trace the existing consumer handoff only as far as source evidence allows. Avoid broad repository archaeology, credential inspection, runtime invocation, network/UI/CDP activity or new edits. Do not repeat the Desktop launch-provenance path. Preserve the dirty local worktree.

Canonical remote source remains the current `main` documentation tree; the local code patch has not been reported as committed or pushed.
