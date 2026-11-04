# P0.21x-R11-POST: Baseline Interaction Post-Readback - Final Report

### Interaction
- **Message**: "Responde únicamente con la palabra BASELINE_OK."
- **Response**: "BASELINE_OK"
- **Interaction ID**: chat-4e75e497654c
- **Dispatch ID**: 93bf88f09ace

==================================================
1. DATABASE READ-BACK
==================================================

### STATE(t0) - Pre-Interaction
- run_records count: 0
- adaptive_sessions count: 0
- session_artifacts count: 0
- episodes count: 0
- chat_messages count: 0 (not checked in pre-snapshot)

### STATE(t1) - Post-Interaction
- run_records count: 1 ✓
- adaptive_sessions count: 1 ✓
- session_artifacts count: 0
- episodes count: 0
- chat_messages count: 3 ✓

### New Run Record
- **run_id**: 2e3ffacf-10d1-4fd0-ab45-a4639fae425e
- **session_id**: 78c130c2-b108-4723-bdca-2d9b30d10004
- **status**: success
- **provider_name**: Adaptive local orchestrator
- **model**: qwen3:8b
- **used_fallback**: false
- **error_summary**: None
- **raw_output**: BASELINE_OK
- **created_at_utc**: 2026-08-16T21:22:16.262216+00:00

### New Adaptive Session
- **session_id**: 78c130c2-b108-4723-bdca-2d9b30d10004
- **run_id**: 2e3ffacf-10d1-4fd0-ab45-a4639fae425e
- **status**: completed
- **intent_key**: general.assistance
- **pack_id**: knowledge.query
- **summary**: BASELINE_OK
- **created_at_utc**: 2026-08-16T21:22:03.244130+00:00
- **updated_at_utc**: 2026-08-16T21:22:16.583622+00:00

### New Chat Messages
- **Message 1** (user): "Responde únicamente con la palabra BASELINE_OK."
  - created_at_utc: 2026-08-16T21:21:04.010991+00:00
- **Message 2** (assistant): "BASELINE_OK"
  - created_at_utc: 2026-08-16T21:22:17.431373+00:00
  - provider: Adaptive local orchestrator
  - model: qwen3:8b
  - evidence_tag: observed
  - reasoning_path: orchestrator_inference

==================================================
2. RUNTIME AUDIT
==================================================

### New Events (Post-STATE(t0))
- **interaction_open**: 2026-08-16T21:21:04.008+00:00
  - interaction_id: chat-4e75e497654c
  - message_preview: "Responde únicamente con la palabra BASELINE_OK."
- **dispatch_started**: 2026-08-16T21:21:04.094+00:00
  - dispatch_id: 93bf88f09ace
  - task_name: chat
  - provider: ""
  - source: sendChat
- **dispatch_terminal**: 2026-08-16T21:22:17.526+00:00
  - dispatch_id: 93bf88f09ace
  - terminal_state: success
  - provider: Adaptive local orchestrator
  - reason: resolved
- **interaction_resolved**: 2026-08-16T21:22:17.527+00:00
  - interaction_id: chat-4e75e497654c
  - outcome: resolved
  - provider: Adaptive local orchestrator
  - total_duration_ms: 73520.2

==================================================
3. TEMPORAL EXPERIENCE
==================================================

### Duration Evidence
- **total_duration_ms**: 73520.2 (73.5 seconds)
- **Classification**: DIRECT_RUNTIME_EVIDENCE ✓

### Phases
- **start**: 2026-08-16T21:21:04.007+00:00
- **first_technical_response**: 2026-08-16T21:21:04.097+00:00
- **first_useful_response**: 2026-08-16T21:22:17.431+00:00
- **final_resolution**: 2026-08-16T21:22:17.527+00:00
- **Classification**: DIRECT_RUNTIME_EVIDENCE ✓

### Window Activity
- **initial_window_active**: true
- **initial_window_visible**: true
- **window_went_inactive**: true
- **window_inactive_intervals**: 2
- **Classification**: DIRECT_RUNTIME_EVIDENCE ✓

==================================================
4. PROVIDER
==================================================

### Provider Evidence
- **Provider**: Adaptive local orchestrator
- **Model**: qwen3:8b
- **Classification**: PROVIDER_INVOKED ✓

### TCP Evidence
- **PID 24276 → 127.0.0.1:11434**: NOT_OBSERVED
- **Ollama process**: PID 17088 (listening on 11434)
- **Classification**: PROVIDER_NOT_OBSERVED (via TCP)
- **Note**: Provider invocation is confirmed via runtime_audit and database, but TCP connection was not captured by Get-NetTCPConnection

