# MCP bridge — estado de seguridad de transporte

## Estado actual de esta candidata

Esta candidata permite que `IABVMCPServer.run()` seleccione únicamente el
transporte local `stdio`. Los transportes de red `sse` y `streamable-http`
fallan cerrados antes de iniciar el servidor. La protección DNS-rebinding y
los allowlists predeterminados del SDK se conservan; no se instalan hosts ni
orígenes comodín.

`MCPBridgeService` pertenece al ciclo de vida de la UI y no puede proporcionar
el pipe `stdio` propiedad del cliente. Por ello, su operación de inicio falla
cerrada antes de invocar el runner del servidor o el runner de túnel. Activar
la preferencia solo la persiste y produce un estado `failed`; no significa que
el transporte haya arrancado. El launcher `scripts/run_mcp_bridge.ps1` es una
ruta directa y local de `stdio`; rechaza cualquier transporte distinto y no
inicia `cloudflared`, HTTP, SSE ni un túnel.

`scripts/start_iabv.ps1` ya no delega al launcher ni intenta liberar un puerto
terminando procesos MCP; informa que el autoarranque de MCP/túnel está
deshabilitado. `scripts/iabv_bootstrap.ps1` también fue modificado en esta
fase: conserva la preparación de instalación/configuración, pero no termina
procesos por puerto, no inicia MCP/túnel mediante `start_iabv.ps1` ni anuncia
una URL pública como resultado normal. Instalar `cloudflared` no equivale a
ejecutarlo. El razonador Common Sense tampoco lanza túneles; el adaptador CLI
solo permite `cloudflared tunnel list` e `cloudflared tunnel info` para esa
familia de comandos.

## Herramientas MCP registradas

El servidor conserva estas herramientas; su registro no implica autorización
para usarlas ni que el transporte remoto esté disponible:

| Herramienta | Servicio de origen | Efecto declarado |
| --- | --- | --- |
| `world_model_snapshot` | `WorldModelService` | Lectura de snapshot |
| `orchestrator_preview` | `AdaptiveTaskOrchestrator` | Vista previa |
| `site_exploration_explore` | `SiteExplorationService` y repositorio | Escribe manuales de sitio |
| `portable_context_get` | `PortableContextService` | Lectura de contexto portable |
| `self_examination_current` | `OperationalSelfExaminationService` | Lectura de revisión |
| `chatgpt_web_capture` | `UIExecutionRunner` | Interacción con navegador |

Las herramientas mantienen sus gates de permiso, estado del mundo y bloqueos
operativos por separado del gate de transporte. `stdio` no concede autoridad
para leer el repositorio ni para ejecutar herramientas bloqueadas.

No conectar esta candidata a un túnel público. La autenticación del transporte,
la autorización independiente por operación, la resolución del destino y la
evidencia de identidad del emisor/servidor siguen sin demostrarse. Esta
restricción no libera bloqueos de gobernanza ni habilita lecturas protegidas.

## Ejecución local explícita

Un cliente local que ya esté autorizado puede iniciar el módulo directamente
como servidor `stdio`, desde un checkout que el operador haya seleccionado:

```powershell
$env:IABV_MCP_TRANSPORT = 'stdio'
python -m iabv_v15.infra.mcp.server
```

El launcher equivalente valida las rutas configuradas y usa `stdio` por
defecto. No ejecutarlo como parte de una inspección estática o prueba unitaria.
No establezcas `IABV_MCP_TRANSPORT=sse` ni `streamable-http`: el launcher los
rechaza y el servidor también los rechaza.

## Gobernanza de herramientas

El gate de cada herramienta permanece separado del gate del transporte. Las
herramientas que leen o producen efectos siguen sujetas a sus verificaciones
de permisos, estado del mundo y bloqueos operativos. El transporte `stdio` no
concede autoridad adicional. `GOVERNANCE=KEEP_BLOCKED` y
`BRIDGE=BRIDGE_NOT_READY` hasta que se establezcan y verifiquen las
precondiciones de confianza y autorización.

## Pruebas unitarias focalizadas

Las pruebas de `tests/test_mcp_server.py`,
`tests/test_mcp_bridge_service.py` y `tests/test_mcp_bridge_launcher.py` usan
dobles, recursos temporales e inspección estática. Verifican rechazos y ausencia
de invocación de runners; no demuestran que un transporte real funcione ni que
la aplicación, el almacenamiento de producción o una ruta de extremo a extremo
estén disponibles.

## Requisitos antes de reactivar HTTP/SSE o un túnel

Una futura autorización separada debe cubrir, como mínimo:

- identidad y autenticación verificables del cliente y del servidor;
- autorización de cada operación, vinculada a un destino y alcance exactos;
- resolución confiable del checkout/instancia y validación de bloqueo antes
  de cada efecto;
- controles de host/origen seguros y pruebas adversariales de DNS rebinding;
- recibos correlacionados para decisión, solicitud, operación y resultado;
- revisión independiente de seguridad y autorización explícita del Owner.

Hasta entonces, la UI no inicia el bridge, el servidor rechaza transportes de
red y no hay instrucciones para crear o iniciar túneles.
