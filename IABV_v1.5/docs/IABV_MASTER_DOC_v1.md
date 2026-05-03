# IABV v1.5 — Documento Maestro de Estado, Visión y Evolución
**Generado:** 2026-05-03  
**Fuente:** análisis de repo real (IABV_v1_5.7z), chats con Windsurf, Codex, ChatGPT, Architecture Report V5  
**Para:** toda IA que trabaje en este proyecto (Devin, Codex, Claude, ChatGPT, Windsurf)  
**Uso:** leer antes de proponer cualquier cambio. No sustituye leer AGENTS.md — lo complementa.

---

## I. VISIÓN ACTIVA (del Control Master real)

> *"IABV v1.5 local-first con Control Maestro vivo: ControlMasterDigest como única fuente compacta para que cualquier IA (Codex, ChatGPT, Devin, Claude) arranque sincronizada sin pegar historial. Super sincronía = lectura automática al entrar + escritura estructurada al cerrar cada sesión."*

**Propósito de largo plazo** (de los chats y backlog):  
IABV debe ser el cerebro central de la laptop — coordinar múltiples IAs/herramientas, sostenerse solo con recursos gratuitos, aprender de cada sesión, detectar cuándo su propia estructura necesita evolucionar, y reestructurarse sin destruir lo ya construido.

**Analogía del ADN** (idea recurrente del propietario):  
El programa debe tener un núcleo que puede modificarse a sí mismo para adaptarse al dispositivo donde corre, igual que el ADN expresa distintos fenotipos según el entorno — sin perder la información acumulada.

---

## II. ESTADO REAL DEL REPOSITORIO

### Métricas de salud (confirmadas del 7z)
| Métrica | Valor |
|---|---|
| Archivos Python fuente | 1801 |
| Archivos de test | 193 |
| Tests confirmados passing | 2524 (última corrida Windsurf) |
| Failures pre-existentes | 23 (no regresiones nuevas) |
| Backlog items totales | 41 |
| Pendientes críticos | 6 |
| Pendientes high | 16 |
| Reglas en Control Master | 37 (desde AGENTS.md) |
| Objetivos activos en CM | 4 |
| Control Master state actualizado | 2026-04-19 (desactualizado — ver Sección IV) |

### Arquitectura real en capas
```
┌─────────────────────────────────────────────────────┐
│  UI / Presentación (Qt/QML)                         │
│  ControlCenterVM  DashboardVM  CaptureStudioVM      │
│  EvolutionCenterVM  KnowledgeBaseVM  ProvidersVM    │
└──────────────────┬──────────────────────────────────┘
                   │ signals/slots
┌──────────────────▼──────────────────────────────────┐
│  Orquestación                                        │
│  AdaptiveTaskOrchestrator  (cerebro central)         │
│  AutonomyGovernancePolicy  (gobernanza)              │
│  CloudReasoningPlannerService                        │
│  [AutonomyCycleService — PROPUESTO, ver Sección IV]  │
└──────────────────┬──────────────────────────────────┘
                   │ delega
┌──────────────────▼──────────────────────────────────┐
│  Percepción / Mundo                                  │
│  WorldModelService → WorldModelSnapshot              │
│  EnvironmentSelfModel                                │
│  OperationalSelfExaminationService (OSES)            │
│  MetacognitionEvolutionMixin                         │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│  Aprendizaje / Evolución                             │
│  ExperimentLab  StrategySelector  AdaptiveWeightLayer│
│  TaskOutcomeRecorder  DecisionAuditTrail             │
│  PortableContextService  PlatformPendingQueue        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│  Gobernanza / Control Maestro                        │
│  ControlMasterService  ControlMasterRepository       │
│  ControlMasterDigestBuilder  CLI (cm export-digest)  │
│  ObjectiveRepository  ControlMasterState             │
└──────────────────┬──────────────────────────────────┘
                   │ persiste
┌──────────────────▼──────────────────────────────────┐
│  Infraestructura                                     │
│  bootstrap.py  InfraStorage  SQLite  JSONL logs      │
│  MCP server (127.0.0.1:8000)  Cloudflared tunnel    │
│  AccountResourceScanner  QuotaTracker               │
└─────────────────────────────────────────────────────┘
```

