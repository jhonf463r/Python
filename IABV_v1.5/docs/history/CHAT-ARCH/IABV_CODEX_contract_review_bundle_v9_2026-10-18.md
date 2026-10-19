# IABV → CODEX — Contract design delta, no runtime
## Paquete autocontenido v9 para novena revisión adversarial documental

**Fecha:** 2026-10-18.  
**Destino de revisión:** Claude / Sonnet.  
**Base documental:** v8 `IABV_CODEX_contract_review_bundle_v8_2026-10-18.md` (SHA-256 `1e7d4fa3a497d329305dba225a9b45d382d07f345e84e6b16d4d8c60c579726b`, 167.312 bytes) y el informe de octava revisión aportado por el propietario en esta conversación (dictamen/identidad del revisor `OWNER_REPORTED`; no se dispone de un artefacto de informe separado con hash verificable).
**Motivo de revisión:** delta documental focalizado para aclarar la respuesta cuando una proyección muestra `USE_COMMITTED` sin autoridad disponible, hacer explícita la rama alternativa de lista manual en N-83 y especificar qué evidencia preexistente podría demostrar exclusividad de cuenta/actividad manual en §2.12. F-V8-02 no se reproduce contra el v8 exacto porque la arista ya figura en la tabla formal; F-V8-01 y F-V8-03 parecen cubiertos por cláusulas preexistentes y se conservan solo como aclaraciones defensivas sujetas a revisión; F-V8-04 sí identifica una carencia concreta de especificación de evidencia.
**Estado:** `PROPOSED_DESIGN_V9 — NOT IMPLEMENTED — NOT ACCEPTED — NOT AUTHORIZED FOR EXECUTION`.  
**Gobierno:** `GOVERNANCE = KEEP_BLOCKED`.  
**Puente:** `BRIDGE_NOT_READY`.

> **Límite vinculante:** esta revisión y este documento son solo documentales. No autorizan preflight local, inspección de checkout, canaria, `codex exec`, App Server, turno de modelo, pruebas, build, runtime, instalación/actualización, autenticación, gasto, acceso a M0A, commit, push, merge ni promoción. La decisión C sigue vigente.

**Procedencia de esta reconciliación v9:** `PROVEN_BY_SOURCE` para la identidad en bytes del v8 verificada mediante SHA-256/tamaño y para la presencia textual de la arista indicada abajo; `OWNER_REPORTED` para el dictamen semántico y las afirmaciones del informe de octava revisión; `PROPOSED` para los cambios v9; `UNPROVEN` para existencia/eficacia de controles; `UNRESOLVED` para capacidades/fuentes no acreditadas; `NOT_RUN` para ejecución, pruebas, build o runtime. La comprobación de identidad del documento o la existencia de una cláusula no valida las conclusiones semánticas del informe.

## 0. Adjudicación de continuidad

La primera revisión del contrato original informó `PASS_WITH_REPAIRS` con C01–C12; la segunda revisión de v2 informó `PASS_WITH_REPAIRS` con N-01–N-12. Las revisiones posteriores agregaron N-13–N-25, N-26–N-41 y N-42–N-64, con estados heredados reportados y no automáticamente aceptados. La sexta revisión informó N-01–N-64: 27 `CLOSED`, 37 `PARTIALLY_CLOSED`; agregó N-65–N-79. El informe suministrado de la séptima revisión declara `PASS_WITH_REPAIRS`, informa N-01–N-79: 30 `CLOSED`, 49 `PARTIALLY_CLOSED`, y añade N-80–N-84. Ese dictamen y esos estados siguen siendo `OWNER_REPORTED`: el coordinador cotejó identidad/tamaño del informe y recuperó el bundle v7 de la Biblioteca, pero no verificó la identidad del revisor ni reabrió las fuentes públicas citadas por este.


**Octava revisión aportada en la conversación (sin archivo separado):** dictamen declarado `PASS_WITH_REPAIRS`; hallazgos F-V8-01 a F-V8-04. El informe declara que F-V8-02 está ausente, pero una lectura independiente del v8 exacto verificado por SHA-256 encontró ya la fila formal `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` en la tabla de transiciones de §2.8. Por ello, F-V8-02 queda `CONTRADICTED_BY_V8_SOURCE / NOT_ADOPTED_AS_NEW_DEFECT`; no se duplica esa arista en v9. La verificación de esta contradicción no autentica al revisor ni valida automáticamente el resto del informe. F-V8-01 y F-V8-03 no se aceptan como defectos independientes sin matiz: §2.8/§2.6 ya cubrían gran parte de su semántica; N-85/N-86 son aclaraciones defensivas opcionales, sujetas a que la novena revisión confirme si queda una brecha real. F-V8-04 se trata como carencia de especificación de evidencia y genera la reparación propuesta N-87. Ninguno levanta gates.

**Regla de adjudicación añadida:** ante cualquier reporte de una arista, cláusula o fila “ausente”, buscarla en el artefacto exacto y verificar la identidad de bytes antes de planear una reparación. El SHA declarado por el informe y el SHA medido del paquete no sustituyen ese cotejo textual local.

**Identidad cotejada de artefactos:** v7: 147.208 bytes, SHA-256 `1672457e391a8882e0b20a855a6d834257cddf3e5f57de198ce6ed85c80db6a4`; informe de séptima revisión: 57.950 bytes, SHA-256 `2d987c533c0bc9ba02b5f981ee0ff2a8d58ef9c39a60b6a6e2d89917930c2cb9`. El hallazgo de continuidad es importante: la búsqueda anterior se limitó a GitHub; v7 estaba en la Biblioteca de archivos aunque no estaba publicado en `main`. No debe repetirse una declaración de “archivo no disponible” hasta buscar fuentes del turno y Biblioteca.

Esta v9 es una delta documental derivada del v8: conserva v8/v7 inmutables, no convierte los dictámenes previos en aceptación, no demuestra controles y no cambia la decisión C. Todo estado derivado de informes anteriores debe seguir etiquetado por procedencia; no se ocultarán degradaciones, hallazgos no recuperados ni dependencias bloqueantes. Los presupuestos permanecen sin gasto adicional y sin plan nuevo.

La revisión de v7 es un informe proporcionado por el propietario, no evidencia de implementación ni prueba de que `CLAUDE_REPORTED_PUBLIC_SOURCE` haya sido verificado en esta sesión.

## 1. Instrucciones para Claude / Sonnet — novena revisión focalizada

Lee íntegro este paquete v9 y revisa su sección contractual §2.1–§2.15. El encargo es una sola revisión adversarial documental; el paquete es autocontenido y no requiere memoria conversacional, otra rama, archivos locales ni acceso al checkout.

Re-adjudica N-01–N-87 contra el texto exacto de v9. No heredes automáticamente `CLOSED` de un informe anterior. Para los hallazgos históricos cuyo contraejemplo no pueda recuperarse fielmente, usa `NOT_RECOVERED`. Evalúa expresamente los cambios propuestos para N-85–N-87 y comprueba si cualquier hallazgo atribuido al v8 ya estaba resuelto en la tabla o cláusula del v8 exacto. La tabla de estados recibidos es historia reportada, no una conclusión normativa que debas preservar si el texto contradice el estado.

Foco obligatorio de N-80–N-87:
- **N-80:** verifica que `authorization_status=CONSUMED` y `authorization_use_status=USE_COMMITTED` sean un único hecho atómico y linealizable por clase/ID; no aceptes `USE_REJECTED_PRECOMMIT` como estado normal compatible con `CONSUMED`. Diferencia una proyección retrasada de una contradicción del log autoritativo.
- **N-81:** comprueba las transiciones explícitas tras expirar el plazo entre gate, reanudación y primera instrucción; fija el resultado de `attempt_status`, incidente y locks para todas las ramas de evidencia, incluida la terminación después de resume pero antes de primera instrucción.
- **N-82:** comprueba la prohibición explícita de usar `LedgerProjector` como fallback para reservar, decidir nonce/gate o resolver indisponibilidad del log. Distingue `DOMAIN_BLOCKED_PENDING` por falta de respuesta de `GOVERNANCE_DOMAIN_BLOCKED` por rollback/divergencia demostrados.
- **N-83:** verifica que scopes solapados/subconjuntos entre clases de autorización jamás sustituyan las autorizaciones predecesoras exigidas en §2.6.
- **N-84:** comprueba que una restauración o cabeza regresiva no convierta la ausencia aparente de `USE_COMMITTED` en prueba de no-uso. La reparación no puede inventar un segundo anclaje por operación que contradiga la arquitectura v7: debe depender de la garantía de no-restauración del log preexistente; si no es acreditable, bloquear.
- **N-85 (de F-V8-01):** una proyección que muestre `USE_COMMITTED` sin respuesta de la autoridad no confirma uso ni no-uso; verifica `USE_UNKNOWN`, `DOMAIN_BLOCKED_PENDING`, ausencia de despacho y retención del lock.
- **N-86 (de F-V8-03):** el orden de predecesores depende de la rama de §2.6; la lista manual exacta firmada para `path_manifest` puede evitar inventario, pero no sustituye autorización de materialización ni pasos aplicables restantes.
- **N-87 (de F-V8-04):** la fila de exclusividad debe identificar evidencia admisible concreta de una capacidad preexistente impuesta por el servicio que cubra el uso manual, sin inferir que esa capacidad existe.
- **Control de contradicciones del informe previo:** el informe octavo declaró ausente la transición `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE`; la tabla formal del v8 exacto ya la contiene. Comprueba la arista en el artefacto recibido, decide si la afirmación es sostenible y no aceptes cambios duplicados por mera repetición de un hallazgo.

Audita además la taxonomía conjunta de satisfacibilidad en §2.12. Debe usar solo `SATISFIABLE`, `CONDITIONALLY_SATISFIABLE`, `BLOCKED_BY_CURRENT_CONSTRAINTS` o `UNRESOLVED` para el estado lógico de cada requisito; mantener por separado el resultado operativo fail-closed `BLOCKED_UNDER_CURRENT_CONSTRAINTS`; nombrar la capacidad exacta, evidencia admisible y dependencia de decisión del propietario. No trates una capacidad “preexistente” hipotética como resuelta ni confundas ausencia de evidencia con prueba de incompatibilidad lógica.

Para cada hallazgo que sobreviva, entrega ID, severidad, sección/frase exacta, contraejemplo discriminante, consecuencia, reparación mínima y criterio futuro. Si una reparación de v8 es incorrecta, identifica por qué y no la marques cerrada por intención. No añadas hallazgos especulativos ni vuelvas a hacer arqueología general; cuestiona las costuras precisas del contrato.

Cierra con los seis ejes: (1) autorización de un solo uso/antirregresión; (2) frontera de confinamiento frente a `Allow`/bypass y descendientes; (3) recibo independiente/raíces de confianza; (4) cuarentena, incidentes, interrupciones, duplicados y recursos solapados; (5) baseline/candidato/diff/consumidor IABV; (6) compatibilidad con decisión C y restricciones actuales. Emite `PASS`, `PASS_WITH_REPAIRS` o `FAIL` solo sobre coherencia documental.

No consultes fuentes públicas ni afirmes `CLAUDE_REPORTED_PUBLIC_SOURCE` como verificado sin leerlas directamente; no ejecutes comandos, pruebas, builds, runtime ni turnos Codex; no inspecciones checkout, `data/`, SQLite, secretos, credenciales o configuración local; no hagas consultas de cuota ni gastos; no modifiques o publiques repositorios. `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE_NOT_READY`. Un `PASS` documental no libera ningún bloqueo.
## 2. Documento propuesto para revisión — IABV → CODEX — Contract design delta, no runtime

### 2.1 Identidad, propósito y límite de autoridad

Este documento propone un contrato que tendría que existir **antes** de estudiar una futura vía gobernada de desarrollo con Codex. No constituye implementación, autorización, aceptación semántica ni evidencia de que el puente exista.

Flujo objetivo:

`objetivo/tarea IABV → prompt exacto aprobado por propietario → identificación/autorización del origen → materialización autorizada del candidato → preflight por separado → lanzamiento por broker gobernado → recibo independiente y artefactos inmutables → verificación IABV → decisión explícita del propietario → promoción separada con autorización propia, si procede`.

Una consulta de texto, thread/turn ID, mensaje final de éxito, código de salida cero o registro persistido no prueba por sí solo que Codex editara el candidato correcto, que se ejecutara confinado ni que IABV aceptara el resultado. Persistencia documental no equivale a aprendizaje causal; una recomendación no equivale a despacho; una respuesta del agente no equivale a un diff verificado.

**Decisión vigente:** `C — keep Codex launch blocked while static design continues`. No selecciona otro ejecutor ni una arquitectura nueva. No autoriza preflight local, `codex exec`, App Server, turno de modelo, canaria, pruebas, builds, runtime, acceso a M0A, autenticación, instalación/actualización, gasto, commit, push, merge o promoción.

### 2.2 Base de evidencia y clasificación de afirmaciones

Este contrato separa la procedencia de la evidencia; las categorías no deben mezclarse:

- `PUBLIC_SOURCE`: comprobado directamente por quien emite la afirmación contra una fuente pública identificada.
- `OWNER_REPORTED`: informado por el propietario; no es observación independiente del coordinador.
- `CLAUDE_REPORTED_PUBLIC_SOURCE`: afirmación de fuente pública verificada en el dictamen adversarial previo de Claude, pero no reabierta por el coordinador en esta revisión documental.
- `PROPOSED`: control o diseño futuro no implementado.
- `UNVERIFIED` / `UNRESOLVED`: no hay evidencia suficiente, falta el mecanismo o la identidad/fuente es ambigua.
- `NOT_RUN` / `NOT_AUTHORIZED`: no ejecutado o no autorizado; no equivalen a un resultado negativo de prueba.
- `AGENT_REPORTED`: dato producido o afirmado por Codex/otro agente, no evidencia independiente de sí mismo.

#### Matriz de afirmaciones con procedencia actual

| Afirmación | Estado en esta revisión | Límite |
|---|---|---|---|
| Codex `rust-v0.120.0` `exec` fija `approval_policy = Never` | `CLAUDE_REPORTED_PUBLIC_SOURCE` (código citado: `codex-rs/exec/src/lib.rs`, línea 375) | No demuestra política local efectiva ni seguridad del lanzamiento. |
| Un override `sandbox_mode` conduce a sintaxis legacy en el camino analizado | `CLAUDE_REPORTED_PUBLIC_SOURCE` (`resolve_permission_config_syntax`) | No demuestra la configuración efectiva en otro binario o versión. |
| Una regla `execpolicy Allow` puede activar `bypass_sandbox` y `SandboxType::None` en el camino analizado | `CLAUDE_REPORTED_PUBLIC_SOURCE` (archivos/caminos citados por Claude) | No afirma que una regla así esté presente localmente. |
| `CODEX_HOME` influye en la resolución de autenticación/keyring | `CLAUDE_REPORTED_PUBLIC_SOURCE` (archivos citados por Claude) | No se debe leer, copiar ni divulgar el material de autenticación. |
| Codex `rust-v0.120.0` no expone la opción `ignore-rules` en la CLI `exec` examinada | `CLAUDE_REPORTED_PUBLIC_SOURCE` (búsqueda de CLI reportada por Claude) | Ausencia en esa fuente/version no prueba ausencia en otras versiones. |
| Las reglas/configuración pueden venir de múltiples capas | `UNVERIFIED` en la revisión de Claude | lo informa la continuidad histórica previa; no se presenta como reabierto en esta revisión. |
| App Server local observado sin ruta completa de coding/diff | `OWNER_REPORTED / UNVERIFIED` | Fuente local no publicada; no inferir que todos los caminos Codex sean imposibles. |
| CLI local `0.120.0`, shim `codex.ps1`, configuración local `never`/`danger-full-access`/`elevated` y auxiliares de Windows | `OWNER_REPORTED` | No demuestran backend efectivo, modelo, autenticación, cuota, coste ni confinamiento. |
| Checkout local dirty, rutas y cantidades reportadas en diferentes momentos | `OWNER_REPORTED`, ligados solo a su ruta/fecha declaradas | No intercambiar ni fusionar identidades de worktrees; no inspeccionar `data/` ni SQLite. |
| Existencia de controles externos definidos en este contrato | `PROPOSED` | No hay implementación, preflight, prueba ni runtime autorizados. |

Como pista de procedencia, informes anteriores mencionaron la fuente pública `jhonf463r/Python` y una revisión histórica de `IABV_v1.5/AGENTS.md`, `IABV_v1.5/docs/history/CHAT-ARCH/README.md` y Entries 241–261. Esta nota no exige que el revisor consulte esos documentos, no afirma verificación actual y no sustituye worktrees locales dirty ni demuestra que su contenido se haya publicado. La puerta de gobernanza de acceso local reportada como `governance_blocked` no puede sortearse mediante este contrato ni mediante reintentos alternativos.

### 2.3 Autorización, identidad ejecutable, confianza, reloj y presupuesto

Toda ejecución futura requeriría una `CandidateExecutionAuthorization` final firmada por el propietario después de un preflight autorizado e independiente. La autorización previa del preflight no autoriza ejecución. La autorización final vincula el recibo de preflight, `path_manifest_digest`, `source_content_manifest_digest`, `candidate_content_manifest_digest`, `ContentReviewPackage` y la versión de cada canonicalizador/algoritmo. No puede firmarse hasta que esos digest estén aprobados de forma comprensible y estén disponibles todas las raíces de confianza necesarias. Actualmente no hay ninguna autorización de este tipo.

#### Aprobación del propietario y vista que se firma

Un `ContentReviewPackage` limitado debe incluir el contenido exacto o una representación íntegra y verificable de todo byte que el cliente pueda leer/transmitir, entradas declaradas de configuración/instrucción de `CODEX_HOME`, prompt, adjuntos, manifests, tipos/tamaños/rutas normalizadas, referencias de secreto clasificadas sin divulgar el secreto, resultado/limitaciones de escaneo y el conjunto de elementos excluidos. Una huella aislada no constituye revisión informada. Si el paquete excede los límites de revisión fijados de antemano, se rechaza o se excluyen explícitamente esos elementos del ámbito de lectura; nunca se firma un resumen que oculte material incluido.

La representación revisable usa canonicalización versionada y algoritmo de digest identificado (`canonicalization_id`, `hash_algorithm_id`). Las rutas se ordenan por claves canónicas, colisiones de mayúsculas/Unicode, separadores, nombres equivalentes, hardlinks y tipos ambiguos bloquean. El `OwnerReviewView` es una función determinista del objeto estructurado y sus bytes inmutables. El canal de aprobación muestra contenido y un `review_view_digest`; la firma cubre `{object_digest, review_view_digest, renderer_id/version, canonicalization_id, task_id, scope, expires_at}`. La interfaz de firma comprueba esos digests desde un canal independiente y no recibe una simple señal «aceptar» del renderer. Si no se puede probar que la vista presentada corresponde exactamente al objeto firmado, la aprobación no se emite.

#### Raíces de confianza, pinning inicial y raíz última

Ninguna clave se confía porque otra clave recién presentada lo afirme. El procedimiento de confianza se divide en dos funciones que no se pueden confundir:

1. **Custodia humana de raíces y épocas:** un procedimiento humano preexistente pinnea la clave del propietario, la clave de administración/recuperación y las raíces para verificar la autoridad de registro. Esta custodia sirve para fijar/rotar raíces, aprobar cambios de época y recuperación; **no** realiza un append por cada reserva ni hace de segundo almacén operativo después de un commit.
2. **Autoridad por operación antirregresión:** las reservas, revocaciones, cambios de locks y decisiones de gate requieren un registro durable, serializable y antirregresión por operación en un dominio de fallo/restore independiente del broker, cliente, launcher y ledger de proyección. Ese registro debe poder confirmar una operación por `request_id` y rechazar/reconocer restauraciones o divergencias. No se considera existente por ser llamado `AnchoredAppendCAS`.

| Raíz/autoridad | Autoridad limitada | Requisito de confianza/recuperación | Estado actual |
|---|---|---|---|
| Raíz humana del propietario | Firmar autorización/decisión exacta | Pinning inicial por canal humano preexistente, vista exacta y epoch/revocación | `PROPOSED / NOT_DEMONSTRATED` |
| Administración/recuperación | Aprobar cambio de raíces, época y recuperación | Firma humana distinta, quórum definido y no capacidad de borrar IDs/tombstones | `UNRESOLVED` |
| Raíz de confianza del registro | Validar la clave/identidad del registro antirregresión | Pinning fuera de banda anterior al uso; rotación/revocación con acta firmada y época monotónica | `UNRESOLVED` |
| `NonRollbackReservationLog` | Ordenar reserva, nonce-use, locks, revocación y gate | Capacidad preexistente, no restaurable junto con el broker/ledger, CAS/append atómico e idempotente por operación; si no puede identificarse/evidenciarse, el despacho está bloqueado | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia admisible |
| Custodia humana/offline de raíz última | Fijar/rotar raíz y aprobar época/recuperación | No pretende anclar cada operación ni compensar un log operativo rollbackable; ceremonia y quórum humanos explícitos | `UNRESOLVED` |
| `LedgerProjector` | Proyectar estados derivados del log autoritativo | No autoridad del nonce, reservas o locks; reconstruible, discrepancia bloquea | `PROPOSED / NOT_TESTED` |
| `SourceHandleBroker` | Entregar handles exactos por autorización | Identidad SO preexistente con ACL que ya deniegan raíces protegidas o proveedor de handles preexistente; no cambiar ACL de la fuente | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia admisible |
| `ReceiptDigestVerifier` | Enumerar el snapshot inmutable y recalcular digests | Identidad/root separada del parser y del signer; enumera bytes/entries desde almacén, no desde manifiesto declarado | `PROPOSED / NOT_DEMONSTRATED` |
| `SnapshotDiffVerifier` | Recalcular diff entre dos snapshots inmutables | Algoritmo byte-oriented versionado, no Git/hook/config del candidato | `PROPOSED / NOT_DEMONSTRATED` |
| `ReceiptSigningService` | Firmar objeto con attestations independientes | Clave fuera del parser/renderer/launcher; acepta solo raíces y attestations fijadas | `PROPOSED / NOT_DEMONSTRATED` |
| `TrustedOwnerReviewChannel` | Mostrar y firmar el objeto exacto | Renderiza desde bytes inmutables y recalcula digests por canal independiente; si no existe previamente, revisión/firma bloqueada | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia admisible |
| Autoridad de tiempo | Firmar hora, skew, vigencia y suspensión | Pinning, rotación/revocación, monotonía y conducta de suspensión definidos | `UNRESOLVED` |
| `ProcessTreeTerminator` | Terminar solo el grupo de procesos vinculado al intento | Principal/SO preexistente distinto del launcher, deadline y latencia medibles; si no existe, no hay despacho | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia admisible |
| `RevocationAuthority` | Firmar o verificar revocación humana y someterla al log autoritativo | Acto humano autenticado, raíz fijada, un solo camino de append; no autocertifica la parada | `PROPOSED / NOT_DEMONSTRATED` |

