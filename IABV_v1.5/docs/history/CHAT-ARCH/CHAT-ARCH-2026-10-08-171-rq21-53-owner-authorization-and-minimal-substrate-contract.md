# CHAT-ARCH 2026-10-08-171 — RQ21.53 OWNER AUTHORIZATION + MINIMAL SUBSTRATE CONTRACT

## Provenance

Human Domain Owner decisions supplied in the current turn:
1. new bounded validation security boundary authorized = YES;
2. seven minimum guarantees authorized = YES;
3. threat boundary accepts candidate-malicious/process-delegation coverage while OS/kernel and host administrative authority remain outside the first guarantee = YES;
4. failure to demonstrate a required guarantee yields NOT VALIDATED, never PASS-by-absence = YES;
5. technology selection remains separate and is not pre-authorized by this decision = YES.

Parent canonical:
CHAT-ARCH-2026-10-08-170-rq21-52-codex-substrate-feasibility.md

Verified remote main before this writeback:
3506fdc3c4871cbc247a4e8e9bd179ee215691f7

Pinned executable baseline:
5b1d89022ee4cdc63c1f88e050f086b40a42875c
Tree:
ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61

## Owner authorization

The Human Domain Owner explicitly authorizes a new, bounded realization substrate for:
capability.sandbox.dynamic_validation

The authorization is for the guarantees and threat boundary below, not for any particular implementation technology.

## Authorized minimum guarantees

The substrate must provide:

1. Effective containment of the candidate and its attributable effects, including descendants and delegated paths such as IPC, loopback and local services.
2. Structured observation of relevant protected effect categories in E, with uncovered categories/channels unable to support PASS.
3. Protected custody and integrity of validation evidence against unauthorized modification from outside its trust boundary.
4. Inaccessibility of X to the candidate during validation, while allowing the validator/judge to retain the reference.
5. Deterministic validation of candidate-observed output against X.
6. Observation-window closure only after attributable actors are terminated/quiescent and final state verification is complete.
7. Binding evidence to the exact candidate artifact/version, relevant configuration and execution environment.

## Threat boundary

The first guarantee targets a malicious or adversarial candidate and processes/channels it can control or use by delegation.

The following remain outside the first guarantee:
- compromise of the operating-system kernel;
- compromise of the host operating-system trust root;
- host administrative authority operating outside the validation trust boundary.

This scope is an explicit first-boundary decision, not a claim of whole-host security.

## Validation failure semantics

If any required containment, attribution, observation, X secrecy, evidence-integrity, quiescence, provenance or binding condition is not demonstrated, the result is:
NOT VALIDATED

Absence of evidence cannot become PASS.

## PASS contract

PASS requires positive establishment of all required conditions:
- declared E categories are contained/observed with sufficient coverage;
- no uncovered relevant channel/category is treated as safe by omission;
- observation closes after quiescence/final state check;
- candidate identity and environment are bound to the evidence;
- X evaluation is deterministic;
- evidence integrity is preserved;
- evidence is independently verifiable rather than merely self-authenticated by the realization.

## Independent evidence boundary

R2 is interpreted as requiring that the realization's own conformance claim cannot be the sole authority for its validity.

Independence does not automatically require a second complete judge. The minimum is an evidence/observation/conformance path whose validity does not depend solely on the realization asserting that its own controls worked.

## Contract status

RQ21.53 = CLOSED / OWNER AUTHORIZED / MINIMAL SUBSTRATE CONTRACT FROZEN.

No implementation technology is selected yet.
No source code was changed by this decision.
No runtime proof exists.

## Routing

Current first open edge:
frozen bounded substrate contract → focused independent Sonnet 5.5 verification → Codex implementation

NEXT ACTOR:
SONNET 5.5

After Sonnet:
ChatGPT reconciliation → Codex implementation only if the contract survives without unresolved normative conflict.

Devin remains downstream of implementation and execution-readiness proof.