---

## III. MAPA DE LO CONSTRUIDO, PARCIAL Y FALTANTE

### A. CONSTRUIDO Y FUNCIONANDO

#### Control Maestro (completo)
- `ControlMasterService` — set_vision, upsert_rule, record_decision, mark_objective, mark_unresolved, seed_from_agents_md, _project_backlog, _project_risks
- `ControlMasterRepository` — save_state, load_latest_state, list_history, upsert_rule, record_decision, list_rules, list_decisions
- `ControlMasterDigestBuilder` — produce digest compacto (<2KB) para inyectar en cualquier IA
- `ControlMasterDigest` en domain/models.py — current_vision, active_objectives_brief, rules_brief, top_backlog, current_risks, recent_decisions_brief, unresolved, tests_state_brief
- CLI: `python -m iabv_v15 cm export-digest --format markdown` funcional
- 37 reglas sembradas desde AGENTS.md
- 4 objetivos activos en el estado persistido
- Bootstrap wiring: ControlMasterService se inyecta en ATO, OSES, EvolutionCenterVM

#### Task Packet (construido como dict, no como dataclass)
- `AdaptiveTaskOrchestrator._build_task_packet()` — produce dict estructurado con: objective, intent_key, route_summary (detected_role, assistant_kind), worker_gate_summary (ran, usable, top_worker, available_count), selected_worker, evidence_basis, governance_flags (approval_required, should_consult, block_risky_action), unresolved
- Se adjunta a `session.metadata['task_packet']` antes del despacho
- `TaskOutcomeRecorder` lee `session.metadata.get('task_packet')` para `selected_worker`
- `RunHistoryViewModel._load_task_packet()` lo lee para display
- `preflight_external_assistant()` produce un task_packet paralelo para consultas externas

#### WorldModel / Percepción (construido)
- `WorldModelService` con `_detected_blocks()`, `_network_status()`, `_block_records()`
- `WorldModelSnapshot` — tool_live_status, active_windows, detected_blocks, block_records, permission_gates, confidence, unresolved_fields
- `EnvironmentSelfModel` — hardware, OS, capacidades, unresolved_fields
- `AutonomyGovernancePolicy.evaluate()` — 260+ líneas de lógica de gobernanza que consume WorldModel

#### Aprendizaje formal (construido)
- `ExperimentLab` → `StrategySelector` → `AdaptiveWeightLayer` → `TaskOutcomeRecorder`
- `DecisionAuditTrail.record()` con audit_id, decision_type, metadata
- `PortableContextService` — exporta estado compacto para IAs externas (MCP tools: world_model_snapshot, portable_context_get, self_examination_current)
- `MetacognitionEvolutionMixin` — all_findings(), react_to_findings(), run_evolution_cycle()
- `PlatformPendingQueue` — 9 tasks sembradas, 4 completadas, infraestructura de resume_hints

#### Arranque (mejorado en PR #307, estado v3)
- Splash → shell en ~6350ms (honesto, sin fallback falso)
- Responding=True @ 30s (primera vez en la serie, confirmado Windsurf v3)
- ViewModels lazy: CaptureStudio, Evolution, Knowledge, Providers se construyen en <40ms on-demand
- IABV_AUDIT_MODE=1: modo read-only que salta auto_install, MCP autostart, correcciones

#### MCP + Tunneling (operativo)
- MCP server en 127.0.0.1:8000 (python.exe hijo)
- Cloudflared tunnel vivo (PID separado)
- Tools MCP: world_model_snapshot, portable_context_get, self_examination_current, run_self_audit, compare_perception_vs_ground_truth, probe_assistant_login, audit_capability

