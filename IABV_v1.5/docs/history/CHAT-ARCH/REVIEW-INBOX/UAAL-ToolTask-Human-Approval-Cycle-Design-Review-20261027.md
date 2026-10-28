# Revisión independiente — Contrato de ciclo de aprobación humana de ToolTask

**Dictamen:** `DESIGN_REVIEW=CONDITIONALLY_ACCEPTABLE_AS_DESIGN_DRAFT`  
**Preparación para implementación:** `IMPLEMENTATION_READINESS=BLOCKED`  
**Código/contrato modificado:** ninguno; este informe es un artefacto separado.  
**Rama de revisión:** `handoff/uaal-tooltask-approval-design-20261027`  
**Commit del diseño:** `7201d35ea9b26a324a24a9e991f1d73e918c05f2`  
**Blob del diseño:** `94aba57d8f430fad26cc657504ad429cee264357`  
**Base fuente declarada por el diseño:** `0672873489db434322cc1ef762e53c4f3aa0aec6`  
**Main vivo comprobado al revisar:** `0bb37eb047481490885bdb2e9fb8a61834c2b72c`  
**Ejecución, tests, build:** `NOT_RUN`

## 1. Resumen del dictamen

El diseño identifica correctamente la frontera causal faltante y elige una dirección razonable: suspensión/reanudación asíncrona y durable de la misma `task_id`, propiedad de `ToolTeachService`, usando `HumanApprovalBroker` como transporte y el repositorio existente como punto de recuperación, sin un segundo coordinador.

También incorpora salvaguardas relevantes: excluir `auto_resolved` de la autorización humana, vincular solicitud y tarea, invalidar la aprobación ante cambios de alcance/contenido, manejar resultados externos ambiguos como `UNKNOWN_OUTCOME`, y separar sandbox de despacho real.

**No está listo para implementación.** El contrato necesita cerrar o delimitar cinco puntos bloqueantes antes de que una implementación pueda considerarse segura: (1) autoridad/procedencia concreta del aprobador; (2) persistencia atómica y fuente de verdad de las transiciones; (3) cableado real de la solicitud/resolución de UI; (4) semántica de reclamo/recuperación frente a crash y posibles efectos externos; (5) límites exactos del objeto que la aprobación autoriza. Además, el índice de fuentes contiene rutas incorrectas que deben corregirse para que otra revisión independiente pueda reproducirla.

## 2. Fortalezas confirmadas

- Distingue la aprobación del flujo `AdaptiveSession/ApprovalCheckpoint` de la tarea directa `ToolTask`.
- No trata `approved=True`, `ApprovalResult.approved` o `approved_by` como prueba suficiente de presencia humana.
- Reconoce el bloqueo síncrono de `HumanApprovalBroker.request()` sobre `Future.result()` y propone una ruta asíncrona.
- Incluye expiración, cancelación, respuestas duplicadas/contradictorias, reinicio y resultado externo ambiguo.
- Aclara que una transacción local no garantiza exactly-once de un efecto externo; exige idempotencia del destino o reconciliación.
- Declara las decisiones de autoridad aún pendientes y no autoriza implementación, tests ni runtime.

## 3. Hallazgos bloqueantes

### R1 — La identidad/autoridad que convierte una interacción en aprobación válida sigue sin resolverse

**Evidencia estática:** `ApprovalResult` contiene `request_id`, `approved`, rechazo/timeout/cancelación y `auto_resolved`, pero no una prueba tipada de actor autenticado. `HumanApprovalBroker.approve(request_id, payload)` crea un resultado con `approved=True`; ese booleano solo registra que se llamó al método. `ApprovalMemory` también puede devolver una resolución automática.

El borrador lo reconoce, pero deja abiertos el principal autorizado, emisor/proveedor de identidad, vínculo con el mandato del Owner, revocación y fuerza de la interacción humana.

**Condición para aceptar el contrato:** definir un perfil de aprobación concreto para esta operación (quién puede aprobar, cómo se verifica la interacción/actor, qué alcance puede conceder, cómo se revoca y cómo se valida el recibo). No hace falta elegirlo por inferencia; las decisiones genuinamente de autoridad deben quedar separadas de los detalles de implementación. Una sesión de usuario o una pantalla visible no demuestran por sí mismas una identidad/mandato confiables.

### R2 — La transición durable `WAITING_APPROVAL` no está implementada y la persistencia actual no ofrece CAS

**Evidencia estática en el SHA base:**

- `ToolTask.status` tiene enum `WAITING_APPROVAL`, pero en el gate de `ToolTeachService.execute_task()` el estado `waiting_approval` se asigna al `ToolResult.execution_state.state`; no se ve una actualización correspondiente de `task.status` antes de `remember_task(task)`/el retorno del resultado.
- `ToolRecordRepository.save_task()` primero escribe el JSON mediante `save_json_atomic()` y después ejecuta `INSERT OR REPLACE INTO tool_tasks`. En los métodos revisados no se ve una transición compare-and-set (CAS) ni una transacción que abarque el JSON, la fila de tarea y el recibo de aprobación.
- `APPROVED_PENDING_RESUME`, `UNKNOWN_OUTCOME` y `FAILED_CLOSED` del diagrama no existen como estados de `ToolTaskStatus` en el modelo revisado.

