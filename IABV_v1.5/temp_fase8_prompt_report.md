# FASE 8: EVOLUCIÓN DEL PROMPT - MEMORIA DE PROMPTS

## RESUMEN EJECUTIVO

- **PortableContextService**: ✅ Disponible
- **OperationalSelfExaminationService**: ✅ Disponible
- **DecisionAuditTrail**: ✅ Disponible
- **Memoria de prompts**: Implementada via PortableContextService
- **Evolución automática**: Implementada via OperationalSelfExaminationService

## SERVICIOS DE MEMORIA DE PROMPTS

### PortableContextService
**Estado**: ✅ Disponible

**Función**: Exporta contexto comprimido y portable para nuevas sesiones

**Capacidades**:
- Exporta contexto comprimido
- Incluye sección cloud_reasoning con health score, trends y recomendaciones
- Portable entre sesiones
- Incluye metadatos de aprendizaje acumulado

**Componentes del contexto portable**:
- Estado del entorno (hardware, runtime, riesgos)
- Herramientas disponibles y su estado
- Historial de decisiones cloud
- Patrones de interacción aprendidos
- Recomendaciones de mejora
- Health score de cloud reasoning
- Trends de rendimiento

### OperationalSelfExaminationService
**Estado**: ✅ Disponible

**Función**: Revisa patrones repetidos, degradaciones y ajustes recomendados

**Capacidades**:
- Revisa patrones repetidos en decisiones
- Detecta degradaciones de rendimiento
- Genera ajustes recomendados
- Lee DecisionAuditTrail para análisis
- Ejecuta análisis estadístico diferido
- Detecta anomalías temporales

**Componentes de autoexaminación**:
- _background_decision_review_findings(): revisa DecisionAuditTrail
- _temporal_awareness_findings(): detecta anomalías de latencia
- _deep_analysis_queue_findings(): análisis estadístico diferido
- _cloud_reasoning_findings(): analiza decisiones cloud

### DecisionAuditTrail
**Estado**: ✅ Disponible

**Función**: Registra cada decisión cloud (proveedor, latencia, confianza, resultado, tendencia)

**Capacidades**:
- Registro append-only en data/evolution/decision_audit/decisions.jsonl
- Registro de proveedor, modelo, latencia, confianza
- Registro de outcome, steps, fallback chain
- Registro de quality signals y user actions
- Análisis de tendencias históricas

**Componentes del registro**:
- decision_id, phase, timestamp_utc
- provider_id, model_used, user_goal
- outcome, latency_ms, confidence
- steps_total, steps_completed, steps_failed
- fallback_chain, error_detail
- user_action, quality_signal

## MEMORIA DE PROMPTS ACTUAL

### Prompts del Sistema
El sistema tiene prompts definidos en varios archivos:
- AGENTS.md: Instrucciones principales para Codex
- .github/copilot-instructions.md: Instrucciones rápidas
- docs/AGENT_QUICK_REFERENCE.md: Referencia rápida

### Prompts de Herramientas
Cada herramienta tiene prompts específicos definidos en sus adapters:
- external_assistant: Prompt para asistentes externos
- ollama: Prompt para inferencia local
- playwright: Prompt para control de navegador
- shell: Prompt para comandos de shell

### Prompts de Interacción
InteractionLearningService genera prompts basados en patrones aprendidos:
- Patrones de interacción reusables
- Historial de éxito/fracaso
- Recomendaciones de modo de interacción

## EVOLUCIÓN AUTOMÁTICA DE PROMPTS

### Mecanismo 1: PortableContextService
**Cómo funciona**:
1. Exporta contexto comprimido con aprendizaje acumulado
2. Incluye health score de cloud reasoning
3. Incluye trends de rendimiento
4. Incluye recomendaciones de mejora
5. Nueva sesión puede importar este contexto

**Impacto en prompts**:
- Los prompts pueden adaptarse al contexto importado
- Las recomendaciones pueden influir en la selección de herramientas
- El health score puede ajustar la confianza en decisiones cloud

### Mecanismo 2: OperationalSelfExaminationService
**Cómo funciona**:
1. Revisa DecisionAuditTrail para detectar patrones
2. Identifica proveedores con baja tasa de éxito
3. Detecta decisiones de baja confianza que fallan
4. Identifica errores que se repiten sin corrección
5. Genera recomendaciones de ajuste

