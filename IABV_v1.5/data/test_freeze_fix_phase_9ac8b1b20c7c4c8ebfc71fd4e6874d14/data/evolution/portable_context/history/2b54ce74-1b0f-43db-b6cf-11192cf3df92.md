# IABV v1.5 - Portable Context Package

Generado: 2026-05-09T03:02:03.042651+00:00
Resumen: Objetivo actual: sin objetivo activo confirmado | mejor ruta conocida: sin preferencia de ruta consolidada | bloqueos activos: 0 | pendientes: 0 | ajustes sugeridos: 6 | unresolved: 7

Usa este contexto como arranque rapido para una sesion nueva. Si algo aparece como UNRESOLVED, no lo des por confirmado.

## Estado actual del proyecto
Sin objetivo activo confirmado | World model: conectado | Validacion: bootstrapping
- Objetivo activo: sin objetivo activo confirmado
- Proyecto activo: sin proyecto activo confirmado
- Tarea activa: sin tarea activa confirmada
- Pulso evolutivo: Dossiers recientes: 0 | fallos: 0 | parciales: 0 | incidentes invisibles: 0 | sesiones adaptativas: 0 | autotests: 0 | pendientes Codex: 0. Prioridad sugerida: seguir reforzando evidencia y conocimiento local.
- World model: Observacion operativa actualizada.
- Validacion autonoma: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
Fuente: aggregated_live_state | refs: objective_repository, evolution_review_service, world_model_service, autonomous_validation_cycle | actualizado: 2026-05-09T03:02:02.606140+00:00

## Arquitectura central vigente
La arquitectura sigue siendo una sola: perception -> orchestrator -> governance -> ejecucion -> aprendizaje.
- PerceptionSnapshot: wired | Entrada unificada antes de decidir.
- TaskContextAssembler: wired | Arma contexto, memoria, aprendizaje y world model.
- AdaptiveTaskOrchestrator: wired | Decide ruta, governance y resultado final.
- EnvironmentSelfModel: wired | Describe hardware, runtime y riesgo operativo.
- WorldModelSnapshot: wired | Panorama operativo vivo de herramientas, red y ventanas.
- ExperimentLab: wired | Memoria persistida de resultados y recomendaciones.
Fuente: project_contract | refs: AGENTS.md, bootstrap wiring | actualizado: 2026-05-09T03:02:03.042651+00:00

## Intencion persistente del usuario
Direccion estable: todas las IAs deben alimentar la metacognicion de IABV para mejorar coherencia, memoria operativa y autonomia gobernada.
- centro_metacognitivo_local: IABV debe ser el centro local-first que observa laptop, nube, herramientas, sesiones y resultados sin crear otro cerebro.
- ias_como_organos_externos: Devin, Codex, ChatGPT, Claude y otros asistentes deben aportar evidencia, trazas y rendimiento al ExperimentLab.
- no_repetir_intencion: Las ideas recurrentes del usuario se condensan en contexto portable para que cada sesion arranque con la misma direccion.
- evolucion_gobernada: Toda incubacion cognitiva, algoritmo mutable o ajuste de prompts pasa por sandbox, consenso y validacion antes de promoverse.
- percepcion_segura_de_cuentas: El sistema puede detectar presencia/sesion y recomendar rutas, pero no extrae contrasenas, cookies ni tokens; pide permiso cuando corresponda.
Fuente: user_intent | refs: chat:metacognicion_extendida, AGENTS.md, portable_context | actualizado: 2026-05-09T03:02:03.042651+00:00

## Piezas ya implementadas
Capas cerradas: P1 y nucleo de P2. P3 ya deja paquete portable util para sesiones nuevas. Validacion actual: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
- P1 World Model operativo: active | Observa estado de herramientas, red, foco, procesos y bloqueos antes de actuar.
- P2 Neuroplasticidad operativa: partial | Aprende resultados reales y ajusta preferencia futura de rutas e IAs.
- Monitor de evolucion de herramientas: active | Resume desempeno por problema, detecta degradacion y genera propuestas para sandbox.
- SandboxExperiment: active | Valida candidatos antes de promoverlos como decision estable.
- P3 Contexto portable: active | Condensa arquitectura, aprendizaje, bloqueos y pendientes en JSON + Markdown reutilizable.
- Preguntas humanas de aprendizaje: active | Responde desde ExperimentLab y validacion sin disparar autonomia operativa.
Fuente: project_contract | refs: bootstrap wiring, world_model_service, experiment_lab_repository, autonomous_validation_cycle | actualizado: 2026-05-09T03:02:03.042651+00:00

## Aprendizaje acumulado util
Aun no hay aprendizaje consolidado.
Fuente: persistent_learning | refs: ExperimentLab, AdaptiveWeightLayer, TaskOutcomeRecorder | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:learning_summary

