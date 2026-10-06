# CHAT-ARCH-2026-10-06-105 — UAAL-RQ13 IMPORT READINESS CORRECTED / RUNTIME NOT AUTHORIZED

## Episode

Date: 2026-10-06
Experiment: UAAL-RQ13 bounded attribution runtime
Harness: `C:\\temp\\rq13_task_precondition.py`
New reported SHA-256:
`771FBFDB26765CEB364D5D485D97A63270C018B8713360FB38FF567B6F464FFC`
Size: 53,654 bytes
Baseline:
`e46d8304167708bed0764d3bf2be8fd6643e8944`

## FACT

The previous runtime failed before AppBootstrap because the runtime-authorized harness did not place the application `src` directory on the Python import path.

The harness was corrected to:
- derive `<application_root>\\src` from the actual application root;
- place the derived source root first in the process `sys.path`;
- place the same source root first in `PYTHONPATH` for child/inherited environments;
- emit explicit `PYTHON_IMPORT_PATH_PROVENANCE` before importing IABV.

Reported syntax check: PASS.
Reported contract-self-test: PASS, exit code 0.

The self-test reports:
- real source root derived as
  `C:\\temp\\rq13-e46-artifact-ready\\IABV_v1.5\\src`;
- isolated synthetic module import succeeded using the prepared path;
- direct/nested layout and prior Git provenance checks remain covered;
- primary-result-before-trace and trace-reporting checks remain covered;
- `iabv_imported=false`;
- AppBootstrap not executed;
- no RQ13 runtime;
- no `current_package` or `latest_active`;
- no SQLite;
- production Python unchanged;
- zero code changes and zero code untracked under `src/` and `tests/` according to the reported final checks.

## INDEPENDENT RECONCILIATION

This episode is a readiness result reported by CODEX. The harness bytes and SHA were not independently byte-read from Windows in this coordination session.

The source-worktree readiness gate from episode 103 remains closed at classification B:
dirty worktree, but no divergent Python source under the RQ13 target path.

## CLASSIFICATION

`PYTHON IMPORT READINESS CORRECTED / SELF-TESTED / RUNTIME NOT AUTHORIZED`

## METHOD DELTA

New invariant:
`Git provenance ready ≠ Python import ready`.

More specifically:
`process CWD correct + source exists ≠ package importable`
unless the executable's import path exposes the application `src`.

Readiness therefore now includes:
`source provenance → interpreter provenance → import-path readiness → application runtime readiness`.

## ROUTING DELTA

Previous harness SHA `60EC734D...` is superseded.

Current first open edge:
`new harness SHA 771FBF... → fresh human authorization → one bounded RQ13 runtime → capture returned package before trace processing → independent verification`.

No runtime authorization is implied by this readiness result.

## TARGET CONTRACT FOR NEXT AUTHORIZED RUN

After fresh authorization of exactly the new SHA:
1. establish exact executable, CWD, HEAD and source provenance;
2. record effective import-path provenance;
3. import IABV;
4. execute normal AppBootstrap once;
5. capture runtime PCS and ObjectiveRepository identity;
6. verify repository equivalence;
7. execute exactly one `current_package(refresh=True)`;
8. immediately serialize the returned package identity/metadata before trace processing;
9. fingerprint/read persisted `portable_context/latest.json`;
10. process `latest_active` trace after preserving the primary result;
11. compare returned/persisted package identity and relevant metadata;
12. stop.

No second target call and no downstream P0/DecisionContext/MCP/provider task execution.

## LEARNING STATUS

Unchanged:
- lower-layer adaptive learning mechanism: PRESENT/OBSERVED;
- selector-level learned-state influence: EVIDENCED;
- strong causal future-decision learning: NOT PROVEN.

This episode is method/readiness adaptation, not IABV learning evidence.
