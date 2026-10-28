# UAAL — Contrato de diseño del ciclo de aprobación de ToolTask

**Estado:** borrador aislado para revisión; no es implementación ni ruta canónica.  
**Base revisada:** jhonf463r/Python, main=0672873489db434322cc1ef762e53c4f3aa0aec6.  
**Alcance:** ToolTask persistida → aprobación humana correlacionada → resolución verificable → recuperación de la misma tarea → ejecución única.  
**Límites:** solo lectura y diseño; no se ejecutaron pruebas, runtime ni herramientas IABV; no se invocaron execute_task ni execute_external_consultation.

## Decisión de diseño

La ruta adecuada es una reanudación asíncrona y durable de la tarea existente. ToolTeachService conserva la propiedad de ToolTask y de su ejecución; HumanApprovalBroker transporta solicitud y resolución, pero no es autoridad suficiente ni almacén durable. ToolRecordRepository sigue siendo fuente de recuperación. La UI existente puede presentar la solicitud, pero debe emitir una resolución autenticada y correlacionada.

No debe bloquearse el hilo de ejecución esperando a la UI con la API actual de HumanApprovalBroker.request(): crea un Future en memoria y espera con future.result(); no ofrece recuperación tras reinicio y no está demostrado que el hilo/UI no dependa del mismo dispatcher. Una decisión de ApprovalMemory que resulte auto_resolved=true no es aprobación humana interactiva.

## Evidencia fuente

Blobs revisados en el SHA base indicado; son evidencia estática, no observaciones de runtime.

| Archivo y método | Blob | Evidencia |
|---|---|---|
| docs/history/CHAT-ARCH/CURRENT-STATE.md | 8fe887ec1352adb5123dd1b781e32661afbaeace | Autoridad de ruta; gates siguen bloqueados. |
| docs/history/CHAT-ARCH/UAAL-CFCP-001 | 8c16a70a5790bba14a731aabd6ca09ca13c290e2 | Continuidad causal aplicable. |
| Registro 051 | d29755095c8d0ef19a3fc4d6d32da9e5795d6b82 | Antecedente de brecha de continuidad directa. |
| Registro 052 | 7985955984bf41c8e029b5c93e3b3a5b5f602c5a | Antecedente; no prueba implementación ni runtime. |
| IABV_v1.5/AGENTS.md | 0495e680cbe6b83d2310f87276bdc03c1c3fcd08 | Contratos de evidencia y límites arquitectónicos. |
| services/tools/tool_teach_service.py | 7f0412627c98074b1e3df0d0f6e76ab5998e3505 | execute_external_consultation crea tarea; execute_task evalúa gate y persiste tarea antes de devolver ToolResult waiting_approval. No se observó broker inyectado ni transición durable de la tarea al estado WAITING_APPROVAL. |
| services/security/human_approval_broker.py | 4a447149cf1b2771f6959658338a72b381f00b19 | request bloquea sobre Future en memoria; approve/reject resuelven por request_id; ApprovalResult no incluye actor autenticado. |
| services/security/approval_memory.py | ed85408d96fb0cdfddb05489d6c38cf714275f91 | Puede auto-resolver; auto_resolved debe excluirse de aprobación humana. |
| services/tools/tool_memory.py | 67f13a507e69ca8cd668a01840a048f5f35ba69c | Operaciones de memoria de tarea/resultado; no prueba atomicidad del ciclo. |
| infra/persistence/tool_record_repository.py | 0576b5c91d10319a3b7b81d3d2f07ce4c4c27ffe | save_task/get_task/save_result; no se observó API CAS/transaccional de ciclo. |
| infra/persistence/database.py | cee153ea8901451086b39273c026bbde20427b49 | Tabla tool_tasks y operaciones SQL; no se observó transición CAS. |
| services/tools/tool_approval_policy.py | b5bd3cba40caa89fcc6a5cd72146281c07c26ea1 | Decisión de política no equivale a prueba humana. |
| services/dashboard/proactive_dashboard_service.py | 08535790507b88f9a36e62cbc02e5fa8f84bf379 | Expone solicitudes pendientes para presentación. |
| presentation/viewmodels/evolution_center_viewmodel.py | af40921e7e56ccb53b059f1b08f19644f4a07a6b | Serializa el dashboard/solicitudes. |
| presentation/qml/EvolutionCenterPage.qml | c96a89bebd405af6a1bd8828d9153d5fd0be882b | Presenta título/detalle; no se observó acción de approve/reject conectada al ciclo. |
| bootstrap.py | blob revisado en base | Crea broker e inyecta en servicios de dashboard/UI; no se observó registro del prompt handler para este flujo. |
| presentation/viewmodels/control_center_viewmodel.py | 628848c631e36b47b4a5b63b9e68d62687625235 | Ruta de chat/autonomía separada. |
| services/orchestration/adaptive_task_orchestrator.py | 41f6f7b6157226a1c6004591ddff4e36ff6f6da5 | approve_next_phase(session_id) pertenece a AdaptiveSession, no reanuda task_id. |
| services/orchestration/execution_playbook_service.py | 002c63706f78cdd5ae7109f6a713514d1b0cad41 | Aprobación de fase de sesión, distinta del recibo ToolTask. |
| services/tools/tool_operational_executor.py | 840addd3dd8a017e83788950ad5ed0205e7b0037 | Ejecuta desde sesión/playbook; no demuestra continuidad del ToolTask original. |
| services/tools/autonomous_evolution_service.py | bf71757e8b90a35ce5c46cc0e6b5a781abbcd7ad | Pasa approved=false en su llamada de consulta; no es bypass. |
| domain/models.py | blob revisado en base | ToolTaskStatus incluye PENDING, WAITING_APPROVAL, READY, EXECUTING y terminales; ToolTask no muestra recibo explícito. |