**Regla de bloqueo por raíz.** La custodia humana/offline no puede tratarse como una autoridad que confirma cada `AnchoredAppendCAS` en línea. Para tener antirregresión por operación se necesita una capacidad de almacenamiento/servicio preexistente con una garantía operativa de append/CAS no restaurable dentro de su dominio; la custodia humana fija la raíz de confianza y la recuperación, no sustituye esa propiedad. Si esa capacidad no se puede identificar a partir de evidencia admisible ya disponible sin instalación, autenticación, gasto o acceso local no autorizado, `RESERVATION_ATOMICITY = BLOCKED_UNDER_CURRENT_CONSTRAINTS`, `GOVERNANCE_DOMAIN_BLOCKED` y no hay despacho. No se autoriza buscarla mediante preflight.

El propio registro de raíces también necesita una época/registro de revocación protegido contra restauración; no se acepta que el mismo registro que perdió su integridad sea la autoridad exclusiva que certifique su recuperación. Si la raíz última o el quórum no pueden fijarse sin crear identidades/servicios/credenciales nuevos, la recuperación permanece bloqueada indefinidamente.

#### Autoridad por operación y autorizaciones de un solo uso

Cada clase de autorización —inventario, lectura de entradas del cliente para revisión (`ClientInputReviewAuthorization`), materialización, preflight, consulta de uso, ejecución, `PolicyObservabilityWaiver`, aceptación, reconciliación, liberación y promoción— requiere objeto propio, scope exacto y mecanismo antirreplay. Una `AuthorizationUseRecord` se vincula por `{authorization_type, authorization_id, nonce, task_id, attempt_id, resource_set_digest}`; la autoridad que ordena uso debe ser la misma autoridad append-only declarada para esa clase. No se presume que una sola llamada `ReserveCAS` cubra autorizaciones previas de inventario/materialización/preflight. Sin un registro/anti-replay preexistente y fijado que abarque cada tipo, ese paso queda `UNRESOLVED` y no se realiza.

El emisor/preparador crea y valida esquemas, pero no firma. La clave privada del propietario no está disponible al agente, broker, cliente ni código autónomo. Ciclos IABV (`AutonomousValidationCycle`, `action_ready` u otros) no pueden invocar firmantes privilegiados, `WitnessService`, `LaunchGate`, colector, aceptador, reconciliador ni liberador. La delegación solo recae en humanos autenticados y su mandato nombra un acto permitido, tarea, objeto, recursos, vigencia y revocabilidad; no se permite subdelegación. Firmar autorización no concede aceptar, reconciliar, disponer incidentes, liberar recursos o promover.

#### Campos obligatorios de `CandidateExecutionAuthorization`

- Identificadores y vínculos: `authorization_id`, `attempt_id`, `task_id`, `dispatch_nonce`, `reservation_request_id`, `source_inventory_authorization_digest`, `client_input_review_authorization_digest`, `path_manifest_digest`, `source_content_manifest_digest`, `candidate_content_manifest_digest`, `content_review_package_digest`, `client_input_manifest_digest`, `client_input_review_package_digest`, `preflight_receipt_digest`, `candidate_snapshot_id` y digest de esquema/canonicalización.
- Entrada del agente: `prompt_digest`, adjuntos/contexto aprobados, `client_read_scope`, `disclosure_scope`, `disclosure_upper_bound`, `disclosure_policy_digest`, `allowed_endpoint_set`, `client_config_manifest_digest`, `declared_policy_inputs_digest` y estado explícito de `effective_policy_fingerprint` (`OBSERVED_INDEPENDENTLY` o `UNKNOWN`).
- Identidad ejecutable: shim, intérprete, binario, loader, módulos, dependencias, perfiles, argumentos, configuración, reglas, entorno allowlisted y handles inmutables; el proceso observado y la clausura usada se atestiguan en el recibo. Cualquier parte de la cadena que no se pueda medir bloquea.
- Aislamiento y recursos: FS/handles, comandos, red, IPC, integraciones, procesos/descendientes, time/wall-clock, CPU/memoria/IO, salida, profundidad, archivos/bytes, colector, destino de publicación y cuenta/servicio; cada límite exigido debe ser efectivamente imponible.
- Tiempo/gobernanza: `issued_at`, `not_before`, `expires_at`, autoridad de tiempo y epoch, `max_clock_skew`, `max_gate_to_first_instruction`, `max_gate_to_resume_latency`, `max_lease_interval`, `max_stop_latency`, política de suspensión, estado de revocación, raíz de confianza y mandato firmado. Cada límite temporal debe contener un valor finito firmado; si falta el valor, la autorización es inválida.
- Gasto: `additional_spend_ceiling = 0` para este proyecto. No consultar cuota ni servicio potencialmente facturable para averiguarla. Sin evidencia preexistente admisible de coste/cupo, la ejecución permanece `BLOCKED`. No se crean planes, cuentas, autenticaciones o credenciales nuevas.
- Waiver: cualquier `PolicyObservabilityWaiver` debe ser firmado por el propietario antes de la autorización final y antes de reservar, y quedar incluido en ella. Un waiver posterior no rescata ningún intento. No puede dispensar aislamiento externo, autoridad, gasto ni gobernanza.

`effective_policy_fingerprint` solo puede usarse si un verificador independiente observa la política efectiva resuelta. El hash de archivos/configuración se llama `declared_policy_inputs_digest`; no debe confundirse con política efectiva. Si el resolvedor del producto es inaccesible o medirlo exige ejecutar código no autorizado, `effective_policy_fingerprint = UNKNOWN`. Solo una frontera externa demostrada que limite todos los efectos, junto con waiver firmado previamente, podría tratar esa incertidumbre como riesgo acotado; sin ambos, se bloquea.

#### Tiempo, revocación y carga del ejecutable

La autoridad de tiempo debe estar identificada, pinneada y firmar hora, skew y estado de suspensión; `trusted_time_source = UNKNOWN` bloquea. `max_clock_skew`, `max_lease_interval`, `max_gate_to_first_instruction` y `max_stop_latency` deben contener valores numéricos finitos, establecidos por una autorización de gobierno anterior al intento. El documento no inventa esos valores. Si uno no está definido, no puede emitirse autorización final ni despacharse.

**Política normativa de primera instrucción (opción A, no una alternativa pendiente):** la primera instrucción de user-code debe ocurrir dentro de la vigencia y deadline impuestos por un mecanismo del SO en el límite de reanudación/ejecución; una parada posterior no sustituye este requisito. El sistema debe impedir la reanudación/primera instrucción si la autorización, tiempo, lease o estado de revocación no siguen vigentes en la decisión física del SO. `GateResumeCAS` en el log no prueba por sí solo esa propiedad. Si la plataforma no impone esta barrera, `GATE_TO_FIRST_INSTRUCTION = BLOCKED_UNDER_CURRENT_CONSTRAINTS` y no hay despacho. Una revocación después de la primera instrucción exige además `ProcessTreeTerminator` independiente dentro de `max_stop_latency`; si no existe, tampoco se despacha.

Toda la clausura de carga previa conocida —shim, intérprete, binario, DLL/shared libraries, módulos, profiles y rutas de búsqueda— debe ser inmutable desde verificación hasta el final. El entorno de loader debe estar allowlisted. Las cargas dinámicas posteriores que no puedan observarse o restringirse a rutas selladas siguen `UNRESOLVED`; no se presume que el inventario previo de archivos sea completo. La identidad del proceso/bytes efectivamente cargados no se deriva de lo que reporte Codex.

La expiración de autorización, revocación, reserva, locks y gate se ordenan por el registro antirregresión de §2.8. La expiración/revocación en vuelo no puede quedarse en un estado textual sin actor de parada: la tabla de principales debe asignar la revocación al `RevocationAuthority` y la terminación al `ProcessTreeTerminator`. Si no están preexistentes y fijados, las capacidades se bloquean, no se sustituyen por el `ProcessLauncher`.

`GOVERNANCE = KEEP_BLOCKED`; todo lo anterior sigue `PROPOSED / NOT_TESTED / UNRESOLVED`.

### 2.4 Autorización independiente de preflight y puerta de gobernanza

Con la decisión C vigente: `LOCAL_PREFLIGHT = NOT_AUTHORIZED_BY_THIS_TASK`. Todo lo siguiente es diseño, no permiso para actuar.

Un futuro preflight requiere un `CandidatePreflightAuthorization` firmado por el propietario o un delegado con mandato específico solo para preflight. Debe identificar propósito, raíz/worktree exacto, directorios y operaciones permitidos, ventana/tiempo, límite de archivos/bytes y esquema de salida. No se acepta una autoridad genérica llamada «competente»: la identidad del firmante, el acto delegado y su raíz de confianza deben estar definidos antes del uso. La autorización no puede reutilizarse para materializar ni ejecutar.

El preflight usa una allowlist de lectura por defecto denegatoria. Se prohíbe abrir, leer, copiar, hashear, enumerar contenido, imprimir, serializar o transmitir `auth.json`, keyrings, tokens, credenciales, archivos de sesión, secretos, variables sensibles, memoria/IPC de autenticación u otros materiales equivalentes. Tampoco se deben leer archivos reales de autenticación como “prueba negativa”. Cualquier prueba futura empleará archivos señuelo sin secretos, con ACL/ubicación equivalentes, y la autoriza una fase aparte; no se ejecuta aquí.

La salida solo contiene estados, recuentos y huellas permitidas del conjunto allowlisted. No puede incluir el volcado de configuración completa, variables de entorno, rutas secretas ni contenido de archivos no autorizados. Si el análisis de reglas necesita una ruta que no está expresamente autorizada, el preflight termina `PREFLIGHT_BLOCKED`; no amplía el alcance por decisión del agente.

La puerta de gobernanza y procedencia del target es anterior e independiente. Si el conector/target, checkout, fuente, lectura o resolución de gobernanza siguen `UNRESOLVED`/`governance_blocked`, no se intenta otra ruta, conector, snapshot o worktree como sustituto. Este contrato no modifica, reintenta ni sortea esa puerta.

Cualquier discrepancia, ruta no permitida, ausencia de firma, salida con contenido extra o incertidumbre produce `PREFLIGHT_BLOCKED`. No usar `--sandbox workspace-write`, `--full-auto`, `execpolicy Allow` ni un `CODEX_HOME` alternativo como sustituto de la evidencia independiente.


### 2.5 Frontera de ejecución, principales, divulgación y recursos compartidos

La frontera necesaria debe estar fuera del agente y del cliente Codex, y debe limitar efectos aunque el sandbox de Codex se omita o `execpolicy Allow` solicite bypass. No se afirma que exista. Prompt, política interna del cliente, Job Object aislado del resto del proceso o recibo del propio agente no acreditan por sí solos el límite.

#### Principales y separación de funciones propuesta

| Principal/capacidad | Puede hacer | No puede hacer |
|---|---|---|
| `OwnerApprovalService` / propietario humano | Firmar el objeto exacto desde un canal de revisión confiable | Lanzar, colectar, aceptar, reconciliar o liberar su propio intento |
| `SourceInventoryAuthority` humana | Autorizar scope de inventario antes de que enumere un principal técnico | Autorizar lectura de bytes por el solo hecho de aprobar raíces |
| `SourceHandleBroker` | Entregar handles exactos dentro de un scope y mediante una capacidad SO preexistente | Cambiar ACL, atravesar raíces protegidas, ampliar el scope o leer por privilegios generales |
| `SourceEnumerator` | Enumerar únicamente los objetos que el handle/ACL ya permite dentro de la autorización de inventario | Leer contenido, enumerar raíces protegidas o interpretar archivos |
| `SourceContentReader` / `SourceMaterializer` | Copiar bytes de handles exactos autorizados a un snapshot de candidato | Leer una ruta no listada, ampliar el scope, acceder a credenciales o alterar la fuente |
| `ClientInputReviewAuthorization` / lector de inputs | Leer únicamente instrucciones/configuración no secreta y exacta aprobada para revisión de divulgación | Leer `auth.json`, keyrings, tokens, sesiones, variables de autenticación u otros secretos |
| `ContentReviewBuilder` | Construir una vista desde bytes ya autorizados y copiados a un snapshot inmutable | Abrir `CODEX_HOME` o el entorno por sí mismo, leer credenciales, red, custodiar claves o aceptar |
| `PreflightInspector` | Inspeccionar solo el candidato y client-input snapshot aprobado bajo autorización propia | Lanzar Codex/código, ampliar lectura o resolver política ejecutando el cliente |
| `AuthorizationVerifier` | Verificar firma, mandato, estado, versión, clase y scope | Firmar, revocar, lanzar, aceptar, reconciliar o cambiar raíces |
| `NonRollbackReservationLog` | Ser la autoridad preexistente de append/CAS para reserva, nonce-use, revocación, locks y gate | Compartir dominio de restauración con broker/ledger, aceptar escrituras del agente o confiar en una proyección |
| `LedgerProjector` | Proyectar estados desde eventos comprometidos | Autorizar nonce/locks, crear hechos privilegiados o resolver rollback |
| `ProcessLauncher` | Crear el proceso exacto en estado no ejecutable/suspendido solo tras reserva confirmada | Firmar, decidir gate, certificar no ejecución, terminar su propio árbol, colectar o aceptar |
| `KernelResumeDeadlineEnforcer` | Impedir que se reanude/ejecute la primera instrucción fuera del deadline autorizado, si el SO lo soporta | Sustituir un límite del SO por checks de user-space o ser presupuesto teórico |
| `RevocationAuthority` humana | Firmar una revocación en el formato/scope del contrato | Certificar la parada o eliminar el historial |
| `ProcessTreeTerminator` | Terminar solo el árbol/proceso vinculado al intento y dentro del límite firmado | Lanzar, certificar por sí solo que no ejecutó, recolectar o liberar locks |
| `OSExecutionObserver` | Registrar creación, reanudación, primera instrucción si es observable, árbol, salida y terminación con secuencia/cobertura comprobables | Lanzar, terminar, revocar, aceptar o alterar sus eventos |
| `LeaseRenewer` / `SuspendResumeObserver` | Renovar solo si log, autoridad temporal y ancla están saludables; detectar suspensión | Renovar ante pérdida de fuente o autorizar |
| `NetworkEgressEnforcer` | Bloquear destinos/flows no incluidos en la política aplicada a cliente e hijos | Ser observador pasivo o ampliar destinos por instrucción del agente |
| `DisclosureObserver` | Registrar metadata de tráfico/eventos por canal y declarar huecos de observación | Afirmar que observó payload cifrado que no pudo inspeccionar |
| `ReceiptDigestVerifier` | Enumerar independientemente todo el snapshot sellado y recalcular la raíz/digests desde bytes | Confiar en la lista del parser, ejecutar Git/hooks, red o custodiar la clave de firma |
| `SnapshotDiffVerifier` | Calcular el diff entre dos snapshots inmutables según algoritmo byte-oriented versionado | Usar configuración/hook del repositorio candidato o aceptar un diff declarado sin recalcular |
| `UntrustedManifestParser` | Parsear estructuras declaradas como entrada hostil, sin privilegios ni claves | Definir completitud del snapshot o determinar por sí solo el digest firmado |
| `ReceiptSigningService` | Firmar solo tras validar attestations independientes, enumeración completa y diff verificado | Parsear el candidato, inventar entradas o sellar ciegamente la salida del parser |
| `TrustedOwnerReviewChannel` | Renderizar desde bytes inmutables en un canal confiable y firmar el mismo objeto/vista que muestra | Recibir solo un botón/booleano del renderer del host o firmar sin mostrar el objeto |
| `IABVArtifactVerifier` | Verificar procedencia/integridad documental del snapshot, diff y recibo | Ejecutar candidato, inferir corrección funcional, aceptar, reconciliar o promover |
| Aceptador humano | Aceptar/rechazar el objeto exacto en un canal preexistente | Ser el autorizador del mismo intento o el reconciliador de un incidente posterior que afecte su decisión |
| `IncidentReconciler` humano | Emitir una disposición delimitada sobre un incidente | Borrar incidentes, lanzar o liberar por sí solo |
| `ResourceReleaseAuthority` humana | Firmar liberación para recursos específicos con evidencia de cierre | Autocertificar limpieza, liberar por aceptación automática o eliminar IDs/locks sin registro |

