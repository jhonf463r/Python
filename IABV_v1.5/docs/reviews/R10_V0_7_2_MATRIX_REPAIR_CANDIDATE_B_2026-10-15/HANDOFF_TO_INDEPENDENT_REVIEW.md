# Handoff para revisión delta independiente

**Decisión requerida:** revisar la candidatura B contra sus bytes y el baseline histórico. Mantener GOVERNANCE = KEEP_BLOCKED. No implementar, ejecutar, aceptar ni promover como resultado de esta revisión documental.

## Artefactos

- Candidatura completa: [candidate/](candidate/)
- Contrato reconstruido candidato: [R10_V0_7_2_RECONSTRUCTED_CONTRACT.md](candidate/R10_V0_7_2_RECONSTRUCTED_CONTRACT.md)
- Matriz candidata T123–T196: [R10_V0_7_2_TEST_MATRIX_T123_T196.csv](candidate/R10_V0_7_2_TEST_MATRIX_T123_T196.csv)
- Delta B: [R10_V0_7_2_MATRIX_REPAIR_DELTA_B.md](candidate/R10_V0_7_2_MATRIX_REPAIR_DELTA_B.md)
- Informe B: [R10_V0_7_2_MATRIX_REPAIR_REPORT_B.md](candidate/R10_V0_7_2_MATRIX_REPAIR_REPORT_B.md)
- Referencia v0.7 namespaced: [R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md](candidate/R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md)
- Auditoría Claude histórica: [R10_V0_7_1_AUDIT_REPORT_CLAUDE.md](candidate/R10_V0_7_1_AUDIT_REPORT_CLAUDE.md)
- Pruebas suplementarias no normativas: [R10_V0_7_2_SUPPLEMENTAL_TESTS_T197_PLUS_PROPOSED.md](candidate/R10_V0_7_2_SUPPLEMENTAL_TESTS_T197_PLUS_PROPOSED.md)
- Manifiesto Candidate B: [R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_B_SHA256.txt](candidate/R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_B_SHA256.txt)
- Baseline histórico byte-exacto: [baseline/](baseline/)
- Manifiesto de publicación: [GITHUB_PUBLICATION_SHA256.txt](GITHUB_PUBLICATION_SHA256.txt)

## Revisión requerida

1. Recalcular SHA-256 y tamaño de cada payload contra ambos manifiestos. Confirmar CSV candidato con BOM UTF-8, 74 IDs únicos/contiguos T123–T196, las 11 columnas originales, estados NOT_RUN y T185–T196 intactos. Compararlo con la matriz baseline sin alterar bytes.
2. Auditar T162 paso a paso: barrera/retracción, resolución independiente, QUARANTINE_RELEASED sin activación directa, nueva evaluación y contribución, validez de digests/generaciones, pérdida de CAS y ausencia de efectos parciales. Comprobar coherencia de los deltas netos 0/0 con los estados inicial/final.
3. Revisar el alcance de T141: el fixture positivo exige correlación atestada y padre exacto. Comprobar si los casos negativos (por ejemplo T135 y otros aplicables) distinguen cada identidad ausente, ajena, antigua o mal correlacionada sin depender solo de la etiqueta del caso positivo.
4. Reconciliar individualmente T123, T134, T135, T142, T145, T165, T167, T169 y T186 con el contrato. No etiquetar todas como defectuosas por la lista de hallazgos histórica: T142 sí se declara laguna contractual; otras tienen oráculos revisados que requieren validación del revisor.
5. Confirmar las brechas expresas T130/T131, T138, T142, T152 y T194. Distinguir una laguna de especificación de una carencia de implementación; no inventar reglas o códigos.
6. Resolver la referencia de §0 que menciona R10_V0_7_RECONSTRUCTED_CONTRACT_REFERENCE.md y SHA 5bab… frente al archivo namespaced que se incluyó. Confirmar qué originales no se recuperaron y verificar que T197+ está marcado PROPOSED y fuera del registro normativo.
7. Mantener separadas estas conclusiones: corrección documental del candidato, validez normativa, implementación real y experiencia runtime. El paquete no demuestra ejecución, CAS/atomicidad real ni capacidades de plataforma.

## Procedencia y límites

Candidate B se generó a partir del paquete original identificado por su hash en REVIEW_BRIEF.md. Los subdirectorios candidate/ y baseline/ son copias para comparación; no sustituir el baseline por el candidato. El informe Claude es evidencia histórica de v0.7.1, no un dictamen automáticamente aplicable a v0.7.2.

Esta publicación solo habilita la revisión de los artefactos publicados. No actualiza CURRENT-STATE.md, CONTEXT-INDEX.md ni otro documento canónico; no cambia M0B; no autoriza implementación; no incluye pruebas de producto, builds ni runtime. No fusionar esta Draft PR.
