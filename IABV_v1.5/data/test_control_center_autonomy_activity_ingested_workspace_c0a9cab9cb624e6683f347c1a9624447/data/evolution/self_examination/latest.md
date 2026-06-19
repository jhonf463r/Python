# IABV v1.5 - Operational Self Examination

Generado: 2026-05-08T17:46:35.306886+00:00
Resumen: Autoexaminacion watch: 12 hallazgos activos. Lo mas fuerte ahora es excessive_polling_threads. Mejoras validadas: 0 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- excessive_polling_threads: 40 hilos de polling activos: ['ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server']. Cada uno ejecuta scans periodicos que compiten por CPU y GIL. | recomendacion: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | confianza 0.90
- RAM bajo presion: 2.5GB libre: 2.5GB de RAM disponible. Solo modelos pequenos caben. | recomendacion: Considerar liberar RAM si se necesita un modelo mas grande | confianza 0.90
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- excessive_threads: 173 hilos activos en el proceso. Python GIL causa contention entre hilos — cada hilo adicional degrada latencia de respuesta. | recomendacion: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | confianza 0.85
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente. | recomendacion: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | confianza 0.85

## Ajustes recomendados
- excessive_polling_threads: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | fuente runtime_performance_monitor
- RAM bajo presion: 2.5GB libre: Considerar liberar RAM si se necesita un modelo mas grande | fuente n/d
- 3 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- excessive_threads: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | fuente runtime_performance_monitor
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner

## Mejoras validadas
- Sin mejoras validadas fuertes todavia.

## Retroalimentacion de ajustes
- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, UNRESOLVED:focused_window, autonomy_score, UNRESOLVED:experiment_history, UNRESOLVED:adaptive_sessions