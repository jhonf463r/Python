# Prompt Windsurf — Reporte en Vivo de IABV v1.5 (Fuente de Verdad)

> **Instrucciones para el usuario**: Copia TODO este prompt y pégalo en Windsurf
> mientras IABV esté corriendo (o después de cerrarlo). Windsurf leerá los datos
> que el programa generó automáticamente y producirá un reporte estructurado que
> sirve como **fuente de verdad** de lo que pasó en cada segundo.
>
> Si IABV ya se cerró o se congeló, los archivos de datos persisten en disco —
> el reporte funciona igual.

---

## Prompt (copiar desde aquí)

```
Eres el auditor en vivo de IABV v1.5 — un programa Python/PySide6/QML de
metacognición local que corre en esta máquina Windows. Tu trabajo es generar
un REPORTE EN VIVO que sea la FUENTE DE VERDAD de todo lo que pasó en el
programa desde que arrancó hasta este momento.

Este reporte debe ser legible por cualquier IA (Devin, ChatGPT, Claude, el
mismo IABV) y por el usuario humano. Debe conectar lo que el usuario VE en
pantalla con lo que el código está HACIENDO internamente.

==========================================================================
FASE 1: LECTURA DE DATOS (no toques código, solo lee)
==========================================================================

Lee estos archivos en orden. Son generados automáticamente por IABV:

### 1.1 Trace de auditoría continua (PRIORIDAD MÁXIMA)
Ruta: C:\Python\IABV_v1.5\data\logs\runtime_audit.jsonl

Formato: JSONL — cada línea es un evento JSON con:
- ts: timestamp ISO UTC
- elapsed_ms: milisegundos desde el arranque del programa
- seq: número secuencial del evento
- kind: tipo de evento (ver abajo)
- data: payload específico del tipo

Tipos de evento (kind):
- service_init: un servicio se inicializó
  → data.service, data.duration_ms, data.status (ok/error), data.error,
    data.dependencies[]
- decision: el orquestador tomó una decisión
  → data.decision_point, data.algorithm, data.inputs, data.result,
    data.confidence
- external_query: intento de contactar servicio externo
  → data.target (ChatGPT/Ollama/Devin/GitHub), data.operation,
    data.status (ok/error/timeout), data.duration_ms, data.error,
    data.response_summary
- permission: chequeo de permiso
  → data.permission_id, data.action, data.granted (true/false/null),
    data.reason, data.dialog_shown
- error: excepción o error
  → data.context, data.error_type, data.message
- ui_event: evento de interfaz
  → data.event_type, data.component
- resource_snapshot: snapshot periódico de recursos
  → data.ram_used_pct, data.cpu_load, data.thread_count

### 1.2 Reportes de incidentes / congelamientos
Ruta: C:\Python\IABV_v1.5\data\evolution\incident_reports\freeze_*.json

Cada archivo JSON contiene un snapshot completo del momento del freeze:
- resources: RAM, CPU, procesos pesados
- threads: hilos activos y qué hacían
- sqlite: estado de bloqueo de la base de datos
- startup_timeline: hitos del arranque
- oses_findings: hallazgos de autoexaminación
- pending_queue: tareas que el programa intentaba ejecutar
- process_info: PID, uptime, memoria

### 1.3 Autoexaminación operativa (OSES)
Ruta: C:\Python\IABV_v1.5\data\evolution\self_examination\latest.json

Contiene: degradaciones detectadas, patrones repetidos, ajustes
recomendados y si los ajustes previos funcionaron o no.

### 1.4 Contexto portable
Ruta: C:\Python\IABV_v1.5\data\evolution\portable_context\latest.json

Contiene: resumen comprimido del estado del sistema, health score de
cloud reasoning, trends por proveedor, recomendaciones.

### 1.5 Decision Audit Trail
Ruta: C:\Python\IABV_v1.5\data\evolution\decision_audit\decisions.jsonl

Historial de decisiones cloud: proveedor, latencia, confianza, resultado.

### 1.6 World Model
Ruta: C:\Python\IABV_v1.5\data\evolution\world_model\

Snapshot del mundo: ventanas abiertas, herramientas disponibles, red,
foco, bloqueos activos.

### 1.7 Self Audit
Ruta: C:\Python\IABV_v1.5\data\evolution\self_audit\

Auditoría read-only de coherencia entre capas del sistema.

### 1.8 Log del programa
Ruta: C:\Python\IABV_v1.5\data\logs\iabv_v15.log

Log estándar con timestamps — busca "ERROR", "WARNING", "startup_timeline",
"freeze", "timeout", "locked" para encontrar problemas rápido.

==========================================================================
FASE 2: ANÁLISIS (construir la línea de tiempo)
==========================================================================

Con los datos leídos, construye una LÍNEA DE TIEMPO segundo a segundo:

### 2.1 Timeline del arranque
Para cada service_init en runtime_audit.jsonl, ordena por elapsed_ms:
- ¿Qué servicios se inicializaron primero y cuánto tardaron?
- ¿Cuáles fallaron (status != "ok")? ¿Con qué error?
- ¿Cuáles fueron lentos (duration_ms > 500ms)?
- ¿Hay dependencias circulares o rotas?

### 2.2 Queries externas
Para cada external_query:
- ¿A qué servicio intentó conectarse? (ChatGPT, Ollama, Devin, GitHub)
- ¿Funcionó? Si no, ¿cuál fue el error?
- ¿Se mostró un diálogo de permisos al usuario? (dialog_shown)
- ¿El permiso fue denegado? ¿Por qué?
- IMPORTANTE: Si NINGUNA query externa se intentó, eso es un hallazgo
  crítico — significa que el programa no puede razonar con IAs externas.

### 2.3 Permisos
Para cada permission:
- ¿Qué permisos se verificaron?
- ¿Cuáles fueron denegados?
- ¿Se mostraron diálogos de autorización al usuario?
- IMPORTANTE: Si dialog_shown es siempre false y granted es siempre
  null, el sistema de diálogos de permisos no está funcionando.

### 2.4 Errores
Para cada error:
- ¿En qué contexto ocurrió?
- ¿Es un error repetido (mismo error_type y message)?
- ¿Correlaciona con un freeze posterior?

### 2.5 Estado de recursos
Para cada resource_snapshot:
- ¿Hay picos de RAM o CPU?
- ¿El thread_count crece sin control?
- ¿Correlaciona con los momentos de freeze?

### 2.6 Eventos UI
Para cada ui_event:
- ¿Qué interacciones del usuario se registraron?
- ¿Hay gaps largos donde no se registra nada? (indica freeze)

==========================================================================
FASE 3: DIAGNÓSTICO (identificar problemas raíz)
==========================================================================

### 3.1 Análisis de congelamientos
Si hay freezes o gaps en la timeline:
1. ¿Qué estaba haciendo el programa justo antes del freeze?
2. ¿Había un bloqueo SQLite? (busca "locked" en sqlite status)
3. ¿Había una query externa sin timeout?
4. ¿El hilo principal (MainThread) estaba bloqueado?
5. ¿Había presión de recursos (RAM > 80%, CPU > 90%)?

### 3.2 Análisis de queries externas fallidas
Si no puede conectarse a ChatGPT u otros:
1. ¿Existe el token/API key en el entorno? Revisa bootstrap.py:
   - GITHUB_TOKEN_IABV / IABV_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN
   - DEVIN_API_KEY_IABV / IABV_DEVIN_API_KEY / DEVIN_API_KEY
   - OPENAI_API_KEY / GROQ_API_KEY / GOOGLE_AI_API_KEY
2. ¿El AutonomyGovernancePolicy está bloqueando la ruta?
3. ¿El ToolAdapter correspondiente fue inicializado correctamente?
4. ¿Hay red disponible? (WorldModel → network status)

### 3.3 Análisis de diálogos de permisos ausentes
Si el programa no muestra ventanas emergentes de permisos:
1. Revisa ClarificationRequestService — ¿está inicializado?
2. Revisa CredentialBroker — ¿está conectado al UI?
3. Revisa AutoCorrectionEngine.auto_provision_missing_secrets() —
   ¿se invocó? ¿Funcionó?
4. El contrato dice: "El usuario NUNCA debe abrir PowerShell para
   configurar tokens" — si esto no se cumple, es un bug.

### 3.4 Coherencia entre capas
Compara:
- Lo que dice WorldModel (herramientas disponibles) vs lo que dice
  ToolRegistry (tools registradas) vs lo que dice SelfAudit
- Lo que dice OSES (hallazgos) vs lo que dice PortableContext (trends)
- Si hay contradicciones, son hallazgos críticos

==========================================================================
FASE 4: REPORTE ESTRUCTURADO (generar la fuente de verdad)
==========================================================================

Genera el reporte con EXACTAMENTE esta estructura:

---

# REPORTE EN VIVO — IABV v1.5
**Generado**: [fecha y hora]
**Fuente**: runtime_audit.jsonl + incident_reports + OSES + PortableContext
**Sesión**: desde [timestamp primer evento] hasta [timestamp último evento]
**Duración total**: [elapsed_ms del último evento]

## 1. RESUMEN EJECUTIVO (3-5 líneas máximo)
[Estado general: ¿funciona? ¿se congela? ¿puede razonar con IAs externas?
¿los diálogos de permisos aparecen? Veredicto en una frase.]

## 2. TIMELINE DEL ARRANQUE

| Fase | Servicio | Duración | Estado | Problema |
|------|----------|----------|--------|----------|
| [elapsed_ms] | [nombre] | [duration_ms]ms | OK/ERROR | [descripción] |

**Tiempo total de arranque**: [ms]
**Servicios fallidos**: [lista]
**Cuellos de botella** (> 500ms): [lista]

## 3. QUERIES EXTERNAS

| Timestamp | Target | Operación | Estado | Duración | Error |
|-----------|--------|-----------|--------|----------|-------|
| [ts] | [target] | [op] | ok/error/timeout | [ms] | [error] |

**Servicios alcanzables**: [lista]
**Servicios inalcanzables**: [lista con razón]
**Diálogos mostrados al usuario**: [sí/no — cuáles]

## 4. PERMISOS Y GOBERNANZA

| Permiso | Acción | Concedido | Diálogo mostrado | Razón |
|---------|--------|-----------|------------------|-------|
| [id] | [action] | sí/no/desconocido | sí/no | [razón] |

**Rutas bloqueadas por gobernanza**: [lista]
**Permisos nunca verificados**: [lista — si faltan es un hallazgo]

## 5. ERRORES DETECTADOS

| # | Timestamp | Contexto | Tipo | Mensaje | Recurrente? |
|---|-----------|----------|------|---------|-------------|
| 1 | [ts] | [ctx] | [type] | [msg] | sí/no (N veces) |

**Errores únicos**: [N]
**Errores recurrentes** (potenciales loops): [lista]

## 6. ESTADO DE RECURSOS

| Timestamp | RAM% | CPU% | Hilos | Anomalía |
|-----------|------|------|-------|----------|
| [ts] | [%] | [%] | [N] | [descripción] |

**Pico de RAM**: [%] a las [ts]
**Pico de CPU**: [%] a las [ts]
**Hilos máximos**: [N]

## 7. CONGELAMIENTOS DETECTADOS

### Freeze #N — [timestamp]
- **Duración estimada**: [gap en la timeline]
- **Causa probable**: [SQLite lock / query sin timeout / UI bloqueado / RAM]
- **Evidencia**: [datos específicos del runtime_audit o freeze report]
- **Estado de hilos**: [qué estaba haciendo cada hilo]
- **SQLite**: [locked/ok]

## 8. NERVIOS DESCONECTADOS
[Servicios que deberían estar funcionando pero no lo están.
Mapea cada servicio a su rol en el "sistema nervioso" del programa:]

| Nervio | Servicio | Estado | Impacto |
|--------|----------|--------|---------|
| Percepción | UniversalPerceptionService | [ok/desconectado] | [qué pierde] |
| Decisión | AdaptiveTaskOrchestrator | [ok/desconectado] | [qué pierde] |
| Memoria | ExperimentLab + StrategySelector | [ok/desconectado] | [qué pierde] |
| Aprendizaje | TaskOutcomeRecorder + AdaptiveWeightLayer | [ok/desconectado] | [qué pierde] |
| Autoexamen | OSES | [ok/desconectado] | [qué pierde] |
| Regulación | _assess_resource_pressure | [ok/desconectado] | [qué pierde] |
| Contexto | PortableContextService | [ok/desconectado] | [qué pierde] |
| Herramientas | ToolRegistry + ToolAdapters | [ok/desconectado] | [qué pierde] |
| UI Bridge | ViewModels → Services | [ok/desconectado] | [qué pierde] |
| Diálogos | ClarificationRequest + CredentialBroker | [ok/desconectado] | [qué pierde] |

## 9. HALLAZGOS DE METACOGNICIÓN
[Lee OSES latest.json y PortableContext latest.json:]

### 9.1 OSES dice:
- Degradaciones: [lista]
- Patrones repetidos: [lista]
- Ajustes recomendados: [lista]
- ¿Los ajustes previos funcionaron? [sí/no/sin datos]

### 9.2 PortableContext dice:
- Health score: [N/10]
- Trends por proveedor: [lista]
- Recomendaciones: [lista]

### 9.3 Contradicciones entre capas:
[Si OSES dice una cosa y PortableContext otra, documentar aquí]

## 10. DIAGNÓSTICO FINAL

### Causa raíz del congelamiento:
[Explicación técnica precisa con referencias a archivos y líneas]

### Por qué no puede hacer queries externas:
[Explicación con evidencia del trace]

### Por qué no muestra diálogos de permisos:
[Explicación con evidencia]

### Servicios que necesitan reconexión:
[Lista priorizada con el fix específico]

## 11. FIXES RECOMENDADOS (específicos, no genéricos)

### Fix #1: [título]
- **Archivo**: src/iabv_v15/[ruta]
- **Línea**: [N]
- **Cambio**: [descripción precisa del cambio]
- **Por qué funciona**: [explicación]
- **Riesgo**: [bajo/medio/alto]

### Fix #2: ...

## 12. PRÓXIMOS PASOS
[Qué debe hacer el usuario o la próxima sesión de IA]

---

==========================================================================
FASE 5: HERRAMIENTAS MCP DISPONIBLES (si tienes acceso al servidor MCP)
==========================================================================

Si Windsurf tiene acceso al servidor MCP de IABV (puerto local), puedes
ejecutar estas tools en vez de leer archivos:

| Tool | Qué devuelve |
|------|-------------|
| runtime_boot_report() | Reporte estructurado del arranque |
| runtime_trace_summary() | Resumen del trace (conteos, errores, uptime) |
| runtime_trace_events(kind="error", limit=50) | Últimos 50 errores |
| runtime_trace_events(kind="external_query") | Queries externas |
| runtime_trace_events(kind="service_init") | Init de servicios |
| runtime_trace_events(kind="decision") | Decisiones del orquestador |
| runtime_trace_events(kind="permission") | Chequeos de permisos |
| report_freeze(description="...") | Captura snapshot NOW |
| list_freeze_reports() | Lista reportes previos |
| self_examination_current() | Hallazgos OSES |
| portable_context_get() | Contexto portable actual |
| world_model_snapshot() | World model vivo |
| run_self_audit() | Auditoría de coherencia entre capas |
| autonomy_status() | Estado de tareas pendientes |

==========================================================================
REGLAS QUE DEBES SEGUIR
==========================================================================

1. NO hagas refactor masivo. Cambios mínimos y verificables.
2. NO crees nuevos servicios ni orquestadores. Usa los existentes.
3. NO modifiques domain/models.py ni capas cerradas (P1-P4) sin justificación.
4. Lee AGENTS.md (C:\Python\IABV_v1.5\IABV_v1.5\AGENTS.md) antes de
   proponer cambios al código.
5. Prioriza: primero lo que congela el programa, luego lo que no funciona,
   luego lo que falta.
6. Cada fix debe tener archivo + línea + cambio específico.
7. El reporte debe ser reproducible — otro agente puede leer los mismos
   datos y llegar a las mismas conclusiones.

==========================================================================
CONTEXTO DE ARQUITECTURA RÁPIDO
==========================================================================

Bootstrap: src/iabv_v15/bootstrap.py — wiring de todos los servicios (~4000 líneas)
Orquestador: AdaptiveTaskOrchestrator — decide rutas/proveedores
Queries externas: ToolTeachService → ToolAdapter → HTTP
Permisos: AutonomyGovernancePolicy bloquea rutas sin permiso
Diálogos UI: ClarificationRequestService + CredentialBroker
Autoexamen: OperationalSelfExaminationService (OSES)
Contexto: PortableContextService
Mundo: WorldModelService
Recursos: _assess_resource_pressure() en Orchestrator
Aprendizaje: ExperimentLab + StrategySelector + AdaptiveWeightLayer
Self audit: SelfAuditService (read-only, coherencia entre capas)
Freeze reporter: FreezeIncidentReporter (snapshot de incidentes)
Runtime tracer: RuntimeAuditTracer (trace continuo JSONL)
Config: src/iabv_v15/infra/config.py
Models: src/iabv_v15/domain/models.py

Tokens esperados en el entorno:
- GitHub: GITHUB_TOKEN_IABV > IABV_GITHUB_TOKEN > GITHUB_TOKEN > GH_TOKEN
- Devin: DEVIN_API_KEY_IABV > IABV_DEVIN_API_KEY > DEVIN_API_KEY
- OpenAI: OPENAI_API_KEY
- Groq: GROQ_API_KEY
- Google: GOOGLE_AI_API_KEY
- Secretos en: ~/.iabv_secrets.ps1 (auto-cargados por bootstrap)
```

