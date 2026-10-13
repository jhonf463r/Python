# CHAT-ARCH-2026-10-13-230 — M0-A free-route and continuity reconciliation

**Date:** 2026-10-13 (Owner report received at approximately 10:12 America/Bogota)
**Classification:** route reconciliation / local-branch evidence intake / continuity and method delta
**Status:** documentary record of an Owner-supplied Codex report; no independent local runtime verification
**Canonical intake baseline:** `main @ 277930351ce4fab36b18f1aaee5aef6a61b5326f`, tree `c8a714376c5c851d2a5c4346ece5751ae00b303e`
**Source coverage:** one complete, user-pasted Codex result for `M0A_OLLAMA_SAFEUI_ADAPTER_WIRED`, plus current canonical documents read from GitHub. This is not the full prior transcript and no hash of the pasted report bytes is available.

## 1. Owner objective and permanent constraint

The governing objective is:

`HUMAN ↔ IABV ↔ capability-bearing AI / tools`

IABV should become the primary human interface and coordinator, reduce routine manual prompt/response transport, and eventually use appropriate external capabilities to advance its own governed development. Provider-specific adapters are realizations, not the universal algorithm.

**Cost constraint:** use resources already available without additional spend. Do not route M0-A through a billable API, ask the Owner to create an API key, buy credits, subscribe, install software, or download a model. The Owner explicitly corrected the prior route drift after an API-key-dependent OpenAI Responses API path was proposed. That API integration may remain preserved as an opt-in local experiment but is not eligible for the active route under the current constraint.

## 2. Canonical conceptual lineage

- `UAAL-ROOT-001`: objective → perceive/represent → interpret/maintain uncertainty → infer needed capability → discover candidate realizations → check constraints/access/resources → select/govern/act → observe/verify → update reusable knowledge → reuse/adapt.
- `UAAL-D016`: governed, reversible, evidence-driven evolution of IABV's own capability system; the first practical inflection is closing a controlled code-evolution loop, not merely adding code or agents.
- `RQ128`: M0-A (explicitly mediated external handoff) and M0-B (objective-driven selection of an unnamed external capability) are separate questions.

The external bridge is an enabling edge, not a substitute for the development loop. A completed consultation alone does not prove self-development, and storing a response alone does not prove learning or causal reuse.

## 3. Latest local result: Ollama adapter — Owner-supplied report

Reported classification: `M0A_OLLAMA_SAFEUI_ADAPTER_WIRED`.

Reported branch/worktree:
- branch `codex/m0a-safe-ui-boot`
- HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- final worktree: 56 tracked files modified and 5 untracked files
- no commit or push
- eight files reportedly edited, with aggregate `+1,162 / -56`; example paths shown include `ollama_expert_provider.py`, `tool_adapters.py`, and `tool_registry.py`.

Reported synthetic/static verification:
- 58 focused tests passed, including OpenAI regression tests.
- AST checks passed for 14 Python files and `git diff --check` was clean.
- The local SafeUI route reportedly wires one-use authorization → `ToolTeachService` → fixed `ollama_llm` adapter → correlated capture and persisted `ToolResult`.
- Test doubles cover the loopback endpoint, fixed model, no `tools` field, invalid/text-call rejection, correlation and persistence.

**Evidence boundary:** this is an actor-reported synthetic result, not a test rerun or independent review in this writeback. Ollama's effective API readiness and real inference were not tested. The result receipt correlates IABV's local operation; it is not an independent server-side confirmation.

## 4. What Ollama solves and what it does not

The new route is a useful local capability and potentially a low-cost way to exercise the shared SafeUI/ToolTeach/result path after a separately authorized local runtime test. It is not a bridge to the user's ChatGPT Web or Codex session. Its adapter being wired does not prove an end-to-end runtime exchange and does not meet the immediate goal of sending development work to an external coding agent.

Do not discard the local work. Preserve it as a candidate realization. Do not expand it further merely to increase provider count.

## 5. Reconciled routes and the decision

### Route A — Existing ChatGPT Web session (current canonical M0-A frontier)

The current canonical product record 229 identifies `TARGET_DISCOVERY_BLOCKED` as the first open edge. Static inspection identified the configured CDP metadata endpoints `/json/version` and `/json/list`, but the prior attempt made no request and did not establish the target count or page identity.

This remains the active route because it honors the free-use constraint and targets an existing authenticated session. It is still blocked. **Scope boundary:** a successful ChatGPT Web round trip proves a generic free external-consultation path only; it does not by itself prove that IABV can dispatch development tasks to Codex and capture Codex's result. Treat the Codex-specific code-development bridge as a separate acceptance edge, using existing RQ128 organs rather than assuming the Web route closes it. A future read-only metadata check is permissible only after a separate, specific Owner authorization and only if the listener can first be tied to the expected existing browser without starting a process. No port scanning, browser startup, helper process, WebSocket, navigation, page script, private conversation inspection, pending approval creation or canary dispatch. If listener identity or a safe read-only mechanism cannot be established, remain blocked.

### Route B — Codex desktop/App Server

Codex remains a strategically relevant coding capability for the later self-development loop. Prior static reports did not establish effective session authentication in the target runtime or an enforceable guarantee that tools cannot execute during a text-only consultation. Sandbox labels and rejecting activity events after receipt do not prove pre-execution prevention. Do not silently treat the App Server route as ready or safe. Reopen it only with a concrete, bounded capability/evidence task and the required permissions.

### Route C — Ollama local

