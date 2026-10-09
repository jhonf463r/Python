# RQ223 — Diseño del contrato mínimo de autoridad de mutación para IABV MCP

**Resultado:** contrato de diseño reconciliado dentro del alcance; implementación bloqueada.  
**Estado global:** `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.  
**Baseline de lectura remota:** `ec35234c64faff2874ce1598d6c32206660801c7` (commit de inspección, no baseline de implementación).  
**Tipo de trabajo:** lectura estática y síntesis documental; sin implementación, pruebas ni runtime.

## 1. Decisión y alcance

RQ223 define el contrato conceptual mínimo para autorizar mutaciones privilegiadas de IABV MCP. No demuestra que el sistema actual pueda implementarlo, no selecciona una tecnología de identidad y no autoriza cambios de código.

Se mantiene el resultado de RQ219/RQ220: `NO_EXISTING_TRUSTED_AUTHORITY_FOUND_IN_SCOPE`. La lectura dirigida de la composición del broker y la UI concuerda con `UI_APPROVAL_BRIDGE_NOT_FOUND_IN_REPOSITORY_SCOPE` para las rutas de fuente examinadas. Estas conclusiones se limitan al alcance inspeccionado; no prueban que no exista autenticación o conexión externa en ningún otro lugar de IABV ni identifican qué bytes ejecutó un proceso histórico.

## 2. Evidencia fuente y límites de procedencia

Las referencias siguientes apuntan al commit remoto de lectura `ec35234c64faff2874ce1598d6c32206660801c7`, no a una afirmación sobre un runtime activo:

- [`bootstrap.py`, cableado de señales](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/bootstrap.py#L4080-L4117): se conectan rutas de credenciales, aclaraciones y dependencias; el recorrido no registra un `prompt_handler` para `HumanApprovalBroker`.
- [`human_approval_broker.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/services/security/human_approval_broker.py#L139-L153): ofrece registro de manejador y hook de preaprobación; su existencia no demuestra cableado funcional ni identidad autenticada.
- [`evolution_center_viewmodel.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py#L396-L425) y [`EvolutionCenterPage.qml`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml#L20-L34): los datos de solicitudes pendientes se exponen en la interfaz; en el recorrido inspeccionado no se demuestra una acción que cierre un retorno autenticado a `approve()`/`reject()`.
- [`server.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/infra/mcp/server.py#L377-L489) y [`self_update_tools.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/infra/mcp/self_update_tools.py#L49-L155): los mutadores examinados usan controles genéricos de gobernanza de ruta, no un recibo de autoridad del Owner ligado a la mutación concreta.
- [`self_update_tools.py`, ruta Git compuesta](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/infra/mcp/self_update_tools.py#L163-L250): el contrato existente incluye selección amplia de archivos y una ruta que puede ejecutar `git push`; esos defaults no pueden heredarse como autoridad implícita en la primera etapa.
- [`world_model_service.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py#L156-L180): `ObservationPermissionGate` modela permiso de observación, no autorización autenticada de escritura.
- [`approval_memory.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/services/security/approval_memory.py#L101-L223): la vía `pre_approver` puede resolver automáticamente; no satisface la aprobación explícita del Owner por cada mutación.
- [`proactive_dashboard_service.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/services/security/proactive_dashboard_service.py#L90-L160): representa solicitudes pendientes; la presentación no equivale a resolverlas con identidad verificada.
- [`tool_record_repository.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/infra/persistence/tool_record_repository.py#L74-L133) y [`tool_teach_service.py`](https://github.com/jhonf463r/Python/blob/ec35234c64faff2874ce1598d6c32206660801c7/IABV_v1.5/src/iabv_v15/services/tools/tool_teach_service.py#L749-L821): el ciclo de vida de `ToolTask` es una referencia de diseño, pero no se ha demostrado que constituya autoridad de mutación para los handlers MCP.

El informe local que dio lugar a RQ223 declara un worktree Windows detached/dirty, con `server.py` modificado y 394 entradas de estado. Esa es evidencia atribuida al actor; el coordinador no inspeccionó ese worktree ni rehashó localmente sus bytes. No debe tratarse como baseline limpio ni como evidencia del código cargado por un proceso histórico.

## 3. Contrato conceptual de autorización

La autorización debe quedar vinculada a una tupla conceptual:

`A = (P, O, R, S, D, T, N)`

- `P`: principal autenticado y facultado para decidir.
- `O`: operación concreta autorizada.
- `R`: recurso objetivo canónico.
- `S`: alcance exacto.
- `D`: contenido/delta o datos exactos aprobados cuando la operación modifica contenido.
- `T`: condiciones de vigencia.
- `N`: identificador único o mecanismo equivalente que impide reutilización.

Esta tupla expresa el contrato, no una API Python ni una elección de tecnología. La identidad, la decisión de autorización, el recibo consumible, la auditoría y el resultado del efecto son conceptos diferentes. Un booleano `approved=True`, una interacción humana, una política aprendida, un permiso de observación o un log no sustituyen esa garantía.

Las seis responsabilidades conceptuales son: autoridad del Owner; intención de mutación inmutable; solicitud correlacionada; decisión/recibo verificable; verificación y consumo por el mutador antes del primer efecto; y auditoría correlacionada. Son responsabilidades, no seis clases o servicios nuevos.

## 4. Órganos existentes: límites de reutilización

- `HumanApprovalBroker`: candidato a transporte de solicitud/decisión y correlación inicial; no es raíz de confianza demostrada.
- `ApprovalMemory`: puede aportar transparencia o aprendizaje no privilegiado; la preaprobación no puede autorizar la primera etapa.
- `ProactiveDashboardService` y UI: pueden presentar la solicitud; falta demostrar el retorno autenticado.
- `ToolRecordRepository`/`ToolTeachService`: referencias para el ciclo de vida de tareas; no equivalen a recibos MCP.
- `WorldModel` y gobernanza de ruta: controles útiles dentro de su dominio, pero no autorización del Owner para mutación.
- Gates de estrategia, credenciales y aprobación de PR: no son autoridad universal para escribir, parchear o ejecutar efectos Git locales.

RQ052 deja una lección metodológica de composición de órganos existentes, pero trata del ciclo de `ToolTask`; no acredita que ese circuito autorice mutaciones MCP.

## 5. Invariantes de la primera etapa aceptados en RQ218

- Aprobación explícita del Human Domain Owner, vinculada a cada operación, recurso canónico y alcance exacto.
- Denegar antes del primer efecto ante autoridad ausente/desconocida, rechazo, error, recibo malformado, vencido, consumido o discordante.
- Verificar de nuevo la ruta canónica, recurso, contenido previo, alcance y baseline relevantes inmediatamente antes del efecto.
- Uso único y prevención de replay/races; si no puede asegurarse el consumo fiable, denegar.
- Raíz de workspace y rutas protegidas bajo política explícita; no inferirlas desde el CWD.
- Git con selección explícita de archivos, revisión del diff, rechazo de cambios staged ajenos y cambios concurrentes invalidantes; **sin `push` en el primer tramo**.
- Estado de red desconocido bloquea las rutas que requieren red; la conectividad nunca autoriza una mutación.
- Timeout, cancelación, respuesta tardía y reinicio no pueden producir permiso por defecto ni reejecutar una intención con un recibo viejo.

Cada efecto compuesto (escritura, parche, stage, commit, checkout, pull, merge y push) debe tratarse según su autoridad concreta. Si el entrypoint existente no puede demostrar estos límites, se bloquea para esa operación.

## 6. Alternativas consideradas

**A — Broker síncrono:** menor cambio conceptual, pero exige timeout finito, no bloquear el canal UI, retorno autenticado y recibo independiente; el estado en memoria no ofrece reanudación durable demostrada.

**B — Flujo asíncrono y reanudación:** evita esperar bloqueando, pero necesita persistir correlación e intención original, resolver reinicios/duplicados/expiración y revalidar recursos y baseline antes de ejecutar.

**C — Dashboard como interfaz de decisión:** puede aportar presentación; añadir botones no acredita identidad ni autoriza el efecto.

**D — Preaprobación aprendida:** descartada como mecanismo de autorización privilegiada de la primera etapa.

Recomendación de diseño: conservar `HumanApprovalBroker` como candidato de transporte, no como raíz de confianza. La elección entre sincronía y asincronía queda supeditada a resolver identidad autenticada, retorno UI, recibo y garantías del ciclo de vida.

## 7. Dependencias abiertas y decisiones del Owner

**Bloqueo sustantivo:** no se ha demostrado una fuente autenticada de identidad/autoridad del Human Domain Owner conectada al camino de respuesta del broker que respalde una decisión verificable y ligada a una mutación concreta. No se presupone firma, MAC, almacén criptográfico, identidad del sistema operativo ni proveedor de identidad.

Antes de cualquier implementación siguen pendientes:

1. Identificar o diseñar y aceptar explícitamente la fuente de confianza del Owner y la semántica de emisión/verificación del recibo.
2. Definir vigencia, consumo único durable, prevención de replay y comportamiento si falla la persistencia o el verificador.
3. Fijar la raíz canónica permitida del workspace y la lista de rutas protegidas.
4. Elegir un baseline inmutable exacto y autorizar un worktree limpio separado; preservar el worktree dirty/detached existente.
5. Precisar el alcance de los archivos editables y la auditoría necesaria.

RQ218 ya aceptó la dirección normativa conservadora; no hace falta volver a adjudicarla. La tecnología de confianza, la raíz, el baseline y el alcance no están concedidos por RQ223.

## 8. Criterios para una implementación futura

La aceptación futura exige demostrar, en los mutadores reales y antes del primer efecto: fuente de autoridad fundamentada; identidad autenticada; intención inmutable; enlace exacto entre operación/recurso/alcance/contenido; recibo verificable y vigente; consumo único durable; denegación de replay, carreras, rutas protegidas y discordancias; alcance Git explícito sin push; manejo seguro de timeout/reinicio; y evidencia auditable de solicitud, identidad, decisión, consumo y resultado.

Las pruebas y la verificación runtime requerirán autorización separada. Este documento no autoriza implementación.

## 9. Reconciliación epistemológica

**FACT dentro del alcance:** handlers examinados usan gobernanza genérica; el gate de WorldModel es de observación; el broker no demuestra por sí mismo identidad/recibo del Owner; el retorno UI no se demuestra en el recorrido examinado; el ciclo de ToolTask no equivale a autoridad MCP; RQ218 aceptó la política conservadora.

**INFERENCE:** hace falta una decisión confiable, un recibo ligado a la intención y una verificación obligatoria previa al efecto; los órganos actuales sólo aportan piezas parciales.

**UNPROVEN:** fuente de identidad/autoridad confiable; productor/verificador de recibo; prevención efectiva de replay/carreras/concurrencia; contención runtime/MCP y bytes históricos cargados; integridad de toda la auditoría.

## 10. Adjudicación y siguiente frontera

- RQ223: diseño conceptual reconciliado dentro del alcance; implementación `BLOCKED`.
- Readiness global: `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.
- RQ219/RQ220: no repetir la búsqueda amplia ni la inspección broker/UI ya delimitada. Sólo una nueva lectura estática si aparece una dependencia concreta (llamante de `approve`, definición directa de identidad o productor/verificador específico).
- **RQ224 — siguiente frente:** diseño estático de la fuente de confianza de identidad/autoridad y del productor/verificador que faltan. Separar mecanismos existentes demostrados de opciones hipotéticas; detenerse si exige recorrer un subsistema general de identidad no delimitado.
- RQ218 sigue siendo política de diseño, no autorización de implementación.
- Sin cambios de código, pruebas/builds, runtime, operaciones MCP, inspección de procesos o mutación del worktree. RQ13-111 y RQ21.200 permanecen separados.

---
