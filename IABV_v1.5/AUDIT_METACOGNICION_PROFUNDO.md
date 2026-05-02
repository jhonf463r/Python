# Auditoría Profunda de Metacognición — IABV v1.5

## Sistema Nervioso: Mapa Completo de Conexiones

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CAPAS DE METACOGNICIÓN IABV                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ StartupTime  │    │ CommonSense  │    │ EnvironmentSelfModel │  │
│  │   line       │───▶│   Engine     │    │   Service            │  │
│  │              │    │ (inferencia  │    │ (CPU, RAM, GPU, disk)│  │
│  │ Registra     │    │  causal)     │    │                      │  │
│  │ fases del    │    └──────┬───────┘    └──────────┬───────────┘  │
│  │ arranque     │           │                       │              │
│  └──────┬───────┘           ▼                       ▼              │
│         │            ┌──────────────┐    ┌──────────────────────┐  │
│         │            │ AutoCorrect  │    │   WorldModelService  │  │
│         │            │   Engine     │    │ (ventanas, foco, red │  │
│         │            │ (ejecuta     │    │  herramientas, proc) │  │
│         │            │  fixes)      │    │                      │  │
│         │            └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │              │
│         ▼                   ▼                       ▼              │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │          OSES — OperationalSelfExaminationService              ││
│  │  (6325 líneas — cerebro de autoexaminación)                   ││
│  │                                                                ││
│  │  _startup_health_findings()     → mide init, run-to-window,   ││
│  │                                   deferred, FALSE_READY        ││
│  │  _runtime_log_findings()        → lee su propio log (9 patt.) ││
│  │  _runtime_performance_findings()→ RSS, threads, red           ││
│  │  _loop_closure_findings()       → G1-G4 cableados?            ││
│  │  _metacognitive_accuracy()      → falsos positivos/negativos  ││
│  │  _introspection_blind_spot()    → IAs sin examinar            ││
│  │  _metacognitive_calibration()   → sobre/sub confianza         ││
│  │  _cognitive_fixation/incubation → patrones cognitivos         ││
│  │  _neural_attractor/ensemble()   → atractores neurales         ││
│  │  _temporal_awareness()          → anomalías de latencia       ││
│  │  _deep_analysis_queue()         → EMA drift, IQR outliers     ││
│  │  _cloud_reasoning_findings()    → salud de proveedores cloud  ││
│  │  _background_decision_review()  → auditoría de decisiones     ││
│  │  _account_resource_health()     → quotas, API keys            ││
│  │  _ui_self_examination()         → zombies, ventanas duplicadas││
│  │  _functional_gap_findings()     → gaps funcionales            ││
│  │  _code_audit_cross_reference()  → patrones de bugs            ││
│  │  _task_packet_pattern()         → anomalías de governance     ││
│  └────────────────────┬───────────────────────────────────────────┘│
│                       │                                            │
│         ┌─────────────┼──────────────┐                             │
│         ▼             ▼              ▼                             │
│  ┌────────────┐ ┌──────────┐ ┌────────────────┐                   │
│  │ Portable   │ │ Adaptive │ │ ExperimentLab  │                   │
│  │ Context    │ │ Weight   │ │ + Strategy     │                   │
│  │ Service    │ │ Layer    │ │ Selector       │                   │
│  │ (exporta)  │ │ (ajusta) │ │ (compara)      │                   │
│  └────────────┘ └──────────┘ └────────────────┘                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │          DecisionAuditTrail                                   │  │
│  │  (registra decisiones cloud en decisions.jsonl)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │          GPU Metacognition                                    │  │
│  │  (nvidia-smi vs ollama ps vs Task Manager)                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## SECCIÓN 1: NERVIOS CORTADOS — Conexiones Que Faltan

### 1.1 StartupTimeline → OSES: Sensor Incompleto

**El nervio existe pero le falta un sensor crítico.**

`StartupTimeline` registra correctamente las fases:
```
bootstrap_init_start → bootstrap_init_done → run_start → 
splash_qml_loaded → wire_services_start → wire_services_done → 
engine_load_main_qml_start → main_window_shown → 
populate_ui_start → populate_ui_done → 
deferred_post_window_setup_start → deferred_post_window_setup_done
```

