# Prompt diagnóstico para Windsurf / cualquier IA

Copia y pega este prompt completo en Windsurf (o cualquier agente)
cuando IABV se congele o tengas un problema. Reemplaza los `[...]`
con la información real.

---

## Prompt

```
Soy el desarrollador de IABV v1.5, una aplicación Python/PySide6/QML
de metacognición local. El programa tiene un sistema de auto-auditoría
continua que genera reportes estructurados.

### Estado actual del problema

[Describe aquí qué pasó: "se congela al abrir el panel de evolución",
"no puede hacer consultas a ChatGPT", "la ventana tarda 30 segundos
en aparecer", etc.]

### Reportes disponibles para tu análisis

El programa genera estos archivos automáticamente — léelos para
diagnosticar:

1. **Trace de auditoría continua** (JSONL, cada línea es un evento):
   `C:\Python\IABV_v1.5\data\logs\runtime_audit.jsonl`
   Contiene: service_init (con duración), decision, external_query,
   permission, error, ui_event, resource_snapshot

2. **Reportes de incidentes/freezes** (JSON individual por incidente):
   `C:\Python\IABV_v1.5\data\evolution\incident_reports\freeze_*.json`
   Contiene: recursos RAM/CPU, hilos, estado SQLite, timeline de
   startup, hallazgos OSES, cola de tareas, señales de riesgo

3. **Self-examination snapshot**:
   `C:\Python\IABV_v1.5\data\evolution\self_examination\latest.json`
   Contiene: hallazgos de degradación, patrones repetidos, ajustes
   recomendados

4. **Contexto portable**:
   `C:\Python\IABV_v1.5\data\evolution\portable_context\latest.json`
   Contiene: resumen del estado del sistema, health score, trends

5. **World model**:
   `C:\Python\IABV_v1.5\data\evolution\world_model\`
   Contiene: ventanas abiertas, herramientas, red, foco, bloqueos

### También puedes usar los MCP tools

Si tienes acceso al servidor MCP de IABV:

- `runtime_boot_report()` — reporte estructurado del arranque
  (servicios fallidos, lentos, queries externas, permisos denegados)
- `runtime_trace_events(kind="error", limit=50)` — errores recientes
- `runtime_trace_events(kind="external_query")` — queries externas
- `runtime_trace_events(kind="service_init")` — inicialización de servicios
- `runtime_trace_summary()` — resumen general del trace
- `report_freeze(description="[lo que pasó]")` — captura snapshot ahora
- `list_freeze_reports()` — lista reportes previos
- `autonomy_status()` — estado de tareas pendientes
- `self_examination_review()` — hallazgos OSES

### Arquitectura clave

- Bootstrap: `src/iabv_v15/bootstrap.py` — wiring de todos los servicios
- Orquestador: `AdaptiveTaskOrchestrator` — decide rutas/proveedores
- Queries externas: pasan por `ToolTeachService` → `ToolAdapter` → HTTP
- Permisos: `AutonomyGovernancePolicy` bloquea rutas sin permiso
- Diálogos UI: `ClarificationRequestService` + `CredentialBroker`
- Config: `src/iabv_v15/infra/config.py`
- Models: `src/iabv_v15/domain/models.py`
- AGENTS.md tiene las reglas completas del proyecto

### Lo que necesito de ti

1. Lee el `runtime_audit.jsonl` y el último `freeze_*.json`
2. Identifica: qué servicios fallaron, qué tardó más de lo normal,
   qué queries externas fallaron y por qué
3. Dame un diagnóstico: ¿por qué se congela? ¿qué está desconectado?
4. Propon un fix específico (archivo + línea + cambio)

NO hagas refactor masivo. NO crees nuevos servicios ni orquestadores.
Lee AGENTS.md antes de cambiar cualquier código.
```

---

## Notas para el usuario

- El trace se activa automáticamente al arrancar IABV
- Se puede desactivar con `$env:IABV_RUNTIME_TRACE='0'` si consume
  demasiado disco
- Los archivos JSONL crecen ~1 KB/minuto en uso normal
- Puedes borrar `runtime_audit.jsonl` en cualquier momento sin romper nada
