# Centro de Control Evolutivo — Informe Técnico Implementable

**Proyecto:** IABV v1.5  
**Autor:** Devin (arquitecto senior, sesión de observabilidad y auditoría evolutiva)  
**Fecha:** 2026-05-14  
**Pre-scan metacognitivo:** Ejecutado (DecisionAuditTrail, OSES, PCS, AVCS, ExperimentLab)

---

## 1. Diagnóstico Arquitectónico

### 1.1 Topología del cerebro existente

El sistema IABV v1.5 implementa un pipeline cognitivo lineal con retroalimentación:

```
Percepción → Contexto → Decisión → Ejecución → Aprendizaje → Metacognición
```

**Pipeline detallado:**

```
InferenceRequest
  → IntentUnderstandingService (clasifica intent)
  → TaskContextAssembler (ensambla contexto + world model + portable context)
  → PerceptionSnapshot (entrada unificada)
  → AdaptiveTaskOrchestrator (orquesta decisión)
    → AutonomyGovernancePolicy (gate: ¿es viable?)
    → LocalRoleRouter / SynapticRouter (rutea a proveedor)
    → CloudReasoningPlannerService (si es cloud)
  → Ejecución (InferenceService / ToolOperationalExecutor)
  → TaskOutcomeRecorder (cierra loop → ExperimentLab)
  → AdaptiveWeightLayer (ajusta pesos futuros)
```

**Metacognición en background:**

```
OperationalSelfExaminationService (OSES, 7800 líneas)
  ├─ _background_decision_review_findings() → lee DecisionAuditTrail
  ├─ _temporal_awareness_findings() → detecta anomalías de latencia
  ├─ _deep_analysis_queue_findings() → EMA drift, correlaciones
  ├─ _startup_health_findings() → degradación de boot
  └─ _cloud_reasoning_findings() → salud de proveedores cloud

AutonomousValidationCycleService (1963 líneas)
  ├─ _monitor_loop() → revisa candidatos sandbox periódicamente
  ├─ _maybe_promote() → promueve candidatos con evidencia
  └─ _auto_research_cycle() → genera sandbox experiments desde backlog
```

### 1.2 Capa de persistencia

| Fuente | Formato | Ubicación |
|--------|---------|-----------|
| DecisionAuditTrail | JSONL append-only | `data/evolution/decision_audit/decisions.jsonl` |
| SelfExaminationSnapshot | JSON + historia | `data/evolution/self_examination/latest.json` + `history/` |
| PortableContextPackage | JSON + historia | `data/evolution/portable_context/latest.json` + `history/` |
| WorldModelSnapshot | JSON | `data/evolution/world_model/latest.json` |
| ExperimentRuns | SQLite | `data/evolution/experiment_runs` (via ExperimentLabRepository) |
| AdaptiveSessions | SQLite | `data/evolution/adaptive_sessions` |
| ControlMasterState | SQLite | via ControlMasterRepository |
| BootProfile | JSON history | via BootProfileStore |
| CodeAuditTrail | TBD | via CodeAuditTrail service |

### 1.3 ViewModels/Pages existentes (UI)

| Page | ViewModel | Líneas | Función |
|------|-----------|--------|---------|
| DashboardPage | DashboardViewModel | 182 | Resumen básico: episodios, conocimiento, runs |
| ControlCenterPage | ControlCenterViewModel | 8116 | Chat, roles, orquestación, evolución overview, autonomía |
| EvolutionCenterPage | EvolutionCenterViewModel | 1018 | Dossiers, incidentes, tool cards, comparaciones IA, OSES |
| CentroVivoPage | CentroVivoViewModel | 422 | Cola orquestador, IAs, heurística, métricas, hallazgos |
| CaptureStudioPage | CaptureStudioViewModel | - | Enseñanza, captura visual |
| KnowledgeBasePage | KnowledgeBaseViewModel | - | Consulta de conocimiento |
| ProviderSettingsPage | ProviderSettingsViewModel | - | Stack local (Ollama, LM Studio) |
| RunHistoryPage | RunHistoryViewModel | - | Historial de ejecuciones |

### 1.4 Pre-scan metacognitivo — Estado encontrado