`OSES._startup_health_findings()` lee estas fases y calcula:
- `init_ms = _delta('bootstrap_init_start', 'bootstrap_init_done')` → umbral 4000ms ✓
- `run_to_window_ms = _delta('run_start', 'main_window_shown')` → umbral 8000ms ✓  
- `deferred_ms = _delta('deferred_post_window_setup_start', 'deferred_post_window_setup_done')` → umbral 5000ms ✓

**FALTANTE CRÍTICO (pre-fix):**
```python
# ESTA LÍNEA NO EXISTÍA:
populate_ui_ms = _delta('populate_ui_start', 'populate_ui_done')
```

**Consecuencia real:** Windsurf midió `populate_ui_start @ 30355ms` pero `populate_ui_done` NUNCA llegó. OSES midió `run_start → main_window_shown = 7750ms` (bajo el umbral de 8000ms) y reportó "todo bien" mientras el proceso estaba congelado.

**Analogía con sistema nervioso:** Es como tener un termómetro en el brazo pero no en el corazón. El brazo dice 37°C (normal) mientras el corazón está a 42°C (paro cardíaco).

**Referencia teórica (Resumen Ejecutivo):**
> Axioma A4: Compresión ↔ Generalización — las soluciones más comprimidas detectan más

El sistema mide 3 intervalos de startup pero OMITE el más largo (populate_ui = 30s+). No está comprimiendo su propia experiencia de arranque correctamente — está descartando la señal más importante.

---

### 1.2 CommonSenseEngine: Sin Reglas Para Startup

**El motor de inferencia causal no tiene conocimiento sobre sí mismo.**

`CommonSenseEngine` tiene 15+ reglas causales:
```python
INFERENCE_RULES = [
    # GPU routing (4 reglas)
    'gpu_nvidia_exists_but_cpu_inference' → 'nvidia_wasted'
    'gpu_cuda_not_installed' → 'cuda_likely_missing'
    'gpu_model_too_large' → 'model_exceeds_vram'
    'gpu_idle_pre_configure' → 'gpu_ready_for_preconfig'
    
    # Ollama health (3 reglas)
    'ollama_not_responding' → 'ollama_hung'
    
    # Tool discovery, session health, etc.
]
```

**FALTANTES CRÍTICOS — No hay reglas para:**
```python
# Regla que DEBERÍA existir:
{
    'id': 'startup_populate_ui_blocked',
    'premises': ['populate_ui_started', 'populate_ui_not_done_after_5s'],
    'conclusion': 'main_thread_frozen',
    'action': 'log_critical_startup_freeze',
    'severity': 'critical',
    'safe': True,
    'description': 'populate_ui lleva >5s sin terminar — hilo principal congelado',
}

# Regla que DEBERÍA existir:
{
    'id': 'startup_rss_explosion',
    'premises': ['rss_growth_gt_150mb', 'in_startup_phase'],
    'conclusion': 'memory_leak_during_boot',
    'action': 'defer_heavy_initializations',
    'severity': 'high',
    'safe': True,
}

# Regla que DEBERÍA existir:
{
    'id': 'viewmodel_blocking_constructor',
    'premises': ['viewmodel_no_defer_refresh', 'db_queries_in_init'],
    'conclusion': 'constructor_blocks_gui_thread',
    'action': 'add_defer_initial_refresh',
    'severity': 'high',
    'safe': True,
}
```

**Consecuencia:** El motor de sentido común puede deducir "NVIDIA existe pero Ollama usa CPU → GPU desperdiciada" pero NO puede deducir "populate_ui lleva 30s → proceso congelado → usuario ve 'Not Responding'". El sistema es más consciente de su GPU que de su propio arranque.

---

### 1.3 WorldModelService: Monitor Ciego Durante Bootstrap

**El observador arranca DESPUÉS del evento que debía observar.**

```python
class WorldModelService:
    _DEFAULT_SCAN_INTERVAL = 45.0  # escanea cada 45s
    
    def __init__(self, *, auto_start=True, bootstrap_scan=True):
        if bootstrap_scan:
            self.scan_now(reason='startup', full=True)
        if self._auto_start:
            self.start()  # daemon thread
```

