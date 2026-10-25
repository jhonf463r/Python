# Stale-route inertia — diagnosis and corrected handoff

- Date: 2026-10-24, America/Bogota
- Baseline: `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`
- Kind: coordinator-reasoning postmortem and bounded Owner decision receipt
- Evidence: direct GitHub reads plus the current Owner conversation and Owner-reported Codex result
- Status: documentation candidate unless adopted on live `main` and fetched back

## What failed in the joint reasoning

The coordinator made three linked errors:

1. **Stale-route inertia:** it treated the old `NEXT_ACTION=MAINTAIN_FAIL_CLOSED_PENDING_PREEXISTING_INDEPENDENT_ROOT_AND_MANDATE_EVIDENCE` as if a new Owner instruction could not change the allowed engineering scope.
2. **Dependency conflation:** it collapsed “no qualifying independent root is established” (so a live protected read cannot be positively authorized) into “source construction of a fail-closed authorization organ cannot proceed.” These are different predicates.
3. **Poor transition execution:** after recognizing that route state needed updating, it attempted to replace the very large `CURRENT-STATE.md` through a connector write that was blocked. It reported the blockage and stopped without producing an executable handoff. The failure of that write surface did not prove the source task impossible, but it should have been converted into a precise candidate-only state-transition step under the newly stated Owner scope.

This was not a failure of the Owner to be clear. The Owner explicitly said to stop deviating, fix the reasoning with the project’s central continuity guidance, and proceed with the next concrete task to build the trust/authorization organ.

## Correct distinction

- `ROOT_REVIEW_TERMINAL`: preserve the prior review result. It did not establish a qualifying independent root and must not be rerun without new root-and-mandate evidence.
- `SOURCE_CONSTRUCTION_AUTHORIZED`: the Owner has newly authorized bounded source-code changes and source-test authoring for the trust/authorization organ.
- `TRUST_ROOT_ESTABLISHED`: still false / not established. The new instruction does not create authority.
- `REAL_READ_AUTHORIZED`: still false. All protected reads must remain fail-closed.
- `TEST_EXECUTION / BUILD / RUNTIME / TRANSPORT`: not authorized.
- `CANONICAL_ROUTE_UPDATE`: the candidate must carry an additive top-of-file routing override and a receipt, preserving the old terminal block below as history. That override remains candidate-only until independently reviewed and adopted on live main.

Do not block construction merely because the root is missing. The organ must be built to refuse positive authorization when trust inputs are absent. Do not create a placeholder/self-issued root or treat a PR actor, a PEM-shaped key, or a generated nonce as authority.

## Owner decision — bounded source task

The Owner's current explicit instruction authorizes this bounded task:

- Preserve and continue the existing local Codex candidate reportedly at branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, HEAD `9803a282760824eae630a27561f6aed6c4b6a6bd`.
- First verify the actual Windows Codex session, repository/worktree, `origin/main`, HEAD, dirty state and exact changed paths. The reported branch/HEAD were not found on remote GitHub; do not claim independent source inspection.
- Reconcile the candidate non-destructively against the current `main` (`fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`) before further changes. Do not discard or reset the Owner's local work.
- Add a provenance-labeled branch-local routing override and decision receipt to the candidate; retain the historical terminal root-review section. Set the candidate scope to bounded source implementation + source-test authoring only, and keep forbidden operations explicit.
- Build the source chain: cryptographic verification, independently provisioned trust-anchor and mandate inputs, exact server/operation/target/policy/version/expiry binding, durable atomic one-time challenge consumption with rollback/corruption fail-closed behavior, authenticated issuer/service boundary and IPC contract, and enforcement by the actual two MCP read paths before access. G2 catalog integrity/revocation and G3 versioned target resolution must be real contracts, not labels.
- If genuine OS process isolation requires installation/ACL changes, do not perform them. Implement only what can be safely represented in source, mark the process boundary unverified, and keep positive authorization impossible until the required runtime boundary is separately authorized and verified.
- Add/update source tests but do not run them.

## Forbidden in this task

No test execution, build, runtime, protected read, network transport, credential/key creation for production, app registration, service installation/start, persistent Windows ACL/trust-store change, public tunnel, deployment, spend, publication, product PR or merge. Do not claim any gate closed.

## Required return

`TASK_RESULT=SOURCE_CANDIDATE_ONLY` with exact repo/worktree, current main, candidate base/head, ancestry merge status, worktree status, paths+blob hashes, source locations for verifier → issuer → IPC → MCP read enforcement, tests authored/not run, dependencies (none new), and gaps. Compare changed code to the earlier reported candidate; no attempt-number-only progress claims.

## Next actor and reason

**IA DESTINO: Codex, in the same Windows session that owns the local candidate.** It is the only known actor reported to have that checkout. The next prompt must perform the route-state transition and continue the bounded source slice in that checkout. Do not delegate the local edits to an agent without the candidate files. After Codex returns, the coordinator performs targeted static review of that exact delta; no broad history restart.

This postmortem records authorization for source construction only; it does not establish a root, close G1–G3, authorize execution, or make the bridge ready.