#### Account Resource Scanner (construido, desconectado)
- `record_message_sent(tool, email)` — tracking de cuota
- `get_all_quota_status()` — estado de todas las cuentas
- `best_account_for_tool(tool)` — mejor cuenta disponible
- `estimate_available_workers()` — pool rankeado
- `verify_account_sessions()` — cruza cookies de Chrome/Edge/Brave/Firefox con emails
- Dual-brain classifier local+cloud con `_save_training_example()`

#### Metacognición y Autoprovisionamiento (reciente, de Codex)
- `MetacognitionEvolutionMixin` detecta "non functional provider" y "single provider dependency"
- Prioriza providers gratis faltantes y dispara aprovisionamiento con cooldown persistido
- `ApiKeyDiscoveryService` + `auto_provision_missing_secrets()`
- `DecisionSimplifierEngine` con contexto real de missing_env_keys

---

### B. PARCIAL O DESCONECTADO

#### AutonomyCycleService (propuesto en Architecture V5, NO en 7z)
**Estado:** diseñado en el Architecture Report V5 del PR #307 (branch devin/1777750256), pero el archivo no existe en el source tree del 7z analizado.  
**Lo que debía hacer:** centralizar bridge OSES→queue (antes inline en OSES), resume hints (antes inline en TOR), capability discovery (antes ad-hoc en bootstrap), startup_summary para el orquestador.  
**UNRESOLVED:** no se puede confirmar si fue mergeado, descartado, o si el 7z es una versión anterior al merge.

#### Resume hints sin consumidor
La infraestructura existe: `PlatformResumeHint`, `PlatformPendingQueue`, `save_resume_hint_if_interrupted` en TOR. Pero **ningún orquestador lee `startup_summary()` al arrancar para ofrecer "continuar tarea interrumpida"**. El loop de autonomía queda abierto aquí: percibir → decidir → ejecutar → verificar → aprender → **reanudar (FALTA)**.

#### Quota tracker sin alimentación automática
`record_message_sent()` existe pero **no se llama en el flujo de ejecución normal**. El Orchestrator hace `best_account_for_tool()` para elegir worker, pero no registra el mensaje enviado. El tracker lee sin escribir → los workers nunca "se gastan" en el modelo interno.

#### Selector unificado cloud/local/web (backlog 8db889f0, crítico)
`AdaptiveModelSelector` rankea APIs (groq, gemini, openrouter, together, ollama_local). Las rutas web (chatgpt_web, claude_web) no son candidatos formales del selector. `CloudReasoningPlannerService` usa una secuencia parcial. El ranking no consume WorldModelSnapshot para excluir providers con permission_gates activos.

#### Shadow mode local (backlog 0b8584c3)
El patrón dual-brain existe en `account_resource_scanner.classify_chat_intent()` (local+cloud en paralelo). Pero NO está generalizado al razonamiento principal. Cada sesión usa un solo provider; no hay comparación cloud vs local con `comparison_scope_key` compartido.

#### Worker pool en WorldModelSnapshot (backlog 32e1ee5b)
`WorldModelSnapshot` no tiene campo `worker_pool_snapshot`. La disponibilidad de workers se consulta ad-hoc en el Orchestrator pero no es parte del estado canónico del mundo. `AutonomyGovernancePolicy` no puede bloquear rutas basándose en cuota agotada porque no tiene ese dato.

#### Control Master desactualizado
El `latest.json` del Control Master tiene timestamp 2026-04-19 — dos semanas antes de los cambios del PR #307 (2026-04-30). Los objetivos activos (4) y el estado de tests no reflejan el trabajo reciente de Windsurf/Codex. La visión es correcta pero los campos `completed_objective_ids`, `current_tests_state` y `recent_decisions` están desactualizados.

---

### C. CONFIRMADAMENTE FALTANTE

