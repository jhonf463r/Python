# AUDIT DEEP REPORT — IABV v1.5

Repositorio: `jhonf463r/Python` (subdirectorio `IABV_v1.5/`).
Commit inspeccionado: `main` (clon local).
Metodología: inspección de código real, verificación de contratos, ejecución parcial de pruebas. Todo hallazgo lleva evidencia `file:line`. Lo que no se pudo comprobar queda marcado `UNRESOLVED`.

Este reporte es **solo diagnóstico**. La Fase 6 (correcciones) NO se ha aplicado; requiere aprobación explícita.

---

## 1) RESUMEN EJECUTIVO

IABV v1.5 **sí tiene núcleo real**, no es un proyecto vacío. El cerebro central existe (`AdaptiveTaskOrchestrator`), el contrato unificado de percepción existe (`PerceptionSnapshot`), el World Model existe y está cableado (`WorldModelService`/`WorldModelSnapshot`), el aprendizaje comparativo real existe (`ExperimentLab` + `StrategySelector` + `AdaptiveWeightLayer`), el contexto portable existe (`PortableContextService`) y la autoexaminación operativa existe (`OperationalSelfExaminationService`). Las capas P1–P4 y N3–N4 declaradas como cerradas en `AGENTS.md` están efectivamente instanciadas en `bootstrap.py` y observadas por la UI.

Pero hay **bugs reales en el núcleo** que contradicen afirmaciones del estado actual:

1. **La preferencia explícita del asistente se pierde en flujos de tools** cuando el `ModeSelector` elige una familia distinta Y la `ToolCard` preferida no queda marcada `available` en ese momento. `_enforce_explicit_external_selection` se rinde en silencio y deja pasar la familia equivocada.
2. **13 pruebas existentes fallan en `main`** (`test_tool_teach_service.py` + `test_autonomous_evolution_service.py`), y describen exactamente este mismo fallo: el sistema prefiere `claude_web_assisted` / `chatgpt_web_assisted` cuando el usuario pidió `codex_installed`, o marca `failed` escenarios que la prueba espera en `ingested`/`awaiting_response`.
3. **`IntentUnderstandingService.classify_with_schema` rompe el contrato de `InferenceRequest`** al reconstruir un request sintético que descarta `site_hint`, `prompt`, `task_role`, `deep_reasoning`, `allowed_tools`, `screenshots`, `steps` y demás campos del request original. El orquestador usa esta ruta en `handle_request` y `build_decision_context_preview`, así que la intención puede clasificarse con menos contexto del que la propia `InferenceRequest` ya cargaba.
4. **El ViewModel del Control Center acumula lógica que no es "observadora"**: lanza hilos daemon en 8 sitios distintos, ejecuta decisiones de consulta externa, genera `goal_parameters` y toca persistencia, lo cual contradice el contrato declarado en `AGENTS.md` ("los ViewModels no deben convertirse en otro cerebro ni tomar decisiones de ruta").
5. **El `control_center_viewmodel.py` tiene 5484 líneas**. No es un problema por sí solo, pero dificulta mantener invariantes: muchas decisiones de ruta quedan implícitas allí (shortcuts de chat, explicit_assistant_preference, run_external_consultation).

No hay duplicación del cerebro (sólo hay un `AdaptiveTaskOrchestrator`). No hay `PerceptionSnapshot` duplicado. No hay un self-model paralelo. Hay **solapamiento de autoridad menor** entre `ControlCenterViewModel` y el orquestador, no duplicación estructural.

**Veredicto rápido:** el proyecto NO está listo para aprobación, pero está **más cerca de lo que parece**. Con 3–5 fixes quirúrgicos (preferencia del asistente, clasificador con request completo, tests rotos, y una línea de responsabilidad clara entre ViewModel y orquestador) se cierra el núcleo. Detalle en §15 y §16.

---

## 2) ESTADO REAL DEL REPO

Conteo real (verificado por `wc -l` y listados de directorio):

- `src/iabv_v15/`: 159 archivos `.py`.
- `domain/models.py`: **2494 líneas** (contratos soberanos).
- `bootstrap.py`: **790 líneas** (wiring real).
- `services/` con 17 subdominios:
  - `adaptive/` (9 módulos): orquestador, intent, context assembler, planner, approval gate, capability readiness, strategy pack registry, task outcome recorder, autonomy governance, goal engine, adaptive weight layer, execution playbook.
  - `evolution/` (17 módulos): world model, environment self-awareness, portable context, self-examination, autonomous evolution, incident packet, hidden incident detector, execution dossier, live audit, self-check orchestrator, tool discovery, tool evolution monitor, autonomy activity projector, session health, user clue, runtime signal collector, evolution review.
  - `tools/` (11 módulos): registry, tool_teach_service, ui_execution_runner, tool_operational_executor, interaction_mode_selector, tool_adapters, tool_approval_policy, tool_memory, tool_sandbox, tool_rollback_manager, tool_validator, interaction_learning_service.
  - `lab/` (5 módulos): experiment_lab, strategy_selector, decision_scoring_engine, algorithm_benchmark_registry, suites.
  - `capture/` (15 módulos): browser_*, replay_*, redaction_engine, sensitive_field_detector, site_policy_registry, universal_perception_service, demo_capture_service, training_profile_manager, secret_vault.
  - `roles/` (6): local_role_router, embedding_index_service, analytics_strategy_service, customer_support_service, engineering_review_service, sql_query_advisor_service, teaching_gap_analyzer.
  - `llm/`, `inference/`, `knowledge/`, `self_teach/`, `audit/`, `training/`, `security/`, `ux/`, `development/`, `environment/`, `providers/`.
- `ui/viewmodels/` (6):
  - `control_center_viewmodel.py` — 5484 líneas.
  - `capture_studio_viewmodel.py` — 2784 líneas.
  - `evolution_center_viewmodel.py` — 594 líneas.
  - `dashboard_viewmodel.py`, `knowledge_base_viewmodel.py`, `provider_settings_viewmodel.py`, `run_history_viewmodel.py`.