## Patrones de coordinacion IA-IA
No IA-IA coordination patterns detected yet.
Fuente: persistent_learning | refs: ExperimentLab, ia_trace_summary | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:coordination_patterns

## Descubrimiento de herramientas
Detecte 0 senal(es) de descubrimiento: 0 activa(s), 0 en evaluacion, 0 promovida(s), 0 descartada(s).
Fuente: tool_discovery | refs: ToolRegistry, WorldModelSnapshot, ExperimentLab, AutonomousValidationCycleService | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:tool_discovery_subjects

## Evolucion de herramientas
Todavia no hay suficiente evidencia comparativa para un monitor de evolucion de herramientas.
Fuente: experiment_lab_monitor | refs: ExperimentLab, AdaptiveWeightLayer, AutonomousValidationCycle | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:tool_evolution_subjects, UNRESOLVED:tool_evolution_performance

## Decisiones evolutivas
Sin decisiones evolutivas registradas todavia.
Fuente: autonomous_validation_cycle | refs: AutonomousValidationCycleService, SandboxExperimentService, ExperimentLab | actualizado: 2026-05-09T03:02:03.042651+00:00

## Autoexaminacion operativa
Autoexaminacion watch: 10 hallazgos activos. Lo mas fuerte ahora es 3 cloud providers not configured. Mejoras validadas: 0 | issues recurrentes: 5.
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up.
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows.
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente.
- 5 platforms need learning: Low confidence platforms: Groq Console, Google AI Studio, OpenRouter, GitHub, Ollama Local API. Consider learning sessions.
- 3 cloud providers not configured: Run auto_provision_missing_secrets()
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario.
Fuente: derived_review | refs: OperationalSelfExaminationService, ExperimentLab, WorldModelSnapshot | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:codex_thread_tracking, autonomy_score, UNRESOLVED:experiment_history, UNRESOLVED:adaptive_sessions

## Historial de auditorias de codigo
Sin auditorias registradas. Usar register_audit_finding via MCP para registrar hallazgos.
Fuente: code_audit | refs: CodeAuditTrail | actualizado: 2026-05-09T03:02:03.042651+00:00

## Estado de Cloud Reasoning
Sin decisiones registradas. Ejecutar "soluciona X" para iniciar el trail de auditoria.
- Recomendacion: Configurar al menos GROQ_API_KEY y ejecutar un plan de prueba
Fuente: decision_audit | refs: DecisionAuditTrail, ApiKeyDiscoveryService | actualizado: 2026-05-09T03:02:03.042651+00:00

## Salud del arranque (startup_timeline)
Sin data/logs/startup_timeline.jsonl. Lanzar la UI con IABV_STARTUP_TIMELINE=1 para registrar arranque.
Fuente: startup_timeline_jsonl | refs: data/logs/startup_timeline.jsonl, iabv_v15.infra.startup_timeline | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:startup_timeline_missing

## Ciclo de vida de interacciones recientes
Sin episodios de interaccion recientes.
Fuente: runtime_audit_jsonl+in_memory | refs: data/logs/runtime_audit.jsonl, ChatInteractionLifecycle | actualizado: 2026-05-09T03:02:03.042651+00:00

## Salud de cuentas, cuotas y workers
44 workers disponibles | 11594 mensajes restantes | tools: github, claude, codex, chatgpt | 5 secretos faltantes
- github: jhonf463r@gmail.com: 
- github: proveedorjf@gmail.com: 
- github: storeburve@gmail.com: 
- github: hectorgeoruiz@gmail.com: 
- github: harvytrujillo156@gmail.com: 
- github: bonikobk@gmail.com: 
Fuente: account_resource_scanner | refs: account_resource_scanner, quota_tracker.json | actualizado: 2026-05-09T03:02:03.042651+00:00

## Inventario de cuentas y cola de continuidad
44 cuentas activas | 11594 mensajes disponibles | siguiente recomendada: jhonf463r@gmail.com (github, score=1.00)
- github: jhonf463r@gmail.com: 
- github: proveedorjf@gmail.com: 
- github: storeburve@gmail.com: 
- github: hectorgeoruiz@gmail.com: 
- github: harvytrujillo156@gmail.com: 
- github: bonikobk@gmail.com: 
Fuente: account_resource_scanner | refs: account_resource_scanner, build_inventory_snapshot | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:quota_never_tracked — cuota real desconocida, UNRESOLVED:visible_account_state_requires_user_permission

## Coordinacion limit-aware de herramientas
Sin datos de coordinacion de herramientas.
Fuente: adaptive_task_orchestrator | refs: tool_selection_summary, worker_gate | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:no_recent_tool_selections

