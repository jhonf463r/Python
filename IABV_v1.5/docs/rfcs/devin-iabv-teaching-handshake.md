# RFC: Handshake Devin ↔ IABV para auditoría humana y auto-enseñanza

- **Estado:** borrador (Frente 3 del plan Devin ↔ IABV v1.5)
- **Última revisión:** 2026-04-19 — UNRESOLVED #1 (`run_self_audit`) y #2
  (`data/evolution/self_audit/`) cerradas por PR #44
  (`534ec7c8f978d31df148d00a7a86b0065785131c`).
- **Alcance:** documentación. No implica cambios de código.
- **Ubicación:** `IABV_v1.5/docs/rfcs/devin-iabv-teaching-handshake.md`
- **Relacionados:** PR #38 (Frente 1: 5 audit tools + governance gate
  `assistant_kind="audit"`), PR #44 (Frente 2: `SelfAuditService` +
  `run_self_audit`), `IABV_v1.5/AGENTS.md`,
  `src/iabv_v15/infra/mcp/server.py`,
  `src/iabv_v15/infra/mcp/audit_tools.py`,
  `src/iabv_v15/services/evolution/operational_self_examination_service.py`,
  `src/iabv_v15/services/evolution/portable_context_service.py`,
  `src/iabv_v15/services/evolution/world_model_service.py`.

## 1. Resumen

El handshake Devin ↔ IABV es un protocolo de lectura y propuesta entre una
sesión remota de Devin y la instancia local de IABV v1.5 sobre el MCP bridge
ya existente. Devin observa el estado operativo real de la laptop del usuario
a través de tools read-only (world model, portable context, auto-examinación
y las 5 audit tools de Frente 1) y, con esa evidencia, propone planes al
operador humano. Devin nunca ejecuta mutaciones locales ni escribe en el
repo sin PR: todo cambio pasa por aprobación humana y, si corresponde, por
un pull request revisado en GitHub.

## 2. Motivación

### 2.1. Desde la perspectiva del operador humano

El operador ya dispone de tres superficies de visibilidad dentro de IABV:
`pending_issues`, los resúmenes de `OperationalSelfExaminationService` (P4) y
la vista del `EvolutionCenterViewModel`. Son suficientes para auditar lo que
el sistema cree que le pasa, pero no para invitar a una sesión remota a
participar sin abrir la puerta a una autonomía no gobernada. Lo que el
operador necesita es una forma documentada y acotada de decirle a Devin:
"mirá el snapshot que IABV ya construye, proponé, y yo reviso". El handshake
formaliza esa invitación — qué tools se exponen, qué no, y dónde queda la
traza.

### 2.2. Desde la perspectiva del sistema (IABV)

IABV ya tiene las piezas para aprender de sí mismo: P1 cierra `WorldModel`,
P2 cierra neuroplasticidad, P3 cierra contexto portable y P4 cierra
auto-examinación. Lo que falta no es otra capa de cerebro sino un canal
donde un asistente externo pueda leer el estado consolidado, compararlo con
evidencia previa y sugerir ajustes sin pasar por encima de
`AutonomyGovernancePolicy`. El `pending_issue_repository` actual captura
hallazgos internos pero no está pensado para recibir propuestas externas
trazables; el P4 detecta regresiones pero no dispara auto-enseñanza cuando
la raíz del problema está fuera del sistema (ej. disponibilidad real de una
tool externa que nunca fue observada con permiso). El handshake ocupa ese
hueco: convierte una sesión Devin en una fuente de propuestas reviewables,
con la misma estructura que el resto del aprendizaje acumulativo.

## 3. No-goals

El handshake no hace, y no debe hacerse pasar por:

- **No crear otro cerebro ni otro orquestador.** `AdaptiveTaskOrchestrator`,
  `TaskContextAssembler` y `AutonomyGovernancePolicy` siguen siendo las
  únicas autoridades de decisión local. El rol de Devin es observar y
  proponer, nunca decidir ruta operativa.
- **No reemplazar `PerceptionSnapshot`, `WorldModelSnapshot` o
  `EnvironmentSelfModel`.** El handshake consume esos contratos; no los
  duplica, no los transforma y no deriva una versión paralela.
