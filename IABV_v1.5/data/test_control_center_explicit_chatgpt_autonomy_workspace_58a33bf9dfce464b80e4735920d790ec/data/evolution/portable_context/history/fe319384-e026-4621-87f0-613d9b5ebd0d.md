# IABV v1.5 - Portable Context Package

Generado: 2026-05-27T15:56:39.148538+00:00
Resumen: Objetivo actual: sin objetivo activo confirmado | mejor ruta conocida: sin preferencia de ruta consolidada | bloqueos activos: 0 | pendientes: 0 | ajustes sugeridos: 6 | unresolved: 5

Usa este contexto como arranque rapido para una sesion nueva. Si algo aparece como UNRESOLVED, no lo des por confirmado.

## Estado actual del proyecto
Sin objetivo activo confirmado | World model: conectado | Validacion: bootstrapping
- Objetivo activo: sin objetivo activo confirmado
- Proyecto activo: sin proyecto activo confirmado
- Tarea activa: sin tarea activa confirmada
- Pulso evolutivo: Dossiers recientes: 0 | fallos: 0 | parciales: 0 | incidentes invisibles: 0 | sesiones adaptativas: 0 | autotests: 0 | pendientes Codex: 0. Prioridad sugerida: seguir reforzando evidencia y conocimiento local.
- World model: Observacion operativa actualizada.
- Validacion autonoma: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
Fuente: aggregated_live_state | refs: objective_repository, evolution_review_service, world_model_service, autonomous_validation_cycle | actualizado: 2026-05-27T15:56:38.985102+00:00

## Arquitectura central vigente
La arquitectura sigue siendo una sola: perception -> orchestrator -> governance -> ejecucion -> aprendizaje.
- PerceptionSnapshot: wired | Entrada unificada antes de decidir.
- TaskContextAssembler: wired | Arma contexto, memoria, aprendizaje y world model.
- AdaptiveTaskOrchestrator: wired | Decide ruta, governance y resultado final.
- EnvironmentSelfModel: wired | Describe hardware, runtime y riesgo operativo.
- WorldModelSnapshot: wired | Panorama operativo vivo de herramientas, red y ventanas.
- ExperimentLab: wired | Memoria persistida de resultados y recomendaciones.
Fuente: project_contract | refs: AGENTS.md, bootstrap wiring | actualizado: 2026-05-27T15:56:39.148538+00:00

## Intencion persistente del usuario
Direccion estable: todas las IAs deben alimentar la metacognicion de IABV para mejorar coherencia, memoria operativa y autonomia gobernada.
- centro_metacognitivo_local: IABV debe ser el centro local-first que observa laptop, nube, herramientas, sesiones y resultados sin crear otro cerebro.
- ias_como_organos_externos: Devin, Codex, ChatGPT, Claude y otros asistentes deben aportar evidencia, trazas y rendimiento al ExperimentLab.
- no_repetir_intencion: Las ideas recurrentes del usuario se condensan en contexto portable para que cada sesion arranque con la misma direccion.
- evolucion_gobernada: Toda incubacion cognitiva, algoritmo mutable o ajuste de prompts pasa por sandbox, consenso y validacion antes de promoverse.
- percepcion_segura_de_cuentas: El sistema puede detectar presencia/sesion y recomendar rutas, pero no extrae contrasenas, cookies ni tokens; pide permiso cuando corresponda.
Fuente: user_intent | refs: chat:metacognicion_extendida, AGENTS.md, portable_context | actualizado: 2026-05-27T15:56:39.148538+00:00

## Piezas ya implementadas
Capas cerradas: P1 y nucleo de P2. P3 ya deja paquete portable util para sesiones nuevas. Validacion actual: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
- P1 World Model operativo: active | Observa estado de herramientas, red, foco, procesos y bloqueos antes de actuar.
- P2 Neuroplasticidad operativa: partial | Aprende resultados reales y ajusta preferencia futura de rutas e IAs.
- Monitor de evolucion de herramientas: active | Resume desempeno por problema, detecta degradacion y genera propuestas para sandbox.
- SandboxExperiment: active | Valida candidatos antes de promoverlos como decision estable.
- P3 Contexto portable: active | Condensa arquitectura, aprendizaje, bloqueos y pendientes en JSON + Markdown reutilizable.
- Preguntas humanas de aprendizaje: active | Responde desde ExperimentLab y validacion sin disparar autonomia operativa.
Fuente: project_contract | refs: bootstrap wiring, world_model_service, experiment_lab_repository, autonomous_validation_cycle | actualizado: 2026-05-27T15:56:39.148538+00:00

