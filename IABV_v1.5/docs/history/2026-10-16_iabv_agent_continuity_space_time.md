# IABV — Memoria de continuidad espacio-temporal y coordinación de agentes

**Corte temporal:** 2026-10-16, America/Bogota  
**Estado:** memoria de continuidad documental; no es contrato normativo, aprobación de Candidate C ni autorización operativa.  
**Gobierno vigente:** GOVERNANCE = KEEP_BLOCKED.  
**Propósito:** preservar estado, secuencia causal, procedencia y siguientes acciones; evitar reiniciar auditorías ya realizadas o mezclar checkouts.

---

## 1. Reglas de continuidad y procedencia

Usar estos estados de evidencia:

- **GITHUB_API_VERIFIED:** metadatos o referencias leídos de la API pública de GitHub en este corte.
- **CODEX_LOCAL_REPORTED:** resultado comunicado por Codex desde un checkout local. Conservar commit, ruta y método que el agente declara.
- **OWNER_REPORTED:** información aportada por el propietario aún no contrastada independientemente.
- **PROPOSED:** análisis, reparación o siguiente paso aún no aprobado.
- **UNPROVEN:** propiedad de implementación/runtime no demostrada.
- **NOT_RECOVERED:** fuente original no recuperada; no reconstruirla ni sustituirla por un archivo parecido.

Todo resultado futuro debe incluir fuente, commit exacto, ruta de trabajo, método de comprobación y limitaciones. No atribuir a otro agente verificaciones que no haya reproducido.

Invariantes:
1. La especificación no demuestra implementación ni runtime.
2. La visibilidad pública no garantiza que un agente tenga el checkout adecuado, red o permisos de escritura.
3. Un nombre de componente no demuestra una conexión causal entre componentes.
4. Una auditoría documental no aprueba la candidatura ni levanta KEEP_BLOCKED.
5. No resolver decisiones reservadas al propietario mediante inferencias del modelo.
6. No alterar o “limpiar” un worktree sin identificarlo y comprobar su estado.

## 2. Estado publicado de GitHub en este corte

Repositorio público: https://github.com/jhonf463r/Python

| Elemento | Estado observado | Interpretación |
|---|---|---|
| main publicado | 9e0ce66768aedd7422e0d3551affd398f44a7532 | SHA informado por la API de GitHub al redactar. No es intercambiable con un SHA de una rama/worktree local. |
| PR #465 / Candidate B | Open, Draft, sin fusionar; HEAD e2876e8e015078d81dd9e1592d2a98122c430b2c; base main en 9e0ce667... | Candidatura B preservada. https://github.com/jhonf463r/Python/pull/465 |
| PR #466 / Candidate C | Open, Draft, sin fusionar; tres commits; HEAD 1f0b114587a761509e6100b13f6ab6a14258e3b8; base en la rama Candidate B con SHA e2876e8e... | Candidatura C documental basada en B. https://github.com/jhonf463r/Python/pull/466 |
| Commit D-C1 | 1f0b114587a761509e6100b13f6ab6a14258e3b8 | Retira el oráculo genérico de replay en T130/T131; no modifica la PR #465. |

**Divergencia de procedencia que no se debe borrar por inferencia:** el informe local de BIO-04 de Codex menciona un main canónico a92b7c1b4, mientras que la API pública consultada aquí informa main = 9e0ce667... Podrían ser referencias local y remota distintas. Antes de sincronizar nada, comparar git rev-parse, git remote -v, git branch -avv y git worktree list --porcelain desde el entorno correspondiente.

## 3. Candidate C — resultados y pendientes

El siguiente resumen se conserva como CODEX_LOCAL_REPORTED. Los recuentos estructurales también se contrastaron en esta conversación leyendo los CSV y el delta publicados.

- Checkout inspeccionado: HEAD 1f0b114587a761509e6100b13f6ab6a14258e3b8, detached HEAD y working tree limpio, según Codex.
- Matriz: 74 IDs únicos y consecutivos T123–T196, 11 columnas originales y todos los estados NOT_RUN.
- Baseline → Candidate C: 53 filas y 111 celdas modificadas; 111 pares únicos (test_id, field). Codex declara que la correspondencia bidireccional del delta fue comprobada.
- SHA-256/tamaños: Codex informa coincidencia para todas las entradas hash enumeradas por los manifiestos.
- Recuentos correctos, distinguiendo entradas hash de inventario:
  - Manifiesto de publicación: **25 entradas hash**; inventario total del paquete: **26 archivos**, incluido el propio manifiesto de publicación.
  - Manifiesto del payload Candidate C: **12 entradas hash**; inventario candidate/: **13 archivos**, incluido su propio manifiesto.
  - Manifiesto baseline: **6 entradas hash**; inventario baseline/: **8 archivos**, incluido el manifiesto baseline y BASELINE_NOTICE.md.
  - Los conteos anteriores 28/28 y 14/14 no se reconcilian con los árboles inspeccionados. El 8/8 corresponde al inventario de baseline, no a ocho entradas hash del manifiesto.