**DecisionAuditTrail.self_examination_summary():**
- Trail activo con modelo de datos sólido: `DecisionRecord` con 17 campos (decision_id, phase, provider_id, model_used, outcome, latency_ms, confidence, steps_total/completed/failed, fallback_chain, error_detail, quality_signal, metadata)
- `ProviderTrend` con análisis first-half vs second-half para detectar mejora/degradación
- Método `self_examination_summary()` genera health_score, overall_trend, recommendations

**OperationalSelfExaminationService.current_review():**
- Review más reciente: status=`partial`, sin degradaciones fuertes
- Hallazgos recurrentes: `light_checks_warning` (×10), `need_codex_fix` (×2)
- 1 mejora validada: `ollama por language_understanding` (score 0.93, adaptativo 1.27)
- Feedback de ajustes: `no_evidence` en la mayoría → necesitan más corridas
- UNRESOLVED: `autonomous_validation_cycle`

**PortableContextService.build_package():**
- Paquete generado con secciones: project_state, architecture, validated_improvements, recommendations
- Objetivo activo: "sabes por que no avanza el trabajo en vivo ?"
- Arquitectura marcada como `wired` para todos los componentes clave
- Bloqueos activos: 3

**AutonomousValidationCycleService:**
- Estado: `bootstrapping` (esperando primer tick)
- `UNRESOLVED` en último snapshot

**ExperimentLab (domain=CLOUD_REASONING):**
- Laboratorio activo con scoring engine, benchmark registry, strategy selector
- StrategySelector usa `adaptive_threshold` calculado dinámicamente
- AdaptiveWeightLayer almacena metacognitive adjustments (clamped ±0.15)

---

## 2. Mapa Visión ↔ Componentes Reales

| Concepto del Centro de Control Evolutivo | Componente Real | Estado | Brecha |
|------------------------------------------|-----------------|--------|--------|
| **Estado global del organismo** | `WorldModelService.current_model()` + `EnvironmentSelfModel` | ✅ Existe | Falta agregación unificada en un solo snapshot |
| **Grafo de dependencias** | `PortableContextService` sección `architecture` | ⚠️ Parcial | Solo lista lineal, no grafo visual |
| **Línea de tiempo evolutiva** | `DecisionAuditTrail.load_recent()` + `BootProfileStore` | ⚠️ Parcial | No hay timeline visual unificado |
| **Experimentos** | `ExperimentLab` + `CentroVivoViewModel.experimentMetrics` | ✅ Existe | Disperso entre páginas |
| **Métricas y anomalías** | `OSES` findings + temporal_awareness | ✅ Existe | No consolidado en un panel |
| **Linaje/auditoría de decisiones** | `DecisionAuditTrail` + `CodeAuditTrail` | ✅ Existe | Falta trazabilidad causal end-to-end |
| **Aprendizaje persistente** | `ExperimentLab` + `StrategySelector` + `AdaptiveWeightLayer` | ✅ Existe | No visualizado como progresión |
| **Alertas** | `EvolutionCenterVM.proactiveDashboard` + incidents | ✅ Existe | Fragmentado |
| **Resumen ejecutivo** | `ControlMasterService.current_state()` + `ControlMasterDigestBuilder` | ✅ Existe | No integra todo |
| **Eventos espontáneos** | `HiddenIncidentDetector` + `FreezeIncidentReporter` | ✅ Existe | Sin timeline causal |
| **Errores** | OSES recurring_issues + RunRecord(FAILED) | ✅ Existe | Sin correlación visual |
| **Cambios de configuración** | `AdaptiveWeightLayer.metacognitive_adjustments` | ✅ Existe | Sin historial visual |
| **Zoom jerárquico** | No existe | ❌ Falta | Necesita aggregator con drill-down |

---

## 3. Brechas Concretas

### B1 — Sin snapshot unificado del organismo (BRECHA PRINCIPAL)
**Severidad:** Alta  
**Detalle:** Cada servicio produce su propio snapshot aislado. No hay un único punto donde converjan:
- WorldModel + OSES findings + DecisionAudit trends + ExperimentLab metrics + ControlMaster state + PortableContext
- El CentroVivoViewModel es lo más cercano, pero solo lee 7 fuentes y sin estructura jerárquica

### B2 — Sin flujo causal trazable
**Severidad:** Alta  
**Detalle:** No se puede seguir: evento → percepción → decisión → ejecución → outcome → aprendizaje → ajuste. Cada paso está en un servicio distinto sin correlation_id compartido.

