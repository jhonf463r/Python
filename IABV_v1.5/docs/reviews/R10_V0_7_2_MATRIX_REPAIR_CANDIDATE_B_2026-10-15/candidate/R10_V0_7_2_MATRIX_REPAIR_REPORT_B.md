# R10 v0.7.2 — Informe de reparación de matriz, candidatura B

## Resultado y alcance

Candidatura documental `PROPOSED`, pendiente de auditoría delta independiente. Gobierno permanece `KEEP_BLOCKED`. No se cambió el contrato reconstruido, no se creó v0.7.3 y no se ejecutaron tests del producto, builds ni runtime.

Entrada: `R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE (1).zip`, SHA-256 `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`. El ZIP original permanece intacto. Su manifiesto interno fue comprobado contra los bytes de los seis archivos enumerados; los seis tamaños y SHA-256 coincidieron. No había un artefacto separado del candidato reparado de Gemini; las reparaciones anteriores quedan `OWNER_REPORTED`/`NOT_RECOVERED`.

El contrato `R10_V0_7_2_RECONSTRUCTED_CONTRACT.md` se copió byte por byte. La matriz candidata conserva el nombre normativo exacto `R10_V0_7_2_TEST_MATRIX_T123_T196.csv`, BOM UTF-8, 11 columnas y 74 IDs únicos y contiguos T123–T196; no hay reasignaciones. Todos los registros de estado continúan `NOT_RUN`.

## Contraste con el informe Claude incluido (auditoría estática de v0.7.1)

El informe se conserva como entrada histórica, no se acepta como autoridad sobre el paquete v0.7.2 real.

- **D1 es materialmente incorrecto para este paquete v0.7.2.** El contrato en §0 declara al CSV como único registro normativo de IDs y exige prefijo `REF_V07_` para pruebas de la referencia histórica. La referencia incluida tiene esos nombres de espacio; el cuerpo del contrato no contiene la supuesta Parte III con escenarios competidores. El CSV sí contiene T185–T196 como las doce asignaciones anunciadas en el README. La afirmación de reasignación basada en otro candidato/reconstrucción no se aplica a estos bytes.
- **D2 está en gran parte reparado en el texto contractual v0.7.2**, pero no todos los oráculos de la matriz quedaban alineados. §§6.1/6.3 prohíben elegir por mayor `task_seq`; §3.2/§11 separan MANUAL de AUTO; §8.3 exige restauración con nueva evaluación/contribución; §12 niega activación directa en `QUARANTINE_RELEASED`. T162 ignoraba específicamente esas protecciones y queda corregido.
- **D3 está cerrado como regla textual en §4.1**, no como propiedad de runtime. El T141 original no fijaba el padre de respuesta autenticado, sesión ni atestación del vínculo; se corrigió como fixture positivo estricto. T135/T136/T138/T176 se revisaron; la expiración de nonce queda sin regla contractual específica.
- **D4 y D5 están expresados en el contrato v0.7.2** (§1.3 y §§8.2–8.3). No se presenta el texto como prueba de implementación atómica real.
- **D6 está abordado en el contrato** (§§1.2, 3, 8.1–8.3, 9, 10), pero la matriz conservaba vocabulario/códigos ajenos o no definidos; se corrigieron varias filas y las restantes están identificadas abajo.

## Reparaciones completadas en la matriz

- `T162`: ya no activa EVALUATION_A directamente. Detecta conflicto y barrera; registra resolución independiente; vuelve a derivar elegibilidad con una evaluación nueva y mismo `result_lineage_id`; crea contribución y plan nuevos; comprueba digests y generaciones vigentes; adopta solo por CAS. El fixture especifica retirada y re-adopción, de modo que los deltas netos `0/0` significan contadores iniciales y finales iguales, no ausencia de transición.
- `T141`: positivo con `dispatch_turn_id` y `destination_session_id` autenticados, `turn_id`/`in_reply_to_turn_id` atestados por plataforma, igualdad exacta del padre, nonce/receipt/captor y digest/canonicalización.
- `T134`: fija el estado inicial y el camino elegible, por lo que el resultado de un nuevo linaje permitido da `+1/+1`, sin resolver ni restaurar el linaje tombstoned.
- `T165/T169`: usan `AUTHORIZATION_GENERATION_MISMATCH` de §9 en vez de `FENCING_VIOLATION` para la discrepancia de generación.
- Corregidos nombres de modo/plan/criterios, filas con fragmentos Markdown residuales `T144/T154/T164`, y oráculos faltantes o vagos en `T123–T128`, `T137`, `T139`, `T143–T149`, `T158–T160`, `T166`, `T170`, `T173–T174`, `T177–T180`, `T182`, `T184–T185`, `T187–T188`, `T191`, `T195–T196`.
- Los rechazos sin código contractual quedan expresados como estado/ausencia de efectos, no como nuevos códigos.

