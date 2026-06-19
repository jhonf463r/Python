# FASE 1: CONTRATO DEL SISTEMA - RESUMEN ESTRUCTURADO

## ARQUITECTURA CENTRAL VIGENTE

### Cerebro y Decisión
- **PerceptionSnapshot**: entrada unificada antes de cada decisión
- **AdaptiveTaskOrchestrator**: orquestador principal
- **TaskContextAssembler**: ensambla contexto, perception y world model summary
- **AutonomyGovernancePolicy**: decide qué rutas son viables o deben bloquearse
- **IntentUnderstandingService**: clasifica la intención
- **LocalRoleRouter**: decide ruta y proveedor local

### Modelos del Entorno
- **EnvironmentSelfModel**: estado de hardware, runtime y riesgos del entorno
- **WorldModelSnapshot**: panorama operativo vivo del sistema, herramientas, red, ventanas y bloqueos
- **UniversalPerceptionSignal**: observación puntual de programa o página

### Cloud Reasoning y Auditoría de Decisiones
- **CloudReasoningPlannerService**: genera planes multi-paso usando modelos cloud (Gemini → Groq → Ollama)
- **DecisionAuditTrail**: registra cada decisión cloud (proveedor, latencia, confianza, resultado, tendencia) en `data/evolution/decision_audit/decisions.jsonl`
- **ApiKeyDiscoveryService**: descubre, prueba, compara y monitorea API keys de proveedores cloud

### Aprendizaje, Contexto y Revisión
- **ExperimentLab**: compara rutas, asistentes y configuraciones
- **StrategySelector**: recomienda rutas por historial y evidencia
- **AdaptiveWeightLayer**: ajusta preferencia futura con base en resultados reales
- **TaskOutcomeRecorder**: cierra el loop de aprendizaje desde la ejecución normal
- **PortableContextService**: exporta contexto comprimido y portable para nuevas sesiones
- **OperationalSelfExaminationService**: revisa patrones repetidos, degradaciones y ajustes recomendados

### Herramientas y Ejecución
- **ToolTeachService**: consultas a herramientas externas
- **ToolRegistry** y **ToolCard**: catálogo operativo de herramientas
- **AutonomousEvolutionService**: puente de consulta externa autónoma
- **UIExecutionRunner**: ejecución UI controlada

### Servicios de Memoria de Comportamiento
- **ToolMemory**: recuerda tareas, resultados y eventos de auditoría
- **InteractionLearningService**: aprende patrones de interacción desde ejecuciones
- **InteractionModeSelector**: selecciona modo de interacción basado en task kind y patrones reusables

### Percepción Universal
- **UniversalPerceptionService**: construye señales de percepción multimodal para páginas web y apps de escritorio
- **BrowserSessionController**: controlador Playwright para sesiones de navegador
- **BrowserActionService**: servicio de acciones de navegador

### World Model
- **WorldModelService**: mantiene panorama operativo de windows, tools, network y blockers
- Escaneo periódico (45s light, 180s full)
- Detección de procesos de navegador
- Monitoreo de latencia de red

### Metacognición
- **UniversalMetacognitiveScanner**: cerebro central metacognitivo
- **OperationalSelfExaminationService**: autoexaminación operacional
- **DecisionAuditTrail**: auditoría de decisiones cloud

## ESTRUCTURA DE ARCHIVOS CLAVE

### Bootstrap
- `main.py`: punto de entrada con crash guard
- `bootstrap.py`: inicialización y wiring de servicios
- `pyproject.toml`: dependencias (PySide6, pydantic, httpx, Pillow, playwright, keyring, psutil, pyperclip, pywin32)

### Servicios de Herramientas
- `services/tools/tool_adapters.py`: adaptadores de herramientas (ToolAdapter)
- `services/tools/tool_registry.py`: registro de herramientas (ToolRegistry)
- `services/tools/tool_memory.py`: memoria de herramientas (ToolMemory)
- `services/tools/interaction_learning_service.py`: aprendizaje de interacciones
- `services/tools/interaction_mode_selector.py`: selector de modo de interacción

### Servicios de Percepción
- `services/capture/universal_perception_service.py`: percepción universal
- `services/capture/browser_session_controller.py`: controlador de sesión de navegador
- `services/capture/browser_action_service.py`: servicio de acciones de navegador

