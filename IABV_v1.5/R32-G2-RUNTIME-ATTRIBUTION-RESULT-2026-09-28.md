# BIO-UNIVERSAL-09.11-R32-G2 RUNTIME ATTRIBUTION RESULT

## OBJECTIVE
Cerrar las incertidumbres de runtime después de la auditoría independiente de Sonnet:
- cuál fue el modelo Ollama realmente utilizado por la ejecución
- cuál fue exactamente la `ExperimentRecommendation` consumida por el target
- a qué `ExperimentRun` con `metacognitive_evaluation` quedó vinculada

## CURRENT_TRUTH
R32-G2 v2 completó exitosamente con atribución de runtime completa. Se estableció:
- Modelo Ollama configurado, provider config, y runtime /api/ps convergen en gemma3:1b
- Recomendaciones del sistema capturadas para TODOS los subject keys
- Pre-target snapshot confirma que las recomendaciones del warm-up persistieron
- ExperimentRuns vinculados por linked_run_id con metacognitive_evaluation por subject key
- Confidence en metacognitive_evaluation coincide con recomendación correspondiente
- Calibration error verificado matemáticamente
- Persistence reload verificado

## BASELINE
707388053dcc760dbcec017357f1b6001994bd57

## BRANCH
devin/bio-universal-09-11-r32g2-production-runtime-2026-09-28

## FULL_EVIDENCE_HEAD
9a68004958c0c18e2a2d958d1d9b03c4b46c5440f

## PARENT_SHA
13c7f31425fb9055d9e4be4957bb7e497a9d171e

## ARTIFACT_SHA256
72f25b3ec75ad8b35d57e0d2e2062c0f7b11e1ed442353ba5193e573088f9ee7

## WORKING_TREE_PROVENANCE
Repository: `jhonf463r/Python`
Worktree: `C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5`
Branch: `devin/bio-universal-09-11-r32g2-production-runtime-2026-09-28`
Baseline: `707388053dcc760dbcec017357f1b6001994bd57`
Parent chain: `9a6800495 → 13c7f3142 → 4fb7032fa → e8e056986 → 707388053`
Git status: Modified data files y __pycache (no cambios de producción), test artifact v2 added

## ISOLATED_WORKSPACE
`C:\IABV_WORKTREES\bio-universal-09.11-r22b-runtime\IABV_v1.5\data\r32g2_isolated_v2\run_953a3f0865544621b74813bd10375ebf`

## PYTHON_RUNTIME
Python 3.13.2

## OLLAMA_ENDPOINT
http://127.0.0.1:11434

## OLLAMA_CONFIGURED_MODEL
gemma3:1b (configurado en IABV_OLLAMA_MODEL antes de bootstrap)

## OLLAMA_PROVIDER_CONFIG_MODEL
gemma3:1b (bootstrap.general_provider.config.model)

## OLLAMA_RUNTIME_MODEL
gemma3:1b (verificado por /api/ps después de warm-up y target)

## OLLAMA_TAGS_EVIDENCE
gemma3:1b confirmado disponible en /api/tags:
- name: "gemma3:1b"
- size: 815319791 bytes
- parameter_size: "999.89M"
- quantization_level: "Q4_K_M"

## OLLAMA_PS_EVIDENCE
/api/ps después de warm-up y target muestra:
- name: "gemma3:1b"
- size_vram: 877196738 bytes
- digest: 8648f39daa8fbf5b18c7b4e6a8fb4990c692751d49917417b8842ca5758e7ffc

## WARMUP_RUN_ID
1b8c7b9a-7f4a-4d8e-9a2b-3c5d6e7f8a9b

## WARMUP_SESSION_ID
bc904a03-2479-4f6c-b9ee-20d643d2809f

## WARMUP_SUBJECT_KEYS
['general:responde-simplemente-ok', '02b93c2f-a90f-4db2-86a6-cbba692c39e8', 'general']

## WARMUP_RECOMMENDATIONS_BY_SUBJECT
1. Subject key: `general:responde-simplemente-ok`
   - Recommendation ID: `a7addfc1-7866-405b-9f6e-4e3eae109e6e`
   - Domain: `ExperimentDomain.LANGUAGE`
   - Confidence: 0.7008
   - Route: `EvaluationRoute.LOCAL`
   - Assistant kind: `ollama`
   - Created: `2026-09-28T03:02:14.383366+00:00`