#### ControlCenterViewModel no bloqueante (bloqueante real)
`ControlCenterViewModel.__init__` tarda **3733ms** al construirse on-demand y bloquea el main thread → Responding=False@60s. Los otros 4 VMs se construyen en <40ms. El fix: mover la inicialización pesada a `_initialize_heavy()` con `QTimer.singleShot(0)` post-registro. Esto es el único bloqueante que separa la v3 de un PASS completo en la auditoría.

#### lazy_vm_prebuild_done nunca dispara
El QTimer de 15s para pre-construir ViewModels en background nunca disparó en 120s de observación. El milestone `lazy_vm_prebuild_done` no existe en los JSONL reales. Si el event loop está ocupado con tool probing y MCP startup al segundo 15, el timer se pierde.

#### Startup freeze de 28s en pageLoader
OSES reporta `startup_populate_ui_freeze: 28716ms CRITICAL`. El pageLoader (QML) incuba síncronamente entre `populate_ui_deferred_1_done` (6337ms) y `page_loader_ready` (35021ms). 28 segundos donde el event loop no puede responder.

#### UniversalAutonomyIndex (idea de ChatGPT, no implementada)
La conversación con ChatGPT definió métricas operativas para medir autonomía real:
```
AutonomyScore = (
    0.30 * capability_coverage +      # tasks que puede hacer solo
    0.25 * handoff_required_rate +     # handoffs a humano
    0.20 * unresolved_ratio +          # campos UNRESOLVED
    0.15 * permission_request_rate +   # permisos pedidos
    0.10 * resume_success_rate         # tareas reanudadas
)
```
Y ResilienceScore, CalibrationError, CapabilityCoverage, BlindSpotRatio. **No hay código que calcule ni persista estas métricas**. Están en los chats como ideas no implementadas.

#### Framework científico de emergencia de razonamiento (ChatGPT)
La conversación exploró el marco formal: sistema (X, Y, θ, L), función de pérdida, K(x) complejidad de Kolmogorov, R(f_θ) capacidad de razonamiento, conjetura d²R/dN² > 0 para N > N_c. **No hay código**. Son bases teóricas para futuras decisiones de arquitectura de aprendizaje.

#### Bloqueo proactivo pre-despacho por evidencia local
AGENTS.md dice que la evidencia del WorldModel prevalece sobre afirmaciones de IAs externas. Pero no existe código que, *antes* de despachar a una ruta externa, compare el estado del WorldModel contra lo que el provider afirma sobre su disponibilidad y bloquee si contradicen.

---

## IV. PROBLEMAS DE ORDEN Y DEUDA TÉCNICA

### Duplicaciones confirmadas

| Código duplicado | Donde está | Donde debería estar |
|---|---|---|
| `_bridge_findings_to_pending_queue` | inline en OSES | AutonomyCycleService (propuesto) |
| `_save_resume_hint_if_interrupted` | inline en TOR | AutonomyCycleService (propuesto) |
| `seed_from_capability_graph` | ad-hoc en bootstrap | AutonomyCycleService (propuesto) |
| Construcción del worker pool | AccountResourceScanner + ATO | Solo ATO, pasado como dato al router |
| Reconstrucción de assistant_kind | TOR._record_learning() | Debería leer task_packet directamente |

### Ideas en chats que NO deben descartarse

| Idea | Origen | Estado | Dónde implementar |
|---|---|---|---|
| Shadow mode cloud+local en paralelo | Codex | Diseñado, no implementado | AdaptiveModelSelector + ATO |
| UniversalAutonomyIndex | ChatGPT | Solo fórmula | OSES findings + ControlMasterDigest |
| AutonomyCycleService | Windsurf | Diseñado, no confirmado en 7z | services/evolution/autonomy_cycle_service.py |
| Rutas web como candidatos formales | Codex | Partial (WorldModel las ve pero selector no las usa) | AdaptiveModelSelector |
| Corpus de entrenamiento derivado de traces | Codex | No implementado | ExperimentLab + PortableContextService |
| Login gobernado de cuentas gratis | Codex | Metacognición dispara pero no completa login | ApiKeyDiscoveryService + MCP tools |
| read-only audit mode | Codex | IMPLEMENTADO (IABV_AUDIT_MODE=1) | ✅ bootstrap.py |
| Pre-scan metacognitivo antes de cada sesión | AGENTS.md | Implementado en OSES | ✅ |
| Resume-aware orchestration | Windsurf Architecture V5 | Infraestructura existe, consumidor falta | ATO + startup |

