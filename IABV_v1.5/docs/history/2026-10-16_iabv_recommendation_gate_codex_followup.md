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


## 11. Nota de configuración de modelos/agentes, contrastada con documentación oficial

**Fuentes consultadas el 2026-10-16:**

- Kilo, “Using Kilo for Free”: https://github.com/Kilo-Org/kilocode/blob/main/packages/kilo-docs/pages/getting-started/using-kilo-for-free.md
- Kilo, “Auto Model”: https://kilo.ai/docs/code-with-ai/agents/auto-model
- Kilo, selección de modelo/agente en VS Code: https://github.com/Kilo-Org/kilocode/blob/main/packages/kilo-docs/pages/code-with-ai/agents/model-selection.md
- OpenCode, catálogo de modelos: https://dev.opencode.ai/v2/docs/console/models/

### Distinciones operativas

- **Herramienta/superficie:** Kilo Code como extensión de VS Code; OpenCode como entorno/agente distinto; Codex CLI como agente local que produjo los informes citados.
- **Modo/agente:** define el rol o tipo de tarea (por ejemplo, Code o Plan en Kilo); no es el modelo ni el proveedor.
- **Modelo/ruta:** `kilo-auto/free` es un tier de enrutamiento dinámico hacia modelos gratuitos disponibles, no un modelo base fijo. Kilo documenta que las rutas cambian según capacidad y disponibilidad del proveedor.
- **Proveedor de inferencia:** puede cambiar bajo una ruta automática. No deducir privacidad o capacidad a partir del nombre “Auto Free”; confirmar la ruta/modelo mostrado para la sesión si la UI lo expone.
- **Datos:** la documentación oficial de Kilo advierte que Auto Free puede usar proveedores que registran prompts y salidas y los utilizan para mejorar sus servicios, y cita en particular endpoints gratuitos de NVIDIA con restricciones de no enviar datos personales o confidenciales. Por tanto, no usar Auto Free con código privado, secretos, credenciales, `.env`, datos reales o contenido sensible sin una ruta explícitamente adecuada.
- **OpenCode:** es un catálogo y una ruta de proveedor separados. En el listado consultado aparecen DeepSeek V4.1 Flash Free, MiMo-V2.6-Flash Free, Nemotron 3.5 Lightning Free y Muse Spark 1.3 Contributor Free. El propio catálogo advierte que varias de estas ofertas gratuitas son temporales; confirmar el identificador y las condiciones actuales en el selector al comenzar la sesión.
- La documentación consultada indica que OpenCode declara zero-retention/no-training para la ruta específica de DeepSeek V4.1 Flash Free, mientras que varias ofertas free de otros modelos se describen como temporales destinadas a recoger feedback/mejorar el modelo. No extrapolar la política de una ruta a otro modelo ni a Kilo Auto Free.

### Registro de capacidad observado hasta ahora

| Superficie | Capacidad reportada/observada | Limitación conocida en esta tarea |
|---|---|---|
| Codex CLI local | Confirmó checkout/HEAD/status y produjo un mapa estático de la ruta gate/outcome | Su propia nota dice que la revisión follow-up no fue independiente y no abarcó los 96 diffs completos |
| Kilo en VS Code, Auto Free reportado por propietario | Encontró el estado del checkout, respetó la restricción sobre los dos SQLite no rastreados y no inventó referencias cuando no halló el checkpoint dentro del árbol | En la respuesta compartida no llegó a entregar un mapa de llamadas completo; la búsqueda relativa no demuestra que el checkpoint fuera inexistente fuera del workspace. No se ha comprobado qué modelo/proveedor subyacente respondió a la sesión |
| OpenCode | El propietario reportó las cuatro opciones de modelo citadas arriba como disponibles/opciones en otro contexto | No está verificado cuál está configurado o seleccionado actualmente, si usa un modo/agent específico, ni si el catálogo de la sesión coincide con la documentación consultada |
| Claude Code/Pro | Revisor adversarial previsto cuando vuelva a estar disponible | No se ha realizado todavía esa revisión del mapa operacional |

### Regla práctica

Para cada tarea importante, registrar: producto/extensión, modo/agente, ID exacto del modelo o tier, proveedor conocido, acceso real al checkout, alcance de lectura, permisos de escritura, salida entregada, si la revisión fue independiente y errores/limitaciones. La palabra “agente” por sí sola no identifica esas capas.

**Aplicación inmediata:** permitir a Kilo seguir con la inspección estática de los archivos relevantes del checkout identificado aunque el checkpoint esté ausente del workspace; el propio prompt autoriza la inspección del código. Mantener el checkpoint como `NOT_FOUND_IN_CHECKOUT`, no `NOT_FOUND_ON_DISK`. No enviar los archivos `data/*.sqlite` ni el repositorio indiscriminadamente al proveedor Auto Free.


## 12. 2026-10-16 — Catálogos free observados por el propietario: OpenCode y Kilo VS Code

**Proveniencia:** `OWNER_REPORTED`. Las listas siguientes se copiaron de las respuestas de OpenCode y Kilo compartidas por el propietario. No son una enumeración API verificada independientemente y su disponibilidad puede cambiar. La documentación oficial de Kilo confirma que `kilo-auto/free` enruta dinámicamente y que el catálogo subyacente cambia; además advierte que algunos proveedores pueden registrar prompts y respuestas y usarlos para mejorar sus servicios. Referencias consultadas:
- https://kilo.ai/docs/code-with-ai/agents/auto-model
- https://kilo.ai/docs/code-with-ai/agents/model-selection
- https://dev.opencode.ai/v2/docs/console/models

### OpenCode — modelos que el selector/respuesta compartida reportó como free

| Modelo mostrado | Variantes reportadas | Uso posible en IABV (propuesta, no benchmark verificado) |
|---|---|---|
| `LL Alpha Free` | low / medium / high / xhigh / max | Contraste de código si el endpoint y el contexto admiten la tarea; no inferir capacidad a partir del nombre. |
| `Nemotron 3.5 Super VL Free` | none / minimal / low / medium / high / xhigh | Tareas de texto+código y, cuando la entrada por imagen está habilitada, capturas de UI. No hace falta para la refutación puramente textual actual. |
| `Beam Free` | low / medium / high / xhigh / max | Posible auditor de razonamiento si este ID coincide con la opción seleccionada; no asumir que es el mismo despliegue que Kilo `Reflection: Beam 1.0`. |
| `LongCat 2.5 Preview Free` | no indicadas | Opción experimental secundaria; no prioridad para el gate crítico. |
| `Space Bunny Free` | low / medium / high / xhigh / max | Reserva; no hay evidencia comparativa en esta sesión para preferirlo. |
| `MiMo-V2.6-Flash Free` | no indicadas | Tarea auxiliar o segunda opinión si está habilitado; revisar su tratamiento de datos. |
| `DeepSeek V4.1 Flash Free` | low / high / max | Candidato para una segunda revisión de código y causalidad. La página de OpenCode consultada describe esta ruta concreta como zero-retention/no-training; confirmar que el identificador seleccionado corresponda a esa ruta exacta. |
| `Muse Spark 1.3 Free` | minimal / low / medium / high / xhigh | Redacción/documentación auxiliar; OpenCode describe la opción Contributor Free como destinada a recoger feedback y mejorar el modelo. No usar para código sensible sin evaluación de privacidad. |
| `GLM-5.3-Flash Free` | low / high / max | Alternativa rápida si los anteriores no están disponibles; no hay comparación empírica local registrada. |
| `Big Pickle` | no indicadas | Legacy/alternativa residual según la respuesta; no seleccionarlo para esta auditoría si hay opciones actuales mejor identificadas. |

La respuesta de OpenCode mostró timestamps numéricos como fechas de disponibilidad. No interpretarlos como fechas de lanzamiento, calidad o vigencia más allá de lo que el selector explique.

### Kilo Code en VS Code — opciones free que reportó Kilo

| Nombre mostrado | Proveedor/variantes según la respuesta recibida | Uso propuesto |
|---|---|---|
| `Auto Free` | `kilo`; enrutador dinámico | Tareas rutinarias, inspección general y exploración no sensible. La ruta subyacente puede cambiar y su política depende del proveedor al que enrute. |
| `Auto Efficient` | `kilo`; enrutador dinámico | Rutina/eficiencia si el usuario confirma que aparece como free en la cuenta actual; no asumir equivalencia con `kilo-auto/efficient`, que la documentación pública actualmente describe como tier de pago, sin comprobar el ID del selector. |
| `NVIDIA: Nemotron 3.5 Super VL` | `instant`, `thinking` | Análisis de capturas y tareas multimodales, siempre que el modelo seleccionado acepte la modalidad de imagen. No es la primera elección para el gate de solo código. Considerar la advertencia de datos para endpoints free de NVIDIA. |
| `Reflection: Beam 1.0` | low / medium / high / xhigh / max | Primera opción propuesta para intentar refutar la ruta causal del gate operacional porque Kilo lo muestra con variantes de razonamiento y lo recomienda para crítica adversarial. La ventaja de calidad no ha sido medida independientemente aquí. |
| `Stealth: Glyph Cluster` | low / medium / high / xhigh | Alternativa de contraste si Beam no está disponible o alcanza límites; su supuesta menor capacidad es una valoración del agente/model picker reportada, no un benchmark independiente. |

