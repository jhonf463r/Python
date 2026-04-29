# 2026-04-28 Codex Startup Timeline Live Follow-up

## Scope

Live audit on Windows after merging startup instrumentation and the
`startup_health` cable into `PortableContextService` and
`OperationalSelfExaminationService`.

## What Was Fixed In This Follow-up

1. `src/iabv_v15/bootstrap.py`
   - The internal MCP child now forces `IABV_STARTUP_TIMELINE=0`.
   - Reason: the startup timeline must audit the visible UI boot, not the MCP
     helper process.

2. `scripts/run_mcp_bridge.ps1`
   - The external MCP path used by `start_iabv.ps1` now also forces
     `IABV_STARTUP_TIMELINE=0`.
   - Reason: the real user path launches MCP outside the UI process, and that
     process was contaminating `data/logs/startup_timeline.jsonl`.

3. Tests
   - `tests/test_startup_evolution.py`
   - `tests/test_run_mcp_bridge_script.py`

## Live Evidence

### Before the bridge fix

`data/logs/startup_timeline.jsonl` was polluted by a second `bootstrap_init_done`
 event coming from the externally launched MCP server. That broke the
 metacognitive reader because the JSONL interleaved UI and helper-process
 phases.

### After the bridge fix

The timeline became UI-only again:

```json
{"phase":"bootstrap_init_done","t_ms_from_start":19107.0}
{"phase":"run_start","t_ms_from_start":19108.2}
{"phase":"splash_visible","t_ms_from_start":20084.7}
{"phase":"main_window_shown","t_ms_from_start":20272.5}
{"phase":"populate_ui_start","t_ms_from_start":20276.4}
{"phase":"populate_ui_done","t_ms_from_start":40965.0}
{"phase":"deferred_post_window_setup_done","t_ms_from_start":47114.6}
```

### Visible behavior still unresolved

Even with a clean timeline:

- the visible window at ~80s is still the BURVE splash
- the splash text can show either `Listo` or `Construyendo ViewModels...`
- the app has already logged:
  - `main_window_shown`
  - `splash_set_ready`
  - `populate_ui_done`
  - `deferred_post_window_setup_done`

Reference screenshot:
- `data/audit/startup_live_80s_no_bridge_noise.png`

This means the current startup code is declaring readiness too early or against
the wrong window object.

## Bridge / Chat Evidence

At the same time:

- `127.0.0.1:18921` is listening
- `UIBridgeServer` reports `ui_running=True`
- `send_message` returns `queued`
- `read_messages` still returns only the initial assistant greeting
- `current_page` stays `unknown`

So the bridge exists, but the visible UI remains stuck in the splash state and
the chat path does not complete the queued message.

## Main Conclusion

The instrumentation is now trustworthy enough to say this:

1. the helper-process timeline contamination is fixed
2. the remaining bug is a real startup readiness mismatch
3. the splash is still blocking or masking the actual shell/chat transition

## Next Recommended Slice

1. Trace the code path that controls splash dismissal versus shell visibility.
2. Verify whether `main_window_shown` is emitted for the splash container
   instead of the real shell.
3. Inspect why `current_page` remains `unknown` after `ui_populated`.
4. Audit `send_message_from_bridge()` / `sendChat()` once the shell transition
   is truthful.