Ninguna fila demuestra existencia. En especial, `NonRollbackReservationLog`, `KernelResumeDeadlineEnforcer`, `ProcessTreeTerminator`, `RevocationAuthority`, `SourceHandleBroker` con aislamiento efectivo y `TrustedOwnerReviewChannel` permanecen `UNRESOLVED` o `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia admisible de capacidad preexistente. No se puede resolver un rol ausente asignándolo nominalmente al mismo proceso.

#### Incompatibilidades entre actos y mínimo humano

| Actos del mismo intento | Regla |
|---|---|
| Autorizar ejecución ↔ aceptar/rechazar | Prohibido |
| Autorizar ↔ reconciliar incidente/liberar recurso | Prohibido |
| Lanzar ↔ observar/terminar/firmar prueba `CLOSED_NO_EFFECT` | Prohibido |
| Parsear bytes hostiles ↔ custodiar clave/firmar recibo | Prohibido |
| Renderer del host ↔ custodiar la clave o decidir contenido firmado | Prohibido |
| Aceptar/rechazar ↔ reconciliar un incidente posterior sobre esa decisión | Prohibido |
| Reconciliar incidente ↔ firmar liberación del mismo incidente | Prohibido |
| Firmante de la raíz de administración ↔ aprobador único de su propia rotación/recuperación | Prohibido |

Para la ruta normal se requieren al menos dos humanos autenticados y preexistentes: H1 firma la autorización; H2, distinto de H1 y sin rol de lanzamiento/colecta, puede aceptar/rechazar y firmar liberación normal solo si no hay incidente. Si aparece un incidente después de la decisión de H2, la reconciliación requiere H3 distinto de H1 y H2; la liberación posterior requiere una autoridad humana distinta de H1, H2, H3, launcher y colector. El pinning/rotación de la raíz y la recuperación del dominio requieren al menos dos personas humanas distintas bajo raíces fijadas. Estos mínimos son requisitos de diseño, no una afirmación de que existan suficientes personas.

Con un solo propietario y sin esas personas/canales preexistentes, no hay aceptación, reconciliación, liberación, pinning o recuperación válidos donde se exige separación. Se conserva `PENDING_OWNER`, `GOVERNANCE_DOMAIN_BLOCKED` y los locks; no se inventa una delegación de IA ni se relajan incompatibilidades.

#### Cliente Codex y descendientes

El cliente y sus descendientes deben tener dominios separados de filesystem, identidad, entorno, IPC, red y credenciales. Los descendientes solo dispondrían de (1) snapshot candidato aprobado de solo lectura, (2) espacio temporal limitado, (3) entorno allowlisted y vacío salvo variables autorizadas, y (4) canales stdout/stderr/eventos capturados por la frontera. No deben recibir HOME del propietario, `CODEX_HOME`, keyring, `auth.json`, archivos de sesión, IPC/sockets del cliente, portapapeles, MCP/plugins, credenciales ni publicación. La lista de lectura de los hijos es una lista positiva aplicada por el SO, no una promesa del prompt.

El cliente tiene que autenticarse al servicio. Un futuro diseño solo puede afirmar que las credenciales no entran al contexto del modelo ni a los hijos si una mediación de transporte preexistente usa el material de autenticación en un canal separado, con destino acotado y sin exponer bytes a la carga del modelo. El material de autenticación no se abre ni se copia en esta fase. Si el cliente necesita leer credenciales generales y no existe ese canal separado, `AUTH_CREDENTIAL_ISOLATION = BLOCKED_UNDER_CURRENT_CONSTRAINTS`; no se despacha.

#### Cota superior de divulgación por canal

`disclosure_upper_bound` no es una sola lista de archivos. Es el producto de (a) conjunto de fuentes byte/metadata legibles, (b) transformaciones permitidas, (c) canal de transmisión, (d) endpoint/protocolo y (e) límite máximo por canal. Debe distinguir al menos:

1. `model_payload`: prompt/contexto/adjuntos aprobados, bytes del snapshot candidato, entradas de instrucciones/configuración exactas aprobadas, variables no secretas permitidas y stdout/stderr/resultados/errores/eventos de descendientes que el cliente pueda devolver al modelo.
2. `transport_auth`: credencial/cookie/token/cabecera necesaria para autenticarse, tratada como clase opaca separada con ruta de custodia/uso, endpoint exacto y límite de transmisión; nunca se materializa en el ContentReviewPackage, payload de modelo ni entorno de hijos.
3. `protocol_metadata`: destino, protocolo, puertos, identificadores, tamaños, tiempos y datos de transporte observables. El contenido cifrado que no se observa no se declara observado.
4. `egress_from_children`: todo byte que los hijos puedan emitir o devolver por stdout/stderr/eventos, y cualquier conexión que la frontera permita; sin filesystem/env de lista blanca y egress enforcement, la cota no es completa.

Cada input no secreto que el cliente pueda leer debe estar listado por ruta/nombre exacto, tipo, tamaño, digest y contenido revisable en un `ContentReviewPackage` autorizado. El valor de una variable de entorno no se presume seguro por el nombre; los valores que el cliente lea deben estar aprobados como contenido o excluidos. Los secretos no se pueden ocultar dentro de una ruta permitida: si no pueden separarse sin leerlos, se bloquea.

El campo de divulgación incluye fuentes, canal, endpoint y tamaños máximos; no exige copiar secretos en un recibo. Un `disclosure_observed = UNKNOWN` por TLS solo es admisible si un aplicador de egreso preexistente y fijado impide destinos alternos y la cota de todas las fuentes/canales está completa, incluida la clase de autenticación separada, y un principal independiente firma la atestación. Sin esas pruebas, `UNKNOWN` significa `BLOCKED`.

`Allow`/bypass no puede ampliar efectos. Si no es demostrable la separación por SO entre cliente, credenciales, filesystem y descendientes, o si el endpoint no puede aplicarse externamente, `BRIDGE_NOT_READY`; no se intenta compensarlo con reglas declarativas ni con una firma de recibo.

### 2.6 Identificación del origen, inventario autorizado, manifiestos y materialización del candidato

`SOURCE_IDENTIFIED` solo declara identidad y no concede permiso para listar, leer, hashear, copiar o atravesar el origen. Debe identificar con exactitud la fuente/checkout/worktree, baseline, fecha de observación y autoridad de procedencia. Un commit Git no representa por sí solo un worktree dirty, archivos sin seguimiento, generados o ignorados.

#### Orden correcto de inventario y aprobación

El orden es obligatorio y sustituye cualquier frase anterior que parezca exigir aprobar un `path_manifest` derivado antes de poder enumerarlo:

1. **`SourceInventoryAuthorization` previa:** el propietario firma un scope de inventario que fija raíces concretas, profundidad máxima, clases de rutas/objetos, presupuesto de entradas/bytes y exclusiones conocidas. Esta autorización da permiso limitado al principal de inventario para enumerar solo metadatos permitidos dentro del scope; no autoriza lectura de bytes. Usa su propio `AuthorizationUseRecord`.
2. **Inventario acotado:** `SourceEnumerator` enumera solo dentro de handles/ACL preexistentes que ya impiden el acceso a raíces protegidas; no hace recorrido recursivo de raíz amplia para después filtrar. Produce una lista de rutas/types/metadata, con cobertura y límites. Si la fuente no puede enumerarse sin tocar rutas fuera de scope, termina `ATTEMPT_BLOCKED`.
3. **`path_manifest` aprobado:** a partir de ese inventario, el propietario revisa y firma un `path_manifest` canónico positivo: rutas relativas exactas, tipo, modo/metadata admitidos, reglas para enlaces y límites. También puede proporcionar una lista manual exacta sin inventario; en ese caso no se recorre fuente para descubrir archivos.
4. **Autorización de materialización:** solo después del `path_manifest` aprobado se emite `MaterializationAuthorization` que autoriza lectura de bytes de esos handles/rutas exactos y nada más, con un `AuthorizationUseRecord` propio.
5. **Copia y `content_manifest`:** el materializador copia bytes desde handles autorizados a un snapshot aislado, calcula hashes del stream de lectura y del stream escrito y crea `source_content_manifest` y `candidate_content_manifest`. Una mutación, entrada extra, enlace, tipo no soportado, digest distinto o inventario incompleto bloquea.
6. **Revisión del contenido real:** el propietario revisa el contenido íntegro incluido, límites y exclusiones a través de un `TrustedOwnerReviewChannel` que derive la vista directamente del snapshot inmutable. Solo tras firmar los bytes/manifiestos exactos puede pasar a `CONTENT_MANIFEST_APPROVED`.
7. **Inputs de cliente:** cualquier entrada `CODEX_HOME` o variable no secreta que Codex vaya a leer requiere una autorización separada `ClientInputReviewAuthorization`, con lista exacta de rutas/nombres de variables y valores, propósito de divulgación, límite y salida. Se copia/revisa solo el contenido declarado no secreto en un snapshot de inputs. El builder no abre esas rutas por su propia autoridad. `auth.json`, keyrings, tokens, cookies, credenciales, archivos de sesión y material equivalente quedan expresamente fuera de la allowlist; no se enumeran, abren, leen, copian, hashean ni incluyen en el paquete.
8. **Preflight:** solo después de aprobar contenido fuente/candidato y los inputs de cliente que la herramienta realmente leería se puede solicitar, de forma independiente, un preflight autorizado. La decisión C vigente no lo autoriza ahora.

#### Manifiestos distintos

- `path_manifest`: paths exactos, canonicalización versionada, tipo/metadata y reglas de inclusión/exclusión; no pretende identificar bytes.
- `source_content_manifest`: digest de cada byte permitido leído desde los handles del origen, ligado a la copia y a la identidad del baseline.
- `candidate_content_manifest`: digest de cada byte/type de la raíz candidata y snapshot final.
- `client_input_manifest`: lista exacta, digest y contenido íntegro revisable de instrucciones/configuración no secreta/variables de entorno que el cliente puede leer.
- `ContentReviewPackage`: vista completa de los bytes que pueden entrar al cliente/payload de modelo, clasificadores/escaneo limitado y límites; no puede ocultar contenido incluido tras un digest.

Un digest no se retrotrae a una aprobación de ruta. La revisión humana debe cubrir el contenido real, no solo un número. El escaneo de secretos es una señal limitada, no prueba ausencia de secretos. Si el contenido supera el límite de revisión, no puede ser inspeccionado por el canal confiable, o contiene datos que no se autoriza enviar, se excluye del `client_read_scope` y la frontera debe hacer imposible que el cliente lo lea; de lo contrario, se bloquea.

#### Handles de SO y prohibición de modificar la fuente

`SourceHandleBroker` solo es admisible si existe una capacidad de SO preexistente con una de estas propiedades: (a) identidad de lectura restringida cuyas ACL ya deniegan las raíces protegidas y permiten las rutas aprobadas, o (b) proveedor de handles/capabilities preexistente que entrega handles de rutas exactas sin facultad de recorrer otras raíces. La propuesta no crea usuarios, identidades, servicios, ACL ni permisos. La fuente no se limpia/restaura/sobrescribe y sus ACL no se cambian.

Una allowlist en el mismo proceso/identidad con acceso general al host no equivale a aislamiento. Si el mismo principal puede leer `data/`, SQLite, Packages B–E, `relay-staging\\IABV_v1.5\\data`, M0A u otra fuente protegida y no hay capacidad preexistente del SO que lo impida, `SOURCE_READ_BOUNDARY = BLOCKED_UNDER_CURRENT_CONSTRAINTS`. No se inspecciona para averiguarlo ni se busca una ruta alternativa.

No se siguen enlaces simbólicos, junctions/reparse points, hardlinks, montajes o streams alternativos; no se admiten sockets, objetos especiales, colisiones canónicas, nombres ambiguos, mutación concurrente o metadatos no soportados. La enumeración y la copia tienen límites externos de entradas, profundidad, bytes, tamaño de ruta y tiempo. Si la API de handles no permite comprobar todas las entradas del scope sin cruzar roots prohibidos, el paso queda bloqueado.

Secuencia de estados: `SOURCE_IDENTIFIED → SOURCE_INVENTORY_AUTHORIZED → PATH_MANIFEST_APPROVED → MATERIALIZATION_AUTHORIZED → CANDIDATE_MATERIALIZED → CONTENT_MANIFEST_APPROVED → CLIENT_INPUT_REVIEW_AUTHORIZED → CLIENT_INPUT_MANIFEST_APPROVED → PREFLIGHT_AUTHORIZED` si el cliente necesita inputs. Si no hay inputs de cliente, esa lista vacía se firma y se puede pasar directamente de `CONTENT_MANIFEST_APPROVED` a `PREFLIGHT_AUTHORIZED`. La autorización de inputs tiene uso/receipt propios y no autoriza inventario/materialización del candidato. Ninguna lectura se autoriza en esta fase.

**No sustitución entre autorizaciones con scope solapado:** `SourceInventoryAuthorization`, `ClientInputReviewAuthorization`, `MaterializationAuthorization`, `PreflightAuthorization`, `CandidateExecutionAuthorization`, waiver, aceptación, reconciliación, liberación y promoción son clases distintas. La igualdad, intersección o relación de subconjunto entre `resource_set_digest` no transfiere autoridad ni `AuthorizationUseRecord`. El orden de §2.6 se evalúa por clase, ID, intento y evento; por ejemplo, una `MaterializationAuthorization` no puede sustituir `SourceInventoryAuthorization` previa cuando la secuencia requiere inventario. Si el paso predecesor que aplique falta, el intento es `ATTEMPT_BLOCKED` antes de cualquier lectura/efecto.

### 2.7 Recibo independiente, verificación de bytes, diff, colector y vista de propietario

`CandidateExecutionReceipt` solo podría ser independiente si las afirmaciones críticas se recalculan desde fuentes independientes, no desde lo que declara Codex, un parser, el launcher, el enumerador de manifiestos o el colector. La firma y todas las atestaciones siguen `PROPOSED / NOT_DEMONSTRATED`.

#### Cadena de verificación y raíz de confianza

1. `ImmutableSnapshotStore` conserva baseline, candidato y snapshot final inmutables en un namespace cerrado, content-addressed y con identidad/retención fijadas. La raíz se bloquea contra escrituras antes de verificar. Entradas no soportadas (symlinks, reparse points, hardlinks ambiguos, alternate data streams/ADS, streams no enumerables, mounts, entradas ocultas que la API no enumera) hacen `ARTIFACT_UNVERIFIED`.
2. `SnapshotInventoryVerifier` enumera independientemente el contenido real del namespace sellado, no consume la lista de paths producida por el parser como autoridad de completitud. Debe enumerar todos los objetos/streams visibles por la API, fijar `entry_count`, tipos, tamaños y total de bytes, calcular una raíz canónica y compararla con `path_manifest` y `candidate_content_manifest` aprobados. Si la API no puede probar que enumera todo el namespace, no hay completitud documental.
3. `ReceiptDigestVerifier` recalcula hashes de bytes/streams usando una primitiva fija y versionada sobre el inventario independiente; no copia digests del parser. Compara su raíz y recuentos con los manifiestos aprobados y los objetos inmutables.
4. `UntrustedManifestParser` procesa estructuras declaradas como entrada hostil sin privilegios ni claves. Puede interpretar un manifiesto, pero no decide qué objetos existen ni su completitud.
5. `SnapshotDiffVerifier` recalcula por sí mismo el diff entre baseline y candidato inmutables mediante algoritmo byte-oriented y schema/version fijos. No usa Git, configuración de repositorio, hooks, filtros, scripts, plugin, atributos o config del candidato. El digest de un diff que solo proporciona el parser/colector no es autoridad; se compara con el cálculo independiente.
6. `OSExecutionObserver`, `NetworkEgressEnforcer`/`DisclosureObserver`, el materializador y el canal de aprobación emiten atestaciones independientes dentro de sus límites declarados. El recibo marca `AGENT_REPORTED` los thread/turn IDs, stdout/stderr, mensaje final y eventos originados solo por el cliente.
7. `ReceiptSigningService` valida esquema fijo y firma solo después de verificar cobertura completa del snapshot, digests recalculados, diff independiente, estado del log antirregresión, identidad del proceso, prueba de terminación, cota/divulgación e incidentes. No interpreta bytes de candidato, no usa la enumeración declarada por el parser como prueba y no custodia parser/renderer/launcher.
8. Si cualquiera de las pruebas de enumeración, raíz, diff o terminación depende de una afirmación no corroborada, la salida es `ARTIFACT_UNVERIFIED` o `ATTEMPT_UNKNOWN`, no `ARTIFACT_VERIFIED`.

#### Campos obligatorios del recibo

El recibo contiene IDs de tarea/operación/intento/nonce; todas las autorizaciones y `AuthorizationUseRecord`; evento y confirmación del `NonRollbackReservationLog`, época/cabeza/request IDs, proyección del ledger; autorización, gate, revocación, reanudación y primera instrucción observadas; identidades del ejecutable/loader/dependencias/proceso; identidad/cobertura del supervisor; digest de `path_manifest`, `source_content_manifest`, `candidate_content_manifest`, `client_input_manifest`, `ContentReviewPackage`, baseline, snapshot y diff; inventario independiente y conteos de objetos/streams/bytes; algoritmo/versiones; attestations de lease/reloj/suspensión; stdout/stderr/resultados del agente marcados `AGENT_REPORTED`; `disclosure_scope`, cota por canal, endpoints, límites por canal y `disclosure_observed` con causa exacta si `UNKNOWN`; clase de autenticación separada sin registrar secreto; estado del scanner y límites; incidentes, locks, reconciliación y `ResourceReleaseRecord`; identidad del verificador/consumidor. No registra material secreto ni copia credenciales.

#### `CLOSED_NO_EFFECT` y observación sin huecos

`CLOSED_NO_EFFECT` exige cobertura de observación independiente desde antes de la primera posibilidad de creación hasta el cierre: secuencia autenticada/firmada de eventos, heartbeat/lease o contador que permite detectar pérdida/lag, identidad del observador, ventana de observación, origen del evento de SO y confirmación de que no hay intervalos sin cobertura. La ausencia de eventos no es prueba si el observador cayó o perdió eventos. Cada `DISPATCH_INTENT`/gate debe correlacionarse con una creación observada o con una afirmación explícita de no creación con cobertura íntegra.

- No se creó proceso: un `OSExecutionObserver` independiente prueba continuidad de la fuente de eventos durante toda la ventana y ausencia del evento de creación; si hay un hueco, `ATTEMPT_UNKNOWN`.
- Proceso creado suspendido: una fuente independiente debe demostrar que el hilo no fue reanudado/ninguna user-code inició y que el proceso/árbol fue terminado. CPU/E/S cero por sí solas no bastan.
- Si la cobertura no se puede demostrar, `CLOSED_NO_EFFECT` no es alcanzable y el lock se retiene.

`ProcessLauncher` nunca firma prueba de no ejecución. `ProcessTreeTerminator` puede detener procesos, pero no se autocertifica limpio; el observador y, cuando corresponda, el observador/aplicador de egreso aportan evidencia independiente. Si no existen, el estado queda `UNKNOWN`.

#### Colector hostil y canal de aprobación

El colector impone límites externos finitos para número de entradas, tamaño por archivo, bytes totales, profundidad, longitud de ruta, CPU, memoria, tiempo y tamaño de reporte. Un exceso produce captura incompleta, `ARTIFACT_UNVERIFIED`/`QUARANTINED`, nunca éxito parcial. El parser de contenido es proceso sin privilegios ni claves y no interpreta configuración ejecutable. El hash-verifier enumera bytes del snapshot; el diff-verifier calcula diff entre snapshots; el firmante solo valida estructura/attestations y firma.

`TrustedOwnerReviewChannel` debe derivar y renderizar por sí mismo una vista desde el paquete inmutable que va a firmarse, recalculando `object_digest` y `review_view_digest` en la ruta de firma. La pantalla/ dispositivo de aprobación muestra ese contenido, rutas/metadata, tipos, límites, exclusiones, digest y versión de canonicalización/renderer al humano; no acepta solo un botón o digest suministrado por el renderer del host. Los nombres/rutas son entradas hostiles: bidi/ANSI/no imprimibles/homoglifos se escapan y señalan. Si la ruta confiable de visualización/firma es la misma salida no verificada del host o no puede mostrarse el contenido dentro de límites, `OWNER_CONTENT_APPROVAL = BLOCKED_UNDER_CURRENT_CONSTRAINTS`.

#### Semántica estricta

`ARTIFACT_VERIFIED` significa solo integridad, procedencia y completitud documental de los snapshots/manifiestos/diff/recibo. No significa corrección funcional, ausencia de vulnerabilidades, que las pruebas pasaron ni que el consumidor ejecutó algo. La aceptación es una decisión de gobierno sobre el objeto exacto, no promoción ni test funcional. Tests dinámicos requieren otra autorización, frontera, divulgación, recibo y consumidor propios en un intento separado; esta versión no los autoriza.

### 2.8 Máquinas de estado, reserva antirregresión, gate, incidentes, locks y recuperación

Esta sección sustituye cualquier formulación anterior que trate la custodia humana offline como si pudiera confirmar cada reserva en línea. La única autoridad por operación admisible sería una capacidad preexistente `NonRollbackReservationLog`: almacenamiento append-only con CAS/serialización, idempotencia por request ID y protección de restauración en un dominio independiente del broker, cliente, launcher y ledger de proyección. El nombre `AnchoredAppendCAS` de v6 queda retirado como interfaz que pudiera sugerir una segunda escritura de anclaje; en v7 el único acto operativo es `NonRollbackReservationLog.AppendCAS` dentro de una sola autoridad. No existe un segundo commit «log → anchor».

Si no se puede identificar y respaldar con evidencia admisible que ese registro preexistente conserva cada nonce/lock/head ante crash, respuesta perdida y rollback, `RESERVATION_ATOMICITY = BLOCKED_UNDER_CURRENT_CONSTRAINTS`; no se emite despacho ni se simula la operación mediante dos almacenes. El registro de raíces/offline sirve para pinning, rotación de claves/época y recuperación humana; no escribe una segunda mitad de cada operación ni reemplaza la monotonía per-operation.

#### Dimensiones de estado separadas

| Dimensión | Estados permitidos y semántica |
|---|---|
| `authorization_status` (por objeto de autorización) | `AUTH_DRAFT`, `AUTHORIZED`, `CONSUMED`, `EXPIRED`, `REVOKED`, `AUTH_BLOCKED`. `CONSUMED` solo significa que el uso único fue comprometido; no que hubo spawn/ejecución. Un objeto consumido no vuelve a `AUTHORIZED`. |
| `authorization_use_status` (por clase e ID) | `USE_NOT_STARTED`, `USE_COMMITTED`, `USE_REJECTED_PRECOMMIT`, `USE_UNKNOWN`. Cada clase (`source_inventory`, `client_input_review`, `materialization`, `preflight`, `execution`, `usage-evidence`, `waiver`, `acceptance`, `reconciliation`, `release`, `promotion`) tiene nonce/request ID y registro propio. Uso comprometido no se recicla. |
| `reservation_status` | `NO_RESERVATION`, `RESERVATION_REQUEST_IN_FLIGHT` (solo cliente/local; no es lock), `RESERVATION_NOT_COMMITTED`, `RESERVATION_COMMIT_CONFIRMED`, `RESERVATION_COMMIT_UNKNOWN`. No existe `RESERVATION_ABORTED` con significado mixto. |
| `launch_status` | `PROCESS_NOT_CREATED`, `PROCESS_CREATED_SUSPENDED`, `GATE_PENDING`, `GATE_RESUME_COMMITTED`, `GATE_RESUME_DEADLINE_EXPIRED`, `RESUME_OBSERVED`, `FIRST_INSTRUCTION_DEADLINE_EXPIRED`, `FIRST_INSTRUCTION_OBSERVED`, `FIRST_INSTRUCTION_OBSERVED_LATE`, `RUNNING`, `TERMINAL_CONFIRMED`, `TERMINATED_NO_RESUME`, `TERMINATED_BEFORE_FIRST_INSTRUCTION`, `LAUNCH_UNKNOWN`. Los estados de expiración son eventos terminales/observacionales de la secuencia; por sí solos no prueban ausencia de ejecución ni autorizan liberar locks. |
| `attempt_status` | `ATTEMPT_DRAFT`, `SOURCE_IDENTIFIED`, `SOURCE_INVENTORY_AUTHORIZED`, `PATH_MANIFEST_APPROVED`, `MATERIALIZATION_AUTHORIZED`, `CANDIDATE_MATERIALIZED`, `CONTENT_MANIFEST_APPROVED`, `CLIENT_INPUT_REVIEW_AUTHORIZED`, `CLIENT_INPUT_MANIFEST_APPROVED`, `PREFLIGHT_AUTHORIZED`, `PREFLIGHT_PASSED`, `EXECUTION_AUTHORIZED`, `ATTEMPT_RESERVATION_PENDING`, `ATTEMPT_DISPATCH_INTENT`, `ATTEMPT_DISPATCHED`, `ATTEMPT_TERMINAL_CAPTURED`, `ATTEMPT_ARTIFACT_VERIFIED`, `PENDING_OWNER`, `ACCEPTED`, `REJECTED`, `ATTEMPT_BLOCKED`, `ATTEMPT_UNKNOWN`, `ATTEMPT_QUARANTINED`, `RECONCILIATION_REVIEW`, `RECONCILED`, `CLOSED_NO_EFFECT`. |
| `artifact_verification_status` | `NOT_EVALUATED`, `VERIFIED_INTEGRITY_PROVENANCE_COMPLETENESS`, `UNVERIFIED`, `QUARANTINED`. |
| `incident_status` | `CLEAR`, `OPEN`, `RESOLUTION_PROPOSED`, `RESOLVED`; los eventos originales/disposiciones son append-only. `OPEN` prevalece sobre cualquier permiso/estado histórico. |
| `resource_lock_status` (por recurso exacto) | `UNLOCKED`, `HELD_ACTIVE`, `HELD_UNKNOWN`, `HELD_INCIDENT`, `RELEASE_PENDING`, `RELEASED`. Solo eventos comprometidos del registro autoritativo crean/cambian locks. |
| `governance_domain_status` | `DOMAIN_ACTIVE`, `DOMAIN_BLOCKED_PENDING`, `GOVERNANCE_DOMAIN_BLOCKED`, `RECOVERY_REVIEW`, `DOMAIN_RECOVERED_NEW_EPOCH`; cada transición está en la tabla de recuperación inferior. |

#### Reserva, revocación y antirregresión

Una solicitud tiene `reservation_request_id = H(authorization_id, nonce, attempt_id, resource_set_digest, schema_version)`. Repetir la misma clave es solo una consulta idempotente de la misma operación; request ID diferente con el mismo nonce se rechaza.

1. Una comprobación de solo lectura de autorización, tiempo, revocación, raíz y locks no autoriza lanzamiento. Si la autoridad de tiempo, log, ancla o identidad de raíz está desconocida, no se inicia el intento.
2. `ReserveCAS` invoca al registro no rollback preexistente. En **una sola operación atómica, durable y linealizable dentro de ese dominio**, vuelve a comprobar firmas/scope, tiempo, revocaciones ya ordenadas, nonce-use, recursos por intersección, límites y dominio; si todo es válido, añade en el mismo commit el evento conjunto `EXECUTION_RESERVATION_AND_DISPATCH_INTENT_COMMITTED`, cambia `authorization_status` a `CONSUMED`, cambia el `authorization_use_status` de la misma clase/`authorization_id` a `USE_COMMITTED`, registra el `AuthorizationUseRecord`, bloquea los recursos exactos y avanza el head/epoch/sequence de la misma autoridad. Estos campos no se comprometen ni se publican como hechos separados. La reserva y `ATTEMPT_DISPATCH_INTENT` no son dos commits. No hay un segundo write posterior al ancla, ni un split commit `witness → anchor`.
3. La revocación la firma un humano autorizado y se ordena en el mismo registro. Si su evento gana antes de la reserva/gate, se deniega la transición. Si una reserva gana primero, el nonce queda consumido para siempre; la revocación posterior no reabre la autorización y se aplica antes del gate si aún no se ha reanudado, o activa parada en vuelo después.
4. `LedgerProjector` es solo una proyección reconstruible de eventos ya comprometidos. Nunca es fuente de verdad para nonce-use, reserva, gate o locks, y nunca es un fallback si `NonRollbackReservationLog` no responde. Las decisiones de autorización/gate/reserva y las consultas de reconciliación se apoyan exclusivamente en la autoridad operativa, con el mismo `reservation_request_id`, clase/ID exactos y head/epoch coherentes. Un estado de proyección que muestre `CONSUMED` pero no `USE_COMMITTED`, o viceversa, no autoriza una inferencia parcial ni un segundo uso: se trata como discrepancia/estado desconocido, se bloquea el intento y se retiene el lock.
5. Si el log no responde, se rechaza todo nuevo despacho en ese dominio mientras la autoridad esté inaccesible, el intento queda `RESERVATION_COMMIT_UNKNOWN`, el uso no resuelto queda `USE_UNKNOWN` y el dominio pasa a `DOMAIN_BLOCKED_PENDING`; no se escribe un “freeze” únicamente en el ledger ni se consulta el ledger como suplente. Solo una consulta read-only idempotente y linealizable a la misma autoridad puede resolver la misma request. Si esa lectura demuestra commit, el nonce permanece consumido y `authorization_use_status=USE_COMMITTED`; si demuestra ausencia de commit bajo una cabeza/época antirregresión coherente, puede producir `RESERVATION_NOT_COMMITTED`/`USE_REJECTED_PRECOMMIT`; si no puede determinarlo, permanece unknown. Una cabeza menor que otra ya aceptada, una época regresiva, o la desaparición de un evento de uso previamente confirmado es divergencia: ante sospecha/no confirmación permanece `DOMAIN_BLOCKED_PENDING`; si el rollback/divergencia se demuestra, pasa a `GOVERNANCE_DOMAIN_BLOCKED`. Ninguno de estos estados se libera por proyección.
6. Ningún nombre de API prueba que el registro tenga esas propiedades. Si no existe una capacidad preexistente con append/CAS atómico, idempotencia y anti-rollback dentro de su dominio, el resultado obligatorio es bloqueo; no se propone crear un servicio/identidad nuevo para satisfacer el contrato.

#### Gate: política estricta de primera instrucción

La política elegida es **A: el SO debe impedir la primera instrucción de user-code fuera de vigencia/deadline**. La alternativa de intentar detenerlo después no sustituye el deadline de primera instrucción. `GateResumeCAS` se registra en la misma autoridad y solo expresa la decisión ordenada; no prueba la acción física. La reanudación efectiva requiere `KernelResumeDeadlineEnforcer` preexistente que compare autorización, hora fresca, revocaciones/epoch, lease y deadline en el límite del SO; `max_gate_to_first_instruction` y `max_stop_latency` son valores finitos, firmados y aprobados por el propietario antes de emitir autorización. El contrato no elige números por él.

**Expiración tras el gate (transiciones obligatorias):** si `GATE_RESUME_COMMITTED` quedó en el registro y vence `max_gate_to_first_instruction` sin `RESUME_OBSERVED`, registrar `GATE_RESUME_DEADLINE_EXPIRED`; si hubo `RESUME_OBSERVED` pero no `FIRST_INSTRUCTION_OBSERVED` dentro del mismo límite, registrar `FIRST_INSTRUCTION_DEADLINE_EXPIRED`. Si el observador registra una primera instrucción después del deadline, el estado es `FIRST_INSTRUCTION_OBSERVED_LATE`, `incident_status=OPEN`, el intento pasa a `ATTEMPT_QUARANTINED` y el dominio se bloquea; no se permite reinterpretar el evento como puntual.

La expiración no basta para `CLOSED_NO_EFFECT`. Si `RESUME_OBSERVED` ocurre y el proceso termina antes de cualquier primera instrucción, registrar `TERMINATED_BEFORE_FIRST_INSTRUCTION` solo si el observer independiente demuestra cobertura continua y ausencia de user-code; si no, `LAUNCH_UNKNOWN`. Ese cierre exige además cobertura independiente continua de la ventana completa, evidencia de ausencia de cualquier primera instrucción, terminación confirmada del proceso/árbol cuando haya sido creado y `ResourceReleaseRecord` admitido. Si la cobertura es completa pero no se confirma terminación/liberación, se conserva `ATTEMPT_UNKNOWN`/cuarentena y el lock. Si falta cobertura o existe contradicción, `ATTEMPT_UNKNOWN` o `ATTEMPT_QUARANTINED` según la evidencia, `incident_status=OPEN` cuando haya incumplimiento demostrado, y no se libera ningún recurso. La transición `GATE_RESUME_COMMITTED → RESUME_OBSERVED → FIRST_INSTRUCTION_OBSERVED` no puede ser la única rama definida.

Si no hay ese enforcement de SO, `GATE_TO_FIRST_INSTRUCTION = BLOCKED_UNDER_CURRENT_CONSTRAINTS` y no hay spawn. Una comprobación en user-space, `sleep`, hash o CAS no lo reemplaza. Tras la primera instrucción, una revocación necesita `ProcessTreeTerminator` independiente y una parada confirmada dentro de `max_stop_latency`; si falta el actor o no puede imponer la parada, no se despacha.

Toda la clausura de carga estática se fija por handles/ACL ya admitidos e inmutables antes de la creación. Los loads dinámicos que no se pueden observar/restringir siguen `UNRESOLVED`. `ATTEMPT_DISPATCHED` solo significa que la fuente de SO independiente observó primera instrucción; el gate o un mensaje del agente no basta.

#### `CLOSED_NO_EFFECT`, reserva sin spawn y prueba de cobertura

Deben distinguirse estos resultados:

- **Rechazo antes de commit:** `reservation_status=RESERVATION_NOT_COMMITTED`, `authorization_use_status=USE_REJECTED_PRECOMMIT`, `launch_status=PROCESS_NOT_CREATED`. No se quemó el nonce de reserva ni se creó lock durable; puede iniciarse un intento nuevo solo con nueva autorización si la política lo permite.
- **Commit confirmado y luego revocación/cancelación antes de crear proceso:** `reservation_status=RESERVATION_COMMIT_CONFIRMED`, autorización `CONSUMED`, nonce quemado; `launch_status=PROCESS_NOT_CREATED`. `CLOSED_NO_EFFECT` requiere prueba de cobertura completa y registro `ResourceReleaseRecord` antes de liberar locks.
- **Proceso creado suspendido y nunca reanudado:** requiere evidencia de SO independiente de que el hilo no se reanudó ni ejecutó user-code, y prueba del cierre del handle/árbol.
- **Creación/estado observador ambiguo o cobertura incompleta:** `ATTEMPT_UNKNOWN`, lock retenido. Nunca se interpreta como `RESERVATION_NOT_COMMITTED`.

`OSExecutionObserver` debe ofrecer secuencia autenticada/firmada sin huecos, heartbeat o contador de cobertura durante toda la ventana desde antes de la posible creación hasta el cierre. Si muere, pierde eventos o no puede demostrar cobertura, no puede afirmar ausencia. El colector solo corrobora bytes; no prueba ausencia de ejecución. `ProcessLauncher` y `ProcessTreeTerminator` no firman su propia prueba de no ejecución. Sin cobertura independiente, `CLOSED_NO_EFFECT` es inalcanzable.

#### Máquina explícita de `attempt_status`

| Estado de origen | Transición permitida | Evento/condición; si falta, resultado |
|---|---|---|
| `ATTEMPT_DRAFT` | `SOURCE_IDENTIFIED` | Identidad documental exacta, sin leer/listar la fuente |
| `SOURCE_IDENTIFIED` | `SOURCE_INVENTORY_AUTHORIZED` o `PATH_MANIFEST_APPROVED` | Scope de inventario firmado antes de enumerar; o lista exacta suministrada por el propietario |
| `SOURCE_INVENTORY_AUTHORIZED` | `PATH_MANIFEST_APPROVED` / `ATTEMPT_BLOCKED` | Inventario limitado completo por API admitida; discrepancia o fuente protegida bloquea |
| `PATH_MANIFEST_APPROVED` | `MATERIALIZATION_AUTHORIZED` | Autorización de lectura/copia independiente, por archivos exactos |
| `MATERIALIZATION_AUTHORIZED` | `CANDIDATE_MATERIALIZED` / `ATTEMPT_BLOCKED` | Copia estable, manifiestos de bytes y digests; cualquier mutación/extra bloquea |
| `CANDIDATE_MATERIALIZED` | `CONTENT_MANIFEST_APPROVED` / `ATTEMPT_BLOCKED` | El humano revisa los bytes reales por canal confiable, no solo digest |
| `CONTENT_MANIFEST_APPROVED` | `CLIENT_INPUT_REVIEW_AUTHORIZED` o `PREFLIGHT_AUTHORIZED` | Si el cliente leerá inputs, autorización de revisión independiente; si no, la lista vacía queda firmada |
| `CLIENT_INPUT_REVIEW_AUTHORIZED` | `CLIENT_INPUT_MANIFEST_APPROVED` / `ATTEMPT_BLOCKED` | El lector autorizado procesa solo las rutas/variables no secretas; el resultado se copia a snapshot y se revisa por canal confiable |
| `CLIENT_INPUT_MANIFEST_APPROVED` | `PREFLIGHT_AUTHORIZED` / `ATTEMPT_BLOCKED` | El propietario aprobó inputs exactos y la lista completa; sin revisión segura, bloquea |
| `PREFLIGHT_AUTHORIZED` | `PREFLIGHT_PASSED` o `ATTEMPT_BLOCKED` | Preflight separado autorizado, vigente, con receipt y alcance íntegro |
| `PREFLIGHT_PASSED` | `EXECUTION_AUTHORIZED` | Autorización final del propietario vinculada a todos los digests de preflight/manifiestos y límites |
| `EXECUTION_AUTHORIZED` | `ATTEMPT_RESERVATION_PENDING` | Solicitud firmada creada; sin permiso de spawn |
| `ATTEMPT_RESERVATION_PENDING` | `ATTEMPT_DISPATCH_INTENT`, `ATTEMPT_BLOCKED` o `ATTEMPT_UNKNOWN` | `ATTEMPT_DISPATCH_INTENT` solo tras commit conjunto; rechazo autoritativo precommit bloquea; respuesta/estado ambiguo da unknown |
| `ATTEMPT_DISPATCH_INTENT` | `ATTEMPT_DISPATCHED`, `CLOSED_NO_EFFECT`, `ATTEMPT_UNKNOWN` o `ATTEMPT_QUARANTINED` | Dispatcher/observador del SO. Expiración antes de resume/primera instrucción no cierra el intento por sí sola: `CLOSED_NO_EFFECT` requiere cobertura independiente completa, no-user-code, terminación y `ResourceReleaseRecord`; sin cobertura/terminación, unknown + lock retenido; primera instrucción tardía, quarantine + incidente |
| `ATTEMPT_DISPATCHED` | `ATTEMPT_TERMINAL_CAPTURED`, `ATTEMPT_UNKNOWN` o `ATTEMPT_QUARANTINED` | Árbol terminado y observación fiable; gap, proceso superviviente o señal contradictoria bloquea |
| `ATTEMPT_TERMINAL_CAPTURED` | `ATTEMPT_ARTIFACT_VERIFIED` o `ATTEMPT_QUARANTINED` | Enumeración, hashes y diff recalculados independientemente; no vale salida del agente |
| `ATTEMPT_ARTIFACT_VERIFIED` | `PENDING_OWNER` o `ATTEMPT_QUARANTINED` | Receipt completo; discrepancia/evento tardío prevalece |
| `PENDING_OWNER` | `ACCEPTED` / `REJECTED` o permanecer pendiente | Humano independiente autorizado; no auto-decision |
| `ATTEMPT_UNKNOWN` / `ATTEMPT_QUARANTINED` | `RECONCILIATION_REVIEW` → `RECONCILED` o seguir bloqueado | Humano independiente y registro append-only; nunca retry/accept por sí solo |
| `ACCEPTED`, `REJECTED`, `CLOSED_NO_EFFECT` | Histórico terminal; puede abrirse un incidente overlay | Un evento tardío no reescribe el histórico ni libera locks |
| `ATTEMPT_BLOCKED` | No hay salida ordinaria/reutilización | Un nuevo intento exige nueva autorización e IDs; ningún estado se recicla |

`PREFLIGHT_INVALIDATED` es un evento que invalida el preflight; no es estado que se pueda reusar. El intento se bloquea o queda unknown según evidencia de efectos. Una nueva inspección requiere otro `attempt_id`, autorización propia y nueva evaluación de gobierno. No hay transición automática desde `ATTEMPT_BLOCKED`, `ATTEMPT_UNKNOWN` o `ATTEMPT_QUARANTINED` a un estado operativo.

#### Transiciones por dimensión y autorización

| Dimensión | Origen → destino | Evento/condición y escritor permitido |
|---|---|---|
| Autorización | `AUTH_DRAFT → AUTHORIZED` | Firmante humano/scope/raíces/mandato válidos; `AuthorizationVerifier` solo verifica |
| Autorización | `AUTHORIZED → CONSUMED` | Evento de uso comprometido en el registro antirregresión por esa clase |
| Autorización | `AUTHORIZED → EXPIRED/REVOKED/AUTH_BLOCKED` | Evento ordenado antes del consumo; no hay reactivación |
| `authorization_use_status` | `USE_NOT_STARTED → USE_COMMITTED` | Un único evento durable e idempotente para la clase/ID/nonce exactos |
| `authorization_use_status` | `USE_NOT_STARTED → USE_REJECTED_PRECOMMIT` | Registro autoritativo confirma que no se consumió/comprometió |
| `authorization_use_status` | Cualquier transición con respuesta perdida | `USE_UNKNOWN` hasta consulta read-only linealizable; nunca nuevo nonce por incertidumbre |
| Reserva | `NO_RESERVATION → RESERVATION_REQUEST_IN_FLIGHT` | Solo estado local; no da permiso ni crea lock |
| Reserva | `RESERVATION_REQUEST_IN_FLIGHT → RESERVATION_COMMIT_CONFIRMED/RESERVATION_NOT_COMMITTED/RESERVATION_COMMIT_UNKNOWN` | Solo evidencia del registro autoritativo; no el mensaje del agente |
| Lanzamiento | `PROCESS_NOT_CREATED → PROCESS_CREATED_SUSPENDED → GATE_PENDING` | Launcher autorizado tras commit confirmado; proceso creado no ejecutable y ligado al handle exacto |
| Lanzamiento | `GATE_PENDING → GATE_RESUME_COMMITTED` | Evento ordenado + deadline/enforcement SO disponible; no prueba resume físico |
| Lanzamiento | `GATE_RESUME_COMMITTED → GATE_RESUME_DEADLINE_EXPIRED` | Vence deadline sin `RESUME_OBSERVED`; observador debe fijar cobertura; no prueba no-ejecución por sí solo |
| Lanzamiento | `GATE_RESUME_DEADLINE_EXPIRED → TERMINATED_NO_RESUME` | Solo con evento independiente de terminación y ausencia de resume bajo cobertura continua; `CLOSED_NO_EFFECT` requiere además cierre/receipt/ResourceReleaseRecord |
| Lanzamiento | `RESUME_OBSERVED → TERMINATED_BEFORE_FIRST_INSTRUCTION` | Si el proceso/árbol termina antes de cualquier primera instrucción; solo se registra con evento independiente de terminación y cobertura continua que pruebe ausencia de user-code; si falta cobertura, `LAUNCH_UNKNOWN` y lock retenido |
| Lanzamiento | `GATE_RESUME_COMMITTED → RESUME_OBSERVED → FIRST_INSTRUCTION_OBSERVED` | Observación independiente dentro del deadline; si hay gap, `LAUNCH_UNKNOWN` |
| Lanzamiento | `RESUME_OBSERVED → FIRST_INSTRUCTION_DEADLINE_EXPIRED` | Vence el límite sin observar primera instrucción; no libera locks ni prueba cierre |
| Lanzamiento | `FIRST_INSTRUCTION_DEADLINE_EXPIRED → TERMINATED_BEFORE_FIRST_INSTRUCTION` | Terminación independiente tras expirar el deadline y antes de user-code; exige cobertura continua; sin cobertura o con contradicción, `LAUNCH_UNKNOWN`/cuarentena; no libera locks por sí sola |
| Lanzamiento | `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` | Si se observa luego una primera instrucción fuera de deadline: incumplimiento, `ATTEMPT_QUARANTINED`, incidente abierto y dominio bloqueado |
| Intento | `SOURCE_IDENTIFIED → SOURCE_INVENTORY_AUTHORIZED → PATH_MANIFEST_APPROVED → MATERIALIZATION_AUTHORIZED → CANDIDATE_MATERIALIZED → CONTENT_MANIFEST_APPROVED` | Autorizaciones separadas y aprobación tras inventario |
| Intento | `CONTENT_MANIFEST_APPROVED → CLIENT_INPUT_REVIEW_AUTHORIZED → CLIENT_INPUT_MANIFEST_APPROVED → PREFLIGHT_AUTHORIZED` | Si hay inputs: autorización y aprobación del contenido independientes; sin inputs, se firma una lista vacía |
| Intento | `PREFLIGHT_AUTHORIZED → PREFLIGHT_PASSED → EXECUTION_AUTHORIZED` | Preflight autorizado, vigente y receipt; propietario firma la autorización final después de preflight |
| Intento | `ATTEMPT_UNKNOWN/ATTEMPT_QUARANTINED → RECONCILIATION_REVIEW → RECONCILED` | Solo principal humano independiente, mandato acotado, evidencia completa e incidente dispuesto; no autoaceptación |
| Incidente | `CLEAR → OPEN → RESOLUTION_PROPOSED → RESOLVED` | Evento append-only; resolución firmada por persona distinta, sin borrar historia |
| Lock | `UNLOCKED → HELD_ACTIVE/HELD_UNKNOWN/HELD_INCIDENT → RELEASE_PENDING → RELEASED` | Registro autoritativo y `ResourceReleaseRecord`; no se libera por terminal, aceptación ni simple reconciliación |
| Dominio | `DOMAIN_ACTIVE → DOMAIN_BLOCKED_PENDING` | Timeout/respuesta perdida; solo consulta idempotente, sin nuevos despachos |
| Dominio | `DOMAIN_BLOCKED_PENDING → DOMAIN_ACTIVE` | Solo si el registro autoritativo demuestra head/epoch/locks concordantes y ausencia de rollback/incidentes; sin evidencia, no salir |
| Dominio | `DOMAIN_ACTIVE/DOMAIN_BLOCKED_PENDING → GOVERNANCE_DOMAIN_BLOCKED` | Divergencia, rollback, raíz/época dudosa o pérdida no reconciliable |
| Dominio | `GOVERNANCE_DOMAIN_BLOCKED → RECOVERY_REVIEW → DOMAIN_RECOVERED_NEW_EPOCH → DOMAIN_ACTIVE` | Paquete de recuperación, dos humanos distintos bajo raíces ya fijadas, conservación de todos los IDs usados/inciertos y evento separado de activación; si el quórum/raíz faltan, no se sale del bloqueo |

#### Transiciones de `artifact_verification_status`, `incident_status` y `resource_lock_status`

| Dimensión | Origen → destino | Evento, escritor y condición |
|---|---|---|
| `artifact_verification_status` | `NOT_EVALUATED → VERIFIED_INTEGRITY_PROVENANCE_COMPLETENESS` | Solo `IABVArtifactVerifier` después de inventario exhaustivo independiente, rehash y diff independiente; receipt/attestations completos |
| `artifact_verification_status` | Cualquier estado → `UNVERIFIED` o `QUARANTINED` | Verificador detecta mismatch/gap, componente pierde cobertura o aparece incidente; no se rehabilita el mismo snapshot por una afirmación del agente |
| `incident_status` | `CLEAR → OPEN` | Evento contradictorio/tardío firmado en log autoritativo; bloquea recursos aun con estado histórico terminal |
| `incident_status` | `OPEN → RESOLUTION_PROPOSED` | `IncidentReconciler` humano distinto adjunta evidencia; no elimina el incidente |
| `incident_status` | `RESOLUTION_PROPOSED → RESOLVED` | Otro humano independiente valida la disposición y se agrega evento firmado; evento contradictorio posterior crea un nuevo `OPEN` append-only |
| `resource_lock_status` | `UNLOCKED → HELD_ACTIVE` | Evento de reserva comprometido por `NonRollbackReservationLog` |
| `resource_lock_status` | `HELD_ACTIVE → HELD_UNKNOWN` | Commit/efectos no determinables o la autoridad pierde disponibilidad; nunca caduca por tiempo |
| `resource_lock_status` | `HELD_ACTIVE/HELD_UNKNOWN → HELD_INCIDENT` | `incident_status=OPEN` o rollback/divergencia que afecte el recurso |
| `resource_lock_status` | `HELD_ACTIVE/HELD_UNKNOWN/HELD_INCIDENT → RELEASE_PENDING` | Propuesta firmada y evidencia preliminar; el lock sigue efectivo |
| `resource_lock_status` | `RELEASE_PENDING → RELEASED` | `ResourceReleaseRecord` comprometido por autoridad y firmante humano independiente, sin incidentes abiertos y con prueba de árbol/recibo/recurso exacto |
| `resource_lock_status` | `RELEASE_PENDING → HELD_INCIDENT/HELD_UNKNOWN` | Incidente/gap/rollback o pérdida de evidencia antes del commit de liberación |
| `resource_lock_status` | `HELD_UNKNOWN/HELD_INCIDENT → UNLOCKED` | **Prohibido directamente**; requiere reconciliación y `ResourceReleaseRecord`, sin borrar nonce ni historia |

#### Invariantes cruzadas, locks y liberación

- **N-80 — autorización y uso son un solo hecho:** para la misma clase/`authorization_id`, `authorization_status=CONSUMED` implica `authorization_use_status=USE_COMMITTED` en el mismo evento atómico de `NonRollbackReservationLog` y bajo la misma lectura linealizable/head/epoch. `USE_REJECTED_PRECOMMIT` no es compatible con `CONSUMED`. Un `LedgerProjector` retrasado puede mostrar temporalmente una proyección antigua, pero nunca decide autorización: se vuelve a consultar la autoridad. **Si la autoridad no responde y la proyección muestra `USE_COMMITTED`, eso no confirma ni el uso autoritativo ni el no-uso; el estado queda `USE_UNKNOWN`, el dominio `DOMAIN_BLOCKED_PENDING`, no hay despacho y el lock se retiene.** La misma regla de no-resolución aplica si la proyección muestra `USE_NOT_STARTED`, `USE_REJECTED_PRECOMMIT` o cualquier otro estado no confirmado por la autoridad. Ninguna proyección puede liberar locks ni resolver `authorization_use_status`; solo una lectura válida de la autoridad operativa puede reconciliar el resultado. Si la autoridad contradice una transacción supuestamente atómica, se abre incidente y se bloquea el dominio.
- **N-81 — toda rama del deadline tiene estado terminal definido:** la expiración posterior a `GATE_RESUME_COMMITTED` debe ir a `GATE_RESUME_DEADLINE_EXPIRED` o `FIRST_INSTRUCTION_DEADLINE_EXPIRED` según si hubo resume. Sin prueba independiente completa no se produce `CLOSED_NO_EFFECT`. Una primera instrucción observada tarde produce `FIRST_INSTRUCTION_OBSERVED_LATE`, `ATTEMPT_QUARANTINED` e incidente abierto. La falta de evidencia no se convierte en resultado negativo.
- **N-82 — ninguna proyección como fallback:** ningún componente puede usar `LedgerProjector` para decidir ausencia de consumo, reserva, gate o lock cuando `NonRollbackReservationLog` no responde. Timeout: `DOMAIN_BLOCKED_PENDING`, estado pertinente `*_UNKNOWN`, sin nuevos despachos. Divergencia/rollback demostrados: `GOVERNANCE_DOMAIN_BLOCKED`.
- **N-83 — clases de autorización no sustituibles por intersección:** autorización y `AuthorizationUseRecord` son específicos de clase, ID, nonce, intento y scope. Un scope igual, solapado o subconjunto no satisface la autorización de otra clase ni omite el orden obligatorio de §2.6. Los predecesores exigidos se determinan por la rama de §2.6 que se esté utilizando. En la rama alternativa de §2.6 paso 3, una lista manual exacta firmada por el propietario puede establecer `PATH_MANIFEST_APPROVED` sin ejecutar inventario; esa alternativa legítima no constituye elusión y **no** sustituye la `MaterializationAuthorization` posterior ni ningún otro paso que siga siendo aplicable. Si falta un paso predecesor aplicable a la rama elegida, `ATTEMPT_BLOCKED`; no lectura, inventario o materialización por inferencia.
- **N-84 — ausencia tras restore no prueba no-uso:** la ausencia actual de `USE_COMMITTED` nunca basta para `USE_REJECTED_PRECOMMIT` cuando existe un evento previamente observado, una cabeza/época previa o una duda de restauración. La consulta debe corroborar la monotonía del mismo log y una cabeza no regresiva. Pérdida de evidencia o duda: `USE_UNKNOWN` + `DOMAIN_BLOCKED_PENDING`; rollback/cambio regresivo probado: `GOVERNANCE_DOMAIN_BLOCKED`. No se agrega un segundo commit de anclaje por operación. Si la garantía preexistente de no-restauración no puede acreditarse, el log no es admisible y el despacho sigue bloqueado.
- `CONSUMED` nunca vuelve a `AUTHORIZED`; una expiración/revocación posterior se refleja en eventos separados, no alterando el consumo histórico.
- `RESERVATION_NOT_COMMITTED` solo puede derivarse de prueba autoritativa no-commit; `RESERVATION_COMMIT_CONFIRMED` nunca se convierte en “no commit” por cancelación posterior.
- Sin `RESERVATION_COMMIT_CONFIRMED`, no hay proceso, gate ni dispatch. Si el resultado es unknown, no spawn ni retry.
- `GATE_RESUME_COMMITTED` no es `FIRST_INSTRUCTION_OBSERVED`; una primera instrucción fuera de la vigencia/deadline está prohibida por política A.
- `ATTEMPT_UNKNOWN`, `ATTEMPT_QUARANTINED` o `incident_status=OPEN` bloquean todo recurso solapado, intento nuevo, aceptación, retry, promoción y liberación.
- `ATTEMPT_ARTIFACT_VERIFIED` requiere inventario íntegro del snapshot, hashes recalculados y diff independiente. Ningún estado de otra dimensión crea esa transición por sí solo.
- `ACCEPTED`, `REJECTED`, `CLOSED_NO_EFFECT` y `RECONCILED` no liberan locks por sí solos. La liberación requiere `ResourceReleaseRecord`, autoridad humana independiente, evidencia de terminación/cobertura y validación de actores externos.
- Recursos sin prueba de disjunción se tratan como solapados: cuenta, quota, `CODEX_HOME`, endpoint, raíces/snapshots, baseline, tarea, dominio y proceso. Un uso manual de la misma cuenta/cuota también cuenta como actor externo; sin lock de servicio o capacidad preexistente que lo impida, la exclusividad queda `BLOCKED_UNDER_CURRENT_CONSTRAINTS`.

#### Dominio de gobernanza y recuperación

El `TrustAnchorRegistry`, fuente de tiempo, log de reservas y marcador de bloqueo deben tener identidades/raíces y procedimientos de rotación/revocación definidos. No se recupera desde un registro restaurado que sea la única autoridad de su propia validez. `GOVERNANCE_DOMAIN_BLOCKED` solo puede levantarse por un paquete de recuperación firmado por el quórum humano requerido, bajo raíces ya fijadas, conservando cada nonce/ID comprometido o incierto, los incidentes y los locks. La falta de raíz, log operativo antirregresión o quórum humano no genera una ruta alterna: el dominio permanece bloqueado indefinidamente.

### 2.9 Matriz de amenazas y resultados obligatorios

| Amenaza/condición | Control de diseño requerido | Resultado si falta o no se demuestra |
|---|---|---|
| Firma/clave/raíz suplantada o vista alterada | Pinning fuera de banda; firmante deriva vista de bytes canónicos; render seguro | `BLOCKED` |
| Roles incompatibles o delegación amplia | Matriz §2.5, permiso por acto; ningún autorizador acepta/reconcilia mismo intento | `BLOCKED` |
| Log operativo restaurado/regresado o commit ambiguo | `NonRollbackReservationLog` preexistente, append/CAS idempotente y antirregresión en un único dominio; sin él, bloqueo | `BLOCKED_UNDER_CURRENT_CONSTRAINTS`, sin spawn |
| Nonce/intent/lock incompleto | Un único evento comprometido por el log: intención + nonce-use + locks + head; ningún spawn sin confirmación | `UNKNOWN`/`QUARANTINED`; nonce consumido no reutilizable |
| Revocación/expiración antes de primera instrucción | Política A: enforcement SO impone deadline real; CAS log no es suficiente | No spawn si no hay enforcement; después, parada dentro de límite firmado |
| Watchdog/ledger/reloj/ancla falla | Lease de SO independiente, kill-on-close, latencia acotada y parada del árbol | Terminar; si no hay prueba, `UNKNOWN`/`QUARANTINED` |
| Ejecutable/loader/módulo/perfil cambian | Digest completo, referencias inmutables y proceso observado | `BLOCKED` |
| Cliente y descendientes comparten identidad, secretos o red | Confinamiento externo probado; si no, frontera `UNRESOLVED` | Sin despacho |
| Divulgación no permitida o payload no observable | Alcance autorizado más observación externa; `disclosure_observed=UNKNOWN` si no medible | `BLOCKED` si hay riesgo de contenido no autorizado |
| Path manifest y content manifest confundidos | Ambos distintos; contenido fuente/destino firmado antes del preflight | `ATTEMPT_BLOCKED` |
| Fuente protegida o ruta inesperada | Allowlist positiva, no atraviesa raíz protegida, enumeración autorizada | Sin lectura/copia; `BLOCKED` |
| `.env`/secretos/rutas no declaradas | Denegación por defecto y no materialización | `BLOCKED` |
| Enlace, reparse point, hardlink, montaje, colisión o cambio concurrente | Rechazo/registro seguro y handle estable | `BLOCKED`/`QUARANTINED` |
| Preflight expirado o modificado | `preflight_valid_until`, nuevos IDs/autorizaciones y manifiestos revalidados | Intento actual `ATTEMPT_BLOCKED`; requiere intento nuevo |
| Colector ejecuta configuración/hook del candidato | Lector de bytes propio, sin Git/config candidata/privilegios/red | `ARTIFACT_VERIFIED` bloqueado |
| Colector agotado por candidato enorme/profundo | Límites externos en entradas/bytes/profundidad/tiempo/CPU/memoria/reporte | Captura incompleta; `ARTIFACT_UNVERIFIED`/`QUARANTINED` |
| Vista del propietario engañosa | Escapar ANSI/bidi/no imprimibles, mostrar rutas/digests, firmar objeto estructurado | No aceptar |
| Captura con árbol activo o señales contradictorias | Supervisor SO autoritativo + corroboración colector; ambos concordantes | `UNKNOWN`/`QUARANTINED` |
| Evento tardío tras terminal | Overlay append-only, bloquea acciones y recursos sin borrar estado histórico | `incident_status=OPEN` |
| Recurso compartido con diferente tupla o actor externo | Intersección de recursos y exclusividad de cuenta/candidato | Rechazar despacho |
| Liberación prematura tras `ACCEPTED`/`REJECTED`/`RECONCILED` | `ResourceReleaseRecord` firmado y prueba del árbol/cierre/limpieza | Recursos siguen bloqueados |
| Política distinta/huella desconocida | Huella pre/post; waiver solo pre-dispatch y con frontera demostrada | `BLOCKED`/`QUARANTINED` |
| Cuota/coste desconocido o query facturable | Sin gasto adicional; no consultar sin autorización específica y prueba cero-gasto | `BLOCKED` |
| `ARTIFACT_VERIFIED` confundido con tests funcionales | Semántica limita a integridad/procedencia; pruebas dinámicas son otro intento autorizado | No afirmar corrección funcional |
| Mensaje de éxito sin recibo/artefacto | Recibo verificado y comparación de bytes/manifests/snapshot | `ARTIFACT_UNVERIFIED` |
| Consumidor IABV no identificado | Identidad/versión/interfaz/permisos reproducibles | `BRIDGE_NOT_READY` |
| Publicación/promoción automática | Credenciales fuera del intento y acto/autorización independiente | `BLOCKED`; incidente |
| Puerta de gobernanza deniega lectura | Respetar la puerta; no buscar conectores/rutas alternativos | `KEEP_BLOCKED` |
| Reserva/response perdido o estado huérfano | Distinción entre no-commit autoritativo, commit confirmado y commit desconocido; sin `RESERVATION_ABORTED` ambiguo | No spawn/retry alternativo; locks retenidos cuando sea incierto |
| Revocación y gate en carrera | Un mismo log ordena eventos; deadline de primera instrucción impuesto por SO y `ProcessTreeTerminator` independiente para revocación en vuelo | Sin enforcement/actor preexistente, bloqueo |
| Retroceso del log/raíces/época | Log operativo anti-rollback y registro de raíces con custodia/quórum separados; no restaurar desde proyección | `GOVERNANCE_DOMAIN_BLOCKED` hasta recuperación válida |
| Manifiesto firmado sin revisión de contenido | `ContentReviewPackage`, clasificación/preview seguro y digest exacto; scanner de secretos no se presenta como garantía | `ATTEMPT_BLOCKED` si contenido no puede clasificarse/aprobarse |
| Lectura de fuente fuera del alcance por actor de inventario/materialización | Principales diferentes, handles/ACL de SO y allowlist positiva por autorización | No leer; bloquear antes de abrir ruta inesperada |
| Parser de bytes hostiles con clave de recibo | Parser, `ReceiptSigningService` y renderer sin privilegios/credenciales separados | Sin recibo/aceptación si no hay separación |
| Divulgación observada `UNKNOWN` | Cota superior exhaustiva de payload posible, inputs de cliente enumerados y endpoint fijado | `BLOCKED` si la cota o autorización de entradas no se demuestra |
| Pérdida de lease/watchdog, ledger, ancla o tiempo | Renovación finita y parada de SO independiente; prueba de latencia/terminación | Terminar; mantener `UNKNOWN`/locks si no se confirma |
| Propietario único sin aceptador separado | Solo humanos autenticados; `PENDING_OWNER` sin aceptación automática | No `ACCEPTED`, no promoción |
| Vocabulario de estados ambiguo | Dimensiones/estados/eventos definidos en §2.8 | `BLOCKED` ante estado desconocido |
| Requisitos conjuntamente insatisfacibles | Registro de satisfacibilidad §2.12; no inferir relajaciones | `BRIDGE_NOT_READY` |

#### Amenazas adicionales derivadas de N65–N79

| Amenaza/condición | Control de diseño requerido | Resultado si falta o no se demuestra |
|---|---|---|
| Registro/raíz operativa no preexistente o restaurable | Log de reserva antirregresión preexistente, dominio independiente, CAS atómico comprobable; si no, bloquea | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` |
| Lectura de `CODEX_HOME` antes de preflight | `ClientInputReviewAuthorization` previa, rutas exactas no secretas, builder no abre rutas por sí mismo | `PREFLIGHT_BLOCKED` |
| Snapshot con archivo/stream omitido del manifiesto | Enumerator/verifier independiente del namespace sellado, cobertura total de entries/ADS/metadata soportados | `ARTIFACT_UNVERIFIED` |
| Diff declarado por parser/colector | `SnapshotDiffVerifier` recalcula diff de snapshots inmutables con algoritmo fijo | `ARTIFACT_UNVERIFIED` |
| Observador de proceso pierde eventos | Cobertura/sequence/heartbeat sin huecos desde antes de spawn hasta cierre | `ATTEMPT_UNKNOWN`, lock retenido |
| Revocación sin actor de parada | `RevocationAuthority` y `ProcessTreeTerminator` preexistentes, distintos de launcher/observer | No despacho |
| ACL de fuente requeriría modificarse | Solo handle/ACL preexistente que ya impide roots protegidas; no cambiar la fuente | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` |
| Vista del propietario distinta de los bytes firmados | Canal confiable renderiza desde bytes inmutables y calcula ambos digests fuera del renderer del host | No aprobar |
| Requisitos de humanos incompatibles | Matriz de actos incompatibles + personas autenticadas por fase | `PENDING_OWNER`/locks; sin sustituto de IA |
| Lease/reloj sin actor ni límite finito | Renovador, detector y deadlines firmados; capacidad externa de parada | No autorización; `UNRESOLVED` no equivale a parada |
| Inventario/manifiesto con orden contradictorio | Autorizar scope de inventario → enumerar metadata → aprobar path_manifest → autorizar copia → aprobar content_manifest | `ATTEMPT_BLOCKED` |
| Registro de satisfacibilidad con celda “capacidad preexistente” no demostrada | Nombrar capacidad, fuente admisible, dependencia, contradicción y autoridad por fila | `BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta evidencia |