- .gitattributes: Codex informa que blob y working tree coinciden; 31 bytes, SHA-256 5d2c66adb84298fd3a0322767edd663cc96af4554d31257ad64fd2d4ddbd70c6, Git blob SHA b3d151ff4aa95313e869da55b2d721c9997323c9. El contenido actual usa LF. La explicación previa de una diferencia CRLF/LF no está respaldada por los bytes actuales.
- Barrido D-C1: la frase genérica de idempotencia aparece en 45 filas del baseline, 44 en el commit intermedio 14edb53e8efd5cd0523cee62646857de14ceb5f7 y 42 en el HEAD actual. El cambio 45→44 corresponde a una revisión previa de T162; D-C1 elimina las dos instancias restantes de T130 y T131.
- El contrato reconstruido y el baseline se informan sin cambios.

Artefactos:
- Matriz: https://github.com/jhonf463r/Python/blob/1f0b114587a761509e6100b13f6ab6a14258e3b8/IABV_v1.5/docs/reviews/R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_C_2026-10-15/candidate/R10_V0_7_2_TEST_MATRIX_T123_T196.csv
- Delta: https://github.com/jhonf463r/Python/blob/1f0b114587a761509e6100b13f6ab6a14258e3b8/IABV_v1.5/docs/reviews/R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_C_2026-10-15/candidate/R10_V0_7_2_MATRIX_REPAIR_DELTA_C.md
- Informe: https://github.com/jhonf463r/Python/blob/1f0b114587a761509e6100b13f6ab6a14258e3b8/IABV_v1.5/docs/reviews/R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_C_2026-10-15/candidate/R10_V0_7_2_MATRIX_REPAIR_REPORT_C.md
- Registro D-01…D-10: https://github.com/jhonf463r/Python/blob/1f0b114587a761509e6100b13f6ab6a14258e3b8/IABV_v1.5/docs/reviews/R10_V0_7_2_MATRIX_REPAIR_CANDIDATE_C_2026-10-15/OWNER_DECISIONS_REQUIRED.md

D-01 a D-10 siguen pendientes de decisión autorizada del propietario. Entre otros puntos: restores_event_id y event_id; transición post-conflicto y supersedes_evaluation_id; ciclo de vida/versionado STRATEGY; TTL del nonce; criterio de incompatibilidad; semántica de adjuntos MANUAL; referencia citada en §0; cobertura §14; pruebas adicionales de correlación; fencing token separado de authorization_generation.

Siguen UNPROVEN la atestación de plataforma, ejecución del validador, secuenciador/CAS real, publicación atómica y barreras, fencing efectivo, propagación de generación de autorización y rechazo de escritores heredados. No se ejecutaron pruebas de producto, builds ni runtime; la matriz continúa NOT_RUN.

**Dictamen operativo:** Candidate C tiene comprobaciones estructurales y del delta satisfactorias según el informe local, pero no es aceptación contractual definitiva ni autorización de implementación. Mantener #465 y #466 abiertas como Draft y KEEP_BLOCKED.

## 4. BIO-04 — continuidad de capability → realization

El informe BIO-04 de Codex es un análisis estático que declara haber inspeccionado fuentes asociadas al commit 07ebffc8f866fc99a3f78091dcd1edd456a0da00. Mantenerlo como CODEX_LOCAL_REPORTED hasta reconciliar exactamente el worktree y el HEAD utilizados.

Conclusiones reportadas:
- Los mismatches de IDs entre capability readiness y strategy packs parecen afectar _candidate_rationale/texto diagnóstico, no el estado calculado por _worst_status en los casos revisados.
- _is_local_chat_flow y tool_operational_executor.supports son consumidores operativos relevantes de chosen_pack_id. No generalizar fuera de los casos revisados.
- ScenarioRegistry tiene una señal pack:browser.generic para browser.search, mientras el fallback genérico podría generar pack:browser.search. Codex lo clasificó RATIONALE ONLY porque la comparación de señales no gobierna decisiones actualmente.
- La mínima comprobación pendiente es inspeccionar ScenarioRegistry:68 y todos los consumidores actuales de expected/observed.
- Pivot propuesto: capability → realization, reutilizando AdaptiveModelSelector y CloudReasoningPlannerService. El parámetro exclude fue reportado como canal de extensión sin llamadores que lo pueblen; verificarlo directamente en el commit correcto antes de aceptarlo como hallazgo final.

**Discrepancia de procedencia BIO-04:** el informe BIO-04 cita un baseline/HEAD 07ebffc8..., mientras el informe R10 posterior identifica C:/IABV_BIO04_009d con HEAD d1a55897b. Además, Candidate C aparece inspeccionada en un momento en C:/temp/candidate-c-inspect y en otro informe en C:/temp/candidate-inspect. No borrar ni sincronizar worktrees para “arreglar” los nombres: listarlos y verificar su commit real antes de asignar tareas de escritura.

## 5. Objetivo de desarrollo que no se debe perder

La cadena causal que se quiere verificar en el código real continúa siendo:

~~~text
sandbox → ToolMemory → InteractionLearningService → InteractionModeSelector
~~~

No queda probada por la mera existencia de esos nombres. La inspección tiene que establecer:
- productor de evidencia en sandbox;
- identidad/correlación conservada por ToolMemory;
- evento o interfaz por la que InteractionLearningService consume esa evidencia;
- resultado persistente que produce el servicio;
- cómo InteractionModeSelector lee y utiliza ese resultado;
- límites entre observación, recomendación y efecto automático;
- evidencia positiva y falsador para cada arista.

