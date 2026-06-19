# IABV v1.5 - Operational Self Examination

Generado: 2026-05-09T14:56:17.004395+00:00
Resumen: Autoexaminacion needs_attention: 20 hallazgos activos. Lo mas fuerte ahora es bootstrap init lento: 16899ms. Mejoras validadas: 1 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- Bootstrap init lento: 16899ms: El paso bootstrap_init_start->bootstrap_init_done duro 16899ms (umbral 4000ms). Esto retiene el GUI thread antes de que aparezca el splash.  [observado: 16898.8ms, umbral: 4000.0ms] | recomendacion: Diferir scans de cuentas, instalacion de mcp_client y probes de proveedores de bootstrap.__init__ a un QTimer post-show. Patron ya aplicado a _log_tool_availability en PR #257. | confianza 0.90
- UniversalAutonomyIndex: INSUFICIENTE (autonomia=50%): AutonomyScore=50% (objetivo >80%), ResilienceScore=35% (objetivo >75%), CalibrationError=0.11 (objetivo <0.10), BlindSpotRatio=17% (objetivo <30%). Componente mas debil: capability_coverage (0%). | recomendacion: Mejorar tasa de exito de tareas. Revisar rutas que fallan frecuentemente en ExperimentLab y rotar a proveedores mas confiables. | confianza 0.88
- Loop introspectivo abierto: 3 mecanismo(s) inactivo(s):  | recomendacion: sin ajuste concreto | confianza 0.00
- multi_source_disagreement repetido en logs: Detectadas 6 ocurrencias de "multi_source_disagreement" en las ultimas 500 lineas del log. Ejemplo reciente: 2026-05-09 00:14:17,602 | INFO | iabv_v15.services.tools.tool_adapters | multi_source_disagreement: claude_installed — positives=['process'] negatives=['filesystem', 'window'] | La herramienta existe  | recomendacion: El cache de 300s puede no ser suficiente o el MCP polling recrea instancias que pierden el cache. Considerar aumentar TTL o mover cache a nivel de clase persistente. | confianza 0.90
- Herramienta faltante reportada en logs: Detectadas 5 ocurrencias de "tool_missing" en las ultimas 500 lineas del log. Ejemplo reciente: 2026-05-09 00:14:21,363 | INFO | iabv_v15.bootstrap | tool_missing: aider_coder — adapter=aider | fix: pip install aider-chat (optional, heavy ~200MB; installed in background) | recomendacion: Verificar si la herramienta faltante es necesaria para el flujo actual o si existe un fallback disponible. | confianza 0.90
- Ruido excesivo de logs HTTP (httpx): Detectadas 9 ocurrencias de "HTTP Request:" en las ultimas 500 lineas del log. Ejemplo reciente: 2026-05-09 00:18:11,521 | INFO | httpx | HTTP Request: GET http://127.0.0.1:11434/api/tags "HTTP/1.1 200 OK" | recomendacion: Demasiadas lineas de httpx poluciona el log y dificulta encontrar hallazgos importantes. Auto-suprimir httpx a WARNING cuando exceda el umbral. | confianza 0.90

## Ajustes recomendados
- Bootstrap init lento: 16899ms: Diferir scans de cuentas, instalacion de mcp_client y probes de proveedores de bootstrap.__init__ a un QTimer post-show. Patron ya aplicado a _log_tool_availability en PR #257. | fuente data/logs/startup_timeline.jsonl, iabv_v15.infra.startup_timeline
- UniversalAutonomyIndex: INSUFICIENTE (autonomia=50%): Mejorar tasa de exito de tareas. Revisar rutas que fallan frecuentemente en ExperimentLab y rotar a proveedores mas confiables. | fuente ExperimentLab, TaskOutcomeRecorder, DecisionAuditTrail, WorldModelSnapshot
- multi_source_disagreement repetido en logs: El cache de 300s puede no ser suficiente o el MCP polling recrea instancias que pierden el cache. Considerar aumentar TTL o mover cache a nivel de clase persistente. | fuente runtime_log, C:\Python\IABV_v1.5\data\logs\iabv_v15.log
- Herramienta faltante reportada en logs: Verificar si la herramienta faltante es necesaria para el flujo actual o si existe un fallback disponible. | fuente runtime_log, C:\Python\IABV_v1.5\data\logs\iabv_v15.log
- Ruido excesivo de logs HTTP (httpx): Demasiadas lineas de httpx poluciona el log y dificulta encontrar hallazgos importantes. Auto-suprimir httpx a WARNING cuando exceda el umbral. | fuente runtime_log, C:\Python\IABV_v1.5\data\logs\iabv_v15.log
- Blocked interaction episodes: 1 of 5 recent: Review blocked interactions for access, quota or preflight issues. | fuente n/d

## Mejoras validadas
- cloud_provider por cloud: Recomiendo cloud para cloud_reasoning en cloud_provider:groq usando cloud_provider con configuracion cloud:groq por score base 0.79 y score adaptativo 1.09 con 21 muestra(s). Ajuste adaptativo: historial de exito 100%; reutilizacion alta 100%. | confianza 1.00

## Retroalimentacion de ajustes
- Bootstrap init lento: 16899ms: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- UniversalAutonomyIndex: INSUFICIENTE (autonomia=50%): no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- multi_source_disagreement repetido en logs: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- Herramienta faltante reportada en logs: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.

UNRESOLVED: UNRESOLVED:world_model, UNRESOLVED:validation_cycle, UNRESOLVED:adaptive_sessions