- **No convertir un ViewModel en decisor de rutas.**
  `EvolutionCenterViewModel` y `ControlCenterViewModel` solo muestran y
  disparan flujos aprobados; una propuesta de Devin debe pasar por el mismo
  flujo que cualquier otra sugerencia humana.
- **No pretender que Devin escriba en el repo sin PR.** Cualquier cambio en
  código, config, datos o artefactos de `data/evolution/...` pasa por un
  pull request revisado por el operador (o por el Devin principal) antes de
  mergearse. El handshake no habilita commits directos a `main`.
- **No habilitar red desde las audit tools.** Las 5 audit tools usan
  `requires_network=False`; el handshake no abre una vía encubierta para
  rutas externas nuevas.
- **No sustituir `pending_issues`.** El handshake produce propuestas que se
  materializan como `pending_issue` o como una entrada visible en UI, no
  como una categoría de registro propia.

## 4. Flujo end-to-end del handshake

El flujo asume que el MCP bridge ya está expuesto por
`IABVMCPServer` (`src/iabv_v15/infra/mcp/server.py`) y que Devin tiene
permiso para conectarse como cliente MCP (transport `stdio`, `sse` o
`streamable-http` según la configuración local del operador). Ningún paso
implica autonomía externa: todas las mutaciones quedan en mano del humano.

1. **Devin pide el estado operativo consolidado.** Antes de proponer
   cualquier cosa Devin llama, vía MCP, a `world_model_snapshot` y a las
   audit tools relevantes del Frente 1 (`run_pytest`, `read_repo_file`,
   `list_repo_directory`, `capture_ui_screenshot`, `git_status_and_log`).
   Estas últimas pasan por el gate `_governance_block_for_route(
   assistant_kind="audit", requires_network=False)`; si hay un
   `OperationalBlockRecord` activo sobre `audit` o `*`, o si falta un
   `ObservationPermissionGate` requerido, el bridge responde
   `{governance_blocked: True, reason, detail, ...}` y Devin no recibe
   datos. El comando lógico "run_self_audit" mencionado por el operador en
   conversaciones previas **no existe hoy como tool MCP**: queda
   `UNRESOLVED` y, mientras tanto, el agrupamiento de las 5 audit tools
   cumple ese rol a nivel de protocolo.
2. **IABV devuelve un snapshot consolidado.** Devin arma su propia vista a
   partir de cuatro llamadas idempotentes: `world_model_snapshot` (ventanas,
   foco, red, tools, bloqueos), `portable_context_get` (paquete P3 con
   contexto portable reciente), `self_examination_current` (review P4 con
   patrones, riesgos y ajustes recomendados) y las audit tools. La respuesta
   incluye evidencia fresca de `tool_checks`, `environment match` (vía
   `EnvironmentSelfModel` embebido en el portable context), `pending_issues`
   recientes, un `world_model` digest y el `summary` markdown generado por
   `OperationalSelfExaminationService.review_summary`.
3. **Devin decide si propone un plan; nunca ejecuta cambios locales.** Con
   el snapshot en mano Devin puede: (a) archivar el material como evidencia
   de auditoría, (b) abrir un PR con cambios de documentación o código en
   GitHub siguiendo el workflow normal (commit + PR + review), (c) redactar
   una propuesta destinada a aparecer en la UI de IABV como `pending_issue`
   o como tarjeta de `EvolutionCenterViewModel`. Devin jamás corre comandos
   mutadores sobre la laptop del operador; ni siquiera indirectamente vía
   MCP — no hay tool de escritura expuesta fuera de los escritores
   legítimos preexistentes (`chatgpt_web_capture`, `site_exploration_explore`),
   que además siguen sujetos a governance.
4. **IABV recibe el plan como propuesta en UI o como pending issue.** Cuando
   Devin propone un cambio, la entrada se materializa por canales humanos:
   un `pending_issue` nuevo, un comentario en PR, o un ítem en la tarjeta de
   auto-examinación. El operador aprueba manualmente. Si la propuesta
   implica código, la aprobación se traduce en un merge de PR; si implica
   datos o configuración, en una acción local ejecutada por el operador o
   por IABV con su governance habitual. El handshake no introduce un camino
   automático entre propuesta y aplicación.

## 5. Contratos MCP usados

Todos los contratos son los ya expuestos por
`IABVMCPServer._register_tools`. Una línea por cada tool:

