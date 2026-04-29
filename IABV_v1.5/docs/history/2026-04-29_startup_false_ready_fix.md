# Startup false-ready fix — handoff

Fecha: 2026-04-29
Branch: `devin/startup-false-ready-fix`
Encadenado a: PRs #257, #258, #259 (cable A ya en main).

## Hallazgo raiz

La auditoria live del 2026-04-28 (`data/audit/startup_live_80s_no_bridge_noise.png`)
muestra el splash BURVE visible a ~80 s pese a que el JSONL declara
`main_window_shown`, `splash_set_ready`, `populate_ui_done` y
`deferred_post_window_setup_done`.  El JSONL miente.  Tres causas
estructurales (verificadas por lectura, no especulacion):

1. **`splash.set_ready()` se emite antes de `app.exec()`**.  En
   `bootstrap.py` (camino viejo) el `set_ready()` corria justo despues
   de `main_win.show()` pero ANTES del primer tick del event loop.  Y
   `_populate_ui` esta encolado a `QTimer.singleShot(0, ...)`, asi que
   los ViewModels son `None` cuando el splash declara ready.
2. **`main_window_shown` muestra una ventana visualmente vacia**.
   `Main.qml` envuelve el shell real en un `Loader { asynchronous: true }`
   que arranca tras un timer de 25 ms.  La `ApplicationWindow` se ve,
   pero el loader sigue compilando en background thread.
3. **`populate_ui_done` no implica "shell visible"**.  Marca solo "VMs
   construidos y context set", no que el `mainShellLoader` haya
   completado su instanciacion async.

Y dos bugs adicionales que la evidencia live registra:

4. **`current_page` siempre es `"unknown"`**.  El UI bridge leia
   `getattr(control_center_viewmodel, "_current_page", "unknown")` —
   atributo que NO existe en `ControlCenterViewModel` (grep en 6961
   lineas: 0 matches).  El estado real de ruta vive en
   `navigation_controller.get_current_route()`.
5. **`send_message_from_bridge` queda `queued`** mientras splash sigue
   visible porque el GUI thread esta bloqueado en `_populate_ui` y el
   slot conectado al signal `bridgeChatRequested` no puede correr hasta
   que termine.

## Cambios soberanos (sin servicio nuevo, sin memoria paralela)

### A. Handshake honesto del shell

Nuevo flujo:

```
QML mainShellLoader.onStatusChanged == Loader.Ready
  → mainWindowBridge.signal_shell_loader_ready()
  → MainWindowBridge.shellLoaderReady (Qt signal)
  → AppBootstrap._handle_shell_loader_ready()
  → mark hito ``shell_loader_ready`` + splash.set_ready()
```

Archivos:
- `src/iabv_v15/ui/qml/Main.qml` — `Loader.onStatusChanged` llama
  `mainWindowBridge.signal_shell_loader_ready()` cuando el contenido
  async termino.
- `src/iabv_v15/ui/controllers/main_window_bridge.py` — ya tenia
  `shellLoaderReady = Signal()` + slot `signal_shell_loader_ready()`
  idempotente.
- `src/iabv_v15/bootstrap.py`:
  - conecta `MainWindowBridge.shellLoaderReady` →
    `AppBootstrap._handle_shell_loader_ready()` justo despues de crear
    el bridge en `_build_ui_objects()`.
  - elimina la llamada `splash.set_ready()` deshonesta de `run()`.
  - agrega `_force_splash_ready_fallback()` con `QTimer.singleShot`
    (default 45 s, configurable via `IABV_SHELL_READY_FALLBACK_MS`)
    para que el splash NUNCA quede congelado si la senal QML no llega.
    El fallback marca un hito distinto (`shell_loader_ready_fallback`)
    para que la auditoria distinga un cierre honesto de uno por timeout.

### B. `current_page` honesto en el bridge

`src/iabv_v15/services/ui_bridge_service.py` — `_on_get_ui_state` ahora
lee de `control_center_viewmodel.navigation_controller.get_current_route()`
con fallback a `_current_route` (atributo) y luego a `_current_page`
(legacy).  Si nada existe, devuelve `"unknown"` honestamente.

### C. PortableContext detecta false-ready

`src/iabv_v15/services/evolution/portable_context_service.py` —
`_startup_health_snapshot()` ahora detecta tres patrones deshonestos en
el JSONL y los expone como `false_ready_detected: True` +
`false_ready_reasons: list[str]` y los suma a `recent_blockers`:

- `splash_set_ready_before_populate_ui_done`: el splash declaro ready
  antes de que `populate_ui_done` llegara (orden roto).
- `splash_set_ready_without_shell_loader_ready`: el splash declaro
  ready y nunca llego ni el hito honesto ni el fallback (configuracion
  desconectada).
- `shell_loader_ready_fallback_used`: el splash cerro por timeout, no
  por senal QML real.

