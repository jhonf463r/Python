# IABV v1.5 - Operational Self Examination

Generado: 2026-09-08T18:45:26.594284+00:00
Resumen: Autoexaminacion watch: 12 hallazgos activos. Lo mas fuerte ahora es 4 cloud providers not configured. Mejoras validadas: 0 | issues recurrentes: 5.

Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.

## Hallazgos
- 4 cloud providers not configured: Missing API keys: OpenAI (ChatGPT), Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up. | recomendacion: Run auto_provision_missing_secrets() | confianza 0.90
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows. | recomendacion: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | confianza 0.90
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente. | recomendacion: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | confianza 0.85
- 5 platforms need learning: Low confidence platforms: Groq Console, Google AI Studio, OpenRouter, GitHub, Ollama Local API. Consider learning sessions. | recomendacion: Run learn_platform() for low-confidence platforms | confianza 0.70
- iabv_window_missing: No se detecta ninguna ventana IABV entre las 11 ventanas activas. La UI puede no haberse iniciado, el titulo no coincide con los marcadores conocidos, o el scan corrio antes de que la ventana fuera visible. Nota: este hallazgo puede ser un falso positivo de timing — el MCP arranca antes de la UI y el primer scan de ventanas no la detecta. Deberia resolverse en el siguiente sync_pulse. | recomendacion: Verificar que el proceso UI (python -m iabv_v15 app) esta corriendo y que la ventana es visible para Win32 (MainWindowHandle != 0). Si el MCP acaba de arrancar, esperar al siguiente sync_pulse para re-evaluar. | confianza 0.50
- Loop introspectivo abierto: 4 mecanismo(s) inactivo(s):  | recomendacion: sin ajuste concreto | confianza 0.00

## Ajustes recomendados
- 4 cloud providers not configured: Run auto_provision_missing_secrets() | fuente n/d
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario. | fuente iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities, data/evolution/platform_pending/
- Gemini Web necesita re-login: Abrir https://gemini.google.com/ en el navegador, hacer login manualmente (captcha/2FA si aplica), y IABV detectara la nueva sesion automaticamente. | fuente check_web_session_health, AccountResourceScanner
- 5 platforms need learning: Run learn_platform() for low-confidence platforms | fuente n/d
- iabv_window_missing: Verificar que el proceso UI (python -m iabv_v15 app) esta corriendo y que la ventana es visible para Win32 (MainWindowHandle != 0). Si el MCP acaba de arrancar, esperar al siguiente sync_pulse para re-evaluar. | fuente WorldModelSnapshot.active_windows
- UniversalAutonomyIndex: datos insuficientes: Ejecutar mas tareas para acumular datos de rendimiento. Las metricas se calcularan automaticamente cuando haya suficiente evidencia. | fuente OperationalSelfExaminationService._universal_autonomy_index_findings

## Mejoras validadas
- Sin mejoras validadas fuertes todavia.

## Retroalimentacion de ajustes
- 4 cloud providers not configured: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- 1 capacidades Windows nativas faltantes: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- Gemini Web necesita re-login: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.
- 5 platforms need learning: no_evidence | Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no. | siguiente paso: Mantenerla en observacion hasta tener mas corridas comparables.

UNRESOLVED: UNRESOLVED:codex_thread_tracking, autonomy_score, UNRESOLVED:experiment_history, UNRESOLVED:adaptive_sessions