### B3 — Sin grafo de dependencias visual
**Severidad:** Media  
**Detalle:** La sección `architecture` del PortableContext lista componentes linealmente. No hay modelo de relaciones entre módulos para visualizar como grafo.

### B4 — Sin timeline evolutiva unificada
**Severidad:** Media  
**Detalle:** Los eventos históricos están en JSONL (decisions), SQLite (experiment_runs), JSON (self_examination history). No hay un stream unificado temporal.

### B5 — Sin zoom jerárquico
**Severidad:** Media  
**Detalle:** No existe la capacidad de hacer drill-down: sistema → módulo → algoritmo → variable/peso → evento → aprendizaje.

### B6 — Sin política de compactación de auditoría
**Severidad:** Media  
**Detalle:** `decisions.jsonl` es append-only sin límite. `self_examination/history/` y `portable_context/history/` acumulan snapshots. Sin compactación, crecen indefinidamente.

### B7 — Sin evento unificado para observabilidad
**Severidad:** Baja  
**Detalle:** Cada servicio usa su propia estructura de evento. No hay un `EvolutionEvent` tipado que permita correlacionar cross-service.

---

## 4. Propuesta UI/Observabilidad por Capas

### Principio de diseño: "Organismo Digital Vivo"

No un dashboard genérico con gráficas estáticas. Un organismo vivo donde:
- Se ve el flujo de "sangre" (eventos) circulando
- Los órganos (módulos) pulsan con actividad
- Las anomalías se destacan como zonas inflamadas
- El zoom revela capas más profundas

### 4.1 Panel de Estado Global (Capa 0 — "Signos Vitales")

```
┌──────────────────────────────────────────────────────┐
│  SIGNOS VITALES DEL ORGANISMO                        │
│                                                       │
│  ❤️ Health Score: 0.87    🧠 Presión cognitiva: NORMAL │
│  🌐 Red: OK (23ms)       📦 Contexto: FRESCO (4min)   │
│  🔬 Experimentos: 3 activos  ⚠️ Anomalías: 1         │
│  📊 Decisiones: 40 (92% éxito)  🔄 Último aprendizaje: 12min │
│                                                       │
│  [Estado compuesto de: WorldModel + OSES + DAT + PCS] │
└──────────────────────────────────────────────────────┘
```

**Fuentes:** `WorldModelService`, `OSES.current_review()`, `DecisionAuditTrail.self_examination_summary()`, `PortableContextService.current_package()`

### 4.2 Panel de Grafo de Dependencias (Capa 1 — "Anatomía")

```
┌────────────────────────────────────────────┐
│  ANATOMÍA DEL ORGANISMO                    │
│                                            │
│  [Percepción] → [Contexto] → [Decisión]   │
│       ↑              ↑            ↓        │
│  [WorldModel]   [Portable]   [Governance]  │
│                      ↑            ↓        │
│  [OSES] ←─────── [Lab] ←──── [Outcome]    │
│                                            │
│  Nodos coloreados por actividad/salud      │
│  Click en nodo → zoom al módulo            │
└────────────────────────────────────────────┘
```

**Implementación:** Modelo de datos estático (`ARCHITECTURE_GRAPH`) con estado dinámico inyectado desde snapshots.

### 4.3 Panel de Línea de Tiempo Evolutiva (Capa 2 — "Historia")

```
┌──────────────────────────────────────────────────────┐
│  LÍNEA DE TIEMPO EVOLUTIVA                           │
│                                                       │
│  ──●──●──●──▲──●──●──■──●──●──▲──●──●──●──          │
│    │     │  │     │  │        │                       │
│    │     │  │     │  │        └ Anomalía latencia     │
│    │     │  │     │  └ Ajuste peso: ollama +0.12      │
│    │     │  │     └ Decisión: groq → success          │
│    │     │  └ Promoción: candidato sandbox            │
│    │     └ OSES review: partial                       │
│    └ Boot: 4200ms (degradado)                        │
│                                                       │
│  [Filtro: decisiones | aprendizaje | anomalías | all] │
└──────────────────────────────────────────────────────┘
```

**Fuentes:** `DecisionAuditTrail` entries + `OSES` history + `PortableContext` history + `ExperimentRuns` + `BootProfileStore`.

