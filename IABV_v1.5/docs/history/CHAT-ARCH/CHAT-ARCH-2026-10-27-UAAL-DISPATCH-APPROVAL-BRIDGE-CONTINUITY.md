# UAAL — Dispatch y puente de aprobación de ToolTask: continuidad

- Fecha: 2026-10-27 (America/Bogota)
- Repositorio: jhonf463r/Python
- Base estática: main 0672873489db434322cc1ef762e53c4f3aa0aec6
- CURRENT-STATE blob: 8fe887ec1352adb5123dd1b781e32661afbaeace
- UAAL-CFCP-001 blob: 8c16a70a5790bba14a731aabd6ca09ca13c290e2
- Handoff MCP130 blob: 620685ffda7808d7253b241d703602a28cacc60c
- Registro 051 blob: d29755095c8d0ef19a3fc4d6d32da9e5795d6b82
- Registro 052 blob: 7985955984bf41c8e029b5c93e3b3a5b5f602c5a
- Registro 050: no existe en el SHA revisado; no se reconstruye ni se cita como fuente disponible.

## Resultado y procedencia

La secuencia de continuidad solicitada es TASK_RESULT=BLOCKED_DISPATCH seguida de TASK_RESULT=BLOCKED_APPROVAL_BRIDGE_MISSING. La interfaz de aprobación es visible en código, pero la sesión local no logró activarla. El estado terminal para el camino ToolTask es TASK_SCOPED_APPROVAL_ROUTE=MISSING y SAME_TASK_CONTINUATION=MISSING.

- SOURCE_STATIC: en ToolTeachService, execute_external_consultation crea la tarea y execute_task evalúa el gate; la ruta devuelve un ToolResult waiting_approval, pero no se observó que la ToolTask se transicione de forma durable a WAITING_APPROVAL.
- SOURCE_STATIC: HumanApprovalBroker ofrece request_id, approve/reject y solicitudes pendientes. request espera sincrónicamente sobre Future en memoria; ApprovalResult no aporta por sí solo identidad humana autenticada ni recuperación durable.
- SOURCE_STATIC: ApprovalMemory puede producir auto_resolved; esto no acredita consentimiento humano interactivo.
- SOURCE_STATIC: ToolRecordRepository puede guardar/recuperar tareas y resultados, pero no se observó una API CAS/transaccional que coordine recibo, recuperación y claim idempotente.
- SOURCE_STATIC: dashboard y Evolution Center presentan solicitudes; no se observó una acción UI conectada a la continuación del ToolTask directo.
- SOURCE_STATIC: la aprobación AdaptiveSession/ApprovalCheckpoint es un flujo diferente y no demuestra identidad ni reanudación del task_id original.
- SESSION_REPORTED: la ruta local de interfaz falló con “failed to write kernel assets … os error 3”.
- SESSION_REPORTED: un checkout parcial se detuvo por “Filename too long”. Los directorios existentes y el clon parcial deben preservarse; no repetir el mismo intento sin precondición materialmente nueva.
- NOT_RUN: no se ejecutó el ciclo ToolTask, no hubo aprobación humana simulada, despacho real, efecto externo, prueba, build ni runtime.

## Fuentes históricas reconciliadas

El registro 051 concluye que existe una aprobación orientada a AdaptiveSession, pero no se demostró un consumidor que vincule el artefacto humano al mismo task_id directo. Prohíbe sustituir la evidencia con execute_task(approved=True).

El registro 052 clasifica CASE B: los órganos existentes pueden expresar conceptualmente la relación, pero el wiring de ToolTask directo no está compuesto. Recomienda diseñar el ciclo antes de codificar y enumera la secuencia mínima: tarea → request task-scoped → resolución verificada → correlación/revalidación → recuperación de la misma tarea → ejecución.

El protocolo UAAL-CFCP-001 separa reporte, revisión estática, ejecución, resultado y verificación; los resultados de pruebas sintéticas o el despacho no prueban consumo/efecto downstream.

## Contrato de diseño preparado

Un borrador local aislado de diseño del ciclo está disponible para revisión del Owner. No forma parte de GitHub ni autoriza implementación.

SHA-256 del borrador: 284fc175240cd32d3b63da3e7fead46d3bcd00667aa17bc92ff0431d18c47bad

El diseño asigna ToolTeachService como dueño de tarea/ejecución, HumanApprovalBroker como transporte, y ToolRecordRepository como fuente de persistencia. Exige correlación inmutable de request_id, task_id, destino, operación/alcance y digest; prueba verificable de actor; exclusión de auto-resolve; transiciones durables; CAS/idempotencia; expiración, cancelación, reinicio y estado UNKNOWN_OUTCOME. La API síncrona actual no se considera segura para esperar a la UI sin demostrar independencia de dispatcher.

## Evidencia fuente exacta

Blobs de los módulos inspeccionados en el SHA base; ubicaciones aproximadas dentro de esos blobs:

