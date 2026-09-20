# IABV v1.5 — I0 PHASE A R2 INDEPENDENT AUDIT

## DATE
2026-09-20

## RESULT

**B — PARTIALLY VERIFIED**

Sonnet independently verified the preserved R2 artifact, its Git lineage and byte integrity, and reconciled its claims against the exact tested source revision `4710a668541225ffe3b9d1335d31bb5da8b1e685`.

## VERIFIED

- R2 artifact is remotely readable.
- Artifact preservation commit: `99d670b0dd2ecea04bc691e09bb2444c7721bff7`.
- Preservation commit is exactly one commit after tested code and adds only the JSON artifact.
- Artifact SHA-256: `8ed7b1e43065a85d91142350ad82b28f9d8fba82075ddeb74c330a71bd3fd074`.
- Embedded target SHA/branch/parent match independently verified Git lineage.
- Production `_resolve_devin_api_key()` and its wiring are consistent with the artifact's resolver claim.
- Production `DevinApiToolAdapter.run()` has an empty-api-key gate before HTTP.
- The artifact contains no secret material.

## EVIDENCE STRENGTH

The artifact is **process-generated and repository-preserved**, but it remains self-attested runtime evidence. No independent OS/process trace directly proves that the exact Windows process recorded the reported environment at the stated time.

Therefore:

`artifact integrity ≠ runtime truth`.

The strongest justified statement is that the R2 runtime report is authentic/preserved and fully consistent with the target source, but the environmental observation remains self-attested rather than independently observed.

## FIRST OPEN CAUSAL BOUNDARY

`real credential availability → authenticated/authorized external request`

The currently reported environment has no real credential and therefore no real authentication was attempted.

No external Devin execution has been proven.

## SECONDARY FINDING

`account_resource_scanner.py` contains multiple Devin credential-check implementations with different variable coverage. Sonnet found no evidence that the divergent path participated in this Phase-A execution.

Classification: **non-causal auditability debt**, not current blocker.

Do not repair it unless future evidence shows causal participation.

## CURRENT I0 STATE

- canonical assistant↔tool/resource-resolution seam = CLOSED / VERIFIED EFFECTIVE;
- Phase-A artifact provenance = CLOSED;
- Phase-A runtime evidence = B / PARTIALLY VERIFIED;
- real credential availability = OPEN;
- authentication = NOT TESTED;
- authorization = NOT TESTED in this experiment;
- real transport/external effect = NOT PROVEN;
- I1 = NOT REACHED;
- I2 = NOT REACHED.

## NEXT ACTOR

**DEVIN**

Reason: the remaining uncertainty is a real Windows/runtime credential and external-connection boundary, which matches Devin's demonstrated execution capability.

The next experiment must use an already securely provisioned real Devin credential if one exists in the controlled Windows runtime. Do not expose, commit, print or derive the secret.

If no real credential is present, record the environmental blocker and stop.

After a real credential is present and the runtime reaches the next boundary, stop at the first causal break and produce a raw evidence artifact for Sonnet.

## NEGATIVE KNOWLEDGE

Do not infer:

- I0 from resolver/resource code;
- authentication from credential presence;
- authorization from authentication;
- external effect from HTTP success;
- result truth from external output;
- I1 from I0;
- I2 from I1;
- development inflection from automation alone.

L5 selector-level causal learning remains separate and previously closed. P0-B authority remains a separate security boundary.
