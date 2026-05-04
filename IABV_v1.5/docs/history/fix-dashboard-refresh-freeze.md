# Fix: Dashboard Refresh Freeze

## Diagnostico

**Problema observado**: despues de `shell_loader_ready` (8689ms),
`page_loader_ready` nunca llega en 35s. El proceso queda alive pero
`Responding=False`, RSS ~2061MB.

**Causa raiz**: `DashboardViewModel.__init__` programa
`QTimer.singleShot(250, self.refresh)`. El metodo `refresh()` corre
**en el GUI thread** y ejecuta I/O real pesado contra SQLite:

| Query | Tiempo medido |
|---|---|
| `episodes.list_recent(100)` | 1.7ms |
| `knowledge.list_recent(100)` | 21305ms |
| `runs.list_recent(100)` | 17137ms |
| `embedding.describe_index()` | 344ms |
| **Total** | **~39068ms** |

Esos ~39s de I/O bloqueante en main thread impiden que el Qt event loop
procese el `Loader.onStatusChanged` de QML, congelando la UI y
evitando que `page_loader_ready` se emita.

## Solucion aplicada

Patron equivalente al de `ControlCenterViewModel`:

1. `ThreadPoolExecutor(max_workers=1, thread_name_prefix='dvm-bg')`
2. `_deferred_initial_refresh()` submite `_refresh_data_bg()` al pool
3. `_refresh_data_bg()` ejecuta I/O pesado fuera del GUI thread
4. Resultados vuelven via `refreshResolved` Signal → `_apply_refresh` Slot
5. `refresh()` (boton manual) tambien delega al pool
6. `_collect_summary_cards()` factoriza la logica de queries

## Instrumentacion

Tres marcas en el startup timeline:
- `dashboard_vm_refresh_start`
- `dashboard_vm_refresh_done`
- `dashboard_vm_refresh_failed`

OSES lee estas marcas en `_startup_health_findings()` y emite:
- `startup_degradation` si refresh > 5000ms
- `startup_degradation` si refresh fallo

## Archivos modificados

- `src/iabv_v15/ui/viewmodels/dashboard_viewmodel.py`
- `src/iabv_v15/services/evolution/operational_self_examination_service.py`
- `tests/test_dashboard_refresh_freeze.py` (nuevo)
- `docs/history/fix-dashboard-refresh-freeze.md` (este archivo)

## UNRESOLVED

- Las queries subyacentes (`knowledge.list_recent`, `runs.list_recent`)
  siguen siendo lentas (~21s y ~17s). Este fix mueve el bloqueo fuera
  del GUI thread pero no optimiza las queries. Requiere investigacion
  separada en los repositorios SQLite.
- No se verifico el fix con PySide6 real (CI no tiene Qt). Los tests
  usan el shim de fallback que simula signals como callbacks sincronos.
