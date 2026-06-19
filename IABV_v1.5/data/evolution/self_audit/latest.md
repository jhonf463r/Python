# Auditoría operativa — IABV v1.5
- Generado: 2026-06-14T17:13:08.240551+00:00
- Razón: Auditoria post-fix tool_calling_bridge
- Tools OK: 18 / 19
## Tools con problema
- `aider_coder` [missing] — adapter reported tool as not available
## Entorno vs WorldModel
- Match OK: EnvironmentSelfModel y WorldModelSnapshot son coherentes.
## Pendientes top-5
- Congelamientos con CPU/RAM estables detectados
- high_memory_usage
- multi_source_disagreement repetido en logs
- Bootstrap init lento: 17676ms
- Error repetido 6 veces sin correccion
## Cruce de fuentes
- Laptop local observada por WorldModel: sí
- Orden: WorldModel/Environment > contratos > contexto/autoexamen > pruebas > ExperimentLab > auditoría externa