- **`world_model_snapshot(refresh: bool = False, full: bool = False)`** —
  input: banderas de refresh. Output: `WorldModelSnapshot` serializado
  (ventanas, foco, red, tools, `block_records`, `permission_gates`).
  Efectos: opcional refresh vivo vía `WorldModelService.request_refresh`.
  Governance gate: no bloquea por `assistant_kind="audit"` (es lectura del
  propio world model); sigue sujeto a que `world_model_service` exista.
- **`portable_context_get(refresh: bool = False, max_age_seconds: int = 300)`** —
  input: banderas de frescura. Output: `PortableContextPackage` condensado
  (P3). Efectos: puede reconstruir el paquete si el cache está stale.
  Governance gate: no aplica `assistant_kind="audit"` (es un servicio de
  solo lectura interno).
- **`self_examination_current(refresh: bool = False)`** — input: bandera
  de refresh. Output: `{review, summary}` con el `SelfExaminationSnapshot`
  y su resumen markdown. Efectos: reconstrucción de review P4 si corresponde.
  Governance gate: mismo criterio que `portable_context_get`.
- **`run_pytest(suite: str | None, keyword: str | None)`** — input: suite
  whitelisted (`tests/`, `tests/subdir/`, `tests/test_*.py`) y `-k`
  opcional (alphanum + `_.:[]-`). Output: `{passed, failed, errors,
  returncode, duration_s, timed_out, output_tail}`. Efectos: subproceso
  pytest server-side con `PYTHONPATH=src/` y timeout 15 min; el intérprete
  se resuelve server-side (config → `EnvironmentSelfModel.runtime_profile` →
  `IABV_PYTEST_PYTHON` → `sys.executable`). Governance gate:
  `assistant_kind="audit"`, `requires_network=False`.
- **`read_repo_file(relative_path: str)`** — input: ruta relativa dentro
  del workspace. Output: `{path, size, content}` UTF-8 o error tipado.
  Efectos: lectura read-only ≤ 1 MiB. Governance gate:
  `assistant_kind="audit"`, `requires_network=False`. Aplica blacklist de
  secrets (`SENSITIVE_GLOB_PATTERNS` en `audit_tools.py`) y rechaza
  paths absolutos, `..` y symlinks que escapan del workspace.
- **`list_repo_directory(relative_path: str = "", max_entries: int = 200)`** —
  input: ruta relativa (vacía = raíz del workspace). Output:
  `{path, entries: [{name, type, size, mtime, sensitive}], truncated,
  total_listed, total_available}`. Efectos: listado read-only con cap en
  `MAX_LIST_ENTRIES=200`. Governance gate: igual que `read_repo_file`.
- **`capture_ui_screenshot(region: str = "control_center")`** — input:
  etiqueta de región. Output: payload con imagen base64 o
  `{error: "ui_not_running", detail, region}` si no hay
  `ui_screenshot_provider` registrado. Efectos: captura vía provider del
  container (`QScreen.grabWindow` / `mss` en Windows real). Governance gate:
  `assistant_kind="audit"`, `requires_network=False`.
- **`git_status_and_log(limit: int = 10)`** — input: límite de commits
  (`DEFAULT_GIT_LOG_LIMIT=10`, cap `MAX_GIT_LOG_LIMIT=100`). Output:
  `{branch, ahead, behind, dirty_files, dirty_count, last_commits}` o
  `{error: "not_a_git_repo"}`. Efectos: `git rev-parse`, `git status
  --porcelain -b`, `git log --pretty=...`, todos read-only, timeout 20 s.
  Governance gate: `assistant_kind="audit"`, `requires_network=False`.
- **`run_self_audit(reason: str | None = None)`** — input: motivo
  opcional libre (se propaga a la traza y al markdown resultante). Output:
  `SelfAuditSnapshot` serializado como `dict` JSON-safe con
  `tool_checks`, `environment_match`, `pending_issues`,
  `world_model_digest`, `summary_markdown` y `generated_at` (ISO 8601).
  Efectos: agrega tool checks vía `ToolCard.dry_check`, compara
  `EnvironmentSelfModel` vs `WorldModelSnapshot`, recolecta hallazgos de
  autoexaminación y **persiste** los 3 artefactos descritos en la
  sección 7 (`data/evolution/self_audit/latest.json`, `latest.md`,
  `history/<ISO>.json`). Governance gate:
  `assistant_kind="audit"`, `requires_network=False`; si el
  `self_audit_service` no está disponible devuelve
  `{"error": "self_audit_unavailable", ...}` en lugar de crashear.
  Cerrada por PR #44
  (`534ec7c8f978d31df148d00a7a86b0065785131c`).

