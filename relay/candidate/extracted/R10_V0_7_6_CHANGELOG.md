# R10 v0.7.6 documentary repair changelog

## Release identity

v0.7.6 is the outer documentary repair-package version. The normative contract remains logical version v0.7.5 and retains `R10_V0_7_5_CONTRACT.md` as its filename.

## Authorized repairs

- **HI-01:** changed only the contract metadata field `Artifact ID` from `R10_V0_7_4_CONTRACT` to `R10_V0_7_5_CONTRACT`; the historical v0.7.3/v0.7.4 contract IDs and the v0.7.5 contract title/body establish the version convention.
- **HI-02:** changed only T157 `crash_retry_conflict_oracle` to specify a post-durable-P2-commit crash, replay of the committed state, one visible contribution, no reapplication/revival, and explicit falsifiers. No pre-marker case was added.
- **HI-03:** replaced broad `§17` references in T222–T233 with clause references checked against the v0.7.5 contract. T229 cites only §8.2 because §17.4 describes tombstone scopes/counters and does not support its staged-plan/no-marker scenario.

## Packaging changes

Added v0.7.6 package README, change map, consistency/traceability report, static preflight report, review prompt, and regenerated manifest. Preserved the frozen v0.7.5 candidate ZIP, its full extracted tree, and historical v0.7.4/v0.7.3/v0.7.2 packages and payloads. No tests/build/runtime were run; all matrix cases remain `NOT_RUN`.