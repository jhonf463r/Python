# IABV v1.5 — Registro de UNRESOLVED

**Actualizado:** 2026-05-03

Todo lo que no puede confirmarse con evidencia del código fuente actual.

---

| ID | Descripción | Origen | Impacto |
|---|---|---|---|
| U1 | **AutonomyCycleService no existe en el source tree.** Evidencia de búsqueda exhaustiva abajo. | Master Doc | Alto — código disperso en OSES y TOR que debería centralizarse |
| U2 | **CPU frequency UNRESOLVED en EnvironmentSelfModel.** `UNRESOLVED:cpu_frequency` persiste (última lectura: 2026-05-02). | EnvironmentSelfModel | Bajo — no afecta decisiones de ruta |
| U3 | **Control Master desactualizado desde 2026-04-19.** Los 4 objetivos activos y el estado de tests no reflejaban el trabajo reciente de Windsurf/Codex hasta esta sesión. | Control Master | Medio — actualizado parcialmente en esta sesión |
| U4 | **lazy_vm_prebuild_done nunca disparó en 120s.** QTimer de 15s para pre-construir ViewModels en background no disparó. ¿Event loop bloqueado por tool probing y MCP startup al segundo 15? | OSES findings | Medio — VMs se construyen on-demand pero sin prebuild |
| U5 | **pageLoader QML síncrono causa freeze de 28s.** OSES reporta `startup_populate_ui_freeze: 28716ms CRITICAL`. Causa raíz dentro del QML loader, no en Python. | Live audit | Alto — impacto directo en UX de arranque |
| U6 | **Verificación visual real de splash/ventana requiere permiso explícito.** Sin permiso de observación, el estado visual no puede confirmarse. | AGENTS.md regla | Bajo — validado por tests en su lugar |
| U7 | **Corpus de entrenamiento derivado de traces.** Diseñado en conversación con Codex pero no implementado. | Chat Codex | Medio — potencia el aprendizaje futuro |
| U8 | **Login humano, captcha y 2FA de terceros.** No automatizable por definición — siempre requerirá interacción. | Limitación inherente | Bajo — aceptado como limitación |
| U9 | **29 tests fallando pre-existentes.** No son regresiones nuevas. Incluyen: cloud_quick_reply (4), cognitive_frame_translate (7), control_center_viewmodel (8), desajustes_fixes (1), specific_apikey_routing (8), startup_evolution (1). | Test suite | Medio — deuda técnica acumulada |
| U10 | **Quota tracker sin alimentación automática.** `record_message_sent()` existe pero no se llama en flujo de ejecución normal. Workers nunca "se gastan" en el modelo interno. | Master Doc / Código | Alto — presupuesto cero no funciona sin esto |

---

## Protocolo para nuevos UNRESOLVED

Si algo no puede confirmarse en el código:
1. Agregarlo aquí con un ID secuencial (U11, U12, ...)
2. Incluir: descripción, origen de la duda, impacto estimado
3. Registrarlo también en el Control Master via CLI:
   ```bash
   PYTHONPATH=src python -m iabv_v15 cm mark-unresolved "texto del unresolved"
   ```
4. No inventar disponibilidad, no fingir confirmación

---

## U1 — Evidencia detallada de búsqueda (AutonomyCycleService)

**Fecha:** 2026-05-03  
**Sesión:** Devin session `2b36b4fec0f84edb872a43580eb90f4f`

### Qué se buscó
- Nombre exacto: `AutonomyCycleService`
- Variantes: `autonomy_cycle`, `AutonomyCycle`, `autonomy_cycle_service`

### Dónde se buscó
1. **Árbol fuente completo:**
   ```
   grep -r "AutonomyCycleService" src/iabv_v15/  →  0 resultados
   grep -r "autonomy_cycle_service" src/iabv_v15/  →  0 resultados
   find src/iabv_v15/ -name "*autonomy_cycle*"  →  0 archivos
   ```
2. **Tests:**
   ```
   grep -r "AutonomyCycleService" tests/  →  0 resultados
   ```
3. **Bootstrap (wiring):**
   ```
   grep "AutonomyCycleService\|autonomy_cycle" src/iabv_v15/bootstrap.py  →  0 resultados
   ```
4. **domain/models.py:** sin referencia.
5. **Git history:** El servicio aparece diseñado en PR #307 (Architecture Report V5, branch `devin/1777750256`) como propuesta de la Fase 4 del plan de evolución. No hay evidencia de que se haya implementado o mergeado y luego eliminado.

### Qué se encontró en su lugar
- `OperationalSelfExaminationService` contiene `bridge_findings()` y lógica de startup summary.
- `TrainingOrchestrator` contiene `seed_capabilities()` y resume hints parciales.
- Ambos incluyen fallbacks inline que hacen lo que el servicio centralizado haría.
- El Master Doc (Fase 4) lo marca como "si no fue mergeado" — implica que era opcional.

### Conclusión
AutonomyCycleService **nunca fue implementado**. Su funcionalidad está dispersa en OSES y TOR con fallbacks. No es un bloqueante para las fases 1-3. Se deja UNRESOLVED para decisión futura del responsable del proyecto.
