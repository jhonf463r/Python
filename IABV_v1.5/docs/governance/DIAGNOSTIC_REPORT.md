# IABV v1.5 — Informe Diagnóstico Completo

**Fecha:** 2026-05-03  
**Agente:** Devin (Cognition AI)  
**Fuentes:** source tree (240 .py), test suite (2416 tests), IABV_MASTER_DOC_v1.md, AGENTS.md, data/evolution/

---

## 1) RESUMEN EJECUTIVO

IABV v1.5 es un sistema **real y funcional** de coordinación multi-IA local-first. No es un prototipo ni un mockup. El núcleo (orquestador, world model, aprendizaje, auditoría, gobernanza, MCP, UI) está construido y operativo, con 2391 tests pasando de 2416.

**Distancia a la visión:** ~65-70% del camino. Las piezas fundamentales existen. Lo que falta es:
- Cerrar el loop de cuota/presupuesto (quota tracker desconectado)
- Selector unificado que incluya rutas web
- Resume-aware orchestration (infraestructura existe, consumidor falta)
- Métricas formales de autonomía (fórmulas definidas, código no implementado)
- Estabilidad de arranque (ControlCenterVM bloqueante, pageLoader freeze)

**Fortalezas principales:**
- Arquitectura por capas bien definida y respetada
- ControlMasterDigest como fuente compacta de gobernanza funciona
- Pipeline de aprendizaje completo (ExperimentLab → StrategySelector → AdaptiveWeightLayer → TaskOutcomeRecorder)
- WorldModel operativo con percepción real vía Win32
- 37 reglas de gobernanza sembradas y respetadas
- MCP server con tools de auditoría funcionales
- Bootstrap que carga secretos automáticamente

**Debilidades principales:**
- ControlCenterVM (7056 LOC) bloquea main thread ~3.7s
- Quota tracker existe pero no se alimenta → presupuesto cero no funciona
- 29 tests fallando (deuda pre-existente)
- Control Master se desactualiza entre sesiones
- Código disperso que debería estar en AutonomyCycleService

---

## 2) ESTADO REAL DEL REPO

| Métrica | Valor |
|---|---|
| Archivos Python fuente | 240 |
| Líneas de código (src/) | 110,348 |
| Archivos de test | 193 |
| Tests passing | 2,391 |
| Tests failing | 29 |
| Tests skipped | 25 |
| Backlog items totales | 41 |
| Pendientes | 25 (6 critical, 16 high) |
| Reglas en Control Master | 37 |
| Objetivos activos | 4 |
| UNRESOLVED items | 10 |
| Repositorios de persistencia | 21 |
| Servicios de evolución | 39 |
| ViewModels | 8 |
| MCP tools | 7+ |

---

## 3) MAPA DE MÓDULOS

Ver `docs/governance/ARCHITECTURE_MAP.md` para el diagrama completo.

**Resumen por capas:**
1. **UI/Presentación:** 8 ViewModels + Controllers, Qt/QML
2. **Orquestación:** ATO (cerebro único) + 14 servicios de soporte
3. **Percepción/Mundo:** WorldModelService + EnvironmentSelfAwareness + 4 servicios
4. **Aprendizaje/Evolución:** 39 archivos — ExperimentLab pipeline, OSES, PortableContext, ControlMaster
5. **Gobernanza:** ControlMasterService + Repository + DigestBuilder + CLI
6. **Herramientas:** 14 servicios de tools con registry, sandbox, approval
7. **Captura/Replay:** 16 servicios de browser automation y replay
8. **Infraestructura:** bootstrap, MCP server, 21 repositorios, logging, config

---

## 4) CEREBRO CENTRAL ACTUAL

`AdaptiveTaskOrchestrator` (3557 líneas) es el **único cerebro**. Decide:

- **Qué hacer:** consume `IntentUnderstandingService` para clasificar intent
- **Quién lo hace:** usa `LocalRoleRouter` + `AdaptiveModelSelector` para elegir provider
- **Si puede hacerse:** consulta `AutonomyGovernancePolicy` + `WorldModelSnapshot`
- **Contexto:** `TaskContextAssembler` ensambla percepción, world model y portable context
- **Registro:** `TaskOutcomeRecorder` cierra el loop de aprendizaje
- **Planes cloud:** `CloudReasoningPlannerService` genera planes multi-paso