### Riesgo de crear otro cerebro (regla AGENTS.md)

Los siguientes backlog items, si se implementan mal, crean un orquestador paralelo:
- `8db889f0` — "Selector soberano unificado": debe ser un método del Orchestrator existente, NO un servicio nuevo con estado propio
- Shadow mode: debe ser una ruta interna del ATO, no un servicio separado que decide
- UniversalAutonomyIndex: debe ser un cálculo de OSES, no un servicio nuevo

---

## V. REGLAS IRREVOCABLES (de AGENTS.md, consolidadas)

Toda IA que trabaje en este proyecto debe respetar estas reglas. No son negociables:

1. **No crear otro orquestador.** `AdaptiveTaskOrchestrator` es el único cerebro. Nuevas lógicas van adentro como métodos, no como servicios paralelos.
2. **No crear memoria paralela.** Todo aprendizaje va a ExperimentLab → StrategySelector → AdaptiveWeightLayer → TaskOutcomeRecorder. No crear otro store.
3. **No mover decisiones soberanas a ViewModels.** Los VMs son display. No modifican task_packet, no deciden rutas.
4. **La evidencia local prevalece.** Si WorldModelSnapshot dice bloqueado, ninguna IA externa puede desbloquear la ruta.
5. **Si algo no puede confirmarse en el código, marcarlo UNRESOLVED.** No inventar disponibilidad.
6. **El sandbox sigue aislado del sistema vivo.** No conectar SandboxExperimentService al runtime real.
7. **No fingir observación que no existe.** Solo lo que WorldModelService puede medir cuenta.
8. **No refactor masivo sin aprobación explícita.** Cambios pequeños y verificables.
9. **Presupuesto cero: local primero, gratis autenticado después, pagas bloqueadas.**

---

## VI. BACKLOG CRÍTICO PRIORIZADO (22 items pendientes, 6 críticos)

### Críticos (desbloquean autonomía real)

| ID | Título | Por qué es crítico |
|---|---|---|
| e1a2b4dd | Destrabar transición splash → shell | Startup falso-ready sigue activo |
| 541f94e2 | Handshake de readiness bridge ↔ UI | Cola de bridge sin respuesta |
| 8db889f0 | Selector soberano unificado | Sin esto, la elección de provider es parcial |
| d2ef6b17 | Rotación gobernada de cuentas y cuotas | Sin esto, el presupuesto cero no funciona |
| startup- | False-ready fix (in_progress) | Splash visible tras main_window |
| ControlCenterVM | Bloqueo 3733ms (no en backlog formal) | Confirmed blocker Responding@60s |

### High (capacidades esenciales)

| ID | Título |
|---|---|
| 32e1ee5b | Inventario vivo de sesiones/cuentas/cuotas en WorldModel |
| 9de52e89 | Integrar quota tracker al selector central |
| 0b8584c3 | Shadow learning local formal |
| 6b6b42f8 | Unificar marco de simbiosis IA-IA |
| 0a4af16a | Registrar interacciones con IAs como aprendizaje operativo |
| 331225c3 | Login gobernado y rotación de cuentas gratis |
| b0a9ad3f | Control soberano de auditorías multi-herramienta |
| 8ca9e3e4 | Supervisión y autoreinicio MCP + tunnel |
| 99438d57 | Autoauditoría live guiada desde UI |
| 487356fd | Aprender patrones de coordinación entre IAs |

