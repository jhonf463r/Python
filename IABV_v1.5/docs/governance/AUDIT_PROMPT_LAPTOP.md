# IABV v1.5 - Prompts de Auditoria Real en Laptop (Segmentados)

**Actualizado:** 2026-05-04
**Para usar con:** Windsurf, Codex, o cualquier agente en la laptop del usuario
**Prerequisito:** El repo debe estar en `C:\Python\IABV_v1.5` con `PYTHONPATH=src`

---

## INSTRUCCION PRINCIPAL

Eres el auditor de validacion real de IABV v1.5. Ejecuta pruebas reales
en la laptop Windows y confirma que los cambios funcionan en el entorno real.

**No modifiques codigo.** Solo observa, mide y reporta.

---

## CONTEXTO DE CAMBIOS APLICADOS

### Fase 1 — ControlCenterVM lazy init
- `_initialize_heavy()` + `_bg_initial_refresh()` en `control_center_viewmodel.py`
- Heavy I/O movido a `_bg_pool.submit()` via `QTimer.singleShot(0)`

### Fase 1b — DashboardVM lazy init (NUEVO)
- `_bg_refresh()` + `_apply_refresh()` + `refreshResolved` signal en `dashboard_viewmodel.py`
- `refresh()` ahora es non-blocking: submit a `_bg_pool` (ThreadPoolExecutor)
- `list_recent()` y `describe_index()` corren en background thread
- Resultado aplicado en main thread via `refreshResolved.connect(_apply_refresh)`

### Fase 2 — Quota tracker wiring
- `_record_quota_usage()` en `adaptive_task_orchestrator.py`
- Llama `record_message_sent(tool, email)` antes de cada despacho externo

### Fase 3 — worker_pool_snapshot en WorldModelSnapshot
- Campo `worker_pool_snapshot: dict` en `domain/models.py`
- `_estimate_worker_pool()` en `world_model_service.py` con timeout 2s

### UI Visibility Audit (NUEVO)
- `src/iabv_v15/infra/ui_visibility_audit.py`
- Captura popups, dialogs, toasts, errores FileNotFound, eventos background
- JSONL append-only en `data/logs/visible_events.jsonl`

---

## PROMPT SEGMENTO 1: ARRANQUE Y BLOQUEO

```
Eres auditor de IABV v1.5. Solo verifica arranque.

Ejecuta:
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

Paso 1 - Medir arranque:
- Arranca la aplicacion normalmente
- Mide tiempo hasta que la ventana sea visible y responsiva
- Verifica que NO hay freeze (Responding=True siempre)
- El ControlCenter debe cargar cards en background (2-5s despues)
- El Dashboard debe cargar summary cards en background (no bloquea main thread)

Paso 2 - Verificar DashboardVM:
- Las summary cards (Episodios, Conocimiento, Ejecuciones, Indexado) deben
  aparecer DESPUES del arranque, no durante __init__
- No debe haber Responding=False en ningun momento post-arranque

Paso 3 - Tests focalizados:
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/test_dashboard_lazy_init.py tests/test_control_center_viewmodel.py -q --tb=short

Reporta:
- Tiempo hasta ventana visible: ___ms
- Freeze observable: Si/No
- DashboardVM cards cargaron en background: Si/No
- Tests: passed/failed
```

---

## PROMPT SEGMENTO 2: QUOTA TRACKER

```
Eres auditor de IABV v1.5. Solo verifica quota tracker.

Ejecuta:
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

Paso 1 - Verificar record_message_sent wiring:
& 'C:\Users\faber\miniconda3\python.exe' -c "
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
import inspect
src = inspect.getsource(AdaptiveTaskOrchestrator)
if '_record_quota_usage' in src:
    print('PASS: _record_quota_usage existe en ATO')
    if 'record_message_sent' in src:
        print('PASS: record_message_sent referenciado en ATO')
    else:
        print('FAIL: record_message_sent NO encontrado en ATO')
else:
    print('FAIL: _record_quota_usage NO existe en ATO')
"

Paso 2 - Verificar quota_tracker.json:
cat data\evolution\quota_tracker.json

Paso 3 - Test funcional:
& 'C:\Users\faber\miniconda3\python.exe' -c "
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
lr = object.__new__(LocalRoleRouter)
lr.quota_tracker = type('QT', (), {'record_message_sent': lambda s,t,e: print(f'OK: recorded {t} / {e}')})()
lr.quota_tracker.record_message_sent('test_tool', 'test@email.com')
"

Reporta:
- _record_quota_usage en ATO: Si/No
- record_message_sent referenciado: Si/No
- quota_tracker.json existe y tiene datos: Si/No
```

---

## PROMPT SEGMENTO 3: WORLD MODEL WORKER POOL

