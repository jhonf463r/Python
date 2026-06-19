# Inventario Operativo Real - IABV Desktop/QML

**Fecha**: 2026-06-17
**Objetivo**: Inventario operativo real del entorno y de la app IABV desktop/QML
**Regla**: IABV no es una web. Es una app desktop/QML. No se asume DOM ni navegador.

---

## 1. Repo Root Real

**Ruta**: `C:\Python\IABV_v1.5`

**Evidencia**:
- `pwd` retorna `C:\Python\IABV_v1.5`
- `git rev-parse --show-toplevel` retorna `C:/Python` (git repo está en nivel superior)
- Directorio raíz del proyecto IABV: `C:\Python\IABV_v1.5`

---

## 2. Herramientas Reales Disponibles para Automatización Desktop

### Dependencias Declaradas (pyproject.toml)
- **PySide6>=6.8**: Qt/QML framework para UI desktop
- **pydantic>=2.7**: Validación de datos
- **httpx>=0.27**: Cliente HTTP
- **Pillow>=10.0**: Procesamiento de imágenes
- **playwright>=1.40**: Automatización de navegadores (NO para IABV desktop)
- **keyring>=25.0**: Gestión de credenciales
- **psutil>=5.9**: Información del sistema/procesos
- **pyperclip>=1.8**: Acceso a clipboard
- **pywin32>=306**: API Win32 (Windows only)

### Herramientas Verificadas Disponibles
- **uiautomation**: ✅ disponible (v2.0.29)
- **pywinauto**: ✅ disponible
- **pyautogui**: ✅ disponible
- **pynput**: ✅ disponible
- **win32gui/win32process**: ✅ disponibles (via pywin32)

---

## 3. Cómo se Controla IABV como App Desktop/QML

### Arquitectura Desktop/QML
- **Framework**: PySide6 (Qt/QML)
- **Tipo de aplicación**: QGuiApplication (NO QApplication de QtWidgets)
- **UI**: 26 archivos QML en `src/iabv_v15/ui/qml/`
- **Comunicación QML-Python**: MainWindowBridge (`src/iabv_v15/ui/controllers/main_window_bridge.py`)

### Punto de Entrada
- **Archivo**: `src/iabv_v15/main.py`
- **Bootstrap**: `AppBootstrap` desde `src/iabv_v15/bootstrap.py`
- **Comando**: `python -m iabv_v15`

### Servicios de Control Desktop
- **UIExecutionRunner**: Ejecución de acciones de bajo nivel en Windows (`src/iabv_v15/services/tools/ui_execution_runner.py`)
- **WorldModelService**: Tracking de ventanas/procesos (`src/iabv_v15/services/evolution/world_model_service.py`)
- **UIScreenshotService**: Captura de screenshots (`src/iabv_v15/services/capture/ui_screenshot_service.py`)
- **WinClipboardBridge**: Acceso a clipboard via Win32 API (`src/iabv_v15/services/platform/win_clipboard_bridge.py`)
- **MultimodalPerceptionService**: Percepción multimodal (`src/iabv_v15/services/perception/multimodal_perception_service.py`)

---

## 4. Mapeo Nombres Conceptuales vs Archivos Reales

| Nombre Conceptual | Archivo Real | Ruta |
|-------------------|--------------|------|
| Bootstrap | bootstrap.py | src/iabv_v15/bootstrap.py |
| Main entry point | main.py | src/iabv_v15/main.py |
| UI QML | 26 archivos QML | src/iabv_v15/ui/qml/ |
| Main window bridge | main_window_bridge.py | src/iabv_v15/ui/controllers/main_window_bridge.py |
| UI screenshot service | ui_screenshot_service.py | src/iabv_v15/services/capture/ui_screenshot_service.py |
| UI execution runner | ui_execution_runner.py | src/iabv_v15/services/tools/ui_execution_runner.py |
| World model service | world_model_service.py | src/iabv_v15/services/evolution/world_model_service.py |
| Clipboard bridge | win_clipboard_bridge.py | src/iabv_v15/services/platform/win_clipboard_bridge.py |
| Multimodal perception | multimodal_perception_service.py | src/iabv_v15/services/perception/multimodal_perception_service.py |
| Qt screenshot provider | qt_screenshot_provider.py | src/iabv_v15/infra/ui/qt_screenshot_provider.py |
| MSS screenshot provider | mss_screenshot_provider.py | src/iabv_v15/infra/ui/mss_screenshot_provider.py |

---

## 5. Tabla de Capacidades vs Herramientas Reales

