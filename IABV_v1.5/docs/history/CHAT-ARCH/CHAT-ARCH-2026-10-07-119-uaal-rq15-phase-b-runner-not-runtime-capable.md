# CHAT-ARCH-2026-10-07-119 — UAAL/RQ15 PHASE-B RUNNER NOT RUNTIME-CAPABLE

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / HARNESS-CONTRACT / AUTHORIZATION / SYMBIOSIS`

## Trigger

Episode 118 established the readiness contract for RQ15 and allowed a fresh authorization for one live observation. The subsequent execution revealed that the authorized artifact itself was only a Phase-A readiness self-test and did not implement the live oracle/sensor execution path.

## FACT

Authorized external harness:

`C:\temp\rq15_readiness_gate_20261006.py`

SHA-256:

`AE9599922D18070BFA308790B39CFA2BDDE54900810BBAF93D03A0CAC8E197F3`

Size:

`10,853` bytes.

Target remained:

- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- focal blob `f420ec48c05d02602954c84d5fba410198f4b58c`
- helper blob `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`
- helper filesystem SHA-256 `3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`
- clean worktree before and after.

The Python executable SHA-256 was checked from disk as:

`DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

No Python process was started for this attempt.

The authorized harness contains Phase-A parser/provenance/fail-closed readiness tests but does not implement a live Windows oracle or live sensor invocation path.

No IABV module, AppBootstrap, MCP, Windows oracle, or process sensor was executed.

`sensor_call_count = 0`.

## INFERENCE

The authorization was technically valid for the exact artifact but the artifact was not capable of exercising the authorized Phase-B observation.

Therefore the live correspondence experiment was not executed and no correspondence evidence exists.

This is a **runner-contract failure**, not a sensor failure.

## ASSUMPTION

No assumption is made about whether a different existing harness already satisfies the full Phase-B contract; that must be established by targeted archaeology.

## KNOWLEDGE DELTA

1. A readiness harness can correctly validate Phase-A gates while remaining incapable of Phase-B execution.
2. `authorization matches artifact` does not imply `artifact implements authorized action`.
3. Experiment authorization must bind not only identity/hash but also the runtime capability contract of the authorized artifact.
4. The Phase-A and Phase-B artifacts should be explicitly differentiated.

## METHOD DELTA

Refined execution readiness:

`experiment contract`
→ `artifact identity`
→ `artifact capability contract`
→ `self-test of required runtime path`
→ `fresh authorization`
→ `live oracle`
→ `sensor`.

New invariant:

`authorized artifact ≠ runtime-capable artifact`.

A harness that can only stop before the oracle/sensor cannot be used to satisfy an authorization for live observation.

## ROUTING DELTA

The current RQ15 correspondence edge remains:

`independent OS process → existing audit_tools_observation.list_running_processes`.

The immediate open readiness edge is:

`runtime-capable Phase-B harness → fresh authorization for one live observation`.

No sensor execution should occur until the Phase-B runner is independently self-tested.

Capability-fit actor remains **CODEX**.

Required capability:
Windows harness construction, subprocess/oracle execution, exact provenance, safe import/isolation and contract self-testing.

No production implementation is justified.

## NEXT ACTION

Create or adapt an **external runtime-capable Phase-B harness** only.

The harness must be able to execute the actual independent Windows oracle and, behind an authorization gate, call exactly one existing IABV process sensor.

The construction must not execute the live path during its own creation/self-test.

After the new harness is self-tested and its exact hash is established, obtain a new authorization that names that exact artifact and hash.

