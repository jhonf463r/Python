# IABV v1.5 - Operational Self Examination

Generado: 2026-09-08T18:58:38.799005+00:00
Resumen: Autoexaminacion needs_attention: 15 hallazgos activos. Lo mas fuerte ahora es iabv_window_missing. Mejoras validadas: 1 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- iabv_window_missing: No se detecta ninguna ventana IABV entre las 11 ventanas activas. La UI puede no haberse iniciado, el titulo no coincide con los marcadores conocidos, o el scan corrio antes de que la ventana fuera visible. | recomendacion: Verificar que el proceso UI (python -m iabv_v15 app) esta corriendo y que la ventana es visible para Win32 (MainWindowHandle != 0). Si el MCP acaba de arrancar, esperar al siguiente sync_pulse para re-evaluar. | confianza 0.80
- 11 consultas externas diferidas por presion de recursos: Se han diferido 11 consultas externas por presion de recursos en esta sesion. Esto indica que el entorno necesita liberacion de recursos o que las consultas deben programarse en momentos de menor carga. | recomendacion: sin ajuste concreto | confianza 0.00
- RAM bajo presion: 2.1GB libre: 2.1GB de RAM disponible. Solo modelos pequenos caben. | recomendacion: Considerar liberar RAM si se necesita un modelo mas grande | confianza 0.90
- 4 cloud providers not configured: Missing API keys: OpenAI (ChatGPT), Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- excessive_threads: 138 hilos activos en el proceso. Python GIL causa contention entre hilos — cada hilo adicional degrada latencia de respuesta. | recomendacion: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | confianza 0.85

## Ajustes recomendados
- iabv_window_missing: Verificar que el proceso UI (python -m iabv_v15 app) esta corriendo y que la ventana es visible para Win32 (MainWindowHandle != 0). Si el MCP acaba de arrancar, esperar al siguiente sync_pulse para re-evaluar. | fuente WorldModelSnapshot.active_windows
- RAM bajo presion: 2.1GB libre: Considerar liberar RAM si se necesita un modelo mas grande | fuente n/d
- 4 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- excessive_threads: Consolidar hilos de polling: WorldModelService, EnvironmentSelfAwareness y HealthRouter podrian compartir un unico hilo con diferentes intervalos. Usar asyncio en vez de threads donde sea posible. | fuente runtime_performance_monitor
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner

## Mejoras validadas
- chatgpt web asistido por ui: Hay una mejora fuerte en experimentos recientes, pero todavia no un recommendation consolidado. | confianza 0.58

## Retroalimentacion de ajustes
- iabv_window_missing: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- RAM bajo presion: 2.0GB libre: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- 4 cloud providers not configured: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- 1 capacidades Windows nativas faltantes: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, UNRESOLVED:gpu_process_usage, autonomy_score, UNRESOLVED:adaptive_sessions