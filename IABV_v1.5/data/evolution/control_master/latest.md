# IABV v1.5 - Control Maestro

Generado: 2026-06-16T02:52:37.871985+00:00
Version: control_master.v1

## Vision actual
IABV v1.5 local-first con Control Maestro vivo: ControlMasterDigest como unica fuente compacta para que cualquier IA (Codex, ChatGPT, Devin, Claude) arranque sincronica sin pegar historial. Super sincronia = lectura automatica al entrar + escritura estructurada al cerrar cada sesion.

## Objetivos
- Activos: 29
- Completados: 50
- Pausados: 0
- Descartados: 0

## Reglas globales
- [irrevocable] **Si algo no puede confirmarse, marcar `UNRESOLVED`** (active)
  - refs: AGENTS.md#si-algo-no-puede-confirmarse-marcar-unresolved
- [strict] **ventanas abiertas reales y foco via Win32** (active)
  - refs: AGENTS.md#ventanas-abiertas-reales-y-foco-via-win32
- [strict] **preflight de consulta externa bloqueado por permiso antes de actuar** (active)
  - refs: AGENTS.md#preflight-de-consulta-externa-bloqueado-por-permiso-antes-de-actuar
- [strict] **se consulta antes de rutas externas** (active)
  - refs: AGENTS.md#se-consulta-antes-de-rutas-externas
- [strict] **el contexto portable se propaga por `TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `EvolutionCenterViewModel`** (active)
  - refs: AGENTS.md#el-contexto-portable-se-propaga-por-taskcontextassembler-adaptivetaskorchestrator-y-evolutioncenterviewmodel
- [irrevocable] **No hacer refactor masivo sin aprobacion explicita** (active)
  - refs: AGENTS.md#no-hacer-refactor-masivo-sin-aprobacion-explicita
- [irrevocable] **No fingir observacion que no existe** (active)
  - refs: AGENTS.md#no-fingir-observacion-que-no-existe
- [strict] **no asumas que el permiso existe** (active)
  - refs: AGENTS.md#no-asumas-que-el-permiso-existe
- [irrevocable] **Si una ruta no es viable en el estado actual, bloquear antes de intentar** (active)
  - refs: AGENTS.md#si-una-ruta-no-es-viable-en-el-estado-actual-bloquear-antes-de-intentar
- [irrevocable] **No convertir un ViewModel en decisor de rutas** (active)
  - refs: AGENTS.md#no-convertir-un-viewmodel-en-decisor-de-rutas
- [strict] **aprendizaje acumulado** (active)
  - refs: AGENTS.md#aprendizaje-acumulado
- [strict] **hilo activo de Codex via `%USERPROFILE%\\.codex\\state_5.sqlite`** (active)
  - refs: AGENTS.md#hilo-activo-de-codex-via-userprofilecodexstate5sqlite
- [strict] **autoconciencia del sistema** (active)
  - refs: AGENTS.md#autoconciencia-del-sistema
- [irrevocable] **No reemplazar `EnvironmentSelfModel`, `WorldModelSnapshot` o `UniversalPerceptionSignal`; se complementan** (active)
  - refs: AGENTS.md#no-reemplazar-environmentselfmodel-worldmodelsnapshot-o-universalperceptionsignal-se-complementan
- [strict] **el sistema aprende por evidencia, no por costumbre** (active)
  - refs: AGENTS.md#el-sistema-aprende-por-evidencia-no-por-costumbre
- [strict] **se elimino refresh redundante de autoexaminacion en `EvolutionCenterViewModel`** (active)
  - refs: AGENTS.md#se-elimino-refresh-redundante-de-autoexaminacion-en-evolutioncenterviewmodel
- [strict] **no dispares autonomia ni consulta externa** (active)
  - refs: AGENTS.md#no-dispares-autonomia-ni-consulta-externa
- [irrevocable] **El sandbox debe seguir aislado del sistema vivo** (active)
  - refs: AGENTS.md#el-sandbox-debe-seguir-aislado-del-sistema-vivo
- [strict] **no declares la herramienta disponible si no pudiste verificarla** (active)
  - refs: AGENTS.md#no-declares-la-herramienta-disponible-si-no-pudiste-verificarla
- [strict] **tambien revisa si sus ajustes previos funcionaron o no** (active)
  - refs: AGENTS.md#tambien-revisa-si-sus-ajustes-previos-funcionaron-o-no
- [strict] **`TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `AutonomyGovernancePolicy` consumen `world_model`** (active)
  - refs: AGENTS.md#taskcontextassembler-adaptivetaskorchestrator-y-autonomygovernancepolicy-consumen-worldmodel
