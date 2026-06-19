# Universal Metacognition Scientific Grounding - 2026-05-23

## Contexto

El usuario pidio que IABV no solo guarde notas, sino que pueda explicar y mejorar
su propio razonamiento: lenguaje, conceptos, vision, pesos, entorno, acciones y
resultado. La interaccion viva `user_operational_note_54f7bb61d491` demostro que
IABV ya captura la observacion, pero la primera clasificacion fue demasiado
generica. Se refino como `metacognitive_reasoning_gap_54f7bb61d491` y se abre
P0.55 para convertir esto en una capa medible.

## Tesis operativa

IABV no necesita otro cerebro. Necesita un contrato comun de evidencia conceptual
que conecte los organos existentes:

- `IntentUnderstandingService`: que quiso decir el usuario.
- `TaskContextAssembler`: que contexto activo modifica esa intencion.
- `UniversalPerceptionService`: que se ve/lee realmente en pantalla, DOM, CDP,
  OCR o accesibilidad.
- `WorldModelService`: que ventanas, procesos y foco existen.
- `RuntimeAuditTracer`: que paso en tiempo real.
- `OSES`: que patrones se repiten y que ajustes recomienda.
- `PortableContextService`: que se lleva a la siguiente sesion.
- `ExperimentLab` + `AdaptiveWeightLayer`: que ruta funciono mejor y con que
  confianza.

## Base cientifica aplicable

1. ReAct: razonamiento y accion se alternan con observaciones del entorno.
   En IABV esto se traduce a `OBSERVE -> FUSE -> INFER -> ACT -> VERIFY`.
   Fuente: https://arxiv.org/abs/2210.03629

2. Reflexion: el feedback verbal y los resultados se guardan como memoria para
   mejorar decisiones futuras. En IABV, el feedback del usuario debe terminar en
   `platform_pending`, `DecisionAuditTrail`, `OSES` y `PortableContext`, no solo
   en chat local. Fuente: https://arxiv.org/abs/2303.11366

3. SeeAct: los agentes web generalistas necesitan grounding con HTML/DOM y
   vision; screenshot solo o DOM solo no es suficiente. En IABV, ChatGPT debe
   validarse con DOM/CDP + target binding + prueba de envio/respuesta.
   Fuente: https://arxiv.org/abs/2401.01614

4. OSWorld: los agentes deben evaluarse en entornos reales de computador, no solo
   benchmarks cerrados. En IABV, cada dispositivo necesita capability calibration
   y pruebas vivas. Fuente: https://arxiv.org/abs/2404.07972

5. Calibration / ECE: la confianza del sistema debe compararse contra acierto
   real. En IABV, `response_verified`, `target_binding_confidence` y
   `intent_confidence` deben calibrarse contra outcomes reales.
   Fuente: https://proceedings.mlr.press/v70/guo17a.html

6. Active inference: actuar debe reducir incertidumbre. En IABV, si falta
   evidencia, la accion correcta no es responder con seguridad, sino pedir la
   observacion minima o enfocar la ventana correcta.
   Fuente: https://arxiv.org/abs/2207.06415

## Contrato propuesto: ConceptWeightEvidence

Campos minimos:

- `user_text`: texto normalizado y original truncado.
- `active_context`: incidente activo, herramienta externa, ventana esperada.
- `concepts_detected`: lista de conceptos con peso y evidencia.
- `sources_used`: chat, runtime_audit, world_model, DOM, CDP, OCR, accesibilidad,
  visual_target_binding.
- `missing_sources`: fuentes no disponibles.
- `contradictions`: hechos que contradicen la hipotesis.
- `chosen_action`: responder local, pedir ayuda humana, capturar, consultar,
  reintentar, registrar tarea.
- `confidence`: confianza calibrable.
- `verification`: resultado real, correccion del usuario, exito/fallo.

## Metricas

- `false_local_rate`: solicitudes que debian ir a externo/visual pero cayeron a
  local.
- `wrong_target_rate`: capturas de IABV/Codex/escritorio cuando el objetivo era
  ChatGPT u otra ventana.
- `unverified_success_rate`: respuestas marcadas como resueltas sin prueba de
  envio y respuesta nueva.
- `concept_calibration_error`: diferencia entre confianza de concepto y outcome.
- `user_repair_rounds`: cuantas correcciones humanas se necesitaron.
- `time_to_shared_reality`: tiempo hasta que usuario y programa hablan de la
  misma ventana/evidencia.

## Pendientes

- P0.55A implementado el 2026-05-23: `UniversalPerceptionService` produce
  `metavision_frame`, una metaestructura visual con conceptos ponderados,
  fuentes usadas, elementos UI, relaciones, acciones disponibles,
  `next_action` y `unresolved_fields`. `ControlCenterViewModel` lo traza en
  `visual_concept_read_result`; OSES detecta degradacion de metavision; y
  `PortableContextService` exporta un resumen compacto.
- P0.55 restante: extender la misma idea a lenguaje/intencion con un contrato
  `ConceptWeightEvidence` consumido por IntentUnderstandingService y
  TaskContextAssembler, manteniendo OSES/PortableContext como memoria y
  auditoria.
- P0.56: prueba viva de calibracion de metavision en Windows con ChatGPT real:
  confirmar ventana objetivo, concepto de verificacion/login/input/respuesta,
  fuentes disponibles y accion humana minima.
- P0.46/P0.51/P0.54: continuar fusion visual, target binding y permisos de
  observacion.
- P0.53: mover la metrica de alineacion comunicativa hacia capas de intent/context,
  no dejarla encerrada solo en el ViewModel.
- Probar en Windows con ChatGPT real: prompt enviado, respuesta nueva capturada,
  y `response_verified=true` solo cuando haya prueba causal.
