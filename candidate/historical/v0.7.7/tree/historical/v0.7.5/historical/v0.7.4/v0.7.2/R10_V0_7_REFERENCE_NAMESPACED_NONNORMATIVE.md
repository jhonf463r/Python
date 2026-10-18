<!-- ARCHIVAL REFERENCE ONLY. The test labels T123–T196 in this copy are namespaced as REF_V07_Tnnn to avoid colliding with the normative v0.7.2 test registry. Content is otherwise retained from the prior reconstructed reference, but this renaming means the file is not byte-identical to its source. -->

## R10_V0_7_RECONSTRUCTED_CONTRACT

**Clasificación del documento:** `RECONSTRUCTED_FROM_REVIEW` + `PROPOSED`

**Postura de gobierno:** `KEEP_BLOCKED`

**Estado:** `RECONSTRUCCIÓN PROPUESTA — PENDIENTE DE REVISIÓN ADVERSARIAL`

---

### SOURCE_GAPS_AND_RECONSTRUCTION_REGISTER

| ID   | Tipo                        | Detalle                                                                                                                                                                                         |
| ---- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SG-1 | `NOT_RECOVERED`             | Texto literal R10 v0.6 — no localizado en el repositorio ni en la memoria de sesión.                                                                                                            |
| SG-2 | `RECONSTRUCTED_FROM_REVIEW` | SC-1–SC-10 y sus secuencias — derivados de las descripciones del informe adversarial v0.6.                                                                                                      |
| SG-3 | `RECONSTRUCTED_FROM_REVIEW` | REF_V07_T123–REF_V07_T184 — escenarios inferidos de las críticas del informe; formulación no reproducida literalmente.                                                                                          |
| SG-4 | `PROPOSED`                  | REF_V07_T185–REF_V07_T196 y toda la especificación contractual — nuevas cláusulas para cerrar los defectos identificados.                                                                                       |
| SG-5 | `NOT_RECOVERED`             | Texto canónico de las reglas de elegibilidad base previas a v0.6.                                                                                                                               |
| SG-6 | `RECOVERED`                 | Vocabulario de niveles L0–L5b, concepto de `UAAL-ROOT-001`, estados IABV, concepto de `BASE_ELIGIBLE` y cadena de aprendizaje causal — inferidos de los documentos del repositorio disponibles. |

---

## PARTE I — R10_V0_7_RECONSTRUCTED_CONTRACT

### §1 MODELO DE IDENTIDADES Y LINAJES

#### §1.1 Entidades principales

```
EXECUTION           Instancia de ejecución real, no simulada, de una estrategia
STRATEGY            Conjunto versioned de parámetros de decisión
LINEAGE             Árbol de derivación entre versiones de estrategia
EVALUATION          Registro de valoración de un resultado de ejecución
CONTRIBUTION        Efecto durable de una evaluación sobre el modelo vigente
PLAN                Secuencia de cambios propuestos derivada de evidencia
RESULT              Captura autenticada del output de una ejecución
TASK                Objetivo operativo que puede instanciar una o más ejecuciones
```

#### §1.2 Identidad

Cada entidad tiene un `entity_id` globalmente único, generado por el coordinador en el momento de creación. Ningún productor externo auto-genera su propio `entity_id`. Cada entidad lleva:

- `entity_id: UUID`
- `entity_type: enum`
- `lineage_id: UUID | null` (para STRATEGY y EVALUATION; null si es raíz)
- `parent_id: UUID | null`
- `created_at: ISO-8601 UTC monotónico`
- `created_by: actor_id`
- `version_seq: uint` (incremento atómico por linaje)

#### §1.3 Linaje de estrategia

Una STRATEGY tiene exactamente un linaje. Un nuevo linaje se crea explícitamente; no se crea por derivación implícita. La sustitución de una estrategia dentro de un linaje incrementa `version_seq`; crea una nueva estrategia hija con `parent_id` = estrategia anterior.

**Invariante:** no pueden coexistir dos estrategias `ACTIVE` con el mismo `lineage_id`.

#### §1.4 Versionado de criterios

Los criterios de evaluación son objetos versionados con su propio `criteria_id` y `criteria_digest` (SHA-256 del contenido canónico). El coordinador mantiene el registro canónico. Ningún evaluador genera ni altera criterios.

---

### §2 REGISTRO DURABLE Y SECUENCIACIÓN DE EVENTOS

#### §2.1 Log de eventos

Todo evento que modifica el estado de una entidad se registra de forma durable antes de devolver éxito al productor. El registro incluye:

- `event_id: UUID`
- `seq: uint64` (secuenciador durable monótonamente creciente)
- `entity_id`
- `event_type`
- `actor_id`
- `timestamp: monotonic UTC`
- `payload_digest: SHA-256`
- `previous_event_id: UUID | null`

#### §2.2 Precondición de escritura

Ninguna escritura se acepta a menos que el `seq` propuesto sea exactamente `max(seq)+1` para la entidad afectada en el momento de la transacción. Escrituras concurrentes con el mismo `seq` se resuelven por CAS: gana la que llegue primero; la segunda recibe error `SEQ_CONFLICT` y debe releer y reenviar.

#### §2.3 Durabilidad

El coordinador confirma durabilidad antes de entregar `ACK`. Un `ACK` no entregado no implica que el evento no se persistió. El productor repite con idempotencia mediante `event_id` hasta recibir `ACK` o detectar un `CONFLICT`.

#### §2.4 Reloj de confianza

El coordinador usa un reloj monotónico de confianza. Si ese reloj no está disponible, ninguna operación dependiente de tiempo (expiración, fencing de generaciones) se ejecuta: resultado `CLOCK_UNAVAILABLE`, fail-closed.

---

### §3 MÁQUINA DE ESTADOS POR ENTIDAD

#### §3.1 EXECUTION

```
DISPATCHED → RUNNING → COMPLETED | FAILED | ABORTED | TIMED_OUT
```

- `DISPATCHED`: despacho registrado, modo y ruta acreditados, nonce asignado.
- `RUNNING`: confirmación de inicio recibida.
- `COMPLETED`: resultado recibido y capturado con correlación verificable.
- `FAILED`: error de ejecución registrado.
- `ABORTED`: cancelación explícita antes de completar.
- `TIMED_OUT`: límite de tiempo superado sin resultado.

`DRY_RUN`, `SIMULATED`, `SANDBOX_ISOLATED` son atributos de modo que coexisten con los estados anteriores. Una ejecución `COMPLETED` con modo `DRY_RUN` nunca transiciona a `BASE_ELIGIBLE`.

Transiciones no permitidas: ningún estado terminal (`COMPLETED`, `FAILED`, `ABORTED`, `TIMED_OUT`) puede revertir a `RUNNING` o `DISPATCHED`. Una ejecución no puede auto-declarar su modo.

#### §3.2 RESULT

```
CAPTURED → CORRELATED | UNCORRELATED → FROZEN | REJECTED
```

- `CAPTURED`: captura recibida del captor.
- `CORRELATED`: relación verificable con el despacho establecida por el coordinador.
- `UNCORRELATED`: relación no verificable; el resultado no puede usarse para aprendizaje automático.
- `FROZEN`: result sellado con digest de criterios vigentes; solo desde `CORRELATED`.
- `REJECTED`: captura rechazada.

#### §3.3 EVALUATION

```
PENDING → VALIDATING → VALID | INVALID → ACTIVE | SUPERSEDED | VOIDED
```

- `ACTIVE`: evaluación válida que contribuye al modelo vigente.
- `SUPERSEDED`: reemplazada por una evaluación posterior del mismo linaje.
- `VOIDED`: invalidada por revocación o condición de tombstone.

Solo una evaluación puede estar `ACTIVE` por `(lineage_id, result_type)` en cualquier momento.

#### §3.4 CONTRIBUTION

```
PENDING → COMMITTED → ACTIVE | RETRACTED
```

Solo una contribución puede estar `ACTIVE` para `(dest, lineage_id, contribution_type)`.

#### §3.5 PLAN

```
DRAFT → VALIDATED → APPROVED → EXECUTING → COMPLETED | VOIDED
```