Esta cadena es una línea de desarrollo coordinada pero distinta de capability → realization. Solo se conectan si el código demuestra la relación causal.

## 6. Coordinación de agentes durante la ausencia temporal de Claude Pro

No es necesario detener la investigación porque Claude Pro no esté disponible temporalmente. Evitar lanzar varios agentes a editar o repetir la misma auditoría.

| Agente/herramienta | Función principal | Límites |
|---|---|---|
| **Codex CLI local** | Agente primario para inspección real del repositorio, worktrees, referencias Git, llamadas entre servicios y análisis estático cuando se autorice. | No tocar C:/Python mientras siga dirty; no cambiar ramas ni modificar Candidate B/C sin autorización. |
| **OpenCode + Kilo Gateway** | Segunda opinión acotada sobre un mapa de llamadas o informe producido por Codex. Verificar modelo, proveedor, contexto y términos de datos en el selector actual. | Gateway no garantiza acceso al checkout local. No enviar secretos, tokens, .env ni datos privados. |
| **Claude Code cuando vuelva el acceso Pro** | Revisión adversarial independiente del mapa de evidencia y de un diff acotado; buscar falsadores y contradicciones. | No repetir toda la auditoría desde cero ni recibir escritura automática sobre el checkout principal. |
| **ChatGPT con conector GitHub** | Coordinar continuidad, contrastar metadatos/artefactos publicados y mantener la memoria documental. | No afirmar acceso a un worktree local o runtime ni a bytes no recuperados. |
| **Propietario** | Resolver D-01…D-10, autorizar cambios y decidir cuándo pasar de lectura a escritura/runtime. | No sustituir decisiones de producto por inferencias de agentes. |

**Privacidad en proveedores gratuitos:** los modelos/endpoints gratuitos pueden cambiar de proveedor y condiciones. La documentación actual de Kilo indica que kilo-auto/free enruta dinámicamente y puede usar proveedores que registran prompts/respuestas para mejorar sus servicios; los endpoints de prueba de NVIDIA advierten no enviar datos personales/confidenciales. Mandar el mínimo contexto necesario y excluir secretos. Ver https://kilo.ai/docs/gateway/models-and-providers.

## 7. Próxima secuencia de trabajo, sin reiniciar

### Fase A — reconciliar procedencia local, solo lectura
1. Desde Codex, ejecutar git worktree list --porcelain, git status --short --branch, git rev-parse HEAD, git remote -v y git branch -avv.
2. Identificar por separado C:/Python (reportado dirty: 511 archivos modificados, muchos .pyc y eliminación de wplay), el worktree BIO-04, C:/temp/candidate-c-inspect y C:/temp/candidate-inspect.
3. No editar, limpiar, resetear, hacer checkout ni sincronizar el árbol dirty. Si la identidad del worktree no es clara, detenerse.

### Fase B — avanzar BIO-04 sin repetir el reporte
4. En un worktree de inspección verificado, revisar ScenarioRegistry:68 y buscar todos los usos de las señales esperadas/observadas.
5. Trazar AdaptiveModelSelector → CloudReasoningPlannerService → llamadas/consumidor de exclude. Construir tabla productor → transformación → consumidor → efecto → falsador.
6. Entregar mapa de llamadas, referencias archivo/línea, commit exacto y plan mínimo. No cambiar el contrato R10 ni modificar lógica todavía.

### Fase C — verificar la conexión de aprendizaje
7. Seguir sandbox → ToolMemory → InteractionLearningService → InteractionModeSelector de origen a destino con búsqueda automatizada en el checkout correcto.
8. Registrar cada arista con evidencia positiva, identidad/correlación, persistencia y falsador.
9. Separar hechos confirmados, hipótesis y componentes existentes cuya conexión no está demostrada.
10. Proponer instrumentación mínima de solo lectura que permita probar causalidad sin activar efectos automáticos.

### Fase D — revisión cruzada
11. OpenCode/Kilo revisa solo los hallazgos de Fases B/C y busca falsadores.
12. Cuando Claude Pro esté disponible, pedir revisión adversarial del informe consolidado y cualquier diff propuesto, no una nueva auditoría completa.
13. Solo después se decide explícitamente si se autoriza escribir código. La ejecución de runtime o activación del puente físico requiere autorización aparte.

## 8. Puente físico de la laptop

El documento https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/mcp-bridge.md describe una arquitectura MCP, pero no prueba el estado runtime actual. La existencia de una guía o de una instancia en bootstrap tampoco prueba que el puente esté activo ni que la cadena de aprendizaje funcione.

**Estado actual:** no activar el puente ni exponer herramientas en red durante las fases anteriores. Inspeccionar antes el estado real de gobernanza, el toggle y las rutas de lectura/escritura. Si posteriormente se autoriza un arranque, definir alcance mínimo, observabilidad, límites de red, rollback y prueba de no-efectos. Esta memoria no es autorización de activación.

## 9. Prompt de continuidad para el siguiente agente

