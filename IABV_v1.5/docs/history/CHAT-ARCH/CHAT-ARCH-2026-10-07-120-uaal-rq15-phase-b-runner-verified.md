# CHAT-ARCH-2026-10-07-120 — UAAL/RQ15 PHASE-B RUNNER VERIFIED

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / HARNESS-CONTRACT / WINDOWS-RUNTIME / AUTHORIZATION`

## Trigger

Episode 119 identified that the authorized Phase-A harness was not capable of executing the authorized Phase-B live observation. A distinct external Phase-B runner was then created and self-tested without executing the live oracle or sensor.

## FACT

Phase-B runner:

`C:\temp\rq15_phase_b_runner_20261006.py`

SHA-256:

`15DF88E873E9CF7288ABFBDFD066C14D98E089774D14C3ECC14CA51400BF6979`

Size:

`23,324` bytes.

Target:
- worktree `C:\temp\wm-synaptic-8425`
- application `C:\temp\wm-synaptic-8425\IABV_v1.5`
- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- focal blob `f420ec48c05d02602954c84d5fba410198f4b58c`
- helper blob `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`
- helper filesystem SHA-256 `3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`
- worktree clean before and after.

Python:
- executable `C:\Users\faber\miniconda3\python.exe`
- version `3.13.2`
- SHA-256 `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

Phase-A:
`SYNTAX_OK`
and
`PHASE_A_SELF_TEST_PASS`.

Fail-closed cases:
- provenance mismatch → `PROVENANCE_NOT_READY`, sensor calls 0;
- invalid oracle fixture → `ORACLE_NOT_READY`, sensor calls 0;
- missing authorization → `AUTHORIZATION_REQUIRED`, sensor calls 0;
- malformed target identity → `TARGET_NOT_READY`, sensor calls 0;
- Phase-B path present but disabled → `PHASE_B_AVAILABLE_BUT_NOT_EXECUTED`, sensor calls 0.

The runner contains an explicit connected Phase-B path:

`provenance → independent Windows CIM oracle → identity/authorization gates → one guarded existing helper call → post-oracle → PID/create_time comparison`.

The oracle path is implemented but was not executed in this episode.

The existing IABV sensor was not invoked.

`live_oracle_called = false`
`live_sensor_called = false`
`sensor_call_count = 0`.

No `iabv_v15` import, AppBootstrap, MCP, WorldModel, provider/network activity or persistence occurred.

## WHAT CLOSED

Closed:
`Phase-A readiness harness`

Closed:
`runtime-capable Phase-B runner availability`

Closed:
`Phase-B path structural/self-test contract`

The external runner is now distinct from the readiness-only artifact.

## WHAT REMAINS OPEN

The actual runtime correspondence remains unobserved:

`independent Windows process identity → existing audit_tools_observation.list_running_processes`.

Neither the live Windows oracle nor the live sensor has yet executed in the Phase-B runner.

## EPISTEMIC STATUS

`PHASE_B_RUNNER_READY`

does not imply:

`LIVE_ORACLE_OBSERVED`

and does not imply:

`SENSOR_OBSERVED`

and does not imply:

`CORRESPONDENCE_PROVEN`.

## KNOWLEDGE DELTA

1. Phase-A and Phase-B artifacts are now explicitly separated.
2. A runtime-capable Phase-B path can be structurally self-tested while keeping live execution disabled.
3. The exact authorized action must bind the runtime-capable runner artifact, not merely a readiness artifact.
4. Self-test evidence remains non-live evidence.

## METHOD DELTA

Refined experiment lifecycle:

`Phase-A readiness`
→ `Phase-B capability self-test`
→ `exact artifact identity`
→ `fresh authorization`
→ `live oracle`
→ `single sensor invocation`
→ `independent post-oracle`
→ `identity comparison`
→ `reconciliation`.

## ROUTING DELTA

Current first open edge remains:

`independent Windows process identity → existing IABV process observation helper`.

Immediate readiness/authorization edge:

`exact Phase-B runner identity/capability → fresh human authorization`.

Next capability-fit actor remains **CODEX** for the eventual live execution.

No live execution is authorized by this episode.

## AUTHORIZATION REQUIREMENT

A new authorization must explicitly bind:

- runner path `C:\temp\rq15_phase_b_runner_20261006.py`;
- runner SHA-256 `15DF88E873E9CF7288ABFBDFD066C14D98E089774D14C3ECC14CA51400BF6979`;
- target HEAD `8425f03eb45abd11951938f6e3234459c1585b55`;
- target tree `1d46e59195d01c1cec6806f264ef75f31541e806`;
- Python executable and SHA;
- helper identity;
- independent Windows CIM/Win32 oracle;
- direct invocation of `audit_tools_observation.list_running_processes` outside MCP governance;
- maximum one sensor observation;
- read-only scope.

Until that authorization is explicitly present, the runner must remain in non-live mode.

## STOP

No production implementation is justified.
No new observer is justified.
No WorldModel/PerceptionSnapshot/ToolRegistry/selection/learning experiment follows yet.
