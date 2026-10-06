# CHAT-ARCH-2026-10-06-098 — UAAL-RQ13 HARNESS PROVENANCE GATE FAILURE / NO TARGET RUNTIME

## 1. Episode identity

Date: 2026-10-06  
Experiment: UAAL-RQ13 bounded PCS/ObjectiveRepository attribution observation  
Authorized harness: `C:\\temp\\rq13_task_precondition.py`  
Harness SHA-256 authorized/reported before execution:
`C94D983D5A8B33C906807AA45B224D4F45430D616EB61E62DD140C32A15B50EA`  
Baseline: `e46d8304167708bed0764d3bf2be8fd6643e8944`  
Worktree: `C:\\temp\\rq13-e46-artifact-ready`  
Requested CWD: `C:\\temp\\rq13-e46-artifact-ready\\IABV_v1.5`

Fresh human authorization: YES.  
Execution count: exactly one.  
Retry: NO.

## 2. Provenance evidence

CODEX reports that the pre-execution checks established:
- HEAD `e46d8304167708bed0764d3bf2be8fd6643e8944`, detached.
- Worktree dirty with 264 entries at pre-execution state.
- No tracked Python differences in `src/` or `tests/`, and no executable untracked files in those paths.
- Four relevant baseline blobs matched:
  - `bootstrap.py`: `e4befa6b683fc87aed7481f377f1332f5753e2c3`
  - `portable_context_service.py`: `021cbe829e96099494444b33275423f8d6319dc6`
  - `objective_repository.py`: `40e70a551df50e8f3c8277e4f82450c26e2b599f`
  - `storage.py`: `e12afde7823ddce21d54ca4871bc9aaef5792d5d`
- `PYTHONPATH` was empty initially and was set only for this execution to the worktree's `IABV_v1.5\\src`.

The harness's own provenance gate then failed before importing IABV:
`git rev-parse e46d830...:src/iabv_v15/bootstrap.py`
returned exit code 128 because, in this checkout, the commit path includes the repository subdirectory `IABV_v1.5/`.

## 3. Runtime boundary

The authorized target observation did NOT begin.

Observed:
- process invocation reached the harness Git provenance gate;
- elapsed time approximately 0.6 s;
- process exit code 1.

Not observed:
- Python PID / parent PID / version from the harness provenance event;
- IABV import;
- AppBootstrap milestones;
- PCS identity;
- ObjectiveRepository identity/correlation;
- `latest_active()`;
- `current_package(refresh=True)`;
- package IDs, metadata or persisted fingerprint;
- TASK inspection/mutation;
- any downstream provider/MCP/P0/DecisionContext operation.

## 4. FACT / INFERENCE / ASSUMPTION

### FACT
- Exactly one authorized execution occurred and terminated in the harness's Git provenance gate.
- No IABV runtime target operation was observed.
- The pre-execution checks reported the baseline HEAD, relevant source blobs and authorized harness SHA described above.

### INFERENCE
- The harness constructs the Git path relative to its CWD as though `src/` were directly below the Git root, while this repository layout places `src/` under `IABV_v1.5/`.

### ASSUMPTION
- None about AppBootstrap, PCS, ObjectiveRepository, `latest_active()`, package alignment or learning. Those states were not observed.

## 5. Epistemic classification

Classification:
`HARNESS PROVENANCE GATE FAILURE / NO TARGET RUNTIME`

This episode does NOT prove:
- an IABV semantic defect;
- an AppBootstrap failure;
- a PCS/ObjectiveRepository attribution failure;
- learning or future-decision influence;
- autonomous coordination or actor selection.

It proves only that the authorized evidence instrument could not enter the target observation boundary because its own repository-path provenance check was structurally misaligned with the checkout layout.

## 6. KNOWLEDGE DELTA

Repository-path assumptions inside an evidence harness are themselves part of the runtime provenance contract. A correct external SHA, baseline HEAD and matching source blobs do not establish target attribution when the harness's internal Git object lookup resolves the wrong repository-relative path.

## 7. METHOD DELTA

Add an explicit harness rule:
`Git repository root path semantics != process CWD path semantics`.

The harness must resolve the target file path from the actual Git root (or otherwise derive the repository-relative path from Git), not assume the application subdirectory is the repository root.

Self-test must cover the exact nested checkout layout used by the experiment, without importing or executing IABV.

## 8. ROUTING DELTA

The prior first open target edge:
`C94D... → bounded PCS/ObjectiveRepository attribution runtime`
did not open.

New first open edge:
`authorized experiment contract → corrected provenance gate in external harness → self-test on nested repo layout → new harness SHA → fresh human authorization → one bounded RQ13 attribution runtime`.

Capability-fit actor:
**CODEX**, because the remaining uncertainty is isolated to external Windows/Git harness path semantics.

No new production implementation is justified. No retry of the failed runtime is justified with the existing harness artifact. The current authorization is consumed by the one execution attempt; a corrected harness requires a new SHA and therefore fresh authorization.

## 9. Learning status

This episode contributes **no new learning evidence**.

The existing project-wide learning reconciliation remains unchanged:
- lower-layer adaptive learning mechanism: present/observed;
- selector-level learned-state influence: evidenced;
- strong causal future-decision learning from a prior verified experience: NOT PROVEN.

Harness correction itself is method adaptation, not evidence that the IABV runtime learned.

## 10. Required next boundary

Correct and self-test only the external harness path-resolution contract. Do not modify IABV production source. Do not run the target runtime again until the corrected harness has a new digest and receives fresh explicit human authorization.
