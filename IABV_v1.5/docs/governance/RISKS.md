# IABV v1.5 — Riesgos Clasificados

**Actualizado:** 2026-05-03

---

## Riesgo Alto

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **ControlCenterVM bloquea main thread 3733ms** | Responding=False@60s → UX degradada, usuario percibe app congelada | Mover init pesada a _initialize_heavy() con QTimer.singleShot(0) |
| **pageLoader QML freeze 28s** | UI no responde entre populate_ui_deferred y page_loader_ready | Causa raíz en QML loader; requiere investigación profunda del lado QML |
| **Quota tracker desconectado** | Workers nunca "se gastan" → selector elige providers agotados | Wiring de record_message_sent() en ATO pre-despacho |
| **Selector de provider parcial** | Rutas web no son candidatos formales → subutilización de recursos | Implementar backlog 8db889f0 (selector unificado) |
| **Crear otro cerebro accidentalmente** | Duplicación de orquestación → conflictos de decisión, bugs difíciles | Seguir regla AGENTS.md: toda lógica nueva va dentro de ATO como método |

## Riesgo Medio

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **29 tests fallando** | Deuda técnica que puede enmascarar regresiones reales | Investigar y corregir por grupos (cloud_reply, cognitive_frame, etc.) |
| **Control Master se desactualiza** | IAs futuras arrancan con estado stale | Disciplina de actualizar al cerrar cada sesión |
| **Resume hints sin consumidor** | Tareas interrumpidas se pierden → usuario debe re-explicar | Fase 5: resume-aware orchestration |
| **AutonomyCycleService no existe** | Código disperso en OSES y TOR → duplicación, difícil de mantener | Fase 4: crear servicio centralizado si se confirma su necesidad |
| **lazy_vm_prebuild_done nunca dispara** | VMs se construyen on-demand en vez de en background | Investigar si QTimer queda bloqueado por event loop al segundo 15 |

## Riesgo Bajo

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **CPU frequency UNRESOLVED** | EnvironmentSelfModel incompleto pero no afecta decisiones | Bajo — se puede ignorar sin consecuencias |
| **Verificación visual requiere permiso** | Sin permiso, estado visual = UNRESOLVED | Aceptado — validación por tests en lugar de observación |
| **Login humano no automatizable** | Limitación inherente de terceros | Aceptado — siempre requerirá interacción para captcha/2FA |

---

## Riesgo de Crear Otro Cerebro (específico AGENTS.md)

Los siguientes items del backlog, si se implementan mal, crean un orquestador paralelo:

| Item | Riesgo específico | Implementación correcta |
|---|---|---|
| 8db889f0 — Selector soberano unificado | Crear servicio con estado propio | Método del Orchestrator existente |
| Shadow mode | Servicio separado que decide | Ruta interna del ATO |
| UniversalAutonomyIndex | Servicio nuevo | Cálculo de OSES, no servicio nuevo |
