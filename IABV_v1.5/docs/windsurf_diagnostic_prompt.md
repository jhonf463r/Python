# Prompt Windsurf — Diagnóstico Profundo de Congelamientos, Consulta Externa y Metacognición

> **Instrucciones**: Copia TODO el bloque de prompt de abajo y pégalo en Windsurf
> después de usar IABV. Este prompt es más profundo que el reporte general — se
> enfoca en los 3 problemas específicos que necesitas resolver:
> 1. Por qué IABV se congela después de cargar
> 2. Por qué hay una micro-congelación al hacer consultas
> 3. Por qué no puede hacer consultas externas a ChatGPT y qué lógica metacognitiva tomó
>
> Además verifica que TODOS los fixes del PR #348 quedaron aplicados correctamente
> y genera un listado de qué necesita el programa para funcionar al 100%.

---

## Prompt (copiar desde aquí)

```
Eres el ingeniero de diagnóstico profundo de IABV v1.5 — un programa
Python/PySide6/QML de metacognición local que corre en esta máquina Windows.

El usuario reporta 3 problemas CONCRETOS que debes diagnosticar:

PROBLEMA 1: "Después de cargar el programa se congela"
PROBLEMA 2: "En la consulta hay una pequeña congelación"
PROBLEMA 3: "No pudo hacer la consulta externa a ChatGPT — necesito ver
             qué lógica tomó y si está aplicando toda su metacognición"

Además debes verificar que los fixes recientes (PR #348) quedaron aplicados
y listar qué necesita el programa para su buen funcionamiento.

==========================================================================
FASE 1: LECTURA DE DATOS (lee TODO esto antes de diagnosticar)
==========================================================================

### 1.1 Runtime Audit Trace (PRIORIDAD MÁXIMA)
Ruta: C:\Python\IABV_v1.5\data\logs\runtime_audit.jsonl

JSONL con eventos:
- ts: timestamp ISO UTC
- elapsed_ms: milisegundos desde arranque
- seq: secuencial
- kind: service_init | decision | external_query | permission | error |
        ui_event | resource_snapshot | metacognition_refresh
- data: payload del evento

CLAVE para congelamientos: busca GAPS en elapsed_ms entre eventos
consecutivos. Un gap > 2000ms indica freeze. Un gap > 5000ms es freeze
grave. Documenta CADA gap con:
- elapsed_ms del evento anterior al gap
- elapsed_ms del evento posterior al gap
- Duración del gap
- Qué kind tenían ambos eventos (indica qué se estaba haciendo)

### 1.2 Freeze Incident Reports
Ruta: C:\Python\IABV_v1.5\data\evolution\incident_reports\freeze_*.json

Si existen, contienen snapshot completo del momento: recursos, hilos,
SQLite, pending queue, OSES findings, procesos.

### 1.3 Startup Timeline
Ruta: C:\Python\IABV_v1.5\data\logs\startup_timeline.jsonl

JSONL de hitos de arranque con elapsed_ms. Busca:
- wire_services_start → wire_services_done (cuánto tardó el wiring)
- main_window_shown (cuándo la ventana fue visible)
- dashboard_vm_refresh_start → dashboard_vm_refresh_done
- deferred_post_window_setup_start → deferred_post_window_setup_done
- lazy_vm_prebuild_* (cuándo se construyen los ViewModels)
- splash_window_closing → ¿el splash se cierra antes que el dashboard?

CLAVE para PROBLEMA 1: si hay un gap largo DESPUÉS de
deferred_post_window_setup_done y ANTES de lazy_vm_prebuild_*, eso es
donde el usuario percibe el congelamiento post-carga.

### 1.4 Log estándar
Ruta: C:\Python\IABV_v1.5\data\logs\iabv_v15.log

Busca (en orden de prioridad):
- "ERROR" — errores fatales
- "WARNING" — advertencias operativas
- "RuntimeAuditTracer._append failed" — si el tracer no pudo escribir
- "credential_broker.request" — si el broker pidió credenciales
- "startup_truth_refresh" — si OSES/PortableContext se regeneraron
- "stale metacognition" — si detectó datos viejos y forzó refresh
- "freeze" — indicios de congelamiento
- "locked" — bloqueos SQLite
- "timeout" — timeouts de red o de servicio
- "preflight" — intentos de consulta externa

### 1.5 Decision Audit Trail
Ruta: C:\Python\IABV_v1.5\data\evolution\decision_audit\decisions.jsonl

Historial de decisiones: proveedor, fase, estado, latencia, error.
CLAVE para PROBLEMA 3: filtra por fase "chat_routing" y busca intentos
de ruta a chatgpt. Si NO hay ninguno, el sistema nunca lo intentó —
y la pregunta es POR QUÉ (gobernanza, falta de worker, etc.).

### 1.6 OSES (Autoexaminación Operativa)
Ruta: C:\Python\IABV_v1.5\data\evolution\self_examination\latest.json

VERIFICAR:
- ¿La fecha de generación es de HOY? (si no, el fix de auto-refresh
  del PR #348 no funcionó)
- ¿status es "complete" o "partial"?
- ¿findings tiene contenido o está vacío?
- ¿recurring_issues menciona congelamientos?
- ¿unresolved_risks incluye algo relevante?

### 1.7 Portable Context
Ruta: C:\Python\IABV_v1.5\data\evolution\portable_context\latest.json

VERIFICAR:
- ¿La fecha de generación es de HOY?
- ¿bloqueos_activos incluye consulta externa?
- ¿validated_improvements tiene algo nuevo?
- ¿unresolved_fields sigue igual o cambió?

### 1.8 World Model
Ruta: C:\Python\IABV_v1.5\data\evolution\world_model\

CLAVE para PROBLEMA 3: busca:
- permission_gates: ¿hay gates para chatgpt con status='requerido'?
- tool_live_status: ¿chatgpt aparece como herramienta?
- active_windows: ¿se detectó ventana de ChatGPT?
- detected_blocks: ¿hay bloqueos activos para consulta externa?

### 1.9 Chat Messages (si está disponible en logs)
Busca en iabv_v15.log o runtime_audit.jsonl eventos que muestren:
- El mensaje que el usuario escribió en el chat
- La respuesta del sistema
- Si el usuario dijo algo como "interactúa conmigo" o "ayúdame"
- Si el sistema detectó la intención o la ignoró

==========================================================================
FASE 2: DIAGNÓSTICO DEL PROBLEMA 1 — CONGELAMIENTO POST-CARGA
==========================================================================

Construye la línea de tiempo EXACTA del arranque hasta el congelamiento:

| Hito | elapsed_ms | Duración | Observación |
|------|-----------|----------|-------------|
| splash_qml_loaded | ? | — | Inicio |
| wire_services_start | ? | — | — |
| wire_services_done | ? | ?ms | ¿Cuello de botella? |
| main_window_shown | ? | — | Usuario ve la ventana |
| dashboard_vm_refresh_start | ? | — | — |
| dashboard_vm_refresh_done | ? | ?ms | ¿Lento o rápido? |
| deferred_post_window_setup_start | ? | — | — |
| deferred_post_window_setup_done | ? | ?ms | ¿Aquí congela? |
| lazy_vm_prebuild_* | ? | — | ¿Gap antes de esto? |
| [GAP DETECTADO] | ?→? | ?ms | ⚠️ FREEZE |

PREGUNTAS CLAVE:
1. ¿El congelamiento ocurre DURANTE deferred_post_window_setup (que hace
   tool probes + SQLite)?
2. ¿O ocurre DESPUÉS, en el gap entre setup y lazy VM construction?
3. ¿Hay un bloqueo SQLite durante el setup? (busca "locked" en log)
4. ¿Los tool probes están tomando mucho tiempo? (check herramientas como
   gh, cloudflared, pip)
5. ¿El hilo principal está bloqueado esperando algo del hilo background?
6. ¿La UI (QML) se renderizó pero no responde a clicks? (indica que el
   event loop de Qt está bloqueado)

HIPÓTESIS A VERIFICAR:
- H1: wire_services tarda >3s porque hay servicios que hacen I/O síncrono
- H2: deferred_post_window_setup bloquea el event loop de Qt
- H3: SQLite lock entre deferred setup y lazy VMs
- H4: _startup_self_examination o _run_startup_common_sense son lentos
- H5: _final_startup_truth_refresh (OSES + PortableContext) bloquea
- H6: La regeneración de metacognición stale (>24h) añade tiempo

Para cada hipótesis, busca la EVIDENCIA en los datos y marca:
✅ confirmada | ❌ descartada | ⚠️ parcial | 🔍 sin datos

==========================================================================
FASE 3: DIAGNÓSTICO DEL PROBLEMA 2 — MICRO-CONGELACIÓN EN CONSULTA
==========================================================================

Cuando el usuario hace una consulta (escribe en el chat y presiona Enter):

1. Lee en runtime_audit.jsonl los eventos alrededor del momento de la
   consulta. Busca kind="decision" con data.decision_point que incluya
   "chat_routing" o "infer_task"

2. Construye la línea de tiempo de la consulta:
   | Paso | elapsed_ms | Duración | Qué hace |
   |------|-----------|----------|----------|
   | Usuario envía mensaje | ? | — | sendChat() |
   | _chat_shortcut_analysis | ? | ≤3s | Analiza si es shortcut |
   | _build_request | ? | ? | Arma PerceptionSnapshot |
   | infer_task | ? | ? | Orquestador decide ruta |
   | Proveedor responde | ? | ? | groq/ollama/local |
   | taskResolved emitted | ? | — | UI actualiza |

3. PREGUNTAS CLAVE:
   - ¿_chat_shortcut_analysis tarda los 3 segundos completos de timeout?
   - ¿_build_request hace I/O síncrono (lee archivos, consulta SQLite)?
   - ¿infer_task bloquea el hilo principal? (debería correr en thread)
   - ¿El proveedor (groq/ollama) tiene latencia alta?
   - ¿Hay un bloqueo entre sendChat y el inicio del thread worker?

4. HIPÓTESIS A VERIFICAR:
   - H1: _chat_shortcut_analysis bloquea 3s esperando timeout de LLM
   - H2: _ingest_chat_capabilities + _refresh_development_packet son
     síncronos y bloquean el hilo de UI
   - H3: El orquestador hace preflight síncrono antes del thread
   - H4: El proveedor (groq) tiene DNS lento o latencia > 2s

==========================================================================
FASE 4: DIAGNÓSTICO DEL PROBLEMA 3 — CONSULTA EXTERNA FALLIDA
==========================================================================

Este es el análisis más profundo. El usuario quiere saber EXACTAMENTE
qué camino metacognitivo tomó IABV cuando intentó (o no intentó)
consultar ChatGPT.

### 4.1 Reconstruir el flujo de decisión

Lee TODOS los eventos de runtime_audit.jsonl y decisions.jsonl para
reconstruir esta cadena:

```
Usuario escribe mensaje → sendChat()
  → ¿_explicit_assistant_preference() detecta "chatgpt"?
    SÍ → _run_external_consultation('chatgpt')
      → _execute_external_consultation_sync()
        → preflight_external_assistant()
          → WorldModelService.request_refresh()
          → _build_governance()
          → AutonomyGovernancePolicy.evaluate()
            → ¿approval_required? ¿block_risky_action?
          → permission_gates (¿hay gates para chatgpt?)
          → worker_health_gate (¿hay worker usable?)
          → RESULTADO: blocked=True/False, reason=?
        SI blocked:
          → runtime_audit: permission blocked
          → _blocked_external_consultation_result()
            → _guidance_for_external_preflight_block()
              → assistant_guidance.mode = 'need_approval'
            → _update_adaptive_state(payload con guidance)
              → ¿Se llamó _apply_assistant_guidance()? ← FIX PR#348
              → ¿_approval_dialog_visible = True?
              → ¿Botón "Permitir observación" visible? ← FIX PR#348
        SI no blocked:
          → ExternalAssistantToolAdapter.run()
          → ¿assistant_login_required?
            SÍ → CredentialBroker.request() ← ¿handler registrado?
            NO → ejecuta consulta
    NO → worker() → infer_task() → ruta local (groq/ollama)