Continúa IABV desde este documento. No reinicies R10 ni BIO-04.

Primero reconcilia los worktrees y commits en modo solo lectura. Protege C:/Python; no hagas limpieza, reset ni sincronización automática.

Después continúa BIO-04: comprueba ScenarioRegistry:68 y traza capability → realization por AdaptiveModelSelector, CloudReasoningPlannerService y exclude. Conserva como objetivo explícito separado la cadena sandbox → ToolMemory → InteractionLearningService → InteractionModeSelector.

Devuelve matriz de evidencia productor → consumidor, falsadores, commit y rutas exactas, limitaciones y propuesta mínima. No edites archivos, no ejecutes runtime, no accedas a M0A ni actives el puente físico. Mantén KEEP_BLOCKED y espera una decisión explícita antes de cualquier escritura.

---

**Regla final:** esta memoria conserva tiempo, proveniencia y dependencias entre sesiones; no convierte hallazgos reportados en hechos independientemente reproducidos ni convierte propuestas en autorizaciones.


## 10. Actualización BIO-04 y arista de aprendizaje — Codex local

**Fuente:** informe de Codex entregado el 2026-10-16 aproximadamente 12:16 America/Bogota; inspección estática declarada en C:/Python/IABV_BIO04_009d, branch codex/bio04-verified-outcome-seams-20261002, HEAD d1a55897…. Esta sección es **CODEX_LOCAL_REPORTED**; los archivos públicos de GitHub consultados separadamente muestran contenido de los símbolos relevantes, pero no demuestran por sí solos el estado runtime del worktree Windows.

### 10.1 Procedencia más precisa

- C:/Python: Codex reporta HEAD detached 8425f03e…, 58.901 entradas de estado (git status --porcelain --untracked-files=all), incluyendo cambios/eliminaciones de wplay. Un reporte anterior registraba 511 archivos modificados. Los números no son comparables sin normalizar método y conteo; mantener el checkout intacto.
- C:/Python/IABV_BIO04_009d: branch codex/bio04-verified-outcome-seams-20261002, HEAD d1a55897…, limpio y siguiendo el mismo commit remoto según Codex.
- C:/CodexWorktrees/bio04-d1a55897-runtime: detached en d1a55897…, 160 entradas de estado; no se usó para el análisis según Codex.
- C:/temp/candidate-c-inspect: detached en 1f0b1145…, limpio; solo se identificó.
- C:/temp/candidate-inspect: no existe según Codex.
- Remoto observado por Codex: origin/main = 9e0ce667…, BIO-04 remoto d1a55897…, continuidad remota c0d04444…; C:/Python local main f12f3bc9…. El reporte dice que 07ebffc8… y d1a55897… existen como objetos locales, pero no detectó merge-base con los comandos usados. Conservar como discrepancia de procedencia; no afirmar una historia lineal ni hacer sincronización automática.
- Candidate B/C y memoria continúan en ramas separadas. No se fusionó ni se editó ninguna PR de R10.

### 10.2 BIO-04: resultado de la investigación de señales

El mismatch entre expected_signals de ScenarioRegistry y el pack canónico tiene estos hechos reportados:

- El caso especial Google de browser.search declara pack:browser.generic.
- El fallback general forma pack:{intent.intent_key}, que para browser.search es pack:browser.search.
- StrategyPackRegistry asigna browser.search a browser.generic; el pack genérico admite esa intención.
- ExpectationMatcher compara/produce señales; ExecutionProbeService las conserva en metadata; ScenarioAutoTestService las persiste en episodio/run; PendingIssueService puede copiar señales esperadas al texto de una sugerencia.
- En el ResultComparator.compare() inspeccionado, las listas expected/observed no se consultan para decidir la categoría. El comparador decide usando capability readiness, incidentes, ejecutor, simulación y evidencia visual.

**Conclusión acotada:** el desajuste es diagnóstico/persistido y podría degradar texto de orientación, pero no se mostró que cambie selección operativa ni categoría de comparación en las fuentes revisadas. **Falsador:** hallar un consumidor adicional de expected/observed que decida ruta, adaptador o ejecución. No convertir esta conclusión acotada en afirmación universal sobre toda la aplicación.

Reparación mínima propuesta: alinear la señal esperada con la resolución canónica del pack o añadir una normalización central para esa identidad. Añadir cobertura fuente para el caso Google y el fallback no-Google; comprobar que la corrección solo cambia el diagnóstico que corresponde y no el resultado operativo. No implementar hasta revisar el consumidor completo y el contrato deseado.

### 10.3 AdaptiveModelSelector → CloudReasoningPlannerService → exclude

Según la inspección de Codex:

- AdaptiveModelSelector.select_best_provider() admite exclude y elimina proveedores del conjunto elegible.
- Bootstrap conecta el selector a CloudReasoningPlannerService.
- El planner llama select_best_provider(task_type='planning') sin exclude; los call sites productivos inspeccionados tampoco lo pasan. Los usos encontrados que lo pasan pertenecen a tests.
- Si un caller lo proporcionara, afectaría elegibilidad/fallback, no los scores del selector.

**Conclusión:** exclude es una capacidad de la API del selector, pero aún no un canal de extensión operativo del planner conectado porque no hay caller productivo que lo alimente. No cablearlo hasta identificar una política real y sus invariantes.