## 6. Governance

### 6.1. Bloqueos vigentes

- **Audit tools (`assistant_kind="audit"`).** Las 5 audit tools pasan por
  `_governance_block_for_route(assistant_kind="audit",
  requires_network=False)`. Un `OperationalBlockRecord` activo con scope
  `audit` o `*` freezea toda la auditoría humana sin afectar al resto del
  bridge. Un bloqueo para otra ruta (`chatgpt_web`, `site_crawler`) no
  impacta el handshake.
- **Rutas externas preexistentes.** `site_exploration_explore` y
  `chatgpt_web_capture` siguen sujetos a sus propios gates con
  `requires_network=True` y `assistant_kind` específicos. El handshake no
  los toca.
- **Lecturas internas.** `world_model_snapshot`, `portable_context_get` y
  `self_examination_current` no pasan por el gate de `audit` porque son
  lecturas del propio sistema; si el `world_model_service` está disponible
  se entregan, si no, la tool devuelve error explícito.

### 6.2. Modos degradados

- **Sin red.** Las audit tools son locales; la ausencia de red no las
  bloquea. Las rutas externas (`chatgpt_web_capture`,
  `site_exploration_explore`) siguen bloqueadas por su propio
  `requires_network=True` vía `network_status.connected`.
- **`OperationalBlockRecord` activo.** Si hay un bloqueo activo con
  `assistant_kind in {"audit", "*", ""}`, el bridge responde
  `{governance_blocked: True, reason: "operational_block_active", blocks:
  [...]}` y Devin recibe la evidencia del bloqueo pero no los datos.
- **Permiso de observación real ausente.** Si hay un
  `ObservationPermissionGate` en estado `requerido` sin conceder para
  `audit` o `*`, el bridge responde `{governance_blocked: True, reason:
  "permission_gate_required", permission_gates: [...]}`. El operador debe
  aprobar el popup de clarificación antes de reintentar. Sin permiso no se
  declara la herramienta disponible ni se invade la ventana externa: es la
  regla de observación real del AGENTS.md.
- **`world_model_service` caído.** Fail-closed:
  `{governance_blocked: True, reason: "world_model_service_unavailable"}`.
  No hay fallback a ejecución ciega.

## 7. Observabilidad y evidencia

Persistencia canónica (las rutas existen en el repo salvo donde se marca
UNRESOLVED):

- **`data/evolution/world_model/`** — snapshots y cache del
  `WorldModelService`. Fuente viva del estado operativo consumido por el
  handshake.
- **`data/evolution/portable_context/`** — incluye
  `latest.json` y `latest.md` generados por `PortableContextService`.
  Cualquier ejecución de `portable_context_get` se apoya o actualiza este
  directorio.
- **`data/evolution/self_examination/`** — incluye `latest.json` y
  `latest.md` del `OperationalSelfExaminationService`. Es la referencia
  humana para revisar qué vio el sistema en su última autoexaminación.
- **`data/evolution/self_audit/`** — directorio materializado por
  `SelfAuditService` (PR #44,
  `534ec7c8f978d31df148d00a7a86b0065785131c`) con 3 artefactos por cada
  corrida de `run_self_audit`:
  - `latest.json` — `SelfAuditSnapshot` serializado: `tool_checks`
    (lista de `ToolCheckResult` con `id`, `available`, `status`,
    `reason`, `evidence`), `environment_match` (`matched`,
    `mismatches`, `environment_digest`, `world_model_digest`),
    `pending_issues` (hallazgos agregados de autoexaminación),
    `world_model_digest`, `summary_markdown`, `reason`, `generated_at`.
  - `latest.md` — versión humana del `summary_markdown`: lista
    legible de tools chequeadas, estado del entorno y pending issues
    consolidados, pensada para que el operador la abra sin parsear JSON.
  - `history/<ISO>.json` — snapshot inmutable de cada corrida
    archivado por timestamp UTC ISO 8601, útil para auditoría
    retrospectiva y comparación entre corridas.