- [strict] **`OperationalSelfExaminationService` detecta patrones, riesgos y ajustes recomendados** (active)
  - refs: AGENTS.md#operationalselfexaminationservice-detecta-patrones-riesgos-y-ajustes-recomendados
- [strict] **sus hallazgos alimentan el contexto portable** (active)
  - refs: AGENTS.md#sus-hallazgos-alimentan-el-contexto-portable
- [strict] **`WorldModelService` es la fuente viva de ventanas, foco, herramientas, red, procesos y bloqueos** (active)
  - refs: AGENTS.md#worldmodelservice-es-la-fuente-viva-de-ventanas-foco-herramientas-red-procesos-y-bloqueos
- [strict] **estado vivo del sistema** (active)
  - refs: AGENTS.md#estado-vivo-del-sistema
- [strict] **la ejecucion normal registra resultados reales** (active)
  - refs: AGENTS.md#la-ejecucion-normal-registra-resultados-reales
- [strict] **la UI lo lee; no lo modifica** (active)
  - refs: AGENTS.md#la-ui-lo-lee-no-lo-modifica
- [irrevocable] **No duplicar `PerceptionSnapshot`** (active)
  - refs: AGENTS.md#no-duplicar-perceptionsnapshot
- [strict] **autoexaminacion operativa** (active)
  - refs: AGENTS.md#autoexaminacion-operativa
- [strict] **usa `world_model`, `environment_self_model`, `ExperimentLab`, `PortableContextService` y `OperationalSelfExaminationService`** (active)
  - refs: AGENTS.md#usa-worldmodel-environmentselfmodel-experimentlab-portablecontextservice-y-operationalselfexaminationservice
- [strict] **el estado vivo del hilo de Codex prevalece sobre historial stale** (active)
  - refs: AGENTS.md#el-estado-vivo-del-hilo-de-codex-prevalece-sobre-historial-stale
- [strict] **`ExperimentLab`, `StrategySelector` y `AdaptiveWeightLayer` influyen decisiones futuras** (active)
  - refs: AGENTS.md#experimentlab-strategyselector-y-adaptiveweightlayer-influyen-decisiones-futuras
- [strict] **responde por la via humana local** (active)
  - refs: AGENTS.md#responde-por-la-via-humana-local
- [strict] **no existe una memoria paralela** (active)
  - refs: AGENTS.md#no-existe-una-memoria-paralela
- [strict] **`PortableContextService` genera paquete portable desde estado vivo y aprendizaje persistido** (active)
  - refs: AGENTS.md#portablecontextservice-genera-paquete-portable-desde-estado-vivo-y-aprendizaje-persistido
- [strict] **pide permiso explicito al usuario** (active)
  - refs: AGENTS.md#pide-permiso-explicito-al-usuario
- [irrevocable] **No crear otro cerebro ni otro orquestador** (active)
  - refs: AGENTS.md#no-crear-otro-cerebro-ni-otro-orquestador

## Backlog tecnico
- Ya existe un patron equivalente Decision: continue_local. Confianza 0.96.
- Sin hallazgos. Decision: continue_local. Confianza 0.66.

## Decisiones recientes
- [implemented] Implementacion de _decide_launch_strategy en ToolAdapter: razonamiento antes de lanzar herramienta externa. Consulta WorldModel para ventanas existentes del asistente. Consulta decision_audit_trail para historial de fallas. Cambia a herramienta alternativa tras >= 3 fallas seguidas. Resultado de prueba: Estrategia=launch_new, Razon=sin historial de fallas ni ventana previa (2026-06-16T02:52:02.893148+00:00)
  - razon: ChatGPT falla con browser_security_verification desde 2026-05-09 porque headless+nuevo lanzamiento es detectado como bot. chatgpt_installed (desktop app) nunca intentado. Sin memoria de sesion, el programa repite el mismo error sin aprender.
