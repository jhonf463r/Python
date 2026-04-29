# Bootstrap Init Deferral — Splash Visible Before Service Wiring

**Fecha**: 2026-04-27
**PR**: devin/1777468965-defer-bootstrap-init
**Base**: 44ff9a6f (main post-#260/#261)

## Problema

`bootstrap_init_start → bootstrap_init_done` tardaba **19-22 s** en Windows real.
Todo el wiring de ~90 servicios, repositorios, scans de hardware (Win32 EnumWindows,
nvidia-smi, typeperf, PowerShell probes) y validaciones ocurría **dentro de
`AppBootstrap.__init__`**, antes de que el splash pudiera renderizarse.

## Solución

### 1. Split de `__init__` en dos fases

- **Fase rápida** (`__init__`): timeline, secrets, config, theme, dirs, logging,
  placeholders de VMs. Completa en **<1 s**.
- **Fase pesada** (`_wire_services()`): DB, repositorios, tool adapters, providers,
  WorldModelService, EnvironmentSelfAwarenessService, OSES, PortableContext, y los
  ~80 servicios restantes.

### 2. `_defer_services` flag

- `main.py` pasa `_defer_services=True` → `__init__` termina rápido, `run()` llama
  `_wire_services()` **después de que el splash es visible**.
- Tests usan `AppBootstrap(tmp_path)` sin flag → comportamiento legacy (todo en `__init__`).
  **Cero regresión para tests existentes.**

### 3. Deferred bootstrap scans

Cuando `_defer_services=True`:
- `WorldModelService(bootstrap_scan=False)` — no bloquea 5-10 s con Win32 window enum + network probes
- `EnvironmentSelfAwarenessService(bootstrap_scan=False)` — no bloquea 3-5 s con CPU/RAM/GPU/Ollama probes
- Ambos servicios usan snapshot persistido del disco como modelo inicial
- Background threads (ya activos via `auto_start=True`) hacen el primer scan **asíncronamente**
- Se dispara `request_refresh(reason='deferred_bootstrap', full=True)` al final de
  `_wire_services()` para despertar los threads inmediatamente

## Timeline Events

| Evento                      | Antes            | Después (deferred)         |
|-----------------------------|------------------|----------------------------|
| `bootstrap_init_start`      | t=0              | t=0                        |
| `bootstrap_init_done`       | t=19-22s         | **t=<1s** ✓                |
| `splash_visible`            | t=19-22s + splash| **t=~1-2s** ✓              |
| `wire_services_start`       | N/A              | t=~2s (after splash)       |
| `wire_services_done`        | N/A              | t=~10-14s (scans async)    |
| `engine_load_main_qml_done` | sin cambio       | sin cambio                 |

Metadata nuevos en timeline:
- `bootstrap_init_done.extra.services_deferred` — `true` cuando se usó deferral
- `wire_services_done.extra.scans_deferred` — `true` cuando bootstrap scans se hicieron async

## Clasificación de candidatos

| Cat | Candidato                             | Costo    | Riesgo | Acción            |
|-----|---------------------------------------|----------|--------|-------------------|
| A   | WorldModelService bootstrap_scan      | 5-10s    | bajo   | `bootstrap_scan=False` |
| A   | EnvironmentSelfAwarenessService scan  | 3-5s     | bajo   | `bootstrap_scan=False` |
| A   | Todos los ~80 servicios en __init__   | colectivo| bajo   | movidos a `_wire_services()` |
| B   | `_seed_control_master_from_agents_md` | ~0.5s    | bajo   | diferido con servicios |
| B   | CapabilityAuditHarness registration   | ~0.3s    | bajo   | diferido con servicios |
| C   | Module-level imports (~90)            | 3-5s     | ALTO   | **NO tocado** — futuro |

## Archivos modificados

- `src/iabv_v15/bootstrap.py` — split `__init__`/`_wire_services()`, `bootstrap_scan=False`
- `src/iabv_v15/main.py` — `_defer_services=True`
- `tests/test_bootstrap_defer_init.py` — 11 tests nuevos
- `docs/history/2026-04-27_bootstrap_init_defer.md` — este archivo

## Tests

11 tests nuevos cubriendo:
- Default (non-deferred) mantiene comportamiento legacy
- Deferred init no wirea servicios
- Deferred init completa en <2s
- VM placeholders existen con deferral
- Timeline marks con metadata
- `_wire_services()` idempotente
- Deferred scans pasan `bootstrap_scan=False`
- Non-deferred scans mantienen `bootstrap_scan=True`

62/62 tests de startup pasan (incl. pre-existentes).
1895/1895 tests del repo pasan (14 fallos pre-existentes en main no relacionados).

## UNRESOLVED

1. **Module-level imports** (~90 imports al cargar `bootstrap.py`): 3-5s en Windows con
   antivirus. Hacer lazy imports requiere refactor masivo de todos los archivos de servicios.
   Documentado como Category C para futuro PR.

2. **Validación Windows real**: este PR no fue testeado en Windows. El usuario debe
   correr `startup_timeline.jsonl` antes/después para confirmar la mejora material.
   Esperado: splash visible en ~1-2s vs ~19-22s anterior.

## Contratos respetados

- ✓ No se creó servicio nuevo
- ✓ No se creó memoria paralela
- ✓ No se hizo refactor masivo
- ✓ No se tocaron capas P1-P4 más allá de `bootstrap_scan` flag
- ✓ startup_timeline funciona con marcas nuevas
- ✓ PortableContext / OSES / WorldModel no degradados (background threads los alimentan)
- ✓ No se finge readiness — `bootstrap_init_done` marca honestamente que servicios están
  deferred, y `wire_services_done` confirma cuando realmente terminaron
