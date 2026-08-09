# AUDITORÍA COMPLETA DE ARQUITECTURA EXISTENTE - IABV v1.5

**Fecha:** 2025-01-XX
**Objetivo:** Descubrir la arquitectura real existente para memoria compartida, visión, metacognición e investigación autónoma antes de implementar cualquier nuevo componente.

---

## 1. MAPA ACTUAL DE MEMORIA

### Fuentes de memoria persistente existentes

| Memoria | Archivo | Servicio | Estado | Contenido |
|---------|---------|----------|--------|----------|
| **Preferencias persistentes** | `data/evolution/human_preferences/preferences.jsonl` | `LocalRoleRouter._apply_persisted_human_preferences()` | REAL | Preferencias de asistente por scope (task, site, general) |
| **Aprobaciones** | `data/evolution/approval_memory/` | `ApprovalMemory` | REAL | Políticas explícitas de aprobación humana |
| **Patrones de interacción** | `data/tool_teaching/interaction_patterns/` | `InteractionLearningService` | REAL | Patrones de uso de herramientas (InteractionPattern) |
| **Enseñanzas** | `data/tool_teaching/teaching_episodes/` | `BrowserLearningAssembler` | REAL | Sesiones de enseñanza de navegación (TeachingEpisode) |
| **Conocimiento general** | `data/knowledge/items/` | `UnifiedMemoryLayer.remember_run()` | REAL | KnowledgeItem con learning_type (NUEVO P1) |
| **Validaciones de reproducibilidad** | `data/evolution/reproducibility_validations/validations.jsonl` | `ReproducibilityValidationService` | REAL (NUEVO P1) | ReproducibilityValidationResult |
| **Interacción humana** | `data/evolution/human_interaction/surface.json` | `HumanInteractionSurfaceService` | REAL (NUEVO P0) | HumanInteractionSurface |
| **Gobernanza humana** | `data/evolution/human_governance/boundary.json` | `HumanGovernanceBoundaryService` | REAL (NUEVO P0) | HumanGovernanceBoundary |
| **Experimentos** | `data/experiment_lab/` | `ExperimentLab` | REAL | ExperimentRun (comparaciones, pruebas) |
| **Sesiones adaptativas** | `data/adaptive_sessions/` | `AdaptiveSessionRepository` | REAL | AdaptiveSession (sesiones de trabajo) |
| **Decision audit trail** | `data/evolution/decision_audit/decisions.jsonl` | `DecisionAuditTrail` | REAL | Registro de decisiones cloud |
| **Autoexaminación** | `data/evolution/self_examination/latest.json` | `OperationalSelfExaminationService` | REAL | SelfExaminationSnapshot |
| **Contexto portable** | `data/evolution/portable_context/latest.json` | `PortableContextService` | REAL | PortableContextPackage |
| **Backlog de evolución** | `data/evolution/backlog.json` | `evolution_backlog` | REAL | Lista de tareas pendientes de evolución |
| **Cola de tareas pendientes** | `data/platform_pending/` | `PlatformPendingQueue` | REAL | PlatformPendingTask |

### Evidencia de memoria compartida entre agentes

**Archivo:** `data/evolution/portable_context/latest.json`
- **Estado:** REAL
- **Servicio:** `PortableContextService.build_package()`
- **Secciones:**
  - `project_state` - Objetivo activo, proyecto activo, tarea activa, pulso evolutivo
  - `architecture` - Arquitectura central vigente (perception → orchestrator → governance → ejecución → aprendizaje)
  - `implemented_capabilities` - Capas cerradas (P1 World Model, P2 Neuroplasticidad, P3 Contexto portable)
  - `tool_discovery` - Señales de descubrimiento de herramientas
  - `cloud_reasoning` - Health score, trends y recomendaciones cloud
  - `learning` - Interaction patterns, knowledge hits, capabilities, experiment insights
  - `evidence` - Evidencia refs, recent teachings, incidents, dossiers
  - `operational` - Recent runs, session readiness, live audit

