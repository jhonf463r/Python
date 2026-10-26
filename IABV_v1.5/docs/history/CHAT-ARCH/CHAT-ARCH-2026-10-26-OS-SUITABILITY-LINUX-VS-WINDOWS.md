# Evaluación de plataforma para IABV v1.5 — Linux vs. Windows

- Fecha: 2026-10-26 (America/Bogota)
- Baseline fuente: `main@80c6825dabf799087e2469c17826545c8ca613f0`
- Estado: **checkpoint documental / propuesta de evaluación; no canónico hasta revisión y adopción**
- Alcance: decisión de plataforma para el IABV v1.5 presente y su objetivo de autonomía progresiva. No es una auditoría línea por línea de todos los archivos del repositorio, ni una prueba de rendimiento de hardware.
- Método: inventario recursivo de la estructura de GitHub y lectura estática focalizada de configuración, inicio, ejecución UI, captura de navegador, portapapeles, metacognición de GPU, puente MCP, dependencias, CI y estado canónico; contraste con documentación oficial actual de Ollama, Qt for Python, Playwright, Microsoft y GitHub Actions.
- Ejecución local/build/pruebas/runtime: **NO EJECUTADOS** por esta evaluación.
- Restricción superior: `CURRENT-STATE.md` sigue siendo la única autoridad de enrutamiento. Esta evaluación no cambia su tarea activa ni autoriza migraciones, cambios de producto, transporte real, lecturas protegidas o aceptación de PRs.

## 1. Decisión ejecutiva

**Para hacer funcionar el IABV actual con el conjunto más amplio de capacidades ya implementadas, mantener Windows como host principal es la decisión de menor riesgo.** El código de IABV v1.5 está orientado de forma tangible a Windows para el control del escritorio, el portapapeles, las ventanas, las rutas del perfil del navegador, el arranque y parte del límite de autorización nativa.

**Para una autonomía futura basada en servicios persistentes sin interfaz gráfica, Linux (por ejemplo, Ubuntu LTS soportado) es una buena plataforma candidata para el plano de coordinación/headless, pero no es un reemplazo directo del host Windows actual.** Migrar toda la aplicación a Linux hoy haría que determinadas rutas de escritorio dejaran de ejecutar acciones reales o requirieran sustituciones y validaciones nativas nuevas.

La arquitectura de destino más prometedora —si el objetivo realmente requiere operación continuada de los dos tipos— es híbrida:
- **Windows Desktop Agent:** ventana interactiva, control de aplicaciones de Windows, portapapeles, perfiles y sesiones de navegador del usuario, controles de identidad/handles y operaciones que dependen del escritorio real.
- **Linux Coordinator/Service (futuro, opcional):** planificación persistente, colas, API/MCP local restringido, registro durable de tareas, procesamiento no gráfico, aislamiento de workers, observabilidad y coordinación de agentes remotos.
- **Contrato autenticado entre ambos:** tareas con identidad, versión/contexto, capacidades requeridas, permisos y caducidad; recibos de ejecución correlacionados; no acceso remoto abierto ni confianza basada solamente en un túnel.

Esto es una recomendación arquitectónica, **no una afirmación de que un despliegue híbrido ya exista ni una autorización para construirlo inmediatamente**. Antes de separar procesos conviene cerrar los contratos de capacidad, autorización y contexto y preservar la evidencia local pendiente.

## 2. Evidencia de que el IABV actual está orientado a Windows

### 2.1 Ejecución de escritorio

Fuente: [`ui_execution_runner.py`](../../src/iabv_v15/services/tools/ui_execution_runner.py).

- `UIExecutionRunner` carga `ctypes.windll.user32` y su `is_available()` exige `os.name == 'nt'` además de un `user32` utilizable.
- Su método `run()` etiqueta el resultado como simulado cuando no hay backend de ejecución real o cuando se ejecuta en sandbox.
- La implementación acciona el cursor, clics, teclas, foco de ventana, captura de pantalla y otras acciones del escritorio mediante interfaces específicas del entorno.
- Por tanto, en Linux la misma clase **no es una automatización de escritorio equivalente**: la ruta actual debe considerarse simulada/no disponible, no una capacidad portátil demostrada.

