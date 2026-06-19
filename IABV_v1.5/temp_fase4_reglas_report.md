# FASE 4: REGLAS DE DECISIÓN - LÓGICA DE REUTILIZACIÓN

## RESUMEN EJECUTIVO

- **Reglas evaluadas**: 5
- **Reglas activas**: 3/5 (60%)
- **Reglas inactivas**: 2/5 (40%)

## REGLA 1: Reutilización de Ventana Existente

**Estado**: ❌ INACTIVA

**Condición**: Ventana ChatGPT existente detectada

**Resultado actual**:
- Ventanas ChatGPT detectadas: 0
- No hay ventana ChatGPT existente

**Estrategia cuando inactiva**:
- Lanzar nueva ventana (comportamiento actual)

**Estrategia cuando activa**:
- Reutilizar ventana existente en lugar de lanzar nueva
- Inyectar en ventana existente en vez de lanzar nueva instancia

**Implementación requerida**:
- Modificar ToolAdapter para detectar ventana existente antes de lanzar
- Usar WorldModelService para verificar windows activas
- Implementar lógica de inyección en ventana existente

## REGLA 2: Cambio a Desktop App tras N Fallos Consecutivos

**Estado**: ❌ INACTIVA

**Condición**: Fallos recientes >= 3 o tasa de fallo >= 30%

**Resultado actual**:
- Resultados recientes chatgpt_web_assisted: 20
- Fallos recientes: 1
- Tasa de fallo: 5.0%
- 1 fallos < 3 umbral
- 5.0% < 30% umbral

**Estrategia cuando inactiva**:
- Continuar usando chatgpt_web_assisted

**Estrategia cuando activa**:
- Cambiar a chatgpt_installed (desktop app)
- Razón: N fallos recientes >= umbral
- Usar desktop app para evitar detección de bot headless

**Implementación requerida**:
- Modificar InteractionModeSelector para contar fallos consecutivos
- Implementar lógica de cambio de herramienta tras N fallos
- Usar chatgpt_installed como alternativa a chatgpt_web_assisted

## REGLA 3: Validación de Herramientas Antes de Uso

**Estado**: ✅ ACTIVA

**Condición**: Herramientas sin validar detectadas

**Resultado actual**:
- Herramientas sin validar: 19/19
- Todas las herramientas están en estado UNVALIDATED

**Estrategia**:
- Ejecutar is_available() para cada herramienta antes de usarla
- Validar herramientas automáticamente en ToolRegistry

**Herramientas a validar**:
- chatgpt_web_assisted: ToolValidationStatus.UNVALIDATED
- chatgpt_installed: ToolValidationStatus.UNVALIDATED
- claude_installed: ToolValidationStatus.UNVALIDATED
- claude_web_assisted: ToolValidationStatus.UNVALIDATED
- codex_installed: ToolValidationStatus.UNVALIDATED
- ... y 14 más

**Implementación requerida**:
- Modificar ToolRegistry para validar herramientas automáticamente
- Implementar validación en refresh_card()
- Cachear resultados de validación (TTL: 120s)

## REGLA 4: Expansión de Uso de Alternativas

**Estado**: ✅ ACTIVA

**Condición**: Herramientas disponibles pero nunca usadas

**Resultado actual**:
- Herramientas disponibles pero nunca usadas: 15
- Uso actual concentrado en 3 herramientas

**Uso actual de herramientas (basado en patrones)**:
- chatgpt_web_assisted: 44 ejecuciones, 77.3% éxito
- ollama_llm: 2 ejecuciones, 100.0% éxito
- codex_installed: 2 ejecuciones, 50.0% éxito

**Herramientas a probar**:
- chatgpt_installed: ChatGPT instalado
- claude_installed: Claude instalado
- claude_web_assisted: Claude web asistido
- cloudflared_cli: Cloudflared CLI
- desktop_human_runner: Desktop human runner
- ... y 10 más

**Estrategia**:
- Probar claude_installed, codex_installed para diversificar
- Expandir uso a herramientas disponibles pero no usadas
- Diversificar para reducir dependencia de chatgpt_web_assisted

**Implementación requerida**:
- Modificar InteractionModeSelector para diversificar uso
- Implementar lógica de selección basada en historial de uso
- Priorizar herramientas subutilizadas con alta disponibilidad

## REGLA 5: Uso de Ollama como Fallback Confiable

**Estado**: ✅ ACTIVA

**Condición**: Ollama tasa de éxito >= 80%

**Resultado actual**:
- Ollama ejecuciones: 2
- Ollama tasa de éxito: 100.0%
- 100.0% >= 80% umbral

**Estrategia**:
- Usar ollama_llm cuando herramientas externas fallen
- Ollama como fallback confiable

**Implementación requerida**:
- Modificar InteractionModeSelector para usar Ollama como fallback
- Implementar lógica de fallback cuando herramientas externas fallen
- Priorizar Ollama cuando herramientas cloud fallan

## RESUMEN DE REGLAS ACTIVAS

### Reglas Activas (3/5)
1. ✅ REGLA 3: Validación de herramientas antes de uso
2. ✅ REGLA 4: Expansión de uso de alternativas
3. ✅ REGLA 5: Uso de Ollama como fallback confiable

### Reglas Inactivas (2/5)
1. ❌ REGLA 1: Reutilización de ventana existente
2. ❌ REGLA 2: Cambio a desktop app tras N fallos consecutivos

## IMPLEMENTACIÓN PRIORITARIA

### Alta Prioridad (Reglas Activas)
1. **REGLA 3**: Validación de herramientas antes de uso
   - Modificar ToolRegistry.refresh_card()
   - Implementar is_available() automático
   - Cachear resultados de validación

2. **REGLA 4**: Expansión de uso de alternativas
   - Modificar InteractionModeSelector.select()
   - Implementar lógica de diversificación
   - Priorizar herramientas subutilizadas

3. **REGLA 5**: Uso de Ollama como fallback confiable
   - Modificar InteractionModeSelector.select()
   - Implementar lógica de fallback
   - Priorizar Ollama cuando herramientas cloud fallan

### Media Prioridad (Reglas Inactivas)
4. **REGLA 1**: Reutilización de ventana existente
   - Modificar ToolAdapter para detectar ventana existente
   - Implementar lógica de inyección en ventana existente
   - Usar WorldModelService para verificar windows activas

5. **REGLA 2**: Cambio a desktop app tras N fallos consecutivos
   - Modificar InteractionModeSelector para contar fallos consecutivos
   - Implementar lógica de cambio de herramienta
   - Usar chatgpt_installed como alternativa

## IMPACTO ESPERADO

### Reglas Activas (Implementación Inmediata)
- **REGLA 3**: Mejorará confiabilidad al validar herramientas antes de uso
- **REGLA 4**: Reducirá dependencia de chatgpt_web_assisted, diversificará uso
- **REGLA 5**: Proporcionará fallback confiable cuando herramientas cloud fallen

### Reglas Inactivas (Implementación Futura)
- **REGLA 1**: Reducirá tiempo de lanzamiento, evitará detección de bot
- **REGLA 2**: Mejorará resiliencia ante fallos recurrentes de ChatGPT web

## PRÓXIMA FASE

FASE 5: Caso especial ChatGPT web asistido - analizar bloqueo browser_security_verification e implementar estrategia de reutilización de ventana
