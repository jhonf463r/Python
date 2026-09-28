# BIO-UNIVERSAL-09.11-R32-G2-V4 CONTRACT RECOGNITION

## OBJECTIVE
Reconocer el contrato de código antes de diseñar el experimento de threshold-crossing metacognitivo.

## CÓMO SE CALCULA actual_success

**Source**: `TaskOutcomeRecorder.record()` línea 321

```python
actual_success = run_record.status == RunStatus.SUCCESS
```

- Si `run_record.status == RunStatus.SUCCESS`: `actual_success = True`
- Si `run_record.status == RunStatus.FAILED`: `actual_success = False`
- Si `run_record.status` es otro valor (CANCELLED, etc.): `actual_success = False`

## QUÉ OCURRE CUANDO OllamaExpertProvider._run() FALLA

**Source**: `OllamaExpertProvider._run()` líneas 238-285

Cuando `_run()` falla:
1. **Timeout**: Lanza `httpx.TimeoutException`, capturado en línea 240
   - Intenta retry con payload reducido
   - Si retry también timeout: lanza `ProviderUnavailableError` (línea 254)
2. **ConnectError**: Lanza `httpx.ConnectError`, capturado en línea 264
   - Lanza `ProviderUnavailableError` (línea 266)
3. **HTTP Error**: Lanza `httpx.HTTPStatusError`, capturado en línea 315
   - Lanza `ProviderUnavailableError` (línea 318)
4. **Other Exception**: Capturado en línea 269
   - Intenta retry con payload reducido
   - Si retry también falla: lanza `ProviderUnavailableError` (línea 283)

**Crítico**: `ProviderUnavailableError` es una **excepción**, no un resultado fallido.

## QUÉ OCURRE CON finalize_with_run() ANTE PROVIDER FAILURE

**Source**: `InferenceService._execute()` líneas 37-77

```python
def _execute(self, method_name: str, request: InferenceRequest) -> RunRecord:
    started = time.perf_counter()
    adaptive_session = None
    try:
        if method_name == 'infer_task' and self.adaptive_orchestrator is not None:
            route, result, adaptive_session = self.adaptive_orchestrator.handle_request(request)
        else:
            router_method = getattr(self.router, method_name)
            route, result = router_method(request)
        status = RunStatus.PARTIAL if result.used_fallback else RunStatus.SUCCESS
        run_record = RunRecord(...)
        saved = self.run_repository.record(run_record)
        if adaptive_session is not None and self.adaptive_orchestrator is not None:
            finalized_session = self.adaptive_orchestrator.finalize_with_run(adaptive_session.session_id, saved)
        # ...
        return saved
    except Exception as exc:
        failed_route = RoleRoute(...)
        failed_result = InferenceResult(...)
        failed_record = RunRecord(
            request=request,
            result=failed_result,
            route=failed_route,
            status=RunStatus.FAILED,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error_summary=str(exc),
        )
        saved = self.run_repository.record(failed_record)
        if adaptive_session is not None and self.adaptive_orchestrator is not None:
            finalized_session = self.adaptive_orchestrator.finalize_with_run(adaptive_session.session_id, saved)
        return saved
```

**CRÍTICO**: Si el provider lanza excepción (incluyendo `ProviderUnavailableError`):
1. El bloque `except Exception` captura la excepción
2. Se crea un RunRecord con `status=RunStatus.FAILED`
3. Se persiste el RunRecord
4. Se llama `finalize_with_run()` con el RunRecord fallido
5. `TaskOutcomeRecorder.record()` se ejecuta con `actual_success=False` (porque RunStatus.FAILED)
6. `metacognitive_evaluation` se genera si hay recomendación previa

**Conclusión**: Un modelo inexistente o Ollama offline SÍ atraviesa la cadena de persistencia y produce `actual_success=False`.

## CÓMO SE CALCULA LA CONFIANZA DE ExperimentRecommendation

**Source**: `TaskOutcomeRecorder._extract_prediction()` línea 715

```python
conf = float(getattr(previous_recommendation, 'confidence', 0.0) or 0.0)
```