## Aprendizaje acumulado util
Aun no hay aprendizaje consolidado.
Fuente: persistent_learning | refs: ExperimentLab, AdaptiveWeightLayer, TaskOutcomeRecorder | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:learning_summary

## Aprendizaje del presupuesto operativo
2 decisiones de presupuesto operativo registradas en ExperimentLab. Calibracion: insufficient_sample.
- metacognition:defer: reason=rest_window_not_reached | source=oses_auto_correction | score=0.79
- deep_scan:defer: reason=rest_window_not_reached | source=oses_deep_cognition | score=0.79
- calibration:insufficient_sample: samples=2/10 | recommendation=collect_more_evidence_before_tuning
Fuente: persistent_learning | refs: AutonomyGovernancePolicy, ExperimentLab, OSES | actualizado: 2026-05-27T15:56:39.148538+00:00

## Patrones de coordinacion IA-IA
No IA-IA coordination patterns detected yet.
Fuente: persistent_learning | refs: ExperimentLab, ia_trace_summary | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:coordination_patterns

## Descubrimiento de herramientas
Detecte 0 senal(es) de descubrimiento: 0 activa(s), 0 en evaluacion, 0 promovida(s), 0 descartada(s).
Fuente: tool_discovery | refs: ToolRegistry, WorldModelSnapshot, ExperimentLab, AutonomousValidationCycleService | actualizado: 2026-05-27T15:56:39.148538+00:00

## Evolucion de herramientas
Superviso 2 contexto(s) con 0 propuesta(s) activa(s), 0 ya decidida(s) y 0 contexto(s) degradado(s). Mejor panorama actual: operational_budget:metacognition favorece iabv_self con score 1.05 Validacion autonoma: bootstrapping. Ciclo de validacion autonoma iniciando; a la espera del primer tick.
- operational_budget:metacognition | iabv_self: route=background | score=1.05 | exito=100% | bloqueos=0%
- operational_budget:deep_scan | iabv_self: route=background | score=1.05 | exito=100% | bloqueos=0%
Fuente: experiment_lab_monitor | refs: ExperimentLab, AdaptiveWeightLayer, AutonomousValidationCycle | actualizado: 2026-05-27T15:56:39.148538+00:00

## Decisiones evolutivas
Sin decisiones evolutivas registradas todavia.
Fuente: autonomous_validation_cycle | refs: AutonomousValidationCycleService, SandboxExperimentService, ExperimentLab | actualizado: 2026-05-27T15:56:39.148538+00:00

## Autoexaminacion operativa
Autoexaminacion watch: 9 hallazgos activos. Lo mas fuerte ahora es 3 cloud providers not configured. Mejoras validadas: 1 | issues recurrentes: 5.
- 3 cloud providers not configured: Missing API keys: Google Gemini (AI Studio), OpenRouter, Together AI. Auto-provisioning can set these up.
- 1 capacidades Windows nativas faltantes: El sistema detecta 1 capacidades de la plataforma Windows que no estan disponibles o tienen dependencias faltantes: Notificaciones Windows.
- Gemini Web necesita re-login: La sesion web de Gemini Web esta expirada o no existe. Razon: No active browser session found for this provider. El proveedor web no sera seleccionado hasta que el usuario re-autentique manualmente.
- 5 platforms need learning: Low confidence platforms: Groq Console, Google AI Studio, OpenRouter, GitHub, Ollama Local API. Consider learning sessions.
- 3 cloud providers not configured: Run auto_provision_missing_secrets()
- 1 capacidades Windows nativas faltantes: Revisar la cola de pendientes de plataforma en data/evolution/platform_pending/. Cada capacidad faltante tiene next_action y dependency_missing documentados para continuacion por agente o usuario.
Fuente: derived_review | refs: OperationalSelfExaminationService, ExperimentLab, WorldModelSnapshot | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: autonomy_score, UNRESOLVED:adaptive_sessions

## Historial de auditorias de codigo
Sin auditorias registradas. Usar register_audit_finding via MCP para registrar hallazgos.
Fuente: code_audit | refs: CodeAuditTrail | actualizado: 2026-05-27T15:56:39.148538+00:00