El registro 050 no existe en el SHA objetivo y no se cita como disponible. “No observado” se limita a los módulos/rutas revisados; no afirma ausencia global.

## Diagrama de estados

    PENDING
      └─ gate requiere humano → WAITING_APPROVAL [persistido]
          ├─ rechazo verificado → REJECTED (terminal)
          ├─ plazo vencido → EXPIRED (terminal)
          ├─ cancelación autorizada → CANCELLED (terminal)
          └─ recibo humano válido → APPROVED_PENDING_RESUME
                ├─ recuperación + revalidación exacta → READY
                │     └─ claim CAS único → EXECUTING
                │           ├─ resultado durable → COMPLETED
                │           ├─ error conocido → FAILED
                │           └─ caída ambigua → UNKNOWN_OUTCOME
                └─ correlación/autoridad/hash inválido → FAILED_CLOSED

Secuencia causal: ToolTeachService persiste ToolTask y envolvente → transición WAITING_APPROVAL → publica petición asíncrona por HumanApprovalBroker → UI presenta alcance → proveedor aprobado autentica al actor → UI devuelve resolución tipada → broker entrega resolución → repositorio registra recibo monotónico → ToolTeachService recupera la misma task_id, valida y reclama ejecución mediante CAS → ruta de ejecución existente → resultado/captura ligado a la tarea.

No se debe reabrir terminales ni convertir timeout en aprobación. UNKNOWN_OUTCOME no se reintenta salvo prueba autoritativa de que no hubo efecto externo.

## Responsabilidad por órgano

| Órgano | Dueño de | No debe |
|---|---|---|
| ToolTeachService | Tarea, gate, suspensión, recuperación, revalidación y ejecución existente. | Crear segundo coordinador, regenerar la tarea o aceptar booleano como prueba. |
| HumanApprovalBroker | Transporte asíncrono, request_id, entrega y recepción tipada. | Ser raíz de confianza, ejecutor o único almacén durable. |
| ToolRecordRepository | Estado y evidencia durable, recibos/resultados y transiciones CAS. | Permitir regresión o sobrescritura que elimine evidencia. |
| ApprovalMemory | Sugerencia automática explícitamente clasificada. | Satisfacer human_required o contar auto_resolved como humano. |
| UI existente | Presentar alcance/destino y enviar decisión explícita. | Bloquear el dispatcher o determinar la autoridad desde texto editable. |
| Proveedor de identidad | Prueba autenticada, revocable y verificable del actor/mandato. | Inferirse de approved_by, nombre visible, rol de entorno o sesión presente. |

## Correlación, procedencia e invariantes

En la creación se fija una envolvente inmutable: request_id único; task_id existente; destino resuelto por el host y su versión; operación y alcance normalizados; hash criptográfico del plan/contenido exacto; identidad del servidor/instancia; versión de esquema/política; expiry y secuencia. El recibo enlaza esos campos y agrega decisión, prueba tipada del actor, issuer/proveedor, instante durable, expiración y referencias de revocación.