Esto pesa mucho en una IA que debe observar e interactuar con los programas instalados en el equipo real. La interfaz PySide6, por sí sola, sí es multiplataforma; las funciones Win32 conectadas a esa interfaz no lo son.

### 2.2 Portapapeles, ventanas y APIs del sistema

Fuente: [`win_clipboard_bridge.py`](../../src/iabv_v15/services/platform/win_clipboard_bridge.py), [`tool_adapters.py`](../../src/iabv_v15/services/tools/tool_adapters.py) y [`bootstrap.py`](../../src/iabv_v15/bootstrap.py).

- `WinClipboardBridge` accede a `user32`/`kernel32`; en sistemas no Windows marca esa función como no disponible y lanza `ClipboardUnavailableError` si se intenta usar el puente Win32.
- Varias rutas de detección/foco de ventanas recurren a `ctypes.windll.user32`.
- Los módulos `win_systray_bridge.py` y `win_toast_bridge.py` son explícitamente bridges de plataforma Windows.
- Hay detección de capacidades que devuelve resultados explícitos cuando faltan dependencias nativas. Esto ayuda a degradar de forma honesta, pero no constituye una implementación Linux equivalente de todas las capacidades.

### 2.3 Configuración del navegador y perfiles

Fuente: [`infra/config.py`](../../src/iabv_v15/infra/config.py) y [`BrowserSessionController`](../../src/iabv_v15/services/capture/browser_session_controller.py).

- La ruta predeterminada del perfil de Chrome utiliza `Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data'`, lo cual es Windows-específico.
- El controlador de sesiones de Playwright es, en sí, portable entre plataformas compatibles, pero usar un perfil persistente, conservar el estado autenticado y capturar respuestas en el navegador del usuario requiere rutas, perfiles, permisos, sesión gráfica y configuración propias de cada sistema.
- Los flujos basados en el perfil de Windows, el portapapeles o una ventana existente no se convierten automáticamente en equivalentes Linux por instalar Playwright en Linux.

### 2.4 Arranque, instalación y operación cotidiana

Fuentes: [`start_iabv.ps1`](../../scripts/start_iabv.ps1), [`iabv_bootstrap.ps1`](../../scripts/iabv_bootstrap.ps1), [`IABV.vbs`](../../scripts/IABV.vbs) y [`mcp-bridge.md`](../../docs/mcp-bridge.md).

- El flujo de inicio “de un clic” se basa en PowerShell y VBScript.
- El bootstrap instala binarios Windows portables de herramientas auxiliares y trabaja con perfiles/secrets de PowerShell.
- Los accesos directos, algunas operaciones de procesos/puertos y los perfiles se documentan con supuestos Windows.
- En el árbol revisado no se encontraron unidades `systemd`, un `Dockerfile`/Compose para el producto ni una ruta equivalente de instalación/inicio Linux para el conjunto actual. **La ausencia en el inventario no prueba que ninguna prueba manual haya existido; sí significa que no hay una ruta Linux completa y documentada visible en ese árbol.**

### 2.5 GPU y recursos

Fuente: [`gpu_metacognition.py`](../../src/iabv_v15/services/gpu_metacognition.py) y [`limits_awareness.py`](../../src/iabv_v15/services/limits_awareness.py).

- La detección de GPU prueba `nvidia-smi`; después intenta `wmic` y una ruta de PowerShell específica de Windows.
- Hay algo de código para sistemas no Windows (por ejemplo `which`, `sensors` y sugerencias de `lm-sensors`), pero las rutas no tienen la misma cobertura: la detección completa no es simétrica.
- El código obtiene una señal de `ollama ps` para analizar la división CPU/GPU, pero no se ha hecho un benchmark comparativo entre ambos sistemas para el hardware del Owner.

## 3. Qué es portátil y qué no