- `infra/persistence/` (23 repos) + `database.py` con creación idempotente (`CREATE TABLE IF NOT EXISTS`) en `__init__` (`database.py:19-317`). **No hay riesgo de "tablas no preparadas antes de refrescos en background"**: el constructor del `AppDatabase` crea todo antes de cualquier servicio que lo consuma (`bootstrap.py:141`).
- `tests/` con 59 archivos. Una corrida parcial (Fase 1 focalizada) arrojó **56 passed, 13 failed** (todos los fallos concentrados en `test_tool_teach_service.py` y `test_autonomous_evolution_service.py`). Detalle en §4, §11, §14.
- `data/evolution/` tiene artefactos vivos (`portable_context/latest.json`, `self_examination/latest.json`, `world_model/`) y ≈60 carpetas de ejecuciones/debug/live_audit — legacy útil, no son basura, pero conviene archivarlos.
- Documentación de gobierno: `AGENTS.md` (206 líneas). Es el control maestro, está actualizado y explícito.

Lo que **no existe** en el repo (y era plausible esperar):
- No hay una "multi-IA coordination layer" explícita más allá del routing por `LocalRoleRouter` + `tool_teach_service` eligiendo la familia (`codex`/`chatgpt`/`claude`/`ollama`). No hay sincronización stateful entre asistentes; hay selección por evidencia y preferencia. Ver §6.
- No hay un `ChatOrchestratorService` separado: el chat vive dentro de `ControlCenterViewModel` (con el orquestador por debajo). No hay capa intermedia dedicada al "chat central robusto".
- No hay un `AuditCentralService` único; la auditoría es una red de servicios (`live_audit_supervisor`, `incident_packet_service`, `execution_dossier_service`, `audit_teach_verification_service`) que convergen en los dossiers y los incident packets.

---

## 3) MAPA DE MÓDULOS (arquitectura real por capas)

Capas verificadas en `bootstrap.py` y `domain/models.py`:

### Capa de contratos (dominio)
- `domain/models.py` (2494 líneas). Una sola fuente de verdad de Pydantic. Incluye `PerceptionSnapshot` (line 1860), `WorldModelSnapshot` (612), `EnvironmentSelfModel` (505), `UniversalPerceptionSignal` (1801), `IATraceEntry` (1826), `PortableContextPackage` (1892), `SelfExaminationSnapshot` (1922), `TaskIntent` (1714), `IntentSchema` (1740), `InferenceRequest` (2341), `DecisionContext` (712), `StrategyCandidate` (2249), `AdaptiveSession`, `ApprovalCheckpoint`, `TaskOutcome`, `ToolCard`, `ToolTask`, `ToolResult`, etc.

### Capa de infraestructura
- `infra/config.py`, `infra/logging.py`, `infra/persistence/database.py`, 23 repositorios SQLite + JSON en `infra/persistence/`.

### Capa de percepción unificada
- `services/capture/universal_perception_service.py` (construye `UniversalPerceptionSignal`).
- `services/evolution/environment_self_awareness_service.py` (mantiene `EnvironmentSelfModel`).
- `services/evolution/world_model_service.py` (mantiene `WorldModelSnapshot`).
- `services/adaptive/task_context_assembler.py` (arma `PerceptionSnapshot` integrando los tres).

### Capa de decisión (cerebro real)
- `services/adaptive/adaptive_task_orchestrator.py` — **único orquestador**.
- `services/adaptive/intent_understanding_service.py` — clasifica.
- `services/adaptive/autonomy_governance_policy.py` — gobierna qué rutas son viables.
- `services/roles/local_role_router.py` — decide ruta/proveedor local.
- `services/adaptive/strategy_pack_registry.py` + `adaptive_planner_service.py` + `execution_playbook_service.py` + `capability_readiness_service.py` + `approval_gate_service.py` + `goal_engine.py` + `task_outcome_recorder.py`.

### Capa de ejecución
- `services/tools/tool_registry.py`, `tool_teach_service.py`, `tool_operational_executor.py`, `interaction_mode_selector.py`, `ui_execution_runner.py`, `tool_adapters.py` (7 adapters: playwright, ollama, shell, desktop_human, aider, mcp, external_assistant).
- `services/tools/tool_sandbox.py`, `tool_rollback_manager.py`, `tool_validator.py`, `tool_approval_policy.py`.
- `services/inference/inference_service.py`, `services/llm/*` (bridges y prompts).

### Capa de aprendizaje (neuroplasticidad)
- `services/lab/experiment_lab.py`, `strategy_selector.py`, `decision_scoring_engine.py`, `algorithm_benchmark_registry.py`.
- `services/adaptive/adaptive_weight_layer.py`.
- `services/adaptive/task_outcome_recorder.py` (cierra loop desde ejecución normal).
- `services/evolution/tool_evolution_monitor.py`, `tool_discovery_service.py`.
- `services/self_teach/self_teach_orchestrator.py`.

### Capa de auditoría / replay / memoria
- `services/audit/live_audit_supervisor.py`, `audit_teach_verification_service.py`.
- `services/evolution/incident_packet_service.py`, `execution_dossier_service.py`, `hidden_incident_detector.py`, `session_health_service.py`, `evolution_review_service.py`, `runtime_signal_collector.py`, `user_clue_service.py`.
- `services/capture/replay_annotation_service.py`, `replay_visual_assembler.py`, `replay_learning_feedback_service.py`, `replay_confidence_service.py`.
- `services/knowledge/*`, `services/adaptive/unified_memory_layer.py`.

### Capa de evolución autónoma / contexto portable / autoexaminación
- `services/evolution/autonomous_evolution_service.py`.
- `services/evolution/portable_context_service.py`.
- `services/evolution/operational_self_examination_service.py`.
- `services/evolution/autonomous_validation_cycle_service.py` (vía bootstrap; usado por `AutonomousValidationCycle`).

### Capa UI observadora
- `ui/viewmodels/` (6 VMs), `ui/qml/*` (no inspeccionado en detalle en esta auditoría — `UNRESOLVED`: si QML respeta solo-observación).
- Controladores: `navigation_controller`, `theme_controller`, `main_window_bridge`.

