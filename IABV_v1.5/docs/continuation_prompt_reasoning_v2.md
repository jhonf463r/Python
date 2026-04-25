# PROMPT DE CONTINUACIÓN — Algoritmo de Razonamiento Autónomo v2

## CONTEXTO: QUÉ SE HIZO Y QUÉ FALTA

### Completado (PRs #178-#182, mergeados en main):
1. **PR #178-179**: Metacognición profunda — 5 capas nuevas (holistic scan, deep env, accounts, limits, regression detector)
2. **PR #180**: GPU auto-routing — verifica y fuerza Ollama a NVIDIA RTX 4050
3. **PR #181**: Common Sense Engine v1 — 13 reglas de inferencia causal (forward chaining)
4. **PR #182**: Bugfix — inicializar variables git antes del try block

### Estado actual del auto-análisis (última ejecución real):
- **GPU**: 2 detectadas (NVIDIA RTX 4050 primaria + Intel UHD refuerzo)
- **GPU Routing**: "pre-configurado" — CUDA_VISIBLE_DEVICES=0, pero solo verifica cuando Ollama carga un modelo
- **Sentido Común v1**: 10 hechos → 2 reglas → 2 acciones ejecutadas (pre-config CUDA + source secrets)
- **Deducciones holísticas**: Bajaron de 3 a 1 (mejora confirmada por trend detector)
- **Tests**: 22/22 pasando
- **Cuentas**: 10 detectadas (9 Chrome + 1 Edge), todas completas
- **Bug fix aplicado**: Error `local_dirty` ya no ocurre

### LO QUE FALTA — Lo verdaderamente importante:

El Common Sense Engine v1 tiene **13 reglas hardcodeadas**. Eso NO es razonamiento real.
Lo que el usuario quiere es un algoritmo que:

1. **No dependa de reglas escritas a mano** — que pueda enfrentar situaciones nuevas que nunca vio
2. **Tenga control total del laptop** — IABV es la ventana de todo el sistema. No debe decir "NECESITA USUARIO" para cosas que puede hacer solo
3. **Tome el camino obvio** — si algo es sensato, coherente, de sentido común → hacerlo sin preguntar
4. **Use ExperimentLab para comparar** algoritmos de razonamiento en paralelo y seleccionar el mejor

---

## TAREA: Construir el Algoritmo de Razonamiento Real

### 1. Análisis del gap actual

**Problema central**: `common_sense_engine.py` y `holistic_metacognition_scan()` usan lógica if/else estática.
No pueden:
- Razonar sobre combinaciones no previstas
- Aprender de resultados pasados para mejorar reglas
- Generar nuevas hipótesis cuando ven anomalías
- Priorizar acciones por impacto real medido

**Archivos clave a estudiar**:
```
src/iabv_v15/services/common_sense_engine.py      — Motor v1 (forward chaining, 13 reglas)
src/iabv_v15/services/self_code_analysis.py        — holistic_metacognition_scan() (línea 829)
src/iabv_v15/services/auto_correction_engine.py    — _ACTION_HANDLERS (línea 284), execute_auto_corrections (421)
src/iabv_v15/services/lab/experiment_lab.py         — ExperimentLab.run_experiment(), record_outcome()
src/iabv_v15/services/lab/strategy_selector.py      — StrategySelector.recommend()
src/iabv_v15/services/lab/decision_scoring_engine.py — 6 dimensiones de scoring
src/iabv_v15/services/lab/adaptive_weight_layer.py  — Ajuste adaptivo por historial
src/iabv_v15/services/adaptive/intent_understanding_service.py — Clasificación de intenciones
src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py  — Orquestador principal
src/iabv_v15/services/gpu_metacognition.py          — verify_ollama_gpu_usage(), detect_physical_gpus()
```

### 2. Qué debe hacer el algoritmo v2

#### A. Razonamiento por anomalía (no por regla fija)
En vez de `if nvidia_present AND ollama_on_cpu → force_nvidia`, el sistema debería:
- Observar que hay un recurso de alta capacidad (NVIDIA 8GB VRAM) **sin uso**
- Observar que hay un proceso (Ollama) usando un recurso inferior (CPU/iGPU)
- **Deducir por anomalía**: "recurso superior disponible + recurso inferior en uso = subóptimo"
- Esta deducción aplica a GPU, RAM, disco, red — sin regla específica por recurso

#### B. Razonamiento por estado esperado vs real
- IABV tiene un `WorldModelSnapshot` que describe el estado esperado
- Tiene scans que muestran el estado real
- **Deducción**: toda diferencia entre esperado y real es un problema potencial
- Ejemplo: WorldModel dice "Ollama disponible", pero `ollama ps` muestra 0 modelos → anomalía