Kilo informó “331 modelos, solo 5 free”, pero la frase “4 listados arriba + Auto Efficient/Auto Free” no concuerda aritméticamente con los cinco renglones visibles (tres modelos con nombre + dos enrutadores). Registrar el detalle real de la UI y su ID de modelo, en vez de repetir ese total como hecho establecido.

### Matriz vigente de selección de agentes

1. **Codex CLI local — fuente primaria de evidencia de checkout.** Inspecciona los archivos en su contexto local y aporta referencias concretas. Sus conclusiones deben etiquetarse por HEAD/working tree; un resultado etiquetado `COMPLETE` no sustituye una revisión independiente.
2. **Kilo Code + Reflection: Beam 1.0, variante `high` inicialmente o `max` si se necesita una pasada adversarial más profunda.** Para la tarea actual, continuar en la misma sesión y workspace ya identificado, con herramientas limitadas a lectura. Elegir un modelo fijo mejora la reproducibilidad frente a Auto Free, aunque no prueba mayor calidad. No configurar ni ejecutar agentes secundarios que puedan escribir al repositorio.
3. **OpenCode + DeepSeek V4.1 Flash Free, variante `high` o `max`**, como contraste independiente enfocado en los mismos símbolos/afirmaciones una vez se cuente con referencias concretas. Si se busca minimizar el riesgo de transmitir código local sin revisar políticas, reducir el contexto a los archivos y fragmentos necesarios. No enviar el árbol entero ni secretos. El modelo `Beam Free` de OpenCode no debe considerarse idéntico a `Reflection: Beam 1.0` de Kilo únicamente por el nombre.
4. **Nemotron 3.5 Super VL** se reserva para una pregunta que realmente dependa de screenshots/UI. El gate actual es de causalidad en código; la capacidad VL no aporta una ventaja evidente en esta iteración.
5. **Claude Code/Pro al regresar**: revisión final de las diferencias entre Codex y Kilo/OpenCode, centrada en falsadores y en el diff mínimo propuesto.

### Próxima acción recomendada

No pedir a Kilo que configure un agente mediante una API inventada. El propietario debe seleccionar manualmente en el selector visible `Reflection: Beam 1.0` y variante `high` (usar `max` si hace falta), conservando la sesión/workspace actual. Dar continuidad al prompt de refutación: el checkpoint ausente no impide seguir la inspección de source. La selección exacta debe anotarse con lo que muestre la UI.

Kilo debe producir referencias concretas; OpenCode debe intentar refutarlas, no rehacer la auditoría general. Si la inspección de archivos de trabajo pudiera transmitir cambios privados a un proveedor free, detener el envío de esos archivos y analizar únicamente source publicado o fragmentos mínimos autorizados.

Toda recomendación anterior es una asignación de tarea basada en herramientas reportadas, no un benchmark formal ni una certificación de privacidad. Conservar `GOVERNANCE = KEEP_BLOCKED`, no editar código, no ejecutar pruebas/runtime y no activar el puente físico.


## 13. 2026-10-16 — Kilo: refutación estática del gate operacional de recomendaciones

**Proveniencia:** `OWNER_REPORTED` para la transcripción recibida; los detalles locales se clasifican como `KILO_LOCAL_REPORTED` hasta que otro proceso los reproduzca. Kilo recorrió source en una sesión distinta pero sobre el mismo checkout/working tree de Codex: es revisión por segundo agente, no independencia de entorno ni validación de runtime.

### Checkout y preservación comunicados

- Raíz: `C:\\temp\\IABV_coordination_20261016`; rama `codex/iabv-agent-coordination-20261016`; HEAD `3926b1144bb23c1066db579da711d3cdbc1611df`.
- `git status --porcelain=v1`: 97 entradas; `git diff --name-only`: 96 rutas unstaged; `git diff --cached --name-only`: 0.
- Reconciliación comunicada: 96 rutas modificadas más una entrada `?? data/` no rastreada, dentro de la cual aparecen dos SQLite. Kilo indica que no leyó, abrió ni hash-eó las bases.
- El checkpoint externo `IABV_recommendation_operational_gate_map_20261016_followup.md` fue encontrado mediante su ruta absoluta de usuario y leído (61 líneas), según Kilo. La búsqueda previa dentro del checkout no lo encontró. No confundir `NOT_FOUND_IN_CHECKOUT` con `NOT_FOUND_ON_DISK`.
- No ejecutó tests/build/runtime, según su reporte.

La reconciliación 96/97 queda explicada por Kilo pero continúa local-reportada hasta reproducir las listas de rutas. Preservar todas las modificaciones; no limpiar ni inspeccionar SQLite.

### Mapa causal comunicado

| Etapa | Referencia local informada | Hallazgo |
|---|---|---|
| Recomendaciones | `experiment_lab_repository.py:155-210` | `list_recommendations` excluye ciertos casos consultivos explícitos, runs de soporte faltantes y dominios/ suites específicos; no exige clase positiva `operational_execution` en cada recomendación/run. La parte nueva existe en working tree, no en HEAD. |
| Propuesta | `tool_evolution_monitor.py:701-748` | `_proposal_from_discovery_signal` genera una propuesta `validate_discovery` con siguiente acción sandbox; no filtra evidencia operacional. |
| Candidato | `autonomous_validation_cycle.py:1811-1826` | Selecciona subjects con prefijo `sandbox:` y omite algunos ya validados por `learning_source='sandbox_experiment'`; no aplica clase de evidencia en la ruta descrita. |
| Validación/promoción | `sandbox_experiment_service.py:20-118` | Con blockers en baseline y una alternativa de `ranked_configurations`, `validate_recommendation` asigna `verdict=VALID`, `promote=True`, `status='promoted'`; no se encontró llamada a ejecutor ni verificación de postcondición en esa ruta. |
| Run sandbox | `sandbox_experiment_service.py:120-158` | `success` se deriva de `verdict in {VALID, DOUBTFUL}`; se persiste `learning_source='sandbox_experiment'` sin `evidence_class`. |
| Run promoción | `sandbox_experiment_service.py:160-193` | `_record_promotion` fija `success=True`, `learning_source='sandbox_promotion'` y `suite_name='sandbox_promotion'`, sin `evidence_class`. |
| Persistencia y regeneración | `experiment_lab.py:160-265` | `record_outcome` guarda metadata del run y luego llama a `strategy_selector.recommend`/`save_recommendation`. Kilo no encontró inyección positiva de clase operacional. |
| Consumidores de éxito | `strategy_selector.py:67-71`; `adaptive_weight_layer.py:112,128`; `experiment_lab.py:270-271,417,484-485` | Se usa `run.success` para seleccionar claves exitosas, computar pesos adaptativos, bonus de reutilización y métricas, sin filtrar `evidence_class` en los fragmentos revisados. |

### Controles parciales identificados

- `task_outcome_recorder.py:468-479`: exige `evidence_class == 'operational_execution'` para insights operativos.
- `task_context_assembler.py:1095-1119`: insights/trazas exigen clase operacional y predicados adicionales de verdict/estado/flags.
- `experiment_lab_repository.py:196-200`: excluye recomendaciones sin `supporting_run_ids`.
- `autonomous_validation_cycle.py:1823-1826`: deduplica ciertos subjects con runs sandbox existentes.
- El working tree añade exclusión de advisory explícito, pero no modifica `sandbox_experiment_service.py` ni los consumidores de `run.success` citados.

Estos controles pertenecen a fronteras distintas; no equivalen a una validación global de evidencia operacional.

### Dictamen calibrado

La formulación inicial de Kilo sobre “refutar parcialmente” es imprecisa. Los detalles expuestos **CORROBORAN estáticamente** el riesgo central; no lo refutan. Lo no resuelto es el comportamiento runtime y la cadena real observada de extremo a extremo. La ruta reportada puede escribir `success=True` sin demostrar ejecución atribuible ni postcondición; consumidores posteriores pueden usar `run.success` sin comprobar clase en el source revisado.