`VOIDED` es terminal. Un plan `VOIDED` no puede reactivarse ni promover sus contribuciones preparadas.

---

### §4 PERFILES, MODOS Y TRANSICIONES PERMITIDAS

#### §4.1 Modos de ejecución

| Modo               | Elegible para aprendizaje automático       |
| ------------------ | ------------------------------------------ |
| `REAL`             | Sí, si se cumplen todas las precondiciones |
| `DRY_RUN`          | No                                         |
| `SIMULATED`        | No                                         |
| `SANDBOX_ISOLATED` | No                                         |
| `UNKNOWN`          | No                                         |

El modo se acredita en el momento del despacho por el coordinador, no por el productor de la ejecución.

#### §4.2 Rutas acreditadas

Solo las rutas de ejecución explícitamente registradas en el registro canónico de rutas (`route_registry`) son elegibles. Una ejecución por una ruta no registrada es `UNACCREDITED_ROUTE` y no es elegible.

#### §4.3 Perfiles

Un perfil es la combinación `(strategy_id, mode, route_id, criteria_id)`. El coordinador verifica que el perfil completo esté registrado antes de aceptar una evaluación.

---

### §5 CAPTURA DE SALIDA Y AUTENTICIDAD DE CORRELACIÓN

#### §5.1 Correlación

La correlación entre un resultado capturado y un despacho es verificable cuando el coordinador puede establecer que:

- el `turn_id` o identificador de turno reportado por el captor fue emitido por el coordinador para ese despacho;
- el nonce del despacho coincide con el nonce reportado en la captura;
- el `timestamp` de la captura es posterior al despacho y anterior al tiempo de expiración del nonce.

Si la plataforma no provee evidencia verificable del `turn_id`, la captura automática es `UNCORRELATED`. Una captura `UNCORRELATED` puede usarse como evidencia manual, etiquetada explícitamente como tal, pero no produce aprendizaje automático (`SC-2` bloqueado).

#### §5.2 Captura completa

Una captura es completa cuando incluye: salida completa (no truncada), metadatos del turno, digest de la captura, identificador del captor y timestamp.

Una captura parcial produce `RESULT.REJECTED`.

#### §5.3 Autenticidad del captor

El captor debe ser un componente autorizado en el registro de captores. Un resultado auto-reportado por el propio productor sin captor independiente es `UNCORRELATED`.

---

### §6 CONGELACIÓN Y VERIFICACIÓN DE CRITERIOS

#### §6.1 Congelación previa al despacho

El paquete de criterios se congela antes de cada despacho pertinente. La congelación produce un `criteria_snapshot_id` y un `criteria_digest`. El coordinador registra el `criteria_snapshot_id` asociado al despacho en el log de eventos antes de emitir el despacho.

#### §6.2 Verificación de uso

El validador registra en cada evaluación los digest de criterios realmente utilizados. Si el digest utilizado no coincide con el `criteria_digest` del despacho, la evaluación es `INVALID` por `CRITERIA_MISMATCH` (`SC-5` bloqueado).

#### §6.3 Retroactividad prohibida

Una revisión de criterios más permisiva no puede convertir retroactivamente en válida una evaluación que usó criterios distintos a los congelados. La modificación de criterios solo afecta a despachos futuros (`SC-5` bloqueado).

---

### §7 VALIDACIÓN Y EVALUACIÓN DETERMINISTAS

#### §7.1 Validación

La validación aplica exactamente los criterios del `criteria_snapshot_id` vinculado al despacho, con los digest registrados. El resultado es binario: `PASS` / `FAIL`. No hay resultados parciales ni “probablemente válido”.

#### §7.2 Evaluación

La evaluación toma un resultado `FROZEN` válido, aplica la política de evaluación congelada del perfil y produce un score o clasificación. El algoritmo de evaluación es determinista: mismas entradas → mismo resultado. Si el algoritmo no es determinista, no puede usarse para producir aprendizaje automático.

#### §7.3 Política de selección congelada y versionada

La política de selección (qué evaluación es la vigente entre candidatas) es versioned y congelada al momento de la proyección. El despacho no altera por sí solo el resultado vigente.

#### §7.4 Invalida y reemplaza

Una nueva evaluación válida del mismo linaje puede reemplazar a la anterior. El reemplazo es atómico: en ningún momento coexisten dos evaluaciones `ACTIVE` del mismo linaje y tipo. El reemplazo marca la anterior como `SUPERSEDED` y activa la nueva en la misma transacción (`SC-3` y `SC-4` bloqueados).

---

### §8 ELEGIBILIDAD BASE UNIVERSAL

#### §8.1 Predicado BASE_ELIGIBLE

`BASE_ELIGIBLE` es derivado por el coordinador. Es verdadero cuando se cumplen simultáneamente todas las siguientes condiciones:

1. La ejecución tiene estado `COMPLETED`.
2. El modo es `REAL` (no `DRY_RUN`, `SIMULATED`, `SANDBOX_ISOLATED`, `UNKNOWN`).
3. La ruta de ejecución está acreditada en `route_registry`.
4. El resultado tiene estado `CORRELATED` (correlación verificable).
5. La captura es completa.
6. Los criterios están congelados y el `criteria_digest` utilizado coincide.
7. La evaluación tiene estado `VALID`.
8. No existe conflicto activo, tombstone aplicable ni revocación vigente para esta ejecución o estrategia.

Si cualquier condición falla, `BASE_ELIGIBLE = false`. Ningún productor puede declarar `BASE_ELIGIBLE = true` directamente: es un predicado derivado, nunca una bandera escribible.

#### §8.2 Fallo operacional no atribuible

Un fallo de ejecución cuya causa no es atribuible a la estrategia (fallo de infraestructura, timeout de red, error del captor) no produce evidencia negativa automática contra la estrategia. El coordinador clasifica la causa y descarta la ejecución de la evaluación de la estrategia, preservando el registro del fallo.

---

### §9 ADOPCIÓN DEL RESULTADO VIGENTE

#### §9.1 Resultado vigente de tarea (`TS`)

El resultado vigente de una tarea (`TS`) es el resultado de la evaluación activa del linaje principal asociado a esa tarea, proyectado por la política de selección vigente. `TS` no cambia cuando un despacho se emite; cambia solo cuando una evaluación activa es reemplazada, retractada o revocada conforme a una regla atómica o recuperable.

#### §9.2 Proyección determinista

La proyección de `TS` desde el conjunto de evaluaciones activas sigue la política versionada y congelada. Si dos evaluaciones candidatas son incompatibles o se procesaron concurrentemente, el coordinador resuelve por secuencia (`seq`) de su registro durable, no por el consumidor que llegó primero (`SC-7` bloqueado).

#### §9.3 Puntero vigente (`PA`)

El puntero activo (`PA`) apunta a la evaluación activa del linaje. Cuando una evaluación es reemplazada, `PA` se actualiza atómicamente a la nueva evaluación en la misma transacción que marca la anterior como `SUPERSEDED`. En ningún momento `PA` apunta a una evaluación `SUPERSEDED` (`SC-4` bloqueado).

---

### §10 CONTRIBUCIONES, PLANES, RETRACTACIONES Y TOMBSTONES

#### §10.1 Contribuciones

Una CONTRIBUTION es el efecto de una evaluación activa sobre el modelo vigente. Al activar una nueva evaluación del mismo linaje, el coordinador:

1. Marca la contribución anterior del mismo `(dest, lineage_id, contribution_type)` como `RETRACTED` (durablemente).
2. Crea la nueva contribución con estado `COMMITTED`.
3. La activa atómicamente.

Solo una contribución puede estar `ACTIVE` para `(dest, lineage_id, contribution_type)` en cualquier momento (`SC-3` bloqueado).

#### §10.2 Durabilidad de la retractación

La retractación es durable: sobrevive a caídas y reinicios. El coordinador, al recuperarse, verifica que no existan dos contribuciones `ACTIVE` para el mismo `(dest, lineage_id, contribution_type)`. Si las detecta, aplica la regla de resolución por `seq` y retracta la de menor `seq`.