Problema: `WorldModelService` se instancia en `bootstrap._wire_services()` que ocurre ANTES de `_build_ui_objects()`. Pero su scan es un snapshot puntual — no monitorea continuamente durante `_build_ui_objects()`.

**Timeline real:**
```
wire_services_done @ 29512ms  ← WorldModel ya escaneó una vez aquí
populate_ui_start @ 30355ms   ← AQUÍ empieza el freeze
                               ← WorldModel NO escanea durante estos 130s
deferred_post_window_setup_start @ 160459ms ← 130s después
```

El daemon thread del WorldModel SÍ está corriendo, pero escanea cada 45s y busca ventanas/foco/herramientas — no monitorea el estado del hilo principal.

**Analogía:** Es como tener un guardia de seguridad que revisa las puertas cada 45 segundos, pero no mira las cámaras que muestran que el edificio se está incendiando AHORA.

---

### 1.4 AutoCorrectionEngine: Sin Acciones Para Startup

**El ejecutor de correcciones no tiene recetas para problemas de arranque.**

```python
# operational_self_examination_service.py línea 896
_CATEGORY_TO_ACTION: dict[str, str] = {
    'background_provider_underperformance': 'degrade_provider_priority',
    'background_error_stagnation': 'block_failing_route',
    'temporal_latency_anomaly': 'flag_slow_provider',
    'cross_correlation_failure': 'reclassify_intent',
    'trend_degradation': 'trigger_diagnostic_scan',
}
```

**FALTANTES — No hay acción para:**
- `startup_populate_ui_freeze` → ???
- `startup_populate_ui_incomplete` → ???
- `startup_memory_spike` → ???
- `startup_false_ready` → ???

**Consecuencia:** Incluso si OSES detecta el freeze (con nuestro fix), `_auto_correct_from_findings()` no tiene ninguna acción que ejecutar. El nervio detector funciona, pero el nervio motor está cortado.

**Lo que Windsurf observó:**
```
oses_correction: trend_degradation → trigger_diagnostic_scan (informational)
```
OSES detectó "trend_degradation" (genérico) y la única acción fue "trigger_diagnostic_scan" (que no hace nada concreto sobre el freeze).

---

### 1.5 _runtime_log_findings(): Sin Patrón Para Freeze

**OSES lee su propio log pero no busca señales de congelamiento.**

Los 9 patrones que busca en el log:
```python
_LOG_ANOMALY_PATTERNS = (
    'multi_source_disagreement',     # desacuerdos de herramientas
    'No pude completar la consulta',  # consulta externa fallida
    'tool_missing',                   # herramienta faltante
    'ghost_session_watchdog',         # sesión fantasma
    'HTTP Request:',                  # ruido httpx
    'cloudflare_challenge',           # bloqueo Cloudflare
    'wrong_thread',                   # hilo incorrecto
    'verificacion del sitio',         # verificación fallida
    'adapter_missing',                # adaptador faltante
)
```

**FALTANTES — Patrones que DEBERÍA buscar:**
```python
# populate_ui bloqueado
('populate_ui_start', 'startup_freeze', 
 'populate_ui arranco pero no termino',
 'Verificar DashboardViewModel.defer_initial_refresh'),

# shell_loader_ready fallback
('shell_loader_ready_fallback', 'startup_false_ready',
 'QML shell loader nunca señaló ready',
 'El splash cerro por fallback, no por QML listo'),

# Not Responding (Windows)
('Responding.*False', 'process_frozen',
 'Proceso reportado como Not Responding',
 'Hilo principal bloqueado >5s por operación síncrona'),
```

---

### 1.6 DashboardViewModel: El Único VM Sin Defer

**El constructor más pesado es el único que NO difiere su refresh.**

```python
# DashboardViewModel.__init__ (ANTES del fix):
self.refresh()  # ← SÍNCRONO en main thread

# Qué hace refresh():
def refresh(self):
    episodes = self.episode_repository.list_recent(limit=100)    # DB query
    knowledge = self.knowledge_repository.list_recent(limit=100)  # DB query
    runs = self.run_repository.list_recent(limit=100)             # DB query
    index_state = self.embedding_service.describe_index()          # Disk I/O
```