Afirmaciones de Kilo:
- A1: `list_recommendations` no exige clase operacional positiva — `CORROBORATED` por el source citado según Kilo.
- A2: blockers + alternativa pueden promover desde ranking sin ejecutar — `CORROBORATED` estáticamente en la ruta citada.
- A3/A4: la persistencia escribe success sin clase operacional — `CORROBORATED` según source revisado.
- A5: existen filtros positivos en consumidores adaptivos — `CORROBORATED`, pero de cobertura local.
- A6: esos filtros no cubren los consumidores de laboratorio citados — `CORROBORATED` en los fragmentos identificados.
- A7: existe otra ruta llamada desde la validación sandbox que ejecute, atribuya y verifique antes de promover — `UNRESOLVED/GAP`; Kilo no encontró esa arista.
- A8: outcome sandbox puede reentrar a ranking — `CORROBORATED` por las llamadas reportadas; efecto observado en runtime permanece `UNPROVEN`.
- A9: reconciliación automática segura — `NOT_RECOVERED`.
- A10: working tree ya corrige la brecha operacional — `REFUTED` para las rutas revisadas; el diff reportado añade filtro consultivo, no gate positivo.

### Cuidado con la reparación sugerida por Kilo

La propuesta no está aprobada y no debe implementarse literalmente todavía:

1. Kilo dice “punto único de entrada” en `_record_promotion`, pero también propone cambios en `strategy_selector`, `adaptive_weight_layer` y `experiment_lab._reuse_bonus`. No es un punto único; es defensa en origen más filtros en consumidores.
2. No inyectar `evidence_class='operational_execution'` genéricamente desde `record_outcome` porque el caller diga ser operativo. La clase debe basarse en evidencia verificable de ejecución atribuida y postcondición, no en una etiqueta.
3. No decidir aún que outcome de sandbox debe volverse `success=False`, ni introducir `learning_source='sandbox_observed'` como vocabulario contractual sin revisar esquema, semántica y consumidores. Podría necesitar separación explícita entre veredicto sandbox y éxito operacional.
4. El predicado propuesto con `verdict='approved'`, `state in {'executed','completed'}` y flags solo es correcto si esos campos/vocabularios están definidos y significan eso en todas las clases de run relevantes. Verificar modelo y productores primero.
5. `VALID` puede significar que una alternativa parece válida según ranking sandbox, no que haya sido ejecutada. No cambiar la semántica por inferencia.

### Siguiente paso técnico

Pedir a Codex un **diseño estático, no edición**: comprobar el modelo `ExperimentRun`, semántica y productores de `verdict/state/success/evidence_class/learning_source`, y todos los usos de `run.success` en StrategySelector, AdaptiveWeightLayer y ExperimentLab. Elaborar un contrato de campos y un grafo de dependencias. Después OpenCode intenta refutar el diseño; Claude revisa la discrepancia al regresar. Nada de tests/runtime hasta una autorización separada. `KEEP_BLOCKED`.

## 14. Protocolo inteligente de selección y aprendizaje de agentes — propuesta v0.1

**Estado:** `PROPOSED / NOT IMPLEMENTED`. Esta sección define un protocolo de coordinación y memoria documental; no afirma que IABV ya tenga una base de rendimiento de agentes funcionando.

### Registro mínimo por interacción de agente

Registrar en cada tarea relevante:
- ID de interacción, fecha, objetivo/tipo de tarea y criterio de finalización;
- repo/worktree, HEAD, estado dirty/clean, alcance autorizado y fuente local/remota;
- producto/superficie (Codex CLI, Kilo VS Code, OpenCode, Claude), modo/agente, proveedor, ID exacto del modelo/ruta y variante cuando se muestre;
- herramientas/permisos realmente disponibles; no inferir acceso local por el solo nombre del modelo;
- ID/versión/hash del prompt y artefactos de salida;
- afirmaciones importantes, referencias, falsadores, limitaciones y clasificación de procedencia;
- resultado revisado: cobertura, errores, controles respetados, solicitudes de confirmación innecesarias, si continuó ante artefacto auxiliar ausente y si fue independiente;
- condiciones de privacidad/retención cuando estén documentadas; costo/latencia solo si se midieron de verdad;
- siguiente recomendación operativa y la evidencia por la que se recomienda.

Si no se conoce modelo/proveedor, registrar `UNKNOWN`; no convertir `Auto Free` en un modelo fijo por inferencia.

### Clasificar objetivo y enrutar capacidades

| Objetivo | Agente inicial | Prompt y validación |
|---|---|---|
| Estado de checkout, archivos y source local | Codex CLI | Identidad de checkout primero; separar HEAD/working tree; referencias exactas. |
| Refutación causal y lógica | Kilo + Reflection: Beam 1.0, `high` o `max` | Intentar refutar, buscar ruta alternativa, productor→consumidor→efecto y falsador. |
| Segunda opinión sobre el mismo conjunto de claims | OpenCode + ID fijo como DeepSeek V4.1 Flash Free reportado | Entregar claims/referencias mínimos; no un resumen que induzca a asentir. Registrar modelo/provider real. |
| Análisis de capturas | Nemotron 3.5 Super VL | Usar solo cuando visión aporte evidencia necesaria. |
| Continuidad/documentación | Modelo de texto con acceso a fuente | Conservar procedencia; no resolver decisiones del propietario. |
| Revisión final cuando vuelva | Claude Code | Comparar desacuerdos concretos y el diff acotado; no repetir auditorías cerradas. |

Las opciones son las reportadas por el propietario y pueden cambiar. No son benchmarks comparativos medidos. Modelos con nombres similares en distintos proveedores no se deben tratar como el mismo despliegue.

### Contrato de un prompt eficaz

Cada prompt de auditoría debe fijar:
1. objetivo y afirmación falsable;
2. identidad de checkout, HEAD y working tree;
3. alcance y límites de herramientas;
4. instrucción de seguir con source primario cuando falte un checkpoint auxiliar, distinguiendo `NOT_FOUND_IN_CHECKOUT` de `NOT_FOUND_ON_DISK`;
5. salida con archivo/símbolo/línea, condiciones, argumentos, productor→transformación→consumidor→efecto y falsador;
6. diferencias HEAD vs working tree;
7. clases de evidencia, límites y criterios de parada;
8. prohibición explícita de editar/ejecutar cuando no está autorizado;
9. obligación de entregar el resultado parcial útil, no quedarse solicitando confirmación cuando la tarea ya autoriza una vía segura.

### Lecciones del comportamiento observado (no generalizar desde una sola tarea)

- **Kilo VS Code:** la primera respuesta se detuvo al no hallar el checkpoint dentro del workspace y pidió los símbolos. Con un prompt explícito para continuar por source, después recuperó el checkpoint por ruta absoluta y aportó referencias causales. Aprendizaje de prompt: siempre separar `NOT_FOUND_IN_CHECKOUT` de `NOT_FOUND_ON_DISK` y seguir la ruta segura disponible.
- **Codex CLI:** produjo un mapa útil de checkout y consumidores; el propio reporte advirtió que no era independiente y que no revisaba todos los diffs. Aprendizaje: exigir identidad HEAD/working tree, procedencia por afirmación y declaración precisa de independencia.
- **OpenCode:** generó una lista útil de modelos/opciones y tareas sugeridas, pero el mensaje compartido no identificó el modelo subyacente ni probó capacidades con benchmarks propios. Aprendizaje: registrar modelo/proveedor/variante reales y separar descripción del catálogo de calidad demostrada.
- **Kilo Auto Free:** la ruta puede cambiar de proveedor; no es adecuada por defecto para código/artefactos sensibles. Preferir modelo fijo cuando la reproducibilidad importe y comprobar privacidad antes de transmitir.
- **Revisión causal actual:** Kilo detectó que “punto único de entrada” no concuerda con proponer gates en cuatro zonas. Aprendizaje: pedir que el informe distinga enforcement de productor, filtro de repositorio y sinks/consumidores.

### Bucle recursivo

`objetivo → recuperar memoria pertinente → clasificar tarea → escoger superficie/modelo → adaptar prompt → ejecutar dentro de autorización → extraer evidencia/falsadores → contraste adversarial → evaluar calidad de esta sesión → actualizar memoria → elegir mejor ruta para la próxima tarea`.

No promocionar preferencias de modelo a hechos globales a partir de una interacción. Repetir evaluaciones comparables y revisar resultados antes de generalizar. La memoria debe aprender patrones de herramienta y prompt; nunca otorgar permisos automáticamente.

### Seguridad y estado

No almacenar secretos, tokens, `.env`, bases locales, datos personales ni diffs privados completos en GitHub. Conservar metadatos, rutas relevantes, hashes cuando procedan, resúmenes y referencias. Los modelos gratuitos tienen políticas distintas y variables. La memoria propone el siguiente agente; no autoriza cambios, pruebas, publicación ni puente físico.

**Estado:** `PROPOSED / NOT IMPLEMENTED`; permanece en la PR #467 Draft para revisión, no se ha implementado un registro automático de rendimiento de agentes. `GOVERNANCE = KEEP_BLOCKED`.