La tabla completa de cambios byte-parsed, con campo, valor anterior, valor propuesto, cláusula y motivo, está en `R10_V0_7_2_MATRIX_REPAIR_DELTA_B.md`.

## Defectos y lagunas supervivientes

1. `T130/T131`: el contrato reconstruido no define ciclo de vida `STRATEGY.ACTIVE`, unicidad de estrategias activas, `version_seq` ni `parent_id` de estrategia. La matriz no puede fijar esos resultados sin una regla nueva. Se dejó una advertencia en sus oráculos; requieren decisión normativa.
2. `T138`: no hay TTL/expiración contractual del nonce. La regla de reloj/deadline no autoriza inferir vencimiento de nonce.
3. `T142`: el contrato no define operación `FREEZE` para un resultado ni código `INVALID_STATE` en esa rama. La fila declara la laguna y no asigna código/resultado inventado.
4. `T152`: el contrato no define una función de puntuación determinista; no hay oráculo normativo de igualdad de score.
5. `T194`: el contrato no fija idempotencia ni conflicto por digest para adjuntos manuales; la separación MANUAL/AUTO sí existe.
6. Otras capacidades nombradas por el contrato siguen técnicamente `UNPROVEN`: attestation de plataforma, verificador de modo/ruta, ejecución real del validador, secuenciador/CAS/transacciones/barreras, fencing, propagación de generación y aislamiento efectivo del writer legacy.
7. La matriz candidata no es todavía una batería completamente ejecutable: las filas de laguna no se pueden adjudicar hasta que se resuelvan normativamente. Las pruebas suplementarias T197+ están separadas y son `PROPOSED`, no normativas.

## Identidad de archivos y manifiestos

Se preservaron contrato, referencia, informe Claude, README, prompt de auditoría y manifiesto de fuente. El SHA de la referencia incluida es `107746aeb02cbf52d736f438cb466b013f66696545b9934b111458ce990ede9e`, distinto del hash histórico `5babd981…` citado por el contrato para `R10_V0_7_RECONSTRUCTED_CONTRACT_REFERENCE.md`. No se creó alias que fingiera equivalencia: el nombre/hash que el contrato cita no está dentro del paquete. El README identifica la referencia namespaced incluida; la discrepancia queda abierta.

El manifiesto de fuente `R10_V0_7_2_SHA256.txt` se conserva como registro histórico de la entrada, no como manifiesto de los archivos modificados. `R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_B_SHA256.txt` cubre los bytes de cada archivo de la candidatura excepto a sí mismo y el ZIP externo, por la imposibilidad autorreferencial; la huella ZIP se informa aparte.

## Verificación mecánica

Se verificó el paquete de entrada contra su manifiesto; se preservó el contrato byte por byte; el CSV parsea con 11 columnas, BOM UTF-8 y exactamente T123–T196 sin duplicados ni huecos. La verificación del ZIP candidato se registra separadamente después de crear y reextraer el archivo. No son pruebas de comportamiento.

## Decisión

La candidatura B corrige T162 y defectos concretos de oráculos sin alterar el contrato ni los IDs. Los defectos supervivientes requieren una decisión normativa o evidencia fuera del alcance. No es `PASS` del contrato: requiere auditoría independiente antes de cualquier aceptación. El próximo paso es revisar delta de esta candidatura, en especial T162 y las lagunas T130/T131/T138/T142/T152/T194. No ejecutar ni promover.

## Verificación final del paquete reextraído

La candidatura B fue comprimida y extraída en un directorio independiente. Los 12 archivos de payload enumerados en el manifiesto de candidatura coincidieron en SHA-256 y tamaño; el manifiesto histórico de fuente también coincidió para sus seis artefactos. El archivo extraído contiene 13 entradas contando el propio manifiesto de candidatura. El contrato extraído conserva el hash fuente `3be41ffc488e5f9e0577baf523d15ab62a8d1da9293ce1ed2d3ce73a90b1064c`. La matriz del root tiene nombre exacto, BOM `EF-BB-BF`, 74 filas, 11 columnas, IDs T123–T196 únicos/contiguos, 12 escenarios T185–T196 conservados, todos `NOT_RUN` y cero encabezados Markdown residuales.

Esta comprobación valida custodia, formato e identidad de archivos; no ejecuta los oráculos ni prueba el comportamiento del sistema.
