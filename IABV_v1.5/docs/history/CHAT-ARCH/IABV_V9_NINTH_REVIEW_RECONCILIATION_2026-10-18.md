# IABV → Codex — Adjudicación de la novena revisión documental

**Fecha de referencia:** 2026-10-18 (America/Bogota)  
**Gobierno:** `GOVERNANCE = KEEP_BLOCKED`  
**Puente:** `BRIDGE_NOT_READY`  
**Implementación:** `IMPLEMENTATION = NOT_AUTHORIZED`

## 1. Identidad y procedencia

El coordinador volvió a medir el paquete v9 en el espacio de trabajo:

- Artefacto: `IABV_CODEX_contract_review_bundle_v9_2026-10-18.md`
- Tamaño: 177,272 bytes
- Líneas: 892
- SHA-256: `3fdfd2f6ea3ca6b38f179341b5807e70c95bdde1e8486b0a047032832d0c5e17`
- Resultado: `BYTE_HASH_VERIFIED`

El informe de novena revisión fue suministrado en la conversación y declara `PASS`. No se recibió como artefacto separado con hash propio; por eso el texto del dictamen y la identidad/independencia del revisor se conservan como `OWNER_REPORTED`. La verificación del hash del paquete demuestra identidad de sus bytes, no por sí misma la verdad del dictamen.

## 2. Reconciliación del resultado

La revisión recibida no presenta hallazgos supervivientes. El cotejo del coordinador con las secciones correspondientes de v9 confirma estos puntos focales:

- **N-80/N-85 (proyección y autoridad):** el paquete prohíbe que `LedgerProjector` sustituya la autoridad de `NonRollbackReservationLog`; ante falta de respuesta, el uso queda `USE_UNKNOWN`, el dominio `DOMAIN_BLOCKED_PENDING`, no hay despacho y el lock no se libera por proyección. v9 etiqueta N-85 como `OPTIONAL_CLARIFICATION` porque el comportamiento ya estaba cubierto en v8. No se declara un defecto semántico nuevo por la mera repetición local de la regla.
- **N-81 / F-V8-02:** la transición `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` existe en el v8 exacto y en v9. El informe de octava revisión afirmó que faltaba, pero la fuente contradice esa afirmación. No se duplica la fila ni se crea una reparación ficticia.
- **N-83/N-86 (lista manual):** §2.6, paso 3, permite la lista manual exacta sin inventario; esa ruta no sustituye `MaterializationAuthorization` ni otros pasos aplicables. v9 etiqueta N-86 como aclaración opcional porque la ruta alternativa ya estaba permitida en v8.
- **N-87 (exclusividad de cuenta/servicio):** §2.12 especifica qué debe contener la evidencia admisible de una capacidad de lock/lease del lado del servicio que cubra los canales manuales y automáticos. Es una mejora documental concreta; no demuestra que tal capacidad preexistente exista.
- **N-01–N-79 y otros estados históricos:** se conserva la procedencia histórica indicada en el paquete. Los números de estados heredados y los contraejemplos que solo sobreviven en resúmenes no se elevan a hechos independientemente probados por el hecho de que esta revisión haya declarado `PASS`.

## 3. Estado de revisión y de implementación

- `NINTH_REVIEW_RESULT = PASS_REPORTED`
- `SOURCE_IDENTITY = BYTE_HASH_VERIFIED`
- `FOCUSED_COORDINATOR_CROSSCHECK = CONSISTENT_WITH_V9_FOR_N-80–N-87_AND_F-V8-02`
- `N-85 = ALREADY_COVERED / OPTIONAL_CLARIFICATION`
- `N-86 = ALREADY_COVERED / OPTIONAL_CLARIFICATION`
- `N-87 = DOCUMENTED_REQUIREMENT; CAPABILITY_NOT_DEMONSTRATED`
- `SEMANTIC_ACCEPTANCE = NOT_ESTABLISHED`
- `IMPLEMENTABILITY_EVIDENCE = NOT_DEMONSTRATED`
- `NONROLLBACK_RESERVATION_LOG = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CAPABILITY_IS_EVIDENCED`
- `ACCOUNT_EXCLUSIVITY_VS_EXTERNAL_ACTORS = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_A_PREEXISTING_SERVICE_SIDE_LOCK_IS_EVIDENCED`
- `LOCAL_PREFLIGHT = NOT_AUTHORIZED_BY_THIS_TASK`
- `TESTS = NOT_RUN`; `BUILD = NOT_RUN`; `RUNTIME = NOT_RUN`; `CODEX_AUTHENTICATION_OR_USAGE = UNVERIFIED`

