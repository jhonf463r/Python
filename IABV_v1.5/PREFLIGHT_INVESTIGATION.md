# Preflight Gate — Causa Raíz de los 8 Tests Humanizados Rotos

## Resumen Ejecutivo

El problema NO es que falten mensajes humanizados — **ya existen todos en el código**. El problema es que el flujo nunca los alcanza porque el **preflight gate aborta antes de ejecutar la consulta externa**.

Los tests mockean `tool_teach_service.execute_external_consultation` para simular fallos específicos. Esperan que el VM: (1) llame al mock, (2) reciba un `ExternalConsultationResult` fallido con flags específicos, (3) humanice ese fallo. Pero el VM corta en el paso 0: el preflight decide que la ruta externa no es viable y nunca llega al mock.

## Evidencia

### Debug capturado en entorno de test

Invocando `adaptive_task_orchestrator.preflight_external_assistant(user_goal='revisa con codex porfa', assistant_kind='codex')` en un `_make_bootstrap()`:

```
blocked: True
reason: 'No pude confirmar que Codex instalado este disponible en este entorno antes de usarlo.'
governance.approval_required: False
governance.block_risky_action: True
governance.autonomy_level: guarded_local
governance.recommended_action: continue_local
governance.blockers: ['No pude verificar el hilo activo de Codex porque no encontre su estado local.']
approval_checkpoints: 0
wm.active_windows: 0
wm.permission_gates: 0
wm.detected_blocks: ['assistant_unavailable']
wm.tool_live_status count: 8
```

### Trazabilidad línea por línea

1. **`control_center_viewmodel.py:4281`** — VM llama al preflight antes de cualquier ejecución:
   ```python
   preflight = self.adaptive_orchestrator.preflight_external_assistant(
       user_goal=self._last_user_goal or 'abre Wplay e inicia sesion',
       assistant_kind=requested_assistant_kind,
   )
   if bool(preflight.get('blocked')):
       return self._blocked_external_consultation_result(...)
   ```

2. **`adaptive_task_orchestrator.py:1430`** — `blocked` se deriva de governance:
   ```python
   'blocked': bool(governance.get('block_risky_action') or governance.get('approval_required')),
   ```

3. **`autonomy_governance_policy.py:571-600`** — si `world_model.block_records` contiene `assistant_unavailable`, governance retorna `block_risky_action=True`:
   ```python
   explicit_record = next(
       (item for item in block_records
        if item.block_type in {'wrong_thread', 'account_limited',
                                'browser_security_verification',
                                'assistant_unavailable',
                                'network_blocked'}),
       None,
   )
   if explicit_record is not None:
       ...
       return self._snapshot(
           ...
           block_risky_action=True,
           ...
       )
   ```

4. **`control_center_viewmodel.py:4504-4507`** — al quedar bloqueado, el VM imprime un mensaje genérico que NO es el humanizado que esperan los tests:
   ```python
   message = (
       f'No voy a lanzar {assistant_title} porque la ruta ya aparece bloqueada antes de intentarla. '
       f'{reason or "Mantengo la via local hasta que el bloqueo cambie."}'
   )
   ```

5. **Las frases humanizadas SÍ existen** (en `_human_external_consultation_failure` y `_external_state_notice`):
   - `'tracking del hilo'` → `control_center_viewmodel.py:2699, 2739`
   - `'verificacion de seguridad'` → `control_center_viewmodel.py:2690`
   - `'hilo esperado'` → `control_center_viewmodel.py:2741`
   - `'cuota, plan o cuenta'` → `control_center_viewmodel.py:2735`
   - `'otra via'` + `'seguir con lo que ya tenemos'` → `control_center_viewmodel.py:2706-2710`

   Todas están en código que **solo se alcanza si preflight NO bloquea**.

## Patrón común de los 5 tests de humanización

Los 5 tests (líneas 2588, 2640, 2692, 2742, 2789 en `tests/test_control_center_viewmodel.py`) hacen EXACTAMENTE lo mismo:

```python
original = bootstrap.tool_teach_service.execute_external_consultation
def fake_execute_external_consultation(**kwargs):
    task, result, meta = original(**{**kwargs, 'launch_dry_run': True})
    blocked = result.model_copy(update={
        'success': False,
        'error_message': <condición específica>,
        'execution_state': ExecutionState(state='failed', ..., metadata={<flags específicos>}),
        'metadata': {'external_state_flags': [<flags>]},
    })
    return task, blocked, meta
bootstrap.tool_teach_service.execute_external_consultation = fake_execute_external_consultation

viewmodel.sendChat('<prompt explícito pidiendo codex/chatgpt>')
_drain_ui(viewmodel)

assert '<frase humanizada>' in viewmodel.get_chat_messages()[-1]['text']
```

