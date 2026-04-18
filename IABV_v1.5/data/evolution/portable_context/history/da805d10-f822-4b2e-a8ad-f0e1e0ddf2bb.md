# IABV v1.5 - Portable Context Package

Generado: 2026-04-18T01:20:00.951959+00:00
Resumen: Objetivo actual: que modelo de ia manejas o fucionas ? | mejor ruta conocida: adaptive local orchestrator por language_understanding | bloqueos activos: 3 | pendientes: 2 | ajustes sugeridos: 5 | unresolved: 3

Usa este contexto como arranque rapido para una sesion nueva. Si algo aparece como UNRESOLVED, no lo des por confirmado.

## Estado actual del proyecto
que modelo de ia manejas o fucionas ? | World model: lento | Validacion: promoted
- Objetivo activo: que modelo de ia manejas o fucionas ?
- Proyecto activo: Asistencia adaptativa general
- Tarea activa: Asistencia adaptativa general
- Pulso evolutivo: Dossiers recientes: 34 | fallos: 0 | parciales: 0 | incidentes invisibles: 0 | sesiones adaptativas: 36 | autotests: 0 | pendientes Codex: 2. Prioridad sugerida: seguir reforzando evidencia y conocimiento local.
- World model: Hay bloqueos operativos activos que conviene respetar antes de lanzar otra accion.
- Validacion autonoma: La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
Fuente: aggregated_live_state | refs: objective_repository, evolution_review_service, world_model_service, autonomous_validation_cycle | actualizado: 2026-04-18T01:18:46.224837+00:00

## Arquitectura central vigente
La arquitectura sigue siendo una sola: perception -> orchestrator -> governance -> ejecucion -> aprendizaje.
- PerceptionSnapshot: wired | Entrada unificada antes de decidir.
- TaskContextAssembler: wired | Arma contexto, memoria, aprendizaje y world model.
- AdaptiveTaskOrchestrator: wired | Decide ruta, governance y resultado final.
- EnvironmentSelfModel: wired | Describe hardware, runtime y riesgo operativo.
- WorldModelSnapshot: wired | Panorama operativo vivo de herramientas, red y ventanas.
- ExperimentLab: wired | Memoria persistida de resultados y recomendaciones.
Fuente: project_contract | refs: AGENTS.md, bootstrap wiring | actualizado: 2026-04-18T01:20:00.951959+00:00

## Piezas ya implementadas
Capas cerradas: P1 y nucleo de P2. P3 ya deja paquete portable util para sesiones nuevas. Validacion actual: La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
- P1 World Model operativo: active | Observa estado de herramientas, red, foco, procesos y bloqueos antes de actuar.
- P2 Neuroplasticidad operativa: active | Aprende resultados reales y ajusta preferencia futura de rutas e IAs.
- Monitor de evolucion de herramientas: active | Resume desempeno por problema, detecta degradacion y genera propuestas para sandbox.
- SandboxExperiment: active | Valida candidatos antes de promoverlos como decision estable.
- P3 Contexto portable: active | Condensa arquitectura, aprendizaje, bloqueos y pendientes en JSON + Markdown reutilizable.
- Preguntas humanas de aprendizaje: active | Responde desde ExperimentLab y validacion sin disparar autonomia operativa.
Fuente: project_contract | refs: bootstrap wiring, world_model_service, experiment_lab_repository, autonomous_validation_cycle | actualizado: 2026-04-18T01:20:00.951959+00:00

## Aprendizaje acumulado util
Aprendizaje acumulado: adaptive local orchestrator viene saliendo mejor en historial comparable.
- Preferencia actual | adaptive local orchestrator: language_understanding
- Patron aprendido | adaptive local orchestrator: language_understanding
- Patron aprendido | ollama: language_understanding
Fuente: persistent_learning | refs: ExperimentLab, AdaptiveWeightLayer, TaskOutcomeRecorder | actualizado: 2026-04-18T01:20:00.951959+00:00

## Descubrimiento de herramientas
Detecte 23 senal(es) de descubrimiento: 23 activa(s), 0 en evaluacion, 0 promovida(s), 0 descartada(s).
- ChatGPT web asistido: scope=general | estado=detected | confianza=0.89 | ChatGPT web asistido aparece disponible y compatible con general. Conviene validarlo frente a ollama.
- Playwright browser: scope=general | estado=detected | confianza=0.80 | Playwright browser aparece disponible y compatible con general. Conviene validarlo frente a ollama.
- Claude web asistido: scope=general | estado=detected | confianza=0.89 | Claude web asistido aparece disponible y compatible con general. Conviene validarlo frente a ollama.
- ChatGPT instalado: scope=general | estado=detected | confianza=0.89 | ChatGPT instalado aparece disponible y compatible con general. Conviene validarlo frente a ollama.
Fuente: tool_discovery | refs: ToolRegistry, WorldModelSnapshot, ExperimentLab, AutonomousValidationCycleService | actualizado: 2026-04-18T01:20:00.951959+00:00

## Evolucion de herramientas
Superviso 4 contexto(s) con 6 propuesta(s) activa(s), 1 ya decidida(s) y 2 contexto(s) degradado(s). Mejor panorama actual: general favorece ollama con score 1.27 Validacion autonoma: promoted. La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
- general | ollama: route=language_understanding | score=1.27 | exito=100% | bloqueos=0%
- general | adaptive local orchestrator: route=language_understanding | score=0.86 | exito=100% | bloqueos=0%
- general | adaptive local orchestrator: route=ui | score=0.77 | exito=100% | bloqueos=0%
- Probar ChatGPT web asistido para general: ChatGPT web asistido aparece disponible y compatible con general. Conviene validarlo frente a ollama.
- Probar Claude web asistido para general: Claude web asistido aparece disponible y compatible con general. Conviene validarlo frente a ollama.
- Probar Ollama local para cb2d05da-7723-4f27-aaec-61ae4030e880: Ollama local aparece disponible y compatible con cb2d05da-7723-4f27-aaec-61ae4030e880. Conviene validarlo frente a adaptive local orchestrator.
Fuente: experiment_lab_monitor | refs: ExperimentLab, AdaptiveWeightLayer, AutonomousValidationCycle | actualizado: 2026-04-18T01:20:00.951959+00:00

