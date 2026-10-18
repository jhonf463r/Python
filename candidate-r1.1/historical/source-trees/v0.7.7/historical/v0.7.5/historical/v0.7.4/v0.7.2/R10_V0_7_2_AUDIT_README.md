# R10 v0.7.2 — Paquete de reparación dirigida

**Estado:** candidato documental para revisión delta independiente.  
**Gobierno:** `KEEP_BLOCKED`.  
**No es:** el artefacto v0.7.1 original de ChatGPT, ni el contrato literal v0.6.  
**Objetivo:** resolver los hallazgos D1–D6 del informe de auditoría incluido, sin reabrir la investigación general ni mezclar el trabajo M0B Entry 283.

## Contenido

- `R10_V0_7_2_RECONSTRUCTED_CONTRACT.md`: contrato normativo completo para este paquete; ya no incrusta el cuerpo de prueba antiguo que colisionaba con el registro normativo.
- `R10_V0_7_2_TEST_MATRIX_T123_T196.csv`: único registro normativo de tests; 74 IDs únicos T123–T196. Todos `NOT_RUN`.
- `R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md`: referencia v0.7 anterior con las etiquetas antiguas renombradas `REF_V07_Tnnn`; no es una fuente normativa ni una copia byte idéntica.
- `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md`: informe de auditoría suministrado, preservado como entrada `OWNER_REPORTED` / reporte estático.
- `R10_V0_7_2_AUDIT_PROMPT_FOR_CLAUDE.md`: misión de auditoría delta para Claude/Sonnet.
- `R10_V0_7_2_SHA256.txt`: hashes de estos artefactos.

## Reparaciones explícitas D1–D6

- D1: un solo registro normativo de pruebas; IDs de referencia se renombran `REF_V07_Tnnn`; T185–T196 conservan exactamente los escenarios requeridos.
- D2: evaluaciones incompatibles con el mismo paquete producen `CONFLICT_DETECTED`, no “gana el mayor seq”; conflicto, manual→AUTO, tombstone y restauración coherentes con cláusulas.
- D3: `dispatch_turn_id` autenticado es obligatorio para captura AUTO conversacional; `in_reply_to_turn_id` debe ser atestado por la plataforma. Sin ese vínculo, la captura es `UNCORRELATED`.
- D4: `strategy_lineage_id` y `result_lineage_id` tienen usos distintos y una única clave de exclusividad de contribución.
- D5: conflicto/tombstone y revocación retroactiva crean barrera de lectura y obligación durable de retractación atómicamente; ningún lector puede ver el efecto invalidado después de la aceptación de la barrera.
- D6: vocabularios de estado y generación unificados; `task_seq` es comparable solo dentro de `task_id`; `authorization_generation` y `projection_generation` son campos diferentes; resolución automática de cuarentena deshabilitada.

## Procedencia y límites

El literal R10 v0.6 no se recuperó. Las definiciones históricas exactas de I1–I12, `TS` y `PA` tampoco están disponibles; se marcan como reconstrucciones, no como equivalencia histórica probada. La matriz T123–T184 es derivada de una referencia reconstruida y se etiqueta como tal. Ningún test se ejecutó.

Las dependencias técnicas siguen `UNPROVEN`: vínculo de turnos autenticado por plataforma, atestación del modo observado, comprobación real del validador, secuenciador durable, CAS/transacciones/barreras de lectura, fencing, propagación de autorización, aislamiento heredado y replays causales.

## Orden recomendado

1. Enviar este ZIP a Claude/Sonnet para revisar los artefactos reales incluidos.
2. Exigir verificación de sus SHA-256 contra el manifiesto del paquete.
3. Revisar D1–D6 y confirmar que no quedan rutas materiales ni contradicciones de pruebas.
4. Si `FAIL`, devolver solo los defectos materiales supervivientes; no generar automáticamente otra versión.

Esta tarea no autoriza pruebas, builds, runtime, acceso M0A, cambios de código ni publicación canónica. `KEEP_BLOCKED`.