El resultado permite registrar que la novena revisión documental declara el contrato v9 coherente dentro del alcance examinado. No equivale a certificación de todo el historial, aceptación operativa, autorización del propietario para avanzar ni prueba del puente ejecutable.

## 4. Decisión sobre v10 y siguiente paso

**No crear v10 automáticamente.** No se han reportado defectos documentales supervivientes que justifiquen otra versión. Mantener v9 como candidato documental revisado y este archivo como adjudicación suplementaria. Solo producir un nuevo delta si aparece un contraejemplo concreto, una contradicción verificable o una decisión explícita del propietario que cambie el alcance.

El siguiente trabajo no es enviar prompts a Codex ni realizar un preflight. Es mantener la separación entre:

1. contrato documental revisado;
2. evidencia admisible preexistente de cada capacidad bloqueante;
3. autorización explícita para cualquier fase posterior;
4. aceptación y promoción separadas, si alguna vez se autorizan.

No se ha cambiado `main`, PR #467, PR #468 ni ninguna otra rama de GitHub. No se han ejecutado código, pruebas, builds, runtime, Codex, App Server, preflight ni canarias. No se ha inspeccionado checkout, `data/`, SQLite, secretos, credenciales ni entorno local.

## 5. Objetivo y trazabilidad que deben sobrevivir entre chats

Objetivo del puente: permitir que una tarea originada en IABV recorra una cadena gobernada de instrucción autorizada, identificación de origen, materialización controlada, lanzamiento confinado, recibo independiente, verificación IABV, decisión explícita del propietario y, solo si se autoriza por separado, promoción.

Cadena causal a preservar:

`objetivo/contexto → evidencia/procedencia → hipótesis/límites → acción autorizada → observación → reconciliación → persistencia/reutilización`.

Aprendizajes metodológicos no negociables:

- Buscar primero en los adjuntos/artefactos del turno, después en Library por nombre exacto y, por último, en la fuente canónica; una ausencia en GitHub no demuestra que el archivo no exista en Library.
- Verificar hash y tamaño del archivo exacto antes de revisar; después cotejar cada hallazgo con la sección, frase o transición exacta.
- No confundir identidad de bytes con verdad, autoría o independencia de un informe.
- No aceptar una alegación de ausencia en una tabla sin buscar la transición en el archivo fuente; F-V8-02 es el ejemplo concreto.
- No heredar `CLOSED` por inercia ni inventar los contraejemplos históricos que no se puedan recuperar; usar `NOT_RECOVERED` cuando corresponda.
- Una aclaración documental no prueba que exista la capacidad técnica nombrada.
- No editar/publicar la memoria canónica de GitHub sin autorización explícita; este archivo es un handoff suplementario, no una actualización de `CURRENT-STATE`.

## 6. Pendientes separados

- **R10 v0.7.4:** el informe derivado de las 99 evaluaciones permanece `OWNER_REPORTED / NOT_ASSEMBLED / NOT_PUBLISHED` hasta recuperar y reconciliar las filas exactas.
- **Candidate C:** el dictamen sigue `OWNER_REPORTED / VERDICT_NOT_EMITTED` hasta recuperar su evidencia exacta. No inferir su resolución a partir del cierre documental v9.