### Dependencia entre capas (observada en bootstrap)
Orden de instanciación (líneas aprox. en `bootstrap.py`):
1. Config + tema + DB + 23 repositorios (141–199).
2. Provider configs + adapters + tool_registry (200–226).
3. `environment_self_awareness_service` + `universal_perception_service` + `world_model_service` (228–240), con `role_router=None` inicial.
4. Servicios de aprendizaje (`experiment_lab`, `adaptive_weight_layer`, `strategy_selector`) y de captura.
5. `LocalRoleRouter` creado (313); luego **inyectado hacia atrás** en `environment_self_awareness_service` y `world_model_service` con un `request_refresh(...)` (330–333). Es wiring circular controlado; funciona porque los servicios aceptan `role_router` opcional.
6. `task_context_assembler` + `capability_readiness_service` + `approval_gate_service` + `execution_playbook_service` + `autonomy_governance_policy` + `goal_engine`.
7. `tool_teach_service` + `tool_operational_executor` + `tool_memory` + `autonomous_evolution_service`.
8. `adaptive_task_orchestrator` (528) — **cerebro final** — recibe todo por inyección.
9. `portable_context_service` recibe referencia al orquestador y al assembler (544–545) después de crear el orquestador.
10. UI VMs se construyen en `_build_ui_objects()` (593–696).

El grafo es consistente, no hay ciclos reales; los pocos casos de inyección hacia atrás son explícitos (comentario `# --- Task A ---` en bootstrap:495–525).

---

## 4) CEREBRO CENTRAL ACTUAL

**Único orquestador:** `AdaptiveTaskOrchestrator.handle_request` (`services/adaptive/adaptive_task_orchestrator.py:113–200`). Es la cadena real de decisión:

```
InferenceRequest
  → intent_service.classify_with_schema     (intent + IntentSchema)
  → role_router.build_decision_from_intent  (RoleRoute tentativa)
  → context_assembler.build_perception_snapshot  (PerceptionSnapshot completo:
       task_context + decision_context + world_model + env_self_model
       + visual_signal + goal_context + memory_snapshot + ia_trace)
  → capability_service.evaluate             (CapabilityReadiness)
  → strategy_pack_registry.resolve_pack + build_candidates
  → planner_service.build_playbook
  → approval_gate_service.evaluate
  → AdaptiveSession + outcome preliminar
  → task_outcome_recorder.record
  → route + InferenceResult
```

`govern_adaptive_payload` (202–260) es el puente a `autonomous_evolution_service.plan_or_execute` cuando corresponde consulta externa; tiene lógica de reintento con `max_retries=3` y agota con `retry_exhausted=True`.

### Hallazgo 4.1 (contrato) — `classify_with_schema` descarta campos del request original
- Evidencia: `services/adaptive/intent_understanding_service.py:461–496`.
- `classify_with_schema(user_goal, goal_parameters, conversation_history=...)` construye internamente un nuevo `InferenceRequest(user_goal=..., goal_parameters=..., conversation_context=..., metadata={...})` y descarta:
  - `site_hint` (el `classify()` interno hace `site_hint = request.site_hint or detected_site` en línea 101, así que si el llamador original tenía `site_hint="wplay"`, se pierde salvo que venga duplicado en `goal_parameters['site_hint']`).
  - `prompt`, `task_role`, `role_hint`, `allowed_tools`, `deep_reasoning`, `requires_vision`, `requires_visual_reasoning`, `complexity`, `ambiguity`, `approval_mode`, `execution_scope`, `enable_planning`, `screenshots`, `steps`, `read_only_sql`, `auto_route`, `knowledge_scope`.
- Llamadores:
  - `adaptive_task_orchestrator.py:102` (`build_decision_context_preview`).
  - `adaptive_task_orchestrator.py:115` (`handle_request`).
- El `ControlCenterViewModel` (en `_chat_shortcut_analysis`, línea 3130) sí usa `classify(request)` pasando el `InferenceRequest` completo; esa ruta está sana, pero es shortcut de preview, no la ruta principal.
- **Impacto funcional:** al clasificar desde `handle_request`, la intención pierde el `site_hint` explícito si no viene también en `goal_parameters`, pierde `task_role` (que puede inclinar la decisión), y pierde `allowed_tools` (que acota posibilidades reales). Es un **contrato roto dentro del propio núcleo**.

### Hallazgo 4.2 (bug real) — preferencia del asistente se pierde
- Evidencia directa: `tests/test_tool_teach_service.py::test_tool_teach_service_explicit_codex_request_overrides_cross_family_selector` **falla en main**. La request lleva `tool_id='codex_installed'`, `assistant_preference='codex'`, `assistant_kind='codex'`, `consultation_scope='external_assistant'`, y `build_task_from_request` devuelve `chatgpt_web_assisted`.
- Causa: `services/tools/tool_teach_service.py:1149–1196` (`_enforce_explicit_external_selection`). El override al selector cross-family está condicionado por:
  - `preferred_card.available` (línea 1173): si la ToolCard de `codex_installed` no quedó `available=True` en el momento del refresh, el override **retorna la selección equivocada en silencio**, sin registrar nada y sin caer a fallback local.
  - No hay log/trace de que la preferencia explícita fue ignorada. No hay `UNRESOLVED` emitido. No se marca `selection_policy='explicit_assistant_override_blocked'`.
- Síntomas en los 13 tests rotos: varios casos terminan en `claude_web_assisted` cuando se pidió `codex_installed` u `ollama_llm`; varios terminan en `'failed'` cuando la prueba espera `'ingested'` o `'awaiting_response'`.
- **Esto contradice directamente la misión del sistema** ("preservación de la preferencia del asistente/IA") y es uno de los criterios que el usuario pide garantizar en Fase 6.

---

## 5) PERCEPCIÓN Y SELF-MODEL

