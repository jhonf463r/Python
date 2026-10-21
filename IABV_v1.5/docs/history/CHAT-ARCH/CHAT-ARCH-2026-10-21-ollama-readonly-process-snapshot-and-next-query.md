# Ollama RAM — owner-supplied read-only process snapshot and next bounded query

- **Date/time:** 2026-10-21 18:22:46, America/Bogota (UTC−05:00), as reported by the owner from direct Codex/PowerShell output.
- **Provenance:** `OWNER_REPORTED`; no separate local query was performed in this coordinator session.
- **Owner priority:** diagnose Ollama RAM pressure first, then perform a bounded static Codex audit of IABV reasoning/coherence. No bridge launch.
- **Preserved state:** `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`.

## Supplied current snapshot

- `LOCAL_TARGET=CONFIRMED`, `RAM_SNAPSHOT=COMPLETE`, `OLLAMA_PROCESS=OBSERVED`, `RAM_DIAGNOSIS=PARTIAL`.
- Total RAM `16,088 MB`, free `4,962 MB`, used `11,126 MB` (`69.2%`).
- Observed `ollama.exe` PID `12316`: working set `18.4 MB`, private memory `60.7 MB`; parent was unavailable in the supplied capture.
- No other process name matching Ollama was reported in that snapshot. This does not establish whether a model was resident in-process, whether a runner's name failed the filter, or whether an earlier high-RAM state differed.
- Top consumers included Opera processes with working sets `801.0`, `637.7`, `410.8`, `388.8`, `290.0`, `265.2`, `224.9`, `207.4`, and `171.1 MB` (among others); ChatGPT processes with `598.3`, `402.5`, `256.7 MB`; `Memory Compression` `562.7 MB`; and `MsMpEng.exe` `353.5 MB`.
- Codex and several Python processes were also observed, but the supplied snapshot intentionally omitted full command lines/paths, so the Python processes cannot be safely attributed to IABV from this information alone.

## Adjudication

1. At the reported time, the `ollama.exe` server process itself had a relatively small working set and private-memory footprint. The snapshot does **not** support concluding that this specific process alone consumed 56% of physical RAM.
2. Overall system memory use was `69.2%`, while multiple Opera and ChatGPT processes were among the largest visible working sets. A single snapshot cannot determine what changed when IABV opened, establish causal attribution, or prove those other processes should be closed.
3. The preceding IABV self-diagnostic claimed that `qwen3:8b` was loaded, but this is a separate `OWNER_REPORTED` output and is not reconciled by the process snapshot. It is unknown whether a model/runner was resident at snapshot time.
4. Do not infer that IABV restarted Ollama. The reported process may have persisted, restarted earlier, or been observed at a different moment; the event sequence is not established.
5. Root cause remains `PARTIAL/UNRESOLVED`; no fix has been applied or verified.

## Corrected next step — determine the IABV startup caller before runtime reproduction

The snapshot was taken by direct Codex/PowerShell without launching IABV. It therefore did not reproduce, observe or explain the event that activates Ollama when IABV opens. The immediate goal is to establish the exact IABV startup -> Ollama launch/connect -> model/provider-selection source path and determine whether local inference is mandatory for the route IABV was using. This requires a legitimate governance-owned scoped source-read route; the local reader was previously denied, and another reader must not be used to bypass it. An optional read-only /api/ps query may identify resident models if Ollama is already listening, but cannot establish startup causality. Do not start IABV or Ollama, reload models, change configuration or conduct a live reproduction in this phase.

## No authorization implied

This record authorizes no source read, code edit, config change, process restart, token mapping, CUDA change, model reload, branch deletion, bridge launch or real transport.

`RAM_DIAGNOSIS=PARTIAL`  
`MODEL_RESIDENCY=UNRESOLVED`  
`FIX=NOT_APPLIED`  
`GOVERNANCE=KEEP_BLOCKED`  
`BRIDGE=BRIDGE_NOT_READY`  
`REAL_TRANSPORT=NOT_RUN`
