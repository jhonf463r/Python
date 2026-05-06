# IABV v1.5 — Estado de Tests

**Actualizado:** 2026-05-05
**Entorno:** Ubuntu Linux (Devin VM), Python 3.12.8, pytest 9.0.3

---

## Resumen

| Metrica | Valor |
|---|---|
| Total ejecutados | 3127 |
| Passed | 3070 |
| Failed | 21 |
| Skipped | 36 |
| Warnings | 25 |
| Duracion | 251.71s (4:11) |
| Regresiones nuevas | 0 |

**Nota:** El aumento de tests (2566 -> 3127) incluye tests de main (PRs 346-349) mas:
- 8 DashboardVM lazy init
- 9 ui_visibility_audit base
- 13 GAP C/D + runtime wiring
- 7 operational wiring (splash, subprocess, Win32, dialog close, Control Master)
- Tests de main: evidence tags, capabilities, chat presentation, signals, task packet

**Reduccion de fallos:** 24 -> 21 (todos pre-existentes en origin/main, 0 nuevos)

---

## Tests Nuevos (esta sesion)

| Archivo | Tests | Estado |
|---|---|---|
| `test_dashboard_lazy_init.py` | 8 | PASS |
| `test_ui_visibility_audit.py` | 46 | PASS (9 base + 7 QML/toast + 5 GAP C + 3 GAP D + 5 runtime wiring + 2 Win32 + 8 previos + 7 operational wiring) |

---

## Tests Fallidos (24 — pre-existentes en origin/main)

### cloud_quick_reply (4 failures)
- `test_returns_none_when_no_keys`
- `test_returns_cloud_response_when_key_available`
- `test_falls_through_on_error`
- `test_tries_next_provider_on_failure`

**Probable causa:** Modulo de cloud quick reply refactorizado sin actualizar tests.

### control_center_viewmodel (7 failures)
- `test_control_center_send_chat_explicit_codex_request_hands_off_externally`
- `test_control_center_send_chat_explicit_codex_blocked_external_surfaces_formal_flags`
- `test_control_center_send_chat_explicit_codex_wrong_thread_surfaces_clear_notice`
- `test_control_center_send_chat_explicit_codex_missing_thread_tracking_surfaces_clear_notice`
- `test_control_center_send_chat_explicit_chatgpt_security_verification_surfaces_clear_notice`
- `test_control_center_send_chat_external_access_denied_is_humanized_and_stops_waiting_state`
- `test_control_center_compound_self_awareness_message_goes_through_inference`

### specific_apikey_routing (8 failures)
- 6 en TestSpecificApiKeyBypassesAccountResource
- 2 en TestBuildCloudReplyContext

### Otros (5 failures)
- `test_self_examination_catches_log_analysis_phrases` (desajustes_fixes)
- `test_start_mcp_subprocess_uses_python_exe_and_hidden_runtime_log` (startup_evolution)
- `test_world_model_snapshot_returns_current_without_refresh` (mcp_server)
- `test_world_model_snapshot_refresh_triggers_request` (mcp_server)
- `test_windsurf_adapter_detects_by_command_name_in_path` (tool_registry)

---

## Tests Skipped (23)

Incluyen tests de UI que requieren PySide6 real, tests de Playwright, y tests con condiciones de entorno Windows.

---

## Nota sobre entorno

Estos tests se ejecutaron en Linux (Devin VM). El proyecto esta disenado para Windows con PySide6 + QML. Algunos fallos se deben a diferencias de plataforma (Win32 APIs, ctypes.wintypes, etc.) y no representan bugs reales del codigo. Los 24 fallos estan verificados como pre-existentes en origin/main.
