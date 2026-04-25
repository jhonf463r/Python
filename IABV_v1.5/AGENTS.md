# IABV v1.5 - Instrucciones Principales Para Codex

Eres el agente principal de ingenieria y evolucion de este proyecto.
Tu trabajo no es improvisar: debes leer el estado real del repo, respetar
la arquitectura vigente y dejar cada sesion con mejor evidencia, mejor
contexto operativo y menos trabajo redundante.

## Identidad Del Proyecto
- Nombre: `IABV v1.5`
- Workspace: `C:\Python\IABV_v1.5`
- Codigo fuente: `src/iabv_v15/`
- Pruebas: `tests/`
- Datos de trabajo: `data/`
- UI: Python + PySide6 + QML
- Enfoque: `local-first`, observabilidad operativa, autonomia gobernada, aprendizaje acumulativo y contexto portable

## Comando Oficial De Pruebas
Bateria completa:

```powershell
$env:PYTHONPATH='C:\Python\IABV_v1.5\src';
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q
```

Regla operativa:
- primero corre pruebas focalizadas del slice que toques
- luego corre una regresion razonable
- usa la bateria completa cuando el cambio toque contratos compartidos o cierre una fase importante

## Arquitectura Central Vigente

### Cerebro Y Decision
- `PerceptionSnapshot`: entrada unificada antes de cada decision
- `AdaptiveTaskOrchestrator`: orquestador principal
- `TaskContextAssembler`: ensambla contexto, perception y world model summary
- `AutonomyGovernancePolicy`: decide que rutas son viables o deben bloquearse
- `IntentUnderstandingService`: clasifica la intencion
- `LocalRoleRouter`: decide ruta y proveedor local

### Modelos Del Entorno
- `EnvironmentSelfModel`: estado de hardware, runtime y riesgos del entorno
- `WorldModelSnapshot`: panorama operativo vivo del sistema, herramientas, red, ventanas y bloqueos
- `UniversalPerceptionSignal`: observacion puntual de programa o pagina

### Aprendizaje, Contexto Y Revision
- `ExperimentLab`: compara rutas, asistentes y configuraciones
- `StrategySelector`: recomienda rutas por historial y evidencia
- `AdaptiveWeightLayer`: ajusta preferencia futura con base en resultados reales
- `TaskOutcomeRecorder`: cierra el loop de aprendizaje desde la ejecucion normal
- `PortableContextService`: exporta contexto comprimido y portable para nuevas sesiones
- `OperationalSelfExaminationService`: revisa patrones repetidos, degradaciones y ajustes recomendados
- `ia_trace_summary`: resumen de que IA o configuracion rindio mejor
- `comparison_scope_key`: agrupa problemas comparables para evaluar ganadores reales
- `adaptive_learning_summary`, `learned_patterns`, `validation_summary`: resumen operativo reusable

### Sandbox Y Validacion
- `SandboxExperimentService`: valida cambios o rutas candidatas sin tocar el sistema vivo
- `AutonomousValidationCycleService`: revisa candidatos y promueve solo lo que tenga evidencia
- `GuidedImprovementCycle`: sigue existiendo como estructura de mejora guiada; no es otro cerebro

### Herramientas Y Ejecucion
- `ToolTeachService`: consultas a herramientas externas
- `ToolRegistry` y `ToolCard`: catalogo operativo de herramientas
- `AutonomousEvolutionService`: puente de consulta externa autonoma
- `UIExecutionRunner`: ejecucion UI controlada

### UI
- `ControlCenterViewModel`: observa, explica y dispara flujos aprobados
- `EvolutionCenterViewModel`: observa estado evolutivo, world model, portable context y autoexaminacion
- Los ViewModels no deben convertirse en otro cerebro ni tomar decisiones de ruta por su cuenta

## Capas Cerradas Que Debes Respetar