**Conclusión:** `PortableContextService` ya es la fuente compartida de contexto para nuevas sesiones. Cualquier IA nueva puede leer `latest.json` y entender el estado del proyecto sin que el humano repita todo.

---

## 2. MAPA ACTUAL DE VISIÓN

### ¿Existe algún componente que conserve visión del sistema?

**Parcialmente SÍ.**

| Componente | Archivo | Servicio | Estado | Contenido |
|------------|---------|----------|--------|----------|
| **Visión del proyecto** | `AGENTS.md` | Documento | REAL | Identidad del proyecto, arquitectura central, capas cerradas |
| **Estado del proyecto** | `data/evolution/portable_context/latest.json` (sección `project_state`) | `PortableContextService` | REAL | Objetivo activo, proyecto activo, tarea activa, pulso evolutivo |
| **Arquitectura** | `data/evolution/portable_context/latest.json` (sección `architecture`) | `PortableContextService` | REAL | Componentes wired, status de cada pieza |
| **Capacidades implementadas** | `data/evolution/portable_context/latest.json` (sección `implemented_capabilities`) | `PortableContextService` | REAL | P1, P2, P3, Monitor de evolución, Sandbox, Contexto portable |

### ¿Qué falta de visión?

- ❌ **No existe un modelo explícito de "Visión del proyecto"** (objetivo mayor, misión, principios, restricciones, roadmap)
- ❌ **No existe un modelo explícito de "Estado de la fase"** (qué fase estamos en el panorama, qué hemos cerrado, qué falta)
- ❌ **No existe un modelo explícito de "Decisiones arquitectónicas"** (por qué se tomó cada decisión)
- ❌ **No existe un modelo explícito de "Próximos pasos"** (qué deberíamos hacer después del aprendizaje actual)

**Nota:** `AGENTS.md` tiene identidad y arquitectura, pero NO tiene visión estratégica (objetivo mayor, roadmap, próximos pasos). `PortableContextService` tiene estado operativo pero NO tiene visión estratégica.

---

## 3. MAPA ACTUAL DE METACOGNICIÓN

### ¿Existe algún mecanismo para representar qué sabe/no sabe IABV?

**SÍ, pero parcial.**

| Componente | Archivo | Servicio | Estado | Contenido |
|------------|---------|----------|--------|----------|
| **Autoexaminación operativa** | `data/evolution/self_examination/latest.json` | `OperationalSelfExaminationService.current_review()` | REAL | Hallazgos de degradación, patrones repetidos, ajustes recomendados |
| **WorldModelSnapshot** | En memoria y disco | `WorldModelService` | REAL | Panorama operativo vivo (ventanas, foco, herramientas, red, bloqueos) |
| **EnvironmentSelfModel** | En memoria y disco | `EnvironmentSelfAwarenessService` | REAL | Estado de hardware, runtime y riesgos del entorno |
| **DecisionAuditTrail** | `data/evolution/decision_audit/decisions.jsonl` | `DecisionAuditTrail` | REAL | Registro de decisiones cloud (proveedor, latencia, confianza, resultado, tendencia) |
| **ExperimentLab** | `data/experiment_lab/` | `ExperimentLab` | REAL | Memoria de resultados y recomendaciones |

### ¿Qué representa OSES actualmente?

**Archivo:** `data/evolution/self_examination/latest.json`
- **Hallazgos típicos:**
  - `_background_decision_review_findings()` - proveedores con tasa de éxito baja, decisiones de baja confianza que fallan
  - `_temporal_awareness_findings()` - anomalías de latencia, regresión de latencia, operaciones estancadas
  - `_deep_analysis_queue_findings()` - EMA drift detection, fallos correlacionados, outliers de latencia
  - `_cloud_reasoning_findings()` - tendencias por proveedor cloud, degradaciones
  - `_interaction_learning_findings()` - patrones de interacción que necesitan corrección
  - `_tool_evolution_findings()` - propuestas de cambio en herramientas

