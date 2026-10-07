# CHAT-ARCH-2026-10-07-124 — UAAL/RQ15 CODEX EXECUTION-CHANNEL POLICY BLOCK

## Classification

`RECONCILIATION / ROUTING / WINDOWS-RUNTIME / EXECUTION-CHANNEL / SYMBIOSIS`

## Trigger

Episode 123 established that the RQ15 pre-live contract was fully closed and the evidence-complete Phase-B runner was ready. The first authorized live attempt with that exact runner then failed before process execution because Codex's execution tool rejected the launch command as `blocked by policy`.

## FACT

Authorized evidence-complete runner:
`C:\temp\rq15_phase_b_evidence_runner_20261006.py`

SHA-256:
`E70D9215B4528ECBC315C0DCA0953AD832071F2E57FB255003698569072F5485`

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
SHA-256 `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

The provenance gate passed.

The Codex execution tool rejected the command to launch the authorized runner with the message:

`blocked by policy`

No more specific reason was supplied.

No temporary authorization file was created by the rejected command.

No live Windows oracle ran.

No real sensor ran.

`real_sensor_call_count = 0`.

No IABV/AppBootstrap/MCP/WorldModel/ToolRegistry/SynapticRouter/provider/network/persistence activity occurred.

## INFERENCE

The experiment was blocked at the **external execution-channel boundary**, before runner execution.

This provides no evidence about:
- the runner's runtime behavior;
- the Windows oracle;
- the IABV sensor;
- process correspondence.

The failure is therefore neither sensor failure nor environment absence.

The exact cause of the policy block is unknown.

## ASSUMPTION

Do not assume the policy block is caused by:
- the runner contents;
- the target repository;
- Windows;
- IABV;
- the sensor;
- a safety policy specific to process inspection.

The only observed fact is that the Codex execution tool rejected the launch.

## KNOWLEDGE DELTA

1. RQ15 now has an additional execution-readiness dimension: `execution-channel admissibility`.
2. A runtime/evidence-complete artifact can still be unusable if the selected actor's execution channel rejects its launch.
3. `runner ready` and `actor-channel ready` are separate gates.
4. Repeating the same Codex launch is not justified without new information about the rejection.
5. The next actor may be selected based on capability + execution-channel availability, not capability alone.

## METHOD DELTA

Refined readiness:

`artifact identity`
→
`runtime capability`
→
`evidence capability`
→
`actor execution-channel admissibility`
→
`fresh authorization`
→
`live execution`.

New invariant:

`capability-fit actor ≠ execution-ready actor`.

When an execution channel rejects a permitted experiment before execution and gives no actionable diagnostic, prefer a different capability-fit execution channel rather than modifying the experiment artifact.

## ROUTING DELTA

Original first open edge remains:

`independent Windows process identity → existing IABV process observation`.

Immediate blocker:

`Windows runtime execution channel admissible for the exact runner`.

Codex's current execution channel is observed blocked by policy. Therefore do not retry the same launch path without new evidence.

**Next capability-fit candidate: DEVIN**, because the remaining task is Windows runtime execution and prior project evidence establishes Devin as a viable Windows runtime/production-lifecycle actor in this development context.

This is capability/channel routing, not a permanent role assignment.

Claude/Sonnet is not the next actor because the failure is not a semantic contradiction or evidence discrepancy; it is execution-channel availability.

Deep Research is not relevant.

Opus is not justified.

## GOVERNANCE

The direct sensor-level authorization was never consumed because execution did not begin.

No policy override is requested or inferred.

## NEXT ACTION

Use a fresh actor/channel capable of executing the exact authorized Windows runner.

First establish execution-channel readiness with the smallest possible check:
- exact runner hash;
- target provenance;
- ability to launch the exact runner in read-only mode.

Only after successful launch should the runner execute its existing Phase-B path.

Do not modify the runner as part of this routing change.