- [accepted] Implementado visible_account_state_requires_user_permission: Creado AccountVisibilityService en services/account_visibility_service.py. El servicio gestiona la visibilidad del estado de cuentas al usuario y solicita permisos cuando es necesario para acceder a información sensible. Incluye métodos para request_permission, grant_permission, revoke_permission, get_visible_account_state y get_permissions_summary. Esto resuelve el UNRESOLVED de visible_account_state_requires_user_permission. (2026-06-14T21:02:51.801096+00:00)
- [accepted] Integración de quota tracker: El sistema de quota tracker existe en account_resource_scanner.py con funcionalidad completa (record_message_sent, get_all_quota_status, best_account_for_tool, governed_quota_rotation). Sin embargo, no está integrado en el flujo de trabajo actual - no hay llamadas a record_message_sent() en tool_adapters.py ni en otros puntos donde se envían mensajes a herramientas externas. El sistema detecta problemas de quota en _build_worker_telemetry pero no los registra. Integración completa requiere agregar llamadas a record_message_sent() después de cada mensaje enviado a ChatGPT/Claude/Codex y usar governed_quota_rotation() para selección de cuentas. (2026-06-14T21:01:11.545598+00:00)
- [accepted] Restaurado filtro permission_required en world_model_service.py: Agregado filtro en _permission_gates que omite gates cuando permission_granted es true. Esto restaura el comportamiento anterior que evita falsos positivos de permisos ya concedidos en el digest de gobernanza. (2026-06-14T20:57:20.085433+00:00)
- [accepted] Restaurada detección de procesos de navegador en world_model_service.py: Agregado _BROWSER_PROCESS_PATTERN con patrones de navegadores (chrome, firefox, brave, opera, vivaldi). Implementado _detect_browser_processes() usando PowerShell Get-Process con fallback a tasklist. Implementado _identify_browser_type() para identificar tipo de navegador. Integrado en _background_processes() cuando full=True. Esto restaura la capacidad eliminada de ~110 líneas. (2026-06-14T20:55:46.744688+00:00)
- [accepted] Investigado visible_account_state_requires_user_permission: No se encontraron referencias a visible_account_state en el código actual. Este UNRESOLVED indica que el estado visible de cuentas requiere permiso de usuario, pero no hay implementación específica en el código. Probablemente este problema está relacionado con la necesidad de mostrar información de cuentas al usuario y solicitar permiso para acceder a ellas, pero no hay código que implemente esta funcionalidad actualmente. (2026-06-14T20:46:34.146096+00:00)
- [accepted] Investigado quota_never_tracked - cuota real desconocida: Confirmado que el sistema de quota tracker existe en account_resource_scanner.py con funcionalidad completa (líneas 449-699). Incluye _FREE_TIER_LIMITS para chatgpt/claude/codex, record_message_sent(), get_all_quota_status(), best_account_for_tool(), governed_quota_rotation(). El problema es que el sistema existe pero no está siendo utilizado correctamente o no está integrado con el resto del sistema. Las funciones de tracking requieren llamadas explícitas a record_message_sent() que probablemente no se están haciendo, causando que las cuotas reales sean desconocidas. (2026-06-14T20:45:47.715268+00:00)
- [accepted] Verificado cambio de filtrado de blockers permission_required en world_model_service.py: Confirmado que el filtro que omitía (continue) cuando permission_granted era true ya no existe. El código actual en _permission_gates (línea 1121) establece status='concedido' si tool.permission_state == 'concedido', pero en _block_records (líneas 1170-1186) no hay filtro que omita gates cuando permission_granted es true. Esto podría causar que aparezcan blockers de permiso ya concedido en el digest de gobernanza. El bloque de filtrado anterior debe restaurarse si es necesario para evitar falsos positivos. (2026-06-14T20:44:25.781691+00:00)
- [accepted] Verificada eliminación de detección de procesos de navegador en world_model_service.py: Confirmado que se eliminaron ~110 líneas de detección de procesos de navegador (PowerShell Get-Process + fallback tasklist + _BROWSER_PROCESS_PATTERN). La capacidad se perdió y no fue reemplazada. El código actual usa Get-CimInstance Win32_PerfFormattedData_PerfProc_Process en _background_processes pero sin detección específica de procesos de navegador. Esta funcionalidad debe restaurarse si es crítica para la detección de herramientas LLM web UI. (2026-06-14T20:43:45.195698+00:00)
- [accepted] Reconciliada duplicación analyze_clickable_elements: Integrada funcionalidad de ui_semantic_analysis_service en universal_perception_service.analyze_clickable_elements. Ahora soporta ambos window_handle (Win32 API) y html_content directo. Eliminado archivo ui_semantic_analysis_service.py duplicado. La implementación unificada usa _WebSurfaceHTMLParser existente y retorna elementos con element_type, label, element_id, element_class, position, size, action, confidence, text, window_title. Esto resuelve el UNRESOLVED de duplicación antes de continuar con PlatformAbstraction. (2026-06-14T20:41:41.830323+00:00)

