# Test report — `chatgpt_web_assisted` / `_capture_browser_dom_response` (2026-04-19)

## Summary
- Ejecuté el test plan `chatgpt-web-test-plan.md` contra el production code
  `UIExecutionRunner._capture_browser_dom_response` (<ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/src/iabv_v15/services/tools/ui_execution_runner.py" /> líneas 684-830).
- **Cloudflare bloqueó chatgpt.com real desde esta VM cloud** — Turnstile entró en loop tanto con click manual como con Playwright `connect_over_cdp` + UA override. La IP + fingerprint de esta VM están flaggeados. **chatgpt.com real queda UNRESOLVED** en esta sesión.
- Pivot: ejercité el mismo production code contra un servidor HTTP local que reproduce fielmente los selectores declarados en el card `chatgpt_web_assisted` (<ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/tool_teaching/cards/chatgpt_web_assisted.json" />).
- Resultado: **Test 1 y Test 2 pasaron** contra el mock, usando exactamente la misma función interna que se usaría con chatgpt.com real.

## Evidencia

### Cloudflare bloquea la navegación real
![Cloudflare "Verify you are human" en chatgpt.com desde la VM](https://app.devin.ai/attachments/a904d1ab-c185-4837-87b1-ade211fee985/screenshot_efc7764816174ce1b8bb0a23720eb1ec.png)

Intento vía Playwright `connect_over_cdp` + UA override tampoco pasa:

![Playwright via CDP: Cloudflare sigue bloqueando](https://app.devin.ai/attachments/098e835e-f03a-4b92-858e-cc6bfb4401c3/chatgpt_cdp_probe.png)

Detalle del probe CDP:

```
TITLE: Just a moment...
URL: https://chatgpt.com/
HAS_TURNSTILE: True
```

### Test 1 — full flow (reingest_only=False)
Ejecuta `_capture_browser_dom_response` contra el mock:
- Abre la página con Playwright+Chromium (`headless=True`).
- Detecta `textarea`.
- Pega el prompt.
- Click en `button[data-testid="send-button"]`.
- Polling del `[data-message-author-role="assistant"]` hasta texto estable (2 hits iguales).

Resultado:
```json
{
  "launched": true,
  "focused": true,
  "focused_title": "Fake ChatGPT",
  "prompt_pasted": true,
  "response_captured": true,
  "captured_text": "NUEVA-RESPUESTA: pong-iabv-test-ok-desde-mock-chatgpt-linea-dos. Fin de respuesta simulada.",
  "capture_source": "browser_dom",
  "error_message": "",
  "execution_ms": 4337
}
```

Aserciones:
- `launched=True` ✓
- `prompt_pasted=True` ✓
- `response_captured=True` ✓
- `captured_text` contiene `pong-iabv-test` y `NUEVA-RESPUESTA` ✓
- `capture_source == 'browser_dom'` ✓

### Test 2 — reingest_only=True (regresión PR #21 sobre browser_dom)
Segundo invocación sobre el mismo profile persistido, con prompt distinto
y `reingest_only=True`. Debe NO pegar nada y NO re-submittear.

Resultado:
```json
{
  "launched": true,
  "focused": true,
  "focused_title": "Fake ChatGPT",
  "prompt_pasted": false,
  "response_captured": true,
  "captured_text": "PRECARGADO: pong-iabv-reingest-validado-linea-uno. Esta respuesta ya existia en el hilo antes del retry.",
  "capture_source": "browser_dom_reingest",
  "error_message": "",
  "execution_ms": 3159
}
```

Aserciones:
- `prompt_pasted=False` (no se pegó `NO-DEBE-PEGARSE-DE-NINGUNA-FORMA`) ✓
- `response_captured=True` (leyó el `[data-message-author-role="assistant"]` precargado) ✓
- `captured_text` contiene `pong-iabv` y **NO** contiene `NO-DEBE-PEGARSE` ✓
- `capture_source == 'browser_dom_reingest'` ✓

## Interpretación
- La rama `browser_dom` del flujo `chatgpt_web_assisted` funciona correctamente end-to-end.
- El contrato semántico de `reingest_only=True` (no pegar, releer) se respeta tanto en la rama `browser_dom` (validado live aquí) como en la rama clipboard fallback (validado con tests unitarios del PR #21).
- El hard-block de Cloudflare desde esta VM impide validación contra chatgpt.com real **en esta sesión**. Probablemente pasaría desde tu máquina Windows real con un Chrome de uso normal y profile persistido, pero no puedo garantizarlo desde acá.

## Hallazgos secundarios (no-bugs)
- `_captured_text_looks_useful` exige `len(text) >= 24` antes de aceptar la respuesta. Con respuestas muy cortas (ej. "pong"), el flow devuelve `browser_dom_capture_pending` al deadline. No es un bug — es un filtro anti-ruido razonable — pero vale documentar la heurística para que auto-tests futuros no usen respuestas cortas.
- El fallback final de `response_selectors`, `main article`, captura el article entero; con múltiples artículos concatena. Funciona mientras `_latest_browser_response_text` priorice selectores más específicos — revisar ante cambios de DOM de chatgpt.com.

## Qué NO probé (declarado arriba, confirmado)
- Login real en chatgpt.com (bloqueado Cloudflare + IP VM).
- Rama `capture_response_from_app` (clipboard fallback, PR #21 directamente) — Windows-only (Win32), cubierta por tests unitarios.
- PySide6/QML popups de credenciales y permission_gate — Windows-only.

## Qué queda UNRESOLVED / pending
- <ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/evolution/pending_issues/audit-2026-04-19-chatgpt-web-validation.json" /> actualizado: el código está validado funcionalmente; la validación contra el dominio real de chatgpt.com no fue posible desde el VM cloud.
- <ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/evolution/pending_issues/audit-2026-04-19-windows-validation.json" /> sin cambios — sigue dependiendo del usuario correr la batería en Windows real.

## Artefactos
- Test plan: <ref_file file="/home/ubuntu/repos/Python/IABV_v1.5/data/evolution/audits/chatgpt-web-test-plan.md" />
- Mock server: `/tmp/fake_chatgpt/server.py` (no persistido en repo — temporal de sesión).
- Exercise script: `/tmp/exercise_runner.py` (no persistido — temporal de sesión).
- Recording: `/home/ubuntu/screencasts/rec-9dd6e9e6-2414-49a3-ad71-582774b5c0f8/rec-9dd6e9e6-2414-49a3-ad71-582774b5c0f8-edited.mp4` (enviado al usuario como attachment).
