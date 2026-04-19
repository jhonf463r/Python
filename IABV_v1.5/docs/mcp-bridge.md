# MCP Bridge — Devin ↔ IABV v1.5

Este documento describe cómo exponer los servicios core de IABV v1.5 como un
servidor MCP (Model Context Protocol) para que agentes externos (Devin, Claude,
Codex y cualquier otro cliente MCP-compatible) puedan consumirlos de forma
autónoma y gobernada.

El bridge **no** introduce otro cerebro ni otro orquestador: es un adaptador
delgado sobre `bootstrap.AppBootstrap` que registra tools sobre `FastMCP`.
Respeta `AutonomyGovernancePolicy`, `WorldModelService`, `PerceptionSnapshot` y
todas las capas cerradas P1–P4 (ver `AGENTS.md`).

---

## Tools expuestas (6 core)

| Tool                      | Servicio origen                             | Tipo    |
|---------------------------|---------------------------------------------|---------|
| `world_model_snapshot`    | `WorldModelService`                         | lectura |
| `orchestrator_preview`    | `AdaptiveTaskOrchestrator` (preview only)   | lectura |
| `site_exploration_explore`| `SiteExplorationService` (+ repository)     | escribe `site_manuals/` |
| `portable_context_get`    | `PortableContextService`                    | lectura |
| `self_examination_current`| `OperationalSelfExaminationService`         | lectura |
| `chatgpt_web_capture`     | `UIExecutionRunner._capture_browser_dom_response` | escribe (browser) |

`orchestrator_preview` sólo **previsualiza** (`build_decision_context_preview`);
no abre sesiones adaptativas ni gasta cuota externa. Para ejecución real hay que
seguir usando la UI controlada del programa.

`chatgpt_web_capture` respeta el contrato de `reingest_only=True` (PRs #13 y
#21): cuando está activo no repasa el prompt — sólo relee el DOM del hilo ya
abierto.

---

## Arquitectura (topología concreta)

```
+-----------------------------------+
|  Tu laptop Windows                |
|  C:\Python\IABV_v1.5              |
|                                   |
|  ┌──────────────────────────┐     |
|  │ AppBootstrap (bootstrap.py)│   |
|  │  - world_model_service      │   |
|  │  - adaptive_task_orchestrator│  |
|  │  - site_exploration_service │   |
|  │  - portable_context_service │   |
|  │  - self_examination_service │   |
|  │  - ui_execution_runner       │  |
|  └────────────┬─────────────┘     |
|               │                    |
|  ┌────────────▼──────────────┐    |
|  │ IABVMCPServer (FastMCP)   │    |
|  │  transport=streamable-http│    |
|  │  bind=127.0.0.1:8765      │    |
|  └────────────┬──────────────┘    |
|               │                    |
|  ┌────────────▼──────────────┐    |
|  │ cloudflared tunnel --url  │    |
|  │   https://xxx.trycloudflare.com
|  └────────────┬──────────────┘    |
+---------------┼-------------------+
                │
                ▼
+-----------------------------------+
|  Devin cloud VM (o cualquier      |
|  cliente MCP: Claude, Codex, ...) |
|  invoca tools sobre la URL pública|
+-----------------------------------+
```

---

## Instalación (laptop Windows)

Una sola vez:

```powershell
# 1. deps del programa (si todavía no estan)
cd C:\Python\IABV_v1.5
pip install -e .

# 2. deps del MCP server
pip install mcp uvicorn

# 3. cloudflared (tunnel sin cuenta)
winget install --id Cloudflare.cloudflared
```

---

## Arranque del bridge

Con el script incluido:

```powershell
cd C:\Python\IABV_v1.5
powershell -ExecutionPolicy Bypass -File scripts\run_mcp_bridge.ps1
```

El script:

1. Configura `PYTHONPATH`, `IABV_WORKSPACE_ROOT`, `FASTMCP_HOST/PORT` y
   `IABV_MCP_TRANSPORT=streamable-http`.
2. Arranca `python -m iabv_v15.infra.mcp.server` enlazado a `127.0.0.1:8765`.
3. Abre `cloudflared tunnel --url http://127.0.0.1:8765` y te imprime en consola
   una URL pública tipo `https://<sub>.trycloudflare.com`.
4. Cuando cortas `Ctrl+C`, mata el MCP server y cierra el tunnel.

Para transporte **stdio** (uso local directo con Claude Desktop, etc.):

```powershell
$env:IABV_MCP_TRANSPORT = 'stdio'
& 'C:\Users\faber\miniconda3\python.exe' -m iabv_v15.infra.mcp.server
```

---

## Registrar el server en Devin

1. Abrí la URL que imprime `cloudflared` (algo tipo
   `https://amber-spider-1234.trycloudflare.com`).
2. En Devin: **Settings → Integrations → MCP Servers → Add Custom MCP**.
3. Rellená:
   - Name: `iabv-v15`
   - URL: la URL del tunnel + `/mcp` (streamable-http expone el path `/mcp/` por defecto).
   - Transport: `streamable-http`
4. Save. A partir de ese momento cada sesión Devin tiene las 6 tools disponibles.

Para que la URL sea **estable** (no cambie entre arranques), usá el flujo
autenticado de Cloudflare Tunnel:

```powershell
cloudflared tunnel login
cloudflared tunnel create iabv-v15
cloudflared tunnel route dns iabv-v15 iabv.tu-dominio.com
cloudflared tunnel run --url http://127.0.0.1:8765 iabv-v15
```

---

## Gobernanza y límites

- Las tools sólo consumen servicios ya existentes: no duplican contratos.
- `AutonomyGovernancePolicy` sigue siendo la fuente de verdad; si el gate bloquea
  una ruta, la tool respeta ese bloqueo (p.ej. `chatgpt_web_capture` devuelve
  `error_message='browser_security_verification'` si Cloudflare bloquea).
- `WorldModelService` continúa siendo la única vista viva del sistema; las
  tools lo consultan pero no lo modifican.
- `PerceptionSnapshot` no se reemplaza; `orchestrator_preview` usa el flujo
  normal de construcción (`build_decision_context_preview`).
- No se expone `execute_now` ni creación de sesiones adaptativas para evitar
  que un cliente MCP abra sesiones que después queden huérfanas en el repositorio.

---

## Testing

Tests unitarios con fakes que reemplazan cada servicio:

```powershell
$env:PYTHONPATH = 'C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/test_mcp_server.py -q
```

Bateria completa (AGENTS.md):

```powershell
$env:PYTHONPATH = 'C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q
```

---

## UNRESOLVED / siguiente paso recomendado

- La URL `*.trycloudflare.com` del script rápido cambia en cada arranque. Para
  producción, configurar un tunnel nombrado con DNS propio (bloque autenticado
  al final de la sección de arranque).
- No hay autenticación por token sobre el MCP endpoint. Si el tunnel es público,
  cualquier cliente MCP podría invocar tools. Recomendado: agregar un header de
  auth cuando se pase a producción.
- `orchestrator_preview` sólo previsualiza por decisión explícita. Si en el
  futuro queremos exponer ejecución real vía MCP, debería pasar por un nuevo
  gate específico (`mcp_execute_gate`) para no bypassear la UI controlada.
