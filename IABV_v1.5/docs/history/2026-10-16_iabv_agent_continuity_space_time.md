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