### 4.4 Panel de Experimentos (Capa 3 — "Laboratorio")

Ya existe en `CentroVivoViewModel.experimentMetrics` y `EvolutionCenterViewModel.iaComparisons`. Se consolida:

- Experimentos activos vs completados
- Ganador actual por dominio
- Ventaja % del ganador
- Número de muestras
- Progresión temporal de scores

### 4.5 Panel de Métricas y Anomalías (Capa 4 — "Diagnóstico")

**Fuentes existentes reutilizables:**
- `OSES.findings` → hallazgos activos
- `OSES.recurring_issues` → patrones repetidos
- `OSES._temporal_awareness_findings()` → anomalías de latencia
- `OSES._deep_analysis_queue_findings()` → EMA drift, correlaciones
- `DecisionAuditTrail.analyze_provider_trends()` → tendencias por proveedor

### 4.6 Panel de Linaje/Auditoría de Decisiones (Capa 5 — "Forense")

```
Decisión #20260418T164321
├─ Fase: plan_generation
├─ Proveedor: groq
├─ Modelo: llama-3.3-70b
├─ Confianza: 0.85
├─ Latencia: 2340ms
├─ Outcome: success
├─ Steps: 3/3 completados
├─ Aprendizaje generado:
│   └─ ExperimentRun #xyz → score 0.93
│       └─ Recommendation: mantener groq para este dominio
└─ Impacto en AdaptiveWeightLayer:
    └─ groq|language_understanding: +0.04
```

### 4.7 Panel de Aprendizaje Persistente (Capa 6 — "Memoria")

**Fuentes:** `PortableContextService` secciones `validated_improvements` + `adaptive_learning_summary` + `learned_patterns`.

### 4.8 Panel de Alertas (Capa 7 — "Sistema Inmune")

Consolidación de:
- `EvolutionCenterVM.proactiveDashboard` (necesidades del humano)
- `HiddenIncidentDetector` (incidentes invisibles)
- `FreezeIncidentReporter` (congelamiento de UI)
- `OSES.recommended_adjustments` con feedback `no_evidence`

### 4.9 Panel de Resumen Ejecutivo (Capa 8 — "Briefing")

Consolidación de `ControlMasterService.current_state()` + `ControlMasterDigestBuilder.build()` + indicadores cruzados.

---

## 5. Modelo de Datos/Eventos Propuesto

### 5.1 EvolutionEvent — Evento unificado de observabilidad

```python
class EvolutionEventKind(str, Enum):
    DECISION = "decision"
    LEARNING = "learning"
    ANOMALY = "anomaly"
    ADJUSTMENT = "adjustment"
    PROMOTION = "promotion"
    INCIDENT = "incident"
    BOOT = "boot"
    CONFIG_CHANGE = "config_change"
    EXAMINATION = "examination"

@dataclass
class EvolutionEvent:
    event_id: str
    kind: EvolutionEventKind
    timestamp_utc: str
    source_service: str          # ej: "DecisionAuditTrail", "OSES", "ExperimentLab"
    summary: str                 # texto humano, 1 línea
    severity: str                # "info", "warning", "critical"
    correlation_id: str          # para trazar flujo causal
    parent_event_id: str         # linaje
    metadata: dict[str, Any]     # datos específicos del tipo
    impact_modules: list[str]    # módulos afectados
```

### 5.2 OrganismHealthSnapshot — Snapshot unificado del organismo

```python
@dataclass
class OrganismHealthSnapshot:
    timestamp_utc: str
    
    # Signos vitales
    health_score: float                    # 0-1, agregado
    cognitive_pressure: str                # "NORMAL", "HIGH", "CRITICAL"
    network_status: str                    # "ok", "degraded", "offline"
    context_freshness_seconds: int
    
    # Contadores
    active_experiments: int
    active_anomalies: int
    recent_decisions_count: int
    recent_decisions_success_rate: float
    last_learning_seconds_ago: int
    
    # Sub-snapshots (refs, no copias)
    world_model_summary: dict[str, Any]
    oses_summary: dict[str, Any]
    decision_audit_summary: dict[str, Any]
    portable_context_summary: dict[str, Any]
    validation_cycle_summary: dict[str, Any]
    control_master_summary: dict[str, Any]
    
    # Alertas activas
    active_alerts: list[dict[str, Any]]
    
    # Últimos N eventos unificados
    recent_events: list[dict[str, Any]]
```

