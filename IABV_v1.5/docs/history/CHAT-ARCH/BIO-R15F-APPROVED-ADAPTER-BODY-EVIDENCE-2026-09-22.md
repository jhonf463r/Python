# BIO-R15F — Evidence and outcome

## Provenance

- Repository: `jhonf463r/Python`, subdirectory `IABV_v1.5/`.
- Required base: `23f17bd2a1895fe12412f20884951cc0b5ccebfa`.
- Branch: `codex/bio-r15f-approved-adapter-body-runtime-2026-09-22`.
- This artifact set records an admission/recovery failure only. It is not a substitute runtime experiment and does not claim R15F causal closure.

## Objective and boundary

R15F was to resume the exact real `ToolTask` produced by the R15E production route and follow real approval, adapter, and `ToolAdapter` bodies up to a synthetic runner. No app, browser, clipboard, HTTP, credentials, prompt delivery, or external effect was permitted.

## Observation

At the required R15F base commit, `IABV_v1.5/tests/experiments/test_bio_r15e_learned_preference_to_toolcard_adapter.py` is absent. The prior R15E harness is located only in its separate worktree and is not part of this base. The first R15F test draft attempted to import that external-worktree module and pytest collection failed with `ModuleNotFoundError`; the draft was removed. The committed admission test now fails closed and does not construct or execute any task.

The exact persisted task/service/repository handle therefore was not available for a valid R15F continuation. No `execute_task(... approved=True, launch_dry_run=False)` resumption was attempted. The synthetic runner received zero calls. No claim is made that the production runtime reached or caused any adapter/runner transition.

## Three-condition status

Control, treatment, and negative control were not run as R15F conditions. Their R15E prior observations are not re-run here and are not evidence of R15F approval or non-sandbox execution. Negative-control equivalence at the R15F boundary is unresolved.

## Causal classification

`PARTIAL` — admission/recovery failure; requested R15F runtime boundary remains open.

First unclosed edge: `approval → ExternalAssistantToolAdapter.run(sandbox=False)` — `OPEN`, because the exact persisted R15E task and service context could not be recovered from the specified base without importing an out-of-branch fixture or manually fabricating a task.

## Safety

- No production files/cards/configuration changed.
- No production UI, browser, process launch, clipboard, HTTP, credentials, prompt send, or external effect occurred.
- No synthetic runner was called.
- R15D/R15E were not rerun as runtime experiments.

## Negative knowledge

Not established: approval-to-adapter causality; execution of the real `ExternalAssistantToolAdapter.run` body under approved non-sandbox mode; delegation into real `ToolAdapter.run`; runner handoff; real response capture; verified response; learning; external effect; development; evolution. Availability/effective external capability remain untested and unknown.

## Environment and validation

The attempted initial collection failed because the draft imported a module absent from this worktree/base. The replacement admission test only checks that the required R15E fixture is absent and exits successfully; this is not runtime validation. See the complete stdout artifact for the exact commands and output.
