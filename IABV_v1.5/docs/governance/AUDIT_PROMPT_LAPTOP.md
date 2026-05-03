# IABV v1.5 - Prompt de Auditoria Real en Laptop

**Generado:** 2026-05-03  
**Para usar con:** Windsurf, Codex, o cualquier agente en la laptop del usuario  
**Prerequisito:** El repo debe estar en `C:\Python\IABV_v1.5` con `PYTHONPATH=src`

---

## INSTRUCCION PRINCIPAL

Eres el auditor de validacion real de IABV v1.5. Tu trabajo es ejecutar
pruebas reales en la laptop donde corre el programa y confirmar que los
cambios de las Fases 1-3 funcionan en el entorno Windows real.

**No modifiques codigo.** Solo observa, mide y reporta.

---

## CONTEXTO DE LOS CAMBIOS (ya aplicados en el repo)

### Fase 1 - ControlCenterVM lazy init
- `_initialize_heavy()` + `_bg_initial_refresh()` en `control_center_viewmodel.py`
- Heavy I/O movido a `_bg_pool.submit()` via `QTimer.singleShot(0)`
- Resultado aplicado en main thread via `taskResolved` signal

### Fase 2 - Quota tracker wiring
- `_record_quota_usage()` en `adaptive_task_orchestrator.py`
- Llama `record_message_sent(tool, email)` antes de cada despacho externo
- Solo cuando `worker_gate.top_worker` tiene email valido

### Fase 3 - worker_pool_snapshot en WorldModelSnapshot
- Campo `worker_pool_snapshot: dict` agregado a `WorldModelSnapshot` en `domain/models.py`
- `_estimate_worker_pool()` en `world_model_service.py` con timeout de 2s
- Solo se ejecuta en scans `full` (no en `light`)

---

## TAREAS DE AUDITORIA

### 1. Verificacion de arranque (Fase 1)

```powershell
# Medir tiempo de arranque de la UI
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& 'C:\Users\faber\miniconda3\python.exe' -c "
from iabv_v15.bootstrap import bootstrap_app
app = bootstrap_app()
print(f'Bootstrap completo en {$sw.ElapsedMilliseconds}ms')
"
```

Observar:
- La ventana debe aparecer **inmediatamente** (< 1s)
- El refresh de datos debe completarse en background (2-5s despues)
- No debe haber freeze visible (Responding=True siempre)
- Comparar con el baseline previo (~3733ms de bloqueo)

### 2. Verificacion de quota tracker (Fase 2)

```powershell
# Verificar que el archivo de quota existe y se actualiza
cat data\evolution\quota_tracker.json

# Hacer una consulta externa y verificar que el tracker registra
# (requiere una sesion activa con ChatGPT/Claude/Codex)
# Despues de la consulta:
cat data\evolution\quota_tracker.json
# Debe mostrar un nuevo entry con timestamp reciente
```

Observar:
- Antes de la primera consulta: archivo puede no existir o estar vacio
- Despues: debe tener una entrada con `tool`, `email`, `messages`, `total_sent`
- El `total_sent` debe incrementar con cada consulta

### 3. Verificacion de worker_pool en WorldModel (Fase 3)

```powershell
# Verificar que el WorldModel snapshot incluye worker_pool
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
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
    print(f'Mensajes restantes total: {pool.get(\"total_remaining_messages\", \"N/A\")}')
    for w in pool.get('workers', []):
        print(f'  - {w[\"tool\"]}:{w[\"email\"]} remaining={w[\"remaining_messages\"]}')
else:
    print('No hay snapshots de WorldModel')
"
```

Observar:
- `available_count` debe ser > 0 si hay sesiones activas en browsers
- `exhausted` debe listar workers sin cuota
- `total_remaining_messages` debe reflejar cuota real
- Si no hay browsers configurados, `available_count` sera 0

### 4. Tests focalizados

```powershell
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

# Tests del ControlCenterVM (Fase 1)
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/test_control_center_viewmodel.py -q --tb=short

# Tests del ATO (Fase 2)
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/ -q --tb=short -k "adaptive_task_orchestrator or orchestrator"

# Tests del WorldModel (Fase 3)
& 'C:\Users\faber\miniconda3\python.exe' -m pytest tests/ -q --tb=short -k "world_model"
```

### 5. Bateria completa

```powershell
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider tests/ -q
```

Baseline esperado: **2391 passed / 29 failed / 25 skipped**  
Los 29 fallos son pre-existentes (ver `docs/governance/TESTS_STATE.md`).

---

## FORMATO DE REPORTE

Al terminar, deja un archivo `docs/governance/LAPTOP_AUDIT_RESULT.md` con:

```markdown
# Auditoria Real - Laptop
**Fecha:** YYYY-MM-DD
**Agente:** [Windsurf/Codex/Claude]
**Entorno:** Windows, [version], [hardware]

## Resultados

### Fase 1 - Arranque
- Tiempo hasta ventana visible: ___ms
- Freeze observable: Si/No
- Tiempo de refresh completo: ___ms

### Fase 2 - Quota Tracker
- Archivo quota_tracker.json creado: Si/No
- Entries registrados despues de consulta: ___
- Datos coherentes: Si/No

### Fase 3 - Worker Pool
- worker_pool_snapshot presente: Si/No
- Workers detectados: ___
- Datos coherentes con sesiones reales: Si/No

### Tests
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
4. Si encuentras una regresion nueva, reportala inmediatamente
5. Deja todo trazado en el repo