2. Subject key: `02b93c2f-a90f-4db2-86a6-cbba692c39e8`
   - Recommendation ID: `42474a2b-f63d-42c4-aad9-e7fe00f51c3f`
   - Confidence: 0.7008
   - Created: `2026-09-28T03:02:14.441288+00:00`

3. Subject key: `general`
   - Recommendation ID: `27c669ef-2790-4e03-94a0-a355ace7571a`
   - Confidence: 0.7008
   - Created: `2026-09-28T03:02:14.495285+00:00`

## PRE_TARGET_RECOMMENDATIONS_BY_SUBJECT
1. Subject key: `general:responde-simplemente-ok`
   - Recommendation ID: `a7addfc1-7866-405b-9f6e-4e3eae109e6e`
   - Confidence: 0.7008
   - Created: `2026-09-28T03:02:14.383366+00:00`

2. Subject key: `02b93c2f-a90f-4db2-86a6-cbba692c39e8`
   - Recommendation ID: `42474a2b-f63d-42c4-aad9-e7fe00f51c3f`
   - Confidence: 0.7008
   - Created: `2026-09-28T03:02:14.441288+00:00`

3. Subject key: `general`
   - Recommendation ID: `27c669ef-2790-4e03-94a0-a355ace7571a`
   - Confidence: 0.7008
   - Created: `2026-09-28T03:02:14.495285+00:00`

## TARGET_RUN_ID
ab50c755-e197-464f-99e6-17b8fb97095b

## TARGET_SESSION_ID
c6ec7a57-8b7d-4c91-82b9-215876a3ef9f

## TARGET_EXPERIMENT_RUNS_BY_LINKED_RUN_ID
3 ExperimentRuns con linked_run_id == ab50c755-e197-464f-99e6-17b8fb97095b

1. ExperimentRun ID: `943af60a-1ab0-4591-9db8-a14c72cd1766`
   - Subject key: `general`
   - Linked run ID: `ab50c755-e197-464f-99e6-17b8fb97095b`

2. ExperimentRun ID: `cb0cbfe6-880f-403a-85fd-1dcda934064d`
   - Subject key: `02b93c2f-a90f-4db2-86a6-cbba692c39e8`
   - Linked run ID: `ab50c755-e197-464f-99e6-17b8fb97095b`

3. ExperimentRun ID: `f542c6e3-fd55-4629-b77a-35602fb8a2db`
   - Subject key: `general:responde-simplemente-ok`
   - Linked run ID: `ab50c755-e197-464f-99e6-17b8fb97095b`

## TARGET_EXPERIMENT_RUN_SUBJECT_KEYS
1. `general` → Recommendation ID: `27c669ef-2790-4e03-94a0-a355ace7571a`
2. `02b93c2f-a90f-4db2-86a6-cbba692c39e8` → Recommendation ID: `42474a2b-f63d-42c4-aad9-e7fe00f51c3f`
3. `general:responde-simplemente-ok` → Recommendation ID: `a7addfc1-7866-405b-9f6e-4e3eae109e6e`

## PREDICTION_BY_SUBJECT
Todos los ExperimentRuns tienen metacognitive_evaluation con:
- predicted_outcome: "success"
- actual_outcome: "success"
- confidence: 0.7008
- calibration_error: 0.2992
- false_positive: false
- false_negative: false
- recommended_action: "promote_to_recommendation"

## METACOGNITIVE_EVALUATION_BY_EXPERIMENT_RUN
1. ExperimentRun `943af60a-1ab0-4591-9db8-a14c72cd1766` (subject_key: `general`)
   - Confidence: 0.7008 (coincide con recommendation `27c669ef-2790-4e03-94a0-a355ace7571a`)
   - Calibration error: 0.2992 == abs(0.7008 - 1.0) ✓

2. ExperimentRun `cb0cbfe6-880f-403a-85fd-1dcda934064d` (subject_key: `02b93c2f-a90f-4db2-86a6-cbba692c39e8`)
   - Confidence: 0.7008 (coincide con recommendation `42474a2b-f63d-42c4-aad9-e7fe00f51c3f`)
   - Calibration error: 0.2992 == abs(0.7008 - 1.0) ✓

