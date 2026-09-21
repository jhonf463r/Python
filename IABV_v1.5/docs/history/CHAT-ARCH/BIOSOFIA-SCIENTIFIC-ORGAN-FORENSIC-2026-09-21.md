# IABV v1.5 — FORENSIC AUDIT OF THE SCIENTIFIC ORGAN
## META-BIO-R01 — 2026-09-21

**Provenance:** static forensic audit on exact HEAD f0c98ca1af756273f14a7fae65fafa9bd69a3a30.
**Runtime:** NOT EXECUTED in this audit.
**Use:** canonical historical knowledge for future reconciliation; never substitute for a fresh current-state check.

## 1. RESULTADO CENTRAL
El órgano científico no está ausente. Está distribuido entre experimentación, medición, aprendizaje, OSES, recomendaciones, calibración y validación.
El problema encontrado es de composición causal: no se cerró la cadena científica completa desde pregunta/predicción hasta actualización de conocimiento/modelo y generación del siguiente experimento.

## 2. OWNERSHIP OBSERVADO
research gap → OSES findings, implícito.
hypothesis → SandboxExperiment.hypothesis, texto libre.
prediction → no entidad dedicada encontrada.
uncertainty → scientific proxy.
experimental design → SandboxExperiment.
control/treatment → baseline/candidate.
observation → ExperimentRun.
outcome → record_outcome().
analysis → scientific_proxy_engine.
falsation/qualification → no concepto explícito encontrado.
reproducibility → ReproducibilityValidationService, como inferencia basada en historial.
knowledge → KnowledgeItem, parcialmente auditado.
model/theory → no owner científico dedicado encontrado.
recommendation → ExperimentRecommendation / worker recommendation.
next experiment → no cadena automática confirmada.

## 3. ESTADO DEL LOOP
question/objective → NO EXPLICIT SCIENTIFIC ENTITY
research_gap → CODE
hypothesis → CODE, weakly structured
prediction → NOT PRESENT AS DEDICATED ENTITY
uncertainty → CODE/INVOKED AS PROXY
experimental_design → CODE
control/treatment → CODE VIA BASELINE/CANDIDATE
execution → INVOKED
observation → INVOKED
measurement → INVOKED
analysis → INVOKED
falsification/qualification → NOT PRESENT EXPLICITLY
independent reproduction → NOT PROVEN
knowledge artifact → OBSERVED / PARTIALLY AUDITED
model/theory update → NOT PRESENT AS SYSTEM OWNER
next hypothesis → NOT TRACED
next experiment → NOT TRACED AUTOMATICALLY

## 4. CAPACIDADES REALES QUE DEBEN CONSERVARSE
- registro de ejecuciones y outcomes;
- métricas descriptivas/proxies explícitos;
- comparación baseline-vs-candidate;
- recomendaciones y calibración;
- estimación de reproducibilidad a partir de historial;
- descubrimiento de research gaps;
- selección de estrategia y adaptive weighting.
Regla: scientific component exists ≠ scientific circuit closes.

## 5. LIMITACIONES CRÍTICAS
Prediction no tiene una entidad separada, dificultando demostrar que la expectativa existía antes del outcome.
No existe falsation/qualification explícita en el modelo científico auditado.
ReproducibilityValidationService no ejecuta una reproducción fresca independiente en el path inspeccionado.
reproducibility estimate ≠ independent reproduction
No apareció owner canónico de theory/model update.
Algunos ajustes siguen siendo descriptivos o human-facing y no constituyen todavía un cambio de política/parámetro que afecte causalmente el siguiente ciclo.

## 6. FIRST OPEN CAUSAL EDGE
ExperimentRun / ExperimentRecommendation → lector downstream concreto → siguiente hipótesis o SandboxExperiment.
La primera acción debe ser un barrido exhaustivo de lectores/consumidores de estos artefactos antes de inventar arquitectura.

## 7. MINIMUM DISCRIMINATING EXPERIMENT
Usar un outcome claramente positivo, uno negativo/contradictorio, un negative control con datos insuficientes, persistencia/cold restart y trazabilidad exacta producer→reader.
Observar si la diferencia de outcome genera una diferencia real en el siguiente experimento o backlog.

## 8. BIOSOFÍA / DESARROLLO
D0-D2: substantial substrate support.
D3: partial support through previously demonstrated experience→decision paths.
D4: requires the full observed deficit → hypothesis → variation → experiment → verified capability → future developmental decision chain.
D5-D9: open research hypotheses.
No promover inventario de módulos a afirmación de organismo o evolución.

## 9. KNOWLEDGE DELTA
1. El órgano científico es sustancial y distribuido.
2. El cuello de botella actual es la composición causal, no la ausencia total de maquinaria científica.
3. Prediction, falsation y model/theory update carecen de ownership científico claro en el path auditado.
4. La reproducibilidad actual debe interpretarse como estimación basada en evidencia histórica, no como reproducción independiente.
5. El primer edge abierto es producer→consumer desde outcome/recommendation hacia el siguiente experimento o decisión desarrollativa.
6. Debe completarse el barrido antes de añadir arquitectura.
7. Esta auditoría es estática y no cierra claims runtime.

## 10. FUTURE AUDIT RULE
Separar siempre: DEFINED → WIRED → INVOKED → OBSERVED → INDEPENDENTLY VERIFIED → CAUSALLY PROVEN → LEARNED → REUSED
Y conservar: NOT TESTED ≠ BROKEN
Este documento es un snapshot forense, no un current-state override.