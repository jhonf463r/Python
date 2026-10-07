# CHAT-ARCH-2026-10-07-117 — UAAL/RQ15 READINESS / PROVENANCE + ORACLE GATE FAILURE

## Classification

`RECONCILIATION / EXPERIMENT-READINESS / PROVENANCE / WINDOWS-ORACLE / SYMBIOSIS`

## Trigger

RQ15 was routed to one bounded live correspondence probe:

`independent OS process → existing IABV process observation helper`

The run returned `E — INCONCLUSIVE`, but the sensor was not invoked. The failure occurred before the observation boundary because the readiness contract was not satisfied.

## FACT

Target provenance:
- Worktree: `C:\temp\wm-synaptic-8425`
- Application: `C:\temp\wm-synaptic-8425\IABV_v1.5`
- HEAD: `8425f03eb45abd11951938f6e3234459c1585b55`
- tree: `1d46e59195d01c1cec6806f264ef75f31541e806`
- worktree clean before and after.
- focal/source blobs reported: `f420ec48c05d02602954c84d5fba410198f4b58c`, `f16a3ad32d008eab65fbaf660a9a9527e44cabc8`.

Harness:
- Python PID `16036`, parent PID `15608`
- started `2026-10-07T01:36:41.568636+00:00`
- Python `3.13.2`
- observed executable SHA-256: `DC7BD562DBD2F2B75EB8C95268828422EF7F9D6FC1AC40C9B281DBDE11CB6580`.

The exact provenance gate was not satisfied because the Python SHA literal expected by the harness differed from the SHA-256 literal reported in the experiment package. The harness compared against the prior canonical digest rather than the literal supplied in the package.

The helper was imported from the authorized `src` path. Its observed file SHA-256 was:
`3813087778DC6E15A279FA2A9174B8B0D22D932AA9614EB80CA194DBDFAAC39E`.

`iabv_v15.bootstrap` was not imported. No MCP server was created or executed.

The independent CIM query failed with `JSONDecodeError` before a usable oracle identity was obtained.

`audit_tools_observation.list_running_processes()` was invoked **zero times**.

No target PID/create_time pair exists. No sensor result exists. No runtime correspondence, mismatch or absence observation exists.

No code changes occurred; worktree remained clean.

## INFERENCE

The live result is strictly:

`E — INCONCLUSIVE / READINESS FAILURE BEFORE SENSOR INVOCATION`.

The edge remains open:

`independent OS process → existing IABV process observation helper`.

There is no evidence in this run for:
- process correspondence;
- sensor omission;
- sensor discordance;
- environmental absence;
- a new process-observer requirement.

## ASSUMPTION

No assumption is made that the malformed/mismatched Python digest intended to repeat the prior canonical value.

No assumption is made that the CIM output contained a valid identity row.

## Knowledge Delta

1. Direct import readiness can resolve the intended existing sensor without importing `AppBootstrap` or starting MCP.
2. A provenance gate that compares against a prior canonical value instead of the exact declared artifact literal is not a sufficient experiment contract.
3. Oracle parsing must produce a validated identity record before any sensor invocation; otherwise the run is not evidence about correspondence.
4. A pre-observation readiness failure must be classified separately from sensor inconclusiveness.
5. The safe direct-helper boundary remains sensor-level and bypasses MCP governance; fresh authorization is required for the next observation.

## Method / Routing Delta

Refine the readiness sequence for bounded live correspondence:

`experiment contract`
→ `exact artifact/input readiness`
→ `literal provenance validation`
→ `transitive side-effect audit`
→ `isolation`
→ `independent oracle execution + schema validation`
→ `authorization`
→ `sensor invocation`
→ `observation`.

New stopping invariant:

`sensor calls = 0` + provenance/oracle gate failure ⇒ `NO RUNTIME EVIDENCE`.

Do not relabel this as an environmental or sensor failure.

Before any fresh live observation, the harness must first self-test:
- exact observed Python executable digest equals the literal declared for this run;
- exact target/source hashes are tied to the declared provenance;
- independent Windows oracle parser returns a validated `(PID, create_time)` identity;
- readiness failure occurs before any IABV sensor call.

## Governance / Stop

No MCP wrapper or governance gate ran. The direct helper route is therefore not governed by MCP in this episode.

The run correctly stopped before observation.

Any subsequent sensor invocation requires a **fresh authorization** scoped to:
- exact target SHA/worktree;
- exact Python executable digest;
- exact sensor file digest;
- direct invocation of `audit_tools_observation.list_running_processes`;
- independent Windows oracle;
- one bounded observation only.

No production implementation is justified.

## Routing Consequence

Current first open edge remains:

`independent OS process → existing IABV process observation helper`.

Immediate next step is **not** another live probe. It is a **harness-only readiness correction/self-test**, followed by a fresh authorization gate before any new observation.

Capability-fit actor: **CODEX**.

Required capability:
Windows provenance/runtime harness correction, parser validation, repository archaeology, and strict read-only readiness testing.

Independent verifier:
Windows OS process oracle, independent of the IABV sensor.

