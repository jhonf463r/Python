# AUDITORÍA DE CIERRE Y BRECHAS - IABV v1.5

## FASE 0 — RECONSTRUCCIÓN DEL PANORAMA

### Qué se pidió
- Auditoría de cierre y brechas del sistema IABV v1.5
- No rehacer toda la auditoría desde cero
- Identificar qué ya existe y funciona, qué existe pero está desconectado/parcial, qué falta, qué está mal configurado
- Identificar qué bloquea la autonomía real
- Entregar 9 secciones obligatorias

### Qué se arregló en auditorías previas
**Auditoría inicial (AUDITORIA_IABV_V1.5_RESULTADOS_FINALES.md)**:
- Inventario del entorno: 14 herramientas detectadas, 3 limitaciones críticas
- Contrato del sistema: arquitectura central, servicios de memoria, contratos de datos
- Memoria de comportamiento: 18 ToolCards, 3 InteractionPatterns, chatgpt_web_assisted degradado (77% éxito)
- Percepción universal: WorldModelService operativo, 11 windows activas, 19 herramientas detectadas, 3 bloqueos activos
- Reglas de decisión: 3/5 reglas activas (validación, expansión, fallback)
- Caso ChatGPT: bloqueo browser_security_verification, 3 estrategias propuestas
- Ejecución real: limitaciones del entorno para operación como humano
- Coherencia: 8/8 servicios conectados, wiring correcto
- Evolución del prompt: PortableContextService y OperationalSelfExaminationService disponibles

**Auditoría delta (AUDITORIA_DELTA_SEGUNDA_PASADA.md)**:
- Mapa de órganos cognitivos: 7/11 existen (64%), solo 4/11 funcionan completamente (36%)
- Memoria de herramientas: 15 herramientas analizadas, chatgpt_web_assisted con fallo recurrente
- Hipótesis de acción: NO existe órgano de simulación interna
- Bloqueos y fallback: 3 bloqueos activos, estrategias de fallback propuestas
- Prompt evolution: IntentLearningLayer y PortableContextService disponibles
- Inspector metacognitivo: Parcialmente implementado (A y B completos, C parcial, D incompleto, E parcial)

**FASE NUEVA (implementada en sesión previa)**:
- Creación de ActionHypothesisSimulatorService
- Integración con InteractionModeSelector
- Conexión de servicios en bootstrap
- Creación de inspector metacognitivo completo (JSON + Markdown)
- Verificación de integración en execute()

### Qué sigue faltando
- Verificación real de que ActionHypothesisSimulatorService funciona en runtime
- Verificación de que la simulación realmente influye en decisiones
- Verificación de que el inspector metacognitivo es visible en UI
- Implementación de feedback loop automático para aprendizaje
- Implementación de reutilización real de sesión/contexto
- Implementación de reglas de decisión en código (no solo identificadas)
- Resolución de bloqueos activos (browser_security_verification, assistant_login_required, capture_unverified)

### Qué sigue sin verificarse
- Si ActionHypothesisSimulatorService realmente se ejecuta antes de cada selección de herramienta
- Si la simulación realmente cambia la selección de herramienta
- Si el inspector metacognitivo es visible para usuarios en UI
- Si el sistema realmente aprende de ejecuciones o solo registra
- Si el sistema realmente reutiliza contexto o solo lo propone
- Si el sistema realmente evita repetir errores o solo los documenta

## FASE 1 — RESUMEN EJECUTIVO DE FALTANTES

### Faltantes Críticos

1. **Simulación interna no verificada en runtime**
   - **Qué es**: ActionHypothesisSimulatorService existe y está conectado, pero no se ha verificado que realmente se ejecuta en cada selección de herramienta
   - **Por qué importa**: Es el órgano crítico de metacognición imaginativa; sin verificación en runtime, no sabemos si realmente funciona
   - **Dónde se ve el problema**: InteractionModeSelector.select() tiene código de simulación, pero no hay logs ni evidencia de ejecución real
   - **Tipo**: Flujo / Ejecución
   - **Base parcial**: ✅ Servicio creado, código integrado, pero no verificado en runtime
   - **Qué falta**: Verificación en runtime con logs reales, pruebas de que la simulación se ejecuta y cambia decisiones

