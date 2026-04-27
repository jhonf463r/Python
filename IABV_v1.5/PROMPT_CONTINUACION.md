# PROMPT DE CONTINUACIÓN — IABV v1.5

## CONTEXTO RÁPIDO

Eres Devin, continuando el trabajo de evolución de IABV v1.5. El repo es `jhonf463r/Python`, workspace en `C:\Python\IABV_v1.5`. Lee `AGENTS.md` primero — es el contrato soberano.

**Estado actual de main (commit más reciente):** PRs #229 y #230 mergeados. El chat routing de API keys está corregido y hay fallback por contexto cuando cloud+Ollama fallan.

**Lo que el usuario espera ahora:** 3 bloques grandes, todos implementados con metacognición real (que el sistema observe, razone, decida, aprenda), NO hardcodeado:

---

## BLOQUE 1: METACOGNICIÓN DE RECURSOS (RAM/GPU/Procesos)

### Qué existe ya (NO duplicar)
- `EnvironmentSelfAwarenessService._memory_snapshot()` — lee RAM total/libre via Win32 `GlobalMemoryStatusEx`
- `EnvironmentSelfAwarenessService._build_risk_signals()` — genera `EnvironmentRiskSignal` con `ram_critical` (<2GB) y `ram_pressure` (<3GB)
- `_assess_resource_pressure()` en `AdaptiveTaskOrchestrator` — lee esos risk signals y clasifica presión
- `gpu_metacognition.py` — detecta GPUs, VRAM, modelos Ollama cargados, auto-libera VRAM (`auto_free_gpu_for_model`)
- `WorldModelService` — panorama de ventanas, procesos, herramientas, red
- `ai_capacity` en `EnvironmentSelfModel` — ya tiene `avoid_heavy_models`, `max_recommended_model`
- `MetacognitionEvolutionMixin` — agrega findings de todos los servicios de evolución para OSES

### Qué falta implementar
Un servicio `ResourceMetacognitionService` (en `src/iabv_v15/services/evolution/resource_metacognition_service.py`) que:

1. **OBSERVA** (método `observe_resources() -> ResourceSnapshot`):
   - RAM: total, libre, por proceso (top 15 consumidores via `tasklist /FO CSV` o WMI)
   - VRAM: total, libre, modelos cargados (`ollama ps`)
   - Procesos: lista con nombre, PID, RAM usada
   - Ya tiene acceso a `_memory_snapshot()` del environment service — reutilizar, no duplicar

2. **RAZONA** (método `analyze_liberation_plan(snapshot) -> LiberationPlan`):
   - Calcula cuánta RAM necesita para el mejor modelo Ollama que podría correr
   - Identifica procesos "safe_to_close" vs "never_close":
     - `never_close`: python, ollama, IABV, svchost, explorer, csrss, lsass, winlogon
     - `safe_to_close_default`: Chrome, Opera GX, Edge, Spotify, Discord, Teams, Slack, Steam, Epic Games
     - `learned_closeable`: lista que crece con el tiempo basada en que cerró antes sin problemas
   - Genera plan: "cerrar X libera ~2.3GB, con eso puedo cargar qwen2.5-coder:7b (necesita 5GB)"
   - Registra la decisión en `DecisionAuditTrail`

3. **ACTÚA** (método `execute_liberation(plan, mode='auto'|'ask') -> LiberationResult`):
   - `mode='auto'`: cierra procesos safe_to_close sin preguntar (el usuario pidió esto explícitamente)
   - `mode='ask'`: muestra en el chat qué va a cerrar y espera confirmación
   - Ejecuta: `taskkill /PID <pid> /F` para cada proceso del plan
   - Después de cerrar: solicita modelo óptimo a Ollama (`ollama pull <model>` si no está, `ollama run <model>` para precalentar)

4. **APRENDE** (método `record_outcome(result)`):
   - Registra en `data/evolution/resource_metacognition/liberation_history.jsonl`:
     - qué cerró, cuánta RAM liberó realmente, qué modelo cargó, si el modelo funcionó
   - La próxima vez consulta este historial para decidir mejor
   - Alimenta `oses_findings()` para que OSES sepa del estado de recursos

