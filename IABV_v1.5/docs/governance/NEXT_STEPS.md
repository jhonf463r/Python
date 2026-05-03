# IABV v1.5 — Siguientes Pasos

**Actualizado:** 2026-05-03

---

## ~~Fase 1 — Estabilidad del Arranque~~ COMPLETADA

### ControlCenterVM lazy init — IMPLEMENTADO
**Archivo:** `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`  
**Cambio realizado:** Heavy I/O movido a `_bg_initial_refresh()` via `_bg_pool.submit()`. Resultado aplicado en main thread via `taskResolved` signal. `QTimer.singleShot(0, self._initialize_heavy)` reemplaza `QTimer.singleShot(250, self.refresh)`.  
**Tests post-fix:** 2391 passed / 29 failed / 25 skipped — 0 regresiones nuevas.

---

## ~~Fase 2 — Cerrar el Loop de Cuota~~ COMPLETADA

### Quota tracker wiring — IMPLEMENTADO
**Archivo:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`  
**Cambio realizado:** `_record_quota_usage()` y `_record_quota_usage_for_candidate()` llaman `record_message_sent(tool, email)` antes de cada `plan_or_execute()`. Extraen tool de governance y email del worker_gate.  
**Tests:** 2391 passed / 29 failed / 25 skipped — 0 regresiones.

---

## ~~Fase 3 — worker_pool en WorldModelSnapshot~~ COMPLETADA

### worker_pool_snapshot — IMPLEMENTADO
**Archivos:** `domain/models.py`, `world_model_service.py`  
**Cambio realizado:** Campo `worker_pool_snapshot: dict = {}` en `WorldModelSnapshot`. `_estimate_worker_pool(timeout_s=2.0)` usa ThreadPoolExecutor. Solo en scans `full`.  
**Tests:** 2391 passed / 29 failed / 25 skipped — 0 regresiones.

---

## Paso Inmediato Recomendado: Fase 4 — AutonomyCycleService

### Centralizar bridge_findings, resume hints, seed capabilities
**Archivo:** `src/iabv_v15/services/evolution/autonomy_cycle_service.py` (nuevo)  
**Cambio:** Centralizar funcionalidad dispersa en OSES y TOR. OSES y TOR delegan con fallback inline.  
**NOTA:** UNRESOLVED (U1). Requiere confirmación del responsable del proyecto antes de implementar.  
**Riesgo:** Bajo-Medio. Requiere definir interfaz y migrar gradualmente.  
**Estimación:** 1-2 sesiones de agente.

---

## Orden de Trabajo Recomendado

| Fase | Qué hacer | Dependencia | Riesgo |
|---|---|---|---|
| ~~1~~ | ~~ControlCenterVM lazy init~~ | ~~Ninguna~~ | ~~Completado~~ |
| ~~2~~ | ~~Quota tracker wiring en ATO~~ | ~~Ninguna~~ | ~~Completado~~ |
| ~~3~~ | ~~worker_pool_snapshot en WorldModel~~ | ~~Ninguna~~ | ~~Completado~~ |
| 4 | AutonomyCycleService (si se confirma U1) | Confirmar U1 | Bajo-Medio |
| 5 | Resume-aware orchestration | Fase 4 | Bajo |
| 6 | Selector unificado (backlog 8db889f0) | Fase 3 | Medio |
| 7 | UniversalAutonomyIndex en OSES | Fases 1-6 acumulan datos | Bajo |

---

## Cómo Arrancar una Sesión de Continuación

```bash
# 1. Leer este handoff + docs de gobernanza
cat docs/governance/SESSION_HANDOFF.md
cat docs/governance/NEXT_STEPS.md
cat docs/governance/UNRESOLVED_REGISTRY.md

# 2. Leer el estado del Control Master
PYTHONPATH=src python -m iabv_v15 cm export-digest --format markdown

# 3. Leer AGENTS.md (siempre antes de tocar código)
cat AGENTS.md

# 4. Correr tests para confirmar baseline
PYTHONPATH=src python -m pytest tests/ -q --tb=no

# 5. Empezar por la fase que corresponda
```

---

## Criterio de Cierre por Sesión

Al terminar cada sesión:
1. Actualizar `docs/governance/SESSION_HANDOFF.md`
2. Actualizar `docs/governance/DECISION_LOG.md` con decisiones tomadas
3. Actualizar `docs/governance/UNRESOLVED_REGISTRY.md` si aparecieron nuevos
4. Actualizar `docs/governance/TESTS_STATE.md` con nueva corrida
5. Registrar decisiones en Control Master vía CLI:
   ```bash
   PYTHONPATH=src python -m iabv_v15 cm record-decision \
     --summary "implementé X" --reason "porque Y" \
     --status implemented --affected-module "nombre_modulo"
   ```
6. Commit trazable con mensaje descriptivo
