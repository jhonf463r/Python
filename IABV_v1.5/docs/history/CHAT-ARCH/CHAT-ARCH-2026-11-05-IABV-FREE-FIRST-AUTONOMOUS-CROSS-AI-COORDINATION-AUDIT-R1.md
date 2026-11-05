# IABV — Auditoría free-first de coordinación autónoma entre IA y vigilancia tecnológica

`TASK_ID=IABV_FREE_FIRST_AUTONOMOUS_CROSS_AI_COORDINATION_AUDIT_R1_20261105`

`REPOSITORY=jhonf463r/Python`

`BASE_MAIN=56e4d8b11846a8d8f3cb8cda08efd773ec235651`

`MODE=BOUNDED_STATIC_SOURCE_AND_TEST_REVIEW`

`WRITEBACK=DOCUMENTATION_ONLY_ISOLATED_BRANCH_DRAFT_PR`

`RUNTIME=NOT_RUN`

`TESTS=NOT_RUN`

`PRODUCT_CODE_CHANGES=NONE`

---

## 1. Propósito y decisión

El objetivo del Owner no es abrir muchas pestañas ni enviar el mismo prompt a varias IA. El objetivo de producto es que **IABV sea el coordinador principal**: interprete el objetivo, seleccione recursos compatibles con el presupuesto gratuito, delegue tareas, observe resultados, contraste perspectivas, solicite aclaraciones, valide evidencias y consolide una respuesta sin convertir al Owner en mensajero entre herramientas.

La restricción económica que gobierna esta auditoría es:

`FREE_FIRST = TRUE`

`NEW_PAID_API_KEYS = NOT_ALLOWED`

`NEW_SUBSCRIPTIONS = NOT_ALLOWED`

La visión y el orden de prioridad ya están documentados: reutilizar primero capacidades locales e instaladas; después niveles gratuitos ya disponibles; luego sesiones/cuentas existentes; después proveedores/modelos locales cuando sean adecuados; y solo discutir infraestructura pagada ante una decisión nueva del Owner. Véase [objetivo laptop-native / free-first / cross-AI](./CHAT-ARCH-2026-10-03-037-laptop-native-free-first-cross-ai-objective.md) y [visión IABV como mente del portátil e intermediario de agentes](./CHAT-ARCH-2026-10-05-059-product-vision-iabv-as-laptop-mind-and-agent-intermediary.md).

**Decisión de esta auditoría:**

1. No instalar Goose, OpenHands, OpenTeam, Nanobrowser, Node.js, Ollama ni otro coordinador por ahora.
2. No crear un segundo cerebro, una segunda memoria ni otro registro universal de herramientas.
3. Reutilizar como primera opción `AdaptiveTaskOrchestrator`, `SynapticRouter`, `ToolRegistry`, `ToolTeachService`, `AutonomousEvolutionService`, `ExperimentLab`, `ToolDiscoveryService`, `ToolEvolutionMonitor`, `PlatformLearningOrchestrator` y la capa de memoria/evidencia ya existentes.
4. No automatizar la lectura o extracción de respuestas de ChatGPT Free mediante DOM, portapapeles o scripts. La ruta actual de captura automatizada de ChatGPT no es una ruta que debamos activar.
5. Priorizar una prueba de integración real del despacho multi-IA y su contrato de resultados antes de instalar o conectar nada.
6. Mantener las restricciones de `CURRENT-STATE.md`: el presente documento no autoriza runtime, dispatch, MCP, túneles, lectores protegidos, cambios de permisos ni implementación.

El resultado que buscamos no es «más agentes porque sí», sino una disminución demostrable del trabajo manual del Owner sin perder trazabilidad ni control.

## 2. Base canónica, método y autoridad

Se refrescó el repositorio remoto y se inspeccionó el `main` vivo:

- `MAIN=56e4d8b11846a8d8f3cb8cda08efd773ec235651`
- Fecha del commit observado: 2026-11-02 22:35:18 UTC.
- Mensaje: `docs(UAAL): adopt decision-complete coordination and review controls`.
- El commit observado es documental; no demuestra activación del runtime ni del puente.

La lectura normal de `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` devolvió cuerpo vacío. Se recuperó su blob exacto por SHA:

`CURRENT_STATE_BLOB=63e1b459a13e23e1012da81826dc50727b688d8c`