2. **Reutilización de sesión/contexto no implementada**
   - **Qué es**: El sistema NO tiene lógica de decisión para reutilizar ventanas/sesiones existentes
   - **Por qué importa**: browser_security_verification bloquea chatgpt_web_assisted por lanzamiento headless repetido
   - **Dónde se ve el problema**: chatgpt_web_assisted siempre lanza nueva ventana, 0 ventanas ChatGPT detectadas
   - **Tipo**: Flujo / Decisión
   - **Base parcial**: ✅ REGLA 1 identificada en auditoría delta, pero no implementada en código
   - **Qué falta**: Implementar detección de ventanas activas, lógica de reutilización, inyección en ventana existente

3. **Feedback loop automático no implementado**
   - **Qué es**: El sistema registra decisiones y resultados pero NO usa esa información para cambiar decisiones futuras automáticamente
   - **Por qué importa**: Sin feedback loop, el sistema no aprende ni evoluciona automáticamente
   - **Dónde se ve el problema**: DecisionAuditTrail registra, OperationalSelfExaminationService revisa, pero no hay acción automática
   - **Tipo**: Flujo / Aprendizaje
   - **Base parcial**: ✅ Servicios de auditoría operativos, pero sin loop de acción
   - **Qué falta**: Implementar lógica que use DecisionAuditTrail para ajustar parámetros de selección automáticamente

### Faltantes Importantes

4. **Inspector metacognitivo no visible en UI**
   - **Qué es**: El inspector metacognitivo existe como JSON/MD pero no es visible en UI para usuarios
   - **Por qué importa**: Sin visibilidad en UI, los usuarios no pueden auditar el sistema en tiempo real
   - **Dónde se ve el problema**: Solo existe como archivos en data/evolution/, no hay panel en Centro de Control
   - **Tipo**: UI / Visibilidad
   - **Base parcial**: ✅ Reporte JSON/MD generado, pero no integrado en UI
   - **Qué falta**: Panel en Centro de Control o pestaña dedicada que muestre el inspector en tiempo real

5. **Reglas de decisión no implementadas en código**
   - **Qué es**: 5 reglas identificadas (3 activas, 2 inactivas) pero no implementadas en código
   - **Por qué importa**: Sin implementación, las reglas son solo documentación, no comportamiento real
   - **Dónde se ve el problema**: REGLA 1 (reutilización de ventana) y REGLA 2 (cambio a desktop app) están inactivas
   - **Tipo**: Código / Decisión
   - **Base parcial**: ✅ Reglas identificadas y documentadas, pero no implementadas
   - **Qué falta**: Implementar las 5 reglas en código con lógica condicional real

6. **Evolución automática de prompts no implementada**
   - **Qué es**: PortableContextService puede exportar contexto pero no hay evolución automática de prompts
   - **Por qué importa**: Sin evolución de prompts, el sistema no mejora su comunicación con herramientas
   - **Dónde se ve el problema**: IntentLearningLayer aprende patrones pero no evoluciona prompts
   - **Tipo**: Aprendizaje / Prompt
   - **Base parcial**: ✅ Servicios disponibles, pero sin lógica de evolución
   - **Qué falta**: Implementar lógica que use patrones aprendidos para evolucionar prompts automáticamente

### Faltantes Secundarios

7. **Validación de herramientas no implementada**
   - **Qué es**: 19/19 herramientas están UNVALIDATED, no hay validación automática
   - **Por qué importa**: Sin validación, el sistema no sabe si una herramienta realmente funciona
   - **Dónde se ve el problema**: ToolCard.validation_status siempre UNVALIDATED
   - **Tipo**: Código / Validación
   - **Base parcial**: ✅ Campo validation_status existe, pero sin lógica de validación
   - **Qué falta**: Implementar validación automática de herramientas

