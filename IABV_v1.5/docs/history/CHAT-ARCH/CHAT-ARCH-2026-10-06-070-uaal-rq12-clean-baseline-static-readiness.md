# CHAT-ARCH-2026-10-06-070 — UAAL-RQ12 CLEAN BASELINE STATIC READINESS

## STATUS

CANONICAL RECONCILIATION / STATIC READINESS / ROUTING

## OBJECTIVE

Determine whether the planned RQ12 clean-baseline runtime observation is technically ready, without executing MCP, invoking tools, scanning WorldModel, or changing production code.

## CANONICAL STATE RECONCILED

- Repository: `jhonf463r/Python`
- Current canonical main at reconciliation: `b158290f4e8afe41760cca18a77ec3e7580f7a6b`
- Executable analysis baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`
- RQ10 formal attribution: `MIXED/INDETERMINATE`
- RQ10 remains variant/candidate evidence; it is not baseline evidence.
- RQ10 PID 21668 exact loaded-byte fingerprint remains a bounded historical evidence gap.
- No fresh RQ12 runtime authorization exists at this phase.

The comparison from `e46d830...` to canonical `main` contains documentation/archive changes only in the reconciled history relevant here; the executable experiment target remains `e46d830...`.

## PHASE 1 RESULT

A dedicated isolated worktree was prepared:

`C:\Users\faber\.codex\worktrees\rq12-clean-baseline\Python\IABV_v1.5`

Git status is clean. No RQ05/RQ10 overlay is present in the two relevant source files.

Confirmed baseline blobs:

- `src/iabv_v15/infra/mcp/server.py`
  - baseline blob: `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`
  - checkout SHA-256: `39264603C9D56B3231F6F0FFAD1D711EDD7F6FBAEF5089AD2BC36CAB3DB2E9CE`
- `src/iabv_v15/services/adaptive/task_context_assembler.py`
  - baseline blob: `c5a6852a6a82a0c60886ea4bb6c236f50fe4a57c`
  - checkout SHA-256: `BEEF00CB07555A5F77A5687BDE2C42D68ADB172D6E21A88EAA41E84C93ADBD4B`

The available interpreter is `C:\Python314\python.exe`, reported as version `3.14.4` from file metadata. This version was not executed during Phase 1.

## IN-PROCESS PROVENANCE CONTRACT

The proposed runtime harness can capture, inside the executing process and before `cognitive_frame_translate`:

- PID and parent PID;
- executable path;
- command line;
- CWD;
- PYTHONPATH/import roots;
- interpreter version;
- `inspect.getfile()`;
- module `__file__`;
- module `__cached__`;
- SHA-256 of the resolved source files;
- SHA-256 of the resolved cached bytecode when present;
- loader/spec metadata sufficient to interpret whether source or cached bytecode is being used.

The harness is disposable and observational; no production source modification is required.

Because an existing `.pyc` may be consumed even when `-B` prevents writing new bytecode, the runtime record must distinguish:
`source artifact fingerprint` from `cached-bytecode artifact fingerprint`, and must not claim exact loaded-code identity from source SHA alone when a cached artifact was actually selected.

## RUNTIME-STATE INPUT BOUNDARY

A clean Git worktree proves source-artifact cleanliness; it does not prove that runtime state is fresh.

`latest.json` therefore becomes an explicit experiment input. Before bootstrap, the harness should record its path, presence, size, mtime and SHA-256 (and its WorldModel identity if readable), without normalizing or rewriting it and without requesting a scan.

This separates:
`clean source artifact`
from
`pre-existing runtime/persistence state`.

## NATURAL REFRESH / SCAN BOUNDARY

Baseline source legitimately requests WorldModel refresh from bootstrap and from the perception assembler. Phase 1 cannot establish whether the monitor will convert those requests into a full scan.

RQ12 must therefore:

1. record every relevant refresh/scan event and reason;
2. distinguish `refresh requested` from `scan executed`;
3. not request an additional/manual scan;
4. treat only effects covered by the explicit runtime authorization as in-scope;
5. stop on an effect outside the authorization contract, especially external execution/provider invocation or an additional MCP observation.

A natural WorldModel refresh/scan is not itself evidence of failure if it is within the authorized scope; its identity and chronology must instead be captured.

## PUBLIC OBSERVATION

The single public observation target is:

`cognitive_frame_translate`

It should be invoked exactly once with the normal baseline contract.

The public payload does not explicitly expose the `PerceptionSnapshot` ID. A transparent harness may observe the return of `TaskContextAssembler.build_perception_snapshot()`, record object/snapshot identity and relevant embedded WorldModel identity, then return the same object to the existing translator without changing production semantics.

No `orchestrator_preview`, `handle_request`, external AI/provider call, or downstream DecisionContext experiment belongs in RQ12.

## TEMPORAL IDENTITY TRACE

RQ12 must preserve, separately rather than by final-state inference:

`pre-bootstrap persisted WorldModel identity`
→ `post-bootstrap in-memory identity`
→ `pre-translation identity`
→ `PerceptionSnapshot identity / embedded WorldModel identity`
→ `final persisted identity`.

Any replacement must be represented as a temporal transition, not silently collapsed into a single final ID.

## READINESS ASSESSMENT

**FACT**

- Isolated worktree exists.
- Worktree is clean.
- HEAD is exactly `e46d830...`.
- Relevant source blobs match the executable baseline.
- Source SHA-256 fingerprints are known before execution.
- The public MCP entrypoint exists.
- A disposable in-process provenance harness is technically feasible.
- Phase 2 has not been executed.

**INFERENCE**

One fresh MCP observation can provide materially stronger baseline attribution than RQ10, provided the process captures its own provenance before translation and the runtime effects remain within authorization.

**ASSUMPTION**

The specified interpreter, import roots and runtime dependencies will be available at execution time. Interpreter version has not yet been runtime-verified in this worktree.

## MAXIMUM JUSTIFIED CLAIM

RQ12 Phase 1 is **READY FOR AUTHORIZED RUNTIME**.

It proves preparation and artifact cleanliness, not runtime behavior, process attribution, WorldModel transition, or PerceptionSnapshot identity.

## FIRST OPEN EDGE AFTER RECONCILIATION

The historical provenance gate is closed as an actionable problem by RQ11B's stopping rule. The first actionable edge is now:

`fresh human authorization`
→ `clean e46d830 execution`
→ `in-process artifact fingerprint`
→ `WorldModel identity/chronology`
→ `PerceptionSnapshot identity/provenance`.

## ACTOR FIT

**CODEX** remains capability-fit.

Required capabilities are exact Windows/MCP runtime control, disposable harnessing, process/import provenance and direct observation of WorldModel/PerceptionSnapshot identity. This is capability-fit, not actor inheritance.

ChatGPT remains coordinator/reconciler/writeback. Independent verification belongs after the observation and should be routed separately according to the resulting uncertainty.

## KNOWLEDGE DELTA

- RQ12 now has an actually clean isolated executable baseline worktree.
- The baseline source fingerprints are known before execution.
- The provenance method is strengthened by requiring source/cache distinction inside the process.
- Runtime-state cleanliness is explicitly separated from Git cleanliness.
- Natural refresh and monitor scan are now treated as observable effects whose authorization scope must be explicit.
- No runtime claim has been added.

## METHOD DELTA

Future clean-baseline runtime experiments should use:

`clean source artifact → pre-state runtime input capture → in-process source/cache fingerprint → process/import identity → event chronology → single observation → final identity → independent verification`.

Do not infer exact runtime attribution from HEAD SHA plus current files alone.

## ROUTING DELTA

**Current actor:** CODEX

**Current action:** obtain fresh explicit human authorization, then execute only RQ12 Phase 2.

**Runtime authorization:** NOT CURRENTLY GRANTED.

## STOP CONDITIONS

Before execution:
- if worktree ceases to be clean, stop;
- if HEAD is not exactly `e46d830...`, stop;
- if relevant source blobs do not match baseline, stop;
- if provenance harness cannot capture in-process identity, stop.

During execution:
- if an external AI/provider/tool outside the contract executes, stop;
- if a second MCP observation occurs, stop;
- if the harness cannot attribute the executing modules, do not promote the observation;
- stop after PerceptionSnapshot identity/provenance and final persistence capture.

## NEGATIVE KNOWLEDGE

Do not infer from Phase 1:
- that baseline `e46d830...` has executed;
- that WorldModel refresh will or will not become a full scan;
- that MCP will preserve the prior producer snapshot;
- that the resulting PerceptionSnapshot will be consumed by downstream DecisionContext governance;
- that any causal learning or future decision change exists.

## TRACEABILITY

Predecessors:
- `CHAT-ARCH-2026-10-06-069-uaal-rq11b-rq10-provenance-final-reconciliation.md`
- `CHAT-ARCH-2026-10-06-068-uaal-rq11-static-readiness-reconciliation.md`
- `CHAT-ARCH-2026-10-06-067-uaal-rq10-provenance-correction.md`

Phase 1 result supplied by Codex in the current collaboration episode and reconciled against canonical GitHub main.
