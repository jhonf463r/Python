# CHAT-ARCH-2026-10-13-231 — Codex bridge priority clarification

**Date:** 2026-10-13 (America/Bogota)
**Classification:** Owner objective clarification / product-routing correction / documentation-only
**Canonical baseline reviewed:** remote `main @ c9f7b2ced5c3878c33499d08ec76c87350f4e2df` before this writeback.
**Evidence coverage:** current GitHub projections and records 229–230; the Owner-pasted `M0A_OLLAMA_SAFEUI_ADAPTER_WIRED` report; current public Codex App Server documentation. Local source/runtime was not independently inspected or executed in this writeback.

## 1. Owner clarification: the bridge that matters

The immediate product priority clarified by the Owner is not merely generic access to an external AI. It is a governed **IABV → Codex → IABV** path so IABV can send development prompts to Codex, receive Codex's result automatically, correlate it to the originating task, evaluate it and use verified results in the controlled self-development path.

Keep the larger goal `HUMAN ↔ IABV ↔ capability-bearing AI/tools`: Codex is a candidate realization for code-development tasks, not the universal algorithm itself. M0-A (explicit, mediated handoff) and M0-B (objective-derived capability/actor selection) remain separate.

**Routing correction:** the prior record 230 selected existing ChatGPT Web target discovery as the active free external-consultation route. That remains valid evidence and a possible generic consultation route, but it does not directly close the newly clarified Codex-specific development objective. Defer the proposed CDP metadata check for now; it is not authorized by this record. Do not reinterpret this correction as authorization for process launch, network requests, UI actions, approvals or sending a prompt.

## 2. Evidence that must remain distinct

- **REMOTE_CANONICAL:** record 128 statically documents the existing Codex consultation composition through `ControlCenterViewModel.sendChat()` → `ToolTeachService`/`ToolTask`/`ToolRegistry` → `ExternalAssistantToolAdapter`/`UIExecutionRunner`, with Codex rollout/thread capture as a defined path. Its table still marks actual Codex execution/runtime capture unproven.
- **OWNER_SUPPLIED_REPORT:** `M0A_OLLAMA_SAFEUI_ADAPTER_WIRED`; 58 focused synthetic tests reportedly pass; the dirty local worktree is reported as branch `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`, 56 tracked modifications and 5 untracked files. Do not discard or reset it. This code is not integrated into `main`; no live Ollama inference or end-to-end round trip was observed.
- **OWNER_SUPPLIED / NOT INDEPENDENTLY VERIFIED:** the recent worktree's report references `CodexAppServerToolAdapter`; the archived/base source did not contain it, so App Server test comparisons against that base are not evidence of baseline failure or runtime success.
- **OFFICIAL EXTERNAL DOCUMENTATION:** Codex App Server exposes a client protocol for initialization, starting/resuming a thread, sending a turn and consuming streamed/final events. Its client must process approval requests and distinguish `turn.status=completed` from failed/interrupted results. This interface is conceptually closer to a direct Codex prompt/response bridge than locating a ChatGPT Web tab. It does not prove that IABV's current adapter uses it safely or that the user's local authentication/plan entitlement is available.
- **UNPROVEN:** a working direct Codex App Server exchange from IABV; effective authentication and cost/entitlement behavior in this environment; enforceable pre-execution tool policy for text-only handoff; response correlation/ingestion into the existing consumer; M0-B; the D016 governed code-evolution loop; causal reuse.

## 3. Decision: inspect the Codex-specific path before spending effort on CDP

Freeze provider expansion. Preserve all dirty local changes and untracked files. Do not extend Ollama further merely to add provider count; preserve it as an auxiliary local realization.

The next discriminating action is a **bounded, read-only static audit of the existing Codex path in the reported local worktree**, comparing only these already identified alternatives:

1. the candidate `CodexAppServerToolAdapter` path; and
2. the established `ExternalAssistantToolAdapter` + `UIExecutionRunner` + Codex rollout/thread capture path from RQ128.

Do not invent another coordinator, memory system, generic provider layer or alternate authorization mechanism. Identify the exact earliest failed or unproven edge and choose the path with the least missing functionality and strongest evidence.

Required audit questions:

1. Is the App Server adapter actually composed into the ordinary SafeUI/ToolTeachService/ToolRegistry flow for an explicitly chosen Codex consultation, or is it only a standalone/test adapter?
2. What process/transport does it use, and can identity and lifecycle be attributed without broad process scans or revealing secrets?
3. What existing authentication source does it use? Do not print/read/exfiltrate tokens or introduce an API key. Distinguish ChatGPT-plan/OAuth access from billable API-key usage; do not assume either entitlement or zero additional spend without evidence.
4. How does it initialize, bind `threadId`/`turnId`/request correlation, consume streaming events and accept only a successful terminal completion?
5. Does the request actually prevent tool execution before effects, rather than merely rejecting tool events after they arrive? How are server-initiated approval requests handled? A natural-language instruction to 'do not use tools' is not an enforcement control.
6. How are timeout, cancellation, uncertain completion, duplicate dispatch, process cleanup and late events handled? Does one authorization bind the exact destination and prompt and permit at most one dispatch?
7. Does a completed reply reach the existing consumer and get evaluated, or is the current proof limited to adapter output / `ToolResult` persistence?
8. If App Server lacks a safe, locally available auth/tool-control contract, does the existing desktop + rollout capture path provide a smaller viable route, and what exact execution-channel permission is missing?

## 4. Scope of the next Codex task

Read-only source inspection only in `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`. Verify actual branch, HEAD and status first; preserve every existing modification and untracked file. No code edits, formatters, tests, commits, pushes, branch changes, process starts/stops, local HTTP/DNS, App Server invocation, inference, UI/CDP activity or credential inspection are included in this next audit.

Report exact source paths, relevant call sites, branch/HEAD/status, and tests already reported versus independently run. Classify each claim as static fact, test-double evidence, actor-reported runtime evidence or unproven. End at the first scope boundary requiring a separate authorization.

## 5. Acceptance boundary and sequence

Do not mark the bridge complete until one specifically authorized Codex task has: (a) an unambiguous Codex destination and task ID; (b) exact prompt and intent-bound one-use approval; (c) a single dispatch through the normal IABV route; (d) a successful terminal Codex result captured from that same thread/turn; (e) request/result correlation and ingestion; and (f) observed evaluation by the existing consumer.

After that, D016 remains a separate governed loop: verified deficit → immutable baseline → isolated candidate → comparable tests → independent review → governed promote/reject/rollback. A real reply or persisted memory alone is not proof of learning. Later causal reuse requires a distinct non-identical task and an observable change in IABV's decision/result.

Cost constraint remains: no billable API key, API credits, subscription purchase, installation or model download. A plan-authenticated App Server route may be considered only if its existing authentication and entitlement are established without new spend; otherwise preserve the current constraint and stop.

## 6. Projection changes required

`CURRENT-STATE.md` is the current routing authority and must name the Codex-specific bridge audit as the active priority. README, CONTEXT-INDEX, MEMORY-OPERATING-PROTOCOL, SYMBIOSIS-MAP, UNRESOLVED-KNOWLEDGE and ARCHIVE-REGISTRY must point to this record. Records 229–230 remain historical evidence and must not be rewritten as though their reported events did not occur.

**Status after this record:** `CODEX_BRIDGE_ROUTE_REASSESSMENT_REQUIRED`; no new runtime outcome is claimed and no execution is authorized.