## 15. 2026-10-16 — Diseño contractual del gate devuelto por Codex

**Proveniencia:** OWNER_REPORTED para la salida compartida; los hallazgos locales se conservan como CODEX_LOCAL_REPORTED. El informe declara revisión estática local, sin tests/build/runtime y sin modificaciones. No equivale a verificación local independiente por este documento.

### Identidad y frontera de trabajo

- Checkout: C:\temp\IABV_coordination_20261016.
- Rama: codex/iabv-agent-coordination-20261016.
- HEAD declarado: 3926b1144bb23c1066db579da711d3cdbc1611df.
- Se reportaron 96 rutas rastreadas modificadas y una entrada data/ no rastreada; no se abrieron las bases SQLite.
- Los filtros evidence_class=operational_execution en task_context_assembler.py y task_outcome_recorder.py, así como los filtros consultivos del repositorio, están en el working tree y no en HEAD.
- sandbox_experiment_service.py, strategy_selector.py y adaptive_weight_layer.py no tienen cambios respecto a HEAD, según el informe.

El checkout debe seguir considerándose compartido y dirty. No limpiarlo ni cambiar de rama. Una futura tarea de edición requiere localizar un espacio de trabajo aislado y preservar todos los cambios existentes.

### Hallazgo contractual central

ExperimentRun.success es un booleano, pero el código lo utiliza para significados diferentes: resultados de suites/benchmarks, estado de ejecución real, diagnóstico guiado y veredicto heurístico de sandbox. Por tanto, success=True no demuestra por sí mismo ejecución atribuible ni postcondición.

- ExperimentRun no declara campos tipados verdict o state; esos nombres aparecen en tipos diferentes como SandboxExperiment, ExecutionState o IATraceEntry.
- evidence_class y learning_source son metadata libre, no un contrato tipado central encontrado.
- Se encontró un productor explícito de consultation_advisory, pero no un productor positivo demostrado de operational_execution. Esa clase aparece en filtros del working tree.
- Trasladar literalmente un predicado desde IATraceEntry a ExperimentRun puede leer campos inexistentes o rechazar todos los runs por ausencia de metadata. Verificar el esquema real y los productores antes de reutilizarlo.

La distinción arquitectónica clave es que clase de evidencia y resultado son dimensiones diferentes. Una ejecución puede ser operacional y fallar; una validación sandbox puede resultar positiva sin que exista una ejecución operacional.

### Productores y consumidores reportados por Codex

Productores:
- ExperimentLab.run_experiment(): usa evaluation.success derivado de una suite; similitud/calidad no necesariamente demuestra ejecución atribuible del candidato.
- TaskOutcomeRecorder.record(): deriva éxito de RunRecord.status == SUCCESS, pero el recorrido revisado no produce explícitamente una clase operacional positiva.
- SelfTeachOrchestrator._register_learning(): éxito derivado de diagnóstico o correcciones.
- SandboxExperimentService.validate_recommendation(): convierte VALID/DOUBTFUL en un resultado sandbox; _record_promotion() fija success=True sin ejecución atribuible demostrada.
- AutonomousEvolutionService: asesoría consultiva marcada explícitamente como consultation_advisory.
- CodeAuditTrail: success=True representa el cierre de auditoría, no ejecución del candidato recomendado.

Consumidores:
- ExperimentLab._reuse_bonus().
- StrategySelector.recommend() y _build_composite_recommendation().
- AdaptiveWeightLayer._profile().
- ExperimentLab.generate_training_examples().
- Cálculos de estadísticas y tasas de éxito.
- TaskOutcomeRecorder.update_weights().
- TaskContextAssembler._adaptive_learning_summary() y _learned_patterns(), que según el informe no aplican el mismo filtro en todos los recorridos.

Los consumidores del laboratorio citados leen run.success sin filtrar clase/origen. El efecto final de cada resumen contextual sobre decisiones posteriores sigue UNPROVEN si no se ha trazado su consumidor.

### Grafo causal refinado reportado

suite / RunRecord / self-teach / sandbox / advisory producers → ExperimentLab.record_outcome o run_experiment → ExperimentRun.success + metadata libre → StrategySelector / AdaptiveWeightLayer / reuse bonus / training examples → recommendation.supporting_run_ids → discovery/sandbox → blockers + alternativa rankeada → sandbox verdict/promotion → nuevo run success.

Esta realimentación es plausible y está apoyada por las rutas estáticas citadas; no se ha medido ni demostrado mediante runtime.

### Evaluación A/B/C

- A: impedir que _record_promotion escriba éxito operacional sin ejecución atribuible. Mitigación concreta pero insuficiente por sí sola: otros runs sandbox y heurísticos siguen alimentando consumidores genéricos de success.
- B: conservar la evaluación sandbox pero excluirla de ranking/aprendizaje operacional. Cubre más consumidores, pero obliga a revisar todas las fronteras decisorias; no basta con filtrar el repositorio o fiarse del nombre de learning_source/suite.
- C: separar tipadamente validación de ejecución operacional. Semánticamente es la opción más sólida a largo plazo, pero requiere definir esquema y compatibilidad histórica; metadata libre no basta.

Conclusión propuesta: C es la dirección conceptual a largo plazo. La mitigación cercana requeriría gates en el productor y en los consumidores decisorios de B. A sola no basta. Ninguna estrategia está aprobada para implementación.

### Precauciones de diseño

1. No asignar evidence_class=operational_execution desde un wrapper genérico solo por learning_source, suite o etiqueta del caller.
2. No introducir learning_source=sandbox_observed sin contrato definido; además, “observed” tampoco debe implicar ejecución no demostrada.
3. No usar directamente verdict=approved ni state in {executed, completed} como predicado de ExperimentRun: según el informe esos campos pertenecen a otros modelos/tipos.
4. Mantener separadas clase de evidencia y resultado: una ejecución fallida puede ser evidencia operacional, aunque no sea éxito.
5. Verificar que cada supporting_run_id pertenezca al scope, candidato y recomendación correcta. Soporte mixto no hereda automáticamente autoridad operacional.
6. Un helper común ayuda a la consistencia, pero no sustituye la comprobación de cada sink: ranking, pesos adaptativos, reuse bonus, training examples y promoción sandbox.
7. Preservar la evaluación sandbox como tal, sin convertirla automáticamente en ejecución operacional.

### Próxima revisión

Claude Code, ahora reportado disponible por el propietario, es el siguiente revisor recomendado. Su cometido es intentar refutar el diseño de Codex: verificar semántica de campos, compatibilidad del esquema, inventario de todos los consumidores, rutas omitidas y falsadores. No debe repetir la búsqueda general ni editar el checkout dirty.

OpenCode queda como tercera opinión solo si Claude identifica objeciones sustantivas o quedan discrepancias específicas. No lanzar tres propuestas de implementación en paralelo.

**Estado:** STATIC_DESIGN_READY_FOR_ADVERSARIAL_REVIEW; no IMPLEMENTATION_READY. GOVERNANCE = KEEP_BLOCKED.

## 16. Actualización temporal y protocolo inteligente de selección de agentes

El propietario informó que Claude vuelve a estar disponible. Este hecho se registra como OWNER_REPORTED; no se afirma conocer la cuota restante ni el modelo/plan exacto de esa sesión. La selección debe seguir la circunstancia temporal real: durante la ausencia se usaron Codex local y Kilo para avanzar; ahora Claude puede revisar el diseño ya producido.

### Selección actual por tarea

1. **Claude Code — siguiente:** revisión adversarial del informe contractual de Codex, focalizada en ExperimentRun, productores/consumidores de success, compatibilidad A/B/C y falsadores. Confirmar que puede inspeccionar sin escribir en la rama o worktree dirty.
2. **Codex CLI — evidencia local:** no repetir la auditoría general; responder a objeciones concretas y, si corresponde, completar una matriz de consumidores y diseño.
3. **Kilo / Reflection: Beam 1.0 — mapa causal existente:** el resultado recibido ya identifica promoción y consumidores. Usarlo para objeciones puntuales, no reiniciar desde cero.
4. **OpenCode / modelo fijo reportado como DeepSeek V4.1 Flash Free:** mantener como tercera opinión, solo si Claude y Codex discrepan. Confirmar el ID/proveedor en el selector.
5. **ChatGPT/GitHub:** mantener procedencia, continuidad documental, diferencias entre informes y coordinación. No afirmar acceso al runtime local.

La preferencia por Claude para el siguiente paso obedece al tipo de tarea (revisión adversarial del diseño contractual) y a que volvió a estar disponible; no implica superioridad universal del modelo.

### Unidad de memoria por interacción