## Estado de Cloud Reasoning
Sin decisiones registradas. Ejecutar "soluciona X" para iniciar el trail de auditoria.
- Recomendacion: Configurar al menos GROQ_API_KEY y ejecutar un plan de prueba
Fuente: decision_audit | refs: DecisionAuditTrail, ApiKeyDiscoveryService | actualizado: 2026-05-27T15:56:39.148538+00:00

## Salud del arranque (startup_timeline)
Sin data/logs/startup_timeline.jsonl. Lanzar la UI con IABV_STARTUP_TIMELINE=1 para registrar arranque.
Fuente: startup_timeline_jsonl | refs: data/logs/startup_timeline.jsonl, iabv_v15.infra.startup_timeline | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:startup_timeline_missing

## Estabilidad del nacimiento consciente
Sin evidencia suficiente de nacimiento/congelamiento para analizar.
- stable_resource_freezes: 
- startup_duplicates: 
- deferred_metacognition: 
Fuente: startup_and_freeze_artifacts | refs: data/logs/startup_audit.jsonl, data/logs/startup_timeline.jsonl, data/evolution/incident_reports/freeze_*.json | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:freeze_reports_missing

## Ciclo de vida de interacciones recientes
Sin episodios de interaccion recientes.
Fuente: runtime_audit_jsonl+in_memory | refs: data/logs/runtime_audit.jsonl, ChatInteractionLifecycle | actualizado: 2026-05-27T15:56:39.148538+00:00

## Salud de cuentas, cuotas y workers
8 workers disponibles | 2107 mensajes restantes | tools: github, claude, codex, chatgpt | 5 secretos faltantes
- github: faber_1520@hotmail.com: 
- github: (sesion activa en Opera): 
- claude: faber_1520@hotmail.com: 
- codex: faber_1520@hotmail.com: 
- claude: (sesion activa en Opera): 
- codex: (sesion activa en Opera): 
Fuente: account_resource_scanner | refs: account_resource_scanner, quota_tracker.json | actualizado: 2026-05-27T15:56:39.148538+00:00

## Inventario de cuentas y cola de continuidad
8 cuentas activas | 2107 mensajes disponibles | siguiente recomendada: faber_1520@hotmail.com (github, score=1.00)
- github: faber_1520@hotmail.com: 
- github: (sesion activa en Opera): 
- claude: faber_1520@hotmail.com: 
- codex: faber_1520@hotmail.com: 
- claude: (sesion activa en Opera): 
- codex: (sesion activa en Opera): 
Fuente: account_resource_scanner | refs: account_resource_scanner, build_inventory_snapshot | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:quota_never_tracked — cuota real desconocida, UNRESOLVED:visible_account_state_requires_user_permission

## Coordinacion limit-aware de herramientas
6 senales de coordinacion; readiness=ready.
- familia:chatgpt: readiness=ready tool=chatgpt_web_assisted lane=background_dom
- familia:claude: readiness=governed_attempt_ready tool=claude_web_assisted lane=background_dom
- familia:codex: readiness=governed_attempt_ready tool=codex_installed lane=background_tool
- familia:devin: readiness=governed_attempt_ready tool=devin_api lane=background_tool
- familia:ollama: readiness=governed_attempt_ready tool=ollama_llm lane=background_tool
- familia:playwright: readiness=manual_handoff tool=playwright_browser lane=manual
Fuente: adaptive_task_orchestrator | refs: tool_selection_summary, worker_gate, ToolDiscoveryService.external_coordination_readiness | actualizado: 2026-05-27T15:56:39.148538+00:00

## Perfil de arranque (boot telemetry)
Boot profile (msi-f11f77ddd2e2): sin datos de arranque todavia.
Fuente: boot_profile_store | refs: data/evolution/boot_profiles/, iabv_v15.services.evolution.boot_profile_store | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:boot_profile_no_data

## Base evidencial del contexto
Evidencia observada en vivo (world_model, environment_self_model). Fuentes persistidas: ninguna.
- state: observed
- live_sources: world_model, environment_self_model
- unresolved_fields: UNRESOLVED:ollama_inventory
Fuente: task_context_assembler | refs: iabv_v15.services.adaptive.task_context_assembler, WorldModelSnapshot, EnvironmentSelfModel | actualizado: 2026-05-27T15:56:39.148538+00:00

