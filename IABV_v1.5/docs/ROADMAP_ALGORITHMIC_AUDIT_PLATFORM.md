# Roadmap: Plataforma de Auditoría, Evaluación y Experimentación Algorítmica

## Visión
El sistema debe poder **mirarse a sí mismo**, detectar fallas en sus propios
algoritmos, tomar tiempo para analizar ciclos, aplicar fórmulas de
optimización, y decidir autónomamente qué mejorar — como una conciencia
operativa que razona sobre su propio funcionamiento.

## Estado Actual (lo que ya existe)

| Componente | Servicio existente | Alcance actual |
|---|---|---|
| Analizador parcial | `SelfAuditService`, `PerceptionCrossValidator` | Solo valida integridad de servicios y percepciones |
| Tester parcial | `ScenarioAutoTestService`, `ExecutionProbeService` | Solo escenarios de usuario y probes puntuales |
| Validador parcial | `ToolValidator`, `AutonomousValidationCycleService` | Solo herramientas y candidatos de evolución |
| Optimizador parcial | `AdaptiveWeightLayer`, `StrategySelector` | Solo pesos y selección de ruta/IA |
| Motor matemático parcial | `DecisionScoringEngine` | Solo scoring de decisiones, no estadística general |
| Simulador parcial | `SandboxExperimentService` | Sandbox básico sin simulación de escenarios complejos |

## Componentes a Implementar

### 1. AlgorithmAnalyzer (Prioridad: CRÍTICA)
Revisa la estructura, entradas, salidas y comportamiento de cada algoritmo.

**Responsabilidades:**
- Mapear dependencias entre servicios (grafo de dependencias vivo)
- Detectar dead code, métodos shadowed, imports no usados
- Medir complejidad ciclomática por método
- Verificar que cada servicio tiene tests suficientes
- Detectar patrones anti-patrón (ej: except Exception: pass sin logging)

**Input:** código fuente del sistema
**Output:** `AlgorithmAnalysisReport` con findings por severidad

### 2. AlgorithmTestBench (Prioridad: CRÍTICA)
Ejecuta casos de prueba sistemáticos contra cada algoritmo interno.

**Responsabilidades:**
- Generar casos de prueba automáticos (edge cases, null inputs, overflow)
- Ejecutar regression tests cuando un algoritmo cambia
- Medir coverage por servicio y método
- Detectar tests faltantes para métodos críticos
- Benchmark de rendimiento por algoritmo (latencia, memoria)

**Input:** servicios del sistema + historial de cambios
**Output:** `TestBenchReport` con resultados y coverage

### 3. AlgorithmValidator (Prioridad: ALTA)
Comprueba si cada algoritmo cumple reglas, límites y requisitos.

**Responsabilidades:**
- Verificar contratos (precondiciones, postcondiciones, invariantes)
- Validar que P1-P4 siguen cerradas después de cambios
- Comprobar que los tipos de retorno son correctos
- Verificar que las excepciones se manejan correctamente
- Detectar violaciones de AGENTS.md (ej: nuevo cerebro, PerceptionSnapshot duplicado)

**Input:** código fuente + AGENTS.md + contratos
**Output:** `ValidationReport` con violaciones y sugerencias

### 4. AlgorithmOptimizer (Prioridad: ALTA)
Prueba cambios para mejorar rendimiento algorítmico.

**Responsabilidades:**
- Ajustar umbrales y parámetros automáticamente (ej: `_AUTO_EXEC_MIN_CONFIDENCE`)
- Probar configuraciones alternativas en sandbox
- Medir impacto de cambios antes de promover
- A/B testing de algoritmos (versión actual vs candidata)
- Optimizar uso de memoria y CPU por servicio

**Input:** métricas de rendimiento + historial de ExperimentLab
**Output:** `OptimizationProposal` con cambios recomendados y evidencia

### 5. MathEngine (Prioridad: ALTA)
Aplica fórmulas, ecuaciones, métricas y estadísticas a datos del sistema.

**Responsabilidades:**
- Calcular tendencias (moving average, exponential smoothing)
- Detectar anomalías estadísticas (z-score, IQR)
- Correlacionar variables (ej: latencia de IA vs calidad de respuesta)
- Distribuciones de rendimiento por IA/ruta
- Métricas de salud del sistema (uptime, error rate, throughput)
- Fórmulas de confianza compuestas (bayesianas, no solo promedios)

**Input:** datos de ExperimentLab, TaskOutcomeRecorder, DecisionAuditTrail
**Output:** `StatisticalReport` con métricas, gráficas y alertas

### 6. ExperimentSimulator (Prioridad: MEDIA)
Simula escenarios complejos sin afectar el sistema real.

**Responsabilidades:**
- Fault injection: simular caída de ChatGPT, GPU saturada, red lenta
- Stress testing: simular 10 tareas simultáneas
- Monte Carlo: evaluar probabilidades de éxito por ruta
- What-if analysis: ¿qué pasa si cambio este umbral?
- Reproducir escenarios pasados con datos históricos

**Input:** estado actual del sistema + escenarios definidos
**Output:** `SimulationReport` con resultados y recomendaciones

## Gaps Cognitivos Pendientes

| Gap | Descripción | Impacto |
|---|---|---|
| CognitiveMonitor | Meta-observador continuo en background | El sistema no reflexiona sobre su propio flujo en tiempo real |
| TemporalAwareness | Conciencia del tiempo y anomalías temporales | No detecta "llevo 5 min en algo que tarda 30s" |
| Exploración proactiva | Probar N IAs simultáneamente de forma proactiva | Solo compara IAs reactivamente |
| DeepAnalysisQueue | Análisis profundo diferido | No aprovecha tiempo libre para análisis estadístico |
| CognitiveLoadManager | Gestión de carga cognitiva | No prioriza cuando llegan muchos estímulos |
| IdentityModel | Identidad persistente y autoconciencia | No sabe "soy mejor con ChatGPT para código" |

## Orden de Implementación Recomendado

### Fase 1: Fundamentos (semana 1-2)
1. **MathEngine** — base estadística para todo lo demás
2. **AlgorithmAnalyzer** — mapear el estado actual
3. **CognitiveMonitor** — empezar a observar en background

### Fase 2: Validación (semana 3-4)
4. **AlgorithmValidator** — verificar contratos y reglas
5. **AlgorithmTestBench** — tests automáticos
6. **TemporalAwareness** — conciencia del tiempo

### Fase 3: Optimización (semana 5-6)
7. **AlgorithmOptimizer** — optimización guiada por datos
8. **DeepAnalysisQueue** — análisis diferido inteligente
9. **CognitiveLoadManager** — gestión de carga

### Fase 4: Simulación (semana 7-8)
10. **ExperimentSimulator** — simulación avanzada
11. **IdentityModel** — autoconciencia de fortalezas
12. **Exploración proactiva** — comparación paralela proactiva

## Principios de Diseño

1. **No crear otro cerebro** — estos componentes son herramientas del
   orquestador existente, no decisores independientes
2. **Respetar P1-P4** — las capas cerradas se auditan pero no se modifican
3. **Local-first** — todo funciona sin conexión externa
4. **Evidencia sobre suposición** — solo proponer cambios con datos reales
5. **No congelar el sistema** — priorizar captura de estímulos, procesar después
6. **Yo y mis circunstancias** — adaptarse al hardware y entorno real