Para cada tarea relevante, registrar:
- fecha/objetivo y criterio de terminación;
- superficie (Codex CLI, Kilo VS Code, OpenCode, Claude Code), modo/agente, proveedor, ID exacto de modelo/ruta y variante cuando se muestren;
- repositorio, worktree, HEAD, estado dirty/clean, fuente de evidencia y límites autorizados;
- versión/hash del prompt si se conoce, fuentes y artefactos de salida;
- afirmaciones principales, contraejemplos, falsadores, limitaciones y clasificación de procedencia;
- si fue independiente, si continuó ante un artefacto auxiliar faltante y si respetó límites;
- latencia/coste solo si se midieron, privacidad/retención solo si las condiciones están documentadas;
- lección de prompt concreta para la siguiente tarea y razón de la siguiente asignación.

Cuando el modelo/proveedor no se conoce, registrar UNKNOWN; nunca deducir un modelo fijo desde Auto Free. No generalizar el rendimiento de un agente por una sola interacción.

### Contrato de prompt adaptativo

Cada prompt de auditoría debe fijar:
1. objetivo y afirmación falsable;
2. identidad de checkout, HEAD y working tree;
3. alcance y límites de las herramientas;
4. recuperación de memoria y continuación por source cuando falte un checkpoint auxiliar;
5. salida por archivo/símbolo/línea con productor → transformación → consumidor → efecto y falsador;
6. comparación HEAD frente a working tree;
7. procedencia y límites de evidencia;
8. prohibición de escribir/ejecutar cuando no está autorizado;
9. obligación de entregar los hallazgos parciales verificables sin quedar bloqueado por un artefacto auxiliar ausente cuando ya existe una ruta segura.

### Lecciones específicas del comportamiento observado

- Kilo VS Code primero detuvo el análisis porque no halló el checkpoint dentro del workspace; después lo recuperó por la ruta absoluta y produjo el mapa causal. Ajuste de prompt: distinguir NOT_FOUND_IN_CHECKOUT de NOT_FOUND_ON_DISK y continuar por source.
- Codex aportó un mapa útil pero distinguió que su seguimiento no era independiente. Ajuste: procedencia por afirmación y separación explícita entre HEAD y working tree.
- OpenCode presentó un catálogo útil pero sin un modelo real de sesión ni evaluación comparativa. Ajuste: registrar el ID/proveedor exacto y tratar las cualidades como hipótesis hasta contrastarlas.
- Kilo detectó la ruta causal, pero la propuesta verbal de “punto único” incluía varios consumidores. Ajuste: pedir que distinga enforcement en productor, repositorio y sinks decisorios.
- El informe contractual de Codex detectó que evidence_class no tiene productor positivo demostrado. Ajuste: no proponer un gate por una clase que ningún productor autorizado puede generar; primero definir evidencia, contrato y productor.

### Bucle recursivo de simbiosis

objetivo → recuperar memoria pertinente → clasificar la tarea → seleccionar agente/modelo/herramientas → adaptar el prompt → ejecución autorizada → extraer pruebas y falsadores → contraste adversarial → evaluar la conducta de la sesión → actualizar memoria → escoger mejor la próxima ruta.

La memoria documental de esta PR permite continuidad entre conversaciones, pero no es todavía una base de datos operacional consultada automáticamente por todas las IAs. Convertirla en sistema persistente dentro de IABV requiere diseño, revisión de privacidad y autorización separados. La memoria puede recomendar herramientas; no concede permisos.

### Seguridad y parada

No guardar secretos, tokens, datos personales, SQLite, .env ni diffs locales completos en GitHub. Usar resúmenes, referencias y hashes solo cuando correspondan. Los catálogos y condiciones free cambian; verificar el selector en cada tarea sensible.

No implementar el gate ni ejecutar pruebas/runtime en esta etapa. No acceder a M0A ni activar el puente físico. Mantener GOVERNANCE = KEEP_BLOCKED.

**Siguiente checkpoint:** informe de Claude con objeciones concretas al diseño A/B/C, seguido de reconciliación con Codex. Después se decidirá si se prepara un diff aislado. No editar todavía.


## 17. 2026-10-16 — Revisión Claude Web y reconciliación contra main público

**Proveniencia:** OWNER_REPORTED para el informe Claude. Claude declara que no tiene acceso al checkout Windows C:\temp\IABV_coordination_20261016; analizó el commit público 5b1d89022ee4cdc63c1f88e050f086b40a42875c. No revisó directamente las 96 rutas locales.

### Reconciliación de versiones

La comparación de GitHub entre el commit de Claude y main público devolvió:
- base: 5b1d89022ee4cdc63c1f88e050f086b40a42875c
- head: main
- ahead_by: 986; behind_by: 0
- merge base igual al SHA analizado por Claude.

El main público observado en ese corte es 9e0ce66768aedd7422e0d3551affd398f44a7532. Por tanto, el informe de Claude parte de un antecesor 986 commits detrás del main público observado. Sus números de línea no deben reutilizarse sin volver a verificarlos en la referencia actual.

Se recuperaron directamente los siguientes archivos fijados al commit público 9e0ce...:

| Archivo | Git blob SHA | Hallazgo confirmado en el commit |
|---|---|---|
| services/self_teach/sandbox_experiment_service.py | a6723261ce31f71a9fcd5433ce3e1e419230440c | Líneas 62–65: blockers + alternativa de ranking producen VALID/promote=True; línea 103 hereda supporting_run_ids de la recomendación original; línea 168 fija success=True en _record_promotion. |
| services/lab/strategy_selector.py | 569a038fae979bb618eddf7a322068b7ad87c63e | Línea 70 usa run.success para successful_keys; líneas 276–280 vuelven a contar r.success en la recomendación compuesta. |
| services/adaptive/adaptive_weight_layer.py | 1de589c1d35969a657ba894a8a0a447e7920e7c7 | Línea 112 cuenta success; línea 184 convierte cualquier run.success en outcome positivo/negativo para recency. |
| services/lab/experiment_lab.py | 05b57d1dde101d5e7ff11955829a9e1d07d1d901 | Líneas 257–258 calculan reuse bonus desde item.success; línea 468 actualiza estadísticas con success. generate_training_examples() no aparece en el archivo público consultado y sigue UNPROVEN en el checkout local. |
| infra/persistence/experiment_lab_repository.py | c0f1437caae9ca022296c0947dfd857c2af51187 | list_recommendations no muestra el filtro consultivo descrito para el working tree local de Codex ni un gate positivo de operational_execution. |
| services/adaptive/task_context_assembler.py | c5a6852a6a82a0c60886ea4bb6c236f50fe4a57c | No contiene la cadena operational_execution en la copia pública; los métodos _adaptive_learning_summary y _learned_patterns transforman insights recibidos; línea 1016 contiene además un consumo de item.success. |
| services/adaptive/task_outcome_recorder.py | fddf3f90e15b4ec74ad813441ceeac18458e0118 | No contiene la cadena operational_execution en el archivo público consultado. |
| domain/models.py | a9033d21052c519e09f482097599c704a62ea916 | Contiene ExperimentRun, SandboxExperimentVerdict y SandboxExperiment; evidence_class no aparece como campo tipado en la definición revisada. |

