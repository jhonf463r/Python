# CHAT-ARCH-2026-10-07-121 — UAAL/RQ15 PHASE-B EVIDENCE CONTRACT GAP

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / EVIDENCE-CONTRACT / HARNESS / SYMBIOSIS`

## Trigger

Episode 120 verified a runtime-capable Phase-B runner. A fresh authorized live attempt then stopped before oracle/sensor execution because the exact authorized runner did not emit all fields required by the observation evidence contract.

## FACT

Authorized runner:

`C:\temp\rq15_phase_b_runner_20261006.py`

SHA-256:

`15DF88E873E9CF7288ABFBDFD066C14D98E089774D14C3ECC14CA51400BF6979`

Target:
- worktree `C:\temp\wm-synaptic-8425`
- HEAD `8425f03eb45abd11951938f6e3234459c1585b55`
- tree `1d46e59195d01c1cec6806f264ef75f31541e806`
- focal blob `f420ec48c05d02602954c84d5fba410198f4b58c`
- helper blob `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`
- helper filesystem SHA-256 `3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`
- worktree clean.

Python:
`C:\Users\faber\miniconda3\python.exe`
version `3.13.2`
expected SHA-256 `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

Pre-execution provenance passed.

The runner did not execute:
- independent Windows oracle;
- existing IABV sensor.

`sensor_call_count = 0`.

The exact runner's live sensor path only called `guard.invoke(...)` and did not record:
- sensor invocation start;
- sensor invocation end;
- elapsed time;
- explicit returned row count.

Those fields are required by the experiment evidence contract.

Therefore using this exact runner would produce an authorization-valid execution but an evidence-incomplete observation.

## INFERENCE

`E — INCONCLUSIVE` is correct, but the cause is specifically:

`READINESS FAILURE — EVIDENCE CONTRACT INCOMPLETE`

This is not:
- sensor failure;
- oracle failure;
- process mismatch;
- environment absence;
- correspondence evidence.

## ASSUMPTION

No assumption is made about live oracle behavior or sensor output.

## KNOWLEDGE DELTA

1. Phase-B runtime capability is not sufficient; the runner must also be evidence-complete.
2. The evidence contract must be validated against the exact runtime output path before consuming live authorization.
3. Sensor call guards alone do not provide sufficient forensic timing/row-count evidence.
4. Authorization identity and evidence capability are separate readiness dimensions.

## METHOD DELTA

Refine the readiness sequence:

`artifact identity`
→ `artifact runtime capability`
→ `artifact evidence capability`
→ `evidence-contract self-test`
→ `fresh authorization`
→ `live execution`.

New invariant:

`runtime-capable ≠ evidence-complete`.

A runner is not ready for live authorization until every required evidence field is emitted by the actual Phase-B execution path.

## ROUTING DELTA

The original correspondence edge remains:

`independent Windows process identity → existing IABV process observation`.

Immediate open edge:

`evidence-complete Phase-B runner → fresh authorization`.

Next actor remains **CODEX**.

Required capability:
external runner correction, exact output-contract self-testing, Windows timing/row-count capture and provenance.

No production changes.

## NEXT ACTION

Build or revise the external Phase-B runner so its actual live path emits all required evidence fields:

- oracle before timestamp;
- sensor invocation start timestamp;
- sensor invocation end timestamp;
- sensor elapsed duration;
- explicit sensor returned row count;
- sensor call count;
- oracle after timestamp;
- before/after independent identities;
- matching sensor row fields;
- runtime side-effect indicators.

Then self-test the output contract without live sensor execution.

Do not consume another live authorization until the exact new runner hash is established and the evidence contract is self-tested.
