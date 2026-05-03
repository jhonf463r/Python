# IABV v1.5 — Log de Decisiones

**Actualizado:** 2026-05-03

---

## Decisiones de esta sesión (2026-05-03, Devin)

### D-2026-05-03-001: Crear capa de trazabilidad interna como docs/governance/
- **Razón:** El repositorio carecía de una fuente de verdad viva que permitiera a cualquier IA entrar, leer el estado actual y seguir trabajando sin depender del historial completo del chat.
- **Módulos afectados:** docs/ (nuevo directorio)
- **Estado:** Implementado
- **Riesgo:** Ninguno — es documentación, no toca código ejecutable

### D-2026-05-03-002: No implementar AutonomyCycleService todavía
- **Razón:** El archivo no existe en el source tree (UNRESOLVED U1). Antes de crearlo hay que confirmar si fue descartado intencionalmente o si fue mergeado en otra rama. El código disperso en OSES y TOR sigue funcionando con fallback inline.
- **Módulos afectados:** Ninguno (decisión de no-cambio)
- **Estado:** Aceptado
- **Riesgo:** Bajo — el código disperso funciona, solo es deuda de organización

### D-2026-05-03-003: No hacer refactor masivo del ControlCenterVM
- **Razón:** Con 7056 líneas, es el archivo más grande del proyecto. Un refactor completo sería riesgoso. La corrección mínima recomendada es mover la inicialización pesada a `_initialize_heavy()` con QTimer, lo cual no requiere reestructurar el VM completo.
- **Módulos afectados:** control_center_viewmodel.py (cambio puntual futuro)
- **Estado:** Propuesto
- **Riesgo:** Bajo si se mantiene como cambio local

### D-2026-05-03-004: Actualizar Control Master con estado de tests y sesión actual
- **Razón:** El Control Master estaba desactualizado desde 2026-04-19 (2 semanas). Los objetivos, tests y decisiones no reflejaban el trabajo reciente.
- **Módulos afectados:** data/evolution/control_master/
- **Estado:** Implementado
- **Riesgo:** Ninguno — es actualización de estado, no de código

### D-2026-05-03-005: Integrar IABV_MASTER_DOC_v1.md al repo
- **Razón:** Documento valioso que consolida estado, visión, backlog y plan. Sin él, futuras sesiones perderían contexto. Debe vivir versionado dentro del repo.
- **Módulos afectados:** docs/
- **Estado:** Implementado
- **Riesgo:** Ninguno

---

## Decisiones históricas relevantes

| Fecha | Decisión | Agente |
|---|---|---|
| 2026-04-19 | Sembrar 37 reglas desde AGENTS.md al Control Master | Codex |
| 2026-04-19 | Crear 4 objetivos de super sincronía | Codex |
| 2026-04-22 | Capa 2: LocalCliToolAdapter + ToolCards | Devin |
| 2026-04-22 | Capa 2.1: inject $HOME/.iabv/tools/* into MCP bridge PATH | Devin |
| 2026-04-22 | Capa 2.2: proactive token rotation detector | Devin |
| 2026-04-30 | PR #307: Architecture Report V5, propuesta de AutonomyCycleService | Devin/Windsurf |