---

## 6. Flujo Causal: origen → decisión → ejecución → resultado → aprendizaje

```
[1] ORIGEN (Estímulo)
    ├─ InferenceRequest del usuario
    ├─ Evento espontáneo (HiddenIncident, FreezeIncident)
    ├─ Tick del ValidationCycle
    └─ Señal de WorldModel (cambio de red, ventana, herramienta)
         │
         ▼
[2] PERCEPCIÓN
    ├─ IntentUnderstandingService.classify()
    ├─ TaskContextAssembler.build()  →  TaskContext
    ├─ WorldModelService.current_model()  →  WorldModelSnapshot
    └─ PortableContextService.current_package()  →  contexto previo
         │
         ▼
[3] DECISIÓN
    ├─ AdaptiveTaskOrchestrator._select_route()
    ├─ AutonomyGovernancePolicy.evaluate()  →  ¿viable?
    ├─ StrategySelector.recommend()  →  ruta recomendada
    ├─ AdaptiveWeightLayer.suggest()  →  pesos adaptativos
    └─ [REGISTRO] DecisionAuditTrail.record(DecisionRecord)
         │
         ▼
[4] EJECUCIÓN
    ├─ LocalRoleRouter / CloudReasoningPlannerService
    ├─ ToolOperationalExecutor (si hay herramienta)
    └─ InferenceService (si es inferencia)
         │
         ▼
[5] RESULTADO
    ├─ TaskOutcomeRecorder.record(session, run_record)
    ├─ ExperimentLab.run_experiment()  →  ExperimentRun + Recommendation
    └─ AdaptiveWeightLayer.update_weights()  →  ajuste de pesos
         │
         ▼
[6] APRENDIZAJE
    ├─ StrategySelector absorbe nueva evidencia
    ├─ PortableContextService incluye nuevo aprendizaje
    ├─ OSES detecta patrones (background, diferido)
    └─ AutonomousValidationCycleService evalúa promociones
         │
         ▼
[7] METACOGNICIÓN (asíncrono)
    ├─ OSES._background_decision_review_findings()
    ├─ OSES._temporal_awareness_findings()
    ├─ OSES._deep_analysis_queue_findings()
    └─ Feedback loop: findings → recommended_adjustments → AdaptiveWeightLayer
```

**Nota:** Hoy este flujo NO tiene `correlation_id`. Cada paso es independiente. La propuesta de `EvolutionEvent.correlation_id` permitiría reconstruir la cadena completa.

---

## 7. Métricas Concretas por Panel

### Panel 0: Signos Vitales
| Métrica | Fuente | Cálculo |
|---------|--------|---------|
| Health Score | DAT | `total_successes / total_decisions` |
| Presión cognitiva | Orchestrator | `_assess_resource_pressure()` |
| Latencia red | WorldModel | `network_status.latency_ms` |
| Frescura contexto | PCS | `now - portable_context.updated_at_utc` |
| Experimentos activos | AVCS | `count(status=running)` |
| Anomalías activas | OSES | `count(findings where severity >= high)` |
| Tasa éxito decisiones | DAT | `success_count / total últimas 50` |
| Último aprendizaje | ExperimentLab | `now - last_run.created_at` |

### Panel 1: Anatomía (Grafo)
| Métrica por nodo | Fuente |
|------------------|--------|
| Actividad (eventos/hora) | DAT + RunRepository |
| Salud (error rate) | OSES findings por módulo |
| Última invocación | AdaptiveSessionRepository |

### Panel 2: Timeline
| Tipo evento | Fuente | Ícono |
|-------------|--------|-------|
| Decisión | DAT entries | ● |
| Aprendizaje | ExperimentRun | ★ |
| Anomalía | OSES findings | ▲ |
| Promoción | AVCS promotions | ■ |
| Ajuste peso | AWL adjustments | ◆ |
| Boot | BootProfileStore | ○ |

### Panel 3: Laboratorio
| Métrica | Fuente |
|---------|--------|
| Runs totales por dominio | ExperimentLabRepository |
| Score promedio por (route, assistant, config) | ExperimentRun.metrics |
| Ganador actual | ExperimentRecommendation.winner_label |
| Ventaja % | ExperimentRecommendation.advantage_pct |
| Muestras de soporte | ExperimentRecommendation.sample_support |