#### C. Razonamiento por historial (aprendizaje)
- ExperimentLab ya registra `ExperimentRun` con precision/robustness
- El algoritmo v2 debería consultar historial ANTES de actuar:
  - "¿La última vez que forcé NVIDIA, funcionó?" → sí → hacerlo otra vez
  - "¿La última vez que reinicié Ollama, mejoró?" → no → probar otra cosa
- Usar `StrategySelector.recommend()` para elegir la mejor acción

#### D. Control total del laptop (eliminar "NECESITA USUARIO" innecesarios)
IABV tiene acceso a:
- **PowerShell** (`subprocess`) → puede instalar cosas, configurar servicios
- **Git** → puede hacer checkout, pull, push, merge
- **Ollama API** → puede cargar/descargar modelos
- **Archivos** → puede leer/escribir configs, secretos
- **Red** → puede verificar conectividad
- **Navegadores** → puede detectar perfiles y cuentas

Lo que NO debería pedir al usuario:
- Instalar paquetes pip/npm → hacerlo solo
- Configurar CUDA_VISIBLE_DEVICES → hacerlo solo (ya lo hace)
- Cambiar de rama git → hacerlo solo (ya lo hace parcialmente)
- Source de archivos de secretos → hacerlo solo (ya lo hace)
- Cargar un modelo en Ollama para verificar GPU → hacerlo solo

Lo que SÍ debe pedir al usuario:
- Instalar software que requiere admin (Docker, CUDA toolkit)
- Crear tokens/API keys (requiere login humano)
- Decisiones de negocio (qué modelo preferir, qué priorizar)

### 3. Arquitectura propuesta para v2

```
common_sense_engine_v2.py:

class ReasoningEngine:
    """Motor de razonamiento autónomo — no depende de reglas fijas."""
    
    def __init__(self, experiment_lab, strategy_selector):
        self.lab = experiment_lab
        self.selector = strategy_selector
    
    def reason(self, observations: dict) -> list[Conclusion]:
        """Pipeline: observe → detect anomalies → evaluate → act"""
        
        # Fase 1: Extraer hechos (igual que v1 pero extensible)
        facts = self.extract_facts(observations)
        
        # Fase 2: Detectar anomalías por comparación
        anomalies = self.detect_anomalies(facts)  # NUEVO
        
        # Fase 3: Forward chaining con reglas fijas (v1 legacy)
        rule_conclusions = self.forward_chain(facts)
        
        # Fase 4: Razonamiento por historial
        historical = self.consult_history(anomalies + rule_conclusions)  # NUEVO
        
        # Fase 5: Priorizar y filtrar
        prioritized = self.prioritize(historical)  # NUEVO
        
        # Fase 6: Ejecutar acciones seguras
        results = self.execute(prioritized)
        
        # Fase 7: Registrar en ExperimentLab para aprendizaje
        self.record(results)
        
        return results
    
    def detect_anomalies(self, facts):
        """Detecta anomalías SIN reglas fijas.
        
        Compara pares de recursos:
        - recurso_disponible vs recurso_en_uso → subóptimo si inferior en uso
        - estado_esperado vs estado_real → anomalía si difieren
        - tendencia_histórica → regresión si empeora
        """
        ...
    
    def consult_history(self, conclusions):
        """Consulta ExperimentLab antes de actuar.
        
        Para cada conclusión, verifica:
        - ¿Se intentó esta acción antes?
        - ¿Funcionó? (success_rate)
        - ¿Hay una alternativa mejor? (strategy_selector)
        """
        ...
```

### 4. Integración con ExperimentLab

El flujo para comparar algoritmos de razonamiento en paralelo:

```python
# En run_experiment, crear candidatos de razonamiento:
candidates = [
    ExperimentCandidate(label='forward_chain_v1', ...),  # reglas fijas actuales
    ExperimentCandidate(label='anomaly_detection_v1', ...),  # por anomalías
    ExperimentCandidate(label='hybrid_v1', ...),  # forward chain + anomalías
]

# Ejecutar ambos sobre los mismos hechos
lab.run_experiment(
    domain=ExperimentDomain.INFERENCE_BENCHMARK,
    objective='reasoning_quality',
    candidates=candidates,
    expected={'min_conclusions': 2, 'min_actionable': 1},
)

# StrategySelector elige el ganador basado en historial
recommendation = selector.recommend(
    domain=ExperimentDomain.INFERENCE_BENCHMARK,
    subject_key='common_sense_reasoning',
)
```

### 5. Pasos concretos de implementación