## Decisiones evolutivas
La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
- general | ollama: decision=promoted | ganador=proposed_tool | La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
Fuente: autonomous_validation_cycle | refs: AutonomousValidationCycleService, SandboxExperimentService, ExperimentLab | actualizado: 2026-04-18T01:20:00.951959+00:00

## Autoexaminacion operativa
Autoexaminacion needs_attention: 1 hallazgos activos. Lo mas fuerte ahora es ruta debil o inercial: chatgpt web asistido por ui. Mejoras validadas: 4 | issues recurrentes: 4.
- Ruta debil o inercial: chatgpt web asistido por ui: Se reutilizo 3 veces con exito 0%, bloqueos 0%, fallback 0% y tendencia +0.00.
- Ruta debil o inercial: chatgpt web asistido por ui: Debilitar esta preferencia hasta que la tendencia vuelva a mejorar.
- Pendiente Codex: : Ya existe un patron equivalente Decision: continue_local. Confianza 0.96.
- Ruta debil o inercial: chatgpt web asistido por ui [no_evidence]: Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no.
- Pendiente Codex: [no_evidence]: Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no.
Fuente: derived_review | refs: OperationalSelfExaminationService, ExperimentLab, WorldModelSnapshot | actualizado: 2026-04-18T01:20:00.951959+00:00

## Herramientas y rutas recomendadas
Ruta lider actual: adaptive local orchestrator por language_understanding para cb2d05da-7723-4f27-aaec-61ae4030e880.
- cb2d05da-7723-4f27-aaec-61ae4030e880 | adaptive local orchestrator: language_understanding
- general | ollama: language_understanding
Fuente: persistent_learning | refs: ExperimentLab, StrategySelector, comparison_scope_key | actualizado: 2026-04-18T01:20:00.951959+00:00

## Bloqueos, limites y rutas inviables
2 bloqueos o limitaciones activas.
- network_slow: La red responde, pero esta bastante lenta para rutas web delicadas.
- tool_status: La herramienta no quedo confirmada como disponible en esta laptop.
Fuente: live_operational_state | refs: WorldModelSnapshot | actualizado: 2026-04-18T01:18:46.224837+00:00

## Decisiones ya validadas
3 decisiones ya tienen validacion o confianza suficiente para reutilizarse.
- validation_cycle: La ruta actual quedo bloqueada por network_slow. La alternativa ollama queda mejor alineada con el estado operativo.
- recommended_route | adaptive local orchestrator: language_understanding
- recommended_route | ollama: language_understanding
Fuente: persistent_learning | refs: ExperimentLab, AutonomousValidationCycle | actualizado: 2026-04-18T01:20:00.951959+00:00

## Historial condensado de decisiones
2 decisiones recientes quedaron condensadas para retomar el hilo rapido.
- cb2d05da-7723-4f27-aaec-61ae4030e880 | adaptive local orchestrator: language_understanding
- general | ollama: language_understanding
Fuente: persistent_learning | refs: ExperimentLab, ia_trace_summary | actualizado: 2026-04-18T01:20:00.951959+00:00

## Pendientes priorizados
2 pending issues y 5 mejoras priorizadas.
- 1cce349e-7257-4625-a66c-c85b935c1444: Ya existe un patron equivalente Decision: continue_local. Confianza 0.96.
- 5967e89a-8c63-4a1b-b5e8-2aa564fbd620: Sin hallazgos. Decision: continue_local. Confianza 0.66.
- Pendiente Codex: : Ya existe un patron equivalente Decision: continue_local. Confianza 0.96.
- Pendiente Codex: : Sin hallazgos. Decision: continue_local. Confianza 0.66.
- Pista de mejora reportada por la ejecucion: Seguir con la estrategia propuesta.
- Pista de mejora reportada por la ejecucion: Probar restauracion de sesion o dejar la fase como login guiado con aprobacion.
Fuente: persistent_backlog | refs: pending_issue_repository, evolution_review_service | actualizado: 2026-04-18T01:20:00.951959+00:00

## UNRESOLVED
3 campos siguen sin evidencia suficiente y no deben asumirse.
- UNRESOLVED:cpu_temperature: 
- UNRESOLVED:battery_status: 
- UNRESOLVED:cpu_frequency: 
Fuente: honest_runtime_limits | refs: WorldModelSnapshot, EnvironmentSelfModel, AutonomousValidationCycle | actualizado: 2026-04-18T01:20:00.951959+00:00
UNRESOLVED: UNRESOLVED:cpu_temperature, UNRESOLVED:battery_status, UNRESOLVED:cpu_frequency

## Reglas duras que no deben romperse
Este paquete portable no reemplaza la arquitectura: solo la condensa y la hace reutilizable.
- No crear otro cerebro ni otro orquestador.
- No duplicar PerceptionSnapshot ni crear una memoria paralela.
- No romper governance ni saltarse bloqueos del world model.
- Cambios minimos, reversibles y verificables.
- Si algo no puede confirmarse con evidencia, marcar UNRESOLVED.
- Los ViewModels observan y explican; no inventan decisiones de ruta.
Fuente: project_contract | refs: AGENTS.md | actualizado: 2026-04-18T01:20:00.951959+00:00