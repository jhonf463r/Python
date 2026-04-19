# Audit Tools MCP — Runbook Operativo

Runbook del Frente 1 del plan Devin ↔ IABV. Describe cómo operar las 5
audit tools que el MCP server de IABV v1.5 expone para auditoría humana.
El contrato vive en `IABV_v1.5/src/iabv_v15/infra/mcp/server.py` y
`IABV_v1.5/src/iabv_v15/infra/mcp/audit_tools.py`. A la fecha de este
runbook ese contrato se agrega en el PR #38
(`devin/1776638007-audit-mcp-tools`); este documento queda en `main` y
describe lo que ese PR expone, sin inventar nada adicional.

Audiencia: operador humano (Jhovanny) en Windows y Devin remoto
consumiendo las tools por MCP.

## 1. Introducción

Las audit tools son una capa delgada sobre `IABVMCPServer` que permite
observar el workspace del operador sin tocarlo: correr la batería
oficial de pytest, leer archivos de texto acotados, listar directorios
con marca de sensibilidad, capturar un screenshot de la UI cuando está
mapeada y leer estado git read-only. A diferencia de las tools de
consulta externa (`chatgpt_web_capture`, `site_exploration_explore`)
éstas no requieren red, no disparan autonomía ni navegación, y sólo
`run_pytest` ejecuta un subprocess acotado a la batería oficial. Todas
pasan por el mismo gate fail-closed
`_governance_block_for_route(assistant_kind="audit", requires_network=False)`.

## 2. Precondiciones

1. IABV corriendo local con el MCP server arriba
   (`python -m iabv_v15.infra.mcp.server`, transport default `stdio`,
   configurable con `IABV_MCP_TRANSPORT`).
2. Workspace montado en `C:\Python\IABV_v1.5`. El server resuelve el
   `workspace_root` server-side; el cliente MCP no lo elige.
3. `WorldModelService` vivo en el container de `AppBootstrap`. Sin él
   el gate devuelve `governance_blocked=True` con
   `reason="world_model_service_unavailable"`.
4. Ningún `OperationalBlockRecord` activo con `assistant_kind="audit"`,
   `"*"` o `""` en el snapshot actual (si hay, `reason="operational_block_active"`).
5. Ningún `permission_gate` con `status="requerido"` y `granted=False`
   para `audit`, `"*"` o `""` (si hay, `reason="permission_gate_required"`).

Respuesta típica cuando el gate bloquea:

```json
{"governance_blocked": true,
 "reason": "operational_block_active",
 "detail": "Hay bloqueos activos en WorldModelSnapshot para esta ruta.",
 "blocks": [ ... ]}
```

Posibles `reason`: `world_model_service_unavailable`,
`world_model_read_failed`, `world_model_snapshot_missing`,
`network_unavailable` (no aplica a audit porque `requires_network=False`),
`operational_block_active`, `permission_gate_required`.

## 3. Tool por tool

### 3.1 `run_pytest`

```python
@mcp.tool()
def run_pytest(
    suite: str | None = None,
    keyword: str | None = None,
) -> dict[str, Any]
```

Inputs válidos (`validate_pytest_suite` / `validate_pytest_keyword`):

- `suite` `None`/`""` → corre `tests/`.
- `suite` matchea `^tests(?:/[A-Za-z0-9_.\-]+)*/?$`
  (ej. `tests/`, `tests/ui/`, `tests/infra/mcp/`).
- `suite` matchea `^tests(?:/[A-Za-z0-9_\-]+)*?/test_[A-Za-z0-9_\-]+\.py$`
  (ej. `tests/test_foo.py`, `tests/ui/test_control_center.py`).
- `keyword` `None`/`""` o matchea `^[A-Za-z0-9_\-:\[\]\. ]{1,200}$`.

Ejemplos de input:

```json
{}
{"suite": "tests/infra/mcp/"}
{"suite": "tests/ui/test_control_center.py", "keyword": "collapse"}
```

Payload happy path:

```json
{"suite": "tests/", "keyword": null,
 "passed": 812, "failed": 0, "errors": 0,
 "returncode": 0, "duration_s": 183.21, "timed_out": false,
 "output_tail": "... 812 passed in 183.21s ..."}
```

Errores posibles:

- `invalid_suite` — suite fuera de la whitelist, absoluto, con `..`, o
  con caracteres no permitidos.
- `invalid_keyword` — keyword con caracteres fuera del patrón.
- `invalid_python_executable` — sólo para callers internos que pasen
  `python_executable` explícito; el tool MCP público no acepta ese
  parámetro.
