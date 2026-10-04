# CHAT-ARCH-2026-10-03-027 — RSK-01C Reconciliation

## PROVENANCE
Source report: RSK-01C Codex fixture/contract audit.
Reported main SHA: `d0c5a1bc3a319a80bcae91450451ff0b3a0bea14`.
Independent GitHub comparison performed during reconciliation: `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442...d0c5a1bc3a319a80bcae91450451ff0b3a0bea14`.

## CORRECTION TO SOURCE REPORT
Codex reported the frozen corpus as 212 commits behind and 55 files different. GitHub compare independently returned `ahead_by=28`, `behind_by=0`, `total_commits=28`, with 13 changed paths. Therefore the numeric 212/55 statement is incorrect for this comparison.

The returned changed paths are documentation/contract surfaces only in the available compare result; no product/runtime source path appears among those changed paths. This supports the narrower conclusion that the relevant code source used for the RSK-01A audit remained unchanged across the compared range, but the report's exact commit/file counts must not be retained as fact.

## RSK-01C FINDING
The fixture/contract proposal is materially sound for the next discriminating step:
`objective → independent expected material state → evaluated retrieval → omission/staleness/currentness/routing scoring`.

Key useful conclusions:
- RSK-01B agent-reported omissions are not independent ground truth.
- completeness must be evaluated against a sealed atomic claim manifest;
- routing must distinguish global project authority from domain-local action;
- currentness/provenance and negative knowledge must be scored explicitly;
- no new permanent retrieval service is justified;
- the next test should remain document-level until the fixture can measure omission independently.

## IMPORTANT SCOPE DECISION
RSK-01C is a **fixture/contract design audit**, not proof of complete continuity and not proof of runtime causal integration.

The proposed global-vs-domain rule is best treated as an evaluation rule for the fixture unless/until the repository explicitly adopts it as operational policy. It must not silently become a new routing authority.

## FIRST OPEN EDGE
`objective → independent expected material state`

## IA DESTINO
**Codex**.

## CAPABILITY
Repository archaeology + reproducible evaluation-fixture construction / evidence manifest generation.

## NEXT ACTION
Prepare and seal the independent atomic `EXPECTED MATERIAL STATE` manifest for the fixed objective against `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`.

Do not run the blind evaluation yet.
Do not modify product/runtime code.
Do not introduce a new retrieval service.

## INDEPENDENCE CONTROL
The manifest must be generated before the evaluated Sonnet session and reviewed independently before the manifest is revealed to the scorer. The evaluated agent must not see the manifest or any prior RSK-01B transcript.

## ROUTING RECONCILIATION
The previous top snapshot route to Sonnet/RSK-01B is now superseded by this reconciliation for the next action. Historical session results remain evidence; they are not routing authorities.

## STATUS
RSK-01C fixture/contract audit: ACCEPTED WITH PROVENANCE CORRECTION.
Implementation: NOT AUTHORIZED.
Runtime continuity: NOT PROVEN.