---

## VII. MÉTRICAS DE AUTONOMÍA (a implementar en OSES)

Derivadas de la conversación con ChatGPT. Estas métricas deben calcularse y exponerse vía ControlMasterDigest para que cada sesión sepa qué tan autónomo está el sistema:

```python
# IABV Autonomy Index (propuesto para OSES + ControlMasterDigest)
AutonomyScore = (
    0.30 * capability_coverage +       # tasks completadas sin intervención / total
    0.25 * (1 - handoff_required_rate) + # 1 - (handoffs / total_tasks)
    0.20 * (1 - unresolved_ratio) +    # 1 - (unresolved_fields / total_fields)
    0.15 * (1 - permission_request_rate) + # 1 - (permisos pedidos / acciones críticas)
    0.10 * resume_success_rate         # tareas reanudadas / tareas interrumpidas
)  # Objetivo: > 0.80

ResilienceScore = (
    0.30 * (1 - mttp / baseline) +    # Mean Time To Provision
    0.30 * fallback_chain_coverage +   # alternativas disponibles
    0.25 * worker_diversity +          # workers distintos usados
    0.15 * checkpoint_coverage         # tareas con checkpoint
)  # Objetivo: > 0.75

CalibrationError = mean(|estimated_confidence - actual_success_rate|)
# Objetivo: < 0.10

BlindSpotRatio = unverified_findings / total_findings
# Objetivo: VerifiedRatio > 0.70
```

Estas métricas NO requieren código nuevo — se calculan desde datos que ExperimentLab, TaskOutcomeRecorder y DecisionAuditTrail ya tienen. OSES debe agregarlas a `_cloud_reasoning_findings()` como un hallazgo periódico.

---

## VIII. MARCO CIENTÍFICO (base teórica para evolución)

La conversación con ChatGPT exploró un marco formal para entender cuándo y cómo un sistema computacional desarrolla razonamiento. **No es código todavía, es la base conceptual para futuras decisiones de arquitectura.**

**Hipótesis central:**
> El razonamiento emerge cuando un sistema alcanza un régimen donde la compresión estructurada de información y la inferencia aproximada inducen representaciones capaces de soportar cómputo multi-step generalizable.

**Conjetura aplicable a IABV:**
```
d²R / dN² > 0  para  N > N_c
```
Donde N = evidencia acumulada (traces, sessions, corrections) y R = AutonomyScore.  
Predicción: existe un umbral N_c de evidencia acumulada donde la calidad de las decisiones del selector muestra un salto no lineal. La curva de aprendizaje del StrategySelector + AdaptiveWeightLayer debería evidenciar este umbral.

**Implicación arquitectónica:**
El sistema debe poder detectar cuándo cruzó N_c (por mejora abrupta en métricas) y registrarlo en ControlMasterDecision como hito evolutivo. Eso es "saber cuándo reestructurarse" — no por timer, sino por evidencia.

**Analogía termodinámica:**
- Entropía ↔ incertidumbre en WorldModelSnapshot (unresolved_fields count)
- Energía ↔ capability_coverage (más capabilities = más capacidad de trabajo)
- Mínimos ↔ configuraciones estables del selector (estrategias que convergen)
- Transición de fase ↔ umbral donde el sistema pasa de necesitar supervisión a operar solo

---

## IX. PLAN DE IMPLEMENTACIÓN — ORDEN CORRECTO

**Principio:** cambios pequeños, aditivos, con tests, sin romper capas cerradas.

### Fase 1 — Estabilidad (desbloquea Responding=True@60s)
**Archivo:** `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`  
**Cambio:** mover la inicialización pesada de `__init__` a `_initialize_heavy()`, llamarlo con `QTimer.singleShot(0)` post `setContextProperty`.  
**Por qué primero:** es el único bloqueante confirmado del main thread. Sin esto, la UI no responde y el resto de los avances son invisibles al usuario.  
**Riesgo:** bajo. El cambio es local al VM y no afecta servicios.

