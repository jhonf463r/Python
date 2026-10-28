# MCP Bridge — Devin ↔ IABV v1.5

> **Estado operativo actual — DESHABILITADO:** el inicio del servidor MCP y
> cualquier túnel (`cloudflared`) se rechazan mientras G1/G2/G3 no estén
> establecidos y no exista una ruta de aceptación autorizada. Los diagramas y
> descripciones siguientes son inventario histórico/de diseño; sus comandos,
> toggles y configuraciones no son instrucciones ejecutables en el estado
> actual. No hay variable de entorno ni modo local que omita esta denegación.

Este documento describe cómo exponer los servicios core de IABV v1.5 como un
servidor MCP (Model Context Protocol) para que agentes externos (Devin, Claude,
Codex y cualquier otro cliente MCP-compatible) puedan consumirlos de forma
autónoma y gobernada.

El bridge **no** introduce otro cerebro ni otro orquestador: es un adaptador
delgado sobre `bootstrap.AppBootstrap` que registra tools sobre `FastMCP`.
Respeta `AutonomyGovernancePolicy`, `WorldModelService`, `PerceptionSnapshot` y
todas las capas cerradas P1–P4 (ver `AGENTS.md`).

---

## Inventario de tools diseñado (6 core; no expuestas actualmente)

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

## Instalación histórica (no requerida ni habilitante mientras el bridge esté bloqueado)

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

## Arranque del bridge — deshabilitado

`start_iabv.ps1`, `run_mcp_bridge.ps1`, `mcp_hot_reload.py`, el entry point
directo del módulo y `MCPBridgeService` devuelven o registran una denegación
antes de lanzar el servidor. `cloudflared` permanece deshabilitado. No uses las
secciones históricas siguientes para intentar arrancar el bridge.

### Capa 1 — Auto-arranque dentro del programa (histórico; bloqueado)

No está disponible el toggle de arranque ni se publica una URL. La
preferencia persistida no constituye autorización. Las variables de entorno
históricas no cambian la denegación.

### Modo script (debug) — bloqueado

El wrapper termina con código 78 antes de modificar el entorno, crear procesos
o invocar `cloudflared`.

El entry point **stdio** directo también está bloqueado:

No ejecutes el comando histórico anterior; `main()` deniega antes de crear
`AppBootstrap` o iniciar transporte.

---

## Registrar el server en Devin — no disponible mientras el bridge esté bloqueado

No hay URL que registrar ni tools MCP disponibles mientras la ruta autorizada
de inicio no exista.

---

## Capa 2 — URL estable con cuenta Cloudflare gratis (named tunnel; bloqueada)

El contenido restante de esta sección es histórico y no autoriza ni habilita
un túnel. No instales, autentiques ni arranques `cloudflared` para este bridge
mientras siga vigente el bloqueo operativo.

La URL `*.trycloudflare.com` del quick tunnel cambia en cada arranque. Para
que Devin / Claude / Codex no tengan que re-registrar la integración cada vez,
hay que migrar a un **named tunnel** autenticado.

Cloudflare ofrece esto **gratis**, pero la cuenta necesita un **dominio bajo
su gestión DNS**. Hay dos caminos:

### Opción A — Dominio propio (ideal)

1. Registrar un dominio barato (p.ej. `.tech`, `.xyz` ~ USD 2–5/año).
2. Añadirlo a Cloudflare (Add Site → Free plan) y apuntar los nameservers del
   registrar a los que te da Cloudflare.
3. Usar subdominio `iabv.tu-dominio.com` como URL estable del tunnel.

### Opción B — Sin dominio propio (trick)

Cloudflare **no regala dominios**, pero te acepta cualquier dominio que
**vos puedas gestionar vía DNS**. Si tenés un dominio gratuito de algún
proveedor que permita cambiar los NS (ej: algunos TLDs experimentales), lo
podés sumar igual al Free plan. Si no, el fallback supportado es usar la URL
`https://<tunnel-uuid>.cfargotunnel.com` que Cloudflare te da **sin DNS
propio** cuando el tunnel está autenticado — es estable mientras no borres
el tunnel.

### Pasos una sola vez (en tu laptop Windows)

```powershell
# 1. login (abre el browser y te pide autorizar el dominio)
cloudflared tunnel login

# 2. crear el tunnel (guarda credencial JSON en %USERPROFILE%\.cloudflared\)
cloudflared tunnel create iabv-v15

# 3a. Si tenés dominio propio, crear el DNS record:
cloudflared tunnel route dns iabv-v15 iabv.tu-dominio.com

# 3b. Si NO tenés dominio, anotá el UUID que imprime `create`:
#     la URL estable queda como https://<UUID>.cfargotunnel.com

# 4. config.yml en %USERPROFILE%\.cloudflared\config.yml:
#    tunnel: iabv-v15
#    credentials-file: C:\Users\<tu_user>\.cloudflared\<UUID>.json
#    ingress:
#      - hostname: iabv.tu-dominio.com     # (o el cfargotunnel.com)
#        service: http://127.0.0.1:8765
#      - service: http_status:404
```

### Activar el named tunnel desde el programa

Setea la variable de entorno `IABV_MCP_NAMED_TUNNEL` con el nombre del tunnel
antes de abrir IABV:

```powershell
[Environment]::SetEnvironmentVariable('IABV_MCP_NAMED_TUNNEL', 'iabv-v15', 'User')
```

El `MCPBridgeService` detecta la variable y lanza `cloudflared tunnel run
iabv-v15` en vez del quick tunnel. La URL publicada queda estable y la podés
registrar una sola vez en **Devin Settings → MCP Servers**.

### Modo script (sin programa)

```powershell
cloudflared tunnel run --url http://127.0.0.1:8765 iabv-v15
```

---

## Gobernanza y límites

- Las tools sólo consumen servicios ya existentes: no duplican contratos.
- **Gate explícito antes de rutas externas**: `site_exploration_explore` y
  `chatgpt_web_capture` consultan `WorldModelSnapshot` via
  `IABVMCPServer._governance_block_for_route` antes de invocar el servicio.
  Si hay red caída, un `OperationalBlockRecord` activo para la ruta, o un
  `ObservationPermissionGate` en estado `requerido` sin `granted=True`, la tool
  devuelve `{"governance_blocked": true, "reason": "...", ...}` y NO ejecuta
  el crawler ni el browser runner. Esto cumple AGENTS.md "Política Operativa
  Actual" (consultar snapshot antes, bloquear si falta permiso o evidencia).
- `AutonomyGovernancePolicy` sigue siendo la fuente de verdad: el gate del MCP
  server lee los bloqueos que esa policy publica en el world model. No duplica
  la lógica: sólo la respeta desde el borde.
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
