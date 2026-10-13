# CHAT-ARCH-2026-10-13-233 — Desktop preflight outcome and launch-provenance gate

**Date:** 2026-10-13 (America/Bogota)
**Classification:** Owner-supplied read-only preflight intake / provenance boundary / next authorization gate
**Canonical baseline at intake:** remote `main @ f6a098fabf38ef6cc1519556d6c3d4b53471cd34`.
**Coverage:** one complete Owner-pasted report classified `DESKTOP_PREFLIGHT_BLOCKED`; no independent Windows/runtime observation was performed by this writeback.

## 1. Objective remains the Codex-specific development bridge

Required outcome: governed `IABV → Codex → IABV` delivery of a development prompt, a result from the same session/turn, task/result correlation, evaluation by the existing consumer and later governed self-development. Preserve `UAAL-ROOT-001`, RQ128, D016 and the distinction between M0-A transport, M0-B capability/actor selection and causal reuse.

## 2. Latest preflight result — OWNER_SUPPLIED_REPORT

Classification: `DESKTOP_PREFLIGHT_BLOCKED`.

Reported worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`; branch `codex/m0a-safe-ui-boot`; HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`; 56 tracked modifications and 5 untracked files. Report says all were preserved and no tests/builds/processes/network/UI interaction beyond passive observation occurred.

Reported visible target: one non-minimized top-level window titled `ChatGPT`, HWND `0x17B0900`, owned by PID `12476`. Its image is `ChatGPT.exe` under the packaged `OpenAI.Codex` installation path. The snapshot reportedly contained 12 processes with that image, but one visible main window.

Important naming note: title `ChatGPT` and executable name `ChatGPT.exe` do not independently establish session identity or account state; the executable's packaged `OpenAI.Codex` location is the supplied attribution evidence for Codex Desktop.

## 3. Exact open edge

Static source report says strict Desktop rollout capture reads from the IABV workspace path:
`data/tool_teaching/external_assistants/codex_home`

including `state_5.sqlite` and `sessions`.

The existing strict UI path targets an already-running window; it does not launch that PID. While the adapter can set a `CODEX_HOME` value in a launch environment, the inspected strict path does not establish that the already-running PID `12476` was launched with that same home.

Therefore the window/process is identified within the reported observation, but `PID 12476 → effective CODEX_HOME → IABV rollout/session store` remains unproven. Neither a HWND, PID, executable path nor existence of files in the expected directory is sufficient to establish that the live process writes there.

## 4. Next observation — exact scope and safety boundary

Next candidate is a one-time, read-only launch-provenance check. Before it is performed, obtain separate explicit Owner authorization. Prefer existing non-sensitive process-start provenance that can bind the PID and ancestor/launcher to the configured capture home. If that source is absent, report the gap; do not invent retrospective provenance.

If direct inspection of the running process is the only possible route, any additional permission must be explicit and allowlisted: inspect only the effective `CODEX_HOME` value for PID `12476` and the minimum parent/launch metadata needed for attribution. Do not dump the process environment, read arbitrary process memory, enumerate unrelated variables, inspect credential-bearing fields, read private profile or session contents, or expose other environment values. If the operating system cannot retrieve that single value without broad secret-bearing inspection, stop and report `LAUNCH_PROVENANCE_UNAVAILABLE` rather than widening scope.

Use canonical path comparison against the exact IABV capture home found in the inspected source. Distinguish (a) launch configuration/provenance, (b) current process environment if available, (c) rollout/session writes observed over time, and (d) causal linkage of a particular future response. A matching configured path or process variable alone proves only configuration alignment, not that a given response was written and later captured.

No application controls inspection, compositor reading, clicks, typing, window activation, page navigation, prompt dispatch, CDP, App Server invocation, process launch/stop, tests/builds, code/config/data mutation, credential extraction or additional-spend route is part of this check.

## 5. Evidence outcomes

Use one of:
- `DESKTOP_CAPTURE_HOME_LINKAGE_VERIFIED`: admissible launch evidence binds PID `12476` to the canonical capture home. This permits only a subsequent independently authorized dispatch-planning/review phase; it does not authorize sending.
- `LAUNCH_PROVENANCE_UNAVAILABLE`: no existing admissible source proves the launch binding and direct process inspection is disallowed or unavailable.
- `DESKTOP_CAPTURE_HOME_MISMATCH`: the effective home is demonstrably different from the capture path.
- `DESKTOP_LINKAGE_AMBIGUOUS`: the evidence binds neither uniquely nor completely.

Keep the original preflight classification `DESKTOP_PREFLIGHT_BLOCKED` as the historical result; a later result supersedes only the launch-provenance edge if supported by new evidence.

## 6. Preservation and wider gates

Do not alter the dirty worktree or the five untracked files. Last reported counts have not been independently remeasured. No code edits, test execution, processes, network calls or UI actions occurred during the reported preflight.

App Server remains an alternative, but its effective auth/home and pre-execution tool-control guarantees are unproven. Do not launch it to bypass a Desktop provenance blocker. The ChatGPT Web edge remains `TARGET_DISCOVERY_BLOCKED` for that separate route. Ollama remains auxiliary with real inference unproven. Do not add providers.

The no-additional-spend constraint remains: no billable API key, credits, paid subscription, installation or model download. Transport approval is not self-mutation authority; RQ218/RQ223/RQ224 workspace/trust/receipt gates remain separate. No dispatch is authorized by this record.

## 7. Continuity projections

Update README, CURRENT-STATE, CONTEXT-INDEX, MEMORY-OPERATING-PROTOCOL, SYMBIOSIS-MAP, UNRESOLVED-KNOWLEDGE and ARCHIVE-REGISTRY to point to this result and set the immediate edge to `DESKTOP_CAPTURE_HOME_LINKAGE_UNPROVEN`. This is a documentary writeback based solely on the supplied preflight report.

**Current route status:** `DESKTOP_PREFLIGHT_BLOCKED`.
**Immediate open edge:** `DESKTOP_CAPTURE_HOME_LINKAGE_UNPROVEN`.
**Next actor/action:** Owner authorization → one-time read-only launch-provenance inspection using only an allowlisted non-sensitive source.
**No prompt dispatch or runtime operation is authorized by this record.**