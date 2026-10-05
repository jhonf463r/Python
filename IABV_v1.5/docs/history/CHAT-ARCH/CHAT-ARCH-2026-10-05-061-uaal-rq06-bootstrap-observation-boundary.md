# CHAT-ARCH-2026-10-05-061 — UAAL-RQ06 Bootstrap / Observation Boundary Reconciliation

**STATUS:** CANONICAL RECONCILIATION / RQ06 STOPPED BEFORE RUNTIME

## RESULT

RQ06 did not start a candidate MCP process because canonical MCP startup constructs `AppBootstrap(workspace_root=...)` with default `_defer_services=False`.

Static source inspection confirms that the normal wiring path requests:

`EnvironmentSelfAwarenessService.request_refresh(reason='role_router_ready', full=False)`

and:

`WorldModelService.request_refresh(reason='role_router_ready', full=False)`

during service wiring.

Therefore a fresh MCP launch naturally performs bootstrap-time refresh work before `cognitive_frame_translate` can be invoked.

RQ06 correctly stopped rather than:
- suppressing those startup refreshes without understanding their semantics;
- attributing a startup scan to the later observation tool;
- treating an unstarted process as runtime evidence.

## RQ05 CANDIDATE STATUS

The RQ05 candidate remains an isolated, uncommitted worktree change against code-bearing baseline:

`e46d8304167708bed0764d3bf2be8fd6643e8944`

Candidate behavior reported by Codex:
`build_perception_snapshot(refresh=False)`
with portable-context reconstruction excluded from the safe observation path.

Focused/related tests:
`19 passed`

This remains candidate evidence, not canonical runtime proof.

## NEW CAUSAL BOUNDARY

The missing experiment is no longer simply:

`start fresh MCP → call tool`.

It is:

`bootstrap startup refresh phase`
→
`bootstrap completion / baseline boundary`
→
`safe observation call`
→
`PerceptionSnapshot`
→
`post-call refresh accounting`.

The experiment must distinguish **bootstrap-induced observation activity** from **tool-induced refresh**.

## IMPORTANT METHOD DELTA

A runtime experiment may allow normal initialization side effects when they are part of the product's existing startup contract, provided the experiment explicitly partitions them from the observation under test and does not misattribute them.

Therefore:

`startup refresh ≠ tool refresh`

and:

`fresh process ≠ clean observation`

unless the phases are measured separately.

The correct test is not to suppress bootstrap behavior blindly. It is to establish a measurement boundary after bootstrap has completed.

## CURRENT OPEN EDGE

`fresh candidate process → bootstrap boundary → candidate tool invocation → no tool-induced refresh → live PerceptionSnapshot correlation`

## REQUIRED CAPABILITY

`phase-separated runtime attribution of an existing MCP observation path`

## ROUTING

**NEXT ACTOR: CODEX**

Reason:
This is a bounded technical/runtime experiment requiring process startup, source provenance, MCP invocation and refresh-call attribution.

Do not route to Sonnet/Claude before a runtime candidate artifact and observation exist.

Do not route to Devin unless Codex encounters a concrete Windows host/process limitation.

## PRODUCT CONTEXT

This remains a prerequisite for the broader target:

`HUMAN ↔ IABV`

with external AIs such as ChatGPT/Codex/Claude functioning as governed resources selected by IABV.

RQ06 is not itself the product objective; it is a narrow capability/evidence seam.

## NEXT EXPERIMENT

Use the existing candidate without further architectural expansion.

Start one fresh candidate MCP process.

Permit normal bootstrap behavior.

Record the complete bootstrap phase separately.

Only after bootstrap completion, install observational counters/wrappers on the existing World Model and Environment Self Model `request_refresh` methods, or use equivalent existing telemetry, to measure calls caused during the subsequent observation.

Then invoke `cognitive_frame_translate`.

Capture:
- world snapshot before tool;
- PerceptionSnapshot returned by the tool;
- world snapshot after tool;
- request_refresh call counts during the tool phase;
- process/module/source provenance.

The primary claim to test is:

`tool invocation → zero additional request_refresh calls`

not:

`entire fresh process → zero refreshes`.

The latter is false by existing startup behavior and is not the contract being tested.

## STOP CONDITION

Stop if:
- bootstrap cannot be separated from tool execution;
- the candidate process cannot be attributed;
- the tool cannot be invoked;
- instrumentation changes the behavior materially;
- the returned PerceptionSnapshot cannot be correlated with the live World Model.

Do not modify bootstrap merely to make the experiment easier.