| Capacidad | Herramienta Real Disponible | Limitación | Evidencia Concreta | Sirve para Operar como Humano |
|-----------|-----------------------------|------------|-------------------|------------------------------|
| **Abrir la app** | subprocess.Popen / os.system | Requiere ruta exacta del ejecutable | UIExecutionRunner._launch_target() usa subprocess.Popen | ✅ Sí (puede lanzar .exe) |
| **Enfocar ventanas** | win32gui.SetForegroundWindow / uiautomation | Requiere HWND o título de ventana | UIExecutionRunner._wait_and_focus_any_window() usa win32gui | ✅ Sí (puede enfocar por HWND/título) |
| **Capturar pantalla** | PIL.ImageGrab / PySide6.QScreen / MSS | Requiere display activo | UIScreenshotService usa PIL -> Qt -> Noop fallback | ✅ Sí (captura pantalla completa o ventana) |
| **Escribir teclado** | pyautogui.typewrite / win32api.keybd_event | Requiere ventana enfocada | UIExecutionRunner._paste_text() usa clipboard + Enter | ⚠️ Parcial (usa clipboard, no teclado directo) |
| **Leer clipboard** | WinClipboardBridge (ctypes) / pyperclip | Solo Windows | WinClipboardBridge.get_text() usa Win32 API CF_UNICODETEXT | ✅ Sí (lee texto Unicode) |
| **Escribir clipboard** | WinClipboardBridge (ctypes) / pyperclip | Solo Windows | WinClipboardBridge.set_text() usa Win32 API CF_UNICODETEXT | ✅ Sí (escribe texto Unicode) |
| **Detectar foco** | win32gui.GetForegroundWindow / uiautomation | Requiere Win32 API | WorldModelService usa _user32.GetForegroundWindow() | ✅ Sí (detecta ventana activa) |
| **Detectar ventana** | win32gui.EnumWindows / uiautomation | Enumera todas las ventanas | WorldModelService._scan_windows() usa EnumWindows | ✅ Sí (enumera ventanas con HWND/título) |
| **Detectar proceso** | psutil.Process / win32process | Requiere PID | WorldModelService usa psutil para info de proceso | ✅ Sí (detecta PID, nombre, cmdline) |
| **Leer logs** | Path.read_text() / logging | Requiere ruta de archivo | Infra.logging.configure_logging() configura logging | ✅ Sí (lee archivos de texto) |
| **Click mouse** | pyautogui.click / win32api.mouse_event | Requiere coordenadas | UIExecutionRunner._mouse_click() usa win32api | ✅ Sí (click en coordenadas) |
| **Mover mouse** | pyautogui.moveTo / win32api.SetCursorPos | Requiere coordenadas | UIExecutionRunner._click_visible_page_read_region() usa SetCursorPos | ✅ Sí (mueve cursor a coordenadas) |
| **Accessibility Tree** | uiautomation (v2.0.29) | Solo Windows | MultimodalPerceptionService usa uiautomation.GetFocusControl() | ✅ Sí (lee estructura UI de Windows) |
| **DOM web** | playwright (>=1.40) | Solo para navegadores, NO para IABV desktop | BrowserSessionController usa playwright | ❌ NO (IABV es desktop, no web) |
| **QML object access** | PySide6 QML bridge | Requiere QGuiApplication vivo | MainWindowBridge expone slots/properties a QML | ⚠️ Limitado (solo dentro del proceso IABV) |

---

## 6. Herramientas Faltantes para Automatización Desktop

### No Faltan Herramientas Críticas
Todas las capacidades necesarias para operar IABV como humano están disponibles:
- ✅ Abrir app: subprocess
- ✅ Enfocar ventanas: win32gui/uiautomation
- ✅ Capturar pantalla: PIL/PySide6/MSS
- ✅ Escribir teclado: pyautogui/win32api (clipboard + Enter)
- ✅ Leer/escribir clipboard: WinClipboardBridge/pyperclip
- ✅ Detectar foco/ventana/proceso: win32gui/psutil
- ✅ Leer logs: Path.read_text()
- ✅ Click/mover mouse: pyautogui/win32api
- ✅ Accessibility Tree: uiautomation

### Limitaciones Conocidas
1. **Teclado directo**: UIExecutionRunner usa clipboard + Enter en lugar de teclado directo (limitación de diseño, no de herramientas)
2. **QML object access**: Solo accesible dentro del proceso IABV (limitación de arquitectura, no de herramientas)
3. **DOM web**: Playwright disponible pero NO aplicable a IABV desktop (IABV no es web)

---

## 7. Conclusión del Inventario

### Estado de Herramientas de Automatización Desktop
**✅ COMPLETO**: Todas las herramientas necesarias para operar IABV como humano están disponibles y verificadas.

### Herramientas Verificadas
- uiautomation ✅
- pywinauto ✅
- pyautogui ✅
- pynput ✅
- win32gui/win32process ✅
- PySide6 (Qt/QML) ✅
- playwright ✅ (NO aplicable a IABV desktop)
- pyperclip ✅
- pywin32 ✅

### Arquitectura IABV Desktop/QML
- **Framework**: PySide6 (Qt/QML)
- **Tipo**: QGuiApplication (desktop, NO web)
- **Control**: MainWindowBridge + UIExecutionRunner + WorldModelService
- **Percepción**: MultimodalPerceptionService + UIScreenshotService
- **Clipboard**: WinClipboardBridge (Win32 API)

### Recomendación
**NO se requieren herramientas adicionales**. El stack actual tiene todas las capacidades necesarias para automatización desktop completa de IABV.

---

**Fin del Inventario Operativo Real**