## Task-packet pattern summary
Task-packet: solo 0 runs, insuficiente para resumir patrones.
Fuente: experiment_lab_repository | refs: ExperimentLab, TaskOutcomeRecorder | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:task_packet_insufficient_data

## Binding visual y conceptos universales
Sin eventos recientes de binding visual.
Fuente: runtime_audit_jsonl | refs: data/logs/runtime_audit.jsonl, UniversalPerceptionService, WorldModelService | actualizado: 2026-05-27T15:56:39.148538+00:00

## Razonamiento formal, referencia y grounding
Probe formal-semantico sin gaps recientes de referencia, verdad y grounding.
- score: 1.0
- external_blocks: 
- deictic_followups: 
- local_misroutes: 
- visual_binding_failures: 
- symbolic_logic_winner: baseline_keyword_reference
Fuente: runtime_audit_and_decision_audit | refs: data/logs/runtime_audit.jsonl, DecisionAuditTrail, ExperimentLab | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:chat_routing_decisions_missing

## Activacion conceptual comun
Sin eventos recientes con evidencia de pesos conceptuales.
Fuente: runtime_audit_jsonl | refs: data/logs/runtime_audit.jsonl, concept_weight_evidence, UniversalPerceptionService | actualizado: 2026-05-27T15:56:39.148538+00:00

## Cierre de aprendizaje desde runtime
Sin eventos recientes para cerrar aprendizaje desde runtime.
Fuente: runtime_audit_jsonl | refs: data/logs/runtime_audit.jsonl, OperationalSelfExaminationService, ExperimentLab, AdaptiveWeightLayer | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:runtime_learning_events

## Nucleo Genesis metacognitivo
Nucleo Genesis bloqueado por fase birth (score=0.19).
- n/d: No hay evidencia suficiente del nacimiento del proceso.
- n/d: No hay suficiente evidencia de estabilidad post-arranque.
- n/d: Fuentes vivas disponibles: world_model, environment_self_model.
- n/d: No hay eventos recientes de binding visual/metavision para probar referencias como "esa ventana".
- n/d: No hay interacciones recientes reconstruibles.
- n/d: 1 mejora(s) validadas con evidencia.
Fuente: aggregated_runtime_contract | refs: data/logs/startup_timeline.jsonl, data/logs/runtime_audit.jsonl, data/evolution/incident_reports/freeze_*.json, WorldModelSnapshot, EnvironmentSelfModel, OperationalSelfExaminationService, AutonomousValidationCycleService | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:startup_timeline_missing, UNRESOLVED:freeze_reports_missing, UNRESOLVED:ollama_inventory, UNRESOLVED:visual_grounding, UNRESOLVED:interaction_lifecycle, UNRESOLVED:autonomous_validation_cycle, UNRESOLVED:portable_device_test_matrix

## Herramientas y rutas recomendadas
No hay rutas recomendadas con evidencia suficiente.
Fuente: persistent_learning | refs: ExperimentLab, StrategySelector, comparison_scope_key | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:recommended_routes

## Bloqueos, limites y rutas inviables
No veo bloqueos operativos fuertes persistidos en este momento.
Fuente: live_operational_state | refs: WorldModelSnapshot | actualizado: 2026-05-27T15:56:38.985102+00:00

## Decisiones ya validadas
1 decisiones ya tienen validacion o confianza suficiente para reutilizarse.
- validation_cycle: Ciclo de validacion autonoma iniciando; a la espera del primer tick.
Fuente: persistent_learning | refs: ExperimentLab, AutonomousValidationCycle | actualizado: 2026-05-27T15:56:39.148538+00:00

## Historial condensado de decisiones
No hay historial condensado de decisiones relevantes.
Fuente: persistent_learning | refs: ExperimentLab, ia_trace_summary | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:decision_history