### 10.4 Cadena causal de aprendizaje inspeccionada

La cadena estática reportada por Codex es:

    ToolTeachService
      → ToolSandbox.run(adapter, sandbox=True)
      → ToolMemory.remember_result(...)
      → InteractionLearningService.learn_from_execution(...)
      → ToolRecordRepository (archivos JSON + índices/tablas SQLite)
      → InteractionModeSelector en selecciones posteriores

Evidencia de fuente que Codex atribuye al checkout d1a55897…:

- bootstrap.py:685 y :730: se instancian los servicios y se comparte el repositorio correspondiente.
- tool_sandbox.py:12: llama al adaptador con sandbox=True, crea un ToolResult con estado sandboxed y solicita validación con sandbox=True.
- tool_teach_service.py:827: guarda el resultado con ToolMemory.remember_result() antes de retornar waiting_approval cuando la acción requiere aprobación y aún está pendiente.
- tool_memory.py:31: persiste el resultado, actualiza el ToolCard, registra la ejecución y llama a learn_from_execution().
- interaction_learning_service.py:535: _is_effective_success() acepta validation_status approved o sandbox_pass, sujeto a otras condiciones.
- interaction_mode_selector.py:222 y el score de _assess_candidate: patrones con éxitos afectan estabilidad/learned-pattern y el score de selecciones genéricas posteriores.
- tool_record_repository.py:227: persiste patrones en JSON e indexa su identidad/camino en SQLite.

### 10.5 Hallazgo prioritario: separar procedencia del aprendizaje

**Código estático confirmado en la revisión de la fuente, runtime no ejecutado:** un resultado sandbox_pass puede aumentar InteractionPattern.success_count; ese patrón se puede consultar en una selección posterior. En ToolTeachService, el aprendizaje ocurre antes del retorno waiting_approval de una tarea que todavía no ha pasado la aprobación necesaria para la ejecución fuera de sandbox.

Esto significa que el sistema puede aprender que una secuencia/patrón fue eficaz **en sandbox** antes de que exista experiencia de ejecución operativa real. No demuestra automáticamente que sea un bug: el diseño puede permitir aprender patrones de preparación/forma de interacción. Sí es un riesgo semántico si el mismo contador/señal se interpreta como evidencia de eficacia operativa al puntuar selecciones futuras.

**Siguiente acción propuesta (solo lectura/diseño, no editar):** construir una tabla de tipos de evidencia y consumo: sandbox_pass, approved, ejecución real verificada, rollback, bloqueado y resultado desconocido. Determinar para cada tipo qué contadores/patrones/episodios actualiza y qué selector lee esos datos. Después presentar una propuesta mínima para que éxito de sandbox y éxito operativo mantengan procedencia separada y no compartan peso semántico accidentalmente. No recomendar bloquear todo aprendizaje sandbox por defecto; distinguir aprendizaje de forma/preparación de experiencia real de eficacia.

Pruebas discriminantes futuras, solo tras autorización: a) sandbox pass antes de aprobación no incrementa el contador destinado a experiencia operativa verificada; b) ejecución real aprobada y verificada sí lo incrementa; c) failure/block/rollback no crea una contribución positiva; d) una selección posterior expone por separado la fuente de su evidencia. No se ejecutaron estas pruebas en esta inspección.

### 10.6 Prioridad y límites actualizados

Orden recomendado:
1. Reconciliar worktrees y procedencia; proteger C:/Python y no limpiar/resetear/sincronizar automáticamente.
2. Documentar el flujo exacto de evidencia sandbox_pass y su impacto en InteractionPattern/InteractionModeSelector.
3. Revisar ScenarioRegistry/expected signals y el no-uso productivo de exclude como tareas de menor riesgo.
4. Preparar una propuesta mínima y pruebas discriminantes; revisión cruzada por OpenCode/Kilo y después Claude cuando esté disponible.
5. Solo con autorización separada, evaluar cambios de código; la prueba runtime y el puente físico requieren gates independientes.

No se accedió a M0A, no se ejecutaron tests/build/runtime en esta misión y no se modificó código de producto. **R10 permanece KEEP_BLOCKED. El puente físico sigue sin activarse.**


## 11. BIO-04 — identidad de intento, doble contabilización y procedencia del éxito

**Fuente:** resultado de inspección estática de Codex aportado el 2026-10-16 a las 12:23 America/Bogota. Checkout declarado: `C:/Python/IABV_BIO04_009d`, branch `codex/bio04-verified-outcome-seams-20261002`, HEAD `d1a55897bf7f758914b8237d48ae43f245f06592`, limpio y coincidente con el commit remoto según Codex. Estado de evidencia: **CODEX_LOCAL_REPORTED**. No hubo edición de código, tests, build, runtime ni acceso a M0A. Los enlaces locales `C:/...` del reporte son evidencia de ruta en el entorno declarado por Codex, no enlaces públicos verificables desde GitHub.

### 11.1 Recorrido de los resultados

