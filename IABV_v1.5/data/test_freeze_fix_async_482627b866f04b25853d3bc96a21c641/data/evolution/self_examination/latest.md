# IABV v1.5 - Operational Self Examination

Generado: 2026-05-09T20:57:36.243502+00:00
Resumen: Autoexaminacion watch: 10 hallazgos activos. Lo mas fuerte ahora es excessive_polling_threads. Mejoras validadas: 1 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- excessive_polling_threads: 5 hilos de polling activos: ['ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'prebuild-snap-refresh', 'ui-bridge-server']. Cada uno ejecuta scans periodicos que compiten por CPU y GIL. | recomendacion: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | confianza 0.90
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente. | recomendacion: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | confianza 0.85
- 5 platforms need learning: Low confidence platforms: Groq Console, Google AI Studio, OpenRouter, GitHub, Ollama Local API. Consider learning sessions. | recomendacion: Run learn_platform() for low-confidence platforms | confianza 0.70
- Loop introspectivo abierto: 4 mecanismo(s) inactivo(s):  | recomendacion: sin ajuste concreto | confianza 0.00

## Ajustes recomendados
- excessive_polling_threads: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | fuente runtime_performance_monitor
- 3 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner
- 5 platforms need learning: Run learn_platform() for low-confidence platforms | fuente n/d
- UniversalAutonomyIndex: datos insuficientes: Ejecutar mas tareas para acumular datos de rendimiento. Las metricas se calcularan automaticamente cuando haya suficiente evidencia. | fuente OperationalSelfExaminationService._universal_autonomy_index_findings

## Mejoras validadas
- iabv_self por background: Hay una mejora fuerte en experimentos recientes, pero todavia no un recommendation consolidado. | confianza 0.58

## Retroalimentacion de ajustes
- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, autonomy_score, UNRESOLVED:adaptive_sessions