```

### 4.2 Verificar cada nodo del flujo

Para CADA nodo del flujo anterior, busca la EVIDENCIA en los datos:

| Nodo | ¿Se ejecutó? | Resultado | Evidencia |
|------|-------------|-----------|-----------|
| sendChat | ? | ? | Busca en log |
| _explicit_assistant_preference | ? | ¿Detectó chatgpt? | Busca "explicit_assistant" |
| preflight_external_assistant | ? | blocked=? reason=? | runtime_audit permission |
| AutonomyGovernancePolicy | ? | approval_required=? | Busca "governance" |
| permission_gates | ? | ¿Hay gates chatgpt? | world_model |
| worker_health_gate | ? | usable=? | Busca "worker_gate" |
| _approval_dialog_visible | ? | true/false | ¿Apareció popup? |
| _apply_assistant_guidance | ? | ¿Se llamó? | FIX PR#348 |
| CredentialBroker.request | ? | ¿Se emitió? | Busca "credential_broker" |

### 4.3 Si el sistema NUNCA intentó ChatGPT

Si en todo decisions.jsonl no hay ningún intento de ruta chatgpt:
1. ¿El usuario pidió explícitamente ChatGPT? ¿Con qué palabras?
2. ¿_explicit_assistant_preference() reconoció la intención?
3. ¿El sistema tomó una ruta local en su lugar? ¿Por qué?
4. ¿La gobernanza tiene chatgpt bloqueado por defecto?
5. ¿Hay un worker registrado para chatgpt en el ToolRegistry?

### 4.4 Si el sistema intentó pero falló

Si hay un intento bloqueado:
1. ¿Qué dijo la gobernanza? (approval_required, block_risky_action)
2. ¿Había permission_gates para chatgpt? ¿Con qué status?
3. ¿Se mostró el popup de aprobación? (approval_dialog_visible)
4. ¿El popup tenía el botón "Permitir observación"? ← FIX PR#348
5. ¿El usuario respondió algo en el chat para conceder permiso?
6. ¿_try_resolve_pending_observation_permission detectó la respuesta? ← FIX PR#348

### 4.5 Verificar metacognición completa

El sistema debería usar TODA su metacognición antes de decidir:

| Capa metacognitiva | ¿Se consultó? | Qué dijo | Evidencia |
|--------------------|--------------|----------|-----------|
| WorldModelSnapshot | ? | ventanas, herramientas, red | world_model/ |
| EnvironmentSelfModel | ? | hardware, runtime | runtime_audit |
| AutonomyGovernancePolicy | ? | should_consult, blocked | decisions.jsonl |
| DecisionAuditTrail | ? | historial de éxito/fallo chatgpt | decisions.jsonl |
| OSES | ? | hallazgos, degradaciones | self_examination/ |
| PortableContext | ? | health score, trends | portable_context/ |
| ExperimentLab | ? | comparaciones activas | Busca "experiment" |
| StrategySelector | ? | recomendación de ruta | Busca "strategy" |

Si alguna capa NO se consultó, es un hallazgo crítico — el sistema
no está aplicando toda su metacognición.

==========================================================================
FASE 5: VERIFICACIÓN DE FIXES PR #348
==========================================================================

Verifica que CADA fix del PR #348 está funcionando:

### Fix 1: RuntimeAuditTracer genera datos
- ¿Existe C:\Python\IABV_v1.5\data\logs\runtime_audit.jsonl?
- ¿Tiene eventos? ¿Cuántos?
- ¿Hay eventos de tipo service_init, decision, permission?
- Si NO existe: busca en iabv_v15.log "RuntimeAuditTracer._append failed"
  para ver si hubo error de escritura

### Fix 2: Botón "Permitir observación" en popup
- Busca en runtime_audit.jsonl eventos permission con action="blocked"
  y dialog_shown=true
- Si hay un bloqueo de consulta externa, ¿approval_dialog_visible fue
  true?
- ¿El flujo llegó hasta _apply_assistant_guidance() en la rama de
  conversación general?

### Fix 3: Auto-resolver permisos desde el chat
- Si el usuario escribió algo afirmativo (si, dale, ayúdame, etc.)
  mientras había permiso de observación pendiente:
  ¿_try_resolve_pending_observation_permission se activó?
- Busca en log "Registre el permiso para observar"

### Fix 4: OSES/PortableContext regenerados
- ¿latest.json de self_examination tiene fecha de HOY?
- ¿latest.json de portable_context tiene fecha de HOY?
- Busca en log "startup_truth_refresh: OSES re-persisted"
- Busca en log "startup_truth_refresh: PortableContext re-persisted"
- Busca en log "stale metacognition" — si aparece, el fix detectó datos
  viejos y forzó refresh
- Busca en runtime_audit.jsonl evento kind="metacognition_refresh"

### Fix 5: CredentialBroker con tracing
- Busca en log "credential_broker.request" — ¿se emitieron solicitudes?
- Si dice "no handler registered": el broker no está conectado a la UI
  y los diálogos de credenciales no aparecerán
- Busca en runtime_audit.jsonl eventos permission con
  permission_id="credential:*"

==========================================================================
FASE 6: REPORTE ESTRUCTURADO
==========================================================================

Genera el reporte con ESTA estructura:

---

# DIAGNÓSTICO PROFUNDO — IABV v1.5
**Generado**: [fecha y hora]
**Sesión analizada**: [duración total]
**Commit**: [HEAD commit hash si disponible]

## 1. RESUMEN EJECUTIVO (máximo 5 líneas)
[¿Se congela? ¿Puede hacer consultas externas? ¿La metacognición está
completa? ¿Los fixes del PR #348 funcionan? Veredicto en una frase.]

## 2. CONGELAMIENTO POST-CARGA (PROBLEMA 1)

### Timeline del arranque
| Hito | elapsed_ms | Duración | Estado |
|------|-----------|----------|--------|
| ... | ... | ... | OK/⚠️/❌ |

### Causa raíz identificada
[Explicación técnica precisa: qué hilo se bloquea, por qué, dónde]

### Evidencia
[Datos específicos de runtime_audit, startup_timeline, iabv_v15.log]

### Hipótesis verificadas
| Hipótesis | Resultado | Evidencia |
|-----------|-----------|-----------|
| H1: wire_services I/O síncrono | ✅/❌/⚠️ | ... |
| H2: deferred_post bloquea Qt | ✅/❌/⚠️ | ... |
| ... | ... | ... |

## 3. MICRO-CONGELACIÓN EN CONSULTA (PROBLEMA 2)

### Timeline de la consulta
| Paso | elapsed_ms | Duración | Observación |
|------|-----------|----------|-------------|
| ... | ... | ... | ... |

### Causa raíz identificada
[Qué paso específico de sendChat() → respuesta congela la UI]

### Evidencia
[Datos]

## 4. CONSULTA EXTERNA FALLIDA (PROBLEMA 3)

### Flujo de decisión reconstruido
```
[Diagrama del flujo real con datos — no teórico, basado en evidencia]
```

### Nodos del flujo verificados
| Nodo | ¿Se ejecutó? | Resultado | Evidencia |
|------|-------------|-----------|-----------|
| ... | ... | ... | ... |

### Metacognición aplicada
| Capa | ¿Consultada? | Qué dijo | Veredicto |
|------|-------------|----------|-----------|
| WorldModel | ? | ... | OK/falta |
| Governance | ? | ... | OK/falta |
| OSES | ? | ... | OK/falta |
| PortableContext | ? | ... | OK/falta |
| DecisionAuditTrail | ? | ... | OK/falta |
| ExperimentLab | ? | ... | OK/falta |

### Por qué falló (explicación completa)
[El camino metacognitivo completo que tomó, paso a paso, con datos]

## 5. VERIFICACIÓN DE FIXES PR #348

| Fix | Estado | Evidencia |
|-----|--------|-----------|
| RuntimeAuditTracer genera datos | ✅/❌ | ¿runtime_audit.jsonl existe y tiene eventos? |
| Botón "Permitir observación" | ✅/❌ | ¿approval_dialog_visible fue true cuando debía? |
| Auto-resolver permisos desde chat | ✅/❌ | ¿_try_resolve detectó mensaje afirmativo? |
| OSES/PortableContext regenerados | ✅/❌ | ¿Fecha de hoy? ¿Log dice "re-persisted"? |
| CredentialBroker con tracing | ✅/❌ | ¿Hay eventos credential en audit? |

## 6. QUÉ NECESITA EL PROGRAMA PARA FUNCIONAR AL 100%

### Requisitos operativos verificados
| Requisito | Estado | Acción necesaria |
|-----------|--------|-----------------|
| runtime_audit.jsonl se genera | ✅/❌ | [acción si falta] |
| Diálogos de permisos aparecen | ✅/❌ | [acción si falta] |
| ChatGPT accesible | ✅/❌ | [acción si falta] |
| OSES actualizado (<24h) | ✅/❌ | [acción si falta] |
| PortableContext actualizado (<24h) | ✅/❌ | [acción si falta] |
| CredentialBroker conectado a UI | ✅/❌ | [acción si falta] |
| Sin congelamiento post-carga | ✅/❌ | [acción si falta] |
| Sin micro-freeze en consultas | ✅/❌ | [acción si falta] |
| Workers externos registrados | ✅/❌ | [acción si falta] |
| Tokens/API keys disponibles | ✅/❌ | [acción si falta] |
| Red funcional para Groq/OpenAI | ✅/❌ | [acción si falta] |
| SQLite sin locks recurrentes | ✅/❌ | [acción si falta] |
| FreezeIncidentReporter activo | ✅/❌ | [acción si falta] |

### Bloqueadores críticos (resolver primero)
[Lista ordenada por prioridad de lo que bloquea el funcionamiento]

### Mejoras recomendadas (después de resolver bloqueadores)
[Lista ordenada de mejoras que aumentarían la autonomía]

## 7. FIXES RECOMENDADOS

### Fix #1: [título]
- **Archivo**: src/iabv_v15/[ruta]
- **Línea**: [N]
- **Cambio**: [descripción precisa]
- **Por qué funciona**: [explicación]
- **Riesgo**: [bajo/medio/alto]

## 8. PRÓXIMOS PASOS
[Qué hacer ahora — priorizado]

---

==========================================================================
HERRAMIENTAS MCP (si tienes acceso)
==========================================================================

| Tool | Qué devuelve |
|------|-------------|
| runtime_boot_report() | Reporte del arranque |
| runtime_trace_summary() | Resumen del trace |
| runtime_trace_events(kind="error") | Errores |
| runtime_trace_events(kind="external_query") | Queries externas |
| runtime_trace_events(kind="permission") | Permisos |
| report_freeze(description="...") | Captura snapshot NOW |
| list_freeze_reports() | Reportes previos |
| self_examination_current() | OSES |
| portable_context_get() | Contexto portable |
| world_model_snapshot() | World model |
| run_self_audit() | Auditoría de coherencia |

==========================================================================
REGLAS
==========================================================================

1. NO propongas refactors masivos. Cambios mínimos verificables.
2. NO crees servicios nuevos. Usa los existentes.
3. NO modifiques domain/models.py ni capas P1-P4 sin justificación.
4. Lee AGENTS.md antes de proponer cambios al código.
5. Cada fix = archivo + línea + cambio + justificación.
6. Prioriza: congelamiento > consulta fallida > metacognición > mejoras.
7. Si faltan datos para confirmar una hipótesis, márcala 🔍 sin datos.
8. El diagnóstico debe ser REPRODUCIBLE — otro agente debe poder
   verificar las mismas conclusiones con los mismos datos.

==========================================================================
ARQUITECTURA RÁPIDA
==========================================================================

Bootstrap: src/iabv_v15/bootstrap.py (~4000 líneas, wiring completo)
Orquestador: AdaptiveTaskOrchestrator (decide rutas, governance, preflight)
Queries externas: preflight_external_assistant() → ToolAdapter → HTTP
Permisos: AutonomyGovernancePolicy + permission_gates en WorldModel
Diálogos UI: ClarificationRequestService + CredentialBroker
  → Signal clarificationRequested / credentialPromptRequested
  → Popup approvalPopup en ControlCenterPage.qml
  → Botón "Permitir observación" (PR #348)
Chat: sendChat() → _try_handle_chat_command → _try_resolve_pending_observation_permission (PR #348) → shortcuts → worker()
Autoexamen: OSES → build_review() → latest.json
Contexto: PortableContextService → build_package() → latest.json
Mundo: WorldModelService → request_refresh() → permission_gates
Recursos: _assess_resource_pressure() en Orchestrator
Aprendizaje: ExperimentLab + StrategySelector + AdaptiveWeightLayer
Freeze: FreezeIncidentReporter (snapshot en freeze_*.json)
Tracer: RuntimeAuditTracer (trace continuo en runtime_audit.jsonl)
Auto-refresh: _final_startup_truth_refresh() + _metacognition_data_is_stale() (PR #348)
```

---

## Cómo usar este prompt

1. Arranca IABV normalmente
2. Úsalo como siempre — intenta consultar ChatGPT, escribe en el chat
3. Cuando veas el congelamiento, espera a que se recupere
4. Abre Windsurf
5. Copia TODO el bloque de arriba (desde ` ``` ` hasta ` ``` `)
6. Pégalo en Windsurf
7. Windsurf leerá los archivos y te dará el diagnóstico completo

Si el programa se congeló y tuviste que cerrarlo, los datos persisten
en disco — el diagnóstico funciona igual.