8. **Expansión de uso de alternativas no implementada**
   - **Qué es**: 15 herramientas nunca usadas, no hay diversificación automática
   - **Por qué importa**: Sin diversificación, el sistema depende de chatgpt_web_assisted que está degradado
   - **Dónde se ve el problema**: 87% del catálogo subutilizado
   - **Tipo**: Flujo / Decisión
   - **Base parcial**: ✅ Herramientas disponibles, pero sin lógica de expansión
   - **Qué falta**: Implementar lógica que pruebe alternativas cuando la principal falla

## FASE 2 — ÓRGANOS COGNITIVOS: ESTADO REAL

### Percepción
- **Servicio**: WorldModelService
- **Estado actual**: ✅ EXISTE Y FUNCIONA
- **Evidencia**: Escanea cada 45s (ligero) y 180s (completo), detecta 11 windows, 19 herramientas
- **Limitación**: No detectó procesos de navegador (0), permisos no configurados (0)
- **Brecha restante**: Configurar permisos de observación, mejorar detección de procesos de navegador

### Memoria de comportamiento
- **Servicio**: ToolMemory + InteractionLearningService
- **Estado actual**: ✅ EXISTE Y FUNCIONA
- **Evidencia**: Recuerda tareas, resultados, aprende patrones, 18 ToolCards, 3 InteractionPatterns
- **Limitación**: Subutilizado (87% del catálogo nunca usado)
- **Brecha restante**: Implementar lógica que use memoria para optimizar decisiones futuras

### Memoria de sesión
- **Servicio**: AdaptiveSessionRepository
- **Estado actual**: ⚠️ EXISTE PERO PARCIAL
- **Evidencia**: Guarda sesiones, contexto persistente
- **Limitación**: No hay reutilización explícita de contexto
- **Brecha restante**: Implementar lógica de reutilización de contexto entre sesiones

### Selección de herramienta
- **Servicio**: InteractionModeSelector
- **Estado actual**: ✅ EXISTE Y FUNCIONA
- **Evidencia**: Selecciona modo basado en task kind y patrones reusables
- **Limitación**: No razona sobre costo, contexto, probabilidad de éxito de manera explícita
- **Brecha restante**: Integrar simulación interna para razonamiento explícito

### Simulación interna / hipótesis de acción
- **Servicio**: ActionHypothesisSimulatorService
- **Estado actual**: ⚠️ EXISTE PERO NO VERIFICADO EN RUNTIME
- **Evidencia**: Servicio creado, código integrado en InteractionModeSelector, bootstrap conectado
- **Limitación**: No se ha verificado que realmente se ejecuta en cada selección
- **Brecha restante**: Verificación en runtime con logs reales, pruebas de que cambia decisiones

### Decisión contextual
- **Servicio**: AdaptiveTaskOrchestrator
- **Estado actual**: ⚠️ EXISTE PERO PARCIAL
- **Evidencia**: Decide ruta operativa, usa LocalRoleRouter
- **Limitación**: No razona explícitamente sobre reutilización de contexto, costo, probabilidad de éxito
- **Brecha restante**: Implementar razonamiento metacognitivo explícito

### Ejecución
- **Servicio**: AdaptiveTaskOrchestrator + ToolAdapter
- **Estado actual**: ✅ EXISTE Y FUNCIONA
- **Evidencia**: Ejecuta herramientas, registra resultados
- **Limitación**: No hay verificación post-ejecución que influya en decisiones futuras
- **Brecha restante**: Implementar feedback loop automático

### Verificación
- **Servicio**: TaskOutcomeRecorder + OperationalSelfExaminationService
- **Estado actual**: ⚠️ EXISTE PERO PARCIAL
- **Evidencia**: Registra resultados, revisa DecisionAuditTrail
- **Limitación**: No hay verificación post-ejecución que influya en decisiones futuras automáticamente
- **Brecha restante**: Implementar feedback loop automático