### Fase 2 — Cerrar el loop de cuota
**Archivo:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`  
**Cambio:** llamar `record_message_sent(packet.assistant_kind, packet.account_email)` inmediatamente antes del despacho a ruta externa. Solo si `budget_tier == 'free_authenticated'` y el packet tiene `account_email`.  
**Por qué segundo:** sin esto, el quota tracker existe pero no aprende. El selector seguirá usando workers ya agotados.  
**Riesgo:** bajo. Envuelto en try/except para que fallo de I/O no rompa la sesión.

### Fase 3 — worker_pool en WorldModelSnapshot
**Archivos:** `domain/models.py`, `world_model_service.py`  
**Cambio:** agregar campo `worker_pool_snapshot: dict = {}` a `WorldModelSnapshot`. En `_build_snapshot()`, llamar `estimate_available_workers()` con timeout de 2s.  
**Por qué tercero:** habilita que AutonomyGovernancePolicy tome decisiones reales de ruta basadas en cuota disponible, sin consultar el scanner ad-hoc desde el Orchestrator.  
**Riesgo:** medio. Agregar I/O al ciclo de monitoreo. Usar ThreadPoolExecutor con timeout.

### Fase 4 — AutonomyCycleService (si no fue mergeado)
**Archivo:** `src/iabv_v15/services/evolution/autonomy_cycle_service.py` (nuevo)  
**Cambio:** centralizar bridge_findings(), save_resume_hint(), seed_capabilities(), startup_summary(). OSES y TOR delegan con fallback inline.  
**Por qué cuarto:** consolida código disperso sin cambiar contratos externos. OSES y TOR mantienen fallback para compatibilidad con sesiones en vuelo.  
**Riesgo:** bajo-medio. El fallback garantiza que si el servicio falla, OSES y TOR siguen funcionando.

### Fase 5 — Resume-aware orchestration
**Archivo:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`  
**Cambio:** al arrancar, leer `startup_summary()` → si hay resume hints, presentarlos al usuario como "¿continuar tarea interrumpida?".  
**Por qué quinto:** cierra el loop de autonomía completo (percibir → decidir → ejecutar → verificar → aprender → **reanudar**).  
**Riesgo:** bajo. Es lectura de estado existente, no escritura nueva.

### Fase 6 — Selector unificado (backlog 8db889f0)
**Archivos:** `adaptive_model_selector.py`, `cloud_reasoning_planner.py`  
**Cambio:** agregar rutas web (chatgpt_web, claude_web) como candidatos formales del selector, excluidos cuando WorldModel tiene permission_gates activos o `worker_pool_snapshot` muestra cuota agotada.  
**Por qué sexto:** requiere Fase 3 (worker_pool en WorldModel) para funcionar correctamente.  
**Riesgo:** medio. Cambio al core del selector. Requiere tests: prioriza API gratis, excluye rate-limited, excluye web con permission_gate, cae a local.

### Fase 7 — UniversalAutonomyIndex en OSES
**Archivo:** `operational_self_examination_service.py`  
**Cambio:** agregar cálculo de AutonomyScore, ResilienceScore, CalibrationError, BlindSpotRatio en `_cloud_reasoning_findings()`. Exponer en ControlMasterDigest.  
**Por qué séptimo:** requiere datos acumulados de fases anteriores para tener valores significativos.  
**Riesgo:** bajo. Es cálculo sobre datos existentes, no nueva infraestructura.

---

## X. CÓMO USAR ESTE DOCUMENTO

### Para cualquier IA que empiece a trabajar