- `workspace_missing` — `workspace_root` no existe o no es dir.

Evidencia típica: `output_tail` (últimos 4000 chars de stdout+stderr),
`returncode`, `duration_s`. Si `timed_out=true` superó
`PYTEST_TIMEOUT_SECONDS` (15 min) — registrar, no reintentar ciego.
Cuando falla, usar `read_repo_file` sobre el test afectado.

### 3.2 `read_repo_file`

```python
@mcp.tool()
def read_repo_file(relative_path: str) -> dict[str, Any]
```

Inputs válidos: `relative_path` relativo al workspace, sin `..`, no
absoluto, tras `resolve()` dentro de `workspace_root`, archivo
existente, no directorio, ≤ 1 MiB, UTF-8, fuera de la blacklist (§4.3).

Ejemplos:

```json
{"relative_path": "pyproject.toml"}
{"relative_path": "src/iabv_v15/bootstrap.py"}
{"relative_path": "tests/infra/mcp/test_audit_tools.py"}
```

Payload happy path:

```json
{"path": "pyproject.toml", "size": 2481,
 "content": "[project]\nname = \"iabv_v15\"\n..."}
```

Errores posibles: `invalid_path` (`None`/vacío),
`absolute_path_forbidden`, `parent_traversal_forbidden`,
`outside_workspace`, `sensitive_file_blocked`, `not_found`,
`is_directory`, `file_too_large`, `binary_not_supported`.

Evidencia típica: `path` normalizado a forward slash y la porción
relevante de `content`. No pegar el archivo completo en el log humano
si pesa varios KB.

### 3.3 `list_repo_directory`

```python
@mcp.tool()
def list_repo_directory(
    relative_path: str = "",
    max_entries: int = audit_tools.DEFAULT_LIST_MAX,
) -> dict[str, Any]
```

Inputs válidos: `relative_path` vacío o `"."` → raíz del workspace; si
no, relativo, sin `..`, no absoluto, dentro del workspace. `max_entries`
entero; se capea a `MAX_LIST_ENTRIES=200`, valores `<0` se suben a 1,
valor `0` se trata como `DEFAULT_LIST_MAX=200` porque la implementación
usa `int(max_entries or DEFAULT_LIST_MAX)` (`0` es falsy).

Ejemplos:

```json
{}
{"relative_path": "src/iabv_v15/infra/mcp"}
{"relative_path": "data/evolution", "max_entries": 50}
```

Payload happy path:

```json
{"path": "src/iabv_v15/infra/mcp",
 "entries": [
   {"name": "audit_tools.py", "type": "file", "size": 28143, "mtime": 1700000001.0, "sensitive": false},
   {"name": "server.py", "type": "file", "size": 22004, "mtime": 1700000002.0, "sensitive": false}],
 "truncated": false, "total_listed": 2, "total_available": 2}
```

`entries[i].type` puede ser `file`, `dir`, `symlink`, `other` o
`unknown`. `sensitive=true` marca entries que matchean la blacklist; la
tool las lista igual, pero `read_repo_file` las bloquea.

Errores posibles: `invalid_path`, `absolute_path_forbidden`,
`parent_traversal_forbidden`, `outside_workspace`, `not_found`,
`not_a_directory`.

Evidencia típica: `total_available` vs `total_listed` y `truncated`;
los nombres `sensitive=true` deben aparecer en la bitácora como señal
de que ese dir tiene material que nunca va a llegar por
`read_repo_file`.

### 3.4 `capture_ui_screenshot`

```python
@mcp.tool()
def capture_ui_screenshot(region: str = "control_center") -> dict[str, Any]
```

Input: `region` es un string libre que el `UIScreenshotProvider`
interpreta; no hay whitelist explícita en `audit_tools.py`.

Payload happy path:

```json
{"region": "control_center", "format": "png",
 "size_bytes": 48213, "bytes_base64": "iVBORw0KGgoAAAANSUhEUgAA..."}
```

Payload degradado (provider no registrado, host headless, provider que
falla o devuelve vacío):

```json
{"error": "ui_not_running",
 "detail": "No hay UIScreenshotProvider registrado en el container; probablemente la UI IABV no está corriendo o el host es headless.",
 "region": "control_center"}
```

`capture_ui_screenshot` nunca lanza excepción hacia el cliente; tira del
provider y traduce cualquier fallo a `{error: "ui_not_running", detail,
region}`. El gate de gobierno corre antes, así que también puede
devolver `governance_blocked=True` sin tocar la UI.