### ¿Qué falta de metacognición?

- ❌ **No existe modelo explícito de "qué sabe" vs "qué no sabe"** (catalogo de conocimientos vs gaps)
- ❌ **No existe modelo explícito de "qué cree saber" vs "qué fue validado"** (distinguir hipótesis de conocimiento validado)
- ❌ **No existe modelo explícito de "qué fue refutado"** (catalogo de hipótesis descartadas)
- ❌ **No existe modelo explícito de "qué necesita investigar"** (lista priorizada de gaps de conocimiento)

---

## 4. MAPA ACTUAL DE ORIGEN DEL CONOCIMIENTO

### ¿Cómo distingue actualmente el sistema el origen del conocimiento?

**NUEVO P0:** `HumanInteractionType` enum en `domain/models.py`
- `PREFERENCE` - preferencia persistente
- `TEACHING` - enseñanza humana
- `CONVERSATION` - conversación normal
- `INSTRUCTION` - instrucción operacional
- `APPROVAL` - aprobación humana
- `GOVERNANCE` - decisión de gobernanza
- `DISCOVERY` - conocimiento descubierto por investigación
- `DEDUCTION` - deducción propia

**NUEVO P1:** `KnowledgeItem.learning_type` (str)
- Campo para etiquetar tipo de aprendizaje en KnowledgeItem

**Estado de uso:**
- ✅ El enum existe
- ✅ El campo existe
- ❌ **NO se usa sistemáticamente en el loop de aprendizaje**
- ❌ `ReproducibilityValidationService` NO valida o distingue por tipo de origen
- ❌ `UnifiedMemoryLayer.remember_run()` NO asigna learning_type automáticamente
- ❌ `InteractionLearningService` NO asigna learning_type a KnowledgeItem

### Flujo real de origen del conocimiento

**Enseñanza humana:**
1. Humano enseña vía CaptureStudio
2. `BrowserLearningAssembler` crea `TeachingEpisode`
3. `InteractionLearningService.learn_from_teaching_session()` crea `InteractionPattern` con `metadata['source'] = 'teaching_session'`
4. ❌ `KnowledgeItem` NO se crea automáticamente desde enseñanza

**Experiencia normal:**
1. Tarea se ejecuta
2. `TaskOutcomeRecorder._record_learning()` registra en `ExperimentLab`
3. `UnifiedMemoryLayer.remember_run()` crea `KnowledgeItem`
4. ❌ `learning_type` NO se asigna automáticamente (queda None)

**Investigación:**
1. `SandboxExperimentService` crea experimento con hipótesis
2. Resultado se registra en `ExperimentLab`
3. ❌ NO se crea `KnowledgeItem` con `learning_type='discovery'`

### Qué falta de origen del conocimiento

- ❌ NO hay sistema que asigne `learning_type` automáticamente basado en origen
- ❌ NO hay sistema que distinga entre hipótesis (antes de experimento) y conocimiento validado (después de experimento)
- ❌ NO hay sistema que etiquete conocimiento como "refutado"
- ❌ NO hay sistema que etiquete recomendaciones vs deduciones propias

---

## 5. MAPA ACTUAL DE CICLO DE APRENDIZAJE

### Flujo actual: humano enseña → conocimiento → memoria → reproducción → validación

```
Humano enseña (CaptureStudio)
  ↓
BrowserTeachSessionService.captura pasos
  ↓
BrowserLearningAssembler.ensambla TeachingEpisode
  ↓
InteractionLearningService.learn_from_teaching_session()
  → Crea InteractionPattern con metadata['source'] = 'teaching_session'
  → Guarda en ToolRecordRepository
  ❌ NO crea KnowledgeItem automáticamente
  ↓
ReproducibilityValidationService.validate_interaction_pattern()
  → Calcula success_rate basado en success_count/failure_count
  → Decide si reproduction_successful (success_rate >= 0.7 AND success_count >= 2)
  → Guarda ReproducibilityValidationResult en validations.jsonl
  ❌ NO genera siguiente hipótesis o tarea automáticamente
```