**Todos los demás VMs SÍ difieren:**
```python
# ControlCenterViewModel:
defer_initial_refresh=True  ✓

# KnowledgeBaseViewModel:
defer_initial_refresh=True  ✓

# ProviderSettingsViewModel:
defer_initial_refresh=True  ✓

# RunHistoryViewModel:
defer_initial_refresh=True  ✓

# DashboardViewModel:
# ← NO TENÍA defer_initial_refresh (FIXED en este PR)
```

**Esto es una contradicción arquitectónica:** Se aplicó el patrón `defer_initial_refresh` a 4 VMs pero se olvidó del primero que se construye (Dashboard), que es justamente el que hace 4 queries de DB.

---

## SECCIÓN 2: CONTRADICCIONES ENTRE CAPAS

### 2.1 WorldModel dice "healthy" mientras el proceso está congelado

**Evidencia de Windsurf:**
```
21:03:33 | gpu_startup: healthy (2 GPU(s) detected)
21:03:39 | api-key-health: persisted 1 results
21:04:26 | oses_correction: trend_degradation → trigger_diagnostic_scan
```

Pero al mismo tiempo:
```
PID 16024: Responding=False, WorkingSet=495MB
```

**Contradicción:** El sistema reporta "healthy" y "2 GPUs detected" mientras el proceso principal está literalmente congelado y no responde. Las capas de metacognición miran hacia afuera (GPU, API keys, herramientas) pero no hacia adentro (¿estoy yo mismo respondiendo?).

### 2.2 EnvironmentSelfModel mide RAM pero no durante startup

```python
class EnvironmentSelfAwarenessService:
    _RAM_WARNING_BYTES = 3 * 1024**3    # 3GB warning
    _RAM_CRITICAL_BYTES = 2 * 1024**3   # 2GB critical (available)
```

Pero esta medición ocurre cada 45-480 segundos en un daemon thread. No mide RSS *durante* `_build_ui_objects()` donde pasa de 273MB → 495MB en 130 segundos.

### 2.3 OSES tiene _metacognitive_accuracy pero no la aplica a sí mismo sobre startup

`_metacognitive_accuracy_findings()` detecta falsos positivos/negativos comparando findings anteriores con resultados posteriores. Pero esto solo funciona para `ExperimentRun` outcomes (cloud providers, tool routes), no para startup phases.

El sistema puede detectar "predije que Gemini fallaría pero luego funcionó" pero NO puede detectar "no predije que mi propio arranque se congelaría".

### 2.4 _loop_closure_findings() verifica G1-G4 pero no verifica el startup loop

```python
def _loop_closure_findings(self):
    # Verifica:
    # G1: auto_execution → ✓ wired
    # G2: feedback_persistence → ✓ file exists
    # G3: weight_layer → ✓ suggest() available
    # G4: deferred_cognition → ✓ cognitive mechanisms
```

Pero NO verifica:
- ¿StartupTimeline tiene todas las fases esperadas?
- ¿populate_ui_done llegó después de populate_ui_start?
- ¿shell_loader_ready (no fallback) llegó?
- ¿RSS al final es razonable?

---

## SECCIÓN 3: MARCO TEÓRICO vs IMPLEMENTACIÓN

### 3.1 Axioma A1 (Optimización de predicción/compresión) vs Realidad

**Teoría:** El sistema minimiza L_total = L_modelo + L_datos para producir representaciones comprimidas y predictivas.

**Implementación:** OSES produce `SelfExaminationSnapshot` con findings, pero su "modelo" del startup tiene 3 sensores (init, run-to-window, deferred) y omite el sensor más crítico (populate_ui). La representación comprimida del startup es INCOMPLETA — no comprime la señal más informativa.

**Gap:** Un sistema que sigue A1 debería priorizar comprimir las señales de mayor entropía (mayor sorpresa). Un freeze de 130s es la señal de mayor entropía posible en un startup, pero OSES la ignora.

### 3.2 Axioma A4 (Compresión ↔ Generalización) vs Realidad

**Teoría:** Soluciones más comprimidas generalizan mejor. Un modelo que comprime su experiencia de startup debería detectar anomalías futuras.