La confianza es el campo top-level `confidence` de la recomendación previa.

## QUÉ RECOMENDACIÓN PREVIA CONSUME _record_learning()

**Source**: `TaskOutcomeRecorder.record()` alrededor de línea 270

Para cada `subject_key` en `session.metadata['adaptive_learning']['subject_keys']`:
```python
recommendation = self.experiment_lab.repository.latest_recommendation(domain.value, subject_key)
```

## CONDICIONES EXACTAS PARA EVALUACIÓN METACOGNITIVA

**Source**: `TaskOutcomeRecorder._evaluate_prediction()` líneas 745-795

Condiciones para que `_evaluate_prediction()` retorne evaluación no vacía:
1. `prediction` no debe ser dict vacío (debe haber recomendación previa)
2. Debe haber `predicted_outcome` en prediction
3. Debe haber `confidence` en prediction

Cálculo de métricas:
```python
predicted_outcome = prediction.get('predicted_outcome', 'unknown')
confidence = float(prediction.get('confidence') or 0.0)
actual_outcome = 'success' if actual_success else 'failure'
predicted_success = predicted_outcome == 'success'

false_positive = predicted_success and not actual_success
false_negative = not predicted_success and actual_success
cal_error = abs(confidence - (1.0 if actual_success else 0.0))
```

## UMBRALES EXACTOS DE _experiment_run_metacognitive_findings()

**Source**: `OperationalSelfExaminationService._experiment_run_metacognitive_findings()`

- Estructural: `total >= 5` (evidence_basis is not None)
- Metacognitivo: `len(mc_cal_errors) >= 3`
- Miscalibración: `avg_ce > 0.4`
- Sobreconfianza: `mc_fp >= 2 and mc_fp > mc_fn`
- Infraconfianza: `mc_fn >= 2 and mc_fn > mc_fp`

## CONDICIONES EXACTAS DE FINDINGS

**task_packet_metacognitive_overconfidence**:
```python
if mc_fp >= 2 and mc_fp > mc_fn:
    # Emit finding
```

**task_packet_metacognitive_underconfidence**:
```python
if mc_fn >= 2 and mc_fn > mc_fp:
    # Emit finding
```

**task_packet_metacognitive_miscalibration**:
```python
if avg_ce > 0.4:
    # Emit finding
```

## CAMBIO EXACTO QUE APLICA _apply_metacognitive_feedback()

**Source**: `OperationalSelfExaminationService._apply_metacognitive_feedback()` líneas 1100-1126

```python
if finding.category == 'task_packet_metacognitive_overconfidence':
    adj = -0.08
elif finding.category == 'task_packet_metacognitive_underconfidence':
    adj = 0.06
else:  # miscalibration
    avg_ce = finding.metadata.get('avg_calibration_error', 0.5)
    adj = -0.04 if avg_ce > 0.5 else -0.02

applied = self.adaptive_weight_layer.apply_metacognitive_adjustment(
    route=dominant_route,
    assistant_kind=dominant_ak,
    adjustment=adj,
    reason=reason,
)
```

## CÓMO SE LEE DE VUELTA EL AJUSTE PERSISTIDO

**Source**: `AdaptiveWeightLayer` líneas 18-33, 280-304

**Constructor**:
```python
def __init__(self, *, persistence_path: str | None = None) -> None:
    self._metacognitive_adjustments: dict[str, dict[str, Any]] = {}
    _rel = Path('data') / 'evolution' / 'adaptive_weights' / 'metacognitive_adjustments.json'
    if persistence_path is not None:
        self._weights_path: Path | None = Path(persistence_path)
    else:
        workspace = (
            os.environ.get('IABV_WORKSPACE')
            or os.environ.get('IABV_WORKSPACE_ROOT')
            or ''
        )
        if workspace:
            self._weights_path = Path(workspace) / _rel
        else:
            self._weights_path = Path.cwd() / _rel
    self._load_persisted()
```

**Persistencia**:
```python
def _persist(self) -> None:
    if self._weights_path is None:
        return
    try:
        self._weights_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**self._metacognitive_adjustments, '_version': 1}
        tmp = self._weights_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self._weights_path)
    except Exception:
        _logger.warning('metacognitive_adjustments: persistence failed', exc_info=True)
```