### Auditoría / trazabilidad
- **Servicio**: DecisionAuditTrail + OperationalSelfExaminationService
- **Estado actual**: ✅ EXISTE Y FUNCIONA
- **Evidencia**: Registra decisiones, revisa patrones, detecta degradaciones
- **Limitación**: No hay acción automática basada en revisiones
- **Brecha restante**: Implementar acción automática basada en revisiones

### Evolución del prompt
- **Servicio**: IntentLearningLayer + PortableContextService
- **Estado actual**: ⚠️ EXISTE PERO PARCIAL
- **Evidencia**: Aprende patrones de intent, puede exportar contexto
- **Limitación**: No hay evolución automática de prompts basada en aprendizaje
- **Brecha restante**: Implementar evolución automática de prompts

### Inspector visible de metacognición
- **Servicio**: temp_fase_nueva_inspeccion_metacognitiva_completa.py
- **Estado actual**: ⚠️ EXISTE PERO NO VISIBLE EN UI
- **Evidencia**: Genera reporte JSON/MD con estado completo del sistema
- **Limitación**: Solo existe como script temporal, no integrado en UI
- **Brecha restante**: Integrar en UI como panel en Centro de Control

## FASE 3 — SIMULACIÓN INTERNA: ESTADO REAL

### Estado actual
ActionHypothesisSimulatorService existe y está conectado, pero NO se ha verificado en runtime.

### Verificación de componentes

**✅ Servicio creado**: `src/iabv_v15/services/adaptive/action_hypothesis_simulator_service.py`
- Estructuras de datos definidas: ActionHypothesis, HypothesisEvaluation, SimulationResult
- Método simulate() implementado con heurísticas
- Conexión a servicios: ToolMemory, WorldModelService, UniversalPerceptionService, DecisionAuditTrail, OperationalSelfExaminationService, PortableContextService

**✅ Integración en InteractionModeSelector**: `src/iabv_v15/services/tools/interaction_mode_selector.py`
- Constructor modificado para aceptar action_hypothesis_simulator
- Código de simulación agregado en select() (líneas 106-175)
- Lógica de override si simulación sugiere herramienta diferente
- Metadata de resultado de simulación agregada

**✅ Conexión en bootstrap**: `src/iabv_v15/bootstrap.py`
- ActionHypothesisSimulatorService instanciado con todas las dependencias
- Inyección en InteractionModeSelector después de creación

**⚠️ NO VERIFICADO EN RUNTIME**:
- No hay logs que confirmen que simulate() se ejecuta en cada selección
- No hay evidencia de que la simulación realmente cambia decisiones
- No hay pruebas unitarias o de integración
- No hay métricas de uso del simulador

### Lo que falta
1. Verificación en runtime con logs reales
2. Pruebas de que la simulación se ejecuta en cada selección
3. Pruebas de que la simulación realmente cambia decisiones
4. Métricas de uso del simulador
5. Validación de que las heurísticas producen resultados razonables

## FASE 4 — MEMORIA Y REUTILIZACIÓN DE CONTEXTO: ESTADO REAL

### Estado actual
El sistema tiene memoria de comportamiento pero NO la usa para optimizar decisiones futuras.

### Verificación de componentes

**✅ ToolMemory**: `src/iabv_v15/services/tools/tool_memory.py`
- Recuerda tareas, resultados, actualiza ToolCards con success/failure counts
- Integra con InteractionLearningService para aprender patrones
- Estado: OPERATIVO pero subutilizado (87% del catálogo nunca usado)

**✅ InteractionLearningService**: `src/iabv_v15/services/tools/interaction_learning_service.py`
- Aprende patrones de interacción desde ejecuciones
- Guarda patrones en ToolRecordRepository
- Estado: OPERATIVO pero patrones no se usan para optimizar decisiones

**✅ InteractionModeSelector**: `src/iabv_v15/services/tools/interaction_mode_selector.py`
- Usa patrones reusables para selección
- Estado: OPERATIVO pero limitado (no razona sobre costo, contexto, probabilidad)

**⚠️ PortableContextService**: `src/iabv_v15/services/adaptive/portable_context_service.py`
- Puede exportar contexto comprimido
- Estado: DISPONIBLE pero no activado para uso real

