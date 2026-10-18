# R10 v0.7.6 consistency, provenance and traceability

## Identity and provenance

This is a new v0.7.6 documentary repair package based on the exact v0.7.5 candidate ZIP at source commit `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`. The v0.7.5 ZIP and v0.7.4/v0.7.3/v0.7.2 source ZIPs were downloaded and byte-verified before editing; exact measurements are in the preflight report. The contract remains logical v0.7.5; only the package is v0.7.6.

Historical convention evidence: the extracted v0.7.3 and v0.7.4 contracts declare `R10_V0_7_3_CONTRACT` and `R10_V0_7_4_CONTRACT`; the v0.7.5 contract title/body identify the logical contract as v0.7.5. Thus HI-01 repairs the stale metadata to `R10_V0_7_5_CONTRACT`, not `.7.6`.

## HI-01–HI-03 disposition

- **HI-01:** one opening metadata value changed; no normative clause changed.
- **HI-02:** only T157's crash/retry/conflict oracle changed. Its preconditions already assert P2 committed, C1 retracted, C2 active and a durable commit record. The replacement specifies only a post-marker crash and replay of committed state. No pre-marker condition is mixed into T157.
- **HI-03:** T222–T233 now cite specific contract provisions, verified against the actual v0.7.5 contract text. T229 cites §8.2 only: that clause expressly says partial writes remain invisible and specifies pre-commit recovery. Proposed §17.4 is about tombstone scopes and counters and does not support T229. The change map records this narrowing.

## Status and limits

All 124 rows T123–T246 remain `NOT_RUN`. The static matrix parse, cell-diff, manifest, archive safety/CRC, historical identity, and cross-reference checks are recorded in `R10_V0_7_6_PREFLIGHT_REPORT.md`. These checks establish documentary consistency and byte integrity only. They do not verify normative sufficiency, implementation, validator authority, durable storage, atomic recovery, runtime behavior, or product efficacy.

Retained states: v0.7.2 `FAIL`; v0.7.3/v0.7.4 `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.5 `REQUIRES_REPAIRS / NOT_ACCEPTED` and frozen; v0.7.6 pending independent review; F-07/F-10 `OPEN`; F-12 proposed/unresolved; SC-10 `PARTIAL`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.