1. **Crear `common_sense_engine_v2.py`** con la clase `ReasoningEngine`
2. **Agregar anomaly detection** que compare recursos disponibles vs en uso
3. **Agregar consulta histórica** que use `ExperimentLab.record_outcome` antes de decidir
4. **Eliminar "NECESITA USUARIO"** para acciones que IABV puede hacer solo
5. **Integrar con ExperimentLab** para comparar v1 vs v2 en paralelo
6. **Registrar en viewmodel** como sección del auto-análisis
7. **Agregar MCP tool** para invocación directa
8. **Verificar GPU real**: que cuando Ollama cargue un modelo, lo fuerce a NVIDIA y confirme con `ollama ps` + `nvidia-smi`

### 6. Reglas de trabajo

- **Repo**: `jhonf463r/Python` — rama `devin/*` para auto-merge
- **Compilar siempre**: `python -m py_compile <archivo>` antes de commit
- **Tests**: `$env:PYTHONPATH='C:\Python\IABV_v1.5\src'; python -m pytest -p no:cacheprovider tests/ -q`
- **No tocar P1-P4** (capas cerradas)
- **No crear otro cerebro** — el orquestador es `AdaptiveTaskOrchestrator`
- **Auto-merge** por scripts si rama es `devin/*` y checks pasan

### 7. Estado del entorno del usuario (MSI laptop)
- **OS**: Windows 10 (26200.8246)
- **GPU0**: Intel UHD Graphics (iGPU)
- **GPU1**: NVIDIA GeForce RTX 4050 Laptop GPU (8GB VRAM)
- **CPU**: Intel (MSI MS-15K1)
- **RAM**: no reportada
- **Monitores**: 2 (1920x1080 principal + PnP genérico)
- **Red**: Ethernet (192.168.1.186) + VPN (TAP-Windows)
- **Python**: 3.13.2 (Miniconda)
- **Ollama**: v0.21.2 (6 modelos: qwen2.5-coder:7b, gpt-oss:20b, embeddinggemma)
- **Cuentas Chrome**: 9 (jhonf463r, proveedorjf, storeburve, hectorgeoruiz, harvytrujillo156, bonikobk, bisuteria.emfapro, cuent4numer4, emfaprochile)
- **Edge**: 1 (faber_1520@hotmail.com)
- **Secretos configurados**: 2/9 (faltan GITHUB_TOKEN, DEVIN_API_KEY_IABV, OPENAI_API_KEY, ANTHROPIC_API_KEY, CLOUDFLARE tokens)
- **Bluetooth**: Intel Wireless
- **Impresoras**: Samsung (default), OneNote, PDF
- **Audio**: 7 dispositivos (Nahimic, Intel SST, NVIDIA HD, Realtek)

### 8. Lo que el usuario espera ver en el próximo "analízate"

```
== RAZONAMIENTO AUTONOMO (SENTIDO COMUN v2) ==
  Hechos observados: 15
  Anomalías detectadas: 3
    [ANOMALÍA] Recurso superior NVIDIA RTX 4050 (8GB VRAM) sin carga activa
    [ANOMALÍA] 7 secretos esperados pero 0 cargados efectivamente
    [ANOMALÍA] 72 archivos modificados en main — probable trabajo no commiteado
  Reglas activadas: 4
  Conclusiones por historial: 2
    [APRENDIDO] force_ollama_to_nvidia: éxito en 3/3 ejecuciones previas → ejecutar
    [APRENDIDO] source_secrets: 0 secretos cargados en últimas 2 ejecuciones → archivo vacío
  Acciones ejecutadas: 5
    [EJECUTADO] Pre-cargó modelo qwen2.5-coder:7b en NVIDIA GPU (100% GPU) ← ESTO ES LO NUEVO
    [EJECUTADO] Configuró CUDA_VISIBLE_DEVICES=0
    [EJECUTADO] Verificó Ollama respondiendo en GPU via nvidia-smi ← ESTO ES LO NUEVO
    [EJECUTADO] Limpió 72 archivos cache/datos del working tree ← ESTO ES LO NUEVO
    [EJECUTADO] Verificó conectividad GitHub API (4934/5000 rate)
  Algoritmo ganador: hybrid_v1 (precision=0.92, robustness=0.85)
    vs forward_chain_v1 (precision=0.75, robustness=0.60)
  Tiempo de razonamiento: 1200ms
```

---

## RESUMEN EJECUTIVO PARA EL AGENTE

**Misión**: Construir un algoritmo de razonamiento que haga que IABV tome decisiones
obvias, sensatas y coherentes SIN que nadie se lo diga. IABV es la ventana del laptop
completo — tiene que actuar como dueño, no como reportero.

**Clave**: No más if/else hardcodeados. Razonamiento por anomalía + historial + ExperimentLab.

**Entregable**: PR con `common_sense_engine_v2.py` que supere a v1 en ExperimentLab.