### 2.10 Consumidor IABV, aceptación y promoción

El consumidor/verificador IABV permanece `UNRESOLVED`. Antes de cualquier evaluación futura se deben identificar implementación, versión, interfaz, raíz de confianza, permisos, entradas, salida, reproducción y separación respecto a emisor, lanzador, colector, reconciliador y decisor. Si no se identifica, no se infiere `ARTIFACT_VERIFIED` ni `BRIDGE_READY`.

El consumidor recibe solo recibo autenticado, estado ledger/testigo y snapshot inmutable con digest. Verifica la firma, ancla anti-rollback, autorización/nonce, cadena del proceso, identidad de origen, `path_manifest` y `content_manifest`, baseline, diff/snapshot, política/frontera, divulgación observada, eventos/incidentes y completitud. No ejecuta archivos del candidato, no rellena evidencia desde mensajes del agente, no acepta, no reconcilia, no libera ni promueve.

`ARTIFACT_VERIFIED` certifica únicamente que se verificaron integridad, procedencia y completitud documental de artefactos y recibo; no certifica que el software funcione, sea seguro o supere pruebas. `ACCEPTED` es decisión de gobierno sobre el objeto exacto, no aceptación funcional ni promoción. El aceptador es un principal separado del que firmó la autorización de despacho, lanzó o recolectó. Pruebas dinámicas/análisis que ejecuten candidato requieren autorización, frontera y recibo propios en un intento nuevo. Promoción/commit/push/merge/despliegue requiere acto y autorización nuevos; nunca es consecuencia automática de aceptar. Ningún flujo autónomo se autoacepta ni reconcilia.