## Perfil de arranque (boot telemetry)
Boot profile (msi-f11f77ddd2e2): sin datos de arranque todavia.
Fuente: boot_profile_store | refs: data/evolution/boot_profiles/, iabv_v15.services.evolution.boot_profile_store | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:boot_profile_no_data

## Base evidencial del contexto
Evidencia observada en vivo (world_model, environment_self_model). Fuentes persistidas: ninguna.
- state: observed
- live_sources: world_model, environment_self_model
- unresolved_fields: UNRESOLVED:codex_thread_tracking, UNRESOLVED:ollama_inventory
Fuente: task_context_assembler | refs: iabv_v15.services.adaptive.task_context_assembler, WorldModelSnapshot, EnvironmentSelfModel | actualizado: 2026-05-09T03:02:03.042651+00:00

## Task-packet pattern summary
Task-packet: sin datos de runs recientes.
Fuente: experiment_lab_repository | refs: ExperimentLab, TaskOutcomeRecorder | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:task_packet_no_data

## Herramientas y rutas recomendadas
No hay rutas recomendadas con evidencia suficiente.
Fuente: persistent_learning | refs: ExperimentLab, StrategySelector, comparison_scope_key | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:recommended_routes

## Bloqueos, limites y rutas inviables
2 bloqueos o limitaciones activas.
- tool_status: La herramienta no quedo confirmada como disponible en esta laptop.
- tool_status: La herramienta no quedo confirmada como disponible en esta laptop.
Fuente: live_operational_state | refs: WorldModelSnapshot | actualizado: 2026-05-09T03:02:02.606140+00:00

## Decisiones ya validadas
1 decisiones ya tienen validacion o confianza suficiente para reutilizarse.
- validation_cycle: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
Fuente: persistent_learning | refs: ExperimentLab, AutonomousValidationCycle | actualizado: 2026-05-09T03:02:03.042651+00:00

## Historial condensado de decisiones
No hay historial condensado de decisiones relevantes.
Fuente: persistent_learning | refs: ExperimentLab, ia_trace_summary | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:decision_history

## Pendientes priorizados
0 pending issues y 1 mejoras priorizadas.
- Seguir capturando evidencia evolutiva: Ejecutar consultas, ensenanzas y autodiagnosticos para poblar la capa evolutiva.
Fuente: persistent_backlog | refs: pending_issue_repository, evolution_review_service, platform_pending_queue | actualizado: 2026-05-09T03:02:03.042651+00:00

## Cola canónica de trabajo
Cola canónica vacía o sin fuentes conectadas.
Fuente: control_master | refs: ControlMasterService, ObjectiveRepository, PlatformPendingQueue, PendingIssueRepository, OSES, runtime_audit | actualizado: 2026-05-09T03:02:03.042651+00:00

## UNRESOLVED
7 campos siguen sin evidencia suficiente y no deben asumirse.
- UNRESOLVED:ollama_inventory: 
- UNRESOLVED:codex_thread_tracking: 
- UNRESOLVED:recommendation_history: 
- UNRESOLVED:active_goal_context: 
- autonomy_score: 
- UNRESOLVED:experiment_history: 
Fuente: honest_runtime_limits | refs: WorldModelSnapshot, EnvironmentSelfModel, AutonomousValidationCycle | actualizado: 2026-05-09T03:02:03.042651+00:00
UNRESOLVED: UNRESOLVED:ollama_inventory, UNRESOLVED:codex_thread_tracking, UNRESOLVED:recommendation_history, UNRESOLVED:active_goal_context, autonomy_score, UNRESOLVED:experiment_history, UNRESOLVED:adaptive_sessions

## Reglas duras que no deben romperse
Este paquete portable no reemplaza la arquitectura: solo la condensa y la hace reutilizable.
- No crear otro cerebro ni otro orquestador.
- No duplicar PerceptionSnapshot ni crear una memoria paralela.
- No romper governance ni saltarse bloqueos del world model.
- Cambios minimos, reversibles y verificables.
- Si algo no puede confirmarse con evidencia, marcar UNRESOLVED.
- Los ViewModels observan y explican; no inventan decisiones de ruta.
Fuente: project_contract | refs: AGENTS.md | actualizado: 2026-05-09T03:02:03.042651+00:00

## Identidad persistente del usuario
Preferencias, hábitos y perfil del entorno que persisten entre sesiones.
- status: No identity profile persisted yet
Fuente: user_identity | refs: portable_context/user_identity.json | actualizado: 2026-05-09T03:02:03.042651+00:00

## Objetivos a largo plazo
Metas persistentes del usuario que sobreviven entre sesiones.
- No long-term goals defined: 
Fuente: user_goals | refs: portable_context/long_term_goals.json | actualizado: 2026-05-09T03:02:03.042651+00:00