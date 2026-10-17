# IABV — Addendum de continuidad: revisión posterior del gate operacional

**Corte:** 2026-10-16, America/Bogota  
**Gobierno:** `GOVERNANCE = KEEP_BLOCKED`  
**Naturaleza:** addendum de continuidad y planificación de auditoría; no es contrato normativo, verificación independiente ni autorización de implementación/runtime.  
**Relación:** complementa `2026-10-16_iabv_agent_continuity_space_time.md`; conserva intactos los informes y decisiones anteriores.

## 1. Procedencia y nivel de confianza

### Resultado recibido

El propietario compartió una nueva salida de Codex con etiqueta `RECOMMENDATION_OPERATIONAL_GATE_MAP_COMPLETE`. Codex declara:

- checkout: `C:\\temp\\IABV_coordination_20261016`;
- rama: `codex/iabv-agent-coordination-20261016`;
- HEAD: `3926b1144bb23c1066db579da711d3cdbc1611df`;
- 96 rutas rastreadas modificadas;
- dos nombres bajo `data/` visibles como no rastreados; Codex declara que no leyó sus contenidos ni accedió a SQLite;
- checkpoint local declarado: `C:\\Users\\faber\\.codex\\visualizations\\2026\\10\\16\\01a146cd-2a68-78c3-819f-a4cc90940058\\IABV_recommendation_operational_gate_map_20261016_followup.md`.

**Clasificación de procedencia:** `OWNER_REPORTED` para el informe pegado en la conversación; `CODEX_LOCAL_REPORTED` para sus observaciones locales. Este addendum no abre el checkpoint en Windows ni verifica de forma independiente la rama, HEAD, working tree, líneas de código o estado de `data/`.

Codex declara expresamente que esta revisión continúa en el mismo contexto, no es independiente y no revisó integralmente los 96 diffs. No elevar este resultado a auditoría completa.

## 2. Hallazgo causal acotado

Codex informa que el spot-check del código respalda este límite:

1. Hay filtros para asesoría consultiva explícita.
2. No se exige una clase operacional positiva para cada recomendación y para cada registro de soporte en todas las rutas relevantes revisadas.
3. En una ruta de sandbox, bajo ciertos blockers y si hay una alternativa disponible, puede producirse una promoción persistida como `success=True` sin que el código revisado demuestre que esa alternativa se ejecutó.
4. La evidencia comunicada llega a escrituras locales de outcomes. No demuestra que haya ocurrido una ejecución operacional atribuible, que una postcondición se haya verificado ni que exista recuperación automática.

**Alcance exacto:** este es un resultado estático reportado, no una demostración de runtime. «La ruta inspeccionada no demuestra ejecución» no equivale a «se ha probado que ninguna ruta ejecute la herramienta». La auditoría adversarial debe buscar explícitamente una ruta alternativa o un control omitido que refute la hipótesis.

## 3. Conciliación con informes locales anteriores

La memoria de continuidad conserva informes anteriores sobre filtros que exigen `evidence_class='operational_execution'` en consumidores concretos —incluidos recorridos de `TaskContextAssembler`, `adaptive_task_orchestrator` y `TaskOutcomeRecorder`— y, por separado, un reporte de que el repositorio de recomendaciones no exige esa clase positiva para cada recomendación y cada run de soporte.

No tratar automáticamente esos reportes como contradicción: pueden describir fronteras distintas (filtro consumidor frente a creación/promoción/soporte de recomendación). Pero tampoco asumir que se complementan correctamente. La siguiente revisión debe mostrar la ruta concreta, el punto donde se aplica cada filtro, los datos que inspecciona y si el filtro es obligatorio antes de cada efecto relevante.

## 4. Evidencia requerida para cerrar el mapa causal

El siguiente informe debe citar archivos, símbolos y líneas exactas, además de productor, transformación, persistencia y consumidores:

- **Origen:** qué objeto o recomendación procede de sandbox/ranking y bajo qué blockers.
- **Promoción:** cuál es la condición precisa para elegir la alternativa y qué significa semánticamente «promovida».
- **Éxito:** sitio exacto que asigna `success=True`, predicados que lo habilitan y si significa propuesta, validación, ejecución o postcondición.
- **Ejecución:** llamada real al ejecutor, identificador del intento, argumentos, resultado devuelto y enlace durable al outcome. La mera disponibilidad de una alternativa no es evidencia de ejecución.
- **Postcondición:** comprobación concreta, autoridad de su resultado y persistencia del resultado verificado.
- **Persistencia:** repositorio/método, campos escritos, orden relevante y fallos parciales posibles, sin inspeccionar `data/` ni SQLite.
- **Consumo downstream:** todas las rutas encontradas que rankean, recomiendan, registran aprendizaje o alimentan `ToolMemory`, `InteractionLearningService` o `InteractionModeSelector`.
- **Gates de evidencia:** para recomendación y para cada run/artefacto de soporte, localizar quién impone la clase operacional positiva, cómo se comprueba y qué ruta queda si falta, es vacía o desconocida.
- **Falsadores:** una ruta que sí ejecute la alternativa y verifique postcondición; una barrera de persistencia anterior al éxito; un consumidor que requiera evidencia atribuible completa y haga imposible que el resultado sospechoso cambie una decisión futura.