### 2.11 Evidencia futura requerida — no autorizada en esta fase

Una futura decisión exigiría, en fases separadas y autorizadas, evidencia independiente de: `NonRollbackReservationLog` preexistente y su política de restore/idempotencia; root-of-roots/pinning/rotación/revocación y quórum; autorización y lector de inputs `CODEX_HOME` no secretos; inventario autorizado previo al `path_manifest`; handles/ACL del SO sin modificación de fuente; `KernelResumeDeadlineEnforcer`, autoridad de revocación, `ProcessTreeTerminator`, reloj/lease/suspensión y latencia; `ImmutableSnapshotStore`, enumeración completa, `ReceiptDigestVerifier` y `SnapshotDiffVerifier`; canal confiable de vista/firma del propietario; salida/divulgación por canal y `NetworkEgressEnforcer`; tablas completas de autorización-use/reserva/launch/incident/lock/domain; matriz de incompatibilidad y número de humanos; registro de satisfacibilidad con siete campos por fila; consumidor IABV y actos separados de aceptación/promoción.

En esta fase esos aspectos siguen `PROPOSED`, `NOT_TESTED` o `UNRESOLVED`. No se realiza un preflight local, no se consulta cuota, no se inspecciona el worktree ni se intenta llegar a fuentes locales bloqueadas. Los informes históricos de CLI/local y estados de worktree siguen siendo `OWNER_REPORTED`; no se mezclan rutas/fechas ni se inspeccionan `data/`, SQLite, M0A u otras fuentes protegidas.

### 2.12 Criterios para una futura evaluación y registro de satisfacibilidad

Ninguna evaluación de implementación, ni siquiera de solo lectura, queda autorizada ahora. Esta tabla evalúa coherencia lógica bajo las restricciones conocidas; no asevera presencia ni ausencia de capacidades no inspeccionadas.

Cada fila contiene siete campos obligatorios: (i) alcance de la restricción, (ii) prerrequisitos técnicos/humanos, (iii) dependencia de cuenta/identidad/credencial/servicio/plan/gasto, (iv) evidencia preexistente admisible que falta o sería suficiente, (v) contradicciones con otros requisitos, (vi) autoridad humana y dependencia concreta de decisión del propietario, y (vii) `satisfiability_status` + `operation_gate_status` con razón. “No identificado” no equivale a “no existe”; pero hasta que una capacidad preexistente se demuestre por vía autorizada, no puede usarse para avanzar. Una posibilidad teórica no cambia el estado.

**Taxonomía normativa única del registro de satisfacibilidad:** cada requisito recibe exactamente uno de estos cuatro estados lógicos: `SATISFIABLE` (las condiciones necesarias están demostradas por evidencia admisible bajo las restricciones vigentes); `CONDITIONALLY_SATISFIABLE` (existe una condición precisa aún no demostrada, con capacidad preexistente concreta y evidencia admisible nombrada); `BLOCKED_BY_CURRENT_CONSTRAINTS` (la conjunción del requisito con una restricción vinculante impide avanzar, o el acto requiere una autoridad humana incompatible/no disponible bajo el marco actual); `UNRESOLVED` (la especificación o evidencia es insuficiente para clasificar la compatibilidad lógica). `OWNER_DECISION_REQUIRED` no es un quinto estado: la decisión pendiente se registra en la columna propia de dependencia de decisión/autoridad y el estado lógico pertinente sigue siendo uno de los cuatro. `NOT_APPLICABLE` se registra como alcance excluido, no como estado de satisfacibilidad.

**Separación de planos:** `BLOCKED_UNDER_CURRENT_CONSTRAINTS` sigue siendo el resultado operativo fail-closed para un gate/intento que no puede avanzar; no es uno de los cuatro estados lógicos del registro. Una fila puede ser `CONDITIONALLY_SATISFIABLE` y a la vez tener `operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS` hasta que la capacidad y su evidencia se acrediten por vía autorizada. No confundir `UNRESOLVED` con incompatibilidad probada, ni usar `CONDITIONALLY_SATISFIABLE` como escape: toda condición debe nombrar capacidad, evidencia admisible, dependencia humana y condición de fallo.

Cada fila conserva los siete campos mínimos: alcance de restricción, prerrequisitos técnicos/humanos, dependencia cuenta/identidad/credencial/servicio/plan/gasto, evidencia preexistente requerida, contradicciones/interacciones, autoridad y dependencia de decisión del propietario, y `satisfiability_status` + `operation_gate_status`/razón. Ninguna fila puede usar “salvo capacidad preexistente” sin nombrar la capacidad, el artefacto admisible que la demostraría y el estado operativo mientras falte.

| Requisito y alcance exacto | Prerrequisitos técnicos/humanos | Dependencia cuenta/identidad/credencial/servicio/gasto | Evidencia admisible preexistente requerida | Contradicción/interacción | Autoridad + dependencia de decisión Owner | Satisfacibilidad lógica + gate operativo y razón |
|---|---|---|---|---|---|---|
| Registro autoritativo antirregresión por operación: reserva, nonce, revocación, locks, gate | Log append-only con CAS/serialización, idempotencia por request ID, restore/rollback detectable y confirmación durable | Servicio/storage identity, root de confianza y política de retención; no se permite crear servicio/credencial nuevo | Identidad/documentación del servicio existente, garantía de operación/restore, raíz pinneada y receipt verificable sin acceder a checkout | La custodia humana offline no puede confirmar cada operación; una proyección ledger no puede suplir el log | Propietario decide cambios de restricción; control/gobernanza valida evidencia | satisfiability_status=CONDITIONALLY_SATISFIABLE; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS hasta prueba admisible de la capacidad preexistente. |
| Root-of-roots, registro de raíces, rotación y recuperación | Raíz inicial pinneada fuera de banda, dos humanos autenticados distintos, epoch/tombstones y matriz de quién revoca a quién | Puede implicar identidades humanas/credenciales o servicio de custodia | Procedimiento/pinning preexistente y actas firmadas verificables; no basta una clave presentada por el mismo registro | Regresión del propio registro crea circularidad; propietario único no cumple quórum | Propietario y autoridad de gobernanza humana distinta | satisfiability_status=BLOCKED_BY_CURRENT_CONSTRAINTS para actos que exigen quórum humano no disponible; la existencia de raíz/custodia que no se ha revisado permanece UNRESOLVED. operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS. |
| Deadline de primera instrucción y revocación en vuelo | Kernel/SO impone política A en reanudación/primera instrucción; `ProcessTreeTerminator` independiente impone `max_stop_latency`; tiempo confiable | Requiere primitiva de SO/preexistente, identidades separadas y valores numéricos firmados | Especificación/atestado preexistente de la plataforma con deadlines y capacidades de terminación; no se prueba mediante texto | CAS en log no es atomicidad física; user-space no puede cubrir la ventana por sí solo | Propietario fija límites; autoridad técnica puede presentar evidencia sin autorizar ejecución | satisfiability_status=CONDITIONALLY_SATISFIABLE solo si las primitivas/actores de SO preexistentes se demuestran; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS sin esa evidencia. |
| Inventario y `path_manifest` | `SourceInventoryAuthorization` con raíces, profundidad, tipos y límites; inventario solo metadata; aprobación humana posterior de rutas | Puede requerir OS identity/handles existentes | Esquema de autorización y evidencia de que enumera solo scope aprobado sin cruzar roots protegidas | No puede aprobarse el resultado antes de obtener inventario; el inventario tampoco autoriza lectura de bytes | Propietario autoriza scope y aprueba el manifiesto | satisfiability_status=CONDITIONALLY_SATISFIABLE si el mecanismo de SO preexistente puede imponer el scope; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS mientras no se autorice/proporcione evidencia. |
| Handles/ACL sin modificar la fuente | Identidad/ACL preexistente ya deniega raíces protegidas o proveedor preexistente de handles exactos | OS identity/capability, pero no se permiten nuevos usuarios/ACL/servicios | Política/ACL/capability existente verificable sin tocar la fuente, por medio autorizado | Allowlist en una identidad con acceso global es solo código y contradice la prohibición de cambiar ACL | Propietario puede decidir una restricción distinta; esta propuesta no la decide | satisfiability_status=CONDITIONALLY_SATISFIABLE solo si la identidad/ACL/handle preexistente ya satisface el scope; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS hasta prueba admisible. |
| Aprobación de contenido y `ContentReviewPackage` | Snapshot inmutable, manifiesto canonizado, render íntegro y límite finito revisable | Puede requerir canal de visualización/firma preexistente | Paquete derivado independientemente de bytes exactos, canonicalización versionada, confirmación del humano sobre la misma vista | Digest opaco o renderer no confiable no es consentimiento informado | Propietario firma el contenido exacto | satisfiability_status=CONDITIONALLY_SATISFIABLE solo con un canal confiable preexistente; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS hasta evidencia. |
| Revisión de `CODEX_HOME`/entorno no secreto | `ClientInputReviewAuthorization` por rutas exactas/nombres de variables antes de lectura, lector con allowlist y salida acotada; exclusión completa de credenciales | Puede tocar archivos dentro de CODEX_HOME; no se permite leer credenciales ni abrir login | Objeto de autorización, `AuthorizationUseRecord`, lista de rutas/nombres, snapshot/digest y vista revisada | ContentReviewBuilder no puede ser la autoridad para leer lo que luego construye; credenciales/secretos embebidos obligan bloqueo | Propietario autoriza lectura exacta y aprueba contenido | satisfiability_status=CONDITIONALLY_SATISFIABLE solo con lector/autorización preexistentes de alcance exacto; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS y la revisión no está autorizada ahora. |
| Credenciales y cota de divulgación por canal | Cliente autenticado mediante canal de credenciales separado; hijos sin credenciales/HOME/CODEX_HOME; endpoint/bytes máximos por canal aplicados externamente | Acceso a credencial existente y mediación del cliente/servicio; no auth nueva, copia o plan nuevo | Capacidad de mediación/egress preexistente, raíz pinneada, cota por fuentes/canal/endpoint y evidencia de aislamiento | El cliente necesita autenticar; TLS puede ocultar payload; una cota incompleta no admite `disclosure_observed=UNKNOWN` | Propietario puede cambiar restricciones; el contrato no lo hace | satisfiability_status=CONDITIONALLY_SATISFIABLE solo si la mediación de credenciales/egress y cota completa preexisten; en otro caso BLOCKED_BY_CURRENT_CONSTRAINTS. operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS hasta demostrarlo. |
| Snapshot completo y autoridad del diff | Namespace inmutable con enumeración total de entries/streams; hash-verifier y diff-verifier independientes | Almacén/snapshot y raíz de bytes preexistentes | Inventario de la API con cobertura, entry count/bytes/root; recálculo de hash y diff desde dos snapshots inmutables | El parser puede omitir archivos o hunks; el hash de lo que el parser lista no demuestra completitud | Verificador independiente valida; propietario decide la aceptación | satisfiability_status=CONDITIONALLY_SATISFIABLE hasta probar enumeración total y diff independiente; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS si falta esa prueba. |
| `CLOSED_NO_EFFECT` y terminación | `OSExecutionObserver` con cobertura sin huecos; `ProcessTreeTerminator` independiente; registro de eventos y correlación intento/creación | Primitivas OS/identidades y lease preexistentes | Secuencia autenticada con cobertura/heartbeat sobre toda la ventana; recibo independiente de cierre | Observador muerto puede dejar log vacío; launcher no puede autocertificar; CPU/E/S cero no bastan | Propietario define tolerancias antes de autorizar; observer atesta solo | satisfiability_status=CONDITIONALLY_SATISFIABLE solo con observer/terminator independientes ya existentes; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS sin evidencia. |
| Human quorum y separación de funciones | Mínimo de 2 humanos en ruta normal; reconciliación incidente y liberación con personas distintas según matriz; 2 humanos para pinning/recovery | Personas/credenciales humanas preexistentes y autenticadas | Matriz acto×acto, mandato por acto, raíces y evidencia de identidades humanas | Propietario único no puede autorizar, aceptar, reconciliar, liberar o recuperar cuando la matriz prohíbe acumulación | Solo propietario puede cambiar restricciones; ninguna IA decide | satisfiability_status=BLOCKED_BY_CURRENT_CONSTRAINTS para la ruta que exige humanos distintos si solo existe la autoridad humana del propietario; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS. |
| Locks/exclusividad de cuenta y actividad externa | Lock por intersección de recursos y exclusión de uso manual concurrente | Cuenta/servicio; puede requerir capacidades de exclusión del lado de servicio o cuenta dedicada | Solo evidencia preexistente admisible que identifique: (a) el servicio/plataforma/cuenta exactos y el mecanismo de lock/lease impuesto por ese servicio; (b) un identificador observable del lock/lease y su scope, vigencia/expiración y, si aplica, fencing/epoch; (c) el artefacto documental/configurativo o contrato de interfaz que establece cómo el servicio serializa o rechaza tanto uso manual/UI como clientes API/automatizados; y (d) un recibo/evento/audit trail preexistente que permita corroborar el estado y la cobertura de ese lock/lease. Un lock local al orquestador, token portador, promesa humana o convención de “no usar manualmente” no demuestra exclusión impuesta por el servicio. La evidencia no debe obtenerse mediante una consulta, autenticación o gasto no autorizado. | “No usar manualmente” no es un lock; cuenta dedicada puede exigir gasto/auth prohibidos; un artefacto que cubre solo API no prueba cobertura de la UI/manual ni viceversa | Propietario decide si cambiar restricciones; el contrato no infiere ni crea capacidades nuevas | satisfiability_status=CONDITIONALLY_SATISFIABLE solo si una capacidad preexistente identificada demuestra exclusión impuesta y observable de los canales que comparten la cuenta; de lo contrario, operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS y sin despacho hasta evidencia. |
| Revocación, lease, reloj y suspensión | `RevocationAuthority`, renovador, detector de suspensión y `max_stop_latency` finitos | Raíces, tiempo/servicio y permisos SO preexistentes | Identidad/raíz/cadencia/latencia documentadas y observables | Un valor “por definir” no es una barrera; pérdida de reloj/lease exige terminar, no solo escribir UNKNOWN | Propietario fija límites finitos; autoridad de gobernanza revisa evidencia | satisfiability_status=CONDITIONALLY_SATISFIABLE solo con mecanismos/actores preexistentes y límites firmados; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS sin evidencia. |
| Antirreplay por cada autorización de uso | Registro por clase de autorización, nonce/ID, scope y actor; consulta idempotente; sin retry con nuevo nonce | Almacenamiento/identidad preexistente | Esquema/registro y raíz; no hay autorización genérica para inventario/materialización/preflight | Nonce de ejecución no cubre usos anteriores | Propietario firma cada clase específica | satisfiability_status=CONDITIONALLY_SATISFIABLE solo si la autoridad/log por clase e ID preexiste y demuestra idempotencia; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS hasta evidencia. |
| Personas y liberación de recursos | Matriz de transición por `resource_lock_status`; firma de liberación independiente y prueba de cierre/incident clear | Humanos/credenciales preexistentes; no automatic delegation | `ResourceReleaseRecord` enlazado a eventos del log y evidencia de terminación/recibo | Aceptar/rechazar/reconciliar no libera por sí; propietario único puede retener lock indefinidamente | Autoridad humana de liberación separada | satisfiability_status=BLOCKED_BY_CURRENT_CONSTRAINTS para actos que requieren autoridad humana independiente no disponible; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS y locks retenidos. |
| Verificador/consumidor IABV | Identidad/versión/schema/raíz y entradas/salidas verificables, sin ejecutar candidate code | Consumidor preexistente, permisos/roots | Artefacto/documentación versionada del consumidor disponible por vía autorizada | No se puede afirmar `ARTIFACT_VERIFIED`/`BRIDGE_READY` sin consumidor identificado | Propietario autoriza evaluación en fase separada | satisfiability_status=UNRESOLVED hasta identificar/verificar el consumidor mediante una fuente autorizada; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS y no es autorización de ejecución. |
| Coste/cuota y pruebas funcionales | Evidencia cero-gasto preexistente; pruebas dinámicas en intento separado con autorización propia | Servicio/plan/cuota; no hay consultas facturables autorizadas | Solo artefacto admisible preexistente que pruebe límite; no consultar al servicio para descubrirlo | Sin dato cero-coste disponible, no se hace despacho; ARTIFACT_VERIFIED no significa que el software funcione | Propietario decide fase futura de pruebas por separado | satisfiability_status=BLOCKED_BY_CURRENT_CONSTRAINTS para comprobarlo consultando servicios/cuota o incurriendo gasto bajo las restricciones actuales; operation_gate_status=BLOCKED_UNDER_CURRENT_CONSTRAINTS sin evidencia cero-gasto preexistente. |

