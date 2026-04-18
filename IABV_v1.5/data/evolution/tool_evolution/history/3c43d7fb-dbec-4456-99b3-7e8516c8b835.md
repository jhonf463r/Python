# IABV v1.5 - Tool Evolution Monitor

Generado: 2026-04-18T16:43:42.408928+00:00
Resumen: Superviso 6 contexto(s) con 9 propuesta(s) activa(s), 5 ya decidida(s) y 6 contexto(s) degradado(s). Mejor panorama actual: general favorece ollama con score 1.27 Validacion autonoma: idle. Sin validacion autonoma reciente.

## Rendimiento por herramienta
- general: ollama | route=language_understanding | score=1.27 | exito=100% | bloqueos=0%
- general: adaptive local orchestrator | route=language_understanding | score=0.86 | exito=100% | bloqueos=0%
- general: adaptive local orchestrator | route=ui | score=0.77 | exito=100% | bloqueos=0%
- 7622d47f-2a89-4928-852e-d1859a411d12: ollama | route=local | score=0.68 | exito=100% | bloqueos=0%
- general:sabes-por-que-no-avanza-el-trabajo-en-vivo: ollama | route=local | score=0.68 | exito=100% | bloqueos=0%
- ollama_llm: ollama local | route=background | score=-0.17 | exito=0% | bloqueos=0%
- d0d559b1-4a38-4729-a4ac-f2134a4f4a1a: ollama | route=local | score=0.73 | exito=100% | bloqueos=0%
- general:sabes-por-que-tu-trabajo-en-vivo-no-avanza-el-que-tiene-de-consulta-cojn: ollama | route=local | score=0.73 | exito=100% | bloqueos=0%

## Propuestas
- Probar Desktop human runner para general: Desktop human runner aparece disponible y compatible con general. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.77
- Recolectar mas evidencia para 7622d47f-2a89-4928-852e-d1859a411d12: La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir. | accion=collect_more_runs | confianza=0.58
- Probar Ollama local para 7622d47f-2a89-4928-852e-d1859a411d12: Ollama local aparece disponible y compatible con 7622d47f-2a89-4928-852e-d1859a411d12. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.94
- Probar ChatGPT web asistido para 7622d47f-2a89-4928-852e-d1859a411d12: ChatGPT web asistido aparece disponible y compatible con 7622d47f-2a89-4928-852e-d1859a411d12. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.89
- Recolectar mas evidencia para general:sabes-por-que-no-avanza-el-trabajo-en-vivo: La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir. | accion=collect_more_runs | confianza=0.58
- Probar Ollama local para general:sabes-por-que-no-avanza-el-trabajo-en-vivo: Ollama local aparece disponible y compatible con general:sabes-por-que-no-avanza-el-trabajo-en-vivo. Conviene validarlo frente a ollama. | accion=validate_in_sandbox | confianza=0.94