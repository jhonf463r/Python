# M1B — Lector de contexto: implementación local y puerta de pruebas

**Fecha:** 2026-10-28 (America/Bogota)  
**Tipo:** recibo de continuidad y evolución de método; este documento no integra código.

## Estado canónico y alcance

- main al iniciar esta actualización: e44403b4a4693275bb531647afc94087f28f3534.
- CURRENT-STATE.md blob previo: f919a3fc2c397d460a44aff9a8f0f498273bf7eb.
- Clon reportado por Codex: C:\_w\m1b-20261028.
- Branch local reportada: codex/m1b-context-reader; base local 9a8738565ac2d100bcd4af906081c00f3cf15384.
- Los dos archivos locales seguían sin seguimiento (??), según los recibos R1/R2/R3. El código de M1B no está publicado en GitHub ni integrado en main.
- C:\Python no se tocó. No se hicieron escrituras en GitHub durante las tareas locales R1/R2/R3.

## Secuencia de evidencia

| Fase | Resultado | Proveniencia / límites |
|---|---|---|
| R1 — primera versión | Lector y suite de pruebas creados localmente | OWNER_CODEX_REPORTED; SHA-256 lector a130fffd37bb5cc1d1a058e8dc21ae565df54419bab51a621699ea8a9c444d54; pruebas 9bdb3ebf5ec310d72fc7b2386833654c0a260021b139175c90980c08e12abcae. |
| Revisión estática 1 | P1: UNVERIFIED todavía podía producir AVAILABLE con contenido. P2: validación estructural insuficiente. | Contenido de ambos archivos compartido en chat e inspeccionado estáticamente. Pruebas no ejecutadas en esa fase. |
| R2 — corrección | Objetivo no verificado/discrepante falla cerrado; validadores estructurales ampliados. | Hashes informados por Codex: lector 14ff1835056df643fdbdd1cefaeed97b8c6b533ea081d8f489d770ad514554be; pruebas b3dfa4fb0a95bc6bd8dab653af3e413eb2176325db19bb66f400ba74610c6962. |
| Revisión estática 2 | Se detectó que algunas fechas internas sin zona horaria podían aceptarse. | Se acotó la corrección a exigir zona horaria explícita y añadir dos casos negativos. |
| R3 — puerta de pruebas | 34 passed, 0 failed, 0 skipped; exit code 0. | OWNER_CODEX_REPORTED; Python 3.13.2; pytest 9.0.3; intérprete C:\Users\faber\miniconda3\python.exe. Esta sesión no ejecutó de nuevo la suite ni leyó los bytes finales directamente del disco. |

## Comando R3 reportado

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'C:\_w\m1b-20261028\IABV_v1.5\src'
& 'C:\Users\faber\miniconda3\python.exe' -m pytest -p no:cacheprovider 'IABV_v1.5/tests/test_control_master_context_reader.py' -q
```

## Huellas finales reportadas

- Lector, 26 662 bytes: e3811a169e9d74e54dccafbef18c52ad34f78b46f8e884d3d7eb77edd123e91e.
- Pruebas, 14 966 bytes: a7459ff550db57e15479c9597e64190489d35c7ae1d0e876f43d968dc1ee53f3.

Estas huellas son informadas por Codex, no recomputadas desde esta sesión. La versión R3 completa aún no está disponible como blob o diff de GitHub; por eso no debe describirse como revisión independiente byte a byte de la versión final. La revisión cubrió el código R1/R2 proporcionado, el delta de zona horaria informado para R3 y los contratos canónicos consultados.

## Comprobación estática contra main

Se consultaron:

- IABV_v1.5/src/iabv_v15/domain/models.py.
- data/evolution/control_master/latest.json, blob d76d521e6f8d73e874a21ffe1b720dcdbcd48293.
- data/evolution/portable_context/latest.json, blob 36ea8b5da1a7b981d5c5fb6e6616ec07dcc59b9d.

En los campos inspeccionados no aparecieron incompatibilidades estructurales con los validadores R2. Los artefactos canónicos están fechados en abril de 2026: control_master.last_updated=2026-04-19T19:23:46.389095Z y portable_context.updated_at_utc=2026-04-18T16:43:21.614937Z. Con una política de frescura que limite la antigüedad a horas o días, deben rechazarse como STALE; fixtures recientes no demuestran que esos datos canónicos sean hoy frescos ni consumibles.

## Limitaciones y puertas preservadas

- Suite ejecutada: solo la suite específica del lector. Suite completa, build, CLI, runtime MCP, E2E y CI: NOT_RUN.
- Las pruebas no demuestran resistencia a todas las carreras adversariales del sistema de archivos.
- Los archivos de código continúan locales y sin seguimiento. Sus hashes o un test local aprobado no equivalen a publicación, revisión de PR ni integración en main.
- M1B no establece autoridad de propietario ni cierra G1/G2/G3.
- Estado operativo: OPTION_D=RATIFIED_NO_BOOTSTRAP; G1/G2/G3=NOT_ESTABLISHED; MCP_TOOL_ALLOWLIST=EMPTY; PROTECTED_READS=FAIL_CLOSED; TUNNEL=DISABLED; BRIDGE=BRIDGE_NOT_READY; AUTOMATIC_FOLLOW_ON=FALSE.

## Próxima frontera causal

No reimplementar el lector ni recrear el clon. Reconciliar los dos archivos locales exactos con una rama/PR de código aislada, capturar un diff revisable y verificar las huellas contra el contenido publicado. Reutilizar R3 sin repetir pruebas si los fuentes son idénticos; repetir la suite solo si cambia el contenido o una nueva revisión identifica un motivo concreto. No fusionar código hasta revisar el diff publicado. No tocar C:\Python ni abrir el puente operativo.

```text
TASK_ID=M1B_CONTEXT_READER_TIMEZONE_SHAPE_AND_TEST_GATE_20261028_R3
LOCAL_IMPLEMENTATION=OWNER_CODEX_REPORTED
TARGETED_TESTS=34_PASSED; OWNER_CODEX_REPORTED
EXACT_R3_BYTES_INDEPENDENTLY_RETRIEVED=FALSE
SOURCE_PUBLISHED_TO_GITHUB=FALSE
M1B_INTEGRATED=FALSE
BUILD/RUNTIME/E2E/CI=NOT_RUN
NEXT_ACTION=PUBLISH_EXISTING_LOCAL_CANDIDATE_TO_ISOLATED_CODE_PR; REVIEW_EXACT_DIFF
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```
