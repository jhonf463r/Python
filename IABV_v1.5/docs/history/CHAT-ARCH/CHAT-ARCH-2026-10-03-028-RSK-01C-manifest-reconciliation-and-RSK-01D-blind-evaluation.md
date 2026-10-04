# CHAT-ARCH-2026-10-03-028 — RSK-01C Manifest Reconciliation / RSK-01D Activation

## PROVENANCE
RSK-01C external report: expected material state built for frozen corpus `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`.
Reported manifest: 19 NDJSON lines / 18 atomic claims / 16,010 bytes.
Reported SHA-256: `cf298c42d86a1f3c3778fbfec4f81cbdd25355697263293c175683be0921a1b6`.
Manifest content was independently reviewed after construction; the reviewer did not independently recalculate the final SHA-256. The hash is therefore treated as **self-verified integrity metadata**, not independently attested checksum evidence.
Manifest is outside the repository and outside the evaluation corpus.

## CORRECTION / ACCEPTANCE
RSK-01C is accepted as the fixture-construction phase.
The primary methodological gap of RSK-01B is now addressed at the contract level: the expected material state exists independently of the evaluated agent's own omission report.

Remaining boundary:
`manifest content independently reviewed != checksum independently verified`.
This does not block the blind document-level evaluation because the evaluated agent will not receive the manifest or its hash; it should be preserved as a provenance caveat.

## CURRENT FIRST OPEN EDGE
`sealed expected material state → blind evaluated retrieval → independent omission/currentness/routing scoring`

## GLOBAL / DOMAIN ROUTING CONTROL
The fixed evaluation objective explicitly binds the global RSK-01 continuity mission and treats BIO-04 as domain context. A domain-specific actor may be reported as a local candidate, but the evaluator must compare the final routing against the sealed expected state and the global snapshot. The test must record an unresolved state if the corpus itself cannot justify promotion from domain-local route to global route.

## NEXT PHASE
RSK-01D is the blind evaluation phase.

**IA DESTINO:** Sonnet
**CAPABILITY:** independent repository reconstruction against a hidden expected-state benchmark.
**CORPUS:** `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`.
**OBJECTIVE:**
`En el corpus fijado, reconstruye el estado global de continuidad RSK-01 y su autoridad de routing. Usa BIO-04 M1/M2 solo para explicar qué aporta como contexto de dominio. Determina si una ruta o NEXT ACTOR histórico de BIO-04 puede reemplazar la ruta global. Enumera el estado actual, evidencia y límites, los materiales que sustentan la decisión y la siguiente acción de acuerdo con el snapshot global.`

Do not reveal the expected-state manifest, its hash, or prior RSK-01B results to Sonnet.

## STOP CONDITION
Stop after Sonnet returns its reconstruction. Do not let Sonnet score itself. The independent comparison occurs afterward.