### Flujo actual: hipótesis → experimento → resultado → validación → aprendizaje

```
ExperimentLab (o SandboxExperimentService)
  ↓
Crea hipótesis: "Validar si X sigue siendo la mejor vía para Y"
  ↓
Ejecuta experimento sandbox
  ↓
Recorda resultado en ExperimentLab (ExperimentRun)
  ↓
AutonomousValidationCycleService.revisa candidatos
  → Promueve si evidence_strength suficiente
  ❌ NO crea KnowledgeItem con learning_type='discovery'
  ❌ NO genera siguiente hipótesis automáticamente
  ↓
TaskOutcomeRecorder._record_learning()
  → Registra learning en ExperimentLab desde sesiones adaptativas
  ❌ NO genera siguiente tarea de evolución automáticamente
```

### Puntos donde el flujo se rompe

1. **Enseñanza → KnowledgeItem:** `InteractionLearningService` NO crea `KnowledgeItem` automáticamente
2. **Validación → siguiente hipótesis:** `ReproducibilityValidationService` es endpoint final, NO genera siguiente investigación
3. **Validación → tarea de evolución:** NO hay conexión desde `ReproducibilityValidationResult` → `evolution_backlog.add_task()`
4. **Experimento → KnowledgeItem:** `AutonomousValidationCycleService` NO crea `KnowledgeItem` con `learning_type='discovery'`
5. **Aprendizaje → siguiente tarea:** NO hay servicio que tome conocimiento validado y genere siguiente tarea automáticamente

---

## 6. MAPA ACTUAL DE ACTUALIZACIÓN DE VISIÓN

### ¿Existe mecanismo para actualizar visión después de aprendizaje significativo?

**NO.**

- ❌ NO existe modelo de "Visión del proyecto" que se pueda actualizar
- ❌ `PortableContextService` actualiza estado operativo (objetivo activo, pulso evolutivo) pero NO visión estratégica
- ❌ `OperationalSelfExaminationService` actualiza hallazgos operativos pero NO visión estratégica
- ❌ NO existe mecanismo que diga "Esto cambió lo que sabemos del proyecto"

**Existe:**
- ✅ `PortableContextService.build_package()` - actualiza estado operativo cada vez que se llama
- ✅ `evolution_backlog.add_task()` - puede agregar tareas pero NO actualiza visión
- ✅ `evolution_backlog.deduce_priorities()` - reprioriza tareas basado en environment_scan pero NO actualiza visión

---

## 7. MAPA ACTUAL DE SIGUIENTE OBJETIVO

### ¿Cómo decide IABV actualmente "¿Qué debería hacer ahora?"

**Múltiples autoridades dispersas:**

| Autoridad | Archivo | Servicio | Estado | Criterio de decisión |
|----------|---------|----------|--------|-------------------|
| **evolution_backlog** | `data/evolution/backlog.json` | `evolution_backlog.get_pending_tasks()` | REAL | Lista de tareas pendientes ordenadas por prioridad |
| **PlatformPendingQueue** | `data/platform_pending/` | `PlatformPendingQueue.list_actionable()` | REAL | Tareas de plataforma (missing_tool, permission_required, investigation) |
| **ToolDiscoveryService** | En memoria y disco | `ToolDiscoveryService.build_status()` | REAL | Señales de descubrimiento de herramientas |
| **ExperimentLab** | `data/experiment_lab/` | `ExperimentLab` | REAL | Resultados de experimentos y recomendaciones |
| **StrategySelector** | En memoria y disco | `StrategySelector` | REAL | Recomendaciones de estrategia basadas en historial |
| **AutonomousValidationCycleService** | En memoria y disco | `AutonomousValidationCycleService` | REAL | Valida candidatos y promueve si tienen evidencia |

### ¿Existe una autoridad unificada?

**NO.**