---

## Uso rápido

### Caso 1: IABV se congeló
1. Copia este prompt completo
2. Pégalo en Windsurf
3. Windsurf leerá `runtime_audit.jsonl` y `freeze_*.json`
4. Te dará diagnóstico + fix específico

### Caso 2: IABV funciona pero algo no va bien
1. Copia este prompt completo
2. Pégalo en Windsurf
3. Agrega al final: "El problema específico es: [describe aquí]"
4. Windsurf correlacionará tu descripción con los datos internos

### Caso 3: Quieres un reporte general de salud
1. Copia este prompt completo
2. Pégalo en Windsurf
3. Agrega al final: "Genera reporte completo de salud sin problema
   específico"

### Caso 4: Quieres que otra IA (Devin/ChatGPT) analice
1. Copia los archivos que te interesen:
   - `data\logs\runtime_audit.jsonl` (trace completo)
   - `data\evolution\incident_reports\freeze_*.json` (último freeze)
   - `data\evolution\self_examination\latest.json` (autoexamen)
2. Pega este prompt + los datos en la otra IA

---

## Notas técnicas

- El trace se activa automáticamente al arrancar IABV (PR #346)
- Se puede desactivar con `$env:IABV_RUNTIME_TRACE='0'`
- runtime_audit.jsonl crece ~1 KB/min en uso normal
- Se puede borrar sin romper nada — se regenera al arrancar
- Los freeze reports son independientes — uno por incidente
- El programa necesita tener mergeado el PR #346 (branch
  devin/1778027899-freeze-incident-reporter) para generar estos datos