- `ToolTeachService.execute_task()` invoca `ToolSandbox.run()`; el sandbox llama `adapter.run(..., sandbox=True)` y después a `ToolValidator`. El resultado de sandbox conserva un `task_id` y tiene `result_id` propio.
- `ToolMemory.remember_result()` persiste el resultado, actualiza los contadores de la tarjeta, registra el evento y llama al aprendizaje de interacción. La ruta inspeccionada lo hace antes de regresar `waiting_approval` cuando falta aprobación para continuar fuera del sandbox.
- La copia devuelta como `waiting_approval` conserva el mismo `result_id`. En el tramo inspeccionado no se vuelve a persistir esa copia modificada salvo que haya supervisor de auditoría.
- Una ejecución posterior puede reconstruir una nueva tarea a partir de la sesión/ruta de ejecución. La construcción usa un `task_id` nuevo por defecto; conservar `session_id` o `run_id` no equivale a conservar identidad de tarea, intento ni idempotencia de etapa.
- Sandbox y ejecución operativa pueden generar `result_id` distintos bajo un mismo `task_id` dentro de una llamada; si la operación aprobada se hace en un ciclo posterior reconstruido, los IDs de tarea pueden también diferir. No hay una identidad tipada y común de intento que una explícitamente estas etapas en el contrato inspeccionado.
- `ToolTask.task_id`, `ToolResult.result_id`, `InteractionPattern.pattern_id`, `InteractionEpisode.interaction_episode_id` y `InteractionObservation.observation_id` son identidades distintas. El patrón también se localiza por una firma derivada del contexto/canal/herramienta/sitio/acciones.

### 11.2 Contabilidad y límites de idempotencia

- `ToolMemory` actualiza `ToolCard.success_count` o `failure_count` según `result.success`, sin exigir por sí mismo que el estado de validación sea aprobado o verificado.
- `InteractionLearningService._is_effective_success()` exige `result.success` y `validation_status` en `approved` o `sandbox_pass`, además de las salvaguardas revisadas contra captura pendiente, login requerido o incoherencia. Por tanto, `sandbox_pass` puede aumentar `InteractionPattern.success_count`.
- La persistencia por `result_id` puede reemplazar el registro de ese resultado, pero `remember_result()` invoca aprendizaje cada vez. No se identificó una clave de deduplicación que proteja las contribuciones por intento, etapa y resultado procesado; volver a recordar el mismo resultado podría incrementar contadores otra vez.
- Los éxitos sandbox y operativo pueden aportar dos contribuciones positivas diferentes, incluso si ambos pertenecen a la misma tarea lógica. Esto es un riesgo potencial de doble peso de una secuencia, no prueba de que un escenario runtime concreto haya ocurrido.
- Los resultados bloqueados antes de entrar al sandbox (por ejemplo, tarjeta/adaptador ausente) toman una ruta de persistencia/evento que omite `ToolMemory` y `InteractionLearningService`; los fallos de sandbox sí pasan por el camino de memoria y aprendizaje.
- Para un fallo no bloqueado, el rollback se intenta bajo condiciones de escritura/destrucción/acciones de rollback. La señal de rollback se agrega al resultado del intento; un rollback exitoso no convierte el resultado operativo fallido en éxito.
- `awaiting_response` no pertenece a la lista de estados de fallo efectivo mencionada por Codex; si conserva `success=True`, tampoco cuenta como éxito efectivo según el predicado descrito. Tratarlo como evidencia neutral/incompleta requiere una decisión explícita del contrato.

### 11.3 Validación frente a postcondición verificada

`ToolValidator` puede marcar `approved` un resultado conforme a `success` y aprobación o al alcance `read_only`. El verificador independiente de postcondición inspeccionado se ejecuta después en el flujo de ejecución y registra su veredicto en el outcome de la sesión. Codex no encontró que ese veredicto vuelva a actualizar `ToolResult`, `InteractionPattern` o `InteractionEpisode`.

**Conclusión acotada:** los contadores vigentes reflejan éxito/validación del resultado del adaptador según las reglas actuales; no constituyen, por sí solos, evidencia de que una postcondición independiente haya sido verificada. Falsador: localizar otro consumidor/camino que propague de forma autoritativa el recibo de postcondición a esos registros antes de puntuar el patrón.

### 11.4 Efecto reportado en selecciones futuras

- `InteractionModeSelector` usa contadores de la tarjeta para estabilidad/frecuencia y patrones exitosos en la puntuación general; los episodios exitosos pueden aportar una bonificación de resolución.
- La ruta especial `external_assistant` mantiene una puntuación fija para la herramienta preferida en el tramo inspeccionado. Aun allí, patrones/episodios afectan estado/reutilización y fallos bloqueados repetidos pueden apartar o impedir esa ruta.
- Por eso, si una contribución `sandbox_pass` se mezcla con el mismo contador interpretado como eficacia operativa, puede cambiar decisiones futuras sin una ejecución real verificada. El efecto exacto depende de la ruta y del candidato; no se afirma que cada selección cambie.

### 11.5 Contrato aditivo propuesto — no implementado

