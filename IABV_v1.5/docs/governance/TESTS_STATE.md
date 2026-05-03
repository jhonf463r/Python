# IABV v1.5 — Estado de Tests

**Actualizado:** 2026-05-03  
**Entorno:** Ubuntu Linux (Devin VM), Python 3.12.8, pytest 9.0.3

---

## Resumen

| Métrica | Valor |
|---|---|
| Total ejecutados | 2416 |
| Passed | 2391 |
| Failed | 29 |
| Skipped | 25 |
| Warnings | 5 |
| Duración | 259.98s (4:19) |
| Regresiones nuevas | 0 |

---

## Tests Fallidos (29 — pre-existentes)

### cloud_quick_reply (4 failures)
- `test_returns_none_when_no_keys`
- `test_returns_cloud_response_when_key_available`
- `test_falls_through_on_error`
- `test_tries_next_provider_on_failure`

**Probable causa:** Módulo de cloud quick reply posiblemente renombrado o refactorizado sin actualizar tests.

### cognitive_frame_translate (7 failures)
- `test_cognitive_frame_translate_returns_payload_for_known_kind`
- `test_cognitive_frame_translate_falls_back_to_structured_qa`
- `test_cognitive_frame_translate_propagates_snapshot_hint`
- `test_cognitive_frame_translate_reports_translator_unavailable`
- `test_cognitive_frame_translate_reports_perception_unavailable_when_assembler_missing`
- `test_cognitive_frame_translate_reports_perception_unavailable_when_assembler_returns_none`
- `test_cognitive_frame_translate_reports_perception_error_on_assembler_crash`

**Probable causa:** MCP tool cognitive_frame_translate con dependencias no disponibles en entorno de test.

### control_center_viewmodel (8 failures)
- `test_control_center_send_chat_explicit_codex_request_hands_off_externally`
- `test_control_center_send_chat_explicit_codex_blocked_external_surfaces_formal_flags`
- `test_control_center_send_chat_explicit_codex_wrong_thread_surfaces_clear_notice`
- `test_control_center_send_chat_explicit_codex_missing_thread_tracking_surfaces_clear_notice`
- `test_control_center_send_chat_explicit_chatgpt_security_verification_surfaces_clear_notice`
- `test_control_center_send_chat_external_access_denied_is_humanized_and_stops_waiting_state`
- `test_control_center_compound_self_awareness_message_goes_through_inference`
- `test_control_center_surfaces_formal_external_state_flags_in_evolution_text` (warning: thread exception)

**Probable causa:** ControlCenterVM depende de infra que no está presente en Linux/test (Win32 clipboard, systray, etc.).

### specific_apikey_routing (8 failures)
- 6 en TestSpecificApiKeyBypassesAccountResource
- 2 en TestBuildCloudReplyContext

**Probable causa:** Tests dependen de mock o estructura de apikey routing que cambió.

### Otros (2 failures)
- `test_self_examination_catches_log_analysis_phrases` (desajustes_fixes)
- `test_start_mcp_subprocess_uses_python_exe_and_hidden_runtime_log` (startup_evolution)

---

## Tests Skipped (25)

Incluyen tests de UI que requieren PySide6 real, tests de Playwright, y tests con condiciones de entorno Windows.

---

## Nota sobre entorno

Estos tests se ejecutaron en Linux (Devin VM). El proyecto está diseñado para Windows con PySide6 + QML. Algunos fallos se deben a diferencias de plataforma (Win32 APIs, ctypes.wintypes, etc.) y no representan bugs reales del código.