## Progreso por organo/modulo
Progreso global 20.0%: 4 completadas, 16 abiertas.
- investigation: 0.0% listo | faltante 100.0% | complejidad 17.0 | criticos abiertos 0
- capability_discovery: 0.0% listo | faltante 100.0% | complejidad 8.0 | criticos abiertos 0
- windows_native: 44.4% listo | faltante 55.6% | complejidad 7.0 | criticos abiertos 0
- top_open_tasks: Primeras tareas abiertas por criticidad y complejidad.
Fuente: platform_pending_progress | refs: data/evolution/platform_pending/*.json | actualizado: 2026-05-27T15:56:39.148538+00:00

## Pendientes priorizados
0 pending issues y 1 mejoras priorizadas. 6 tareas de plataforma pendientes.
- Seguir capturando evidencia evolutiva: Ejecutar consultas, ensenanzas y autodiagnosticos para poblar la capa evolutiva.
- Fase A2: Auto-tests periodicos con presupuesto operativo: 
- Fase A3: Evaluar presupuesto operativo con ExperimentLab: 
- Fase A4: Calibrar umbrales del presupuesto operativo por evidencia: 
- Fase A: Regulación inteligente anti-freeze: 
Fuente: persistent_backlog | refs: pending_issue_repository, evolution_review_service, platform_pending_queue | actualizado: 2026-05-27T15:56:39.148538+00:00

## Cola canónica de trabajo
5 items prioritarios en cola canónica de trabajo.
- [medium|45] platform:inv_phase_a2_budgeted_idle_self_tests: Fase A2: Auto-tests periodicos con presupuesto operativo (src=platform_pending_queue) → Conectar AutonomousValidationCycleService y OSES al nuevo ev
- [medium|45] platform:inv_phase_a3_budget_experiment_feedback: Fase A3: Evaluar presupuesto operativo con ExperimentLab (src=platform_pending_queue) → Registrar outcomes de evaluate_operational_budget en Experim
- [medium|45] platform:inv_phase_a4_budget_threshold_calibration: Fase A4: Calibrar umbrales del presupuesto operativo por evidencia (src=platform_pending_queue) → Agregar resumen de calibracion a OSES/PortableContext y emit
- [medium|45] platform:inv_phase_a_antifreeze: Fase A: Regulación inteligente anti-freeze (src=platform_pending_queue) → Aplicar evaluate_operational_budget() a cada trabajo auxilia
- [medium|45] platform:cap_platform.notifications: Capacidad faltante: Notificaciones Windows (src=platform_pending_queue) → Verificar e instalar dependencia para platform.notifications
Fuente: control_master | refs: ControlMasterService, ObjectiveRepository, PlatformPendingQueue, PendingIssueRepository, OSES, runtime_audit | actualizado: 2026-05-27T15:56:39.148538+00:00

## UNRESOLVED
5 campos siguen sin evidencia suficiente y no deben asumirse.
- UNRESOLVED:ollama_inventory: 
- UNRESOLVED:recommendation_history: 
- UNRESOLVED:active_goal_context: 
- autonomy_score: 
- UNRESOLVED:adaptive_sessions: 
Fuente: honest_runtime_limits | refs: WorldModelSnapshot, EnvironmentSelfModel, AutonomousValidationCycle | actualizado: 2026-05-27T15:56:39.148538+00:00
UNRESOLVED: UNRESOLVED:ollama_inventory, UNRESOLVED:recommendation_history, UNRESOLVED:active_goal_context, autonomy_score, UNRESOLVED:adaptive_sessions

## Reglas duras que no deben romperse
Este paquete portable no reemplaza la arquitectura: solo la condensa y la hace reutilizable.
- No crear otro cerebro ni otro orquestador.
- No duplicar PerceptionSnapshot ni crear una memoria paralela.
- No romper governance ni saltarse bloqueos del world model.
- Cambios minimos, reversibles y verificables.
- Si algo no puede confirmarse con evidencia, marcar UNRESOLVED.
- Los ViewModels observan y explican; no inventan decisiones de ruta.
Fuente: project_contract | refs: AGENTS.md | actualizado: 2026-05-27T15:56:39.148538+00:00

## Identidad persistente del usuario
Preferencias, hábitos y perfil del entorno que persisten entre sesiones.
- status: No identity profile persisted yet
Fuente: user_identity | refs: portable_context/user_identity.json | actualizado: 2026-05-27T15:56:39.148538+00:00

## Objetivos a largo plazo
Metas persistentes del usuario que sobreviven entre sesiones.
- No long-term goals defined: 
Fuente: user_goals | refs: portable_context/long_term_goals.json | actualizado: 2026-05-27T15:56:39.148538+00:00