1. Añadir procedencia tipada para cada contribución, por ejemplo `sandbox_preapproval`, `execution_approved`, `postcondition_verified`, `failed`, `blocked`, `rolled_back` y `legacy_unknown`.
2. Distinguir tarea lógica, intento de ejecución, resultado y etapa de evidencia. Asignar `execution_id` al intento y aplicar idempotencia a `execution_id + evidence_stage + result_id` (o una clave estable equivalente) para que re-procesar el mismo aporte no incremente contadores otra vez.
3. Conservar el aprendizaje de sandbox para forma/secuencia/preparación, pero mantenerlo separado de la señal que representa fiabilidad operativa. No promover registros históricos ambiguos a éxito operativo verificado: clasificarlos `legacy_unknown` hasta contar con evidencia suficiente.
4. Requerir un recibo independiente y atribuible de postcondición antes de añadir evidencia positiva a la señal operativa verificada; `ToolValidator.approved` no debe equivaler automáticamente a `postcondition_verified`.
5. Registrar la procedencia y los IDs de evidencia que contribuyen a cada decisión del selector, para explicar qué contador/patrón/episodio influyó realmente en el score.

Riesgo de no separar señales: una práctica de preparación puede presentarse como eficacia operativa. Riesgo de separar sin compatibilidad: recalificar injustificadamente patrones históricos cuya procedencia ya no puede reconstruirse. El diseño debería ponderar ambas cuestiones y preservar compatibilidad histórica.

### 11.6 Pruebas discriminantes propuestas — NO EJECUTADAS

1. Un `sandbox_pass` previo a aprobación incrementa evidencia de preparación, pero deja en cero la evidencia de operación verificada.
2. Una ejecución real con postcondición independiente atribuible incrementa una sola vez la señal operativa; aprobación del validador por sí sola no basta.
3. Bloqueo, fallo, rollback exitoso/fallido y resultado incompleto nunca incrementan la señal operativa positiva.
4. Recordar dos veces el mismo resultado/etapa no duplica contabilidad; sandbox y ejecución son etapas distinguibles; un intento nuevo tiene un `execution_id` nuevo.
5. Una selección posterior expone procedencia/IDs de evidencia e identifica qué componente influyó en su puntuación.

6. **Runtime separado y pendiente de autorización:** demostrar persistencia tras reinicio, observar una ejecución real con verificador independiente, confirmar la semántica de `sandbox=True` para cada adaptador y verificar qué evidencia consume una selección posterior. La mera presencia del argumento `sandbox=True` no prueba confinamiento del sistema operativo.

### 11.7 Siguiente paso y gobierno

El siguiente mínimo técnico es preparar un cambio offline y acotado para el modelo de procedencia, deduplicación por etapa y consumo del selector, acompañado de pruebas unitarias discriminantes. **Esta recomendación no es autorización para implementarlo**: la autorización de escritura debe ser expresa y separada de cualquier autorización runtime. Hasta entonces, continuar solo con especificación/diff propuesto, revisión adversarial y protección de `C:/Python`.

**Estado final de este corte:** `GOVERNANCE = KEEP_BLOCKED`. No se editaron archivos de producto, no se ejecutaron tests/build/runtime, no se accedió a M0A y el puente físico sigue sin autorización/activación. La ruta de aprendizaje está respaldada por análisis estático reportado; persistencia viva, confinamiento efectivo y eficacia operativa verificada permanecen **UNPROVEN**.

## 12. Learning provenance — implementation offline report and next objective: agent continuity loop

**Source / provenance:** report pasted by the owner at approximately 13:29 America/Bogota on 2026-10-16, attributed to Codex. Preserve as **CODEX_LOCAL_REPORTED (relayed by owner)** until the worktree, diff and test artifacts are independently inspected. This section does not imply that ChatGPT inspected the local files.

### 12.1 Offline implementation reported

- Worktree: `C:/temp/IABV_BIO04_learning_provenance_20261016`.
- Branch reported: `codex/iabv-learning-provenance-20261016`.
- HEAD reported: `d1a55897bf7f758914b8237d48ae43f245f06592`; no commit and no push.
- 21 files modified; report states +952 / -54 lines.
- Scope reported: domain models, persistence/database, ToolRecordRepository, ToolMemory, interaction learning, selector, ToolTeachService, ToolOperationalExecutor, TaskOutcomeRecorder and direct consumers.
- Semantics reported: separate preparation evidence (including sandbox and human teaching) from operational outcomes; selector no longer treats sandbox success as task resolution; operational outcomes that require a postcondition wait for an attributable verified receipt; identities for task, attempt and result remain distinct; contribution ledger deduplicates repeated processing; historical aggregates are retained but marked unattributable and excluded from selector operational reliability.
- Verification reported: 35 focused tests passed with 30 deselected; 18 tests in `test_verified_operational_outcome_seams.py` passed; AST parsing of 21 affected Python files and `git diff --check` passed. No product runtime or external integration executed. The relationship between the two stated test counts must be preserved as reported rather than silently added together.
- Residual data: after an interrupted earlier test run, the isolated worktree contains an untracked `data/` directory with 92 files. Contents and exact provenance were not inspected; none were deleted. Do not bulk-add, publish or delete them until their origin and necessity are established.
- Source BIO-04 worktree and the dirty canonical `C:/Python` were reportedly not intentionally modified.

### 12.2 Unresolved atomicity risk