**Cadena de decisión real:**
```
user input → IntentUnderstandingService → TaskContextAssembler
  → AutonomyGovernancePolicy.evaluate()
  → LocalRoleRouter → AdaptiveModelSelector
  → ATO._build_task_packet() → despacho → TaskOutcomeRecorder
```

**No hay otro cerebro.** Los VMs observan pero no deciden. El sandbox está aislado. La regla AGENTS.md se respeta en el código actual.

---

## 5) PERCEPCIÓN Y SELF-MODEL

### WorldModelSnapshot (bien encarnada)
- `WorldModelService` mantiene snapshot vivo con scan periódico (45s light, 180s full)
- Campos: active_windows, focused_window, tool_live_status, network_status, background_processes, detected_blocks, block_records, permission_gates, confidence, unresolved_fields
- **Falta:** campo `worker_pool_snapshot` (backlog 32e1ee5b)

### EnvironmentSelfModel (funcional)
- Hardware, OS, capacidades, riesgos del entorno
- `UNRESOLVED:cpu_frequency` persiste pero no afecta decisiones

### PerceptionSnapshot (entrada unificada)
- Se construye antes de cada decisión
- Consumido por ATO como input principal

**Evaluación:** Percepción unificada está **bien implementada**. Las 3 piezas (WorldModel, SelfModel, Perception) se complementan sin duplicarse. Solo falta worker_pool para completar la foto del mundo.

---

## 6) SINCRONIZACIÓN ENTRE IAs

### Lo que funciona:
- **ControlMasterDigest:** <2KB compacto inyectable en cualquier IA — funcional
- **PortableContextService:** exporta contexto comprimido con sección cloud_reasoning
- **CLI `cm export-digest`:** funcional, permite sincronía al arrancar sesión
- **MCP tools:** portable_context_get, world_model_snapshot, self_examination_current

### Lo que falta:
- **El digest se desactualiza** si no se actualiza al cerrar cada sesión
- **No hay escritura automática** al cerrar sesión (AGENTS.md lo define como objetivo pero no hay hook automático)
- **Rutas web no son candidatos formales** del selector → IAs web (ChatGPT, Claude) no participan del ranking

**Evaluación:** La infraestructura de sincronía existe y funciona. El gap es operacional (disciplina de actualizar) más que arquitectónico.

---

## 7) APRENDIZAJE Y EVOLUCIÓN

### Pipeline completo y funcional:
```
ExperimentLab → StrategySelector → AdaptiveWeightLayer → TaskOutcomeRecorder
```

- **ExperimentLab:** compara rutas, asistentes y configuraciones
- **StrategySelector:** recomienda por historial y evidencia
- **AdaptiveWeightLayer:** ajusta preferencia futura con resultados reales
- **TaskOutcomeRecorder:** cierra el loop desde ejecución normal
- **DecisionAuditTrail:** registra decisiones cloud en JSONL

### Parcial:
- **PlatformPendingQueue:** 9 tasks sembradas, 4 completadas, resume_hints existen pero nadie los consume al arrancar
- **MetacognitionEvolutionMixin:** detecta providers no funcionales y dispara aprovisionamiento con cooldown
- **Quota tracker:** existe pero no se alimenta → selector no sabe cuotas reales

### No implementado:
- **Shadow mode cloud+local en paralelo** (diseñado, no implementado)
- **UniversalAutonomyIndex** (fórmulas definidas, código no existe)
- **Corpus de entrenamiento de traces** (idea, no código)

**Evaluación:** El aprendizaje es **real y reutilizable** en su pipeline core. El gap está en el loop de cuota (no se alimenta) y en métricas formales de autonomía.

---

## 8) AUDITORÍA Y REPLAY

### Operativo:
- **OSES (6485 LOC):** revisa patrones, degradaciones, ajustes recomendados, temporal awareness, background decision review, deep analysis queue
- **DecisionAuditTrail:** persiste en JSONL con proveedor, latencia, confianza, resultado, tendencia
- **SelfAuditService:** run_self_audit produce SelfAuditSnapshot
- **MCP tools:** run_self_audit, audit_capability, compare_perception_vs_ground_truth, probe_assistant_login
- **IABV_AUDIT_MODE=1:** modo read-only funcional

### Parcial:
- **Live audit supervisor:** existe pero la cadena completa requiere MCP + tunnel activos
- **ReplayAnnotationService / ReplayConfidenceService:** infraestructura de replay existe

