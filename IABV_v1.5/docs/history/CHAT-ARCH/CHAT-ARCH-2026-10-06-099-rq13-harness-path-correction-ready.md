# CHAT-ARCH-2026-10-06-099 — UAAL-RQ13 HARNESS PATH CORRECTION READY / RUNTIME NOT AUTHORIZED

## Episode

Date: 2026-10-06
Experiment: UAAL-RQ13 PCS/ObjectiveRepository attribution
External harness: `C:\\temp\\rq13_task_precondition.py`
New harness SHA-256 reported by CODEX:
`50779B1DD321258729E1BB9ABEBA4D04ACBBFCC45CF0FDFDD0555AE5F6C1FA37`
Size: 44,485 bytes
Baseline:
`e46d8304167708bed0764d3bf2be8fd6643e8944`

## FACT

CODEX reports that the harness was modified only to correct its Git provenance path resolution and to extend self-test coverage.

The correction:
- derives the actual Git root using `git rev-parse --show-toplevel`;
- maps the harness's application-relative source path through the actual Git-root/CWD relationship;
- uses `git show <baseline>:<repo-relative-path>` from the Git root;
- reconstructs the Git blob SHA-1 from the served bytes;
- compares the working source bytes against the baseline blob;
- emits the resolved Git path as provenance.

The reported real checkout test resolves:
`IABV_v1.5/src/iabv_v15/bootstrap.py`

and reports baseline blob:
`e4befa6b683fc87aed7481f377f1332f5753e2c3`.

CODEX also reports:
- syntax check PASS;
- `contract-self-test` exit code 0;
- direct-root synthetic path test PASS;
- nested-checkout synthetic path test PASS;
- real `git show` path test PASS;
- no IABV import;
- no AppBootstrap;
- no SQLite oracle;
- no target operation;
- no TASK mutation;
- no production Python source change;
- no runtime RQ13 execution.

The evidence-contract assertions for PCS/repository identity, transparent `latest_active`, exactly one `current_package(refresh=True)`, and persisted-package SHA-256 fingerprint remain present according to CODEX.

## INDEPENDENT RECONCILIATION

GitHub read-back independently confirms that the canonical baseline repository path is:
`IABV_v1.5/src/iabv_v15/bootstrap.py`

with blob:
`e4befa6b683fc87aed7481f377f1332f5753e2c3`.

Therefore the specific path mismatch identified in episode 098 is real and the reported correction is semantically aligned with the repository layout.

The external harness bytes and its new SHA are still CODEX-reported evidence; they were not independently byte-read from the Windows filesystem in this coordination session.

## CLASSIFICATION

`HARNESS PROVENANCE PATH CORRECTED / SELF-TESTED / RUNTIME NOT AUTHORIZED`

The target observation boundary remains unopened.

## NOT PROVEN

This episode does not prove:
- AppBootstrap behavior;
- PCS identity;
- ObjectiveRepository identity/correlation;
- `latest_active()`;
- package alignment;
- P0 or DecisionContext continuity;
- causal learning;
- future decision influence;
- autonomous actor selection.

Harness correction is method adaptation, not runtime learning.

## ROUTING DELTA

The previous open edge
`C94D... → bounded RQ13 runtime`
is superseded.

Current first open edge:
`new harness SHA 50779B1D... → fresh human authorization → one bounded RQ13 attribution runtime → independent verification`.

No authorization transfers from the superseded SHA.

## NEXT RUNTIME CONTRACT

After fresh authorization naming exactly the new SHA, execute once and only once:

1. establish exact executable artifact and CWD provenance;
2. run normal AppBootstrap once;
3. capture runtime PCS identity;
4. capture runtime ObjectiveRepository identity;
5. verify PCS repository corresponds to the AppBootstrap repository;
6. invoke exactly one `current_package(refresh=True)`;
7. transparently observe `latest_active()` success/empty/exception without altering its semantics;
8. capture returned package ID, persisted package ID, `site_id`, `active_objective_id`, persisted `portable_context/latest.json` SHA-256, size, mtime and match status;
9. stop.

Do not proceed to TASK mutation, P0, `handle_request`, DecisionContext reconstruction, MCP/provider task execution, learning claims, or downstream causal inference in the same run.

## LEARNING STATUS

Project-wide status remains:
- lower-layer adaptive learning mechanism: PRESENT/OBSERVED;
- selector-level learned-state influence: EVIDENCED;
- strong causal future-decision learning from a verified prior experience: NOT PROVEN.

This episode adds only a provenance/method correction.