1. El permiso cubre solo esa tarea, digest, destino, operación y alcance; cualquier cambio invalida el recibo.
2. approved=true, approved_by, VALIDATED, firma sin raíz independiente, sesión Entra sin mandato, o policy aprendida son insuficientes por sí solos.
3. auto_resolved=true nunca satisface aprobación humana.
4. No se ejecuta hasta validar tipo, actor, autoridad, revocación, expiración y coincidencia exacta de correlación.
5. Eventos/recibos son monotónicos y no sobrescribibles; CAS con versión esperada protege transiciones concurrentes.
6. Resoluciones duplicadas devuelven el mismo resultado; decisiones contradictorias se rechazan y auditan.
7. READY→EXECUTING se reclama una sola vez. Exactly-once de efectos externos requiere idempotencia del destino o reconciliación; una transacción local sola no lo garantiza.
8. Reinicio conserva solicitud/recibo; nunca convierte estado incierto en READY.

## Errores y recuperación

- Rechazo: recibo autenticado y REJECTED; no ejecutar.
- Expiración: CAS a EXPIRED; una respuesta tardía se rechaza. Timeout de Future no es rechazo humano.
- Cancelación: solo actor autorizado; se serializa frente al claim. Si ya ejecuta, informar el estado real.
- Error UI/broker: dejar durable WAITING_APPROVAL y republicar la misma request, no crear autorización implícita.
- Error de persistencia: fail-closed; no confirmar ni ejecutar.
- Reinicio: cargar la misma task, verificar digest/version/expiry/revocación, republicar pendientes y reanudar aprobadas idempotentemente.
- Caída durante ejecución: UNKNOWN_OUTCOME hasta reconciliar; no repetir acción no idempotente.
- Cambio de destino/plan: invalidar ciclo y requerir nueva task/request.

Auditoría: task_id, request_id, digest/scope, destino/versionado, actor pseudónimo, issuer, decisión interactiva/automática, referencias de prueba, timestamps/expiry, transición y versión, clave idempotente, claim, inicio/fin, resultado y referencia de captura. No registrar secretos. Cada evento debe etiquetarse REPORTADO, VERIFICADO, EJECUTADO u OBSERVADO; presencia en UI o estado approved no demuestra los siguientes niveles.

## Matriz de brechas

| Requisito | Estado | Evidencia y límite |
|---|---|---|
| Modelo y enum ToolTask | EXISTENTE | Modelo publicado; sin recibo explícito. |
| Guardar/recuperar task | PARCIAL | save/get existen; no atomicidad de ciclo demostrada. |
| WAITING_APPROVAL durable | PARCIAL | ToolResult lo informa; transición de ToolTask no observada. |
| Broker | PARCIAL | request_id y approve/reject existen; Future volátil, sin actor autenticado. |
| Presentar solicitud | PARCIAL | Dashboard/UI lista; acciones de resolución no observadas. |
| Procedencia humana verificable | AUSENTE en flujo revisado | approved_by/result no prueba actor. |
| Excluir auto-aprobación | PARCIAL | flag existe; integración ToolTask no observada. |
| Enlace task/request/scope/hash | AUSENTE en flujo revisado | No enforcement end-to-end observado. |
| Recuperar misma tarea | AUSENTE en flujo revisado | AdaptiveSession es ruta diferente. |
| CAS/idempotencia durable | AUSENTE en APIs revisadas | No se observó claim/transición CAS. |
| Exactly-once ante efecto externo | DESCONOCIDO | Requiere contrato del destino/reconciliación. |
| Autoridades G1/G2/G3 | NO ESTABLECIDAS | Fuera de este contrato y siguen bloqueadas. |

## Cambios futuros mínimos (no escritos)

1. Añadir modelo/recibo de ciclo y API de persistencia transaccional/CAS al repositorio existente, con migración no destructiva.
2. Hacer que ToolTeachService persista espera, publique asíncronamente y reanude la misma task_id.
3. Usar HumanApprovalBroker como transporte/fachada; recibo tipado con procedencia, correlación, expiry y rechazo de auto-resolve.
4. Conectar la UI existente a approve/reject sin bloquear el dispatcher y mostrar alcance exacto.
5. Resolver mediante decisión del Owner la raíz, mandato, actor, revocación, custodia y privacidad/retención antes de permitir ejecución.
6. Añadir pruebas de transiciones, replay, concurrencia, reinicio y una E2E futura con autorización separada.

