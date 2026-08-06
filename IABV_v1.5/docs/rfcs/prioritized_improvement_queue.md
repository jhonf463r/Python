# RFC: Cola Priorizada De Mejoras

## Objetivo
Dar al programa una guia clara para ordenar ideas, arreglos y mejoras de la mas importante a la menos importante, sin perder trazabilidad ni mezclar tareas criticas con mejoras secundarias.

## Idea Principal
Cada instalacion de IABV debe guardar una cola local de mejoras y el sistema debe clasificar cada item con una prioridad explicita antes de ejecutarlo o mostrarlo.

La prioridad no debe depender solo de la intuicion. Debe considerar:
- impacto funcional
- riesgo de error o bloqueo
- frecuencia de repeticion
- dependencia con otras tareas
- costo de implementacion
- evidencia real en logs, tests o auditoria

## Regla De Orden
Orden sugerido:
1. **P0 - Critico**: bloquea arranque, chat, UI, seguridad o datos.
2. **P1 - Alto**: mejora una ruta central que ya existe y evita fallos repetidos.
3. **P2 - Medio**: optimiza calidad, rendimiento o estabilidad sin romper flujos.
4. **P3 - Bajo**: ideas de limpieza, refactor cosmetico o mejoras opcionales.

Si dos items tienen la misma prioridad, gana el que tenga mas evidencia real y menor riesgo.

## Formato De Cada Idea
Cada item de la cola debe guardar:
- `id`
- `title`
- `summary`
- `priority`
- `reason`
- `evidence`
- `status`
- `created_at`
- `last_reviewed_at`
- `device_id`
- `source`

## Flujo De Trabajo
1. El sistema detecta una mejora o ajuste.
2. La registra en una cola local.
3. Calcula prioridad.
4. La compara con otras ideas pendientes.
5. Muestra primero lo critico y luego lo secundario.
6. Cuando se resuelve, conserva evidencia y marca el resultado.

## Regla Para Aprendizaje Evolutivo
La prioridad futura debe subir o bajar segun resultados reales:
- si una solucion redujo errores, su patron asociado gana peso
- si una solucion no resolvio el problema, baja su confianza
- si una mejora se repite en varios dispositivos, sube a candidato universal

## Idea De Implementacion
Agregar una capa ligera llamada `PriorityQueueService` o equivalente que:
- lea la evidencia local de `data/evolution/`
- ordene items por prioridad y confianza
- produzca un resumen para `PortableContextService`
- alimente `OperationalSelfExaminationService`
- mantenga una vista de "principales vs no principales"

## Criterio De Exito
El programa debe poder responder:
- que es lo mas importante ahora
- por que es importante
- que depende de eso
- que puede esperar

## Resultado Esperado
Con esta cola, IABV no solo acumula ideas: las convierte en una lista ordenada de accion, priorizando primero lo que desbloquea el sistema y dejando lo accesorio al final.