- ❌ NO hay un servicio que coordine entre estas autoridades
- ❌ NO hay un "Scheduler" central que seleccione el siguiente paso
- ❌ NO hay un "ResearchOrchestrator" que coordine investigación autónoma
- ❌ Cada autoridad decide independientemente sin coordinación

---

## 8. MAPA ACTUAL DE INVESTIGACIÓN AUTÓNOMA

### Paso a paso del comportamiento de investigación autónoma

| Paso | Estado | Evidencia |
|------|--------|----------|
| 1. Detectar gap | PARCIAL | `OperationalSelfExaminationService` detecta degradaciones, `ToolEvolutionMonitor` detecta gaps de herramientas |
| 2. Formular pregunta | INEXISTENTE | NO hay servicio que formule preguntas explícitas |
| 3. Formular hipótesis | PARCIAL | `SandboxExperimentService` genera hipótesis solo para validar rutas existentes |
| 4. Decidir qué investigar | INEXISTENTE | NO hay servicio que decida qué investigar automáticamente |
| 5. Elegir herramienta | PARCIAL | `ToolDiscoveryService` genera señales pero NO elige automáticamente |
| 6. Investigar | INEXISTENTE | NO hay servicio que ejecute investigación autónoma más allá de sandbox |
| 7. Experimentar | PARCIAL | `SandboxExperimentService` ejecuta solo en sandbox |
| 8. Evaluar resultado | REAL | `ExperimentLab` registra resultados |
| 9. Validar | REAL | `AutonomousValidationCycleService` valida candidatos |
| 10. Aprender | PARCIAL | `TaskOutcomeRecorder` registra learning en ExperimentLab, `UnifiedMemoryLayer` crea KnowledgeItem |
| 11. Actualizar memoria | REAL | Todas las memorias se actualizan cuando se usan |
| 12. Actualizar visión | INEXISTENTE | NO hay mecanismo para actualizar visión estratégica |
| 13. Crear siguiente tarea | INEXISTENTE | NO hay conexión automática desde aprendizaje → siguiente tarea |
| 14. Repetir | INEXISTENTE | NO hay loop completo |

---

## 9. QUÉ PUEDE HACER IABV SIN CONSTRUIR NADA

1. ✅ **Leer estado persistente del proyecto** - `PortableContextService.latest.json` contiene estado operativo, arquitectura, capacidades, descubrimiento de herramientas
2. ✅ **Distinguir tipos de interacción humana** - `HumanInteractionType` enum existe (P0)
3. ✅ **Validar reproducibilidad de aprendizaje** - `ReproducibilityValidationService` existe (P1)
4. ✅ **Registrar aprendizaje con metadata de tipo** - `KnowledgeItem.learning_type` existe (P1)
5. ✅ **Mantener superficie de interacción humana** - `HumanInteractionSurfaceService` existe (P0)
6. ✅ **Mantener frontera de gobernanza humana** - `HumanGovernanceBoundaryService` existe (P0)
7. ✅ **Ejecutar experimentos sandbox** - `SandboxExperimentService` + `AutonomousValidationCycleService`
8. ✅ **Registrar resultados de experimentos** - `ExperimentLab`
9. ✅ **Generar tareas de evolución** - `evolution_backlog.add_task()` existe
10. ✅ **Priorizar tareas automáticamente** - `evolution_backlog.deduce_priorities()` existe
11. ✅ **Descubrir herramientas** - `ToolDiscoveryService` existe
12. ✅ **Autoexaminarse operativamente** - `OperationalSelfExaminationService` existe
13. ✅ **Exportar contexto portable** - `PortableContextService` existe

---

## 10. QUÉ NO PUEDE HACER IABV TODAVÍA