```
Eres auditor de IABV v1.5. Solo verifica worker_pool_snapshot.

Ejecuta:
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

Paso 1 - Verificar campo en modelo:
& 'C:\Users\faber\miniconda3\python.exe' -c "
from iabv_v15.domain.models import WorldModelSnapshot
import inspect
sig = inspect.signature(WorldModelSnapshot)
if 'worker_pool_snapshot' in sig.parameters:
    print('PASS: worker_pool_snapshot es parametro de WorldModelSnapshot')
else:
    src = inspect.getsource(WorldModelSnapshot)
    if 'worker_pool_snapshot' in src:
        print('PASS: worker_pool_snapshot existe en WorldModelSnapshot')
    else:
        print('FAIL: worker_pool_snapshot NO existe')
"

Paso 2 - Verificar snapshot real:
& 'C:\Users\faber\miniconda3\python.exe' -c "
import json
from pathlib import Path
wm = Path('data/evolution/world_model')
latest = sorted(wm.glob('*.json'))[-1] if wm.exists() else None
if latest:
    data = json.loads(latest.read_text(encoding='utf-8'))
    pool = data.get('worker_pool_snapshot', {})
    print(f'Workers disponibles: {pool.get(\"available_count\", \"N/A\")}')
    print(f'Workers agotados: {pool.get(\"exhausted_count\", \"N/A\")}')
else:
    print('No hay snapshots de WorldModel')
"

Paso 3 - Tests focalizados:
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/ -q --tb=short -k "world_model"

Reporta:
- worker_pool_snapshot en WorldModelSnapshot: Si/No
- Datos coherentes en snapshot real: Si/No
- Tests: passed/failed
```

---

## PROMPT SEGMENTO 4: UI VISIBILITY AUDIT

```
Eres auditor de IABV v1.5. Solo verifica ui_visibility_audit.

Ejecuta:
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

Paso 1 - Verificar modulo existe:
& 'C:\Users\faber\miniconda3\python.exe' -c "
from iabv_v15.infra.ui_visibility_audit import (
    get_audit_log, VisibilityAuditLog, Win32PopupWatcher,
    SplashAuditAdapter, SubprocessAuditWrapper,
    CAT_INTENTIONAL, CAT_UNEXPECTED, CAT_BACKGROUND,
    KIND_FILE_NOT_FOUND, KIND_BG_CHECK,
)
print('PASS: todos los exports importan correctamente')
"

Paso 2 - Smoke test:
& 'C:\Users\faber\miniconda3\python.exe' -c "
import tempfile, pathlib
from iabv_v15.infra.ui_visibility_audit import (
    get_audit_log, CAT_INTENTIONAL, CAT_BACKGROUND,
    SubprocessAuditWrapper,
)
audit = get_audit_log()
tmp = pathlib.Path(tempfile.mkdtemp()) / 'test.jsonl'
audit.open(tmp)
audit.record('dialog_shown', source='test', event_category=CAT_INTENTIONAL)
audit.record_background('provider probe', source='test')
try:
    raise FileNotFoundError(2, 'test error', 'missing.exe')
except FileNotFoundError as e:
    audit.record_file_not_found(e, source='test')
s = audit.summary()
print(f'total_events: {s[\"total_events\"]}')
print(f'by_category: {s[\"by_category\"]}')
print(f'file_not_found_count: {s[\"file_not_found_count\"]}')
assert s['total_events'] >= 4, 'Expected at least 4 events'
assert s['file_not_found_count'] >= 1, 'Expected FileNotFound'
print('PASS')
"

Paso 3 - Tests focalizados:
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/test_ui_visibility_audit.py -q --tb=short

Reporta:
- Modulo importa correctamente: Si/No
- Smoke test: PASS/FAIL
- Tests: passed/failed
- Eventos se registran en categorias correctas: Si/No
```

---

## PROMPT SEGMENTO 5: BATERIA COMPLETA

```
Eres auditor de IABV v1.5. Corre la bateria completa de tests.

Ejecuta:
cd C:\Python\IABV_v1.5
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q

Baseline esperado: ~2489 passed / ~24 failed / ~23 skipped
(los fallos son pre-existentes — verificar con docs/governance/TESTS_STATE.md)

Reporta:
- Passed: ___
- Failed: ___
- Skipped: ___
- Nuevas regresiones vs baseline: Si/No (listar si hay)
```

---

## FORMATO DE REPORTE

Al terminar, deja `docs/governance/LAPTOP_AUDIT_RESULT.md` con:

```markdown
# Auditoria Real - Laptop
**Fecha:** YYYY-MM-DD
**Agente:** [Windsurf/Codex/Claude]
**Entorno:** Windows, [version], [hardware]

## Resultados

### Segmento 1 - Arranque
- Tiempo hasta ventana visible: ___ms
- Freeze observable: Si/No
- DashboardVM bg refresh: Si/No

### Segmento 2 - Quota Tracker
- _record_quota_usage en ATO: Si/No
- record_message_sent wired: Si/No
- Datos en quota_tracker.json: Si/No

### Segmento 3 - Worker Pool
- worker_pool_snapshot en WorldModelSnapshot: Si/No
- Datos coherentes: Si/No

### Segmento 4 - UI Visibility Audit
- Modulo importa: Si/No
- Smoke test: PASS/FAIL
- Categorias correctas: Si/No

### Segmento 5 - Tests
- Passed: ___
- Failed: ___
- Skipped: ___
- Nuevas regresiones: Si/No

### Observaciones
- [cualquier anomalia o hallazgo]
```

---

## PRINCIPIOS

1. No modifiques codigo
2. No inventes datos — reporta lo que observas
3. Si algo no puede verificarse, marca UNRESOLVED
4. Si encuentras regresion nueva, reportala inmediatamente
5. Deja todo trazado en el repo