5. **AUTO-SELECCIÓN DE MODELO** (método `select_optimal_model(available_ram_gb) -> str`):
   - Mapa de modelos por RAM requerida:
     - `gemma3:1b` → 1.5GB (fallback mínimo)
     - `gemma3:4b` → 3.5GB
     - `qwen2.5-coder:7b` → 5GB
     - `llama3.1:8b` → 6GB
     - `qwen2.5-coder:14b` → 10GB
     - `deepseek-coder-v2:16b` → 12GB
   - Selecciona el más grande que quepa en RAM disponible (después de liberación)
   - Compara con `ExperimentLab` — si un modelo más chico rindió mejor históricamente, prefiere ese

### Integración en bootstrap
En `bootstrap.py`, dentro de `_schedule_startup_evolution()`, DESPUÉS del step 3 (optimize brain):
```python
# Step 4: Resource metacognition — observe, liberate, select model
resource_meta = getattr(self, 'resource_metacognition_service', None)
if resource_meta:
    snapshot = resource_meta.observe_resources()
    plan = resource_meta.analyze_liberation_plan(snapshot)
    if plan.should_liberate:
        result = resource_meta.execute_liberation(plan, mode='auto')
        resource_meta.record_outcome(result)
        logger.info('startup_evolution: resource liberation — freed %.1fGB, model=%s', 
                     result.ram_freed_gb, result.selected_model)
```

### Integración en chat
En `control_center_viewmodel.py`, detectar comandos como:
- "liberar ram", "libera recursos", "optimizar memoria", "cerrar programas innecesarios"
- Llama a `resource_metacognition_service.observe_resources()` → `analyze_liberation_plan()` → muestra plan en chat → ejecuta

---

## BLOQUE 2: LAUNCHER SILENCIOSO + ICONO BURVE

### Qué existe ya
- `scripts/IABV.vbs` — launcher silencioso que llama a `start_iabv.ps1 -StartUI -Quiet` oculto
- `scripts/install_shortcut.ps1` — crea acceso directo en escritorio apuntando a `IABV.vbs` con icono `iabv.ico`
- `scripts/iabv.ico` — icono genérico
- `scripts/start_iabv.ps1` — arranque completo: auto-pull, secrets, health checks, MCP, tunnel, UI
- `scripts/iabv_bootstrap.ps1` — instalación zero-touch (gh, cloudflared, profile, tokens, shortcut)
- `assets/burve.ico` (87KB, 6 tamaños) — icono BURVE generado en esta sesión (ya commiteado en branch, **FALTA merge a main**)
- `assets/burve.png` (210KB) — PNG alta resolución

### Qué falta implementar

1. **Actualizar `install_shortcut.ps1`** para usar `assets/burve.ico` en vez de `scripts/iabv.ico`:
   - Cambiar la referencia del icono a `assets/burve.ico`
   - Nombre del shortcut: "BURVE - IABV v1.5"
   - Agregar al menú Start además del escritorio

2. **Actualizar `IABV.vbs`** para que antes de arrancar PowerShell, copie `assets/burve.ico` a `scripts/` si no existe (por compatibilidad)

3. **Merge de `assets/burve.ico` y `assets/burve.png` a main** — están en branch `devin/1777313824-context-fallback-reply` pero ese branch ya se mergeó como squash, así que los assets no llegaron a main. Hay que hacer un PR nuevo con esos archivos.

4. **Comando de instalación final para el usuario:**
```powershell
cd C:\Python\IABV_v1.5
git pull origin main
powershell -ExecutionPolicy Bypass -File scripts\install_shortcut.ps1
```
Después de eso, doble clic en "BURVE - IABV v1.5" del escritorio arranca todo.

---

## BLOQUE 3: AUTO-ACTUALIZACIÓN INTELIGENTE

### Qué existe ya
- `start_iabv.ps1` ya tiene `-AutoPull` (default ON) que hace `git pull --rebase=false` antes de arrancar
- Si hay commits nuevos, corre `summarize_updates` para imprimir un resumen en español
- Si el pull falla, aborta con mensaje claro