1. ❌ **Actualizar visión estratégica del proyecto** - NO existe modelo de visión que se pueda actualizar
2. ❌ **Asignar learning_type automáticamente** - NO hay sistema que asigne tipo de origen al conocimiento
3. ❌ **Distinguir hipótesis de conocimiento validado** - NO hay modelo para este estado
4. ❌ **Etiquetar conocimiento refutado** - NO hay modelo para este estado
5. ❌ **Validar → siguiente hipótesis** - `ReproducibilityValidationService` es endpoint final
6. ❌ **Validación → tarea de evolución** - NO hay conexión automática
7. ❌ **Aprendizaje → siguiente tarea** - NO hay loop automático
8. ❌ **Decidir qué investigar automáticamente** - NO hay servicio que coordine esta decisión
9. ❌ **Elegir herramienta automáticamente** - `ToolDiscoveryService` solo genera señales
10. ❌ **Actualizar visión después de aprendizaje** - NO hay mecanismo
11. ❌ **Coordinar autoridades múltiples** - NO hay scheduler central

---

## 11. QUÉ PIEZA MÍNIMA FALTA

**Hueco exacto:**

Falta un **puente de coordinación** que conecte el loop de aprendizaje con el loop de investigación y generación de tareas.

**Especificación mínima:**

Un servicio (o extensión de uno existente) que:

1. **Consuma `ReproducibilityValidationResult`** cuando `reproduction_successful=True`
2. **Genera hipótesis siguiente** basada en el conocimiento validado
3. **Llama a `evolution_backlog.add_task()`** para crear tarea de evolución
4. **Opcionalmente llama a `ToolDiscoveryService`** para sugerir nueva herramienta
5. **Extiende `KnowledgeItem`** para asignar `learning_type` automáticamente desde origen

**NO debe ser:**
- ❌ Un nuevo scheduler global (usar autoridades existentes)
- ❌ Una nueva memoria (usar `evolution_backlog` existente)
- ❌ Un nuevo observador (usar `OperationalSelfExaminationService` existente)
- ❌ Un ResearchOrchestrator completo (primero cerrar el puente mínimo)

**Debe ser:**
- ✅ Un puente ligero que conecte piezas existentes
- ✅ Posible implementación como extensión de `ReproducibilityValidationService` o como servicio nuevo simple
- ✅ Que use `evolution_backlog` como autoridad para tareas
- ✅ Que use `ToolDiscoveryService` para sugerencias
- ✅ Que NO cree nuevas autoridades globales

---

## 12. QUÉ NO DEBEMOS CONSTRUIR

1. ❌ **NO crear ResearchOrchestrator** - Primero cerrar el puente mínimo entre piezas existentes
2. ❌ **NO crear nueva memoria** - Usar `evolution_backlog`, `ExperimentLab`, `KnowledgeRepository` existentes
3. ❌ **NO crear nuevo scheduler** - Usar autoridades existentes (`evolution_backlog`, `PlatformPendingQueue`)
4. ❌ **NO crear nuevo observador** - Usar `OperationalSelfExaminationService` existente
5. ❌ **NO duplicar `StrategySelector` o `ExperimentLab` - Ya existen
6. ❌ **NO duplicar `PortableContextService` - Ya es la fuente compartida de contexto
7. ❌ **NO duplicar `UnifiedMemoryLayer` - Ya maneja memoria de conocimiento
8. ❌ **NO crear "Visión del Proyecto" completo** - Primero cerrar el loop de investigación básico

---

## 13. DEPENDENCIAS DE LA SIGUIENTE FASE

**Para cerrar el loop de investigación autónoma:**

1. Implementar puente `ReproducibilityValidationResult` → hipótesis → `evolution_backlog.add_task()`
2. Extender `KnowledgeItem` para asignar `learning_type` automáticamente desde origen
3. Conectar aprendizaje → siguiente tarea automáticamente
4. Probar el loop completo: validación → hipótesis → tarea → experimento → validación

**Para actualización de visión (futura, no inmediata):**

1. Definir modelo de "Visión del Proyecto" (objetivo mayor, misión, principios, restricciones, roadmap)
2. Conectar `OperationalSelfExaminationService` para actualizar visión después de hallazgos significativos
3. Probar que IABV puede decir "Esto cambió lo que sabemos del proyecto"

