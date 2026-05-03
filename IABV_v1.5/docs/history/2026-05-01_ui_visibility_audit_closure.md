# UI Visibility Audit — Closure Operativa (2026-05-01)

## Objetivo

Cerrar los gaps operativos de `ui_visibility_audit` sin cambiar la
arquitectura. Conectar adapters/watchers al runtime real, cerrar el
ciclo de tracking de dialogs, y alimentar el Control Master con
senales visibles del usuario.

## Lo que quedo conectado

### 1. UIVisibilityAuditService (NUEVO)

- Archivo: `src/iabv_v15/services/audit/ui_visibility_audit_service.py`
- Registro central thread-safe de eventos visibles del usuario
- Categorias: `dialog`, `splash`, `subprocess`, `file_not_found`,
  `win32_popup`, `unexpected`
- API de lectura: `snapshot()` retorna `{unresolved, file_not_found,
  unexpected, total_events, by_category}`
- Instanciado en bootstrap como `self.ui_visibility_audit`

### 2. SplashAuditAdapter (NUEVO)

- Archivo: `src/iabv_v15/services/audit/splash_audit_adapter.py`
- Se conecta a `SplashController.statusChanged`, `hasErrorChanged`,
  `readyChanged`, `closingNow`
- Wire en `bootstrap.run()` despues de crear `SplashController`
- Eventos: `splash/status`, `splash/error`, `splash/ready`,
  `splash/closing`

### 3. SubprocessAuditWrapper (NUEVO)

- Archivo: `src/iabv_v15/services/audit/subprocess_audit_wrapper.py`
- API: `record_start()`, `record_exit()`, `record_error()`
- Instanciado en bootstrap como `self.subprocess_audit_wrapper`
- Listo para que MCP/tunnel startup invoque los records

### 4. Win32PopupWatcher (NUEVO)

- Archivo: `src/iabv_v15/services/audit/win32_popup_watcher.py`
- `record_popup()`, `record_popup_dismissed()` para tracking manual
- `check_popups()` con EnumWindows real en Windows
- Instanciado en bootstrap como `self.win32_popup_watcher`

### 5. Dialog Closed Tracking (CIERRE)

- `ControlCenterViewModel.dialogClosed(dialog_type, detail)` — `@Slot`
- `ControlCenterViewModel.dialogOpened(dialog_type, detail)` — `@Slot`
- QML: `onVisibleChanged` en CredentialPromptDialog,
  ClarificationDialog, MissingDependencyDialog llama
  `dialogOpened`/`dialogClosed` automaticamente
- Archivos QML: `ControlCenterPage.qml`, `EvolutionCenterPage.qml`
- Cadena completa: QML dialog open/close → Python @Slot →
  UIVisibilityAuditService → ControlMaster metadata

### 6. Control Master consume senales visibles (CIERRE)

- `ControlMasterService.__init__` acepta `ui_visibility_audit`
- `_project_visibility_audit()` lee `audit.snapshot()` en cada
  `current_state()` call
- Resultado depositado en `state.metadata["ui_visibility_audit"]`
- Contiene: `unresolved`, `file_not_found`, `unexpected`,
  `total_events`, `by_category`
- `visibility_audit_snapshot()` — API publica para OSES/digest
- Bootstrap pasa `ui_visibility_audit` al construir
  `ControlMasterService` y `ControlCenterViewModel`

## Tests

12 tests en `tests/test_ui_visibility_audit.py`:

1. `test_splash_audit_adapter_connects` — adapter se conecta a senales
2. `test_splash_audit_adapter_noop_without_splash` — safe noop
3. `test_subprocess_audit_wrapper_records_lifecycle` — start/exit
4. `test_subprocess_audit_wrapper_noop_without_audit` — safe noop
5. `test_win32_popup_watcher_records_popup` — detect/dismiss
6. `test_win32_popup_watcher_noop_without_audit` — safe noop
7. `test_dialog_closed_records_via_audit_service` — open+close cycle
8. `test_dialog_closed_snapshot_counts` — unresolved count
9. `test_control_master_reads_visibility_audit` — metadata populated
10. `test_control_master_without_visibility_audit` — backward compat
11. `test_bootstrap_has_visibility_audit_services` — wiring check
12. `test_control_master_service_receives_visibility_audit` — DI check

Resultado: **12/12 passed**, 0 regresiones nuevas.

## Lo que depende de Windows real

- `Win32PopupWatcher.check_popups()` — EnumWindows via ctypes solo
  funciona en Windows con desktop activo. `record_popup()` manual
  funciona en cualquier plataforma.
- `SplashAuditAdapter` — las senales reales de `SplashController`
  solo se emiten cuando hay QGuiApplication (es decir, en la UI real).
  En tests se simula con stubs.
- Dialog tracking QML (`onVisibleChanged`) — solo se ejecuta con la
  UI QML real en Windows.

## UNRESOLVED

1. **SubprocessAuditWrapper no auto-instrumenta MCP/tunnel**: El
   wrapper esta listo pero los call sites en bootstrap que lanzan
   `_start_mcp_subprocess()` y `_start_tunnel_subprocess()` no
   llaman `record_start()`/`record_exit()` todavia. Requiere
   instrumentar esos metodos sin cambiar su contrato.

2. **Win32PopupWatcher.check_popups() sin polling automatico**: El
   watcher detecta popups bajo demanda pero no tiene un timer/loop
   que lo ejecute periodicamente. Un QTimer o background thread
   podria agregarse en el futuro.

3. **EvolutionCenterViewModel no tiene @Slot dialogOpened/Closed**:
   Los QML del EvolutionCenter llaman condicionalmente con
   `typeof evolutionCenterViewModel.dialogOpened === "function"`.
   Si el EvolutionCenterViewModel no expone esos slots, los eventos
   no se registran desde esa pagina. Solo ControlCenterVM los tiene.

4. **Digest builder no incluye visibility audit**: El
   `ControlMasterDigestBuilder` no lee `metadata.ui_visibility_audit`
   para el digest compacto que se inyecta en prompts. Se puede agregar
   como una seccion breve si se necesita.

## Archivos modificados

- `src/iabv_v15/bootstrap.py` — wiring de UIVisibilityAuditService,
  SubprocessAuditWrapper, Win32PopupWatcher, SplashAuditAdapter
- `src/iabv_v15/services/evolution/control_master_service.py` —
  ui_visibility_audit param + _project_visibility_audit()
- `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py` —
  ui_visibility_audit param + @Slot dialogOpened/dialogClosed
- `src/iabv_v15/ui/qml/pages/ControlCenterPage.qml` — onVisibleChanged
- `src/iabv_v15/ui/qml/pages/EvolutionCenterPage.qml` — onVisibleChanged

## Archivos nuevos

- `src/iabv_v15/services/audit/ui_visibility_audit_service.py`
- `src/iabv_v15/services/audit/splash_audit_adapter.py`
- `src/iabv_v15/services/audit/subprocess_audit_wrapper.py`
- `src/iabv_v15/services/audit/win32_popup_watcher.py`
- `tests/test_ui_visibility_audit.py`
- `docs/history/2026-05-01_ui_visibility_audit_closure.md` (este doc)

## Siguiente paso recomendado

1. Instrumentar `_start_mcp_subprocess()` y `_start_tunnel_subprocess()`
   con `subprocess_audit_wrapper.record_start()`/`record_exit()`.
2. Agregar QTimer para `win32_popup_watcher.check_popups()` periodico.
3. Exponer `dialogOpened`/`dialogClosed` en `EvolutionCenterViewModel`.
4. Incluir snapshot de visibility audit en el digest compacto.
