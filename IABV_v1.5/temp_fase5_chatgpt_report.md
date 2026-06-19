# FASE 5: CASO ESPECIAL CHATGPT WEB ASISTIDO

## RESUMEN EJECUTIVO

- **Herramienta**: chatgpt_web_assisted
- **Estado**: DEGRADADO
- **Bloqueo activo**: browser_security_verification
- **Historial**: 34 éxitos, 10 fallos (77% éxito)
- **Alternativa disponible**: chatgpt_installed (desktop app, nunca usado)
- **Ventanas existentes**: 0

## ANÁLISIS DEL BLOQUEO

### browser_security_verification
**Tipo**: Bloqueo de seguridad del navegador

**Causa probable**:
- Lanzamiento headless de ChatGPT web detectado como bot
- Verificación de seguridad de OpenAI bloquea ejecución automatizada
- Nuevo lanzamiento cada vez activa detección

**Historial de fallos**:
- 10 fallos de 44 ejecuciones (23% tasa de fallo)
- Patrón recurrente desde 2026-05-09
- Fallos consistentes con browser_security_verification

**Impacto**:
- Bloquea ejecución de chatgpt_web_assisted
- Reduce confiabilidad del sistema
- Aumenta tiempo de respuesta (reintentos)

## ALTERNATIVAS DISPONIBLES

### chatgpt_installed (Desktop App)
**Estado**: DISPONIBLE
**Uso**: Nunca usado
**Ventajas**:
- No requiere navegador headless
- Evita detección de bot
- Menor latencia (sin overhead de navegador)
- Más estable para automatización

**Desventajas**:
- Requiere instalación previa
- No probado en este entorno
- Puede tener diferentes limitaciones

### claude_installed / claude_web_assisted
**Estado**: DISPONIBLE
**Uso**: Nunca usado
**Ventajas**:
- Alternativa a ChatGPT
- Diversificación de proveedores
- Puede no tener los mismos bloqueos

**Desventajas**:
- No probado en este entorno
- Diferente modelo de IA
- Puede requerir adaptación

### ollama_llm (Local)
**Estado**: DISPONIBLE
**Uso**: 2 ejecuciones, 100% éxito
**Ventajas**:
- 100% tasa de éxito
- Ejecución local (sin dependencia cloud)
- Sin bloqueos de seguridad
- Fallback confiable

**Desventajas**:
- Modelo local menos capaz
- Requiere recursos locales
- No tiene acceso a internet en tiempo real

## ESTRATEGIAS PROPUESTAS

### Estrategia 1: Reutilización de Ventana Existente
**Objetivo**: Evitar nuevo lanzamiento que activa detección de bot

**Implementación**:
1. Detectar ventana ChatGPT existente via WorldModelService
2. Si ventana existe, reusarla en lugar de lanzar nueva
3. Inyectar consulta en ventana existente
4. Mantener ventana abierta entre consultas

**Requisitos**:
- Implementar detección de ventana en ToolAdapter
- Implementar inyección en ventana existente
- Configurar WorldModelService para escanear windows

**Beneficios esperados**:
- Evita detección de bot (ventana ya autenticada)
- Reduce tiempo de lanzamiento
- Mejora tasa de éxito

**Riesgos**:
- Ventana puede cerrarse manualmente
- Sesión puede expirar
- Requiere gestión de estado de ventana

### Estrategia 2: Cambio a Desktop App
**Objetivo**: Usar chatgpt_installed en lugar de chatgpt_web_assisted

**Implementación**:
1. Activar REGLA 2 cuando fallos >= 3 consecutivos
2. Cambiar a chatgpt_installed automáticamente
3. Mantener chatgpt_web_assisted como fallback

**Requisitos**:
- Implementar lógica de cambio en InteractionModeSelector
- Validar chatgpt_installed antes de uso
- Configurar cambio automático tras N fallos

**Beneficios esperados**:
- Evita bloqueo browser_security_verification
- Más estable para automatización
- Menor latencia

**Riesgos**:
- chatgpt_installed puede no estar disponible
- Puede tener diferentes limitaciones
- Requiere validación previa

### Estrategia 3: Híbrida con Fallback
**Objetivo**: Combinar reutilización de ventana y cambio a desktop app

**Implementación**:
1. Intentar reutilizar ventana ChatGPT existente
2. Si no existe, lanzar chatgpt_installed
3. Si chatgpt_installed falla, usar chatgpt_web_assisted
4. Si todo falla, usar ollama_llm como fallback final

**Requisitos**:
- Implementar cadena de fallback en InteractionModeSelector
- Validar cada herramienta antes de uso
- Configurar prioridades de selección

**Beneficios esperados**:
- Máxima resiliencia
- Múltiples opciones de fallback
- Adaptación automática a condiciones

**Riesgos**:
- Complejidad de implementación
- Requiere validación de múltiples herramientas
- Puede aumentar tiempo de decisión

## RECOMENDACIÓN

### Recomendación Inmediata
**Implementar Estrategia 1 (Reutilización de Ventana Existente)**

**Justificación**:
- Resuelve directamente el bloqueo browser_security_verification
- Menor complejidad de implementación
- Aprovecha herramienta existente (chatgpt_web_assisted)
- No requiere cambio de herramienta

### Recomendación Secundaria
**Implementar Estrategia 2 (Cambio a Desktop App) como fallback**

**Justificación**:
- Proporciona alternativa cuando reutilización falla
- chatgpt_installed está disponible
- Evita dependencia única de chatgpt_web_assisted

### Recomendación Terciaria
**Implementar Estrategia 3 (Híbrida) a largo plazo**

**Justificación**:
- Máxima resiliencia
- Múltiples opciones de fallback
- Adaptación automática a condiciones

## PLAN DE IMPLEMENTACIÓN

### Fase 1: Reutilización de Ventana (Inmediata)
1. Modificar ToolAdapter para detectar ventana ChatGPT existente
2. Implementar lógica de inyección en ventana existente
3. Configurar WorldModelService para escanear windows
4. Probar con consultas simples

### Fase 2: Cambio a Desktop App (Corto plazo)
1. Activar REGLA 2 en InteractionModeSelector
2. Validar chatgpt_installed antes de uso
3. Implementar cambio automático tras 3 fallos consecutivos
4. Probar con consultas simples

### Fase 3: Híbrida con Fallback (Medio plazo)
1. Implementar cadena de fallback en InteractionModeSelector
2. Configurar prioridades de selección
3. Validar todas las herramientas antes de uso
4. Probar con consultas complejas

## IMPACTO ESPERADO

### Inmediato (Fase 1)
- Reducción de fallos browser_security_verification
- Mejora de tasa de éxito de chatgpt_web_assisted
- Reducción de tiempo de lanzamiento

### Corto plazo (Fase 2)
- Alternativa confiable cuando chatgpt_web_assisted falla
- Diversificación de herramientas
- Mejora de resiliencia general

### Medio plazo (Fase 3)
- Máxima resiliencia
- Adaptación automática a condiciones
- Múltiples opciones de fallback

## PRÓXIMA FASE

FASE 6: Ejecución real - probar UI como humano (limitado por entorno)