#### §10.3 Planes

Un PLAN lleva sus propias contribuciones preparadas (`draft_contributions`) con estado `DRAFT`. Las contribuciones `DRAFT` no son visibles al modelo vigente. Solo cuando el plan completa exitosamente (`COMPLETED`) el coordinador activa las contribuciones, siguiendo §10.1. Si el plan es `VOIDED`, todas sus `draft_contributions` permanecen invisibles y no se activan bajo ninguna condición.

#### §10.4 Tombstones

Un tombstone es un registro durable que excluye a una entidad (estrategia, linaje, ejecución) del aprendizaje automático. Los tombstones son permanentes y no revocables por el mismo actor que los produjo. Un tombstone aplicable hace `BASE_ELIGIBLE = false` para todas las ejecuciones afectadas. El tombstone no impide registrar evidencia nueva a través de una evaluación nueva sobre la misma tarea con un linaje diferente (`SC-10` bloqueado).

---

### §11 RECIBOS E IDEMPOTENCIA

#### §11.1 Recibo de despacho

El coordinador emite un `dispatch_receipt` con `(dispatch_id, nonce, expiry, criteria_snapshot_id)`. El receipt se firma con la clave del coordinador. Un despacho sin receipt no puede producir evaluación automática.

#### §11.2 Idempotencia de escritura

Cada operación de escritura lleva un `idempotency_key = (actor_id, operation_type, entity_id, event_id)`. Si el coordinador recibe dos escrituras con el mismo `idempotency_key`, acepta la primera y devuelve `ACK_DUPLICATE` para la segunda, sin efecto adicional.

#### §11.3 Abandono

Una evaluación no puede ser “abandonada” basándose en un plazo que no ha sido registrado durablemente. El plazo de abandono debe estar en el registro canónico del despacho y ser verificable con el reloj de confianza (`SC-6` bloqueado).

---

### §12 CONFLICTOS Y CUARENTENA

#### §12.1 Definición de conflicto

Un conflicto ocurre cuando dos evaluaciones del mismo linaje, ambas `VALID`, intentan activarse simultáneamente (detección por CAS en la transacción de activación). El coordinador:

1. Acepta la de mayor `seq`.
2. Coloca la otra en `QUARANTINE` con estado `CONFLICT_PENDING`.
3. Registra el conflicto en el log de eventos.

#### §12.2 Resolución de cuarentena

Una evaluación en `QUARANTINE` permanece inaccesible al modelo vigente hasta que una autoridad explícita la resuelva (manual o por regla de resolución automática documentada). La resolución puede ser `ACTIVATE` (si la evaluación en cuarentena es la correcta) o `DISCARD`. La retractación/activación sigue §10.1.

#### §12.3 Conflicto no bloquea evaluaciones futuras

Un conflicto en un linaje no bloquea la evaluación de otros linajes ni la creación de nuevas ejecuciones. Solo bloquea la activación de contribuciones del linaje en conflicto hasta su resolución.

---

### §13 AUTORIZACIÓN, REVOCACIÓN, CAS Y FENCING

#### §13.1 Autorización por generación

Cada acción sobre una entidad requiere que el actor posea una `authorization_token` con `generation_id` igual a la generación vigente de la entidad en el momento de la transacción. El `generation_id` se incrementa en cada revocación o rotación. Una escritura con `generation_id` obsoleto es rechazada con `FENCING_VIOLATION`.

#### §13.2 Revocación

La revocación es atómica y fail-closed. Al revocar:

1. Se incrementa el `generation_id` de la entidad.
2. Todas las autorizaciones con el `generation_id` anterior se invalidan.
3. Si hay un plan `EXECUTING` o `APPROVED` en el linaje revocado, transiciona a `VOIDED` y todas sus contribuciones `DRAFT` permanecen invisibles.

Un commit de efectos con `generation_id` obsoleto que llega después de la revocación es rechazado por fencing (`SC-8` bloqueado).

#### §13.3 CAS en activación

La activación de una evaluación usa CAS sobre `(lineage_id, result_type, current_active_id)`. Si el `current_active_id` ha cambiado entre la lectura y el commit (revocación o activación concurrente), la transacción falla con `CAS_CONFLICT` y el actor debe releer.

---

### §14 AISLAMIENTO DE LOS CARRILES AUTOMÁTICO Y MANUAL

#### §14.1 Separación semántica

El carril automático produce evaluaciones con `lane = AUTO`. El carril manual produce evaluaciones con `lane = MANUAL`. Son registros separados, con campos de resultado separados, y sus efectos no se mezclan.

#### §14.2 El carril manual no ocupa la plaza terminal automática

Una evaluación `lane=MANUAL` no puede activarse como resultado vigente automático (`TS`), no se convierte en ganador de tarea, y no altera `TS` ni `PA` automáticos. El carril manual tiene su propia proyección (`TS_MANUAL`) separada.

#### §14.3 No conversión automática

Una evaluación `lane=MANUAL` no puede ser promovida a `lane=AUTO` sin una operación explícita de conversión, autorizada, que genere un nuevo `event_id` y registre el cambio de carril durablemente (`SC-9` bloqueado).

#### §14.4 Análisis manual separado

Un resultado manual puede alimentar una ruta de análisis humano-in-the-loop separada. Esta ruta no comparte los predicados de elegibilidad del carril automático y no genera contribuciones automáticas.

---

### §15 TRATAMIENTO DEL LEGADO

#### §15.1 Definición de registro heredado

Un registro heredado es cualquier entidad creada antes de la entrada en vigor de este contrato o importada desde un sistema sin los campos `entity_id`, `criteria_digest`, `dispatch_receipt` o `generation_id` requeridos.

#### §15.2 Política de legado

Los registros heredados reciben `legacy=true`. Son inaccesibles para el predicado `BASE_ELIGIBLE` automático. Pueden consultarse y exportarse para análisis manual. No pueden contribuir al modelo vigente automático sin una operación explícita de migración que complete todos los campos requeridos y sea auditada.

#### §15.3 Aislamiento

Las rutas heredadas no comparten la cola de evaluación automática ni el secuenciador durable con las rutas nuevas.

---

### §16 NIVELES L0–L5b

Los niveles son predicados derivados, no marcas históricas. Su evaluación ocurre en el momento de la consulta, sobre el estado vigente de registros y contribuciones.

| Nivel | Predicado                                                                                                          | No se presume por       |
| ----- | ------------------------------------------------------------------------------------------------------------------ | ----------------------- |
| `L0`  | Ejecución registrada y modo `REAL`                                                                                 | Persistir un resultado  |
| `L1`  | `L0` + correlación verificable                                                                                     | Correlación declarada   |
| `L2`  | `L1` + criterios congelados y digest coincidentes                                                                  | Existir criterios       |
| `L3`  | `L2` + evaluación `VALID` y `ACTIVE`                                                                               | Completar un plan       |
| `L4`  | `L3` + contribución `ACTIVE` que influye en decisiones actuales                                                    | Persistir un resultado  |
| `L5a` | `L4` + evidencia verificable de influencia en decisiones pasadas                                                   | Ejecutar una evaluación |
| `L5b` | `L5a` + diseño de medición con comparador predefinido y criterios preestablecidos que demuestra mejora verificable | Diseñar un experimento  |

`L4` es un predicado derivado del estado vigente de las contribuciones: si la contribución es retractada, `L4` deja de ser verdadero aunque el registro histórico persista. `L5b` requiere un comparador explícito definido antes de la ejecución, no a posteriori.

---

### §17 RECUPERACIÓN ANTE CAÍDAS Y CONCURRENCIA

#### §17.1 Protocolo de recuperación

Al reiniciar tras una caída:

1. Leer el log de eventos desde el último checkpoint durable.
2. Identificar todas las entidades con estado no-terminal cuyo `event_id` de última escritura no tiene `ACK` registrado.
3. Para cada una: intentar confirmar el `ACK` (idempotencia); si el evento no se persistió, descartarlo y revertir el estado al último `ACK` confirmado.
4. Verificar que no coexistan dos contribuciones `ACTIVE` para el mismo `(dest, lineage_id, contribution_type)`. Si las hay, resolver por `seq`.
5. Verificar que todos los planes `EXECUTING` tengan su `generation_id` vigente. Los que no lo tengan transicionan a `VOIDED`.