El bloque activo de ese blob conserva:

```text
ACTIVE_TASK=IABV_M1A_OWNER_ISSUER_MECHANISM_INPUT_GATE_R1_20261030
LANE_A=M1A_G1_ROOT_AUTHORITY_AND_PROVENANCE; BLOCKED
LANE_A_WAIT_SCOPE=TASK_LOCAL_M1A_AUTHORITY_DEPENDENCY_ONLY; NOT_PROJECT_WIDE_STOP
LANE_B=INDEPENDENT_PROGRESS; SELECT_ONLY_WHEN_CURRENT_OWNER_OBJECTIVE_AND_OWN_AUTHORIZATION_SUPPORT_A_CONCRETE_TASK
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PARALLEL_DISPATCH=NOT_AUTHORIZED
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

Esta auditoría se mantiene en el carril de progreso independiente, no reabre M1A ni modifica su router. El Owner pidió expresamente preservar este trabajo en GitHub; por ello se registra en un branch documental y un PR en borrador, sin merge ni cambios a los documentos que poseen el estado canónico.

Método aplicado:
- **UAAL-D019:** aislar la primera arista causal, no repetir rutas sin un delta material.
- **UAAL-D020:** comparar realizaciones realmente disponibles; priorizar `REUSE > COMPOSE > WIRE/REPAIR > EXTEND > NEW`; no contar preparación como progreso.
- **UAAL-D021:** revalidar fuente, revisión, procedencia y permisos; distinguir verificado, reportado, inferido, desconocido y no ejecutado.
- **Mapa de simbiosis:** los actores externos son recursos/capacidades, no órganos permanentes; la simbiosis es un bucle epistemológico, no otra mente.

`CONTROL_MASTER_DIGEST=UNAVAILABLE`: no se dispone en esta sesión de una superficie de lectura runtime autorizada para el digest vivo. No se sustituye por una instantánea histórica ni se interpreta como cola vacía.

## 3. Inventario estático de los órganos reutilizables

### 3.1 Coordinación, selección y despacho

**AdaptiveTaskOrchestrator** contiene una ruta de comparación paralela de hasta dos candidatos:

- `_PARALLEL_IA_COMPARISON_MAX_WORKERS=2`.
- `_PARALLEL_IA_COMPARISON_TIMEOUT_S=30.0`.
- `_ranked_candidates_from_synaptic()` construye candidatos desde el seleccionado y sus alternativas.
- `_parallel_ia_comparison()` crea un `ThreadPoolExecutor`, somete dos consultas a `AutonomousEvolutionService.plan_or_execute()`, registra resultados en `ExperimentLab` si está disponible y devuelve un resultado consolidado.
- `_synthesize_parallel_results()` selecciona un resultado primario por estado/completitud/confianza y añade contribuciones de algunos campos de resultados secundarios.
- `_chained_ia_consultation()` puede enviar una consulta secuencial adicional a otro asistente usando un resumen de la primera respuesta.

Fuentes:
- [AdaptiveTaskOrchestrator — comparación paralela](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L355-L492)
- [Síntesis de resultados](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L535-L618)
- [Despacho paralelo](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1315-L1433)
- [Consulta encadenada](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L922-L1008)

**Clasificación:** existe un mecanismo de cotejo de consultas externas en paralelo, no un equipo de agentes persistentes con bandejas de tareas, ciclo de vida independiente, memoria de trabajo propia y mensajería general entre ellos. La implementación actual es un pool breve de dos hilos que invoca dos consultas y consolida sus resultados. El tercer paso, cuando ocurre, es una consulta encadenada, no un worker permanente.

### 3.2 Selección de recursos y ejecución

La cadena existente contiene:

- `SynapticRouter`: ranking de candidatos según el objetivo/capacidad.
- `ToolRegistry`: catálogo y selección de `ToolCard`, con refresco de disponibilidad mediante el adaptador.
- `ToolTeachService`: genera `ToolTask`, aplica selección, sandbox, aprobación, ejecución, validación, rollback y persistencia.
- `ToolOperationalExecutor`: conecta una sesión adaptativa con `ToolTeachService`.
- `AutonomousEvolutionService`: prepara y ejecuta consultas externas, ingiere respuestas y conserva estados de consulta, trazas y resultados.
- `ExperimentLab`: conserva corridas y comparaciones para realimentar selección/evolución.

Fuentes:
- [ToolRegistry](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_registry.py)
- [ToolTeachService — construcción de tareas](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py#L537-L667)
- [ToolTeachService — sandbox, aprobación, ejecución y validación](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py#L749-L932)
- [AutonomousEvolutionService — planificar/ejecutar y registrar consulta](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/autonomous_evolution_service.py#L77-L278)
- [ToolOperationalExecutor](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_operational_executor.py)
- [Modelo ToolTask](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/domain/models.py#L1299-L1317)

El modelo `ToolTask` tiene `tool_id`, `objective`, `actions`, `execution_scope`, aprobaciones, referencias de sesión/ejecución y `metadata`; no tiene un campo de primer nivel `required_capability_id`. El enum `ToolCapability` existe en el dominio, pero no está enlazado como campo obligatorio del contrato de `ToolTask` en la definición examinada. Esto mantiene vigente como problema de diseño a revisar el puente entre demanda operativa exacta y realización seleccionada; no se propone crear otro registro de capacidades.

### 3.3 Descubrimiento, evolución y aprendizaje de plataformas

**ToolDiscoveryService**:
- Lee recomendaciones y corridas de `ExperimentLab`.
- Lee las `ToolCard` disponibles en `ToolRegistry`.
- Compara las realizaciones ya registradas contra una línea base.
- Calcula señales/propuestas y las reconcilia con el registro de decisiones de validación.

No realiza por sí solo búsquedas externas de software, extensiones, releases, repositorios, licencias o vulnerabilidades.

**ToolEvolutionMonitor**:
- Agrupa resultados históricos por dominio/ruta/asistente/configuración.
- Calcula perfiles y degradación mediante `AdaptiveWeightLayer`.
- Produce propuestas de evolución y reconcilia decisiones previas.
- Depende de corridas y señales ya incorporadas; no es un rastreador general de Internet.

**PlatformLearningOrchestrator**:
- Aprende perfiles de plataformas Browser/UI, REST/gRPC, CLI y servicios de fondo mediante percepción → plan → acción → verificación → ajuste → persistencia.
- Alimenta órganos existentes como `ExperimentLab`, `SelfTeachOrchestrator` y OSES.
- No sustituye al coordinador ni demuestra una vigilancia continua de proyectos OSS.

Fuentes:
- [ToolDiscoveryService](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_discovery_service.py#L59-L153)
- [Catálogo disponible consultado por ToolDiscoveryService](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_discovery_service.py#L216-L257)
- [Señales construidas desde ToolCard/ExperimentLab](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_discovery_service.py#L257-L360)
- [ToolEvolutionMonitor](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/tool_evolution_monitor.py#L61-L191)
- [PlatformLearningOrchestrator — alcance declarado](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/platform_learning_orchestrator.py#L1-L25)

**Resultado:** hay descubrimiento/evaluación interna de realizaciones ya catalogadas y aprendizaje de plataformas usadas. No se encontró en el árbol de `main` un servicio dedicado de vigilancia tecnológica externa (Technology Watch/Radar) que busque continuamente nuevos proyectos y los califique con evidencia independiente. No se justifica crear un nuevo órgano hasta diseñar cómo alimentar los órganos existentes con fuentes externas versionadas y comprobables.

### 3.4 Proveedores gratuitos/locales y recursos existentes

El bootstrap construye un `OllamaExpertProvider`, un `OpenAICompatLocalProvider` para visión, un adaptador Playwright, un adaptador Ollama y adaptadores externos. También conecta `ToolDiscoveryService`, `ToolEvolutionMonitor`, `AutonomousEvolutionService`, `AdaptiveTaskOrchestrator` y `ToolOperationalExecutor`.

Fuentes:
- [Bootstrap — providers y adapters](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py#L616-L659)
- [Bootstrap — ToolDiscoveryService](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py#L802-L837)
- [Bootstrap — ToolEvolutionMonitor](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py#L1036-L1043)
- [Bootstrap — AutonomousEvolutionService y AdaptiveTaskOrchestrator](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py#L1447-L1505)
- [OllamaExpertProvider](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/providers/ollama_expert_provider.py)

La tarjeta estática de `ollama_llm` registra `available=false` y `validation_status=unvalidated`. Por tanto, el código del proveedor existe, pero no se puede afirmar que Ollama esté instalado, activo, con modelo cargado ni que el equipo tenga memoria suficiente en este momento. Las mediciones históricas del portátil (~16 GB RAM y episodios de presión) son antecedentes, no telemetría actual. No se realizó consulta local ni se intentó iniciar/cargar un modelo.

## 4. Hallazgo prioritario: la prueba paralela no demuestra dos proveedores reales distintos

El código crea un payload distinto para cada candidato y añade `metadata.assistant_kind`. Sin embargo, `_run_single_ia_consultation()` llama a `AutonomousEvolutionService.plan_or_execute()` con el mismo `decision_context` compartido por ambas tareas.

La selección real de `AutonomousEvolutionService` tiene dos fuentes:
- `_assessment_from_decision_context()` lee `governance.should_consult` y `governance.assistant_kind`; si el objeto no contiene `governance`, devuelve un dict vacío.
- `_assess()` decide a partir de diagnóstico, guidance, incidentes y auditoría; el fragmento examinado no toma `adaptive_payload.metadata.assistant_kind` como identidad obligatoria del candidato.

Además, el `TaskContextAssembler` crea inicialmente el `DecisionContext` con `governance={}`, y el cotejo paralelo se ejecuta en `_handle_request_body` antes de crear la sesión y antes de que el flujo llegue a la decisión posterior. Por tanto, el contrato entre el candidato de Synaptic y el asistente que acaba seleccionado por la ruta real no está cerrado en la fuente examinada.

Fuentes:
- [Payload de candidato y llamada real a plan_or_execute](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L413-L492)
- [DecisionContext inicial con governance vacío](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py#L130-L220)
- [Uso de DecisionContext y selección de AutonomousEvolutionService](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/autonomous_evolution_service.py#L702-L718)
- [Fallback de selección en _assess](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/autonomous_evolution_service.py#L932-L972)
- [Lugar del cotejo en handle_request](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1485-L1540)

La prueba `test_parallel_ia_comparison.py` utiliza un `_RecordingEvolutionService` simulado cuyo `plan_or_execute()` lee directamente `adaptive_payload.metadata.assistant_kind`. El test acredita el pool y la lógica del orquestador frente a ese sustituto, pero no prueba que el servicio real cree dos `ToolTask` con dos `actual_assistant_kind` diferentes, ni que ambos adapters ejecuten rutas distintas.

Fuentes:
- [Stub que toma assistant_kind del payload](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/tests/test_parallel_ia_comparison.py#L110-L170)
- [Aserción de dos candidatos en el test](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/tests/test_parallel_ia_comparison.py#L217-L232)

**Clasificación del hallazgo:**

```text
PARALLEL_POOL_IMPLEMENTED=YES_STATIC
PARALLEL_CANDIDATE_PAYLOAD=YES_STATIC
REAL_SERVICE_CANDIDATE_BINDING=NOT_PROVEN
DISTINCT_REAL_TOOL_TASKS=NOT_PROVEN
DISTINCT_REAL_ADAPTER_EXECUTIONS=NOT_PROVEN
PERSISTENT_WORKER_LIFECYCLE=NOT_PRESENT_IN_REVIEWED_PATH
```

No se declara que el runtime haya enviado dos veces al mismo asistente: eso no se observó. Sí se declara que la ruta de decisión examinada no demuestra el enlace candidato → proveedor real, y que el test actual no detecta esa posible divergencia.

**Primera prueba de integración futura, si se autoriza:** usar el servicio real y adapters interceptados; asignar dos candidatos diferentes; comprobar que cada candidato produce un `ToolTask` con proveedor solicitado/real correcto, `tool_id`, `config_signature`, `task_id` y `result_id` correlacionados; comprobar que una discrepancia o fallback queda marcada y no se cuenta como comparación de dos proveedores distintos. No llamar ChatGPT ni realizar transporte real en esa prueba.

## 5. Otros bloqueos para autonomía real

### 5.1 Aprobación humana

`ToolApprovalPolicy` exige aprobación cuando la tarjeta requiere aprobación, admite escritura, el alcance es write/destructive o una acción es destructiva. Las tarjetas actuales de ChatGPT indican `requires_human_approval=true`. A su vez, `AutonomousEvolutionService.plan_or_execute()` llama a `execute_external_consultation(... approved=False ...)`; tras sandbox, la tarea debe quedar en `waiting_approval` cuando la política exige aprobación. Por tanto, no debe describirse ese canal como delegado sin intervención.

Fuentes:
- [ToolApprovalPolicy](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_approval_policy.py)
- [ToolTeachService: aprobación antes de ejecutar adapter](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py#L749-L850)
- [ChatGPT web ToolCard](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/data/tool_teaching/cards/chatgpt_web_assisted.json)

### 5.2 Captura automatizada de ChatGPT

La tarjeta `chatgpt_web_assisted` especifica:
- `response_capture_mode=dom_capture`;
- `background_capture_mode=browser_dom`;
- selectores de entrada y de respuesta del DOM;
- captura headless y sesión aislada;
- `requires_manual_pasteback=false`.

El servidor MCP expone `chatgpt_web_capture`, que llama al capturador DOM de Playwright. El adaptador de asistente externo también tiene rutas de captura DOM/portapapeles.

Fuentes:
- [ChatGPT web ToolCard](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/data/tool_teaching/cards/chatgpt_web_assisted.json)
- [MCP chatgpt_web_capture](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/infra/mcp/server.py#L830-L885)
- [ToolAdapter: DOM/clipboard capture](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py#L598-L760)

Los Términos de Uso de OpenAI, efectivos desde el 1 de enero de 2026, prohíben extraer datos u Output de los servicios de manera automática o programática y también saltarse límites o medidas de protección. La captura programática de respuestas de ChatGPT mediante DOM/portapapeles cae en el tipo de actividad que no debemos utilizar como transporte de coordinación. Fuente oficial: https://openai.com/policies/terms-of-use/

```text
CHATGPT_FREE_MANUAL_INTERACTION=AVAILABLE_AS_HUMAN_MEDIATED_CHANNEL
CHATGPT_DOM_OUTPUT_CAPTURE=DO_NOT_ENABLE
CHATGPT_CLIPBOARD_OUTPUT_CAPTURE=DO_NOT_ENABLE
CHATGPT_AUTOMATED_SESSION_DISPATCH=NOT_AN_ADMISSIBLE_ROUTE_FOR_THIS_DESIGN
```

Esta restricción no impide que el Owner utilice ChatGPT Free normalmente ni que IABV prepare un paquete de consulta para que el Owner lo entregue y devuelva manualmente. Esa modalidad corresponde a la colaboración asistida, no a autonomía completa.

### 5.3 Disponibilidad obsoleta/no validada

Las tarjetas fuente reflejan una instantánea estática de abril de 2026:
- `chatgpt_web_assisted`: `available=true`, pero `validation_status=unvalidated` y `requires_human_approval=true`.
- `chatgpt_installed`: `available=false` y `validation_status=unvalidated`.
- `ollama_llm`: `available=false` y `validation_status=unvalidated`.

El `ToolRegistry.refresh_card()` puede comprobar disponibilidad contra un adapter, pero este análisis no ejecutó ese refresco en la laptop. Por tanto, los valores no representan disponibilidad actual en Windows ni prueban login, cuota, modelo cargado o respuesta operativa.

### 5.4 Presión de recursos y trabajos de fondo

El orquestador detecta señales HIGH y CRITICAL en `EnvironmentSelfModel`. Sin embargo, la rama principal que decide el cotejo paralelo omite el cotejo solo cuando `resource_pressure.critical` es verdadero; el comentario menciona que HIGH debería limitar candidatos, pero el fragmento de ejecución conserva el top-two. Se necesita un test de política para presión HIGH antes de confiar en la reducción de carga.

Fuentes:
- [Detección de presión de recursos](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L619-L651)
- [Gate de cotejo ante presión CRITICAL](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py#L1515-L1540)

El bootstrap contiene una ruta diferida que puede ejecutar `auto_fix_missing_tools()` para herramientas pip ausentes. También se integra `ResourceMetacognitionService`, cuyo camino `execute_liberation(mode='auto')` puede cerrar procesos y cargar/descargar modelos Ollama. La presencia del código no prueba que estas rutas se hayan ejecutado en la laptop. Debido a los antecedentes históricos de RAM y al espacio de disco comunicado anteriormente, ninguna instalación automática, cierre de procesos, pull de modelo o escaneo amplio debe utilizarse en esta fase sin autorización puntual y medición de recursos actual.

Fuentes:
- [Bootstrap: escaneo/metacognición diferidos e instalación automática](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py#L1803-L1881)
- [ResourceMetacognitionService: plan y ejecución de liberación](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/evolution/resource_metacognition_service.py#L357-L590)

## 6. Qué significa realmente “vigilancia tecnológica” en IABV

El carril de vigilancia solicitado debe responder de forma periódica y basada en evidencia:

- ¿Apareció una herramienta o proyecto OSS nuevo que resuelva una capacidad requerida?
- ¿Está mantenido y tiene releases recientes?
- ¿Qué licencia tiene y permite el uso previsto?
- ¿Qué dependencias, permisos, red, credenciales o datos necesita?
- ¿Funciona en Windows y con el presupuesto de hardware disponible?
- ¿Requiere API keys, billing, suscripción o un plan que el Owner no tiene?
- ¿Puede integrarse mediante una capacidad ya existente (browser, CLI, API, MCP, provider local)?
- ¿Qué evidencia independiente confirma su funcionamiento?
- ¿Qué órgano existente debería consumir la señal?

El diseño recomendado es una **fuente externa de señales que alimente los órganos existentes**, no un nuevo cerebro:
1. La investigación web/feeds/consulta GitHub produce candidatos con URL, fecha de observación, release/tag, licencia, actividad, dependencias, requisitos y evidencia.
2. La señal se normaliza a una ficha provisional y se compara con `ToolRegistry` y capacidades/demanda de IABV.
3. `ToolDiscoveryService` genera propuestas desde el catálogo y las necesidades registradas.
4. `ExperimentLab` y `ToolEvolutionMonitor` registran y evalúan resultados de pruebas controladas.
5. `PlatformLearningOrchestrator` puede aprender el procedimiento de uso de una plataforma concreta después de que su uso sea autorizado.
6. El Owner aprueba cualquier incorporación que implique instalar, autenticarse, ejecutar código, habilitar red nueva o cambiar permisos.

**No se ha implementado ni activado aquí una vigilancia periódica.** El presente informe únicamente identifica su lugar arquitectónico y contrato de entrada.

Cada candidato debería quedar clasificado como:
- `DISCOVERED`: encontrado en una fuente externa, aún sin validar.
- `SCREENED_FREE_FIRST`: precio/licencia y requisitos contrastados.
- `STATIC_REVIEWED`: código, permisos, dependencias y riesgos inspeccionados.
- `LOCALLY_AVAILABLE`: presencia local comprobada con observación actual.
- `VALIDATED`: prueba autorizada con resultado reproducible.
- `REJECTED` o `DEFERRED`: decisión y motivo conservados.

No promover una herramienta a `VALIDATED` por README, estrellas, una demo o una promesa de proveedor.

## 7. Ruta gratuita realista para avanzar

| Recurso | Papel admisible | Límite actual |
|---|---|---|
| Capacidades de IABV ya integradas | Coordinación, selección, historial y ejecución local | Composición end-to-end no demostrada |
| Ollama local | Proveedor potencial sin API pagada | Tarjeta estática no validada; estado y RAM actuales desconocidos |
| Playwright | Navegar e inspeccionar sitios web y aplicaciones permitidas | No extraer Output de ChatGPT |
| Codex incluido en Free | Recurso de desarrollo que el Owner ya utiliza | Acceso de prueba limitado; no equivale a chats normales de ChatGPT |
| ChatGPT Free | Segunda perspectiva de razonamiento con intervención humana | No automatizar envío/captura programática de Output |
| GitHub API/conector autorizado | Leer estado, historial y documentación del repo | No es un runtime local ni un bus de agentes automático |

Los Términos de OpenAI son la razón para excluir el capturador automático de ChatGPT, no una razón para abandonar el objetivo general. La autonomía gratuita sí puede progresar usando el coordinador de IABV, proveedores locales cuando estén disponibles y recursos gratuitos oficialmente admitidos. La ruta de ChatGPT Free queda manual hasta que exista un mecanismo oficial y permitido que cubra este caso.

## 8. Arquitectura objetivo sin duplicar órganos

```text
OBJETIVO DEL OWNER
        |
        v
