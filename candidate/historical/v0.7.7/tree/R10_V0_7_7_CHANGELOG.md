# R10 v0.7.7 changelog

Outer package identity: v0.7.7. Logical contract identity and filenames remain v0.7.5.

- **HI-01:** the logical contract metadata identifies `R10_V0_7_5_CONTRACT`; no normative clause changed.
- **HI-02:** T157 retains a post-durable-P2-commit crash oracle: committed C1/C2 state persists, exactly one contribution is visible, replay does not reapply effects or revive C1, and falsifiers cover duplicate application, divergence and revival. No pre-marker crash was introduced.
- **HI-03:** T222–T233 normative bases are written to the actual twelfth field using a CSV parser/writer. Each record has 12 fields; the accidental thirteenth field from the failed v0.7.6 serialization is absent. T229 cites §8.2 alone.
- **v0.7.6 disposition:** frozen and superseded for this task after the coordinator identified 13 fields in T222–T233; its earlier author preflight is not accepted as valid. v0.7.6 bytes and relay were not altered.
- **Packaging:** new v0.7.7 README, change map, consistency/traceability report, preflight report, manifest and review prompt; preserved source packages/payloads are byte-identical.

All documented cases remain `NOT_RUN`; no product code, tests, build, runtime, probes, migrations, dispatcher or bridge were executed.