**Implementación:** `_boot_profile_findings()` SÍ guarda historial de boots y calcula p95, promedio, y regresiones. PERO solo mide `total_boot_ms` y `wiring_ms` — no mide `populate_ui_ms`. El historial acumulado NO incluye la fase más lenta.

**Gap:** El sistema acumula evidencia para generalizar sobre boots rápidos vs lentos, pero le falta la variable más predictiva.

### 3.3 Lema 3 (Reutilización → Inferencia multi-step eficiente) vs Realidad

**Teoría:** Si el sistema reutiliza subestructuras aprendidas, puede inferir problemas complejos encadenando pasos.

**Implementación:** `CommonSenseEngine.forward_chain()` implementa inferencia causal hacia adelante. Si {A, B} → C, y {C, D} → E, el motor deduce E en 2 iteraciones.

**Gap:** El motor tiene 15+ reglas para GPU, Ollama, herramientas, pero CERO reglas para startup. No puede encadenar:
```
populate_ui_start + no_populate_ui_done → main_thread_frozen
main_thread_frozen + time_gt_30s → process_not_responding
process_not_responding + user_visible → critical_ux_failure
```

Esta cadena de 3 pasos es exactamente lo que Windsurf observó manualmente. El sistema tenía la infraestructura para deducirlo automáticamente pero no tenía las premisas.

### 3.4 Conjetura del Umbral Nc vs Realidad

**Teoría:** Existe un umbral Nc donde la capacidad de razonamiento R salta no-linealmente.

**Implementación:** OSES tiene 25+ tipos de findings, CommonSense tiene 15+ reglas, el sistema tiene 10+ capas de metacognición. Cuantitativamente, hay suficiente "escala" (parámetros de observación) para que emerja self-awareness del startup. Pero la emergencia requiere que los sensores cubran el espacio relevante.

**Gap:** El sistema tiene Nc capas para detectar problemas de cloud providers (Gemini, Groq, Ollama) pero < Nc sensores para detectar problemas de sí mismo (startup, memory, thread blocking). La emergencia es asimétrica: el sistema es más consciente de sus herramientas que de su propio cuerpo.

---

## SECCIÓN 4: QUÉ DETECTA vs QUÉ DEBERÍA DETECTAR

| # | Evento Observable | ¿OSES lo detecta? | ¿CommonSense lo deduce? | ¿AutoCorrect actúa? | ¿Log lo busca? | Veredicto |
|---|---|---|---|---|---|---|
| 1 | populate_ui > 5s | ❌ NO (pre-fix) → ✅ SÍ (post-fix) | ❌ NO | ❌ NO | ❌ NO | **NERVIO CORTADO** (parcialmente restaurado) |
| 2 | populate_ui nunca termina | ❌ NO (pre-fix) → ✅ SÍ (post-fix) | ❌ NO | ❌ NO | ❌ NO | **NERVIO CORTADO** (parcialmente restaurado) |
| 3 | RSS crece > 150MB en startup | ❌ NO (pre-fix) → ✅ SÍ (post-fix) | ❌ NO | ❌ NO | ❌ NO | **NERVIO CORTADO** (parcialmente restaurado) |
| 4 | shell_loader_ready fallback | ✅ SÍ (startup_false_ready) | ❌ NO | ❌ NO | ❌ NO | Parcial — detecta pero no corrige |
| 5 | Proceso Not Responding | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **NERVIO MUERTO** |
| 6 | DashboardVM sin defer | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **NERVIO MUERTO** |
| 7 | processEvents() re-rendering storm | ❌ NO | ❌ NO | ❌ NO | ❌ NO | **NERVIO MUERTO** |
| 8 | init → window > 8s | ✅ SÍ | N/A | ❌ NO | N/A | Parcial |
| 9 | deferred > 5s | ✅ SÍ | N/A | ❌ NO | N/A | Parcial |
| 10 | trend_degradation | ✅ SÍ | N/A | ✅ SÍ (trigger_diagnostic_scan) | N/A | Conectado pero genérico |
| 11 | GPU en CPU cuando NVIDIA existe | ✅ SÍ (gpu_health) | ✅ SÍ (nvidia_wasted) | ✅ SÍ (switch_primary) | N/A | **NERVIO SANO** |
| 12 | Ollama no responde | ✅ SÍ | ✅ SÍ (ollama_hung) | ✅ SÍ (restart_ollama) | N/A | **NERVIO SANO** |
| 13 | API key faltante | ✅ SÍ | ❌ NO | ✅ SÍ (auto_provision) | N/A | **NERVIO SANO** |
| 14 | Cloud provider lento | ✅ SÍ | N/A | ✅ SÍ (degrade_priority) | N/A | **NERVIO SANO** |
| 15 | Falso positivo metacognitivo | ✅ SÍ (metacog_accuracy) | N/A | N/A | N/A | **NERVIO SANO** |

