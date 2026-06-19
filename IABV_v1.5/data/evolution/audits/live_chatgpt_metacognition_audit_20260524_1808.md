# Live ChatGPT Metacognition Audit - 2026-05-24 18:08 UTC

## Scope

Auditoria viva ejecutada como usuario desde el chat de IABV:

- `auditoria viva: dime si entiendes mi objetivo universal...`
- `haz una consulta en chatgpt: responde solo S si entiendes`

Runtime auditado: `C:\Python\IABV_v1.5_runtime_ready\IABV_v1.5`.

## Result

### Metacognition question

Estado: `PASS`

IABV respondio por `universal_metacognition`, no por nota operacional ni charla local generica. La respuesta uso OSES, WorldModel, EnvironmentSelfModel, ValidationCycle y platform_pending.

### ChatGPT consultation

Estado: `PARTIAL`

IABV:

- detecto intencion explicita de ChatGPT,
- no cayo a local,
- abrio/solicito superficie visible de ChatGPT,
- capturo la ventana correcta `ChatGPT - Google Chrome`,
- dejo `working=false` y `live_status=idle`,
- no declaro exito sin respuesta capturada.

Evidencia visual:

- `data/evolution/visual_evidence/visual_20260524_180811_537093_chatgpt.png`
- `target_window_found=true`
- `target_window_title=ChatGPT - Google Chrome`
- `capture_quality.useful=true`

## Remaining Gap

La consulta aun no queda completa porque IABV no envio el prompt ni capturo respuesta verificable. La captura muestra ChatGPT abierto con input listo, pero sin texto enviado.

Campos no resueltos observados:

- `UNRESOLVED:ocr_not_enabled_on_ui_path`
- `UNRESOLVED:visual_semantic_reader_unavailable`

Interpretacion: el organo de target binding ya encontro la ventana correcta; el organo que falta cerrar es lectura/accion semantica gobernada sobre la superficie web visible: DOM/CDP/OCR/accesibilidad o un runner de UI que pegue, envie y luego capture respuesta con prueba.

## Changes Applied In This Slice

- Se amplio el detector de preguntas de metacognicion universal para reconocer auditoria viva, evidencia, organo que falla, accion concreta y rechazo de respuesta local generica.
- Cuando la ruta externa puede crear superficie (`chatgpt_web_assisted`) y el target visual falta, IABV ahora abre/solicita la ventana visible en vez de bloquear por target missing.
- Al abrir superficie externa se extiende el timeout visible a 180s para evitar cerrar antes de que llegue la captura.
- Si la automatizacion falla despues de abrir la superficie, el flujo queda como `awaiting_external_response`, no como fallback local.

## Next Correct Slice

P0.45 - Governed Web Surface Actuation + Semantic Response Proof

Objetivo:

1. Usar el target binding ya resuelto (`ChatGPT - Google Chrome`).
2. Verificar input listo con DOM/CDP/OCR/accesibilidad si existe.
3. Si el usuario pidio explicitamente consulta externa, pegar prompt y enviar con una accion gobernada.
4. Capturar respuesta con prueba causal: prompt enviado despues de timestamp T, respuesta nueva despues de T.
5. Si no puede leer semanticamente, pedir una accion humana concreta y mostrar exactamente que ventana ve.

No crear otro cerebro. Extender `UIExecutionRunner`, `ToolAdapter`, `UniversalPerceptionService`, OSES y PortableContext.

## Follow-up Fix - Presence And Session Hygiene

Estado: `APPLIED`

Hallazgo nuevo del run vivo: IABV podia abrir o solicitar otra superficie de ChatGPT aunque acabara de abrir una. La causa era doble:

- `_external_visual_target_missing()` trataba `status=unavailable` como `target_missing` aunque `target_binding_status=bound`.
- `_request_external_target_surface_for_missing_target()` leia `_external_visible_verification_opened_at`, pero no lo actualizaba cuando abria la superficie.