**⚠️ OperationalSelfExaminationService**: `src/iabv_v15/services/evolution/operational_self_examination_service.py`
- Revisa DecisionAuditTrail periódicamente
- Genera recomendaciones de ajuste
- Estado: OPERATIVO pero recomendaciones no se implementan automáticamente

**✅ DecisionAuditTrail**: `src/iabv_v15/services/evolution/decision_audit_trail.py`
- Registra decisiones en append-only JSONL
- Estado: OPERATIVO pero no se usa para aprendizaje automático

### Conclusión
**¿El sistema realmente aprende o solo registra?**
- SOLO REGISTRA. No hay feedback loop automático que use DecisionAuditTrail para cambiar decisiones futuras.

**¿Realmente reutiliza contexto o solo lo propone?**
- SOLO LO PROPONE. No hay lógica de decisión para reutilizar ventanas/sesiones existentes.

**¿Realmente evita repetir errores o solo los documenta?**
- SOLO LOS DOCUMENTA. No hay lógica que use historial de fallos para evitar repetir errores automáticamente.

### Lo que falta
1. Implementar feedback loop automático que use DecisionAuditTrail
2. Implementar lógica de decisión para reutilización de contexto
3. Implementar lógica que use historial de fallos para evitar repetir errores
4. Activar PortableContextService para uso real
5. Implementar acción automática basada en recomendaciones de OperationalSelfExaminationService

## FASE 5 — INSPECTOR METACOGNITIVO: VISIBILIDAD Y UTILIDAD

### Estado actual
El inspector metacognitivo existe como JSON/MD pero NO es visible en UI.

### Verificación de componentes

**✅ Script de inspección**: `temp_fase_nueva_inspeccion_metacognitiva_completa.py`
- Genera reporte JSON completo con estado del sistema
- Genera reporte Markdown con formato legible
- Muestra: estado del entorno, memoria, simulación, decisión, descarte, aprendizaje
- Estado: FUNCIONAL pero solo como script temporal

**✅ Reporte JSON**: `data/evolution/metacognition_inspector_complete_report.json`
- Contiene estado completo del sistema
- Timestamp: 2026-06-16T04:14:52.001970+00:00
- Estado: GENERADO pero no visible en UI

**✅ Reporte Markdown**: `data/evolution/metacognition_inspector_complete_report.md`
- Contiene estado completo del sistema en formato legible
- Estado: GENERADO pero no visible en UI

**❌ Integración en UI**: NO EXISTE
- No hay panel en Centro de Control
- No hay pestaña dedicada
- No hay endpoint API para consulta en tiempo real
- No hay actualización automática

### Utilidad actual
- ✅ Muestra qué ve el sistema (estado del entorno)
- ✅ Muestra qué recuerda (memoria de herramientas)
- ✅ Muestra qué imagina (simulación de hipótesis)
- ✅ Muestra qué elige (decisión final)
- ✅ Muestra por qué descarta (evaluaciones descartadas)
- ⚠️ Muestra qué aprende (parcial, no hay feedback loop automático)
- ✅ Permite auditoría humana (formato JSON/MD legible)

### Recomendación concreta
**Panel en Centro de Control**:
- Ubicación: Centro de Control → Pestaña "Metacognición"
- Contenido: Vista en tiempo real del inspector metacognitivo
- Actualización: Cada 30s o manual
- Exportación: Botón para exportar JSON/MD

Alternativa: **Reporte exportable** con endpoint API para consulta en tiempo real.

## FASE 6 — BLOQUEOS Y CUELLOS DE BOTELLA

### Bloqueos actuales

**1. browser_security_verification**
- **Estado**: ACTIVO
- **Causa raíz**: Lanzamiento headless de ChatGPT web detectado como bot
- **Síntoma**: 10 fallos de 44 ejecuciones (23% tasa de fallo)
- **Efecto secundario**: chatgpt_web_assisted degradado (77% éxito)
- **Solución propuesta**: Reutilizar ventana existente o cambiar a desktop app
- **Estado de solución**: NO IMPLEMENTADA (REGLA 1 inactiva)