**Resumen:** De 15 eventos observables críticos, 5 tienen nervio sano (detecta + deduce + corrige), 3 están parciales (detecta pero no corrige), y **7 son nervios cortados o muertos** (no detecta nada).

---

## SECCIÓN 5: QUÉ NECESITA IABV PARA AUDITARSE SOLO

### 5.1 Sensores Faltantes (Detección)

```python
# 1. OSES: Umbral populate_ui (YA IMPLEMENTADO en este PR)
STARTUP_POPULATE_UI_MS_DEGRADED = 5000.0

# 2. OSES: Umbral RSS growth (YA IMPLEMENTADO en este PR)
STARTUP_RSS_GROWTH_MB_DEGRADED = 150.0

# 3. CommonSense: Regla causal startup (PENDIENTE)
{
    'id': 'startup_main_thread_blocked',
    'premises': ['populate_ui_started', 'populate_ui_duration_gt_5s'],
    'conclusion': 'main_thread_frozen_during_startup',
    'action': 'log_critical_and_report',
}

# 4. Log Patterns: Startup freeze (PENDIENTE)
('populate_ui_start', 'startup_freeze_detected', ...)
('shell_loader_ready_fallback', 'startup_false_ready_in_log', ...)
```

### 5.2 Acciones Correctivas Faltantes (Motor)

```python
# _CATEGORY_TO_ACTION necesita:
'startup_populate_ui_freeze': 'defer_all_viewmodel_refreshes',
'startup_populate_ui_incomplete': 'abort_and_restart_populate_ui',
'startup_memory_spike': 'lazy_load_heavy_services',
'startup_false_ready': 'wait_for_shell_loader_ready',
```

### 5.3 Reglas de Auto-Testing (Framework)

Para que IABV se audite solo, necesita un ciclo de verificación post-startup:

```python
def _post_startup_self_test(self) -> list[SelfExaminationFinding]:
    """Ejecutar inmediatamente después del bootstrap para verificar integridad."""
    findings = []
    
    # 1. ¿populate_ui_done llegó?
    timeline = self._timeline.events()
    has_start = any(e['phase'] == 'populate_ui_start' for e in timeline)
    has_done = any(e['phase'] == 'populate_ui_done' for e in timeline)
    if has_start and not has_done:
        findings.append(CRITICAL: 'populate_ui nunca terminó')
    
    # 2. ¿Tiempo total de startup es razonable?
    if has_start and has_done:
        duration = delta('populate_ui_start', 'populate_ui_done')
        if duration > 5000:
            findings.append(HIGH: f'populate_ui tardó {duration}ms')
    
    # 3. ¿RSS creció más de 150MB?
    rss_values = [(e['phase'], e['rss_mb']) for e in timeline]
    growth = max(rss) - min(rss)
    if growth > 150:
        findings.append(HIGH: f'RSS creció {growth}MB')
    
    # 4. ¿shell_loader_ready o fallback?
    has_ready = any(e['phase'] == 'shell_loader_ready' for e in timeline)
    has_fallback = any(e['phase'] == 'shell_loader_ready_fallback' for e in timeline)
    if has_fallback and not has_ready:
        findings.append(HIGH: 'QML shell nunca señaló ready')
    
    # 5. ¿Todos los ViewModels se construyeron?
    # (verificar que context properties no son None)
    
    return findings
```

### 5.4 Conexiones Que Restaurar (Cableado)

