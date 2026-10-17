# R10 v0.7.3 changelog

## From supplied v0.7.2 package

- Added explicit precedence: reconstructed contract is normative; matrix is the sole test-ID registry; inconsistent matrix rows must be corrected and cannot override the contract. v0.6 remains unrecovered.
- Removed unsupported `FAILED`, `ABORTED`, and `TIMED_OUT` execution states. Infrastructure timeout/crash without accepted terminal output remains diagnostic; it creates no automatic negative learning.
- Made missing authenticated `dispatch_turn_id` a fail-closed pre-dispatch rejection (`DISPATCH_TURN_ID_REQUIRED`) and added T197 with zero effects.
- Clarified that only authenticated parent-turn equality plus all session, receipt, nonce, captor, completeness, and terminal-slot checks can yield `CORRELATED`; `UNCORRELATED` is not an eligible result.
- Specified immutable validation evidence references bound to execution/result/check, complete frozen check-set coverage, exact digest comparison, and explicit `UNPROVEN` validator execution.
- Defined strict abandonment boundary (`accepted_at > abandon_deadline_at`); equality is not due. Removed nonce-expiry as an unsupported transition.
- Clarified canonical plan/contribution states, invisible drafts, exact-plan recovery under unchanged guards, conflict-resolution non-activation, and fresh IDs for any restoration.
- Normalized matrix cases for producer event identity, criteria bundles, plan state, authorization-generation mismatch, crash recovery, MANUAL/AUTO separation, tombstones, and attribution.
- Repaired incomplete T124–T126 oracles, removed stray section headings from test cells, added a `normative_basis` column, and preserved T123–T196 IDs while adding T197.
- Corrected I4/I10/I12 test traceability mapping.
- Preserved all seven supplied v0.7.2 archive entries unchanged under `historical/v0.7.2/`.

## No runtime changes

No product code changed. No tests, builds, runtime, services, migrations, probes, transport, M0A, dispatcher, provider or physical bridge were run or activated. All candidate matrix entries remain `NOT_RUN`; this changelog records documentary edits only.