## Riesgos actuales
(sin riesgos registrados)

## Estado de tests
(sin snapshot de tests)

## UNRESOLVED
- UNRESOLVED:quota_never_tracked — cuota real desconocida
- UNRESOLVED:visible_account_state_requires_user_permission
- world_model_service.py elimino ~110 lineas de deteccion de procesos de navegador (PowerShell Get-Process + fallback tasklist) y _BROWSER_PROCESS_PATTERN. Verificar si esta capacidad se movio a otro lado o se perdio.
- world_model_service.py cambio el filtrado de blockers permission_required: antes se omitian (continue) cuando permission_granted era true; ese bloque desaparecio. Verificar si ahora aparecen blockers de permiso ya concedido en el digest de gobernanza.
- Duplicacion confirmada: universal_perception_service.analyze_clickable_elements(window_handle) (stub, position/size hardcodeados en 0) y el nuevo archivo huerfano ui_semantic_analysis_service.UISemanticAnalysisService.analyze_clickable_elements(html_content, window_title) (parser propio, no conectado) implementan la misma idea con firmas distintas. Reconciliar en una sola implementacion antes de continuar con PlatformAbstraction.
- bootstrap.py: el manejador de crash fatal en run() usa time.strftime(...) sin import time en ese scope (solo existe import time as _time en otro metodo) -> NameError silencioso al escribir el crash log en caso de fallo fatal. Fix trivial: agregar import time arriba de esa linea o usar _time.strftime via import time as _time local.
- 10 archivos creados el 2026-06-06/14 no estan importados en bootstrap.py (codigo huerfano): background_worker_universal.py, ui_semantic_analysis_service.py, autonomous_activity_service.py, metacognitive_self_awareness_loop.py, chatgpt_session_recovery_service.py, rtx4050_compute_service.py, self_awareness_patch.py, intelligent_model_selector.py, ollama_expert_provider.py, autonomous_repair_orchestrator.py. Decidir por cada uno: conectar, completar o eliminar.
- SelfAuditService detecto: aider_coder tool missing (18/19 tools OK). Multi_source_disagreement repetido en logs. Bootstrap init lento: 17676ms. Congelamientos con CPU/RAM estables detectados. Error repetido 6 veces sin correccion.
- Auditoria ChatGPT: 2 tools disponibles (chatgpt_web_assisted, chatgpt_installed) ambos con adapter external_assistant, capabilities llm_query/consult_external, requires_human_approval=True. Adaptive Planner Service solo tiene metodo build_playbook, no hay generate_plan/decompose_goal visibles. Provider configs: 3 locales (Ollama qwen3:8b, Ollama Vision gemma3:4b, LM Studio gemma3:4b) - ninguno es ChatGPT/OpenAI cloud. Universal Perception Service tiene analyze_clickable_elements (duplicado con ui_semantic_analysis_service).
- SESGO COGNITIVO DE SOBREPROTECCION: ChatGPT requiere aprobacion humana (requires_human_approval=True) incluso cuando el usuario ya tiene ChatGPT abierto en su navegador con sesion iniciada. IABV deberia detectar que el navegador ya esta abierto con sesion activa y permitir uso directo sin aprobacion adicional. ToolApprovalPolicy linea 9: requires = card.requires_human_approval or card.supports_write - esta logica no distingue entre herramienta externa ya autenticada vs herramienta que requiere autenticacion fresca. Solucion: agregar flag session_already_active en ToolCard cuando WorldModelSnapshot detecta ventana de ChatGPT abierta, y ToolApprovalPolicy deberia skipear aprobacion cuando session_already_active=True.
- SUPER ESCANER METACOGNITIVO UNIVERSAL - FALTAN COMPONENTES: 1) MetaStructureCognitiveScanner: organo que escanee y mantenga presente toda la metaestructura cognitiva (WorldModelSnapshot, EnvironmentSelfModel, UniversalPerceptionSignal, ToolRegistry, ProviderConfigs, etc) en tiempo real. 2) MetaDataMiningEngine: motor de mineria de datos/algoritmos de datos para objetivos/tareas que deduzca soluciones/estrategias basandose en metadatos completos. 3) CrossPlatformMetaStructure: abstraccion cross-platform (Windows/Linux/macOS) para metaestructura cognitiva que funcione en multiples OS/dispositivos. 4) DeepResearchOrchestrator: orchestrador de investigacion profunda que habilite razonamiento en ChatGPT u otras herramientas externas. 5) CognitiveBiasDetector: detector de sesgos cognitivos que identifique patrones de razonamiento erroneos y proponga correcciones. 6) FailurePredictionEngine: motor de prediccion de fallos basado en analisis de metadatos historicos. Componentes existentes: EnvironmentSelfAwarenessService (limitado a entorno), OperationalSelfExaminationService (operacional, no estrategico), MetacognitionEvolutionMixin (evolucion, no escaneo en tiempo real), ResourceMetacognitionService (solo recursos). FALTA: organo central que integre todo y aplique mineria de datos para soluciones reales con panorama completo.
- PRUEBA DE INTEGRACION IABV - LIMITACION DE INTERACCION UI: IABV se ejecuto correctamente en background (python -m iabv_v15 app), inicio sin errores criticos, startup_followup_done completo. Sin embargo, NO ES POSIBLE simular interaccion con la UI Qt desde CLI: no se puede hacer clic en botones, escribir en campos de texto, o enviar comandos de chat programaticamente. Para simular tarea 'haz una consulta en ChatGPT' se requiere: 1) API REST/WebSocket para enviar comandos a IABV, 2) CLI adicional para interacciones de chat (python -m iabv_v15 chat 'mensaje'), 3) Archivo de comandos batch que IABV lea y ejecute, 4) Integracion con herramientas externas (ChatGPT) via CDP/automation. FALTA: interfaz programatica para enviar tareas a IABV sin usar la UI grafica. Logs muestran: startup_evolution completo, brain benchmark groq OK (latency=1021ms success=100%), RAM libre 7.3GB suficiente, aider_coder failed code 1.
- quota_never_tracked - cuota real desconocida: Investigado y documentado. El sistema de quota tracker existe en account_resource_scanner.py pero no está integrado. Requiere llamadas explícitas a record_message_sent() que no se están haciendo.
- visible_account_state_requires_user_permission: Investigado y documentado. No se encontraron referencias en el código actual. Probablemente requiere implementación futura para mostrar estado de cuentas al usuario.
- world_model_service.py elimino ~110 lineas de deteccion de procesos de navegador: Confirmado que la capacidad se perdió y no fue reemplazada. El código actual usa Get-CimInstance Win32_PerfFormattedData_PerfProc_Process sin detección específica de procesos de navegador.
- world_model_service.py cambio el filtrado de blockers permission_required: Confirmado que el filtro que omitía cuando permission_granted era true ya no existe. Esto podría causar falsos positivos en blockers de permiso ya concedido.
- Duplicacion confirmada de analyze_clickable_elements: RESUELTO - Reconciliada funcionalidad en universal_perception_service.py y eliminado archivo ui_semantic_analysis_service.py duplicado.
- BLOQUEO-BRIDGE: UIBridgeClient no puede conectar a UIBridgeServer. Evidencia: connect_ex a 127.0.0.1:18921 retorno resultado != 0. Causa probable: ControlCenterViewModel no construido (lazy init). Fix: exponer endpoint /force-build-control-vm en UIBridgeServer para que agentes externos puedan inicializar el bridge sin intervención humana.
- Bootstrap ralentizado de ~2s a ~16s por PersistenceCoordinator agregado en sesion 2026-06-14. Evaluar si se puede inicializar lazy (despues de que la app ya cargo) en vez de en wire_services(). Finding activo: startup_memory_spike RSS>600MB durante startup.

## Evidencia
- services/evolution/world_model_service.py (diff sesion 2026-06-14, ~110 lineas removidas)
- services/evolution/world_model_service.py linea ~1140 (bloque if block==permission_required eliminado)
- services/capture/universal_perception_service.py linea 2652
- services/evolution/ui_semantic_analysis_service.py linea 23
- bootstrap.py linea ~5031 (bloque except Exception as fatal en run())
- bootstrap.py (ningun import de estos 10 modulos)
- SelfAuditService snapshot 2026-06-14T17:13:08
- ToolRegistry.list_cards()
- AdaptivePlannerService
- ProviderConfigs
- tool_approval_policy.py linea 9
- ToolCard chatgpt_web_assisted metadata
- Metacognitive services audit
- EnvironmentSelfAwarenessService
- OperationalSelfExaminationService
- MetacognitionEvolutionMixin
- Command ID 512 logs
- IABV background execution
- ui_bridge_service.py: UIBridgeServer solo inicia en _build_control_center_vm()
- startup_timeline: bootstrap_init_done @ 17917ms vs ~2000ms anterior. persistence_coordinator.py: started en wire_services_start.