### Lo que existe, verificado
- `EnvironmentSelfModel` (`domain/models.py:505`) cubre `hardware_profile`, `runtime_profile`, `capability_graph`, `available_tools`, `missing_tools`, `risk_signals`, `ai_capacity`, `last_scan`. Es razonable.
- `WorldModelSnapshot` (`domain/models.py:612`) cubre `active_windows`, `focused_window`, `tool_live_status`, `network_status`, `background_processes`, `detected_blocks`, `observation_permission_gates`, `assistant_thread_signals`. Está bien modelado; incluye campos para `wrong_thread`, `assistant_login_required`, `session_expired`.
- `UniversalPerceptionSignal` (`domain/models.py:1801`) es el signal puntual por ventana/herramienta.
- `PerceptionSnapshot` (`domain/models.py:1860`) integra: `task_context`, `decision_context`, `goal_context`, `memory_snapshot`, `live_audit`, `runtime_signals`, `session_health`, `ia_trace`, `visual_signal`, `environment_self_model`, `world_model`, `external_state_flags`, `unresolved_fields`, `metadata`. Es un contrato **sólido y unificado**.

### Flujo real verificado
`TaskContextAssembler.build_perception_snapshot(request, intent, route_decision, intent_schema)` compone el `PerceptionSnapshot`. Se llama desde `AdaptiveTaskOrchestrator.handle_request:122` y `build_decision_context_preview:108`. Se incluye en `AdaptiveSession.metadata['perception_snapshot']` (`orchestrator.py:170`).

### Limitaciones / desviaciones
- **El `PerceptionSnapshot` no incluye el `IntentSchema` como atributo** directo. Solo se cablea a través de `build_perception_snapshot(..., intent_schema=intent_schema)` y se incrusta en `session.metadata['etapa2_conversation_analysis']` (orchestrator.py:171). Los consumidores río abajo (por ejemplo la UI o `autonomous_evolution`) deben mirar `session.intent.metadata['conversation_analysis']` o el metadata de la sesión. No está roto, pero la información vive en 3 sitios (intent.metadata, schema, session.metadata['etapa2_conversation_analysis']) — es **duplicación leve**.
- El `PerceptionSnapshot.visual_signal` es `VisualSignalSnapshot`, pero el ViewModel también llama `universal_perception_service.build_signal(...)` por su cuenta en `_latest_visual_signal` (`control_center_viewmodel.py:322`) y lo sirve a QML. El ViewModel sólo cache/observa, no decide; no rompe contrato, pero duplica un camino.
- `UNRESOLVED`: no revisé qué tan actualizado queda el `world_model` entre turnos largos; depende del `request_refresh(reason=..., full=False)` que se llama en bootstrap, pero la periodicidad la gobierna el propio servicio. Hay que correr en vivo para confirmar.

---

## 6) SINCRONIZACIÓN ENTRE IAs

La visión pide "coordinación entre múltiples IAs". Lo que existe:

- **Selección por familia:** `ToolCard.assistant_kind` permite mapear `codex`, `chatgpt`, `claude`, `ollama` a tool_ids específicos (`codex_installed`, `chatgpt_installed`, `chatgpt_web_assisted`, `claude_installed`, `claude_web_assisted`, `ollama_llm`, etc.).
- **Laboratorio comparativo:** `ExperimentLab` + `StrategySelector` + `AdaptiveWeightLayer` permiten comparar rutas por resultado real y asesorar al `tool_teach_service` (`_external_lab_recommendation` en tool_teach_service.py:~1280).
- **Preferencia explícita:** `goal_parameters['assistant_preference']` + `goal_parameters['consultation_scope']='external_assistant'`, enforced por `_enforce_explicit_external_selection` (con el bug del Hallazgo 4.2).
- **Trazabilidad IA por IA:** `IATraceEntry` (`domain/models.py:1826`) y `ia_trace` en `PerceptionSnapshot`. `tool_teach_service` y `autonomous_evolution_service` registran `comparison_scope_key` y `source_trace_ids`.

Lo que **no** existe:
- No hay "conversación cruzada entre IAs". El sistema no le pregunta a ChatGPT sobre la respuesta de Codex ni vota entre varias respuestas. Hay selección y aprendizaje, no consenso multi-IA.
- No hay paralelismo real: el `autonomous_evolution_service.plan_or_execute` ejecuta una consulta a la vez.
- **Estado clasificación:** parcialmente alineado. La capa comparativa sí cumple el espíritu de "aprendizaje por comparación de rutas y configuraciones". El "multi-IA coordinado en paralelo" **no** existe como concepto explícito; hay que definir si eso está fuera de alcance v1.5 o es un gap real.

---

## 7) APRENDIZAJE Y EVOLUCIÓN

Existe y es real. Verificado:

- `ExperimentLab` (services/lab/experiment_lab.py): entrena comparando rutas/configuraciones para scope comparable (`comparison_scope_key`).
- `StrategySelector` (services/lab/strategy_selector.py): recomienda ruta por historial real.
- `AdaptiveWeightLayer` (services/adaptive/adaptive_weight_layer.py): ajusta peso futuro.
- `TaskOutcomeRecorder` (services/adaptive/task_outcome_recorder.py): cierra loop desde `orchestrator.handle_request` línea 197 — todo request deja rastro.
- `tool_memory` + `interaction_learning_service`: memoria por patrón y observación.
- `tool_evolution_monitor` + `tool_discovery_service`: discovery activo.
- `operational_self_examination_service`: detecta patrones recurrentes y sugiere ajustes; **incluye validación de si sus ajustes previos funcionaron**.
- `autonomous_validation_cycle_service`: valida candidatos y sólo promueve lo que tiene evidencia.

Persistencia viva: `data/evolution/portable_context/latest.json`, `data/evolution/self_examination/latest.json`, `data/evolution/world_model/`. Artefactos presentes.

### Riesgo observado
- La superficie de aprendizaje está **dispersa en muchos módulos pequeños**. No hay un `LearningFacade` único, lo cual obliga a que tanto `tool_teach_service` como `autonomous_evolution_service` y `portable_context_service` consulten 3–4 subsistemas cada uno. No es un bug; es **deuda tolerable**.

---

## 8) AUDITORÍA Y REPLAY

Existe una red de servicios bien cableada:

- **Incidentes:** `incident_packet_service`, `hidden_incident_detector`, `hidden_incident_repository`, `pending_issue_repository`.
- **Dossiers:** `execution_dossier_service` + `execution_dossier_repository` (persiste ejecuciones completas a disco, visibles en `data/...`).
- **Supervisión viva:** `live_audit_supervisor`, `session_health_service`, `user_clue_service`, `runtime_signal_collector`.
- **Verificación de enseñanzas:** `audit_teach_verification_service`.
- **Replay:** `replay_annotation_service`, `replay_visual_assembler`, `replay_learning_feedback_service`, `replay_confidence_service`.
- **Redacción / privacidad:** `redaction_engine`, `sensitive_field_detector`, `secret_vault`, `site_policy_registry`. Los datos sensibles se redactan antes de persistir.
- **Packets para Codex:** `incident_packet_service.build_codex_packet_for_issue(...)`.

Trazabilidad: `IATraceEntry` + `ia_trace` en Perception + `comparison_scope_key`. **La trazabilidad es real**, no es decorativa.

### Limitación
- Los artefactos de auditoría crecen sin límite en `data/evolution/`. Hay ≈60 carpetas `live_*`, `debug_*`, `test_*_workspace`. No es un bug, pero conviene pensar en rotación — **deuda tolerable**.

---

## 9) UI Y VIEWMODELS

### `ControlCenterViewModel` (5484 líneas)
- **Sí observa** adecuadamente: `dataChanged.emit()`, `taskResolved.emit(...)`, `taskFailed.emit(...)`.
- **Pero hace más que observar**. Responsabilidades detectadas que exceden "observador":
  - Decide la `explicit_assistant_preference` de la entrada del usuario (líneas 618–673). Esa decisión debería nacer en `IntentUnderstandingService`, no en la UI.
  - Construye `goal_parameters` con `consultation_scope='external_assistant'` y `assistant_preference` antes de llamar al orquestador (695–708).
  - Ejecuta consulta externa directa en `_run_external_consultation` (4668) lanzando `threading.Thread`. La decisión la toma el VM.
  - Lanza 8 hilos daemon (`threading.Thread`): líneas 4010, 4700, 4877, 4950, 4985, 5044, 5061, 5078.
- `AGENTS.md` dice explícitamente: *"Los ViewModels no deben convertirse en otro cerebro ni tomar decisiones de ruta por su cuenta"*. Parcialmente roto.

### `EvolutionCenterViewModel` (594 líneas)
- Observa dossiers, incidentes, world model, portable_context, self_examination. Ejecuta `runDeepSelfCheck` lanzando un hilo daemon (línea 342); eso está OK porque no decide ruta, solo dispara una suite.
- Nota de `AGENTS.md`: "se elimino refresh redundante de autoexaminacion en EvolutionCenterViewModel" — verificado, no hay llamadas redundantes a `self_examination_service.refresh(...)` dentro del VM.

### `CaptureStudioViewModel` (2784 líneas)
- No inspeccionado en profundidad en esta auditoría. `UNRESOLVED`: requiere inspección similar al Control Center para confirmar que no decide tool_id ni route_id.

### Persistencia desde VMs
- `ControlCenterViewModel` recibe 7 repositorios por constructor (`episode_repository`, `knowledge_repository`, `run_repository`, `session_artifact_repository`, `experiment_lab_repository`, `tool_record_repository`, `scenario_run_repository`, `objective_repository`). Lee de ellos directamente. Esto es una **dependencia alta**, no una ruptura de contrato estricta; el patrón es lectura, no escritura silenciosa. Pero sí implica acoplar la UI a la forma de los repos.
- No encontré casos donde el VM escriba a persistencia antes de que la tabla exista. El esquema se crea en `AppDatabase.__init__` (database.py:19), y `AppDatabase` se instancia antes que todos los servicios en `bootstrap.py:141`.

### Suites de UI
- `AGENTS.md` avisa: *"Varias suites de UI siguen siendo lentas en Windows; no es una falla funcional, pero si una deuda de rendimiento de pruebas"*. Confirmado como deuda, no verifiqué su velocidad aquí.

---

## 10) DIFERENCIAS CON LA VISIÓN ORIGINAL

| Visión original | Estado real | Clasificación |
|---|---|---|
| Chat central robusto | Existe dentro de `ControlCenterViewModel`, sin capa dedicada. Funciona, pero el VM mezcla chat + decisión de asistente. | **parcial / desviado** |
| Razonamiento desde percepción unificada | `PerceptionSnapshot` integra env + world + goal + visual + ia_trace. Se alimenta en cada request. | **alineado / fortalecido** |
| Self-model operativo | `EnvironmentSelfModel` presente y cableado en `WorldModelService`. | **alineado** |
| World model | `WorldModelSnapshot` + `WorldModelService` cubre ventanas/foco/red/procesos/bloques. | **alineado / fortalecido** |
| Coordinación entre múltiples IAs | Hay selección por familia + lab comparativo, pero no consenso/paralelismo ni diálogo inter-IA. | **parcial** |
| Aprendizaje por comparación de rutas y configuraciones | `ExperimentLab` + `StrategySelector` + `AdaptiveWeightLayer` + `comparison_scope_key`. | **alineado / fortalecido** |
| Auditoría viva y replay | Red de servicios amplia y real. | **alineado / fortalecido** |
| Detección formal de fallas externas reales | `ExternalStateFlag` + `canonical_external_state_flags` + `_consultation_external_state_flags`. Cubre `wrong_thread`, `account_limited`, `session_expired`, `assistant_login_required`. | **alineado** |
| Automejora guiada | `GuidedImprovementCycle` + `OperationalSelfExaminationService` + `AutonomousValidationCycle`. | **alineado** |
| UI clara que muestra estado real | Los VMs observan, pero `ControlCenterViewModel` **decide algunas rutas**. | **parcial / desviado** |
| Evolución del sistema sin duplicar arquitectura | No hay segundo cerebro. No hay `PerceptionSnapshot` duplicado. Hay sólo solapamiento menor. | **alineado** |
| Contexto portable | `PortableContextService` persiste `data/evolution/portable_context/latest.json`. | **alineado** |
| Autoexaminación operativa | `OperationalSelfExaminationService` activo. | **alineado** |

---

## 11) DESVIACIONES Y POSIBLES CAUSAS