| Subsistema | Situación observada | Implicación para Linux |
|---|---|---|
| Núcleo Python, modelos Pydantic, planificación y contratos de tareas | Mayormente Python; no se verificó todo módulo por módulo | Candidato razonable para ejecución multiplataforma con pruebas |
| UI PySide6 / Qt | Framework multiplataforma | Se puede construir en Linux, pero faltan validaciones de la aplicación integrada y del comportamiento de sistema |
| Playwright/browser control | La biblioteca soporta Windows y Linux; el código IABV también usa perfiles y modos de captura dependientes del entorno | Adecuado para automatización de navegador aislada/headless, no prueba paridad con un navegador autenticado del escritorio Windows |
| `UIExecutionRunner` / APIs de ventanas | Backend real depende de Win32/user32 | No está portado a Linux; la ruta actual simula/no ejecuta funciones reales |
| Portapapeles, bandeja, toast, foco de ventana | Bridges explícitamente Windows | Requiere backends Linux separados y tests de paridad |
| Inicio y packaging | Scripts PowerShell/VBS; pyproject de Python | Linux necesita unidad de usuario/servicio, configuración, paths, secretos, gestión de señales y paquetes de despliegue propios |
| Ollama / inferencia local | Disponible en Windows y Linux; el soporte GPU depende del modelo de GPU, controlador y backend | El SO por sí solo no permite concluir cuál será más rápido |
| MCP/cliente remoto | Transporte basado en Python/HTTP y procesos; su superficie de seguridad sigue condicionada por los gates actuales | Portable en principio, pero el bridge productivo no debe activarse hasta que la autorización/identidad se acepte de forma independiente |
| Límite de confianza nativo en la propuesta M1F | La candidata contiene lector/contratos Windows específicos; no está integrada en `main` | No se deben extrapolar a Linux las garantías de handle/ACL de Windows; el backend Linux necesitaría una revisión de seguridad propia |

