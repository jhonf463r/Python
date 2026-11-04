## Auditoría R10 v0.7.1: dictamen `FAIL`

Revisión estática, sin ejecutar nada. Clasifico como `PROVEN_BY_SOURCE` lo que cito del texto del paquete y como `UNPROVEN` toda dependencia técnica.

### 1. INPUT_ARTIFACTS_AND_PROVENANCE

Calculé el SHA-256 sobre los bytes reales del zip y de los cinco archivos extraídos. Los seis hashes y tamaños coinciden con `R10_V0_7_1_AUDIT_PACKAGE_SHA256.txt`. Estado: verificado.

El `SOURCE_V0_7_SHA256` que cita el contrato (`5babd981…`) coincide con la referencia incluida. Los hashes del v0.7.1 original de ChatGPT siguen siendo `OWNER_REPORTED`. Ese artefacto no está en el paquete, así que lo que audité es la reconstrucción, no el original.

El cuerpo del contrato se declara `PASS_WITH_REPAIRS` a sí mismo y afirma que no encuentra ningún camino indebido. No lo uso como evidencia.

### 2. SC1_SC10_VERDICT

Se evalúa con C1–C13 prevaleciendo sobre el cuerpo subordinado, como indica §0.

| SC    | Estado           | Motivo                                                                                                                                        |
| ----- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| SC-1  | Cerrado en texto | C8 exige modo planeado igual a modo observado y atestado. El `T195` del cuerpo lo contradice: “campo modo ignorado… establecido en DISPATCH”. |
| SC-2  | Parcial          | Ver D3.                                                                                                                                       |
| SC-3  | Parcial          | Ver D4 y D6.                                                                                                                                  |
| SC-4  | Parcial          | `PA` y `TS` no tienen mapeo a los punteros de C1.                                                                                             |
| SC-5  | Parcial          | Solo se detecta discrepancia declarada. El validador reporta sus propios digest (C3 lo admite).                                               |
| SC-6  | Parcial          | Los ciclos de vida del cuerpo (§3.1) no tienen `ABANDONED` ni `SUPERSEDED`. No hay prueba de `TASK_REOPENED`.                                 |
| SC-7  | Abierto          | Ver D2.                                                                                                                                       |
| SC-8  | Cerrado en texto | C9 y el fencing cubren el commit. Queda el residuo de D5.                                                                                     |
| SC-9  | Abierto          | Ver D2.                                                                                                                                       |
| SC-10 | Abierto          | Ver D2.                                                                                                                                       |

### 3. CONTRACT_CONSISTENCY_FINDINGS

**D1 (material). `T185–T196` reasignados.**

Los 12 IDs designan un escenario en el cuerpo del contrato (Parte III) y en la referencia v0.7, y otro distinto en el CSV:

| ID   | Parte III del contrato     | CSV                         |
| ---- | -------------------------- | --------------------------- |
| T185 | Legado                     | `MODE_MISMATCH`             |
| T186 | L4 derivado                | `MODE_UNATTESTED…`          |
| T188 | Recuperación de dos ACTIVE | `MISSING_PRODUCER_EVENT_ID` |
| T195 | Escritor de modo           | `LEGACY_RESULT_SUCCESS`     |

Lo mismo ocurre con T187 y T189–T194 y T196. Una cita de `T188` es ambigua según el archivo. Los escenarios originales (receipt faltante, `criteria_digest` mal formado, `ABORTED` por caída, escritor de modo) pierden su ID.

- Reparación mínima: IDs únicos entre cuerpo y CSV, p. ej. renumerar el CSV desde T197 y marcar los T185–T196 del cuerpo como retirados.
- Prueba discriminante: validador que falle si un `test_id` tiene dos `scenario` distintos en el paquete.

**D2 (material). Oráculos que contradicen C1–C13.**

- `T171`, `T181`, `T167`: “C (mayor seq) gana, B→QUARANTINE”. C4 dice “No escoger simplemente el mayor `seq`” y exige `CONFLICT_DETECTED`. Además “CAS resuelve por seq mayor” es incoherente: CAS decide por orden de llegada, que es justo lo que SC-7 prohíbe.
- `T188` (cuerpo), §10.2 y §17.1(4): “retracta la de menor seq”. C5 lo prohíbe.
- `T183`, §14.3 y la matriz §18 (Human): permiten “conversión manual→auto con autorización”. C7 dice que no existe esa operación.
- `T184`, §10.4 y `T134`: “nuevo linaje permitido”. C6 dice que un linaje nuevo no sustituye resolver SC-10.
- §12.2 y la parte IV: “regla automática documentada”. C6 la deshabilita.
- La precedencia de §0 resuelve el texto, pero no las pruebas: una implementación conforme a C falla `T171`, `T181` y `T183`, y una que pase esas pruebas viola C.
- Reparación mínima: retirar o reescribir esos oráculos según C4–C7.
- Prueba discriminante: dos evaluaciones incompatibles con el mismo paquete congelado deben producir `CONFLICT_DETECTED` y ninguna contribución automática. Un resolvedor por mayor `seq` debe fallar.

**D3 (material). Correlación con huecos.**

- C2 exige `dispatch_turn_id` “cuando esté disponible” y `in_reply_to_turn_id` “cuando el sistema de destino expresa esa relación”.
- Si el despacho se registra sin `dispatch_turn_id`, no hay contra qué comparar y quedan nonce, sesión y plazo, que C2 declara insuficientes. La cláusula no dice qué rama gana.
- Además, `in_reply_to_turn_id` lo reporta el captor, sin atestación de plataforma.
- `T141` (cuerpo) da `CORRELATED` solo con nonce, timestamp y turn_id.
- Reparación mínima: despacho sin `dispatch_turn_id` autenticado implica `UNCORRELATED`, y `in_reply_to` debe ser atestado por la plataforma, no por el captor.
- Prueba discriminante: nonce, sesión y plazo válidos, pero `in_reply_to_turn_id` distinto o ausente, debe dar `UNCORRELATED`.