### Servicios de Evolución
- `services/evolution/world_model_service.py`: modelo del mundo
- `services/evolution/decision_audit_trail.py`: auditoría de decisiones
- `services/evolution/universal_metacognitive_scanner.py`: scanner metacognitivo universal
- `services/evolution/operational_self_examination_service.py`: autoexaminación operacional

## CONTRATOS DE DATOS

### ToolCard
- tool_id, tool_type, title, description
- capabilities, adapter_key
- success_count, failure_count
- validation_status, available
- metadata (credential_domain, web_url, assistant_kind, etc.)

### ToolTask
- task_id, tool_id, objective, title
- actions, approval_decision
- execution_scope, site_id
- metadata (goal_parameters, goal_context, mode_selection, etc.)

### ToolResult
- result_id, task_id, tool_id
- success, validation_status
- execution_state, output
- metadata (interaction_pattern_id, interaction_channel, etc.)

### InteractionPattern
- signature, title, channel
- tool_id, tool_type, site_id
- operations (normalized steps)
- success_count, failure_count
- reusable, metadata

### WorldModelSnapshot
- windows, tools, network_status
- external_state_flags
- blockers, observations
- timestamp

## PATRONES DE INTERACCIÓN

### InteractionMode
- **EXTERNAL_ASSISTANT**: asistente externo (ChatGPT, Claude, etc.)
- **LOCAL_INFERENCE**: inferencia local (Ollama, etc.)
- **BROWSER_TEACH**: enseñanza de navegador
- **UI_AUTOMATION**: automatización de UI
- **FALLBACK**: fallback cuando no hay opción viable

### InteractionChannel
- **WEB**: navegador web
- **DESKTOP**: aplicación de escritorio
- **CLI**: línea de comandos
- **API**: API directa

## PATRONES DE FALLA DETECTADOS

### Stall Patterns
- 'just a moment', 'un momento', 'loading'
- 'browser_input_missing', 'browser_security_verification'

### WinError5 Patterns
- '[winerror 5]', 'access is denied', 'acceso denegado', 'permissionerror'

### Wrong Thread Patterns
- 'wrong_thread', 'thread_mismatch', 'invalid_thread'

## LIMITACIONES IDENTIFICADAS

### Entorno
- NO puedo operar UI como humano (no hay pyautogui ni control directo de QML)
- NO puedo capturar screenshots directamente (solo vía PowerShell indirecto)
- NO puedo controlar navegador directamente en tiempo real (Playwright solo si está configurado)

### Sistema
- Bootstrap lento (~16s vs ~2s anterior) por PersistenceCoordinator
- UIBridgeServer bloqueado (detectado en sesiones anteriores)
- ChatGPT web falla con browser_security_verification desde 2026-05-09

## PRÓXIMOS PASOS

### FASE 2: Entender Memoria de Comportamiento
- Construir modelo por herramienta
- Analizar ToolCard, ToolTask, ToolResult
- Entender InteractionPattern y InteractionLearningService
- Mapear modos de interacción y canales

### FASE 3: Percepción Universal
- Usar servicios de percepción
- Analizar UniversalPerceptionService
- Entender BrowserSessionController
- Mapear señales de percepción multimodal

### FASE 4: Reglas de Decisión
- Implementar lógica de reutilización
- Analizar InteractionModeSelector
- Entender WorldModelService
- Mapear reglas de decisión basadas en memoria

### FASE 5: Caso Especial ChatGPT Web Asistido
- Analizar bloqueo browser_security_verification
- Implementar estrategia de reutilización de ventana
- Usar chatgpt_installed como alternativa

### FASE 6: Ejecución Real
- Probar UI como humano (limitado por entorno)
- Usar PowerShell para automatización limitada
- Documentar limitaciones

### FASE 7: Evaluación de Coherencia
- Verificar órganos conectados
- Analizar wiring en bootstrap.py
- Verificar inyección de dependencias

### FASE 8: Evolución del Prompt
- Memoria de prompts
- PortableContextService
- OperationalSelfExaminationService

### FASE 9: Salida Obligatoria
- 9 resultados finales
- Reporte de auditoría completa
- Recomendaciones de evolución