Fuentes externas actuales:
- Qt for Python enumera plataformas de escritorio Windows y Linux como plataformas soportadas: [Qt supported platforms](https://doc.qt.io/qtforpython-6/overviews/qtdoc-supported-platforms.html) y [deployment](https://doc.qt.io/qtforpython-6/deployment/index.html).
- Playwright documenta Windows, WSL y distribuciones concretas de Linux como plataformas de soporte: [Playwright Python installation/system requirements](https://playwright.dev/python/docs/intro).

## 4. Comparación orientada al objetivo de IABV

Las valoraciones siguientes son una síntesis arquitectónica de la evidencia disponible, no resultados de pruebas de rendimiento.

| Criterio | Windows 11 como host único | Linux LTS como host único | Interpretación |
|---|---|---|---|
| Ejecutar las funciones actuales sin reescribir backends | **Mejor** | Bajo/parcial | El código de escritorio y el inicio favorecen Windows |
| Controlar las aplicaciones y el perfil del usuario Windows | **Mejor** | Débil/indirecto | Un proceso Linux no tiene automáticamente el acceso a `user32`, al portapapeles o a la sesión interactiva de Windows |
| UI PySide6 | Soportado | Soportado | Qt no decide la elección por sí solo |
| Navegador Playwright headless | Soportado | Soportado | Ambos sirven; hay diferencias de dependencias de sistema y perfiles |
| Servicio de coordinación sin escritorio, reinicio y logs | Posible, pero hay que separar el trabajo de GUI de los procesos de fondo | **Ventaja operativa** | Linux/Ollama documenta arranque y supervisión con systemd |
| Modelo local Ollama | Soportado; GPU compatible según hardware/driver | Soportado; GPU compatible según hardware/driver | No hay ganador de rendimiento probado para la GPU del Owner |
| Validar funciones nativas Windows/ACL/handles | **Necesario** para el backend Windows | No valida el mismo backend | Las pruebas nativas deben ejecutarse en el sistema al que pertenecen |
| Migración inmediata | Menor coste/riesgo | Alto coste de portar y validar | No conviene mover el host completo sin necesidad |
| Coordinación a largo plazo de procesos headless/agentes remotos | Viable | **Buena candidata** | Puede alojarse como servicio separado, conservando un agente desktop |
| Paridad actual completa entre plataformas | No demostrada | No demostrada | Windows es más cercano a lo que el código ya intenta hacer; eso no equivale a runtime probado |

## 5. GPU, RAM y coste: no declarar un ganador sin el hardware real

Las páginas oficiales actuales de Ollama documentan instalación nativa tanto para [Windows](https://docs.ollama.com/windows) como para [Linux](https://docs.ollama.com/linux). La documentación de Windows incluye soporte de GPU NVIDIA y AMD Radeon; Linux documenta un servicio de usuario/sistema mediante systemd y las rutas de drivers CUDA/ROCm. La compatibilidad y el rendimiento concretos dependen de la tarjeta, sus controladores, el tamaño del modelo, la VRAM y el backend de aceleración.

Por lo tanto:
- **No** migraría a Linux con la promesa de conseguir por sí solo más VRAM, reducir la memoria que ocupa el modelo o acelerar Ollama.
- **Sí** realizaría, más adelante y bajo una prueba controlada, una comparación del mismo modelo/cuántización, prompt, concurrencia, contexto y hardware: tokens/s, latencia, VRAM usada, RAM máxima, temperatura, carga CPU/GPU, consumo y estabilidad.
- Para una GPU limitada, el plan de concurrencia y la política que decide cuándo ejecutar dos modelos puede pesar más que el SO. IABV ya posee un mecanismo de presión de recursos que puede limitar una comparación paralela, pero no se ejecutó una prueba comparativa en esta evaluación.

Ollama: [Windows support](https://docs.ollama.com/windows), [Linux service/GPU setup](https://docs.ollama.com/linux).

## 6. Autonomía real: qué aporta el SO y qué no arregla

Linux facilita desplegar procesos headless supervisados y reiniciables. La documentación oficial de Ollama propone una unidad systemd para su servicio: [Ollama Linux setup](https://docs.ollama.com/linux). Eso es útil para un futuro coordinador que debe permanecer activo.

Pero cambiar de sistema operativo **no repara por sí solo**:
1. La pérdida de identidad de capacidades requeridas antes de escoger un `ToolCard`.
2. La precedencia y las rutas de fallback entre los selectores existentes.
3. La frescura y vinculación del paquete de contexto al objetivo y a la sesión.
4. La ausencia de prueba universal de entrega/recepción y correlación de las respuestas de los agentes.
5. La falta de prueba de reutilización causal de una lección en una tarea posterior.
6. Los gates de autorización de lectura y de transporte del bridge.

Estos son temas de contratos, wiring, evidencias y política. Requieren reparación y aceptación de los órganos existentes, no una migración de SO.

### Importante para la interacción gráfica en ambos sistemas

No se debe ejecutar la parte que necesita controlar el escritorio como si fuera un servicio genérico sin sesión interactiva. En Windows, Microsoft documenta que los servicios no deben interactuar directamente con el usuario desde el servicio y recomienda una aplicación GUI separada comunicándose mediante IPC protegido por ACL: [Microsoft Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services). Linux también necesita una sesión gráfica/permisos adecuados para controlar el escritorio. El diseño debe separar el coordinador headless del agente de escritorio en vez de asumir que un proceso de fondo ve la pantalla, el perfil o el portapapeles del usuario.

## 7. Hallazgos de preparación/CI relevantes para elegir plataforma

### 7.1 Los runners de GitHub no han ejecutado los tests

El estado canónico de `main` informa que los runs focalizados usando etiquetas `windows-latest` y también el fallback `ubuntu-latest` terminaron con `runner_id=0`, nombre de runner vacío y `steps=[]`. Se detuvieron antes del checkout, la instalación de dependencias o pytest. Esto es un bloqueo de asignación/infraestructura de ejecución; **no** demuestra que el código haya fallado en Windows ni que haya pasado en Linux.

La referencia oficial de GitHub documenta runners Windows y Ubuntu como opciones soportadas: [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). No se debe elegir Linux como sustituto de las pruebas Windows nativas, ni interpretar que una etiqueta de workflow garantice que el trabajo realmente se haya ejecutado.

El estado canónico registra:
```text
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
NATIVE_WINDOWS_HANDLES_ACL=NOT_RUN
REAL_MCP_TRANSPORT=NOT_RUN
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

### 7.2 Candidata M1F no es código aceptado en main

La PR #531 continúa como candidata aislada y en borrador; sus correcciones de vínculo de identidad G3 y preflight del bridge fueron inspeccionadas estáticamente, pero sus pruebas nuevas aún no se han ejecutado. No se puede usar la presencia del lector de handles/guardas del candidato como evidencia de una implementación aceptada o validada nativamente en Windows.

Referencia: [PR #531](https://github.com/jhonf463r/Python/pull/531) y el route snapshot de `CURRENT-STATE.md` (única autoridad de tareas/permisos).

### 7.3 Hallazgo independiente de packaging que debe verificarse antes de comparar sistemas

El `pyproject.toml` de `IABV_v1.5` declara `readme = "README.md"`, pero el inventario recursivo de `main@80c6825` no encontró `IABV_v1.5/README.md` (solo `docs/history/CHAT-ARCH/README.md`). Eso puede afectar la construcción/instalación editable en cualquiera de los dos SO. Es una **inconsistencia estática por reproducir**, no un build fallido demostrado; los builds no se ejecutaron. Antes de hacer una comparación cruzada, resuélvase o verifíquese en una copia aislada para que un fallo de metadata no se confunda con una incompatibilidad del SO.

### 7.4 La higiene del repositorio afecta la reproducibilidad, no determina el SO

El árbol recursivo del repositorio en el baseline contiene 25,648 entradas; dentro de `IABV_v1.5` hay 17,634 archivos. La distribución observada incluye aproximadamente:
- `data/`: 12,593 archivos;
- `.vendor_deps/`: 1,533;
- `.vendor_pytest/`: 692;
- `docs/`: 585;
- `src/`: 253 archivos Python en el paquete inspeccionado;
- `tests/`: 280 archivos Python.

También hay snapshots de auditoría, `.tmp_tests`, `__pycache__` y artefactos de prueba versionados. Esto complica el inventario, aumenta ruido y puede afectar clones, revisión y reproducibilidad. No prueba que Windows ni Linux sea más lento; conviene una política de fixtures/snapshots y exclusión de generados, revisada aparte sin borrar evidencia requerida.

## 8. Ruta de decisión recomendada

### Fase A — Ahora: mantener el host Windows
1. No reinstalar ni migrar el sistema operativo para “conseguir autonomía”.
2. Mantener la versión productiva separada de las copias/ramas de desarrollo; evitar que el arranque automático modifique un checkout de desarrollo con cambios pendientes.
3. Conservar los gates de seguridad: no activar MCP real ni lecturas protegidas hasta que la ruta canónica indique aceptación con evidencia.
4. Resolver la tarea vigente de preservación/reconciliación que indique el `CURRENT-STATE.md` remoto al reanudar trabajo; no sustituirla con este documento.
5. Ejecutar las suites autorizadas en un entorno Windows aislado cuando haya una asignación válida de runner o el entorno local autorizado esté disponible; guardar logs completos y SHA exacto.

### Fase B — Antes de portar funcionalidades
1. Definir una interfaz de plataforma (por ejemplo, captura de ventana/pantalla, foco, portapapeles, lanzamiento y consulta de sesiones) sin exponer tipos Win32 al núcleo de dominio.
2. Mantener backends explícitos: `windows_desktop`, `linux_x11` y/o `linux_wayland`, cada uno declarando sus capacidades reales y sus limitaciones. No fingir paridad si no hay display/sesión/permisos.
3. Mantener Playwright headless separado de la automatización del navegador interactivo y autenticado del usuario.
4. Hacer que el selector de capacidades descarte herramientas/backends que no satisfacen la tarea; una tarjeta existente o un nombre similar no es garantía de capacidad.
5. Añadir CI con dos clases de suite: cross-platform para núcleo/modelos/contexto/MCP genérico; suite nativa Windows para Win32/handles/ACL/UI; suite Linux para backend Linux, servicios, sesión gráfica y permisos Linux.
6. No marcar Windows/Linux como soportados hasta que cada suite se ejecute en un runner/host que realmente registró su ejecución.

### Fase C — Solo si hay un objetivo de servicio 24/7
1. Crear un diseño separado para un coordinador Linux headless: colas/IDs, planner, memoria/provenance y workers de tareas no gráficas.
2. Mantener el agente Windows en la sesión del usuario para ejecutar tareas locales que necesitan GUI/Windows APIs.
3. Definir autenticación/identidad mutua, permisos por herramienta, límites de acciones, timeouts, cancelación, logs de evidencia y un protocolo explícito de resultado/ack entre coordinator y agente.
4. Probar pérdida de red, reinicio de procesos, sesión de usuario cerrada, modelo local no disponible, cuota agotada y respuesta de IA incorrecta.
5. Activar el modo híbrido solo tras pruebas de seguridad, recuperación y aceptación operativa; no simplemente porque cada componente arranque.

## 9. Condiciones para reconsiderar la decisión

Reconsiderar Linux como host principal de todo IABV solo si se cumplen estas condiciones:
- todas las tareas críticas están identificadas y las funciones dependientes de Windows se han sustituido por backends Linux reales o declaradas explícitamente fuera de alcance;
- hay pruebas en Linux de las funciones de producto que se prometen, no solo del núcleo Python;
- los flows de navegador autenticado, sesión, captura y respuesta están definidos sin depender del perfil Windows;
- se ha diseñado y aceptado una autoridad/IPC/identidad específica de Linux para la frontera de seguridad;
- el benchmark en el hardware real prueba una ventaja material en rendimiento/recursos/estabilidad para el modelo que se usará;
- la instalación, actualización, rollback, arranque y backup han sido probados en una instalación Linux limpia.

Si la motivación principal es coordinar más modelos, conservar contexto y trabajar de manera autónoma, esas mejoras deberían primero expresarse como contratos portables del núcleo. No justifican por sí solas una migración completa.

## 10. Conclusión para el siguiente chat

```text
AUDIT_BASE_MAIN=80c6825dabf799087e2469c17826545c8ca613f0
SCOPE=TARGETED_STATIC_PLATFORM_REVIEW_PLUS_RECURSIVE_TREE_INVENTORY
FULL_LINE_BY_LINE_REPO_AUDIT=NOT_CLAIMED
TESTS_BUILD_RUNTIME=NOT_RUN
CURRENT_FULL_APPLICATION_HOST=WINDOWS_IS_LOWER_RISK
LINUX_HEADLESS_COORDINATOR=FUTURE_CANDIDATE
RECOMMENDED_TARGET_ARCHITECTURE=WINDOWS_DESKTOP_AGENT_PLUS_OPTIONAL_LINUX_COORDINATOR
LINUX_EQUIVALENCE_FOR_WIN32_UI_RUNNER=NOT_IMPLEMENTED/NOT_PROVEN
PLAYWRIGHT=PORTABLE_LIBRARY; PRODUCT_SESSION_PARITY_NOT_PROVEN
OLLAMA_WINDOWS_AND_LINUX=SUPPORTED; HARDWARE_BENCHMARK_NOT_RUN
M1F_WINDOWS_AUTHZ_CANDIDATE=OPEN_DRAFT; TESTS_NOT_RUN
HOSTED_RUNNER_ASSIGNMENT=BLOCKED_BEFORE_STEPS_ON_WINDOWS_AND_UBUNTU_LABELS
POTENTIAL_PACKAGING_ISSUE=PYPROJECT_README_PATH_ABSENT_FROM_TREE; NOT_REPRODUCED
CURRENT_STATE_ROUTE=AUTHORITATIVE; MUST_REFRESH BEFORE NEXT WORK
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CODE_CHANGED=NO
OS_MIGRATION_AUTHORIZED=NO
NEXT_ACTION=FOLLOW_FRESH_CANONICAL_CURRENT_STATE; DO NOT USE THIS REPORT TO OVERRIDE ROUTING
```

**Resultado:** mantener Windows para el IABV completo actual; diseñar la portabilidad del núcleo y evaluar Linux como coordinador de servicio futuro, no como una migración precipitada del escritorio. La autonomía se desbloqueará cerrando los contratos de selección, autorización, contexto, entrega y recuperación de errores y probando la cadena completa, más que cambiando el SO de todo el proyecto.
