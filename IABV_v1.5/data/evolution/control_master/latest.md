# IABV v1.5 - Control Maestro

Generado: 2026-04-19T19:45:04.027095+00:00
Version: control_master.v1

## Vision actual
(sin vision registrada)

## Objetivos
- Activos: 1
- Completados: 3
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
(sin backlog persistido)

## Decisiones recientes
- [accepted] Los 3 gaps super-sync (cli-export, write-bridge, outcome-loop) quedan cerrados via PR #23 y PR #24; el objetivo raiz sigue ACTIVE hasta que PR #20/#23/#24 se mergeen a main (2026-04-19T19:44:23.380918+00:00)
  - razon: Solo con PRs mergeados la super sincronia vive en main. Mientras tanto las piezas existen, tienen tests verdes y estan cerradas como tareas en el propio ControlMasterService.
- [accepted] Los tres gaps de super sincronia se registran como objetivos reales dentro del propio ControlMasterService, sin codigo nuevo. El sistema se gobierna a si mismo. (2026-04-19T19:23:46.112273+00:00)
  - razon: El usuario pidio que cualquier sesion futura vea donde vamos y que falta. La infraestructura ya estaba: falta usarla. Registrar los gaps como objetivos persistidos es el camino minimo que preserva arquitectura y no inventa otro cerebro.

## Riesgos actuales
(sin riesgos registrados)

## Estado de tests
(sin snapshot de tests)

## UNRESOLVED
(sin items UNRESOLVED)
