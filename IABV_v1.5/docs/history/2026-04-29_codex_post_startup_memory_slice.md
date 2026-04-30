# 2026-04-29 - Codex post-startup memory slice

## Objetivo

Reducir carga post-startup causada por rutas que deserializaban listas completas
solo para construir resúmenes en UI y métricas livianas.

## Cambios implementados

- `ToolRecordRepository`
  - nuevos helpers SQL/livianos:
    - `latest_result()`
    - `count_results()`
    - `count_interaction_patterns()`
    - `count_interaction_observations()`
    - `count_interaction_episodes()`
- `ControlCenterViewModel`
  - `_update_evolution_snapshot()` ya no carga listas completas de
    patterns/observations/episodes/results solo para contar o tomar el último.
  - se eliminan lecturas redundantes de `ExperimentLab` que quedaban pisadas por
    el historial scoped.
  - se agrega semilla honesta del panel evolutivo para que, con
    `defer_initial_refresh=True`, la UI no nazca vacía.
- `DashboardViewModel`
  - usa `repo.count()` en lugar de `list_recent(...)+len(...)` para resúmenes.
- `LocalRoleRouter`
  - usa conteos SQL donde solo necesitaba cardinalidad para resúmenes y refresh
    metadata.

## Pruebas corridas

- `tests/test_tool_record_repository.py`
- `tests/test_post_startup_perf.py`
- `tests/test_local_role_router.py`
- `tests/test_control_center_viewmodel.py -k "evolution or snapshot"`

Resultado:

- `31 passed`
- `9 passed, 84 deselected`

## Evidencia live Windows

El startup visible mejoró previamente, pero la memoria post-startup sigue
inestable y es el cuello real actual.

Muestra live observada:

- ~30s: `2565.4 MB WS / 2580.7 MB PM`
- ~60s: `618.0 MB WS / 642.9 MB PM`
- ~120s: `8150.9 MB WS / 8470.0 MB PM`

Lectura:

- el problema ya no es solo resumen/UI;
- hay presión fuerte y no determinista en servicios vivos después del arranque.

## Conclusión

Este slice reduce deserialización innecesaria y limpia una regresión de UI
deferida, pero NO cierra la deuda principal de RAM.

## Siguiente paso recomendado

Atacar lazy loading real en `AppBootstrap` y wiring pesado de servicios no
críticos, siguiendo lo que ya marca OSES:

- `EmbeddingIndexService`
- `SiteExplorationService`
- `BrowserSessionController`
- y servicios similares que no deberían instanciarse al encender la UI

## UNRESOLVED

- memoria post-startup sigue crítica e inestable en Windows live
- `portable_context/latest.*` y `self_examination/latest.*` siguen siendo
  snapshots de runtime; no son un fix de código por sí mismos
- todavía falta ingesta automática de auditorías live hacia
  `CodeAuditTrail` / `ExperimentLab`