Cambios aplicados:

- Nuevo contrato interno `_external_visual_target_bound()`: una ventana vinculada de ChatGPT cuenta como presencia real aunque falte OCR/DOM/CDP.
- `_external_visual_target_missing()` ya no marca como faltante una ventana `bound`.
- `_execute_external_consultation_sync()` registra `external_target_bound_reused` y mantiene el handoff externo vivo sin abrir otra ventana cuando ya hay target vinculado.
- `_request_external_target_surface_for_missing_target()` ahora recuerda la apertura y aplica cooldown de 10 minutos para evitar llenar Chrome con ventanas/tabs repetidas.

Pruebas:

- `tests/test_control_center_freeze_fix.py::test_external_surface_request_remembers_recent_open_to_avoid_duplicate_tabs`
- `tests/test_control_center_freeze_fix.py::test_bound_chatgpt_window_reused_without_opening_duplicate_surface`
- `tests/test_control_center_freeze_fix.py::test_external_route_without_launch_surface_blocks_missing_target`
- Regresion: `tests/test_control_center_freeze_fix.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado: `112 passed`.

## Follow-up Fix - Governed Visible Surface Actuation

Estado: `APPLIED`

Hallazgo: cuando DOM/CDP/headless no completaba la consulta, IABV ya podia tener una ventana correcta vinculada (`ChatGPT - Google Chrome`) pero solo dejaba handoff manual. Eso preservaba la verdad, pero no avanzaba hacia la tarea simple de enviar la consulta.

Cambios aplicados:

- `UIExecutionRunner.submit_prompt_to_existing_window()` pega y envia un prompt en una ventana visible ya enfocada por titulo/WorldModel.
- El metodo prueba solo actuacion (`prompt_pasted`, `submit_invoked`), no respuesta. `response_captured` permanece `false`.
- `_execute_external_consultation_sync()` intenta este fallback solo cuando existe superficie visible disponible y la ruta primaria fallo sin haber pegado/enviado.
- Si el envio visible se invoca, el estado queda `awaiting_response`, `handoff_reason=visible_surface_prompt_submitted_response_unverified`, `needs_human_send=false`, `response_capture_pending=true`.
- El mensaje al usuario cambia a "Intenté pegar y enviar..." y sigue sin declarar exito hasta tener respuesta capturada.

Pruebas:

- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_pastes_and_submits_visible_surface`
- `tests/test_control_center_freeze_fix.py::test_visible_bound_surface_attempts_prompt_submission_without_declaring_response`
- Regresion: `tests/test_control_center_freeze_fix.py tests/test_ui_execution_runner.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado: `132 passed`.

UNRESOLVED:

- La prueba viva por `UIBridgeClient.send_message()` quedo `buffered` y no genero un `interaction_open` nuevo en `runtime_audit.jsonl`. Requiere interaccion directa en la UI o revisar el drenaje del buffer del bridge si se quiere usar como prueba automatica.
- Sigue faltando prueba viva de respuesta capturada despues de envio visible. El contrato actual evita mentir: enviar no equivale a capturar respuesta.

## Follow-up Fix - Background Attempt Explanation

Estado: `APPLIED`

Hallazgo del run vivo `chat-bd5a548cfe87`: IABV entendio la consulta externa y uso `chatgpt_web_assisted`, pero el resultado quedo en `browser_dom_pre_submit_response_unverified`. Eso significa que la ruta de navegador/DOM de segundo plano encontro una respuesta o interfaz no atribuible causalmente al prompt actual. El programa no lo explicaba bien: mostraba un handoff generico como si no hubiese intentado nada en segundo plano.

Cambios aplicados:

- `_execute_external_consultation_sync()` ahora distingue `background_prompt_pasted` y `background_submit_invoked`.
- Si el envio ya fue invocado en segundo plano, IABV no reenvia en la ventana visible para evitar duplicados.
- El handoff pasa a `background_prompt_submitted_response_unverified` y `needs_human_send=false`.
- La respuesta al usuario debe decir: “Intenté hacer la consulta en segundo plano..., pero no pude probar que la respuesta visible sea posterior a este prompt”.
- `_answer_external_consultation_diagnosis_question()` ahora incluye `prompt_pasted`, `submit_invoked`, `failure_detail` y traduce ese estado en lenguaje causal.

Pruebas:

- `tests/test_control_center_freeze_fix.py::test_background_prompt_submission_is_reported_without_reasking_human_send`
- `tests/test_control_center_freeze_fix.py::test_visible_bound_surface_attempts_prompt_submission_without_declaring_response`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_pastes_and_submits_visible_surface`
- Regresion: `tests/test_control_center_freeze_fix.py tests/test_ui_execution_runner.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado: `133 passed`.

UNRESOLVED:

- Falta prueba viva posterior a este ajuste con una consulta nueva desde la UI.
- Sigue sin haber OCR/CDP/accesibilidad activos para leer semanticamente la ventana visible; la evidencia pixel/WorldModel si vincula la ventana.

## Follow-up Fix - Short Response Capture And Visible Response Proof

Estado: `APPLIED`

Hallazgo del run vivo posterior: ChatGPT podia producir una respuesta minima
como `S`, pero IABV la trataba como no util porque el lector exigia texto
largo. Ademas, la ruta visible pegaba/enviaba el prompt pero no intentaba leer
una respuesta nueva desde la misma ventana.

Causa raiz:

- `_captured_text_looks_useful()` descartaba cualquier texto menor a 24
  caracteres, incluso cuando el prompt pidio explicitamente `responde solo S`.
- La lectura DOM no diferenciaba de forma suficiente entre una respuesta vieja y
  una respuesta nueva si el texto era corto.
- La ruta visible gobernada no hacia lectura posterior; por eso el estado
  quedaba en `response_capture_pending` aunque la pagina ya mostrara una
  respuesta.

Cambios aplicados:

- `UIExecutionRunner` ahora extrae respuestas cortas esperadas desde el prompt
  (`responde solo S`, `answer only OK`, etc.).
- Una respuesta corta solo se acepta si hay prueba de frescura:
  - DOM: aparece un nuevo elemento de respuesta respecto al baseline.
  - Reingesta: se lee una sesion existente asociada al intento actual.
  - Ventana visible: el texto copiado contiene una linea nueva no presente en
    el baseline y no es eco del prompt.
- `_capture_browser_dom_response()` guarda `baseline_response_count` y no
  confunde respuestas antiguas con la consulta nueva.
- `submit_prompt_to_existing_window()` puede esperar una respuesta y leerla por
  delta de portapapeles cuando no hay CDP/OCR/accesibilidad.
- `_execute_external_consultation_sync()` cierra la consulta como
  `response_captured` cuando la ruta visible demuestra una respuesta nueva.

Pruebas:

- `tests/test_ui_execution_runner.py::test_ui_execution_runner_accepts_expected_short_fresh_response`
- `tests/test_ui_execution_runner.py::test_ui_execution_runner_browser_dom_captures_one_letter_expected_answer`
- `tests/test_ui_execution_runner.py::test_ui_execution_runner_browser_dom_reingest_accepts_expected_short_answer`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_captures_expected_short_visible_response`
- `tests/test_control_center_freeze_fix.py::test_visible_bound_surface_captured_response_resolves_external_consultation`
- Regresion: `tests/test_ui_execution_runner.py tests/test_control_center_freeze_fix.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado: `138 passed`.

Runtime:

- Cambios sincronizados a `C:\Python\IABV_v1.5_runtime_ready\IABV_v1.5`.
- Cambios sincronizados a `C:\Python\IABV_v1.5_runtime_main\IABV_v1.5`.
- IABV reiniciado desde el acceso `runtime_ready`.

Siguiente prueba viva:

1. Abrir IABV desde el acceso directo.
2. Enviar: `haz una consulta a ChatGPT: responde solo S si entiendes`.
3. Resultado esperado aceptable:
   - `S` capturado desde DOM/background, o
   - `S` capturado desde la ventana visible, o
   - handoff especifico indicando que la ventana se ve pero no hay lector
     semantico suficiente.
4. Resultado invalido:
   - respuesta local generica,
   - `procesando` indefinido,
   - declarar exito sin `response_captured=true`.

UNRESOLVED:

- `live_chatgpt_short_response_capture_proof`: falta la prueba viva posterior a
  este ajuste desde la UI real.

## Follow-up Fix - Visible Input Focus Proof

Estado: `APPLIED`

Hallazgo del run vivo `2026-05-24T20:27`: la captura mas reciente mostro
`ChatGPT - Google Chrome` enfocado, pero el cuadro de entrada seguia vacio.
Sin embargo, el runtime habia registrado:

- `prompt_pasted=true`
- `submit_invoked=true`
- `response_captured=false`

Eso era una contradiccion metacognitiva: el sistema decia "pegue" porque habia
enviado Ctrl+V, no porque comprobo que el texto entro al campo de ChatGPT.

Causa raiz:

- El click visible apuntaba a `90%` de la altura de la ventana. En una pagina
  nueva de ChatGPT el composer puede estar centrado, no abajo.
- `prompt_pasted` no tenia prueba de foco real del input.
- La ruta visible no diferenciaba entre "mande teclas al sistema operativo" y
  "el campo semantico recibio el prompt".

Cambios aplicados:

- `submit_prompt_to_existing_window()` ahora prueba varios puntos candidatos
  del composer:
  - `center_new_chat`
  - `lower_composer`
  - `bottom_thread_composer`
- Despues de pegar, copia el foco activo y verifica que el texto copiado
  contenga el prompt. Solo entonces marca:
  - `input_focus_verified=true`
  - `prompt_pasted=true`
  - `submit_invoked=true`
- Si no puede verificar el foco del input, retorna
  `visible_input_focus_unverified` y no declara envio.
- El trace `visible_external_prompt_submission_result` ahora incluye
  `input_focus_verified`.

Pruebas:

- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_pastes_and_submits_visible_surface`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_captures_expected_short_visible_response`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_tries_center_then_lower_input`
- `tests/test_control_center_freeze_fix.py::test_visible_bound_surface_captured_response_resolves_external_consultation`
- Regresion: `tests/test_ui_execution_runner.py tests/test_control_center_freeze_fix.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado:

- Focalizadas: `4 passed`.
- Regresion: `139 passed`.
- Runtime ready smoke: `3 passed`.

Runtime:

- Cambios sincronizados a `C:\Python\IABV_v1.5_runtime_ready\IABV_v1.5`.
- Cambios sincronizados a `C:\Python\IABV_v1.5_runtime_main\IABV_v1.5`.
- IABV reiniciado desde `runtime_ready`.

Siguiente prueba viva:

Enviar otra vez desde la UI:

`haz una consulta a ChatGPT: responde solo S si entiendes`

Criterio de exito:

- `input_focus_verified=true`
- `prompt_pasted=true`
- `submit_invoked=true`
- `response_captured=true` si DOM o delta visible lee `S`

Criterio de fallo util:

- `visible_input_focus_unverified`: significa que IABV enfoco la ventana, pero
  no logro colocar el cursor en el campo correcto. En ese caso el siguiente
  ajuste debe ir a un selector semantico real: CDP, accesibilidad u OCR.

## Follow-up Fix - Background Freshness And Real Foreground Verification

Estado: `APPLIED`

Hallazgo adicional durante la auditoria viva:

- La prueba directa mostro `input_focus_verified=true`, pero
  `response_captured=false`.
- Al capturar la pantalla despues, IABV estaba encima del escritorio y el
  browser visible ya no estaba en una pestana ChatGPT sino en YouTube. Eso
  demostro dos problemas separados:
  - Windows puede negar `SetForegroundWindow` aunque el codigo crea que enfoco
    la ventana.
  - Una ventana Chrome no equivale a una pestana ChatGPT activa.

Causa raiz de segundo plano:

- El runner DOM ya podia saber si aparecio un nuevo elemento de respuesta
  (`final_response_count > baseline_response_count`), pero ese dato no llegaba
  al adaptador.
- `ToolAdapter._browser_capture_is_pre_submit_response()` invalidaba respuestas
  frescas cuando el input seguia disponible en la pagina, degradandolas a
  `browser_dom_pre_submit_response_unverified`.

Cambios aplicados:

- `_capture_browser_dom_response()` ahora exporta:
  - `baseline_response_count`
  - `final_response_count`
  - `fresh_response_observed`
- `ToolAdapter._semantic_capture_metadata()` conserva esos campos.
- `_browser_capture_is_pre_submit_response()` ya no invalida una respuesta si
  `fresh_response_observed=true` y `submit_invoked=true`.
- `_focus_window()` ahora usa `_force_foreground_window()` con verificacion de
  `GetForegroundWindow()` y fallback `AttachThreadInput` para no asumir foco
  falso.

Pruebas:

- `tests/test_tool_adapters.py::test_external_assistant_adapter_accepts_fresh_browser_response_even_if_input_still_available`
- `tests/test_tool_adapters.py::test_external_assistant_adapter_rejects_pre_submit_browser_response`
- `tests/test_ui_execution_runner.py::test_ui_execution_runner_browser_dom_captures_one_letter_expected_answer`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_tries_center_then_lower_input`
- Regresion: `tests/test_ui_execution_runner.py tests/test_tool_adapters.py tests/test_control_center_freeze_fix.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado:

- Focalizadas: `4 passed`.
- Regresion: `160 passed`.
- Runtime ready smoke: `2 passed`.

Nuevo criterio metacognitivo:

- `prompt_pasted=true` ya no basta.
- `submit_invoked=true` ya no basta.
- Exito externo requiere al menos una de estas pruebas:
  - DOM con `fresh_response_observed=true`.
  - Ventana visible con `input_focus_verified=true` y delta de texto nuevo.
  - Handoff especifico indicando pestana/ventana objetivo no disponible.

UNRESOLVED:

- Si Chrome esta abierto en otra pestana (por ejemplo YouTube), sin CDP no hay
  forma confiable de seleccionar la pestana ChatGPT existente. IABV debe abrir
  o pedir enfocar ChatGPT, no actuar sobre una ventana Chrome cualquiera.

## Follow-up Fix - User Activity And Self-Occlusion Contract

Estado: `APPLIED`

Hallazgo del run vivo `chat-02a9a0cc956f`:

- El usuario estaba usando el portatil.
- IABV intento abrir/preparar ChatGPT.
- El target binding selecciono una ventana Chrome con titulo
  `Te damos la bienvenida de nuevo - OpenAI - Google Chrome`.
- `target_focus_result.reason=set_foreground_failed`.
- La captura guardada muestra principalmente la propia ventana de IABV encima
  de Chrome.

Interpretacion:

El programa no fallo solo por ChatGPT. Fallo porque confundio tres estados:

1. La ventana objetivo existe.
2. La ventana objetivo esta en foreground real.
3. La captura representa realmente esa ventana.

Solo el punto 1 era cierto. Los puntos 2 y 3 eran falsos.

Causa raiz:

- `target_window_found=true` se derivaba de WorldModel/Win32, no de
  visibilidad no ocluida.
- La captura por `bbox` puede incluir otra ventana encima si IABV cubre el
  area. Eso genero evidencia visual contaminada.
- El algoritmo no trataba la actividad del usuario como una razon para no
  pelear por foreground.

Cambios aplicados:

- Nuevo contrato interno de oclusion visual:
  - detecta si ventanas self (`IABV`, `Codex`) se solapan con el target.
  - combina overlap con fallo de foreground (`set_foreground_failed`).
  - si el target esta ocluido por IABV, bloquea la captura.
- `_capture_visual_evidence_snapshot()` ahora produce:
  - `capture_scope=target_occluded_by_self_no_capture`
  - `status=target_occluded`
  - `UNRESOLVED:external_target_occluded_by_iabv`
  - `UNRESOLVED:visual_target_foreground_not_verified`
- Se agrega trace:
  - `visual_target_occlusion_detected`

Pruebas:

- `tests/test_control_center_freeze_fix.py::test_visual_evidence_blocks_capture_when_iabv_occludes_target`
- `tests/test_control_center_freeze_fix.py::test_visual_evidence_capture_with_permission_prefers_visible_bbox`
- `tests/test_tool_adapters.py::test_external_assistant_adapter_accepts_fresh_browser_response_even_if_input_still_available`
- `tests/test_ui_execution_runner.py::test_submit_prompt_to_existing_window_tries_center_then_lower_input`
- Regresion: `tests/test_control_center_freeze_fix.py tests/test_ui_execution_runner.py tests/test_tool_adapters.py tests/test_runtime_p044_visual_concept_resolver.py`

Resultado:

- Focalizadas: `4 passed`.
- Regresion: `161 passed`.
- Runtime ready smoke: `2 passed`.

Nuevo criterio:

IABV no debe considerar valida una captura externa si:

- el target existe pero `SetForegroundWindow` fallo,
- una ventana self se solapa con el target,
- la captura no puede probar que ve la superficie externa no ocluida.

En ese caso debe pasar a segundo plano real, pedir CDP/OCR/accesibilidad, o
pedir una accion humana concreta. No debe guardar una captura contaminada como
si fuera ChatGPT.

## Follow-up Fix - Login Title And Runtime-Ready Validation

Estado: `APPLIED`

Hallazgo complementario:

- La ventana objetivo detectada tenia titulo
  `Te damos la bienvenida de nuevo - OpenAI - Google Chrome`.
- Sin OCR/DOM/CDP/accesibilidad, la unica pista semantica confiable era el
  titulo de la ventana.
- Antes del ajuste, la metavision marcaba `login_detected=false` aunque el
  titulo de OpenAI indicaba una superficie de bienvenida/login.

Cambio aplicado:

- `UniversalPerceptionService` ahora incorpora `target_window_title` al texto
  combinado de etiquetas semanticas.
- La deteccion universal de login reconoce patrones de titulo como:
  - `welcome back`
  - `te damos la bienvenida`
- Esto permite producir `login_screen_candidate` aunque OCR no este disponible.

Pruebas finales:

- `tests/test_runtime_p044_visual_concept_resolver.py::test_visual_concepts_infer_login_from_target_window_title`
- `tests/test_control_center_freeze_fix.py::test_visual_evidence_blocks_capture_when_iabv_occludes_target`
- `tests/test_tool_adapters.py::test_external_assistant_adapter_accepts_fresh_browser_response_even_if_input_still_available`
- Regresion relevante:
  `tests/test_runtime_p044_visual_concept_resolver.py tests/test_control_center_freeze_fix.py tests/test_ui_execution_runner.py tests/test_tool_adapters.py`

Resultado:

- Runtime ready smoke: `3 passed`.
- Regresion relevante: `162 passed`.

Interpretacion final del incidente:

El usuario si influyo en el resultado porque estaba usando el portatil y la
ventana de IABV quedo encima del objetivo externo. El programa debe trabajar en
segundo plano cuando tenga CDP/DOM disponible; si solo tiene vision por
captura, debe demostrar que la superficie externa esta realmente visible y no
ocluida antes de razonar. Este contrato queda como regla general para cualquier
pagina, dispositivo o sistema operativo: primero resolver objetivo y
visibilidad no ocluida; despues interpretar; despues actuar.
