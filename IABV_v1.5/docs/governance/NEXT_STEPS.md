# IABV v1.5 — Siguientes Pasos

**Actualizado:** 2026-05-03

---

## Paso Inmediato Recomendado: Fase 1 — Estabilidad del Arranque

### ControlCenterVM lazy init
**Archivo:** `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`  
**Cambio:** Mover la inicialización pesada de `__init__` a `_initialize_heavy()`, llamarlo con `QTimer.singleShot(0)` post `setContextProperty`.  
**Por qué primero:** Es el único bloqueante confirmado del main thread. Sin esto, la UI no responde y el resto de los avances son invisibles al usuario.  
**Riesgo:** Bajo. El cambio es local al VM y no afecta servicios.  
**Estimación:** 1 sesión de agente.

---

## Orden de Trabajo Recomendado

| Fase | Qué hacer | Dependencia | Riesgo |
|---|---|---|---|
| 1 | ControlCenterVM lazy init | Ninguna | Bajo |
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
