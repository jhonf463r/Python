# BIO-R15E — Learned Preference → Real ToolCard / Adapter Runtime

## Scope and identity

This is a three-condition runtime experiment on a clean worktree based on `23f17bd2a1895fe12412f20884951cc0b5ccebfa`. It does not rerun BIO-R15D, change production, alter the harness from a prior experiment, open an external assistant, or perform a live external action. The single new test executes the R15E control, treatment, and trace-only negative control in separate temporary SQLite workspaces, then deletes those temporary workspaces.

Branch: `codex/bio-r15e-toolfcard-adapter-runtime-2026-09-22`.

## Runtime route exercised

Each condition enters the real `AutonomousEvolutionService.plan_or_execute` → `ToolTeachService.execute_external_consultation` → `build_task_from_request` → `execute_task` path. The real `ToolRegistry.pick_card_for_task` selects and refreshes the requested card, and the real `ExternalAssistantToolAdapter.is_available` predicate is called. Observers around registry selection, refresh, and availability delegate to their original implementations without changing arguments or results. `execute_task` then calls the resolved adapter's `run(..., sandbox=True)` boundary; the observer records the call and immediately returns a safe synthetic sandbox result. It does not invoke the adapter implementation body. The approval gate then returns `waiting_approval` before any non-sandbox call.

To retain the committed card declarations, the harness loads the three tracked ToolCard JSON blobs from the experiment base into each isolated registry before execution. It does not construct replacement cards or force availability. The original declarations were `chatgpt_web_assisted=true`, `chatgpt_installed=false`, and `codex_installed=false`. The real adapter availability predicate returned `true` for all three in this Windows session, and registry refresh persisted that observed predicate result. This records the current predicate result only; it does not establish that the target desktop app is installed, authenticated, launchable, or usable.

## Conditions and observations

| Condition | Learning / recommendation | Real task and selected card | Adapter and terminal |
|---|---|---|---|
| Control | BIO-R15B outcome `FAILED`, no promotion; recommendation and preferred assistant `chatgpt` (`language_understanding`, `chatgpt-baseline`, score `0.964`) | `chatgpt_web_assisted`; card assistant `chatgpt`, adapter key `external_assistant`, `web_assisted`, `dom_capture`; declared available `true`, refreshed `true` | Real adapter resolved; `is_available=true`; `run(sandbox=True)` call reached spy and received synthetic success. Terminal `prepared` / `waiting_approval`, `sandbox_pass`, approval `pending`. |
| Treatment | BIO-R15B outcome `VALID`, promoted; recommendation and preferred assistant `codex` (`code_agent`, `codex-sandbox`, score `1.0306`) | `codex_installed`; card assistant `codex`, adapter key `external_assistant`, `desktop_app`, `clipboard_capture`; declared available `false`, refreshed `true` by the adapter predicate | Same real adapter class resolved; `is_available=true`; `run(sandbox=True)` call reached spy and received synthetic success. Terminal `prepared` / `waiting_approval`, `sandbox_pass`, approval `pending`. |
| Negative control | BIO-R15B outcome `FAILED`, no promotion, changing only `trace_id`; recommendation and preferred assistant remain `chatgpt` | Same `chatgpt_web_assisted` ToolTask and ToolCard route as control | Same adapter call boundary observed by the spy; synthetic sandbox result and `waiting_approval` terminal state match control. |

The treatment changed both the actual `ToolTask.tool_id` and the exact ToolCard selected relative to control. The negative control matched control on recommendation, decision, requested assistant, task tool ID, and card tool ID. This supports a causal claim through real task construction, registry selection/refresh, adapter availability checking, and reaching the resolved adapter's `run` call boundary. The observer, not the adapter implementation, returned the synthetic result.

## Classification and first stopping edge

**CAUSALLY_CONFIRMED** for the bounded claim “the learned preference determines which real ToolTask/ToolCard is selected and reaches the resolved adapter's sandbox `run` invocation boundary.” The control/treatment change follows the learned outcome; trace-only negative control does not. The test's differential explicitly checks both task and ToolCard identity. `DEFINED | WIRED | INVOKED | OBSERVED | CAUSED` is supported through this intercepted call boundary; the adapter implementation itself is deliberately not invoked.

The first unclosed continuation is sandbox validation → non-sandbox adapter call. `ToolApprovalPolicy` stopped it: the synthetic sandbox result passed validation, but task approval remained `PENDING`; `execute_task` returned `waiting_approval`. For that continuation, `DEFINED | WIRED | OBSERVED` (the gate and stop) are established; `INVOKED | CAUSED` are not. The actual browser/desktop adapter implementation and any external action were neither invoked nor caused.

## Safety and epistemic limits

- No browser or desktop assistant was opened; no clipboard was read or written; no HTTP request, prompt delivery, external response, or external-agent consumption occurred.
- No production file, ToolCard source JSON, runtime availability flag, or adapter implementation was changed. Every call to the resolved adapter's `run` boundary was intercepted and returned a synthetic payload immediately. The real adapter implementation body, non-sandbox run, browser, desktop app, clipboard, HTTP, and external effects were not executed.
- `is_available=true` is the return value of the real adapter predicate in this runtime. It is not proof of actual executable presence, usable desktop integration, authentication, successful launch, prompt submission, response capture, or useful output.
- The test passed in the recorded environment. Cross-machine / future runtime availability and actual post-approval adapter behavior remain `UNRESOLVED`.

## Reproduction

Environment: Windows 11 build `10.0.26200`, Python `3.13.2` Anaconda, 64-bit. Exact PowerShell command and complete test stdout are preserved in `BIO-R15E-TOOLCARD-ADAPTER-STDOUT-2026-09-22.txt`. Result: `1 passed in 7.80s`, exit code `0`. Set `PYTHONDONTWRITEBYTECODE=1` for a repeat to keep bytecode out of the checkout; the experiment itself does not rely on that variable.

The test file and this report are the entire source/documentation change set for this experiment; production remains untouched.