1. **ControlCenterViewModel como semi-cerebro.** Causa probable: la UI apareció antes que `IntentUnderstandingService` o antes de que `goal_engine` existiera, así que el VM asumió responsabilidades que hoy podría delegar. Fix de bajo riesgo: mover `_explicit_assistant_preference` a un `AssistantPreferenceResolver` consumible por el orquestador.
2. **`classify_with_schema` con firma estrecha.** Causa probable: el método se agregó para una llamada conveniente desde código que ya tenía `user_goal + goal_parameters + conversation_history` (por ejemplo desde un shortcut UI), y los llamadores del orquestador lo adoptaron sin notar que perdían campos. Fix: aceptar `InferenceRequest | None` y, si viene, NO reconstruirlo.
3. **`_enforce_explicit_external_selection` silenciosa.** Causa probable: el guard con `preferred_card.available` se añadió para evitar forzar herramientas no instaladas, pero no hay camino "mejor alternativa dentro de la misma familia" ni log de que la preferencia fue bloqueada. Fix: al no poder respetar la familia, marcar `UNRESOLVED`/`assistant_preference_blocked` y emitir guidance explícito.
4. **13 tests rojos en main.** Causa probable: tests pre-existentes describen el comportamiento "correcto" del override, y la implementación actual no los cumple tras un cambio reciente (no investigué el git blame fino). Son tests **útiles como especificación** del fix.
5. **Gap de "multi-IA paralela".** Causa probable: fuera del alcance v1.5. Declarar explícitamente o moverlo a backlog.

---

## 12) DUPLICACIONES Y SOLAPAMIENTOS

Verificado con grep/lectura:

- **NO hay** duplicación de cerebro (sólo `AdaptiveTaskOrchestrator` ejecuta `handle_request`).
- **NO hay** duplicación de `PerceptionSnapshot`, `EnvironmentSelfModel`, `WorldModelSnapshot`, `UniversalPerceptionSignal` (1 definición cada uno en `domain/models.py`).
- **NO hay** duplicación estructural entre `ExperimentLab` / `StrategySelector` / `tool_teach_service`: cada uno tiene responsabilidad distinta (lab compara, selector recomienda, teach aplica).
- **Sí hay solapamientos leves**:
  - `_explicit_assistant_preference` vive en `ControlCenterViewModel` (línea 618). La lógica de "qué asistente quiere el usuario" debería estar en `IntentUnderstandingService` o en un resolver dedicado que ambos (VM y orquestador) consuman.
  - `classify` vs `classify_with_schema` con firmas incompatibles; el schema se arma desde análisis ya calculado por `classify`, pero se rearma la request (hallazgo 4.1). Hay dos caminos para lo mismo.
  - Información del IntentSchema vive en 3 lugares: `intent.metadata['conversation_analysis']`, `IntentSchema`, `session.metadata['etapa2_conversation_analysis']`. Los 3 son consistentes pero se pueden derivar en el mismo instante. Es duplicación de lectura, no de lógica.
- **NO detecté** colisión entre `goal_engine` y `goal_context` del TaskContext; `goal_engine.attach_session_goal_context` enlaza pero no reemplaza.

---

## 13) GAPS REALES (qué falta para cerrar el núcleo)

Ordenados por importancia:

1. **Fix de preferencia explícita del asistente** en `_enforce_explicit_external_selection`, con fallback explícito dentro de la familia y con emit de guidance cuando la ruta preferida está bloqueada. (crítico)
2. **Fix de `classify_with_schema`** para no descartar campos del `InferenceRequest` original; idealmente aceptar la request completa o construir el schema desde `classify(request)` sin recrear la request. (crítico para coherencia)
3. **Reparar los 13 tests rojos** de `test_tool_teach_service.py` y `test_autonomous_evolution_service.py`. (crítico)
4. **Extraer la decisión de asistente explícito** de `ControlCenterViewModel` a un servicio (por ejemplo `AssistantPreferenceResolver` dentro de `services/adaptive/` o `services/roles/`), consumido por el orquestador vía inyección. Sin eso, cualquier no-UI que llame al orquestador (tests, sub-Devin, API futura) no tiene cómo preservar la preferencia.
5. **Logging/guidance cuando la preferencia no puede cumplirse.** Hoy se silencia. Debe aparecer en `session.metadata['assistant_preference_blocked']` + `guidance` explícita al usuario.
6. **Limitar el crecimiento de `data/evolution/`** (rotación/archival). Deuda tolerable pero creciente.
7. **Alinear documentación**: `AGENTS.md` declara N3 y N4 cerradas — lo están en esencia, pero los 13 tests rotos contradicen una lectura optimista del estado P2/N4; conviene registrar los 13 como `UNRESOLVED` hasta el fix.

Gaps aspiracionales (no críticos para v1.5):
- "Multi-IA coordinada en paralelo / consenso": no existe; decidir si se incluye en v1.5 o se agenda.
- Una capa `ChatOrchestratorService` dedicada al chat central (opcional; hoy vive en el VM + orquestador).

---

## 14) RIESGOS Y DEUDA (clasificación por impacto)

### Riesgo alto (bloquea aprobación)
- **R-A-1: Preferencia explícita del asistente se pierde en silencio.** Evidencia: `tool_teach_service.py:1149–1196` + test rojo `test_tool_teach_service_explicit_codex_request_overrides_cross_family_selector`. Impacto: el usuario pide Codex y recibe ChatGPT/Claude sin aviso. Rompe uno de los criterios explícitos de aprobación.
- **R-A-2: 13 pruebas rojas en `main`** relacionadas con `tool_teach_service` y `autonomous_evolution_service`. Las suites se ejecutan hoy en CI implícito como gate, y no pasan. Mientras haya 13 rojas, el núcleo no puede firmarse.
- **R-A-3: `classify_with_schema` descarta campos del request.** Impacto: intención clasificada con menos contexto del real; decisiones río abajo pueden ser incorrectas para flujos con `site_hint`/`task_role` explícitos que no vienen en `goal_parameters`.

### Riesgo medio
- **R-M-1: `ControlCenterViewModel` decide ruta de asistente externo.** Impacto: la misma lógica no es reutilizable desde tests o desde un llamador no-UI. No bloquea aprobación, pero erosiona el contrato "UI observadora".
- **R-M-2: Ausencia de telemetría cuando `_enforce_explicit_external_selection` baila.** Impacto: no hay forma de auditar en vivo cuándo el sistema degradó la preferencia.
- **R-M-3: 5484 líneas en un solo VM** dificultan mantener invariantes. No es urgente, pero cualquier fix futuro se vuelve más lento.

