# IABV — Codex handoff blocked by resource pressure; wrong-thread rejection and browser fallback

- **Date:** 2026-10-21 (America/Bogota)
- **Evidence class:** owner-supplied IABV responses; no independent local/runtime verification.
- **Primary objective:** `GOVERNED_IABV_CODEX_BRIDGE`.
- **Operational state remains:** `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`.

## Supplied sequence

1. IABV reported it could not start a Codex consultation: `resource_pressure_critical`, `manual_handoff`, build `current`, pressure `critical`, confidence `0.7`; it said it would defer the consultation until pressure decreased.
2. Owner reports closing Ollama because of high RAM use. No post-action RAM/CPU measurement is available here; do not infer how much pressure changed.
3. IABV reported: `Herramienta: Codex instalado. Bloqueo: fallo no clasificado. Evidencia: wrong_thread. La respuesta externa no coincide con el hilo esperado; no se toma como valida y queda marcada para auditoria. Sigo con la via local.`
4. On another attempt, IABV reported browser processes such as `msedgewebview2` without an identified visible window, said it could not verify a linked window and had no DOM/CDP access to read a background response, and asked the owner to complete a login/verification or paste the answer. It also reported: `usé el navegador predeterminado del usuario antes de abrir una ventana gobernada`.

All four events are `OWNER_REPORTED`. They are not independent proof that a browser action, a Codex call or a process-state change occurred.

## Adjudication

- `resource_pressure_critical`: a claimed resource gate stopped or deferred the Codex consultation. It is not evidence that Codex executed or that the bridge worked. The pressure figure/confidence is not corroborated by a resource measurement in this record.
- `wrong_thread`: rejecting an external reply that cannot be correlated with the expected thread is the correct safety behavior if the implementation did as reported. But this rejection means the reply is not a valid task result and does not advance the bridge.
- `browser_fallback`: attempting to use the user's default browser after the scoped-read request, without proving a governed binding to the expected response, is an out-of-scope fallback and must not be used to circumvent the denied route. The lack of DOM/CDP means IABV itself admits it cannot verify the supposed response.
- The request was to identify a legitimate governance-owned scoped read route for the already-authorized static inspection. A browser-based ChatGPT handoff is not that route and cannot establish local executor identity, effective policy, consumer binding or a verifiable bridge receipt.
- Do not ask the owner to log in, complete verification, relay a browser response, or disclose session material as a way to move past this blocker. Do not retry the Codex request by another path, use another reader, launch Codex CLI/App Server, start IABV/MCP, or initiate transport.
- The claimed correct `wrong_thread` rejection is useful only as owner-reported behavior; it is not a validated conformance test of the boundary.

## Next route (unchanged)

`NEXT_STEP=IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.

Use only an existing, explicit, supported governance operation for the already-authorized static inspection of executor registration/caller/consumer and whitelisted non-secret effective policy fields. Exact UI/action remains `UNRESOLVED`. If no such control is available, stop and preserve the block. Do not invent a UI or reinterpret a generic browser session as scoped-read authority.

This incident update is documentary only; it did not inspect local state, run tools in the user's environment, read session data, or alter source code.

## Preserved states

`GOVERNANCE=KEEP_BLOCKED`  
`BRIDGE=BRIDGE_NOT_READY`  
`REAL_TRANSPORT=NOT_RUN`  
`CANDIDATE_MERGED=NO`  
`LOCAL_WORKTREE=UNTOUCHED`  
`LOCAL_EXECUTOR_IDENTITY=UNRESOLVED`  
`LOCAL_EFFECTIVE_CONFIGURATION=UNRESOLVED`
