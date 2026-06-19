# IABV v1.5 - Operational Self Examination

Generado: 2026-05-09T20:57:44.887238+00:00
Resumen: Autoexaminacion watch: 11 hallazgos activos. Lo mas fuerte ahora es excessive_polling_threads. Mejoras validadas: 0 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- excessive_polling_threads: 6 hilos de polling activos: ['ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'prebuild-snap-refresh', 'ui-bridge-server', 'ui-bridge-server']. Cada uno ejecuta scans periodicos que compiten por CPU y GIL. | recomendacion: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | confianza 0.90
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- excessive_threads: 21 hilos activos en el proceso. Python GIL causa contention entre hilos — cada hilo adicional degrada latencia de respuesta. | recomendacion: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | confianza 0.85
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente. | recomendacion: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | confianza 0.85
- 5 platforms need learning: Low confidence platforms: Groq Console, Google AI Studio, OpenRouter, GitHub, Ollama Local API. Consider learning sessions. | recomendacion: Run learn_platform() for low-confidence platforms | confianza 0.70

## Ajustes recomendados
- excessive_polling_threads: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | fuente runtime_performance_monitor
- 3 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- excessive_threads: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | fuente runtime_performance_monitor
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner
- 5 platforms need learning: Run learn_platform() for low-confidence platforms | fuente n/d

## Mejoras validadas
- Sin mejoras validadas fuertes todavia.

## Retroalimentacion de ajustes
- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, autonomy_score, UNRESOLVED:experiment_history, UNRESOLVED:adaptive_sessions