Evidencia típica: guardar `bytes_base64` decodificado como PNG en
`data/evolution/audit_screenshots/<timestamp>.png` y adjuntar ese path
al reporte humano.

### 3.5 `git_status_and_log`

```python
@mcp.tool()
def git_status_and_log(limit: int = audit_tools.DEFAULT_GIT_LOG_LIMIT) -> dict[str, Any]
```

Inputs: `limit` entero ≥ 1, default `DEFAULT_GIT_LOG_LIMIT=10`, capeado
a `MAX_GIT_LOG_LIMIT=100`.

Ejemplos: `{}` o `{"limit": 25}`.

Payload happy path:

```json
{"branch": "main", "ahead": 0, "behind": 0,
 "dirty_files": [{"status": "M", "path": "pyproject.toml"}],
 "dirty_count": 1,
 "last_commits": [
   {"sha": "d033688d...", "short_sha": "d033688d",
    "author": "Devin <devin-ai-integration[bot]@users.noreply.github.com>",
    "date_iso": "2026-04-18T20:14:09+00:00",
    "message": "fix(mcp-audit): normalize list_repo_directory path to forward slash on Windows"}]}
```

Payload degradado:

- `{"error": "not_a_git_repo", "detail": "..."}` si el probe
  `git rev-parse --is-inside-work-tree` no devuelve `true`.
- `{"error": "git_status_failed", "detail": "..."}` si `git status`
  tira non-zero.
- `{"error": "git_log_failed", "detail": "...", "branch", "ahead",
  "behind", "dirty_files"}` si `git log` tira; el status ya se computó.
- `workspace_missing` (excepción) si `workspace_root` no existe.

Evidencia típica: `branch`, `ahead`, `behind`, `dirty_count` y la
lista de `dirty_files` como snapshot previo a cualquier decisión.

## 4. Troubleshooting

### 4.1 El gate bloquea todo con `audit_blocked`

La etiqueta exacta en el payload es `governance_blocked=True`; el
operador lo verá en cualquier respuesta de las 5 tools. Diagnóstico:

1. Leer `reason`:
   - `world_model_service_unavailable` / `world_model_read_failed`
     / `world_model_snapshot_missing` → container sin
     `WorldModelService` vivo o `current_model()` tiró. Reiniciar IABV
     y revisar logs de `WorldModelService`.
   - `operational_block_active` → inspeccionar `blocks[]`. Cada entry
     viene serializada de `OperationalBlockRecord`; mirar
     `assistant_kind`, `reason`, `expires_at`. Scope `"*"`/`""` bloquea
     todo, no sólo audit.
   - `permission_gate_required` → aprobar el popup de clarificación en
     ControlCenter y reintentar.
2. Confirmar que ningún otro Frente emitió un bloqueo durante su
   ciclo (el gate no distingue emisor, sólo `scope`).
3. `network_unavailable` no debería aparecer en audit
   (`requires_network=False`); si aparece es regresión del gate →
   `UNRESOLVED`.

### 4.2 `run_pytest` responde `invalid_suite`

Whitelist real en `audit_tools.py`:

- `_SUITE_PATTERN = r"^tests(?:/[A-Za-z0-9_.\-]+)*/?$"`
  permite `tests/`, `tests/ui/`, `tests/infra/mcp/`, etc.
- `_SUITE_TESTFILE_PATTERN = r"^tests(?:/[A-Za-z0-9_\-]+)*?/test_[A-Za-z0-9_\-]+\.py$"`
  permite archivos `test_*.py` dentro de `tests/`.

Se rechaza: `suite` absoluto (`/...` o `\...`), con componente `..`,
fuera de `tests/` (ej. `src/`, `./tests/` sin norm), o archivos que no
empiezan con `test_` ni terminan en `.py`. Si el operador necesita
correr algo fuera de la whitelist, lo hace manual desde PowerShell
según `AGENTS.md`, no via MCP.

`invalid_keyword` aplica cuando `-k` trae caracteres fuera de
`[A-Za-z0-9_\-:\[\]\. ]` o > 200 chars.

### 4.3 `read_repo_file` responde `sensitive_file_blocked`

`SENSITIVE_GLOB_PATTERNS` matchea por nombre, path completo y cada
componente:

- `.env`, `.env.*`, `*.env`
- `credentials`, `credentials.*`, `credentials*.json`
- `*.key`, `*.pem`, `*.pfx`, `*.p12`
- `id_rsa`, `id_rsa.*`, `id_ed25519`, `id_ed25519.*`
- `secrets.json`, `secrets.*.json`
- `mcp_bridge.json`

