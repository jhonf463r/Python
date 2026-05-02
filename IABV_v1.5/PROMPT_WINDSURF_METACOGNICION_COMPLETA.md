# Prompt Completo Para Windsurf — Auditoría de Metacognición Profunda IABV v1.5

## Contexto Para Windsurf

Eres Windsurf ejecutando sobre la máquina real del usuario (Windows, PowerShell).
Tu objetivo es usar TODAS las capas de metacognición de IABV v1.5 para generar
un reporte exhaustivo como **fuente de verdad** del programa en su entorno real.

IABV se describe a sí mismo como un "algoritmo universal adaptativo que se conoce
a sí mismo" (Resumen Ejecutivo, basado en compresión de Kolmogorov y MDL). Tu
trabajo es verificar si esto es cierto: ¿realmente se conoce a sí mismo? ¿detecta
sus propios problemas? ¿corrige lo que detecta?

---

## PASO 0: Setup Previo

```powershell
cd C:\Python\IABV_v1.5
git fetch origin
git checkout devin/1777690043-metacognition-blind-spots
git pull origin devin/1777690043-metacognition-blind-spots
$env:PYTHONPATH = "C:\Python\IABV_v1.5\src"
```

> **IMPORTANTE**: Usa la rama `devin/1777690043-metacognition-blind-spots` (PR #304),
> NO la rama de PR #303 (`devin/1777687784-fix-startup-freeze`) — PR #303 empeoró
> el freeze con processEvents(). PR #304 tiene los fixes correctos (Fix 12, 13a-c, 14).

---

## PASO 1: Arrancar IABV y Cronometrar el Startup

```powershell
# Medir tiempo total de arranque
$start = Get-Date
& python -m iabv_v15 2>&1 | Tee-Object -FilePath "$HOME\iabv_startup_log.txt"
```

### Qué observar durante el arranque:
1. **Progreso del splash** — ¿llega de 10% a 100% de forma incremental?
2. **populate_ui_start → populate_ui_done** — ¿cuánto tarda? (antes era 30s+)
3. **shell_loader_ready** — ¿llega el real o usa el fallback?
4. **Proceso Responding** — ¿Windows marca "Not Responding" en algún momento?

```powershell
# En otra terminal, mientras IABV arranca:
# Monitorear estado del proceso cada 10s durante 3 minutos
for ($i=0; $i -lt 18; $i++) {
    $ts = Get-Date -Format "HH:mm:ss"
    $proc = Get-Process python -ErrorAction SilentlyContinue |
        Where-Object { $_.WorkingSet -gt 50MB } |
        Select-Object Id, ProcessName, @{N='RSS_MB';E={[math]::Round($_.WorkingSet/1MB)}}, CPU, Responding
    Write-Host "[$ts] $($proc | Format-Table -AutoSize | Out-String)"
    Start-Sleep 10
}
```

### Resultados esperados post-fix:
- `populate_ui_done` debería llegar (antes no llegaba)
- Duration de populate_ui debería ser < 5s (antes era 30s+)
- El proceso debería mantener Responding=True
- El splash debería mostrar progreso incremental 70%→80%→90%→100%

---

## PASO 2: Leer los Logs de StartupTimeline

```powershell
# Después de que IABV arranque, buscar las fases del timeline
Select-String -Path C:\Python\IABV_v1.5\data\logs\iabv_v15.log `
  -Pattern "startup_timeline" | Select-Object -Last 30
```

### Verificar estos hitos críticos:

| Hito | Esperado | Si falta = problema |
|------|----------|---------------------|
| `bootstrap_init_done` | < 5000ms | Init muy lento |
| `run_start` | inmediato después de init | — |
| `splash_visible` | < 20000ms | QML lento |
| `wire_services_done` | < 35000ms | Servicios pesados |
| `populate_ui_start` | después de wire | — |
| `populate_ui_done` | < 5000ms después de start | **FREEZE si falta** |
| `main_window_shown` | < 40000ms total | — |
| `shell_loader_ready` (NO fallback) | < 60000ms | QML no terminó |
| `deferred_post_window_setup_done` | < 10000ms | Tool probes lentos |

```powershell
# Calcular duración de populate_ui
$log = Get-Content C:\Python\IABV_v1.5\data\logs\iabv_v15.log
$start_line = $log | Select-String "populate_ui_start" | Select-Object -Last 1
$done_line = $log | Select-String "populate_ui_done" | Select-Object -Last 1
Write-Host "START: $start_line"
Write-Host "DONE:  $done_line"
```

---

## PASO 3: Ejecutar OSES — Auto-Examinación Operativa

```python
# Ejecutar desde Python interactivo con IABV corriendo:
import sys; sys.path.insert(0, r'C:\Python\IABV_v1.5\src')
from iabv_v15.bootstrap import AppBootstrap
import json

# Si IABV ya está corriendo, conectar al bootstrap existente
# Si no, crear uno para lectura:
bootstrap = AppBootstrap(r'C:\Python\IABV_v1.5')

# 3a. Obtener review completo de OSES
oses = bootstrap.operational_self_examination_service
review = oses.build_review()

print("=" * 60)
print("OSES REVIEW — FINDINGS")
print("=" * 60)
for f in review.findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  Summary: {f.summary}")
    print(f"  Recommendation: {f.recommendation}")
    if f.metadata:
        print(f"  Metadata: {json.dumps(f.metadata, default=str, indent=2)[:500]}")
    print()

# 3b. Startup health findings específicos
print("=" * 60)
print("STARTUP HEALTH FINDINGS")
print("=" * 60)
startup_findings = oses._startup_health_findings()
for f in startup_findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  {f.summary}")
    print()

# 3c. Runtime performance findings
print("=" * 60)
print("RUNTIME PERFORMANCE FINDINGS")
print("=" * 60)
perf_findings = oses._runtime_performance_findings()
for f in perf_findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  {f.summary}")
    print()

# 3d. Boot profile findings (historial)
print("=" * 60)
print("BOOT PROFILE FINDINGS (HISTORIAL)")
print("=" * 60)
boot_findings = oses._boot_profile_findings()
for f in boot_findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  {f.summary}")
    print()

# 3e. Log anomaly findings
print("=" * 60)
print("LOG ANOMALY FINDINGS")
print("=" * 60)
log_findings = oses._runtime_log_findings()
for f in log_findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  {f.summary}")
    print()

# 3f. Loop closure — ¿están bien cableados los nervios?
print("=" * 60)
print("LOOP CLOSURE FINDINGS (CABLEADO)")
print("=" * 60)
loop_findings = oses._loop_closure_findings(
    findings_so_far=review.findings,
    experiment_runs=oses._recent_experiment_runs(),
)
for f in loop_findings:
    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
    print(f"[{sev}] {f.category}: {f.title}")
    print(f"  {f.summary}")
    if f.metadata:
        print(f"  Metadata: {json.dumps(f.metadata, default=str)[:300]}")
    print()

# 3g. Metacognitive accuracy — ¿cuántos falsos positivos/negativos?
print("=" * 60)
print("METACOGNITIVE ACCURACY")
print("=" * 60)
try:
    accuracy_findings = oses._metacognitive_accuracy_findings(review.findings)
    for f in accuracy_findings:
        sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
        print(f"[{sev}] {f.category}: {f.title}")
        print(f"  {f.summary}")
        print()
except Exception as e:
    print(f"Error: {e}")
```

---

## PASO 4: Ejecutar CommonSenseEngine — Inferencia Causal

```python
# 4a. Observar hechos del entorno actual
# NOTA: La función correcta es extract_facts() (no observe_facts).
# extract_facts() recibe scans opcionales y devuelve un set[str] de hechos.
# run_common_sense_reasoning() ejecuta el pipeline completo (observe+detect+infer+act).
from iabv_v15.services.common_sense_engine import (
    forward_chain, extract_facts, run_common_sense_reasoning, INFERENCE_RULES
)

print("=" * 60)
print("COMMON SENSE ENGINE — HECHOS OBSERVADOS")
print("=" * 60)
facts = extract_facts()  # sin args = escanea GPU, procesos, etc.
for fact in sorted(facts):
    print(f"  HECHO: {fact}")

# 4b. Ejecutar forward chaining
print("\n" + "=" * 60)
print("COMMON SENSE ENGINE — INFERENCIA CAUSAL")
print("=" * 60)
result = forward_chain(facts)
print(f"Hechos totales: {len(result['all_facts'])}")
print(f"Hechos nuevos inferidos: {len(result['all_facts']) - len(facts)}")
print(f"Reglas disparadas: {len(result['fired_rules'])}")
for rule in result['fired_rules']:
    print(f"  REGLA: {rule['id']} → {rule['conclusion']}")
    print(f"    Severidad: {rule.get('severity', 'N/A')}")
    print(f"    Acción: {rule.get('action', 'N/A')}")
    print()

# 4b-extra. Pipeline completo v2 (observe → detect anomalies → infer → learn → act)
print("\n" + "=" * 60)
print("COMMON SENSE ENGINE — PIPELINE COMPLETO v2")
print("=" * 60)
full_result = run_common_sense_reasoning(execute=False, dry_run=True)
print(f"Anomalías detectadas: {full_result.get('anomaly_count', 0)}")
for anomaly in full_result.get('anomalies', []):
    print(f"  ANOMALÍA: {anomaly.get('category', '?')} — {anomaly.get('description', '?')}")
print(f"History consultations: {full_result.get('history_consultations', 0)}")
print(f"Algorithm recommendation: {full_result.get('algorithm_recommendation', {})}")

# 4c. Listar TODAS las reglas y verificar cobertura
print("=" * 60)
print("COBERTURA DE REGLAS")
print("=" * 60)
for i, rule in enumerate(INFERENCE_RULES):
    fired = rule['id'] in [r['id'] for r in result['fired_rules']]
    status = "DISPARADA" if fired else "SILENTE"
    print(f"  [{status}] {rule['id']}: {rule.get('description', 'sin descripción')[:80]}")

# 4d. VERIFICAR: ¿Hay reglas para startup/freeze/memory?
startup_rules = [r for r in INFERENCE_RULES
                 if any(kw in r.get('id', '').lower() + r.get('description', '').lower()
                        for kw in ('startup', 'freeze', 'populate', 'memory', 'responding'))]
print(f"\nReglas relacionadas con startup/freeze: {len(startup_rules)}")
for r in startup_rules:
    print(f"  {r['id']}: {r.get('description', '')[:80]}")
if not startup_rules:
    print("  ⚠️ PUNTO CIEGO: No hay reglas causales para startup freeze")
```

---

## PASO 5: Verificar EnvironmentSelfModel

```python
# 5a. Estado actual del entorno
env_service = bootstrap.environment_self_awareness_service
model = env_service.current_model()

print("=" * 60)
print("ENVIRONMENT SELF MODEL")
print("=" * 60)
print(f"Environment ID: {model.environment_id}")
print(f"Scan Status: {model.scan_status}")
print(f"Known Environment: {model.known_environment}")
print(f"Last Scan: {model.last_scan}")
print(f"Unresolved Fields: {model.unresolved_fields}")

# Hardware
hw = model.hardware_profile
print(f"\nHardware:")
print(f"  CPU: {hw.get('cpu_model', 'unknown')}")
print(f"  RAM Total: {hw.get('ram_total_bytes', 0) / 1024**3:.1f} GB")
print(f"  GPU Count: {hw.get('gpu_count', 0)}")
for gpu in hw.get('gpus', []):
    print(f"  GPU: {gpu.get('name', 'unknown')} - VRAM: {gpu.get('vram_mb', 0)} MB")

# Tools
print(f"\nAvailable Tools ({len(model.available_tools)}):")
for t in model.available_tools:
    print(f"  ✓ {t.get('tool_id', 'unknown')} [{t.get('launch_mode', '')}]")
print(f"\nMissing Tools ({len(model.missing_tools)}):")
for t in model.missing_tools:
    print(f"  ✗ {t.get('tool_id', 'unknown')} [{t.get('launch_mode', '')}]")

# Risk Signals
print(f"\nRisk Signals ({len(model.risk_signals)}):")
for rs in model.risk_signals:
    sev = rs.severity.value if hasattr(rs.severity, 'value') else str(rs.severity)
    print(f"  [{sev}] {rs.category}: {rs.description}")

# Notifications
print(f"\nNotifications ({len(model.notifications)}):")
for n in model.notifications:
    print(f"  {n}")
```

---

## PASO 6: Verificar WorldModel

```python
# 6a. Snapshot actual del mundo
world_service = bootstrap.world_model_service
snapshot = world_service.current_model()

print("=" * 60)
print("WORLD MODEL SNAPSHOT")
print("=" * 60)
print(f"Health Status: {snapshot.health_status}")
print(f"Scan Count: {snapshot.metadata.get('scan_count', 0)}")

# Ventanas
print(f"\nWindows ({len(snapshot.windows)}):")
for w in snapshot.windows[:10]:
    print(f"  {w.get('title', 'unknown')[:60]} - focused={w.get('focused', False)}")

# Herramientas
print(f"\nTools ({len(snapshot.tools)}):")
for t in snapshot.tools:
    print(f"  {t.get('name', 'unknown')}: {t.get('status', 'unknown')}")

# Red
print(f"\nNetwork: {json.dumps(snapshot.network, default=str)[:200]}")

# Procesos
print(f"\nBlocking Issues: {snapshot.blocking_issues}")
```

---

## PASO 7: Verificar PortableContext

```python
# 7a. Paquete portable actual
portable = bootstrap.portable_context_service.build_package()

print("=" * 60)
print("PORTABLE CONTEXT PACKAGE")
print("=" * 60)
# Imprimir secciones disponibles
for key in sorted(portable.__dict__.keys()):
    val = getattr(portable, key, None)
    if val:
        vtype = type(val).__name__
        vlen = len(val) if hasattr(val, '__len__') else 'N/A'
        print(f"  Section: {key} [{vtype}, len={vlen}]")

# Cloud reasoning section
if hasattr(portable, 'cloud_reasoning') and portable.cloud_reasoning:
    cr = portable.cloud_reasoning
    print(f"\nCloud Reasoning:")
    print(f"  Health Score: {cr.get('health_score', 'N/A')}")
    print(f"  Trends: {cr.get('trends', {})}")
    print(f"  Recommendations: {cr.get('recommendations', [])}")

# Learned patterns
if hasattr(portable, 'learned_patterns') and portable.learned_patterns:
    print(f"\nLearned Patterns ({len(portable.learned_patterns)}):")
    for p in portable.learned_patterns[:5]:
        print(f"  {p}")
```

---

## PASO 8: Verificar DecisionAuditTrail

```python
# 8a. Resumen de decisiones cloud
audit = bootstrap.decision_audit_trail
summary = audit.self_examination_summary()

print("=" * 60)
print("DECISION AUDIT TRAIL")
print("=" * 60)
print(json.dumps(summary, default=str, indent=2)[:2000])

# 8b. Últimas decisiones
recent = audit.recent_decisions(limit=10)
print(f"\nÚltimas {len(recent)} decisiones:")
for d in recent:
    print(f"  [{d.get('provider', '?')}] latency={d.get('latency_ms', '?')}ms "
          f"confidence={d.get('confidence', '?')} result={d.get('result', '?')}")
```

---

## PASO 9: Verificar AdaptiveWeightLayer

```python
# 9a. Pesos actuales
awl = bootstrap.adaptive_weight_layer

print("=" * 60)
print("ADAPTIVE WEIGHT LAYER")
print("=" * 60)
weights = awl.current_weights()
for key, value in sorted(weights.items()):
    print(f"  {key}: {value:.4f}")

# 9b. Historial de ajustes recientes
history = awl.adjustment_history(limit=10)
print(f"\nÚltimos ajustes:")
for h in history:
    print(f"  {h}")
```

---

## PASO 10: Verificar ExperimentLab

```python
# 10a. Experimentos recientes
lab = bootstrap.experiment_lab

print("=" * 60)
print("EXPERIMENT LAB")
print("=" * 60)
experiments = lab.list_experiments(limit=10)
print(f"Total experimentos: {len(experiments)}")
for exp in experiments:
    print(f"  [{exp.get('domain', '?')}] {exp.get('description', '?')[:60]}")
    print(f"    Winner: {exp.get('winner', '?')} | Runs: {exp.get('run_count', '?')}")
```

---

## PASO 11: Verificar GPU Metacognition

```python
from iabv_v15.services.gpu_metacognition import startup_gpu_health_check

print("=" * 60)
print("GPU METACOGNITION")
print("=" * 60)
report = startup_gpu_health_check()
print(json.dumps(report, default=str, indent=2))
```

---

## PASO 12: Verificar AutoCorrectionEngine

```python
from iabv_v15.services.auto_correction_engine import execute_corrections

print("=" * 60)
print("AUTO CORRECTION ENGINE — ACCIONES DISPONIBLES")
print("=" * 60)
# Listar las categorías que AutoCorrect puede manejar
# (las que están en _CATEGORY_TO_ACTION en OSES)
known_actions = {
    'background_provider_underperformance': 'degrade_provider_priority',
    'background_error_stagnation': 'block_failing_route',
    'temporal_latency_anomaly': 'flag_slow_provider',
    'cross_correlation_failure': 'reclassify_intent',
    'trend_degradation': 'trigger_diagnostic_scan',
}
print("Categorías con acción correctiva:")
for cat, action in known_actions.items():
    print(f"  {cat} → {action}")

# VERIFICAR: ¿Hay acciones para startup?
startup_actions = {k: v for k, v in known_actions.items()
                   if 'startup' in k.lower() or 'populate' in k.lower() or 'freeze' in k.lower()}
print(f"\nAcciones para startup: {len(startup_actions)}")
if not startup_actions:
    print("  ⚠️ PUNTO CIEGO: No hay acciones correctivas para problemas de startup")
```

---

## PASO 13: Prueba de Contradicciones Entre Capas

```python
print("=" * 60)
print("PRUEBA DE CONTRADICCIONES ENTRE CAPAS")
print("=" * 60)

# 13a. WorldModel vs StartupHealth
world_health = snapshot.health_status
startup_critical = any(
    f.severity.value == 'CRITICAL' if hasattr(f.severity, 'value') else str(f.severity) == 'CRITICAL'
    for f in startup_findings
)
if world_health == 'healthy' and startup_critical:
    print("❌ CONTRADICCIÓN: WorldModel='healthy' pero startup tiene findings CRITICAL")
else:
    print(f"✓ WorldModel='{world_health}', startup CRITICAL={startup_critical}")

# 13b. EnvironmentSelfModel vs RSS real
import psutil
current_rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
env_rss = model.hardware_profile.get('process_rss_mb', 0)
print(f"\n✓ RSS actual: {current_rss_mb:.0f} MB")
print(f"  RSS en EnvironmentSelfModel: {env_rss:.0f} MB")
if abs(current_rss_mb - env_rss) > 100:
    print("  ⚠️ DISCREPANCIA: RSS en modelo no refleja RSS real")

# 13c. OSES findings vs CommonSense rules
oses_categories = set(f.category for f in review.findings)
cs_conclusions = set(r['conclusion'] for r in result.get('fired_rules', []))
print(f"\nOSES categorías detectadas: {len(oses_categories)}")
print(f"CommonSense conclusiones: {len(cs_conclusions)}")
overlap = oses_categories & cs_conclusions
print(f"Overlap (ambos detectan): {len(overlap)}")
if overlap:
    for o in overlap:
        print(f"  ✓ {o}")
print(f"Solo OSES: {oses_categories - cs_conclusions}")
print(f"Solo CommonSense: {cs_conclusions - oses_categories}")

# 13d. PortableContext vs estado real
if hasattr(portable, 'health_score'):
    print(f"\nPortableContext health_score: {portable.health_score}")
if hasattr(portable, 'last_boot_ms'):
    print(f"PortableContext last_boot_ms: {portable.last_boot_ms}")
```

---

## PASO 14: Tests Automatizados

```powershell
# Correr la batería completa de tests
$env:PYTHONPATH = 'C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q 2>&1 |
    Tee-Object -FilePath "$HOME\iabv_test_results.txt"
```

### Verificar que los tests de metacognición pasen:
```powershell
# Tests específicos de las capas que tocamos
& python -m pytest tests/test_startup_health_cable.py tests/test_provider_health_router.py `
    tests/test_environment_self_awareness_service.py tests/test_bootstrap_defer_tool_probe.py `
    tests/test_tool_registry.py -v 2>&1
```

---

## PASO 15: Generar Reporte Final

### El reporte debe incluir:

1. **Timeline de startup real** — todos los hitos con timestamps
2. **Duración de populate_ui** — ¿mejoró vs los 30s+ anteriores?
3. **Proceso Responding** — ¿se mantuvo True durante todo el arranque?
4. **RSS durante startup** — ¿cuánto creció? ¿en qué fase?
5. **OSES findings** — lista completa con severidad
6. **CommonSense rules** — cuáles se dispararon, cuáles no y por qué
7. **Puntos ciegos encontrados** — qué debería detectar pero no detecta
8. **Contradicciones entre capas** — dónde una capa dice algo diferente a otra
9. **Nervios cortados vs restaurados** — comparando con el AUDIT_METACOGNICION_PROFUNDO.md
10. **Estado de Fix 12-14** — ¿funcionaron?
11. **Tests pasados/fallados** — resultado de la batería completa
12. **Recomendaciones** — qué nervios faltan por restaurar, ordenados por impacto

### Formato del reporte:

```markdown
# Reporte de Metacognición — Fuente de Verdad — [FECHA]

## Resumen Ejecutivo
[1 párrafo: ¿IABV se conoce a sí mismo? ¿Qué tan bien?]

## 1. Timeline de Startup
[Tabla con todos los hitos y timestamps]

## 2. Resultados de Cada Capa
### 2.1 OSES
[Findings con severidad]
### 2.2 CommonSenseEngine
[Hechos, reglas disparadas, cobertura]
### 2.3 EnvironmentSelfModel
[Estado del entorno]
### 2.4 WorldModel
[Snapshot del mundo]
### 2.5 PortableContext
[Contexto exportado]
### 2.6 DecisionAuditTrail
[Decisiones cloud]
### 2.7 AdaptiveWeightLayer
[Pesos y ajustes]
### 2.8 ExperimentLab
[Experimentos]
### 2.9 GPU Metacognition
[Salud GPU]
### 2.10 AutoCorrectionEngine
[Acciones disponibles vs necesarias]

## 3. Contradicciones Detectadas
[Lista de contradicciones entre capas]

## 4. Puntos Ciegos
[Tabla: Evento | ¿Detecta? | ¿Deduce? | ¿Corrige? | Veredicto]

## 5. Nervios Restaurados (Fixes 12-14)
[Estado de cada fix]

## 6. Nervios Pendientes
[Qué falta por restaurar, con prioridad]

## 7. Tests
[Resultados de la batería]

## 8. Veredicto Final
[¿Es IABV realmente un algoritmo universal adaptativo que se conoce a sí mismo?]
[¿Cumple los axiomas A1-A4 del Resumen Ejecutivo?]
[¿Dónde está su umbral Nc de emergencia metacognitiva?]
```

---

## Referencia Rápida: Archivos Clave

| Archivo | Qué contiene | Líneas |
|---------|-------------|--------|
| `src/iabv_v15/bootstrap.py` | Wiring del sistema, startup | ~3200 |
| `src/iabv_v15/services/evolution/operational_self_examination_service.py` | OSES, findings, auto-correct | ~6300 |
| `src/iabv_v15/services/common_sense_engine.py` | Reglas causales, forward chain | ~2100 |
| `src/iabv_v15/services/evolution/world_model_service.py` | WorldModel, escaneo periódico | ~1400 |
| `src/iabv_v15/services/evolution/environment_self_awareness_service.py` | EnvironmentSelfModel | ~900 |
| `src/iabv_v15/services/evolution/portable_context_service.py` | Contexto portable | ~600 |
| `src/iabv_v15/services/tools/tool_adapters.py` | Multi-source detection, cache | ~2600 |
| `src/iabv_v15/services/tools/tool_registry.py` | Registry, availability cache | ~630 |
| `src/iabv_v15/services/providers/provider_health_router.py` | Health polling | ~200 |
| `src/iabv_v15/services/auto_correction_engine.py` | Correcciones automáticas | ~2200 |
| `src/iabv_v15/services/gpu_metacognition.py` | Salud GPU | ~440 |
| `src/iabv_v15/ui/viewmodels/dashboard_viewmodel.py` | Dashboard VM (fix defer) | — |
| `IABV_v1.5/AUDIT_METACOGNICION_PROFUNDO.md` | Auditoría previa de Devin | 662 |
| `Resumen ejecutivo (3).pdf` | Marco teórico Kolmogorov/MDL | — |

---

## Nota Importante Sobre el Marco Teórico

El Resumen Ejecutivo propone que el razonamiento emergente surge de la compresión
(Kolmogorov, MDL, energía libre). Los axiomas A1-A4 dicen:

- **A1**: El sistema optimiza predicción/compresión
- **A2**: El espacio es composicional (subestructuras reutilizables)
- **A3**: Exploración efectiva del espacio de soluciones
- **A4**: Compresión ↔ Generalización (soluciones más comprimidas generalizan mejor)

Tu reporte debe evaluar si IABV implementa estos axiomas en su metacognición:
- ¿Comprime su experiencia de startup correctamente? (A1)
- ¿Reutiliza subestructuras de detección? (A2, Lema 3)
- ¿Explora soluciones alternativas cuando algo falla? (A3)
- ¿Las soluciones comprimidas generalizan a nuevos problemas? (A4)

---

*Prompt generado por Devin para que Windsurf ejecute una auditoría completa de
metacognición sobre IABV v1.5 en el entorno real del usuario (Windows).*
