# R10 v0.7.5 changelog

- Reidentified candidate contract and matrix; §0 no longer names v0.7.3 as current. Matrix registry is T123–T246.
- §17 separates execution and result state machines, RESULT_RECORDED from RESULT_ACCEPTED, defines durable capture rejection/stale/timeout records, correlation_status, duplicate turns, conflict digest semantics, and deterministic rejection precedence; T200,T230–T232; T238–T240.
- §17.3 separates QUARANTINE_RELEASED from CONFLICT_RESOLVED and requires independent resolver, restores_event_id and fresh IDs; T184.
- §17.4 fixes CONTRIBUTION_ONLY vs RESULT_AND_LEARNING pointer/counter effects; T205,T233.
- §17.5 defines pre/post-marker recovery with retry prohibition when participant effect is uncertain; T156,T158,T159,T177,T192,T212. No cross-store exactly-once claim.
- Matrix removes redundant expected_final_state/evidence_required/fixture_discriminant columns and BOM; setup, oracle, closure evidence and discriminator now have distinct schema meanings. Generic crash placeholders replaced row-by-row with scenario-specific recovery-not-applicable reasons or explicit recovery fault models.
- Repairs: T134 (B criteria failure separated from lineage independence); T179 CRITERIA_MISMATCH; T184 conflict restoration; T200 second turn claim UNCORRELATED; T205 scope and deltas; T210 +1 contribution; T212 coherent pre-marker crash; T221 sample-only; T222 lift-only; positive controls T223–T225; independent negatives L1/L2/L4 T226–T229; split route/mode and dispatch/revocation cases T234–T237; policy/history boundary T238–T240.
- T230 same-ID/different-digest conflict, T231 result/execution lifecycle, T232 rejection precedence; T233 RESULT_AND_LEARNING tombstone scope.
- F-07 and F-10 remain open. F-04/F-11 remain documentary repairs with notes; F-12 is proposed and pending independent review; F-14 preserves missing-source caveats. Original Claude report remains NOT_RECOVERED.
- Historical v0.7.4, v0.7.3 and v0.7.2 ZIPs and extracted trees copied unchanged. All matrix rows remain NOT_RUN. No product code, tests, builds, runtime or probes executed. Governance KEEP_BLOCKED.

- Final adversarial decomposition: T143/T230 separate idempotent replay from digest conflict; T154/T241 separate absent criteria from unresolved bundle content; T170/T242/T243 separate missing receipt, invalid attestation, and wrong execution binding; T176/T244 separate cross-execution old parent from late output on terminal execution; T187/T245 separate NO_RESULT from sandbox-only diagnostics; T201–T204/T206 separate positive predicates from existing negative controls; T238–T240 enforce deterministic precedence.

- Independent-path decomposition added T241–T246: missing frozen bundle content; invalid validator signature; dispatch-receipt execution misbinding; durable late output after abandonment; sandbox-only diagnostic; and L0 missing-execution negative. T240 now asserts deterministic AUTHORIZATION_REQUIRED precedence when authorization and policy registration both fail.
- Added explicit codes `DISPATCH_RECEIPT_INVALID`, `VALIDATOR_ATTESTATION_INVALID`, and `VALIDATOR_UNAUTHORIZED` and their deterministic precedence in contract §17.2.