#### Conjunciones bloqueantes identificadas expresamente

1. **Antirregresión por operación + no crear servicios/credenciales:** sin un `NonRollbackReservationLog` ya disponible en dominio independiente, el nonce/lock/head no puede tener garantía operacional; `BLOCKED_UNDER_CURRENT_CONSTRAINTS`, no solo `UNRESOLVED`.
2. **Custodia humana offline + atomismo por operación:** una firma offline de checkpoint no detecta por sí sola una reserva después de ese checkpoint. Solo un log preexistente con monotonicidad por operación permite continuar; si no existe, no hay despacho.
3. **Exclusividad de cuenta + sin plan/auth/gasto nuevos:** incompatibles si no existe un lock del lado del servicio/cuenta ya activo que incluya uso manual. Convención humana no sustituye lock.
4. **Propietario único + separación de funciones:** pinning/recuperación y aceptación/reconciliación/liberación que exigen humanos distintos son bloqueados. La consecuencia válida puede ser `PENDING_OWNER` y locks permanentes; no se autoacepta.
5. **Cliente autenticado + credenciales fuera del modelo/hijos + TLS opaco:** si no hay mediación de transporte y egreso preexistentes, la cota no es completa; `BLOCKED_UNDER_CURRENT_CONSTRAINTS`.
6. **Lectura de fuente sin cambiar ACL + aislamiento real de roots protegidas:** si no existe una identidad/handle capability SO preexistente que ya deniegue las roots protegidas, inventario/materialización bloqueados.
7. **Gate del log + deadline de primera instrucción:** la política A exige enforcement del SO en el límite físico; CAS + proceso suspendido en user-space no bastan. Sin mecanismo preexistente, no hay despacho.
8. **Recibo independiente + parser sin privilegios:** el hash-verifier enumera todo el snapshot y un diff-verifier independiente recalcula el diff. Si no puede demostrar completitud, no hay `ARTIFACT_VERIFIED`.
9. **CLOSED_NO_EFFECT + observer/terminator independientes:** sin cobertura de eventos sin huecos y parada atribuible, el resultado es `ATTEMPT_UNKNOWN`; el lock no se libera.
10. **La falta de segundo humano + recursos compartidos:** aceptar/reconciliar/liberar no se sustituye por una IA ni por una autoridad imaginaria; los recursos permanecen bloqueados.
11. **Autenticación/coste no observables + prohibición de consulta/gasto:** no se consulta al servicio para “probar cero gasto”; sin evidencia preexistente, no hay despacho.
12. **Verificación de artefacto + corrección funcional:** `ARTIFACT_VERIFIED` no autoriza pruebas ni certifica funcionalidad; cualquier verificación dinámica es otro intento con autorización independiente.

Para cada `BLOCKED_UNDER_CURRENT_CONSTRAINTS`, una futura reconsideración exigiría decisión explícita del propietario sobre la restricción relevante y evidencia admisible de la capacidad concreta. El diseño v7 no solicita ni presupone esa decisión; esta frase se conserva como historial del candidato v7.
### 2.13 Matriz de pruebas futuras — propuestas, no ejecutadas ni autorizadas

La siguiente matriz es una lista de oráculos candidatos, no una autorización. Cualquier futura prueba exigiría un acto separado del propietario y una decisión de gobernanza; no se infiere permiso de que un test aparezca aquí.

- Para un log preexistente (solo tras autorización separada): respuesta perdida de `NonRollbackReservationLog.AppendCAS` y `LedgerProjector`; restauración del registro raíz-de-raíces; nonce igual con request-id distinto; retry idempotente; revocación intercalada antes/después de append/CAS; rollback con época vieja; pérdida transitoria frente a divergencia real. Esta matriz no afirma que tal log exista.
- Inyectar caída antes/durante/después del `NonRollbackReservationLog.AppendCAS` y de la proyección del ledger; demostrar que evento, nonce, lock y head son todos committed o ninguno, y que la consulta read-only por request ID resuelve una respuesta perdida sin segundo proceso.
- Inyectar revocación/expiración justo antes/después de `GateResumeCAS`, durante pausa suspendida, entre gate y resume, y cerca de primera instrucción; el gate debe bloquear o el SO debe parar dentro de latencia declarada. Si el mecanismo del SO no existe, mantener `UNRESOLVED`, no marcar test como aprobado.
- Forzar pérdida de broker, `NonRollbackReservationLog`, ledger, fuente de tiempo, renovador de lease y detector de suspensión; verificar parada real del árbol y medir latencia. Marcar `UNKNOWN` sin terminación no cuenta como pass.
- Restaurar raíz/época de `TrustAnchorRegistry`; revocar/rotar cada raíz; intentar firmar con raíz no pinneada; combinar autorización con aceptación, reconciliación, liberación o promoción; comprobar que ningún principal asume dos actos incompatibles.
- SourceInventoryAuthorization, client-input review y MaterializationAuthorization sin scope; ruta permitida y protegida comparten raíz; abrir/filtrar/hashear `auth.json`; enlaces, reparse points, hardlinks, mounts, ADS, rutas equivalentes/colliding, `.env` y mutación concurrente. Ninguna prueba usa credenciales reales ni autoriza inspeccionar roots protegidas.
- Igualdad de rutas con bytes diferentes; aprobación de manifiesto con 5.000 entradas o contenido sobre presupuesto; falso negativo de secreto; `CODEX_HOME` con instrucciones privadas; env/outputs de descendientes fuera de alcance; el propietario debe ver el contenido exacto o el intento se bloquea.
- Cliente que requiere credential file; canal de autenticación, contexto de modelo y descendientes; intentos de serializar token; `NetworkEgressEnforcer` con endpoint alterno/telemetría/proxy/hijo; ciphertext con `disclosure_observed=UNKNOWN`; el oráculo exige cota completa y enforcement independiente.
- Parser/manifest malicioso que omite una entrada/ADS; enumerador independiente recalcula la raíz de todo el snapshot; `SnapshotDiffVerifier` omite/añade hunk; signer rechaza digest/diff no atestado; renderer y canal confiable muestran objetos distintos; bidi/ANSI/homoglifos. Sin enumeration coverage o firma/view channel independiente, bloqueo.
- Prueba de `CLOSED_NO_EFFECT` para no proceso creado, proceso suspendido nunca reanudado y gate confirmado; matar/pausear el observador, perder heartbeat, cortar lease, revocar antes/después del gate y detener el árbol por el terminador independiente. CPU/I/O cero por sí solo nunca basta; toda pérdida de cobertura resulta `UNKNOWN`.
- Intentar locks con tuplas distintas pero recursos solapados (cuenta, home, endpoint, raíz, baseline, tarea, dominio, procesos externos), liberar tras `ACCEPTED`/`REJECTED`, actividad manual concurrente, incidente tardío tras cualquier terminal e imposibilidad de segundo humano. Bloqueo no se libera sin record válido.
- Revisión del registro de satisfacibilidad: validar los siete campos por requisito; identificar contradicciones causales N65/N70/N71/N74, dependencias de personas/credenciales/gasto y estados bloqueados. No llamar a una conjunción “satisfacible” porque hipotéticamente podría existir un servicio nuevo.

Ninguna prueba enumerada ha sido ejecutada, y ninguna autoriza leer el worktree, datos, secretos, cuota, autenticación, instalar, realizar turnos Codex, builds, runtime, commits o publicar.

### 2.14 Historial, registro acumulado de hallazgos y delta v7→v8

Este historial refleja informes `CLAUDE_REPORTED` recibidos en la conversación; el coordinador no reabrió las fuentes públicas. Un estado `CLOSED` en una revisión previa significa únicamente cierre documental según ese informe, nunca control implementado. La quinta revisión de v5 devolvió `PASS_WITH_REPAIRS`: N-31 y N-41 `CLOSED`; los demás N-26–N-40 `PARTIALLY_CLOSED`; N-01–N-25 `NOT_RECOVERED` para esa revisión porque v5 solo preservaba estados, no el texto íntegro de los hallazgos. En v6 se incluyen resúmenes y contraejemplos para volverlos revisables; no se afirma que el texto aquí sea una cita literal de los informes anteriores.

#### Historial de estados recibidos

| Revisión | Estados reportados y límites |
|---|---|
| Contrato original | `PASS_WITH_REPAIRS`, C01–C12; no es aceptación del puente. |
| v2 | `PASS_WITH_REPAIRS`, N-01–N-12; defectos de estados/autoridad, ejecutable, frontera, consumo, captura, límites, política, materialización y preflight. |
| v3 | `PASS_WITH_REPAIRS`; `CLOSED`: N-01, N-03, N-07, N-09, N-11; `PARTIALLY_CLOSED`: N-02, N-04–N-06, N-08, N-10, N-12; se añadieron N-13–N-25. |
| v4 | `PASS_WITH_REPAIRS`; `CLOSED`: N-03, N-09–N-11, N-17–N-18, N-20–N-21, N-24–N-25; `PARTIALLY_CLOSED`: N-01, N-02, N-04–N-08, N-12–N-16, N-19, N-22–N-23; se añadieron N-26–N-41. |
| v5 | `PASS_WITH_REPAIRS`; la revisión dijo que no podía readjudicar N-01–N-25 por falta de contraejemplos; `CLOSED`: N-31 y N-41; se añadieron N-42–N-64. |
| v6 | Sexta revisión: `PASS_WITH_REPAIRS`; N-01–N-64: 27 `CLOSED`, 37 `PARTIALLY_CLOSED`, ninguno `OPEN`; se añadieron N-65–N-79. Los estados son reportados por Claude y se reproducen en la tabla inferior, no son aceptación de IABV. |
| v7 | Informe suministrado por el propietario: `PASS_WITH_REPAIRS`; N-01–N-79: 30 `CLOSED`, 49 `PARTIALLY_CLOSED`; N-80–N-84 nuevos. `OWNER_REPORTED`; el informe declara que no volvió a abrir fuentes públicas. |
| v8 | `PROPOSED_DESIGN_V8`; incorpora reparaciones textuales para N-80–N-84 y normaliza la taxonomía del registro; la octava revisión reportó `PASS_WITH_REPAIRS`, pero se mantiene `OWNER_REPORTED`. |
| v9 | `PROPOSED_DESIGN_V9`; aclara proyección sin autoridad, rama manual y evidencia concreta para exclusividad; el informe octavo contenía una afirmación contradicha por la tabla v8 respecto de la arista de primera instrucción tardía. Pendiente de novena revisión, sin aceptación anticipada. |

La sexta revisión señaló degradación de N-09 (`CLOSED` en v4 a `PARTIALLY_CLOSED` en v6) por el acceso previo de `ContentReviewBuilder`, y la trayectoria de N-01/N-07 (`CLOSED` en v3 → `PARTIALLY_CLOSED` en v4 → N-01–N-25 `NOT_RECOVERED` en la revisión de v5 → `PARTIALLY_CLOSED` en la revisión de v6). Estos cambios no se ocultan ni se corrigen retroactivamente.

#### Registro acumulado N-01–N-79 (problema, contraejemplo y respuesta v7 resumidos)

Los enunciados heredados son resúmenes trazables para revisión, no citas literales de todos los informes originales. Los estados N-01–N-64 son los reportados por la sexta revisión; deben contrastarse contra la redacción v7, no aceptarse automáticamente. La columna `Respuesta v7` describe la respuesta documental y el residual que debe revisar Claude.