Si el archivo matchea, `read_repo_file` lanza `sensitive_file_blocked`
aunque viva en subdirectorio. `list_repo_directory` sí lo muestra con
`sensitive=true`; es la forma correcta de confirmar que existe sin
leerlo. No hay workaround por MCP: renombrar el archivo o leerlo local
fuera de la tool.

### 4.4 `capture_ui_screenshot` degrada a `ui_not_running`

El payload real trae `error="ui_not_running"`; ese es el string exacto
que hay que buscar en logs y código (ver `audit_tools.py`). Causas:

- Container sin `UIScreenshotProvider` registrado (Linux CI, tests
  headless, MCP levantado sin UI). Esperado.
- Ventana IABV cerrada o minimizada en Windows; el provider puede
  decidir que no hay target válido y tirar, se traduce a
  `ui_not_running`.
- Provider devolvió `bytes` vacío o no-bytes.

Validación en Windows con UI abierta:

1. Abrir IABV (PySide6/QML) y dejar Control Center visible.
2. Pedir `capture_ui_screenshot` desde el cliente MCP.
3. Confirmar payload con `format="png"`, `size_bytes>0`,
   `bytes_base64` decodificable a un PNG real.

Si con la UI abierta sigue degradando es `UNRESOLVED` del provider;
registrar y pedir revisión al Frente 2 antes de insistir.

## 5. Seguridad y límites

- `read_repo_file` tope **1 MiB** (`MAX_READ_BYTES`), sólo **UTF-8**
  (`binary_not_supported` si no decodifica).
- `list_repo_directory` tope **200 entries** (`MAX_LIST_ENTRIES`);
  `max_entries` del cliente se capea.
- `run_pytest` timeout **15 min** (`PYTEST_TIMEOUT_SECONDS`);
  intérprete Python resuelto **server-side** (container → env
  `IABV_PYTEST_PYTHON` con validación estricta → `sys.executable`).
  El cliente MCP **no** elige binario.
- `git_status_and_log` timeout **20 s** (`GIT_TIMEOUT_SECONDS`);
  `limit` capeado a **100** (`MAX_GIT_LOG_LIMIT`). Lee sólo
  `git rev-parse`, `git status --porcelain=1 --branch` y
  `git log -n<limit> --pretty=format:...`; no escribe.
- Todas pasan por `_governance_block_for_route(assistant_kind="audit",
  requires_network=False)` antes de ejecutar; fail-closed si no hay
  `WorldModelSnapshot`.

## 6. Ejemplo de uso desde Devin remoto

Pseudo-secuencia, sólo las tools reales:

1. `git_status_and_log({})` → `{branch: "feature/foo", ahead: 2,
   behind: 0, dirty_count: 3, dirty_files: [...], last_commits: [...]}`.
2. Rama sucia → `run_pytest({"suite": "tests/ui/"})` →
   `{passed: 214, failed: 1, errors: 0, returncode: 1, output_tail:
   "... tests/ui/test_control_center.py::test_collapse FAILED ..."}`.
3. Devin extrae el archivo afectado del `output_tail` y pide
   `read_repo_file({"relative_path": "tests/ui/test_control_center.py"})`
   para ver el test que falla.
4. Con el contenido, Devin propone al humano un fix concreto. No lo
   aplica: las audit tools son read-only salvo la ejecución de pytest.
5. Si el fix requiere ver la UI real, Devin pide
   `capture_ui_screenshot({"region": "control_center"})`. Si responde
   `ui_not_running`, deja `UNRESOLVED` y pide al humano que valide con
   la UI abierta.
6. Antes de cerrar, `list_repo_directory({"relative_path":
   "data/evolution/self_examination", "max_entries": 20})` para
   confirmar que la evidencia del ciclo quedó persistida.

## 7. UNRESOLVED

- Screenshot real de la UI IABV sólo se valida con la UI activa en
  Windows; en host headless la tool degrada legítimamente a
  `ui_not_running` y no hay forma de confirmar el contenido desde
  Devin remoto sin observación humana.
- La disponibilidad real (y cuotas) de herramientas externas visibles
  no es parte de esta capa de audit; consultarla requiere permiso
  explícito del operador humano (ver `AGENTS.md`, sección *Regla De
  Observación Real*).
- `python_executable` del lado del cliente MCP: el tool público no lo
  expone, la validación existe para callers internos. Si un futuro
  caller lo expone, revalidar contra `validate_pytest_executable`
  antes de aceptarlo.
