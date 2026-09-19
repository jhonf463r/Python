# CHAT-ARCH 2026-09-19-001 — L5 Final Independent Forensic Audit

## PURPOSE

Canonical writeback of the independent Sonnet 5 Low adjudication of the L5 causal-learning experiment and its evidence/provenance closure.

## TARGET

Evidence branch: `l5-evidence-capture-3241b3ef6`
Publication commit: `97bb60b71a3ed438021cb18acf55111d7c71265a`
Parent: `caaf23c4b380d2228b3f5a7e494e66419b6934fb`

Runtime artifact:
`IABV_v1.5/l5_evidence/l5_experiment_20260918_022256_runtime.txt`

Original/remote artifact identity independently verified by Sonnet from Git bytes:
- size: 17617 bytes
- SHA-256: `61c56fd0404469dec60cb29827546b23011d93d4942ce5470c83a705d1628ef2`

## TESTED CODE PROVENANCE

The runtime artifact records:

`TESTED_HEAD = 70553010bafca96e98b7dc5b113eed4f3ad84e8b`

`PARENT = 3241b3ef65630f2f863d532d75ae816349e18584`

Sonnet independently verified both commits and their exact parent relationship.

The Windows E2E test at the tested SHA has blob:
`78e54fa995d011ffb3c69cc1e7b04153888c7e51`

The separate selector-only test has blob:
`2844537f80c190a1351dac3a95f35f80cf79dc19`

These are distinct artifacts; the captured runtime evidence comes from the Windows E2E test.

## VERIFIED CAUSAL CHAIN

The independent audit established:

`real G3 execution → independently observed world effect → VerifiedTransition → persistence → cold reload → normal production InteractionModeSelector.select() → multiple candidates → winner change`

Observed execution included real Ollama provider interaction, real authority/process identity observation, execution/run/lease identities, filesystem mutation, independent filesystem observation, transition persistence and fresh reload.

## CAUSAL ATTRIBUTION

The apparent `cost 0.40 → 0.75` anomaly was a false comparison: the printed Reason line describes the winning candidate for each round. Control's winner was `aider_coder` (CODE_EDITOR cost 0.40); treatment's winner was `mcp_client` (MCP_CLIENT cost 0.75). No candidate changed type or cost.

For the actual `mcp_client` candidate, the selector source shows constant values for the non-learning terms. The only changing score channels were:

- stability: 0.55 → 1.00
- frequency: 0.00 → 0.125 (reported rounded to 0.12)
- learned_pattern: 0.00 → 1.00

These derive from the persisted InteractionPattern containing the verified-transition success. Independent arithmetic reconstructs:

`0.45×1.5 + 0.125×0.6 + 1.0×1.8 = 2.55` (within displayed rounding)

matching the observed winner/score change.

Therefore the L5 decision change is causally attributable to the persisted verified experience, not to an uncontrolled cost/type mutation.

## PRIMARY CLASSIFICATION

**L5 = PROVEN** for the canonical selector-level causal-learning claim.

This closure is scoped carefully:

- It proves verified experience can survive persistence/reload and alter a future competitive selector decision under the tested control/treatment conditions.
- It does NOT prove L6 (the changed decision causes changed real behavior).
- It does NOT prove L7 (world outcome caused by the changed decision and independently verified at that later stage).
- It does NOT close P0-B adversarial authority security or I0/I1/I2 external-agent orchestration.
- `REAL AUTHORITY = NOT PROVEN BY G3` remains valid as a separate security/provenance boundary unless independently closed.

## KNOWLEDGE DELTA

### Delta-K

L5 selector-level causal learning is now independently verified and can be promoted from candidate/pending audit to PROVEN.

### Delta-Pi

Do not reopen the cost/type confound unless new contradictory evidence appears. When reading selector evidence, distinguish the winning candidate's score breakdown from a longitudinal decomposition of one candidate.

### Delta-B

Publication and byte provenance are closed for the captured L5 runtime artifact.

### Delta-Y

No new external-world claim is made beyond the already captured G3 effect. The new result is an epistemic/causal adjudication of the selector-learning claim.

## NEXT FRONTIER

The next work should not be another L5 reproduction. The scientific proof track can advance to L6 when useful.

In parallel, the symbiosis inflection track may begin its minimum I0/I1 experiment without waiting for L6/L7 closure. The preferred first experiment is a bounded, real IABV→Devin round trip through existing adapters/briefing/orchestration, with provenance and independent verification, not creation of a new orchestration subsystem.