The contribution ledger, aggregate counters and related artifacts are not updated in one atomic transaction. A process interruption between those operations could leave a partially projected state. Deduplicating a repeated contribution does not, by itself, repair a partially completed update.

**UNPROVEN:** crash consistency and recovery/reconciliation. Do not claim exactly-once semantics or recovery guarantees until the persistence boundary, transaction scope, failure injection and restart behavior are established.

A valid next technical step is to define whether the contract requires crash recovery; then inspect existing SQLite transaction facilities and the JSON/SQLite dual-write pattern. Prefer an atomic authoritative ledger with rebuildable projections or another minimal design proven compatible with current repository contracts. Do not assume a cross-file/filesystem/SQLite transaction exists.

### 12.3 New coordination objective: autonomous, gated agent loop

The owner's goal is to reduce repeated manual prompting and have Codex keep progressing until the system genuinely needs owner authorization. Treat this as an engineering objective, not proof that ChatGPT's active conversation can call a local Codex process.

Target protocol:
1. A durable task ledger with unique task ID, objective, current phase, source/base SHA, lease/owner, attempt count, status, last artifact, last error, and explicit stop reason.
2. Append-only agent messages with sender, recipient, task ID, timestamp, evidence refs, requested action and response correlation ID. Avoid overwrite-only shared notes that erase provenance.
3. A shared evidence/artifact location in GitHub for reports and diffs, with status transitions such as `READY`, `IN_PROGRESS`, `NEEDS_REVIEW`, `NEEDS_OWNER`, `BLOCKED`, `DONE`; every transition records an actor and evidence.
4. A Codex loop that reads the task ledger, claims only authorized work, performs a bounded step, verifies the result, writes an artifact/message and loops again while permitted work remains.
5. Event-triggered independent reviews (for example, a Draft PR or explicit review request) for the second agent; do not let reviewer and implementer silently share one unreviewed conclusion.
6. Idempotent dispatch, bounded retries/backoff, timeouts, loop/run budgets, lock/lease expiry, structured error reports, no recursive spawning without limits, and no automatic merge.
7. Explicit human gates for secrets/credential setup, unreviewed external spend, destructive actions, runtime/physical bridge activation, access to M0A, production execution, branch protection changes, and unresolved product semantics.
8. The active ChatGPT conversation may coordinate through the connected GitHub files when a turn is active; it must not be described as a continuously running worker. A scheduled/API-based OpenAI agent is a separate model process and credential scope, not the same identity or live hidden context as this particular ChatGPT conversation.

### 12.4 What to prove before calling the agents “connected”

- Verify the actual Codex CLI invocation and permissions in the local environment; do not assume it can safely modify any worktree simply because it can access the machine.
- Establish a supported execution route for each worker: Codex CLI, Claude Code, and OpenCode/Kilo. Confirm model/provider identity, authentication source, data handling and whether unattended execution is supported.
- Establish the bridge from the current ChatGPT conversation to the shared mailbox via the connected GitHub integration. This bridge is turn-driven; it does not provide continuous ChatGPT availability.
- If using GitHub Actions, inspect current workflows first, then propose a least-privilege event-driven workflow. API credentials must be configured by an authorized owner in repository/environment secrets; never request the secret value in chat or commit it to the repository.
- Perform a safe handshake test using a harmless nonce/task ID: each configured worker must acknowledge the same task ID, preserve a correlation ID, and return a verifiable artifact/commit or explicit unavailable status. No product/runtime/physical effects are permitted in this handshake.
- Demonstrate a failure case (missing credentials, worker offline, timeout) that transitions to `NEEDS_OWNER` or `BLOCKED` rather than spinning indefinitely or fabricating success.
- Only after all checks pass may the report claim which agents are truly connected, and through what exact channel.

### 12.5 Autonomous continuation instruction

Continue from Sections 10–12; do not restart BIO-04 or Candidate C. First inspect the actual 21-file diff and the 92-file untracked data directory **without deleting or bulk-adding anything**. Verify the test commands/results and the current worktree branch/HEAD/status. Resolve whether the atomicity contract is required from existing project requirements; if it is not specified, present the narrow decision to the owner rather than inventing one.

In parallel, design the agent-continuity control plane described above. Inspect the repository for existing agent instructions, MCP configuration, workflows, CLI wrappers and safe task dispatch before adding new infrastructure. Do not commit the 21-file implementation until the untracked data's provenance is understood and the diff/test claims are reconciled. Do not create workflows that assume unavailable secrets or claim direct access to this live ChatGPT conversation. Prefer a small, testable proof of channel connectivity over broad speculative infrastructure.

Autonomous loop policy: continue each safe, read-only or already authorized engineering step without asking the owner after every routine operation. On each iteration, update durable task status, record evidence, check remaining authorized work and either continue or stop with a specific blocker. Stop and request the owner only for the explicit gates above, a product-semantic decision, a missing credential/permission, an irreconcilable source-provenance conflict, or a risk outside this authorization.

**Governance:** `KEEP_BLOCKED`. The offline code change remains reported but uncommitted/unpushed and not independently reviewed here. Runtime behavior, crash recovery, cross-agent handshake, and operational efficacy remain **UNPROVEN**. No M0A access, runtime execution or physical-bridge activation is authorized by this memory.