### Panel 4: Diagnóstico
| Métrica | Fuente |
|---------|--------|
| Findings activos | OSES.findings |
| Issues recurrentes | OSES.recurring_issues |
| Z-score latencia | OSES._temporal_awareness |
| EMA drift | OSES._deep_analysis |
| Provider trends | DAT.analyze_provider_trends() |

### Panel 5: Forense (Linaje)
| Dato | Fuente |
|------|--------|
| Decision chain | DAT.load_recent() con filtro |
| Fallback chain | DecisionRecord.fallback_chain |
| Steps completed/failed | DecisionRecord.steps_total/completed/failed |
| Learning generado | ExperimentRun linked por timestamp |

### Panel 6: Memoria
| Métrica | Fuente |
|---------|--------|
| Validated improvements | PCS.sections[validated_improvements] |
| Learned patterns | PCS.adaptive_learning_summary |
| Recommendations activas | OSES.recommended_adjustments |
| Feedback status | OSES adjustment.last_feedback_status |

### Panel 7: Alertas
| Tipo | Fuente | Prioridad |
|------|--------|-----------|
| Necesidad humana | ProactiveDashboardService | Alta |
| Incidente oculto | HiddenIncidentRepository | Alta |
| Degradación | OSES finding (degradation) | Media |
| Token expiring | TokenRotationLedger | Media |
| Light checks | OSES recurring (light_checks_warning) | Baja |

### Panel 8: Briefing Ejecutivo
| Dato | Fuente |
|------|--------|
| Objetivos activos | ControlMasterService.objectives |
| Backlog priorizado | ControlMasterService.backlog |
| Riesgos actuales | ControlMasterService.risks |
| Decisiones recientes | ControlMasterService.decisions |
| Digest narrativo | ControlMasterDigestBuilder |

---

## 8. Política de Retención/Compactación de Auditoría

### 8.1 Principio: "Nunca perder lo esencial, compactar lo redundante"

### 8.2 Niveles de retención

| Fuente | Retención raw | Compactación | Retención compactada |
|--------|--------------|--------------|---------------------|
| `decisions.jsonl` | 30 días | Agregar por proveedor/día → stats | Indefinida |
| `self_examination/history/` | 90 días | Mantener solo snapshots con findings no vacíos | Indefinida |
| `portable_context/history/` | 60 días | Mantener solo snapshots con cambios significativos | Indefinida |
| `experiment_runs` (SQLite) | 1000 registros | Purge runs donde score < threshold y no son ganadores | Indefinida para ganadores |
| `adaptive_sessions` (SQLite) | 500 registros | Archive completed con más de 90 días | 1 año |

### 8.3 Algoritmo de compactación propuesto

```python
def compact_decision_audit(data_root: Path, retention_days: int = 30) -> dict:
    """Compacta decisions.jsonl conservando:
    - Todos los registros de los últimos N días (raw)
    - Resumen diario por proveedor para registros anteriores:
      {date, provider, count, success_rate, avg_latency, errors_sample}
    - Decisiones históricas con outcome != 'success' (errores siempre se conservan)
    """
```

### 8.4 Reglas de preservación

1. **Nunca eliminar:** Decisiones con `outcome == 'failed'` o `outcome == 'rate_limited'`
2. **Nunca eliminar:** OSES findings con `severity >= 'high'`
3. **Nunca eliminar:** ExperimentRuns que son `winner` en alguna recommendation
4. **Nunca eliminar:** PortableContext snapshots que marquen UNRESOLVED
5. **Compactar con resumen:** Decisiones exitosas rutinarias (> 30 días)
6. **Compactar con resumen:** OSES reviews sin findings (> 90 días)

---

## 9. Plan Mínimo de Implementación por Fases

### Fase 0: Aggregator de solo lectura (IMPLEMENTABLE AHORA)
**Riesgo:** Bajo  
**Cambio:** Añadir `EvolutionaryObservabilityAggregator` en `services/evolution/`  
**Qué hace:** Lee de servicios existentes, produce `OrganismHealthSnapshot`  
**No toca:** domain/models.py, bootstrap.py (salvo wiring), AutonomyGovernancePolicy  
**Tests:** Unitarios con fakes de los servicios

