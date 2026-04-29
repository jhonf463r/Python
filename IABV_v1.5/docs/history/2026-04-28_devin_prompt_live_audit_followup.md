## Prompt para Devin - Continuacion de auditoria live y cierre de autonomia operativa

Trabaja sobre `C:\Python\IABV_v1.5` y parte desde el estado real del repo, no desde supuestos.

### Contexto obligatorio

Lee primero:

1. `AGENTS.md`
2. `docs/history/2026-04-28_codex_live_audit_handoff.md`
3. `data/evolution/backlog.json`
4. `data/evolution/portable_context/latest.md`
5. `data/evolution/self_examination/latest.md`
6. `bootstrap.py`

### Regla principal

No descartes ningun hallazgo de este handoff salvo que lo verifiques resuelto con evidencia real o con una prueba focalizada suficiente.

### Lo que YA se hizo y no debes rehacer a ciegas

1. Auditoria standalone read-only mas limpia.
2. Fix de `workspace_root` y autostart MCP con `python.exe` cuando la UI corre con `pythonw.exe`.
3. MCP y `cloudflared` ocultos con logs en `data/logs/`.
4. Cooldown persistido para `aider_coder`.
5. Metacognicion que ya detecta `no functional provider` y `single provider dependency` con mejor contexto de aprovisionamiento.
6. Ruta de chat ligero para `hola`, world model, autoexaminacion y preguntas simples.
7. Defer inicial en varios ViewModels y en el shell principal de `Main.qml`.
8. Bridge leyendo mensajes vivos del ViewModel.

Esas piezas ya tienen pruebas focalizadas pasando. No las rompas al perseguir el startup live.

### Problema principal actual

La app sigue fallando en la transicion `splash -> shell principal interactivo`.

Hallazgos live ya comprobados:

- En varias corridas `127.0.0.1:8000` sube correctamente.
- En varias corridas el bridge tambien sube.
- Aun asi, la ventana visible puede quedarse en splash durante 45-75s o mas.
- Cuando el bridge ya esta arriba pero el shell no esta realmente listo, `send_message` puede quedar encolado sin respuesta visible.
- Antes del recorte del chat, un `hola` por bridge podia disparar `pythonw` a ~8.4 GB y congelar la sesion.
- Luego del recorte, ese camino mejoro, pero el arranque visible sigue pesado y la RAM base sigue alta.

### Tu objetivo

Cerrar el startup live y dejar el programa en un estado mas cercano a autonomia real sin violar la arquitectura soberana:

- una sola ventana
- world model como fuente viva
- sin otro cerebro
- sin inventar credenciales
- sin fingir readiness

### Orden de trabajo requerido

#### Fase 1. Reproducir con UI visible y medir

1. Ejecuta el programa real con interfaz visible.
2. Usa la auditoria interna y evidencia live, no solo tests.
3. Mide el startup por etapas con timestamps reales:
   - splash 0-20%
   - splash 20-60%
   - shell principal materializado
   - bridge listo
   - primer chat procesado
4. Cruza eso con logs, listeners y world model.

No cierres la fase hasta saber con precision cual etapa sigue reteniendo el hilo principal.

#### Fase 2. Resolver shell readiness

Necesitas dejar un handshake soberano y observable que diferencie:

- proceso vivo
- splash vivo
- engine QML cargado
- shell principal materializado
- chat listo para procesar
- bridge listo para aceptar trafico real

El bridge no debe reportar `sent` o `queued` como si la UI estuviera lista cuando el shell aun no puede responder.

#### Fase 3. Sacar mas peso del camino critico

Revisa y difiere o desacopla, si todavia corren demasiado pronto:

- `_log_tool_availability()`
- `mcp_client` install/verification
- scans de providers
- refreshes de UI no criticos
- cualquier auto-correction no esencial para mostrar la ventana

Haz cambios minimos y medibles.

#### Fase 4. Reducir memoria y regresiones de chat ligero

Confirma que:

- `hola`
- preguntas sobre pantalla/navegadores
- world model
- autoexaminacion

no entren al camino pesado ni disparen consumo absurdo de RAM.

#### Fase 5. Despues del startup, seguir con la autonomia real del razonamiento

Cuando el startup live quede estable, avanza con este bloque estrategico:

1. selector soberano unificado:
   - API gratis/trial
   - sesiones web gobernadas
   - fallback/local shadow
2. inventario vivo de cuentas, sesiones, cuotas y permission gates en `WorldModel`
3. rotacion gobernada de cuentas/cuotas gratis
4. shadow learning local formal:
   - acuerdo/desacuerdo
   - latencias
   - ganador real
   - corpus util para aprendizaje local

### Pendientes que NO debes perder

Aunque no los resuelvas todos en una sola sesion, deben quedar presentes en backlog/doc si siguen abiertos:

1. `splash -> shell principal` sigue inestable
2. handshake real de readiness entre UI y bridge
3. scans/installers no criticos todavia demasiado temprano
4. RAM alta en arranque
5. selector `API gratis + web session + local shadow`
6. rotacion multi-cuenta/cuota gratis
7. inventario vivo de sesiones/cuentas/cuotas en `WorldModel`
8. shadow learning local formal
9. supervision y autoreinicio de MCP + tunnel con heartbeat
10. export/commit/push de evidencia de auditoria desde una sola ventana

### Requisitos de validacion

No te quedes en teoria.

Debes:

1. correr pruebas focalizadas del slice tocado
2. ejecutar la app visible de verdad
3. producir evidencia del antes/despues
4. dejar actualizado:
   - `data/evolution/backlog.json`
   - `docs/history/...`
   - pruebas del slice

### Archivos donde mirar primero

- `src/iabv_v15/bootstrap.py`
- `src/iabv_v15/ui/qml/Main.qml`
- `src/iabv_v15/services/ui_bridge_service.py`
- `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`
- `src/iabv_v15/ui/viewmodels/evolution_center_viewmodel.py`
- `src/iabv_v15/ui/viewmodels/centro_vivo_viewmodel.py`
- `src/iabv_v15/services/auto_correction_engine.py`

### Entregable esperado

Al cerrar tu sesion:

1. deja el startup visible objetivamente mejor o explica con evidencia exacta que lo bloquea
2. deja pruebas nuevas o ajustadas
3. deja backlog y handoff actualizados
4. no ocultes `UNRESOLVED`
5. si tocas la ruta Devin/tunnel, deja estrategia clara para que no dependa de una terminal manual

### Nota final de estrategia

No intentes resolver la autonomia total metiendo mas IAs primero.

La ruta fuerte es:

1. startup visible y estable
2. readiness soberano
3. supervision de MCP/tunnel
4. selector unificado de razonamiento
5. rotacion de cuentas/cuotas
6. shadow learning local
7. export de auditoria y evidencia

Sin 1-3, lo demas se vuelve ruido porque el usuario no ve lo mismo que el sistema cree ver.
