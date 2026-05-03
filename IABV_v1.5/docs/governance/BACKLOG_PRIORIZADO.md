# IABV v1.5 — Backlog Técnico Priorizado

**Actualizado:** 2026-05-03  
**Fuente:** data/evolution/backlog.json (41 items total, 25 pendientes)

---

## Críticos (desbloquean autonomía real)

| ID | Título | Estado | Por qué es crítico |
|---|---|---|---|
| e1a2b4dd | Destrabar transición splash → shell | pending | Startup falso-ready sigue activo |
| 541f94e2 | Handshake de readiness bridge ↔ UI | pending | Cola de bridge sin respuesta |
| 8db889f0 | Selector soberano unificado | pending | Elección de provider es parcial |
| d2ef6b17 | Rotación gobernada de cuentas y cuotas | pending | Presupuesto cero no funciona |
| startup- | False-ready fix (in_progress) | in_progress | Splash visible tras main_window |
| CCVM-init | ControlCenterVM bloqueo 3733ms | pending (no formal) | Confirmed blocker Responding@60s |

---

## High (capacidades esenciales)

| ID | Título | Estado |
|---|---|---|
| 32e1ee5b | Inventario vivo de sesiones/cuentas/cuotas en WorldModel | pending |
| 9de52e89 | Integrar quota tracker al selector central | pending |
| 0b8584c3 | Shadow learning local formal | pending |
| 6b6b42f8 | Unificar marco de simbiosis IA-IA | pending |
| 0a4af16a | Registrar interacciones con IAs como aprendizaje operativo | pending |
| 331225c3 | Login gobernado y rotación de cuentas gratis | pending |
| b0a9ad3f | Control soberano de auditorías multi-herramienta | pending |
| 8ca9e3e4 | Supervisión y autoreinicio MCP + tunnel | pending |
| 99438d57 | Autoauditoría live guiada desde UI | pending |
| 487356fd | Aprender patrones de coordinación entre IAs | pending |
| (varios) | Administración RAM/CPU, detección inactividad, diagnóstico freezes | pending |
| (varios) | Startup timeline + diferimiento, startup false-ready fix | partial/pending |

---

## Medium (mejoras de calidad)

| ID | Título | Estado |
|---|---|---|
| (export) | Exportar/versionar/pushear evidencia de auditoría | pending |
| (telemetría) | Conectar startup_timeline al ciclo metacognitivo | partial |

---

## Plan de Implementación Recomendado (del Master Doc)

1. **Fase 1 — Estabilidad:** ControlCenterVM lazy init (desbloquea Responding@60s)
2. **Fase 2 — Quota loop:** Wiring de record_message_sent() en ATO
3. **Fase 3 — worker_pool:** Campo en WorldModelSnapshot + populate
4. **Fase 4 — AutonomyCycleService:** Centralizar bridge_findings, resume hints
5. **Fase 5 — Resume-aware:** Leer startup_summary() al arrancar
6. **Fase 6 — Selector unificado:** Rutas web como candidatos formales
7. **Fase 7 — AutonomyIndex:** Métricas en OSES + ControlMasterDigest