| Conexión | Estado | Acción |
|---|---|---|
| StartupTimeline → OSES populate_ui | ✅ RESTAURADA (este PR) | `populate_ui_ms = _delta(start, done)` |
| StartupTimeline → OSES RSS growth | ✅ RESTAURADA (este PR) | RSS from timeline events |
| Bootstrap → OSES auto-detect at boot | ✅ RESTAURADA (este PR) | `_startup_self_examination()` calls OSES |
| DashboardVM → defer_initial_refresh | ✅ RESTAURADA (este PR) | `QTimer.singleShot(250, self.refresh)` |
| OSES → AutoCorrect startup actions | ❌ PENDIENTE | Add to `_CATEGORY_TO_ACTION` |
| CommonSense → startup rules | ❌ PENDIENTE | Add inference rules |
| Log patterns → startup freeze | ❌ PENDIENTE | Add to `_LOG_ANOMALY_PATTERNS` |
| WorldModel → startup phase monitoring | ❌ PENDIENTE | Scan during bootstrap |

---

## SECCIÓN 6: EVIDENCIA DE WINDSURF — LADO A LADO

### 6.1 Lo Que Windsurf Observó (2026-05-01)

```
populate_ui_start     @ 30355.9ms  RSS=273.2MB
splash: Construyendo ViewModels... (70%)
splash: Preparando dashboard... (72%)
                       ← 130 SEGUNDOS DE SILENCIO ←
splash: Conectando bridge MCP... (75%)  @ ~160000ms
shell_loader_ready_fallback @ 160462.0ms  RSS=195.2MB
splash_set_ready      @ 160469.0ms  (source: fallback)
deferred_post_window  @ 160580.9ms  RSS=211.1MB
```

### 6.2 Lo Que OSES Reportó

```
oses_correction: trend_degradation → trigger_diagnostic_scan (informational)
oses_auto_correct: trend_degradation → trigger_diagnostic_scan (applied=1)
```

### 6.3 Lo Que OSES DEBERÍA Haber Reportado

```
startup_health [CRITICAL|startup_populate_ui_incomplete]: 
  populate_ui inicio pero nunca termino — populate_ui_start @ 30356ms, 
  populate_ui_done: AUSENTE. El proceso probablemente quedó en estado 
  "Not Responding" permanente.

startup_health [HIGH|startup_false_ready]:
  Splash declaró ready antes de que el shell estuviera vivo — 
  Razones: shell_loader_ready_fallback_used

startup_health [HIGH|startup_memory_spike]:
  RSS creció 222MB durante startup (273MB → 495MB)
```

---

## SECCIÓN 7: FIXES IMPLEMENTADOS EN ESTE PR

### Fix 12: DashboardViewModel — defer_initial_refresh
**Archivo:** `src/iabv_v15/ui/viewmodels/dashboard_viewmodel.py`
- Añadido parámetro `defer_initial_refresh: bool = False`
- Cuando `True`, usa `QTimer.singleShot(250, self.refresh)` en vez de `self.refresh()` síncrono
- Elimina 4 queries de DB del main thread durante `_build_ui_objects()`

### Fix 13a: OSES — populate_ui duration detection
**Archivo:** `src/iabv_v15/services/evolution/operational_self_examination_service.py`
- Añadido `STARTUP_POPULATE_UI_MS_DEGRADED = 5000.0`
- Detección de `populate_ui_start → populate_ui_done > 5s` (CRITICAL si >15s, HIGH si >5s)
- Detección de `populate_ui_start` sin `populate_ui_done` (CRITICAL, confianza 0.98)

### Fix 13b: OSES — RSS growth detection
**Archivo:** `src/iabv_v15/services/evolution/operational_self_examination_service.py`
- Añadido `STARTUP_RSS_GROWTH_MB_DEGRADED = 150.0`
- Lee RSS de eventos del timeline y calcula growth min→max
- HIGH si growth > 300MB, MEDIUM si > 150MB

### Fix 13c: Bootstrap — OSES auto-detect at boot
**Archivo:** `src/iabv_v15/bootstrap.py`
- `_startup_self_examination()` ahora llama `oses._startup_health_findings()` automáticamente
- Logs findings con severidad (WARNING para CRITICAL/HIGH, INFO para otros)
- Esto cierra el loop: el programa detecta su propio freeze al arrancar