- **`data/evolution/pending_issues/`** — destino habitual de hallazgos
  humanos y de propuestas resultantes del handshake cuando se convierten
  en acciones concretas.

### 7.1. Cómo el usuario revisa lo que pasó

1. Revisa `data/evolution/self_examination/latest.md` para ver el resumen
   P4 reciente.
2. Revisa `data/evolution/portable_context/latest.md` para ver qué
   contexto portable devolvió el bridge.
3. Abre la UI (`EvolutionCenterViewModel`) para ver `pending_issues`,
   autoexaminación y propuestas activas.
4. Si hubo una sesión Devin asociada, revisa el PR que quedó abierto en
   GitHub y la conversación del handshake. El PR es la fuente de verdad
   para cualquier cambio proveniente del handshake.

## 8. Seguridad

### 8.1. Devin nunca ejecuta comandos arbitrarios

- `run_pytest` acepta solo `suite` que matchee el regex
  `_SUITE_PATTERN` / `_SUITE_TESTFILE_PATTERN` de `audit_tools.py`
  (`^tests(?:/[A-Za-z0-9_.\-]+)*/?$` y
  `^tests(?:/[A-Za-z0-9_\-]+)*?/test_[A-Za-z0-9_\-]+\.py$`) y `keyword`
  que matchee `_KEYWORD_PATTERN` (`^[A-Za-z0-9_\-:\[\]\. ]{1,200}$`).
  Cualquier otro valor se rechaza con `AuditToolError`.
- El intérprete Python se resuelve **server-side** vía la jerarquía
  documentada en `IABVMCPServer._pytest_python_executable`: config →
  `EnvironmentSelfModel.runtime_profile.python_executable` →
  `IABV_PYTEST_PYTHON` → `sys.executable`. El client MCP no puede elegir
  binario; pasar uno desde fuera ni siquiera aparece en el contrato de la
  tool.
- El timeout (`PYTEST_TIMEOUT_SECONDS=15 min`) evita que una invocación
  pueda colgar el bridge indefinidamente.

### 8.2. Blacklist de archivos sensibles

`read_repo_file` y `list_repo_directory` usan
`audit_tools.SENSITIVE_GLOB_PATTERNS`:

```
.env, .env.*, *.env, credentials, credentials.*, credentials*.json,
*.key, *.pem, *.pfx, *.p12, id_rsa, id_rsa.*, id_ed25519,
id_ed25519.*, secrets.json, secrets.*.json, mcp_bridge.json
```

- `read_repo_file` responde `sensitive_file_blocked` para cualquier coincidencia.
- `list_repo_directory` no oculta: marca la entry con `sensitive=true` para
  que el operador vea qué hay, sin permitir lectura.
- `resolve_workspace_path` rechaza paths absolutos, `..` y symlinks que
  apunten fuera del `workspace_root` resuelto.

### 8.3. Acceso a la UI

`capture_ui_screenshot` depende de `container.ui_screenshot_provider`. Si
no está registrado (Linux CI, UI apagada, sandbox), la tool degrada
explícito a `{error: "ui_not_running"}`. Un provider registrado sin
permiso explícito del operador no debe ser considerado cobertura
suficiente: la regla de observación real del AGENTS.md prevalece. El
sandbox de Devin no tiene acceso directo al escritorio Windows del
operador — depende de que IABV corra localmente y haya autorizado el
bridge.

### 8.4. Superficie de mutación

Las únicas tools MCP con efectos escritores son las preexistentes
(`chatgpt_web_capture`, `site_exploration_explore`) y quedan fuera del
handshake. El handshake, por definición, no introduce ni habilita mutación
remota.

## 9. Riesgos y mitigaciones

### 9.1. Flood de `run_pytest`

**Riesgo.** Una sesión Devin puede disparar batería completa en loop y
saturar la CPU/disco del operador, además de enmascarar resultados reales.
**Mitigación.** (a) Timeout duro en `PYTEST_TIMEOUT_SECONDS=15 min`. (b)
Whitelist de suites que obliga a ser específico. (c) Governance gate
`assistant_kind="audit"`: el operador puede emitir un
`OperationalBlockRecord` temporal que freezee la auditoría sin desactivar
el bridge. (d) Traza de duración en `output_tail` para que el operador
detecte abuso.