### Riesgo bajo
- **R-B-1: Duplicación de IntentSchema en 3 ubicaciones de metadata.** Consistente hoy; puede divergir si hay edición parcial. Fácil de normalizar.
- **R-B-2: Wiring circular controlado en `WorldModelService`/`EnvironmentSelfAwarenessService` ↔ `LocalRoleRouter`.** Funciona con `request_refresh(reason='role_router_ready')` en bootstrap:330–333; no es bonito pero es seguro.
- **R-B-3: Crecimiento sin límite de `data/evolution/`.** Conocida.

### Deuda tolerable
- D-T-1: Suites UI lentas en Windows (ya documentado en `AGENTS.md`).
- D-T-2: Superficie de aprendizaje dispersa (3–4 servicios a consultar). Funcional; facade puede llegar después.
- D-T-3: Docstrings/comentarios mezclados con español sin acentos y caracteres ` ` al inicio de algunos archivos (ej. `intent_understanding_service.py:1`). Cosmético.

### UNRESOLVED
- U-1: Velocidad exacta de `world_model` refresh en sesión larga (no medí en vivo).
- U-2: Disciplina de "no-decidir-ruta" dentro de `CaptureStudioViewModel` (no inspeccionado a fondo, 2784 líneas).
- U-3: Los archivos QML reales (no los viewmodels) no fueron inspeccionados; potencialmente existen bindings que tomen decisiones implícitas.
- U-4: Comportamiento observado bajo Windows real (el repo local está en Linux); hallazgos N4 del `AGENTS.md` asumen Windows y no son replicables aquí.

---

## 15) PRIORIDAD DE IMPLEMENTACIÓN (Fase 6, si se aprueba)

### Primero (crítico, bloquea aprobación)
1. **Fix `_enforce_explicit_external_selection`** (`services/tools/tool_teach_service.py:1149–1196`):
   - Respetar `assistant_preference` cuando la `preferred_card` no está `available`: elegir la mejor alternativa dentro de la misma familia (ej. `chatgpt_installed` → `chatgpt_web_assisted`), o si no hay ninguna, bloquear con `selection_policy='explicit_assistant_blocked'` y `metadata.assistant_preference_blocked=True` en vez de dejar pasar una familia distinta.
   - Emitir guidance al usuario (vía `autonomous_evolution_service`/session metadata) cuando la preferencia queda bloqueada.
2. **Fix `IntentUnderstandingService.classify_with_schema`** (`services/adaptive/intent_understanding_service.py:461–496`):
   - Aceptar `request: InferenceRequest | None = None`; si viene, no reconstruirlo — usar el mismo request en `classify(request)`.
   - Mantener los argumentos actuales por compatibilidad con llamadores existentes.
   - Actualizar ambos llamadores en `adaptive_task_orchestrator.py:102` y `:115` para pasar el request completo.
3. **Reparar los 13 tests rotos**. Los tests describen el comportamiento correcto; no modificar los tests — arreglar el código hasta que pasen.

### Después (riesgo medio, mejora coherencia)
4. **Extraer `AssistantPreferenceResolver`** de `ControlCenterViewModel:618–673` a `services/adaptive/assistant_preference_resolver.py`, consumido por `IntentUnderstandingService` (o directamente por el orquestador vía `request.goal_parameters`) y por el VM. Evita duplicación y permite tests sin Qt.
5. **Agregar telemetría** en `_enforce_explicit_external_selection` para toda rama que no puede respetar la familia pedida (`metadata['preference_outcome']` = `'respected'|'fallback_same_family'|'blocked'`).

### Conservar intacto (no tocar en este ciclo)
- `domain/models.py` (contratos). Cualquier cambio es ruptura de contrato.
- `bootstrap.py` orden de instanciación. Funciona; no refactorizar "por limpieza".
- `WorldModelService`, `EnvironmentSelfAwarenessService`, `PortableContextService`, `OperationalSelfExaminationService` (capas cerradas P1–P4).
- `ExperimentLab`, `StrategySelector`, `AdaptiveWeightLayer` (capa cerrada P2).

### No tocar aún (aspiracional)
- Refactor del `ControlCenterViewModel` completo (5484 líneas). Sólo extraer `AssistantPreferenceResolver`; el resto queda para ciclo posterior.
- Multi-IA paralela / consenso.
- Reestructurar `data/evolution/`.

---

## 16) CONCLUSIÓN HONESTA

**¿Qué es realmente el proyecto hoy?** Un sistema local-first con un cerebro único real (`AdaptiveTaskOrchestrator`), percepción unificada (`PerceptionSnapshot`), world model vivo, aprendizaje comparativo real, auditoría amplia, contexto portable y autoexaminación funcional. Las capas P1–P4 están en su sitio. No hay arquitectura duplicada. **El núcleo existe y es coherente en estructura.**

**¿Qué tan cerca está de estar listo para aprobación?** No está listo. Tiene **3 bugs críticos verificables** que tocan el corazón operativo:
- preferencia del asistente se pierde en silencio,
- `classify_with_schema` descarta campos del request,
- 13 pruebas fallan en `main`.

Estos bugs **no requieren refactor masivo**. Son fixes quirúrgicos de entre 10 y 60 líneas por cambio. Con esos 3 fixes + extraer la decisión de asistente del VM + telemetría cuando la preferencia no puede respetarse, el sistema queda **listo para aprobación** del núcleo.

**Lo que conservar sin discusión:** todo el trabajo de P1–P4, los contratos soberanos, el wiring de `bootstrap.py`, el lab comparativo, el portable context y la autoexaminación. Son la columna vertebral del proyecto y están bien.

**Lo que se desvió y hay que corregir:** preferencia del asistente + clasificador + decisión de ruta dentro del VM.

**Lo que no se ha construido y hay que decidir:** multi-IA paralela/consenso. No es un bug; es una funcionalidad no implementada. Decidir explícitamente si entra o no en v1.5.