```bash
# Leer el estado actual del Control Master (siempre hacer primero)
PYTHONPATH=src python -m iabv_v15 cm export-digest --format markdown

# Ver backlog priorizado
cat data/evolution/backlog.json | python3 -c "
import json,sys
b=json.load(sys.stdin)
for i in b:
    if i.get('status') not in ('completed',):
        print(i.get('priority','?'), '|', i.get('status','?'), '|', str(i.get('title',''))[:70])
" | sort

# Ver OSES findings actuales
PYTHONPATH=src python3 scripts/run_self_audit.py --json

# Ver estado del startup
cat data/logs/startup_milestones_*.jsonl | tail -1
```

### Para actualizar el Control Master al cerrar sesión

```bash
# Registrar decisiones tomadas
PYTHONPATH=src python -m iabv_v15 cm record-decision \
  --summary "implementé X" \
  --reason "porque Y" \
  --status implemented \
  --affected-module "adaptive_task_orchestrator"

# Marcar objetivos completados
PYTHONPATH=src python -m iabv_v15 cm mark-objective obj-id completed

# Agregar UNRESOLVED
PYTHONPATH=src python -m iabv_v15 cm mark-unresolved "texto del unresolved"
```

### Regla de oro para cada sesión de trabajo

1. Leer `cm export-digest --format markdown` primero
2. Leer AGENTS.md si vas a tocar un módulo nuevo
3. Antes de proponer un cambio: verificar que no viola ninguna de las 9 reglas irrevocables
4. Si algo no está en el código, marcarlo UNRESOLVED — no inventarlo
5. Al terminar: actualizar el Control Master con lo que cambiaste y por qué

---

## XI. UNRESOLVED ACTIVOS

| ID | Descripción |
|---|---|
| U1 | AutonomyCycleService: ¿fue mergeado del PR #307 o está solo en la rama devin/1777750256? No confirmado en 7z |
| U2 | CPU frequency: `UNRESOLVED:cpu_frequency` en EnvironmentSelfModel (última lectura: 2026-05-02) |
| U3 | Control Master state no actualizado desde 2026-04-19 — los 4 objetivos activos pueden estar desactualizados |
| U4 | lazy_vm_prebuild_done nunca disparó en 120s — ¿QTimer de 15s bloqueado por event loop? |
| U5 | pageLoader QML síncrono causa freeze de 28s — causa raíz dentro de QML loader, no en Python |
| U6 | Verificación visual real de splash y ventana principal requiere permiso explícito de observación |
| U7 | Corpus de entrenamiento derivado de traces: diseñado en Codex pero no implementado |
| U8 | Login humano, captcha y 2FA de terceros: no automatizable por definición — siempre requerirá interacción |

---

## XII. VISIÓN DE AUTONOMÍA — ESTADO ACTUAL vs OBJETIVO

| Dimensión | Estado actual | Objetivo |
|---|---|---|
| **Arranque** | Responding=True@30s, False@60s | Responding=True en todo el ciclo |
| **Elección de proveedor** | APIs conocidas, no web sessions, no cuota real | Selector unificado con WorldModel como árbitro |
| **Cuota/presupuesto** | Scanner existe, no se alimenta | Cuota actualizada en tiempo real, bloqueante de ruta |
| **Resume de tareas** | Infraestructura existe, nadie la consume | Orchestrator ofrece "continuar" al arrancar |
| **Aprendizaje IA-IA** | Solo dual-brain del classifier | Shadow mode formal en razonamiento principal |
| **Métricas de autonomía** | No existen en código | AutonomyScore > 0.80 como objetivo medible |
| **Control Maestro** | Implementado, desactualizado | Actualizado en cada sesión, fuente de verdad viva |
| **Reestructuración adaptativa** | Manual (Devin, Windsurf, Codex) | Autodetección del umbral N_c → registrar como hito |

---

*Última actualización de este documento: 2026-05-03 por análisis de Claude Sonnet 4.6 sobre: IABV_v1_5.7z, chatwindsurf.txt, chatgpt.txt, chatCodex.txt, ARCHITECTURE_REPORT_V5.md, PROMPT_WINDSURF_AUDIT_PR307_V5.md*