**Condición para aceptar el contrato:** nombrar una sola fuente de verdad y especificar exactamente qué agregado/tabla persiste cada transición, qué transacción protege estado + recibo + claim, y cómo se reconcilia el JSON si el proceso cae entre la escritura del archivo y la fila SQL. Definir si los estados nuevos son estados de `ToolTask` o de un agregado de aprobación separado, evitando dos máquinas de estado que diverjan. No tratar `INSERT OR REPLACE` como CAS.

### R3 — La UI que muestra la solicitud no está demostrada como ruta operativa de resolución

**Evidencia estática:** `bootstrap.py` crea `HumanApprovalBroker` y `ProactiveDashboardService`, y registra handlers para otros brokers/servicios en el bloque de composición de UI; en ese bloque no se observó un `register_prompt_handler()` del `HumanApprovalBroker`. La página `EvolutionCenterPage.qml` muestra datos de elementos, incluido `title/detail`, pero la búsqueda estática del archivo no encontró acciones `approve`/`reject` conectadas a este ciclo.

**Condición para aceptar el contrato:** representar la UI como una brecha por conectar, no como un órgano que ya puede emitir la resolución del ciclo. Especificar el contrato de mensaje/retorno y el punto de wiring a añadir al diseñar la futura implementación. No dar por probada la ruta solo porque existe el dashboard o el broker.

### R4 — El claim de ejecución y recuperación debe cerrar la ventana de crash antes/después de iniciar Codex

El borrador advierte correctamente que una transacción local no ofrece exactly-once externo. Falta volverlo un contrato verificable para el adaptador local: puede haber una caída después de crear el proceso/efecto y antes de persistir la respuesta/recibo. Un reintento podría lanzar un segundo Codex si no hay reconciliación.

**Condición para aceptar el contrato:** definir el momento del claim duradero, la clave idempotente estable, qué prueba identifica el proceso/sesión/rollout que pertenece al claim, y el comportamiento estricto cuando no puede demostrarse si hubo lanzamiento. En esa situación se mantiene `UNKNOWN_OUTCOME`; nunca se reintenta automáticamente por ausencia de captura. Explicar cómo el estado sobrevive a reinicios y qué límite existe si se restaura una copia antigua del almacenamiento.

### R5 — La huella debe abarcar todos los valores que afectan al efecto autorizado

El borrador exige `digest`, destino, operación y alcance; es correcto, pero la aceptación debe fijar la canonicalización exacta y el conjunto de valores cubiertos. Para una consulta a Codex, no basta con el texto visible del prompt si el lanzamiento depende además de tool/adapter seleccionados, contexto de consulta, executable/runner, directorio de trabajo o checkout, argumentos, variables relevantes de entorno, configuración de captura y política de dry-run/real.

**Condición para aceptar el contrato:** el digest debe calcularse sobre una envolvente canónica e inmutable de todos los inputs de ejecución relevantes, incluidos la política/versión de autorización y el contrato de captura. Cualquier mutación del objetivo, destino, runner o alcance obliga a una nueva aprobación. Definir qué campos se incluyen y cómo se excluyen secretos del registro (sin excluirlos silenciosamente del hash si afectan al efecto).

## 4. Hallazgos mayores no bloqueantes por separado

### R6 — El resultado sandbox puede contaminar métricas y aprendizaje

En `ToolTeachService.execute_task()`, `self.memory.remember_result(card, task, sandbox_result)` se llama antes del gate de aprobación. `ToolMemory.remember_result()` incrementa `success_count` a partir de `result.success` y, cuando está configurado, llama a `interaction_learning_service.learn_from_execution(..., result=result)`. Por tanto, el riesgo no es solo una etiqueta de éxito incorrecta: un resultado de sandbox puede alimentar el aprendizaje antes del despacho real.

**Criterio de aceptación adicional:** el contrato/test futuro debe distinguir `sandbox_passed`, `approval_granted`, `adapter_dispatched`, `external_action_succeeded` y `response_captured`; solo la fase apropiada puede actualizar sus métricas/patrones. Una sandbox aprobada no representa éxito del objetivo externo.

### R7 — Aclarar el alcance de estados, migración e historial

El diagrama combina estados existentes del modelo con estados propuestos. La versión de implementación necesitará migración no destructiva, lectura de tareas antiguas y una política para registros previos que tengan un resultado `waiting_approval` pero `ToolTask.status` aún en `PENDING`. No debe inferirse ni fabricarse una aprobación para esas tareas heredadas.