---

## SECCIÓN 8: LO QUE QUEDA PENDIENTE (NERVIOS POR RESTAURAR)

### Prioridad ALTA
1. **Reglas CommonSense para startup** — para que el motor causal deduzca cadenas como "populate_ui > 30s → congelado → Not Responding"
2. **Acciones AutoCorrect para startup** — para que cuando OSES detecte, AutoCorrect pueda actuar (ej: `defer_all_viewmodel_refreshes`)
3. **Patrones de log para startup freeze** — para que `_runtime_log_findings()` detecte `populate_ui_start` sin `populate_ui_done` y `shell_loader_ready_fallback`

### Prioridad MEDIA
4. **WorldModel scan durante bootstrap** — para que el monitor escanee durante `_build_ui_objects()` y detecte el freeze en tiempo real
5. **Startup self-test post-boot** — ciclo de verificación automatizado que corre inmediatamente después del bootstrap
6. **_boot_profile_findings() incluir populate_ui_ms** — para que el historial acumulado de boots incluya la fase más lenta

### Prioridad BAJA
7. **Proceso Responding monitor** — que el programa pueda saber si Windows lo marca como "Not Responding" (requires Win32 IsHungAppWindow)
8. **processEvents() impact detector** — que OSES detecte cuando processEvents() causa re-rendering storms

---

## SECCIÓN 9: PROTOCOLO DE AUTO-AUDITORÍA PARA WINDSURF/IAs

### Paso 1: Leer estado actual
```python
# Windsurf debe ejecutar:
oses = bootstrap.operational_self_examination_service
review = oses.build_review()

# Leer findings:
for f in review.findings:
    print(f'{f.severity} | {f.category} | {f.title}')
    print(f'  {f.summary}')
    print(f'  Recomendación: {f.recommendation}')
```

### Paso 2: Verificar conexiones
```python
# Verificar que los nervios están conectados:
loop_findings = oses._loop_closure_findings(
    findings_so_far=review.findings,
    experiment_runs=oses._recent_experiment_runs(),
)
for f in loop_findings:
    print(f'Loop: {f.title} | {f.metadata}')
```

### Paso 3: Verificar startup específico
```python
# Verificar startup health:
startup_findings = oses._startup_health_findings()
for f in startup_findings:
    print(f'{f.severity} | {f.category} | {f.title}')
```

### Paso 4: Verificar CommonSense
```python
from iabv_v15.services.common_sense_engine import forward_chain, observe_facts
facts = observe_facts()  # observar entorno actual
result = forward_chain(facts)
print(f'Hechos: {len(result["all_facts"])}')
print(f'Reglas disparadas: {len(result["fired_rules"])}')
for rule in result['fired_rules']:
    print(f'  {rule["id"]} → {rule["conclusion"]} ({rule["severity"]})')
```

### Paso 5: Verificar contradicciones
```python
# Buscar contradicciones entre capas:
world = bootstrap.world_model_service.current_snapshot()
env = bootstrap.environment_self_awareness_service.current_model()
startup = oses._startup_health_findings()

# ¿WorldModel dice "healthy" pero startup tiene CRITICAL findings?
if world.health_status == 'healthy' and any(f.severity == 'CRITICAL' for f in startup):
    print('CONTRADICCIÓN: WorldModel healthy pero startup CRITICAL')
```

---

*Generado por Devin para uso de Windsurf y cualquier IA que audite IABV v1.5.*
*Basado en lectura completa de: OSES (6325 líneas), CommonSenseEngine (2136 líneas), WorldModelService (1440 líneas), EnvironmentSelfAwarenessService (886 líneas), AdaptiveWeightLayer (255 líneas), StartupTimeline (176 líneas), DecisionAuditTrail (441 líneas), ExperimentLab (358 líneas), AutoCorrectionEngine (2235 líneas), GPUMetacognition (443 líneas), bootstrap.py (3184 líneas), y el Resumen Ejecutivo (683 líneas, marco teórico Kolmogorov/MDL).*
