# CHAT-ARCH-2026-10-13-263 — M0B-R3 architecture adjudication: Codex bridge first, preserve existing route

- **Episode ID:** CHAT-ARCH-2026-10-13-263
- **Reported time (America/Bogota):** 2026-10-13, 18:08 (Owner-supplied report)
- **Reconciled published baseline:** `main @ 708c8fc408b74bf03ed681afccedcdde3bcc37b4`
- **Input:** Owner-supplied M0B-R3 report + independent static spot-check of public main and current official OpenAI documentation
- **Classification:** `M0B_R3_STATIC_ARCHITECTURE_DIRECTION_CONFIRMED_WITH_EXISTING_UI_BRIDGE_REASSESSMENT_REQUIRED`
- **Posture:** `KEEP_BLOCKED`
- **Priority edge:** `LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED`
- **Governance edge:** `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`
- **Architecture edge:** `CODEX_BRIDGE_ROUTE_REASSESSMENT_REQUIRED`
- **Secondary edge:** `CHATGPT_AUTOMATIC_TURN_AND_CORRELATED_RETURN_UNRESOLVED`

## 1. M0B-R3 adjudication

Owner-supplied M0B-R3 recommends Codex App Server as the direct candidate for `IABV → Codex → IABV`, while leaving authentication/entitlement, confinement, event correlation, result consumer and the local wiring unproven. It identifies an important limitation of the inspected Workspace Agents API trigger: it returns `202 Accepted` without a response body or run ID, and the agent response is not retrievable through that API. Treat those API properties as **reported from the cited official docs**, not as runtime-tested here.

The report is a useful static architecture comparison, not proof of a working bridge. It did not inspect the dirty M0A checkout, dispatch a turn, or verify a result consumer. Its proposed M0B-R4 depends on authorized local source inspection after the outstanding governance issue is legitimately resolved.

## 2. Independent public-source correction: do not skip the existing Codex desktop/rollout path

Fresh inspection of published main at the pinned baseline confirms:

- `bootstrap.py` registers `ExternalAssistantToolAdapter` as `external_assistant` and wires `ToolTeachService` with `ToolRegistry`, `ToolSandbox`, `ToolValidator`, `ToolMemory`, approval policy and rollback manager.
- `data/tool_teaching/cards/codex_installed.json` declares `adapter_key=external_assistant`, `launch_mode=desktop_app`, `response_capture_mode=clipboard_capture`, `background_capture_mode=codex_rollout`, `requires_manual_pasteback=false`, and `requires_human_approval=true`; the published card is marked `available=false` and `validation_status=unvalidated`.
- `ToolAdapter._capture_desktop_response` delegates to `UIExecutionRunner.capture_response_from_app`; the runner has a Codex rollout capture path that reads Codex's state database and candidate rollout files.
- `ToolValidator` explicitly treats `response_capture_pending` as `awaiting_response` with `UNVALIDATED`, preventing a pending capture from being represented as a verified success.
- Public logs/records contain cases with `response_capture_pending=true` / `capture_pending`; those are historical repository artifacts, not proof of the present local runtime.

Sources: [bootstrap.py](https://github.com/jhonf463r/Python/blob/708c8fc408b74bf03ed681afccedcdde3bcc37b4/IABV_v1.5/src/iabv_v15/bootstrap.py), [tool_adapters.py](https://github.com/jhonf463r/Python/blob/708c8fc408b74bf03ed681afccedcdde3bcc37b4/IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py), [ui_execution_runner.py](https://github.com/jhonf463r/Python/blob/708c8fc408b74bf03ed681afccedcdde3bcc37b4/IABV_v1.5/src/iabv_v15/services/tools/ui_execution_runner.py), [tool_validator.py](https://github.com/jhonf463r/Python/blob/708c8fc408b74bf03ed681afccedcdde3bcc37b4/IABV_v1.5/src/iabv_v15/services/tools/tool_validator.py), [Codex card](https://github.com/jhonf463r/Python/blob/708c8fc408b74bf03ed681afccedcdde3bcc37b4/IABV_v1.5/data/tool_teaching/cards/codex_installed.json).

The public branch does not contain `CodexAppServerToolAdapter` in `tool_adapters.py` or its registration in `bootstrap.py`; earlier owner reports place that candidate in the separate dirty local M0A branch, but that claim has not been independently verified. Therefore App Server is a strong architectural candidate, not an automatic winner over the existing desktop/rollout path. The next source comparison must decide whether to reuse/repair the existing UI/rollout capture route, integrate the local App Server candidate through the ordinary task pipeline, or keep both as separate modes.

## 3. ChatGPT integration boundary

Current official OpenAI plugin documentation states that plugins can expose MCP server-backed capabilities to both ChatGPT and Codex. This suggests that a controlled IABV MCP service could serve as a shared tool surface, subject to connection, account/workspace availability, authentication and security checks. It does not by itself let the IABV process initiate an arbitrary new ChatGPT conversation or retrieve a ChatGPT session's response without an established callback/trigger path.

Official source: [OpenAI MCP server quickstart](https://developers.openai.com/plugins/build/app-quickstart). The Workspace Agents API response limitation cited in M0B-R3 remains a separate constraint; a callback MCP design is a candidate only until its trigger and task-correlation contract are demonstrated. An API-backed model path may be technically straightforward but must not be assumed to be included in the user's ChatGPT plan or free of extra cost.

## 4. Evidence classes

- **PROVEN_BY_SOURCE:** public main registers the desktop `ExternalAssistantToolAdapter`; the Codex card specifies UI/clipboard/rollout capture; the UI runner has a rollout reader; the validator marks pending capture unvalidated; the published main lacks `CodexAppServerToolAdapter` in the two fetched registration/source files.
- **OWNER_REPORTED:** M0B-R3 research findings on official API contract; previous reports about the dirty M0A branch and blocked MCP tool.
- **INFERRED:** direct App Server may shorten the Codex handoff, but must be compared with existing UI/rollout path before committing to it; IABV's MCP may be a shared tool surface for both agents.
- **UNPROVEN:** M0A local adapter and wiring; target workspace of `mcp__iabv_v15_rsk01a5`; live Codex auth/entitlement and cost; OS-level confinement; actual result correlation; a ChatGPT trigger-and-return loop; end-to-end autonomy.

## 5. Next route and stop conditions

Do not repeat generic App Server/MCP research or ask the Owner for a manual code dump. The next discriminating local-source audit should compare the actual M0A candidate `CodexAppServerToolAdapter` with the existing `ExternalAssistantToolAdapter` + `UIExecutionRunner` + Codex rollout capture, then trace normal dispatch through `ToolTeachService`/ `ToolRegistry` and the real result consumer. It should be strictly read-only and should not run tests, launch App Server, call CDP, inspect credentials or modify source.

However, the prior audit reader returned an active governance block. **No alternate read path may be used to route around that block.** Local inspection stays on hold until the Owner or authorized Control Center resolves the gate through the intended governance mechanism and the MCP-to-M0A workspace mapping is directly evidenced. Do not disable or clear the genuine memory-pressure guard blindly.

Global objective remains IABV as the governed operational mind: automatically route prompts, collect evidence-backed results, verify them, persist relevant memory, and select the next task across IABV, Codex and ChatGPT. This is a target architecture, not a claim of current end-to-end autonomy.

No code or runtime changed in this adjudication. `KEEP_BLOCKED`.