## Criterios de aceptación independiente y E2E futura

- Un único dueño (ToolTeachService), repositorio existente, sin nuevo coordinador.
- Evidencia de task persistida y WAITING_APPROVAL durable; correlación request/task/digest/destino exactos.
- La UI expone alcance; actor autenticado produce recibo tipado no automático.
- La reanudación recupera la misma task_id y revalida todo antes del único claim.
- Pruebas negativas de booleano aislado, actor no autenticado, auto_resolved, correlación alterada, expiración, revocación, duplicado/contradicción, fallo de persistencia y carrera cancel/claim.
- Reinicio y caída producen recuperación segura; UNKNOWN_OUTCOME no duplica efectos.
- Resultado/captura se persisten bajo el mismo task_id; reportes se distinguen de hechos verificados.
- No se habilita lectura protegida sin autoridad real; G1/G2/G3 continúan bloqueados hasta demostración independiente.

## Decisiones del Owner y estado

Decisiones pendientes: autoridad aceptable del Owner, custodio/ciclo de raíz, principal Windows, issuer/revocación, límites visibles de aprobación, retención de auditoría y semántica/idempotencia de cada destino. Son dependencias externas; no se simulan.

Este borrador no cambia la ruta canónica ni autoriza implementación.

    G1/G2/G3=NOT_ESTABLISHED
    MCP_TOOL_ALLOWLIST=EMPTY
    PROTECTED_READS=FAIL_CLOSED
    TUNNEL=DISABLED
    BRIDGE=BRIDGE_NOT_READY
    MERGE/PUBLISH=NOT_AUTHORIZED
    TESTS/BUILD/RUNTIME=NOT_RUN

**Siguiente acción única:** revisión del Owner del contrato y resolución de decisiones de autoridad; implementación requiere autorización separada.

## Índice de ubicaciones fuente en el SHA revisado

Las ubicaciones siguientes son referencias del árbol de main en 0672873489db434322cc1ef762e53c4f3aa0aec6; deben revalidarse si cambia el SHA.

- services/tools/tool_teach_service.py: execute_external_consultation alrededor de 718; execute_task y gate/resultado waiting_approval alrededor de 826–843.
- services/security/human_approval_broker.py: request alrededor de 178; approve alrededor de 269; reject alrededor de 287; pending_requests alrededor de 315. El request usa Future.result; las peticiones pendientes viven en memoria.
- services/security/approval_memory.py: pre_approver alrededor de 188; auto_resolved producido alrededor de 222.
- infra/persistence/tool_record_repository.py: save_task alrededor de 74; get_task alrededor de 122; save_result alrededor de 135.
- infra/persistence/database.py: definición de tool_tasks alrededor de 218; ejecución SQL alrededor de 551.
- bootstrap.py: creación de HumanApprovalBroker alrededor de 1116; configuración del capturador alrededor de 1134; inyección a EvolutionCenterViewModel alrededor de 3579. No se encontró registro del handler de prompt de este broker en la composición revisada.
- services/dashboard/proactive_dashboard_service.py: exposición de solicitudes pendientes alrededor de 105.
- presentation/viewmodels/evolution_center_viewmodel.py: serialización del dashboard alrededor de 397.
- presentation/qml/EvolutionCenterPage.qml: presentación de solicitud alrededor de 319; el bloque observado muestra título/detalle, sin controles de resolución para este ciclo.
- presentation/viewmodels/control_center_viewmodel.py: sendChat alrededor de 13700; ruta de autonomía alrededor de 10818 y llamada desde chat alrededor de 14412.
- services/orchestration/adaptive_task_orchestrator.py: approve_next_phase(session_id) alrededor de 2084.
- services/orchestration/execution_playbook_service.py: approve_next_phase alrededor de 89.
- services/tools/tool_operational_executor.py: execute(session) alrededor de 37.
- services/tools/autonomous_evolution_service.py: invocación de execute_external_consultation alrededor de 136 con approved=false.
- domain/models.py: ToolTaskStatus alrededor de 201; ToolTask alrededor de 1299.

Las búsquedas de wiring fueron acotadas a AppBootstrap, broker y las rutas UI citadas. La falta de una coincidencia en esas rutas no se generaliza a todo el sistema.