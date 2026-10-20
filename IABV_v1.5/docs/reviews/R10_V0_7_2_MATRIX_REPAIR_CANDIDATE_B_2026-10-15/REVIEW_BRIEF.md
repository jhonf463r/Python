# R10 v0.7.2 — revisión de la candidatura B

**Gobierno: KEEP_BLOCKED · Estado: PROPOSED · Aceptación independiente: pendiente**

## Propósito y procedencia

Este directorio publica una candidatura documental para revisión independiente. No acepta el contrato, no demuestra implementación y no habilita ejecución o promoción.

- ZIP original de entrada: SHA-256 acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e.
- ZIP de Candidate B: SHA-256 3ddb8f38c8e549b23a291300cd9ce02128e07ea6af9dbdaaf4914200be2371c7.
- El contrato reconstruido candidato fue preservado byte por byte en la reparación reportada.
- candidate/ contiene la disposición íntegra del ZIP de Candidate B, incluido su manifiesto y SOURCE_ORIGINALS/; baseline/ conserva copias exactas del contrato, matriz y manifiesto originales.
- GITHUB_PUBLICATION_SHA256.txt calcula SHA-256 sobre los archivos publicados. Estos valores son distintos de los Git blob SHA.

## Resultado que el revisor debe comprobar contra los bytes

El informe de Candidate B declara que el dictamen FAIL del informe Claude incluido corresponde a la auditoría histórica v0.7.1 y no debe trasladarse automáticamente a los bytes v0.7.2. También afirma que T185–T196 conserva sus doce escenarios en la matriz v0.7.2, cuyo CSV es el registro normativo de IDs. Verificar ambas afirmaciones comparando candidate/ con baseline/ y leyendo los artefactos, no aceptarlas por este resumen.

La candidatura informa correcciones textuales en T162, T141, T134 y T165/T169, entre otras. En particular:

- **T162:** el nuevo oráculo conserva la evaluación antigua en cuarentena, exige resolución independiente, liberación sin activación directa, nueva evaluación/contribución/plan y adopción por CAS con generaciones y digests vigentes. La matriz expresa deltas netos 0/0; el revisor debe validar que el recorrido y el estado final son coherentes con los estados inicial/final.
- **T141:** ahora es un caso positivo estricto: identidad de despacho/sesión autenticada, IDs de turno atestados por plataforma y relación padre exacta. Esto no sustituye la revisión de casos negativos de correlación; contrastar, entre otros, T135 y las filas de rechazo pertinentes.
- **T134:** fija precondiciones y recorrido de un linaje nuevo separado, con deltas +1/+1; no resuelve SC-10 ni restaura evidencia del linaje tombstoned.
- **T165/T169:** el informe dice que usan AUTHORIZATION_GENERATION_MISMATCH de §9, no FENCING_VIOLATION.

## Oráculos específicos a revisar

La lista inicial de T123, T134, T135, T142, T145, T165, T167, T169 y T186 no debe tratarse como si cada defecto siguiera abierto:

- T123 especifica no elegibilidad y ausencia de efectos para DRY_RUN, sin inventar un código de rechazo.
- T134 especifica el camino de linaje distinto y sus condiciones iniciales.
- T135 expresa el rechazo de una respuesta del turno antiguo al intento nuevo como no correlacionada.
- T142 permanece como laguna: no hay operación normativa FREEZE ni código de error aplicable a ese caso.
- T145 especifica CRITERIA_MISMATCH y ausencia de adopción/contribución.
- T165/T169 usan el código de discrepancia de generación que el informe atribuye a §9.
- T167 especifica ACK_DUPLICATE para replay idéntico, que debe contrastarse con §2.2.
- T186 separa ruta no acreditada de modo no atestado.
- Todas las filas siguen siendo definiciones NOT_RUN; la precisión del oráculo no es evidencia de ejecución.

## Brechas y riesgos que siguen explícitos

El informe candidato identifica como brechas normativas T130/T131 (ciclo de vida/versionado de estrategias), T138 (expiración de nonce), T142 (congelación de resultado), T152 (función de puntuación determinista) y T194 (idempotencia/conflicto de adjuntos MANUAL). También marca como UNPROVEN la atestación de plataforma, validadores, secuenciador, CAS, transacciones/barreras, fencing, propagación de generación y rechazo efectivo del writer legacy.

El propio contrato contiene en §0 una referencia a R10_V0_7_RECONSTRUCTED_CONTRACT_REFERENCE.md y un SHA que no coincide con el nombre del archivo de referencia incluido. La candidatura reporta que el literal v0.6 y su matriz original no fueron recuperados. Revisar esta reconciliación de nombres, manifiestos y referencias; no fabricar alias ni presentar artefactos reconstruidos como originales.

Las pruebas suplementarias T197+ están separadas como PROPOSED, no normativas. No hay ejecución de pruebas de producto, builds ni runtime en esta publicación.

## Qué no significa esta publicación

Publicar la rama y abrir un borrador solo crea un punto común para revisión. No significa que los defectos estén aceptados/cerrados, que el contrato esté implementado, que haya aprendizaje o que M0B/M0A se haya habilitado.
