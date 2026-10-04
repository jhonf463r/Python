# CHAT-ARCH-2026-10-04-048 — IABV → CODEX REAL DISPATCH FRONTIER

## OBJECTIVE
Demonstrate the smallest real production causal chain in which IABV identifies a technical consultation need, selects the Codex realization, dispatches through the existing external-assistant path, captures the response with verified session provenance, and returns the result to IABV without manual copy/paste.

## CURRENT VERIFIED SOURCE STATE

Verified on remote `main` at the current canonical state:

- `ToolRegistry` contains `codex_installed` with `assistant_kind=codex` and `adapter_key=external_assistant`.
- `ToolTeachService._preferred_external_tool_id()` can resolve technical categories/incidents and explicit Codex requests to `codex_installed`.
- `AutonomousEvolutionService._assess()` routes `need_codex_fix`, `need_adapter` and defined technical incident kinds to `consult_codex`.
- `AutonomousEvolutionService.plan_or_execute()` calls `ToolTeachService.execute_external_consultation()`.
- `ToolTeachService.execute_task()` performs adapter availability, governance, sandbox and execution handling.
- `ExternalAssistantToolAdapter` wraps the external-assistant path and stamps worker telemetry.
- Codex capture has a dedicated `codex_rollout` lane and isolated `CODEX_HOME`/session paths; response capture can use session rollout and thread verification.
- `IABV_AUTONOMOUS_EXTERNAL_LAUNCH` defaults to enabled in current config.

## GOVERNANCE BOUNDARY

`codex_installed` is configured with `requires_human_approval=True`. Therefore the current path is not fully autonomous in the sense of bypassing human approval. The first real proof must preserve this gate; do not weaken or remove it.

## NOT PROVEN

- real Windows production invocation of the IABV decision path selecting Codex and reaching the actual Codex process;
- verified rollout capture from that production run;
- response ingestion changing a later IABV decision in the same causal episode;
- autonomous actor selection from an unprompted natural environmental deficit;
- autonomous runtime use of GitHub memory as a live control bus.

## FIRST OPEN CAUSAL EDGE

`IABV production decision → existing AutonomousEvolutionService → codex_installed → ExternalAssistantToolAdapter → real Codex launch → verified response capture`.

## MINIMUM DISCRIMINATING EXPERIMENT

Run one harmless, read-only Codex consultation through the real production runtime on Windows.

The test must:

1. use the exact published `main` SHA selected for the run;
2. create only a bounded diagnostic condition that is already supported by the production code path (`need_codex_fix` or an existing technical incident classification);
3. let the existing selection logic choose `codex_installed` rather than hard-coding the final tool at the execution call-site;
4. keep the existing approval gate intact and obtain explicit user approval at the gate;
5. send a harmless no-write prompt to Codex, such as an instruction to inspect/read only and return a fixed acknowledgment;
6. require response capture through the existing Codex rollout/session-verification path; clipboard alone is not sufficient when rollout verification is expected;
7. preserve task/result/session/thread/rollout provenance and the complete execution state;
8. stop immediately on the first causal break.

Do not change code unless the experiment reveals a concrete blocking seam. If a source change is required, stop before implementation and report the exact missing ownership/wiring edge for a separate implementation decision.

## SUCCESS CONDITION

Minimum success is one traceable episode proving:
`IABV decision → Codex selected → Codex launched → Codex produced response → response captured by the existing verified Codex session lane`.

This proves real dispatch/capture, not learning or autonomous developmental reuse.

## NEXT EDGE AFTER SUCCESS

`captured Codex response → IABV ingestion → verified downstream state/decision change`.

Independent verification should occur after the runtime artifact exists.

END OF RECORD