Si no se puede demostrar una arista, etiquetarla `GAP`/`UNPROVEN`, no inferirla por nombres de clases ni por comentarios.

## 5. Distinciones semánticas que deben mantenerse

No colapsar estos estados en un único booleano:

1. recomendación propuesta;
2. validación sandbox;
3. herramienta realmente ejecutada;
4. resultado de ejecución atribuido a un intento;
5. postcondición verificada;
6. outcome persistido con procedencia;
7. evidencia elegible para ranking/aprendizaje;
8. resultado que modifica una futura selección de modo.

Estos son ejes analíticos para seguir la implementación; no se afirma que todos estén formalizados como contrato en el repositorio. Un `success=True` aislado no demuestra los estados 3–8.

## 6. Metodología de la próxima ronda

### A. Codex: extraer evidencia sin editar

Abrir y leer el checkpoint local citado arriba y producir un anexo de referencias verificables para la ruta exacta. Indicar qué afirmaciones se comprobaron en esta sesión, cuáles provienen de notas anteriores y cuáles aún no están trazadas. No repetir la auditoría completa de los 96 diffs.

Antes de continuar, reconfirmar raíz, rama, HEAD y estado del checkout en modo de solo lectura. No limpiar ni alterar cambios y no abrir los contenidos de `data/`. Si el checkout difiere del declarado, detenerse y registrar la diferencia.

### B. OpenCode/Kilo: refutación independiente y acotada

Usar el mapa con rutas/símbolos de Codex como objeto de contraste, no como verdad asumida. Buscar rutas de ejecución real, comprobaciones de postcondición y filtros positivos de procedencia que el mapa pudiera omitir. Devolver evidencia en contra y a favor.

Antes de enviar contexto local a un proveedor de modelo, revisar la ruta/modelo y sus condiciones de datos. No transmitir secretos, `.env`, SQLite ni los contenidos de `data/`. Si el proveedor no puede inspeccionar el checkout sin ampliar indebidamente la transmisión de archivos, limitar el análisis a los archivos y fragmentos estrictamente pertinentes.

### C. Reconciliación

Comparar afirmación por afirmación y resolver las diferencias mediante código y referencias, no por votación entre modelos. Mantener separadas las categorías:

- `PROVEN_BY_SOURCE`: referencia primaria revisada con ubicación exacta;
- `CODEX_LOCAL_REPORTED`: resultado local del agente que aún no se reprodujo aquí;
- `OWNER_REPORTED`: información aportada por el propietario;
- `PROPOSED`: explicación o reparación aún no aceptada;
- `UNPROVEN`: comportamiento que no quedó demostrado.

El análisis estático puede proponer un cambio mínimo; no puede certificar ejecución real ni recuperación automática.

## 7. Decisión técnica provisional

Si la revisión adversarial confirma la brecha, preparar —sin implementar todavía— un cambio mínimo que impida que una promoción de sandbox sea elegible como éxito operacional aprendido sin, al menos, ejecución atribuible y postcondición verificada. Antes de elegir el punto de enforcement, demostrar todos los productores y consumidores relevantes para evitar un filtro local que deje una ruta alternativa.

No diseñar todavía una nueva máquina de estados ni prometer `exactly-once`, atomicidad o recuperación automática sin evidencia y decisión contractual.

Después de acordar el diff mínimo, solicitar autorización específica para editar y autorización separada para ejecutar las pruebas discriminantes pertinentes. Claude Code, cuando vuelva a estar disponible, revisará el mapa reconciliado y el diff acotado; no reiniciará BIO-04 ni R10.

## 8. Límites que continúan vigentes

- Los 96 archivos/rutas modificadas siguen preservados; no se ha establecido que todos pertenezcan a esta tarea.
- Los nombres no rastreados en `data/` no se abrieron; sus contenidos y relación con el cambio permanecen desconocidos.
- No se ejecutaron pruebas, builds, código de producto ni runtime en la revisión descrita.
- No se ha demostrado la cadena completa `sandbox → ToolMemory → InteractionLearningService → InteractionModeSelector`.
- Candidate C no queda aprobada por este resultado. Las PR #465 y #466 siguen sujetas a sus gates documentales y decisiones del propietario.
- No acceder a M0A, no iniciar el puente físico ni activar efectos automáticos.
- Mantener `GOVERNANCE = KEEP_BLOCKED`.

**Siguiente checkpoint esperado:** evidencia causal con líneas exactas + intento explícito de refutación por Kilo/OpenCode + reconciliación de diferencias. Detenerse antes de editar código o ejecutar pruebas.


