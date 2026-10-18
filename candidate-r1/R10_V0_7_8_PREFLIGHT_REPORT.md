# R10 v0.7.8 static preflight report

Status: `DOCUMENTARY_CANDIDATE_CREATED_PREFLIGHT_COMPLETE_PENDING_COORDINATOR_RECHECK` only after all reported checks below are confirmed. This is documentary/static verification; no test case has passed.

## Required source identities

| Source | Bytes | SHA-256 | Result |
|---|---:|---|---|
| v0.7.7 candidate | 1,248,405 | `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf` | PASS |
| v0.7.5 candidate | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` | PASS |
| v0.7.4 candidate | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` | PASS |
| v0.7.3 candidate | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` | PASS |
| v0.7.2 source package | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` | PASS |

All were fetched from commit-pinned URLs at `5534761ac877ee2f5b1f56ba354e4b09b760b717`. Hashes are over received bytes. Historical copies are checked against these source bytes.

## Static checks

| Check | Result | Scope |
|---|---|---|
| ZIP CRC and safe unique paths | PASS | Five required source ZIPs and final candidate ZIP; no absolute, drive, parent-traversal or duplicate paths |
| Source manifests | PASS | Every embedded manifest in source extractions checked against its payload bytes, sizes and SHA-256; v0.7.5 and v0.7.7 root manifests checked |
| Historical preservation | PASS | Source ZIP copies byte-identical; extracted source trees byte-identical; v0.7.7 full extraction preserved |
| Strict matrix parse | PASS | 124 rows, IDs T123–T246 unique/contiguous, 12 unique columns and 12 fields on every record |
| Execution statuses | PASS | All 124 values are `NOT_RUN` |
| HI-03 bases | PASS | T222–T233 normative bases are in field 12; no surplus field |
| F1/F2 state alignment | PASS | §§3.3/12/17.1 aligned; T132/T136/T137/T138/T176/T231/T244 dispositions checked against clauses |
| F4 thresholds | PASS | T221/T222/T224/T225 individually state supplied scalar, inclusive lift threshold, both sample floors, values and one predicate |
| F5 labels/oracle framing | PASS | Exactly the specified 20 prefixes removed; four initial-state oracle framings normalized; category/provenance unchanged |
| T157 HI-02 retention | PASS | Scenario retitled; preconditions, crash oracle and 0/0 deltas equal v0.7.7 parsed values |
| Parsed matrix delta | PASS | Full field-level delta against v0.7.7 recorded in `R10_V0_7_8_FULL_DIFF_V0_7_7.md`; only authorized changes appear |
| Contract diff | PASS | Full line diff is recorded in `R10_V0_7_8_FULL_DIFF_V0_7_7.md`; only version/provenance and scoped F1/F2 changes appear |
| Candidate manifest and ZIP/tree agreement | PASS | Payload sizes/hashes checked; self-entry omitted; every archive member equals extracted bytes |
| Remote readback | Relay-level verification | Performed after publication from immutable artifact commit and recorded in the relay readback report; not embedded recursively in this candidate ZIP |

## T222–T233 field-12 audit

The row-level exact values are listed in the matrix and verified by the strict parser: T222 `§17.7`; T223 `§1.3; §8.3`; T224 `§17.7`; T225 `§17.7`; T226 `§4.1; §17.2`; T227 `§7.1; §17.2`; T228 `§7.1; §17.2`; T229 `§8.2`; T230 `§2.2; §17.2`; T231 `§12; §17.1`; T232 `§17.2`; T233 `§8.3; §17.4`.

## Limits

The immutable relay commit, candidate ZIP digest, commit-pinned links and remote download/CSV reparse are recorded in the separate relay index/readback report. Those checks are required before the overall task outcome is declared complete.


All 124 cases remain `NOT_RUN`. ZIP/manifests and parsed text checks establish documentary integrity only. They do not verify implementation, runtime behavior, cross-store atomicity, exactly-once effects, operational efficacy, validator authority, recovery, bridge readiness, or acceptance. The lift formula from raw observations remains unspecified; the four fixtures treat lift as a fixture-supplied scalar. v0.7.6 remains the frozen external failed-preflight artifact and was not modified or reverified here. v0.7.7 remains frozen and `REQUIRES_REPAIRS / NOT_ACCEPTED`.

`PRODUCT_CODE_EXECUTION = NOT_RUN`; `TESTS = NOT_RUN`; `BUILD = NOT_RUN`; `RUNTIME = NOT_RUN`; `GOVERNANCE = KEEP_BLOCKED`.