Fuentes fijas:
- [SandboxExperimentService, main público 9e0ce](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/self_teach/sandbox_experiment_service.py#L20-L118)
- [StrategySelector, main público 9e0ce](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/lab/strategy_selector.py#L32-L125)
- [AdaptiveWeightLayer, main público 9e0ce](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_weight_layer.py#L109-L194)
- [ExperimentLab, main público 9e0ce](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/lab/experiment_lab.py#L150-L258)

### Evaluación de las afirmaciones de Claude

- C1, evidence_class no es campo tipado en los modelos inspeccionados: CORROBORATED para el main público 9e0ce.
- C2, learning_source es metadata libre y no aparece como gate decisorio en los consumidores inspeccionados: CORROBORATED en los archivos públicos recuperados.
- C3, consumidores de estrategia, pesos adaptativos y reuse usan success sin el filtro de clase reportado: CORROBORATED en main público 9e0ce.
- C4, _record_promotion persiste success=True: CORROBORATED en el main público.
- C5, la promoción usa blockers y alternativa rankeada sin que validate_recommendation muestre ejecución en esa ruta: CORROBORATED dentro del alcance del método inspeccionado; esto no prueba que no exista ninguna ruta de ejecución en otra parte del sistema.
- C6, supporting_run_ids se copia de la recomendación, no de una ejecución atribuible de la alternativa: CORROBORATED en la línea 103 pública.
- C7, no aparece productor de operational_execution en la búsqueda pública comunicada y no aparece en los archivos públicos clave inspeccionados: CORROBORATED dentro de ese ámbito. No extender la afirmación más allá del árbol/patrones realmente buscados.
- C8, sobre igualdad del working tree local con HEAD_GH: NO VERIFICABLE por Claude Web. Claude no podía acceder al checkout de Codex; solo se puede afirmar que los filtros descritos no aparecen en el main público 9e0ce. La comparación local sigue CODEX_LOCAL_REPORTED hasta que Codex la reproduzca.
- U1/U2, HEAD local y las 96 rutas modificadas: no verificables por Claude Web.
- U3, generate_training_examples(): ausente en el archivo del main público consultado; su existencia/comportamiento en el checkout 3926b... sigue UNPROVEN. El uso público de success en estadísticas, línea 468, sí está confirmado.

**Conclusión:** aunque Claude empezó en un commit público antiguo, las piezas centrales de la ruta de promoción y los consumidores se comprobaron en el main público observado y siguen presentes. Sin embargo, el informe de Claude no puede certificar nada de los cambios locales no publicados. No se inspeccionó runtime ni el checkout Windows.

### Corrección crítica al stopgap A+B propuesto por Claude

Cambiar success=True a success=False en _record_promotion() es una posible mitigación, pero sin filtros de elegibilidad puede convertir una evaluación sandbox en un falso fracaso operacional. En el main público, AdaptiveWeightLayer._profile calcula failure_count = sample_count - success_count, y _recency_score asigna outcome negativo a todos los runs con success=False. Un run sandbox que nunca ejecutó la herramienta no debe contar como fracaso de una ejecución real.

El filtro por suite_name in {'sandbox_experiment', 'sandbox_promotion'} es un stopgap identificable para los dos orígenes conocidos; no es un contrato probatorio. Antes de usarlo, se requiere inventario local completo de productores y consumidores, incluyendo:
- StrategySelector.recommend y _build_composite_recommendation.
- AdaptiveWeightLayer._profile y _recency_score.
- ExperimentLab._reuse_bonus y estadísticas por asistente.
- TaskContextAssembler u otros resúmenes de aprendizaje.
- training examples si existen en la versión local.
- promoción sandbox y cualquier consumidor adicional de los campos resultantes.

No basta con excluir sandbox de success_count dejando los runs en sample_count, failure_count, score promedio o recency. Para las métricas operacionales, un outcome sandbox debe quedar neutral/no elegible, o contabilizarse en una dimensión separada; métricas de bloqueos y evaluaciones sandbox pueden preservarse explícitamente. No asumir que blocked_rate se conserva automáticamente, pues _record_promotion puede persistir una lista de flags distinta de la del experimento sandbox.

Los nombres suite_name y learning_source no son prueba de ejecución. Pueden servir para un stopgap por exclusión de orígenes conocidos, pero la dirección robusta separa: clase/procedencia de evidencia, resultado de la evidencia y elegibilidad para cada consumidor. La ausencia de evidencia operacional no debe rellenarse retroactivamente en datos históricos. Para consumidores decisorios, legacy/unknown debe quedar inelegible hasta definir una regla; los reportes descriptivos pueden mostrarlo como histórico sin clase.

El supporting_run_ids copiado en la promoción también necesita validación de scope, candidato y configuración: el ID por sí solo no demuestra que se ejecutara la alternativa promovida.

### Fase siguiente

1. Codex local, solo lectura: volver a enumerar todos los usos y productores de success en el checkout 3926b... y su working tree; reconciliar las diferencias con main público 9e0ce y resolver generate_training_examples y cualquier otro consumer local.
2. Diseño corregido: mantener los outcomes sandbox neutrales en métricas de ejecución operativa, pero preservar por separado sus señales de evaluación/bloqueo.
3. Claude Web: ya aportó revisión de source público; volver a utilizarlo solo ante una discrepancia concreta o para revisar un diseño que pueda observar en GitHub. No pedirle certificar los archivos locales que no puede ver.
4. OpenCode/Kilo: tercera opinión solo para discrepancias que no se resuelvan mediante source concreto.
5. Implementación: tras decidir el contrato, crear un espacio aislado que preserve los cambios actuales; revisar el diff y autorizar pruebas por separado.

No se aprueban aún A/B/C para implementación. GOVERNANCE = KEEP_BLOCKED; no acceder a M0A ni activar el puente físico.


## 19. 2026-10-16 — Codex local census and corrected neutral-outcome design

**Provenance:** OWNER_REPORTED for the pasted Codex report; detailed local facts remain CODEX_LOCAL_REPORTED until inspected by another process. The report says no files were edited, staged, switched or executed, and no SQLite content was opened.

### Preserved checkout

- Root: C:\temp\IABV_coordination_20261016
- Branch: codex/iabv-agent-coordination-20261016
- HEAD: 3926b1144bb23c1066db579da711d3cdbc1611df
- State at end: 96 tracked modified paths plus one untracked data/ entry. Keep all intact; do not reset, clean, stash, stage, switch branches or overwrite files.
- The untracked directory contains two reported SQLite paths: data/test_autonomous_evolution_service_ingest_codex_workspace/data/app.sqlite and data/test_autonomous_evolution_service_insufficient_response_workspace/data/app.sqlite. Their contents remain uninspected and must stay untouched.
- Codex reports that object 9e0ce66768aedd7422e0d3551affd398f44a7532 was available locally, refs/remotes/origin/main pointed to it, and eight selected source files matched HEAD. This is a reported local observation, not a new independent check here.
- The 12 modified source files reported are:
  IABV_v1.5/src/iabv_v15/domain/models.py;
  IABV_v1.5/src/iabv_v15/infra/persistence/database.py;
  IABV_v1.5/src/iabv_v15/infra/persistence/experiment_lab_repository.py;
  IABV_v1.5/src/iabv_v15/infra/persistence/tool_record_repository.py;
  IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py;
  IABV_v1.5/src/iabv_v15/services/adaptive/task_context_assembler.py;
  IABV_v1.5/src/iabv_v15/services/adaptive/task_outcome_recorder.py;
  IABV_v1.5/src/iabv_v15/services/evolution/autonomous_evolution_service.py;
  IABV_v1.5/src/iabv_v15/services/lab/experiment_lab.py;
  IABV_v1.5/src/iabv_v15/services/self_teach/self_teach_orchestrator.py;
  IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py;
  IABV_v1.5/src/iabv_v15/ui/viewmodels/control_center_viewmodel.py.
- The other 84 tracked changes are test files under IABV_v1.5/tests/ as enumerated in the owner-shared report. Do not inspect/revert them broadly merely to continue this gate task.

### Corrected local finding and names

The method generate_training_examples() does not exist in the checkout according to Codex. The relevant method is ExperimentLab.generate_training_corpus() at experiment_lab.py:447. It processes recent runs, aggregates run.success by assistant and computes rates/latency. The adaptive threshold and per-assistant statistics also use success. Correct the earlier method-name discrepancy; do not claim the corpus path is absent.

The working tree adds CONSULTATION_ADVISORY and filters for consultative evidence, plus gates that require evidence_class='operational_execution' in task_context_assembler.py and task_outcome_recorder.py. These are not in HEAD. Codex found no positive producer for operational_execution. Enforcing these gates as-is may reject all otherwise legitimate candidates; producer and contract must be designed together. strategy_selector.py, adaptive_weight_layer.py and sandbox_experiment_service.py are unchanged versus HEAD in the reported worktree.

### Producers/consumers and scope details

The local report identifies additional producers beyond sandbox: suite evaluation results; TaskOutcomeRecorder outcomes linked to RunRecord; SelfTeachOrchestrator diagnostic/correction outcomes; AdaptiveTaskOrchestrator parallel-comparison and shadow-parallel outcomes; consultative AutonomousEvolutionService results; and CodeAuditTrail round-completion results. These meanings differ, so success=True is not a unified fact of operational execution.

Consumers include StrategySelector eligibility and composite recommendation, AdaptiveWeightLayer success/failure/recency/trend/score/reuse weighting, ExperimentLab reuse bonus, adaptive threshold, per-assistant statistics and training corpus, plus TaskContextAssembler trace/context/reusable-pattern construction. The exact runtime impact on a later mode decision remains UNPROVEN.

### New identity/provenance gap

StrategySelector builds supporting_run_ids from ExperimentRun IDs grouped by route/assistant/configuration. SandboxExperimentService copies these IDs into evidence_refs and source_trace_ids. TaskOutcomeRecorder._source_trace_ids() consumes operational_trace_ids as trace references. Do not silently relabel run IDs as trace IDs: these may be different identifier namespaces.

The repository reportedly checks existence and some advisory exclusions for support IDs, but does not validate every ID against the exact recommendation domain, subject, scope, candidate and configuration. A support ID does not prove that the promoted alternative ran. Include run-ID/trace-ID namespace and support membership in the next static audit.

### Correct neutral-outcome principle

Changing sandbox promotion from success=True to success=False without eligibility filtering is unsafe: it may count an unexecuted candidate as an operational failure. AdaptiveWeightLayer currently counts false success in failure_count and uses it for negative recency; sandbox score, trend, sample denominator and reuse_score may also continue affecting the profile.

Target behavior: sandbox outcome is **neutral for operational-execution metrics**, not a success and not a failed operational execution. Preserve sandbox verdicts, blockers, availability and comparison score in a distinct evaluation cohort. For operational metrics, exclude that cohort from success/failure, sample denominators, recency/trend, reuse, ranking and training corpus—or compute these in separately typed dimensions. Keep blocker/availability statistics explicitly rather than assuming they survive a general exclusion.

suite_name and learning_source may support a temporary exclusion for known origins, but they are labels, not proof of execution. Historical records without a verified classification must not be retroactively labelled operational or converted into failure; keep them legacy/unknown for decision consumers while retaining descriptive visibility.

The long-term contract should separate evidence provenance/class, evidence result, and eligibility for a specific consumer. Evidence class is not a result: a real operational execution can fail and remain operational evidence. No schema or implementation change is approved here.

### State of the claims

Corroborated statically from the reported local source and selected public-source checks:
- sandbox promotion can persist success=True without evidence that the alternative was executed;
- StrategySelector, AdaptiveWeightLayer and ExperimentLab use success in decision/scoring paths;
- the reported working-tree positive evidence gates lack a demonstrated positive producer;
- a success=False-only fix risks false negative weighting;
- supporting IDs are not shown to bind the promoted candidate fully.

Still UNPROVEN:
- runtime changes to ranking/mode selection;
- a universal postcondition for all task families;
- exact effects of all 96 local diffs beyond the reported census;
- correct resolution of run IDs vs trace IDs in every consumer;
- CAS, fencing, atomicity, exactly-once or recovery guarantees.

### Current open edge and actor route

The first open edge is now a **static design-and-identity audit**, not implementation:
1. Codex local: census every producer/consumer in the preserved checkout, including generate_training_corpus(), identity linkage and all effects of success; no broad diff review and no data/ access.
2. Specify how sandbox remains neutral in operational metrics while preserving separate evaluation/blocker information; decide treatment of historical unknowns.
3. Claude Web can challenge public source and the written design, but cannot certify the dirty local checkout. Use it for concrete claims/deltas only.
4. Kilo/OpenCode are reserved for unresolved contradictions, not duplicate broad audits.
5. If a patch later becomes justified, prepare it in a new isolated worktree after a separate authorization. Preserve the existing 96 tracked modifications and untracked data/ entry.

### Relation to existing IABV memory

This is a method delta within existing memory organs, not a proposal for a second coordinator or parallel memory database. The canonical route remains README → CURRENT-STATE → CONTEXT-INDEX → MEMORY-OPERATING-PROTOCOL → SYMBIOSIS-MAP → UNRESOLVED-KNOWLEDGE → ARCHIVE-REGISTRY → AGENTS → evidence record. The agent-learning notes in this addendum must be absorbed into those route surfaces. A GitHub writeback is not proof that IABV runtime automatically retrieves memory, routes agents, or changes later behavior.

**State:** STATIC_DESIGN_READY_FOR_RECONCILIATION; not IMPLEMENTATION_READY. GOVERNANCE = KEEP_BLOCKED.


## 20. 2026-10-16 — Routing correction after Codex's local census

The local census has now been reported by Codex. The next edge is no longer a full census; it is a targeted reconciliation of the run-ID/trace-ID claim and then an adversarial design challenge.

### Important HEAD/worktree discrepancy discovered during public cross-check

At public commit 9e0ce66768aedd7422e0d3551affd398f44a7532, TaskOutcomeRecorder._source_trace_ids() reads ia_trace_summary.reusable_trace_ids, winning_trace_ids or decision_metadata.supporting_trace_ids. The owner-shared Codex report describes its local version as consuming operational_trace_ids. Since task_outcome_recorder.py is one of the 12 reported modified source files, this could be a genuine working-tree delta; it is not yet proven to be a code defect or a mistaken report.

Required narrow reconciliation by Codex:
1. Compare exact lines and diff for TaskOutcomeRecorder._source_trace_ids() in HEAD versus working tree.
2. Find every producer of the fields it reads (operational_trace_ids, source_trace_ids, supporting_trace_ids, reusable_trace_ids and winning_trace_ids).
3. Find all consumers of those fields and determine whether values are RunRecord IDs, ExperimentRun IDs, IATraceEntry IDs or another typed namespace.
4. Trace source references from StrategySelector.supporting_run_ids through SandboxExperimentService evidence_refs/metadata into TaskOutcomeRecorder and ToolDiscoveryService.
5. Mark the concern as CONFIRMED, REFUTED or UNRESOLVED; do not relabel IDs as traces from the key name alone.

This is a focused follow-up, not a broad diff audit. No edits, tests, runtime or data/ access.

### Updated route after the local census

Codex's local report now supplies: the complete reported list of 96 modified tracked files, exact source/worktree distinctions, the corrected method name generate_training_corpus(), producers/consumers of success, the absence of a positive operational evidence producer, and the neutral-sandbox outcome proposal.

The first remaining edge is therefore:
- resolve the exact local run/trace identity lineage;
- then send the reconciled design to Claude Web for an adversarial challenge of the neutral metric policy, the proposed A+B mitigation, historical unknowns and every decision sink.
Claude Web should receive the Codex report and relevant public source links; it must not claim to have inspected the local dirty checkout. If a Claude objection depends on local-only code, route that exact question back to Codex rather than asking Claude to guess.

OpenCode/Kilo remain fallback challengers only if a material disagreement remains after those two stages. Avoid redundant three-agent audits.

### Evidence calibration

- The local 96-path state and modified TaskOutcomeRecorder behavior are CODEX_LOCAL_REPORTED.
- The public implementation of _source_trace_ids() described above is PROVEN_BY_SOURCE for commit 9e0ce...
- The possibility that local modifications change the ID namespace is UNRESOLVED until Codex supplies the exact HEAD/worktree diff.
- The operational effect of these metadata IDs on ranking or learned behavior remains UNPROVEN without complete consumer tracing and runtime evidence.

Governance remains KEEP_BLOCKED; no implementation or runtime is approved.


## 21. 2026-10-16 — Claude adversarial review of the evidence contract

### Dictamen recibido

Claude Web returned `CONTRACT_NOT_READY`, while preserving `GOVERNANCE = KEEP_BLOCKED`. The report identifies four genuine contract gaps: incomplete coverage of reference-propagation paths; undefined rules for mixed-support groups; sandbox neutrality not operationalized across metrics/denominators; and no safe handling policy for unclassified historical runs. This is a design gap, not evidence that the goal is infeasible.

### Evidence boundary

- The Codex local checkout remains owner-/agent-reported at root `C:\\temp\\IABV_coordination_20261016`, branch `codex/iabv-agent-coordination-20261016`, HEAD `3926b1144bb23c1066db579da711d3cdbc1611df`; 96 tracked modifications plus untracked `data/`. Do not inspect `data/` or SQLite, modify the checkout, or run code/tests/build/runtime without separate authorization.
- Claude Web could not inspect that dirty local checkout. Its local-path limitations remain.
- Public source was independently fetched at commit `9e0ce66768aedd7422e0d3551affd398f44a7532`. `IABV_v1.5/src/iabv_v15/services/lab/experiment_lab.py` contains `ExperimentLab.generate_training_corpus()`: it loads up to 500 runs, groups by domain and suite, and aggregates `int(run.success)`/total/latency. Thus corpus generation is confirmed in that public commit, even though Claude marked coverage UNRESOLVED. The exact current dirty-working-tree behavior remains a distinct question.
- Public claims and Codex-local claims must not be merged into a single source state.

### Corrections needed to Claude's proposed contract

1. The proposed predicate `NOT EXISTS(ExperimentRun WHERE run_id = ref)` is not a valid general test that a trace reference is wrong: string-valued identifiers in distinct namespaces can collide. Require an explicitly typed reference and a lookup in the declared namespace; never infer entity type from string equality or inequality.
2. `execution_ms > 0` is necessary only if demanded by the execution model; it is not sufficient proof of execution or candidate identity. Operational class must be grounded in an authorized execution attestation/record linked to the exact candidate, scope, executor, status and verified postconditions. Keep evidence class distinct from success/failure result.
3. `candidate_id` (if the domain has one) or an equivalent stable candidate fingerprint must be part of support membership. A route/assistant/config signature alone is insufficient if candidates can differ within it. If no stable candidate identity exists, that is a blocker, not a reason to weaken membership checks.
4. Sandbox neutrality covers all operational metrics, including both numerator and denominator, failure count, recency, trend, reuse bonus, adaptive weights, thresholds, ranking and operational training corpora. Sandbox-specific blocker/fallback metrics may exist only in a separate evaluation cohort and must not silently enter operational `blocked_count`, `fallback_count` or denominators.
5. Transitional `suite_name`/`learning_source` filters can reduce immediate exposure but are not the durable contract. They must not be presented as complete protection.
6. Do not change sandbox outcomes to `success=False` merely to exclude them; that can convert “not executed” into an operational failure.

### Conservative design defaults (proposals, not owner approvals)

- Candidate identity: require `candidate_id` or a canonical stable candidate fingerprint in support membership. Reject ambiguous cross-candidate support.
- Metrics: only eligible operational-execution evidence enters operational numerators or denominators. Sandbox and legacy records belong to separate descriptive/evaluation cohorts.
- Blockers/fallbacks: permit sandbox to update explicitly sandbox-scoped blocker/availability metrics only; never shared operational metrics without separate, explicit policy and names.
- Legacy: missing/unknown evidence classification stays `LEGACY_UNATTRIBUTABLE`/unknown, descriptive-only and excluded from operational learning. Reclassification requires a separately authorized, auditable process supported by source evidence; no bulk inference from `success=True`, `suite_name` or metadata.
- IDs: typed namespaces and explicit relation resolution at write, transform and consumer boundaries; no `run_id` alias to `trace_id`.

These are proposed safe defaults for review, not a claim that the owner has approved them.

### Revised next frontier

Do not restart the broad audit. Produce a version-2 contract that incorporates the corrections above, closes the denominator and candidate-identity holes, includes the already-publicly-confirmed training-corpus consumer, and labels any dirty-local-only coverage as UNRESOLVED pending the authorized local source record. Then seek a narrow adversarial check of those repaired invariants. Do not implement yet.

Governance remains `KEEP_BLOCKED`; PR #467 remains draft/unmerged and branch-only. No local changes, product code, tests, runtime, M0A, SQLite or physical bridge are authorized by this documentation update.


## 22. 2026-10-16 — Contract V2 adjudication and narrow local verification route

### Received V2 result

Claude Web returned `CONTRACT_READY_WITH_REPAIRS`. The proposal is substantially improved, but this is not implementation authorization. Independent review found material internal consistency and coverage gaps that must be corrected before any implementation plan is treated as complete.

### Public-source reconciliation performed in this turn

The GitHub API currently resolves public `main` to `9e0ce66768aedd7422e0d3551affd398f44a7532` (commit dated 2026-10-14), not `cbc522140`. The latter resolves to full commit `cbc5221407630fc80721619d2b2b2c45eedb50fb`, parent `d4b3ec9a24420dd9f76da9e2040e0335509422b5`. The inspected blob SHAs for `models.py`, `task_outcome_recorder.py`, `sandbox_experiment_service.py`, `tool_memory.py`, `experiment_lab.py`, `strategy_selector.py`, and `adaptive_weight_layer.py` were identical at refs `cbc522140` and `9e0ce...`. The source-tip description differs, while these checked files match between the two refs.

Publicly confirmed at `9e0ce...`:

- `domain/models.py::ExperimentRun` has `candidate_id: str = ""` and `evidence_refs: list[str]`; it has no first-class `evidence_class`, `execution_id` or `attested_by`. `ExperimentRecommendation.supporting_run_ids` is `list[str]`.
- `TaskOutcomeRecorder` assigns `candidate_id=run_record.run_id`.
- `SandboxExperimentService._record_sandbox_run()` assigns `candidate_id=experiment.experiment_id`, has `execution_ms=0), and copies `supporting_run_ids` into `evidence_refs` and metadata `source_trace_ids`. `_record_promotion()` also uses the experiment ID as candidate ID, writes `success=True`, and uses the recommendation's subject key.
- `AdaptiveWeightLayer._profile()`, `StrategySelector.recommend()`, `ExperimentLab._reuse_bonus()` and `ExperimentLab.generate_training_corpus()` consume `run.success` without an evidence-class gate; the corpus increments both success and total.
- `ToolMemory.remember_result()` persists the result and increments `ToolCard.success_count`/`failure_count` from `result.success` before/independently of its call to `InteractionLearningService.learn_from_execution()`. Therefore guarding only the interaction-learning call for `SANDBOX_PASS` is insufficient to establish complete sandbox neutrality.

Pinned public-source links:
- [ExperimentRun and recommendation models](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/domain/models.py)
- [TaskOutcomeRecorder](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/adaptive/task_outcome_recorder.py)
- [SandboxExperimentService](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/self_teach/sandbox_experiment_service.py)
- [ToolMemory](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/tools/tool_memory.py)
- [ExperimentLab/training corpus](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/lab/experiment_lab.py)
- [StrategySelector](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/lab/strategy_selector.py)
- [AdaptiveWeightLayer](https://github.com/jhonf463r/Python/blob/9e0ce66768aedd7422e0d3551affd398f44a7532/IABV_v1.5/src/iabv_v15/services/adaptive/adaptive_weight_layer.py)

### Contract V2 gaps requiring repair

1. **Class-set contradiction:** I-1 omits `SANDBOX_PROMOTED`, though I-8 and §2.1 require it. All normative enumerations must share the same closed class set or define a typed subtype relation.
2. **Resolve identifier namespaces; do not compare raw strings:** U-5's rejection of `candidate_id == run_id` repeats the category of mistake corrected for Run IDs versus Trace IDs. Public producers appear to put run/experiment IDs into `candidate_id`, but the invariant should resolve `candidate_id` to an actual candidate or canonical fingerprint, not reject accidental string equality alone. The sandbox producer's `candidate_id=experiment.experiment_id` is another route to reconcile.
3. **Attestation contract mismatch:** I-4 requires task/candidate/scope/postconditions and verifiable authorization, while §3.1 lists only `execution_id`, `attested_by`, `task_id` and `observed_state`. Non-empty strings do not prove authorization. Bind the authoritative execution record to exact candidate/fingerprint, configuration, scope/task, terminal state and required postconditions.
4. **TypedRef is not referential integrity:** a `ref_type` does not prove that the object exists or that its relationship is valid. Define a closed allowlist for each field, typed resolution in the correct repository, and behavior for missing, mismatched or stale references. Replace the open-ended `...` with an explicit entity set after local source census.
5. **ToolMemory neutrality is incomplete:** sandbox results must not increment operational ToolCard success/failure counters, alter last-operational validation state, or flow into operational interaction patterns. Keep result persistence/descriptive counters separate from operational learning; `validation_status` alone is not a sufficient provenance source unless bound to trusted execution provenance.
6. **I-11 (only newest run counts) is unsubstantiated:** it could discard valid independent operational history and collapse sample statistics. Do not supersede historical evidence just because a newer run exists. Deduplicate repeated delivery by stable execution/event ID; supersede only through explicit correction/retraction semantics. If the intended metric is latest state, define it separately from aggregate reliability learning.
7. **Candidate fingerprint is underspecified:** V2 refers to `candidate_fingerprint` without a canonical schema/versioning rule. It must distinguish meaningful candidate changes and not merge candidates merely because route/assistant/config fields coincide.
8. **Cohort separation must be mandatory for every query:** scope prefixes are defense-in-depth, not a replacement for class filtering and consumer tests.
9. **InteractionPattern path needs full accounting:** gating `learn_from_execution()` alone cannot neutralize counters incremented earlier in `ToolMemory.remember_result()`; the local check must trace every consumer of these counters and patterns.

### Conservative adjudication

Treat V2 as `CONTRACT_READY_WITH_REPAIRS` for continued documentary specification only; it is **not yet implementation-ready**. Do not begin code changes from its present wording.

### Next route: targeted Codex local verification (no broad re-audit)

Ask Codex local for a read-only comparison of the exact dirty working tree against its declared HEAD, limited to:
- candidate identity fields `candidate_id`, `experiment_id`, `run_id`, and any candidate fingerprint in TaskOutcomeRecorder and SandboxExperimentService;
- ToolMemory result persistence, ToolCard counters, validation-state updates and interaction-learning writes for sandbox versus operational results;
- current local consumers of ToolCard counters/InteractionPattern, plus the local versions of ExperimentLab, AdaptiveWeightLayer and StrategySelector;
- whether any changed local source provides a verified execution attestation, evidence class, or explicit supersession/idempotency semantics;
- changed/unchanged status versus HEAD and exact source lines supporting each claim.

Do not edit files, run tests/code/build/runtime, inspect `data/` or SQLite, access M0A, or alter the 96 modified tracked paths and untracked `data/`. Classify each claim as `CONFIRMED_LOCAL`, `DIFFERS_FROM_PUBLIC`, or `UNRESOLVED`. After this narrow source report, revise V2 for consistency and conduct one bounded adversarial pass. No implementation until separately authorized.

Governance remains `KEEP_BLOCKED`. PR #467 remains branch-only, Draft and unmerged.