### P1 - World Model Operativo
Ya esta cerrado.
Estado esperado:
- `WorldModelService` es la fuente viva de ventanas, foco, herramientas, red, procesos y bloqueos
- se consulta antes de rutas externas
- `TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `AutonomyGovernancePolicy` consumen `world_model`
- la UI lo lee; no lo modifica

### P2 - Neuroplasticidad Operativa Real
Ya esta cerrada en su nucleo.
Estado esperado:
- la ejecucion normal registra resultados reales
- `ExperimentLab`, `StrategySelector` y `AdaptiveWeightLayer` influyen decisiones futuras
- el sistema aprende por evidencia, no por costumbre

### P3 - Contexto Portable
Ya esta cerrado.
Estado esperado:
- `PortableContextService` genera paquete portable desde estado vivo y aprendizaje persistido
- el contexto portable se propaga por `TaskContextAssembler`, `AdaptiveTaskOrchestrator` y `EvolutionCenterViewModel`
- no existe una memoria paralela

### P4 - Autoexaminacion Operativa Real
Ya esta cerrada.
Estado esperado:
- `OperationalSelfExaminationService` detecta patrones, riesgos y ajustes recomendados
- tambien revisa si sus ajustes previos funcionaron o no
- sus hallazgos alimentan el contexto portable

### N3 - Autoexaminacion Del Codigo Fuente
Ya esta validada.
Hallazgo corregido relevante:
- se elimino refresh redundante de autoexaminacion en `EvolutionCenterViewModel`

### N4 - Validacion Real De WorldModel En Windows
Ya esta validada.
Hechos confirmados:
- ventanas abiertas reales y foco via Win32
- hilo activo de Codex via `%USERPROFILE%\\.codex\\state_5.sqlite`
- preflight de consulta externa bloqueado por permiso antes de actuar
- el estado vivo del hilo de Codex prevalece sobre historial stale

## Fuentes De Verdad Actuales
Prioriza esta jerarquia:
1. `WorldModelSnapshot` y `EnvironmentSelfModel`
2. contratos del codigo fuente
3. `PortableContextPackage` y `SelfExaminationSnapshot`
4. pruebas
5. historial persistido (`ExperimentLab`, sesiones adaptativas, run records)
6. suposiciones

Nunca inviertas ese orden.

Fuentes concretas:
- `bootstrap.py`: wiring real del sistema
- `src/iabv_v15/domain/models.py`: contratos soberanos
- `data/evolution/portable_context/latest.json` y `latest.md`
- `data/evolution/self_examination/latest.json` y `latest.md`
- `data/evolution/world_model/`
- `tests/`

## Politica Operativa Actual

Antes de usar una herramienta externa:
1. consulta `WorldModelSnapshot`
2. verifica red, foco, hilo, cuota, permiso y bloqueo activo
3. si falta permiso o evidencia, bloquea la ruta y explicalo

Si una pregunta es de:
- estado vivo del sistema
- autoconciencia del sistema
- aprendizaje acumulado
- autoexaminacion operativa

entonces:
- responde por la via humana local
- usa `world_model`, `environment_self_model`, `ExperimentLab`, `PortableContextService` y `OperationalSelfExaminationService`
- no dispares autonomia ni consulta externa

Cuando una herramienta falle o rinda mal:
1. no insistas a ciegas
2. registra el fallo con evidencia
3. revisa alternativas disponibles en `ToolRegistry`, `ExperimentLab`, MCPs o proveedores locales
4. compara la nueva ruta contra la actual usando resultados reales

## Contratos Que No Debes Romper
- No crear otro cerebro ni otro orquestador
- No duplicar `PerceptionSnapshot`
- No reemplazar `EnvironmentSelfModel`, `WorldModelSnapshot` o `UniversalPerceptionSignal`; se complementan
- No convertir un ViewModel en decisor de rutas
- No hacer refactor masivo sin aprobacion explicita
- No fingir observacion que no existe
- Si algo no puede confirmarse, marcar `UNRESOLVED`
- Si una ruta no es viable en el estado actual, bloquear antes de intentar
- El sandbox debe seguir aislado del sistema vivo

## Regla De Observacion Real
Si necesitas observar contenido visible de una ventana externa para verificar
si una herramienta esta utilizable:
- pide permiso explicito al usuario
- no asumas que el permiso existe
- no declares la herramienta disponible si no pudiste verificarla

## Pendientes Reales Que Siguen Abiertos
- La disponibilidad real de mensajes/cuota en herramientas externas visibles sigue requiriendo permiso explicito de observacion; sin ese permiso debe quedar `desconocidos` o `UNRESOLVED`.
- Algunos estados live, como `wrong_thread`, dependen del escritorio real del momento; si no estan presentes en vivo, se validan por pruebas y no se inventan.
- Varias suites de UI siguen siendo lentas en Windows; no es una falla funcional, pero si una deuda de rendimiento de pruebas.
- Si alguna conclusion depende solo de historial stale y contradice observacion viva, debe prevalecer la observacion viva.

## Autonomia De Operacion (Reduccion De Trabajo Manual)
Objetivo: que el usuario solo intervenga cuando hay decision real, no
rutina. Mientras la tarea sea ``implementar + pushear + mergear + audit``,
la ejecuta el agente en su VM sin pedir click en GitHub.

Reglas de auto-merge (usar ``scripts/auto_merge_devin_pr.py``):
- Rama obligatoria: ``devin/*`` o ``iabv-auto/*``. Otro prefijo requiere
  aprobacion explicita del usuario.
- El PR debe tener ``mergeable_state`` distinto de ``blocked`` / ``dirty``
  / ``behind``.
- Checks registradas deben concluir ``success`` / ``skipped`` / ``neutral``
  (si no hay checks, el repo IABV lo permite; queda registrado).
- ``--force`` solo se usa cuando el usuario pidio explicitamente saltear
  salvaguardas; el agente no se auto-concede force.

Aprobacion humana obligatoria (no auto-mergear) cuando:
- El PR toca ``main`` via merge directo (fast-forward sin PR).
- Cambia policies, contratos ``domain/models.py``, o capas cerradas
  P1-P4 (``world_model``, neuroplasticidad, contexto portable, auto-
  examinacion) mas alla de lo trivial.
- Implica migracion destructiva de ``data/`` o borra evidencia historica.
- Toca la politica de ``AutonomyGovernancePolicy``.
- Agrega dependencias nuevas pesadas (ej: ``watchdog``, modelos grandes).

Infra de arranque operativo para el usuario:
- ``scripts/iabv_bootstrap.ps1``: **entry point zero-touch** para maquinas
  / cuentas nuevas. Instala ``gh`` y ``cloudflared`` portable (sin winget,
  sin admin) en ``$HOME\.iabv\tools``, corre ``setup_iabv_profile.ps1``,
  corre ``rotate_tokens.ps1`` y arranca ``start_iabv.ps1``. Unico paso
  manual: click "Authorize" en el browser durante el device-flow de GitHub.
  Flags: ``-Force``, ``-NoStart``, ``-SkipInstalls``, ``-PrintTunnelUrl``.
- ``scripts/iabv_secrets.template.ps1``: template de secretos locales.
- ``scripts/setup_iabv_profile.ps1``: one-shot que deja ``$PROFILE`` y
  ``~/.iabv_secrets.ps1`` configurados; se corre una sola vez por maquina.
- ``scripts/start_iabv.ps1``: un comando para cargar secretos, validar
  shape y arrancar MCP + tunnel via ``run_mcp_bridge.ps1``.
- ``scripts/mcp_hot_reload.py``: wrapper opcional (``IABV_MCP_HOT_RELOAD=1``)
  que reinicia el MCP al detectar cambios en ``src/iabv_v15/*.py``. Sin
  dependencias externas; polling de mtimes.
- ``scripts/rotate_tokens.ps1``: rotacion asistida sin copy-paste. Usa
  ``gh auth login --web`` (device-flow) para obtener el PAT de GitHub y
  ``Read-Host -AsSecureString`` para pegar la Devin API key una vez.
  Escribe ambos valores a ``$HOME\.iabv_secrets.ps1`` solo despues de
  validarlos con HTTP 200 contra los endpoints reales. Nota: ``gh auth
  status`` escribe a stderr cuando no hay login; el script baja
  ``$ErrorActionPreference`` localmente alrededor de esa llamada para no
  matarse antes de leer el exit code.

## Principio Central De Autonomia — UNA SOLA VENTANA

IABV es **una unica ventana** con la que el usuario interactua al prender
su laptop. Todo lo demas lo hace el programa solo.

Reglas absolutas:
1. **El usuario NUNCA debe abrir PowerShell para configurar tokens.** Si
   falta un secreto, IABV abre el browser a la pagina correcta (GitHub
   settings, Devin API keys, etc.) y le pide al usuario que pegue el
   token en un dialogo dentro de la UI. IABV lo guarda automaticamente
   en ``~/.iabv_secrets.ps1`` via ``save_secret_to_profile()``.
2. **El usuario NUNCA debe instalar herramientas manualmente.** Si falta
   algo (gh, cloudflared, paquete pip), IABV lo instala solo. Si necesita
   admin, lo explica en la UI y ofrece un boton para elevacion.
3. **El usuario NUNCA debe editar archivos de configuracion.** Todo se
   configura desde la UI o se auto-detecta.
4. **Cada sesion de agente debe entender este principio.** No sugerir al
   usuario que ejecute comandos manuales, edite archivos, o copie tokens
   en una terminal. Si el agente necesita algo del usuario, lo pide via
   la UI de IABV o via un mecanismo automatico (device-flow, browser).

Funciones clave para autonomia de secretos:
- ``auto_correction_engine.auto_provision_missing_secrets()``: detecta
  secretos faltantes y abre el browser automaticamente para crearlos.
- ``auto_correction_engine.save_secret_to_profile(name, value)``: guarda
  un token en ``~/.iabv_secrets.ps1`` y lo activa en ``os.environ``.
  Llamado desde la UI cuando el usuario pega un token.
- ``auto_correction_engine._SECRET_PROVIDERS``: mapa de patrones de
  nombre de secreto a URLs de creacion (GitHub, Devin, OpenAI, etc.).

El bootstrap desde PowerShell (``iabv_bootstrap.ps1``) existe como
fallback para la primera instalacion o maquinas sin UI. Pero una vez
que la UI esta corriendo, **todo pasa por la ventana**.

## Forma De Trabajo En Sesiones Nuevas
1. lee este archivo primero
2. inspecciona `bootstrap.py` y los archivos del slice relevante
3. identifica contratos involucrados
4. busca el cambio minimo que preserve arquitectura
5. valida con pruebas focalizadas y luego regresion razonable
6. si algo falla, diagnostica y corrige antes de seguir
7. reporta resultado, pruebas, riesgos y `UNRESOLVED`

## Prompt De Arranque
Al empezar una sesion nueva:
- lee `AGENTS.md`
- despues inspecciona los archivos relevantes del repo
- usa primero estado vivo y contratos reales
- evita releer todo el historial si `PortableContextService` o `OperationalSelfExaminationService` ya condensan lo necesario
- trabaja con cambios minimos, verificables y guiados por evidencia real

## Salida Esperada Al Terminar
- que cambiaste
- por que era el cambio correcto
- que pruebas corriste
- que resultado dieron
- que quedo `UNRESOLVED`
- cual es el siguiente paso recomendado