**Impacto en prompts**:
- Los prompts pueden incluir advertencias sobre proveedores degradados
- Los prompts pueden sugerir alternativas basadas en historial
- Los prompts pueden incluir restricciones basadas en patrones de fallo

### Mecanismo 3: InteractionLearningService
**Cómo funciona**:
1. Aprende patrones de interacción desde ejecuciones
2. Clasifica patrones como reusables o no
3. Registra éxito/fracaso de cada patrón
4. Genera recomendaciones de modo de interacción

**Impacto en prompts**:
- Los prompts pueden sugerir modos de interacción probados
- Los prompts pueden incluir advertencias sobre patrones degradados
- Los prompts pueden priorizar patrones con alta tasa de éxito

## ESTRATEGIAS DE EVOLUCIÓN DE PROMPTS

### Estrategia 1: Adaptación Contextual
**Objetivo**: Adaptar prompts basándose en contexto portable

**Implementación**:
1. Importar contexto portable al inicio de sesión
2. Extraer health score y trends de cloud reasoning
3. Ajustar prompts basándose en contexto
4. Incluir restricciones basadas en historial

**Beneficios esperados**:
- Prompts más relevantes al contexto actual
- Reducción de errores repetidos
- Mejora de tasa de éxito

### Estrategia 2: Aprendizaje de Fallos
**Objetivo**: Incorporar lecciones de fallos en prompts

**Implementación**:
1. Analizar DecisionAuditTrail para patrones de fallo
2. Identificar errores recurrentes
3. Incluir advertencias en prompts
4. Sugerir alternativas basadas en historial

**Beneficios esperados**:
- Reducción de errores repetidos
- Mejora de resiliencia
- Aprendizaje acumulativo

### Estrategia 3: Evolución Continua
**Objetivo**: Evolucionar prompts continuamente basándose en uso

**Implementación**:
1. Registrar cada decisión y resultado
2. Analizar tendencias de rendimiento
3. Ajustar prompts basándose en trends
4. Validar cambios con pruebas

**Beneficios esperados**:
- Mejora continua de prompts
- Adaptación a cambios en entorno
- Optimización de rendimiento

## ESTADO ACTUAL DE MEMORIA DE PROMPTS

### DecisionAuditTrail
**Estado**: ✅ Operativo

**Ubicación**: data/evolution/decision_audit/decisions.jsonl

**Registros**: 20 resultados recientes (19 éxitos, 1 fallo)

**Análisis disponible**:
- Proveedores usados y su tasa de éxito
- Latencia promedio por proveedor
- Confianza promedio por proveedor
- Tendencias de rendimiento

### PortableContextService
**Estado**: ✅ Disponible

**Capacidad**: Exportar contexto comprimido

**Componentes disponibles**:
- Estado del entorno
- Herramientas disponibles
- Historial de decisiones
- Patrones aprendidos
- Recomendaciones

### OperationalSelfExaminationService
**Estado**: ✅ Operativo

**Capacidad**: Revisar patrones y generar recomendaciones

**Componentes disponibles**:
- Revisión de DecisionAuditTrail
- Detección de anomalías temporales
- Análisis estadístico diferido
- Recomendaciones de ajuste

## RECOMENDACIONES

### Inmediata
1. **Activar PortableContextService**: Exportar contexto portable regularmente
2. **Analizar DecisionAuditTrail**: Extraer insights de decisiones recientes
3. **Generar recomendaciones**: Usar OperationalSelfExaminationService para generar ajustes

### Corto plazo
1. **Implementar adaptación contextual**: Ajustar prompts basándose en contexto portable
2. **Incorporar aprendizaje de fallos**: Incluir advertencias en prompts basadas en historial
3. **Validar cambios**: Probar prompts evolucionados con casos de prueba

### Medio plazo
1. **Implementar evolución continua**: Ajustar prompts continuamente basándose en uso
2. **Automatizar análisis**: Ejecutar OperationalSelfExaminationService periódicamente
3. **Optimizar rendimiento**: Ajustar prompts basándose en trends de rendimiento

## PRÓXIMA FASE

FASE 9: Salida obligatoria - 9 resultados finales