CURRENT-STATE + UAAL-D019/D020/D021
        |
        v
ADAPTIVE TASK ORCHESTRATOR
        |
        +--> capability demand / task contract
        |
        v
SYNAPTIC ROUTER + TOOL REGISTRY
        |
        +--> LOCAL PROVIDER (si disponible y dentro de RAM)
        +--> CODEX FREE (tareas de desarrollo compatibles)
        +--> PLAYWRIGHT (sitios/apps permitidos)
        +--> CHATGPT FREE (paquete manual; sin DOM/clipboard extraction)
        +--> REST/MCP (solo recursos y gates autorizados)
        |
        v
TASK / RESULT / TRACE CORRELATION
        |
        v
INDEPENDENT VALIDATION + EXPERIMENT LAB
        |
        v
TOOL DISCOVERY / TOOL EVOLUTION / PLATFORM LEARNING
        |
        v
VERIFIED KNOWLEDGE + METHOD + ROUTING DELTA
        |
        v
LATER NON-IDENTICAL REUSE
```

No crear `IABV2Coordinator`, un segundo ToolRegistry o un store alternativo salvo que una prueba demuestre un hueco que no se puede componer con los órganos actuales.

## 9. Orden de trabajo recomendado y puertas de aceptación

### G0 — Preservación documental (completada en este branch)

Conservar la auditoría, las fuentes exactas, las limitaciones y la siguiente frontera de evidencia. La rama y el PR son documentales; el merge queda pendiente de revisión del Owner.

### G1 — Contrato de candidato → proveedor real (siguiente prioridad técnica)

Diseñar una prueba focalizada de integración con `AutonomousEvolutionService` real y transporte/adapters interceptados. Debe probar dos tareas distintas, no dos llamadas a un stub:

- candidatos distintos llegan a rutas/adapters distintos;
- `requested_assistant_kind` coincide con `actual_assistant_kind`;
- cada tarea tiene IDs y configuración correlacionados;
- si el selector no puede respetar un candidato, el resultado queda etiquetado como fallback/bloqueado y no se cuenta como cotejo independiente;
- la prueba no usa ChatGPT web ni captura Output;
- timeout/cancelación no deja ejecuciones fantasma sin recibo;
- se registra la razón de cada fallo.

No modificar código ni ejecutar esta prueba hasta autorización separada.

### G2 — Gate de aprobación y gobernanza

Comprobar en una prueba real de servicio:
- `requires_human_approval`, `approved=False`, sandbox y estado `waiting_approval`;
- diferencia entre `launch_dry_run` y aprobación;
- `PARALLEL_DISPATCH=NOT_AUTHORIZED` del router canónico prevalece sobre el default local `allow_parallel_comparison=True`;
- ninguna tarjeta ChatGPT dispara DOM/clipboard output capture.

### G3 — Presión de recursos

Agregar a la especificación de aceptación:
- presión CRITICAL: no lanzar cotejo;
- presión HIGH: reducir o suprimir concurrencia conforme a política explícita;
- presupuesto de RAM por proveedor y límite de workers;
- nunca cerrar procesos ni descargar modelos automáticamente durante una prueba de coordinación;
- capturar RAM antes/después y proceso/modelo asociados, no usar datos históricos como estado actual.

### G4 — Vigilancia tecnológica externa alimentando órganos existentes

Definir fuentes, frecuencia, metadatos, licencia, precio, mantenimiento, seguridad, plataforma, consumo de RAM y prueba de compatibilidad. Ingerir señales en el mecanismo de descubrimiento actual, sin crear otra memoria.

### G5 — Prueba de aceptación end-to-end, autorizada separadamente

Solo después de G1–G4 y de reconciliar permisos:
- una tarea del Owner;
- dos recursos realmente distintos;
- ejecución paralela limitada;
- evidencia verificable de cada resultado;
- un revisor independiente;
- consolidación y reconciliación;
- persistencia del delta;
- posterior reutilización en una tarea no idéntica.

No declarar autonomía porque dos respuestas se generaron; demostrar que IABV seleccionó, ejecutó, capturó, verificó y usó el resultado en su siguiente decisión.

## 10. Matriz de evidencia de esta auditoría

| Afirmación | Clasificación | Resultado |
|---|---|---|
| Orquestador paralelo de hasta 2 hilos / 30 s | `VERIFIED_STATIC` | Presente en fuente |
| Síntesis/registro de resultados | `VERIFIED_STATIC` | Presente en fuente |
| Dos asistentes distintos en producción | `NOT_PROVEN` | Contrato candidato→proveedor no cerrado |
| Prueba unitaria con dos proveedores distintos | `VERIFIED_STATIC` | Stub, no servicio real |
| Delegación persistente con workers independientes | `NOT_PROVEN` | No demostrada en ruta revisada |
| Discovery interno desde ToolRegistry/ExperimentLab | `VERIFIED_STATIC` | Presente |
| Radar externo OSS continuo | `NOT_FOUND_IN_REVIEWED_TREE` | No identificado |
| Captura automática de ChatGPT por DOM/clipboard | `VERIFIED_STATIC` | Presente en tarjetas/adapters |
| Uso permitido de captura automática de ChatGPT Output | `EXCLUDED_BY_TERMS` | No activar |
| Ollama instalado y operativo en laptop | `UNKNOWN` | No se consultó runtime |
| Memoria RAM actual libre | `UNKNOWN` | Solo existen antecedentes históricos |
| ControlMasterDigest vivo | `UNAVAILABLE` | Sin superficie autorizada disponible |
| Runtime/bridge/MCP/dispatch actual | `NOT_RUN` | Respetado el router canónico |

## 11. Alcance ejecutado y no ejecutado

**Ejecutado:**
- refresh de `main`;
- recuperación del blob exacto de `CURRENT-STATE.md`;
- inspección estática de los órganos, adaptadores, providers, tarjetas, bootstrap y pruebas focalizadas indicadas;
- contraste de términos actuales de OpenAI;
- reconciliación con visión free-first y UAAL-D019/D020/D021;
- preparación de este documento.

**No ejecutado:**
- ningún test, build o runtime;
- ningún arranque de IABV, Ollama o MCP;
- ninguna captura de ChatGPT, clipboard o DOM;
- ninguna instalación o pull de modelos;
- ninguna lectura de secretos o credenciales;
- ninguna modificación del producto/código/configuración;
- ningún cambio de permisos, tunnel o MCP allowlist;
- ningún dispatch paralelo;
- ningún merge.

Estados que permanecen inalterados:

```text
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PARALLEL_DISPATCH=NOT_AUTHORIZED
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```

## 12. Siguiente acción

`NEXT_ACTION=PREPARE_A_SEPARATE_OWNER_AUTHORIZED_G1_REAL_SERVICE_CANDIDATE_BINDING_INTEGRATION_TEST_DESIGN`

La siguiente tarea útil no es instalar otro producto. Es fijar el test de integración que pueda demostrar o falsificar la primera arista abierta: que dos candidatos elegidos por Synaptic se conviertan en dos tareas reales para dos recursos diferentes, manteniendo gobernanza, límites gratuitos y recibos independientes.

No iniciar implementación, runtime ni pruebas hasta una autorización separada y la reconciliación de `CURRENT-STATE.md`.

---

## Fuentes técnicas principales

- [CURRENT-STATE.md (live path; body recovered from exact blob SHA 63e1b459a13e23e1012da81826dc50727b688d8c)](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md)
- [AGENTS.md — continuidad, D019/D020/D021 y Control Master](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/AGENTS.md#L14-L35)
- [Free-first / laptop-native objective](./CHAT-ARCH-2026-10-03-037-laptop-native-free-first-cross-ai-objective.md)
- [IABV as laptop mind / agent intermediary](./CHAT-ARCH-2026-10-05-059-product-vision-iabv-as-laptop-mind-and-agent-intermediary.md)
- [Symbiosis cumulative developmental control loop](./CHAT-ARCH-2026-10-08-148-symbiosis-cumulative-developmental-control-loop.md)
- [UAAL-D020 — progress utility and strategy switching](./CHAT-ARCH-2026-10-28-UAAL-D020-VERIFIED-PROGRESS-UTILITY-STRATEGY-SWITCH.md)
- [OpenAI Terms of Use — effective 2026-01-01](https://openai.com/policies/terms-of-use/)\n- [Codex pricing — Free has limited trial access](https://chatgpt.com/codex/pricing/)