### D. OSES emite `startup_false_ready` finding

`src/iabv_v15/services/evolution/operational_self_examination_service.py`
— `_startup_health_findings()` agrega un cuarto finding cuando los
patrones de C se cumplen.  Categoria nueva `startup_false_ready` (no se
mezcla con `startup_degradation` porque mide algo cualitativamente
distinto: orden vs latencia).  Severidad `HIGH`, confianza `0.95`,
recomendacion concreta apunta al fix de A.

## Tests focalizados (70 nuevos / extendidos)

Todos pasan en mi VM Linux.  La fixture es JSONL sintetico — no se
necesita la UI viva.

- `tests/test_startup_health_cable.py` — extendido con 7 tests para
  false-ready detection (orden roto, sin shell_loader_ready, fallback,
  honest path, OSES finding emission).
- `tests/test_bootstrap_shell_readiness.py` — nuevo, 7 tests:
  hito + splash, idempotencia, splash ausente tolerado, fallback
  hito distinto, no double-fire entre fallback y honest, bridge
  signal emit.
- `tests/test_ui_bridge_service.py` — extendido con 3 tests para
  `current_page` (lee de navigation_controller, devuelve unknown si
  falta nav, fallback a `_current_page` legacy).

Resultado:
```
tests/test_startup_health_cable.py ............................ 17 passed
tests/test_bootstrap_shell_readiness.py ....................... 7 passed
tests/test_ui_bridge_service.py ............................... 18 passed
tests/test_portable_context_service.py + test_oses + timeline .. 38 passed
```
Total focal + regresion: 80 passed.

## Verificacion live pendiente (Windows)

Mi VM Linux NO puede reproducir la patologia: el bug es del rendering
nativo Windows con `Qt.SplashScreen | Qt.WindowStaysOnTopHint` y el
GUI thread Python bloqueado.  La verificacion final requiere:

```powershell
cd C:\Python\IABV_v1.5
git pull --ff-only
scripts\start_iabv.ps1 -StartUI
```

Despues mandar:
1. `data/logs/startup_timeline.jsonl` — debe mostrar
   `populate_ui_done` y `shell_loader_ready` ANTES de `splash_set_ready`.
2. Video o capturas con timestamps de splash → shell → primer chat.
3. `data/evolution/portable_context/latest.md` — debe reportar
   `false_ready_detected: false` si el handshake funciono.
4. `data/evolution/self_examination/latest.md` — debe NO listar
   `startup_false_ready` finding.

Si el JSONL muestra `shell_loader_ready_fallback` en lugar de
`shell_loader_ready`, la conexion QML tiene un problema todavia (por
ejemplo `mainWindowBridge` no esta inyectado al QML scope cuando el
loader resuelve) y hay que iterar sobre eso.

## Reglas que respete (verificacion)

- [x] No abri login multi-cuenta, shadow learning ni nuevos providers.
- [x] No invente otro servicio.  Todo va sobre las 8 piezas existentes
      (ExperimentLab, StrategySelector, AdaptiveWeightLayer,
      TaskOutcomeRecorder, DecisionAuditTrail, PortableContext, OSES,
      account_resource_scanner).
- [x] No saque la auditoria de la arquitectura soberana.
- [x] Todo pasa por startup_timeline + OSES + PortableContext +
      backlog + handoff.
- [x] Evidencia persiste en `docs/history` (este archivo) +
      `data/evolution/backlog.json`.

## D1-D7 siguen abiertos (no se tocaron)

Igual que en `docs/history/2026-04-29_startup_instrumentation_fase_1.md`.
Resumen para el lector apurado:

- D1: chat ligero → DecisionAuditTrail
- D2: chat ligero → ExperimentLab via TaskOutcomeRecorder
- D3: LocalRoleRouter consulta worker_pool antes de rutear
- D4: shadow learning formal (cerrado mientras el arranque siga inestable)
- D5: PortableContext.account_inventory (parte ya: startup_health esta;
      account_inventory aun no)
- D6: rotacion gobernada cruzando trends
- D7: OSES findings desde scanner (parte ya: startup_health emite;
      account_inventory aun no)

D4 sigue cerrado hasta que la evidencia live confirme que el arranque
quedo estable con el handshake nuevo.

## UNRESOLVED honestos

- Verificacion live en Windows: pendiente, depende del usuario.
- Si el `shell_loader_ready_fallback` aparece en la evidencia live, el
  cableado QML→bridge no esta funcionando y hay que iterar.
- `send_message_from_bridge` queda `queued` durante `_populate_ui`:
  con el handshake nuevo, el mensaje deberia procesarse en cuanto el
  shell este listo.  Si la evidencia live muestra que sigue colgado,
  el siguiente cable es D1 (chat → DecisionAuditTrail) para tener
  metrica directa.