#### §17.2 Concurrencia y fencing

Los escritores en concurrencia usan el `generation_id` como fence. Un escritor que obtiene su token de autorización, luego sufre una revocación concurrente, y luego intenta el commit, recibe `FENCING_VIOLATION` y su commit se descarta sin efecto (`SC-8` bloqueado).

#### §17.3 Operaciones no retomables

Una operación `DISPATCHED` que no transicionó a `RUNNING` antes de la caída no se auto-reanuda. El coordinador la marca como `ABORTED` con causa `CRASH_RECOVERY`. El actor puede emitir un nuevo despacho con un nuevo nonce.

---

### §18 MATRIZ DE ESCRITORES Y PERMISOS

| Actor              | Puede escribir                                                                                              | No puede escribir                                          |
| ------------------ | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `Coordinator`      | Todo, con `seq` y `generation_id` actuales                                                                  | Nada sin autorización interna                              |
| `Executor`         | `EXECUTION.state` (DISPATCHED→RUNNING→COMPLETED\|FAILED\|ABORTED\|TIMED_OUT), `RESULT.CAPTURED`             | `entity_id`, `BASE_ELIGIBLE`, modo de ejecución, criterios |
| `Captor`           | `RESULT.CAPTURED`, `RESULT.CORRELATED\|UNCORRELATED`, `capture_digest`                                      | `turn_id` propio, correlación propia, `criteria_digest`    |
| `Validator`        | `EVALUATION.VALIDATING→VALID\|INVALID`, `criteria_digest_used`                                              | Criterios, `lineage_id`, modo                              |
| `Evaluator`        | `EVALUATION.VALID→ACTIVE\|SUPERSEDED`, scores                                                               | `PA`, `TS` directamente                                    |
| `Plan owner`       | `PLAN.DRAFT→VALIDATED→APPROVED→EXECUTING`, `PLAN.VOIDED`                                                    | Contribuciones fuera del plan, `BASE_ELIGIBLE`             |
| `Human (manual)`   | `lane=MANUAL` evaluaciones, resolución de cuarentena, tombstones, conversión manual→auto (con autorización) | `lane=AUTO` directamente, `TS` automático                  |
| `Ningún productor` | `BASE_ELIGIBLE` (es derivado)                                                                               | —                                                          |

---

### §19 DEPENDENCIAS TÉCNICAS NO DEMOSTRADAS

Todas las siguientes permanecen `UNPROVEN` hasta que exista evidencia independiente:

| Dependencia                                                    | Por qué es necesaria           | Comportamiento de rechazo si ausente                                  |
| -------------------------------------------------------------- | ------------------------------ | --------------------------------------------------------------------- |
| Identidad estable de turnos y vínculo autenticado de respuesta | Correlación verificable (§5.1) | Captura → `UNCORRELATED`                                              |
| Atestación de modo y ruta de ejecución                         | §4                             | Ejecución → `UNACCREDITED_ROUTE` o modo `UNKNOWN`                     |
| Reloj monotónico de confianza                                  | §2.4, §11.3, §17.1             | Operaciones dependientes de tiempo → `CLOCK_UNAVAILABLE`, fail-closed |
| CAS y transacciones atómicas                                   | §2.2, §10.1, §13.3             | Conflictos de concurrencia no resueltos                               |
| Secuenciador durable                                           | §2.1                           | `seq` no garantizado; resolución de conflictos indefinida             |
| Fencing de escritores                                          | §13.2                          | Commits post-revocación posibles                                      |
| Unicidad de eventos, evaluaciones y contribuciones             | §10.1, §12.1                   | Duplicados activos posibles                                           |
| Commit y retractación recuperables                             | §10.2, §17.1                   | Estado inconsistente tras caída                                       |
| Generación versionada de autorización                          | §13.1                          | Fencing inoperante                                                    |
| Aislamiento real de rutas heredadas                            | §15.3                          | Contaminación del carril automático                                   |
| Replay contrafactual y medición de mejora                      | §16 (L5b)                      | L5b no evaluable                                                      |
| Autorización por evento con firma del coordinador              | §11.1                          | Receipts no verificables                                              |

---

### PARTE II — MATRICES DE EVENTOS, ESCRITORES, ESTADOS Y PERMISOS

*(Las matrices de escritores y permisos están en §18; la máquina de estados en §3; los niveles en §16. Las matrices de eventos se definen a continuación.)*

#### MATRIZ DE TRANSICIONES DE EVENTOS

| Entidad      | Evento      | Precondición                                       | Efecto                                        | Actor autorizado    |
| ------------ | ----------- | -------------------------------------------------- | --------------------------------------------- | ------------------- |
| EXECUTION    | `DISPATCH`  | Modo y ruta registrados, nonce generado            | Estado→DISPATCHED, dispatch_receipt emitido   | Coordinator         |
| EXECUTION    | `START`     | Estado=DISPATCHED, `generation_id` vigente         | Estado→RUNNING                                | Executor            |
| EXECUTION    | `COMPLETE`  | Estado=RUNNING, captura completa disponible        | Estado→COMPLETED                              | Executor + Captor   |
| EXECUTION    | `FAIL`      | Estado=RUNNING                                     | Estado→FAILED                                 | Executor            |
| EXECUTION    | `ABORT`     | Estado=DISPATCHED o RUNNING                        | Estado→ABORTED                                | Coordinator o Human |
| RESULT       | `CAPTURE`   | EXECUTION.COMPLETED                                | Estado→CAPTURED                               | Captor              |
| RESULT       | `CORRELATE` | Estado=CAPTURED, nonce coincide                    | Estado→CORRELATED                             | Coordinator         |
| RESULT       | `FREEZE`    | Estado=CORRELATED, criteria_digest coincide        | Estado→FROZEN                                 | Coordinator         |
| EVALUATION   | `VALIDATE`  | RESULT.FROZEN, criteria_snapshot válido            | Estado→VALID o INVALID                        | Validator           |
| EVALUATION   | `ACTIVATE`  | Estado=VALID, CAS sobre PA                         | Estado→ACTIVE, anterior→SUPERSEDED            | Coordinator         |
| EVALUATION   | `VOID`      | Revocación aplicable                               | Estado→VOIDED                                 | Coordinator         |
| CONTRIBUTION | `COMMIT`    | EVALUATION.ACTIVE, CAS sobre contribución anterior | Estado→ACTIVE, anterior→RETRACTED             | Coordinator         |
| PLAN         | `VOID`      | Revocación concurrente o tombstone                 | Estado→VOIDED, draft_contributions invisibles | Coordinator         |

---

## PARTE III — R10_V0_7_TEST_MATRIX (REF_V07_T123–REF_V07_T196)

**Clasificación de cada prueba:**

- `EXPRESSED`: escenario descrito expresamente en la misión o informe adversarial.
- `RECONSTRUCTED`: formulación anterior mencionada o criticada; formulación nueva aquí.
- `NEW_COVERAGE`: prueba nueva para completar cobertura.

No se afirma que ninguna prueba haya sido ejecutada.

---

#### REF_V07_T123–REF_V07_T134: Identidad, linaje y elegibilidad base

**REF_V07_T123** `EXPRESSED` — `DRY_RUN` no produce `BASE_ELIGIBLE`

Estado inicial: EXECUTION.mode=DRY_RUN, EXECUTION.state=COMPLETED, RESULT.CORRELATED, EVALUATION.VALID.

Evento aceptado: `FREEZE`, `VALIDATE`.

Evento rechazado: activación de contribución automática.

Estado final: `BASE_ELIGIBLE=false`, EVALUATION.state=VALID pero sin contribución AUTO activa.

ΔTS=none, ΔPA=none. Niveles: L0=false (modo DRY_RUN). Oráculo exacto: el coordinador rechaza la activación de contribución con `INELIGIBLE_MODE`.

