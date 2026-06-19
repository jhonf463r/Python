# IABV v1.5 - Tool Evolution Monitor

Generado: 2026-05-25T02:41:42.347763+00:00
Resumen: Superviso 5 contexto(s) con 7 propuesta(s) activa(s), 6 ya decidida(s) y 4 contexto(s) degradado(s). Mejor panorama actual: general favorece ollama con score 0.59 y propuesta collect_more_evidence Validacion autonoma: paused. La validacion autonoma se pauso porque el entorno no esta en condiciones seguras para validar.

## Rendimiento por herramienta
- general: ollama | route=local | score=0.59 | exito=100% | bloqueos=50%
- 464db78d-dc4a-4098-aecf-a5f6a2158877: ollama | route=local | score=0.66 | exito=100% | bloqueos=0%
- google:que-ves: ollama | route=local | score=0.66 | exito=100% | bloqueos=0%
- cloud_provider:groq: cloud_provider | route=cloud | score=1.09 | exito=100% | bloqueos=0%
- chatgpt_web_assisted: chatgpt web asistido | route=ui | score=-0.14 | exito=0% | bloqueos=0%

## Propuestas
- Recolectar mas evidencia para general: La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir. | accion=collect_more_runs | confianza=0.58
- Probar Playwright browser para general: Playwright browser aparece disponible y compatible con general. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.75
- Recolectar mas evidencia para 464db78d-dc4a-4098-aecf-a5f6a2158877: La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir. | accion=collect_more_runs | confianza=0.58
- Probar Claude web asistido para 464db78d-dc4a-4098-aecf-a5f6a2158877: Claude web asistido aparece disponible y compatible con 464db78d-dc4a-4098-aecf-a5f6a2158877. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.84
- Probar ChatGPT web asistido para 464db78d-dc4a-4098-aecf-a5f6a2158877: ChatGPT web asistido aparece disponible y compatible con 464db78d-dc4a-4098-aecf-a5f6a2158877. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.74
- Recolectar mas evidencia para google:que-ves: La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir. | accion=collect_more_runs | confianza=0.58