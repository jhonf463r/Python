# CHAT-ARCH-2026-10-07-122 — UAAL/RQ15 EVIDENCE-COMPLETE PHASE-B RUNNER READY

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / EVIDENCE-CONTRACT / WINDOWS-RUNTIME / SYMBIOSIS`

## Trigger

Episode 121 identified that the prior Phase-B runner was runtime-capable but lacked required live evidence fields. A new external evidence-capable Phase-B runner was then constructed and self-tested without live oracle or sensor execution.

## FACT

New runner:
`C:\temp\rq15_phase_b_evidence_runner_20261006.py`

SHA-256:
`E70D9215B4528ECBC315C0DCA0953AD832071F2E57FB255003698569072F5485`

Size:
`33,832` bytes.

Target:
- worktree `C:\temp\wm-synaptic-8425`
- CWD `C:\temp\wm-synaptic-8425\IABV_v1.5`
- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- focal blob `f420ec48c05d02602954c84d5fba410198f4b58c`
- helper blob `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`
- helper filesystem SHA-256 `3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`
- worktree clean before and after.

Python:
- `C:\Users\faber\miniconda3\python.exe`
- version `3.13.2`
- SHA-256 `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

Phase-A self-tests:
- `SYNTAX_OK`
- `PHASE_A_SELF_TEST_PASS`
- `EVIDENCE_SCHEMA_PASS`
- `SYNTHETIC_INSTRUMENTATION_PASS`
- `FAIL_CLOSED_PASS`
- `PHASE_B_PATH_PRESENT`
- `LIVE_ORACLE_EXECUTED = false`
- `REAL_SENSOR_EXECUTED = false`
- `REAL_SENSOR_CALL_COUNT = 0`.

Fail-closed gates A–E:
- provenance mismatch → `PROVENANCE_NOT_READY`
- invalid oracle fixture → `ORACLE_NOT_READY`
- missing authorization → `AUTHORIZATION_REQUIRED`
- malformed target identity → `TARGET_NOT_READY`
- incomplete evidence → `EVIDENCE_CONTRACT_NOT_READY`

All passed with the real sensor uncalled.

Synthetic instrumentation verified UTC timestamps, monotonic duration, target row capture, `returned_row_count == len(result)`, and second-call blocking.

The runner contains a connected Phase-B path:
`provenance → independent Windows CIM oracle → identity/authorization gates → one guarded real helper call → post-oracle → PID/create_time comparison`.

The actual live path exposes:
- oracle before/after;
- sensor start/end;
- monotonic elapsed;
- returned row count;
- call count;
- target row;
- corroborators;
- comparison A–E;
- runtime boundary;
- worktree state.

## WHAT CLOSED

- Phase-A readiness;
- Phase-B runtime capability;
- Phase-B evidence capability;
- evidence schema/self-test;
- exact runner artifact identity.

## WHAT REMAINS OPEN

The actual runtime correspondence remains completely unobserved:

`independent Windows process identity → existing audit_tools_observation.list_running_processes`.

No live oracle or real sensor call has yet occurred.

## WHY RQ15 HAS NOT ADVANCED RUNTIME-WISE

The repeated episodes did not discover defects in the IABV sensor. They successively discovered gaps in the external experiment contract:
1. wrong provenance comparison;
2. Phase-A artifact lacked live Phase-B capability;
3. Phase-B runner lacked required evidence fields;
4. corrected evidence-capable runner is now ready.

Thus the project has accumulated methodological progress while the target runtime edge remained untouched.

This is best described as:
`READINESS ENGINEERING ITERATIONS`, not repeated sensor failures.

## KNOWLEDGE DELTA

1. The full pre-live contract must be designed before consuming authorization.
2. Artifact identity, runtime capability and evidence capability are distinct readiness dimensions.
3. Each readiness dimension can be self-tested independently without touching production.
4. Repeated stop-before-sensor results are valid negative knowledge about the experiment harness, not about the target sensor.
5. The current RQ15 target remains a single existing-organ correspondence edge; no production mechanism gap has been demonstrated.

## METHOD DELTA

Refined reusable sequence:

`objective`
→ `composition archaeology`
→ `experiment contract`
→ `artifact identity`
→ `runtime capability`
→ `evidence capability`
→ `evidence self-test`
→ `fresh authorization`
→ `one live observation`
→ `independent verification`
→ `reconciliation`.

Optimization rule:
**complete the pre-live experiment contract before spending a bounded live observation authorization.**

## ROUTING DELTA

Current first open edge remains:
`independent Windows process identity → existing IABV process observation`.

Immediate edge is now:
`exact evidence-complete runner identity → fresh human authorization`.

Next capability-fit actor for the live step:
**CODEX**.

No live observation is authorized by this record.

## GOVERNANCE

No MCP wrapper or governed lifecycle was invoked. The future action is direct sensor-level and must remain explicitly authorized.

## STOP

No production code changes.
No new observer.
No WorldModel/PerceptionSnapshot/ToolRegistry/selection/learning experiment.