**REF_V07_T124** `EXPRESSED` — `SIMULATED` no produce `BASE_ELIGIBLE`

Igual a REF_V07_T123 con mode=SIMULATED. Oráculo idéntico.

**REF_V07_T125** `EXPRESSED` — `SANDBOX_ISOLATED` no produce `BASE_ELIGIBLE`

Igual a REF_V07_T123 con mode=SANDBOX_ISOLATED. Oráculo idéntico.

**REF_V07_T126** `RECONSTRUCTED` — Modo `UNKNOWN` no produce `BASE_ELIGIBLE`

Igual a REF_V07_T123 con mode=UNKNOWN. Oráculo idéntico.

**REF_V07_T127** `NEW_COVERAGE` — Ruta no acreditada bloquea elegibilidad

Estado inicial: EXECUTION.mode=REAL, ruta_id no en route_registry.

Evento rechazado: DISPATCH (falla antes).

Oráculo: DISPATCH→`UNACCREDITED_ROUTE`, estado permanece pre-DISPATCHED, BASE_ELIGIBLE=false.

**REF_V07_T128** `NEW_COVERAGE` — Ejecución REAL con todos los predicados cumplidos → BASE_ELIGIBLE=true

Estado inicial: EXECUTION.mode=REAL, ruta acreditada, RESULT.CORRELATED, EVALUATION.VALID, criteria_digest coincide, sin conflicto ni tombstone.

Evento aceptado: activación de contribución.

Estado final: BASE_ELIGIBLE=true, CONTRIBUTION.ACTIVE.

Niveles: L0..L4=true.

**REF_V07_T129** `RECONSTRUCTED` — Predicado BASE_ELIGIBLE no escribible por productor

Intento: Executor escribe `BASE_ELIGIBLE=true` directamente.

Oráculo: rechazado con `UNAUTHORIZED_WRITE`.

**REF_V07_T130** `NEW_COVERAGE` — Linaje único activo

Intento: activar dos estrategias del mismo lineage_id simultáneamente.

Resolución por CAS: primera gana, segunda→`CAS_CONFLICT`.

Estado final: exactamente una STRATEGY.ACTIVE por lineage_id.

**REF_V07_T131** `NEW_COVERAGE` — version_seq incrementa correctamente en sustitución

Estado inicial: STRATEGY.version_seq=3 activa.

Evento: derivar nueva estrategia del mismo linaje.

Estado final: nueva STRATEGY con parent_id=anterior, version_seq=4, anterior→no ACTIVE.

**REF_V07_T132** `NEW_COVERAGE` — Fallo no atribuible a estrategia

Estado inicial: EXECUTION.mode=REAL, falla por timeout de red (causa registrada como `INFRA_TIMEOUT`).

Oráculo: fallo clasificado como no-atribuible, no genera evidencia negativa de estrategia, RESULT.REJECTED, BASE_ELIGIBLE=false para esta ejecución.

**REF_V07_T133** `NEW_COVERAGE` — Tombstone hace BASE_ELIGIBLE=false permanente

Estado inicial: EXECUTION.COMPLETED, BASE_ELIGIBLE=true antes del tombstone.

Evento: tombstone aplicado al linaje.

Estado final: BASE_ELIGIBLE=false para todas las ejecuciones del linaje. ΔTS: si la contribución activa era de este linaje, TS se recalcula sin ella.

**REF_V07_T134** `NEW_COVERAGE` — Tombstone no bloquea nuevo linaje sobre misma tarea

Estado inicial: tombstone sobre linaje_A para tarea_X.

Evento: crear linaje_B para tarea_X y ejecutar.

Oráculo: permitido, BASE_ELIGIBLE evaluado limpiamente para linaje_B.

---

#### REF_V07_T135–REF_V07_T144: Correlación y captura

**REF_V07_T135** `EXPRESSED` — Turno de ejecución anterior no atribuible a ejecución nueva

Estado inicial: EXECUTION_1.COMPLETED (turno_id=T1), EXECUTION_2.DISPATCHED.

Intento: captor reporta turno_id=T1 para EXECUTION_2.

Oráculo: RESULT_2→`UNCORRELATED` (nonce no coincide con dispatch_2).

**REF_V07_T136** `NEW_COVERAGE` — Captura sin turn_id verificable

Estado inicial: plataforma no provee evidencia de turn_id.

Oráculo: RESULT→`UNCORRELATED`, no apta para aprendizaje automático.

**REF_V07_T137** `NEW_COVERAGE` — Captura parcial rechazada

Estado inicial: EXECUTION.COMPLETED, captor entrega salida truncada.

Oráculo: RESULT→`REJECTED`.

**REF_V07_T138** `NEW_COVERAGE` — Nonce expirado en correlación

Estado inicial: captura llega después de la expiración del nonce del despacho.

Oráculo: RESULT→`UNCORRELATED`.

**REF_V07_T139** `NEW_COVERAGE` — Captor no autorizado

Estado inicial: entidad no registrada en captor_registry intenta CAPTURE.

Oráculo: `UNAUTHORIZED_CAPTOR`, RESULT no creado.

**REF_V07_T140** `RECONSTRUCTED` — Resultado no correlacionado permite análisis manual pero no automático

Estado inicial: RESULT.UNCORRELATED, lane=MANUAL asignado explícitamente.

Oráculo: EVALUATION.lane=MANUAL puede crearse; CONTRIBUTION.lane=AUTO rechazada.

**REF_V07_T141** `NEW_COVERAGE` — Correlación correcta establece RESULT.CORRELATED

Estado inicial: nonce coincide, timestamp dentro del rango, turn_id verificable.

Oráculo: RESULT→`CORRELATED`.

**REF_V07_T142** `NEW_COVERAGE` — Congelación requiere estado CORRELATED previo

Intento: FREEZE sobre RESULT.UNCORRELATED.

Oráculo: rechazado con `INVALID_STATE`.

**REF_V07_T143** `NEW_COVERAGE` — Captura duplicada con mismo idempotency_key

Estado inicial: RESULT ya en CAPTURED.

Evento: segundo CAPTURE con mismo idempotency_key.

Oráculo: `ACK_DUPLICATE`, sin efecto adicional.

**REF_V07_T144** `NEW_COVERAGE` — Salida completa con metadata completa → CAPTURED exitoso

Oráculo: RESULT→CAPTURED con capture_digest registrado.

---

#### REF_V07_T145–REF_V07_T154: Criterios, validación y evaluación

**REF_V07_T145** `EXPRESSED` — Evaluación con criterios distintos a los congelados → CRITERIA_MISMATCH

Estado inicial: despacho con criteria_snapshot_id=CS1 (digest=D1). Validador usa criteria_snapshot_id=CS2 (digest=D2).

Oráculo: EVALUATION→`INVALID` por CRITERIA_MISMATCH.

**REF_V07_T146** `NEW_COVERAGE` — Revisión permisiva no retroactiva

Estado inicial: EVALUATION.INVALID por CRITERIA_MISMATCH. Nuevos criterios CS3 son más permisivos.

Oráculo: EVALUATION permanece INVALID. CS3 solo aplica a despachos futuros.

**REF_V07_T147** `NEW_COVERAGE` — Congelación registra digest correcto

Estado inicial: criteria_snapshot_id=CS1, digest=D1.

Evento: FREEZE con criteria_snapshot_id=CS1.

Oráculo: RESULT.criteria_digest=D1 registrado en el log.

**REF_V07_T148** `RECONSTRUCTED` — Validación determinista: mismas entradas → mismo resultado

Estado inicial: RESULT.FROZEN, CS1.

Evento: dos validaciones independientes con mismas entradas.

Oráculo: ambas producen PASS o ambas producen FAIL; nunca divergen.

**REF_V07_T149** `NEW_COVERAGE` — Evaluación inválida no activa contribución

Estado inicial: EVALUATION.INVALID.

Intento: activar contribución.

Oráculo: rechazado con `INVALID_EVALUATION`.

**REF_V07_T150** `NEW_COVERAGE` — Activación de evaluación: atómica, PA actualiza

