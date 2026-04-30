# Multi-IA Coordination Protocol v1

Fecha: 2026-04-29

## Objetivo

Formalizar como IABV coordina varias IAs y herramientas sin crear otro
cerebro. La coordinacion debe montarse sobre las capas soberanas ya existentes
del proyecto.

## Regla central

La verdad viva local manda siempre.

Jerarquia:

1. `WorldModelSnapshot` y `EnvironmentSelfModel`
2. contratos reales del codigo
3. `DecisionAuditTrail` y `TaskOutcomeRecorder`
4. `PortableContextService`
5. recomendaciones o afirmaciones de IAs externas

## Que ya existe

Estas piezas ya cubren gran parte del protocolo:

- `WorldModelService`
  - verdad viva local del dispositivo
- `account_resource_scanner`
  - cuentas, workers, sesiones, cuota y rotacion basica
- `StrategySelector`
  - recomendacion por evidencia
- `AdaptiveWeightLayer`
  - ajuste adaptativo por rendimiento real
- `DecisionAuditTrail`
  - por que se tomo una decision
- `TaskOutcomeRecorder`
  - que paso de verdad
- `ExperimentLab`
  - comparacion de rutas/configuraciones
- `PortableContextService`
  - memoria portable no soberana
- `OperationalSelfExaminationService`
  - deteccion de degradacion, loops, drift y gaps

## Que falta

### 1. Task Packet canonico

Falta un contrato unico para representar una tarea, su presupuesto, fuente de
verdad, handoff y estado entre IAs/herramientas.

Campos minimos sugeridos:

- `task_id`
- `parent_task_id`
- `goal`
- `truth_source`
- `constraints`
- `budget`
- `status`
- `assigned_agent`
- `assigned_tool`
- `success_criteria`
- `evidence_required`
- `unresolved`
- `next_step`
- `last_decision_ref`
- `outcome_ref`

### 2. Handoff estructurado

Falta registrar de forma canónica:

- quien delega
- a quien
- por que
- que contexto se envia
- que evidencia debe volver
- cuanto presupuesto se consumio

### 3. Politica de conflicto

Falta explicitar:

- que hacer si dos IAs discrepan
- que hacer si una IA dice "listo" y la evidencia visible dice que no
- que hacer si una cuenta esta bloqueada o sin auth
- que hacer si una ruta consume mucha cuota para poco progreso

### 4. Presupuesto soberano multi-IA

Falta que el sistema use de forma centralizada:

- cuota
- mensajes disponibles
- riesgo de bloqueo
- auth vigente
- costo marginal de cada ruta

sin crear un nuevo coordinador paralelo.

## Implementacion correcta

No crear un nuevo servicio de "simbiosis".

Montarlo sobre:

- `account_resource_scanner`
- `StrategySelector`
- `AdaptiveWeightLayer`
- `DecisionAuditTrail`
- `TaskOutcomeRecorder`
- `PortableContextService`
- `OperationalSelfExaminationService`

## Secuencia recomendada

### Fase 1

- `Task Packet` canonico
- handoff estructurado
- registro obligatorio en `DecisionAuditTrail`
- outcome obligatorio en `TaskOutcomeRecorder`

### Fase 2

- snapshot soberano de auth/cuota/bloqueo por cuenta
- politica de corte por cuota/costo/bloqueo
- conflicto entre afirmacion de IA y evidencia local

### Fase 3

- aprendizaje por tipo de tarea
- aprendizaje por dispositivo
- ajuste de asignacion entre local/cloud/cuentas
- sync portable/local-cloud sin split-brain

## No hacer

- no crear otro cerebro
- no crear memoria paralela
- no mover decisiones soberanas a ViewModels
- no dejar que la nube mande sobre la verdad viva local

## Relacion con el objetivo del usuario

El objetivo no es solo "usar varias IAs".

El objetivo es que IABV se vuelva la ventana principal de la laptop y pueda:

- ver estado real del dispositivo
- ver que cuentas estan autenticadas o bloqueadas
- decidir a que IA delegar cada tarea
- evitar trabajo duplicado
- aprender de cada intento real

## Estado actual

La base arquitectonica ya existe.

Lo que falta no es otro sistema; falta cerrar los contratos:

- `Task Packet`
- `handoff`
- `presupuesto`
- `conflicto`
- `aprendizaje por dispositivo`