**Veredicto:** "casi listo, con 3 fixes puntuales y 1 decisión de alcance". El proyecto está en mejor estado de lo que un vistazo superficial sugiere, y los bugs que tiene son los que el propio usuario sospechaba. Las sospechas planteadas en el prompt se confirmaron con evidencia en código y en test rojo:

- ✅ confirmado: inconsistencias en el contrato de `IntentUnderstandingService` → Hallazgo 4.1.
- ✅ confirmado: pérdida de la preferencia explícita del asistente en flujos de tools → Hallazgo 4.2 + test rojo.
- ◐ parcialmente confirmado: "estados inconsistentes en servicios de evolución autónoma" → sólo por herencia del bug 4.2 (autonomous_evolution termina en `failed` porque el tool seleccionado es incorrecto). Una vez reparado 4.2, 6 de los 7 fallos en `test_autonomous_evolution_service.py` deberían caer.
- ✗ no confirmado: "dependencia excesiva del UI ViewModel sobre persistencia o threads" — hay hilos y hay lectura de repos, pero el esquema se inicializa antes de cualquier refresh (no hay carrera de tablas). Sí hay exceso de responsabilidad en decisiones (R-M-1).
- ✗ no confirmado: "tablas o repositorios no preparados antes de refrescos en background" — `AppDatabase.__init__` hace `CREATE TABLE IF NOT EXISTS` antes de que cualquier servicio se construya (`bootstrap.py:141`, `database.py:19`).
- ◐ parcialmente confirmado: "solapamiento entre orquestador, laboratorio, router y tool-teach" — son capas distintas sin duplicación estructural, pero la información del IntentSchema vive en 3 metadatas y la decisión de asistente vive en VM + tool_teach (R-B-1, R-M-1).

---

## Apéndice A — Evidencia de tests

Ejecución focalizada (Fase 1 diagnóstico, sin pre-cachear):
```
tests/test_intent_understanding_service.py           → PASS
tests/test_adaptive_task_orchestrator.py             → PASS (33 tests)
tests/test_tool_teach_service.py                     → 6 FAIL
tests/test_autonomous_evolution_service.py           → 7 FAIL
tests/test_world_model_service.py                    → PASS
tests/test_portable_context_service.py               → PASS
tests/test_operational_self_examination_service.py   → PASS
tests/test_task_context_assembler.py                 → PASS
tests/test_etapa2_conversation_analysis.py           → PASS
```
Total: **56 passed, 13 failed**.

Tests rojos (todos en main):
- `test_tool_teach_service_external_consultation_prefers_codex_for_bridge_lag` — esperaba `codex_installed`, obtuvo `claude_web_assisted`.
- `test_tool_teach_service_external_consultation_supports_direct_text_capture`.
- `test_tool_teach_service_external_consultation_can_fall_back_to_local_ollama_when_enabled` — esperaba `ollama_llm`, obtuvo `claude_web_assisted`.
- `test_tool_teach_service_external_consultation_rejects_unverified_codex_clipboard_capture`.
- `test_tool_teach_service_external_consultation_prefers_desktop_codex_over_learned_web_pattern` — esperaba `codex_installed`, obtuvo `chatgpt_web_assisted`.
- `test_tool_teach_service_explicit_codex_request_overrides_cross_family_selector` — esperaba `codex_installed`, obtuvo `chatgpt_web_assisted`.
- `test_autonomous_evolution_service_prepares_codex_consultation_for_bridge_lag` — esperaba `awaiting_response`, obtuvo `failed`.
- `test_autonomous_evolution_service_preview_prefers_codex_for_bridge_lag` — esperaba `codex_installed`, obtuvo `claude_web_assisted`.
- `test_autonomous_evolution_service_auto_ingests_direct_response_from_external_tool` — esperaba `ingested`, obtuvo `failed`.
- `test_autonomous_evolution_service_can_fall_back_to_local_ollama_when_external_apps_are_unavailable` — esperaba `ollama_llm`, obtuvo `claude_web_assisted`.
- `test_autonomous_evolution_service_reuses_successful_local_consultation_for_same_scope` — esperaba `ingested`, obtuvo `failed`.
- `test_autonomous_evolution_service_rejects_unverified_clipboard_captured_codex_response` — esperaba `failed`, obtuvo `ingested`.
- `test_autonomous_evolution_service_auto_ingests_codex_rollout_capture` — esperaba `codex`, obtuvo `claude`.

---

## Apéndice B — Referencias clave (file:line)

- `bootstrap.py:141` — `AppDatabase` creado antes que cualquier servicio.
- `bootstrap.py:228–240` — `WorldModelService` construido con `role_router=None`, luego (313–333) cableado al `LocalRoleRouter`.
- `bootstrap.py:528–543` — `AdaptiveTaskOrchestrator` como orquestador único.
- `bootstrap.py:608–636` — `ControlCenterViewModel` recibe 20+ dependencias (VM con superficie muy amplia).
- `domain/models.py:1714` — `TaskIntent`.
- `domain/models.py:1740` — `IntentSchema`.
- `domain/models.py:1860` — `PerceptionSnapshot`.
- `domain/models.py:2341` — `InferenceRequest`.
- `services/adaptive/adaptive_task_orchestrator.py:102,115` — llamadores de `classify_with_schema` que pierden campos.
- `services/adaptive/intent_understanding_service.py:461–496` — `classify_with_schema` reconstruye request estrecha.
- `services/tools/tool_teach_service.py:531–541` — `build_task_from_request`.
- `services/tools/tool_teach_service.py:1149–1196` — `_enforce_explicit_external_selection` silenciosa.
- `services/evolution/autonomous_evolution_service.py:47–200` — `plan_or_execute` y estados de consulta.
- `ui/viewmodels/control_center_viewmodel.py:618–673` — lógica de `_explicit_assistant_preference` que debería vivir en un servicio.
- `ui/viewmodels/control_center_viewmodel.py:4668–4701` — `_run_external_consultation` con hilo daemon.
- `infra/persistence/database.py:19–317` — esquema idempotente en `__init__`.

---

**Fin del reporte.** Esperando aprobación del usuario para pasar a Fase 6 (correcciones mínimas).