Estado inicial: EVALUATION_A.ACTIVE (PA→A). Nueva EVALUATION_B.VALID mismo linaje.

Evento: ACTIVATE B.

Estado final atómico: B.ACTIVE, A.SUPERSEDED, PA→B. En ningún estado intermedio coexisten dos ACTIVE.

**REF_V07_T151** `NEW_COVERAGE` — Política de selección congelada y versionada

Estado inicial: dos evaluaciones candidatas, política=v2.

Evento: actualización de política a v3.

Oráculo: proyección actual usa v2 (congelada en el momento de la consulta activa). v3 aplica a proyecciones futuras.

**REF_V07_T152** `NEW_COVERAGE` — Score evaluación es determinista dado mismo perfil

Estado inicial: mismo RESULT.FROZEN, mismo perfil.

Evento: dos ejecuciones del evaluador.

Oráculo: scores idénticos.

**REF_V07_T153** `NEW_COVERAGE` — Perfil no registrado bloquea evaluación

Intento: evaluación con perfil (strategy_id, mode, route_id, criteria_id) no registrado.

Oráculo: rechazado con `UNREGISTERED_PROFILE`.

**REF_V07_T154** `NEW_COVERAGE` — Criterios congelados antes del despacho

Intento: despacho sin criteria_snapshot_id asignado.

Oráculo: rechazado con `CRITERIA_NOT_FROZEN`.

---

#### REF_V07_T155–REF_V07_T164: Contribuciones, planes y retractaciones

**REF_V07_T155** `EXPRESSED` — Contribuciones activas duplicadas bloqueadas

Estado inicial: CONTRIBUTION_A.ACTIVE para (dest_X, linaje_1, tipo_T).

Intento: activar CONTRIBUTION_B para mismo (dest_X, linaje_1, tipo_T) sin retractar A.

Oráculo: CAS rechaza, B no se activa hasta que A está RETRACTED.

**REF_V07_T156** `EXPRESSED` — Sustitución atómica de contribuciones

Estado inicial: CONTRIBUTION_A.ACTIVE.

Evento: nueva evaluación activa en mismo linaje.

Oráculo: A→RETRACTED y B→ACTIVE en la misma transacción. Ningún estado intermedio con dos ACTIVE.

**REF_V07_T157** `NEW_COVERAGE` — Retractación durable sobrevive a caída

Estado inicial: A→RETRACTED (durable), B→ACTIVE.

Evento: caída y recuperación.

Estado final: A sigue RETRACTED, B sigue ACTIVE. No se reactivan contribuciones retractadas.

**REF_V07_T158** `EXPRESSED` — Plan VOIDED: draft_contributions invisibles

Estado inicial: PLAN.EXECUTING con draft_contributions=[C1, C2].

Evento: VOID (por revocación).

Estado final: PLAN.VOIDED, C1 y C2 permanecen DRAFT invisible. TS no cambia.

**REF_V07_T159** `NEW_COVERAGE` — Plan COMPLETED activa contribuciones siguiendo §10.1

Estado inicial: PLAN.EXECUTING, draft_contributions=[C1] para (dest_X, linaje_1, tipo_T), CONTRIBUTION_A.ACTIVE para misma clave.

Evento: PLAN.COMPLETE.

Estado final atómico: A→RETRACTED, C1→ACTIVE. Una sola ACTIVE.

**REF_V07_T160** `NEW_COVERAGE` — Tombstone permanente, no revocable por mismo actor

Intento: actor que creó el tombstone intenta revocarlo.

Oráculo: rechazado con `TOMBSTONE_IRREVOCABLE`.

**REF_V07_T161** `NEW_COVERAGE` — Conflicto en cuarentena no bloquea otros linajes

Estado inicial: EVALUATION_A y EVALUATION_B del mismo linaje en conflicto (A en QUARANTINE).

Evento: nueva evaluación de linaje_2 sobre otra tarea.

Oráculo: linaje_2 no está bloqueado, puede activarse.

**REF_V07_T162** `NEW_COVERAGE` — Resolución de cuarentena por autoridad explícita

Estado inicial: EVALUATION_A.QUARANTINE, EVALUATION_B.ACTIVE.

Evento: autoridad humana resuelve: ACTIVATE A (A era correcta).

Estado final: B→SUPERSEDED, A→ACTIVE atómicamente.

**REF_V07_T163** `NEW_COVERAGE` — Abandono requiere plazo registrado

Intento: coordinador intenta abandonar evaluación basándose en plazo no registrado durablemente.

Oráculo: rechazado con `UNDOCUMENTED_DEADLINE`.

**REF_V07_T164** `NEW_COVERAGE` — Idempotencia de commit de contribución

Estado inicial: CONTRIBUTION_A ya COMMITTED.

Evento: segundo intento con mismo idempotency_key.

Oráculo: `ACK_DUPLICATE`, A sin cambio.

---

#### REF_V07_T165–REF_V07_T174: Autorización, revocación y fencing

**REF_V07_T165** `RECONSTRUCTED` — Commit post-revocación rechazado por fencing

Estado inicial: actor_1 obtiene authorization_token con generation_id=5. Coordinador revoca (generation_id→6). Actor_1 intenta commit.

Oráculo: `FENCING_VIOLATION`, commit descartado.

**REF_V07_T166** `NEW_COVERAGE` — Plan EXECUTING → VOIDED por revocación concurrente

Estado inicial: PLAN.EXECUTING, draft_contributions=[C1], generation_id=5. Revocación concurrente → generation_id=6.

Oráculo: PLAN→VOIDED, C1 invisible. No reactivación posible.

**REF_V07_T167** `NEW_COVERAGE` — CAS en activación de evaluación

Estado inicial: PA apunta a EVAL_A. Dos evaluaciones B y C intentan activarse simultáneamente.

Resolución: primera (mayor seq) → ACTIVE; segunda → CAS_CONFLICT, debe releer.

**REF_V07_T168** `NEW_COVERAGE` — Reloj no disponible → operaciones de tiempo fail-closed

Estado inicial: reloj monotónico de confianza no disponible.

Intento: operación de expiración de nonce.

Oráculo: `CLOCK_UNAVAILABLE`, operación rechazada.

**REF_V07_T169** `NEW_COVERAGE` — Generación actual requerida para escritura

Intento: escritura con generation_id=4, vigente es 6.

Oráculo: `FENCING_VIOLATION`.

**REF_V07_T170** `NEW_COVERAGE` — Token de autorización sin firma del coordinador

Intento: dispatch_receipt sin firma verificable.

Oráculo: evaluación automática rechazada.

**REF_V07_T171** `RECONSTRUCTED` — Evaluaciones concurrentes incompatibles resueltas por seq

Estado inicial: EVAL_B (seq=100) y EVAL_C (seq=101) ambas VALID, mismo linaje.

Evento: intento de activación concurrente.

Oráculo: C (mayor seq) gana. B→QUARANTINE, no depende del consumidor (`SC-7` bloqueado).

**REF_V07_T172** `NEW_COVERAGE` — Revocación no bloquea consulta de historial

Estado inicial: linaje revocado.

Evento: consulta del log de eventos del linaje.

Oráculo: log accesible en modo lectura. No se activan nuevas contribuciones.

**REF_V07_T173** `NEW_COVERAGE` — Nuevo despacho tras caída y ABORT correcto

Estado inicial: EXECUTION_1.DISPATCHED, caída antes de RUNNING.

Recuperación: EXECUTION_1→ABORTED (causa=CRASH_RECOVERY).

Nuevo despacho: EXECUTION_2 con nuevo nonce.

Oráculo: EXECUTION_2 es un despacho independiente y válido.

**REF_V07_T174** `NEW_COVERAGE` — SEQ_CONFLICT en escritura concurrente

Estado inicial: dos escritores intentan escribir seq=N+1 sobre la misma entidad.

Oráculo: primera acepta, segunda→`SEQ_CONFLICT`, debe releer y reenviar con N+2.

---

#### REF_V07_T175–REF_V07_T184: Casos adversariales SC-1 a SC-10

**REF_V07_T175** `EXPRESSED` (SC-1) — DRY_RUN no genera aprendizaje automático

