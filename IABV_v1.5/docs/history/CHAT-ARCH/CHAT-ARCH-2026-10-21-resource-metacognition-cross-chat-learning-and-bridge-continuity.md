# IABV — Resource metacognition, cross-chat learning, human interaction, and bridge continuity

- **Date:** 2026-10-21, America/Bogota.
- **Status:** durable documentary reconciliation; no product implementation, local checkout read, process mutation, or bridge launch.
- **Owner objective:** build IABV as a governed, space-time-continuous assistant that retains and contrasts experience across chats, uses multiple AIs according to their capabilities, manages its own resource footprint safely, and ultimately delegates to Codex through a verifiable governed bridge.
- **Evidence labels:** all local PowerShell metrics below are `OWNER_REPORTED` via the pasted Codex result. GitHub source and prior canonical documents were fetched through the GitHub connector in the coordinator session. No claim is made that this coordinator directly inspected the Windows machine.

## 1. Canonical governance and active route remain unchanged

The top snapshot of `CURRENT-STATE.md` remains the sole routing authority.

```
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
CANDIDATE_MERGED=NO
LOCAL_WORKTREE=UNTOUCHED
ROUTE_A=NO_GO_KEEP_BLOCKED
```

The sole active next step remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`. The last reader operation was denied by `governance_blocked=true` / `operational_block_active` and read zero source files. Do not retry the blocked reader, switch to an alternate reader to bypass it, launch IABV/MCP or Codex CLI/App Server, or use a prompt to pretend the access gate has been lifted. The exact supported route and local executor identity/effective configuration remain unresolved. This record supplements but does not supersede current routing authority.

The scope-fix candidate remains unmerged; the reported run collected 76 tests, with 74 passed and 2 failed (exit 1). The two reported failures concern the `_FakeWorldModelService.scan_stats` fixture mismatch. Do not reopen that test investigation or widen candidate scope absent a separately authorized reason.

## 2. New resource observation — bounded Codex/PowerShell sample

**Observation window:** 2026-10-21 22:15:14.302–22:15:21.635 America/Bogota. Provenance: pasted `LLAMA_RAM_DIAGNOSTIC_RESULT`, therefore `OWNER_REPORTED`.

- Physical RAM total: 16,087.50 MB.
- Available RAM: 3,929.19 → 3,849.62 MB.
- Used RAM: 75.58% → 76.07%.
- `llama-server.exe`: zero instances across all three samples.
- `ollama.exe`: PID 12316, path `C:\Users\faber\AppData\Local\Programs\Ollama\ollama.exe`, working set 26.47 MB (0.165% of physical RAM), private bytes 61.79 MB.
- Parent PID 13284 was not present in the samples; parent attribution is partial.
- Local Ollama API answered `GET /api/ps`, with no resident models listed.
- No process actions or configuration changes were reported.
- The first version of the diagnostic script failed at PowerShell parsing and did not collect samples; only the corrected run above is evidence.

### Bounded interpretation

1. At this exact observation window, the evidence does not support attributing the global 76.07% RAM use to an active `llama-server.exe` or to models listed by `/api/ps`.
2. This does **not** refute the owner's earlier report that `llama-server.exe` was using roughly 60% of RAM at another time. The event was not reproduced, and its temporal cause remains unresolved.
3. The top-15 working-set list included several Opera and ChatGPT processes, `Memory Compression`, `opencode-cli.exe` (456.51 MB working set; 865.58 MB private), and `MsMpEng.exe`. These are comparison evidence, not a complete accounting of RAM and not causal proof. Working set and private bytes are different metrics and must not be added as independent consumption.
4. A snapshot that does not observe a process cannot establish what starts it when IABV opens, whether local inference is required, or whether a model runner appeared transiently before/after the sample.
5. The previous snapshot at 18:22 reported 69.2% RAM use and `ollama.exe` at 18.4 MB working set / 60.7 MB private. Both snapshots are point-in-time observations; they do not establish startup causality or a durable fix.

State:
```
RAM_DIAGNOSIS=PARTIAL
CURRENT_LLAMA_SERVER=NOT_OBSERVED
CURRENT_RESIDENT_OLLAMA_MODELS=NONE_REPORTED_BY_API
HISTORICAL_60_PERCENT_CAUSE=UNRESOLVED
OLLAMA_STARTUP_CAUSALITY=UNRESOLVED
RESOURCE_PRESSURE_GUARD_THRESHOLD=UNRESOLVED
FIX=NOT_APPLIED_OR_VERIFIED
```

## 3. Metacognitive deduction: a warning is not a diagnosis or a learning event

The owner supplied an IABV response:

```
No puedo iniciar la consulta a Codex ahora.
Razon: resource_pressure_critical
Accion requerida: Presion critica de recursos (RAM/CPU). Diferire la consulta hasta que baje la presion.
Sesion: manual_handoff | Build: current | Presion: critical | Confianza: 0.7
```

This is an owner-supplied report, not a verifiable resource receipt. It does not contain the measured RAM/CPU values, sampling timestamp/source, processes/models that triggered the gate, threshold/policy version, defer decision ID, or objective re-evaluation condition. Confidence `0.7` cannot replace the missing evidence.

Future resource gating should persist a correlated receipt with:
- observation ID, timestamp, source, freshness and units;
- physical RAM total/available/used and, where relevant, a defined CPU window;
- per-process PID, parent, executable identity, working set/private bytes; resident model list and size/VRAM only if the existing endpoint is already listening;
- exact policy/threshold/version and which measured predicate fired;
- decision ID, reason for defer, bounded retry/re-evaluation condition and lowest-cost authorized diagnostic alternative;
- action ID if a separately authorized mitigation is performed;
- post-action observation and explicit postcondition;
- links connecting observation → decision → action → post-observation → verified outcome.

Distinguish:
- `RESOURCE_PRESSURE_DETECTED`: a threshold was crossed;
- `CAUSE_ATTRIBUTED`: evidence links a particular process/model/behavior to the pressure;
- `MITIGATION_AUTHORIZED`: an action is separately permitted;
- `MITIGATION_APPLIED`: an execution receipt proves it happened;
- `MITIGATION_VERIFIED`: a post-observation proves the expected improvement;
- `LEARNING_PERSISTED`: the experience is stored with provenance and is retrievable/reused by a later decision.

Never collapse these states. Do not claim that IABV controls/stabilizes its environment merely because it can detect pressure or emit a deferral message.

## 4. Resource optimization is a future research hypothesis, not permission to change runtime

The owner proposes that if a tool/model has an unjustifiably high resource footprint, IABV should investigate lighter alternatives and potentially replace, lazily load, or avoid installing/running unnecessary components.

This is a valid **PROPOSED research direction**, not a finding that Ollama or any specific model is unnecessary. Once the legitimate scoped-read route exists, source review should establish:
1. the exact IABV startup path and whether it spawns Ollama, connects to an existing endpoint, performs health/readiness checks, warms a model, or selects a fallback;
2. which IABV functions truly require local inference versus an existing remote/provider route;
3. whether the model is eagerly loaded or only loaded on demand, its lifecycle/keep-alive behavior, and whether multiple servers/runners can overlap;
4. the actual quality/latency/functional requirements and RAM/VRAM measurements for the relevant tasks;
5. whether lazy loading, optional local inference, shorter residency, a smaller quantized model, or another already-supported provider can meet requirements without losing necessary capability;
6. whether alternatives can be installed or changed under existing constraints (no new paid plans/spend, no new authentication if avoidable, no unapproved install/update/configuration).

Any comparison should use a fixed representative task set and report quality/correctness, latency, peak RAM/VRAM, idle footprint, startup cost, model-residency behavior, failure/recovery, and operational dependencies. Do not choose a replacement based on parameter count or one memory snapshot alone. No install, download, model load/unload, restart, provider switch, CUDA/GPU edit, or credential change is authorized by this hypothesis.

## 5. Cross-chat space-time continuity and human-interaction lessons

The project memory is intended to behave as a space-time knowledge system, not a transcript dump. Every new chat should:
1. read the canonical remote `main` and its current SHA;
2. follow `AGENTS.md` → CHAT-ARCH README → top of CURRENT-STATE → CONTEXT-INDEX → MEMORY-OPERATING-PROTOCOL → relevant incident/history records;
3. activate `UAAL-ROOT-001` and preserve the causal chain: objective/context → evidence/provenance → hypothesis/frontier → authorized action → observation → reconciliation → persist/reuse;
4. retrieve established prior results and closed edges before asking the owner to repeat facts or rerunning investigations;
5. distinguish `HEAD_SOURCE`, `WORKTREE_SOURCE`, `CONFIRMED_LOCAL`, `OWNER_REPORTED`, `PROPOSED`, `NOT_FOUND`, and `UNRESOLVED` accurately;
6. turn failed interactions into constraints and discriminating acceptance checks, not just prose summaries;
7. select the next actor based on the first unresolved causal/evidential edge, required capability, access, cost and authorization;
8. provide progress visibility that differentiates queued, running, blocked, completed, failed and verified; never infer completion from an announcement;
9. verify persistent write-back by fetching the exact saved artifact and its identity;
10. preserve a negative result as time-bounded evidence, not as universal absence.

The 2026-10-21 human–IABV interaction audit already records `REQUEST_INTERPRETATION=FAIL`, `SCOPE_DISCIPLINE=FAIL`, `EXECUTION_PROVENANCE=FAIL`, `CAUSAL_LEARNING_EVIDENCE=FAIL`, `TASK_PROGRESS_OBSERVABILITY=PARTIAL`, and `LONG_RUNNING_MULTI_AI_READINESS=NOT_READY`. The latest resource incident reinforces these same failure classes: the requested narrow RAM diagnosis was previously replaced by a broad auto-scan, and the resource gate later emitted a deferral without enough observable evidence to audit it. Do not repeat broad auto-scan, claim that a report proves an action occurred, or make the owner manually bridge gaps that an authorized connected tool can complete.

Persistent GitHub documentation is necessary for continuity, but documentation alone does not prove autonomous learning. Learning is demonstrated only when a later decision retrieves a specific prior experience, applies its verified constraint, and records a changed outcome.

## 6. Bridge readiness: keep separate from RAM diagnosis

The RAM incident is important for environment stability but does not release the governance block. The bridge remains:
```
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
CANDIDATE_MERGED=NO
LOCAL_WORKTREE=UNTOUCHED
LOCAL_EXECUTOR_IDENTITY=UNRESOLVED
LOCAL_EFFECTIVE_CONFIGURATION=UNRESOLVED
```

The sole next route remains `IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE` for the already-authorized narrow static inspection. Do not retry the denied reader, bypass it, launch IABV/MCP or Codex CLI/App Server, or infer local runtime behavior from public `main`. Even after a permitted static read, bridge implementation, adoption and real transport each remain separately gated.

## 7. Evidence-linked persistence locations

- [Current routing snapshot](./CURRENT-STATE.md) — sole actor-routing authority.
- [Human–IABV interaction audit](./CHAT-ARCH-2026-10-21-human-iabv-interaction-audit.md) — request/scope/provenance/learning/progress findings.
- [Ollama startup causality](./CHAT-ARCH-2026-10-21-ollama-startup-causality-not-tested-by-codex-snapshot.md) — why prior RAM snapshot did not reproduce startup.
- [Local executor read denial and scope-fix test reconciliation](./CHAT-ARCH-2026-10-21-local-executor-read-denied-and-scopefix-test-result.md) — current bridge gate.
- GitHub issue #450 — persistent cognitive knowledge and organism-integrity backlog, including RAM observations and metacognitive resource receipt requirements.
- GitHub issue #470 — governance decision for the supported scoped-read route.

## Final reconciled state

```
CROSS_CHAT_CONTINUITY=DOCUMENTED; AUTONOMOUS_REUSE_NOT_YET_DEMONSTRATED
HUMAN_INTERACTION_LESSONS=PERSISTED
RESOURCE_DIAGNOSTIC=PARTIAL
ENVIRONMENT_SELF_STABILIZATION=NOT_DEMONSTRATED
OLLAMA_STARTUP_CAUSALITY=UNRESOLVED
LIGHTER_TOOL_OR_MODEL_ALTERNATIVE=PROPOSED_RESEARCH_ONLY
GOVERNED_SCOPED_READ_ROUTE=UNRESOLVED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```