### Fase 1: ViewModel unificado para Centro de Control Evolutivo
**Riesgo:** Bajo-Medio  
**Cambio:** Nuevo ViewModel `EvolutionControlCenterViewModel` que consume el aggregator  
**No toca:** Servicios existentes, solo los lee  

### Fase 2: QML Page con paneles
**Riesgo:** Bajo  
**Cambio:** Nueva page con los paneles descritos en sección 4  
**Dependencias:** PySide6 + QML existente

### Fase 3: Timeline evolutiva
**Riesgo:** Medio  
**Cambio:** Unificar eventos de distintas fuentes en stream temporal  
**Requiere:** Definir `EvolutionEvent` en domain/models.py (cambio de contrato → aprobación humana)

### Fase 4: Zoom jerárquico
**Riesgo:** Medio  
**Cambio:** Modelo de grafo + navegación drill-down  
**Requiere:** Diseño de interacción

### Fase 5: Compactación de auditoría
**Riesgo:** Medio  
**Cambio:** Script/servicio de compactación con las reglas de sección 8  
**Requiere:** Tests de no-pérdida-de-datos

### Fase 6: Correlation ID en flujo causal
**Riesgo:** Alto  
**Cambio:** Inyectar `correlation_id` en el flujo Percepción→Decisión→Ejecución→Aprendizaje  
**Toca:** TaskContextAssembler, AdaptiveTaskOrchestrator, DecisionAuditTrail, TaskOutcomeRecorder  
**Requiere:** Aprobación humana por tocar contratos cerrados

---

## 10. Tests Sugeridos y Tests Ejecutados

### Tests ejecutados (pre-existentes)
```
tests/test_centro_vivo_viewmodel.py    → 9 passed
tests/test_control_center_viewmodel.py → 94 passed, 2 failed (pre-existentes)
```

Los 2 fallos pre-existentes son:
1. `test_control_center_bootstrap_seeds_lightweight_development_packet` — falla por timing de deferred init
2. `test_control_center_evolution_panel_has_honest_fallbacks` — falla por tabla SQLite no creada en fixture

### Tests sugeridos para Fase 0 (Aggregator)
1. `test_aggregator_empty_services` — con servicios None, produce snapshot con defaults
2. `test_aggregator_health_score_from_decision_audit` — calcula health_score correctamente
3. `test_aggregator_cognitive_pressure_propagated` — lee resource_pressure del WorldModel
4. `test_aggregator_active_anomalies_from_oses` — cuenta findings high/critical
5. `test_aggregator_context_freshness` — calcula segundos desde último PCS update
6. `test_aggregator_recent_events_unified` — unifica eventos de múltiples fuentes
7. `test_aggregator_no_side_effects` — verifica que no modifica ningún servicio

---

## 11. Riesgos y Puntos UNRESOLVED

### UNRESOLVED

1. **UNRESOLVED:correlation_id** — No se puede implementar trazabilidad causal end-to-end sin modificar `AdaptiveTaskOrchestrator` y `TaskContextAssembler` (contratos cerrados P1-P4). Requiere aprobación humana.

2. **UNRESOLVED:qml_graph_rendering** — QML nativo no tiene un widget de grafos. Las opciones son:
   - Canvas 2D personalizado (implementable pero laborioso)
   - QML WebView con D3.js (dependency pesada)
   - Representación textual/ASCII del grafo (funcional, no bonita)

3. **UNRESOLVED:autonomous_validation_cycle** — El snapshot de AVCS muestra `bootstrapping` permanentemente. El primer tick no ocurrió en la sesión evaluada. Puede ser normal (el sistema requiere runtime live en Windows).

4. **UNRESOLVED:compaction_migration** — La compactación de `decisions.jsonl` requiere decidir si se hace in-place (riesgo de pérdida) o copy-on-write (usa más disco).

5. **UNRESOLVED:event_bus_architecture** — Un bus de eventos unificado (para alimentar el timeline en tiempo real) implicaría añadir un servicio nuevo. AGENTS.md prohíbe crear servicios paralelos. La alternativa (polling periódico del aggregator) es menos eficiente pero segura.

### Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Aggregator se vuelve un "segundo cerebro" | Media | Alto | Solo lectura, sin lógica de decisión |
| Performance del aggregator en cada refresh | Baja | Medio | Caché con TTL, solo refresca lo cambiado |
| QML page se vuelve pesada (como ControlCenterPage: 8116 líneas) | Media | Medio | Componentes modulares, lazy loading |
| Compactación pierde datos esenciales | Baja | Alto | Tests exhaustivos, dry-run mode |

---

## 12. Recomendaciones Visuales Innovadoras

### R1 — "Pulso del Organismo" (no un dashboard estático)
En vez de cards estáticas, un anillo central que pulsa con la frecuencia de eventos del sistema. Cuando hay actividad, el anillo late más rápido. Cuando hay anomalía, cambia de color. Click en el anillo → zoom al módulo activo.

### R2 — "Arterias de Datos" (no flechas estáticas)
Las conexiones entre módulos en el grafo deben tener "partículas" que fluyen en la dirección del dato. Más partículas = más actividad. Partículas rojas = errores fluyendo. Esto da la sensación de un organismo vivo.

### R3 — "Estratigrafía Temporal" (no timeline lineal)
En vez de una línea de tiempo horizontal, usar capas verticales como estratos geológicos. Cada capa representa un tipo de evento. Los estratos más gruesos = más actividad. Los eventos se pueden correlacionar visualmente entre capas.

### R4 — "Heatmap de Salud por Módulo"
Cada módulo del grafo tiene un color que refleja su salud. Verde brillante → excelente. Amarillo → degradado. Rojo → fallando. Gris → inactivo. Los colores deben ser suaves y usar el sistema de colores existente (cyan `#73d7d4`, amber `#c98a3d`, green `#6fcf97`, red `#eb5757`).

### R5 — "Respiration View" para ExperimentLab
Los experimentos se muestran como una "respiración": inhalar = recopilar datos, exhalar = emitir recomendación. El tamaño del "pulmón" refleja la cantidad de evidencia. Esto comunica intuitivamente si el sistema tiene suficiente evidencia o no.

### R6 — "Ghost Events" para UNRESOLVED
Los eventos marcados como UNRESOLVED se muestran semi-transparentes, como "fantasmas" en la timeline. No son datos confirmados pero tampoco se ignoran. Click → muestra por qué están unresolved.

### R7 — Implementación práctica con QML existente
Dado que el stack es PySide6 + QML y ya existe un design system (GlassPanel, AppButton, StatusPill, TruthStateBadge), las recomendaciones R1-R6 se implementarían con:
- `Canvas` de QML para el anillo pulsante
- `Repeater` + `Rectangle` con animaciones para arterias
- `ListView` con delegates diferenciados para estratigrafía
- `Rectangle` con `color` binding para heatmap
- `OpacityAnimator` para ghost events

---

## Resumen Final

### ¿Qué se encontró?
El sistema IABV v1.5 tiene **excelente infraestructura de metacognición** (OSES: 7800 líneas, DAT: 514 líneas, PCS: 3464 líneas). Los datos existen. Lo que falta es la **convergencia visual**: un único punto donde el operador vea todo el organismo, haga drill-down, y rastree linaje causal.

### ¿Qué ya existe y se reutiliza?
- `CentroVivoViewModel` como punto de partida para el aggregator (ya lee 7 fuentes)
- `DecisionAuditTrail.self_examination_summary()` para health score
- `OSES.current_review()` para findings y anomalías
- `PortableContextService.build_package()` para arquitectura y aprendizaje
- `ControlMasterService.current_state()` para governance
- Design system QML existente (GlassPanel, StatusPill, etc.)

### ¿Qué es implementable ahora?
**Fase 0:** Un `EvolutionaryObservabilityAggregator` de solo lectura que produce `OrganismHealthSnapshot` sin tocar contratos cerrados ni crear un cerebro paralelo. Incluye tests focalizados.

### ¿Qué queda UNRESOLVED?
1. `correlation_id` para trazabilidad causal (requiere tocar contratos cerrados → aprobación humana)
2. Grafo visual en QML (requiere decisión de implementación)
3. Compactación de auditoría (requiere diseño de migración)
4. `AutonomousValidationCycleService` en estado `bootstrapping` permanente
5. Bus de eventos vs polling

### Siguiente paso recomendado
Implementar Fase 0 (aggregator de solo lectura) en esta sesión, con tests, en rama `devin/evolution-control-center-observability`.