### R8 — Separar decisiones del Owner de decisiones de ingeniería

El bloque final mezcla decisiones genuinas de autoridad (principal/mandato/raíz de confianza, revocación, alcance máximo y retención sensible) con decisiones técnicas (CAS, outbox, estado desconocido, canonicalización e idempotencia). Las primeras necesitan una decisión explícita del Owner; las segundas deben resolverse mediante contrato de ingeniería sin trasladarle la carga técnica al Owner. La implementación seguirá dependiendo de autorización separada.

## 5. Correcciones obligatorias del índice de fuentes

Los blob SHA citados para los siguientes archivos corresponden a rutas reales distintas de las escritas en el diseño. Corregir el índice antes de una revisión independiente definitiva:

| Ruta escrita en el diseño | Ruta verificada en el SHA base |
|---|---|
| `services/dashboard/proactive_dashboard_service.py` | `services/security/proactive_dashboard_service.py` |
| `presentation/viewmodels/evolution_center_viewmodel.py` | `ui/viewmodels/evolution_center_viewmodel.py` |
| `presentation/qml/EvolutionCenterPage.qml` | `ui/qml/pages/EvolutionCenterPage.qml` |
| `presentation/viewmodels/control_center_viewmodel.py` | `ui/viewmodels/control_center_viewmodel.py` |
| `services/orchestration/adaptive_task_orchestrator.py` | `services/adaptive/adaptive_task_orchestrator.py` |
| `services/orchestration/execution_playbook_service.py` | `services/adaptive/execution_playbook_service.py` |
| `services/tools/autonomous_evolution_service.py` | `services/evolution/autonomous_evolution_service.py` |

Todas las rutas anteriores son relativas a `IABV_v1.5/src/iabv_v15/`. Los blob SHA principales fueron re-obtenidos en el SHA base; el archivo de modelos `domain/models.py` tiene blob `a9033d21052c519e09f482097599c704a62ea916`. Los archivos encontrados y verificados incluyen `tool_teach_service.py` = `7f0412627c98074b1e3df0d0f6e76ab5998e3505`, `human_approval_broker.py` = `4a447149cf1b2771f6959658338a72b381f00b19`, `approval_memory.py` = `ed85408d96fb0cdfddb05489d6c38cf714275f91`, `tool_record_repository.py` = `0576b5c91d10319a3b7b81d3d2f07ce4c4c27ffe`, `database.py` = `cee153ea8901451086b39273c026bbde20427b49`, `tool_approval_policy.py` = `b5bd3cba40caa89fcc6a5cd72146281c07c26ea1`, `bootstrap.py` = `e4befa6b683fc87aed7481f377f1332f5753e2c3`, y `ui/qml/pages/EvolutionCenterPage.qml` = `c96a89bebd405af6a1bd8828d9153d5fd0be882b`.

El índice dice que `ToolTaskStatus` contiene `WAITING_APPROVAL`; eso fue verificado. La observación de que el gate no actualiza `task.status` procede de leer el código de ese gate, no de una ejecución en runtime.

## 6. Condiciones para una revisión de cierre del diseño

El borrador podrá pasar a revisión de cierre cuando:

1. Se mantenga separada la autoridad humana de los flags/auto-aprobaciones.
2. Se especifique una transición durable y atómica del mismo `task_id`, con migración y recuperación de estado antiguo.
3. La UI/broker tenga una ruta de solicitud/respuesta descrita de forma realista; los handlers aún no conectados queden explícitos.
4. Se defina el digest completo de los inputs que hacen que el dispatch sea el mismo efecto.
5. Se cierre el comportamiento de claim/recovery/`UNKNOWN_OUTCOME` sin reintentos duplicados.
6. Las métricas y aprendizaje no conviertan sandbox en éxito externo.
7. Se corrijan las rutas de fuentes y se mantenga la evidencia de acuerdo con su clase.

## 7. Límites y estado

Esta revisión se hizo por inspección estática de GitHub. No se ejecutó IABV, no se crearon tareas, no se invocó el broker, no se aprobaron acciones y no se corrieron tests/build/runtime.

```text
SOURCE_REVIEW=STATIC
DESIGN_REVIEW=CONDITIONALLY_ACCEPTABLE_AS_DESIGN_DRAFT
IMPLEMENTATION_READINESS=BLOCKED
OWNER_AUTHORITY_DECISIONS=OPEN
TASK_SCOPED_APPROVAL_ROUTE=MISSING
SAME_TASK_CONTINUATION=MISSING
TESTS/BUILD/RUNTIME=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE/PUBLISH=NOT_AUTHORIZED
```

**Siguiente acción:** mantener la implementación bloqueada; incorporar las precisiones y correcciones al contrato aislado, y separar las decisiones que de verdad pertenecen al Owner de las que corresponden al diseño técnico. No actualizar `main`, abrir PR ni fusionar como consecuencia de esta revisión.