Estado inicial: EXECUTION.mode=DRY_RUN, completado con resultado.

Secuencia adversarial: intentar activar evaluación AUTO sobre resultado de DRY_RUN.

Regla que lo impide: §8.1 condición 2; §4.1.

Estado final: BASE_ELIGIBLE=false, CONTRIBUTION.AUTO no creada.

Efectos permitidos: registro histórico, análisis manual con lane=MANUAL si se asigna explícitamente.

Prueba discriminante: validar que CONTRIBUTION.lane=AUTO.ACTIVE es false tras la secuencia.

**REF_V07_T176** `EXPRESSED` (SC-2) — Turno de ejecución anterior no atribuible a ejecución nueva

Estado inicial: EXECUTION_1.COMPLETED (nonce_1). EXECUTION_2.DISPATCHED (nonce_2).

Secuencia adversarial: captor reporta result_2 con turn_id del turno de EXECUTION_1 (nonce_1).

Regla: §5.1 — nonce de la captura debe coincidir con nonce del despacho.

Estado final: RESULT_2→UNCORRELATED. BASE_ELIGIBLE=false para EXECUTION_2.

Prueba discriminante: verificar que RESULT_2.state=UNCORRELATED cuando nonce en captura ≠ nonce en dispatch_receipt.

**REF_V07_T177** `EXPRESSED` (SC-3) — Contribuciones activas duplicadas bloqueadas entre evaluaciones sucesoras

Estado inicial: EVALUATION_A.ACTIVE, CONTRIBUTION_A.ACTIVE para (dest_X, linaje_1, tipo_T).

Secuencia adversarial: activar EVALUATION_B del mismo linaje sin retractar CONTRIBUTION_A.

Regla: §10.1, §7.4 — activación de B retracta A atómicamente.

Estado final: exactamente una CONTRIBUTION.ACTIVE para la clave. Si CAS falla, B→QUARANTINE.

Prueba discriminante: contar CONTRIBUTION.ACTIVE=1 tras cualquier activación de evaluación del mismo linaje.

**REF_V07_T178** `EXPRESSED` (SC-4) — PA no apunta a evaluación SUPERSEDED

Estado inicial: PA→EVAL_A. EVAL_B activa (EVAL_A→SUPERSEDED).

Secuencia adversarial: lectura de PA.

Regla: §9.3 — PA actualiza atómicamente con la activación.

Estado final: PA→EVAL_B. PA nunca apunta a EVAL_A (SUPERSEDED).

Prueba discriminante: lectura de PA inmediatamente después de activación de B → devuelve B.

**REF_V07_T179** `EXPRESSED` (SC-5) — Éxito evaluado con comprobaciones distintas a las congeladas

Estado inicial: despacho con criteria_snapshot_id=CS1 (digest=D1). Evaluación usa CS2 (digest=D2).

Secuencia adversarial: validador usa digest D2 ≠ D1.

Regla: §6.2, §7.1.

Estado final: EVALUATION→INVALID por CRITERIA_MISMATCH.

Prueba discriminante: EVALUATION.state=INVALID y reason=CRITERIA_MISMATCH cuando digests difieren.

**REF_V07_T180** `EXPRESSED` (SC-6) — Abandono basado en plazo inexistente bloqueado

Estado inicial: EVALUATION.VALIDATING, sin plazo de abandono registrado durablemente.

Secuencia adversarial: coordinador intenta abandonar basándose en tiempo transcurrido sin registro.

Regla: §11.3.

Estado final: abandono rechazado con UNDOCUMENTED_DEADLINE.

Prueba discriminante: intento de abandono sin plazo → error, evaluación permanece en estado previo.

**REF_V07_T181** `EXPRESSED` (SC-7) — Evaluaciones concurrentes: resultado determinado por seq, no por consumidor

Estado inicial: EVAL_B (seq=100) y EVAL_C (seq=101), mismo linaje, ambas VALID.

Secuencia adversarial: dos consumidores intentan activar B y C simultáneamente.

Regla: §9.2, §13.3 — CAS resuelve por seq mayor.

Estado final: C.ACTIVE (seq=101), B.QUARANTINE.

Prueba discriminante: resultado siempre C independientemente del orden de llegada de los consumidores.

**REF_V07_T182** `EXPRESSED` (SC-8) — Commit post-revocación bloqueado

Estado inicial: actor_1 tiene authorization_token generation_id=5, PLAN.EXECUTING. Revocación → generation_id=6. Actor_1 intenta commit de efectos.

Regla: §13.1, §13.2, §17.2.

Estado final: FENCING_VIOLATION, commit descartado, PLAN→VOIDED.

Prueba discriminante: ningún efecto del plan es visible tras la secuencia.

**REF_V07_T183** `EXPRESSED` (SC-9) — Evaluación manual no se convierte en resultado automático vigente

Estado inicial: EVALUATION.lane=MANUAL, válida y activa como TS_MANUAL.

Secuencia adversarial: intento de promover a lane=AUTO sin operación explícita autorizada.

Regla: §14.3.

Estado final: TS automático no cambia; EVALUATION.lane=MANUAL permanece en carril separado.

Prueba discriminante: TS_AUTO ≠ valor de la evaluación manual.

**REF_V07_T184** `EXPRESSED` (SC-10) — Retractación no impide nueva evaluación sobre misma tarea con nuevo linaje

Estado inicial: CONTRIBUTION_A del linaje_A retractada. Tombstone sobre linaje_A.

Secuencia adversarial: intento de restaurar linaje_A (bloqueado por tombstone). Nuevo linaje_B creado para misma tarea.

Regla: §10.4 (tombstone no bloquea linajes nuevos), §1.3.

Estado final: linaje_A irrecuperable; linaje_B puede producir nueva evaluación limpia.

Prueba discriminante: BASE_ELIGIBLE puede ser true para EXECUTION de linaje_B sobre tarea_X.

---

#### REF_V07_T185–REF_V07_T196: Coberturas adicionales

**REF_V07_T185** `NEW_COVERAGE` — Legado no elegible para AUTO

Estado inicial: registro legacy=true (campos requeridos ausentes).

Intento: activar CONTRIBUTION.AUTO.

Oráculo: rechazado con `LEGACY_INELIGIBLE`.

**REF_V07_T186** `NEW_COVERAGE` — L4 es predicado derivado, no marca histórica

Estado inicial: CONTRIBUTION.ACTIVE (L4=true). Retractación de la contribución.

Oráculo: L4 recalcula → false. El registro histórico persiste pero L4 actual es false.

**REF_V07_T187** `NEW_COVERAGE` — L5b requiere comparador predefinido antes de ejecución

Estado inicial: diseño de medición sin comparador predefinido.

Intento: reclamar L5b post-hoc.

Oráculo: L5b=false. Predicado derivado exige criterios preestablecidos anteriores a la ejecución.

**REF_V07_T188** `NEW_COVERAGE` — Recuperación de dos ACTIVE tras caída

Estado inicial: caída durante transacción de retractación; al recuperar, CONTRIBUTION_A y CONTRIBUTION_B ambas ACTIVE para misma clave.

Oráculo: coordinador detecta duplicado, retracta la de menor seq. Una sola ACTIVE.

**REF_V07_T189** `NEW_COVERAGE` — Operación DISPATCHED sin RUNNING tras caída → ABORTED

Estado inicial: EXECUTION.DISPATCHED antes de caída. Coordinador reinicia.

Oráculo: EXECUTION→ABORTED (causa=CRASH_RECOVERY). Nuevo despacho posible.

**REF_V07_T190** `NEW_COVERAGE` — Aislamiento carril manual: TS_MANUAL ≠ TS_AUTO

Estado inicial: EVALUATION.lane=MANUAL activa, EVALUATION.lane=AUTO activa, valores diferentes.

Oráculo: TS_MANUAL y TS_AUTO son proyecciones independientes y pueden diferir.

**REF_V07_T191** `NEW_COVERAGE` — Despacho sin receipt no produce evaluación automática

Intento: evaluación sobre EXECUTION que no tiene dispatch_receipt firmado.