**Evaluación:** La trazabilidad es **fuerte**. OSES es la pieza más robusta del sistema con 6485 LOC de meta-observación continua. El replay existe como infraestructura pero su uso depende de la captura de sesiones de browser.

---

## 9) UI Y VIEWMODELS

### Estado:
| ViewModel | LOC | Función | Estado |
|---|---|---|---|
| ControlCenterVM | 7056 | Centro de control principal | **Bloqueante (3733ms init)** |
| CaptureStudioVM | 2797 | Captura y enseñanza de browser | Funcional |
| EvolutionCenterVM | 1014 | Estado evolutivo y world model | Funcional |
| DashboardVM | ~500 | Dashboard general | Funcional |
| KnowledgeBaseVM | ~400 | Base de conocimiento | Funcional |
| ProviderSettingsVM | ~300 | Configuración de providers | Funcional |
| RunHistoryVM | ~400 | Historial de ejecuciones | Funcional |
| CentroVivoVM | ~300 | Centro vivo | Funcional |

### Problema principal:
ControlCenterVM es el VM más grande (7056 LOC) y su `__init__` tarda 3733ms, bloqueando el main thread. Los otros VMs se construyen lazy en <40ms.

### Regla respetada:
Los VMs no toman decisiones de ruta ni modifican task_packet. Son display observacional, no otro cerebro.

---

## 10) DIFERENCIAS CON LA VISIÓN ORIGINAL

| Componente | Visión original | Estado real | Clasificación |
|---|---|---|---|
| Chat central robusto | Hub de decisión unificado | ATO funcional como cerebro | **Alineado** |
| Percepción unificada | WorldModel + SelfModel + Perception | Construido y operativo | **Alineado** |
| Self-model operativo | EnvironmentSelfModel vivo | Funcional (cpu_freq UNRESOLVED) | **Fortalecido** |
| World model | WorldModelSnapshot con scan periódico | Operativo, falta worker_pool | **Incompleto** |
| Multi-IA coordinada | Selector unificado all-sources | Solo APIs, no web sessions | **Incompleto** |
| Aprendizaje | Pipeline completo con evidencia | ExperimentLab pipeline funcional | **Alineado** |
| Auditoría viva y replay | OSES + DecisionAuditTrail + replay | Operativo, replay parcial | **Fortalecido** |
| Detección de fallas | Metacognición + hidden incidents | Implementado en OSES | **Alineado** |
| Automejora guiada | AutonomousValidationCycle + Sandbox | Existe, funcional | **Alineado** |
| UI estado real | VMs observacionales | Funcional pero ControlCenterVM bloqueante | **Incompleto** |
| Evolución sin duplicar | Una sola arquitectura | Respetado, sin cerebros paralelos | **Alineado** |
| Autonomía progresiva | Presupuesto cero + auto-provisioning | Parcial — quota no se alimenta | **Desviado** |
| Control Maestro vivo | Fuente de verdad gobernanza | Implementado pero se desactualiza | **Incompleto** |

---

## 11) DESVIACIONES Y POSIBLES CAUSAS

### 1. Quota tracker desconectado
**Causa:** Se construyó la infraestructura de quota tracking pero la integración con el flujo de despacho del ATO quedó pendiente — probablemente por priorización de features más visibles.

### 2. Selector no incluye rutas web
**Causa:** Las rutas web (chatgpt_web, claude_web) tienen un modelo de interacción diferente (browser automation) que no encaja naturalmente en el ranking de APIs. Requiere diseño de cómo rankear UI vs API.

### 3. Resume hints sin consumidor
**Causa:** Se construyó la infraestructura de persistencia (PlatformResumeHint, PlatformPendingQueue) pero el consumidor en el ATO al arrancar nunca se implementó — el loop de autonomía quedó abierto en la fase "reanudar".

### 4. ControlCenterVM excesivamente grande
**Causa:** Evolución orgánica. A medida que se agregaron features (formal external state flags, compound self-awareness, agent cards, etc.), el VM creció sin reestructurarse.

### 5. Control Master se desactualiza
**Causa:** La escritura al cerrar sesión depende de disciplina del agente. No hay hook automático que fuerce la actualización.

---

## 12) DUPLICACIONES Y SOLAPAMIENTOS