**2. assistant_login_required**
- **Estado**: ACTIVO
- **Causa raíz**: Requiere login de asistente
- **Síntoma**: Herramientas externas no pueden ejecutar sin credenciales
- **Efecto secundario**: Limitación de uso de herramientas externas
- **Solución propuesta**: Implementar gestión de credenciales con CredentialBroker
- **Estado de solución**: INFRAESTRUCTURA PREPARADA pero no implementada

**3. capture_unverified**
- **Estado**: ACTIVO
- **Causa raíz**: Captura no verificada
- **Síntoma**: No se puede capturar contenido de ventanas/sesiones
- **Efecto secundario**: Limitación de percepción
- **Solución propuesta**: Implementar verificación de captura
- **Estado de solución**: NO IMPLEMENTADA

### Cuellos de botella

**1. Subutilización de herramientas**
- **Estado**: ACTIVO
- **Causa raíz**: 87% del catálogo nunca usado (15/18 herramientas)
- **Síntoma**: Dependencia excesiva de chatgpt_web_assisted que está degradado
- **Efecto secundario**: Falta de diversificación, riesgo de fallo único
- **Solución propuesta**: Implementar expansión de uso de alternativas
- **Estado de solución**: NO IMPLEMENTADA

**2. Falta de reutilización de contexto**
- **Estado**: ACTIVO
- **Causa raíz**: NO hay lógica de decisión para reutilizar ventanas/sesiones
- **Síntoma**: Cada ejecución es independiente, pierde contexto previo
- **Efecto secundario**: browser_security_verification por lanzamiento headless repetido
- **Solución propuesta**: Implementar REGLA 1 (reutilización de ventana existente)
- **Estado de solución**: NO IMPLEMENTADA

**3. Falta de feedback loop automático**
- **Estado**: ACTIVO
- **Causa raíz**: DecisionAuditTrail registra pero no se usa para aprendizaje
- **Síntoma**: El sistema no aprende ni evoluciona automáticamente
- **Efecto secundario**: Comportamiento estático, sin mejora continua
- **Solución propuesta**: Implementar feedback loop automático
- **Estado de solución**: NO IMPLEMENTADA

### Qué bloquea realmente la autonomía
- **browser_security_verification**: Bloquea ejecución de chatgpt_web_assisted
- **Falta de reutilización de contexto**: Bloquea uso eficiente de herramientas web
- **Falta de feedback loop automático**: Bloquea aprendizaje y evolución del sistema

### Qué es síntoma vs causa raíz
- **Síntoma**: 10 fallos de chatgpt_web_assisted
- **Causa raíz**: Falta de reutilización de ventana (REGLA 1 no implementada)
- **Síntoma**: 87% del catálogo nunca usado
- **Causa raíz**: Falta de expansión de uso de alternativas
- **Síntoma**: Sistema no aprende
- **Causa raíz**: Falta de feedback loop automático

## FASE 7 — QUÉ YA ESTÁ BIEN Y CONVIENE CONSERVAR

### Arquitectura y servicios
- ✅ Arquitectura sólida con servicios bien definidos
- ✅ Servicios de memoria de comportamiento operativos (ToolMemory, InteractionLearningService)
- ✅ Servicios de percepción universal operativos (WorldModelService, UniversalPerceptionService)
- ✅ Servicios de auditoría operativos (DecisionAuditTrail, OperationalSelfExaminationService)
- ✅ Wiring correcto de servicios (bootstrap)

### Órganos cognitivos operativos
- ✅ Percepción: WorldModelService escanea entorno correctamente
- ✅ Memoria de comportamiento: ToolMemory recuerda tareas y resultados
- ✅ Selección de herramienta: InteractionModeSelector selecciona modo correctamente
- ✅ Ejecución: AdaptiveTaskOrchestrator ejecuta herramientas correctamente
- ✅ Auditoría: DecisionAuditTrail registra decisiones correctamente