Oráculo: rechazado con `MISSING_RECEIPT`.

**REF_V07_T192** `NEW_COVERAGE` — criteria_digest mal formado rechazado en congelación

Intento: FREEZE con criteria_digest no coincidente con el contenido del snapshot.

Oráculo: RESULT→REJECTED o congelación rechazada con `DIGEST_MISMATCH`.

**REF_V07_T193** `NEW_COVERAGE` — Concurrencia: dos retractaciones sobre misma contribución

Estado inicial: CONTRIBUTION_A.ACTIVE. Dos actores intentan retractarla simultáneamente.

Oráculo: primera → RETRACTED; segunda → `ACK_DUPLICATE` o `SEQ_CONFLICT` sin efecto.

**REF_V07_T194** `NEW_COVERAGE` — Plan no se reactiva tras VOIDED

Estado inicial: PLAN.VOIDED.

Intento: transicionar PLAN a EXECUTING.

Oráculo: rechazado con `TERMINAL_STATE`.

**REF_V07_T195** `NEW_COVERAGE` — Escritor de modo no puede ser el ejecutor

Intento: EXECUTION reporta su propio modo en el momento de COMPLETE.

Oráculo: campo modo ignorado en evento COMPLETE; modo fue establecido en DISPATCH por el coordinador.

**REF_V07_T196** `NEW_COVERAGE` — seq_conflict resuelto y reintento exitoso

Estado inicial: escritor_A y escritor_B intentan seq=N+1 sobre entidad E. A gana (seq=N+1). B recibe SEQ_CONFLICT.

Evento: B relee, obtiene seq vigente=N+1, reenvía con seq=N+2.

Oráculo: B acepta con seq=N+2.

---

## PARTE IV — R10_V0_7_ADVERSARIAL_REVIEW

### SC-1–SC-10 (resumen de cierre)

| SC    | Secuencia adversarial                             | Cláusula que cierra                       | Estado final tras cierre                         |
| ----- | ------------------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| SC-1  | DRY_RUN → aprendizaje AUTO                        | §8.1(2), §4.1                             | BASE_ELIGIBLE=false, contribución AUTO no creada |
| SC-2  | Turno anterior → ejecución nueva                  | §5.1, nonce check                         | RESULT→UNCORRELATED                              |
| SC-3  | Contribuciones duplicadas en sucesoras            | §10.1, CAS atómico                        | Exactamente una ACTIVE por clave                 |
| SC-4  | PA apunta a SUPERSEDED                            | §9.3, activación atómica                  | PA→nueva en misma transacción                    |
| SC-5  | Comprobaciones distintas a criterios congelados   | §6.2, §7.1                                | EVALUATION→INVALID/CRITERIA_MISMATCH             |
| SC-6  | Abandono por plazo inexistente                    | §11.3                                     | Abandono rechazado/UNDOCUMENTED_DEADLINE         |
| SC-7  | Evaluaciones concurrentes, ganador por consumidor | §9.2, §13.3, CAS por seq                  | Ganador determinado por seq, no por consumidor   |
| SC-8  | Commit post-revocación                            | §13.1, §13.2, fencing                     | FENCING_VIOLATION, commit descartado             |
| SC-9  | Manual → resultado AUTO vigente                   | §14.3, separación de carriles             | TS_AUTO no alterado por evaluación MANUAL        |
| SC-10 | Retractación bloquea nueva evidencia              | §10.4, tombstone no cierra nuevos linajes | Nuevo linaje permitido sobre misma tarea         |

### Invariantes I1–I12 (verificación)

Los invariantes I–VIII de la misión se mapean a cláusulas del contrato:

| Invariante                         | Cláusula principal | Cláusula de respaldo |
| ---------------------------------- | ------------------ | -------------------- |
| I (Elegibilidad universal)         | §8.1               | §4.1                 |
| II (Correlación auténtica)         | §5.1               | §11.1                |
| III (Criterios congelados)         | §6.1–§6.3          | §7.1–§7.2            |
| IV (Contribuciones y recuperación) | §10.1–§10.2        | §17.1                |
| V (Proyección determinista)        | §9.1–§9.3          | §7.3                 |
| VI (Revocación fail-closed)        | §13.1–§13.2        | §17.2                |
| VII (Separación de carriles)       | §14.1–§14.4        | §3.3                 |
| VIII (Evidencia vigente)           | §16                | §8.1                 |

### Revisión adversarial de cierre

No se encuentra ningún camino por el que simulación, respuesta no correlacionada o criterios no congelados puedan producir `BASE_ELIGIBLE=true` en la especificación reconstruida.

**Reglas alternativas revisadas:**

- ¿Puede un productor alcanzar BASE_ELIGIBLE=true escribiendo directamente? No: §18 y §8.1 lo prohíben.
- ¿Puede un resultado UNCORRELATED ser reconvertido en CORRELATED post-hoc? No: CORRELATED requiere verificación del coordinador en el momento de la correlación; no hay transición UNCORRELATED→CORRELATED.
- ¿Puede un plan VOIDED reactivar sus contribuciones en la recuperación? No: §10.3 y §17.1(5).
- ¿Puede un evaluador manual alterar TS automático sin operación explícita? No: §14.2–§14.3.
- ¿Puede un commit con generation_id obsoleto persistir si llega después de la recuperación del coordinador? No: §17.1(5) verifica generation_id en la recuperación.

**Defecto residual identificado (local, no material):** la especificación define que la resolución de cuarentena puede ser por “regla de resolución automática documentada” (§12.2) pero no enumera esas reglas. Esto crea una apertura teórica para una regla automática mal diseñada. Es un defecto de completitud del documento, no una contradicción que permita efectos indebidos ya que cualquier regla de resolución debe documentarse explícitamente antes de usarse.

---

## PARTE V — IMPLEMENTATION_DEPENDENCIES_UNPROVEN

Ver §19 del contrato. Resumen de consecuencias operativas:

Si `CLOCK_UNAVAILABLE`: todas las operaciones de expiración y fencing basadas en tiempo fallan cerradas. El sistema no puede completar evaluaciones con plazo.

Si CAS no disponible: SC-3, SC-4 y SC-7 no están cerrados en runtime aunque el contrato los especifique.

Si correlación de turno no verificable: toda captura automática es UNCORRELATED. El aprendizaje automático queda inoperante.

Estas dependencias no reducen la suficiencia semántica del contrato, pero son requisitos de implementación necesarios para que el contrato sea efectivo en runtime.

---

## PARTE VI — AUTHORIZATION_BOUNDARY

Esta reconstrucción autoriza únicamente:

- Reconstrucción documental, formalización y revisión estática.
- Uso como especificación de referencia para diseño.

**No autoriza:**

- Ejecución, pruebas, builds.
- Acceso al checkout local M0A.
- Credenciales o cambios en el repositorio.
- Modificación de documentos canónicos.

La reconstrucción de la especificación no demuestra que esté implementada.

---

## ACCEPTANCE_DECISION

**`PASS_WITH_REPAIRS`**

El contrato reconstruido es internamente coherente. Los diez contraejemplos SC-1–SC-10 están cerrados por cláusulas específicas. Los invariantes I–VIII están respaldados. La matriz REF_V07_T123–REF_V07_T196 tiene oráculos exactos y no disyuntivos.

Defecto local identificado: §12.2 menciona “regla de resolución automática documentada” sin enumerar esas reglas. Este defecto no permite efectos indebidos porque cualquier regla debe documentarse explícitamente, pero debe completarse antes de la implementación.

**Reparación mínima:** añadir a §12.2 la lista cerrada de reglas de resolución automática permitidas, o explícitamente declarar que solo se permite resolución manual en v0.7.

La postura de gobierno permanece `KEEP_BLOCKED`. La suficiencia semántica es necesaria pero no suficiente: la viabilidad técnica, la evidencia de implementación y la evidencia causal de mejora son dimensiones separadas, todas `UNPROVEN`.

Se quedó sin [mensajes](https://support.claude.com/en/articles/11647753-understanding-usage-and-length-limits) gratuitos hasta 2:40 p.m.