### Qué falta implementar
La auto-actualización ya funciona en el script PowerShell. Lo que falta es hacerla visible desde la metacognición:

1. **En `_schedule_startup_evolution()`**: detectar si el commit actual es diferente al último registrado, y si hubo actualización, generar un finding en OSES: "Se actualizó de commit X a Y — N archivos cambiados"

2. **En el chat**: si el usuario pregunta "estas actualizado?", "hay actualizaciones?", el sistema puede verificar `git fetch origin main --dry-run` y responder sin necesidad de reiniciar

3. **Auto-restart tras update**: si el auto-pull detectó cambios en archivos críticos (`bootstrap.py`, `control_center_viewmodel.py`, servicios core), relanzar el proceso automáticamente (ya existe el mecanismo en `start_iabv.ps1` que podría extenderse)

---

## ESTADO DE API KEYS (IMPORTANTE)

El usuario NO tiene ninguna API key de cloud configurada:
```
startup_evolution: API keys — configured=none, missing=['groq', 'gemini', 'openrouter', 'together']
startup_evolution: best reasoning provider = ollama_local (latency=4000ms success=80%)
```

Esto significa que TODAS las respuestas pasan por Ollama local (lento, timeout frecuente). El fix de PR #230 agregó `_try_context_based_reply()` que responde preguntas sobre API keys sin necesitar IA, pero para respuestas generales inteligentes necesita al menos una cloud key.

**Recomendación para el usuario:** Configurar Groq (gratis, ~200ms):
1. https://console.groq.com/keys → crear key
2. En chat IABV: "ingresar clave" → pegar la key
3. El sistema la guarda en `~/.iabv_secrets.ps1` automáticamente via `save_secret_to_profile()`

---

## ARCHIVOS CLAVE QUE MODIFICAR

| Archivo | Qué hacer |
|---------|-----------|
| `src/iabv_v15/services/evolution/resource_metacognition_service.py` | **CREAR** — servicio completo de metacognición de recursos |
| `src/iabv_v15/bootstrap.py` | Wiring del nuevo servicio + llamada en startup evolution |
| `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py` | Chat commands para "liberar ram"/"optimizar" |
| `src/iabv_v15/services/evolution/metacognition_evolution_mixin.py` | Agregar `resource_metacognition` a findings |
| `scripts/install_shortcut.ps1` | Actualizar icono a `assets/burve.ico` |
| `assets/burve.ico` | Merge a main (no llegó en squash merge de PR #230) |
| `assets/burve.png` | Merge a main |
| `tests/test_resource_metacognition.py` | **CREAR** — tests del servicio |

---

## REGLAS DE ORO (del AGENTS.md)

1. **NO crear otro cerebro** — el servicio es un módulo que alimenta findings a OSES via `MetacognitionEvolutionMixin`, no decide rutas
2. **NO duplicar** `_memory_snapshot()`, `_build_risk_signals()`, `auto_free_gpu_for_model()` — reutilizar
3. **Registrar decisiones** en `DecisionAuditTrail` y resultados en `ExperimentLab`
4. **Branch `devin/*`** para auto-merge
5. **Tests primero** del slice que toques, luego regresión
6. **Una sola ventana** — todo se controla desde el chat de IABV, no pedirle al usuario que abra PowerShell

---

## VERIFICACIÓN FINAL

Cuando termines, el usuario debería poder:
1. Hacer doble clic en el icono BURVE del escritorio → IABV arranca sin PowerShell visible
2. IABV auto-actualiza desde GitHub al arrancar
3. Al arrancar, libera RAM cerrando programas innecesarios automáticamente
4. Selecciona el mejor modelo Ollama para la RAM disponible
5. En el chat: "la api key de groq la está usando?" → responde directo (sin listar cuentas, sin timeout)
6. En el chat: "liberar ram" → muestra cuánta RAM hay, qué cerró, qué modelo cargó
7. En el chat: "que cuentas tienes" → sigue funcionando el scanner de cuentas

## TESTS PARA VERIFICAR

```powershell
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'; & 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/test_resource_metacognition.py tests/test_specific_apikey_routing.py -q
```
