# Handoff — targeted review of M1A v1.0.1 successor candidate

- Task ID: `M1A_CONTRACT_V1_0_1_CANDIDATE_TARGETED_ADVERSARIAL_REVIEW`
- Date: 2026-10-22, America/Bogota.
- Intended destination: Sonnet 4.6 in the Owner-reported existing Antigravity session.
- Dispatch state: `NOT_DISPATCHED`; the handoff being persisted is not evidence of invocation.
- Mode: documentary/static adversarial review only.
- Current authority: opening snapshot of [CURRENT-STATE.md](./CURRENT-STATE.md), which remains the only active-task authority.
- Review target: [M1A consolidated scope contract v1.0.1 candidate](./CHAT-ARCH-2026-10-22-M1A-consolidated-operational-block-scope-contract-v1_0_1-candidate.md), blob `4befbbb352bed35f813b9ada2d3b672cf91e328a`.
- Predecessor retained unchanged: v1.0.0 blob `8181c7c0cf6036c76cf365510e8d9665cf84e57e`.
- Finding register: [v1.0.0 review receipt/register](./CHAT-ARCH-2026-10-22-M1A-contract-v1-sonnet-review-receipt-and-finding-register.md), blob `396606e5744f0b3d0332f8ee9f02ec14cdcea588`.

## Copyable prompt for the reviewer

> **Destination:** Sonnet 4.6 in the existing Antigravity session. If the exact artifact or required inputs cannot be retrieved and identity-checked, return `NOT_DISPATCHED` or `INPUTS_INCOMPLETE`; do not claim review completion.
>
> **Task:** Perform one bounded independent adversarial review of the exact candidate `IABV-OPERATIONAL-BLOCK-SCOPE v1.0.1`, blob `4befbbb352bed35f813b9ada2d3b672cf91e328a`. This is a successor candidate derived from the `PASS_WITH_REPAIRS` report on v1.0.0. Do not treat this candidate as adopted policy; v1.0.0 remains the Owner-adopted baseline unless the canonical route is updated after review.
>
> **Bounded documentary inputs — verify the actual retrieved Git blob for each:**
>
> 1. Candidate v1.0.1 — `4befbbb352bed35f813b9ada2d3b672cf91e328a`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-consolidated-operational-block-scope-contract-v1_0_1-candidate.md
> 2. Immutable predecessor v1.0.0 — `8181c7c0cf6036c76cf365510e8d9665cf84e57e`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-consolidated-operational-block-scope-contract-v1.md
> 3. M1A v1.0.0 review finding register — `396606e5744f0b3d0332f8ee9f02ec14cdcea588`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-contract-v1-sonnet-review-receipt-and-finding-register.md
> 4. Normalized Owner design ledger — `3425144a661c713eb8898c1eacefb2d791519bc0`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md
> 5. UAAL-ROOT-001 — `2e42ce7dd1615f83cb690b226e2a27af90190751`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md
> 6. Entry 274 — `5943a87d907436fc7ecac31534cbfcd31fe7de55`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md
> 7. UAAL construction-completeness overlay — `788732f2908f63bae13be42a8359b069d42db633`: https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-UAAL-construction-completeness-traceability-overlay.md
>
> Do not inspect unrelated repository content or substitute versions. The reference to the Central M1A reconciliation document is explicitly context-only and incorporates no extra normative requirements by reference.
>
> **Review purpose:** determine whether the candidate closes every reported finding F-M1A-01 through F-M1A-08 without changing OG-M1A-01..07, weakening fail-closed behavior, inventing a presently existing runtime authority, or breaking Entry 274.
>
> **Required checks:**
>
> - F-M1A-01: a selector mismatch concurrent with catalogue/producer/schema/version/resolver validation failure can never become `PROVEN_NOT_APPLICABLE`; all denial reasons remain observable.
> - F-M1A-02: active-block-set completeness is anchored to an authenticated, versioned snapshot/attestation; a missing/unverified set differs from a verified explicit empty set; the document does not claim that the registry/service exists today.
> - F-M1A-03: every per-block outcome other than `BLOCK_APPLIES` and `PROVEN_NOT_APPLICABLE`, including `LEGACY_SCOPE_UNEVALUABLE`, forces overall denial.
> - F-M1A-04: `pre_selector_validation_status`, required stage statuses and evidence references are defined, and no unauditable status or boolean can authorize a mismatch.
> - F-M1A-05: a release artifact requires current authority, block/scope binding, expiry and revocation validation; stale cached status or unavailable revocation source denies; Entry 274's independent reader checks remain intact.
> - F-M1A-06/F-M1A-08: traceability rows unambiguously map the cases to active-set completeness, aggregation/order-independence, partial releases, evidence-not-authority and C29/C30 gate semantics. Reconcile the declared count of 38 cases.
> - F-M1A-07: the Central M1A reconciliation reference cannot silently add normative obligations outside the bounded review inputs.
> - Check every OG-M1A-01..07 decision remains unchanged; check candidate version status, case numbering, matrix mapping, vocabulary, prose consistency, positive/negative/unknown discrimination, and any newly introduced contradiction.
>
> Try to falsify the candidate with at least one concrete counterexample per repair group. Do not assume that a normative requirement proves an existing implementation. If a repair is inadequate, cite the exact candidate section and give the minimal additional repair plus a discriminating case.
>
> **Output:** exactly one verdict, `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`, followed by target/input identity and hashes, actual timestamp/timezone, review limitations, and findings with unique IDs, severity, exact section, invariant, concrete counterexample, minimal repair, discriminating case, and disposition. A PASS must explicitly remain documentary-only.
>
> **Strict exclusions:** do not scan the repository; inspect source, checkout, `data/`, SQLite, secrets, credentials or `.env`; modify files; run code, tests, build, runtime or transport; invoke another agent; merge, deploy, or release a block. Do not reopen accepted design decisions absent an actual higher-authority contradiction; if such a contradiction is found, identify it and stop that clause.
>
> Operational status remains `GOVERNANCE=KEEP_BLOCKED`, `IMPLEMENTATION=NOT_AUTHORIZED`, `TESTS=NOT_RUN`, `READ_LIST=FAIL_CLOSED`, `BRIDGE=BRIDGE_NOT_READY`. Return the report and stop.

## Acceptance and stop conditions

The coordinator will verify the review is bound to the exact candidate and required input blobs, reconcile each original finding row-by-row, classify any new finding, fetch back any subsequent documentary change, and only then route the next dependency. The v1.0.0 baseline and the report/register remain immutable historical inputs. No source/runtime/test/permission claim can be inferred from the candidate or review verdict.