---

## 14. PROMPT RECOMENDADO PARA LA SIGUIENTE IA

**Contexto:** La auditoría completó que las piezas de memoria, validación, experimentación y tareas existen pero están parcialmente desconectadas. El puente mínimo falta conectar validación de reproducibilidad con generación de hipótesis y tareas de evolución.

**Prompt recomendado:**

> "Implementa el puente mínimo que conecte el loop de investigación autónoma. Extiende `ReproducibilityValidationService` o crea un servicio simple `ResearchBridgeService` que:
> 
> 1. Consuma `ReproducibilityValidationResult` cuando `reproduction_successful=True`
> 2. Genera hipótesis siguiente basada en el conocimiento validado (ej: 'Validar si X funciona para Y')
> 3. Llama a `evolution_backlog.add_task()` para crear tarea de evolución con la hipótesis
> 4. Opcionalmente llama a `ToolDiscoveryService` para sugerir nueva herramienta si aplica
> 5. Extiende `UnifiedMemoryLayer.remember_run()` para asignar `learning_type` automáticamente basado en origen (teaching, discovery, deduction)
> 
> NO crees un ResearchOrchestrator completo. Solo el puente mínimo que conecte piezas existentes. Usa `evolution_backlog` como autoridad para tareas, `ToolDiscoveryService` para sugerencias, y `ExperimentLab` para experimentos. NO crees nuevas memorias ni autoridades globales."

---

## RESPUESTA A LAS DOS PREGUNTAS CRÍTICAS

### 1. "Si mañana entra una IA nueva al proyecto, ¿puede leer el estado persistente de IABV y entender qué estamos intentando construir, qué ya aprendimos, qué falta, qué se intentó, qué funcionó, qué no funcionó y cuál debería ser el siguiente paso?"

**Respuesta:**
- ✅ **SÍ** - Puede leer `PortableContextService.latest.json` y entender:
  - Objetivo activo actual
  - Arquitectura central vigente
  - Capacidades implementadas (P1, P2, P3)
  - Estado de WorldModel, EnvironmentSelfModel
  - Descubrimiento de herramientas
  - Hallazgos de autoexaminación
  - Learning y experiment insights
  - Backlog de evolución
  - Cola de tareas pendientes
- ❌ **NO** - No puede entender:
  - Visión estratégica del proyecto (objetivo mayor, misión, roadmap)
  - Qué fase del panorama estamos en
  - Decisiones arquitectónicas (por qué se tomó cada decisión)
  - Próximos pasos estratégicos (más allá de backlog de tareas técnicas)

### 2. "Si IABV aprende algo nuevo mediante una interacción humana o investigación autónoma, ¿puede incorporarlo a su memoria, validarlo, deducir consecuencias, actualizar su visión y generar la siguiente tarea coherente con el objetivo mayor?"

**Respuesta:**
- ✅ **SÍ** - Puede:
  - Incorporar a memoria (`KnowledgeRepository`, `ToolRecordRepository`, `ExperimentLab`)
  - Validar reproducibilidad (`ReproducibilityValidationService`)
- ❌ **NO** - No puede:
  - Deducir consecuencias automáticamente
  - Actualizar visión estratégica
  - Generar siguiente tarea coherente con objetivo mayor (loop roto)

---

## CONCLUSIÓN

**Estado actual:** Las piezas de memoria, validación, experimentación y tareas existen pero están parcialmente desconectadas. Existe una fuente compartida de contexto (`PortableContextService`) que permite que nuevas IAs entiendan el estado operativo del proyecto, pero falta visión estratégica.

**Hueco mínimo:** Un puente ligero que conecte `ReproducibilityValidationResult` → hipótesis → `evolution_backlog.add_task()` sin crear nuevas autoridades globales.

**NO implementar:** ResearchOrchestrator, nueva memoria, nuevo scheduler, nuevo observador, modelo completo de visión. Primero cerrar el puente mínimo.
