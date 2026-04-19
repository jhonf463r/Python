# Test plan — `chatgpt_web_assisted` flow real

## Contexto
- Feature bajo test: `UIExecutionRunner._capture_browser_dom_response`
  (<ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/src/iabv_v15/services/tools/ui_execution_runner.py" /> líneas 684-830).
- ToolCard: `chatgpt_web_assisted` (<ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/tool_teaching/cards/chatgpt_web_assisted.json" />).
- launch_target: `https://chatgpt.com/`.
- input_selectors: `textarea`, `div[contenteditable="true"]`.
- response_selectors: `[data-message-author-role="assistant"]`, `main article`.
- submit_selectors: `button[data-testid="send-button"]`.
- Bug target del PR #21: en `reingest_only=True` la rama clipboard no debe
  re-pegar prompt. (Equivalente browser_dom ya existía antes; aquí validamos
  que el flujo completo sigue coherente sobre un hilo real).

## Pre-condiciones
- Chrome visible corriendo en la VM con CDP en `http://localhost:29229`.
- `user-data-dir=/home/ubuntu/.browser_data_dir` (profile persistido).
- Secrets `CHATGPT_WEB_EMAIL` y `CHATGPT_WEB_PASSWORD` disponibles en env.
- Cuenta descartable provista por el usuario. Si tiene 2FA, pedir
  `_2FA_CHATGPT_WEB` antes de continuar.

## Estrategia de acceso
Cloudflare bloquea Playwright headless puro con "Just a moment..." — por
eso NO uso headless nuevo. En cambio:
1. Atacar el Chrome visible ya corriendo en la VM, con Playwright
   `connect_over_cdp("http://localhost:29229")` o directamente computer use.
2. Loguearme UNA VEZ en chatgpt.com a través de ese browser.
3. Una vez autenticado, ejercitar `_capture_browser_dom_response`
   apuntando al mismo `user_data_dir=/home/ubuntu/.browser_data_dir` con
   `headless=False` — el profile ya tiene cookies de sesión válidas.
   Importante: cerrar el Chrome visible primero para no chocar con el
   `launch_persistent_context` de Playwright (misma carpeta de profile).

## Test assertions

### Setup 0 — Login real
- **setup**: abrir chatgpt.com en Chrome visible. Si no hay sesión, pegar
  `CHATGPT_WEB_EMAIL` y `CHATGPT_WEB_PASSWORD`.
- **Precondición**: `https://chatgpt.com/` con textarea visible.

### Test 1 — It should paste prompt + capture assistant response end-to-end
- **test_start**: `It should paste prompt in textarea and capture assistant DOM response`
- **acción**:
  - invocar `UIExecutionRunner._capture_browser_dom_response` con:
    - launch_target `https://chatgpt.com/`
    - prompt_text `"Responde exactamente 'pong-iabv-test' y nada mas."`
    - response_wait_seconds 45
    - reingest_only=False
- **assertion**: `result['prompt_pasted'] is True`, `result['response_captured'] is True`,
  `result['captured_text']` contiene `pong-iabv-test` o razonablemente alineado.
- **fallo esperado / adversarial**: si Cloudflare aparece, debería devolver
  `error_message='browser_security_verification'`. Si no hay sesión, debería
  devolver `error_message='assistant_login_required'`. Ambos deben ser
  surfacedados limpiamente.

### Test 2 — It should reingest existing thread without re-pasting prompt
(Fix PR #21 validado sobre browser_dom branch.)
- **test_start**: `It should reingest DOM without pasting when reingest_only=True`
- **precondición**: el hilo del Test 1 dejó respuesta visible.
- **acción**:
  - volver a invocar `_capture_browser_dom_response` con mismos args pero
    `reingest_only=True`, `prompt_text="NO-DEBE-PEGARSE"`.
- **assertion**:
  - `result['prompt_pasted'] is False` (no se pegó).
  - `result['response_captured'] is True` (leyó la respuesta previa).
  - `result['captured_text']` sigue conteniendo la respuesta original del
    Test 1, NO contiene `NO-DEBE-PEGARSE`.
  - `result['capture_source'] == 'browser_dom_reingest'`.
- **fallo esperado**: si hay regresión del bug del PR #21, veríamos
  `prompt_pasted=True` y `captured_text` conteniendo `NO-DEBE-PEGARSE`.

## Qué NO voy a probar en esta sesión
- Rama clipboard fallback (PR #21 real) — requiere Win32 + ventanas de
  escritorio. Queda cubierto por los tests unitarios
  `test_ui_execution_runner_skips_paste_in_clipboard_reingest_only` y
  `test_ui_execution_runner_still_pastes_prompt_when_not_reingesting`.
- Popup de credenciales de PySide6/QML (PR #12) — UI Windows-only.
- Popup de permission_gate (PR #15) — UI Windows-only.
- Bateria completa en Windows — el usuario lo valida en su máquina real.

## Artefactos a producir
- Recording con anotaciones `setup/test_start/assertion`.
- Evidence `data/tool_teaching/external_assistants/web_program_session/browser_profile/`
  con cookies de sesión.
- Actualizar <ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/evolution/audits/human-audit-2026-04-19.md" />
  con sección "ChatGPT web assisted — test real".
- Cerrar o actualizar <ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/evolution/pending_issues/audit-2026-04-19-chatgpt-web-validation.json" />:
  status → `observed` si pasa, `needs_fix` + nuevo PR si falla.

## Riesgos conocidos
- Cuenta puede tener 2FA sin previo aviso → bloqueo, pediría TOTP.
- Cuenta puede estar flaggeada por OpenAI por login desde IP nueva → espera
  captcha / verificación email. No puedo resolver sin ayuda del usuario.
- Playwright `launch_persistent_context` no puede abrir un profile ya usado
  por otro Chromium. Hay que cerrar el Chrome visible antes de correr el
  runner, o usar `connect_over_cdp` + ejecutar lógica de DOM equivalente al
  runner para no bloquear la conexión.
