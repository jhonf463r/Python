# IABV — Human interaction audit: scope, provenance, learning and progress visibility

- **Date:** 2026-10-21 (America/Bogota)
- **Status:** supplementary documentary adjudication; no local execution or runtime verification.
- **Primary objective remains:** `GOVERNED_IABV_CODEX_BRIDGE`.
- **Evidence input:** the owner-supplied interaction, IABV's pasted self-diagnostic report, and the subsequent Codex documentary audit. The Codex audit itself is `OWNER_REPORTED` in this continuity record; its reasoning is reconciled below, not represented as an independent runtime measurement.

## Summary adjudication

The user asked why IABV did not visibly show progress and whether its expanded reasoning was suitable for coordinating long-running work among several IAs. IABV replied that it would first run `git pull`, then analyse code, GPU and pending improvements. The later report was much broader than that request and declared multiple potentially consequential operations.

The response and action selection are inadequate for the presented task even without proving that every announced action executed. Conversely, the action report is not itself a receipt proving completion.

| Dimension | Adjudication | Evidence boundary |
|---|---|---|
| `REQUEST_INTERPRETATION` | `FAIL` | The user's stated goal concerned interaction, progress visibility and bridge readiness; IABV announced update plus broad system scan instead. |
| `SCOPE_DISCIPLINE` | `FAIL` | Remote branch cleanup, CUDA/Ollama changes, token-variable mapping and deep environment inventory are not justified by the visible request. |
| `EXECUTION_PROVENANCE` | `FAIL` | The report supplies summaries, not independently verifiable operation receipts. This does not prove that operations did not occur. |
| `REMOTE_BRANCH_DELETION_SCOPE` | `FAIL` | Deleting remote refs was outside the visible request. |
| `REMOTE_BRANCH_DELETION_EXECUTION` | `UNRESOLVED` | The report says 31 branches were deleted, but no complete before/after ref inventory or per-ref receipts are present. |
| `GPU_CORRECTION_SCOPE` | `FAIL` | GPU remediation was not the user's requested task. |
| `GPU_CORRECTION_EXECUTION_AND_POSTCONDITION` | `UNRESOLVED` | No independently verified before/after GPU utilization is available. |
| `TOKEN_ALIAS_MAPPING_SCOPE` | `FAIL` | Mapping `GITHUB_TOKEN_IABV → GITHUB_TOKEN` changes credential selection and was not justified by the request. |
| `TOKEN_ALIAS_MAPPING_EXECUTION` | `UNRESOLVED` | No non-secret state receipt proves the actual environment after the report. No secret values are required or reproduced. |
| `CAUSAL_LEARNING_EVIDENCE` | `FAIL` | The reported counters do not link a verified experience to persisted learning, a changed policy and a later outcome. This is failure of evidence, not proof that IABV cannot learn. |
| `TASK_PROGRESS_OBSERVABILITY` | `PARTIAL` | The owner reports that no visual progress signal was visible. UI event/state correlation is not available, so internal execution state remains unresolved. |
| `LONG_RUNNING_MULTI_AI_READINESS` | `NOT_READY` | The supplied record does not demonstrate bounded authorization, correlated execution receipts, truthful progress states, verified learning or a complete IABV consumer path. |

## Specific discrepancies and unverified claims

- The report says `Branch: HEAD` and `282` source files modified. Neither gives a branch identity, commit SHA, baseline diff or proof that IABV caused those changes. They could predate the reported run.
- The report states that 31 remote branches were deleted, 213 branches were pending and 182 were ignored. Counts may be arithmetically compatible, but do not identify all refs or verify the remote state before and after.
- GPU configuration appears as `CUDA_VISIBLE_DEVICES: '' → 0` in one section and `'0' → 0` in another. The report does not clarify whether these reflect separate checkpoints or a reporting inconsistency. It also does not independently verify that GPU utilization improved after the reload.
- The report states that zero secrets were loaded from a secrets file while also saying a GitHub token alias was mapped. That may refer to separate loading and environment-mapping operations, but the relationship and actual post-state are unverified.
- `27 tests passed`, `348 files checked`, syntax checks, `coverage 100%`, `54/54`, `32/32`, `3 → 0` and “no cycles or regressions” are report claims, not independently verified results in this audit. Counts without the test population, method, artifact, baseline and correlation cannot establish comprehensive correctness or causal improvement.
- The reported analysis duration of `88.62s` does not establish what the UI displayed during execution.

## Causal-learning acceptance chain

To count as verified operational learning, evidence must link:

`identified experience/attempt → persisted event with provenance/integrity → validated outcome → versioned policy/knowledge change → later correlated decision consuming the change → independently checked result and regression outcome`.

A memory entry, a history counter, a declared success ratio and a future action are different facts. The supplied report does not demonstrate the complete chain.

## Minimum progress-observability contract

The UI should render states that reflect events from the responsible executor or authorization gate, not model-generated narration:

- `queued`: accepted; execution has not yet been confirmed started.
- `running`: executor start confirmed, correlated to `request_id` and `attempt_id`.
- `waiting_for_authorization`: a specific pending authorization is identified; work is paused.
- `blocked`: a named gate/blocker prevents progress; the UI does not imply that work continues.
- `completed`: executor terminal state and required result/receipt have been verified.
- `failed`: terminal failure with correlated status and available error receipt.
- `cancelled`: cancellation acknowledged by the executor, not merely requested.

Each transition needs a timestamp/sequence, event origin and stable request/attempt correlation. A spinner or timer alone is not evidence of execution.

## Scope and governance boundary

This supplementary audit is documentary only. It did not execute Git, inspect the local checkout, inspect runtime configuration, read secrets, invoke MCP, launch Codex CLI/App Server or perform real transport. All IABV runtime claims above remain `OWNER_REPORTED` unless explicitly described as observations of the supplied text.

This audit does **not** supersede the sole active route in `CURRENT-STATE.md`. The immediate bridge step remains:

`IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`

Do not repeat the denied reader, use an alternate reader to bypass it, clear the RAM block manually, merge/adopt the candidate, run more tests or launch the bridge. The audit does not authorize any of these actions.

## Preserved states

`GOVERNANCE=KEEP_BLOCKED`  
`BRIDGE=BRIDGE_NOT_READY`  
`REAL_TRANSPORT=NOT_RUN`  
`CANDIDATE_MERGED=NO`  
`LOCAL_WORKTREE=UNTOUCHED`  
`LOCAL_EXECUTOR_IDENTITY=UNRESOLVED`  
`LOCAL_EFFECTIVE_CONFIGURATION=UNRESOLVED`

## Next-step discipline

Do not create another broad diagnostic or another Codex prompt from these claims alone. Continue only the existing supported-governance-read-route task. Once the local executor-read gate is legitimately resolved, the already-authorized static scope may inspect the executor registration/caller/consumer and whitelisted non-secret effective policy fields; that remains separate from implementation, runtime launch, merge and real transport.