Los 5 casos y condiciones:

| # | Test | error_message | metadata clave | Frase esperada |
|---|---|---|---|---|
| 1 | explicit_codex_blocked_external | `'quota_exhausted'` | `credits_exhausted=True, quota_status='exhausted'` | `'cuota, plan o cuenta'` |
| 2 | explicit_codex_wrong_thread | `'wrong_thread'` | `thread_verification='wrong_thread', capture_unverified=True` | `'hilo esperado'` |
| 3 | explicit_codex_missing_thread_tracking | `'codex_state_missing'` | `missing_thread_tracking=True` | `'tracking del hilo'` |
| 4 | explicit_chatgpt_security_verification | `'browser_security_verification'` | `capture_unverified=True` | `'verificacion de seguridad'` |
| 5 | external_access_denied | `'[WinError 5] Acceso denegado'` | (no flags especiales) | `'otra via'` OR `'seguir con lo que ya tenemos'` |

Todos los prompts son explícitos: `'revisa con codex porfa'`, `'consulta chatgpt'`, `'Necesito una consulta externa con ChatGPT'`, etc. El usuario está pidiendo la ruta externa a propósito.

## Diagnóstico Raíz

`wm.block_records` en el bootstrap de test contiene un `BlockRecord(block_type='assistant_unavailable', ...)` porque el `WorldModel` construido por el `ToolLiveStatus` detecta que `Codex instalado` / `ChatGPT` no están abiertos como aplicaciones vivas en el entorno (no hay Qt app real corriendo, no hay `%USERPROFILE%\.codex\state_5.sqlite`, no hay browser activo).

**En producción Windows real**: si Codex está abierto con hilo correcto y cuenta activa, `assistant_unavailable` NO aparece → preflight pasa → execute corre → si falla por cuota/thread/security/WinError, la humanización existente se aplica correctamente.

**En entorno de test**: `assistant_unavailable` aparece SIEMPRE → preflight bloquea SIEMPRE → execute_external_consultation nunca se llama → los mocks no se disparan → las humanizaciones específicas nunca se alcanzan → los 5 tests fallan.

**Tres tests adicionales** (665 `build_request_uses_visual_signal_snapshot`, 745 `operational_teaching_prompt`, 3029 `compound_self_awareness`) fallan por razones independientes al preflight — cada uno es su propio bug de ruteo interno. No son parte del mismo fix.

## Propuesta de Fix (mínima, quirúrgica, segura)

**Observación clave:** `'assistant_unavailable'` NO es un bloqueo operativo real tan definitivo como los otros 4 tipos en ese mismo match (`wrong_thread`, `account_limited`, `browser_security_verification`, `network_blocked`). Los otros 4 reflejan estados verificados por observación viva (hilo comparado, cuenta agotada, captcha detectado, red desconectada). `'assistant_unavailable'` refleja **ausencia de confirmación**, no un bloqueo verificado.

Cuando el usuario pide explícitamente la ruta externa, la política correcta es:
- intentar la ejecución,
- dejar que la capa de ejecución real (tool adapter) falle con su error específico,
- humanizar ese fallo (lo que ya sabe hacer el VM).

**Candidato A — Downgrade de `assistant_unavailable` a warning, no block:**
En `autonomy_governance_policy.py:565-600`, quitar `'assistant_unavailable'` del set que fuerza `block_risky_action=True`. En su lugar, devolverlo como `diagnostic_category='assistant_unavailable'` con `block_risky_action=False`, permitiendo que preflight pase y execute intente.

- **Pros**: mínimo (1 linea), semánticamente correcto (no es bloqueo verificado), no toca VM.
- **Contras**: en producción podría dejar pasar intentos que fallaran de todos modos.
- **Mitigación**: el downstream (`execute_external_consultation`) ya detecta el fallo real y lo humaniza. El usuario ve el mismo mensaje útil que vería en test.