## 9. 2026-10-16 — Primera respuesta de Kilo Gateway en VS Code

**Proveniencia:** `OWNER_REPORTED`; transcripción de la salida del agente Kilo compartida por el propietario. No constituye verificación independiente por este documento.

### Entorno y conducta observados

- El propietario aclara que usa Kilo Gateway como extensión de VS Code y menciona una ruta/configuración `Auto Free`. Esto se registra como configuración reportada, no como verificación del modelo o proveedor realmente seleccionado en la sesión.
- El texto de continuidad menciona por separado opciones de OpenCode (DeepSeek V4.1 Flash Free, MiMo-V2.6-Flash Free, Nemotron 3.5 Lightning Free y Muse Spark 1.3 Free). No hay evidencia suficiente en este reporte para identificar qué agente/modelo de OpenCode está activo en otra sesión ni si estas opciones están disponibles ahora. No inferir la configuración de OpenCode a partir de la de Kilo.
- Kilo verificó según su salida la raíz `C:/temp/IABV_coordination_20261016`, HEAD `3926b1144bb23c1066db579da711d3cdbc1611df` y rama `codex/iabv-agent-coordination-20261016`.
- Kilo no encontró el checkpoint `IABV_recommendation_operational_gate_map_20261016_followup.md` dentro del checkout al usar búsquedas por patrones y recorrer ese árbol. La conclusión admisible es **NOT_FOUND_IN_CHECKOUT**. Esto no demuestra que el archivo no exista en otra ubicación del disco: el path citado por Codex se encuentra bajo el directorio de usuario y fuera del repositorio, y el texto de Kilo no demuestra haber leído esa ruta absoluta.
- Kilo informó 97 rutas con estado `M`, frente a las 96 rutas rastreadas informadas antes por Codex. Confirmó además dos rutas no rastreadas bajo `data/`, ambas SQLite, y declaró no haber abierto sus contenidos ni SQLite. La variación 96/97 queda como **UNRESOLVED**: requiere comparar las salidas de `git status --short` y `git diff --name-only` antes/después y comprobar si un cambio adicional preexistía o apareció durante la sesión. No contar líneas de salida como archivos sin corroborar la lista de rutas.
- Kilo reconoció el límite de preservación y no indicó haber editado archivos, ejecutado pruebas o leído las bases SQLite. No elevar esta afirmación a una atestación externa: es el propio informe del agente.

### Evaluación del comportamiento de Kilo

**Observaciones favorables reportadas:** identificó el checkpoint ausente en el workspace, mantuvo separados los dos archivos SQLite y no inventó símbolos a partir del checkpoint no recuperado; registró la identidad del checkout antes de proseguir.

**Límite/procedimiento por mejorar:** el prompt ya permitía continuar el análisis del código en el HEAD declarado sin el checkpoint, marcando las referencias no recuperadas como tales. Por ello Kilo no necesita bloquear toda la investigación ni pedir al propietario que copie manualmente código. Debe continuar con el source disponible en el checkout, buscar el recorrido de forma autónoma y marcar explícitamente cada hallazgo como `HEAD_SOURCE`, `WORKTREE_SOURCE`, `NOT_FOUND` o `UNPROVEN`. Debe inspeccionar el checkpoint por su ruta absoluta fuera del repositorio solo si el acceso está autorizado y el archivo está realmente disponible; no declarar su inexistencia global basándose solo en un glob del workspace.

**Configuración de agente/modelo:** una extensión/agente (Kilo en VS Code), el modo de enrutamiento (`Auto Free`), el proveedor y el modelo concreto son capas distintas. Registrar la selección observable en la UI antes de comparar su comportamiento; no asumir que `Auto Free` equivale a DeepSeek ni que Kilo y OpenCode son la misma sesión.

## 10. Próxima instrucción a Kilo — continuar sin pedir datos manuales

La siguiente acción es que Kilo prosiga con el análisis estático del checkout ya identificado, sin depender del checkpoint ausente. No debe inspeccionar `data/` ni SQLite, ni modificar los archivos. Para resolver 96/97, registrar solo nombres y estados de rutas sin leer los archivos no rastreados; comparar el estado al inicio y al final, sin intentar limpiar los cambios.

Debe producir referencias de source exactas para promoción sandbox → asignación de `success=True` → persistencia → consumidores de ranking/aprendizaje, y buscar activamente una ruta real de ejecución atribuible y verificación de postcondición. Toda evidencia se separa por HEAD frente a working tree. Si no puede demostrar una arista, declarar `GAP`; no pedir al propietario fragmentos manuales mientras exista un camino local autorizado para la inspección.

El informe sigue siendo una continuación no independiente hasta que exista una revisión adversarial centrada en las mismas referencias y que documente falsadores concretos.

**Gobierno:** `KEEP_BLOCKED`. Sin edición de código, tests, builds, runtime, operaciones en M0A ni activación del puente.