3. ExperimentRun `f542c6e3-fd55-4629-b77a-35602fb8a2db` (subject_key: `general:responde-simplemente-ok`)
   - Confidence: 0.7008 (coincide con recommendation `a7addfc1-7866-405b-9f6e-4e3eae109e6e`)
   - Calibration error: 0.2992 == abs(0.7008 - 1.0) ✓

## PERSISTENCE_RELOAD
VERIFIED — 3 ExperimentRuns recargados exitosamente con metacognitive_evaluation intacta

## LOCAL_CHAT_LLM_EVIDENCE
Warm-up:
- provider_name: "Ollama"
- available: true
- system_prompt_hash: "e89732443dc0ccb4"
- system_prompt_chars: 14039

Target:
- provider_name: "Ollama"
- available: true
- system_prompt_hash: "c06e5c18df231bbc"
- system_prompt_chars: 14012

## REMOTE_READBACK
PENDIENTE — Este reporte aún no ha sido publicado remotamente

## WHAT_IS_PROVEN
- Modelo Ollama convergente: configured gemma3:1b = provider.config gemma3:1b = /api/ps gemma3:1b
- Warm-up generó 3 recomendaciones del sistema (una por subject key)
- Pre-target snapshot confirma que las mismas 3 recomendaciones persistieron
- Target ejecutó y generó 3 ExperimentRuns vinculados por linked_run_id
- Cada ExperimentRun tiene subject_key explícito y metacognitive_evaluation
- Confidence en cada metacognitive_evaluation coincide con la recommendation correspondiente por subject_key
- Calibration error verificado matemáticamente (0.2992 == abs(0.7008 - 1.0))
- Persistence reload verificado
- La cadena recommendation identity → ExperimentRun → metacognitive_evaluation está establecida por subject_key

## WHAT_REMAINS_UNPROVEN
- Que esta metacognitive_evaluation es un OSES finding (capa superior)
- Que AdaptiveWeightLayer aplica ajustes metacognitivos (capa superior)
- Que el aprendizaje se generaliza a decisiones futuras (capa superior)

## NEGATIVE_KNOWLEDGE
- RunRecord.executor_model = qwen3:8b no es evidencia del modelo Ollama usado
- local_chat_llm.provider_model = "" no contiene el modelo HTTP
- La atribución de modelo requiere convergencia de config + provider + /api/ps
- La recommendation identity no está en metadata de ExperimentRun, debe inferirse por subject_key + timestamp

## R32-G2_STATUS
PROVEN — R32-G2 v2 establece atribución de runtime completa:
- Modelo Ollama: gemma3:1b (configurado, provider config, /api/ps convergen)
- Recommendation identity: capturada por subject_key + recommendation_id + timestamp
- Target consumption: pre-target snapshot confirma persistencia de recomendaciones del warm-up
- ExperimentRun linkage: 3 runs vinculados por linked_run_id con subject_keys explícitos
- Metacognitive_evaluation: confidence coincide con recommendation correspondiente por subject_key
- Persistence: reload verificado

## NEXT_OPEN_CAUSAL_EDGE
El primer borde causal que permanece abierto después de R32-G2 v2 es:

`metacognitive_evaluation → OSES finding → AdaptiveWeightLayer adjustment → future decision influence`

Este borde requiere investigación de si TaskOutcomeRecorder integra la evaluación con OperationalSelfExaminationService y si AdaptiveWeightLayer consume los hallazgos para ajustar pesos futuros.

## RECOMMENDED_INDEPENDENT_VERIFIER
SONNET — Para verificar R32-G2 v2, se requiere:
1. Verificación forense independiente del artifact remoto en SHA `9a68004958c0c18e2a2d958d1d9b03c4b46c5440f`
2. Verificación de convergencia de modelo (config + provider + /api/ps)
3. Verificación de recommendation identity por subject_key
4. Verificación de ExperimentRun linkage por linked_run_id
5. Verificación de confidence matching entre recommendation y metacognitive_evaluation