**Carga**:
```python
def _load_persisted(self) -> None:
    if self._weights_path is None or not self._weights_path.exists():
        return
    try:
        raw = self._weights_path.read_text(encoding='utf-8')
        data = json.loads(raw)
        if isinstance(data, dict):
            version = data.pop('_version', None)
            for k, v in data.items():
                if isinstance(v, dict) and 'adjustment' in v:
                    self._metacognitive_adjustments[k] = v
    except Exception:
        _logger.debug('metacognitive_adjustments: corrupt file, starting empty')
```

**Lectura de ajuste**:
```python
def get_metacognitive_adjustment(self, route: str, assistant_kind: str) -> float:
    key = f"{route}|{assistant_kind}".strip().lower()
    entry = self._metacognitive_adjustments.get(key)
    return float(entry['adjustment']) if entry else 0.0
```

**Ruta del archivo**: `{workspace}/data/evolution/adaptive_weights/metacognitive_adjustments.json`

## RESUMEN DE CONTRATO PARA DISEÑO DE EXPERIMENTO

1. **actual_success**: `run_record.status == RunStatus.SUCCESS`
2. **Provider failure**: Se captura en `InferenceService._execute()`, crea RunRecord con `RunStatus.FAILED`, y llama `finalize_with_run()`
3. **finalize_with_run()**: Siempre se llama con el RunRecord (success o failed)
4. **TaskOutcomeRecorder.record()**: Siempre se ejecuta, calcula `actual_success` y genera `metacognitive_evaluation` si hay recomendación previa
5. **Recomendación previa**: `latest_recommendation(domain, subject_key)` desde ExperimentLab
6. **subject_keys**: Se recuperan de `session.metadata['adaptive_learning']['subject_keys']` después de `finalize_with_run()`
7. **Umbrales OSES**:
   - Estructural: `total >= 5`
   - Metacognitivo: `len(mc_cal_errors) >= 3`
   - Miscalibración: `avg_ce > 0.4`
   - Sobreconfianza: `mc_fp >= 2 and mc_fp > mc_fn`
   - Infraconfianza: `mc_fn >= 2 and mc_fn > mc_fp`
8. **Ajuste AWL**: -0.08 (sobreconfianza), +0.06 (infraconfianza), -0.04/-0.02 (miscalibración)
9. **Persistencia AWL**: JSON en `{workspace}/data/evolution/adaptive_weights/metacognitive_adjustments.json`
10. **Fresh-process read-back**: Nueva instancia de AdaptiveWeightLayer con mismo `persistence_path` carga automáticamente el ajuste

## ESTRATEGIA DE EXPERIMENTO

Basado en el contrato, el experimento mínimo discriminante es:

1. **Warm-up**: Ejecutar con modelo real (gemma3:1b) para generar recomendación
   - Esto crea ExperimentRun con `actual_success=True`
   - TaskOutcomeRecorder genera recomendación

2. **Target**: Ejecutar con modelo inexistente o Ollama detenido
   - Esto causa `ProviderUnavailableError`
   - InferenceService captura excepción, crea RunRecord con `RunStatus.FAILED`
   - TaskOutcomeRecorder calcula `actual_success=False`
   - Si hay recomendación previa con confidence alta → false_positive (sobreconfianza)
   - Si hay recomendación previa con confidence baja → false_negative (infraconfianza)

3. **Repetir**: Crear suficientes runs para cruzar umbrales:
   - `total >= 5` (evidence_basis)
   - `len(mc_cal_errors) >= 3` (metacognitive evaluations)
   - `mc_fp >= 2` o `mc_fn >= 2` (threshold de finding)

4. **Verificar**: Ejecutar OSES review y verificar finding emitido
5. **Verificar AWL**: Leer archivo `metacognitive_adjustments.json` y crear nueva instancia para read-back

**Cambio de modelo**: Necesito verificar cómo cambiar el modelo del provider entre warm-up y target.