==================================================
5. SESSION / MEMORY
==================================================

### Session Evidence
- **session_id**: 78c130c2-b108-4723-bdca-2d9b30d10004 ✓
- **run_id**: 2e3ffacf-10d1-4fd0-ab45-a4639fae425e ✓
- **adaptive_session**: CREATED ✓
- **summary**: BASELINE_OK ✓
- **Classification**: SESSION_CREATED ✓

### Learning Evidence
- **intent_key**: general.assistance
- **pack_id**: knowledge.query
- **Classification**: SESSION_METADATA_RECORDED ✓

==================================================
6. GESTURE
==================================================

### Gesture Evidence
- **"siguiente gesto sugerido"**: NOT_OBSERVED
- **strategy_packs**: 10 existing packs (no new ones created)
- **Classification**: GESTURE_NOT_SUGGESTED ✓

==================================================
7. STATE DELTA
==================================================

### STATE(t0) → STATE(t1)
- **run_records**: 0 → 1 ✓
- **adaptive_sessions**: 0 → 1 ✓
- **chat_messages**: 0 → 3 ✓
- **session_artifacts**: 0 → 0 (no change)
- **episodes**: 0 → 0 (no change)

### State Changes Observed
- **New run_record**: ✓
- **New adaptive_session**: ✓
- **New chat_messages**: ✓
- **No session_artifacts**: ✓
- **No episodes**: ✓

==================================================
8. EVIDENCE CHAIN
================================================##

interaction_id (chat-4e75e497654c)
→ dispatch_id (93bf88f09ace) [DIRECT]
→ session_id (78c130c2-b108-4723-bdca-2d9b30d10004) [DIRECT]
→ run_id (2e3ffacf-10d1-4fd0-ab45-a4639fae425e) [DIRECT]
→ provider (Adaptive local orchestrator) [DIRECT]
→ result (BASELINE_OK) [DIRECT]
→ persistence (run_records, adaptive_sessions, chat_messages) [DIRECT]

==================================================
9. SCIENTIFIC CONCLUSION
==================================================

### A. ¿La interacción fue persistida?
**YES** ✓
- Evidence: run_records (1), adaptive_sessions (1), chat_messages (3)
- Classification: DIRECT_RUNTIME_EVIDENCE

### B. ¿La IA/proveedor fue invocada?
**YES** ✓
- Evidence: runtime_audit dispatch_started, dispatch_terminal, database provider_name
- Classification: DIRECT_RUNTIME_EVIDENCE

### C. ¿La duración de la interacción quedó registrada internamente?
**YES** ✓
- Evidence: total_duration_ms: 73520.2, phases timestamps
- Classification: DIRECT_RUNTIME_EVIDENCE

### D. ¿El organismo registró algún cambio de estado?
**YES** ✓
- Evidence: run_records 0→1, adaptive_sessions 0→1, chat_messages 0→3
- Classification: DIRECT_RUNTIME_EVIDENCE

### E. ¿Se generó una propuesta de siguiente acción?
**NO** ✗
- Evidence: No gesture suggestions observed, no new strategy_packs
- Classification: NOT_OBSERVED

### F. ¿Hubo aprendizaje?
**PARTIAL** ✓
- Evidence: session_id created, intent_key and pack_id recorded
- Classification: SESSION_METADATA_RECORDED

### G. ¿Se creó ExperimentRun?
**YES** ✓
- Evidence: run_id created with full metadata
- Classification: DIRECT_RUNTIME_EVIDENCE

==================================================
10. FINAL VERDICT
================================================##

**BASELINE_EPISODE_PERSISTED**

**Rationale**:
- Interaction was successfully persisted in run_records ✓
- Adaptive session was created with metadata ✓
- Chat messages were recorded ✓
- Provider invocation was confirmed ✓
- Duration was internally recorded (73.5 seconds) ✓
- State changes were observed ✓
- No gesture suggestions were generated (expected for simple query) ✓

**Conclusion**:
The deterministic baseline launch (P0.21x-R10) successfully resolved the persistence issue. The BASELINE_OK interaction was fully persisted in the database with complete metadata, including session information, provider details, and temporal duration. The runtime now correctly records interactions when started from the correct CWD with the proper configuration.

==================================================
11. NEXT_SINGLE_ACTION
================================================##

Investigate the TCP observation mechanism to determine why Get-NetTCPConnection did not capture the connection from PID 24276 to 127.0.0.1:11434, even though the runtime_audit and database confirm provider invocation. This will improve the external observability capability for future experiments.
