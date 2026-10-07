# CHAT-ARCH-2026-10-07-118 — UAAL/RQ15 READINESS HARNESS VERIFIED

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / PROVENANCE / WINDOWS-ORACLE / AUTHORIZATION`

## Trigger

Episode 117 stopped before the RQ15 sensor because the provenance literal and independent oracle gates were not satisfied. A harness-only correction was then required before any new live observation.

## FACT

External harness:
`C:\temp\rq15_readiness_gate_20261006.py`

Reported SHA-256:
`AE9599922D18070BFA308790B39CFA2BDDE54900810BBAF93D03A0CAC8E197F3`

Size:
`10,853` bytes.

Target provenance was reverified:
- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- focal blob `f420ec48c05d02602954c84d5fba410198f4b58c`
- helper blob `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`
- worktree clean before and after.

Python provenance was checked against the literal declared for this execution:
- path `C:\Users\faber\miniconda3\python.exe`
- version `3.13.2`
- SHA-256 `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

Helper SHA-256 declared/observed:
`3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`.

Static resolution placed the helper under the authorized `src` root. `psutil` was locatable without import.

Syntax self-test:
`SYNTAX_OK`.

Parser fixtures:
- valid identity;
- invalid JSON;
- missing timestamp;
- invalid PID;
- timestamp without timezone.

All parser fixtures passed.

Fail-closed gate self-tests produced:
- `PROVENANCE_NOT_READY`
- `ORACLE_NOT_READY`
- `AUTHORIZATION_REQUIRED`

All failed closed with:
`sensor_call_count = 0`.

No IABV import, AppBootstrap, MCP, CIM/Win32 live query or sensor invocation occurred. No source/test changes occurred and the target worktree remained clean.

## WHAT CLOSED

The RQ15 readiness harness is now verified for Phase A.

Closed:
`declared artifact provenance → exact observed provenance`

Closed:
`parser fixture contract → fail-closed gate behavior`

Closed:
`missing provenance/oracle/authorization → sensor blocked`.

## WHAT REMAINS OPEN

The actual correspondence edge remains completely unobserved:

`independent OS process → existing audit_tools_observation.list_running_processes`

There is still no live PID/create_time comparison.

The live Windows oracle itself has not yet been demonstrated in this episode because Phase A intentionally stopped before live observation.

## EPISTEMIC CLASSIFICATION

Readiness:
`READY_FOR_FRESH_AUTHORIZATION`

Runtime correspondence:
`NOT OBSERVED`.

This is **not** evidence of sensor correctness, sensor failure, environmental absence, mismatch or semantic integration.

## KNOWLEDGE DELTA

1. Exact per-execution provenance can be enforced without silently reusing a previous digest.
2. Oracle parsing can be validated independently with local fixtures before any live query.
3. Authorization can be made a hard gate independent of parser/provenance readiness.
4. Phase-A harness correctness can be established while keeping the production sensor unreachable.
5. Readiness completion and runtime evidence are distinct epistemic states.

## METHOD DELTA

The bounded-experiment sequence is refined to:

`exact provenance`
→ `static sensor resolution`
→ `oracle parser self-test`
→ `fail-closed gate self-test`
→ `fresh human authorization`
→ `live independent oracle`
→ `existing sensor invocation`
→ `comparison`.

A readiness result must not be converted into runtime correspondence evidence.

## ROUTING DELTA

The harness-only route is closed.

Current first open edge remains:

`independent OS process → existing IABV process observation helper`.

Capability-fit actor for the eventual live probe remains **CODEX** because the remaining work is Windows runtime execution and provenance-bounded observation.

## AUTHORIZATION BOUNDARY

No fresh authorization is inferred from earlier episodes.

A new authorization must explicitly cover:
- target `8425f03eb45abd11951938f6e3234459c1585b55`;
- exact harness identity;
- exact Python executable and digest;
- exact helper identity/digest;
- direct invocation of `audit_tools_observation.list_running_processes` outside MCP governance;
- one independent Windows process oracle;
- one bounded synchronized observation only.

Until that authorization exists, no live sensor or oracle run is authorized by this episode.

## STOP CONDITIONS FOR THE NEXT EPISODE

Before sensor invocation, stop on any provenance mismatch or missing oracle identity.

During live observation, stop on:
- target provenance drift;
- inability to establish independent oracle identity;
- unexpected production import/lifecycle activation;
- MCP/AppBootstrap/WorldModel/ToolRegistry/provider/network/persistence activation;
- sensor call count > 1;
- inability to compare `PID + create_time`.

No production implementation is justified by this readiness result.
