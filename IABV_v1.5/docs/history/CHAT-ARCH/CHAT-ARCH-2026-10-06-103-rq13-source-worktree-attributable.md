# CHAT-ARCH-2026-10-06-103 — UAAL-RQ13 SOURCE WORKTREE TARGET-PATH ATTRIBUTABLE

## Episode

Date: 2026-10-06
Experiment: UAAL-RQ13
Baseline:
`e46d8304167708bed0764d3bf2be8fd6643e8944`
Worktree:
`C:\\temp\\rq13-e46-artifact-ready`
Harness:
`C:\\temp\\rq13_task_precondition.py`
Current harness SHA reported by CODEX:
`60EC734CD8694F8ABF797A2A78942F5DF60C464B10E5C27742097BAF2DFA422F`

## FACT

CODEX's read-only forensic inventory reports:

- `git status --porcelain=v1 --untracked-files=all`: 421 entries;
  - 361 tracked modified;
  - 60 untracked;
  - no tracked deletions or renames.
- Under `IABV_v1.5/src/`:
  - 288 tracked modified entries, all `.pyc`;
  - 147 ignored `.pyc` cache entries;
  - 0 modified `.py`;
  - 0 deleted/renamed/untracked `.py`.
- The four focal Python sources exactly match baseline blobs:
  - `bootstrap.py` `e4befa6b683fc87aed7481f377f1332f5753e2c3`;
  - `portable_context_service.py` `021cbe829e96099494444b33275423f8d6319dc6`;
  - `objective_repository.py` `40e70a551df50e8f3c8277e4f82450c26e2b599f`;
  - `storage.py` `e12afde7823ddce21d54ca4871bc9aaef5792d5d`.
- CODEX reports 144/144 tracked Python 3.13 bytecodes and 144/144 tracked Python 3.14 bytecodes valid and equivalent to their current baseline source code; ignored caches were also source-equivalent in the inspected dimensions.
- No Python source overlay under `src/` was found.
- The target import/dependency path has no detected divergent Python source.
- No runtime was executed in this readiness inspection.

## CLASSIFICATION

`SOURCE WORKTREE DIRTY BUT TARGET PATH BASELINE ATTRIBUTABLE`

This closes the prior readiness question sufficiently for the bounded experiment under the stated evidence contract, with one residual epistemic caveat: the historical execution does not establish exactly which cached bytecode files were loaded. The current source and inspected bytecode are nevertheless baseline-equivalent, so no divergent Python source overlay is identified.

## NOT PROVEN

This does not prove:
- which exact `.pyc` file a future process will load;
- future runtime outcome;
- package returned/persisted correspondence;
- `latest_active()` success/content;
- learning or future-decision influence.

## ROUTING DELTA

The source-worktree readiness edge is now closed at classification B.

New first open edge:
`fresh authorization for harness 60EC734D... → one bounded RQ13 runtime → capture primary return before trace reporting → persisted package fingerprint → independent verification`.

No authorization is implied by this readiness result.

No worktree cleanup is required for this route. The current dirty state remains preserved as evidence.

## METHOD DELTA

New invariant:
`dirty worktree + baseline source + source-equivalent bytecode ≠ clean worktree`,
but it can still be
`target-path baseline attributable`
when executable overlays are classified and no divergent Python source is found.

Residual cache-load uncertainty must remain explicit rather than silently upgraded to exact artifact identity.

## LEARNING STATUS

Unchanged:
- lower-layer adaptive learning mechanism: PRESENT/OBSERVED;
- selector-level learned-state influence: EVIDENCED;
- strong causal future-decision learning: NOT PROVEN.