**D4 (material). Dos nociones de “linaje”.**

El cuerpo identifica contribuciones por `(dest, lineage_id de estrategia, tipo)` y C5 por `(destination, result_lineage_id, kind)`. Dos resultados de una misma estrategia pueden ser legítimamente visibles bajo C5 y violación bajo `T155`, `T156` y `T177`.

- Reparación mínima: una sola clave de unicidad y un glosario de ambos linajes.

**D5 (material). Efectos visibles tras perder la elegibilidad.**

- C8 pone tombstone, obsolescencia y revocación aplicable como causas de `BASE_ELIGIBLE=false`. Pero solo un conflicto (C6) crea un trabajo durable de retractación.
- C9 hace la revocación prospectiva por defecto, y `retroactive_scope` no tiene autoridad definida.
- Además, el trabajo de suspensión por conflicto no es atómico con el registro del conflicto.
- Secuencia: contribución ACTIVE visible, luego tombstone o `CONFLICT_DETECTED`, luego caída antes del trabajo. L4 es falso por predicado, pero el selector sigue viendo el efecto.
- Reparación mínima: tombstone, conflicto y revocación retroactiva deben retraer atómicamente, o bloquear la lectura de la contribución hasta completar el trabajo.
- Prueba discriminante: caída entre el evento y el trabajo; ningún consumidor debe ver la contribución.

**D6 (parcial).**

- Vocabularios de estado: C5 y C9 usan `PREPARING` y `PARTIAL`, y el cuerpo usa `PENDING` y `COMMITTED`. No queda claro si `COMMITTED` es visible.
- “Autoridad independiente” no está definida.
- “Generación” significa dos cosas: publicación (C5) y autorización (C9).
- El cuerpo usa `REAL` y C8 usa `AUTHORIZED_REAL_EXECUTION`.
- El `seq` es por entidad en el cuerpo y `task_seq` por tarea en C4.

### 4. TEST_MATRIX_AUDIT

- **Identidad:** 74 filas, T123–T196 completas, sin duplicados ni huecos. Las 74 están `NOT_RUN`.
- **T185–T196:** no se corresponden con sus escenarios declarados en el cuerpo. Fueron reasignados (D1). Entre sí, los 12 escenarios del CSV son coherentes con la misión declarada en el README.
- **Oráculos de T123–T184:** 62 de 74 filas tienen campos marcadores (“Derive from C1-C13”, “See source_test_body”, “Review required”). Los deltas y el oráculo de crash no están especificados. La columna de oráculo conserva el texto viejo en conflicto con C (D2).
- **Cobertura:** ninguna fila menciona `CONFLICT_DETECTED`, `EXTRA_TERMINAL_OUTPUT`, `in_reply_to`, `dispatch_turn_id`, `observed_mode`, `PREPARING`, `PARTIAL`, `CONFLICT_RESOLVED`, `supersedes_evaluation_id`, `restores_event_id`, `TASK_REOPENED` ni `ABANDONED`. No hay prueba de mismo `producer_event_id` con digest distinto.
- **Oráculos disyuntivos:** `T193` del cuerpo (“`ACK_DUPLICATE` o `SEQ_CONFLICT`”) y `T191` del CSV (“`LATE_STALE` or rejected”) contradicen la afirmación de “oráculos exactos y no disyuntivos”.

### 5. INVARIANT_TRACEABILITY_I1_I12

El paquete solo mapea “I–VIII”, con etiquetas descriptivas. No hay I9–I12 ni definiciones literales de I1–I12. Sus definiciones históricas no se recuperaron, así que no puedo afirmar equivalencia exacta. El mapeo I–VIII a cláusulas (Parte IV) es del cuerpo subordinado y arrastra D2.

### 6. IMPLEMENTATION_DEPENDENCIES_UNPROVEN

Todas `UNPROVEN`:

- identidad de turno y vínculo respuesta-turno atestado por plataforma;
- atestación del modo observado y de la ruta;
- atestación de que el validador aplicó realmente las comprobaciones;
- reloj autoritativo;
- CAS y transacciones atómicas, y secuenciador durable por tarea;
- fencing y generación de autorización;
- publicación atómica y recuperación;
- aislamiento de escritores legados y rechazo en interfaz R10;
- independencia de la autoridad de resolución;
- replay contrafactual para L5a y L5b.

### 7. ACCEPTANCE_DECISION

**`FAIL`**

No concedo `PASS_WITH_REPAIRS`. D3 y D5 describen caminos de aprendizaje o efecto indebido que el texto no cierra: respuesta insuficientemente correlacionada, efecto visible tras tombstone, conflicto o revocación. Además, D1 y D2 impiden confiar en la matriz como oráculo.

Defectos supervivientes: D1, D2, D3, D4, D5. Reparaciones mínimas arriba. No genero otra versión.

### 8. AUTHORIZATION_BOUNDARY

`KEEP_BLOCKED`. Esto no autoriza ejecución, pruebas, builds, acceso a M0A ni cambios canónicos. Nada de lo auditado demuestra comportamiento de runtime.

---

La revisión de Entry 283 que dejé a medias sigue sin dictamen. Mi análisis parcial mostraba un posible defecto en W1, entre `APPROVAL_FRESHNESS_EXPIRED` y `ISSUANCE_DEADLINE_MISSED`. **Siguiente paso recomendado:** dime si retomo Entry 283 y emito su dictamen antes de que corrijas R10.