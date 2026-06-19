# IABV v1.5 - Operational Self Examination

Generado: 2026-05-23T03:46:15.101174+00:00
Resumen: Autoexaminacion watch: 11 hallazgos activos. Lo mas fuerte ahora es excessive_polling_threads. Mejoras validadas: 1 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- excessive_polling_threads: 80 hilos de polling activos: ['ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server', 'ui-bridge-server']. Cada uno ejecuta scans periodicos que compiten por CPU y GIL. | recomendacion: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | confianza 0.90
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- UniversalAutonomyIndex: PARCIAL (autonomia=69%): AutonomyScore=69% (objetivo >80%), ResilienceScore=2% (objetivo >75%), CalibrationError=0.17 (objetivo <0.10), BlindSpotRatio=10% (objetivo <30%). Componente mas debil: capability_coverage (0%). | recomendacion: Mejorar tasa de exito de tareas. Revisar rutas que fallan frecuentemente en ExperimentLab y rotar a proveedores mas confiables. | confianza 0.88
- excessive_threads: 261 hilos activos en el proceso. Python GIL causa contention entre hilos — cada hilo adicional degrada latencia de respuesta. | recomendacion: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | confianza 0.85
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente. | recomendacion: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | confianza 0.85

## Ajustes recomendados
- excessive_polling_threads: Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL de 18s a 45s para uso normal. Usar scan_interval_seconds=120 cuando la presion de recursos es alta. | fuente runtime_performance_monitor
- 3 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- UniversalAutonomyIndex: PARCIAL (autonomia=69%): Mejorar tasa de exito de tareas. Revisar rutas que fallan frecuentemente en ExperimentLab y rotar a proveedores mas confiables. | fuente ExperimentLab, TaskOutcomeRecorder, DecisionAuditTrail, WorldModelSnapshot
- excessive_threads: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | fuente runtime_performance_monitor
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner

## Mejoras validadas
- iabv_self por background: Hay una mejora fuerte en experimentos recientes, pero todavia no un recommendation consolidado. | confianza 0.58

## Retroalimentacion de ajustes
- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, UNRESOLVED:adaptive_sessions