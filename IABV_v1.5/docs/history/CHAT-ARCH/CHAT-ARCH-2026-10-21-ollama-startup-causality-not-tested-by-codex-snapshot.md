# Ollama startup causality — direct Codex snapshot did not execute IABV

- Date: 2026-10-21 (America/Bogota).
- Primary user priority: determine why opening IABV starts or activates Ollama, whether activation is necessary for IABV reasoning, and reduce unjustified RAM use before the separate static reasoning/bridge audit.
- Evidence: owner-supplied direct Codex/PowerShell snapshot at 18:22:46 UTC−05:00, prior IABV diagnostic outputs, and canonical governance state.
- Important correction: the direct Codex RAM snapshot did NOT launch IABV, reproduce IABV startup, or observe the transition from IABV closed to IABV open. It cannot answer what causes Ollama to start when IABV opens.

## Snapshot facts, limited to the supplied evidence

The owner-reported PowerShell snapshot showed 16,088 MB total RAM, 4,962 MB free, and 69.2% used. It observed ollama.exe PID 12316 with 18.4 MB working set and 60.7 MB private memory. Opera and ChatGPT processes were among the largest visible working sets; Memory Compression and MsMpEng also appeared among the top consumers. These values describe one instant and remain OWNER_REPORTED.

Consequences:
- The snapshot does not support attributing 56% of physical RAM to the observed ollama.exe process itself.
- It does not rule out a prior peak, a model runner with another process name, a resident model, shared-memory accounting, or a different process state at IABV startup.
- It cannot establish whether IABV started the server, whether the server persisted after the user closed it, or whether another launcher/service started it.
- The earlier IABV self-diagnostic's claim that qwen3:8b was loaded and GPU-corrected is separate OWNER_REPORTED material; the process snapshot does not verify it.
- No correction was applied or verified.

## The actual unanswered technical question

The next code-level question is not merely “is Ollama running now?” It is:

**What exact local IABV startup call path starts or activates Ollama, under which condition, and is that path required for the functions the user is invoking?**

Once a legitimate scoped-read route exists, trace only these source connections:
1. IABV application startup entry, bootstrap, service registration and model/provider initialization.
2. The exact caller that launches Ollama, connects to an existing endpoint, or checks health; distinguish process spawn from an HTTP probe and from an independently running service.
3. Whether the trigger is eager at application startup, lazy on a local-model request, model warm-up, readiness preflight, a background/autonomous loop, fallback routing, or a separately selected feature.
4. The provider/model selector and which IABV capabilities actually require a local model versus any configured alternative provider.
5. Whether the code loads a model or only checks the endpoint; the lifecycle/keep-alive policy and relevant non-secret configuration.
6. The smallest supported way to make local inference lazy/optional or limit residency if the source shows it is unnecessary at startup. Do not assume Ollama is unnecessary; establish the dependency before recommending disabling it.

These are hypotheses to distinguish, not facts already established by the snapshot.

## Boundary and next action

The canonical CURRENT-STATE says local source inspection was denied by governance_blocked=true / operational_block_active, and the exact governance-owned scoped-read route remains unresolved.

Next action: identify and use a supported governance-owned scoped-read operation for an already owner-authorized, strictly read-only trace of IABV startup → Ollama launch/connection → model/provider selection, together with the existing Codex executor/consumer identity seam. Do not inspect the local dirty checkout through another reader or infer local code from public main.

Do not launch IABV to reproduce the problem yet. Do not restart Ollama, load/reload a model, change source/config, CUDA/environment variables, credential aliases, or remote branches. Do not launch Codex CLI/App Server, IABV/MCP, browser fallback or real transport while the gate is unresolved.

A GET to 127.0.0.1:11434/api/ps may later be a supplementary read-only observation if the endpoint is already listening; it can identify resident models but cannot identify which IABV code path caused launch. It must not substitute for the startup-source trace.

After the source path is established, any live before/after experiment needs its own specific authorization and should be small and controlled. The separate Codex static audit of IABV's reasoning follows the RAM/startup diagnosis; do not combine these tasks into another general auto-scan.

## Preserved states

RAM_DIAGNOSIS=PARTIAL  
OLLAMA_STARTUP_CAUSE=UNRESOLVED  
MODEL_RESIDENCY=UNRESOLVED  
FIX=NOT_APPLIED  
GOVERNANCE=KEEP_BLOCKED  
BRIDGE=BRIDGE_NOT_READY  
REAL_TRANSPORT=NOT_RUN