| ID | Estado reportado en la sexta revisión | Problema heredado / contraejemplo representativo | Respuesta v7 y residual que debe revisarse |
|---|---|---|---|
| N-01 | PARTIALLY_CLOSED | En v2 intención y consumo de nonce aparecían en orden contradictorio; caída entre ambos podía dejar autorización reutilizable. | §2.8 especifica un log operativo preexistente con evento conjunto de intención/nonce/locks/head; si no se identifica su capacidad anti-rollback, bloqueo efectivo. |
| N-02 | PARTIALLY_CLOSED | Manifiesto que contenía digests antes de copiar, o inventario que recorría raíz protegida; lectura local sin autorización clara. | §2.6 pone autorización de scope de inventario antes de enumeración, aprobación de `path_manifest` después y copia solo tras autorización; handles/ACL preexistentes siguen bloqueantes. |
| N-03 | CLOSED | Evento tardío contradictorio tras estado terminal sin transición de incidente ni autoridad de salida. | §2.8 overlay append-only prevalece en todas dimensiones; comprobar cobertura de todos los terminales. |
| N-04 | PARTIALLY_CLOSED | Un principal/delegado podía combinar emisión, aceptación, reconciliación u otros actos incompatibles. | §2.5 matriz con principales humanos/servicios separados; el entorno real sigue no demostrado. |
| N-05 | PARTIALLY_CLOSED | Firma de propietario con referencia/clave sin raíz de confianza, canal de firma o revocación independiente. | §2.3 define pinning, vista firmada y root-of-roots; el mecanismo inicial sigue `UNRESOLVED`. |
| N-06 | CLOSED | Colector podía ejecutar/interpretar configuración o hooks hostiles del candidato al crear diff/manifiesto. | §2.7 separa parser, hash-verifier y signer; presupuestos y separación real requieren evidencia futura. |
| N-07 | PARTIALLY_CLOSED | `disclosure_scope` se confundía con payload observado; cota no incluía todo lo que cliente/descendientes podían devolver al modelo. | §2.5/2.7 amplía cota a config, entorno, outputs, protocolo y endpoint; autenticación/egress preexistentes siguen `UNRESOLVED`. |
| N-08 | PARTIALLY_CLOSED | Estado de preflight invalidad/revocado no tenía transición de salida o expiración clara; tablas de autorización incompletas. | §2.8 enumera dimensiones y eventos; validar todos los cross-state invariants. |
| N-09 | PARTIALLY_CLOSED | Preflight de reglas podía abrir/volcar auth.json o entorno sensible por estar en la misma raíz. | §2.6 añade `ClientInputReviewAuthorization` y prohíbe al builder abrir rutas por su cuenta; ningún preflight/input review está autorizado ahora y falta probar una capacidad de lectura segura preexistente. |
| N-10 | CLOSED | Waiver de política posterior podía rescatar un intento ya lanzado. | §2.3 requiere waiver antes de autorización final y reserva; validar timestamp y scope ligados a digests. |
| N-11 | CLOSED | Recursos no imponibles se omitían con “en la medida posible”; timeout/coste no tenía oráculo. | §2.3 exige límites imponibles y bloquea coste desconocido; fuente de tiempo/capacidad real continúa no demostrada. |
| N-12 | PARTIALLY_CLOSED | Reloj/watchdog no tenía autoridad, skew o parada definida al perder fuente confiable. | §2.3/2.8 define fuentes, lease y límites, pero observador/renovador/detector real siguen no identificados. |
| N-13 | PARTIALLY_CLOSED | Restaurar snapshot viejo del ledger podía revivir nonce; freeze escrito en ledger incierto. | §2.8 exige un log operacional antirregresión separado del ledger; sin evidencia de ese log preexistente, nonce/locks/head no son demostrables y el despacho está bloqueado. |
| N-14 | CLOSED | `path_manifest` y `content_manifest` confundidos; owner firmaba rutas sin aprobar bytes reales. | §2.6 requiere aprobación posterior de digests por archivo y ContentReviewPackage antes de preflight. |
| N-15 | CLOSED | Revocación/cambio del candidato tras revalidación/commit y antes de spawn. | §2.8 Gate CAS + límite gate→primera instrucción; falta mecanismo real de SO y se bloquea si no existe. |
| N-16 | PARTIALLY_CLOSED | Watchdog muerto permitía que árbol siguiera; marcar UNKNOWN no ejecuta la parada. | §2.8 exige kill/lease externa y límite de parada; capacidad real `UNRESOLVED`. |
| N-17 | CLOSED | Waiver posterior a observar discrepancia permitía “rescatar” el intento con sesgo retrospectivo. | §2.3 exige waiver anterior a firma final y reserva. |
| N-18 | CLOSED | `ARTIFACT_VERIFIED` podía leerse como corrección funcional/tests. | §2.7 limita la semántica a integridad/procedencia/completitud. |
| N-19 | PARTIALLY_CLOSED | Vista de propietario con bidi/ANSI/homoglifos podía ser diferente del objeto firmado. | §2.3/2.7 liga object digest y review-view digest; seguridad real del canal/render sigue no demostrada. |
| N-20 | CLOSED | Vencimiento de preflight/ATTEMPT_BLOCKED/AUTH_BLOCKED sin transición o reintento definido. | §2.8 define invalidación como evento, no reutiliza intento. |
| N-21 | CLOSED | Evidencia de cuota/coste requería consulta autenticada posiblemente billable. | §2.3/2.12 prohíben consulta para descubrir cuota; sin evidencia preexistente no hay despacho. |
| N-22 | CLOSED | Recibo registraba scope autorizado, no divulgación observada. | §2.7 distingue scope, upper bound y observed; credenciales/egress siguen bloqueantes si no se acotan. |
| N-23 | CLOSED | Cuarentena/locks no cubrían uso manual ni liberación tras terminal normal. | §2.8 locks por intersección y actores externos; exclusividad real bloqueada sin capacidad previa. |
| N-24 | CLOSED | Colector podía agotar recursos con candidatos enormes sin límites. | §2.7 fija límites y nunca éxito parcial; su imposición no demostrada. |
| N-25 | CLOSED | No había fuente única de verdad para TERMINAL_CAPTURED; supervisor y colector podían discrepar. | §2.7 asigna supervisor OS autoritativo y colector corroborativo; capacidad de observación queda `UNRESOLVED`. |
| N-26 | PARTIALLY_CLOSED | `ReserveCAS` podía quemar autorización en witness mientras ledger quedaba AUTHORIZED; revocación entre pasos no tenía linealización. | §2.8 prohíbe split commits y requiere un `NonRollbackReservationLog` preexistente; su existencia/capacidad sigue bloqueante. |
| N-27 | PARTIALLY_CLOSED | Check-then-resume: revocación entraba después de leer “sin revocación” y antes de reanudar. | §2.8 requiere Gate CAS anclado y admite explícitamente que política de primera instrucción necesita primitiva SO; sigue bloqueante si falta. |
| N-28 | PARTIALLY_CLOSED | Proceso creado suspendido carga módulos después; CPU/E/S cero no prueba nunca ejecutó. | §2.3/2.8 limita clausura estática y exige observación del SO; dynamic loads y primera instrucción quedan `UNRESOLVED` si no observables. |
| N-29 | PARTIALLY_CLOSED | Lanzador/supervisor se autocertificaba `CLOSED_NO_EFFECT` pese a regla que lo prohíbe. | §2.5 separa ProcessLauncher y OSExecutionObserver; prueba independiente real no demostrada. |
| N-30 | CLOSED | Propietario firmaba digest opaco sin comprender contenido ni secreto incrustado. | §2.6 ContentReviewPackage acotado, contenidos y límites revisables; clasificación/scan no prueba ausencia de secretos. |
| N-31 | CLOSED | Autorización final no tenía estado después de que preflight produce huellas. | `PREFLIGHT_PASSED → EXECUTION_AUTHORIZED`; revisable documentalmente, no implementación. |
| N-32 | PARTIALLY_CLOSED | No había principal/ACL que abriese contenido exacto por handles sin cruzar ruta protegida. | §2.5/2.6 SourceHandleBroker y principals definidos; OS ACL/handles no identificados localmente. |
| N-33 | PARTIALLY_CLOSED | Root of roots, testigo, ledger, colector y tiempo sin pinning/rotación/quórum. | §2.3 tabla ampliada; root ultimate remains `UNRESOLVED` si no existe preexistente. |
| N-34 | PARTIALLY_CLOSED | Propietario único no puede autorizar y aceptar/reconciliar su propio intento; flujo queda atascado. | §2.5/2.8 lo reconoce como bloqueo deliberado, sin aceptación automática. |
| N-35 | CLOSED | TLS impedía observar payload, pero UNKNOWN podía aceptarse sin cota completa; faltaban inputs de cliente. | §2.5/2.7 define cota completa; auth broker/egress enforcement no identificado y bloquearían. |
| N-36 | CLOSED | Lease/check de fuente no identificaba renovador, fuente de tiempo o suspensión. | §2.3/2.8 nombra componentes/condiciones; existencia/latencia siguen no demostradas. |
| N-37 | CLOSED | Parser de bytes hostiles y firmante/renderer demasiado acoplados. | §2.7 separa hash verifier, parser, signer, renderer y owner approval channel; todas raíces/capabilities propuestos. |
| N-38 | PARTIALLY_CLOSED | `resource_lock_status`/dominio sin transiciones ni recuperación fiable tras rollback. | §2.8 tablas ampliadas y recuperación con tombstones; anchor registry rollback remains root blocker. |
| N-39 | PARTIALLY_CLOSED | Condiciones necesarias podrían ser incompatibles bajo no gasto/auth nueva, cliente/hijos, exclusividad y aceptador independiente. | §2.12 clasifica conjunciones bloqueadas/condicionadas; el entorno no se declara satisfacible. |
| N-40 | PARTIALLY_CLOSED | Vocabulario y estados duplicados; `CONSUMED`, waiver y bloqueos sin semántica única. | §2.8 prefijos y estados separados; revisar todas las transiciones cruzadas. |
| N-41 | CLOSED | Historial no reflejaba estados exactos anteriores. | §2.14 conserva los estados reportados e informa límites de procedencia; no se atesta el informe de Claude. |
| N-42 | PARTIALLY_CLOSED | Testigo podía preparar head 7 mientras el ancla seguía en head 6; restaurar el testigo a 6 podía permitir reusar nonce. | §2.8 separa el root humano del log operativo; si no hay log antirregresión por operación ya disponible, el sistema queda bloqueado. |
| N-43 | PARTIALLY_CLOSED | Pausa entre GateResumeCAS y ResumeProcess podía pasar expires_at o max latency. | §2.8 exige primitiva SO/time/latency; `GATE_TO_FIRST_INSTRUCTION` explícitamente `UNRESOLVED` sin ella. |
| N-44 | PARTIALLY_CLOSED | Reserva abortada sin proceso no podía probar `CLOSED_NO_EFFECT`; pruebas asumían proceso suspendido. | §2.8 distingue no proceso creado y creado suspendido; solo OS observer independiente puede acreditar. |
| N-45 | PARTIALLY_CLOSED | Respuesta perdida de ReserveCAS podía bloquear dominio de forma excesiva o permitir retry ambiguo. | §2.8 añade consulta read-only idempotente a la misma autoridad; pérdida transitoria no produce nuevo dispatch ni por sí sola rollback; divergencia sí bloquea dominio. |
| N-46 | PARTIALLY_CLOSED | Faltaban principals/escritores de CAS, revocación, ledger, ancla, lease, divulgación y roots. | §2.3/2.5/2.8 nombra capacidades, pero el pinning/custodia real sigue no demostrado. |
| N-47 | PARTIALLY_CLOSED | Owner Review Package no tenía constructor, límites, canonicalización versionada ni colisiones definidas. | §2.3/2.6 define paquete, límites/algoritmos/colisiones; capacidad presente no verificada. |
| N-48 | PARTIALLY_CLOSED | Handles exigidos sin principal que los abriera de forma acotada. | §2.5/2.6 define `SourceHandleBroker`, pero solo sirve si una ACL/capacidad de SO preexistente ya niega roots protegidas; no se cambian ACL y, si falta, se bloquea. |
| N-49 | PARTIALLY_CLOSED | Autorizaciones de inventario/materialización/preflight llamadas “un solo uso” sin consumo anti-replay propio. | §2.3/2.8 `AuthorizationUseRecord` por clase; mecanismo no demostrado. |
| N-50 | PARTIALLY_CLOSED | Restaurar TrustAnchorRegistry podía revivir root revocada y borrar bloqueo. | §2.3/2.8 root-de-roots independiente; si no existe, `GOVERNANCE_DOMAIN_BLOCKED` sin recuperación. |
| N-51 | CLOSED | Estados del dominio no tenían tabla completa/activación post recovery. | §2.8 añade transiciones explícitas; integridad real de marcador sigue no probada. |
| N-52 | PARTIALLY_CLOSED | `CODEX_HOME` podía contener instrucciones privadas no incluidas en revisión pero enviadas al servicio. | §2.5/2.6 requiere revisar entradas exactas legibles o denegarlas. |
| N-53 | CLOSED | Credenciales denegadas y a la vez necesarias para cliente; cota imposible si cliente las lee. | §2.5/2.7 exige mediación preexistente separada; si no existe, `BLOCKED_UNDER_CURRENT_CONSTRAINTS`. |
| N-54 | CLOSED | Salida de descendiente podía acceder a datos fuera de snapshot y luego ser transmitida al modelo. | §2.5 cierra FS/env/network de hijos y mete stdout/stderr/eventos en disclosure bound; enforcement real no demostrado. |
| N-55 | CLOSED | Observer de divulgación observa pero no impone destinos; endpoint alternate/telemetría sin límite. | §2.5 requiere `NetworkEgressEnforcer`; no identificado, así que no despacho. |
| N-56 | CLOSED | Fingerprint “efectiva” venía de inspector que solo lee archivos y no ejecuta el resolvedor. | §2.3 renombra a `declared_policy_inputs_digest`; efectiva es `UNKNOWN` salvo observación independiente, con frontera/waiver requeridos. |
| N-57 | PARTIALLY_CLOSED | Supervisor/lanzador firmaba que no ejecutó; colector no puede observar instrucciones, red o hijos. | §2.5/2.8 separa OSExecutionObserver del ProcessLauncher; sin observador independiente no hay CLOSED_NO_EFFECT. |
| N-58 | CLOSED | Lease/detector de suspensión no identificados; loader dinámico no puede sellarse solo con inventario previo. | §2.3/2.8 mantiene esas capacidades `UNRESOLVED`; no se afirma cierre por listas estáticas. |
| N-59 | PARTIALLY_CLOSED | Recibo dependía del digest que declaraba parser comprometible. | §2.7 añade `ReceiptDigestVerifier` que re-hash-ea bytes inmutables independientemente; atestación/raíz siguen propuestos. |
| N-60 | PARTIALLY_CLOSED | Renderer podía mostrar vista distinta del objeto que el firmante sellaba. | §2.3/2.7 liga object digest + review-view digest + renderer version en la firma; canal exacto sigue no demostrado. |
| N-61 | PARTIALLY_CLOSED | Estados/tokens repetidos entre dimensiones y combinaciones legales no definidas. | §2.8 usa tokens por dimensión; revisar que no persista combinación inconsistente entre reserva/intento/locks. |
| N-62 | PARTIALLY_CLOSED | Propietario único sin aceptador/reconciliador/liberador independiente dejaba locks permanentes. | §2.5/2.8 acepta el bloqueo potencialmente indefinido y no inventa acto alterno. |
| N-63 | PARTIALLY_CLOSED | Registro de satisfacibilidad enumeraba condiciones, pero no definía alcance/gastos/auth/conjunciones. | §2.12 añade taxonomía, prerrequisitos, dependencias y conjunciones bloqueantes; validar cobertura completa. |
| N-64 | CLOSED | v5 se decía autocontenido pero remitía a conversación/Entries y un resumen de transacción no reflejaba dos almacenes. | §2.2 conserva las filas públicas como `CLAUDE_REPORTED_PUBLIC_SOURCE`; §2.8 define el log operacional preexistente y el ledger como proyección. Las afirmaciones de fuente siguen sin verificarse. |

`CLAUDE_REPORTED_PUBLIC_SOURCE` se mantiene como afirmación reportada; esta revisión no vuelve a consultar ni verifica el código público. Los informes locales permanecen `OWNER_REPORTED`. Ninguna corrección de texto acredita existencia de root, testigo, anchor, ACL, watcher, egress enforcer, collector, signer o consumer.

| N-65 | NEW — HIGH | Custodia offline no puede atestiguar cada reserva; sin log operativo no-rollback preexistente, una restauración puede revivir nonce/head. | Se separan log operativo y raíz humana; si el log preexistente con CAS/anti-rollback no puede demostrarse, `BLOCKED_UNDER_CURRENT_CONSTRAINTS`; no se simulan dos commits. |
| N-66 | NEW — HIGH | `ContentReviewBuilder` requería leer `CODEX_HOME` antes de una autorización que no existía; podía abrir credenciales. | `ClientInputReviewAuthorization` separada y lista exacta de inputs no secretos; builder solo procesa snapshot autorizado; credenciales excluidas y bloqueo si no puede separarse. |
| N-67 | NEW — HIGH | Parser podía omitir un archivo/ADS del manifiesto y el verificador rehash-ear solo la lista declarada. | `SnapshotInventoryVerifier` enumera independientemente todo el namespace; si su API no demuestra cobertura total de entradas/streams, `ARTIFACT_UNVERIFIED`. |
| N-68 | NEW — MEDIUM | Ningún componente recalculaba independientemente el diff; el colector podía omitir hunks y hashear su propio resultado. | `SnapshotDiffVerifier` recalcula diff de baseline/candidato inmutables con algoritmo byte-oriented versionado, sin Git/hooks/config del candidato. |
| N-69 | NEW — HIGH | Observador caído/pérdida de eventos podía dejar log vacío y atestiguar que no hubo creación. | `CLOSED_NO_EFFECT` requiere secuencia/heartbeat/cobertura continua; cualquier gap causa `ATTEMPT_UNKNOWN` y retención de locks. |
| N-70 | NEW — HIGH | La matriz no autorizaba actor de revocación ni de terminación, pese a exigir parada en vuelo. | `RevocationAuthority` y `ProcessTreeTerminator` quedan nombrados y separados del launcher; si no preexisten con raíz/latencia, `BLOCKED_UNDER_CURRENT_CONSTRAINTS`. |
| N-71 | NEW — MEDIUM-HIGH | ACL deny-by-default contradice no modificar ACL si el broker no tiene identidad/handles preexistentes aislados de roots protegidas. | No crear usuarios/ACL/servicios; usar solo capacidad SO preexistente que ya deniegue roots protegidas; si falta, bloquea inventario/materialización. |
| N-72 | NEW — MEDIUM-HIGH | El canal de firma podía verificar digests recibidos sin probar que la vista humana fuese la del objeto firmado. | `TrustedOwnerReviewChannel` deriva vista/digests desde bytes inmutables y los muestra por canal confiable; sin ese canal preexistente, aprobación bloqueada. |
| N-73 | NEW — MEDIUM | `RESERVATION_ABORTED`, estados de reserva/uso/launch y locks tenían semántica cruzada ambigua. | El token ambiguo se elimina: `RESERVATION_NOT_COMMITTED` solo si la autoridad prueba no-commit; después de commit la reserva permanece confirmada y el nonce quemado, aunque no haya spawn. Tablas e invariantes por dimensión y liberación solo por `ResourceReleaseRecord`. |
| N-74 | NEW — MEDIUM | Propietario único y quórum/actos incompatibles podían hacer inalcanzables pinning, recuperación, aceptación y liberación. | Matriz de incompatibilidades y mínimos humanos por ruta; sin humanos autenticados preexistentes requeridos, `PENDING_OWNER`/locks permanecen. |
| N-75 | NEW — MEDIUM | Se pretendía aprobar un path_manifest derivado antes de autorizar inventario capaz de producirlo. | Secuencia scope de inventario aprobado → enumeración de metadata → aprobación de path_manifest → autorización de lectura/copia → aprobación de content_manifest. |
| N-76 | NEW — MEDIUM | Registro de satisfacibilidad tenía tres columnas pese a exigir siete campos y usaba «capacidad preexistente» como escape universal. | Tabla de siete campos por requisito y conjunciones bloqueantes explícitas; ninguna capacidad se presume existente ni una incógnita se etiqueta satisfecha. |
| N-77 | NEW — MEDIUM-LOW | La cota de divulgación mezclaba bytes payload con credenciales/cabeceras, sin límites claros por canal. | `disclosure_upper_bound` distingue fuentes/canales/endpoint/tamaño máximo y clase opaca de transporte-auth; sin aislamiento/cota completa, bloqueo. |
| N-78 | NEW — LOW | Resumen de estado final omitía principales, capabilities y disponibilidad de humanos implicados. | §2.15 añade lector/constructor/observador/terminador/revocador/verificadores/canal humano y estados bloqueantes. |
| N-79 | NEW — MEDIUM | Política sobre expiración/primera instrucción dejaba como alternativa indefinida un check post hoc. | Se elige explícitamente política A: deadline exigible por SO antes de primera instrucción; revocación posterior requiere terminador con max_stop_latency; si falta mecanismo, no hay despacho. |

#### Detalle de hallazgos N65–N79 reportados en la sexta revisión

Estos hallazgos se reproducen como material de auditoría reportado; no son verificaciones del coordinador ni pruebas de implementación. Esta frase pertenece al informe histórico v7. La octava revisión debe contrastar cada base/contraejemplo con el texto exacto de v8, no con un resumen ni con memoria conversacional.

**N65 — HIGH — Antirregresión por operación frente a custodia offline.** Base reportada: la custodia offline solo fija checkpoints, mientras la reserva necesita actualizar nonce/head por operación. Contraejemplo: el testigo se restaura a un snapshot posterior al último checkpoint pero anterior a la reserva; el nonce aparece libre. Si se usa un servicio online nuevo para cada operación, se viola la restricción de no crear servicio. Consecuencia: se puede reutilizar una autorización o hay dos dominios de commit no atómicos. Corrección propuesta: log de reservas no restaurable en un dominio independiente y custodia humana solo para época/raíces; sin el log preexistente, `BLOCKED_UNDER_CURRENT_CONSTRAINTS`. Criterio futuro: rollback a una cabeza anterior bloquea antes de cualquier segundo despacho.

**N66 — HIGH — Autoridad circular de lectura de `CODEX_HOME`/entorno.** Base reportada: el `ContentReviewPackage` contiene entradas de config/instrucción; el builder parte de bytes aprobados, pero no hay autoridad anterior a preflight para leer esas entradas. Contraejemplo: para formar el paquete se lee `~/.codex`, que puede contener `auth.json`; ningún permiso cubre la lectura. Consecuencia: acceso sin autorización y posible lectura de credenciales. Corrección: autorización propia con rutas exactas, handle, principal, salida acotada y `AuthorizationUseRecord`; prohibición expresa para el builder de abrir las rutas. Criterio futuro: ninguna lectura previa a aprobación sin autorización/handle específico, probado solo con señuelos.

**N67 — HIGH — Completitud del verificador de hashes.** Base reportada: el verifier recalculaba hashes de entradas que recibía, sin enumeración independiente demostrada. Contraejemplo: un parser omite un archivo M del manifiesto y el verifier recalcula solo lo listado; el snapshot aún contiene M. Consecuencia: `ARTIFACT_VERIFIED` pese a archivo omitido. Corrección: enumerar independientemente el almacén/snapshot sellado, contar entries/streams/bytes y recalcular la raíz sobre todo el namespace. Criterio futuro: entrada extra, archivo oculto o ADS no soportado produce `ARTIFACT_UNVERIFIED`.

**N68 — MEDIUM — Autoridad del diff.** Base reportada: se guardaba el hash del diff sin asignar quién lo recalcula. Contraejemplo: el colector omite hunks y luego el verifier confirma el hash de ese diff parcial. Consecuencia: artefacto íntegro pero diff incompleto. Corrección: `SnapshotDiffVerifier` independiente recalcula diff entre baseline y candidato inmutables con algoritmo versionado byte-oriented. Criterio futuro: diff falsificado/parcial no coincide con el recálculo y bloquea.

**N69 — HIGH — Evidencia de ausencia en `CLOSED_NO_EFFECT`.** Base reportada: un observador puede afirmar ausencia de creación durante toda la ventana. Contraejemplo: el observador cae o pierde eventos y deja un log vacío aunque el proceso fue creado. Consecuencia: cierre sin efecto falso y liberación indebida de locks. Corrección: cobertura demostrable sin huecos mediante secuencia autenticada y heartbeat/contador de salud durante toda la ventana; una intención debe corresponder a creación observada o no-creación explícita con cobertura continua. Criterio futuro: matar/pausear el observador genera `ATTEMPT_UNKNOWN`.

**N70 — HIGH — Falta principal de terminación y revocación.** Base reportada: el contrato exigía parada en vuelo pero no asignaba permiso a ningún principal; launcher/verifier/observer tenían prohibida esa tarea. Contraejemplo: se revoca después del gate y nadie puede terminar el árbol sin que el launcher controle su propia evidencia. Consecuencia: fail-closed enunciado pero no ejecutable. Corrección: `RevocationAuthority` y `ProcessTreeTerminator`, identidades/ACL/raíz/canal/latencias definidos, separados del launcher y del observador. Criterio futuro: revocación causa parada medida dentro de límite. Si no preexisten, bloqueo.

**N71 — MEDIUM-HIGH — ACL del broker frente a no modificar la fuente.** Base reportada: el broker necesita ACL deny-by-default pero no se permiten cambios de ACL; el mismo principal podría tener acceso general. Contraejemplo: principal restringido no puede leer solo paths permitidos sin concederle ACL nuevas, y principal propietario amplio no logra enforcement real por código solamente. Consecuencia: o se viola la restricción o no hay aislamiento. Corrección: usar únicamente una identidad/capacidad/handle de SO preexistente con ACL ya correctas; no cambiar ACL; de no existir, bloquear inventario/materialización. Criterio futuro: ruta protegida permanece inaccesible al principal sin cambiar la fuente.

**N72 — MEDIUM-HIGH — Vista humana no ligada a los bytes firmados.** Base reportada: la interfaz comprueba digests recibidos pero el renderer del host compone la vista. Contraejemplo: el renderer muestra texto benigno y entrega los digests de otra vista; el canal de firma solo comprueba consistencia. Consecuencia: el propietario firma un objeto que no vio. Corrección: canal/dispositivo confiable preexistente deriva y muestra su propia vista de los bytes inmutables, recalcula `object_digest` y `review_view_digest` y firma esa vista exacta. Criterio futuro: renderer host manipulado no puede mostrar un objeto diferente sin que la firma se bloquee; sin canal previo, aprobación bloqueada.

**N73 — MEDIUM — Inconsistencia de máquinas de estado.** Base reportada: `RESERVATION_ABORTED` podía indicar no-commit y también cancelación tras commit; faltaban transiciones y locks cruzados. Contraejemplo: reserva ya comprometida, proceso no creado, evento de no-efecto; un lector deriva “nonce consumido” y otro “sin commit”. Consecuencia: reutilización de nonce o liberación incorrecta. Corrección: estados separados para no-commit autoritativo, commit confirmado y commit desconocido; el intento cancelado post-commit conserva nonce consumido y lock. Añadir tablas/eventos por dimensión e invariantes. Criterio futuro: cada estado final identifica inequívocamente consumo y lock.

**N74 — MEDIUM — Actos incompatibles y número mínimo de humanos.** Base reportada: propietario no puede aceptar/reconciliar/liberar su intento, y pinning/recuperación requieren quórum; no había matriz acto×acto. Contraejemplo: con dos humanos, uno autoriza y otro acepta, pero tras incidente se necesita un reconciliador distinto de ambos; un solo propietario tampoco satisface pinning/recuperación. Consecuencia: flujo permanentemente bloqueado, no solo aceptación. Corrección: matriz de incompatibilidades y número mínimo de humanos por flujo normal, incidente y recuperación; declarar `BLOCKED_UNDER_CURRENT_CONSTRAINTS` donde el quórum no existe. Criterio futuro: ningún mandato combina actos prohibidos.

**N75 — MEDIUM — Orden de `path_manifest` e inventario.** Base reportada: una cláusula exigía aprobar el manifiesto antes de inventario, otra lo derivaba del inventario. Contraejemplo: el manifiesto de rutas no puede aprobarse antes de enumerar las rutas si la lista la construye el inventario. Consecuencia: alcance de enumeración sin autorización. Corrección: autorización previa del scope de inventario, enumeración acotada de metadata, aprobación del `path_manifest` derivado, autorización posterior de lectura/materialización y aprobación de `content_manifest`. Criterio futuro: cada operación corresponde a su autorización específica.

**N76 — MEDIUM — Registro de satisfacibilidad incompleto.** Base reportada: la definición exigía siete campos, pero la tabla solo tenía tres y omitía bloqueos reales. Contraejemplo: capacidad necesaria depende de nueva identidad/credencial, pero la fila dice “propuesta” o “salvo capacidad preexistente”. Consecuencia: incógnita e incompatibilidad se mezclan. Corrección: siete campos por requisito y listado explícito de combinaciones bloqueadas N65/N70/N71/N74, con la prueba concreta que permitiría cambiar el estado. Criterio futuro: toda fila contiene alcance, prerrequisitos, dependencia, evidencia, contradicción, autoridad y estado/razón.