| Ruta relativa | Blob | Método/contrato observado |
|---|---|---|
| IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py | 7f0412627c98074b1e3df0d0f6e76ab5998e3505 | execute_external_consultation (~718); execute_task/gate (~826–843). |
| IABV_v1.5/src/iabv_v15/services/security/human_approval_broker.py | 4a447149cf1b2771f6959658338a72b381f00b19 | request (~178), approve (~269), reject (~287), pending_requests (~315); espera síncrona/Future en memoria. |
| IABV_v1.5/src/iabv_v15/services/security/approval_memory.py | ed85408d96fb0cdfddb05489d6c38cf714275f91 | pre_approver (~188), decisión auto_resolved (~222). |
| IABV_v1.5/src/iabv_v15/infra/persistence/tool_record_repository.py | 0576b5c91d10319a3b7b81d3d2f07ce4c4c27ffe | save_task (~74), get_task (~122), save_result (~135). |
| IABV_v1.5/src/iabv_v15/infra/persistence/database.py | cee153ea8901451086b39273c026bbde20427b49 | tabla tool_tasks (~218), ejecución SQL (~551). |
| IABV_v1.5/src/iabv_v15/bootstrap.py | e4befa6b683fc87aed7481f377f1332f5753e2c3 | creación broker (~1116), wiring dashboard/UI (~3579); handler de prompt no observado en el wiring revisado. |
| IABV_v1.5/src/iabv_v15/services/dashboard/proactive_dashboard_service.py | 08535790507b88f9a36e62cbc02e5fa8f84bf379 | exposición de solicitudes pendientes (~105). |
| IABV_v1.5/src/iabv_v15/presentation/viewmodels/evolution_center_viewmodel.py | af40921e7e56ccb53b059f1b08f19644f4a07a6b | serialización del dashboard (~397). |
| IABV_v1.5/src/iabv_v15/presentation/qml/EvolutionCenterPage.qml | c96a89bebd405af6a1bd8828d9153d5fd0be882b | panel de solicitudes (~319); no se observó acción de resolución para ToolTask directo. |
| IABV_v1.5/src/iabv_v15/domain/models.py | a9033d21052c519e09f482097599c704a62ea916 | ToolTaskStatus (~201), ToolTask (~1299); no se observó recibo explícito. |
| IABV_v1.5/src/iabv_v15/presentation/viewmodels/control_center_viewmodel.py | 628848c631e36b47b4a5b63b9e68d62687625235 | entrada chat/autonomía (~10818, ~13700, ~14412); ruta fuente, no activación observada. |
| IABV_v1.5/src/iabv_v15/services/orchestration/adaptive_task_orchestrator.py | 41f6f7b6157226a1c6004591ddff4e36ff6f6da5 | approve_next_phase(session_id) (~2084), flujo AdaptiveSession distinto. |
| IABV_v1.5/src/iabv_v15/services/orchestration/execution_playbook_service.py | 002c63706f78cdd5ae7109f6a713514d1b0cad41 | aprobación de fase de sesión (~89). |
| IABV_v1.5/src/iabv_v15/services/tools/tool_operational_executor.py | 840addd3dd8a017e83788950ad5ed0205e7b0037 | execute(session) (~37), reconstruye desde sesión. |
| IABV_v1.5/src/iabv_v15/services/tools/autonomous_evolution_service.py | bf71757e8b90a35ce5c46cc0e6b5a781abbcd7ad | consulta externa (~136) pasa approved=false. |

Las líneas son orientativas para el SHA indicado; los blobs son las identidades de contenido. No se inspeccionó ni afirmó runtime.

## Brechas causales

1. Persistir WAITING_APPROVAL y una envolvente de autorización inmutable en la misma fuente durable.
2. Obtener y verificar procedencia humana y autoridad independiente; approved/approved_by no basta.
3. Conectar la UI existente al broker sin bloqueo mutuo.
4. Registrar resolución y recuperar exactamente el task_id existente.
5. Proteger frente a respuestas duplicadas/contradictorias, carreras y replay con transición atómica.
6. Definir comportamiento tras reinicio y resultado externo incierto.
7. Asegurar que sandbox, despacho, resultado externo y captura se informen como etapas distintas.

Estas brechas son del flujo fuente revisado; no demuestran ausencia global de capacidades fuera de las rutas indicadas.

## Aprendizaje reutilizable y límite

No repetir la inicialización UI que falló por kernel ausente ni el checkout idéntico que falló por longitud de ruta. No generar una tarea nueva para alcanzar la UI de aprobación. Antes de implementación, adjudicar el contrato de aprobación y el órgano propietario con fuentes exactas; los fakes, reportes y estados declarativos no prueban consentimiento/consumo. El aprendizaje se considera persistido documentalmente; su reutilización causal futura aún no está demostrada.

## Única siguiente acción

Revisión del Owner del diseño contractual de aprobación. No implementar, cambiar código, tests, PR #531/#549, activar runtime ni alterar gates hasta una autorización independiente.

    G1/G2/G3=NOT_ESTABLISHED
    MCP_TOOL_ALLOWLIST=EMPTY
    PROTECTED_READS=FAIL_CLOSED
    TUNNEL=DISABLED
    BRIDGE=BRIDGE_NOT_READY
    MERGE/PUBLISH=NOT_AUTHORIZED
    TESTS/BUILD/RUNTIME=NOT_RUN
    AUTOMATIC_FOLLOW_ON=FALSE