### Nuevos componentes (FASE NUEVA)
- ✅ ActionHypothesisSimulatorService creado con estructuras de datos y heurísticas
- ✅ Integración en InteractionModeSelector con código de simulación
- ✅ Conexión de servicios en bootstrap
- ✅ Inspector metacognitivo completo (JSON/MD)

### Reportes y auditorías
- ✅ Auditoría inicial completa con 9 resultados finales
- ✅ Auditoría delta con mapa de órganos cognitivos
- ✅ Reportes de memoria de herramientas
- ✅ Reportes de reglas de decisión
- ✅ Inspector metacognitivo completo

## FASE 8 — QUÉ HAY QUE CORREGIR O CONSTRUIR DESPUÉS

### Prioridad CRÍTICA

1. **Verificar ActionHypothesisSimulatorService en runtime**
   - Agregar logs en simulate() para confirmar ejecución
   - Agregar logs en InteractionModeSelector.select() para confirmar uso
   - Agregar métricas de uso del simulador
   - Validar que la simulación realmente cambia decisiones

2. **Implementar reutilización de sesión/contexto (REGLA 1)**
   - Implementar detección de ventanas activas
   - Implementar lógica de reutilización de ventana existente
   - Implementar inyección en ventana existente
   - Resolver browser_security_verification

### Prioridad IMPORTANTE

3. **Implementar feedback loop automático**
   - Implementar lógica que use DecisionAuditTrail para ajustar parámetros
   - Implementar acción automática basada en recomendaciones de OperationalSelfExaminationService
   - Implementar aprendizaje automático de fallos

4. **Integrar inspector metacognitivo en UI**
   - Crear panel en Centro de Control
   - Crear endpoint API para consulta en tiempo real
   - Implementar actualización automática

5. **Implementar reglas de decisión en código**
   - Implementar REGLA 1 (reutilización de ventana existente)
   - Implementar REGLA 2 (cambio a desktop app después de fallos)
   - Implementar REGLA 3 (validación de herramientas)
   - Implementar REGLA 4 (expansión de uso de alternativas)
   - Implementar REGLA 5 (uso de Ollama como fallback)

### Prioridad SECUNDARIA

6. **Implementar evolución automática de prompts**
   - Implementar lógica que use patrones aprendidos para evolucionar prompts
   - Implementar adaptación contextual de prompts

7. **Implementar validación de herramientas**
   - Implementar validación automática de herramientas
   - Implementar pruebas de funcionalidad

8. **Implementar expansión de uso de alternativas**
   - Implementar lógica que pruebe alternativas cuando la principal falla
   - Implementar diversificación automática

## FASE 9 — PREGUNTAS QUE NECESITO QUE RESPONDAS PARA CERRAR LA SIGUIENTE ITERACIÓN

1. **¿Quieres priorizar verificación de ActionHypothesisSimulatorService o implementación de reutilización de contexto primero?**
   - Verificación de simulación interna es crítica para confirmar que el órgano de metacognición funciona
   - Implementación de reutilización de contexto es crítica para resolver browser_security_verification

2. **¿Quieres que el inspector metacognitivo sea visible en UI (panel en Centro de Control) o basta con reporte exportable?**
   - Panel en Centro de Control permite auditoría en tiempo real
   - Reporte exportable es más simple de implementar pero menos conveniente

3. **¿Quieres priorizar implementación de feedback loop automático o implementación de reglas de decisión primero?**
   - Feedback loop automático es crítico para aprendizaje y evolución
   - Reglas de decisión son críticas para resolver bloqueos específicos

4. **¿Quieres que priorice velocidad de implementación, exactitud de metacognición, o trazabilidad de decisiones?**
   - Velocidad: implementar lo mínimo para que funcione
   - Exactitud: implementar metacognición completa y precisa
   - Trazabilidad: implementar auditoría completa y visible

5. **¿Quieres que la siguiente iteración se enfoque en resolver bloqueos (browser_security_verification) o en mejorar metacognición (simulación, aprendizaje)?**
   - Resolver bloqueos mejora autonomía inmediata
   - Mejorar metacognición mejora autonomía a largo plazo