**N77 — MEDIUM-LOW — Cota de divulgación por canal.** Base reportada: la cota incluía todo lo serializable, pero excluía credenciales/cabeceras del payload sin una categoría alternativa suficiente. Contraejemplo: credenciales y headers son transmitidos por el cliente, pero no pueden inspeccionarse ni aprobarse como contenido. Consecuencia: cota “completa” que omite parte del tráfico. Corrección: conjuntos de fuentes + transformaciones + canal + endpoint/protocolo + límites máximos por canal; autenticación como clase opaca separada, aislada de modelo e hijos. Criterio futuro: cualquier canal/endpoint fuera de la cota bloquea.

**N78 — LOW — Estado final incompleto.** Base reportada: el resumen no nombraba todos los componentes implicados en terminación/revocación/lease/suspensión o disponibilidad humana. Consecuencia: lectores pueden tratar una capacidad ausente como si no fuera requisito. Corrección: enumerar todos los principales y capacidades en §2.15, incluyendo su estado real (`PROPOSED`, `UNRESOLVED` o bloqueado). Criterio futuro: todo componente nombrado en el contrato aparece en la matriz y el estado final.

**N79 — MEDIUM — Política de primera instrucción ambigua.** Base reportada: una cláusula condicionaba la política a impedir primera instrucción tardía y otra parecía permitir terminación posterior. Contraejemplo: se compromete gate en plazo, el proceso se reanuda una hora tarde y luego termina; no está claro si la primera instrucción tardía invalida el intento. Consecuencia: autorización fuera de vigencia. Corrección: fijar una política normativa; v7 elige A: el SO impide primera instrucción fuera de deadline y la parada posterior por revocación es requisito adicional. Criterio futuro: sin enforcement físico y valores finitos aprobados, no hay despacho.

#### N-80–N-84 — defectos reportados en la séptima revisión; reparación propuesta en v8

**Procedencia:** el informe de séptima revisión entregado por el propietario (`OWNER_REPORTED`; SHA-256 `2d987c533c0bc9ba02b5f981ee0ff2a8d58ef9c39a60b6a6e2d89917930c2cb9`). El coordinador cotejó el texto contra v7; los hallazgos nuevos se conservan como `PROPOSED` hasta la octava revisión. No deben marcarse `CLOSED` por su mera incorporación.

**N-80 — MEDIUM — Consistencia linealizable entre autorización consumida y uso.** Base reportada: §2.8 define dimensiones separadas y el invariante actual solo prohíbe `CONSUMED → AUTHORIZED`. Contraejemplo: una lectura independiente/proyección observa `authorization_status=CONSUMED` pero `authorization_use_status=USE_NOT_STARTED`, permitiendo que un actor que consulte solo la segunda dimensión intente un segundo uso. Consecuencia: carrera y posible reutilización. Corrección v8: el mismo evento atómico/linealizable compromete `CONSUMED`, `USE_COMMITTED`, `AuthorizationUseRecord`, locks y head; `CONSUMED` es incompatible con `USE_REJECTED_PRECOMMIT`; una proyección desigual nunca decide y la inconsistencia bloquea. Criterio futuro: las consultas concurrentes bajo la misma clase/ID/head no pueden autorizar un uso adicional; cualquier split/contradicción bloquea y pone el dominio en revisión.

**N-81 — MEDIUM — Expiración después de `GATE_RESUME_COMMITTED` sin primera instrucción.** Base reportada: §2.8 no asignaba resultado explícito a la expiración sin reanudación o entre reanudación y primera instrucción. Corrección v8: estados/ramas explícitas `GATE_RESUME_DEADLINE_EXPIRED`, `FIRST_INSTRUCTION_DEADLINE_EXPIRED` y `FIRST_INSTRUCTION_OBSERVED_LATE`, con asignación a attempt/incident/lock. `CLOSED_NO_EFFECT` requiere cobertura, no-user-code, terminación cuando aplique y recibo de liberación; la instrucción tardía abre incidente y cuarentena. Criterio futuro: cada una de las tres ramas tiene un único resultado admisible y nunca libera por expiración sola.

**N-82 — MEDIUM-LOW — Proyección ledger como fallback.** Base reportada: §2.3/§2.8 ya describen al `LedgerProjector` como proyección sin autoridad y bloquean nuevos despachos si el log no responde; el hallazgo es una aclaración defensiva, no prueba de que la vía alternativa exista. Corrección v8: prohibición inequívoca de usar una proyección en cualquier decisión de nonce, gate, reserva o lock cuando la autoridad no responde; timeout lleva a `DOMAIN_BLOCKED_PENDING` y estados unknown, rollback/divergencia probados a `GOVERNANCE_DOMAIN_BLOCKED`. Criterio futuro: la indisponibilidad del log jamás produce fallback ni nuevo despacho.

**N-83 — LOW — Scopes solapados entre clases de autorización.** Base reportada: §2.6 define el orden correcto y §2.8 registra clases separadas, pero no prohíbe expresamente que un scope subconjunto se interprete como sustituto del paso anterior. Corrección v8: ninguna igualdad/intersección/subconjunto transfiere autoridad ni `AuthorizationUseRecord` entre clases; se exige la cadena aplicable por intento/ID. Criterio futuro: materialización sin la autorización de inventario requerida queda bloqueada antes de cualquier efecto.

**N-84 — MEDIUM — `USE_UNKNOWN` tras restauración del log.** Base reportada: v7 ya requiere una autoridad `NonRollbackReservationLog` resistente a restore y bloquea si no se puede demostrar, por lo que N-84 es interdependiente de N-65 y no acredita por sí solo un segundo defecto arquitectónico independiente. El riesgo residual es que una respuesta aparente `USE_NOT_STARTED` tras perder/restaurar historia se trate como prueba de no-uso. Corrección v8: ausencia no basta; exige cabeza/época coherente y garantía antirregresión del mismo log; evento previamente confirmado que desaparece/retrocede produce bloqueo; sin evidencia anti-restore admisible, el log no es elegible y no hay despacho. No se crea un segundo anclaje por operación. Criterio futuro: no existe transición a `USE_REJECTED_PRECOMMIT` tras duda/regresión, y una restauración demostrada bloquea el dominio antes de cualquier segundo despacho.


### Delta de diseño v7 (histórico, preservado)

1. Se separa la raíz humana/offline para pinning/rotación de una autoridad operacional antirregresión por reserva. Solo una capacidad `NonRollbackReservationLog` preexistente que haga CAS/append atómico, idempotente y resistente a restore permite despacho; si no existe o no se puede demostrar, `BLOCKED_UNDER_CURRENT_CONSTRAINTS`.
2. `ClientInputReviewAuthorization` antecede a cualquier lectura de inputs no secretos de `CODEX_HOME`/entorno; `ContentReviewBuilder` no abre esos recursos por autoridad propia. Credenciales, keyrings, tokens y sesiones quedan fuera de la allowlist.
3. La secuencia de fuente se fija: autorización de scope de inventario → enumeración limitada de metadata → aprobación de `path_manifest` → autorización de copia → manifiestos de contenido → revisión de contenido real. No se cambian ACL; si no hay una capacidad SO preexistente de handles/ACL, se bloquea.
4. `SnapshotInventoryVerifier` enumera independientemente el snapshot completo y `SnapshotDiffVerifier` recalcula diff desde snapshots inmutables. El parser no decide completitud ni autoridad del diff.
5. `CLOSED_NO_EFFECT` requiere cobertura de observación sin huecos y una fuente independiente de SO; cualquier pérdida de evento/heartbeat produce `UNKNOWN`. Launcher y terminator no autocertifican.
6. La matriz añade `RevocationAuthority`, `ProcessTreeTerminator`, canal confiable de firma/vista y mínimos humanos por ruta. Si esos principales/capacidades no preexisten bajo restricciones, no se despacha ni se libera.
7. Se elige la política estricta A para la primera instrucción: el SO debe imponer el deadline físico. La parada acotada tras revocación es una condición adicional, no sustituto. Los valores temporales deben ser finitos y firmados antes de autorización.
8. El registro de satisfacibilidad contiene siete campos por requisito, nombra la evidencia preexistente concreta que falta y distingue `UNRESOLVED` de `BLOCKED_UNDER_CURRENT_CONSTRAINTS` y de incompatibilidad lógica. No se infiere ninguna relajación por el propietario.

### Delta de diseño v8 — reparaciones focalizadas propuestas

1. `authorization_status=CONSUMED` y `authorization_use_status=USE_COMMITTED` se comprometen en el mismo evento atómico/linealizable por clase e ID; una proyección contradictoria no decide y bloquea.
2. Se especifican los branches `GATE_RESUME_DEADLINE_EXPIRED`, `FIRST_INSTRUCTION_DEADLINE_EXPIRED`, `FIRST_INSTRUCTION_OBSERVED_LATE` y `TERMINATED_BEFORE_FIRST_INSTRUCTION`, con mapeo conservador a `ATTEMPT_UNKNOWN`, `ATTEMPT_QUARANTINED` o `CLOSED_NO_EFFECT` solo con evidencia completa y liberación válida.
3. Se prohíbe el `LedgerProjector` como fallback operacional y se distingue la espera `DOMAIN_BLOCKED_PENDING` del bloqueo de dominio por rollback/divergencia demostrados.
4. Scopes de autorización iguales, solapados o anidados no sustituyen clases distintas ni permiten omitir el orden de §2.6.
5. N-84 se trata como condición interdependiente de N-65: una ausencia aparente de uso tras duda de restore no es no-uso; sin garantía admisible anti-restore del mismo log no hay despacho y no se inventa un segundo anclaje por operación.
6. El registro de satisfacibilidad usa cuatro estados lógicos (`SATISFIABLE`, `CONDITIONALLY_SATISFIABLE`, `BLOCKED_BY_CURRENT_CONSTRAINTS`, `UNRESOLVED`) y separa el bloqueo operativo `BLOCKED_UNDER_CURRENT_CONSTRAINTS`; conserva siete campos y una dependencia explícita de decisión del propietario.

**Estado histórico al cerrar v8:** estos cambios eran `PROPOSED / PENDING_EIGHTH_REVIEW`; el informe de octava revisión aportado reportó `PASS_WITH_REPAIRS`, pero sigue `OWNER_REPORTED` y no constituyó aceptación formal ni evidencia de implementación.

#### N-85–N-87 — residuales de octava revisión; reparaciones propuestas en v9

**Procedencia:** mapeo del informe de octava revisión aportado por el propietario (`OWNER_REPORTED`) a las cláusulas exactas del v8. Son reparaciones de explicitud documental; no prueban que el control exista o funcione.

**N-85 — CLARIFICATION / reported MEDIUM, gap not independently confirmed — Projection `USE_COMMITTED` without authority response.** Base reportada: F-V8-01. No se confirma que v8 dejara indefinido el resultado: §2.8, párrafo de indisponibilidad del log, ya prescribe `USE_UNKNOWN` + `DOMAIN_BLOCKED_PENDING`, prohíbe usar el ledger como suplente y dispone que esos estados no se liberen por proyección. La frase añadida dentro de N-80 es una aclaración defensiva local, no prueba de un defecto semántico nuevo. Resultado exigido ya en v8: sin respuesta autoritativa, no despacho y lock retenido. Criterio futuro: Claude/Sonnet debe determinar si la redacción v8 era suficiente; si sí, clasificar F-V8-01 como `ALREADY_COVERED / OPTIONAL_CLARIFICATION`, no como defecto abierto.

**N-86 — CLARIFICATION / reported LOW, gap not independently confirmed — Manual-list branch summary in N-83.** Base reportada: F-V8-03. §2.6 paso 3 ya permite `path_manifest` manual exacto sin inventario y N-83 limita la regla a un predecesor “aplicable” conforme a §2.6; por tanto, el informe no demuestra una contradicción del contrato, solo una posible pérdida de claridad para quien lea el invariante aislado. La frase añadida remite expresamente a la rama manual, pero es aclaración defensiva, no prueba de un defecto semántico nuevo. Criterio futuro: evaluar si la referencia explícita a §2.6 es suficiente; si la cláusula previa ya excluye la interpretación indebida, clasificar F-V8-03 como `ALREADY_COVERED / OPTIONAL_CLARIFICATION`.

**N-87 — LOW — Evidencia especificada insuficientemente en fila de exclusividad.** Base reportada: F-V8-04. v9 exige que cualquier afirmación de lock/lease preexistente identifique servicio/cuenta y mecanismo impuesto, scope/canales cubiertos, identificador/estado observable, vigencia/epoch cuando aplique y artefacto documental/evento admisible. Ninguna capacidad se presume existente; si no hay evidencia admisible preexistente, el gate sigue bloqueado. Criterio futuro: una revisión estática puede identificar qué evidencia aceptaría el contrato sin consultar servicios, autenticar, crear recursos o gastar.

**F-V8-02 — arista supuestamente ausente (no adoptada):** el informe octavo afirmó que faltaba `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE`, pero el v8 exacto ya contenía esa fila en la tabla formal de transiciones de §2.8. Esta afirmación queda `CONTRADICTED_BY_V8_SOURCE`; no se crea un N adicional ni se duplica una fila ya existente. La novena revisión debe verificar esta decisión contra v9 y no heredarla automáticamente.


### Delta de diseño v9 — aclaraciones focalizadas propuestas

1. N-80 repite de forma local la regla ya prescrita en §2.8 para la indisponibilidad de la autoridad: la proyección no confirma ni descarta uso y no libera locks. Esta frase es defensiva; no se presume que F-V8-01 pruebe una brecha real.
2. N-83 incorpora un recordatorio explícito de la ruta manual que §2.6 paso 3 ya permitía. Es claridad adicional, no una conclusión de que v8 prohibiera esa ruta.
3. §2.12 nombra los elementos mínimos de evidencia admisible para una capacidad preexistente de lock/lease impuesto por el servicio que abarque uso manual y automático, sin presuponer su existencia ni autorizar consultas para descubrirla. Este es el único defecto nuevo que se trata como carencia concreta de especificación en esta reconciliación.
4. F-V8-02 no se repara ni se duplica: la arista reclamada como ausente ya existe en v8 exacto y queda registrada como afirmación no confirmada por la fuente.
5. N-85/N-86 son aclaraciones opcionales `PROPOSED / PENDING_NINTH_REVIEW`; N-87 es la reparación propuesta a una carencia de especificación de evidencia. Ningún cambio es evidencia de implementación, de capacidad preexistente ni de desbloqueo.

### 2.15 Estado final de la propuesta v9

- `DOCUMENT_STATUS = PROPOSED_DESIGN_V9`.
- `SEMANTIC_ACCEPTANCE = NOT_ESTABLISHED`.
- `SATISFIABILITY_AS_A_WHOLE = BLOCKED_BY_CURRENT_CONSTRAINTS`; `IMPLEMENTABILITY_EVIDENCE = NOT_DEMONSTRATED`. Un estado global bloqueado no demuestra imposibilidad lógica de cada fila, pero la conjunción operativa no puede avanzar mientras persistan requisitos bloqueantes o no demostrados.
- `GOVERNANCE = KEEP_BLOCKED`.
- `BRIDGE_NOT_READY`.
- `IMPLEMENTATION = NOT_AUTHORIZED`.
- `LOCAL_PREFLIGHT = NOT_AUTHORIZED_BY_THIS_TASK`.
- `SOURCE_INVENTORY = NOT_AUTHORIZED_BY_THIS_TASK`.
- `CLIENT_INPUT_REVIEW = NOT_AUTHORIZED_BY_THIS_TASK`.
- `MATERIALIZATION = NOT_AUTHORIZED_BY_THIS_TASK`.
- `DEVELOPMENT_TURN = NOT_RUN`.
- `TESTS = NOT_RUN`.
- `BUILD = NOT_RUN`.
- `RUNTIME = NOT_RUN`.
- `CODEX_AUTHENTICATION_OR_USAGE = UNVERIFIED`.
- `NONROLLBACK_RESERVATION_LOG = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CAPABILITY_IS_EVIDENCED`.
- `RESERVATION_ATOMICITY_AND_ANTIROLLBACK = BLOCKED_UNDER_CURRENT_CONSTRAINTS`.
- `ROOT_OF_ROOTS_PINNING_ROTATION_AND_HUMAN_QUORUM = UNRESOLVED / BLOCKED_WHERE_QUORUM_IS_REQUIRED`.
- `CANDIDATE_EXECUTOR_CONFINEMENT = UNRESOLVED`.
- `CLIENT_DESCENDANT_SEPARATION = UNRESOLVED`.
- `PROCESS_TREE_TERMINATOR_AND_REVOCATION_AUTHORITY = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CAPABILITY_IS_EVIDENCED`.
- `KERNEL_RESUME_DEADLINE_ENFORCER = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CAPABILITY_IS_EVIDENCED`.
- `EXECUTOR_CHAIN_AND_DYNAMIC_LOADER_IDENTITY = UNRESOLVED`.
- `TRUSTED_TIME_AND_SUSPEND_RESUME_OBSERVER = UNRESOLVED`.
- `SOURCE_INVENTORY_AUTHORIZATION_AND_PATH_MANIFEST_ORDER = PROPOSED / NOT_TESTED`.
- `SOURCE_HANDLE_BROKER_AND_READ_AUTHORITY = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CAPABILITY_IS_EVIDENCED`.
- `CLIENT_INPUT_REVIEW_AUTHORIZATION = NOT_AUTHORIZED / NOT_TESTED`.
- `CLIENT_INPUT_MANIFEST_APPROVAL = PROPOSED / NOT_TESTED`.
- `PATH_MANIFEST_SOURCE_CONTENT_MANIFEST_CANDIDATE_CONTENT_MANIFEST = PROPOSED / NOT_TESTED`.
- `CONTENT_REVIEW_PACKAGE_AND_TRUSTED_OWNER_VIEW = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_CHANNEL_IS_EVIDENCED`.
- `CODEX_HOME_INPUTS_AND_AUTH_CREDENTIAL_ISOLATION = BLOCKED_UNDER_CURRENT_CONSTRAINTS_IF_NO_PREEXISTING_MEDIATION`.
- `DISCLOSURE_UPPER_BOUND_BY_CHANNEL = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_COMPLETE_BOUND_AND_PREEXISTING_EGRESS_ENFORCEMENT_ARE_EVIDENCED`.
- `DISCLOSURE_OBSERVED = UNKNOWN_UNLESS_INDEPENDENTLY_OBSERVABLE_AND_UPPER_BOUND_IS_COMPLETE`.
- `NETWORK_EGRESS_ENFORCEMENT = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_APPLICATOR_IS_EVIDENCED`.
- `SNAPSHOT_INDEPENDENT_ENUMERATION = PROPOSED / NOT_DEMONSTRATED`.
- `RECEIPT_DIGEST_VERIFIER = PROPOSED / NOT_DEMONSTRATED`.
- `SNAPSHOT_DIFF_VERIFIER = PROPOSED / NOT_DEMONSTRATED`.
- `RECEIPT_SIGNING_SERVICE_AND_ROOT = PROPOSED / NOT_DEMONSTRATED`.
- `OWNER_VIEW_RENDERER_AND_SIGNATURE_CHANNEL = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_PREEXISTING_TRUSTED_CHANNEL_IS_EVIDENCED`.
- `CLOSED_NO_EFFECT_EVIDENCE = BLOCKED_UNDER_CURRENT_CONSTRAINTS_IF_OBSERVER_COVERAGE_IS_UNPROVEN`.
- `RESOURCE_LOCK_STATUS_AND_CROSS_DIMENSION_INVARIANTS = PROPOSED / PENDING_NINTH_REVIEW; NOT_TESTED`.
- `N80_AUTHORIZATION_USE_LINEARIZABILITY = PROPOSED / PENDING_NINTH_REVIEW`.
- `N81_GATE_DEADLINE_EXPIRY_TRANSITIONS = PROPOSED / PENDING_NINTH_REVIEW`.
- `N82_LEDGER_PROJECTOR_NO_FALLBACK = PROPOSED / PENDING_NINTH_REVIEW`.
- `N83_AUTHORIZATION_CLASS_SCOPE_NON_SUBSTITUTION = PROPOSED / PENDING_NINTH_REVIEW`.
- `N84_RESTORE_AND_USE_UNKNOWN_RECONCILIATION = PROPOSED / PENDING_NINTH_REVIEW`.
- `SATISFIABILITY_TAXONOMY = PROPOSED / PENDING_NINTH_REVIEW`.
- `N85_PROJECTION_USE_COMMITTED_WITH_AUTHORITY_UNAVAILABLE = OPTIONAL_CLARIFICATION / PENDING_NINTH_REVIEW; V8_MAY_ALREADY_COVER_BEHAVIOR`.
- `N86_MANUAL_PATH_MANIFEST_BRANCH_CLARITY = OPTIONAL_CLARIFICATION / PENDING_NINTH_REVIEW; V8_MAY_ALREADY_COVER_BEHAVIOR`.
- `N87_SERVICE_SIDE_EXCLUSIVITY_EVIDENCE = PROPOSED / PENDING_NINTH_REVIEW`.
- `GOVERNANCE_DOMAIN_RECOVERY_AND_ROOT_REGISTRY_ANTIROLLBACK = BLOCKED_UNDER_CURRENT_CONSTRAINTS_WHERE_ROOT_OR_QUORUM_IS_UNAVAILABLE`.
- `ACCOUNT_EXCLUSIVITY_VS_EXTERNAL_ACTORS = BLOCKED_UNDER_CURRENT_CONSTRAINTS_UNTIL_A_PREEXISTING_SERVICE_SIDE_LOCK_IS_EVIDENCED`.
- `ZERO_SPEND_EVIDENCE = BLOCKED_UNDER_CURRENT_CONSTRAINTS_WITHOUT_PREEXISTING_ADMISSIBLE_SOURCE`.
- `HUMAN_AUTHORITY_MINIMUMS = BLOCKED_WHERE_REQUIRED_INDEPENDENT_HUMANS_ARE_UNAVAILABLE`.
- `ACCEPTANCE_WITH_SINGLE_OWNER = PENDING_OWNER / RESOURCE_LOCK_RETAINED`.
- `IABV_CONSUMER_IDENTITY_AND_VERIFICATION_SCOPE = UNRESOLVED`.
- `SATISFIABILITY_REGISTER = PROPOSED / PENDING_NINTH_REVIEW; SEVEN_FIELDS_REQUIRED; FOUR_STATE_TAXONOMY`.
- `LOCAL_SOURCE_HANDOFF_AND_GOVERNANCE_TARGET = UNRESOLVED`.

**Decisión vigente:** v9 es una propuesta documental derivada del v8 inmutable; no acepta el puente ni demuestra sus controles. No se cambia ninguna restricción de gasto, autenticación, acceso local, número de humanos o ejecución. El candidato v9 no se ha publicado en GitHub y no modifica el v8/v7 inmutable. N-85–N-87 permanecen `PROPOSED / PENDING_NINTH_REVIEW`; el informe de octava revisión y sus estados anteriores siguen siendo `OWNER_REPORTED` hasta adjudicación independiente. La arista `FIRST_INSTRUCTION_DEADLINE_EXPIRED → FIRST_INSTRUCTION_OBSERVED_LATE` ya constaba en v8 y no se incorpora como reparación nueva. Los bloqueos enumerados son condiciones de no avance, no autorizaciones para comprobarlos localmente. La decisión C sigue vigente.
