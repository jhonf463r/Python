# Contrato De Arquitectura Unificada Para Auditoria, Aprendizaje Y Evolucion

## Proposito

Toda auditoria, analisis, correccion, experimento y aprendizaje sobre IABV debe converger en una sola logica arquitectonica.

La meta no es "tener mas reportes". La meta es:

- no repetir codigo
- no crear memorias paralelas
- no dejar logs muertos que ninguna otra IA vuelva a mirar
- no chocar algoritmos entre si
- no producir basura desconectada de la metacognicion

Este contrato existe para que cualquier IA que entre al repo vea por donde debe pasar la evidencia y donde debe aterrizar cada mejora.

## Regla soberana

Si una auditoria o mejora no termina alimentando la arquitectura metacognitiva existente, esta incompleta.

No basta con:

- generar un log temporal
- escribir un script aislado
- dejar una conclusion en un chat externo
- agregar otro analizador paralelo

Debe quedar conectada a los repositorios, trails, contexto portable o backlog que el propio sistema ya consume.

## Donde debe converger la evidencia

### 1. Decisiones y rendimiento de proveedores

Usar:

- `DecisionAuditTrail`
- `OperationalSelfExaminationService._cloud_reasoning_findings()`
- `PortableContextService._cloud_reasoning_section()`

No crear otro audit trail para decisiones cloud.

### 2. Aprendizaje de rutas, asistentes y configuraciones

Usar:

- `ExperimentLab`
- `StrategySelector`
- `AdaptiveWeightLayer`
- `TaskOutcomeRecorder`

La comparacion entre IAs, rutas o configuraciones debe caer aqui con:

- `assistant_kind`
- `config_signature`
- `comparison_scope_key`
- `source_trace_ids`
- `adaptive_learning_summary`

### 3. Estado vivo, bloqueos y permisos

Usar:

- `WorldModelSnapshot`
- `EnvironmentSelfModel`
- `AutonomyGovernancePolicy`

No inventar disponibilidad de herramientas si no fue observada o inferida por estas capas.

### 4. Hallazgos metacognitivos y feedback de ajustes

Usar:

- `OperationalSelfExaminationService`
- `recommendation_feedback`
- `feedback_summary`
- `validated_improvements`
- `unresolved_risks`

Si un ajuste funciono o no, debe verse aqui.

### 5. Contexto portable para sesiones nuevas y otras IAs

Usar:

- `PortableContextService`
- `data/evolution/portable_context/latest.json`
- `data/evolution/portable_context/latest.md`

Toda IA nueva debe poder leer el estado resumido sin recorrer chats viejos.

### 6. Pendientes estrategicos y deuda viva

Usar:

- `data/evolution/backlog.json`
- `docs/history/...`

El backlog guarda deuda estructurada.
Los handoff docs guardan evidencia y narrativa tecnica de una fase concreta.

### 7. Telemetria de startup y auditoria live

Si se agrega instrumentacion live, no debe quedarse como archivo muerto.

Debe alimentar, directa o indirectamente:

- `OperationalSelfExaminationService`
- `PortableContextService`
- `backlog.json`
- `docs/history/...` cuando la fase lo amerite

## Patrones permitidos

1. Instrumentar un problema real.
2. Guardar evidencia en trail/log estructurado.
3. Traducir esa evidencia a hallazgos metacognitivos.
4. Exportarla al contexto portable.
5. Reflejar la deuda abierta en backlog.
6. Validar con pruebas o con observacion live real.

## Patrones prohibidos

- crear otro cerebro
- crear otro orquestador
- crear otra memoria paralela
- dejar un `jsonl` o `md` que ninguna capa soberana consume
- repetir el mismo analisis en varios servicios distintos
- inventar una "mejor IA" sin evidencia real persistida
- dejar una conclusion solo en la conversacion y no en el repo

## Aplicacion concreta al paradigma multi-IA

La simbiosis entre IAs no debe nacer como subsistema aparte.

Debe montarse sobre:

- `ExperimentLab`
- `StrategySelector`
- `AdaptiveWeightLayer`
- `TaskOutcomeRecorder`
- `DecisionAuditTrail`
- `OperationalSelfExaminationService`
- `PortableContextService`
- `account_resource_scanner` para sesiones, cuotas y pool real

Eso significa:

- comparar IAs con `comparison_scope_key`
- guardar `source_trace_ids`
- ajustar pesos por exito, bloqueo, fallback y latencia
- exportar las recomendaciones al contexto portable
- dejar deuda abierta en backlog cuando algo siga incompleto

## Aplicacion concreta al problema actual

Hoy la prioridad no es ampliar providers.

Hoy la prioridad soberana es:

1. `startup visible estable`
2. `shell readiness real`
3. `bridge usable`
4. `RAM/control de congelamientos`

Recién despues:

5. selector unificado `API gratis + web session + local shadow`
6. rotacion gobernada de cuentas/cuotas
7. aprendizaje formal de colaboraciones entre IAs

## Regla de cierre de sesion para cualquier IA

Antes de terminar una sesion, cualquier IA debe dejar al menos una de estas huellas utiles:

- codigo integrado a la arquitectura vigente
- pruebas
- backlog actualizado
- contexto portable mas fiel
- self-examination mas informativa
- handoff doc en `docs/history/`

Si no deja ninguna, probablemente solo produjo contexto efimero.
