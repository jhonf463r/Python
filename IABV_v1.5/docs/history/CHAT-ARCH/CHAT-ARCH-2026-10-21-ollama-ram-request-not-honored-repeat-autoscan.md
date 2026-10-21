# IABV — Ollama RAM request not honored; broad auto-scan repeated

- **Date:** 2026-10-21 (America/Bogota)
- **Evidence class:** owner-supplied IABV output; no independent local/runtime inspection.
- **Owner's requested order:** diagnose/correct Ollama RAM pressure first; afterwards ask Codex for a bounded static audit of IABV's existing reasoning, resource handling, inter-IA coordination and progress visibility.
- **Current bridge state remains:** `GOVERNANCE=KEEP_BLOCKED`, `BRIDGE=BRIDGE_NOT_READY`, `REAL_TRANSPORT=NOT_RUN`.

## What the supplied output says

Instead of the requested scoped RAM report, IABV returned the broad `== AUTO-UPDATE ==` self-diagnostic again. It reported:
- `Branch: HEAD`, 282 modified source files and 9004 ignored cache/data items.
- 348 files syntactically checked, 66 MCP tools, 68 QML-callable methods, 27 passing tests, 8 performance issues.
- `Ollama: ok`, model `qwen3:8b` listed as loaded, and 10 models available.
- GPU issue still described as `qwen3:8b` running 100% on CPU, while an automatic correction again claims `CUDA_VISIBLE_DEVICES: '' → 0` and a model reload.
- An automatic environment action again claims `GITHUB_TOKEN_IABV → GITHUB_TOKEN`, as well as sourcing a secrets file that yielded zero loaded secrets.
- 182 remote branches marked ignored due to unsafe prefix; this report says no obsolete branches were deleted in this run.
- Reported historical counters rose to `force_ollama_to_nvidia 1/1`, `verify_cuda_installation 1/1`, `source_secrets_file 55/55`, and `map_secret_alias 33/33`.
- Reported scan time 73.58 seconds; it does not provide per-process memory, RAM total/free before and after, Ollama server/runner PID lineage, model residency duration, or a measured before/after resource outcome.

Every runtime or action claim above is `OWNER_REPORTED`. The report is not independent proof of process state, changes, model utilization or the execution result.

## Adjudication

1. **Scope failure:** the RAM-focused instruction asked for bounded resource evidence and, if safe configuration existed, a narrowly reversible mitigation. IABV returned another all-environment scan and did not supply the requested resource measurements. `RAM_DIAGNOSIS=UNRESOLVED`, `SAFE_FIX=NOT_APPLIED_OR_UNVERIFIED`.
2. **Possible state mismatch:** the owner said Ollama had been closed because of memory use; the following IABV output says `Ollama: ok` and reports a loaded model. This does not prove IABV restarted Ollama: the report could be stale, refer to a different process/session, or describe a real running service. The actual state is `UNRESOLVED` and must not be probed by launching processes or broad scans.
3. **Correction not durably demonstrated:** the same GPU issue and auto-correction appear again despite earlier claims that the correction and reload had been successful. This shows that the supplied reports do not demonstrate a durable, measured postcondition. It does not independently prove whether the operation was executed.
4. **Unrelated credential action:** the reported GitHub token alias mapping is out of scope for RAM diagnosis. Do not repeat it, source secret files, display token values or adjust credential mappings without separate explicit authorization.
5. **Branch history needs restraint:** the preceding owner-supplied report claimed 31 remote branch deletions. This report states no obsolete branches were deleted in this run and 182 are ignored. Without verified before/after remote refs and per-operation receipts, neither report proves the current remote-ref state or reconciles the earlier claim.
6. **Learning counters are not outcome verification:** `1/1`, `55/55` and `33/33` have no cited execution IDs, independent outcome receipts or correlated later validation. Repeated GPU detection after the claimed correction makes a simple success counter especially insufficient to establish durable correction or causal learning.
7. **Do not infer GPU or RAM improvement:** neither utilization-after nor RAM-after evidence was supplied.

## Immediate safe boundary

Do not prompt IABV's general self-diagnostic again for this RAM task. Do not trigger another Ollama/model reload, change CUDA or environment variables, modify token aliases, delete branches, open a browser/login flow or launch Codex/MCP to continue.

A valid RAM diagnosis would require an already-supported, bounded, read-only observation path exposing the relevant current measurements and process attribution. If that path is unavailable, stop and say so rather than performing a broad scan. Any configuration change or process restart needs a separate, specific authorization after the source of pressure is evidenced.

The later Codex audit of IABV reasoning should use an independently verifiable direct Codex session and the allowed public/documentary source scope, not the unverified browser fallback. This incident does not authorize Codex CLI/App Server launch or real transport.

## Preserved states

`RAM_DIAGNOSIS=UNRESOLVED`  
`SAFE_FIX=NOT_APPLIED_OR_UNVERIFIED`  
`GOVERNANCE=KEEP_BLOCKED`  
`BRIDGE=BRIDGE_NOT_READY`  
`REAL_TRANSPORT=NOT_RUN`  
`LOCAL_WORKTREE=UNTOUCHED`