Keep the newly wired adapter as an optional local realization. Its current maturity is `WIRED_REPORTED / SYNTHETIC_TESTS_REPORTED / LIVE_INFERENCE_UNPROVEN`. A future authorized local smoke test could verify the SafeUI → provider → ToolResult path without a billable API, but it would not close external ChatGPT/Codex transport or objective-driven actor selection.

### Route D — OpenAI API

Out of active scope under the Owner's cost constraint. Do not ask for `OPENAI_API_KEY`, do not call the API and do not recommend it as the next step unless the Owner explicitly changes the cost requirement. Preserve existing local work without allowing this candidate to displace the free route.

## 6. Recommended sequence — minimum work toward the stated goal

1. **Freeze scope:** do not add more provider adapters or refactor the universal coordinator. Preserve the dirty worktree and all new evidence.
2. **Return to the canonical M0-A edge:** `TARGET_DISCOVERY_BLOCKED` for the existing free ChatGPT Web session. Ask the Owner for separate, narrowly scoped authorization before any local CDP metadata observation. Do not treat the previous API-call authorization as CDP authorization.
3. **Only after target identity is proved:** use the normal SafeUI route to display and approve the exact destination and exact canary/request; dispatch once; capture from the same target; verify correlation and persist the response. On timeout/ambiguity, do not retry.
4. **After M0-A round trip:** prove that the result reaches its existing consumer and is used in an explicitly governed code-development task. That still does not establish M0-B or causal learning.
5. **Then close the D016 loop:** bounded deficit → minimal isolated variant → comparable tests/baseline → independent verification → governed promote/reject/rollback. Later, test whether a verified prior result changes a subsequent decision and improves its outcome.
6. Keep local Ollama available as an auxiliary realization where it materially improves local reasoning or can test shared SafeUI mechanics, not as a substitute for the current external-session edge.

This ordering follows the first unresolved causal edge and prevents additional integration work from obscuring it.

## 7. Interaction space-time / transcript continuity

Use the existing Memory Operating Protocol; do not create a parallel memory organ. For every material episode preserve at least:
- episode/source identity and timestamp/order;
- objective, stage, environment and resource conditions;
- activated prior knowledge and human correction/decision;
- hypotheses, action and expected observation;
- actual observation and verifier;
- provenance and explicit evidence class;
- Knowledge, Method, Relation and Routing deltas;
- what remains unproven, next open edge and supersession links.

Evidence classes for this episode:
- **REMOTE_CANONICAL / COORDINATOR_VERIFIED:** current main baseline and current contents/routing of README, CURRENT-STATE, CONTEXT-INDEX, MOP, Constitution, D016, RQ128 and record 229.
- **OWNER_SUPPLIED_REPORT:** the Ollama wiring, 58 synthetic passes, local worktree counts and static checks.
- **INFERENCE / ROUTING DECISION:** preserve Ollama as an auxiliary realization; prioritize the canonical free ChatGPT Web target-discovery edge for the bridge goal.
- **UNPROVEN:** actual Ollama inference; actual ChatGPT Web/Codex round trip; external response ingestion and evaluation; M0-B dynamic selection; causal reuse; autonomous governed code evolution.

Persistence ≠ retrieval ≠ activation ≠ decision impact ≠ causal reuse. A branch-local patch ≠ canonical source state. Test pass ≠ runtime success. A provider registered in SafeUI ≠ an established bridge between independent AIs.

## 8. State and authority boundaries

The local branch/worktree report is distinct from remote `main`; its 56 modified files and 5 untracked files are not merged into `main`. No local code, test, runtime or manifest was independently inspected by this writeback, and no local command, process, HTTP request, CDP request or inference was executed here.

The remote canonical security route remains separate: RQ224 Option A is design-only; RQ218/RQ223 gates remain open. M0-A transport progress neither closes nor authorizes changes to those mutation-authority gates. Overall MCP readiness remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.

## 9. Acceptance criteria for the next M0-A edge

Do not mark `REAL_ROUND_TRIP_VERIFIED` until all required observations are tied to the same task/session:
- one eligible target identified with provenance and an unambiguous page identity;
- SafeUI displayed the exact target and exact text before explicit approval;
- one authorized dispatch occurred;
- the expected response was captured from that same target;
- request/response correlation and ingestion succeeded;
- the existing consumer completed its evaluation;
- no unapproved tool action or provider fallback occurred.

If safe destination discovery cannot be done with existing admissible access, keep `TARGET_DISCOVERY_BLOCKED` and request the exact missing Owner authorization or identify the precise missing capability. Do not relabel it as target-not-found.

## 10. Canonical sources

- [README.md](README.md)
- [CURRENT-STATE.md](CURRENT-STATE.md)
- [CONTEXT-INDEX.md](CONTEXT-INDEX.md)
- [MEMORY-OPERATING-PROTOCOL.md](MEMORY-OPERATING-PROTOCOL.md)
- [Constitution / UAAL-ROOT-001](UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md)
- [D016 self-development inflection](CHAT-ARCH-2026-10-05-054-iabv-self-development-inflection-code-plasticity.md)
- [RQ128 M0 routing reconciliation](CHAT-ARCH-2026-10-07-128-m0-causal-routing-reconciliation.md)
- [229 SafeUI target-discovery continuity](CHAT-ARCH-2026-10-13-229-m0a-safeui-target-discovery-continuity.md)

This is a documentary continuity and routing update only. It does not promote the local source changes into main, independently verify runtime behavior, or authorize CDP/runtime operations.
