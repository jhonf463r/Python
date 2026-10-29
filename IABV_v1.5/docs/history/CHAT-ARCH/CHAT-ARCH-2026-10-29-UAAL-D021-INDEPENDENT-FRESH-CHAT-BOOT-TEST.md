# Independent fresh-chat boot and method-application test

**Purpose:** test what an independently opened ChatGPT session can retrieve and apply from canonical external memory. This is an explicit handoff test, not proof that memory loads automatically.

## Copy this complete prompt into a newly opened ChatGPT conversation

---

You are the independent validation session for the IABV Space-Time / cross-session memory lane. Do not assume you have any hidden context from the earlier conversation. Your first task is to independently retrieve and adjudicate the canonical GitHub state.

### 1. Bind the live source before reasoning
Repository: `jhonf463r/Python`.

Read the current live `refs/heads/main` first and record the exact SHA and observation time. Then retrieve from that exact main:
- `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — sole active route authority.
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-UAAL-D021-CROSS-SESSION-BOOT-AND-STATE-RECONCILIATION.md` — method contract.
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-23-CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1.md` — living Space-Time operating protocol.
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-UAAL-D021-FIRST-LATER-TASK-REUSE-RECEIPT.md`.
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-UAAL-D021-SECOND-LATER-TASK-REUSE-RECEIPT.md`.
- This test handoff file: `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-29-UAAL-D021-INDEPENDENT-FRESH-CHAT-BOOT-TEST.md`.

Bind every assertion to the exact ref/blob. If normal reading of `CURRENT-STATE.md` returns empty, find its blob in the Git tree for the exact main commit and fetch by that blob SHA. An empty/truncated transport response is retrieval failure, not an empty file. Do not use old HEADs or counts as current without comparing them against live main.

### 2. Activate the method and show a decision it changes
Apply D019's first-open-causal-edge / anti-loop rule, D020's verified-progress utility and strategy-switch rule, and D021's route-truth, task-local world-model and incoming-result adjudication requirements.

Create a concise `WORLD_MODEL_SNAPSHOT` with: objective and acceptance oracle; observed time/currentness; exact source refs; verified observations separated from inferences/unknowns/NOT_RUN; competing explanations and their falsifiers; authority/scope/no-go limits; first open causal/evidential edge; selected action and why it is the smallest useful authorized step; expected observation and stop condition.

Do not merely summarize the files. Identify one concrete conclusion or action choice that changed because of retrieved canonical memory rather than old conversational recency. If you cannot demonstrate a changed choice, mark method application as partial/unknown rather than claiming success.

### 3. Strict safety and evidence boundaries
This test is in the continuity/documentation lane only. Do not modify product code, tests, build configuration or runtime; do not create credentials, keys, authority assets, Entra registrations, MCP allowlists, protected reads, tunnel or bridge activation. Do not merge, rebase or alter PRs #555, #556 or #557. Do not change the technical gates: `G1/G2/G3=NOT_ESTABLISHED`, `PROTECTED_READS=FAIL_CLOSED`, `TUNNEL=DISABLED`, `BRIDGE=BRIDGE_NOT_READY`, `MCP_TOOL_ALLOWLIST=EMPTY`.

Do not invent a new Owner objective or a result from Chat B. If a current concrete user objective or incoming result is actually available in this fresh conversation, adjudicate it against the original contract and exact HEAD. Otherwise keep the experiment bounded to source retrieval, method activation and the first open edge.

### 4. Report the result without overclaiming
Return a compact receipt with:
- `observed_main_sha`
- `route_blob_sha` and retrieval result
- exact paths/blobs retrieved
- `activated_rules`
- `WORLD_MODEL_SNAPSHOT`
- `method_application` and the exact action choice it changed
- `result_evidence_and_provenance`
- `first_open_causal_edge`
- `independent_fresh_chat_retrieval=VERIFIED|PARTIAL|FAILED`
- `independent_fresh_chat_method_application=VERIFIED|PARTIAL|UNKNOWN`
- `automatic_cross_session_boot=NOT_PROVEN` unless you have genuinely independent evidence beyond this explicit prompt
- `product_tests_build_runtime=NOT_RUN`
- the exact next authorized action and stop condition.

If there is no separate non-identical Owner task in the new conversation, do not claim a third causal-reuse instance. Explicit retrieval prompted by this handoff only verifies the explicit bootstrap path; it does not prove an arbitrary new chat automatically received memory, nor that model weights changed.

---

## Acceptance condition for this experiment

A fresh-chat retrieval is verified only if the new session independently reads the live canonical source bytes and cites exact refs/blobs. Method application is verified only if it shows a specific action-selection difference caused by the retrieved rules and checks the resulting observation. Automatic boot remains **NOT_PROVEN** unless a test without an explicit retrieval instruction demonstrates it. The Owner must later adjudicate the receipt against its exact source refs; do not merge any code or change G1/G2/G3 as part of this test.