**Candidato B — Bypass en VM cuando la preferencia es explícita y el único bloqueo es `assistant_unavailable`:**
En `control_center_viewmodel.py:4285`, después de detectar preflight bloqueado, si `explicit_assistant_preference == requested_assistant_kind` Y `governance.diagnostic_category == 'assistant_unavailable'` Y no hay otros bloqueos, proceder a ejecutar con un warning preservado.

- **Pros**: respeta policy global, solo afecta casos de preferencia explícita del usuario.
- **Contras**: más código, más ramas, más riesgo.

**Candidato C — Humanizar el mensaje de preflight-block directamente:**
En `_blocked_external_consultation_result` (`control_center_viewmodel.py:4462`), en vez de imprimir el mensaje genérico, pasar por `_human_external_consultation_failure` con los flags del governance.

- **Pros**: aplica para todos los casos de bloqueo.
- **Contras**: NO resuelve los 5 tests porque el test espera flags específicos del `ExecutionState` mockeado (`credits_exhausted`, `thread_verification`, etc.), que solo existen si execute corre. El adaptive_evolution_text también necesita que `payload` tenga el estado `blocked_external` y los `external_state_flags` del mock.

## Recomendación

**Candidato A es el fix correcto y suficiente.** Cambio de 1 línea en `autonomy_governance_policy.py`:

```python
# antes:
if item.block_type in {'wrong_thread', 'account_limited', 'browser_security_verification', 'assistant_unavailable', 'network_blocked'}

# después:
if item.block_type in {'wrong_thread', 'account_limited', 'browser_security_verification', 'network_blocked'}
```

Y manejar `assistant_unavailable` por separado como `diagnostic_category` sin `block_risky_action`. El impacto:

- **Los 5 tests de humanización pasan** porque el preflight deja de bloquear por `assistant_unavailable`, execute_external_consultation corre el mock, y la humanización existente se aplica.
- **Producción**: si Codex/ChatGPT no están disponibles en Windows real, el tool adapter fallará con `FileNotFoundError` o `ConnectionError` específico. El VM ya sabe humanizar esos fallos (`_human_external_consultation_failure` tiene ramas para `acceso denegado`, `session`, etc.). El usuario verá un mensaje similar al que veía antes.
- **No hay pérdida de seguridad**: los 4 bloqueos reales verificados (`wrong_thread`, `account_limited`, `browser_security_verification`, `network_blocked`) siguen bloqueando preflight.

## UNRESOLVED / Fuera de Scope

- **Test 665** (`build_request_uses_visual_signal_snapshot_and_formal_ia_trace`): bug aparte. Requiere su propia investigación — espera que `request.metadata['visual_signal']['capture_available']` sea `True` y que `ia_trace[0]` tenga trace_id específico. No relacionado al preflight.
- **Test 745** (`operational_teaching_prompt_does_not_bypass_into_learning_chat`): bug aparte. Espera que el prompt largo de Wplay entre en inferencia normal y que `site_hint='wplay'` se preserve.
- **Test 3029** (`compound_self_awareness_message_goes_through_inference`): bug aparte. Espera que un mensaje compuesto no entre por el shortcut de self-awareness.

Estos 3 requieren sus propios análisis y probablemente fixes en ruteo de `sendChat` (detección de intent y shortcuts). No son un solo fix.

## Colisión con Sesión Paralela

**Verificada, CERO conflicto textual.** La rama `devin/1776623476-control-master-wiring` toca:
- `adaptive_task_orchestrator.py`: `__init__` (+2 lineas), línea ~885 (+3), nuevo método `_control_master_digest()` (~línea 997).
- `control_center_viewmodel.py`: `__init__` (+6 lineas), línea ~3937 (+1).

Mi fix propuesto solo toca `autonomy_governance_policy.py` (archivo que la rama paralela NO toca), en ~1 línea. Sin colisión.

## Plan de Ejecución (si apruebas)

1. Rama nueva `devin/<ts>-preflight-assistant-unavailable` desde `main`.
2. Fix de 1 línea en `autonomy_governance_policy.py` + ajustar retorno del branch downgradeado.
3. Correr los 5 tests humanizados → debe pasar 5/5.
4. Correr regresión focalizada: `test_control_center_viewmodel.py`, `test_autonomy_governance_policy.py`, `test_adaptive_task_orchestrator.py` → 0 regresiones esperadas.
5. Correr batería completa → comparar vs baseline actual (10 failing).
6. PR con evidencia pre/post.

Duración estimada: 30-45 min hasta PR abierto.
