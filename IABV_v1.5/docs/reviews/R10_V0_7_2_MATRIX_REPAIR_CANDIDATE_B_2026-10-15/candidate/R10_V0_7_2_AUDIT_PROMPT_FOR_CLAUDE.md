# DESTINO EXPLÍCITO: CLAUDE/SONNET
## R10 v0.7.2 — revisión delta independiente de D1–D6

Inspecciona los archivos reales de este paquete. Comprueba primero los hashes del manifiesto contra los bytes reales, no contra valores copiados en un informe. El ZIP y sus archivos están disponibles adjuntos al prompt.

### Continuidad y alcance

El contrato literal v0.6 y la matriz histórica original no se recuperaron. No afirmes equivalencia histórica. El archivo `R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md` es un documento de referencia no normativo y sus test labels `REF_V07_Tnnn` no son los IDs de la matriz actual. El único registro normativo de pruebas es `R10_V0_7_2_TEST_MATRIX_T123_T196.csv`, con T123–T196. No accedas a M0A, no ejecutes tests, builds, código, shell o runtime, ni modifiques el repo o documentos canónicos.

### Revisión dirigida

Audita solo el cierre de los seis defectos del informe `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md`:

- D1: unicidad global/inequívoca de IDs de prueba y ausencia de identificadores asignados a escenarios incompatibles.
- D2: ausencia de oráculos que contradigan el contrato, incluyendo selección por mayor seq, conversión MANUAL→AUTO, recuperación por nuevo strategy lineage y resolución automática de cuarentena.
- D3: `dispatch_turn_id` obligatorio/autenticado para AUTO conversational capture y `in_reply_to_turn_id` atestado por la plataforma; sin vínculo, `UNCORRELATED`.
- D4: separación de `strategy_lineage_id` y `result_lineage_id`, y una única clave normativa de exclusividad de contribución.
- D5: barrera de visibilidad y trabajo durable de retractación atómicos para conflicto/tombstone/revocación retroactiva; ningún selector observa efecto invalidado durante caída.
- D6: vocabularios de estado, autoridad independiente, `authorization_generation` frente a `projection_generation`, modos y secuenciación por tarea sin comparaciones entre secuencias locales.

Comprueba además si SC-1–SC-10 quedan cerrados por reglas ejecutables en términos lógicos, no por meras promesas. Revisa T123–T196 en busca de marcadores vagos, oráculos disyuntivos, campos sin estado final, deltas no especificados y contradicciones. Para T185–T196 confirma los escenarios fijados en el README y la matriz.

No aceptes como suficiente una frase “la operación es atómica” si la especificación no determina qué lectores ven antes/después, qué registro se escribe en la transacción, y qué hace la recuperación. Si una capacidad técnica no está demostrada, conserva `UNPROVEN`, pero examina si el comportamiento contractual está bien definido.

### Salida

1. `INPUT_ARTIFACTS_AND_HASH_VERIFICATION`
2. `D1_D6_DELTA_VERDICT`
3. `SC1_SC10_STATUS`
4. `TEST_MATRIX_AUDIT_T123_T196`
5. `REMAINING_CONTRADICTIONS_AND_MINIMAL_REPAIRS`
6. `IMPLEMENTATION_DEPENDENCIES_UNPROVEN`
7. `ACCEPTANCE_DECISION`
8. `AUTHORIZATION_BOUNDARY`

Dictamen `PASS`, `PASS_WITH_REPAIRS` o `FAIL`. No generes R10 v0.7.3 automáticamente. Si quedan defectos, enumera solo los supervivientes. Mantén `KEEP_BLOCKED`.