| Código duplicado | Donde está | Donde debería estar | Impacto |
|---|---|---|---|
| bridge_findings_to_pending_queue | inline en OSES | AutonomyCycleService (propuesto) | Medio |
| save_resume_hint_if_interrupted | inline en TOR | AutonomyCycleService (propuesto) | Bajo |
| seed_from_capability_graph | ad-hoc en bootstrap | AutonomyCycleService (propuesto) | Bajo |
| Construcción del worker pool | AccountResourceScanner + ATO | Solo ATO, pasado como dato al router | Medio |
| Reconstrucción de assistant_kind | TOR._record_learning() | Debería leer task_packet directamente | Bajo |

**Nota:** Estas duplicaciones son menores y tienen fallbacks que funcionan. No son bugs sino deuda de organización. La consolidación en AutonomyCycleService es la solución correcta, pero requiere confirmar UNRESOLVED U1 primero.

---

## 13) GAPS REALES

Para cerrar el núcleo y llegar al sistema deseado, falta:

| Gap | Gravedad | Esfuerzo |
|---|---|---|
| ControlCenterVM lazy init | Bloqueante | 1 sesión |
| Quota tracker wiring | Alto | 1 sesión |
| worker_pool en WorldModel | Medio | 1 sesión |
| Selector unificado (web + API + local) | Alto | 2-3 sesiones |
| Resume-aware orchestration | Medio | 1 sesión |
| UniversalAutonomyIndex en OSES | Bajo | 1 sesión |
| AutonomyCycleService (si se confirma) | Medio | 2 sesiones |
| Actualización automática del Control Master al cerrar | Medio | 1 sesión |
| Shadow mode cloud+local | Bajo | 2-3 sesiones |
| Corpus de entrenamiento de traces | Bajo | 3+ sesiones |

---

## 14) RIESGOS Y DEUDA

Ver `docs/governance/RISKS.md` para clasificación completa.

**Top 3 por impacto inmediato:**
1. ControlCenterVM bloqueante → usuario percibe app congelada
2. Quota tracker desconectado → presupuesto cero no funciona
3. 29 tests fallando → pueden enmascarar regresiones reales

---

## 15) PRIORIDAD DE IMPLEMENTACIÓN

**Corregir primero (máxima autonomía con mínimo riesgo):**
1. ControlCenterVM lazy init → desbloquea Responding=True@60s
2. Quota tracker wiring → cierra el loop de presupuesto
3. worker_pool en WorldModel → habilita decisiones basadas en cuota

**Conservar (ya está sano):**
- WorldModelService core
- ExperimentLab → StrategySelector → AdaptiveWeightLayer pipeline
- OSES (6485 LOC de meta-observación)
- ControlMaster infrastructure
- MCP server y tools
- Bootstrap (carga de secretos, wiring)

**No tocar todavía:**
- Refactor masivo de ControlCenterVM → solo lazy init por ahora
- AutonomyCycleService → confirmar U1 primero
- Shadow mode → depende de selector unificado
- Corpus de entrenamiento → requiere datos acumulados
- Framework científico (marco teórico) → base conceptual, no código

---

## 16) CONCLUSIÓN HONESTA

**IABV v1.5 es un proyecto real, ambicioso y sorprendentemente bien estructurado** para su complejidad. Tiene 110K+ LOC de código Python funcional con 2391 tests pasando, una arquitectura por capas coherente, gobernanza formal con 37 reglas, y un pipeline de aprendizaje completo.

**No es un prototipo.** El sistema ya percibe su entorno (WorldModel), toma decisiones (ATO), aprende de resultados (ExperimentLab pipeline), se audita (OSES), y expone su estado interno (ControlMasterDigest, PortableContext, MCP tools).

**Lo que le falta para ser sólido:**
1. **Cerrar el loop de cuota** — la pieza que hace real el "presupuesto cero"
2. **Estabilidad de arranque** — el ControlCenterVM bloqueante es la única barrera visible
3. **Selector unificado** — para que el sistema elija la mejor IA disponible de verdad
4. **Métricas formales** — para que el sistema sepa cuán autónomo es objetivamente
5. **Resume-aware** — para que las tareas interrumpidas no se pierdan

**Estimación realista:** con 4-6 sesiones más de trabajo enfocado (siguiendo el plan de implementación del Master Doc), el sistema puede cruzar el umbral de autonomía básica donde se sostiene solo para tareas rutinarias.

**El mayor riesgo no es técnico sino de continuidad:** si cada sesión empieza sin contexto, se repite trabajo y se pierde alineación. La capa de gobernanza creada en esta sesión busca resolver exactamente ese problema.
