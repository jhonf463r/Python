# IABV v1.5 — Siguientes Pasos

**Actualizado:** 2026-05-03

---

## ~~Fase 1 — Estabilidad del Arranque~~ COMPLETADA

### ControlCenterVM lazy init — IMPLEMENTADO
**Archivo:** `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`  
**Cambio realizado:** Heavy I/O movido a `_bg_initial_refresh()` via `_bg_pool.submit()`. Resultado aplicado en main thread via `taskResolved` signal. `QTimer.singleShot(0, self._initialize_heavy)` reemplaza `QTimer.singleShot(250, self.refresh)`.  
**Tests post-fix:** 2391 passed / 29 failed / 25 skipped — 0 regresiones nuevas.

---

## Paso Inmediato Recomendado: Fase 2 — Cerrar el Loop de Cuota

### Quota tracker wiring
**Archivo:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`  
**Cambio:** Llamar `record_message_sent(packet.assistant_kind, packet.account_email)` inmediatamente antes del despacho a ruta externa. Solo si `budget_tier == 'free_authenticated'` y el packet tiene `account_email`.  
**Por qué ahora:** Sin esto, el quota tracker existe pero no aprende. El selector seguirá usando workers ya agotados.  
**Riesgo:** Bajo. Envuelto en try/except.  
**Estimación:** 1 sesión de agente.

---

## Orden de Trabajo Recomendado

| Fase | Qué hacer | Dependencia | Riesgo |
|---|---|---|---|
| ~~1~~ | ~~ControlCenterVM lazy init~~ | ~~Ninguna~~ | ~~Completado~~ |
| 2 | Quota tracker wiring en ATO | Ninguna | Bajo |
| 3 | worker_pool_snapshot en WorldModel | Ninguna | Medio |
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