### 9.2. Envenenamiento de `IABV_PYTEST_PYTHON`

**Riesgo.** Si un proceso local malicioso exporta `IABV_PYTEST_PYTHON`
apuntando a un binario arbitrario, `run_pytest` podría terminar ejecutando
ese binario.
**Mitigación.** `validate_pytest_executable` valida basename `python*`,
existencia y ausencia de metacaracteres de shell antes de aceptar el
override. Si la validación falla, el resolver cae al siguiente nivel de la
jerarquía. La env var no sobrescribe config ni `EnvironmentSelfModel`: es
el último recurso antes de `sys.executable`. Recomendación operativa:
fijar `pytest_python_executable` en la config del container para evitar
sorpresas.

### 9.3. Pérdida de contexto entre sesiones Devin

**Riesgo.** Cada sesión Devin arranca sin memoria local; sin un
mecanismo de continuidad, el handshake se vuelve repetitivo y propenso a
proponer lo mismo varias veces.
**Mitigación.** `PortableContextService` (P3) condensa el estado vivo y
el aprendizaje persistido en un único paquete reutilizable. Devin llama a
`portable_context_get` al inicio del handshake; la nueva sesión hereda lo
que sabía la anterior sin releer historial bruto.

### 9.4. Falsa sensación de autonomía

**Riesgo.** Que una sesión Devin genere muchas propuestas parezca
"autonomía" y empuje al operador a mergear sin revisar.
**Mitigación.** Todo cambio pasa por PR (ver §4 y §3); el bridge no tiene
ruta de escritura para datos internos; la UI muestra propuestas como
`pending_issues` que requieren aprobación manual; el AGENTS.md prohíbe
explícitamente convertir ViewModels en decisores. El handshake redobla
esta disciplina documentándola.

### 9.5. Disponibilidad real de tools externas desconocida sin permiso

**Riesgo.** Sin permiso explícito de observación, Devin no puede saber si
una herramienta externa visible (ChatGPT web, por ejemplo) está utilizable
en ese momento. Asumirla disponible y recomendarla lleva a decisiones
ciegas.
**Mitigación.** El governance gate bloquea la ruta si el
`ObservationPermissionGate` está `requerido` sin conceder. Devin debe
marcar el hallazgo como `UNRESOLVED` hasta que el operador apruebe el
popup o conceda el permiso. AGENTS.md es explícito: "no declares la
herramienta disponible si no pudiste verificarla".

### 9.6. Stale snapshots

**Riesgo.** `portable_context_get` y `self_examination_current` usan cache
con `max_age_seconds=300` por defecto; si el operador no fuerza
`refresh=True`, Devin puede trabajar sobre una foto vieja.
**Mitigación.** Documentar en el handshake que para decisiones críticas
el primer llamado debe usar `refresh=True`; para revisiones periódicas, el
cache es aceptable. El `world_model_snapshot` acepta `refresh=True` con
`full=True` cuando se necesita un barrido profundo.

## 10. UNRESOLVED

Puntos que solo el operador valida con IABV corriendo en Windows real y
que quedan fuera del alcance de este RFC:

- **Screenshot de ventana IABV vía `capture_ui_screenshot`.** En Linux CI
  no hay `ui_screenshot_provider`; el wiring del provider real en
  `bootstrap.py` se valida en la laptop del usuario, no aquí.
- **Botón QML "Auditarme ahora" del Frente 2.** Entrada de UI que dispara
  el handshake desde `ControlCenterViewModel.runSelfAuditNow`; requiere
  validación en Windows con UI IABV viva (PySide6 + QML real), fuera del
  alcance de CI Linux.
- **Disponibilidad real de mensajes/cuota en herramientas externas
  visibles.** Sin permiso explícito de observación, el handshake no puede
  confirmar cuota ni foco de ChatGPT web / otras tools; queda
  `UNRESOLVED` conforme a AGENTS.md.
- **`EnvironmentSelfModel.runtime_profile.python_executable`.** El valor
  real depende del entorno Windows del operador; los tests no pueden
  validar que el intérprete resuelto server-side coincida con el esperado
  sin ejecutar en la máquina del usuario.
